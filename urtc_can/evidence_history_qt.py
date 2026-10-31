# =============================================================================
# URTC-COMMON - src/urtc_common/evidence_history_qt.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The Qt object behind ``EvidenceHistoryDialog.qml``: the records of the evidence of a folder, checked, filtered and in the language it is in.

It only reads. ``refresh`` reads the folder again (the window calls it each time it opens); the filters (result, text, only the records that fail their
check) work on what was read. The window shows at most ``ROW_LIMIT`` rows and says how many there are.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Property, QObject, Signal, Slot

from . import evidence, evidence_history, evidence_report
from . import evidence_history_strings as strings
from . import evidence_report_strings as report_strings

ROW_LIMIT = 500


class EvidenceHistoryModel(QObject):
    changed = Signal()

    def __init__(self, folder: Callable[[], str | Path | None], language: Callable[[], str] = lambda: "english", parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._folder = folder
        self._language = language
        self._entries: list[evidence_history.Entry] | None = None
        self._error = ""
        self._outcome = ""
        self._query = ""
        self._only_invalid = False
        self._report_status = ""

    # -- reading -------------------------------------------------------------------------------------------------
    def _folder_path(self) -> Path | None:
        value = self._folder()
        return Path(value) if value else None

    def _all(self) -> list[evidence_history.Entry]:
        if self._entries is None:
            self._entries, self._error = [], ""
            folder = self._folder_path()
            if folder is not None and folder.is_dir():
                try:
                    self._entries = evidence_history.load_folder(folder)
                except OSError as error:
                    self._error = strings.text(self._language(), "EH_READ_FAILED", text=str(error))
        return self._entries

    def _chosen(self) -> list[evidence_history.Entry]:
        return evidence_history.select(self._all(), outcome=self._outcome or None, text=self._query.strip() or None, only_invalid=self._only_invalid)

    def t(self, key: str, **values: object) -> str:
        return strings.text(self._language(), key, **values)

    # -- text ----------------------------------------------------------------------------------------------------
    @Slot(str, result=str)
    def text(self, key: str) -> str:
        return self.t(key)

    @Property(str, notify=changed)
    def title(self) -> str:
        return self.t("EH_TITLE")

    @Property(str, notify=changed)
    def intro(self) -> str:
        return self.t("EH_INTRO")

    @Property(str, notify=changed)
    def closeText(self) -> str:
        return self.t("EH_BTN_CLOSE")

    @Property(str, notify=changed)
    def refreshText(self) -> str:
        return self.t("EH_BTN_REFRESH")

    @Property(str, notify=changed)
    def searchHint(self) -> str:
        return self.t("EH_FILTER_TEXT")

    @Property(str, notify=changed)
    def onlyInvalidText(self) -> str:
        return self.t("EH_ONLY_INVALID")

    @Property(str, notify=changed)
    def outcomeLabel(self) -> str:
        return self.t("EH_FILTER_OUTCOME")

    @Property("QVariantList", notify=changed)
    def outcomeChoices(self) -> list:
        """The labels of the result filter: all, then one for each outcome of a record (``evidence.OUTCOMES``)."""
        return [self.t("EH_FILTER_ALL")] + [self.t(strings.outcome_key(name)) for name in evidence.OUTCOMES]

    @Property("QVariantList", notify=changed)
    def headers(self) -> list:
        return [self.t(key) for key in ("EH_COL_TIME", "EH_COL_KIND", "EH_COL_OUTCOME", "EH_COL_TOOL", "EH_COL_BOARD", "EH_COL_VERSION", "EH_COL_CHECK")]

    # -- state ---------------------------------------------------------------------------------------------------
    @Property(str, notify=changed)
    def folderText(self) -> str:
        folder = self._folder_path()
        return self.t("EH_FOLDER", folder=str(folder)) if folder is not None else ""

    @Property(str, notify=changed)
    def emptyText(self) -> str:
        """Why the list is empty (no folder, a folder that is not there, nothing in it, nothing that matches), or an empty text when it is not."""
        folder = self._folder_path()
        if folder is None:
            return self.t("EH_NO_FOLDER")
        if not folder.is_dir():
            return self.t("EH_FOLDER_MISSING", folder=str(folder))
        if self._all():
            if all(e.other for e in self._all()):
                return self.t("EH_ONLY_OTHERS")
            return "" if self._chosen() else self.t("EH_NO_MATCH")
        return self._error or self.t("EH_EMPTY")

    @Property(str, notify=changed)
    def summaryText(self) -> str:
        entries = self._all()
        if not entries:
            return ""
        counts = evidence_history.summary(entries)
        text = self.t("EH_SUMMARY", shown=len(self._chosen()), records=counts["records"], valid=counts["valid"], invalid=counts["invalid"])
        return text + ("\n" + self.t("EH_OTHERS_SUMMARY", others=counts["others"]) if counts["others"] else "")

    @Property(int, notify=changed)
    def othersCount(self) -> int:
        """How many records of the folder are not evidence (the update reports and the result records): they are not rows of the list and are never not valid."""
        return len(evidence_history.others_of(self._all()))

    @Property(str, notify=changed)
    def othersText(self) -> str:
        """The records that are not evidence, one line each with its type (at most ``ROW_LIMIT``), under a title; empty when there are none."""
        others = evidence_history.others_of(self._all())
        if not others:
            return ""
        lines = [self.t("EH_OTHERS_TITLE") + f" ({len(others)})"]
        for entry in others[:ROW_LIMIT]:
            data = evidence_history.other_row(entry)
            lines.append(f"{data['file']}  -  " + self.t("EH_OTHER_" + str(data["type"]).upper()))
        if len(others) > ROW_LIMIT:
            lines.append("...")
        return "\n".join(lines)

    @Property("QVariantList", notify=changed)
    def rows(self) -> list:
        out = []
        for entry in self._chosen()[:ROW_LIMIT]:
            data = evidence_history.row(entry)
            outcome, kind = str(data["outcome"]), str(data["kind"])
            if data["version_after"]:
                version = f"{data['version_before'] or '?'} -> {data['version_after']}"
            else:
                version = str(data["version_before"] or "")
            out.append({
                "time": data["timestamp_utc"] or "-", "kind": kind, "kindText": self.t(strings.kind_key(kind)) if kind in evidence.KINDS else (kind or "-"),
                "outcome": outcome, "outcomeText": self.t(strings.outcome_key(outcome)) if outcome in evidence.OUTCOMES else (outcome or "-"),
                "tool": f"{data['tool']} {data['tool_version']}".strip() or "-", "board": data["subject"] or "-", "version": version or "-",
                "valid": entry.valid, "checkText": self.t("EH_VALID") if entry.valid else self.t("EH_NOT_VALID"),
                "file": data["file"], "problems": list(entry.problems),
            })
        return out

    @Property(bool, notify=changed)
    def onlyInvalid(self) -> bool:
        return self._only_invalid

    @Property(str, notify=changed)
    def query(self) -> str:
        return self._query

    @Property(int, notify=changed)
    def outcomeIndex(self) -> int:
        return (evidence.OUTCOMES.index(self._outcome) + 1) if self._outcome in evidence.OUTCOMES else 0

    # -- actions (all of them only change what is shown) -----------------------------------------------------------
    @Slot()
    def refresh(self) -> None:
        self._entries = None
        self.changed.emit()

    @Slot(int)
    def setOutcomeIndex(self, index: int) -> None:
        self._outcome = evidence.OUTCOMES[index - 1] if 1 <= index <= len(evidence.OUTCOMES) else ""
        self.changed.emit()

    @Slot(str)
    def setQuery(self, value: str) -> None:
        self._query = value
        self.changed.emit()

    @Slot(bool)
    def setOnlyInvalid(self, value: bool) -> None:
        self._only_invalid = bool(value)
        self.changed.emit()

    @Slot()
    def writeReport(self) -> None:
        """Write ``evidence_report.html`` and ``evidence_report.pdf`` in the folder, with every record of it (the filters of the window do not apply). Only these two
        files are written; the records are not touched."""
        folder = self._folder_path()
        language = self._language()
        try:
            if folder is None or not folder.is_dir():
                raise OSError(self.t("EH_NO_FOLDER"))
            entries = evidence_history.load_folder(folder)    # every record, those that are not evidence too: the report lists them apart
            for fmt in evidence_report.FORMATS:
                (folder / f"evidence_report.{fmt}").write_bytes(evidence_report.render(entries, fmt, language))
            self._report_status = report_strings.text(language, "ER_DONE", path=str(folder / "evidence_report.html"))
        except OSError as error:
            self._report_status = report_strings.text(language, "ER_FAILED", text=str(error))
        self._entries = None
        self.changed.emit()

    @Property(str, notify=changed)
    def reportText(self) -> str:
        return report_strings.text(self._language(), "ER_BTN")

    @Property(str, notify=changed)
    def reportStatus(self) -> str:
        return self._report_status

    @Slot()
    def languageChanged(self) -> None:
        self.changed.emit()
