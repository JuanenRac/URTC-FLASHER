#!/usr/bin/env python3
# =============================================================================
# URTC Flasher - tools/version_compat_command.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Workshop tool: make the signed command that sets how one head reads an image without a patch number.

    python tools/version_compat_command.py --query
    python tools/version_compat_command.py --key-file KEY --uid W0,W1,W2 --current-serial HEX --mode strict|accept_patchless --counter N --yes

The command is the one of ``0x7EE`` described by URTC-COMMON ("The version rule for an image without a patch number"): it names the 96-bit unique ID of the head,
the serial the head answers with now, the mode and a counter that must be higher than the one the head stores. The tool prints the twelve SLCAN lines to put on
the bus, one per line. ``--query`` prints the single line that asks for the state without changing it; it needs no key.

``accept_patchless`` lets an image whose signed header says patch 0 replace an installed x.y.Z of the same major.minor without the downgrade authorization: set
the head back to ``strict`` when the old flasher is gone. The private key is NEVER looked for: ``--key-file`` names a file with the 32-byte seed (64
hexadecimal digits, or the raw 32 bytes). Only a bootloader built with the version command (off in the builds), whose trust table holds the public half of that
key, will obey. Nothing is sent from here and without ``--yes`` the tool only describes what it would make.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from serial_command import parse_uid, read_seed  # noqa: E402
from urtc_can import slcan, version_compat  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--query", action="store_true", help="print the line that asks for the state (no key, changes nothing)")
    parser.add_argument("--key-file", type=Path, help="file with the 32-byte seed of a key of the trust table of the bootloader")
    parser.add_argument("--uid", help="the three words of the unique ID of the head, hexadecimal, comma separated")
    parser.add_argument("--current-serial", help="the serial the head answers with now (hexadecimal)")
    parser.add_argument("--mode", choices=sorted(version_compat.MODE_NAMES), help="the rule to store in the head")
    parser.add_argument("--counter", type=int, help="higher than the counter the head stores; 1 or more for the first")
    parser.add_argument("--yes", action="store_true", help="really make the command (without it the tool only describes it)")
    args = parser.parse_args(argv)

    expect = f"EXPECT t{version_compat.ID_RESULT:03X}8 C5 ..."
    if args.query:
        print(slcan.encode_line(version_compat.ID_COMMAND, version_compat.query_frame()))
        print(f"{expect} (status, mode in force, flags, stored counter; a bootloader without the feature answers nothing)")
        return 0
    missing = [name for name in ("key_file", "uid", "current_serial", "mode", "counter") if getattr(args, name) is None]
    if missing:
        raise SystemExit("missing: " + ", ".join("--" + name.replace("_", "-") for name in missing))

    uid = parse_uid(args.uid)
    current = int(args.current_serial, 16)
    if not 1 <= args.counter <= 0xFFFFFFFF:
        raise SystemExit("the counter is between 1 and 4294967295")
    plan = f"version rule {args.mode} on the head {current:08X} with unique ID {uid[0]:08X} {uid[1]:08X} {uid[2]:08X}, counter {args.counter}"
    if not args.yes:
        print(f"VERSION_COMPAT_COMMAND=PLAN {plan} (add --yes to make it)")
        return 2
    command = version_compat.make_command(read_seed(args.key_file), uid, current, version_compat.MODE_NAMES[args.mode], args.counter)
    print(f"VERSION_COMPAT_COMMAND=MADE {plan}")
    for frame in version_compat.chunks(command):
        print(slcan.encode_line(version_compat.ID_COMMAND, frame))
    print(f"{expect} (status 0 = stored)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
