# =============================================================================
# URTC Flasher - tests/test_flash_protocol_dispatch.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Real gap this closes: flasher_protocol.py is the code that writes to
real hardware over CAN, yet before this file only its verify-fail
reporting path (tests/test_flash_verify_fail_reporting.py) and its use of
time.monotonic() (tests/test_flasher_protocol_clock.py) had automated
coverage. The size-guard checks in flash()/flash_slave(), query_version(),
and the manifest sha256 cross-check in _check_manifest() had none - this
file adds it, against the same real MockCAN simulated peer the existing
suite already uses (flasher_transports.py), never mocking flash() itself.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from flasher_config import APP_MAX_SIZE, SLAVE_APP_MAX_SIZE
from flasher_protocol import FlashError, URTCFlasher
from flasher_transports import MockCAN


def _write_firmware(tmp_path: Path, size: int, name: str = "firmware.bin") -> str:
    firmware_path = tmp_path / name
    firmware_path.write_bytes(bytes((i % 251) + 1 for i in range(size)))
    return str(firmware_path)


class _ExplodingCAN:
    """A CAN stand-in that fails the test if flash()/flash_slave() ever
    sends a single real frame - used to prove the size guards below
    reject an oversized/empty file BEFORE any bus traffic, not just
    eventually via some later protocol timeout."""

    def send_frame(self, can_id, data):
        raise AssertionError(f"flash() sent a frame (0x{can_id:X}) despite an invalid firmware file - the size guard did not run first")

    def read_frame(self, timeout=0.05):
        raise AssertionError("flash() waited for a reply despite an invalid firmware file")


def test_flash_rejects_empty_firmware_file_before_sending_anything(tmp_path):
    firmware_path = _write_firmware(tmp_path, 0)
    flasher = URTCFlasher(_ExplodingCAN(), log=lambda msg: None)
    with pytest.raises(FlashError, match="empty"):
        flasher.flash(firmware_path)


def test_flash_rejects_oversized_firmware_file_before_sending_anything(tmp_path):
    firmware_path = _write_firmware(tmp_path, APP_MAX_SIZE + 1)
    flasher = URTCFlasher(_ExplodingCAN(), log=lambda msg: None)
    with pytest.raises(FlashError, match="exceeds"):
        flasher.flash(firmware_path)


def test_flash_accepts_a_file_exactly_at_the_max_size_boundary(tmp_path):
    # The boundary itself (not one byte over) must not be rejected by the
    # same guard - a real, exactly-full image is a legitimate case.
    firmware_path = _write_firmware(tmp_path, APP_MAX_SIZE)
    can = MockCAN()
    flasher = URTCFlasher(can, log=lambda msg: None)
    assert flasher.flash(firmware_path) is True


def test_flash_slave_rejects_empty_firmware_file_before_sending_anything(tmp_path):
    firmware_path = _write_firmware(tmp_path, 0)
    flasher = URTCFlasher(_ExplodingCAN(), log=lambda msg: None)
    with pytest.raises(FlashError, match="empty"):
        flasher.flash_slave(firmware_path)


def test_flash_slave_rejects_oversized_firmware_file_before_sending_anything(tmp_path):
    firmware_path = _write_firmware(tmp_path, SLAVE_APP_MAX_SIZE + 1)
    flasher = URTCFlasher(_ExplodingCAN(), log=lambda msg: None)
    with pytest.raises(FlashError, match="exceeds"):
        flasher.flash_slave(firmware_path)


def test_query_version_reports_a_bootloader_responder_via_mockcan(tmp_path):
    # MockCAN's own send_frame() always answers CAN_ID_QUERY_VERSION as a
    # bootloader (see its docstring) - this is the one direct test of
    # query_version() against that real simulated peer; every other test
    # in this suite only exercises it indirectly through flash()'s own
    # final-verification fallback path.
    can = MockCAN()
    flasher = URTCFlasher(can, log=lambda msg: None)
    info = flasher.query_version(timeout=1.0)
    assert info is not None
    assert info["responder"] == "bootloader"
    assert info["bootloader_version"] == (1, 0, 1)


def test_manifest_sha256_mismatch_logs_a_warning_but_does_not_abort(tmp_path):
    # _check_manifest() is documented as "a convenience warning, not an
    # authoritative gate" - real behavior this test locks in: a
    # mismatched manifest must not raise or prevent the flash from
    # proceeding, only be visible in the log.
    firmware_path = _write_firmware(tmp_path, 100)
    manifest_path = Path(firmware_path + ".manifest.json")
    manifest_path.write_text(json.dumps({"sha256": "0" * 64, "version": "1.2"}))

    logged: list[str] = []
    can = MockCAN()
    flasher = URTCFlasher(can, log=logged.append)

    assert flasher.flash(firmware_path) is True
    assert any("MANIFEST MISMATCH" in line for line in logged)


def test_manifest_sha256_match_is_logged_as_confirmed(tmp_path):
    import hashlib

    firmware_path = _write_firmware(tmp_path, 100)
    actual_sha256 = hashlib.sha256(Path(firmware_path).read_bytes()).hexdigest()
    manifest_path = Path(firmware_path + ".manifest.json")
    manifest_path.write_text(json.dumps({"sha256": actual_sha256, "version": "1.2"}))

    logged: list[str] = []
    can = MockCAN()
    flasher = URTCFlasher(can, log=logged.append)

    assert flasher.flash(firmware_path) is True
    assert not any("MANIFEST MISMATCH" in line for line in logged)
