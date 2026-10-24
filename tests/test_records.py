# =============================================================================
# URTC Flasher - tests/test_records.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Session logs (where, how many) and the JSON report written after an update, and the
choice of an official image for a board that has no firmware."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flasher_config import THIS_HARDWARE_ID
from flasher_records import (
    build_update_report, find_recovery_image, prune_session_logs, sign_update_report, verify_signed_report, verify_update_report,
    writable_logs_folder, write_update_report,
)


def test_the_logs_folder_next_to_the_program_is_used_when_it_is_writable(tmp_path):
    assert writable_logs_folder(str(tmp_path / "logs"), str(tmp_path / "fallback")) == str(tmp_path / "logs")


def test_a_per_user_folder_is_used_when_the_preferred_one_cannot_be_written(tmp_path):
    blocked = tmp_path / "file-not-folder"
    blocked.write_text("x")
    assert writable_logs_folder(str(blocked / "logs"), str(tmp_path / "fallback")) == str(tmp_path / "fallback")


def test_no_folder_at_all_gives_none(tmp_path):
    blocked = tmp_path / "f"
    blocked.write_text("x")
    assert writable_logs_folder(str(blocked / "a"), str(blocked / "b")) is None


def test_only_the_newest_session_logs_are_kept(tmp_path):
    for n in range(8):
        log = tmp_path / f"urtc_flasher_2000010{n}_000000.log"
        log.write_text("x")
        os.utime(log, (1000 + n, 1000 + n))
    other = tmp_path / "urtc_update_report_x.json"
    other.write_text("{}")
    assert prune_session_logs(str(tmp_path), keep=3) == 5
    assert sorted(p.name for p in tmp_path.glob("urtc_flasher_*.log")) == [
        "urtc_flasher_20000105_000000.log", "urtc_flasher_20000106_000000.log", "urtc_flasher_20000107_000000.log"]
    assert other.exists()  # reports are never pruned


def _report(**over):
    args = dict(tool_version="0.2.8", image_path="x/URTC_MAIN_FIRMWARE_v0.3.3.bin", image_sha256="ab" * 32, image_size=73476,
                target="master", installed=(0, 2), new=(0, 3), hardware_id=THIS_HARDWARE_ID, signing_key_kind="dev",
                result="success", operator="bench", timestamp="T")
    args.update(over)
    return build_update_report(**args)


def test_the_report_records_what_changed_and_carries_its_own_digest():
    report = _report()
    assert report["version_before"] == "0.2" and report["version_after"] == "0.3"
    assert report["image"] == {"file": "URTC_MAIN_FIRMWARE_v0.3.3.bin", "size": 73476, "sha256": "ab" * 32, "signing_key_kind": "dev"}
    assert report["operator"] == "bench" and report["hardware_id"] == f"0x{THIS_HARDWARE_ID:08X}"
    assert verify_update_report(report)
    report["version_after"] = "9.9"
    assert not verify_update_report(report)  # an edited report is noticed


def test_an_unknown_installed_version_is_null():
    assert _report(installed=None)["version_before"] is None


def test_the_report_is_written_as_json_and_never_overwrites(tmp_path):
    first = write_update_report(_report(), str(tmp_path))
    second = write_update_report(_report(), str(tmp_path))
    assert first != second and Path(first).exists() and Path(second).exists()
    assert verify_update_report(json.loads(Path(first).read_text(encoding="utf-8")))


def _official(folder, name, version, component="main_application", hardware_id=THIS_HARDWARE_ID):
    path = Path(folder) / name
    path.write_bytes(b"\x01" * 16)
    Path(str(path) + ".manifest.json").write_text(
        json.dumps({"component": component, "version": version, "hardware_id": f"0x{hardware_id:08X}"}), encoding="utf-8")
    return str(path)


def test_the_newest_main_board_image_is_chosen_for_a_board_without_firmware(tmp_path):
    _official(tmp_path, "URTC_MAIN_FIRMWARE_v0.3.3.bin", "0.3.3")
    newest = _official(tmp_path, "URTC_MAIN_FIRMWARE_v0.3.10.bin", "0.3.10")
    _official(tmp_path, "URTC_MAIN_BOOTLOADER_v9.9.bin", "9.9")
    _official(tmp_path, "URTC_SLAVE_FIRMWARE_v9.9.bin", "9.9", component="slave_application", hardware_id=0x0303CB01)
    assert find_recovery_image(str(tmp_path), THIS_HARDWARE_ID) == newest


def test_no_suitable_image_gives_none(tmp_path):
    _official(tmp_path, "URTC_SLAVE_FIRMWARE_v1.0.bin", "1.0", component="slave_application")
    (tmp_path / "loose.bin").write_bytes(b"x")
    assert find_recovery_image(str(tmp_path), THIS_HARDWARE_ID) is None
    assert find_recovery_image(str(tmp_path / "missing"), THIS_HARDWARE_ID) is None


def test_a_report_signed_with_the_key_of_the_user_shows_any_edit(tmp_path):
    key = str(tmp_path / "records.key")
    signed = sign_update_report(_report(), key)
    assert signed["signature"]["algorithm"] == "Ed25519" and verify_update_report(signed)
    assert verify_signed_report(signed)
    assert sign_update_report(_report(), key)["signature"]["public_key"] == signed["signature"]["public_key"]  # the key is reused
    edited = dict(signed, result="failed")
    assert not verify_signed_report(edited)
    # rewriting the digest to match the edit does not help: the signature covered the old one
    from flasher_records import _report_digest
    edited["report_sha256"] = _report_digest(edited)
    assert verify_update_report(edited) and not verify_signed_report(edited)
    assert not verify_signed_report(_report())  # an unsigned report is not a signed one
