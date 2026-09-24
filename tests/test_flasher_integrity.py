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




class PreflightTests(unittest.TestCase):
    def setUp(self):
        import tempfile as _t

        self._dir = _t.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.path = os.path.join(self._dir.name, "fw.bin")
        with open(self.path, "wb") as stream:
            stream.write(PAYLOAD)

    def _sidecar(self, text):
        with open(self.path + ".sha256", "w", encoding="utf-8") as stream:
            stream.write(text)

    def test_without_a_published_digest_it_is_allowed_but_reports_the_digest(self):
        from flasher_integrity import preflight_image

        result = preflight_image(self.path)
        self.assertFalse(result.blocked)
        self.assertFalse(result.verified)
        self.assertEqual(result.sha256, SHA)

    def test_a_matching_sidecar_verifies_in_both_layouts(self):
        from flasher_integrity import preflight_image

        for text in (SHA + "\n", f"{SHA.upper()}  fw.bin\n"):
            self._sidecar(text)
            result = preflight_image(self.path)
            self.assertTrue(result.verified)
            self.assertFalse(result.blocked)

    def test_a_mismatching_sidecar_blocks(self):
        from flasher_integrity import preflight_image

        self._sidecar("0" * 64 + "\n")
        result = preflight_image(self.path)
        self.assertTrue(result.blocked)
        self.assertIn("mismatch", result.reasons[0])

    def test_a_garbage_sidecar_is_treated_as_absent(self):
        from flasher_integrity import preflight_image, read_sidecar_sha256

        self._sidecar("not a digest")
        self.assertIsNone(read_sidecar_sha256(self.path))
        self.assertFalse(preflight_image(self.path).blocked)

    def test_an_unreadable_image_blocks(self):
        from flasher_integrity import preflight_image

        self.assertTrue(preflight_image(self.path + ".missing").blocked)


if __name__ == "__main__":
    unittest.main()
