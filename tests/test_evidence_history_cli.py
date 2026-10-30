# =============================================================================
# URTC-FLASHER - tests/test_evidence_history_cli.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""``urtc_flasher.py --history FOLDER``: the evidence records of a folder, listed and checked, with no bus involved."""
from __future__ import annotations

import json

import urtc_flasher
from urtc_can import evidence


def _record(when: str, outcome: str = "pass") -> dict:
    return evidence.build(kind="flash", outcome=outcome, timestamp_utc=when, tool="URTC-FLASHER", tool_version="0.4.2",
                          subject={"name": "head-1", "version_before": "0.3.9", "version_after": "0.4.1"})


def test_the_history_lists_the_records_newest_first_and_exits_zero(tmp_path, capsys):
    (tmp_path / "urtc_evidence_a.json").write_text(json.dumps(_record("2026-01-01T10:00:00Z")), encoding="utf-8")
    (tmp_path / "urtc_evidence_b.json").write_text(json.dumps(_record("2026-02-01T10:00:00Z", "fail")), encoding="utf-8")
    assert urtc_flasher.run_history([str(tmp_path)]) == 0
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert len(lines) == 2 and lines[0].startswith("2026-02-01") and "0.3.9 -> 0.4.1" in lines[0]
    assert urtc_flasher.run_history([str(tmp_path), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["summary"]["records"] == 2


def test_a_record_edited_after_it_was_written_makes_the_history_fail(tmp_path, capsys):
    edited = _record("2026-01-01T10:00:00Z")
    edited["outcome"] = "fail"
    (tmp_path / "urtc_evidence_a.json").write_text(json.dumps(edited), encoding="utf-8")
    assert urtc_flasher.run_history([str(tmp_path)]) == 1
    assert "NOT VALID" in capsys.readouterr().out


def test_a_missing_folder_is_a_usage_error(tmp_path, capsys):
    assert urtc_flasher.run_history([str(tmp_path / "missing")]) == 2
    assert "not a folder" in capsys.readouterr().err
