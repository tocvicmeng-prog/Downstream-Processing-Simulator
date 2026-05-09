# B-2h Close — Pre-Flight UX Wiring

**Date:** 2026-05-10
**Scope:** Closing batch B-2h from `docs/update_workplan_2026-05-10_m3_pressure.md` — UX-facing close of the v0.7.0 M3 back-pressure work; closes W-025 (Δ6 lifecycle wire-in), W-028 (G8 gate), W-029 (tab_m3.py UI section).
**Branch state at handover:** `main` at the B-2g commit + uncommitted B-2h files.
**Authors:** `/architect` (G8 + lifecycle integration design), `/scientific-coder` (implementation).

---

## 1. What landed

### W-025 — Lifecycle wire-in

| File | Change |
|---|---|
| `src/dpsim/lifecycle/orchestrator.py` | Added `pressure_envelope` field to `DownstreamLifecycleResult`. Imported `MobilePhase` and `compute_pressure_envelope`. After M2 completes, computes a per-run `PressureEnvelope` using the M2-updated G_DN/E_star and a default `MobilePhase()` (water-like equilibration buffer at 20 °C). Emits BLOCKER on `headroom_ratio > 1.0`, WARNING on > 0.7, WARNING per `valid_domain_violations`. Threads the envelope through to the result for UI consumption. |

### W-028 — G8 recipe-validation gate

| File | Change |
|---|---|
| `src/dpsim/core/recipe_validation.py` | New `_g8_pressure_envelope_check(recipe, fmc, report)` mirroring the G7 shape from B-1a. Recipe-side pre-flight that flags negative or absurdly-large declared flow rates BEFORE the long M1+M2+M3 chain runs. Wired into `validate_recipe_first_principles` after G7. v0.7 scope: sanity bounds only (G_DN_updated and bead_d32 are not yet known at recipe-validation time; the lifecycle check W-025 does the full envelope). |

### W-029 — M3 UI section

| File | Change |
|---|---|
| `src/dpsim/visualization/tabs/tab_m3.py` | New "Pressure envelope (pre-flight)" subsection inside the M3 Results header. 4-column metric panel (u_crit, Q_max, Q_recommended, Headroom) plus 3-column ΔP panel (predicted, max operational, max burst diagnostic) using `render_metric` (B-1b precedent). Status chip (st.success/warning/error) on the headroom ratio. Expanders for valid_domain violations and provenance notes. All values tier-aware via the new B-1h decision-grade extension. |

### Tests

| File | Cases |
|---|---|
| `tests/core/test_recipe_validation_g8_pressure.py` (NEW) | 8 cases: positive normal flow passes, negative blocks, extreme warns, missing flow_rate silent skip, invalid value silent skip, fmc=None works. |

---

## 2. Verification

- **8/8** new B-2h G8 tests passing.
- **63/63** combined recipe-validation tests (B-1a G7 + B-2h G8 + existing).
- **39/39** lifecycle integration tests passing — M2→M3 wire-in does not break existing flows.
- **10/10** v60 integration tests passing (full M1+M2+M3 lifecycle).
- **664/664** wide regression in 92 s.
- ruff: clean on all touched paths.
- mypy: 0 issues on `recipe_validation.py`. (Pre-existing baseline noise on `lifecycle/orchestrator.py` from M1ExportContract.replace usage at line 1518 is unchanged from v0.6.6 — not introduced by B-2h.)
- AST gate: 3/3 passing.

---

## 3. Module registry

| Module | Status |
|---|---|
| `lifecycle/orchestrator.py` | **APPROVED** (post-B-2h pressure-envelope wire-in; pre-existing mypy baseline unchanged) |
| `core/recipe_validation.py` | **APPROVED** (post-B-2h G8 gate) |
| `visualization/tabs/tab_m3.py` | **APPROVED** (post-B-2h pressure-envelope section) |

v0.7.0 W-item progress: **9/11 closed** (W-021, W-023, W-024, W-030, W-020, W-026, W-022, W-025, W-028, W-029). W-027 is the only remaining item.

---

## 4. Concrete starting point for next session — B-3d

B-3d is the final v0.7.0 batch — Tier 3 maintenance. Closes W-027 (Δ8 streaming pressure-trace evaluator). Function-only ship; streaming UI deferred to v0.8.

### 4.1 W-027 — `pressure_monitor.py`

Files to create:

- `src/dpsim/module3_performance/pressure_monitor.py` (NEW) per architect §3.5:
  - `PressureMonitorRule` enum: HEADROOM_WARNING, HEADROOM_BLOCKER, DPDT_WARNING, DPDT_BLOCKER, MODEL_DEVIATION_LOW, MODEL_DEVIATION_HIGH, SPIKE.
  - `PressureMonitorState` enum: OK, WARNING, BLOCKER.
  - `PressureMonitorReading` frozen dataclass (t_s, dP_pa, Q_m3_s).
  - `PressureMonitorOutput` frozen dataclass (state, triggered_rule, suggested_action, headroom_ratio, dpdt_pct_per_min, model_deviation_ratio, history).
  - `evaluate_pressure_trace(reading, envelope, history=None, history_max_seconds=300, warning_dwell_seconds=30) -> PressureMonitorOutput` pure function.

- `tests/module3_performance/test_pressure_monitor.py` (NEW): ~25 cases covering each rule, hysteresis, history pruning, immutable history return, CSV fixture replay.

---

## 5. v0.7.0 release checklist (after B-3d)

1. Confirm all 11 W-items closed (W-020..W-030).
2. Run wide regression (~700+ tests including the new pressure_monitor suite).
3. Update `CHANGELOG.md` with the v0.7.0 entry.
4. Bump `VERSION` to `0.7.0`.
5. Tag release.
6. Public-communication framing (work plan §4.3): "DPSim v0.7.0 ships as a research-grade screening simulator with first-principles back-pressure envelopes rendered at SEMI_QUANTITATIVE INTERVAL precision. Promotion to CALIBRATED_LOCAL NUMBER precision requires user-supplied manufacturer pressure-flow curves or local wet-lab calibration."

---

## 6. Constraints

- The lifecycle wire-in uses a **default `MobilePhase()`** (water-like at 20 °C). Future scope: per-step buffer composition driving the envelope through the full recipe program. v0.7 establishes the wire path.
- The G8 gate is **recipe-side sanity only** — it does NOT replace the lifecycle's full envelope check. The architectural rationale: G_DN_updated and bead_d32 are M2 outputs, unavailable at recipe-validation time. G8 catches OBVIOUS user errors (negative Q, 1 L/s, etc.) before the slow M1→M2→M3 chain runs.
- The UI section consumes `lifecycle_result.pressure_envelope` from `st.session_state["lifecycle_result"]`. If the envelope is None (e.g., M2 didn't complete or polymer family unregistered without fallback), the section silently skips.
- mypy baseline noise on `lifecycle/orchestrator.py:1518` (M1ExportContract.replace) is **pre-existing from v0.6.6** — NOT introduced by B-2h.
