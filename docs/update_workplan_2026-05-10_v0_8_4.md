# DPSim v0.8.4 — UI completeness against the v0.8.3 backend

**Date:** 2026-05-10
**Author:** `/dev-orchestrator` (Phase 3 of the joint engagement that produced
`docs/handover/AUDIT_v0_8_3_ui_completeness.md` (Phase 1) and
`docs/handover/ARCH_v0_8_3_ui_decomposition.md` (Phase 2))
**Inputs inherited:** Phase 1 defect catalogue C1–C9 + W-1 + W-2 (audit §6); Phase 2 module decomposition (§2), signature contracts §3 (a)–(j), seam map §4, and dependency bundles §7 (A → F)
**Target release:** v0.8.4 (patch bump per the project versioning policy — minor bumps remain reserved for matured-status milestones; v0.9 still gated on the wet-lab + hardware deferrals catalogued in ADRs 008/009/010)
**Mode:** project plan; no code edits in this document

---

## 1. Reconciliation summary

The v0.8.3 release handover left **zero open code-work items** at the backend level. Every cumulative-open item from the v0.8.2 catalogue closed cleanly; the residual deferrals (AKTA UNICORN socket, cyclic SMB, MCMC inverse, hierarchical multi-column inference, wet-lab K_geom/ν calibration) all live behind hardware or wet-lab gates and are correctly held for v0.9.

v0.8.4 is therefore a **UI-only refresh against the v0.8.3 backend** — closing the completeness gap that Phase 1 catalogued. The Streamlit surface exposes ~1/3 of the v0.7 → v0.8.3 user-facing capability; v0.8.4 takes that to ≥ 95 % (the residual 5 % being the v0.9 deferrals).

**Single backend-touching item.** Phase 2 §4 identifies one and only one backend change required: `lifecycle/orchestrator.py:781` currently instantiates `MobilePhase()` with hardcoded defaults at the post-M2 pre-flight envelope wire-in. The new mobile-phase widget (Bundle A, W-053) needs the lifecycle to honour user-supplied composition. This is W-054 — a one-function-signature change with backwards-compatible default. **Everything else in v0.8.4 is purely additive UI.**

**Conflict scan vs the v0.8.3 backend (W-046 → W-050):** none. v0.8.3 closed cleanly; nothing in this plan re-opens or contradicts those items.

**Sequencing decision:** B-0i (Tier 0) lands the cross-cutting prerequisites — the three new `OutputType` enum members + the AST scanner extension. Tier 1 ships three parallel batches (A foundation, B isotherm + plot, E calibration + banner). Tier 2 ships the keystone Bundle C uncertainty stack with a milestone handover at close, then Bundle D multi-column, then Bundle F UX polish. v0.8.4 release tag at B-4c.

---

## 2. New work item ledger

Numbering continues from W-050 (last v0.8.3 item). All new items are scoped to v0.8.4.

### 2.1 New work items

