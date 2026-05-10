# AUDIT — v0.8.5 end-to-end UI ↔ backend architecture review (Phase 3)

> **Role**: /architect — applying the six-dimension audit framework + the dev-orchestrator integration discipline.
> **Date**: 2026-05-10 · **Audit scope**: v0.8.5. · **Method**: structural cross-checking of every UI component against its backend wire-in, every backend module against its UI consumer, and every ADR against its enforcement.
> **Companion**: Phase 1 (`AUDIT_v0_8_5_e2e_phase1_scientific.md`), Phase 2 (`AUDIT_v0_8_5_e2e_phase2_user.md`), joint plan (`update_workplan_2026-05-10_v0_9_0.md`).

---

## §0 — Six-dimension verdict on the v0.8.5 codebase

| Dimension | Verdict | Diagnosis |
|---|---|---|
| **D1 Correctness** | **PARTIAL** | Backend physics + ADR-locked invariants are sound. UI ↔ backend wiring breaks correctness for two of the three scientifically consequential M3 inputs (mobile phase, isotherm class) — see §1 / A-1 + A-2 + A-3 + A-4. |
| **D2 Completeness** | **FAIL** | Six backend modules ship without UI exposure (HIC, ProteinA bare, IMAC bare, OptimizationEngine, MonitorSource Protocol, multi-step coupled MC). The detection module family is 100 % orphan. See §2. |
| **D3 Modularity** | **PASS** | The v0.8.4 decomposition (panels/ + tabs/ + components/ + shell/) is the right substrate. New code lands in correctly-sized modules. |
| **D4 Scalability** | **PASS** | Streamlit's session_state keys are still tractable (≤ 30); cross-tab dispatch via `_jump_to_calibration_section` works; the AST gate enforces the Family-First contract at CI. |
| **D5 Maintainability** | **PARTIAL** | `tab_m3.py` at 1198 LOC is too large; B-3b (v0.8.5) added rather than refactoring. State-management duplication: M3 tab does its own pre-flight envelope at line 1054, parallel to the lifecycle's pre-flight at orchestrator.py:782. See §4. |
| **D6 Scientific provenance** | **PARTIAL** | Decision-grade routing is inconsistent across panels (see §5). The v0.8.5 pressure indicator does not route through `render_decision_grade_annotation`. |

Verdict in one line: **PARTIAL** with two CRITICAL wiring breaks that must be closed in v0.8.6 before any further feature work.

---

## §1 — Critical wiring breaks (v0.8.6 priority)

These are the architectural defects that masquerade as defect closures in the v0.8.4 release notes.

### A-1 · `render_mobile_phase_widget` is unmounted in production

**Evidence**:
* Definition: `src/dpsim/visualization/panels/mobile_phase.py:33`.
* Production callers (verified by grep `render_mobile_phase_widget(`): **zero**. Only the test file `tests/visualization/test_mobile_phase_widget.py` calls it.
* The closest production usage of `MobilePhase` is `tab_m3.py:1054` — but this calls the bare constructor `_MP_bt()` (defaults), not the widget.

**Root cause**: B-1p (v0.8.4 W-053) shipped the widget but left the wire-in to a follow-on batch that never happened. The CHANGELOG entry at line 13 is therefore inaccurate.

**Architectural fix**: mount `render_mobile_phase_widget` in the M3 tab's input section (above the Run button). Persist the resulting `MobilePhase` to `st.session_state["m3_mobile_phase"]`. Read it from `tab_m3.py:1054` and from `ui_workflow.render_lifecycle_run_panel`'s lifecycle-call site.

**Severity**: **CRITICAL**.

### A-2 · `render_isotherm_widget` is unmounted in production

**Evidence**:
* Definition: `panels/isotherm_selector.py:357`.
* Production callers (verified by grep): **zero**. Only `tests/visualization/test_isotherm_selector.py`.
* `IsothermChoice` and `IsothermSpec` types are referenced only inside `panels/isotherm_selector.py` itself. The lifecycle orchestrator's `run()` signature (line 255) does **not** include an `isotherm_spec=` kwarg.

**Root cause**: same as A-1.

**Architectural fix**: mount `render_isotherm_widget` in the M3 tab. Add `isotherm_spec: IsothermSpec | None = None` to `lifecycle/orchestrator.py::DownstreamProcessOrchestrator.run()`. Wire it through to `module3_performance/orchestrator.py:247` so it overrides `select_isotherm_from_fmc(fmc_hint)`. Update `ui_workflow.render_lifecycle_run_panel` to pass the spec.

