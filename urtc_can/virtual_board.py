# =============================================================================
# URTC-COMMON - src/urtc_common/virtual_board.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""A virtual tool-head board behind an SLCAN adapter that listens on a TCP port.

The flasher, the tester and the gateway open their CAN channel through ``transports.SLCAN``. Given a URL that
pyserial understands (``socket://127.0.0.1:7777``) instead of a COM port, that class talks to this server, and
behind it there is a board that answers like the real one, so every one of those programs can be run end to end
with no adapter and no hardware::

    python -m urtc_common.virtual_board --port 7777
    # then, in a tool, choose the port  socket://127.0.0.1:7777

Two layers:

* ``SlcanAdapter`` is the adapter: it parses the lines of the SLCAN subset (bit rate, open, listen-only, close,
  version queries and standard ``t`` frames), answers them as an adapter does (a carriage return, or a bell for what
  it does not understand, ``z`` after an accepted transmit) and refuses to transmit when the channel is closed or
  opened listen-only.
* ``VirtualBoard`` is what sits behind it. In application mode it answers the version query (0x7F8 with 0x7F9 and the
  patch frame 0x7E9) and the active-tool query (0x110 with 0x111), and enters the bootloader on 0x7F0 carrying the
  magic payload and on nothing else, announcing it with the heartbeat of the listening window. In bootloader mode it plays the update exchange of ``transports.MockCAN``.

This is a second reading of the protocol by the same author as the tools, not the firmware: the tests run the
shared conformance vectors through it, but only the firmware's own virtual board (``tests/virtual_board.c`` in the
URTC repository, started with ``--exec``) runs the real receive path. ``--exec`` bridges the same SLCAN text to any
program that reads one line per frame on its standard input and writes SLCAN lines on its standard output, which is
what that program does.