| ID | Bundle | Severity | Title | Files affected | Phase-2 §3 ref | Phase-1 defect resolved |
|---|---|---|---|---|---|---|
| **W-051** | (foundation) | MEDIUM | Three new `OutputType` enum members (`MC_PROBABILITY`, `POSTERIOR_PARAMETER`, `ESS`) + decision-grade policy rows | `src/dpsim/core/decision_grade.py` (after the existing `PRESSURE_HEADROOM` entry) | §5.3 | Enables C3, C4 |
| **W-052** | (foundation) | LOW | Extend the AST enum-comparison scanner to also cover `IsothermChoice` + `OutputType` | `tests/test_v9_3_enum_comparison_enforcement.py` | §5.5 | Pre-empts the AST-gate risk introduced by W-055 |
| **W-053** | A | **HIGH** | Mobile-phase composition widget (T_C, c_NaCl, glycerol, ethanol, optional μ override) | NEW `src/dpsim/visualization/panels/mobile_phase.py` | §3(a) | C1 |
| **W-054** | A | HIGH | Lifecycle `MobilePhase` override at the pre-flight envelope call site | `src/dpsim/lifecycle/orchestrator.py:781` (in-place modification) | §4 wire-in | C1 (backend half) |
| **W-055** | B | **HIGH** | Family-aware isotherm selector + conditional parameter sub-form (5 isotherm classes) | NEW `src/dpsim/visualization/panels/isotherm_selector.py`; in-place at `tabs/tab_m3.py:360–377` | §3(b) | C2 |
| **W-056** | B | LOW | `plots_m2.py` surface-area chart tier-gated through `render_decision_grade_annotation` | `src/dpsim/visualization/plots_m2.py:130–146` (in-place) | §3(h) | C8 |
| **W-057** | E | HIGH | Calibration-store wet-lab YAML ingestion panel with tier-promotion preview | NEW `src/dpsim/visualization/tabs/calibration/wetlab_ingestion.py`; deletes the unlabelled uploader at `panels/calibration.py:42` | §3(f) | C6 |
| **W-058** | E | MEDIUM | Top-of-page SEMI_QUANTITATIVE banner | NEW `src/dpsim/visualization/shell/tier_banner.py`; in-place at `app.py::_render_stage` (line ~506) | §3(i) | W-1 |
| **W-059** | C | **HIGH** | New `tab_calibration` top-level tab + forward MC sub-section (`p_blocker`/`p_warning` advisory) | NEW `src/dpsim/visualization/tabs/tab_calibration.py`; NEW `tabs/calibration/forward_mc.py`; in-place at `app.py` to mount the tab | §3(c) + §2 | C3 |
| **W-060** | C | **HIGH** | Inverse Bayesian inference sub-section (measurement editor + ESS chip + posterior round-trip into forward MC) | NEW `tabs/calibration/inverse_inference.py` | §3(d) | C4 |
| **W-061** | D | MEDIUM | Multi-column series builder sub-section | NEW `tabs/calibration/multi_column.py` | §3(e) | C5 |
| **W-062** | F | LOW | Per-rule `RecoveryAction` timeline ribbon under the streaming monitor | `src/dpsim/visualization/tabs/tab_m3_monitor.py:240+` (in-place) | §3(g) | C9 |
| **W-063** | F | LOW | Post-lifecycle "what's next" 3-button affordance | NEW `src/dpsim/visualization/components/next_step_affordance.py`; in-place at `tabs/tab_m3.py` after the breakthrough panel | §3(j) | W-2 |

**Total: 13 new work items.** Bundle A through F maps to roughly 1700 LOC of new UI code + ~30 LOC of in-place backend signature widening.

### 2.2 BLOCKER classification (release-gate)

None operational. **C1 (mobile-phase missing input) is the headline UX defect** but it is a UI-completeness gap, not a runtime-stability blocker — the lifecycle still produces correct envelopes at the silently-defaulted MobilePhase. **The full v0.8.4 close requires that no scientifically meaningful capability ship in the backend without a UI surface**, which is the framing this plan operationalises.

---

## 3. Sequenced batched work plan

Sequencing principles inherited from the v0.7 / v0.8.x plans, adjusted for this UI-only cycle:

- **B-0i Tier-0 first** — three OutputType members + AST scanner extension. Foundational; small; lands ahead of every panel that consumes the new policy rows.
- **Tier-1 parallel where possible** — Bundle A, Bundle B, and Bundle E are mutually independent (Phase 2 §7). Three batches can proceed in any order; recommended as listed (foundation → consumers).
- **Bundle C is the keystone** — the new top-level tab + forward MC + inverse round-trip is the largest single batch. Milestone handover at close.
- **Bundle D after C** — multi-column builder shares `tab_calibration` host but is otherwise independent.
- **Bundle F last** — UX polish (recovery timeline, next-step affordance). The next-step affordance specifically requires the three preceding tabs to exist as targets.
- **One module at a time** within each bundle (orchestrator inner-loop discipline).
- **Compress before you code** — at every PR boundary, refresh local context budget; Bundle C will require a milestone handover at close.

### 3.1 Tier 0 — Foundations (B-0i)

