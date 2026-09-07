# =============================================================================
# URTC Flasher - Animated HYDRA-UMC identity widget for Tkinter.
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""A tiny, dependency-free player for pre-rendered HYDRA-UMC SVG frames.

Tkinter does not support animated SVG files itself.  The maintained source is
``assets/HYDRA_UMC_ICON.svg``; its twelve PNG render frames live underneath
``assets/hydra_umc_icon_frames`` so the normal source run and the one-file
PyInstaller build can show the same animation without embedding a browser or
a heavyweight Qt runtime in this hardware tool.
"""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import ttk


class AnimatedHydraUMCMark:
    """Display the pre-rendered official mark and cycle it while its widget lives."""

    FRAME_COUNT = 12
    FRAME_DELAY_MS = 125

    def __init__(self, parent: tk.Misc, frames_dir: str) -> None:
        self._frames: list[tk.PhotoImage] = []
        for index in range(self.FRAME_COUNT):
            frame_path = os.path.join(frames_dir, f"frame_{index:02d}.png")
            self._frames.append(tk.PhotoImage(file=frame_path))

        self.widget = ttk.Label(parent, image=self._frames[0])
        self._frame_index = 0
        self._after_id: str | None = None
        self.widget.bind("<Destroy>", self._on_destroy, add="+")
        self._schedule_next_frame()

    def _schedule_next_frame(self) -> None:
        self._after_id = self.widget.after(self.FRAME_DELAY_MS, self._advance)

    def _advance(self) -> None:
        if not self.widget.winfo_exists():
            return
        self._frame_index = (self._frame_index + 1) % len(self._frames)
        self.widget.configure(image=self._frames[self._frame_index])
        self._schedule_next_frame()

    def _on_destroy(self, _event: tk.Event) -> None:
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None
