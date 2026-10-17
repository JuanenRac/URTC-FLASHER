# =============================================================================
# URTC Flasher - tests/test_patch_number.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""The firmware PATCH number over CAN: frame 0x7E9, the extended slave answer
0x218, the patch in the end-of-update frame, and full compatibility with boards
and simulators that predate it."""
from __future__ import annotations

import hashlib
import json
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from flasher_protocol import URTCFlasher, minor_with_patch
from flasher_transports import MockCAN


class Scripted:
    """Answers 0x7F8 / 0x217 with a fixed list of frames, in order."""

    def __init__(self, version_frames=(), slave_frames=()):
        self.version_frames = list(version_frames)
        self.slave_frames = list(slave_frames)
        self.queue = []

    def send_frame(self, can_id, data):
        if can_id == 0x7F8:
            self.queue += self.version_frames
        elif can_id == 0x217:
            self.queue += self.slave_frames

    def read_frame(self, timeout=0.05):
        return self.queue.pop(0) if self.queue else None


def _f9(responder=0, major=0, minor=3):
    return (0x7F9, bytes([responder]) + struct.pack(">I", 0x0303CC01) + struct.pack(">H", major) + bytes([minor]))


def _image(tmp_path, version="0.3.5", name="URTC_MAIN_FIRMWARE_v0.3.5.bin", data=b"\x01" * 2100):
    path = tmp_path / name
    path.write_bytes(data)
    manifest = {"version": version, "sha256": hashlib.sha256(data).hexdigest(), "hmac_sha256": "ab" * 32}
    Path(str(path) + ".manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return str(path)


def test_the_patch_frame_after_the_application_answer_gives_major_minor_patch():
    info = URTCFlasher(Scripted([_f9(), (0x7E9, bytes([0, 5, 0]))]), log=print).query_version()
    assert (info["version_major"], info["version_minor"], info["version_patch"]) == (0, 3, 5)
    assert info["patch_aware"] is True and info["accepts_patch_in_end_update"] is False
    assert minor_with_patch(info) == "3.5"


def test_the_patch_frame_may_arrive_before_the_version_frame_and_may_be_longer():
    info = URTCFlasher(Scripted([(0x7E9, bytes([1, 7, 1, 0, 0, 0])), _f9(1), (0x7FA, bytes([1, 0, 1]))]), log=print).query_version()
    assert info["version_patch"] == 7
    assert info["accepts_patch_in_end_update"] is True
    assert info["bootloader_version"] == (1, 0, 1)


def test_an_unknown_patch_is_none_but_the_board_is_still_patch_aware():
    info = URTCFlasher(Scripted([_f9(), (0x7E9, bytes([0, 0xFF, 0]))]), log=print).query_version()
    assert info["version_patch"] is None and info["patch_aware"] is True
    assert minor_with_patch(info) == "3"


def test_a_board_without_the_patch_frame_is_reported_as_before():
    info = URTCFlasher(Scripted([_f9()]), log=print).query_version(patch_grace=0.05)
    assert info["version_patch"] is None and info["patch_aware"] is False
    assert info["accepts_patch_in_end_update"] is False
    assert (info["version_major"], info["version_minor"]) == (0, 3)


def test_the_old_mock_board_has_no_patch_and_the_new_one_sends_it():
    old = URTCFlasher(MockCAN(installed_version=(0, 3)), log=print).query_version(patch_grace=0.05)
    assert old["patch_aware"] is False and old["version_patch"] is None and old["bootloader_version"] == (1, 0, 1)
    new = URTCFlasher(MockCAN(installed_version=(0, 3), installed_patch=5, accepts_patch=True), log=print).query_version()
    assert new["version_patch"] == 5 and new["accepts_patch_in_end_update"] is True


def test_the_slave_answer_with_five_bytes_carries_the_patch_and_the_acceptance():
    part1 = (0x217, bytes([1]) + struct.pack(">I", 0x0303CC02) + struct.pack(">H", 0) + bytes([0]))
    info = URTCFlasher(Scripted(slave_frames=[part1, (0x218, bytes([9, 2, 4, 2, 1]))]), log=print).query_slave_version()
    assert (info["app_version_major"], info["app_version_minor"], info["app_version_patch"]) == (0, 9, 4)
    assert (info["bootloader_version"], info["bootloader_minor"], info["bootloader_patch"]) == (2, 2, 1)
    assert info["accepts_patch_in_end_update"] is True


def test_the_slave_answer_with_two_bytes_is_the_legacy_one():
    part1 = (0x217, bytes([1]) + struct.pack(">I", 0x0303CC02) + struct.pack(">H", 0) + bytes([0]))
    info = URTCFlasher(Scripted(slave_frames=[part1, (0x218, bytes([9, 2]))]), log=print).query_slave_version()
    assert info["app_version_patch"] is None and info["accepts_patch_in_end_update"] is False
    assert info["bootloader_version"] == 2


def test_the_mock_slave_answers_both_forms():
    legacy = URTCFlasher(MockCAN(slave_version={"version": (0, 1), "bootloader": 2}), log=print).query_slave_version()
    assert legacy["accepts_patch_in_end_update"] is False
    extended = URTCFlasher(MockCAN(slave_version={"version": (0, 1), "bootloader": 2, "patch": 9, "patch_extension": True}),
                           log=print).query_slave_version()
    assert extended["app_version_patch"] == 9 and extended["accepts_patch_in_end_update"] is True
    assert URTCFlasher(MockCAN(), log=print).query_slave_version(timeout=0.2) is None


# -- the patch of an image and the comparison ---------------------------------

def test_the_image_patch_comes_from_the_manifest_the_given_version_or_the_name(tmp_path):
    flasher = URTCFlasher(MockCAN(), log=print)
    assert flasher.new_image_patch(_image(tmp_path)) == 5
    assert flasher.new_image_patch(_image(tmp_path, version="0.3")) is None
    nameless = tmp_path / "image.bin"
    nameless.write_bytes(b"1")
    assert flasher.new_image_patch(str(nameless)) is None
    assert flasher.new_image_patch(str(nameless), version="v0.3.8") == 8
    assert flasher.new_image_patch(str(tmp_path / "URTC_MAIN_FIRMWARE_v0.3.7.bin")) == 7
    assert flasher.new_image_patch(_image(tmp_path, version="0.3.200")) is None  # more than the 7 bits the frame has


def test_the_patch_decides_only_when_both_sides_have_one(tmp_path):
    lines = []
    older = URTCFlasher(MockCAN(installed_version=(0, 3), installed_patch=7), log=lines.append).report_version_change(_image(tmp_path))
    assert older["downgrade"] is True and (older["installed_patch"], older["new_patch"]) == (7, 5)
    assert any("0.3.7" in line and "0.3.5" in line for line in lines)
    assert any("OLDER" in line for line in lines)
    newer = URTCFlasher(MockCAN(installed_version=(0, 3), installed_patch=2), log=lambda m: None).report_version_change(_image(tmp_path))
    assert newer["downgrade"] is False
    # the board does not carry a patch: same major.minor is not a downgrade, whatever the image says
    legacy = URTCFlasher(MockCAN(installed_version=(0, 3)), log=lambda m: None).report_version_change(_image(tmp_path, version="0.3.1"))
    assert legacy["downgrade"] is False and legacy["installed_patch"] is None
    # an image without a patch against a board that has one: not compared either
    nopatch = URTCFlasher(MockCAN(installed_version=(0, 3), installed_patch=9), log=lambda m: None).report_version_change(_image(tmp_path, version="0.3"))
    assert nopatch["downgrade"] is False
    # major.minor still wins over the patch
    assert URTCFlasher(MockCAN(installed_version=(0, 4), installed_patch=0), log=lambda m: None).report_version_change(_image(tmp_path))["downgrade"] is True


# -- the end-of-update frame ---------------------------------------------------

def test_the_minor_field_carries_the_patch_only_when_it_is_accepted():
    field = URTCFlasher._end_update_minor_field
    assert field(3, 5, True) == 0x8503
    assert field(3, 5, False) == 3
    assert field(3, None, True) == 3
    assert field(3, 200, True) == 3


def _flash(mock, image):
    URTCFlasher(mock, log=lambda m: None).flash(image)
    return struct.unpack(">IHH", mock.end_update_payload)


def test_a_bootloader_that_announced_support_receives_the_patch(tmp_path):
    image = _image(tmp_path)
    crc, major, minor_field = _flash(MockCAN(installed_patch=1, accepts_patch=True), image)
    assert crc == zlib.crc32(Path(image).read_bytes()) & 0xFFFFFFFF
    assert (major, minor_field) == (0, 0x8503)


@pytest.mark.parametrize("mock", [
    MockCAN(),                                        # a board that predates the patch
    MockCAN(installed_patch=1, accepts_patch=False),  # patch-aware but the bootloader does not read it
])
def test_every_other_board_receives_the_legacy_payload(tmp_path, mock):
    assert _flash(mock, _image(tmp_path))[1:] == (0, 3)


def test_an_image_without_a_patch_always_gets_the_legacy_payload(tmp_path):
    assert _flash(MockCAN(installed_patch=1, accepts_patch=True), _image(tmp_path, version="0.3", name="URTC_MAIN_FIRMWARE.bin"))[1:] == (0, 3)
