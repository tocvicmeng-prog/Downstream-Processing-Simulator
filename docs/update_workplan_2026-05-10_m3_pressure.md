# DPSim v0.7.0 — M3 Interface Back-Pressure Optimization Work Plan

**Authors:** `/scientific-advisor` + `/architect` + `/dev-orchestrator` (joint)
**Inputs:**
- /scientific-advisor M3 Back-Pressure Architecture (delivered 2026-05-10) — the eight scientific deltas (Δ1–Δ8) with first-principles derivation, M1/M2 field map, decision-grade tier ladder, and dynamic warning rules
- /architect Design Specification (delivered 2026-05-10) — six-dimension audit verdict (CORRECTNESS FAIL CRITICAL; SCIENTIFIC PROVENANCE FAIL CRITICAL), module decomposition (5 new modules + 1 extension), full contract signatures, integration-seam map, dependency-bundle graph, forward-audit verdict
- 2026-05-04 plan (`docs/update_workplan_2026-05-04.md`) — the prior work plan whose v0.6.6 release closed 14 of 19 items

**Date:** 2026-05-10
**Mode:** project plan; no code edits in this document
**Target release:** v0.7.0

---

## 1. Reconciliation summary — interleaving with the residual five W-items

The 2026-05-04 plan §3 listed five items as "remaining" after the v0.6.6 release — W-012, W-013, W-014, W-015, W-018. **Re-reading the closure record (`docs/handover/HANDOVER_tier_0_close_2026-05-04.md` §2 + commit `6303464` "B-0b doc/mechanical hygiene") shows that all five were in fact closed prior to v0.6.6 shipping.** The "remaining 5" framing in the prior plan reflected the count at the time of plan authorship (2026-05-04), not the closure state at v0.6.6 release (2026-05-04 evening). Verification matrix re-run on 2026-05-10:

| W-item | Source | Status as of v0.6.6 | Verified at |
|---|---|---|---|
| W-012 | doc MAJOR-4 | **CLOSED** — already corrected by F-arch A-007 (resolved without new edit) | `core/recipe_validation.py:381–387` (dict matches comment) |
| W-013 | doc MINOR-3 | **CLOSED** — commit `6303464` (B-0b) replaced the stale block | `cad/README.md` (no "datatypes.py mismatches" block) |
| W-014 | doc MINOR-1+2 | **CLOSED** — commit `6303464` renamed test fn + `EXEMPT_FILES` is referenced at `tests/test_v9_3_enum_comparison_enforcement.py:110` (not orphan) | `tests/test_v9_3_enum_comparison_enforcement.py` |
| W-015 | doc MINOR-4 | **CLOSED** — commit `6303464` rewrote the gap-numbered rule list | `cfd/zonal_pbe.py` (no "Rule N" labelling) |
| W-018 | doc MINOR-7 (residual) | **CLOSED** — inventory in 2026-05-04 handover §2 confirmed all hits class-(a)/class-(c); B-3b cancelled. Site count drifted slightly (9 vs 11 originally inventoried) due to minor unrelated refactors; conclusion unchanged | `optimization/objectives.py` (6 sites), `module3_performance/catalysis/packed_bed.py` (3 sites) |

**Result: B-0d collapses to a verification-only batch.** No code changes were required for any of the five W-items themselves. One incidental ruff finding was cleaned up in the same pass (`tests/test_v9_3_enum_comparison_enforcement.py` had an unused `import pytest` — one-line removal, verified the AST-gate test still 3/3 passing).

**Conflict scan vs the M3 changes (W-020 … W-030 below):** none. The M3 work proceeds straight to Tier 1 with a clean working tree.

**Sequencing decision (revised):**

B-0d is closed-on-verification at v0.6.6 + the one-line ruff fix landed 2026-05-10. The M3 work begins **Tier 1 immediately**.

There is **no blocker analogous to W-001** (the Python-3.13 environment lockdown that gated all other 2026-05-04 work). The runtime stack is correct.

---

## 2. New work item ledger

Numbering continues from W-019 (last item in the 2026-05-04 plan). All new items are scoped to v0.7.0.

### 2.1 Reconciled open finding ledger — new entries

