# Carry-over Close — Milestone Handover

**Date:** 2026-05-04
**Scope:** Close the two deferred carry-overs from `HANDOVER_post_tier_2_close_2026-05-04.md` §5 — B-2e GradientContext consumption in the M3 isotherm/transport adapter, and B-1b decision-grade `render_value` UI integration.
**Branch state at handover:** `main` at `46081db` (the bundled Tier-1+2+post-2 commit) + uncommitted carry-over working tree. No commits made.
**Authors:** `/scientific-coder` (Claude Opus 4.7).

---

## 1. Project context

The Tier 0/1/2 close + post-Tier-2 commit landed all 14 work items closeable from code with two scoped carry-overs noted as "incremental" follow-ons:

| Carry-over | From | Status |
|---|---|---|
| **B-2e GradientContext** consumption in M3 adapter | Tier 2 | **DONE** |
| **B-1b `render_value` UI integration** (helper + reference site) | Tier 1 | **DONE** (helper landed; per-site coverage continues incrementally) |

W-017 visual verification (Streamlit dev session) remains user-side and is not addressable from a coding agent.

---

## 2. Per-batch summaries

### B-2e — GradientContext consumption in M3 adapter

**Files:** `src/dpsim/module3_performance/method.py` (+25 lines, 4 modifications), `tests/module3_performance/test_method_gradient_context.py` (NEW, 165 lines, 12 cases).

**Deliverable:**
- New optional field on `ChromatographyMethodStep`: `gradient_context: GradientContext | None = None`. Old code that passes the legacy `gradient_field` / `gradient_start` / `gradient_end` triple still works exactly as before.
- New helper `_resolve_gradient(step) -> GradientContext | None` — typed-first with legacy fallback. If `step.gradient_context` is set and active, returns it. Otherwise, builds a `GradientContext` on-the-fly from the legacy fields (using `step.duration_s` as the ramp duration). Returns `None` only when no gradient information is available.
- Three call sites in `method.py` refactored to consume the resolved typed object instead of probing `step.gradient_field.lower() == "ph"` and friends:
  - `run_loaded_state_elution` pH_start computation (was lines 651-655).
  - `ph_at_time` closure inside `run_loaded_state_elution` (was lines 676-680).
  - `_elution_pH(step)` helper (was lines 1277-1282).
- `default_protein_a_method_steps()` now populates BOTH the legacy fields (back-compat) AND the new `gradient_context` so every default recipe flows through the typed path.

**Backward-compat contract verified:**
- A step constructed with only legacy fields produces a non-None resolved context whose values match the legacy values (test: `test_legacy_fields_fall_back`).
- A step with both legacy and typed fields prefers the typed context (test: `test_typed_context_preferred`) — this is the migration semantics that lets the caller upgrade incrementally without losing back-compat.
- An inactive (zero-duration) typed context falls back to the legacy fields (test: `test_inactive_typed_context_falls_back_to_legacy`).
- Existing M3 method test suite (`tests/lifecycle/test_p4_m3_method.py`) still passes 3/3 with no recipe changes.

**Out of scope (deferred):** plumbing `GradientContext` through the salt-concentration / imidazole gradient paths in the isotherm adapter. The `gradient_field` discriminator now correctly routes only the "ph" case through the typed path; non-pH gradients continue to fall back to the buffer pH (current behavior). Adding salt/imidazole gradient physics is a separate scientific scope item, not a refactor.

### B-1b — Decision-grade `render_value` UI integration

**Files:** `src/dpsim/visualization/decision_grade_render.py` (NEW, 115 lines), `src/dpsim/visualization/tabs/tab_m3.py` (+20 lines, 1 reference-site wiring), `tests/visualization/test_decision_grade_render.py` (NEW, 195 lines, 15 cases).

**Deliverable — three-layer helper:**
1. `format_decision_graded(value, output_type, tier, *, unit, scale, rank_reference) -> tuple[RenderMode, str]` — pure formatting, no Streamlit. Wraps `core.decision_grade.render_value`. The `scale` kwarg lets callers pre-multiply for display unit conversion (Pa→kPa, m→µm, fraction→%) without affecting the gate decision.
2. `caption_for_mode(mode) -> str` — one-line user-facing explanation of why a value is rendered in a non-NUMBER mode (e.g., "Rendered as ±30 % interval — calibration is one tier below the policy floor for this output.").
3. `render_metric(label, *, value, output_type, tier, unit, scale, rank_reference, help)` — `st.metric` wrapper that composes the formatted display value + the mode-specific caption into the metric's help-tooltip. Backward-compatible `help=` kwarg is concatenated with the auto-caption.

**Reference-site wiring** in `tab_m3.py` "Pressure preview":
- The existing `st.metric("Estimated Pressure Drop", f"{_dP / 1000:.1f} kPa")` call is replaced with `render_metric(..., output_type=OutputType.PRESSURE_DROP, tier=<m2_manifest_tier>, unit="kPa", scale=1.0/1000.0)`.
- Tier sourced from `m2_result.model_manifest.evidence_tier` with a `SEMI_QUANTITATIVE` fallback (matches the PRESSURE_DROP policy floor → still NUMBER mode).
- This site is the canonical example for incremental future per-site PRs.

