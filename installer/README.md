# DPSim Windows Release-Build Sources

This directory holds the build assets that produce the **two**
Windows release artifacts attached to each GitHub release:

| Artifact | Use case |
|---|---|
| `DPSim-<version>-Setup.exe` | One-click installer with EULA wizard, Start-Menu shortcut, post-install hook, clean uninstaller. |
| `DPSim-<version>-Windows-x64-portable.zip` | Unzip-and-run package for users who prefer no installation, no admin, no registry footprint. |

Both artifacts share the **same payload** (wheel + configs + PDFs +
launcher batch files + EULA + LICENSE). The only difference is the
delivery wrapper.

## What is tracked here

| File | Role |
|---|---|
| `DPSim.iss` | Inno Setup script: installer metadata, EULA page, file layout, Start-Menu / desktop shortcuts, post-install hook, uninstall steps, Python-presence check. |
| `LICENSE_AND_IP.txt` | End-user licence agreement shown on the installer's first page. States that intellectual property rights belong to **Holocyte Pty Ltd**, that the software is licensed under **GPL-3.0**, and that the canonical source is the GitHub repository. |
| `build_installer.bat` | Build helper. Rebuilds the wheel, stages runtime assets, substitutes version banners, compiles the installer via `ISCC.exe`, **and** packages the portable ZIP via PowerShell `Compress-Archive`. |
| `templates/` | Source files for everything that ends up in the user's install folder: `install.bat`, `launch_ui.bat`, `launch_cli.bat`, `uninstall.bat`, `README.txt`, `INSTALL.md`, `RELEASE_NOTES.md`, `WHERE_ARE_THE_PROGRAM_FILES.txt`. Each carries an `__DPSIM_VERSION__` placeholder that the build substitutes from `pyproject.toml` at staging time, so version bumps don't require touching templates. |
| `README.md` | This file. |

## What is **not** tracked (gitignored)

- `stage/` — transient build directory, recreated each time
  `build_installer.bat` runs. Contains the runtime assets that get
  compressed into the installer payload AND the portable ZIP source.
- `stage_portable/` — transient ZIP staging.
- Build outputs in `release/` (`*Setup.exe`, `*portable.zip`,
  wheels in `dist/`). The installers ship as GitHub Release
  assets, not committed binaries.

## Building from scratch

### Prerequisites

- **Python 3.11 or 3.12** on `PATH` (for building the wheel and
  running the version-substitution helper).
- **Inno Setup 6** — install with
  `winget install -e --id JRSoftware.InnoSetup` or download from
  <https://jrsoftware.org/isdl.php>.
- **PowerShell** (built into Windows 10/11 — used for the
  portable ZIP step via `Compress-Archive`).

### Build

From the repo root:

```
installer\build_installer.bat
```

Build steps (all five run sequentially in one command):

