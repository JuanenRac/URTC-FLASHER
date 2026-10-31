# =============================================================================
# URTC-COMMON - src/urtc_common/evidence_history.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The history of the evidence the programs wrote: read a folder of ``urtc-evidence/1`` records, check each one and list them.

The flasher, the tester and the updater each leave records of what they did (``evidence``); this is the one view over them, the same for every
program: which tool did what to which board, when, with which files, how it ended, and whether the record is still the one that was written.

* ``load_folder`` reads every ``*.json`` and ``*.jsonl`` file of a folder (and of the folders under it when asked) and returns the entries, each with the
  problems ``evidence.verify`` found; a file that is not JSON, or a record in a format this module does not know, is an entry with a problem, never skipped;
* the update report of the flasher (``urtc_update_report_*.json``) and the result record of the tester (``<name>_<time>.json``) are written in the same
  folder as the evidence but are not evidence. They are told apart by their shape, never by their name, and are returned as entries with ``other`` set
  (``update_report`` or ``result_record``): they are counted apart (``summary`` and ``others_of``), listed by name and type, never called NOT VALID and
  never left out. JSON of any other shape stays an entry with a problem;
* ``select`` keeps the entries that match a kind, an outcome, a tool, a time range or a piece of text, newest first;
* ``summary`` counts them; ``to_text``, ``to_csv`` and ``to_json`` write the list.

