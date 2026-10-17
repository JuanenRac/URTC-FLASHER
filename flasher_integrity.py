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

import json
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


def read_sidecar_sha256(path: str) -> str | None:
    """The SHA-256 published next to an image, in `<image>.sha256`.

    Accepts a bare digest or the `sha256sum` layout (`<digest>  <name>`).
    Returns None when there is no such file or it holds no valid digest.
    """
    try:
        with open(path + ".sha256", "r", encoding="utf-8") as stream:
            first = stream.read().split()
    except (OSError, UnicodeDecodeError):
        return None
    if first and _SHA256_RE.match(first[0]):
        return first[0].lower()
    return None


@dataclass(frozen=True)
class Preflight:
    """What to do before flashing an image.

    `blocked` is true when a published digest (`<image>.sha256` or the
    manifest's sha256) does not match, or the image cannot be read. An image
    with no published digest at all (a self-built file) is allowed here, but
    flasher_protocol.py still refuses it unless a signing key is configured.
    """

    blocked: bool
    verified: bool
    sha256: str = ""
    reasons: tuple[str, ...] = field(default_factory=tuple)


def read_manifest_sha256(path: str) -> str | None:
    """The SHA-256 declared in `<image>.manifest.json` (written by the URTC
    build next to every image), or None when absent/unreadable."""
    try:
        with open(path + ".manifest.json", "r", encoding="utf-8") as stream:
            manifest = json.load(stream)
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    value = str(manifest.get("sha256", "") or "").strip().lower() if isinstance(manifest, dict) else ""
    return value if _SHA256_RE.match(value) else None


def manifest_signing_kind(path: str) -> str | None:
    """`signing_key_kind` declared in `<image>.manifest.json` ("dev", "production", ...),
    lower-cased, or None when there is no readable manifest or no such field."""
    try:
        with open(path + ".manifest.json", "r", encoding="utf-8") as stream:
            manifest = json.load(stream)
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    if not isinstance(manifest, dict):
        return None
    kind = str(manifest.get("signing_key_kind", "") or "").strip().lower()
    return kind or None


def preflight_image(path: str) -> Preflight:
    """Every published digest (`<image>.sha256` and the manifest's sha256)
    must match the image, and must agree with each other."""
    sidecar = read_sidecar_sha256(path)
    declared = read_manifest_sha256(path)
    if sidecar and declared and sidecar != declared:
        return Preflight(True, False, "", (f"{path}.sha256 ({sidecar}) and its manifest ({declared}) disagree",))
    expected = sidecar or declared
    if expected is None:
        try:
            sha, _crc = _digests(path)
        except OSError as exc:
            return Preflight(True, False, "", (f"cannot read the image: {exc}",))
        return Preflight(False, False, sha)
    result = verify_image(path, expected)
    return Preflight(not result.ok, result.ok, result.sha256, result.reasons)
