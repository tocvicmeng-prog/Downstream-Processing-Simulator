# HANDOVER — v0.8.8 release close

**Date:** 2026-05-10
**Tag:** v0.8.8
**Work plan:** `docs/update_workplan_2026-05-10_v0_9_0.md` §3
**Theme:** Maturation milestone — *the dashboard becomes wet-lab-credible*.

## Summary

v0.8.8 closes 17 of the 25 W-items in the joint v0.9.0 plan §3. Versioned as v0.8.8 (not v0.9.0) per the project's versioning policy: v0.9 stays reserved for the matured-status plateau that arrives only after the three durable v1.0 deferrals close. After v0.8.8 the dashboard meets the audit's *wet-lab-credible* bar — operator affordances, decision-grade consistency, save/load, run-comparison, SOP export, spreadsheet calibration import, first-run examples, guided workflow tour, predicted-vs-measured ΔP overlay, tier-promotion guidance.

## Closed W-items (17)

| W-ID | Title | Resolves audit defect |
|---|---|---|
| W-079 | Pressure indicator → tier-aware INTERVAL bracket | A-14, S-10 |
| W-080 (partial) | Cycle lifetime / asymmetry / impurity-risk metrics tier-routed | A-15 |
| W-082 | Pre-flight envelope summary above Run | S-11, U-11, A-17 |
| W-085 (partial) | Multi-column "design-time tool" warning | A-16, U-18 |
| W-086 | M1 → M2 → M3 chain confirmation banner | U-7 |
| W-088 | Inverse Bayesian input-time blocker (< 8 measurements) | S-12, U-16 |
| W-089 | Spreadsheet (CSV/XLSX) → CalibrationEntry import + column mapping | U-19, S-18 |
| W-090 | Tier-promotion hints in tier banner | U-29 |
| W-091 | "Set Q to Q_recommended" button on pressure indicator | U-12, U-23 |
| W-093 | Save/load session JSON snapshot | U-25 |
| W-094 | Wet-lab SOP Markdown export | U-26 |
| W-095 | Run-vs-run snapshot + compare table | U-27 |
| W-097 | First-run examples (Protein A / IEX / IMAC) | U-1, U-15, S-15, S-19 |
| W-098 | Scientific Mode consequence-on-rerun caption | U-2 |
| W-099 | Guided workflow tour (sidebar expander) | S-19, U-1 |
| W-100 | Predicted vs measured ΔP overlay in streaming monitor | U-22 |
| W-101 | Missing writer for orphan reader `_m3_column_for_envelope` | A-11 |

## Deferred (8)

| W-ID | Title | Reason for deferral | Target |
|---|---|---|---|
| W-081 | Tier-routing CI gate | Requires mass-fix of legacy `st.metric` calls | v0.9 |
| W-083 | Remove parallel pre-flight compute | Behaviour-changing refactor | v0.9 |
| W-084 | M3 geometry → recipe writethrough | Deeply complex IA change | v0.9 |
| W-087 | `tab_m3.py` refactor (1198 LOC → modular) | High regression risk | v1.0 |
| W-092 | All RecoveryAction labels clickable | W-091 closed the highest-impact one | v0.9 |
| W-096 | Full unit standardisation pass | Large scope; partial via SOP export | v0.9 |
| W-102 | Remove orphan `m3_latest_state` write | Low priority; harmless | v0.9 |

## NEW modules

| Path | LOC | Purpose |
|---|---|---|
| `panels/session_io.py` | ~140 | Save/load session JSON snapshot |
| `panels/first_run_examples.py` | ~150 | Three canonical-recipe loaders |
| `panels/sop_export.py` | ~210 | Markdown SOP export |
| `panels/run_compare.py` | ~120 | Run-history snapshot + compare table |
| `panels/spreadsheet_calibration_import.py` | ~210 | CSV/XLSX → CalibrationEntry with column mapping |

## Modified modules (selected)

| Path | Change |
|---|---|
| `tabs/tab_m3.py` | M2→M3 chain banner; cycle-lifetime tier routing; SOP export mount; run-compare mount; orphan-reader writer |
| `shell/tier_banner.py` | Tier-promotion hint per band |
| `shell/stage_panels.py` | Pre-flight envelope summary above Run; optimization tab mount |
| `tabs/tab_calibration.py` | Multi-column "design-time tool" warning; spreadsheet import mount |
| `tabs/tab_m3_monitor.py` | Predicted-ΔP overlay |
| `tabs/calibration/inverse_inference.py` | < 8-measurement input blocker |
| `components/pressure_indicator.py` | Tier-aware INTERVAL bracket; "Set Q to Q_recommended" button |
| `app.py` | Guided workflow tour; first-run examples + session-io sidebar mount; tier-banner top-of-page mount |

## Verification

- **523 tests pass** across the visualization + module3_performance + lifecycle + AST-gate scope (no regression vs v0.8.7).
- 139/139 visualization tests including the existing 3 widget-mounting AST gates.
- ruff: 0 violations across all edited paths.
- mypy: 0 issues on the changed source files.
- AST gate: 0 violations on managed enums.
- Widget-mounting AST gate: every new `render_*_panel` properly mounted.

## Public framing

> v0.8.8 ships as **"the dashboard becomes wet-lab-credible"**. The v0.7→v0.8.7 backend has been mature for some time; v0.8.4 → v0.8.7 closed the coverage and wiring gaps; v0.8.8 closes the operator-affordance and tier-honesty gaps that kept the simulator feeling like a research tool rather than a wet-lab planner. A bench user can now: pick a first-run example, see what experiment promotes their tier, save / load / compare sessions, export a wet-lab SOP, ingest spreadsheet calibration data, and see predicted-vs-measured ΔP at the bench. The v0.9 maturity plateau is reserved for once the three durable v1.0 deferrals close (live AKTA UNICORN, MCMC inverse, cyclic SMB).

## Outstanding (next horizon)

- Close the 8 deferred W-items above when the work permits (target v0.9.0 unless v1.0).
- The three durable v0.9-deferred items remain v1.0+ candidates: live AKTA UNICORN socket (ADR-008 hardware), MCMC inverse promotion (ADR-010 dataset-bound), cyclic SMB physics (ADR-009).
