# =============================================================================
# URTC-COMMON - src/urtc_common/self_update.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Update of an application from a signed package of a GitHub release: check, download, verify, install, roll back.

One implementation for the programs that update themselves (flasher, tester, updater). Nothing in it touches the
network or the screen by itself: the caller passes the function that fetches a URL and the function that reports
progress, so the rules are tested with a fake server, and the window of each program only draws the steps.

The steps, in the order the person sees them:

1. ``find_update`` reads the JSON of the latest release and says whether a package for this platform exists whose
   version is *higher* than the installed one (an older or equal version is never offered; going back is
   ``rollback``). Nothing is downloaded.
2. ``download_package`` fetches the package, its ``.sha256`` and its ``.sig`` only from the hosts of GitHub's release
   downloads, checks the size it was announced with, and leaves nothing behind when it fails.
3. ``verify_package`` checks the SHA-256 and the Ed25519 signature of the text
   ``urtc-pkg/1|<app>|<version>|<platform>|<sha256>|<size>`` against the public key pinned in the program (and the key
   identifier the release declares). A package that fails is never offered for installation.
4. ``install_package`` extracts it next to the others (``<root>/releases/<version>``) without ever writing outside the
   folder (no absolute path, no ``..``, no link, no device), checks the ``app_info.json`` inside against what was
   announced, and points ``current.txt`` to it. It refuses while ``busy_reason`` says an operation on the bus is running.
5. ``rollback`` points ``current.txt`` back to the previous release; ``finish_first_start`` does it by itself when
   the new release does not pass its own start-up check. The two latest releases are kept.
6. Every step is appended to ``history.jsonl``.

Standard library only; the Ed25519 check is the one of RFC 8032 written out (one verification per update is fast
enough). Messages of ``UpdateError`` carry a stable ``code`` so each program can say it in the language of the person.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import tarfile
import time
import urllib.parse
import zipfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

SCHEME = "urtc-pkg/1"
ALLOWED_HOSTS = ("api.github.com", "github.com", "objects.githubusercontent.com", "release-assets.githubusercontent.com")
MAX_PACKAGE_BYTES = 600 * 1024 * 1024
MAX_EXTRACTED_BYTES = 2 * 1024 * 1024 * 1024
MAX_EXTRACTED_FILES = 20_000
KEEP_RELEASES = 2
_APP = re.compile(r"^[a-z][a-z0-9-]{1,40}$")
_VERSION = re.compile(r"^\d{1,4}(\.\d{1,4}){2,3}$")


class UpdateError(Exception):
    """A step of the update failed. ``code`` is stable (for translation); the text is for the log."""

    def __init__(self, code: str, text: str = "") -> None:
        super().__init__(text or code)
        self.code = code


# --- versions and platforms -------------------------------------------------------------------------------------
def parse_version(text: str) -> tuple[int, int, int, int]:
    """``0.8.0.1`` -> (0, 8, 0, 1); a version with three components has a zero fourth. A leading ``v`` is allowed."""
    cleaned = str(text).strip().lstrip("vV")
    if not _VERSION.match(cleaned):
        raise UpdateError("bad_version", f"not a version: {text!r}")
    parts = [int(p) for p in cleaned.split(".")]
    a, b, c, d = (parts + [0] * 4)[:4]
    return (a, b, c, d)


def is_newer(installed: str, candidate: str) -> bool:
    """True only when the candidate is strictly higher: an equal or older version is never an update."""
    return parse_version(candidate) > parse_version(installed)


def platform_tag(system: str, machine: str) -> str:
    """``windows-x64`` / ``linux-x64`` / ``linux-arm64`` / ``macos-arm64``... from ``platform.system()`` and ``platform.machine()``."""
    system = system.lower()
    machine = machine.lower()
    name = {"windows": "windows", "linux": "linux", "darwin": "macos"}.get(system)
    arch = "arm64" if machine in ("arm64", "aarch64") else "x64" if machine in ("amd64", "x86_64", "x64") else None
    if name is None or arch is None:
        raise UpdateError("unsupported_platform", f"{system}/{machine}")
    return f"{name}-{arch}"


