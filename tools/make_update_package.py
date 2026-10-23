#!/usr/bin/env python3
# =============================================================================
# URTC-COMMON - tools/make_update_package.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Build, sign and check the update package of a program for a release.

    python tools/make_update_package.py build  --app urtc-flasher --version 0.5.0 --platform windows-x64 \\
                                               --source dist/URTC-Flasher --entry URTC-Flasher.exe --out out/
    python tools/make_update_package.py verify out/urtc-flasher-0.5.0-windows-x64.zip
    python tools/make_update_package.py public

``build`` copies the folder of the program, adds ``app_info.json`` (name, version, platform, entry), packs it as
``<app>-<version>-<platform>.zip`` (``.tar.gz`` outside Windows) with the same bytes every time (sorted, fixed times),
and writes next to it ``<package>.sha256`` and ``<package>.sig``: the Ed25519 signature, by the key of the releases, of
``urtc-pkg/1|app|version|platform|sha256|size``. It prints the ``key_id:`` line to put in the notes of the release.
The private key is never printed and never in a repository: ``--key``, ``URTC_RELEASE_KEY`` or
``~/.urtc-keys/urtc_release_ed25519.pem`` (PKCS8, as the other signing tools read it). Signing here is plain
Python (RFC 8032), so no package has to be installed; ``verify`` needs no private key.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

try:  # URTC-COMMON itself
    from urtc_common import self_update as su  # noqa: E402
    from urtc_common import update_service as svc  # noqa: E402
except ImportError:  # a program that carries the copy in urtc_can/
    from urtc_can import self_update as su  # type: ignore[no-redef]  # noqa: E402
    from urtc_can import update_service as svc  # type: ignore[no-redef]  # noqa: E402

FIXED_TIME = (2020, 1, 1, 0, 0, 0)
EXCLUDED = {"__pycache__", ".git", ".venv"}


# --- Ed25519 signing (RFC 8032) -----------------------------------------------------------------------------------
def _compress(point) -> bytes:
    x, y, z, _ = point
    zi = pow(z, su._P - 2, su._P)
    x, y = x * zi % su._P, y * zi % su._P
    return (y | ((x & 1) << 255)).to_bytes(32, "little")


def _expand(seed: bytes):
    h = hashlib.sha512(seed).digest()
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    return a, h[32:]


def public_key_of(seed: bytes) -> bytes:
    a, _ = _expand(seed)
    return _compress(su._mul(a, su.BASE_POINT))


def sign(seed: bytes, message: bytes) -> bytes:
    a, prefix = _expand(seed)
    public = _compress(su._mul(a, su.BASE_POINT))
    r = int.from_bytes(hashlib.sha512(prefix + message).digest(), "little") % su._Q
    r_bytes = _compress(su._mul(r, su.BASE_POINT))
    k = int.from_bytes(hashlib.sha512(r_bytes + public + message).digest(), "little") % su._Q
    return r_bytes + ((r + k * a) % su._Q).to_bytes(32, "little")


def read_seed(path: Path) -> bytes:
    """The 32-byte seed of an Ed25519 key in PKCS8 PEM (48 bytes of DER: a 16-byte header and the seed)."""
    lines = [line.strip() for line in path.read_text(encoding="ascii").splitlines() if line.strip() and not line.startswith("-----")]
    der = base64.b64decode("".join(lines))
    if len(der) != 48 or not der.startswith(bytes.fromhex("302e020100300506032b657004220420")):
        raise SystemExit(f"PACKAGE=FAIL {path} is not an Ed25519 key in PKCS8 form")
    return der[16:]


def key_path(explicit: str | None) -> Path:
    return Path(explicit or os.environ.get("URTC_RELEASE_KEY") or Path.home() / ".urtc-keys" / "urtc_release_ed25519.pem")


# --- the package ---------------------------------------------------------------------------------------------------
def collect(source: Path) -> list[Path]:
    files = []
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if path.is_file() and not any(part in EXCLUDED for part in relative.parts):
            files.append(relative)
    return files


