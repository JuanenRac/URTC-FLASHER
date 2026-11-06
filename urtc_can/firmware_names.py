"""GENERATED from spec/firmware_images.json by tools/generate_tools.py - do not edit by hand.

How the files of a firmware release are named (standard library only).
Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
"""
from __future__ import annotations

import re

PREFIX = 'URTC'
BOARDS = ('MAIN', 'SLAVE')
KINDS = ('FIRMWARE', 'BOOTLOADER')
IMAGE_EXTENSION = '.bin'
SIDECAR_SUFFIXES = ('.sha256', '.manifest.json', '.sig')
IMAGE_NAME = re.compile('^URTC_(MAIN|SLAVE)_(FIRMWARE|BOOTLOADER)_v(\\d+(?:\\.\\d+)+)\\.bin$', re.IGNORECASE)


def image_name(board: str, kind: str, version: str) -> str:
    """``URTC_MAIN_FIRMWARE_v0.4.1.bin`` from its parts; a board or kind that is not listed is refused."""
    if board.upper() not in BOARDS or kind.upper() not in KINDS or not re.fullmatch(r"\d+(?:\.\d+)+", version):
        raise ValueError(f"not a firmware image: {board!r} {kind!r} {version!r}")
    return f"{PREFIX}_{board.upper()}_{kind.upper()}_v{version}{IMAGE_EXTENSION}"


def parse_image_name(name: str) -> tuple[str, str, str] | None:
    """``(board, kind, version)`` of an image file name, or None when it is not one (a sidecar is not an image)."""
    match = IMAGE_NAME.fullmatch(name)
    return (match.group(1).upper(), match.group(2).upper(), match.group(3)) if match else None


def sidecar_names(image: str) -> tuple[str, ...]:
    """The files that travel with an image: its name plus each suffix."""
    return tuple(image + suffix for suffix in SIDECAR_SUFFIXES)


def is_sidecar(name: str) -> bool:
    return name.endswith(SIDECAR_SUFFIXES)
