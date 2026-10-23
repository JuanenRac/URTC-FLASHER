# =============================================================================
# URTC-COMMON - src/urtc_common/launcher.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The launcher of a program installed by ``self_update``: starts the release ``current.txt`` points to.

    python -m urtc_common.launcher ROOT [-- arguments for the program]

The program lives in ``ROOT/releases/<version>/`` and its ``app_info.json`` names the file to run (``entry``, a path
inside that folder). The launcher is small on purpose: it runs that file, waits for it, and when the release that was
installed last (``first_start_pending.txt``, written by the installer) ends with an error before the program reported
``mark_started``, it points ``current.txt`` back to the previous release by itself and says so in ``history.jsonl``.
It never downloads, never installs and never decides to update. Standard library only.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from . import self_update as su

PENDING_FILE = "first_start_pending.txt"


def resolve_entry(root: str | Path) -> Path:
    """The executable of the current release. ``UpdateError`` when there is no current release or its entry leaves the folder."""
    base = Path(root)
    version = su.current_version(base)
    if version is None:
        raise su.UpdateError("no_current_release", "current.txt is missing or not a version")
    folder = (base / "releases" / version).resolve()
    try:
        info = json.loads((folder / "app_info.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise su.UpdateError("app_info_missing", f"releases/{version} has no readable app_info.json") from error
    entry = info.get("entry") if isinstance(info, dict) else None
    if not isinstance(entry, str) or not entry:
        raise su.UpdateError("entry_missing", "app_info.json names no entry")
    target = (folder / entry).resolve()
    if folder != target and folder not in target.parents:
        raise su.UpdateError("entry_outside", entry)
    if not target.is_file():
        raise su.UpdateError("entry_missing", entry)
    return target


def launch(root: str | Path, arguments: Sequence[str] = (), run: Callable[..., int] | None = None) -> int:
    """Runs the current release and returns its exit code. Rolls back by itself when a first start fails."""
    base = Path(root)
    entry = resolve_entry(base)
    command = [str(entry), *arguments]
    if entry.suffix.lower() == ".py":
        command = [sys.executable, *command]
    code = run(command, cwd=str(entry.parent)) if run else subprocess.call(command, cwd=str(entry.parent), env={**os.environ, "URTC_UPDATE_ROOT_IN_USE": str(base)})
    pending = base / PENDING_FILE
    if pending.is_file():
        try:
            pending.unlink()
        except OSError:
            pass
        su.finish_first_start(base, code == 0)
    return code


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help"}:
        print(__doc__)
        return 0 if args else 2
    root, rest = args[0], args[1:]
    if rest[:1] == ["--"]:
        rest = rest[1:]
    try:
        return launch(root, rest)
    except su.UpdateError as error:
        print(f"LAUNCH=FAIL {error.code}: {error}", file=sys.stderr)
        return 3


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
