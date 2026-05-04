# Tier 0 Close — Milestone Handover

**Date:** 2026-05-04
**Scope:** Closing of Tier 0 from `docs/update_workplan_2026-05-04.md`; preparing for Tier 1 (substantive scientific work).
**Branch state at handover:** `main` clean, in sync with `origin/main`, head `6303464`.
**Authors:** `/dev-orchestrator` + `/architect` + `/scientific-coder` (joint).

---

## 1. Project context

DPSim v0.6.3 — the lifecycle simulator for polysaccharide-microsphere fabrication, functionalisation, and affinity chromatography. Two audits run in parallel on 2026-05-04 (`docs/functional_architecture_audit_2026-05-04.md` and `docs/joint_audit_v0_6_3_2026-05-04.md`) produced 19 open work items consolidated into `docs/update_workplan_2026-05-04.md`. Tier 0 is the prerequisite-and-hygiene tier; Tier 1 is the scientific-validity tier.

Both audits cleared v0.6.3 for *screening use*. Nothing identified is a runtime BLOCKER. The work plan is about graduating DPSim from "screening" toward "calibrated quantitative" per the §5 release gate.

---

## 2. Tier 0 close summary

### Landed (in chronological commit order)

| Commit | Scope | Files | Tests |
|---|---|---|---|
| `297a216` | F-arch audit fixes A-001..A-007 (M2 preflight allowlist; reload-safe evidence rollup; PBE manifest provenance; L2 1D radial CH manifest; CFD docstring; `pipeline/` README wording; bit-exact wording; G6 error message; regression coverage) | 12 modified | F-arch trio + AST gate: 63 passed |
| `a6fed74` | B-0a — W-001 in-process Python-version preflight (`dpsim._check_python_version`) | 1 modified + 1 new | 7 new + integrated suite: 70 passed |
| `f59c2ef` | Audit + work-plan documentation (3 new docs) | 3 new | n/a |
| `6303464` | B-0b — W-013 (`cad/README.md` stale Stirrer A block), W-014 (AST gate test docstring + EXEMPT_FILES orphan comment), W-015 (CFD validation rule labelling). W-018 inventory closed in commit message. | 3 modified | 43 passed |

### Resolved without new edit

- **W-012** — `_phase_rank` "rank 2.5" comment — already corrected by F-arch A-007; verified at `core/recipe_validation.py:365-366`.
- **W-018** continuation (B-3b in the work plan) — inventory of the 11 hardcoded `ModelEvidenceTier` literals showed all hits are class-(a) legitimate references or class-(c) downgrade sentinels. **B-3b cancelled.**

### Deferred from Tier 0

- **W-017** — `st.components.v1.html` → replacement migration. The deprecation message claims "replace with `st.iframe`", but `st.iframe(src=...)` takes a URL while the M1 live cross-section component passes a ~700-line inline HTML/SVG/JS string. The likely correct replacement is `st.html(...)` (Streamlit ≥ 1.39), not `st.iframe`. Resolution requires a focused Streamlit session that (1) confirms which API is canonical in the installed version, (2) tests the cross-section animation under the chosen API, (3) lands the migration. **Deadline: 2026-06-01 (28 days away from this handover).**
- **W-016** — `use_container_width` sweep moved to Tier 3 (rolling maintenance). No hard deadline; Streamlit has not yet enforced removal despite the 2025-12-31 nominal deprecation date.

---

## 3. Module registry — current state

Verdict abbreviations: APPROVED, APPROVED-WITH-FIX-LIST, REVISION REQUIRED, REDESIGN REQUIRED, NOT STARTED.

| Module | Verdict | Linked work items |
|---|---|---|
| `src/dpsim/__init__.py` | **APPROVED** (post W-001) | — |
| `pyproject.toml` + CI matrix | **APPROVED** (verified correct in pre-flight) | — |
| `src/dpsim/cfd/__init__.py` + `cfd/zonal_pbe.py` | **APPROVED** (post A-005, A-007, W-015) | W-006, W-008 |
| `core/evidence.py` + `core/result_graph.py` | **APPROVED** (post A-002) | — |
| `core/recipe_validation.py` | **APPROVED-WITH-FIX-LIST** (post A-007) | **W-002 (next)**, W-005 |
| `level1_emulsification/solver.py` | **APPROVED** (post A-003) | W-006 |
| `level2_gelation/solver.py` + family dispatch | **APPROVED** (post A-004) | W-007 |
| `module2_functionalization/orchestrator.py` | **APPROVED** (post A-001) | W-002, W-005 |
| `module3_performance/method.py` + `orchestrator.py` | **APPROVED-WITH-FIX-LIST** | W-004 |
| `cad/README.md` | **APPROVED** (post W-013) | — |
| `tests/test_v9_3_enum_comparison_enforcement.py` | **APPROVED** (post W-014) | — |
| `optimization/objectives.py` | **APPROVED** (W-018 inventory cleared) | — |
| `module3_performance/catalysis/packed_bed.py` | **APPROVED** (W-018 inventory cleared) | — |
| `core/process_dossier.py` | **REDESIGN REQUIRED** | W-011 |
| `core/decision_grade.py` | **NOT STARTED** | W-003 |
| `core/step_kind_mapping.py` | **NOT STARTED** | W-005 |
| `level1_emulsification/wash_residuals.py` | **NOT STARTED** | W-009 |
| `docs/current_support_matrix.md` | **NOT STARTED** | W-019 |
| `visualization/components/impeller_xsec_v3.py` | **APPROVED-WITH-FIX-LIST** (deferred) | W-017 |
| `visualization/**` (use_container_width sites) | **APPROVED-WITH-FIX-LIST** (rolling) | W-016 |

