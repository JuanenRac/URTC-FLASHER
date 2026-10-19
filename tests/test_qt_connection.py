# =============================================================================
# URTC Flasher - Qt Quick deck: connecting, disconnecting, the flash gate and the board snapshot
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
from __future__ import annotations

import unittest
from unittest import mock

try:
    import qt_flasher
except ImportError:  # PySide6 is not installed
    qt_flasher = None


class Inline:
    def __init__(self, target=None, args=(), **kwargs):
        self.target, self.args = target, args

    def start(self):
        self.target(*self.args)


class FakeAdapter:
    instances: list = []

    def __init__(self, port, log=None):
        self.port, self.opened, self.closed = port, None, False
        FakeAdapter.instances.append(self)

    def open_channel(self, code=None, listen_only=False):
        self.opened = code

    def close(self):
        self.closed = True


@unittest.skipIf(qt_flasher is None, "PySide6 is not available")
class QtConnectionTests(unittest.TestCase):
    def setUp(self):
        FakeAdapter.instances = []
        for patch in (
            mock.patch.object(qt_flasher.threading, "Thread", Inline),
            mock.patch.object(qt_flasher, "SLCAN", FakeAdapter),
            mock.patch.object(qt_flasher, "SocketCAN", FakeAdapter),
        ):
            patch.start()
            self.addCleanup(patch.stop)
        self.bridge = qt_flasher.FlasherQtBridge()
        self.logs: list[str] = []
        self.bridge._log = self.logs.append
        self.bridge._ports = ["COM7", "can0"]
        self.bridge._socketcan_ports = {"can0"}
        self.bridge._selected_port = "COM7"

    def test_connecting_opens_the_serial_adapter_at_the_chosen_speed_and_disconnecting_closes_it(self):
        self.bridge.selectBitrate("125 kbit/s")
        self.bridge.toggleConnection()
        self.assertTrue(self.bridge.connected)
        self.assertEqual(FakeAdapter.instances[0].opened, dict(qt_flasher.SLCAN_BITRATES)["125 kbit/s"])
        self.bridge.toggleConnection()
        self.assertFalse(self.bridge.connected)
        self.assertTrue(FakeAdapter.instances[0].closed)

    def test_a_socketcan_interface_is_opened_without_a_bit_rate(self):
        self.bridge._selected_port = "can0"
        self.bridge.toggleConnection()
        self.assertTrue(self.bridge.connected)
        self.assertIsNone(FakeAdapter.instances[0].opened)

    def test_a_failing_adapter_leaves_the_deck_disconnected_and_free(self):
        def broken(self, code=None, listen_only=False):
            raise OSError("port busy")

        with mock.patch.object(FakeAdapter, "open_channel", broken):
            self.bridge.toggleConnection()
        self.assertFalse(self.bridge.connected)
        self.assertFalse(self.bridge.busy)
        self.assertTrue(any(line.startswith("CONNECTION_FAILED") for line in self.logs))

    def test_connecting_without_a_port_does_nothing(self):
        self.bridge._selected_port = ""
        self.bridge.toggleConnection()
        self.assertFalse(self.bridge.connected)
        self.assertEqual(FakeAdapter.instances, [])

    def test_nothing_changes_while_the_deck_is_busy(self):
        self.bridge._busy = True
        self.bridge.toggleConnection()
        self.assertEqual(FakeAdapter.instances, [])

    def test_the_flash_needs_a_connection_an_image_and_an_idle_deck(self):
        self.bridge._selected_firmware = "image.bin"
        self.assertFalse(self.bridge.canFlash)
        self.bridge.toggleConnection()
        self.assertTrue(self.bridge.canFlash)
        self.bridge._busy = True
        self.assertFalse(self.bridge.canFlash)
        self.bridge._busy = False
        self.bridge._selected_firmware = ""
        self.assertFalse(self.bridge.canFlash)

    def test_the_flash_is_refused_without_a_connection(self):
        started = []
        self.bridge._selected_firmware = "image.bin"
        with mock.patch.object(self.bridge, "_flash_worker", lambda *a, **k: started.append(a)):
            self.bridge.confirmCanOtaFlash()
        self.assertEqual(started, [])


@unittest.skipIf(qt_flasher is None, "PySide6 is not available")
class QtBoardSnapshotTests(unittest.TestCase):
    def test_the_snapshot_lists_what_the_board_answers_and_marks_silence(self):

        bridge = qt_flasher.FlasherQtBridge()
        bridge._log = lambda message: None
        results = []
        bridge._snapshotResult.connect(lambda items, error: results.append((items, error)))

        class Transport:
            def __init__(self):
                self.queue = []

            def send_frame(self, can_id, data):
                if can_id == qt_flasher.CAN_ID_QUERY_ERROR_COUNTERS:
                    self.queue.append((qt_flasher.CAN_ID_ERROR_COUNTERS_RESPONSE, bytes([0, 0])))

            def read_frame(self, timeout=0.1):
                return self.queue.pop(0) if self.queue else None

        fake_flasher = mock.Mock()
        fake_flasher.query_version.return_value = {
            "responder": "application", "version_major": 0, "version_minor": 3, "hardware_id": qt_flasher.THIS_HARDWARE_ID,
            "bootloader_version": None,
        }
        with mock.patch.object(qt_flasher, "URTCFlasher", lambda *a, **k: fake_flasher), \
                mock.patch.object(qt_flasher.FlasherQtBridge, "_wait_for_frame", staticmethod(lambda transport, expected, size, timeout=1.5: (transport.read_frame() or (0, None))[1])):
            bridge._read_board_snapshot_worker(Transport())
        items, error = results[0]
        self.assertEqual(error, "")
        labels = {item["label"]: item for item in items}
        self.assertTrue(labels["Version"]["ok"])
        self.assertTrue(labels["CAN health"]["ok"])
        self.assertFalse(labels["Expansion"]["ok"])
        self.assertEqual(labels["Expansion"]["value"], "No response")


if __name__ == "__main__":
    unittest.main()
