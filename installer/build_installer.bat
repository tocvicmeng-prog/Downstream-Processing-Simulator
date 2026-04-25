@echo off
REM ---------------------------------------------------------------------
REM Build the DPSim Windows installer (.exe) with Inno Setup.
REM
REM Prerequisites:
REM   * Python 3.11+ on PATH (for building the wheel)
REM   * Inno Setup 6 (winget install -e --id JRSoftware.InnoSetup)
REM
REM Usage (from repo root):
REM   installer\build_installer.bat
REM
REM Produces:
REM   release\DPSim-<version>-Setup.exe
REM ---------------------------------------------------------------------

setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0\.."

echo [build-installer] 1/5  Building wheel + sdist
python -m pip install --quiet --upgrade build wheel || exit /b 1
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist src\downstream_processing_simulator.egg-info rmdir /s /q src\downstream_processing_simulator.egg-info
python -m build --wheel --sdist || exit /b 2

echo [build-installer] 2/5  Staging runtime assets
if exist installer\stage rmdir /s /q installer\stage
mkdir installer\stage\wheels
mkdir installer\stage\configs
mkdir installer\stage\docs

copy /y dist\downstream_processing_simulator-*-py3-none-any.whl installer\stage\wheels\       > nul
copy /y configs\default.toml            installer\stage\configs\       > nul
copy /y configs\fast_smoke.toml         installer\stage\configs\       > nul
copy /y configs\stirred_vessel.toml     installer\stage\configs\       > nul

REM Manuals: rebuild both PDFs (main + Appendix J) from Markdown sources.
REM build_pdf.py iterates its BUILD_TARGETS registry to cover both files.
if exist docs\user_manual\build_pdf.py (
    python docs\user_manual\build_pdf.py > nul
)
copy /y docs\user_manual\polysaccharide_microsphere_simulator_first_edition.pdf ^
        installer\stage\docs\User_Manual_First_Edition.pdf > nul
REM Do NOT ship the Markdown source of the main manual in the installer.
REM Runtime users do not need the .md; it belongs in the repo only.
REM (v9.0 cleanliness: no technical development docs in the installer.)
copy /y docs\user_manual\appendix_J_functionalization_protocols.pdf ^
        installer\stage\docs\Appendix_J_Functionalization_Protocols.pdf > nul

REM Bundled launcher + docs from the tracked template directory.
REM These live under installer\templates\ so the build is reproducible
REM from a fresh clone (release\ is gitignored and would be missing).
for %%F in (install.bat launch_ui.bat launch_cli.bat uninstall.bat
            README.txt INSTALL.md RELEASE_NOTES.md WHERE_ARE_THE_PROGRAM_FILES.txt) do (
    copy /y installer\templates\%%F installer\stage\ > nul
)
copy /y LICENSE installer\stage\LICENSE.txt > nul

REM v0.3.8 release-tooling refresh: derive version from pyproject.toml
REM and substitute __DPSIM_VERSION__ placeholders in every staged
REM template. This keeps install.bat / launch_*.bat / README.txt /
REM RELEASE_NOTES.md banners truthful without hardcoding a version
REM string in each file (the v0.1.0 templates went stale by v0.3.x).
python -c "from pathlib import Path; import sys, re;^
 ver = re.search(r'^version = \"([^\"]+)\"', Path('pyproject.toml').read_text(encoding='utf-8'), re.M).group(1);^
 [p.write_text(p.read_text(encoding='utf-8').replace('__DPSIM_VERSION__', ver), encoding='utf-8')^
  for p in Path('installer/stage').rglob('*')^
  if p.is_file() and p.suffix in ('.bat', '.txt', '.md')];^
 print(f'[build-installer] Substituted __DPSIM_VERSION__ -> {ver} in staged templates')"
if errorlevel 1 (
    echo [build-installer] ERROR: version substitution failed.
    exit /b 6
)

