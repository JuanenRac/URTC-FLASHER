# =============================================================================
# URTC-COMMON - src/urtc_common/evidence.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""One shape for the records the programs keep of what they did: ``urtc-evidence/1``.

The flasher writes an update report, the tester a result record, the updater a line of its evidence log and each of them says the same things in its own
words: which tool did what, when, to which board, over which transport, with which files, and how it ended. This module is that shape and nothing more:

* ``build`` makes a record from named parts and gives it its digest (``evidence_sha256``), so a later edit of the file is noticed;
* ``verify`` returns the list of what is wrong with a record (empty when it is well formed and its digest is right);
* ``from_update_report``, ``from_result_record`` and ``from_updater_line`` turn the three existing records into it without changing them.

The digest shows that a record was not edited after it was written. It does not say who wrote it: that is what the signature of
``record_signing`` is for, which a program may add around a record. Nothing here reads the disk or the network, and a value that is not understood is
refused, never guessed: an unknown field, an unknown kind or outcome and a malformed hash are all problems.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping

FORMAT = "urtc-evidence/1"
KINDS = ("flash", "test", "install", "session")
OUTCOMES = ("pass", "fail", "error", "skipped")
FIELDS = ("format", "kind", "outcome", "timestamp_utc", "tool", "tool_version", "operator", "subject", "transport", "artifacts", "detail", "evidence_sha256")
SUBJECT_FIELDS = ("name", "hardware_id", "version_before", "version_after", "commit_before", "commit_after", "key_id")
TRANSPORT_FIELDS = ("adapter", "bus", "bitrate")
ARTIFACT_FIELDS = ("name", "sha256", "bytes")
DETAIL_LIMIT = 500

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_TIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")
_HARDWARE_ID = re.compile(r"^0x[0-9A-F]{8}$")
_VERSION = re.compile(r"^\d+(?:\.\d+){1,3}$")
_COMMIT = re.compile(r"^[0-9a-f]{7,64}$")
_KEY_ID = re.compile(r"^[0-9a-f]{8,64}$")


