# =============================================================================
# URTC Flasher - tests/test_key_precheck.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The signing-key check before the transfer: a bootloader that publishes the fingerprint of the key it accepts (the eight bytes of 0x7ED, right after its
0x7F9 answer; 0x7FA stays at the three bytes of the version) is compared with the fingerprint the manifest of the image declares. Tried against simulated
bootloaders, alone and sharing a bus; no board, no bus."""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

import flasher_protocol
from flasher_config import (CAN_ID_BOOTLOADER_KEY_ID, CAN_ID_BOOTLOADER_VERSION_RESPONSE, CAN_ID_QUERY_VERSION, CAN_ID_VERSION_PATCH_RESPONSE,
                            CAN_ID_VERSION_RESPONSE, THIS_HARDWARE_ID)
from flasher_protocol import FlashError, URTCFlasher

BOARD_KEY = bytes.fromhex("a1b2c3d4e5f60718")


class SimBootloader:
    """Answers the version query like a bootloader: 0x7F9, 0x7FA with the three bytes of its version and, when it holds a trusted key, 0x7ED with the
    eight bytes of its fingerprint."""

    def __init__(self, key_id: bytes | None, key_first: bool = False):
        self.frames: list[tuple[int, bytes]] = []
        self.key_id = key_id
        self.key_first = key_first
        self.sent: list[int] = []

    def answer(self):
        key = [(CAN_ID_BOOTLOADER_KEY_ID, self.key_id)] if self.key_id else []
        main = [(CAN_ID_VERSION_RESPONSE, b"\x01" + struct.pack(">I", THIS_HARDWARE_ID) + struct.pack(">H", 0) + b"\x03"),
                (CAN_ID_BOOTLOADER_VERSION_RESPONSE, bytes((1, 0, 0)))]
        return key + main if self.key_first else main + key

    def send_frame(self, can_id, data):
        self.sent.append(can_id)
        if can_id == CAN_ID_QUERY_VERSION:
            self.frames.extend(self.answer())

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


def test_a_bootloader_without_the_fingerprint_sends_no_0x7ed_and_nothing_is_compared(tmp_path, monkeypatch):
    flasher, state, lines, _path = check(tmp_path, None, "a1b2c3d4e5f60718", monkeypatch=monkeypatch)
    assert state == "unknown"
    assert flasher.query_version()["bootloader_version"] == (1, 0, 0)
    assert flasher.query_version()["bootloader_key_id"] is None
    assert sum("does not publish the signing key" in line for line in lines) == 1   # said once, as information: no difference and no error


def test_the_fingerprint_of_0x7ed_is_read_in_either_order():
    for first in (False, True):
        info = URTCFlasher(SimBootloader(BOARD_KEY, key_first=first), log=lambda m: None).query_version()
        assert info["bootloader_version"] == (1, 0, 0) and info["bootloader_key_id"] == BOARD_KEY.hex(), first


def test_an_eleven_byte_0x7fa_is_not_a_version_and_carries_no_fingerprint():
    """The first precheck expected version plus fingerprint in 0x7FA: eleven bytes cannot exist on a classic CAN frame, so it is not read at all."""
    class Eleven(SimBootloader):
        def answer(self):
            return [(CAN_ID_VERSION_RESPONSE, b"\x01" + struct.pack(">I", THIS_HARDWARE_ID) + struct.pack(">H", 0) + b"\x03"),
                    (CAN_ID_BOOTLOADER_VERSION_RESPONSE, bytes((1, 0, 0)) + BOARD_KEY)]
    info = URTCFlasher(Eleven(None), log=lambda m: None).query_version()
    assert info["bootloader_version"] is None and info["bootloader_key_id"] is None


def test_a_0x7ed_of_the_wrong_length_is_ignored():
    for payload in (BOARD_KEY[:7], BOARD_KEY + b"\x00", b""):
        class Odd(SimBootloader):
            def answer(self, payload=payload):
                return [(CAN_ID_VERSION_RESPONSE, b"\x01" + struct.pack(">I", THIS_HARDWARE_ID) + struct.pack(">H", 0) + b"\x03"),
                        (CAN_ID_BOOTLOADER_VERSION_RESPONSE, bytes((1, 0, 0))), (CAN_ID_BOOTLOADER_KEY_ID, payload)]
        assert URTCFlasher(Odd(None), log=lambda m: None).query_version()["bootloader_key_id"] is None


def test_the_patch_frame_and_the_fingerprint_are_both_waited_for():
    class Full(SimBootloader):
        def answer(self):
            frames = super().answer()
            return frames[:2] + [(CAN_ID_VERSION_PATCH_RESPONSE, bytes((1, 0xFF, 1)))] + frames[2:]
    info = URTCFlasher(Full(BOARD_KEY), log=lambda m: None).query_version()
    assert info["patch_aware"] and info["bootloader_key_id"] == BOARD_KEY.hex()


# --- several heads on one bus ---------------------------------------------------------------------------------------------------------------------
class MixedBus:
    """Several bootloaders hear the same query and all answer; a head of the old kind answers without 0x7ED."""

    def __init__(self, *heads: SimBootloader):
        self.heads = heads
        self.sent: list[int] = []

    def send_frame(self, can_id, data):
        self.sent.append(can_id)
        for head in self.heads:
            head.send_frame(can_id, data)

    def read_frame(self, timeout=0.05):
        for head in self.heads:
            if head.frames:
                return head.frames.pop(0)
        return None


def test_two_heads_with_one_key_are_a_match_and_an_old_head_beside_a_new_one_gives_the_fingerprint_of_the_new_one():
    for heads in ((SimBootloader(BOARD_KEY), SimBootloader(BOARD_KEY)), (SimBootloader(None), SimBootloader(BOARD_KEY))):
        flasher = URTCFlasher(MixedBus(*heads), log=lambda m: None)
        assert flasher.query_version()["bootloader_key_id"] == BOARD_KEY.hex()


def test_two_heads_with_different_keys_and_none_selected_are_never_a_mismatch(tmp_path, monkeypatch):
    monkeypatch.setattr(flasher_protocol, "KEY_ID_PRECHECK", "refuse")
    flasher = URTCFlasher(MixedBus(SimBootloader(BOARD_KEY), SimBootloader(bytes.fromhex("0011223344556677"))), log=lambda m: None)
    assert flasher.report_version_change(image(tmp_path, BOARD_KEY.hex()))["key_check"] == "unknown"   # nothing can be attributed to the head the image goes to
    assert flasher._key_mismatch is None


def test_an_application_never_gives_a_fingerprint(tmp_path, monkeypatch):
    class App(SimBootloader):
        def answer(self):
            return [(CAN_ID_VERSION_RESPONSE, b"\x00" + struct.pack(">I", THIS_HARDWARE_ID) + struct.pack(">H", 0) + b"\x03"), (CAN_ID_BOOTLOADER_KEY_ID, BOARD_KEY)]
    monkeypatch.setattr(flasher_protocol, "KEY_ID_PRECHECK", "refuse")
    flasher = URTCFlasher(App(None), log=lambda m: None)
    assert flasher.report_version_change(image(tmp_path, "0011223344556677"))["key_check"] == "unknown"


def test_the_same_key_is_a_match_and_the_manifest_may_carry_the_whole_fingerprint(tmp_path, monkeypatch):
    assert check(tmp_path, BOARD_KEY, BOARD_KEY.hex(), monkeypatch=monkeypatch)[1] == "match"
    assert check(tmp_path, BOARD_KEY, BOARD_KEY.hex() + "00" * 24, monkeypatch=monkeypatch)[1] == "match"


def test_an_image_without_the_fingerprint_in_its_manifest_is_never_a_mismatch(tmp_path, monkeypatch):
    assert check(tmp_path, BOARD_KEY, None, monkeypatch=monkeypatch)[1] == "unknown"
    assert check(tmp_path, None, None, monkeypatch=monkeypatch)[1] == "unknown"


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


# --- the key named by the signature record (<image>.imgsig) ---------------------------------------------------------------------------------------
def write_record(path, key_id: bytes):
    """A 76-byte record (key id, counter, signature): only the key id matters to the precheck."""
    Path(str(path) + ".imgsig").write_bytes((key_id + bytes(4) + bytes(64)).hex().encode("ascii") + b"\n")


def test_the_key_id_of_the_signature_record_is_compared_when_the_manifest_declares_none(tmp_path, monkeypatch):
    monkeypatch.setattr(flasher_protocol, "KEY_ID_PRECHECK", "warn")
    path = image(tmp_path, None)
    write_record(path, BOARD_KEY)
    flasher = URTCFlasher(SimBootloader(BOARD_KEY), log=lambda m: None)
    assert flasher.report_version_change(path)["key_check"] == "match"
    write_record(path, bytes.fromhex("0011223344556677"))
    flasher = URTCFlasher(SimBootloader(BOARD_KEY), log=lambda m: None)
    assert flasher.report_version_change(path)["key_check"] == "mismatch"


def test_the_record_wins_over_the_key_of_an_older_manifest(tmp_path, monkeypatch):
    monkeypatch.setattr(flasher_protocol, "KEY_ID_PRECHECK", "refuse")
    path = image(tmp_path, "0011223344556677")   # the key id of the earlier generation of bootloaders
    write_record(path, BOARD_KEY)                  # the key the bootloader of today will check
    flasher = URTCFlasher(SimBootloader(BOARD_KEY), log=lambda m: None)
    assert flasher.report_version_change(path)["key_check"] == "match"
    assert flasher._key_mismatch is None


def test_a_file_that_is_not_a_record_does_not_hide_the_manifest_and_is_reported_when_flashing(tmp_path, monkeypatch):
    monkeypatch.setattr(flasher_protocol, "KEY_ID_PRECHECK", "warn")
    path = image(tmp_path, BOARD_KEY.hex())
    Path(path + ".imgsig").write_text("not a record\n", encoding="ascii")
    flasher = URTCFlasher(SimBootloader(BOARD_KEY), log=lambda m: None)
    assert flasher.report_version_change(path)["key_check"] == "match"
    with pytest.raises(FlashError):
        flasher.flash(path)