| ID | Source | Severity | Title | Files affected | Architect §3 contract | Architect §4 seam | Architect §5 bundle |
|---|---|---|---|---|---|---|---|
| **W-020** | Δ1 | **CRITICAL** | Replace ΔP_max anchor: u_crit per family, not safety×E_star | `module3_performance/pressure_envelope.py` (NEW), `module3_performance/family_kgeom.py` (NEW), `module3_performance/hydrodynamics.py` (deprecate `max_safe_flow_rate`) | §3.4 + §3.7 + §3.3 | seam #1 + #7 | **B** |
| **W-021** | Δ2 | HIGH | Surface bead_d32 + dsd_sigma_ln from M1; replace bead_d50 in `_column_with_microsphere` | `level1_emulsification/solver.py`, `module2_functionalization/orchestrator.py` (FunctionalMicrosphere.m1_contract), `module3_performance/method_simulation.py:316,520` | n/a (existing M1 contract extension) | seam #2 | **A** |
| **W-022** | Δ3 | HIGH | Iterate ΔP–ε_b coupling (fixed-point on KC + bed compression) | `module3_performance/hydrodynamics.py` (new `iterate_kc_compression`), `module3_performance/pressure_envelope.py` (consume in `compute_pressure_envelope`) | n/a | seam #3 | **C** |
| **W-023** | Δ4 | HIGH | Buffer-and-T viscosity model: μ = f(T, c_NaCl, φ_glycerol, φ_ethanol) | `core/viscosity.py` (NEW), `core/mobile_phase.py` (NEW) | §3.1 + §3.2 | seam #4 | **A** |
| **W-024** | Δ5 | MEDIUM | Frit / fitting series resistance: ΔP_frit = μ·u·t_frit / k_f | `module3_performance/hydrodynamics.py` (`ColumnGeometry` Optional fields + new `frit_pressure_drop` method) | n/a (additive to ColumnGeometry) | seam #5 | **A** |
| **W-025** | Δ6 | **CRITICAL** | Pre-flight pressure envelope wired into lifecycle | `lifecycle/orchestrator.py` (post-M2 wire-in), `module3_performance/pressure_envelope.py::compute_pressure_envelope` consumption | §3.4 | seam #6 | **D** |
| **W-026** | Δ7 | HIGH | Per-family `valid_domain` envelope + auto-tier downgrade | `module3_performance/family_kgeom.py` (NEW — `FAMILY_KGEOM_REGISTRY`), `module3_performance/pressure_envelope.py` (tier-rollup logic) | §3.7 | seam #7 | **B** |
| **W-027** | Δ8 | MEDIUM | In-flight pressure-trace evaluator (function only; streaming UI deferred to v0.8) | `module3_performance/pressure_monitor.py` (NEW) | §3.5 | seam #8 | **E** |
| **W-028** | (composite — Δ6 follow-on) | HIGH | G8 recipe-validation gate: pressure-envelope check per step | `core/recipe_validation.py` (new `_g8_pressure_envelope_check`) | n/a (mirrors G7 shape, B-1a precedent) | architect §4.2 | **D** |
| **W-029** | (composite — Δ6 follow-on) | MEDIUM | M3 UI section: pressure envelope display with decision-grade rendering | `visualization/tabs/tab_m3.py` (new "Pressure envelope" subsection), `visualization/decision_grade_render.py` (reuse `render_metric` per B-1b) | n/a (UI integration) | architect §4.1 | **D** |
| **W-030** | (composite — Δ1 follow-on) | MEDIUM | Decision-grade extension: PRESSURE_LIMIT, Q_MAX, U_CRIT, PRESSURE_HEADROOM OutputTypes | `core/decision_grade.py` (new `OutputType` members + policy rows) | (extension of existing closed-set enum) | architect §3.6 | **B** (must ship with B for the new render-mode policy to exist) |

**Total: 11 new work items.** Combined with the 5 residuals, v0.7.0 carries 16 items in flight.

### 2.2 BLOCKER classification (release-gate)

None operational at the runtime level. **W-020 is a CRITICAL scientific defect** (current code under-reports bead-crush risk by 5–50× factor) but does not crash the runtime — silent wrong-answer. **W-025 is CRITICAL UX completeness** (no pre-flight preview before "Start flow"). Both are functional release-blockers for v0.7.0; neither is a runtime-stability blocker.

---

## 3. Sequenced batched work plan

Sequencing principles applied (carried from the 2026-05-04 plan, adjusted for this work):

