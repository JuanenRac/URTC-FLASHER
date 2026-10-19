# =============================================================================
# URTC-COMMON - src/urtc_ui/__init__.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Pieces the URTC desktop programs share: the language list and its selector model, status badges and the formatting
of identifiers, bitrates, frames, sizes and durations.

Nothing here imports Qt, so the logic is tested without a display. A program binds these helpers to its own Qt or QML
objects; the programs do not use this package yet.
"""
from __future__ import annotations

from .formatting import (format_bitrate, format_bytes, format_can_id, format_duration_ms, format_frame, format_hex,
                         format_uptime, parse_bitrate, parse_can_id)
from .languages import DEFAULT_LANGUAGE, LANGUAGES, LanguageModel, normalize_language
from .status import Badge, Level, badge_for, connection_badge

__all__ = [
    "Badge", "DEFAULT_LANGUAGE", "LANGUAGES", "LanguageModel", "Level", "badge_for", "connection_badge",
    "format_bitrate", "format_bytes", "format_can_id", "format_duration_ms", "format_frame", "format_hex",
    "format_uptime", "normalize_language", "parse_bitrate", "parse_can_id",
]
