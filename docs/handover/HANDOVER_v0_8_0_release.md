# HANDOVER — v0.8.0 release close

**Date:** 2026-05-10 (same day as v0.7.0 ship)
**Tag:** v0.8.0
**Work plan:** `docs/update_workplan_2026-05-10_v0_8.md`

## Summary

v0.8.0 closes the three deferred items from v0.7.0 §6:
- **W-031 (B-1i):** removed `ColumnGeometry.max_safe_flow_rate` after the
  one-release deprecation grace.
- **W-032 (B-2i):** shipped the streaming pressure-monitor UI as an
  offline CSV-replay surface in `tab_m3.py`, plus the underlying
  `pressure_monitor_replay.py` helper.
- **W-033 (B-2j):** added the `PressureFeasibilityContext` opt-in
  pressure-feasibility constraint to the BO objectives layer.

## Commit chain

```
fa159c8 B-2j: pressure-feasibility BO constraint (W-033, v0.8.0)
1aa9ac3 B-2i: streaming pressure-monitor UI + CSV-replay (W-032, v0.8.0)
4d21290 B-1i: remove deprecated max_safe_flow_rate (W-031, v0.8.0)
f5039cc chore: close pre-existing mypy tech debt (v0.7.0 follow-on)
069d0d4 release: v0.7.0 — M3 back-pressure optimization
```

## Verification

- 681 tests passing in v0.8-relevant scope (module3_performance + visualization + core + lifecycle + new feasibility tests). One pre-existing `confidence_tier` test fail is unrelated to v0.8 work.
- ruff: clean across all changed paths.
- mypy: 0 issues on new source files.
- AST gate: no new `is` / `is not` comparisons against managed enums.

## Validation gates closed in this release

- **Gate 9 — Deprecation-cycle hygiene:** establishes "deprecate one release, remove next" cadence as a first-class precedent.
- **Gate 10 — Pressure-monitor offline replay:** operators can validate envelope accuracy against historical AKTA traces without a live hardware bridge.
- **Gate 11 — BO-side pressure feasibility:** the optimizer cannot recommend recipes whose post-M2 column step would exceed the operational envelope.

## Public-communication framing

> v0.8.0 ships as **DPSim's pressure envelope is end-to-end** — pre-flight (v0.7), in-flight (v0.8 monitor UI for offline replay), and back-prop (v0.8 BO feasibility). Calibration tier remains SEMI_QUANTITATIVE INTERVAL until manufacturer pressure-flow curves are loaded into the calibration store. The streaming UI is offline-only — live AKTA UNICORN integration is a v0.9 epic.

## Next-release scope (v0.9 candidates)

- Live AKTA UNICORN integration (WebSocket bridge to UNICORN data stream).
- Multi-step pressure feasibility (worst-case across load / wash / elute / CIP).
- Multi-column / SMB pressure modelling.
- Bayesian uncertainty propagation through the envelope.
- Channeling auto-recovery (currently only detected, not auto-handled).
- Wet-lab calibration of K_geom (gates promotion to CALIBRATED_LOCAL render).
- Pre-existing tech-debt: `FunctionalMediaContract.confidence_tier` test stale-field fix in `test_breakthrough_inherits_fmc_qualitative_tier`.
