# =============================================================================
# URTC Flasher - tests/test_sync_firmware.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""tools/sync_firmware.py takes the firmware set from the assets of a URTC
release or from a local folder, and checks it before touching firmware/."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("sync_firmware", ROOT / "tools" / "sync_firmware.py")
sync_firmware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync_firmware)

FILES = {
    "URTC_MAIN_FIRMWARE_v0.3.5.bin": ("main_application", b"main-app" * 10),
    "URTC_SLAVE_FIRMWARE_v0.1.9.bin": ("slave_application", b"slave-app" * 10),
}


def _release_set(folder: Path, tamper=False):
    folder.mkdir(parents=True, exist_ok=True)
    components = {}
    for name, (component, data) in FILES.items():
        digest = hashlib.sha256(data).hexdigest()
        (folder / name).write_bytes(data)
        (folder / (name + ".sha256")).write_text(digest + "  " + name, encoding="utf-8")
        manifest = {"component": component, "sha256": "0" * 64 if tamper else digest, "hmac_sha256": "ab" * 32}
        (folder / (name + ".manifest.json")).write_text(json.dumps(manifest), encoding="utf-8")
        components[component] = {"files": {"bin": {"filename": name}}}
    (folder / "firmware_manifest.json").write_text(json.dumps({"components": components}), encoding="utf-8")


@pytest.fixture
def dest(tmp_path, monkeypatch):
    folder = tmp_path / "bundled"
    folder.mkdir()
    (folder / "URTC_OLD_FIRMWARE_v0.0.1.bin").write_bytes(b"old")
    monkeypatch.setattr(sync_firmware, "DEST", folder)
    return folder


def test_a_local_folder_is_copied_and_stale_images_are_removed(tmp_path, dest, capsys):
    source = tmp_path / "local"
    _release_set(source)
    assert sync_firmware.main(["sync_firmware.py", str(source)]) == 0
    assert sorted(p.name for p in dest.iterdir()) == sorted(
        n + s for n in FILES for s in ("", ".sha256", ".manifest.json"))
    assert sync_firmware.check(dest) == []


def test_an_inconsistent_set_is_refused_and_firmware_is_untouched(tmp_path, dest):
    source = tmp_path / "local"
    _release_set(source, tamper=True)
    with pytest.raises(SystemExit):
        sync_firmware.sync(source)
    assert [p.name for p in dest.iterdir()] == ["URTC_OLD_FIRMWARE_v0.0.1.bin"]


def test_a_set_with_a_missing_file_is_refused(tmp_path, dest):
    source = tmp_path / "local"
    _release_set(source)
    (source / "URTC_SLAVE_FIRMWARE_v0.1.9.bin.manifest.json").unlink()
    with pytest.raises(SystemExit):
        sync_firmware.sync(source)


class FakeRelease:
    """Stands in for flasher_github.fetch_release / download_file."""

    def __init__(self, folder: Path, names=None):
        self.folder = folder
        self.names = names if names is not None else sorted(p.name for p in folder.iterdir())
        self.asked_tag = "unset"
        self.downloaded = []

    def fetch(self, tag=None, only_firmware=True):
        self.asked_tag = tag
        assert only_firmware is False  # the index is an asset of its own
        return "v0.3.5", [{"name": n, "size": (self.folder / n).stat().st_size,
                           "download_url": "https://github.com/JuanenRac/URTC/releases/download/v0.3.5/" + n} for n in self.names]

    def download(self, url, dest_path, expected_size=None, **_kw):
        name = url.rsplit("/", 1)[1]
        self.downloaded.append(name)
        Path(dest_path).write_bytes((self.folder / name).read_bytes())
        return expected_size


def test_the_release_assets_are_downloaded_and_then_synced(tmp_path, dest):
    assets = tmp_path / "assets"
    _release_set(assets)
    (assets / "URTC_MAIN_FIRMWARE_v0.3.5.hex").write_text("hex")  # an asset that is not needed
    fake = FakeRelease(assets)
    work = tmp_path / "work"
    work.mkdir()
    tag = sync_firmware.download_release(work, "v0.3.5", fetch=fake.fetch, download=fake.download, allow_unsigned=True)
    assert tag == "v0.3.5" and fake.asked_tag == "v0.3.5"
    assert "URTC_MAIN_FIRMWARE_v0.3.5.hex" not in fake.downloaded
    assert len(fake.downloaded) == 1 + 2 * 3
    sync_firmware.sync(work)
    assert sync_firmware.check(dest) == [] and len(list(dest.iterdir())) == 6


