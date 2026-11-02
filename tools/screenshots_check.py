#!/usr/bin/env python3
# =============================================================================
# URTC-COMMON - tools/screenshots_check.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The screenshots of a README: ``docs/screenshots.json``, the PNG files it lists, their weight, and the file tree that lists their folder.

A repository that has a window or a web page lists its pictures in ``docs/screenshots.json`` (the pictures live in ``images/screenshots/``), with a short name
and a caption in the eight languages; the format is the same in every family. The README generator (``tools/readme_sections.py``) writes the Screenshots
section from that file, right after Architecture. Standard library only; the repositories that carry screenshots hold a copy of this file.

    python tools/screenshots_check.py [--repo PATH]       # one repository (the current one by default)
    python tools/screenshots_check.py --all [ROOT]         # every URTC-* folder next to this repository (or in ROOT) that has screenshots

The file is ``{"screens": [{"file": "overview.png", "alt": {<8 languages>}, "caption": {<8 languages>}}]}``. Prints one line per problem and
``SCREENSHOTS=PASS`` or ``SCREENSHOTS=FAIL <n>``; exits 1 on a problem.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

MAX_BYTES = 400 * 1024
MAX_SHOTS = 8
LANGS = ("en", "es", "fr", "it", "de", "zh", "ja", "pt")
RELATIVE = Path("docs") / "screenshots.json"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

HEADING = {
    "en": "Screenshots", "es": "Capturas de pantalla", "fr": "Captures d'écran", "it": "Schermate", "de": "Screenshots", "zh": "屏幕截图", "ja": "スクリーンショット",
    "pt": "Capturas de ecrã",
}

NOTE = {
    "en": "Captured on a test bench with made-up sample data and no real installation behind them.",
    "es": "Capturadas en un banco de pruebas con datos de ejemplo inventados y sin ninguna instalación real detrás.",
    "fr": "Capturées sur un banc d'essai avec des données d'exemple fictives et sans installation réelle derrière.",
    "it": "Catturate su un banco di prova con dati di esempio inventati e senza alcuna installazione reale dietro.",
    "de": "Aufgenommen auf einem Prüfstand mit erfundenen Beispieldaten und ohne eine echte Anlage dahinter.",
    "zh": "在测试台上使用虚构的示例数据截取，背后没有真实的安装。",
    "ja": "テストベンチで架空のサンプルデータを使って撮影したもので、実際の設備は接続されていません。",
    "pt": "Capturadas numa bancada de testes com dados de exemplo inventados e sem qualquer instalação real por trás.",
}


def read(repo: Path) -> list[dict[str, Any]] | None:
    """The screens listed by the repository, or None when it has no docs/screenshots.json."""
    path = repo / RELATIVE
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    screens = data.get("screens") if isinstance(data, dict) else None
    return screens if isinstance(screens, list) else []


def has(repo: Path) -> bool:
    return (repo / RELATIVE).is_file()


def problems(repo: Path) -> list[str]:
    """Everything that is wrong with the screenshots of a repository (an empty list when there are none or all is well)."""
    try:
        screens = read(repo)
    except ValueError:
        return [f"{RELATIVE.as_posix()} is not valid JSON"]
    if screens is None:
        return []
    found: list[str] = []
    if not screens:
        found.append(f"{RELATIVE.as_posix()} lists no screens")
    if len(screens) > MAX_SHOTS:
        found.append(f"{len(screens)} screenshots; at most {MAX_SHOTS}")
    seen: set[str] = set()
    for index, screen in enumerate(screens):
        name = screen.get("file") if isinstance(screen, dict) else None
        if not isinstance(name, str) or not name.endswith(".png") or "/" in name or "\\" in name:
            found.append(f"screen {index}: 'file' must be the name of a .png")
            continue
        if name in seen:
            found.append(f"{name}: listed twice")
        seen.add(name)
        for key in ("alt", "caption"):
            texts = screen.get(key)
            missing = [lg for lg in LANGS if not isinstance(texts, dict) or not str(texts.get(lg, "")).strip()]
            if missing:
                found.append(f"{name}: '{key}' lacks {', '.join(missing)}")
        picture = repo / "images" / "screenshots" / name
        if not picture.is_file():
            found.append(f"{name}: images/screenshots/{name} does not exist")
        elif picture.stat().st_size > MAX_BYTES:
            found.append(f"{name}: {picture.stat().st_size} bytes; at most {MAX_BYTES}")
        elif not picture.read_bytes().startswith(PNG_MAGIC):
            found.append(f"{name}: not a PNG")
    folder = repo / "images" / "screenshots"
    if folder.is_dir():
        found.extend(f"images/screenshots/{path.name}: not listed in {RELATIVE.as_posix()}" for path in sorted(folder.glob("*.png")) if path.name not in seen)
    return found


