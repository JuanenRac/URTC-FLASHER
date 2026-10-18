# =============================================================================
# URTC-COMMON - src/urtc_common/transports.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""CAN transports with one interface: SLCAN (serial), SocketCAN (Linux), python-can and a simulated board.

Extracted from the two copies that the flasher and the tester kept (they had diverged; each had fixes
the other lacked) and merged so that every fix applies everywhere:

* SLCAN and SocketCAN serialise their writes with a lock, so two threads cannot interleave the bytes of
  two frames; a failed serial write or read is a typed error, not a raw serial exception;
* SLCAN clears its receive buffer when the channel is opened, so a stale half-line never reaches the
  first read; its reader skips status characters and reads the frame from the first ``t``;
* SocketCAN closes its socket when the bind fails, retries a full kernel transmit queue (ENOBUFS) a few
  times before giving up, discards error, extended and remote frames, and logs a read error instead of
  hiding it;
* a channel opened in listen-only mode refuses to transmit, on every transport that supports it.

Every optional dependency (pyserial, python-can, a Linux socket) is imported or injected only when a
transport that needs it is created, so importing this module never needs any of them, and the tests
run with fakes.
"""
from __future__ import annotations

import errno
import os
import socket as _socket
import struct
import threading
import time
from typing import Callable, Iterable, Protocol

from . import protocol
from .framing import CanFrame, FrameError, check_frame
from .slcan import LineReader, encode_line

Frame = tuple[int, bytes]


class TransportError(Exception):
    """Base of every transport error, so a caller can catch any of them."""


class SLCANError(TransportError):
    pass


class SocketCANError(TransportError):
    pass


class PythonCANError(TransportError):
    pass


class CanTransport(Protocol):
    """What the tools need from a transport, whichever one is underneath."""

    def open_channel(self, bitrate_code: str | None = ..., listen_only: bool = ...) -> None: ...

    def close_channel(self) -> None: ...

    def close(self) -> None: ...

    def send_frame(self, can_id: int, data: bytes) -> None: ...

    def read_frame(self, timeout: float = ...) -> Frame | None: ...


MESSAGES = {
    "WARN_NO_CARRIER": "interface '{interface}' has no carrier (bus-off, down or unplugged); nothing will get through until it is brought up again",
    "WARN_SOCKETCAN_READ_ERROR": "read error on '{interface}': {e}",
    "WARN_SOCKETCAN_LISTEN_ONLY_SOFT": "'{interface}' cannot be opened listen-only at kernel level from here; this connection will not transmit, but the controller may still acknowledge frames",
}


def _noop_log(message: str) -> None:
    return None


def _checked(error: type[TransportError], can_id: int, data: bytes) -> bytes:
    data = bytes(data)
    try:
        check_frame(can_id, data)
    except FrameError as exc:
        raise error(str(exc)) from exc
    return data


# =============================================================================
# SLCAN
# =============================================================================
class SLCAN:
    """The adapter's virtual COM port, speaking the SLCAN ASCII protocol.

    The OS-level read timeout is fixed once at connection and never changed: a caller's "wait up to N
    seconds" is a software deadline, because reassigning a serial port's timeout reaches down to the OS
    and has been reported to lose bytes on some loaded USB-serial drivers.
    """

    _OS_READ_TIMEOUT = 0.02

    def __init__(self, port: str, baud: int = 115200, log: Callable[[str], None] | None = None, serial_module=None,
                 settle_seconds: float = 0.2) -> None:
        if serial_module is None:
            try:
                import serial as serial_module  # type: ignore[no-redef]
            except ImportError as exc:
                raise SLCANError("pyserial isn't installed, so serial/SLCAN connections aren't available. Install it with: pip install pyserial") from exc
        self.log = log or _noop_log
        self._serial_exception = getattr(serial_module, "SerialException", OSError)
        self.ser = serial_module.Serial(port, baudrate=baud, timeout=self._OS_READ_TIMEOUT)
        self._reader = LineReader()
        # Guards the write itself: send_frame can be called from a button, a keep-alive timer and a worker thread at once.
        self._write_lock = threading.Lock()
        self.listen_only = False
        time.sleep(settle_seconds)
        self.ser.reset_input_buffer()

    def _send_raw(self, command: str) -> None:
        with self._write_lock:
            try:
                self.ser.write((command + "\r").encode("ascii"))
            except self._serial_exception as exc:
                raise SLCANError(f"serial write failed (adapter disconnected?): {exc}") from exc

    def open_channel(self, bitrate_code: str | None = protocol.SLCAN_BITRATE_DEFAULT_CODE, listen_only: bool = False) -> None:
        """Close first (an adapter rejects O when it is already open), set the bitrate, open (L = receive only, never even acknowledge)."""
        bitrate_code = protocol.SLCAN_BITRATE_DEFAULT_CODE if bitrate_code is None else bitrate_code
        self._send_raw("C")
        time.sleep(0.05)
        self.ser.reset_input_buffer()
        self._reader.clear()
        self._send_raw("S" + bitrate_code)
        time.sleep(0.05)
        self._send_raw("L" if listen_only else "O")
        time.sleep(0.1)
        self.ser.reset_input_buffer()
        self._reader.clear()
        self.listen_only = listen_only

    def close_channel(self) -> None:
        try:
            self._send_raw("C")
        except Exception:
            pass

    def close(self) -> None:
        self.close_channel()
        try:
            self.ser.close()
        except Exception:
            pass

    def send_frame(self, can_id: int, data: bytes = b"") -> None:
        if self.listen_only:
            raise SLCANError("Cannot transmit - channel is open in listen-only mode.")
        data = _checked(SLCANError, can_id, data)
        self._send_raw(encode_line(can_id, data))

    def read_frame(self, timeout: float = 0.05) -> Frame | None:
        """(identifier, payload) or None when nothing arrived within ``timeout`` seconds."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not self._reader.has_line():
                try:
                    waiting = self.ser.in_waiting
                    chunk = self.ser.read(waiting if waiting > 0 else 1)
                except self._serial_exception as exc:
                    raise SLCANError(f"serial read failed (adapter disconnected?): {exc}") from exc
                if not chunk:
                    continue
                self._reader.feed(chunk)
                continue
            frame = self._reader.next_frame()
            if frame is not None:
                return frame.id, frame.data
        return None


