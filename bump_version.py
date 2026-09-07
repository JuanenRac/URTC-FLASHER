#!/usr/bin/env python3
# =============================================================================
# URTC Flasher - build-time version bump
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Bumps FLASHER_VERSION in flasher_config.py by exactly one patch increment,
following the ecosystem-wide "odometer" versioning policy: the patch digit
goes up by 1; if that pushes it past 9, it resets to 0 and the minor digit
goes up by 1 instead (example: 0.1.9 -> 0.2.0). The same base-10 carry
applies from minor into major, for the same reason an odometer's tens digit
rolls the hundreds digit over too, even though in practice minor is expected
to stay single-digit for a long time.

This script is meant to run automatically, once, as a build step -
build_exe.bat and build_exe.sh both call it right before invoking
PyInstaller, so every real packaged build gets a new, unique version number
with no manual step to forget. It is NOT meant to be run by hand as part of
ordinary development; editing FLASHER_VERSION directly in flasher_config.py
is still the right move for anything that isn't an actual build (e.g.
deliberately setting a specific version for a release).

Usage:
    python bump_version.py            (or python3 on Linux/Mac)

Exits non-zero (and touches nothing) if flasher_config.py can't be found or
doesn't contain a FLASHER_VERSION line in the expected "X.Y.Z" quoted-string
form - a build should fail loudly here rather than silently ship an
unversioned or wrongly-versioned .exe/binary.
"""
import re
import sys
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent / "flasher_config.py"
# Deliberately anchored to a 3-part "X.Y.Z" quoted string only - a 2-part
# leftover ("1.1") or anything else unexpected fails loudly below instead of
# being silently reinterpreted, since that would mean the ecosystem-wide
# normalization to 3 parts didn't actually happen.
VERSION_RE = re.compile(r'^FLASHER_VERSION = "(\d+)\.(\d+)\.(\d+)"$', re.MULTILINE)


def bump(major, minor, patch):
    """Applies the base-10 carry rule described in the module docstring to
    one (major, minor, patch) tuple and returns the result - kept separate
    from the file I/O below so it can be tested/verified in isolation."""
    patch += 1
    if patch > 9:
        patch = 0
        minor += 1
    if minor > 9:
        minor = 0
        major += 1
    return major, minor, patch


def main():
    if not CONFIG_PATH.is_file():
        print(f"ERROR: {CONFIG_PATH} not found - is this script sitting next "
              f"to flasher_config.py?", file=sys.stderr)
        return 1

    text = CONFIG_PATH.read_text(encoding="utf-8")
    match = VERSION_RE.search(text)
    if not match:
        print(f'ERROR: could not find a FLASHER_VERSION = "X.Y.Z" line in '
              f"{CONFIG_PATH} - refusing to guess, touching nothing.", file=sys.stderr)
        return 1

    major, minor, patch = (int(g) for g in match.groups())
    new_major, new_minor, new_patch = bump(major, minor, patch)
    old_version = f"{major}.{minor}.{patch}"
    new_version = f"{new_major}.{new_minor}.{new_patch}"

    new_text = (
        text[: match.start()]
        + f'FLASHER_VERSION = "{new_version}"'
        + text[match.end() :]
    )
    CONFIG_PATH.write_text(new_text, encoding="utf-8")
    print(f"FLASHER_VERSION bumped: {old_version} -> {new_version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
