# =============================================================================
# URTC-COMMON - src/urtc_common/node_picker_qt.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The Qt object behind ``NodePickerDialog.qml``: the rows, the texts and the buttons of the window that selects one of several tool heads.

The program creates one ``NodePickerModel`` around a ``node_picker.NodePicker``, exposes it to QML and opens the dialog from its menu.
Finding the heads and selecting one wait for the bus, so they run in a thread of their own and the window shows ``busy`` meanwhile;
``sync=True`` runs them in place (tests and pictures without a bus). A timer keeps the selection alive while a head is selected, and
what the picker says (a lapse included) reaches the person as a message and, for a lapse, also as ``lapseText``. PySide6 is imported
here and nowhere else of the node picker.
"""
from __future__ import annotations

import threading
from collections.abc import Callable

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from . import node_picker as npk
from . import node_picker_strings as strings

TICK_MS = 500


class NodePickerModel(QObject):
    changed = Signal()
    _finished = Signal()

    def __init__(self, picker: npk.NodePicker | None = None, language: Callable[[], str] = lambda: "english",
                 save_release: Callable[[bool], None] | None = None, sync: bool = False,
                 app_busy: Callable[[], bool] = lambda: False, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.picker: npk.NodePicker | None = None
        self._language = language
        self._save_release = save_release
        self._sync = sync
        self._app_busy = app_busy        # True while the program does an exchange of its own on the bus: the picker keeps off it
        self._busy = False
        self._release_pending = True
        self._shot: dict = npk.empty_snapshot(language())
        self._messages: list[dict] = []
        self._lapse = ""
        self._finished.connect(self._refresh)
        self._timer = QTimer(self)
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self._tick)
        if picker is not None:
            self.attach(picker)

    # -- text ------------------------------------------------------------------------------------------------------
    @Slot(str, result=str)
    def t(self, key: str) -> str:
        return strings.text(self._language(), key)

    @Property(str, notify=changed)
    def title(self) -> str:
        return self.t("NP_TITLE")

    @Property(str, notify=changed)
    def summary(self) -> str:
        return self._shot["summary"]

    @Property(str, notify=changed)
    def switchText(self) -> str:
        return self._shot["switch_text"] if self._shot["searched"] else ""

    @Property(str, notify=changed)
    def switchLevel(self) -> str:
        return "warning" if self._shot["switch"] in (npk.SW_PENDING_ON, npk.SW_PENDING_OFF) else "info"

    @Property(str, notify=changed)
    def message(self) -> str:
        return self._messages[-1]["text"] if self._messages else self.t("NP_MSG_NOT_SEARCHED")

    @Property(str, notify=changed)
    def messageLevel(self) -> str:
        return self._messages[-1]["level"] if self._messages else "info"

    @Property("QVariantList", notify=changed)
    def messages(self) -> list:
        return list(self._messages[-4:])

    @Property(str, notify=changed)
    def lapseText(self) -> str:
        return self._lapse

    @Property(str, notify=changed)
    def confirmText(self) -> str:
        return self._shot["confirm_text"]

    # -- state -----------------------------------------------------------------------------------------------------
    @Property("QVariantList", notify=changed)
    def rows(self) -> list:
        return self._shot["rows"]

    @Property(bool, notify=changed)
    def busy(self) -> bool:
        return self._busy

    @Property(str, notify=changed)
    def mode(self) -> str:
        return self._shot["mode"]

    @Property(int, notify=changed)
    def selected(self) -> int:
        return -1 if self._shot["selected"] is None else int(self._shot["selected"])

    @Property(bool, notify=changed)
    def hasSelection(self) -> bool:
        return self._shot["selected"] is not None

    @Property(bool, notify=changed)
    def releaseOnLapse(self) -> bool:
        return self._release_pending if self.picker is None else bool(self._shot["release_on_lapse"])

    @Property(bool, notify=changed)
    def mayShowRows(self) -> bool:
        return self._shot["mode"] == npk.MODE_MULTI

    # -- the connection -------------------------------------------------------------------------------------------
    def attach(self, picker: npk.NodePicker | None) -> None:
        """Give the window the picker of the connection that was just opened, or None when it was closed."""
        self.picker = picker
        self._messages.clear()
        self._lapse = ""
        if picker is not None:
            picker.language = self._language
            picker.release_on_lapse = self._release_pending
        self._refresh()

    @Property(bool, notify=changed)
    def connected(self) -> bool:
        return self.picker is not None

    # -- actions ---------------------------------------------------------------------------------------------------
    @Slot()
    def find(self) -> None:
        if self.picker is None:
            self._messages.append({"text": self.t("NP_MSG_NOT_CONNECTED"), "level": "warning"})
            self.changed.emit()
            return
        self._run(self.picker.scan)

    @Slot(int)
    def ask(self, node: int) -> None:
        if self.picker is not None:
            self.picker.ask(node)
        self._refresh()

    @Slot()
    def confirm(self) -> None:
        if self.picker is not None:
            self._run(self.picker.confirm)

    @Slot()
    def cancel(self) -> None:
        if self.picker is not None:
            self.picker.cancel()
        self._refresh()

    @Slot()
    def release(self) -> None:
        if self.picker is not None:
            self._run(self.picker.release)

    @Slot(bool, result=bool)
    def needsWarningForRelease(self, value: bool) -> bool:
        """True when the change lowers the protection (it switches the release of the heads off): the dialog asks first."""
        return not value and self._release_pending

    def restoreReleaseOption(self, value: bool) -> None:
        """The program gives back the option it saved last time (nothing is saved again)."""
        self._release_pending = bool(value)
        if self.picker is not None:
            self.picker.release_on_lapse = bool(value)
        self._refresh()

    @Slot(bool)
    def setReleaseOnLapse(self, value: bool) -> None:
        self._release_pending = bool(value)
        if self.picker is not None:
            self.picker.release_on_lapse = bool(value)
        if self._save_release:
            self._save_release(bool(value))
        self._refresh()

    @Slot()
    def languageChanged(self) -> None:
        self._refresh()

    def start(self) -> None:
        """Start the timer that keeps the selection alive and notices a lapse (the program calls it once, after creating the model)."""
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    # -- inside ----------------------------------------------------------------------------------------------------
    def _run(self, work: Callable[[], object]) -> None:
        if self._busy or self._app_busy():
            return
        self._busy = True
        self.changed.emit()
        if self._sync:
            work()
            self._busy = False
            self._refresh()
            return

        def job() -> None:
            try:
                work()
            finally:
                self._busy = False
                self._finished.emit()

        threading.Thread(target=job, daemon=True, name="urtc-node-picker").start()

    def _tick(self) -> None:
        if self._busy or self.picker is None or self.picker.selected is None or self._app_busy():
            return
        self._run(self.picker.tick)

    def _refresh(self) -> None:
        language = self._language()
        if self.picker is None:
            self._shot = npk.empty_snapshot(language)
            self.changed.emit()
            return
        for notice in self.picker.take_notices():
            text = self.picker.render(notice, language)
            self._messages.append({"text": text, "level": notice.level})
            if notice.key in ("NP_LAPSE_RELEASED", "NP_LAPSE_KEPT"):
                self._lapse = text
            elif notice.key in ("NP_MSG_SELECTED", "NP_MSG_RELEASED"):
                self._lapse = ""
        del self._messages[:-12]
        self._shot = self.picker.snapshot(language)
        self.changed.emit()
