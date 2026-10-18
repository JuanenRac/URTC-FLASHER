# =============================================================================
# URTC-COMMON - src/urtc_common/slcan.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The SLCAN subset this protocol relies on: standard ``t`` data frames, strict hexadecimal, one frame per line.

Strictness is the point. ``int(text, 16)`` alone accepts a sign, a ``0x`` prefix and underscores, which
turned line noise into plausible frames in the copies this module replaces; here every character after
the leading ``t`` must be a real hexadecimal digit, a ``T`` (29-bit) line is never handed on as a
standard frame, and a line whose length is not exactly what its own DLC implies is dropped.
"""
from __future__ import annotations

from .framing import CanFrame, FrameError, check_frame
from . import protocol

HEX_DIGITS = frozenset("0123456789abcdefABCDEF")
TERMINATOR = b"\r"
RX_BUFFER_LIMIT = protocol.SLCAN_RX_BUFFER_LIMIT


def encode_line(can_id: int, data: bytes = b"") -> str:
    """The line that transmits a frame: ``t`` + 3 hex digits + DLC + data, upper case, without the terminator."""
    data = bytes(data)
    check_frame(can_id, data)
    return f"t{can_id:03X}{len(data):01X}" + "".join(f"{b:02X}" for b in data)


def decode_line(line: str) -> CanFrame | None:
    """The frame in one received line, or None when the line holds no valid standard data frame.

    A status character (``z``, ``Z``, BELL) that arrived without a terminator of its own may precede the
    frame in the same buffered line, so the frame starts at the first ``t`` or ``T`` in the line.
    """
    line = line.strip()
    start = -1
    for index, char in enumerate(line):
        if char in ("t", "T"):
            start = index
            break
    if start == -1:
        return None
    line = line[start:]
    if line[0] == "T":
        return None
    if any(char not in HEX_DIGITS for char in line[1:]):
        return None
    if len(line) < 5:
        return None
    can_id = int(line[1:4], 16)
    dlc = int(line[4:5], 16)
    if dlc > protocol.DLC_MAX:
        return None
    if len(line) != 5 + dlc * 2:
        return None
    try:
        return CanFrame(can_id, bytes(int(line[5 + i * 2:7 + i * 2], 16) for i in range(dlc)))
    except FrameError:
        return None


class LineReader:
    """Turns the bytes of a serial stream into frames, keeping the unfinished line between calls.

    A real USB-serial link can split one line over several reads; the partial line stays in the buffer
    until its terminator arrives. A buffer that grows past the limit with no terminator is noise (or the
    wrong baud rate) and is discarded, so it cannot grow without bound.
    """

    def __init__(self, limit: int = RX_BUFFER_LIMIT) -> None:
        self.limit = limit
        self.buffer = b""

    def clear(self) -> None:
        self.buffer = b""

    def has_line(self) -> bool:
        return TERMINATOR in self.buffer

    def feed(self, chunk: bytes) -> None:
        self.buffer += chunk
        if TERMINATOR not in self.buffer and len(self.buffer) > self.limit:
            self.buffer = b""

    def next_frame(self) -> CanFrame | None:
        """The next frame of the complete lines in the buffer, skipping lines that hold none; None when out of lines."""
        while TERMINATOR in self.buffer:
            raw, self.buffer = self.buffer.split(TERMINATOR, 1)
            try:
                text = raw.decode("ascii", errors="strict")
            except UnicodeDecodeError:
                continue
            frame = decode_line(text)
            if frame is not None:
                return frame
        return None

    def frames(self, chunk: bytes) -> list[CanFrame]:
        """Feed bytes and return every frame they completed."""
        self.feed(chunk)
        out = []
        while True:
            frame = self.next_frame()
            if frame is None:
                return out
            out.append(frame)