# =============================================================================
# SocketCAN
# =============================================================================
def list_socketcan_interfaces(sysfs_root: str = "/sys/class/net") -> list[str]:
    """CAN-type interfaces (ARPHRD_CAN is 280) from a directory listing: no subprocess, no dependency."""
    interfaces: list[str] = []
    if not os.path.isdir(sysfs_root):
        return interfaces
    for name in sorted(os.listdir(sysfs_root)):
        try:
            with open(os.path.join(sysfs_root, name, "type")) as handle:
                if handle.read().strip() == "280":
                    interfaces.append(name)
        except OSError:
            continue
    return interfaces


class SocketCAN:
    """A Linux kernel CAN interface through a raw AF_CAN socket.

    The bitrate is a property of the kernel interface (brought up beforehand with ``ip link``), not
    something this class sets: by the time the constructor runs the interface must already be up.
    """

    _FRAME_FMT = "=IB3x8s"
    _FRAME_SIZE = struct.calcsize(_FRAME_FMT)
    _ERROR_FLAGS = 0x80000000 | 0x40000000 | 0x20000000  # extended, remote request, kernel error frame
    SYSFS_NET = "/sys/class/net"

    @classmethod
    def read_interface_stats(cls, interface: str) -> dict | None:
        """Rx/tx counters and error/drop counts of the interface from sysfs, or None when not readable."""
        base = f"{cls.SYSFS_NET}/{interface}/statistics"
        if not os.path.isdir(base):
            return None
        stats = {}
        for name in ("rx_packets", "tx_packets", "rx_errors", "tx_errors", "rx_dropped", "tx_dropped", "collisions"):
            try:
                with open(os.path.join(base, name)) as handle:
                    stats[name] = int(handle.read().strip())
            except (OSError, ValueError):
                return None
        return stats

    @classmethod
    def check_carrier(cls, interface: str) -> bool | None:
        """True when up, False when there is no carrier (bus-off or down), None when it cannot be read."""
        try:
            with open(f"{cls.SYSFS_NET}/{interface}/carrier") as handle:
                return handle.read().strip() == "1"
        except OSError:
            return None

    def __init__(self, interface: str, log: Callable[[str], None] | None = None, socket_module=None,
                 translate: Callable[..., str] | None = None) -> None:
        self.log = log or _noop_log
        self.interface = interface
        # translate(key, **params) lets a tool with its own language files say the warnings in its language;
        # without it the English text of MESSAGES is used.
        self._translate = translate
        self._socket_module = socket_module or _socket
        self._write_lock = threading.Lock()
        self.listen_only = False
        if self.check_carrier(interface) is False:
            self.log(self._say("WARN_NO_CARRIER", interface=interface))
        sock = None
        try:
            sock = self._socket_module.socket(self._socket_module.AF_CAN, self._socket_module.SOCK_RAW, self._socket_module.CAN_RAW)
            sock.bind((interface,))
        except (OSError, AttributeError) as exc:
            if sock is not None:
                try:
                    sock.close()
                except Exception:
                    pass
            raise SocketCANError(
                f"couldn't open '{interface}': {exc}. Check it exists and is up - 'ip link show {interface}' - and that your user can access it "
                f"(bringing the interface up in the first place usually needs sudo)."
            ) from exc
        self.sock = sock
        self.sock.settimeout(0.05)
        self._last_timeout = 0.05

    def _say(self, key: str, **params) -> str:
        if self._translate is not None:
            return self._translate(key, **params)
        return MESSAGES[key].format(**params)

    def open_channel(self, bitrate_code: str | None = None, listen_only: bool = False) -> None:
        self.listen_only = listen_only
        if listen_only:
            self.log(self._say("WARN_SOCKETCAN_LISTEN_ONLY_SOFT", interface=self.interface))

    def close_channel(self) -> None:
        return None

    def close(self) -> None:
        try:
            self.sock.close()
        except Exception:
            pass

    def send_frame(self, can_id: int, data: bytes = b"") -> None:
        if self.listen_only:
            raise SocketCANError("Cannot transmit - this connection was opened in (application-level) listen-only mode.")
        data = _checked(SocketCANError, can_id, data)
        frame = struct.pack(self._FRAME_FMT, can_id, len(data), data + bytes(8 - len(data)))
        # ENOBUFS means the kernel's transmit queue is momentarily full (a burst faster than the controller can
        # put on the wire): normally gone within milliseconds, so retry a few times; any other error fails at once.
        last_error: OSError | None = None
        for attempt in range(5):
            if attempt:
                time.sleep(0.005 * attempt)
            try:
                with self._write_lock:
                    self.sock.send(frame)
                return
            except OSError as exc:
                last_error = exc
                if exc.errno != errno.ENOBUFS:
                    raise SocketCANError(f"send failed on '{self.interface}': {exc}") from exc
        raise SocketCANError(
            f"send failed on '{self.interface}': kernel TX queue stayed full (ENOBUFS) after 5 retries - {last_error}. "
            f"The bus is likely severely congested or stuck (check termination and wiring)."
        )

    def read_frame(self, timeout: float = 0.05) -> Frame | None:
        if timeout != self._last_timeout:
            self.sock.settimeout(timeout)
            self._last_timeout = timeout
        try:
            raw = self.sock.recv(self._FRAME_SIZE)
        except TimeoutError:  # socket.timeout is this class
            return None
        except OSError as exc:
            # A timeout is the only case that means "quiet". Anything else (interface removed, taken down, socket
            # closed) is logged, then a short pause so a dead socket cannot turn the caller's loop into a busy spin.
            self.log(self._say("WARN_SOCKETCAN_READ_ERROR", interface=self.interface, e=exc))
            time.sleep(0.1)
            return None
        try:
            can_id_raw, dlc, data = struct.unpack(self._FRAME_FMT, raw)
        except struct.error:
            return None
        # Flag bits are checked BEFORE masking to 11 bits: an error frame's low bits could otherwise look like a real answer.
        if can_id_raw & self._ERROR_FLAGS:
            return None
        return can_id_raw & protocol.STANDARD_ID_MAX, data[:min(dlc, protocol.DLC_MAX)]


