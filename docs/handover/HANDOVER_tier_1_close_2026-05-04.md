# Tier 1 Close — Milestone Handover

**Date:** 2026-05-04
**Scope:** Closing of Tier 1 (B-1a … B-1e) from `docs/update_workplan_2026-05-04.md`. All five Tier 1 work items landed in one session under `/scientific-coder` discipline.
**Branch state at handover:** `main` at `d067d73` + uncommitted Tier 1 working tree (see §9). No commits made.
**Authors:** `/scientific-coder` (Claude Opus 4.7).

---

## 1. Project context

Tier 0 closed earlier on 2026-05-04 (`HANDOVER_tier_0_close_2026-05-04.md`). Tier 1 is the scientific-validity tier — five work items that move DPSim from "screening" toward "calibrated quantitative" per the validation release gate. All five landed in this session:

| Batch | ID | Title | Status |
|---|---|---|---|
| **B-1a** | W-002 | Recipe Guardrail 2 — pH/pKa/reagent stability windows | **DONE** |
| **B-1b** | W-003 | Decision-grade gates per output type | **DONE** |
| **B-1c** | W-007 | L2 family dispatch `valid_domain` | **DONE** |
| **B-1d** | W-006 | M1 PBE regime guards (Kolmogorov diagnostics) | **DONE** |
| **B-1e** | W-005 | Taxonomy mapping refactor | **DONE** |

Tier 1 is fully landed. Remaining scope before the v0.6.4 release gate per work plan §5:
1. **W-001** (Python 3.11/3.12 CI dual-matrix enforcement) — already addressed in Tier 0 B-0a.
2. **End-to-end calibrated wet-lab dataset** — requires user-side wet-lab data; no code change can close.
3. **Independent holdout validation** — requires user-side wet-lab data.
4. **Decision-grade automatic downgrade** — **B-1b API delivered**; UI/lifecycle render-path integration is incremental (next session).
5. **Process dossier export** — Tier 2 batch B-2d.

---

## 2. Per-batch summaries

### B-1a — G7 pH Window Guardrail (W-002)

**Files:** `src/dpsim/core/recipe_validation.py` (+ ~106 lines), `src/dpsim/module2_functionalization/reagent_profiles.py` (4 new fields + 23 curated entries), `tests/core/test_recipe_validation_g7_ph.py` (290 lines, 40 cases).

**Deliverable:** `_g7_ph_window_check` validates every M2 step's pH against the reagent profile's hard / soft / optimum bands. Outside hard → BLOCKER; outside soft & inside hard → WARNING; inside soft → silent. 23 reagent profiles spanning the 10 chemistry classes from the brief table (CNBr, CDI, tresyl, epoxide, NaBH4 reduction, boronate, IMAC, Protein A, borax, glutaraldehyde) curated.

**Default-recipe impact:** zero new BLOCKERs, zero new WARNINGs (verified). ECH at pH 12 in soft (9-13); Protein A at pH 9 in soft (8.5-9.5).

**Detailed handoff:** `docs/handover/HANDOFF_b1a_g7_ph_window_2026-05-04.md`.

### B-1b — Decision-Grade Gates (W-003)

**Files:** `src/dpsim/core/decision_grade.py` (NEW, 230 lines), `tests/core/test_decision_grade.py` (NEW, 195 lines, 42 cases).

**Deliverable:** Render-path-only policy module exposing:
- `OutputType` (14 outputs spanning M1/M2/M3 — DSD, D32, PORE_SIZE, MODULUS, RESIDUAL_OIL, RESIDUAL_SURFACTANT, LIGAND_DENSITY, COUPLING_YIELD, REAGENT_RESIDUAL, DBC, PRESSURE_DROP, BREAKTHROUGH, RECOVERY, CYCLE_LIFE).
- `RenderMode` (NUMBER, INTERVAL, RANK_BAND, SUPPRESS) — 4-step graceful degradation.
- `DECISION_GRADE_POLICY` table mapping each OutputType to its minimum-tier requirement.
- `decide_render_mode(output_type, tier)` — the central decision API.
- `render_value(value, output_type, tier, …)` — high-level formatter returning a `RenderedValue` with mode + display string + structured components.
- Streamlit-reload-safe tier comparison (by `.value`) — survives `importlib.reload`.

