# Initial Handover: Downstream Processing Simulator Fork

Date: 2026-04-25  
Location: `C:\Users\tocvi\OneDrive\文档\Project_Code\EmulSim\Downstream Processing Simulator`

## What Was Created

This folder is a new local fork of the upstream microsphere simulation project. The
fork is renamed to **Downstream Processing Simulator** and the Python package is
renamed to `dpsim`.

The implementation keeps the mature inherited solver stack and adds the
first clean-slate lifecycle architecture layer requested by the project owner.

## New Files

Core architecture:

- `src/dpsim/core/__init__.py`
- `src/dpsim/core/quantities.py`
- `src/dpsim/core/parameters.py`
- `src/dpsim/core/process_recipe.py`
- `src/dpsim/core/validation.py`
- `src/dpsim/core/result_graph.py`
- `src/dpsim/core/evidence.py`
- `src/dpsim/core/model_registry.py`

Lifecycle orchestration:

- `src/dpsim/lifecycle/__init__.py`
- `src/dpsim/lifecycle/orchestrator.py`

Documentation:

- `README.md`
- `docs/DPS_CLEAN_SLATE_ARCHITECTURE.md`
- `docs/INDEX.md`
- `docs/handover/INITIAL_HANDOVER.md`

Tests:

- `tests/core/test_clean_architecture.py`

Key modified files:

- `pyproject.toml`
- `src/dpsim/__init__.py`
- `src/dpsim/__main__.py`
- `src/dpsim/module2_functionalization/modification_steps.py`
- `src/dpsim/module2_functionalization/orchestrator.py`
- `src/dpsim/module3_performance/orchestrator.py`

## Important Existing Code Reused

- `src/dpsim/pipeline/orchestrator.py`: M1 fabrication pipeline.
- `src/dpsim/module2_functionalization/`: ACS and functionalization workflows.
- `src/dpsim/module3_performance/`: chromatography/catalysis performance.
- `src/dpsim/calibration/`: calibration data model and store.
- `src/dpsim/datatypes.py`: legacy dataclasses, evidence tiers, and M1/M2 contracts.

## Current Lifecycle Path

The new CLI command is:

```bash
python -m dpsim lifecycle configs/fast_smoke.toml
```

It runs:

1. M1 fabrication using `PipelineOrchestrator`.
2. M1 export through `M1ExportContract`.
3. M2 functionalization using:
   - ECH activation of hydroxyl groups;
   - modeled wash after activation;
   - Protein A coupling;
   - modeled wash after coupling;
   - ethanolamine quench;
   - modeled final wash.
4. M2 export through `FunctionalMediaContract`.
5. M1 DSD quantile propagation into M2 capacity and M3 pressure/compression
   sensitivity screening.
6. M3 breakthrough using `run_breakthrough` and the M2 media contract.
7. Evidence and validation roll-up through `ResultGraph` and `ValidationReport`.

## Scientific Caveats

- Protein A capacity is ranking-only until calibrated with target-specific
  binding or breakthrough data.
- The lifecycle pathway now propagates representative DSD quantiles, but it is
  still a screening model. It does not yet run full LRM breakthrough for every
  DSD bin.
- Washing is modeled as advisory diffusion-out residual tracking. It is not a
  substitute for validated residual/leachables assays.
- The inherited UI still contains legacy-era language and should be refactored
  after backend lifecycle objects stabilize.
- Stale copied egg-info metadata from the source project was removed.
- `pyproject.toml` intentionally keeps the inherited Python policy
  `>=3.11,<3.13`. The local `python` command used during validation reported
  Python 3.14.3, so checks were run from the source tree with `PYTHONPATH=src`.
  Use a Python 3.11 or 3.12 environment for editable installation.

## Next Developer Tasks

1. Calibrate M2 washing against wash-volume, conductivity/UV/free-ligand, and
   residual-reactive-group assays.
2. Run full M3 breakthrough or method simulations per DSD quantile when the
   decision depends on pressure, mass transfer, or classification/sieving.
3. Add `PerformanceRecipe` and method simulation for equilibrate/load/wash/elute.
4. Add M3 gradient elution evidence inheritance from `FunctionalMediaContract`.
5. Extend calibration ingest to M2 ligand-density assays and M3 breakthrough.
6. Migrate Streamlit UI from legacy M1/M2/M3 tabs to `ProcessRecipe` and
   `ResultGraph`.
7. Clean installer branding once the fork is stable.

## Verification Performed

The following validation commands were run successfully from the fork root:

```powershell
$env:PYTHONPATH = "src"
python -m pytest -q tests/core/test_clean_architecture.py -p no:cacheprovider
python -m pytest -q tests/test_module2_workflows.py tests/test_module3_breakthrough.py -p no:cacheprovider
python -m dpsim lifecycle configs/fast_smoke.toml --quiet
python -m dpsim run configs/fast_smoke.toml --quiet
```

Observed lifecycle smoke result:

- weakest evidence tier: `qualitative_trend`
- M1 bead d50: `18.99 um`
- M1 pore size: `180.9 nm`
- M2 ligand: `Protein A`
- M3 DBC10: `0.706 mol/m3 column`
- M3 pressure drop: `37.12 kPa`
- M3 mass-balance error: `0.00%`
- DSD screen: `3` quantiles, pressure-drop range `13.65-113.63 kPa`
- structured validation warnings include M1 crosslinker limitation,
  phenomenological modulus caveat, DSD pressure-spread risk, and M3 bed
  compression above 20%.

Additional inherited-suite check attempted:

```powershell
$env:PYTHONPATH = "src"
python -m pytest -q -m "not slow" -p no:cacheprovider --basetemp .pytest_tmp
```

This broader run selected 987 inherited non-slow tests and reached the end of
collection/execution, but it is not a clean acceptance gate in the current
sandbox because pytest and several inherited tests could not create or inspect
temporary directories (`AppData\Local\Temp`, `.pytest_tmp`, and Windows
root-style `/tmp` paths). The visible non-temp failures in that broad attempt
were also output-directory permission failures, not assertion mismatches in the
new lifecycle code. The focused architecture tests and M1/M2/M3 smoke commands
above are the accepted verification for this fork handover.
