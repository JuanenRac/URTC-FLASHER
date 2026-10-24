# =============================================================================
# URTC Flasher - Qt Quick deck: files picked by hand, signing warning, session log, closing
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
from __future__ import annotations

import os
import tempfile
import unittest
from unittest import mock

try:
    import qt_flasher
except ImportError:  # PySide6 is not installed
    qt_flasher = None


@unittest.skipIf(qt_flasher is None, "PySide6 is not available")
class QtFirmwareFilesTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.bridge = qt_flasher.FlasherQtBridge()
        self.logs: list[str] = []
        self.bridge._log = self.logs.append
        self.image = os.path.join(self.folder.name, "picked.bin")
        with open(self.image, "wb") as stream:
            stream.write(b"\x00" * 16)

    def _validation(self, valid, reason="ok"):
        return mock.patch.object(qt_flasher, "validate_firmware_file", lambda path, addr, size: (valid, reason, 16))

    def test_a_valid_file_from_anywhere_is_listed_and_selected(self):
        with self._validation(True):
            self.bridge.addFirmwareFile(self.image)
        self.assertEqual(self.bridge.selectedFirmware, self.image)
        self.assertIn(self.image, [item["path"] for item in self.bridge.firmware])
        self.assertEqual(self.bridge.invalidFirmwareReason, "")

    def test_the_file_stays_listed_after_a_rescan(self):
        with self._validation(True):
            self.bridge.addFirmwareFile(self.image)
            self.bridge.scanFirmware()
        self.assertIn(self.image, [item["path"] for item in self.bridge.firmware])
        self.assertEqual(self.bridge.selectedFirmware, self.image)

    def test_a_file_that_looks_invalid_waits_for_confirmation_and_is_not_selected(self):
        with self._validation(False, "wrong address"):
            self.bridge.addFirmwareFile(self.image)
        self.assertNotEqual(self.bridge.selectedFirmware, self.image)
        self.assertIn("wrong address", self.bridge.invalidFirmwareReason)

    def test_confirming_selects_it_and_rejecting_forgets_it(self):
        with self._validation(False, "wrong address"):
            self.bridge.addFirmwareFile(self.image)
            self.bridge.acceptInvalidFirmware()
        self.assertEqual(self.bridge.selectedFirmware, self.image)
        self.assertEqual(self.bridge.invalidFirmwareReason, "")
        self.assertTrue(any(line.startswith("FIRMWARE_SELECTED_DESPITE_WARNING") for line in self.logs))
        other = os.path.join(self.folder.name, "other.bin")
        with open(other, "wb") as stream:
            stream.write(b"\x00")
        with self._validation(False, "too big"):
            self.bridge.addFirmwareFile(other)
            self.bridge.rejectInvalidFirmware()
            self.bridge.acceptInvalidFirmware()
        self.assertEqual(self.bridge.selectedFirmware, self.image)

    def test_a_missing_file_or_a_busy_deck_changes_nothing(self):
        with self._validation(True):
            self.bridge.addFirmwareFile(os.path.join(self.folder.name, "missing.bin"))
            self.bridge._busy = True
            self.bridge.addFirmwareFile(self.image)
        self.assertNotEqual(self.bridge.selectedFirmware, self.image)

    def test_a_file_url_from_the_dialog_is_accepted(self):
        from PySide6.QtCore import QUrl

        with self._validation(True):
            self.bridge.addFirmwareFile(QUrl.fromLocalFile(self.image).toString())
        self.assertEqual(self.bridge.selectedFirmware, self.image)

    # -- signing warning --------------------------------------------------
    def test_a_development_key_image_shows_the_warning_and_a_production_one_does_not(self):
        self.bridge._selected_firmware = self.image
        with mock.patch.object(qt_flasher, "manifest_signing_kind", lambda path: "dev"):
            warning = self.bridge.signingWarning
        self.assertTrue(warning)
        with mock.patch.object(qt_flasher, "manifest_signing_kind", lambda path: "production"):
            self.assertEqual(self.bridge.signingWarning, "")
        self.bridge._selected_firmware = ""
        self.assertEqual(self.bridge.signingWarning, "")

    def test_the_warning_says_the_image_will_be_refused_when_production_signing_is_required(self):
        self.bridge._selected_firmware = self.image
        with mock.patch.object(qt_flasher, "manifest_signing_kind", lambda path: "dev"):
            plain = self.bridge.signingWarning
            with mock.patch.object(qt_flasher, "REQUIRE_PRODUCTION_SIGNATURE", True):
                strict = self.bridge.signingWarning
        self.assertNotEqual(plain, strict)

    # -- session log and closing -----------------------------------------------
    def test_the_session_log_file_receives_every_line_and_is_closed_on_quit(self):
        bridge = qt_flasher.FlasherQtBridge()
        with mock.patch.object(qt_flasher, "writable_logs_folder", lambda folder: self.folder.name):
            bridge.start_session_log()
        bridge._append_log("PORT_SCAN count=0")
        files = [name for name in os.listdir(self.folder.name) if name.startswith("urtc_flasher_")]
        self.assertEqual(len(files), 1)
        bridge.prepareToQuit()
        with open(os.path.join(self.folder.name, files[0]), encoding="utf-8") as stream:
            text = stream.read()
        self.assertIn("session started", text)
        self.assertIn("count=0", text)
        self.assertEqual(bridge._file_logger.handlers, [])

    def test_the_deck_writes_no_log_file_unless_the_program_asks_for_one(self):
        bridge = qt_flasher.FlasherQtBridge()
        self.assertIsNone(bridge._file_logger)

    def test_quitting_cancels_a_transfer_and_releases_the_adapter(self):
        closed = []
        self.bridge._transport = mock.Mock(close=lambda: closed.append(True))
        self.bridge.prepareToQuit()
        self.assertTrue(self.bridge._cancel_requested)
        self.assertEqual(closed, [True])
        self.assertIsNone(self.bridge._transport)

    def test_a_failing_adapter_close_does_not_stop_the_quit(self):
        def boom():
            raise OSError("gone")

        self.bridge._transport = mock.Mock(close=boom)
        self.bridge.prepareToQuit()
        self.assertIsNone(self.bridge._transport)

    def test_the_close_prompt_texts_exist(self):
        self.assertTrue(self.bridge.closeWhileBusyTitle and self.bridge.closeWhileBusyBody)
        self.assertNotEqual(self.bridge.closeWhileBusyTitle, "TITLE_FLASH_IN_PROGRESS")


if __name__ == "__main__":
    unittest.main()


@unittest.skipIf(qt_flasher is None, "PySide6 is not available")
class FirmwareArgumentTests(unittest.TestCase):
    def test_the_image_handed_over_on_the_command_line_is_read(self):
        self.assertEqual(qt_flasher.firmware_argument(["--firmware", "a.bin"]), "a.bin")
        self.assertEqual(qt_flasher.firmware_argument(["--qtquick", "--firmware=b c.bin"]), "b c.bin")
        self.assertEqual(qt_flasher.firmware_argument(["--firmware"]), "")
        self.assertEqual(qt_flasher.firmware_argument([]), "")
