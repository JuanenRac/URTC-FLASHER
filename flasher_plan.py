# =============================================================================
# URTC Flasher - flasher_plan.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The plan of an update, made without a bus and without a board: ``urtc_flasher.py --cli --check-only --file IMAGE``.

It runs the checks the flasher runs before it sends a single frame (the plausibility of the file, the digest published next to it, the release signature, the
version of the image) and lists the steps the update would take, in the order of the protocol, so an image can be checked on any computer, in a pipeline, before
it goes near a bench. Nothing is opened, nothing is sent and nothing is written: the answer is the same for the same file.

What it does not do: it does not say that the update would succeed (that depends on the board, its bootloader and its version rule), and it does not make the
HMAC signature (that needs the key of the bench, which is never read here).
"""
from __future__ import annotations

import hashlib
import os
import re
import zlib
from typing import Any

from flasher_integrity import preflight_image
from flasher_validation import validate_firmware_file

PLAN_FORMAT = "urtc-flash-plan/1"
FRAME_BYTES = 8   # the data of a CAN frame: the image goes out eight bytes at a time

# the steps of an update in the order of the protocol (flasher_protocol.URTCFlasher.flash); the first one is left out when the bootloader is already running
STEPS = (
    ("trigger", "Ask the running application to restart into the bootloader (0x7F0)"),
    ("start_update", "Send the start of the update with the size of the image and the hardware identifier (0x7F1)"),
    ("signature", "Send the HMAC-SHA256 signature of the image in four chunks (0x7F7)"),
    ("data", "Send the image page by page, eight bytes per frame, waiting for the acknowledgement of each page (0x7F2)"),
    ("end_update", "Send the end of the update with the CRC32 and the version of the image (0x7F4)"),
    ("verify", "The bootloader verifies the image and reports its result (0x7F5)"),
)


def _version_from_name(path: str) -> str | None:
    match = re.search(r"[vV](\d+)\.(\d+)(?:\.(\d+))*", os.path.basename(path))
    return match.group(0)[1:] if match else None


def build_plan(path: str, version: str | None = None, no_trigger: bool = False, force: bool = False) -> dict[str, Any]:
    """The checks and the steps for an image. ``accepted`` is true when the flasher would go on to open a bus with this file (``force`` lets a file that fails
    the plausibility check through, as it does in the update)."""
    problems: list[str] = []
    is_valid, reason, size = validate_firmware_file(path)
    if not is_valid:
        problems.append(reason if force is False else f"{reason} (overridden by --force)")
    sha256 = crc32 = ""
    if size:
        try:
            with open(path, "rb") as stream:
                data = stream.read()
            sha256, crc32 = hashlib.sha256(data).hexdigest(), f"{zlib.crc32(data) & 0xFFFFFFFF:08X}"
        except OSError as exc:
            problems.append(f"can't read file: {exc}")
    check = preflight_image(path) if size else None
    digest = signature = "none"
    if check is not None:
        digest = "blocked" if check.blocked else ("verified" if check.verified else "not published")
        signature = check.release_signature or "none"
        if check.blocked:
            problems.extend(check.reasons)
    image_version = version or _version_from_name(path)
    steps: list[dict[str, Any]] = [{"step": key, "text": text} for key, text in STEPS if not (key == "trigger" and no_trigger)]
    for number, step in enumerate(steps, 1):
        step["number"] = number
    frames = -(-size // FRAME_BYTES) if size else 0
    accepted = (is_valid or force) and not (check is not None and check.blocked) and not any(p.startswith("can't read") for p in problems)
    return {
        "format": PLAN_FORMAT, "file": os.path.basename(path), "size": size, "sha256": sha256, "crc32": crc32, "plausible": is_valid, "reason": reason,
        "digest": digest, "release_signature": signature, "version": image_version, "data_frames": frames, "steps": steps, "problems": problems, "accepted": accepted,
    }


def render(plan: dict[str, Any]) -> list[str]:
    """The plan as lines of text."""
    lines = [f"Plan for {plan['file']}: {plan['size']} bytes, SHA-256 {plan['sha256'] or '-'}, CRC32 {plan['crc32'] or '-'}",
             f"  plausibility of the file: {'ok' if plan['plausible'] else 'FAILS'} - {plan['reason']}",
             f"  published digest: {plan['digest']}; release signature: {plan['release_signature']}; version: {plan['version'] or 'not known (the update would stop and ask for --version)'}"]
    lines += [f"  {s['number']}. {s['text']}" for s in plan["steps"]]
    lines.append(f"  {plan['data_frames']} data frames in all")
    lines += [f"  PROBLEM: {p}" for p in plan["problems"]]
    lines.append("The flasher would go on to open a bus with this image." if plan["accepted"] else "The flasher would refuse this image.")
    lines.append("Nothing was sent: this is a check, not an update (the HMAC signature needs the key of the bench and is not made here).")
    return lines
