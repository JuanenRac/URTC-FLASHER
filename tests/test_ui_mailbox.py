# =============================================================================
# URTC Flasher - tests/test_ui_mailbox.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Worker threads never touch Tk: they post to a mailbox that the main thread drains."""
from __future__ import annotations

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flasher_uithread import UiMailbox


class _FakeRoot:
    """Records the thread every call came from; `after` only stores the callback."""

    def __init__(self):
        self.main = threading.get_ident()
        self.callbacks = {}
        self.cancelled = []
        self.next_id = 0
        self.foreign_calls = 0

    def after(self, ms, fn):
        if threading.get_ident() != self.main:
            self.foreign_calls += 1
        self.next_id += 1
        self.callbacks[self.next_id] = fn
        return self.next_id

    def after_cancel(self, ident):
        self.cancelled.append(ident)
        self.callbacks.pop(ident, None)


def test_calls_posted_from_threads_run_on_the_main_thread_in_order():
    root = _FakeRoot()
    box = UiMailbox(root)
    ran = []

    def worker(n):
        for i in range(50):
            box.post(lambda n=n, i=i: ran.append((n, i, threading.get_ident())))

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert ran == []  # nothing runs while the main thread is not draining
    while box.drain():
        pass
    assert len(ran) == 200
    assert {thread for _n, _i, thread in ran} == {root.main}
    for n in range(4):  # each producer keeps its own order
        assert [i for m, i, _t in ran if m == n] == list(range(50))
    assert root.foreign_calls == 0  # the threads never touched the root


def test_start_polls_with_after_and_rearms():
    root = _FakeRoot()
    box = UiMailbox(root)
    ran = []
    box.start()
    box.post(ran.append, 1)
    (ident, tick), = root.callbacks.items()
    root.callbacks.clear()
    tick()
    assert ran == [1]
    assert len(root.callbacks) == 1  # re-armed for the next poll


def test_the_next_poll_is_armed_before_a_blocking_call_runs():
    """A call that opens a modal dialog must not stop later log lines from being shown."""
    root = _FakeRoot()
    box = UiMailbox(root)
    seen = []
    box.start()
    box.post(lambda: seen.append(len(root.callbacks)))
    tick = next(iter(root.callbacks.values()))
    root.callbacks.clear()
    tick()
    assert seen == [1]


def test_close_drops_queued_and_late_posts_and_cancels_the_timer():
    root = _FakeRoot()
    box = UiMailbox(root)
    box.start()
    ran = []
    box.post(ran.append, "queued")
    box.close()
    assert box.post(ran.append, "late") is False
    assert box.drain() == 0
    assert ran == []
    assert root.cancelled  # the pending timer was cancelled


def test_a_failing_call_is_reported_and_does_not_stop_the_others():
    errors = []
    box = UiMailbox(_FakeRoot(), on_error=errors.append)
    ran = []

    def boom():
        raise RuntimeError("widget gone")

    box.post(boom)
    box.post(ran.append, "after")
    box.drain()
    assert ran == ["after"]
    assert len(errors) == 1 and "widget gone" in errors[0]
