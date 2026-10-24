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


# -- the application of the expansion slave: 0x221 (register 0x01) and its companion 0x222 ---------------------------------------
SLAVE_APP_PATCH_MAX = 127


def slave_app_version_request() -> tuple[int, bytes]:
    """The frame that asks the master for the version register of the slave application (it relays 8 bytes of the 10)."""
    return protocol.encode_slave_reg_read_request(protocol.SLAVE_APP_REG_APP_VERSION, 8)


def parse_slave_app_version(frames: Iterable[Frame]) -> dict | None:
    """Combine the frames that answer one read of the slave version register (0x221, then 0x222) into one description.

    None when there is no 0x221 answer of at least 8 bytes. Keys: responder ('application' or 'bootloader'), hardware_id,
    major, minor (None: the answer of 8 bytes stops at the high byte of the minor field, so the low byte is not in it; it is read from
    the third byte of the 0x222 companion when the slave sends one, or from a longer answer, and is otherwise not known), minor_high, patch (None when the slave sends none: a slave
    application from before the field, whose tenth byte is 0, gets no 0x222) and patch_aware.
    """
    answer = None
    patch = None
    minor_low = None
    for can_id, data in frames:
        data = bytes(data)
        if can_id == protocol.CAN_ID_SLAVE_REG_READ and len(data) >= 8 and answer is None:
            answer = data
        elif can_id == protocol.CAN_ID_SLAVE_APP_PATCH and patch is None:
            fields = protocol.decode_slave_app_patch(data)
            if fields is not None and fields["register"] == protocol.SLAVE_APP_REG_APP_VERSION and 1 <= fields["patch"] <= SLAVE_APP_PATCH_MAX:
                patch = fields["patch"]
                minor_low = fields.get("minor_low")
    if answer is None:
        return None
    if len(answer) >= 9:
        minor = int.from_bytes(answer[7:9], "big")
    elif minor_low is not None:
        minor = (answer[7] << 8) | minor_low
    else:
        minor = None
    return {
        "responder": "bootloader" if answer[0] == protocol.RESPONDER_BOOTLOADER else "application",
        "hardware_id": f"0x{int.from_bytes(answer[1:5], 'big'):08X}",
        "major": int.from_bytes(answer[5:7], "big"),
        "minor": minor,
        "minor_high": answer[7],
        "patch": patch,
        "patch_aware": patch is not None,
    }


def slave_app_version_text(info: dict | None) -> str:
    """``major.minor.patch`` with a ``?`` for what the frames did not carry (the minor of a slave seen through the master)."""
    if info is None:
        return "?"
    minor = "?" if info["minor"] is None else str(info["minor"])
    return f"{info['major']}.{minor}" + (f".{info['patch']}" if info["patch"] is not None else "")
