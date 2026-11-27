# =============================================================================
# URTC-COMMON - src/urtc_common/version_compat.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The version rule for an image without a patch number, kept in a bootloader and changed by a signed command: the host reference of
``firmware_base/urtc_version_compat.h`` (standard library plus ``ed25519``).

The command is 12 chunks on ``0x7EE`` with the indexes 0x40 to 0x4B (84 bytes: target, key id, mode, counter, signature); a frame whose first byte is 0x60 only
asks for the state. The answer is 8 bytes on ``0x7EF`` that begin with 0xC5. A bootloader built without the feature (the default) answers neither.

Signing needs a private seed. This module takes it as an argument and never looks for one.
"""
from __future__ import annotations

import hashlib
import struct
import zlib
from collections.abc import Sequence
from typing import NamedTuple

from . import ed25519

ID_COMMAND = 0x7EE      # host to the bootloader
ID_RESULT = 0x7EF       # bootloader to host
CHUNKS, CHUNK_BYTES, COMMAND_SIZE = 12, 7, 84
CHUNK_BASE, QUERY_INDEX = 0x40, 0x60
DOMAIN = b"URTC-VERCOMPAT-1"
KEY_ID_SIZE = 8
ANSWER_SIZE, ANSWER_MARKER, FLAG_STORED = 8, 0xC5, 0x01
RECORD_SIZE, RECORD_MAGIC = 16, 0x31564356
MODE_NONE, MODE_STRICT, MODE_ACCEPT_PATCHLESS = 0, 1, 2
MODE_NAMES = {"strict": MODE_STRICT, "accept_patchless": MODE_ACCEPT_PATCHLESS}
SLAVE_REG, SLAVE_ACCEPT = 0x0D, 0xA5
OK, BAD_SIGNATURE, UNKNOWN_KEY, REPLAY, BAD_MODE, FLASH_FAILED, DISABLED, BUSY, NOT_FOR_ME = range(9)
STATUS_NAMES = ("ok", "bad_signature", "unknown_key", "replay", "bad_mode", "flash_failed", "disabled", "busy", "not_for_me")


class Answer(NamedTuple):
    status: int
    mode: int       # the mode in force
    stored: bool    # a mode is stored in the board
    counter: int    # the stored counter: the next command needs a higher one


def key_id(public_key: bytes) -> bytes:
    return hashlib.sha512(public_key).digest()[:KEY_ID_SIZE]


def mode_is_valid(mode: int) -> bool:
    return mode in (MODE_STRICT, MODE_ACCEPT_PATCHLESS)


def effective_mode(stored_mode: int, build_unknown_is_zero: bool = True) -> int:
    if mode_is_valid(stored_mode):
        return stored_mode
    return MODE_STRICT if build_unknown_is_zero else MODE_ACCEPT_PATCHLESS


def message(uid: Sequence[int], mode: int, counter: int, kid: bytes) -> bytes:
    if len(uid) != 3 or len(kid) != KEY_ID_SIZE:
        raise ValueError("wrong length in the signed message")
    return DOMAIN + struct.pack(">IIIII", *(w & 0xFFFFFFFF for w in uid), mode & 0xFFFFFFFF, counter & 0xFFFFFFFF) + kid


def make_command(seed: bytes, uid: Sequence[int], current_serial: int, mode: int, counter: int) -> bytes:
    """The 84-byte command that sets ``mode`` on the head with this unique ID, which now answers with ``current_serial``. A seed is a secret."""
    kid = key_id(ed25519.public_key(seed))
    signature = ed25519.sign(seed, message(uid, mode, counter, kid))
    return struct.pack(">I", current_serial & 0xFFFFFFFF) + kid + struct.pack(">II", mode & 0xFFFFFFFF, counter & 0xFFFFFFFF) + signature


def chunks(command: bytes) -> list[bytes]:
    """The 12 CAN frames of a command, to send on ``ID_COMMAND`` in any order."""
    if len(command) != COMMAND_SIZE:
        raise ValueError("a command is 84 bytes")
    return [bytes([CHUNK_BASE + i]) + command[i * CHUNK_BYTES:(i + 1) * CHUNK_BYTES] for i in range(CHUNKS)]


def query_frame() -> bytes:
    """The 8 bytes on ``ID_COMMAND`` that ask for the state without changing it."""
    return bytes([QUERY_INDEX]) + bytes(7)


def answer_frame(status: int, mode: int, stored: bool, counter: int) -> bytes:
    return bytes([ANSWER_MARKER, status, mode, FLAG_STORED if stored else 0]) + struct.pack(">I", counter & 0xFFFFFFFF)


def parse_answer(data: bytes) -> Answer | None:
    """The answer of a bootloader on ``ID_RESULT``, or None for anything else (the 5-byte answer of the serial command included)."""
    if len(data) != ANSWER_SIZE or data[0] != ANSWER_MARKER or data[1] >= len(STATUS_NAMES) or not mode_is_valid(data[2]) or data[3] & ~FLAG_STORED:
        return None
    return Answer(data[1], data[2], bool(data[3] & FLAG_STORED), struct.unpack(">I", data[4:8])[0])


def decide(command: bytes, uid: Sequence[int], current_serial: int, trusted_keys: Sequence[bytes], stored_counter: int, enabled: bool = True,
           busy: bool = False) -> tuple[int, int, int]:
    """(status, mode, counter) as the bootloader decides, in the order of the C code; mode and counter are 0 unless the status is OK."""
    if len(command) != COMMAND_SIZE:
        raise ValueError("a command is 84 bytes")
    if struct.unpack(">I", command[:4])[0] != current_serial:
        return NOT_FOR_ME, 0, 0
    if not enabled:
        return DISABLED, 0, 0
    if busy:
        return BUSY, 0, 0
    mode, counter = struct.unpack(">II", command[12:20])
    kid = command[4:12]
    key = next((k for k in trusted_keys if key_id(k) == kid), None)
    if key is None:
        return UNKNOWN_KEY, 0, 0
    if not ed25519.verify(key, message(uid, mode, counter, kid), command[20:84]):
        return BAD_SIGNATURE, 0, 0
    if not mode_is_valid(mode):
        return BAD_MODE, 0, 0
    if counter <= stored_counter:
        return REPLAY, 0, 0
    return OK, mode, counter


def record_pack(mode: int, counter: int) -> bytes:
    body = struct.pack("<III", RECORD_MAGIC, mode & 0xFFFFFFFF, counter & 0xFFFFFFFF)
    return body + struct.pack("<I", zlib.crc32(body))


def record_read(record: bytes) -> tuple[int, int] | None:
    """(mode, counter) of a complete record, or None for a blank, damaged or unknown one."""
    if len(record) != RECORD_SIZE:
        return None
    magic, mode, counter, crc = struct.unpack("<IIII", record)
    if magic != RECORD_MAGIC or crc != zlib.crc32(record[:12]) or not mode_is_valid(mode):
        return None
    return mode, counter
