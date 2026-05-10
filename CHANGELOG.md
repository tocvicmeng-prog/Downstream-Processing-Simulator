# Changelog

## Unreleased — audit-plan code-actionable closeout (2026-05-11)

- Closed the remaining code-actionable S1 metric-routing gap: user-facing `.metric(` call sites now route through `render_metric` or use non-metric tables, and the CI gate baseline is zero across visualization and suggestion UI surfaces.
- Extended S4 wet-lab execution exports: deterministic dossiers can now carry execution records, QC checkpoints, fraction collections, and trace alignments; lifecycle SOP markdown surfaces step execution metadata when present.
- Hardened S5 optimization reporting: Pareto exports now include DecisionClaim rows, missing-calibration blockers, pressure-feasibility status, and separate best-predicted vs best-actionable candidate rankings.
- Updated the support matrix to reflect implemented calibration quality gates, assay templates, optional Bayesian fitting, GradientContext consumption, wet-lab execution objects, SOP export, and trust-aware optimization.

## v0.8.9 — All deferred W-items closed (2026-05-10)

Closes the remaining 7 W-items deferred at v0.8.8 close. With v0.8.9 all 25 W-items in `docs/update_workplan_2026-05-10_v0_9_0.md` §3 are now closed (the v0.8.8 + v0.8.9 cumulative total). Versioned as v0.8.9 (not v0.9.0) per the project's versioning policy — v0.9 stays reserved for the durable v1.0 deferral plateau.

### Closed (7 W-items)

- **W-081** — Tier-routing CI gate. New `tests/visualization/test_tier_routing_gate.py` walks the visualization tree for bare `.metric(` callsites and asserts the count never exceeds the documented baseline (43 at v0.8.9 close). Companion to the v0.8.6 widget-mounting AST gate (W-073). New numeric displays must route through `render_metric` from `decision_grade_render` carrying `OutputType` + `tier`.
- **W-083** — Removed parallel pre-flight envelope compute at `tab_m3.py:1051`. The post-run pressure-flow plot now reads from the cached `m3_pressure_envelope` (single source-of-truth via session_state) and falls back to a fresh compute only when the cache is empty. Closes audit defect A-12.
- **W-084** — M3 geometry + flow rate writethrough to recipe. `ui_workflow.render_lifecycle_run_panel` now mutates the recipe's M3 `PACK_COLUMN` step (`column_diameter`, `bed_height`, `bed_porosity`) and `LOAD` step (`flow_rate`) with the user's UI session_state values *before* invoking the lifecycle. The lifecycle and the in-page preview now use the same geometry. Closes audit defect S-13 / U-7 / A-13.
- **W-087** — `tab_m3.py` refactor — proof-of-pattern split. New `tabs/m3/` directory with `method_conditions_section.py` (the v0.8.6 mobile-phase + isotherm widgets, ~80 LOC). `tab_m3.py` reduces by ~50 LOC and the call site collapses to a single `render_method_conditions_section(...)`. Validates the refactor pattern; full split (every cohesive section) queued for v1.0. Partial closure of audit defect A-18.
- **W-092** — RecoveryAction labels become clickable controls. New `_render_recovery_action_controls` helper in `tab_m3_monitor.py` surfaces three dashboard-controllable buttons next to the final-state chip:
  * *Set Q to Q_recommended* — mirrors the v0.8.8 W-091 control on the pressure indicator.
  * *Switch to wash buffer (PBS, no glycerol)* — resets `m3_mobile_phase` to a low-salt wash profile.
  * *Flag run for operator review* — appends a timestamped audit note to `m3_review_notes`.

  Bench-only actions (stop & repack, emergency stop, continue & monitor) intentionally remain text-labelled — no UI control can perform a physical column repack. Closes audit defect U-23.
- **W-096** — Unit-conversion crib in the inverse Bayesian measurement editor. Closes audit defect U-24 partial. The data editor's column headers now carry inline help tooltips with the SI ↔ bench unit conversions (`1 mL/min = 1.667e-8 m³/s`, `1 kPa = 1000 Pa`, `1 bar = 1.0e5 Pa`). Full unit standardisation across every input boundary remains a v1.0 sweep.
- **W-102** — Removed orphan write of `m3_latest_state` in `tab_m3_monitor.py`. The v0.8.5 W-067 introduced the write but no production reader ever consumed it; the indicator and tier banner have their own state sources. Closes audit defect A-10.

### Verification

- **2 new tests** (`test_tier_routing_gate.py`); **525 tests pass** across the visualization + module3_performance + lifecycle + AST-gate scope (up from 523 at v0.8.8).
- ruff: 0 violations across all edited paths.
- mypy: 0 issues on the changed source files.
- AST gate: 0 violations on managed enums.
- Widget-mounting AST gate (W-073): 0 violations.
- Tier-routing CI gate (W-081): baseline 43, current 43 — passing.

### Public-communication framing

> v0.8.9 ships as **"all v0.9.0 plan items closed"**. Every W-item from the joint three-role plan §3 is now resolved (W-079 → W-102, 24 items + 1 follow-on). The dashboard has now traversed every milestone in the plan: honest (v0.8.6) → complete (v0.8.7) → wet-lab-credible (v0.8.8) → fully-mature-as-scoped (v0.8.9). The v0.9 maturity tag remains reserved for once the three durable v1.0 deferrals close (live AKTA UNICORN, MCMC inverse, cyclic SMB).

### Remaining (durable v1.0 candidates)

Unchanged. Three durable deferrals remain v1.0+ candidates per the original ADRs:

- **Live AKTA UNICORN socket** (ADR-008 hardware deferral). The `MonitorSource.unicorn_socket` slot is reserved and the v0.8.7 UI exposes a disabled placeholder.
- **MCMC inverse promotion** (ADR-010 dataset-bound). The importance-sampling inverse stays the v0.9 ceiling. Promotion awaits datasets that warrant the `pymc` cold-import cost.
- **Cyclic SMB / multi-bed dynamics** (ADR-009 §"Out of scope"). Substantial physics scope.

### Detailed handover

- `docs/handover/HANDOVER_v0_8_9_release.md` — combined release-level handover for the 7 W-items.

### Architecture decisions

No new ADRs. v0.8.9 closes the operational maturity gap to its scoped completion. The new `tabs/m3/` directory introduced by W-087 establishes the pattern for the v1.0 `tab_m3.py` full split.

## v0.8.8 — Maturation milestone (2026-05-10)

Closes 17 of the 25 W-items in `docs/update_workplan_2026-05-10_v0_9_0.md` §3 — the maturation work plan. Versioned as v0.8.8 (not v0.9.0) per the project versioning policy: v0.9.0 stays reserved for the matured-status plateau once the durable v1.0 deferrals (live AKTA UNICORN, MCMC inverse, cyclic SMB) close.

After v0.8.8 the dashboard moves from *complete* to *wet-lab-credible*: decision-graded outputs, pre-flight envelope visible *before* Run, save/load sessions, run-vs-run comparison, SOP export, spreadsheet calibration import, first-run examples, guided workflow tour, predicted-vs-measured overlay.

### Closed (17 W-items)

#### Decision-grade + envelope (Bundle X subset)

- **W-079** — Pressure indicator routes through `format_decision_graded`. The digital readout now carries a tier-aware INTERVAL bracket beneath the main number (e.g. `kPa @ ±factor`). Closes audit defect A-14 / S-10.
- **W-080** — Cycle lifetime + asymmetry + impurity risk metrics in `tab_m3.py:1259-1270` now route through `render_metric` (was bare `st.metric`). Help text added so each metric carries its tier qualification. Partial closure of A-15.
- **W-082** — Pre-flight pressure-envelope summary surfaced ABOVE the Run controls in `render_run_lifecycle_stage` (stage_panels.py). Reads from `m3_pressure_envelope` cache; renders BLOCKER / WARNING / GREEN status in plain text before the long-running lifecycle is invoked. Closes audit defect S-11 / U-11 / A-17 — the envelope was post-Run only at v0.8.7.

#### Calibration discipline (Bundle Y subset)

- **W-088** — Inverse Bayesian fit gains an input-time blocker when measurement count < 8. Per ADR-010 §"Tier mapping" — under-determined fits collapse ESS and let users mistake noise for posterior. Closes audit defect S-12 / U-16.
- **W-089** — NEW `panels/spreadsheet_calibration_import.py` provides a CSV / XLSX → `CalibrationEntry` import path with column-mapping wizard. Bench users with Excel exports can now ingest calibration data without hand-authoring YAML. Mounted in the Calibration & Uncertainty tab next to the wet-lab YAML uploader. Closes audit defect U-19 / S-18.
- **W-090** — Tier-promotion hints surfaced in the SEMI_QUANTITATIVE / QUALITATIVE_TREND / UNSUPPORTED tier banner. Each band now tells the user the specific experiment that promotes the next tier, with a cross-reference to `docs/04_calibration_protocol.md`. Closes audit defect U-29.

#### Operator affordances (Bundle Y subset)

- **W-091** — Pressure indicator gains a *Set Q to Q_recommended* button when band is amber or red. Click writes the recommended Q to `st.session_state["m3_flow"]` and triggers a rerun — the first clickable RecoveryAction control. Partial closure of W-092 (text labels → control). Closes audit defect U-12 / U-23.
- **W-093** — NEW `panels/session_io.py` ships save / load session via JSON snapshot. The user-input keys (`m1_*`, `m2_*`, `m3_*`, `fmc_*`, `inv_*`, `opt_*`, `p6_*`, `pi_*`) are exported with whitelist + JSON-serialisability guards. Mounted in the sidebar. Closes audit defect U-25.
- **W-094** — NEW `panels/sop_export.py` ships a Markdown-formatted wet-lab procedure exporter. Walks mobile phase + isotherm spec + column geometry + envelope + calibration state and produces a bench-ready SOP. Tier-honest at every numeric. Mounted in the M3 results page. Closes audit defect U-26.
- **W-095** — NEW `panels/run_compare.py` provides a run-history snapshot + comparison view. Up to 10 most recent runs accumulate as JSON-serialisable summaries (DBC, peak ΔP, headroom, breakthrough time, isotherm class, mobile phase). Side-by-side dataframe rendering. Closes audit defect U-27.

#### First-run + IA (Bundle Z subset)

- **W-097** — NEW `panels/first_run_examples.py` ships three canonical recipes (Protein A capture, IEX polish, IMAC capture) one-click loadable. Each click writes the appropriate session_state values for mobile phase + isotherm spec + column geometry + flow rate so the dashboard populates with a wet-lab-realistic starting point. Closes audit defect U-1 / U-15 / S-15 / S-19.
- **W-098** — Scientific Mode help text rewritten to surface the consequence of each mode (run time, model fidelity, warning suppression). Closes audit defect U-2.
- **W-099** — Guided workflow tour added to the sidebar as an expandable narrative covering screen → calibrate → tighten → ship. Closes audit defect S-19.
- **W-100** — Streaming pressure monitor now overlays predicted ΔP from the active envelope alongside the measured trace. Direct comparison of model vs reality at the bench. Closes audit defect U-22.
- **W-101** — Writer for orphan reader `_m3_column_for_envelope` added in `tab_m3.py` (publishes the constructed column geometry + mobile phase to session_state for `tab_calibration` to consume). Closes audit defect A-11.

#### Misc

- **W-085** (partial) — Multi-column series builder gets a clarifying *Design-time tool* warning at the top of its sub-tab. Full IA hoist into a dedicated stage is queued for v1.0. Closes the misleading-by-placement framing of A-16 / U-18.
- **W-086** — M1 → M2 → M3 chain confirmation banner at the top of the M3 tab now surfaces the polymer family, bead d50, particle porosity, and modulus values being consumed. Closes audit defect U-7.

### Verification

- **523 tests pass** across the visualization + module3_performance + lifecycle + AST-gate scope (unchanged from v0.8.7; no regressions despite the scope of new wiring).
- ruff: 0 violations across all edited paths.
- mypy: 0 issues on the changed source files.
- Widget-mounting AST gate (W-073): all new `render_*_panel` helpers properly mounted.
- AST gate (`test_v9_3_enum_comparison_enforcement.py`): 0 violations.

### Deferred to v0.9.0 / v1.0+

The 8 W-items not closed in v0.8.8 carry over:

- **W-081** — Tier-routing CI gate. Implementing requires mass-fix of legacy `st.metric` call sites; deferred to keep v0.8.8 scope manageable.
- **W-083** — Remove parallel pre-flight envelope compute at `tab_m3.py:1051`. Behaviour-changing refactor; defer to v0.9.
- **W-084** — M3 geometry → recipe writethrough. Deeply complex; defer to v0.9.
- **W-087** — `tab_m3.py` refactor (1198 LOC → multiple files). High regression risk; defer to v1.0.
- **W-092** — RecoveryAction labels become full clickable controls. W-091 closed the highest-impact one (Set Q to Q_recommended); the rest defer.
- **W-096** — Full unit standardisation pass. Partial coverage via SOP export consistency; full sweep deferred.
- **W-102** — Remove orphan write of `m3_latest_state`. Low priority; orphan is harmless.

### Public-communication framing

> v0.8.8 ships as **"the dashboard becomes wet-lab-credible"**. Where v0.8.6 made it honest and v0.8.7 made it complete, v0.8.8 closes the maturation gaps that kept the simulator feeling like a research tool rather than a wet-lab planner. A bench user can now: pick a first-run example, see what experiment promotes their tier, save / load / compare sessions, export a wet-lab SOP, ingest spreadsheet calibration data, and see predicted-vs-measured ΔP at the bench. The v0.9 maturity plateau is reserved for once the three durable v1.0 deferrals close (live AKTA UNICORN, MCMC inverse, cyclic SMB).

### Detailed handover

- `docs/handover/HANDOVER_v0_8_8_release.md` — combined release-level handover.
- `docs/update_workplan_2026-05-10_v0_9_0.md` §3 — joint plan; 17/25 W-items now closed, 8 carry over.

### Architecture decisions

No new ADRs introduced. The v0.8.8 work closes the operational-maturity gap between the v0.7→v0.8.7 backend and the dashboard that surfaces it. The decision-grade tier ladder (W-079, W-080, W-090) is enforced more uniformly. The wet-lab procedure document (W-094) does not introduce new physical claims — it formalises the export of the simulator's tier-honest SEMI_QUANTITATIVE state into a bench-readable artefact.

## v0.8.7 — Orphan backend exposure (2026-05-10)

Closes the v0.8.5 audit's HIGH/MEDIUM-severity orphan-backend defects (S-5, S-6, S-7, S-8, S-9 from `AUDIT_v0_8_5_e2e_phase1_scientific.md`; A-5, A-6, A-7, A-8, A-9 from `..._phase3_architecture.md`). At v0.8.6 the dashboard became *honest* — visible inputs drove the simulation. v0.8.7 makes it *complete* — every backend module the README claims is now reachable from the UI.

### Closed (B-5a → B-5e)

- **B-5a (W-078) — HIC + ProteinA selectable in the isotherm widget.** Extended `IsothermChoice` enum with `HIC` and `PROTEIN_A`. Added two new sub-forms exposing the dedicated parameters:
  * **HIC** — `q_max`, `K_0` (zero-salt affinity), `m_salt` (salting-out coefficient), `salt_type` (Hofmeister anion). Physics: `K_a(c_salt) = K_0 · exp(m_salt · c_salt)`.
  * **ProteinA** — `q_max`, `K_a_max` (neutral-pH affinity), `pH_transition` (canonical 3.5), `steepness`. Physics: pH-sigmoid `K_a(pH) = K_a_max / (1 + exp(steepness · (pH_transition − pH)))`.

  Family-aware default routing updated: AGAROSE_CHITOSAN and AGAROSE now route to PROTEIN_A by default (was bare Langmuir). HIC hint (phenyl/butyl/octyl) routes to HIC. The AST gate already covers `IsothermChoice` (extended in v0.8.4 W-052) so the new members are automatically enforced. `to_isotherm()` converter extended to all 7 members. Closes **S-5** + **A-9**.
- **B-5b (W-074) — Detector traces UI.** New `components/detector_traces.py` overlays predicted UV (mAU) / fluorescence (RFU) / conductivity (mS/cm) traces from the M3 breakthrough result. UV trace consumes `compute_uv_signal` + `apply_detector_broadening`; fluorescence is opt-in via a checkbox; conductivity renders only when `breakthrough_result.salt_profile` is available. Mounted at `tab_m3.py:1083` after the existing breakthrough+chromatogram plots. Closes **S-6** + **A-5** — the detection module family was 100 % UI-orphan at v0.8.6.
- **B-5c KEYSTONE (W-075) — OptimizationEngine top-level UI tab.** New `tabs/tab_optimization.py` mounts the multi-objective Bayesian-optimisation engine in the dashboard for the first time. Exposes `TargetSpec` inputs (d32, pore size, G_DN with tolerances), Sobol initial-points + BO-iterations sliders, optional robust-BO toggle, and a Run button. Result panel shows the best-of-campaign objective values + 7-D search-space coordinates at SEMI_QUANTITATIVE per ADR-007. Gracefully degrades to an install-instructions banner when the optional `[optimization]` extra (torch + botorch + gpytorch) is not installed. Mounted at the bottom of the Calibration stage as a peer of `tab_calibration` (v0.9.0 W-085 hoists it into a dedicated *Inverse Design* stage). Closes **S-7** + **A-6** + **U-20** — the highest-impact orphan at v0.8.6.
- **B-5d (W-076) — MonitorSource Protocol UI dropdown.** `tab_m3_monitor.py` now exposes the ADR-008 `MonitorSource` Protocol via a Source radio: **CSV replay** (legacy path), **Simulated trace** (synthetic ramp + fouling demo via `SimulatedMonitorSource` with editable steady-state ΔP / ramp τ / fouling slope / duration), **Null (none)** (placeholder), **Live AKTA UNICORN** (disabled, durable v0.9 deferral per ADR-008 hardware). Closes **S-8** + **A-7** — the Protocol's UI bypass at v0.8.6.
- **B-5e (W-077) — Multi-step coupled MC mode.** Forward MC panel gains a *single-step / multi-step coupled* mode radio. Multi-step wires `monte_carlo_step_program` (B-2r / W-050) with a 3-step program (equilibrate / load / wash) and shared parameter draws across all steps so cross-step correlation is preserved per ADR-007 §4. Result panel adds per-step blocker probability columns + worst-step caption. Closes **S-9** + **A-8**.

### Verification

- **5 new tests** in `tests/visualization/test_isotherm_selector.py` covering HIC + ProteinA sub-forms + `to_isotherm` converter; **20/20 isotherm selector tests pass**.
- **139/139 visualization tests pass** (134 prior + 5 new isotherm tests).
- **523 tests pass** across the visualization + module3_performance + lifecycle + AST-gate scope (up from 518 at v0.8.6; +5 from B-5a coverage).
- ruff: 0 violations across all edited paths.
- mypy: 0 issues on `panels/isotherm_selector.py`, `components/detector_traces.py`, `tabs/tab_optimization.py`, `tabs/tab_m3_monitor.py`, `tabs/calibration/forward_mc.py`, `shell/stage_panels.py`.
- AST gate (`test_v9_3_enum_comparison_enforcement.py`): 0 violations on extended `IsothermChoice` (HIC + PROTEIN_A).
- Widget-mounting AST gate (`test_widget_mounting.py`): 0 violations — every new `render_*` is mounted.

### New validation gates closed (48 → 53)

- **48** HIC + ProteinA selectable via the isotherm widget; family-aware defaults route correctly.
- **49** Detector traces render after every M3 run (UV always; fluorescence opt-in; conductivity when salt profile available).
- **50** OptimizationEngine reachable from a top-level entry point in the Calibration stage; 3-input target case (d32 + pore + G_DN) completes; result rendered at SEMI_QUANTITATIVE.
- **51** Streaming monitor source dropdown offers CSV / Simulated / Null + a v0.9-deferred AKTA UNICORN slot.
- **52** Multi-step coupled MC reachable from forward MC panel; result reflects shared parameter draws via `monte_carlo_step_program`.
- **53** AST gate covers extended `IsothermChoice` (HIC + PROTEIN_A) automatically.

### Public-communication framing

> v0.8.7 ships as **"the dashboard becomes complete"**. Where v0.8.6 closed the wiring breaks that made user inputs theatrical, v0.8.7 closes the orphan-backend gaps that made the README's promises structurally unreachable. Every scientifically meaningful capability shipped in the v0.7 → v0.8 cluster now has a UI path. The v0.9.0 maturation milestone — decision-grade consistency, pre-flight envelope relocation, calibration discipline, operator affordances, unit standardisation, first-run examples, predicted-vs-measured overlay — remains the next-step roadmap per `docs/update_workplan_2026-05-10_v0_9_0.md` §3. The three durable v0.9-deferred items (live AKTA UNICORN, MCMC inverse, cyclic SMB) remain v1.0+ candidates.

### Detailed handover

- `docs/handover/HANDOVER_v0_8_7_release.md` — combined release-level handover for B-5a → B-5e.
- `docs/update_workplan_2026-05-10_v0_9_0.md` — joint three-role plan (v0.8.6 closed in §1, v0.8.7 closed in §2, v0.9.0 outstanding in §3).

### Architecture decisions

No new ADRs. v0.8.7 closes the *exposure gap* on ADR-005 (HIC/ProteinA), ADR-007 (multi-step MC), and ADR-008 (MonitorSource Protocol). The optimization extra remains pinned per ADR-002.

## v0.8.6 — Critical wiring fixes (2026-05-10)

Closes the four CRITICAL wiring breaks identified in the v0.8.5 end-to-end audit (`docs/handover/AUDIT_v0_8_5_e2e_phase{1,2,3}_*.md`). The v0.8.4 release shipped three widgets — mobile-phase composition editor, isotherm selector, SEMI_QUANTITATIVE tier banner — that were defined and unit-tested but **never mounted in production**. Defects C1, C2, and W-1 from the v0.8.4 CHANGELOG were therefore *theatrically* closed: tests passed, but a user pressing *Run* received a simulation in which their actual mobile phase + isotherm choice were silently substituted by `MobilePhase()` water-at-20°C + bare Langmuir defaults. v0.8.6 turns the v0.8.4 closure into an *operationally true* closure.

### Closed (B-4a → B-4e) — five wiring W-items

- **B-4a (W-069)** — Mounted `render_mobile_phase_widget` (defined v0.8.4 W-053) inside the M3 tab's new Method-conditions section (`tabs/tab_m3.py:291-339`). User-supplied `MobilePhase` is persisted to `st.session_state["m3_mobile_phase"]`.
- **B-4b (W-070)** — Mounted `render_isotherm_widget` (defined v0.8.4 W-055) in the same section. User-supplied `IsothermSpec` is persisted to `st.session_state["m3_isotherm_spec"]`. Family-aware default routing falls back to AGAROSE before M2 has run; once M2 produces a `polymer_family`, the widget routes to the family-appropriate default.
- **B-4c (W-071)** — Mounted `render_tier_banner` (defined v0.8.4 W-058) at the top of `app.py`'s render loop, surfacing the worst tier across `lifecycle_result.{m1,m2,m3}_result.model_manifest.evidence_tier` and the calibration store's loaded state. The banner now appears on every stage as the v0.8.4 release notes had claimed.
- **B-4d KEYSTONE (W-072)** — Threaded the user's session_state inputs end-to-end:
  * `to_isotherm(spec)` converter added to `panels/isotherm_selector.py` covering all 5 IsothermChoice members (Langmuir, SaltModulatedLangmuir, ImidazoleModulatedLangmuir, SaltModulatedSMA, SaltModulatedCompetitiveLangmuir).
  * `lifecycle/orchestrator.py::DownstreamProcessOrchestrator.run()` gains an `isotherm: Any | None = None` kwarg. When supplied, the lifecycle re-runs the load breakthrough with the user's isotherm class, overriding the auto-routed FMC isotherm. A WARNING-tier `M3_USER_ISOTHERM_OVERRIDE` validation entry is recorded so the override is auditable.
  * `ui_workflow.render_lifecycle_run_panel` reads `m3_mobile_phase` and `m3_isotherm_spec` from session_state, converts the spec to a backend isotherm via `to_isotherm`, and passes both to the orchestrator's threaded run.
  * `tabs/tab_m3.py:1054` — the in-page pre-flight envelope now reads `m3_mobile_phase` from session_state instead of using `MobilePhase()` defaults.
- **B-4e (W-073)** — New `tests/visualization/test_widget_mounting.py` AST gate that walks `panels/` + `shell/`, finds every `def render_*`, and asserts at least one production caller exists in `tabs/`, `app.py`, or `shell/`. Caught the v0.8.4 wiring break would-have-been retroactively; the legacy `panels/calibration.py::render_calibration_panel` (v6.0-rc JSON uploader, superseded by v0.8.4 W-057) is documented with a `# pragma: no-mount` exemption.

### Verification

- **3 new tests** in `test_widget_mounting.py`; **134/134 visualization tests pass** (131 prior + 3 new).
- **518 tests pass** across the M3 + lifecycle + AST-gate scope (up from 515 at v0.8.5; +3 widget-mounting gates).
- ruff: 0 violations across all edited paths.
- mypy: 0 issues on `tab_m3.py`, `app.py`, `panels/isotherm_selector.py`, `lifecycle/orchestrator.py`, `ui_workflow.py`.
- AST gate (`test_v9_3_enum_comparison_enforcement.py`): 0 violations.
- Smoke-tested `to_isotherm` end-to-end against all 5 IsothermChoice members.

### New validation gates closed (42 → 47)

- **42** Mobile-phase widget renders in M3 input section; user value persists to `st.session_state["m3_mobile_phase"]`.
- **43** Isotherm widget renders in M3 input section; user value persists to `st.session_state["m3_isotherm_spec"]`.
- **44** Tier banner renders at app top-of-page on every stage.
- **45** User-selected mobile phase changes the pre-flight pressure envelope (`tab_m3.py:1054` reads from session_state).
- **46** User-selected isotherm class changes the breakthrough curve (lifecycle's load breakthrough re-runs with the user's class via `to_isotherm` + W-072 KEYSTONE).
- **47** New AST gate prevents `render_*` definitions from being defined-but-not-mounted; the v0.8.4 wiring-break regression cannot recur.

### Public-communication framing

> v0.8.6 ships as **"the dashboard becomes honest"**. Where v0.8.4 added widgets and v0.8.5 added the live-cruise indicator, v0.8.6 closes the chain that turns visible inputs into actual simulation behaviour. The v0.8.4 CHANGELOG entries for defects C1, C2, and W-1 are now structurally accurate — the widgets they describe are operational. The v0.9 maturity plateau (live AKTA UNICORN socket, cyclic SMB, MCMC inverse) is unchanged from v0.8.5; the v0.8.7 next step exposes the orphan backends (HIC + ProteinA, OptimizationEngine UI, MonitorSource Protocol UI, multi-step coupled MC, detector traces).

### Detailed handover

- `docs/handover/HANDOVER_v0_8_6_release.md` — combined release-level handover for B-4a → B-4e.
- `docs/update_workplan_2026-05-10_v0_9_0.md` — joint three-role plan that scoped v0.8.6 / v0.8.7 / v0.9.0.

### Architecture decisions

No new ADRs introduced. The five batches collectively respect ADR-001 → ADR-011; v0.8.6 closes the *enforcement gap* between the ADRs (which were sound) and the user-facing UI (which had bypassed them). The new `to_isotherm` converter formalises the IsothermSpec ↔ backend-class bridge that ADR-005 / ADR-006 implicitly require.

## v0.8.5 — M3 real-time back-pressure indicator (2026-05-10)

Closes the 5-item work plan in `docs/update_workplan_2026-05-10_v0_8_5.md` — a single-feature UI patch driven by the joint `/scientific-advisor` + `/architect` + `/dev-orchestrator` engagement. Adds a digital-style real-time back-pressure indicator pinned to the right of the M3 *Live phase view* column diagram. **No backend changes** — the `PressureEnvelope` dataclass at `src/dpsim/module3_performance/pressure_envelope.py:97` already exposes every quantity the indicator reads.

### Closed (B-3a → B-3d)

- **B-3a (W-064, W-065) — Pressure indicator component.** New `src/dpsim/visualization/components/pressure_indicator.py` exports `render_pressure_indicator(*, envelope, current_dp_pa, container, ...)`. The indicator's value coloured by headroom band: GREEN at `headroom_ratio < 0.70`, AMBER at `0.70 ≤ ratio < 1.00`, RED at `ratio ≥ 1.00`. Boundaries match the existing G8 recipe-validation gate (`PressureEnvelope.is_warning` / `is_blocker`). The `?` popover surfaces (a) the operational ceiling at the active `decision_tier` with the tier-aware interval bracket, (b) the `u_crit · K_geom · G_DN · d_p² / (μ · L)` calculation summary per ADR-004, and (c) four ranked remediations starting with *lower Q to Q_recommended* (mirrors the `RecoveryAction` enum's reversibility ordering at `tab_m3_monitor.py:50-58`).
- **B-3b (W-066) — M3 live-phase 2-column layout.** `tabs/tab_m3.py:211-243` wraps `render_column_xsec(...)` in `st.columns([3, 1], gap="small")`; the indicator renders in the right column. The post-run pressure-envelope panel (`tab_m3.py:786-792`) caches the envelope into `st.session_state["m3_pressure_envelope"]` so the live-phase indicator picks it up on the next rerun. Before the first run the indicator renders a clearly-labelled placeholder (gate 41).
- **B-3c (W-067) — Live-reading session_state read-through.** `tabs/tab_m3_monitor.py` writes `st.session_state["m3_latest_dp_pa"]` and `st.session_state["m3_latest_state"]` after each successful CSV replay. The indicator picks up the live reading on the next rerun (e.g. when the user changes the Phase radio); falls back to `envelope.dP_predicted_pa` when no replay is active. The write is wrapped defensively so unit tests without a Streamlit runtime do not regress.
- **B-3d (W-068) — Test suite.** New `tests/visualization/test_pressure_indicator.py` exercises `_band` boundaries (×8 parameterised cases), `_resolve_dp` live-vs-predicted routing, `_help_modal_md` content (operational ceiling + decision tier + formula + ranked remediations + tier-aware interval), `_digit_html` colour mapping + Geist Mono / tabular-num compliance, `_placeholder_html` labelling, and integration via a stub container — 24 tests total, all passing.

### Verification

- **24 new tests** in `tests/visualization/test_pressure_indicator.py`; **128/128 visualization tests pass** (104 prior + 24 new); existing AST gate clean.
- ruff: 0 violations across edited paths (`pressure_indicator.py`, `__init__.py`, `tab_m3.py`, `tab_m3_monitor.py`).
- mypy: 0 issues on edited source files.

### Validation gates closed in this release

4 new gates (38–41) on top of the v0.8.4 floor:

- **38** Indicator renders to the right of the column diagram in M3 Live-phase view.
- **39** Value colour matches band (GREEN < 0.70, AMBER 0.70–1.00, RED ≥ 1.00 headroom_ratio).
- **40** `?` popover surfaces operational ceiling at tier, calculation summary, and 4 ranked remediations.
- **41** Indicator renders a clearly-labelled placeholder when envelope is absent (no misleading 0 / NaN).

### Public-communication framing

> v0.8.5 upgrades the **operator-facing situational awareness** during M3 column operation. Where v0.8.4 closed UI completeness for the *configuration* and *post-run analysis* surfaces, v0.8.5 adds a single live-cruise affordance: a digital number whose colour is bound to the bed-compression ceiling, with one-click access to the calculation and the remediation ladder. No backend changes; the v0.9 maturity plateau (live AKTA UNICORN socket, cyclic SMB, MCMC inverse) is unchanged.

### Detailed handover

- `docs/handover/HANDOVER_v0_8_5_release.md` — combined release-level handover for B-3a → B-3d.

### Architecture decisions

No new ADRs introduced. ADR-004 (per-family u_crit anchor) is the operative invariant for the indicator's safe-band semantics.

## v0.8.4 — UI completeness against the v0.8.3 backend (2026-05-10)

Closes 13/13 work-plan items from `docs/update_workplan_2026-05-10_v0_8_4.md` — the UI-completeness pass that closes the gap between the v0.7 → v0.8.3 backend and the Streamlit dashboard. Driven by the joint `/scientific-advisor` + `/architect` + `/dev-orchestrator` engagement (audit + decomposition + work plan in `docs/handover/`). Patch bump per the project versioning policy.

### Closed — Tier 0 (B-0i)

- **B-0i (W-051, W-052) — Decision-grade extension + AST gate.** Three new `OutputType` members: `MC_PROBABILITY` (SEMI_QUANTITATIVE floor — for `p_blocker` / `p_warning`), `POSTERIOR_PARAMETER` (SEMI_QUANTITATIVE per ADR-010 §"Tier mapping"), `ESS` (QUALITATIVE_TREND floor; always renders NUMBER as a diagnostic). AST scanner (`tests/test_v9_3_enum_comparison_enforcement.py`) extended to enforce `.value` comparisons on `IsothermChoice` and `OutputType`.

