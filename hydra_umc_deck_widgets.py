# =============================================================================
# URTC Flasher - rounded HYDRA-UMC command-deck widgets
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Small Tk widgets that provide the rounded-panel language of Updater.

Tk/ttk themes cannot draw a consistently rounded group box on Windows and
Linux.  ``RoundedDeckCard`` keeps the existing, proven ttk controls as its
children while drawing the actual 16px curved shell behind them.  This keeps
the CAN flashing behaviour separate from the presentation layer.
"""

import tkinter as tk
from tkinter import font as tkfont


class RoundedDeckCard(tk.Frame):
    """A 16px rounded panel with a caption and an ordinary child container."""

    def __init__(self, parent, title, *, canvas_color, panel_color, border_color,
                 accent_color, text_color, title_size=11):
        super().__init__(parent, bg=canvas_color, highlightthickness=0, bd=0)
        self._canvas_color = canvas_color
        self._panel_color = panel_color
        self._border_color = border_color
        self._accent_color = accent_color
        self._text_color = text_color
        self._title = title
        self._title_size = title_size
        self._surface = tk.Canvas(
            self, bg=canvas_color, highlightthickness=0, bd=0, relief="flat"
        )
        self._surface.place(relx=0, rely=0, relwidth=1, relheight=1)
        # Canvas.lower() lowers a *canvas item*, while here we must lower the
        # Canvas widget below the real child-control frame.
        self.tk.call("lower", self._surface._w)
        # The inner frame is inset far enough from the rounded boundary that
        # its rectangular child geometry never cuts across the curved corners.
        self.content = tk.Frame(self, bg=panel_color, highlightthickness=0, bd=0)
        self.content.place(x=14, y=34)
        self.content.bind("<Configure>", self._sync_requested_size, add="+")
        self.bind("<Configure>", self._redraw, add="+")

    @staticmethod
    def _rounded_points(left, top, right, bottom, radius):
        return [
            left + radius, top, right - radius, top, right, top,
            right, top + radius, right, bottom - radius, right, bottom,
            right - radius, bottom, left + radius, bottom, left, bottom,
            left, bottom - radius, left, top + radius, left, top,
        ]

    def _sync_requested_size(self, _event=None):
        """Let grid/pack request the size that the real controls require."""
        requested_width = self.content.winfo_reqwidth() + 28
        requested_height = self.content.winfo_reqheight() + 48
        if self.winfo_reqwidth() != requested_width or self.winfo_reqheight() != requested_height:
            self.configure(width=requested_width, height=requested_height)

    def _redraw(self, event=None):
        width = max((event.width if event else self.winfo_width()), 2)
        height = max((event.height if event else self.winfo_height()), 2)
        inset = 1
        self._surface.delete("deck")
        self._surface.create_polygon(
            self._rounded_points(inset, inset, width - inset, height - inset, 16),
            smooth=True, splinesteps=18, fill=self._panel_color,
            outline=self._border_color, width=1, tags="deck",
        )
        self._surface.create_rectangle(
            14, 14, 18, 27, fill=self._accent_color, outline="", tags="deck"
        )
        self._surface.create_text(
            25, 20, anchor="w", text=self._title, fill=self._accent_color,
            font=("Bahnschrift", self._title_size, "bold"), tags="deck",
        )
        # Update the embedded real-control surface after its parent has been
        # allocated a width by grid. Its height follows content unless the
        # caller deliberately stretches this card vertically.
        self.content.place_configure(width=max(width - 28, 1), height=max(height - 47, 1))


class RoundedDeckButton(tk.Canvas):
    """A keyboard-accessible button with Updater's 10px rounded geometry.

    It deliberately accepts the familiar ``text``, ``command`` and ``state``
    options used by ttk.Button, so existing connection/flash callbacks can be
    retained unchanged while the high-value actions gain a real curved shell.
    """

    def __init__(self, parent, *, text, command, panel_color, border_color,
                 text_color, muted_color, accent_color, accent=False, state="normal"):
        self._text = text
        self._command = command
        self._panel_color = panel_color
        self._border_color = border_color
        self._text_color = text_color
        self._muted_color = muted_color
        self._accent_color = accent_color
        self._accent = accent
        self._state = state
        self._hover = False
        self._pressed = False
        self._font = tkfont.Font(family="Bahnschrift", size=10, weight="bold")
        requested_width = max(112, self._font.measure(text) + 34)
        super().__init__(
            parent, width=requested_width, height=42, bg=panel_color,
            highlightthickness=0, bd=0, relief="flat", takefocus=True,
        )
        self.bind("<Configure>", lambda _event: self._draw())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Return>", lambda _event: self.invoke())
        self.bind("<space>", lambda _event: self.invoke())
        self._draw()

    @staticmethod
    def _rounded_points(left, top, right, bottom, radius):
        return [
            left + radius, top, right - radius, top, right, top,
            right, top + radius, right, bottom - radius, right, bottom,
            right - radius, bottom, left + radius, bottom, left, bottom,
            left, bottom - radius, left, top + radius, left, top,
        ]

    def _draw(self):
        self.delete("button")
        width, height = max(self.winfo_width(), 2), max(self.winfo_height(), 2)
        enabled = self._state != "disabled"
        base = self._accent_color if self._accent else self._panel_color
        if not enabled:
            base, border, foreground = "#122031", "#25384b", "#6d8294"
        elif self._pressed:
            base, border, foreground = ("#07566A" if self._accent else "#0A1E2B"), self._accent_color, self._text_color
        elif self._hover:
            base, border, foreground = ("#109DB9" if self._accent else "#173A56"), self._accent_color, self._text_color
        else:
            border, foreground = (self._accent_color if self._accent else self._border_color), self._text_color
        self.create_polygon(
            self._rounded_points(1, 1, width - 1, height - 1, 10), smooth=True,
            splinesteps=18, fill=base, outline=border, width=1, tags="button",
        )
        if enabled:
            self.create_line(12, 2, width - 12, 2, fill="#9EEEFF", width=1, tags="button")
        self.create_text(
            width // 2, height // 2, text=self._text, fill=foreground,
            font=self._font, tags="button",
        )

    def _on_enter(self, _event):
        if self._state != "disabled":
            self._hover = True
            self.configure(cursor="hand2")
            self._draw()

    def _on_leave(self, _event):
        self._hover = self._pressed = False
        self.configure(cursor="")
        self._draw()

    def _on_press(self, _event):
        if self._state != "disabled":
            self._pressed = True
            self.focus_set()
            self._draw()

    def _on_release(self, event):
        activate = self._pressed and self._state != "disabled" and 0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height()
        self._pressed = False
        self._draw()
        if activate:
            self.invoke()

    def invoke(self):
        if self._state != "disabled" and self._command:
            return self._command()
        return None

    def configure(self, cnf=None, **kwargs):
        options = dict(cnf or {})
        options.update(kwargs)
        if "text" in options:
            self._text = options.pop("text")
            self.configure(width=max(112, self._font.measure(self._text) + 34))
        if "command" in options:
            self._command = options.pop("command")
        if "state" in options:
            self._state = options.pop("state")
        result = super().configure(**options) if options else None
        if hasattr(self, "_state"):
            self._draw()
        return result

    config = configure
