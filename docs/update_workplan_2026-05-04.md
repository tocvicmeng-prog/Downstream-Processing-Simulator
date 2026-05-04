# DPSim v0.6.3 — Joint Review of the Two Audit Reports + Update Work Plan

**Reviewers:** `/scientific-advisor` + `/architect` + `/dev-orchestrator` (joint)
**Inputs:**
- `docs/functional_architecture_audit_2026-05-04.md` (referred to below as **F-arch audit**; 15 findings F-001…F-015, of which 7 were fixed during that audit as A-001…A-007)
- `docs/joint_audit_v0_6_3_2026-05-04.md` (referred to below as **doc audit**; 5 MAJOR + 7 MINOR findings)

**Date:** 2026-05-04
**Mode:** read-only review; no code edits

---

## 1. Reconciliation summary (overlap matrix)

The two audits have **highly complementary scopes**, with five points of explicit overlap. The doc audit was tight on documentation precision, taxonomy structure, and deprecation tracking; the F-arch audit was deep on scientific validity, calibration gating, and operational reproducibility. Neither was redundant.

| # | Joint-audit finding | F-arch counterpart | Status |
|---|---|---|---|
| 1 | MAJOR-1 (bit-exact 0.000000 % claim) | A-007 (CFD one-zone equivalence wording downgraded) | **Resolved** by A-007 |
| 2 | MAJOR-2 (parallel `ProcessStepKind` ↔ `ModificationStepType` taxonomies) | F-001 / A-001 (preflight allowlist expanded) | **Partially resolved** — A-001 closes the immediate dispatch hole; the structural mapping-table refactor remains open (filed as **W-005** below) |
| 3 | MAJOR-3 (`pipeline/` README description) | A-007 (README `pipeline/` wording corrected) | **Resolved** by A-007 |
| 4 | MAJOR-5 (G6 error message omits `ARM_ACTIVATE`) | A-007 (G6 ordering error includes `ARM_ACTIVATE`) | **Resolved** by A-007 |
| 5 | MINOR-7 (98 hardcoded `evidence_tier` literals in 30 files) | F-002 / A-002 (centralised reload-safe rollup) | **Partially resolved** — A-002 fixes the rollup function; per-callsite literal review of `optimization/objectives.py` (7 sites) and `catalysis/packed_bed.py` (4 sites) still warranted (filed as **W-018** below) |

Five of the joint audit's twelve findings were caught and resolved (or partially resolved) by the F-arch audit, before the joint audit was even committed. The two remaining MAJORs from the joint audit (**MAJOR-2 deeper refactor**, **MAJOR-4 `_phase_rank` comment**) and the six remaining MINORs are all unresolved and remain in the work plan.

The F-arch audit caught **three real defects the joint audit missed**:

- A-003 (M1 PBE manifest claimed beta daughter distribution; solver does binary equal-volume) — **scientific provenance bug**, not just doc drift.
- A-004 (L2 1D radial Cahn-Hilliard solver labelled as 2D in `model_name` and `assumptions`) — **scientific provenance bug**.
- A-005 (CFD `__init__.py` framing said scaffold-only; coupling is actually implemented) — **doc drift in code-level docstring**.

These are credit to the F-arch auditor; the joint audit's targeted code-reads did not surface them.

---

## 2. Verified resolved (collapse and close)

The following findings are **closed** for the work plan:

