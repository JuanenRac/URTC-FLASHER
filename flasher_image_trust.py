# =============================================================================
# URTC-FLASHER - flasher_image_trust.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The signature record of an image (`<image>.imgsig`), checked on this computer before anything is sent.

The bootloader of the board verifies the record itself and always decides; this check only saves a transfer that would end in a refusal and gives the reason.
The record is `key id (8) | counter (4, big-endian) | Ed25519 signature (64)` and the signature covers an 88-byte message: `URTC-IMG-SIG-V1` and a zero, the
first 28 bytes of the image header (rebuilt from the hardware, the version in the file name and the image itself), the SHA-256 of the image, the counter and the key id.

PINNED_KEYS is a pinned copy of the public trust table of the bootloaders (the keys a bootloader accepts to sign an application image): the key that signs the
official images, the reserved next key and the public development key of the bench builds. Only public values are written here. A table that has fallen behind
would say "unknown key" for a good image, which is why the setting `imgsig_precheck` is `warn` by default.
"""
from __future__ import annotations

import hashlib
import re
import struct

from urtc_can import ed25519
from urtc_can import image_header as _image_header

PINNED_KEYS = (
    ("release current", "80344f1a557fac5d2426c633342d17ddafd6b2a8bfd35efbe0e7a7acfdcce5f5"),
    ("release next", "ac856598a0ac8e45c5f3c66c597c83ccb6a9c0424a434222de14e59cd27c367b"),
    ("development", "81f29be04dfa58f37458e6182a027d83f12330265d61bd6bfcedb2ba8833b80c"),
)

OK = "ok"
UNKNOWN_KEY = "unknown_key"
BAD_SIGNATURE = "bad_signature"

_DOMAIN = b"URTC-IMG-SIG-V1\x00"
_RECORD_SIZE = 76
_NAME_VERSION = re.compile(r"_v(\d+)\.(\d+)\.(\d+)(?:\.(\d+))?\.(?:bin|hex)$", re.IGNORECASE)


def key_id(public: bytes) -> bytes:
    """The eight bytes that name a public key: the start of its SHA-512."""
    return hashlib.sha512(public).digest()[:8]


def version_from_name(name: str) -> tuple[int, int, int, int] | None:
    """The four components of the version in the name of an image (`URTC_MAIN_FIRMWARE_v0.8.0.1.bin`); the build is 0 when the name has three. None when it has none."""
    found = _NAME_VERSION.search(name)
    if not found:
        return None
    major, minor, patch, build = (int(part or 0) for part in found.groups())
    return major, minor, patch, build


def header28(image: bytes, hardware_id: int, version: tuple[int, int, int, int]) -> bytes:
    """The 28 bytes the record covers: the descriptor of the image, rebuilt from the image, the hardware and the version."""
    return _image_header.make_header(image, hardware_id, version, signed=False)[:28]


def verify_record(record: bytes, image: bytes, hardware_id: int, version: tuple[int, int, int, int]) -> str:
    """`OK`, `UNKNOWN_KEY` (no pinned key has the id of the record) or `BAD_SIGNATURE`. The record must have the 76 bytes."""
    if len(record) != _RECORD_SIZE:
        return BAD_SIGNATURE
    kid, counter = record[:8], record[8:12]
    publics = [bytes.fromhex(hex_key) for _, hex_key in PINNED_KEYS if key_id(bytes.fromhex(hex_key)) == kid]
    if not publics:
        return UNKNOWN_KEY
    message = _DOMAIN + header28(image, hardware_id, version) + hashlib.sha256(image).digest() + counter + kid
    return OK if ed25519.verify(publics[0], message, record[12:]) else BAD_SIGNATURE


def key_name(record: bytes) -> str:
    """The name of the pinned key that has the id of the record ('' when none has)."""
    for name, hex_key in PINNED_KEYS:
        if key_id(bytes.fromhex(hex_key)) == record[:8]:
            return name
    return ""


def counter_of(record: bytes) -> int:
    return int(struct.unpack(">I", record[8:12])[0])