The server listens on the loopback interface unless told otherwise: anybody who can reach the port can talk to the
board.
"""
from __future__ import annotations

import argparse
import shlex
import socket
import subprocess
import sys
import threading
from typing import Any, Callable, Iterable

from . import protocol
from .framing import FrameError
from .slcan import decode_line, encode_line
from .transports import MockCAN

Frame = tuple[int, bytes]

APPLICATION = "application"
BOOTLOADER = "bootloader"
DEFAULT_PORT = 7777
ADAPTER_VERSION = "V0101"  # hardware 01, software 01: what the V command answers


def _magic(name: str) -> bytes:
    magic: Any = protocol.MAGIC_PAYLOADS[name]
    return bytes.fromhex(magic["data"])


class VirtualBoard:
    """The board: frames in, the frames it would transmit out.

    ``version`` is the application version (major, minor) and ``patch`` its patch number (``protocol.PATCH_UNKNOWN``
    to say it is not known, ``None`` for a board that predates the patch frame and never sends 0x7E9). ``state``
    holds the quick-state fields the active-tool answer reports. ``bootloader=True`` starts in the bootloader.
    The remaining keyword arguments go to ``transports.MockCAN`` (the bootloader's behaviour).
    """

    def __init__(self, hardware_id: int = protocol.HARDWARE_ID_MAIN, version: tuple[int, int] = (0, 4), patch: int | None = 0,
                 accepts_patch: bool = False, tool_id: int = 0, system_error: bool = False, can_error: bool = False,
                 booting: bool = False, thermal_fault: int | None = 0, reset_cause: int | None = 0,
                 bootloader: bool = False, **bootloader_options) -> None:
        self.hardware_id = hardware_id
        self.version = version
        self.patch = patch
        self.accepts_patch = accepts_patch
        self.tool_id = tool_id
        self.system_error = system_error
        self.can_error = can_error
        self.booting = booting
        self.thermal_fault = thermal_fault
        self.reset_cause = reset_cause
        self.mode = BOOTLOADER if bootloader else APPLICATION
        self.bootloader_options = dict(bootloader_options)
        self.bootloader_options.setdefault("delay", 0)
        self.bootloader_options.setdefault("installed_version", version)
        self.bootloader_options.setdefault("installed_patch", patch)
        self.bootloader_options.setdefault("accepts_patch", accepts_patch)
        self._bootloader = MockCAN(**self.bootloader_options)
        self.received: list[Frame] = []

    # ---- the application -------------------------------------------------------------------------
    def _version_answer(self) -> list[Frame]:
        frames = [protocol.encode_version_response(protocol.RESPONDER_APPLICATION, self.hardware_id, self.version[0], self.version[1])]
        if self.patch is not None:
            flags = protocol.PATCH_FLAG_ACCEPTS_IN_END_UPDATE if self.accepts_patch else 0
            frames.append(protocol.encode_version_patch_response(protocol.RESPONDER_APPLICATION, self.patch, flags))
        return frames

    def _quick_state(self) -> Frame:
        return protocol.encode_active_tool_resp(self.tool_id, int(self.system_error), int(self.can_error), int(self.booting),
                                                self.thermal_fault, self.reset_cause)

    def _application(self, can_id: int, data: bytes) -> list[Frame]:
        if can_id == protocol.CAN_ID_QUERY_VERSION:
            return self._version_answer()
        if can_id == protocol.CAN_ID_QUERY_ACTIVE_TOOL:
            return [self._quick_state()]
        if can_id == protocol.CAN_ID_ENTER_BOOTLOADER and data == _magic("enter_bootloader"):
            self.enter_bootloader()
            # The bootloader opens its listening window with its first heartbeat: status "listening", progress not applicable.
            return [(protocol.CAN_ID_HEARTBEAT, bytes([protocol.STATUS_LISTENING, 0xFF]))]
        return []  # every other identifier is outside what this model plays

    # ---- the bootloader --------------------------------------------------------------------------
    def enter_bootloader(self) -> None:
        self._bootloader = MockCAN(**self.bootloader_options)
        self.mode = BOOTLOADER

    def reboot(self) -> None:
        """Back to the application, as after the board resets."""
        self.mode = APPLICATION

    def _bootloader_frames(self, can_id: int, data: bytes) -> list[Frame]:
        self._bootloader.send_frame(can_id, data)
        out: list[Frame] = []
        while True:
            frame = self._bootloader.read_frame()
            if frame is None:
                return out
            out.append(frame)

    # ---- the bus ---------------------------------------------------------------------------------
    def handle(self, can_id: int, data: bytes = b"") -> list[Frame]:
        """The frames the board transmits in answer to one received frame (possibly none)."""
        data = bytes(data)
        self.received.append((can_id, data))
        if self.mode == BOOTLOADER:
            return self._bootloader_frames(can_id, data)
        return self._application(can_id, data)


class SlcanAdapter:
    """The adapter between a text stream and a board: ``feed(bytes)`` returns the bytes to send back."""

    def __init__(self, board: VirtualBoard, acknowledge_transmit: bool = True) -> None:
        self.board = board
        self.acknowledge_transmit = acknowledge_transmit
        self.state = "closed"  # closed, open or listen
        self.bitrate_code: str | None = None
        self._pending = b""

    @staticmethod
    def _lines(frames: Iterable[Frame]) -> bytes:
        return b"".join(encode_line(can_id, data).encode("ascii") + b"\r" for can_id, data in frames)

    def command(self, line: str) -> bytes:
        """The reply to one line (without its terminator)."""
        if not line:
            return b""
        head = line[0]
        if head in "tT":
            if head == "T" or self.state != "open":
                return b"\a"  # no 29-bit frames; nothing is sent from a closed or listen-only channel
            frame = decode_line(line)
            if frame is None:
                return b"\a"
            replies = self._lines(self.board.handle(frame.id, frame.data))
            return (b"z\r" if self.acknowledge_transmit else b"") + replies
        if head == "S" and len(line) == 2 and line[1] in "0123456789":
            if self.state != "closed":
                return b"\a"
            self.bitrate_code = line[1]
            return b"\r"
        if head in "OL" and len(line) == 1:
            if self.state != "closed":
                return b"\a"
            self.state = "open" if head == "O" else "listen"
            return b"\r"
        if head == "C" and len(line) == 1:
            self.state = "closed"
            return b"\r"
        if head == "V" and len(line) == 1:
            return ADAPTER_VERSION.encode("ascii") + b"\r"
        if head == "F" and len(line) == 1:
            return b"F00\r"  # status flags: none set
        return b"\a"

    def feed(self, chunk: bytes) -> bytes:
        self._pending += chunk
        out = b""
        while b"\r" in self._pending:
            raw, self._pending = self._pending.split(b"\r", 1)
            try:
                line = raw.decode("ascii").strip("\n ")
            except UnicodeDecodeError:
                out += b"\a"
                continue
            reply = self.command(line)
            if reply and not reply.endswith(b"\r"):
                reply += b"\r"  # a bell is followed by the terminator like every other reply
            out += reply
        if len(self._pending) > 4096:
            self._pending = b""
        return out


class ProcessBackend:
    """Bridges the adapter's frames to a program that speaks SLCAN text by lines (the firmware's virtual board).

    Every line is written to the program's standard input with a newline; every line it prints is sent back to
    the client as it arrives. The program decides what the board does.
    """

    def __init__(self, command: list[str], send: Callable[[bytes], None]) -> None:
        self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self._send = send
        self._pending = b""
        self._thread = threading.Thread(target=self._pump, daemon=True)
        self._thread.start()

    def _pump(self) -> None:
        assert self.process.stdout is not None
        for raw in iter(self.process.stdout.readline, b""):
            if not raw:
                break
            text = raw.rstrip(b"\r\n")
            if text == b"X":
                continue  # the program reports a reset into the bootloader; nothing goes on the bus
            if text:
                self._send(text + b"\r")

    def feed(self, chunk: bytes) -> bytes:
        self._pending += chunk
        while b"\r" in self._pending:
            raw, self._pending = self._pending.split(b"\r", 1)
            line = raw.strip(b"\n ")
            if line and self.process.stdin is not None:
                try:
                    self.process.stdin.write(line + b"\n")
                    self.process.stdin.flush()
                except OSError:
                    break
        return b""

    def close(self) -> None:
        try:
            if self.process.stdin is not None:
                self.process.stdin.close()
        except OSError:
            pass
        try:
            self.process.terminate()
            self.process.wait(timeout=2)
        except Exception:
            pass


class VirtualBoardServer:
    """A TCP server whose every client talks SLCAN to one shared board, like several programs on one bus."""

    def __init__(self, board: VirtualBoard | None = None, host: str = "127.0.0.1", port: int = 0, command: list[str] | None = None,
                 acknowledge_transmit: bool = True) -> None:
        self.board = board or VirtualBoard()
        self.command = command
        self.acknowledge_transmit = acknowledge_transmit
        self._lock = threading.Lock()
        self._listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._listener.bind((host, port))
        self._listener.listen(8)
        self._listener.settimeout(0.2)
        self.host = host
        self.port = self._listener.getsockname()[1]
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._clients: list[socket.socket] = []

    @property
    def url(self) -> str:
        """What to type where a serial port is asked for."""
        return f"socket://{self.host}:{self.port}"

    def start(self) -> "VirtualBoardServer":
        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        for client in list(self._clients):
            try:
                client.close()
            except OSError:
                pass
        try:
            self._listener.close()
        except OSError:
            pass
        if self._thread is not None:
            self._thread.join(timeout=2)

    def __enter__(self) -> "VirtualBoardServer":
        return self.start()

    def __exit__(self, *exc) -> None:
        self.stop()

    def _accept_loop(self) -> None:
        while not self._stop.is_set():
            try:
                client, _ = self._listener.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            self._clients.append(client)
            threading.Thread(target=self._serve, args=(client,), daemon=True).start()

    def _serve(self, client: socket.socket) -> None:
        send_lock = threading.Lock()

        def send(data: bytes) -> None:
            with send_lock:
                try:
                    client.sendall(data)
                except OSError:
                    pass

        if self.command:
            backend: SlcanAdapter | ProcessBackend = ProcessBackend(self.command, send)
        else:
            backend = SlcanAdapter(self.board, self.acknowledge_transmit)
        try:
            client.settimeout(0.2)
            while not self._stop.is_set():
                try:
                    chunk = client.recv(4096)
                except socket.timeout:
                    continue
                except OSError:
                    break
                if not chunk:
                    break
                with self._lock:
                    reply = backend.feed(chunk)
                if reply:
                    send(reply)
        finally:
            if isinstance(backend, ProcessBackend):
                backend.close()
            try:
                client.close()
            except OSError:
                pass
            if client in self._clients:
                self._clients.remove(client)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="urtc-virtual-board", description="A virtual tool-head board behind an SLCAN adapter on a TCP port.")
    parser.add_argument("--host", default="127.0.0.1", help="interface to listen on (default: loopback only)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"TCP port (default {DEFAULT_PORT}; 0 picks a free one)")
    parser.add_argument("--firmware-version", dest="board_version", default="0.4", help="application version of the board, major.minor (default 0.4)")
    parser.add_argument("--patch", type=int, default=0, help="application patch number (default 0; 255 is unknown)")
    parser.add_argument("--tool", type=int, default=0, help="active tool profile reported in the quick state (default 0)")
    parser.add_argument("--bootloader", action="store_true", help="start in the bootloader instead of the application")
    parser.add_argument("--exec", dest="command", default=None, metavar="COMMAND",
                        help="bridge to a program that speaks SLCAN text by lines (the firmware's virtual board) instead of the built-in model")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        major, minor = (int(part) for part in args.board_version.split("."))
        board = VirtualBoard(version=(major, minor), patch=args.patch, tool_id=args.tool, bootloader=args.bootloader)
        server = VirtualBoardServer(board, args.host, args.port, shlex.split(args.command) if args.command else None)
    except (ValueError, OSError, FrameError) as exc:
        print(f"VIRTUAL_BOARD=FAIL {exc}", file=sys.stderr)
        return 2
    server.start()
    print(f"VIRTUAL_BOARD=LISTENING {server.url}  (type this where a serial port is asked for; Ctrl+C stops it)", flush=True)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
