# =============================================================================
# URTC-COMMON - src/urtc_ui/formatting.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Text for identifiers, bitrates, frames, sizes and durations, the same in every program. All functions are pure."""
from __future__ import annotations

import re


def format_can_id(can_id: int, extended: bool = False) -> str:
    """0x1A0 for a standard identifier (three digits), 0x00000123 for an extended one (eight digits)."""
    limit = 0x1FFFFFFF if extended else 0x7FF
    if isinstance(can_id, bool) or not isinstance(can_id, int) or not 0 <= can_id <= limit:
        raise ValueError(f"identifier {can_id!r} is outside 0..0x{limit:X}")
    return f"0x{can_id:08X}" if extended else f"0x{can_id:03X}"


def parse_can_id(text: str, extended: bool = False) -> int:
    """Read '0x1a0', '1A0h' or a plain decimal number as an identifier; refuses anything outside the identifier range."""
    value = text.strip().lower()
    if re.fullmatch(r"0x[0-9a-f]+", value):
        number = int(value, 16)
    elif re.fullmatch(r"[0-9a-f]+h", value):
        number = int(value[:-1], 16)
    elif re.fullmatch(r"[0-9]+", value):
        number = int(value, 10)
    else:
        raise ValueError(f"not an identifier: {text!r}")
    format_can_id(number, extended)
    return number


def format_hex(data: bytes | bytearray | list[int], separator: str = " ") -> str:
    """Bytes as upper-case hexadecimal pairs."""
    return separator.join(f"{b:02X}" for b in bytes(data))


def format_frame(can_id: int, data: bytes, extended: bool = False) -> str:
    """The usual single-line form: 0x1A0#01 02 03."""
    return f"{format_can_id(can_id, extended)}#{format_hex(data)}"


def format_bitrate(bps: int) -> str:
    """500000 -> '500 kbit/s', 1000000 -> '1 Mbit/s', 800 -> '800 bit/s' (the labels of the SLCAN table)."""
    if isinstance(bps, bool) or not isinstance(bps, int) or bps <= 0:
        raise ValueError(f"bitrate {bps!r} must be a positive integer")
    if bps % 1_000_000 == 0:
        return f"{bps // 1_000_000} Mbit/s"
    if bps % 1000 == 0:
        return f"{bps // 1000} kbit/s"
    return f"{bps} bit/s"


def parse_bitrate(label: str) -> int:
    """The inverse of format_bitrate; also accepts 'kbps', 'mbps', 'k' and 'M' spellings and a bare number of bit/s."""
    match = re.fullmatch(r"\s*([0-9]+(?:\.[0-9]+)?)\s*(m|k)?(?:bit/s|bps|b/s)?\s*", label.lower())
    if not match:
        raise ValueError(f"not a bitrate: {label!r}")
    number = float(match.group(1)) * {"m": 1_000_000, "k": 1000, None: 1}[match.group(2)]
    if number <= 0 or number != int(number):
        raise ValueError(f"not a whole positive bitrate: {label!r}")
    return int(number)


def format_bytes(count: int) -> str:
    """1536 -> '1.5 KiB'; below 1 KiB the plain count."""
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise ValueError(f"size {count!r} must be a non-negative integer")
    if count < 1024:
        return f"{count} B"
    value = float(count)
    for unit in ("KiB", "MiB", "GiB"):
        value /= 1024
        if value < 1024 or unit == "GiB":
            return f"{value:.1f} {unit}"
    raise AssertionError("unreachable")


def format_duration_ms(ms: int) -> str:
    """250 -> '250 ms', 2500 -> '2.5 s', 125000 -> '2 min 5 s'."""
    if isinstance(ms, bool) or not isinstance(ms, int) or ms < 0:
        raise ValueError(f"duration {ms!r} must be a non-negative integer")
    if ms < 1000:
        return f"{ms} ms"
    if ms < 60_000:
        return f"{ms / 1000:.1f} s".replace(".0 s", " s")
    minutes, rest = divmod(ms // 1000, 60)
    return f"{minutes} min" + (f" {rest} s" if rest else "")


def format_uptime(seconds: int) -> str:
    """3725 -> '1 h 2 min'; 59 -> '59 s'; 90000 -> '1 d 1 h'. Two units at most."""
    if isinstance(seconds, bool) or not isinstance(seconds, int) or seconds < 0:
        raise ValueError(f"uptime {seconds!r} must be a non-negative integer")
    parts = []
    for unit, size in (("d", 86400), ("h", 3600), ("min", 60), ("s", 1)):
        amount, seconds = divmod(seconds, size)
        if amount:
            parts.append(f"{amount} {unit}")
    return " ".join(parts[:2]) if parts else "0 s"