def test_a_release_that_lacks_an_asset_is_reported(tmp_path, dest):
    assets = tmp_path / "assets"
    _release_set(assets)
    fake = FakeRelease(assets, names=[p.name for p in assets.iterdir() if not p.name.endswith(".manifest.json") or "SLAVE" not in p.name])
    work = tmp_path / "work"
    work.mkdir()
    with pytest.raises(SystemExit) as info:
        sync_firmware.download_release(work, None, fetch=fake.fetch, download=fake.download, allow_unsigned=True)
    assert "SLAVE_FIRMWARE_v0.1.9.bin.manifest.json" in str(info.value)


def test_the_default_mode_downloads_the_latest_release(tmp_path, dest, monkeypatch, capsys):
    assets = tmp_path / "assets"
    _release_set(assets)
    fake = FakeRelease(assets)
    monkeypatch.syspath_prepend(str(ROOT))
    import flasher_github
    monkeypatch.setattr(flasher_github, "fetch_release", fake.fetch)
    monkeypatch.setattr(flasher_github, "download_file", fake.download)
    assert sync_firmware.main(["sync_firmware.py"]) == 1  # no release signatures in this set
    assert "--allow-unsigned" in capsys.readouterr().out
    assert sync_firmware.main(["sync_firmware.py", "--allow-unsigned"]) == 0
    assert fake.asked_tag is None
    assert "release v0.3.5" in capsys.readouterr().out
    assert sync_firmware.check(dest) == [] and len(list(dest.iterdir())) == 6


def test_a_download_failure_is_reported_without_a_traceback_and_firmware_is_untouched(dest, monkeypatch, capsys):
    import flasher_github

    def boom(tag=None, only_firmware=True):
        raise flasher_github.GitHubDownloadError("no network")

    monkeypatch.setattr(flasher_github, "fetch_release", boom)
    assert sync_firmware.main(["sync_firmware.py", "--release", "v0.3.4"]) == 1
    assert "no network" in capsys.readouterr().out
    assert [p.name for p in dest.iterdir()] == ["URTC_OLD_FIRMWARE_v0.0.1.bin"]


try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
except ImportError:
    Ed25519PrivateKey = None


def _sign_set(folder: Path, key, only=None, wrong_for=None):
    """Writes <file>.sig for every file of the set, with a throwaway key."""
    import flasher_release_signature as sig

    for path in sorted(folder.iterdir()):
        if path.suffix == ".sig" or (only and path.name not in only):
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        name = "other.bin" if path.name == wrong_for else path.name
        Path(str(path) + ".sig").write_text(key.sign(sig.release_message(name, digest)).hex() + "\n", encoding="ascii")


@pytest.fixture
def test_key(monkeypatch):
    if Ed25519PrivateKey is None:
        pytest.skip("cryptography is not installed")
    import flasher_release_signature as sig
    from cryptography.hazmat.primitives import serialization

    key = Ed25519PrivateKey.generate()
    monkeypatch.setattr(sig, "PUBLIC_KEY_HEX", key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex())
    return key


def test_a_signed_release_is_accepted_and_its_signatures_are_kept(tmp_path, dest, test_key):
    assets = tmp_path / "assets"
    _release_set(assets)
    _sign_set(assets, test_key)
    fake = FakeRelease(assets)
    work = tmp_path / "work"
    work.mkdir()
    sync_firmware.download_release(work, "v0.3.5", fetch=fake.fetch, download=fake.download)
    sync_firmware.sync(work)
    assert sync_firmware.check(dest) == []
    assert (dest / "URTC_MAIN_FIRMWARE_v0.3.5.bin.sig").is_file()


def test_a_signature_of_another_file_or_key_is_refused_even_with_allow_unsigned(tmp_path, dest, test_key):
    assets = tmp_path / "assets"
    _release_set(assets)
    _sign_set(assets, test_key, wrong_for="URTC_MAIN_FIRMWARE_v0.3.5.bin")
    fake = FakeRelease(assets)
    work = tmp_path / "work"
    work.mkdir()
    with pytest.raises(SystemExit) as info:
        sync_firmware.download_release(work, "v0.3.5", fetch=fake.fetch, download=fake.download, allow_unsigned=True)
    assert "does not match its release signature" in str(info.value)


def test_a_release_with_only_some_signatures_is_refused_unless_unsigned_is_allowed(tmp_path, dest, test_key):
    assets = tmp_path / "assets"
    _release_set(assets)
    _sign_set(assets, test_key, only={"URTC_MAIN_FIRMWARE_v0.3.5.bin"})
    fake = FakeRelease(assets)
    work = tmp_path / "work"
    work.mkdir()
    with pytest.raises(SystemExit) as info:
        sync_firmware.download_release(work, "v0.3.5", fetch=fake.fetch, download=fake.download)
    assert "no release signature" in str(info.value)
