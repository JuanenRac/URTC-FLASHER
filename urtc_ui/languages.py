# =============================================================================
# URTC-COMMON - src/urtc_ui/languages.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The eight interface languages and the model behind a language selector.

The codes are the ones the URTC programs store in their configuration files (``english``, ``spanish`` ...). The list is
the same in every program: English, Spanish, Italian, French, German, Simplified Chinese, Japanese and Portuguese
(Portugal), each named in its own language.
"""
from __future__ import annotations

from dataclasses import dataclass

DEFAULT_LANGUAGE = "english"

LANGUAGES: tuple[tuple[str, str], ...] = (
    ("english", "English"),
    ("spanish", "Español"),
    ("italian", "Italiano"),
    ("french", "Français"),
    ("german", "Deutsch"),
    ("chinese", "简体中文"),
    ("japanese", "日本語"),
    ("portuguese", "Português"),
)

# ISO 639-1 codes (and the common regional forms) that map onto a stored code.
_ISO = {"en": "english", "es": "spanish", "it": "italian", "fr": "french", "de": "german", "zh": "chinese", "ja": "japanese", "pt": "portuguese"}


def normalize_language(value: str | None) -> str:
    """The stored code for a stored code, an ISO code or a locale name ('pt_PT', 'zh-CN', 'de_DE.UTF-8'); English when unknown."""
    if not value or not isinstance(value, str):
        return DEFAULT_LANGUAGE
    text = value.strip().lower()
    if text in dict(LANGUAGES):
        return text
    head = text.replace("-", "_").split(".")[0].split("_")[0]
    return _ISO.get(head, DEFAULT_LANGUAGE)


@dataclass
class LanguageModel:
    """What a language selector needs: the names to show, the index of the current language and the code of a chosen index."""

    current: str = DEFAULT_LANGUAGE

    def __post_init__(self) -> None:
        self.current = normalize_language(self.current)

    def names(self) -> list[str]:
        return [name for _code, name in LANGUAGES]

    def codes(self) -> list[str]:
        return [code for code, _name in LANGUAGES]

    def index(self) -> int:
        return self.codes().index(self.current)

    def code_at(self, index: int) -> str | None:
        """The code at a selector position, or None when the position is outside the list."""
        if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(LANGUAGES):
            return None
        return LANGUAGES[index][0]

    def choose(self, index: int) -> str | None:
        """Select a position. Returns the new code when the language changed, None when nothing changed or the index is invalid."""
        code = self.code_at(index)
        if code is None or code == self.current:
            return None
        self.current = code
        return code
