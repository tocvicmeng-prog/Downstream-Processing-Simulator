# HANDOVER — B-2j BO pressure feasibility close (v0.8.0)

**Batch:** B-2j
**Work item:** W-033 (MEDIUM)
**Source delta:** v0.7.0 plan §6 optimization integration
**Date:** 2026-05-10

## Summary

The BO Pareto filter can now drop candidates whose post-M2 column step
would exceed the operational pressure envelope at the user's target
flow rate. The constraint is opt-in via a keyword-only argument; v0.7
behaviour is preserved exactly when the argument is omitted.

## Files changed

| File | Change |
|---|---|
| `src/dpsim/optimization/objectives.py` | Add `PressureFeasibilityContext` frozen dataclass. Add `pressure_feasible(result, ctx)` helper. Extend `check_constraints` with `pressure_ctx` keyword-only kwarg. Defensive: ValueError / KeyError on envelope computation declares the candidate infeasible with a clean violation message. |
| `src/dpsim/optimization/__init__.py` | Replace eager `from .engine import OptimizationEngine` with PEP 562 `__getattr__` lazy load. Importing `dpsim.optimization.objectives` no longer requires torch. |
| `tests/test_pressure_feasibility.py` | NEW — 12 tests covering admit / reject paths, threshold variants, unsupported-family handling, keyword-only enforcement, lazy-import sentinel. |

## Design

`PressureFeasibilityContext` carries run-level fixed inputs that are
not part of the BO parameter space:
- `column: ColumnGeometry` — geometry; particle_diameter / G_DN / E_star
  are overridden per candidate from `result.emulsification.d32` and
  `result.mechanical.{G_DN, E_star}`.
- `mobile_phase: MobilePhase` — the operating buffer.
- `Q_target_m3_s: float` — target volumetric flow rate.
- `polymer_family: PolymerFamily` — for K_geom lookup.
- `headroom_threshold: float = 1.0` — drop candidates with
  `headroom_ratio > threshold`. Set to 0.7 to also drop WARNING-band
  candidates (more conservative).

`pressure_feasible` is a pure function: builds a per-candidate
ColumnGeometry by `dataclasses.replace`, runs `compute_pressure_envelope`,
returns `(feasible, violations)`.

## Acceptance

- Default (no `pressure_ctx`) preserves v0.7 behaviour exactly.
- Comfortable candidate at headroom < 1.0 is admitted.
- Excessive Q_target / tiny d32 / very low G_DN candidates are rejected.
- `headroom_threshold` = 0.5 path works for advisory-conservative BO runs.
- Existing constraints (G_DN floor, span, RPM, etc.) still fire alongside.
- `pressure_ctx` is keyword-only.
- `dpsim.optimization.objectives` imports without torch.
- 12/12 new tests pass; ruff + mypy clean.

## Out of scope (deferred)

- Wiring `pressure_ctx` through `OptimizationEngine` to be set from
  the Streamlit BO setup UI — v0.9 (requires UI-side surface changes).
- Per-step (load / wash / elute / CIP) pressure feasibility —
  currently checks one Q_target; a multi-step variant would screen
  the worst case.
- Bayesian uncertainty propagation through the envelope — still future.
