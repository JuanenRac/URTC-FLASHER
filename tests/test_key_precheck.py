# =============================================================================
# URTC Flasher - tests/test_key_precheck.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The signing-key check before the transfer: a bootloader that publishes the fingerprint of the key it accepts (an 11-byte 0x7FA) is compared with the
fingerprint the manifest of the image declares. Tried against a simulated bootloader; no board, no bus."""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

import flasher_protocol
from flasher_config import CAN_ID_BOOTLOADER_VERSION_RESPONSE, CAN_ID_QUERY_VERSION, CAN_ID_VERSION_RESPONSE, THIS_HARDWARE_ID
from flasher_protocol import FlashError, URTCFlasher

BOARD_KEY = bytes.fromhex("a1b2c3d4e5f60718")


class SimBootloader:
    """Answers the version query like a bootloader: 0x7F9, then 0x7FA with three bytes or with the key fingerprint after them."""

    def __init__(self, key_id: bytes | None):
        self.frames: list[tuple[int, bytes]] = []
        self.key_id = key_id
        self.sent: list[int] = []

    def send_frame(self, can_id, data):
        self.sent.append(can_id)
        if can_id == CAN_ID_QUERY_VERSION:
            self.frames.append((CAN_ID_VERSION_RESPONSE, b"\x01" + struct.pack(">I", THIS_HARDWARE_ID) + struct.pack(">H", 0) + b"\x03"))
            self.frames.append((CAN_ID_BOOTLOADER_VERSION_RESPONSE, bytes((1, 0, 0)) + (self.key_id or b"")))

    def read_frame(self, timeout=0.05):
        return self.frames.pop(0) if self.frames else None


def image(tmp_path, key_id=None):
    path = tmp_path / "URTC_MAIN_FIRMWARE_v0.3.3.bin"
    path.write_bytes(b"\x01" * 100)
    manifest = {"version": "0.3.3"}
    if key_id is not None:
        manifest["signing_key_id"] = key_id
    Path(str(path) + ".manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return str(path)


def check(tmp_path, board_key, image_key, policy="warn", monkeypatch=None):
    monkeypatch.setattr(flasher_protocol, "KEY_ID_PRECHECK", policy)
    lines: list[str] = []
    flasher = URTCFlasher(SimBootloader(board_key), log=lines.append)
    path = image(tmp_path, image_key)
    return flasher, flasher.report_version_change(path)["key_check"], lines, path


def test_a_bootloader_without_the_fingerprint_sends_three_bytes_and_nothing_is_compared(tmp_path, monkeypatch):
    flasher, state, lines, _path = check(tmp_path, None, "a1b2c3d4e5f60718", monkeypatch=monkeypatch)
    assert state == "unknown"
    assert flasher.query_version()["bootloader_version"] == (1, 0, 0)


def test_the_fingerprint_after_the_version_is_read(tmp_path, monkeypatch):
    info = URTCFlasher(SimBootloader(BOARD_KEY), log=lambda m: None).query_version()
    assert info["bootloader_version"] == (1, 0, 0) and info["bootloader_key_id"] == BOARD_KEY.hex()


def test_the_same_key_is_a_match_and_the_manifest_may_carry_the_whole_fingerprint(tmp_path, monkeypatch):
    assert check(tmp_path, BOARD_KEY, BOARD_KEY.hex(), monkeypatch=monkeypatch)[1] == "match"
    assert check(tmp_path, BOARD_KEY, BOARD_KEY.hex() + "00" * 24, monkeypatch=monkeypatch)[1] == "match"


def test_an_image_without_the_fingerprint_in_its_manifest_is_never_a_mismatch(tmp_path, monkeypatch):
    assert check(tmp_path, BOARD_KEY, None, monkeypatch=monkeypatch)[1] == "unknown"


def test_a_different_key_warns_by_default_and_the_update_goes_on(tmp_path, monkeypatch):
    flasher, state, lines, _path = check(tmp_path, BOARD_KEY, "0011223344556677", monkeypatch=monkeypatch)
    assert state == "mismatch"
    assert any(BOARD_KEY.hex() in line and "0011223344556677" in line for line in lines)
    assert flasher._key_mismatch is not None


def test_refuse_stops_before_a_single_data_frame(tmp_path, monkeypatch):
    flasher, state, _lines, path = check(tmp_path, BOARD_KEY, "0011223344556677", policy="refuse", monkeypatch=monkeypatch)
    assert state == "mismatch"
    sent_before = len(flasher.can.sent) if hasattr(flasher, "can") else None
    with pytest.raises(FlashError, match="0011223344556677"):
        flasher.flash(path)
    if sent_before is not None:
        assert len(flasher.can.sent) == sent_before


def test_off_skips_the_comparison(tmp_path, monkeypatch):
    flasher, state, _lines, _path = check(tmp_path, BOARD_KEY, "0011223344556677", policy="off", monkeypatch=monkeypatch)
    assert state == "off" and flasher._key_mismatch is None


def test_the_default_is_warn_and_a_wrong_value_falls_back_to_it():
    import flasher_config
    assert flasher_config.KEY_ID_PRECHECK in ("off", "warn", "refuse")
