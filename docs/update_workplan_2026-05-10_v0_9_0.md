# Joint work plan — v0.8.6 → v0.8.7 → v0.9.0

> **Driving inputs**: `docs/handover/AUDIT_v0_8_5_e2e_phase1_scientific.md`, `..._phase2_user.md`, `..._phase3_architecture.md` (all written 2026-05-10).
> **Authors**: /scientific-advisor + /dev-orchestrator + /architect (joint engagement).
> **Type**: three-stage remediation roadmap. v0.8.6 closes the critical wiring breaks; v0.8.7 exposes orphan backends; v0.9.0 is the maturation milestone.
> **Versioning policy**: patch bumps for incremental wiring/exposure work; minor bump v0.9.0 reserved for the maturity plateau (per the project versioning rule).

---

## §0 — Reconciliation

The Phase 1–3 audits surface 18 defects (A-1 → A-18 architectural; S-1 → S-20 scientific; U-1 → U-30 practitioner). They cluster into three release horizons and one explicitly out-of-scope set.

| Defect class | Defects | Release |
|---|---|---|
| **CRITICAL — false v0.8.4 closure (widgets defined but unmounted)** | A-1/S-1/U-8, A-2/S-2/U-9, A-3/S-3/U-10, A-4/S-4 | **v0.8.6** |
| **HIGH — orphan backend modules** | A-5/S-6/U-13, A-6/S-7/U-20, A-7/S-8, A-8/S-9, A-9/S-5 | **v0.8.7** |
| **MEDIUM/HIGH — maturation (UX, tier-consistency, IA, calibration discipline)** | A-10..A-18, S-10..S-20 (subset), U-1..U-30 (subset) | **v0.9.0** |
| **OUT OF SCOPE** | live AKTA UNICORN (ADR-008 hardware), MCMC inverse promotion (ADR-010 dataset-bound), wet-lab K_geom calibration (user-side) | — |