| Batch | IDs | Modules | Model tier | Notes |
|---|---|---|---|---|
| **B-0i** *Decision-grade extension + AST gate* | W-051, W-052 | `core/decision_grade.py` (3 new `OutputType` members + 3 policy rows); `tests/test_v9_3_enum_comparison_enforcement.py` (extended enum coverage list) | **Haiku** (mechanical extension; mirrors v0.7 W-030 enum extension exactly) | **Acceptance:** (i) `OutputType.MC_PROBABILITY`, `OutputType.POSTERIOR_PARAMETER`, `OutputType.ESS` enum members exist with correct `.value` strings; (ii) policy rows added to `DECISION_GRADE_POLICY` (MC_PROBABILITY → SEMI_QUANTITATIVE floor mirroring `PRESSURE_HEADROOM`; POSTERIOR_PARAMETER → SEMI_QUANTITATIVE; ESS → QUALITATIVE_TREND so it always renders NUMBER); (iii) AST scanner test extends its enum-coverage list to include `IsothermChoice` + `OutputType` and still passes 3/3; (iv) ruff = 0, mypy = 0; (v) 5 new test cases in `tests/core/test_decision_grade.py` covering each new policy row's render-mode ladder. |

### 3.2 Tier 1 — Parallel quick wins (Bundles A, B, E)

Three batches, each independent. Can proceed in any order; recommended as listed.

| Batch | IDs | Modules | Model tier | Notes |
|---|---|---|---|---|
| **B-1p** *Bundle A — Mobile-phase foundation (C1)* | W-053, W-054 | NEW `panels/mobile_phase.py` (~90 LOC); in-place `tabs/tab_m3.py` near line 320 (column-geometry section); in-place `lifecycle/orchestrator.py:781` (signature widening) | **Sonnet** (5-field widget + lifecycle signature change; clear contract from §3(a) + §4 wire-in) | **Acceptance:** (i) Widget exposes T_C 0–80, c_nacl_M 0–0.5, phi_glycerol/ethanol 0–0.5 sliders with viscosity-model `valid_domain` enforced; (ii) `custom_mu_pa_s` override toggle present and routes to `MobilePhase.custom_mu_pa_s` field; (iii) Widget writes `st.session_state['mobile_phase']`; (iv) Pre-flight envelope call at `tab_m3.py:1005` reads from session state instead of literal `MobilePhase()`; (v) Lifecycle accepts an optional `MobilePhase` argument with backwards-compatible default; (vi) 12 new tests covering range edges, override path, session-state propagation. |
| **B-1q** *Bundle B — Isotherm selector + plots_m2 tier (C2 + C8)* | W-055, W-056 | NEW `panels/isotherm_selector.py` (~220 LOC); in-place `tabs/tab_m3.py:360–377` (replace hardcoded q_max/K_L sliders); in-place `plots_m2.py:130, 144–146` (tier kwarg) | **Opus** for the isotherm widget design (5 conditional sub-forms, family-aware default routing per §3(b)); **Sonnet** for plot tier wire (mirrors W-035/W-037 directly) | **Acceptance W-055:** (i) `IsothermChoice` enum with 5 members + `IsothermSpec` frozen dataclass; (ii) Family-First default routing: AGAROSE/AGAROSE_CHITOSAN→Langmuir, IEX-flagged families→SaltModulatedLangmuir, IMAC-flagged families→ImidazoleModulatedLangmuir; (iii) Conditional sub-form per choice (Langmuir: q_max/K_L; SaltModulated: + ν + c_salt_ref + calibrated_locally; SMA: z/σ/K_eq/Λ; Competitive: per-component ν array); (iv) All `IsothermChoice` comparisons by `.value`, AST gate clean. **Acceptance W-056:** (i) `plot_surface_area_comparison` accepts optional `tier` kwarg; (ii) when set, the "Trust:" badge routes through `render_decision_grade_annotation` with `OutputType.MODULUS`; (iii) `tier=None` preserves legacy formatting bit-for-bit. **Tests:** 25+ for W-055 (factor coverage per choice + AST coverage); 4 for W-056 (mirrors `tests/visualization/test_plots_m1_tier.py`). |
| **B-1r** *Bundle E — Calibration ingestion + tier banner (C6 + W-1)* | W-057, W-058 | NEW `tabs/calibration/wetlab_ingestion.py` (~130 LOC); NEW `shell/tier_banner.py` (~80 LOC); in-place `app.py::_render_stage` at line ~506; **delete** unlabelled uploader at `panels/calibration.py:42` | **Sonnet** | **Acceptance W-057:** (i) Single clearly-labelled "Upload wet-lab calibration campaign (YAML)" file_uploader; (ii) Validation summary surfaces row count + schema errors via `wetlab_ingestion`; (iii) Tier-promotion preview shows before→after tier diff per affected output; (iv) Confirm button writes to `_cal_store`; (v) `panels/calibration.py:42` legacy uploader deleted. **Acceptance W-058:** (i) Banner renders on every stage as the first child of the stage container; (ii) Three states (GREEN at calibrated_local+ AND calibration loaded; AMBER at semi_quantitative; RED at qualitative_trend or below); (iii) Banner text quotes the README guardrail; (iv) DESIGN.md compliance — reuses existing semantic palette, no new colours. **Tests:** 8 for W-057 (parse/preview/confirm flow); 6 for W-058 (per-state rendering). |

