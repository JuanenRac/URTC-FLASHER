# =============================================================================
# URTC-FLASHER - tests/test_readme_test_files.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The tree of the README files states how many test files there are: the number of the tests folder."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_the_tree_of_every_readme_states_the_number_of_test_files():
    files = len(list((ROOT / "tests").glob("test_*.py")))
    readmes = sorted(ROOT.glob("README*.md"))
    assert len(readmes) == 8
    for readme in readmes:
        stated = re.findall(r"^\u251c\u2500\u2500 tests/\s+(\d+)", readme.read_text(encoding="utf-8"), re.MULTILINE)
        assert stated == [str(files)], readme.name
