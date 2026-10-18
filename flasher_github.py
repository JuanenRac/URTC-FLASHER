# =============================================================================
# URTC Flasher - Download firmware from the assets of a GitHub release of the
# project's own repository (github.com/JuanenRac/URTC).
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The URTC firmware binaries are not versioned in git: each release carries
# them as assets (the images, their .sha256 and .manifest.json files and
# firmware_manifest.json). This module lists the assets of the latest release
# (or of a chosen tag) through GitHub's Releases API and downloads them.
#
# Uses only Python's own standard library (urllib, json) - deliberately no
# `requests` or other third-party HTTP dependency, since this is a
# distributed desktop app and every extra dependency is one more thing a
# person has to `pip install` (or one more thing PyInstaller has to bundle)
# before this tool runs at all.
#
# What a download is trusted for: the listing is data from the network, so a
# file is only fetched from GitHub's own hosts (github.com for the asset
# address, and the asset storage hosts it redirects to), over https, and what
# arrives is compared with the size the release announces. The signature and
# digests that matter for flashing travel in the manifests and are checked
# again before anything is sent to a board.
# =============================================================================
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

from flasher_config import _

GITHUB_REPO = "JuanenRac/URTC"
GITHUB_API_BASE = "https://api.github.com/repos/" + GITHUB_REPO + "/releases"
GITHUB_REPO_URL = "https://github.com/" + GITHUB_REPO
# The only hosts a listed file may be downloaded from. An asset address is on
# github.com and answers with a redirect to GitHub's asset storage
# (objects.githubusercontent.com, and release-assets.githubusercontent.com for
# newer uploads); the check runs before the request and again on the address
# the response really came from.
ALLOWED_DOWNLOAD_HOSTS = (
    "github.com",
    "objects.githubusercontent.com",
    "release-assets.githubusercontent.com",
)
USER_AGENT = "URTC-Flasher"  # GitHub's own API rejects requests with no User-Agent header at all
_TAG_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class GitHubDownloadError(Exception):
    pass


def _check_download_host(url):
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or host not in ALLOWED_DOWNLOAD_HOSTS:
        raise GitHubDownloadError(_("ERR_GITHUB_BAD_HOST", host=host or url))


def _is_rate_limited(error):
    """A 403 from the API is a rate limit only when GitHub says so (no
    requests left in the window, or a Retry-After); any other 403 is a
    refusal for a different reason and must not be reported as one."""
    headers = error.headers
    if headers is None:
        return False
    return headers.get("X-RateLimit-Remaining") == "0" or headers.get("Retry-After") is not None


def _release_url(tag):
    if tag is None or not str(tag).strip():
        return GITHUB_API_BASE + "/latest"
    tag = str(tag).strip()
    if tag[0].isdigit():
        tag = "v" + tag  # "0.3.5" and "v0.3.5" name the same release
    if not _TAG_PATTERN.match(tag):
        raise GitHubDownloadError(_("ERR_GITHUB_BAD_TAG", tag=tag))
    return GITHUB_API_BASE + "/tags/" + urllib.parse.quote(tag)


def fetch_release(tag=None, log=None, only_firmware=True):
    """Lists the assets of a release of this project's own repository through
    GitHub's Releases API (GET /repos/{owner}/{repo}/releases/latest, or
    /releases/tags/{tag} for a chosen one). Returns (tag_name, entries), each
    entry a dict with the 3 fields download_file() needs: "name", "size" and
    "download_url" (the asset's browser_download_url, on github.com). With
    only_firmware (the default) the list is reduced to the images and the
    files that travel with them (.bin, .sha256, .manifest.json); with False
    it holds every uploaded asset (the sync tool also wants
    firmware_manifest.json). Raises GitHubDownloadError with a human-readable
    reason on any failure (network unreachable, rate limited, release not
    found, unexpected response shape) - the caller's job is to show that
    reason to the person, not to guess at it.
    """
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
    }
    # Optional: an authenticated request has a far higher rate limit. The
    # token is only ever sent to the API itself, never to the file host.
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(_release_url(tag), headers=headers)
    if log:
        log(_("LOG_GITHUB_FETCHING_LIST"))
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            raw = response.read()
    except urllib.error.HTTPError as e:
        if e.code == 403:
            if _is_rate_limited(e):
                raise GitHubDownloadError(_("ERR_GITHUB_RATE_LIMITED")) from e
            raise GitHubDownloadError(_("ERR_GITHUB_FORBIDDEN")) from e
        if e.code == 429:
            raise GitHubDownloadError(_("ERR_GITHUB_RATE_LIMITED")) from e
        if e.code == 404:
            raise GitHubDownloadError(_("ERR_GITHUB_NOT_FOUND")) from e
        raise GitHubDownloadError(_("ERR_GITHUB_HTTP_ERROR", code=e.code)) from e
    except urllib.error.URLError as e:
        raise GitHubDownloadError(_("ERR_GITHUB_NETWORK", reason=e.reason)) from e
    except TimeoutError:
        raise GitHubDownloadError(_("ERR_GITHUB_TIMEOUT")) from None

    try:
        release = json.loads(raw)
    except json.JSONDecodeError:
        raise GitHubDownloadError(_("ERR_GITHUB_BAD_RESPONSE")) from None

    if not isinstance(release, dict) or not isinstance(release.get("assets"), list):
        raise GitHubDownloadError(_("ERR_GITHUB_UNEXPECTED_SHAPE"))
    tag_name = str(release.get("tag_name") or "")

    results = []
    for asset in release["assets"]:
        if not isinstance(asset, dict):
            continue
        name = asset.get("name")
        download_url = asset.get("browser_download_url")
        if not name or not download_url:
            continue
        # An asset still being uploaded is not a complete file.
        if asset.get("state", "uploaded") != "uploaded":
            continue
        # A file name from the network becomes a path on this machine: only a plain name.
        if os.path.basename(name) != name or name in (".", ".."):
            continue
        if only_firmware and not (name.endswith(".bin") or name.endswith(SIDECAR_SUFFIXES)):
            continue
        results.append({
            "name": name,
            "size": asset.get("size", 0),
            "download_url": download_url,
        })

    if log:
        log(_("LOG_GITHUB_RELEASE_TAG", tag=tag_name or "?"))
        log(_("LOG_GITHUB_LIST_COUNT", count=len(results)))
    return tag_name, results