# =============================================================================
# python-can
# =============================================================================
class PythonCAN:
    """Optional transport over the python-can package (PCAN, Kvaser, gs_usb, SocketCAN ...).

    ``spec`` is ``<interface>:<channel>``, for example ``pcan:PCAN_USBBUS1``, ``kvaser:0`` or ``socketcan:can0``.
    The package is imported only when the channel is opened. The bus runs at a fixed 500 kbit/s.
    """

    def __init__(self, spec: str, log: Callable[[str], None] | None = None, bitrate: int = protocol.BITRATE, can_module=None) -> None:
        self.log = log or _noop_log
        self.spec = spec
        self.bitrate = bitrate
        self._can = can_module
        self._bus = None
        self.listen_only = False

    def _module(self):
        if self._can is None:
            try:
                import can
            except ImportError as exc:
                raise PythonCANError("python-can is not installed (pip install python-can)") from exc
            self._can = can
        return self._can

    def open_channel(self, bitrate_code: str | None = None, listen_only: bool = False) -> None:
        can = self._module()
        interface, separator, channel = self.spec.partition(":")
        if not interface or not separator or not channel:
            raise PythonCANError(f"expected <interface>:<channel> (for example pcan:PCAN_USBBUS1), got {self.spec!r}")
        try:
            self._bus = can.Bus(interface=interface, channel=int(channel) if channel.isdigit() else channel, bitrate=self.bitrate)
        except Exception as exc:
            raise PythonCANError(f"cannot open {self.spec}: {exc}") from exc
        self.listen_only = listen_only

    def close_channel(self) -> None:
        if self._bus is not None:
            try:
                self._bus.shutdown()
            finally:
                self._bus = None

    def close(self) -> None:
        self.close_channel()

    def send_frame(self, can_id: int, data: bytes = b"") -> None:
        if self._bus is None:
            raise PythonCANError("the channel is not open")
        if self.listen_only:
            raise PythonCANError("Cannot transmit - this connection was opened in listen-only mode.")
        data = _checked(PythonCANError, can_id, data)
        try:
            self._bus.send(self._module().Message(arbitration_id=can_id, data=data, is_extended_id=False))
        except Exception as exc:
            raise PythonCANError(f"send failed: {exc}") from exc

    def read_frame(self, timeout: float = 0.05) -> Frame | None:
        if self._bus is None:
            raise PythonCANError("the channel is not open")
        message = self._bus.recv(timeout)
        if message is None or message.is_extended_id or message.is_remote_frame or message.is_error_frame:
            return None
        return message.arbitration_id, bytes(message.data)