# --- Ed25519 (RFC 8032), verification only ---------------------------------------------------------------------
_P = 2**255 - 19
_Q = 2**252 + 27742317777372353535851937790883648493
_D = -121665 * pow(121666, _P - 2, _P) % _P
_SQRT_M1 = pow(2, (_P - 1) // 4, _P)


def _add(a, b):
    x1, y1, z1, t1 = a
    x2, y2, z2, t2 = b
    pa = (y1 - x1) * (y2 - x2) % _P
    pb = (y1 + x1) * (y2 + x2) % _P
    pc = 2 * t1 * t2 * _D % _P
    pd = 2 * z1 * z2 % _P
    e, f, g, h = pb - pa, pd - pc, pd + pc, pb + pa
    return (e * f % _P, g * h % _P, f * g % _P, e * h % _P)


def _mul(scalar, point):
    result = (0, 1, 1, 0)
    while scalar > 0:
        if scalar & 1:
            result = _add(result, point)
        point = _add(point, point)
        scalar >>= 1
    return result


def _equal(a, b):
    return (a[0] * b[2] - b[0] * a[2]) % _P == 0 and (a[1] * b[2] - b[1] * a[2]) % _P == 0


def _recover_x(y, sign):
    if y >= _P:
        return None
    x2 = (y * y - 1) * pow(_D * y * y + 1, _P - 2, _P) % _P
    if x2 == 0:
        return None if sign else 0
    x = pow(x2, (_P + 3) // 8, _P)
    if (x * x - x2) % _P:
        x = x * _SQRT_M1 % _P
    if (x * x - x2) % _P:
        return None
    return _P - x if (x & 1) != sign else x


def _decompress(data):
    y = int.from_bytes(data, "little")
    sign, y = y >> 255, y & ((1 << 255) - 1)
    x = _recover_x(y, sign)
    return None if x is None else (x, y, 1, x * y % _P)


_GY = 4 * pow(5, _P - 2, _P) % _P
_GX = _recover_x(_GY, 0)
BASE_POINT = (_GX, _GY, 1, _GX * _GY % _P)


def ed25519_verify(public: bytes, message: bytes, signature: bytes) -> bool:
    """True only for a valid Ed25519 signature of ``message`` by the 32-byte key ``public``."""
    if len(public) != 32 or len(signature) != 64:
        return False
    a_point, r_point = _decompress(public), _decompress(signature[:32])
    s = int.from_bytes(signature[32:], "little")
    if a_point is None or r_point is None or s >= _Q:
        return False
    h = int.from_bytes(hashlib.sha512(signature[:32] + public + message).digest(), "little") % _Q
    return _equal(_mul(s, BASE_POINT), _add(r_point, _mul(h, a_point)))


def package_message(app: str, version: str, platform: str, sha256: str, size: int) -> bytes:
    """The text the release key signs for a package."""
    return f"{SCHEME}|{app}|{version}|{platform}|{sha256}|{size}".encode()


# --- hosts and the release listing -----------------------------------------------------------------------------
def check_host(url: str, allowed: Iterable[str] = ALLOWED_HOSTS) -> None:
    """Only ``https`` on the hosts GitHub serves releases from."""
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or host not in tuple(allowed):
        raise UpdateError("bad_host", f"{host or url} is not an allowed download host")


@dataclass(frozen=True)
class Asset:
    name: str
    url: str
    size: int


@dataclass(frozen=True)
class Offer:
    app: str
    version: str
    platform: str
    tag: str
    published: str
    notes: str
    package: Asset
    sha256: Asset
    signature: Asset
    key_id: str


def package_name(app: str, version: str, platform: str) -> str:
    extension = "zip" if platform.startswith("windows") else "tar.gz"
    return f"{app}-{version}-{platform}.{extension}"


def _asset(release: dict, name: str) -> Asset | None:
    for item in release.get("assets", []):
        if isinstance(item, dict) and item.get("name") == name:
            url = str(item.get("browser_download_url", ""))
            size = item.get("size", 0)
            return Asset(name, url, size if isinstance(size, int) and size >= 0 else 0)
    return None


def find_update(release: dict, app: str, installed: str, platform: str) -> Offer | None:
    """The package of the release for this platform when its version is higher than ``installed``; None when there is nothing to do.

    A draft or a pre-release is never offered. Raises ``UpdateError`` for a release that announces a package but lacks
    its checksum or its signature (an incomplete release is a problem to report, not an update).
    """
    if not _APP.match(app):
        raise UpdateError("bad_app", app)
    if not isinstance(release, dict) or release.get("draft") or release.get("prerelease"):
        return None
    tag = str(release.get("tag_name", ""))
    try:
        version = ".".join(str(n) for n in parse_version(tag)[: (4 if tag.count(".") >= 3 else 3)])
    except UpdateError:
        return None
    if not is_newer(installed, version):
        return None
    name = package_name(app, version, platform)
    package = _asset(release, name)
    if package is None:
        return None  # a release of this repository with no package for this platform: nothing to offer
    sha = _asset(release, name + ".sha256")
    sig = _asset(release, name + ".sig")
    if sha is None or sig is None:
        raise UpdateError("incomplete_release", f"{name} has no {'checksum' if sha is None else 'signature'}")
    if package.size > MAX_PACKAGE_BYTES:
        raise UpdateError("too_big", f"{name} announces {package.size} bytes")
    for asset in (package, sha, sig):
        check_host(asset.url)
    key_id = ""
    match = re.search(r"(?mi)^key[_ ]id:\s*([0-9a-f]{8,64})\s*$", str(release.get("body") or ""))
    if match:
        key_id = match.group(1).lower()
    return Offer(app, version, platform, tag, str(release.get("published_at", "")), str(release.get("body") or ""), package, sha, sig, key_id)


# --- download and verification ---------------------------------------------------------------------------------
Fetch = Callable[[str], "io.BufferedIOBase"]


def _read_all(fetch: Fetch, url: str, limit: int) -> bytes:
    check_host(url)
    with fetch(url) as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise UpdateError("too_big", url)
    return data


def download_package(offer: Offer, fetch: Fetch, directory: str | Path, progress: Callable[[int, int], None] | None = None) -> tuple[Path, str, bytes]:
    """Downloads the package, reads its announced SHA-256 and its signature. Returns (path, sha256 hex, signature bytes).

    ``fetch(url)`` returns a readable stream (a context manager). The announced size must be the size received;
    when anything fails the partial file is deleted.
    """
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / offer.package.name
    part = folder / (offer.package.name + ".part")
    announced = _read_all(fetch, offer.sha256.url, 4096).decode("ascii", errors="replace").split()
    if not announced or not re.fullmatch(r"[0-9a-fA-F]{64}", announced[0]):
        raise UpdateError("bad_checksum_file", offer.sha256.name)
    try:
        signature = bytes.fromhex(_read_all(fetch, offer.signature.url, 4096).decode("ascii").strip())
    except ValueError as error:
        raise UpdateError("bad_signature_file", offer.signature.name) from error
    check_host(offer.package.url)
    written = 0
    digest = hashlib.sha256()
    try:
        with fetch(offer.package.url) as stream, open(part, "wb") as out:
            while True:
                block = stream.read(1 << 16)
                if not block:
                    break
                written += len(block)
                if written > MAX_PACKAGE_BYTES or (offer.package.size and written > offer.package.size):
                    raise UpdateError("too_big", f"{offer.package.name} is larger than announced")
                digest.update(block)
                out.write(block)
                if progress:
                    progress(written, offer.package.size)
        if offer.package.size and written != offer.package.size:
            raise UpdateError("size_mismatch", f"{written} bytes received, {offer.package.size} announced")
        if digest.hexdigest() != announced[0].lower():
            raise UpdateError("sha256_mismatch", offer.package.name)
        os.replace(part, target)
    except BaseException:
        try:
            part.unlink()
        except OSError:
            pass
        raise
    return target, announced[0].lower(), signature


def verify_package(offer: Offer, path: str | Path, sha256_hex: str, signature: bytes, public_key_hex: str, key_id: str) -> None:
    """Raises ``UpdateError`` unless the file is the one the key signed. ``key_id`` is the identifier of the key pinned in the program."""
    if offer.key_id and offer.key_id != key_id.lower():
        raise UpdateError("key_mismatch", f"the release declares key {offer.key_id}, this program trusts {key_id}")
    digest = hashlib.sha256()
    size = 0
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
            size += len(block)
    if digest.hexdigest() != sha256_hex.lower():
        raise UpdateError("sha256_mismatch", Path(path).name)
    message = package_message(offer.app, offer.version, offer.platform, digest.hexdigest(), size)
    try:
        public = bytes.fromhex(public_key_hex)
    except ValueError as error:
        raise UpdateError("bad_key", "the pinned public key is not hexadecimal") from error
    if not ed25519_verify(public, message, signature):
        raise UpdateError("bad_signature", Path(path).name)


# --- safe extraction ---------------------------------------------------------------------------------------------
def _safe_target(root: Path, member: str) -> Path:
    pure = PurePosixPath(member.replace("\\", "/"))
    if pure.is_absolute() or re.match(r"^[A-Za-z]:", member) or ".." in pure.parts or not pure.parts or "\x00" in member:
        raise UpdateError("unsafe_path", member)
    target = (root / Path(*pure.parts)).resolve()
    if root.resolve() != target and root.resolve() not in target.parents:
        raise UpdateError("unsafe_path", member)
    return target


def safe_extract(archive: str | Path, destination: str | Path) -> int:
    """Extracts a ``.zip`` or ``.tar.gz`` into ``destination``; returns the number of files. Refuses any path outside it, any
    link or device, and an archive that expands past the limits."""
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=True)
    count = 0
    total = 0
    name = str(archive)
    if name.endswith(".zip"):
        with zipfile.ZipFile(archive) as zf:
            for info in zf.infolist():
                target = _safe_target(root, info.filename)
                mode = (info.external_attr >> 16) & 0o170000
                if mode in (0o120000, 0o060000, 0o020000, 0o010000, 0o140000):
                    raise UpdateError("unsafe_member", info.filename)
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                count += 1
                total += info.file_size
                if count > MAX_EXTRACTED_FILES or total > MAX_EXTRACTED_BYTES:
                    raise UpdateError("too_big", "the package expands past the limits")
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as src, open(target, "wb") as out:
                    shutil.copyfileobj(src, out)
    elif name.endswith((".tar.gz", ".tgz")):
        with tarfile.open(archive, "r:gz") as tf:
            for member in tf:
                target = _safe_target(root, member.name)
                if member.issym() or member.islnk() or member.isdev() or member.isfifo():
                    raise UpdateError("unsafe_member", member.name)
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                if not member.isfile():
                    raise UpdateError("unsafe_member", member.name)
                count += 1
                total += member.size
                if count > MAX_EXTRACTED_FILES or total > MAX_EXTRACTED_BYTES:
                    raise UpdateError("too_big", "the package expands past the limits")
                target.parent.mkdir(parents=True, exist_ok=True)
                source = tf.extractfile(member)
                if source is None:
                    raise UpdateError("unsafe_member", member.name)
                with source, open(target, "wb") as out:
                    shutil.copyfileobj(source, out)
                if member.mode & 0o111:
                    target.chmod(0o755)
    else:
        raise UpdateError("unknown_archive", name)
    return count


# --- installation, rollback, history -----------------------------------------------------------------------------
def _history(root: Path, **entry) -> None:
    entry["time"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    root.mkdir(parents=True, exist_ok=True)
    with open(root / "history.jsonl", "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")


def read_history(root: str | Path) -> list[dict]:
    path = Path(root) / "history.jsonl"
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def current_version(root: str | Path) -> str | None:
    path = Path(root) / "current.txt"
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return text if _VERSION.match(text) else None


def _write_current(root: Path, version: str) -> None:
    temporary = root / "current.txt.new"
    temporary.write_text(version + "\n", encoding="utf-8")
    os.replace(temporary, root / "current.txt")


def installed_versions(root: str | Path) -> list[str]:
    folder = Path(root) / "releases"
    if not folder.is_dir():
        return []
    versions = [p.name for p in folder.iterdir() if p.is_dir() and _VERSION.match(p.name)]
    return sorted(versions, key=parse_version)


def install_package(archive: str | Path, root: str | Path, offer: Offer, busy_reason: str | None = None, sha256_hex: str = "") -> Path:
    """Installs a package that ``verify_package`` accepted. Returns the folder of the new release.

    ``busy_reason`` is the text of an operation that must not be interrupted (a flash, a bus session): when it is set
    nothing is touched. The previous release stays in place, so ``rollback`` is one write.
    """
    base = Path(root)
    if busy_reason:
        raise UpdateError("busy", busy_reason)
    releases = base / "releases"
    final = releases / offer.version
    staging = releases / (offer.version + ".partial")
    if staging.exists():
        shutil.rmtree(staging)
    releases.mkdir(parents=True, exist_ok=True)
    previous = current_version(base)
    try:
        safe_extract(archive, staging)
        info_path = staging / "app_info.json"
        try:
            info = json.loads(info_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise UpdateError("app_info_missing", "the package has no readable app_info.json") from error
        if not isinstance(info, dict) or info.get("name") != offer.app or str(info.get("version")) != offer.version:
            raise UpdateError("app_info_mismatch", f"app_info.json says {info.get('name') if isinstance(info, dict) else '?'} {info.get('version') if isinstance(info, dict) else '?'}, {offer.app} {offer.version} was announced")
        if final.exists():
            shutil.rmtree(final)
        os.replace(staging, final)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        _history(base, event="install", result="refused", app=offer.app, to=offer.version, previous=previous)
        raise
    _write_current(base, offer.version)
    _prune(base, keep=KEEP_RELEASES)
    _history(base, event="install", result="ok", app=offer.app, to=offer.version, previous=previous, sha256=sha256_hex)
    return final


def _prune(base: Path, keep: int) -> None:
    current = current_version(base)
    versions = installed_versions(base)
    survivors = set(versions[-keep:])
    if current:
        survivors.add(current)
    for version in versions:
        if version not in survivors:
            shutil.rmtree(base / "releases" / version, ignore_errors=True)


def rollback(root: str | Path, reason: str = "requested") -> str:
    """Points ``current.txt`` to the release before the current one. Returns that version."""
    base = Path(root)
    current = current_version(base)
    older = [v for v in installed_versions(base) if current is None or parse_version(v) < parse_version(current)]
    if not older:
        raise UpdateError("nothing_to_roll_back", "there is no earlier release kept")
    target = older[-1]
    _write_current(base, target)
    _history(base, event="rollback", result="ok", reason=reason, **{"from": current, "to": target})
    return target


def finish_first_start(root: str | Path, started_ok: bool) -> str | None:
    """To be called after the first start of a new release. When its start-up check failed, goes back to the previous one by
    itself and records it; returns the version restored, or None when nothing had to be done."""
    base = Path(root)
    if started_ok:
        _history(base, event="first_start", result="ok", version=current_version(base))
        return None
    try:
        return rollback(base, reason="first start failed")
    except UpdateError:
        _history(base, event="first_start", result="failed, nothing to go back to", version=current_version(base))
        return None
