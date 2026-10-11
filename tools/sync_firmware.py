#!/usr/bin/env python3
# =============================================================================
# URTC Flasher - tools/sync_firmware.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Copies the URTC build output into this tool's own firmware/ folder:
the four .bin images named in URTC's firmware_manifest.json, each with its
<bin>.sha256 and <bin>.manifest.json (which carries the signature the
bootloader expects). Every image is checked against its own manifest before
it is copied, and stale images are removed, so firmware/ can never again
drift from what URTC published.

    python tools/sync_firmware.py [path/to/URTC/firmware]   (default ../URTC/firmware)
    python tools/sync_firmware.py --check                    (exit 1 if firmware/ is inconsistent)
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "firmware"
SIDECARS = (".sha256", ".manifest.json")


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
    return problems


def sync(source: Path) -> list[str]:
    index = json.loads((source / "firmware_manifest.json").read_text(encoding="utf-8"))
    names = [component["files"]["bin"]["filename"] for component in index["components"].values()]
    problems = check(source)
    if problems:
        raise SystemExit("refusing to sync, the source is inconsistent:\n  " + "\n  ".join(problems))
    DEST.mkdir(exist_ok=True)
    for stale in DEST.iterdir():
        if stale.is_file() and stale.name.startswith("URTC_"):
            stale.unlink()
    for name in names:
        for suffix in ("",) + SIDECARS:
            shutil.copy2(source / (name + suffix), DEST / (name + suffix))
    return names


def main(argv: list[str]) -> int:
    if len(argv) > 1 and argv[1] == "--check":
        problems = check(DEST)
        for problem in problems:
            print(f"FAIL {problem}")
        print("firmware/ consistent" if not problems else f"{len(problems)} problem(s)")
        return 1 if problems else 0
    source = Path(argv[1]) if len(argv) > 1 else ROOT.parent / "URTC" / "firmware"
    for name in sync(source.resolve()):
        print(f"synced {name} (+ .sha256, .manifest.json)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
