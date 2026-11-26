# =============================================================================
# URTC Flasher - the Qt Quick deck fits its window: no control is cut off at the right edge, in any of the eight languages
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""A row that cannot wrap (several long check boxes, or fields and buttons side by side) makes the whole scrolled column as wide as that row, and every
control of the column - the cancel and backup buttons among them - ends beyond the window. Each language is loaded in its own process, headless."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

try:
    import PySide6
except ImportError:  # PySide6 is not installed
    PySide6 = None

LANGUAGES = ("english", "spanish", "german", "french", "italian", "japanese", "chinese", "portuguese")

PROBE = r"""
import importlib, os, sys, time
root_folder, language = sys.argv[1], sys.argv[2]
sys.path.insert(0, root_folder)
from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication, QWindow
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
config = importlib.import_module("flasher_config")
if language != "english":
    config._current_language = language
    config._translations = config.load_language(language)
module = importlib.import_module("qt_flasher")
if hasattr(module, "_current_language"):
    module._current_language = language
QQuickStyle.setStyle("Basic")
app = QGuiApplication([])
bridge = module.FlasherQtBridge()
engine = QQmlApplicationEngine()
engine.rootContext().setContextProperty("flasherBackend", bridge)
engine.load(QUrl.fromLocalFile(os.path.join(root_folder, "assets", "qml", "FlasherDeck.qml")))
if not engine.rootObjects():
    raise SystemExit("the deck did not load")
window = engine.rootObjects()[0]
window.setVisibility(QWindow.Visibility.Windowed)


def pump(seconds):
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents()
        time.sleep(0.01)


def cut(item, found):
    if not item.isVisible():
        return
    right = item.mapToScene(item.boundingRect().topRight()).x()
    if right > window.width() + 1:
        text = item.property("text")
        found.append("%s right=%d %s" % (item.metaObject().className().split("_QML")[0], right, ascii(text[:40]) if isinstance(text, str) else ""))
        return
    for child in item.childItems():
        cut(child, found)


problems = []
for width in (1080, 1440, 1920):  # the smallest and the starting width of the settings file, and a full screen
    window.setWidth(width)
    window.setHeight(900)
    pump(0.6)
    found = []
    cut(window.contentItem(), found)
    if found:
        problems.append("width %d: %d cut off, first %s" % (width, len(found), found[:4]))
print("\n".join(problems) or "FITS")
sys.stdout.flush()
os._exit(0)
"""


@unittest.skipIf(PySide6 is None, "PySide6 is not available")
class DeckFitsItsWindowTests(unittest.TestCase):
    def test_no_control_is_cut_off_in_any_language(self):
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen", PYTHONDONTWRITEBYTECODE="1")
        if sys.platform == "win32":  # an offscreen Qt has no fonts of its own there
            env.setdefault("QT_QPA_FONTDIR", os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "Fonts"))
        for language in LANGUAGES:
            with self.subTest(language=language), tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
                result = subprocess.run([sys.executable, "-c", PROBE, str(ROOT), language], cwd=folder, env=env, capture_output=True, text=True, timeout=120)
                self.assertEqual(result.returncode, 0, result.stderr[-2000:])
                self.assertEqual(result.stdout.strip(), "FITS")


if __name__ == "__main__":
    unittest.main()