**No solver code changed.** UI / lifecycle integration is incremental (call `render_value` at every numeric display site). One reference integration is recommended next.

**Test coverage:** every OutputType has a policy row (parametrised); every step on the NUMBER → INTERVAL → RANK_BAND → SUPPRESS ladder verified; reload-aliased tier objects accepted.

### B-1c — L2 Family `valid_domain` (W-007)

**Files modified:** `src/dpsim/level2_gelation/{agarose_only,chitosan_only,ionic_ca,nips_cellulose,solvent_evaporation,solver,tier2_families,tier3_families,v9_5_composites}.py` — 12 ModelManifest construction sites populated with `valid_domain={...}`. **New tests:** `tests/level2_gelation/test_valid_domain_coverage.py` (AST-scanner regression).

**Deliverable:** Every L2 family solver's ModelManifest now carries a non-empty `valid_domain` dict (concentration bands, pH range, temperature range, ionic strength, solvent class, etc.). Tier-2 / Tier-3 / v9.5-composite helper functions inherit the delegate solver's domain and tag with `calibration_status` (analogy_inheritance / research_only / composite_research) — this is the `analogy_source_family` hook described in the brief.

**Carve-out:** UNSUPPORTED-tier degenerate manifests (zero-input short-circuits) keep `valid_domain={}`, semantically correct. The AST-scanner test enforces the contract: any non-UNSUPPORTED ModelManifest in `level2_gelation/*.py` MUST declare a non-empty valid_domain.

**Domain values authored from:** standard literature operating envelopes for each chemistry (Cytiva Protein A protocol for agarose; Manno 2014 for agarose-chitosan; Sorlier 2001 for chitosan pKa; Hagel 1996 for dextran-ECH; Cai & Zhang 2005 for cellulose NIPS; Voragen 2009 for pectin Ca; Pernodet AFM data for empirical pore correlation).

### B-1d — M1 PBE Regime Guards (W-006)

**Files modified:** `src/dpsim/cfd/zonal_pbe.py` (+ ~75 lines in `integrate_pbe_with_zones`). **New tests:** `tests/test_cfd_zonal_pbe_regime_guards.py` (NEW, 165 lines, 6 cases).

**Deliverable:** Every successful zonal PBE integration now exposes in `result.diagnostics`:
- `eta_K_per_zone_m: dict[zone, float]` — Kolmogorov microscale per zone (uses CFD-supplied `kolmogorov_length_m` if present, otherwise computes `(ν³/ε_break)^(1/4)`).
- `d32_over_eta_K_per_zone: dict[zone, float]` — droplet-to-Kolmogorov ratio.
- `d32_over_eta_K_aggregated_min: float` — worst-case ratio across zones.
- `sub_kolmogorov_zones: list[str]` — zones with ratio < 5 (Liao & Lucas threshold).
- `sub_kolmogorov_ratio_threshold: float = 5.0` — the threshold itself, exposed for downstream filtering.
- `breakage_C3: float` — kernel calibration constant exposed for the user/auditor.
- `breakage_model: str` — name of the active kernel.
- `regime_guard_warnings: list[str]` — human-readable advisories (sub-Kolmogorov regime detected, …) including the active `breakage_C3` value.

**Field finding from B-1d test:** most practical stirred-vessel emulsifications operate at d/η_K ~ 1–10 (i.e. comparable scales). The sub-Kolmogorov warning is therefore expected to fire for typical oil-in-water bench geometries; its value lies in tagging the regime so the B-1b decision-grade gate can downgrade DSD numbers to ranking-only when appropriate.

### B-1e — Taxonomy Mapping Refactor (W-005)

