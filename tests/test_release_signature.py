# =============================================================================
# URTC-FLASHER - tests/test_release_signature.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The release signature of an image: the pinned key, the verifier and the pre-flash decision."""
import hashlib
import re
from pathlib import Path

import pytest

import flasher_integrity
import flasher_release_signature as sig

ROOT = Path(__file__).resolve().parent.parent
RFC_PUBLIC = bytes.fromhex("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
RFC_SIGNATURE = bytes.fromhex(
    "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b")

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
except ImportError:
    Ed25519PrivateKey = None


def test_the_rfc_vector_verifies_and_tampering_does_not():
    assert sig.ed25519_verify(RFC_PUBLIC, b"", RFC_SIGNATURE)
    assert not sig.ed25519_verify(RFC_PUBLIC, b"x", RFC_SIGNATURE)
    assert not sig.ed25519_verify(RFC_PUBLIC, b"", RFC_SIGNATURE[:-1] + b"\x00")
    assert not sig.ed25519_verify(RFC_PUBLIC[:-1], b"", RFC_SIGNATURE)


def test_the_pinned_key_is_the_one_published_in_the_firmware_repository():
    published = ROOT.parent / "URTC" / "docs" / "RELEASE_SIGNING.md"
    if not published.is_file():
        pytest.skip("the URTC repository is not next to this one")
    assert re.search(r"ed25519 ([0-9a-f]{64})", published.read_text(encoding="utf-8")).group(1) == sig.PUBLIC_KEY_HEX


@pytest.fixture
def signed_image(tmp_path, monkeypatch):
    if Ed25519PrivateKey is None:
        pytest.skip("cryptography is not installed")
    key = Ed25519PrivateKey.generate()
    monkeypatch.setattr(sig, "PUBLIC_KEY_HEX", key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex())
    image = tmp_path / "URTC_MAIN_FIRMWARE_v1.0.0.bin"
    image.write_bytes(b"firmware" * 20)
    digest = hashlib.sha256(image.read_bytes()).hexdigest()
    (tmp_path / (image.name + ".sha256")).write_text(f"{digest}  {image.name}\n", encoding="utf-8")
    Path(str(image) + ".sig").write_text(key.sign(sig.release_message(image.name, digest)).hex() + "\n", encoding="ascii")
    return image


def test_a_signed_image_is_verified(signed_image):
    check = flasher_integrity.preflight_image(str(signed_image))
    assert (check.blocked, check.verified, check.release_signature) == (False, True, "signed")


def test_a_changed_or_renamed_image_is_blocked(signed_image):
    renamed = signed_image.with_name("URTC_MAIN_FIRMWARE_v1.0.1.bin")
    renamed.write_bytes(signed_image.read_bytes())
    renamed.with_name(renamed.name + ".sig").write_text(Path(str(signed_image) + ".sig").read_text(), encoding="ascii")
    check = flasher_integrity.preflight_image(str(renamed))
    assert check.blocked and check.release_signature == "invalid"


def test_an_unsigned_image_passes_during_the_transition_and_is_blocked_after(signed_image, monkeypatch):
    Path(str(signed_image) + ".sig").unlink()
    check = flasher_integrity.preflight_image(str(signed_image))
    assert (check.blocked, check.release_signature) == (False, "unsigned")
    monkeypatch.setattr(sig, "REQUIRE_RELEASE_SIGNATURE", True)
    check = flasher_integrity.preflight_image(str(signed_image))
    assert check.blocked and "no release signature" in check.reasons[0]


def test_garbage_in_the_signature_file_is_invalid_not_a_crash(signed_image):
    Path(str(signed_image) + ".sig").write_text("zz", encoding="ascii")
    assert flasher_integrity.preflight_image(str(signed_image)).release_signature == "invalid"