def build_archive(source: Path, files: list[Path], info: dict, platform: str) -> bytes:
    info_bytes = (json.dumps(info, indent=2, sort_keys=True) + "\n").encode("utf-8")
    buffer = io.BytesIO()
    if platform.startswith("windows"):
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for relative in files:
                if relative.as_posix() == "app_info.json":
                    continue
                entry = zipfile.ZipInfo(relative.as_posix(), FIXED_TIME)
                entry.compress_type = zipfile.ZIP_DEFLATED
                entry.external_attr = 0o644 << 16
                archive.writestr(entry, (source / relative).read_bytes())
            entry = zipfile.ZipInfo("app_info.json", FIXED_TIME)
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o644 << 16
            archive.writestr(entry, info_bytes)
    else:
        with tarfile.open(fileobj=buffer, mode="w:gz", format=tarfile.PAX_FORMAT, compresslevel=9) as archive:
            for relative in files:
                if relative.as_posix() == "app_info.json":
                    continue
                data = (source / relative).read_bytes()
                member = tarfile.TarInfo(relative.as_posix())
                member.size = len(data)
                member.mtime = 0
                member.mode = 0o755 if os.access(source / relative, os.X_OK) else 0o644
                archive.addfile(member, io.BytesIO(data))
            member = tarfile.TarInfo("app_info.json")
            member.size = len(info_bytes)
            member.mtime = 0
            member.mode = 0o644
            archive.addfile(member, io.BytesIO(info_bytes))
    return buffer.getvalue()


def build(app: str, version: str, platform: str, source: Path, entry: str, out: Path, seed: bytes) -> tuple[Path, str]:
    su.parse_version(version)
    if not su._APP.match(app):
        raise SystemExit(f"PACKAGE=FAIL {app!r} is not an application name")
    if not source.is_dir():
        raise SystemExit(f"PACKAGE=FAIL {source} is not a folder")
    files = collect(source)
    if Path(entry) not in files:
        raise SystemExit(f"PACKAGE=FAIL the entry {entry} is not in {source}")
    info = {"name": app, "version": version, "platform": platform, "entry": entry}
    data = build_archive(source, files, info, platform)
    out.mkdir(parents=True, exist_ok=True)
    package = out / su.package_name(app, version, platform)
    package.write_bytes(data)
    sha = hashlib.sha256(data).hexdigest()
    (out / (package.name + ".sha256")).write_text(f"{sha}  {package.name}\n", encoding="ascii")
    signature = sign(seed, su.package_message(app, version, platform, sha, len(data)))
    (out / (package.name + ".sig")).write_text(signature.hex() + "\n", encoding="ascii")
    key_id = hashlib.sha256(public_key_of(seed)).hexdigest()[:16]
    return package, key_id


def verify(package: Path) -> str:
    """Checks a package and its two companions against the pinned key; returns a line describing it."""
    name = package.name
    stem = name[:-4] if name.endswith(".zip") else name[:-7] if name.endswith(".tar.gz") else None
    if stem is None:
        raise SystemExit("VERIFY=FAIL the package is neither .zip nor .tar.gz")
    # <app>-<version>-<os>-<arch>: the platform has a dash of its own
    pieces = stem.split("-")
    platform = "-".join(pieces[-2:])
    version = pieces[-3]
    app = "-".join(pieces[:-3])
    sha = package.with_name(name + ".sha256").read_text(encoding="ascii").split()[0]
    signature = bytes.fromhex(package.with_name(name + ".sig").read_text(encoding="ascii").strip())
    asset = su.Asset(name, "", package.stat().st_size)
    offer = su.Offer(app, version, platform, "v" + version, "", "", asset, asset, asset, "")
    su.verify_package(offer, package, sha, signature, svc.RELEASE_PUBLIC_KEY_HEX, svc.RELEASE_KEY_ID)
    return f"VERIFY=PASS {name} sha256 {sha} key_id {svc.RELEASE_KEY_ID}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build")
    b.add_argument("--app", required=True)
    b.add_argument("--version", required=True)
    b.add_argument("--platform", required=True)
    b.add_argument("--source", required=True)
    b.add_argument("--entry", required=True)
    b.add_argument("--out", required=True)
    b.add_argument("--key")
    v = sub.add_parser("verify")
    v.add_argument("package")
    p = sub.add_parser("public")
    p.add_argument("--key")
    args = parser.parse_args(argv)
    try:
        if args.command == "public":
            print(public_key_of(read_seed(key_path(args.key))).hex())
            return 0
        if args.command == "verify":
            print(verify(Path(args.package)))
            return 0
        seed = read_seed(key_path(args.key))
        package, key_id = build(args.app, args.version, args.platform, Path(args.source), args.entry, Path(args.out), seed)
        if key_id != svc.RELEASE_KEY_ID:
            print(f"PACKAGE=FAIL the key signs as {key_id}, the programs trust {svc.RELEASE_KEY_ID}", file=sys.stderr)
            return 1
        print(f"PACKAGE=PASS {package}")
        print(f"key_id: {key_id}")
        return 0
    except su.UpdateError as error:
        print(f"PACKAGE=FAIL {error.code}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
