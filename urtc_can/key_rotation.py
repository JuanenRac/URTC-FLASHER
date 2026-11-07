# =============================================================================
# URTC-COMMON - src/urtc_common/key_rotation.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Rotation of the signing key: up to two fingerprints announced and accepted during a configurable window.

[FIRMWARE] The bootloader side is designed and tested on the host only; nothing is built for the board or flashed. See ``docs/BOOTLOADER_AUTH.md``.

A bootloader trusts a *current* key and, while a rotation is in progress, also the *previous* one. The rules, all of them in ``active_key_ids``:

* the window is a CONFIGURATION PARAMETER (``rotation_window_s``, seconds), never a constant of the code; ``0`` means "no overlap";
* inside the window ``[started_at, started_at + window_s)`` both fingerprints are valid; the previous one expires when the window ends;
* outside the window (or with a window of zero, or when the clock reads earlier than the start, which fails closed) only the current one is valid;
* a revoked key is never valid, window or not; a revoked current key leaves nothing trusted (fails closed);
* a fingerprint that is not announced is unknown and is refused; a fingerprint listed twice counts once;
* the policy is never touched: ``ed25519_only`` stays ``ed25519_only``, a rotation only decides WHICH Ed25519 keys verify.

The announcement: up to two frames on ``0x7ED`` (8 bytes each, the current key first, so a host that reads only the first one sees what it sees today),
and the status on ``0x7EB`` (``05``, number of keys, flags, seconds left in the window, big-endian, ``0xFFFFFFFF`` when there is no window).
Nothing here holds a key: fingerprints are the first 8 bytes of the SHA-512 of a public key.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

KEY_ID_SIZE = 8
MAX_ANNOUNCED = 2
STATUS_OP = 0x05
NO_WINDOW = 0xFFFFFFFF
FLAG_ROTATING = 0x01   # a previous key is still valid
FLAG_CURRENT_REVOKED = 0x02


@dataclass(frozen=True)
class Rotation:
    """What a bootloader stores about its keys. ``window_s`` and ``started_at`` come from the metadata / configuration; ``started_at`` is in the same
    monotonic seconds as ``now`` (the source of that clock is an open point of the firmware design)."""
    current: bytes
    previous: bytes | None = None
    window_s: int = 0
    started_at: int = 0
    revoked: frozenset[bytes] = frozenset()


def _check(kid: bytes) -> None:
    if len(kid) != KEY_ID_SIZE:
        raise ValueError("a key fingerprint is 8 bytes")


def in_window(window_s: int, started_at: int, now: int) -> bool:
    if window_s <= 0 or now < started_at:
        return False
    return now - started_at < window_s


def active_key_ids(rot: Rotation, now: int) -> list[bytes]:
    """The fingerprints valid at ``now``: the current one first, then the previous one while the window lasts. Never more than two, never a repeat."""
    _check(rot.current)
    ids: list[bytes] = []
    if rot.current not in rot.revoked:
        ids.append(rot.current)
    if rot.previous is not None:
        _check(rot.previous)
        if rot.previous not in rot.revoked and rot.previous not in ids and rot.current not in rot.revoked and in_window(rot.window_s, rot.started_at, now):
            ids.append(rot.previous)
    return ids[:MAX_ANNOUNCED]


def is_accepted(rot: Rotation, now: int, kid: bytes) -> bool:
    return len(kid) == KEY_ID_SIZE and kid in active_key_ids(rot, now)


def seconds_left(rot: Rotation, now: int) -> int:
    if rot.previous is None or len(active_key_ids(rot, now)) < 2:
        return NO_WINDOW
    return min(rot.started_at + rot.window_s - now, NO_WINDOW - 1)


def announce(rot: Rotation, now: int) -> tuple[list[bytes], bytes]:
    """``(frames on 0x7ED, payload on 0x7EB)`` for ``now``. No active key: no ``0x7ED`` frame (a host reads "no data", never a difference)."""
    ids = active_key_ids(rot, now)
    flags = (FLAG_ROTATING if len(ids) == 2 else 0) | (FLAG_CURRENT_REVOKED if rot.current in rot.revoked else 0)
    return list(ids), struct.pack(">BBBI", STATUS_OP, len(ids), flags, seconds_left(rot, now))


def parse_status(payload: bytes) -> dict[str, int | bool] | None:
    if len(payload) != 7 or payload[0] != STATUS_OP or payload[1] > MAX_ANNOUNCED or payload[2] & ~(FLAG_ROTATING | FLAG_CURRENT_REVOKED):
        return None
    return {"count": payload[1], "rotating": bool(payload[2] & FLAG_ROTATING), "current_revoked": bool(payload[2] & FLAG_CURRENT_REVOKED),
            "seconds_left": struct.unpack(">I", payload[3:7])[0]}


def host_check(announced: list[bytes], image_key_id: bytes) -> str:
    """What a flashing tool says about the key of an image: ``no_data`` (the bootloader announced nothing), ``match`` (any announced fingerprint) or ``differs``."""
    frames = [f for f in announced if len(f) == KEY_ID_SIZE][:MAX_ANNOUNCED]
    if not frames:
        return "no_data"
    return "match" if image_key_id in frames else "differs"
