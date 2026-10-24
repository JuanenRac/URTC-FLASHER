# =============================================================================
# URTC-COMMON - src/urtc_common/node_picker.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""What a program shows to let the person pick one of several tool heads on a bus: no window and no Qt, only the rules.

``NodePicker`` wraps a ``multinode_host.MultinodeHost``: it finds the heads, keeps one row per head with a state a person can read
(ready, selected, address conflict, fault, bootloader, lost), asks for a confirmation before it selects, tells the person what it did
in notices that are keys of ``node_picker_strings`` and keeps the selection while the program works. The switch of the extension is
off by default in the firmware: the picker reads it (0x1AD, when the program gives a function that does) and says so, and a bus on
which nobody answers is a plain single-head bus (``legacy``) where the program sends as it always did.

When the selected head stops being confirmed the picker records the lapse (``multinode_host``), shows it and, by default, has every
head put in its safe state; ``release_on_lapse`` switches that off. ``classify_node`` and ``switch_state`` are pure, and
``conformance/node_picker_vectors.json`` holds both to the same answers in the web studio, which has the same rules in TypeScript.
"""
from __future__ import annotations

import contextlib
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from . import multinode_host as mh
from . import node_picker_strings as strings
from . import protocol as p
from .transports import TransportError

ST_READY, ST_SELECTED, ST_CONFLICT, ST_FAULT, ST_BOOTLOADER, ST_LOST = "ready", "selected", "conflict", "fault", "bootloader", "lost"
SW_UNKNOWN, SW_OFF, SW_ON, SW_PENDING_ON, SW_PENDING_OFF = "unknown", "off", "on", "pending_on", "pending_off"
MODE_IDLE, MODE_LEGACY, MODE_MULTI = "idle", "legacy", "multi"

_STATE_KEYS = {
    ST_READY: "NP_ST_READY", ST_SELECTED: "NP_ST_SELECTED", ST_CONFLICT: "NP_ST_CONFLICT", ST_FAULT: "NP_ST_FAULT",
    ST_BOOTLOADER: "NP_ST_BOOTLOADER", ST_LOST: "NP_ST_LOST",
}
_WHY_KEYS = {
    "gone": "NP_WHY_GONE", "conflict": "NP_WHY_CONFLICT", "fault": "NP_WHY_FAULT", "bootloader": "NP_WHY_BOOTLOADER",
    "lost": "NP_WHY_LOST", "several": "NP_WHY_SEVERAL",
}
_STATUS_FAIL_KEYS = {
    ST_CONFLICT: "NP_FAIL_CONFLICT", ST_FAULT: "NP_FAIL_FAULT", ST_BOOTLOADER: "NP_FAIL_BOOTLOADER", ST_LOST: "NP_FAIL_GONE",
}
_SW_KEYS = {
    SW_UNKNOWN: "NP_SW_UNKNOWN", SW_OFF: "NP_SW_OFF", SW_ON: "NP_SW_ON", SW_PENDING_ON: "NP_SW_PENDING_ON", SW_PENDING_OFF: "NP_SW_PENDING_OFF",
}


def classify_node(state: int, conflict: bool, alive: bool) -> str:
    """The state of one head as a person reads it. A conflict, a lost head, a fault and a bootloader each rule out a selection."""
    if conflict or state & p.MN_STATE_CONFLICT:
        return ST_CONFLICT
    if not alive:
        return ST_LOST
    if state & p.MN_STATE_FAULT:
        return ST_FAULT
    if state & p.MN_STATE_BOOTLOADER:
        return ST_BOOTLOADER
    if state & p.MN_STATE_SELECTED:
        return ST_SELECTED
    return ST_READY


def switch_state(config: dict | None) -> str:
    """What the answer of the head to 0x1AC/0x1AD (``stored``, ``running``) says about the switch of the extension."""
    if not config:
        return SW_UNKNOWN
    stored, running = bool(config.get("stored")), bool(config.get("running"))
    if stored and running:
        return SW_ON
    if stored and not running:
        return SW_PENDING_ON
    if running and not stored:
        return SW_PENDING_OFF
    return SW_OFF


def tool_name(tool_id: int) -> str:
    try:
        from . import tools_catalog
    except ImportError:
        return f"tool {tool_id}"
    entry = tools_catalog.tool_by_id(tool_id)
    return entry["short_name"] if entry else f"tool {tool_id}"


@dataclass
class NodeRow:
    address: int
    tool_id: int
    tool: str
    serial: str
    instance: int
    status: str
    mine: bool            # the host selected it and keeps the selection
    selectable: bool

    def as_dict(self) -> dict:
        return {"address": self.address, "tool_id": self.tool_id, "tool": self.tool, "serial": self.serial, "instance": self.instance,
                "status": self.status, "mine": self.mine, "selectable": self.selectable}


@dataclass
class Notice:
    key: str
    params: dict = field(default_factory=dict)
    level: str = "info"        # info, warning, error

    def as_dict(self) -> dict:
        return {"key": self.key, "params": dict(self.params), "level": self.level}


class NodeBlocked(TransportError):
    """A single-head frame was not sent because several heads are on the bus and none is selected and confirmed."""


class NodePicker:
    def __init__(self, host: mh.MultinodeHost, config_reader: Callable[[], dict | None] | None = None,
                 tool_namer: Callable[[int], str] = tool_name, language: Callable[[], str] = lambda: "english",
                 lock=None) -> None:
        self.host = host
        # The program's own lock around its bus traffic: the picker reads the bus too, and must not do it in the middle of an exchange.
        self.lock = lock if lock is not None else contextlib.nullcontext()
        self.language = language
        self.in_bootloader_session = False       # the selected head took the enter-bootloader frame: its bootloader frames go out unchecked
        self.config_reader = config_reader
        self.tool_namer = tool_namer
        self.mode = MODE_IDLE
        self.switch = SW_UNKNOWN
        self.pending: int | None = None          # the head the person asked for and has not confirmed yet
        self.notices: list[Notice] = []
        self.searched = False

    # -- reading the bus -----------------------------------------------------------------------------------------------------
    def scan(self) -> None:
        """Read the switch of the extension, look for heads and say what was found. Never selects anything."""
        self.pending = None
        self.in_bootloader_session = False
        self.host.wanted = None
        try:
            with self.lock:
                self.switch = switch_state(self.config_reader() if self.config_reader else None)
                found = self.host.discover()
        except Exception as error:  # noqa: BLE001 - a transport that fails must reach the person as a notice, not as a crash of the window
            self.mode = MODE_IDLE
            self._say("NP_MSG_SCAN_FAILED", level="error", text=str(error) or type(error).__name__)
            return
        self.searched = True
        self.mode = MODE_MULTI if found else MODE_LEGACY
        if self.switch != SW_ON:
            self._say(_SW_KEYS[self.switch], level="warning" if self.switch in (SW_PENDING_ON, SW_PENDING_OFF) else "info")
        self._say("NP_MSG_FOUND" if found else "NP_MSG_LEGACY", count=len(found))

    def tick(self) -> None:
        """Call while the program works: keeps the selection alive and reports a head that stopped being confirmed."""
        with self.lock:
            self.host.tick()
        for lapse in self.host.take_lapses():
            self._say("NP_LAPSE_RELEASED" if lapse.released else "NP_LAPSE_KEPT", level="warning" if lapse.released else "error",
                      node=lapse.node, why=lapse.reason)

    def rows(self) -> list[NodeRow]:
        now = self.host.io.now()
        alive = set(self.host.table.alive(now))
        rows = []
        for address in sorted(self.host.table.nodes):
            record = self.host.table.nodes[address]
            status = classify_node(record.state, record.conflict, address in alive)
            rows.append(NodeRow(address, record.tool, self.tool_namer(record.tool), f"{record.serial:08X}", record.instance, status,
                                self.host.wanted == address and status == ST_SELECTED, status == ST_READY))
        return rows

    # -- choosing ------------------------------------------------------------------------------------------------------------
    def ask(self, node: int) -> bool:
        """The person pressed Select on a row: nothing is sent yet; the program shows ``confirm_text`` and waits for ``confirm``."""
        row = next((r for r in self.rows() if r.address == node), None)
        if row is None or not row.selectable:
            self._say("NP_FAIL_NOT_ANNOUNCED" if row is None else _STATUS_FAIL_KEYS.get(row.status, "NP_FAIL_OTHER"), level="error")
            return False
        self.pending = node
        return True

    def confirm_text_params(self) -> dict:
        row = next((r for r in self.rows() if r.address == self.pending), None)
        if row is None:
            return {}
        return {"node": row.address, "tool": row.tool, "serial": row.serial}

    def cancel(self) -> None:
        self.pending = None

    def confirm(self) -> bool:
        """The person confirmed: select the head and wait until it says it is selected. A failure leaves nothing selected."""
        node, self.pending = self.pending, None
        if node is None:
            return False
        self.in_bootloader_session = False
        try:
            with self.lock:
                self.host.select(node)
        except mh.NodeNotReady as error:
            self._say(strings.fail_key(error.reason), level="error")
            return False
        self._say("NP_MSG_SELECTED", node=node)
        return True

    def release(self) -> None:
        with self.lock:
            self.host.release()
        self.pending = None
        self.in_bootloader_session = False
        self._say("NP_MSG_RELEASED")

    @property
    def selected(self) -> int | None:
        return self.host.wanted

    @property
    def release_on_lapse(self) -> bool:
        return self.host.release_on_lapse

    @release_on_lapse.setter
    def release_on_lapse(self, value: bool) -> None:
        self.host.release_on_lapse = bool(value)

    def gate(self, can_id: int) -> None:
        """Called before a single-head frame goes out. With heads on the bus it must go to the selected, confirmed head: anything else
        raises ``NodeBlocked`` and nothing is sent. The enter-bootloader frame needs the confirmation like any other and, once it
        has gone, the bootloader frames of that head pass (the bootloader is not part of the extension and the head stops reporting
        by design, so the selection is not watched until it is released)."""
        if self.mode != MODE_MULTI:
            return
        if self.in_bootloader_session and can_id in mh.BOOTLOADER_IDS and can_id != p.CAN_ID_ENTER_BOOTLOADER:
            return
        if not self.may_send():
            raise NodeBlocked(strings.text(self.language(), "NP_MSG_NEED_SELECTION"))
        if can_id == p.CAN_ID_ENTER_BOOTLOADER:
            self.in_bootloader_session = True
            self.host.suspend()

    def may_send(self) -> bool:
        """True when the program may send single-head frames now: a bus without the extension, or one head selected and confirmed."""
        if self.mode == MODE_LEGACY or (self.mode == MODE_IDLE and not self.host.table.nodes):
            return True
        return self.host.wanted is not None and self.host.is_confirmed(self.host.wanted)

    # -- saying it -----------------------------------------------------------------------------------------------------------
    def _say(self, key: str, level: str = "info", **params) -> None:
        if key == "NP_LAPSE_RELEASED" or key == "NP_LAPSE_KEPT":
            params["why_key"] = _WHY_KEYS.get(params.get("why", ""), "NP_WHY_LOST")
        self.notices.append(Notice(key, params, level))

    def take_notices(self) -> list[Notice]:
        taken, self.notices = self.notices, []
        return taken

    def render(self, notice: Notice, language: str) -> str:
        params = dict(notice.params)
        if "why_key" in params:
            params["why"] = strings.text(language, params["why_key"])
        return strings.text(language, notice.key, **params)

    def snapshot(self, language: str = "english") -> dict:
        """Everything a window shows, already in the language: ``rows`` with the state text, the switch line and the bus summary."""
        rows = []
        for row in self.rows():
            data = row.as_dict()
            data["status_text"] = strings.text(language, _STATE_KEYS[row.status])
            rows.append(data)
        found = len(rows)
        if self.host.wanted is not None:
            summary = strings.text(language, "NP_BUS_SELECTED", node=self.host.wanted)
        elif found:
            summary = strings.text(language, "NP_BUS_FOUND", count=found)
        else:
            summary = strings.text(language, "NP_BUS_NONE")
        confirm = strings.text(language, "NP_MSG_CONFIRM", **self.confirm_text_params()) if self.pending is not None else ""
        return {
            "mode": self.mode, "searched": self.searched, "switch": self.switch, "switch_text": strings.text(language, _SW_KEYS[self.switch]),
            "rows": rows, "selected": self.host.wanted, "pending": self.pending, "confirm_text": confirm, "summary": summary,
            "release_on_lapse": self.host.release_on_lapse, "may_send": self.may_send(),
        }


class GatedTransport:
    """A transport that asks the picker before every single-head frame; everything else is the transport underneath.

    Over a bus with no heads found (or with one head and no extension) the picker is not in multi-head mode and every frame passes."""

    def __init__(self, transport, picker: NodePicker) -> None:
        self._transport = transport
        self.picker = picker

    def send_frame(self, can_id: int, data: bytes = b"") -> None:
        if p.mn_split_id(can_id) is None:
            self.picker.gate(can_id)
        self._transport.send_frame(can_id, data)

    def __getattr__(self, name: str):
        return getattr(self._transport, name)


def empty_snapshot(language: str = "english") -> dict:
    """What a window shows before any connection: no rows, nothing selected."""
    return {
        "mode": MODE_IDLE, "searched": False, "switch": SW_UNKNOWN, "switch_text": strings.text(language, _SW_KEYS[SW_UNKNOWN]), "rows": [],
        "selected": None, "pending": None, "confirm_text": "", "summary": strings.text(language, "NP_BUS_NONE"), "release_on_lapse": True,
        "may_send": True,
    }


# -- connecting it to something --------------------------------------------------------------------------------------------------
def transport_io(transport, clock: Callable[[], float] = time.monotonic) -> mh.HostIO:
    """A ``HostIO`` over a transport of the programs (``send_frame``, ``read_frame(timeout)``): time passes by listening."""
    inbox: list[tuple[int, int, bytes]] = []

    def now() -> int:
        stamp = getattr(transport, "now_ms", None)
        return int(stamp()) if stamp is not None else int(clock() * 1000)

    def poll() -> list:
        while True:
            frame = transport.read_frame(0.0)
            if frame is None:
                break
            inbox.append((now(), frame[0], bytes(frame[1])))
        taken, inbox[:] = list(inbox), []
        return taken

    def advance(ms: int) -> None:
        frame = transport.read_frame(max(ms, 1) / 1000.0)
        if frame is not None:
            inbox.append((now(), frame[0], bytes(frame[1])))

    return mh.HostIO(send=lambda can_id, data: transport.send_frame(can_id, bytes(data)), poll=poll, now=now, advance=advance)


def config_reader_for(transport, timeout_s: float = 0.5, clock: Callable[[], float] = time.monotonic) -> Callable[[], dict | None]:
    """A function that asks the head for its multinode switch (0x1AD) over a transport and returns the decoded answer, or None."""

    def read() -> dict | None:
        transport.send_frame(*p.encode_multinode_config_resp_request())
        deadline = clock() + timeout_s
        while clock() < deadline:
            frame = transport.read_frame(max(deadline - clock(), 0.001))
            if frame is not None and frame[0] == p.CAN_ID_MULTINODE_CONFIG_RESP:
                return p.decode_multinode_config_resp_response(bytes(frame[1]))
        return None

    return read


class SimTransport:
    """A transport (``send_frame``, ``read_frame``) over the modelled bus, on the clock of the model: listening for a time lets that time pass in the
    model. For tests, pictures and trying a program with several heads and no boards (``now_ms`` is what ``transport_io`` uses as the clock)."""

    def __init__(self, bus) -> None:
        self.bus = bus
        self.sent: list[tuple[int, bytes]] = []
        self._inbox: list[tuple[int, int, bytes]] = []

    def now_ms(self) -> int:
        return int(self.bus.elapsed)

    def open_channel(self, bitrate_code=None, listen_only: bool = False) -> None:
        pass

    def close_channel(self) -> None:
        pass

    def close(self) -> None:
        pass

    def send_frame(self, can_id: int, data: bytes = b"") -> None:
        self.sent.append((can_id, bytes(data)))
        self.bus.host_send(can_id, bytes(data))

    def read_frame(self, timeout: float = 0.05):
        if not self._inbox:
            self._inbox.extend(self.bus.read_host())
        if not self._inbox and timeout > 0:
            self.bus.step(max(1, int(timeout * 1000)))
            self._inbox.extend(self.bus.read_host())
        if not self._inbox:
            return None
        _t, can_id, data = self._inbox.pop(0)
        return can_id, data


def sim_transport(addresses: tuple[int, ...] = (2, 5)):
    """(transport, bus): a transport over a modelled bus with one head per address, already past its listening window."""
    from . import multinode_sim as sim

    bus = sim.SimBus(now_ms=0)
    for address in addresses:
        bus.add(sim.SimNode(address, tool=address % 8, serial=0x1000 + address, start_ms=0))
    bus.step(100)
    return SimTransport(bus), bus


def sim_picker(addresses: tuple[int, ...] = (2, 5), config: dict | None = None, release_on_lapse: bool = True):
    """A picker over a modelled bus (``multinode_sim``) for tests, screenshots and trying a window without boards: (picker, bus)."""
    from . import multinode_sim as sim

    bus = sim.SimBus(now_ms=0)
    for address in addresses:
        bus.add(sim.SimNode(address, tool=address % 8, serial=0x1000 + address, start_ms=0))
    bus.step(100)
    io = mh.HostIO(send=bus.host_send, poll=bus.read_host, now=lambda: bus.elapsed, advance=bus.step)
    host = mh.MultinodeHost(io, release_on_lapse=release_on_lapse)
    return NodePicker(host, config_reader=(lambda: config) if config is not None else None), bus


__all__ = [
    "NodePicker", "NodeRow", "Notice", "NodeBlocked", "GatedTransport", "classify_node", "switch_state", "tool_name", "transport_io", "config_reader_for", "sim_picker", "sim_transport", "SimTransport", "empty_snapshot",
]
