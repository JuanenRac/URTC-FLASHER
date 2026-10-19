# =============================================================================
# URTC Flasher - tests/test_language_selector.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The window offers the eight languages, saves the choice and says it applies on the next start."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

pytest.importorskip("PySide6")
import flasher_config  # noqa: E402
import qt_flasher  # noqa: E402


def test_the_eight_languages_are_offered_each_in_its_own_name():
    bridge = qt_flasher.FlasherQtBridge()
    assert len(bridge.languageNames) == 8
    assert "Português" in bridge.languageNames and "日本語" in bridge.languageNames


def test_choosing_another_language_saves_it_and_returns_the_restart_notice(monkeypatch):
    saved = []
    monkeypatch.setattr(qt_flasher, "save_config", lambda updates: saved.append(updates) or True)
    bridge = qt_flasher.FlasherQtBridge()
    other = next(index for index, (code, _name) in enumerate(flasher_config.AVAILABLE_LANGUAGES) if code != qt_flasher._current_language)
    assert bridge.selectLanguage(other)
    assert saved == [{"language": flasher_config.AVAILABLE_LANGUAGES[other][0]}]


def test_the_current_language_and_an_invalid_index_save_nothing(monkeypatch):
    saved = []
    monkeypatch.setattr(qt_flasher, "save_config", lambda updates: saved.append(updates) or True)
    bridge = qt_flasher.FlasherQtBridge()
    assert bridge.selectLanguage(bridge.languageIndex) == ""
    assert bridge.selectLanguage(99) == "" and bridge.selectLanguage(-1) == ""
    assert saved == []


def test_the_list_and_the_selector_come_from_the_shared_interface_package():
    import urtc_ui
    import flasher_config

    assert flasher_config.AVAILABLE_LANGUAGES == list(urtc_ui.LANGUAGES)
    bridge = qt_flasher.FlasherQtBridge()
    assert bridge.languageNames == urtc_ui.LanguageModel().names()
    assert bridge.languageIndex == urtc_ui.LanguageModel(qt_flasher._current_language).index()


def test_the_status_line_takes_its_colour_from_the_shared_connection_badge():
    import urtc_ui

    bridge = qt_flasher.FlasherQtBridge()
    assert bridge.statusColor == urtc_ui.connection_badge(None).colour
    bridge._transport = object()
    assert bridge.statusColor == urtc_ui.connection_badge(True).colour
