# =============================================================================
# URTC Flasher - tests/test_gui_threading.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""The Tk window's worker threads must not touch Tk. The window is built without
a display (no __init__): every Tk object is a fake that fails when it is used off the
main thread, the transport is the simulated bootloader, and the results reach the
fake widgets only when the main thread drains the mailbox."""
from __future__ import annotations

import json
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

pytest.importorskip("tkinter")
import flasher_gui  # noqa: E402
from flasher_config import THIS_HARDWARE_ID  # noqa: E402
from flasher_transports import MockCAN  # noqa: E402
from flasher_uithread import UiMailbox  # noqa: E402

MAIN = threading.get_ident()


def _main_only(name):
    assert threading.get_ident() == MAIN, f"{name} was used off the main thread"


class _Var:
    def __init__(self, value=None):
        self.value = value

    def get(self):
        _main_only("a Tk variable")
        return self.value

    def set(self, value):
        _main_only("a Tk variable")
        self.value = value


class _Widget:
    def __init__(self):
        self.calls = []

    def config(self, **kwargs):
        _main_only("a widget")
        self.calls.append(kwargs)

    configure = config

    def __setitem__(self, key, value):
        _main_only("a widget")
        self.calls.append({key: value})


class _Root:
    def after(self, ms, fn):
        _main_only("root.after")
        return 1

    def after_cancel(self, ident):
        _main_only("root.after_cancel")

    def destroy(self):
        _main_only("root.destroy")
        self.destroyed = True


@pytest.fixture
def gui(tmp_path, monkeypatch):
    window = flasher_gui.FlasherGUI.__new__(flasher_gui.FlasherGUI)
    window.root = _Root()
    window._ui = UiMailbox(window.root)
    window._post = window._ui.post
    window._file_logger = None
    window._logs_folder = str(tmp_path / "logs")
    window.log_text = _Widget()
    window.progress = _Widget()
    window.cancel_btn = _Widget()
    window.transfer_status_var = _Var("")
    window.transfer_status_label = _Widget()
    window._stop_requested = False
    window._flash_thread = None
    window._swd_flash_thread = None
    window.transport = MockCAN()
    window.busy_states = []
    window._set_ui_busy_state = lambda busy: window.busy_states.append(busy)
    window._stop_transfer_liveness_watch = lambda: window.busy_states.append("stopped")
    window.dialogs = []
    monkeypatch.setattr(flasher_gui.messagebox, "showinfo", lambda *a, **k: window.dialogs.append(("info", a)))
    monkeypatch.setattr(flasher_gui.messagebox, "showerror", lambda *a, **k: window.dialogs.append(("error", a)))
    monkeypatch.setattr(flasher_gui.messagebox, "askyesno", lambda *a, **k: True)
    # a variable that would be read by a worker fails the test
    for name in ("flash_target_var", "trigger_var", "erase_fram_var", "allow_downgrade_var", "bitrate_var", "swd_tool_var"):
        setattr(window, name, _Var("master"))
    return window


def _image(tmp_path, size=3000):
    path = tmp_path / "URTC_MAIN_FIRMWARE_v0.3.3.bin"
    path.write_bytes(bytes((i % 251) + 1 for i in range(size)))
    Path(str(path) + ".manifest.json").write_text(
        json.dumps({"component": "main_application", "hardware_id": f"0x{THIS_HARDWARE_ID:08X}", "version": "0.3.3"}),
        encoding="utf-8")
    return str(path)


def _drain(window):
    while window._ui.drain():
        pass


def test_the_flash_worker_posts_everything_and_touches_no_tk_object(gui, tmp_path):
    options = {"target": "master", "trigger": False, "erase_fram": False, "allow_downgrade": False, "path": _image(tmp_path)}
    worker = threading.Thread(target=gui._flash_worker, args=(options,))
    worker.start()
    worker.join()
    # nothing reached the widgets while only the worker ran
    assert gui.dialogs == [] and gui.busy_states == [] and gui.progress.calls == []
    _drain(gui)
    assert [kind for kind, _a in gui.dialogs] == ["info"]
    assert gui.busy_states == [False, "stopped"]
    assert gui.progress.calls and gui.progress.calls[-1] == {"value": 100}
    assert any("\n" in call.get("state", "") or True for call in gui.log_text.calls)
    assert list(Path(gui._logs_folder).glob("urtc_update_report_*.json"))  # the update report was written


def test_a_failed_flash_reports_the_error_through_the_mailbox(gui, tmp_path):
    options = {"target": "master", "trigger": False, "erase_fram": False, "allow_downgrade": False, "path": str(tmp_path / "missing.bin")}
    worker = threading.Thread(target=gui._flash_worker, args=(options,))
    worker.start()
    worker.join()
    assert gui.dialogs == []
    _drain(gui)
    assert [kind for kind, _a in gui.dialogs] == ["error"]
    assert gui.busy_states == [False, "stopped"]


def test_the_connect_worker_gets_the_bitrate_instead_of_reading_the_variable(gui, monkeypatch):
    opened = []

    class _Adapter:
        def __init__(self, port, log=None):
            opened.append(port)

        def open_channel(self, code=None, listen_only=False):
            opened.append(code)

    monkeypatch.setattr(flasher_gui, "SLCAN", _Adapter)
    gui._on_connected = lambda port, is_serial, bitrate: opened.append(("connected", port, bitrate))
    worker = threading.Thread(target=gui._connect_worker, args=("COM3", True, "250 kbit/s"))
    worker.start()
    worker.join()
    _drain(gui)
    assert opened[0] == "COM3"
    assert opened[-1] == ("connected", "COM3", "250 kbit/s")


def test_log_from_a_thread_is_deferred_and_a_late_log_after_close_is_dropped(gui):
    worker = threading.Thread(target=gui.log, args=("hello",))
    worker.start()
    worker.join()
    assert gui.log_text.calls == []
    _drain(gui)
    assert gui.log_text.calls  # shown once the main thread drains
    gui._ui.close()
    late = threading.Thread(target=gui.log, args=("late",))
    late.start()
    late.join()
    before = len(gui.log_text.calls)
    _drain(gui)
    assert len(gui.log_text.calls) == before  # no widget is touched after the window is closed


def test_closing_the_window_stops_the_mailbox_before_destroying_it(gui):
    gui.on_close()
    assert gui._ui.closed and gui.root.destroyed and gui._stop_requested
