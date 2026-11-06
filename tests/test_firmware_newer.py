# =============================================================================
# URTC Flasher - tests/test_firmware_newer.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""`sync_firmware.py --newer` compares the images of firmware/ with the newest official release, in the language asked for, without downloading anything."""
from __future__ import annotations

import importlib.util
import urllib.error
from pathlib import Path

import pytest

from urtc_can import firmware_check as fc

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("sync_firmware", ROOT / "tools" / "sync_firmware.py")
sync_firmware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync_firmware)

LATEST = {("MAIN", "FIRMWARE"): "0.4.5", ("SLAVE", "FIRMWARE"): "0.2.9", ("MAIN", "BOOTLOADER"): "0.4.7", ("SLAVE", "BOOTLOADER"): "0.3.1"}


@pytest.fixture
def folder(tmp_path, monkeypatch):
    monkeypatch.setattr(sync_firmware, "DEST", tmp_path / "firmware")
    monkeypatch.setenv("URTC_UPDATE_ROOT", str(tmp_path / "data"))
    (tmp_path / "firmware").mkdir()
    return tmp_path / "firmware"


def release_answers(monkeypatch, images=LATEST):
    calls = []

    def fake(fetch, cache_file, now, ttl=fc.CACHE_TTL_SECONDS, retry_after=fc.RETRY_AFTER_SECONDS, repo=fc.FIRMWARE_REPO, force=False):
        calls.append((cache_file, force))
        return fc.LatestRelease("v0.4.5", dict(images), 0.0)

    monkeypatch.setattr(fc, "latest_release", fake)
    return calls


def fill(folder, versions):
    for (board, kind), version in versions.items():
        (folder / f"URTC_{board}_{kind}_v{version}.bin").write_bytes(b"x")


def test_a_folder_that_matches_the_release_says_so_and_exits_with_zero(folder, monkeypatch, capsys):
    release_answers(monkeypatch)
    fill(folder, LATEST)
    assert sync_firmware.main(["sync_firmware.py", "--newer"]) == 0
    assert "All the firmware matches the release v0.4.5." in capsys.readouterr().out


def test_an_older_or_missing_image_is_reported_in_the_language_asked_for(folder, monkeypatch, capsys):
    release_answers(monkeypatch)
    fill(folder, {**LATEST, ("MAIN", "FIRMWARE"): "0.4.4"})
    (folder / "URTC_SLAVE_BOOTLOADER_v0.3.1.bin").unlink()
    assert sync_firmware.main(["sync_firmware.py", "--newer", "--language", "spanish"]) == 1
    out = capsys.readouterr().out
    assert "tienes la 0.4.4, la release v0.4.5 trae la 0.4.5" in out
    assert "no tienes imagen para ella" in out


def test_a_test_build_newer_than_the_release_is_not_a_failure(folder, monkeypatch, capsys):
    release_answers(monkeypatch)
    fill(folder, {**LATEST, ("MAIN", "FIRMWARE"): "0.5.0"})
    assert sync_firmware.main(["sync_firmware.py", "--newer"]) == 0
    assert "not a published version" in capsys.readouterr().out


def test_refresh_asks_again_and_the_cache_lives_in_the_data_folder_of_the_program(folder, monkeypatch, tmp_path):
    calls = release_answers(monkeypatch)
    fill(folder, LATEST)
    sync_firmware.main(["sync_firmware.py", "--newer"])
    sync_firmware.main(["sync_firmware.py", "--newer", "--refresh"])
    assert [force for _cache, force in calls] == [False, True]
    assert all(Path(cache).parent == tmp_path / "data" / "urtc-flasher" for cache, _force in calls)


def test_a_failed_check_is_a_message_and_exit_2_not_a_traceback(folder, monkeypatch, capsys):
    def refuse(*args, **kwargs):
        raise fc.FirmwareCheckError("rate_limit", "HTTP 403")

    monkeypatch.setattr(fc, "latest_release", refuse)
    assert sync_firmware.main(["sync_firmware.py", "--newer", "--language", "german"]) == 2
    assert "Das Anfragelimit von GitHub wurde erreicht" in capsys.readouterr().out


def test_the_default_network_path_only_asks_the_api_host(monkeypatch, tmp_path):
    seen = []

    def fetch(url):
        seen.append(url)
        raise urllib.error.URLError("offline")

    with pytest.raises(fc.FirmwareCheckError):
        fc.latest_release(fetch, tmp_path / "cache.json")
    assert seen == ["https://api.github.com/repos/JuanenRac/URTC/releases/latest"]
