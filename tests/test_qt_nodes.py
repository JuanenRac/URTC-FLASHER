# =============================================================================
# URTC-FLASHER - tests/test_qt_nodes.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The window of the tool heads in the flasher: the connection is wrapped so a command goes only to the selected head, the states and the lapse
are shown in the language of the program, the option is saved, and the slave application shows its version (with the patch of 0x222)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import QCoreApplication  # noqa: E402

import flasher_config  # noqa: E402
import qt_flasher  # noqa: E402
from urtc_can import node_picker, protocol  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SINGLE_HEAD = 0x120


@pytest.fixture(scope="module")
def qt_app():
    yield QCoreApplication.instance() or QCoreApplication([])


def connected_bridge(addresses):
    bridge = qt_flasher.FlasherQtBridge()
    transport, bus = node_picker.sim_transport(addresses)
    bridge.nodes._sync = True
    bridge._on_connection_result(transport, "")
    return bridge, transport, bus


def test_the_window_exists_once_and_starts_without_a_connection(qt_app):
    bridge = qt_flasher.FlasherQtBridge()
    assert bridge.nodes is bridge.nodes
    assert not bridge.nodes.connected and bridge.nodes.rows == [] and bridge.nodes.releaseOnLapse
    bridge.nodes.stop()


def test_a_connection_is_wrapped_and_a_command_goes_only_to_the_confirmed_head(qt_app):
    bridge, transport, bus = connected_bridge((2, 5))
    assert isinstance(bridge._transport, node_picker.GatedTransport) and bridge.nodes.connected
    bridge._transport.send_frame(SINGLE_HEAD, b"")           # not searched yet: the heads ignore it by themselves
    bridge.nodes.find()
    assert [row["address"] for row in bridge.nodes.rows] == [2, 5] and bridge.nodes.mayShowRows
    with pytest.raises(node_picker.NodeBlocked):
        bridge._transport.send_frame(SINGLE_HEAD, b"")
    bridge.nodes.ask(5)
    assert "5" in bridge.nodes.confirmText and not bridge.nodes.hasSelection
    bridge.nodes.confirm()
    bridge._transport.send_frame(SINGLE_HEAD, b"")
    assert bridge.nodes.selected == 5 and bus.nodes[1].obeyed and not bus.nodes[0].obeyed
    bridge.nodes.stop()


def test_a_bus_with_one_head_and_no_extension_is_sent_to_as_always(qt_app):
    bridge, transport, _bus = connected_bridge(())
    bridge.nodes.find()
    assert bridge.nodes.mode == "legacy" and bridge.nodes.rows == []
    bridge._transport.send_frame(SINGLE_HEAD, b"")
    assert (SINGLE_HEAD, b"") in transport.sent
    bridge.nodes.stop()


def test_closing_the_connection_takes_the_picker_away(qt_app):
    bridge, _transport, _bus = connected_bridge((2,))
    bridge.toggleConnection()
    assert bridge._transport is None and not bridge.nodes.connected
    bridge.nodes.find()
    assert bridge.nodes.messageLevel == "warning"
    bridge.nodes.stop()


def test_the_window_speaks_the_language_of_the_program(qt_app, monkeypatch):
    bridge, _transport, _bus = connected_bridge((2, 5))
    monkeypatch.setattr(qt_flasher, "_current_language", "german")
    bridge.nodes.find()
    assert bridge.nodes.t("NP_BTN_FIND") == "Köpfe suchen" and bridge.nodes.summary == "2 Kopf/Köpfe am Bus"
    assert bridge.nodes.rows[0]["status_text"] == "Bereit"
    bridge.nodes.stop()


def test_a_lost_head_is_reported_and_the_option_is_saved(qt_app):
    bridge, _transport, bus = connected_bridge((2, 5))
    bridge.nodes.find()
    bridge.nodes.ask(2)
    bridge.nodes.confirm()
    bus.nodes[0].enabled = False
    for _ in range((protocol.MN_NODE_TIMEOUT_MS + 300) // 10):
        bus.step(10)
        bridge.nodes._tick()
    assert "safe state" in bridge.nodes.lapseText and not bridge.nodes.hasSelection and bus.safe_state_calls.get(5) == 1
    bridge.nodes.setReleaseOnLapse(False)
    assert flasher_config.load_config()["multinode_release_on_lapse"] is False
    again = qt_flasher.FlasherQtBridge()
    assert again.nodes.releaseOnLapse is False
    again.nodes.setReleaseOnLapse(True)
    bridge.nodes.stop()
    again.nodes.stop()


def test_the_window_keeps_off_the_bus_while_a_transfer_runs(qt_app):
    bridge, _transport, _bus = connected_bridge((2,))
    bridge._busy = True
    bridge.nodes.find()
    assert bridge.nodes.rows == []
    bridge._busy = False
    bridge.nodes.find()
    assert [row["address"] for row in bridge.nodes.rows] == [2]
    bridge.nodes.stop()


class _Scripted:
    def __init__(self, frames):
        self.frames = list(frames)
        self.sent = []

    def send_frame(self, can_id, data=b""):
        self.sent.append((can_id, bytes(data)))

    def read_frame(self, timeout=0.05):
        return self.frames.pop(0) if self.frames else None


def test_the_slave_application_shows_its_version_with_the_patch_of_the_companion_frame(qt_app):
    answer = (protocol.CAN_ID_SLAVE_REG_READ, bytes.fromhex("000303cc01000000"))
    companion = protocol.encode_slave_app_patch(protocol.SLAVE_APP_REG_APP_VERSION, 5)
    transport = _Scripted([answer, companion])
    item = qt_flasher.FlasherQtBridge._slave_application_item(transport)
    assert transport.sent == [(0x221, bytes([1, 8]))]
    assert item["ok"] and item["label"] == "Slave application" and item["value"] == "v0.?.5 / HW 0x0303CC01"
    whole = protocol.encode_slave_app_patch(protocol.SLAVE_APP_REG_APP_VERSION, 4, 2)
    full = qt_flasher.FlasherQtBridge._slave_application_item(_Scripted([answer, whole]))
    assert full["value"] == "v0.2.4 / HW 0x0303CC01"
    old = qt_flasher.FlasherQtBridge._slave_application_item(_Scripted([answer]))
    assert old["value"] == "v0.? / HW 0x0303CC01"
    none = qt_flasher.FlasherQtBridge._slave_application_item(_Scripted([]))
    assert not none["ok"] and none["value"].startswith("No answer")


def test_the_slave_application_line_follows_the_vectors_of_the_shared_code(qt_app):
    vectors = json.loads((FIXTURES / "slave_version_vectors.json").read_text(encoding="utf-8"))
    for case in vectors["cases"]:
        frames = [(can_id, bytes.fromhex(data)) for can_id, data in case["frames"]]
        item = qt_flasher.FlasherQtBridge._slave_application_item(_Scripted(frames))
        if case["expected"] is None:
            assert not item["ok"], case["name"]
        else:
            assert item["ok"] and f"v{case['text']} " in item["value"], case["name"]
