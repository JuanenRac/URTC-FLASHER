# =============================================================================
# URTC Flasher - Qt Quick CAN-OTA options: slave target, downgrade, firmware backup
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The options of the CAN-OTA window, checked with fake boards (no hardware)."""
from __future__ import annotations

import os
import types
import unittest
import zipfile
from unittest import mock

try:
    import qt_flasher
except ImportError:  # PySide6 is not installed
    qt_flasher = None


class FakeFlasher:
    """Records what the worker asks the protocol class to do."""

    calls: list = []

    def __init__(self, transport, log=None, progress_cb=None, stop_flag=None, speed_cb=None):
        self.log = log

    def report_version_change(self, path, target="master"):
        FakeFlasher.calls.append(("report", target))
        return {"installed": (1, 0), "new": (1, 1), "downgrade": False}

    def trigger_bootloader_entry(self):
        FakeFlasher.calls.append("trigger")

    def trigger_slave_bootloader_entry(self):
        FakeFlasher.calls.append("trigger_slave")

    def erase_fram(self):
        FakeFlasher.calls.append("erase_fram")

    def flash(self, path, allow_downgrade=False):
        FakeFlasher.calls.append(("flash", allow_downgrade))

    def flash_slave(self, path):
        FakeFlasher.calls.append("flash_slave")

    def read_back_flash(self, path):
        FakeFlasher.calls.append(("readback", path))
        with open(path, "wb") as stream:
            stream.write(b"\x01" * 16)
        return 16


def _check(blocked=False):
    return types.SimpleNamespace(blocked=blocked, reasons=[], verified=False, sha256="0" * 64, release_signature="")


@unittest.skipIf(qt_flasher is None, "PySide6 is not available")
class QtFlashOptionsTests(unittest.TestCase):
    def setUp(self):
        FakeFlasher.calls = []
        patches = [
            mock.patch.object(qt_flasher, "URTCFlasher", FakeFlasher),
            mock.patch.object(qt_flasher, "preflight_image", lambda path: _check()),
            mock.patch.object(qt_flasher, "writable_logs_folder", lambda folder: None),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.bridge = qt_flasher.FlasherQtBridge()
        self.logs: list[str] = []
        self.results: list[str] = []
        self.bridge._log = self.logs.append  # the real one queues onto the GUI thread
        self.bridge._flashResult.connect(self.results.append)
        self.bridge._transport = object()
        self.bridge._selected_firmware = "image.bin"

    def _run(self, **options):
        self.bridge._flash_worker("image.bin", options)

    # -- target -----------------------------------------------------------
    def test_the_main_board_is_the_default_target(self):
        self.assertEqual(self.bridge.flashTarget, "master")
        self.assertTrue(self.bridge.downgradeOptionsAvailable)
        self.assertTrue(self.bridge.triggerBootloader)
        self.assertFalse(self.bridge.eraseFram)
        self.assertFalse(self.bridge.allowDowngrade)

    def test_choosing_the_slave_drops_the_main_board_only_options_and_the_selected_image(self):
        self.bridge.setEraseFram(True)
        self.bridge.setAllowDowngrade(True)
        self.bridge.setFlashTarget("slave")
        self.assertEqual(self.bridge.flashTarget, "slave")
        self.assertFalse(self.bridge.eraseFram)
        self.assertFalse(self.bridge.allowDowngrade)
        self.assertFalse(self.bridge.downgradeOptionsAvailable)
        self.assertNotEqual(self.bridge.selectedFirmware, "image.bin")  # the old choice was for the other slot
        self.bridge.setEraseFram(True)
        self.bridge.setAllowDowngrade(True)
        self.assertFalse(self.bridge.eraseFram)
        self.assertFalse(self.bridge.allowDowngrade)

    def test_an_unknown_target_or_a_change_while_busy_is_ignored(self):
        self.bridge.setFlashTarget("other")
        self.assertEqual(self.bridge.flashTarget, "master")
        self.bridge._busy = True
        self.bridge.setFlashTarget("slave")
        self.assertEqual(self.bridge.flashTarget, "master")

    def test_images_are_checked_against_the_slot_of_the_chosen_target(self):
        seen = []
        with mock.patch.object(qt_flasher, "validate_firmware_file", lambda path, addr, size: seen.append((addr, size)) or (True, "ok", 4)), \
                mock.patch.object(qt_flasher.glob, "glob", lambda pattern: ["x.bin"]), \
                mock.patch.object(qt_flasher.Path, "is_dir", lambda self: True):
            self.bridge.scanFirmware()
            self.bridge.setFlashTarget("slave")
        self.assertEqual(seen[0], (qt_flasher.APP_FLASH_ADDR, qt_flasher.APP_MAX_SIZE))
        self.assertEqual(seen[-1], (qt_flasher.SLAVE_APP_FLASH_ADDR, qt_flasher.SLAVE_APP_MAX_SIZE))

    def test_the_confirmation_names_the_target(self):
        main = self.bridge.flashConfirmBody
        self.bridge.setFlashTarget("slave")
        self.assertNotEqual(main, self.bridge.flashConfirmBody)

    # -- worker -----------------------------------------------------------
    def test_a_main_board_update_enters_the_bootloader_then_flashes_without_downgrade(self):
        self._run()
        self.assertEqual(FakeFlasher.calls, [("report", "master"), "trigger", ("flash", False)])
        self.assertEqual(self.results, ["FLASH_COMPLETE"])

    def test_a_slave_update_uses_the_slave_path(self):
        self._run(target="slave")
        self.assertEqual(FakeFlasher.calls, [("report", "slave"), "trigger_slave", "flash_slave"])

    def test_without_the_trigger_option_the_board_is_assumed_to_be_in_its_bootloader(self):
        self._run(trigger=False)
        self.assertEqual(FakeFlasher.calls, [("report", "master"), ("flash", False)])

    def test_fram_is_erased_before_the_flash_only_when_the_bootloader_entry_is_requested(self):
        self._run(erase_fram=True)
        self.assertEqual(FakeFlasher.calls, [("report", "master"), "erase_fram", "trigger", ("flash", False)])
        FakeFlasher.calls = []
        self._run(erase_fram=True, trigger=False)
        self.assertNotIn("erase_fram", FakeFlasher.calls)
        self.assertTrue(any(line.startswith("FRAM_ERASE_SKIPPED") for line in self.logs))

    def test_the_downgrade_flag_reaches_the_protocol(self):
        self._run(allow_downgrade=True)
        self.assertIn(("flash", True), FakeFlasher.calls)

    def test_a_refused_image_stops_before_any_protocol_call(self):
        with mock.patch.object(qt_flasher, "preflight_image", lambda path: _check(blocked=True)):
            self._run()
        self.assertEqual(FakeFlasher.calls, [])
        self.assertTrue(self.results[0].startswith("FLASH_FAILED"))

    # -- the second confirmation of a downgrade ---------------------------
    def _spy_threads(self):
        started = []

        class Spy:
            def __init__(self, target=None, args=(), **kwargs):
                started.append((target.__name__, args))

            def start(self):
                pass

        return started, mock.patch.object(qt_flasher.threading, "Thread", Spy)

    def test_a_downgrade_does_not_start_without_its_own_confirmation(self):
        self.bridge._busy = False
        self.bridge._transport = types.SimpleNamespace()
        self.bridge.setAllowDowngrade(True)
        started, patch = self._spy_threads()
        with patch, mock.patch.object(type(self.bridge), "connected", True):
            self.bridge.confirmCanOtaFlash()
            self.assertEqual(started, [])
            self.assertTrue(any(line.startswith("DOWNGRADE_NOT_CONFIRMED") for line in self.logs))
            self.bridge.confirmDowngrade()
            self.bridge.confirmCanOtaFlash()
        self.assertEqual(len(started), 1)
        self.assertTrue(started[0][1][1]["allow_downgrade"])

    def test_the_downgrade_confirmation_is_used_up_by_one_flash(self):
        self.bridge.setAllowDowngrade(True)
        self.bridge.confirmDowngrade()
        started, patch = self._spy_threads()
        with patch, mock.patch.object(type(self.bridge), "connected", True):
            self.bridge.confirmCanOtaFlash()
            self.bridge._busy = False
            self.bridge.confirmCanOtaFlash()
        self.assertEqual(len(started), 1)

    def test_a_confirmation_given_in_the_wrong_state_does_not_arm_a_downgrade(self):
        self.bridge.confirmDowngrade()  # the option is not ticked
        self.bridge.setAllowDowngrade(True)
        started, patch = self._spy_threads()
        with patch, mock.patch.object(type(self.bridge), "connected", True):
            self.bridge.confirmCanOtaFlash()
        self.assertEqual(started, [])

    def test_unticking_the_option_forgets_the_confirmation(self):
        self.bridge.setAllowDowngrade(True)
        self.bridge.confirmDowngrade()
        self.bridge.setAllowDowngrade(False)
        self.bridge.setAllowDowngrade(True)
        started, patch = self._spy_threads()
        with patch, mock.patch.object(type(self.bridge), "connected", True):
            self.bridge.confirmCanOtaFlash()
        self.assertEqual(started, [])

    # -- backup of the running firmware -----------------------------------
    def test_the_backup_is_refused_for_the_slave_and_when_not_connected(self):
        started, patch = self._spy_threads()
        self.bridge._transport = None
        with patch:
            self.bridge.startReadback("backup.bin")  # not connected
            self.bridge._transport = object()
            with mock.patch.object(type(self.bridge), "connected", True):
                self.bridge.setFlashTarget("slave")
                self.bridge.startReadback("backup.bin")
        self.assertEqual(started, [])
        self.assertTrue(any(line.startswith("READBACK_BLOCKED") for line in self.logs))

    def test_the_backup_worker_writes_the_file_and_reports_the_size(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "backup.bin")
            self.bridge._readback_worker(path)
            self.assertTrue(os.path.isfile(path))
        self.assertTrue(self.results[0].startswith("READBACK_COMPLETE 16 "))
        self.bridge._on_flash_result(self.results[0])
        self.assertIn("16", self.bridge.readbackResult)

    def test_a_failed_backup_is_reported(self):
        def boom(self, path):
            raise qt_flasher.FlashError("no answer")

        with mock.patch.object(FakeFlasher, "read_back_flash", boom):
            self.bridge._readback_worker("backup.bin")
        self.assertEqual(self.results, ["READBACK_FAILED no answer"])

    def test_file_urls_from_the_dialog_become_paths(self):
        self.assertEqual(qt_flasher._local_path("plain.bin"), "plain.bin")
        self.assertTrue(qt_flasher._local_path("file:///C:/tmp/x.bin").endswith("x.bin"))
        self.assertNotIn("file:", qt_flasher._local_path("file:///C:/tmp/x.bin"))

    # -- update report, bus activity, debug bundle ------------------------
    def test_a_finished_update_writes_its_report(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            image = os.path.join(folder, "image.bin")
            with open(image, "wb") as stream:
                stream.write(b"\x00" * 8)
            with mock.patch.object(qt_flasher, "writable_logs_folder", lambda f: folder):
                self.bridge._flash_worker(image, {})
            self.assertTrue(any(name.startswith("urtc_update_report_") for name in os.listdir(folder)))
        self.assertTrue(any(line.startswith("UPDATE_REPORT_WRITTEN") for line in self.logs))

    def test_the_bus_activity_check_counts_frames_and_leaves_the_bus_alone(self):
        clock = iter(x * 0.5 for x in range(1000))

        class Bus:
            sent = []

            def read_frame(self, timeout=0.1):
                return (0x100, b"")

            def send_frame(self, *args):
                Bus.sent.append(args)

        fake_time = types.SimpleNamespace(time=lambda: next(clock), monotonic=lambda: 0.0)
        counted = []
        self.bridge._busActivityResult.connect(lambda count, errors: counted.append((count, errors)))
        with mock.patch.object(qt_flasher, "time", fake_time):
            self.bridge._bus_activity_worker(Bus())
        self.assertEqual(Bus.sent, [])
        self.assertTrue(counted and counted[0][0] > 0 and counted[0][1] == 0)

    def test_the_debug_bundle_holds_the_log_the_diagnostics_and_the_image(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            image = os.path.join(folder, "image.bin")
            with open(image, "wb") as stream:
                stream.write(b"abc")
            self.bridge._selected_firmware = image
            self.bridge._logs = ["line one"]
            target = os.path.join(folder, "bundle.zip")
            self.bridge.exportDebugBundle(target)
            with zipfile.ZipFile(target) as bundle:
                names = set(bundle.namelist())
                self.assertEqual(bundle.read("session_log.txt").decode().strip(), "line one")
        self.assertEqual(names, {"session_log.txt", "system_diagnostics.txt", "firmware/image.bin"})
        self.assertIn(target, self.bridge.exportResult)

    def test_the_debug_bundle_reports_an_unwritable_destination(self):
        self.bridge.exportDebugBundle(os.path.join(os.path.dirname(__file__), "no_such_folder", "x.zip"))
        self.assertTrue(any(line.startswith("DEBUG_BUNDLE_FAILED") for line in self.logs))

    def test_the_recovery_image_is_offered_for_a_board_without_firmware(self):
        self.bridge._selected_firmware = ""
        self.bridge._recovery_candidate = "recovery.bin"
        self.bridge._on_snapshot_result([], "")
        self.assertEqual(self.bridge.selectedFirmware, "recovery.bin")
        self.assertTrue(any(line.startswith("RECOVERY_IMAGE_SELECTED") for line in self.logs))

    def test_a_board_without_firmware_and_without_a_local_image_lists_the_newest_release(self):
        listed = []
        self.bridge.loadRelease = lambda tag: listed.append(tag)
        self.bridge._selected_firmware = ""
        self.bridge._recovery_candidate = ""
        self.bridge._recovery_wants_download = True
        self.bridge._on_snapshot_result([], "")
        self.assertEqual(listed, [""])
        self.assertEqual(self.bridge.selectedFirmware, "")  # nothing is downloaded or chosen by itself
        self.assertTrue(any(line == "RECOVERY_NO_LOCAL_IMAGE" for line in self.logs))
        # asked once only, and never when an image is already chosen or the target is the slave
        self.bridge._on_snapshot_result([], "")
        self.assertEqual(listed, [""])
        for chosen, target in (("x.bin", "master"), ("", "slave")):
            listed.clear()
            self.bridge._selected_firmware, self.bridge._flash_target = chosen, target
            self.bridge._recovery_wants_download = True
            self.bridge._on_snapshot_result([], "")
            self.assertEqual(listed, [], (chosen, target))


if __name__ == "__main__":
    unittest.main()
