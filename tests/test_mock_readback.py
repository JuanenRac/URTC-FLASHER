# =============================================================================
# URTC Flasher - tests/test_mock_readback.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The simulated bootloader answers a readback like the real one: the size first, pages of
8-byte frames, the last frame as short as needed, the next page after each ACK."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from flasher_protocol import FlashError, URTCFlasher
from flasher_transports import MockCAN


@pytest.mark.parametrize("size", [1, 8, 9, 2047, 2048, 2049, 5000])
def test_a_backup_from_the_simulated_board_is_complete(tmp_path, size):
    image = bytes((i * 5 + 1) % 256 for i in range(size))
    output = tmp_path / "backup.bin"
    assert URTCFlasher(MockCAN(installed_image=image), log=lambda m: None).read_back_flash(str(output)) == size
    assert output.read_bytes() == image


def test_a_board_with_nothing_installed_says_so(tmp_path):
    with pytest.raises(FlashError):
        URTCFlasher(MockCAN(), log=lambda m: None).read_back_flash(str(tmp_path / "backup.bin"))