1. Build wheel + sdist via `python -m build`.
2. Stage runtime assets into `installer\stage\` (wheel, configs,
   docs PDFs, launcher templates, LICENSE, EULA).
3. Locate `ISCC.exe`.
4. Compile the installer to `release\DPSim-<version>-Setup.exe`.
5. Pack the portable ZIP to
   `release\DPSim-<version>-Windows-x64-portable.zip` (uses the
   same staged payload, wrapped with the EULA at the top level).

Build time: ≈ 30 s on a typical Windows 11 box.

Output sizes (typical):
- Setup.exe: ≈ 2.5 MB.
- Portable ZIP: ≈ 2.5 MB (same payload, slightly different
  packaging overhead).

## What the **installer** does when run

1. **EULA page** (the first user-facing page) — displays
   `LICENSE_AND_IP.txt`:
   - Intellectual property belongs to Holocyte Pty Ltd.
   - Software is licensed under GPL-3.0.
   - Source code: <https://github.com/tocvicmeng-prog/Downstream-Processing-Simulator>.
   The user must click *I accept the agreement* to continue.
2. **README page** — shows the quickstart `README.txt`.
3. **Install location** — default `%LOCALAPPDATA%\Programs\DPSim`
   (per-user). Picked deliberately so the post-install
   `install.bat` step can create `.venv\` without requiring admin
   elevation.
4. **Shortcuts options** — Start-Menu group (default), optional
   desktop shortcut.
5. **Python presence check** — if Python 3.11/3.12 is not on
   `PATH`, the installer offers to open
   <https://www.python.org/downloads/windows/> in the default
   browser before proceeding.
6. **File extraction** — wheel, configs, docs PDFs, launcher
   batch files, LICENSE, EULA.
7. **Post-install step** — runs the bundled `install.bat`, which:
   - creates a local `.venv\` in the install directory,
   - installs the wheel with the `[ui,optimization]` extras,
   - runs a smoke pipeline to verify.
   All bytes stay inside the install directory; no registry,
   system Python, or global state is touched beyond Inno Setup's
   standard uninstall record.
8. **Optional final action** — offer to open the First Edition
   PDF manual immediately.

## What the **portable ZIP** does when used

1. User extracts `DPSim-<version>-Windows-x64-portable.zip` to a
   folder of their choice (e.g. `D:\Apps\DPSim`).
2. User reviews `LICENSE_AND_IP.txt` (same content as the
   installer's EULA page) — the portable distribution does not
   gate execution on a click-through, but the file is shipped at
   the top of the unzipped folder so first-run users see it.
3. User double-clicks `install.bat` once. This:
   - creates a local `.venv\` in the unzipped folder,
   - pip-installs the bundled wheel + extras,
   - runs the smoke pipeline.
4. User double-clicks `launch_ui.bat` to start the Streamlit
   dashboard at `http://localhost:8501`.
5. To "uninstall," the user simply deletes the unzipped folder.
   No registry / Start-Menu / desktop trace.

## What the uninstaller does (installer path)

- Runs `rmdir /s /q "{app}\.venv"` to purge the virtual env.
- Removes every file the installer placed.
- Removes Start-Menu and desktop shortcuts.
- Leaves your user data and any files outside the install
  directory untouched.

## What is excluded from both artifacts ("clean" requirement)

The build pipeline guarantees that the staged payload contains
**only** runtime files. None of the following ever reach the
installer or the portable ZIP:

- `__pycache__/`, `*.pyc`, `*.pyo`
- `.git/`, `.github/`
- `tests/`, `docs/handover/`, `docs/decisions/` (development docs)
- `*.log`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`
- `pytest-cache-files-*/`, `pytest-of-*/`, `.dpsim_tmp/`
- `build/`, `dist/`, `*.egg-info/`
- Any IDE / editor metadata

Staging is done via explicit `copy /y` of named files only — there
is no recursive copy of the source tree, so no stray files can
slip through.

## Release process

1. Bump `pyproject.toml` and `src/dpsim/__init__.py` to the new
   version. Update `CHANGELOG.md`.
2. Run `installer\build_installer.bat` to produce both artifacts.
3. Smoke-test:
   - Right-click `release\DPSim-<version>-Setup.exe` → Run.
     Confirm EULA page renders Holocyte / GPL-3.0 / GitHub URL.
     Walk through to launch_ui.bat opens the dashboard.
   - Extract `release\DPSim-<version>-Windows-x64-portable.zip` to
     a temp folder; run `install.bat` then `launch_ui.bat`.
4. Tag the commit and push:
   ```
   git tag v<version>
   git push --tags
   ```
5. Publish via GitHub:
   ```
   gh release create v<version> ^
       release\DPSim-<version>-Setup.exe ^
       release\DPSim-<version>-Windows-x64-portable.zip ^
       --title "DPSim v<version>" ^
       --notes-file installer\templates\RELEASE_NOTES.md
   ```
6. Announce.

## Version-banner discipline

Every staged file (`install.bat`, `launch_ui.bat`, `launch_cli.bat`,
`uninstall.bat`, `README.txt`, `INSTALL.md`, `RELEASE_NOTES.md`,
`WHERE_ARE_THE_PROGRAM_FILES.txt`) carries the `__DPSIM_VERSION__`
placeholder where a literal version would otherwise live. The
build script reads `pyproject.toml`, extracts the `version`
field, and substitutes the placeholder in every staged template
before compiling the installer.

This keeps the version banner truthful across releases without
requiring the contributor to remember to bump strings in eight
different files. **Do not hardcode literal version strings into
the templates** — use the placeholder.
