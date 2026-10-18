# =============================================================================
# URTC-FLASHER - flasher_release_signature.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Release signatures of the files this tool downloads or flashes.

Every asset of an official URTC release comes with `<asset>.sig`: the Ed25519
signature, by the key of the releases, of the text
`urtc-rel/1|<file name>|<sha256 of the file>`. The public key is pinned below
and the check uses the standard library only (no extra package to install).
This is a layer in front of the signature the bootloader verifies on the
board; it says who published the file, not that the board will accept it.

REQUIRE_RELEASE_SIGNATURE is the transition switch: while False, a file with
no `.sig` is reported as unsigned (the images of the bench pre-releases have
none) and a wrong one is always refused; once the first official release
exists it is set to True and an unsigned file is refused as well.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass

SCHEME = "urtc-rel/1"
PUBLIC_KEY_HEX = "4020c46d76c8ebacb64c5c7b9f3e7c62475afeb133d7421591988174e0f5dc90"
REQUIRE_RELEASE_SIGNATURE = False

# --- Ed25519 verification (RFC 8032) ------------------------------------------
_P = 2**255 - 19
_Q = 2**252 + 27742317777372353535851937790883648493
_D = -121665 * pow(121666, _P - 2, _P) % _P
_SQRT_M1 = pow(2, (_P - 1) // 4, _P)


def _add(a, b):
    x1, y1, z1, t1 = a
    x2, y2, z2, t2 = b
    pa = (y1 - x1) * (y2 - x2) % _P
    pb = (y1 + x1) * (y2 + x2) % _P
    pc = 2 * t1 * t2 * _D % _P
    pd = 2 * z1 * z2 % _P
    e, f, g, h = pb - pa, pd - pc, pd + pc, pb + pa
    return (e * f % _P, g * h % _P, f * g % _P, e * h % _P)


def _mul(scalar, point):
    result = (0, 1, 1, 0)
    while scalar > 0:
        if scalar & 1:
            result = _add(result, point)
        point = _add(point, point)
        scalar >>= 1
    return result


def _equal(a, b):
    return (a[0] * b[2] - b[0] * a[2]) % _P == 0 and (a[1] * b[2] - b[1] * a[2]) % _P == 0


def _recover_x(y, sign):
    if y >= _P:
        return None
    x2 = (y * y - 1) * pow(_D * y * y + 1, _P - 2, _P) % _P
    if x2 == 0:
        return None if sign else 0
    x = pow(x2, (_P + 3) // 8, _P)
    if (x * x - x2) % _P:
        x = x * _SQRT_M1 % _P
    if (x * x - x2) % _P:
        return None
    return _P - x if (x & 1) != sign else x


def _decompress(data):
    y = int.from_bytes(data, "little")
    sign, y = y >> 255, y & ((1 << 255) - 1)
    x = _recover_x(y, sign)
    return None if x is None else (x, y, 1, x * y % _P)


_GY = 4 * pow(5, _P - 2, _P) % _P
_GX = _recover_x(_GY, 0)
_BASE = (_GX, _GY, 1, _GX * _GY % _P)


def ed25519_verify(public: bytes, message: bytes, signature: bytes) -> bool:
    """True only for a valid Ed25519 signature of `message` by the 32-byte key `public`."""
    if len(public) != 32 or len(signature) != 64:
        return False
    a_point, r_point = _decompress(public), _decompress(signature[:32])
    s = int.from_bytes(signature[32:], "little")
    if a_point is None or r_point is None or s >= _Q:
        return False
    h = int.from_bytes(hashlib.sha512(signature[:32] + public + message).digest(), "little") % _Q
    return _equal(_mul(s, _BASE), _add(r_point, _mul(h, a_point)))


@dataclass(frozen=True)
class SignatureStatus:
    state: str  # "signed" | "unsigned" | "invalid"
    detail: str = ""


def _sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def release_message(name: str, digest: str) -> bytes:
    return f"{SCHEME}|{name}|{digest}".encode("utf-8")


def check_file(path: str, public_hex: str | None = None) -> SignatureStatus:
    """The release-signature state of `path` from its `<path>.sig`."""
    sig_path = path + ".sig"
    if not os.path.isfile(sig_path):
        return SignatureStatus("unsigned", f"{os.path.basename(path)} has no release signature")
    try:
        with open(sig_path, "r", encoding="ascii") as handle:
            signature = bytes.fromhex(handle.read().strip())
        good = ed25519_verify(bytes.fromhex(public_hex or PUBLIC_KEY_HEX),
                              release_message(os.path.basename(path), _sha256_file(path)), signature)
    except (OSError, ValueError) as exc:
        return SignatureStatus("invalid", f"{os.path.basename(path)}: unreadable release signature ({exc})")
    if not good:
        return SignatureStatus("invalid", f"{os.path.basename(path)} does not match its release signature")
    return SignatureStatus("signed")


def refusal(status: SignatureStatus, require: bool | None = None) -> str | None:
    """Why a file must not be used (None when it may): a wrong signature always, a missing one once the transition is over."""
    if status.state == "invalid":
        return status.detail
    if status.state == "unsigned" and (REQUIRE_RELEASE_SIGNATURE if require is None else require):
        return status.detail
    return None
