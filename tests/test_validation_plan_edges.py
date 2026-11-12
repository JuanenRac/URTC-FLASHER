# =============================================================================
# URTC Flasher - tests/test_validation_plan_edges.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The plausibility check of an image and the plan of an update at the edges of their ranges, and over generated files (a fixed seed, so a failure repeats)."""
from __future__ import annotations

import random
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

import flasher_plan
from flasher_config import APP_FLASH_ADDR, APP_MAX_SIZE
from flasher_validation import validate_firmware_file

SEED = 20261112
GOOD_SP = 0x20003000
GOOD_RESET = APP_FLASH_ADDR + 0x101


def _write(tmp_path, name, sp, reset, body_len):
    path = tmp_path / name
    path.write_bytes(struct.pack("<II", sp, reset) + bytes(range(256)) * (body_len // 256) + bytes(body_len % 256))
    return str(path)


# ---- the stack pointer -------------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("sp, ok", [
    (0x200000FF, False), (0x20000100, True), (0x20003000, True), (0x2000A000, True), (0x2000A001, False),
    (0x100000FF, False), (0x10000100, True), (0x10002000, True), (0x10002001, False),
    (0, False), (0xFFFFFFFF, False), (0x08000000, False),
])
def test_the_stack_pointer_must_be_in_sram_or_ccm_inclusive_at_both_ends(tmp_path, sp, ok):
    valid, reason, size = validate_firmware_file(_write(tmp_path, "a.bin", sp, GOOD_RESET, 100))
    assert valid is ok and size == 108
    assert ("stack pointer" in reason) is (not ok)


# ---- the reset handler -------------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("reset, ok", [
    (APP_FLASH_ADDR - 1, False), (APP_FLASH_ADDR, True), (APP_FLASH_ADDR + APP_MAX_SIZE - 1, True), (APP_FLASH_ADDR + APP_MAX_SIZE, False),
    (0, False), (0xFFFFFFFF, False), (0x08000785, False),
])
def test_the_reset_handler_must_point_inside_the_application_slot_at_both_ends(tmp_path, reset, ok):
    valid, reason, _size = validate_firmware_file(_write(tmp_path, "a.bin", GOOD_SP, reset, 100))
    assert valid is ok
    assert ("reset handler" in reason) is (not ok)


def test_another_slot_is_accepted_when_it_is_named_and_refused_when_it_is_not(tmp_path):
    path = _write(tmp_path, "slave.bin", GOOD_SP, 0x08005101, 100)
    assert validate_firmware_file(path)[0] is False
    assert validate_firmware_file(path, expected_base_addr=0x08005000, max_size=0x3000)[0] is True


# ---- the size ----------------------------------------------------------------------------------------------------------------------------------

def test_the_size_limits_are_exact(tmp_path):
    exact = tmp_path / "exact.bin"
    exact.write_bytes(struct.pack("<II", GOOD_SP, GOOD_RESET) + bytes(APP_MAX_SIZE - 8))
    assert validate_firmware_file(str(exact)) == (True, "looks valid", APP_MAX_SIZE)
    over = tmp_path / "over.bin"
    over.write_bytes(struct.pack("<II", GOOD_SP, GOOD_RESET) + bytes(APP_MAX_SIZE - 7))
    valid, reason, size = validate_firmware_file(str(over))
    assert not valid and "too large" in reason and size == APP_MAX_SIZE + 1


@pytest.mark.parametrize("length", [1, 4, 7])
def test_a_file_too_short_for_a_vector_table_is_refused(tmp_path, length):
    path = tmp_path / "short.bin"
    path.write_bytes(bytes(length))
    valid, reason, size = validate_firmware_file(str(path))
    assert not valid and "too small" in reason and size == length


def test_an_empty_file_and_a_missing_file_are_refused_with_size_zero(tmp_path):
    empty = tmp_path / "empty.bin"
    empty.write_bytes(b"")
    assert validate_firmware_file(str(empty)) == (False, "empty file", 0)
    valid, reason, size = validate_firmware_file(str(tmp_path / "nothing.bin"))
    assert not valid and size == 0 and "can't read" in reason


