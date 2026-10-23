# =============================================================================
# URTC-COMMON - src/urtc_common/update_service.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""What a program needs on top of ``self_update`` to offer "Check for updates": the options, the key it trusts and the steps.

``self_update`` has the rules (versions, hosts, size, SHA-256, signature, safe extraction, rollback) and no opinion about
the person. This module adds the part every window of the family shares, so the flasher, the tester and the updater
say the same thing and none of them can be made to update by itself:

* **Options** (``UpdatePolicy``), all conservative by default. ``auto_check`` is off: the program never contacts the
  network until the person asks. ``require_confirmation`` is on: ``install`` refuses unless the caller says the person
  confirmed, after seeing the version and the notes. There is no option to skip the
  checksum or the signature, and none to add a host: the signed package of a release is the only thing installed.
  Each option can come from the saved settings or from the environment (``URTC_UPDATE_AUTO_CHECK=1``, ``URTC_UPDATE_REQUIRE_CONFIRMATION=0``);
  the environment wins, and ``lowering_warnings`` says in words when a run lowers a protection the settings had on.
* **The pinned key.** ``RELEASE_PUBLIC_KEY_HEX`` is the Ed25519 key of the releases (the one that also signs the
  firmware images), ``RELEASE_KEY_ID`` its identifier (the first sixteen hex digits of the SHA-256 of the key).
* **The steps** (``UpdateService``): ``check`` (one request, nothing downloaded), ``prepare`` (download and verify, nothing
  installed), ``install`` (needs the confirmation), ``rollback``, and ``mark_started`` for the program to call once its
  window is up, so a release that cannot start is replaced by the previous one by the launcher (``launcher.py``).

No window, no thread and no global state: the program calls the steps from its own worker and draws the result.
Standard library only.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform as _platform
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from . import self_update as su

RELEASE_PUBLIC_KEY_HEX = "4020c46d76c8ebacb64c5c7b9f3e7c62475afeb133d7421591988174e0f5dc90"
RELEASE_KEY_ID = hashlib.sha256(bytes.fromhex(RELEASE_PUBLIC_KEY_HEX)).hexdigest()[:16]
GITHUB_OWNER = "JuanenRac"
USER_AGENT = "urtc-self-update/1"
PENDING_FILE = "first_start_pending.txt"

ENV_AUTO_CHECK = "URTC_UPDATE_AUTO_CHECK"
ENV_REQUIRE_CONFIRMATION = "URTC_UPDATE_REQUIRE_CONFIRMATION"
ENV_ROOT = "URTC_UPDATE_ROOT"


# --- options ----------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class UpdatePolicy:
    """The options of the update. The defaults are the conservative ones."""

    auto_check: bool = False
    require_confirmation: bool = True


def _env_flag(environ: Mapping[str, str], name: str) -> bool | None:
    value = str(environ.get(name, "")).strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return None


def policy_from(settings: Mapping[str, object] | None = None, environ: Mapping[str, str] | None = None) -> UpdatePolicy:
    """Saved settings (``update_auto_check`` ...) first, the environment over them; anything not a boolean falls back to the default."""
    settings = settings or {}
    environ = os.environ if environ is None else environ
    defaults = UpdatePolicy()

    def pick(key: str, env: str, default: bool) -> bool:
        flag = _env_flag(environ, env)
        if flag is not None:
            return flag
        value = settings.get(key)
        return value if isinstance(value, bool) else default

    return UpdatePolicy(
        auto_check=pick("update_auto_check", ENV_AUTO_CHECK, defaults.auto_check),
        require_confirmation=pick("update_require_confirmation", ENV_REQUIRE_CONFIRMATION, defaults.require_confirmation),
    )


def lowering_warnings(saved: UpdatePolicy, effective: UpdatePolicy) -> list[str]:
    """Codes of the protections that ``effective`` (a run) lowers below ``saved``: confirmation off, check on its own on."""
    found = []
    if saved.require_confirmation and not effective.require_confirmation:
        found.append("confirmation_off")
    if not saved.auto_check and effective.auto_check:
        found.append("auto_check_on")
    return found


def is_lowering(old: UpdatePolicy, new: UpdatePolicy) -> bool:
    """True when saving ``new`` over ``old`` lowers a protection (the window asks before saving it)."""
    return bool(lowering_warnings(old, new))


