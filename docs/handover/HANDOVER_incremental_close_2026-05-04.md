# Incremental Close — Milestone Handover

**Date:** 2026-05-04
**Scope:** Finish the incremental work flagged in `HANDOVER_carryovers_close_2026-05-04.md` §5 — B-1b per-display-site rollout across M1/M2/M3 and B-2e salt/imidazole gradient time-profile scaffolding.
**Branch state at handover:** `main` at `5aa255e` (the carry-over close commit) + uncommitted incremental working tree. No commits made yet.
**Authors:** `/scientific-coder` (Claude Opus 4.7).

---

## 1. Project context

The carry-over close commit landed the B-1b helper module + 1 reference site (M3 pressure-drop preview) and the B-2e GradientContext consumption in the M3 adapter. Its §5 listed three follow-on items as incremental:

| Item | Status |
|---|---|
| Per-display-site rollout of `render_metric` across M1/M2/M3 | **DONE** (12 high-impact metrics wired across 5 callsites in M1 + 5 in M3) |
| Salt/imidazole gradient time profile (scaffolding for the deferred isotherm physics) | **DONE** (generic `gradient_value_at_time` + `LoadedStateElutionResult.gradient_diagnostics` field) |
| W-017 visual verification (`streamlit run`) | **NOT DONE** — manual user-side; cannot be done from a coding agent |

---

## 2. Per-batch summaries

### B-1b rollout — M1 + M3 metric wiring

**Files:** `src/dpsim/visualization/decision_grade_render.py` (extended `render_metric` signature with `delta` / `delta_color` / `container` passthroughs), `src/dpsim/visualization/tabs/tab_m1.py` (2 callsites, 8 metrics), `src/dpsim/visualization/tabs/tab_m3.py` (2 callsites, 5 metrics).

**Helper extension (1 file, +12 lines):**
- `render_metric` now accepts `delta`, `delta_color`, `container` kwargs. The first two passthrough directly to `st.metric` (used by existing M1 dashboard sites for "X% from target"). `container=col` is equivalent to `col.metric(...)` so callers don't need a `with col:` block — keeps the migration to one line per site.

**M1 wiring (12 metrics across 2 sites):**
- `tab_m1.py:394-397` — family-neutral results display: `d_mode`/`d32`, `Pore size`, `Porosity` (left as plain `st.metric` — not in the policy table), `G (modulus)`. Tier sourced from each level's `model_manifest.evidence_tier`.
- `tab_m1.py:1217-1232` — dashboard KPIs with target-deviation deltas: `d_mode`/`d32`, `Pore Size`, `G_DN` (with two delta variants — Hashin-Shtrikman ref bounds vs. % from target).

**M3 wiring (5 metrics across 2 sites):**
- `tab_m3.py:808-812` (was) — Breakthrough subtab: `DBC₅%`, `DBC₁₀%`, `DBC₅₀%`, `Pressure drop`. NaN guard preserved (legacy `st.metric` for "N/A").
- `tab_m3.py:931` (was) — Method subtab: `Elution recovery` (RECOVERY policy floor = VALIDATED_QUANTITATIVE).

**Tier sourcing pattern** (canonical for future PRs):

```python
_tier = (
    getattr(getattr(result_obj, "model_manifest", None),
            "evidence_tier", None)
    or ModelEvidenceTier.SEMI_QUANTITATIVE
)
```

The fallback to `SEMI_QUANTITATIVE` (the typical in-tree default) keeps display behavior unchanged for results that don't carry an explicit manifest tier.

**Sites NOT wired (intentional carry-over):**
- M2 tab — outputs are mostly per-step diagnostic captions (`st.write(f"... conversion {x:.1%}...")`), not headline `st.metric` calls. Highest leverage for M2 chemistry surfaces via M3 DBC/recovery (already wired).
- M3 cycle-life rendering — already has its own bucketed-ranking logic (v0.3.0 B6) that mirrors the decision-grade ladder semantics. Migrating it would be churn for no behavior change.
- Plots (`plots_m3.py`) — DBC annotations live on plotly figures, not Streamlit widgets. Visual gating via plot annotations is a follow-on UX exploration.

### B-2e — Salt/imidazole gradient time profile (scaffolding)

**Files:** `src/dpsim/module3_performance/method.py` (~50 line refactor), `tests/module3_performance/test_method_gradient_context.py` (+85 lines, 4 new cases).