def test_generated_images_are_judged_the_same_way_every_time(tmp_path):
    rng = random.Random(SEED)
    for i in range(80):
        sp = rng.choice([rng.randrange(0, 2**32), rng.randrange(0x20000100, 0x2000A001), rng.randrange(0x10000100, 0x10002001)])
        reset = rng.choice([rng.randrange(0, 2**32), rng.randrange(APP_FLASH_ADDR, APP_FLASH_ADDR + APP_MAX_SIZE)])
        path = _write(tmp_path, f"g{i}.bin", sp, reset, rng.randrange(0, 2000))
        first = validate_firmware_file(path)
        assert first == validate_firmware_file(path)
        in_sram = 0x20000100 <= sp <= 0x2000A000 or 0x10000100 <= sp <= 0x10002000
        in_slot = APP_FLASH_ADDR <= reset < APP_FLASH_ADDR + APP_MAX_SIZE
        assert first[0] is (in_sram and in_slot)


# ---- the plan ----------------------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("name, version", [
    ("URTC_MAIN_FIRMWARE_v0.3.9.bin", "0.3.9"), ("app_V1.2.bin", "1.2"), ("x_v10.20.30.bin", "10.20.30"), ("firmware_v1.2.3.4.bin", "1.2.3.4"),
    ("no_version.bin", None), ("v1.bin", None), ("version2.0.bin", None), ("URTC_v0.3.bin", "0.3"), ("a/b/c_v0.4.5.bin", "0.4.5"),
])
def test_the_version_is_read_from_the_name_of_the_file_only(name, version):
    assert flasher_plan._version_from_name(name) == version


def test_the_folders_in_front_of_the_name_never_give_a_version():
    assert flasher_plan._version_from_name("C:/builds/v9.9.9/firmware.bin") is None


@pytest.mark.parametrize("size, frames", [(8, 1), (9, 2), (16, 2), (17, 3), (6008, 751)])
def test_the_data_frames_are_the_size_divided_by_eight_rounded_up(tmp_path, size, frames):
    path = tmp_path / "URTC_v1.0.bin"
    path.write_bytes(struct.pack("<II", GOOD_SP, GOOD_RESET) + bytes(size - 8))
    plan = flasher_plan.build_plan(str(path))
    assert plan["data_frames"] == frames and plan["size"] == size


def test_the_steps_are_numbered_from_one_in_the_order_of_the_protocol(tmp_path):
    path = _write(tmp_path, "URTC_v1.0.bin", GOOD_SP, GOOD_RESET, 64)
    plan = flasher_plan.build_plan(path)
    assert [step["number"] for step in plan["steps"]] == list(range(1, len(plan["steps"]) + 1))
    assert [step["step"] for step in plan["steps"]] == [key for key, _text in flasher_plan.STEPS]
    without = flasher_plan.build_plan(path, no_trigger=True)
    assert [step["step"] for step in without["steps"]] == [key for key, _text in flasher_plan.STEPS][1:]
    assert [step["number"] for step in without["steps"]] == list(range(1, len(without["steps"]) + 1))


def test_force_lets_an_implausible_file_through_but_not_an_unreadable_one(tmp_path):
    bad = _write(tmp_path, "bad.bin", 0, 0, 64)
    assert flasher_plan.build_plan(bad)["accepted"] is False
    forced = flasher_plan.build_plan(bad, force=True)
    assert forced["accepted"] is True and any("overridden by --force" in problem for problem in forced["problems"])
    assert flasher_plan.build_plan(str(tmp_path / "missing.bin"), force=True)["accepted"] is False


def test_render_always_ends_with_the_verdict_and_the_note_that_nothing_was_sent(tmp_path):
    good = flasher_plan.render(flasher_plan.build_plan(_write(tmp_path, "URTC_v1.0.bin", GOOD_SP, GOOD_RESET, 64)))
    bad = flasher_plan.render(flasher_plan.build_plan(_write(tmp_path, "bad.bin", 0, 0, 64)))
    assert good[-2] == "The flasher would go on to open a bus with this image." and bad[-2] == "The flasher would refuse this image."
    assert good[-1].startswith("Nothing was sent") and bad[-1] == good[-1]
    assert any(line.startswith("  PROBLEM:") for line in bad) and not any(line.startswith("  PROBLEM:") for line in good)
