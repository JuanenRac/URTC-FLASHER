"""How a tool head follows the emergency stop frame of the stack, written down apart from the firmware.

The frame on the identifier 0x001 is defined by the stack that carries it; this module is the part a head needs: which frames are a stop, which one
ends it, and when the silence of the master puts a ready head back in its safe state. One rule shapes everything: a stop is never refused. Any
frame on 0x001 that is not a well-formed release or heartbeat is a stop; only the way out is checked.

The head starts latched. A trip, a malformed frame, a heartbeat that says tripped and a bus-off latch it at once. A release moves it to ready only when
it is latched, the master was heard within the timeout (``ESTOP_ALIVE_TIMEOUT_MS``, 100 ms unless the head is configured otherwise), the epoch is the one of the stop it knows, the sequence is newer than the last one
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

# The silence of the master after which a ready head latches again is configurable per head. The default is the constant of the specification, the
# limits are hard: a configured value outside them is rejected (the default is used and the status says so), never accepted in silence.
TIMEOUT_DEFAULT_MS = protocol.ESTOP_ALIVE_TIMEOUT_MS
TIMEOUT_MIN_MS = protocol.ESTOP_ALIVE_TIMEOUT_MIN_MS
TIMEOUT_MAX_MS = protocol.ESTOP_ALIVE_TIMEOUT_MAX_MS
CONFIG_KEY = "estop_alive_timeout_ms"   # the key of the head's configuration file (absent or 0 = the default)

TIMEOUT_OK = 0              # the configured value (or the default, when none was set) is the one in use
TIMEOUT_REJECTED = 1        # the configured value was outside the limits: the default is in use (warn)
TIMEOUT_MASTER_DIFFERS = 2  # the master announced another value: the lower of the two is in use (warn)
TIMEOUT_MASTER_REJECTED = 3 # the master announced a value outside the limits: it is ignored, the head's own value is in use (warn)


def resolve_timeout(requested: int | None) -> tuple[int, int]:
    """``(milliseconds, status)`` for a configured value: ``None`` or 0 means not set (the default); a value outside the hard limits is rejected."""
    if requested is None or requested == 0:
        return TIMEOUT_DEFAULT_MS, TIMEOUT_OK
    if isinstance(requested, bool) or not isinstance(requested, int) or not TIMEOUT_MIN_MS <= requested <= TIMEOUT_MAX_MS:
        return TIMEOUT_DEFAULT_MS, TIMEOUT_REJECTED
    return requested, TIMEOUT_OK


def timeout_from_config(config: dict) -> tuple[int, int]:
    """The timeout of a head from its configuration mapping (the key ``estop_alive_timeout_ms``); see ``resolve_timeout``."""
    return resolve_timeout(config.get(CONFIG_KEY))


def effective_timeout(own_ms: int, master_ms: int | None) -> tuple[int, int]:
    """The value a head uses when the master announces its own: the LOWER of the two, never more tolerant than the head's configuration.

    ``master_ms`` of ``None`` or 0 means the master announced nothing. An announced value outside the limits is ignored with ``TIMEOUT_MASTER_REJECTED``.
    """
    if master_ms is None or master_ms == 0:
        return own_ms, TIMEOUT_OK
    if not TIMEOUT_MIN_MS <= master_ms <= TIMEOUT_MAX_MS:
        return own_ms, TIMEOUT_MASTER_REJECTED
    if master_ms == own_ms:
        return own_ms, TIMEOUT_OK
    return min(own_ms, master_ms), TIMEOUT_MASTER_DIFFERS


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

    def __init__(self, alive_timeout_ms: int | None = None) -> None:
        self.own_timeout_ms, self.timeout_status = resolve_timeout(alive_timeout_ms)
        self.alive_timeout_ms = self.own_timeout_ms   # the value in use: never above the one of this head's configuration
        self.latched = True
        self.have_epoch = False
        self.epoch = 0
        self.have_seq = False
        self.last_seq = 0
        self.have_alive = False
        self.last_alive_ms = 0
        self.busoff_wait = False

    def set_master_timeout(self, announced_ms: int | None) -> int:
        """The master announced its timeout: the head uses the lower of the two and returns the status (``TIMEOUT_*``)."""
        self.alive_timeout_ms, status = effective_timeout(self.own_timeout_ms, announced_ms)
        if status != TIMEOUT_OK or self.timeout_status != TIMEOUT_REJECTED:
            self.timeout_status = status
        return self.timeout_status

    @property
    def state(self) -> int:
        return STATE_LATCHED if self.latched else STATE_READY

    def _alive(self, now_ms: int) -> bool:
        return self.have_alive and ((now_ms - self.last_alive_ms) & UINT32_MASK) <= self.alive_timeout_ms

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


# ---------------------------------------------------------------------------------------------------------------------
# The silence of the master on the bus: writing it with 0x1AE (DLC 8) and asking for it with 0x1AF (query byte 3 or 4). The decisions are the ones of
# ``Feat_ParseWrite`` and ``Feat_QueryForm`` of the firmware, which replay the vectors written by ``tools/make_estop_vectors.py``. A frame of the old
# forms (DLC 5 and 6, an empty query or the byte 2) behaves exactly as before.
# ---------------------------------------------------------------------------------------------------------------------
FEATURES_MAGIC = b"FEAT"
FEATURE_MASK_SUPPORTED = 0xFF
FEATURE_EXT_MASK_SUPPORTED = 0x03

QUERY_BASIC = 0            # three-byte answer (an empty query or any byte not listed below)
QUERY_EXTENDED = 1         # six-byte answer (the byte 2)
QUERY_TIMEOUT_IN_FORCE = 2 # eight-byte answer with the silence in force now (the byte 3)
QUERY_TIMEOUT_STORED = 3   # eight-byte answer with the silence stored in the record (the byte 4)

KEEP_STORED_TIMEOUT = None  # the timeout of a write that is not in the eight-byte form: the stored value stays


@dataclass(frozen=True)
class FeaturesWrite:
    """A valid write of 0x1AE: the masks, the silence to store (``None``: keep the stored one) and the length of the frame (5, 6 or 8)."""

    mask: int
    mask_ext: int
    timeout_ms: int | None
    dlc: int


def write_timeout_valid(timeout_ms: int) -> bool:
    """A silence a write may store: 0 (clear it, the default applies) or inside the hard limits. Anything else makes the whole write invalid."""
    return timeout_ms == 0 or TIMEOUT_MIN_MS <= timeout_ms <= TIMEOUT_MAX_MS


def parse_features_write(data: bytes) -> FeaturesWrite | None:
    """The write when the 0x1AE payload is valid, ``None`` when the firmware ignores it (nothing is changed and nothing is answered)."""
    if len(data) not in (5, 6, 8) or data[:4] != FEATURES_MAGIC:
        return None
    ext = data[5] if len(data) >= 6 else 0
    if data[4] & ~FEATURE_MASK_SUPPORTED or ext & ~FEATURE_EXT_MASK_SUPPORTED:
        return None
    timeout: int | None = KEEP_STORED_TIMEOUT
    if len(data) == 8:
        timeout = (data[6] << 8) | data[7]   # big endian, like every 16-bit field of the protocol
        if not write_timeout_valid(timeout):
            return None
    return FeaturesWrite(data[4], ext, timeout, len(data))


def query_form(data: bytes) -> int:
    """Which answer a 0x1AF query gets (``QUERY_*``): only the one-byte queries 2, 3 and 4 ask for more than the three-byte form."""
    if len(data) == 1:
        return {2: QUERY_EXTENDED, 3: QUERY_TIMEOUT_IN_FORCE, 4: QUERY_TIMEOUT_STORED}.get(data[0], QUERY_BASIC)
    return QUERY_BASIC


def encode_timeout_answer(stored: int, running: int, stored_ext: int, running_ext: int, timeout_ms: int) -> bytes:
    """The eight data bytes of the 0x1AF answer with the silence of the master (big endian); the supported masks are those of this reference."""
    return bytes([stored, running, FEATURE_MASK_SUPPORTED, stored_ext, running_ext, FEATURE_EXT_MASK_SUPPORTED, (timeout_ms >> 8) & 0xFF, timeout_ms & 0xFF])


def decode_timeout_answer(data: bytes) -> dict | None:
    """The fields of the eight-byte answer, ``None`` for any other length. ``timeout_ms`` is 0 while ESTOP_FOLLOW does not run (in force) or for the default (stored)."""
    if len(data) != 8:
        return None
    return {"stored": data[0], "running": data[1], "supported": data[2], "stored_ext": data[3], "running_ext": data[4], "supported_ext": data[5],
            "timeout_ms": (data[6] << 8) | data[7]}
