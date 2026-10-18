# =============================================================================
# URTC Flasher - tests/test_swd_tools.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""The SWD/JTAG wrappers around pyOCD and STM32CubeProgrammer, with the child
process replaced by a stand-in: the exact command lines, the order of the
destructive steps, and every way a run is judged to have failed."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

import flasher_swd_tools as swd
from flasher_swd_tools import CubeProgrammerCLI, PyOCDCLI, SWDFlashError, _address_args_bin_needs_it

PROBE_TABLE = "--------------------------------------------------\n0   STM32 STLink         2900240008000054574E514E   n/a\n"
TWO_PROBES = PROBE_TABLE + "1   STM32 STLink         AAAA00000000000000000000   n/a\n"


class _Proc:
    def __init__(self, output, returncode):
        self.stdout = iter(output.splitlines(keepends=True))
        self.returncode = returncode
        self.killed = False

    def wait(self):
        pass

    def kill(self):
        self.killed = True


class _Runner:
    """Records every command line; answers from a script keyed by a fragment of the arguments."""

    def __init__(self, monkeypatch, answers=None, default=("", 0)):
        self.commands = []
        self.answers = answers or {}
        self.default = default
        monkeypatch.setattr(swd.subprocess, "Popen", self._popen)

    def _popen(self, cmd, **kwargs):
        self.commands.append(list(cmd))
        joined = " ".join(cmd)
        for fragment, (output, code) in self.answers.items():
            if fragment in joined:
                return _Proc(output, code)
        return _Proc(*self.default)

    def verbs(self):
        return [c[1] for c in self.commands]


@pytest.fixture
def pyocd(monkeypatch):
    monkeypatch.setattr(swd, "_find_executable", lambda names: "/bin/pyocd")
    logs = []
    tool = PyOCDCLI(log=logs.append)
    tool.logs = logs
    return tool


@pytest.fixture
def cube(monkeypatch):
    monkeypatch.setattr(swd, "_find_executable", lambda names: "/bin/cube")
    logs = []
    tool = CubeProgrammerCLI(log=logs.append)
    tool.logs = logs
    return tool


def _images(tmp_path, bootloader="boot.bin", app="app.bin"):
    boot, application = tmp_path / bootloader, tmp_path / app
    boot.write_bytes(b"\x00" * 16)
    application.write_bytes(b"\x00" * 16)
    return str(boot), str(application)


# ---- helpers -----------------------------------------------------------------------
def test_executable_lookup_returns_the_first_hit(monkeypatch):
    monkeypatch.setattr(swd.shutil, "which", lambda name: "/x/" + name if name == "second" else None)
    assert swd._find_executable(["first", "second", "third"]) == "/x/second"
    assert swd._find_executable(["first"]) is None


def test_only_raw_images_get_an_explicit_load_address():
    assert _address_args_bin_needs_it("a.bin", 0x08008000, "--base-address") == ["--base-address", "0x08008000"]
    assert _address_args_bin_needs_it("a.img", 0x08000000) == ["0x08000000"]
    for name in ("a.hex", "a.ELF", "a.axf", "a.srec", "a.s19", "a.s37"):
        assert _address_args_bin_needs_it(name, 0x08008000, "--base-address") == []


def test_failure_words_are_found_but_not_inside_the_file_names_passed_as_arguments(pyocd):
    assert pyocd._looks_like_failure("Error: something broke")
    assert pyocd._looks_like_failure("verification FAILED".replace("FAILED", "failed"))
    assert not pyocd._looks_like_failure("flashed 16 bytes")
    path = "C:/builds/mismatch_error:fix/app.bin"
    assert not pyocd._looks_like_failure(f"programming {path} done", exclude_args=[path])
    assert pyocd._looks_like_failure(f"programming {path} failed to connect", exclude_args=[path])


# ---- running a child process ----------------------------------------------------------
def test_run_without_an_executable_refuses(monkeypatch):
    monkeypatch.setattr(swd, "_find_executable", lambda names: None)
    with pytest.raises(SWDFlashError, match="not found"):
        PyOCDCLI()._run(["list"], dry_run=False)


def test_dry_run_logs_the_command_and_executes_nothing(pyocd, monkeypatch):
    runner = _Runner(monkeypatch)
    assert pyocd._run(["erase", "--chip"], dry_run=True) == ""
    assert runner.commands == []
    assert any("erase --chip" in line for line in pyocd.logs)


def test_a_nonzero_exit_code_is_a_failure(pyocd, monkeypatch):
    _Runner(monkeypatch, default=("boom", 3))
    with pytest.raises(SWDFlashError, match="exited with code 3"):
        pyocd._run(["flash"], dry_run=False)


def test_a_zero_exit_code_with_a_failure_message_is_still_a_failure(pyocd, monkeypatch):
    _Runner(monkeypatch, default=("Error: target is not responding", 0))
    with pytest.raises(SWDFlashError, match="failure indicator"):
        pyocd._run(["flash"], dry_run=False)


