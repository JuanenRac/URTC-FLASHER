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

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import flasher_protocol  # noqa: E402

BENCH_KEY = bytes(range(32))
BENCH_SLAVE_KEY = bytes(range(32, 64))


@pytest.fixture(autouse=True)
def bench_signing_keys(monkeypatch):
    monkeypatch.setattr(flasher_protocol, "HMAC_KEY", BENCH_KEY)
    monkeypatch.setattr(flasher_protocol, "SLAVE_HMAC_KEY", BENCH_SLAVE_KEY)
