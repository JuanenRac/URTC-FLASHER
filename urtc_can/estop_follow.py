"""How a tool head follows the emergency stop frame of the stack, written down apart from the firmware.

The frame on the identifier 0x001 is defined by the stack that carries it; this module is the part a head needs: which frames are a stop, which one
ends it, and when the silence of the master puts a ready head back in its safe state. One rule shapes everything: a stop is never refused. Any
frame on 0x001 that is not a well-formed release or heartbeat is a stop; only the way out is checked.

The head starts latched. A trip, a malformed frame, a heartbeat that says tripped and a bus-off latch it at once. A release moves it to ready only when
it is latched, the master was heard within ``ESTOP_ALIVE_TIMEOUT_MS``, the epoch is the one of the stop it knows, the sequence is newer than the last one
seen, and, after a bus-off, a new heartbeat was heard. A ready head that hears no new heartbeat for ``ESTOP_ALIVE_TIMEOUT_MS`` latches again. The
decisions here are the ones of ``fw_estop_follow.c``, which replays the vectors written by ``tools/make_estop_vectors.py``. Standard library only.
This is not a certified safety function and never replaces a hardware emergency stop.
Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
"""
from __future__ import annotations

from dataclasses import dataclass

from . import protocol

KIND_TRIP = 0x01
KIND_RELEASE = 0x02
KIND_ALIVE = 0x03

ALIVE_OK = 0x00
ALIVE_TRIPPED = 0x01

SOURCE_BRAIN = 0x00
SOURCE_SLOT_FIRST = 0x01
SOURCE_SLOT_LAST = 0x08
SOURCE_CM5 = 0x10

REASON_UNSPECIFIED = 0xFF
REASONS = frozenset(range(0x01, 0x09)) | {REASON_UNSPECIFIED}

STATE_LATCHED = 0
STATE_READY = 1

UINT32_MASK = 0xFFFFFFFF


@dataclass(frozen=True)
class Frame:
    kind: int
    detail: int
    source: int
    epoch: int
    seq: int


@dataclass(frozen=True)
class Effect:
    """What the head must do after an event: ``stop_reason`` is an ``ERROR_REASON_*`` code (0 = no stop to apply), ``released`` is true when the head became ready."""

    stop_reason: int = 0
    released: bool = False


def encode(kind: int, detail: int, source: int, epoch: int, seq: int) -> bytes:
    """The eight data bytes: kind, detail, source, epoch, sequence (little endian), then the complement of kind and detail."""
    return bytes([kind, detail, source, epoch, seq & 0xFF, (seq >> 8) & 0xFF, kind ^ 0xFF, detail ^ 0xFF])


def decode(data: bytes) -> Frame | None:
    """The frame when the bytes are well formed, ``None`` when they are not (the head then treats the frame as a stop)."""
    if len(data) != 8:
        return None
    kind, detail, source = data[0], data[1], data[2]
    if data[6] != kind ^ 0xFF or data[7] != detail ^ 0xFF:
        return None
    if kind == KIND_TRIP:
        source_ok = source in (SOURCE_BRAIN, SOURCE_CM5) or SOURCE_SLOT_FIRST <= source <= SOURCE_SLOT_LAST
        if detail not in REASONS or not source_ok:
            return None
    elif kind == KIND_RELEASE:
        if detail != 0x00 or source != SOURCE_BRAIN:
            return None
    elif kind == KIND_ALIVE:
        if detail not in (ALIVE_OK, ALIVE_TRIPPED) or source != SOURCE_BRAIN:
            return None
    else:
        return None
    return Frame(kind, detail, source, data[3], data[4] | (data[5] << 8))


def seq_newer(candidate: int, have_last: bool, last: int) -> bool:
    """True when ``candidate`` is 1..32767 steps ahead of ``last`` in the modular order of 16 bits; always true when there is no last yet."""
    if not have_last:
        return True
    step = (candidate - last) & 0xFFFF
    return 1 <= step <= 0x7FFF


class Node:
    """The state of one head that follows the stop. It starts latched."""

    def __init__(self) -> None:
        self.latched = True
        self.have_epoch = False
        self.epoch = 0
        self.have_seq = False
        self.last_seq = 0
        self.have_alive = False
        self.last_alive_ms = 0
        self.busoff_wait = False

    @property
    def state(self) -> int:
        return STATE_LATCHED if self.latched else STATE_READY

    def _alive(self, now_ms: int) -> bool:
        return self.have_alive and ((now_ms - self.last_alive_ms) & UINT32_MASK) <= protocol.ESTOP_ALIVE_TIMEOUT_MS

    def on_frame(self, now_ms: int, data: bytes) -> Effect:
        """Feed one frame received on 0x001 (any length): a malformed one is a stop."""
        stop = Effect(stop_reason=protocol.ERROR_REASON_ESTOP)
        frame = decode(data)
        if frame is None:
            self.latched = True
            return stop
        if frame.kind == KIND_TRIP:
            self.latched = True
            self.have_epoch, self.epoch = True, frame.epoch
            return stop
        newer = seq_newer(frame.seq, self.have_seq, self.last_seq)
        if frame.kind == KIND_ALIVE:
            if frame.detail == ALIVE_TRIPPED:   # recovers a stop this head never heard
                self.latched = True
                self.have_epoch, self.epoch = True, frame.epoch
                if newer:
                    self.have_seq, self.last_seq = True, frame.seq
                    self.have_alive, self.last_alive_ms = True, now_ms & UINT32_MASK
                return stop
            if newer:   # a frozen or replayed sender does not keep the head alive
                self.have_seq, self.last_seq = True, frame.seq
                self.have_alive, self.last_alive_ms = True, now_ms & UINT32_MASK
                self.busoff_wait = False
            return Effect()
        # A release: only from a latched head that heard a live master (and, after a bus-off, a new heartbeat), for the epoch it knows, with a newer sequence.
        if self.latched and not self.busoff_wait and newer and self.have_epoch and frame.epoch == self.epoch and self._alive(now_ms):
            self.have_seq, self.last_seq = True, frame.seq
            self.latched = False
            return Effect(released=True)
        return Effect()

    def on_bus_off(self) -> Effect:
        """The bus coming back never releases anything, and a release waits for a new heartbeat."""
        self.latched = True
        self.busoff_wait = True
        return Effect(stop_reason=protocol.ERROR_REASON_ESTOP)

    def tick(self, now_ms: int) -> Effect:
        """Call every pass: a ready head that has not heard the master within the timeout is latched again."""
        if not self.latched and not self._alive(now_ms):
            self.latched = True
            return Effect(stop_reason=protocol.ERROR_REASON_ESTOP_SILENCE)
        return Effect()
