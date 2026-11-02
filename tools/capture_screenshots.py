#!/usr/bin/env python3
# =============================================================================
# URTC-FLASHER - tools/capture_screenshots.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Retakes the screenshots of the README, headless and with made-up sample data (nothing real is behind them, and no window opens on the desktop).

    py -3 tools/capture_screenshots.py              # writes images/screenshots/<file> for every screen listed in docs/screenshots.json
    py -3 tools/capture_screenshots.py --out DIR    # writes them in DIR instead, to look at them first

It runs tools/capture_screens.py (the real Qt Quick window, drawn offscreen, with a modelled bus), then keeps only the screens of docs/screenshots.json and shrinks every picture that weighs more than the limit (at most 400 KB each) by reducing
its palette (Pillow is needed for that last step only).
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MAX_BYTES = 400 * 1024
TARGET_BYTES = 380 * 1024


def shrink(source: Path, target: Path) -> int:
    """Copies source to target; when it is too heavy, reduces it to a 256-colour palette (then fewer colours) until it fits. Returns the final size."""
    if source.stat().st_size <= TARGET_BYTES:
        shutil.copyfile(source, target)
        return target.stat().st_size
    try:
        from PIL import Image
    except ImportError as error:  # pragma: no cover - depends on the machine
        raise SystemExit(f"{source.name} weighs {source.stat().st_size} bytes and Pillow is not installed to shrink it: py -3 -m pip install pillow") from error
    image = Image.open(source).convert("RGB")
    for colours in (256, 192, 128, 96, 64):
        image.quantize(colors=colours, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(target, optimize=True)
        if target.stat().st_size <= TARGET_BYTES:
            break
    return target.stat().st_size


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=REPO / "images" / "screenshots")
    args = parser.parse_args(argv)
    screens = json.loads((REPO / "docs" / "screenshots.json").read_text(encoding="utf-8"))["screens"]
    args.out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="urtc-shots-") as scratch:
        raw = Path(scratch)
        subprocess.run([sys.executable, "tools/capture_screens.py", "--readme", "--out", str(raw)], cwd=REPO, check=True)
        for screen in screens:
            name = screen["file"]
            source = raw / name
            if not source.is_file():
                print(f"missing: {name}")
                return 1
            size = shrink(source, args.out / name)
            print(f"{name}: {size} bytes")
            if size > MAX_BYTES:
                print(f"{name} is still heavier than {MAX_BYTES} bytes")
                return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