- **B-0d hygiene first** — same precedent as B-0b in the prior plan; ≤ 5 files, no behavioural change.
- **Bundle A items (W-021, W-023, W-024) parallelisable** — independent quick wins, each <200 LOC.
- **Bundle B (W-020 + W-026 + W-030) is the keystone** — must land together; replacing the wrong ΔP_max anchor is a coordinated change across `family_kgeom.py`, `pressure_envelope.py`, and `decision_grade.py`. Single PR.
- **Bundle C (W-022) after B** — iteration logic is meaningful only against the correct anchor.
- **Bundle D (W-025 + W-028 + W-029) after B+C** — UX wires the now-correct envelope into the recipe-validation gate, the lifecycle orchestrator, and the M3 UI tab.
- **Bundle E (W-027) after D** — streaming function depends on `PressureEnvelope` value type but ships independent of UI.
- **One module at a time** within each bundle (orchestrator inner-loop discipline).
- **Compress before you code** — at every PR boundary, refresh local context budget; Bundle B will require a milestone handover at close.

### 3.1 Tier 0 — Immediate (CLOSED on verification 2026-05-10)

| Batch | IDs | Modules | Model tier | Notes |
|---|---|---|---|---|
| **B-0d** *Residual hygiene verification* | W-012, W-013, W-014, W-015, W-018 — all confirmed CLOSED at v0.6.6 per §1; one-line ruff fix landed 2026-05-10 (`tests/test_v9_3_enum_comparison_enforcement.py` unused `import pytest` removed) | n/a (verification only) | n/a | **Verification:** Tier 0 regression baseline 95/95 passed (`tests/test_v9_3_enum_comparison_enforcement.py`, `test_evidence_tier.py`, `test_v0_5_2_codex_fixes.py`, `test_python_version_preflight.py`, `test_cfd_zonal_pbe.py`); ruff: clean on the 5 touched paths; mypy: documented scipy-stubs baseline noise unchanged. **Status: ✅ COMPLETE** |

### 3.2 Tier 1 — Short-term (1–2 weeks) — Bundle A quick wins

Three batches, each independent. Can run in any order; recommended as listed (foundation → consumers).

| Batch | IDs | Modules | Model tier | Notes |
|---|---|---|---|---|
| **B-1f** *Buffer + viscosity foundation (Δ4)* | W-023 | `core/mobile_phase.py` (NEW), `core/viscosity.py` (NEW), `tests/core/test_mobile_phase.py`, `tests/core/test_viscosity.py` | **Sonnet** (≈ 150 LOC + lookup tables; data-heavy with literature anchors per /scientific-advisor §D buffer-μ table) | Independent quick win. Establishes `MobilePhase` and `resolve_mobile_phase_viscosity` value types — used by Bundles B + D. **Acceptance:** 30+ test cases (water-T table from Crittenden 2012; NaCl additive from Out & Los 1980; glycerol-water from Cheng 2008; ethanol-water from Khattab 2017; `custom_mu_pa_s` override; extrapolation flag at \|T-25\| > 15 °C with non-zero φ_glycerol/φ_ethanol). Carries `ViscosityResult.tier=SEMI_QUANTITATIVE` from the additive model; promotes to `CALIBRATED_LOCAL` only when `custom_mu_pa_s` is user-supplied. |
| **B-1g** *Sauter d32 surfacing + frit fields (Δ2 + Δ5)* | W-021, W-024 | `level1_emulsification/solver.py` (PBE-result aggregation surfaces `bead_d32` and `dsd_sigma_ln` flat fields), `module2_functionalization/orchestrator.py` (FunctionalMicrosphere.m1_contract — extend), `module3_performance/method_simulation.py:316,520` (replace `m1.bead_d50` → `m1.bead_d32`), `module3_performance/hydrodynamics.py:21` (add `Optional` `frit_permeability_m2`, `frit_thickness_m` to `ColumnGeometry` + new `frit_pressure_drop` method) | **Sonnet** for d32 (cross-module M1 contract change), **Haiku** for frit (additive Optional fields, no cross-module impact) | Two minimally-coupled deltas; can ship as one PR. **Acceptance W-021:** existing M1 tests still pass; new test asserts `d32 ≈ 0.80 · d50` for σ_ln = 0.3 lognormal DSD; `_column_with_microsphere` integration test asserts ΔP correction factor 1.5–1.6× for d32 vs d50 at typical M1 output. **Acceptance W-024:** 8 new test cases (frit on/off, ΔP_frit additivity, default `Optional` = None preserves backwards compatibility). |
| **B-1h** *Decision-grade enum extension (Δ1 follow-on, lands ahead of B-2f)* | W-030 | `core/decision_grade.py` (extend `OutputType` enum with `PRESSURE_LIMIT`, `Q_MAX`, `U_CRIT`, `PRESSURE_HEADROOM`; add four rows to `DECISION_GRADE_POLICY`), `tests/core/test_decision_grade_pressure_outputs.py` (NEW) | **Haiku** (boilerplate enum + policy-table addition; ~20 LOC + 12 test cases) | Decoupled prerequisite for Bundle B's render-path plumbing. Lands here so B-2f can consume the extension cleanly without bundling a stylistic change with the science fix. **Acceptance:** mirrors existing `PRESSURE_DROP` policy (min tier `SEMI_QUANTITATIVE` → INTERVAL render; promote to NUMBER at `CALIBRATED_LOCAL`). `PRESSURE_HEADROOM` tier-independent (always renders as percentage; threshold is what depends on tier). |

