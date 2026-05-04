# DPSim — Current Support Matrix

**Version:** v0.6.5 (post-Tier 2 working tree, 2026-05-04)
**Maintainer:** `/architect`
**Updated by:** any PR that materially changes a feature's support status

This document is the **single source of truth** for what DPSim currently
claims to support, at what level of evidence, and where each claim is
implemented. It supersedes ad-hoc README assertions; if a downstream
consumer (UI, dossier export, journal-grade publication) needs to check
whether a feature is decision-grade today, this is the authoritative
ledger.

---

## Status legend

| Status | Meaning |
|---|---|
| **live** | Production-use ready; calibrated against the relevant analogue OR validated by a wet-lab dataset for the in-tree default recipe. Outputs renderable as numbers under the B-1b `decision_grade` policy without intervention. |
| **screening** | Implementation correct, but uncalibrated; outputs are reliable as **trends and rankings** only. UI / report layer should render as INTERVAL or RANK_BAND per the B-1b policy. Default tier for v0.6.x. |
| **requires calibration** | Implementation correct; specifically blocked from quantitative use until paired with a wet-lab dataset (e.g., M3 DBC / cycle-life claims, ligand-density / coupling-yield numbers). Render-path will SUPPRESS or RANK_BAND until calibration is loaded. |
| **scaffolded** | Module / API exists but the underlying physics or data path is incomplete. Useful for development and integration tests; not for production claims. |
| **deferred** | Designed but intentionally not implemented in v0.6.x. Tracked under a `W-NNN` ID in `docs/update_workplan_2026-05-04.md`. |
| **rejected** | Considered and explicitly out of scope for the current architecture (e.g., new polymer families, alternative isotherm formulations). Reopen via a new ADR if the constraint changes. |

---

## Feature matrix — by module

### M1 Fabrication (PBE + CFD coupling)

| Feature | Status | Evidence floor | Implementation | Notes / W-IDs |
|---|---|---|---|---|
| Single-zone PBE breakage / coalescence | live | CALIBRATED_LOCAL | `level1_emulsification/solver.py` | Alopaeus & CT kernels; calibrated against published rotor-stator geometries. |
| Zonal CFD-PBE coupling | screening | CALIBRATED_LOCAL after PIV | `cfd/zonal_pbe.py` + `cfd/validation.py` | Locked tier ladder via `assign_cfd_evidence_tier`; bench-DSD validation pending. |
| 4 operational-quality CFD gates | live | n/a (gate is binary) | `cfd/validation.py` (B-2b) | Mesh, residual, ε-volume, exchange-flow conservation. |
| Sub-Kolmogorov regime diagnostics | live | n/a (diagnostic) | `cfd/zonal_pbe.py` (B-1d) | `d/η_K` per zone + aggregated; warnings surface in diagnostics. |
| M1 wash mass-balance gate (G1) | live | screening | `core/recipe_validation.py` | BLOCKER above 5× target; WARNING above target. |
| Wash residual diffusion-partition + hydrolysis | screening | QUALITATIVE_TREND default; CALIBRATED_LOCAL with assay LOD | `level1_emulsification/wash_residuals.py` (B-2a) | Literature half-lives for CNBr/CDI/tresyl/NaBH4. |
| L2 family solvers (agarose, chitosan, alginate, dextran-ECH, NIPS-cellulose, solvent-evap PLGA) | screening | SEMI_QUANTITATIVE | `level2_gelation/*.py` | All publish `valid_domain` post-B-1c. |
| L2 tier-2 / tier-3 / v9.5 composite analogies | screening | QUALITATIVE_TREND for tier-3 | `level2_gelation/{tier2,tier3,v9_5}_*.py` | Inherit base solver `valid_domain` + `calibration_status` tag. |

### M2 Functionalization

| Feature | Status | Evidence floor | Implementation | Notes / W-IDs |
|---|---|---|---|---|
| Reagent profile library (~100 reagents) | live | SEMI_QUANTITATIVE | `module2_functionalization/reagent_profiles.py` | Per-class kinetics from literature; pH windows curated for 23 profiles in B-1a. |
| Family × reagent compatibility matrix (G4) | live | n/a (gate is binary) | `core/recipe_validation.py` | BLOCKERs on incompatible pairings; WARNINGs on qualitative-only. |
| ACS-Converter sequence FSM (G6) | live | n/a (gate is binary) | `core/recipe_validation.py` | Enforces ACTIVATE → INSERT_SPACER → ARM_ACTIVATE → COUPLE_LIGAND → METAL_CHARGE chain. |
| Per-step pH window guardrail (G7) | live | n/a (gate is binary) | `core/recipe_validation.py` (B-1a) | Hard / soft windows from literature; 23 profiles curated. |
| ProcessStepKind ↔ ModificationStepType mapping | live | n/a (mapping is canonical) | `core/step_kind_mapping.py` (B-1e) | Single source of truth; AST-style coverage test. |
| Coupling-yield numerical predictions | requires calibration | VALIDATED_QUANTITATIVE for NUMBER render | `module2_functionalization/orchestrator.py` | Render path uses `decision_grade.OutputType.COUPLING_YIELD` floor. |
| Ligand density numerical predictions | requires calibration | VALIDATED_QUANTITATIVE for NUMBER | same | floor = VALIDATED_QUANTITATIVE in policy. |
| Reagent residual nondetectability claims | requires calibration | VALIDATED_QUANTITATIVE for NUMBER | `level1_emulsification/wash_residuals.py` | Uses `assay_detection_limit` from `CalibrationEntry`. |

