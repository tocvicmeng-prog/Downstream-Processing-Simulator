# P4 M3 Chromatography Operation Handover

Date: 2026-04-25

## Scope

P4 expands M3 from a single breakthrough-only screen into a method-level Protein A chromatography operation. The lifecycle now represents the practical wet-lab sequence:

1. Pack column
2. Equilibrate column
3. Load IgG feed
4. Wash unbound protein
5. Elute bound IgG

The existing LRM breakthrough solver is preserved and used for the dynamic load step. The new method layer wraps it with recipe-owned buffer conditions, step flow rates, residence-time checks, column operability diagnostics, and Protein A performance screens.

## Main Files Added Or Changed

- `src/dpsim/module3_performance/method.py`
  - New method-level M3 dataclasses and orchestration.
  - Adds `ChromatographyOperation`, `BufferCondition`, `ChromatographyMethodStep`, `ChromatographyMethodResult`, `ColumnOperabilityReport`, and `ProteinAPerformanceReport`.
  - Adds `run_chromatography_method()`.
  - Adds `evaluate_column_operability()` and `evaluate_protein_a_performance()`.

- `src/dpsim/core/process_recipe.py`
  - Default recipe now includes explicit M3 pack, equilibrate, load, wash, and elute steps.
  - M3 recipe parameters include bed height, column diameter, bed porosity, pH, conductivity, flow rate, feed concentration, residence-time target, and pH-gradient metadata.

- `src/dpsim/lifecycle/recipe_resolver.py`
  - Resolver now emits typed `m3_method_steps` from `ProcessRecipe`.
  - M3 parameters still pass through `Quantity`, `ResolvedParameter`, and `ParameterProvider`.
  - Added unit checks for M3 conductivity, method duration, residence time, column diameter, bed porosity, and elution pH gradient fields.

- `src/dpsim/lifecycle/orchestrator.py`
  - Lifecycle now calls `run_chromatography_method()`.
  - `DownstreamLifecycleResult.m3_method` carries the full M3 method result.
  - `DownstreamLifecycleResult.m3_breakthrough` remains the load-step breakthrough result for backward compatibility.
  - M3 graph node now reports method steps, operability limits, Protein A binding/isotherm metrics, mass-transfer resistance, alkaline degradation, cycle lifetime, and leaching risk.

- `src/dpsim/module3_performance/__init__.py`
  - Exports the new method-level M3 API.

- `src/dpsim/__main__.py`
  - Lifecycle CLI output now prints the M3 method sequence, maldistribution risk, and Protein A lifetime screen.

- `tests/test_module3_method.py`
  - Unit tests for method-step construction, method orchestration, operability limits, and alkaline degradation response.

- `tests/lifecycle/test_p4_m3_method.py`
  - Lifecycle tests proving the resolver and lifecycle graph now use the full M3 method.

## Scientific Model Boundaries

### Dynamic Load

The load step uses the existing single-component LRM breakthrough solver. This preserves the already-tested DBC5/DBC10/DBC50, UV signal, pressure drop, and mass-balance behavior.

The method result stores this as `ChromatographyMethodResult.load_breakthrough`. The lifecycle exposes the same object as `DownstreamLifecycleResult.m3_breakthrough`.

### Pack, Equilibrate, Wash, Elute

Pack/equilibrate/wash/elute are currently represented as operational method steps, not as a fully coupled cyclic PDE initialized from a loaded column state. They provide:

- buffer pH and conductivity audit trail
- step duration and column-volume calculations
- pressure drop and bed-compression checks per method flow
- residence-time diagnostics
- Protein A elution and cycling risk screens

This is scientifically appropriate for P4 because it makes the real method structure explicit without pretending that the platform already has a validated full-cycle chromatographic desorption solver.

### Protein A Model

The Protein A report includes:

- pH-dependent IgG binding isotherm via `ProteinAIsotherm`
- load pH and elution pH affinity comparison
- equilibrium load capacity estimate
- film mass-transfer coefficient and characteristic resistance time
- ligand accessibility factor from FMC area/activity fields
- alkaline degradation per cycle from high-pH exposure
- cycle lifetime to 70% capacity
- ligand leaching risk from FMC assay contract fields
- screening elution recovery estimate

These are development-screening correlations. They must be calibrated against resin-lot and target-IgG data before use as decision-grade process predictions.

## Operability Limits Added

`ColumnOperabilityReport` evaluates:

- pressure drop against method target and pump limit
- bed compression
- particle Reynolds number
- axial Peclet number
- flow maldistribution risk

The lifecycle maps operability blockers and warnings into `ValidationReport` under `M3_OPERABILITY_LIMIT`.

## Recipe Parameters Now Supported

Default M3 method recipe fields:

- Pack:
  - `column_diameter`
  - `bed_height`
  - `bed_porosity`
  - `packing_flow_rate`

- Equilibrate:
  - `buffer_name`
  - `pH`
  - `conductivity`
  - `flow_rate`
  - `duration`

- Load:
  - `buffer_name`
  - `pH`
  - `conductivity`
  - `feed_concentration`
  - `flow_rate`
  - `feed_duration`
  - `total_time`
  - `residence_time`

- Wash:
  - `buffer_name`
  - `pH`
  - `conductivity`
  - `flow_rate`
  - `duration`

- Elute:
  - `buffer_name`
  - `pH`
  - `conductivity`
  - `flow_rate`
  - `duration`
  - `gradient_field`
  - `gradient_start_pH`
  - `gradient_end_pH`

## Validation And Provenance

Every method result carries a `ModelManifest` named `M3.method.ProteinAOperation`.

The manifest inherits upstream FMC evidence tier and adds diagnostics for:

- method operation sequence
- maximum pressure drop
- maximum bed compression
- particle Reynolds number
- axial Peclet number
- maldistribution risk
- Protein A load and elution affinity
- cycle lifetime
- leaching risk
- load-step LRM mass balance

Lifecycle graph node `M3` now uses the method manifest while keeping the breakthrough result accessible.

## Known Limitations

- Elution is a screening estimate, not a full PDE desorption simulation from the loaded bound-state profile.
- Equilibration and wash do not yet model impurity displacement, UV baseline drift, or host-cell protein removal.
- Protein A alkaline degradation is a simple pH-time screen and not a fitted resin-lifetime model.
- Ligand leaching depends on FMC assay fields; without measured leaching data it remains an inferred development screen.
- Real column efficiency metrics such as asymmetry, HETP, plate count, and distributor effects are not yet mechanistically simulated.

## Verification

Focused regression passed:

```text
59 passed, 13 warnings in 60.90s
```

Command:

```powershell
$env:TEMP='C:\Users\tocvi\DPSimTemp'; $env:TMP=$env:TEMP; $env:TMPDIR=$env:TEMP; $env:DPSIM_TMPDIR='C:\Users\tocvi\DPSimTemp'; $env:DPSIM_OUTPUT_DIR='C:\Users\tocvi\DPSimOutput\p4-m3-focused'; $env:PYTHONIOENCODING='utf-8'; .\.venv\Scripts\python -m pytest -q -p no:cacheprovider --basetemp C:\Users\tocvi\DPSimTemp\pytest-p4-m3-focused tests\test_module3_method.py tests\test_module3_breakthrough.py tests\test_gradient_lrm.py tests\lifecycle\test_p4_m3_method.py tests\lifecycle\test_p1_scientific_boundaries.py
```

Warnings are the existing short-smoke LRM mass-balance caution warnings and are already represented in M3 evidence-tier diagnostics.

## Recommended Next Work

1. Add a true loaded-state elution solver that initializes from the load-step bound concentration profile.
2. Add HETP, asymmetry, and tracer-pulse column efficiency models.
3. Add impurity/host-cell-protein wash and co-elution representations.
4. Fit Protein A alkaline degradation and leaching to resin-lot cycling data.
5. Extend UI controls to edit the full M3 method recipe directly.
