# =============================================================================
# URTC Flasher - tests/test_bootloader_twin.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The flasher against the real bootloader of the master, compiled for the host (the twin in the URTC repository).

The virtual board of the shared package can start the twin behind its SLCAN adapter, so ``URTCFlasher.flash`` runs here unchanged against the C that runs on the
chip: its window, its page buffer, its CRC check and its Ed25519 check of the image record. The image has a manifest that names the board, the hash and the version, as a
published one does, and a ``<image>.imgsig`` file next to it, as a release has. The record is the one the URTC repository made for the same patterned image with the
public DEVELOPMENT seed of the bench table (``urtc_common.image_sig.DEV_SEED``; the twin is built with that table): it holds no secret and no key of the releases is ever read.
The tests need the URTC repository next to this one (or in the folder the environment variable URTC_FIRMWARE_REPO names) and a host C compiler (WSL on Windows);
without them they are skipped, and the continuous integration of this repository provides both.
"""
from __future__ import annotations

import hashlib
import json
import os
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

#: The case of tests/boot_sig_cases.json of the URTC repository this test uses: the patterned image of 3000 bytes, version 0.5.1, counter 5, signed with the development seed.
IMAGE_SIZE = 3000
IMAGE_VERSION = "0.5.1"
CASE_MINOR_FIELD = ((0x80 | 1) << 8) | 5
CASE_COUNTER = 5


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
def image_record() -> bytes:
    """The 76-byte record of the case, signed with the public development seed (the table of the twin trusts that key)."""
    cases_file = _firmware_repo() / "tests" / "boot_sig_cases.json"
    if not cases_file.is_file():
        pytest.skip("the URTC repository has no tests/boot_sig_cases.json")
    for case in json.loads(cases_file.read_text(encoding="utf-8"))["cases"]:
        if (case["size"], case["hardware_id"], case["major"], case["minor_field"], case["counter"], case["key"]) == (
                IMAGE_SIZE, THIS_HARDWARE_ID, 0, CASE_MINOR_FIELD, CASE_COUNTER, "dev"):
            return bytes.fromhex(case["record"])
    pytest.skip("the signed case of this test is not in tests/boot_sig_cases.json of the URTC repository")


def _image_with_record(tmp_path: Path, record: bytes, flip_signature_bit: bool = False) -> str:
    image = bytes((i * 13 + 5) & 0xFF for i in range(IMAGE_SIZE))
    path = tmp_path / f"URTC_MAIN_FIRMWARE_v{IMAGE_VERSION}.bin"
    path.write_bytes(image)
    signed = bytearray(record)
    if flip_signature_bit:
        signed[-1] ^= 1
    Path(str(path) + ".imgsig").write_text(bytes(signed).hex() + "\n", encoding="ascii")
    manifest = {
        "component": "main_application",
        "hardware_id": f"0x{THIS_HARDWARE_ID:08X}",
        "version": IMAGE_VERSION,
        "build_date": "bench",
        "sha256": hashlib.sha256(image).hexdigest(),
        "crc32": f"0x{zlib.crc32(image) & 0xFFFFFFFF:08X}",
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


def test_the_flasher_installs_an_image_with_its_signature_record_through_the_real_bootloader(tmp_path, monkeypatch, twin_command, image_record):
    monkeypatch.setattr(flasher_protocol, "REQUIRE_PRODUCTION_SIGNATURE", False)
    done, log = _flash(twin_command, _image_with_record(tmp_path, image_record))
    assert done is True
    assert any("0.5" in line for line in log)


def test_the_real_bootloader_refuses_a_record_with_one_bit_changed(tmp_path, monkeypatch, twin_command, image_record):
    monkeypatch.setattr(flasher_protocol, "REQUIRE_PRODUCTION_SIGNATURE", False)
    with pytest.raises(FlashError):
        _flash(twin_command, _image_with_record(tmp_path, image_record, flip_signature_bit=True))
