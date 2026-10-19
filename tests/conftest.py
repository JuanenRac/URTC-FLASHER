# =============================================================================
# URTC Flasher - tests/conftest.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Most tests flash a synthetic image with no published manifest - in real
use that is a self-built image on a bench board, which needs a signing key
from urtc_config.json. This gives every test such a bench key, so they keep
exercising the protocol; tests/test_firmware_signature.py removes it again
to prove an unsigned image is refused when no key is configured."""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import flasher_config  # noqa: E402
import flasher_protocol  # noqa: E402

BENCH_KEY = bytes(range(32))
BENCH_SLAVE_KEY = bytes(range(32, 64))


@pytest.fixture(autouse=True)
def bench_signing_keys(monkeypatch):
    monkeypatch.setattr(flasher_protocol, "HMAC_KEY", BENCH_KEY)
    monkeypatch.setattr(flasher_protocol, "SLAVE_HMAC_KEY", BENCH_SLAVE_KEY)


# No test may touch the real urtc_config.json (it can hold a signing key): every test gets its own path for it and, at the end of the whole run, the real file must be
# exactly as it was (present or absent, same bytes).
REAL_CONFIG = Path(flasher_config.CONFIG_FILE_PATH)


def _config_state() -> tuple[bool, str | None, bool]:
    digest = hashlib.sha256(REAL_CONFIG.read_bytes()).hexdigest() if REAL_CONFIG.is_file() else None
    return REAL_CONFIG.exists(), digest, Path(str(REAL_CONFIG) + ".tmp").exists()


@pytest.fixture(scope="session", autouse=True)
def the_real_config_is_left_alone():
    before = _config_state()
    yield
    assert _config_state() == before, f"the tests changed the real {REAL_CONFIG}: a test must save its settings through a temporary path"


@pytest.fixture(autouse=True)
def config_goes_to_a_temporary_file(tmp_path, monkeypatch):
    monkeypatch.setattr(flasher_config, "CONFIG_FILE_PATH", str(tmp_path / "urtc_config.json"))
