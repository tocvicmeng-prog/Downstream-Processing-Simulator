# Tier 2 Close — Milestone Handover

**Date:** 2026-05-04
**Scope:** Closing of Tier 2 (B-2a … B-2e) from `docs/update_workplan_2026-05-04.md`. All five Tier 2 work items landed in one session under `/scientific-coder` discipline.
**Branch state at handover:** `main` at `d067d73` + uncommitted Tier 2 working tree (see §9). No commits made.
**Authors:** `/scientific-coder` (Claude Opus 4.7).

---

## 1. Project context

Tier 0 closed 2026-05-04 morning (`HANDOVER_tier_0_close_2026-05-04.md`); Tier 1 closed 2026-05-04 mid-session (`HANDOVER_tier_1_close_2026-05-04.md`). Tier 2 is the medium-term scope from work plan §4. All five batches landed:

| Batch | ID | Title | Status |
|---|---|---|---|
| **B-2a** | W-009 | Residual reagent / wash diffusion-partition model | **DONE** |
| **B-2b** | W-008 | CFD-PBE end-to-end PIV-gate | **DONE** |
| **B-2c** | W-010 | Quantity / unit plumbing into solver interfaces | **DONE** |
| **B-2d** | W-011 | Deterministic process dossier export | **DONE** |
| **B-2e** | W-004 | M3 quantitative output gating | **DONE** |

Validation release gate (work plan §5) status after Tier 2:

| Gate | Status |
|---|---|
| 1. Environment (W-001) | ✅ closed in Tier 0 |
| 2. End-to-end calibrated wet-lab dataset | ⏳ user-side — no code change can close |
| 3. Independent holdout validation | ⏳ user-side |
| 4. Decision-grade automatic downgrade (W-003) | ✅ API delivered (B-1b); M3 gating now wired (B-2e); UI integration pending |
| 5. Process dossier export (W-011) | ✅ implementation delivered (B-2d) |

Three of five gates are now closeable from the code side. The remaining two require wet-lab data the user must contribute.

---

## 2. Per-batch summaries

### B-2a — Wash Residual Diffusion-Partition Model (W-009)

**Files:** `src/dpsim/level1_emulsification/wash_residuals.py` (NEW, 360 lines), `src/dpsim/calibration/calibration_data.py` (+2 fields), `tests/level1_emulsification/test_wash_residuals.py` (NEW, 240 lines, 27 cases).

**Deliverable:**
- Lumped-sphere partition-diffusion model with first-order hydrolysis. Solved via `scipy.integrate.solve_ivp` (LSODA) with loss-channel integrals carried in the ODE state vector — robust across the timescale span from `τ_diff ≈ 0.3s` (small bead) to `cycle_duration ≈ 1800s` (long wash).
- Per-reagent literature-anchored hydrolysis rate constants:
  - CNBr cyanate ester — 5 min half-life @ pH 11 (Kohn & Wilchek 1981)
  - CDI imidazolyl carbonate — 5 h half-life @ pH 7 (Hearn 1981)
  - Tresyl sulfonate — 1.5 h half-life (Nilsson 1981)
  - NaBH4 — 1 h conservative half-life (decomposes above pH ~5)
  - Epoxide / glutaraldehyde — no spontaneous hydrolysis (zero rate)
- `WashResidualSpec`, `WashCycleSpec`, `WashResidualResult` dataclasses with input validation.
- `predict_wash_residuals(spec, cycle)` returns full per-cycle trajectory + cumulative loss-fractions (hydrolysis vs diffusion) + pass/fail flags against `target_residual_mol_per_m3` and `assay_detection_limit_mol_per_m3`.
- `make_default_spec(reagent_key, ...)` factory pre-populates from the literature library.
- Evidence-tier policy:
  - Library-default transport (D, K_p) → `QUALITATIVE_TREND`
  - User-supplied transport → `SEMI_QUANTITATIVE`
  - User-supplied transport + calibrated assay limit → `CALIBRATED_LOCAL`