**Severity**: **CRITICAL**.

### A-3 · `render_tier_banner` is unmounted in production

**Evidence**:
* Definition: `shell/tier_banner.py:35`.
* Production callers (verified by grep): **zero**.

**Architectural fix**: mount `render_tier_banner` at the top of `app.py`'s render loop (before any tab dispatch). Drive its 3-state colour from the *worst* tier across all stages currently in `lifecycle_result` (use `_per_stage_tiers` from `shell/stage_panels.py:217` as the input).

**Severity**: **CRITICAL**.

### A-4 · `ui_workflow.render_lifecycle_run_panel` does not thread `mobile_phase` or `isotherm_spec`

**Evidence**: `grep mobile_phase\|isotherm_spec src/dpsim/visualization/ui_workflow.py` returns one comment line and zero usages. The orchestrator's W-054 `mobile_phase=` parameter (lifecycle/orchestrator.py:782) has no caller in the dashboard.

**Architectural fix**: thread both kwargs through `ui_workflow.render_lifecycle_run_panel` so the user's session_state inputs reach the orchestrator. Coordinate with A-1 and A-2.

**Severity**: **CRITICAL** (gates A-1 and A-2 from being end-to-end functional).

---

## §2 — Backend orphan modules (v0.8.7 priority)

Backend modules with **zero** UI consumers in `src/dpsim/visualization/`:

### A-5 · Detection module family — 100 % orphan

**Files**: `src/dpsim/module3_performance/detection/{uv,fluorescence,conductivity,ms}.py`.

**UI consumers**: zero (grep verified).

**Architectural fix**: add a *Detector traces* sub-section to the M3 results page that calls these modules with the run's effluent concentration profile and overlays the synthesized traces. Match against an uploaded UNICORN export when the user provides one.

**Severity**: **HIGH**.

### A-6 · OptimizationEngine — CLI-only

**File**: `src/dpsim/optimization/engine.py:127`.

**UI consumers**: zero. Only `src/dpsim/__main__.py:685, 713` (CLI subcommands).

**Architectural fix**: new top-level *Inverse Design / Optimization* tab. Surface the BO-under-pressure-constraint workflow with target inputs (capacity, sharpness, pressure budget) and result inputs (recommended geometry, Q, ligand density). Tier output as SEMI_QUANTITATIVE pending wet-lab calibration.

**Severity**: **HIGH**.

### A-7 · `MonitorSource` Protocol unused by UI (ADR-008 unenforced)

**File**: `src/dpsim/module3_performance/monitor_source.py`.

**UI consumers**: zero. The streaming monitor uses the legacy `parse_csv` + `replay()` path.

**Architectural fix**: refactor `tabs/tab_m3_monitor.py` to consume `MonitorSource` instead of `parse_csv` directly. Expose a *Source* dropdown with `csv_replay` / `simulated` / `null`. Reserve a fourth slot for future `unicorn_socket` per the ADR-008 deferral.

**Severity**: **MEDIUM**.

### A-8 · `monte_carlo_step_program` (B-2r/W-050) unused by UI

**File**: `src/dpsim/module3_performance/pressure_envelope_mc.py` (the multi-step variant).

**UI consumers**: forward MC panel calls only `monte_carlo_pressure_envelope` (single-step), per `tabs/calibration/forward_mc.py:28`.

**Architectural fix**: extend the forward MC panel with a *single-step / multi-step coupled* radio. Multi-step uses `monte_carlo_step_program` with shared draws across recipe steps for correlated step-to-step uncertainty per ADR-007 §4.

**Severity**: **MEDIUM**.

### A-9 · Bare-isotherm classes (HIC, ProteinA, IMAC, SMA, CompetitiveLangmuir, CompetitiveAffinity) absent from `IsothermChoice`

**Files**: `module3_performance/isotherms/{hic,protein_a,imac,sma,competitive_langmuir,competitive_affinity}.py`.

**UI selection path**: only via internal `select_isotherm_from_fmc(fmc_hint)`; the user cannot set the hint.

**Architectural fix** (depends on A-2 landing first): extend `IsothermChoice` with `HIC`, `PROTEIN_A` and (optionally) bare `IMAC`/`SMA`/`COMPETITIVE_LANGMUIR`/`COMPETITIVE_AFFINITY`. Add corresponding sub-forms. Update the AST gate to cover the extended enum.

