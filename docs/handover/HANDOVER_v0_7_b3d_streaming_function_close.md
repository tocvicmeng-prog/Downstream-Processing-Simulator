# B-3d Close — Streaming Pressure Monitor Function

**Date:** 2026-05-10
**Scope:** Closing batch B-3d from `docs/update_workplan_2026-05-10_m3_pressure.md` — final v0.7.0 batch; closes W-027 (Δ8 from /scientific-advisor architecture). Function-only ship; live UI deferred to v0.8.
**Branch state at handover:** uncommitted B-3d files on top of B-2h.
**Authors:** `/architect` (state-machine design + rule taxonomy), `/scientific-coder` (implementation).

---

## 1. What landed

| File | Change |
|---|---|
| `src/dpsim/module3_performance/pressure_monitor.py` (NEW) | 285 LOC. `PressureMonitorRule` enum (7 rules), `PressureMonitorState` enum (OK/WARNING/BLOCKER), `PressureMonitorReading` + `PressureMonitorOutput` frozen dataclasses, `evaluate_pressure_trace(reading, envelope, history, history_max_seconds, warning_dwell_seconds)` pure function. Three diagnostic ratios computed per call: headroom_ratio, dpdt_pct_per_min, model_deviation_ratio. |
| `src/dpsim/module3_performance/__init__.py` | Exported the 5 new symbols. |
| `tests/module3_performance/test_pressure_monitor.py` (NEW) | 20 cases covering OK state, headroom rules, dΔP/dt rules, model deviation, spike detection, history pruning + immutability, validation, frozen contract, and a synthetic fouling-trace replay verifying OK→WARNING→BLOCKER state transitions. |

---

## 2. Rule taxonomy (architect §2.h)

The function evaluates seven rules against (reading, envelope, history). Order is BLOCKER-first, then WARNING. First match wins for the state assignment.

| Rule | Threshold | State |
|---|---|---|
| SPIKE | dΔP/dt > 100 %/min sustained > 5 s | BLOCKER (immediate) |
| HEADROOM_BLOCKER | ΔP_meas / ΔP_max ≥ 0.85 | BLOCKER |
| DPDT_BLOCKER | dΔP/dt ≥ 20 %/min | BLOCKER |
| MODEL_DEVIATION_LOW | ΔP_meas / ΔP_predicted < 0.60 (channeling) | BLOCKER |
| MODEL_DEVIATION_HIGH | ΔP_meas / ΔP_predicted > 1.50 (fouling) | WARNING |
| HEADROOM_WARNING | ΔP_meas / ΔP_max ≥ 0.70 (and < 0.85) | WARNING |
| DPDT_WARNING | dΔP/dt ≥ 5 %/min (and < 20) | WARNING |
| (otherwise) | — | OK |

Each rule's triggered output carries a human-readable `suggested_action` (e.g., "EMERGENCY STOP. Sudden ΔP spike detected — channeling collapse or gas-pocket release likely." for SPIKE).

---

## 3. Verification

- **20/20** new B-3d tests passing.
- **694/694** wide regression in 93 s.
- ruff: clean. mypy: 0 issues on `pressure_monitor.py`.
- AST gate: 3/3 passing.

---

## 4. Module registry

| Module | Status |
|---|---|
| `module3_performance/pressure_monitor.py` | **APPROVED** (post-B-3d) |

**v0.7.0 W-item progress: 11/11 closed.** All Tier 0 / Tier 1 / Tier 2 / Tier 3 batches complete.

---

## 5. v0.7.0 release readiness

The v0.7.0 release pipeline is now ready for the final tag:

1. ✅ Tier 0 (B-0d residual hygiene + verification + v0.7.0 plan)
2. ✅ Tier 1 (B-1f viscosity + B-1g d32+frit + B-1h decision_grade ext)
3. ✅ Tier 2 (B-2f keystone + B-2g iteration + B-2h UX wiring)
4. ✅ Tier 3 (B-3d streaming function)
5. **Pending:** CHANGELOG.md entry + VERSION bump + tag.

Full test sweep at the v0.7.0 candidate state: **694/694** in 93 s with 23 expected DeprecationWarnings on `max_safe_flow_rate` (legacy callers retained for the v0.7.x deprecation window).

Public-communication framing (work plan §4.3) — DPSim v0.7.0 ships as: **"a research-grade screening simulator with first-principles back-pressure envelopes rendered at SEMI_QUANTITATIVE INTERVAL precision; promotion to CALIBRATED_LOCAL NUMBER precision requires user-supplied manufacturer pressure-flow curves or local wet-lab calibration."**

---

## 6. Deferred to v0.8

- Streaming UI widget for `evaluate_pressure_trace` (the function alone ships v0.7).
- AKTA UNICORN trace integration (CSV format mapping).
- Removal of deprecated `ColumnGeometry.max_safe_flow_rate` (one-release deprecation window).
- Per-recipe-step `MobilePhase` driving the envelope through the full program (v0.7 uses a single default `MobilePhase()` for the lifecycle wire-in).
- Rubbery-state PLGA T_C window expansion (v0.7 caps at 25 °C).
- Bayesian uncertainty propagation through the envelope.
- Fracture-mechanics cracking threshold (5–10× E_star per Hertz/K_IC scaling).
- Per-family K_geom calibration against manufacturer pressure-flow curves (user-data-side; the `calibration_store` argument exists but is empty).