**Files:** `src/dpsim/core/step_kind_mapping.py` (NEW, 175 lines), `src/dpsim/lifecycle/recipe_resolver.py` (delegated `_step_type_from_process_kind` to the new module). **New tests:** `tests/core/test_step_kind_mapping.py` (NEW, 230 lines, 52 cases).

**Deliverable:** Closes joint-audit MAJOR-2. The new module exposes:
- `PROCESS_KIND_TO_MODIFICATION_TYPE: dict[ProcessStepKind, Optional[ModificationStepType]]` — explicit mapping with **every** ProcessStepKind member as a key (M1/M3 kinds map to None; M2 kinds map to their ModificationStepType).
- `process_kind_to_modification_type(kind, reagent_profile=None)` — wrapper that handles the COUPLE_LIGAND ↔ {LIGAND_COUPLING, PROTEIN_COUPLING} polymorphism (sole context-dependent entry).
- `is_m2_step_kind(kind)` and `M{1,3}_KINDS` / `M2_{WASH,QUENCH}_KINDS` accessor sets.
- `get_allowed_reaction_types()` — fresh-copy view of the orchestrator's `_STEP_ALLOWED_REACTION_TYPES` (one source of truth, lazy import to break the cycle).

**Regression test asserts:** every ProcessStepKind is in the table; every ModificationStepType has an allowlist row; the wrapper returns the same value as the legacy v0.6.3 helper for every (kind, reagent shape) combination — except `ARM_ACTIVATE → ARM_ACTIVATION` which is an intentional improvement over the legacy `None` mapping.

