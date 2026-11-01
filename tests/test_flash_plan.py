# =============================================================================
# URTC Flasher - tests/test_flash_plan.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""``--check-only``: the plan of an update and the checks of the image, with no bus, no port and no board; the update itself is as it was."""
from __future__ import annotations

import hashlib
import json
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

import flasher_plan
import urtc_flasher
from flasher_config import APP_FLASH_ADDR


@pytest.fixture()
def image(tmp_path):
    path = tmp_path / "URTC_MAIN_FIRMWARE_v0.3.9.bin"
    path.write_bytes(struct.pack("<II", 0x20003000, APP_FLASH_ADDR + 0x101) + bytes((i * 7 + 1) % 251 for i in range(6000)))
    return str(path)


def check(capsys, *args):
    code = urtc_flasher.run_cli(["--check-only", *args])
    return code, capsys.readouterr().out


# -- characterization: the update path is what it was ---------------------------------------------------------------------------------------------
def test_without_the_flag_the_update_still_runs_against_the_mock(capsys, image):
    code = urtc_flasher.run_cli(["--transport", "mock", "--no-trigger", "--file", image, "--version", "0.3"])
    assert code == 0 and "SUCCESS" in capsys.readouterr().out


def test_the_port_is_still_required_for_a_real_transport(capsys, image):
    assert urtc_flasher.run_cli(["--file", image]) == 2
    assert "--port is required" in capsys.readouterr().out


def test_json_without_the_check_is_refused(capsys, image):
    assert urtc_flasher.run_cli(["--transport", "mock", "--file", image, "--json"]) == 2
    assert "--json goes with --check-only" in capsys.readouterr().out


# -- the plan ---------------------------------------------------------------------------------------------------------------------------------
def test_a_good_image_gets_a_plan_without_a_port_or_a_bus(capsys, image):
    code, out = check(capsys, "--file", image)
    assert code == 0
    data = Path(image).read_bytes()
    assert hashlib.sha256(data).hexdigest() in out and f"{zlib.crc32(data) & 0xFFFFFFFF:08X}" in out
    assert "The flasher would go on to open a bus with this image." in out and "Nothing was sent" in out
    for number in range(1, 7):
        assert f"  {number}. " in out
    assert "version: 0.3.9" in out and f"{-(-len(data) // 8)} data frames" in out


def test_the_plan_as_json_has_the_fixed_format_and_the_steps(capsys, image):
    code, out = check(capsys, "--file", image, "--json")
    plan = json.loads(out)
    assert code == 0 and plan["format"] == flasher_plan.PLAN_FORMAT and plan["accepted"] is True and plan["plausible"] is True
    assert [s["step"] for s in plan["steps"]] == ["trigger", "start_update", "signature", "data", "end_update", "verify"]
    assert plan["file"] == "URTC_MAIN_FIRMWARE_v0.3.9.bin" and plan["version"] == "0.3.9" and plan["problems"] == []


def test_the_same_file_gives_the_same_plan(capsys, image):
    first = check(capsys, "--file", image, "--json")
    second = check(capsys, "--file", image, "--json")
    assert first == second


def test_no_trigger_leaves_out_the_first_step_and_a_given_version_wins(capsys, image):
    _, out = check(capsys, "--file", image, "--json", "--no-trigger", "--version", "0.4")
    plan = json.loads(out)
    assert [s["step"] for s in plan["steps"]][0] == "start_update" and [s["number"] for s in plan["steps"]] == [1, 2, 3, 4, 5]
    assert plan["version"] == "0.4"


def test_nothing_is_written_next_to_the_image(capsys, image, tmp_path):
    before = sorted(p.name for p in tmp_path.iterdir())
    check(capsys, "--file", image)
    assert sorted(p.name for p in tmp_path.iterdir()) == before


# -- images that are refused ------------------------------------------------------------------------------------------------------------------
def test_a_file_that_is_not_a_plausible_image_is_refused_and_force_lets_it_through_as_in_the_update(capsys, tmp_path):
    bad = tmp_path / "junk.bin"
    bad.write_bytes(b"\xff" * 4000)
    code, out = check(capsys, "--file", str(bad))
    assert code == 2 and "FAILS" in out and "The flasher would refuse this image." in out
    code, out = check(capsys, "--file", str(bad), "--force")
    assert code == 0 and "overridden by --force" in out


def test_a_missing_and_an_empty_file_are_refused_and_never_accepted_by_force(capsys, tmp_path):
    code, out = check(capsys, "--file", str(tmp_path / "nope.bin"), "--force", "--json")
    assert code == 2 and json.loads(out)["accepted"] is False
    empty = tmp_path / "empty.bin"
    empty.write_bytes(b"")
    code, out = check(capsys, "--file", str(empty), "--json")
    plan = json.loads(out)
    assert code == 2 and plan["size"] == 0 and plan["sha256"] == "" and plan["accepted"] is False


def test_a_digest_that_does_not_match_blocks_the_image_even_with_force(capsys, image):
    Path(image + ".sha256").write_text("0" * 64 + "  URTC_MAIN_FIRMWARE_v0.3.9.bin\n", encoding="utf-8")
    code, out = check(capsys, "--file", image, "--force", "--json")
    plan = json.loads(out)
    assert code == 2 and plan["digest"] == "blocked" and plan["accepted"] is False and plan["problems"]


def test_a_matching_digest_is_verified(capsys, image):
    Path(image + ".sha256").write_text(hashlib.sha256(Path(image).read_bytes()).hexdigest() + "  x\n", encoding="utf-8")
    code, out = check(capsys, "--file", image, "--json")
    assert code == 0 and json.loads(out)["digest"] == "verified"


def test_the_flag_does_not_go_with_a_scenario(capsys, image, tmp_path):
    scenario = tmp_path / "s.json"
    scenario.write_text("{}", encoding="utf-8")
    code, out = check(capsys, "--transport", "mock", "--file", image, "--scenario", str(scenario))
    assert code == 2 and "--check-only opens no bus" in out
    code, out = check(capsys, "--file", image, "--seed", "3")
    assert code == 2 and "--check-only opens no bus" in out


def test_a_name_without_a_version_says_so(capsys, tmp_path):
    path = tmp_path / "firmware.bin"
    path.write_bytes(struct.pack("<II", 0x20003000, APP_FLASH_ADDR + 0x101) + bytes(range(200)) * 10)
    code, out = check(capsys, "--file", str(path))
    assert code == 0 and "version: not known" in out
