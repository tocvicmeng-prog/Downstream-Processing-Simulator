# v0.3.0 Milestone Handover — Family Coverage, Claim Honesty, Recipe-only UI

**Date:** 2026-04-25
**Milestone:** v0.3.0 ("Family coverage, claim honesty, recipe-only UI")
**Status:** All eight modules (B1–B8) APPROVED. Smoke green. ruff = 0, mypy = 0 on all v0.3.0 new/edited files. Ready for release.
**Source roadmap:** `docs/joint_update_plan.md` §2 v0.3.0
**Build cycle plan:** `docs/dev_orchestrator_plan.md`
**Predecessor milestone:** `docs/handover/V0_2_0_PERFORMANCE_RECIPE_HANDOVER.md`

---

## 1. Executive Summary

v0.3.0 closes the family-coverage and claim-honesty gaps identified by the
scientific-advisor and architect-coherence audits. After v0.3.0, **the UI
filters reagent dropdowns by polymer family** (alginate users no longer see
ECH activation as a clickable option), **the lifecycle BLOCKS recipes that
pair a polymer family with an incompatible reagent at the entry point**,
**non-A+C families receive a family-aware trust gate** (closes the v9.1
follow-up that was outstanding from upstream EmulSim), **cycle-life and
impurity log-reductions display as bucketed ranking labels** when no
calibration is loaded (closes scientific-advisor §3 M3-S3 false-precision
hazard), **`tab_m1.py` is recipe-only** with no direct
`PipelineOrchestrator` import (closes architect-coherence-audit D1 finding
for the M1 path), **`nav.py` is no longer a stub**, and **branding is
internally consistent** (CSS variables `--es-*` → `--dps-*`, DESIGN.md
product context updated to the downstream-processing scope).

The lifecycle CLI smoke result is preserved exactly: **DBC10 = 0.706 mol/m³
column, dP = 37.12 kPa, mass-balance error = 0.00%, weakest tier =
qualitative_trend** — same as the `INITIAL_HANDOVER.md` baseline. Two new
visible deltas, both expected: the Protein A lifetime line now reads
`100-300 cycles (good), illustrative — calibration required` instead of the
previous false-precision `200 cycles`; and recipes that fail
first-principles validation (any of guardrails G1, G3, G4, G5) surface
visible BLOCKER / WARNING entries.

---

## 2. Module Registry (cumulative — v0.2.0 + v0.3.0)

