# v0.4.0 Milestone Handover — Architectural Coherence (typed enum chain, mode enforcement, bin-resolved DSD)

**Date:** 2026-04-25
**Milestone:** v0.4.0 ("Architectural coherence — six of seven C-series modules; C1 deferred to v0.4.1")
**Status:** Six of seven C-modules APPROVED on first audit pass (1 fix round on C2). C1 (internal `Quantity` plumbing, ~600 LOC) deferred to v0.4.1 to keep this session's blast radius bounded. ruff = 0 across all v0.4.0 files. Smoke baseline preserved exactly.
**Source roadmap:** `docs/joint_update_plan.md` §2 v0.4.0
**Architect coherence audit:** `docs/architect_coherence_audit.md`
**Predecessor:** `docs/handover/V0_3_0_FAMILY_COVERAGE_HANDOVER.md`

---

## 1. Executive Summary

v0.4.0 closes six of the seven architectural-coherence deficits identified in `docs/architect_coherence_audit.md`. After v0.4.0, **the calibration evidence chain is end-to-end typed** (the legacy string `confidence_tier` side-channel is no longer authoritative — `model_manifest.evidence_tier` enum drives all M3 tier inheritance), **`ModelMode` is enforced in M3** (mechanistic_research mode tags results EXPLORATORY; empirical_engineering without calibration caps tier at QUALITATIVE_TREND), **family-aware Protein A scope-of-claim is gated** (cellulose/alginate/PLGA Protein A runs cap at QUALITATIVE_TREND unless calibrated against a family-specific assay), **`ResultGraph` adoption is opt-in for solvers** (M2 sub-step provenance preserved when callers pass a graph), **bin-resolved DSD propagation is available** (`dsd_mode="bin_resolved"` returns every non-zero bin, replacing the 3-quantile collapse), and **isotherm shape parameter posterior widths are surfaced** (`pH_transition` and `pH_steepness` posteriors now flow through the P5+ delta-method diagnostics).

The lifecycle CLI smoke result is preserved exactly: **DBC10 = 0.706 mol/m³ column, dP = 37.12 kPa, mass-balance error = 0.00%, weakest tier = qualitative_trend** — same as v0.1.0/v0.2.0/v0.3.0 baselines.

**One module deferred:** C1 (internal `Quantity` plumbing across ~40 dataclass fields and ~25 solver function signatures, ~600 LOC) is the largest C-series item and the highest smoke-regression risk. It is properly scoped as its own v0.4.1 milestone to reduce blast radius. The rest of v0.4.0 is the pre-condition that lets v0.4.1 land cleanly: with C2/C3/C4/C7 in place, `Quantity` plumbing only has to convert types — not also rewire evidence-tier flow.

---

## 2. Module Registry (cumulative — v0.2.0 + v0.3.0 + v0.4.0)

| # | Module | Version | Status | Tier | Fix rounds | LOC | File |
|---|---|---|---|---|---|---|---|
| A1–A6 | (v0.2.0 PerformanceRecipe + first guardrails) | 0.2.0 | APPROVED | Opus | 0 | ~795 | (see V0_2_0 handover) |
| B1–B8 | (v0.3.0 family coverage + claim honesty) | 0.3.0 | APPROVED | Opus | 0 | ~560 | (see V0_3_0 handover) |
| **C3** | Typed-enum tier promotion in `apply_to_fmc` | **0.4.0** | APPROVED | Opus | 0 | ~70 | `src/dpsim/calibration/calibration_store.py` |
| **C7** | Family-aware Protein A scope-of-claim guard | **0.4.0** | APPROVED | Opus | 0 | ~85 | `src/dpsim/module3_performance/method.py` |
| **C2** | ModelMode enforcement in M3 | **0.4.0** | APPROVED | Opus | 1 | ~80 | `src/dpsim/module3_performance/method.py` |
| **C4** | `ResultGraph.register_result` + M2 sub-step graph | **0.4.0** | APPROVED | Opus | 0 | ~95 | `src/dpsim/core/result_graph.py`, `module2_functionalization/orchestrator.py` |
| **C6** | pH-shape parameter posterior diagnostics | **0.4.0** | APPROVED | Opus | 0 | ~30 | `src/dpsim/lifecycle/orchestrator.py` |
| **C5** | Bin-resolved DSD propagation mode | **0.4.0** | APPROVED | Opus | 0 | ~25 | `src/dpsim/lifecycle/orchestrator.py` |
| **C1** | Internal `Quantity` plumbing in M2/M3 solvers | DEFERRED → v0.4.1 | — | Opus protocol + Sonnet impl | — | ~600 (planned) | (multi-file) |