| ID | Source | What was fixed | Where |
|---|---|---|---|
| A-001 | F-arch | `ACS_CONVERSION` + `ARM_ACTIVATION` added to backend preflight allowlist | `module2_functionalization/orchestrator.py` |
| A-002 | F-arch | Centralised reload-safe `weakest_evidence_tier` via `core/evidence.py` | `core/evidence.py`, `core/result_graph.py` |
| A-003 | F-arch | PBE manifest assumption: beta → binary equal-volume daughter | `level1_emulsification/solver.py` |
| A-004 | F-arch | L2 manifest: `CahnHilliard2D` → `CahnHilliard1D.Radial`; "2D approximation" → "1D radial approximation" | `level2_gelation/<cellulose pore solver>.py` |
| A-005 | F-arch | CFD `__init__.py` updated to state DPSim-side coupling is implemented; OpenFOAM-side scripts still pre-validation | `cfd/__init__.py` |
| A-006 | F-arch | Regression tests added for ACS converter → ligand coupling preflight + reload-safe evidence rollup | `tests/` |
| A-007 | F-arch | (a) CFD bit-exact claim → integrator-tolerance agreement; (b) README `pipeline/` wording corrected; (c) G6 error message includes `ARM_ACTIVATE` | `cfd/zonal_pbe.py`, `CHANGELOG.md`, `README.md`, `core/recipe_validation.py` |
| MAJOR-1 | doc | (= A-007 (a)) | as above |
| MAJOR-3 | doc | (= A-007 (b)) | as above |
| MAJOR-5 | doc | (= A-007 (c)) | as above |

**Verification policy:** at next session start, run `git diff --stat eea8776..HEAD` and `pytest -q tests/test_v0_5_2_codex_fixes.py tests/test_result_graph_register.py tests/test_evidence_tier.py` to confirm A-001…A-007 are present and passing. The F-arch audit reported 60 passed at that step.

---

## 3. Reconciled open finding ledger

Severity is the **higher** of the two audits' grades when both flagged a finding. New IDs (`W-NNN`) are assigned for the work plan.

### BLOCKER (release-gate)

None as a runtime defect. **W-001** (Python 3.13+ environment) is operational-BLOCKER for reproducibility.

### MAJOR

| ID | Source | Title | Severity |
|---|---|---|---|
| **W-001** | F-005 | Python environment is not reproducible — active interpreter is 3.14.3, pyproject caps at <3.13 | HIGH operational |
| **W-002** | F-006 | Recipe Guardrail 2 (pH / pKa / reagent-stability windows) is deferred — chemistry can pass G6 ordering and still be physically implausible at the wrong pH | MEDIUM-HIGH scientific |
| **W-003** | F-007 | Quantitative claims need output-specific calibration gates (DSD, pore, ligand density, residuals, DBC, pressure-flow, cycle life) | HIGH scientific |
| **W-004** | F-011 | M3 default isotherms / Protein A lifetime values produce smooth numeric curves that can be over-interpreted | MEDIUM-HIGH scientific |
| **W-005** | doc MAJOR-2 (deeper) | Two parallel taxonomies (`ProcessStepKind` ↔ `ModificationStepType`) need an explicit mapping table + regression test, beyond the A-001 dispatch patch | MEDIUM structural |
| **W-006** | F-009 | M1 emulsification physics regime guards (sub-Kolmogorov, high `μ_d`, strong ε gradients) need explicit `d/η_K` diagnostics on the zonal CFD-PBE path | MEDIUM scientific |
| **W-007** | F-008 | L2 family dispatch needs machine-readable `valid_domain` + analogy-source diagnostic for every family route | MEDIUM scientific |
| **W-008** | F-012 | CFD-PBE coupling needs end-to-end OpenFOAM → zones.json → PBE walk on a real bench geometry, mesh QA + PIV-gating | MEDIUM scientific |
| **W-009** | F-010 | Residual reagent / wash model (CNBr, CDI, tresyl, epoxide, surfactant, oil) is too coarse for protein-contact release | MEDIUM scientific |
| **W-010** | F-014 | Quantity / unit plumbing only at boundaries; many internal solvers still pass floats | MEDIUM correctness |
| **W-011** | F-015 | Deterministic process dossier export (`process_dossier.py`) is a stub; no authoritative audit-trail bundle | MEDIUM reproducibility |
| **W-012** | doc MAJOR-4 | `_phase_rank` comment claims "rank 2.5" but dict maps `ARM_ACTIVATE: 3` | MINOR doc, but in audit-trail-critical code |