### 3.3 Tier 2 — Keystone + follow-ons (Bundles C, D, F)

| Batch | IDs | Modules | Model tier | Notes |
|---|---|---|---|---|
| **B-2s** *Bundle C — Uncertainty stack (KEYSTONE)* | W-059, W-060 | NEW `tabs/tab_calibration.py` (~700 LOC; thin sub-section dispatcher); NEW `tabs/calibration/forward_mc.py` (~180 LOC); NEW `tabs/calibration/inverse_inference.py` (~220 LOC); in-place `app.py` to mount the new top-level tab | **Opus** for the inverse-inference panel (`MeasuredPressureFlowPoint` table editor + ESS warning surface + posterior round-trip into forward MC is the most complex single piece of v0.8.4 work); **Sonnet** for the forward MC panel + the tab dispatcher | **Acceptance W-059:** (i) `tab_calibration` mounted as a top-level peer to M1/M2/M3; (ii) Forward MC panel — n_samples slider 50–5000, seed input, prior mode radio (literature/family/custom), correlated-prior toggle that consumes `st.session_state['posterior_log_cov']` when present; (iii) Run → `monte_carlo_pressure_envelope`; (iv) Result panel renders P05/P50/P95 of Q_max + ΔP_predicted + headroom_ratio via `render_metric` with new `MC_PROBABILITY` / existing tier policies; (v) `p_blocker` chip with 3-band ladder (RED > 0.05, AMBER 0.01–0.05, GREEN < 0.01); (vi) "Drop Q to Q_recommended" callout when `p_blocker > 0.05`. **Acceptance W-060:** (i) `st.data_editor` table over `MeasuredPressureFlowPoint` (Q_m3_s, dP_pa, sigma_dP_pa columns); (ii) Run → `infer_posterior_envelope`; (iii) ESS metric via new `OutputType.ESS`; (iv) `ess_warning` surfaced as `st.warning()` block when present; (v) Posterior bands rendered via `OutputType.POSTERIOR_PARAMETER`; (vi) "Round-trip into forward MC" button writes posterior `log_cov` to `st.session_state['posterior_log_cov']`. **Tests:** 30+ across the two panels (smoke, statistical sanity, edge cases). **Milestone handover REQUIRED at close** — see §5. **`/qa-only` Standard tier before merge.** |
| **B-2t** *Bundle D — Multi-column series* | W-061 | NEW `tabs/calibration/multi_column.py` (~200 LOC) | **Sonnet** (focused per-row table editor + envelope runner; clear contract from §3(e)) | **Acceptance:** (i) `st.data_editor` over per-column rows (polymer_family, diameter, bed_height, bed_porosity, particle_porosity, optional G_DN/E*/d32 overrides); (ii) Default rows: capture (bed_height=0.05) + polish (bed_height=0.10); (iii) Add/remove buttons; (iv) Run → `compute_multi_column_envelope`; (v) Per-column envelopes table + series_Q_max/headroom/decision_tier readout; (vi) Bottleneck column highlighted in the per-column table; (vii) Stores result on `st.session_state['multi_column_envelope']`. **Tests:** 12 covering empty/single-row/multi-row/bottleneck-detection/override-path. |
| **B-2u** *Bundle F — UX polish (C9 + W-2)* | W-062, W-063 | In-place `tabs/tab_m3_monitor.py:240+` (RecoveryAction timeline ribbon); NEW `components/next_step_affordance.py` (~70 LOC); in-place `tabs/tab_m3.py` after breakthrough panel | **Sonnet** | **Acceptance W-062:** (i) Per-reading state-chip + action-chip ribbon under the existing trace plot; (ii) Reuses existing `_STATE_COLORS` + `_RECOVERY_ACTION_LABEL` registries (no new palettes); (iii) Hover-text shows `triggered_rule.value`. **Acceptance W-063:** (i) 3-button strip rendered when `lifecycle_result is not None`; (ii) Buttons write `st.session_state['_jump_to_calibration_section']` to one of {'forward_mc', 'inverse', 'multi_column'}; (iii) `tab_calibration` dispatcher honours the flag on first render after it's set (one-shot read-and-clear). **Tests:** 8 for W-062 (timeline + hover); 4 for W-063 (each button → jump flag). |

