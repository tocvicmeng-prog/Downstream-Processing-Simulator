# P2 M1 DSD And Washing Handover

Date: 2026-04-25

## Scope

This pass starts P2 by improving M1 microsphere-fabrication handoff fidelity.
The main change is that the M1-to-M2 contract no longer exposes only d50/d32.
It now carries the full bead-size distribution, volume-weighted quantile
transfer helpers, wet-lab calibration hooks, and explicit screening fields for
oil/surfactant carryover after washing. A continuation pass replaced the first
fixed carryover constants with a recipe-owned well-mixed extraction model. A
second continuation wires calibrated wash parameters and carryover limits into
the lifecycle M2/M3 validation gates. A scientific-perfection continuation adds
adaptive DSD-bin propagation, M1 physical-QC assay ingest, and M3 static/DBC
calibration ingest.

## Key Changes

- Added `BeadSizeDistributionPayload` in `src/dpsim/datatypes.py`.
  - Stores diameter bins, number density, normalized volume fractions, CDF,
    d10/d32/d43/d50/d90/span, source, evidence tier, and calibration hooks.
  - Provides `quantile_diameter()` and `quantile_table()` for downstream
    DSD transfer.
  - Validates finite positive diameters, non-negative density, monotonic CDF,
    and physical total volume fraction.

- Extended `M1ExportContract`.
  - Added `bead_size_distribution`.
  - Added `calibration_hooks` covering DSD, pore structure, swelling,
    mechanics, and wash residuals.
  - Added `oil_removal_efficiency`, `residual_oil_volume_fraction`,
    `residual_surfactant_concentration_kg_m3`, and `washing_assumptions`.
  - Added `washing_model`, carrying the model inputs, per-cycle removal,
    residual outputs, assumptions, warnings, and model manifest.
  - Extended `validate_units()` to include the DSD payload and wash residuals.

- Updated M1 export in `src/dpsim/pipeline/orchestrator.py`.
  - Builds a distribution payload from the PBE output.
  - Uses the formulation dispersed-phase fraction as the physical contract
    `total_volume_fraction`, because the inherited PBE internal total-volume
    scalar is not a clean release-ready fraction in all smoke configurations.
  - Calls `solve_m1_washing()` instead of using hard-coded carryover constants.
  - Records assumptions requiring replacement or calibration from residual
    oil/surfactant assays.

- Added `src/dpsim/level1_emulsification/washing.py`.
  - Implements `M1.washing.well_mixed_extraction`.
  - Inputs are `initial_oil_carryover_fraction`, `wash_cycles`,
    `wash_volume_ratio`, `wash_mixing_efficiency`, `oil_retention_factor`, and
    `surfactant_retention_factor`.
  - Each wash is treated as a drain/resuspend extraction stage:
    `mixing_efficiency * wash_volume_ratio / (wash_volume_ratio + retention)`.
  - Evidence tier is `qualitative_trend` until retention factors are fitted.

- Updated lifecycle DSD propagation in `src/dpsim/lifecycle/orchestrator.py`.
  - The DSD screen now consumes `m1_contract.bead_size_distribution` when
    available.
  - DSD diagnostics now include source, bin count, and d10/d50/d90.
  - Added adaptive DSD mode. When runtime allows, the lifecycle can use every
    non-zero DSD volume-fraction bin; otherwise it collapses the DSD to a
    bounded number of volume-probability representatives.
  - DSD summaries now report weighted p50/p95 pressure drop, weighted p50/p95
    bed compression, and weighted p05/p50/p95 capacity estimates.
  - Added opt-in DSD-resolved M3 LRM breakthrough with `dsd_run_breakthrough`
    / `--dsd-breakthrough`. When enabled, each DSD representative receives a
    per-representative DBC5/DBC10/DBC50 and mass-balance error, and the summary
    reports weighted DBC10 mean/p05/p50/p95 plus worst mass-balance error.
  - M1 result graph caveats now explicitly call out DSD, pore, swelling,
    mechanics, and wash-residual wet-lab requirements.

- Updated lifecycle CLI output in `src/dpsim/__main__.py`.
  - Prints M1 DSD bin count and d10/d50/d90.
  - Prints modeled oil carryover and surfactant residuals.
  - Prints wash cycles, wash volume ratio, and modeled oil-removal efficiency.

