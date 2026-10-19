# =============================================================================
# URTC Flasher - the Qt Quick deck lets the operator pick the serial CAN adapter bus speed
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
import unittest

try:
    import qt_flasher
except ImportError:  # PySide6 is not installed
    qt_flasher = None


@unittest.skipIf(qt_flasher is None, "PySide6 is not available")
class QtBitrateTests(unittest.TestCase):
    def setUp(self):
        self.bridge = qt_flasher.FlasherQtBridge()

    def test_the_default_is_500_kbit_and_maps_to_the_documented_slcan_code(self):
        self.assertEqual(self.bridge.selectedBitrate, "500 kbit/s")
        self.assertEqual(self.bridge._slcan_bitrate_code(), qt_flasher.BITRATE_500K_SLCAN_CODE)

    def test_every_listed_speed_can_be_selected_and_maps_to_its_own_code(self):
        for label, code in qt_flasher.SLCAN_BITRATES:
            self.bridge.selectBitrate(label)
            self.assertEqual(self.bridge.selectedBitrate, label)
            self.assertEqual(self.bridge._slcan_bitrate_code(), code)

    def test_an_unknown_speed_is_ignored(self):
        self.bridge.selectBitrate("123 kbit/s")
        self.assertEqual(self.bridge.selectedBitrate, "500 kbit/s")

    def test_the_speed_cannot_change_while_a_transport_is_open(self):
        self.bridge._transport = object()
        self.bridge.selectBitrate("125 kbit/s")
        self.assertEqual(self.bridge.selectedBitrate, "500 kbit/s")


if __name__ == "__main__":
    unittest.main()