**Deliverable:**
- New inner helper `gradient_value_at_time(t)` inside `run_loaded_state_elution`. Returns the active gradient's value at time `t` (linear ramp; the only shape v0.6.x supports). Returns `None` when no active gradient.
- `ph_at_time(t)` refactored to delegate to the generic helper (was: open-coded linear interpolation).
- New optional field on `LoadedStateElutionResult`: `gradient_diagnostics: dict | None = None`. Backward-compatible default.
- Populated whenever the active gradient is non-pH (salt, imidazole). Carries:
  - `field`, `start_value`, `end_value`, `duration_s`, `shape` — the full `GradientContext` envelope.
  - `values: np.ndarray` — per-time-sample gradient value (linearly interpolated).
  - `isotherm_consumes: False` — explicit flag so downstream consumers know the binding physics ignores the value.
  - `advisory: str` — human-readable "what this means" caveat.

**Critical scope-boundary note:**
The isotherm / transport adapter does **not** yet consume non-pH gradient values. Adding salt-dependent K_a (e.g., stoichiometric displacement model, Mollerup-style ion-exchange) or imidazole-competition kinetics is a **scientific scope item** that requires:
1. Scientific Advisor input on the appropriate isotherm formulation.
2. Wet-lab calibration data for the new parameter set.
3. A separate ADR documenting the physics choice.

The diagnostic envelope this PR delivers is the plumbing that makes a future scientific PR a one-line wire-up at the consumer side rather than another adapter refactor.

---

## 3. Module registry — current state

| Module | Verdict | Note |
|---|---|---|
| `visualization/decision_grade_render.py` | **APPROVED** | extended with `delta`/`delta_color`/`container` passthroughs |
| `visualization/tabs/tab_m1.py` | **APPROVED** (post-B-1b rollout) | 8 metrics gated; full coverage of headline M1 outputs |
| `visualization/tabs/tab_m3.py` | **APPROVED** (post-B-1b rollout) | 5 metrics gated; cycle-life intentionally retained |
| `module3_performance/method.py` | **APPROVED** (post-B-2e scaffolding) | gradient_value_at_time + LoadedStateElutionResult.gradient_diagnostics |

All other modules unchanged from the carry-over close handoff §3.

---

## 4. Verification matrix

### Tests
| Suite | Result |
|---|---|
| Tier 0 baseline | 103/103 ✓ |
| Combined Tier 1+2+post-2+carry-overs+incremental + integration (26 files) | **494 passed, 8 skipped** |

Specific new tests added in this session:
- `tests/module3_performance/test_method_gradient_context.py` — +4 cases for `TestSaltGradientScaffolding` (pH does not populate diag; salt/imidazole populate diag with `isotherm_consumes=False`; no gradient → no diag).

Net new this session: **4 tests**.

### Lint / type
| Gate | Result |
|---|---|
| ruff (all 5 changed paths) | All checks passed ✓ |
| mypy on `decision_grade_render.py` | Success, 0 issues ✓ |

---

## 5. Concrete starting point for next session

The three Tier 1/2 carry-over items are now closed. Remaining work is now genuinely user-side or future-scope:

### User-side (cannot be done from coding agent)
1. **W-017 visual verification** — `streamlit run` against the M1/M2/M3 tabs. If DOMPurify in Streamlit ≥ 1.39 strips SVG attributes from the impeller / column cross-sections, set `DPSIM_USE_LEGACY_HTML=1` and file a follow-up to either pre-sanitise the HTML or relax the wrapper.
2. **Wet-lab calibration data** — closes work plan §5 gates 2 and 3 (end-to-end calibrated dataset + independent holdout validation).

### Future scientific scope (requires Scientific Advisor + ADR)
1. **Salt-dependent isotherm physics** — stoichiometric displacement model (SDM) or Mollerup-style ion-exchange. The B-2e scaffolding (`LoadedStateElutionResult.gradient_diagnostics`) gives downstream consumers a typed handle to the gradient envelope; the consumer wire-up becomes ~5 lines once the isotherm exists.
2. **Imidazole-competition for IMAC elution** — analogous physics scope.
3. **B-1b plot annotations** — wire decision_grade decisions into plotly chart annotations (not just Streamlit widgets). UX exploration; lower priority than the headline metric coverage.

