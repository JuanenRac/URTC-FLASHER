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
what that program does. ``--firmware-repo DIR`` builds that program from a checkout of the URTC repository (inside WSL on Windows, where the
fake flash of the firmware's host build needs a 64-bit Linux) and bridges to it, so FLASHER, TESTER and the gateway can be tried against the
real receive path with no adapter, no board and nothing to compile by hand: ``urtc-virtual-board --firmware-repo ../URTC``, then
``URTC_VIRTUAL_PORT=socket://127.0.0.1:7777`` where a port is asked for. ``--firmware-bootloader`` bridges to the twin of the bootloader instead
(``tests/virtual_bootloader.c``: the bootloader of the master, its window, main loop, flash and signature check, compiled for the host), so an update can be
flashed through the real code that accepts or refuses it.

The server listens on the loopback interface unless told otherwise: anybody who can reach the port can talk to the
board.
"""
from __future__ import annotations

import argparse
import json
import shlex
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable, Iterable

from . import key_rotation as kr, key_rotation_command as krc, protocol
from .framing import FrameError
from .heater_sim import SolderingIronModel
from .local_build import local_build_refusal
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
                 bootloader: bool = False, heater_config: dict | None = None, key_rotation: krc.State | None = None,
                 error_reason: int | None = None, clear_result: int | None = None, features: int = 0, temperature_c: int = 20,
                 actuators_off: bool = True, **bootloader_options) -> None:
        # ``error_reason`` and ``clear_result`` are the two last bytes of the quick state (None: a board that does not send them). ``features`` is the mask in
        # force (every optional function off by default), ``temperature_c`` what the tool reads (0xFFFF: unknown) and ``actuators_off`` whether everything is at zero.
        self.error_reason = error_reason
        self.clear_result = clear_result
        self.features = features
        self.temperature_c = temperature_c
        self.actuators_off = actuators_off
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
        # The soldering iron loop is built on the first setpoint: a board that never gets one carries no model.
        self.heater: SolderingIronModel | None = None
        self.heater_config = heater_config
        # The signing keys this bootloader trusts (None: it announces nothing, as the bootloaders that predate the rotation). ``uptime_s`` is its own clock, which
        # restarts at zero on every reset; the time of the HOST arrives only inside a signed rotation command, never from this clock.
        self.key_rotation = key_rotation
        self.uptime_s = 0.0
        self.last_rotation_result: str | None = None
        self._assembler = krc.Assembler()

    def advance(self, seconds: float) -> list[Frame]:
        """Let simulated time pass: the telemetry the heater loop sends meanwhile (none when it never got a setpoint)."""
        self.uptime_s += seconds
        if self.mode == BOOTLOADER or self.heater is None:
            return []   # a head in its bootloader drives no heater
        return self.heater.advance(seconds)

    # ---- the application -------------------------------------------------------------------------
    def _version_answer(self) -> list[Frame]:
        frames = [protocol.encode_version_response(protocol.RESPONDER_APPLICATION, self.hardware_id, self.version[0], self.version[1])]
        if self.patch is not None:
            flags = protocol.PATCH_FLAG_ACCEPTS_IN_END_UPDATE if self.accepts_patch else 0
            frames.append(protocol.encode_version_patch_response(protocol.RESPONDER_APPLICATION, self.patch, flags))
        return frames

    def _quick_state(self) -> Frame:
        return protocol.encode_active_tool_resp(self.tool_id, int(self.system_error), int(self.can_error), int(self.booting),
                                                self.thermal_fault, self.reset_cause,
                                                self.error_reason if self.error_reason is not None or self.clear_result is None else protocol.ERROR_REASON_NONE,
                                                self.clear_result)

    def _clear_error(self, data: bytes) -> list[Frame]:
        """0x1B2: with the magic payload the decision of ``safety_policy`` is applied; the answer is the quick state, whose last byte tells the outcome."""
        if data != protocol.MAGIC_CLEAR_ERROR:
            return []   # any other payload is ignored, like every command that needs its magic
        from . import safety_policy   # here and not at the top: a program that copied this file before the decisions existed still imports it
        reason = self.error_reason if self.error_reason is not None else protocol.ERROR_REASON_UNKNOWN
        result = safety_policy.clear_error_decision(bool(self.features & protocol.FEATURE_CLEAR_ERROR), self.system_error, reason, self.temperature_c,
                                                    self.actuators_off)
        self.clear_result = result
        if result == protocol.CLEAR_ERROR_CLEARED:
            self.system_error = False
            self.error_reason = protocol.ERROR_REASON_NONE
            self.thermal_fault = 0 if self.thermal_fault is not None else None
        return [self._quick_state()]

    def _application(self, can_id: int, data: bytes) -> list[Frame]:
        if can_id == protocol.CAN_ID_QUERY_VERSION:
            return self._version_answer()
        if can_id == protocol.CAN_ID_QUERY_ACTIVE_TOOL:
            return [self._quick_state()]
        if can_id == protocol.CAN_ID_CLEAR_ERROR:
            return self._clear_error(data)
        if can_id == protocol.CAN_ID_SOLDER_SETPOINT and self.tool_id == protocol.TOOL_SOLDERING_IRON and not self.system_error:
            fields = protocol.decode_solder_setpoint(data)
            if fields is not None:
                if self.heater is None:
                    self.heater = SolderingIronModel(self.heater_config)
                self.heater.set_target(fields["setpoint_c"])
            return []
        if can_id == protocol.CAN_ID_ENTER_BOOTLOADER and data == _magic("enter_bootloader"):
            self.enter_bootloader()
            # The bootloader opens its listening window with its first heartbeat: status "listening", progress not applicable.
            return [(protocol.CAN_ID_HEARTBEAT, bytes([protocol.STATUS_LISTENING, 0xFF]))]
        return []  # every other identifier is outside what this model plays

    # ---- the bootloader --------------------------------------------------------------------------
    def enter_bootloader(self) -> None:
        self.heater = None
        self._bootloader = MockCAN(**self.bootloader_options)
        self.mode = BOOTLOADER

    def reboot(self) -> None:
        """Back to the application, as after the board resets."""
        self.mode = APPLICATION
        self.uptime_s = 0.0   # the clock does not survive a reset; what the rotation command stored (the window and the offset) does, in the state
        self._assembler = krc.Assembler()
        if self.key_rotation is not None:
            # The offset belonged to the previous uptime: a bootloader that lost its clock cannot place the window until the host sends a new command.
            self.key_rotation = self._after_reset(self.key_rotation)

    @staticmethod
    def _after_reset(state: krc.State) -> krc.State:
        return replace(state, clock_offset=0)

    def rotation_now(self) -> int:
        return krc.now_of(self.key_rotation, int(self.uptime_s)) if self.key_rotation is not None else 0

    def _rotation_frames(self, can_id: int, data: bytes) -> list[Frame] | None:
        """The answers of the key rotation (None: this frame is not about it). The status is asked with 0x7EA operation 05; the command comes on 0x7EC."""
        state = self.key_rotation
        if state is None:
            return None
        if can_id == protocol.CAN_ID_BOOTLOADER_SELECT and data[:1] == bytes([kr.STATUS_OP]) and len(data) == 1:
            ids, status = kr.announce(state.rotation, self.rotation_now())
            return [(protocol.CAN_ID_BOOTLOADER_KEY_ID, kid) for kid in ids] + [(protocol.CAN_ID_BOOTLOADER_SELECT_RESPONSE, status)]
        if can_id == protocol.CAN_ID_BOOTLOADER_SIGNATURE_CHUNK and krc.is_chunk(data):
            record = self._assembler.feed(data)
            if record is not None:
                self.key_rotation, self.last_rotation_result = krc.decide(state, record, int(self.uptime_s))
            return []
        return None

    def _bootloader_frames(self, can_id: int, data: bytes) -> list[Frame]:
        rotation = self._rotation_frames(can_id, data)
        if rotation is not None:
            return rotation
        self._bootloader.send_frame(can_id, data)
        out: list[Frame] = []
        while True:
            frame = self._bootloader.read_frame()
            if frame is None:
                break
            out.append(frame)
            if self.key_rotation is not None and frame[0] == protocol.CAN_ID_VERSION_RESPONSE:
                # A bootloader with trusted keys announces them right after its 0x7F9 answer (the current one first).
                out.extend((protocol.CAN_ID_BOOTLOADER_KEY_ID, kid) for kid in kr.announce(self.key_rotation.rotation, self.rotation_now())[0])
        return out

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

    def __init__(self, board: VirtualBoard, acknowledge_transmit: bool = True, bus_bitrate_code: str | None = None) -> None:
        self.board = board
        self.acknowledge_transmit = acknowledge_transmit
        # The SLCAN code of the speed the bus runs at; None means the bus follows whatever the adapter is set to (the older behaviour). With a code, a board and an
        # adapter at different speeds do not hear each other: what the adapter sends reaches nobody and nothing comes back, as on a real bus of another speed.
        self.bus_bitrate_code = bus_bitrate_code
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
            if self.bus_bitrate_code is not None and self.bitrate_code != self.bus_bitrate_code:
                return b"z\r" if self.acknowledge_transmit else b""          # sent into a bus that is at another speed: nobody hears it
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
                out += b"\a\r"  # a line that is not text is a bell like any other refusal, with its terminator
                continue
            reply = self.command(line)
            if reply and not reply.endswith(b"\r"):
                reply += b"\r"  # a bell is followed by the terminator like every other reply
            out += reply
        if len(self._pending) > 4096:
            self._pending = b""
        return out


class FirmwareBoardError(Exception):
    """The firmware's own virtual board could not be built (no URTC checkout there, no host C compiler, WSL missing on Windows)."""


FIRMWARE_BOARD_BUILDER = ("tools", "fuzz_virtual_board.py")
FIRMWARE_BOOTLOADER_BUILDER = ("tools", "bootloader_twin.py")
FIRMWARE_BOARD_MARK = "VIRTUAL_BOARD_COMMAND="


def firmware_board_command(repo: Path, tool: int = 0, features: int = 0, build_dir: Path | None = None, bootloader: bool = False) -> list[str]:
    """Builds the firmware's own virtual board and returns the command that runs it, ready for ``--exec``.

    ``repo`` is a checkout of the URTC repository (its ``tests/virtual_board.c`` is the real receive path of the firmware compiled for the
    host, with the address and undefined-behaviour sanitizers); the builder it carries compiles it with the host gcc, or inside WSL on Windows
    because the fake flash needs a 64-bit Linux host. ``tool`` is the tool profile the board starts with (0 to 24) and ``features`` the
    mask of the optional features that are on. With ``bootloader=True`` it is the twin of the bootloader that is built instead (``tests/virtual_bootloader.c``:
    the bootloader of the master as it is, with its window, its main loop and its flash), which takes no arguments, so ``tool`` and ``features`` do not apply."""
    script = Path(repo).joinpath(*(FIRMWARE_BOOTLOADER_BUILDER if bootloader else FIRMWARE_BOARD_BUILDER))
    if not script.is_file():
        raise FirmwareBoardError(f"{script} not found: give the folder of the URTC repository")
    if not 0 <= tool <= 24:
        raise FirmwareBoardError("the tool profile must be between 0 and 24")
    refusal = local_build_refusal()
    if refusal is not None:
        raise FirmwareBoardError(refusal)
    folder = build_dir or Path(tempfile.mkdtemp(prefix="urtc_virtual_board_"))
    try:
        done = subprocess.run([sys.executable, str(script), "--build-only", "--build-dir", str(folder)], capture_output=True, text=True, timeout=600)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise FirmwareBoardError(f"the build of the virtual board did not run: {exc}") from exc
    if done.returncode == 2:
        raise FirmwareBoardError("no host C compiler (install gcc, or WSL on Windows)")
    if done.returncode != 0:
        raise FirmwareBoardError("the virtual board of the firmware did not build: " + (done.stdout + done.stderr).strip()[-400:])
    for line in reversed(done.stdout.splitlines()):
        if line.startswith(FIRMWARE_BOARD_MARK):
            prefix = json.loads(line[len(FIRMWARE_BOARD_MARK):])
            return list(prefix) if bootloader else [*prefix, str(tool), str(features)]
    raise FirmwareBoardError("the builder did not say how to run the virtual board")


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

    TICK_SECONDS = 0.05  # how often real time is handed to the board (the heater loop of the soldering iron)

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
        self._adapters: dict[socket.socket, tuple[SlcanAdapter, Callable[[bytes], None]]] = {}
        self._ticker: threading.Thread | None = None

    @property
    def url(self) -> str:
        """What to type where a serial port is asked for."""
        return f"socket://{self.host}:{self.port}"

    def start(self) -> "VirtualBoardServer":
        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()
        if not self.command:
            self._ticker = threading.Thread(target=self._tick_loop, daemon=True)
            self._ticker.start()
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
        if self._ticker is not None:
            self._ticker.join(timeout=2)

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

    def _tick_loop(self) -> None:
        """Let real time pass for the board: the telemetry of a running heater loop goes to every client whose channel is open."""
        last = time.monotonic()
        while not self._stop.wait(self.TICK_SECONDS):
            now = time.monotonic()
            with self._lock:
                frames = self.board.advance(now - last)
                targets = [(adapter, send) for adapter, send in self._adapters.values() if adapter.state in ("open", "listen")]
            last = now
            if frames:
                data = SlcanAdapter._lines(frames)
                for _adapter, send in targets:
                    send(data)

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
            self._adapters[client] = (backend, send)
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
            self._adapters.pop(client, None)
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
    parser.add_argument("--firmware-repo", default=None, metavar="DIR",
                        help="build the firmware's own virtual board from this checkout of the URTC repository (inside WSL on Windows) and bridge to it, "
                             "as --exec would; --tool and --features choose the profile and the optional features it starts with")
    parser.add_argument("--features", type=lambda text: int(text, 0), default=0, help="with --firmware-repo: the mask of optional features that are on (default 0)")
    parser.add_argument("--firmware-bootloader", action="store_true",
                        help="with --firmware-repo: bridge to the twin of the bootloader (the real C of the master's bootloader on the host) instead of the virtual board of the application")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    work: Path | None = None
    try:
        major, minor = (int(part) for part in args.board_version.split("."))
        board = VirtualBoard(version=(major, minor), patch=args.patch, tool_id=args.tool, bootloader=args.bootloader)
        if args.firmware_repo and args.command:
            raise ValueError("--firmware-repo and --exec are two ways to say the same thing: give one")
        command = shlex.split(args.command) if args.command else None
        if args.firmware_repo:
            work = Path(tempfile.mkdtemp(prefix="urtc_virtual_board_"))
            command = firmware_board_command(Path(args.firmware_repo), args.tool, args.features, work, bootloader=args.firmware_bootloader)
        elif args.firmware_bootloader:
            raise ValueError("--firmware-bootloader needs --firmware-repo")
        server = VirtualBoardServer(board, args.host, args.port, command)
    except (ValueError, OSError, FrameError, FirmwareBoardError) as exc:
        if work is not None:
            shutil.rmtree(work, ignore_errors=True)
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
        if work is not None:
            shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