### M3 Performance (chromatography)

| Feature | Status | Evidence floor | Implementation | Notes / W-IDs |
|---|---|---|---|---|
| LRM breakthrough simulation (single solute) | live | screening | `module3_performance/method.py` | Validated against Cytiva Protein A Sepharose literature; default isotherm screening-grade. |
| Loaded-state low-pH elution dynamics | screening | SEMI_QUANTITATIVE | `module3_performance/method.py` | gradient_field="ph" supported; salt gradients via `GradientContext` (B-2e) — adapter consumption pending. |
| Pressure-flow / column-operability checks | screening | SEMI_QUANTITATIVE | `module3_performance/method.py` | Ergun-class correlations; calibration recommended. |
| DBC10 / DBC50 quantitative claims | requires calibration | VALIDATED_QUANTITATIVE | gated by `quantitative_gates.assign_m3_evidence_tier` (B-2e) | 4-of-4 calibration → VALIDATED; the orchestrator now applies the gate when `process_state["calibration_entries"]` is set. |
| Recovery / cycle-life predictions | requires calibration | VALIDATED_QUANTITATIVE | same | same gating ladder. |
| Family-conditional Protein A defaults | screening | QUALITATIVE_TREND for non-A+C families | `module3_performance/method.py` | Tier capped at QUALITATIVE_TREND when polymer family is non-A+C. |
| GradientContext-typed gradient plumbing | scaffolded | n/a | `module3_performance/quantitative_gates.py` (B-2e) | Dataclass + parser delivered; isotherm/transport adapter consumption is a follow-on PR. |

### Cross-cutting (core / lifecycle / calibration)

| Feature | Status | Evidence floor | Implementation | Notes / W-IDs |
|---|---|---|---|---|
| Recipe → resolved-parameter pipeline | live | n/a | `lifecycle/recipe_resolver.py` | post-B-1e taxonomy delegation. |
| ValidationReport infrastructure | live | n/a | `core/validation.py`, `core/recipe_validation.py` | Carries G1-G7 issues; INFO/WARNING/BLOCKER severities. |
| Decision-grade gate (render-path policy) | live | n/a | `core/decision_grade.py` (B-1b) | 14 OutputTypes; NUMBER → INTERVAL → RANK_BAND → SUPPRESS ladder. |
| ResultGraph + ModelManifest evidence tiers | live | n/a | `core/result_graph.py`, `core/evidence.py`, `datatypes.py` | reload-safe enum comparison via `.value`. |
| Quantity (typed unit-aware scalar) | live | n/a | `core/quantities.py` | + 10 typed SI boundary helpers post-B-2c. |
| Process dossier export | live | n/a | `core/process_dossier.py` (B-2d) | Hash-locked deterministic JSON; gates the validation release ladder. |
| Calibration store + entries | live | n/a | `calibration/calibration_data.py`, `calibration/calibration_store.py` | + `assay_detection_limit` / `assay_quantitation_limit` post-B-2a. |
| Bayesian fit (PyMC) | scaffolded | n/a | `calibration/bayesian_fit.py` | Optional `[bayesian]` extra; not exercised in default flow. |
| BoTorch-driven optimization | scaffolded | n/a | `optimization/objectives.py` | Optional `[optimization]` extra; ADR-002 pin. |

### UI (Streamlit)

| Feature | Status | Evidence floor | Implementation | Notes / W-IDs |
|---|---|---|---|---|
| Lifecycle-first triptych workbench | live | n/a (UX) | `visualization/shell/triptych.py` | Direction-B layout. |
| M1 / M2 / M3 tab-based workflow | live | n/a (UX) | `visualization/tabs/tab_m{1,2,3}.py` | Direction-A layout, retained. |
| Hardware Mode (Stirrer A / B / Pitched-blade) | live | n/a (UX) | `visualization/tabs/m1/family_selector.py` + cross-section components | post-W-017 Streamlit migration. |
| Cross-section animations (impeller, column) | live | n/a (UX) | `visualization/components/{impeller_xsec*,column_xsec}.py` | Migrated to `st.html` via `_html_helper` (W-017). |
| `width=` / `use_container_width=` migration | live | n/a (UX) | all `visualization/**` callsites swept | post-B-3a. |
| Decision-grade render-mode formatting | scaffolded | n/a | `visualization/**` consume of `core.decision_grade.render_value` | API delivered (B-1b); per-callsite UI integration is incremental. |