Nothing is changed on disk: the history only reads. A record that fails its check is listed with ``valid`` false and what is wrong, so a record edited after it
was written is seen instead of trusted. Standard library only.
"""
from __future__ import annotations

import csv
import io
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

from . import evidence

COLUMNS = ("timestamp_utc", "kind", "outcome", "tool", "tool_version", "subject", "version_before", "version_after", "artifacts", "valid", "file")
FILE_LIMIT = 5000       # the most files read from one folder
LINE_LIMIT = 100_000    # the most records read from one file
SIZE_LIMIT = 8_000_000  # a file bigger than this is listed as a problem, not read
OTHER_KINDS = ("update_report", "result_record")

_REPORT_KEYS = frozenset({"tool", "tool_version", "timestamp_utc", "image", "result", "report_sha256"})   # the update report of the flasher
_REPORT_OPTIONAL = frozenset({"operator", "target", "hardware_id", "version_before", "version_after", "signature"})
_RESULT_KEYS = frozenset({"test_name", "outcome", "adapter", "firmware_version", "bus", "bitrate", "log_file", "log_sha256"})   # ResultRecord of the tester
_RESULT_OPTIONAL = frozenset({"detail"})


def other_kind(record: Any) -> str:
    """The kind of a record that is not evidence but whose shape is known (``update_report`` or ``result_record``), or an empty text.

    Only the shape decides, never the file name: the exact set of keys and the type of the main values. A record that claims to be evidence
    (it has ``format`` or ``evidence_sha256``) is never one of these; it is checked as evidence."""
    if not isinstance(record, dict) or "format" in record or "evidence_sha256" in record:
        return ""
    keys = set(record)
    if _REPORT_KEYS <= keys <= _REPORT_KEYS | _REPORT_OPTIONAL:
        if all(isinstance(record[k], str) for k in ("tool", "tool_version", "timestamp_utc", "report_sha256")) and isinstance(record["image"], dict):
            return "update_report"
    if _RESULT_KEYS <= keys <= _RESULT_KEYS | _RESULT_OPTIONAL:
        text_fields = ("test_name", "outcome", "adapter", "firmware_version", "bus", "log_file", "log_sha256")
        bitrate = record["bitrate"]
        if all(isinstance(record[k], str) for k in text_fields) and isinstance(bitrate, int) and not isinstance(bitrate, bool):
            return "result_record"
    return ""


@dataclass
class Entry:
    """One record found on disk and what is wrong with it (``problems`` is empty for a record that is well formed and whose digest matches)."""

    file: str
    line: int
    record: dict[str, Any] = field(default_factory=dict)
    problems: list[str] = field(default_factory=list)
    other: str = ""     # a record that is not evidence but is a known shape (``OTHER_KINDS``); it has no problems and is not counted as evidence

    @property
    def valid(self) -> bool:
        return not self.problems

    @property
    def time(self) -> str:
        value = self.record.get("timestamp_utc")
        return value if isinstance(value, str) else ""


def _entries_of(path: Path, base: Path) -> list[Entry]:
    name = path.relative_to(base).as_posix() if base in path.parents else path.name
    try:
        if path.stat().st_size > SIZE_LIMIT:
            return [Entry(name, 0, problems=[f"the file is bigger than {SIZE_LIMIT} bytes and was not read"])]
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        return [Entry(name, 0, problems=[f"the file could not be read: {error}"])]
    if path.suffix == ".jsonl":
        out: list[Entry] = []
        for number, line in enumerate(text.splitlines()[:LINE_LIMIT], 1):
            if line.strip():
                out.append(_entry(name, number, line))
        return out
    return [_entry(name, 0, text)]


def _entry(name: str, line: int, text: str) -> Entry:
    try:
        record = json.loads(text)
    except ValueError as error:
        return Entry(name, line, problems=[f"not JSON: {error}"])
    if not isinstance(record, dict):
        return Entry(name, line, problems=["a record is a JSON object"])
    kind = other_kind(record)
    if kind:
        return Entry(name, line, record, [], kind)
    return Entry(name, line, record, evidence.verify(record))


def load_folder(folder: str | Path, recursive: bool = False) -> list[Entry]:
    """Every record of the ``.json`` and ``.jsonl`` files of ``folder``, in the order of the file names."""
    base = Path(folder)
    if not base.is_dir():
        raise FileNotFoundError(f"{base} is not a folder")
    pattern = "**/*" if recursive else "*"
    paths = sorted(p for p in base.glob(pattern) if p.is_file() and p.suffix in (".json", ".jsonl"))[:FILE_LIMIT]
    entries: list[Entry] = []
    for path in paths:
        entries += _entries_of(path, base)
    return entries


def select(entries: Iterable[Entry], *, kind: str | None = None, outcome: str | None = None, tool: str | None = None, since: str | None = None,
           until: str | None = None, text: str | None = None, only_invalid: bool = False) -> list[Entry]:
    """The entries that match every given condition, newest first. ``since`` and ``until`` are ISO times compared as text; ``text`` is looked for, without
    regard to case, in the subject, the tool, the detail and the names of the files."""
    needle = text.lower() if text else None
    chosen: list[Entry] = []
    for entry in entries:
        record = entry.record
        if entry.other:    # not evidence: counted and listed apart (``others_of``), never mixed into the list of evidence
            continue
        if kind and record.get("kind") != kind:
            continue
        if outcome and record.get("outcome") != outcome:
            continue
        if tool and str(record.get("tool", "")).lower() != tool.lower():
            continue
        if since and entry.time < since:
            continue
        if until and entry.time > until:
            continue
        if only_invalid and entry.valid:
            continue
        if needle and needle not in json.dumps({k: record.get(k) for k in ("subject", "tool", "detail", "artifacts")}, ensure_ascii=False).lower():
            continue
        chosen.append(entry)
    chosen.sort(key=lambda e: (e.time, e.file, e.line), reverse=True)
    return chosen


def others_of(entries: Iterable[Entry]) -> list[Entry]:
    """The records that are not evidence but a known shape (``other`` set), by file name: what the list leaves out of its rows and shows apart."""
    return sorted((e for e in entries if e.other), key=lambda e: (e.file, e.line))


def other_row(entry: Entry) -> dict[str, Any]:
    """The name and type of an ``other`` record (what is printed about it)."""
    return {"file": entry.file + (f":{entry.line}" if entry.line else ""), "type": entry.other}


def row(entry: Entry) -> dict[str, Any]:
    """The columns of a list for one entry (``COLUMNS``)."""
    record = entry.record
    raw_subject, raw_artifacts = record.get("subject"), record.get("artifacts")
    subject: dict[str, Any] = raw_subject if isinstance(raw_subject, dict) else {}
    artifacts: list[Any] = raw_artifacts if isinstance(raw_artifacts, list) else []
    return {
        "timestamp_utc": entry.time, "kind": record.get("kind", ""), "outcome": record.get("outcome", ""), "tool": record.get("tool", ""),
        "tool_version": record.get("tool_version", ""), "subject": subject.get("name", ""), "version_before": subject.get("version_before", ""),
        "version_after": subject.get("version_after", ""), "artifacts": len(artifacts), "valid": entry.valid,
        "file": entry.file + (f":{entry.line}" if entry.line else ""),
    }


def summary(entries: Sequence[Entry]) -> dict[str, Any]:
    """How many evidence records there are, how many are valid and how they are spread over the outcomes and kinds; ``others`` counts the records that are
    not evidence (``other_kinds`` by type) and that are not part of the other numbers."""
    outcomes = {name: 0 for name in evidence.OUTCOMES}
    kinds = {name: 0 for name in evidence.KINDS}
    other_kinds = {name: 0 for name in OTHER_KINDS}
    shown = [e for e in entries if not e.other]
    for entry in entries:
        if entry.other:
            other_kinds[entry.other] = other_kinds.get(entry.other, 0) + 1
    for entry in shown:
        outcome, kind = entry.record.get("outcome"), entry.record.get("kind")
        if outcome in outcomes:
            outcomes[outcome] += 1
        if kind in kinds:
            kinds[kind] += 1
    times = sorted(e.time for e in shown if e.time)
    return {"records": len(shown), "valid": sum(1 for e in shown if e.valid), "invalid": sum(1 for e in shown if not e.valid), "outcomes": outcomes,
            "kinds": kinds, "first": times[0] if times else "", "last": times[-1] if times else "",
            "others": sum(other_kinds.values()), "other_kinds": other_kinds}


def to_text(entries: Sequence[Entry], others: Sequence[Entry] = ()) -> str:
    """A readable list, one record per line, and below it one line for each problem found; ``others`` (see ``others_of``) are listed after it by name and
    type, never as not valid."""
    lines = _text_lines(entries)
    others = others_of(others)
    if others:
        lines += ["", f"{len(others)} other record(s), not evidence (not checked as evidence, not counted above):"]
        lines += [f"    {r['file']}  [{r['type']}]" for r in map(other_row, others)]
    return "\n".join(lines)


def _text_lines(entries: Sequence[Entry]) -> list[str]:
    if not entries:
        return ["no records"]
    lines = []
    for entry in entries:
        r = row(entry)
        versions = f"{r['version_before'] or '?'} -> {r['version_after']}" if r["version_after"] else (str(r["version_before"]) if r["version_before"] else "")
        lines.append(f"{r['timestamp_utc'] or '-':<26} {r['kind'] or '-':<8} {r['outcome'] or '-':<8} {r['tool'] or '-':<22} {r['subject']:<20} {versions:<16} {r['file']}"
                     + ("" if entry.valid else "  [NOT VALID]"))
        lines += [f"    problem: {problem}" for problem in entry.problems]
    return lines


def to_csv(entries: Sequence[Entry]) -> str:
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    for entry in entries:
        writer.writerow(row(entry))
    return out.getvalue()


def to_json(entries: Sequence[Entry], others: Sequence[Entry] = ()) -> str:
    """The list with its summary and, for each entry, its problems; the records are written as they were read. ``others`` (see ``others_of``) are listed
    by file and type under ``others`` and counted in the summary."""
    others = others_of(others)
    document = {"format": "urtc-evidence-history/1", "summary": summary([*entries, *others]),
                "entries": [{**row(e), "problems": e.problems, "record": e.record} for e in entries],
                "others": [other_row(e) for e in others]}
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="List the urtc-evidence/1 records of a folder, checking each one.")
    parser.add_argument("folder")
    parser.add_argument("--recursive", action="store_true")
    parser.add_argument("--kind", choices=evidence.KINDS)
    parser.add_argument("--outcome", choices=evidence.OUTCOMES)
    parser.add_argument("--tool")
    parser.add_argument("--since")
    parser.add_argument("--until")
    parser.add_argument("--text")
    parser.add_argument("--invalid", action="store_true", help="only the records that fail their check")
    parser.add_argument("--format", choices=("text", "csv", "json"), default="text")
    args = parser.parse_args(argv)
    loaded = load_folder(args.folder, args.recursive)
    entries = select(loaded, kind=args.kind, outcome=args.outcome, tool=args.tool, since=args.since, until=args.until, text=args.text, only_invalid=args.invalid)
    others = others_of(loaded)
    if args.format == "csv":
        print(to_csv(entries), end="")
        if others:    # the table has fixed columns for evidence: say what is not in it
            print(f"{len(others)} other record(s), not evidence, are not in this table: " + ", ".join(f"{r['file']} [{r['type']}]" for r in map(other_row, others)), file=sys.stderr)
    elif args.format == "json":
        print(to_json(entries, others), end="")
    else:
        print(to_text(entries, others))
    return 1 if any(not e.valid for e in entries) else 0


if __name__ == "__main__":
    raise SystemExit(main())
