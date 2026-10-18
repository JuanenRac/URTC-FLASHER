# =============================================================================
# URTC Flasher - tests/test_can_conformance.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The flasher's reading of the CAN protocol, against the shared vectors.

tests/fixtures/can_conformance_vectors.json is a committed copy of the vectors
that the other URTC clients (the Tester and the Web Studio) are checked against
too, so the three implementations are compared with the same expected bytes.
This file only reads its own copy."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import flasher_config  # noqa: E402
import flasher_protocol  # noqa: E402
from flasher_protocol import URTCFlasher  # noqa: E402
from flasher_transports import SLCAN, SLCANError  # noqa: E402

VECTORS = json.loads((Path(__file__).parent / "fixtures" / "can_conformance_vectors.json").read_text(encoding="utf-8"))


class _FakeSerial:
    def __init__(self):
        self.written = b""
        self.incoming = bytearray()

    @property
    def in_waiting(self):
        return len(self.incoming)

    def read(self, count):
        chunk = bytes(self.incoming[:count])
        del self.incoming[:count]
        return chunk

    def write(self, data):
        self.written += data

    def reset_input_buffer(self):
        self.incoming.clear()

    def close(self):
        pass


def _slcan():
    transport = SLCAN.__new__(SLCAN)
    transport.log = lambda message: None
    transport.ser = _FakeSerial()
    transport._rx_buf = b""
    return transport


def _hex(text):
    return bytes.fromhex(text)


def _id(text):
    return int(text, 16)


@pytest.mark.parametrize("entry", [e for e in VECTORS["identifiers"] if "flasher" in e["names"]], ids=lambda entry: entry["id"])
def test_identifiers_match_the_shared_table(entry):
    assert getattr(flasher_config, entry["names"]["flasher"]) == _id(entry["id"])


def test_erase_fram_magic_matches():
    magic = next(m for m in VECTORS["magic_payloads"] if m["name"] == "erase_fram")
    assert flasher_config.ERASE_FRAM_MAGIC == _hex(magic["data"])
    assert flasher_config.CAN_ID_ERASE_FRAM == _id(magic["id"])


class _RecordingCan:
    def __init__(self, answers=()):
        self.sent = []
        self.answers = list(answers)

    def send_frame(self, can_id, data):
        self.sent.append((can_id, bytes(data)))

    def read_frame(self, timeout=0.05):
        if self.answers:
            return self.answers.pop(0)
        time.sleep(min(timeout, 0.005))
        return None


def _flasher(can):
    return URTCFlasher(can, lambda message: None)


def test_bootloader_entry_frame_matches_the_shared_magic():
    magic = next(m for m in VECTORS["magic_payloads"] if m["name"] == "enter_bootloader")
    can = _RecordingCan()
    _flasher(can).trigger_bootloader_entry(timeout=0.05)
    assert can.sent[0] == (_id(magic["id"]), _hex(magic["data"]))


def test_downgrade_authorisation_uses_the_shared_magic():
    magic = next(m for m in VECTORS["magic_payloads"] if m["name"] == "authorize_downgrade")
    source = Path(flasher_protocol.__file__).read_text(encoding="utf-8")
    assert flasher_config.CAN_ID_AUTHORIZE_DOWNGRADE == _id(magic["id"])
    expected = ", ".join(f"0x{byte:02X}" for byte in _hex(magic["data"]))
    assert expected in source or expected.lower() in source.lower()


@pytest.mark.parametrize("vector", VECTORS["slcan_encode"], ids=lambda vector: vector["line"])
def test_slcan_encode(vector):
    transport = _slcan()
    transport.send_frame(_id(vector["id"]), _hex(vector["data"]))
    assert transport.ser.written == vector["line"].encode("ascii") + b"\r"


@pytest.mark.parametrize("vector", VECTORS["slcan_encode_rejected"], ids=lambda vector: vector["id"] + "-" + str(len(vector["data"]) // 2))
def test_slcan_encode_rejected(vector):
    transport = _slcan()
    with pytest.raises(SLCANError):
        transport.send_frame(_id(vector["id"]), _hex(vector["data"]))
    assert transport.ser.written == b""


@pytest.mark.parametrize("vector", VECTORS["slcan_decode"], ids=lambda vector: vector["name"])
def test_slcan_decode(vector):
    transport = _slcan()
    transport.ser.incoming.extend(vector["line"].encode("ascii") + b"\r")
    got = transport.read_frame(timeout=0.05)
    if "note" in vector:
        # Documented, tolerated difference between the readers: only check it does not crash.
        assert got is None or isinstance(got, tuple)
        return
    if vector["frame"] is None:
        assert got is None
    else:
        assert got == (_id(vector["frame"]["id"]), _hex(vector["frame"]["data"]))


def test_status_character_glued_in_front_of_a_frame_does_not_lose_it():
    """Specific to this reader (the Tester drops such a line): an adapter's
    acknowledge character that arrives without its own terminator."""
    transport = _slcan()
    transport.ser.incoming.extend(b"zt1110\r")
    assert transport.read_frame(timeout=0.05) == (0x111, b"")


def _frames_for(vector):
    return [(_id(frame_id), _hex(data)) for frame_id, data in vector["frames"]]


@pytest.mark.parametrize("vector", VECTORS["version_query"], ids=lambda vector: vector["name"])
def test_version_query(vector):
    can = _RecordingCan(_frames_for(vector))
    flasher = _flasher(can)
    result = flasher.query_version(timeout=0.2, patch_grace=0.02)
    assert can.sent[0] == (flasher_config.CAN_ID_QUERY_VERSION, b"\x00")
    expect = vector["expect"]
    if expect is None:
        assert result is None
        return
    assert result["responder"] == expect["responder"]
    assert result["hardware_id"] == _id(expect["hardware_id"])
    assert result["version_major"] == expect["major"]
    assert result["version_minor"] == expect["minor"]
    assert result["version_patch"] == expect["patch"]
    assert result["patch_aware"] is expect["patch_aware"]
    assert result["accepts_patch_in_end_update"] is expect["accepts_patch_in_end_update"]
    if "bootloader" in expect:
        assert result["bootloader_version"] == tuple(expect["bootloader"])


@pytest.mark.parametrize("vector", VECTORS["minor_field"], ids=lambda vector: f"{vector['minor']}-{vector['patch']}-{vector['bootloader_accepts_patch']}")
def test_end_update_minor_field(vector):
    got = URTCFlasher._end_update_minor_field(vector["minor"], vector["patch"], vector["bootloader_accepts_patch"])
    assert got == vector["expect"]
