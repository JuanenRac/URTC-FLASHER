# =============================================================================
# URTC Flasher - the folder given to the picture tool is the one of the caller
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The tool moves to a temporary folder before it draws. A relative --out has to be resolved before that, or the pictures are written there, the run
says it passed and the folder of the caller stays empty. With --all-languages each child process receives the folder."""
import importlib.util
import os
import subprocess
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load_tool():
    spec = importlib.util.spec_from_file_location("capture_screens_under_test", ROOT / "tools" / "capture_screens.py")
    module = importlib.util.module_from_spec(spec)
    with mock.patch.dict(os.environ):  # the tool prepares the environment of its own run when it is loaded
        spec.loader.exec_module(module)
    return module


class CaptureOutFolderTests(unittest.TestCase):
    def test_a_relative_folder_is_handed_to_every_language_as_an_absolute_one(self):
        tool = load_tool()
        with mock.patch.object(subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as run:
            self.assertEqual(tool.main(["--all-languages", "--out", "pictures/guide"]), 0)
        folders = {call.args[0][call.args[0].index("--out") + 1] for call in run.call_args_list}
        self.assertEqual(folders, {os.path.abspath("pictures/guide")})
        self.assertEqual(run.call_count, 8)


if __name__ == "__main__":
    unittest.main()
