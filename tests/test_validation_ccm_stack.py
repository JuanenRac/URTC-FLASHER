# =============================================================================
# URTC Flasher - tests/test_validation_ccm_stack.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The bootloader accepts an initial stack pointer in the main SRAM or in the CCM RAM; the plausibility check of the flasher only accepted the main SRAM, so a valid image with its stack
in the CCM was marked invalid. The example configuration also no longer carries values that change how an image is signed or laid out."""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from flasher_config import APP_FLASH_ADDR, APP_MAX_SIZE
from flasher_validation import validate_firmware_file


def _image(tmp_path, stack):
    path = tmp_path / "app.bin"
    path.write_bytes(struct.pack("<II", stack, APP_FLASH_ADDR + 0x101) + bytes(1000))
    return str(path)


@pytest.mark.parametrize("stack, valid", [(0x20009000, True), (0x2000A000, True), (0x10002000, True), (0x10000100, True), (0x20000000, False), (0x2000A004, False), (0x10002004, False), (0x08000000, False)])
def test_the_stack_pointer_may_be_in_the_main_sram_or_in_the_ccm(tmp_path, stack, valid):
    is_valid, _reason, _size = validate_firmware_file(_image(tmp_path, stack), APP_FLASH_ADDR, APP_MAX_SIZE)
    assert is_valid is valid


def test_the_example_configuration_only_asks_for_the_language():
    example = json.loads((Path(__file__).resolve().parent.parent / "urtc_config.json.example").read_text(encoding="utf-8"))
    assert {key for key in example if not key.startswith("_")} == {"language"}