### 3.4 Tier 3 — Release tag

| Batch | IDs | Modules | Notes |
|---|---|---|---|
| **B-4c** *v0.8.4 release* | — | `pyproject.toml` (0.8.3 → 0.8.4); `src/dpsim/__init__.py` (`__version__`); `CHANGELOG.md`; per-batch handovers + combined release handover; commit + tag. Patch bump per the project versioning policy. | n/a |

---

## 4. Validation release gates (v0.8.4)

The v0.8.3 release closed 27 cumulative gates (1–27). v0.8.4 adds 10 new gates that turn the UI-completeness gap from §6 of the audit into a closed surface.

### 4.1 Inherited from v0.8.3

Gates 1–27 — covered in `CHANGELOG.md` v0.8.3 entry. None re-opened by this plan.

### 4.2 New gates introduced by v0.8.4

| # | Gate | Closed by |
|---|---|---|
| **28** | Mobile-phase composition reachable from UI (T_C, c_NaCl, glycerol, ethanol, μ override) | B-1p / W-053 + W-054 |
| **29** | Isotherm selector covers all 5 v0.8.x adapters with family-aware defaults | B-1q / W-055 |
| **30** | Forward MC `p_blocker` advisory chip surfaces with the 3-band threshold ladder | B-2s / W-059 |
| **31** | Inverse Bayesian inference reachable from UI with posterior log_cov round-trip into forward MC | B-2s / W-060 |
| **32** | Multi-column series envelope reachable with per-column geometry editor + bottleneck highlight | B-2t / W-061 |
| **33** | Calibration-store ingestion has a clearly-labelled UI path with tier-promotion preview | B-1r / W-057 |
| **34** | SEMI_QUANTITATIVE banner surfaces tier state at every stage (top-of-page) | B-1r / W-058 |
| **35** | Per-rule `RecoveryAction` timeline ribbon surfaces under the streaming monitor | B-2u / W-062 |
| **36** | `plots_m2.py` surface-area chart routes through `render_decision_grade_annotation` | B-1q / W-056 |
| **37** | Post-lifecycle "what's next" affordance surfaces 3 next-step buttons with cross-tab navigation | B-2u / W-063 |

### 4.3 v0.8.4 release framing

After all 7 batches land, gates 28–37 close. Therefore:

