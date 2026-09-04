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
import time
from pathlib import Path

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from flasher_config import (
    APP_FLASH_ADDR, APP_MAX_SIZE, BITRATE_500K_SLCAN_CODE,
    CAN_ID_ERROR_COUNTERS_RESPONSE, CAN_ID_EXPANSION_TYPE_RESP,
    CAN_ID_FREE_TOOL_CONFIG_RESP, CAN_ID_MLX_VARIANT_RESP,
    CAN_ID_PERIPHERAL_INFO_RESP, CAN_ID_QUERY_ERROR_COUNTERS,
    CAN_ID_SET_DEVICE_SERIAL, CAN_ID_SET_EXPANSION_TYPE,
    CAN_ID_SET_FREE_TOOL, CAN_ID_SET_MLX_VARIANT,
    EXPANSION_BOARD_TYPES, FIRMWARE_FOLDER,
    FLASHER_VERSION, ICON_IMAGE_PATH, MLX_SENSOR_VARIANTS, TOOL_NAMES, _,
)
from flasher_protocol import FlashError, URTCFlasher
from flasher_swd_tools import CubeProgrammerCLI, PyOCDCLI
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
    _swdProbeResult = Signal("QVariantList")
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
        self._selected_firmware = ""
        self._transport = None
        self._busy = False
        self._progress = 0
        self._status = "READY"
        self._logs: list[str] = []
        self._cancel_requested = False
        self._flash_path = ""
        self._swd_scanning = False
        self._swd_tools: list[dict[str, object]] = []
        self._swd_probes: list[dict[str, str]] = []
        self._board_snapshot: list[dict[str, object]] = []
        self._config_write_texts: dict[str, str] = {
            "expansion_type": "", "mlx_variant": "", "free_tool": "", "device_serial": "",
        }
        self._connectionResult.connect(self._on_connection_result)
        self._flashResult.connect(self._on_flash_result)
        self._flashProgress.connect(self._on_flash_progress)
        self._swdProbeResult.connect(self._on_swd_probe_result)
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
            "QT_SCAN_PROBES": "SCAN PROBES",
            "QT_NOT_INSTALLED": "NOT INSTALLED",
            "QT_NO_PROBES": "No USB debug probe detected.",
            "QT_SWD_SAFETY_NOTE": "Discovery only: no target is erased, written or reset. Full-chip SWD/JTAG programming remains in the established Tkinter workflow until hardware validation.",
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
    def status(self) -> str:
        return self._status

    @Property("QStringList", notify=logChanged)
    def logs(self) -> list[str]:
        return self._logs[-12:]

    @Property(bool, notify=changed)
    def canFlash(self) -> bool:
        return self.connected and bool(self._selected_firmware) and not self._busy

    @Property("QVariantList", notify=changed)
    def swdTools(self) -> list[dict[str, object]]:
        return self._swd_tools

    @Property("QVariantList", notify=changed)
    def swdProbes(self) -> list[dict[str, str]]:
        return self._swd_probes

    @Property(bool, notify=changed)
    def swdScanning(self) -> bool:
        return self._swd_scanning

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
        flasher_gui.py's own _free_tool_display_to_selection)."""
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
                            f"{version['version_minor']} / HW 0x{version['hardware_id']:08X}{suffix}"
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
    # established Tkinter panel for this exact same real confirmation) -
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
        flasher_gui.py's own _free_tool_display_to_selection), not a
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