- Expanded wet-lab assay vocabulary in `src/dpsim/assay_record.py`.
  - Added `swelling_ratio`.
  - Added `compression_modulus`.
  - Added `residual_oil`.
  - Added `residual_surfactant`.

- Strengthened default recipe QC in `src/dpsim/core/process_recipe.py`.
  - M1 emulsification now requires measured DSD quantile archiving.
  - M1 gel/wash now requires pore imaging or SEC inverse-size calibration,
    swelling ratio, compression/modulus testing, and residual oil/surfactant
    assays.
  - M1 gel/wash now owns wash-model inputs as `Quantity` values.

- Updated recipe resolution in `src/dpsim/lifecycle/recipe_resolver.py`.
  - Routes M1 wash inputs through `ParameterProvider`.
  - Adds validation blockers for impossible wash fractions, negative cycles,
    negative wash volume, and non-positive retention factors.

- Added M1 wash calibration ingest.
  - `fit_m1_washing_to_calibration_entries()` consumes `RESIDUAL_OIL` and
    `RESIDUAL_SURFACTANT` `AssayRecord`s.
  - It inverts the well-mixed extraction model and emits
    `target_module="M1"` entries for `m1_oil_retention_factor` and
    `m1_surfactant_retention_factor`.
  - `dpsim ingest M1` now writes CalibrationStore-compatible fit JSON.
  - `data/validation/m1_washing/schema.json` documents the required assay
    conditions and units.

- Added M1 physical-QC ingest.
  - `fit_m1_physical_qc_to_calibration_entries()` consumes `PORE_SIZE`,
    `POROSITY`, `SWELLING_RATIO`, `BULK_MODULUS`, and `COMPRESSION_MODULUS`
    `AssayRecord`s.
  - `dpsim ingest M1QC` writes reference `CalibrationEntry` objects using
    `fit_method="assay_reference_mean"`.
  - `data/validation/m1_physical_qc/schema.json` documents the accepted assay
    records and units.

- Added M3 binding and breakthrough calibration ingest.
  - `fit_m3_binding_to_calibration_entries()` consumes
    `STATIC_BINDING_CAPACITY` and `DYNAMIC_BINDING_CAPACITY` `AssayRecord`s.
  - Static binding records emit `estimated_q_max` entries for
    `target_module="M3"`.
  - Dynamic binding records emit threshold-specific `dbc_5_reference`,
    `dbc_10_reference`, or `dbc_50_reference` entries for measured-vs-simulated
    breakthrough diagnostics.
  - `K_affinity` is emitted only when the assay record includes both an
    equilibrium liquid concentration and an explicit qmax reference, avoiding
    underdetermined single-point Langmuir fitting.
  - `dpsim ingest M3` writes CalibrationStore-compatible fit JSON.
  - `data/validation/m3_binding/schema.json` documents the accepted capacity,
    DBC, units, and molecular-weight metadata needed for mass-to-molar
    conversion.

- Extended uncertainty propagation.
  - `PipelineOrchestrator.run_single()` applies `target_module="M1"`
    calibration entries to `FormulationParameters`.
  - `UnifiedUncertaintyEngine` dispatches M1 calibration posteriors into
    `FormulationParameters`.
  - Unified uncertainty output now includes `residual_oil_volume_fraction` and
    `residual_surfactant_concentration`.

- Added downstream carryover validation gates.
  - `TargetProductProfile` now owns `max_residual_oil_volume_fraction` and
    `max_residual_surfactant_concentration` as `Quantity` values.
  - `recipe_resolver` routes these target limits through `ParameterProvider`.
  - `DownstreamProcessOrchestrator.run()` accepts `RunContext`, passes it into
    the M1 pipeline, and continues with the calibrated `m1_result.parameters`.
  - M1/M2/M3 graph nodes now carry residual-limit diagnostics.
  - Lifecycle validation emits `M1_RESIDUAL_OIL_CARRYOVER` and
    `M1_RESIDUAL_SURFACTANT_CARRYOVER` warnings/blockers when wash residuals
    exceed recipe targets.

