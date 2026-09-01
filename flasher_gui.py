# =============================================================================
# URTC Flasher - Main GUI (FlasherGUI). Only ever imported when NOT running
# in --cli mode - see urtc_flasher.py's own conditional tkinter import
# reasoning, which applies here too since this module is only loaded once
# that decision has already been made.
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
import glob
import logging
import os
import platform
import sys
import threading
import time
import zipfile

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import flasher_config
from flasher_config import (
    _, _CONFIG_LOADED, APP_FLASH_ADDR, APP_MAX_SIZE, AVAILABLE_LANGUAGES, BANNER_IMAGE_PATH,
    BITRATE_500K_SLCAN_CODE, BOOTLOADER_FLASH_ADDR, BOOTLOADER_MAX_SIZE, CONFIG_FILE_PATH, DEFAULT_LANGUAGE,
    EXPANSION_BOARD_TYPES, MLX_SENSOR_VARIANTS, FIRMWARE_FOLDER, FIRMWARE_VERSION_MAJOR, FIRMWARE_VERSION_MINOR,
    FLASHER_AUTHOR, FLASHER_VERSION,
    HYDRA_UMC_ICON_FRAMES_DIR, ICON_IMAGE_PATH, LOGS_FOLDER, PYOCD_TARGET_NAME, SLCAN_BITRATES,
    SLAVE_BOOTLOADER_FLASH_ADDR, SLAVE_APP_FLASH_ADDR, SLAVE_BOOTLOADER_MAX_SIZE,
    SLAVE_APP_MAX_SIZE, SLAVE_PYOCD_TARGET_NAME, SLAVE_TOTAL_FLASH_SIZE,
    STATUS_NAMES, THIS_HARDWARE_ID, TOOL_NAMES, CAN_ID_SET_FREE_TOOL, CAN_ID_FREE_TOOL_CONFIG_RESP,
    CAN_ID_SET_DEVICE_SERIAL, CAN_ID_PERIPHERAL_INFO_RESP,
    CAN_ID_SET_EXPANSION_TYPE, CAN_ID_EXPANSION_TYPE_RESP,
    CAN_ID_SET_MLX_VARIANT, CAN_ID_MLX_VARIANT_RESP,
    CAN_ID_QUERY_ERROR_COUNTERS, CAN_ID_ERROR_COUNTERS_RESPONSE,
    _center_geometry, _load_config_overrides, save_config,
)
from flasher_transports import SLCAN, SLCANError, SocketCAN, list_socketcan_interfaces
from flasher_protocol import URTCFlasher, FlashError
from flasher_github import list_firmware_files, download_file, GitHubDownloadError
from flasher_swd_tools import SWDFlashError, PyOCDCLI, CubeProgrammerCLI
from flasher_validation import validate_firmware_file, validate_swd_image_file
from hydra_umc_animation import AnimatedHydraUMCMark
from hydra_umc_deck_widgets import RoundedDeckButton, RoundedDeckCard

try:
    import serial
    import serial.tools.list_ports
    HAVE_SERIAL = True
except ImportError:
    HAVE_SERIAL = False

import socket
HAVE_SOCKETCAN = hasattr(socket, "AF_CAN")

