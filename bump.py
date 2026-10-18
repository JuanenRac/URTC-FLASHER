#!/usr/bin/env python3
# =============================================================================
# URTC-FLASHER - bump.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Raises this project's version by one step of the ecosystem odometer, explicitly.

Building never changes a version; run this first when a new version is wanted:

    python bump.py             raise the version (native source, urtc.project.json, CHANGELOG.md heading)
    python bump.py --dry-run   show the next version, write nothing
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(*command: str) -> None:
    result = subprocess.run([sys.executable, *command], cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main(argv: list[str]) -> int:
    if "--dry-run" in argv:
        import json
        sys.path.insert(0, str(ROOT))
        manifest = json.loads((ROOT / "urtc.project.json").read_text(encoding="utf-8"))
        print(f"current version {manifest['version']}; --dry-run writes nothing")
        return 0
    run("bump_version.py")
    run("bump_manifest_version.py", "--sync")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
