# =============================================================================
# URTC-FLASHER - tests/test_evidence_signing.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The Ed25519 signature of the evidence records the flasher writes (off by default, the key from a file and never printed, fail-closed) and the trust store of
public keys in its history."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import flasher_config
import flasher_records
import urtc_flasher
from flasher_config import THIS_HARDWARE_ID
from flasher_records import build_update_report, seal_evidence, write_evidence_record, write_update_report
from urtc_can import evidence, record_signing

SEED = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
OTHER = bytes.fromhex("4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb")
PUB, OTHER_PUB = record_signing.public_key(SEED), record_signing.public_key(OTHER)


def _report(**over):
    args = dict(tool_version="0.4.5", image_path="x/URTC_MAIN_FIRMWARE_v0.3.3.bin", image_sha256="ab" * 32, image_size=73476, target="master",
                installed=(0, 2), new=(0, 3), hardware_id=THIS_HARDWARE_ID, signing_key_kind="dev", result="success", operator="bench", timestamp="2026-01-02T03:04:05Z")
    args.update(over)
    return build_update_report(**args)


def _config(monkeypatch, config):
    monkeypatch.setattr(flasher_config, "load_config", lambda: config)


@pytest.fixture
def key_file(tmp_path, monkeypatch):
    path = tmp_path / "keys" / "records.key"
    path.parent.mkdir()
    path.write_text(SEED.hex() + "\n", encoding="ascii")
    monkeypatch.setenv(record_signing.KEY_ENV, str(path))
    return path


def _written(folder: Path) -> dict:
    (path,) = sorted(folder.glob("urtc_evidence_*.json"))
    return json.loads(path.read_text(encoding="utf-8"))


# -- the setting -------------------------------------------------------------------------------------------------------------------------
def test_the_setting_is_off_unless_it_is_exactly_true():
    assert flasher_config.evidence_signing_settings({}) == (False, "")
    for value in ("true", "yes", 1, None, "false", False):
        assert flasher_config.evidence_signing_settings({"sign_evidence": value})[0] is False
    assert flasher_config.evidence_signing_settings({"sign_evidence": True, "record_key_file": "/k/x"}) == (True, "/k/x")


def test_the_report_signature_setting_is_a_different_switch(monkeypatch):
    _config(monkeypatch, {"sign_update_reports": True})        # signs the report, which is on by default; the evidence stays unsigned
    assert flasher_config.evidence_signing_settings()[0] is False


# -- characterization: the evidence record is what it was unless the switch is on ------------------------------------------------------------
def test_by_default_the_evidence_record_is_not_signed(tmp_path, monkeypatch, key_file):
    _config(monkeypatch, {})
    path = write_update_report(_report(), str(tmp_path))
    write_evidence_record(_report(), path)
    record = _written(tmp_path)
    assert "signature" not in record and evidence.verify(record) == []


# -- signing -----------------------------------------------------------------------------------------------------------------------------
def test_with_the_switch_on_the_record_is_signed_with_the_key_of_the_file(tmp_path, monkeypatch, key_file, capsys):
    _config(monkeypatch, {"sign_evidence": True})
    path = write_update_report(_report(), str(tmp_path))
    write_evidence_record(_report(), path)
    record = _written(tmp_path)
    assert evidence.verify(record) == [] and record["signature"]["public_key"] == PUB.hex()
    assert record_signing.verify_evidence(record, PUB)
    out = capsys.readouterr()
    assert SEED.hex() not in out.out + out.err + json.dumps(record)


def test_the_key_file_of_the_setting_is_used(tmp_path, monkeypatch):
    other = tmp_path / "other.key"
    other.write_text(OTHER.hex() + "\n", encoding="ascii")
    _config(monkeypatch, {"sign_evidence": True, "record_key_file": str(other)})
    path = write_update_report(_report(), str(tmp_path / "out"))
    write_evidence_record(_report(), path)
    assert _written(tmp_path / "out")["signature"]["public_key"] == OTHER_PUB.hex()


def test_the_argument_overrides_the_setting(tmp_path, monkeypatch, key_file):
    _config(monkeypatch, {"sign_evidence": True})
    path = write_update_report(_report(), str(tmp_path))
    write_evidence_record(_report(), path, sign=False)
    assert "signature" not in _written(tmp_path)


def test_a_key_that_cannot_be_used_raises_and_writes_no_evidence(tmp_path, monkeypatch):
    bad = tmp_path / "bad.key"
    bad.write_text("not hexadecimal secret-ish text\n", encoding="ascii")
    monkeypatch.setenv(record_signing.KEY_ENV, str(bad))
    _config(monkeypatch, {"sign_evidence": True})
    path = write_update_report(_report(), str(tmp_path / "out"))
    with pytest.raises(ValueError) as caught:
        write_evidence_record(_report(), path)
    assert "secret-ish" not in str(caught.value)
    assert not list((tmp_path / "out").glob("urtc_evidence_*.json"))
    assert Path(path).is_file()                                      # the update report is there


def test_the_seal_changes_nothing_when_off():
    plain = evidence.build(kind="flash", outcome="pass", timestamp_utc="2026-01-02T03:04:05Z", tool="URTC-FLASHER", tool_version="0.4.5")
    assert seal_evidence(plain, False) is plain


def test_the_records_of_a_scenario_run_are_signed_too(tmp_path, monkeypatch, key_file):
    import flasher_scenario

    _config(monkeypatch, {"sign_evidence": True})
    monkeypatch.setattr(flasher_scenario, "scenario_evidence", lambda report, bus, note: evidence.from_update_report(report))
    report_path, evidence_path = flasher_scenario.write_scenario_records(_report(), None, str(tmp_path), "note")
    assert record_signing.verify_evidence(json.loads(Path(evidence_path).read_text(encoding="utf-8")), PUB) and Path(report_path).is_file()


