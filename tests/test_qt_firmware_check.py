# =============================================================================
# URTC Flasher - the Qt Quick deck compares firmware/ with the newest official release
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
import tempfile
import time
import unittest
from unittest import mock

try:
    import qt_flasher
except ImportError:  # PySide6 is not installed
    qt_flasher = None

from urtc_can import firmware_check as fc


class Inline:
    """Runs the thread body at once so the test needs no waiting."""

    def __init__(self, target=None, args=(), **kwargs):
        self.target, self.args = target, args

    def start(self):
        self.target(*self.args)


@unittest.skipIf(qt_flasher is None, "PySide6 is not available")
class QtFirmwareCheckTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.bridge = qt_flasher.FlasherQtBridge()
        self.logs = []
        self.bridge._log = self.logs.append
        self.answer = None
        self.calls = []

        def fake_check(local, fetch=None, cache_file=None, now=None, force=False):
            self.calls.append(dict(local))
            if isinstance(self.answer, Exception):
                raise self.answer
            return self.answer

        for patch in (
            mock.patch.object(qt_flasher, "FIRMWARE_FOLDER", self.folder.name),
            mock.patch.object(fc, "check", fake_check),
            mock.patch.object(qt_flasher.update_service, "default_root", lambda name: self.folder.name),
            mock.patch.object(qt_flasher.threading, "Thread", Inline),
        ):
            patch.start()
            self.addCleanup(patch.stop)

    def _release(self, state):
        rows = [fc.Row("MAIN", "FIRMWARE", "0.4.4", "0.4.5", state)]
        return fc.LatestRelease("v0.4.5", {("MAIN", "FIRMWARE"): "0.4.5"}, time.time()), rows

    def test_nothing_is_asked_until_the_person_presses_the_button(self):
        self.assertEqual(self.bridge.firmwareCheckLines, [])
        self.assertFalse(self.bridge.firmwareChecking)
        self.assertEqual(self.calls, [])

    def test_an_older_image_is_reported_in_the_language_of_the_deck(self):
        self.answer = self._release(fc.OUTDATED)
        self.bridge.checkFirmwareNewer()
        lines = self.bridge.firmwareCheckLines
        self.assertEqual(len(lines), 1)
        self.assertIn("0.4.4", lines[0])
        self.assertIn("0.4.5", lines[0])
        self.assertFalse(self.bridge.firmwareChecking)
        self.assertEqual(len(self.calls), 1)

    def test_a_failed_check_is_reported_not_raised(self):
        self.answer = fc.FirmwareCheckError("network", "offline")
        self.bridge.checkFirmwareNewer()
        self.assertEqual(len(self.bridge.firmwareCheckLines), 1)
        self.assertTrue(self.bridge.firmwareCheckLines[0])
        self.assertFalse(self.bridge.firmwareChecking)
        self.assertTrue(any(line.startswith("GITHUB_FAILED") for line in self.logs))

    def test_an_unexpected_failure_never_crashes_the_deck(self):
        self.answer = RuntimeError("boom")
        self.bridge.checkFirmwareNewer()
        self.assertFalse(self.bridge.firmwareChecking)
        self.assertIn("boom", self.bridge.firmwareCheckLines[0])

    def test_a_check_in_progress_is_not_started_twice(self):
        self.bridge._firmware_checking = True
        self.bridge.checkFirmwareNewer()
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
