# =============================================================================
# URTC-COMMON - src/urtc_common/bus_scenario.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Scenarios for a simulated CAN bus: the faults a real bus has, written in a file and replayed the same way every time.

A scenario (``urtc-scenario/1``, a JSON file, described in ``docs/BUS_SCENARIOS.md``) is a list of fault rules. ``FaultyBus`` wraps any simulated
transport (the in-memory bootloader of the flasher, the simulated head of the tester, the virtual board) and applies the rules to the frames that go
to the node (``tx``) and to the frames that come back (``rx``):

* the frame faults: ``drop``, ``duplicate``, ``reorder``, ``delay``, ``burst_loss`` and ``truncate`` (a frame shorter than its minimum length);
* the node faults: ``mute`` (the node does not answer), ``reject`` (the node refuses a command and says why, with the reason codes of the rack) and
  ``free_tool`` (a head whose ID jumpers read ``0x1F``: what it answers to ``0x1A3`` and ``0x1A2``).

Nothing is random in the sense of "different every time": every choice comes from one generator seeded by the scenario, so the same scenario
and the same seed give the same frames in the same order. ``generate`` makes a scenario from a seed and a list of fault kinds, again the same
every time. A scenario can only take frames away, repeat them, move them, shorten them, or make the node refuse or stay silent: it cannot make a
node say that something worked. ``FaultyBus`` is a bus for a simulator; the programs refuse to apply a scenario to a real adapter.

Everything is checked before it runs and anything that is not understood is refused (an unknown field, a value out of range, a duplicated key,
a wrong type): no rule is guessed. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

FORMAT = "urtc-scenario/1"
MAX_FILE_BYTES = 65536
MAX_RULES = 64
MAX_EVENTS = 20000
MAX_PULLS = 256            # frames pulled from the node in one read before giving up (a rule set that drops everything must not spin)
SEED_MAX = 0xFFFFFFFF
NAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}")

KINDS = ("drop", "duplicate", "reorder", "delay", "burst_loss", "truncate", "mute", "reject", "free_tool")
FRAME_KINDS = ("drop", "duplicate", "reorder", "delay", "burst_loss", "truncate", "mute")
NODE_KINDS = ("reject", "free_tool")
DIRECTIONS = ("tx", "rx", "both")
FREE_TOOL_ANSWERS = ("valid", "unset", "foreign", "out_of_range", "short", "silent")

# The reason codes of the rack (rack_sim.REPLY_CODES, a test compares the two) and the frame of a refusal: command answered, tool byte, reason code.
REPLY_CODES = ("applied", "repeat", "wrong_length", "tool_absent", "temp_out_of_range", "tool_invalid", "not_heatable", "held_rate", "unknown_command")
REFUSAL_REASONS = REPLY_CODES[2:]
CMD_SET_PREHEAT = 0x01
CAN_ID_SET_PREHEAT = 0x260
CAN_ID_REPLY = 0x261  # the standard identifier of the reply of the rack (rack_sim.CAN_ID_REPLY): the default of ``reject``
CAN_ID_SET_FREE_TOOL = 0x1A2
CAN_ID_FREE_TOOL_QUERY = 0x1A3
FREE_TOOL_JUMPER = 0x1F
TOOL_LAST = 24

Frame = tuple[int, bytes]

COMMON_FIELDS = {"fault", "direction", "id", "from", "count", "per_mille"}
KIND_FIELDS: dict[str, set[str]] = {
    "drop": set(),
    "duplicate": {"copies"},
    "reorder": {"window"},
    "delay": {"ms", "min_ms", "max_ms"},
    "burst_loss": {"length", "period"},
    "truncate": {"dlc"},
    "mute": set(),
    "reject": {"reason", "reply_id", "cmd", "deliver"},
    "free_tool": {"answer", "tool", "selection", "jumper", "answer_to_write", "deliver"},
}
# Fields a kind does not take from the common ones.
FORBIDDEN_COMMON = {"burst_loss": {"per_mille", "count"}, "mute": {"per_mille"}, "reject": {"direction"}, "free_tool": {"direction", "id"}}


class ScenarioError(ValueError):
    """A scenario that cannot be run; the text lists everything that is wrong with it."""


