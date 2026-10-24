# =============================================================================
# URTC Flasher - session logs and update reports.
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Where session logs go, how many are kept, and the JSON report written
after an update.

* The logs folder next to the program is used when it is writable; when it is
  not (a program installed under a read-only location) a per-user folder is
  used instead.
* Only the newest ``KEEP_SESSION_LOGS`` session logs are kept, so the folder
  does not grow with every start of the tool.
* After an update a small JSON report records what was installed, over what,
  and the digest of the image. The report carries its own SHA-256 so a later
  edit of the file can be noticed; it is not a signature (the tool holds no
  signing key of its own).
"""
from __future__ import annotations

import getpass
import glob
import hashlib
import json
import os
import sys
import time

KEEP_SESSION_LOGS = 30
SESSION_LOG_PATTERN = "urtc_flasher_*.log"


def _user_state_folder() -> str:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
        return os.path.join(base, "URTC-Flasher", "logs")
    base = os.environ.get("XDG_STATE_HOME") or os.path.join(os.path.expanduser("~"), ".local", "state")
    return os.path.join(base, "urtc-flasher", "logs")


def _is_writable_folder(folder: str) -> bool:
    try:
        os.makedirs(folder, exist_ok=True)
        probe = os.path.join(folder, ".write_test")
        with open(probe, "w", encoding="utf-8") as stream:
            stream.write("")
        os.remove(probe)
        return True
    except OSError:
        return False


def writable_logs_folder(preferred: str, fallback: str | None = None) -> str | None:
    """`preferred` when it can be written, else the per-user folder, else None."""
    if _is_writable_folder(preferred):
        return preferred
    fallback = fallback or _user_state_folder()
    return fallback if _is_writable_folder(fallback) else None


def prune_session_logs(folder: str, keep: int = KEEP_SESSION_LOGS) -> int:
    """Removes the oldest session logs beyond `keep`. Returns how many went."""
    try:
        files = sorted(glob.glob(os.path.join(folder, SESSION_LOG_PATTERN)), key=os.path.getmtime)
    except OSError:
        return 0
    removed = 0
    for old in files[: max(0, len(files) - max(1, keep))]:
        try:
            os.remove(old)
            removed += 1
        except OSError:
            pass
    return removed


def _report_digest(report: dict) -> str:
    body = {key: value for key, value in report.items() if key not in ("report_sha256", "signature")}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def build_update_report(*, tool_version, image_path, image_sha256, image_size, target, installed, new,
                        hardware_id, signing_key_kind, result, operator=None, timestamp=None) -> dict:
    def _ver(value):
        return "{}.{}".format(*value) if value else None

    report = {
        "tool": "URTC Flasher",
        "tool_version": tool_version,
        "timestamp_utc": timestamp or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "operator": operator if operator is not None else _operator(),
        "target": target,
        "hardware_id": f"0x{hardware_id:08X}" if isinstance(hardware_id, int) else None,
        "image": {
            "file": os.path.basename(image_path),
            "size": image_size,
            "sha256": image_sha256,
            "signing_key_kind": signing_key_kind,
        },
        "version_before": _ver(installed),
        "version_after": _ver(new),
        "result": result,
    }
    report["report_sha256"] = _report_digest(report)
    return report


def verify_update_report(report: dict) -> bool:
    return isinstance(report, dict) and report.get("report_sha256") == _report_digest(report)


def sign_update_report(report: dict, key_file: str | None = None) -> dict:
    """The report with a ``signature`` block made with the key of this user (see urtc_can/record_signing.py).

    The key is made on first use. The signature shows the report was written with this user's key and not edited
    afterwards; it does not say who the user is. A failure to read or make the key raises ``SigningError``.
    """
    from urtc_can import record_signing

    return record_signing.sign_report(report, record_signing.load_seed(key_file))


def verify_signed_report(report: dict) -> bool:
    """True when the report is unedited (its digest) and carries a signature that matches it."""
    from urtc_can import record_signing

    return verify_update_report(report) and record_signing.verify_report(report)


def _operator() -> str:
    try:
        return getpass.getuser()
    except Exception:
        return ""


def write_update_report(report: dict, folder: str) -> str:
    """Writes the report as `urtc_update_report_<time>.json` and returns the path."""
    os.makedirs(folder, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    path = os.path.join(folder, f"urtc_update_report_{stamp}.json")
    counter = 1
    while os.path.exists(path):
        counter += 1
        path = os.path.join(folder, f"urtc_update_report_{stamp}_{counter}.json")
    with open(path, "w", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False)
    return path


def _version_key(text: str):
    parts = []
    for piece in str(text).replace("v", "").replace("V", "").split("."):
        if not piece.isdigit():
            break
        parts.append(int(piece))
    return tuple(parts)


def find_recovery_image(folder: str, hardware_id: int | None = None) -> str | None:
    """The newest main-board application image in `folder`, or None.

    An image counts when its manifest says ``component: main_application`` (and, when
    `hardware_id` is given and the manifest names one, the same hardware id). The
    version is the manifest's, else the one in the file name.
    """
    import re

    best_key, best_path = None, None
    for path in glob.glob(os.path.join(folder, "*.bin")):
        if "BOOTLOADER" in os.path.basename(path).upper():
            continue
        try:
            with open(path + ".manifest.json", "r", encoding="utf-8") as stream:
                manifest = json.load(stream)
        except (OSError, ValueError):
            continue
        if not isinstance(manifest, dict) or manifest.get("component") != "main_application":
            continue
        declared = manifest.get("hardware_id")
        if hardware_id is not None and declared not in (None, ""):
            try:
                if int(str(declared), 0) != hardware_id:
                    continue
            except ValueError:
                continue
        version = _version_key(manifest.get("version", ""))
        if not version:
            match = re.search(r"[vV](\d+(?:\.\d+)+)", os.path.basename(path))
            version = _version_key(match.group(1)) if match else ()
        key = (version, os.path.getmtime(path))
        if best_key is None or key > best_key:
            best_key, best_path = key, path
    return best_path
