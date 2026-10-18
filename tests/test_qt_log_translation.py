# =============================================================================
# URTC Flasher - tests/test_qt_log_translation.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""The log lines of the Qt Quick deck start with a token; it is shown in the interface language."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import flasher_config
from flasher_config import load_language, translate_log_line

ROOT = Path(__file__).resolve().parent.parent
LANGUAGES = ("english", "spanish", "german", "french", "italian", "japanese", "chinese", "portuguese")


def test_a_known_token_is_translated_and_its_detail_is_kept(monkeypatch):
    monkeypatch.setattr(flasher_config, "_translations", load_language("spanish"))
    assert translate_log_line("PORT_SCAN count=3") == "Búsqueda de puertos: count=3"
    assert translate_log_line("FLASH_COMPLETE") == "Actualización terminada"


def test_a_whole_sentence_label_replaces_the_english_detail(monkeypatch):
    monkeypatch.setattr(flasher_config, "_translations", load_language("german"))
    text = translate_log_line("FIRMWARE_SCAN_BLOCKED operation in progress")
    assert "operation in progress" not in text and "blockiert" in text


def test_an_unknown_line_is_returned_unchanged(monkeypatch):
    monkeypatch.setattr(flasher_config, "_translations", load_language("english"))
    assert translate_log_line("Connected to COM3") == "Connected to COM3"
    assert translate_log_line("SOMETHING_NEW detail") == "SOMETHING_NEW detail"
    assert translate_log_line("") == ""


def test_every_token_the_deck_logs_has_a_label_in_every_language():
    source = (ROOT / "qt_flasher.py").read_text(encoding="utf-8")
    tokens = set(re.findall(r"""(?:_log|emit)\(\s*f?["']([A-Z][A-Z0-9_]+)""", source))
    tokens = {t for t in tokens if not t.endswith("_")}  # IMAGE_DIGEST_{VERIFIED,RECORDED} and IMAGE_RELEASE_{SIGNED,UNSIGNED} are built from two parts and listed below
    tokens |= {"IMAGE_DIGEST_VERIFIED", "IMAGE_DIGEST_RECORDED", "IMAGE_RELEASE_SIGNED", "IMAGE_RELEASE_UNSIGNED"}
    assert {"PORT_SCAN", "FLASH_FAILED", "SWD_FLASH_STARTED", "IMAGE_REFUSED"} <= tokens
    for language in LANGUAGES:
        table = load_language(language)
        assert [t for t in sorted(tokens) if "QTLOG_" + t not in table] == [], language
