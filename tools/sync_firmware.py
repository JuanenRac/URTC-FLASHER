#!/usr/bin/env python3
# =============================================================================
# URTC Flasher - tools/sync_firmware.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Refreshes this tool's own firmware/ folder from a URTC firmware set: the
four .bin images named in URTC's firmware_manifest.json, each with its
<bin>.sha256 and <bin>.manifest.json (which carries the signature the
bootloader expects). Every image is checked against its own manifest before
it is copied, and stale images are removed, so firmware/ can never again
drift from what URTC published.

The firmware is not in the URTC git repository: it is published as assets of
each GitHub release. The set therefore comes from

    python tools/sync_firmware.py                    the assets of the latest URTC release
    python tools/sync_firmware.py --release v0.3.5   the assets of that release
    python tools/sync_firmware.py path/to/folder     a local folder holding the set
                                                     (a local URTC build writes it to URTC/firmware)
    python tools/sync_firmware.py --check            exit 1 if firmware/ is inconsistent
    python tools/sync_firmware.py --release v0.3.5 --allow-unsigned
                                                     a release whose assets carry no release signature (.sig),
                                                     such as a bench pre-release

A release is downloaded into a temporary folder and goes through the same
check as a local folder before anything in firmware/ is touched. Each file of
an official release has a release signature (<file>.sig, Ed25519 by the key of
the releases): a download is refused when a signature is wrong, and also when
it is missing unless --allow-unsigned says the unsigned set is wanted. An optional
GITHUB_TOKEN environment variable raises the API rate limit.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import flasher_release_signature as release_signature  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "firmware"
SIDECARS = (".sha256", ".manifest.json")
SIGNATURE = ".sig"
INDEX_NAME = "firmware_manifest.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(folder: Path) -> list[str]:
    """Problems with the images in `folder` (empty list = consistent)."""
    problems = []
    for image in sorted(folder.glob("*.bin")):
        manifest_path = image.with_name(image.name + ".manifest.json")
        sidecar_path = image.with_name(image.name + ".sha256")
        if not manifest_path.is_file() or not sidecar_path.is_file():
            problems.append(f"{image.name}: missing .sha256 or .manifest.json")
            continue
        actual = _sha256(image)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("sha256") != actual:
            problems.append(f"{image.name}: sha256 {actual} does not match its manifest")
        if not sidecar_path.read_text(encoding="utf-8").startswith(actual):
            problems.append(f"{image.name}: sha256 does not match its .sha256 file")
        if "FIRMWARE" in image.name and not manifest.get("hmac_sha256"):
            problems.append(f"{image.name}: application image without a published hmac_sha256")
    for signed in sorted(folder.glob("*" + SIGNATURE)):
        status = release_signature.check_file(str(signed)[: -len(SIGNATURE)])
        if status.state == "invalid":
            problems.append(status.detail)
    return problems


def signature_problems(source: Path, names: list[str], allow_unsigned: bool) -> list[str]:
    """Release-signature problems of the files a sync would copy: a wrong signature always, a missing one unless `allow_unsigned`."""
    problems = []
    for name in names:
        for suffix in ("",) + SIDECARS:
            status = release_signature.check_file(str(source / (name + suffix)))
            if status.state == "invalid" or (status.state == "unsigned" and not allow_unsigned):
                problems.append(status.detail)
    index_status = release_signature.check_file(str(source / INDEX_NAME))
    if index_status.state == "invalid" or (index_status.state == "unsigned" and not allow_unsigned):
        problems.append(index_status.detail)
    return problems


def image_names(source: Path) -> list[str]:
    index = json.loads((source / INDEX_NAME).read_text(encoding="utf-8"))
    return [component["files"]["bin"]["filename"] for component in index["components"].values()]


