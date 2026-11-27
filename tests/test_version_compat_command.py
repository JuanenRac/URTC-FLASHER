# =============================================================================
# URTC Flasher - tests/test_version_compat_command.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The workshop tool for the signed command of the version rule: it signs with a key file it is given, and its frames are accepted by the reference of the
bootloader only for the right head, once."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))

import version_compat_command  # noqa: E402
from urtc_can import ed25519, slcan, version_compat  # noqa: E402

UID = (0xCAFEBABE, 0x0BADF00D, 0x12345678)
CURRENT = 0x00C0FFEE


def run(tmp_path, capsys, *extra, mode="accept_patchless", counter="3", seed=None):
    seed = seed or os.urandom(32)                      # an ephemeral key: the tests never read a key of the workshop
    key = tmp_path / "ephemeral.key"
    key.write_text(seed.hex(), encoding="ascii")
    code = version_compat_command.main(["--key-file", str(key), "--uid", "CAFEBABE,0BADF00D,12345678", "--current-serial", f"{CURRENT:08X}",
                                        "--mode", mode, "--counter", counter, *extra])
    return code, capsys.readouterr().out, seed


def frames_of(out):
    return [slcan.decode_line(line) for line in out.splitlines() if line.startswith("t7EE")]


def test_without_yes_it_only_describes_and_signs_nothing(tmp_path, capsys):
    code, out, _ = run(tmp_path, capsys)
    assert code == 2 and "VERSION_COMPAT_COMMAND=PLAN" in out and "t7EE" not in out


@pytest.mark.parametrize("mode", ["strict", "accept_patchless"])
def test_the_twelve_frames_rebuild_a_command_that_the_bootloader_accepts_once(tmp_path, capsys, mode):
    code, out, seed = run(tmp_path, capsys, "--yes", mode=mode)
    assert code == 0 and "VERSION_COMPAT_COMMAND=MADE" in out
    frames = frames_of(out)
    assert len(frames) == 12 and all(f is not None and f.id == 0x7EE and len(f.data) == 8 for f in frames)
    command = b"".join(bytes(f.data[1:]) for f in sorted(frames, key=lambda f: f.data[0]))
    public = ed25519.public_key(seed)
    wanted = version_compat.MODE_NAMES[mode]
    assert version_compat.decide(command, UID, CURRENT, [public], 0) == (version_compat.OK, wanted, 3)
    assert version_compat.decide(command, UID, CURRENT, [public], 3)[0] == version_compat.REPLAY
    assert version_compat.decide(command, (UID[0], UID[1], UID[2] ^ 1), CURRENT, [public], 0)[0] == version_compat.BAD_SIGNATURE
    assert version_compat.decide(command, UID, CURRENT, [ed25519.public_key(os.urandom(32))], 0)[0] == version_compat.UNKNOWN_KEY


def test_the_query_needs_no_key_and_prints_one_frame_that_changes_nothing(capsys):
    assert version_compat_command.main(["--query"]) == 0
    frames = frames_of(capsys.readouterr().out)
    assert len(frames) == 1 and bytes(frames[0].data) == version_compat.query_frame()


def test_a_missing_argument_or_a_counter_out_of_range_makes_nothing(tmp_path, capsys):
    with pytest.raises(SystemExit):
        version_compat_command.main(["--mode", "strict", "--yes"])
    with pytest.raises(SystemExit):
        run(tmp_path, capsys, "--yes", counter="0")
    assert "t7EE" not in capsys.readouterr().out