---

## Validation release-gate status (work plan §5)

| Gate | Status | Closed by |
|---|---|---|
| 1. Environment reproducibility | ✅ closed | Tier 0 B-0a (W-001) |
| 2. End-to-end calibrated wet-lab dataset (M1→M2→M3) | ⏳ wet-lab side | — |
| 3. Independent holdout validation | ⏳ wet-lab side | — |
| 4. Decision-grade automatic downgrade | ✅ API + M3 wiring closed | B-1b + B-2e + B-2e orchestrator integration |
| 5. Process dossier export | ✅ closed | B-2d (W-011) |

**Three of five gates closeable from code.** The remaining two require user-side wet-lab data. Until all five close, **every public communication describes DPSim as *"a research-grade screening simulator with explicit evidence tiers"* and never as *"validated for downstream-processing release decisions"*.**

---

## Deferred / rejected scope (explicit non-goals for v0.6.x)

| Item | Status | Reason |
|---|---|---|
| New polymer families beyond the 21 currently registered | rejected | Out of scope per work plan §7. Reopen via ADR if a target chemistry requires it. |
| Isotherm physics beyond Langmuir + LRM + axial dispersion + film mass transfer | rejected | Same. M3 can render existing physics decision-grade; new physics demands a calibration campaign. |
| Bayesian-fit gate semantics (R-hat / ESS / divergences) tightening | deferred | Audited only superficially in the v0.6.3 audits; tighter gate semantics are a Tier 3+ item. |
| Full `Quantity` adoption inside solver kernels | deferred | B-2c chose typed boundary helpers instead. Migration path is documented (`as_si_<quantity>_<unit>`). |
| OpenFOAM end-to-end run on bench geometry | deferred | B-2b delivered the gating infrastructure. Running OpenFOAM requires user-side mesh + bench DSD data. |
| `visualization/components/streamlit_components/` migration | deferred | These wrap a different Streamlit pattern (custom React component); not affected by the W-017 deprecation. Track separately if needed. |

---

## Historical archive

The following milestone handovers describe the path to the current state. Read in chronological order for narrative; read latest-first for the freshest module-registry snapshot.

| Date | File | Scope |
|---|---|---|
| 2026-05-04 | `docs/handover/HANDOVER_tier_0_close_2026-05-04.md` | Tier 0 close — environment + doc/mechanical hygiene |
| 2026-05-04 | `docs/handover/HANDOFF_b1a_g7_ph_window_2026-05-04.md` | B-1a detailed (G7 pH guardrail) |
| 2026-05-04 | `docs/handover/HANDOVER_tier_1_close_2026-05-04.md` | Tier 1 close — B-1a..B-1e |
| 2026-05-04 | `docs/handover/HANDOVER_tier_2_close_2026-05-04.md` | Tier 2 close — B-2a..B-2e |
| 2026-05-04 | `docs/handover/HANDOVER_post_tier_2_close_2026-05-04.md` | Post-Tier 2 — W-017, B-2e integration, Tier 3 sweep + this matrix |

Older handovers (pre-Tier 0) live alongside in `docs/handover/` and describe earlier audit / refactor cycles. They are kept for traceability but the module registry in §3 of the most recent handover supersedes them.

---

## How to update this matrix

1. Any PR that adds a feature, promotes a tier, closes a W-item, or rejects a previously-open scope **must** update the relevant row in §"Feature matrix" or §"Deferred / rejected scope".
2. Promote a status only when the underlying evidence supports it. The tier ladders in `core.evidence`, `core.decision_grade`, `cfd.validation`, and `module3_performance.quantitative_gates` are the authoritative test for "promotable".
3. Add a row to §"Historical archive" when a milestone handover is committed.
4. Status changes that affect the validation release-gate status (e.g., closing an audit gate) **must** also be reflected in §"Validation release-gate status" and in the corresponding section of `docs/update_workplan_2026-05-04.md` §5.

---

**Disclaimer:** This support matrix is informational. Numeric outputs labelled `live` are calibrated against published or in-tree wet-lab analogues; any specific decision (process release, regulatory filing, IP claim) must be backed by an explicit calibration entry, an end-to-end wet-lab validation, or a B-2d process dossier with appropriate evidence tier. The matrix is not a substitute for wet-lab judgment.
