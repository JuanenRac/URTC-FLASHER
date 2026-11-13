# =============================================================================
# URTC-COMMON - src/urtc_common/health_info.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The identity frame of a head (0x1BB) read for both versions of the protocol, and the bit rate of the bus that a head declares in it.

Protocol version 2 uses byte 5 of the frame to declare the bit rate the head runs at and keeps the uptime in the last two bytes (16 bits, stopping at 65535).
Version 1 had a 24-bit uptime over bytes 5 to 7 and declared nothing. A host reads byte 5 as a rate only when byte 0 says version 2 or more, so a head with
older firmware is read as before and its rate is simply unknown: the tools then fall back on the symptoms of the bus (``bus_health``). A head that runs at another
rate than its bus is not heard at all; what the declaration adds is that two heads of one bus that were built for different rates are named, and that a tool can
show the rate each head says it runs at. Standard library only.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

CAN_ID_HEALTH_INFO = 0x1BB           # the same value as protocol.CAN_ID_HEALTH_INFO; kept here so that a copy needs nothing else
FIRST_DECLARING_VERSION = 2          # the protocol version from which byte 5 is a bit rate code
UPTIME_V2_MAX = 0xFFFF

CODE_UNKNOWN = 0
#: the code a head sends, by the bit rate in bit/s
CODE_OF_RATE = {1_000_000: 1, 500_000: 2, 250_000: 3, 125_000: 4}
RATE_OF_CODE = {code: rate for rate, code in CODE_OF_RATE.items()}


@dataclass(frozen=True)
class HealthInfo:
    protocol_version: int
    reset_cause: int
    fw_minor: int
    fw_patch: int
    fw_build: int
    uptime_s: int
    rate_code: int | None        # None: the frame does not declare a rate (version 1); 0: version 2 and not declared; 1..4 a rate

    @property
    def rate_bps(self) -> int | None:
        """The declared bit rate in bit/s, or None when it is not declared or the code is one this reader does not know."""
        return RATE_OF_CODE.get(self.rate_code) if self.rate_code is not None else None


def encode(protocol_version: int, reset_cause: int, fw_minor: int, fw_patch: int, fw_build: int, uptime_s: int, rate_bps: int | None = None) -> bytes:
    """The eight bytes of the frame as a head of this protocol version sends them (used by the virtual boards and the tests).

    Version 1 ignores ``rate_bps`` and carries a 24-bit uptime; version 2 carries the rate code (0 when ``rate_bps`` is None or not one of the four known rates)
    and an uptime that stops at 65535."""
    head = bytes([protocol_version & 0xFF, reset_cause & 0xFF, fw_minor & 0xFF, fw_patch & 0xFF, fw_build & 0xFF])
    if protocol_version >= FIRST_DECLARING_VERSION:
        return head + bytes([CODE_OF_RATE.get(rate_bps or 0, CODE_UNKNOWN)]) + min(max(uptime_s, 0), UPTIME_V2_MAX).to_bytes(2, "big")
    return head + min(max(uptime_s, 0), 0xFFFFFF).to_bytes(3, "big")


def parse(data: bytes) -> HealthInfo | None:
    """The fields of a 0x1BB payload, or None when it is not eight bytes long. The rate is read only from a frame of version 2 or more."""
    if len(data) != 8:
        return None
    version = data[0]
    if version >= FIRST_DECLARING_VERSION:
        return HealthInfo(version, data[1], data[2], data[3], data[4], int.from_bytes(data[6:8], "big"), data[5])
    return HealthInfo(version, data[1], data[2], data[3], data[4], int.from_bytes(data[5:8], "big"), None)


def declared_rates(frames: Iterable[bytes]) -> list[int]:
    """The bit rates (bit/s) that the 0x1BB frames declare, one per frame that declares a known one, in order; a frame that declares nothing is skipped."""
    rates: list[int] = []
    for frame in frames:
        info = parse(bytes(frame))
        if info is not None and info.rate_bps is not None:
            rates.append(info.rate_bps)
    return rates


def rates_by_head(frames_by_head: Mapping[str, bytes]) -> dict[str, int | None]:
    """For each head (a name, a serial number or a node number as text) the rate its last 0x1BB frame declares, or None."""
    result: dict[str, int | None] = {}
    for head, frame in frames_by_head.items():
        info = parse(bytes(frame))
        result[str(head)] = info.rate_bps if info is not None else None
    return result


def rate_text(rate_bps: int | None) -> str:
    """``"1 Mbit/s"``, ``"500 kbit/s"``... for a rate; an empty string for none. Numbers only: the tools put the words around it in their own language."""
    if not rate_bps:
        return ""
    return f"{rate_bps // 1_000_000} Mbit/s" if rate_bps % 1_000_000 == 0 else f"{rate_bps // 1000} kbit/s"
