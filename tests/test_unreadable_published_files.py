# =============================================================================
# URTC-FLASHER - tests/test_unreadable_published_files.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""A digest or manifest that is next to an image and cannot be read is not the same as none: the image is not flashed."""
from __future__ import annotations

import hashlib
import json
import os

import pytest

import flasher_config
import flasher_integrity
import flasher_plan

IMAGE = b"\x00" * 1024
DIGEST = hashlib.sha256(IMAGE).hexdigest()

BAD = {
    "empty digest": (".sha256", b""),
    "binary digest": (".sha256", b"\x89PNG\r\n\x1a\n\x00\xff\xfe"),
    "digest with no digest": (".sha256", b"<html>404 Not Found</html>"),
    "cut digest": (".sha256", DIGEST[:40].encode()),
    "empty manifest": (".manifest.json", b""),
    "cut manifest": (".manifest.json", b'{"version": "0.3.5", "sha2'),
    "binary manifest": (".manifest.json", b"\xff\x00\x81"),
    "manifest that is a list": (".manifest.json", b"[1, 2]"),
    "manifest with an empty digest": (".manifest.json", b'{"sha256": ""}'),
    "manifest with a null digest": (".manifest.json", b'{"sha256": null}'),
    "manifest nested without end": (".manifest.json", b"[" * 200000),
}


def image(tmp_path, folder="firmware"):
    home = tmp_path / folder
    home.mkdir()
    path = home / "URTC_MAIN_FIRMWARE_v9.9.9.bin"
    path.write_bytes(IMAGE)
    return str(path)


@pytest.mark.parametrize("suffix, content", BAD.values(), ids=BAD.keys())
def test_an_unreadable_published_file_blocks_the_flash_and_is_named(tmp_path, suffix, content):
    path = image(tmp_path)
    with open(path + suffix, "wb") as stream:
        stream.write(content)
    check = flasher_integrity.preflight_image(path)
    assert check.blocked and not check.verified
    assert any(os.path.basename(path) + suffix in reason for reason in check.reasons)


def test_a_good_digest_does_not_hide_an_unreadable_manifest(tmp_path):
    path = image(tmp_path)
    with open(path + ".sha256", "w", encoding="ascii") as stream:
        stream.write(DIGEST)
    with open(path + ".manifest.json", "w", encoding="ascii") as stream:
        stream.write("{")
    assert flasher_integrity.preflight_image(path).blocked


def test_a_folder_in_the_place_of_the_digest_blocks_the_flash(tmp_path):
    path = image(tmp_path)
    os.mkdir(path + ".sha256")
    assert flasher_integrity.preflight_image(path).blocked


def test_no_published_file_and_a_manifest_without_a_digest_are_allowed(tmp_path):
    path = image(tmp_path)
    assert not flasher_integrity.preflight_image(path).blocked
    with open(path + ".manifest.json", "w", encoding="ascii") as stream:
        json.dump({"version": "9.9.9"}, stream)
    assert not flasher_integrity.preflight_image(path).blocked


def test_good_files_are_verified_in_a_folder_with_spaces_and_other_alphabets(tmp_path):
    path = image(tmp_path, "mis im\u00e1genes \u56fa\u4ef6 (copia 2)")
    with open(path + ".sha256", "w", encoding="utf-8") as stream:
        stream.write(f"{DIGEST}  {os.path.basename(path)}\n")
    check = flasher_integrity.preflight_image(path)
    assert check.verified and not check.blocked


def test_the_plan_of_an_update_refuses_it_too(tmp_path):
    path = image(tmp_path)
    open(path + ".sha256", "wb").close()
    plan = flasher_plan.build_plan(path, force=True)
    assert plan["digest"] == "blocked" and not plan["accepted"]


def test_the_message_is_in_the_eight_languages():
    folder = flasher_config.LANGUAGE_FOLDER if hasattr(flasher_config, "LANGUAGE_FOLDER") else os.path.join(os.path.dirname(flasher_config.__file__), "language")
    names = [name for name in os.listdir(folder) if name.endswith(".lng")]
    assert len(names) == 8
    for name in names:
        with open(os.path.join(folder, name), encoding="utf-8") as stream:
            line = next(line for line in stream if line.startswith("ERR_PUBLISHED_FILE_UNREADABLE="))
        assert "{name}" in line, name


def test_the_swd_programming_does_not_touch_the_probe(tmp_path, monkeypatch):
    pytest.importorskip("PySide6")
    import qt_flasher

    path = image(tmp_path)
    open(path + ".sha256", "wb").close()
    good = tmp_path / "boot.bin"
    good.write_bytes(IMAGE)
    touched, logs, results = [], [], []

    class Probe:
        def __init__(self, log=None):
            pass

        def full_chip_flash(self, *args, **kwargs):
            touched.append(args)

    class Signal:
        def emit(self, value):
            results.append(value)

    class Window:
        _swdFlashResult = Signal()

        def _log(self, line):
            logs.append(line)

    monkeypatch.setattr(qt_flasher, "PyOCDCLI", Probe)
    qt_class = next(value for value in vars(qt_flasher).values() if isinstance(value, type) and "_swd_flash_worker" in vars(value))
    qt_class._swd_flash_worker(Window(), str(good), path, "pyocd", False, None, None, False)
    assert touched == []
    assert results and results[0].startswith("SWD_FLASH_FAILED") and any(line.startswith("IMAGE_REFUSED") for line in logs)
    os.remove(path + ".sha256")
    qt_class._swd_flash_worker(Window(), str(good), path, "pyocd", False, None, None, False)
    assert len(touched) == 1
