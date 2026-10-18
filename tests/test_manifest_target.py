# =============================================================================
# URTC Flasher - tests/test_manifest_target.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""An image's manifest says which board it is for. The slave's image sent to the main board used to be transferred in full (34 KB) and rejected only at the end, by the HMAC, with
a reason that blamed the key; it is now refused before a single frame is sent."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from flasher_config import SLAVE_HARDWARE_ID, THIS_HARDWARE_ID
from flasher_protocol import FlashError, URTCFlasher
from flasher_transports import MockCAN


class _Silent:
    def send_frame(self, can_id, data):
        raise AssertionError("a frame was sent for an image of another board")

    def read_frame(self, timeout=0.05):
        return None


def _image(tmp_path, manifest):
    path = tmp_path / "URTC_X_v0.3.3.bin"
    path.write_bytes(bytes((i % 251) + 1 for i in range(3000)))
    Path(str(path) + ".manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return str(path)


@pytest.mark.parametrize("manifest", [{"component": "slave_application"}, {"hardware_id": f"0x{SLAVE_HARDWARE_ID:08X}"}, {"component": "slave_application", "hardware_id": f"0x{SLAVE_HARDWARE_ID:08X}"}])
def test_an_image_of_the_slave_is_refused_for_the_main_board_before_any_traffic(tmp_path, manifest):
    with pytest.raises(FlashError, match="another board"):
        URTCFlasher(_Silent(), log=lambda m: None).flash(_image(tmp_path, manifest))


@pytest.mark.parametrize("manifest", [{"component": "main_application"}, {"hardware_id": f"0x{THIS_HARDWARE_ID:08X}"}])
def test_an_image_of_the_main_board_is_refused_for_the_slave_before_any_traffic(tmp_path, manifest):
    with pytest.raises(FlashError, match="another board"):
        URTCFlasher(_Silent(), log=lambda m: None).flash_slave(_image(tmp_path, manifest))


def test_an_image_of_the_right_board_still_goes(tmp_path):
    manifest = {"component": "main_application", "hardware_id": f"0x{THIS_HARDWARE_ID:08X}"}
    assert URTCFlasher(MockCAN(), log=lambda m: None).flash(_image(tmp_path, manifest)) is True