---

## 4. Tier 1 — next-up batches

| Batch | IDs | Estimated context | Model | Notes |
|---|---|---|---|---|
| **B-1a** *Recipe Guardrail 2 — pH / pKa / reagent stability windows* | W-002 | 60–80 % | **Opus** | Highest scientific-impact item in Tier 1. Needs literature-backed pH/pKa windows for ~10 reagent classes. |
| **B-1b** *Decision-grade gates per output type* | W-003 | 60–80 % | **Opus** | Cross-cutting policy layer; render-path-only change. |
| **B-1c** *Family dispatch `valid_domain`* | W-007 | 50–70 % | Opus design + Sonnet rollout | Per-family rollout. |
| **B-1d** *M1 PBE regime guards on CFD-PBE path* | W-006 | 40–60 % | **Sonnet** | Lightest Tier-1 item; `d/η_K` diagnostics. |
| **B-1e** *Taxonomy mapping refactor* | W-005 | 40–60 % | **Opus** | Closes MAJOR-2 from the joint audit at the structural level. |

The work plan recommends B-1a first as the highest scientific-impact item and the most defensible for journal / IP / regulatory review.

---

## 5. Concrete starting point for next session — B-1a

### Brief

Implement Recipe Guardrail 2 in `src/dpsim/core/recipe_validation.py`. The guardrail validates each M2 step's pH against the reagent's hard/soft pH windows, blocks unsafe chemistry, warns for rate-degraded windows, and attaches the pH decision to the step manifest's `diagnostics`.

### Reagent-class pH windows (from `/scientific-advisor` literature review)

| Reagent class | Coupling pH (optimum) | Hard limits | Notes |
|---|---|---|---|
| CNBr activation | 11.0 – 11.5 (narrow) | < 10.5 hydrolyses; > 12.0 damages matrix | Cyanate ester half-life ~5 min @ pH 11 |
| CDI activation | 8.0 – 9.0, anhydrous | < 7 reverses; aqueous hydrolysis | Imidazolide intermediate |
| Tresyl chloride | 7.5 – 9.0 | < 7 inert; > 10 hydrolyses | Stable activated bead at neutral pH |
| Epoxide (ECH/DVS/BDDE) | 9 – 11 (amine), 11.5 – 13 (hydroxyl) | < 8 slow; > 13 polymer damage | Bifunctional linker; opening kinetics pH-dependent |
| Aldehyde + reductive amination | 7 – 8 (imine), 7 – 9 (NaCNBH₃) | < 5 unstable imine; > 9 cyanide hazard | Two-step: imine then reduce |
| Boronate ester | 7 – 9 | < 6 ester opens; > 10 boronate ionises | cis-Diol selectivity |
| Ni-NTA / IMAC | 7 – 8 (binding), 4 – 4.5 (elution) | > 9 strips Ni²⁺ | Imidazole gradient elution |
| Protein A coupling (EDC) | 7 – 8.5 (EDC); 7 – 7.4 (protein stability) | EDC hydrolysis @ pH > 8 | NHS booster recommended |
| Borax | 8.5 – 9.5 | < 7 reversibility lost | v9.5 reversibility caveat |
| Glutaraldehyde | 7 – 8 | extreme pH polymerises | Schiff-base + Michael addition |

### Implementation sketch

1. **Reagent profile schema** — add `ph_min_hard`, `ph_max_hard`, `ph_min_soft`, `ph_max_soft`, `ph_optimum` fields to `ReagentProfile`. Default to `None` (no check). Populate the 10 classes above.
2. **Validation function** — new `_g7_ph_window_check(recipe, report)` in `core/recipe_validation.py`, called from the same dispatcher that runs G6.
3. **Decision policy:**
   - `ph < ph_min_hard` or `ph > ph_max_hard` → BLOCKER (`FP_G7_PH_OUT_OF_HARD_WINDOW`)
   - Outside soft window but inside hard → WARNING (`FP_G7_PH_RATE_DEGRADED`)
   - Inside soft window → silent pass; attach `ph_decision: "in_optimum"` to step diagnostics