### 3.3 Tier 2 — Medium-term (1–2 months) — Bundles B, C, D

| Batch | IDs | Modules | Model tier | Notes |
|---|---|---|---|---|
| **B-2f** *Pressure envelope science fix (Δ1 + Δ7) — KEYSTONE* | W-020, W-026 | `module3_performance/family_kgeom.py` (NEW — `FamilyKGeom` + `FAMILY_KGEOM_REGISTRY` for 5 PolymerFamily values, comparison by `.value` per v9.0 contract; literature-anchored K_geom defaults from Stickel & Fotopoulos 2001 / Bemberis-style derivation), `module3_performance/pressure_envelope.py` (NEW — `PressureEnvelope` frozen dataclass + `compute_pressure_envelope` orchestrator + tier-rollup logic walking `valid_domain`), `module3_performance/hydrodynamics.py:89` (deprecate `max_safe_flow_rate` with `DeprecationWarning`; keep one release; `dP_max_burst_pa` becomes the structural-ceiling diagnostic, no longer the operational limit), `tests/module3_performance/test_family_kgeom.py` (NEW), `tests/module3_performance/test_pressure_envelope.py` (NEW), `tests/module3_performance/test_hydrodynamics_deprecation.py` (NEW), `docs/decisions/ADR-pressure-envelope-anchor.md` (NEW) | **Opus** for design refinement and the u_crit / tier-rollup core; **Sonnet** for the registry data + dataclass scaffolding + test suites | The science fix. ~600–800 LOC; ~60 new tests. Touches the science, the API, and the test suite simultaneously. Bundle B + W-030 (already landed in Tier 1 as B-1h) together produce the corrected ΔP_max prediction. **Acceptance:** (i) per-family u_crit = K_geom · G_DN · d32² / (μ·L) with `K_geom_source = "family_default"` carrying `tier = SEMI_QUANTITATIVE`; (ii) `valid_domain` violation downgrades tier by one step (floor `QUALITATIVE_TREND`); (iii) `PressureEnvelope.dP_max_operational_pa` and `dP_max_burst_pa` are distinct fields — burst is no longer the operational limit; (iv) golden-numbers test for one family (agarose) anchors the K_geom against Sepharose-class manufacturer pressure-flow curves at L = 10 cm, μ = 1×10⁻³ → u_crit ∈ literature-published 300–500 cm·h⁻¹ envelope; (v) deprecated `max_safe_flow_rate` emits `DeprecationWarning` and existing tests redirect to `compute_pressure_envelope`; (vi) `ruff = 0`, `mypy = 0`, `test_v9_3_enum_comparison_enforcement.py` passes. **Milestone handover REQUIRED at close** — see §5. |
| **B-2g** *ΔP–ε_b iteration refinement (Δ3)* | W-022 | `module3_performance/hydrodynamics.py` (NEW `iterate_kc_compression(geometry, Q, μ, max_iter=50, tol=1e-4) → tuple[ΔP, ε_b_final, n_iter, converged]`), `module3_performance/pressure_envelope.py::compute_pressure_envelope` (consume the new iterated form), `tests/module3_performance/test_pressure_envelope_iteration.py` (NEW) | **Sonnet** (~80 LOC numerical refinement; well-defined fixed-point loop) | Numerical refinement of B-2f. No API change — iteration runs inside `compute_pressure_envelope`. **Acceptance:** 15 test cases (convergence within `iteration_tol=1e-4`; `max_iter=50` ceiling enforced; ε_b floor at 0.10 to prevent divide-by-zero; runaway detection sets `converged=False` → triggers tier downgrade and BLOCKER warning at the envelope level; smooth-flow case agrees with one-shot to within 0.5 % when far from u_crit). |
| **B-2h** *Pre-flight UX wiring (Δ6 + G8 + UI section)* | W-025, W-028, W-029 | `lifecycle/orchestrator.py` (post-M2 wire-in: produces one `PressureEnvelope` per recipe step), `core/recipe_validation.py` (new `_g8_pressure_envelope_check` — mirrors G7 shape from B-1a; emits BLOCKER on `headroom_ratio > 1.0`, WARNING on > 0.7, WARNING per `valid_domain_violations`), `visualization/tabs/tab_m3.py` (new "Pressure envelope" section using `render_metric` from `decision_grade_render.py` per B-1b precedent — Q-vs-ΔP plot with operational ceiling shaded; status chip OK/NEAR LIMIT/EXCEEDED; per-step μ_peak read from `LoadedStateElutionResult.gradient_diagnostics` for elution steps per B-2e; tier badge auto-derived from `PressureEnvelope.decision_tier`), `tests/lifecycle/test_pressure_envelope_wiring.py` (NEW), `tests/core/test_recipe_validation_g8_pressure.py` (NEW), `tests/visualization/test_tab_m3_pressure_section.py` (NEW) | **Sonnet** for orchestrator + G8 (cross-cutting, domain-aware); **Sonnet** for UI wiring (visualization with business logic per /architect §3 model-selection criteria) | UX-facing close. ~20 new test cases. **Acceptance:** (i) `lifecycle/orchestrator.py` emits one `PressureEnvelope` per `ProcessStepKind` step; (ii) G8 gate triggers BLOCKER/WARNING per the threshold ladder; (iii) `tab_m3.py` renders the envelope section before "Start flow" simulation kicks off; (iv) elution step μ_peak is read from `gradient_diagnostics` per B-2e and never duplicated; (v) `/qa-only` triple-tier pass before merge. |

