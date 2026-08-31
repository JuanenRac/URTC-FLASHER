# =============================================================================
# URTC Flasher - Render Tkinter frames from the official HYDRA-UMC SVG.
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Regenerate the lightweight animation frames bundled with the application.

Run with a Python environment that provides PySide6, for example the
HYDRA-UMC-UPDATER development environment.  PySide6 is deliberately a build
tool only: the deployed URTC Flasher still uses only Tkinter and pyserial.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PySide6.QtCore import QSize
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


FRAME_COUNT = 12
FRAME_SIZE = 48


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--svg", type=Path, default=Path("assets/HYDRA_UMC_ICON.svg"),
        help="animated SVG source relative to the current directory",
    )
    parser.add_argument(
        "--output", type=Path, default=Path("assets/hydra_umc_icon_frames"),
        help="directory for frame_00.png through frame_11.png",
    )
    args = parser.parse_args()

    renderer = QSvgRenderer(str(args.svg))
    if not renderer.isValid() or not renderer.animated():
        raise RuntimeError(f"Expected a valid animated SVG: {args.svg}")

    args.output.mkdir(parents=True, exist_ok=True)
    total_frames = max(1, renderer.framesPerSecond() * renderer.animationDuration() // 1000)
    for index in range(FRAME_COUNT):
        renderer.setCurrentFrame(index * total_frames // FRAME_COUNT)
        image = QImage(QSize(FRAME_SIZE, FRAME_SIZE), QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(QColor(0, 0, 0, 0))
        painter = QPainter(image)
        renderer.render(painter)
        painter.end()
        if not image.save(str(args.output / f"frame_{index:02d}.png")):
            raise RuntimeError(f"Unable to write frame {index}")
    print(f"HYDRA_UMC_ICON_FRAMES=PASS count={FRAME_COUNT} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
