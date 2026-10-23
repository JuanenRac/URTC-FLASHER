#!/usr/bin/env python3
# =============================================================================
# URTC - tools/capture_screens.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Takes the pictures of the window that the guide in docs/ shows: the real Qt Quick deck, loaded without a screen (``QT_QPA_PLATFORM=offscreen``) and
drawn to a PNG with ``grabWindow``. No board is needed and nothing is sent: the window is shown at rest, as it opens, in English.

    python tools/capture_screens.py                 # writes docs/screenshots/<program>-deck.png, -help.png and -updates.png
    python tools/capture_screens.py --out DIR       # another folder

The same file is in the flasher and in the tester; it finds out which one it is in. The pictures use the Basic style of Qt Quick Controls, the one the
programs run with, and, on Windows, the fonts of the system (an offscreen Qt has none of its own there).
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if sys.platform == "win32":
    os.environ.setdefault("QT_QPA_FONTDIR", os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "Fonts"))

PROGRAMS = {
    "flasher": {"module": "qt_flasher", "bridge": "FlasherQtBridge", "context": "flasherBackend", "deck": "FlasherDeck.qml"},
    "tester": {"module": "qt_tester", "bridge": "TesterQtBridge", "context": "testerBackend", "deck": "TesterDeck.qml"},
}
SIZE = (1440, 900)


def which_program() -> str:
    return "flasher" if (ROOT / "qt_flasher.py").is_file() else "tester"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=str(ROOT / "docs" / "screenshots"))
    args = parser.parse_args(argv)
    name = which_program()
    spec = PROGRAMS[name]
    sys.path.insert(0, str(ROOT))
    os.chdir(tempfile.mkdtemp(prefix="urtc_capture_"))  # the program writes its small files next to where it runs: not into the repository

    import importlib

    from PySide6.QtCore import QMetaObject, QObject, Qt, QUrl
    from PySide6.QtGui import QGuiApplication, QWindow
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuick import QQuickWindow
    from PySide6.QtQuickControls2 import QQuickStyle

    module = importlib.import_module(spec["module"])
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication([])
    bridge = getattr(module, spec["bridge"])()
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty(spec["context"], bridge)
    engine.load(QUrl.fromLocalFile(str(ROOT / "assets" / "qml" / spec["deck"])))
    if not engine.rootObjects():
        print("CAPTURE=FAIL the deck did not load", file=sys.stderr)
        return 1
    root = engine.rootObjects()[0]

    def pump(seconds: float) -> None:
        end = time.time() + seconds
        while time.time() < end:
            app.processEvents()
            time.sleep(0.01)

    root.setVisibility(QWindow.Visibility.Windowed)
    root.setWidth(SIZE[0])
    root.setHeight(SIZE[1])
    pump(1.0)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    written = []

    def shot(label: str) -> None:
        image = QQuickWindow.grabWindow(root)
        path = out / f"{name}-{label}.png"
        if not image.save(str(path)):
            raise SystemExit(f"CAPTURE=FAIL could not write {path}")
        written.append(path.name)

    shot("deck")
    for dialog_name, label in (("helpDialog", "help"), ("updateDialog", "updates")):
        dialog = root.findChild(QObject, dialog_name)
        if dialog is None:
            raise SystemExit(f"CAPTURE=FAIL no {dialog_name} in the deck")
        QMetaObject.invokeMethod(dialog, "open", Qt.ConnectionType.DirectConnection)
        pump(0.8)
        shot(label)
        QMetaObject.invokeMethod(dialog, "close", Qt.ConnectionType.DirectConnection)
        pump(0.3)
    print("CAPTURE=PASS " + ", ".join(written))
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    raise SystemExit(main())
