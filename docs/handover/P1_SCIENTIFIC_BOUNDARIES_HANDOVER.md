# P1 Scientific Boundaries Handover

Date: 2026-04-25

## Scope

This pass starts P1 by making the clean wet-lab `ProcessRecipe` the authoritative
source for lifecycle M1/M2/M3 process inputs and by adding backend validation
gates for units, reagent domains, column mechanics, site balance, and model
domain extrapolation.

## Key Changes

- Added `dpsim.lifecycle.recipe_resolver`.
  - Registers recipe `Quantity` values into `ParameterProvider`.
  - Resolves stable `ResolvedParameter` names such as `M1.emulsify.rpm`,
    `M2.<step>.pH`, `M3.pack_column.bed_height`, and `M3.load.flow_rate`.
  - Converts recipe values into legacy `SimulationParameters`, M2
    `ModificationStep` objects, M3 `ColumnGeometry`, and breakthrough inputs.

- Expanded the default affinity-media recipe.
  - M1 rpm now uses explicit `rpm` units.
  - M2 includes activation, wash, Protein A coupling, wash, quench, and final wash.
  - M2 reagent concentrations and quench temperature are explicit recipe inputs.
  - M3 flow, feed duration, and total simulation time are explicit recipe inputs.

- Extended unit support in `Quantity`.
  - Added `rpm`, `1/s`, `1/min`, `kg/m3`, `g/L`, and `mg/mL`.

- Added validation gates.
  - Unit consistency for recipe-owned parameters.
  - pH, temperature, reagent identity, and reagent-profile domain warnings.
  - M1 and M2 contract unit/range validation.
  - M2 ACS site-balance validation.
  - M3 pressure target, pump pressure limit, compression limit, and mass balance.
  - Model/calibration-domain warnings from `ModelManifest.valid_domain`.

- Extended result provenance.
  - `DownstreamLifecycleResult` now exposes `resolved_parameters`.
  - `ResultNode` now carries `wet_lab_caveats`.
  - `ResultGraph.as_summary()` includes manifest evidence tier, calibration ref,
    validity domain, assumptions, diagnostics, and caveats.

- Added recipe artifact I/O.
  - `dpsim.core.recipe_io` round-trips `ProcessRecipe` as JSON or TOML.
  - `recipe_from_simulation_parameters()` bridges legacy M1 config/UI inputs
    into a recipe while M2/M3 controls migrate.
  - CLI now supports `dpsim recipe export-default`, `dpsim recipe validate`,
    `dpsim lifecycle --recipe <path>`, `--export-recipe`, and `--no-dsd`.

## Scientific Interpretation

The lifecycle path is now auditable from recipe value to solver input. A future
developer can inspect `result.resolved_parameters` to see which wet-lab value
set a solver field, including unit and source provenance.

The new gates do not claim GMP readiness. They separate:

- hard blockers, such as impossible units, invalid pH ranges, negative reagent
  concentrations, contract unit failures, severe column pressure/compression
  failures, and broken site balance;
- warning-level scientific limits, such as reagent operation outside profile
  pH/temperature windows or model use outside declared validity domains.

## Verification

Targeted P1 tests:

```powershell
$env:TEMP='C:\Users\tocvi\DPSimTemp'
$env:TMP=$env:TEMP
$env:TMPDIR=$env:TEMP
$env:DPSIM_TMPDIR='C:\Users\tocvi\DPSimTemp'
$env:DPSIM_OUTPUT_DIR='C:\Users\tocvi\DPSimOutput\p1-tests'
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python -m pytest -q -p no:cacheprovider --basetemp C:\Users\tocvi\DPSimTemp\pytest-p1 tests\core\test_clean_architecture.py tests\lifecycle\test_p1_scientific_boundaries.py
```

Result:

- `10 passed in 4.94s`

Nearby M1/M2/M3 regression tests:

```powershell
.\.venv\Scripts\python -m pytest -q -p no:cacheprovider --basetemp C:\Users\tocvi\DPSimTemp\pytest-p1-nearby-2 tests\test_smoke.py tests\test_module2_workflows.py tests\test_module3_breakthrough.py
```

Result:

- `77 passed, 7 warnings in 60.59s`

The warnings are existing M3 mass-balance caution warnings in breakthrough
unit tests and are expected by the current inherited test suite.

Full inherited suite:

```powershell
.\.venv\Scripts\python -m pytest -q -p no:cacheprovider --basetemp C:\Users\tocvi\DPSimTemp\pytest-full-p1
```

Result:

- `1029 passed, 2 xfailed, 39 warnings in 378.31s`

Recipe I/O and CLI continuation:

```powershell
.\.venv\Scripts\python -m pytest -q -p no:cacheprovider --basetemp C:\Users\tocvi\DPSimTemp\pytest-p1-recipe tests\core\test_process_recipe_io.py
.\.venv\Scripts\python -m pytest -q -p no:cacheprovider --basetemp C:\Users\tocvi\DPSimTemp\pytest-p1-recipe-cli tests\test_cli_v7.py
.\.venv\Scripts\python -m pytest -q -p no:cacheprovider --basetemp C:\Users\tocvi\DPSimTemp\pytest-p1-recipe-core-2 tests\core tests\lifecycle\test_p1_scientific_boundaries.py
```

Results:

- `4 passed in 0.26s`
- `13 passed in 23.89s`
- `14 passed in 2.95s`

Direct CLI smoke:

```powershell
.\.venv\Scripts\python -m dpsim lifecycle configs\fast_smoke.toml --no-dsd --quiet --output C:\Users\tocvi\DPSimOutput\p1-recipe\lifecycle-export --export-recipe C:\Users\tocvi\DPSimOutput\p1-recipe\bridged_recipe.toml
.\.venv\Scripts\python -m dpsim recipe validate C:\Users\tocvi\DPSimOutput\p1-recipe\bridged_recipe.toml
```

Observed:

- Lifecycle completed with DBC10 `0.706 mol/m3 column`, pressure drop `37.12 kPa`,
  and mass balance error `0.00%`.
- Exported bridged recipe validated cleanly: `steps: 11`,
  `resolved parameters: 46`, `validation: ok`.

Full inherited suite after recipe I/O continuation:

```powershell
.\.venv\Scripts\python -m pytest -q -p no:cacheprovider --basetemp C:\Users\tocvi\DPSimTemp\pytest-full-p1-recipe
```

Result:

- `1035 passed, 2 xfailed, 39 warnings in 433.75s`

## Remaining P1 Work

- Move Streamlit M1/M2/M3 forms from the legacy bridge toward emitting
  `ProcessRecipe` directly.
- Add recipe editing/download/upload controls in the UI using `dpsim.core.recipe_io`.
- Expand manifest-domain checks beyond pH/temperature into calibrated kinetic,
  mass-transfer, and chromatography fitting domains as calibration records grow.
- Add stricter lifecycle behavior for blockers when running in production mode.
- Add wet-lab assay records as first-class evidence inputs for upgrading
  Protein A capacity from ranking-only to calibrated local evidence.
