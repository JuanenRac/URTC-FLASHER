# =============================================================================
# URTC Flasher - tests/test_github_download.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""The GitHub download path: only .bin images and their sidecars are listed,
the file host is restricted, a short or padded body is discarded, and a 403
is only called a rate limit when GitHub says so."""
from __future__ import annotations

import io
import json
import urllib.error
from email.message import Message

import pytest

import flasher_github
from flasher_github import GitHubDownloadError, download_file, list_firmware_files

RAW = "https://raw.githubusercontent.com/JuanenRac/URTC/main/firmware/"


class FakeResponse(io.BytesIO):
    def __init__(self, body, url=RAW + "x.bin", length="auto"):
        super().__init__(body)
        self.headers = Message()
        if length == "auto":
            length = len(body)
        if length is not None:
            self.headers["Content-Length"] = str(length)
        self._url = url

    def geturl(self):
        return self._url


def _http_error(code, **headers):
    msg = Message()
    for key, value in headers.items():
        msg[key.replace("_", "-")] = value
    return urllib.error.HTTPError("https://api.github.com/x", code, "err", msg, None)


def test_listing_keeps_only_bin_images_and_their_sidecars(monkeypatch):
    names = ["a.bin", "a.bin.sha256", "a.bin.manifest.json", "firmware_manifest.json", "a.elf", "a.hex", "notes.txt"]
    payload = json.dumps([
        {"name": n, "type": "file", "size": 10, "download_url": RAW + n} for n in names
    ]).encode()
    monkeypatch.setattr(flasher_github.urllib.request, "urlopen", lambda req, timeout=0: FakeResponse(payload))
    listed = [e["name"] for e in list_firmware_files()]
    assert listed == ["a.bin", "a.bin.sha256", "a.bin.manifest.json"]


def test_token_is_sent_to_the_api_only_when_set(monkeypatch):
    seen = []

    def fake_urlopen(req, timeout=0):
        seen.append(req.get_header("Authorization"))
        return FakeResponse(b"[]")

    monkeypatch.setattr(flasher_github.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    list_firmware_files()
    monkeypatch.setenv("GITHUB_TOKEN", "abc")
    list_firmware_files()
    assert seen == [None, "Bearer abc"]


@pytest.mark.parametrize("headers,expect_rate", [
    ({"X_RateLimit_Remaining": "0"}, True),
    ({"Retry_After": "60"}, True),
    ({}, False),
])
def test_403_is_a_rate_limit_only_when_github_says_so(monkeypatch, headers, expect_rate):
    def boom(req, timeout=0):
        raise _http_error(403, **headers)

    monkeypatch.setattr(flasher_github.urllib.request, "urlopen", boom)
    with pytest.raises(GitHubDownloadError) as info:
        list_firmware_files()
    assert ("HTTP 403" not in str(info.value)) is expect_rate


def test_download_writes_file_when_size_matches(monkeypatch, tmp_path):
    body = b"x" * 5000
    monkeypatch.setattr(flasher_github.urllib.request, "urlopen", lambda req, timeout=0: FakeResponse(body))
    dest = tmp_path / "x.bin"
    assert download_file(RAW + "x.bin", str(dest), expected_size=5000) == 5000
    assert dest.read_bytes() == body


def test_truncated_download_is_discarded(monkeypatch, tmp_path):
    body = b"x" * 100
    monkeypatch.setattr(flasher_github.urllib.request, "urlopen",
                        lambda req, timeout=0: FakeResponse(body, length=200))
    dest = tmp_path / "x.bin"
    with pytest.raises(GitHubDownloadError):
        download_file(RAW + "x.bin", str(dest))
    assert not dest.exists()
    assert not (tmp_path / "x.bin.part").exists()


def test_size_from_listing_is_enforced(monkeypatch, tmp_path):
    monkeypatch.setattr(flasher_github.urllib.request, "urlopen",
                        lambda req, timeout=0: FakeResponse(b"x" * 100, length=None))
    dest = tmp_path / "x.bin"
    with pytest.raises(GitHubDownloadError):
        download_file(RAW + "x.bin", str(dest), expected_size=101)
    assert not dest.exists()


@pytest.mark.parametrize("url", [
    "https://evil.example.com/x.bin",
    "http://raw.githubusercontent.com/x.bin",
    "https://raw.githubusercontent.com.evil.example/x.bin",
])
def test_foreign_host_is_refused_before_any_request(monkeypatch, tmp_path, url):
    def never(req, timeout=0):
        raise AssertionError("no request may be made")

    monkeypatch.setattr(flasher_github.urllib.request, "urlopen", never)
    with pytest.raises(GitHubDownloadError):
        download_file(url, str(tmp_path / "x.bin"))


def test_redirect_to_a_foreign_host_is_refused(monkeypatch, tmp_path):
    monkeypatch.setattr(flasher_github.urllib.request, "urlopen",
                        lambda req, timeout=0: FakeResponse(b"x", url="https://evil.example.com/x.bin"))
    with pytest.raises(GitHubDownloadError):
        download_file(RAW + "x.bin", str(tmp_path / "x.bin"))
    assert not (tmp_path / "x.bin").exists()
