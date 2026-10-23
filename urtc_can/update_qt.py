# =============================================================================
# URTC-COMMON - src/urtc_common/update_qt.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The Qt object behind ``UpdateDialog.qml``: the properties the dialog binds to and the slots its buttons call.

The program creates one ``UpdateModel`` with its ``UpdateService``, exposes it to QML (as a property of its backend or a
context property) and opens the dialog from its menu. The model forwards the changes of the ``UpdateController`` (which
come from a worker thread) to the GUI thread, says everything in the language the program is in
(``update_strings``), and keeps the two options of the person (``auto_check``, ``require_confirmation``) through a
callback so the program saves them where it saves its own settings. Lowering a protection is asked by the dialog first
(``needsWarning``). PySide6 is imported here and nowhere else of the update code.
"""
from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Property, QObject, Signal, Slot

from . import update_controller as uc
from . import update_service as svc
from . import update_strings as strings


class UpdateModel(QObject):
    changed = Signal()
    _pushed = Signal(object)

    def __init__(
        self,
        service: svc.UpdateService,
        language: Callable[[], str] = lambda: "english",
        save_options: Callable[[bool, bool], None] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._language = language
        self._save_options = save_options
        self._shot: dict = {}
        self.controller = uc.UpdateController(service, on_change=self._pushed.emit)
        self._pushed.connect(self._take)
        self._shot = self.controller.snapshot()

    def _take(self, shot: dict) -> None:
        self._shot = shot
        self.changed.emit()

    # -- text ------------------------------------------------------------------------------------------------------
    @Slot(str, result=str)
    def t(self, key: str) -> str:
        shot = self._shot
        return strings.text(self._language(), key, version=shot.get("version", ""), installed=shot.get("installed", ""),
                            progress=shot.get("progress", 0), current=shot.get("current", ""), text=shot.get("error_text", ""))

    @Property(str, notify=changed)
    def title(self) -> str:
        return self.t("UPD_TITLE")

    @Property(str, notify=changed)
    def statusText(self) -> str:
        state = self._shot.get("state", uc.IDLE)
        key = {
            uc.CHECKING: "UPD_CHECKING", uc.UP_TO_DATE: "UPD_UP_TO_DATE", uc.AVAILABLE: "UPD_AVAILABLE", uc.DOWNLOADING: "UPD_DOWNLOADING",
            uc.READY: "UPD_READY", uc.INSTALLING: "UPD_INSTALLING", uc.INSTALLED: "UPD_INSTALLED", uc.ROLLED_BACK: "UPD_ROLLED_BACK",
        }.get(state)
        if state == uc.ERROR or (state == uc.READY and self._shot.get("error_code")):
            return self.t(strings.error_key(self._shot.get("error_code", "")))
        return self.t(key) if key else ""

    # -- state -----------------------------------------------------------------------------------------------------
    @Property(str, notify=changed)
    def state(self) -> str:
        return self._shot.get("state", uc.IDLE)

    @Property(str, notify=changed)
    def version(self) -> str:
        return self._shot.get("version", "")

    @Property(str, notify=changed)
    def notes(self) -> str:
        return self._shot.get("notes", "")

    @Property(int, notify=changed)
    def progress(self) -> int:
        return int(self._shot.get("progress", 0))

    @Property(bool, notify=changed)
    def busy(self) -> bool:
        return self._shot.get("state") in uc.BUSY_STATES

    @Property(bool, notify=changed)
    def isError(self) -> bool:
        return self._shot.get("state") == uc.ERROR or bool(self._shot.get("error_code"))

    @Property(bool, notify=changed)
    def canCheck(self) -> bool:
        return self._shot.get("state") not in uc.BUSY_STATES

    @Property(bool, notify=changed)
    def canDownload(self) -> bool:
        return self._shot.get("state") == uc.AVAILABLE

    @Property(bool, notify=changed)
    def canInstall(self) -> bool:
        return self._shot.get("state") == uc.READY

    @Property(bool, notify=changed)
    def canRollBack(self) -> bool:
        return bool(self._shot.get("can_roll_back")) and self._shot.get("state") not in uc.BUSY_STATES

    @Property(bool, notify=changed)
    def autoCheck(self) -> bool:
        return bool(self._shot.get("auto_check"))

    @Property(bool, notify=changed)
    def requireConfirmation(self) -> bool:
        return bool(self._shot.get("require_confirmation"))

    # -- actions ---------------------------------------------------------------------------------------------------
    @Slot()
    def check(self) -> None:
        self.controller.check()

    @Slot()
    def startupCheck(self) -> None:
        """For the program to call when it opens; it does nothing unless the person turned the automatic check on."""
        self.controller.startup_check()

    @Slot()
    def download(self) -> None:
        self.controller.download()

    @Slot()
    def install(self) -> None:
        """Called by the dialog after the person said yes in its confirmation."""
        self.controller.confirm_install()
        self.controller.install()

    @Slot()
    def rollBack(self) -> None:
        self.controller.roll_back()

    @Slot()
    def dismiss(self) -> None:
        self.controller.dismiss()

    # -- options ---------------------------------------------------------------------------------------------------
    @Slot(bool, result=bool)
    def needsWarningForAuto(self, value: bool) -> bool:
        return svc.is_lowering(self.controller.service.policy, svc.UpdatePolicy(auto_check=value, require_confirmation=self.controller.service.policy.require_confirmation))

    @Slot(bool, result=bool)
    def needsWarningForConfirmation(self, value: bool) -> bool:
        return svc.is_lowering(self.controller.service.policy, svc.UpdatePolicy(auto_check=self.controller.service.policy.auto_check, require_confirmation=value))

    @Slot(bool)
    def setAutoCheck(self, value: bool) -> None:
        self._set_policy(auto_check=bool(value))

    @Slot(bool)
    def setRequireConfirmation(self, value: bool) -> None:
        self._set_policy(require_confirmation=bool(value))

    def _set_policy(self, **changes) -> None:
        service = self.controller.service
        old = service.policy
        service.policy = svc.UpdatePolicy(auto_check=changes.get("auto_check", old.auto_check),
                                          require_confirmation=changes.get("require_confirmation", old.require_confirmation))
        if self._save_options:
            self._save_options(service.policy.auto_check, service.policy.require_confirmation)
        self._take(self.controller.snapshot())

    @Slot()
    def languageChanged(self) -> None:
        """The program changed language: the texts are read again."""
        self.changed.emit()
