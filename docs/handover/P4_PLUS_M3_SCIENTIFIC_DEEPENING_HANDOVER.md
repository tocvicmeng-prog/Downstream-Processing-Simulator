# P4+ M3 Scientific Deepening Handover

Date: 2026-04-25

## Scope

P4+ deepens the P4 method-level chromatography model. The system now goes beyond a method wrapper around breakthrough and adds:

- loaded-state Protein A elution initialized from the post-load bound profile
- column efficiency screening with plate count, HETP, asymmetry, and tracer width
- HCP/DNA/aggregate wash and co-elution screening
- Protein A cycling calibration hooks for alkaline degradation, leaching, and lifetime
- M3 UI support for a Protein A Method mode

## Main Files Changed

- `src/dpsim/module3_performance/transport/lumped_rate.py`
  - `LRMResult` now carries final axial `C`, `Cp`, and `q` profiles.
  - This makes the load-step bound profile available for downstream elution initialization.

- `src/dpsim/module3_performance/orchestrator.py`
  - `BreakthroughResult` now carries final axial profiles and axial grid metadata.

- `src/dpsim/module3_performance/method.py`
  - Added `LoadedStateElutionResult`.
  - Added `run_loaded_state_elution()`.
  - Added `ColumnEfficiencyReport` and `evaluate_column_efficiency()`.
  - Added `ImpurityClearanceReport`, `ImpuritySpeciesReport`, and `evaluate_impurity_clearance()`.
  - `ChromatographyMethodResult` now carries loaded elution, efficiency, and impurity reports.
  - Protein A performance now consumes loaded-elution recovery when available.

- `src/dpsim/lifecycle/orchestrator.py`
  - M3 graph diagnostics now include loaded-state elution recovery and mass balance, column plates/HETP/asymmetry/tailing, and impurity clearance risk.
  - Added M3 process-state calibration routing for Protein A cycling and elution model parameters.

- `src/dpsim/visualization/tabs/tab_m3.py`
  - Added `Protein A Method` UI mode.
  - UI can now run method-level Protein A chromatography and display loaded-state elution, cycle lifetime, asymmetry, HETP, and impurity risk.

- `tests/test_module3_method.py`
  - Added tests for loaded-state elution, efficiency, impurity clearance, and cycling calibration overrides.

- `tests/lifecycle/test_p4_m3_method.py`
  - Added lifecycle coverage for P4+ M3 graph diagnostics and M3 calibration routing.

## Loaded-State Elution

The previous P4 elution result was a scalar screening estimate. P4+ adds a dynamic elution solver:

1. The load step runs the existing LRM breakthrough model.
2. The final axial bound profile `q_profile_final` is passed to `run_loaded_state_elution()`.
3. The elution solver initializes `C=0`, `Cp=0`, and `q=q_profile_final`.
4. The inlet switches to protein-free low-pH elution buffer.
5. The model solves the same transport/film/pore/bound-state equations with pH-suppressed Protein A-IgG affinity.

The output includes:

- elution time profile
- outlet concentration
- UV signal
- pH profile
- initial bound mass
- eluted mass
- remaining bound mass
- recovery fraction
- elution peak time and width
- mass-balance error

## Column Efficiency

`evaluate_column_efficiency()` estimates:

- theoretical plate count
- HETP
- asymmetry factor
- tailing factor
- tracer residence time
- tracer half-height peak width

This is a screening estimate based on axial Peclet number, compression, and maldistribution risk. It does not replace tracer-pulse column qualification.

## Impurity Clearance

`evaluate_impurity_clearance()` adds first-pass wash/co-elution screening for:

- host-cell protein
- DNA
- aggregate

The model uses normalized impurity load fractions and first-order wash removal per column volume. This is deliberately conservative and must be replaced or calibrated with measured impurity concentrations in feed, wash, and elution fractions.

## Protein A Calibration Hooks

The lifecycle M3 process-state calibration map now recognizes:

- `protein_a_alkaline_rate_s_at_pH13`
- `protein_a_alkaline_degradation_rate_s`
- `protein_a_leaching_fraction_per_cycle`
- `protein_a_cycle_loss_fraction`
- `protein_a_cycle_lifetime_to_70pct`
- `protein_a_pH_transition`
- `protein_a_pH_steepness`
- `protein_a_elution_residual_activity`

These can be supplied as `CalibrationEntry` objects with `target_module="M3"`.

## UI Behavior

The M3 Streamlit tab now offers:

- `Breakthrough`
- `Gradient Elution`
- `Protein A Method`

Protein A Method mode exposes binding/wash pH, conductivity, wash duration, elution pH, elution conductivity, and elution duration. Results include elution recovery, cycle lifetime, asymmetry, impurity risk, pressure, plates, HETP, wash CV, and a loaded-state elution chromatogram.

## Scientific Boundaries

P4+ improves scientific continuity but remains a development simulator:

- Loaded-state elution is dynamic, but the Protein A pH-affinity model remains a screening model until calibrated.
- Column efficiency uses transport-derived estimates; real HETP/asymmetry requires tracer experiments.
- Impurity clearance uses normalized defaults until HCP/DNA/aggregate data are supplied.
- Protein A cycling/lifetime becomes calibration-aware, but true lifetime prediction requires multi-cycle resin data.

## Verification

Focused P4+ regression passed:

```text
132 passed, 8 warnings in 35.68s
```

Command:

```powershell
$env:TEMP='C:\Users\tocvi\DPSimTemp'; $env:TMP=$env:TEMP; $env:TMPDIR=$env:TEMP; $env:DPSIM_TMPDIR='C:\Users\tocvi\DPSimTemp'; $env:DPSIM_OUTPUT_DIR='C:\Users\tocvi\DPSimOutput\p4plus-focused'; $env:PYTHONIOENCODING='utf-8'; .\.venv\Scripts\python -m pytest -q -p no:cacheprovider --basetemp C:\Users\tocvi\DPSimTemp\pytest-p4plus-focused tests\test_module3_method.py tests\lifecycle\test_p4_m3_method.py tests\test_module3_breakthrough.py tests\test_ui_contract.py
```

## Recommended Next Work

1. Replace normalized impurity defaults with recipe-owned impurity feed concentrations and assay records.
2. Add an explicit tracer-pulse simulation and fit HETP/asymmetry from measured tracer data.
3. Add fraction collection logic for elution pooling, neutralization delay, and aggregate growth risk.
4. Add multi-cycle simulation across repeated load/wash/elute/CIP cycles.
5. Add recipe serialization for impurity and lifetime calibration sections.