# =============================================================================
# GUI
# =============================================================================
class FlasherGUI:
    # Command-deck palette shared by the fixed connection card, operation
    # pages and status surfaces.  The tooling remains intentionally Tkinter
    # based; this is a visual layer over the proven flashing workflow, not a
    # replacement for it with a non-functional mock-up.
    BG = "#07131B"
    PANEL = "#0C1A24"
    PANEL_ALT = "#102431"
    BORDER = "#1B4051"
    ACCENT = "#23C9E8"
    TEXT = "#E8F4F8"
    MUTED = "#91A9B5"
    SUCCESS = "#65DE91"
    WARNING = "#F7B955"
    DANGER = "#FF6B78"

    def _configure_command_deck_theme(self):
        """Apply the common dark control-deck surface before any widgets exist."""
        self.root.configure(bg=self.BG)
        style = ttk.Style(self.root)
        # clam honours colours consistently on Windows and Linux, unlike the
        # platform-native themes which silently discard several background
        # settings and leave white fields inside an otherwise dark interface.
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", background=self.PANEL, foreground=self.TEXT, font=("Segoe UI", 10))
        style.configure("TFrame", background=self.PANEL)
        style.configure("TLabel", background=self.PANEL, foreground=self.TEXT)
        style.configure(
            "TLabelframe", background=self.PANEL, foreground=self.ACCENT,
            bordercolor=self.BORDER, lightcolor=self.BORDER, darkcolor=self.BORDER,
            borderwidth=1, relief="solid",
        )
        style.configure(
            "TLabelframe.Label", background=self.PANEL, foreground=self.ACCENT,
            font=("Segoe UI Semibold", 11),
        )
        style.configure(
            "TButton", background=self.PANEL_ALT, foreground=self.TEXT,
            bordercolor=self.BORDER, lightcolor=self.BORDER, darkcolor=self.BORDER,
            padding=(12, 7), font=("Segoe UI Semibold", 10),
        )
        style.map(
            "TButton", background=[("active", "#173544"), ("pressed", "#0A6579")],
            foreground=[("disabled", "#5D7480")], bordercolor=[("active", self.ACCENT)],
        )
        style.configure(
            "Accent.TButton", background="#0B7187", foreground="#F3FDFF",
            bordercolor=self.ACCENT, padding=(13, 7), font=("Segoe UI Semibold", 10),
        )
        style.map("Accent.TButton", background=[("active", "#109DB9"), ("pressed", "#07566A")])
        style.configure(
            "TEntry", fieldbackground="#09151D", foreground=self.TEXT,
            insertcolor=self.ACCENT, bordercolor=self.BORDER, padding=6,
        )
        style.configure(
            "TCombobox", fieldbackground="#09151D", background=self.PANEL_ALT,
            foreground=self.TEXT, arrowcolor=self.ACCENT, bordercolor=self.BORDER,
            padding=5,
        )
        style.map("TCombobox", fieldbackground=[("readonly", "#09151D")], foreground=[("readonly", self.TEXT)])
        style.configure("TCheckbutton", background=self.PANEL, foreground=self.TEXT)
        style.configure("TRadiobutton", background=self.PANEL, foreground=self.TEXT)
        style.configure("TNotebook", background=self.BG, borderwidth=0, tabmargins=(0, 0, 0, 0))
        style.configure(
            "TNotebook.Tab", background="#0A1821", foreground=self.MUTED,
            bordercolor=self.BORDER, padding=(16, 9), font=("Segoe UI Semibold", 10),
        )
        style.map("TNotebook.Tab", background=[("selected", self.PANEL_ALT), ("active", "#132D3A")], foreground=[("selected", self.ACCENT), ("active", self.TEXT)])
        style.configure(
            "Treeview", background="#09151D", fieldbackground="#09151D",
            foreground=self.TEXT, bordercolor=self.BORDER, rowheight=28,
        )
        style.map("Treeview", background=[("selected", "#155269")], foreground=[("selected", "#FFFFFF")])
        style.configure(
            "Treeview.Heading", background="#122A36", foreground=self.ACCENT,
            bordercolor=self.BORDER, relief="flat", font=("Segoe UI Semibold", 9), padding=(8, 7),
        )
        style.map("Treeview.Heading", background=[("active", "#173A49")])
        style.configure(
            "Horizontal.TProgressbar", troughcolor="#071018", background=self.ACCENT,
            bordercolor=self.BORDER, lightcolor=self.ACCENT, darkcolor=self.ACCENT,
        )
        style.configure("TScrollbar", background=self.PANEL_ALT, troughcolor="#071018", bordercolor=self.BORDER, arrowcolor=self.ACCENT)

    def _build_command_deck_header(self):
        """Add a compact application identity/status deck above all real controls."""
        header = tk.Frame(self.root, bg=self.BG, height=76, highlightthickness=0)
        header.grid(row=0, column=0, sticky="ew", padx=8, pady=(7, 4))
        header.grid_propagate(False)
        header.grid_columnconfigure(1, weight=1)
        tk.Frame(header, bg=self.ACCENT, width=4).grid(row=0, column=0, sticky="ns", padx=(0, 13))
        title_block = tk.Frame(header, bg=self.BG)
        title_block.grid(row=0, column=1, sticky="w")
        tk.Label(title_block, text="URTC", bg=self.BG, fg=self.ACCENT, font=("Segoe UI Semibold", 12)).pack(anchor="w")
        tk.Label(title_block, text="Flasher", bg=self.BG, fg=self.TEXT, font=("Segoe UI", 20, "bold")).pack(anchor="w")
        tk.Label(title_block, text="CAN-OTA  •  SWD/JTAG  •  FIRMWARE CONTROL DECK", bg=self.BG, fg=self.MUTED, font=("Segoe UI Semibold", 8)).pack(anchor="w", pady=(1, 0))
        state = tk.Frame(header, bg="#0B202A", highlightbackground=self.BORDER, highlightthickness=1)
        state.grid(row=0, column=2, sticky="e", padx=(12, 0))
        tk.Label(state, text="●  HARDWARE SAFE", bg="#0B202A", fg=self.SUCCESS, font=("Segoe UI Semibold", 9)).pack(padx=12, pady=(8, 1))
        tk.Label(state, text=f"APP v{FLASHER_VERSION}", bg="#0B202A", fg=self.MUTED, font=("Segoe UI", 8)).pack(padx=12, pady=(0, 8))

    def _new_deck_card(self, parent, title):
        """Create an Updater-style 16px surface without changing flash logic."""
        return RoundedDeckCard(
            parent, title, canvas_color=self.BG, panel_color=self.PANEL,
            border_color=self.BORDER, accent_color=self.ACCENT,
            text_color=self.TEXT,
        )

    def _new_deck_button(self, parent, text, command, *, accent=False, state="normal"):
        """Create an Updater-style action while preserving Button semantics."""
        return RoundedDeckButton(
            parent, text=text, command=command, panel_color=self.PANEL_ALT,
            border_color=self.BORDER, text_color=self.TEXT, muted_color=self.MUTED,
            accent_color=self.ACCENT, accent=accent, state=state,
        )

    @staticmethod
    def _make_scrollable_tab(notebook, tab_text):
        """Adds a new notebook tab whose content sits inside a vertically
        scrollable canvas, and returns the inner Frame to build that tab's
        real content into - a drop-in replacement for
        ttk.Frame(notebook, padding=8) at the call site, so nothing below
        this needs to know its parent is a canvas rather than the notebook
        directly."""
        outer = ttk.Frame(notebook)
        canvas = tk.Canvas(outer, highlightthickness=0, background=FlasherGUI.PANEL, borderwidth=0)
        vscroll = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vscroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        vscroll.pack(side="right", fill="y")

        inner = ttk.Frame(canvas, padding=8)
        inner_window = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        # Match the embedded frame's width to the canvas's own visible
        # width (never its content's natural width) - only the height
        # should ever come from content and trigger scrolling; the width
        # tracking here is what keeps every control left-aligned and
        # wrapped text using the full available width instead of the
        # canvas's own tiny default request.
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(inner_window, width=e.width))

        # Mousewheel only scrolls this canvas while the pointer is actually
        # over it - bind_all() is unbound again on <Leave>, so it doesn't
        # keep intercepting the wheel once the pointer moves to the other
        # tab, a dialog, or anywhere else.
        def _on_wheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_wheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        notebook.add(outer, text=tab_text)
        return inner

    def __init__(self, root):
        self.root = root
        root.title(f"URTC Flasher v{FLASHER_VERSION}")
        self._configure_command_deck_theme()
        self._build_menu_bar()
        # Geometry (size + centered position) is set once in main(), before
        # this class is constructed - not here, so it isn't overwritten by
        # a second, uncentered geometry() call.
        root.resizable(True, True)

        # Persistent per-session log file (logs/urtc_flasher_YYYYMMDD_HHMMSS.log)
        # - purely additive to the on-screen log, so a technician can share
        # a session's full trace after the fact without having to copy text
        # out of the scrolling widget by hand. Failure to set this up
        # (read-only filesystem, etc.) is non-fatal - the on-screen log
        # still works exactly as before either way.
        self._file_logger = None
        try:
            os.makedirs(LOGS_FOLDER, exist_ok=True)
            log_path = os.path.join(
                LOGS_FOLDER, f"urtc_flasher_{time.strftime('%Y%m%d_%H%M%S')}.log"
            )
            self._file_logger = logging.getLogger(f"urtc_flasher_{id(self)}")
            self._file_logger.setLevel(logging.INFO)
            handler = logging.FileHandler(log_path, encoding="utf-8")
            handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
            self._file_logger.addHandler(handler)
            self._file_logger.info(f"=== URTC Flasher v{FLASHER_VERSION} session started ===")
        except OSError:
            self._file_logger = None

        # App icon - a small, bold design (a bright ring + a single accent
        # dot) deliberately simpler than the full banner artwork, which
        # doesn't hold up at 16-32px the way it does at banner size.
        # iconphoto (not iconbitmap) since it works identically on both
        # Windows and Linux from a plain PNG - iconbitmap's own .ico
        # support is Windows-only. Silently skipped if missing, same
        # reasoning as the banner elsewhere in this file: cosmetic, never worth a crash.
        try:
            self._icon_img = tk.PhotoImage(file=ICON_IMAGE_PATH)
            root.iconphoto(True, self._icon_img)
        except (tk.TclError, OSError):
            pass

        self.transport = None
        self.firmware_path = None
        self._detected_paths = {}
        self._stop_requested = False
        self._flash_thread = None
        self._swd_flash_thread = None

        pad = {"padx": 8, "pady": 4}

        # --- Connect (fixed at the top, outside the tabs below - connection
        # state matters regardless of which programming mode - CAN-OTA or
        # SWD/JTAG - is currently selected, so it doesn't get hidden behind
        # a tab switch the way the rest of the controls do) ---
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(2, weight=1)  # notebook row
        root.grid_rowconfigure(4, weight=1)  # log row - the one that should actually grow
        self._build_command_deck_header()
        conn_card = self._new_deck_card(root, _("TAB_CONNECT_TITLE"))
        conn_card.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)
        conn_frame = conn_card.content

        # Tkinter cannot play the animated SVG directly.  This deliberately
        # small mark plays twelve pre-rendered frames derived from the
        # official HYDRA-UMC SVG, while the native window/taskbar icon keeps
        # the URTC-specific static asset appropriate for 16-32px surfaces.
        self._hydra_umc_mark = None
        try:
            self._hydra_umc_mark = AnimatedHydraUMCMark(
                conn_frame, HYDRA_UMC_ICON_FRAMES_DIR
            )
            self._hydra_umc_mark.widget.grid(
                row=0, column=5, rowspan=3, sticky="ne", padx=(8, 10), pady=(2, 2)
            )
        except (OSError, tk.TclError):
            # Branding is cosmetic. Missing/corrupt generated frames must
            # never prevent a technician from flashing a board.
            self._hydra_umc_mark = None

        row = 0
        # Transport choice only appears at all when SocketCAN is actually
        # available (Linux, socket.AF_CAN present) - on Windows/macOS this
        # whole row is skipped and the UI looks exactly like the
        # Serial/SLCAN-only original, unchanged.
        self.transport_var = tk.StringVar(value="serial" if HAVE_SERIAL else "socketcan")
        if HAVE_SOCKETCAN:
            ttk.Label(conn_frame, text=_("LBL_TRANSPORT")).grid(row=row, column=0, sticky="w", **pad)
            transport_sub = ttk.Frame(conn_frame)
            transport_sub.grid(row=row, column=1, columnspan=3, sticky="w")
            self.transport_radio_serial = ttk.Radiobutton(
                transport_sub, text=_("RADIO_SERIAL_SLCAN"), value="serial",
                variable=self.transport_var, command=self.on_transport_change,
                state="normal" if HAVE_SERIAL else "disabled",
            )
            self.transport_radio_serial.pack(side="left", padx=(4, 12))
            self.transport_radio_socketcan = ttk.Radiobutton(
                transport_sub, text=_("RADIO_SOCKETCAN_NATIVE"), value="socketcan",
                variable=self.transport_var, command=self.on_transport_change,
            )
            self.transport_radio_socketcan.pack(side="left")
            row += 1

        self.port_label = ttk.Label(conn_frame, text=_("LBL_COM_PORT") if self.transport_var.get() == "serial" else "CAN interface:")
        self.port_label.grid(row=row, column=0, sticky="w", **pad)
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(conn_frame, textvariable=self.port_var, width=20, state="readonly")
        self.port_combo.grid(row=row, column=1, **pad)
        ttk.Button(conn_frame, text=_("BTN_REFRESH"), command=self.refresh_ports).grid(row=row, column=2, **pad)
        self.connect_btn = self._new_deck_button(
            conn_frame, _("BTN_CONNECT"), self.toggle_connect, accent=True
        )
        self.connect_btn.grid(row=row, column=3, **pad)
        self.conn_status = ttk.Label(conn_frame, text=_("STATUS_NOT_CONNECTED"), foreground="red")
        self.conn_status.grid(row=row, column=4, **pad)
        row += 1

        # Bitrate selector (Serial/SLCAN only - SocketCAN's bitrate is set
        # at the OS/interface level, not by this application, so there's
        # nothing for auto-detect to try there). URTC's own bus is fixed at
        # 500k, so that stays the default - this is for a misconfigured
        # adapter, or a non-standard board, not something normal use needs
        # to touch.
        self.bitrate_label = ttk.Label(conn_frame, text=_("LBL_BITRATE"))
        self.bitrate_label.grid(row=row, column=0, sticky="w", **pad)
        self.bitrate_var = tk.StringVar(value="500 kbit/s")
        self.bitrate_combo = ttk.Combobox(
            conn_frame, textvariable=self.bitrate_var, width=20, state="readonly",
            values=[label for label, _ in SLCAN_BITRATES],
        )
        self.bitrate_combo.grid(row=row, column=1, **pad)
        self.autobaud_btn = ttk.Button(conn_frame, text=_("BTN_AUTO_DETECT"), command=self.auto_detect_bitrate)
        self.autobaud_btn.grid(row=row, column=2, **pad)
        self.bitrate_status = ttk.Label(conn_frame, text="", foreground="gray")
        self.bitrate_status.grid(row=row, column=3, columnspan=2, sticky="w", **pad)
        if self.transport_var.get() != "serial":
            self.bitrate_combo.config(state="disabled")
            self.autobaud_btn.config(state="disabled")
        row += 1

        ttk.Label(conn_frame, text=_("LBL_CURRENTLY_INSTALLED")).grid(row=row, column=0, sticky="w", **pad)
        self.current_version_label = ttk.Label(conn_frame, text=_("STATUS_CONNECT_TO_CHECK"), foreground="gray")
        self.current_version_label.grid(row=row, column=1, columnspan=3, sticky="w", **pad)
        self.query_btn = ttk.Button(conn_frame, text=_("BTN_QUERY"), command=self.query_current_version)
        self.query_btn.grid(row=row, column=4, **pad)
        self.query_btn_holder = [self.query_btn]
        row += 1

        ttk.Label(conn_frame, text=_("LBL_BUS_ACTIVITY")).grid(row=row, column=0, sticky="w", **pad)
        self.bus_activity_label = ttk.Label(conn_frame, text=_("STATUS_CHECK_REQUIRES_CONNECTION"), foreground="gray")
        self.bus_activity_label.grid(row=row, column=1, columnspan=3, sticky="w", **pad)
        self.bus_activity_btn = ttk.Button(conn_frame, text=_("BTN_CHECK_2S"), command=self.check_bus_activity)
        self.bus_activity_btn.grid(row=row, column=4, **pad)
        self.query_btn_holder.append(self.bus_activity_btn)  # locked by _set_ui_busy_state the same way Query is
        row += 1

        ttk.Label(conn_frame, text=_("LBL_ERROR_COUNTERS")).grid(row=row, column=0, sticky="w", **pad)
        self.error_counters_label = ttk.Label(conn_frame, text=_("STATUS_CHECK_REQUIRES_CONNECTION"), foreground="gray")
        self.error_counters_label.grid(row=row, column=1, columnspan=3, sticky="w", **pad)
        self.error_counters_btn = ttk.Button(conn_frame, text=_("BTN_QUERY"), command=self.query_error_counters)
        self.error_counters_btn.grid(row=row, column=4, **pad)
        self.query_btn_holder.append(self.error_counters_btn)  # locked by _set_ui_busy_state the same way Query is
        row += 1

        ttk.Label(conn_frame, text=_("LBL_EXPANSION_BOARD")).grid(row=row, column=0, sticky="w", **pad)
        self.expansion_type_var = tk.StringVar(value=EXPANSION_BOARD_TYPES[0])
        self.expansion_type_combo = ttk.Combobox(
            conn_frame, textvariable=self.expansion_type_var, values=EXPANSION_BOARD_TYPES,
            state="readonly", width=32,
        )
        self.expansion_type_combo.grid(row=row, column=1, columnspan=3, sticky="w", **pad)
        exp_btn_row = ttk.Frame(conn_frame)
        exp_btn_row.grid(row=row, column=4, **pad)
        self.expansion_type_query_btn = ttk.Button(exp_btn_row, text=_("BTN_QUERY"), command=self.query_expansion_board_type)
        self.expansion_type_query_btn.pack(side="left")
        self.expansion_type_save_btn = ttk.Button(exp_btn_row, text=_("BTN_SAVE"), command=self.save_expansion_board_type)
        self.expansion_type_save_btn.pack(side="left", padx=(4, 0))
        self.query_btn_holder.append(self.expansion_type_combo)
        # Both buttons send their own CAN frames (0x1A0 query, 0x1A0 write)
        # over the same shared transport an active flash thread may still
        # be using - only the combo was being locked here before, leaving
        # these two clickable mid-flash despite the exact same
        # concurrent-port-access hazard already called out for the other
        # buttons in this list (free tool config, peripheral info, device
        # serial).
        self.query_btn_holder.append(self.expansion_type_query_btn)
        self.query_btn_holder.append(self.expansion_type_save_btn)
        row += 1

        # Only meaningful when expansion_board_type is 3, 4, or 6 - see
        # this control's own query/save handlers for the same reasoning
        # already established for expansion_board_type above. Shown
        # unconditionally rather than hidden/shown dynamically based on
        # the expansion board dropdown's own current value, since the
        # person may not have queried that value yet when this window
        # first opens - a control that appears and disappears based on
        # another control's own not-yet-known state would be more
        # confusing than one that's simply always visible.
        ttk.Label(conn_frame, text=_("LBL_MLX_SENSOR_VARIANT")).grid(row=row, column=0, sticky="w", **pad)
        self.mlx_variant_var = tk.StringVar(value=MLX_SENSOR_VARIANTS[0])
        self.mlx_variant_combo = ttk.Combobox(
            conn_frame, textvariable=self.mlx_variant_var, values=MLX_SENSOR_VARIANTS,
            state="readonly", width=32,
        )
        self.mlx_variant_combo.grid(row=row, column=1, columnspan=3, sticky="w", **pad)
        mlx_btn_row = ttk.Frame(conn_frame)
        mlx_btn_row.grid(row=row, column=4, **pad)
        self.mlx_variant_query_btn = ttk.Button(mlx_btn_row, text=_("BTN_QUERY"), command=self.query_mlx_sensor_variant)
        self.mlx_variant_query_btn.pack(side="left")
        self.mlx_variant_save_btn = ttk.Button(mlx_btn_row, text=_("BTN_SAVE"), command=self.save_mlx_sensor_variant)
        self.mlx_variant_save_btn.pack(side="left", padx=(4, 0))
        self.query_btn_holder.append(self.mlx_variant_combo)
        # Same gap as expansion_type's own Query/Save buttons just above -
        # only the combo was locked here before, leaving these two able to
        # send 0x1A6 queries/writes over the same transport an active flash
        # thread may still be using.
        self.query_btn_holder.append(self.mlx_variant_query_btn)
        self.query_btn_holder.append(self.mlx_variant_save_btn)
        row += 1
        # --- Tabbed body: CAN-OTA and SWD/JTAG are two genuinely different
        # operating modes (an auto-recovering OTA update vs. a destructive
        # full-chip programming session) rarely used side by side in the
        # same session, so they map onto tabs rather than two permanently
        # visible columns - the window only needs to be wide enough to
        # show whichever single tab is open. ---
        notebook = ttk.Notebook(root)
        notebook.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 4))
        self._notebook = notebook
        # Each tab's content lives inside its own scrollable canvas rather
        # than a plain Frame. root's own fixed 1235x1040 initial geometry
        # (see urtc_flasher.py) is only a starting hint - Tk still expands
        # the actual window past it to fit whatever a tab's content
        # naturally needs, and CAN-OTA Programming's own control count grew
        # past that budget, pushing the window taller than a 1080p screen
        # and hiding the log frame below the taskbar entirely with no way
        # to reach it. A plain Canvas (unlike a Frame) doesn't propagate
        # its embedded content's size to its parent - it only ever claims
        # whatever space the notebook's own row actually has - so wrapping
        # each tab this way caps the window at a sane height for good,
        # trading "everything always visible without scrolling" (impossible
        # once a tab's own content genuinely doesn't fit) for "the log
        # frame is always reachable regardless of which tab is open".
        canota_tab = self._make_scrollable_tab(notebook, _("TAB_CAN_OTA"))
        swdjtag_tab = self._make_scrollable_tab(notebook, _("TAB_SWD_JTAG"))

        # 2 columns rather than everything stacked in one - halves the
        # tab's vertical height for the same content, since the left
        # column (core flashing: pick a file, flash it) and the right
        # column (device configuration: free tool selection, peripheral
        # info) are independent enough to sit side by side rather than
        # needing to read top-to-bottom as one continuous flow.
        canota_tab.grid_columnconfigure(0, weight=1)
        canota_tab.grid_columnconfigure(1, weight=1)

        # --- Firmware frame (left column, top) ---
        fw_card = self._new_deck_card(canota_tab, _("TITLE_SELECT_FIRMWARE"))
        fw_card.grid(row=0, column=0, sticky="new", **pad)
        fw_frame = fw_card.content

        ttk.Label(fw_frame, text=_("LBL_DETECTED_IN_FIRMWARE")).grid(row=0, column=0, sticky="w", **pad)
        ttk.Button(fw_frame, text=_("BTN_REFRESH"), command=self.scan_firmware_folder).grid(row=0, column=1, sticky="w", **pad)

        columns = ("file", "size", "status")
        self.fw_tree = ttk.Treeview(fw_frame, columns=columns, show="headings", height=3, selectmode="browse")
        self.fw_tree.heading("file", text=_("COL_FILE"))
        self.fw_tree.heading("size", text=_("COL_SIZE"))
        self.fw_tree.heading("status", text=_("COL_STATUS"))
        # "file" gets the lion's share of the width and stretches with
        # the window - filenames here can run long (this project's own
        # "URTC_V1.1_F303CC.bin"-style naming, or whatever a future
        # GitHub download brings in), and this column was cramped at
        # its old 160px, forcing long names to truncate. size/status
        # stay fixed-width and non-stretching, since neither one's own
        # content grows with window width the way a filename might.
        self.fw_tree.column("file", width=320, stretch=True)
        self.fw_tree.column("size", width=70, anchor="e", stretch=False)
        self.fw_tree.column("status", width=170, stretch=False)
        self.fw_tree.grid(row=1, column=0, columnspan=3, sticky="ew", padx=8, pady=2)
        self.fw_tree.bind("<<TreeviewSelect>>", self.select_detected_firmware)
        self.fw_tree.tag_configure("invalid", foreground="red")
        self.fw_tree.tag_configure("valid", foreground=self.TEXT)

        ttk.Label(fw_frame, text=_("LBL_OR_BROWSE_ELSEWHERE")).grid(row=2, column=0, sticky="w", **pad)
        ttk.Button(fw_frame, text=_("BTN_BROWSE_BIN"), command=self.browse_firmware).grid(row=2, column=1, sticky="w", **pad)
        ttk.Button(fw_frame, text=_("BTN_DOWNLOAD_FROM_GITHUB"), command=self.open_github_download_dialog).grid(row=2, column=2, sticky="w", **pad)

        self.fw_label = ttk.Label(fw_frame, text=_("STATUS_NO_FILE_SELECTED"), foreground="gray", wraplength=350)
        self.fw_label.grid(row=3, column=0, columnspan=3, sticky="w", padx=8, pady=(0, 4))

        # --- Action frame (left column, bottom) - only the compact controls
        # (checkboxes/radios/button, none of which wrap) are paired 2-per-row;
        # every help label still spans the frame's FULL width. An earlier cut
        # of this also halved the help labels' own wraplength to fit a
        # sub-column, which backfired badly - a narrower label wraps onto
        # MORE lines, not fewer, so that version was taller than the
        # original single-column stack it was meant to shrink. Pairing just
        # the controls (which do save real rows) while leaving prose at full
        # width is the actual net height win.
        act_card = self._new_deck_card(canota_tab, _("TITLE_FLASH_BY_CAN_OTA"))
        act_card.grid(row=1, column=0, sticky="new", **pad)
        act_frame = act_card.content
        act_frame.grid_columnconfigure(0, weight=1)
        act_frame.grid_columnconfigure(1, weight=1)
        full_wrap = 380  # same wraplength the single-column layout used - help text always gets the frame's full width, never a half-column

        # Which chip this flash actually targets - the main board's own
        # STM32F303CC (direct CAN), or the expansion slave's own
        # STM32F303CBT6 (relayed through the main board's own I2C
        # bridge, CANBUS.TXT's own 0x210-0x218) - only meaningful, and
        # only actually reaches anything, when an Advanced expansion
        # board is populated (see EXPANSION.TXT). Defaults to the main
        # board, the far more common case.
        self.flash_target_var = tk.StringVar(value="master")
        target_row = ttk.Frame(act_frame)
        target_row.grid(row=0, column=0, columnspan=2, sticky="w", **pad)
        ttk.Label(target_row, text=_("LBL_FLASH_TARGET")).pack(side="left")
        ttk.Radiobutton(target_row, text=_("OPT_TARGET_MASTER"), value="master",
                         variable=self.flash_target_var, command=self._on_flash_target_change).pack(side="left", padx=(8, 0))
        ttk.Radiobutton(target_row, text=_("OPT_TARGET_SLAVE"), value="slave",
                         variable=self.flash_target_var, command=self._on_flash_target_change).pack(side="left", padx=(8, 0))
        ttk.Label(
            act_frame,
            text=_("HELP_FLASH_TARGET_SLAVE"),
            foreground="gray", wraplength=full_wrap, justify="left",
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 4))

        self.trigger_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            act_frame,
            text=_("CHK_BOARD_RUNNING_APP"),
            variable=self.trigger_var,
        ).grid(row=2, column=0, sticky="w", **pad)

        self.erase_fram_var = tk.BooleanVar(value=False)
        self.erase_fram_check = ttk.Checkbutton(
            act_frame,
            text=_("CHK_ERASE_FRAM_BEFORE_FLASHING"),
            variable=self.erase_fram_var,
        )
        self.erase_fram_check.grid(row=2, column=1, sticky="w", **pad)

        ttk.Label(
            act_frame,
            text=_("HELP_UNCHECK_IF_IN_BOOTLOADER"),
            foreground="gray", wraplength=full_wrap, justify="left",
        ).grid(row=3, column=0, columnspan=2, sticky="w", padx=8)
        ttk.Label(
            act_frame,
            text=_("HELP_ERASE_FRAM_OPTIONAL"),
            foreground="gray", wraplength=full_wrap, justify="left",
        ).grid(row=4, column=0, columnspan=2, sticky="w", padx=8)

        # 0x7FD - bypasses the bootloader's own anti-rollback check for
        # this one attempt (Target: main board only; the expansion slave's
        # own bootloader doesn't implement this yet). Off by default and
        # asked to confirm again in start_flash() below, same "opt in
        # twice for something deliberately dangerous" pattern the SWD
        # section's own dry-run/option-bytes checks already use.
        self.allow_downgrade_var = tk.BooleanVar(value=False)
        self.allow_downgrade_check = ttk.Checkbutton(
            act_frame,
            text=_("CHK_ALLOW_DOWNGRADE"),
            variable=self.allow_downgrade_var,
        )
        self.allow_downgrade_check.grid(row=5, column=0, sticky="w", **pad)

        # 0x7FE/0x7FF - reads the currently-installed firmware back over
        # CAN before you deliberately overwrite it. Main board only (same
        # reasoning as Allow downgrade above - the expansion slave's own
        # bootloader doesn't implement this yet), disabled the same way
        # for the slave target.
        self.readback_btn = ttk.Button(
            act_frame, text=_("BTN_BACKUP_FIRMWARE_CAN"), command=self.start_readback,
        )
        self.readback_btn.grid(row=5, column=1, sticky="w", **pad)

        ttk.Label(
            act_frame,
            text=_("HELP_ALLOW_DOWNGRADE"),
            foreground="#b35900", wraplength=full_wrap, justify="left",
        ).grid(row=6, column=0, columnspan=2, sticky="w", padx=8)
        ttk.Label(
            act_frame,
            text=_("HELP_BACKUP_FIRMWARE_CAN"),
            foreground="gray", wraplength=full_wrap, justify="left",
        ).grid(row=7, column=0, columnspan=2, sticky="w", padx=8)

        flash_btn_row = ttk.Frame(act_frame)
        flash_btn_row.grid(row=8, column=0, columnspan=2, sticky="w", **pad)
        self.flash_btn = self._new_deck_button(
            flash_btn_row, _("BTN_FLASH_FIRMWARE"), self.start_flash, accent=True
        )
        self.flash_btn.pack(side="left")
        self.cancel_btn = self._new_deck_button(
            flash_btn_row, _("BTN_CANCEL"), self.cancel_flash, state="disabled"
        )
        self.cancel_btn.pack(side="left", padx=(8, 0))

        # --- Free tool configuration (right column, top) - (0x1A2/0x1A3),
        # only consulted by a board whose ID jumpers read 11111 (0x1F,
        # all 5 installed); see EEPROM.TXT section 5 for the full
        # mechanism. This tool is the only one that writes it - the
        # Tester can read it back but doesn't offer a way to change it,
        # same asymmetry as the OTA update process itself. ---
        free_tool_card = self._new_deck_card(canota_tab, _("TITLE_FREE_TOOL_CONFIG"))
        free_tool_card.grid(row=0, column=1, sticky="new", **pad)
        free_tool_frame = free_tool_card.content
        ttk.Label(
            free_tool_frame,
            text=_("HELP_FREE_TOOL_CONFIG"),
            foreground="gray", wraplength=380, justify="left",
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=8, pady=(4, 4))
        self._free_tool_display_to_selection = {_("OPT_FREE_TOOL_NONE"): 0}
        for tool_id, name in TOOL_NAMES.items():
            self._free_tool_display_to_selection[f"{tool_id + 1} - {name}"] = tool_id + 1
        self.free_tool_var = tk.StringVar(value=_("OPT_FREE_TOOL_NONE"))
        ttk.Combobox(
            free_tool_frame, textvariable=self.free_tool_var, state="readonly", width=22,
            values=list(self._free_tool_display_to_selection.keys()),
        ).grid(row=1, column=0, sticky="w", **pad)
        self.free_tool_program_btn = ttk.Button(
            free_tool_frame, text=_("BTN_PROGRAM"), command=self.program_free_tool_config)
        self.free_tool_program_btn.grid(row=1, column=1, **pad)
        self.query_btn_holder.append(self.free_tool_program_btn)  # locked by _set_ui_busy_state the same way Query is - writes 0x1A2 over the same serial/CAN link an active flash is using, same concurrent-port-access hazard as the buttons already in this list
        self.free_tool_result_var = tk.StringVar(value="")
        ttk.Label(free_tool_frame, textvariable=self.free_tool_result_var, wraplength=380, justify="left").grid(
            row=2, column=0, columnspan=3, sticky="w", padx=8, pady=(0, 4))

        # --- Peripheral type + device serial number (right column,
        # bottom) - (0x1A4/0x1A5), see EEPROM.TXT section 6. Exists so
        # multiple otherwise-identical URTC boards on the same CAN bus
        # can be told apart. Peripheral type is a fixed firmware
        # constant (always 0x03/URTC) - shown after a query, never
        # editable. Serial number is the one real writable value here,
        # same asymmetry as free tool configuration above: this tool
        # writes it, the Tester can only read it back. ---
        peripheral_card = self._new_deck_card(canota_tab, _("TITLE_PERIPHERAL_INFO"))
        peripheral_card.grid(row=1, column=1, sticky="new", **pad)
        peripheral_frame = peripheral_card.content
        ttk.Label(
            peripheral_frame,
            text=_("HELP_PERIPHERAL_INFO"),
            foreground="gray", wraplength=380, justify="left",
        ).grid(row=0, column=0, columnspan=4, sticky="w", padx=8, pady=(4, 4))
        self.peripheral_query_btn = ttk.Button(
            peripheral_frame, text=_("BTN_QUERY"), command=self.query_peripheral_info)
        self.peripheral_query_btn.grid(row=1, column=0, **pad)
        self.query_btn_holder.append(self.peripheral_query_btn)  # locked by _set_ui_busy_state the same way Query is - queries 0x1A5 over the same serial/CAN link an active flash is using, same concurrent-port-access hazard as the buttons already in this list
        ttk.Label(peripheral_frame, text=_("LBL_NEW_SERIAL")).grid(row=1, column=1, sticky="e", **pad)
        self.device_serial_var = tk.StringVar(value="0")
        ttk.Spinbox(
            peripheral_frame, textvariable=self.device_serial_var, from_=0, to=255, width=6,
        ).grid(row=1, column=2, sticky="w", **pad)
        self.device_serial_program_btn = ttk.Button(
            peripheral_frame, text=_("BTN_PROGRAM"), command=self.program_device_serial)
        self.device_serial_program_btn.grid(row=1, column=3, **pad)
        self.query_btn_holder.append(self.device_serial_program_btn)  # locked by _set_ui_busy_state the same way Query is - writes 0x1A4 over the same serial/CAN link an active flash is using, same concurrent-port-access hazard as the buttons already in this list
        self.peripheral_info_result_var = tk.StringVar(value="")
        ttk.Label(peripheral_frame, textvariable=self.peripheral_info_result_var, wraplength=380, justify="left").grid(
            row=2, column=0, columnspan=4, sticky="w", padx=8, pady=(0, 4))

        # --- SWD/JTAG full-chip programming frame (advanced, separate risk profile) ---
        swd_card = self._new_deck_card(swdjtag_tab, _("TITLE_PROGRAM_COMPLETE_CHIP"))
        swd_card.pack(fill="both", expand=True, **pad)
        swd_frame = swd_card.content

        # Which chip a probe is actually connected to - genuinely
        # different silicon (STM32F303CC vs STM32F303CB), different
        # flash addresses/sizes, and a different PyOCD target string.
        # SWD/JTAG needs its own physical probe wired to whichever chip
        # this is set to - unlike CAN-OTA, there's no bridge that lets
        # one connection reach both chips here.
        self.swd_target_var = tk.StringVar(value="master")
        swd_target_row = ttk.Frame(swd_frame)
        swd_target_row.grid(row=0, column=0, columnspan=3, sticky="w", **pad)
        ttk.Label(swd_target_row, text=_("LBL_SWD_TARGET")).pack(side="left")
        ttk.Radiobutton(swd_target_row, text=_("OPT_TARGET_MASTER"), value="master",
                         variable=self.swd_target_var).pack(side="left", padx=(8, 0))
        ttk.Radiobutton(swd_target_row, text=_("OPT_TARGET_SLAVE"), value="slave",
                         variable=self.swd_target_var).pack(side="left", padx=(8, 0))
        ttk.Label(
            swd_frame,
            text=_("HELP_SWD_TARGET_SLAVE"),
            foreground="gray", wraplength=680, justify="left",
        ).grid(row=1, column=0, columnspan=3, sticky="w", padx=8, pady=(0, 4))

        self._pyocd_ok = PyOCDCLI.available()
        self._cube_ok = CubeProgrammerCLI.available()
        self.swd_tool_var = tk.StringVar(value="pyocd" if self._pyocd_ok else "cube")
        tool_sub = ttk.Frame(swd_frame)
        tool_sub.grid(row=2, column=0, columnspan=3, sticky="w", **pad)
        ttk.Radiobutton(
            tool_sub, text=_("RADIO_PYOCD_BUILTIN") + ("" if self._pyocd_ok else " - not found"),
            value="pyocd", variable=self.swd_tool_var, state="normal" if self._pyocd_ok else "disabled",
            command=self.refresh_swd_probes,
        ).pack(side="top", anchor="w")
        ttk.Radiobutton(
            tool_sub, text=_("RADIO_STM32CUBEPROGRAMMER") + ("" if self._cube_ok else " - not found"),
            value="cube", variable=self.swd_tool_var, state="normal" if self._cube_ok else "disabled",
            command=self.refresh_swd_probes,
        ).pack(side="top", anchor="w")

        probe_sub = ttk.Frame(tool_sub)
        probe_sub.pack(side="top", anchor="w", pady=(4, 0))
        ttk.Label(probe_sub, text=_("LBL_PROBE")).pack(side="left")
        self.swd_probe_var = tk.StringVar(value="")
        self.swd_probe_combo = ttk.Combobox(probe_sub, textvariable=self.swd_probe_var, width=20, state="readonly")
        self.swd_probe_combo.pack(side="left", padx=(4, 4))
        self.swd_probe_refresh_btn = ttk.Button(probe_sub, text=_("BTN_REFRESH"), command=self.refresh_swd_probes)
        self.swd_probe_refresh_btn.pack(side="left")
        # uid -> description, for turning the combobox's shown text back
        # into the actual --probe/sn value to pass to the subprocess
        self._swd_probe_map = {}

        if not self._pyocd_ok and not self._cube_ok:
            ttk.Label(
                swd_frame,
                text=_("HELP_NEITHER_TOOL_FOUND"),
                foreground="red", wraplength=680, justify="left",
            ).grid(row=3, column=0, columnspan=3, sticky="w", padx=8)

        ttk.Label(swd_frame, text=_("LBL_BOOTLOADER_FILE")).grid(row=4, column=0, sticky="w", **pad)
        self.swd_bootloader_var = tk.StringVar()
        ttk.Entry(swd_frame, textvariable=self.swd_bootloader_var, width=20).grid(row=4, column=1, sticky="ew", **pad)
        ttk.Button(swd_frame, text=_("BTN_BROWSE"), command=self.browse_swd_bootloader).grid(row=4, column=2, **pad)

        ttk.Label(swd_frame, text=_("LBL_APPLICATION_FILE")).grid(row=5, column=0, sticky="w", **pad)
        self.swd_app_var = tk.StringVar()
        ttk.Entry(swd_frame, textvariable=self.swd_app_var, width=20).grid(row=5, column=1, sticky="ew", **pad)
        ttk.Button(swd_frame, text=_("BTN_BROWSE"), command=self.browse_swd_app).grid(row=5, column=2, **pad)

        self.swd_dry_run_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            swd_frame,
            text=_("CHK_DRY_RUN"),
            variable=self.swd_dry_run_var,
        ).grid(row=6, column=0, columnspan=3, sticky="w", padx=8)

        self.swd_backup_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            swd_frame,
            text=_("CHK_BACKUP_BEFORE_ERASING"),
            variable=self.swd_backup_var,
        ).grid(row=7, column=0, columnspan=3, sticky="w", padx=8)

        self.check_ob_btn = ttk.Button(
            swd_frame, text=_("BTN_CHECK_OPTION_BYTES"), command=self.start_check_option_bytes,
            state="normal" if self._cube_ok else "disabled",
        )
        self.check_ob_btn.grid(row=8, column=0, columnspan=3, sticky="w", **pad)
        ttk.Label(
            swd_frame,
            text=_("HELP_RDP_CHECK_READONLY")
                 + ("" if self._cube_ok else _("HELP_NEEDS_CUBEPROGRAMMER_SUFFIX")),
            foreground="gray", wraplength=680, justify="left",
        ).grid(row=9, column=0, columnspan=3, sticky="w", padx=8)

        self.swd_flash_btn = self._new_deck_button(
            swd_frame, _("BTN_FLASH_COMPLETE_CHIP"), self.start_swd_flash,
            accent=True, state="normal" if (self._pyocd_ok or self._cube_ok) else "disabled",
        )
        self.swd_flash_btn.grid(row=10, column=0, columnspan=3, sticky="w", **pad)
        ttk.Label(
            swd_frame,
            text=_("HELP_ERASES_WHOLE_CHIP"),
            foreground="#b35900", wraplength=680, justify="left",
        ).grid(row=9, column=0, columnspan=3, sticky="w", padx=8)

        self.progress = ttk.Progressbar(root, orient="horizontal", mode="determinate", maximum=100)
        self.progress.grid(row=3, column=0, sticky="ew", padx=12, pady=(4, 8))

        # --- Log frame ---
        log_card = self._new_deck_card(root, _("TITLE_LOG"))
        log_card.grid(row=4, column=0, sticky="nsew", padx=8, pady=(0, 8))
        log_frame = log_card.content
        log_toolbar = ttk.Frame(log_frame)
        log_toolbar.pack(fill="x", side="top")
        ttk.Button(log_toolbar, text=_("BTN_EXPORT_DEBUG_BUNDLE"), command=self.export_debug_bundle).pack(
            side="left", padx=4, pady=2
        )
        self.log_text = tk.Text(
            log_frame, height=5, state="disabled", wrap="word", bg="#071018",
            fg=self.TEXT, insertbackground=self.ACCENT, relief="flat", borderwidth=0,
            selectbackground="#155269", selectforeground="#FFFFFF", font=("Cascadia Mono", 9),
        )
        self.log_text.pack(fill="both", expand=True, side="left")
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=scrollbar.set)

        self.refresh_ports()
        self.scan_firmware_folder()
        self.log(_("LOG_FLASHER_READY", hw_id=THIS_HARDWARE_ID, major=FIRMWARE_VERSION_MAJOR, minor=FIRMWARE_VERSION_MINOR))
        if _CONFIG_LOADED:
            _load_config_overrides(self.log)  # re-run just to emit its own log line - values don't change
        if self.transport_var.get() == "serial":
            self.log(_("LOG_EXPECTING_SLCAN_MODE"))
        else:
            self.log(_("LOG_EXPECTING_SOCKETCAN_MODE"))

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        if self._pyocd_ok or self._cube_ok:
            self.refresh_swd_probes()

    def export_debug_bundle(self):
        save_path = filedialog.asksaveasfilename(
            title="Save Debug Bundle",
            defaultextension=".zip",
            initialfile=f"urtc_flasher_debug_{time.strftime('%Y%m%d_%H%M%S')}.zip",
            filetypes=[("ZIP archive", "*.zip")],
        )
        if not save_path:
            return
        try:
            with zipfile.ZipFile(save_path, "w", zipfile.ZIP_DEFLATED) as zf:
                # On-screen log, exactly as currently shown - not just the
                # file logger's copy, in case file logging failed to set up
                zf.writestr("session_log.txt", self.log_text.get("1.0", "end"))

                diag = [
                    f"URTC Flasher version: {FLASHER_VERSION}",
                    f"Python: {sys.version}",
                    f"Platform: {platform.platform()}",
                    f"pyserial available: {HAVE_SERIAL}",
                    f"SocketCAN available: {HAVE_SOCKETCAN}",
                    f"pyOCD found: {PyOCDCLI.available()}",
                    f"STM32CubeProgrammer found: {CubeProgrammerCLI.available()}",
                    f"Current transport: {self.transport_var.get()}",
                    f"Current port/interface: {self.port_var.get()}",
                    f"Current bitrate (Serial/SLCAN): {self.bitrate_var.get()}",
                    f"Connected: {self.transport is not None}",
                    f"Selected CAN firmware file: {self.firmware_path or '(none)'}",
                    f"Selected SWD bootloader file: {self.swd_bootloader_var.get() or '(none)'}",
                    f"Selected SWD application file: {self.swd_app_var.get() or '(none)'}",
                ]
                zf.writestr("system_diagnostics.txt", "\n".join(diag))

                # The firmware file itself, if one's selected and still
                # readable - the single most useful thing to have alongside
                # the log when diagnosing a failed flash after the fact.
                if self.firmware_path and os.path.isfile(self.firmware_path):
                    zf.write(self.firmware_path, "firmware/" + os.path.basename(self.firmware_path))

            messagebox.showinfo(_("TITLE_DEBUG_BUNDLE_SAVED"), _("MSG_SAVED_TO", path=save_path))
            self.log(_("LOG_DEBUG_BUNDLE_EXPORTED", path=save_path))
        except OSError as e:
            messagebox.showerror(_("TITLE_EXPORT_FAILED"), str(e))

    def _build_menu_bar(self):
        menu_style = {
            "background": self.PANEL_ALT, "foreground": self.TEXT,
            "activebackground": self.ACCENT, "activeforeground": "#03161D",
            "borderwidth": 0,
        }
        menubar = tk.Menu(self.root, **menu_style)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=False, **menu_style)
        file_menu.add_command(label=_("MENU_SAVE_LOGS"), command=self._menu_save_logs)
        file_menu.add_separator()
        file_menu.add_command(label=_("MENU_EXIT"), command=self.on_close)
        menubar.add_cascade(label=_("MENU_FILE"), menu=file_menu)

        # Radiobutton-style menu items so the current language shows a
        # checkmark - purely cosmetic (each one calls _on_language_change
        # with its own fixed code regardless of this variable's value),
        # but confirms at a glance which one is actually active without
        # opening a submenu of plain, unmarked entries.
        language_menu = tk.Menu(menubar, tearoff=False, **menu_style)
        self._menu_lang_var = tk.StringVar(value=flasher_config._current_language)
        for code, display in AVAILABLE_LANGUAGES:
            language_menu.add_radiobutton(
                label=display, value=code, variable=self._menu_lang_var,
                command=lambda c=code: self._on_language_change(c),
            )
        menubar.add_cascade(label=_("MENU_LANGUAGE"), menu=language_menu)

        help_menu = tk.Menu(menubar, tearoff=False, **menu_style)
        help_menu.add_command(label=_("MENU_README"), command=self._menu_show_readme)
        help_menu.add_command(label=_("MENU_GITHUB"), command=self._menu_show_github)
        help_menu.add_separator()
        help_menu.add_command(label=_("MENU_LICENSE"), command=self._menu_show_license)
        help_menu.add_command(label=_("MENU_ABOUT"), command=self._menu_show_about)
        menubar.add_cascade(label=_("MENU_HELP"), menu=help_menu)

    def _menu_save_logs(self):
        """Saves just the on-screen log as plain text - the lighter-weight
        counterpart to export_debug_bundle's full zip (log + diagnostics +
        firmware file), for when only the log itself is actually needed."""
        save_path = filedialog.asksaveasfilename(
            title=_("MENU_SAVE_LOGS"),
            defaultextension=".txt",
            initialfile=f"urtc_flasher_log_{time.strftime('%Y%m%d_%H%M%S')}.txt",
            filetypes=[(_("LBL_TEXT_FILES"), "*.txt")],
        )
        if not save_path:
            return
        try:
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(self.log_text.get("1.0", "end"))
            self.log(_("LOG_LOGS_SAVED", path=save_path))
        except OSError as e:
            messagebox.showerror(_("TITLE_EXPORT_FAILED"), str(e))

    def _menu_show_github(self):
        import webbrowser
        # This tool's own dedicated repository - deliberately not URTC's
        # own monorepo (github.com/JuanenRac/URTC), since this tool is
        # versioned, released, and issue-tracked independently from the
        # board firmware it flashes, even though the two work closely
        # together.
        webbrowser.open("https://github.com/JuanenRac/URTC-FLASHER")

    def _show_text_window(self, title, text, width=90, height=30):
        """Shared plain-text viewer window - used by both the Readme and
        License menu entries. Read-only Text widget with a scrollbar,
        rather than trying to render Markdown (no renderer is bundled, and
        adding one just for this would be a lot of weight for a "view the
        file" feature). Centered here, once, so every caller gets it for
        free rather than each one needing its own centering call."""
        win = tk.Toplevel(self.root)
        win.title(title)
        win.transient(self.root)
        frame = ttk.Frame(win, padding=8)
        frame.pack(fill="both", expand=True)
        text_widget = tk.Text(frame, wrap="word", width=width, height=height)
        text_widget.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(frame, command=text_widget.yview)
        scrollbar.pack(side="right", fill="y")
        text_widget.config(yscrollcommand=scrollbar.set)
        text_widget.insert("1.0", text)
        text_widget.config(state="disabled")
        win.update_idletasks()
        win.geometry(_center_geometry(win, win.winfo_reqwidth(), win.winfo_reqheight()))
        return win

    def _menu_show_readme(self):
        # Language-specific filename first (readme_spa.md etc.), falling
        # back to the English readme.md if that translation doesn't exist
        # yet - so this works today (everything falls back to English) and
        # picks up translated READMEs automatically once they're added,
        # with no code change needed here when that happens.
        lang_suffix = {"spanish": "_spa", "italian": "_ita", "french": "_fra", "german": "_deu"}.get(
            flasher_config._current_language, ""
        )
        # flasher_config.base_dir, not a fresh __file__-based calculation -
        # see that module's own comment on why: __file__ resolves into
        # PyInstaller's temporary extraction folder when this is running
        # as a frozen .exe, not to wherever the .exe actually sits on disk.
        candidate = os.path.join(flasher_config.base_dir, f"README{lang_suffix}.md")
        readme_path = candidate if os.path.isfile(candidate) else os.path.join(flasher_config.base_dir, "README.md")
        try:
            with open(readme_path, encoding="utf-8") as f:
                content = f.read()
        except OSError as e:
            messagebox.showerror(_("TITLE_EXPORT_FAILED"), str(e))
            return
        self._show_text_window(_("MENU_README"), content)

    def _menu_show_license(self):
        # Looks next to the executable/script (build_exe.bat/.sh both copy
        # LICENSE there - see those scripts), not via a "../../../" relative
        # path up to the repository root - that only ever resolved
        # correctly when running from within the source tree, never for a
        # standalone distributed exe with no repository around it at all.
        try:
            license_path = os.path.join(flasher_config.base_dir, "LICENSE")
            with open(license_path, encoding="utf-8") as f:
                content = f.read()
        except OSError:
            content = _("MSG_LICENSE_FALLBACK")
        win = self._show_text_window(_("MENU_LICENSE"), content, width=80, height=24)
        ttk.Button(win, text=_("BTN_ACCEPT"), command=win.destroy).pack(pady=(0, 8))

    def _menu_show_about(self):
        win = tk.Toplevel(self.root)
        win.title(_("MENU_ABOUT"))
        win.transient(self.root)
        win.resizable(False, False)
        try:
            banner_img = tk.PhotoImage(file=BANNER_IMAGE_PATH)
            banner_label = ttk.Label(win, image=banner_img)
            banner_label.image = banner_img  # keep a reference - PhotoImage is garbage-collected otherwise
            banner_label.pack(padx=8, pady=8)
        except tk.TclError:
            pass  # banner image missing/unreadable - still show the text below
        ttk.Label(
            win, text=f"URTC Flasher v{FLASHER_VERSION}\n{_('LBL_ABOUT_AUTHOR', author=FLASHER_AUTHOR)}",
            justify="center",
        ).pack(padx=8, pady=(0, 8))
        ttk.Button(win, text=_("BTN_ACCEPT"), command=win.destroy).pack(pady=(0, 8))
        win.update_idletasks()
        win.geometry(_center_geometry(win, win.winfo_reqwidth(), win.winfo_reqheight()))

    def on_close(self):
        # A confirmation here matters more than it might for an ordinary
        # window: a CAN OTA update interrupted mid-flash is still safe
        # (golden-image backup slot), but the board is left waiting on a
        # bootloader timeout rather than resuming normal operation right
        # away, and an SWD/JTAG full-chip flash has no such safety net at
        # all - both worth a deliberate choice rather than a silent kill.
        flashing = bool(
            (self._flash_thread and self._flash_thread.is_alive())
            or (self._swd_flash_thread and self._swd_flash_thread.is_alive())
        )
        if flashing:
            if not messagebox.askyesno(
                _("TITLE_FLASH_IN_PROGRESS"),
                _("MSG_FLASH_IN_PROGRESS_CLOSE_CONFIRM"),
            ):
                return
        if self.transport is not None:
            try:
                self.transport.close()
            except Exception:
                pass
        self.root.destroy()

    def log(self, msg):
        if self._file_logger:
            try:
                self._file_logger.info(msg)
            except OSError:
                pass  # disk full, permissions changed mid-session, etc. - on-screen log still works
        def _append():
            self.log_text.config(state="normal")
            self.log_text.insert("end", msg + "\n")
            self.log_text.see("end")
            self.log_text.config(state="disabled")
        self.root.after(0, _append)

    def on_transport_change(self):
        self.port_label.config(text=_("LBL_COM_PORT") if self.transport_var.get() == "serial" else "CAN interface:")
        self.port_var.set("")
        is_serial = self.transport_var.get() == "serial"
        self.bitrate_combo.config(state="readonly" if is_serial else "disabled")
        self.autobaud_btn.config(state="normal" if is_serial else "disabled")
        self.bitrate_status.config(text="" if is_serial else "SocketCAN's bitrate is set at the OS level (ip link), not here")
        self.refresh_ports()

    def refresh_ports(self):
        if self.transport_var.get() == "serial":
            ports = [p.device for p in serial.tools.list_ports.comports()] if HAVE_SERIAL else []
        else:
            ports = list_socketcan_interfaces()
            if not ports:
                self.log(_("LOG_NO_SOCKETCAN_INTERFACES"))
        self.port_combo["values"] = ports
        if ports and not self.port_var.get():
            self.port_var.set(ports[0])

    def toggle_connect(self):
        if self.transport is None:
            port = self.port_var.get()
            if not port:
                messagebox.showerror(_("TITLE_NOTHING_SELECTED"), _("MSG_SELECT_PORT_FIRST"))
                return
            is_serial = self.transport_var.get() == "serial"
            self.conn_status.config(text=_("STATUS_CONNECTING"), foreground="gray")
            self.connect_btn.config(state="disabled")
            threading.Thread(target=self._connect_worker, args=(port, is_serial), daemon=True).start()
        else:
            try:
                self.transport.close()
            except Exception:
                pass
            self.transport = None
            self.conn_status.config(text=_("STATUS_NOT_CONNECTED"), foreground="red")
            self.connect_btn.config(text=_("BTN_CONNECT"))
            self.current_version_label.config(text=_("STATUS_CONNECT_TO_CHECK"), foreground="gray")
            self.log(_("LOG_DISCONNECTED"))

    def _connect_worker(self, port, is_serial):
        try:
            if is_serial:
                bitrate_label = self.bitrate_var.get()
                bitrate_code = next((code for label, code in SLCAN_BITRATES if label == bitrate_label),
                                     BITRATE_500K_SLCAN_CODE)
                transport = SLCAN(port, log=self.log)
                transport.open_channel(bitrate_code)
            else:
                transport = SocketCAN(port, log=self.log)
                transport.open_channel()
            self.transport = transport
            self.root.after(0, lambda: self._on_connected(port, is_serial))
        except Exception as e:
            error_msg = str(e)  # captured now - 'e' itself is deleted the moment this except block exits, but the lambda below runs later, via root.after()
            self.root.after(0, lambda: self._on_connect_failed(error_msg, is_serial))

    def _on_connected(self, port, is_serial):
        self.conn_status.config(text=f"Connected ({port})", foreground="green")
        self.connect_btn.config(text=_("BTN_DISCONNECT"), state="normal")
        self.log(_("LOG_CONNECTED_TO_PORT", port=port)
                  + (_("LOG_AT_BITRATE_SUFFIX", bitrate=self.bitrate_var.get()) if is_serial else "."))
        self.query_current_version()

    def _on_connect_failed(self, msg, is_serial):
        self.transport = None
        self.conn_status.config(text=_("STATUS_NOT_CONNECTED"), foreground="red")
        self.connect_btn.config(state="normal")
        # A permission-denied serial error is the single most common
        # first-run snag on Linux (unlike Windows, opening a serial
        # device needs group membership there) - worth a specific,
        # actionable message instead of just surfacing pyserial's
        # raw exception text.
        if is_serial and ("Permission denied" in msg or "Errno 13" in msg):
            messagebox.showerror(
                _("TITLE_CONNECTION_FAILED_PERMISSION"),
                _("MSG_PERMISSION_DENIED_HELP", msg=msg),
            )
        else:
            messagebox.showerror(_("TITLE_CONNECTION_FAILED"), msg)

    def scan_firmware_folder(self):
        for item in self.fw_tree.get_children():
            self.fw_tree.delete(item)
        self._detected_paths = {}

        matches = []
        if os.path.isdir(FIRMWARE_FOLDER):
            all_bins = sorted(glob.glob(os.path.join(FIRMWARE_FOLDER, "*.bin")))
            # Bootloaders never belong in this list - CAN-OTA only ever
            # flashes application firmware (this board's own, or the
            # expansion slave's own, once that path exists - see
            # flash_slave_via_can_ota). A bootloader update needs
            # SWD/JTAG (the other tab), not this one.
            matches = [p for p in all_bins if "BOOTLOADER" not in os.path.basename(p).upper()]

        if not os.path.isdir(FIRMWARE_FOLDER):
            self.log(_("LOG_NO_FIRMWARE_FOLDER", folder=FIRMWARE_FOLDER))
            return
        if not matches:
            self.log(_("LOG_FIRMWARE_FOLDER_NO_BINS", folder=FIRMWARE_FOLDER))
            return

        # Validate against whichever slot the current CAN-OTA target
        # actually flashes into - a real URTC_SLAVE_APP.bin genuinely
        # links at SLAVE_APP_FLASH_ADDR (0x08005000), not this board's
        # own APP_FLASH_ADDR (0x08008000, see flasher_config.py), so
        # checking every file against the main board's address always
        # flagged a real slave image as invalid regardless of target.
        is_slave = self.flash_target_var.get() == "slave"
        fw_addr = SLAVE_APP_FLASH_ADDR if is_slave else APP_FLASH_ADDR
        fw_max = SLAVE_APP_MAX_SIZE if is_slave else APP_MAX_SIZE

        valid_entries = []
        for path in matches:
            name = os.path.basename(path)
            is_valid, reason, size = validate_firmware_file(path, fw_addr, fw_max)
            size_str = f"{size/1024:.1f} KB" if size else "-"
            status_str = "\u2713 " + reason if is_valid else "\u2717 " + reason
            tag = "valid" if is_valid else "invalid"
            item_id = self.fw_tree.insert("", "end", values=(name, size_str, status_str), tags=(tag,))
            self._detected_paths[item_id] = (path, is_valid)
            if is_valid:
                valid_entries.append((item_id, path, name))

        self.log(_("LOG_SCANNED_FIRMWARE", found=len(matches), valid=len(valid_entries)))
        for path in matches:
            name = os.path.basename(path)
            is_valid, reason, size = validate_firmware_file(path, fw_addr, fw_max)
            if not is_valid:
                self.log(_("LOG_FIRMWARE_ENTRY_INVALID", name=name, reason=reason))

        if len(valid_entries) == 1:
            # Exactly one VALID candidate - not just one file period. An
            # invalid file sitting alone in the folder should never get
            # auto-selected just because nothing else is competing with it.
            item_id, path, name = valid_entries[0]
            self.fw_tree.selection_set(item_id)
            self.firmware_path = path
            self.fw_label.config(text=path, foreground="black")
            self.log(_("LOG_AUTO_SELECTED_FIRMWARE", name=name))
        elif len(valid_entries) > 1:
            self.log(_("LOG_MULTIPLE_VALID_FILES"))

    def select_detected_firmware(self, event=None):
        selection = self.fw_tree.selection()
        if not selection:
            return
        path, is_valid = self._detected_paths.get(selection[0], (None, False))
        if path is None:
            return
        if not is_valid:
            if not messagebox.askyesno(
                _("TITLE_FILE_LOOKS_INVALID"),
                _("MSG_FIRMWARE_FILE_LOOKS_INVALID"),
            ):
                return
        self.firmware_path = path
        self.fw_label.config(text=path, foreground="black" if is_valid else "red")

    def browse_firmware(self):
        initial_dir = FIRMWARE_FOLDER if os.path.isdir(FIRMWARE_FOLDER) else None
        path = filedialog.askopenfilename(
            title="Select URTC firmware",
            initialdir=initial_dir,
            filetypes=[("Firmware binary", "*.bin"), ("All files", "*.*")],
        )
        if not path:
            return
        is_slave = self.flash_target_var.get() == "slave"
        fw_addr = SLAVE_APP_FLASH_ADDR if is_slave else APP_FLASH_ADDR
        fw_max = SLAVE_APP_MAX_SIZE if is_slave else APP_MAX_SIZE
        is_valid, reason, size = validate_firmware_file(path, fw_addr, fw_max)
        if not is_valid:
            if not messagebox.askyesno(
                _("TITLE_FILE_LOOKS_INVALID"),
                _("MSG_FIRMWARE_FILE_LOOKS_INVALID_REASON", reason=reason),
            ):
                return
        self.firmware_path = path
        self.fw_label.config(text=path, foreground="black" if is_valid else "red")
        self.fw_tree.selection_remove(self.fw_tree.selection())  # no detected-list item matches a manual browse

    def open_github_download_dialog(self):
        win = tk.Toplevel(self.root)
        win.title(_("TITLE_DOWNLOAD_FROM_GITHUB"))
        win.transient(self.root)
        win.resizable(True, True)
        win.geometry(_center_geometry(win, 560, 360))

        status_var = tk.StringVar(value=_("LBL_GITHUB_LOADING"))
        ttk.Label(win, textvariable=status_var, foreground="gray").pack(anchor="w", padx=8, pady=(8, 4))

        columns = ("name", "size")
        tree = ttk.Treeview(win, columns=columns, show="headings", selectmode="browse")
        tree.heading("name", text=_("COL_FILE"))
        tree.heading("size", text=_("COL_SIZE"))
        tree.column("name", width=380, stretch=True)
        tree.column("size", width=100, anchor="e", stretch=False)
        tree.pack(fill="both", expand=True, padx=8, pady=4)

        btn_row = ttk.Frame(win)
        btn_row.pack(fill="x", padx=8, pady=(4, 8))
        progress = ttk.Progressbar(btn_row, mode="determinate", maximum=100)
        progress.pack(side="left", fill="x", expand=True, padx=(0, 8))
        download_btn = ttk.Button(btn_row, text=_("BTN_DOWNLOAD_SELECTED"), state="disabled")
        download_btn.pack(side="left")
        ttk.Button(btn_row, text=_("BTN_CLOSE"), command=win.destroy).pack(side="left", padx=(8, 0))

        entries_by_iid = {}

        def _load_list():
            try:
                entries = list_firmware_files(log=self.log)
            except GitHubDownloadError as e:
                # Captured now - 'e' itself is deleted the moment this except
                # block exits, but the lambda below runs later, via root.after().
                error_msg = str(e)
                self.root.after(0, lambda: status_var.set(error_msg))
                return
            except Exception as e:
                error_msg = _("ERR_GITHUB_UNEXPECTED", e=e)
                self.root.after(0, lambda: status_var.set(error_msg))
                return

            def _populate():
                if not entries:
                    status_var.set(_("LBL_GITHUB_EMPTY"))
                    return
                for entry in entries:
                    size_kb = entry["size"] / 1024
                    iid = tree.insert("", "end", values=(entry["name"], f"{size_kb:.1f} KB"))
                    entries_by_iid[iid] = entry
                status_var.set(_("LBL_GITHUB_LOADED_COUNT", count=len(entries)))
            self.root.after(0, _populate)

        def _on_select(_event=None):
            download_btn.config(state="normal" if tree.selection() else "disabled")

        tree.bind("<<TreeviewSelect>>", _on_select)

        def _do_download():
            selection = tree.selection()
            if not selection:
                return
            entry = entries_by_iid.get(selection[0])
            if entry is None:
                return
            if not os.path.isdir(FIRMWARE_FOLDER):
                os.makedirs(FIRMWARE_FOLDER, exist_ok=True)
            dest_path = os.path.join(FIRMWARE_FOLDER, entry["name"])
            if os.path.isfile(dest_path) and not messagebox.askyesno(
                _("TITLE_FILE_EXISTS"), _("MSG_GITHUB_FILE_EXISTS_OVERWRITE", name=entry["name"]),
            ):
                return
            download_btn.config(state="disabled")
            status_var.set(_("LBL_GITHUB_DOWNLOADING_NAME", name=entry["name"]))

            def _download_worker():
                try:
                    download_file(
                        entry["download_url"], dest_path, log=self.log,
                        progress_cb=lambda pct: self.root.after(0, lambda: progress.configure(value=pct)),
                    )
                    self.root.after(0, lambda: status_var.set(_("LBL_GITHUB_DOWNLOAD_DONE", name=entry["name"])))
                    self.root.after(0, self.scan_firmware_folder)
                except GitHubDownloadError as e:
                    # Same capture-before-schedule fix as _load_list() above.
                    error_msg = str(e)
                    self.root.after(0, lambda: status_var.set(error_msg))
                except Exception as e:
                    error_msg = _("ERR_GITHUB_UNEXPECTED", e=e)
                    self.root.after(0, lambda: status_var.set(error_msg))
                finally:
                    self.root.after(0, lambda: download_btn.config(state="normal"))

            threading.Thread(target=_download_worker, daemon=True).start()

        download_btn.config(command=_do_download)
        threading.Thread(target=_load_list, daemon=True).start()

    def check_bus_activity(self):
        if self.transport is None:
            messagebox.showerror(_("TITLE_NOT_CONNECTED"), _("MSG_CONNECT_FIRST"))
            return
        self.bus_activity_label.config(text=_("STATUS_LISTENING_2S"), foreground="gray")
        self._set_ui_busy_state(True)
        threading.Thread(target=self._check_bus_activity_worker, daemon=True).start()

    def _check_bus_activity_worker(self):
        # Counts real protocol frames actually seen over a fixed window -
        # this is deliberately NOT the same thing as a true CAN bus-load
        # percentage or the controller's own REC/TEC error counters, which
        # would need a netlink query (SocketCAN) or adapter-specific
        # extensions (SLCAN) this project doesn't have a standard,
        # dependency-free way to get. What this DOES give: a genuine,
        # directly-measured "is anything talking on this bus at all, and
        # about how often" signal, on either transport.
        frame_count = 0
        is_socketcan = isinstance(self.transport, SocketCAN)
        before = SocketCAN.read_interface_stats(self.transport.interface) if is_socketcan else None
        deadline = time.time() + 2.0
        try:
            while time.time() < deadline:
                frame = self.transport.read_frame(timeout=0.1)
                if frame is not None:
                    frame_count += 1
        except Exception as e:
            self.log(_("LOG_BUS_ACTIVITY_CHECK_ERROR", e=e))
        after = SocketCAN.read_interface_stats(self.transport.interface) if is_socketcan else None
        self.root.after(0, lambda: self._show_bus_activity_result(frame_count, before, after))

    def _show_bus_activity_result(self, frame_count, before, after):
        self._set_ui_busy_state(False)
        rate = frame_count / 2.0
        text = _("LBL_FRAMES_IN_2S", count=frame_count, rate=rate)
        self.bus_activity_label.config(text=text, foreground="green" if frame_count > 0 else "orange")
        self.log(_("LOG_BUS_ACTIVITY", text=text))
        if before is not None and after is not None:
            deltas = {k: after[k] - before[k] for k in after}
            err_total = deltas["rx_errors"] + deltas["tx_errors"] + deltas["rx_dropped"] + deltas["tx_dropped"]
            self.log(_("LOG_SOCKETCAN_COUNTERS_DELTA", deltas=deltas))
            if err_total > 0:
                # This can't distinguish termination specifically from a
                # bitrate mismatch, a damaged cable, or a marginal
                # transceiver - the kernel's own counters don't carry that
                # level of detail, and getting it would need an actual
                # oscilloscope on the bus lines. What this DOES give: a
                # real, directly-measured signal that something at the
                # physical layer is off, named as a starting point for
                # troubleshooting rather than left as a bare number.
                err_rate = err_total / max(1, frame_count)
                self.log(
                    f"  {err_total} error(s)/drop(s) against {frame_count} good frames "
                    f"({err_rate:.1%} of traffic) - worth checking, in rough order of how "
                    f"common each cause tends to be: missing or doubled-up 120Ω bus "
                    f"termination (should be exactly 2 total, one at each physical end), a "
                    f"bitrate mismatch between nodes, a damaged/too-long cable run, or a "
                    f"marginal transceiver on one of the nodes."
                )

    def query_error_counters(self):
        # TEC/REC (Transmit/Receive Error Counter), read directly from the
        # board's own CAN peripheral ESR register - answered by whichever
        # of the application or bootloader is currently running, same
        # dual-answerable convention as CAN_ID_QUERY_VERSION. Complements
        # check_bus_activity above: that one counts frames actually seen
        # on the bus, this one asks the board itself what its own
        # controller's fault-confinement counters say.
        if self.transport is None:
            messagebox.showerror(_("TITLE_NOT_CONNECTED"), _("MSG_CONNECT_FIRST"))
            return
        self.error_counters_label.config(text=_("STATUS_QUERYING"), foreground="gray")
        self._set_ui_busy_state(True)

        def _worker():
            try:
                self.transport.send_frame(CAN_ID_QUERY_ERROR_COUNTERS, b"")
                deadline = time.time() + 1.5
                tec = rec = None
                while time.time() < deadline:
                    frame = self.transport.read_frame(timeout=0.1)
                    if frame is not None and frame[0] == CAN_ID_ERROR_COUNTERS_RESPONSE and len(frame[1]) >= 2:
                        tec, rec = frame[1][0], frame[1][1]
                        break
                if tec is None:
                    self.log(_("LOG_ERROR_COUNTERS_NO_RESPONSE"))
                    self.root.after(0, lambda: self.error_counters_label.config(
                        text=_("STATUS_NO_RESPONSE_LONG"), foreground="red"))
                else:
                    text = _("LBL_TEC_REC_VALUES", tec=tec, rec=rec)
                    self.log(_("LOG_ERROR_COUNTERS_VALUE", tec=tec, rec=rec))
                    # Error-passive at 128+, bus-off territory above that -
                    # same thresholds the CAN protocol's own fault-
                    # confinement state machine uses (RM0316).
                    color = "red" if (tec >= 128 or rec >= 128) else ("orange" if (tec > 0 or rec > 0) else "green")
                    self.root.after(0, lambda: self.error_counters_label.config(text=text, foreground=color))
            except Exception as e:
                self.log(_("LOG_ERROR_COUNTERS_QUERY_FAILED", e=e))
            finally:
                self.root.after(0, lambda: self._set_ui_busy_state(False))

        threading.Thread(target=_worker, daemon=True).start()

    def query_current_version(self):
        if self.transport is None:
            messagebox.showerror(_("TITLE_NOT_CONNECTED"), _("MSG_CONNECT_FIRST"))
            return
        self.current_version_label.config(text=_("STATUS_QUERYING"), foreground="gray")
        self._set_ui_busy_state(True)

        def _worker():
            try:
                flasher = URTCFlasher(self.transport, log=self.log)
                result = flasher.query_version()
                self.root.after(0, lambda: self._show_version_result(result))
            finally:
                self.root.after(0, lambda: self._set_ui_busy_state(False))

        threading.Thread(target=_worker, daemon=True).start()

    def query_expansion_board_type(self):
        if self.transport is None:
            messagebox.showerror(_("TITLE_NOT_CONNECTED"), _("MSG_CONNECT_FIRST"))
            return
        self._set_ui_busy_state(True)

        def _worker():
            try:
                self.transport.send_frame(CAN_ID_EXPANSION_TYPE_RESP, b"")
                deadline = time.time() + 1.5
                value = None
                while time.time() < deadline:
                    frame = self.transport.read_frame(timeout=0.1)
                    if frame is not None and frame[0] == CAN_ID_EXPANSION_TYPE_RESP and len(frame[1]) >= 1:
                        value = frame[1][0]
                        break
                if value is None or value > 6:
                    self.log(_("LOG_EXPANSION_TYPE_NO_RESPONSE"))
                    self.root.after(0, lambda: self.expansion_type_var.set(EXPANSION_BOARD_TYPES[0]))
                else:
                    self.log(_("LOG_EXPANSION_TYPE_VALUE", type=EXPANSION_BOARD_TYPES[value]))
                    self.root.after(0, lambda: self.expansion_type_var.set(EXPANSION_BOARD_TYPES[value]))
            except Exception as e:
                self.log(_("LOG_EXPANSION_TYPE_QUERY_FAILED", e=e))
            finally:
                self.root.after(0, lambda: self._set_ui_busy_state(False))

        threading.Thread(target=_worker, daemon=True).start()

    def save_expansion_board_type(self):
        if self.transport is None:
            messagebox.showerror(_("TITLE_NOT_CONNECTED"), _("MSG_CONNECT_FIRST"))
            return
        value = EXPANSION_BOARD_TYPES.index(self.expansion_type_var.get())
        if not messagebox.askyesno(
            _("TITLE_CONFIRM_EXPANSION_BOARD_TYPE"),
            _("MSG_CONFIRM_EXPANSION_BOARD_TYPE", type=EXPANSION_BOARD_TYPES[value]),
        ):
            return
        self._set_ui_busy_state(True)

        def _worker():
            try:
                self.transport.send_frame(CAN_ID_SET_EXPANSION_TYPE, bytes([value]))
                deadline = time.time() + 1.5
                confirmed = None
                while time.time() < deadline:
                    frame = self.transport.read_frame(timeout=0.1)
                    if frame is not None and frame[0] == CAN_ID_EXPANSION_TYPE_RESP and len(frame[1]) >= 1:
                        confirmed = frame[1][0]
                        break
                if confirmed == value:
                    self.log(_("LOG_EXPANSION_TYPE_SAVED_CONFIRMED", type=EXPANSION_BOARD_TYPES[value]))
                elif confirmed is not None:
                    self.log(_("LOG_EXPANSION_TYPE_MISMATCH", value=value, confirmed=confirmed))
                else:
                    self.log(_("LOG_EXPANSION_TYPE_NO_CONFIRMATION"))
            except Exception as e:
                self.log(_("LOG_EXPANSION_TYPE_SAVE_FAILED", e=e))
            finally:
                self.root.after(0, lambda: self._set_ui_busy_state(False))

        threading.Thread(target=_worker, daemon=True).start()

    # Same shape as query_expansion_board_type/save_expansion_board_type
    # above, for CAN_ID_SET_MLX_VARIANT/CAN_ID_MLX_VARIANT_RESP
    # (0x1A6/0x1A7) instead - see MLX_SENSOR_VARIANTS's own comment
    # (flasher_config.py) for when this control actually matters.
    def query_mlx_sensor_variant(self):
        if self.transport is None:
            messagebox.showerror(_("TITLE_NOT_CONNECTED"), _("MSG_CONNECT_FIRST"))
            return
        self._set_ui_busy_state(True)

        def _worker():
            try:
                self.transport.send_frame(CAN_ID_MLX_VARIANT_RESP, b"")
                deadline = time.time() + 1.5
                value = None
                while time.time() < deadline:
                    frame = self.transport.read_frame(timeout=0.1)
                    if frame is not None and frame[0] == CAN_ID_MLX_VARIANT_RESP and len(frame[1]) >= 1:
                        value = frame[1][0]
                        break
                if value is None or value > 3:
                    self.log(_("LOG_MLX_VARIANT_NO_RESPONSE"))
                    self.root.after(0, lambda: self.mlx_variant_var.set(MLX_SENSOR_VARIANTS[0]))
                else:
                    self.log(_("LOG_MLX_VARIANT_VALUE", type=MLX_SENSOR_VARIANTS[value]))
                    self.root.after(0, lambda: self.mlx_variant_var.set(MLX_SENSOR_VARIANTS[value]))
            except Exception as e:
                self.log(_("LOG_MLX_VARIANT_QUERY_FAILED", e=e))
            finally:
                self.root.after(0, lambda: self._set_ui_busy_state(False))

        threading.Thread(target=_worker, daemon=True).start()

    def save_mlx_sensor_variant(self):
        if self.transport is None:
            messagebox.showerror(_("TITLE_NOT_CONNECTED"), _("MSG_CONNECT_FIRST"))
            return
        value = MLX_SENSOR_VARIANTS.index(self.mlx_variant_var.get())
        if not messagebox.askyesno(
            _("TITLE_CONFIRM_MLX_VARIANT"),
            _("MSG_CONFIRM_MLX_VARIANT", type=MLX_SENSOR_VARIANTS[value]),
        ):
            return
        self._set_ui_busy_state(True)

        def _worker():
            try:
                self.transport.send_frame(CAN_ID_SET_MLX_VARIANT, bytes([value]))
                deadline = time.time() + 1.5
                confirmed = None
                while time.time() < deadline:
                    frame = self.transport.read_frame(timeout=0.1)
                    if frame is not None and frame[0] == CAN_ID_MLX_VARIANT_RESP and len(frame[1]) >= 1:
                        confirmed = frame[1][0]
                        break
                if confirmed == value:
                    self.log(_("LOG_MLX_VARIANT_SAVED_CONFIRMED", type=MLX_SENSOR_VARIANTS[value]))
                elif confirmed is not None:
                    self.log(_("LOG_MLX_VARIANT_MISMATCH", value=value, confirmed=confirmed))
                else:
                    self.log(_("LOG_MLX_VARIANT_NO_CONFIRMATION"))
            except Exception as e:
                self.log(_("LOG_MLX_VARIANT_SAVE_FAILED", e=e))
            finally:
                self.root.after(0, lambda: self._set_ui_busy_state(False))

        threading.Thread(target=_worker, daemon=True).start()

    def program_free_tool_config(self):
        if self.transport is None:
            messagebox.showerror(_("TITLE_NOT_CONNECTED"), _("MSG_CONNECT_FIRST"))
            return
        value = self._free_tool_display_to_selection[self.free_tool_var.get()]
        tool_display = self.free_tool_var.get()
        if not messagebox.askyesno(
            _("TITLE_CONFIRM_FREE_TOOL_CONFIG"),
            _("MSG_CONFIRM_FREE_TOOL_CONFIG", tool=tool_display),
        ):
            return
        self._set_ui_busy_state(True)

        def _worker():
            try:
                self.transport.send_frame(CAN_ID_SET_FREE_TOOL, bytes([value]))
                deadline = time.time() + 1.5
                confirmed = None
                while time.time() < deadline:
                    frame = self.transport.read_frame(timeout=0.1)
                    if frame is not None and frame[0] == CAN_ID_FREE_TOOL_CONFIG_RESP and len(frame[1]) >= 2:
                        confirmed = frame[1][1]  # frame[1][0] is the raw ID-jumper reading, not needed here
                        break
                if confirmed == value:
                    self.log(_("LOG_FREE_TOOL_SAVED_CONFIRMED", tool=tool_display))
                    result = _("LOG_FREE_TOOL_SAVED_CONFIRMED", tool=tool_display)
                elif confirmed is not None:
                    self.log(_("LOG_FREE_TOOL_MISMATCH", value=value, confirmed=confirmed))
                    result = _("LOG_FREE_TOOL_MISMATCH", value=value, confirmed=confirmed)
                else:
                    self.log(_("LOG_FREE_TOOL_NO_CONFIRMATION"))
                    result = _("LOG_FREE_TOOL_NO_CONFIRMATION")
            except Exception as e:
                self.log(_("LOG_FREE_TOOL_SAVE_FAILED", e=e))
                result = _("LOG_FREE_TOOL_SAVE_FAILED", e=e)
            finally:
                self.root.after(0, lambda: self.free_tool_result_var.set(result))
                self.root.after(0, lambda: self._set_ui_busy_state(False))

        threading.Thread(target=_worker, daemon=True).start()

    def query_peripheral_info(self):
        if self.transport is None:
            messagebox.showerror(_("TITLE_NOT_CONNECTED"), _("MSG_CONNECT_FIRST"))
            return
        self._set_ui_busy_state(True)

        def _worker():
            try:
                # 0x1A5 specifically, not 0x1A4 - 0x1A4 with any payload
                # byte is interpreted by the firmware as a set command
                # (see CANBUS.TXT); an empty payload to 0x1A5 can only
                # ever be a query.
                self.transport.send_frame(CAN_ID_PERIPHERAL_INFO_RESP, b"")
                deadline = time.time() + 1.5
                info = None
                while time.time() < deadline:
                    frame = self.transport.read_frame(timeout=0.1)
                    if frame is not None and frame[0] == CAN_ID_PERIPHERAL_INFO_RESP and len(frame[1]) >= 2:
                        info = (frame[1][0], frame[1][1])
                        break
                if info is None:
                    self.log(_("LOG_PERIPHERAL_NO_RESPONSE"))
                    result = _("LOG_PERIPHERAL_NO_RESPONSE")
                else:
                    peripheral_type, serial = info
                    type_desc = _("LBL_PERIPHERAL_TYPE_URTC") if peripheral_type == 0x03 else _(
                        "LBL_PERIPHERAL_TYPE_UNKNOWN", value=peripheral_type)
                    result = f"{type_desc}\n{_('LBL_DEVICE_SERIAL', serial=serial)}"
                    self.log(_("LOG_PERIPHERAL_INFO", type=type_desc, serial=serial))
                    self.root.after(0, lambda: self.device_serial_var.set(str(serial)))
            except Exception as e:
                self.log(_("LOG_PERIPHERAL_QUERY_FAILED", e=e))
                result = _("LOG_PERIPHERAL_QUERY_FAILED", e=e)
            finally:
                self.root.after(0, lambda: self.peripheral_info_result_var.set(result))
                self.root.after(0, lambda: self._set_ui_busy_state(False))

        threading.Thread(target=_worker, daemon=True).start()

    def program_device_serial(self):
        if self.transport is None:
            messagebox.showerror(_("TITLE_NOT_CONNECTED"), _("MSG_CONNECT_FIRST"))
            return
        try:
            value = int(self.device_serial_var.get())
            if not (0 <= value <= 255):
                raise ValueError
        except ValueError:
            messagebox.showerror(_("TITLE_INVALID_SERIAL"), _("MSG_INVALID_SERIAL"))
            return
        if not messagebox.askyesno(
            _("TITLE_CONFIRM_DEVICE_SERIAL"),
            _("MSG_CONFIRM_DEVICE_SERIAL", serial=value),
        ):
            return
        self._set_ui_busy_state(True)

        def _worker():
            try:
                self.transport.send_frame(CAN_ID_SET_DEVICE_SERIAL, bytes([value]))
                deadline = time.time() + 1.5
                confirmed = None
                while time.time() < deadline:
                    frame = self.transport.read_frame(timeout=0.1)
                    if frame is not None and frame[0] == CAN_ID_PERIPHERAL_INFO_RESP and len(frame[1]) >= 2:
                        confirmed = frame[1][1]  # frame[1][0] is the fixed peripheral type, not needed here
                        break
                if confirmed == value:
                    self.log(_("LOG_DEVICE_SERIAL_SAVED_CONFIRMED", serial=value))
                    result = _("LOG_DEVICE_SERIAL_SAVED_CONFIRMED", serial=value)
                elif confirmed is not None:
                    self.log(_("LOG_DEVICE_SERIAL_MISMATCH", value=value, confirmed=confirmed))
                    result = _("LOG_DEVICE_SERIAL_MISMATCH", value=value, confirmed=confirmed)
                else:
                    self.log(_("LOG_DEVICE_SERIAL_NO_CONFIRMATION"))
                    result = _("LOG_DEVICE_SERIAL_NO_CONFIRMATION")
            except Exception as e:
                self.log(_("LOG_DEVICE_SERIAL_SAVE_FAILED", e=e))
                result = _("LOG_DEVICE_SERIAL_SAVE_FAILED", e=e)
            finally:
                self.root.after(0, lambda: self.peripheral_info_result_var.set(result))
                self.root.after(0, lambda: self._set_ui_busy_state(False))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_language_change(self, chosen):
        if save_config({"language": chosen}):
            messagebox.showinfo(_("TITLE_RESTART_NEEDED"), _("MSG_RESTART_NEEDED"))
        else:
            messagebox.showerror(_("TITLE_COULDNT_SAVE"), _("MSG_LANGUAGE_NOT_SAVED", path=CONFIG_FILE_PATH))

    def auto_detect_bitrate(self):
        if self.transport is not None:
            messagebox.showerror(_("TITLE_ALREADY_CONNECTED"), _("MSG_DISCONNECT_FIRST_AUTODETECT"))
            return
        port = self.port_var.get()
        if not port:
            messagebox.showerror(_("TITLE_NOTHING_SELECTED"), _("MSG_SELECT_COM_PORT_FIRST"))
            return

        self._set_ui_busy_state(True)
        self.bitrate_status.config(text=_("STATUS_TRYING_EACH_BITRATE"), foreground="gray")

        def _worker():
            found_label = None
            try:
                # Most-likely-first order, not just the table's natural
                # order: URTC's bus is fixed at 500k, so that's tried
                # first, then its two most common neighbors.
                try_order = ["500 kbit/s", "250 kbit/s", "125 kbit/s", "1 Mbit/s",
                             "100 kbit/s", "50 kbit/s", "20 kbit/s", "10 kbit/s", "800 kbit/s"]
                for label in try_order:
                    code = next(c for l, c in SLCAN_BITRATES if l == label)
                    self.log(_("LOG_AUTODETECT_TRYING", label=label))
                    trial = None
                    try:
                        trial = SLCAN(port, log=lambda m: None)  # quiet - avoid spamming the log with 9 failed attempts
                        trial.open_channel(code)
                        flasher = URTCFlasher(trial, log=lambda m: None)
                        result = flasher.query_version(timeout=0.8)
                        if result is not None:
                            found_label = label
                            break
                    except (SLCANError, OSError):
                        pass
                    finally:
                        if trial is not None:
                            try:
                                trial.close()
                            except Exception:
                                pass
            finally:
                self.root.after(0, lambda: self._auto_detect_done(found_label))

        threading.Thread(target=_worker, daemon=True).start()

    def _auto_detect_done(self, found_label):
        self._set_ui_busy_state(False)
        if found_label:
            self.bitrate_var.set(found_label)
            self.bitrate_status.config(text=f"Found: {found_label}", foreground="green")
            self.log(_("LOG_AUTODETECT_RESPONDED", label=found_label))
        else:
            self.bitrate_status.config(text=_("STATUS_NO_RESPONSE_ANY_BITRATE"), foreground="red")
            self.log(_("LOG_AUTODETECT_NO_RESPONSE"))

    def _show_version_result(self, result):
        if result is None:
            self.current_version_label.config(
                text=_("STATUS_NO_RESPONSE_LONG"),
                foreground="red",
            )
            return
        hw_match = "" if result["hardware_id"] == THIS_HARDWARE_ID else "  \u26a0 HardwareID mismatch!"
        boot_ver = result.get("bootloader_version")
        boot_ver_text = f", bootloader v{boot_ver[0]}.{boot_ver[1]}.{boot_ver[2]}" if boot_ver else ""
        if result["responder"] == "bootloader" and result["hardware_id"] == 0:
            text = f"Bootloader running, no valid firmware currently installed{boot_ver_text}"
            color = "orange"
        else:
            text = (
                f"v{result['version_major']}.{result['version_minor']} "
                f"({result['responder']}, HardwareID 0x{result['hardware_id']:08X}){hw_match}{boot_ver_text}"
            )
            color = "green" if not hw_match else "red"
        self.current_version_label.config(text=text, foreground=color)
        self.log(_("LOG_CURRENT_VERSION_QUERY", text=text))

    def _set_ui_busy_state(self, busy):
        # Centralizes exactly which controls need to be locked while either
        # flash path is running - both touch self.transport (CAN path) or
        # spawn their own subprocess (SWD path), and letting Connect/
        # Disconnect/Query/the port selector fire concurrently from the
        # main thread was a real race condition: e.g. clicking Disconnect
        # mid-transfer closes the same serial port/socket the flash thread
        # is still reading from.
        state = "disabled" if busy else "normal"
        self.connect_btn.config(state=state)
        self.port_combo.config(state="disabled" if busy else "readonly")
        for child in self.query_btn_holder:
            child.config(state=state)
        if hasattr(self, "transport_radio_serial"):
            self.transport_radio_serial.config(state="disabled" if busy else ("normal" if HAVE_SERIAL else "disabled"))
        if hasattr(self, "transport_radio_socketcan"):
            self.transport_radio_socketcan.config(state="disabled" if busy else "normal")
        self.flash_btn.config(state="disabled" if busy else "normal")
        self.readback_btn.config(
            state="disabled" if (busy or self.flash_target_var.get() == "slave") else "normal"
        )
        self.swd_flash_btn.config(
            state="disabled" if (busy or not (self._pyocd_ok or self._cube_ok)) else "normal"
        )
        # Check Option Bytes connects via the exact same CubeProgrammerCLI
        # (same "-c port=SWD ..." connect syntax) that full_chip_flash uses
        # against the exact same physical probe - left unlocked here, it
        # could launch a second STM32CubeProgrammer CLI process against
        # that probe while an SWD full-chip erase/write is already
        # in-flight, which is exactly the kind of interrupted-write
        # scenario this section's own docstring warns can leave the board
        # with no valid firmware until reprogrammed.
        self.check_ob_btn.config(state="disabled" if (busy or not self._cube_ok) else "normal")
        # Auto Detect Bitrate opens up to 9 successive SLCAN connections on
        # this same COM port, one per candidate bitrate, each held open for
        # up to ~0.8s - a scan already in progress (itself a "busy" state,
        # see auto_detect_bitrate) left this button clickable, so a second
        # click could open a second SLCAN instance on the exact same port
        # while the first scan still has it open, corrupting both scans'
        # reads/writes against each other. Also respects is_serial the same
        # way on_transport_change already does - never enabled for
        # SocketCAN, which has no bitrate of its own to detect.
        self.autobaud_btn.config(
            state="disabled" if (busy or self.transport_var.get() != "serial") else "normal"
        )

    def _on_flash_target_change(self):
        # The expansion slave chip has no F-RAM of its own - confirmed
        # against its own real firmware source rather than assumed to
        # mirror the main board's own memory map - so "Erase F-RAM"
        # is meaningless for it, disabled rather than left clickable and
        # silently doing nothing.
        if self.flash_target_var.get() == "slave":
            self.erase_fram_var.set(False)
            self.erase_fram_check.config(state="disabled")
            # The expansion slave's own bootloader doesn't implement 0x7FD
            # (CANBUS.TXT) yet - same reasoning as F-RAM above, disabled
            # rather than left clickable and silently doing nothing.
            self.allow_downgrade_var.set(False)
            self.allow_downgrade_check.config(state="disabled")
            self.readback_btn.config(state="disabled")
        else:
            self.erase_fram_check.config(state="normal")
            self.allow_downgrade_check.config(state="normal")
            self.readback_btn.config(state="normal")

        # Master and slave application images validate against different
        # flash addresses (see scan_firmware_folder) - a file already
        # selected under the old target may be the wrong slot for the new
        # one, so re-scan and drop the stale selection rather than leaving
        # a now-mismatched path silently in place.
        self.firmware_path = None
        self.fw_label.config(text=_("STATUS_NO_FILE_SELECTED"), foreground="gray")
        self.scan_firmware_folder()

    def start_readback(self):
        if self.transport is None:
            messagebox.showerror(_("TITLE_NOT_CONNECTED"), _("MSG_CONNECT_FIRST"))
            return
        if self._flash_thread and self._flash_thread.is_alive():
            messagebox.showerror(_("TITLE_BUSY"), _("MSG_FLASH_ALREADY_IN_PROGRESS"))
            return
        save_path = filedialog.asksaveasfilename(
            title=_("TITLE_SAVE_READBACK"),
            defaultextension=".bin",
            initialfile=f"urtc_readback_{time.strftime('%Y%m%d_%H%M%S')}.bin",
            filetypes=[("Firmware binary", "*.bin")],
        )
        if not save_path:
            return

        self._stop_requested = False
        self._set_ui_busy_state(True)
        self.cancel_btn.config(state="normal")
        self.progress["value"] = 0

        def _worker():
            try:
                flasher = URTCFlasher(
                    self.transport,
                    log=self.log,
                    progress_cb=lambda pct: self.root.after(0, lambda: self.progress.configure(value=pct)),
                    stop_flag=lambda: self._stop_requested,
                )
                size = flasher.read_back_flash(save_path)
                self.root.after(0, lambda: messagebox.showinfo(
                    _("TITLE_SUCCESS"), _("MSG_READBACK_COMPLETE", size=size, path=save_path)))
            except FlashError as e:
                self.log(_("LOG_FAILED", e=e))
                msg = str(e)
                self.root.after(0, lambda: messagebox.showerror(_("TITLE_FLASH_FAILED"), msg))
            except Exception as e:
                self.log(_("LOG_UNEXPECTED_ERROR", e=e))
                msg = str(e)
                self.root.after(0, lambda: messagebox.showerror(_("TITLE_UNEXPECTED_ERROR"), msg))
            finally:
                self.root.after(0, lambda: self._set_ui_busy_state(False))
                self.root.after(0, lambda: self.cancel_btn.config(state="disabled"))

        self._flash_thread = threading.Thread(target=_worker, daemon=True)
        self._flash_thread.start()

    def start_flash(self):
        if self.transport is None:
            messagebox.showerror(_("TITLE_NOT_CONNECTED"), _("MSG_CONNECT_FIRST"))
            return
        if not self.firmware_path:
            messagebox.showerror(_("TITLE_NO_FIRMWARE"), _("MSG_SELECT_BIN_FIRST"))
            return
        if self._flash_thread and self._flash_thread.is_alive():
            messagebox.showerror(_("TITLE_BUSY"), _("MSG_FLASH_ALREADY_IN_PROGRESS"))
            return
        # Mirrors the symmetric check start_swd_flash() already does against
        # self._flash_thread - added as defense in depth even though it isn't
        # reachable through normal UI use today (_set_ui_busy_state(True)
        # already disables flash_btn synchronously, on the same click that
        # starts start_swd_flash(), before _swd_flash_thread itself exists).
        if self._swd_flash_thread and self._swd_flash_thread.is_alive():
            messagebox.showerror(_("TITLE_BUSY"), _("MSG_SWD_FLASH_ALREADY_IN_PROGRESS"))
            return
        target_label = _("OPT_TARGET_SLAVE") if self.flash_target_var.get() == "slave" else _("OPT_TARGET_MASTER")
        if not messagebox.askyesno(
            _("TITLE_CONFIRM_FLASH"),
            _("MSG_CONFIRM_FLASH_TARGET", target=target_label),
        ):
            return
        # Second, separate confirmation specifically for the anti-rollback
        # bypass - deliberately not folded into the confirmation above, so
        # checking this box always means an extra, unambiguous prompt of
        # its own rather than blending into the routine "confirm target"
        # dialog every flash already shows.
        if self.allow_downgrade_var.get() and not messagebox.askyesno(
            _("TITLE_CONFIRM_DOWNGRADE"),
            _("MSG_CONFIRM_DOWNGRADE"),
        ):
            return

        self._stop_requested = False
        self._set_ui_busy_state(True)
        self.cancel_btn.config(state="normal")
        self.progress["value"] = 0

        self._flash_thread = threading.Thread(target=self._flash_worker, daemon=True)
        self._flash_thread.start()

    def cancel_flash(self):
        self._stop_requested = True
        self.log(_("LOG_CANCEL_REQUESTED"))

    def _flash_worker(self):
        try:
            flasher = URTCFlasher(
                self.transport,
                log=self.log,
                progress_cb=lambda pct: self.root.after(0, lambda: self.progress.configure(value=pct)),
                stop_flag=lambda: self._stop_requested,
            )
            if self.flash_target_var.get() == "slave":
                if self.trigger_var.get():
                    flasher.trigger_slave_bootloader_entry()
                flasher.flash_slave(self.firmware_path)
            else:
                if self.erase_fram_var.get():
                    if not self.trigger_var.get():
                        self.log(_("LOG_SKIPPING_FRAM_ERASE"))
                    else:
                        flasher.erase_fram()
                if self.trigger_var.get():
                    flasher.trigger_bootloader_entry()
                flasher.flash(self.firmware_path, allow_downgrade=self.allow_downgrade_var.get())
            self.root.after(0, lambda: messagebox.showinfo(_("TITLE_SUCCESS"), _("MSG_FIRMWARE_UPDATE_COMPLETE")))
        except FlashError as e:
            self.log(_("LOG_FAILED", e=e))
            msg = str(e)
            self.root.after(0, lambda: messagebox.showerror(_("TITLE_FLASH_FAILED"), msg))
        except Exception as e:
            self.log(_("LOG_UNEXPECTED_ERROR", e=e))
            msg = str(e)
            self.root.after(0, lambda: messagebox.showerror(_("TITLE_UNEXPECTED_ERROR"), msg))
        finally:
            self.root.after(0, lambda: self._set_ui_busy_state(False))
            self.root.after(0, lambda: self.cancel_btn.config(state="disabled"))

    def browse_swd_bootloader(self):
        path = filedialog.askopenfilename(
            title="Select bootloader image",
            filetypes=[("Bootloader image", "*.bin *.hex *.elf *.axf"), ("All files", "*.*")],
        )
        if not path:
            return
        # Target-aware validation, same rule start_swd_flash() applies before
        # actually flashing - otherwise a legitimate slave image picked while
        # target=="slave" gets checked against the master's addr/size and
        # trips a confusing "invalid" warning.
        is_slave = self.swd_target_var.get() == "slave"
        boot_addr = SLAVE_BOOTLOADER_FLASH_ADDR if is_slave else BOOTLOADER_FLASH_ADDR
        boot_max = SLAVE_BOOTLOADER_MAX_SIZE if is_slave else BOOTLOADER_MAX_SIZE
        is_valid, reason, size = validate_swd_image_file(path, boot_max, "bootloader", boot_addr)
        if not is_valid:
            if not messagebox.askyesno(
                _("TITLE_FILE_LOOKS_INVALID"),
                _("MSG_BOOTLOADER_FILE_LOOKS_INVALID", reason=reason),
            ):
                return
        self.swd_bootloader_var.set(path)

    def browse_swd_app(self):
        path = filedialog.askopenfilename(
            title="Select application image",
            filetypes=[("Application image", "*.bin *.hex *.elf *.axf"), ("All files", "*.*")],
        )
        if not path:
            return
        # Target-aware validation, same rule start_swd_flash() applies before
        # actually flashing - see browse_swd_bootloader() above for why.
        is_slave = self.swd_target_var.get() == "slave"
        app_addr = SLAVE_APP_FLASH_ADDR if is_slave else APP_FLASH_ADDR
        app_max = SLAVE_APP_MAX_SIZE if is_slave else APP_MAX_SIZE
        is_valid, reason, size = validate_swd_image_file(path, app_max, "application", app_addr)
        if not is_valid:
            if not messagebox.askyesno(
                _("TITLE_FILE_LOOKS_INVALID"),
                _("MSG_APPLICATION_FILE_LOOKS_INVALID", reason=reason),
            ):
                return
        self.swd_app_var.set(path)

    def refresh_swd_probes(self):
        if not (self._pyocd_ok or self._cube_ok):
            return
        self.swd_probe_combo.set("(checking...)")
        self.swd_probe_refresh_btn.config(state="disabled")
        threading.Thread(target=self._refresh_swd_probes_worker, daemon=True).start()

    def _refresh_swd_probes_worker(self):
        tool = self.swd_tool_var.get()
        try:
            if tool == "pyocd" and self._pyocd_ok:
                prog = PyOCDCLI(log=lambda m: None)
            elif tool == "cube" and self._cube_ok:
                prog = CubeProgrammerCLI(log=lambda m: None)
            else:
                self.root.after(0, lambda: self._show_swd_probes([]))
                return
            probes = prog.list_probes()
        except Exception:
            probes = []
        self.root.after(0, lambda: self._show_swd_probes(probes))

    def _show_swd_probes(self, probes):
        self.swd_probe_refresh_btn.config(state="normal")
        # pyOCD gives (uid, description) pairs; CubeProgrammer gives bare
        # serial strings - normalize both into the same uid->label map so
        # the rest of the UI doesn't need to care which tool is active.
        if probes and isinstance(probes[0], tuple):
            self._swd_probe_map = {uid: desc for uid, desc in probes if uid}
        else:
            self._swd_probe_map = {serial: serial for serial in probes}
        labels = list(self._swd_probe_map.values())
        self.swd_probe_combo["values"] = labels
        if len(labels) == 1:
            self.swd_probe_combo.set(labels[0])
        elif len(labels) == 0:
            self.swd_probe_combo.set("(none found)")
        else:
            self.swd_probe_combo.set("")  # force an explicit choice when there's more than one

    def _selected_swd_probe_uid(self):
        """Turns the combobox's shown label back into the actual uid/serial
        to pass to the subprocess - returns None if nothing usable is
        selected (no probes, or multiple with nothing explicitly chosen)."""
        label = self.swd_probe_var.get()
        for uid, desc in self._swd_probe_map.items():
            if desc == label:
                return uid
        return None

    def start_check_option_bytes(self):
        if not self._cube_ok:
            messagebox.showerror(_("TITLE_NOT_AVAILABLE"), _("MSG_NEEDS_CUBEPROGRAMMER_SPECIFICALLY"))
            return
        if len(self._swd_probe_map) > 1 and not self._selected_swd_probe_uid():
            messagebox.showerror(
                _("TITLE_MULTIPLE_PROBES"),
                _("MSG_MULTIPLE_PROBES_PICK_ONE"),
            )
            return
        self._set_ui_busy_state(True)
        threading.Thread(target=self._check_option_bytes_worker, daemon=True).start()

    def _check_option_bytes_worker(self):
        try:
            prog = CubeProgrammerCLI(log=self.log)
            level, output = prog.read_option_bytes(serial=self._selected_swd_probe_uid(), dry_run=False)
            self.root.after(0, lambda: self._show_option_bytes_result(level))
        except SWDFlashError as e:
            self.log(_("LOG_FAILED", e=e))
            msg = str(e)
            self.root.after(0, lambda: messagebox.showerror(_("TITLE_OPTION_BYTE_CHECK_FAILED"), msg))
        except Exception as e:
            self.log(_("LOG_UNEXPECTED_ERROR", e=e))
            msg = str(e)
            self.root.after(0, lambda: messagebox.showerror(_("TITLE_UNEXPECTED_ERROR"), msg))
        finally:
            self.root.after(0, lambda: self._set_ui_busy_state(False))

    def _show_option_bytes_result(self, level):
        if level == "2":
            messagebox.showerror(
                _("TITLE_RDP_LEVEL_2_PERMANENT"),
                _("MSG_RDP_LEVEL_2_DETAIL"),
            )
        elif level == "1":
            messagebox.showwarning(
                _("TITLE_RDP_LEVEL_1"),
                _("MSG_RDP_LEVEL_1_DETAIL"),
            )
        elif level == "0":
            messagebox.showinfo(_("TITLE_RDP_LEVEL_0"), _("MSG_NO_READOUT_PROTECTION"))
        else:
            messagebox.showinfo(
                _("TITLE_RDP_UNPARSEABLE"),
                _("MSG_RDP_UNPARSEABLE_DETAIL"),
            )

    def start_swd_flash(self):
        if self._flash_thread and self._flash_thread.is_alive():
            messagebox.showerror(_("TITLE_BUSY"), _("MSG_CAN_UPDATE_ALREADY_IN_PROGRESS"))
            return
        if self._swd_flash_thread and self._swd_flash_thread.is_alive():
            messagebox.showerror(_("TITLE_BUSY"), _("MSG_SWD_FLASH_ALREADY_IN_PROGRESS"))
            return
        bootloader_path = self.swd_bootloader_var.get().strip()
        app_path = self.swd_app_var.get().strip()
        if not bootloader_path or not os.path.isfile(bootloader_path):
            messagebox.showerror(_("TITLE_MISSING_BOOTLOADER_IMAGE"), _("MSG_SELECT_VALID_BOOTLOADER_FILE"))
            return
        if not app_path or not os.path.isfile(app_path):
            messagebox.showerror(_("TITLE_MISSING_APPLICATION_IMAGE"), _("MSG_SELECT_VALID_APPLICATION_FILE"))
            return

        # Re-validated here too, not just in the Browse dialog above - the
        # path fields are plain text entries, so a manually typed or
        # pasted path would otherwise skip the check entirely.
        is_slave = self.swd_target_var.get() == "slave"
        boot_addr = SLAVE_BOOTLOADER_FLASH_ADDR if is_slave else BOOTLOADER_FLASH_ADDR
        boot_max = SLAVE_BOOTLOADER_MAX_SIZE if is_slave else BOOTLOADER_MAX_SIZE
        app_addr = SLAVE_APP_FLASH_ADDR if is_slave else APP_FLASH_ADDR
        app_max = SLAVE_APP_MAX_SIZE if is_slave else APP_MAX_SIZE
        ok, reason, _size = validate_swd_image_file(bootloader_path, boot_max, "bootloader", boot_addr)
        if not ok and not messagebox.askyesno(
            _("TITLE_BOOTLOADER_FILE_LOOKS_INVALID"),
            _("MSG_REASON_PROCEED_ANYWAY", reason=reason),
        ):
            return
        ok, reason, _size = validate_swd_image_file(app_path, app_max, "application", app_addr)
        if not ok and not messagebox.askyesno(
            _("TITLE_APPLICATION_FILE_LOOKS_INVALID"),
            _("MSG_REASON_PROCEED_ANYWAY", reason=reason),
        ):
            return

        if len(self._swd_probe_map) > 1 and not self._selected_swd_probe_uid():
            messagebox.showerror(
                _("TITLE_MULTIPLE_PROBES"),
                _("MSG_MULTIPLE_PROBES_PICK_ONE_FULLCHIP"),
            )
            return

        dry_run = self.swd_dry_run_var.get()
        tool_name = "pyOCD" if self.swd_tool_var.get() == "pyocd" else "STM32CubeProgrammer"
        probe_uid = self._selected_swd_probe_uid()
        probe_line = f"Probe: {self.swd_probe_var.get()}\n" if probe_uid else ""

        backup_path = None
        if self.swd_backup_var.get() and not dry_run:
            default_name = f"urtc_flash_backup_{time.strftime('%Y%m%d_%H%M%S')}.bin"
            backup_path = filedialog.asksaveasfilename(
                defaultextension=".bin", initialfile=default_name,
                filetypes=[("Binary files", "*.bin")],
                title="Save flash backup as...",
            )
            if not backup_path:
                return  # user cancelled the save dialog - don't proceed without the backup they asked for

        if dry_run:
            proceed = messagebox.askyesno(
                _("TITLE_DRY_RUN"),
                _("MSG_DRY_RUN_CONFIRM", tool=tool_name),
            )
        else:
            backup_line = _("LOG_BACKUP_TO_LINE", path=backup_path) if backup_path else ""
            proceed = messagebox.askyesno(
                _("TITLE_CONFIRM_FULL_CHIP"),
                _("MSG_CONFIRM_FULL_CHIP", tool=tool_name, probe_line=probe_line,
                  bootloader=bootloader_path, app=app_path, backup_line=backup_line),
            )
        if not proceed:
            return

        self._set_ui_busy_state(True)
        self._swd_flash_thread = threading.Thread(
            target=self._swd_flash_worker,
            args=(bootloader_path, app_path, self.swd_tool_var.get(), dry_run, probe_uid, backup_path, is_slave),
            daemon=True,
        )
        self._swd_flash_thread.start()

    def _swd_flash_worker(self, bootloader_path, app_path, tool, dry_run, probe_uid=None, backup_path=None, is_slave=False):
        try:
            if is_slave:
                target_kwargs = {
                    "bootloader_addr": SLAVE_BOOTLOADER_FLASH_ADDR,
                    "app_addr": SLAVE_APP_FLASH_ADDR,
                    "total_flash_size": SLAVE_TOTAL_FLASH_SIZE,
                }
            else:
                target_kwargs = {}  # main board's own defaults already baked into full_chip_flash's own signature
            if tool == "pyocd":
                programmer = PyOCDCLI(log=self.log)
                pyocd_target = SLAVE_PYOCD_TARGET_NAME if is_slave else PYOCD_TARGET_NAME
                programmer.full_chip_flash(bootloader_path, app_path, dry_run=dry_run, probe_uid=probe_uid,
                                            backup_path=backup_path, target=pyocd_target, **target_kwargs)
            else:
                programmer = CubeProgrammerCLI(log=self.log)
                programmer.full_chip_flash(bootloader_path, app_path, dry_run=dry_run, serial=probe_uid,
                                            backup_path=backup_path, **target_kwargs)
            if dry_run:
                self.root.after(0, lambda: messagebox.showinfo(
                    _("TITLE_DRY_RUN_COMPLETE"), _("MSG_DRY_RUN_COMPLETE")))
            else:
                self.root.after(0, lambda: messagebox.showinfo(
                    _("TITLE_SUCCESS"), _("MSG_FULL_CHIP_COMPLETE")))
        except SWDFlashError as e:
            self.log(_("LOG_FAILED", e=e))
            msg = str(e)
            self.root.after(0, lambda: messagebox.showerror(_("TITLE_SWD_FLASH_FAILED"), msg))
        except Exception as e:
            self.log(_("LOG_UNEXPECTED_ERROR", e=e))
            msg = str(e)
            self.root.after(0, lambda: messagebox.showerror(_("TITLE_UNEXPECTED_ERROR"), msg))
        finally:
            self.root.after(0, lambda: self._set_ui_busy_state(False))
