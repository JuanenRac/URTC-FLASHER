# =============================================================================
# URTC Flasher - hand-off from worker threads to the Tk main thread.
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Tkinter is not thread-safe: calling ``root.after`` or reading a Tk variable
from a worker thread usually works, but is not guaranteed, and fails when the
window is closed while a worker is still logging.

Worker threads therefore never touch Tk. They call :meth:`UiMailbox.post`,
which only appends to a thread-safe queue; the main thread drains the queue
from a ``root.after`` timer (:meth:`UiMailbox.start`). After :meth:`close`
nothing is run any more and late posts are silently dropped.
"""
from __future__ import annotations

import queue
import traceback


class UiMailbox:
    POLL_MS = 30
    MAX_PER_TICK = 200

    def __init__(self, root, on_error=None):
        self._root = root
        self._queue: queue.SimpleQueue = queue.SimpleQueue()
        self._closed = False
        self._after_id = None
        self._on_error = on_error or (lambda text: traceback.print_exc())

    @property
    def closed(self) -> bool:
        return self._closed

    def post(self, fn, *args) -> bool:
        """Queue ``fn(*args)`` to run on the main thread. Safe from any thread."""
        if self._closed:
            return False
        self._queue.put((fn, args))
        return True

    def start(self):
        """Begin polling. Must be called on the main thread."""
        if self._after_id is None and not self._closed:
            self._after_id = self._root.after(self.POLL_MS, self._tick)

    def drain(self) -> int:
        """Run the queued calls (main thread). Returns how many ran."""
        ran = 0
        while ran < self.MAX_PER_TICK and not self._closed:
            try:
                fn, args = self._queue.get_nowait()
            except queue.Empty:
                break
            ran += 1
            try:
                fn(*args)
            except Exception:
                self._on_error(traceback.format_exc())
        return ran

    def _tick(self):
        self._after_id = None
        if self._closed:
            return
        # Re-arm before running the calls: one of them may open a modal dialog,
        # and the log lines posted meanwhile must still appear.
        self._after_id = self._root.after(self.POLL_MS, self._tick)
        self.drain()

    def close(self):
        """Stop polling and drop anything still queued (main thread)."""
        self._closed = True
        if self._after_id is not None:
            try:
                self._root.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
