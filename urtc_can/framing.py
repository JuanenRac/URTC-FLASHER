# =============================================================================
# URTC-COMMON - src/urtc_common/framing.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""A classic CAN frame as this protocol uses it: a standard 11-bit identifier and up to eight bytes."""
from __future__ import annotations

from typing import Any

from dataclasses import dataclass

from . import protocol

CAN_ID_MAX = protocol.STANDARD_ID_MAX
DLC_MAX = protocol.DLC_MAX


class FrameError(ValueError):
    """The identifier or the payload cannot be carried by a classic CAN frame."""


def check_frame(can_id: int, data: bytes) -> None:
    """Raise FrameError unless the pair is a valid standard classic CAN frame."""
    if isinstance(can_id, bool) or not isinstance(can_id, int):
        raise FrameError("the identifier must be an integer")
    if can_id < 0:
        raise FrameError(f"ID {can_id} is negative - not a valid CAN ID")
    if can_id > CAN_ID_MAX:
        raise FrameError(f"ID 0x{can_id:X} is outside the standard 11-bit range (0-0x{CAN_ID_MAX:X})")
    if len(data) > DLC_MAX:
        raise FrameError(f"CAN data payload cannot exceed {DLC_MAX} bytes")


@dataclass(frozen=True)
class CanFrame:
    """One standard data frame."""

    id: int
    data: bytes = b""

    def __post_init__(self) -> None:
        object.__setattr__(self, "data", bytes(self.data))
        check_frame(self.id, self.data)

    @property
    def dlc(self) -> int:
        return len(self.data)

    def id_hex(self) -> str:
        return f"0x{self.id:03X}"

    def data_hex(self) -> str:
        return self.data.hex().upper()

    @classmethod
    def from_hex(cls, id_text: str, data_text: str = "") -> "CanFrame":
        """Build a frame from ``0x1A6`` and ``01``-style text, as the conformance vectors write them."""
        return cls(int(id_text, 16), bytes.fromhex(data_text))

    def name(self) -> str | None:
        """The canonical name of the identifier, or None for one the protocol does not define."""
        info: Any = protocol.MESSAGES.get(self.id)
        return info["name"] if info else None


def is_magic(can_id: int, data: bytes) -> str | None:
    """The name of the magic payload this frame carries (identifier and four bytes both right), else None."""
    magic: Any
    for name, magic in protocol.MAGIC_PAYLOADS.items():
        if can_id == magic["id"] and bytes(data) == bytes.fromhex(magic["data"]):
            return name
    return None
