# =============================================================================
# URTC Flasher - tests/test_language_files.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""All 8 language files have the same keys and the same placeholders, and every key the
code asks for exists."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from flasher_config import load_language

ROOT = Path(__file__).resolve().parent.parent
LANGUAGES = ["english", "spanish", "german", "french", "italian", "japanese", "chinese", "portuguese"]
PLACEHOLDER = re.compile(r"\{(\w+)(?::[^}]*)?\}")


def _all():
    return {name: load_language(name) for name in LANGUAGES}


def test_every_language_has_the_same_keys():
    tables = _all()
    english = set(tables["english"])
    for name, table in tables.items():
        assert set(table) == english, (name, sorted(english ^ set(table))[:10])


def test_every_language_uses_the_same_placeholders_and_no_value_is_empty():
    tables = _all()
    for key, text in tables["english"].items():
        wanted = sorted(PLACEHOLDER.findall(text))
        for name, table in tables.items():
            assert table[key].strip(), (name, key)
            assert sorted(PLACEHOLDER.findall(table[key])) == wanted, (name, key)


def test_the_portuguese_file_is_portugal_portuguese_not_a_copy_of_the_english_one():
    tables = _all()
    different = sum(1 for key, text in tables["portuguese"].items() if text != tables["english"][key])
    assert different > len(tables["english"]) * 0.8


def _keys_used_in_code():
    used = set()
    for path in ROOT.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        used.update(re.findall(r"""\b_\(\s*["']([A-Z][A-Z0-9_]+)["']""", text))
        used.update(re.findall(r"""\.uiText\(\s*["']([A-Z][A-Z0-9_]+)["']""", text))
    for path in (ROOT / "assets" / "qml").glob("*.qml"):
        used.update(re.findall(r"""uiText\(\s*["']([A-Z][A-Z0-9_]+)["']""", path.read_text(encoding="utf-8")))
    return used


def test_every_key_the_code_asks_for_exists():
    english = load_language("english")
    missing = sorted(key for key in _keys_used_in_code() if key not in english)
    assert missing == []


def test_the_error_messages_of_the_protocol_are_translated_not_hard_coded():
    source = (ROOT / "flasher_protocol.py").read_text(encoding="utf-8")
    assert not re.search(r"""FlashError\(\s*f?["']""", source)


@pytest.mark.parametrize("name", LANGUAGES)
def test_the_language_files_are_read_as_utf8(name):
    (ROOT / "language" / f"{name}.lng").read_bytes().decode("utf-8-sig")
