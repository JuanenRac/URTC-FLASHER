# =============================================================================
# URTC Flasher - tests/test_bootloader_twin.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The flasher against the real bootloader of the master, compiled for the host (the twin in the URTC repository).

The virtual board of the shared package can start the twin behind its SLCAN adapter, so ``URTCFlasher.flash`` runs here unchanged against the C that runs on the
chip: its window, its page buffer, its CRC check and its signature check. The image has a manifest that names the board, the hash and the signature, as a published
one does. The tests need the URTC repository next to this one (or in the folder the environment variable URTC_FIRMWARE_REPO names) and a host C compiler
(WSL on Windows); without them they are skipped, and the continuous integration of this repository provides both.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import zlib
from pathlib import Path

import pytest

import flasher_protocol
from flasher_config import THIS_HARDWARE_ID
from flasher_protocol import FlashError, URTCFlasher
from flasher_transports import SLCAN
from test_virtual_board import SERIAL_MODULE
from urtc_can.virtual_board import FirmwareBoardError, VirtualBoardServer, firmware_board_command

ROOT = Path(__file__).resolve().parent.parent


def _firmware_repo() -> Path:
    named = os.environ.get("URTC_FIRMWARE_REPO", "").strip()
    repo = Path(named) if named else ROOT.parent / "URTC"
    if not (repo / "tools" / "bootloader_twin.py").is_file():
        pytest.skip("the URTC repository with the twin of the bootloader is not next to this one")
    return repo


@pytest.fixture(scope="module")
def twin_command() -> list[str]:
    repo = _firmware_repo()
    try:
        return firmware_board_command(repo, bootloader=True)
    except FirmwareBoardError as exc:
        pytest.skip(str(exc))


@pytest.fixture(scope="module")
def bootloader_key() -> bytes:
    """The key the twin was built with (the public development key, written in the source of the bootloader's crypto)."""
    source = (_firmware_repo() / "src" / "F303-master" / "boot" / "bootloader_crypto.c").read_text(encoding="utf-8")
    block = re.search(r"#else.*?const uint8_t HMAC_KEY\[32\] = \{(.*?)\};", source, re.S)
    if not block:
        pytest.skip("the bootloader of the master verifies an Ed25519 record and holds no HMAC key; the flasher does not transport that record yet")
    return bytes(int(x, 16) for x in re.findall(r"0x([0-9A-Fa-f]{2})", block.group(1)))


def _image_with_manifest(tmp_path: Path, key: bytes, size: int = 2100, flip_signature_bit: bool = False) -> str:
    image = bytes((i * 13 + 5) & 0xFF for i in range(size))
    path = tmp_path / "URTC_MAIN_FIRMWARE_v0.5.0.bin"
    path.write_bytes(image)
    signature = bytearray(hmac.new(key, image, hashlib.sha256).digest())
    if flip_signature_bit:
        signature[31] ^= 1
    manifest = {
        "component": "main_application",
        "hardware_id": f"0x{THIS_HARDWARE_ID:08X}",
        "version": "0.5.0",
        "build_date": "bench",
        "sha256": hashlib.sha256(image).hexdigest(),
        "crc32": f"0x{zlib.crc32(image) & 0xFFFFFFFF:08X}",
        "hmac_sha256": bytes(signature).hex(),
        "signing_key_kind": "dev",
    }
    Path(str(path) + ".manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return str(path)


def _flash(command: list[str], firmware: str) -> tuple[bool, list[str]]:
    log: list[str] = []
    with VirtualBoardServer(command=command) as server:
        transport = SLCAN(server.url, serial_module=SERIAL_MODULE, settle_seconds=0)
        transport.open_channel()
        try:
            return URTCFlasher(transport, log=log.append).flash(firmware), log
        finally:
            transport.close()


def test_the_flasher_installs_a_signed_image_through_the_real_bootloader(tmp_path, monkeypatch, twin_command, bootloader_key):
    monkeypatch.setattr(flasher_protocol, "REQUIRE_PRODUCTION_SIGNATURE", False)
    done, log = _flash(twin_command, _image_with_manifest(tmp_path, bootloader_key))
    assert done is True
    assert any("0.5" in line for line in log)


def test_the_real_bootloader_refuses_a_signature_with_one_bit_changed(tmp_path, monkeypatch, twin_command, bootloader_key):
    monkeypatch.setattr(flasher_protocol, "REQUIRE_PRODUCTION_SIGNATURE", False)
    with pytest.raises(FlashError):
        _flash(twin_command, _image_with_manifest(tmp_path, bootloader_key, flip_signature_bit=True))