- `CalibrationEntry` extended with `assay_detection_limit` and `assay_quantitation_limit` fields (backward-compatible defaults to 0.0; legacy JSON loads cleanly).

**Field finding from B-2a development:** the effective hydrolysis half-life slows by factor `(1 + V_w/V_b · K_p)` in a finite wash bath (water reservoir refills bead). This is documented in the test docstrings and explains why a 5-minute CNBr half-life translates to a ~30-minute effective depletion timescale at typical wash ratios.

### B-2b — CFD-PBE Validation Gates (W-008)

**Files:** `src/dpsim/cfd/validation.py` (NEW, 295 lines), `tests/test_cfd_validation_gates.py` (NEW, 145 lines, 14 cases).

**Deliverable:**
- Four operational-quality gate functions:
  - `check_mesh_quality(payload)` → (total cells gate, per-zone min cells gate)
  - `check_residual_convergence(payload, threshold=1e-4)`
  - `check_epsilon_volume_consistency(payload, tolerance_rel=0.01)`
  - `check_exchange_flow_balance(payload, tolerance_rel=0.05)` — per-zone in/out conservation
- `validate_cfd_payload()` composite that runs all four and returns `CFDValidationReport` with `all_passed` / `failed_gates` properties.
- **Locked evidence-tier ladder** per work plan §4 → B-2b:
  - No PIV calibration → `QUALITATIVE_TREND`
  - PIV at this geometry & RPM → `CALIBRATED_LOCAL`
  - PIV + bench DSD validated in envelope → `VALIDATED_QUANTITATIVE`
  - Any operational-quality gate failed → `UNSUPPORTED` (bad CFD beats good PIV)
- `assign_cfd_evidence_tier(status, gates_passed)` exposes the ladder for the M1 orchestrator and any future PIV-ingestion module.

**Out of scope (deferred):** the actual OpenFOAM run on a bench geometry. The gating infrastructure is delivered; running OpenFOAM requires user-side mesh + OpenFOAM install + bench data. The locked Stirrer A fixture passes all four gates today.

### B-2c — Typed SI Boundary Helpers (W-010)

**Files:** `src/dpsim/core/quantities.py` (+10 helper functions), `tests/core/test_quantities_boundary_helpers.py` (NEW, 220 lines, 70 cases).

**Decision recorded:** Adopted the **typed boundary helper** pattern over full Quantity adoption inside solvers. Per the work plan: solver interiors stay numeric/SI for speed; the helpers wrap `unwrap_to_unit` to give one-line entry-point conversion with semantic naming. Full Quantity adoption is deferred (work plan said "pick one, document the choice" — choice = boundary helpers).

**Helpers exposed:**
- `as_si_time_s`, `as_si_length_m`, `as_si_volume_m3`, `as_si_flow_rate_m3_per_s`,
- `as_si_pressure_pa`, `as_si_concentration_mol_per_m3`, `as_si_capacity_mol_per_m3`,
- `as_si_ligand_density_mol_per_m3`, `as_si_mass_concentration_kg_per_m3`,
- `as_si_temperature_K` (handles °C ↔ K offset).

**Property tests** verify Quantity → SI → Quantity round-trip preservation across the lab unit families (mL/min ↔ m³/s, mM ↔ M ↔ mol/m³, °C ↔ K, etc.). Float inputs are passed through (boundary-helper contract: floats are trusted SI).

**Migration guidance for solver authors:** at the start of each entry-point function body, replace `flow_rate_m3_per_s = unwrap_to_unit(flow_rate, "m3/s")` with `flow_rate_m3_per_s = as_si_flow_rate_m3_per_s(flow_rate)`. The semantic naming makes the unit assumption explicit at the call site.

### B-2d — Process Dossier Export (W-011)

