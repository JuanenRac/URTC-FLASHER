# =============================================================================
# URTC-COMMON - src/urtc_common/multinode.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Host-side helpers for the multinode extension (several tool heads on one bus).

The firmware implements the node side behind a switch that is off by default; it is tested on the host only and has not been tried on hardware
(see docs/MULTINODE.md). Everything here is pure arithmetic and bookkeeping, so it is tested without a bus.
The frames themselves come from ``urtc_common.protocol`` (the ``encode_mn_*`` and ``decode_mn_*`` functions).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import protocol as p

# Bits of a classic CAN data frame with an 11-bit identifier, without stuffing: start of frame 1, identifier 11,
# RTR 1, IDE 1, reserved 1, DLC 4, CRC 15, CRC delimiter 1, ACK 2, end of frame 7, inter-frame space 3.
FRAME_OVERHEAD_BITS = 47
# The part of the frame that is subject to bit stuffing: everything from the start of frame to the end of the CRC.
STUFFED_OVERHEAD_BITS = 34


def address_from_jumpers(bits) -> int:
    """The node address from the five identity jumpers, ID0 first (a closed jumper is a 1)."""
    values = list(bits)
    if len(values) != p.MN_ADDRESS_BITS:
        raise ValueError(f"expected {p.MN_ADDRESS_BITS} jumper values, got {len(values)}")
    return sum((1 if v else 0) << i for i, v in enumerate(values))


def frame_bits(dlc: int, worst_case: bool = False) -> int:
    """Bits one classic data frame occupies on the bus; worst_case adds the maximum number of stuff bits."""
    if not isinstance(dlc, int) or isinstance(dlc, bool) or not 0 <= dlc <= p.DLC_MAX:
        raise ValueError(f"dlc {dlc!r} is outside 0..{p.DLC_MAX}")
    bits = FRAME_OVERHEAD_BITS + 8 * dlc
    if worst_case:
        bits += (STUFFED_OVERHEAD_BITS + 8 * dlc - 1) // 4
    return bits


def bus_load(frames_per_second, bitrate: int, worst_case: bool = False) -> float:
    """Fraction of the bus a traffic mix uses. frames_per_second is a list of (dlc, frames per second)."""
    if bitrate <= 0:
        raise ValueError("bitrate must be positive")
    return sum(rate * frame_bits(dlc, worst_case) for dlc, rate in frames_per_second) / bitrate


def status_traffic(nodes: int) -> list[tuple[int, float]]:
    """The periodic traffic of the extension for a number of nodes: one status frame per node per period."""
    if not 0 <= nodes <= p.MN_NODE_MAX:
        raise ValueError(f"nodes {nodes!r} is outside 0..{p.MN_NODE_MAX}")
    return [(4, nodes * 1000.0 / p.MN_STATUS_PERIOD_MS)]


def discover_answer_delay_ms(node: int, slot_ms: int = p.MN_DISCOVER_SLOT_MS) -> int:
    """How long after DISCOVER a node answers: its address times the slot, so the answers are spread out."""
    if not 0 <= node <= p.MN_ADDRESS_MASK:
        raise ValueError(f"node address {node!r} is outside 0..{p.MN_ADDRESS_MASK}")
    return node * slot_ms


def discover_window_ms(slot_ms: int = p.MN_DISCOVER_SLOT_MS, bitrate: int = p.BITRATE, nodes: int = p.MN_NODE_MAX) -> float:
    """How long the host waits for every answer.

    The answers are spread by the slot, but on a slow bus a frame takes longer than a slot, so the answers queue up and the
    wait is whichever is longer: the last slot plus one frame, or all the frames back to back. One slot of margin is added.
    """
    frame_ms = 1000.0 * frame_bits(8, worst_case=True) / bitrate
    last = discover_answer_delay_ms(p.MN_ADDRESS_MASK, slot_ms) + frame_ms
    return max(last, nodes * frame_ms) + slot_ms


@dataclass
class NodeRecord:
    node: int
    tool: int
    state: int
    instance: int
    serial: int
    last_seen_ms: int
    error: int = 0
    uptime_s: int = 0
    conflict: bool = False


@dataclass
class NodeTable:
    """What the host knows about the nodes of one bus, fed with decoded NODE_INFO and NODE_STATUS frames."""

    timeout_ms: int = p.MN_NODE_TIMEOUT_MS
    nodes: dict[int, NodeRecord] = field(default_factory=dict)

    def on_info(self, node: int, fields: dict, now_ms: int) -> NodeRecord:
        known = self.nodes.get(node)
        record = NodeRecord(node, fields["tool"], fields["state"], fields["instance"], fields["serial"], now_ms)
        if known is not None and known.serial != record.serial:
            # Two different boards claim one address: neither is trusted until one is removed or re-addressed.
            record.conflict = True
            known.conflict = True
        elif known is not None:
            record.conflict = known.conflict
        self.nodes[node] = record
        return record

    def on_status(self, node: int, fields: dict, now_ms: int) -> NodeRecord | None:
        record = self.nodes.get(node)
        if record is None:
            return None
        record.state = fields["state"]
        record.error = fields["error"]
        record.uptime_s = fields["uptime_s"]
        record.last_seen_ms = now_ms
        return record

    def alive(self, now_ms: int) -> list[int]:
        return sorted(n for n, r in self.nodes.items() if now_ms - r.last_seen_ms <= self.timeout_ms)

    def gone(self, now_ms: int) -> list[int]:
        return sorted(n for n, r in self.nodes.items() if now_ms - r.last_seen_ms > self.timeout_ms)

    def selected(self, now_ms: int) -> int | None:
        """The one live node that reports itself selected, or None; more than one is an error the host must clear."""
        chosen = [n for n in self.alive(now_ms) if self.nodes[n].state & p.MN_STATE_SELECTED]
        return chosen[0] if len(chosen) == 1 else None

    def may_command(self, node: int, now_ms: int) -> bool:
        """A node may be commanded only while it is alive, in no conflict, with no latched fault and out of its bootloader."""
        record = self.nodes.get(node)
        if record is None or node not in self.alive(now_ms) or record.conflict:
            return False
        return not record.state & (p.MN_STATE_FAULT | p.MN_STATE_CONFLICT | p.MN_STATE_BOOTLOADER)