def list_firmware_files(log=None, tag=None):
    """The firmware files (images and their sidecars) of the latest release,
    or of `tag`: the list half of fetch_release()."""
    return fetch_release(tag, log=log)[1]


def download_file(download_url, dest_path, log=None, progress_cb=None, expected_size=None):
    """Downloads a single file from download_url (as returned by
    fetch_release above) to dest_path, streamed in chunks rather
    than loaded whole into memory - a firmware binary is only ever a few
    hundred KB, but there's no reason to assume that stays true forever,
    and streaming costs nothing extra here. Returns the number of bytes
    written. Raises GitHubDownloadError on any failure, same reasoning as
    fetch_release above."""
    _check_download_host(download_url)
    parsed = urllib.parse.urlparse(download_url)
    if (parsed.hostname or "").lower() == "github.com" and not parsed.path.startswith("/" + GITHUB_REPO + "/releases/download/"):
        raise GitHubDownloadError(_("ERR_GITHUB_BAD_HOST", host=download_url))  # an asset of this project's releases only, not any other path on github.com
    req = urllib.request.Request(download_url, headers={"User-Agent": USER_AGENT})
    if log:
        log(_("LOG_GITHUB_DOWNLOADING", name=os.path.basename(dest_path)))
    written = 0  # set before the try so the finally block below can safely reference it even if urlopen() itself fails before any bytes are written
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            _check_download_host(response.geturl())  # after any redirect
            try:
                total_size = int(response.headers.get("Content-Length", 0))
            except (TypeError, ValueError):
                total_size = 0
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
            # A truncated or padded body is not a firmware image: compare
            # with what the server announced and with the listing's size.
            for expected in (total_size, expected_size):
                if expected and written != expected:
                    raise GitHubDownloadError(_(
                        "ERR_GITHUB_SIZE_MISMATCH",
                        name=os.path.basename(dest_path), got=written, expected=expected,
                    ))
            os.replace(tmp_path, dest_path)
    except GitHubDownloadError:
        raise
    except urllib.error.HTTPError as e:
        raise GitHubDownloadError(_("ERR_GITHUB_HTTP_ERROR", code=e.code)) from e
    except urllib.error.URLError as e:
        raise GitHubDownloadError(_("ERR_GITHUB_NETWORK", reason=e.reason)) from e
    except TimeoutError:
        raise GitHubDownloadError(_("ERR_GITHUB_TIMEOUT")) from None
    except OSError as e:
        raise GitHubDownloadError(_("ERR_GITHUB_WRITE_FAILED", reason=e)) from e
    finally:
        # A connection dropped mid-transfer (network error, timeout, or the
        # request failing before any bytes ever arrived) raises out of the
        # "with open(tmp_path, ...)" block before os.replace() ever runs,
        # leaving the half-written ".part" file behind. On success
        # os.replace() has already renamed it away, so this is a no-op then;
        # on failure it's removed here so a retry starts from a fresh file
        # instead of silently reusing (via truncating "wb") a stale partial
        # download, and so a failed download never leaves debris next to
        # FIRMWARE_FOLDER.
        try:
            if os.path.isfile(dest_path + ".part"):
                os.remove(dest_path + ".part")
        except OSError:
            pass

    if log:
        log(_("LOG_GITHUB_DOWNLOAD_COMPLETE", name=os.path.basename(dest_path), size=written))
    return written


SIDECAR_SUFFIXES = (".sha256", ".manifest.json")


def is_sidecar(name):
    """True for the <image>.sha256 / <image>.manifest.json files the URTC
    build publishes next to each image - listed by GitHub as files of their
    own, but they travel with their image rather than being picked alone."""
    return name.endswith(SIDECAR_SUFFIXES)


def sidecars_for(entries, image_name):
    """The listing entries holding `image_name`'s sidecars (its published
    sha256 and its manifest with the signature), in a fixed order."""
    by_name = {entry["name"]: entry for entry in entries}
    return [by_name[image_name + suffix] for suffix in SIDECAR_SUFFIXES if image_name + suffix in by_name]

