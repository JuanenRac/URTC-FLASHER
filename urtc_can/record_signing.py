# =============================================================================
# URTC-COMMON - src/urtc_common/record_signing.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Sign the records a program writes (a saved session, an update report) with a key that stays on this computer.

The programs already name a log or an image by its SHA-256, which shows that a record and its log belong together.
That does not show who wrote the record, nor that nobody rewrote both. A signature with a key that only this user holds
adds that: whoever has the public key of the user can check that the record was written by a program running with the
user's key and was not changed afterwards.

What it proves, and what it does not:

* it proves the record and the key belong together, and that the record was not edited after it was signed;
* it does not prove who the person behind the key is: the key is made on the first use, there is no authority above it.
  A reader decides to trust a public key (by its key id) the same way he trusts an SSH key.

The key is a 32-byte seed in a text file (hexadecimal), by default ``~/.urtc-keys/records_ed25519.key``, or the file
named by ``URTC_RECORD_KEY_FILE``. It is made the first time a record is signed and is never printed or logged. The
signature is Ed25519 (RFC 8032), standard library only; the browser program makes the same signature with WebCrypto.

The signed message is ``urtc-record/1`` + a line break + the kind + a line break + the payload, where the payload of a
saved session is ``log_file``, ``log_sha256`` and ``log_bytes`` one per line, and the one of an update report is its
``report_sha256``.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

from . import self_update as _su

ALGORITHM = "Ed25519"
KIND_SESSION = "session"
KIND_REPORT = "update-report"
KEY_ENV = "URTC_RECORD_KEY_FILE"
_PREFIX = "urtc-record/1"


class SigningError(Exception):
    """The key file cannot be read, or the key in it is not usable."""


def _clamp(seed: bytes) -> tuple[int, bytes]:
    digest = hashlib.sha512(seed).digest()
    scalar = int.from_bytes(digest[:32], "little")
    scalar &= (1 << 254) - 8
    scalar |= 1 << 254
    return scalar, digest[32:]


def _compress(point) -> bytes:
    x, y, z, _ = point
    inverse = pow(z, _su._P - 2, _su._P)
    x, y = x * inverse % _su._P, y * inverse % _su._P
    return (y | ((x & 1) << 255)).to_bytes(32, "little")


def public_key(seed: bytes) -> bytes:
    """The 32-byte public key of a 32-byte seed."""
    if len(seed) != 32:
        raise SigningError("the seed of a key has 32 bytes")
    return _compress(_su._mul(_clamp(seed)[0], _su.BASE_POINT))


def sign(seed: bytes, message: bytes) -> bytes:
    """The 64-byte Ed25519 signature of ``message`` (RFC 8032, pure)."""
    scalar, prefix = _clamp(seed)
    public = public_key(seed)
    r = int.from_bytes(hashlib.sha512(prefix + message).digest(), "little") % _su._Q
    r_bytes = _compress(_su._mul(r, _su.BASE_POINT))
    h = int.from_bytes(hashlib.sha512(r_bytes + public + message).digest(), "little") % _su._Q
    return r_bytes + ((r + h * scalar) % _su._Q).to_bytes(32, "little")


def key_id(public: bytes) -> str:
    """Sixteen hexadecimal digits that name a public key (the start of its SHA-256)."""
    return hashlib.sha256(public).hexdigest()[:16]


def default_key_path() -> Path:
    named = os.environ.get(KEY_ENV)
    return Path(named) if named else Path.home() / ".urtc-keys" / "records_ed25519.key"


def load_seed(path: str | Path | None = None, create: bool = True) -> bytes:
    """The seed in the key file; with ``create`` a new random one is written when the file is not there."""
    target = Path(path) if path is not None else default_key_path()
    if target.is_file():
        text = target.read_text(encoding="ascii", errors="replace").strip()
        try:
            seed = bytes.fromhex(text)
        except ValueError as exc:
            raise SigningError(f"{target.name}: the key file does not hold a hexadecimal seed") from exc
        if len(seed) != 32:
            raise SigningError(f"{target.name}: the seed must have 32 bytes")
        return seed
    if not create:
        raise SigningError(f"{target.name}: there is no key file")
    seed = os.urandom(32)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(str(target), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="ascii") as stream:
        stream.write(seed.hex() + "\n")
    return seed


def message(kind: str, payload: str) -> bytes:
    return f"{_PREFIX}\n{kind}\n{payload}".encode()


def session_payload(manifest: dict) -> str:
    return f"{manifest['log_file']}\n{manifest['log_sha256']}\n{manifest['log_bytes']}"


def report_payload(report: dict) -> str:
    return str(report.get("report_sha256", ""))


def make_signature(seed: bytes, kind: str, payload: str) -> dict:
    """The block that goes into a record: algorithm, key id, public key and signature (hexadecimal)."""
    public = public_key(seed)
    return {
        "algorithm": ALGORITHM,
        "key_id": key_id(public),
        "public_key": public.hex(),
        "signature": sign(seed, message(kind, payload)).hex(),
    }


def check_signature(block: object, kind: str, payload: str) -> bool:
    """True when ``block`` is a well-formed signature block that matches the payload (it says nothing about trusting the key)."""
    if not isinstance(block, dict) or block.get("algorithm") != ALGORITHM:
        return False
    try:
        public = bytes.fromhex(str(block["public_key"]))
        signature = bytes.fromhex(str(block["signature"]))
    except (KeyError, ValueError):
        return False
    if block.get("key_id") != key_id(public):
        return False
    return _su.ed25519_verify(public, message(kind, payload), signature)


def sign_session(manifest: dict, seed: bytes | None = None) -> dict:
    """A copy of a session record with its ``signature`` block."""
    body = {key: value for key, value in manifest.items() if key != "signature"}
    body["signature"] = make_signature(seed or load_seed(), KIND_SESSION, session_payload(body))
    return body


def verify_session(record: dict) -> bool:
    """True when the record carries a signature that matches its log name, hash and size."""
    try:
        return check_signature(record.get("signature"), KIND_SESSION, session_payload(record))
    except (KeyError, AttributeError):
        return False


def sign_report(report: dict, seed: bytes | None = None) -> dict:
    """A copy of an update report with its ``signature`` block (the report must carry ``report_sha256``)."""
    body = {key: value for key, value in report.items() if key != "signature"}
    body["signature"] = make_signature(seed or load_seed(), KIND_REPORT, report_payload(body))
    return body


def verify_report(report: dict) -> bool:
    try:
        return check_signature(report.get("signature"), KIND_REPORT, report_payload(report))
    except AttributeError:
        return False
