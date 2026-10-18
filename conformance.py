# =============================================================================
# URTC-COMMON - src/urtc_common/conformance.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Run the shared conformance vectors (conformance/can_vectors.json) against this package.

``check_all`` returns one line per vector that this implementation does not reproduce; an empty list means
it reproduces them all. A tool that migrates to this package can run the same function on its own copy of
the vectors, and the same file is what the other implementations (C tests, TypeScript) read.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from . import protocol, quick_state, versioning
from .framing import CanFrame, FrameError
from .slcan import LineReader, decode_line, encode_line

SECTIONS_LEGACY = ("identifiers", "magic_payloads", "slcan_encode", "slcan_encode_rejected", "slcan_decode", "quick_state", "version_query", "minor_field", "version_order")
SECTIONS_GENERATED = ("identifiers_all", "frames_encode", "frames_decode", "frames_rejected", "slcan_stream")
SECTIONS = SECTIONS_LEGACY + SECTIONS_GENERATED
DEFAULT_PATH = Path(__file__).resolve().parents[2] / "conformance" / "can_vectors.json"


def load(path: Path | str = DEFAULT_PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _to_call_fields(layout: str, fields: dict) -> dict:
    """Vector fields to call arguments: the hex string of a bytes field becomes bytes."""
    types = {f["name"]: f["type"] for f in protocol.LAYOUTS[layout]["fields"]}
    return {name: (bytes.fromhex(value) if types[name] == "bytes" and value is not None else value) for name, value in fields.items()}


def _from_result(layout: str, fields: dict | None) -> dict | None:
    if fields is None:
        return None
    types = {f["name"]: f["type"] for f in protocol.LAYOUTS[layout]["fields"]}
    return {name: (value.hex().upper() if types[name] == "bytes" and value is not None else value) for name, value in fields.items()}


def _frame_dict(frame: CanFrame | None) -> dict | None:
    return None if frame is None else {"id": frame.id_hex(), "data": frame.data_hex()}


def _id(text: str) -> int:
    return int(text, 16)


def check_identifiers(vectors: dict) -> list[str]:
    problems = []
    for entry in vectors["identifiers"]:
        if _id(entry["id"]) not in protocol.MESSAGES:
            problems.append(f"identifiers: {entry['id']} is not in the protocol table")
    return problems


def check_identifiers_all(vectors: dict) -> list[str]:
    problems = []
    for entry in vectors["identifiers_all"]:
        value = getattr(protocol, f"CAN_ID_{entry['name']}", None)
        if value != _id(entry["id"]):
            problems.append(f"identifiers_all: CAN_ID_{entry['name']} is {value!r}, the vector says {entry['id']}")
    if len(vectors["identifiers_all"]) != len(protocol.MESSAGES):
        problems.append(f"identifiers_all: {len(vectors['identifiers_all'])} vectors for {len(protocol.MESSAGES)} identifiers")
    return problems


def check_magic_payloads(vectors: dict) -> list[str]:
    problems = []
    for entry in vectors["magic_payloads"]:
        known = protocol.MAGIC_PAYLOADS.get(entry["name"])
        if known is None or known["id"] != _id(entry["id"]) or known["data"] != entry["data"]:
            problems.append(f"magic_payloads: {entry['name']} differs from the protocol")
    if {e["name"] for e in vectors["magic_payloads"]} != set(protocol.MAGIC_PAYLOADS):
        problems.append("magic_payloads: the set of names differs from the protocol")
    return problems


def check_slcan_encode(vectors: dict) -> list[str]:
    problems = []
    for entry in vectors["slcan_encode"]:
        line = encode_line(_id(entry["id"]), bytes.fromhex(entry["data"]))
        if line != entry["line"]:
            problems.append(f"slcan_encode: {entry['id']} {entry['data']} gives {line!r}, expected {entry['line']!r}")
    for entry in vectors["slcan_encode_rejected"]:
        try:
            encode_line(_id(entry["id"]), bytes.fromhex(entry["data"]))
        except FrameError:
            continue
        problems.append(f"slcan_encode_rejected: {entry['id']} {entry['data']} was accepted")
    return problems


def check_slcan_decode(vectors: dict) -> list[str]:
    problems = []
    for entry in vectors["slcan_decode"]:
        if "note" in entry:
            continue  # the readers are allowed to differ here
        got = _frame_dict(decode_line(entry["line"]))
        expected = entry["frame"]
        if expected is not None:
            expected = {"id": expected["id"].upper().replace("0X", "0x"), "data": expected["data"]}
        if got != expected:
            problems.append(f"slcan_decode: {entry['name']}: got {got}, expected {expected}")
    return problems


def check_quick_state(vectors: dict) -> list[str]:
    problems = []
    for entry in vectors["quick_state"]:
        got = quick_state.decode(bytes.fromhex(entry["data"]))
        expected = entry["expect"]
        if expected is None:
            if got is not None:
                problems.append(f"quick_state: {entry['name']}: expected no answer, got {got}")
            continue
        if got is None or any(got.get(key) != value for key, value in expected.items()):
            problems.append(f"quick_state: {entry['name']}: got {got}, expected {expected}")
    return problems


def check_version_query(vectors: dict) -> list[str]:
    problems = []
    for entry in vectors["version_query"]:
        frames = [(_id(i), bytes.fromhex(d)) for i, d in entry["frames"]]
        got = versioning.parse_version_answer(frames)
        expected = entry["expect"]
        if expected is None:
            if got is not None:
                problems.append(f"version_query: {entry['name']}: expected no answer, got {got}")
            continue
        if got is None:
            problems.append(f"version_query: {entry['name']}: no answer")
            continue
        for key, value in expected.items():
            have = got.get(key)
            if key == "bootloader" and have is not None:
                have = list(have)
            if have != value:
                problems.append(f"version_query: {entry['name']}: {key} is {have!r}, expected {value!r}")
    return problems


def check_minor_field(vectors: dict) -> list[str]:
    problems = []
    for entry in vectors["minor_field"]:
        got = versioning.end_update_minor_field(entry["minor"], entry["patch"], entry["bootloader_accepts_patch"])
        if got != entry["expect"]:
            problems.append(f"minor_field: {entry}: got {got}")
    return problems


def check_version_order(vectors: dict) -> list[str]:
    problems = []
    for entry in vectors["version_order"]:
        got = versioning.compare(tuple(entry["installed"]), tuple(entry["candidate"]))
        if got != entry["expect"]:
            problems.append(f"version_order: {entry}: got {got}")
    return problems


def check_frames_encode(vectors: dict) -> list[str]:
    problems = []
    for entry in vectors["frames_encode"]:
        try:
            got = protocol.encode(entry["layout"], **_to_call_fields(entry["layout"], entry["fields"]))
        except (ValueError, TypeError) as exc:
            problems.append(f"frames_encode: {entry['name']}: raised {exc}")
            continue
        expected = (_id(entry["frame"]["id"]), bytes.fromhex(entry["frame"]["data"]))
        if got != expected:
            problems.append(f"frames_encode: {entry['name']}: got {got[0]:#x} {got[1].hex().upper()}, expected {entry['frame']['id']} {entry['frame']['data']}")
    return problems


def check_frames_decode(vectors: dict) -> list[str]:
    problems = []
    for entry in vectors["frames_decode"]:
        got = _from_result(entry["layout"], protocol.decode(entry["layout"], bytes.fromhex(entry["frame"]["data"]), bool(entry.get("strict"))))
        if got != entry["fields"]:
            problems.append(f"frames_decode: {entry['name']}: got {got}, expected {entry['fields']}")
        if _id(entry["frame"]["id"]) != protocol.LAYOUTS[entry["layout"]]["id"]:
            problems.append(f"frames_decode: {entry['name']}: the identifier does not belong to the layout")
    return problems


def check_frames_rejected(vectors: dict) -> list[str]:
    problems = []
    for entry in vectors["frames_rejected"]:
        try:
            protocol.encode(entry["layout"], **_to_call_fields(entry["layout"], entry["fields"]))
        except (ValueError, TypeError):
            continue
        problems.append(f"frames_rejected: {entry['name']} was accepted")
    return problems


def check_slcan_stream(vectors: dict) -> list[str]:
    problems = []
    for entry in vectors["slcan_stream"]:
        reader = LineReader()
        got = []
        for chunk in entry["chunks"]:
            got += [_frame_dict(frame) for frame in reader.frames(bytes.fromhex(chunk))]
        expected = [{"id": f["id"], "data": f["data"]} for f in entry["frames"]]
        if got != expected:
            problems.append(f"slcan_stream: {entry['name']}: got {got}, expected {expected}")
    return problems


CHECKS: dict[str, Callable[[dict], list[str]]] = {
    "identifiers": check_identifiers,
    "identifiers_all": check_identifiers_all,
    "magic_payloads": check_magic_payloads,
    "slcan_encode": check_slcan_encode,
    "slcan_decode": check_slcan_decode,
    "quick_state": check_quick_state,
    "version_query": check_version_query,
    "minor_field": check_minor_field,
    "version_order": check_version_order,
    "frames_encode": check_frames_encode,
    "frames_decode": check_frames_decode,
    "frames_rejected": check_frames_rejected,
    "slcan_stream": check_slcan_stream,
}


def check_all(vectors: dict | None = None) -> list[str]:
    """Every vector this package does not reproduce, one line each; [] when it reproduces them all."""
    vectors = load() if vectors is None else vectors
    problems: list[str] = []
    for section in SECTIONS:
        if section not in vectors:
            problems.append(f"the vectors have no {section} section")
    for name, check in CHECKS.items():
        if name in vectors:
            problems += check(vectors)
    return problems
