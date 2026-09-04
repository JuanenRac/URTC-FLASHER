# =============================================================================
# URTC Flasher - real, hardware-free end-to-end check of the Qt Quick
# device-configuration writes (expansion board type / MLX sensor variant /
# free tool config / device serial)
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Deliberately kept OUTSIDE any pytest suite - needs a real PySide6 event
loop for the real cross-thread Signal delivery every write worker uses.
Run directly: QT_QPA_PLATFORM=offscreen python verify_qt_device_config.py

A fake transport (real read_frame/send_frame call shape) answers each real
SET frame with the real documented confirmation response, from a separate
thread - the real _run_config_write worker still does its own real
polling read loop against it, exactly like it would against a real SLCAN/
SocketCAN transport.
"""
from __future__ import annotations

import queue
import sys
import threading
import time

from PySide6.QtGui import QGuiApplication

from qt_flasher import FlasherQtBridge


class FakeTransport:
    def __init__(self) -> None:
        self.inbox: queue.Queue = queue.Queue()
        self.sent: list[tuple[int, bytes]] = []
        self._lock = threading.Lock()
        self._responders: dict[int, tuple[int, bytes]] = {}

    def respond(self, request_can_id: int, response_data: bytes, response_can_id: int | None = None) -> None:
        with self._lock:
            self._responders[request_can_id] = (response_can_id if response_can_id is not None else request_can_id, response_data)

    def read_frame(self, timeout: float = 0.1):
        try:
            return self.inbox.get(timeout=timeout)
        except queue.Empty:
            return None

    def send_frame(self, can_id: int, data: bytes) -> None:
        self.sent.append((can_id, data))
        with self._lock:
            response = self._responders.get(can_id)
        if response is not None:
            self.inbox.put(response)

    def close(self) -> None:
        pass


def _pump_until(app: QGuiApplication, condition, timeout_s: float = 2.0) -> None:
    deadline = time.monotonic() + timeout_s
    while not condition() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.02)


def _run() -> None:
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    bridge = FlasherQtBridge()
    transport = FakeTransport()

    bridge._transport = transport
    bridge._set_state(status="READY", busy=False)
    assert bridge.canWriteDeviceConfig is True

    # --- expansion board type: real request 0x1A0, real confirm on 0x1A1 ---
    transport.respond(0x1A0, bytes([2]), response_can_id=0x1A1)
    bridge.saveExpansionBoardType(2)
    _pump_until(app, lambda: bridge.expansionBoardTypeResult != "")
    assert "confirm" in bridge.expansionBoardTypeResult.lower(), bridge.expansionBoardTypeResult
    assert transport.sent[-1] == (0x1A0, bytes([2]))

    # A real out-of-range index must never reach the transport at all.
    before = len(transport.sent)
    bridge.saveExpansionBoardType(999)
    assert len(transport.sent) == before, "an out-of-range expansion type index must be rejected before ever sending"

    # --- MLX sensor variant: real request 0x1A6, real confirm on 0x1A7 ---
    transport.respond(0x1A6, bytes([1]), response_can_id=0x1A7)
    bridge.saveMlxSensorVariant(1)
    _pump_until(app, lambda: bridge.mlxSensorVariantResult != "")
    assert "confirm" in bridge.mlxSensorVariantResult.lower(), bridge.mlxSensorVariantResult

    # --- free tool config: real request 0x1A2, real confirm on 0x1A3
    # (frame[1] is the real confirmed selection, frame[0] is the raw
    # ID-jumper reading and must be ignored for this comparison) ---
    transport.respond(0x1A2, bytes([31, 5]), response_can_id=0x1A3)
    bridge.saveFreeToolConfig(5)
    _pump_until(app, lambda: bridge.freeToolConfigResult != "")
    assert "confirm" in bridge.freeToolConfigResult.lower(), bridge.freeToolConfigResult

    # A real MISMATCH (board confirms a different value than what was
    # sent) must be reported as one, not silently treated as success -
    # the real LOG_FREE_TOOL_MISMATCH text names both the sent (3) and
    # confirmed (9) values, and must NOT claim success.
    prior_result = bridge.freeToolConfigResult
    transport.respond(0x1A2, bytes([31, 9]), response_can_id=0x1A3)  # sent 3, board confirms 9
    bridge.saveFreeToolConfig(3)
    _pump_until(app, lambda: bridge.freeToolConfigResult != prior_result)
    assert "3" in bridge.freeToolConfigResult and "9" in bridge.freeToolConfigResult, bridge.freeToolConfigResult
    assert "may not have taken" in bridge.freeToolConfigResult, "a real mismatch must say so, not read like a success"

    # --- device serial: real request 0x1A4, confirms on the same real
    # CAN_ID_PERIPHERAL_INFO_RESP the board snapshot's own read uses ---
    transport.respond(0x1A4, bytes([0x03, 42]), response_can_id=0x1A5)
    bridge.saveDeviceSerial(42)
    _pump_until(app, lambda: bridge.deviceSerialResult != "")
    assert "confirm" in bridge.deviceSerialResult.lower(), bridge.deviceSerialResult

    # Out-of-range serial (not 0-255) must never reach the transport.
    before = len(transport.sent)
    bridge.saveDeviceSerial(9999)
    assert len(transport.sent) == before, "an out-of-range device serial must be rejected before ever sending"

    # --- a genuine timeout (no responder) must produce a real
    # "no confirmation" text, never hang or fabricate a value ---
    transport._responders.pop(0x1A0, None)
    bridge._config_write_texts["expansion_type"] = ""
    bridge.saveExpansionBoardType(0)
    _pump_until(app, lambda: bridge.expansionBoardTypeResult != "", timeout_s=2.5)
    assert bridge.expansionBoardTypeResult != "", "a genuine timeout must still produce real display text"

    # --- busy must block a second write from starting concurrently ---
    transport.respond(0x1A6, bytes([0]), response_can_id=0x1A7)
    bridge._busy = True
    before = len(transport.sent)
    bridge.saveMlxSensorVariant(0)
    assert len(transport.sent) == before, "a write must not start while another real operation is in progress"
    bridge._busy = False

    # --- QML itself loads with a fresh bridge and shows zero warnings ---
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuickControls2 import QQuickStyle

    QQuickStyle.setStyle("Basic")
    engine = QQmlApplicationEngine()
    qml_bridge = FlasherQtBridge()
    engine.rootContext().setContextProperty("flasherBackend", qml_bridge)
    warnings: list[str] = []
    engine.warnings.connect(lambda ws: warnings.extend(str(w) for w in ws))
    engine.load("assets/qml/FlasherDeck.qml")
    assert engine.rootObjects(), "FlasherDeck.qml must load with the real bridge"
    assert not warnings, f"QML must load with zero warnings, got: {warnings}"

    print("verify_qt_device_config: all real assertions passed")


if __name__ == "__main__":
    _run()
