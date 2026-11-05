#!/usr/bin/env python3
# =============================================================================
# URTC Flasher - tools/serial_command.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Workshop tool: make the signed command that programs the serial number of one bootloader.

    python tools/serial_command.py --key-file KEY --uid W0,W1,W2 --current-serial HEX --serial HEX --counter N --yes

The command is the one of ``0x7EE`` (see docs of URTC-COMMON, "The signed command"): it names the 96-bit unique ID of the head (the three words that the
bootloader answers to the UID query, in hexadecimal), the serial the head answers with now, the new serial and a counter that must be higher than the one
the head stores (the first command needs 1 or more). The tool prints the twelve SLCAN lines to put on the bus, one per line, and the answer to expect.

The private key is NEVER looked for: ``--key-file`` names a file with the 32-byte seed (64 hexadecimal digits, or the raw 32 bytes). Only a bootloader built with
the programmable serial, whose trust table holds the public half of that key, will obey. Nothing is sent from here and without ``--yes`` the tool only
describes what it would make: writing a serial is a deliberate act of the workshop.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from urtc_can import bl_serial, slcan  # noqa: E402


def read_seed(path: Path) -> bytes:
    raw = path.read_bytes()
    if len(raw) == 32:
        return raw
    try:
        text = raw.decode("ascii").strip()
        seed = bytes.fromhex(text)
    except (UnicodeDecodeError, ValueError):
        raise SystemExit("the key file holds neither 32 raw bytes nor 64 hexadecimal digits") from None
    if len(seed) != 32:
        raise SystemExit("the key file must hold a 32-byte seed")
    return seed


def parse_uid(text: str) -> tuple[int, int, int]:
    parts = [p.strip() for p in text.split(",")]
    if len(parts) != 3:
        raise SystemExit("--uid takes three words in hexadecimal, separated by commas")
    return tuple(int(p, 16) & 0xFFFFFFFF for p in parts)  # type: ignore[return-value]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--key-file", type=Path, required=True, help="file with the 32-byte seed of a key of the trust table of the bootloader")
    parser.add_argument("--uid", required=True, help="the three words of the unique ID of the head, hexadecimal, comma separated")
    parser.add_argument("--current-serial", required=True, help="the serial the head answers with now (hexadecimal)")
    parser.add_argument("--serial", required=True, help="the new serial (hexadecimal, not 0 and not FFFFFFFF)")
    parser.add_argument("--counter", type=int, required=True, help="higher than the counter the head stores; 1 or more for the first")
    parser.add_argument("--yes", action="store_true", help="really make the command (without it the tool only describes it)")
    args = parser.parse_args(argv)

    uid = parse_uid(args.uid)
    current, serial = int(args.current_serial, 16), int(args.serial, 16)
    if serial in (0, 0xFFFFFFFF):
        raise SystemExit("0 and FFFFFFFF are not serials")
    if not 1 <= args.counter <= 0xFFFFFFFF:
        raise SystemExit("the counter is between 1 and 4294967295")
    plan = f"serial {current:08X} -> {serial:08X} on the head with unique ID {uid[0]:08X} {uid[1]:08X} {uid[2]:08X}, counter {args.counter}"
    if not args.yes:
        print(f"SERIAL_COMMAND=PLAN {plan} (add --yes to make it)")
        return 2
    command = bl_serial.make_command(read_seed(args.key_file), uid, current, serial, args.counter)
    print(f"SERIAL_COMMAND=MADE {plan}")
    for frame in bl_serial.chunks(command):
        print(slcan.encode_line(bl_serial.ID_CHUNK, frame))
    print(f"EXPECT t{bl_serial.ID_RESULT:03X}5 00 {serial:08X} (status 0 = written)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
