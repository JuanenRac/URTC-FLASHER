# =============================================================================
# URTC-COMMON - src/urtc_common/key_rotation_command.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The signed command that starts a rotation of the signing key, with the time of the host.

[FIRMWARE] Host reference and simulator only; nothing is built for a board and no bootloader reads these bytes yet. See ``docs/BOOTLOADER_AUTH.md``.

A bootloader has no clock of its own that survives a reset, so the HOST says when the rotation starts: it signs a small record with the key the bootloader
trusts now (the release key; the bootloader only VERIFIES, it never signs) and sends it. The record (big-endian, 100 bytes)::

    signer key id (8) | new current key id (8) | previous key id (8, zeros: none) | window seconds (4) | host time, seconds (4) | counter (4) | Ed25519 signature (64)

The signature covers ``DOMAIN`` followed by the first 36 bytes. The domain is not the one of image signatures, so a signature made for an image can never
be replayed as a rotation. It travels in 15 chunks of the same frame as the signature record of an image (``0x7EC``), told apart by the top bit of the
index (``0x80`` to ``0x8E``); the last chunk is padded with zeros. The bootloader answers nothing: the host asks the status (``0x7EA`` operation ``05``) and
reads the fingerprints (``0x7ED``).

A bootloader accepts a command only when ALL of this holds (the reason of the first rule that fails is reported, see ``REASONS``):

* the option is on (``allow_rotation_command``; the default is OFF: a bootloader that was never configured to rotate refuses);
* the 15 chunks arrived in order; the signer is the key trusted NOW (never the previous one, never a revoked one) and the signature verifies;
* the counter is higher than the last one accepted and the host time is not earlier than the last one accepted (a replayed or reordered command is refused);
* the new current key is in the trust table and not revoked, differs from the previous one, and the previous one is zeros or the key trusted now;
* the window does not exceed the maximum the bootloader was configured with.