### Tier 3 cosmetic carry-overs from earlier closes
- B-3a Streamlit `use_container_width` sweep is complete; W-016 closed.
- B-3c support matrix is in place and updated through this session.

**No new tier of work plan items remains open.** Every numbered W-item is either closed in code, deferred to a documented future scientific scope, or pending wet-lab data.

---

## 6. Constraints to remember (anti-stale-context anchors)

- **`render_metric` `container` kwarg accepts a Streamlit column / container** — `container=col` replaces `col.metric(...)`. This is the migration shape for any remaining per-display-site work; do NOT introduce `with col:` blocks just to accommodate the helper.
- **`render_metric` `scale` is for DISPLAY only.** The decision-grade gate sees the scaled value too, but the policy floor is unit-agnostic. Use `scale` for unit conversion (Pa→kPa, m→µm, fraction→%), not for masking a tier policy.
- **B-2e `LoadedStateElutionResult.gradient_diagnostics` is `None` for pH gradients** because pH_profile already carries the envelope. Non-pH gradients populate the field with `isotherm_consumes=False` to signal that the binding physics has not yet been extended.
- **Tier sourcing pattern** for any future per-site B-1b work: read `result_obj.model_manifest.evidence_tier` with a `SEMI_QUANTITATIVE` fallback. Do NOT hard-code `VALIDATED_QUANTITATIVE` — the rendering must reflect the actual upstream evidence.
- **Cycle-life UI in `tab_m3.py` already implements bucketed-ranking** (v0.3.0 B6) that mirrors the decision-grade ladder. Don't re-migrate it; the existing logic is correct and the migration would be churn.

---

## 7. Verification commands

Run from the repo root with the project venv:

```powershell
# Tier 0 baseline
.\.venv\Scripts\python -m pytest -q `
    tests\test_v0_5_2_codex_fixes.py tests\test_result_graph_register.py `
    tests\test_evidence_tier.py tests\test_v9_3_enum_comparison_enforcement.py `
    tests\test_python_version_preflight.py tests\test_cfd_zonal_pbe.py `
    -p no:cacheprovider
# Expected: 103 passed.

# Full Tier 1+2+post-2+carry-overs+incremental + integration (26 files)
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
# Expected: 391 passed, 8 skipped.

# Lint / type
.\.venv\Scripts\python -m ruff check `
    src\dpsim\visualization\decision_grade_render.py `
    src\dpsim\visualization\tabs\tab_m1.py `
    src\dpsim\visualization\tabs\tab_m3.py `
    src\dpsim\module3_performance\method.py `
    tests\module3_performance\test_method_gradient_context.py
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
- Carry-over close: `docs/handover/HANDOVER_carryovers_close_2026-05-04.md`
- This handover: `docs/handover/HANDOVER_incremental_close_2026-05-04.md`

---

## 9. Files delivered this session

### Modified files (4)

| File | Change |
|---|---|
| `src/dpsim/visualization/decision_grade_render.py` | Extended `render_metric` with `delta`/`delta_color`/`container` passthroughs |
| `src/dpsim/visualization/tabs/tab_m1.py` | B-1b rollout: 8 metrics across 2 callsites (results display + dashboard KPIs) |
| `src/dpsim/visualization/tabs/tab_m3.py` | B-1b rollout: 5 metrics across 2 callsites (DBC + pressure + recovery) |
| `src/dpsim/module3_performance/method.py` | B-2e scaffolding: `gradient_value_at_time` + `LoadedStateElutionResult.gradient_diagnostics` |

### Modified test (1)

| File | Change |
|---|---|
| `tests/module3_performance/test_method_gradient_context.py` | +4 `TestSaltGradientScaffolding` cases for the gradient_diagnostics envelope |

### New file (1)

| File | Purpose |
|---|---|
| `docs/handover/HANDOVER_incremental_close_2026-05-04.md` | This document |

### Integration instructions

1. **No new imports required for downstream consumers.** All changes are additive (new helper kwargs + new optional dataclass field) or in-place behavior preservation (M1/M3 metric labels and values unchanged for upstream-tier-aware results).
2. **Recommended commit grouping:** one bundled "incremental close" PR (all four modified files + new test cases + handoff doc) — matches the carry-over close pattern.

### Suggested commit message

> `[incremental] feat: finish B-1b per-site rollout (M1+M3) and B-2e salt-gradient scaffolding; 13 metrics gated; 4 new tests; ruff/mypy clean.`
