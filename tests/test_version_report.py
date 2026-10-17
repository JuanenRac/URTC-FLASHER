# =============================================================================
# URTC Flasher - tests/test_version_report.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Before an update the tool says "installed X -> new Y" and warns about a downgrade."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


from flasher_protocol import URTCFlasher
from flasher_transports import MockCAN


def _image(tmp_path, name="URTC_MAIN_FIRMWARE_v0.3.3.bin", version="0.3.3"):
    path = tmp_path / name
    path.write_bytes(b"\x01" * 100)
    if version:
        Path(str(path) + ".manifest.json").write_text(json.dumps({"version": version}), encoding="utf-8")
    return str(path)


def test_an_upgrade_is_reported_without_a_warning(tmp_path):
    lines = []
    result = URTCFlasher(MockCAN(installed_version=(0, 2)), log=lines.append).report_version_change(_image(tmp_path))
    assert result == {"installed": (0, 2), "new": (0, 3), "downgrade": False}
    assert any("0.2" in line and "0.3" in line for line in lines)
    assert not any("OLDER" in line for line in lines)


def test_a_downgrade_is_warned_about_and_a_backup_is_suggested(tmp_path):
    lines = []
    result = URTCFlasher(MockCAN(installed_version=(1, 0)), log=lines.append).report_version_change(_image(tmp_path))
    assert result["downgrade"] is True
    assert any("OLDER" in line and "backup" in line for line in lines)


def test_the_same_version_is_not_a_downgrade(tmp_path):
    result = URTCFlasher(MockCAN(installed_version=(0, 3)), log=lambda m: None).report_version_change(_image(tmp_path))
    assert result["downgrade"] is False


def test_a_board_that_does_not_answer_is_reported_as_unknown_and_nothing_stops(tmp_path):
    class _Dead:
        def send_frame(self, can_id, data):
            pass

        def read_frame(self, timeout=0.05):
            return None

    lines = []
    result = URTCFlasher(_Dead(), log=lines.append).report_version_change(_image(tmp_path), timeout=0.2)
    assert result == {"installed": None, "new": (0, 3), "downgrade": False}
    assert any("?" in line for line in lines)


def test_the_new_version_comes_from_the_name_when_there_is_no_manifest(tmp_path):
    flasher = URTCFlasher(MockCAN(), log=lambda m: None)
    assert flasher.new_image_version(_image(tmp_path, version=None)) == (0, 3)
    assert flasher.new_image_version(_image(tmp_path, name="image.bin", version=None)) is None
    assert flasher.new_image_version(_image(tmp_path, name="image.bin", version=None), version="2.5") == (2, 5)


def test_a_board_in_its_bootloader_with_no_firmware_has_nothing_installed(tmp_path):
    class _Empty(MockCAN):
        def send_frame(self, can_id, data):
            super().send_frame(can_id, data)
            # the simulated bootloader reports HardwareID 0 when no valid application is installed
            self._response_queue[:] = [(i, bytes([d[0]]) + b"\x00\x00\x00\x00" + d[5:]) if i == 0x7F9 else (i, d) for i, d in self._response_queue]

    result = URTCFlasher(_Empty(), log=lambda m: None).report_version_change(_image(tmp_path))
    assert result["installed"] is None and result["downgrade"] is False