**Severity**: **HIGH** for HIC + ProteinA; **MEDIUM** for the bare modulated underlies.

---

## §3 — Session-state map + dispatch defects

I traced every `st.session_state[...]` write and read across `src/dpsim/visualization/`. Findings:

| Key | Writers | Readers | Verdict |
|---|---|---|---|
| `lifecycle_result` | `ui_workflow` (run completion) | `tab_m3.py`, `tab_m2.py`, `stage_panels.py` (validation ladder) | OK |
| `m3_pressure_envelope` | `tab_m3.py:786-792` (post-run cache, v0.8.5) | `tab_m3.py:247` (pressure indicator), v0.8.5 | OK |
| `m3_latest_dp_pa` | `tab_m3_monitor.py` (post-replay, v0.8.5) | `tab_m3.py:248` (pressure indicator) | OK |
| `m3_latest_state` | `tab_m3_monitor.py` (post-replay, v0.8.5) | none yet | **ORPHAN WRITER** — written but no reader. Either remove or wire into tier-banner. |
| `_jump_to_calibration_section` | `next_step_affordance.py` (button click) | `tab_calibration.py:110` (one-shot read-and-clear) | OK |
| `multi_column_envelope` | `tabs/calibration/multi_column.py:204` | `tabs/calibration/multi_column.py:178` (re-render cache) | OK (intra-tab) |
| `posterior_envelope` | `tabs/calibration/inverse_inference.py:205` | `tabs/calibration/inverse_inference.py:174` (round-trip into forward MC) + forward_mc.py | OK |
| `pressure_monitor_csv_upload` | streamlit `file_uploader` | implicit | OK |
| `_m3_column_for_envelope` | (unknown writer) | `tabs/tab_calibration.py:62` | **ORPHAN READER** — search for the writer; if absent, defect. |
| `m2_result` | `tab_m2.py` | `tab_m3.py:1040` | OK |
| `m3_mobile_phase` | (none) | (none, would be added by A-1) | NOT YET WIRED — A-1 fix |
| `m3_isotherm_spec` | (none) | (none, would be added by A-2) | NOT YET WIRED — A-2 fix |

### A-10 · Orphan session_state writer: `m3_latest_state`

Written at `tab_m3_monitor.py` (v0.8.5 B-3c) but no reader exists. Either remove the write or wire into the tier banner / next-step affordance to reflect the current monitor state.

**Severity**: LOW (defensive code; harmless but noisy).

### A-11 · Orphan session_state reader: `_m3_column_for_envelope`

Read at `tab_calibration.py:62`. I could not locate the writer. If absent, the calibration tab's column-geometry resolver returns None and silently fails over to a default — masking what should be a clear "configure M3 first" dependency.

**Architectural fix**: locate the writer; if absent, add one in the M3 tab's column-geometry input section.

**Severity**: MEDIUM.

---

## §4 — Duplicated state and parallel pre-flight

### A-12 · M3 tab does its own pre-flight envelope, parallel to the lifecycle's

**Evidence**: `tab_m3.py:1051-1056` calls `compute_pressure_envelope` directly; `lifecycle/orchestrator.py:783` calls it again as part of the lifecycle's pre-flight. The two computations can disagree if the M3 tab's mobile phase / column / Q diverges from what the lifecycle ultimately runs.

**Architectural fix**: have a single source-of-truth for the pre-flight envelope. The M3 tab should display from `st.session_state["m3_pressure_envelope"]` (cached by either the explicit pre-flight button or the lifecycle run). Remove the parallel compute at line 1051.

**Severity**: MEDIUM.

### A-13 · Recipe geometry vs M3-tab geometry can diverge

**Evidence**: the recipe object passed to `render_lifecycle_run_panel` contains a column geometry. The M3 tab also renders geometry inputs. Today there is no enforcement that the M3-tab geometry the user sees is the same as the recipe geometry the lifecycle will use.

**Architectural fix**: lift M3 geometry inputs to write through to the recipe; render the recipe-resolved geometry in the M3 tab as read-only confirmation.

**Severity**: MEDIUM.

---

## §5 — Decision-grade routing inconsistency

The decision-grade tier ladder (`core/decision_grade.py`) is the right primitive. Application is inconsistent.

