# =============================================================================
# URTC Flasher - tests/test_firmware_signature.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Which signature goes to the bootloader (see URTC docs/FIRMWARE_SIGNING.TXT):
the one published in <image>.manifest.json; a locally computed one only with
a configured bench key; otherwise the flash is refused before any bus
traffic. Also checks preflight_image() against the published digests and
that the bundled firmware/ is exactly what URTC published."""
from __future__ import annotations

import hashlib
import hmac
import json
import subprocess
import sys
from pathlib import Path

import pytest

import flasher_protocol
from flasher_integrity import preflight_image
from flasher_protocol import FlashError, URTCFlasher
from flasher_transports import MockCAN

ROOT = Path(__file__).resolve().parent.parent


class _RecordingCAN(MockCAN):
    def __init__(self):
        super().__init__()
        self.sent = []

    def send_frame(self, can_id, data):
        self.sent.append((can_id, bytes(data)))
        return super().send_frame(can_id, data)


class _ExplodingCAN:
    def send_frame(self, can_id, data):
        raise AssertionError(f"sent 0x{can_id:X} although the image should have been refused")

    def read_frame(self, timeout=0.05):
        raise AssertionError("waited for a reply although the image should have been refused")


def _image(tmp_path: Path, size: int = 4096) -> Path:
    path = tmp_path / "URTC_MAIN_FIRMWARE_v9.9.9.bin"
    path.write_bytes(bytes((i * 7 + 3) % 256 for i in range(size)))
    return path


def _publish(path: Path, signature: bytes | None, sha256: str | None = None) -> None:
    manifest = {"version": "9.9", "sha256": sha256 or hashlib.sha256(path.read_bytes()).hexdigest()}
    if signature is not None:
        manifest["hmac_sha256"] = signature.hex()
        manifest["signing_key_kind"] = "dev"
    Path(str(path) + ".manifest.json").write_text(json.dumps(manifest))


def _sent_signature(can: _RecordingCAN, chunk_id: int) -> bytes:
    return b"".join(data for can_id, data in can.sent if can_id == chunk_id)


def test_the_published_signature_is_sent_even_without_any_key(tmp_path, monkeypatch):
    monkeypatch.setattr(flasher_protocol, "HMAC_KEY", None)
    path = _image(tmp_path)
    published = bytes(range(100, 132))
    _publish(path, published)
    can = _RecordingCAN()
    assert URTCFlasher(can, log=lambda m: None).flash(str(path), version=(0, 3)) is True
    assert _sent_signature(can, flasher_protocol.CAN_ID_HMAC_CHUNK) == published


def test_an_unsigned_image_without_a_key_is_refused_before_any_traffic(tmp_path, monkeypatch):
    monkeypatch.setattr(flasher_protocol, "HMAC_KEY", None)
    monkeypatch.setattr(flasher_protocol, "SLAVE_HMAC_KEY", None)
    path = _image(tmp_path)
    flasher = URTCFlasher(_ExplodingCAN(), log=lambda m: None)
    with pytest.raises(FlashError, match="no published signature"):
        flasher.flash(str(path), version=(0, 3))
    with pytest.raises(FlashError, match="no published signature"):
        flasher.flash_slave(str(path))


def test_a_bench_key_signs_an_unsigned_image_locally(tmp_path):
    path = _image(tmp_path)
    can = _RecordingCAN()
    assert URTCFlasher(can, log=lambda m: None).flash(str(path), version=(0, 3)) is True
    expected = hmac.new(flasher_protocol.HMAC_KEY, path.read_bytes(), hashlib.sha256).digest()
    assert _sent_signature(can, flasher_protocol.CAN_ID_HMAC_CHUNK) == expected


def test_a_malformed_published_signature_is_refused(tmp_path):
    path = _image(tmp_path)
    _publish(path, b"\x01\x02")
    with pytest.raises(FlashError, match="32 bytes"):
        URTCFlasher(_ExplodingCAN(), log=lambda m: None).flash(str(path), version=(0, 3))


def test_preflight_uses_the_manifest_digest_when_there_is_no_sha256_file(tmp_path):
    path = _image(tmp_path)
    _publish(path, None, sha256="ab" * 32)
    check = preflight_image(str(path))
    assert check.blocked and not check.verified
    _publish(path, None)
    check = preflight_image(str(path))
    assert check.verified and not check.blocked


def test_preflight_blocks_when_the_published_digests_disagree(tmp_path):
    path = _image(tmp_path)
    _publish(path, None)
    Path(str(path) + ".sha256").write_text("cd" * 32 + "  x.bin\n")
    assert preflight_image(str(path)).blocked


def test_bundled_firmware_is_exactly_what_urtc_published():
    result = subprocess.run([sys.executable, str(ROOT / "tools" / "sync_firmware.py"), "--check"],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert list((ROOT / "firmware").glob("*.bin")), "firmware/ has no images"
