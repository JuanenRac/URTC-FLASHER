# =============================================================================
# URTC-FLASHER - image and target integrity tests
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
import hashlib
import os
import sys
import tempfile
import unittest
import zlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flasher_integrity import may_report_success, verify_image, verify_target  # noqa: E402

PAYLOAD = b"\x00\x01firmware-image\xff" * 100
SHA = hashlib.sha256(PAYLOAD).hexdigest()
CRC = f"0x{zlib.crc32(PAYLOAD) & 0xFFFFFFFF:08X}"


class ImageTests(unittest.TestCase):
    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".bin")
        with os.fdopen(handle, "wb") as stream:
            stream.write(PAYLOAD)
        self.addCleanup(os.remove, self.path)

    def test_a_matching_image_passes_and_reports_its_digests(self):
        result = verify_image(self.path, SHA, CRC)
        self.assertTrue(result.ok, result.reasons)
        self.assertEqual((result.sha256, result.crc32), (SHA, CRC))

    def test_uppercase_and_prefixless_values_are_accepted(self):
        self.assertTrue(verify_image(self.path, SHA.upper(), CRC[2:].lower()).ok)

    def test_a_different_image_is_refused_with_both_values_named(self):
        result = verify_image(self.path, hashlib.sha256(b"other").hexdigest())
        self.assertFalse(result.ok)
        self.assertIn(SHA, result.reasons[0])

    def test_a_wrong_crc_is_refused_even_when_the_sha_matches(self):
        result = verify_image(self.path, SHA, "0x00000001")
        self.assertFalse(result.ok)
        self.assertIn("CRC-32 mismatch", result.reasons[0])

    def test_no_expectation_is_never_a_pass(self):
        for missing in (None, ""):
            self.assertFalse(verify_image(self.path, missing).ok)

    def test_malformed_expectations_and_unreadable_files_are_refused(self):
        self.assertFalse(verify_image(self.path, "not-hex").ok)
        self.assertFalse(verify_image(self.path, SHA, "zzzz").ok)
        self.assertFalse(verify_image(self.path + ".missing", SHA).ok)


class TargetTests(unittest.TestCase):
    def test_the_expected_board_passes_case_insensitively(self):
        self.assertTrue(verify_target("URTC-MAIN", " urtc-main ").ok)

    def test_a_wrong_or_silent_or_unspecified_board_is_refused(self):
        self.assertFalse(verify_target("URTC-MAIN", "URTC-SLAVE").ok)
        self.assertFalse(verify_target("URTC-MAIN", None).ok)
        self.assertFalse(verify_target(None, "URTC-MAIN").ok)


class SuccessTests(unittest.TestCase):
    def test_success_needs_both_checks(self):
        handle, path = tempfile.mkstemp()
        with os.fdopen(handle, "wb") as stream:
            stream.write(PAYLOAD)
        self.addCleanup(os.remove, path)
        good_image, bad_image = verify_image(path, SHA), verify_image(path, "0" * 64)
        good_target, bad_target = verify_target("A", "A"), verify_target("A", "B")
        self.assertTrue(may_report_success(good_image, good_target)[0])
        for image, target in ((good_image, bad_target), (bad_image, good_target), (bad_image, bad_target)):
            ok, reasons = may_report_success(image, target)
            self.assertFalse(ok)
            self.assertTrue(reasons)


if __name__ == "__main__":
    unittest.main()
