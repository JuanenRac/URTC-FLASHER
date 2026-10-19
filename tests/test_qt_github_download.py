# =============================================================================
# URTC Flasher - the Qt Quick deck lists a GitHub release, downloads the chosen image with its digest files
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

IMAGE = {"name": "URTC_MAIN_FIRMWARE_v9.9.9.bin", "download_url": "https://github.com/x", "size": 2048}
SHA = {"name": "URTC_MAIN_FIRMWARE_v9.9.9.bin.sha256", "download_url": "https://github.com/y", "size": 5}
MANIFEST = {"name": "URTC_MAIN_FIRMWARE_v9.9.9.bin.manifest.json", "download_url": "https://github.com/z", "size": 50}
OTHER = {"name": "URTC_SLAVE_APP_v9.9.9.bin", "download_url": "https://github.com/w", "size": 10}


class Inline:
    """Runs the thread body at once so the test needs no waiting."""

    def __init__(self, target=None, args=(), **kwargs):
        self.target, self.args = target, args

    def start(self):
        self.target(*self.args)


@unittest.skipIf(qt_flasher is None, "PySide6 is not available")
class QtGithubDownloadTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.bridge = qt_flasher.FlasherQtBridge()
        self.logs = []
        self.bridge._log = self.logs.append
        self.asked, self.written = [], []

        def fake_fetch(tag=None, log=None, only_firmware=True):
            self.asked.append(tag)
            if self.fetch_error:
                raise self.fetch_error
            return "v9.9.9", self.entries

        def fake_download(url, dest, log=None, progress_cb=None, expected_size=None):
            self.written.append(os.path.basename(dest))
            if progress_cb:
                progress_cb(100)
            with open(dest, "wb") as stream:
                stream.write(b"x")

        self.fetch_error = None
        self.entries = [IMAGE, SHA, MANIFEST, OTHER]
        for patch in (
            mock.patch.object(qt_flasher, "FIRMWARE_FOLDER", self.folder.name),
            mock.patch.object(qt_flasher, "fetch_release", fake_fetch),
            mock.patch.object(qt_flasher, "download_file", fake_download),
            mock.patch.object(qt_flasher.threading, "Thread", Inline),
        ):
            patch.start()
            self.addCleanup(patch.stop)

    def test_the_listing_shows_the_images_with_a_readable_size_and_hides_their_digest_files(self):
        self.bridge.loadRelease("")
        names = [item["name"] for item in self.bridge.releaseImages]
        self.assertEqual(names, [IMAGE["name"], OTHER["name"]])
        self.assertEqual(self.bridge.releaseImages[0]["size"], "2.0 KiB")
        self.assertEqual(self.asked, [None])
        self.assertIn("v9.9.9", self.bridge.releaseStatus)

    def test_a_typed_tag_is_asked_for_and_an_empty_one_means_the_newest(self):
        self.bridge.loadRelease(" v0.3.6 ")
        self.bridge.loadRelease("")
        self.assertEqual(self.asked, ["v0.3.6", None])

    def test_a_failed_lookup_is_reported_not_raised_and_clears_the_list(self):
        self.bridge.loadRelease("")
        self.fetch_error = qt_flasher.GitHubDownloadError("offline")
        self.bridge.loadRelease("")
        self.assertEqual(self.bridge.releaseImages, [])
        self.assertIn("offline", self.bridge.releaseStatus)
        self.assertFalse(self.bridge.releaseBusy)
        self.assertTrue(any(line.startswith("GITHUB_FAILED") for line in self.logs))

    def test_an_empty_release_says_so(self):
        self.entries = []
        self.bridge.loadRelease("")
        self.assertEqual(self.bridge.releaseImages, [])
        self.assertTrue(self.bridge.releaseStatus)

    def test_only_the_chosen_image_and_its_own_digest_files_are_downloaded(self):
        self.bridge.loadRelease("")
        self.bridge.downloadReleaseFile(IMAGE["name"])
        self.assertEqual(sorted(self.written), sorted([IMAGE["name"], SHA["name"], MANIFEST["name"]]))
        self.assertNotIn(OTHER["name"], self.written)
        self.assertEqual(self.bridge.releaseProgress, 100)
        self.assertFalse(self.bridge.releaseBusy)
        self.assertTrue(any(line.startswith("GITHUB_DOWNLOADED") for line in self.logs))

    def test_the_downloaded_image_shows_up_in_the_firmware_list(self):
        self.bridge.loadRelease("")
        with mock.patch.object(self.bridge, "scanFirmware") as rescan:
            self.bridge.downloadReleaseFile(IMAGE["name"])
        rescan.assert_called_once()

    def test_an_existing_file_waits_for_a_yes_before_it_is_replaced(self):
        path = os.path.join(self.folder.name, IMAGE["name"])
        with open(path, "wb") as stream:
            stream.write(b"mine")
        self.bridge.loadRelease("")
        self.bridge.downloadReleaseFile(IMAGE["name"])
        self.assertEqual(self.written, [])
        self.assertEqual(self.bridge.releaseOverwriteName, IMAGE["name"])
        self.assertIn(IMAGE["name"], self.bridge.releaseOverwriteQuestion)
        self.bridge.cancelReleaseOverwrite()
        self.assertEqual(self.bridge.releaseOverwriteName, "")
        with open(path, "rb") as stream:
            self.assertEqual(stream.read(), b"mine")
        self.bridge.downloadReleaseFile(IMAGE["name"])
        self.bridge.confirmReleaseOverwrite()
        self.assertIn(IMAGE["name"], self.written)

    def test_a_name_that_leaves_the_firmware_folder_or_is_not_listed_is_never_written(self):
        evil = {"name": "../evil.bin", "download_url": "https://github.com/x", "size": 1}
        self.entries = [evil]
        self.bridge.loadRelease("")
        self.bridge.downloadReleaseFile("../evil.bin")
        self.bridge.downloadReleaseFile("never_listed.bin")
        self.assertEqual(self.written, [])

    def test_a_digest_file_cannot_be_downloaded_on_its_own(self):
        self.bridge.loadRelease("")
        self.bridge.downloadReleaseFile(SHA["name"])
        self.assertEqual(self.written, [])

    def test_a_failed_download_is_reported(self):
        self.bridge.loadRelease("")

        def broken(url, dest, **kwargs):
            raise qt_flasher.GitHubDownloadError("size differs")

        with mock.patch.object(qt_flasher, "download_file", broken):
            self.bridge.downloadReleaseFile(IMAGE["name"])
        self.assertIn("size differs", self.bridge.releaseStatus)
        self.assertFalse(self.bridge.releaseBusy)


if __name__ == "__main__":
    unittest.main()