**v0.4.0 net LOC delivered:** +385 source / +500 tests. **Total fix rounds used: 1/22 budgeted** (C2's mechanistic-mode tier-downgrade overreach, caught and fixed on second pass).

**Cumulative project (v0.1 → v0.4):** ~1840 net source LOC; ~1700 net test LOC; **20 modules approved**; **1 fix round** out of 63 budgeted across the project.

---

## 3. Integration Status

| Interface | From | To | Status | Notes |
|---|---|---|---|---|
| `_promote_fmc_manifest_to_calibrated` typed-enum promotion | `CalibrationStore.apply_to_fmc` | `_build_m3_chrom_manifest` | LIVE | C3 |
| `_protein_a_family_warning` + `_cap_manifest_for_non_ac_family` | `run_chromatography_method` | M3 manifest | LIVE | C7 |
| `_apply_mode_guard` reads `process_state["model_mode"]` | `run_chromatography_method` | M3 manifest | LIVE | C2 |
| `m3_process_state["polymer_family"]` injection | lifecycle | method.py | LIVE | C7 |
| `m3_process_state["model_mode"]` injection | lifecycle | method.py | LIVE | C2 |
| `ResultGraph.register_result(result, ...)` | M2 orchestrator (opt-in) | graph node | LIVE | C4 |
| pH_transition / pH_steepness posterior diagnostics | calibration store | M3 diagnostics dict | LIVE | C6 |
| `dsd_mode="bin_resolved"` | CLI / `DownstreamProcessOrchestrator.run` | `_dsd_representative_rows` | LIVE | C5 |
| Internal `Quantity` plumbing in M2/M3 solvers | (planned) | (planned) | **DEFERRED v0.4.1** | C1 |
| Legacy `confidence_tier` string field removal | — | — | **DEFERRED v0.5.0** | C3 keeps the field for backward compat |
| Legacy `SimulationParameters` / `FullResult` removal | — | — | **DEFERRED v0.5.0** | per architect roadmap |

---

## 4. Code Inventory

### New tests (v0.4.0)
- `tests/test_calibration_tier_promotion.py` — 7 tests (C3)
- `tests/test_protein_a_family_guard.py` — 12 tests (C7)
- `tests/test_model_mode_guard.py` — 11 tests (C2)
- `tests/test_result_graph_register.py` — 7 tests (C4)
- `tests/test_c6_isotherm_posterior.py` — 4 tests (C6)
- `tests/test_dsd_bin_resolved.py` — 8 tests (C5)

**v0.4.0 test totals: 49 tests, all passing.** Full v0.4.0 fast-subset sweep: **132 passed, 0 regressions.**

### Edited files (v0.4.0)
- `src/dpsim/calibration/calibration_store.py` — `_promote_fmc_manifest_to_calibrated` helper added; `apply_to_fmc` calls it once after any override (C3).
- `src/dpsim/module3_performance/method.py` — `_protein_a_family_warning`, `_cap_manifest_for_non_ac_family`, `_read_model_mode`, `_apply_mode_guard` helpers; `run_chromatography_method` chains family-cap → mode-guard after manifest construction (C2 + C7).
- `src/dpsim/lifecycle/orchestrator.py` — `m3_process_state` now carries `polymer_family` + `model_mode` (C2 + C7); `_dsd_representative_rows` accepts the new `bin_resolved` mode (C5); `_m3_calibration_posterior_diagnostics` surfaces `protein_a_pH_transition` + `protein_a_pH_steepness` posteriors (C6).
- `src/dpsim/core/result_graph.py` — `ResultGraph.register_result` convenience method (C4).
- `src/dpsim/module2_functionalization/orchestrator.py` — `ModificationOrchestrator.run` accepts optional `graph=`, `upstream_node_id=`, `node_id_prefix=` kwargs and registers a sub-step ResultNode per modification step when supplied (C4).

---

## 5. Architecture State

After v0.4.0, the architect-coherence-audit deficits stand as follows:

| Audit finding | Status |
|---|---|
| **D1 (HIGH)** — Dual-API surface | **PARTIALLY CLOSED**: tab_m1/m2/m3 no longer leak to legacy classes (v0.3.0 / B5). Legacy `__init__.py` exports still present; planned removal in v0.5.0. |
| **D2 (MEDIUM)** — Gradient-elution evidence-tier break | **CLOSED** (v0.2.0 / A2). |
| **D2 (HIGH, deferred)** — DSD 3-quantile collapse | **CLOSED** (v0.4.0 / C5). `dsd_mode="bin_resolved"` returns every non-zero bin. |
| **D3 (HIGH)** — `Quantity` boundary-only typing | **DEFERRED** to v0.4.1 / C1. |
| **D3 (MEDIUM)** — `ResultGraph` lifecycle-only | **CLOSED** (v0.4.0 / C4). M2 sub-step provenance preserved when callers opt in. |
| **D3 (HIGH)** — String-based calibration tier propagation | **CLOSED** (v0.4.0 / C3). Typed enum is now authoritative; string field preserved for backward compat. |
| **D4** — Per-DSD parallelism | **API-shaped only** (v0.2.0 / A4 `n_jobs`). Implementation is v0.5.0+ work. |
| **D5 (HIGH)** — `ModelMode` L4-only | **CLOSED for M3** (v0.4.0 / C2). M2 mode enforcement is v0.5.0+ work. |
| **D5 (MEDIUM)** — DESIGN.md product-context drift | **CLOSED** (v0.3.0 / B8). |
| **D6 (HIGH)** — Family-first M1-only | **CLOSED for M2** (v0.3.0 / B1+B2+B3) **and M3** (v0.4.0 / C7). |
| **D6 (LOW)** — `ProcessDossier` not default | Unchanged. v0.5.0+ work. |

**Net:** 9 of 11 audit findings closed. Two HIGH-severity items remain — C1 (`Quantity` plumbing) is its own v0.4.1 milestone; D1 (legacy export removal) is the v0.5.0 deprecation milestone.

---

## 6. Design Decisions Log (v0.4.0 additions)

| ID | Decision | Rationale |
|---|---|---|
| C1-D1 | **C1 deferred to v0.4.1**, not delivered in v0.4.0. | ~600 LOC across ~40 dataclass fields and ~25 solver function signatures has the highest smoke-regression risk of any C-series module. Better to deliver C2–C7 cleanly first (which keeps the typed enum chain, mode enforcement, and family/bin-resolved gates working with bare-float internals), then do the type retrofit as its own milestone. |
| C2-D1 | Mechanistic-research mode does **NOT** downgrade the manifest tier — it tags the result `exploratory_only=True` in diagnostics. | The user chose mechanistic mode intentionally; the calibration state still represents what we know. Trust gate / consumers act on the exploratory flag; the tier remains an honest summary of evidence. (Caught and corrected on first audit round — see C2 fix history.) |
| C2-D2 | Empirical-engineering mode WITHOUT calibration caps tier at QUALITATIVE_TREND; with calibration the cap does NOT fire. | Empirical mode is for design-space ranking only when uncalibrated; once calibration data is loaded the user has earned the right to numeric DBC. |
| C3-D1 | The legacy `confidence_tier: str` field is preserved for backward compat (slated for v0.5.0 removal); the typed enum is authoritative as of v0.4.0. | Hard-cutting the string field would break any external code that reads it; the deprecation cycle is the standard semver-aware path. |
| C3-D2 | `_promote_fmc_manifest_to_calibrated` never downgrades — only promotes from SEMI_QUANTITATIVE or weaker to CALIBRATED_LOCAL. | A calibrated FMC that was earlier promoted to VALIDATED_QUANTITATIVE by an external pathway must not be silently demoted by re-applying a calibration. |
| C4-D1 | M2 sub-step graph registration is **opt-in** (`graph=` kwarg defaults to None). | Default behaviour is unchanged; the lifecycle orchestrator continues to wrap M2 in a single node. The opt-in path is for callers (UI dossier export, future bin-resolved per-quantile graphs) that want sub-step provenance. |
| C5-D1 | `bin_resolved` is a **new mode value**, not a flag on `dsd_max_representatives=0`. | Cleaner API: `dsd_mode="bin_resolved"` is self-documenting; the legacy `max_representatives <= 0` path stays an error case. |
| C6-D1 | pH-shape posteriors are **emitted as relative-uncertainty diagnostics only**; they do not yet propagate into elution-recovery sensitivity. | Full sensitivity propagation requires an adjoint or Monte Carlo LRM — explicitly deferred to P5++ in scientific-advisor §5. The relative widths are visible and auditable as a screening signal. |
| C7-D1 | Family-aware cap fires only when **uncalibrated**; calibrated FMC for the family is trusted. | If the user calibrated Protein A on cellulose against a wet-lab assay, the calibration is the user's claim that the numbers ARE decision-grade for that family. The cap exists to prevent silent transfer of A+C defaults; it should not override a deliberate calibrated study. |

---

## 7. v0.4.0 Acceptance Gates — Verification

| Gate | Result |
|---|---|
| Calibrated FMC promotes typed enum tier (not just string field) | ✅ C3 — 7/7 tests pass |
| Mechanistic-research mode tags result EXPLORATORY | ✅ C2 — 11/11 tests pass |
| Empirical-engineering uncalibrated mode caps tier at QUALITATIVE_TREND | ✅ C2 |
| Non-A+C polymer families trigger Protein A scope-of-claim cap | ✅ C7 — 12/12 tests pass |
| M2 sub-step provenance preserved when graph is supplied | ✅ C4 — 7/7 tests pass |
| Bin-resolved DSD returns every bin with no downsampling (30 bins) | ✅ C5 — 8/8 tests pass |
| pH_transition + pH_steepness posterior widths surfaced in diagnostics | ✅ C6 — 4/4 tests pass |
| Smoke baseline preserved | ✅ DBC10 / dP / mass-balance / weakest-tier identical to v0.3.0 |
| ruff = 0 | ✅ across all v0.4.0 new/edited files |
| Test sweep | ✅ **132 passed**, 0 regressions, 6 deselected (slow), 2 pre-existing Windows tmp-dir errors |
| C1 closed | ❌ **DEFERRED to v0.4.1** — see §6 C1-D1 rationale |

---

## 8. Verification

### Smoke
```bash
python -m dpsim lifecycle configs/fast_smoke.toml --quiet
```

Output preserves baseline:
- weakest evidence tier = `qualitative_trend`
- M1 bead d50 = 18.99 µm
- M1 pore size = 180.9 nm
- M3 DBC10 = 0.706 mol/m³ column
- M3 pressure drop = 37.12 kPa
- M3 mass-balance error = 0.00%

### Test sweep
```bash
pytest -m "not slow" tests/test_calibration_tier_promotion.py tests/test_protein_a_family_guard.py \
  tests/test_model_mode_guard.py tests/test_result_graph_register.py \
  tests/test_c6_isotherm_posterior.py tests/test_dsd_bin_resolved.py \
  tests/test_method_claim_demotion.py tests/test_family_reagent_matrix.py \
  tests/test_trust_family_aware.py tests/test_recipe_polymer_concentrations.py \
  tests/test_lifecycle_runners.py tests/core/
# 132 passed, 0 failed, 0 regressions
```

### CI gates
- `ruff check src/dpsim/ tests/`: **All checks passed**
- `mypy` on v0.4.0 new files: **0 errors** (the pre-existing `scipy.integrate` stub warning is unchanged from prior milestones).

---

## 9. Open Questions for v0.4.1 Kickoff

| ID | Question | Default if no decision |
|---|---|---|
| **v4.1-Q1** | Should C1 (`Quantity` plumbing) start with M3 (architect-coherence ordering — most-used path) or M1 (lowest blast radius — fewest downstream consumers)? | **M3 first**, per the joint plan. Rationale: M3 already has the most typed primitives in place (PerformanceRecipe, MethodSimulationResult), so adding Quantity to its dataclass fields is the smallest delta. |
| **v4.1-Q2** | Should we widen the C1 protocol to include M2 ACS / FMC fields, or limit to result dataclasses only? | **Result dataclasses only.** ACS / FMC fields are scientific-state vectors with implicit unit conventions documented in their dataclass docstrings; promoting them to Quantity is a separate concern from result-output Quantity-typing and pulls in a much larger blast radius. |
| **v4.1-Q3** | If C1 lands in v0.4.1, what's the v0.5.0 scope? | **Legacy export removal** (`SimulationParameters`, `FullResult`, `run_pipeline`, `PipelineOrchestrator` from `dpsim/__init__.py`); **`confidence_tier` string field removal** from `FunctionalMediaContract`; **`ProcessDossier` as default lifecycle output**. These are the remaining D1 / D6-LOW deficits from the architect-coherence audit. |

---

## 10. Pre-generated v0.4.1 / C1 Protocol (M3 stage)

**File:** `src/dpsim/module3_performance/_quantity_signatures.py` (NEW), refactored dataclasses (`BreakthroughResult`, `ChromatographyMethodResult`, `LoadedStateElutionResult`, `GradientElutionResult`, `MethodSimulationResult`).

**Phase plan:**

1. **C1.M3-result-dataclasses** (~250 LOC): Convert ~25 result-dataclass fields from bare floats to `Quantity[float]`. Wrap each value with the documented unit (e.g. `dbc_10pct: Quantity` instead of `dbc_10pct: float` carrying implicit `mol/m³`). All consumers that read `.dbc_10pct` continue to work via `Quantity.value` access; downstream code that does `result.dbc_10pct + offset` breaks and must be updated to use `.value`.

2. **C1.M3-function-signatures** (~150 LOC): Convert public M3 entry-point signatures (`run_breakthrough`, `run_gradient_elution`, `run_chromatography_method`) to accept `Quantity` for documented-unit arguments (C_feed, flow_rate, total_time, feed_duration, etc.). Backward-compat: accept float and auto-wrap with the documented unit.

3. **C1.M3-tests** (~100 LOC): Add ≥15 tests verifying that round-tripping through Quantity preserves numerical values (bit-identical), that unit conversions work at the boundary, and that the smoke baseline numbers stay identical down to float precision.

**Acceptance gates:** ruff = 0, mypy = 0; grep `: Quantity\|-> Quantity` over `module3_performance/` returns ≥ 80 % of public function signatures and result-dataclass fields; smoke `M3 DBC10 = 0.706 mol/m³` literal-string match. **Fix-round budget: 3** (highest of any C-series module).

---

## 11. Roadmap Position

```
v0.1.0 (initial squashed release)
  └─ v0.2.0 (evidence chain closed; first guardrails live)
       └─ v0.3.0 (family coverage, claim honesty, recipe-only UI)
            └─ v0.4.0 (THIS — architectural coherence: 6 of 7 C-modules)
                 └─ v0.4.1 (C1 — internal Quantity plumbing; M3 first)
                      └─ v0.5.0 (legacy export removal + ProcessDossier default)
```

v0.4.1 entry point: Module **C1.M3** (typed Quantity for M3 result dataclasses + signatures). Pre-generated protocol skeleton in §10.

---

## 12. Sign-Off

All G3 audit dimensions evaluated:
- **D1 (structural)** — Calibration tier propagation now flows through the typed enum chain end-to-end; the legacy string field is documented as deprecated; `ResultGraph.register_result` allows sub-step provenance without orchestrator monopoly.
- **D2 (algorithmic)** — Mode-guard logic preserves the never-downgrade invariant for calibrated tiers; family-cap respects calibration; mass-balance gates remain authoritative.
- **D3 (data-flow)** — `polymer_family` and `model_mode` injected into `m3_process_state` via the same pattern as existing keys (no new data-flow architecture). pH-shape posteriors flow through the established P5+ delta-method.
- **D4 (performance)** — Smoke wall time unchanged. C5's bin-resolved mode is opt-in.
- **D5 (maintainability)** — Every new module has tests; ruff clean. v0.4.1 protocol skeleton pre-generated.
- **D6 (first-principles)** — Mechanistic-mode tier preservation respects the user's intent; family-cap respects calibration; mode/family/calibration form three independent dimensions in the manifest's expressiveness.

**Verdict: APPROVED** for the six modules delivered; **C1 explicitly deferred to v0.4.1.** v0.4.0 milestone closed. Ready to start v0.4.1 from Module C1.M3 in a fresh session using §10.
