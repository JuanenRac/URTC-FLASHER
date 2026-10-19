# =============================================================================
# URTC Flasher - hardware-free check that the Qt Quick deck loads with the
# CAN-OTA options (target, downgrade, firmware backup, bus activity, debug bundle)
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Run directly: QT_QPA_PLATFORM=offscreen python verify_qt_can_options.py

Loads assets/qml/FlasherDeck.qml with the real bridge (no board, no transport) and
checks that the QML compiles, the window object exists and the option properties
the QML binds to behave as the window expects.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from qt_flasher import FlasherQtBridge


def main() -> int:
    QQuickStyle.setStyle("Basic")
    _app = QGuiApplication(sys.argv)  # must stay alive while the engine runs
    bridge = FlasherQtBridge()
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("flasherBackend", bridge)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).resolve().parent / "assets" / "qml" / "FlasherDeck.qml")))
    failures = []
    if not engine.rootObjects():
        failures.append("FlasherDeck.qml did not load")
    if bridge.flashTarget != "master" or bridge.allowDowngrade or bridge.eraseFram or not bridge.triggerBootloader:
        failures.append("unsafe or unexpected defaults")
    bridge.setFlashTarget("slave")
    if bridge.flashTarget != "slave" or bridge.downgradeOptionsAvailable or bridge.canReadback:
        failures.append("the slave target must not offer F-RAM erase, downgrade or backup")
    bridge.setFlashTarget("master")
    bridge.setAllowDowngrade(True)
    if not bridge.allowDowngrade:
        failures.append("the downgrade option could not be armed on the main board")
    for name in ("flashConfirmBody", "downgradeConfirmBody", "aboutText"):
        if not str(getattr(bridge, name)):
            failures.append(f"{name} is empty")
    del engine
    if failures:
        print("FAIL: " + "; ".join(failures))
        return 1
    print("PASS: Qt Quick deck loads; CAN-OTA options behave")
    return 0


if __name__ == "__main__":
    sys.exit(main())