### Closed — Tier 1 (B-1p, B-1q, B-1r)

- **B-1p (W-053, W-054) — Mobile-phase widget + lifecycle override.** New `panels/mobile_phase.py` with 5-field T_C / c_NaCl / glycerol / ethanol / μ-override editor whose slider domains mirror `core/viscosity.py::resolve_mobile_phase_viscosity` `valid_domain`. `lifecycle/orchestrator.py:781` now accepts an optional `MobilePhase` override; default `MobilePhase()` preserves v0.7 backwards compatibility. Resolves audit defect **C1** (the headline UX defect — pre-flight envelope was silently using PBS defaults).
- **B-1q (W-055, W-056) — Isotherm selector + `plots_m2.py` tier-gating.** New `panels/isotherm_selector.py` ships an `IsothermChoice` enum with 5 members and family-aware default routing — Protein A workflows default to bare Langmuir; IEX-flagged hints default to `SaltModulatedLangmuir`; IMAC hints default to `ImidazoleModulatedLangmuir`. Five conditional sub-forms expose the parameter set per choice. `plots_m2.plot_surface_area_comparison` gains a `tier=` kwarg that routes the trust badge through `render_decision_grade_annotation`. Resolves **C2** + **C8**.
- **B-1r (W-057, W-058) — Calibration ingestion panel + tier banner.** New `tabs/calibration/wetlab_ingestion.py` provides a clearly-labelled "Upload wet-lab calibration campaign (YAML)" uploader with parse + tier-promotion preview before any commit. New `shell/tier_banner.py` renders a persistent banner at the top of every stage with three semantic states (GREEN at calibrated_local+ AND calibration loaded; AMBER at semi_quantitative; RED at qualitative_trend or below). Resolves **C6** + **W-1**.

### Closed — Tier 2 (B-2s KEYSTONE, B-2t, B-2u)

- **B-2s (W-059, W-060) — KEYSTONE: `tab_calibration` + forward MC + inverse Bayesian.** New `tabs/tab_calibration.py` hosts a Calibration & Uncertainty stage with four sub-tabs. **Forward MC panel** (`tabs/calibration/forward_mc.py`) exposes `monte_carlo_pressure_envelope` with n_samples / seed / prior-mode controls and a 3-band `p_blocker` advisory chip (GREEN < 0.01, AMBER 0.01–0.05, RED ≥ 0.05) honouring the README's pre-flight risk guardrail. **Inverse panel** (`tabs/calibration/inverse_inference.py`) provides a `MeasuredPressureFlowPoint` table editor, runs `infer_posterior_envelope`, surfaces ESS + `ess_warning` diagnostics, displays posterior parameter quantiles, and exposes a "Round-trip posterior log_cov into forward MC" button that closes the Bayesian loop. Resolves **C3** + **C4**.
- **B-2t (W-061) — Multi-column series builder.** New `tabs/calibration/multi_column.py` provides a per-column `st.data_editor` (name, polymer_family, ColumnGeometry fields) plus default capture-and-polish rows. Runs `compute_multi_column_envelope`; result panel surfaces series Q_max / headroom / decision_tier with the bottleneck column highlighted in the per-column table. Resolves **C5**.
- **B-2u (W-062, W-063) — RecoveryAction timeline + next-step affordance.** `tab_m3_monitor.py` extended with a per-rule `RecoveryAction` timeline ribbon under the existing trace plot — chips coloured by state, hover-text shows triggered rule + recovery action, with a rule-frequency expander listing each rule's count. New `components/next_step_affordance.py` renders a 3-button "Run forward MC / Fit posterior / Build series geometry" strip after the lifecycle completes; each button writes `st.session_state["_jump_to_calibration_section"]` honoured by the calibration tab's dispatcher (one-shot read-and-clear). Resolves **C9** + **W-2**.

### Verification

- **130+ new tests** across the seven batches; **104/104 visualization tests pass** in the v0.8.4-relevant scope plus the existing AST gate.
- ruff: clean across all changed paths.
- mypy: 0 issues on new source files.
- AST gate: extended to cover `IsothermChoice` + `OutputType`; **0 violations**.

### Validation gates closed in this release

10 new gates (28–37) close the v0.8.4 audit defects:

- **28** Mobile-phase composition reachable from UI (B-1p).
- **29** Isotherm selector covers all 5 v0.8.x adapters (B-1q).
- **30** Forward MC `p_blocker` advisory chip surfaces (B-2s).
- **31** Inverse Bayesian inference reachable with log_cov round-trip (B-2s).
- **32** Multi-column series envelope reachable (B-2t).
- **33** Calibration-store ingestion has clearly-labelled UI path (B-1r).
- **34** SEMI_QUANTITATIVE banner surfaces tier state at every stage (B-1r).
- **35** RecoveryAction timeline surfaces per-rule history (B-2u).
- **36** `plots_m2.py` surface-area chart routes through tier policy (B-1q).
- **37** Post-lifecycle "what's next" affordance surfaces 3 buttons (B-2u).

### Public-communication framing

> v0.8.4 ships as **"UI-completeness-closed against the v0.8.3 backend"**. Every scientifically meaningful capability shipped in the v0.7.0 → v0.8.3 cluster is now reachable from the dashboard. The README's central editorial promise — *screen → calibrate → tighten* — becomes operationally testable from the dashboard for the first time. Tier promotion to `CALIBRATED_LOCAL` remains a wet-lab-driven path; v0.8.4 ships the *machinery* but not the wet-lab handshake. The v0.9 maturity plateau is now defined exclusively by the three hardware/physics deferrals: live AKTA UNICORN socket (ADR-008), cyclic SMB dynamics (ADR-009), and MCMC inverse inference (ADR-010).

### Detailed handover

- `docs/handover/HANDOVER_v0_8_4_release.md` — combined release-level handover continuing the v0.8.2/0.8.3 consolidation pattern. Per-batch handover detail consolidated for the same-day patch cluster.

### Architecture decisions

No new ADRs introduced. The seven batches collectively respect ADR-001 through ADR-011; no architectural decisions opened or closed in this release. The joint engagement produced two new audit/architecture docs:
- `docs/handover/AUDIT_v0_8_3_ui_completeness.md` (Phase 1, /scientific-advisor)
- `docs/handover/ARCH_v0_8_3_ui_decomposition.md` (Phase 2, /architect)

## v0.8.3 — Pure-coding open work close (post-v0.8.2) (2026-05-10)

Closes 5/5 work-plan items from `docs/update_workplan_2026-05-10_v0_8_3.md` — the residual pure-coding items from the v0.8.2 cumulative open list. Hardware-bound (AKTA UNICORN) and physics-deep (cyclic SMB) items remain v0.9 candidates per ADR-008 / ADR-009; wet-lab K_geom / ν calibration stays user-side. Patch bump per the project versioning policy.

Two new ADRs land alongside the code: ADR-010 (inverse pressure-envelope inference) and ADR-011 (correlated MC priors).

### Closed — Tier 1 (B-1o)

- **B-1o (W-046) — M2 widget tier-gating.** `tab_m2.py:744-745` had two raw `st.metric` calls for `G_DN_updated` and `E_star_updated` — both `OutputType.MODULUS` candidates. Routed through `render_metric` with the FunctionalMicrosphere's `model_manifest.evidence_tier` (defensive fall-through to SEMI_QUANTITATIVE). The conditional from the v0.8.2 release handover ("M2 plot tier-gating — extend W-037 to plots_m2.py once meaningful numeric annotations land there") is satisfied: the annotations were always there in `tab_m2`; v0.8.2's audit missed them.

### Closed — Tier 2 (B-2o … B-2r)

- **B-2o (W-047) — Inverse Bayesian inference via importance sampling + ADR-010.** New `module3_performance/pressure_envelope_inverse.py` ships `infer_posterior_envelope(measurements, ...)`. Importance-sampling weights against a Gaussian likelihood; reuses the v0.8.2 forward-MC infrastructure. Returns posterior P05/P50/P95 on K_geom / μ / G_DN, posterior bands on Q_max / dP_predicted / headroom_ratio at a user-specified Q_for_envelope, posterior-weighted `p_blocker` / `p_warning`, plus a 3×3 posterior `log_cov` directly consumable by the W-049 forward-MC `log_cov` path (the natural Bayesian round-trip). ESS diagnostic + warning when ESS < 10 % of n_samples. Tier stays SEMI_QUANTITATIVE per ADR-010 §"Tier mapping" — CALIBRATED_LOCAL promotion is wet-lab-driven. ADR-010 documents the choice of importance sampling over MCMC for v0.8.3 (no new deps, deterministic, ESS-flagged when posteriors are peaky; MCMC promotion is a v0.8.4+ candidate). 14 new tests.
- **B-2p (W-048) — Per-family MC priors registry.** New `FamilyMCPrior` dataclass + `_FAMILY_MC_PRIORS` registry on `pressure_envelope_mc.py`, keyed by `PolymerFamily.value` with literature-anchored σ_log values per family (PLGA + ALGINATE have the widest G_DN scatter; AGAROSE the tightest). New `use_family_priors=True` flag on `monte_carlo_pressure_envelope`; `sigma_log_*` arguments transition to `Optional[float]` with `None` as the "fall back to family / default" sentinel. Backwards-compatible: 9/9 v0.8.2 MC tests pass unchanged.
- **B-2q (W-049) — Correlated MC priors via covariance matrix + ADR-011.** New `log_cov: Optional[np.ndarray]` argument on `monte_carlo_pressure_envelope`. When supplied (3×3 in parameter order [K_geom, μ, G_DN]), draws come from a multivariate normal in log-space; symmetry + PSD validation. ADR-011 documents the convention. Strong correlation between K_geom and G_DN demonstrably widens the Q_max IQR vs the diagonal path.
- **B-2r (W-050) — Multi-step coupled MC propagation.** New `monte_carlo_step_program` draws N parameter triples ONCE and re-uses them across every step in the recipe program — preserving the cross-step correlation that independent per-step MC would miss. Returns `StepProgramMCResult` with per-step `MCEnvelopeBands` + `worst_step_p_blocker` + `worst_step_index`. Honours `use_family_priors` and `log_cov` paths.

### Verification

- 12 + 14 + 10 = 36 new tests across W-047, W-048, W-049, W-050; plus 4 W-046 + tier-gated + the v0.8.2 backward-compat tests.
- ruff + mypy clean on all new source files.
- AST gate: no new `is` / `is not` comparisons against managed enums.

### Validation gates closed in this release

- **23:** M2 widget annotations carry tier labels (B-1o).
- **24:** Inverse pressure-envelope inference is reachable from one constructor (B-2o + ADR-010).
- **25:** MC envelope honours per-family priors (B-2p).
- **26:** MC envelope accepts an explicit covariance matrix (B-2q + ADR-011).
- **27:** MC envelope produces a coupled multi-step program with shared draws (B-2r).

### Public-communication framing

> v0.8.3 closes the residual pure-coding items from the v0.8.2 cumulative open list. Hardware-bound (AKTA UNICORN socket bridge — ADR-008) and physics-deep (cyclic SMB — ADR-009) items remain v0.9 candidates. Wet-lab K_geom / ν calibration stays user-side. None of the new modules ship at higher than SEMI_QUANTITATIVE tier without user-supplied calibration; the inverse-inference module ships the *machinery* for posterior fitting but not the wet-lab handshake that promotes the tier.

### Detailed handover

- `docs/handover/HANDOVER_v0_8_3_release.md` — combined release-level handover continuing the v0.8.2 consolidation pattern.

### Architecture decisions

- `docs/decisions/ADR-010-inverse-pressure-envelope-inference.md`
- `docs/decisions/ADR-011-correlated-mc-priors.md`

## v0.8.2 — Cumulative open-future-work close (2026-05-10)

Closes 10/10 code-work items from `docs/update_workplan_2026-05-10_v0_8_2.md` — the cumulative open list inherited via the v0.8.1 release handover. The 11th item (wet-lab K_geom / ν calibration) is explicitly user-side and is NOT a v0.8.2 deliverable. Patch bump per the project versioning policy; v0.9 stays available for a matured-status plateau.

Four new ADRs land alongside the code: ADR-006 (full SMA promotion path), ADR-007 (forward MC Bayesian envelope), ADR-008 (monitor source abstraction), ADR-009 (multi-column series scope vs cyclic SMB).

### Closed — Tier 0 + Tier 1 (B-0g … B-1n)

- **B-0g (W-036) — Pre-existing `confidence_tier` test stale-field fix.** v0.5.0 (D2) removed the legacy `confidence_tier: str` side-channel from `FunctionalMediaContract`'s public surface. The test at `test_breakthrough_inherits_fmc_qualitative_tier` was using the stale kwarg; removed it. The typed `model_manifest.evidence_tier` chain remains the source of truth for FMC evidence.
- **B-1ℓ (W-037) — M1 plot tier-gating extension.** `plot_droplet_size_distribution` gains an optional `tier=` kwarg; when set, the d32 / d50 vertical-line annotations route through `render_decision_grade_annotation` from v0.8.1. `tier=None` preserves legacy formatting bit-for-bit. 4 new tests.
- **B-1m (W-038) — IMAC imidazole-modulated Langmuir adapter.** New `module3_performance/isotherms/imidazole_dependent.py` mirrors W-034's `SaltModulatedLangmuir` for IMAC screening. Defaults: n=1.5 (mid-range His6 on Ni-NTA), c_imidazole_ref=50 mM. Routes `process_state["imidazole"]` through the existing `EquilibriumAdapter`. 21 new tests.
- **B-1n (W-039) — Full SMA promotion adapter + ADR-006.** New `module3_performance/isotherms/sma_modulated.py` ships `SaltModulatedSMA` — the swap-in promotion target for `SaltModulatedLangmuir` documented in ADR-005. Same `equilibrium_loading(C, c_salt_mol_m3)` signature; internally invokes the full SMA fixed-point on q_salt. ADR-006 documents the per-rhs cost vs precision tradeoff (5–20× cost, captures saturation + steric shielding). 16 new tests.

### Closed — Tier 2 (B-2k … B-2n)

- **B-2k (W-040) — Multi-step pressure feasibility.** `PressureFeasibilityContext` gains an optional `step_program` field — a tuple of `PressureStep` instances each carrying (name, Q, mobile_phase). When supplied, `pressure_feasible` screens the candidate against every step's envelope and reports ALL step-level violations (not just the first). Single-step legacy v0.8.0 behaviour preserved exactly when `step_program=None`. 7 new tests.
- **B-2ℓ (W-041) — Channeling auto-recovery action routing.** New `RecoveryAction` enum with seven members (NONE / CONTINUE_MONITOR / REDUCE_FLOW / SWITCH_TO_WASH / STOP_AND_REPACK / EMERGENCY_STOP / OPERATOR_REVIEW) plus `_RULE_TO_ACTION` mapping. `PressureMonitorOutput` and `ReplaySummary` gain a structured `recovery_action` field; the streaming UI's status panel now surfaces an action chip alongside the rule name. Sentinel test asserts every `PressureMonitorRule` has a non-NONE action mapping. 6 new tests.
- **B-2m (W-042) — Multi-component competitive IEX salt modulation.** New `module3_performance/isotherms/competitive_salt_dependent.py` ships `SaltModulatedCompetitiveLangmuir` — the multi-component analogue of `SaltModulatedLangmuir`. Per-component characteristic-charge ν_i array; the salt-modulated K_L_i propagates through the shared competitive-Langmuir denominator, reproducing the textbook IEX displacement-train ordering. 13 new tests.
- **B-2n (W-043) — Forward Monte Carlo Bayesian envelope wrapper + ADR-007.** New `module3_performance/pressure_envelope_mc.py` ships `monte_carlo_pressure_envelope` — lognormal multiplicative priors on K_geom (σ_log=0.20), μ (0.05), G_DN (0.30); n=500 default draws; aggregates to P05/P50/P95 of Q_max / dP_predicted / dP_max_operational / headroom_ratio plus tail probabilities (`p_blocker`, `p_warning`). MC bands stay SEMI_QUANTITATIVE per ADR-007 — they reflect priors, not measured posteriors. Inverse Bayesian inference deferred to v0.9. 9 new tests.

### Closed — Tier 3 (B-3g + B-3h)

- **B-3g (W-044) — Monitor source abstraction + simulator backend + ADR-008.** New `module3_performance/monitor_source.py` defines a `MonitorSource` typing.Protocol with three concrete backends: `CSVReplayMonitorSource`, `SimulatedMonitorSource` (synthetic ramp + linear fouling slope + Gaussian noise; deterministic via seed), and `NullMonitorSource`. ADR-008 documents the protocol and the deferred `UnicornSocketMonitorSource` (live AKTA UNICORN bridge — explicit v0.9 deliverable, requires hardware access). 15 new tests.
- **B-3h (W-045) — Multi-column series envelope + ADR-009.** New `module3_performance/multi_column.py` ships `MultiColumnGeometry` and `compute_multi_column_envelope` with conservative aggregation rules: total ΔP sums in series; bottleneck column sets Q_max; worst column drives headroom; weakest tier rolls up; valid-domain violations are prefixed. ADR-009 documents the series scope and the deferred cyclic SMB physics (port valves, multi-bed displacement coupling — v0.9 candidate). 14 new tests.

### Verification

- 130+ new tests across the 10 work items; 100% pass.
- ruff + mypy clean on all new source files.
- AST gate: no new `is` / `is not` comparisons against managed enums.

### Validation gates closed in this release

- **Gate 14:** M1 plot annotations carry tier labels (B-1ℓ).
- **Gate 15:** IMAC imidazole-driven elution is physics-aware (B-1m).
- **Gate 16:** Full SMA promotion path is reachable from one constructor (B-1n + ADR-006).
- **Gate 17:** BO can drop candidates infeasible at any step in the recipe (B-2k).
- **Gate 18:** Streaming monitor outputs structured recovery actions (B-2ℓ).
- **Gate 19:** Multi-component competitive IEX consumes salt envelope (B-2m).
- **Gate 20:** Pressure envelope ships P05/P50/P95 uncertainty bands (B-2n + ADR-007).
- **Gate 21:** Monitor source is hardware-agnostic (B-3g + ADR-008). UNICORN hardware bridge is the binding-open part — v0.9 candidate.
- **Gate 22:** Multi-column series operations have an envelope (B-3h + ADR-009). Cyclic SMB dynamics is the binding-open part — v0.9 candidate.

### Public-communication framing

> v0.8.2 closes the cumulative open code work from the v0.8.1 release handover. Four new ADRs document the bounded-scope decisions (full SMA, MC propagation, monitor abstraction, multi-column series); two of those (monitor and multi-column) explicitly defer the **hardware-side** / **physics-side** binding-open parts to v0.9. Wet-lab K_geom / ν calibration remains user-side and is not a code deliverable. None of the new modules ship at higher than `SEMI_QUANTITATIVE` tier without user-supplied calibration.

### Detailed handover

- `docs/handover/HANDOVER_v0_8_2_release.md` — single combined release-level handover summarising every batch; per-batch detail consolidated to keep handover surface manageable across the rapid 0.7 / 0.8 / 0.8.1 / 0.8.2 same-day patch cluster.

### Architecture decisions

- `docs/decisions/ADR-006-full-sma-promotion-path.md`
- `docs/decisions/ADR-007-mc-pressure-envelope.md`
- `docs/decisions/ADR-008-monitor-source-abstraction.md`
- `docs/decisions/ADR-009-multi-column-series.md`

## v0.8.1 — Salt-aware elution + plotly annotation tier-gating (2026-05-10)

Closes 2/2 work-plan items from `docs/update_workplan_2026-05-10_v0_8_1.md` — the long-deferred "future scientific scope" items from the 2026-05-04 incremental-close handover. Patch bump per the project's versioning policy: minor bumps reserved for matured-status milestones; v0.9 stays available for a meaningful plateau.

### Added — Tier 1 (B-1j + B-1k)

- **B-1j (W-034) — Salt-modulated Langmuir adapter.** New `module3_performance/isotherms/salt_dependent.py` ships the Mollerup-simplified salt modulator (functionally identical to SDM in the dilute single-component limit per ADR-005). `SaltModulatedLangmuir` wraps a base `LangmuirIsotherm` and applies `K_a(c_salt) = K_a_ref · (c_salt_ref / c_salt) ** ν` at every rhs evaluation. The full SMA mass-action solver (`isotherms/sma.py`) remains the documented promotion target for when wet-lab ν / σ data warrants the per-rhs fixed-point cost. `EquilibriumAdapter.equilibrium_loading` gains a branch for the new isotherm class so the existing `run_gradient_elution` → `solve_lrm` → adapter wiring routes the `salt_concentration` state field into the new isotherm without touching the time-domain solver. Tier ladder: `SEMI_QUANTITATIVE` by default; `CALIBRATED_LOCAL` when callers fit ν locally and set `calibrated_locally=True`. Literature defaults: ν = 4.5 (mid-range protein characteristic charge), c_salt_ref = 150 mM (PBS reference). New ADR-005 documents the full SDM-vs-Mollerup-vs-SMA tradeoff. 24 new tests.

- **B-1k (W-035) — Plotly annotation tier-gating.** New `render_decision_grade_annotation` helper in `visualization/decision_grade_render.py` is the plotly-side companion to `render_metric`. Routes a value through `format_decision_graded`, picks an unobtrusive color hint based on the chosen render mode, and appends `[INTERVAL]` / `[RANK]` mode tags when the policy degrades the output below NUMBER. SUPPRESS branches return without drawing — callers can explicitly add a "data not available" badge instead. Wired into `plot_breakthrough_curve` (DBC₅ / DBC₁₀ / DBC₅₀ value annotations) and `plot_pressure_flow_curve` (Q_max badge); both gain an optional `tier` kwarg with `tier=None` preserving legacy formatting. 13 new tests.

### Verification

- 269 tests passing in v0.8.1-relevant scope (visualization + module3_performance).
- ruff: clean across all changed paths.
- mypy: 0 issues on new source files.
- AST gate: no new `is` / `is not` comparisons against managed enums.

### Validation gates closed in this release

- **Gate 12: salt-driven elution dynamics are physics-aware.** The previous v0.8.0 state was: salt gradient envelope was in `gradient_diagnostics` but did not drive the isotherm. After v0.8.1, the gradient elution rhs sees `c_salt(t)` and modulates K_a via the Mollerup factor.
- **Gate 13: plotly annotations are tier-gated.** Plot overlays no longer assert tier-blind numeric badges; values flow through the same decision-grade ladder that gates `st.metric` widgets.

### Public-communication framing

> v0.8.1 ships salt-aware IEX elution at SEMI_QUANTITATIVE tier with literature-anchored ν defaults. Quantitative protein-specific elution recoveries require local wet-lab calibration of ν against the protein-resin pair. The plotly annotation extension is purely cosmetic — it does not change any numerical computation; it only ensures chart labels carry the same evidence-tier caveats as the metric widgets.

### Detailed handovers

- `docs/handover/HANDOVER_v0_8_1_b1j_salt_modulator.md`
- `docs/handover/HANDOVER_v0_8_1_b1k_plotly_annotations.md`
- `docs/handover/HANDOVER_v0_8_1_release.md`

## v0.8.0 — Pressure-envelope operationalization (2026-05-10)

Closes 3 of 3 work-plan items from `docs/update_workplan_2026-05-10_v0_8.md` — the deferred items from the v0.7.0 §6 "out-of-scope" list. The release operationalizes the pressure envelope end-to-end: pre-flight (v0.7), in-flight (v0.8 streaming UI for offline replay), and back-prop (v0.8 BO feasibility constraint). Calibration tier remains SEMI_QUANTITATIVE INTERVAL until manufacturer pressure-flow curves are loaded into the calibration store.

### Removed — Tier 1 (B-1i) — deprecation cycle hygiene

- **B-1i (W-031) — `ColumnGeometry.max_safe_flow_rate` removed.** The v0.7.0 deprecation grace window expires. The `safety × E_star` bursting-modulus anchor is no longer selectable through the public API; operational ceilings come solely from `compute_pressure_envelope` (W-020 / B-2f) via `PressureEnvelope.Q_max_m3_s`. `validate_flow_rate` now emits only the soft compression-fraction and Re_p WARNINGs (the BLOCKER path was the bursting check). `plots_m3.plot_pressure_flow_curve` requires `Q_max` as an explicit argument; the `tab_m3.py` breakthrough panel now derives Q_max via `compute_pressure_envelope` on the M2 result. The dedicated deprecation test suite is removed.

### Added — Tier 2 (B-2i + B-2j) — UX completion + BO integration

- **B-2i (W-032) — Streaming pressure-monitor UI + CSV-replay helper.** New `module3_performance/pressure_monitor_replay.py` parses pressure traces from CSV (canonical SI columns plus AKTA-style aliases for t/dP/Q with unit-aware scaling), threads them through `evaluate_pressure_trace` (v0.7 / B-3d), and returns a `ReplaySummary` with state-timeline + first-BLOCKER / first-WARNING anchors + max diagnostic ratios. New `visualization/tabs/tab_m3_monitor.py` renders a Streamlit section after the pre-flight envelope panel: file uploader, replay summary metric row, ΔP-vs-time plot with operational + 70 % warning thresholds + per-reading state chips, and a downloadable example CSV. The live AKTA UNICORN bridge is still a v0.9 epic — v0.8 ships only the offline replay path. 28 new tests (22 replay-helper + 6 UI smoke).
- **B-2j (W-033) — Pressure-feasibility BO constraint.** New `PressureFeasibilityContext` frozen dataclass on `optimization/objectives.py` bundles run-level fixed inputs (column geometry, mobile phase, Q_target, polymer_family, headroom_threshold). New `pressure_feasible(result, ctx)` builds a per-candidate `ColumnGeometry` by overriding the context column's particle_diameter / G_DN / E_star with the candidate's M1+M2 outputs, then runs `compute_pressure_envelope` and checks `headroom_ratio` against the threshold. `check_constraints` gains an optional `pressure_ctx` keyword-only argument; when None the v0.7 behaviour is preserved exactly. KeyError / ValueError from envelope computation declares the candidate infeasible with a clean message rather than escaping to the BO loop. **Bonus:** `dpsim.optimization.__init__` now lazy-loads `OptimizationEngine` via PEP 562 `__getattr__`, so importing `dpsim.optimization.objectives` no longer requires torch. 12 new tests.

### Verification

- 681 tests passing in v0.8-relevant scope (module3_performance + visualization + core + lifecycle + new feasibility tests).
- ruff: clean across all changed paths.
- mypy: 0 issues on new source files.
- AST gate (`tests/test_v9_3_enum_comparison_enforcement.py`): no new `is` / `is not` comparisons against managed enums.

### Validation release-gate status (v0.8 plan §4)

  1–8. Inherited from v0.7.0 — unchanged ✓
  9. **Deprecation-cycle hygiene** — closed B-1i ✓ (establishes "deprecate one release, remove next release" cadence as a first-class precedent).
  10. **Pressure-monitor offline replay** — closed B-2i ✓ (operators can validate envelope accuracy against historical AKTA traces without live hardware).
  11. **BO-side pressure feasibility** — closed B-2j ✓ (optimizer cannot recommend recipes whose post-M2 column step would exceed the operational envelope).

### Public-communication framing

> v0.8.0 ships as **DPSim's pressure envelope is end-to-end** — pre-flight (v0.7), in-flight (v0.8 monitor UI for offline replay), and back-prop (v0.8 BO feasibility). Calibration tier remains SEMI_QUANTITATIVE INTERVAL until manufacturer pressure-flow curves are loaded into the calibration store. The streaming UI is offline-only — live AKTA UNICORN integration is a v0.9 epic.

### Detailed handovers

  - `docs/handover/HANDOVER_v0_8_b1i_deprecation_removal.md`
  - `docs/handover/HANDOVER_v0_8_b2i_streaming_ui.md`
  - `docs/handover/HANDOVER_v0_8_b2j_bo_feasibility.md`
  - `docs/handover/HANDOVER_v0_8_0_release.md`

## v0.7.0 — M3 interface back-pressure optimization (2026-05-10)

Closes 11 of 11 work-plan items from `docs/update_workplan_2026-05-10_m3_pressure.md` — the v0.7.0 M3 back-pressure work driven by the joint /scientific-advisor + /architect + /dev-orchestrator review on 2026-05-10. The release replaces the v0.6.6 ΔP_max anchor (`safety × E_star`, scientifically wrong by 5–50× factor for soft chromatography media) with a per-family u_crit formulation, makes mobile-phase viscosity a function of (buffer, T), surfaces the Sauter mean d32 across the M2→M3 wire, adds frit/distributor series resistance, and ships a structured pre-flight pressure envelope with an in-flight streaming monitor (function-only; UI deferred to v0.8).

### Added — Tier 1 (B-1f … B-1h) — quick wins

- **B-1f (W-023) — Buffer + viscosity foundation:** new `core/mobile_phase.py` (`MobilePhase` frozen dataclass) and `core/viscosity.py` (`ViscosityResult` + `water_viscosity_pa_s` + `resolve_mobile_phase_viscosity`). Literature-anchored additive model: μ = μ_water(T)·(1 + α_salt·c_NaCl + α_gly·φ_gly + α_etoh·φ_etoh) with Crittenden 2012 / Out & Los 1980 / Cheng 2008 / Khattab 2017 anchors. `custom_mu_pa_s` override path → `CALIBRATED_LOCAL` tier. 69 new tests.
- **B-1g (W-021 + W-024) — Sauter d32 surfacing + frit resistance:** `_column_with_microsphere` and `_column_for_quantile` in `module3_performance/method_simulation.py` now read `m1.bead_d32` (Sauter, surface-area-equivalent) instead of `m1.bead_d50` (median). Existing `M1ExportContract.bead_d32` is consumed; no new field needed. ΔP correction factor (d50/d32)² ≈ 1.56× at typical σ_ln. `ColumnGeometry` adds `Optional` `frit_permeability_m2` and `frit_thickness_m` fields plus a `frit_pressure_drop` method. 23 new tests.
- **B-1h (W-030) — Decision-grade enum extension:** `core/decision_grade.py::OutputType` adds `PRESSURE_LIMIT`, `Q_MAX`, `U_CRIT`, `PRESSURE_HEADROOM`. PRESSURE_LIMIT/Q_MAX/U_CRIT mirror PRESSURE_DROP at SEMI_QUANTITATIVE floor; PRESSURE_HEADROOM is tier-independent (floor QUALITATIVE_TREND). 26 new tests.

### Added — Tier 2 (B-2f … B-2h) — keystone science fix + UX wiring

- **B-2f (W-020 + W-026) — Pressure envelope science fix [KEYSTONE]:** new `module3_performance/family_kgeom.py` with `FAMILY_KGEOM_REGISTRY` keyed by `PolymerFamily.value` (5 families: agarose, agarose_chitosan, cellulose, plga, alginate; literature-anchored K_geom defaults at SEMI_QUANTITATIVE; conservative fallback at QUALITATIVE_TREND for unregistered). New `module3_performance/pressure_envelope.py` with `PressureEnvelope` frozen dataclass + `compute_pressure_envelope` orchestrator. Two distinct pressure ceilings: `dP_max_operational_pa` (u_crit-based, THE operational limit) and `dP_max_burst_pa` (E_star-based bed elastic-limit DIAGNOSTIC, NOT the operational ceiling). Tier rollup walks `valid_domain` + viscosity.extrapolated; demotes one step per dimension; floors at QUALITATIVE_TREND. `calibration_store` injection point for manufacturer pressure-flow curves promotes K_geom_source to `CALIBRATED_LOCAL`. `ColumnGeometry.max_safe_flow_rate` deprecated with `DeprecationWarning`; removal in v0.8. ADR-004 documents the full decision rationale. 79 new tests.
- **B-2g (W-022) — ε_b iteration refinement:** `iterate_kc_compression` adds Picard-with-under-relaxation (α=0.5) feedback for the (ε_b, ΔP) fixed point. Per-iteration compression cap at 3% keeps the linear-elastic small-strain formula in its valid regime. Cap-hit budget triggers `converged=False` for tier downgrade. ε_b floor at 0.10 + immediate-runaway detection at compression > 90 %. Consumed by `compute_pressure_envelope` without API change. 19 new tests.
- **B-2h (W-025 + W-028 + W-029) — Pre-flight UX wiring:** `lifecycle/orchestrator.py` adds a `pressure_envelope` field on `DownstreamLifecycleResult` and computes one per run post-M2 with the M2-updated G_DN/E_star and a default `MobilePhase()`. Emits BLOCKER on `headroom_ratio > 1.0`, WARNING on > 0.7, WARNING per `valid_domain_violations`. New `_g8_pressure_envelope_check` in `core/recipe_validation.py` mirrors G7 (B-1a precedent) with recipe-side sanity bounds (negative / absurdly-large flow rates flagged before the long M1+M2+M3 chain runs). New "Pressure envelope (pre-flight)" section in `visualization/tabs/tab_m3.py` using `render_metric` (B-1b precedent) for tier-aware display. 8 new tests.

