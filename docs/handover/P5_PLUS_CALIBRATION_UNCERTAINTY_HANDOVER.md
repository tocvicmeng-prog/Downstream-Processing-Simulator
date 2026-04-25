# P5+ Calibration Posterior Propagation Handover

Date: 2026-04-25

## Scope

P5+ extends the P5 calibration ingest work by making calibration posterior
widths visible at the M3 lifecycle result. This is not a full Monte Carlo
chromatography solve. It is a conservative first-order propagation layer that
turns calibrated parameter uncertainty into auditable screening intervals and
validation warnings.

## Implemented Changes

### M3 Posterior Diagnostics

Lifecycle M3 now reads `CalibrationEntry.posterior_uncertainty` for applied
M2/M3 calibration entries and emits diagnostics such as:

- `calibration_posterior_count`
- `calibration_posterior_parameters`
- `calibration_uncertainty_model`
- `estimated_q_max_calibration_relative_uncertainty`
- `K_affinity_calibration_relative_uncertainty`
- `m3_capacity_calibration_relative_uncertainty`
- `dbc_10pct_calibration_sigma_mol_m3`
- `dbc_10pct_calibration_p95_lower_mol_m3`
- `dbc_10pct_calibration_p95_upper_mol_m3`
- `pressure_flow_reference_pressure_sigma_Pa`
- `pressure_flow_reference_pressure_p95_lower_Pa`
- `pressure_flow_reference_pressure_p95_upper_Pa`

The capacity interval uses a first-order delta-method approximation:

```text
relative_sigma_DBC ~= sqrt(relative_sigma_qmax^2 + (0.25 * relative_sigma_K)^2)
```

When qmax is not directly calibrated, M2 ligand-density and activity-retention
posteriors are combined as the capacity drivers.

### Validation Warnings

Two warning gates were added:

- `M3_CALIBRATION_UNCERTAINTY_HIGH`
  - Emitted when propagated M3 capacity uncertainty exceeds 30 percent.
- `M3_PRESSURE_FLOW_UNCERTAINTY_HIGH`
  - Emitted when pressure-flow posterior uncertainty exceeds 30 percent.

These warnings do not block exploratory runs, but they prevent broad posterior
intervals from being hidden behind a single deterministic DBC or pressure value.

### Manifest Annotation

M3 method manifests now carry the posterior-propagation diagnostics and an
explicit assumption that the intervals are first-order screening estimates.

### Example Assay Records

Template records were added outside the live ingest directories:

- `data/validation/m2_capacity/examples/example_ligand_density.json`
- `data/validation/m2_capacity/examples/example_activity_retention.json`
- `data/validation/m3_binding/examples/example_static_binding_isotherm_point.json`
- `data/validation/m3_binding/examples/example_breakthrough_curve.json`
- `data/validation/m3_binding/examples/example_pressure_flow_curve.json`

These examples are intentionally not in `assays/`, so the default CLI ingest
path does not treat them as real campaign data.

## Key Files

- `src/dpsim/lifecycle/orchestrator.py`
- `tests/lifecycle/test_p5_calibration_evidence.py`
- `tests/test_validation_pipeline.py`
- `data/validation/m2_capacity/examples/`
- `data/validation/m3_binding/examples/`

## Scientific Limitations

- The new intervals assume local linearity and independent calibration
  posteriors.
- K-affinity sensitivity is represented by a conservative screening factor,
  not an adjoint or stochastic LRM solve.
- Pressure uncertainty is propagated to the calibrated pressure-flow reference,
  not to a re-solved compressible-bed hydraulic model.
- Full Bayesian fitting and Monte Carlo propagation remain future P5++ work.