### MINOR

| ID | Source | Title |
|---|---|---|
| **W-013** | doc MINOR-3 | `cad/README.md` "datatypes.py mismatches" block is stale post-v0.6.0 |
| **W-014** | doc MINOR-1 + MINOR-2 | AST-gate test docstring + `EXEMPT_FILES` orphan comment |
| **W-015** | doc MINOR-4 | CFD validation rule numbering (Rule 2 / 3 / 6 with no 1, 4, 5) |
| **W-016** | doc MINOR-5 | Streamlit `use_container_width` deprecation sweep — already past the 2025-12-31 deadline |
| **W-017** | doc MINOR-6 | `st.components.v1.html` → `st.iframe` migration — deadline 2026-06-01 (≈ 27 days away) |
| **W-018** | doc MINOR-7 (residual) | Per-callsite review of hardcoded `evidence_tier` literals in `optimization/objectives.py` (7) and `catalysis/packed_bed.py` (4) |
| **W-019** | F-013 | `docs/current_support_matrix.md` — single source of truth for what is `live` / `screening` / `requires calibration` / `scaffolded` / `deferred` / `rejected` |

---

## 4. Sequenced update work plan

Sequencing principles applied:

- **F-005 / W-001 first** — every other test result is suspect under a wrong-version interpreter.
- **One module at a time** — never two scientific-validity items in parallel.
- **Doc / mechanical fixes batched** into a single hygiene PR.
- **Architectural changes** (taxonomy mapping, decision-grade gates, dossier export) each get their own PR with paired tests.
- **Compress before you code** — at every PR boundary, refresh the local context budget; if RED, dump a milestone handover before starting the next.

### Tier 0 — Immediate (0–2 days)

| Batch | IDs | Modules | Model tier | Notes |
|---|---|---|---|---|
| **B-0a** *Environment lockdown* | W-001 | `pyproject.toml`, new preflight in `__main__.py`, README install section, CI matrix | **Sonnet** (small, mechanical) | Rebuild `.venv` with Python 3.12; add `sys.version_info >= (3,13)` fail-fast at import time; pin CI to 3.11/3.12 only. Run full smoke + targeted suites. **Blocker for everything below — do this PR alone.** |
| **B-0b** *Doc / mechanical hygiene* | W-012, W-013, W-014, W-015, W-018 (read-only) | `core/recipe_validation.py`, `cad/README.md`, `tests/test_v9_3_enum_comparison_enforcement.py`, `cfd/zonal_pbe.py`, plus a read-only inventory of `evidence_tier` literals | **Haiku** (boilerplate doc edits) | Single PR; ≤ 5 files; no behavioural change. Output of the W-018 read-only inventory feeds W-005 / W-007. |
| **B-0c** *Streamlit deadline-driven migration* | W-017, W-016 (start) | `visualization/components/impeller_xsec_v3.py`, sample of `tabs/*.py` | **Sonnet** | W-017 has a hard deadline of 2026-06-01. W-016 is a sweep — start with the highest-traffic tab and complete in tier 3. |

### Tier 1 — Short-term (1–2 weeks)

