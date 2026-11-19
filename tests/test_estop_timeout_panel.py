# =============================================================================
# URTC Flasher - tests/test_estop_timeout_panel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The silence of the master of the emergency stop in the optional functions panel: read with the queries 3 and 4, written with the eight-byte
0x1AE only after the person confirmed that one write, never without it, with a fake head. Nothing here has run against a real board.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import flasher_functions as functions  # noqa: E402
from urtc_can import estop_follow as ef  # noqa: E402
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
    """A head with the eight-byte forms: it answers the queries 3 and 4 and stores a valid eight-byte write (an invalid one it ignores, as the firmware does)."""

    def __init__(self, stored=0x00, stored_ext=0x00, stored_timeout=0, running_timeout=100, silent=False, keeps=True):
        self.can = FakeCan()
        self.stored, self.stored_ext = stored, stored_ext
        self.stored_timeout, self.running_timeout = stored_timeout, running_timeout
        self.silent, self.keeps = silent, keeps
        self.lines: list[str] = []

    def log(self, text):
        self.lines.append(text)

    def _wait_for(self, expected_id, timeout=2.0, expected_status_value=None):
        if self.silent:
            raise RuntimeError("timeout")
        _, data = self.can.sent[-1]
        write = ef.parse_features_write(data)
        if write is not None and write.timeout_ms is not None:
            self.stored, self.stored_ext = write.mask, write.mask_ext
            if self.keeps:
                self.stored_timeout = write.timeout_ms
            return ef.encode_timeout_answer(self.stored, 0, self.stored_ext, 0, self.stored_timeout)
        form = ef.query_form(data)
        if form == ef.QUERY_TIMEOUT_STORED:
            return ef.encode_timeout_answer(self.stored, 0, self.stored_ext, 0, self.stored_timeout)
        if form == ef.QUERY_TIMEOUT_IN_FORCE:
            return ef.encode_timeout_answer(self.stored, 0, self.stored_ext, 0, self.running_timeout)
        raise RuntimeError("an older head: no answer in the new form")


def translate(key, **kwargs):
    return key + " " + " ".join(f"{k}={v}" for k, v in sorted(kwargs.items()))


class ValueTests(unittest.TestCase):
    def test_the_limits_are_the_ones_of_the_specification(self):
        self.assertEqual((functions.TIMEOUT_MIN_MS, functions.TIMEOUT_MAX_MS), (40, 500))

    def test_only_zero_and_the_range_are_valid_and_nothing_is_guessed(self):
        for ms in (0, 40, 41, 100, 499, 500):
            self.assertTrue(functions.timeout_valid(ms), ms)
        for ms in (-1, 1, 20, 39, 501, 65535, 2 ** 20, True, False, 50.0, "50", None):
            self.assertFalse(functions.timeout_valid(ms), ms)


class ReadTests(unittest.TestCase):
    def test_it_asks_for_the_stored_and_the_running_value_and_writes_nothing(self):
        head = FakeHead(stored_timeout=250, running_timeout=100)
        answer = functions.read_estop_timeout(head, translate)
        self.assertEqual(answer, {"running": 100, "stored": 250})
        self.assertEqual(head.can.sent, [(protocol.CAN_ID_FEATURES_RESP, b"\x04"), (protocol.CAN_ID_FEATURES_RESP, b"\x03")])
        self.assertTrue(all(can_id != protocol.CAN_ID_SET_FEATURES for can_id, _ in head.can.sent))
        self.assertIn("LOG_OPT_TIMEOUT_READ", head.lines[-1])
        self.assertIn("running=100", head.lines[-1])

    def test_an_older_head_is_told_so_and_left_alone(self):
        head = FakeHead(silent=True)
        self.assertIsNone(functions.read_estop_timeout(head, translate))
        self.assertIn("LOG_OPT_TIMEOUT_UNSUPPORTED", head.lines[-1])


