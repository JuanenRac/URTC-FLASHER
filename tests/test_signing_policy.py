# =============================================================================
# URTC Flasher - tests/test_signing_policy.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""An image signed with the PUBLIC development key is flagged, and in "production only"
mode it is refused before a single frame is sent."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

import flasher_protocol
from flasher_config import THIS_HARDWARE_ID
from flasher_integrity import manifest_signing_kind
from flasher_protocol import FlashError, URTCFlasher
from flasher_transports import MockCAN


def _image(tmp_path, kind):
    path = tmp_path / "URTC_MAIN_FIRMWARE_v0.3.3.bin"
    data = bytes((i % 251) + 1 for i in range(3000))
    path.write_bytes(data)
    manifest = {
        "component": "main_application", "hardware_id": f"0x{THIS_HARDWARE_ID:08X}", "version": "0.3.3",
        "sha256": hashlib.sha256(data).hexdigest(), "hmac_sha256": "ab" * 32,
    }
    if kind is not None:
        manifest["signing_key_kind"] = kind
    Path(str(path) + ".manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return str(path)


class _Silent:
    def send_frame(self, can_id, data):
        raise AssertionError("a frame was sent")

    def read_frame(self, timeout=0.05):
        return None


@pytest.mark.parametrize("kind,expected", [("dev", "dev"), ("DEV", "dev"), ("production", "production"), (None, None)])
def test_manifest_signing_kind(tmp_path, kind, expected):
    assert manifest_signing_kind(_image(tmp_path, kind)) == expected


def test_manifest_signing_kind_without_a_manifest_is_none(tmp_path):
    assert manifest_signing_kind(str(tmp_path / "nothing.bin")) is None


def test_production_only_mode_refuses_a_development_signature_before_any_traffic(tmp_path, monkeypatch):
    monkeypatch.setattr(flasher_protocol, "REQUIRE_PRODUCTION_SIGNATURE", True)
    with pytest.raises(FlashError, match="development key"):
        URTCFlasher(_Silent(), log=lambda m: None).flash(_image(tmp_path, "dev"))


def test_production_only_mode_still_accepts_a_production_signature(tmp_path, monkeypatch):
    monkeypatch.setattr(flasher_protocol, "REQUIRE_PRODUCTION_SIGNATURE", True)
    assert URTCFlasher(MockCAN(), log=lambda m: None).flash(_image(tmp_path, "production")) is True


def test_by_default_a_development_signature_is_accepted_and_noted_in_the_log(tmp_path):
    lines = []
    assert URTCFlasher(MockCAN(), log=lines.append).flash(_image(tmp_path, "dev")) is True
    assert any("development key" in line for line in lines)