# --- places and the network -------------------------------------------------------------------------------------
def default_root(app: str, environ: Mapping[str, str] | None = None, system: str | None = None) -> Path:
    """Where the releases of ``app`` are kept: ``URTC_UPDATE_ROOT``, or the data folder of the person."""
    environ = os.environ if environ is None else environ
    explicit = str(environ.get(ENV_ROOT, "")).strip()
    if explicit:
        return Path(explicit) / app
    system = (system or _platform.system()).lower()
    if system == "windows":
        base = Path(environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    elif system == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return base / "URTC" / app


def urllib_fetch(url: str, timeout: float = 20.0):
    """The default ``fetch``: https only, on the allowed hosts (the caller of ``self_update`` checks it again)."""
    su.check_host(url)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json, application/octet-stream"})
    return urllib.request.urlopen(request, timeout=timeout)  # noqa: S310 - the scheme and the host were checked above


@dataclass(frozen=True)
class Prepared:
    """A package that was downloaded and verified and has not been installed."""

    offer: su.Offer
    path: Path
    sha256: str


class UpdateService:
    """The steps of "Check for updates" for one program.

    ``busy`` returns the text of an operation that must not be interrupted (or ``None``); ``fetch`` and ``platform`` are
    parameters so the tests need neither the network nor a given system.
    """

    def __init__(
        self,
        app: str,
        installed: str,
        root: str | Path | None = None,
        policy: UpdatePolicy | None = None,
        public_key_hex: str = RELEASE_PUBLIC_KEY_HEX,
        key_id: str = RELEASE_KEY_ID,
        repo: str | None = None,
        fetch: Callable[[str], object] = urllib_fetch,
        platform: str | None = None,
        busy: Callable[[], str | None] | None = None,
    ) -> None:
        su.parse_version(installed)
        self.app = app
        self.installed = installed
        self.root = Path(root) if root is not None else default_root(app)
        self.policy = policy or UpdatePolicy()
        self.public_key_hex = public_key_hex
        self.key_id = key_id
        self.repo = repo or f"{GITHUB_OWNER}/{app.upper()}"
        self.fetch = fetch
        self.platform = platform or su.platform_tag(_platform.system(), _platform.machine())
        self.busy = busy

    # -- steps -----------------------------------------------------------------------------------------------
    def release_url(self) -> str:
        return f"https://api.github.com/repos/{self.repo}/releases/latest"

    def check(self) -> su.Offer | None:
        """One request. Returns the offer, or None when this version is the latest (or the newest has no package for this system)."""
        with self.fetch(self.release_url()) as stream:
            raw = stream.read(2 * 1024 * 1024 + 1)
        if len(raw) > 2 * 1024 * 1024:
            raise su.UpdateError("too_big", "release listing")
        try:
            release = json.loads(raw.decode("utf-8"))
        except ValueError as error:
            raise su.UpdateError("bad_release_listing", "the release listing is not JSON") from error
        offer = su.find_update(release, self.app, self.installed, self.platform)
        self._note(event="check", result="offer" if offer else "none", offered=offer.version if offer else None)
        return offer

    def prepare(self, offer: su.Offer, progress: Callable[[int, int], None] | None = None) -> Prepared:
        """Downloads and verifies; installs nothing. The package never reaches ``install`` unless it passed the checksum and the signature."""
        folder = self.root / "downloads"
        path, sha, signature = su.download_package(offer, self.fetch, folder, progress)
        try:
            su.verify_package(offer, path, sha, signature, self.public_key_hex, self.key_id)
        except BaseException:
            try:
                path.unlink()
            except OSError:
                pass
            self._note(event="verify", result="refused", offered=offer.version)
            raise
        self._note(event="verify", result="ok", offered=offer.version, sha256=sha)
        return Prepared(offer, path, sha)

    def install(self, prepared: Prepared, confirmed: bool = False) -> Path:
        """Installs a prepared package. Without ``confirmed`` (and while the policy asks for it) nothing is touched."""
        if self.policy.require_confirmation and not confirmed:
            raise su.UpdateError("confirmation_required", "the person has not confirmed this update")
        reason = self.busy() if self.busy else None
        final = su.install_package(prepared.path, self.root, prepared.offer, reason, prepared.sha256)
        (self.root / PENDING_FILE).write_text(prepared.offer.version + "\n", encoding="utf-8")
        try:
            prepared.path.unlink()
        except OSError:
            pass
        return final

    def rollback(self) -> str:
        return su.rollback(self.root)

    def history(self) -> list[dict]:
        return su.read_history(self.root)

    def current(self) -> str | None:
        return su.current_version(self.root)

    def _note(self, **entry) -> None:
        try:
            su._history(self.root, app=self.app, **entry)
        except OSError:
            pass  # a history that cannot be written must not stop a check


def mark_started(root: str | Path) -> bool:
    """For the program to call once its window is up: clears the pending first start of a new release. Returns True when one was pending."""
    path = Path(root) / PENDING_FILE
    if not path.is_file():
        return False
    try:
        path.unlink()
    except OSError:
        return False
    su.finish_first_start(root, True)
    return True


def pending_first_start(root: str | Path) -> str | None:
    path = Path(root) / PENDING_FILE
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return text or None
