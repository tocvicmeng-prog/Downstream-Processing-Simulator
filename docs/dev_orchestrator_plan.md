# Dev-Orchestrator Plan — DPSim v0.2.0 → v0.3.0

**Date:** 2026-04-25
**Scope:** Closes architect gaps (PerformanceRecipe + method simulation, gradient elution FMC inheritance) AND scientific-advisor guardrails (recipe first-principles validation, family-aware paths, claim demotion) AND UI alignment (evidence badges in M2/M3, recipe-only M1, nav, branding).
**Framework:** dev-orchestrator inner loop, one module at a time, /architect designs + audits, /scientific-coder implements.

---

## Build sequence (one module at a time, in order)

### Milestone v0.2.0 — architect gaps + critical guardrails

| # | Module | Tier | LOC | Deps | Fix-round budget |
|---|---|---|---|---|---|
| **A1** | `core/performance_recipe.py` (typed primitive + DSDPolicy + builder) | Sonnet | ~120 | none | 1 |
| **A2** | `module3_performance/orchestrator.py` — add `fmc=` to `run_gradient_elution`, route through `_build_m3_chrom_manifest` | Sonnet | ~30 | none | 1 |
| **A3** | `core/recipe_validation.py` — `validate_recipe_first_principles()`: mass-balance closure, `gradient_field` ↔ isotherm consistency, surface-area inheritance check (sci-advisor guardrails 1, 3, 5) | Sonnet | ~150 | A1 | 2 |
| **A4** | `module3_performance/method_simulation.py` — `run_method_simulation` + `MethodSimulationResult` + DSD aggregation; per-DSD full method opt-in | Sonnet | ~250 | A1, A2 | 2 |
| **A5** | `lifecycle/orchestrator.py` — replace dual M3 calls with `run_method_simulation`; wire validate_recipe_first_principles before resolve | Sonnet | ~150 net | A4 | 2 |
| **A6** | `visualization/tabs/tab_m3.py` + `visualization/ui_workflow.py` — switch to `MethodSimulationResult`, add evidence-tier badges to M3 result panels, pass FMC to gradient elute call site | Sonnet | ~120 | A5 | 2 |
| **— G3 audit + v0.2.0 milestone handover —** | Opus | — | — | A6 | — |

**v0.2.0 acceptance:** ruff=0, mypy=0; smoke + DSD-full-method paths green; gradient elution carries calibrated tier when FMC supplies one; recipes that fail first-principles validation are blocked at the lifecycle entry point; tab_m3 displays evidence badges and consumes the new typed result.

### Milestone v0.3.0 — remaining sci guardrails + UI debt

| # | Module | Tier | LOC | Deps | Fix-round budget |
|---|---|---|---|---|---|
| **B1** | `module2_functionalization/family_reagent_matrix.py` — polymer-family × reagent compatibility data + BLOCK in `validate_recipe_first_principles` (sci-advisor guardrail 4) | Sonnet | ~120 | A3 | 2 |
| **B2** | `trust.py` — family-aware trust gate covering alginate / cellulose / PLGA paths (closes v9.1 follow-up) | Sonnet | ~100 | B1 | 2 |
| **B3** | `visualization/tabs/tab_m2.py` + per-family panels — evidence-tier badges on M2 results; family-aware reagent dropdown filtering | Sonnet | ~120 | B1 | 1 |
| **B4** | `core/process_recipe.py` extension — promote remaining family-specific M1 fields from `base_params` into typed recipe `Quantity` slots; update `recipe_resolver` | Sonnet | ~150 | none | 2 |
| **B5** | `visualization/tabs/tab_m1.py` — drop `PipelineOrchestrator` legacy import; recipe-only path | Sonnet | ~80 | B4 | 1 |
| **B6** | `module3_performance/method.py` — demote `cycle_lifetime_to_70pct_capacity`, `log10_reduction`, leaching numeric outputs to ranking labels when no calibration loaded (sci-advisor scope-of-claim) | Haiku | ~40 | none | 1 |
| **B7** | `visualization/nav.py` — implement `build_navigation()` (currently raises NotImplementedError) | Haiku | ~40 | none | 1 |
| **B8** | CSS / branding sweep — rename `--es-*` → `--dps-*`, audit user-facing strings | Haiku | ~50 | none | 1 |
| **— G3 audit + v0.3.0 milestone handover —** | Opus | — | — | B8 | — |

**v0.3.0 acceptance:** Per-family M2/M3 paths produce family-conditioned trust gates; UI cannot construct polymer-family/reagent-incompatible recipes; M1 tab is fully recipe-native; nav.py is functional; cycle-life/leaching outputs read as rankings until calibrated; branding is internally consistent.

---

## Sequencing & parallelism

**Strict-sequential (architect rule):** A1→A2→A3→A4→A5→A6, then B1→B2→B3, then B4→B5, with B6/B7/B8 freely interleavable as filler at GREEN-zone moments. **No two modules implement in parallel.**

**Independent (orderable for context-budget reasons):** A2 can run before A1 if context favours it (no mutual dependency). B6, B7, B8 are independent of every other v0.3 item.

---

## Context-budget risks

- **Highest risk: A4 + A5.** Together ~30k tokens of inner-loop spend. If session enters at >45 % consumed, A5 will land in RED zone. **Action:** trigger compression after A3 audit; pre-allocate ~4 k for the v0.2.0 milestone handover.
- **Medium risk: B1 + B2 + B3.** Family-coverage cluster. ~25 k combined. **Action:** if a fresh session resumes from the v0.2.0 handover, the cluster fits in GREEN. If continued in the same session, compress at the v0.2.0 boundary regardless of zone.
- **Low risk:** A1, A2, A3, A6, B4–B8.

---

## Milestone handovers (mandatory, Opus)

1. **After A6** — v0.2.0 handover. Standard 12-section template. Include: updated module registry, full module-protocol regeneration for B1–B8 so any new session can resume.
2. **After B8** — v0.3.0 handover. Includes status of remaining v9.1+ debt (Python-3.14 compat, full Bayesian fitting / MC LRM = P5++) for v0.4.0 backlog.

---

## Fix-round budget summary

Total budget: 19 fix rounds across 14 modules. If any module exceeds its budget, **escalate to /architect REDESIGN** rather than running a 4th round — protocol defect more likely than implementation defect. Re-audit after fixes is focused, not full six-dimension, **except** when a fix is algorithmic (then D2 reapplied in full per Ref 07 §8).

---

## Non-goals (explicitly deferred to v0.4.0+)

Bin-resolved DSD breakthrough; full MC LRM uncertainty propagation; ProteinAIsotherm `pH_transition`/`steepness` calibration ingest; SOP regulated-batch-record export; Streamlit browser QA automation; `python -m dpsim method` standalone CLI subcommand.