def digest(record: Mapping[str, Any]) -> str:
    """SHA-256 of the record without its own digest, as compact JSON with the keys sorted (the same text on every platform)."""
    body = {key: value for key, value in record.items() if key != "evidence_sha256"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def _clean(values: Mapping[str, Any] | None, allowed: tuple[str, ...]) -> dict[str, Any]:
    """The given values that are not empty, in a new dictionary (a ``None`` or an empty text is simply absent)."""
    return {key: values[key] for key in allowed if values and values.get(key) not in (None, "")}


def build(*, kind: str, outcome: str, timestamp_utc: str, tool: str, tool_version: str, operator: str = "", subject: Mapping[str, Any] | None = None,
          transport: Mapping[str, Any] | None = None, artifacts: list[Mapping[str, Any]] | None = None, detail: str = "") -> dict[str, Any]:
    """A record with its digest. Raises ``ValueError`` listing everything wrong with it (see ``verify``)."""
    record: dict[str, Any] = {"format": FORMAT, "kind": kind, "outcome": outcome, "timestamp_utc": timestamp_utc, "tool": tool, "tool_version": tool_version}
    if operator:
        record["operator"] = operator
    if subject:
        record["subject"] = _clean(subject, SUBJECT_FIELDS)
    if transport:
        record["transport"] = _clean(transport, TRANSPORT_FIELDS)
    if artifacts:
        record["artifacts"] = [_clean(item, ARTIFACT_FIELDS) for item in artifacts]
    if detail:
        record["detail"] = detail[:DETAIL_LIMIT]
    record["evidence_sha256"] = digest(record)
    problems = verify(record)
    if problems:
        raise ValueError("; ".join(problems))
    return record


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _check_group(name: str, value: Any, allowed: tuple[str, ...], rules: Mapping[str, Any], problems: list[str]) -> None:
    if not isinstance(value, dict) or not value:
        problems.append(f"{name} must be a non-empty object")
        return
    for key, item in value.items():
        if key not in allowed:
            problems.append(f"{name}.{key} is not a field of urtc-evidence/1")
        elif key in rules and not rules[key](item):
            problems.append(f"{name}.{key} is not valid")


def verify(record: Any) -> list[str]:
    """Everything that is wrong with a record; an empty list means it is well formed and its digest matches."""
    if not isinstance(record, dict):
        return ["a record is a JSON object"]
    problems: list[str] = []
    if record.get("format") != FORMAT:
        problems.append(f"format must be {FORMAT!r}")
    for key in record:
        if key not in FIELDS:
            problems.append(f"{key} is not a field of urtc-evidence/1")
    if record.get("kind") not in KINDS:
        problems.append(f"kind must be one of {KINDS}")
    if record.get("outcome") not in OUTCOMES:
        problems.append(f"outcome must be one of {OUTCOMES}")
    if not (isinstance(record.get("timestamp_utc"), str) and _TIME.match(record["timestamp_utc"])):
        problems.append("timestamp_utc must be an ISO 8601 time with Z or an offset")
    for key in ("tool", "tool_version"):
        if not _text(record.get(key)):
            problems.append(f"{key} must be a non-empty text")
    for key in ("operator", "detail"):
        if key in record and not isinstance(record[key], str):
            problems.append(f"{key} must be a text")
    if isinstance(record.get("detail"), str) and len(record["detail"]) > DETAIL_LIMIT:
        problems.append(f"detail is longer than {DETAIL_LIMIT} characters")
    if "subject" in record:
        _check_group("subject", record["subject"], SUBJECT_FIELDS, {
            "name": _text, "hardware_id": lambda v: isinstance(v, str) and bool(_HARDWARE_ID.match(v)),
            "version_before": lambda v: isinstance(v, str) and bool(_VERSION.match(v)), "version_after": lambda v: isinstance(v, str) and bool(_VERSION.match(v)),
            "commit_before": lambda v: isinstance(v, str) and bool(_COMMIT.match(v)), "commit_after": lambda v: isinstance(v, str) and bool(_COMMIT.match(v)),
            "key_id": lambda v: isinstance(v, str) and bool(_KEY_ID.match(v)),
        }, problems)
    if "transport" in record:
        _check_group("transport", record["transport"], TRANSPORT_FIELDS, {
            "adapter": _text, "bus": _text, "bitrate": lambda v: isinstance(v, int) and not isinstance(v, bool) and v > 0,
        }, problems)
    if "artifacts" in record:
        items = record["artifacts"]
        if not isinstance(items, list) or not items:
            problems.append("artifacts must be a non-empty list")
        else:
            for index, item in enumerate(items):
                _check_group(f"artifacts[{index}]", item, ARTIFACT_FIELDS, {
                    "name": _text, "sha256": lambda v: isinstance(v, str) and bool(_SHA256.match(v)),
                    "bytes": lambda v: isinstance(v, int) and not isinstance(v, bool) and v >= 0,
                }, problems)
                if isinstance(item, dict) and not {"name", "sha256"} <= set(item):
                    problems.append(f"artifacts[{index}] needs a name and a sha256")
    declared = record.get("evidence_sha256")
    if not (isinstance(declared, str) and _SHA256.match(declared)):
        problems.append("evidence_sha256 must be 64 lowercase hexadecimal digits")
    elif not problems and declared != digest(record):
        problems.append("evidence_sha256 does not match the record (edited after it was written?)")
    return problems


def _version(value: Any) -> str | None:
    """``"1.2"`` from the pair ``(1, 2)`` or the text of one, else ``None``."""
    if isinstance(value, (list, tuple)) and 2 <= len(value) <= 4 and all(isinstance(part, int) for part in value):
        return ".".join(str(part) for part in value)
    return value if isinstance(value, str) and _VERSION.match(value) else None


def _utc(value: str) -> str:
    return value.replace("+00:00", "Z")


def from_update_report(report: Mapping[str, Any]) -> dict[str, Any]:
    """The update report of the flasher (``flasher_records.build_update_report``) as a record. The result words of the report are mapped:
    anything that is not a plain success is an error."""
    image = report.get("image") or {}
    result = str(report.get("result", "")).lower()
    outcome = "pass" if result in {"ok", "success", "succeeded", "pass", "passed"} else "fail" if result in {"fail", "failed", "rejected"} else "error"
    return build(
        kind="flash", outcome=outcome, timestamp_utc=_utc(str(report.get("timestamp_utc", ""))), tool=str(report.get("tool", "")), tool_version=str(report.get("tool_version", "")),
        operator=str(report.get("operator") or ""),
        subject={"name": report.get("target"), "hardware_id": report.get("hardware_id"), "version_before": _version(report.get("version_before")),
                 "version_after": _version(report.get("version_after"))},
        artifacts=[{"name": image["file"], "sha256": image["sha256"], "bytes": image.get("size")}] if image.get("file") and image.get("sha256") else None,
        detail=str(report.get("result", "")),
    )


def from_result_record(record: Mapping[str, Any], *, tool_version: str, timestamp_utc: str, operator: str = "") -> dict[str, Any]:
    """The result record of the tester (``ResultRecord`` as a dictionary). The record has no time of its own, so the caller gives it."""
    return build(
        kind="test", outcome=str(record.get("outcome", "")), timestamp_utc=timestamp_utc, tool="URTC Tester", tool_version=tool_version, operator=operator,
        subject={"name": record.get("test_name"), "version_after": _version(record.get("firmware_version"))},
        transport={"adapter": record.get("adapter"), "bus": record.get("bus"), "bitrate": record.get("bitrate")},
        artifacts=[{"name": record["log_file"], "sha256": record["log_sha256"]}] if record.get("log_file") and record.get("log_sha256") else None,
        detail=str(record.get("detail", "")),
    )


def from_updater_line(line: Mapping[str, Any]) -> dict[str, Any]:
    """One line of the updater's evidence log (``evidence.record_attempt``)."""
    return build(
        kind="install", outcome="pass" if line.get("ok") else "fail", timestamp_utc=_utc(str(line.get("timestamp", ""))), tool="URTC Updater",
        tool_version=str(line.get("updaterVersion", "")), operator=str(line.get("user") or ""),
        subject={"name": line.get("project"), "version_before": _version(line.get("versionBefore")), "version_after": _version(line.get("versionAfter")),
                 "commit_before": line.get("commitBefore"), "commit_after": line.get("commitAfter")},
        detail=str(line.get("message", "")),
    )