### 3.4 Tier 3 — Maintenance / parallel (rolling)

| Batch | IDs | Modules | Model tier | Notes |
|---|---|---|---|---|
| **B-3d** *Streaming pressure monitor function (Δ8)* | W-027 | `module3_performance/pressure_monitor.py` (NEW — `PressureMonitorRule` enum, `PressureMonitorState` enum, `PressureMonitorReading` + `PressureMonitorOutput` frozen dataclasses, `evaluate_pressure_trace` pure function with hysteresis), `tests/module3_performance/test_pressure_monitor.py` (NEW) | **Sonnet** (≈ 150 LOC pure function + state-machine logic; ~25 new tests including a CSV-fixture replay test for offline trace evaluation) | Function-only ship; **streaming UI deferred to v0.8 epic.** AKTA UNICORN integration also v0.8. The function alone is independently testable against recorded run traces. **Acceptance:** 25 test cases covering each `PressureMonitorRule` (HEADROOM_WARNING / HEADROOM_BLOCKER / DPDT_WARNING / DPDT_BLOCKER / MODEL_DEVIATION_LOW / MODEL_DEVIATION_HIGH / SPIKE), 30-s warning-dwell hysteresis, 5-min history window pruning, immutable history return, CSV fixture replay reproducing a known-fouling trace from a previous run for training-purpose validation. |

---

## 4. Validation release gate (v0.7.0)

The 2026-05-04 plan §5 defined five release gates for "validated for downstream-processing release decisions". v0.7.0 inherits those five and adds three back-pressure-specific gates.

### 4.1 Inherited from 2026-05-04 plan

  1. **Environment** (W-001) — closed in Tier 0 of 2026-05-04 plan ✓
  2. **Calibrated wet-lab dataset** — wet-lab side, open
  3. **Independent wet-lab holdout validation** — wet-lab side, open
  4. **Decision-grade automatic downgrade** (W-003) — closed v0.6.6 (B-1b API + B-2e M3 wiring) ✓
  5. **Process dossier export** (W-011) — closed v0.6.6 (B-2d) ✓