The total work is large. Sequencing tightly so each release closes a coherent operator-facing promise. After v0.8.6 the dashboard becomes *honest* (the visible inputs drive the simulation); after v0.8.7 it becomes *complete* (the README's promises are structurally reachable); after v0.9.0 it becomes *wet-lab-credible* (decision-graded, IA-organised, exportable, comparable).

---

## §1 — v0.8.6 — Critical wiring fixes

**Theme**: turn the v0.8.4 widgets that were defined-but-unmounted into actual production paths. No new science. No new backend. **All five W-items are pure wiring.** Any user pressing *Run* after v0.8.6 sees their actual mobile phase + isotherm choice drive the simulation.

### 1.1 W-item ledger (continuing from W-068)

| W-ID | Severity | Title | Files | Resolves |
|---|---|---|---|---|
| W-069 | CRITICAL | Mount `render_mobile_phase_widget` in M3 input | `tabs/tab_m3.py` (input section) + `tabs/m3/mobile_phase_section.py` NEW | A-1 / S-1 / U-8 |
| W-070 | CRITICAL | Mount `render_isotherm_widget` in M3 input | `tabs/tab_m3.py` + new section | A-2 / S-2 / U-9 |
| W-071 | CRITICAL | Mount `render_tier_banner` at app top-of-page | `visualization/app.py` | A-3 / S-3 / U-10 |
| W-072 | CRITICAL | Thread `mobile_phase` and `isotherm_spec` UI → orchestrator | `ui_workflow.py` + `lifecycle/orchestrator.py:run()` (add `isotherm_spec=` kwarg) + `module3_performance/orchestrator.py:247` | A-4 / S-4 |
| W-073 | HIGH | Regression tests + AST gate extension | NEW `tests/visualization/test_widget_mounting.py` (asserts every `render_*` defined under panels/ has at least one production caller) | gate-42, gate-43 |

### 1.2 Sequenced batched plan

| Batch | W-IDs | Modules | Model | Acceptance criteria |
|---|---|---|---|---|
| **B-4a** | W-069 | NEW `tabs/m3/mobile_phase_section.py` ≤ 60 LOC; mount in `tab_m3.py` input section; persist to `st.session_state["m3_mobile_phase"]`. | Sonnet | Widget renders above the Run button; user input writes to `st.session_state["m3_mobile_phase"]`; default-on-first-load is `MobilePhase()`. |
| **B-4b** | W-070 | NEW `tabs/m3/isotherm_section.py` ≤ 60 LOC; mount the widget; persist to `st.session_state["m3_isotherm_spec"]`. | Sonnet | Widget shows the family-aware default; user can override; the chosen `IsothermSpec` is in session_state. |
| **B-4c** | W-071 | Mount `render_tier_banner(get_worst_tier_from_session())` at the top of `app.py`. | Haiku | Banner renders on every page; colour reflects the worst stage tier currently in `lifecycle_result`. |
| **B-4d KEYSTONE** | W-072 | Thread `mobile_phase` + `isotherm_spec` from `st.session_state` through `ui_workflow.render_lifecycle_run_panel` → `DownstreamProcessOrchestrator.run(mobile_phase=, isotherm_spec=)` → `module3_performance/orchestrator.py` `select_isotherm_from_fmc` override. | **Opus** | A user-selected isotherm class actually changes the breakthrough curve. A user-selected mobile phase changes the pressure envelope. Round-trip integration test. |
| **B-4e** | W-073 | NEW `tests/visualization/test_widget_mounting.py` — AST scanner that walks `panels/` and `shell/`, finds every `def render_*`, then walks `tabs/` + `app.py` + `shell/` for callers; fails if any `render_*` has zero production callers (excluding test files). | Sonnet | Test catches A-1, A-2, A-3 if reverted. Existing widgets pass. |
| **B-4f** | release | pyproject.toml + `__init__.py` 0.8.5 → 0.8.6; CHANGELOG; HANDOVER. | Haiku | Tag + GitHub release with installer + portable ZIP. |

### 1.3 Token-economy

* **Total**: ~25 K tokens. Single-session feasible at GREEN context.
* **One mid-cycle compression** between B-4d and B-4e (B-4d is the largest single batch — Opus review of the orchestrator threading).
* **`/qa-only`** invocation between B-4d and B-4e.
* **`/design-review`** invocation against the rendered banner (tier_banner.py) once mounted.

### 1.4 Validation gates added (42 → 47)

| Gate | Description |
|---|---|
| 42 | Mobile-phase widget renders in M3 input; user value is persisted to session_state. |
| 43 | Isotherm widget renders in M3 input; user value is persisted to session_state. |
| 44 | Tier banner renders at app top-of-page on every stage. |
| 45 | User-selected mobile phase changes the pre-flight envelope's μ resolution (verified by integration test that compares envelope under PBS vs 1M NaCl + 10 % glycerol). |
| 46 | User-selected isotherm class changes the M3 breakthrough curve (verified by integration test against the LRM with bare Langmuir vs SaltModulatedSMA). |
| 47 | New AST gate: every `def render_*` defined in `panels/` or `shell/` has ≥ 1 production caller in `tabs/` or `app.py` or `shell/` (excluding tests). |

### 1.5 Definition of "v0.8.6 ships"

> v0.8.6 ships when gates 42–47 pass + the v0.8.5 gate floor (1–41) is regressed clean. The dashboard is then *honest*: the visible inputs drive the simulation. The CHANGELOG entries for v0.8.4 defects C1, C2, W-1 are now structurally accurate.

---

## §2 — v0.8.7 — Orphan exposure

**Theme**: every backend module the README promises is reachable from the dashboard. **No new science** beyond exposing what already exists.

### 2.1 W-item ledger

| W-ID | Severity | Title | Files | Resolves |
|---|---|---|---|---|
| W-074 | HIGH | Detector traces sub-section in M3 results | NEW `tabs/m3/detector_traces.py`; reads run effluent → calls `detection/{uv,fluorescence,conductivity,ms}.py` | A-5 / S-6 / U-13 |
| W-075 | HIGH | OptimizationEngine top-level UI tab | NEW `tabs/tab_optimization.py` ~250 LOC; new top-level stage in `app.py` navigation | A-6 / S-7 / U-20 |
| W-076 | MEDIUM | `MonitorSource` Protocol UI dropdown | refactor `tab_m3_monitor.py` to consume `MonitorSource`; add CSV/Simulated/Null source dropdown | A-7 / S-8 |
| W-077 | MEDIUM | Multi-step coupled MC radio in forward MC panel | extend `tabs/calibration/forward_mc.py` with single-step / multi-step toggle calling `monte_carlo_step_program` | A-8 / S-9 |
| W-078 | HIGH | Bare isotherms (HIC, ProteinA) in `IsothermChoice` | extend `panels/isotherm_selector.py::IsothermChoice` with `HIC` + `PROTEIN_A`; add sub-forms; update AST gate enum coverage | A-9 / S-5 (subset) |

### 2.2 Sequenced batched plan

| Batch | W-IDs | Modules | Model | Acceptance criteria |
|---|---|---|---|---|
| **B-5a** | W-078 | Extend `IsothermChoice`; add 2 sub-forms; update family-aware default routing (AGAROSE_CHITOSAN → PROTEIN_A; hydrophobic ligand families → HIC). | Sonnet | User can pick HIC and ProteinA; chosen class threads through W-072's plumbing into the breakthrough curve. |
| **B-5b** | W-074 | NEW `tabs/m3/detector_traces.py`; mount as a sub-section in M3 results page; render UV / conductivity / fluorescence overlays alongside breakthrough plot. | Sonnet | After a run completes, detector traces render. CSV export available. |
| **B-5c KEYSTONE** | W-075 | NEW `tabs/tab_optimization.py`. Inputs: target capacity / sharpness / pressure budget. Outputs: recommended geometry / Q / ligand density bands. Tier output as SEMI_QUANTITATIVE pending wet-lab calibration. | **Opus** | User can run BO from dashboard; result is decision-graded; convergence diagnostics visible. |
| **B-5d** | W-076 | Refactor `tab_m3_monitor.py` to consume `MonitorSource`; add source dropdown. Reserve `unicorn_socket` slot disabled with v0.9 deferral note. | Sonnet | CSV / Simulated / Null modes work. Live socket slot disabled with explanatory caption. |
| **B-5e** | W-077 | Extend forward MC panel with multi-step radio; wire `monte_carlo_step_program`. | Sonnet | User can run multi-step coupled MC; result panel shows correlated step-to-step uncertainty. |
| **B-5f** | release | Version bump + CHANGELOG + HANDOVER. | Haiku | Tag v0.8.7 + GitHub release + artefacts. |

### 2.3 Validation gates added (48 → 53)

* **48** HIC + ProteinA selectable via the isotherm widget; family-aware defaults route correctly.
* **49** Detector traces render after every M3 run; UV / conductivity / fluorescence visible.
* **50** OptimizationEngine reachable from a top-level tab; canonical 3-input case completes.
* **51** Streaming monitor source dropdown offers CSV / Simulated / Null modes.
* **52** Multi-step coupled MC reachable from forward MC panel; result reflects shared draws.
* **53** AST gate covers extended `IsothermChoice` (HIC + PROTEIN_A).

---

## §3 — v0.9.0 — Maturation milestone

**Theme**: turn DPSim from *honest + complete* into *wet-lab-credible*. Decision-graded, IA-organised, exportable, comparable. This is the minor bump.

### 3.1 W-item ledger

Grouped by theme.

#### 3.1.1 Decision-grade consistency (A-14, A-15, S-10)

| W-ID | Severity | Title |
|---|---|---|
| W-079 | MEDIUM | Pressure indicator routes through `render_decision_grade_annotation` |
| W-080 | MEDIUM | Replace bare `st.metric` calls with `render_metric` across M2 + M3 result surfaces |
| W-081 | MEDIUM | Tier-routing CI gate — every numeric display in `tabs/` must use `render_metric` (parallel to AST gate) |

#### 3.1.2 Pre-flight envelope relocation (A-12, A-17, S-11, U-11)

| W-ID | Severity | Title |
|---|---|---|
| W-082 | HIGH | Pre-flight envelope panel relocated to M3 *configure* section (above Run); post-run panel becomes audit-trail |
| W-083 | MEDIUM | Remove parallel pre-flight compute at `tab_m3.py:1051`; single source-of-truth via session_state |

#### 3.1.3 Workflow + IA reorganisation (A-13, A-16, S-13, U-7, U-18)

| W-ID | Severity | Title |
|---|---|---|
| W-084 | MEDIUM | M3 geometry inputs write through to recipe object; recipe-resolved geometry rendered as read-only confirmation |
| W-085 | LOW | Multi-column series builder hoisted out of Calibration into top-level *Series Design* |
| W-086 | MEDIUM | M2 → M3 chain confirmation: render *"your M3 will use ligand density X / surface area Y from the M2 you ran at HH:MM"* |
| W-087 | LOW | Refactor `tab_m3.py` (1198 LOC) into `tabs/m3/` directory with ≤ 250 LOC per file |

#### 3.1.4 Calibration discipline (S-12, U-16, U-19)

| W-ID | Severity | Title |
|---|---|---|
| W-088 | HIGH | Inverse Bayesian fit: input-time blocker if measurements < 8 (configurable threshold per ADR-010) |
| W-089 | HIGH | Spreadsheet → calibration store import (.xlsx, .csv); column-mapping wizard |
| W-090 | MEDIUM | Per-parameter "what experiment promotes me?" surfaced inline (links into `docs/04_calibration_protocol.md` study sections) |

#### 3.1.5 Operator affordances (U-12, U-23, U-25, U-26, U-27)

| W-ID | Severity | Title |
|---|---|---|
| W-091 | HIGH | "Set my flow rate to Q_recommended" button on the pressure indicator (RED state) |
| W-092 | MEDIUM | RecoveryAction labels become clickable controls in the streaming monitor |
| W-093 | HIGH | Save-session / load-previous-run via JSON snapshot; lives under sidebar *Sessions* |
| W-094 | HIGH | SOP / wet-lab procedure PDF export — turns recipe + envelope + isotherm + calibration store into a bench-ready procedure document |
| W-095 | MEDIUM | Run-vs-run comparison overlay (configure A vs B in side-by-side) |

#### 3.1.6 Unit standardisation (S-14, U-24)

| W-ID | Severity | Title |
|---|---|---|
| W-096 | HIGH | Unit standardisation pass: every Q in **mL/min**, every ΔP in **kPa**, every concentration in **mM** at the user-input boundary; SI conversion at backend boundary via the existing B-2c helpers |

#### 3.1.7 First-run + exemplars (U-1, U-2, S-15, S-19)

| W-ID | Severity | Title |
|---|---|---|
| W-097 | HIGH | First-run example loader: 3 canonical recipes (Protein-A capture, IEX polish, IMAC) one-click loadable |
| W-098 | MEDIUM | "Scientific Mode" radio gets a clear consequence-on-rerun caption |
| W-099 | MEDIUM | End-to-end *screen → calibrate → tighten* guided workflow tour (uses the canonical recipes) |

#### 3.1.8 Predicted-vs-measured + state-machine cleanup (A-10, A-11, U-22)

| W-ID | Severity | Title |
|---|---|---|
| W-100 | HIGH | Streaming monitor overlays predicted ΔP from the active envelope alongside measured trace |
| W-101 | LOW | Locate writer for `_m3_column_for_envelope`; if absent, add it and document the contract |
| W-102 | LOW | Remove orphan write of `m3_latest_state` or wire into the tier banner |

### 3.2 Batched plan (high-level — too many W-items for one table)

Three sub-bundles:

* **Bundle X — decision-grade + envelope relocation** (W-079 → W-083): one ~2-week sub-cycle. All Sonnet.
* **Bundle Y — calibration + operator affordances** (W-088 → W-095): one ~3-week sub-cycle. W-094 (SOP export) is Opus due to the document-generation complexity.
* **Bundle Z — unit pass + first-run + IA refactor** (W-096 → W-102 + W-084..W-087): one ~3-week sub-cycle. W-087 (tab_m3.py refactor) is Opus due to risk of regression.

Per-bundle handover; one milestone handover at end of v0.9.0; final release handover.

### 3.3 Validation gates added (54 → 70+)

The full gate list will be in the v0.9.0 release plan; high-level themes:

* Decision-grade routing universality (54).
* Pre-flight envelope visible *before* Run (55).
* M2 → M3 chain confirmation visible (56).
* Inverse Bayesian input-time blocker (57).
* Spreadsheet calibration import (58).
* Save-session / load-session (59).
* SOP PDF export (60).
* Run-vs-run comparison (61).
* Unit standardisation passing the unit-audit gate (62).
* First-run example loader (63).
* Predicted-vs-measured overlay (64).
* AST + tier-routing CI gates extended (65, 66).

### 3.4 Definition of "v0.9.0 ships"

> v0.9.0 is the *wet-lab-credible* release. A demanding bench user can:
> * Pick their actual mobile phase + isotherm class + reagents (v0.8.6 closure).
> * See the decision tier on every number (v0.9.0 W-079..W-081).
> * Run optimization to design a target-driven protocol (v0.8.7 W-075).
> * Run forward + inverse Bayesian + multi-step coupled MC (v0.8.7 W-077).
> * Compare predicted-vs-measured pressure traces (v0.9.0 W-100).
> * Save / load / compare sessions (v0.9.0 W-093, W-095).
> * Export a wet-lab SOP PDF (v0.9.0 W-094).
> * Promote tier from SEMI_QUANTITATIVE to CALIBRATED_LOCAL via spreadsheet import (v0.9.0 W-089).
> * Land at a first-run example (v0.9.0 W-097).
>
> **The v0.9 maturity plateau** then has only the three durable v0.9-deferred items remaining (live AKTA UNICORN per ADR-008, MCMC inverse promotion per ADR-010, cyclic SMB physics per ADR-009 §"Out of scope").

---

## §4 — Out of scope (durable deferrals)

These remain v1.0+ candidates, in line with the v0.8.4 release framing. No work scheduled in this plan:

* **Live AKTA UNICORN socket** (ADR-008 hardware deferral). The `MonitorSource.unicorn_socket` slot is reserved by W-076 with a disabled UI affordance.
* **MCMC inverse inference** (ADR-010 promotion target). The importance-sampling path stays the v0.9 ceiling. Promotion awaits datasets that warrant the `pymc` cold-import cost.
* **Cyclic SMB / multi-bed dynamics** (ADR-009 §"Out of scope"). Substantial physics scope; not in this maturation plan.
* **Wet-lab K_geom / ν calibration** (user-side). The tooling for ingestion (W-089 spreadsheet import) is in v0.9.0; the calibration itself is wet-lab work, not code.
* **Regulatory SOP / GMP-grade export** beyond the W-094 wet-lab procedure PDF. v1.0+.

---

## §5 — Token-economy + milestones

### 5.1 Per-release context budget estimate

| Release | Estimated context | Compression checkpoints | Milestone handover |
|---|---|---|---|
| v0.8.6 | ~25 K | 1 mid-cycle | yes (post-B-4d) |
| v0.8.7 | ~60 K | 2 mid-cycle | yes (post-B-5c) |
| v0.9.0 | ~150 K (split into 3 bundles X/Y/Z) | 4 mid-cycle | yes per bundle + final release |

### 5.2 Recommended `/checkpoint` and `/qa-only` triggers

* **`/checkpoint`** before each KEYSTONE batch (B-4d, B-5c, Bundle Y W-094, Bundle Z W-087).
* **`/qa-only`** between each KEYSTONE and its release-tag batch.
* **`/design-review`** against the new top-level Optimization tab (W-075) and the SOP PDF export (W-094) and the first-run example loader (W-097) and the tier banner (W-071).

---

## §6 — Module registry deltas

### 6.1 New modules introduced (v0.8.6 + v0.8.7 + v0.9.0)

| Module | First introduced in | Owner |
|---|---|---|
| `tabs/m3/mobile_phase_section.py` | v0.8.6 / W-069 | architect |
| `tabs/m3/isotherm_section.py` | v0.8.6 / W-070 | architect |
| `tabs/m3/detector_traces.py` | v0.8.7 / W-074 | architect |
| `tabs/m3/configure_section.py` (renamed pre-flight target) | v0.9.0 / W-082 | architect |
| `tabs/tab_optimization.py` | v0.8.7 / W-075 | architect |
| `tabs/tab_series_design.py` | v0.9.0 / W-085 | architect |
| `panels/spreadsheet_calibration_import.py` | v0.9.0 / W-089 | architect |
| `panels/sop_export.py` | v0.9.0 / W-094 | architect |
| `panels/run_compare.py` | v0.9.0 / W-095 | architect |
| `panels/session_io.py` | v0.9.0 / W-093 | architect |
| `panels/first_run_examples.py` | v0.9.0 / W-097 | architect |
| `tests/visualization/test_widget_mounting.py` | v0.8.6 / W-073 | scientific-coder |
| `tests/visualization/test_tier_routing_gate.py` | v0.9.0 / W-081 | scientific-coder |

### 6.2 Modules retired

| Module | Retired in | Reason |
|---|---|---|
| Inline pre-flight compute at `tab_m3.py:1051-1056` | v0.9.0 / W-083 | duplicated state — merged into single source-of-truth via session_state |

---

## §7 — Handover targets

### 7.1 Per-release release handovers

* `docs/handover/HANDOVER_v0_8_6_release.md` — combined batch handover for B-4a → B-4f.
* `docs/handover/HANDOVER_v0_8_7_release.md` — combined for B-5a → B-5f.
* `docs/handover/HANDOVER_v0_9_0_release.md` — milestone handover with all three bundles X/Y/Z.

### 7.2 Per-bundle handovers (v0.9.0 only)

* `HANDOVER_v0_9_0_bundle_X_decision_grade.md`
* `HANDOVER_v0_9_0_bundle_Y_calibration.md`
* `HANDOVER_v0_9_0_bundle_Z_ux.md`

---

## §8 — Risk register

| Risk | Mitigation |
|---|---|
| W-072 changes the orchestrator signature; downstream callers may break | Add `mobile_phase` / `isotherm_spec` as **optional kwargs** with `None` defaults preserving v0.8.5 behaviour. Run full test sweep. |
| W-075 BO UI design is non-trivial | Opus-design first, prototype as a hidden tab in v0.8.7 before promoting. |
| W-087 (tab_m3.py refactor) high regression risk | Property tests covering the M3 surface MUST land before the refactor. Refactor is one PR per extracted section. |
| W-094 SOP PDF export is the largest single new module | Treat as an Opus design + Sonnet implementation; reuse the existing `docs/user_manual/build_pdf.py` infrastructure. |
| W-073 widget-mounting AST gate may flag intentional helpers | Allow explicit opt-out via `# pragma: no-mount` comment with reason. |
| Multi-bundle parallel work in v0.9 risks merge churn | Use a single long-running v0.9 branch with bundle-merge cadence; do not parallelise bundles unless the team grows. |

---

## §9 — Executive summary (≤ 200 words)

The v0.8.5 dashboard advertises capabilities the v0.8.4 release did not actually wire. The mobile-phase widget, isotherm selector, and tier banner — all shipped in v0.8.4 — exist as defined-and-tested code but **have zero production callers**. Users pressing *Run* receive simulations in which their actual reagents and binding regime are silently replaced by water + Langmuir defaults. **v0.8.6** closes this with five wiring fixes (W-069 → W-073) plus a new AST gate (W-073) that prevents the pattern from recurring. **v0.8.7** exposes six orphan backends to the dashboard — detector traces, optimization engine, MonitorSource Protocol, multi-step coupled MC, plus HIC and ProteinA isotherms (W-074 → W-078). **v0.9.0** is the maturation milestone that turns DPSim from "honest + complete" into "wet-lab-credible": decision-graded, IA-organised, with SOP export, run-vs-run comparison, save/load sessions, calibration spreadsheet import, and a first-run example loader (W-079 → W-102). The three durable v0.9-deferred items — live AKTA UNICORN, MCMC inverse, cyclic SMB — remain out-of-scope per the original ADRs and form the v1.0 plateau.

The plan totals **34 W-items** across three releases with ~235 K context budget, ~10 milestone handovers, and three release tags. Closing v0.8.6 alone restores the simulator's truthfulness; closing v0.9.0 makes it operationally suitable for real wet-lab planning.
