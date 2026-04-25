@echo off
REM ---------------------------------------------------------------------
REM DPSim 0.1.0 -- Open a Command Prompt with dpsim on PATH (self-heal)
REM Drops into an interactive cmd.exe with the .venv activated, so you
REM can run dpsim subcommands directly:
REM     dpsim run configs\default.toml
REM     dpsim sweep --rpm-min 3000 --rpm-max 15000
REM     dpsim uncertainty --n-samples 50
REM     dpsim design --d32 50e-6 --d32-tol 10e-6
REM Type 'exit' to close.
REM
REM If the virtual environment is missing, this script offers to run
REM install.bat automatically so the first launch "just works".
REM ---------------------------------------------------------------------

setlocal EnableExtensions
cd /d "%~dp0"

if not defined DPSIM_RUNTIME_DIR set "DPSIM_RUNTIME_DIR=%LOCALAPPDATA%\DPSim"
if "%DPSIM_RUNTIME_DIR%"=="\DPSim" set "DPSIM_RUNTIME_DIR=%CD%\.runtime"
set "DPSIM_TMPDIR=%DPSIM_RUNTIME_DIR%\tmp"
set "DPSIM_CACHE_DIR=%DPSIM_RUNTIME_DIR%\cache"
set "DPSIM_OUTPUT_DIR=%DPSIM_RUNTIME_DIR%\output"
if not exist "%DPSIM_TMPDIR%" mkdir "%DPSIM_TMPDIR%"
if not exist "%DPSIM_CACHE_DIR%" mkdir "%DPSIM_CACHE_DIR%"
if not exist "%DPSIM_OUTPUT_DIR%" mkdir "%DPSIM_OUTPUT_DIR%"
set "TEMP=%DPSIM_TMPDIR%"
set "TMP=%DPSIM_TMPDIR%"
set "TMPDIR=%DPSIM_TMPDIR%"
set "PIP_CACHE_DIR=%DPSIM_CACHE_DIR%\pip"
set "MPLCONFIGDIR=%DPSIM_CACHE_DIR%\matplotlib"
if not exist "%PIP_CACHE_DIR%" mkdir "%PIP_CACHE_DIR%"
if not exist "%MPLCONFIGDIR%" mkdir "%MPLCONFIGDIR%"

REM Check both the venv activation script AND that dpsim is actually
REM installed inside the venv. A partial install (venv created, pip
REM install failed) would otherwise pass the first check and drop the
REM user into a shell without the dpsim command available.
if not exist ".venv\Scripts\activate.bat" goto setup
if not exist ".venv\Scripts\python.exe"  goto setup
".venv\Scripts\python.exe" -c "import dpsim" 1>nul 2>nul
if errorlevel 1 goto setup

:launch
echo [DPSim 0.1.0] Command-line shell. Type 'exit' to close.
echo                 Example: dpsim run configs\default.toml
echo.
cmd /k ".venv\Scripts\activate.bat && cd /d %~dp0"
endlocal
exit /b %ERRORLEVEL%

:setup
echo [DPSim 0.1.0] Virtual environment not found at:
echo                 %CD%\.venv
echo.
echo The installer's post-install step appears not to have completed.
echo (Most common cause: a supported Python (3.11 or 3.12) was not on PATH at install time.)
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo [DPSim] Python is not on PATH either.
    echo           1. Install Python 3.11 or newer from
    echo              https://www.python.org/downloads/windows/
    echo              (tick "Add python.exe to PATH" during setup).
    echo           2. Re-run launch_cli.bat and setup will continue.
    echo.
    pause
    endlocal
    exit /b 1
)

echo [DPSim] Python was found:
for /f "delims=" %%v in ('python --version 2^>^&1') do echo           %%v
echo.
echo           Press any key to run setup now (creates .venv and
echo           installs the runtime -- approx. 3-8 minutes), or
echo           close this window to abort.
pause >nul

call "%~dp0install.bat" --no-test
if errorlevel 1 (
    echo.
    echo [DPSim] Setup failed with error code %ERRORLEVEL%.
    echo           Scroll up to see the cause, or rerun
    echo           install.bat for a full re-install.
    pause
    endlocal
    exit /b %ERRORLEVEL%
)

echo.
echo [DPSim] Setup finished successfully. Starting the CLI shell...
echo.
goto launch
