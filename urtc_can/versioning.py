# =============================================================================
# URTC-COMMON - src/urtc_common/versioning.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The version query and the patch number over CAN: reading the answers, the minor field, the order of versions.

A board that predates the patch extension never sends 0x7E9; a host that gets 0x7F9 and no 0x7E9 within the
grace window treats the patch as unknown and keeps the legacy two-component version and the legacy end-of-update
payload. This module only interprets frames that were already collected; waiting for them is the caller's job
(``protocol.VERSION_PATCH_GRACE_MS`` is the window).
"""
from __future__ import annotations

from typing import Any, Iterable

from . import protocol

Frame = tuple[int, bytes]
Version = tuple[int, int, "int | None"]


def parse_version_answer(frames: Iterable[Frame]) -> dict | None:
    """Combine the answer frames of one version query into one description, or None when there is no 0x7F9 of 8 bytes.

    Keys: responder ('application' or 'bootloader'), hardware_id, major, minor, patch (None when unknown),
    patch_aware (a valid 0x7E9 was seen), accepts_patch_in_end_update, and bootloader as (major, minor, patch)
    when the bootloader answered and sent its own 0x7FA.
    """
    answer = None
    bootloader = None
    patch_frame = None
    for can_id, data in frames:
        data = bytes(data)
        if can_id == protocol.CAN_ID_VERSION_RESPONSE and len(data) == 8 and answer is None:
            answer = data
        elif can_id == protocol.CAN_ID_BOOTLOADER_VERSION_RESPONSE and len(data) == 3 and bootloader is None:
            bootloader = (data[0], data[1], data[2])
        elif can_id == protocol.CAN_ID_VERSION_PATCH_RESPONSE and len(data) >= 3 and patch_frame is None:
            patch_frame = data[:3]
    if answer is None:
        return None
    result: dict[str, Any] = {
        "responder": "bootloader" if answer[0] == protocol.RESPONDER_BOOTLOADER else "application",
        "hardware_id": f"0x{int.from_bytes(answer[1:5], 'big'):08X}",
        "major": int.from_bytes(answer[5:7], "big"),
        "minor": answer[7],
        "patch": None,
        "patch_aware": patch_frame is not None,
        "accepts_patch_in_end_update": False,
    }
    if patch_frame is not None:
        result["patch"] = None if patch_frame[1] == protocol.PATCH_UNKNOWN else patch_frame[1]
        result["accepts_patch_in_end_update"] = bool(patch_frame[2] & protocol.PATCH_FLAG_ACCEPTS_IN_END_UPDATE)
    if bootloader is not None and result["responder"] == "bootloader":
        result["bootloader"] = bootloader
    return result


def end_update_minor_field(minor: int, patch: int | None, bootloader_accepts_patch: bool) -> int:
    """The 16-bit minor field to send: the patch rides in the high byte only towards a bootloader that announced it."""
    if bootloader_accepts_patch and patch is not None and 0 <= patch <= protocol.PATCH_MAX:
        return protocol.minor_field_pack(minor, patch)
    return minor


def compare(installed: Version, candidate: Version) -> int:
    """1 when the candidate is newer, 0 when equal, -1 when older. The patch decides only when both carry one."""
    return protocol.version_compare(installed, candidate)
