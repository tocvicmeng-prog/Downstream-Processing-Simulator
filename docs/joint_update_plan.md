# DPSim Joint Update Plan — Scientific–Architectural–Orchestration Synthesis

**Date:** 2026-04-25
**Roles consulted:** /scientific-advisor, /architect (twice — design + coherence audit), /dev-orchestrator
**Source artifacts (this directory):**
- `performance_recipe_protocol.md` — architect design protocol (G1=PASS) for the `PerformanceRecipe` + method-simulation layer
- `dev_orchestrator_plan.md` — 14-module v0.2.0 + v0.3.0 build cycle with model tiers
- `architect_coherence_audit.md` — system-level six-dimension audit (verdict: COHERENT_WITH_GAPS)
- The scientific-advisor's validity audit (verdict M1 SEMI@calibrated/QUAL else, M2 SEMI@A+C / QUAL else, M3 SEMI@calibrated breakthrough / QUAL gradient + UNSUPPORTED cycle-life)

This document is the single authoritative roadmap. It supersedes the older "Next Developer Tasks" list at the bottom of `handover/INITIAL_HANDOVER.md`.

---

## 1. Joint System Verdict

DPSim has correct architectural instincts and a defensible scientific tier framework. Three classes of gaps must be closed for the system to be **scientifically reliable, architecturally coherent, and UI-faithful**:

1. **Scope-of-claim leaks** — gradient elution does not inherit calibrated tier; cycle-life and impurity log-reductions print as numbers when they are rankings; M2/M3 result panels do not display evidence badges at all (M1 does).
2. **UI ↔ science misalignments** — UI permits invalid recipes (polymer-family/reagent mismatches, gradient_field/isotherm incompatibilities, pH-window violations); M1 tab still uses the legacy `PipelineOrchestrator` import; `nav.py` is a stub; `--es-*` CSS variables remain.
3. **Architectural coherence depth** — `Quantity` is a boundary type only (zero references inside M2/M3); `ResultGraph` is populated by the lifecycle orchestrator only; `ModelMode` is L4-only; the family-first dispatch is M1-only; calibration tier promotion uses a string side-channel instead of the typed `ModelEvidenceTier` enum.

**Path forward:** three milestones — v0.2.0, v0.3.0, v0.4.0 — each tied to a specific verdict that the system can defensibly claim after it ships.

---

## 2. Three-Milestone Roadmap

### v0.2.0 — "Evidence chain closed; first guardrails live"

**Verdict the system can claim after v0.2.0:** every M3 method result carries a manifest whose tier truthfully inherits from upstream FMC; recipes that violate first-principles physics are blocked at the lifecycle entry; per-DSD-quantile full-method execution is reachable from the CLI.

| Order | Module | Source role | Tier | LOC |
|---|---|---|---|---|
| **A1** | `core/performance_recipe.py` typed primitive (`PerformanceRecipe`, `DSDPolicy`, `from_resolved` builder) | Architect | Sonnet | ~120 |
| **A2** | `module3_performance/orchestrator.py` — extend `run_gradient_elution(fmc=...)` and route through `_build_m3_chrom_manifest` | Architect + sci-advisor | Sonnet | ~30 |
| **A3** | `core/recipe_validation.py` — `validate_recipe_first_principles()` enforcing: (a) mass-balance closure on M1 wash; (b) `gradient_field` ↔ `isotherm.gradient_field` consistency; (c) surface-area inheritance check on M3 capacity claims | Sci-advisor guardrails 1, 3, 5 | Sonnet | ~150 |
| **A4** | `module3_performance/method_simulation.py` — `run_method_simulation` + `MethodSimulationResult` + DSD aggregation; per-DSD full method opt-in (`--dsd-full-method`) | Architect | Sonnet | ~250 |
| **A5** | `lifecycle/orchestrator.py` — replace dual M3 calls with `run_method_simulation`; wire `validate_recipe_first_principles` before `resolve_lifecycle_inputs` | Architect | Sonnet | ~150 net |
| **A6** | `visualization/tabs/tab_m3.py` + `visualization/ui_workflow.py` — switch to `MethodSimulationResult`, add evidence-tier badges to M3 result panels, pass FMC to gradient elute call site | UI alignment | Sonnet | ~120 |
| — | **G3 audit + v0.2.0 milestone handover** | Architect | Opus | — |

**v0.2.0 acceptance gates**
- `python -m dpsim lifecycle configs/fast_smoke.toml` — wall time ≤ 1.5× v0.1.0; smoke result table within ±5 % of `INITIAL_HANDOVER.md` baseline.
- `python -m dpsim lifecycle configs/fast_smoke.toml --dsd-full-method` — per-quantile DBC10 list non-empty; mass-weighted DBC10 p50 within 10 % of d50 result.
- Recipe with calibrated FMC + gradient elute → manifest tier inherits FMC tier; `calibration_ref` propagated.
- ruff = 0, mypy = 0, all existing tests pass + ≥18 new tests across A1–A6.
- M3 tab renders evidence-tier badges adjacent to DBC10, pressure drop, and recovery numbers.