# =============================================================================
# simulated board
# =============================================================================
class MockCAN:
    """A simulated board with the same interface as the real transports: nothing to open, answers in memory.

    It plays back a plausible bootloader exchange (version query, update with page acknowledgements, read-back,
    the slave version answer) so the logic of a tool can be tested against a predictable peer. It is a second
    reading of the prose by one author, not a substitute for the bootloader: a defect that both the simulator and
    the tool share stays invisible to it.

    ``simulate_failure``: a VERIFY_FAIL_REASON value, to make the update fail verification with that reason.
    ``installed_patch``: 0-127 or PATCH_UNKNOWN to make the board also send 0x7E9; ``accepts_patch`` sets its flag.
    ``slave_version``: a dict with ``version`` (major, minor), optional ``patch``, ``bootloader`` (major) and
    ``patch_extension``; without it the slave stays silent. The last end-of-update payloads are kept in
    ``end_update_payload`` and ``slave_end_update_payload``.
    """

    def __init__(self, simulate_failure: int | None = None, log: Callable[[str], None] | None = None,
                 installed_version: tuple[int, int] = (0, 2), installed_image: bytes = b"", installed_patch: int | None = None,
                 accepts_patch: bool = False, slave_version: dict | None = None, page_size: int = protocol.FLASH_PAGE_SIZE,
                 delay: float = 0.005) -> None:
        self.log = log or _noop_log
        self.simulate_failure = simulate_failure
        self.installed_version = installed_version
        self.installed_image = bytes(installed_image)
        self.installed_patch = installed_patch
        self.accepts_patch = accepts_patch
        self.slave_version = slave_version
        self.page_size = page_size
        self.delay = delay
        self.end_update_payload: bytes | None = None
        self.slave_end_update_payload: bytes | None = None
        self.sent: list[Frame] = []
        self._readback_sent = 0
        self._queue: list[Frame] = []
        self._update_total_size = 0
        self._update_bytes_received = 0
        self._next_page_index = 0

    def open_channel(self, bitrate_code: str | None = None, listen_only: bool = False) -> None:
        return None  # nothing to open

    def close_channel(self) -> None:
        return None

    def close(self) -> None:
        return None

    def send_frame(self, can_id: int, data: bytes = b"") -> None:
        data = _checked(SLCANError, can_id, data)
        self.sent.append((can_id, data))
        if can_id == protocol.CAN_ID_QUERY_VERSION:
            self._queue.append((protocol.CAN_ID_VERSION_RESPONSE, bytes([0x01]) + struct.pack(">I", protocol.HARDWARE_ID_MAIN)
                                + struct.pack(">H", self.installed_version[0]) + bytes([self.installed_version[1]])))
            self._queue.append((protocol.CAN_ID_BOOTLOADER_VERSION_RESPONSE, bytes([1, 0, 1])))
            if self.installed_patch is not None:
                self._queue.append((protocol.CAN_ID_VERSION_PATCH_RESPONSE,
                                    bytes([0x01, self.installed_patch, protocol.PATCH_FLAG_ACCEPTS_IN_END_UPDATE if self.accepts_patch else 0x00])))
        elif can_id == protocol.CAN_ID_SLAVE_VERSION_RESP_1 and self.slave_version is not None:
            info = self.slave_version
            major, minor = info.get("version", (0, 1))
            self._queue.append((protocol.CAN_ID_SLAVE_VERSION_RESP_1,
                                bytes([0x01]) + struct.pack(">I", 0x0303CC02) + struct.pack(">H", major) + bytes([(minor >> 8) & 0xFF])))
            tail = bytes([minor & 0xFF, info.get("bootloader", 0)])
            if info.get("patch_extension"):
                patch = info.get("patch")
                tail += bytes([protocol.PATCH_UNKNOWN if patch is None else patch, 0, 0])
            self._queue.append((protocol.CAN_ID_SLAVE_VERSION_RESP_2, tail))
        elif can_id == protocol.CAN_ID_SLAVE_END_UPDATE:
            self.slave_end_update_payload = data
        elif can_id == protocol.CAN_ID_READBACK:
            self._readback_sent = 0
            self._queue.append((protocol.CAN_ID_READBACK, struct.pack(">I", len(self.installed_image))))
            self._queue_readback_page()
        elif can_id == protocol.CAN_ID_READBACK_PAGE_ACK:
            self._queue_readback_page()
        elif can_id == protocol.CAN_ID_START_UPDATE:
            self._update_total_size = struct.unpack(">I", data[0:4])[0]
            self._update_bytes_received = 0
            self._next_page_index = 0
            self._queue.append((protocol.CAN_ID_STATUS, bytes([protocol.STATUS_ERASING])))
            self._queue.append((protocol.CAN_ID_STATUS, bytes([protocol.STATUS_RECEIVING])))
        elif can_id == protocol.CAN_ID_HMAC_CHUNK:
            pass  # no answer, as the real bootloader
        elif can_id == protocol.CAN_ID_DATA:
            self._update_bytes_received += len(data)
            # Like the real bootloader: a page is acknowledged when its buffer is full; the last, partial page waits for the end of the update.
            while self._update_bytes_received >= (self._next_page_index + 1) * self.page_size:
                self._queue.append((protocol.CAN_ID_PAGE_ACK, struct.pack(">I", self._next_page_index)))
                self._next_page_index += 1
        elif can_id == protocol.CAN_ID_END_UPDATE:
            self.end_update_payload = data
            if self._update_bytes_received > self._next_page_index * self.page_size:
                self._queue.append((protocol.CAN_ID_PAGE_ACK, struct.pack(">I", self._next_page_index)))
                self._next_page_index += 1
            self._queue.append((protocol.CAN_ID_STATUS, bytes([protocol.STATUS_VERIFYING])))
            if self.simulate_failure is not None:
                self._queue.append((protocol.CAN_ID_STATUS, bytes([protocol.STATUS_VERIFY_FAIL, self.simulate_failure])))
            else:
                self._queue.append((protocol.CAN_ID_STATUS, bytes([protocol.STATUS_VERIFY_OK])))

    def _queue_readback_page(self) -> None:
        page = self.installed_image[self._readback_sent:self._readback_sent + self.page_size]
        for index in range(0, len(page), 8):
            self._queue.append((protocol.CAN_ID_READBACK, page[index:index + 8]))
        self._readback_sent += len(page)

    def read_frame(self, timeout: float = 0.05) -> Frame | None:
        if self._queue:
            if self.delay:
                time.sleep(self.delay)
            return self._queue.pop(0)
        return None


