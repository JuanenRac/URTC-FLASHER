# =============================================================================
# URTC-COMMON - src/urtc_common/multinode_host.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""What a host program does to work with several tool heads on one bus: find them, select one, keep the selection, and refuse to send
a single-head frame to a head it has not confirmed.

No window, no thread and no transport of its own: the caller gives four functions (``HostIO``) and calls ``tick`` while it works. Over
a bus with one head and no extension everything stays as it is today: ``legacy`` is true when discovery finds nobody, and ``send`` then
passes the frame through. With heads present a single-head frame goes out only to a node that reported itself selected in the last
status, is not in conflict, has no latched fault and is not in its bootloader; anything destructive (the bootloader frames) needs that
confirmation even more clearly, because an unselected head ignores them and a lapsed selection would send them to nobody.

Written against the model in ``urtc_common.multinode_sim``; it has not been tried on boards.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from . import multinode as mn
from . import protocol as p

BOOTLOADER_IDS = range(0x7F0, 0x800)
# The reason byte the host puts in SAFE_STOP when it lets go of a head whose selection it lost (the byte is informational for the nodes).
STOP_REASON_HOST_LAPSE = 0x10


class NodeNotReady(RuntimeError):
    """The node cannot be commanded now: not found, gone, in conflict, faulted, in its bootloader or not confirmed selected."""

    def __init__(self, node: int | None, reason: str):
        super().__init__(f"node {node}: {reason}")
        self.node = node
        self.reason = reason


@dataclass
class Lapse:
    """The selection the host wanted and no longer has: which head, why, and whether the host asked every head for its safe state."""

    node: int
    reason: str            # gone, conflict, fault, bootloader, lost, several
    released: bool         # SAFE_STOP was sent (the outputs of the heads go to their safe state)
    at_ms: int


@dataclass
class HostIO:
    send: Callable[[int, bytes], None]
    poll: Callable[[], list]           # frames received since the last call: (time_ms, can_id, data)
    now: Callable[[], int]             # the clock of the host in ms
    advance: Callable[[int], None]     # let ms go by (the bus model steps; a real host sleeps)


