# =============================================================================
# URTC-COMMON - src/urtc_common/multinode_sim.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""A model of the nodes of the multinode extension and of a bus that joins them, to try a host against without boards.

``SimNode`` follows the rules of ``docs/MULTINODE.md`` as the firmware applies them (``multinode.c``): it listens for 1.5 s after
it starts, behaves as the one head of the bus when it hears nobody, starts unselected when it hears another node, obeys single-head
frames only while selected, lets a selection lapse after 2 s, latches a conflict when a frame arrives on its own address, and obeys
SAFE_STOP always. The scenarios in ``conformance/multinode_scenarios.json`` hold both this model and the firmware to the same
steps. ``SimBus`` delivers every frame to every other node, as a bus does, and keeps the clock.

Approximations, all on the safe side of what a host must handle: a frame is delivered at the millisecond it is sent, arbitration is
not modelled (frames due in one millisecond go out in order of identifier), and two boards that send the same identifier at the
same time both hear the other's frame, where a real bus would corrupt it (the effect on the nodes is the same: each sees a frame on
its own address and latches a conflict). Nothing here has been compared with a bus of boards.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import protocol as p

U32 = 0xFFFFFFFF
PHASE_LISTEN, PHASE_UNSELECTED, PHASE_SELECTED, PHASE_LEGACY = range(4)
VERDICT_PASS, VERDICT_CONSUME = "pass", "consume"
MN_CMD_FUNC_STATUS = 0x110


def _since(now: int, then: int) -> int:
    """Signed distance in ms from then to now on a 32-bit counter."""
    d = (now - then) & U32
    return d - (1 << 32) if d & 0x80000000 else d


@dataclass
class Effects:
    safe_stop: bool = False
    answer_cmd: bool = False
    cmd_func: int = 0