# =============================================================================
# bitrate detection
# =============================================================================
def detect_bitrate_listen_only(open_trial: Callable[[str], CanTransport], bitrates: Iterable[tuple[str, str]],
                               listen_seconds: float = 1.0, on_try: Callable[[str], None] | None = None) -> str | None:
    """Find the bus bitrate WITHOUT transmitting anything.

    Transmitting at a wrong bitrate makes every correctly configured node on a running bus see bit and form
    errors, so each candidate is only listened to: ``open_trial(code)`` must return a transport opened in
    listen-only mode, and a bitrate counts as found when one well-formed frame arrives within ``listen_seconds``.
    ``bitrates`` is a list of ``(label, code)`` in the order to try. Returns the label, or None when the bus is
    silent at every bitrate (nothing heard means nothing can be concluded: ask for the bitrate instead of guessing).
    """
    for label, code in bitrates:
        if on_try:
            on_try(label)
        trial = None
        try:
            trial = open_trial(code)
            if trial.read_frame(timeout=listen_seconds) is not None:
                return label
        except (TransportError, OSError):
            pass
        finally:
            if trial is not None:
                try:
                    trial.close()
                except Exception:
                    pass
    return None


def as_frames(frames: Iterable[Frame]) -> list[CanFrame]:
    """Wrap (identifier, payload) pairs in CanFrame objects."""
    return [CanFrame(can_id, data) for can_id, data in frames]
