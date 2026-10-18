# =============================================================================
# URTC Flasher - tests/test_qt_bridge_log.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The Qt Quick deck keeps a bounded log and shows it in the interface language."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

pytest.importorskip("PySide6")
import flasher_config  # noqa: E402
import qt_flasher  # noqa: E402
from flasher_config import load_language  # noqa: E402


def test_the_log_is_bounded_and_keeps_the_newest_lines():
    bridge = qt_flasher.FlasherQtBridge()
    for n in range(qt_flasher.FlasherQtBridge.MAX_LOG_LINES + 50):
        bridge._append_log(f"line {n}")
    assert len(bridge._logs) == qt_flasher.FlasherQtBridge.MAX_LOG_LINES
    assert bridge.logs[-1] == f"line {qt_flasher.FlasherQtBridge.MAX_LOG_LINES + 49}"
    assert len(bridge.logs) == 12


def test_log_lines_and_the_status_are_shown_in_the_interface_language(monkeypatch):
    monkeypatch.setattr(flasher_config, "_translations", load_language("german"))
    bridge = qt_flasher.FlasherQtBridge()
    bridge._append_log("FLASH_COMPLETE")
    assert bridge.logs[-1] == "Update abgeschlossen"
    bridge._set_state(status="FLASH_FAILED boom")
    assert bridge.status == "Update fehlgeschlagen: boom"
    bridge._set_state(status="Ready")
    assert bridge.status == "Ready"
