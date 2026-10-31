# =============================================================================
# URTC-FLASHER - tests/test_qt_history.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The history window in the flasher: it reads the evidence records the flasher wrote in its logs folder, checks each one, speaks the language of the
program and sits in the deck next to the other dialogs."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import QCoreApplication  # noqa: E402

import qt_flasher  # noqa: E402
from urtc_can import evidence  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def qt_app():
    yield QCoreApplication.instance() or QCoreApplication([])


def write_record(folder: Path, name: str, when: str, board: str, edited: bool = False) -> None:
    record = evidence.build(kind="flash", outcome="pass", timestamp_utc=when, tool="URTC-FLASHER", tool_version="0.4.2",
                            subject={"name": board, "version_before": "0.3.9", "version_after": "0.4.1"},
                            artifacts=[{"name": "fw.bin", "sha256": "c" * 64, "bytes": 10}])
    if edited:
        record["outcome"] = "fail"
    (folder / name).write_text(json.dumps(record), encoding="utf-8")


def test_the_window_lists_the_records_of_the_logs_folder_and_flags_an_edited_one(qt_app, tmp_path, monkeypatch):
    monkeypatch.setattr(qt_flasher, "LOGS_FOLDER", str(tmp_path))
    write_record(tmp_path, "urtc_evidence_a.json", "2026-01-01T10:00:00Z", "main-board")
    write_record(tmp_path, "urtc_evidence_b.json", "2026-01-02T10:00:00Z", "other-board", edited=True)
    bridge = qt_flasher.FlasherQtBridge()
    assert bridge.history is bridge.history
    rows = bridge.history.rows
    assert [r["board"] for r in rows] == ["other-board", "main-board"] and [r["valid"] for r in rows] == [False, True]
    assert bridge.history.summaryText == "2 of 2 record(s) shown; 1 valid, 1 not valid"


def test_the_window_is_in_the_deck_with_a_button_that_opens_it():
    deck = (ROOT / "assets" / "qml" / "FlasherDeck.qml").read_text(encoding="utf-8")
    assert "EvidenceHistoryDialog {" in deck and "model: flasherBackend.history" in deck and "historyDialog.open()" in deck
    assert (ROOT / "assets" / "qml" / "EvidenceHistoryDialog.qml").is_file()
