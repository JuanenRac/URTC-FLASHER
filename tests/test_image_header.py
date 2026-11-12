# =============================================================================
# URTC Flasher - tests/test_image_header.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The header inside the image: what the flasher reads from a file before it sends a frame, and the switch for an image that has none."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import flasher_config as cfg
import flasher_protocol
from flasher_protocol import FlashError, URTCFlasher
from urtc_can import image_header as ih

VECTORS = json.loads((Path(__file__).resolve().parent.parent / "urtc_can" / "image_header_embedded_vectors.json").read_text(encoding="utf-8"))


class Bus:
    def __init__(self):
        self.sent = []

    def send_frame(self, can_id, data):
        self.sent.append((can_id, bytes(data)))


def _binary(hardware=None, version=(0, 8, 1, 3), length=768):
    raw = bytearray((i * 31 + 7) & 0x7F for i in range(length))
    raw[ih.EMBED_OFFSET:ih.EMBED_OFFSET + 32] = ih.embedded_slot(cfg.THIS_HARDWARE_ID if hardware is None else hardware, version)
    return bytes(raw)


def _flasher(log):
    return URTCFlasher(Bus(), log=log.append)


def _check(tmp_path, data, name="URTC_MAIN_FIRMWARE_v0.8.1.3.bin", hardware=None):
    log = []
    path = tmp_path / name
    path.write_bytes(data)
    flasher = _flasher(log)
    result = flasher._check_image_header(str(path), data, cfg.THIS_HARDWARE_ID if hardware is None else hardware)
    return result, log, flasher.can.sent


def test_a_sealed_image_is_accepted_and_its_identity_is_logged(tmp_path):
    result, log, sent = _check(tmp_path, ih.seal_embedded(_binary()))
    assert result.accepted and result.info.version == (0, 8, 1, 3) and sent == []
    assert any("0.8.1.3" in line and "768" in line for line in log)


def test_an_image_for_another_board_is_refused_before_a_frame_is_sent(tmp_path):
    with pytest.raises(FlashError) as error:
        _check(tmp_path, ih.seal_embedded(_binary(hardware=cfg.SLAVE_HARDWARE_ID)))
    assert f"0x{cfg.SLAVE_HARDWARE_ID:08X}" in str(error.value) and f"0x{cfg.THIS_HARDWARE_ID:08X}" in str(error.value)


def test_a_header_that_says_another_version_than_the_file_name_is_refused(tmp_path):
    with pytest.raises(FlashError) as error:
        _check(tmp_path, ih.seal_embedded(_binary()), name="URTC_MAIN_FIRMWARE_v0.8.2.bin")
    assert "0.8.1.3" in str(error.value) and "0.8.2" in str(error.value)
    _check(tmp_path, ih.seal_embedded(_binary()), name="URTC_MAIN_FIRMWARE_v0.8.1.bin")   # three parts: the first three are compared
    _check(tmp_path, ih.seal_embedded(_binary()), name="firmware_v1.2.bin")               # two parts: the name says nothing about the build


@pytest.mark.parametrize("damage", ["code", "unsealed", "length"])
def test_a_broken_header_is_always_refused_whatever_the_switch(tmp_path, monkeypatch, damage):
    sealed = bytearray(ih.seal_embedded(_binary()))
    data = {"code": lambda: bytes(sealed[:700]) + bytes([sealed[700] ^ 1]) + bytes(sealed[701:]), "unsealed": _binary, "length": lambda: bytes(sealed) + b"\0"}[damage]()
    for policy in ih.POLICIES:
        monkeypatch.setattr(flasher_protocol, "IMAGE_HEADER_POLICY", policy)
        with pytest.raises(FlashError):
            _check(tmp_path, data)


def test_an_image_without_a_header_follows_the_switch(tmp_path, monkeypatch):
    plain = bytes((i * 31 + 7) & 0x7F for i in range(768))
    monkeypatch.setattr(flasher_protocol, "IMAGE_HEADER_POLICY", "warn")
    result, log, _sent = _check(tmp_path, plain)
    assert result.accepted and result.warn and any("no header" in line.lower() for line in log)
    monkeypatch.setattr(flasher_protocol, "IMAGE_HEADER_POLICY", "accept")
    result, log, _sent = _check(tmp_path, plain)
    assert result.accepted and not result.warn and log == []
    monkeypatch.setattr(flasher_protocol, "IMAGE_HEADER_POLICY", "require")
    with pytest.raises(FlashError, match="requires"):
        _check(tmp_path, plain)


def test_a_stamped_file_is_not_an_image_to_flash(tmp_path):
    stamped = ih.build_image(bytes(range(200)), cfg.THIS_HARDWARE_ID, (0, 8, 1, 3))
    with pytest.raises(FlashError, match=r"\.bin"):
        _check(tmp_path, stamped, name="URTC_MAIN_FIRMWARE_v0.8.1.3.urimg")


def test_the_configured_switch_is_read_from_the_config_file_and_a_typo_is_the_strictest():
    assert ih.parse_policy(None) == "warn"
    assert ih.parse_policy("Require") == "require" and ih.parse_policy("requires") == "require"
    assert cfg.IMAGE_HEADER_POLICY in ih.POLICIES


def test_every_message_of_the_check_exists_in_the_eight_languages():
    language_dir = Path(__file__).resolve().parent.parent / "language"
    keys = ["LOG_IMAGE_HEADER_OK", "LOG_IMAGE_HEADER_NONE", "ERR_IMAGE_HEADER_BAD", "ERR_IMAGE_HEADER_HARDWARE", "ERR_IMAGE_HEADER_VERSION",
            "ERR_IMAGE_HEADER_REQUIRED", "ERR_IMAGE_HEADER_STAMPED"] + list(flasher_protocol.IMAGE_HEADER_REASON_KEYS.values())
    files = sorted(language_dir.glob("*.lng"))
    assert len(files) == 8
    for path in files:
        text = path.read_text(encoding="utf-8")
        for key in keys:
            assert f"\n{key}=" in text, f"{path.name} lacks {key}"
    assert set(flasher_protocol.IMAGE_HEADER_REASON_KEYS) == set(ih.STATUS_NAMES) - {"ok"}


def test_the_decisions_of_the_shared_vectors_hold_here_too():
    for case in VECTORS["policy_cases"]:
        version = tuple(case["version"]) if case["version"] else None
        check = ih.inspect_image(bytes.fromhex(case["image"]), case["policy"], case["hardware_id"], version)
        assert (check.accepted, check.kind, check.reason) == (case["accepted"], case["kind"], case["reason"]), case["name"]