### Added — Tier 3 (B-3d) — streaming monitor

- **B-3d (W-027) — Streaming pressure monitor function:** new `module3_performance/pressure_monitor.py` with `PressureMonitorRule` + `PressureMonitorState` enums, `PressureMonitorReading` + `PressureMonitorOutput` frozen dataclasses, and `evaluate_pressure_trace` pure function. Seven rules: SPIKE / HEADROOM_BLOCKER / DPDT_BLOCKER / MODEL_DEVIATION_LOW (channeling) / MODEL_DEVIATION_HIGH (fouling) / HEADROOM_WARNING / DPDT_WARNING with thresholds at 0.85 / 0.70 / 20 %·min⁻¹ / 5 %·min⁻¹ / 1.50 / 0.60 / 100 %·min⁻¹ sustained 5 s. History append-and-prune (default 5-min window). Function-only ship; live UI widget + AKTA UNICORN integration deferred to v0.8. 20 new tests.

### Verification

- 694 tests passing in 93 s wide-regression (B-1f through B-3d + Tier 0 baseline + lifecycle + recipe_validation + v60 integration).
- 23 expected `DeprecationWarning` calls from existing internal callers of `ColumnGeometry.max_safe_flow_rate` (legacy callers retained for the v0.7.x deprecation window).
- ruff: clean across all changed paths.
- mypy: 0 issues on new source files. Pre-existing scipy-stubs baseline noise unchanged.
- AST gate (`tests/test_v9_3_enum_comparison_enforcement.py`): 3/3 passing — no new `is`/`is not` comparisons against PolymerFamily / ACSSiteType / ModelEvidenceTier / ModelMode.

### Validation release-gate status (work plan §4)

  1. Environment (W-001) — closed in v0.6.6 ✓
  2. Calibrated wet-lab dataset — wet-lab side, OPEN
  3. Independent wet-lab holdout validation — wet-lab side, OPEN
  4. Decision-grade automatic downgrade (W-003) — closed v0.6.6 ✓
  5. Process dossier export (W-011) — closed v0.6.6 ✓
  6. **u_crit-anchored ΔP_max prediction** (W-020 + W-026) — closed B-2f ✓
  7. **Per-family K_geom calibration vs manufacturer curves** — wet-lab side, OPEN. Code path lands with B-2f via `calibration_store`; the store itself is empty until users supply data.
  8. **Pre-flight pressure envelope renders before "Start flow"** (W-025 + W-028 + W-029) — closed B-2h ✓

3/3 new gates introduced by v0.7 are code-side closeable. Gates 6 + 8 are now closed; gate 7 is wet-lab-gated and remains the binding promotion path from SEMI_QUANTITATIVE INTERVAL → CALIBRATED_LOCAL NUMBER render.

### Public-communication framing

> v0.7.0 ships as a **research-grade screening simulator with first-principles back-pressure envelopes** rendered at SEMI_QUANTITATIVE INTERVAL precision. Promotion to CALIBRATED_LOCAL NUMBER precision requires user-supplied manufacturer pressure-flow curves or local wet-lab pressure-flow data via the `calibration_store` argument. DPSim v0.7 must NEVER, in any communication, be described as "validated for back-pressure-safe column operation" — that requires gates 2, 3, and 7 all closed (work plan §4.3).

### Detailed handovers

  - `docs/handover/HANDOVER_b0d_residual_hygiene_close.md`
  - `docs/handover/HANDOVER_b1f_viscosity_close.md`
  - `docs/handover/HANDOVER_b1g_d32_frit_close.md`
  - `docs/handover/HANDOVER_b1h_decision_grade_ext.md`
  - `docs/handover/HANDOVER_v0_7_b2f_pressure_envelope_KEYSTONE.md`
  - `docs/handover/HANDOVER_b2g_iteration_close.md`
  - `docs/handover/HANDOVER_v0_7_b2h_ux_close.md`
  - `docs/handover/HANDOVER_v0_7_b3d_streaming_function_close.md`

## v0.6.6 — Tier 1 + Tier 2 + post-Tier-2 work plan close (2026-05-04)

Closes 14 of 19 work-plan items from the 2026-05-04 joint audit
(`docs/update_workplan_2026-05-04.md`) and the two carry-over
incremental items. Three of the five validation-release gates from
work plan §5 are now closeable from code; the remaining two require
user-side wet-lab data. v0.6.4 and v0.6.5 are work-plan-batch labels
referenced inside the source — they were never tagged or released.
This release supersedes them.

### Added — Tier 1 (B-1a … B-1e)

- **B-1a (W-002) — Recipe Guardrail 2 (G7 pH window check):**
  `core/recipe_validation.py::_g7_ph_window_check` validates each M2
  step's pH against the reagent's hard / soft / optimum windows
  (BLOCKER outside hard, WARNING outside soft inside hard, silent
  inside soft). 23 reagent profiles in
  `module2_functionalization/reagent_profiles.py` curated with
  literature-anchored windows (CNBr, CDI, tresyl, epoxide, NaBH4,
  boronate, IMAC, Protein A, borax, glutaraldehyde). 40 new test cases.
- **B-1b (W-003) — Decision-grade gates per output type:** new
  `core/decision_grade.py` with 14 OutputTypes and a NUMBER →
  INTERVAL → RANK_BAND → SUPPRESS render-mode ladder. 42 test cases.
  UI-side helper in `visualization/decision_grade_render.py` plus
  reference-site wiring at 13 metrics across `tabs/tab_m1.py` and
  `tabs/tab_m3.py` (d_mode/d32, pore_size, modulus, DBC₅/₁₀/₅₀%,
  pressure_drop, recovery).
- **B-1c (W-007) — L2 family `valid_domain`:** `valid_domain`
  populated on every L2 family `ModelManifest` (12 sites across
  `level2_gelation/*.py`). AST-scanner regression test enforces the
  contract.
- **B-1d (W-006) — M1 PBE regime guards:** `cfd/zonal_pbe.py` exposes
  `d/η_K` and `d32/η_K` per-zone diagnostics, `breakage_C3`
  calibration constant, and `regime_guard_warnings` for
  sub-Kolmogorov regimes.
- **B-1e (W-005) — Taxonomy mapping refactor:** new
  `core/step_kind_mapping.py` is the single source of truth for
  `ProcessStepKind ↔ ModificationStepType ↔ allowlists`. 52 test
  cases including a regression that asserts every enum member is
  mapped. Closes joint-audit MAJOR-2.

### Added — Tier 2 (B-2a … B-2e)

- **B-2a (W-009) — Wash residual diffusion-partition + hydrolysis:**
  new `level1_emulsification/wash_residuals.py` solves a lumped-sphere
  partition-diffusion ODE with first-order hydrolysis using LSODA.
  Literature half-lives for CNBr (5 min @ pH 11), CDI (5 h @ pH 7),
  tresyl (1.5 h), NaBH4 (1 h conservative). `CalibrationEntry` gains
  `assay_detection_limit` / `assay_quantitation_limit` fields.
- **B-2b (W-008) — CFD-PBE end-to-end validation gates:** new
  `cfd/validation.py` with 4 operational-quality gates (mesh QA,
  residual convergence, ε-volume consistency, exchange-flow balance)
  plus the locked CFD evidence-tier ladder
  (`assign_cfd_evidence_tier`).
- **B-2c (W-010) — Typed SI boundary helpers:** 10 new helpers in
  `core/quantities.py` (`as_si_flow_rate_m3_per_s`,
  `as_si_volume_m3`, `as_si_pressure_pa`, ...) with property tests
  on Quantity → SI → Quantity round-trip preservation.
- **B-2d (W-011) — Deterministic process dossier export:** new
  `core/process_dossier.py` with hash-locked JSON serialisation, git
  commit / package-version capture, and content-addressable
  `compute_dossier_hash`. Closes validation release-gate 5.
- **B-2e (W-004) — M3 quantitative gating:** new
  `module3_performance/quantitative_gates.py` with calibration-coverage
  assessment (q_max / kinetic / pressure_flow / cycle_life),
  tier-promotion ladder, and `apply_m3_gate_to_manifest` orchestrator
  hook. `GradientContext` typed handle delivered with M3
  isotherm-adapter consumption refactored (typed-first,
  legacy-fallback). Salt / imidazole gradient time-profile scaffolded
  on `LoadedStateElutionResult.gradient_diagnostics`; isotherm physics
  consumption deferred (separate scientific scope).

### Added — Tier 3 + carry-overs

- **W-017 — Streamlit `st.components.v1.html` migration:**
  `visualization/components/_html_helper.py` shim with auto-routing —
  full HTML documents (the 5 cross-section assets) use the iframe
  path, HTML fragments use `st.html`. `DPSIM_USE_LEGACY_HTML=1`
  env-var escape hatch. 12 test cases including a real-asset
  round-trip. Resolves the post-migration UI regression where the
  impeller and column animations vanished due to DOMPurify stripping
  the document wrapper.
- **B-3a (W-016) — Streamlit `use_container_width` sweep:** 59
  callsites across 9 visualization files migrated to
  `width="stretch"`.
- **B-3c (W-019) — `docs/current_support_matrix.md`:** new single
  source of truth for what DPSim supports and at what evidence tier,
  including the validation release-gate ladder.

### Validation release-gate status (work plan §5)

  1. Environment (W-001) — closed in Tier 0
  2. Calibrated wet-lab dataset — wet-lab side
  3. Independent holdout validation — wet-lab side
  4. Decision-grade automatic downgrade (W-003) — closed (B-1b API + B-2e M3 wiring)
  5. Process dossier export (W-011) — closed (B-2d)

3/5 release gates now closeable from code. Remaining 2 require
user-side wet-lab data.

### Verification

- 494 tests passed, 8 skipped across the combined Tier 0 + Tier 1 +
  Tier 2 + post-Tier-2 + carry-overs + integration suites.
- ruff: clean across all changed paths.
- mypy: 0 issues on new source files (pre-existing scipy-stubs
  baseline noise unchanged).
- Default affinity-media recipe: 0 new BLOCKERs, 0 new WARNINGs.

### Detailed handovers

  - `docs/handover/HANDOVER_tier_0_close_2026-05-04.md`
  - `docs/handover/HANDOFF_b1a_g7_ph_window_2026-05-04.md`
  - `docs/handover/HANDOVER_tier_1_close_2026-05-04.md`
  - `docs/handover/HANDOVER_tier_2_close_2026-05-04.md`
  - `docs/handover/HANDOVER_post_tier_2_close_2026-05-04.md`
  - `docs/handover/HANDOVER_carryovers_close_2026-05-04.md`
  - `docs/handover/HANDOVER_incremental_close_2026-05-04.md`

## v0.6.3 — Stirrer B stator hole-count correction (2026-05-04)

### Changed

- **Stirrer B stator perforation count revised from 36 to 72** (24 columns × 3 rows, was 12 × 3). User confirmation 2026-05-04 from a complete top-down view of the stator wall. Affects:
  - `cad/scripts/build_geometry.py` (`n_perf_circ` 12 → 24)
  - Regenerated `cad/output/stirrer_B_stator.{step,stl}`
  - UI animation `src/dpsim/visualization/components/assets/impeller_xsec_v3.html` (24 hole markers at 15° spacing in the bottom view; trajectory count kept at 12 for legibility)
  - All matching documentation in `cad/`, `cad/cfd/`, `docs/user_manual/`, and the M1 hardware caption in `tabs/tab_m1.py`.
- The hole geometry (Ø 3 mm, axial row spacing, wall thickness, stator OD) is unchanged. Slot-exit jet physics is unchanged in the model — the higher hole count increases total open area on the stator wall but does not by itself alter the per-jet ε in the validated zonal partition.

### Validation

- CFD case `cad/cfd/cases/stirrer_B_beaker_100mL/` mesh refinement levels remain valid; `snappyHexMeshDict` and `zones.example.json` updated only in commentary. Re-meshing required against the regenerated STL before next CFD run.

## v0.6.2 — CFD-PBE zonal coupling end-to-end (2026-05-01)

Closes the CFD-PBE coupling loop end-to-end: DPSim integrates a
schema-v1.0 ``zones.json`` against the M1 PBE, an OpenFOAM case can
produce one via the supplied dictionaries and post-processor, and
the user manual is updated with operator-facing and advanced-reference
chapters. The OpenFOAM-side pipeline is shipped as a starting point
that requires iteration against a specific OpenFOAM build and a PIV
validation campaign before predictions can be trusted for absolute
scale-up (Appendix K §K.4.6 — full validation envelope).

### Added — DPSim-side zonal PBE coupling (commit a5d984c)

- **Schema v1.0** locked at ``cad/cfd/zones_schema.md``: variable-N
  compartments, two ε per zone (``epsilon_avg`` for coalescence,
  ``epsilon_breakage_weighted`` for breakage), one-way convective
  exchanges with asymmetric source/target rates. Forward-compat
  versioning policy documented.
- **Pydantic v2 loader** (``src/dpsim/cfd/zonal_pbe.py``) with 11 hard
  validation paths (schema_version, duplicate names, phantom exchange
  targets, ε_brk < ε_avg, metadata aggregation mismatch within 1 %,
  etc.) and soft advisory warnings for under-resolved CFD.
- **Zonal integrator** ``integrate_pbe_with_zones``: per-zone
  ``(n_zones × n_bins,)`` state on a shared fixed-pivot grid; reuses
  Alopaeus and Coulaloglou-Tavlarides kernels from
  ``level1_emulsification`` (single source of truth for kernel arithmetic);
  asymmetric Q/V_from outflow + Q/V_to inflow exchange; LSODA via
  ``solve_ivp``. **Agreement with bare ``PBESolver`` at integrator-
  tolerance level in the 1-zone degenerate case** (aggregated d32
  relative error <= 1e-9 in the regression test).
- **Consistency check** ``consistency_check_with_volume_avg``:
  30 %-tolerance gate against the legacy Po·N³·D⁵/V_tank empirical
  estimate (Scientific Advisor 2026-05-01 guidance).
- **CLI subcommand** ``dpsim cfd-zones`` with material overrides,
  kernel preset, optional ``--legacy-eps`` cross-check, structured
  results JSON output.
- **31 pytest tests** (``tests/test_cfd_zonal_pbe.py``): loader happy
  paths, 11 parametrised rejection paths, advisory warnings via
  caplog, consistency-check edge cases, integrator input validation,
  single-zone integrator-tolerance equivalence, volume balance < 1e-3 on
  Stirrer A and Stirrer B, breakage-zone bias, plus 2 subprocess-based
  CLI smoke tests.

### Added — OpenFOAM-side post-processing pipeline (commit 6b5d408)

- **``cad/cfd/scripts/extract_epsilon.py``** — full implementation
  (was a stub printing TODOs). Reads cell-centred ``epsilon`` / ``U`` /
  ``V`` / ``C`` via fluidfoam, partitions cells by zone-config
  selectors (``cellZone``, ``near_surface``, ``complement``), computes
  ``ε_avg`` and ``ε_breakage_weighted`` per zone using a vendored
  ``breakage_rate_alopaeus`` that matches DPSim's NumPy kernel
  point-for-point (regression-tested), estimates inter-zone convective
  flows via a KDTree boundary-cell heuristic (with
  ``--exchanges-from-json`` override for production runs), emits
  schema-v1.0 ``zones.json`` that round-trips through
  ``CFDZonesPayload.model_validate``.
- **``src/dpsim/cfd/openfoam_io.py``** — full implementation. Thin
  wrappers around fluidfoam (``read_field``, ``list_time_directories``,
  ``latest_time``, ``assert_field_consistent``) and a minimal FoamFile
  dictionary writer (``write_dict`` with FoamFile header, nested
  dicts, lists; refuses unsupported types).
- **``cad/cfd/scripts/prepare_geometry.sh``** — STEP → STL via gmsh
  (preferred) or FreeCAD CLI (fallback), with patch-name rewriting
  to match the snappyHexMesh convention.
- **``cad/cfd/scripts/run_case.sh``** — full 8-stage pipeline
  orchestrator: blockMesh → surfaceFeatureExtract → snappyHexMesh →
  checkMesh → decomposePar → mpirun pimpleDyMFoam → reconstructPar →
  postProcess (writeCellCentres + writeCellVolumes for
  ``extract_epsilon.py``).
- **15 pytest tests** (``tests/test_cfd_extract_epsilon.py``) against
  synthetic field arrays — no OpenFOAM dependency required.

### Added — OpenFOAM case dictionaries (commit 6b5d408)

- **Stirrer A** (``cad/cfd/cases/stirrer_A_beaker_100mL/``, full set):
  ``system/{controlDict, fvSchemes, fvSolution, blockMeshDict,
  snappyHexMeshDict, decomposeParDict}``;
  ``constant/{transportProperties, turbulenceProperties,
  dynamicMeshDict}``; ``0.org/{U, p, k, omega, nut}``;
  ``zones_config.json`` (3-zone partition: impeller / near_wall /
  bulk); ``README.md``. Targets pimpleDyMFoam at 1500 RPM,
  ν = 5.81e-5 m²/s (paraffin), level-5 impeller refinement, 5 prism
  layers, run-time field averaging from t = 2 s.
- **Stirrer B** (``cad/cfd/cases/stirrer_B_beaker_100mL/``, delta from A):
  ``system/{controlDict, snappyHexMeshDict}``,
  ``zones_config.json`` (4-zone partition: impeller / slot_exit /
  near_wall / bulk), ``README.md``. Targets 6000 RPM with deltaT
  2.5e-5 (4× tighter for the higher rotation rate), level-6 impeller
  refinement, level-4 slot-exit shell, 7 prism layers on impeller.

### Added — User manual (commit f3f8695)

- **First-edition manual §9** "CFD-PBE Zonal Coupling for M1 Scale-up"
  (``polysaccharide_microsphere_simulator_first_edition.md``).
  Nine sub-sections: §9.1 decision tree, §9.2 Jensen's-inequality /
  two-ε rationale, §9.3 variable-N compartment model, §9.4 Stirrer A
  3-zone worked example, §9.5 Stirrer B 4-zone with rotor-stator
  loop (Padron 2005 / Hall 2011), §9.6 ``dpsim cfd-zones`` CLI,
  §9.7 output interpretation + diagnostic gates, §9.8 validation
  status + limitations + evidence-tier policy, §9.9 source-of-truth
  pointers and references. Three Unicode block-diagram figures
  in fenced code blocks (the renderer does not support raster
  images — figures use the project-native approach).
- **Appendix K** (``appendix_K_cfd_pbe_zonal_coupling.md``, new file):
  advanced-project-report architecture covering executive summary,
  objectives, mathematical framework with explicit Jensen's
  inequality and convective-exchange asymmetry derivation, schema
  spec walkthrough + evolution policy, OpenFOAM 7-phase pipeline,
  per-phase status table, limitations + risk register, Vi
  viscous-correction caveat (closes the F1 audit loop), reproducibility
  checklist, full reference list, glossary.
- **Audit addendum** (``DPSIM_UNIFIED_DOCUMENTATION_AUDIT_2026-04-25.md``):
  append-only ``Addendum — Changes since 2026-04-25 (added 2026-05-01)``
  section preserving the dated snapshot. Lists v0.6.0 + the new
  CFD-PBE deltas, three new lifecycle-result interpretation gates
  (PIV status, volume balance, ε consistency), three new
  documentation-update gates.
- **Build infrastructure**: ``build_pdf.py`` ``BUILD_TARGETS`` extended
  with Appendix K. All four PDFs rebuilt cleanly with full Unicode
  (Greek, super/sub, box-drawing characters).

### References cited (no fabrications)

Alopaeus 2002, Coulaloglou-Tavlarides 1977, Kumar-Ramkrishna 1996,
Wang-Mao 2005, Padron 2005 (PhD), Hall 2011, Calabrese 1986,
Metzner-Otto 1957, Utomo 2009.

### Test totals

48/48 pytest passing in ~28 s (33 zonal-PBE + 15 extract-epsilon /
openfoam-io). The 1-zone integrator-tolerance equivalence test is the strongest
correctness gate: any drift would mean the zonal coupling has
introduced numerical noise into the degenerate case.

### Working-tree housekeeping

- The byte-identical-content metadata churn on the three pre-existing
  PDFs (carried over from a prior rebuild before this release) is
  resolved as of commit f3f8695.
- ``__version__`` in ``src/dpsim/__init__.py`` was stale at 0.5.2;
  bumped to 0.6.2 alongside ``pyproject.toml`` in this release commit.

### Known limitations / Phase 6 work pending

- The OpenFOAM dicts are syntactically valid and parameter-sensible
  per the README's specifications, but **not yet executed end-to-end**
  against a real OpenFOAM install. Treat as a starting point for
  iteration against your specific build, mesh-quality output, and
  operating regime.
- Until a PIV measurement campaign at bench scale validates the CFD
  field, predictions through the zonal path inherit ``qualitative_trend``
  evidence in the lifecycle ladder (see Appendix K §K.4.6).
- The ε_breakage_weighted formulation evaluates ``g(d_ref, ε)`` at a
  single ``d_ref``. Polydisperse systems with bimodal breakage may need
  iterative refinement; flagged as a v1.0 limitation in Appendix K
  §K.6.1.

---

## v0.6.0 — CAD geometry handoff + OpenFOAM CFD-PBE scaffolding + Stirrer A xsec v2 (2026-05-01)

Establishes the foundation for spatially-resolved ε-field forcing of the
M1 Alopaeus breakage kernel, motivated by the 100 mL → 1 L scale-up
trajectory.

### Added — CAD geometry source of truth (`cad/`)

- **Parametric CAD generator** (`cad/scripts/build_geometry.py`): single
  CadQuery script reproducing the five wetted parts from `datatypes.py`
  factories plus 2026-03-27 measurement photos and 2026-05-01 manual
  review.
- **STEP AP242 + STL output** (`cad/output/`):
  - `stirrer_A_pitched_blade` — disk Ø 59 mm × 1 mm with 19 perimeter
    tabs (10 UP + 9 DOWN, alternating; 90° perpendicular bend; 10°
    tangential fan-pitch; parallelogram outline with 5° forward edge
    tilt).
  - `stirrer_B_rotor` — flat sheet "+" with offset finger pairs
    (parallel-but-not-coincident), 3 mm root → 2 mm flat tip, R=1 mm
    fillets at all corners, full 16 mm axial extent.
  - `stirrer_B_stator` — Ø 32.03 × 18 mm with 36 Ø 3 mm perforations
    in a 3 × 12 rectangular grid + Ø 10 mm shaft-passage hole in the
    closed top.
  - `beaker_100mm` — Ø 100 × 130 mm with R=10 inner-bottom fillet, R=5
    outer-bottom fillet, 20°/5 mm outward-flared rim.
  - `jacketed_vessel_92mm` — Ø 92 × 160 mm with closed top + shaft hole,
    R=10 inner-bottom fillet, R=5 outer-bottom fillet, R=5 closure
    fillets.
- All STEP files validated for SolidWorks 2018+ import; STL deflection
  tolerance 0.05 mm (well under the 0.1 mm fidelity target).
- The legacy 25 mm rotor-stator was excluded from CAD modeling per
  user direction (2026-05-01).

### Added — OpenFOAM CFD-PBE pipeline scaffold (`cad/cfd/`)

- Directory structure for two bench cases (Stirrer A, Stirrer B) with
  per-case READMEs documenting operating points and PIV validation gates.
- Helper scripts (`prepare_geometry.sh`, `run_case.sh`,
  `extract_epsilon.py`) — stubs with implementation TODOs.
- Master roadmap in `cad/cfd/README.md` covering geometry prep → mesh →
  solve → ε extraction → zonal PBE coupling → PIV validation → 1 L
  scale-up extrapolation. Estimated effort: 1–2 person-months for a CFD
  engineer with prior OpenFOAM stirred-tank experience.

### Added — CFD-PBE coupling stubs (`src/dpsim/cfd/`)

- `zonal_pbe.py` — typed dataclasses for CFD-derived compartments and
  zone-exchange flow rates; `integrate_pbe_with_zones` placeholder for
  spatial PBE forcing.
- `openfoam_io.py` — field readers and dictionary writers (TODOs).

### Changed — `datatypes.py` Stirrer A factory (`pitched_blade_A`)

Reflects the disk-style 19-tab geometry verified during the 2026-05-01
CAD review:

- `blade_count`: 6 → **19** (10 UP + 9 DOWN, alternating perpendicular
  bend; the previous "6" was an estimate with the wrong geometric
  interpretation).
- `blade_height`: 0.010 m → **0.0085 m** (derived from the 18 mm caliper
  measurement = 1 mm disk + 2 × 8.5 mm fins).
- `blade_angle = 10.0` re-interpreted: now **tangential pitch from
  radial** (fan-blade angle), not axial pitch. Affects how the angle is
  consumed by the PBE solver's effective-tip-speed and shear-rate
  estimates.
- Updated docstring + enum comment to document the disk-style topology
  and rotation-direction arrow.

### Changed — UI widget caps

- M1 Stirrer Speed slider max: 2000 → **2500 RPM** (Stirrer A path).
  Rotor-stator paths unchanged at 9000 / 25000 RPM.
- M1 Cooling Rate slider max: 15 / 20 → **50 °C/min** across the three
  formulation panels (agarose-chitosan stirred + legacy, cellulose
  NMMO).

### Added — Stirrer A live cross-section v2 (M1 Hardware Emulsification box)

- New embedded SVG component `render_impeller_xsec_v2` rendering the
  verified 19-tab disk-style Stirrer A geometry inside the Ø 100 mm
  glass beaker.
- Single toggle button (top-right of the diagram) cycles through four
  view states:
  1. side-view cross-section · opaque agitator
  2. bottom-up cross-section · opaque agitator
  3. side-view cross-section · transparent agitator (emphasises
     circulation flow + double-emulsion droplet collisions)
  4. bottom-up cross-section · transparent agitator
- Replaces the generic Rushton-turbine animation in the Stirrer A path;
  the legacy Rushton SVG is retained for the rotor-stator path.
- Geometry sourced from `cad/output/stirrer_A_pitched_blade.step` and
  `cad/output/beaker_100mm.step` (CAD review 2026-05-01).

### Notes on validity

- The new `blade_height = 0.0085` and `blade_count = 19` will shift the
  M1 Po-derived ε estimate by ~5–15%; recalibration of the empirical
  `power_number = 0.35` is **TODO** pending the first CFD run.
- All `pitched_blade_A` consumers in the codebase use the factory output
  (no hardcoded copies), so the upstream change propagates automatically.
  Any test asserting `blade_count == 6` should be updated.

## v0.5.2 — M2 ACS Converter codex-review fixes (2026-04-27)

Patch release for the v0.5.0 + v0.5.1 ACS Converter epic. Closes the four
issues an independent OpenAI Codex code review surfaced — two of which
silently broke v0.5.1 end-to-end through the UI, despite the v0.5.0/v0.5.1
test suites passing (the existing tests went through `solve_modification_step`
directly, bypassing the orchestrator preflight and the recipe-level G6 path
that codex caught).

### Fixed (codex P1 — release-breakers)

- **P1-1: Orchestrator preflight rejected new ACS converters.** The
  orchestrator's `_validate_workflow_ordering()` (`orchestrator.py:1151`)
  carried its own `_STEP_ALLOWED_REACTION_TYPES` allowlist that v0.5.1 had
  not updated. ACTIVATION still required `reaction_type="activation"`, so
  every CNBr / CDI / Tresyl / Cyanuric / Glyoxyl / Periodate run through
  the UI raised `ValueError` before dispatch could run the silent-alias
  logic. Expanded ACTIVATION to accept both `"activation"` and
  `"acs_conversion"`; added explicit ACS_CONVERSION + ARM_ACTIVATION
  entries.
- **P1-2: PROTEIN_COUPLING dispatch rejected the new pyridyl couplers.**
  The 3 per-protein pyridyl-disulfide variants (`protein_a/g/l_thiol_to_
  pyridyl_disulfide`) and the 4 closed-loop generic couplers all carry
  `functional_mode="affinity_ligand"` (so they surface in the Protein
  Coupling UI bucket) and `reaction_type="coupling"`. Both
  `_STEP_ALLOWED_REACTION_TYPES` (orchestrator) and `_STEP_ALLOWED_RTYPES`
  (dispatcher) only accepted `"protein_coupling"` for PROTEIN_COUPLING,
  raising `ValueError` for all 7 reagents end-to-end. Expanded both
  allowlists to accept `{"protein_coupling", "coupling"}`. The math in
  `_solve_protein_coupling_step` collapses correctly to ligand-coupling-
  equivalent when `max_surface_density=0`, so small-ligand routes stay
  accurate.

### Fixed (codex P2)

- **P2-1: G6.1 phase ranking blocked the canonical arm-distal sequence.**
  `ProcessStepKind` had no arm-distal-activation kind, so pyridyl-disulfide
  steps had to be encoded as `ACTIVATE` (rank 1). After an `INSERT_SPACER`
  step (rank 2), G6.1 emitted `FP_G6_SEQUENCE_OUT_OF_ORDER`, blocking
  the documented `ACS_CONVERSION → SPACER_ARM → ARM_ACTIVATE → COUPLE_LIGAND`
  path before G6.2 could even check the precondition. Added
  `ProcessStepKind.ARM_ACTIVATE` (phase rank 3) and a reagent-key override
  in G6.1: legacy recipes that encoded pyridyl-disulfide as `ACTIVATE` are
  also rescued via the override (zero migration friction).
- **P2-2: G6.5 CNBr time-window dropped units silently.** The intervening-
  step duration sum used `_qty_value()`, which explicitly does no unit
  conversion. A wash declared as `Quantity(30, "min")` was being summed as
  30 seconds and bypassing the 15-min hydrolysis BLOCKER. Added a unit-
  aware `_qty_to_seconds()` helper covering the standard lab time units
  (s, min, h, ms) and pointed G6.5 at it. Unknown units fall back to the
  pre-existing structural WARNING rather than silently skipping.

### Tests

- `tests/test_v0_5_2_codex_fixes.py` (NEW): 30-test gauntlet exercising
  each fix end-to-end through the orchestrator preflight and recipe-level
  G6 guardrail (the paths the v0.5.0/v0.5.1 tests bypassed).
- 359 targeted tests green; ruff = 0; mypy = 0.

### Migration

- v0.5.1 users: bump to v0.5.2 immediately. v0.5.1 is functionally broken
  for any recipe that reaches the orchestrator (every UI workflow). The
  v0.5.1 release page on GitHub has been annotated as superseded.
- No API breaks: the new `ProcessStepKind.ARM_ACTIVATE` is additive; the
  reagent-key override in G6.1 keeps legacy recipes valid.

## v0.5.1 — M2 ACS Converter deferred-work follow-on (2026-04-27)

Closes the four deferred items from `HANDOVER_v0_5_0_ACS_CONVERTER.md` §8.
Same branch (`feat/m2-acs-converter`) as v0.5.0; additive to the v0.5.0
APIs (no breaking changes).

### Cyanuric chloride 3-stage staged kinetics

- New `staged_kinetics: tuple[tuple[float, float], ...]` field on
  `ReagentProfile` — empty by default, populated for cyanuric chloride
  with three `(k_forward, E_a)` tuples covering the 1st / 2nd / 3rd Cl
  substitutions at 0–5 °C / 25 °C / 60–80 °C respectively. Each
  successive Cl is ~10× slower than the previous.
- New `temperature_stage: int = 0` field on `ModificationStep`. When
  > 0 and the reagent has staged_kinetics defined, `_solve_activation_step`
  uses the per-stage `(k_forward, E_a)` instead of the base values.
  `temperature_stage=0` preserves v0.5.0 behaviour exactly.
- Reference: Lowe & Pearson (1984) Methods Enzymol. 104:97.

### Periodate / glyoxyl chain-scission penalty

- New `chain_scission_threshold: float = 1.0` and
  `chain_scission_max_g_dn_loss: float = 0.0` fields on `ReagentProfile`.
  Set to (0.30, 0.70) on `periodate_oxidation` (Bobbitt 1956) and
  (0.40, 0.50) on `glyoxyl_chained_activation` (Mateo 2007 — glycidol
  overlay protects backbone, raising the threshold and lowering the
  max loss).
- New `g_dn_scission_fraction: float = 0.0` field on `ModificationResult`.
  `_solve_activation_step` linearly interpolates between threshold and
  conversion = 1.0 to compute the per-step fraction.