**Convenience accessor:** `gate_decision_for(output_type, tier) -> RenderMode` — re-exports `decide_render_mode` so a caller that just wants to check "should I draw this chart at all?" can do so without importing from two modules.

---

## 3. Module registry — current state

| Module | Verdict | Note |
|---|---|---|
| `module3_performance/method.py` | **APPROVED** (post-B-2e gradient-context refactor) | typed-first / legacy-fallback resolver |
| `module3_performance/quantitative_gates.py` | **APPROVED** | unchanged this session |
| `visualization/decision_grade_render.py` | **APPROVED** (NEW) | three-layer helper for incremental UI integration |
| `visualization/tabs/tab_m3.py` | **APPROVED** (post-B-1b reference site) | one display site wired; rest are incremental |

All other modules unchanged from the post-Tier-2 close handoff §3.

---

## 4. Verification matrix

### Tests
| Suite | Result |
|---|---|
| Tier 0 baseline | 103/103 ✓ |
| Combined Tier 1+2+post-2+carry-overs + integration (26 files) | **490 passed, 8 skipped** |

Specific new suites added in this session:
- `tests/module3_performance/test_method_gradient_context.py` — 12 cases (B-2e gradient consumption)
- `tests/visualization/test_decision_grade_render.py` — 15 cases (B-1b helpers + reference-site smoke)

Net new this session: **27 tests**.

### Lint / type
| Gate | Result |
|---|---|
| ruff (all 6 changed paths) | All checks passed ✓ |
| mypy on new files (`decision_grade_render.py`, updated `quantitative_gates.py`) | Success, 0 issues ✓ |

---

## 5. Concrete starting point for next session — incremental coverage

The two carry-overs from §5 of the post-Tier-2 handoff are now closed at the **infrastructure level**. Incremental coverage continues:

### B-1b per-display-site rollout
- One reference site (M3 pressure preview) wired in `tab_m3.py`. Future per-site PRs should follow the same pattern: locate `st.metric(...)` / `st.write(f"... = {value:.1f} unit")` calls in `visualization/tabs/`, swap to `render_metric(...)`, and pass the relevant `OutputType` + tier from the upstream manifest.
- Highest-value remaining sites (per the tier-policy → ROI ranking):
  - **DBC** in M3 breakthrough rendering (`tabs/tab_m3.py`, plus `panels/calibration.py`).
  - **d32 / DSD** in M1 result rendering (`tabs/tab_m1.py`).
  - **ligand_density / coupling_yield** in M2 result rendering (`tabs/tab_m2.py`).
  - **residual_oil / residual_surfactant** in the M1 wash report (existing G1 callers + `level1_emulsification/wash_residuals.py` consumers).
- Each site is mechanically ~5-15 lines of change. Recommended chunking: one tab per PR (M1 / M2 / M3) so reviewers can verify visual regressions per-tab.

### B-2e GradientContext rollout
- M3 adapter consumes `GradientContext` for pH gradients. Salt-concentration and imidazole gradients are still buffer-pH-fallback (the existing v0.6.x behavior). Adding salt-gradient physics to the isotherm requires a new scientific scope item (likely Tier 4 or future audit).
- If a recipe-level constructor is added that converts `step.parameters` (the M3 stage of `ProcessRecipe`) into a `GradientContext`, plumb it via `gradient_context_from_recipe_params` (already implemented in B-2e) and set it on the `ChromatographyMethodStep` when materialising the recipe.

### Wet-lab carry-over (user-side)
- End-to-end calibrated M1→M2→M3 dataset (work plan §5 gate 2).
- Independent holdout validation (work plan §5 gate 3).

---

## 6. Constraints to remember (anti-stale-context anchors)

- **B-2e gradient resolver is typed-first / legacy-fallback.** When adding new gradient-aware code in M3, consume `_resolve_gradient(step)` rather than `step.gradient_field.lower()`. The legacy fields stay populated for one major release; do not delete them in a v0.6.x patch.
- **Inactive `GradientContext` (zero duration) falls through to legacy.** This is intentional — it lets a recipe-level constructor pre-populate `gradient_context` with sentinel zeros without accidentally overriding a legacy-supplied gradient. Test `test_inactive_typed_context_falls_back_to_legacy` enforces this.
- **B-1b `render_metric` `scale` is for DISPLAY only.** The decision-grade gate sees the scaled value too, but the policy is unit-agnostic (the tier requirement is a property of the output type, not its unit). Don't be tempted to use `scale` for unit-aware policy logic; that belongs in the policy table.
- **`render_metric` help-text auto-composition:** if a future call site passes its own `help=` and the gate selects a degraded mode, the user help and the auto-caption are joined by a blank line. This is by design — both are user-relevant.
- **Reference-site wiring in `tab_m3.py` uses `m2_result.model_manifest.evidence_tier`** because the pressure preview consumes upstream M2 geometry. When wiring a site that consumes M3 results directly (DBC, recovery), use the M3 result's manifest tier instead. The `_m3_evidence_tier_badge` helper already in `tab_m3.py` shows the canonical access pattern.