| Batch | IDs | Modules | Model tier | Notes |
|---|---|---|---|---|
| **B-1a** *Recipe Guardrail 2 — pH / pKa* | W-002 | `core/recipe_validation.py`, `module2_functionalization/<reagent profiles>.py`, new tests | **Opus** (novel scientific guardrail; needs literature for reagent pH windows) | Specific list per /scientific-advisor: CNBr (pH 11–11.5 narrow), CDI (pH 8–9, anhydrous coupling), tresyl chloride (pH 7.5–9 coupling), epoxide (pH 9–11 amine, pH 11.5–13 hydroxyl), aldehyde + reductive amination (pH 7–8 imine, pH 7–9 NaCNBH3), boronate ester (pH 7–9 cis-diol), Ni-NTA / IMAC (pH 7–8 binding, pH 4–4.5 elution), Protein A coupling (pH 7–8.5 EDC; pH 7–7.4 protein stability), borax (pH 8.5–9.5). Block on out-of-window; warn on rate-degraded. Attach decision to step-manifest `diagnostics`. |
| **B-1b** *Decision-grade gates per output type* | W-003 | new `core/decision_grade.py`, plumbing in `lifecycle/orchestrator.py`, UI display layer | **Opus** (cross-cutting policy) | One `decision_grade` policy table: each output (DSD, d32, pore, modulus, ligand density, residual, DBC, pressure, cycle life) carries a min-evidence-tier requirement. Below requirement → render as rank band / interval, not as a number. **No code change to solvers**, only to render path. |
| **B-1c** *Family dispatch valid_domain* | W-007 | `level2_gelation/*.py` (dispatch) | **Opus** for design + **Sonnet** for per-family rollout | Add `valid_domain` schema (concentration, ionic strength, pH, temperature, solvent, crosslinker, bead radius) to every family's `ModelManifest`. Add `analogy_source_family` diagnostic where applicable. |
| **B-1d** *M1 PBE regime guards on CFD-PBE path* | W-006 | `cfd/zonal_pbe.py`, `level1_emulsification/validation.py` | **Sonnet** | Add `d/η_K` and `d32/η_K` diagnostics to the zonal path; expose `breakage_C3` calibration in manifests. |
| **B-1e** *Taxonomy mapping refactor* | W-005 | new `core/step_kind_mapping.py` + regression test | **Opus** | The mapping table is one source of truth for `ProcessStepKind ↔ ModificationStepType ↔ allowlists`. Regression test asserts every enum member resolves to a `ModificationStepType` or explicit `None`. |

### Tier 2 — Medium-term (1–2 months)

| Batch | IDs | Modules | Model tier | Notes |
|---|---|---|---|---|
| **B-2a** *Residual reagent / wash diffusion-partition model* | W-009 | new `level1_emulsification/wash_residuals.py`, calibration store assay-detection-limit fields | **Opus** + scientific-advisor concept-to-computation translation | Bead/water partition-diffusion + first-order hydrolysis for labile activated groups (CNBr cyanate ester half-life 5 min @ pH 11; CDI ~5 h @ pH 7; tresyl 1–2 h depending on solvent). |
| **B-2b** *CFD-PBE end-to-end PIV-gated walkthrough* | W-008 | `cad/cfd/`, `tests/`, validation docs (Appendix K) | **Opus** for the validation envelope; **Sonnet** for fixture wiring | Run OpenFOAM → zones.json → DPSim PBE end-to-end against one bench geometry (Stirrer A or B, 100 mL beaker). Add mesh QA + residual convergence + ε-volume consistency + exchange-flow checks to CI fixtures (mocked for the OpenFOAM-required step). Lock CFD evidence-tier ladder: no PIV → `QUALITATIVE_TREND`; PIV at geometry / RPM → `CALIBRATED_LOCAL`; PIV + bench DSD → `VALIDATED_QUANTITATIVE` within envelope. |
| **B-2c** *Quantity / unit plumbing into solver interfaces* | W-010 | `core/quantities.py`, M1/M2/M3 solver function signatures | **Opus** for design; **Sonnet** for per-solver migration | SI-only typed boundary helpers OR full `Quantity` adoption — pick one, document the choice. Property tests on flow rate, bed volume, pressure, capacity, ligand density, time. |
| **B-2d** *Deterministic process dossier export* | W-011 | `core/process_dossier.py` (currently stub), CLI entry, hash-of-recipe | **Opus** for spec; **Sonnet** for impl | Bundle: recipe TOML + resolved parameters + M1/M2/M3 contracts + `ResultGraph` + manifests + calibration entries + warnings/blockers + git commit + package versions + smoke status + recipe-hash + calibration-store-hash. |
| **B-2e** *M3 quantitative gating* | W-004 | `module3_performance/method.py`, `orchestrator.py`, UI render | **Sonnet** + scientific-advisor escalation for isotherm review | Require calibrated `q_max`, kinetic constants, pressure-flow, and cycle-life data before labeling M3 outputs `validated_quantitative`. Default to interval / rank rendering otherwise. Plumb pH and salt gradients through the isotherm/transport adapter (not just manifest text) when elution / recovery is being predicted. |