- Wired M3 calibration into lifecycle execution.
  - `RunContext(calibration_store=...)` is now consumed by
    `DownstreamProcessOrchestrator.run()` after M2 builds the
    FunctionalMediaContract and before M3 breakthrough.
  - `estimated_q_max`/`q_max` entries calibrate the FMC capacity field and
    mark `q_max_confidence="calibrated"`.
  - `K_affinity`/`K_L` entries are passed through M3 process state so the
    selected Langmuir isotherm uses measured affinity constants.
  - DSD representative FMCs receive the same capacity calibration, and
    DSD-resolved breakthrough receives the same M3 process state.
  - M3 graph diagnostics now include measured DBC references and signed
    relative error against simulated DBC5/DBC10/DBC50.

- Wired M1 physical-QC references into lifecycle handoffs where the mapping is
  direct.
  - `measured_pore_size_mean` and `measured_porosity` condition the
    M1-to-M2 contract before M2 surface-area and ligand-capacity estimates.
  - `measured_compression_modulus` conditions the M3 packed-bed mechanical
    state through `FunctionalMicrosphere.E_star_updated`.
  - `measured_swelling_ratio` and `measured_bulk_modulus` remain explicit graph
    diagnostics only, because no validated direct mapping to the current M1/M3
    contract fields exists yet.
  - Lifecycle validation emits informational `M1_PHYSICAL_QC_APPLIED` and
    `M3_PHYSICAL_QC_APPLIED` issues, plus warning-level
    `M1_PHYSICAL_QC_SHIFT` when measured pore/porosity values strongly shift
    the uncorrected M1 prediction.

## Scientific Interpretation

The simulator still does not run a full population of particles through every
M2 and M3 equation. Instead, it now exposes the full M1 DSD as a first-class
contract object and uses volume-weighted quantiles for downstream transfer.
That is the correct next step because chromatography hydraulics and capacity
depend strongly on particle volume and diameter, while a single d50 hides
pressure-drop and packing risks.

The washing fields are intentionally labeled as qualitative. They make residual
oil and surfactant visible to downstream modules and responsive to actual wash
operations, but they are not a release-quality leachables model. Real process
use still requires residual oil/surfactant assays and calibration of the oil
and surfactant retention factors. The lifecycle carryover gates are
process-development thresholds, not GMP release specifications.

## Verification

Focused P2 test slice:

```powershell
$env:TEMP='C:\Users\tocvi\DPSimTemp'
$env:TMP=$env:TEMP
$env:TMPDIR=$env:TEMP
$env:DPSIM_TMPDIR='C:\Users\tocvi\DPSimTemp'
$env:DPSIM_OUTPUT_DIR='C:\Users\tocvi\DPSimOutput\p2-m1'
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python -m pytest -q -p no:cacheprovider --basetemp C:\Users\tocvi\DPSimTemp\pytest-p2-m1 tests\lifecycle\test_p2_m1_dsd_contract.py tests\test_assay_record.py tests\test_unit_assertions.py tests\core\test_clean_architecture.py
```

Result:

```text
29 passed in 5.21s
```

Extended lifecycle, recipe, and CLI slice:

```text
50 passed in 42.52s
```

Downstream-impact slice covering batch variability, M2 contract consumers,
M3 breakthrough, and v6.0 integration:

```text
128 passed, 7 warnings in 34.25s
```

The 7 warnings are pre-existing M3 LRM mass-balance warnings in
`tests/test_module3_breakthrough.py`; the tests intentionally allow them.

P2 wash-model continuation slices:

```text
44 passed in 30.82s
167 passed, 7 warnings in 66.27s
```

P2 wash-calibration continuation slices:

```text
43 passed in 35.09s
44 passed in 31.12s
187 passed, 7 warnings in 90.81s
```

P2 downstream carryover continuation slice:

```text
39 passed in 20.28s
235 passed, 7 warnings in 73.17s
```

P2 adaptive DSD / physical-QC continuation slice:

```text
19 passed in 48.16s
48 passed in 50.01s
240 passed, 7 warnings in 124.22s
22 passed in 66.95s
242 passed, 7 warnings in 104.42s
```

P2 remaining calibration closure:

```text
39 passed in 90.88s
1059 passed, 2 xfailed, 39 warnings in 409.33s
40 passed in 59.53s
1060 passed, 2 xfailed, 39 warnings in 276.07s
```

## Remaining P2 Work

- Extend measured DBC comparison from lifecycle diagnostics into optimizer
  objective penalties once target-specific acceptance windows are agreed.
