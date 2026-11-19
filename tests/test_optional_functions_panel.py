# =============================================================================
# URTC Flasher - tests/test_optional_functions_panel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The optional functions panel: hidden and unticked by default, the only place the emergency stop following is written, with a fake board.

Nothing here has run against a real board.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import flasher_functions as functions  # noqa: E402
from urtc_can import protocol  # noqa: E402

try:
    import qt_flasher
except ImportError:  # PySide6 is not installed
    qt_flasher = None

ESTOP = protocol.FEATURE_ESTOP_FOLLOW


class FakeCan:
    def __init__(self):
        self.sent: list[tuple[int, bytes]] = []

    def send_frame(self, can_id, data=b""):
        self.sent.append((can_id, bytes(data)))


class FakeHead:
    """Answers a query with the stored mask, and a write by storing it."""

    def __init__(self, stored=0x00, supported=0xFF, silent=False):
        self.can = FakeCan()
        self.stored, self.supported, self.silent = stored, supported, silent
        self.lines: list[str] = []

    def log(self, text):
        self.lines.append(text)

    def _wait_for(self, expected_id, timeout=2.0, expected_status_value=None):
        if self.silent:
            raise RuntimeError("timeout")
        last = self.can.sent[-1]
        if last[1].startswith(functions.FEATURES_MAGIC):
            self.stored = last[1][4]
        return bytes([self.stored, self.stored, self.supported])


def translate(key, **kwargs):
    return key + " " + " ".join(f"{k}={v}" for k, v in sorted(kwargs.items()))


class PanelSwitchTests(unittest.TestCase):
    def test_the_panel_is_off_unless_the_config_says_exactly_true(self):
        for config in (None, {}, {"optional_functions_panel": False}, {"optional_functions_panel": "true"}, {"optional_functions_panel": 1}, []):
            self.assertFalse(functions.panel_enabled(config), config)
        self.assertTrue(functions.panel_enabled({"optional_functions_panel": True}))

    def test_the_example_config_does_not_turn_the_panel_on(self):
        text = (ROOT / "urtc_config.json.example").read_text(encoding="utf-8")
        self.assertNotIn('"optional_functions_panel": true', text)


class WriteTests(unittest.TestCase):
    def test_the_frame_is_the_magic_and_the_mask(self):
        self.assertEqual(functions.features_frame(0x80), (protocol.CAN_ID_SET_FEATURES, b"FEAT\x80"))
        with self.assertRaises(ValueError):
            functions.features_frame(0x100)

    def test_the_answer_must_have_three_bytes(self):
        self.assertIsNone(functions.decode_features(b"\x01\x02"))
        self.assertEqual(functions.decode_features(b"\x80\x00\xff"), {"stored": 0x80, "running": 0, "supported": 0xFF})

    def test_only_the_bit_of_the_stop_following_changes(self):
        self.assertEqual(functions.merged_mask(0x11, True), 0x91)
        self.assertEqual(functions.merged_mask(0x91, False), 0x11)
        self.assertEqual(functions.merged_mask(0x00, False), 0x00)

    def test_switching_it_on_keeps_the_other_functions(self):
        head = FakeHead(stored=0x11)
        answer = functions.write_optional_functions(head, True, translate)
        self.assertEqual(head.can.sent, [(protocol.CAN_ID_FEATURES_RESP, b""), (protocol.CAN_ID_SET_FEATURES, b"FEAT\x91")])
        self.assertEqual(answer["stored"], 0x91)
        self.assertIn("LOG_OPT_FUNCTIONS_WRITTEN", head.lines[-1])

    def test_without_the_tick_the_button_switches_it_off(self):
        head = FakeHead(stored=0x91)
        functions.write_optional_functions(head, False, translate)
        self.assertEqual(head.can.sent[-1], (protocol.CAN_ID_SET_FEATURES, b"FEAT\x11"))

    def test_a_head_that_does_not_answer_is_left_alone(self):
        head = FakeHead(silent=True)
        self.assertIsNone(functions.write_optional_functions(head, True, translate))
        self.assertEqual(head.can.sent, [(protocol.CAN_ID_FEATURES_RESP, b"")])  # only the query: nothing was written
        self.assertIn("LOG_OPT_FUNCTIONS_NO_ANSWER", head.lines[-1])

    def test_a_function_the_head_does_not_have_is_not_asked_for(self):
        head = FakeHead(stored=0x00, supported=0x7F)
        functions.write_optional_functions(head, True, translate)
        self.assertEqual(head.can.sent[-1], (protocol.CAN_ID_SET_FEATURES, b"FEAT\x00"))


class CatalogTests(unittest.TestCase):
    def test_every_text_of_the_panel_is_in_the_eight_languages(self):
        keys = ("LBL_OPT_FUNCTIONS_TITLE", "CHK_OPT_ESTOP_FOLLOW", "BTN_WRITE_OPT_FUNCTIONS", "HELP_OPT_FUNCTIONS", "LOG_OPT_FUNCTIONS_WRITTEN", "LOG_OPT_FUNCTIONS_NO_ANSWER")
        files = sorted((ROOT / "language").glob("*.lng"))
        self.assertEqual(len(files), 8)
        for path in files:
            lines = path.read_text(encoding="utf-8").splitlines()
            for key in keys:
                self.assertTrue(any(line.startswith(key + "=") and len(line) > len(key) + 3 for line in lines), (path.name, key))


@unittest.skipIf(qt_flasher is None, "PySide6 is not available")
class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.bridge = qt_flasher.FlasherQtBridge()
        self.logs: list[str] = []
        self.bridge._log = self.logs.append
        self.bridge._transport = object()

    def test_the_panel_is_hidden_and_the_box_unticked_by_default(self):
        with mock.patch.object(qt_flasher.flasher_config, "load_config", lambda: {}):
            self.assertFalse(self.bridge.optionalFunctionsPanel)
            self.assertFalse(self.bridge.canWriteOptionalFunctions)
        self.assertFalse(self.bridge.optEstopFollow)

    def test_with_the_panel_off_the_slot_writes_nothing(self):
        with mock.patch.object(qt_flasher.flasher_config, "load_config", lambda: {}), mock.patch.object(qt_flasher, "URTCFlasher") as flasher_class:
            self.bridge.writeOptionalFunctions()
        flasher_class.assert_not_called()
        self.assertEqual(self.logs, ["FUNCTIONS_BLOCKED"])

    def test_the_worker_writes_the_ticked_value(self):
        calls = []
        with mock.patch.object(qt_flasher, "URTCFlasher", lambda *a, **k: object()), \
                mock.patch.object(qt_flasher.flasher_functions, "write_optional_functions", lambda f, on, t: calls.append(on)):
            results = []
            self.bridge._flashResult.connect(results.append)
            self.bridge._functions_worker(True)
        self.assertEqual(calls, [True])
        self.assertEqual(results, ["FUNCTIONS_DONE"])


if __name__ == "__main__":
    unittest.main()