REM Defensive: force CRLF line endings on all .bat files before
REM bundling. A previous release shipped LF-terminated .bat files
REM (sed -i on Git Bash strips CRLF), which breaks cmd.exe's
REM multi-line for/if block parser with "`.` was unexpected" errors.
python -c "from pathlib import Path; import sys;^
 [p.write_bytes(p.read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))^
  for p in Path('installer/stage').glob('*.bat')];^
 print('[build-installer] CRLF normalised on all staged .bat files')"
if errorlevel 1 (
    echo [build-installer] WARNING: CRLF normalisation failed.
)

echo [build-installer] 3/5  Locating ISCC.exe
set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
    echo [build-installer] ERROR: ISCC.exe not found.
    echo                  Install Inno Setup:
    echo                  winget install -e --id JRSoftware.InnoSetup
    exit /b 3
)

REM Derive the version from the wheel filename so the installer name,
REM the .iss AppVersion, and the final "Output:" echo all track the
REM single source of truth (pyproject.toml -> the wheel just built).
REM Wheel filename: downstream_processing_simulator-<VERSION>-py3-none-any.whl
set "VERSION="
for %%W in (installer\stage\wheels\downstream_processing_simulator-*-py3-none-any.whl) do (
    set "_WHL_NAME=%%~nW"
)
for /f "tokens=2 delims=-" %%V in ("!_WHL_NAME!") do set "VERSION=%%V"
if not defined VERSION (
    echo [build-installer] ERROR: could not derive VERSION from wheel filename.
    exit /b 5
)
echo [build-installer] Building installer for DPSim %VERSION%.

echo [build-installer] 4/5  Compiling installer
"%ISCC%" /DMyAppVersion=%VERSION% installer\DPSim.iss || exit /b 4

echo [build-installer] 5/5  Building portable ZIP
REM v0.3.8 release-tooling: ship a portable ZIP alongside the .exe
REM installer for users who prefer unzip-and-run (no admin, no Start
REM Menu shortcut, no uninstaller record). Same staged contents as
REM the installer payload — just packed into a ZIP that extracts to a
REM single self-contained DPSim-X.Y.Z-Windows-x64\ folder. The user
REM runs install.bat once inside the unzipped folder to create the
REM .venv and pip-install the bundled wheel; subsequent runs of
REM launch_ui.bat skip straight to the UI.
set "PORTABLE_ROOT=installer\stage_portable"
set "PORTABLE_FOLDER=DPSim-%VERSION%-Windows-x64"
if exist "%PORTABLE_ROOT%" rmdir /s /q "%PORTABLE_ROOT%"
mkdir "%PORTABLE_ROOT%\%PORTABLE_FOLDER%"
xcopy /e /i /q /y installer\stage\* "%PORTABLE_ROOT%\%PORTABLE_FOLDER%\" > nul
copy /y installer\LICENSE_AND_IP.txt "%PORTABLE_ROOT%\%PORTABLE_FOLDER%\" > nul

REM Build the ZIP with PowerShell's Compress-Archive (built into
REM Windows 10+); avoids requiring 7-Zip on the build machine.
set "PORTABLE_ZIP=release\DPSim-%VERSION%-Windows-x64-portable.zip"
if not exist release mkdir release
if exist "%PORTABLE_ZIP%" del /q "%PORTABLE_ZIP%"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "Compress-Archive -Path '%PORTABLE_ROOT%\%PORTABLE_FOLDER%' -DestinationPath '%PORTABLE_ZIP%' -CompressionLevel Optimal -Force"
if errorlevel 1 (
    echo [build-installer] ERROR: portable ZIP build failed.
    exit /b 7
)
rmdir /s /q "%PORTABLE_ROOT%"

echo.
echo [build-installer] DONE.
echo Output:
echo     release\DPSim-%VERSION%-Setup.exe
echo     release\DPSim-%VERSION%-Windows-x64-portable.zip
endlocal
exit /b 0
