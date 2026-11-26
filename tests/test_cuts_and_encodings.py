# =============================================================================
# URTC-FLASHER - tests/test_cuts_and_encodings.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Downloads cut in the middle, and the files that travel with an image or hold the options when a Windows editor or shell
saved them with a byte-order mark or in UTF-16. The network is replaced by functions; nothing leaves the machine."""
from __future__ import annotations

import hashlib
import http.client
import io
import json
import os

import pytest

import flasher_config
import flasher_github
import flasher_integrity


class Answer(io.BytesIO):
    def __init__(self, failure, url="https://github.com/x"):
        super().__init__()
        self.failure = failure
        self.headers = {"Content-Length": "100"}
        self.url = url

    def read(self, *args):
        raise self.failure

    def geturl(self):
        return self.url

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


CUTS = [http.client.IncompleteRead(b"{", 100), ConnectionResetError("reset by peer")]


@pytest.mark.parametrize("failure", CUTS, ids=["incomplete", "reset"])
def test_a_cut_release_listing_is_a_message(monkeypatch, failure):
    monkeypatch.setattr(flasher_github.urllib.request, "urlopen", lambda *a, **k: Answer(failure))
    with pytest.raises(flasher_github.GitHubDownloadError):
        flasher_github.fetch_release()


def test_an_answer_that_is_not_text_is_a_message(monkeypatch):
    monkeypatch.setattr(flasher_github.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(b'{"assets": "\xff\xfe\xfd"}'))
    with pytest.raises(flasher_github.GitHubDownloadError):
        flasher_github.fetch_release()


def test_an_asset_with_a_name_that_is_not_text_is_left_out(monkeypatch):
    body = {"tag_name": "v1", "assets": [{"name": 5, "browser_download_url": "https://github.com/a"},
                                         {"name": "A.bin", "browser_download_url": 7},
                                         {"name": "B.bin", "browser_download_url": "https://github.com/b", "size": 1}]}
    monkeypatch.setattr(flasher_github.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(json.dumps(body).encode()))
    assert [entry["name"] for entry in flasher_github.fetch_release()[1]] == ["B.bin"]


@pytest.mark.parametrize("failure", CUTS, ids=["incomplete", "reset"])
def test_a_download_cut_in_the_middle_is_a_message_and_leaves_nothing(monkeypatch, tmp_path, failure):
    url = f"https://github.com/{flasher_github.GITHUB_REPO}/releases/download/v1/A.bin"
    monkeypatch.setattr(flasher_github.urllib.request, "urlopen", lambda *a, **k: Answer(failure, url))
    target = tmp_path / "A.bin"
    with pytest.raises(flasher_github.GitHubDownloadError) as stop:
        flasher_github.download_file(url, str(target))
    assert os.listdir(tmp_path) == []
    assert str(failure) in str(stop.value) or "IncompleteRead" in str(stop.value) or "reset" in str(stop.value)


ENCODINGS = ["utf-8-sig", "utf-16"]


@pytest.mark.parametrize("encoding", ENCODINGS)
def test_a_published_digest_saved_with_a_byte_order_mark_still_blocks_another_image(tmp_path, encoding):
    image = tmp_path / "image.bin"
    image.write_bytes(b"the image")
    sidecar = tmp_path / "image.bin.sha256"
    sidecar.write_text("0" * 64 + "  image.bin\n", encoding=encoding)
    assert flasher_integrity.preflight_image(str(image)).blocked, "a digest that does not match was ignored"
    sidecar.write_text(hashlib.sha256(b"the image").hexdigest() + "\n", encoding=encoding)
    result = flasher_integrity.preflight_image(str(image))
    assert result.verified and not result.blocked


@pytest.mark.parametrize("encoding", ENCODINGS)
def test_a_manifest_saved_with_a_byte_order_mark_is_read(tmp_path, encoding):
    image = tmp_path / "image.bin"
    image.write_bytes(b"x")
    (tmp_path / "image.bin.manifest.json").write_text(json.dumps({"sha256": "0" * 64, "signing_key_kind": "dev"}), encoding=encoding)
    assert flasher_integrity.read_manifest_sha256(str(image)) == "0" * 64
    assert flasher_integrity.manifest_signing_kind(str(image)) == "dev"
    assert flasher_integrity.preflight_image(str(image)).blocked


@pytest.mark.parametrize("raw", [
    '{"language": "es"}'.encode("utf-16"),
    b'{"hardware_id": "se\xf1al"}',
    b"5",
    b'"hardware_id"',
    b"[1]",
    b"{ cut",
], ids=["utf16", "latin1", "number", "text", "list", "cut"])
def test_a_damaged_options_file_never_stops_the_program(monkeypatch, tmp_path, raw):
    path = tmp_path / "urtc_config.json"
    path.write_bytes(raw)
    monkeypatch.setattr(flasher_config, "CONFIG_FILE_PATH", str(path))
    said: list[str] = []
    result = flasher_config._load_config_overrides(said.append)
    assert result[0] == flasher_config.THIS_HARDWARE_ID or result[-1] is False
    assert isinstance(flasher_config.load_config(), dict)


def test_an_options_file_with_a_byte_order_mark_is_read(monkeypatch, tmp_path):
    path = tmp_path / "urtc_config.json"
    path.write_bytes(b'\xef\xbb\xbf{"language": "es", "hardware_id": "0x01020304"}')
    monkeypatch.setattr(flasher_config, "CONFIG_FILE_PATH", str(path))
    assert flasher_config.load_config()["language"] == "es"
    assert flasher_config._load_config_overrides()[0] == 0x01020304
