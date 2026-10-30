# =============================================================================
# URTC-FLASHER - tests/test_window_guide.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The guide of the window: its pictures exist and are real PNG files, the guide shows each of them and every README (the eight languages) points to the guide and shows the first one."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROGRAM = "flasher"
SUFFIXES = ["", "-es", "-de", "-fr", "-it", "-ja", "-zh", "-pt"]   # English and the seven other languages of the program
PICTURES = [f"{PROGRAM}-{screen}{suffix}.png" for suffix in SUFFIXES for screen in ("deck", "help", "updates", "heads")]
READMES = ["README.md", "README_spa.md", "README_fra.md", "README_ita.md", "README_deu.md", "README_jpn.md", "README_zho.md", "README_por.md"]


def test_the_pictures_are_png_files_of_the_size_of_the_window():
    for name in PICTURES:
        data = (ROOT / "docs" / "screenshots" / name).read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) > 20_000, name
        width, height = int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
        assert (width, height) == (1440, 900), (name, width, height)


def test_the_guide_shows_every_picture_and_every_link_in_it_exists():
    guide = (ROOT / "docs" / "WINDOW_GUIDE.md").read_text(encoding="utf-8")
    for name in PICTURES:
        assert f"screenshots/{name}" in guide, name
    for target in re.findall(r"\]\(([^)#]+)\)", guide):
        assert (ROOT / "docs" / target).is_file(), target


def test_every_readme_points_to_the_guide_and_shows_the_window():
    for readme in READMES:
        text = (ROOT / readme).read_text(encoding="utf-8")
        assert "docs/WINDOW_GUIDE.md" in text and "images/screenshots/deck.png" in text, readme


def test_the_script_that_takes_the_pictures_is_there_and_names_this_program():
    source = (ROOT / "tools" / "capture_screens.py").read_text(encoding="utf-8")
    assert "grabWindow" in source and "QT_QPA_PLATFORM" in source and PROGRAM in source
    assert "--all-languages" in source and all(suffix in source for suffix in SUFFIXES if suffix)
