# DPSim __DPSIM_VERSION__ — Release Notes

**Release date:** __DPSIM_RELEASE_DATE__
**Platform:** Windows 11 x64 (Windows 10 x64 also supported)
**Python:** 3.11 or 3.12 (3.13+ unsupported per ADR-001)

This release of the **Downstream Processing Simulator** (DPSim) ships
both an MSI-style one-click **installer**
(`DPSim-__DPSIM_VERSION__-Setup.exe`) and a **portable ZIP**
(`DPSim-__DPSIM_VERSION__-Windows-x64-portable.zip`) of the same
payload.

---

## What's new in this release

For per-version highlights, see the GitHub Release notes:
<https://github.com/tocvicmeng-prog/Downstream-Processing-Simulator/releases/tag/v__DPSIM_VERSION__>

For the cumulative changelog across all releases, see
[`CHANGELOG.md`](https://github.com/tocvicmeng-prog/Downstream-Processing-Simulator/blob/main/CHANGELOG.md)
in the source repository.

DPSim's stable user-facing surfaces (covered in the bundled First
Edition manual) are:

- **21 polymer families** across the v9.1 baseline, v9.2/v9.3
  expansion, v9.4 niche set, and v9.5 multi-variant composites.
- **103 reagents** in **18 chemistry buckets** on the M2 page,
  including the v0.5.0 ACS-Converter epic and v0.5.1 deferred-work
  follow-on.
- **13 ion-gelant profiles** (per-family + freestanding) with
  biotherapeutic-safety flags.
- **Lumped Rate Model (LRM)** chromatography solver with optional
  Monte-Carlo uncertainty driver and Bayesian posterior fitting
  (`dpsim[bayesian]` extra).
- **Streamlit dashboard** at `localhost:8501` with seven-step
  lifecycle workflow, per-module result panels, validation report,
  evidence ladder, and run history.
- **CFD-PBE zonal coupling** (v0.6.2+) — schema-v1.0 zone
  partitioning with per-zone breakage / coalescence ε, OpenFOAM
  case dictionaries for both stirrer geometries, and a
  `dpsim cfd-zones` CLI.

---

## Installer features

- **EULA-first wizard** — the very first installer page shows the
  intellectual-property + GPL-3.0 + GitHub-source statement
  (`LICENSE_AND_IP.txt`). User must accept before any files are
  written.
- **Per-user install** — default location is
  `%LOCALAPPDATA%\Programs\DPSim`. No admin elevation required;
  the post-install `install.bat` step can create the local
  `.venv\` without privilege escalation.
- **Python presence check** — if Python 3.11/3.12 is not on
  PATH, the wizard offers to open the python.org Windows download
  page in your default browser before installing.
- **Optional Start-Menu group + desktop shortcut** —
  user-selectable in the Tasks page.
- **Bundled documentation** — both the First Edition manual and
  Appendix J ship as PDFs in `docs\`. They are also reachable via
  the upper-right corner of the Streamlit dashboard.
- **Clean uninstaller** — removes `.venv\` plus every file the
  installer placed. Leaves user data and any files outside the
  install directory untouched.

## Portable ZIP features

For users who prefer unzip-and-run:

- Same payload as the installer (wheel, configs, docs, launchers,
  EULA, LICENSE).
- Extracts to a self-contained `DPSim-X.Y.Z-Windows-x64\` folder.
- Run `install.bat` once inside the unzipped folder to create the
  `.venv\` and pip-install the bundled wheel.
- Run `launch_ui.bat` to start the Streamlit dashboard.
- Delete the folder to remove (no Start Menu / registry footprint
  to clean up).

## System requirements

- Windows 11 x64 (Windows 10 x64 also supported).
- Python 3.11 or 3.12.
- 2 GB free disk for the local `.venv\`.
- 8 GB RAM recommended (4 GB minimum).
- Internet during first install (downloads dependencies from PyPI).

## Source code

The canonical source-code repository is published on GitHub at
<https://github.com/tocvicmeng-prog/Downstream-Processing-Simulator>.
Each tagged release is available under the **Releases** tab.

## Licence

GNU General Public License v3.0 (GPL-3.0). Full text in
`LICENSE.txt`. Intellectual property in this software belongs to
**Holocyte Pty Ltd**. By installing or using DPSim you accept the
GPL-3.0 terms.
