#!/usr/bin/env python3
# =============================================================================
# URTC - tools/capture_screens.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Takes the pictures of the window that the guide in docs/ shows: the real Qt Quick deck, loaded without a screen (``QT_QPA_PLATFORM=offscreen``) and
drawn to a PNG with ``grabWindow``. No board is needed and nothing is sent: the window is shown at rest, as it opens, in English. The picture of the
window of the tool heads (``-heads``) is taken over a modelled bus of seven heads, one in each state a head can be in; it shows the window, not a bus. The picture of the History
window (``-history``) is taken over four sample evidence records and a trust store with one key, so the Signature column shows each of its states.

    python tools/capture_screens.py                 # writes docs/screenshots/<program>-deck.png, -help.png, -updates.png, -heads.png and -history.png
    python tools/capture_screens.py --readme                 # the pictures of the README: images/screenshots/<screen>.png at 1920x1080
    python tools/capture_screens.py --out DIR       # another folder
    python tools/capture_screens.py --language german        # the same pictures in German: <program>-deck-de.png ...
    python tools/capture_screens.py --all-languages          # the English ones and those of the seven other languages

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
    "flasher": {"module": "qt_flasher", "bridge": "FlasherQtBridge", "context": "flasherBackend", "deck": "FlasherDeck.qml", "config": "flasher_config"},
    "tester": {"module": "qt_tester", "bridge": "TesterQtBridge", "context": "testerBackend", "deck": "TesterDeck.qml", "config": "tester_config"},
}
SIZE = (1440, 900)
# the language code the program stores -> the suffix of the picture (English has none)
LANGUAGE_SUFFIX = {"english": "", "spanish": "-es", "german": "-de", "french": "-fr", "italian": "-it", "japanese": "-ja", "chinese": "-zh",
                   "portuguese": "-pt"}


def prepare_heads(bridge) -> None:
    """Give the window of the tool heads a modelled bus: 2 selected and confirmed, 5 in conflict (two boards), 9 with a fault latched, 12 in its
    bootloader, 14 lost, 17 ready. Everything runs in place (no thread) and on the clock of the model."""
    from urtc_can import node_picker, protocol

    picker, bus = node_picker.sim_picker((2, 5, 5, 9, 12, 14, 17), config={"stored": 1, "running": 1})
    bus.nodes[2].serial = 0x77
    bus.nodes[3].fault = True
    bus.nodes[3].status_now = True
    model = bridge.nodes
    model._sync = True
    model.attach(picker)
    model.find()
    model.ask(2)
    model.confirm()
    bus.nodes[5].enabled = False
    for _ in range((protocol.MN_NODE_TIMEOUT_MS + 300) // 10):
        bus.step(10)
        picker.tick()
    picker.host.table.nodes[12].state |= protocol.MN_STATE_BOOTLOADER
    model._refresh()


def prepare_history(module, config) -> None:
    """Points the program at a folder of four sample evidence records, so the History window has something to show: one signed by a key the trust store lists,
    one signed by another key, one not signed and one edited after it was signed. The keys are fixed test keys (RFC 8032), the records say they are samples,
    and nothing is written outside a temporary folder."""
    import json

    from urtc_can import evidence, record_signing

    seeds = {"ana": bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60"),
             "other": bytes.fromhex("4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb")}
    folder = Path(tempfile.mkdtemp(prefix="urtc_capture_history_"))

    def record(day: int, name: str, outcome: str = "pass") -> dict:
        return evidence.build(kind="test", outcome=outcome, timestamp_utc=f"2026-01-{day:02d}T10:00:00Z", tool="Sample", tool_version="1.0.0",
                              subject={"name": name, "version_after": "1.0.0"}, detail="a sample record for the picture")

    edited = record_signing.sign_evidence(record(4, "bench-4"), seeds["ana"])
    edited["outcome"] = "fail"
    items = {"a": record_signing.sign_evidence(record(1, "bench-1"), seeds["ana"]), "b": record_signing.sign_evidence(record(2, "bench-2"), seeds["other"]),
             "c": record(3, "bench-3"), "d": edited}
    for key, item in items.items():
        (folder / f"urtc_evidence_{key}.json").write_text(json.dumps(item), encoding="utf-8")
    config.LOGS_FOLDER = str(folder)
    if hasattr(module, "LOGS_FOLDER"):
        module.LOGS_FOLDER = str(folder)
    store = {"trusted_keys": {"Ana bench 1": record_signing.public_key(seeds["ana"]).hex()}}
    config.load_config = lambda: dict(store)

    # the window prints the folder it reads: the picture says "logs", not the temporary folder of this computer
    from urtc_can import evidence_history_qt

    original = evidence_history_qt.EvidenceHistoryModel.t

    def text(self, key, **values):
        if key == "EH_FOLDER":
            values["folder"] = "logs"
        return original(self, key, **values)

    evidence_history_qt.EvidenceHistoryModel.t = text


def which_program() -> str:
    return "flasher" if (ROOT / "qt_flasher.py").is_file() else "tester"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=str(ROOT / "docs" / "screenshots"))
    parser.add_argument("--readme", action="store_true", help="the pictures of the README: 1920x1080, in images/screenshots/, named after the screen only")
    parser.add_argument("--language", choices=sorted(LANGUAGE_SUFFIX), default="english", help="the interface language of the pictures")
    parser.add_argument("--all-languages", action="store_true", help="one run per language (each in its own process)")
    args = parser.parse_args(argv)
    if args.all_languages:
        import subprocess

        for code in LANGUAGE_SUFFIX:
            result = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--language", code, "--out", args.out], check=False)
            if result.returncode != 0:
                return result.returncode
        return 0
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
    if args.language != "english":
        # the program reads its language from its configuration file when it is imported: switch the texts and the copies of the code
        config = importlib.import_module(spec["config"])
        config._current_language = args.language
        config._translations = config.load_language(args.language)
        if hasattr(module, "_current_language"):
            module._current_language = args.language
    prepare_history(module, importlib.import_module(spec["config"]))
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
    size = (1920, 1080) if args.readme else SIZE
    root.setWidth(size[0])
    root.setHeight(size[1])
    pump(1.0)
    out = Path(args.out) if not args.readme or args.out != str(ROOT / "docs" / "screenshots") else ROOT / "images" / "screenshots"
    out.mkdir(parents=True, exist_ok=True)
    written = []

    def shot(label: str) -> None:
        image = QQuickWindow.grabWindow(root)
        path = out / (f"{label}.png" if args.readme else f"{name}-{label}{LANGUAGE_SUFFIX[args.language]}.png")
        if not image.save(str(path)):
            raise SystemExit(f"CAPTURE=FAIL could not write {path}")
        written.append(path.name)

    shot("deck")
    for dialog_name, label in (("helpDialog", "help"), ("updateDialog", "updates"), ("nodeDialog", "heads"), ("historyDialog", "history")):
        dialog = root.findChild(QObject, dialog_name)
        if dialog is None:
            raise SystemExit(f"CAPTURE=FAIL no {dialog_name} in the deck")
        if label == "heads":
            prepare_heads(bridge)
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