### Tier 3 — Maintenance / parallel (rolling)

| Batch | IDs | Modules | Model tier | Notes |
|---|---|---|---|---|
| **B-3a** *Streamlit deprecation sweep finish* | W-016 | all `visualization/**` callsites | **Haiku** | Mechanical replace `use_container_width=True` → `width='stretch'` and `=False` → `width='content'`. ~30–60 sites. |
| **B-3b** *evidence_tier per-callsite refactor (if W-018 inventory finds class-(b) hits)* | W-018 (continuation) | `optimization/objectives.py`, `catalysis/packed_bed.py` | **Sonnet** | Convert hardcoded literals to derive-from-input where appropriate. Skip if all hits prove benign. |
| **B-3c** *Active support matrix doc* | W-019 | new `docs/current_support_matrix.md` | **Haiku** for first cut; **Sonnet** for the categorisation pass | Single source of truth: every module feature labelled `live` / `screening` / `requires calibration` / `scaffolded` / `deferred` / `rejected`. Link old handovers under "historical archive". |

---

## 5. Validation release gate

Per the F-arch audit's §8 release gate (which we adopt), DPSim cannot be presented as **scientifically complete for quantitative downstream-processing decisions** until:

1. **Environment** — full test suite passes on Python 3.11 and 3.12; CI enforces both. (Closes W-001.)
2. **End-to-end calibrated path** — at least one calibrated M1 → M2 → M3 wet-lab dataset (ideally agarose-chitosan + Protein A, since that is the default first-run recipe).
3. **Independent wet-lab holdout validation** — DSD, ligand density, DBC, pressure-flow, residuals.
4. **Report-level evidence-tier downgrade** — extrapolated or uncalibrated outputs are downgraded automatically by the decision-grade policy layer (closes W-003).
5. **Process dossier export** — deterministic, reproducible, hash-locked (closes W-011).

Until all five gates close, every public communication should describe DPSim as *"a research-grade screening simulator with explicit evidence tiers"* and **never** as *"validated for downstream-processing release decisions"*.

---

## 6. Token-economy sequencing (orchestrator framing)

| Tier | Estimated PRs | Estimated context per PR | Suggested model |
|---|---|---|---|
| Tier 0 | 3 PRs (B-0a / B-0b / B-0c) | 30–60 % | Sonnet / Haiku / Sonnet |
| Tier 1 | 5 PRs (B-1a … B-1e) | 50–80 % each | Opus for B-1a, B-1b, B-1c-design, B-1e; Sonnet rest |
| Tier 2 | 5 PRs (B-2a … B-2e) | 70–90 % each | Opus design + Sonnet impl per PR; expect ≥1 milestone handover per PR |
| Tier 3 | 3 PRs, parallelisable | 20–40 % | Haiku / Sonnet |

**Compression checkpoints:** between every Tier-1 / Tier-2 PR, run a milestone handover (`docs/handover/HANDOVER_w-XXX_close.md`) per the orchestrator skill's reference 04. Tier 0 and Tier 3 PRs are small enough to chain without a handover unless context drops below YELLOW.

**Module registry** (initial state for the work plan): see Appendix A below.

---

## 7. What this plan does *not* attempt to fix