class WriteTests(unittest.TestCase):
    def test_nothing_is_written_without_the_confirmation(self):
        head = FakeHead()
        self.assertIsNone(functions.write_estop_timeout(head, True, 80, False, translate))
        self.assertEqual(head.can.sent, [])   # not even a query
        self.assertIn("LOG_OPT_TIMEOUT_NOT_CONFIRMED", head.lines[-1])

    def test_a_value_outside_the_limits_is_refused_before_anything_is_sent(self):
        for ms in (1, 39, 501, 65535, -5):
            head = FakeHead()
            self.assertIsNone(functions.write_estop_timeout(head, True, ms, True, translate))
            self.assertEqual(head.can.sent, [], ms)
            self.assertIn("LOG_OPT_TIMEOUT_INVALID", head.lines[-1])
            self.assertIn("min=40", head.lines[-1])

    def test_a_confirmed_value_is_written_with_the_eight_byte_form_and_nothing_else_changes(self):
        head = FakeHead(stored=0x11, stored_ext=0x02, stored_timeout=0)
        answer = functions.write_estop_timeout(head, True, 80, True, translate)
        self.assertEqual(head.can.sent[0], (protocol.CAN_ID_FEATURES_RESP, b"\x04"))
        can_id, data = head.can.sent[1]
        self.assertEqual((can_id, data), (protocol.CAN_ID_SET_FEATURES, b"FEAT\x91\x02\x00\x50"))   # the other functions and the second byte are carried over
        self.assertEqual(answer["timeout_ms"], 80)
        self.assertEqual(head.stored, 0x91)
        self.assertEqual(head.stored_ext, 0x02)
        self.assertFalse(any("MISMATCH" in line for line in head.lines))

    def test_zero_clears_the_stored_value_and_unticked_switches_the_stop_following_off(self):
        head = FakeHead(stored=0x91, stored_timeout=300)
        functions.write_estop_timeout(head, False, 0, True, translate)
        self.assertEqual(head.can.sent[-1], (protocol.CAN_ID_SET_FEATURES, b"FEAT\x11\x00\x00\x00"))
        self.assertEqual(head.stored_timeout, 0)

    def test_a_head_without_the_eight_byte_form_is_not_written(self):
        head = FakeHead(silent=True)
        self.assertIsNone(functions.write_estop_timeout(head, True, 80, True, translate))
        self.assertEqual(head.can.sent, [(protocol.CAN_ID_FEATURES_RESP, b"\x04")])   # only the query
        self.assertIn("LOG_OPT_TIMEOUT_UNSUPPORTED", head.lines[-1])

    def test_a_head_that_does_not_keep_the_value_is_reported(self):
        head = FakeHead(stored_timeout=0, keeps=False)
        functions.write_estop_timeout(head, True, 80, True, translate)
        self.assertIn("LOG_OPT_TIMEOUT_MISMATCH stored=0", head.lines[-1])

    def test_a_head_that_does_not_answer_the_write_is_reported(self):
        head = FakeHead()
        original = head._wait_for
        calls = []

        def flaky(expected_id, timeout=2.0, expected_status_value=None):
            calls.append(1)
            if len(calls) > 1:
                raise RuntimeError("timeout")
            return original(expected_id, timeout)

        head._wait_for = flaky
        self.assertIsNone(functions.write_estop_timeout(head, True, 80, True, translate))
        self.assertIn("LOG_OPT_FUNCTIONS_NO_ANSWER", head.lines[-1])


class CatalogTests(unittest.TestCase):
    def test_every_text_is_in_the_eight_languages(self):
        keys = ("LBL_OPT_ESTOP_TIMEOUT", "CHK_OPT_ESTOP_TIMEOUT", "CHK_OPT_ESTOP_TIMEOUT_CONFIRM", "BTN_READ_OPT_FUNCTIONS", "LOG_OPT_TIMEOUT_READ",
                "LOG_OPT_TIMEOUT_INVALID", "LOG_OPT_TIMEOUT_NOT_CONFIRMED", "LOG_OPT_TIMEOUT_MISMATCH", "LOG_OPT_TIMEOUT_UNSUPPORTED")
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

    def test_the_silence_is_off_unconfirmed_and_zero_at_start(self):
        self.assertFalse(self.bridge.optTimeoutSet)
        self.assertFalse(self.bridge.optTimeoutConfirm)
        self.assertEqual(self.bridge.optTimeoutMs, 0)
        self.assertEqual((self.bridge.optTimeoutMin, self.bridge.optTimeoutMax), (40, 500))

    def test_a_changed_value_or_an_untick_drops_the_confirmation(self):
        self.bridge.setOptTimeoutSet(True)
        self.bridge.setOptTimeoutConfirm(True)
        self.assertTrue(self.bridge.optTimeoutConfirm)
        self.bridge.setOptTimeoutMs(90)
        self.assertFalse(self.bridge.optTimeoutConfirm)
        self.bridge.setOptTimeoutConfirm(True)
        self.bridge.setOptTimeoutSet(False)
        self.assertFalse(self.bridge.optTimeoutConfirm)

    def test_the_confirmation_is_spent_by_the_attempt(self):
        started = []
        self.bridge.setOptTimeoutSet(True)
        self.bridge.setOptTimeoutMs(90)
        self.bridge.setOptTimeoutConfirm(True)
        with mock.patch.object(qt_flasher.flasher_config, "load_config", lambda: {"optional_functions_panel": True}), \
                mock.patch.object(type(self.bridge), "connected", mock.PropertyMock(return_value=True)), \
                mock.patch.object(qt_flasher.threading, "Thread", lambda target, args, **k: mock.Mock(start=lambda: started.append(args))):
            self.bridge._flash_target = "master"
            self.bridge.writeOptionalFunctions()
        self.assertEqual(started, [(False, (90, True))])
        self.assertFalse(self.bridge.optTimeoutConfirm)

    def test_the_worker_without_a_silence_uses_the_old_write(self):
        calls = []
        with mock.patch.object(qt_flasher, "URTCFlasher", lambda *a, **k: object()), \
                mock.patch.object(qt_flasher.flasher_functions, "write_optional_functions", lambda f, on, t: calls.append(("old", on))), \
                mock.patch.object(qt_flasher.flasher_functions, "write_estop_timeout", lambda f, on, ms, ok, t: calls.append(("new", ms, ok))):
            self.bridge._functions_worker(True)
            self.bridge._functions_worker(True, (90, True))
        self.assertEqual(calls, [("old", True), ("new", 90, True)])

    def test_nothing_is_written_during_a_flash(self):
        self.bridge._busy = True
        with mock.patch.object(qt_flasher.flasher_config, "load_config", lambda: {"optional_functions_panel": True}), \
                mock.patch.object(qt_flasher, "URTCFlasher") as flasher_class:
            self.bridge.writeOptionalFunctions()
            self.bridge.readOptionalFunctions()
        flasher_class.assert_not_called()
        self.assertEqual(self.logs, ["FUNCTIONS_BLOCKED", "FUNCTIONS_BLOCKED"])


if __name__ == "__main__":
    unittest.main()