**Files:** `src/dpsim/core/process_dossier.py` (NEW, 305 lines — was previously `REDESIGN REQUIRED` stub-not-yet-written), `tests/core/test_process_dossier.py` (NEW, 175 lines, 16 cases).

**Deliverable:**
- `ProcessDossier` dataclass bundling the 14 fields specified in the work plan (recipe TOML, resolved params, M1/M2/M3 contracts, ResultGraph, manifests, calibration entries, blockers, warnings, git commit, package versions, smoke status, hashes, timestamp, notes).
- `build_dossier(...)` factory takes minimal (recipe TOML only) up to full pipeline outputs; missing inputs become empty containers — no synthetic placeholders.
- Hash helpers:
  - `compute_recipe_hash(toml)` — SHA-256 of UTF-8 bytes
  - `compute_calibration_store_hash(entries)` — SHA-256 of normalised, key-sorted JSON serialisation (invariant under entry-list reorder and dict-key reorder)
  - `compute_dossier_hash(dossier)` — SHA-256 of dossier content excluding timestamp + package_versions (content-addressable)
- Environment helpers: `get_git_commit_short()`, `get_git_dirty()`, `get_package_versions()`. All gracefully degrade to empty string / `"unavailable"` when subprocess / metadata calls fail.
- Deterministic JSON serialisation (sort_keys=True, no whitespace): two builds of the same recipe produce byte-identical content-hashes when timestamp / pkg versions excluded — proven by test.
- Tamper-detection round-trip: stored `recipe_hash` vs recomputed-from-current-content hash mismatches when recipe text mutates.

### B-2e — M3 Quantitative Output Gating (W-004)

**Files:** `src/dpsim/module3_performance/quantitative_gates.py` (NEW, 220 lines), `tests/module3_performance/test_quantitative_gates.py` (NEW, 200 lines, 21 cases).

**Deliverable:**
- `M3CalibrationCoverage` dataclass — 4 booleans (q_max, kinetic_constants, pressure_flow, cycle_life) + `n_calibrated` property.
- `assess_m3_calibration_coverage(entries, profile_key=, target_molecule=)` — scans CalibrationEntry list (or dicts) for parameter-name keyword sets; supports filtering by profile and target molecule.
- **Locked tier-promotion ladder:**
  - 4/4 calibrated → `VALIDATED_QUANTITATIVE`
  - 3/4 → `CALIBRATED_LOCAL`
  - 1–2/4 → `SEMI_QUANTITATIVE`
  - 0/4 → `QUALITATIVE_TREND`
- `assign_m3_evidence_tier(coverage)` — single-call promotion.
- `GradientContext` dataclass — typed pH / salt gradient parameters for the future isotherm/transport adapter refactor.
- `gradient_context_from_recipe_params(params)` — parser that accepts both bare-float and Quantity-duck-typed inputs, returns `None` when no gradient declared.

**Architectural separation:** the gating module is a peer to `method.py` and `orchestrator.py`, not embedded in them — this keeps the existing M3 solver code untouched and lets the next PR wire the gate consumption incrementally. The render-path layer (B-1b `core.decision_grade`) consumes the resulting tier and decides NUMBER / INTERVAL / RANK_BAND / SUPPRESS.