class MultinodeHost:
    def __init__(self, io: HostIO, slot_ms: int = p.MN_DISCOVER_SLOT_MS, confirm_ms: int = 100, attempts: int = 3,
                 release_on_lapse: bool = True):
        self.io = io
        # What to do when the head that was being driven stops being confirmed selected (it was lost, faulted, entered its
        # bootloader, or its selection lapsed): True (the conservative default) asks every head for its safe state, False only
        # tells the caller. Either way the host stops believing that it has a selection and the caller is told through ``lapses``.
        self.release_on_lapse = release_on_lapse
        self.lapses: list[Lapse] = []
        self.suspended = False             # the head is about to reset into its bootloader: no lapse is reported and no SELECT is repeated
        self.slot_ms = slot_ms
        self.confirm_ms = confirm_ms
        self.attempts = attempts
        self.table = mn.NodeTable()
        self.legacy = False
        self.wanted: int | None = None      # the node the caller selected and wants kept
        self._seq = 0
        self._last_select_ms = 0

    # -- listening ----------------------------------------------------------------------------------------------------------
    def ingest(self) -> None:
        for _t, can_id, data in self.io.poll():
            self._handle(can_id, data)

    def _handle(self, can_id: int, data: bytes) -> None:
        split = p.mn_split_id(can_id)
        if split is None:
            return
        name, node = split
        now = self.io.now()
        if name == "NODE_INFO":
            fields = p.decode_mn_node_info(data)
            if fields is not None:
                self.table.on_info(node, fields, now)
        elif name == "NODE_STATUS":
            fields = p.decode_mn_node_status(data)
            if fields is not None and self.table.on_status(node, fields, now) is None:
                # A status from a node never announced: ask everyone to announce, so it is listed with its serial.
                self._send(*p.encode_mn_discover(p.MN_VERSION, self.slot_ms))

    def _send(self, can_id: int, data: bytes) -> None:
        self.io.send(can_id, data)

    # -- finding the heads --------------------------------------------------------------------------------------------------
    def discover(self, window_ms: float | None = None) -> list[int]:
        """Ask every head to announce itself and wait for the answers; returns the addresses found. None found means a bus with one
        head and no extension, or none at all: ``legacy`` is set and single-head frames pass through unchanged."""
        self.ingest()
        self.table = mn.NodeTable()
        self._send(*p.encode_mn_discover(p.MN_VERSION, self.slot_ms))
        wait = int(window_ms if window_ms is not None else mn.discover_window_ms(self.slot_ms))
        for _ in range(wait + 1):
            self.io.advance(1)
            self.ingest()
        found = self.table.alive(self.io.now())
        self.legacy = not found
        return found

    def node_info(self, node: int):
        return self.table.nodes.get(node)

    # -- selecting ----------------------------------------------------------------------------------------------------------
    def select(self, node: int) -> None:
        """Select a head and wait for its own status to say so. Raises NodeNotReady and leaves nothing selected when it cannot."""
        self.ingest()
        now = self.io.now()
        if self.table.nodes.get(node) is None:
            raise NodeNotReady(node, "not announced")
        if not self.table.may_command(node, now):
            raise NodeNotReady(node, self._why_not(node, now))
        self.suspended = False
        for _attempt in range(self.attempts):
            self._seq = (self._seq + 1) & 0xFF
            self._send(*p.encode_mn_select(p.MN_SELECT_SELECT, node, self._seq))
            self._last_select_ms = self.io.now()
            for _ in range(self.confirm_ms):
                self.io.advance(1)
                self.ingest()
                chosen = self.table.selected(self.io.now())
                if chosen == node:
                    self.wanted = node
                    return
                if chosen is None and self._several_selected():
                    break
            if self._several_selected():
                # Two heads report themselves selected: no selection until it is cleared, then try again.
                self._send(*p.encode_mn_select(p.MN_SELECT_DESELECT_ALL, 0, self._seq))
                self.io.advance(self.confirm_ms)
                self.ingest()
        self._send(*p.encode_mn_select(p.MN_SELECT_DESELECT_ALL, 0, self._seq))
        self.wanted = None
        raise NodeNotReady(node, "did not confirm the selection")

    def _several_selected(self) -> bool:
        now = self.io.now()
        return sum(1 for n in self.table.alive(now) if self.table.nodes[n].state & p.MN_STATE_SELECTED) > 1

    def _why_not(self, node: int, now: int) -> str:
        record = self.table.nodes[node]
        if node not in self.table.alive(now):
            return "gone (no status for too long)"
        if record.conflict or record.state & p.MN_STATE_CONFLICT:
            return "another board uses its address"
        if record.state & p.MN_STATE_FAULT:
            return "a fault is latched"
        if record.state & p.MN_STATE_BOOTLOADER:
            return "in its bootloader"
        return "not ready"

    def release(self) -> None:
        self._send(*p.encode_mn_select(p.MN_SELECT_DESELECT_ALL, 0, self._seq))
        self.wanted = None
        self.suspended = False

    def suspend(self) -> None:
        """The selected head is going to reset into its bootloader (the update tools call this after the enter-bootloader frame): its status
        stops by design, so ``tick`` neither calls that a lapse nor repeats SELECT until ``release`` or a new ``select``."""
        self.suspended = True

    def _lapse_reason(self, node: int, now: int) -> str | None:
        record = self.table.nodes.get(node)
        if record is None or node not in self.table.alive(now):
            return "gone"
        if record.conflict or record.state & p.MN_STATE_CONFLICT:
            return "conflict"
        if record.state & p.MN_STATE_FAULT:
            return "fault"
        if record.state & p.MN_STATE_BOOTLOADER:
            return "bootloader"
        if self._several_selected():
            return "several"
        if not record.state & p.MN_STATE_SELECTED and now - self._last_select_ms > self.confirm_ms:
            return "lost"
        return None

    def take_lapses(self) -> list[Lapse]:
        """The lapses since the last call (the caller shows them once)."""
        taken, self.lapses = self.lapses, []
        return taken

    def tick(self) -> None:
        """Call while working: reads the bus, notices a head that is no longer confirmed selected and repeats SELECT before it lapses.

        When the head being driven is gone, in conflict, faulted, in its bootloader or no longer reports itself selected, the host forgets
        the selection, records a ``Lapse`` and, with ``release_on_lapse`` (the default), sends SAFE_STOP so no head keeps an output on
        without a host watching it. Nothing is ever sent to the head again until it is selected and confirmed anew."""
        if self.suspended:
            return
        self.ingest()
        if self.wanted is not None:
            why = self._lapse_reason(self.wanted, self.io.now())
            if why is not None:
                self.lapses.append(Lapse(self.wanted, why, self.release_on_lapse, self.io.now()))
                self.wanted = None
                if self.release_on_lapse:
                    self.safe_stop(STOP_REASON_HOST_LAPSE)
                return
        if self.wanted is not None and self.io.now() - self._last_select_ms >= p.MN_SELECT_TIMEOUT_MS // 2:
            self._seq = (self._seq + 1) & 0xFF
            self._send(*p.encode_mn_select(p.MN_SELECT_SELECT, self.wanted, self._seq))
            self._last_select_ms = self.io.now()

    # -- sending ------------------------------------------------------------------------------------------------------------
    def require_selected(self, node: int) -> None:
        self.ingest()
        now = self.io.now()
        record = self.table.nodes.get(node)
        if record is None:
            raise NodeNotReady(node, "not announced")
        if not self.table.may_command(node, now):
            raise NodeNotReady(node, self._why_not(node, now))
        if self.table.selected(now) != node:
            raise NodeNotReady(node, "not confirmed selected")

    def is_confirmed(self, node: int) -> bool:
        """True when, by what the host has already read, the node is alive, commandable and the one head that reports itself selected.
        Reads nothing from the bus (``require_selected`` does), so a program can ask it in the middle of its own traffic."""
        now = self.io.now()
        return self.table.may_command(node, now) and self.table.selected(now) == node

    def send(self, can_id: int, data: bytes, node: int | None = None) -> None:
        """Send a single-head frame. On a bus without the extension it goes straight out; with heads present it needs ``node`` to be
        the confirmed selected head, and the bootloader frames refuse anything else."""
        if p.mn_split_id(can_id) is not None:
            raise ValueError("an identifier of the extension is not a single-head frame")
        if self.legacy and not self.table.nodes:
            self._send(can_id, data)
            return
        if node is None:
            raise NodeNotReady(None, "several heads on the bus: say which one")
        self.require_selected(node)
        self._send(can_id, data)

    def send_destructive(self, can_id: int, data: bytes, node: int) -> None:
        """Bootloader entry, erase and update frames: the confirmation is checked even if the bus looked like a single head."""
        if can_id not in BOOTLOADER_IDS and can_id != p.CAN_ID_ERASE_FRAM:
            raise ValueError("not a destructive frame")
        if self.legacy and not self.table.nodes:
            self._send(can_id, data)
            return
        self.require_selected(node)
        self._send(can_id, data)

    def safe_stop(self, reason: int = 0) -> None:
        """Ask every head to enter its safe state (never needs a selection)."""
        self._send(*p.encode_mn_safe_stop(reason))

    def command_status(self, node: int) -> bytes | None:
        """The short status query to one head, without selecting it; None when no answer comes."""
        self.ingest()
        self._send(*p.encode_mn_node_cmd(node, 0x110, b""))
        for _ in range(self.confirm_ms):
            self.io.advance(1)
            for _t, can_id, data in self.io.poll():
                split = p.mn_split_id(can_id)
                if split == ("NODE_RESP", node):
                    fields = p.decode_mn_node_resp(data)
                    if fields is not None:
                        return bytes(fields["data"])
                elif split is not None:
                    self._handle(can_id, data)
        return None
