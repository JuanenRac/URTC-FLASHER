# =============================================================================
# URTC Flasher - tests/test_imgsig_precheck.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The signature record of an image is checked on this computer before the transfer: against the pinned table of public keys, with records made with the public
development seed (the one a bench bootloader trusts). No board, no bus."""
from __future__ import annotations

import hashlib
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

import flasher_image_trust as trust
import flasher_protocol
from flasher_config import SLAVE_HARDWARE_ID, THIS_HARDWARE_ID
from flasher_protocol import FlashError, URTCFlasher
from urtc_can import ed25519

DEV_SEED = hashlib.sha256(b"urtc public development image key v1").digest()
NAME = "URTC_MAIN_FIRMWARE_v0.8.0.1.bin"
VERSION = (0, 8, 0, 1)
IMAGE = bytes(range(256)) * 3


def record_for(seed=DEV_SEED, image=IMAGE, hardware=THIS_HARDWARE_ID, version=VERSION, counter=7):
    kid = trust.key_id(ed25519.public_key(seed))
    message = b"URTC-IMG-SIG-V1\x00" + trust.header28(image, hardware, version) + hashlib.sha256(image).digest() + struct.pack(">I", counter) + kid
    return kid + struct.pack(">I", counter) + ed25519.sign(seed, message)


def test_the_pinned_keys_are_the_ones_of_the_trust_table_of_the_bootloaders():
    ids = {name: trust.key_id(bytes.fromhex(public)).hex() for name, public in trust.PINNED_KEYS}
    assert ids == {"release current": "97c7dc7915767823", "release next": "1901dcd29e353430", "development": "fe58bb1362df0ea6"}
    assert ed25519.public_key(DEV_SEED).hex() == dict(trust.PINNED_KEYS)["development"]


def test_a_record_that_belongs_to_the_image_verifies():
    assert trust.verify_record(record_for(), IMAGE, THIS_HARDWARE_ID, VERSION) == trust.OK
    assert trust.key_name(record_for()) == "development"
    assert trust.counter_of(record_for(counter=9)) == 9


def test_a_record_of_another_image_or_hardware_or_version_does_not_verify():
    record = record_for()
    assert trust.verify_record(record, IMAGE[:-1] + b"\x00", THIS_HARDWARE_ID, VERSION) == trust.BAD_SIGNATURE
    assert trust.verify_record(record, IMAGE, SLAVE_HARDWARE_ID, VERSION) == trust.BAD_SIGNATURE
    assert trust.verify_record(record, IMAGE, THIS_HARDWARE_ID, (0, 8, 0, 2)) == trust.BAD_SIGNATURE
    flipped = bytearray(record)
    flipped[-1] ^= 1
    assert trust.verify_record(bytes(flipped), IMAGE, THIS_HARDWARE_ID, VERSION) == trust.BAD_SIGNATURE
    counter_changed = bytearray(record)
    counter_changed[11] ^= 1
    assert trust.verify_record(bytes(counter_changed), IMAGE, THIS_HARDWARE_ID, VERSION) == trust.BAD_SIGNATURE
    assert trust.verify_record(record[:-1], IMAGE, THIS_HARDWARE_ID, VERSION) == trust.BAD_SIGNATURE


def test_a_record_of_a_key_the_table_does_not_hold_is_an_unknown_key():
    stranger = hashlib.sha256(b"a key nobody pinned").digest()
    record = record_for(seed=stranger)
    assert trust.verify_record(record, IMAGE, THIS_HARDWARE_ID, VERSION) == trust.UNKNOWN_KEY
    assert trust.key_name(record) == ""


def test_the_version_is_read_from_the_name_of_the_image():
    assert trust.version_from_name("URTC_MAIN_FIRMWARE_v0.8.0.1.bin") == (0, 8, 0, 1)
    assert trust.version_from_name("URTC_MAIN_FIRMWARE_v0.3.3.bin") == (0, 3, 3, 0)
    assert trust.version_from_name("URTC_SLAVE_FIRMWARE_v1.2.3.HEX") == (1, 2, 3, 0)
    assert trust.version_from_name("firmware.bin") is None


def flasher(monkeypatch, policy):
    monkeypatch.setattr(flasher_protocol, "IMGSIG_PRECHECK", policy)
    lines: list[str] = []
    return URTCFlasher(object(), log=lines.append), lines


def test_by_default_a_record_that_does_not_verify_is_said_and_the_transfer_goes_on(monkeypatch, tmp_path):
    flash, lines = flasher(monkeypatch, "warn")
    path = str(tmp_path / NAME)
    assert flash._check_record_signature(path, IMAGE[:-1] + b"\x01", record_for(), THIS_HARDWARE_ID) == trust.BAD_SIGNATURE
    assert len(lines) == 1 and NAME + ".imgsig" in lines[0] and "imgsig_precheck" in lines[0]
    flash, lines = flasher(monkeypatch, "warn")
    assert flash._check_record_signature(path, IMAGE, record_for(seed=hashlib.sha256(b"x").digest()), THIS_HARDWARE_ID) == trust.UNKNOWN_KEY
    assert len(lines) == 1 and "imgsig_precheck" in lines[0]


def test_a_record_that_verifies_is_said_once(monkeypatch, tmp_path):
    flash, lines = flasher(monkeypatch, "warn")
    assert flash._check_record_signature(str(tmp_path / NAME), IMAGE, record_for(), THIS_HARDWARE_ID) == trust.OK
    assert len(lines) == 1 and "development" in lines[0]


def test_with_refuse_a_record_that_does_not_verify_stops_the_flash_before_anything_is_sent(monkeypatch, tmp_path):
    flash, lines = flasher(monkeypatch, "refuse")
    with pytest.raises(FlashError) as stopped:
        flash._check_record_signature(str(tmp_path / NAME), IMAGE[:-1] + b"\x01", record_for(), THIS_HARDWARE_ID)
    assert NAME + ".imgsig" in str(stopped.value) and "imgsig_precheck" in str(stopped.value)
    assert lines == []
    # a record that verifies passes in the same mode
    assert flash._check_record_signature(str(tmp_path / NAME), IMAGE, record_for(), THIS_HARDWARE_ID) == trust.OK


def test_switched_off_or_without_a_record_or_a_version_nothing_is_checked(monkeypatch, tmp_path):
    flash, lines = flasher(monkeypatch, "off")
    assert flash._check_record_signature(str(tmp_path / NAME), IMAGE[:-1], record_for(), THIS_HARDWARE_ID) == "off"
    flash, lines = flasher(monkeypatch, "refuse")
    assert flash._check_record_signature(str(tmp_path / NAME), IMAGE, None, THIS_HARDWARE_ID) == "off"
    assert flash._check_record_signature(str(tmp_path / "firmware.bin"), IMAGE[:-1], record_for(), THIS_HARDWARE_ID) == "unknown"
    assert lines == []


def test_the_setting_is_read_from_the_configuration_and_only_the_known_words_count():
    import flasher_config
    assert flasher_config.IMGSIG_PRECHECK in ("off", "warn", "refuse")