### v0.3.0 — "Family coverage, claim honesty, recipe-only UI"

**Verdict the system can claim after v0.3.0:** UI cannot construct polymer-family/reagent-incompatible recipes; non-A+C families receive family-aware trust gates and family-aware Protein A defaults; cycle-life and impurity log-reductions print as ranking labels (not numbers) when no calibration is loaded; M1 tab is fully recipe-native; branding is internally consistent.

| Order | Module | Source role | Tier | LOC |
|---|---|---|---|---|
| **B1** | `module2_functionalization/family_reagent_matrix.py` — polymer-family × reagent compatibility data; BLOCK in `validate_recipe_first_principles` (sci-advisor guardrail 4) | Sci-advisor | Sonnet | ~120 |
| **B2** | `trust.py` — family-aware paths covering alginate / cellulose / PLGA (closes v9.1 follow-up) | Sci-advisor + architect coherence D6 | Sonnet | ~100 |
| **B3** | `visualization/tabs/tab_m2.py` + per-family panels — evidence-tier badges; family-aware reagent dropdown filtering | UI + sci-advisor | Sonnet | ~120 |
| **B4** | `core/process_recipe.py` extension — promote remaining family-specific M1 fields from `base_params` into typed recipe `Quantity` slots; update `recipe_resolver` | Architect coherence D1 | Sonnet | ~150 |
| **B5** | `visualization/tabs/tab_m1.py` — drop legacy `PipelineOrchestrator` import; recipe-only path | UI + architect coherence D1 | Sonnet | ~80 |
| **B6** | `module3_performance/method.py` — demote `cycle_lifetime_to_70pct_capacity`, impurity `log10_reduction`, leaching numeric outputs to ranking labels when no calibration loaded | Sci-advisor scope-of-claim | Haiku | ~40 |
| **B7** | `visualization/nav.py` — implement `build_navigation()` (currently `raise NotImplementedError`) | UI + architect coherence D1 | Haiku | ~40 |
| **B8** | CSS / branding — `--es-*` → `--dps-*`; update `DESIGN.md:8` product-context line; audit user-facing strings | UI + architect coherence D5 | Haiku | ~50 |
| — | **G3 audit + v0.3.0 milestone handover** | Architect | Opus | — |

**v0.3.0 acceptance gates**
- UI in alginate / cellulose / PLGA modes blocks an "ECH activation" recipe construction with an actionable error.
- Family-aware trust gate produces non-empty results for non-A+C families.
- `cycle_lifetime_to_70pct_capacity` displays as `"~50 cycles (illustrative — calibration required)"` when no resin-cycling assay is loaded.
- M1 tab does not import `PipelineOrchestrator`.
- `nav.py` no longer raises `NotImplementedError`.
- DESIGN.md product-context describes the **downstream-processing** scope.

### v0.4.0 — "Architectural coherence: one architecture, not two"

**Verdict the system can claim after v0.4.0:** the clean-slate primitives are consumed end-to-end, not just at the boundary; the legacy data contracts (`SimulationParameters`, `FullResult`) are deprecated and slated for v0.5.0 removal; bin-resolved DSD propagation replaces the 3-quantile collapse.

| Order | Module | Source | Tier | LOC |
|---|---|---|---|---|
| **C1** | M2/M3 internal `Quantity` retrofit — convert ~40 dataclass fields and ~25 solver function signatures from bare floats to typed `Quantity` | Architect coherence Deficit-1 | Opus protocol + Sonnet impl | ~600 |
| **C2** | `ModelMode` consumption in M2/M3 — gate manifest tier and result-numeric output on mode (mechanistic-mode results carry `EXPLORATORY_ONLY` regardless of calibration) | Architect coherence Deficit-2 + sci-advisor | Sonnet | ~250 |
| **C3** | `CalibrationStore.apply_to_model_params` — promote `model_manifest.evidence_tier` from `SEMI_QUANTITATIVE` to `CALIBRATED_LOCAL` via the typed enum, retire the `confidence_tier` string side-channel | Architect coherence D3 | Sonnet | ~80 |
| **C4** | `ResultGraph` adoption inside solvers — each ModificationStep + each chromatography method step adds its own ResultNode; sub-step provenance preserved | Architect coherence D3 | Sonnet | ~200 |
| **C5** | Bin-resolved DSD propagation — `_dsd_bin_iterator` replaces `_dsd_representative_rows`; mass-weighted aggregation; `joblib` per-bin parallelism (the A4 API is already shaped for this) | Architect coherence Deficit-3 + sci-advisor M1-S1 | Opus protocol + Sonnet impl | ~400 |
| **C6** | M3 isotherm shape parameter calibration ingest (`pH_transition`, `steepness`, competitive `K_L` array) — extend P5+ uncertainty propagation | Sci-advisor §5 | Sonnet | ~250 |
| **C7** | M3 `_protein_a_isotherm_from_state` → family-aware default selection (cellulose-affinity uses Cibacron Blue, alginate uses ion-exchange, etc.) | Architect coherence D6 + sci-advisor §4 | Sonnet | ~150 |
| — | **G3 audit + v0.4.0 milestone handover** | Architect | Opus | — |

