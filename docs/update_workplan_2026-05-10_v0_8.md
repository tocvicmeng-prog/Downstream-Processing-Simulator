# DPSim v0.8.0 — Pressure-Envelope Operationalization Work Plan

**Date:** 2026-05-10 (same day as v0.7.0 ship)
**Author:** `/dev-orchestrator` (continuation of the v0.7.0 plan)
**Inputs inherited:** `docs/update_workplan_2026-05-10_m3_pressure.md` §6 (deferred items)
**Target release:** v0.8.0
**Mode:** project plan; execution interleaved

---

## 1. Scope — three deferred items from v0.7.0 §6

The v0.7.0 plan §6 explicitly deferred:

1. **Streaming UI for `evaluate_pressure_trace`** — the function shipped in B-3d / W-027; the live widget + AKTA UNICORN integration + WebSocket plumbing was scoped as a separate ~3-week epic.
2. **`max_safe_flow_rate` removal** — deprecated in B-2f / W-020 with `DeprecationWarning`; "kept one release", to be removed in v0.8.
3. **Optimization integration** — adding ΔP_max as an explicit BoTorch optimization objective/constraint, deferred from v0.7.

This v0.8.0 plan operationalizes all three.

## 2. Work item ledger — W-031 … W-033

| ID | Severity | Title | Files affected | Source delta | Bundle |
|---|---|---|---|---|---|
| **W-031** | HIGH | Remove deprecated `max_safe_flow_rate`; migrate callers | `module3_performance/hydrodynamics.py` (delete method + update `validate_flow_rate`); `visualization/plots_m3.py`, `tests/test_module3_breakthrough.py` (call-site migration); `tests/module3_performance/test_hydrodynamics_deprecation.py` (REMOVE — obsolete) | v0.7 §6 deprecation grace expired | A |
| **W-032** | HIGH | Streaming pressure-monitor UI + CSV-replay helper | `module3_performance/pressure_monitor_replay.py` (NEW — CSV → reading sequence); `visualization/tabs/tab_m3_monitor.py` (NEW — Streamlit live monitor section); test fixtures + ~20 new tests | v0.7 §6 streaming-UI epic | B |
| **W-033** | MEDIUM | Pressure-feasibility constraint in BO objectives | `optimization/objectives.py` (add `PressureFeasibilityCheck` value type + integration in `check_constraints`); ~12 new tests | v0.7 §6 optimization integration | C |

### 2.1 BLOCKER classification

None. v0.7.0 already shipped the science fix; v0.8 is hardening + UX completion.

## 3. Sequenced batches

| Batch | IDs | Modules | Model tier | Notes |
|---|---|---|---|---|
| **B-1i** *Deprecation removal (W-031)* | W-031 | `hydrodynamics.py`, `plots_m3.py`, two tests | **Haiku** (mechanical removal) | First — clears deprecation noise from downstream batches. |
| **B-2i** *Streaming UI (W-032)* | W-032 | `pressure_monitor_replay.py` (NEW), `tab_m3_monitor.py` (NEW) | **Sonnet** (Streamlit + state-machine bridging) | Largest batch. Includes CSV-fixture replay test + UI smoke test. |
| **B-2j** *BO pressure feasibility (W-033)* | W-033 | `optimization/objectives.py`, new tests | **Sonnet** (light) | Independent; can run parallel to B-2i but kept sequential for context. |
| **B-3e** *v0.8.0 release* | — | `pyproject.toml`, `CHANGELOG.md`, `__init__.py` version bump, handover docs | n/a | Tag and ship. |

## 4. Validation gates — v0.8.0

Inherits all v0.7 gates plus:

- **Gate 9: deprecation-cycle hygiene** — closed when B-1i lands. Establishes the "deprecate one release, remove next release" cadence as a first-class precedent.
- **Gate 10: pressure-monitor offline replay** — closed when B-2i lands. Operators can validate envelope accuracy against historical AKTA traces without a live hardware integration.
- **Gate 11: BO-side pressure feasibility** — closed when B-2j lands. Optimizer cannot recommend recipes whose post-M2 column step would exceed the operational envelope.

### 4.1 v0.8.0 release framing

> **v0.8.0 ships as: "DPSim's pressure envelope is end-to-end — pre-flight (v0.7), in-flight (v0.8 monitor UI), and back-prop (v0.8 BO feasibility). Calibration tier remains SEMI_QUANTITATIVE INTERVAL until manufacturer pressure-flow curves are loaded into the calibration store."**

## 5. What v0.8.0 does *not* attempt

- **AKTA UNICORN live integration** — still deferred. The v0.8 monitor consumes CSV traces (offline replay); a true WebSocket bridge to UNICORN's data stream is a v0.9 epic.
- **Multi-column / SMB pressure modelling** — still v0.9.
- **Bayesian uncertainty propagation through the envelope** — still future.
- **Channeling auto-recovery** — still future. The monitor *detects* MODEL_DEVIATION_LOW; automated repacking guidance stays out of scope.

## 6. Handover targets

- `docs/handover/HANDOVER_v0_8_b1i_deprecation_removal.md` — at end of B-1i
- `docs/handover/HANDOVER_v0_8_b2i_streaming_ui.md` — at end of B-2i
- `docs/handover/HANDOVER_v0_8_b2j_bo_feasibility.md` — at end of B-2j
- `docs/handover/HANDOVER_v0_8_0_release.md` — at v0.8.0 tag

---

### Disclaimer

> Work plan provided for development purposes only. K_geom values and pressure-flow thresholds remain literature-anchored placeholders pending wet-lab calibration. The streaming UI ships as an offline CSV replay; it is not a hardware-certified live monitor. Refer to the v0.7.0 plan §4 + §6 for the inherited tier ladder and out-of-scope statements.