def _int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def parse_id(value: Any) -> int | None:
    """A CAN identifier given as a number, as ``"0x1A3"`` or as decimal text; None when it is none (11 bits only)."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        number = value
    elif isinstance(value, str) and re.fullmatch(r"(0[xX][0-9A-Fa-f]{1,3}|\d{1,4})", value.strip()):
        number = int(value.strip(), 0)
    else:
        return None
    return number if 0 <= number <= 0x7FF else None


def _ids(value: Any) -> list[int] | None:
    items = value if isinstance(value, list) else [value]
    if not 1 <= len(items) <= 16:
        return None
    parsed = [parse_id(item) for item in items]
    return None if any(item is None for item in parsed) else [int(item) for item in parsed if item is not None]


def _range(rule: dict, key: str, low: int, high: int, where: str, problems: list[str], required: bool = False) -> None:
    if key not in rule:
        if required:
            problems.append(f"{where}: {key} is required")
        return
    if not _int(rule[key]) or not low <= rule[key] <= high:
        problems.append(f"{where}: {key} must be a whole number from {low} to {high}")


def validate(doc: Any) -> list[str]:
    """Everything that is wrong with a scenario document; an empty list means it can be run."""
    if not isinstance(doc, dict):
        return ["a scenario is a JSON object"]
    problems: list[str] = []
    unknown = set(doc) - {"format", "name", "description", "seed", "faults"}
    if unknown:
        problems.append("unknown scenario fields: " + ", ".join(sorted(map(str, unknown))))
    if doc.get("format") != FORMAT:
        problems.append(f"format must be {FORMAT!r}")
    if not isinstance(doc.get("name"), str) or not NAME_PATTERN.fullmatch(doc["name"]):
        problems.append("name must be 1 to 64 letters, digits, '.', '_' or '-'")
    if "description" in doc and (not isinstance(doc["description"], str) or len(doc["description"]) > 300):
        problems.append("description must be text of at most 300 characters")
    if "seed" in doc and (not _int(doc["seed"]) or not 0 <= doc["seed"] <= SEED_MAX):
        problems.append(f"seed must be a whole number from 0 to {SEED_MAX}")
    rules = doc.get("faults")
    if not isinstance(rules, list) or len(rules) > MAX_RULES:
        problems.append(f"faults must be a list of at most {MAX_RULES} rules (it may be empty)")
        return problems
    for number, rule in enumerate(rules, start=1):
        problems += _validate_rule(f"fault {number}", rule)
    return problems


def _validate_rule(where: str, rule: Any) -> list[str]:
    if not isinstance(rule, dict):
        return [f"{where}: must be an object"]
    kind = rule.get("fault")
    if kind not in KINDS:
        return [f"{where}: unknown fault {kind!r}"]
    problems: list[str] = []
    allowed = (COMMON_FIELDS - FORBIDDEN_COMMON.get(kind, set())) | KIND_FIELDS[kind]
    unknown = set(rule) - allowed
    if unknown:
        problems.append(f"{where} ({kind}): fields not allowed here: {', '.join(sorted(map(str, unknown)))}")
    if "direction" in rule and rule["direction"] not in DIRECTIONS:
        problems.append(f"{where}: direction must be one of {DIRECTIONS}")
    if "id" in rule and _ids(rule["id"]) is None:
        problems.append(f"{where}: id must be a CAN identifier (0 to 0x7FF) or a list of up to 16")
    _range(rule, "from", 0, 1_000_000, where, problems)
    _range(rule, "count", 1, 1_000_000, where, problems)
    _range(rule, "per_mille", 1, 1000, where, problems)
    if kind == "duplicate":
        _range(rule, "copies", 1, 3, where, problems)
    elif kind == "reorder":
        _range(rule, "window", 2, 8, where, problems)
    elif kind == "delay":
        fixed, low, high = "ms" in rule, "min_ms" in rule, "max_ms" in rule
        if fixed == (low or high):
            problems.append(f"{where}: give either ms, or both min_ms and max_ms")
        if low != high:
            problems.append(f"{where}: min_ms and max_ms go together")
        for key in ("ms", "min_ms", "max_ms"):
            _range(rule, key, 1, 60000, where, problems)
        if low and high and _int(rule["min_ms"]) and _int(rule["max_ms"]) and rule["min_ms"] > rule["max_ms"]:
            problems.append(f"{where}: min_ms is greater than max_ms")
    elif kind == "burst_loss":
        _range(rule, "length", 1, 64, where, problems, required=True)
        _range(rule, "period", 2, 100_000, where, problems)
        if _int(rule.get("length")) and _int(rule.get("period")) and rule["period"] <= rule["length"]:
            problems.append(f"{where}: period must be greater than length")
    elif kind == "truncate":
        _range(rule, "dlc", 0, 7, where, problems, required=True)
    elif kind == "reject":
        if "id" not in rule:
            problems.append(f"{where}: reject needs the id of the command it refuses")
        if rule.get("reason") not in REFUSAL_REASONS:
            problems.append(f"{where}: reason must be one of {REFUSAL_REASONS}")
        if "reply_id" in rule and parse_id(rule["reply_id"]) is None:
            problems.append(f"{where}: reply_id must be the CAN identifier the refusal is sent with (omit it for the standard reply identifier 0x{CAN_ID_REPLY:03X})")
        _range(rule, "cmd", 0, 255, where, problems)
        if "deliver" in rule and not isinstance(rule["deliver"], bool):
            problems.append(f"{where}: deliver must be true or false")
    elif kind == "free_tool":
        answer = rule.get("answer")
        if answer not in FREE_TOOL_ANSWERS:
            problems.append(f"{where}: answer must be one of {FREE_TOOL_ANSWERS}")
        if answer == "valid":
            _range(rule, "tool", 0, TOOL_LAST, where, problems, required=True)
        elif "tool" in rule:
            problems.append(f"{where}: tool goes only with answer valid")
        if answer == "out_of_range":
            _range(rule, "selection", 26, 255, where, problems)
        elif "selection" in rule:
            problems.append(f"{where}: selection goes only with answer out_of_range")
        if answer == "foreign":
            _range(rule, "jumper", 0, 30, where, problems)
        elif "jumper" in rule:
            problems.append(f"{where}: jumper goes only with answer foreign")
        for key in ("answer_to_write", "deliver"):
            if key in rule and not isinstance(rule[key], bool):
                problems.append(f"{where}: {key} must be true or false")
    if kind in NODE_KINDS and rule.get("direction", "tx") != "tx":
        problems.append(f"{where}: {kind} acts on the frames sent to the node")
    return problems


@dataclass(frozen=True)
class Scenario:
    name: str
    description: str
    seed: int
    faults: tuple[dict, ...]

    def as_dict(self) -> dict:
        doc: dict[str, Any] = {"format": FORMAT, "name": self.name}
        if self.description:
            doc["description"] = self.description
        doc["seed"] = self.seed
        doc["faults"] = [dict(rule) for rule in self.faults]
        return doc

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), indent=2, sort_keys=True) + "\n"


def from_dict(doc: Any) -> Scenario:
    problems = validate(doc)
    if problems:
        raise ScenarioError("the scenario is not valid: " + "; ".join(problems))
    return Scenario(doc["name"], doc.get("description", ""), doc.get("seed", 0), tuple(dict(rule) for rule in doc["faults"]))


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict:
    keys = [key for key, _ in pairs]
    if len(set(keys)) != len(keys):
        raise ScenarioError("a key is written twice in the file")
    return dict(pairs)


def _no_constant(name: str) -> Any:
    raise ScenarioError(f"{name} is not a number a scenario can hold")


def parse(text: str) -> Scenario:
    """A scenario from its JSON text. Anything wrong raises ``ScenarioError``."""
    if len(text.encode("utf-8")) > MAX_FILE_BYTES:
        raise ScenarioError(f"the scenario is larger than {MAX_FILE_BYTES} bytes")
    try:
        doc = json.loads(text, object_pairs_hook=_no_duplicates, parse_constant=_no_constant)
    except json.JSONDecodeError as exc:
        raise ScenarioError(f"the scenario is not JSON: {exc}") from exc
    return from_dict(doc)


def load(path: str | Path) -> Scenario:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ScenarioError(f"cannot read the scenario {path}: {exc}") from exc
    return parse(text)


# ---------------------------------------------------------------------------------------------------------------------
# the faulty bus
# ---------------------------------------------------------------------------------------------------------------------
@dataclass
class _Item:
    can_id: int
    data: bytes
    delay_s: float = 0.0


@dataclass
class _RuleState:
    rule: dict
    ids: frozenset[int] | None
    matched: dict[str, int] = field(default_factory=lambda: {"tx": 0, "rx": 0})
    buffer: dict[str, list[_Item]] = field(default_factory=lambda: {"tx": [], "rx": []})
    free: dict[str, Any] = field(default_factory=dict)


class VirtualTime:
    """A clock that only moves when something sleeps or reads. Passed to a program (its clock and sleep) and to the bus, a whole run takes no real
    time and its timing is the same every time, so the same scenario and seed give the same frames even for a program that waits on a clock."""

    def __init__(self, start: float = 1000.0) -> None:
        self.now = float(start)

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += max(0.0, seconds)


class FaultyBus:
    """A transport (``open_channel``, ``close_channel``, ``close``, ``send_frame``, ``read_frame``) that applies a scenario to another one.

    ``inner`` is a simulated node. ``clock`` and ``sleep`` are the ones of the program that uses the bus (a test passes a fake pair): a delayed
    frame is released when the clock reaches its time, and a read that finds only delayed frames waits for the first of them, up to its timeout.
    ``read_cost_s`` is the time each read of the node takes (slept with ``sleep``): with a ``VirtualTime`` it is what makes time pass while a program polls.
    ``events`` is the list of what the scenario did, in order (``"tx drop 0x110"``); ``stats`` counts it by kind.
    """

    def __init__(self, inner: Any, scenario: Scenario, *, seed: int | None = None, clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep, read_cost_s: float = 0.0) -> None:
        self.inner = inner
        self.read_cost_s = read_cost_s
        self.scenario = scenario
        self.seed = scenario.seed if seed is None else seed
        if not _int(self.seed) or not 0 <= self.seed <= SEED_MAX:
            raise ScenarioError(f"seed must be a whole number from 0 to {SEED_MAX}")
        self.clock = clock
        self.sleep = sleep
        self.rng = random.Random(self.seed)
        self.events: list[str] = []
        self.stats: Counter[str] = Counter()
        self._states: list[_RuleState] = []
        for rule in scenario.faults:
            ids = frozenset(_ids(rule["id"]) or []) if "id" in rule else None
            state = _RuleState(rule, ids)
            if rule["fault"] == "free_tool":
                state.free = {"answer": rule["answer"], "tool": rule.get("tool"), "selection": rule.get("selection", 26),
                              "jumper": rule.get("jumper", 0), "pending": None}
            self._states.append(state)
        self._sequence = 0
        self._rx_pending: list[tuple[float, int, Frame]] = []
        self._tx_pending: list[tuple[float, int, Frame]] = []

    # -- the interface of the transports -----------------------------------------------------------------------------
    def open_channel(self, *args: Any, **kwargs: Any) -> None:
        self.inner.open_channel(*args, **kwargs)

    def close_channel(self) -> None:
        self.inner.close_channel()

    def close(self) -> None:
        self.inner.close()

    def send_frame(self, can_id: int, data: bytes = b"") -> None:
        self._release_tx()
        for item in self._apply("tx", [_Item(can_id, bytes(data))], 0):
            self._schedule("tx", item)
        self._release_tx()

    def read_frame(self, timeout: float = 0.05) -> Frame | None:
        deadline = self.clock() + max(0.0, timeout)
        for attempt in range(MAX_PULLS):
            self._release_tx()
            ready = self._pop_ready()
            if ready is not None:
                return ready
            if attempt and self.clock() >= deadline:
                break
            frame = self.inner.read_frame(max(0.0, deadline - self.clock()))
            if self.read_cost_s > 0:
                self.sleep(self.read_cost_s)
            if frame is not None:
                for item in self._apply("rx", [_Item(frame[0], bytes(frame[1]))], 0):
                    self._schedule("rx", item)
                continue
            # nothing from the node: wait for the first delayed frame if one is due before the deadline
            due = self._next_due()
            now = self.clock()
            if due is None and any(state.buffer[d] for state in self._states for d in ("tx", "rx")):
                self.flush()    # a reorder window that did not fill while the program waits is released as it is
                continue
            if due is None or due > deadline:
                break
            if due > now:
                self.sleep(due - now)
        self._release_tx()
        return self._pop_ready()

    # -- control the scenario may need ---------------------------------------------------------------------------------
    def power_cycle(self) -> None:
        """The node restarts: a selection written to a free-configuration head with ``0x1A2`` is what it answers from now on."""
        for state in self._states:
            if state.rule["fault"] != "free_tool" or state.free["pending"] is None:
                continue
            selection = state.free["pending"]
            state.free["pending"] = None
            if selection == 0:
                state.free.update(answer="unset", tool=None)
            else:
                state.free.update(answer="valid", tool=selection - 1)
            self._note("power", "free_tool", None)

    def flush(self) -> None:
        """Release what a ``reorder`` rule still holds (a window that never filled), as it is."""
        for index, state in enumerate(self._states):
            for direction in ("tx", "rx"):
                if state.buffer[direction]:
                    held, state.buffer[direction] = state.buffer[direction], []
                    for item in self._apply(direction, held, index + 1):
                        self._schedule(direction, item)

    def summary(self) -> str:
        """One line for a record: the name, the seed and what the scenario did."""
        done = ", ".join(f"{key} {self.stats[key]}" for key in sorted(self.stats)) or "nothing"
        return f"scenario {self.scenario.name} seed {self.seed}: {done}"

    # -- inside --------------------------------------------------------------------------------------------------------
    def _note(self, direction: str, kind: str, can_id: int | None) -> None:
        self.stats[kind] += 1
        if len(self.events) < MAX_EVENTS:
            self.events.append(f"{direction} {kind}" + (f" 0x{can_id:03X}" if can_id is not None else ""))

    def _schedule(self, direction: str, item: _Item) -> None:
        self._sequence += 1
        entry = (self.clock() + item.delay_s, self._sequence, (item.can_id, item.data))
        (self._rx_pending if direction == "rx" else self._tx_pending).append(entry)

    def _release_tx(self) -> None:
        now = self.clock()
        due = sorted(entry for entry in self._tx_pending if entry[0] <= now)
        if not due:
            return
        self._tx_pending = [entry for entry in self._tx_pending if entry[0] > now]
        for _, _, (can_id, data) in due:
            self.inner.send_frame(can_id, data)

    def _pop_ready(self) -> Frame | None:
        now = self.clock()
        due = [entry for entry in self._rx_pending if entry[0] <= now]
        if not due:
            return None
        first = min(due)
        self._rx_pending.remove(first)
        return first[2]

    def _next_due(self) -> float | None:
        times = [entry[0] for entry in self._rx_pending + self._tx_pending]
        return min(times) if times else None

    def _active(self, state: _RuleState, direction: str, can_id: int) -> bool:
        rule = state.rule
        if rule.get("direction", "both") not in (direction, "both"):
            return False
        if rule["fault"] in NODE_KINDS and direction != "tx":
            return False
        ids = state.ids
        if rule["fault"] == "free_tool":
            ids = frozenset({CAN_ID_SET_FREE_TOOL, CAN_ID_FREE_TOOL_QUERY})
        if ids is not None and can_id not in ids:
            return False
        index = state.matched[direction]
        state.matched[direction] += 1
        start = rule.get("from", 0)
        if index < start or ("count" in rule and index >= start + rule["count"]):
            return False
        if rule.get("per_mille", 1000) < 1000 and self.rng.randrange(1000) >= rule["per_mille"]:
            return False
        return True

    def _apply(self, direction: str, items: list[_Item], first: int) -> list[_Item]:
        for index in range(first, len(self._states)):
            state = self._states[index]
            out: list[_Item] = []
            for item in items:
                out += self._one(index, state, direction, item)
            items = out
            if not items:
                break
        return items

    def _one(self, index: int, state: _RuleState, direction: str, item: _Item) -> list[_Item]:
        rule = state.rule
        kind = rule["fault"]
        matches_before = state.matched[direction]
        if not self._active(state, direction, item.can_id):
            return [item]
        position = matches_before - rule.get("from", 0)
        if kind == "drop" or kind == "mute":
            self._note(direction, kind, item.can_id)
            return []
        if kind == "burst_loss":
            period = rule.get("period")
            inside = position % period if period else position
            if inside < rule["length"]:
                self._note(direction, kind, item.can_id)
                return []
            return [item]
        if kind == "duplicate":
            self._note(direction, kind, item.can_id)
            return [item] + [_Item(item.can_id, item.data, item.delay_s) for _ in range(rule.get("copies", 1))]
        if kind == "truncate":
            if len(item.data) > rule["dlc"]:
                self._note(direction, kind, item.can_id)
                return [_Item(item.can_id, item.data[:rule["dlc"]], item.delay_s)]
            return [item]
        if kind == "delay":
            ms = rule["ms"] if "ms" in rule else self.rng.randrange(rule["min_ms"], rule["max_ms"] + 1)
            self._note(direction, kind, item.can_id)
            return [_Item(item.can_id, item.data, item.delay_s + ms / 1000.0)]
        if kind == "reorder":
            state.buffer[direction].append(item)
            if len(state.buffer[direction]) < rule.get("window", 2):
                return []
            held, state.buffer[direction] = state.buffer[direction], []
            order = self.rng.sample(range(len(held)), len(held))
            self._note(direction, kind, None)
            return [held[i] for i in order]
        if kind == "reject":
            self._note(direction, kind, item.can_id)
            tool = item.data[0] if item.data else 0xFF
            code = REPLY_CODES.index(rule["reason"])
            self._inject(_Item(int(parse_id(rule["reply_id"]) or 0) if "reply_id" in rule else CAN_ID_REPLY, bytes([rule.get("cmd", CMD_SET_PREHEAT), tool, code])))
            return [item] if rule.get("deliver", False) else []
        if kind == "free_tool":
            self._free_tool(state, item)
            return [item] if rule.get("deliver", False) else []
        return [item]

    def _inject(self, item: _Item) -> None:
        for out in self._apply("rx", [item], 0):
            self._schedule("rx", out)

    def _free_tool(self, state: _RuleState, item: _Item) -> None:
        rule, free = state.rule, state.free
        if item.can_id == CAN_ID_SET_FREE_TOOL:
            self._note("tx", "free_tool_write", item.can_id)
            if item.data and item.data[0] <= TOOL_LAST + 1:
                free["pending"] = item.data[0]      # reaches the answer after the next power cycle of the head
            if not rule.get("answer_to_write", True):
                return
        else:
            self._note("tx", "free_tool_query", item.can_id)
        answer = free["answer"]
        if answer == "silent":
            return
        if answer == "valid":
            data = bytes([FREE_TOOL_JUMPER, int(free["tool"]) + 1])
        elif answer == "unset":
            data = bytes([FREE_TOOL_JUMPER, 0])
        elif answer == "foreign":
            data = bytes([int(free["jumper"]), 1])
        elif answer == "out_of_range":
            data = bytes([FREE_TOOL_JUMPER, int(free["selection"])])
        else:   # short: one byte, below the two the answer needs
            data = bytes([FREE_TOOL_JUMPER])
        self._inject(_Item(CAN_ID_FREE_TOOL_QUERY, data))


# ---------------------------------------------------------------------------------------------------------------------
# the generator
# ---------------------------------------------------------------------------------------------------------------------
GENERATED_KINDS = ("drop", "duplicate", "reorder", "delay", "burst_loss", "truncate", "mute")   # none of them can make a node say something it did not
NODE_PROFILES = ("reject", "free_tool")
SAFE_FREE_ANSWERS = tuple(answer for answer in FREE_TOOL_ANSWERS if answer != "valid")
DEFAULT_IDS = (0x110, 0x111, 0x7F8, 0x7F9, 0x1A3, 0x260)


def _rule_for(rng: random.Random, kind: str, ids: tuple[int, ...], reply_id: int | None) -> dict:
    rule: dict[str, Any] = {"fault": kind}
    if kind == "drop":
        rule["per_mille"] = rng.choice((50, 100, 250, 500))
    elif kind == "duplicate":
        rule.update(copies=rng.randint(1, 2), per_mille=rng.choice((100, 300, 1000)))
    elif kind == "reorder":
        rule["window"] = rng.randint(2, 4)
    elif kind == "delay":
        low = rng.choice((1, 5, 20))
        rule.update(min_ms=low, max_ms=low + rng.choice((5, 20, 80)))
    elif kind == "burst_loss":
        length = rng.randint(1, 6)
        rule.update(length=length, period=length + rng.randint(1, 12), **{"from": rng.randint(0, 5)})
    elif kind == "truncate":
        rule.update(dlc=rng.randint(0, 7), per_mille=rng.choice((100, 500, 1000)))
    elif kind == "mute":
        rule.update(**{"from": rng.randint(0, 8)}, count=rng.randint(1, 20))
    elif kind == "reject":
        rule.update(id=rng.choice((CAN_ID_SET_PREHEAT, 0x110)), reason=rng.choice(REFUSAL_REASONS))
        if reply_id is not None and reply_id != CAN_ID_REPLY:
            rule["reply_id"] = reply_id   # the standard identifier is the default of the rule and is not written
    elif kind == "free_tool":
        answer = rng.choice(SAFE_FREE_ANSWERS)
        rule["answer"] = answer
        if answer == "foreign":
            rule["jumper"] = rng.randint(0, 30)
        if answer == "out_of_range":
            rule["selection"] = rng.randint(26, 255)
    if kind in FRAME_KINDS:
        rule["direction"] = rng.choice(DIRECTIONS)
    if kind in ("drop", "duplicate", "delay", "truncate") and rng.randint(0, 2) == 0:
        rule["id"] = rng.choice(ids)
    return rule


def generate(seed: int, *, kinds: tuple[str, ...] = GENERATED_KINDS, rules: int | None = None, ids: tuple[int, ...] = DEFAULT_IDS,
             reply_id: int | None = None) -> Scenario:
    """A scenario made from ``seed``: the same seed and the same arguments give the same scenario. It combines 1 to 4 rules (or ``rules``) of the
    kinds given. ``reject`` and ``free_tool`` may be asked for; a free-tool head never answers with a valid tool in a generated scenario."""
    if not _int(seed) or not 0 <= seed <= SEED_MAX:
        raise ScenarioError(f"seed must be a whole number from 0 to {SEED_MAX}")
    allowed = GENERATED_KINDS + NODE_PROFILES
    if not kinds or any(kind not in allowed for kind in kinds):
        raise ScenarioError(f"kinds must be some of {allowed}")
    rng = random.Random(seed)
    count = rules if rules is not None else rng.randint(1, 4)
    if not _int(count) or not 1 <= count <= 16:
        raise ScenarioError("rules must be a whole number from 1 to 16")
    chosen = [_rule_for(rng, rng.choice(kinds), ids, reply_id) for _ in range(count)]
    scenario = from_dict({"format": FORMAT, "name": f"generated-{seed}", "description": "made by the generator from its seed",
                          "seed": seed, "faults": chosen})
    return scenario


def generate_suite(seed: int, count: int, *, kinds: tuple[str, ...] = GENERATED_KINDS) -> list[Scenario]:
    """``count`` scenarios; the seed of each one comes from ``seed`` in order, so the suite is the same every time."""
    if not _int(count) or not 1 <= count <= 1000:
        raise ScenarioError("count must be a whole number from 1 to 1000")
    rng = random.Random(seed)
    return [generate(rng.randrange(SEED_MAX + 1), kinds=kinds) for _ in range(count)]


# ---------------------------------------------------------------------------------------------------------------------
# command line
# ---------------------------------------------------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bus_scenario", description="Check or generate the scenarios of a simulated CAN bus (urtc-scenario/1).")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("validate", help="check a scenario file; exit 0 if it can be run, 1 if not")
    check.add_argument("file")
    make = sub.add_parser("generate", help="write generated scenarios (the same seed gives the same files)")
    make.add_argument("--seed", type=int, required=True)
    make.add_argument("--count", type=int, default=1)
    make.add_argument("--kinds", default=",".join(GENERATED_KINDS), help="comma separated: " + ", ".join(GENERATED_KINDS + NODE_PROFILES))
    make.add_argument("--out", help="folder for the files; without it the first scenario is printed")
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            scenario = load(args.file)
            print(f"valid: {scenario.name}, {len(scenario.faults)} rule(s), seed {scenario.seed}")
            return 0
        kinds = tuple(item.strip() for item in args.kinds.split(",") if item.strip())
        suite = generate_suite(args.seed, args.count, kinds=kinds)
        if not args.out:
            print(suite[0].to_json(), end="")
            return 0
        folder = Path(args.out)
        folder.mkdir(parents=True, exist_ok=True)
        for scenario in suite:
            (folder / f"{scenario.name}.json").write_text(scenario.to_json(), encoding="utf-8", newline="\n")
        print(f"wrote {len(suite)} scenario(s) to {folder}")
        return 0
    except ScenarioError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
