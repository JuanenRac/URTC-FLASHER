# =============================================================================
# URTC-FLASHER - tests/test_qt_status_translation.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The status line of the window is shown in the language of the program: every status the window sets has a text in the eight languages."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

import flasher_config as config

ROOT = Path(__file__).resolve().parent.parent
LANGUAGES = ("english", "spanish", "german", "french", "italian", "japanese", "chinese", "portuguese")


def _statuses() -> set[str]:
    """The uppercase words of every literal status the window sets (the part of an f-string before its first brace is the word to translate)."""
    source = (ROOT / "qt_flasher.py").read_text(encoding="utf-8")
    found: set[str] = set()
    for call in re.findall(r"_set_state\(status=([^\n]*)", source):
        for literal in re.findall(r'f?"([A-Z][A-Z0-9 -]*[A-Z0-9])[ {"]', call):
            found.add(literal.strip())
    found.add(re.search(r'self\._status = "([A-Z -]+)"', source).group(1))
    return found


def test_the_window_sets_a_known_set_of_statuses():
    statuses = _statuses()
    assert {"READY", "CONNECTING", "DISCONNECTED", "CONNECTION FAILED"} <= statuses
    assert len(statuses) >= 10


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_status_has_a_text_in_every_language(language):
    table = config.load_language(language)
    missing = [token for token in sorted(_statuses()) if "QTSTATUS_" + re.sub(r"[^A-Z0-9]+", "_", token).strip("_") not in table]
    assert missing == [], language


def test_a_status_is_translated_and_what_follows_it_is_kept(monkeypatch):
    monkeypatch.setattr(config, "_translations", config.load_language("german"))
    assert config.translate_status("CONNECTED COM3") == "VERBUNDEN COM3"
    assert config.translate_status("READY") == "BEREIT"
    monkeypatch.setattr(config, "_translations", config.load_language("japanese"))
    assert config.translate_status("DISCONNECTED") == "切断済み"
    assert config.translate_status("SOMETHING ELSE") == "SOMETHING ELSE"


def test_a_token_that_is_no_status_is_left_alone(monkeypatch):
    monkeypatch.setattr(config, "_translations", config.load_language("spanish"))
    assert config.translate_status("NO_SUCH_TOKEN") == "NO_SUCH_TOKEN"
