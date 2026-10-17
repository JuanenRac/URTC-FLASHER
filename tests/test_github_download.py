# =============================================================================
# URTC Flasher - tests/test_github_download.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""The GitHub download path: the assets of a release are listed through the
Releases API, only .bin images and their sidecars are offered, the file hosts
are restricted (asset address on github.com, storage hosts after the
redirect), a short or padded body is discarded, and a 403 is only called a
rate limit when GitHub says so."""
from __future__ import annotations

import io
import json
import urllib.error
from email.message import Message

import pytest

import flasher_github
from flasher_github import GitHubDownloadError, download_file, fetch_release, list_firmware_files

ASSET = "https://github.com/JuanenRac/URTC/releases/download/v0.3.5/"
STORAGE = "https://objects.githubusercontent.com/github-production-release-asset/1/x.bin"


class FakeResponse(io.BytesIO):
    def __init__(self, body, url=STORAGE, length="auto"):
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


def _release(names, tag="v0.3.5", **extra):
    return json.dumps({
        "tag_name": tag,
        "assets": [{"name": n, "size": 10, "state": "uploaded", "browser_download_url": ASSET + n, **extra} for n in names],
    }).encode()


def test_listing_keeps_only_bin_images_and_their_sidecars(monkeypatch):
    names = ["a.bin", "a.bin.sha256", "a.bin.manifest.json", "firmware_manifest.json", "a.elf", "a.hex", "notes.txt"]
    monkeypatch.setattr(flasher_github.urllib.request, "urlopen", lambda req, timeout=0: FakeResponse(_release(names)))
    listed = [e["name"] for e in list_firmware_files()]
    assert listed == ["a.bin", "a.bin.sha256", "a.bin.manifest.json"]


def test_the_sync_tool_can_ask_for_every_asset_and_gets_the_tag(monkeypatch):
    names = ["a.bin", "firmware_manifest.json", "a.hex"]
    monkeypatch.setattr(flasher_github.urllib.request, "urlopen", lambda req, timeout=0: FakeResponse(_release(names)))
    tag, entries = fetch_release(only_firmware=False)
    assert tag == "v0.3.5"
    assert [e["name"] for e in entries] == names
    assert entries[0] == {"name": "a.bin", "size": 10, "download_url": ASSET + "a.bin"}


def test_latest_release_and_a_chosen_tag_use_the_right_api_address(monkeypatch):
    seen = []

    def fake_urlopen(req, timeout=0):
        seen.append(req.full_url)
        return FakeResponse(_release([]))

    monkeypatch.setattr(flasher_github.urllib.request, "urlopen", fake_urlopen)
    fetch_release()
    fetch_release("v0.3.4")
    fetch_release("0.3.3")  # the leading v is optional
    assert seen == [
        "https://api.github.com/repos/JuanenRac/URTC/releases/latest",
        "https://api.github.com/repos/JuanenRac/URTC/releases/tags/v0.3.4",
        "https://api.github.com/repos/JuanenRac/URTC/releases/tags/v0.3.3",
    ]


@pytest.mark.parametrize("tag", ["../x", "v1/../../repos", "a b", "v1?x=1"])
def test_a_tag_that_is_not_a_tag_never_reaches_the_network(monkeypatch, tag):
    def never(req, timeout=0):
        raise AssertionError("no request may be made")

    monkeypatch.setattr(flasher_github.urllib.request, "urlopen", never)
    with pytest.raises(GitHubDownloadError):
        fetch_release(tag)


def test_assets_still_uploading_and_names_with_paths_are_not_offered(monkeypatch):
    body = json.dumps({"tag_name": "v1", "assets": [
        {"name": "a.bin", "size": 1, "state": "starter", "browser_download_url": ASSET + "a.bin"},
        {"name": "../b.bin", "size": 1, "state": "uploaded", "browser_download_url": ASSET + "b.bin"},
        {"name": "c.bin", "size": 1, "state": "uploaded", "browser_download_url": ASSET + "c.bin"},
    ]}).encode()
    monkeypatch.setattr(flasher_github.urllib.request, "urlopen", lambda req, timeout=0: FakeResponse(body))
    assert [e["name"] for e in list_firmware_files()] == ["c.bin"]


@pytest.mark.parametrize("body", [b"[]", b"{}", b'{"assets": 3}', b"not json"])
def test_an_unexpected_listing_is_an_error_not_an_empty_list(monkeypatch, body):
    monkeypatch.setattr(flasher_github.urllib.request, "urlopen", lambda req, timeout=0: FakeResponse(body))
    with pytest.raises(GitHubDownloadError):
        list_firmware_files()


def test_token_is_sent_to_the_api_only_when_set(monkeypatch):
    seen = []

    def fake_urlopen(req, timeout=0):
        seen.append(req.get_header("Authorization"))
        return FakeResponse(_release([]))

    monkeypatch.setattr(flasher_github.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    list_firmware_files()
    monkeypatch.setenv("GITHUB_TOKEN", "abc")
    list_firmware_files()
    assert seen == [None, "Bearer abc"]


def test_the_token_is_never_sent_to_the_file_host(monkeypatch, tmp_path):
    seen = []

    def fake_urlopen(req, timeout=0):
        seen.append(req.get_header("Authorization"))
        return FakeResponse(b"x")

    monkeypatch.setattr(flasher_github.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("GITHUB_TOKEN", "abc")
    download_file(ASSET + "x.bin", str(tmp_path / "x.bin"))
    assert seen == [None]


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
    assert download_file(ASSET + "x.bin", str(dest), expected_size=5000) == 5000
    assert dest.read_bytes() == body


@pytest.mark.parametrize("storage", [
    "https://objects.githubusercontent.com/x/y.bin",
    "https://release-assets.githubusercontent.com/x/y.bin",
    ASSET + "x.bin",  # no redirect at all
])
def test_the_asset_storage_hosts_are_accepted_after_the_redirect(monkeypatch, tmp_path, storage):
    monkeypatch.setattr(flasher_github.urllib.request, "urlopen", lambda req, timeout=0: FakeResponse(b"abc", url=storage))
    assert download_file(ASSET + "x.bin", str(tmp_path / "x.bin")) == 3


def test_truncated_download_is_discarded(monkeypatch, tmp_path):
    body = b"x" * 100
    monkeypatch.setattr(flasher_github.urllib.request, "urlopen",
                        lambda req, timeout=0: FakeResponse(body, length=200))
    dest = tmp_path / "x.bin"
    with pytest.raises(GitHubDownloadError):
        download_file(ASSET + "x.bin", str(dest))
    assert not dest.exists()
    assert not (tmp_path / "x.bin.part").exists()


def test_size_from_listing_is_enforced(monkeypatch, tmp_path):
    monkeypatch.setattr(flasher_github.urllib.request, "urlopen",
                        lambda req, timeout=0: FakeResponse(b"x" * 100, length=None))
    dest = tmp_path / "x.bin"
    with pytest.raises(GitHubDownloadError):
        download_file(ASSET + "x.bin", str(dest), expected_size=101)
    assert not dest.exists()


@pytest.mark.parametrize("url", [
    "https://evil.example.com/x.bin",
    "http://github.com/JuanenRac/URTC/releases/download/v0.3.5/x.bin",
    "https://github.com.evil.example/JuanenRac/URTC/releases/download/v0.3.5/x.bin",
    "https://objects.githubusercontent.com.evil.example/x.bin",
    "https://raw.githubusercontent.com/JuanenRac/URTC/main/firmware/x.bin",
    # github.com itself, but not an asset of this project's releases
    "https://github.com/someone/else/releases/download/v1/x.bin",
    "https://github.com/JuanenRac/URTC/archive/refs/heads/main.zip",
])
def test_foreign_address_is_refused_before_any_request(monkeypatch, tmp_path, url):
    def never(req, timeout=0):
        raise AssertionError("no request may be made")

    monkeypatch.setattr(flasher_github.urllib.request, "urlopen", never)
    with pytest.raises(GitHubDownloadError):
        download_file(url, str(tmp_path / "x.bin"))


@pytest.mark.parametrize("final", [
    "https://evil.example.com/x.bin",
    "http://objects.githubusercontent.com/x.bin",
    "https://raw.githubusercontent.com/JuanenRac/URTC/main/x.bin",
])
def test_redirect_to_a_foreign_host_is_refused(monkeypatch, tmp_path, final):
    monkeypatch.setattr(flasher_github.urllib.request, "urlopen",
                        lambda req, timeout=0: FakeResponse(b"x", url=final))
    with pytest.raises(GitHubDownloadError):
        download_file(ASSET + "x.bin", str(tmp_path / "x.bin"))
    assert not (tmp_path / "x.bin").exists()