> **v0.8.4 ships as: "DPSim's user-facing surface is complete against the v0.8.3 backend. Every scientifically meaningful capability shipped in the v0.7.0 → v0.8.3 cluster is now reachable from the dashboard. Remaining gaps are exclusively the v0.9 deferrals (UNICORN socket, cyclic SMB, MCMC inverse) — bound on hardware availability or substantial new physics."**

The README's central editorial promise — *screen → calibrate → tighten* — becomes operationally testable from the dashboard for the first time. Tier promotion to `CALIBRATED_LOCAL` remains a wet-lab-driven path; v0.8.4 ships the *machinery* but not the wet-lab handshake.

---

## 5. Token-economy sequencing

Per-bundle estimates assume the orchestrator inner-loop overhead from `references/01-master-cycle.md` (≈ 1500–3000 tokens for protocol, 4 tokens/LOC for implementation, 0.6× for tests, 800–2000 for audit, 1.5× safety margin).

| Tier | Batch | Estimated context per inner loop | Suggested model | Compression checkpoint |
|---|---|---|---|---|
| 0 | B-0i decision_grade + AST | 6–10 K | Haiku | none — small |
| 1 | B-1p mobile_phase + lifecycle override | 14–20 K | Sonnet | none |
| 1 | B-1q isotherm selector + plots_m2 tier | 30–40 K | **Opus** for selector design + Sonnet impl | optional `/checkpoint` after merge |
| 1 | B-1r calibration ingestion + tier banner | 18–25 K | Sonnet | none |
| 2 | **B-2s Bundle C — uncertainty stack KEYSTONE (W-059+W-060)** | **75–95 K** | **Opus design + Sonnet impl + Opus audit** | **MILESTONE HANDOVER REQUIRED at close** — `docs/handover/HANDOVER_v0_8_4_b2s_uncertainty_stack.md`; pre-allocate 4–6 K context for handover generation |
| 2 | B-2t multi_column builder | 22–32 K | Sonnet | optional `/checkpoint` if context drops below GREEN after handover |
| 2 | B-2u UX polish (timeline + next-step) | 18–25 K | Sonnet | **`/qa-only` Standard tier before merge** (recovery timeline + next-step affordance both touch existing UI; smoke regression matters); `/checkpoint` after merge |

### 5.1 Compression triggers

- **Pre-flight to B-2s:** compute `tokens_remaining` before starting; if YELLOW (30–60 % remaining) → execute Dialogue Compression first; if RED (< 30 %) → produce milestone handover + start fresh session.
- **Mid-B-2s if hits RED:** produce Emergency Handover per orchestrator framework Reference 03; resume in new session.
- **Post-B-2s always:** generate full milestone handover regardless of zone — this is the keystone batch and must be safely re-resumable.
- **Post-B-2u:** `/checkpoint` to capture working state before the v0.8.4 release tag.

### 5.2 Quality-gate invocations across the plan

- After **B-1q** (isotherm selector): `/architect` six-dimension forward audit on the conditional sub-form pattern. The 5-class isotherm selector with family-aware defaults is the most novel single design surface in v0.8.4 and warrants the audit before consuming downstream.
- After **B-2s**: `/architect` six-dimension forward audit (Phase 3 Gate G3 of the orchestrator inner loop) — this is the single most important checkpoint of the plan.
- Before **B-2u** merge: `/qa-only` (Standard tier) — produces structured bug report on the new UX polish before fixes.
- Before **v0.8.4 tag**: `/design-review` — designer's-eye QA on the new top-level tab's visual hierarchy + the SEMI_QUANTITATIVE banner's prominence at every stage. The banner change is the most user-visible of all v0.8.4 work and warrants designer review.
- Before **v0.8.4 tag**: `/review` (the pre-landing PR review skill) on the cumulative diff vs `main`.
- Optional: `/codex review` adversarial second-opinion on the B-2s keystone.

### 5.3 Total estimated work-plan budget

Rough order-of-magnitude: **190–260 K tokens across the full plan**. Comparable to v0.8.2 (~220 K) and tighter than v0.7.0 (~290 K). The keystone batch B-2s carries 35–50 % of the budget on its own.

---