**v0.4.0 acceptance gates**
- Grep `: Quantity\|-> Quantity` over `module2_functionalization/` and `module3_performance/` returns ≥ 80 % of public-facing function signatures.
- Mode-conditional output: `mechanistic_research` mode produces results tagged `EXPLORATORY_ONLY`; `empirical_engineering` mode refuses to produce a numeric DBC10 unless an FMC with calibrated `q_max` is loaded.
- Bin-resolved DSD propagation runs with up to 30 bins in ≤ 5× the d50 wall time on default `joblib` parallelism.
- The string `confidence_tier` field on FMC is gone; tier is read from `model_manifest.evidence_tier`.

---

## 3. Cross-Milestone Discipline

**Sequencing.** Strict-sequential within each milestone (A1→A6, then B1→B5, B6/B7/B8 free; then C1→C7). One module at a time per the dev-orchestrator framework. Architect designs and audits; scientific-coder implements.

**Model tier discipline.** Architecture and full audits = Opus (non-negotiable). Standard implementation = Sonnet. Boilerplate / branding / nav stub / claim-strength downgrade = Haiku. Re-audits after algorithmic fixes upgrade to Opus.

**Compression cadence.** Trigger compression after the A3 audit (before A4 + A5 push toward RED). Mandatory milestone handover after A6, B8, C7. The v0.2.0 handover should pre-generate B1 protocol so a fresh session can resume immediately.

**Fix-round budget.** 19 rounds across 14 v0.2/v0.3 modules; ~22 rounds across 7 v0.4 modules. Escalate to /architect REDESIGN before round 4.

**Scientific-validity guardrails.** Every G3 audit must explicitly check:
- Manifest tier truthfully inherits from weakest upstream contributor.
- Numeric outputs match their evidence-tier (no SEMI_QUANTITATIVE numbers from QUAL inputs).
- Mode-conditional gates fire when the user's `ModelMode` does not match the result's calibration state (post-C2).

**Documentation discipline.** Every milestone updates: `CHANGELOG.md`, `docs/INDEX.md`, the relevant `docs/handover/PN_*.md`, and `DESIGN.md` if any visual contract changes. Do not let the documentation drift the system observed in this audit (DESIGN.md product-context line surviving from EmulSim) recur.

---

## 4. Out-of-Scope (v0.5.0+)

- Removal of the deprecated `SimulationParameters` / `FullResult` / `run_pipeline` API surface. v0.5 is the deprecation removal release.
- Full Bayesian fitting + Monte Carlo LRM uncertainty propagation (P5++).
- Streamlit browser QA automation.
- Regulated-batch-record SOP export with signature lines, deviation fields, and explicit assay acceptance tables.
- `python -m dpsim method` standalone CLI (M3-only run against a saved FMC JSON).
- Python 3.14 compat of the `botorch` / `torch` optimization stack.

---

## 5. The Single Decision Required From the Project Manager Before Kickoff

The architect protocol's **Open Question Q1** (in `performance_recipe_protocol.md` §8) determines whether the v0.2.0 default elute path stays on `run_loaded_state_elution` (low-pH single-component) or switches to `run_gradient_elution` (multi-component competitive Langmuir) when the recipe sets `gradient_field="ph"`.

**Recommendation:** keep `run_loaded_state_elution` as default for v0.2.0; gate the gradient-via-method path on an explicit recipe flag (`elute.use_competitive_gradient = true`). Switch the default in v0.3.0 alongside the M2/M3 evidence-tier UI work, and update `INITIAL_HANDOVER.md` smoke-result table in the same PR.

Once that decision is logged, kickoff is module A1 at Sonnet tier, ~120 LOC, fix-round budget 1.

---

## 6. Source-Material Cross-Reference

| If you need… | Read |
|---|---|
| The full PerformanceRecipe + method-simulation design | `performance_recipe_protocol.md` |
| The 14-module build sequence with tiers, dependencies, and context-budget zones | `dev_orchestrator_plan.md` |
| The cross-cutting structural deficits the per-module plan cannot close | `architect_coherence_audit.md` |
| The first-principles validity envelope and UI-permitted invalid recipes | The scientific-advisor verdict in this conversation thread |
| The product / scientific intent the architecture is trying to honour | `docs/03_architecture_modification_plan.md` and `docs/01_scientific_advisor_report.md` |