### 4.2 New gates introduced by v0.7.0

  6. **u_crit-anchored ΔP_max prediction** (W-020 + W-026) — code-side; closed when B-2f lands. Defines the difference between "screening simulator with explicit pressure envelopes" (post-v0.7, this gate closed) and the legacy v0.6.6 state (this gate open — bursting modulus used as operational limit, scientifically wrong by 5–50× factor).
  7. **Per-family K_geom calibration against manufacturer pressure-flow curves** — wet-lab/user-data-side; **gates promotion from SEMI_QUANTITATIVE INTERVAL to CALIBRATED_LOCAL NUMBER render**. Code path lands with B-2f via the `calibration_store` argument; the store itself is empty until users supply manufacturer curves or local pressure-flow calibrations. **Connects to existing `M3CalibrationCoverage.pressure_flow_calibrated` from B-2e** — reuse, no parallel mechanism.
  8. **Pre-flight pressure envelope renders before "Start flow"** (W-025 + W-028 + W-029) — code-side; closed when B-2h lands. Defines whether DPSim can claim "back-pressure-safe column operation" guidance for first-time operators.

### 4.3 v0.7.0 release framing

After B-2f + B-2h + B-3d land, gates 6 and 8 are closed; gate 7 is wet-lab-gated. Therefore:

> **v0.7.0 ships as: "DPSim is a research-grade screening simulator with first-principles back-pressure envelopes rendered at SEMI_QUANTITATIVE INTERVAL precision; promotion to CALIBRATED_LOCAL NUMBER precision requires user-supplied manufacturer pressure-flow curves or local wet-lab calibration."**

DPSim must NEVER, in any v0.7 communication, be described as "validated for back-pressure-safe column operation" — that requires gates 2, 3, and 7 all closed. The framing for v0.7 is "**operates a scientifically-anchored pressure envelope; pre-flight warnings are advisory, not certified**."

---

## 5. Token-economy sequencing

Per-bundle estimates assume the orchestrator inner-loop overhead from `references/01-master-cycle.md` (≈ 1500–3000 tokens for protocol, 4 tokens/LOC for implementation, 0.6× for tests, 800–2000 for audit, 1.5× safety margin).

| Tier | Batch | Estimated context per inner loop | Suggested model | Compression checkpoint |
|---|---|---|---|---|
| 0 | B-0d hygiene | 8–12 K | Haiku/Sonnet | none — small |
| 1 | B-1f viscosity | 25–35 K | Sonnet | none — single module pair |
| 1 | B-1g d32 + frit | 18–25 K | Sonnet/Haiku | none |
| 1 | B-1h decision_grade ext | 4–6 K | Haiku | none |
| 2 | **B-2f keystone (W-020+W-026)** | **70–90 K** | **Opus design + Sonnet impl + Opus audit** | **MILESTONE HANDOVER REQUIRED at close** — `docs/handover/HANDOVER_v0_7_b2f_pressure_envelope.md`; pre-allocate 4–6 K context for handover generation |
| 2 | B-2g iteration | 20–30 K | Sonnet | optional `/checkpoint` if context drops below GREEN after handover |
| 2 | B-2h UX wiring | 40–55 K | Sonnet | **`/qa-only` triple-tier pass before merge** (Quick + Standard + Exhaustive); `/checkpoint` after merge |
| 3 | B-3d streaming function | 20–30 K | Sonnet | none — function-only |

### 5.1 Compression triggers (from orchestrator framework)

- **Pre-flight to B-2f:** compute `tokens_remaining` before starting; if YELLOW (30–60 % remaining) → execute Dialogue Compression first; if RED (<30 %) → produce milestone handover + start fresh session.
- **Mid-B-2f if hits RED:** produce Emergency Handover per orchestrator framework Reference 03; resume in new session.
- **Post-B-2f always:** generate full milestone handover regardless of zone — this is the keystone batch and must be safely re-resumable.
- **Post-B-2h:** `/checkpoint` to capture working state before B-3d (which is genuinely independent).

### 5.2 Quality-gate invocations across the plan

