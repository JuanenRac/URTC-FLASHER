# =============================================================================
# URTC-COMMON - src/urtc_ui/status.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Status badges: a level, a colour and a translation key, so every program shows the same state the same way."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Level(str, Enum):
    OK = "ok"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"
    UNKNOWN = "unknown"


# Foreground colours chosen to read on both a light and a dark background.
_COLOURS = {
    Level.OK: "#2e9e5b",
    Level.INFO: "#2f7fd0",
    Level.WARN: "#d08a1a",
    Level.ERROR: "#d0412f",
    Level.UNKNOWN: "#7a8591",
}


@dataclass(frozen=True)
class Badge:
    level: Level
    colour: str
    key: str  # the translation key a program looks up in its own language files


def badge_for(level: Level | str) -> Badge:
    """The badge of a level (a Level or its text); an unknown text gives the UNKNOWN badge."""
    try:
        value = level if isinstance(level, Level) else Level(str(level).lower())
    except ValueError:
        value = Level.UNKNOWN
    return Badge(value, _COLOURS[value], f"STATUS_{value.name}")


def connection_badge(connected: bool | None, listening_only: bool = False) -> Badge:
    """Connected, listen-only (connected but sending nothing), disconnected, or unknown when the state has not been read."""
    if connected is None:
        return badge_for(Level.UNKNOWN)
    if not connected:
        return Badge(Level.ERROR, _COLOURS[Level.ERROR], "STATUS_DISCONNECTED")
    if listening_only:
        return Badge(Level.INFO, _COLOURS[Level.INFO], "STATUS_LISTEN_ONLY")
    return Badge(Level.OK, _COLOURS[Level.OK], "STATUS_CONNECTED")
