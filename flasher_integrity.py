# =============================================================================
# URTC-FLASHER - flasher_integrity.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Checks that come before a flash may be reported as done.

A flash is only satisfactory when the image on disk is the one that was
meant to be flashed (its SHA-256, and optionally its CRC-32, match the
values the caller expects) and the board that answered is the board that
was meant to be flashed. Both checks return every reason they fail, and a
missing expectation is never treated as a pass: with nothing to compare
against, the result says so.
"""

from __future__ import annotations

import hashlib
import re
import zlib
from dataclasses import dataclass, field

_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_CRC32_RE = re.compile(r"^(?:0x)?[0-9a-fA-F]{1,8}$")


@dataclass(frozen=True)
class IntegrityResult:
    ok: bool
    reasons: tuple[str, ...] = field(default_factory=tuple)
    sha256: str = ""
    crc32: str = ""


def _digests(path: str) -> tuple[str, int]:
    sha, crc = hashlib.sha256(), 0
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 16), b""):
            sha.update(chunk)
            crc = zlib.crc32(chunk, crc)
    return sha.hexdigest(), crc & 0xFFFFFFFF


def verify_image(path: str, expected_sha256: str | None, expected_crc32: str | None = None) -> IntegrityResult:
    """Compare the file's digests with the expected ones.

    `expected_sha256` is required for a pass: without it there is nothing to
    prove the image is the intended one, and the result says so.
    """
    reasons: list[str] = []
    try:
        sha, crc = _digests(path)
    except OSError as exc:
        return IntegrityResult(False, (f"cannot read the image: {exc}",))
    crc_text = f"0x{crc:08X}"
    if not expected_sha256:
        reasons.append("no expected SHA-256 was given, so the image cannot be shown to be the intended one")
    elif not _SHA256_RE.match(expected_sha256):
        reasons.append("the expected SHA-256 is not a 64-digit hexadecimal value")
    elif sha.lower() != expected_sha256.lower():
        reasons.append(f"SHA-256 mismatch: the file is {sha}, expected {expected_sha256.lower()}")
    if expected_crc32:
        if not _CRC32_RE.match(expected_crc32):
            reasons.append("the expected CRC-32 is not a hexadecimal value")
        elif crc != int(expected_crc32, 16):
            reasons.append(f"CRC-32 mismatch: the file is {crc_text}, expected {expected_crc32}")
    return IntegrityResult(not reasons, tuple(reasons), sha, crc_text)


def verify_target(expected: str | None, reported: str | None) -> IntegrityResult:
    """The board that answered must be the board that was meant to be flashed."""
    if not expected:
        return IntegrityResult(False, ("no expected target was given, so the board cannot be confirmed",))
    if not reported:
        return IntegrityResult(False, ("the board reported no identity",))
    if expected.strip().lower() != reported.strip().lower():
        return IntegrityResult(False, (f"wrong target: expected {expected!r}, the board reported {reported!r}",))
    return IntegrityResult(True)


def may_report_success(image: IntegrityResult, target: IntegrityResult) -> tuple[bool, tuple[str, ...]]:
    """A flash is reported successful only when both checks passed."""
    reasons = image.reasons + target.reasons
    return (image.ok and target.ok), reasons
