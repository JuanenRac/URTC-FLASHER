# =============================================================================
# URTC Flasher - tests/test_flash_verify_fail_reporting.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""I54's own real acceptance test: "Bootloader falso acepta todos los
bloques pero falla en checksum final: la UI no anuncia exito." -
MockCAN(simulate_failure=...) and flash()'s own 0x05-handling branch were
both already real and correct (see flasher_transports.py's own docstring
and flasher_protocol.py's own STATUS_VERIFY_FAIL branch) - what was
genuinely missing was an automated test actually exercising that path
end-to-end, real firmware bytes included. `--mock-fail` on the CLI let a
human trigger this by hand, but nothing proved it for real on every run.

Every test below drives the exact same `URTCFlasher.flash()` real
callers use (CLI and GUI alike) against a real temp firmware file - no
part of flash() itself is mocked, only the CAN transport underneath it
(MockCAN, itself a real, already-tested simulated peer).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from flasher_config import VERIFY_FAIL_REASONS
from flasher_protocol import FlashError, URTCFlasher
from flasher_transports import MockCAN


def _write_firmware(tmp_path: Path, size: int = 100) -> str:
    # Real bytes, not all zero - closer to a real compiled image than an
    # all-zero buffer, though flash()'s own logic never actually inspects
    # content beyond size/CRC/HMAC either way.
    firmware_path = tmp_path / "firmware.bin"
    firmware_path.write_bytes(bytes((i % 251) + 1 for i in range(size)))
    return str(firmware_path)


def test_all_pages_accepted_then_a_real_verify_failure_never_reports_success(tmp_path):
    firmware_path = _write_firmware(tmp_path)
    can = MockCAN(simulate_failure=0x03)  # HMAC signature mismatch
    reported_progress: list[int] = []
    flasher = URTCFlasher(can, log=lambda msg: None, progress_cb=reported_progress.append)

    with pytest.raises(FlashError) as exc_info:
        flasher.flash(firmware_path)

    # The real, human-readable reason (not just the raw status byte) must
    # reach whoever called flash() - a caller-facing message that just
    # says "failed" would be a real regression of what this exception
    # already carries.
    assert VERIFY_FAIL_REASONS[0x03] in str(exc_info.value)
    # This is the acceptance criterion itself: every real byte of the
    # firmware was accepted (progress reached 70%, the page-transfer
    # phase's own real ceiling - see flash()'s own comment on why it
    # never uses 100% for that phase), but 100% - "verified" - must never
    # appear when the bootloader's own final verification genuinely
    # failed.
    assert 70 in reported_progress
    assert 100 not in reported_progress


def test_a_real_successful_verification_does_reach_100_percent(tmp_path):
    # The necessary positive control for the test above: without this,
    # "100 not in reported_progress" could pass merely because nothing in
    # this test suite ever calls progress_cb(100) at all, not because
    # flash() genuinely withholds it on failure specifically.
    firmware_path = _write_firmware(tmp_path)
    can = MockCAN()  # no simulate_failure - real STATUS_VERIFY_OK (0x04) path
    reported_progress: list[int] = []
    flasher = URTCFlasher(can, log=lambda msg: None, progress_cb=reported_progress.append)

    result = flasher.flash(firmware_path)

    assert result is True
    assert 100 in reported_progress


@pytest.mark.parametrize("reason_code", sorted(VERIFY_FAIL_REASONS))
def test_every_real_documented_verify_fail_reason_is_reported_honestly(tmp_path, reason_code):
    # Not just the one reason a human happened to pick with --mock-fail -
    # every real VERIFY_FAIL_REASONS entry this project itself documents
    # (CANBUS.TXT) must surface its own real text, never a generic
    # "verification failed" that hides which of the 5 real causes it was.
    firmware_path = _write_firmware(tmp_path)
    can = MockCAN(simulate_failure=reason_code)
    flasher = URTCFlasher(can, log=lambda msg: None)

    with pytest.raises(FlashError) as exc_info:
        flasher.flash(firmware_path)

    assert VERIFY_FAIL_REASONS[reason_code] in str(exc_info.value)


def test_an_unknown_verify_fail_reason_byte_is_still_reported_not_swallowed(tmp_path):
    # A real bootloader could in principle send a reason byte this
    # tool's own VERIFY_FAIL_REASONS doesn't recognize yet (a future
    # firmware revision adding a new one) - flash() must still raise with
    # SOME real explanation, never silently claim success just because
    # the specific byte was unrecognized.
    firmware_path = _write_firmware(tmp_path)
    unknown_reason = 0x99
    assert unknown_reason not in VERIFY_FAIL_REASONS
    can = MockCAN(simulate_failure=unknown_reason)
    flasher = URTCFlasher(can, log=lambda msg: None)

    with pytest.raises(FlashError, match=r"0x99"):
        flasher.flash(firmware_path)
