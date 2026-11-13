# =============================================================================
# URTC Flasher - tests/test_bus_symptoms.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The flasher has no continuous poll of the bus: it listens to the health frames (0x1B8) that go by while it works and judges them when an operation ends. A bus that
mixes speeds is recognised by its symptoms; the thresholds come from urtc_config.json. No change of the protocol."""
from __future__ import annotations

import unittest
import unittest.mock as mock

import flasher_config as config
from urtc_can import bus_health, health_info, protocol

try:
    import qt_flasher
except ImportError:  # PySide6 is not installed
    qt_flasher = None


def health_frame(tec=0, rec=0, bus_off=0) -> bytes:
    return protocol.encode_health_profile(tec=tec, rec=rec, bus_off_count=bus_off, hsi_trim=16, loop_max_ms=7, mcu_temp_plus_40=65, vdda_mv=3300)[1]


class FakeTransport:
    def __init__(self, frames):
        self.frames = list(frames)
        self.closed = False

    def read_frame(self, timeout=0.05):
        return self.frames.pop(0) if self.frames else None

    def send_frame(self, can_id, data=b""):
        return None

    def close(self):
        self.closed = True


class ThresholdTests(unittest.TestCase):
    def test_the_defaults_and_the_values_of_the_configuration_file(self):
        self.assertEqual(config.bus_health_thresholds({}), bus_health.Thresholds())
        given = {"bus_health": {"tec_warn": 40, "rec_warn": 50, "bus_off_warn": 3, "legacy_heads": ["A"]}}
        self.assertEqual(config.bus_health_thresholds(given), bus_health.Thresholds(40, 50, 3, ("A",)))

    def test_a_bad_value_keeps_its_default(self):
        self.assertEqual(config.bus_health_thresholds({"bus_health": {"tec_warn": 0, "rec_warn": 999, "bus_off_warn": "1"}}), bus_health.Thresholds())
        self.assertEqual(config.bus_health_thresholds({"bus_health": "nonsense"}), bus_health.Thresholds())

    def test_every_warning_has_a_log_line_with_its_text_in_the_eight_languages(self):
        for token in config.BUS_SYMPTOM_TOKENS.values():
            self.assertIn(token, config._LOG_LABEL_ONLY)
            for language in ("english", "spanish", "german", "french", "italian", "japanese", "chinese", "portuguese"):
                with open(f"language/{language}.lng", encoding="utf-8") as handle:
                    self.assertIn(f"\nQTLOG_{token}=", handle.read(), (language, token))
        self.assertEqual(sorted(config.BUS_SYMPTOM_TOKENS), sorted(bus_health.CODES))


@unittest.skipIf(qt_flasher is None, "PySide6 is not available")
class LiveReadingTests(unittest.TestCase):
    def setUp(self):
        self.bridge = qt_flasher.FlasherQtBridge()
        self.logs: list[str] = []
        self.bridge._log = self.logs.append

    def connect(self, frames):
        transport = FakeTransport(frames)
        self.bridge._on_connection_result(transport, "")
        return transport

    def work(self, transport, reads):
        for _ in range(reads):
            transport.read_frame()

    def test_a_transport_that_is_connected_is_listened_to_and_keeps_its_own_class(self):
        transport = self.connect([])
        self.assertIsNotNone(self.bridge._health_tap)
        self.assertIs(type(transport), FakeTransport)

    def test_health_frames_with_errors_that_go_by_during_an_operation_are_reported_when_it_ends(self):
        transport = self.connect([(protocol.CAN_ID_HEALTH_PROFILE, health_frame(tec=120)), (0x7F3, b"\x00\x00\x00\x01")])
        self.work(transport, 2)
        self.bridge._on_flash_result("FLASH_COMPLETE")
        self.assertIn("BUS_ERRORS_SEEN", self.logs)
        self.logs.clear()
        self.bridge._on_flash_result("FLASH_COMPLETE")          # the frames were handed over: nothing is said twice
        self.assertNotIn("BUS_ERRORS_SEEN", self.logs)

    def test_a_quiet_bus_says_nothing(self):
        transport = self.connect([(protocol.CAN_ID_HEALTH_PROFILE, health_frame()), (0x7F3, b"\x00")])
        self.work(transport, 2)
        self.bridge._on_flash_result("FLASH_COMPLETE")
        self.assertEqual([line for line in self.logs if line.startswith("BUS_")], [])

    def test_the_thresholds_of_the_configuration_are_the_ones_the_judgement_uses(self):
        transport = self.connect([(protocol.CAN_ID_HEALTH_PROFILE, health_frame(tec=50))])
        self.work(transport, 1)
        with mock.patch.object(config, "bus_health_thresholds", return_value=bus_health.thresholds_from_config({"tec_warn": 40})):
            self.bridge._on_flash_result("FLASH_COMPLETE")
        self.assertIn("BUS_ERRORS_SEEN", self.logs)          # 50 is above the 40 of the file and below the 96 of the default

    def test_a_mixed_bus_is_said_with_its_own_line(self):
        transport = self.connect([(protocol.CAN_ID_HEALTH_PROFILE, health_frame(tec=120))])
        self.work(transport, 1)
        with mock.patch.object(bus_health, "warnings", return_value=[bus_health.MIXED_BUS_SUSPECTED, bus_health.BUS_ERRORS, bus_health.LEGACY_HEAD_KNOWN]):
            self.bridge._on_flash_result("FLASH_FAILED x")
        self.assertEqual([line for line in self.logs if line.startswith("BUS_")], ["BUS_MIXED_SPEEDS", "BUS_ERRORS_SEEN", "BUS_LEGACY_HEAD"])

    def test_the_speed_the_heads_declare_is_said_when_the_operation_ends(self):
        transport = self.connect([(protocol.CAN_ID_HEALTH_INFO, health_info.encode(2, 8, 4, 4, 0, 60, 1_000_000)), (0x7F3, b"\x00")])
        self.work(transport, 2)
        self.bridge._on_flash_result("FLASH_COMPLETE")
        self.assertEqual([line for line in self.logs if line.startswith("BUS_")], ["BUS_RATE_DECLARED 1 Mbit/s"])

    def test_two_different_declared_speeds_are_a_mixed_bus_before_anything_else(self):
        transport = self.connect([(protocol.CAN_ID_HEALTH_INFO, health_info.encode(2, 8, 4, 4, 0, 60, 1_000_000)),
                                  (protocol.CAN_ID_HEALTH_INFO, health_info.encode(2, 8, 4, 4, 0, 61, 500_000)), (0x7F3, b"\x00")])
        self.work(transport, 3)
        self.bridge._on_flash_result("FLASH_COMPLETE")
        self.assertEqual([line for line in self.logs if line.startswith("BUS_")], ["BUS_RATES_DECLARED_DIFFER", "BUS_RATE_DECLARED 1 Mbit/s / 500 kbit/s"])

    def test_a_head_of_older_firmware_says_that_it_declares_nothing(self):
        transport = self.connect([(protocol.CAN_ID_HEALTH_INFO, health_info.encode(1, 8, 4, 4, 0, 60, None)), (0x7F3, b"\x00")])
        self.work(transport, 2)
        self.bridge._on_flash_result("FLASH_COMPLETE")
        self.assertEqual([line for line in self.logs if line.startswith("BUS_")], ["BUS_RATE_NOT_DECLARED"])

    def test_the_log_lines_of_the_declared_speed_are_translated_with_the_speed_in_place(self):
        with mock.patch.object(config, "_translations", config.load_language("german")):
            self.assertEqual(config.translate_log_line("BUS_RATE_DECLARED 500 kbit/s"), "Vom Kopf gemeldete Busgeschwindigkeit: 500 kbit/s")
            self.assertIn("unterschiedliche", config.translate_log_line("BUS_RATES_DECLARED_DIFFER"))
        with mock.patch.object(config, "_translations", config.load_language("english")):
            self.assertEqual(config.translate_log_line("BUS_RATE_DECLARED 1 Mbit/s"), "Bus speed the head declares: 1 Mbit/s")

    def test_without_a_connection_the_end_of_an_operation_says_nothing_about_the_bus(self):
        self.bridge._on_flash_result("FLASH_FAILED x")
        self.assertEqual([line for line in self.logs if line.startswith("BUS_")], [])

    def test_the_transport_reads_as_before_after_the_window_lets_go_of_it(self):
        transport = self.connect([(protocol.CAN_ID_HEALTH_PROFILE, health_frame(1))])
        self.bridge.prepareToQuit()
        self.assertTrue(transport.closed)
        self.assertEqual(transport.read_frame(), (protocol.CAN_ID_HEALTH_PROFILE, health_frame(1)))


if __name__ == "__main__":
    unittest.main()
