# =============================================================================
# URTC-COMMON - src/urtc_common/update_controller.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The state machine behind the "Check for updates" menu of a window, with no window in it.

The flasher, the tester and the updater each draw their own buttons; the order of things is the same, so it lives
here and is tested once:

    idle -> checking -> up_to_date | available | error
    available -> downloading -> ready | error          (download and verification; nothing installed yet)
    ready -> installing -> installed | error           (only after ``confirm_install``)
    installed -> (the program is restarted by the person) ; rolled_back

``snapshot()`` is a plain dictionary for the window (``state``, ``version``, ``notes``, ``progress``, ``error_code``,
``error_text``, ``current``, ``can_roll_back``, ``auto_check``, ``require_confirmation``). The steps that touch the
network run in a worker thread that this class starts (or inline with ``background=False``, for the tests); every
change calls ``on_change(snapshot)``, which the window forwards to its own thread. Nothing here installs by itself:
``install`` needs ``confirm_install`` first (once, for that one package) unless the person turned the confirmation off
in the settings, and ``startup_check`` does nothing unless the person turned ``auto_check`` on.
"""
from __future__ import annotations

import threading
from collections.abc import Callable

from . import self_update as su
from . import update_service as svc

IDLE, CHECKING, UP_TO_DATE, AVAILABLE = "idle", "checking", "up_to_date", "available"
DOWNLOADING, READY, INSTALLING, INSTALLED, ERROR, ROLLED_BACK = "downloading", "ready", "installing", "installed", "error", "rolled_back"
BUSY_STATES = {CHECKING, DOWNLOADING, INSTALLING}


class UpdateController:
    def __init__(self, service: svc.UpdateService, on_change: Callable[[dict], None] | None = None, background: bool = True) -> None:
        self.service = service
        self.on_change = on_change
        self.background = background
        self._lock = threading.RLock()
        self._state = IDLE
        self._offer: su.Offer | None = None
        self._prepared: svc.Prepared | None = None
        self._confirmed = False
        self._progress = (0, 0)
        self._error: tuple[str, str] = ("", "")

    # -- reading ---------------------------------------------------------------------------------------------------
    def snapshot(self) -> dict:
        with self._lock:
            done, total = self._progress
            try:
                can_roll_back = len(su.installed_versions(self.service.root)) > 1
            except OSError:
                can_roll_back = False
            return {
                "state": self._state,
                "installed": self.service.installed,
                "version": self._offer.version if self._offer else "",
                "notes": self._offer.notes if self._offer else "",
                "progress": (done * 100 // total) if total else 0,
                "error_code": self._error[0],
                "error_text": self._error[1],
                "current": self.service.current() or "",
                "can_roll_back": can_roll_back,
                "auto_check": self.service.policy.auto_check,
                "require_confirmation": self.service.policy.require_confirmation,
            }

    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    def _set(self, state: str, **fields) -> None:
        with self._lock:
            self._state = state
            if "offer" in fields:
                self._offer = fields["offer"]
            if "error" in fields:
                self._error = fields["error"]
            elif state != ERROR:
                self._error = ("", "")
            callback = self.on_change
            shot = self.snapshot()
        if callback:
            callback(shot)

    def _run(self, work: Callable[[], None]) -> bool:
        if self.background:
            threading.Thread(target=work, name="urtc-update", daemon=True).start()
        else:
            work()
        return True

    def _fail(self, error: BaseException) -> None:
        code = error.code if isinstance(error, su.UpdateError) else "unexpected"
        self._set(ERROR, error=(code, str(error)))

    # -- steps -----------------------------------------------------------------------------------------------------
    def check(self) -> bool:
        """Asks GitHub once. Returns False (and does nothing) when another step is running."""
        with self._lock:
            if self._state in BUSY_STATES:
                return False
            self._offer = None
            self._prepared = None
            self._confirmed = False
        self._set(CHECKING)

        def work() -> None:
            try:
                offer = self.service.check()
            except (su.UpdateError, OSError, ValueError) as error:
                self._fail(error)
                return
            if offer is None:
                self._set(UP_TO_DATE, offer=None)
            else:
                self._set(AVAILABLE, offer=offer)

        return self._run(work)

    def startup_check(self) -> bool:
        """For the program to call when it opens: a check only when the person turned ``auto_check`` on; never anything else."""
        if not self.service.policy.auto_check:
            return False
        return self.check()

    def download(self) -> bool:
        """Downloads and verifies the offered package. Nothing is installed."""
        with self._lock:
            if self._state != AVAILABLE or self._offer is None:
                return False
            offer = self._offer
            self._progress = (0, offer.package.size)
        self._set(DOWNLOADING)

        def progress(done: int, total: int) -> None:
            with self._lock:
                self._progress = (done, total)
            if self.on_change:
                self.on_change(self.snapshot())

        def work() -> None:
            try:
                prepared = self.service.prepare(offer, progress)
            except (su.UpdateError, OSError) as error:
                self._fail(error)
                return
            with self._lock:
                self._prepared = prepared
                self._confirmed = False
            self._set(READY)

        return self._run(work)

    def confirm_install(self) -> bool:
        """The person saw the version and the notes and said yes. Valid for the prepared package only."""
        with self._lock:
            if self._state != READY:
                return False
            self._confirmed = True
            return True

    def install(self) -> bool:
        with self._lock:
            if self._state != READY or self._prepared is None:
                return False
            missing_confirmation = self.service.policy.require_confirmation and not self._confirmed
            prepared, confirmed = self._prepared, self._confirmed
        if missing_confirmation:
            self._set(READY, error=("confirmation_required", "the person has not confirmed this update"))
            return False
        self._set(INSTALLING)

        def work() -> None:
            try:
                self.service.install(prepared, confirmed=confirmed)
            except (su.UpdateError, OSError) as error:
                self._fail(error)
                return
            with self._lock:
                self._prepared = None
                self._confirmed = False
            self._set(INSTALLED)

        return self._run(work)

    def roll_back(self) -> bool:
        with self._lock:
            if self._state in BUSY_STATES:
                return False
        try:
            self.service.rollback()
        except (su.UpdateError, OSError) as error:
            self._fail(error)
            return False
        self._set(ROLLED_BACK)
        return True

    def dismiss(self) -> None:
        """Back to idle (the window closed the dialog); an offer and a prepared package are forgotten."""
        with self._lock:
            if self._state in BUSY_STATES:
                return
            self._offer = None
            self._prepared = None
            self._confirmed = False
        self._set(IDLE)
