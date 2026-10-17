# =============================================================================
# URTC Flasher - tests/test_version_resolution.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""The version written into the board with END_UPDATE is the real one of the image (its manifest, the one given, or the one in its file name) and is never invented: the tool used to
report 1.0 for an image without a manifest, so every later official image (0.3.x, 0.4) looked older to the anti-rollback check and was rejected."""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from flasher_config import CAN_ID_END_UPDATE
from flasher_protocol import FlashError, URTCFlasher
from flasher_transports import MockCAN


class _Spy(MockCAN):
    def __init__(self):
        super().__init__()
        self.reported = None

    def send_frame(self, can_id, data):
        if can_id == CAN_ID_END_UPDATE:
            self.reported = struct.unpack(">IHH", data)[1:]
        super().send_frame(can_id, data)


def _image(tmp_path, name, size=3000):
    path = tmp_path / name
    path.write_bytes(bytes((i % 251) + 1 for i in range(size)))
    return str(path)


def test_the_version_in_the_manifest_is_reported(tmp_path):
    path = _image(tmp_path, "build.bin")
    Path(path + ".manifest.json").write_text(json.dumps({"version": "0.4.1"}), encoding="utf-8")
    can = _Spy()
    assert URTCFlasher(can, log=lambda m: None).flash(path) is True
    assert can.reported == (0, 4)


def test_the_version_in_the_file_name_is_reported(tmp_path):
    can = _Spy()
    assert URTCFlasher(can, log=lambda m: None).flash(_image(tmp_path, "URTC_MAIN_FIRMWARE_v0.3.3.bin")) is True
    assert can.reported == (0, 3)


@pytest.mark.parametrize("given, expected", [((0, 5), (0, 5)), ("0.6", (0, 6)), ("v1.2.3", (1, 2))])
def test_the_version_given_by_the_caller_is_reported(tmp_path, given, expected):
    can = _Spy()
    assert URTCFlasher(can, log=lambda m: None).flash(_image(tmp_path, "build.bin"), version=given) is True
    assert can.reported == expected


@pytest.mark.parametrize("given", [None, "x.y", "7", (300, 1), ("a", "b")])
def test_without_a_real_version_nothing_is_sent_and_none_is_invented(tmp_path, given):
    class _Silent:
        def send_frame(self, can_id, data):
            raise AssertionError("a frame was sent although the version is not known")

        def read_frame(self, timeout=0.05):
            raise AssertionError("waited although the version is not known")

    with pytest.raises(FlashError, match="version"):
        URTCFlasher(_Silent(), log=lambda m: None).flash(_image(tmp_path, "build.bin"), version=given)
