# =============================================================================
# URTC Flasher - tests/test_qml_deck_loads.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The Qt Quick deck loads as the program loads it (offscreen) without a single QML error or warning, and every member of the backend that the QML uses exists on the bridge,
so a renamed slot or a typo in the QML shows up here and not as a dead button on the bench. The load runs in its own process: Qt keeps global state (the application, the style)
that the other tests of the run have already set."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

pytest.importorskip("PySide6")
import qt_flasher  # noqa: E402

DECK = ROOT / "assets" / "qml" / "FlasherDeck.qml"
CONTEXT_NAME = "flasherBackend"

LOADER = """
import json, sys
sys.path.insert(0, sys.argv[1])
from PySide6.QtCore import QUrl, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
import qt_flasher
QQuickStyle.setStyle("Basic")
app = QGuiApplication([])
messages = []
qInstallMessageHandler(lambda mode, context, message: messages.append(message))
bridge = qt_flasher.FlasherQtBridge()
engine = QQmlApplicationEngine()
engine.rootContext().setContextProperty(sys.argv[3], bridge)
engine.load(QUrl.fromLocalFile(sys.argv[2]))
print("RESULT " + json.dumps({"loaded": bool(engine.rootObjects()), "messages": messages}))
sys.stdout.flush()
import os
os._exit(0)
"""


def test_the_deck_loads_without_qml_errors_or_warnings():
    environment = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    done = subprocess.run([sys.executable, "-c", LOADER, str(ROOT), str(DECK), CONTEXT_NAME], capture_output=True, text=True, env=environment, timeout=120, cwd=str(ROOT))
    line = next((l for l in done.stdout.splitlines() if l.startswith("RESULT ")), None)
    assert line is not None, done.stderr[-2000:]
    result = json.loads(line[len("RESULT "):])
    assert result["loaded"], result["messages"]
    problems = [m for m in result["messages"] if ".qml" in m or "QML" in m or "qrc:" in m]
    assert problems == []


def test_every_backend_member_the_qml_uses_exists_on_the_bridge():
    source = DECK.read_text(encoding="utf-8")
    used = set(re.findall(CONTEXT_NAME + r"\.([A-Za-z_]\w*)", source))
    assert len(used) > 20  # the scan found the deck's calls
    missing = sorted(name for name in used if not hasattr(qt_flasher.FlasherQtBridge, name))
    assert missing == []