- Polymer-chemistry coverage beyond the 21 currently registered families (no plan to add new families during this work).
- M3 isotherm physics beyond Langmuir + LRM + axial dispersion + film mass transfer (no change to the underlying model in this plan; only its calibration gating).
- The Bayesian-fit gate semantics (R-hat / ESS / divergences) — left as-is, audited only superficially.
- The optimization extra (BoTorch / GPyTorch / PyTorch pin) — covered by ADR-002, deferred unless a Tier-2 work item touches it.
- Any new wet-lab campaign — that is the user's responsibility; this plan only specifies what data DPSim needs to consume.

---

## 8. Appendix A — Initial module registry

| Module | Owner | Status | Linked work items |
|---|---|---|---|
| `core/recipe_validation.py` | architect | APPROVED-WITH-FIX-LIST | W-002, W-005, W-012 |
| `core/evidence.py` + `core/result_graph.py` | architect | APPROVED (post A-002) | W-018 |
| `core/process_dossier.py` | architect | REDESIGN REQUIRED | W-011 |
| `core/decision_grade.py` (NEW) | architect | NOT STARTED | W-003 |
| `core/step_kind_mapping.py` (NEW) | architect | NOT STARTED | W-005 |
| `level1_emulsification/solver.py` | architect | APPROVED (post A-003) | W-006 |
| `level1_emulsification/wash_residuals.py` (NEW) | architect | NOT STARTED | W-009 |
| `level2_gelation/*` family solvers | architect | APPROVED (post A-004) | W-007 |
| `module2_functionalization/orchestrator.py` | architect | APPROVED (post A-001) | W-002, W-005 |
| `module3_performance/method.py` | architect | APPROVED-WITH-FIX-LIST | W-004 |
| `cfd/__init__.py` + `cfd/zonal_pbe.py` | architect | APPROVED (post A-005, A-007) | W-006, W-008 |
| `visualization/**` | architect | APPROVED-WITH-FIX-LIST | W-016, W-017 |
| `__main__.py` (preflight) | architect | NOT STARTED (W-001 hook) | W-001 |
| `cad/README.md` | architect | APPROVED-WITH-FIX-LIST | W-013 |
| `tests/test_v9_3_enum_comparison_enforcement.py` | architect | APPROVED-WITH-FIX-LIST | W-014 |
| `pyproject.toml` + CI | architect | REVISION REQUIRED | W-001 |
| `docs/current_support_matrix.md` (NEW) | architect | NOT STARTED | W-019 |

Verdict abbreviations follow the architect-skill vocabulary: APPROVED, APPROVED-WITH-FIX-LIST, REVISION REQUIRED, REDESIGN REQUIRED, NOT STARTED.

---

## 9. Final disposition

- **Both audits cleared the v0.6.3 release** for *screening use*; nothing flagged is a runtime BLOCKER.
- The **highest-leverage next step is W-001** (Python 3.12 venv reproducibility) — closing it makes every subsequent test-and-fix cycle trustworthy.
- The **highest-scientific-value PRs are W-002, W-003, W-006, W-008** — these convert DPSim from "screening" toward "calibrated quantitative" and will be the most defensible to a journal / IP / regulatory reviewer.
- The **highest-architectural-value PR is W-005** — closing the taxonomy parallelism prevents a class of future v0.5.2-style external-review incidents.
- **Doc / mechanical hygiene (Tier 0b + Tier 3) is independent** of the science work and can ride alongside any other batch.

Recommended next move: open three PRs for Tier 0 (B-0a, B-0b, B-0c). Each is small enough to land in a single session. After Tier 0 is on `main`, schedule a working session for B-1a (the pH/pKa guardrail) — the most scientifically dense item in Tier 1 and the one that most reduces the gap between "chemically valid order" and "chemically valid order *and* physically plausible window".

---

> **Disclaimer:** This joint review reconciles two audit reports and proposes a sequenced update plan; it is provided for informational and engineering-review purposes only. Findings inherited from the F-arch audit (A-001 … A-007 status, smoke-test counts, environment observations) should be re-verified against the live codebase before any PR is merged. The auditors made no code edits in this turn.