## 6. What this plan does *not* attempt to fix

Out-of-scope for v0.8.4; explicitly deferred:

- **Live AKTA UNICORN UI** — backend is the deferred `UnicornSocketMonitorSource` from ADR-008. v0.9 deliverable. v0.8.4 ships only the offline `MonitorSource` Protocol + the existing 3 backends (CSV / Simulated / Null); no UI hook for the live socket exists.
- **Cyclic SMB UI** — backend is the deferred port-rotation / multi-bed displacement coupling from ADR-009. v0.9 deliverable. v0.8.4 ships only the series `MultiColumnGeometry` aggregation.
- **MCMC inverse inference UI** — backend is the deferred MCMC promotion path from ADR-010 §"Why not MCMC". v0.8.4's inverse panel ships importance sampling only (the v0.8.3 implementation).
- **Per-family covariance registry UI** — explicitly out of scope per ADR-011 §"Out of scope". v0.8.4 forward MC accepts a user-supplied `log_cov` (via the inverse round-trip or direct upload) but does not ship a family-keyed covariance registry.
- **Auto-promotion of `CALIBRATED_LOCAL` tier from posterior fit alone** — wet-lab handshake required. v0.8.4 ships the *machinery* (inverse panel + ingestion panel) but not the auto-promotion.
- **Hierarchical / multi-column inference UI** — out of scope per ADR-010. v0.8.4 multi-column builder is forward-only (each column gets its own envelope; no inference across columns).
- **M1 / M2 plot tier-gating beyond v0.8.3** — already shipped (W-037, W-046). v0.8.4 closes the M2 surface-area chart (C8 / W-056); no further plot tier-gating planned.
- **Optimization-side BO pressure feasibility UI** — `PressureFeasibilityContext` and the multi-step variant remain Python-API only. The optimization-tab redesign is a separate v0.8.5+ scope.

---

## 7. Appendix A — Initial module registry

For the new modules introduced in this plan. Status semantics per orchestrator `references/01-master-cycle.md` Phase 5:

| Module | Owner | Status | Target tier | Linked W-items | First-build batch |
|---|---|---|---|---|---|
| `panels/mobile_phase.py` (NEW) | architect | NOT STARTED | (UI value-coupling, no tier of its own) | W-053 | B-1p |
| `panels/isotherm_selector.py` (NEW) | architect | NOT STARTED | (UI dispatch surface; family-first default routing) | W-055 | B-1q |
| `tabs/tab_calibration.py` (NEW) | architect | NOT STARTED | (top-level tab dispatcher; thin) | W-059 | B-2s |
| `tabs/calibration/forward_mc.py` (NEW) | architect | NOT STARTED | SEMI_QUANTITATIVE bands rendered through `OutputType.MC_PROBABILITY` policy floor | W-059 | B-2s |
| `tabs/calibration/inverse_inference.py` (NEW) | architect | NOT STARTED | SEMI_QUANTITATIVE per ADR-010 §"Tier mapping"; CALIBRATED_LOCAL only when user explicitly registers the posterior into calibration_store | W-060 | B-2s |
| `tabs/calibration/multi_column.py` (NEW) | architect | NOT STARTED | (consumes `MultiColumnPressureEnvelope` with weakest-tier rollup) | W-061 | B-2t |
| `tabs/calibration/wetlab_ingestion.py` (NEW) | architect | NOT STARTED | (ingestion + preview only; tier promotion happens server-side in `wetlab_ingestion.py`) | W-057 | B-1r |
| `shell/tier_banner.py` (NEW) | architect | NOT STARTED | (consumes `weakest_evidence_tier` from lifecycle result) | W-058 | B-1r |
| `components/next_step_affordance.py` (NEW) | architect | NOT STARTED | (UX-only) | W-063 | B-2u |

### Existing modules that move status as a result of this plan