@dataclass
class SimNode:
    address: int
    tool: int = 3
    instance: int = 0
    serial: int = 0
    enabled: bool = True
    start_ms: int = 0
    phase: int = PHASE_LISTEN
    conflict: bool = False
    seq: int = 0
    stop_reason: int = 0
    info_pending: bool = True
    status_now: bool = False
    select_deadline_ms: int = 0
    info_due_ms: int = 0
    status_due_ms: int = 0
    fault: bool = False
    error: int = 0
    # what the model lets the tests observe
    obeyed: list = field(default_factory=list)       # single-head frames (id, data) handed to the dispatcher
    safe_stops: int = 0

    def __post_init__(self):
        self.address &= p.MN_ADDRESS_MASK
        self.boot_ms = self.start_ms & U32
        self.info_due_ms = (self.boot_ms + self.address * p.MN_DISCOVER_SLOT_MS) & U32
        self.status_due_ms = (self.boot_ms + p.MN_STATUS_PERIOD_MS) & U32

    # -- the rules ----------------------------------------------------------------------------------------------------------
    def _advance(self, now: int) -> None:
        if self.phase == PHASE_LISTEN and _since(now, self.boot_ms) >= p.MN_LEGACY_LISTEN_MS:
            self.phase = PHASE_UNSELECTED if self.conflict else PHASE_LEGACY
        if self.phase == PHASE_SELECTED and _since(now, self.select_deadline_ms) >= 0:
            self.phase = PHASE_UNSELECTED
            self.status_now = True

    def may_single_head(self) -> bool:
        return not self.conflict and self.phase in (PHASE_SELECTED, PHASE_LEGACY)

    def state_flags(self, fault: bool | None = None) -> int:
        fault = self.fault if fault is None else fault
        return ((p.MN_STATE_SELECTED if self.may_single_head() else 0) | (p.MN_STATE_FAULT if fault else 0)
                | (p.MN_STATE_CONFLICT if self.conflict else 0))

    def _on_select(self, data: bytes, now: int) -> None:
        if len(data) != 3 or data[0] > p.MN_SELECT_SELECT or data[1] > p.MN_ADDRESS_MASK:
            return
        self.seq = data[2]
        if data[0] == p.MN_SELECT_SELECT and data[1] == self.address:
            if self.conflict:
                return
            self.phase = PHASE_SELECTED
            self.select_deadline_ms = (now + p.MN_SELECT_TIMEOUT_MS) & U32
            self.status_now = True
        else:
            self.phase = PHASE_UNSELECTED
            self.status_now = True

    def on_rx(self, can_id: int, data: bytes, now: int) -> tuple[str, Effects]:
        """Every received frame goes through here first. Returns the verdict and the effects the board must carry out."""
        fx = Effects()
        now &= U32
        self._advance(now)
        if not p.MN_ID_DISCOVER <= can_id <= 0x49F:
            if self.may_single_head():
                self.obeyed.append((can_id, bytes(data)))
                return VERDICT_PASS, fx
            return VERDICT_CONSUME, fx
        for base in (p.MN_ID_NODE_INFO_BASE, p.MN_ID_NODE_STATUS_BASE):
            if base <= can_id < base + p.MN_NODE_MAX:
                if can_id & p.MN_ADDRESS_MASK == self.address:
                    if not self.conflict:
                        self.conflict = True
                        self.phase = PHASE_UNSELECTED
                        self.status_now = True
                        fx.safe_stop = True
                        self.safe_stops += 1
                elif self.phase == PHASE_LISTEN:
                    self.phase = PHASE_UNSELECTED
                    self.status_now = True
                return VERDICT_CONSUME, fx
        if can_id == p.MN_ID_DISCOVER:
            if len(data) == 2 and data[0] >= p.MN_VERSION and 1 <= data[1] <= 50:
                self.info_pending = True
                self.info_due_ms = (now + self.address * data[1]) & U32
        elif can_id == p.MN_ID_SELECT:
            self._on_select(data, now)
        elif can_id == p.MN_ID_SAFE_STOP:
            if len(data) == 1:
                self.stop_reason = data[0]
                fx.safe_stop = True
                self.safe_stops += 1
        elif can_id == p.MN_ID_NODE_CMD_BASE + self.address:
            if not self.conflict and 2 <= len(data) <= 8:
                func = (data[0] << 8) | data[1]
                if func == MN_CMD_FUNC_STATUS:
                    fx.answer_cmd = True
                    fx.cmd_func = func
        return VERDICT_CONSUME, fx

    def service(self, now: int, fault: bool | None = None, error: int | None = None) -> tuple[int, bytes] | None:
        """The next frame due, or None; call until it returns None."""
        now &= U32
        fault = self.fault if fault is None else fault
        error = self.error if error is None else error
        self._advance(now)
        if self.info_pending and _since(now, self.info_due_ms) >= 0:
            self.info_pending = False
            return p.encode_mn_node_info(self.address, tool=self.tool, state=self.state_flags(fault), instance=self.instance,
                                         mn_version=p.MN_VERSION, serial=self.serial)
        if self.status_now or _since(now, self.status_due_ms) >= 0:
            uptime = min(_since(now, self.boot_ms) // 1000, 0xFFFF)
            self.status_now = False
            self.status_due_ms = (now + p.MN_STATUS_PERIOD_MS) & U32
            return p.encode_mn_node_status(self.address, state=self.state_flags(fault), error=error, uptime_s=uptime)
        return None

    def answer(self, func: int, data: bytes = b"") -> tuple[int, bytes]:
        return p.encode_mn_node_resp(self.address, func=func, data=data[:p.MN_CMD_ARGS_MAX])


class SimBus:
    """Nodes that hear each other and a host, on a clock that the caller moves."""

    def __init__(self, nodes: list[SimNode] | None = None, now_ms: int = 0):
        self.nodes: list[SimNode] = list(nodes or [])
        self.now = now_ms                # the 32-bit millisecond counter of the boards
        self.elapsed = 0                 # the clock of the host: milliseconds since the bus was made, which never wraps
        self.log: list[tuple[int, int, bytes, str]] = []    # (time, id, data, sender)
        self.host_inbox: list[tuple[int, int, bytes]] = []  # frames the host has not read yet
        self.safe_state_calls: dict[int, int] = {}
        self._pending_answers: list = []

    def add(self, node: SimNode) -> SimNode:
        self.nodes.append(node)
        return node

    def _deliver(self, can_id: int, data: bytes, sender: SimNode | None) -> None:
        self.log.append((self.now, can_id, bytes(data), "host" if sender is None else f"node{sender.address}"))
        if sender is not None:
            self.host_inbox.append((self.now, can_id, bytes(data)))
        for node in self.nodes:
            if node is sender or not node.enabled:
                continue
            verdict, fx = node.on_rx(can_id, data, self.now)
            if fx.safe_stop:
                self.safe_state_calls[node.address] = self.safe_state_calls.get(node.address, 0) + 1
            if fx.answer_cmd:
                self._pending_answers.append((node, fx.cmd_func))

    def host_send(self, can_id: int, data: bytes = b"") -> None:
        self._pending_answers = []
        self._deliver(can_id, data, None)
        self._flush_answers()

    def _flush_answers(self) -> None:
        while self._pending_answers:
            node, func = self._pending_answers.pop(0)
            frame = node.answer(func, bytes(6))
            self._deliver(frame[0], frame[1], node)

    def step(self, ms: int = 1) -> None:
        """Advance the clock; each millisecond every node sends what is due (in order of identifier)."""
        for _ in range(ms):
            self.now = (self.now + 1) & U32
            self.elapsed += 1
            self._pending_answers = []
            due = []
            for node in self.nodes:
                if not node.enabled:
                    continue
                while (frame := node.service(self.now)) is not None:
                    due.append((frame[0], frame[1], node))
            for can_id, data, node in sorted(due, key=lambda f: f[0]):
                self._deliver(can_id, data, node)
            self._flush_answers()

    def read_host(self) -> list[tuple[int, int, bytes]]:
        frames, self.host_inbox = self.host_inbox, []
        return frames