def download_release(target: Path, tag: str | None = None, fetch=None, download=None, allow_unsigned: bool = False) -> str:
    """Downloads firmware_manifest.json and the images it names, with their
    sidecars, from the assets of a URTC release into the empty folder
    `target`. Returns the release tag. `fetch` and `download` default to
    flasher_github.fetch_release / download_file (the host, size and
    Content-Length checks live there) and exist so a test can fake the network.
    The release signature (<file>.sig) of each file is downloaded when the release has it and checked
    with the pinned key of the releases; a file without one is refused unless `allow_unsigned`."""
    if fetch is None or download is None:
        sys.path.insert(0, str(ROOT))
        import flasher_github
        fetch = fetch or flasher_github.fetch_release
        download = download or flasher_github.download_file
    tag_name, assets = fetch(tag, only_firmware=False)
    by_name = {asset["name"]: asset for asset in assets}

    def get(name: str) -> None:
        if name not in by_name:
            raise SystemExit(f"release {tag_name or tag or 'latest'} has no asset named {name}")
        download(by_name[name]["download_url"], str(target / name), expected_size=by_name[name].get("size"))

    def get_signature(name: str) -> None:
        if name + SIGNATURE in by_name:
            get(name + SIGNATURE)

    get(INDEX_NAME)
    get_signature(INDEX_NAME)
    names = image_names(target)
    for name in names:
        for suffix in ("",) + SIDECARS:
            get(name + suffix)
            get_signature(name + suffix)
    problems = signature_problems(target, names, allow_unsigned)
    if problems:
        joined = ("\n  ").join(problems)
        hint = "\n  (use --allow-unsigned for a set that has no release signatures)" if any("no release signature" in p for p in problems) else ""
        raise SystemExit("refusing the release, its signatures are not acceptable:\n  " + joined + hint)
    return tag_name


def sync(source: Path) -> list[str]:
    names = image_names(source)
    problems = check(source)
    missing = [name + suffix for name in names for suffix in ("",) + SIDECARS if not (source / (name + suffix)).is_file()]
    if missing:
        problems.append("missing from the source: " + ", ".join(missing))
    if problems:
        raise SystemExit("refusing to sync, the source is inconsistent:\n  " + "\n  ".join(problems))
    DEST.mkdir(exist_ok=True)
    for stale in DEST.iterdir():
        if stale.is_file() and stale.name.startswith("URTC_"):  # the images and everything that travels with them, .sig included
            stale.unlink()
    for name in names:
        for suffix in ("",) + SIDECARS:
            shutil.copy2(source / (name + suffix), DEST / (name + suffix))
            if (source / (name + suffix + SIGNATURE)).is_file():
                shutil.copy2(source / (name + suffix + SIGNATURE), DEST / (name + suffix + SIGNATURE))
    return names


def main(argv: list[str]) -> int:
    args = argv[1:]
    if args and args[0] == "--check":
        problems = check(DEST)
        for problem in problems:
            print(f"FAIL {problem}")
        print("firmware/ consistent" if not problems else f"{len(problems)} problem(s)")
        return 1 if problems else 0
    allow_unsigned = "--allow-unsigned" in args
    args = [item for item in args if item != "--allow-unsigned"]
    tag = None
    if args and args[0] == "--release":
        if len(args) < 2:
            print("usage: sync_firmware.py [--release TAG | path/to/folder | --check]")
            return 2
        tag, args = args[1], args[2:]
    if args and tag is None:
        names = sync(Path(args[0]).resolve())
    else:
        with tempfile.TemporaryDirectory(prefix="urtc_release_") as temp:
            try:
                tag_name = download_release(Path(temp), tag, allow_unsigned=allow_unsigned)
            except SystemExit as error:  # a missing asset or a refused signature
                print(f"could not use the release: {error}")
                return 1
            except Exception as error:  # a network or host refusal is reported, not a traceback
                print(f"could not download the release: {error}")
                return 1
            print(f"release {tag_name or tag or 'latest'}")
            names = sync(Path(temp))
    for name in names:
        print(f"synced {name} (+ .sha256, .manifest.json)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
