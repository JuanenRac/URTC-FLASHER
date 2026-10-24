# =============================================================================
# URTC Flasher - tests/test_qt_updates.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The "Check for updates" model of the window: conservative defaults, saved options, nothing while a transfer runs, nothing over the network until asked."""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import QCoreApplication  # noqa: E402

import flasher_config  # noqa: E402
import qt_flasher  # noqa: E402
from urtc_can import self_update  # noqa: E402
from urtc_can import update_service  # noqa: E402


@pytest.fixture(scope="module")
def qt_app():
    yield QCoreApplication.instance() or QCoreApplication([])


def test_the_model_starts_idle_with_the_conservative_options(qt_app):
    bridge = qt_flasher.FlasherQtBridge()
    model = bridge.updates
    assert model is bridge.updates
    assert model.state == "idle" and not model.autoCheck and model.requireConfirmation
    service = model.controller.service
    assert service.app == "urtc-flasher" and service.installed == flasher_config.FLASHER_VERSION
    assert service.repo == "JuanenRac/URTC-FLASHER"
    assert service.public_key_hex == update_service.RELEASE_PUBLIC_KEY_HEX


def test_nothing_goes_over_the_network_on_start_unless_the_person_turned_it_on(qt_app, monkeypatch):
    calls = []
    bridge = qt_flasher.FlasherQtBridge()
    bridge.updates.controller.service.fetch = lambda url: calls.append(url)
    bridge.updates.startupCheck()
    assert calls == [] and bridge.updates.state == "idle"


def test_the_options_are_saved_in_the_configuration_file(qt_app, tmp_path):
    bridge = qt_flasher.FlasherQtBridge()
    bridge.updates.setAutoCheck(True)
    bridge.updates.setRequireConfirmation(False)
    saved = flasher_config.load_config()
    assert saved["update_auto_check"] is True and saved["update_require_confirmation"] is False
    again = qt_flasher.FlasherQtBridge()
    assert again.updates.autoCheck and not again.updates.requireConfirmation


def test_an_update_is_refused_while_a_transfer_is_running(qt_app):
    bridge = qt_flasher.FlasherQtBridge()
    service = bridge.updates.controller.service
    assert service.busy() is None
    bridge._busy = True
    assert service.busy() == "CAN-OTA / SWD"
    with pytest.raises(self_update.UpdateError) as caught:
        self_update.install_package(__file__, service.root, _offer(), service.busy())
    assert caught.value.code == "busy"


def test_the_texts_follow_the_language_of_the_program(qt_app, monkeypatch):
    bridge = qt_flasher.FlasherQtBridge()
    monkeypatch.setattr(qt_flasher, "_current_language", "portuguese")
    assert bridge.updates.t("UPD_BTN_CLOSE") == "Fechar"
    monkeypatch.setattr(qt_flasher, "_current_language", "japanese")
    assert bridge.updates.t("UPD_BTN_CLOSE") == "閉じる"


def _offer():
    asset = self_update.Asset("x", "https://github.com/x", 1)
    return self_update.Offer("urtc-flasher", "9.9.9", "windows-x64", "v9.9.9", "", "", asset, asset, asset, "")


def test_the_help_guide_is_the_shared_one_in_the_language_of_the_program(qt_app, monkeypatch):
    bridge = qt_flasher.FlasherQtBridge()
    assert bridge.help is bridge.help
    monkeypatch.setattr(qt_flasher, "_current_language", "spanish")
    assert bridge.help.title == "Ayuda" and len(bridge.help.sections) == 6 and bridge.help.sections[0]["title"] == "Conectar"
    monkeypatch.setattr(qt_flasher, "_current_language", "portuguese")
    assert bridge.help.closeText == "Fechar"
