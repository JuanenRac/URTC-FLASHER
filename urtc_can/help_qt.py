# =============================================================================
# URTC-COMMON - src/urtc_common/help_qt.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The Qt object behind ``HelpDialog.qml``: the title and the sections of the quick guide of a program, in the language it is in."""
from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Property, QObject, Signal, Slot

from . import help_text, update_strings


class HelpModel(QObject):
    changed = Signal()

    def __init__(self, app: str, language: Callable[[], str] = lambda: "english", parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._app = app
        self._language = language

    @Property(str, notify=changed)
    def title(self) -> str:
        return help_text.title(self._language())

    @Property(str, notify=changed)
    def closeText(self) -> str:
        return update_strings.text(self._language(), "UPD_BTN_CLOSE")

    @Property("QVariantList", notify=changed)
    def sections(self) -> list:
        return [{"title": heading, "text": body} for heading, body in help_text.guide(self._app, self._language())]

    @Slot()
    def languageChanged(self) -> None:
        self.changed.emit()
