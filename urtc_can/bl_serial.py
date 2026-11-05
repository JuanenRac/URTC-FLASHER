# =============================================================================
# URTC-COMMON - src/urtc_common/bl_serial.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The programmed serial number of a bootloader: the host reference of ``firmware_base/urtc_bl_serial.h`` (standard library plus ``ed25519``).

The serial is written by a SIGNED command in the workshop: 12 chunks on ``0x7EE`` (84 bytes: target, key id, serial, counter, signature), answered on ``0x7EF``.
What the signature covers is a 44-byte message that names the unique ID of the head, so a command made for one head fails on another, and a counter that is not
higher than the stored one is a replay. The record that keeps the serial sits in two 16-byte slots (see the header); the newest valid one wins.

Signing needs a private seed. This module takes it as an argument and never looks for one: the workshop tool of the flasher reads it from a file the person names.
"""
from __future__ import annotations

import hashlib
import struct
from collections.abc import Sequence

from . import bl_select, ed25519

ID_CHUNK = 0x7EE        # host to the bootloader: one chunk of the signed command
ID_RESULT = 0x7EF       # bootloader to host: the result
CHUNKS, CHUNK_BYTES, COMMAND_SIZE = 12, 7, 84
DOMAIN = b"URTC-SERIAL-V1\x00\x00"
KEY_ID_SIZE = 8
SLOT_BYTES = 16
OK, BAD_SIGNATURE, UNKNOWN_KEY, REPLAY, BAD_SERIAL, FLASH_FAILED, DISABLED, BUSY, NOT_FOR_ME = range(9)
STATUS_NAMES = ("ok", "bad_signature", "unknown_key", "replay", "bad_serial", "flash_failed", "disabled", "busy", "not_for_me")


def key_id(public_key: bytes) -> bytes:
    return hashlib.sha512(public_key).digest()[:KEY_ID_SIZE]


def message(uid: Sequence[int], serial: int, counter: int, kid: bytes) -> bytes:
    if len(uid) != 3 or len(kid) != KEY_ID_SIZE:
        raise ValueError("wrong length in the signed message")
    return DOMAIN + struct.pack(">IIIII", *(w & 0xFFFFFFFF for w in uid), serial & 0xFFFFFFFF, counter & 0xFFFFFFFF) + kid


def make_command(seed: bytes, uid: Sequence[int], current_serial: int, serial: int, counter: int) -> bytes:
    """The 84-byte command that sets ``serial`` on the head with this unique ID, which now answers with ``current_serial``. A seed is a secret."""
    kid = key_id(ed25519.public_key(seed))
    signature = ed25519.sign(seed, message(uid, serial, counter, kid))
    return struct.pack(">I", current_serial & 0xFFFFFFFF) + kid + struct.pack(">II", serial & 0xFFFFFFFF, counter & 0xFFFFFFFF) + signature


def chunks(command: bytes) -> list[bytes]:
    """The 12 CAN frames (8 bytes: index and 7 data bytes) of a command."""
    if len(command) != COMMAND_SIZE:
        raise ValueError("a command is 84 bytes")
    return [bytes([i]) + command[i * CHUNK_BYTES:(i + 1) * CHUNK_BYTES] for i in range(CHUNKS)]


def result_frame(status: int, serial: int) -> bytes:
    """The answer on 0x7EF: the status and the serial the head answers with now."""
    return bytes([status]) + struct.pack(">I", serial & 0xFFFFFFFF)


def decide(command: bytes, uid: Sequence[int], current_serial: int, trusted_keys: Sequence[bytes], stored_counter: int, enabled: bool = True,
           busy: bool = False) -> tuple[int, int, int]:
    """(status, serial, counter) as the bootloader decides, in the order of the C code."""
    if len(command) != COMMAND_SIZE:
        raise ValueError("a command is 84 bytes")
    if struct.unpack(">I", command[:4])[0] != current_serial:
        return NOT_FOR_ME, 0, 0
    if not enabled:
        return DISABLED, 0, 0
    if busy:
        return BUSY, 0, 0
    new_serial, new_counter = struct.unpack(">II", command[12:20])
    kid = command[4:12]
    key = next((k for k in trusted_keys if key_id(k) == kid), None)
    if key is None:
        return UNKNOWN_KEY, 0, 0
    if not ed25519.verify(key, message(uid, new_serial, new_counter, kid), command[20:84]):
        return BAD_SIGNATURE, 0, 0
    if not bl_select.serial_is_valid(new_serial):
        return BAD_SERIAL, 0, 0
    if new_counter <= stored_counter:
        return REPLAY, 0, 0
    return OK, new_serial, new_counter


def slot_pack(serial: int, counter: int) -> bytes:
    """The 16 bytes of a slot: magic, serial, complement of the serial, counter (little-endian words)."""
    return struct.pack("<IIII", bl_select.SERIAL_RECORD_MAGIC, serial & 0xFFFFFFFF, ~serial & 0xFFFFFFFF, counter & 0xFFFFFFFF)


def slot_value(slot: bytes) -> tuple[int, int] | None:
    """(serial, counter) of a complete slot, or None."""
    words = struct.unpack("<IIII", slot)
    serial = bl_select.serial_from_record((words[0], words[1], words[2]))
    return None if serial is None else (serial, words[3])


def pick(slot_a: bytes, slot_b: bytes) -> tuple[int, int] | None:
    """The newest valid of the two slots (the highest counter; the first on a tie), or None."""
    a, b = slot_value(slot_a), slot_value(slot_b)
    if a and b:
        return b if b[1] > a[1] else a
    return a or b