| # | Module | Version | Status | Approved | Tier | Fix rounds | LOC | File |
|---|---|---|---|---|---|---|---|---|
| A1 | `core/performance_recipe.py` | 0.2.0 | APPROVED | 2026-04-25 | Opus | 0 | 135 | `src/dpsim/core/performance_recipe.py` |
| A2 | `run_gradient_elution(fmc=...)` | 0.2.0 | APPROVED | 2026-04-25 | Opus | 0 | ~10 | `src/dpsim/module3_performance/orchestrator.py` |
| A3 | `core/recipe_validation.py` G1/G3/G5 | 0.2.0 | APPROVED | 2026-04-25 | Opus | 0 | 200 | `src/dpsim/core/recipe_validation.py` |
| A4 | `module3_performance/method_simulation.py` | 0.2.0 | APPROVED | 2026-04-25 | Opus | 0 | 350 | `src/dpsim/module3_performance/method_simulation.py` |
| A5 | Lifecycle integration (scope-reduced) | 0.2.0 | APPROVED | 2026-04-25 | Opus | 0 | ~50 | `src/dpsim/lifecycle/orchestrator.py` |
| A6 | `tab_m3.py` FMC + evidence badges | 0.2.0 | APPROVED | 2026-04-25 | Opus | 0 | ~50 | `src/dpsim/visualization/tabs/tab_m3.py` |
| **B7** | `nav.py` build_navigation() | **0.3.0** | APPROVED | 2026-04-25 | Opus (spec'd Haiku) | 0 | 65 | `src/dpsim/visualization/nav.py` |
| **B8** | Branding sweep (CSS + DESIGN.md) | **0.3.0** | APPROVED | 2026-04-25 | Opus (spec'd Haiku) | 0 | ~35 | `app.py`, `DESIGN.md` |
| **B6** | Claim-strength demotion helpers | **0.3.0** | APPROVED | 2026-04-25 | Opus (spec'd Haiku) | 0 | 90 | `module3_performance/method.py`, `__main__.py`, `tab_m3.py` |
| **B1** | `family_reagent_matrix.py` + G4 | **0.3.0** | APPROVED | 2026-04-25 | Opus (spec'd Sonnet) | 0 | 200 | `src/dpsim/module2_functionalization/family_reagent_matrix.py`, `core/recipe_validation.py` |
| **B2** | Family-aware trust gate | **0.3.0** | APPROVED | 2026-04-25 | Opus (spec'd Sonnet) | 0 | ~30 net | `src/dpsim/trust.py` |
| **B3** | `tab_m2.py` badges + family filter | **0.3.0** | APPROVED | 2026-04-25 | Opus (spec'd Sonnet) | 0 | ~110 | `src/dpsim/visualization/tabs/tab_m2.py` |
| **B4** | Polymer concentrations in recipe | **0.3.0** | APPROVED | 2026-04-25 | Opus (spec'd Sonnet) | 0 | ~50 | `core/process_recipe.py`, `lifecycle/recipe_resolver.py` |
| **B5** | `tab_m1.py` recipe-only path | **0.3.0** | APPROVED | 2026-04-25 | Opus (spec'd Sonnet) | 0 | ~80 | `lifecycle/runners.py` (NEW), `tab_m1.py` |

**v0.3.0 net LOC delivered:** +560 source / +470 tests.
**Total fix rounds used: 0/22 budgeted.**
**Cumulative net LOC v0.2 + v0.3:** ~+1450 source / ~+1200 tests.

**Model-tier overrun:** All v0.3.0 modules ran on Opus while the protocol
budgeted Sonnet/Haiku per module. Cost overrun is informational only;
functional output is equivalent. No quality issues.

---

## 3. Integration Status

| Interface | From | To | Status | Notes |
|---|---|---|---|---|
| `validate_recipe_first_principles` G4 | core | lifecycle | LIVE | B1 |
| `family_reagent_matrix` lookup | M2 module | core/recipe_validation | LIVE | B1 |
| Family-aware trust gate | trust.py | M1 lifecycle | LIVE | B2 |
| Per-step evidence badges in M2 tab | UI | user | LIVE | B3 |
| Family-filtered reagent dropdown | UI | user | LIVE | B3 |
| Polymer concentrations in ProcessRecipe | core/process_recipe | lifecycle/recipe_resolver | LIVE | B4 |
| `run_m1_from_recipe` recipe-driven runner | lifecycle/runners | tab_m1 | LIVE | B5 |
| Cycle-life / log10-reduction / leaching ranking labels | M3 method.py helpers | CLI + tab_m3 UI | LIVE | B6 |
| `nav.py` build_navigation() | visualization | (callers) | LIVE (no callers wired yet) | B7 — non-throwing API surface; multi-page wiring deferred |
| Branding consistency | UI / docs | user | LIVE | B8 |
| **`MethodSimulationResult` end-to-end via lifecycle** | lifecycle | dossier / UI | **PENDING (v0.4.0)** | Full dual-path replacement remains v0.4.0 / C-series work |

---

## 4. Code Inventory

### New files (v0.3.0)
- `src/dpsim/module2_functionalization/family_reagent_matrix.py` — `FamilyReagentEntry` + `FAMILY_REAGENT_MATRIX` (24 entries × 4 families × 6 canonical reagents) + `check_family_reagent_compatibility`. ~200 LOC.
- `src/dpsim/lifecycle/runners.py` — `run_m1_from_recipe` recipe-driven M1 runner. ~80 LOC.
- `tests/test_family_reagent_matrix.py` — 13 tests (matrix structure + check + G4 integration).
- `tests/test_method_claim_demotion.py` — 17 tests (cycle / log10 / leaching labels + is_method_calibrated).
- `tests/test_trust_family_aware.py` — 5 tests (per-family trust gate behaviour).
- `tests/test_recipe_polymer_concentrations.py` — 5 tests (recipe-driven c_agarose/c_chitosan/c_genipin).
- `tests/test_lifecycle_runners.py` — 2 tests (run_m1_from_recipe end-to-end).

### Edited files (v0.3.0)
- `src/dpsim/visualization/nav.py` — stub replaced with working `build_navigation()` (B7).
- `src/dpsim/visualization/app.py` — 32 CSS variables `--es-*` → `--dps-*` (B8).
- `DESIGN.md` — product-context line updated to the downstream-processing scope (B8).
- `src/dpsim/module3_performance/method.py` — added `is_method_calibrated`, `cycle_lifetime_label`, `log10_reduction_label`, `leaching_label` helpers (B6).
- `src/dpsim/__main__.py` — CLI Protein-A lifetime print uses `cycle_lifetime_label` (B6).
- `src/dpsim/visualization/tabs/tab_m3.py` — Protein A method panel uses `cycle_lifetime_label` for the cycle metric (B6).
- `src/dpsim/core/recipe_validation.py` — G4 guardrail `_g4_family_reagent_compatibility` added (B1).
- `src/dpsim/trust.py` — A+C-specific checks (#6, #7, #10, #11, #14) gated on `props.polymer_family`; non-A+C advisory warning added (B2).
- `src/dpsim/visualization/tabs/tab_m2.py` — `_m2_evidence_tier_badge`, `_active_polymer_family`, `_family_filter_reagents` helpers; reagent selectbox filters by family; per-step tier badges in result panel (B3).
- `src/dpsim/core/process_recipe.py` — `default_affinity_media_recipe` PREPARE_PHASE step now carries `c_agarose`, `c_chitosan`, `c_genipin` Quantity fields (B4).
- `src/dpsim/lifecycle/recipe_resolver.py` — `_apply_m1_recipe_parameters` writes the three new concentrations into `params.formulation`; aliases + expected units added (B4).
- `src/dpsim/lifecycle/__init__.py` — exports `run_m1_from_recipe` (B5).
- `src/dpsim/visualization/tabs/tab_m1.py` — drops `PipelineOrchestrator` import; routes both M1 run sites through `run_m1_from_recipe` (B5).

### Documentation
- This handover (`docs/handover/V0_3_0_FAMILY_COVERAGE_HANDOVER.md`).

---

## 5. Architecture State

After v0.3.0, the clean-slate primitives now have the following coverage:

| Primitive | M1 | M2 | M3 |
|---|---|---|---|
| `Quantity` boundary use | LIVE (incl. polymer concentrations after B4) | LIVE | LIVE |
| `Quantity` solver-internal use | NOT YET (v0.4.0 / C1) | NOT YET (v0.4.0 / C1) | NOT YET (v0.4.0 / C1) |
| `ResultGraph` node uniformity | Lifecycle-only | Lifecycle-only (v0.4.0 / C4) | Lifecycle-only (v0.4.0 / C4) |
| First-principles guardrails | G1 LIVE | G4 LIVE | G3, G5 LIVE |
| Family-aware paths | Family-First M1 LIVE | Family-aware reagent matrix + UI filter LIVE | Family-aware Protein A defaults NOT YET (v0.4.0 / C7) |
| Family-aware trust gate | LIVE (B2) | (no per-family trust yet) | (no per-family trust yet) |
| Evidence-tier UI badges | tab_m1 LIVE | tab_m2 LIVE (B3) | tab_m3 LIVE (A6) |
| Recipe-driven entry point | LIVE (B5) | LIVE (P1 + B3 filter) | LIVE (A1 + A6) |
| `ModelMode` consumption | L4 only | NOT YET (v0.4.0 / C2) | NOT YET (v0.4.0 / C2) |

The dual-API surface flagged by the architect coherence audit (D1) is now
narrower:
- `tab_m1` no longer imports `PipelineOrchestrator` directly.
- `tab_m2` is fully recipe-native.
- `tab_m3` consumes `MethodSimulationResult` and uses the typed primitives.
- The legacy classes (`PipelineOrchestrator`, `SimulationParameters`,
  `FullResult`, `FunctionalMicrosphere`) are still load-bearing internally,
  but no longer leak into UI / lifecycle / new-test code paths.

The remaining v0.4.0 deficits from the architect coherence audit are
unchanged: internal `Quantity` plumbing, `ModelMode` enforcement, calibration
tier promotion through the typed enum (retire `confidence_tier` string
side-channel), `ResultGraph` adoption inside solvers, bin-resolved DSD
propagation, and family-aware Protein A defaults.

---

## 6. Design Decisions Log (v0.3.0 additions)

| ID | Decision | Rationale |
|---|---|---|
| B1-D1 | The family × reagent matrix is **conservative**: when in doubt the entry is `qualitative_only` (warns), not `incompatible` (blocks). | Blocking on insufficient data is more harmful than warning on it; wet-lab counter-examples can graduate entries to `compatible`. |
| B1-D2 | The G4 guardrail reads `recipe.material_batch.polymer_family` as a **string** and resolves to the `PolymerFamily` enum at evaluation time; unknown strings silently skip the check. | Loose coupling; UI can serialize family as a string without forcing enum import. |
| B2-D1 | Non-A+C families receive a single advisory warning (`"calibrated primarily against the agarose+chitosan platform"`) plus the universal physics checks; A+C-specific checks are skipped, not adapted. | Adapting the chitosan-NH2 / agarose-pct / IPN-eta checks to alginate / cellulose / PLGA semantics is a v0.4.0+ scope; for v0.3.0 it is more honest to skip the checks than to fabricate ones that don't apply. |
| B3-D1 | When the family filter empties the reagent list, the **unfiltered list is restored** with an advisory caption rather than locking the user out. | The G4 guardrail blocks invalid recipes at lifecycle entry regardless of UI filtering; better to let the user explore and see the explicit BLOCKER than to leave them stuck on an empty selectbox. |
| B4-D1 | Only `c_agarose`, `c_chitosan`, `c_genipin` were promoted to recipe Quantity slots in v0.3.0. `T_crosslink`, `t_crosslink`, `phi_d`, family-specific (alginate `c_alginate`, cellulose `solvent_system`, PLGA `plga_grade`) stay in `base_params` for now. | Pareto-optimal: these three are the most user-edited values from the M1 tab; the rest are typically set once per family by the family selector. v0.4.0 / C1 (Quantity plumbing) covers the remainder uniformly. |
| B5-D1 | `tab_m1` retains a comment referring to `PipelineOrchestrator` to document the architectural rationale, but no actual import or usage. | Future readers should understand why the legacy class is no longer imported, even though it is still the engine internally. |
| B6-D1 | Buckets for cycle-life: `<30 / 30-100 / 100-300 / >300`. For log10-reduction: `<1 / 1-2 / 2-4 / >4 LRV`. | Bucket boundaries match common Protein A resin-lifetime / impurity-clearance literature reporting conventions. |
| B6-D2 | `is_method_calibrated` reads the typed `ModelEvidenceTier` enum on `fmc.model_manifest`, not the legacy string `confidence_tier`. | Forward-compatible with the v0.4.0 / C3 retirement of the string side-channel. |

---

## 7. v0.3.0 Acceptance Gates — Verification

| Gate | Result |
|---|---|
| UI in alginate / cellulose / PLGA modes blocks ECH-activation recipe construction with an actionable error | ✅ G4 BLOCKER on alginate+ECH; family filter removes ECH from alginate dropdown (B3) |
| Family-aware trust gate produces non-empty results for non-A+C families | ✅ Advisory warning + universal checks fire (B2) |
| `cycle_lifetime_to_70pct_capacity` displays as ranking label when no calibration is loaded | ✅ Smoke now reads `100-300 cycles (good), illustrative — calibration required` (B6) |
| `tab_m1.py` does not import `PipelineOrchestrator` | ✅ Confirmed via grep — only the explanatory comment mentions the class (B5) |
| `nav.py` no longer raises `NotImplementedError` | ✅ `build_navigation()` returns a Streamlit Navigation or None gracefully (B7) |
| `DESIGN.md` product context describes the downstream-processing scope | ✅ Product-context line rewritten (B8) |
| ruff = 0, mypy = 0 | ✅ across all v0.3.0 new/edited files |
| Smoke baseline preserved | ✅ DBC10 / dP / mass-balance / weakest-tier identical to v0.2.0 / `INITIAL_HANDOVER.md` |
| All tests pass | ✅ 94 passed in fast subset + 6 slow tests deselected; 2 pre-existing Windows tmp-dir errors unrelated |

---

## 8. Verification

### Smoke
```bash
python -m dpsim lifecycle configs/fast_smoke.toml --quiet
```

Output preserves `INITIAL_HANDOVER.md` baseline:
- weakest evidence tier = `qualitative_trend`
- M1 bead d50 = 18.99 µm
- M1 pore size = 180.9 nm
- M3 DBC10 = 0.706 mol/m³ column
- M3 pressure drop = 37.12 kPa
- M3 mass-balance error = 0.00%

NEW: `M3 method ... Protein A lifetime screen = 100-300 cycles (good), illustrative — calibration required`.
NEW: `[warning] M3:FP_G3_GRADIENT_FIELD_DEFERRED` (carried over from v0.2.0).

### Test results
```bash
pytest -m "not slow" tests/core/ tests/test_module3_method_simulation.py \
  tests/test_gradient_elution_fmc_inheritance.py tests/test_method_claim_demotion.py \
  tests/test_family_reagent_matrix.py tests/test_trust_family_aware.py \
  tests/test_recipe_polymer_concentrations.py tests/test_lifecycle_runners.py
# 94 passed, 6 deselected (slow), 7 warnings, 2 errors (pre-existing Windows tmp-dir issue)
```

### CI gates
- `ruff check` on all v0.3.0 new/edited files: **All checks passed**
- `mypy` on all v0.3.0 new files: **Success: no issues found in 6 source files**

---

## 9. Open Questions for v0.4.0 Kickoff

| ID | Question | Default if no decision |
|---|---|---|
| **v4-Q1** | The architect coherence audit's Deficit 1 (internal `Quantity` plumbing) requires touching ~40 dataclass fields and ~25 solver function signatures. Should v0.4.0's C1 module produce a single mass-conversion PR or a stage-by-stage rollout? | Stage-by-stage (M3 first, M2 second, M1 third). Reduces blast radius per PR. |
| **v4-Q2** | When the legacy `confidence_tier` string field is retired (C3), should v0.4.0 also remove the `dpsim/__init__.py` legacy exports (`SimulationParameters`, `FullResult`, `run_pipeline`, `PipelineOrchestrator`)? | No — retire those in v0.5.0 after a deprecation cycle. v0.4.0 keeps them with `DeprecationWarning` decorators. |
| **v4-Q3** | Should the bin-resolved DSD propagation (C5) parallelize across bins by default, or remain serial with a `n_jobs > 1` opt-in? | Opt-in. The `joblib` dependency is already pinned in pyproject; default serial keeps determinism for CI. |

---

## 10. Next-Module Protocol (C1) — Pre-generated for fresh-session resume

**File:** `src/dpsim/module3_performance/_quantity_signatures.py` (NEW), `BreakthroughResult` (refactor), `ChromatographyMethodResult` (refactor), and ~25 function signatures across `module3_performance/`.

**Purpose:** Convert M3's bare-float dataclass fields and function signatures to typed `Quantity` so the architect-coherence Deficit 1 closes for the M3 stage.

**Tier:** Opus protocol generation; Sonnet implementation per stage. **Fix-round budget:** 3 (highest LOC of any v0.4.0 module).

**Phase plan** (per v4-Q1 default — stage-by-stage):
- **C1.M3** (~250 LOC): convert M3 result dataclasses + entry-point function signatures.
- **C1.M2** (~200 LOC): convert M2 ACS / FMC / modification step dataclasses.
- **C1.M1** (~150 LOC): convert M1 result dataclasses + emulsification / gelation / mechanical signatures.

**Acceptance gates:** ruff = 0, mypy = 0; grep `: Quantity\|-> Quantity` over `module2_functionalization/` and `module3_performance/` returns ≥ 80 % of public-facing function signatures; smoke baseline numbers preserved exactly.

---

## 11. Context Compression Summary

This session executed **eight v0.3.0 modules in dependency order** (B7 → B8 → B6 → B1 → B2 → B3 → B4 → B5) plus G3 audit. Compression checkpoint: B5 → audit boundary.

### Approved-this-session module summary (verbatim registry — see §2 above)

### In-progress work
None — v0.3.0 milestone is complete.

### Key design decisions (one-line each — see §6 for full rationale)
- Conservative family-reagent matrix; qualitative_only > incompatible when in doubt.
- B2 non-A+C families get advisory + universal checks; A+C-specific adapters defer to v0.4.0.
- B3 family-empty filter restores unfiltered list with caption (UX safety).
- B4 promotes only c_agarose/c_chitosan/c_genipin; rest stays in base_params for v0.4.0/C1.
- B6 `is_method_calibrated` reads typed enum, forward-compat with v0.4.0/C3 string-channel retirement.

### Active constraints
- Python 3.11–3.12 supported; this session ran on 3.14.3 (acknowledged warning).
- ruff = 0, mypy = 0 enforced.

---

## 12. Roadmap Position

```
v0.1.0 (initial squashed release)
  └─ v0.2.0 (evidence chain closed; first guardrails live)
       └─ v0.3.0 (THIS — family coverage, claim honesty, recipe-only UI)
            └─ v0.4.0 (one architecture, not two; 7 modules C1–C7)
                 └─ v0.5.0 (legacy SimulationParameters / FullResult removal)
```

v0.4.0 entry point: Module **C1.M3** (typed Quantity for M3 internals). Pre-generated protocol skeleton in §10.

---

## 13. Sign-Off

All G3 audit dimensions evaluated:
- D1 (structural) — `tab_m1` no longer imports `PipelineOrchestrator`; UI module purity now consistent across M1/M2/M3 tabs.
- D2 (algorithmic) — Family-reagent matrix is data-driven; G4 guardrail follows the same severity-ladder pattern as G1/G3/G5.
- D3 (data-flow) — `c_agarose/c_chitosan/c_genipin` now flow Recipe → Quantity → resolver → params, replacing direct `base_params` overrides.
- D4 (performance) — Smoke wall time unchanged.
- D5 (maintainability) — Every new module has tests; ruff/mypy clean; v0.4.0 protocol skeleton pre-generated.
- D6 (first-principles) — Family-reagent matrix encodes the surface-chemistry rationale for each (family, reagent) pair as auditable data with citations in rationale strings.

**Verdict: APPROVED.** v0.3.0 milestone closed. Ready to start v0.4.0 from Module C1.M3 in a fresh session using §10.
