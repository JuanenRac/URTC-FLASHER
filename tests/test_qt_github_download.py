# =============================================================================
# URTC Flasher - the Qt Quick deck downloads the newest release images with their digest files
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
import os
import tempfile
import unittest
from unittest import mock

try:
    import qt_flasher
except ImportError:  # PySide6 is not installed
    qt_flasher = None


@unittest.skipIf(qt_flasher is None, "PySide6 is not available")
class QtGithubDownloadTests(unittest.TestCase):
    def _run(self, entries, fetch_error=None):
        written, results = [], []
        bridge = qt_flasher.FlasherQtBridge()
        bridge._githubResult.connect(results.append)
        bridge._log = lambda message: None

        def fake_fetch(tag=None, log=None, only_firmware=True):
            if fetch_error:
                raise fetch_error
            return "v9.9.9", entries

        def fake_download(url, dest, log=None, progress_cb=None, expected_size=None):
            written.append(os.path.basename(dest))

        with tempfile.TemporaryDirectory() as folder, \
                mock.patch.object(qt_flasher, "FIRMWARE_FOLDER", folder), \
                mock.patch.object(qt_flasher, "fetch_release", fake_fetch), \
                mock.patch.object(qt_flasher, "download_file", fake_download):
            bridge._github_download_worker()
        return written, results

    def test_images_and_their_digest_files_are_all_downloaded(self):
        entries = [
            {"name": "URTC_MAIN_FIRMWARE_v9.9.9.bin", "download_url": "https://github.com/x", "size": 10},
            {"name": "URTC_MAIN_FIRMWARE_v9.9.9.bin.sha256", "download_url": "https://github.com/y", "size": 5},
        ]
        written, results = self._run(entries)
        self.assertEqual(written, [e["name"] for e in entries])
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].startswith("GITHUB_FAILED"), results)

    def test_a_name_that_leaves_the_firmware_folder_is_never_written(self):
        entries = [{"name": "../evil.bin", "download_url": "https://github.com/x", "size": 1}]
        written, results = self._run(entries)
        self.assertEqual(written, [])

    def test_a_failed_lookup_is_reported_not_raised(self):
        written, results = self._run([], fetch_error=qt_flasher.GitHubDownloadError("offline"))
        self.assertEqual(written, [])
        self.assertTrue(results[0].startswith("GITHUB_FAILED"), results)
        self.assertIn("offline", results[0])


if __name__ == "__main__":
    unittest.main()
