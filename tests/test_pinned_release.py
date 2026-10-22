# =============================================================================
# URTC Flasher - tests/test_pinned_release.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""While the project has no official release GitHub's "latest" answers 404 (it does not count a pre-release): the release named in firmware_release.json is
used instead, and only then - a tag the person typed is never replaced, and any other failure is shown as it is."""
from __future__ import annotations

import json

import pytest

import flasher_github
from flasher_github import GitHubDownloadError, fetch_release_or_pinned, pinned_release_tag


def _not_found() -> GitHubDownloadError:
    error = GitHubDownloadError("not found")
    error.not_found = True
    return error


class Fetcher:
    def __init__(self, fail_latest: bool, other_error: Exception | None = None) -> None:
        self.calls: list[object] = []
        self.fail_latest = fail_latest
        self.other_error = other_error

    def __call__(self, tag=None, log=None, only_firmware=True):
        self.calls.append(tag)
        if tag is None and self.other_error is not None:
            raise self.other_error
        if tag is None and self.fail_latest:
            raise _not_found()
        return (tag or "v1.0.0"), [{"name": "a.bin", "size": 1, "download_url": "x"}]


def test_the_pin_file_is_read_and_checked(tmp_path):
    path = tmp_path / "firmware_release.json"
    assert pinned_release_tag(str(path)) is None
    path.write_text(json.dumps({"fallback_tag": "v0.3.8"}), encoding="utf-8")
    assert pinned_release_tag(str(path)) == "v0.3.8"
    for bad in ('{"fallback_tag": "../x"}', '{"fallback_tag": 8}', "[1]", "not json", "{}"):
        path.write_text(bad, encoding="utf-8")
        assert pinned_release_tag(str(path)) is None, bad


def test_the_repository_pin_names_a_tag():
    assert pinned_release_tag() is not None


def test_the_newest_release_is_used_when_there_is_one():
    fetch = Fetcher(fail_latest=False)
    assert fetch_release_or_pinned(None, pinned="v0.3.8", fetch=fetch)[0] == "v1.0.0"
    assert fetch.calls == [None]


def test_without_a_release_the_pinned_one_is_used_and_the_log_says_so():
    fetch = Fetcher(fail_latest=True)
    lines: list[str] = []
    tag, entries = fetch_release_or_pinned(None, log=lines.append, pinned="v0.3.8", fetch=fetch)
    assert tag == "v0.3.8" and entries and fetch.calls == [None, "v0.3.8"]
    assert any("v0.3.8" in line and "firmware_release.json" in line for line in lines)


def test_a_tag_that_was_asked_for_is_never_replaced():
    fetch = Fetcher(fail_latest=True)

    def not_found_tag(tag=None, log=None, only_firmware=True):
        raise _not_found()

    with pytest.raises(GitHubDownloadError):
        fetch_release_or_pinned("v9.9.9", pinned="v0.3.8", fetch=not_found_tag)
    assert fetch.calls == []


def test_only_a_missing_release_is_answered_by_the_pin():
    other = GitHubDownloadError("rate limited")
    fetch = Fetcher(fail_latest=False, other_error=other)
    with pytest.raises(GitHubDownloadError, match="rate limited"):
        fetch_release_or_pinned(None, pinned="v0.3.8", fetch=fetch)
    assert fetch.calls == [None]


def test_with_no_pin_the_error_stays(monkeypatch):
    monkeypatch.setattr(flasher_github, "pinned_release_tag", lambda path=None: None)
    with pytest.raises(GitHubDownloadError):
        fetch_release_or_pinned(None, fetch=Fetcher(fail_latest=True))


def test_a_404_from_the_api_is_marked_as_not_found(monkeypatch):
    import urllib.error
    from email.message import Message

    def refuse(req, timeout=0):
        raise urllib.error.HTTPError("https://api.github.com/x", 404, "nf", Message(), None)

    monkeypatch.setattr(flasher_github.urllib.request, "urlopen", refuse)
    with pytest.raises(GitHubDownloadError) as info:
        flasher_github.fetch_release()
    assert info.value.not_found is True
    assert GitHubDownloadError("x").not_found is False
