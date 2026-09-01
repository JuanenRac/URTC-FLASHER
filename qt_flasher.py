# =============================================================================
# URTC Flasher - Qt Quick CAN-OTA command deck
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Qt Quick front end for the real, safe CAN-OTA workflow.

This is not a second flashing implementation.  It uses the existing SLCAN,
SocketCAN, firmware validation and URTCFlasher protocol classes.  Tkinter
remains the default until the SWD/JTAG and configuration pages reach parity.
"""
from __future__ import annotations

import glob
import os
import sys
import threading
from pathlib import Path

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from flasher_config import APP_FLASH_ADDR, APP_MAX_SIZE, BITRATE_500K_SLCAN_CODE, FIRMWARE_FOLDER, FLASHER_VERSION, ICON_IMAGE_PATH
from flasher_protocol import FlashError, URTCFlasher
from flasher_transports import SLCAN, SocketCAN, list_socketcan_interfaces
from flasher_validation import validate_firmware_file

try:
    import serial.tools.list_ports
    HAVE_SERIAL = True
except ImportError:
    HAVE_SERIAL = False


class FlasherQtBridge(QObject):
    """QML-facing state model over the production CAN-OTA backend."""

    changed = Signal()
    logChanged = Signal()
    _connectionResult = Signal(object, str)
    _flashResult = Signal(str)
    _flashProgress = Signal(int)
    _logRequested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._ports: list[str] = []
        self._socketcan_ports: set[str] = set()
        self._firmware: list[dict[str, object]] = []
        self._selected_port = ""
        self._selected_firmware = ""
        self._transport = None
        self._busy = False
        self._progress = 0
        self._status = "READY"
        self._logs: list[str] = []
        self._cancel_requested = False
        self._flash_path = ""
        self._connectionResult.connect(self._on_connection_result)
        self._flashResult.connect(self._on_flash_result)
        self._flashProgress.connect(self._on_flash_progress)
        self._logRequested.connect(self._append_log)
        self.scanPorts()
        self.scanFirmware()

    @Property(str, constant=True)
    def title(self) -> str:
        return "URTC FLASHER"

    @Property(str, constant=True)
    def version(self) -> str:
        return FLASHER_VERSION

    @Property(str, constant=True)
    def iconSource(self) -> str:
        return QUrl.fromLocalFile(str(Path(ICON_IMAGE_PATH))).toString()

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
    def status(self) -> str:
        return self._status

    @Property("QStringList", notify=logChanged)
    def logs(self) -> list[str]:
        return self._logs[-12:]

    @Property(bool, notify=changed)
    def canFlash(self) -> bool:
        return self.connected and bool(self._selected_firmware) and not self._busy

    def _log(self, message: str) -> None:
        """Queue logs from CAN worker threads onto the Qt GUI thread."""
        self._logRequested.emit(str(message))

    @Slot(str)
    def _append_log(self, message: str) -> None:
        self._logs.append(message)
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
                valid, reason, size = validate_firmware_file(path, APP_FLASH_ADDR, APP_MAX_SIZE)
                entries.append({"name": path.name, "path": str(path), "valid": valid, "reason": reason, "size": size})
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
                transport.open_channel(BITRATE_500K_SLCAN_CODE)
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
        self._cancel_requested = False
        self._progress = 0
        self._flash_path = self._selected_firmware
        self._set_state(status="CAN-OTA IN PROGRESS", busy=True)
        self._log(f"FLASH_STARTED {Path(self._flash_path).name}")
        threading.Thread(
            target=self._flash_worker,
            args=(self._flash_path,),
            daemon=True,
            name="urtc-qt-flash",
        ).start()

    @Slot()
    def cancelFlash(self) -> None:
        if self._busy:
            self._cancel_requested = True
            self._log("CANCEL_REQUESTED")

    def _flash_worker(self, firmware_path: str) -> None:
        try:
            flasher = URTCFlasher(
                self._transport, log=self._log, progress_cb=self._flashProgress.emit,
                stop_flag=lambda: self._cancel_requested,
            )
            flasher.trigger_bootloader_entry()
            flasher.flash(firmware_path)
            self._flashResult.emit("FLASH_COMPLETE")
        except FlashError as exc:
            self._flashResult.emit(f"FLASH_FAILED {exc}")
        except Exception as exc:
            self._flashResult.emit(f"FLASH_UNEXPECTED {exc}")

    def _on_flash_progress(self, progress: int) -> None:
        self._progress = max(0, min(100, progress))
        self.changed.emit()

    def _on_flash_result(self, result: str) -> None:
        self._set_state(status=result, busy=False)
        self._log(result)


def run_qtquick() -> int:
    """Run the QML command deck explicitly selected through ``--qtquick``."""
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
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("flasherBackend", bridge)
    qml_path = Path(__file__).resolve().parent / "assets" / "qml" / "FlasherDeck.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        return 1
    return app.exec()
