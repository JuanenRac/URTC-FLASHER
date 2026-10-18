# =============================================================================
# URTC Flasher - the Qt Quick CAN-OTA flash refuses an image whose published digest does not match
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
import os
import tempfile
import unittest

try:
    import qt_flasher
except ImportError:  # PySide6 is not installed
    qt_flasher = None


@unittest.skipIf(qt_flasher is None, "PySide6 is not available")
class QtFlashPreflightTests(unittest.TestCase):
    def _run(self, sidecar_digest):
        with tempfile.TemporaryDirectory() as folder:
            image = os.path.join(folder, "firmware.bin")
            with open(image, "wb") as stream:
                stream.write(b"\x00" * 64)
            if sidecar_digest is not None:
                with open(image + ".sha256", "w") as stream:
                    stream.write(sidecar_digest + "  firmware.bin\n")
            bridge = qt_flasher.FlasherQtBridge()
            results, logs = [], []
            bridge._flashResult.connect(results.append)
            bridge._log = logs.append  # the real one queues onto the GUI thread
            bridge._flash_worker(image)
            return results, logs

    def test_a_wrong_published_digest_stops_the_flash_before_any_frame(self):
        results, logs = self._run("0" * 64)
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].startswith("FLASH_FAILED"), results)
        self.assertTrue(any(line.startswith("IMAGE_REFUSED") for line in logs), logs)

    def test_an_image_with_no_published_digest_logs_its_digest_and_goes_on(self):
        results, logs = self._run(None)
        self.assertTrue(any(line.startswith("IMAGE_DIGEST_RECORDED") for line in logs), logs)
        self.assertFalse(any(line.startswith("IMAGE_REFUSED") for line in logs), logs)


if __name__ == "__main__":
    unittest.main()