def tree_problems(repo: Path) -> list[str]:
    """The file tree (docs/structure.json) has to list the images/ folder that holds the pictures, and the English README has to show every picture."""
    if not has(repo):
        return []
    found: list[str] = []
    structure = repo / "docs" / "structure.json"
    text = structure.read_text(encoding="utf-8") if structure.is_file() else ""
    if '"images/"' not in text:
        found.append("the file tree (docs/structure.json) does not list images/, the folder of the pictures of the README")
    readme = repo / "README.md"
    page = readme.read_text(encoding="utf-8") if readme.is_file() else ""
    for screen in read(repo) or []:
        name = screen.get("file") if isinstance(screen, dict) else None
        if isinstance(name, str) and f"images/screenshots/{name}" not in page:
            found.append(f"README.md does not show images/screenshots/{name}: run tools/readme_sections.py apply in URTC-COMMON")
    return found


def section(language: str, repo: Path) -> dict[str, Any] | None:
    """The Screenshots section as the README generator places it (the shape of an entry of spec/readme/sections.json), or None when the repository has none.

    ``language`` is the key of ``readme_sections.FILES`` ("english", "spanish"...); the section carries all eight, so the same call serves every README."""
    screens = read(repo)
    if screens is None:
        return None
    bad = problems(repo)
    if bad:
        raise ValueError(f"{repo.name}: screenshots: " + "; ".join(bad))
    names = {"english": "en", "spanish": "es", "german": "de", "french": "fr", "italian": "it", "japanese": "ja", "chinese": "zh", "portuguese": "pt"}
    body = {}
    for long, code in names.items():
        blocks = [NOTE[code]]
        for screen in screens:
            blocks.append(f'<p align="center">\n  <img src="images/screenshots/{screen["file"]}" alt="{screen["alt"][code]}" width="100%">\n</p>')
            blocks.append(f'<p align="center"><em>{screen["caption"][code]}</em></p>')
        body[long] = "\n\n".join(blocks)
    return {"id": "screenshots", "emoji": "🖼️", "repos": [repo.name], "universal": {"after": "architecture"},
            "heading": {long: HEADING[code] for long, code in names.items()}, "body": body}


def run_in_ci(root: Path) -> list[str]:
    """What the CI of a repository reports about its screenshots (nothing when it has none)."""
    return problems(root) + tree_problems(root)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", type=Path)
    parser.add_argument("--all", nargs="?", const="", metavar="ROOT")
    args = parser.parse_args(argv)
    if args.all is not None:
        root = Path(args.all) if args.all else Path(__file__).resolve().parents[2]
        repos = sorted(path for path in root.glob("URTC-*") if has(path))
    else:
        repos = [args.repo or Path(__file__).resolve().parents[1]]
    found = [f"{repo.name}: {problem}" for repo in repos for problem in run_in_ci(repo)]
    for problem in found:
        print(problem)
    print("SCREENSHOTS=PASS" if not found else f"SCREENSHOTS=FAIL {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
