# =============================================================================
# URTC Flasher - tests/test_bus_scenario_cli.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""An update against the simulated bootloader through a bus scenario: off unless asked for, refused on a real adapter, the same every time for the
same seed, and the evidence says it was a simulation. No scenario makes an update that must fail succeed."""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

import urtc_flasher
from flasher_config import APP_FLASH_ADDR
from urtc_can import bus_scenario as bs
from urtc_can import evidence


@pytest.fixture()
def image(tmp_path):
    path = tmp_path / "URTC_MAIN_FIRMWARE_v0.3.9.bin"
    path.write_bytes(struct.pack("<II", 0x20003000, APP_FLASH_ADDR + 0x101) + bytes((i * 7 + 1) % 251 for i in range(6000)))
    return str(path)


def scenario_file(tmp_path, faults, seed=3, name="s"):
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps({"format": bs.FORMAT, "name": name, "seed": seed, "faults": faults}), encoding="utf-8")
    return str(path)


def run(capsys, image, *extra):
    code = urtc_flasher.run_cli(["--transport", "mock", "--no-trigger", "--file", image, "--version", "0.3", *extra])
    return code, capsys.readouterr().out


def evidence_of(folder: Path) -> dict:
    (path,) = sorted(folder.glob("urtc_evidence_*.json"))
    record = json.loads(path.read_text(encoding="utf-8"))
    assert evidence.verify(record) == []
    return record


# ---- before: the mock transport is what it was ----------------------------------------------------------------------------------
def test_without_a_scenario_the_mock_update_runs_as_it_always_did(tmp_path, capsys, image):
    code, out = run(capsys, image)
    assert code == 0 and "SUCCESS" in out and "bus scenario" not in out.lower()
    code, out = run(capsys, image, "--mock-fail", "0x03")
    assert code == 1 and "FAILED" in out


# ---- with a scenario -------------------------------------------------------------------------------------------------------------
def test_a_scenario_with_no_faults_updates_and_leaves_evidence(tmp_path, capsys, image):
    folder = tmp_path / "ev"
    code, out = run(capsys, image, "--scenario", scenario_file(tmp_path, []), "--evidence-dir", str(folder))
    assert code == 0 and "SUCCESS" in out
    record = evidence_of(folder)
    assert record["kind"] == "flash" and record["outcome"] == "pass"
    assert record["transport"] == {"adapter": "mock:scenario:s", "bus": "can"}
    assert "SIMULATED bus with a scenario" in record["detail"] and "scenario s seed 3" in record["detail"]
    assert record["artifacts"][0]["name"].endswith(".bin")


def test_a_bus_that_repeats_and_delays_frames_still_updates(tmp_path, capsys, image):
    scenario = scenario_file(tmp_path, [{"fault": "duplicate", "direction": "rx", "id": 0x7F9}, {"fault": "delay", "direction": "rx", "ms": 4}])
    code, out = run(capsys, image, "--scenario", scenario, "--evidence-dir", str(tmp_path / "ev"))
    assert code == 0, out
    assert evidence_of(tmp_path / "ev")["outcome"] == "pass"


def test_a_bus_that_loses_everything_fails_the_update_and_says_so(tmp_path, capsys, image):
    code, out = run(capsys, image, "--scenario", scenario_file(tmp_path, [{"fault": "drop", "direction": "rx"}]), "--evidence-dir", str(tmp_path / "ev"))
    assert code == 1 and "FAILED" in out
    record = evidence_of(tmp_path / "ev")
    assert record["outcome"] == "fail" and "SIMULATED" in record["detail"] and "drop" in record["detail"]


def test_a_silent_bootloader_fails_the_update(tmp_path, capsys, image):
    code, out = run(capsys, image, "--scenario", scenario_file(tmp_path, [{"fault": "mute", "direction": "tx"}]), "--evidence-dir", str(tmp_path / "ev"))
    assert code == 1 and evidence_of(tmp_path / "ev")["outcome"] == "fail"


@pytest.mark.parametrize("seed", range(30))
def test_an_update_that_must_fail_never_succeeds_under_a_generated_scenario(tmp_path, capsys, image, seed):
    """The mock bootloader reports a failed verification (HMAC mismatch); no scenario the generator makes can turn that into a success."""
    scenario = tmp_path / "g.json"
    scenario.write_text(bs.generate(seed).to_json(), encoding="utf-8")
    code, out = run(capsys, image, "--mock-fail", "0x03", "--scenario", str(scenario), "--evidence-dir", str(tmp_path / "ev"))
    assert code != 0
    assert evidence_of(tmp_path / "ev")["outcome"] != "pass"


def test_the_same_scenario_and_seed_give_the_same_run(tmp_path, capsys, image):
    scenario = scenario_file(tmp_path, [{"fault": "drop", "direction": "rx", "per_mille": 150}, {"fault": "reorder", "direction": "rx", "window": 3},
                                        {"fault": "delay", "direction": "rx", "min_ms": 1, "max_ms": 20}], seed=17)
    runs = []
    for n in range(2):
        code, out = run(capsys, image, "--scenario", scenario, "--evidence-dir", str(tmp_path / f"e{n}"))
        record = evidence_of(tmp_path / f"e{n}")
        lines = [line for line in out.splitlines() if "Update report" not in line and "Evidence record" not in line]
        runs.append((code, lines, record["outcome"], record["detail"]))
    assert runs[0] == runs[1]


# ---- refused cases ---------------------------------------------------------------------------------------------------------------
def test_a_scenario_is_never_applied_to_a_real_adapter(tmp_path, capsys, image):
    scenario = scenario_file(tmp_path, [])
    for transport in ("serial", "socketcan", "python-can"):
        code = urtc_flasher.run_cli(["--transport", transport, "--port", "x", "--file", image, "--scenario", scenario])
        assert code == 2 and "only for --transport mock" in capsys.readouterr().out
    assert not (tmp_path / "ev").exists()


def test_a_scenario_that_is_not_valid_runs_nothing(tmp_path, capsys, image):
    bad = tmp_path / "bad.json"
    bad.write_text('{"format": "urtc-scenario/1", "name": "x", "faults": [{"fault": "drop", "bogus": 1}]}', encoding="utf-8")
    code, out = run(capsys, image, "--scenario", str(bad), "--evidence-dir", str(tmp_path / "ev"))
    assert code == 2 and "not valid" in out and not (tmp_path / "ev").exists()
    code, out = run(capsys, image, "--scenario", str(tmp_path / "missing.json"))
    assert code == 2
    code, out = run(capsys, image, "--scenario", scenario_file(tmp_path, []), "--seed", "-1")
    assert code == 2


def test_a_seed_or_a_folder_without_a_scenario_is_refused(tmp_path, capsys, image):
    for extra in (["--seed", "4"], ["--evidence-dir", str(tmp_path)]):
        code, out = run(capsys, image, *extra)
        assert code == 2 and "go with --scenario" in out


def test_the_protocol_clock_is_put_back_after_a_scenario_run(tmp_path, capsys, image):
    import time as real_time

    import flasher_protocol
    run(capsys, image, "--scenario", scenario_file(tmp_path, []), "--evidence-dir", str(tmp_path / "ev"))
    assert flasher_protocol.time is real_time
    run(capsys, image, "--scenario", scenario_file(tmp_path, [{"fault": "drop", "direction": "rx"}]), "--evidence-dir", str(tmp_path / "ev2"))
    assert flasher_protocol.time is real_time


def test_the_history_command_reads_the_evidence_of_a_scenario_run(tmp_path, capsys, image):
    run(capsys, image, "--scenario", scenario_file(tmp_path, []), "--evidence-dir", str(tmp_path / "ev"))
    urtc_flasher.run_history([str(tmp_path / "ev")])   # the update report written beside the record is listed too, as it is for the window
    assert "flash    pass" in capsys.readouterr().out