---

## 7. Verification commands

Run from the repo root with the project venv:

```powershell
# Tier 0 baseline (unchanged)
.\.venv\Scripts\python -m pytest -q `
    tests\test_v0_5_2_codex_fixes.py tests\test_result_graph_register.py `
    tests\test_evidence_tier.py tests\test_v9_3_enum_comparison_enforcement.py `
    tests\test_python_version_preflight.py tests\test_cfd_zonal_pbe.py `
    -p no:cacheprovider
# Expected: 103 passed.

# All Tier 1+2+post-2+carry-overs + integration (26 files)
.\.venv\Scripts\python -m pytest -q `
    tests\test_cfd_zonal_pbe_regime_guards.py `
    tests\test_cfd_validation_gates.py `
    tests\core\test_recipe_validation.py `
    tests\core\test_recipe_validation_g7_ph.py `
    tests\core\test_decision_grade.py `
    tests\core\test_step_kind_mapping.py `
    tests\core\test_quantities_boundary_helpers.py `
    tests\core\test_process_dossier.py `
    tests\level1_emulsification\test_wash_residuals.py `
    tests\level2_gelation\test_valid_domain_coverage.py `
    tests\module3_performance\test_quantitative_gates.py `
    tests\module3_performance\test_method_gradient_context.py `
    tests\visualization\test_html_helper.py `
    tests\visualization\test_decision_grade_render.py `
    tests\lifecycle\test_p1_scientific_boundaries.py `
    tests\lifecycle\test_p2_m1_washing_model.py `
    tests\lifecycle\test_p3_m2_functionalization.py `
    tests\lifecycle\test_p4_m3_method.py `
    tests\core\test_clean_architecture.py `
    tests\test_dsd_bin_resolved.py `
    -p no:cacheprovider
# Expected: 387 passed, 8 skipped (Tier 0 not included in this slice).

# Lint / type
.\.venv\Scripts\python -m ruff check `
    src\dpsim\module3_performance\method.py `
    src\dpsim\module3_performance\quantitative_gates.py `
    src\dpsim\visualization\decision_grade_render.py `
    src\dpsim\visualization\tabs\tab_m3.py `
    tests\module3_performance\test_method_gradient_context.py `
    tests\visualization\test_decision_grade_render.py
# Expected: All checks passed!
```

---

## 8. Quick links

- Work plan: `docs/update_workplan_2026-05-04.md`
- Support matrix: `docs/current_support_matrix.md`
- Tier 0 close: `docs/handover/HANDOVER_tier_0_close_2026-05-04.md`
- Tier 1 close: `docs/handover/HANDOVER_tier_1_close_2026-05-04.md`
- Tier 2 close: `docs/handover/HANDOVER_tier_2_close_2026-05-04.md`
- Post-Tier 2 close: `docs/handover/HANDOVER_post_tier_2_close_2026-05-04.md`
- This handover: `docs/handover/HANDOVER_carryovers_close_2026-05-04.md`

---

## 9. Files delivered this session

### New files (3)

| File | Purpose | Lines |
|---|---|---|
| `src/dpsim/visualization/decision_grade_render.py` | B-1b Streamlit-side helpers (format / caption / render_metric / gate_decision_for) | 115 |
| `tests/module3_performance/test_method_gradient_context.py` | B-2e gradient-context + resolver tests (12 cases) | 165 |
| `tests/visualization/test_decision_grade_render.py` | B-1b helper + reference-site tests (15 cases) | 195 |
| `docs/handover/HANDOVER_carryovers_close_2026-05-04.md` | This document | ~250 |

### Modified files (2)

| File | Change |
|---|---|
| `src/dpsim/module3_performance/method.py` | B-2e: GradientContext field on ChromatographyMethodStep; `_resolve_gradient` helper; 3 consumer sites refactored; default factory populates both paths |
| `src/dpsim/visualization/tabs/tab_m3.py` | B-1b: reference-site wiring of `render_metric` for the pressure-drop preview |

### Integration instructions

1. **No new imports required for downstream consumers.** B-2e is fully back-compat (legacy fields still work). B-1b is opt-in (callers explicitly invoke `render_metric`).
2. **Recommended commit grouping:**
   - PR A: B-2e gradient-context refactor (`method.py` + tests). Standalone.
   - PR B: B-1b helper module + reference-site wiring + tests. Standalone.
   - OR: bundle as one carry-over close PR.
3. **W-017 visual verification still recommended** (manual `streamlit run` against M1/M2/M3 tabs), unchanged from the post-Tier-2 handoff.

### Suggested commit message (bundle path)

> `[carry-overs] feat: close B-2e GradientContext consumption + B-1b decision-grade UI helpers; reference site wired in tab_m3 pressure preview; 27 new tests; ruff/mypy clean.`
