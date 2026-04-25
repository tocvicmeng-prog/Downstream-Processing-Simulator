# P0 Stabilization Handover

Date: 2026-04-25

## Scope

This pass stabilized the Downstream Processing Simulator fork for Python
3.12 development, inherited-suite execution, CI smoke gates, installer naming,
and runtime path hygiene.

## Runtime Environment

Validated interpreter:

- Python 3.12.13
- Virtual environment: `.venv`
- Project install: editable `downstream-processing-simulator[all]`

Local runtime directories used during validation:

- Temp: `C:\Users\tocvi\DPSimTemp`
- Cache: `C:\Users\tocvi\DPSimPipCache`
- Output: `C:\Users\tocvi\DPSimOutput`

The new `dpsim.runtime_paths` module centralizes runtime path policy. CLI,
tests, pipeline orchestrators, lifecycle orchestration, and optimization now
default to DPSim-owned output/temp/cache directories instead of source-tree
`output/`, root `/tmp`, or fragile OneDrive/AppData temp locations.

## Branding And Packaging

Remaining old application branding was removed from UI-facing text, CLI help,
installer scripts, release notes, manual PDF builder metadata, validation data
schemas, and documentation. The only remaining old-name match found by search
is the literal parent folder name in the local Windows path.

Installer updates:

- Inno script renamed to `installer/DPSim.iss`.
- Installer version fallback set to `0.1.0`.
- Wheel lookup corrected to
  `downstream_processing_simulator-<version>-py3-none-any.whl`.
- Installer launch scripts export `DPSIM_TMPDIR`, `DPSIM_CACHE_DIR`,
  `DPSIM_OUTPUT_DIR`, `TEMP`, `TMP`, `TMPDIR`, `PIP_CACHE_DIR`, and
  `MPLCONFIGDIR`.

## CI Gates

`.github/workflows/ci.yml` now defines:

- Python 3.11/3.12 P0 smoke gate job.
- Clean architecture test gate.
- M2 functionalization workflow gate.
- M3 breakthrough gate.
- M1 legacy CLI run gate.
- DPSim lifecycle CLI gate.
- Python 3.12 full inherited-suite job with `[all]` dependencies.

Both jobs configure temp/cache/output directories under `RUNNER_TEMP`.

## Numerical Stabilization

Three inherited numerical paths blocked the full inherited suite under the
clean Python 3.12 runtime:

1. M3 LRM transport:
   - LSODA stalled on high-affinity Langmuir and gradient-related cases.
   - The solver now uses BDF for the stiff chromatography semi-discretization.

2. M1 fixed-pivot PBE:
   - BDF spent too long in dense LU factorization for the inherited 30-bin
     smoke fixture.
   - The PBE solver now uses LSODA, which completed the same fixture quickly
     while preserving expected trends and full test behavior.

3. L2 2D Cahn-Hilliard solver:
   - Repeated SuperLU factorization could stall on the 32 x 32 smoke grid.
   - The solver keeps direct LU only for tiny systems and uses an iterative
     sparse solve after operator rebuilds for normal smoke grids.
   - The physical reported domain remains the represented droplet
     cross-section, while the internal numerical RVE is capped for stable
     Windows SciPy execution.

## Verification

Executed successfully under Python 3.12.13:

```powershell
python -m pytest -q tests/core/test_clean_architecture.py -p no:cacheprovider
python -m pytest -q tests/test_module2_workflows.py tests/test_module3_breakthrough.py -p no:cacheprovider
python -m pytest -q tests/test_gradient_lrm.py -p no:cacheprovider
python -m pytest -q tests/test_level1_emulsification.py -p no:cacheprovider
python -m pytest -q tests/test_level2_gelation.py -p no:cacheprovider
python -m pytest -q -p no:cacheprovider --basetemp C:\Users\tocvi\DPSimTemp\pytest-full
python -m dpsim run configs/fast_smoke.toml --quiet --output C:\Users\tocvi\DPSimOutput\m1-final
python -m dpsim lifecycle configs/fast_smoke.toml --quiet --output C:\Users\tocvi\DPSimOutput\lifecycle-final
```

Full inherited-suite result:

- `1025 passed`
- `2 xfailed`
- `39 warnings`
- Runtime: `446.27 s`

Smoke lifecycle result:

- weakest evidence tier: `qualitative_trend`
- M2 ligand: `Protein A`
- M3 DBC10: `0.706 mol/m3 column`
- M3 pressure drop: `37.12 kPa`