# -- the history with the trust store ------------------------------------------------------------------------------------------------------
@pytest.fixture
def folder(tmp_path):
    base = tmp_path / "evidence"
    base.mkdir()
    for name, item in {"a": record_signing.sign_evidence(_ev("a"), SEED), "b": record_signing.sign_evidence(_ev("b"), OTHER), "c": _ev("c")}.items():
        (base / f"urtc_evidence_{name}.json").write_text(json.dumps(item), encoding="utf-8")
    return base


def _ev(detail):
    return evidence.build(kind="flash", outcome="pass", timestamp_utc="2026-01-02T10:00:00Z", tool="URTC-FLASHER", tool_version="0.4.5", subject={"name": "head-1"}, detail=detail)


def test_the_history_counts_the_trusted_and_unknown_keys(folder, monkeypatch, capsys):
    _config(monkeypatch, {"trusted_keys": {"Ana": PUB.hex()}})
    assert urtc_flasher.run_history([str(folder)]) == 0
    assert "1 signed by a trusted key (Ana), 1 by an unknown key, 0 not valid, 1 unsigned" in capsys.readouterr().out


def test_the_history_without_a_store_is_as_it_was(folder, monkeypatch, capsys):
    _config(monkeypatch, {})
    assert urtc_flasher.run_history([str(folder)]) == 0
    assert "trust store" not in capsys.readouterr().out


def test_the_public_key_given_wins_over_the_store_and_a_bad_one_is_a_usage_error(folder, monkeypatch, capsys):
    _config(monkeypatch, {"trusted_keys": {"Ana": PUB.hex(), "Bea": OTHER_PUB.hex()}})
    assert urtc_flasher.run_history([str(folder), "--public-key", PUB.hex()]) == 1       # b is by another key than the one given
    assert "trust store" not in capsys.readouterr().out
    assert urtc_flasher.run_history([str(folder), "--public-key", "zz"]) == 2
    assert "ERROR" in capsys.readouterr().err


def test_a_forged_signature_fails_the_history(folder, monkeypatch, capsys):
    _config(monkeypatch, {})
    path = folder / "urtc_evidence_a.json"
    forged = json.loads(path.read_text(encoding="utf-8"))
    forged["detail"] = "changed"
    forged["evidence_sha256"] = evidence.digest(forged)
    path.write_text(json.dumps(forged), encoding="utf-8")
    assert urtc_flasher.run_history([str(folder)]) == 1


def test_a_bad_entry_of_the_store_is_a_warning_and_not_trusted(folder, monkeypatch, capsys):
    _config(monkeypatch, {"trusted_keys": {"Ana": "nope"}})
    assert urtc_flasher.run_history([str(folder)]) == 0
    captured = capsys.readouterr()
    assert "WARNING" in captured.err and "nope" not in captured.err and "trusted key" not in captured.out


def test_the_window_has_the_signature_column_with_the_store(folder, monkeypatch):
    pytest.importorskip("PySide6")
    from urtc_can.evidence_history_qt import EvidenceHistoryModel

    _config(monkeypatch, {"trusted_keys": {"Ana": PUB.hex()}})
    model = EvidenceHistoryModel(lambda: folder, trusted=lambda: flasher_config.trusted_keys_store()[0] or None)
    assert len(model.headers) == 8
    assert {r["signatureText"] for r in model.rows} == {"Signed by Ana", "Valid signature, unknown key", "Not signed"}


def test_the_records_module_exports_the_seal():
    assert flasher_records.seal_evidence is seal_evidence


# -- the switch in the Qt interface -------------------------------------------------------------------------------------------------------------
def test_the_text_of_the_switch_exists_in_the_eight_languages():
    root = Path(__file__).resolve().parent.parent
    for name in ("english", "spanish", "german", "french", "italian", "japanese", "chinese", "portuguese"):
        lines = (root / "language" / f"{name}.lng").read_text(encoding="utf-8").splitlines()
        assert any(line.startswith("CHK_SIGN_EVIDENCE=") and len(line) > 25 for line in lines), name


def test_the_switch_is_off_by_default_and_saves_the_setting(monkeypatch):
    pytest.importorskip("PySide6")
    import qt_flasher

    saved = {}
    monkeypatch.setattr(qt_flasher, "save_config", lambda updates: saved.update(updates) or True)
    _config(monkeypatch, {})
    bridge = qt_flasher.FlasherQtBridge()
    bridge._log = lambda text: None
    assert bridge.signEvidence is False
    bridge.setSignEvidence(True)
    assert saved == {"sign_evidence": True}
    _config(monkeypatch, {"sign_evidence": True})
    assert bridge.signEvidence is True
    bridge.setSignEvidence(False)
    assert saved == {"sign_evidence": False}


def test_a_switch_that_cannot_be_saved_is_logged_and_does_not_claim_to_be_on(monkeypatch):
    pytest.importorskip("PySide6")
    import qt_flasher

    logged = []
    monkeypatch.setattr(qt_flasher, "save_config", lambda updates: False)
    _config(monkeypatch, {})
    bridge = qt_flasher.FlasherQtBridge()
    bridge._log = logged.append
    bridge.setSignEvidence(True)
    assert logged == ["SIGN_EVIDENCE_NOT_SAVED"] and bridge.signEvidence is False


def test_the_deck_has_the_checkbox_bound_to_the_setting():
    qml = (Path(__file__).resolve().parent.parent / "assets" / "qml" / "FlasherDeck.qml").read_text(encoding="utf-8")
    assert 'objectName: "signEvidenceCheck"' in qml and "flasherBackend.signEvidence" in qml and "flasherBackend.setSignEvidence(checked)" in qml
