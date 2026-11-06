# =============================================================================
# URTC-COMMON - src/urtc_common/firmware_check.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Compare the firmware images a program carries with the newest official release of the firmware repository.

``update_service`` asks GitHub about the release of the PROGRAM; this module asks about the release of the FIRMWARE
(``JuanenRac/URTC``, whose assets are the four images of the two boards) and says, image by image, whether what the
program carries is the published version, an older one, a newer one (a test build) or missing.

* **One request, only when called.** Nothing here runs by itself. The answer is kept in a small cache file for
  ``ttl`` seconds (an hour by default), so asking again does not use up the anonymous limit of the GitHub API
  (60 requests per hour per address); a failed request is not repeated before ``retry_after`` seconds.
* **Only https on the GitHub hosts** (``self_update.check_host``, also after redirects through ``update_service``
  when the default fetch is used), a listing no larger than 2 MiB, and only the official release: ``releases/latest``
  never answers with a pre-release or a draft, and a listing that says it is one is refused.
* **No file is downloaded and nothing is installed.** The result is a list of rows for the window to draw with the texts
  of ``firmware_check_strings`` (eight languages).

No window, no thread, no global state; standard library only.
"""
from __future__ import annotations

import json
import time
import urllib.error
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import firmware_names as names
from . import self_update as su
from . import update_service as svc
from .firmware_check_strings import error_key, text

FIRMWARE_REPO = "JuanenRac/URTC"
CACHE_TTL_SECONDS = 3600
RETRY_AFTER_SECONDS = 60
MAX_LISTING_BYTES = 2 * 1024 * 1024
CACHE_FILE = "firmware_release_cache.json"

CURRENT = "current"
OUTDATED = "outdated"
AHEAD = "ahead"
ABSENT = "absent"
NOT_RELEASED = "not_released"


class FirmwareCheckError(Exception):
    """The check could not be made. ``code`` is stable (``rate_limit``, ``network``, ``no_release``, ``bad_release``, ``too_soon``)."""

    def __init__(self, code: str, text: str = "") -> None:
        super().__init__(text or code)
        self.code = code


@dataclass(frozen=True)
class LatestRelease:
    """The images of the newest official release: ``(board, kind)`` -> version text."""

    tag: str
    images: dict[tuple[str, str], str]
    checked_at: float
    from_cache: bool = False


@dataclass(frozen=True)
class Row:
    board: str
    kind: str
    local: str | None
    latest: str | None
    state: str


def _version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def images_of_release(release: Any) -> dict[tuple[str, str], str]:
    """``(board, kind)`` -> version of the images named by the assets of a release listing; the highest wins when two share a slot."""
    if not isinstance(release, dict) or not isinstance(release.get("assets"), list):
        raise FirmwareCheckError("bad_release", "no list of assets")
    found: dict[tuple[str, str], str] = {}
    for asset in release["assets"]:
        parsed = names.parse_image_name(str(asset.get("name", ""))) if isinstance(asset, dict) else None
        if parsed is None:
            continue
        board, kind, version = parsed
        slot = (board, kind)
        if slot not in found or _version_key(version) > _version_key(found[slot]):
            found[slot] = version
    return found


def images_in(files: Iterable[str]) -> dict[tuple[str, str], str]:
    """``(board, kind)`` -> the highest version among the image file names given (sidecars and other files are ignored)."""
    return images_of_release({"assets": [{"name": Path(str(f)).name} for f in files]})


def images_in_folder(folder: str | Path) -> dict[tuple[str, str], str]:
    """The images found in a folder of firmware (an absent folder holds none)."""
    path = Path(folder)
    try:
        return images_in(entry.name for entry in path.iterdir() if entry.is_file())
    except OSError:
        return {}


def _read_cache(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_cache(path: Path | None, data: dict[str, Any]) -> None:
    if path is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
    except OSError:
        pass  # a cache that cannot be written must not stop a check


def _from_cache(data: dict[str, Any], repo: str, now: float, ttl: float) -> LatestRelease | None:
    try:
        if data.get("repo") != repo or not (0 <= now - float(data["checked_at"]) < ttl):
            return None
        images = {(str(b), str(k)): str(v) for b, k, v in data["images"]}
        return LatestRelease(str(data["tag"]), images, float(data["checked_at"]), True) if images else None
    except (KeyError, TypeError, ValueError):
        return None


def latest_release(
    fetch: Callable[[str], Any] = svc.urllib_fetch,
    cache_file: str | Path | None = None,
    now: Callable[[], float] = time.time,
    ttl: float = CACHE_TTL_SECONDS,
    retry_after: float = RETRY_AFTER_SECONDS,
    repo: str = FIRMWARE_REPO,
    force: bool = False,
) -> LatestRelease:
    """The images of the newest official release. A fresh cache answers without a request (unless ``force``); after a failed request the
    next one waits ``retry_after`` seconds (``too_soon``). Raises ``FirmwareCheckError``."""
    path = Path(cache_file) if cache_file is not None else None
    stamp = now()
    cache = _read_cache(path)
    if not force:
        cached = _from_cache(cache, repo, stamp, ttl)
        if cached is not None:
            return cached
        failed_at = cache.get("failed_at")
        if isinstance(failed_at, (int, float)) and 0 <= stamp - failed_at < retry_after:
            raise FirmwareCheckError("too_soon", "the last request failed a moment ago")
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    try:
        su.check_host(url)
        with fetch(url) as stream:
            raw = stream.read(MAX_LISTING_BYTES + 1)
    except su.UpdateError as error:
        _note_failure(path, cache, stamp)
        raise FirmwareCheckError("network", error.code) from error
    except urllib.error.HTTPError as error:
        _note_failure(path, cache, stamp)
        headers = error.headers
        limited = error.code == 429 or (error.code == 403 and headers is not None and (headers.get("X-RateLimit-Remaining") == "0" or headers.get("Retry-After") is not None))
        if limited:
            raise FirmwareCheckError("rate_limit", f"HTTP {error.code}") from error
        if error.code == 404:
            raise FirmwareCheckError("no_release", "HTTP 404") from error
        raise FirmwareCheckError("network", f"HTTP {error.code}") from error
    except (urllib.error.URLError, OSError, TimeoutError) as error:
        _note_failure(path, cache, stamp)
        raise FirmwareCheckError("network", str(getattr(error, "reason", error))) from error
    if len(raw) > MAX_LISTING_BYTES:
        _note_failure(path, cache, stamp)
        raise FirmwareCheckError("bad_release", "the listing is too large")
    try:
        release = json.loads(raw.decode("utf-8"))
        images = images_of_release(release)
    except (ValueError, FirmwareCheckError) as error:
        _note_failure(path, cache, stamp)
        raise FirmwareCheckError("bad_release", "not a release listing") from error
    if release.get("draft") or release.get("prerelease") or not images:
        _note_failure(path, cache, stamp)
        raise FirmwareCheckError("no_release", "no official release with images")
    tag = str(release.get("tag_name") or "")
    _write_cache(path, {"repo": repo, "checked_at": stamp, "tag": tag, "images": [[b, k, v] for (b, k), v in sorted(images.items())]})
    return LatestRelease(tag, images, stamp)


def _note_failure(path: Path | None, cache: dict[str, Any], stamp: float) -> None:
    kept = {key: cache[key] for key in ("repo", "checked_at", "tag", "images") if key in cache}
    kept["failed_at"] = stamp
    _write_cache(path, kept)


def compare(local: dict[tuple[str, str], str], latest: dict[tuple[str, str], str]) -> list[Row]:
    """One row for every slot the release or the program has, in the order of ``names.BOARDS`` and ``names.KINDS``."""
    rows: list[Row] = []
    for board in names.BOARDS:
        for kind in names.KINDS:
            slot = (board, kind)
            mine, published = local.get(slot), latest.get(slot)
            if mine is None and published is None:
                continue
            if published is None:
                state = NOT_RELEASED
            elif mine is None:
                state = ABSENT
            elif _version_key(mine) == _version_key(published):
                state = CURRENT
            elif _version_key(mine) < _version_key(published):
                state = OUTDATED
            else:
                state = AHEAD
            rows.append(Row(board, kind, mine, published, state))
    return rows


def check(
    local: dict[tuple[str, str], str],
    fetch: Callable[[str], Any] = svc.urllib_fetch,
    cache_file: str | Path | None = None,
    now: Callable[[], float] = time.time,
    force: bool = False,
) -> tuple[LatestRelease, list[Row]]:
    """The newest official release and the rows that compare ``local`` with it."""
    latest = latest_release(fetch, cache_file, now, force=force)
    return latest, compare(local, latest.images)


_STATE_KEYS = {CURRENT: "FWC_CURRENT", OUTDATED: "FWC_OUTDATED", AHEAD: "FWC_AHEAD", ABSENT: "FWC_ABSENT", NOT_RELEASED: "FWC_NOT_RELEASED"}


def describe(rows: list[Row], tag: str, language: str = "english", cached_minutes: int | None = None) -> list[str]:
    """The lines to show, in ``language``: one per row, or the single line that says everything matches; a cached answer adds its age."""
    lines: list[str] = []
    for row in rows:
        name = text(language, "FWC_NAME", board=text(language, f"FWC_BOARD_{row.board}"), kind=text(language, f"FWC_KIND_{row.kind}"))
        lines.append(text(language, _STATE_KEYS[row.state], name=name, local=row.local or "", latest=row.latest or "", tag=tag))
    if rows and all(row.state == CURRENT for row in rows):
        lines = [text(language, "FWC_ALL_CURRENT", tag=tag)]
    if cached_minutes is not None:
        lines.append(text(language, "FWC_CACHED", minutes=cached_minutes))
    return lines


def describe_error(error: FirmwareCheckError, language: str = "english") -> str:
    return text(language, error_key(error.code), text=str(error))
