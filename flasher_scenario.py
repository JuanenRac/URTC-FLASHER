# =============================================================================
# URTC-FLASHER - flasher_scenario.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""An update against the simulated bootloader through a bus scenario, and the evidence it leaves.

``python urtc_flasher.py --cli --transport mock --scenario FILE`` makes the in-memory bootloader (``MockCAN``) sit behind a simulated bus that loses,
repeats, reorders, delays or cuts frames, or goes silent or refuses (``urtc_can/bus_scenario.py``). Off unless asked for; never with a real adapter.

The run lives on a clock of its own (``VirtualTime``): the timeouts of the protocol code count virtual seconds, so a lost frame costs no real waiting and the
same scenario and seed give the same run. That clock is put in place of the ``time`` module of ``flasher_protocol`` only while the update runs.

Whether the update succeeded or failed, the run writes the update report and a ``urtc-evidence/1`` record next to it that says the bus was a simulation, with
the scenario, its seed and what it did. The report is not signed: this run touches no key.
"""
from __future__ import annotations

import contextlib
import json
import os
from collections.abc import Iterator
from typing import Any

import flasher_protocol
from flasher_records import write_update_report
from urtc_can import bus_scenario, evidence

READ_COST_S = 0.001   # the time one read of the simulated bus takes on the virtual clock


class _VirtualTimeModule:
    """What ``flasher_protocol`` uses of the ``time`` module, on a virtual clock."""

    def __init__(self, virtual: bus_scenario.VirtualTime) -> None:
        self.monotonic = virtual.clock
        self.time = virtual.clock
        self.sleep = virtual.sleep


@contextlib.contextmanager
def virtual_clock(virtual: bus_scenario.VirtualTime) -> Iterator[None]:
    """For the length of the block the protocol code reads and sleeps on ``virtual``."""
    saved = flasher_protocol.time
    setattr(flasher_protocol, "time", _VirtualTimeModule(virtual))
    try:
        yield
    finally:
        setattr(flasher_protocol, "time", saved)


def scenario_evidence(report: dict[str, Any], bus: bus_scenario.FaultyBus, note: str = "") -> dict[str, Any]:
    """The update report as a ``urtc-evidence/1`` record that says the bus was a simulation with a scenario."""
    base = evidence.from_update_report(report)
    fields = {key: base[key] for key in ("kind", "outcome", "timestamp_utc", "tool", "tool_version", "operator", "subject", "artifacts") if key in base}
    detail = "; ".join(part for part in (str(report.get("result", "")), note, "SIMULATED bus with a scenario", bus.summary()) if part)
    return evidence.build(**fields, transport={"adapter": f"mock:scenario:{bus.scenario.name}", "bus": "can"}, detail=detail)


def write_scenario_records(report: dict[str, Any], bus: bus_scenario.FaultyBus, folder: str, note: str = "") -> tuple[str, str]:
    """The report and its evidence record, side by side in ``folder``: (report path, evidence path)."""
    report_path = write_update_report(report, folder)
    name = os.path.basename(report_path)
    path = os.path.join(os.path.dirname(report_path), "urtc_evidence_" + name[len("urtc_update_report_"):])
    with open(path, "w", encoding="utf-8") as stream:
        json.dump(scenario_evidence(report, bus, note), stream, indent=2, ensure_ascii=False)
    return report_path, path