def test_output_is_not_judged_when_the_caller_turns_the_check_off(pyocd, monkeypatch):
    _Runner(monkeypatch, default=("no probes", 0))
    assert pyocd._run(["list"], dry_run=False, check_output=False) == "no probes"


def test_a_child_that_cannot_start_is_reported(pyocd, monkeypatch):
    def refuse(*args, **kwargs):
        raise OSError("denied")
    monkeypatch.setattr(swd.subprocess, "Popen", refuse)
    with pytest.raises(SWDFlashError, match="couldn't run"):
        pyocd._run(["list"], dry_run=False)


def test_a_child_that_overruns_is_killed_and_reported(pyocd, monkeypatch):
    class _Timer:
        def __init__(self, interval, function):
            self.function = function

        def start(self):
            self.function()

        def cancel(self):
            pass

    runner = _Runner(monkeypatch, default=("still going", 0))
    monkeypatch.setattr(swd.threading, "Timer", _Timer)
    with pytest.raises(SWDFlashError, match="timed out"):
        pyocd._run(["flash"], dry_run=False, timeout=1)
    assert runner.commands


# ---- pyOCD ---------------------------------------------------------------------------------
def test_pyocd_lists_probes_from_its_table(pyocd, monkeypatch):
    _Runner(monkeypatch, {"list --probes": (PROBE_TABLE, 0)})
    assert pyocd.list_probes() == [("2900240008000054574E514E", "STM32 STLink")]


def test_pyocd_probe_listing_failure_gives_an_empty_list(pyocd, monkeypatch):
    _Runner(monkeypatch, {"list --probes": ("", 1)})
    assert pyocd.list_probes() == []


def test_pyocd_refuses_when_no_probe_is_connected(pyocd, monkeypatch):
    _Runner(monkeypatch, {"list --probes": ("No available debug probes are connected\n", 0)})
    with pytest.raises(SWDFlashError, match="No SWD/JTAG probe"):
        pyocd.check_connection()


def test_pyocd_refuses_to_guess_between_two_probes(pyocd, monkeypatch):
    _Runner(monkeypatch, {"list --probes": (TWO_PROBES, 0)})
    with pytest.raises(SWDFlashError, match="refusing to guess"):
        pyocd.check_connection()
    pyocd.check_connection(probe_uid="AAAA00000000000000000000")


def test_pyocd_refuses_a_probe_uid_that_is_not_connected(pyocd, monkeypatch):
    _Runner(monkeypatch, {"list --probes": (PROBE_TABLE, 0)})
    with pytest.raises(SWDFlashError, match="doesn't appear"):
        pyocd.check_connection(probe_uid="DEADBEEF")


def test_pyocd_full_chip_flash_sequence(pyocd, monkeypatch, tmp_path):
    runner = _Runner(monkeypatch, {"list --probes": (PROBE_TABLE, 0)})
    boot, app = _images(tmp_path)
    pyocd.full_chip_flash(boot, app)
    steps = [(c[1], c[2] if len(c) > 2 else None) for c in runner.commands]
    assert [s[0] for s in steps] == ["list", "erase", "flash", "flash", "commander", "commander", "reset"]
    assert runner.commands[1][-1] == "--chip"
    boot_cmd, app_cmd = runner.commands[2], runner.commands[3]
    assert "0x08000000" in boot_cmd and boot_cmd[-1] == boot
    assert "0x08008000" in app_cmd and app_cmd[-1] == app
    assert "compare 0x08000000" in runner.commands[4][-1]
    assert "compare 0x08008000" in runner.commands[5][-1]


def test_pyocd_hex_images_carry_their_own_address_and_skip_the_compare(pyocd, monkeypatch, tmp_path):
    runner = _Runner(monkeypatch, {"list --probes": (PROBE_TABLE, 0)})
    boot, app = _images(tmp_path, "boot.hex", "app.hex")
    pyocd.full_chip_flash(boot, app)
    assert "--base-address" not in " ".join(" ".join(c) for c in runner.commands)
    assert "commander" not in runner.verbs()


def test_pyocd_probe_selection_reaches_every_command(pyocd, monkeypatch, tmp_path):
    runner = _Runner(monkeypatch, {"list --probes": (TWO_PROBES, 0)})
    boot, app = _images(tmp_path)
    pyocd.full_chip_flash(boot, app, probe_uid="AAAA00000000000000000000")
    for command in runner.commands[1:]:
        assert command[command.index("--probe") + 1] == "AAAA00000000000000000000"


def test_pyocd_backup_is_taken_before_the_erase(pyocd, monkeypatch, tmp_path):
    backup = tmp_path / "backup.bin"
    runner = _Runner(monkeypatch, {"list --probes": (PROBE_TABLE, 0)})
    original = runner._popen

    def write_backup(cmd, **kwargs):
        if "savemem" in " ".join(cmd):
            backup.write_bytes(b"\x01" * 32)
        return original(cmd, **kwargs)
    monkeypatch.setattr(swd.subprocess, "Popen", write_backup)
    boot, app = _images(tmp_path)
    pyocd.full_chip_flash(boot, app, backup_path=str(backup))
    order = [c[1] for c in runner.commands]
    assert order.index("commander") < order.index("erase")


