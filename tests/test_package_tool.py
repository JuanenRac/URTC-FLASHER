# =============================================================================
# URTC Flasher - tests/test_package_tool.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The tool that packs and signs the update package of a release works from this repository with the copy of the update modules it carries."""
from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import make_update_package as tool  # noqa: E402

from urtc_can import self_update  # noqa: E402

SEED = bytes(range(32))


def test_a_package_is_built_signed_and_accepted_by_the_verifier_of_the_program(tmp_path):
    source = tmp_path / "dist"
    source.mkdir()
    (source / "URTC-Flasher.exe").write_bytes(b"MZ")
    package, key_id = tool.build("urtc-flasher", "0.5.0", "windows-x64", source, "URTC-Flasher.exe", tmp_path / "out", SEED)
    assert package.name == "urtc-flasher-0.5.0-windows-x64.zip"
    with zipfile.ZipFile(package) as archive:
        assert json.loads(archive.read("app_info.json"))["entry"] == "URTC-Flasher.exe"
    sha = hashlib.sha256(package.read_bytes()).hexdigest()
    signature = bytes.fromhex((package.parent / (package.name + ".sig")).read_text().strip())
    public = tool.public_key_of(SEED)
    assert key_id == hashlib.sha256(public).hexdigest()[:16]
    assert self_update.ed25519_verify(public, self_update.package_message("urtc-flasher", "0.5.0", "windows-x64", sha, package.stat().st_size), signature)


def test_the_tool_and_the_program_trust_the_same_key():
    assert tool.svc.RELEASE_PUBLIC_KEY_HEX == "4020c46d76c8ebacb64c5c7b9f3e7c62475afeb133d7421591988174e0f5dc90"
    assert tool.svc.__name__.startswith("urtc_can")
