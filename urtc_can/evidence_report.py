# =============================================================================
# URTC-COMMON - src/urtc_common/evidence_report.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""A report of the evidence records of a folder, as one HTML page or one PDF file.

The records are those of ``evidence_history`` (``urtc-evidence/1``, each one checked with ``evidence.verify``). The report lists every record: a record that
fails its check is shown as NOT VALID with what is wrong, never left out, and a record that says it came from a simulated bus is marked SIMULATED. The files that
are not evidence but a known shape (the update report of the flasher, the result record of the tester) are counted and listed apart, by name and type, never as NOT VALID.

* the HTML is one self-contained file: no script, no external resource, a policy that forbids both, plain tables with captions and header cells, and every
  text that comes from a record is escaped (control characters and direction marks are replaced), so a hostile record cannot inject markup;
* the PDF is written here, in plain objects, with the same content as lines of text: Western text in the standard font Courier, Chinese and Japanese in a
  SUBSET of Noto Sans CJK embedded in the file (SIL Open Font License 1.1, see ``evidence_report_fonts``); a character the subset lacks is printed as a visible
  square and the report says so, never as a silent ``?`` (the HTML keeps every character);
* the same records give the same bytes: nothing reads the clock, only the times the records carry are printed.

What the report proves: a matching digest shows a record was not changed after it was written, not who wrote it; "real adapter" means only that no
simulation is stated. Standard library only.
"""
from __future__ import annotations

import html
import json
import textwrap
import unicodedata
from collections.abc import Sequence
from typing import Any

from . import evidence, evidence_history
from . import evidence_history_strings as _hist
from . import evidence_report_strings as _st

FORMATS = ("html", "pdf")
FIELD_LIMIT = 2000   # the most characters of one value that the report prints
ORIGINS = ("simulated", "replay", "real", "unknown")
PDF_COLUMNS = 88   # Courier: characters per line
PDF_LINES = 62
PDF_WIDTH = 495    # embedded font: points per line (A4 less the margins)
PDF_SIZE = 9       # points


def origin(record: dict[str, Any]) -> str:
    """``simulated`` when the adapter is a simulation or the detail says so, ``replay`` for a recorded trace, ``real`` for another adapter, else ``unknown``."""
    transport = record.get("transport")
    adapter = str(transport.get("adapter", "")) if isinstance(transport, dict) else ""
    detail = record.get("detail")
    lowered = adapter.lower()
    if lowered.startswith("simulate") or (isinstance(detail, str) and "SIMULATED" in detail):
        return "simulated"
    if lowered.startswith("replay"):
        return "replay"
    return "real" if adapter.strip() else "unknown"


def clean(value: Any) -> str:
    """A value as printable text: no control or format characters (they become U+FFFD), a line break becomes a space, and a long one is cut."""
    if isinstance(value, str):
        raw = value
    else:
        try:
            raw = json.dumps(value, ensure_ascii=False, sort_keys=True)
        except (TypeError, ValueError):
            raw = repr(value)
    out = []
    for char in raw[:FIELD_LIMIT]:
        category = unicodedata.category(char)
        if char in "\r\n\t":
            out.append(" ")
        elif category in ("Cc", "Cf", "Cs", "Co", "Cn", "Zl", "Zp"):
            out.append("�")
        else:
            out.append(char)
    return "".join(out) + ("..." if len(raw) > FIELD_LIMIT else "")


def _group(record: dict[str, Any], name: str) -> dict[str, Any]:
    value = record.get(name)
    return value if isinstance(value, dict) else {}


def _versions(subject: dict[str, Any]) -> str:
    before, after = subject.get("version_before"), subject.get("version_after")
    if after:
        return f"{clean(before) if before else '?'} -> {clean(after)}"
    return clean(before) if before else ""


def _recomputed(record: dict[str, Any]) -> str:
    try:
        return evidence.digest(record)
    except (TypeError, ValueError, KeyError):
        return ""


class _Item:
    """One record prepared for printing: every value already clean."""

    def __init__(self, number: int, entry: evidence_history.Entry, language: str) -> None:
        record = entry.record
        subject, transport = _group(record, "subject"), _group(record, "transport")
        t = lambda key: _st.text(language, key)   # noqa: E731
        self.number = number
        self.valid = entry.valid
        self.problems = [clean(p) for p in entry.problems]
        self.origin = origin(record)
        self.origin_text = t("ER_ORIGIN_" + self.origin.upper())
        outcome, kind = record.get("outcome"), record.get("kind")
        self.outcome = clean(outcome) if isinstance(outcome, str) else ""
        self.outcome_text = _hist.text(language, _hist.outcome_key(self.outcome)) if self.outcome in evidence.OUTCOMES else (self.outcome or "-")
        self.kind_text = _hist.text(language, _hist.kind_key(kind)) if isinstance(kind, str) and kind in evidence.KINDS else (clean(kind) if kind else "-")
        self.time = clean(entry.time) or "-"
        tool = f"{clean(record.get('tool', ''))} {clean(record.get('tool_version', ''))}".strip()
        self.tool = tool or "-"
        self.board = clean(subject.get("name", "")) or "-"
        self.integrity = t("ER_INTEGRITY_OK") if entry.valid else t("ER_INTEGRITY_BAD")
        self.file = clean(entry.file + (f":{entry.line}" if entry.line else ""))
        none = t("ER_NONE")
        declared = record.get("evidence_sha256")
        artifacts = record.get("artifacts")
        files = []
        if isinstance(artifacts, list):
            for item in artifacts:
                if isinstance(item, dict):
                    files.append(f"{clean(item.get('name', ''))} {clean(item.get('sha256', ''))}" + (f" ({clean(item.get('bytes'))} B)" if "bytes" in item else ""))
                else:
                    files.append(clean(item))
        self.fields = [
            (t("ER_F_OPERATOR"), clean(record.get("operator", "")) or none),
            (t("ER_F_HARDWARE"), clean(subject.get("hardware_id", "")) or none),
            (t("ER_F_VERSIONS"), _versions(subject) or none),
            (t("ER_F_ADAPTER"), (clean(transport.get("adapter", "")) + (f" / {clean(transport.get('bus'))}" if "bus" in transport else "")
                                 + (f" / {clean(transport.get('bitrate'))}" if "bitrate" in transport else "")) or none),
            (t("ER_F_DIGEST"), clean(declared) if declared is not None else none),
            (t("ER_F_ARTIFACTS"), "; ".join(files) or none),
            (t("ER_F_DETAIL"), clean(record.get("detail", "")) or none),
        ]
        if not entry.valid:
            recomputed = _recomputed(record)
            if recomputed and recomputed != declared:
                self.fields.append((t("ER_F_DIGEST") + " *", recomputed))


def _items(entries: Sequence[evidence_history.Entry], language: str) -> list[_Item]:
    ordered = evidence_history.select(entries)    # newest first, the file name decides ties: the same records give the same order
    return [_Item(number, entry, language) for number, entry in enumerate(ordered, 1)]


def _others(entries: Sequence[evidence_history.Entry], language: str) -> list[tuple[str, str]]:
    """The records that are not evidence, as (file, type) already clean and in the language, by file name: they are listed, never left out."""
    return [(clean(r["file"]), _hist.text(language, "EH_OTHER_" + r["type"].upper())) for r in map(evidence_history.other_row, evidence_history.others_of(entries))]


def _summary(items: Sequence[_Item], entries: Sequence[evidence_history.Entry]) -> dict[str, Any]:
    base = evidence_history.summary(entries)
    origins = {name: sum(1 for item in items if item.origin == name) for name in ORIGINS}
    return {**base, "origins": origins}


def _tr(language: str):
    return lambda key, **values: _st.text(language, key, **values)


# -- HTML -------------------------------------------------------------------------------------------------------------------------------------
_CSS = (
    "body{font-family:system-ui,Segoe UI,Arial,sans-serif;margin:0 auto;max-width:72rem;padding:1rem;color:#111;background:#fff;line-height:1.45}"
    "h1,h2,h3{line-height:1.2}table{border-collapse:collapse;width:100%;margin:.5rem 0 1.25rem}"
    "caption{text-align:left;font-weight:bold;padding:.25rem 0}th,td{border:1px solid #555;padding:.3rem .5rem;text-align:left;vertical-align:top;word-break:break-word}"
    "th{background:#e8e8e8}.bad{border:3px solid #a00;background:#fde8e8}.bad h3{color:#a00}.flag{font-weight:bold}.sim{background:#fff3c4}"
    "section.record{margin:1rem 0;padding:.5rem 1rem;border:1px solid #888}.note{border-left:4px solid #555;padding-left:.75rem}"
    "@media print{body{max-width:none}section.record{break-inside:avoid}}"
)
_POLICY = "default-src 'none'; style-src 'unsafe-inline'; img-src 'none'; form-action 'none'; base-uri 'none'"


def _e(value: Any) -> str:
    return html.escape(clean(value), quote=True)


def to_html(entries: Sequence[evidence_history.Entry], language: str = "english") -> str:
    """The report as one HTML page (a string with ``\\n`` line ends)."""
    t = _tr(language)
    items = _items(entries, language)
    info = _summary(items, entries)
    out: list[str] = []
    add = out.append
    add("<!DOCTYPE html>")
    add(f'<html lang="{_st.HTML_LANG.get(language, "en")}">')
    add("<head>")
    add('<meta charset="utf-8">')
    add(f'<meta http-equiv="Content-Security-Policy" content="{html.escape(_POLICY, quote=True)}">')
    add('<meta name="viewport" content="width=device-width, initial-scale=1">')
    add(f"<title>{_e(t('ER_TITLE'))}</title>")
    add(f"<style>{_CSS}</style>")
    add("</head>")
    add("<body>")
    add(f"<header><h1>{_e(t('ER_TITLE'))}</h1><p>{_e(t('ER_LEAD'))}</p></header>")
    add("<main>")
    add('<section aria-labelledby="summary"><h2 id="summary">' + _e(t("ER_SUMMARY")) + "</h2>")
    add("<table><caption>" + _e(t("ER_SUMMARY")) + "</caption><tbody>")
    rows = [
        (t("ER_TOTAL"), info["records"]), (t("ER_VALID"), info["valid"]), (t("ER_INVALID"), info["invalid"]),
        (t("ER_BY_OUTCOME"), ", ".join(f"{_hist.text(language, _hist.outcome_key(k))}: {v}" for k, v in info["outcomes"].items())),
        (t("ER_BY_KIND"), ", ".join(f"{_hist.text(language, _hist.kind_key(k))}: {v}" for k, v in info["kinds"].items())),
        (t("ER_BY_ORIGIN"), ", ".join(f"{t('ER_ORIGIN_' + k.upper())}: {v}" for k, v in info["origins"].items())),
        (t("ER_FIRST"), info["first"] or "-"), (t("ER_LAST"), info["last"] or "-"),
    ]
    others = _others(entries, language)
    if others:
        rows.append((t("ER_OTHERS"), ", ".join(f"{_hist.text(language, 'EH_OTHER_' + k.upper())}: {v}" for k, v in info["other_kinds"].items() if v)))
    for label, value in rows:
        add(f'<tr><th scope="row">{_e(label)}</th><td>{_e(value)}</td></tr>')
    add("</tbody></table>")
    add(f'<p class="note">{_e(t("ER_NOTE"))}</p>')
    add("</section>")
    if not items:
        add(f"<p>{_e(t('ER_EMPTY'))}</p>")
    else:
        add('<section aria-labelledby="list"><h2 id="list">' + _e(t("ER_LIST")) + "</h2>")
        add("<table><caption>" + _e(t("ER_LIST")) + "</caption><thead><tr>")
        for key in ("ER_COL_NUM", "EH_COL_TIME", "EH_COL_KIND", "EH_COL_OUTCOME", "EH_COL_TOOL", "EH_COL_BOARD", "ER_COL_ORIGIN", "EH_COL_CHECK"):
            label = _st.text(language, key) if key.startswith("ER_") else _hist.text(language, key)
            add(f'<th scope="col">{_e(label)}</th>')
        add("</tr></thead><tbody>")
        for item in items:
            row_class = ' class="bad"' if not item.valid else (' class="sim"' if item.origin == "simulated" else "")
            add(f'<tr{row_class}><th scope="row"><a href="#r{item.number}">{item.number}</a></th><td>{_e(item.time)}</td><td>{_e(item.kind_text)}</td>'
                f'<td>{_e(item.outcome_text)}</td><td>{_e(item.tool)}</td><td>{_e(item.board)}</td><td class="flag">{_e(item.origin_text)}</td>'
                f'<td class="flag">{_e(item.integrity)}</td></tr>')
        add("</tbody></table></section>")
        add('<section aria-labelledby="detail"><h2 id="detail">' + _e(t("ER_DETAIL")) + "</h2>")
        for item in items:
            klass = "record bad" if not item.valid else "record"
            add(f'<section class="{klass}" id="r{item.number}" aria-labelledby="h{item.number}">')
            add(f'<h3 id="h{item.number}">{item.number}. {_e(item.board)} - {_e(item.kind_text)} - {_e(item.outcome_text)}</h3>')
            if not item.valid:
                add(f'<p class="flag" role="alert">{_e(t("ER_BANNER_INVALID"))}</p>')
                add(f"<p>{_e(t('ER_PROBLEMS'))}:</p><ul>")
                for problem in item.problems:
                    add(f"<li>{_e(problem)}</li>")
                add("</ul>")
            add(f"<table><caption>{_e(t('ER_F_RECORD'))} {item.number}</caption><tbody>")
            add(f'<tr><th scope="row">{_e(_hist.text(language, "EH_COL_TIME"))}</th><td>{_e(item.time)}</td></tr>')
            add(f'<tr><th scope="row">{_e(t("ER_COL_ORIGIN"))}</th><td class="flag">{_e(item.origin_text)}</td></tr>')
            add(f'<tr><th scope="row">{_e(_hist.text(language, "EH_COL_CHECK"))}</th><td class="flag">{_e(item.integrity)}</td></tr>')
            add(f'<tr><th scope="row">{_e(t("ER_COL_FILE"))}</th><td>{_e(item.file)}</td></tr>')
            for label, value in item.fields:
                add(f'<tr><th scope="row">{_e(label)}</th><td>{_e(value)}</td></tr>')
            add("</tbody></table></section>")
        add("</section>")
    if others:
        add('<section aria-labelledby="others"><h2 id="others">' + _e(t("ER_OTHERS")) + "</h2>")
        add(f'<p class="note">{_e(t("ER_OTHERS_NOTE"))}</p>')
        add("<table><caption>" + _e(t("ER_OTHERS")) + '</caption><thead><tr><th scope="col">' + _e(t("ER_COL_FILE")) + '</th><th scope="col">' + _e(t("ER_COL_TYPE")) + "</th></tr></thead><tbody>")
        for name, kind_text in others:
            add(f'<tr><th scope="row">{_e(name)}</th><td>{_e(kind_text)}</td></tr>')
        add("</tbody></table></section>")
    add("</main>")
    add("</body>")
    add("</html>")
    return "\n".join(out) + "\n"


# -- plain text and PDF -------------------------------------------------------------------------------------------------------------------------
def to_text(entries: Sequence[evidence_history.Entry], language: str = "english") -> str:
    """The same report as lines of text (what the PDF prints)."""
    t = _tr(language)
    items = _items(entries, language)
    info = _summary(items, entries)
    lines = [t("ER_TITLE").upper(), "=" * len(t("ER_TITLE")), "", t("ER_LEAD"), "", t("ER_SUMMARY"), "-" * len(t("ER_SUMMARY")),
             f"{t('ER_TOTAL')}: {info['records']}", f"{t('ER_VALID')}: {info['valid']}", f"{t('ER_INVALID')}: {info['invalid']}",
             f"{t('ER_BY_OUTCOME')}: " + ", ".join(f"{_hist.text(language, _hist.outcome_key(k))} {v}" for k, v in info["outcomes"].items()),
             f"{t('ER_BY_KIND')}: " + ", ".join(f"{_hist.text(language, _hist.kind_key(k))} {v}" for k, v in info["kinds"].items()),
             f"{t('ER_BY_ORIGIN')}: " + ", ".join(f"{t('ER_ORIGIN_' + k.upper())} {v}" for k, v in info["origins"].items()),
             f"{t('ER_FIRST')}: {info['first'] or '-'}", f"{t('ER_LAST')}: {info['last'] or '-'}",
             *([f"{t('ER_OTHERS')}: " + ", ".join(f"{_hist.text(language, 'EH_OTHER_' + k.upper())} {v}" for k, v in info["other_kinds"].items() if v)] if info["others"] else []),
             "", t("ER_NOTE"), ""]
    lines += [_st.text(language, "ER_PDF_NOTE"), ""]
    if not items:
        lines.append(t("ER_EMPTY"))
    for item in items:
        lines += ["", f"[{item.number}] {item.board} | {item.kind_text} | {item.outcome_text} | {item.origin_text} | {item.integrity}"]
        if not item.valid:
            lines += ["    *** " + t("ER_BANNER_INVALID"), "    " + t("ER_PROBLEMS") + ":"] + [f"      - {p}" for p in item.problems]
        lines += [f"    {_hist.text(language, 'EH_COL_TIME')}: {item.time}", f"    {t('ER_COL_FILE')}: {item.file}"]
        lines += [f"    {label}: {value}" for label, value in item.fields]
    others = _others(entries, language)
    if others:
        lines += ["", t("ER_OTHERS").upper(), "-" * len(t("ER_OTHERS")), t("ER_OTHERS_NOTE")]
        lines += [f"    {name} | {kind_text}" for name, kind_text in others]
    return "\n".join(lines) + "\n"


def _pdf_escape(line: str) -> bytes:
    data = line.encode("cp1252", errors="replace")
    return data.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def pdf_font_for(text: str, language: str) -> str | None:
    """Which font the PDF of this text needs: ``None`` for the standard Courier (the text is Western, in a Western language), ``sc`` or ``jp`` for an embedded subset.

    Chinese uses ``sc`` and Japanese ``jp`` (their own letter forms). Western text that holds a character Courier cannot show goes in the embedded font too: ``jp``
    when the text holds kana, else ``sc``.
    """
    if language == "chinese":
        return "sc"
    if language == "japanese":
        return "jp"
    try:
        text.encode("cp1252")
    except UnicodeEncodeError:
        return "jp" if any("぀" <= char <= "ヿ" for char in text) else "sc"
    return None


def _wrap_courier(lines: Sequence[str]) -> list[str]:
    wrapped: list[str] = []
    for line in lines:
        indent = len(line) - len(line.lstrip(" "))
        pieces = textwrap.wrap(line, width=PDF_COLUMNS, subsequent_indent=" " * (indent + 2), drop_whitespace=False, break_long_words=True) if line.strip() else [""]
        wrapped += [p.rstrip() for p in pieces] or [""]
    return wrapped


def _wrap_measured(lines: Sequence[str], glyphs: dict[int, tuple[int, int]]) -> list[str]:
    """Wrap by the width of the glyphs (1/1000 em), at a space when there is one in reach, else between two characters (Chinese and Japanese have no spaces)."""
    limit = PDF_WIDTH * 1000 / PDF_SIZE
    wrapped: list[str] = []
    for line in lines:
        if not line.strip():
            wrapped.append("")
            continue
        indent = len(line) - len(line.lstrip(" "))
        prefix = " " * (indent + 2)
        lead = indent
        rest = line
        while True:
            width, cut = 0, 0
            while cut < len(rest) and width + glyphs[ord(rest[cut])][1] <= limit:
                width += glyphs[ord(rest[cut])][1]
                cut += 1
            if cut >= len(rest):
                wrapped.append(rest.rstrip())
                break
            space = rest.rfind(" ", lead + 1, cut + 1)
            if space > lead:
                cut = space
            cut = max(cut, lead + 1)
            wrapped.append(rest[:cut].rstrip())
            rest = prefix + rest[cut:].lstrip(" ")
            lead = len(prefix)
    return wrapped


def _hex(text: str, glyphs: dict[int, tuple[int, int]], used: dict[int, int]) -> bytes:
    """The text as a PDF hex string of glyph ids (Identity-H); ``used`` collects glyph id -> character for the ToUnicode map."""
    out = []
    for char in text:
        gid = glyphs[ord(char)][0]
        used.setdefault(gid, ord(char))
        out.append("%04X" % gid)
    return b"<" + "".join(out).encode("ascii") + b">"


def _utf16_hex(text: str) -> bytes:
    return b"<FEFF" + text.encode("utf-16-be").hex().upper().encode("ascii") + b">"


def _to_unicode(used: dict[int, int]) -> bytes:
    """The ToUnicode CMap of the glyphs the document uses (so the text can be copied and searched)."""
    lines = [b"/CIDInit /ProcSet findresource begin", b"12 dict begin", b"begincmap", b"/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def",
             b"/CMapName /Adobe-Identity-UCS def", b"/CMapType 2 def", b"1 begincodespacerange", b"<0000> <FFFF>", b"endcodespacerange"]
    items = sorted(used.items())
    for start in range(0, len(items), 100):
        chunk = items[start:start + 100]
        lines.append(b"%d beginbfchar" % len(chunk))
        for gid, code in chunk:
            lines.append(b"<%04X> <" % gid + chr(code).encode("utf-16-be").hex().upper().encode("ascii") + b">")
        lines.append(b"endbfchar")
    lines += [b"endcmap", b"CMapName currentdict /CMap defineresource pop", b"end", b"end"]
    return b"\n".join(lines)


def to_pdf(entries: Sequence[evidence_history.Entry], language: str = "english") -> bytes:
    """The report as a PDF file (version 1.4, A4, no date): the same records give the same bytes.

    Western text is set in the standard font Courier, no font inside. Chinese and Japanese (and any text with a character Courier cannot show) are set in a subset
    of Noto Sans CJK that the file embeds (Type0 / CIDFontType2, Identity-H, with a ToUnicode map so the text can be copied). A character the subset lacks is printed
    as U+25A1 and the report says how many different ones there were: never a silent ``?``.
    """
    if language not in _st.LANGUAGES:
        language = "english"
    source = to_text(entries, language).splitlines()
    footer_sample = _st.text(language, "ER_PAGE", page=999, pages=999) + _st.text(language, "ER_TITLE")
    font_name = pdf_font_for("\n".join(source) + footer_sample, language)
    glyphs: dict[int, tuple[int, int]] = {}
    used: dict[int, int] = {}
    if font_name is None:
        wrapped = _wrap_courier(source)
    else:
        from . import evidence_report_fonts as _fonts
        font = _fonts.font(font_name)
        glyphs = font["glyphs"]
        replacement = chr(font["replacement"])
        missing = {char for line in source for char in line if ord(char) not in glyphs}
        if missing:
            source = ["".join(char if ord(char) in glyphs else replacement for char in line) for line in source]
            note = _st.text(language, "ER_PDF_NOTE")
            at = source.index(note) + 1 if note in source else 0
            source[at:at] = [_st.text(language, "ER_PDF_SUBST", count=len(missing)), ""]
        wrapped = _wrap_measured(source, glyphs)
    pages = [wrapped[i:i + PDF_LINES] for i in range(0, len(wrapped), PDF_LINES)] or [[""]]
    title = _st.text(language, "ER_TITLE")
    objects: list[bytes] = []   # object n is objects[n - 1]
    first_page = 5 if font_name is None else 9
    page_ids = [first_page + 2 * i for i in range(len(pages))]
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = b" ".join(b"%d 0 R" % pid for pid in page_ids)
    objects.append(b"<< /Type /Pages /Kids [" + kids + b"] /Count %d >>" % len(pages))
    if font_name is None:
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>")
        objects.append(b"<< /Title (" + _pdf_escape(title) + b") /Producer (urtc_common.evidence_report) >>")
    else:
        base = b"URTC" + font_name.upper().encode("ascii") + b"+NotoSansCJK" + font_name.upper().encode("ascii") + b"-Regular"
        objects.append(b"<< /Type /Font /Subtype /Type0 /BaseFont /" + base + b" /Encoding /Identity-H /DescendantFonts [5 0 R] /ToUnicode 8 0 R >>")
        objects.append(b"<< /Title " + _utf16_hex(title) + b" /Producer (urtc_common.evidence_report) >>")
    bodies = []
    for index, page in enumerate(pages):
        footer = _st.text(language, "ER_PAGE", page=index + 1, pages=len(pages))
        if font_name is None:
            body = [b"BT", b"/F1 9 Tf", b"11 TL", b"50 792 Td"] + [b"(" + _pdf_escape(line) + b") '" for line in page] + [b"ET",
                    b"BT", b"/F1 8 Tf", b"50 30 Td", b"(" + _pdf_escape(footer) + b") Tj", b"ET"]
        else:
            body = [b"BT", b"/F1 9 Tf", b"11 TL", b"50 792 Td"] + [_hex(line, glyphs, used) + b" '" for line in page] + [b"ET",
                    b"BT", b"/F1 8 Tf", b"50 30 Td", _hex(footer, glyphs, used) + b" Tj", b"ET"]
        bodies.append(b"\n".join(body))
    if font_name is not None:
        compressed = font["ttf"]
        advance = {g: adv for g, adv in glyphs.values()}
        widths = b" ".join(b"%d [%d]" % (gid, advance[gid]) for gid in sorted(used))
        objects.append(b"<< /Type /Font /Subtype /CIDFontType2 /BaseFont /" + base + b" /CIDSystemInfo << /Registry (Adobe) /Ordering (Identity) /Supplement 0 >> "
                       b"/FontDescriptor 6 0 R /DW 1000 /W [" + widths + b"] /CIDToGIDMap /Identity >>")
        objects.append(b"<< /Type /FontDescriptor /FontName /" + base + b" /Flags 4 /FontBBox [-200 -300 1200 1100] /ItalicAngle 0 /Ascent 880 /Descent -120 "
                       b"/CapHeight 733 /StemV 80 /FontFile2 7 0 R >>")
        objects.append(b"<< /Length %d /Length1 %d /Filter /FlateDecode >>\nstream\n" % (len(compressed), font["length"]) + compressed + b"\nendstream")
        unicode_map = _to_unicode(used)
        objects.append(b"<< /Length %d >>\nstream\n" % len(unicode_map) + unicode_map + b"\nendstream")
    for index, stream in enumerate(bodies):
        objects.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R >> >> /Contents %d 0 R >>" % (page_ids[index] + 1))
        objects.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for number, obj in enumerate(objects, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + obj + b"\nendobj\n"
    start = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root 1 0 R /Info 4 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, start)
    return bytes(out)


def render(entries: Sequence[evidence_history.Entry], fmt: str = "html", language: str = "english") -> bytes:
    """The report in ``fmt`` (``html`` or ``pdf``) as bytes; raises ``ValueError`` for another format."""
    if fmt == "html":
        return to_html(entries, language).encode("utf-8")
    if fmt == "pdf":
        return to_pdf(entries, language)
    raise ValueError(f"format must be one of {FORMATS}, got {fmt!r}")
