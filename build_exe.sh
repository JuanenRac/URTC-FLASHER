#!/usr/bin/env bash
# HYDRA_UMC_SCRIPT_STANDARD_HEADER_BEGIN
# *****************************************************************************
# Project   : URTC-FLASHER
# Script    : build_exe.sh
# Purpose   : Incremental standalone executable build and packaging workflow.
# Author    : JuanenRac (Electro Hobby 3D)
# Email     : electrohobby3d@gmail.com
# Copyright : (C) 2026 JuanenRac
# License   : GPL-3.0 - see LICENSE
# *****************************************************************************
# HYDRA_UMC_SCRIPT_STANDARD_HEADER_END
# HYDRA_UMC_SCRIPT_STANDARD_BANNER_BEGIN
printf '\n*******************************************************************************\n'
printf '%s\n' "* URTC-FLASHER - build_exe.sh"
printf '%s\n' "* Mode      : INCREMENTAL BUILD"
printf '%s\n' "* Author    : JuanenRac (Electro Hobby 3D)"
printf '%s\n' "* Email     : electrohobby3d@gmail.com"
printf '%s\n' "* Copyright : (C) 2026 JuanenRac"
printf '%s\n' "* License   : GPL-3.0 - see LICENSE"
printf '%s\n' "* ------------------------------------------------------------------------- *"
printf '%s\n' "* 1. Increment the project version and synchronise its manifest."
printf '%s\n' "* 2. Run this project's declared build, verification and packaging commands."
printf '%s\n' "* 3. Report the result and keep an interactive terminal open."
printf '%s\n' "*******************************************************************************"
printf '\n'
# HYDRA_UMC_SCRIPT_STANDARD_BANNER_END
# Builds a standalone Linux binary for the URTC Flasher.
# Run this on the Linux machine you actually want to run it on - unlike
# cross-compiling, PyInstaller builds a binary for whatever OS it runs on,
# so this won't produce something usable on Windows, and build_exe.bat
# won't produce something usable here.
#
# Usage:
#   chmod +x build_exe.sh   (one-time)
#   ./build_exe.sh
#
# Output: dist/URTC_Flasher (no Python installation needed to run it)
#
# NOTE: python3 -m pip / python3 -m PyInstaller, same reasoning as
# build_exe.bat's Windows PATH note - calling the installed modules
# directly sidesteps any question of whether their wrapper scripts landed
# somewhere on PATH.
set -euo pipefail

# Keeps the terminal window open long enough to actually read the output
# when this script was launched by double-clicking rather than from an
# already-open shell - fires on a normal successful finish AND on any
# failure exit, including one `set -euo pipefail` triggers on its own for
# a command with no explicit error handling below (a plain `exit 1` placed
# only at the bottom of the file would never run in that case, since
# `set -e` jumps straight past it). Reading into a throwaway variable
# because `read -p` alone still needs somewhere to put its input.
trap 'read -p "Pulsa Enter para cerrar..." _' EXIT
if ! python3 -c "import tkinter" 2>/dev/null; then
    echo "      tkinter isn't available for this Python install."
    echo "      On Debian/Ubuntu:  sudo apt install python3-tk"
    echo "      On Fedora:         sudo dnf install python3-tkinter"
    echo "      On Arch:           sudo pacman -S tk"
    exit 1
fi
echo "      Found."
echo

echo "[2/6] Installing Python dependencies..."
python3 -m pip install --upgrade pip >/dev/null
python3 -m pip install -r requirements.txt
python3 -m pip install pyinstaller
echo "      Done."
echo

echo "[3/6] Bumping FLASHER_VERSION (ecosystem-wide build-version policy)..."
# Every real packaged build gets a new patch version automatically - see
# bump_version.py's own docstring for the base-10 carry rule
# (1.1.9 -> 1.2.0). Runs before PyInstaller so the bumped value is what
# actually gets compiled into this binary, not the pre-bump value.
# HYDRA_UMC_SCRIPT_STANDARD_VERSION_STEP
printf '%s\n' "[1/6] Incrementing project version and synchronising its manifest..."
python3 bump_version.py || exit 1
# HYDRA_UMC_SCRIPT_STANDARD_VERSION_CAPTURE_BEFORE
HYDRA_UMC_VERSION_BEFORE="$(python3 -c 'import json, pathlib, sys; print(json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))["version"])' "$(dirname "$0")/hydra-umc.project.json")"
python3 "$(dirname "$0")/bump_manifest_version.py" --sync || exit 1
# HYDRA_UMC_SCRIPT_STANDARD_VERSION_CAPTURE_AFTER
HYDRA_UMC_VERSION_AFTER="$(python3 -c 'import json, pathlib, sys; print(json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))["version"])' "$(dirname "$0")/hydra-umc.project.json")"
printf '\n*******************************************************************************\n'
printf '%s\n' '* VERSION INCREMENT COMPLETED'
printf '%s\n' "* v${HYDRA_UMC_VERSION_BEFORE:-unknown} -> v${HYDRA_UMC_VERSION_AFTER:-unknown}"
printf '%s\n' '* Project manifest has been synchronised by the project build flow.'
printf '%s\n' '*******************************************************************************'
printf '\n'
echo "      Done."
echo

