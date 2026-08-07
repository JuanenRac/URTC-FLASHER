# =============================================================================
# URTC Flasher - Download firmware directly from the project's own GitHub
# repository (github.com/JuanenRac/URTC, firmware/ folder).
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Uses only Python's own standard library (urllib, json) - deliberately no
# `requests` or other third-party HTTP dependency, since this is a
# distributed desktop app and every extra dependency is one more thing a
# person has to `pip install` (or one more thing PyInstaller has to bundle)
# before this tool runs at all.
#
# IMPORTANT CAVEAT, stated plainly rather than buried: the exact JSON shape
# GitHub's own Contents API returns was NOT verified against a live call to
# this project's own real repository while writing this - every attempt
# from this development environment hit GitHub's own unauthenticated rate
# limit (60 requests/hour, shared across whatever pool of outbound IPs this
# sandbox sits behind, already exhausted by other traffic on every retry).
# What's implemented here follows GitHub's own publicly documented Contents
# API response shape (a stable, widely-used public API, unlikely to have
# quietly changed shape) - but "documented" isn't the same confidence level
# as "confirmed against a real response from this project's own repo," and
# that gap is real. Test this against the actual repository once it's
# reachable, before trusting it blindly.
# =============================================================================
import json
import os
import urllib.error
import urllib.request

from flasher_config import _

GITHUB_API_BASE = "https://api.github.com/repos/JuanenRac/URTC/contents/firmware"
GITHUB_REPO_URL = "https://github.com/JuanenRac/URTC"
USER_AGENT = "URTC-Flasher"  # GitHub's own API rejects requests with no User-Agent header at all


class GitHubDownloadError(Exception):
    pass


def list_firmware_files(log=None):
    """Fetches the file listing from this project's own GitHub repository
    (firmware/ folder), via GitHub's Contents API
    (GET /repos/{owner}/{repo}/contents/{path}). Returns a list of dicts,
    each with at least "name", "size", and "download_url" - the 3 fields
    this module's own download_file() actually needs, deliberately not the
    full raw API response (which also carries "sha", "url", "git_url",
    "html_url", "type", "_links" - all real per GitHub's own documented
    shape, none of them used here). Raises GitHubDownloadError with a
    human-readable reason on any failure (network unreachable, rate
    limited, repository/folder not found, unexpected response shape) -
    the caller's job is to show that reason to the person, not to guess
    at it.
    """
    req = urllib.request.Request(GITHUB_API_BASE, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
    })
    if log:
        log(_("LOG_GITHUB_FETCHING_LIST"))
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            raw = response.read()
    except urllib.error.HTTPError as e:
        if e.code == 403:
            raise GitHubDownloadError(_("ERR_GITHUB_RATE_LIMITED"))
        if e.code == 404:
            raise GitHubDownloadError(_("ERR_GITHUB_NOT_FOUND"))
        raise GitHubDownloadError(_("ERR_GITHUB_HTTP_ERROR", code=e.code))
    except urllib.error.URLError as e:
        raise GitHubDownloadError(_("ERR_GITHUB_NETWORK", reason=e.reason))
    except TimeoutError:
        raise GitHubDownloadError(_("ERR_GITHUB_TIMEOUT"))

    try:
        entries = json.loads(raw)
    except json.JSONDecodeError:
        raise GitHubDownloadError(_("ERR_GITHUB_BAD_RESPONSE"))

    if not isinstance(entries, list):
        # A single-file path (not a folder) returns a dict, not a list -
        # per GitHub's own documented Contents API behavior. This
        # module's own GITHUB_API_BASE is a folder path, so a dict here
        # means something unexpected happened upstream (the folder was
        # replaced with a file of the same name, or the API's own
        # response shape genuinely changed) - surfaced as an error
        # rather than this function silently returning something the
        # caller can't iterate over the way it expects.
        raise GitHubDownloadError(_("ERR_GITHUB_UNEXPECTED_SHAPE"))

    results = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        # "type": "file" per GitHub's own documented values ("file",
        # "dir", "symlink", "submodule") - skip anything that isn't a
        # plain file (a subfolder under firmware/, if one ever exists,
        # shouldn't show up as something this tool tries to download and
        # save as a firmware image).
        if entry.get("type") != "file":
            continue
        name = entry.get("name")
        download_url = entry.get("download_url")
        if not name or not download_url:
            continue
        results.append({
            "name": name,
            "size": entry.get("size", 0),
            "download_url": download_url,
        })

    if log:
        log(_("LOG_GITHUB_LIST_COUNT", count=len(results)))
    return results


def download_file(download_url, dest_path, log=None, progress_cb=None):
    """Downloads a single file from download_url (as returned by
    list_firmware_files above) to dest_path, streamed in chunks rather
    than loaded whole into memory - a firmware binary is only ever a few
    hundred KB, but there's no reason to assume that stays true forever,
    and streaming costs nothing extra here. Returns the number of bytes
    written. Raises GitHubDownloadError on any failure, same reasoning as
    list_firmware_files above."""
    req = urllib.request.Request(download_url, headers={"User-Agent": USER_AGENT})
    if log:
        log(_("LOG_GITHUB_DOWNLOADING", name=os.path.basename(dest_path)))
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            total_size = int(response.headers.get("Content-Length", 0))
            written = 0
            # Write to a temp path first, rename into place only once
            # the full download succeeds - a connection dropped mid-
            # transfer should never leave a truncated, silently-wrong
            # firmware file sitting under its own real name where a
            # later flash could pick it up without anyone noticing it's
            # incomplete.
            tmp_path = dest_path + ".part"
            with open(tmp_path, "wb") as f:
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
                    written += len(chunk)
                    if progress_cb and total_size > 0:
                        progress_cb(int((written / total_size) * 100))
            os.replace(tmp_path, dest_path)
    except urllib.error.HTTPError as e:
        raise GitHubDownloadError(_("ERR_GITHUB_HTTP_ERROR", code=e.code))
    except urllib.error.URLError as e:
        raise GitHubDownloadError(_("ERR_GITHUB_NETWORK", reason=e.reason))
    except TimeoutError:
        raise GitHubDownloadError(_("ERR_GITHUB_TIMEOUT"))
    except OSError as e:
        raise GitHubDownloadError(_("ERR_GITHUB_WRITE_FAILED", reason=e))

    if log:
        log(_("LOG_GITHUB_DOWNLOAD_COMPLETE", name=os.path.basename(dest_path), size=written))
    return written
