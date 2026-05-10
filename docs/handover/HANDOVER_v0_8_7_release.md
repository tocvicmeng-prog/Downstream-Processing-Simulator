# HANDOVER — v0.8.7 release close

**Date:** 2026-05-10
**Tag:** v0.8.7
**Work plan:** `docs/update_workplan_2026-05-10_v0_9_0.md` §2
**Driving audits:** `docs/handover/AUDIT_v0_8_5_e2e_phase{1,2,3}_*.md`

## Summary

v0.8.7 closes the v0.8.5 audit's HIGH/MEDIUM-severity orphan-backend defects: HIC + ProteinA isotherms unreachable from the UI (S-5/A-9), detection module family 100 % UI-orphan (S-6/A-5), `OptimizationEngine` CLI-only (S-7/A-6), `MonitorSource` Protocol bypassed by the UI (S-8/A-7), `monte_carlo_step_program` orphaned at the UI (S-9/A-8). After v0.8.7 every scientifically meaningful capability shipped in the v0.7 → v0.8 cluster has a UI path.

**Five W-items shipped (W-074 → W-078); six new validation gates (48–53) closed.**

## Per-batch summary

### B-5a (W-078) — HIC + ProteinA in IsothermChoice

* `panels/isotherm_selector.py`: extended enum + 2 sub-forms + 2 to_isotherm cases + family-aware default routing changes.
* AGAROSE / AGAROSE_CHITOSAN now default to PROTEIN_A (was bare Langmuir before — the Phase 1 audit's S-5 finding).
* AST gate (already covers `IsothermChoice`) automatically enforces the new members.

### B-5b (W-074) — Detector traces UI

* NEW `components/detector_traces.py` (~210 LOC) with `_build_detector_figure` + `render_detector_traces`.
* Multi-y-axis Plotly figure: UV (mAU, primary), fluorescence (RFU, secondary), conductivity (mS/cm, tertiary).
* Mounted at `tab_m3.py:1083` after the breakthrough+chromatogram plots.

### B-5c KEYSTONE (W-075) — OptimizationEngine top-level UI

* NEW `tabs/tab_optimization.py` (~250 LOC).
* TargetSpec inputs (d32 / pore / G_DN with tolerances), Sobol initial points + BO iterations sliders, optional robust-BO toggle.
* Graceful degradation when `[optimization]` extra is not installed — surfaces install banner with the pinned `pip install -e '.[optimization]'` command.
* Mounted at the bottom of the Calibration stage in `shell/stage_panels.py`.
* Result panel shows best-of-campaign objective values + 7-D search-space coordinates at SEMI_QUANTITATIVE per ADR-007.

### B-5d (W-076) — MonitorSource Protocol UI

* `tab_m3_monitor.py` refactored to consume the Protocol via a Source radio.
* Four options: CSV replay (legacy), Simulated trace (synthetic ramp + fouling), Null (placeholder), Live AKTA UNICORN (disabled v0.9 slot per ADR-008).
* Simulated path exposes the `SimulatedMonitorSource` parameters (steady-state ΔP / ramp τ / fouling slope / duration) and drains the source into a readings tuple consumed by the existing `replay()` path.

### B-5e (W-077) — Multi-step coupled MC

* `tabs/calibration/forward_mc.py` extended with a single-step / multi-step coupled mode radio.
* Multi-step path wires `monte_carlo_step_program` with a 3-step program (equilibrate / load / wash) and shared parameter draws.
* Result panel adds a per-step blocker probability section with a worst-step caption.

## Commit chain

```
(this release commit) — release: v0.8.7 — orphan backend exposure
76f2f12 (v0.8.6)        — release: v0.8.6 — critical wiring fixes for v0.8.4 widgets
ba2ac56 (v0.8.5)        — release: v0.8.5 — M3 real-time back-pressure indicator
beacd0c (v0.8.4)        — release: v0.8.4 — UI completeness against the v0.8.3 backend
```

## Verification

* **5 new tests** in `tests/visualization/test_isotherm_selector.py` (20 total).
* **139/139 visualization tests pass** (134 prior + 5 new).
* **523 tests pass** across the visualization + module3_performance + lifecycle + AST-gate scope (up from 518 at v0.8.6).
* ruff: 0 violations.
* mypy: 0 issues on the 6 changed source files.
* AST gate: 0 violations on extended `IsothermChoice`.
* Widget-mounting AST gate: 0 violations.

## Validation gates closed (48 → 53)

| Gate | Description | Resolved by |
|---|---|---|
| 48 | HIC + ProteinA selectable; family-aware defaults route correctly | B-5a |
| 49 | Detector traces (UV / fluor / cond) render after every M3 run | B-5b |
| 50 | OptimizationEngine reachable from top-level UI entry | B-5c |
| 51 | Streaming monitor source dropdown (CSV / Simulated / Null + v0.9 slot) | B-5d |
| 52 | Multi-step coupled MC reachable from forward MC panel | B-5e |
| 53 | AST gate covers extended `IsothermChoice` (HIC + PROTEIN_A) | B-5a |

## Public-communication framing

> v0.8.7 ships as **"the dashboard becomes complete"**. Where v0.8.6 closed the wiring breaks that made user inputs theatrical, v0.8.7 closes the orphan-backend gaps that made the README's promises structurally unreachable. Every scientifically meaningful capability shipped in the v0.7 → v0.8 cluster now has a UI path. The v0.9.0 maturation milestone — decision-grade consistency, pre-flight envelope relocation, calibration discipline, operator affordances, unit standardisation, first-run examples, predicted-vs-measured overlay — remains the next-step roadmap. The three durable v0.9-deferred items (live AKTA UNICORN, MCMC inverse, cyclic SMB) remain v1.0+ candidates.

## Open future work — v0.9.0

Per `docs/update_workplan_2026-05-10_v0_9_0.md` §3 (24 W-items in three bundles):

* **Bundle X** — Decision-grade consistency + pre-flight envelope relocation (W-079 → W-083).
* **Bundle Y** — Calibration discipline + operator affordances (W-088 → W-095): SOP PDF export, save/load sessions, run-vs-run comparison, spreadsheet calibration import.
* **Bundle Z** — Unit standardisation + first-run examples + IA refactor (W-096 → W-102): `tab_m3.py` refactor (~1198 LOC → 250 LOC per file), guided wizard, predicted-vs-measured overlay.

The three durable v0.9-deferred items remain v1.0+ candidates: live AKTA UNICORN socket (ADR-008 hardware), MCMC inverse promotion (ADR-010 dataset-bound), cyclic SMB physics (ADR-009).
