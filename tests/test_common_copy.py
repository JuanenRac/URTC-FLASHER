# =============================================================================
# URTC Flasher - tests/test_common_copy.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""The generated protocol module and the shared vectors are copies: nobody edits them by hand, they do not fall behind
the shared repository when it is next to this one, and the constants this program uses are the generated ones."""
import hashlib
import json
from pathlib import Path

import pytest

import flasher_config as config
from urtc_can import protocol

ROOT = Path(__file__).resolve().parent.parent
COMMON = ROOT.parent / "URTC-COMMON"
LOCKS = (ROOT / "urtc_can" / "urtc_common.lock.json", ROOT / "tests" / "fixtures" / "urtc_common.lock.json")


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


@pytest.mark.parametrize("lock_path", LOCKS, ids=lambda path: path.parent.name)
def test_a_copied_file_is_not_edited_by_hand(lock_path):
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    assert lock["files"], "the lock lists no file"
    for name, expected in lock["files"].items():
        assert _digest(lock_path.parent / name) == expected["sha256"], f"{name} differs from the lock: sync it again instead of editing it"


def test_the_copies_have_not_fallen_behind_the_shared_repository():
    if not COMMON.is_dir():
        pytest.skip("URTC-COMMON is not next to this repository")
    assert _digest(ROOT / "urtc_can" / "protocol.py") == _digest(COMMON / "src" / "urtc_common" / "protocol.py")
    assert _digest(ROOT / "tests" / "fixtures" / "can_conformance_vectors.json") == _digest(COMMON / "conformance" / "can_vectors.json")


def test_every_identifier_this_program_defines_is_the_generated_one():
    generated = {name: value for name, value in vars(protocol).items() if name.startswith("CAN_ID_")}
    defined = {name: value for name, value in vars(config).items() if name.startswith("CAN_ID_")}
    assert defined, "no identifiers found"
    for name, value in defined.items():
        assert value in generated.values(), f"{name} = {value:#05x} is not an identifier of the specification"


def test_the_magic_payload_and_the_hardware_ids_are_the_generated_ones():
    assert config.ERASE_FRAM_MAGIC == protocol.MAGIC_ERASE_FRAM
    assert config.THIS_HARDWARE_ID == protocol.HARDWARE_ID_MAIN