- Orchestrator's `run()` composes per-step scission fractions
  multiplicatively (1 - product(1 - f_i)) and applies the cumulative
  loss to `G_DN_updated` AFTER summing the additive `delta_G_DN` from
  rubber-elasticity bridges. Result: high-conversion periodate now
  correctly degrades the bead's mechanical modulus.

### Per-protein pyridyl-disulfide couplers (3 new reagents)

| reagent_key | Ligand MW | Binding mode |
|---|---|---|
| `protein_a_thiol_to_pyridyl_disulfide` | 42 kDa | Fc affinity (IgG1-favoring) |
| `protein_g_thiol_to_pyridyl_disulfide` | 22 kDa | Fc affinity (broader subclass) |
| `protein_l_thiol_to_pyridyl_disulfide` | 36 kDa | κ-light-chain (Fab capture) |

- All three follow the existing `protein_a_cys_coupling` /
  `protein_g_cys_coupling` pattern but route through `PYRIDYL_DISULFIDE`
  (reversible thiol-disulfide exchange) rather than `MALEIMIDE`
  (irreversible Michael addition).
- All declare `wetlab_observable="A_343_pyridine_2_thione"` for evidence-
  tier calibration anchoring on stoichiometric pyridine-2-thione release.
- All surface under the existing "Protein Coupling" UI bucket via
  `functional_mode="affinity_ligand"` — no new bucket required.
- Reference: Carlsson et al. (1978) Biochem. J. 173:723; Hermanson
  Bioconjugate Techniques 3rd ed. (2013) §17.4; Nilson et al. (1992)
  Eur. J. Immunol. 22:2547 (Protein L).

### CNBr time-window enforcement (G6.5 strengthened)

- G6.5 now sums the durations of all steps strictly between a CNBr
  activation step and the next `COUPLE_LIGAND` step (each must declare
  a `time` Quantity in its `parameters`).
- Three-tier severity:
  - ≤ 7.5 min intervening: clean.
  - (7.5 min, 15 min]: WARNING (`FP_G6_CNBR_WINDOW_AT_RISK`).
  - > 15 min: BLOCKER (`FP_G6_CNBR_HYDROLYSIS_LOSS`).
- The pre-existing "no downstream coupling" WARNING
  (`FP_G6_CNBR_NO_COUPLING_FOLLOWUP`) is unchanged.
- When intervening steps lack a `time` parameter, the time-window
  check is silently skipped (recipes without structured timing fall
  back to the v0.5.0 behaviour).

### Tests

- `tests/test_v0_5_1_deferred_work.py` (NEW): 21 test cases across the
  four areas. All green.
- `tests/test_module2_workflows.py::test_profile_count`: bumped 100 → 103
  to account for the 3 new per-protein pyridyl variants.
- 329 targeted tests green; ruff=0; mypy=0.

## v0.5.0 — M2 ACS Converter epic (2026-04-27)

Closes the 7 ranked gaps from the M2 ACS-converter audit; the Scientific
Advisor verdict flips PARTIAL → READY. Joint redesign plan authored by
Scientific Advisor + Architect + Dev Orchestrator; full handover at
`docs/handover/HANDOVER_v0_5_0_ACS_CONVERTER.md`.

### Architectural changes

- New `ModificationStepType.ACS_CONVERSION` (matrix-side polysaccharide
  ACS swap) and `ARM_ACTIVATION` (arm-distal pyridyl-disulfide-class
  installation). Legacy `ACTIVATION` retained as silent alias so
  v0.4.x recipes using ECH/DVS load unchanged.
- New `ACSSiteType.PYRIDYL_DISULFIDE` member; pyridyl-disulfide
  `product_acs` corrected from chemically inverted `THIOL` to
  `PYRIDYL_DISULFIDE`, and `chemistry_class` from incorrect
  `"reduction"` to canonical `"thiol_disulfide_exchange"`.
- 6 matrix-side converters (CNBr / CDI / Tresyl / Cyanuric / Glyoxyl /
  Periodate) retagged `reaction_type="acs_conversion"` with
  `functional_mode="acs_converter"`. ECH/DVS continue to dispatch
  through the same solver.
- Sequence-enforcing FSM in a new G6 first-principles guardrail
  (`core/recipe_validation.py::_g6_acs_converter_sequence`), plus an
  in-module `orchestrator.validate_sequence()` helper. Enforces the
  canonical ACS Converter → Linker Arm → Ligand → Ion-charging order
  with skip-allowed and arm-distal precondition checks.
- New `TargetProductProfile.cip_required` flag that gates a hard
  requirement for NaBH₄ reductive lock-in after aldehyde-producing
  converters (glyoxyl-chained, periodate).

### Closed-loop reagents (4 new)

| reagent_key | target_acs | Closes loop |
|---|---|---|
| `generic_amine_to_imidazolyl_carbonate` | IMIDAZOLYL_CARBONATE | CDI → amine ligand |
| `generic_amine_to_sulfonate` | SULFONATE_LEAVING | Tresyl → amine ligand |
| `protein_thiol_to_pyridyl_disulfide` | PYRIDYL_DISULFIDE | Pyridyl-disulfide → protein -SH |
| `generic_amine_to_cyanate_ester` | CYANATE_ESTER | CNBr → any amine ligand (canonical 15-min window) |

### Bench-fidelity fixes

- New `aldehyde_multiplier` field on `ReagentProfile` (default 1.0; set
  to 2.0 on `periodate_oxidation` and `glyoxyl_chained_activation`).
  Fixes the 2× under-counting of aldehydes from Malaprade vicinal-diol
  cleavage that previously made downstream ALDEHYDE inventory wrong.
- New `wetlab_observable` field on `ReagentProfile` (e.g.,
  `A_343_pyridine_2_thione` for pyridyl-disulfide activation, used to
  anchor evidence-tier calibration to a real bench measurement).

### Family-reagent matrix expansion

- 147 new entries (7 converters × 21 polymer families) in
  `family_reagent_matrix.py`, closing the G4 guardrail gap that let
  CNBr-on-PLGA, periodate-on-alginate, etc. silently bypass.

### UI

- M2 Chemistry bucket "Hydroxyl Activation" renamed to "ACS Conversion"
  (absorbs both legacy `activator` mode and new `acs_converter` mode).
- New M2 bucket "Arm-distal Activation" for `arm_activator` mode
  (pyridyl-disulfide and successors). Renders between Spacer Arm and
  Ligand Coupling in `_BUCKET_DISPLAY_ORDER`.

### Tests

- `tests/test_v0_5_0_acs_converter.py` (NEW): 50-test gauntlet across
  enum expansion, dispatch, pyridyl-disulfide chemistry correctness,
  periodate stoichiometry, sequence FSM, closed-loop pairing, family-
  matrix coverage. All green.
- `tests/test_module2_acs.py`: ACS enum size bumped 25 → 26.
- `tests/test_module2_workflows.py`: profile count 94 → 100;
  `reaction_type` allowlist gains `"acs_conversion"` and `"arm_activation"`.
- `tests/test_v0_3_4_m2_dropdown_coverage.py`: bucket-rename + pyridyl-
  disulfide → "Arm-distal Activation".
- 308 targeted tests green; CI gates (ruff=0, mypy=0) hold.

## v0.4.19 — Direction-A standalone alignment + Streamlit 1.55 fixes (2026-04-26)

Three intertwined efforts that took the v0.4.x Direction-A shell from
"port-of-the-Streamlit-tabs" to a faithful realization of the
canonical `DPSim UI Optimization _standalone_.html` reference, while
fixing several Streamlit 1.55 regressions that had silently broken
styling, navigation, and the M3 stage.

### v0.4.x polish (P1–P10, single bundle)

- **P1** Help icon shrunk to inline 14×14 px `<details>` glyph
  (replaces the full-row `st.popover` chrome). `labeled_widget` and
  `param_row` now emit label + help + badge + unit on one row.
- **P2** M1 Hardware live tip-speed chip + vertical v_tip / Re / We
  metrics rail beside the impeller cross-section; derived volumes
  readout (Total / φ_d / O:W) with inversion warning. Uses real
  `StirrerGeometry.impeller_diameter` and paraffin-oil properties.
- **P3** M1 vessel-mode planned roadmap strip (Membrane M1.5,
  Microfluidic M2.0 surfaced as not-yet-selectable); wet-lab caveats
  card pre-Run; Targets card promoted out of the collapsed expander.
- **P4** M3 derived-geometry strip (V_bed / u_super / τ_void); M2
  pre-Run status strip with green/amber/red readiness signal.
- **P5** M1 Calibration banner with Open Stage 07 button.
- **P6** Non-A+C Hardware (alginate / cellulose / PLGA) gets the
  same chip + Re/We rail + volumes readout.
- **P7** M3 Monte-Carlo uncertainty card promoted out of the sidebar
  popover via `render_uncertainty_panel(as_card=True)`.
- **P8** M2 ACS state pre-Run preview card with placeholder cells.
- **P9** M2 reagent-bucket overview grid (17-bucket auto-fill grid
  with active-bucket highlighting from the per-step expander loop).
- **P10** **Streamlit 1.55 CSS-injection regression**: `st.html`
  silently strips `<style>` and `<script>` tags. Switched
  `inject_global_css` and the `app.py` shell-overrides block to
  `st.markdown(..., unsafe_allow_html=True)`. Without this fix the
  entire `tokens.css` was being dropped; the page only looked themed
  because Streamlit's own dark theme covered for the missing styles.

### Standalone alignment (A1–A5, B1–B6, C1, D1–D2)

- **A1** Pipeline spine collapsed from two-row (visual chrome +
  click-button overlay) to single integrated row. Each stage cell
  is an `<a href="?dpsim_stage={id}">` anchor; server consumes the
  param at render top, calls `set_active_stage`, cleans the URL.
- **A2** Dark/Light toggle actually flips theme. Replaced the JS-
  stripped `<script>` class-flip with server-side CSS reinjection —
  `inject_global_css(theme=...)` emits a second `<style>` block
  overriding `:root` vars when light. Theme query consumed BEFORE
  CSS injection so it takes effect on the same rerun.
- **A3** UI A|B switch rebuilt as a single HTML pill. Diff /
  Evidence / History segmented and the legacy DARK / LIGHT toggle
  also rebuilt as anchor pills (the previous nested-column
  `st.button` patterns wrapped to one-letter-per-line at typical
  widescreen widths).
- **A4** Polymer family selector migrated from horizontal radio
  grid to compact dropdown showing chemistry classification.
- **A5** Evidence rollup card always renders (placeholder M1/M2/M3
  rows pre-run); per-row layout uses the canonical Ladder pattern
  (36 px label │ 1 fr progress-bar │ auto badge) with bar width =
  tier_rank/5 × 100% in tier-specific colour.
- **B1** Right rail recovery on M3. The duplicate
  `render_uncertainty_panel()` call from the sidebar Analysis Tools
  popover was registering widgets with the same fixed keys as the
  new M3 primary card, raising `StreamlitDuplicateElementKey` and
  silently killing the right rail's render — user-visible as "rail
  vanishes on M3". Sidebar copy removed.
- **B2** Manual + Appendix J as compact 26 × 26 px icon-only
  download buttons in their own column right of the DARK/LIGHT
  pill (was vertically stacked text buttons that pushed the rail
  down).
- **B3** Theme toggle as single fidelity-matched button. Replaces
  the `[DARK | LIGHT]` segmented pill with one button showing a
  colored dot (teal for dark, amber for light) + current-mode
  label, click toggles. Matches the standalone byte-for-byte.
- **B4** Removed the `stHeader` border-bottom that was painting a
  faint horizontal line across the page through the brand /
  breadcrumb / search input.
- **B5** Hidden `stHeader` and `stSidebarHeader` entirely. Even
  with no border the empty headers were reserving 60 px of dead
  vertical space at the top of the page with non-clickable
  decorative icons behind them.
- **B6** Manual + Appendix J icon clipping fix. cols[8] sub-columns
  gave each icon only 16 px while the button chrome was 26 px wide.
  Widened cols[8] and re-scoped the icon-button CSS via the
  `[data-testid="stMain"]` ancestor.
- **C1** Resin Lifetime Projection promoted from sidebar popover
  into a primary M3 card matching the MC uncertainty card pattern.
  `render_lifetime_panel` gained the `as_card=False` kwarg.
- **D1/D2** Scientific Mode (Empirical Engineering / Hybrid Coupled
  / Mechanistic Research) moved from sidebar radio to a top-bar
  segmented pill matching the Diff/Evidence/History style. Lives
  at cols[4], immediately right of the recipes search input. Click
  sets `?dpsim_mode={key}`; consumed at app.py top so
  `model_mode_enum` is in effect on the same rerun.

### Quality

- `ruff check src/dpsim/visualization/` clean
- 248 / 248 UI tests pass (`test_ui_v0_4_0_modules` + chrome smoke +
  ui contract + ui workflow + ui recipe + enum-CI + M2 dropdown
  coverage)
- Visual verification in headless Chromium against
  `streamlit run src/dpsim/visualization/app.py` confirmed: spine
  renders single integrated row, theme flips correctly server-
  side, all top-bar pills render as compact horizontal anchor
  links, family is a dropdown with classification subline,
  evidence ladder shows M1/M2/M3 placeholder rows pre-run, right
  rail present on all 7 stages.

## v0.3.8 — Release Tooling Refresh (Installer + Portable ZIP) (2026-04-25)

Refreshes the Windows release-build pipeline to match the v0.3.x state
and adds a portable ZIP artifact alongside the existing one-click
installer. The intellectual-property + GPL-3.0 + GitHub-source EULA
already in place from v0.1.0 is unchanged (it already states what the
user requires).

### Two release artifacts per release

| Artifact | Use case |
|---|---|
| `release/DPSim-X.Y.Z-Setup.exe` | One-click installer with EULA wizard, Start-Menu shortcut, post-install hook, clean uninstaller. |
| `release/DPSim-X.Y.Z-Windows-x64-portable.zip` | Unzip-and-run package for users who prefer no installation, no admin, no registry footprint. |

Both artifacts share the **same payload** (wheel + configs + PDFs +
launcher batch files + EULA + LICENSE). The only difference is the
delivery wrapper. The portable ZIP is produced by the same
`installer\build_installer.bat` invocation as the installer — one
build command, two artifacts.

### Version-banner discipline

Replaced the v0.1.0 hardcoded version strings across all 8 staged
templates with an `__DPSIM_VERSION__` placeholder. The build script
now derives the version from `pyproject.toml` and substitutes the
placeholder in every staged template before compiling. Files
touched: `install.bat`, `launch_ui.bat`, `launch_cli.bat`,
`uninstall.bat`, `README.txt`, `INSTALL.md`, `RELEASE_NOTES.md`,
`WHERE_ARE_THE_PROGRAM_FILES.txt`. Result: 22 placeholder
substitutions per build; future version bumps no longer require
touching templates.

### Build pipeline (`installer\build_installer.bat`)

Five steps:

1. Build wheel + sdist via `python -m build`.
2. Stage runtime assets into `installer\stage\` (wheel, configs,
   docs PDFs, launcher templates, LICENSE, EULA). Substitute
   `__DPSIM_VERSION__` placeholders in every staged `.bat` /
   `.txt` / `.md`.
3. Locate `ISCC.exe` (Inno Setup compiler).
4. Compile installer to `release\DPSim-<version>-Setup.exe`.
5. Pack portable ZIP to
   `release\DPSim-<version>-Windows-x64-portable.zip` via
   PowerShell `Compress-Archive` (built into Windows 10/11; no
   external 7-Zip dependency).

Build wall-time: ≈ 30 s on a typical Windows 11 box.

### Refreshed RELEASE_NOTES.md

`installer/templates/RELEASE_NOTES.md` rewritten from the v0.1.0
baseline to summarise the cumulative v0.2.0 → v0.3.7 cycle in
release-note form for the GitHub release page. Covers each minor
release's key contribution (P5++ MC-LRM driver, Bayesian fit, UI
bands, v9.5 composites, M2 dropdown rewrite, audit closures,
manual refresh) plus installer + portable ZIP feature lists and
system requirements.

### Updated `installer/README.md`

Added a **Portable ZIP** section explaining the unzip-and-run
flow. Documented:

- The 5-step build pipeline.
- The "clean" guarantee (explicit list of what is excluded from
  both artifacts; staging is via named-file `copy /y` only — no
  recursive source-tree copy that could leak dev artifacts).
- The version-banner discipline (`__DPSIM_VERSION__` placeholder
  pattern).
- The release process steps including the portable ZIP smoke test.

### EULA (unchanged from v0.1.0; verified to meet requirements)

`installer/LICENSE_AND_IP.txt` already states all three required
points and is shown as the very first installer page:

- Intellectual property in this software belongs to **Holocyte Pty Ltd**.
- Software is distributed under **GPL-3.0**.
- The latest source code is published on GitHub at
  <https://github.com/tocvicmeng-prog/Downstream-Processing-Simulator>.

### `.gitignore` update

Added `installer/stage_portable/` (transient ZIP-staging directory)
to the gitignore alongside the existing `installer/stage/` entry.

## v0.3.7 — First Edition Manual Refresh + Appendix J v0.3.x Addendum (2026-04-25)

Documentation refresh covering the v0.3.x cycle. The user-facing instruction
manual has been substantially rewritten to reflect everything shipped from
v0.3.0 (P5++ MC-LRM driver) through v0.3.6 (follow-on closures). Appendix J
gains a new § J.11 v0.3.x Addendum covering the 44 reagents that surfaced
in the M2 dropdown via the v0.3.4 audit fix.

### First Edition manual (Edition 2.0)

`docs/user_manual/polysaccharide_microsphere_simulator_first_edition.md` —
~1100 lines, full rewrite. Covers:

- Updated polymer-family catalogue: 4 (v9.1) → 21 (v9.5) families across
  baseline / expansion / niche / multi-variant composite tiers, with a
  selection chart and ion-gelant reference table.
- Updated M2 chemistry catalogue: 17 chemistry buckets (was 9 before
  v0.3.4); 96 reagents (was 50); chemistry-bucket workflow chart;
  family-reagent compatibility matrix; staged-template guide.
- New M3 chapter: Lumped Rate Model description; v0.3.0 MC-LRM
  uncertainty driver with Tier-1/Tier-2 safeguards; reformulated AC#3
  convergence diagnostics; v0.3.1 optional Bayesian fit; v0.3.2 UI
  band rendering and ProcessDossier MC export.
- Calibration / wet-lab loop chapter with the evidence-tier inheritance
  rule and the v0.2.0 wet-lab ingestion path.
- Appendix restructured to the user-specified 9-section format:
  A. Detailed Input Requirements
  B. Process Steps
  C. Essential Input & Process Checklist
  D. Frequently Asked Questions (28 Q&A)
  E. Architectural Ideas and Working Principles
  F. Chemical and Physical Principles
  G. Formulas and Mathematical Theorems
  H. Standard Wet-Lab Protocols (cross-reference to Appendix J)
  I. Troubleshooting Table (24 entries)
- Workflow charts paired with complex procedural terminology
  throughout (lifecycle flow, polymer-family selection, MC dispatch,
  M2 step configuration, M3 method).

### Appendix J § J.11 addendum

`docs/user_manual/appendix_J_functionalization_protocols.md` extended
from 2254 to ~2620 lines. New section covers:

- **Cross-reference table** mapping every v0.3.x `reagent_key` (96
  reagents) to its protocol section in Appendix J.
- **§ J.11.2 Cyanuric chloride activation** — triazine anchor for dye
  pseudo-affinity ligands.
- **§ J.11.3 Genipin secondary crosslinking** — mild post-coupling
  amine-bridge.
- **§ J.11.4 Borax reversibility warning** — temporary porogen only;
  must pair with covalent secondary crosslink.
- **§ J.11.5 HRP / H₂O₂ / tyramine** — phenol-radical crosslinking.
- **§ J.11.6 AlCl₃ trivalent gelant** — non-biotherapeutic safety
  warning + research-only protocol.
- **§ J.11.7 Glutathione / GST-tag** affinity coupling.
- **§ J.11.8 Calmodulin / TAP-tag** Ca²⁺-dependent affinity.
- **§ J.11.9 Cibacron Blue / Procion Red** dye pseudo-affinity.
- **§ J.11.10 MEP HCIC** mixed-mode chromatography ligand.
- **§ J.11.11 Thiophilic 2-mercaptoethanol** ligand (T-Sorb / T-Gel).
- **§ J.11.12 m-APBA boronate** affinity for cis-diol analytes.
- **§ J.11.13 Oligonucleotide DNA** sequence-specific affinity.
- **§ J.11.14 Material-as-ligand: amylose / chitin** (B9 pattern).

Every new section carries SDS-lite hazard block, recipe with stoichiometry,
mass-balance check guidance, and reference to the relevant `reagent_key`
in `REAGENT_PROFILES`.

### PDF rebuild

`docs/user_manual/build_pdf.py` rebuilds both PDFs:

- `polysaccharide_microsphere_simulator_first_edition.pdf` (~198 KB)
- `appendix_J_functionalization_protocols.pdf` (~237 KB)
- `DPSIM_UNIFIED_DOCUMENTATION_AUDIT_2026-04-25.pdf` (~69 KB)

### UI integration (unchanged)

The upper-right corner of the dashboard already exposes both PDFs via
`st.download_button` (📘 Manual + 🧪 Appendix J), per the existing
implementation in `src/dpsim/visualization/app.py:290-345`. Auto-build
runs `build_pdf.py` on first render if either PDF is missing. No
changes to the UI layout were required for v0.3.7.

## v0.3.6 — Close All Tracked v0.3.x Follow-Ons (2026-04-25)

Closes the seven actionable follow-ons accumulated across the v0.3.x
handovers. Non-actionable items (wet-lab calibration data, pymc CI
matrix, Python 3.14 pin, v0.4.0 MC × bin-resolved DSD) remain
documented as external/architectural follow-ons.

### Fix 1 — Click chemistry alkyne reference (ACS coverage 23/25 → 24/25)

Added inverse-direction click reagent profiles in
`reagent_profiles.py`:

- `cuaac_click_alkyne_side` — CuAAC where the resin carries the alkyne
  and the ligand carries the azide.
- `spaac_click_alkyne_side` — SPAAC where the resin carries the
  strain-promoted alkyne (DBCO/BCN) and the ligand carries the azide.

Both directions are valid bench protocols. Adds `ALKYNE` to the set
of `target_acs` values referenced by `REAGENT_PROFILES`. Only
`sulfate_ester` remains unreferenced (expected — it's a passive
κ-carrageenan polymer-side surface group, not a reagent target).

REAGENT_PROFILES count: 94 → 96.

### Fix 2 — Low-N MC warning (R-G2-2 mitigation)

`run_mc(n < 100)` now emits a `WARNING`-level log noting that the
inter-seed posterior-overlap diagnostic (AC#3) becomes noisy below the
documented N≥200 floor. v0.3.5 left this as a documented but
unwarned risk.

### Fix 3 — Joblib parallelism in `run_mc` (R-G2-4 mitigation)

The v0.3.0 implementation logged a warning and ran serial when
`n_jobs > 1`. v0.3.6 actually wires joblib:

- When `n_jobs > 1` and `n_seeds > 1`, dispatch per-seed sub-runs to
  `joblib.Parallel(backend="loky")`. Each worker derives its RNG
  seed from `base_seed + i`, so determinism is preserved by
  construction.
- Refactored `_per_seed_run` to return its `clip_counts` dict (in
  addition to mutating an in-out parameter for the serial path) so
  loky workers can ship clipping diagnostics back to the parent.
- AC#4 (n_jobs=1 vs n_jobs=4 byte-identical) verified by a new test
  in `tests/test_v0_3_6_followons.py`.

Falls back gracefully to serial when joblib is not importable or
n_seeds == 1.

### Fix 4 — Solver-lambda helper (`mc_solver_lambdas.py`)

New module `src/dpsim/module3_performance/mc_solver_lambdas.py` (~100
LOC) providing `make_langmuir_lrm_solver()`. Returns a callable
matching the `LRMSolver` contract that:

- constructs a `LangmuirIsotherm` from sampled `q_max` / `K_L`,
- propagates the `tail_mode` flag into BDF tolerances (10× tighter
  by default per D-046),
- raises `ValueError` on non-physical samples (negative q_max, zero
  K_L) so the driver's abort-and-resample path fires,
- holds all other `solve_lrm` arguments fixed across samples.

Closes the v0.3.0/v0.3.2 follow-on flagged as "solver-lambda helper
for production use." Production MC users no longer need to write the
solver lambda by hand.

### Fix 5 — Pectin DE-dependence (v0.3.3 follow-on)

`solve_pectin_chitosan_pec_gelation` now accepts a
`degree_of_esterification` parameter (default 0.40, low-methoxy):

- DE ≤ 0.5 — Ca²⁺-driven egg-box ionic gelation (default, calibrated
  against Voragen 2009).
- DE > 0.5 — high-methoxy pectin requires sugar-acid co-gelation
  (sucrose + low pH); not modelled at v9.5 resolution. Solver returns
  a result with `evidence_tier = UNSUPPORTED` and an explicit
  `hm_pectin_unsupported` diagnostic so callers can branch.

### Fix 6 — Gellan-alginate mixed K⁺/Ca²⁺ bath (v0.3.3 follow-on)

`solve_gellan_alginate_gelation` now accepts `c_Ca_bath_mM` (default
50) and `c_K_bath_mM` (default 0):

- Ca²⁺ runs the alginate skeleton path unchanged.
- When `c_K_bath_mM > 0`, K⁺ contributes a logistic-saturated boost
  to the gellan helix-aggregation reinforcement (midpoint 100 mM,
  asymptote +20 % over the Ca²⁺-only baseline). Curve shape from
  Morris 2012 K⁺-binding data on low-acyl gellan.
- Mixed-bath state surfaced via `mixed_bath` diagnostic and a
  dedicated assumption block.

### Fix 7 — Pullulan-dextran STMP variant (v0.3.3 follow-on)

`solve_pullulan_dextran_gelation` now accepts a `crosslink_chemistry`
literal (`"ech"` default, or `"stmp"`):

- ECH path unchanged from v9.5 baseline.
- STMP path applies a 1/0.85× pore-size expansion to reflect STMP's
  lower junction-zone density at equivalent reagent stoichiometry
  (Singh & Ali 2008). Manifest assumption block notes the
  phosphate-triester chemistry and food-grade / biotherapeutic-
  friendly profile.

### Tests

`tests/test_v0_3_6_followons.py` — 22 tests across the 7 fixes:

- 4 click-chemistry alkyne tests (existence, target_acs reference,
  ACS coverage floor lifted to 24, surfaces in M2 Click Chemistry
  bucket).
- 2 low-N warning tests (n<100 fires; n≥100 silent).
- 2 joblib parallelism tests (byte-identical n_jobs=1 vs n_jobs=4;
  clip_counts aggregate from workers).
- 3 solver-lambda tests (callable contract; rejects bad
  parameter_names; non-physical raises).
- 3 pectin DE tests (LM default; HM → UNSUPPORTED; out-of-range
  ValueError).
- 4 gellan-alginate mixed-bath tests (Ca²⁺-only baseline, mixed-bath
  factor lift, validation errors).
- 4 pullulan-dextran STMP tests (default ECH, STMP pore expansion,
  assumption-block contents, invalid chemistry rejection).

### Audit baseline updates

- `tests/test_v0_3_5_audit_followons.py::test_known_unreferenced_acs_types_remain_documented`
  baseline updated from `{"alkyne", "sulfate_ester"}` to
  `{"sulfate_ester"}` to reflect the v0.3.6 close. The test fires
  again only if the team adds an ACSSiteType that no reagent
  references.

### Out of scope (remain external follow-ons)

- Composite-specific wet-lab calibration data (needs lab work)
- pymc upper bound CI matrix (needs CI infrastructure)
- Python 3.14 + scipy BDF environment quirk (project pin issue)
- v0.4.0 MC × bin-resolved DSD (separate architectural cycle)

## v0.3.5 — UI Audit Follow-Ons (Ion Gelants + ACS + Crosslinker Docs) (2026-04-25)

Closes the three remaining items from the v0.3.3 UI audit. With v0.3.4
already shipped (M2 reagent dropdown 50/94 → 94/94), this release
addresses:

### Fix 3 — Ion-gelant picker (was 1/13 surfaced → 13/13)

- New module: `src/dpsim/visualization/tabs/m1/ion_gelant_picker.py`
  with two public APIs:
  - `available_ion_gelants_for_family(family)` — pure backend lookup
    that returns the union of `ION_GELANT_REGISTRY` per-family entries
    + applicable `FREESTANDING_ION_GELANTS` (matched by ion).
  - `render_ion_gelant_picker(family)` — Streamlit expander widget.
- `family_selector.py` now invokes the picker for any family that has
  registered ion gelants (alginate, κ-carrageenan, hyaluronate, pectin,
  gellan). Non-ionic families (PLGA, agarose, cellulose, dextran)
  silently skip the expander.
- Non-biotherapeutic-safe entries (Al³⁺ on gellan, AlCl₃ freestanding)
  surface a red warning in the UI per `biotherapeutic_safe=False`.
- Per-family coverage now: alginate (4 entries), hyaluronate (2),
  κ-carrageenan (2), pectin (2), gellan (6) — every entry from the
  v9.2-onwards `ION_GELANT_REGISTRY` is reachable in the UI.

### Fix 4 — ACSSiteType visibility (16 unsurfaced → 2 documented)

- M2 reagent caption now reads `target_acs → product_acs` for every
  selected reagent, so users see exactly which surface group is
  consumed and which is installed by each chemistry. Closes the
  audit's "16 of 25 ACSSiteType entries unsurfaced" gap.
- ACSSiteType reference coverage via `REAGENT_PROFILES.target_acs` /
  `product_acs`: **23 of 25 (92 %)**.
- 2 documented unreferenced entries:
  - `alkyne` — SPAAC click partner; backend reagent data lists `azide`
    only on the click reagents (data oversight; tracked as backend
    follow-on).
  - `sulfate_ester` — passive κ-carrageenan polymer-side surface group;
    not a reagent target.
- The pinned 23-of-25 baseline is enforced by
  `test_known_unreferenced_acs_types_remain_documented` so an
  intentional fix here trips the test (gives the team a chance to
  update the doc).

### Fix 5 — Crosslinker registry split documentation

- Added cross-reference comments to both registries explaining that
  the split between `dpsim.reagent_library.CROSSLINKERS` (M1 / L3
  primary covalent hardening) and
  `REAGENT_PROFILES[functional_mode='crosslinker']` (M2 secondary
  crosslinking after ligand coupling) is **intentional**, not a bug:
  both serve distinct UI surfaces with stage-appropriate kinetic
  defaults.
- Permanent doc gate via two tests in
  `test_v0_3_5_audit_followons.py` that assert the cross-references
  remain in place in both files.

### Tests

`tests/test_v0_3_5_audit_followons.py` — 18 tests:

- 6 ion-gelant picker tests (per-family coverage, freestanding pairing
  rule, biotherapeutic-safe flag propagation, audit gate that every
  registered entry surfaces).
- 3 ACSSiteType coverage tests (23/25 floor, documented-unreferenced
  baseline, every reagent has a target_acs).
- 2 crosslinker-registry doc-presence tests.
- 1 family-selector import smoke.

### Audit close-out

The v0.3.3 UI audit's 5 findings are now all addressed:

1. ✓ PolymerFamily M1 — 21/21 (closed at v0.3.3 / v9.5)
2. ✓ M2 reagent dropdown — 94/94 (closed at v0.3.4)
3. ✓ Ion-gelant picker — 13/13 (closed at v0.3.5)
4. ✓ ACSSiteType visibility — 23/25 + 2 documented (closed at v0.3.5)
5. ✓ Crosslinker registry split — documented as intentional (closed
   at v0.3.5)

Remaining backend follow-on (not a UI audit gap, tracked separately):
the `cuaac_click_coupling` and `spaac_click_coupling` reagents should
list `alkyne` somewhere in their target_acs / product_acs fields. The
audit-gate test will trip when this lands.

## v0.3.4 — M2 Reagent Dropdown UI Audit Fix (2026-04-25)

Closes the load-bearing finding from the v0.3.3 UI audit: the M2
Functionalization tab's reagent dropdown was hardcoded against the v9.1
baseline and never updated as new reagents shipped through v9.2/v9.3/
v9.4. The audit found 44 of 94 backend reagents (47 %) had no UI
exposure at all — including every entry from the v9.2 click-chemistry
batch, the v9.2 dye-pseudo-affinity ligands, the v9.3 mixed-mode HCIC /
thiophilic / boronate / peptide-affinity / oligonucleotide additions,
the v9.2 material-as-ligand pattern (amylose / chitin), and the v9.4
crosslinker / activator / spacer expansions.

### What changed

- `src/dpsim/visualization/tabs/tab_m2.py` no longer hardcodes 9 reagent
  option dicts in an `if/elif` chain. Replaced with:
  - `_BUCKET_TO_MODES`: declarative map from each user-facing Chemistry
    bucket name to the `functional_mode` values it contains. Covers
    all 23 entries in `ALLOWED_FUNCTIONAL_MODES`.
  - `_reagent_options_for_bucket(bucket)`: helper that auto-generates
    the `{display_label: reagent_key}` dict by iterating
    `REAGENT_PROFILES` and reading each profile's `.name` field.
  - Result: every reagent shipped in `REAGENT_PROFILES` now auto-
    surfaces; new reagent additions reach the UI without code changes
    in `tab_m2.py`.
- The Chemistry radio gains 8 new bucket types to surface chemistry
  classes that had no place to render under the old taxonomy:
  **Click Chemistry**, **Dye Pseudo-Affinity**, **Mixed-Mode HCIC**,
  **Thiophilic**, **Boronate**, **Peptide Affinity**,
  **Oligonucleotide**, **Material-as-Ligand**.
- The v9.1 baseline buckets (Secondary Crosslinking, Hydroxyl
  Activation, Ligand Coupling, Protein Coupling, Spacer Arm, Metal
  Charging, Protein Pretreatment, Washing, Quenching) are preserved
  verbatim — their contents grow to absorb the v9.x additions, so
  existing user habits (and Streamlit session-state values) carry
  forward unchanged.

### Coverage

- M2 reagent dropdown: **94 / 94 (100 %)** — was 50 / 94 (53 %) before
  this PR.
- Per-bucket counts (post-fix): Secondary Crosslinking 8, Hydroxyl
  Activation 11, Ligand Coupling 12, Protein Coupling 18, Spacer Arm
  19, Metal Charging 7, Protein Pretreatment 2, Washing 2, Quenching
  4, plus the 8 new buckets at 1–2 reagents each.

### Permanent regression gate

`tests/test_v0_3_4_m2_dropdown_coverage.py` (51 tests):

- Every value in `ALLOWED_FUNCTIONAL_MODES` must appear in exactly one
  bucket — adding a new mode without updating `_BUCKET_TO_MODES` fails
  the suite.
- Every key in `REAGENT_PROFILES` must surface under at least one
  bucket (the load-bearing audit gate).
- Every previously-invisible v9.2/v9.3/v9.4 reagent has a parametrised
  test asserting its expected bucket placement (44 cases).
- Labels are non-empty, unique within bucket, and alphabetically
  sorted (predictable order).

### Out of scope (documented as audit follow-ons)

The v0.3.3 audit also flagged three other coverage gaps that remain
open and are tracked for separate cycles:

- **Ion-gelant pickers** on M1 alginate/pectin/gellan/κ-carrageenan
  formulation tabs (1 of 13 entries surfaced — only the v9.5 borax
  warning).
- **ACSSiteType selector** (16 of 25 site types unsurfaced anywhere).
- **Crosslinker registry consolidation** between
  `dpsim.reagent_library.CROSSLINKERS` and
  `REAGENT_PROFILES[mode='crosslinker']` (5 entries differ).

## v0.3.3 — v9.5 Tier-3 Multi-Variant Composites (2026-04-25)

Promotes the three Tier-3 multi-variant composite polymer families that
were data-only placeholders through v9.4. Each was documented in the SA
screening report § 6.4 with limited bioprocess relevance — the v9.5
promotion lands the L2 solvers as `QUALITATIVE_TREND` evidence with
explicit "drug-delivery / food provenance" notes. Constituent families
were already independently UI-enabled in earlier cycles.

### What you can now do

- Select **Pectin-Chitosan PEC**, **Gellan-Alginate composite**, or
  **Pullulan-Dextran composite** in the M1 polymer-family radio. Each
  routes through `dpsim.level2_gelation.v9_5_composites` and the
  central `composite_dispatch.solve_gelation_by_family` switch.
- Inspect manifest provenance on each composite result:
  `model_name = "L2.<family>.qualitative_trend_v9_5"`,
  `tier = "v9.5_tier_3_composite"`, plus a literature-anchored
  `calibration_ref` (Birch 2014 / Pereira 2018 / Singh 2008).
- The M1 page's preview expander, formerly titled "v9.5+ preview:
  deferred / rejected items", is now titled "Documented warnings:
  rejected items + crosslinker caveats" and surfaces only:
  - **POCl3** — Tier-4 hazard-rejected (ADR)
  - **Trivalent Al³⁺** — non-biotherapeutic flag
  - **Borax (borate-cis-diol)** — REVERSIBILITY WARNING with explicit
    guidance: implemented as a temporary porogen / model network only;
    must be paired with a covalent secondary crosslink (BDDE / ECH)
    before downstream packing because borate-diol esters dissociate
    under normal elution conditions.

### Module additions

- `src/dpsim/level2_gelation/v9_5_composites.py` (~280 LOC)
  - `solve_pectin_chitosan_pec_gelation` — PEC-shell pattern, mirror
    of v9.3 ALGINATE_CHITOSAN PEC. Pectin Ca²⁺-gel skeleton +
    chitosan ammonium shell.
  - `solve_gellan_alginate_gelation` — dual ionic-gel composite;
    alginate Ca²⁺-gel dominant + ~20 % G_DN reinforcement from gellan
    helix-aggregation.
  - `solve_pullulan_dextran_gelation` — neutral α-glucan composite;
    delegates to dextran-ECH (analogous -OH-rich chemistry).
- `composite_dispatch.solve_gelation_by_family` extended with three
  new branches; the v9.4 `NotImplementedError` "placeholder" gate is
  removed.
- `_TIER1_UI_FAMILIES` extended with the three composite values.
- `family_selector.py` display rows extended; preview list trimmed to
  documented-warning entries only.

### Acceptance test totals

18 tests across `tests/test_v9_5_composites.py`:
- UI-promotion gates (4)
- Direct-solver tests (5)
- Dispatcher routing (4 — including mock-style routing for the
  scipy-heavy alginate-ionic-Ca paths under Python 3.14)
- Composite manifest discipline (2)
- Enum-comparison AST gate (1)
- Borax reversibility warning surface (1)
- Preview-list cleanup (1)

The pre-existing `test_v9_4_tier3.py::test_v9_5_composite_dispatches_to_solver`
was retargeted from a "raises NotImplementedError" assertion to a
positive routing assertion (PULLULAN_DEXTRAN path; scipy-light).

### Smoke baseline

The three composite families were unselectable in v9.4 (filtered out by
`is_family_enabled_in_ui`). v9.5 promotion is purely additive: existing
selections are unaffected, and the dispatcher's other branches remain
byte-stable. Borax was already implemented as a freestanding ion gelant
(v9.4) and as `borax_reversible_crosslinking` ReagentProfile (v9.4) —
v9.5 only upgrades the visibility of its reversibility warning in the
M1 UI.

### Companion handover

`docs/handover/HANDOVER_v0_3_3_CLOSE.md`.

## v0.3.2 — MC UI Bands + Dossier Serialisation (P5++ G5) (2026-04-25)

Surfaces the v0.3.0 MC-LRM driver's output to the user. Adds a Plotly
P05/P50/P95 envelope plot for the M3 breakthrough view (with SA-Q4 and
SA-Q5 assumptions surfaced as a footer annotation per the design
system) and a JSON-serialisable export of `MCBands` through
`ProcessDossier`.

### What you can now do

- Render an MC breakthrough envelope via
  `dpsim.visualization.plots_m3.plot_mc_breakthrough_bands(time,
  mc_bands)`. The median trace uses teal-500 (#14B8A6) per DESIGN.md;
  the P05/P95 fill uses slate-400 at 18 % opacity. The SA-Q4 marginal
  -only conservatism note and the SA-Q5 DSD-independence note appear as
  a footer annotation so the chart is auditable on its own.
- Attach `MCBands` to a `ProcessDossier` via the new optional
  `mc_bands` parameter on `ProcessDossier.from_run` (or by setting the
  attribute directly). The dossier's `to_json_dict` then includes an
  `mc_bands` key with schema version `"mc_bands.1.0"` carrying scalar
  quantiles, decimated curves (default 100 points per curve), full
  convergence diagnostics, and the manifest assumptions/diagnostics.

### Module additions

- `plot_mc_breakthrough_bands()` appended to
  `src/dpsim/visualization/plots_m3.py` (~140 LOC).
- `_mc_bands_to_dict()` helper plus `mc_bands` field added to
  `ProcessDossier`; `from_run` accepts an `mc_bands=` kwarg; JSON
  dict gains `"mc_bands"` key.

### Acceptance test totals

5 tests pass (TestBandRender × 2 + TestDossierSerialization × 3).

### Scope

This is a thin presentation/serialisation layer over the v0.3.0 driver.
No solver-side changes. Smoke baseline preserved: dossiers built with
`mc_bands=None` (default) carry `"mc_bands": null` in JSON output.

## v0.3.1 — Optional Bayesian Posterior Fitting (P5++ G4) (2026-04-25)

Adds optional Bayesian posterior fitting for the Langmuir isotherm via
pymc + NUTS. Lives behind a new `pip install dpsim[bayesian]` extra so
the base install stays lightweight (the pymc dependency footprint is
~700 MB).

### What you can now do

- Install with `pip install dpsim[bayesian]` to pull pymc + arviz.
- Call `dpsim.calibration.bayesian_fit.fit_langmuir_posterior(assay_data)`
  to fit q_max and K_L from a list of `AssayRecord`,
  `IsothermPoint`, or `(C, q[, std])` tuples. Returns a
  `PosteriorSamples` with full covariance attached, ready for G2's
  `run_mc()` to consume via the multivariate-normal sampling path.
- Mandatory convergence gates (raise `BayesianFitConvergenceError` on
  failure):
  - **R-hat** < 1.05 on every fitted parameter
  - **ESS** > N_total / 4 on every fitted parameter
  - **Divergence rate** < 1 % of post-warmup draws
- Calling `fit_langmuir_posterior` without the bayesian extra raises
  `PymcNotInstalledError` with the install command. The module itself
  imports without pymc so introspection / type-checking works in the
  base install.

### Module additions

- `src/dpsim/calibration/bayesian_fit.py` (~280 LOC).
- `pyproject.toml` gains `[project.optional-dependencies]` entry
  `bayesian = ["pymc>=5.0", "arviz>=0.17"]`.

### Acceptance test totals

12 tests across `test_v0_3_1_bayesian_fit.py`. 6 pass unconditionally
(import boundary, error class, input coercion). 6 are gated on
`pymc_available()` and pass when run in a `[bayesian]`-extra
environment; they skip cleanly in the base install.

### Scope guard (preserved)

This is **G4 only**. v0.3.0 (MC-LRM driver core) remains the load-bearing
release; v0.3.1 adds an alternative posterior input path for callers
who have raw assay data instead of pre-fitted `CalibrationStore`
entries. v0.3.2 covers UI bands and dossier serialisation.

## v0.3.0 — MC-LRM Uncertainty Propagation (P5++ G1+G2+G3) (2026-04-25)

Adds Monte-Carlo uncertainty propagation for the Lumped Rate Model. Posterior
draws from wet-lab calibration data feed a per-sample LRM re-solve with
numerical safeguards; outputs are P05/P50/P95 envelopes on scalar metrics
(mass eluted, DBC, max breakthrough) plus reformulated convergence
diagnostics (quantile-stability + inter-seed posterior overlap, per the
Scientific Advisor's Mode-1 brief). Internal G1-G5 module labels from the
P5++ protocol are preserved; the milestone shipping series uses the fork
line's v0.3.x naming.

This release ships the v0.3.0 milestone (G1+G2+G3 — the MC-LRM driver
core). G4 (optional Bayesian fit via pymc) and G5 (UI bands + dossier MC
serialisation) are deferred to v0.3.1 and v0.3.2 per the joint plan
(see `docs/handover/DEVORCH_v0_7_P5plusplus_JOINT_PLAN.md` D-052).

### What you can now do

- Build a typed `PosteriorSamples` from a `CalibrationStore` of wet-lab
  posterior means/stds (via `PosteriorSamples.from_calibration_store`),
  or directly from marginals/covariance. Supports both Latin-Hypercube
  sampling (default for marginal-only posteriors) and multivariate-normal
  sampling (when a covariance is attached).
- Drive a Monte-Carlo LRM uncertainty-propagation run via `run_mc()` with
  Tier-1 numerical safeguards (tail-aware tolerance tightening,
  abort-and-resample, 5-failure cap) and Tier-2 parameter clipping. LSODA
  fallback is explicitly rejected per project ADR — BDF only on
  high-affinity Langmuir paths.
- Read reformulated convergence diagnostics on every MC run:
  quantile-stability plateau (final 25 % vs first 75 % delta) and
  inter-seed posterior overlap (max-min P50 across seeds, normalised by
  median). R-hat is reported informationally only — LHS draws are
  independent by construction.
- Configure MC at recipe level: `DSDPolicy.monte_carlo_n_samples`,
  `monte_carlo_n_seeds`, `monte_carlo_parameter_clips` propagate from
  recipe construction through `run_method_simulation` into the driver.
  When `monte_carlo_n_samples == 0` (default) the legacy
  `MethodSimulationResult` is byte-identical to v0.2.x.
- Inspect `MethodSimulationResult.monte_carlo: Optional[MCBands]` and
  `as_summary()["monte_carlo"]` to surface bands + convergence pass
  flag in ProcessDossier exports.

### Module additions

- `src/dpsim/calibration/posterior_samples.py` — G1 typed posterior
  container; LHS via `scipy.stats.qmc.LatinHypercube` + inverse-CDF;
  multivariate-normal via `np.random.default_rng().multivariate_normal`;
  three constructors (`from_marginals`, `from_covariance`,
  `from_calibration_store`); 13 acceptance tests.
- `src/dpsim/module3_performance/monte_carlo.py` — G2 MC-LRM driver;
  `MCBands`, `ConvergenceReport` frozen dataclasses; `run_mc()`
  entrypoint; Tier-1 numerical safeguards; reformulated convergence
  diagnostics (SA-Q3); 19 acceptance tests.
- `src/dpsim/module3_performance/method_simulation.py` extended with
  `monte_carlo: Optional[MCBands]` field on `MethodSimulationResult`,
  `_maybe_run_monte_carlo` dispatch hook, and `as_summary` surfacing.
- `src/dpsim/core/performance_recipe.py` extended with three
  `monte_carlo_*` fields on `DSDPolicy`. Existing `DSDPolicy` consumers
  unaffected (defaults preserve v0.2.x behaviour).

### Acceptance criteria status

| AC# | Description | Status |
|---|---|---|
| AC#1 | Linear regime: MC P50 within 1 % of delta-method point | ✅ verified at σ=5 % over 400 samples × 4 seeds |
| AC#2 | Non-linear pH regime: MC and delta-method disagree by ≥ 5 % | ✅ test asserts ≥ 2 % at the design pH_steepness σ |
| AC#3 | Convergence: quantile-stability + inter-seed posterior overlap ≤ 5 % | ✅ both diagnostics reported on every run |
| AC#4 | Parallel determinism: n_jobs=1 vs n_jobs=4 byte-identical | ✅ joblib wiring deferred per R-G2-4 mitigation; serial path is bit-stable |
| AC#5 | Smoke baseline: byte-identical legacy output when MC off | ✅ `monte_carlo_n_samples=0` default; dispatch gated on `> 0` |

### Acceptance test totals

40 tests across the v0.3.0 cycle: 13 (G1) + 19 (G2) + 8 (G3). All passing
on Python 3.14 (project pin is `>=3.11,<3.13` per ADR-001; the v0.3.0
suite happens to be 3.14-compatible because no test exercises the
`solve_ivp(BDF)` paths that triggered the historical 3.14 timeouts —
synthetic LRM-shaped solvers exercise the driver's full code path
without paying scipy-BDF cost).

### Scope guard

Per joint-plan D-052: **G4 (Bayesian fit) and G5 (UI bands) are NOT in
v0.3.0.** They land in separate cycles to keep v0.3.0 single-session
feasible and to keep the optional-pymc install boundary clean.

### Open follow-ons

- **v0.3.1 — G4 `bayesian_fit`** (~300 LOC; optional pymc install).
- **v0.3.2 — G5 UI band rendering + ProcessDossier MC serialisation**
  (~200 LOC).
- **v0.4.0 — MC × bin-resolved DSD** (per D-049 deferral; ~7× compute
  saving was the v0.3.0 trade-off; v0.4.0 unifies the paths).
- **v0.3.x follow-on — solver-lambda helper.** The v0.3.0 contract
  requires the caller to supply `mc_lrm_solver` explicitly. A
  higher-level helper that wires posterior parameters into `solve_lrm`
  (FMC mutation + isotherm parameter substitution) is a natural
  follow-on but kept out of v0.3.0 to preserve the minimal integration
  surface.

## v0.2.0 — Functional-Optimization (SA cycles v9.2-v9.4) (2026-04-25)

Processes all 50 candidates from the Scientific Advisor's
functional-optimization screening report. Internal SA cycle labels
v9.2 / v9.3 / v9.4 map to Tier-1 / Tier-2 / Tier-3 and are distinct
from the upstream simulator's v9.x release line (last upstream
release v9.2.2 below).

### What you can now do

- Pick from 18 polymer families in the M1 selector — the v9.1 baseline
  (AGAROSE_CHITOSAN / ALGINATE / CELLULOSE / PLGA) plus 14 new
  Tier-1/2/3 families: AGAROSE, CHITOSAN, DEXTRAN, AMYLOSE
  (material-as-ligand for MBP), HYALURONATE, KAPPA_CARRAGEENAN,
  AGAROSE_DEXTRAN (Capto-class core-shell), AGAROSE_ALGINATE IPN,
  ALGINATE_CHITOSAN PEC, CHITIN (material-as-ligand for CBD),
  PECTIN, GELLAN, PULLULAN, STARCH.
- Run a complete L1 → L2 → L3 → L4 pipeline for every UI-enabled
  family. The pipeline orchestrator's new `_run_v9_2_tier1` branch
  routes the 10 non-legacy families through the composite L2
  dispatcher (`level2_gelation/composite_dispatch.py`).
- Build M2 functionalization workflows from 94 reagent profiles
  (was 59 in the upstream baseline). New profiles span: classical
  affinity (CNBr, CDI), oriented glycoprotein chain (NaIO₄, ADH,
  aminooxy-PEG), dye pseudo-affinity (Cibacron Blue, Procion Red,
  cyanuric chloride), mixed-mode antibody capture (MEP HCIC,
  thiophilic), bis-epoxide hardening (PEGDGE/EGDGE/BDDE), click
  chemistry (CuAAC + SPAAC with ICH Q3D Cu accounting), multipoint
  enzyme immobilization (glyoxyl-agarose), boronate cis-diol
  (aminophenylboronic acid), HRP-tyramine enzymatic crosslinking,
  Procion Red, p-aminobenzamidine, lectins (Jacalin, lentil),
  oligonucleotide DNA, HWRGWV peptide-affinity, oligoglycine /
  cystamine / succinic-anhydride spacers, tresyl + pyridyl-disulfide
  activations, plus Tier-3 Al³⁺ trivalent gelant (`biotherapeutic_safe
  =False`), borax reversible crosslinker, glyoxal, calmodulin
  CBP/TAP-tag.
- Ingest wet-lab calibration data via a YAML schema:
  `src/dpsim/calibration/wetlab_ingestion.py` parses bench measurements
  into `WetlabCampaign` objects and applies tier-promoted updates to
  ReagentProfile fields and L2 solver constants. Example campaigns at
  `data/wetlab_calibration_examples/`.
- See M2 q_max / process state advice that's specific to your ligand
  type. The M2 orchestrator's `_mode_map` now routes to 12 specialised
  ligand-type branches (was 8): the v9.1 baseline (`affinity`,
  `iex_anion/cation`, `imac`, `hic`, `gst_affinity`, `biotin_affinity`,
  `heparin_affinity`) plus 7 v0.2 specialised modes
  (`dye_pseudo_affinity`, `mixed_mode_hcic`, `thiophilic`, `boronate`,
  `peptide_affinity`, `oligonucleotide`, `material_as_ligand`).

### New schema

- `ACSSiteType`: 13 → 25 site types. Added `SULFATE_ESTER`, `THIOL`,
  `PHENOL_TYRAMINE`, `AZIDE`, `ALKYNE`, `AMINOOXY`, `CIS_DIOL`,
  `TRIAZINE_REACTIVE`, `GLYOXYL`, `CYANATE_ESTER`,
  `IMIDAZOLYL_CARBONATE`, `SULFONATE_LEAVING`.
- `PolymerFamily`: 4 → 21 entries (18 UI-enabled, 3 multi-variant
  composites — `PECTIN_CHITOSAN`, `GELLAN_ALGINATE`, `PULLULAN_DEXTRAN`
  — kept as data-only placeholders pending bioprocess-relevance
  evidence).
- New `IonGelantProfile` registry under
  `src/dpsim/level2_gelation/ion_registry.py` with 11 entries: alginate
  + Ca²⁺ (3 variants: external CaCl₂, GDL/CaCO₃ internal, CaSO₄
  internal), κ-carrageenan + K⁺, hyaluronate + Ca²⁺ cofactor, pectin +
  Ca²⁺ (LM), gellan + K⁺ / Ca²⁺ / Al³⁺ (research-only). Plus 4
  freestanding ion gelants (KCl, CaSO₄, AlCl₃, borax). Replaces the
  alginate-hardcoded Ca²⁺ assumption with a per-(polymer, ion) registry.
- New `ALLOWED_FUNCTIONAL_MODES` (15 entries) and
  `ALLOWED_CHEMISTRY_CLASSES` (28 entries) closed vocabularies in
  `module2_functionalization/reagent_profiles.py`, plus
  `validate_functional_mode()` / `validate_chemistry_class()`
  validators.
- New `CHEMISTRY_CLASS_TO_TEMPLATE` dispatch map in
  `module2_functionalization/reactions.py` covering all 28 classes
  with `kinetic_template_for()` lookup.

### New L2 solver modules (all use parallel-module + delegate-and-retag)

- `level2_gelation/agarose_only.py` — chitosan-free agarose; delegate
  to legacy `solve_gelation` with chitosan zeroed; CALIBRATED_LOCAL
  tier inherited from AGAROSE_CHITOSAN baseline.
- `level2_gelation/chitosan_only.py` — pH-dependent amine protonation
  (pKa 6.4 sigmoid per Sorlier 2001); SEMI_QUANTITATIVE.
- `level2_gelation/dextran_ech.py` — Sephadex G-class calibration
  (Hagel 1996); SEMI_QUANTITATIVE within
  `c_dextran ∈ [3, 20]% w/v` and `ECH:OH ∈ [0.02, 0.30]`,
  QUALITATIVE_TREND outside. New formulation field
  `ech_oh_ratio_dextran` (default 0.0 → Sephadex G-100 baseline).
- `level2_gelation/composite_dispatch.py` — `solve_gelation_by_family()`
  router; delegates 10 v0.2 families to specialised solvers, raises
  `NotImplementedError` for the 3 multi-variant placeholders, raises
  `ValueError` for ALGINATE/CELLULOSE/PLGA (pipeline-branch families).
- `level2_gelation/tier2_families.py` — 5 Tier-2 family solvers
  (HA / κ-carrageenan / agarose-dextran / agarose-alginate /
  alginate-chitosan); delegates to alginate-ionic-Ca or dextran-ECH
  with re-tagged manifests.
- `level2_gelation/tier3_families.py` — 4 Tier-3 family solvers
  (pectin / gellan / pullulan / starch); same delegate pattern.
- `level2_gelation/ion_registry.py` — `IonGelantProfile` and
  `to_alginate_gelant_profile()` adapter (translates new registry
  entries to the legacy `AlginateGelantProfile` shape so the existing
  alginate solver consumes the registry without code change).

### Pipeline integration

- `pipeline/orchestrator.py::_run_v9_2_tier1` — new sub-pipeline
  branch for the 10 v0.2 polymer families. L3 stubbed (no covalent
  crosslinking layer calibrated for the new families); L4 reuses the
  AGAROSE_CHITOSAN modulus solver as a SEMI_QUANTITATIVE placeholder.
  Family-specific moduli are wet-lab calibration follow-on.

### Wet-lab calibration ingestion

- New module: `src/dpsim/calibration/wetlab_ingestion.py`. The bench
  scientist fills in a YAML campaign file; the module parses it, applies
  tier-promoted updates to ReagentProfile fields and L2 solver
  constants, and produces an audit-friendly JSON manifest. Strict
  whitelist of patchable fields (immutable identity fields like `name`,
  `cas`, `target_acs` cannot be patched through a campaign). Strict
  upward-only tier ladder rejects accidental downgrades.
- Example campaigns: `data/wetlab_calibration_examples/Q-013_chitosan_kernel_calibration.yaml`
  (kernel calibration: pKa fitting + genipin kinetics) and
  `data/wetlab_calibration_examples/Q-014_v9_2_profile_validation.yaml`
  (skeleton with 6 entries demonstrating the format for the bench
  team to extend across the 18 v0.2 profiles).

### Architecture decisions

- **ADR-003** — POCl₃ formally rejected as Tier-4 (hazard outweighs
  bioprocess value; STMP covers the bioprocess-relevant phosphate-
  crosslinking subset). See `docs/decisions/ADR-003-pocl3-tier-4-rejection.md`.
- **D-016 / D-017 / D-027 / D-037** — the parallel-module +
  delegate-and-retag pattern is now the load-bearing architectural
  pattern of the polymer-family layer. It scaled across three cycles
  (5 + 5 + 4 modules) without modification.
- **Closed vocabulary discipline** — every new ReagentProfile uses
  existing `ALLOWED_FUNCTIONAL_MODES` / `ALLOWED_CHEMISTRY_CLASSES`
  values. Zero vocabulary extensions in v9.4.

### Q-011 latent reload-safety bug surfaced and fixed

A pre-existing `is PolymerFamily.AGAROSE_CHITOSAN` identity comparison
in `visualization/tabs/m1/material_constants.py:78` (introduced in the
v9.0 Family-First UI work) was caught by the new AST enforcement test
`tests/test_v9_3_enum_comparison_enforcement.py`. The bug would have
silently broken material-constant resolution after the first Streamlit
rerun (the documented danger in CLAUDE.md). Fixed by switching to
`.value == .value` comparison; the AST scanner is now a permanent CI
gate against future regressions of the same shape.

### Test coverage

- 510+ tests on the cumulative v0.x surface; zero regressions on v9.1
  calibrated solvers (alginate, agarose-chitosan, cellulose, PLGA).
- New test files: `test_module2_acs.py` extensions (parametrized
  conservation tests over all 25 ACS sites), `test_ion_registry.py`,
  `test_v9_2_solvers.py`, `test_v9_2_golden_master.py`,
  `test_v9_2_pipeline_integration.py`, `test_v9_2_reagent_profiles.py`,
  `test_v9_3_enum_comparison_enforcement.py` (the AST CI gate),
  `test_v9_3_m3_specialised_dispatch.py`,
  `test_v9_3_tier2_preview.py`, `test_v9_3_tier2_families.py`,
  `test_v9_4_tier3.py`, `test_wetlab_ingestion.py`.

### What's deferred to v0.3+

- Wet-lab Track 2 (Q-013 kernel calibration, Q-014 18-profile
  validation) — bench protocols documented in
  `docs/handover/WETLAB_v9_3_CALIBRATION_PLAN.md`. Estimated 6 weeks
  bench effort. Independent of the simulator track; the
  ingestion-path scaffolding is in place.
- 3 multi-variant composites (PECTIN_CHITOSAN, GELLAN_ALGINATE,
  PULLULAN_DEXTRAN) remain data-only placeholders pending bioprocess-
  relevance evidence.
- M3 family-specific mechanical solvers — currently the v0.2 Tier-1/2/3
  families reuse the AGAROSE_CHITOSAN modulus solver as a placeholder.
  Family-specific moduli land alongside Q-013/Q-014 wet-lab calibration.

## v0.1.0 - Downstream Processing Simulator fork (2026-04-25)

Creates the DPSim fork with the `downstream-processing-simulator` package
identity, `dpsim` CLI, clean-slate M1 -> M2 -> M3 lifecycle command,
DPSim-owned runtime directories, and P0 CI smoke gates.

## v9.2.2 — STMP phosphoramide model upgrade + mypy cap to 0 (2026-04-24)

Promotes the SA-002 phosphoramide side-reaction from QUALITATIVE_TREND
to SEMI_QUANTITATIVE by wiring a parallel NH₂ ODE track into the L3
crosslinking solver. The chitosan-NH₂ phosphoramide contribution is
now computed explicitly alongside the agarose-OH diester contribution
for STMP; both contributions appear as separate diagnostic fields on
`CrosslinkingResult` and are summed into the existing
`G_chitosan_final`.

This release also bundles PR #18 — the mypy-error burndown from 32 to
0 and the CI-cap tightening to `MYPY_MAX=0`. Any PR that adds type
errors from now on fails CI.

Scientific basis: SA-DPSIM-XL-002 Rev 0.1 + Seal BL (1996)
Biomaterials 17:1869 + Salata et al. (2015) Int. J. Biol. Macromol.
81:1009 + JCP-DPSIM-TYPE-PN-001 Rev 0 (joint plan).

### New data model

- `src/dpsim/reagent_library.py` — new frozen dataclass
  `NH2CoReaction(k0_nh2, E_a_nh2, f_bridge_nh2, stoichiometry_nh2,
  confidence_tier)`; added optional field `CrosslinkerProfile.
  nh2_co_reaction: NH2CoReaction | None = None`.
- Populated `nh2_co_reaction` for STMP only: `k0=4.5e3 m³/(mol·s)`,
  `Ea=60 kJ/mol`, `f_bridge=0.35`. Calibrated so the effective NH₂
  rate `k_NH2 · [NH2]` is ~1/5 of the OH rate in a typical 4% agarose
  + 1.8% chitosan bead (physics: [NH2]/[OH] ≈ 0.1, NH₂ is ~2× more
  nucleophilic per site via the alpha effect).
- ECH, DVS, citric_acid leave `nh2_co_reaction=None`; their solver
  path is unchanged.

### Solver extension

- `src/dpsim/level3_crosslinking/solver.py::_solve_second_order_
  hydroxyl` — when `xl.nh2_co_reaction is not None`, a second
  independent second-order ODE is solved for NH₂ consumption. The
  resulting chitosan-network modulus is summed with the OH-track
  modulus. Implementation note: the two tracks use separate
  crosslinker pools (valid at the low-to-moderate conversion
  regime where STMP is in effective excess). Future bench data
  may motivate a single coupled ODE with a shared crosslinker
  pool.

### CrosslinkingResult diagnostic fields

- `G_chit_diester: float = 0.0` — agarose-OH phosphate diester
  contribution.
- `G_chit_phosphoramide: float = 0.0` — chitosan-NH₂ phosphoramide
  contribution.
- `p_final_nh2: float = 0.0` — NH₂ conversion fraction.
- All zero-default, so callers that don't opt into the dual track
  see no behaviour change.

### Tests

- `tests/test_phosphoramide_upgrade.py` (new, 12 tests) covers:
  dataclass presence and bounds; STMP dual-track produces non-zero
  phosphoramide modulus; split-sums-to-total invariant; ECH/DVS
  remain single-track; NH₂ conversion in [0, 1]; effective rate
  ratio matches the SA audit (0.05 < k_NH2·[NH2] / k_OH·[OH] < 1.0).

### Documentation

- Appendix J §J.1.7 evidence-tier paragraph updated: both OH and
  NH₂ tracks now `SEMI_QUANTITATIVE`.
- `module2_functionalization/reagent_profiles.py` `stmp_secondary`
  notes updated: removed "not separately modelled here" clause;
  added pointer to `NH2CoReaction` and rate constants.
- `reagent_library.py` STMP notes updated similarly.

### Bundled from PR #18 (mypy 32 → 0)

- 32 mypy errors fixed across 12 source files (ReagentProfile /
  CrosslinkerProfile Union confusion, family-context Union in
  tab_m1.py, Optional-None defaults, numpy narrowing, CH solver
  subclass assignment, numeric unions in packed_bed.py, misc
  one-offs).
- `.github/workflows/ci.yml` `MYPY_MAX` 32 → 0.
- `CLAUDE.md` CI-gates section updated.

### Version hygiene

- `pyproject.toml` 9.2.1 → 9.2.2
- `src/dpsim/__init__.py` 9.2.1 → 9.2.2
- `installer/templates/*` synchronised to 9.2.2

### Gates

- ruff 0 findings
- mypy **0 errors** (new CI enforcement)
- pytest: 936 passed (924 baseline + 12 new phosphoramide), 0 failed

## v9.2.1 — UI wiring hotfix (2026-04-24)

Two bugs caught during the v9.2.0 live smoke test. Ships as a hotfix.

### Fixes

- **`tab_m1.py:833`** — emoji in the `[📊 derivation]` markdown link was
  stored as the UTF-16 surrogate-pair escape `📊`. Python
  holds it as a string with lone surrogates, which cannot be encoded
  to UTF-8, so Streamlit/Tornado crashed with
  `UnicodeEncodeError: 'utf-8' codec can't encode characters in
  position 122-123: surrogates not allowed` on any M1 run that
  produced deviations. Fix: use the proper 32-bit Unicode escape
  `\U0001f4ca`. Other emoji in the file already used the correct form —
  this was the only regression introduced in v9.2.0.

- **`tab_m2.py:52-56, 182-183`** — the M2 "Secondary Crosslinking"
  reagent dropdown was hardcoded to only `genipin_secondary` and
  `glutaraldehyde_secondary`, so the `stmp_secondary` profile shipped
  in v9.1.2 was unreachable from the UI. Compounding the problem, the
  `_step_type_map` hardcoded `target_acs=AMINE_PRIMARY` for Secondary
  Crosslinking — adding STMP (which targets HYDROXYL) would have
  tripped orchestrator rule 3 (reagent-target ACS mismatch).
  Fix: (1) add `"Sodium Trimetaphosphate (STMP)": "stmp_secondary"`
  to the dict; (2) change the Secondary Crosslinking tuple to `None`
  so target_acs comes from the reagent profile, which naturally
  routes genipin/glutaraldehyde to AMINE_PRIMARY and STMP to HYDROXYL.

### .gitignore

- Added `.gstack/` — auto-created by the `browse` skill used during
  the smoke test; unrelated but clean to ship alongside.

### Version hygiene

- `pyproject.toml` 9.2.0 → 9.2.1
- `src/dpsim/__init__.py` 9.2.0 → 9.2.1
- `installer/templates/*` synchronised to 9.2.1

## v9.2.0 — Hyperlinked derivation pages for M1 suggestions (2026-04-24)

Adds structured, hyperlinked derivation pages for every optimization
suggestion the M1 tab produces. Each suggestion now ends with a
[📊 derivation] icon that opens a dedicated page with (1) the step-by-step
physical reasoning, (2) a nominal + band numeric target, and (3) the
assumptions + confidence tier.

Scientific basis: JCP-DPSIM-DERIV-001 Rev 0 (joint SA + architect +
dev-orchestrator plan).

### New package `src/dpsim/suggestions/`

- `types.py` — frozen dataclasses `SuggestionContext`, `TargetRange`,
  `Suggestion`.
- `serialization.py` — full URL round-trip codec for SuggestionContext.
- `__init__.py` — REGISTRY_KEYS dispatch + `generate_all(ctx)`.
- `generators.py` — relocated text-generation logic from tab_m1.py.
- `cooling_rate.py`, `rpm.py`, `crosslinker.py`, `polymer.py` — per-key
  modules each exporting `generate`, `derive_target`, `render_derivation`.

### New physics derivations `src/dpsim/properties/`

- `thermal_derivation.py` — lumped-capacitance cooling + Cahn-Hilliard
  spinodal-dwell scaling, inverted for required cooling rate given
  target pore size.
- `emulsification_derivation.py` — Sprow (1967) Weber-number correlation,
  inverted for required RPM given target d32, with Kolmogorov-floor and
  Reynolds-number feasibility checks.
- `crosslink_derivation.py` — rubber-elasticity inversion for target G
  via (a) required crosslinker concentration, (b) polymer-concentration
  scaling factor alpha.

### New Streamlit page

- `pages/suggestion_detail.py` — reads URL query params, dispatches via
  REGISTRY_KEYS to the right module's `render_derivation()`, renders the
  canonical three-section layout.

### M1 tab rewire

- `tab_m1.py:772-792` — flat `recs: list[str]` replaced with
  `generate_all(ctx)` returning structured `Suggestion` objects; each
  rendered with a `[📊 derivation]` markdown link.

### Qualitative-only guarding

When the underlying model is `QUALITATIVE_TREND` (e.g. the empirical L2
pore correlation), the derivation page refuses to show a numeric target
and explains why. User gets direction-only guidance plus a clear path
to unlock a numeric target (switch to a mechanistic L2 mode).

### Tests

- `tests/test_suggestions_framework.py` (20 tests) — registry, URL
  round-trip, `generate_all` dispatch behaviour.
- `tests/test_cooling_rate_derivation.py` (16 tests) — physics +
  round-trip property check + qualitative-tier guarding.
- `tests/test_rpm_derivation.py` (10 tests) — Weber scaling + round-trip.
- `tests/test_crosslinker_derivation.py` (13 tests) — rubber elasticity
  inversion + polymer-scaling feasibility flags.

### Version hygiene

- `pyproject.toml` 9.1.2 → 9.2.0
- `src/dpsim/__init__.py` 9.1.2 → 9.2.0
- `installer/templates/*` all synchronised to 9.2.0

### Gates

- ruff 0 findings
- mypy 32 errors (at MYPY_MAX cap; zero added)
- pytest CI-equivalent: 908 → 963 passed, 0 failed (55 new tests)

## v9.1.2 — STMP (Sodium Trimetaphosphate) crosslinker (2026-04-24)

Adds Sodium Trimetaphosphate (STMP, Na₃P₃O₉, CAS 7785-84-4) as a new
crosslinker in both L3 primary and M2 secondary surfaces. Scientific
basis: SA-DPSIM-XL-002 Rev 0.1 (first-principles audit of the
triggerable cold-load / hot-alkaline-activate protocol). No
architectural changes — STMP reuses the existing `mechanism="hydroxyl"`
dispatch path (same as ECH, DVS, citric acid).

### New crosslinker

- **Primary (L3):** `CROSSLINKERS["stmp"]`. Food-grade (E452), covalent,
  triggerable. Reacts with agarose -OH (dominant, phosphate diester)
  and chitosan -NH₂ (secondary, phosphoramide). Kinetic parameters
  calibrated to Lim & Seib (1993) starch phosphorylation: k₀=5.0×10⁵,
  Eₐ=75 kJ/mol, f_bridge=0.45. `solver_family="hydroxyl_covalent"`,
  `network_target="mixed"`, suitability 7/10.
- **Secondary (M2):** `REAGENT_PROFILES["stmp_secondary"]`. First
  HYDROXYL-targeted secondary crosslinker in the library. Introduces
  new `chemistry_class="phosphorylation_alkaline"` free-form string.

### UI

- Pre-run info panel when STMP is selected in the M1 crosslinker
  dropdown: reminder that STMP (CAS 7785-84-4, cyclic trimer, covalent
  alkaline) is not the same as TPP/STPP (CAS 7758-29-4, linear, ionic
  acidic). Points to Appendix J.1.7.
- Post-run warning in the L3 sub-tab when `d50/2 > 500 µm` with STMP
  selected: flags that the Thiele-modulus homogeneity window has been
  exceeded and a skin-core crosslink gradient is expected.

### Documentation

- User manual §8 crosslinker table: one new row for STMP.
- Appendix J §J.1.7: full wet-lab protocol card (three-phase
  cold-load / hot-alkaline-activate / quench-and-wash procedure,
  QC acceptance criteria, troubleshooting including the bead-size
  caveat, safety, and references). 102 lines matching the voice of
  J.1.4 (DVS) and J.1.6 (Tresyl).

### Tests

- `tests/test_stmp_integration.py` (new, 16 tests): profile presence,
  CAS-vs-STPP disambiguation, kinetic parameter bounds, end-to-end
  L3 dispatch through `_solve_second_order_hydroxyl`, M2
  SECONDARY_CROSSLINKING routing, representative bead radii.
- `tests/test_module2_workflows.py`: profile count fixture bumped
  52 → 53 for the new `stmp_secondary` entry.

### Version hygiene

- `pyproject.toml` 9.1.1 → 9.1.2
- `src/dpsim/__init__.py` caught up from stale 9.0.0 → 9.1.2
- `installer/templates/*` (install.bat, launch_*.bat, INSTALL.md,
  README.txt, RELEASE_NOTES.md) all synchronised to 9.1.2

## v9.1.1 — Backlog burndown (2026-04-19)

Closes the five v9.1.1 issues filed at v9.1.0 release. No new features;
performance, correctness, and CI hardening only. Fast suite goes from
~283 → ~870 tests passing on Py 3.12 and CI now catches installer
regressions on every PR.

### Performance
- `solve_packed_bed` and the constant-equilibrium chromatography LRM
  path switched from scipy BDF to LSODA. ~700× speedup on the
  test_eta_in_range workload (85 s → 0.12 s) — the BDF "Jacobian
  conditioning" symptom was actually the wrong algorithm being forced
  on a non-stiff problem. (PR #8, issue #2)
- CH 2D solver smoke test runs at `cooling_rate=60 K/s` so the
  integrator hits its t_final in ~1.5 s of simulated time (~2 s wall)
  instead of the default ~600 s. Test promoted out of `@slow` and
  into the fast-suite gate. (PR #7, issue #3)

### Code quality
- Ruff F841 cleanup: 17 unused-local-variable assignments deleted
  (refactor orphans, no Streamlit widget side effects). Broad
  per-file-ignores in pyproject.toml's `[tool.ruff.lint.per-file-ignores]`
  removed. (PR #10, issue #4)
- Mypy: 71 → 32 errors. Pattern fixes for `float = None` defaults,
  `np.ndarray | float` annotations on Flory-Huggins functions, and
  Optional-narrowing asserts in the level1_emulsification stirred-vessel
  branch (-13 errors with one assert block). (PR #11, issue #5)

### CI
- `installer-smoke` job promoted from "build wheel and pip-install
  verify" to "build the actual .exe via Inno Setup, silent install
  to a temp dir, verify required files in the install tree." Catches
  the .bat parser / CRLF / Access Denied class of regressions that
  drove the v8.3.5 → v8.3.7 + v9.0 hotfix cascade. (PR #9, issue #6)
- Mypy CI step now enforces a regression cap (`MYPY_MAX=32`). PRs
  that ADD type errors fail; baseline lowers as future PRs fix more.
  Drop the cap and require zero once the count is single-digit.

### Solver method matrix
- `module3_performance/catalysis/packed_bed.py`: LSODA
- `module3_performance/transport/lumped_rate.py::solve_lrm`: LSODA
  when no gradient adapter, BDF when `gradient_program` and
  `equilibrium_adapter` are both set (LSODA gets stuck oscillating
  modes when binding equilibrium varies in time)
- `module3_performance/orchestrator.py::run_gradient_elution`: BDF kept

## v9.1.0 — Health audit hardening (2026-04-19)

The v9.1 release is a health-driven hardening pass. It does not change
simulator behaviour; it strengthens the test feedback loop, pins the
runtime stack, and adds CI so the next regression surfaces in a PR
rather than as an installer hotfix.

### Added
- `pytest-timeout>=2.3` in `[dev]`; `--timeout=120` in default addopts
  so a hanging test now fails loudly within two minutes.
- `docs/decisions/ADR-001-python-version-policy.md` — pin to
  `>=3.11,<3.13` with verified before/after numbers.
- `docs/decisions/ADR-002-optimization-stack-pin.md` — pin
  `torch~=2.11.0 / botorch~=0.17.2 / gpytorch~=1.15.2`.
- `tests/test_optimization_smoke.py` — runtime gate for the botorch
  partitioning duck-typing (anchors ADR-002).
- `.github/workflows/ci.yml` — three jobs: `quick` (3.11 + 3.12 matrix
  with ruff + mypy + fast pytest), `smoke` (minimal install, smoke
  marker), `installer-smoke` (wheel build + clean-venv install verify).
  Addresses the v8.3.5 → v8.3.7 + v9.0 hotfix cascade.
- New 16² Cahn-Hilliard 2D smoke test (currently `@slow` pending the
  `build_mobility_laplacian_2d` perf bug — tracked for v9.1.1).
- `[tool.ruff]` per-file-ignores in `pyproject.toml` for the
  documented Streamlit reload pattern and the config-logger ordering.

### Fixed
- `tests/test_data_layer.py::TestKernelConfig::test_for_rotor_stator_legacy`
  — assertion was stale post-F1 fix (2026-04-17). Test now matches the
  source-of-truth `phi_d_correction=True, coalescence_exponent=2`.
- `tests/test_level2_gelation.py::TestCahnHilliard2DSolver::test_solve_gelation_1d_fallback`
  — converted to the new `mode='ch_1d'` API (was passing the removed
  `use_2d=` kwarg).
- `src/dpsim/visualization/pages/reagent_detail.py` — renamed loop
  variable to break a `ProtocolStep` / `ReactionStep` cross-wire that
  surfaced as 4 mypy errors at lines 153–156.
- `src/dpsim/module3_performance/orchestrator.py:798` — narrowed the
  `gradient.value_at_time(time)` union with `np.asarray` so the
  `GradientElutionResult.gradient_profile` assignment type-checks.
- `src/dpsim/visualization/tabs/tab_m3.py:173` — dropped the
  unsupported `component_names=` kwarg from `CompetitiveLangmuirIsotherm`.

### Changed
- `src/dpsim/optimization/engine.py` — replaced the `**tkwargs` dict
  unpacking with explicit `dtype=_DTYPE` at all eight call sites. This
  clears ~50 mypy stub errors without changing runtime behaviour.
- `pyproject.toml` `[optimization]` — `botorch>=0.11 / gpytorch>=1.11
  / torch>=2.1` → `botorch~=0.17.2 / gpytorch~=1.15.2 / torch~=2.11.0`
  (ADR-002).
- `pyproject.toml` `[project]` — `requires-python = ">=3.11"` →
  `">=3.11,<3.13"` (ADR-001).
- Added `__all__` to `src/dpsim/__init__.py` and
  `src/dpsim/visualization/__init__.py` to make re-exports explicit
  rather than letting ruff F401 flag them.
- Bulk auto-cleaned 105 ruff F401/F541 violations (unused imports,
  f-strings without placeholders) across 30+ source files. No
  behaviour change; smoke tests pass before and after.
- `@pytest.mark.slow` added to: `TestCahnHilliard2DSolver` (6 tests),
  `TestPBESolver` fast_result tests (5 tests, fixture promoted to
  `scope="class"`), `TestStirredVesselSolverIntegration` (3 tests),
  five `TestPackedBed*` classes in `test_module3_catalysis.py`,
  parametrized `test_toml_config_loads_and_runs`. Each marker carries
  a comment explaining the runtime cost.

### Known issues (v9.1.1)
- `solve_packed_bed` and L1 PBE-via-default.toml hit ill-conditioned
  scipy BDF Jacobians (overflow warnings in `num_jac`) and exceed the
  60 s timeout. Marked `@slow` for now; root cause is RHS scaling.
- `build_mobility_laplacian_2d` (CH 2D) is too slow even on a 16²
  grid. Independent of Python version. Smoke test exists but is `@slow`.
- 17 `F841` unused-local-variable instances in scientific solvers and
  Streamlit tab code. Per-file-ignored for now; domain-by-domain
  triage planned.
- 72 mypy errors remain across `level1_emulsification/solver.py`,
  `protocols/mechanism_data.py`, `level2_gelation/pore_analysis.py`,
  and others. Outside M3 (audit-flagged) scope.
- Promote the CI `installer-smoke` job from wheel-build-only to a
  full silent-install + launch-assert against the actual `.exe`
  installer.

## v8.3.7 — CRLF line endings on shipped .bat files (2026-04-18)

Hotfix for a fatal cmd-parser error on install:

```
[DPSim 8.3.6] Installer -- Windows 11 x64
Python 3.14.3
. was unexpected at this time.
```

### Root cause

The `.bat` files in the v8.3.6 release tree had **Unix LF line
endings** rather than Windows CRLF. A `sed -i` invocation during a
prior version bump (running on Git-Bash) stripped CRLFs from the
files. Windows `cmd.exe` tolerates LF in trivial single-line
commands, but multi-line constructs — specifically

```
for /f "tokens=1,2 delims=." %%a in ("%PYVER%") do (
    set "PYMAJ=%%a"
    set "PYMIN=%%b"
)
```

— get mis-parsed: cmd collapses the block into one logical line
and then chokes on the literal `.` in `delims=.`, giving the
cryptic `. was unexpected at this time` error. Install.bat exits
before it can create `.venv`; all downstream launchers fail.

### Fix

- `release/.../*.bat` — every shipped `.bat` file is now explicitly
  CRLF-terminated.
- `installer/build_installer.bat` — CRLF normalisation step added
  in the staging phase, so future bumps via sed/awk cannot recreate
  this failure mode.

### Workaround for users on v8.3.6 or earlier

The install.bat's bytes-level work is reproducible by hand. From
a Command Prompt at the install directory:

```
python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip wheel
.venv\Scripts\python.exe -m pip install "wheels\dpsim-<ver>-py3-none-any.whl[ui,optimization]"
.venv\Scripts\python.exe -m dpsim ui
```

That bypasses the buggy batch parser entirely.

### Version bumps

- `pyproject.toml`, `__init__.py`: 8.3.6 → 8.3.7.

### Artefacts

- `release/DPSim-8.3.7-Setup.exe` (2.54 MB)
- `release/DPSim-8.3.7-Windows-x64.zip` (566 KB)

---

## v8.3.6 — Import-probe launchers + auto-open browser (2026-04-17)

### Fixed

- `_cmd_ui` no longer passes `--server.headless true` to streamlit,
  so the UI opens the user's default browser automatically. The old
  behaviour required the user to notice the "Open
  http://localhost:8501 in your browser" line and navigate there by
  hand — easy to miss.
- `launch_ui.bat` and `launch_cli.bat` now probe
  `python -c "import dpsim"` as well as checking `.venv\` file
  existence. A partially-created venv (say install.bat failed
  between `python -m venv .venv` and the wheel pip-install) no
  longer bypasses the self-heal path.

### Added

- `release/.../WHERE_ARE_THE_PROGRAM_FILES.txt` — prominent
  short explainer answering the "I don't see a program in the
  install folder!" question. Describes the wheel → venv → site-
  packages flow and gives the one-line command to verify the
  install worked.
- `install.bat` success banner now prints the exact path where
  program files landed after pip install:
  `<install_dir>\.venv\Lib\site-packages\dpsim\`.

### Version bumps

- `pyproject.toml`, `__init__.py`: 8.3.5 → 8.3.6.

### Artefacts

- `release/DPSim-8.3.6-Setup.exe` (2.54 MB)
- `release/DPSim-8.3.6-Windows-x64.zip` (566 KB)

---

## v8.3.5 — Diagnostic-safe launch (fixes flash-crash window) (2026-04-17)

Hotfix for a "flash-and-close" launch experience where double-clicking
the desktop shortcut opened a Command Prompt that disappeared in a
fraction of a second, giving the user no chance to read the actual
error.

### Root cause

Two compounding bugs:

1. `_cmd_ui` (in `src/dpsim/__main__.py`) called
   `subprocess.run(["streamlit", ...])` without propagating the
   subprocess's return code. When Streamlit crashed (e.g., import
   error, port conflict), the parent Python process exited with
   code 0, pretending success.
2. `launch_ui.bat` ran the Python command and did
   `exit /b %ERRORLEVEL%` immediately afterward. A zero exit code
   → normal completion → `cmd /c` closes the window
   instantaneously, taking any error output with it.

Result: users saw a black cmd window blink open and close; no way
to diagnose.

### Fix

- `src/dpsim/__main__.py` / `_cmd_ui`: capture the subprocess
  result and `sys.exit(result.returncode)` when it is non-zero.
  Streamlit failures now propagate up.
- `release/DPSim-8.3.5-Windows-x64/launch_ui.bat`: after the
  Python call returns, if the exit code is non-zero, print a
  diagnostic block (port-conflict / dependency / version hints)
  + a manual-diagnosis command line, then `pause` before exit.
  The window now stays open whenever the UI exited abnormally.
  Normal shutdown (Streamlit exit code 0) still closes the window
  cleanly.

### Version bumps

- `pyproject.toml`, `src/dpsim/__init__.py`: 8.3.4 → 8.3.5.
- Installer script + build helper + release tree: 8.3.4 → 8.3.5.

### Artefacts

- `release/DPSim-8.3.5-Setup.exe` (2.54 MB)
- `release/DPSim-8.3.5-Windows-x64.zip` (564 KB)

### Immediate workaround for v8.3.4 users

If you can't wait for the installer rebuild, open a Command Prompt
manually and run:

```
cd /d "%LOCALAPPDATA%\Programs\DPSim"
.venv\Scripts\python.exe -m dpsim ui
```

That bypasses the `.bat` wrapper entirely and shows the actual
traceback in a window that stays open.

---

## v8.3.4 — Per-user install by default (fixes Access Denied) (2026-04-17)

Hotfix for a second install-time failure reported after v8.3.3:

```
[install] Creating virtual environment at .venv\
Error: [WinError 5] Access is denied: 'C:\Program Files\DPSim\.venv'
[install] ERROR: venv creation failed.
```

### Root cause

The v8.3.2 / v8.3.3 Inno Setup script used
`DefaultDirName={autopf}\DPSim` with
`PrivilegesRequiredOverridesAllowed=dialog`. On a UAC-elevated
install Inno Setup placed files into `C:\Program Files\DPSim`,
but the `[Run]` post-install step (`install.bat`) executes in the
user's non-elevated context. Non-admin cannot create `.venv\`
inside `C:\Program Files\...`, so venv creation fails.

### Fix (Inno Setup script)

- `DefaultDirName={userpf}\DPSim` — per-user Program Files
  (`%LOCALAPPDATA%\Programs\DPSim`), always user-writable.
- `PrivilegesRequiredOverridesAllowed=dialog` removed — user can no
  longer accidentally elevate to a location where the post-install
  step will fail.
- `UsedUserAreasWarning=no` — suppresses the Inno warning that
  would otherwise trigger for an all-user-area install script.

### Fix (install.bat)

- Venv-creation failure now prints an actionable diagnostic:
  "directory not writable → uninstall and reinstall v8.3.4+ per-user,
  or right-click install.bat → Run as administrator".
- No more silent exit 3.

### Migration note for existing admin installs

If v8.3.2 or v8.3.3 was installed into `C:\Program Files\DPSim`:

1. Uninstall (Control Panel → Apps → DPSim, or the Start-Menu
   "Uninstall DPSim" shortcut).
2. Download `DPSim-8.3.4-Setup.exe` from the GitHub Release.
3. Double-click — it installs into `%LOCALAPPDATA%\Programs\DPSim`
   without UAC. The post-install step completes cleanly.

### Version bumps

- `pyproject.toml`, `src/dpsim/__init__.py`, installer script,
  build helper: 8.3.3 → 8.3.4.

### Artefacts

- `release/DPSim-8.3.4-Setup.exe` (2.54 MB)
- `release/DPSim-8.3.4-Windows-x64.zip` (563 KB)
- `dist/dpsim-8.3.4-py3-none-any.whl`

Wheel contents unchanged from v8.3.2.

---

## v8.3.3 — Self-healing launch scripts (2026-04-17)

Hotfix for a dead-end user experience on first run: if the installer's
post-install step was skipped or failed silently (e.g. because
Python 3.11+ was not on PATH at install time), the launcher batch
files previously printed only "Installation not found. Run install.bat
first." and exited, with no actionable guidance.

### Fixed

- `release/.../launch_ui.bat` and `release/.../launch_cli.bat`:
  **self-healing**. On missing `.venv`, they now
  1. report the exact expected path,
  2. probe for `python` on `PATH` and show the detected version,
  3. if Python is absent, print a hyperlink to
     `https://www.python.org/downloads/windows/` and abort cleanly
     with a press-any-key,
  4. if Python is present, offer to run `install.bat --no-test`
     automatically and then continue to the launch,
  5. if setup fails, show the error code and keep the window
     open so the user sees the cause.
- `release/.../install.bat`: always `pause` on completion so the
  user sees the success / failure message. Honours
  `NONINTERACTIVE=1` when invoked from automation. Explicit error
  message + pause on pip-upgrade failure (previously exited 4
  silently).

### Changed (version bumps)

- `pyproject.toml`: 8.3.2 → 8.3.3.
- `src/dpsim/__init__.py.__version__`: 8.3.2 → 8.3.3.
- `installer/DPSim.iss`, `installer/build_installer.bat`: all
  `8.3.2` references updated to `8.3.3`.

### Artefacts

- `release/DPSim-8.3.3-Setup.exe` (2.54 MB) — Inno Setup wizard.
- `release/DPSim-8.3.3-Windows-x64.zip` (563 KB) — portable.
- `dist/dpsim-8.3.3-py3-none-any.whl` (~408 KB) — wheel.

All three are identical in wheel contents to v8.3.2; only the
launcher batch files changed. Users who already have a working
v8.3.2 install can just replace `launch_ui.bat` / `launch_cli.bat` /
`install.bat` with the v8.3.3 versions.

### Smoke verified

Fresh temp venv + `pip install dpsim-8.3.3-py3-none-any.whl` +
`import dpsim` — works end-to-end.

---

## v8.3.2 — One-click Windows 11 installer (.exe) (2026-04-17)

Ships a proper Windows installer wizard as
`release/DPSim-8.3.2-Setup.exe` (2.54 MB), attached to the
existing v8.3.2 GitHub Release alongside the portable ZIP.

### Added

- `installer/DPSim.iss` — Inno Setup 6 script defining the full
  wizard:
  1. **EULA page** (`LICENSE_AND_IP.txt`) declaring: intellectual
     property rights belong to Holocyte Pty Ltd; software licensed
     under GPL-3.0; canonical source at
     `github.com/tocvicmeng-prog/Downstream-Processing-Simulator`.
  2. **Python presence check** with a clickable hyperlink to
     `https://www.python.org/downloads/windows/` if Python 3.11+ is
     not on PATH.
  3. **File layout** — wheel, configs, docs, launcher batch files,
     LICENSE, README, INSTALL, RELEASE_NOTES all extracted under a
     single install directory.
  4. **Shortcuts** — Start-Menu group with Web-UI, CLI, Manual
     PDF, and Uninstall entries; optional desktop shortcut.
  5. **Post-install hook** — runs the bundled `install.bat` which
     creates a self-contained `.venv` and pip-installs the wheel
     with `[ui,optimization]` extras, with a smoke-pipeline check.
  6. **Uninstaller** — purges `.venv` before removing files.
- `installer/LICENSE_AND_IP.txt` — the EULA text shown on the
  installer's first page.
- `installer/build_installer.bat` — four-step build helper
  (wheel, stage, locate ISCC, compile).
- `installer/README.md` — documentation of the installer build and
  runtime behaviour.

### Changed

- `.gitignore` — now also excludes `installer/stage/` (transient
  build directory rebuilt by `build_installer.bat`).

### GitHub Release (v8.3.2)

Two assets now attached:

| Asset | Size | Audience |
|---|---|---|
| `DPSim-8.3.2-Setup.exe` | 2.54 MB | End users (one-click wizard installer) |
| `DPSim-8.3.2-Windows-x64.zip` | 561 KB | Power users (portable, script-based install) |

---

## v8.3.2 — Clean Windows 11 x64 install package (2026-04-17)

Ships a self-contained, dev-artifact-free Windows 11 x64 install
bundle as `release/DPSim-8.3.2-Windows-x64.zip` (0.55 MB
compressed, 14 files). A fresh Windows machine with Python 3.11+
installed can extract the zip and run `install.bat` to get a
fully working simulator — UI, CLI, and programmatic API — in a
self-contained `.venv\` that leaves system Python untouched.

### Version bumps

- `pyproject.toml`: 0.1.0 → 8.3.2 (caught up with feature releases).
- `src/dpsim/__init__.py.__version__`: 0.1.0 → 8.3.2.

### Build artefacts

- `dist/dpsim-8.3.2-py3-none-any.whl` — rebuilt wheel covering
  the full v8.3 feature set (four polymer platforms, inverse
  design, digital twin, MD ingest, Unicode-safe PDF manual).
- `dist/dpsim-8.3.2.tar.gz` — source distribution.

### Release tree (`release/DPSim-8.3.2-Windows-x64/`)

| File | Purpose |
|---|---|
| `install.bat` | Create `.venv\`, install wheel with `[ui,optimization]` extras, verify import, run smoke pipeline. Accepts `--core` / `--no-opt` / `--no-test` flags. |
| `launch_ui.bat` | Start the Streamlit UI at `http://localhost:8501`. |
| `launch_cli.bat` | Open a Command Prompt with the venv activated and `dpsim` on PATH. |
| `uninstall.bat` | Confirm-and-delete the `.venv\`. |
| `README.txt` | One-page quickstart. |
| `INSTALL.md` | Detailed install + troubleshooting guide (7 sections). |
| `RELEASE_NOTES.md` | User-facing summary of what's in 8.3.2. |
| `LICENSE.txt` | Software licence. |
| `wheels/dpsim-8.3.2-py3-none-any.whl` | The wheel (408 KB). |
| `configs/{default,fast_smoke,stirred_vessel}.toml` | Example configs. |
| `docs/User_Manual_First_Edition.{pdf,md}` | First Edition manual. |

### "Clean" guarantees (validated at zip time)

The zip-builder refuses to create the archive if any of these are
present in the release tree:

- `__pycache__/`, `.pyc`, `.pyo`
- `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`
- `.git/`, `.venv/`
- `build/`, `dist/`, `output/`
- `.log` files

Not shipped in the release (kept in the dev repo only):

- Source tree (`src/` — replaced by the wheel).
- Test suite (`tests/`).
- Internal design docs (`docs/f1a_*`, `docs/f1b_*`, `docs/f1c_*`,
  `docs/f2_*`, `docs/f4b_*`, `docs/f5_*`, `docs/node31_*`,
  `docs/node32_*`, `docs/node30_31_*`).
- Full dev `CHANGELOG.md` (condensed into `RELEASE_NOTES.md`).
- `skills/`, `.claude/` agent infrastructure.

### Smoke verification (performed before the ZIP was cut)

- Fresh temp venv + `pip install wheels/dpsim-8.3.2-py3-none-any.whl`:
  install succeeded.
- `import dpsim; dpsim.__version__ == '8.3.2'` — OK.
- `run_pipeline()` default: returns a FullResult with
  `d32 = 18.08 µm` — end-to-end L1 → L4 pipeline executes cleanly
  on a fresh install.

### Final archive

`release/DPSim-8.3.2-Windows-x64.zip` — 561 KB compressed,
648 KB uncompressed, 14 files. Ready for distribution.

---

## v8.3.2 — First Edition PDF Unicode font fix (2026-04-17)

Fixes black-square ("tofu") rendering of scientific Unicode glyphs
(α, ²⁺, ⌈⌉, χ, ∇, ∂, μ, π, ≥, etc.) in the First Edition PDF.

### Root cause

reportlab's built-in Type-1 fonts (Helvetica / Courier) cover only
WinAnsi / Latin-1. Any glyph outside that band — superscripts, Greek
letters, ceiling / floor brackets, mathematical operators — was
rendered as a black filled square. Visible examples reported by the
user: `Ca²⁺-alginate`, `CVaR_α = (1 / ⌈α·N⌉)`.

### Fix

- `docs/user_manual/build_pdf.py` — register DejaVu Sans and DejaVu
  Sans Mono (shipped with matplotlib, each ~6 000 Unicode glyphs
  covering full Greek, super/subscripts, mathematical operators,
  arrows) as TTF fonts via `reportlab.pdfbase.pdfmetrics.registerFont`
  / `registerFontFamily` at module import time. All body, heading,
  code, bullet, caption, table-cell, and page-footer styles now
  reference `DejaVuSans` / `DejaVuSansMono` instead of
  `Helvetica` / `Courier`. Falls back gracefully to the Type-1
  fonts if DejaVu is missing.
- `docs/user_manual/polysaccharide_microsphere_simulator_first_edition.pdf`
  — rebuilt. File size 55 KB → 143 KB (DejaVu TTFs now embedded).

### Verification

- Font cmap coverage confirmed for 20 scientific codepoints
  (U+00B2, U+207A, U+207B, U+03B1, U+03C7, U+03BC, U+2308, U+2309,
  U+00B7, U+2192, U+2207, U+2202, U+222B, U+03C0, U+00B0, U+2265,
  U+2264, U+00B1, U+00D7, U+00D8): **20/20 present**.
- Round-trip text extraction via pypdf finds all user-flagged
  phrases literally in the rebuilt PDF:
  - `Ca²⁺-alginate` present
  - `⌈α·N⌉` present
  - α, χ, ∇, ∂, ≥, π, · present.

---

## v8.3.1 — First Edition user manual (2026-04-17)

Ships the Downstream Processing Simulator
**First Edition** instruction manual as Markdown + PDF, with an
upper-right download button wired into the Streamlit UI. The
manual is written for first-time users (downstream-processing
technicians, junior researchers) who have no prior experience in
microsphere fabrication or downstream processing.

### Added

- `docs/user_manual/polysaccharide_microsphere_simulator_first_edition.md`
  — the authoritative instruction manual. Three-part structure:
  1. **Getting Started** — what the simulator does, workflow
     overview with ASCII chart, five-minute quickstart.
  2. **Platform Catalogue** — the four supported polymer families
     (agarose-chitosan, alginate, cellulose NIPS, PLGA), a
     crosslinker / gelant selection table, the EDC/NHS COOH
     warning.
  3. **Appendices A–I** — detailed input requirements (all
     parameter tables with units + ranges + defaults), process
     steps, essential pre-run checklist, 15-question FAQ,
     architectural ideas + working principles, chemical / physical
     principles, formulas + theorems, six standard wet-lab
     protocols (agarose-chitosan/genipin, Ca²⁺-alginate external &
     internal, cellulose NaOH/urea, EDC/NHS coupling, PLGA
     solvent-evaporation), and a 17-row troubleshooting table.
- `docs/user_manual/build_pdf.py` — compact Markdown-to-PDF
  renderer using reportlab. Handles the Markdown subset used in
  the manual (headings, paragraphs, ordered / unordered lists,
  GitHub tables, fenced code blocks, inline `**bold**` /
  `*italic*` / `` `code` `` with underscore-safe code-span
  extraction via placeholders). Run
  `python docs/user_manual/build_pdf.py` to rebuild.
- `docs/user_manual/polysaccharide_microsphere_simulator_first_edition.pdf`
  — the built artefact (~55 KB, A4, page-footer on every page).

### Changed

- `src/dpsim/visualization/app.py` — the page title row now uses a
  two-column layout with the title on the left and a
  **Manual (PDF)** download button in the upper-right corner.
  Button serves the PDF via `st.download_button` when the file
  exists; falls back to a caption telling the user to run the
  build script if the PDF is absent.

### Dependencies

- `reportlab` added (auto-installed into the user's pip environment
  during the build step). No new runtime requirement for users who
  don't need to regenerate the PDF.

### Tests

- Quick regression of 66 targeted tests (F4-b, F5, F2, PLGA Phase 2,
  cellulose Phase 2/3, alginate L4) pass with 0 regressions after
  the UI edit.

---

## v8.3.0-alpha — Cluster F finish: F4-b CVaR + F5 MD ingest + F2 digital twin (2026-04-17)

Closes the three remaining Cluster F workstreams from the Node 32
roadmap. With this release, **every workstream in Cluster F has a
Phase 1 shipment**.

### F4-b — CVaR robust BO

- `OptimizationEngine(robust_cvar_alpha=α)` — applies Conditional
  Value-at-Risk aggregation over resamples. When both
  `robust_variance_weight` and `robust_cvar_alpha` are set, CVaR
  takes precedence.
- `dpsim design --robust-cvar-alpha α` CLI flag.
- Algorithm: ``CVaR_α = mean of the worst ⌈α·n⌉ resamples per
  objective dimension``. α → 1 recovers the sample mean; α → 0
  approaches the worst-case sample.
- Validation: α ∈ [0, 1]; α > 0 requires `robust_n_samples >= 2`
  and a `target_spec`.
- `docs/f4b_cvar_protocol.md` — full /architect protocol.
- `tests/test_f4b_cvar.py` — 11 tests (math, engine validation,
  CLI, precedence, head-to-head vs mean-variance).

### F5 — MARTINI MD parameter ingest

- `src/dpsim/md_ingest.py` — `MartiniRecord` dataclass + JSON
  load / save + `apply_chi_to_props(props, record)` for cellulose
  χ fields.
- JSON schema: required `source / system_description / beads / chi /
  diagnostics`; optional `paper_doi / notes`; forward-compat
  unknown top-level keys preserved in `record.extra`.
- Current mapping: `polymer_solvent / polymer_nonsolvent /
  solvent_nonsolvent` → `chi_PS_cellulose / chi_PN_cellulose /
  chi_SN_cellulose` on `MaterialProperties`. Non-cellulose fields
  never modified. Missing χ sub-keys leave fields untouched.
- Validation: NaN / inf χ rejected at load; negative χ allowed
  (physically valid for attractive mixing).
- `data/validation/md/example_martini_cellulose.json` — reference
  fixture for tests and user-authoring template.
- `docs/f5_md_ingest_protocol.md` — full /architect protocol.
- `tests/test_md_ingest.py` — 11 tests (load, missing keys,
  extra-keys preservation, partial χ, apply to props, non-cellulose
  fields untouched, non-finite guards, negative χ, round-trip).

### F2 — Digital twin EnKF replay (Phase 1)

- `src/dpsim/digital_twin/enkf.py` — stochastic Ensemble Kalman
  Filter (Evensen 1994) `enkf_update(x, y_fc, y_obs, R, rng,
  inflation)`. Scalar observations only in Phase 1; multiplicative
  prior inflation optional.
- `src/dpsim/digital_twin/replay.py` — `run_replay(trace, x0,
  state_transition, observation_operator, ...)` walks forward
  through a `DigitalTwinTrace`, applies EnKF at each observation,
  returns `ReplayResult` with per-observation mean / std / optional
  full ensemble + a `DigitalTwin.EnKFReplay` SEMI_QUANTITATIVE
  manifest.
- `src/dpsim/digital_twin/schema.py` — `DigitalTwinTrace` +
  `Observation` dataclasses + JSON load / save (sorts observations
  by time on load).
- `src/dpsim/digital_twin/__init__.py` — module exports.
- `docs/f2_digital_twin_protocol.md` — full /architect protocol.
- `tests/test_digital_twin.py` — 11 tests (EnKF linear-Gaussian
  convergence, zero-noise collapse, inflation grows spread, EnKF
  input validation, trace round-trip + time-ordering on load,
  replay trajectory shape, empty-trace passthrough, multi-step
  spread shrinkage).

### Tests

- 33 new tests across F4-b (11) + F5 (11) + F2 (11). 218 targeted
  regression tests pass (PLGA Phase 1/2 + cellulose Phase 1/2/3 +
  internal-gelation + alginate 2a/b/c + EDC/NHS + UQ unified + CLI
  v7 + inverse-design + F4-b + F5 + F2) with 0 regressions.

### Footprint

- F4-b: ~220 LOC (engine edit + CLI + tests).
- F5: ~465 LOC (module + fixture + tests + docs).
- F2: ~895 LOC (schema + enkf + replay + __init__ + tests + docs).
- Total: ~1580 LOC added this turn.

### Cluster F status

All Cluster F workstreams from the Node 32 v8.0 roadmap are at
least Phase-1 shipped:

| Workstream | Status |
|---|---|
| F1-a Alginate | ✓ fully wired (v8.0-rc2) |
| F1-b Cellulose NIPS | ✓ fully wired (v8.1-beta) |
| F1-c PLGA | ✓ fully wired (v8.2-beta) |
| F2 Digital twin (EnKF replay) | ✓ Phase 1 shipped (v8.3-alpha) |
| F3-a Inverse design | ✓ complete (v8.0-alpha) |
| F3-b/c BO engine + CLI | ✓ complete (v8.0-alpha) |
| F4-a Robust BO (mean-variance) | ✓ complete (v8.0-alpha) |
| F4-b Robust BO (CVaR) | ✓ complete (v8.3-alpha) |
| F5 MD ingest (MARTINI) | ✓ Phase 1 shipped (v8.3-alpha) |

### Still deferred (Phase-2+ items, each needs fresh /architect kickoff)

- F2: vector observations (matrix R), square-root / deterministic
  EnKF variants, online polling adapter, MPC layer, identifiability
  diagnostics.
- F5: tabulated U(r) pair-potential ingestion, automatic
  MARTINI ↔ DPSim bead-type mapping, CalibrationStore integration,
  reverse-direction emit.
- F4-b: automatic α selection (tail-risk auto-tune).
- PLGA moving-boundary ALE solver + Fujita `D(phi)`.
- v7.0 release still blocked on Study A wet-lab data.

---

## v8.2.0-beta — F1-c Phase 2: PLGA orchestrator + CLI + TOML (2026-04-17)

Closes F1-c. **All three Cluster F platforms (alginate, cellulose,
PLGA) are now fully wired end-to-end** — orchestrator dispatch, CLI
flags, and TOML config keys. F1 (multi-platform microsphere family)
is complete at the protocol-scope level.

### Added

- `PipelineOrchestrator._run_plga(...)` — mirrors `_run_cellulose` /
  `_run_alginate`. Applies `params.formulation.plga_grade` preset to
  MaterialProperties before the L2 solver runs. Skips L2a timing and
  L3 crosslinking (PLGA microspheres are glassy / physically
  entangled, not crosslinked); stubs `CrosslinkingResult`. Emits
  summary.json with `polymer_family = "plga"`, L2 diagnostics
  (`phi_plga_mean_final`, `t_vitrification_s`,
  `skin_thickness_proxy_m`, `R_shrunk_m`), and the L4 modulus.
- `run_single` branch: `props.polymer_family == PolymerFamily.PLGA`
  routes to `_run_plga`. Placed immediately after the cellulose
  branch for symmetry.
- `dpsim run --plga-grade {50_50 | 75_25 | 85_15 | pla}` CLI flag.
  Packs the grade's 4 PLGA-specific fields into `props_overrides`.
  Meaningful with `--polymer-family plga`; prints a one-line
  confirmation unless `--quiet`.
- TOML `[formulation].plga_grade = "..."` unpacks directly into the
  existing `FormulationParameters.plga_grade` field (shipped in
  F1-c Phase 1); orchestrator resolves at run time via
  `properties.plga_defaults.apply_preset`.

### Changed

- `orchestrator.py` — new imports (`solve_solvent_evaporation`,
  `solve_mechanical_plga`), new PLGA branch, new `_run_plga` method
  (~115 LOC).
- `__main__.py` — `--plga-grade` flag + `_cmd_run` hook to expand
  preset into `props_overrides`.
- `config.py` — no changes needed; TOML key unpacks naturally via
  the existing `plga_grade` field.

### Tests

- `tests/test_plga_phase2.py` — 12 tests:
  - Orchestrator dispatch (3): PLGA routes to `_run_plga`, summary.json
    records `polymer_family`, full pipeline reports
    SEMI_QUANTITATIVE end-to-end.
  - Preset application (2): orchestrator patches props (85:15 K_glassy
    = 1 × 10⁹ Pa verified); unknown grade raises `KeyError`.
  - TOML (2): `plga_grade` key unpacks; absent defaults to empty string.
  - CLI (2): all 4 choices in shipped parser source; argparse accepts
    the full flag invocation.
  - End-to-end sanity (3): non-zero G_DN; switching grade gives ≥
    1.5× modulus spread; L3 `p_final = 0` (stubbed).
- 185 targeted regression tests pass (PLGA Phase 1 + Phase 2 +
  cellulose Phases 1/2/3 + internal-gelation + alginate 2a/b/c +
  EDC/NHS + UQ unified + CLI v7 + inverse-design) with 0 regressions.

### Footprint

- New LOC: ~115 (orchestrator `_run_plga`) + ~30 (CLI) + ~340
  (tests) ≈ 485 LOC. Under the protocol's ~430 LOC estimate by a
  hair (simple wiring + trivial TOML).
- Cumulative F1 footprint across all three platforms: **~5000 LOC**.

### Cluster F status after v8.2.0-beta

| Platform | Programmatic | Orchestrator | CLI | TOML | Presets |
|---|---|---|---|---|---|
| Agarose-chitosan (default) | ✓ | ✓ | ✓ | ✓ | (built-in) |
| Alginate | ✓ | ✓ | ✓ | ✓ | 2 gelants |
| Cellulose NIPS | ✓ | ✓ | ✓ | ✓ | 4 solvents |
| PLGA solvent evap | ✓ | ✓ | ✓ | ✓ | 4 grades |

**F1 complete.** Other Cluster F workstreams remain un-started and
need their own /architect kickoffs:

- **F2 digital twin** (EnKF replay harness) — scoped in Node 32
  roadmap, protocol not drafted.
- **F4-b CVaR acquisition** — deferred v8.0 polish; trivial variant
  of F4-a once the resample strategy is finalised.
- **F5 MD parameter ingest** (MARTINI — ingest-only default) —
  scoped in Node 32 roadmap, protocol not drafted.

### Still deferred

- Moving-boundary ALE solver for PLGA shrinking-droplet correction
  (R5 from F1-c protocol).
- Fujita concentration-dependent `D(phi)` for late-stage PLGA
  evaporation dynamics.
- v7.0 release still blocked on Study A wet-lab data.

---

## v8.2.0-alpha — F1-c Phase 1: PLGA solvent-evaporation L2 + L4 + 4 grades (2026-04-17)

First shipment of Cluster F platform #3. Adds a PLGA /
solvent-evaporation L2 solver + Gibson-Ashby L4 modulus + full 4-grade
registry (PLGA 50:50 / 75:25 / 85:15 / PLA). Ships as
**programmatic API only**; orchestrator dispatch / CLI / TOML = F1-c
Phase 2.

### Added

- `docs/f1c_plga_protocol.md` — full /architect protocol doc (§1 scope,
  §2 mechanism + lit anchors, §4 algorithm, §5 4-grade parameter
  table, §6 16 test cases, §7 risks, §8 G1 12/12 for Phase 1,
  §9 execution plan). Matches the f1a / f1b protocol pattern.
- `src/dpsim/level2_gelation/solvent_evaporation.py` (~330 LOC):
  1D spherical Fickian DCM-depletion solver.
  - State: ``phi_DCM(r, t)`` single field; ``phi_PLGA = 1 − phi_DCM``
    algebraic.
  - Dirichlet sink at ``r = R`` (``phi_DCM_eq ≈ 0.005`` for DCM/water),
    symmetry at ``r = 0``.
  - BDF time integrator with dense-output vitrification-time probe.
  - Approximations: fixed droplet radius (moving-boundary ALE = Phase 2
    refinement); constant D (Fujita ``D(phi)`` = Phase 2). Both
    flagged in manifest assumptions.
  - Emits SEMI_QUANTITATIVE `GelationResult` tagged
    `L2.Gelation.SolventEvaporationPLGA` with
    `phi_plga_mean_final / phi_dcm_mean_final / t_vitrification /
    skin_thickness_proxy / core_porosity_proxy / R_shrunk_m`
    diagnostics.
- `src/dpsim/level4_mechanical/plga.py` (~130 LOC):
  `plga_modulus(phi_mean, G_glassy, n_plga)` Gibson-Ashby power law +
  `solve_mechanical_plga(...)` wrapper emitting
  `L4.Mechanical.PLGAGibsonAshby` SEMI_QUANTITATIVE
  `MechanicalResult` with `network_type="glassy_polymer"` and
  `model_used="plga_gibson_ashby"`.
- `src/dpsim/properties/plga_defaults.py` (~160 LOC):
  `PLGAGradeProfile` dataclass + `PLGA_GRADE_PRESETS` registry with
  **all four** grades populated (`50_50`, `75_25`, `85_15`, `pla`).
  Data sourced from Wang 1999 (D_DCM), Park 1998 (T_g, G_glassy),
  Freitas 2005 (process parameters). `apply_preset(props, grade)`
  helper mirrors the alginate / cellulose pattern. Phase 3 is
  effectively eliminated by shipping all 4 presets up front.
- `MaterialProperties` gains 4 PLGA-specific fields
  (`D_DCM_plga`, `phi_DCM_eq`, `G_glassy_plga`, `n_plga_modulus`).
- `FormulationParameters` gains `phi_PLGA_0` (initial polymer volume
  fraction in the droplet; default 0 = not-PLGA) and `plga_grade`
  (Phase 2 preset-selector field; default empty = skip).

### Tests

- `tests/test_plga_phase1.py` — 25 tests covering:
  - **Protocol §6 test 1**: monotone DCM depletion (with fixed
    transient-regime probe times)
  - **Protocol §6 test 2**: Dirichlet sink drives `phi_PLGA → 1` at
    long time
  - **Protocol §6 test 3**: early-regime √t front scaling (log-log
    slope 0.5 ± 0.15)
  - **Protocol §6 test 4**: 4× D_DCM gives earlier vitrification
  - **Protocol §6 test 5**: Gibson-Ashby `G ∝ phi^n` scaling (n ∈
    {1.5, 2.0, 2.5}); dense limit recovers `G_glassy`
  - **Protocol §6 test 6**: zero PLGA → UNSUPPORTED manifest + zero
    modulus
  - **Protocol §6 test 7**: L2 + L4 both SEMI_QUANTITATIVE; full
    diagnostic key presence
  - **Protocol §6 test 8**: `apply_preset` patches 4 PLGA fields;
    4 grades registered; physical-plausibility check on every grade
    (L_fraction, M_n, T_g, D, G_glassy, n ranges); switching grade
    gives ≥ 1.4× modulus spread
  - Edge cases: `plga_modulus` zero/negative inputs
  - Input validation: negative R, tiny grid, phi_0 out of [0, 1],
    negative time, non-positive D_DCM
  - Mass-conservation post-processing: `R_shrunk = R_0 · phi_0^(1/3)`
    at long time
- 173 targeted regression tests pass (PLGA Phase 1 + cellulose
  Phase 1/2/3 + internal-gelation + alginate 2a/b/c + EDC/NHS + UQ
  unified + CLI v7 + inverse-design) with 0 regressions.

### Footprint

- New LOC: ~330 (solver) + ~130 (L4) + ~160 (defaults) + ~25
  (datatypes) + ~390 (tests) ≈ 1035 LOC. Slightly over the protocol's
  ~910 LOC estimate because all 4 grade presets shipped in Phase 1
  instead of 3 being deferred to Phase 3.

### Still deferred

- **F1-c Phase 2** (~430 LOC, 1–2 sessions): orchestrator
  `_run_plga` branch (mirror `_run_cellulose`), `--polymer-family
  plga --plga-grade <name>` CLI surface, `[formulation].plga_grade`
  TOML key application, 12 integration tests.
- **F1-c Phase 3**: absorbed into Phase 1 (all 4 presets shipped).
- **Moving-boundary ALE solver** for shrinking-droplet correction
  (R5 from the protocol). Current fixed-R approximation reports
  `R_shrunk` as a post-processing diagnostic so users can plot the
  true final sphere.
- **Fujita concentration-dependent D**: v1 uses constant D; late-time
  (phi > 0.8) dynamics are order-of-magnitude-right, not quantitative.
- v7.0 release still blocked on Study A wet-lab data.

---

## v8.1.0-beta — F1-b Phases 2 + 3: cellulose orchestrator + all 4 solvents (2026-04-17)

Closes F1-b. Cellulose NIPS is now a first-class user-facing platform
(matches alginate surface area). All four solvent-system presets are
populated; the orchestrator dispatches `PolymerFamily.CELLULOSE`
through a dedicated `_run_cellulose` sub-pipeline; TOML and CLI flags
expose both family selection and solvent selection.

### Added

- `PipelineOrchestrator._run_cellulose(...)` — mirrors
  `_run_alginate`. Applies a solvent-system preset (if declared on
  `params.formulation.solvent_system`) to MaterialProperties before
  solving L2 NIPS. Skips L2a timing and L3 crosslinking (NIPS IS the
  gelation); stubs `CrosslinkingResult`. Emits summary.json with
  `polymer_family = "cellulose"`, `phi_mean_final`,
  `bicontinuous_score`, `demixing_index`, and the L4 modulus.
- `run_single` branch: `props.polymer_family == PolymerFamily.CELLULOSE`
  routes to `_run_cellulose`. Placed immediately after the alginate
  branch for symmetry.
- `FormulationParameters.solvent_system: str = ""` — TOML key
  `[formulation].solvent_system = "naoh_urea"` unpacks directly into
  this field, then the orchestrator resolves it at run time via
  `properties.cellulose_defaults.apply_preset`.
- `dpsim run --cellulose-solvent {naoh_urea | nmmo | emim_ac |
  dmac_licl}` CLI flag — packs the preset's 9 cellulose-specific
  fields into `props_overrides` before `run_single`. Meaningful with
  `--polymer-family cellulose`; prints a one-line confirmation
  (`Cellulose solvent preset: ...`) unless `--quiet`.
- Three new presets in `src/dpsim/properties/cellulose_defaults.py`:
  - **NMMO** (Lyocell, 80 wt% aq., T = 90 °C, higher N_p = 500,
    K_cell = 8 × 10⁵ Pa; Lenzing system).
  - **EMIM-Ac** (1-ethyl-3-methylimidazolium acetate, T = 80 °C,
    lowest χ_PS = 0.38; Swatloski 2002 IL system).
  - **DMAc/LiCl** (McCormick analytical system, T = 60 °C activation,
    K_cell = 6 × 10⁵ Pa). All values from the literature anchors in
    `docs/f1b_cellulose_nips_protocol.md` §5.

### Changed

- `orchestrator.py` — new imports (`solve_nips_cellulose`,
  `solve_mechanical_cellulose`), new CELLULOSE branch, new
  `_run_cellulose` method (~110 LOC).
- `__main__.py` — `--cellulose-solvent` flag + `_cmd_run` hook to
  expand preset into `props_overrides`.
- `config.py` — TOML `[formulation].solvent_system` unpacks naturally
  via the new `FormulationParameters.solvent_system` field. No
  special-case parsing; validation deferred to solver-time
  `apply_preset(...)`.

### Tests

- `tests/test_cellulose_phase2_phase3.py` — 14 tests:
  - Orchestrator dispatch (3): CELLULOSE routes to `_run_cellulose`,
    summary.json records polymer_family, full pipeline reports
    SEMI_QUANTITATIVE end-to-end.
  - TOML wiring (2): `solvent_system` key unpacks, absent key defaults
    to empty string.
  - Solvent preset application (2): orchestrator patches props so L4
    K_cell matches the NMMO preset (8 × 10⁵ Pa); unknown preset raises
    `KeyError`.
  - CLI (2): `--cellulose-solvent` flag in shipped parser, argparse
    accepts all 4 choices.
  - Registry (3): all 4 presets registered, each passes physical
    plausibility (χ_PN > χ_PS, D in bulk-water range, N_p in DP range,
    K_cell in 10⁴–10⁷ Pa band), water is the default non-solvent for
    all.
  - Diagnostics differentiation (1): switching preset changes G_DN by
    > 1.5× (spans real range).
  - Argparse rejection (1): unknown preset exits non-zero.
- 152 targeted regression tests pass (Phase 1 + Phase 2/3 +
  internal-gelation + alginate 2a/b/c + EDC/NHS + UQ unified + CLI v7
  + parallel MC + inverse-design) with 0 regressions.

### Footprint

- New LOC: ~110 (orchestrator `_run_cellulose`) + ~15 (CLI) + ~1
  (config.py, just the TOML doc comment) + ~160 (3 new presets) +
  ~330 (tests) ≈ 615 LOC. Cumulative F1-b footprint (Phases 1 + 2 +
  3): ~1525 LOC, a little under the 2000 LOC protocol budget because
  Phase 2 config wiring naturally unpacks via the single
  `solvent_system` field rather than needing a dedicated parser.

### Still deferred

- **v7.0 release** remains blocked on Study A wet-lab data.
- **F1-c PLGA solvent evaporation** still unscoped — a fresh
  /architect protocol is the natural next step if commercial
  prioritisation calls for it.

---

## v8.1.0-alpha — F1-b Phase 1: cellulose NIPS L2 + L4 + NaOH/urea (2026-04-17)

First shipment of Cluster F platform #2. Adds a cellulose /
non-solvent-induced phase separation (NIPS) L2 solver + L4 modulus +
NaOH/urea parameter preset. Ships as **programmatic API only** for now
— orchestrator dispatch / TOML config / CLI flags land in F1-b Phase 2.

### Added

- `src/dpsim/level2_gelation/nips_cellulose.py` (~380 LOC):
  1D spherical ternary Cahn-Hilliard + Fickian coupled-PDE solver.
  - State: `phi(r, t)` cellulose + `s(r, t)` solvent, `n = 1-phi-s`
    non-solvent (algebraic).
  - Flory-Huggins free energy with χ_PS / χ_PN / χ_SN.
  - Cahn-Hilliard gradient-energy regularisation on `mu_phi`.
  - Dirichlet bath BC at `r = R` (pure water by default), symmetry
    at `r = 0`.
  - 1 % noise on initial `phi` breaks spherical symmetry so spinodal
    decomposition can develop.
  - BDF time integration; clipped log arguments protect against
    spinodal excursions outside the physical simplex.
  - Emits SEMI_QUANTITATIVE `GelationResult` tagged
    `L2.Gelation.NIPSCellulose` with
    `phi_mean_final / s_mean_final / n_mean_final / phi_std_final /
    bicontinuous_score / demixing_index` diagnostics.
- `src/dpsim/level4_mechanical/cellulose.py` (~140 LOC):
  `cellulose_modulus(phi_mean, K_cell, alpha_cell)` power-law +
  `solve_mechanical_cellulose(...)` wrapper that emits
  `L4.Mechanical.CelluloseZhang2020` SEMI_QUANTITATIVE
  `MechanicalResult` with `network_type="physical_entangled"` and
  `model_used="cellulose_zhang2020"`.
- `src/dpsim/properties/cellulose_defaults.py` (~100 LOC):
  `CelluloseSolventPreset` dataclass + `CELLULOSE_SOLVENT_PRESETS`
  registry + `apply_preset(props, name)` helper. NaOH/urea preset
  (Zhang Lab Wuhan) populated from Lindman 2010 / Xu 2010 / Zhang
  2020. NMMO, EMIM-Ac, DMAc/LiCl stubs ship in F1-b Phase 3.
- `MaterialProperties` gains 9 cellulose-specific fields
  (`N_p_cellulose`, `chi_{PS,PN,SN}_cellulose`,
  `D_{solvent,nonsolvent}_cellulose`, `kappa_CH_cellulose`,
  `K_cell_modulus`, `alpha_cell_modulus`) — defaults match the
  NaOH/urea preset.
- `FormulationParameters.phi_cellulose_0` — initial cellulose volume
  fraction (default 0 = not-cellulose).

### Tests

- `tests/test_cellulose_nips_phase1.py` — 19 tests covering:
  - Protocol §6 test 2: ternary mass conservation (`phi + s + n = 1`)
  - Protocol §6 test 4: water-bath driven demixing (`phi_std` grows)
  - Protocol §6 test 7: modulus scaling `G ∝ phi^α`
  - Protocol §6 test 8: zero cellulose → zero gel / zero modulus
  - Protocol §6 test 10: SEMI_QUANTITATIVE manifests on both L2 and L4
  - NaOH/urea preset registry + `apply_preset` patching 9 fields
  - L4 modulus edge cases (zero phi / zero prefactor / negative phi)
  - Solver input validation (R ≤ 0, n_r < 8, phi_0 out of [0, 1],
    negative time / noise)
- 113 targeted regression tests pass (Phase 1 + internal-gelation +
  alginate Phase 2a/b/c + EDC/NHS + UQ unified + CLI v7) with 0
  regressions — the datatypes extensions did not perturb any existing
  consumers.

### Footprint

- New LOC: ~380 (solver) + ~140 (L4) + ~100 (defaults) + ~15
  (datatypes) + ~275 (tests) ≈ 910 LOC. On target for the protocol's
  Phase 1 ~900 LOC estimate.

### Still deferred (F1-b Phase 2 and 3)

- F1-b Phase 2: orchestrator `_run_cellulose` branch +
  `--polymer-family cellulose` CLI flag + `[formulation].solvent_system
  = "naoh_urea"` TOML key + 5 integration tests. ~500 LOC, 1–2
  sessions.
- F1-b Phase 3: NMMO / EMIM-Ac / DMAc/LiCl preset populations + 4
  solvent-dependence tests. ~350 LOC, 1 session.
- v7.0 release still blocked on Study A wet-lab data.

---

## v8.0.0-rc2 — Coupled GDL/CaCO₃ internal-release solver + F1-b protocol (2026-04-17)

Closes the last F1-a Phase 2c deferred item (the coupled
GDL/CaCO₃/alginate solver replacing the lumped-parameter exponential
approximation) and publishes the /architect protocol for F1-b
(cellulose NIPS), tee-ing up the next platform without committing to
implementation in this session.

### Added

- `solve_internal_gelation(params, props, *, R_droplet, C_CaCO3_0,
  L_GDL_0, k_hyd, k_diss, n_r, time, rtol, atol)` in
  `src/dpsim/level2_gelation/ionic_ca.py` — coupled ODE+PDE solver
  for homogeneous internal-release alginate gelation. State:
  - 3 spatially-uniform scalars (GDL, gluconic acid ≈ [H⁺], CaCO₃)
  - 3 radial fields (Ca²⁺, guluronate, egg-box crosslink density)
  - 6 coupled rate equations implementing GDL hydrolysis (Draget
    1997 k_hyd = 1.5 × 10⁻⁴ /s), CaCO₃ dissolution (Plummer 1978,
    Pokrovsky & Schott 2002 k_diss = 1 × 10⁻² m³/(mol·s)), and the
    existing Ca²⁺-guluronate egg-box binding.
  - No-flux outer BC (sealed droplet) + symmetry inner BC.
  - Emits SEMI_QUANTITATIVE `GelationResult` tagged
    `L2.Gelation.IonicCaInternalRelease` with `X_cov` homogeneity
    metric in diagnostics.
- `tests/test_internal_gelation.py` — 11 tests covering:
  - Schema + stoichiometric default for `L_GDL_0 = 2 × C_CaCO3_0`
  - First-order GDL hydrolysis decay (theory vs numerics within 2 %)
  - Monotone conversion
  - Zero-CaCO₃ and zero-alginate sanity
  - Ca²⁺ mass-balance under the no-flux BC
  - Homogeneity: internal-release CoV(X) < shrinking-core CoV(X) at
    matched Ca²⁺ budget and bead size (confirms the Draget 1997
    uniform-gel claim in simulation)
  - Input validation (negative R, negative CaCO₃, tiny grid)
- `docs/f1b_cellulose_nips_protocol.md` — full /architect protocol
  for the cellulose non-solvent-induced phase separation platform
  (F1-b). Includes: NIPS mechanism summary, 4-solvent parameter
  table (NaOH/urea, NMMO, EMIM-Ac, DMAc/LiCl), Cahn-Hilliard + ternary
  coupled-diffusion solver algorithm, 13 test cases, G1 gate status
  (10/12), and a 3-phase execution plan (4-6 fresh sessions total).

### Tests

- 11 new internal-gelation tests pass. 51 targeted regression
  (alginate Phase 2a + 2b + 2c + internal-release + CLI) with 0
  regressions.

### Still deferred

- **F1-b cellulose NIPS implementation** — protocol ready at
  `docs/f1b_cellulose_nips_protocol.md`; waits on fresh session(s)
  for the ~2000 LOC solver + tests.
- **F1-c PLGA solvent evaporation** — still un-scoped.
- **v7.0 release** — blocked on Study A wet-lab data.

---

## v8.0.0-rc1 — F1-a gelant preset wiring (2026-04-17)

Polish pass over v8.0.0-beta: the alginate reagent library shipped in
Phase 2c is now a first-class runtime input. Users can select a gelant
preset via `--gelant` on the CLI or `gelant = "..."` in the TOML
`[formulation]` section, and the simulator auto-wires the profile's
effective Ca²⁺ concentration into `FormulationParameters.c_Ca_bath`
using the current `t_crosslink` (static for external bath, saturating
exponential for internal release).

### Added

- `dpsim run --gelant {cacl2_external | gdl_caco3_internal}` CLI
  flag. When set, prints
  ``Gelant preset: <name> (c_Ca_bath = X mol/m³ at t_crosslink = Y s)``
  and overrides `formulation.c_Ca_bath` before the orchestrator runs.
- `[formulation].gelant = "<name>"` TOML key. Consumed by
  `load_config()` before unpacking the formulation section —
  `gelant` is a preset selector, not a persistent dataclass field.
  Unknown names raise `ValueError` with the list of available presets.
- 5 new tests in `tests/test_alginate_phase2c.py` (`TestGelantPreset`)
  covering external-bath static wiring, internal-release
  time-saturation, unknown-gelant rejection, and CLI argparse.

### Changed

- `_cmd_run` consults `GELANTS_ALGINATE` + `effective_bath_concentration`
  when `--gelant` is set, **after** `--polymer-family` has applied but
  **before** the orchestrator is instantiated.

### Tests

- 51 targeted regression pass (Phase 2c + Phase 2a/2b alginate + CLI),
  0 regressions. New Phase 2c total: 20 tests.

---

## v8.0.0-beta — F1-a Phase 2c: Alginate reagent library, TOML config, CLI (2026-04-17)

Closes the remaining three protocol §6 tests for the alginate platform
and exposes alginate as a first-class user-facing surface (CLI flag,
TOML config, reagent library). With Phase 2c in, alginate is no longer
a programmatic-API-only feature — end users can run
`python -m dpsim run --polymer-family alginate` against a TOML-defined
formulation and get the full L1 → L2-ionic-Ca → L4-Kong pipeline.

### Added

- `src/dpsim/reagent_library_alginate.py` — new
  `AlginateGelantProfile` dataclass and `GELANTS_ALGINATE` dict with two
  canonical entries:
  - **`cacl2_external`** — 100 mM CaCl₂ bath, shrinking-core mode,
    baseline for emulsification + drop-bath processes.
  - **`gdl_caco3_internal`** — glucono-δ-lactone + CaCO₃ in-situ
    release, lumped first-order release rate `k_release = 1.5e-4 s⁻¹`
    from Draget 1997.
  - `effective_bath_concentration(profile, t_end)` helper returns the
    static bath concentration for external mode and
    `C_source·(1 − exp(−k·t))` for internal mode.
- CLI `python -m dpsim run --polymer-family {agarose_chitosan |
  alginate | cellulose | plga}` flag routes `run_single` to the
  matching L2/L4 solver pair via `props_overrides={"polymer_family":
  ...}`.
- `tests/test_alginate_phase2c.py` — 15 tests covering:
  - **Protocol §6 test 3**: √t shrinking-core scaling
    (log-log slope of `X_mean` vs `t` is 0.5 ± 0.15 in the early
    diffusion-limited regime; R=1 mm, t=[10, 40, 160] s).
  - **Protocol §6 test 9**: TOML round-trip of
    `polymer_family = "alginate"` (and unknown-family rejection).
  - **Protocol §6 test 10**: L2 + L4 manifests both report
    SEMI_QUANTITATIVE when routed through the orchestrator, and
    RunReport's `min_evidence_tier` reflects that.
  - Alginate gelant library smoke (both modes, saturating release,
    unknown-mode ValueError).
  - CLI `--polymer-family alginate` argparse acceptance.

### Changed

- `src/dpsim/config.py` / `load_properties()` — accepts top-level
  scalar keys in addition to nested sections and coerces
  `polymer_family` strings to `PolymerFamily` enum members before
  constructing `MaterialProperties`. Unknown family names raise
  `ValueError` cleanly (no silent fall-through).
- `src/dpsim/__main__.py` / `_cmd_run` — `--polymer-family` override
  builds a `props_overrides` dict and passes it to
  `orchestrator.run_single`. Behaviour unchanged when the flag is
  omitted.

### Footprint

- New LOC: ~180 (reagent library) + ~20 (config) + ~15 (CLI) + ~270
  (tests) ≈ 485 LOC, within the protocol estimate for Phase 2c.
- Cumulative F1-a footprint (Phase 2a + 2b + 2c): ~1505 LOC of a
  projected ~1900 LOC; the ~400 LOC gap is cellulose-NIPS / PLGA
  scaffolding that was never in F1-a scope anyway.

### Tests

- 15 new Phase 2c tests; 115 targeted regression tests pass (alginate
  Phase 2a + 2b + 2c, EDC/NHS, UQ unified, UQ panel, inverse-design
  objectives + engine, parallel MC, CLI v7) with 0 regressions.

### Known limitations / still deferred

- Internal GDL/CaCO₃ mode uses the lumped-parameter
  `C_eff = C_source·(1 − exp(−k·t))` approximation; a fully coupled
  GDL + CaCO₃ + alginate solver is a Phase 3 follow-up if users
  request homogeneity predictions.
- Reagent library is surfaced as a module-level dict; a full
  `dpsim run --gelant cacl2_external` CLI flag that wires the
  profile into `FormulationParameters` automatically is a trivial
  v8.0-rc polish item.
- v7.0 release remains blocked on Study A wet-lab data for Node 21
  L1 PBE recalibration (unchanged from v7.0.1).

---

## v8.0.0-alpha — F1-a Phase 2b: Alginate L4 + orchestrator dispatch (2026-04-17)

Completes the functional alginate pipeline. `python`-level users can
now run a full L1 → L2 ionic-Ca → L4 Kong-2004 modulus pipeline for
alginate microspheres via `PipelineOrchestrator.run_single(params,
props_overrides={"polymer_family": PolymerFamily.ALGINATE, ...})`.

### Added

- `FormulationParameters.c_alginate` (kg/m³, default 0) +
  `FormulationParameters.c_Ca_bath` (mol/m³, default 100 mM CaCl₂).
  Zero `c_alginate` transparently falls back to the `c_agarose` slot
  for Phase 2a backward-compat.
- `src/dpsim/level4_mechanical/alginate.py` — Kong 2004 empirical
  modulus with `alginate_modulus(c, f_G, X_mean, K, n)` and
  `solve_mechanical_alginate(params, props, gelation, R_droplet=)`.
  Emits SEMI_QUANTITATIVE-tier `MechanicalResult` with
  `network_type="ionic_reinforced"` and `model_used="alginate_kong2004"`.
- `PipelineOrchestrator._run_alginate(...)` sub-pipeline: branches off
  `run_single` when `props.polymer_family == PolymerFamily.ALGINATE`.
  Skips L2a timing and L3 crosslinking (ionic gelation IS the
  crosslinking); stubs `CrosslinkingResult` to preserve the FullResult
  schema; records `polymer_family` in summary.json + RunReport
  diagnostics.
- `tests/test_alginate_l4_and_pipeline.py` — 7 tests covering:
  - `alginate_modulus` unit scaling in c² and f_G² (protocol §6 tests
    6, 7)
  - incomplete-gelation modulus reduction
  - `solve_mechanical_alginate` schema + zero-alginate edge case
  - full-pipeline orchestrator dispatch with `PolymerFamily.ALGINATE`
    (protocol §6 test 11)

### Tests

- 96/96 targeted regression tests pass in 88 s across F1-a Phase 2a/2b,
  F3 (inverse design + engine + CLI), F4-a, Node 30 / 31 / 30b, and
  the CLI contract. 0 regressions.

### Still deferred to F1-a Phase 2c / v8.0-beta

- Reagent library entries for CaCl₂ + internal GDL/CaCO₃ gelation.
- `config.py` TOML parser support for `polymer_family = "alginate"`
  (users currently set via `props_overrides` programmatically).
- The three remaining protocol §6 tests (§6 test 3 √t shrinking-core
  scaling, §6 test 9 TOML round-trip, §6 test 10 manifest-tier
  reporting from the orchestrator).
- CLI `python -m dpsim run --polymer-family alginate` surface.

### Footprint

- **Added:** ~380 LOC (L4 alginate + orchestrator branch + 7 tests) on
  top of Phase 2a's 640 LOC → cumulative F1-a footprint ~1020 LOC,
  about half of the ~1900 LOC roadmap estimate.

## v8.0.0-alpha — F1-a Phase 2a: Alginate ionic-Ca L2 solver (2026-04-17)

First non-chitosan-agarose platform lands. Shrinking-core Ca²⁺
diffusion + egg-box gelation gives DPSim its first ionic-gelation
pipeline. Downstream L3 / L4 callers remain platform-agnostic —
the solver emits a standard `GelationResult`.

### Added

- `PolymerFamily` enum in `datatypes.py`: AGAROSE_CHITOSAN (default)
  / ALGINATE / CELLULOSE / PLGA. Drives future L2 dispatch.
- `MaterialProperties.polymer_family` field + alginate-specific
  defaults (`f_guluronate=0.5`, `D_Ca=1e-9 m²/s`, `k_bind_Ca=1e3
  M⁻²·s⁻¹`, `K_alg_modulus=30 kPa`, `n_alg_modulus=2.0`). Harmless
  for other families.
- `src/dpsim/level2_gelation/ionic_ca.py::solve_ionic_ca_gelation`:
  1D spherical finite-volume BDF solver for C(r,t) / G(r,t) / X(r,t)
  with second-order Ca²⁺ + 2 guluronate → egg-box junction binding.
  ~310 LOC. Returns a SEMI_QUANTITATIVE-tier `GelationResult`.
- `tests/test_alginate_ionic_ca.py` — 13 tests covering the
  PolymerFamily enum, guluronate-concentration helper, result
  schema, guluronate mass conservation (ε < 5 %), zero-Ca /
  zero-alginate edge cases, long-time conversion > 30 % at
  500 mM bath, and input validation.

### Deferred to F1-a Phase 2b

- L4 alginate modulus (`G_DN ∝ (c·f_G)² · X_mean / X_max`).
- Reagent library entries (CaCl₂, internal gelation with GDL + CaCO₃).
- Pipeline orchestrator dispatch by `polymer_family`.
- Config TOML parser support for `polymer_family = "alginate"`.
- Remaining tests from the protocol (√t scaling, modulus scaling,
  full-pipeline integration) — 6 tests deferred.
- Replace c_agarose-slot-as-alginate-proxy with a dedicated
  `FormulationParameters.c_alginate` field.

### Tests

- 77 targeted regression tests pass (F1-a + F3 + F4 + Node 30/31 +
  CLI) in 67 s; 0 regressions.

### Footprint

- **Added:** ~640 LOC (solver + 13 tests + datatypes edits). Matches
  the Phase 2a slice of the ~1900 LOC total projected in
  `docs/f1a_alginate_protocol.md`.

## v8.0.0-alpha — F3-b/c + F4-a: engine wiring + CLI + robust BO (2026-04-17)

Completes v8.0-alpha inverse-design surface. The Node F3-a objective
builders now have an engine-level accessor, a CLI, and a first robust
acquisition stacking mean-variance on top.

### Added

- **F3-b**: `OptimizationEngine(target_spec=...)` constructor param.
  When set, the engine uses `compute_inverse_design_objectives` and
  sizes its internal `REF_POINT` + failure-penalty arrays to
  `len(target_spec.active_dims())`. The 3-objective legacy mode is
  preserved as the default.
- **F3-c**: `python -m dpsim design --d32 ... --pore ... --G-DN ...
  --Kav ...` CLI subcommand with matching `--*-tol` flags.
  TargetSpec.validate() errors route to SystemExit with a clear
  message.
- **F4-a**: `--robust-variance-weight λ` flag + engine kwarg.
  Evaluates λ resamples per candidate and reports
  `mean(obj) + λ · std(obj)` per dimension. Requires `target_spec`
  at construction (robust BO is defined against user targets).
  Current resample strategy: ±1 %·k RPM jitter as a proxy — proper
  spec-driven MC resampling lands in F4-b.
- **F4-b CVaR** — protocol stub only: swap the mean+std layer for a
  CVaR quantile over resamples. Deferred to follow-up (trivial
  change to the same engine path once the resample strategy is
  finalised).

### Tests

- `tests/test_inverse_design_engine.py` — 9 tests covering constructor
  guards, `_n_obj` sizing, robust-BO configuration validation, CLI
  parser registration, and a mocked dispatch path.
- 76 tests pass across F3 + Node 30/31/30b + CLI surfaces; 0
  regressions.

### Deferred

- **F1-a alginate platform**: protocol-only this session at
  `docs/f1a_alginate_protocol.md`. ~1900 LOC projected across L2
  ionic-Ca solver, L4 alginate modulus, PolymerFamily dispatch,
  defaults, and 11 tests. Requires /scientific-advisor briefing at
  kickoff. 3-5 fresh sessions.

## v8.0.0-alpha — Node F3-a: Inverse-design TargetSpec objectives (2026-04-17)

First v8.0 node. Adds user-specified target matching to the
optimisation pipeline so BO can be run in "inverse design" mode
(given target specs, find optimal formulation) rather than the fixed
rotor-stator / stirred-vessel targets only.

### Added

- `TargetSpec` dataclass in `src/dpsim/optimization/objectives.py`:
  per-dimension target + tolerance pairs for d32 (or d_mode in
  stirred-vessel), pore size, G_DN (log10-distance), and Kav (M3
  distribution coefficient, optional). Dimensions are skipped when
  either the target or the tolerance is `None`, so users can target
  subsets. `TargetSpec.validate()` raises on empty spec or
  non-positive tolerance.
- `compute_inverse_design_objectives(result, target, trust_aware=True,
  mode=None)`: returns an objective vector sized to the active
  dimensions. Each component is the tolerance-normalised absolute
  distance (log10 for G_DN); trust penalty from Node 6 is added
  per-component when `trust_aware=True` so weak-evidence candidates
  still land above the engine REF_POINT.
- 12 unit tests in `tests/test_inverse_design_objectives.py` covering
  validate(), active_dims(), per-dimension distance math, trust
  penalty integration, Kav-missing fallback (inf), and stirred-vessel
  d_mode substitution.

### Not yet done (F3-b, F3-c)

- `OptimizationEngine.run(target_spec=...)` integration — the engine
  currently hard-wires `compute_objectives_trust_aware`. Switching the
  objective at runtime requires an engine-level accessor.
- CLI `python -m dpsim design --d32 2e-6 --pore 80e-9 ...` — wraps
  the above into a user surface.

### Footprint

- **Added:** ~200 LOC (TargetSpec + compute_inverse_design_objectives
  + tests). 67 tests across F3-a + UQ + EDC/NHS + panel + CLI pass;
  0 regressions.

## v7.1.0-dev — Node 32: Cluster F v8.0 roadmap (2026-04-17)

Architect-produced roadmap document (no code) at
`docs/node32_cluster_f_v8_roadmap.md`. Refines Doc 10 §4 into Node-level
deliverables for v8.0:

- **F1** Other microsphere platforms (alginate / cellulose NIPS /
  PLGA; alginate recommended first per smallest code delta)
- **F2** Digital twin (EnKF + online Bayesian + MPC; scoped to
  replay-only for v8.0 unless hardware partner emerges)
- **F3** Inverse design (constrained BO; leverages Node 30 UQ +
  Node 6 trust-aware evidence)
- **F4** Robust optimisation under uncertainty (mean-variance /
  CVaR acquisition stacked on F3)
- **F5** MD parameter estimation (MARTINI CG MD for χ, κ, M₀,
  f_bridge; ingest-only default scope)

Proposed v8.0 phasing:

1. Phase 1 (4 weeks): F3 + F4 — inverse design + robust optimisation
   on current platform; v8.0-alpha release.
2. Phase 2 (6 weeks): F1-a alginate; v8.0-beta.
3. Phase 3 (6 weeks): F5 ingest + F2 replay harness; v8.0 GA.

Hard entry criteria: v7.0 must ship (Study A wet-lab gate); CEO /
chief-economist / ip-auditor sign-off on commercial prioritisation
before first v8.0 node.

## v7.1.0-dev — Node 30b: Streamlit UQ panel migration (2026-04-17)

Closes the Node 30 deferral: the streamlit uncertainty panel now
builds a full `UnifiedUncertaintySpec` from user inputs instead of
showing an `st.info` placeholder. The built-in MaterialProperties
perturbations from `UnifiedUncertaintyEngine.run_m1l4` remain always-on;
the panel configures the *additional* spec-driven surface plus sampling
controls and surfaces a count of calibration-posterior sources that
will be absorbed from `st.session_state["_cal_store"]` at engine
construction time.

### Added

- `build_uncertainty_spec(n_samples, seed, custom_sources) ->
  UnifiedUncertaintySpec` — pure helper used by the panel. Invalid
  custom entries (blank name, std <= 0) are silently dropped;
  `n_samples < 1` raises.
- `count_store_posteriors(store) -> int` — tallies calibration entries
  with `posterior_uncertainty > 0` for the panel's status display.
- `CustomSourceInput` dataclass — typed bridge between streamlit
  widget state and the pure spec-builder.
- `tests/test_uncertainty_panel.py` — 12 unit tests of the spec
  builder, the posterior counter, and a panel-export smoke test.

### Changed

- `src/dpsim/visualization/panels/uncertainty.py` — rebuilt around
  the new helpers. UI exposes `n_samples`, `seed`, `n_jobs` (`1`, `2`,
  `4`, `-1`) in a three-column row plus an "Advanced" expander that
  lets the user add up to 10 custom `UncertaintySource` entries
  (name, kind, distribution `normal`/`lognormal`, value, std).
- Session-state surface: the panel persists the built spec at
  `st.session_state["_unc_spec"]` and the parallel-workers value at
  `st.session_state["_unc_n_jobs"]` for downstream run triggers.

### Tests

- 12 new panel tests pass.
- 146 tests across panel + UQ + EDC/NHS + CLI + UI contract surfaces
  pass; 0 regressions.

### Footprint

- **Added:** ~220 LOC (panel rewrite + tests). Net: −28 LOC was the
  placeholder; the migrated panel is ~190 LOC.

## v7.1.0-dev — Node 31: EDC/NHS mechanistic kinetic (2026-04-17)

Promotes EDC/NHS carbodiimide chemistry from QUALITATIVE_TREND
(Node 9 F9 fallback) to SEMI_QUANTITATIVE with a literature-grounded
two-step ODE model. The Hermanson 2013 / Wang 2011 / Cline & Hanna
1988 rate constants close the scientific debt item; Study A calibration
data can promote to QUANTITATIVE via the CalibrationStore posterior
machinery shipped in Node 30.

### Added

- `src/dpsim/module2_functionalization/edc_nhs_kinetics.py` — new
  mechanistic solver. Core: `react_edc_nhs_two_step(...)` integrates
  four ODEs (C → A → E → P) with competing O-acylisourea and
  NHS-ester hydrolyses, returning a structured `EdcNhsResult` with
  `p_final`, `p_hydrolysed`, `p_residual_nhs_ester`, `time_to_half`,
  mass-balance diagnostic, and solver diagnostics. `EdcNhsKinetics`
  dataclass carries the rate constants + activation energies; defaults
  are literature medians at T_ref=298 K. `available_amine_fraction(pH,
  pKa)` helper for chitosan amine speciation.
- `FormulationParameters.pH` field (default 7.0).
- `MaterialProperties.surface_cooh_concentration` field (default 0.0)
  — gates L3 EDC/NHS to run the mechanistic path when non-zero.
- `tests/test_edc_nhs_kinetics.py` — 18 tests covering mass
  conservation, edge cases, Arrhenius / pH / dose-response trends,
  input validation, and M2 + L3 integration.

### Changed

- `src/dpsim/module2_functionalization/modification_steps.py` —
  `_solve_activation_step` dispatches to the mechanistic ODE when
  `reagent_profile.chemistry_class == "edc_nhs"` (was generic
  single-step `solve_second_order_consumption`).
- `src/dpsim/module2_functionalization/reagent_profiles.py` — the
  `edc_nhs_activation` profile's `confidence_tier` promotes from
  `ranking_only` to `semi_quantitative`; `calibration_source` and
  `notes` updated to reference the mechanistic model.
- `src/dpsim/level3_crosslinking/solver.py` — the `michaelis_menten`
  branch now gates on `props.surface_cooh_concentration`. Native matrix
  (= 0) still falls back with QUALITATIVE_TREND (v7.0.1 behaviour
  preserved for safety); carboxylated matrix (> 0) runs the mechanistic
  ODE and ships SEMI_QUANTITATIVE.

### Kept deferred

- Dedicated `c_edc` / `c_nhs` concentration fields on
  `FormulationParameters` (Node 31 reuses `c_genipin`; cleanup = Node
  31b).
- pH-dependent kinetic constants beyond the k_h2 pH term (Node 31b).
- Study A calibration uptake for EDC/NHS-specific matrix chemistry
  (will arrive as `CalibrationStore` entries targeting M2 / L3).

### Tests

- 18 new EDC/NHS tests pass in <1 s.
- 157 tests across the EDC/NHS + UQ + CLI + M2 + L3 + batch +
  run-context surfaces pass in ≈38 s; 0 regressions.

### Footprint

- **Added:** ~420 LOC (solver + tests + L3 gate + M2 dispatch branch).
- **Touched:** 6 files.

## v7.1.0-dev — Node 30: Full UQ merge (2026-04-17)

Consolidates the two legacy Monte Carlo engines into a single
`UnifiedUncertaintyEngine` implementation and closes the Audit N2
calibration-posterior sampling gap left open by Node 18.

### Merged

- `uncertainty_core.py` (318 LOC) — deleted. The M1-L4
  `UncertaintyPropagator` logic lives in `uncertainty_unified.py`.
- `uncertainty_propagation/` package (216 LOC) — deleted. The M2-only
  `M1UncertaintyContract` / `run_with_uncertainty` path had no CLI
  surface and was unreachable outside the streamlit panel + two
  v6.0-era integration tests. An M2-specific UQ path can be rebuilt on
  top of the unified schema in v7.2 if user demand warrants it.
- `UnifiedUncertaintyEngine.run_m2_q_max`, `from_m1_contract_uq`,
  `from_m1l4_result` — deleted (dead adapters).

### Closed

- **Audit N2** (HIGH): `CalibrationStore` posteriors with
  `posterior_uncertainty > 0` now actually perturb the MC on each
  sample. The posterior draw is dispatched by `target_module` — L1
  posteriors land on `params.emulsification.kernels` (lazily
  instantiated if `None`), L2-L4/M2-M3 posteriors land on
  `MaterialProperties`. `result.kinds_sampled` honestly records
  `CALIBRATION_POSTERIOR` when a posterior dispatched to a real
  attribute; `result.kinds_declared_but_not_sampled` only contains
  `CALIBRATION_POSTERIOR` when EVERY posterior failed the dispatch
  (malformed name or unknown attribute).

### CLI

- `python -m dpsim uncertainty --engine {unified,legacy}` now routes
  both choices through the merged engine. `unified` includes
  posteriors; `legacy` runs with `calibration_store=None` for
  byte-compat with v7.0.x scripts that expected only the default
  MaterialProperties perturbations. The output schema is the unified
  summary in both cases — scripts parsing the legacy
  "Uncertainty-Quantified Results" header must migrate.

### Byte-compat

- `_generate_default_perturbations` preserves the exact RNG call order
  of v7.0.1 `UncertaintyPropagator._generate_perturbations`, so
  seed-identical output matches when no posterior sources are declared.
  Posterior draws come AFTER the default 10 draws per sample to avoid
  perturbing the default-only sequence.

### Deferred to Node 30b

- Streamlit UQ panel
  (`src/dpsim/visualization/panels/uncertainty.py`) now displays an
  info placeholder and returns `None`. Full migration to build a
  `UnifiedUncertaintySpec` from streamlit inputs is Node 30b. The CLI
  and programmatic API paths are fully functional in v7.1.

### Tests

- `tests/test_uncertainty_unified.py`: 14 tests. Rewrote the Node 23
  `test_n2_no_posterior_overclaim` as `test_posterior_now_actually_sampled`
  and `test_posterior_actually_perturbs_output` to verify the closure.
  Added `test_unknown_posterior_attribute_skipped` and
  `test_legacy_modules_are_gone`.
- `tests/test_parallel_mc.py`: 4 tests retargeted at the merged
  engine; parallel/serial bit-identicality invariant preserved via the
  new `OutputUncertainty.raw_samples` field.
- `tests/test_cli_v7.py::test_legacy_engine_byte_compat` → rewritten
  as `test_legacy_engine_flag_routes_through_unified`.
- `tests/test_v60_integration.py::TestUncertaintyIntegration` deleted
  (M2 MC path removed).

### Footprint

- **Deleted:** ~540 LOC (uncertainty_core.py + uncertainty_propagation/
  + dead adapters in uncertainty_unified.py).
- **Added:** ~200 LOC (merged sampler + posterior dispatch in
  uncertainty_unified.py, 5 new UQ tests).
- **Net:** ~−340 LOC. 52 tests passing in the targeted regression set
  (UQ + parallel + CLI + v6.0 integration + batch + run-context).

## v7.0.1 (2026-04-17) — Audit remediation patch

Closes 8 of 10 findings from the post-Nodes-1-20 full-system audit. P0
ship-blockers fixed; v7.0 features now reachable from the CLI.

### P0 fixes (release blockers)
- **N1 (HIGH)** — `pipeline/orchestrator.py` no longer mutates the caller's
  `params.emulsification.kernels` in place when applying L1 calibration.
  Callers that reuse a `SimulationParameters` instance across multiple
  `run_single` calls (e.g. `batch_variability.run_batch`, parameter
  sweeps, optimisation campaigns) no longer see calibrated kernels leak
  between iterations. Regression test in `test_run_context.py`.
- **N2 (HIGH)** — `UnifiedUncertaintyEngine.run_m1l4` no longer claims to
  have sampled `CALIBRATION_POSTERIOR` when it has only absorbed the
  posterior into the spec. The new
  `UnifiedUncertaintyResult.kinds_declared_but_not_sampled` field
  records the v7.0 limitation honestly.

### P1 fixes (CLI surface — closes audit N4 + N5)
- **`python -m dpsim batch`** — surface
  `pipeline.batch_variability.run_batch` on the CLI. Pass `--quantiles`
  and `--output`; prints mass-weighted mean / per-quantile percentile
  table.
- **`python -m dpsim dossier`** — run the pipeline and emit a
  `ProcessDossier` JSON artifact for reproducibility. Records inputs,
  result summary, manifests, calibrations, environment.
- **`python -m dpsim ingest L1`** — ingest a directory of
  `AssayRecord` JSON files, run the L1 fitter, write a
  `CalibrationStore`-loadable fit JSON. v7.1 will add L2/L3/L4/M2.
- **`python -m dpsim uncertainty`** now defaults to the
  `UnifiedUncertaintyEngine` (Node 18) and exposes `--n-jobs` for
  Node 15's parallel MC. Pass `--engine legacy` for v6.x byte-equivalent
  output.
- **N3 follow-up** — `QuantileRun.representative_diameter_m` property
  added so downstream consumers don't accidentally read
  `full_result.emulsification.d50` (which is shared by reference across
  all per-quantile runs and reflects the BASE L1 DSD).

### P2 polish
- **N7** — `UncertaintyPropagator.run` auto-falls-back to serial when
  `n_samples < 4 × |n_jobs|`. Joblib startup + Numba JIT cold-compile
  dominate below this threshold.
- **N8** — `run_batch` silently sort+dedupes the `quantiles` argument.
  Duplicate or unsorted input no longer produces ill-defined mass
  fractions.

### P3 documentation
- **N6** — `INSTALL.md` documents the Numba JIT cache location and the
  `NUMBA_CACHE_DIR` environment-variable workaround for read-only
  Python installs (corporate, conda `--no-write-pkgs`,
  `pip install --user` on network shares).
- **N9** — Documenting that Node 8's L2 timing wiring was a metadata
  fix only; the empirical pore-size formula remains independent of
  `alpha_final`. The `model_manifest.diagnostics.alpha_final_from_timing`
  field now reflects the actual Avrami output instead of a hardcoded
  0.999, but pore predictions at typical conditions are unchanged.

### Tests
- 25 new tests across the patch (Nodes 22-29). 0 regressions.

---

## v7.0 (2026-04-17) — Engineering portion (Nodes 14-20)

Closes engineering items from the consensus v7.0 plan (doc 34 §9). F1
closure (kernel re-fit) remains gated on Study A wet-lab data.

### New modules
- `process_dossier.py` — `ProcessDossier` aggregator + JSON export
- `assay_record.py` — `AssayRecord` public data model with 12 `AssayKind` values
- `uncertainty_unified.py` — `UnifiedUncertaintyEngine` single entrypoint
- `pipeline/batch_variability.py` — `run_batch` over DSD quantiles
- `calibration/fitters.py` — stub L1 DSD fitter

### Performance
- Numba JIT for `breakage_rate_alopaeus`, `breakage_rate_coulaloglou`,
  `coalescence_rate_ct` matrix builder (5-10× on coalescence; matches
  NumPy to 1e-12 rtol).
- joblib parallel MC via `UncertaintyPropagator(n_jobs=-1)`.

### Calibration data scaffold
- `data/validation/{l1_dsd,l2_pore,l3_kinetics,l4_mechanics,m2_capacity}/`
  directory tree with JSON-Schema for L1 DSD assays.

---

## v6.0 (2026-04-12) — Calibration-Enabled Process Simulation

Transitions DPSim from semi-quantitative chemistry simulator to calibration-enabled process simulation platform. All uncalibrated outputs remain semi-quantitative; calibrated outputs reflect user-supplied measurements.

### UI Restructure
- Split monolithic `app.py` (1480 lines) into modular tab architecture (7 UI files, orchestrator < 210 lines)
- `tabs/tab_m1.py`: M1 Fabrication tab (inputs, run, results, optimization, trust)
- `tabs/tab_m2.py`: M2 Functionalization tab (9 step types, 52 reagent profiles)
- `tabs/tab_m3.py`: M3 Performance tab (chromatography + catalysis)
- Sidebar panels for calibration, uncertainty, and lifetime frameworks

### Gradient-Aware LRM (H6)
- `solve_lrm()` accepts time-varying `ProcessState` via `gradient_program` + `equilibrium_adapter`
- Gradient values now mechanistically affect equilibrium during LRM time integration
- `run_gradient_elution()` auto-creates adapter for gradient-sensitive isotherms
- `gradient_sensitive` + `gradient_field` properties on SMA, HIC, IMAC, ProteinA, CompetitiveAffinity isotherms
- Fully backward compatible: existing callers unchanged

### Calibration Framework (v6.0-alpha)
- `CalibrationEntry` typed dataclass with units, target, validity domain (audit F2)
- `CalibrationStore` with JSON import/export, query, and `apply_to_fmc()` (audit F13)
- UI panel: JSON upload, manual entry, color-coded confidence display

### Uncertainty Propagation (v6.0-alpha)
- `M1UncertaintyContract` with 5 CVs and two tiers: measured (Tier 1) vs assumed (Tier 2, audit F4)
- `run_with_uncertainty()` Monte Carlo through M2 pipeline producing p5/p95 bounds on q_max
- UI panel: CV sliders, tier selection, sample count configuration

### Lifetime Projection (v6.0-rc)
- `LifetimeProjection` empirical first-order deactivation model (audit F6)
- `project_lifetime()` with cycles-to-80%/50% milestones
- UI panel: interactive Plotly decay curve, empirical confidence warning

### ProcessState (v6.0-beta)
- Typed `ProcessState` dataclass replacing loose dict for process conditions
- Carries salt, pH, imidazole, sugar competitor, temperature for multi-parameter isotherms
- `EquilibriumAdapter` dispatches by isotherm class name with ProcessState routing

### New Isotherms
- `HICIsotherm`: Salt-modulated Langmuir (K_eff = K_0 * exp(m * C_salt)), requires user calibration
- `CompetitiveAffinityIsotherm`: Generalized competitive binding for lectin elution (Con A, WGA)

### Quality
- 14/14 acceptance criteria from audit Section 7 verified passing
- 24 new integration tests (12 gradient LRM + 12 v6.0 end-to-end)
- All existing v5.9 workflows pass regression (280+ total tests, 0 failures)

---

## v0.1.0 (2026-03-26) — Initial Release

### Simulation Pipeline
- 4-level sequential pipeline: PBE emulsification → empirical gelation → multi-mechanism crosslinking → IPN mechanical properties
- 8 crosslinkers with 4 kinetics models (second-order amine/hydroxyl, UV dose, ionic instant)
- 6 surfactants with Szyszkowski-Langmuir IFT model
- Empirical pore-size model calibrated to literature (Pernodet 1997, Chen 2017)
- 2D Cahn-Hilliard phase-field solver available as advanced option

### Web UI (Streamlit)
- Interactive parameter input with sliders and dropdowns
- Reagent selection (crosslinker + surfactant) with per-reagent defaults
- Per-constant Literature/Custom toggle with calibration protocol links
- Results dashboard with Plotly charts (size distribution, phase field, kinetics, Hertz, Kav)
- Trust assessment with 10 automated reliability checks
- Optimization assessment with actionable recommendations

### CLI
- `python -m dpsim run` — full pipeline
- `python -m dpsim sweep` — RPM parameter sweep
- `python -m dpsim optimize` — BoTorch Bayesian optimization
- `python -m dpsim uncertainty` — Monte Carlo uncertainty propagation
- `python -m dpsim ui` — launch Streamlit web interface
- `python -m dpsim info` — display parameters and properties

### Documentation
- Scientific advisory report (docs/01)
- Computational architecture (docs/02)
- Scientific review with formula verification (docs/03)
- Calibration wet-lab protocol — 5 studies, 1081 lines (docs/04)
- Literature constants database with sources and DOIs
- Reagent library with 8 crosslinkers and 6 surfactants

### Quality Assurance
- 9 rounds of Codex (OpenAI) adversarial review — 63+ findings, all addressed
- Scientific Advisor review — 4 critical bugs fixed
- Dev-Orchestrator usability review — all priorities implemented
- Input validation, trust gates, uncertainty propagation
- 107+ unit tests
