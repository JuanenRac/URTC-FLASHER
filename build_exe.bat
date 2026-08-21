@echo off
setlocal EnableDelayedExpansion
REM Builds a standalone Windows .exe for the URTC Flasher.
REM Run this on a Windows machine with Python installed.
REM
REM Usage:
REM   build_exe.bat
REM
REM Output: dist\URTC_Flasher.exe (no Python installation needed to run it)

echo.
echo  ===============================================================
echo   URTC-FLASHER - build_exe.bat
echo   Builds a standalone Windows .exe (dist\URTC_Flasher.exe) via
echo   PyInstaller - no Python installation needed to run the result.
echo  ===============================================================
echo   Copyright (C) 2026 JuanenRac (Electro Hobby 3D)
echo   ^<electrohobby3d@gmail.com^>
echo   GPL-3.0 - see LICENSE
echo  ===============================================================
echo.

REM NOTE: every step below runs through "python -m" rather than calling
REM pip/pyinstaller directly. pip.exe and pyinstaller.exe both get installed
REM into Python's Scripts\ folder, which on plenty of Windows setups isn't
REM on PATH (common if Python was installed without checking "Add Python to
REM PATH") - calling them directly then fails with a "not recognized"
REM error even though the install itself succeeded. "python -m" sidesteps
REM this by finding the installed module directly rather than needing its
REM wrapper .exe to be on PATH.

echo [1/6] Installing Python dependencies...
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt
python -m pip install pyinstaller
echo       Done.
echo.

echo [2/6] Bumping FLASHER_VERSION (ecosystem-wide build-version policy)...
REM Every real packaged build gets a new patch version automatically -
REM see bump_version.py's own docstring for the base-10 carry rule
REM (1.1.9 -> 1.2.0). Runs before PyInstaller so the bumped value is what
REM actually gets compiled into this .exe, not the pre-bump value.
python bump_version.py
if errorlevel 1 (
    echo       ERROR: version bump failed - see the output above.
    pause
    exit /b 1
)
echo       Done.
echo.

echo [3/6] Cleaning previous build...
REM Clean slate before compiling: build\ holds PyInstaller's intermediate
REM artifacts (its own bytecode/dependency cache), and dist\ holds the
REM previous output - removing both first means nothing stale from an
REM earlier build can survive into this one, rather than relying on
REM --noconfirm alone to just overwrite the final .exe.
if exist build rmdir /s /q build
if exist dist (
    rmdir /s /q dist
    if exist dist (
        echo       ERROR: couldn't remove dist\ - is URTC_Flasher.exe currently running?
        echo       Close it first, then run this script again.
        pause
        exit /b 1
    )
)
echo       Done.
echo.

echo [4/6] Compiling URTC_Flasher.exe with PyInstaller...
REM --add-data uses ";" as the source/destination separator on Windows -
REM Linux/Mac PyInstaller uses ":" instead (see build_exe.sh). Bundles the
REM assets/ folder (the banner + icon images) into the .exe itself so it
REM doesn't need to sit next to it the way firmware/ does.
REM --icon sets what Explorer/the taskbar shows for the .exe file itself -
REM separate from root.iconphoto() in the code, which sets the title-bar/
REM Alt-Tab icon of the running window. Both need setting for a consistent
REM icon everywhere.
REM --noconfirm: kept as a second layer even with the clean above - in
REM case dist\ gets recreated between the rmdir and this running.
REM --hidden-import for each of this project's own modules: this file was
REM split from one large urtc_flasher.py into several (flasher_config.py,
REM flasher_transports.py, etc.) for readability. PyInstaller's static
REM analyzer normally finds these on its own by walking the import tree,
REM but flasher_gui is imported deferred (inside main(), only once --cli
REM mode is ruled out) rather than at module level - listing every one
REM explicitly here removes any doubt about whether that's caught.
python -m PyInstaller --onefile --windowed --noconfirm --name "URTC_Flasher" ^
    --icon "assets\urtc_icon.ico" ^
    --add-data "assets;assets" ^
    --hidden-import flasher_config ^
    --hidden-import flasher_transports ^
    --hidden-import flasher_swd_tools ^
    --hidden-import flasher_validation ^
    --hidden-import flasher_protocol ^
    --hidden-import flasher_github ^
    --hidden-import flasher_gui ^
    urtc_flasher.py
if not exist dist\URTC_Flasher.exe (
    echo       ERROR: PyInstaller did not produce dist\URTC_Flasher.exe - see the output above.
    pause
    exit /b 1
)
echo       Done.
echo.

echo [5/6] Copying files that must sit next to the .exe, not inside it...
REM firmware/ and language/ are deliberately NOT bundled into the .exe
REM itself (unlike assets/ above) - both are meant to stay editable
REM without a rebuild, and FIRMWARE_FOLDER/LANGUAGE_FOLDER both resolve
REM next to the .exe, not inside PyInstaller's bundled data.
if exist firmware (
    xcopy /E /I /Y firmware dist\firmware >nul
    echo       Copied firmware\ into dist\firmware\
)
if exist language (
    xcopy /E /I /Y language dist\language >nul
    echo       Copied language\ into dist\language\
)
REM README.md and LICENSE: read directly by the Help menu's Readme/License
REM entries (flasher_config.base_dir - next to the .exe, same reasoning as
REM firmware/language above). Missing from dist/ meant those menu entries
REM had nothing to open in a built .exe, even though they worked fine
REM running from source. README_*.md (README_spa.md, README_ita.md, etc.)
REM are the per-language versions the Readme menu entry picks up
REM automatically based on the active language - copied via a for loop
REM rather than listing each language explicitly, so a new translation
REM added later is picked up without editing this script again.
if exist README.md (
    copy /Y README.md dist\README.md >nul
    echo       Copied README.md into dist\
)
for %%f in (README_*.md) do (
    copy /Y "%%f" "dist\%%f" >nul
    echo       Copied %%f into dist\
)
if exist LICENSE (
    copy /Y LICENSE dist\LICENSE >nul
    echo       Copied LICENSE into dist\
)
REM urtc_config.json.example: a starting point for the technical HMAC
REM key/HardwareID overrides described in the README - copied as-is
REM (still ".example", not renamed to urtc_config.json) so it never
REM silently activates overrides nobody asked for; a user who needs it
REM renames it themselves after editing it.
if exist urtc_config.json.example (
    copy /Y urtc_config.json.example dist\urtc_config.json.example >nul
    echo       Copied urtc_config.json.example into dist\
)
echo       Done.
echo.

echo [6/6] Build complete.
echo  ===============================================================
echo   dist\URTC_Flasher.exe is ready to run - no Python needed.
echo  ===============================================================
echo.
pause