- After B-2f: `/architect` six-dimension forward audit (Phase 3 Gate G3 of the orchestrator inner loop) — this is the single most important checkpoint of the plan.
- Before B-2h merge: `/qa-only` (Standard tier) — produces structured bug report on the new M3 UI section before fixes.
- After B-2h merge: `/design-review` (live, not plan-mode) — designer's-eye QA on the rendered envelope display.
- Before v0.7.0 tag: `/review` (the pre-landing PR review skill) on the cumulative diff vs `main`.
- Optional: `/codex review` adversarial second-opinion on the B-2f keystone PR (the "200 IQ autistic developer" gate).

### 5.3 Total estimated work-plan budget

Rough order-of-magnitude: **220–290 K tokens across the full plan** (excluding handover regeneration and emergency-recovery overhead). At Sonnet-equivalent pricing this is ~2× the 2026-05-04 plan's v0.6.6 batch — proportional to the single-keystone-batch concentration in B-2f.

---

## 6. What this plan does *not* attempt to fix

Out-of-scope for v0.7.0; explicitly deferred:

- **Streaming UI for `evaluate_pressure_trace`** — v0.8 epic. The function ships v0.7; the live widget + AKTA UNICORN integration + WebSocket plumbing are a separate ~3-week scope.
- **CALIBRATED_LOCAL tier promotion via manufacturer pressure-flow curves** — user-data-side, not code-side. The `calibration_store` argument exists from B-2f; the store itself is empty until users supply manufacturer-published curves or local wet-lab calibrations. Connects to gate 7 (§4.2).
- **Wet-lab calibration of K_geom for any specific resin product** — wet-lab-side. v0.7 ships SEMI_QUANTITATIVE INTERVAL render with literature-anchored K_geom defaults per family; tighter intervals require local fits.
- **CIP-specific calibration anchors** (high-NaOH viscosity at elevated T, ethanol-water cross-terms, fines accumulation across cycles) — wet-lab-gated. Code path correctly handles the high-μ regime via Δ4 / W-023; quantitative anchors await wet-lab data.
- **Additional polymer families beyond the current 5** (alginate, agarose, agarose-chitosan, cellulose, PLGA) — out of scope. Adding a new family means adding one row to `FAMILY_KGEOM_REGISTRY` per the data-driven design from B-2f; no architectural change required.
- **Channeling repair / "ΔP-too-low" recovery automation** — the W-027 monitor *detects* MODEL_DEVIATION_LOW (channeling) but the suggested action is "stop, repack or replace column" — automated repacking guidance is a future scope.
- **Multi-column / parallel-bed pressure modelling** — current `ColumnGeometry` is single-column only. Parallel beds (CC8 / SMB) are a v0.9 epic.
- **Bayesian uncertainty propagation through the envelope** — v0.7 ships ±factor-2 SEMI_QUANTITATIVE intervals from policy, not from posterior sampling. Bayesian envelope inference is a future scope tied to wet-lab data.
- **Optimization integration** — The B-2e M3 quantitative gates already promote `pressure_flow_calibrated` independently. v0.7 does NOT add ΔP_max as an explicit BoTorch optimization objective; that integration is v0.8+.

---

## 7. Appendix A — Initial module registry

For the new modules introduced in this plan. Status semantics per orchestrator `references/01-master-cycle.md` Phase 5:

| Module | Owner | Status | Target tier | Linked W-items | First-build batch |
|---|---|---|---|---|---|
| `core/mobile_phase.py` (NEW) | architect | NOT STARTED | (value type — no tier) | W-023 | B-1f |
| `core/viscosity.py` (NEW) | architect | NOT STARTED | SEMI_QUANTITATIVE (additive model) → CALIBRATED_LOCAL on `custom_mu_pa_s` override | W-023 | B-1f |
| `module3_performance/family_kgeom.py` (NEW) | architect | NOT STARTED | SEMI_QUANTITATIVE (literature-anchored K_geom defaults) → CALIBRATED_LOCAL with manufacturer pressure-flow curve | W-020, W-026 | B-2f |
| `module3_performance/pressure_envelope.py` (NEW) | architect | NOT STARTED | SEMI_QUANTITATIVE INTERVAL (default render); tier rollup walks `valid_domain` per family | W-020, W-022, W-025, W-026 | B-2f (initial scaffold), B-2g (iteration), B-2h (lifecycle wire-in) |
| `module3_performance/pressure_monitor.py` (NEW) | architect | NOT STARTED | SEMI_QUANTITATIVE (rule-based; thresholds calibrated to literature defaults) | W-027 | B-3d |

