# P5 Calibration And Evidence Upgrade Handover

Date: 2026-04-25

## Scope

P5 extends the calibration system from simple M1/M3 reference means into a broader M2/M3 assay ingest and evidence-governance layer. The objective is to let wet-lab measurements enter DPSim as auditable `AssayRecord` objects, become uncertainty-carrying `CalibrationEntry` records, and then constrain lifecycle evidence claims when the simulated method leaves the fitted domain.

## Implemented Changes

### Assay Ingest Contract

- Added `AssayKind.PRESSURE_FLOW_CURVE`.
- Existing M2 assay kinds remain supported:
  - `LIGAND_DENSITY`
  - `ACTIVITY_RETENTION`
  - `LIGAND_LEACHING`
  - `FREE_PROTEIN_WASH_FRACTION`
- Existing M3 assay kinds now support both scalar and richer curve-style records:
  - `STATIC_BINDING_CAPACITY`
  - `DYNAMIC_BINDING_CAPACITY`
  - `PRESSURE_FLOW_CURVE`

### M2 Calibration

M2 functionalization ingest now uses replicate standard deviations when supplied. This preserves the prior `assay_reference_mean` behavior for ordinary replicate records, but upgrades to `weighted_assay_reference_mean` when per-replicate uncertainty is present.

Supported outputs:

- `functional_ligand_density`
- `activity_retention`
- `ligand_leaching_fraction`
- `free_protein_wash_fraction`

Each entry carries:

- `posterior_uncertainty`
- `valid_domain`
- source record IDs
- assay metadata such as pH, temperature, salt, and target molecule when available

### M3 Static Binding Calibration

Static binding capacity records now support weighted least-squares Langmuir fitting when at least three independent equilibrium concentrations are supplied.

Outputs from full isotherm records:

- `estimated_q_max`, units `mol/m3`
- `K_affinity`, units `m3/mol`

Fit method:

- `weighted_least_squares_langmuir`

Fallback behavior is preserved:

- A single static capacity record still emits `estimated_q_max` using `static_capacity_reference_mean`.
- Single-point `K_affinity` inversion still requires both equilibrium concentration and explicit qmax reference.

### M3 Breakthrough Calibration

Dynamic binding capacity ingest now accepts two wet-lab styles:

- Scalar DBC records with capacity replicates.
- Raw breakthrough curves with `time_s`, normalized `C_over_C0` or absolute outlet concentration, feed concentration, flow rate, and bed volume.

Raw curves are integrated as:

```text
DBC_x = C_feed * Q * integral(1 - C_out/C_feed) dt / V_bed
```

Default raw-curve thresholds:

- DBC5
- DBC10
- DBC50 when the curve reaches 50 percent breakthrough

Fit method:

- `breakthrough_curve_integration`

### M3 Pressure-Flow Calibration

Pressure-flow records fit a packed-bed hydraulic slope:

```text
deltaP = slope * flow_rate
```

Output:

- `pressure_flow_slope_Pa_per_m3_s`, units `Pa/(m3/s)`

Fit method:

- `weighted_least_squares_pressure_flow`

The lifecycle compares simulated pressure drop against this calibrated slope and emits `M3_PRESSURE_FLOW_REFERENCE_MISMATCH` when the relative mismatch exceeds 30 percent.

### Evidence And Domain Governance

Lifecycle M3 now applies calibration-domain gates:

- M3 calibration entries with `valid_domain` are checked against the simulated load-step method context.
- Extrapolation emits `M3_CALIBRATION_DOMAIN_EXTRAPOLATION`.
- Any M3 calibration-domain exit caps the M3 method manifest to `qualitative_trend`.
- M3 evidence is explicitly capped so it can never be stronger than the upstream M2 `FunctionalMediaContract`.

This is intentionally conservative. A calibrated qmax or isotherm parameter does not make the full packed-bed method validated unless the M2 media contract and M3 operating window also support that claim.

## Key Files

- `src/dpsim/assay_record.py`
- `src/dpsim/calibration/fitters.py`
- `src/dpsim/lifecycle/orchestrator.py`
- `src/dpsim/__main__.py`
- `tests/test_assay_record.py`
- `tests/test_validation_pipeline.py`
- `tests/lifecycle/test_p5_calibration_evidence.py`

## Verification

Focused regression:

```text
30 passed
```

Command used:

```powershell
$env:TEMP='C:\Users\tocvi\DPSimTemp'; $env:TMP=$env:TEMP; $env:TMPDIR=$env:TEMP; $env:DPSIM_TMPDIR='C:\Users\tocvi\DPSimTemp'; $env:DPSIM_OUTPUT_DIR='C:\Users\tocvi\DPSimOutput\p5-focused'; $env:PYTHONIOENCODING='utf-8'; .\.venv\Scripts\python -m pytest -q -p no:cacheprovider --basetemp C:\Users\tocvi\DPSimTemp\pytest-p5-focused3 tests\test_assay_record.py tests\test_validation_pipeline.py tests\lifecycle\test_p5_calibration_evidence.py
```

## Remaining Scientific Work

- Add Bayesian posterior fitting for richer calibration campaigns with enough replicate structure.
- Add explicit M2 recipe-domain checks once the M2 assay records are linked to resolved functionalization stage context.
- Extend pressure-flow calibration from a through-origin linear slope to nonlinear compressible-bed fitting when multi-pressure compression data are available.
- Add uncertainty propagation from calibration entries into M3 DBC and recovery intervals, not only evidence-tier and diagnostics.
- Add UI upload/inspection widgets for curve-style assay records.