| Module | Owner | Status before | Status after | Linked W-items |
|---|---|---|---|---|
| `core/decision_grade.py` | architect | APPROVED (post v0.8.3 W-046) | **REVISION REQUIRED** (B-0i: 3 new OutputType members + 3 policy rows) → APPROVED post-B-0i | W-051 |
| `tests/test_v9_3_enum_comparison_enforcement.py` | architect | APPROVED | **REVISION REQUIRED** (B-0i: extended enum coverage) → APPROVED post-B-0i | W-052 |
| `lifecycle/orchestrator.py` | architect | APPROVED (post v0.7 W-025) | **REVISION REQUIRED** (B-1p: MobilePhase override at line 781) → APPROVED post-B-1p | W-054 |
| `tabs/tab_m3.py` | architect | APPROVED (post v0.8.3 W-037 etc.) | **REVISION REQUIRED** (B-1p mobile_phase wire; B-1q isotherm selector replace; B-2u next-step affordance) → APPROVED post-B-2u | W-053, W-055, W-063 |
| `plots_m2.py` | architect | APPROVED | **REVISION REQUIRED** (B-1q tier-gating wire) → APPROVED post-B-1q | W-056 |
| `panels/calibration.py` | architect | APPROVED | **DEPRECATED** at B-1r (unlabelled uploader deleted; replaced by `wetlab_ingestion.py`) | W-057 |
| `app.py` | architect | APPROVED | **REVISION REQUIRED** (B-1r tier_banner mount; B-2s tab_calibration mount) → APPROVED post-B-2s | W-058, W-059 |
| `tabs/tab_m3_monitor.py` | architect | APPROVED (post v0.8.2 W-041) | **REVISION REQUIRED** (B-2u recovery timeline) → APPROVED post-B-2u | W-062 |

---

## 8. Appendix B — Handover targets

By analogy with the v0.8.x handover trail, this plan will produce:

- `docs/handover/HANDOVER_v0_8_4_b0i_decision_grade_ext_close.md` — at end of B-0i
- `docs/handover/HANDOVER_v0_8_4_b1p_mobile_phase_close.md` — at end of B-1p
- `docs/handover/HANDOVER_v0_8_4_b1q_isotherm_selector_close.md` — at end of B-1q
- `docs/handover/HANDOVER_v0_8_4_b1r_calibration_banner_close.md` — at end of B-1r
- **`docs/handover/HANDOVER_v0_8_4_b2s_uncertainty_stack_KEYSTONE.md`** — REQUIRED at end of B-2s (largest batch; milestone)
- `docs/handover/HANDOVER_v0_8_4_b2t_multi_column_close.md` — at end of B-2t
- `docs/handover/HANDOVER_v0_8_4_b2u_ux_polish_close.md` — at end of B-2u
- `docs/handover/HANDOVER_v0_8_4_release.md` — at v0.8.4 tag (combined; per the consolidation pattern from v0.8.2 and v0.8.3)

---

## 9. Quick links

- This plan: `docs/update_workplan_2026-05-10_v0_8_4.md`
- Phase 1 audit (input): `docs/handover/AUDIT_v0_8_3_ui_completeness.md`
- Phase 2 architecture (input): `docs/handover/ARCH_v0_8_3_ui_decomposition.md`
- Prior plan (v0.8.3): `docs/update_workplan_2026-05-10_v0_8_3.md`
- Validation release-gate ladder: §4 of this document + cumulative §4 from v0.7.0 / v0.8.0–v0.8.3 plans
- Decision-grade policy registry: `src/dpsim/core/decision_grade.py` (extended at B-0i)

---

### Disclaimer

> This work plan is provided for informational and development purposes only. UI for safety-critical, medical, financial, or regulatory systems must be reviewed by qualified domain engineers + UX practitioners before deployment. The K_geom values, viscosity correlation coefficients, MC priors, and warning/blocker thresholds underlying every panel in this plan are placeholders pending calibration against published manufacturer pressure-flow curves and/or wet-lab data. The author is an AI assistant; all designs should be validated through appropriate testing and peer review before production use. **v0.8.4 of DPSim must be described as "UI-completeness-closed against the v0.8.3 backend" — not as "validated for clinical or production use" — see §4.3 for the canonical communication framing.**