Once accepted, the bootloader keeps ``started_at = host time`` and the offset between that time and its own uptime, so ``now = uptime + offset`` (the same
seconds the decision in ``key_rotation`` uses). Nothing here holds a key: signing needs a seed handed in by the caller (the release machine, or a throwaway test key).
"""
from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass, field, replace

from . import ed25519, key_rotation as kr

DOMAIN = b"URTC-KEY-ROTATE-V1\x00"
RECORD_SIZE = 100
BODY_SIZE = 36
CHUNK_DATA = 7
CHUNK_COUNT = 15
CHUNK_FLAG = 0x80            # the top bit of the index of a chunk marks a rotation command
FRAME_ID = 0x7EC
NO_KEY = bytes(8)
DEFAULT_MAX_WINDOW_S = 7 * 86400

OK = "ok"
REASONS = ("ok", "disabled", "malformed", "unknown_signer", "signer_not_current", "bad_signature", "replayed_counter", "time_backwards", "unknown_new_key",
           "revoked_new_key", "bad_previous", "window_too_long")


class RotationCommandError(ValueError):
    """The record cannot be built or read; the message says why."""


@dataclass(frozen=True)
class Command:
    signer: bytes
    new_current: bytes
    previous: bytes          # NO_KEY: no overlap
    window_s: int
    host_time: int
    counter: int
    signature: bytes


def key_id(public_key: bytes) -> bytes:
    """The fingerprint of a public key: the first 8 bytes of its SHA-512 (the same as ``image_auth.key_id``, repeated so that this module stands alone)."""
    return hashlib.sha512(public_key).digest()[:kr.KEY_ID_SIZE]


def body(signer: bytes, new_current: bytes, previous: bytes, window_s: int, host_time: int, counter: int) -> bytes:
    for name, kid in (("signer", signer), ("new current", new_current), ("previous", previous)):
        if len(kid) != kr.KEY_ID_SIZE:
            raise RotationCommandError(f"the {name} key id is 8 bytes")
    for name, value in (("window", window_s), ("host time", host_time), ("counter", counter)):
        if not 0 <= value <= 0xFFFFFFFF:
            raise RotationCommandError(f"the {name} is a 32-bit number")
    return signer + new_current + previous + struct.pack(">III", window_s, host_time, counter)


def message(record_body: bytes) -> bytes:
    if len(record_body) != BODY_SIZE:
        raise RotationCommandError("the body of the record is 36 bytes")
    return DOMAIN + record_body


def sign(seed: bytes, new_current: bytes, previous: bytes | None, window_s: int, host_time: int, counter: int) -> bytes:
    """The 100-byte record, signed by the key of ``seed`` (the release machine). The signer id is derived from the seed, never typed."""
    signer = key_id(ed25519.public_key(seed))
    record_body = body(signer, new_current, previous if previous is not None else NO_KEY, window_s, host_time, counter)
    return record_body + ed25519.sign(seed, message(record_body))


def parse(record: bytes) -> Command:
    if len(record) != RECORD_SIZE:
        raise RotationCommandError("a rotation command is 100 bytes")
    window_s, host_time, counter = struct.unpack(">III", record[24:36])
    return Command(record[0:8], record[8:16], record[16:24], window_s, host_time, counter, record[36:100])


def to_chunks(record: bytes) -> list[bytes]:
    """The 15 payloads for 0x7EC: ``0x80 | n`` then seven bytes; the last one is padded with zeros."""
    if len(record) != RECORD_SIZE:
        raise RotationCommandError("a rotation command is 100 bytes")
    padded = record + bytes(CHUNK_COUNT * CHUNK_DATA - RECORD_SIZE)
    return [bytes([CHUNK_FLAG | n]) + padded[n * CHUNK_DATA:(n + 1) * CHUNK_DATA] for n in range(CHUNK_COUNT)]


def is_chunk(data: bytes) -> bool:
    return len(data) == 8 and CHUNK_FLAG <= data[0] < CHUNK_FLAG + CHUNK_COUNT


@dataclass(frozen=True)
class Trust:
    """What the bootloader holds to verify: the public keys of its trust table (one or two), by fingerprint."""
    keys: dict[bytes, bytes]


@dataclass(frozen=True)
class State:
    """What a bootloader keeps about the rotation between resets (the metadata page) plus the offset of its clock."""
    rotation: kr.Rotation
    trust: Trust
    last_counter: int = 0
    last_host_time: int = 0
    clock_offset: int = 0
    allow: bool = False
    max_window_s: int = DEFAULT_MAX_WINDOW_S


def now_of(state: State, uptime_s: int) -> int:
    """The time the rotation decision uses: the uptime shifted by the offset the last accepted command set (zero before any command)."""
    return uptime_s + state.clock_offset


def decide(state: State, record: bytes, uptime_s: int) -> tuple[State, str]:
    """``(new state, reason)``; the state is returned unchanged unless the reason is ``ok``."""
    if not state.allow:
        return state, "disabled"
    if len(record) != RECORD_SIZE:
        return state, "malformed"
    cmd = parse(record)
    current = state.rotation.current
    if cmd.signer not in state.trust.keys:
        return state, "unknown_signer"
    if cmd.signer != current or current in state.rotation.revoked:
        return state, "signer_not_current"
    if not ed25519.verify(state.trust.keys[cmd.signer], message(record[:BODY_SIZE]), cmd.signature):
        return state, "bad_signature"
    if cmd.counter <= state.last_counter:
        return state, "replayed_counter"
    if cmd.host_time < state.last_host_time or cmd.host_time == 0:
        return state, "time_backwards"
    if cmd.new_current not in state.trust.keys:
        return state, "unknown_new_key"
    if cmd.new_current in state.rotation.revoked:
        return state, "revoked_new_key"
    if cmd.new_current == cmd.previous or cmd.previous not in (NO_KEY, current):
        return state, "bad_previous"
    if cmd.window_s > state.max_window_s:
        return state, "window_too_long"
    previous = None if cmd.previous == NO_KEY or cmd.new_current == current else cmd.previous
    rotation = replace(state.rotation, current=cmd.new_current, previous=previous, window_s=cmd.window_s if previous else 0, started_at=cmd.host_time)
    return replace(state, rotation=rotation, last_counter=cmd.counter, last_host_time=cmd.host_time, clock_offset=cmd.host_time - uptime_s), "ok"


@dataclass
class Assembler:
    """Collects the chunks of 0x7EC in order. A chunk 0 starts again; an index out of order drops what was collected (the host sends it all again)."""
    parts: list[bytes] = field(default_factory=list)

    def feed(self, data: bytes) -> bytes | None:
        if not is_chunk(data):
            return None
        index = data[0] & ~CHUNK_FLAG & 0xFF
        if index == 0:
            self.parts = [bytes(data[1:])]
        elif index == len(self.parts):
            self.parts.append(bytes(data[1:]))
        else:
            self.parts = []
            return None
        if len(self.parts) < CHUNK_COUNT:
            return None
        record = b"".join(self.parts)[:RECORD_SIZE]
        self.parts = []
        return record