4. **Special handling:**
   - Two-step reagents (aldehyde + reduction) check both phases.
   - Protein-stability vs reaction-pH conflicts (Protein A EDC) → prefer the stricter window.
5. **Tests** — `tests/test_recipe_validation_g7_ph.py`. ≥ 12 cases:
   - Each of the 10 classes: in-optimum (pass), in-hard-soft gap (warning), out-of-hard (blocker).
   - Two-step reagent both-phase edge case.
   - Profile with no pH metadata (silent pass — backward compat).

### Pre-flight before starting B-1a (next session)

1. Confirm head is `6303464` or later (`git log -1 --oneline`).
2. Confirm `.venv/Scripts/python.exe -c "import dpsim; print(dpsim.__version__)"` returns `0.6.3` cleanly (preflight + import path live).
3. Re-run the F-arch trio + AST gate + preflight (~70 tests) to confirm tier 0 still green.
4. Read this handover, then read `docs/update_workplan_2026-05-04.md §4 → B-1a`.
5. Start with the protocol generation phase — the scientific-advisor's pH window table above is the authoritative input; cross-check 1–2 reagents against PubMed before declaring the protocol final.

---

## 6. Constraints to remember (anti-stale-context anchors)

- **`.venv` is Python 3.12.10** — verified during B-0a pre-flight. The F-arch audit's "active interpreter is 3.14.3" referred to the *system-level* python, not the project venv. The preflight in `dpsim.__init__` will fire if anyone re-runs against system 3.14.
- **The G6 sequence FSM canonical chain is `ACTIVATE → INSERT_SPACER → ARM_ACTIVATE → COUPLE_LIGAND → METAL_CHARGE`** (post-v0.5.2). Already enforced; the G7 pH guardrail layers on top — does not replace.
- **AST gate flags `is`/`is not` only**, not `==` (CLAUDE.md rationale: Streamlit reload aliases break identity but `Enum.__eq__` falls back to value comparison). Test docstring corrected in W-014.
- **Two parallel taxonomies** still exist: `ProcessStepKind` (recipe-level) ↔ `ModificationStepType` (kinetic-solver-level). Mapping is implicit and currently held in dispatch allowlists (A-001 closed the immediate hole). **W-005 / B-1e** will introduce the explicit mapping table; **B-1a should not introduce new dispatch lookups that bypass this future mapping.**
- **`pipeline/` is an orchestration shell**, not legacy L1-L4 kernels. The actual L1-L4 logic is in `level{1,2,3,4}_*` directories. (Corrected by A-007; do not re-introduce the legacy framing.)
- **CFD-PBE 1-zone reduction is integrator-tolerance agreement (rel ≤ 1e-9)**, not "bit-exact 0.000000 %". The earlier wording was mathematically impossible for two adaptive `solve_ivp` calls. (Corrected by A-007.)
- **Streamlit deprecation deadline 2026-06-01** (28 days) for `st.components.v1.html`. W-017 must land before then; the right replacement is likely `st.html(...)`, not `st.iframe(src=...)`, for the inline-HTML use case.
- **Validation release gate (work plan §5)** — five conditions for graduating from "screening" to "calibrated quantitative". Until all five close, every public communication describes DPSim as *"a research-grade screening simulator with explicit evidence tiers"* and **never** as *"validated for downstream-processing release decisions"*.

---

## 7. Verification commands

Run from the repo root with the project venv:

```powershell
# Confirm head and clean tree
git log -3 --oneline
git status

# Confirm version + preflight live
.\.venv\Scripts\python -c "import dpsim; print(f'dpsim {dpsim.__version__} on Python {__import__(\"sys\").version_info[:2]}')"

# Re-run the F-arch trio + AST gate + preflight (Tier 0 regression baseline)
.\.venv\Scripts\python -m pytest -q `
    tests\test_v0_5_2_codex_fixes.py `
    tests\test_result_graph_register.py `
    tests\test_evidence_tier.py `
    tests\test_v9_3_enum_comparison_enforcement.py `
    tests\test_python_version_preflight.py `
    tests\test_cfd_zonal_pbe.py `
    -p no:cacheprovider
# Expected: 76 passed (32 + 8 + 20 + 3 + 7 + 6 ⋯ confirm exact count on resume)
```

If any of these regress, **stop and diagnose before starting B-1a** — the Tier 0 baseline must be green before Tier 1 builds on top.

---

## 8. Quick links

- Work plan: `docs/update_workplan_2026-05-04.md`
- Joint audit: `docs/joint_audit_v0_6_3_2026-05-04.md`
- F-arch audit: `docs/functional_architecture_audit_2026-05-04.md`
- ADR-001 (Python version range): `docs/decisions/ADR-001` (referenced by the preflight error message)
- This handover: `docs/handover/HANDOVER_tier_0_close_2026-05-04.md`
