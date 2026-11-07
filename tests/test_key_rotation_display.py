# =============================================================================
# URTC Flasher - tests/test_key_rotation_display.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""While a rotation of the signing key is in progress the bootloader trusts two keys. The flasher asks which (0x7EA, operation 05), says both fingerprints in the
log with the minutes left and accepts an image signed with either. Tried against the virtual bootloader with throwaway keys (evidence = simulator); no board, no bus."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import flasher_protocol
from flasher_protocol import URTCFlasher
from urtc_can import ed25519, key_rotation as kr, key_rotation_command as krc, protocol
from urtc_can.virtual_board import VirtualBoard

SEED_A, SEED_B = (hashlib.sha256(b"flasher-rotation-" + x).digest() for x in (b"A", b"B"))
KEY_A, KEY_B = (krc.key_id(ed25519.public_key(s)) for s in (SEED_A, SEED_B))
HOST_TIME = 1_700_000_000


class Bus:
    """The CAN interface the flasher uses, backed by a virtual bootloader."""

    def __init__(self, board):
        self.board = board
        self.pending = []

    def send_frame(self, can_id, data):
        self.pending.extend(self.board.handle(can_id, data))

    def read_frame(self, timeout=0.05):
        return self.pending.pop(0) if self.pending else None


def make_bus(rotated: bool, window=1800, revoked=False) -> Bus:
    trust = krc.Trust({KEY_A: ed25519.public_key(SEED_A), KEY_B: ed25519.public_key(SEED_B)})
    state = krc.State(kr.Rotation(KEY_A, revoked=frozenset({KEY_A}) if revoked else frozenset()), trust, allow=True)
    board = VirtualBoard(bootloader=True, key_rotation=state)
    bus = Bus(board)
    if rotated:
        for chunk in krc.to_chunks(krc.sign(SEED_A, KEY_B, KEY_A, window, HOST_TIME, 1)):
            board.handle(protocol.CAN_ID_BOOTLOADER_SIGNATURE_CHUNK, chunk)
        assert board.last_rotation_result == "ok"
    return bus


def image(tmp_path, key: bytes):
    path = tmp_path / "URTC_MAIN_FIRMWARE_v0.3.3.bin"
    path.write_bytes(b"\x01" * 100)
    Path(str(path) + ".manifest.json").write_text(json.dumps({"version": "0.3.3", "signing_key_id": key.hex()}), encoding="utf-8")
    return str(path)


def run(tmp_path, bus, key, monkeypatch):
    monkeypatch.setattr(flasher_protocol, "KEY_ID_PRECHECK", "warn")
    lines: list[str] = []
    flasher = URTCFlasher(bus, log=lines.append)
    return flasher.report_version_change(image(tmp_path, key)), lines


def test_two_keys_are_shown_with_the_minutes_left(tmp_path, monkeypatch):
    bus = make_bus(rotated=True, window=1800)
    bus.board.advance(60)
    info, lines = run(tmp_path, bus, KEY_B, monkeypatch)
    assert info["key_rotation"]["keys"] == [KEY_B.hex(), KEY_A.hex()] and info["key_rotation"]["rotating"]
    said = "\n".join(lines)
    assert KEY_B.hex() in said and KEY_A.hex() in said and "29" in said
    assert info["key_check"] == "match"


def test_an_image_signed_with_the_previous_key_is_accepted_with_a_warning(tmp_path, monkeypatch):
    info, lines = run(tmp_path, make_bus(rotated=True, window=600), KEY_A, monkeypatch)
    assert info["key_check"] == "match"
    assert any(KEY_A.hex() in line and KEY_B.hex() in line and "10" in line for line in lines)


def test_after_the_window_only_the_new_key_matches(tmp_path, monkeypatch):
    bus = make_bus(rotated=True, window=60)
    bus.board.advance(61)
    info, lines = run(tmp_path, bus, KEY_A, monkeypatch)
    assert info["key_rotation"]["keys"] == [KEY_B.hex()] and info["key_check"] == "mismatch"


def test_without_a_rotation_one_key_is_shown(tmp_path, monkeypatch):
    info, lines = run(tmp_path, make_bus(rotated=False), KEY_A, monkeypatch)
    assert info["key_rotation"]["keys"] == [KEY_A.hex()] and not info["key_rotation"]["rotating"] and info["key_check"] == "match"
    assert any(KEY_A.hex() in line for line in lines)


def test_a_revoked_current_key_is_said_and_nothing_matches(tmp_path, monkeypatch):
    info, lines = run(tmp_path, make_bus(rotated=False, revoked=True), KEY_A, monkeypatch)
    assert info["key_rotation"]["current_revoked"] and info["key_rotation"]["keys"] == []
    assert any("revoked" in line for line in lines)


def test_a_bootloader_that_says_nothing_gives_none():
    class Silent:
        def send_frame(self, can_id, data):
            pass

        def read_frame(self, timeout=0.05):
            return None

    assert URTCFlasher(Silent(), log=lambda _t: None).query_key_rotation(timeout=0.05) is None


def test_two_different_statuses_are_not_attributed_to_anyone():
    class TwoHeads:
        def __init__(self):
            self.queue = [(protocol.CAN_ID_BOOTLOADER_SELECT_RESPONSE, bytes([5, 1, 0, 255, 255, 255, 255])),
                          (protocol.CAN_ID_BOOTLOADER_SELECT_RESPONSE, bytes([5, 2, 1, 0, 0, 0, 60])),
                          (protocol.CAN_ID_BOOTLOADER_KEY_ID, KEY_A), (protocol.CAN_ID_BOOTLOADER_KEY_ID, KEY_B)]

        def send_frame(self, can_id, data):
            pass

        def read_frame(self, timeout=0.05):
            return self.queue.pop(0) if self.queue else None

    assert URTCFlasher(TwoHeads(), log=lambda _t: None).query_key_rotation(timeout=0.3) is None


def test_a_count_that_does_not_match_the_fingerprints_is_ignored():
    class Odd:
        def __init__(self):
            self.queue = [(protocol.CAN_ID_BOOTLOADER_SELECT_RESPONSE, bytes([5, 2, 1, 0, 0, 0, 60])), (protocol.CAN_ID_BOOTLOADER_KEY_ID, KEY_A)]

        def send_frame(self, can_id, data):
            pass

        def read_frame(self, timeout=0.05):
            return self.queue.pop(0) if self.queue else None

    assert URTCFlasher(Odd(), log=lambda _t: None).query_key_rotation(timeout=0.3) is None