### A-14 · `render_pressure_indicator` does not route through `render_decision_grade_annotation`

**Evidence**: the v0.8.5 indicator computes colour-by-headroom inline (`pressure_indicator.py:_band`) but does not call `render_decision_grade_annotation`. The displayed number does not visually carry the SEMI_QUANTITATIVE interval bracket the ADR-policy ladder would require.

**Architectural fix**: route the displayed value through `render_decision_grade_annotation` with `OutputType.PRESSURE_PA` (or add a new `PRESSURE_READING` member if the existing one is reserved for predictions).

**Severity**: MEDIUM.

### A-15 · Bare `st.metric` calls without tier annotation

**Examples**: `tab_m3.py:1140-1145` (cycle lifetime), various M2 widgets, M1 modulus / d50 / porosity displays.

**Architectural fix**: per-call audit. Replace bare `st.metric(...)` with `render_metric(..., output_type=..., tier=...)`. The CHANGELOG should mention each replacement explicitly.

**Severity**: MEDIUM.

---

## §6 — IA / placement defects

### A-16 · Multi-column series builder placed in Calibration & Uncertainty

**Diagnosis**: this is a design-time tool, not a calibration activity. Per Phase 2 §U-18.

**Architectural fix**: hoist `tabs/calibration/multi_column.py` to a top-level *Series Design* sub-tab inside M3, or create a top-level *Inverse / Series Design* stage that hosts both the OptimizationEngine UI (A-6) and the multi-column builder.

**Severity**: LOW (functional today; misleads on intent).

### A-17 · Pre-flight pressure envelope panel is on the post-run *Results* page

**Diagnosis**: per ADR-004 §3, the envelope is a *pre-flight* check. Today it appears at `tab_m3.py:786+` after `lifecycle_result` is in session_state.

**Architectural fix**: render a compact pre-flight envelope panel in the M3 tab's *configure* section (above the Run button). Keep the detailed post-run envelope panel as the audit-trail surface.

**Severity**: HIGH for practitioners (per Phase 2 §U-11).

### A-18 · `tab_m3.py` at 1198 LOC violates the v0.8.4 decomposition principle

**Diagnosis**: the v0.8.4 architect decomposition extracted six new panels but did not pull existing M3 sub-sections out of the 1198-line file. Adding the v0.8.5 indicator wire-up went into the same file.

**Architectural fix**: incremental split — `tabs/m3/` directory containing `geometry_section.py`, `mode_section.py`, `monitor_section.py` (already moved), `results_section.py`, `lifetime_section.py`, with `tab_m3.py` as the orchestrator. Keep the file under 250 LOC.

**Severity**: LOW (technical debt, not blocking).

---

## §7 — ADR enforcement audit

| ADR | Invariant | Enforcement at v0.8.5 |
|---|---|---|
| ADR-001 (Python pin) | Py 3.11/3.12 only | `__init__.py:35` runtime check ✓ |
| ADR-002 (optim stack pin) | botorch~=0.17.2 etc. | pyproject.toml ✓; smoke test ⚠ requires torch installed |
| ADR-003 (POCl3 rejection) | tier-4 reject of POCl3 | applied in M2 reagent matrix ✓ |
| ADR-004 (per-family u_crit) | u_crit anchor for ΔP_max,op | `pressure_envelope.py:329` ✓ |
| ADR-005 (salt-modulated isotherm) | salt-aware K_eq | `isotherms/salt_dependent.py` ✓ but **not user-selectable** (A-2) |
| ADR-006 (full SMA promotion) | salt-modulated SMA | `isotherms/sma_modulated.py` ✓ but **not user-selectable** (A-2) |
| ADR-007 (MC pressure envelope) | forward MC | wired ✓; multi-step coupled is **orphan** (A-8) |
| ADR-008 (MonitorSource Protocol) | hardware-agnostic monitor | backend ✓; **UI bypasses** (A-7) |
| ADR-009 (multi-column series) | series envelope | wired ✓ (placement issue A-16) |
| ADR-010 (inverse Bayesian) | importance-sampling posterior | wired ✓; ESS warning is post-hoc (Phase 1 §S-12) |
| ADR-011 (correlated MC priors) | log_cov | wired ✓ |

**Verdict**: ADR machinery is sound; UI exposure of ADR-005, 006, 008 invariants is **broken or partial** through the wiring defects A-2 and A-7.

