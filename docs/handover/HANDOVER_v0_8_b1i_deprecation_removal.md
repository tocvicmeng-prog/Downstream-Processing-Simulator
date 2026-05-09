# HANDOVER — B-1i deprecation removal close (v0.8.0)

**Batch:** B-1i
**Work item:** W-031 (HIGH)
**Source delta:** v0.7.0 plan §6 deprecation grace expiry
**Date:** 2026-05-10

## Summary

`ColumnGeometry.max_safe_flow_rate` is removed. The v0.7.0 deprecation
window (one release) closes; the `safety × E_star` bursting-modulus
anchor is no longer reachable through the public API. Operational
ceilings come solely from `compute_pressure_envelope` (W-020 / B-2f) →
`PressureEnvelope.Q_max_m3_s`.

## Files changed

| File | Change |
|---|---|
| `src/dpsim/module3_performance/hydrodynamics.py` | Drop `max_safe_flow_rate`. `validate_flow_rate` keeps only the soft compression-fraction + Re_p WARNINGs (the BLOCKER path was the bursting check). |
| `src/dpsim/visualization/plots_m3.py` | `plot_pressure_flow_curve` requires `Q_max` as an explicit argument. |
| `src/dpsim/visualization/tabs/tab_m3.py` | The breakthrough panel computes the envelope on demand (lazy `compute_pressure_envelope` on the M2 result) and feeds `Q_max_m3_s` to the plot. |
| `src/dpsim/lifecycle/orchestrator.py` | Comment refresh — `validate_flow_rate` WARNINGs are now a backstop, not a fall-back. |
| `tests/test_module3_breakthrough.py` | Remove `TestMaxSafeFlowRate`. |
| `tests/module3_performance/test_hydrodynamics_deprecation.py` | DELETED — obsolete after removal. |
| `tests/{core,level1_emulsification,level2_gelation,lifecycle,module3_performance,visualization}/__init__.py` | Added — namespaces test subdirs (incidental clean-up; resolves a long-standing duplicate-module pytest collision on `test_process_dossier.py`). |

## Verification

- 209 module3_performance tests + 432 lifecycle/viz/core tests pass.
- ruff + mypy clean on changed files.
- 1 pre-existing test failure (`test_breakthrough_inherits_fmc_qualitative_tier` referencing a stale `confidence_tier` field) is unrelated to v0.8 scope.

## Out of scope

The pre-existing `confidence_tier` test failure (separate stale field-name issue on `FunctionalMediaContract`) is left to a future tech-debt pass.