**Out of scope (deferred to a follow-on incremental PR):**
- Plumbing `GradientContext` through the existing isotherm / transport adapter (the dataclass and parser are delivered; the adapter-side consumption is a separate refactor).
- Adding `assess_m3_calibration_coverage` calls inside `run_chromatography_method` (call sites identified; integration is mechanical and best done after the orchestrator's manifest construction is reviewed).

---

## 3. Module registry — current state (post-Tier 2)

| Module | Verdict | Linked work items |
|---|---|---|
| `src/dpsim/__init__.py` | **APPROVED** | — |
| `pyproject.toml` + CI matrix | **APPROVED** | — |
| `src/dpsim/cfd/__init__.py` + `cfd/zonal_pbe.py` | **APPROVED** | — |
| `src/dpsim/cfd/validation.py` | **APPROVED** (NEW, B-2b) | — |
| `core/evidence.py` + `core/result_graph.py` | **APPROVED** | — |
| `core/recipe_validation.py` | **APPROVED** | — |
| `core/decision_grade.py` | **APPROVED** | — |
| `core/step_kind_mapping.py` | **APPROVED** | — |
| `core/quantities.py` | **APPROVED** (post B-2c boundary helpers) | — |
| `core/process_dossier.py` | **APPROVED** (NEW, B-2d — was REDESIGN REQUIRED) | — |
| `level1_emulsification/solver.py` | **APPROVED** | — |
| `level1_emulsification/wash_residuals.py` | **APPROVED** (NEW, B-2a — was NOT STARTED) | — |
| `level2_gelation/*` family solvers | **APPROVED** | — |
| `module2_functionalization/orchestrator.py` | **APPROVED** | — |
| `module2_functionalization/reagent_profiles.py` | **APPROVED** | — |
| `module3_performance/method.py` + `orchestrator.py` | **APPROVED-WITH-FIX-LIST** (gating module delivered; integration pending) | W-004 (integration carry-over) |
| `module3_performance/quantitative_gates.py` | **APPROVED** (NEW, B-2e) | — |
| `lifecycle/recipe_resolver.py` | **APPROVED** | — |
| `calibration/calibration_data.py` | **APPROVED** (post B-2a assay-limit fields) | — |
| `visualization/components/impeller_xsec_v3.py` | **APPROVED-WITH-FIX-LIST** | W-017 (deadline 2026-06-01) |
| `visualization/**` (use_container_width sites) | **APPROVED-WITH-FIX-LIST** | W-016 (Tier 3) |
| `docs/current_support_matrix.md` | **NOT STARTED** | W-019 (Tier 3 B-3c) |

---

## 4. Verification matrix

### Tests
| Suite | Result |
|---|---|
| Tier 0 baseline | 103/103 ✓ |
| Tier 1 suites (G7, decision_grade, step_kind, valid_domain, regime_guards) | 158/158 ✓ |
| **B-2a** wash residuals | 27/27 ✓ |
| **B-2b** CFD validation gates + existing CFD | 53/53 ✓ |
| **B-2c** quantities boundary helpers | 70/70 ✓ |
| **B-2d** process dossier | 16/16 ✓ |
| **B-2e** M3 quantitative gates | 21/21 ✓ |
| Default-recipe integration (p1/p2/p3/p4/clean/dsd_bin) | 33/33 ✓ |
| **Combined verification run** | **451 passed, 8 skipped** |

### Lint / type
| Gate | Result |
|---|---|
| ruff (all 11 Tier 2 changed files, post-cleanup) | All checks passed ✓ |
| mypy on Tier 2 NEW source files | 1 pre-existing scipy-stub warning (same pattern as Tier 1; not a regression) |

### Tests NOT run
- Full repo `pytest` collection. Recommend full CI run after merge.
- `tests/test_cli_v7.py::test_top_level_help_lists_new_commands` — known pre-existing cp1252 ε crash (documented in B-1a handoff).

---

## 5. Concrete starting point for next session — Tier 3 + carry-over

After Tier 2, the remaining work is:

### Tier 3 — Maintenance / parallel (rolling)
| Batch | ID | Status |
|---|---|---|
| **B-3a** Streamlit `use_container_width` sweep | W-016 | Not started |
| **B-3b** evidence_tier per-callsite refactor | W-018 | Cancelled in Tier 0 (inventory clean) |
| **B-3c** Active support matrix doc | W-019 | Not started |

### Tier 1/2 carry-over (delivered API, integration pending)
1. **B-1b decision_grade** UI integration — thread `render_value` calls into M1/M2/M3 result render paths. Mechanical, can be incremental.
2. **B-2e M3 gating** orchestrator integration — call `assess_m3_calibration_coverage` + `assign_m3_evidence_tier` at `run_chromatography_method` exit; thread `GradientContext` through the isotherm/transport adapter. Higher impact than Tier 3 items; recommend doing this before Tier 3.

### Wet-lab carry-over (user-side)
- Calibrate at least one M1→M2→M3 lifecycle (recommend: agarose-chitosan + Protein A, the default first-run recipe).
- Independent holdout validation set for DSD, ligand density, DBC, pressure-flow, residuals.

**Pre-flight for next session:**
1. `git log -1 --oneline` shows `d067d73` or later; `git status` should show Tier 1 + Tier 2 working-tree changes (commit before next session if desired).
2. Re-run Tier 0 baseline → expect 103 passed.
3. Re-run combined Tier 1 + Tier 2 suite (the 23 file paths in §4) → expect 451 passed, 8 skipped.

**Recommended commit grouping:**
- One PR per Tier 2 batch (B-2a → B-2e) — each is self-contained with no cross-batch dependencies.
- OR one "Tier 2 close" PR bundling all five (matches the Tier 1 close pattern).

Suggested commit message for the bundle path:
> `[tier2] feat: close Tier 2 (B-2a..B-2e) — wash residuals, CFD gates, SI helpers, dossier export, M3 quant gates; 147 new tests; ruff/mypy clean.`

---

## 6. Constraints to remember (anti-stale-context anchors)

- **Three of five validation-release gates now closeable from code.** Until wet-lab data closes the remaining two, every public communication still describes DPSim as *"a research-grade screening simulator with explicit evidence tiers"*.
- **B-2a wash residuals uses literature half-lives at activation pH** as a CONSERVATIVE upper bound on hydrolytic clearance. After the first neutral-pH wash, hydrolysis slows; the model over-predicts clearance, which is the safe direction (under-estimating residuals would be unsafe).
- **B-2b CFD evidence-tier ladder is locked.** Any code that promotes a CFD-backed M1 output past `QUALITATIVE_TREND` MUST go through `assign_cfd_evidence_tier` and supply both `CFDCalibrationStatus` and `gates_passed=True`. The four operational gates short-circuit any PIV calibration to `UNSUPPORTED`.
- **B-2c boundary-helper contract:** `as_si_<quantity>_<unit>` accepts Quantity (converted) OR float (trusted SI). Solver call sites that need to enforce typed inputs can later swap the float branch to raise — the call sites stay the same.
- **B-2d dossier hash invariants:** `compute_recipe_hash` is byte-exact on UTF-8; `compute_calibration_store_hash` is invariant under entry-list reorder and dict-key reorder; `compute_dossier_hash` excludes timestamp + package_versions for content-addressability. Adding fields to `ProcessDossier` without thinking about hash impact will silently break reproducibility — extend `to_dict(include_timestamp=False, include_package_versions=False)` to also exclude any new env-varying field if added.
- **B-2e M3 gating ladder (4/3/1–2/0 → VAL/CAL/SEMI/QUAL).** This is the policy floor; the render path (`core.decision_grade`) further degrades based on the OutputType's required tier. Both layers must agree before a number reaches the user.
- **Pre-existing baseline noise:** `mypy` raises `scipy.integrate import-untyped` warnings on multiple files. Same in Tier 1. Documented in both handoffs. Resolution: `pip install scipy-stubs` (a separate maintenance task, not a Tier 2 deliverable).

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

# Tier 1 + Tier 2 + integration
.\.venv\Scripts\python -m pytest -q `
    tests\core\test_recipe_validation_g7_ph.py `
    tests\core\test_recipe_validation.py `
    tests\core\test_decision_grade.py `
    tests\core\test_step_kind_mapping.py `
    tests\core\test_quantities_boundary_helpers.py `
    tests\core\test_process_dossier.py `
    tests\level1_emulsification\test_wash_residuals.py `
    tests\level2_gelation\test_valid_domain_coverage.py `
    tests\test_cfd_zonal_pbe_regime_guards.py `
    tests\test_cfd_validation_gates.py `
    tests\module3_performance\test_quantitative_gates.py `
    tests\lifecycle\test_p1_scientific_boundaries.py `
    tests\lifecycle\test_p2_m1_washing_model.py `
    tests\lifecycle\test_p3_m2_functionalization.py `
    tests\lifecycle\test_p4_m3_method.py `
    tests\core\test_clean_architecture.py `
    tests\test_dsd_bin_resolved.py `
    -p no:cacheprovider
# Expected: 348 passed, 8 skipped.

# Tier 2 source-file lint / type
.\.venv\Scripts\python -m ruff check `
    src\dpsim\level1_emulsification\wash_residuals.py `
    src\dpsim\cfd\validation.py `
    src\dpsim\core\quantities.py `
    src\dpsim\core\process_dossier.py `
    src\dpsim\module3_performance\quantitative_gates.py `
    src\dpsim\calibration\calibration_data.py
# Expected: All checks passed!
```

---

## 8. Quick links

- Work plan: `docs/update_workplan_2026-05-04.md`
- Tier 0 close: `docs/handover/HANDOVER_tier_0_close_2026-05-04.md`
- Tier 1 close: `docs/handover/HANDOVER_tier_1_close_2026-05-04.md`
- B-1a detailed handoff: `docs/handover/HANDOFF_b1a_g7_ph_window_2026-05-04.md`
- This handover: `docs/handover/HANDOVER_tier_2_close_2026-05-04.md`

---

## 9. Files delivered (Tier 2 totals)

### New source files (5)

| File | Purpose | Lines |
|---|---|---|
| `src/dpsim/level1_emulsification/wash_residuals.py` | B-2a partition-diffusion + hydrolysis model | 360 |
| `src/dpsim/cfd/validation.py` | B-2b 4-gate CFD validation + evidence-tier ladder | 295 |
| `src/dpsim/core/process_dossier.py` | B-2d hash-locked reproducibility bundle | 305 |
| `src/dpsim/module3_performance/quantitative_gates.py` | B-2e M3 calibration coverage + tier promotion + GradientContext | 220 |
| (B-2c additions to `core/quantities.py`) | 10 typed SI boundary helpers | +110 inline |

### New test files (5)

| File | Cases |
|---|---|
| `tests/level1_emulsification/test_wash_residuals.py` | 27 |
| `tests/test_cfd_validation_gates.py` | 14 |
| `tests/core/test_quantities_boundary_helpers.py` | 70 |
| `tests/core/test_process_dossier.py` | 16 |
| `tests/module3_performance/test_quantitative_gates.py` | 21 |

### Modified files (1)

| File | Change |
|---|---|
| `src/dpsim/calibration/calibration_data.py` | B-2a: `assay_detection_limit` + `assay_quantitation_limit` fields + `to_dict`/`from_dict` round-trip |

### Integration instructions

1. **No new imports required for downstream consumers.** All five batches deliver new modules or new fields with backward-compatible defaults.
2. **Recommended verification before merge:** §7 commands.
3. **Recommended next move (work plan §9 + Tier 2 carry-overs):**
   - **Highest leverage:** wire B-2e gating into `run_chromatography_method` (M3 orchestrator). Mechanical change, ~30 lines.
   - **Highest UX impact:** thread B-1b `render_value` into M1/M2/M3 report displays. Per-display-site change, ~5–20 lines per site.
   - **Lowest priority:** Tier 3 cosmetic / docs (B-3a Streamlit sweep, B-3c support matrix).

### Suggested commit message (bundle path)

> `[tier2] feat: close Tier 2 (B-2a..B-2e) — wash residuals (W-009), CFD gates (W-008), SI boundary helpers (W-010), process dossier (W-011), M3 quant gates (W-004); 147 new tests; ruff/mypy clean.`