---

## §8 — README claims vs reality

(Cross-check sample.)

| README claim | UI reality |
|---|---|
| *"Pre-flight pressure envelope"* | Implemented post-run, not pre-run (A-17) |
| *"Five isotherm classes"* | Defined in `IsothermChoice` but not user-selectable (A-2) |
| *"Mobile-phase composition editor"* | Widget defined; not mounted (A-1) |
| *"SEMI_QUANTITATIVE banner at every stage"* | Defined; not mounted (A-3) |
| *"Forward + inverse Bayesian round-trip"* | Wired ✓ (per Phase 1 §S-12 caveat) |
| *"Multi-column series envelope"* | Wired ✓ (placement A-16) |
| *"Decision-graded outputs"* | Inconsistent (A-14, A-15) |
| *"AKTA UNICORN integration (v0.9)"* | Correctly deferred per ADR-008 ✓ |

The README's promises that are **structurally** unmet at v0.8.5: 5 of the 8 sampled.

---

## §9 — Test-coverage architecture gaps

* **Property tests for tier-honesty**: no test asserts that every UI panel that surfaces a number routes through `render_metric` or `render_decision_grade_annotation`. The AST gate only checks enum-comparison. Tier-routing should be a parallel CI gate.
* **Integration test that mounts widgets**: `test_isotherm_selector.py` exercises the widget in isolation but not in production. There is no test that asserts *"if `render_isotherm_widget` is defined, then it is called from at least one production tab"*. This class of test would have caught A-1, A-2, A-3.
* **End-to-end smoke test for the mobile-phase → envelope chain**: there is no test asserting that user-supplied mobile phase changes the envelope output. Today, that property is silently violated; A-1+A-4 fixes restore it but a regression test should accompany.
* **README contract test**: no test mechanically reads the README's claim list and verifies each is reachable from a production import path.

---

## §10 — Summary defect ledger

| ID | Title | Severity | v0.8.6 / v0.8.7 / v0.9 | Phase 1 mapping | Phase 2 mapping |
|---|---|---|---|---|---|
| A-1 | mobile-phase widget unmounted | CRITICAL | v0.8.6 | S-1 | U-8 |
| A-2 | isotherm widget unmounted | CRITICAL | v0.8.6 | S-2 | U-9 |
| A-3 | tier banner unmounted | CRITICAL | v0.8.6 | S-3 | U-10 |
| A-4 | ui_workflow doesn't thread mobile_phase / isotherm_spec | CRITICAL | v0.8.6 | S-4 | (gates U-8/U-9) |
| A-5 | detection modules orphan | HIGH | v0.8.7 | S-6 | U-13 |
| A-6 | OptimizationEngine UI absent | HIGH | v0.8.7 | S-7 | U-20 |
| A-7 | MonitorSource Protocol unused | MEDIUM | v0.8.7 | S-8 | U-21 |
| A-8 | multi-step coupled MC orphan | MEDIUM | v0.8.7 | S-9 | — |
| A-9 | bare-isotherm classes inaccessible | HIGH | v0.8.7 | S-5 | (refines U-9) |
| A-10 | orphan writer `m3_latest_state` | LOW | v0.9 | — | — |
| A-11 | orphan reader `_m3_column_for_envelope` | MEDIUM | v0.9 | — | — |
| A-12 | parallel pre-flight envelope compute | MEDIUM | v0.9 | — | (related U-11) |
| A-13 | recipe vs M3-tab geometry divergence | MEDIUM | v0.9 | S-13 | U-7 |
| A-14 | pressure indicator no decision-grade routing | MEDIUM | v0.9 | S-10 | U-12 |
| A-15 | bare `st.metric` without tier | MEDIUM | v0.9 | S-10 | U-4 |
| A-16 | multi-column builder mis-placed in Calibration | LOW | v0.9 | — | U-18 |
| A-17 | pre-flight panel on post-Run page | HIGH | v0.9 | S-11 | U-11 |
| A-18 | tab_m3.py 1198 LOC | LOW | v0.9 | — | — |

---

## §11 — Disclaimer

This architecture analysis is provided for informational and development purposes only. The findings were derived by static cross-checking; some claims (notably orphan-reader / orphan-writer) require runtime verification under a live Streamlit session before remediation work commits. Each defect closure should be paired with a regression test that asserts the wired property end-to-end, not just the unit behaviour.