### Existing modules that move status as a result of this plan

| Module | Owner | Status before | Status after | Linked W-items |
|---|---|---|---|---|
| `module3_performance/hydrodynamics.py` | architect | APPROVED-WITH-FIX-LIST (post-v0.6.6) | **REVISION REQUIRED** (B-2f deprecates `max_safe_flow_rate`; B-2g adds `iterate_kc_compression`; B-1g adds frit fields) → APPROVED post-B-2g | W-020, W-022, W-024 |
| `module3_performance/method_simulation.py` (`_column_with_microsphere`) | architect | APPROVED | **REVISION REQUIRED** (B-1g d32 swap) → APPROVED post-B-1g | W-021 |
| `core/decision_grade.py` | architect | APPROVED (post v0.6.6 B-1b) | **REVISION REQUIRED** (B-1h enum + policy extension) → APPROVED post-B-1h | W-030 |
| `core/recipe_validation.py` | architect | APPROVED (post v0.6.6 B-1a G7) | **REVISION REQUIRED** (B-2h G8 gate) → APPROVED post-B-2h | W-028 |
| `lifecycle/orchestrator.py` | architect | APPROVED | **REVISION REQUIRED** (B-2h post-M2 wire-in) → APPROVED post-B-2h | W-025 |
| `visualization/tabs/tab_m3.py` | architect | APPROVED (post v0.6.6 B-1b rollout) | **REVISION REQUIRED** (B-2h pressure-envelope section) → APPROVED post-B-2h | W-029 |
| `level1_emulsification/solver.py` | architect | APPROVED (post v0.6.6 A-003) | **REVISION REQUIRED** (B-1g d32 + dsd_sigma_ln surfacing) → APPROVED post-B-1g | W-021 |
| `module2_functionalization/orchestrator.py` (FunctionalMicrosphere) | architect | APPROVED (post v0.6.6 A-001) | **REVISION REQUIRED** (B-1g m1_contract extension) → APPROVED post-B-1g | W-021 |

---

## 8. Detailed handover targets

By analogy with the 2026-05-04 plan's handover trail, this plan will produce:

- `docs/handover/HANDOVER_b0d_residual_hygiene_close.md` — at end of B-0d
- `docs/handover/HANDOVER_b1f_viscosity_close.md` — at end of B-1f
- `docs/handover/HANDOVER_b1g_d32_frit_close.md` — at end of B-1g
- `docs/handover/HANDOVER_b1h_decision_grade_ext.md` — at end of B-1h
- **`docs/handover/HANDOVER_v0_7_b2f_pressure_envelope_KEYSTONE.md`** — REQUIRED at end of B-2f (largest batch; milestone)
- `docs/handover/HANDOVER_b2g_iteration_close.md` — at end of B-2g
- `docs/handover/HANDOVER_v0_7_b2h_ux_close.md` — at end of B-2h (release candidate)
- `docs/handover/HANDOVER_v0_7_b3d_streaming_function_close.md` — at end of B-3d
- `docs/handover/HANDOVER_v0_7_0_release.md` — at v0.7.0 tag

---

## 9. Quick links

- This plan: `docs/update_workplan_2026-05-10_m3_pressure.md`
- Prior plan (residual 5 items): `docs/update_workplan_2026-05-04.md`
- Support matrix (will need v0.7.0 update after B-2h): `docs/current_support_matrix.md`
- ADR for u_crit anchor (NEW with B-2f): `docs/decisions/ADR-pressure-envelope-anchor.md`
- Validation release-gate ladder: §4 of this document + §5 of 2026-05-04 plan

---

### Disclaimer

> This work plan is provided for informational and development purposes only. Computational architectures for safety-critical, medical, financial, or regulatory systems must be reviewed by qualified domain engineers before deployment. K_geom values, viscosity correlation coefficients, and warning/blocker thresholds in this plan are placeholders pending calibration against published manufacturer pressure-flow curves and/or wet-lab data. The author is an AI assistant; all designs should be validated through appropriate testing and peer review before production use. v0.7.0 of DPSim explicitly ships as a "research-grade screening simulator with first-principles back-pressure envelopes" — see §4.3 for the public-communication framing constraints.