echo "[4/6] Cleaning previous build..."
# Clean slate before compiling: build/ holds PyInstaller's intermediate
# artifacts (its own bytecode/dependency cache), and dist/ holds the
# previous output - removing both first means nothing stale from an
# earlier build can survive into this one, rather than relying on
# --noconfirm alone to just overwrite the final binary.
rm -rf build dist
echo "      Done."
echo

echo "[5/6] Compiling URTC_Flasher with PyInstaller..."
# --hidden-import for each of this project's own modules: this file was
# split from one large urtc_flasher.py into several (flasher_config.py,
# flasher_transports.py, etc.) for readability. PyInstaller's static
# analyzer normally finds these on its own by walking the import tree, but
# flasher_gui is imported deferred (inside main(), only once --cli mode is
# ruled out, matching the reasoning already in that function) rather than
# at module level - listing every one explicitly here removes any doubt
# about whether the analyzer's own import-tree walk catches that case.
python3 -m PyInstaller --onefile --noconfirm --name "URTC_Flasher" \
    --add-data "assets:assets" \
    --hidden-import flasher_config \
    --hidden-import flasher_transports \
    --hidden-import flasher_swd_tools \
    --hidden-import flasher_validation \
    --hidden-import flasher_protocol \
    --hidden-import flasher_github \
    --hidden-import flasher_gui \
    urtc_flasher.py
if [ ! -f dist/URTC_Flasher ]; then
    echo "      ERROR: PyInstaller did not produce dist/URTC_Flasher - see the output above."
    exit 1
fi
echo "      Done."
echo

echo "[6/6] Copying files that must sit next to the binary, not inside it..."
# firmware/ and language/ are deliberately NOT bundled into the binary
# itself (unlike assets/ above) - both are meant to stay editable without
# a rebuild, and FIRMWARE_FOLDER/LANGUAGE_FOLDER both resolve next to the
# executable, not inside PyInstaller's bundled data.
if [ -d firmware ]; then
    mkdir -p dist/firmware
    cp -r firmware/. dist/firmware/
    echo "      Copied firmware/ into dist/firmware/"
fi
if [ -d language ]; then
    mkdir -p dist/language
    cp -r language/. dist/language/
    echo "      Copied language/ into dist/language/"
fi
# README.md and LICENSE: read directly by the Help menu's Readme/License
# entries (flasher_config.base_dir - next to the executable, same
# reasoning as firmware/language above). Missing from dist/ meant those
# menu entries had nothing to open in a built binary, even though they
# worked fine running from source. README_*.md (README_spa.md,
# README_ita.md, etc.) are the per-language versions the Readme menu
# entry picks up automatically based on the active language - copied via
# a glob rather than listing each language explicitly, so a new
# translation added later is picked up without editing this script again.
if [ -f README.md ]; then
    cp README.md dist/README.md
    echo "      Copied README.md into dist/"
fi
for f in README_*.md; do
    if [ -f "$f" ]; then
        cp "$f" "dist/$f"
        echo "      Copied $f into dist/"
    fi
done
if [ -f LICENSE ]; then
    cp LICENSE dist/LICENSE
    echo "      Copied LICENSE into dist/"
fi
# urtc_config.json.example: a starting point for the technical HMAC
# key/HardwareID overrides described in the README - copied as-is (still
# ".example", not renamed to urtc_config.json) so it never silently
# activates overrides nobody asked for; a user who needs it renames it
# themselves after editing it.
if [ -f urtc_config.json.example ]; then
    cp urtc_config.json.example dist/urtc_config.json.example
    echo "      Copied urtc_config.json.example into dist/"
fi
echo "      Done."
echo

echo " ==============================================================="
echo "  Build complete: dist/URTC_Flasher is ready to run - no Python needed."
echo "  (chmod +x dist/URTC_Flasher if it isn't already executable)"
echo " ==============================================================="
echo
