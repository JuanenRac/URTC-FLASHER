# =============================================================================
# URTC Flasher - tests/test_serial_command.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The workshop tool that makes the signed command for the serial number of a bootloader: it signs with a key file it is given, never looks for one, and its frames
are accepted by the reference of the bootloader only for the right head."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))

import serial_command  # noqa: E402
from urtc_can import bl_select, bl_serial, ed25519, slcan  # noqa: E402

UID = (0xCAFEBABE, 0x0BADF00D, 0x12345678)
CURRENT = bl_select.serial_from_uid(*UID)


def run(tmp_path, capsys, *extra, seed=None):
    seed = seed or os.urandom(32)                      # an ephemeral key: the tests never read a key of the workshop
    key = tmp_path / "ephemeral.key"
    key.write_text(seed.hex(), encoding="ascii")
    code = serial_command.main(["--key-file", str(key), "--uid", "CAFEBABE,0BADF00D,12345678", "--current-serial", f"{CURRENT:08X}", "--serial", "00C0FFEE",
                                "--counter", "3", *extra])
    return code, capsys.readouterr().out, seed


def frames_of(out):
    lines = [line for line in out.splitlines() if line.startswith("t7EE")]
    return [slcan.decode_line(line) for line in lines]


def test_without_yes_it_only_describes_and_signs_nothing(tmp_path, capsys):
    code, out, _ = run(tmp_path, capsys)
    assert code == 2 and "SERIAL_COMMAND=PLAN" in out and "t7EE" not in out


def test_the_twelve_frames_rebuild_a_command_that_the_bootloader_accepts_for_this_head_only(tmp_path, capsys):
    code, out, seed = run(tmp_path, capsys, "--yes")
    assert code == 0 and "SERIAL_COMMAND=MADE" in out and "EXPECT t7EF5 00 00C0FFEE" in out
    frames = frames_of(out)
    assert len(frames) == 12 and all(f is not None and f.id == 0x7EE and len(f.data) == 8 for f in frames)
    command = b"".join(bytes(f.data[1:]) for f in sorted(frames, key=lambda f: f.data[0]))
    public = ed25519.public_key(seed)
    assert bl_serial.decide(command, UID, CURRENT, [public], 0) == (bl_serial.OK, 0x00C0FFEE, 3)
    assert bl_serial.decide(command, UID, CURRENT, [public], 3)[0] == bl_serial.REPLAY
    assert bl_serial.decide(command, (UID[0], UID[1], UID[2] ^ 1), CURRENT, [public], 0)[0] == bl_serial.BAD_SIGNATURE
    assert bl_serial.decide(command, UID, CURRENT, [ed25519.public_key(os.urandom(32))], 0)[0] == bl_serial.UNKNOWN_KEY


def test_the_key_file_may_hold_the_raw_seed(tmp_path, capsys):
    seed = os.urandom(32)
    key = tmp_path / "raw.key"
    key.write_bytes(seed)
    assert serial_command.read_seed(key) == seed


@pytest.mark.parametrize("content", [b"not a key", b"ab" * 10, b""])
def test_a_file_that_is_not_a_seed_is_refused(tmp_path, content):
    key = tmp_path / "bad.key"
    key.write_bytes(content)
    with pytest.raises(SystemExit):
        serial_command.read_seed(key)


def test_a_serial_that_is_no_serial_a_bad_uid_and_a_bad_counter_are_refused(tmp_path, capsys):
    key = tmp_path / "k"
    key.write_text(os.urandom(32).hex(), encoding="ascii")
    base = ["--key-file", str(key), "--uid", "1,2,3", "--current-serial", "1"]
    for extra in (["--serial", "0", "--counter", "1"], ["--serial", "FFFFFFFF", "--counter", "1"], ["--serial", "5", "--counter", "0"]):
        with pytest.raises(SystemExit):
            serial_command.main([*base, *extra, "--yes"])
    with pytest.raises(SystemExit):
        serial_command.main(["--key-file", str(key), "--uid", "1,2", "--current-serial", "1", "--serial", "5", "--counter", "1", "--yes"])


def test_the_tool_never_looks_for_a_key_of_the_workshop():
    source = (ROOT / "tools" / "serial_command.py").read_text(encoding="utf-8")
    assert "expanduser" not in source and "Path.home" not in source and ".urtc-keys" not in source.replace("NEVER looked for", "")