def test_pyocd_stops_before_the_erase_when_the_backup_is_empty(pyocd, monkeypatch, tmp_path):
    runner = _Runner(monkeypatch, {"list --probes": (PROBE_TABLE, 0)})
    boot, app = _images(tmp_path)
    with pytest.raises(SWDFlashError, match="Backup"):
        pyocd.full_chip_flash(boot, app, backup_path=str(tmp_path / "missing.bin"))
    assert "erase" not in runner.verbs()


def test_pyocd_dry_run_touches_nothing(pyocd, monkeypatch, tmp_path):
    runner = _Runner(monkeypatch)
    boot, app = _images(tmp_path)
    pyocd.full_chip_flash(boot, app, dry_run=True, backup_path=str(tmp_path / "b.bin"))
    assert runner.commands == []


def test_pyocd_programming_failure_stops_the_sequence(pyocd, monkeypatch, tmp_path):
    runner = _Runner(monkeypatch, {"list --probes": (PROBE_TABLE, 0), "flash": ("Error: write failed", 0)})
    boot, app = _images(tmp_path)
    with pytest.raises(SWDFlashError):
        pyocd.full_chip_flash(boot, app)
    assert "reset" not in runner.verbs()


# ---- STM32CubeProgrammer -----------------------------------------------------------------
CUBE_PROBE = "ST-LINK SN  : 066DFF303535414D43092031\n"
CUBE_TWO = CUBE_PROBE + "ST-LINK SN  : 0670FF303535414D43092099\n"


def test_cube_lists_probe_serials(cube, monkeypatch):
    _Runner(monkeypatch, {"-l": (CUBE_TWO, 0)})
    assert cube.list_probes() == ["066DFF303535414D43092031", "0670FF303535414D43092099"]


def test_cube_without_the_tool_lists_nothing(monkeypatch):
    monkeypatch.setattr(swd, "_find_executable", lambda names: None)
    monkeypatch.setattr(swd, "_search_windows_registry_for_stm32cubeprogrammer", lambda: None)
    monkeypatch.setattr(swd.os.path, "isfile", lambda path: False)
    tool = CubeProgrammerCLI()
    assert tool.exe is None and tool.list_probes() == []


def test_cube_full_chip_flash_sequence(cube, monkeypatch, tmp_path):
    runner = _Runner(monkeypatch, {"-l": (CUBE_PROBE, 0), "-c port=SWD": ("Connected\nDevice ID : 0x422\n", 0)})
    boot, app = _images(tmp_path)
    cube.full_chip_flash(boot, app)
    flat = [" ".join(c) for c in runner.commands]
    erase = [i for i, c in enumerate(flat) if "-e all" in c]
    writes = [i for i, c in enumerate(flat) if " -w " in c]
    assert len(erase) == 1 and len(writes) == 2 and erase[0] < writes[0] < writes[1]
    assert "0x08000000" in flat[writes[0]] and "0x08008000" in flat[writes[1]]
    assert flat[writes[1]].rstrip().endswith("-v -rst")
    assert all("-ob" not in c or "displ" in c for c in flat), "option bytes are never written"


def test_cube_backup_failure_stops_before_the_erase(cube, monkeypatch, tmp_path):
    runner = _Runner(monkeypatch, {"-l": (CUBE_PROBE, 0), "-c port=SWD": ("Device ID : 0x422\n", 0)})
    boot, app = _images(tmp_path)
    with pytest.raises(SWDFlashError, match="Backup"):
        cube.full_chip_flash(boot, app, backup_path=str(tmp_path / "nothing.bin"))
    assert not any("-e all" in " ".join(c) for c in runner.commands)


def test_cube_dry_run_touches_nothing(cube, monkeypatch, tmp_path):
    runner = _Runner(monkeypatch)
    boot, app = _images(tmp_path)
    cube.full_chip_flash(boot, app, dry_run=True)
    assert runner.commands == []


def test_cube_refuses_to_guess_between_two_probes(cube, monkeypatch):
    _Runner(monkeypatch, {"-l": (CUBE_TWO, 0)})
    with pytest.raises(SWDFlashError, match="refusing to guess"):
        cube.check_connection()


def test_cube_needs_a_connection_confirmation(cube, monkeypatch):
    _Runner(monkeypatch, {"-l": (CUBE_PROBE, 0), "-c port=SWD": ("nothing useful\n", 0)})
    with pytest.raises(SWDFlashError, match="Couldn't confirm"):
        cube.check_connection()


def test_cube_reports_a_failed_connection(cube, monkeypatch):
    _Runner(monkeypatch, {"-l": (CUBE_PROBE, 0), "-c port=SWD": ("Error: No STLink detected\n", 0)})
    with pytest.raises(SWDFlashError, match="reported a failure"):
        cube.check_connection()