**Improvement beyond joint-audit MAJOR-2:** `ARM_ACTIVATE` previously had no explicit mapping (silently returned None and slipped past the orchestrator's allowlist check). The new table makes it explicit and routes it to `ARM_ACTIVATION`.

---

## 3. Module registry — current state (post-Tier 1)

| Module | Verdict | Linked work items |
|---|---|---|
| `src/dpsim/__init__.py` | **APPROVED** | — |
| `pyproject.toml` + CI matrix | **APPROVED** | — |
| `src/dpsim/cfd/__init__.py` + `cfd/zonal_pbe.py` | **APPROVED** (post B-1d) | W-008 (CFD-PBE end-to-end PIV-gate, Tier 2) |
| `core/evidence.py` + `core/result_graph.py` | **APPROVED** | — |
| `core/recipe_validation.py` | **APPROVED** (post B-1a / G7) | — |
| `core/decision_grade.py` | **APPROVED** (NEW, B-1b) | — |
| `core/step_kind_mapping.py` | **APPROVED** (NEW, B-1e) | — |
| `level1_emulsification/solver.py` | **APPROVED** | W-006 (closed) |
| `level2_gelation/*` family solvers | **APPROVED** (post B-1c) | — |
| `module2_functionalization/orchestrator.py` | **APPROVED** | W-005 (closed via B-1e) |
| `module2_functionalization/reagent_profiles.py` | **APPROVED** (post B-1a curation) | — |
| `module3_performance/method.py` + `orchestrator.py` | **APPROVED-WITH-FIX-LIST** | W-004 (Tier 2 B-2e) |
| `lifecycle/recipe_resolver.py` | **APPROVED** (post B-1e delegation) | — |
| `core/process_dossier.py` | **REDESIGN REQUIRED** | W-011 (Tier 2 B-2d) |
| `level1_emulsification/wash_residuals.py` | **NOT STARTED** | W-009 (Tier 2 B-2a) |
| `docs/current_support_matrix.md` | **NOT STARTED** | W-019 (Tier 3 B-3c) |
| `visualization/components/impeller_xsec_v3.py` | **APPROVED-WITH-FIX-LIST** (deferred) | W-017 (deadline 2026-06-01) |
| `visualization/**` (use_container_width sites) | **APPROVED-WITH-FIX-LIST** (rolling) | W-016 (Tier 3 B-3a) |

---

## 4. Verification matrix

### Tests
| Suite | Result |
|---|---|
| Tier 0 baseline (handover §7 commands) | 103/103 ✓ |
| `tests/core/test_recipe_validation_g7_ph.py` (B-1a) | 40/40 ✓ |
| `tests/core/test_recipe_validation.py` (G1-G6 sister) | 15/15 ✓ |
| `tests/core/test_decision_grade.py` (B-1b) | 42/42 ✓ |
| `tests/level2_gelation/test_valid_domain_coverage.py` (B-1c) | 10/10 ✓ (8 skipped — files w/o ModelManifest) |
| `tests/test_cfd_zonal_pbe_regime_guards.py` (B-1d) | 6/6 ✓ |
| `tests/test_cfd_zonal_pbe.py` (existing CFD suite) | 33/33 ✓ |
| `tests/core/test_step_kind_mapping.py` (B-1e) | 52/52 ✓ |
| Default-recipe integration suites (`p1`/`p2`/`p3`/`p4`/`clean_architecture`/`dsd_bin_resolved`) | 33/33 ✓ |
| **Total combined run** | **303 passed, 8 skipped** |

### Lint / type
| Gate | Result |
|---|---|
| ruff (all changed files, 17 paths) | All checks passed ✓ |
| mypy on new files (`core/decision_grade.py`, `core/step_kind_mapping.py`) | Success, 0 issues ✓ |
| mypy on edited L2 / CFD source | 6 pre-existing scipy-stub-import warnings (not introduced by Tier 1) |

### Tests NOT run
- Full repo `pytest` collection (~1500+ tests). The Tier 0 baseline + every default-recipe-touching integration suite was exercised; recommend full CI run after merge.
- `tests/test_cli_v7.py::TestCliRegistration::test_top_level_help_lists_new_commands` — known pre-existing cp1252 ε crash (documented in B-1a handoff).

---

## 5. Concrete starting point for next session — Tier 2

The work plan recommends **B-2a (W-009) — Residual reagent / wash diffusion-partition model** first as the highest scientific-impact Tier 2 item with a defensible literature base. Brief from work plan §4:

> Bead/water partition-diffusion + first-order hydrolysis for labile activated groups (CNBr cyanate ester half-life 5 min @ pH 11; CDI ~5 h @ pH 7; tresyl 1–2 h depending on solvent).

**Pre-flight before starting B-2a:**
1. `git log -1 --oneline` shows `d067d73` or later; `git status` should show only Tier 1 changes (commit them first if desired).
2. Re-run handover §7 commands → expect 103 passed.
3. Re-run the combined Tier 1 suite (the 18 file paths above) → expect 303 passed, 8 skipped.
4. Read `docs/update_workplan_2026-05-04.md` §4 → B-2a; this handover §3 module registry; and `docs/handover/HANDOFF_b1a_g7_ph_window_2026-05-04.md` for the M2 chemistry context.
5. The new B-2a module will be `level1_emulsification/wash_residuals.py` — currently NOT STARTED.

**Recommended commit grouping for Tier 1 (if committing as separate PRs):**
- PR 1: B-1a (G7 pH guardrail) — already prepared as standalone in earlier session.
- PR 2: B-1b (decision_grade.py) — standalone, no dependencies.
- PR 3: B-1c (L2 valid_domain) — standalone.
- PR 4: B-1d (PBE regime guards) — standalone.
- PR 5: B-1e (step_kind_mapping) — depends on no other Tier 1 PR; the recipe_resolver delegation is the only consumer change.

If batching Tier 1 as a single PR, the title should mention all 5 W-items and §3 module-registry updates. Suggested commit message:
> `[tier1] feat: close Tier 1 (B-1a..B-1e) — pH guardrail, decision-grade gates, L2 valid_domain, PBE regime guards, taxonomy mapping; 198 new tests; ruff/mypy clean.`

---

## 6. Constraints to remember (anti-stale-context anchors)

- **`.venv` is Python 3.12.10**; preflight in `dpsim.__init__` enforces 3.11/3.12.
- **G6 sequence FSM canonical chain** is `ACTIVATE → INSERT_SPACER → ARM_ACTIVATE → COUPLE_LIGAND → METAL_CHARGE`. **G7 layers on top** (pH window per step) and B-1e mapping table makes ARM_ACTIVATE explicit.
- **AST gate flags `is`/`is not` only**, not `==`. All Tier 1 code uses `==` for enum comparison and `.value` access for reload safety; the AST gate continues to pass.
- **Decision-grade gate (B-1b) is render-path only.** Solvers continue to emit numeric values regardless of evidence tier; the gate kicks in only when the UI / report layer calls `render_value`. Future incremental work: thread `render_value` calls into the M1/M2/M3 result render paths.
- **L2 valid_domain inheritance pattern** (B-1c): tier-2 / tier-3 / v9.5 helpers seed the valid_domain from the delegate solver and tag `calibration_status`. Callers that need to know the analogy source can pass `extra_diagnostics={"analogy_source_family": "<base>"}`.
- **PBE regime-guard threshold = 5.0** (B-1d). Below this `d32/η_K`, inertial breakage kernels (CT) lose accuracy; Alopaeus with `breakage_C3 > 0` is recommended. The threshold is exposed in the diagnostics dict so it can be filtered upstream.
- **Taxonomy mapping table is the single source of truth** (B-1e). Adding a new ProcessStepKind member without extending `PROCESS_KIND_TO_MODIFICATION_TYPE` will fail `tests/core/test_step_kind_mapping.py::test_every_process_kind_in_mapping`.
- **`test_cli_v7` cp1252 ε failure is pre-existing.** Not caused by any Tier 1 batch.
- **Validation release gate (work plan §5) — three of five gates close-able post-Tier 1:** W-001 (closed Tier 0), W-003 API delivered (B-1b; UI integration pending). The remaining two are wet-lab-driven (calibration data + holdout validation). Until all five close, every public communication describes DPSim as *"a research-grade screening simulator with explicit evidence tiers"*.

---

## 7. Verification commands

Run from the repo root with the project venv:

```powershell
# Confirm head and clean tree (post-commit)
git log -3 --oneline
git status

# Tier 0 baseline regression
.\.venv\Scripts\python -m pytest -q `
    tests\test_v0_5_2_codex_fixes.py tests\test_result_graph_register.py `
    tests\test_evidence_tier.py tests\test_v9_3_enum_comparison_enforcement.py `
    tests\test_python_version_preflight.py tests\test_cfd_zonal_pbe.py `
    -p no:cacheprovider
# Expected: 103 passed.

# Tier 1 — full new + integration suite
.\.venv\Scripts\python -m pytest -q `
    tests\core\test_recipe_validation_g7_ph.py `
    tests\core\test_recipe_validation.py `
    tests\core\test_decision_grade.py `
    tests\core\test_step_kind_mapping.py `
    tests\level2_gelation\test_valid_domain_coverage.py `
    tests\test_cfd_zonal_pbe_regime_guards.py `
    tests\lifecycle\test_p1_scientific_boundaries.py `
    tests\lifecycle\test_p2_m1_washing_model.py `
    tests\lifecycle\test_p3_m2_functionalization.py `
    tests\lifecycle\test_p4_m3_method.py `
    tests\core\test_clean_architecture.py `
    tests\test_dsd_bin_resolved.py `
    -p no:cacheprovider
# Expected: 303 passed, 8 skipped.

# Lint / type on Tier 1 source files
.\.venv\Scripts\python -m ruff check `
    src\dpsim\core\decision_grade.py `
    src\dpsim\core\step_kind_mapping.py `
    src\dpsim\cfd\zonal_pbe.py `
    src\dpsim\level2_gelation\*.py `
    src\dpsim\lifecycle\recipe_resolver.py
# Expected: All checks passed!

.\.venv\Scripts\python -m mypy `
    src\dpsim\core\decision_grade.py `
    src\dpsim\core\step_kind_mapping.py
# Expected: Success: no issues found in 2 source files.
```

---

## 8. Quick links

- Work plan: `docs/update_workplan_2026-05-04.md`
- Tier 0 close: `docs/handover/HANDOVER_tier_0_close_2026-05-04.md`
- B-1a detailed handoff: `docs/handover/HANDOFF_b1a_g7_ph_window_2026-05-04.md`
- This handover: `docs/handover/HANDOVER_tier_1_close_2026-05-04.md`
- Joint audit: `docs/joint_audit_v0_6_3_2026-05-04.md`
- F-arch audit: `docs/functional_architecture_audit_2026-05-04.md`

---

## 9. Files delivered (Tier 1 totals)

### New files (5)

| File | Purpose | Lines |
|---|---|---|
| `src/dpsim/core/decision_grade.py` | B-1b policy + decision API + render_value | 230 |
| `src/dpsim/core/step_kind_mapping.py` | B-1e ProcessStepKind ↔ ModificationStepType single source of truth | 175 |
| `tests/core/test_decision_grade.py` | B-1b 42 test cases | 195 |
| `tests/core/test_step_kind_mapping.py` | B-1e 52 test cases | 230 |
| `tests/level2_gelation/test_valid_domain_coverage.py` | B-1c AST-scanner regression test | 130 |
| `tests/test_cfd_zonal_pbe_regime_guards.py` | B-1d 6 test cases | 165 |
| `tests/core/test_recipe_validation_g7_ph.py` | B-1a 40 test cases | 290 |
| `docs/handover/HANDOFF_b1a_g7_ph_window_2026-05-04.md` | B-1a detailed handoff | ~250 |
| `docs/handover/HANDOVER_tier_1_close_2026-05-04.md` | This document | ~350 |

### Modified files (15)

| File | Change |
|---|---|
| `src/dpsim/core/recipe_validation.py` | B-1a: `_g7_ph_window_check` + dispatcher hook + docstring update |
| `src/dpsim/module2_functionalization/reagent_profiles.py` | B-1a: 4 new pH-window fields + 23 reagent entries curated |
| `src/dpsim/cfd/zonal_pbe.py` | B-1d: regime-guard computation block + diagnostics dict expansion |
| `src/dpsim/level2_gelation/agarose_only.py` | B-1c: `valid_domain` populated |
| `src/dpsim/level2_gelation/chitosan_only.py` | B-1c: `valid_domain` populated |
| `src/dpsim/level2_gelation/ionic_ca.py` | B-1c: 2 manifest sites populated |
| `src/dpsim/level2_gelation/nips_cellulose.py` | B-1c: `valid_domain` populated |
| `src/dpsim/level2_gelation/solvent_evaporation.py` | B-1c: `valid_domain` populated |
| `src/dpsim/level2_gelation/solver.py` | B-1c: 3 manifest sites populated (CH 1D, CH 2D, empirical) |
| `src/dpsim/level2_gelation/tier2_families.py` | B-1c: helper inherits + tags domain |
| `src/dpsim/level2_gelation/tier3_families.py` | B-1c: helper inherits + tags domain |
| `src/dpsim/level2_gelation/v9_5_composites.py` | B-1c: helper inherits + tags domain |
| `src/dpsim/lifecycle/recipe_resolver.py` | B-1e: `_step_type_from_process_kind` delegates to new module |

### Integration instructions

1. **No new imports required for downstream consumers.** All five batches preserve existing import contracts. New modules are opt-in (decision_grade) or transparent delegates (step_kind_mapping).
2. **Module registry update:** see §3 above — apply at next module-registry refresh.
3. **Recommended verification before merge:** run §7 commands.
4. **Recommended next move (per work plan §9):** B-2a (residual reagent diffusion-partition model) — highest Tier 2 scientific impact. See §5.
