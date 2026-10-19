# =============================================================================
# URTC Flasher - Qt Quick CAN-OTA command deck
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Qt Quick front end for the real, safe CAN-OTA workflow.

This is not a second flashing implementation.  It uses the existing SLCAN,
SocketCAN, firmware validation and URTCFlasher protocol classes.  It is the
only window of the program (the headless ``--cli`` mode needs no window).
"""
from __future__ import annotations

import glob
import logging
import os
import platform
import sys
import threading
import time
import zipfile
from pathlib import Path

from PySide6.QtCore import QObject, Property, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

import flasher_config
from flasher_config import (
    APP_FLASH_ADDR, APP_MAX_SIZE, BITRATE_500K_SLCAN_CODE, SLCAN_BITRATES,
    BOOTLOADER_FLASH_ADDR, BOOTLOADER_MAX_SIZE,
    CAN_ID_ERROR_COUNTERS_RESPONSE, CAN_ID_EXPANSION_TYPE_RESP,
    CAN_ID_FREE_TOOL_CONFIG_RESP, CAN_ID_MLX_VARIANT_RESP,
    CAN_ID_PERIPHERAL_INFO_RESP, CAN_ID_QUERY_ERROR_COUNTERS,
    CAN_ID_SET_DEVICE_SERIAL, CAN_ID_SET_EXPANSION_TYPE,
    CAN_ID_SET_FREE_TOOL, CAN_ID_SET_MLX_VARIANT,
    EXPANSION_BOARD_TYPES, FIRMWARE_FOLDER,
    FLASHER_VERSION, ICON_IMAGE_PATH, MLX_SENSOR_VARIANTS,
    LOGS_FOLDER, PYOCD_TARGET_NAME, REQUIRE_PRODUCTION_SIGNATURE, SLAVE_APP_FLASH_ADDR, SLAVE_APP_MAX_SIZE,
    SLAVE_HARDWARE_ID, THIS_HARDWARE_ID,
    SLAVE_BOOTLOADER_FLASH_ADDR, SLAVE_BOOTLOADER_MAX_SIZE,
    SLAVE_PYOCD_TARGET_NAME, SLAVE_TOTAL_FLASH_SIZE, TOOL_NAMES, _, _current_language, save_config, translate_log_line,
)
from flasher_github import GitHubDownloadError, download_file, fetch_release, is_sidecar, sidecars_for
from flasher_integrity import manifest_signing_kind, preflight_image
from flasher_records import (
    build_update_report, find_recovery_image, prune_session_logs, writable_logs_folder, write_update_report,
)
from flasher_protocol import FlashError, URTCFlasher, minor_with_patch
from flasher_swd_tools import CubeProgrammerCLI, PyOCDCLI, SWDFlashError
from flasher_transports import SLCAN, SocketCAN, detect_bitrate_listen_only, list_socketcan_interfaces
from flasher_validation import validate_firmware_file, validate_swd_image_file
from urtc_ui import LanguageModel, connection_badge, format_bytes

try:
    import serial.tools.list_ports
    HAVE_SERIAL = True
except ImportError:
    HAVE_SERIAL = False


def _local_path(value: str) -> str:
    """A path chosen in a QML file dialog arrives as a file: URL; accept both forms."""
    text = str(value or "")
    if text.startswith("file:"):
        local = QUrl(text).toLocalFile()
        return os.path.normpath(local) if local else text
    return text


class FlasherQtBridge(QObject):
    """QML-facing state model over the production CAN-OTA backend."""

    MAX_LOG_LINES = 500  # the deck shows the last 12; older lines are dropped, not kept for ever

    changed = Signal()
    logChanged = Signal()
    _connectionResult = Signal(object, str)
    _flashResult = Signal(str)
    _flashProgress = Signal(int)
    _flashSpeed = Signal(float)
    _swdProbeResult = Signal("QVariantList")
    _swdFlashResult = Signal(str)
    releaseChanged = Signal()
    _releaseListed = Signal(str, object, str)
    _releaseProgressed = Signal(int)
    _releaseDownloaded = Signal(str, str)
    _busActivityResult = Signal(int, int)
    _bitrateDetected = Signal(str)
    _swdOptionByteResult = Signal(str, str)
    _snapshotResult = Signal(object, str)
    _logRequested = Signal(str)
    # Real device-configuration writes (expansion board type/MLX sensor
    # variant/free tool selection/device serial) - one shared signal,
    # keyed by which real field it is (mirrors URTC-TESTER's own
    # _queryResult, added for the exact same real reason there: one
    # generic worker instead of 4 near-duplicate ones). confirmed is the
    # real value the board echoed back (or None on a genuine timeout);
    # expected is what was actually sent, so _on_config_write_result can
    # tell a real match from a real mismatch without re-deriving it.
    _configWriteResult = Signal(str, object, object)

    def __init__(self) -> None:
        super().__init__()
        self._ports: list[str] = []
        self._socketcan_ports: set[str] = set()
        self._firmware: list[dict[str, object]] = []
        self._selected_port = ""
        self._bitrate_label = "500 kbit/s"
        self._selected_firmware = ""
        self._transport = None
        self._busy = False
        self._progress = 0
        self._status = "READY"
        self._logs: list[str] = []
        self._cancel_requested = False
        self._flash_path = ""
        # CAN-OTA options, with the same safe defaults as the Tk window:
        # main board, bootloader entry requested, no F-RAM erase and no
        # downgrade (which also needs its own second confirmation).
        self._flash_target = "master"
        self._trigger_bootloader = True
        self._erase_fram = False
        self._allow_downgrade = False
        self._downgrade_confirmed = False
        self._readback_result = ""
        self._bus_activity_text = ""
        self._export_result = ""
        self._recovery_candidate = ""
        self._browsed: dict[str, dict[str, object]] = {}   # files picked by hand, kept across rescans
        self._pending_invalid: dict[str, object] | None = None
        self._file_logger: logging.Logger | None = None
        self._release_entries: list[dict] = []
        self._release_status = ""
        self._release_loading = False
        self._release_downloading = False
        self._release_progress = 0
        self._release_overwrite = ""
        # Live transfer speed (kB/s, from URTCFlasher's speed_cb) plus a
        # reactive "still waiting" indicator driven by a plain QTimer -
        # deliberately not derived from _flashProgress/_flashSpeed alone,
        # since a genuinely stalled transfer means NEITHER of those signals
        # fires at all; only a timer ticking independently of the worker
        # thread can notice that and surface it.
        self._transfer_speed_kbps = 0.0
        self._transfer_last_update: float | None = None
        self._transfer_liveness_timer = QTimer(self)
        self._transfer_liveness_timer.setInterval(500)
        self._transfer_liveness_timer.timeout.connect(self._poll_transfer_liveness)
        self._transfer_idle_seconds = 0
        self._swd_scanning = False
        self._swd_tools: list[dict[str, object]] = []
        self._swd_probes: list[dict[str, str]] = []
        # Full-chip SWD/JTAG programming - real state mirroring the
        # earlier Tk window's own swd_target_var/swd_tool_var/
        # swd_probe_var/swd_dry_run_var/swd_backup_var (the earlier Tk window).
        # Same real safe defaults: master board, whichever tool is
        # actually installed, dry-run ON, backup OFF.
        self._swd_target = "master"
        self._swd_tool = "pyocd" if PyOCDCLI.available() else "cube"
        self._swd_selected_probe = ""
        self._swd_dry_run = True
        self._swd_backup = False
        self._swd_bootloader_path = ""
        self._swd_bootloader_valid = True
        self._swd_bootloader_reason = ""
        self._swd_app_path = ""
        self._swd_app_valid = True
        self._swd_app_reason = ""
        self._swd_flash_result = ""
        self._swd_option_byte_text = ""
        self._board_snapshot: list[dict[str, object]] = []
        self._config_write_texts: dict[str, str] = {
            "expansion_type": "", "mlx_variant": "", "free_tool": "", "device_serial": "",
        }
        self._connectionResult.connect(self._on_connection_result)
        self._flashResult.connect(self._on_flash_result)
        self._flashProgress.connect(self._on_flash_progress)
        self._flashSpeed.connect(self._on_flash_speed)
        self._swdProbeResult.connect(self._on_swd_probe_result)
        self._swdFlashResult.connect(self._on_swd_flash_result)
        self._releaseListed.connect(self._on_release_listed)
        self._releaseProgressed.connect(self._on_release_progress)
        self._releaseDownloaded.connect(self._on_release_downloaded)
        self._busActivityResult.connect(self._on_bus_activity_result)
        self._bitrateDetected.connect(self._on_bitrate_detected)
        self._swdOptionByteResult.connect(self._on_swd_option_byte_result)
        self._snapshotResult.connect(self._on_snapshot_result)
        self._logRequested.connect(self._append_log)
        self._configWriteResult.connect(self._on_config_write_result)
        self.scanPorts()
        self.scanFirmware()
        self.scanSwdCapabilities()

    @Property(str, constant=True)
    def title(self) -> str:
        return "URTC FLASHER"

    @Property(str, constant=True)
    def version(self) -> str:
        return FLASHER_VERSION

    @Property("QStringList", constant=True)
    def languageNames(self) -> list:
        """The names of the interface languages, each in its own language; the choice is saved and applies on the next start."""
        return LanguageModel(_current_language).names()

    @Property(int, constant=True)
    def languageIndex(self) -> int:
        return LanguageModel(_current_language).index()

    @Slot(int, result=str)
    def selectLanguage(self, index: int) -> str:
        """Saves the chosen language in the configuration file and returns the (already translated) notice to show."""
        code = LanguageModel().code_at(index)
        if code is None or code == _current_language:
            return ""
        if save_config({"language": code}):
            self._log(f"LANGUAGE_SAVED {code}")
            return _("MSG_RESTART_NEEDED")
        self._log(f"LANGUAGE_SAVE_FAILED {code}")
        return ""

    @Property(str, constant=True)
    def iconSource(self) -> str:
        return QUrl.fromLocalFile(str(Path(ICON_IMAGE_PATH))).toString()

    @Slot(str, result=str)
    def uiText(self, key: str) -> str:
        """Expose the established .lng lookup to the QML surface."""
        translated = _(key)
        return translated if translated != key else {
            "QT_CONNECTION": "CONNECTION",
            "QT_FIRMWARE_INVENTORY": "FIRMWARE INVENTORY",
            "QT_SCAN_FIRMWARE": "SCAN FIRMWARE",
            "QT_VALID": "VALID",
            "QT_INVALID": "INVALID",
            "QT_UPDATE_CHECKPOINTS": "CAN-OTA UPDATE CHECKPOINTS",
            "QT_CHECKPOINTS": "1  Validate selected firmware\n2  Enter signed bootloader session\n3  Transfer and verify backup image\n4  Confirm safe completion",
            "QT_START_CAN_OTA": "START CAN-OTA",
            "QT_ACTIVITY_LOG": "ACTIVITY LOG",
            "QT_CONFIRM_CAN_OTA": "Confirm CAN-OTA update",
            "QT_CONFIRM_CAN_OTA_BODY": "The selected application firmware will be sent to the connected board. Continue?",
            "QT_CONFIRM_FLASH": "CONFIRM FLASH",
            "QT_ADVANCED_DIAGNOSTICS": "ADVANCED DIAGNOSTICS",
            "QT_SWD_JTAG_READONLY": "SWD/JTAG READ-ONLY DISCOVERY",
            "QT_SWD_FULL_CHIP_SECTION": "FULL-CHIP PROGRAMMING (SWD/JTAG)",
            "QT_SCAN_PROBES": "SCAN PROBES",
            "QT_NOT_INSTALLED": "NOT INSTALLED",
            "QT_NO_PROBES": "No USB debug probe detected.",
            "QT_SWD_SAFETY_NOTE": (
                "Discovery is read-only. Full-chip programming below talks to the target "
                "directly over SWD/JTAG (not this app's CAN-OTA connection) - it genuinely "
                "erases and reprograms the whole chip. Dry run is on by default; read the "
                "log before turning it off."
            ),
            "QT_BOARD_SNAPSHOT": "BOARD SNAPSHOT",
            "QT_READ_BOARD_STATE": "READ BOARD STATE",
            "QT_BOARD_SNAPSHOT_HELP": "Active diagnostics send documented read queries only. No persistent setting, firmware or option byte is changed.",
            "QT_NO_BOARD_SNAPSHOT": "No board state read yet.",
            "QT_DEVICE_CONFIG": "DEVICE CONFIGURATION",
        }.get(key, key)

    @Property("QVariantList", notify=changed)
    def ports(self) -> list[str]:
        return self._ports

    @Property("QVariantList", notify=changed)
    def firmware(self) -> list[dict[str, object]]:
        return self._firmware

    @Property(str, notify=changed)
    def selectedPort(self) -> str:
        return self._selected_port

    @Property(str, notify=changed)
    def selectedFirmware(self) -> str:
        return self._selected_firmware

    @Property(bool, notify=changed)
    def connected(self) -> bool:
        return self._transport is not None

    @Property(bool, notify=changed)
    def busy(self) -> bool:
        return self._busy

    @Property(int, notify=changed)
    def progress(self) -> int:
        return self._progress

    @Property(str, notify=changed)
    def transferSpeedText(self) -> str:
        if not self._busy or self._transfer_speed_kbps <= 0:
            return ""
        return _("LBL_TRANSFER_SPEED", kbps=f"{self._transfer_speed_kbps:.1f}")

    @Property(str, notify=changed)
    def transferStalledText(self) -> str:
        if not self._busy or self._transfer_idle_seconds < 2:
            return ""
        return _("LBL_TRANSFER_STALLED", secs=self._transfer_idle_seconds)


    @Property(str, notify=changed)
    def statusColor(self) -> str:
        """Colour of the status line: the shared badge of the connection state (connected or disconnected)."""
        return connection_badge(True if self.connected else None).colour

    @Property(str, notify=changed)
    def status(self) -> str:
        return translate_log_line(self._status)

    @Property("QStringList", notify=logChanged)
    def logs(self) -> list[str]:
        return self._logs[-12:]

    @Property(bool, notify=changed)
    def canFlash(self) -> bool:
        return self.connected and bool(self._selected_firmware) and not self._busy

    # -- a firmware file chosen by hand, the signing warning, the release tag ---
    @Slot(str)
    def addFirmwareFile(self, file_url: str) -> None:
        """Use a file picked from anywhere. A file that does not look like an image for the chosen slot
        waits for the operator's explicit confirmation (acceptInvalidFirmware) before it can be selected."""
        path = _local_path(file_url)
        if self._busy or not path or not os.path.isfile(path):
            return
        valid, reason, size = validate_firmware_file(path, *self._flash_slot())
        entry = {"name": os.path.basename(path), "path": path, "valid": valid, "reason": reason, "size": size}
        if valid:
            self._browsed[path] = entry
            self._selected_firmware = path
            self._pending_invalid = None
            self.scanFirmware()
            return
        self._pending_invalid = entry
        self.changed.emit()

    @Property(str, notify=changed)
    def invalidFirmwareReason(self) -> str:
        """Why the file just picked does not look valid; empty when nothing waits for confirmation."""
        entry = self._pending_invalid
        return _("MSG_FIRMWARE_FILE_LOOKS_INVALID_REASON", reason=entry["reason"]) if entry else ""

    @Slot()
    def acceptInvalidFirmware(self) -> None:
        entry, self._pending_invalid = self._pending_invalid, None
        if entry is None or self._busy:
            return
        self._browsed[str(entry["path"])] = entry
        self._selected_firmware = str(entry["path"])
        self._log("FIRMWARE_SELECTED_DESPITE_WARNING")
        self.scanFirmware()

    @Slot()
    def rejectInvalidFirmware(self) -> None:
        self._pending_invalid = None
        self.changed.emit()

    @Property(str, notify=changed)
    def signingWarning(self) -> str:
        """Shown under the selected image when it is signed with the PUBLIC development key."""
        if not self._selected_firmware:
            return ""
        try:
            kind = manifest_signing_kind(self._selected_firmware)
        except OSError:
            return ""
        if kind != "dev":
            return ""
        return _("LBL_DEV_KEY_REFUSED" if REQUIRE_PRODUCTION_SIGNATURE else "LBL_DEV_KEY_WARNING")

    # -- the files of a GitHub release: list them, pick one, download it with its digest and manifest ---
    @Property("QVariantList", notify=releaseChanged)
    def releaseImages(self) -> list[dict[str, str]]:
        return [
            {"name": str(entry["name"]), "size": format_bytes(int(entry.get("size") or 0))}
            for entry in self._release_entries
            if not is_sidecar(str(entry["name"]))
        ]

    @Property(str, notify=releaseChanged)
    def releaseStatus(self) -> str:
        return self._release_status

    @Property(bool, notify=releaseChanged)
    def releaseBusy(self) -> bool:
        return self._release_loading or self._release_downloading

    @Property(int, notify=releaseChanged)
    def releaseProgress(self) -> int:
        return self._release_progress

    @Property(str, notify=releaseChanged)
    def releaseOverwriteName(self) -> str:
        """The file that already exists in firmware/ and waits for the operator's yes before it is replaced."""
        return self._release_overwrite

    @Property(str, notify=releaseChanged)
    def releaseOverwriteQuestion(self) -> str:
        return _("MSG_GITHUB_FILE_EXISTS_OVERWRITE", name=self._release_overwrite) if self._release_overwrite else ""

    @Slot(str)
    def loadRelease(self, tag: str) -> None:
        """List the files of a release (the newest when the tag is empty)."""
        if self.releaseBusy:
            self._log("GITHUB_DOWNLOAD_BLOCKED")
            return
        self._release_loading = True
        self._release_status = _("LBL_GITHUB_LOADING")
        self.releaseChanged.emit()
        threading.Thread(target=self._release_list_worker, args=(tag.strip() or None,), daemon=True, name="urtc-qt-github-list").start()

    def _release_list_worker(self, tag: str | None) -> None:
        try:
            release_tag, entries = fetch_release(tag, log=self._log)
            self._releaseListed.emit(release_tag or "?", entries, "")
        except GitHubDownloadError as exc:
            self._releaseListed.emit("", [], str(exc))
        except Exception as exc:  # network or unexpected response: show it, never crash the deck
            self._releaseListed.emit("", [], _("ERR_GITHUB_UNEXPECTED", e=exc))

    @Slot(str, object, str)
    def _on_release_listed(self, tag: str, entries: object, error: str) -> None:
        self._release_loading = False
        self._release_entries = [] if error else list(entries)  # type: ignore[call-overload]
        images = self.releaseImages
        if error:
            self._release_status = error
            self._log(f"GITHUB_FAILED {error}")
        elif not images:
            self._release_status = _("LBL_GITHUB_EMPTY")
        else:
            self._release_status = _("LBL_GITHUB_LOADED_RELEASE", count=len(images), tag=tag)
        self.releaseChanged.emit()

    @Slot(str)
    def downloadReleaseFile(self, name: str) -> None:
        """Download one listed image and the digest and manifest files published with it into firmware/."""
        if self.releaseBusy:
            return
        entry = next((e for e in self._release_entries if e["name"] == name and not is_sidecar(name)), None)
        if entry is None or os.path.basename(name) != name:
            return  # unknown, or a name that tries to leave the firmware folder: never written
        try:
            os.makedirs(FIRMWARE_FOLDER, exist_ok=True)
        except OSError as exc:
            self._release_status = _("ERR_GITHUB_WRITE_FAILED", reason=exc)
            self.releaseChanged.emit()
            return
        if os.path.isfile(os.path.join(FIRMWARE_FOLDER, name)) and self._release_overwrite != name:
            self._release_overwrite = name
            self.releaseChanged.emit()
            return
        self._release_overwrite = ""
        self._release_downloading = True
        self._release_progress = 0
        self._release_status = _("LBL_GITHUB_DOWNLOADING_NAME", name=name)
        self.releaseChanged.emit()
        threading.Thread(target=self._release_download_worker, args=(entry,), daemon=True, name="urtc-qt-github-download").start()

    @Slot()
    def confirmReleaseOverwrite(self) -> None:
        name = self._release_overwrite
        if name:
            self.downloadReleaseFile(name)

    @Slot()
    def cancelReleaseOverwrite(self) -> None:
        self._release_overwrite = ""
        self.releaseChanged.emit()

    def _release_download_worker(self, entry: dict) -> None:
        name = str(entry["name"])
        try:
            download_file(
                entry["download_url"], os.path.join(FIRMWARE_FOLDER, name), log=self._log, expected_size=entry.get("size"),
                progress_cb=self._releaseProgressed.emit,
            )
            # The published digest and manifest (with the signature the bootloader expects) travel with the image.
            for sidecar in sidecars_for(self._release_entries, name):
                side = str(sidecar["name"])
                if os.path.basename(side) == side:
                    download_file(sidecar["download_url"], os.path.join(FIRMWARE_FOLDER, side), log=self._log, expected_size=sidecar.get("size"))
            self._releaseDownloaded.emit(name, "")
        except GitHubDownloadError as exc:
            self._releaseDownloaded.emit(name, str(exc))
        except Exception as exc:
            self._releaseDownloaded.emit(name, _("ERR_GITHUB_UNEXPECTED", e=exc))

    @Slot(int)
    def _on_release_progress(self, percent: int) -> None:
        self._release_progress = max(0, min(100, percent))
        self.releaseChanged.emit()

    @Slot(str, str)
    def _on_release_downloaded(self, name: str, error: str) -> None:
        self._release_downloading = False
        if error:
            self._release_status = error
            self._log(f"GITHUB_FAILED {error}")
        else:
            self._release_status = _("LBL_GITHUB_DOWNLOAD_DONE", name=name)
            self._release_progress = 100
            self._log(f"GITHUB_DOWNLOADED {name}")
            self.scanFirmware()
        self.releaseChanged.emit()

    # -- closing and the session log file -------------------------------------
    def start_session_log(self) -> None:
        """Write every log line also to logs/urtc_flasher_<time>.log (only the program itself calls this, not the tests)."""
        try:
            folder = writable_logs_folder(LOGS_FOLDER)
            if folder is None:
                return
            prune_session_logs(folder)
            handler = logging.FileHandler(os.path.join(folder, f"urtc_flasher_{time.strftime('%Y%m%d_%H%M%S')}.log"), encoding="utf-8")
        except OSError:
            return
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        self._file_logger = logging.getLogger(f"urtc_flasher_qt_{id(self)}")
        self._file_logger.setLevel(logging.INFO)
        self._file_logger.addHandler(handler)
        self._file_logger.info("=== URTC Flasher v%s session started ===", FLASHER_VERSION)

    @Property(str, constant=True)
    def closeWhileBusyTitle(self) -> str:
        return _("TITLE_FLASH_IN_PROGRESS")

    @Property(str, constant=True)
    def closeWhileBusyBody(self) -> str:
        return _("MSG_FLASH_IN_PROGRESS_CLOSE_CONFIRM")

    @Slot()
    def prepareToQuit(self) -> None:
        """Stop a transfer and release the adapter before the window goes away."""
        self._cancel_requested = True
        transport, self._transport = self._transport, None
        if transport is not None:
            try:
                transport.close()
            except Exception:
                pass
        handlers = list(self._file_logger.handlers) if self._file_logger is not None else []
        for handler in handlers:
            handler.close()
            self._file_logger.removeHandler(handler)

    # -- CAN-OTA options (target, bootloader entry, F-RAM erase, downgrade) --
    def _flash_slot(self) -> tuple[int, int]:
        """Flash address and size the images are validated against for the chosen target."""
        if self._flash_target == "slave":
            return SLAVE_APP_FLASH_ADDR, SLAVE_APP_MAX_SIZE
        return APP_FLASH_ADDR, APP_MAX_SIZE

    @Property(str, notify=changed)
    def flashTarget(self) -> str:
        return self._flash_target

    @Property(bool, notify=changed)
    def triggerBootloader(self) -> bool:
        return self._trigger_bootloader

    @Property(bool, notify=changed)
    def eraseFram(self) -> bool:
        return self._erase_fram

    @Property(bool, notify=changed)
    def allowDowngrade(self) -> bool:
        return self._allow_downgrade

    @Property(bool, notify=changed)
    def downgradeOptionsAvailable(self) -> bool:
        """F-RAM erase, the downgrade authorisation and the CAN backup exist for the main board only."""
        return self._flash_target == "master"

    @Property(bool, notify=changed)
    def canReadback(self) -> bool:
        return self.connected and not self._busy and self._flash_target == "master"

    @Property(str, notify=changed)
    def readbackResult(self) -> str:
        return self._readback_result

    @Property(str, notify=changed)
    def flashConfirmTitle(self) -> str:
        return _("TITLE_CONFIRM_FLASH")

    @Property(str, notify=changed)
    def flashConfirmBody(self) -> str:
        label = _("OPT_TARGET_SLAVE") if self._flash_target == "slave" else _("OPT_TARGET_MASTER")
        return _("MSG_CONFIRM_FLASH_TARGET", target=label)

    @Property(str, constant=True)
    def downgradeConfirmTitle(self) -> str:
        return _("TITLE_CONFIRM_DOWNGRADE")

    @Property(str, constant=True)
    def downgradeConfirmBody(self) -> str:
        return _("MSG_CONFIRM_DOWNGRADE")

    @Slot(str)
    def setFlashTarget(self, target: str) -> None:
        """Main board or expansion slave. Switching drops the options that do not exist for the slave
        and the selected image (it was validated for the other slot), then rescans."""
        if self._busy or target not in ("master", "slave") or target == self._flash_target:
            return
        self._flash_target = target
        if target == "slave":
            self._erase_fram = False
            self._allow_downgrade = False
        self._downgrade_confirmed = False
        self._selected_firmware = ""
        self.scanFirmware()

    # -- help texts: README (in the interface language when a translation exists), licence, project page, plain log ---
    README_SUFFIXES = {
        "spanish": "_spa", "italian": "_ita", "french": "_fra", "german": "_deu",
        "chinese": "_zho", "japanese": "_jpn", "portuguese": "_por",
    }

    @Slot(result=str)
    def readmeText(self) -> str:
        folder = flasher_config.base_dir
        candidate = os.path.join(folder, f"README{self.README_SUFFIXES.get(_current_language, '')}.md")
        path = candidate if os.path.isfile(candidate) else os.path.join(folder, "README.md")
        try:
            with open(path, encoding="utf-8") as stream:
                return stream.read()
        except OSError as exc:
            return f"{_('TITLE_EXPORT_FAILED')}: {exc}"

    @Slot(result=str)
    def licenseText(self) -> str:
        try:
            with open(os.path.join(flasher_config.base_dir, "LICENSE"), encoding="utf-8") as stream:
                return stream.read()
        except OSError:
            return _("MSG_LICENSE_FALLBACK")

    @Property(str, constant=True)
    def githubUrl(self) -> str:
        return "https://github.com/JuanenRac/URTC-FLASHER"

    @Slot(str, result=bool)
    def saveLogText(self, save_path: str) -> bool:
        """Save the on-screen log as plain text (the lighter counterpart of the debug bundle)."""
        path = QUrl(save_path).toLocalFile() if save_path.startswith("file:") else save_path
        try:
            with open(path, "w", encoding="utf-8") as stream:
                stream.write("\n".join(self._logs) + "\n")
        except OSError as exc:
            self._log(f"LOG_SAVE_FAILED {exc}")
            return False
        self._log(f"LOG_SAVED {path}")
        return True

    @Slot(bool)
    def setTriggerBootloader(self, enabled: bool) -> None:
        if not self._busy:
            self._trigger_bootloader = bool(enabled)
            self.changed.emit()

    @Slot(bool)
    def setEraseFram(self, enabled: bool) -> None:
        if not self._busy and self._flash_target == "master":
            self._erase_fram = bool(enabled)
            self.changed.emit()

    @Slot(bool)
    def setAllowDowngrade(self, enabled: bool) -> None:
        """Ticking this only arms the option: the flash still needs the separate downgrade confirmation."""
        if self._busy or self._flash_target != "master":
            return
        self._allow_downgrade = bool(enabled)
        self._downgrade_confirmed = False
        self.changed.emit()

    @Slot()
    def confirmDowngrade(self) -> None:
        """The operator accepted the extra downgrade prompt (asked after the routine target prompt)."""
        if self._allow_downgrade and self._flash_target == "master":
            self._downgrade_confirmed = True

    @Slot(str)
    def startReadback(self, save_path: str) -> None:
        """Back up the firmware installed on the main board over CAN (the file name comes from a save dialog)."""
        path = _local_path(save_path)
        if not self.canReadback:
            self._log("READBACK_BLOCKED")
            return
        if not path:
            return
        self._cancel_requested = False
        self._progress = 0
        self._transfer_speed_kbps = 0.0
        self._transfer_idle_seconds = 0
        self._transfer_last_update = time.monotonic()
        self._transfer_liveness_timer.start()
        self._readback_result = ""
        self._set_state(status="READBACK IN PROGRESS", busy=True)
        self._log("READBACK_STARTED")
        threading.Thread(target=self._readback_worker, args=(path,), daemon=True, name="urtc-qt-readback").start()

    def _readback_worker(self, save_path: str) -> None:
        try:
            flasher = URTCFlasher(
                self._transport, log=self._log, progress_cb=self._flashProgress.emit,
                stop_flag=lambda: self._cancel_requested, speed_cb=self._flashSpeed.emit,
            )
            size = flasher.read_back_flash(save_path)
            self._flashResult.emit(f"READBACK_COMPLETE {size} {save_path}")
        except FlashError as exc:
            self._flashResult.emit(f"READBACK_FAILED {exc}")
        except Exception as exc:
            self._flashResult.emit(f"READBACK_UNEXPECTED {exc}")

    @Property(str, notify=changed)
    def busActivityText(self) -> str:
        return self._bus_activity_text

    @Slot()
    def checkBusActivity(self) -> None:
        """Count the frames seen on the bus for two seconds (nothing is transmitted)."""
        if self._transport is None or self._busy:
            self._log("BUS_ACTIVITY_BLOCKED")
            return
        self._bus_activity_text = ""
        self._set_state(status="BUS ACTIVITY CHECK", busy=True)
        threading.Thread(target=self._bus_activity_worker, args=(self._transport,), daemon=True, name="urtc-qt-bus-activity").start()

    def _bus_activity_worker(self, transport) -> None:
        count = 0
        before = after = None
        is_socketcan = isinstance(transport, SocketCAN)
        try:
            if is_socketcan:
                before = SocketCAN.read_interface_stats(transport.interface)
            deadline = time.time() + 2.0
            while time.time() < deadline:
                if transport.read_frame(timeout=0.1) is not None:
                    count += 1
            if is_socketcan:
                after = SocketCAN.read_interface_stats(transport.interface)
        except Exception as exc:
            self._log(f"BUS_ACTIVITY_FAILED {exc}")
        errors = 0
        if before is not None and after is not None:
            errors = sum(
                max(0, after[key] - before[key])
                for key in ("rx_errors", "tx_errors", "rx_dropped", "tx_dropped")
                if key in after and key in before
            )
        self._busActivityResult.emit(count, errors)

    @Slot(int, int)
    def _on_bus_activity_result(self, count: int, errors: int) -> None:
        text = _("LBL_FRAMES_IN_2S", count=count, rate=count / 2.0)
        if errors:
            text += f" / {errors} err"
        self._bus_activity_text = text
        self._set_state(status="READY", busy=False)
        self._log(f"BUS_ACTIVITY {text}")

    @Slot(str)
    def exportDebugBundle(self, save_path: str) -> None:
        """Write the on-screen log, a diagnostics summary and the selected image to a .zip."""
        path = _local_path(save_path)
        if not path:
            return
        try:
            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as bundle:
                bundle.writestr("session_log.txt", "\n".join(self._logs) + "\n")
                diagnostics = [
                    f"URTC Flasher version: {FLASHER_VERSION}",
                    f"Python: {sys.version}",
                    f"Platform: {platform.platform()}",
                    f"pyserial available: {HAVE_SERIAL}",
                    f"pyOCD found: {PyOCDCLI.available()}",
                    f"STM32CubeProgrammer found: {CubeProgrammerCLI.available()}",
                    f"Current port/interface: {self._selected_port}",
                    f"Current bitrate (Serial/SLCAN): {self._bitrate_label}",
                    f"Connected: {self._transport is not None}",
                    f"Flash target: {self._flash_target}",
                    f"Selected CAN firmware file: {self._selected_firmware or '(none)'}",
                    f"Selected SWD bootloader file: {self._swd_bootloader_path or '(none)'}",
                    f"Selected SWD application file: {self._swd_app_path or '(none)'}",
                ]
                bundle.writestr("system_diagnostics.txt", "\n".join(diagnostics))
                if self._selected_firmware and os.path.isfile(self._selected_firmware):
                    bundle.write(self._selected_firmware, "firmware/" + os.path.basename(self._selected_firmware))
        except OSError as exc:
            self._export_result = _("TITLE_EXPORT_FAILED") + ": " + str(exc)
            self._log(f"DEBUG_BUNDLE_FAILED {exc}")
        else:
            self._export_result = _("MSG_SAVED_TO", path=path)
            self._log(f"DEBUG_BUNDLE_EXPORTED {path}")
        self.changed.emit()

    @Property(str, notify=changed)
    def exportResult(self) -> str:
        return self._export_result

    @Property(str, constant=True)
    def aboutText(self) -> str:
        return (
            f"URTC Flasher v{FLASHER_VERSION}\n"
            "JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>\n"
            "GNU General Public License v3.0 or later (GPL-3.0-or-later)"
        )


    @Property("QVariantList", notify=changed)
    def swdTools(self) -> list[dict[str, object]]:
        return self._swd_tools

    @Property("QVariantList", notify=changed)
    def swdProbes(self) -> list[dict[str, str]]:
        return self._swd_probes

    @Property(bool, notify=changed)
    def swdScanning(self) -> bool:
        return self._swd_scanning

    # -- Full-chip SWD/JTAG programming - real state mirroring
    # the earlier Tk window's own swd_target_var/swd_tool_var/swd_probe_var/
    # swd_dry_run_var/swd_backup_var. This talks to the target directly
    # over the debug probe, NOT the CAN transport - every gate below is
    # deliberately independent of self.connected. --
    @Property(str, notify=changed)
    def swdTarget(self) -> str:
        return self._swd_target

    @Property(str, notify=changed)
    def swdTool(self) -> str:
        return self._swd_tool

    @Property(str, notify=changed)
    def swdSelectedProbe(self) -> str:
        return self._swd_selected_probe

    @Property(bool, notify=changed)
    def swdDryRun(self) -> bool:
        return self._swd_dry_run

    @Property(bool, notify=changed)
    def swdBackup(self) -> bool:
        return self._swd_backup

    @Property(str, notify=changed)
    def swdBootloaderPath(self) -> str:
        return self._swd_bootloader_path

    @Property(bool, notify=changed)
    def swdBootloaderValid(self) -> bool:
        return self._swd_bootloader_valid

    @Property(str, notify=changed)
    def swdBootloaderReason(self) -> str:
        return self._swd_bootloader_reason

    @Property(str, notify=changed)
    def swdAppPath(self) -> str:
        return self._swd_app_path

    @Property(bool, notify=changed)
    def swdAppValid(self) -> bool:
        return self._swd_app_valid

    @Property(str, notify=changed)
    def swdAppReason(self) -> str:
        return self._swd_app_reason

    @Property(str, notify=changed)
    def swdFlashResult(self) -> str:
        return self._swd_flash_result

    @Property(str, notify=changed)
    def swdOptionByteText(self) -> str:
        return self._swd_option_byte_text

    def _swd_tool_display_name(self) -> str:
        return "pyOCD" if self._swd_tool == "pyocd" else "STM32CubeProgrammer"

    @Property("QVariantList", notify=changed)
    def swdMatchingProbes(self) -> list[dict[str, str]]:
        """swdProbes (above) intentionally lists every probe both CLIs
        found, even the same physical ST-Link reported twice - real,
        useful for the read-only discovery panel. Picking a probe to
        actually flash with needs the subset that answers to the
        CURRENTLY selected tool, since a pyOCD uid isn't a valid
        STM32CubeProgrammer --sn (and vice versa)."""
        tool_name = self._swd_tool_display_name()
        return [p for p in self._swd_probes if p.get("tool") == tool_name]

    @Property(bool, notify=changed)
    def canCheckSwdOptionBytes(self) -> bool:
        """Real STM32CubeProgrammer-only check - pyOCD doesn't expose
        option bytes the same way (see HELP_RDP_CHECK_READONLY's own
        real text)."""
        cube_available = any(item["name"] == "STM32CubeProgrammer" and item["available"] for item in self._swd_tools)
        return cube_available and not self._busy

    @Property(bool, notify=changed)
    def canFullChipFlash(self) -> bool:
        """Same real preconditions as the earlier Tk window's own
        start_swd_flash(): a supported tool actually installed, both
        real image files selected, and - if more than one probe answers
        to the selected tool - one of them explicitly chosen rather
        than letting the CLI guess which ST-Link to erase."""
        tool_available = any(item["name"] == self._swd_tool_display_name() and item["available"] for item in self._swd_tools)
        matching_probes = self.swdMatchingProbes
        probe_ok = len(matching_probes) <= 1 or bool(self._swd_selected_probe)
        return (
            not self._busy
            and tool_available
            and probe_ok
            and bool(self._swd_bootloader_path)
            and bool(self._swd_app_path)
        )

    @Property(bool, notify=changed)
    def swdNeedsProbeChoice(self) -> bool:
        return len(self.swdMatchingProbes) > 1 and not self._swd_selected_probe

    @Property(str, notify=changed)
    def swdFlashConfirmTitle(self) -> str:
        return _("TITLE_DRY_RUN") if self._swd_dry_run else _("TITLE_CONFIRM_FULL_CHIP")

    @Slot(str, result=str)
    def buildSwdFlashConfirmBody(self, backup_path: str) -> str:
        """Real message assembly, matching the earlier Tk window's own
        start_swd_flash() probe_line/backup_line construction exactly -
        kept here rather than chained QML .replace() calls since
        MSG_CONFIRM_FULL_CHIP alone carries 5 real placeholders, more
        than any other confirm dialog this deck shows. backup_path is
        "" whenever no backup was requested (or this is a dry run,
        which never needs one)."""
        tool_name = self._swd_tool_display_name()
        if self._swd_dry_run:
            return _("MSG_DRY_RUN_CONFIRM", tool=tool_name)
        probe_line = _("LBL_PROBE") + f" {self._swd_selected_probe}\n" if self._swd_selected_probe else ""
        backup_line = _("LOG_BACKUP_TO_LINE", path=backup_path) if backup_path else ""
        return _(
            "MSG_CONFIRM_FULL_CHIP",
            tool=tool_name, probe_line=probe_line,
            bootloader=self._swd_bootloader_path, app=self._swd_app_path,
            backup_line=backup_line,
        )

    @Property("QVariantList", notify=changed)
    def boardSnapshot(self) -> list[dict[str, object]]:
        return self._board_snapshot

    @Property(bool, notify=changed)
    def canReadBoardSnapshot(self) -> bool:
        return self.connected and not self._busy

    # -- device configuration writes (real, persistent EEPROM fields -
    # only this tool ever writes them; every other real app in this
    # ecosystem, including URTC-TESTER's own Qt Quick deck, only reads
    # them). Same real gate as the board snapshot above. --
    @Property(bool, notify=changed)
    def canWriteDeviceConfig(self) -> bool:
        return self.connected and not self._busy

    @Property("QVariantList", constant=True)
    def expansionBoardTypeOptions(self) -> list[str]:
        return list(EXPANSION_BOARD_TYPES)

    @Property("QVariantList", constant=True)
    def mlxSensorVariantOptions(self) -> list[str]:
        return list(MLX_SENSOR_VARIANTS)

    @Property("QVariantList", constant=True)
    def freeToolOptions(self) -> list[str]:
        """Real display labels, index-aligned with the real selection
        value each one writes (0 = none, matching
        the earlier Tk window's own _free_tool_display_to_selection)."""
        return [_("OPT_FREE_TOOL_NONE")] + [f"{tool_id + 1} - {name}" for tool_id, name in TOOL_NAMES.items()]

    @Property(str, notify=changed)
    def expansionBoardTypeResult(self) -> str:
        return self._config_write_texts["expansion_type"]

    @Property(str, notify=changed)
    def mlxSensorVariantResult(self) -> str:
        return self._config_write_texts["mlx_variant"]

    @Property(str, notify=changed)
    def freeToolConfigResult(self) -> str:
        return self._config_write_texts["free_tool"]

    @Property(str, notify=changed)
    def deviceSerialResult(self) -> str:
        return self._config_write_texts["device_serial"]

    def _log(self, message: str) -> None:
        """Queue logs from CAN worker threads onto the Qt GUI thread."""
        self._logRequested.emit(str(message))

    @Slot(str)
    def _append_log(self, message: str) -> None:
        line = translate_log_line(message)
        self._logs.append(line)
        if self._file_logger is not None:
            self._file_logger.info(line)
        if len(self._logs) > self.MAX_LOG_LINES:
            del self._logs[: len(self._logs) - self.MAX_LOG_LINES]
        self.logChanged.emit()

    def _set_state(self, *, status: str | None = None, busy: bool | None = None) -> None:
        if status is not None:
            self._status = status
        if busy is not None:
            self._busy = busy
        self.changed.emit()

    @Slot()
    def scanPorts(self) -> None:
        ports = [item.device for item in serial.tools.list_ports.comports()] if HAVE_SERIAL else []
        if sys.platform.startswith("linux"):
            self._socketcan_ports = set(list_socketcan_interfaces())
            ports.extend(item for item in sorted(self._socketcan_ports) if item not in ports)
        else:
            self._socketcan_ports = set()
        self._ports = ports
        if self._selected_port not in ports:
            self._selected_port = ports[0] if ports else ""
        self._log(f"PORT_SCAN count={len(ports)}")
        self.changed.emit()

    @Slot(str)
    def selectPort(self, port: str) -> None:
        if self._transport is None and not self._busy and port in self._ports:
            self._selected_port = port
            self.changed.emit()

    @Property("QVariantList", constant=True)
    def bitrateLabels(self) -> list[str]:
        return [label for label, _code in SLCAN_BITRATES]

    @Property(str, notify=changed)
    def selectedBitrate(self) -> str:
        return self._bitrate_label

    @Slot(str)
    def selectBitrate(self, label: str) -> None:
        """Bus speed for serial (SLCAN) adapters; SocketCAN takes its speed from the interface."""
        if self._transport is None and not self._busy and label in self.bitrateLabels:
            self._bitrate_label = label
            self.changed.emit()

    @Slot()
    def autoDetectBitrate(self) -> None:
        """Listen-only search for the bus speed: nothing is transmitted at any speed tried."""
        if self._transport is not None or self._busy:
            return
        if not self._selected_port or self._selected_port in self._socketcan_ports:
            self._log(_("MSG_SELECT_COM_PORT_FIRST"))
            return
        self._set_state(status=_("STATUS_TRYING_EACH_BITRATE"), busy=True)
        threading.Thread(target=self._autodetect_worker, args=(self._selected_port,), daemon=True, name="urtc-qt-autobaud").start()

    def _autodetect_worker(self, port: str) -> None:
        found = ""
        try:
            # Most likely first: URTC's bus is 500 kbit/s, then its two usual neighbours.
            order = ["500 kbit/s", "250 kbit/s", "125 kbit/s", "1 Mbit/s", "100 kbit/s", "50 kbit/s", "20 kbit/s", "10 kbit/s", "800 kbit/s"]
            by_label = dict(SLCAN_BITRATES)

            def open_listen_only(code):
                trial = SLCAN(port, log=lambda message: None)
                try:
                    trial.open_channel(code, listen_only=True)
                except Exception:
                    trial.close()
                    raise
                return trial

            found = detect_bitrate_listen_only(
                open_listen_only, [(label, by_label[label]) for label in order],
                listen_seconds=1.0, on_try=lambda label: self._log(_("LOG_AUTODETECT_TRYING", label=label)),
            ) or ""
        except Exception as exc:  # a missing adapter or a busy port must not crash the deck
            self._log(f"AUTODETECT_FAILED {exc}")
        finally:
            self._bitrateDetected.emit(found)

    def _on_bitrate_detected(self, label: str) -> None:
        if label:
            self._bitrate_label = label
            self._set_state(status=_("STATUS_FOUND_BITRATE", label=label), busy=False)
            self._log(_("LOG_AUTODETECT_RESPONDED", label=label))
        else:
            self._set_state(status=_("STATUS_NO_RESPONSE_ANY_BITRATE"), busy=False)
            self._log(_("LOG_AUTODETECT_NO_RESPONSE"))

    def _slcan_bitrate_code(self) -> str:
        for label, code in SLCAN_BITRATES:
            if label == self._bitrate_label:
                return code
        return BITRATE_500K_SLCAN_CODE

    @Slot()
    def scanFirmware(self) -> None:
        if self._busy:
            self._log("FIRMWARE_SCAN_BLOCKED operation in progress")
            return
        entries: list[dict[str, object]] = []
        folder = Path(FIRMWARE_FOLDER)
        if folder.is_dir():
            for raw_path in sorted(glob.glob(str(folder / "*.bin"))):
                path = Path(raw_path)
                if "BOOTLOADER" in path.name.upper():
                    continue
                valid, reason, size = validate_firmware_file(path, *self._flash_slot())
                entries.append({"name": path.name, "path": str(path), "valid": valid, "reason": reason, "size": size})
        for path, browsed in list(self._browsed.items()):
            if not os.path.isfile(path):
                del self._browsed[path]
            elif not any(item["path"] == path for item in entries):
                valid, reason, size = validate_firmware_file(path, *self._flash_slot())
                browsed.update(valid=valid, reason=reason, size=size)
                entries.append(dict(browsed))
        self._firmware = entries
        valid_paths = [str(item["path"]) for item in entries if item["valid"]]
        if self._selected_firmware not in {str(item["path"]) for item in entries}:
            self._selected_firmware = valid_paths[0] if len(valid_paths) == 1 else ""
        self._log(f"FIRMWARE_SCAN count={len(entries)} valid={len(valid_paths)}")
        self.changed.emit()

    @Slot(str)
    def selectFirmware(self, path: str) -> None:
        if (
            not self._busy
            and any(str(item["path"]) == path and bool(item["valid"]) for item in self._firmware)
        ):
            self._selected_firmware = path
            self.changed.emit()

    @Slot()
    def scanSwdCapabilities(self) -> None:
        """Report actual local SWD tooling without touching a target device."""
        pyocd = PyOCDCLI()
        cube = CubeProgrammerCLI()
        self._swd_tools = [
            {"name": "pyOCD", "available": bool(pyocd.exe), "path": pyocd.exe or ""},
            {
                "name": "STM32CubeProgrammer",
                "available": bool(cube.exe),
                "path": cube.exe or "",
            },
        ]
        self._log(
            "SWD_CAPABILITIES "
            + " ".join(
                f"{item['name']}={'READY' if item['available'] else 'MISSING'}"
                for item in self._swd_tools
            )
        )
        self.changed.emit()

    @Slot()
    def scanSwdProbes(self) -> None:
        """Enumerate USB debug probes only; never connect to or program a chip."""
        if self._busy or self._swd_scanning:
            return
        self.scanSwdCapabilities()
        if not any(bool(item["available"]) for item in self._swd_tools):
            self._swd_probes = []
            self._log("SWD_PROBE_SCAN_SKIPPED no supported programmer found")
            self.changed.emit()
            return
        self._swd_scanning = True
        self._swd_probes = []
        self._log("SWD_PROBE_SCAN_STARTED read-only USB enumeration")
        self.changed.emit()
        threading.Thread(
            target=self._scan_swd_probes_worker,
            daemon=True,
            name="urtc-qt-swd-probe-scan",
        ).start()

    def _scan_swd_probes_worker(self) -> None:
        probes: list[dict[str, str]] = []
        if PyOCDCLI.available():
            try:
                for uid, description in PyOCDCLI(log=self._log).list_probes():
                    probes.append(
                        {"tool": "pyOCD", "identifier": uid, "description": description}
                    )
            except Exception as exc:
                self._log(f"SWD_PROBE_SCAN_PYOCD_FAILED {exc}")
        if CubeProgrammerCLI.available():
            try:
                for probe_serial in CubeProgrammerCLI(log=self._log).list_probes():
                    probes.append(
                        {
                            "tool": "STM32CubeProgrammer",
                            "identifier": probe_serial,
                            "description": "ST-LINK serial",
                        }
                    )
            except Exception as exc:
                self._log(f"SWD_PROBE_SCAN_CUBE_FAILED {exc}")
        self._swdProbeResult.emit(probes)

    @Slot("QVariantList")
    def _on_swd_probe_result(self, probes: list[dict[str, str]]) -> None:
        # One physical ST-Link may be reported by both tools.  Keep both
        # reports visible because they prove which CLI can address it later.
        self._swd_probes = probes
        self._swd_scanning = False
        self._log(f"SWD_PROBE_SCAN_COMPLETE count={len(probes)}")
        self.changed.emit()

    def _swd_target_addrs(self) -> tuple[int, int, int, int]:
        """(bootloader_addr, bootloader_max_size, app_addr, app_max_size)
        for the currently selected target - same real per-chip table as
        the earlier Tk window's own browse_swd_bootloader/browse_swd_app."""
        if self._swd_target == "slave":
            return SLAVE_BOOTLOADER_FLASH_ADDR, SLAVE_BOOTLOADER_MAX_SIZE, SLAVE_APP_FLASH_ADDR, SLAVE_APP_MAX_SIZE
        return BOOTLOADER_FLASH_ADDR, BOOTLOADER_MAX_SIZE, APP_FLASH_ADDR, APP_MAX_SIZE

    @Slot(str)
    def setSwdTarget(self, target: str) -> None:
        if target not in ("master", "slave") or self._busy:
            return
        self._swd_target = target
        # Re-validate both already-selected files against the new
        # target's own real addr/size table - start_swd_flash() itself
        # re-checks on every flash attempt for the same real reason: a
        # bootloader picked while "master" was selected shouldn't keep
        # showing green after switching to "slave".
        if self._swd_bootloader_path:
            self.setSwdBootloaderPath(self._swd_bootloader_path)
        if self._swd_app_path:
            self.setSwdAppPath(self._swd_app_path)
        self.changed.emit()

    @Slot(str)
    def setSwdTool(self, tool: str) -> None:
        if tool in ("pyocd", "cube") and not self._busy:
            self._swd_tool = tool
            self._swd_selected_probe = ""  # a probe uid/serial from one CLI is meaningless to the other
            self.changed.emit()

    @Slot(str)
    def setSwdSelectedProbe(self, identifier: str) -> None:
        if not self._busy:
            self._swd_selected_probe = identifier
            self.changed.emit()

    @Slot(bool)
    def setSwdDryRun(self, enabled: bool) -> None:
        if not self._busy:
            self._swd_dry_run = enabled
            self.changed.emit()

    @Slot(bool)
    def setSwdBackup(self, enabled: bool) -> None:
        if not self._busy:
            self._swd_backup = enabled
            self.changed.emit()

    @Slot(str)
    def setSwdBootloaderPath(self, path: str) -> None:
        """path is either a plain filesystem path (re-validation call
        from setSwdTarget above, or a manually typed/pasted TextField
        value) or a file:// URL (QML's own FileDialog.selectedFile) -
        both normalized to a plain path here, same real re-validate-on
        every-entry-point discipline the earlier Tk window's own
        browse_swd_bootloader has (its own docstring: "the path fields
        are plain text entries, so a manually typed or pasted path
        would otherwise skip the check entirely")."""
        if self._busy:
            return
        local_path = QUrl(path).toLocalFile() or path
        self._swd_bootloader_path = local_path
        if local_path and os.path.isfile(local_path):
            boot_addr, boot_max, _app_addr, _app_max = self._swd_target_addrs()
            ok, reason, _size = validate_swd_image_file(local_path, boot_max, "bootloader", boot_addr)
            self._swd_bootloader_valid, self._swd_bootloader_reason = ok, reason
        else:
            self._swd_bootloader_valid, self._swd_bootloader_reason = False, "file not found"
        self._log(f"SWD_BOOTLOADER_SELECTED {local_path} valid={self._swd_bootloader_valid}")
        self.changed.emit()

    @Slot(str)
    def setSwdAppPath(self, path: str) -> None:
        if self._busy:
            return
        local_path = QUrl(path).toLocalFile() or path
        self._swd_app_path = local_path
        if local_path and os.path.isfile(local_path):
            _boot_addr, _boot_max, app_addr, app_max = self._swd_target_addrs()
            ok, reason, _size = validate_swd_image_file(local_path, app_max, "application", app_addr)
            self._swd_app_valid, self._swd_app_reason = ok, reason
        else:
            self._swd_app_valid, self._swd_app_reason = False, "file not found"
        self._log(f"SWD_APP_SELECTED {local_path} valid={self._swd_app_valid}")
        self.changed.emit()

    @Slot(str)
    def startFullChipFlash(self, backup_path: str) -> None:
        """Called once the user has confirmed via the shared
        configConfirm dialog (see FlasherDeck.qml's own
        fullChipFlashButton handler) - backup_path is "" whenever no
        backup was requested (or this is a dry run, which never
        actually needs a real file). This is the one real destructive
        action this whole method migrates from the earlier Tk window's own
        start_swd_flash()/_swd_flash_worker - full_chip_flash() itself
        (flasher_swd_tools.py) is reused completely unchanged."""
        if not self.canFullChipFlash:
            self._log("SWD_FLASH_BLOCKED not ready - busy, missing tool/files, or multiple probes with none selected")
            return
        is_slave = self._swd_target == "slave"
        self._set_state(
            status="SWD/JTAG DRY RUN" if self._swd_dry_run else "SWD/JTAG FULL-CHIP PROGRAMMING",
            busy=True,
        )
        self._log(
            f"SWD_FLASH_STARTED tool={self._swd_tool} target={self._swd_target} "
            f"dry_run={self._swd_dry_run} backup={'yes' if backup_path else 'no'}"
        )
        threading.Thread(
            target=self._swd_flash_worker,
            args=(
                self._swd_bootloader_path, self._swd_app_path, self._swd_tool, self._swd_dry_run,
                self._swd_selected_probe or None, backup_path or None, is_slave,
            ),
            daemon=True,
            name="urtc-qt-swd-flash",
        ).start()

    def _swd_flash_worker(
        self, bootloader_path: str, app_path: str, tool: str, dry_run: bool,
        probe_uid: str | None, backup_path: str | None, is_slave: bool,
    ) -> None:
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
                programmer = PyOCDCLI(log=self._log)
                pyocd_target = SLAVE_PYOCD_TARGET_NAME if is_slave else PYOCD_TARGET_NAME
                programmer.full_chip_flash(
                    bootloader_path, app_path, dry_run=dry_run, probe_uid=probe_uid,
                    backup_path=backup_path, target=pyocd_target, **target_kwargs,
                )
            else:
                programmer = CubeProgrammerCLI(log=self._log)
                programmer.full_chip_flash(
                    bootloader_path, app_path, dry_run=dry_run, serial=probe_uid,
                    backup_path=backup_path, **target_kwargs,
                )
            self._swdFlashResult.emit("SWD_FLASH_DRY_RUN_COMPLETE" if dry_run else "SWD_FLASH_COMPLETE")
        except SWDFlashError as exc:
            self._swdFlashResult.emit(f"SWD_FLASH_FAILED {exc}")
        except Exception as exc:
            self._swdFlashResult.emit(f"SWD_FLASH_UNEXPECTED {exc}")

    @Slot(str)
    def _on_swd_flash_result(self, result: str) -> None:
        self._swd_flash_result = result
        self._set_state(status=result, busy=False)
        self._log(result)

    @Slot()
    def checkSwdOptionBytes(self) -> None:
        """Real, read-only RDP (readout protection) level check - see
        HELP_RDP_CHECK_READONLY's own real text for why this is
        STM32CubeProgrammer-only."""
        if not self.canCheckSwdOptionBytes:
            self._log("SWD_OPTION_BYTE_CHECK_BLOCKED needs STM32CubeProgrammer specifically, or busy")
            return
        self._set_state(status="CHECKING OPTION BYTES", busy=True)
        threading.Thread(
            target=self._check_option_bytes_worker,
            daemon=True,
            name="urtc-qt-swd-optionbytes",
        ).start()

    def _check_option_bytes_worker(self) -> None:
        try:
            prog = CubeProgrammerCLI(log=self._log)
            level, _output = prog.read_option_bytes(serial=self._swd_selected_probe or None, dry_run=False)
            self._swdOptionByteResult.emit(level or "", "")
        except SWDFlashError as exc:
            self._swdOptionByteResult.emit("", str(exc))
        except Exception as exc:
            self._swdOptionByteResult.emit("", str(exc))

    @Slot(str, str)
    def _on_swd_option_byte_result(self, level: str, error: str) -> None:
        if error:
            self._swd_option_byte_text = f"{_('TITLE_SWD_FLASH_FAILED')}: {error}"
        else:
            texts = {
                "0": _("MSG_NO_READOUT_PROTECTION"),
                "1": _("MSG_RDP_LEVEL_1_DETAIL"),
                "2": _("MSG_RDP_LEVEL_2_DETAIL"),
            }
            self._swd_option_byte_text = texts.get(level, _("MSG_RDP_UNPARSEABLE_DETAIL"))
        self._log(f"SWD_OPTION_BYTE_CHECK_RESULT level={level!r} error={error!r}")
        self._set_state(status="READY" if not error else "OPTION BYTE CHECK FAILED", busy=False)

    @Slot()
    def readBoardSnapshot(self) -> None:
        """Read documented runtime identity/configuration responses only."""
        if not self.canReadBoardSnapshot:
            self._log("BOARD_SNAPSHOT_BLOCKED connect first")
            return
        transport = self._transport
        if transport is None:
            return
        self._set_state(status="READING BOARD STATE", busy=True)
        self._log("BOARD_SNAPSHOT_STARTED documented read queries only")
        threading.Thread(
            target=self._read_board_snapshot_worker,
            args=(transport,),
            daemon=True,
            name="urtc-qt-board-snapshot",
        ).start()

    @staticmethod
    def _wait_for_frame(transport, expected_id: int, minimum_size: int, timeout: float = 1.5):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            frame = transport.read_frame(timeout=0.1)
            if frame is not None and frame[0] == expected_id and len(frame[1]) >= minimum_size:
                return frame[1]
        return None

    def _read_board_snapshot_worker(self, transport) -> None:
        items: list[dict[str, object]] = []
        try:
            version = URTCFlasher(transport, log=self._log).query_version()
            self._recovery_candidate = ""
            if (
                version is not None and version["responder"] == "bootloader" and version["hardware_id"] == 0
                and self._flash_target == "master" and not self._selected_firmware
            ):
                # The board sits in its bootloader with no valid application: offer the newest official image.
                self._recovery_candidate = find_recovery_image(FIRMWARE_FOLDER, THIS_HARDWARE_ID) or ""
            if version is None:
                items.append({"label": "Version", "value": "No response", "ok": False})
            else:
                suffix = ""
                if version["bootloader_version"] is not None:
                    suffix = " / bootloader " + ".".join(map(str, version["bootloader_version"]))
                items.append(
                    {
                        "label": "Version",
                        "value": (
                            f"{version['responder']} v{version['version_major']}."
                            f"{minor_with_patch(version)} / HW 0x{version['hardware_id']:08X}{suffix}"
                        ),
                        "ok": True,
                    }
                )

            transport.send_frame(CAN_ID_QUERY_ERROR_COUNTERS, b"")
            counters = self._wait_for_frame(transport, CAN_ID_ERROR_COUNTERS_RESPONSE, 2)
            if counters is None:
                items.append({"label": "CAN health", "value": "No response", "ok": False})
            else:
                tec, rec = counters[0], counters[1]
                items.append(
                    {
                        "label": "CAN health",
                        "value": f"TEC {tec} / REC {rec}",
                        "ok": tec == 0 and rec == 0,
                    }
                )

            transport.send_frame(CAN_ID_EXPANSION_TYPE_RESP, b"")
            expansion = self._wait_for_frame(transport, CAN_ID_EXPANSION_TYPE_RESP, 1)
            expansion_value = expansion[0] if expansion is not None else -1
            items.append(
                {
                    "label": "Expansion",
                    "value": (
                        EXPANSION_BOARD_TYPES[expansion_value]
                        if 0 <= expansion_value < len(EXPANSION_BOARD_TYPES)
                        else "No response"
                    ),
                    "ok": expansion is not None,
                }
            )

            transport.send_frame(CAN_ID_MLX_VARIANT_RESP, b"")
            mlx = self._wait_for_frame(transport, CAN_ID_MLX_VARIANT_RESP, 1)
            mlx_value = mlx[0] if mlx is not None else -1
            items.append(
                {
                    "label": "MLX sensor",
                    "value": (
                        MLX_SENSOR_VARIANTS[mlx_value]
                        if 0 <= mlx_value < len(MLX_SENSOR_VARIANTS)
                        else "No response"
                    ),
                    "ok": mlx is not None,
                }
            )

            transport.send_frame(CAN_ID_PERIPHERAL_INFO_RESP, b"")
            peripheral = self._wait_for_frame(transport, CAN_ID_PERIPHERAL_INFO_RESP, 2)
            items.append(
                {
                    "label": "Peripheral",
                    "value": (
                        f"type 0x{peripheral[0]:02X} / serial {peripheral[1]}"
                        if peripheral is not None
                        else "No response"
                    ),
                    "ok": peripheral is not None,
                }
            )
            self._snapshotResult.emit(items, "")
        except Exception as exc:
            self._snapshotResult.emit(items, str(exc))

    @Slot(object, str)
    def _on_snapshot_result(self, items: list[dict[str, object]], error: str) -> None:
        self._board_snapshot = items
        candidate, self._recovery_candidate = self._recovery_candidate, ""
        if candidate and not self._selected_firmware and self._flash_target == "master":
            self._selected_firmware = candidate
            self._log(f"RECOVERY_IMAGE_SELECTED {os.path.basename(candidate)}")
        if error:
            self._set_state(status="BOARD STATE FAILED", busy=False)
            self._log(f"BOARD_SNAPSHOT_FAILED {error}")
        else:
            self._set_state(status="BOARD STATE COMPLETE", busy=False)
            self._log(f"BOARD_SNAPSHOT_COMPLETE fields={len(items)}")

    # -- device configuration writes ------------------------------------

    def _run_config_write(self, key: str, request: tuple[int, bytes], response_id: int, min_size: int, extract, expected: object) -> None:
        """Real, generic write-then-confirm worker every one of the 4
        real config writes below shares - send the real SET frame, wait
        up to 1.5s for the board's own real response on response_id,
        extract the real confirmed value from it, and emit it (or None
        on a genuine timeout) through the one shared _configWriteResult
        signal - not 4 near-duplicate workers, mirroring the same real
        pattern already established for URTC-TESTER's own _run_query."""
        transport = self._transport
        if transport is None:
            return
        self._set_state(status=f"SAVING {key.upper()}", busy=True)

        def _worker() -> None:
            try:
                transport.send_frame(*request)
                frame = self._wait_for_frame(transport, response_id, min_size)
                confirmed = extract(frame) if frame is not None else None
                self._configWriteResult.emit(key, confirmed, expected)
            except Exception as exc:
                self._log(f"CONFIG_WRITE_FAILED key={key} error={exc}")
                self._configWriteResult.emit(key, None, expected)

        threading.Thread(target=_worker, daemon=True, name=f"urtc-qt-config-write-{key}").start()

    # Real, pre-existing per-field i18n keys (already used by the
    # earlier Tk window for this exact same real confirmation) -
    # reused here verbatim rather than inventing generic ones, so both
    # UIs show identical, already-translated wording for the same event.
    _CONFIG_WRITE_LABELS = {
        "expansion_type": (EXPANSION_BOARD_TYPES, "LOG_EXPANSION_TYPE_SAVED_CONFIRMED", "LOG_EXPANSION_TYPE_MISMATCH", "LOG_EXPANSION_TYPE_NO_CONFIRMATION"),
        "mlx_variant": (MLX_SENSOR_VARIANTS, "LOG_MLX_VARIANT_SAVED_CONFIRMED", "LOG_MLX_VARIANT_MISMATCH", "LOG_MLX_VARIANT_NO_CONFIRMATION"),
    }

    @Slot(str, object, object)
    def _on_config_write_result(self, key: str, confirmed: object, expected: object) -> None:
        if key in self._CONFIG_WRITE_LABELS:
            labels, confirmed_key, mismatch_key, no_confirm_key = self._CONFIG_WRITE_LABELS[key]
            if confirmed == expected:
                text = _(confirmed_key, type=labels[expected])
            elif confirmed is not None:
                text = _(mismatch_key, value=expected, confirmed=confirmed)
            else:
                text = _(no_confirm_key)
        elif key == "free_tool":
            if confirmed == expected:
                tool_display = _("OPT_FREE_TOOL_NONE") if expected == 0 else f"{expected} - {TOOL_NAMES.get(expected - 1, '?')}"
                text = _("LOG_FREE_TOOL_SAVED_CONFIRMED", tool=tool_display)
            elif confirmed is not None:
                text = _("LOG_FREE_TOOL_MISMATCH", value=expected, confirmed=confirmed)
            else:
                text = _("LOG_FREE_TOOL_NO_CONFIRMATION")
        elif key == "device_serial":
            if confirmed == expected:
                text = _("LOG_DEVICE_SERIAL_SAVED_CONFIRMED", serial=expected)
            elif confirmed is not None:
                text = _("LOG_DEVICE_SERIAL_MISMATCH", value=expected, confirmed=confirmed)
            else:
                text = _("LOG_DEVICE_SERIAL_NO_CONFIRMATION")
        else:
            return
        self._log(f"CONFIG_WRITE key={key} sent={expected} confirmed={confirmed}")
        self._config_write_texts[key] = text
        self._set_state(status="READY", busy=False)

    @Slot(int)
    def saveExpansionBoardType(self, index: int) -> None:
        """QML asks for an explicit confirmation immediately before
        calling this Slot (same real requestConfigWrite pattern as
        every other real persistent write below) - this changes a real,
        persistent EEPROM field on the board."""
        if not self.canWriteDeviceConfig or not 0 <= index < len(EXPANSION_BOARD_TYPES):
            self._log("EXPANSION_TYPE_SAVE_BLOCKED not connected, busy, or index out of range")
            return
        self._run_config_write("expansion_type", (CAN_ID_SET_EXPANSION_TYPE, bytes([index])), CAN_ID_EXPANSION_TYPE_RESP, 1, lambda f: f[0], index)

    @Slot(int)
    def saveMlxSensorVariant(self, index: int) -> None:
        if not self.canWriteDeviceConfig or not 0 <= index < len(MLX_SENSOR_VARIANTS):
            self._log("MLX_VARIANT_SAVE_BLOCKED not connected, busy, or index out of range")
            return
        self._run_config_write("mlx_variant", (CAN_ID_SET_MLX_VARIANT, bytes([index])), CAN_ID_MLX_VARIANT_RESP, 1, lambda f: f[0], index)

    @Slot(int)
    def saveFreeToolConfig(self, selection: int) -> None:
        """selection is the real value already resolved by QML from
        freeToolOptions' own index (0 = none, matching
        the earlier Tk window's own _free_tool_display_to_selection), not a
        raw combo index - see that Property's own docstring."""
        if not self.canWriteDeviceConfig or not 0 <= selection <= len(TOOL_NAMES):
            self._log("FREE_TOOL_SAVE_BLOCKED not connected, busy, or selection out of range")
            return
        # frame[1] is the real resolved selection; frame[0] is the raw
        # ID-jumper reading, not relevant to confirming this write.
        self._run_config_write("free_tool", (CAN_ID_SET_FREE_TOOL, bytes([selection])), CAN_ID_FREE_TOOL_CONFIG_RESP, 2, lambda f: f[1], selection)

    @Slot(int)
    def saveDeviceSerial(self, serial: int) -> None:
        if not self.canWriteDeviceConfig or not 0 <= serial <= 255:
            self._log("DEVICE_SERIAL_SAVE_BLOCKED not connected, busy, or serial out of range (0-255)")
            return
        # Confirms via CAN_ID_PERIPHERAL_INFO_RESP, the same real ID the
        # board snapshot's own peripheral-info read already uses -
        # frame[0] is the fixed peripheral type, not relevant here.
        self._run_config_write("device_serial", (CAN_ID_SET_DEVICE_SERIAL, bytes([serial])), CAN_ID_PERIPHERAL_INFO_RESP, 2, lambda f: f[1], serial)

    @Slot()
    def toggleConnection(self) -> None:
        if self._busy:
            return
        if self._transport is not None:
            try:
                self._transport.close()
            finally:
                self._transport = None
                self._set_state(status="DISCONNECTED")
                self._log("TRANSPORT_DISCONNECTED")
            return
        if not self._selected_port:
            self._log("ERROR select a serial or SocketCAN interface first")
            return
        self._set_state(status="CONNECTING", busy=True)
        threading.Thread(target=self._connect_worker, daemon=True, name="urtc-qt-connect").start()

    def _connect_worker(self) -> None:
        try:
            if self._selected_port in self._socketcan_ports:
                transport = SocketCAN(self._selected_port, log=self._log)
                transport.open_channel()
            else:
                transport = SLCAN(self._selected_port, log=self._log)
                transport.open_channel(self._slcan_bitrate_code())
            self._connectionResult.emit(transport, "")
        except Exception as exc:
            self._connectionResult.emit(None, str(exc))

    def _on_connection_result(self, transport, error: str) -> None:
        self._transport = transport
        if error:
            self._set_state(status="CONNECTION FAILED", busy=False)
            self._log(f"CONNECTION_FAILED {error}")
        else:
            self._set_state(status=f"CONNECTED {self._selected_port}", busy=False)
            self._log(f"TRANSPORT_CONNECTED {self._selected_port}")

    @Slot()
    def confirmCanOtaFlash(self) -> None:
        if not self.canFlash:
            return
        if self._allow_downgrade and not self._downgrade_confirmed:
            self._log("DOWNGRADE_NOT_CONFIRMED")
            return
        options = {
            "target": self._flash_target,
            "trigger": self._trigger_bootloader,
            "erase_fram": self._erase_fram,
            "allow_downgrade": self._allow_downgrade and self._flash_target == "master",
        }
        self._downgrade_confirmed = False  # every flash asks again
        self._cancel_requested = False
        self._progress = 0
        self._transfer_speed_kbps = 0.0
        self._transfer_idle_seconds = 0
        self._transfer_last_update = time.monotonic()
        self._transfer_liveness_timer.start()
        self._flash_path = self._selected_firmware
        self._set_state(status="CAN-OTA IN PROGRESS", busy=True)
        self._log(f"FLASH_STARTED {Path(self._flash_path).name}")
        threading.Thread(
            target=self._flash_worker,
            args=(self._flash_path, options),
            daemon=True,
            name="urtc-qt-flash",
        ).start()

    @Slot()
    def cancelFlash(self) -> None:
        if self._busy:
            self._cancel_requested = True
            self._log("CANCEL_REQUESTED")

    def _flash_worker(self, firmware_path: str, options: dict | None = None) -> None:
        options = {"target": "master", "trigger": True, "erase_fram": False, "allow_downgrade": False, **(options or {})}
        try:
            # A digest published next to the image (<image>.sha256) must match it;
            # without one the digest is only logged so it can be recorded.
            check = preflight_image(firmware_path)
            if check.blocked:
                reasons = "; ".join(check.reasons)
                self._log(f"IMAGE_REFUSED {reasons}")
                raise FlashError(reasons)
            self._log(f"IMAGE_DIGEST_{'VERIFIED' if check.verified else 'RECORDED'} {check.sha256}")
            if check.release_signature in ("signed", "unsigned"):
                self._log(f"IMAGE_RELEASE_{check.release_signature.upper()}")
            flasher = URTCFlasher(
                self._transport, log=self._log, progress_cb=self._flashProgress.emit,
                stop_flag=lambda: self._cancel_requested,
                speed_cb=self._flashSpeed.emit,
            )
            versions = flasher.report_version_change(firmware_path, options["target"])
            if options["target"] == "slave":
                if options["trigger"]:
                    flasher.trigger_slave_bootloader_entry()
                flasher.flash_slave(firmware_path)
            else:
                if options["erase_fram"]:
                    if not options["trigger"]:
                        self._log("FRAM_ERASE_SKIPPED")
                    else:
                        flasher.erase_fram()
                if options["trigger"]:
                    flasher.trigger_bootloader_entry()
                flasher.flash(firmware_path, allow_downgrade=options["allow_downgrade"])
            self._write_update_report(firmware_path, options, check, versions)
            self._flashResult.emit("FLASH_COMPLETE")
        except FlashError as exc:
            self._flashResult.emit(f"FLASH_FAILED {exc}")
        except Exception as exc:
            self._flashResult.emit(f"FLASH_UNEXPECTED {exc}")

    def _write_update_report(self, firmware_path: str, options: dict, check, versions) -> None:
        """Record a finished update next to the session logs (worker thread; a failure never fails the update)."""
        try:
            folder = writable_logs_folder(LOGS_FOLDER)
            if not folder or not versions:
                return
            slave = options["target"] == "slave"
            report = build_update_report(
                tool_version=FLASHER_VERSION, image_path=firmware_path, image_sha256=check.sha256,
                image_size=os.path.getsize(firmware_path), target=options["target"],
                installed=versions["installed"], new=versions["new"],
                hardware_id=SLAVE_HARDWARE_ID if slave else THIS_HARDWARE_ID,
                signing_key_kind=manifest_signing_kind(firmware_path), result="success",
            )
            self._log(f"UPDATE_REPORT_WRITTEN {write_update_report(report, folder)}")
        except (OSError, TypeError, KeyError) as exc:
            self._log(f"UPDATE_REPORT_FAILED {exc}")

    def _on_flash_progress(self, progress: int) -> None:
        self._progress = max(0, min(100, progress))
        self._transfer_last_update = time.monotonic()
        self._transfer_idle_seconds = 0
        self.changed.emit()

    def _on_flash_speed(self, kbps: float) -> None:
        self._transfer_speed_kbps = kbps
        self._transfer_last_update = time.monotonic()
        self._transfer_idle_seconds = 0
        self.changed.emit()

    def _poll_transfer_liveness(self) -> None:
        if self._transfer_last_update is None:
            return
        self._transfer_idle_seconds = int(time.monotonic() - self._transfer_last_update)
        self.changed.emit()

    def _on_flash_result(self, result: str) -> None:
        self._transfer_liveness_timer.stop()
        self._transfer_last_update = None
        if result.startswith("READBACK_"):
            token, _sep, detail = result.partition(" ")
            if token == "READBACK_COMPLETE":
                size, _sep, path = detail.partition(" ")
                self._readback_result = _("MSG_READBACK_COMPLETE", size=size, path=path)
            else:
                self._readback_result = detail
        self._set_state(status=result, busy=False)
        self._log(result)


def run_qtquick() -> int:
    """Run the QML command deck (the program's only window)."""
    # Basic is a portable Qt Quick Controls style with fully customizable
    # QML backgrounds. The platform-native Windows style ignores rounded
    # Rectangle backgrounds, which would undermine the shared Updater look.
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication(sys.argv)
    app.setApplicationName("URTC Flasher")
    icon = QIcon(ICON_IMAGE_PATH)
    if not icon.isNull():
        app.setWindowIcon(icon)
    bridge = FlasherQtBridge()
    bridge.start_session_log()
    app.aboutToQuit.connect(bridge.prepareToQuit)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("flasherBackend", bridge)
    qml_path = Path(__file__).resolve().parent / "assets" / "qml" / "FlasherDeck.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        return 1
    return app.exec()
