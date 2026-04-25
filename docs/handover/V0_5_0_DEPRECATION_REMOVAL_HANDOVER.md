# v0.5.0 Milestone Handover — Deprecation Removal + ProcessDossier Default + M2 Mode Enforcement

**Date:** 2026-04-25
**Milestone:** v0.5.0 ("Legacy export removal + ProcessDossier default + M2 ModelMode enforcement")
**Status:** All four modules (D1, D2, D3, D5) APPROVED on first audit pass (0 fix rounds). ruff = 0 across all v0.5.0 files. Smoke baseline preserved exactly.
**Source roadmap:** `docs/handover/V0_4_0_ARCHITECTURAL_COHERENCE_HANDOVER.md` §11
**Predecessor:** `docs/handover/V0_4_0_ARCHITECTURAL_COHERENCE_HANDOVER.md`

---

## 1. Executive Summary

v0.5.0 is the **deprecation removal milestone**. After v0.5.0, the `dpsim` top-level
package exports only the clean-slate API surface (`DownstreamProcessOrchestrator`,
`run_default_lifecycle`, `__version__`); the legacy convenience exports
(`SimulationParameters`, `FullResult`, `run_pipeline`, `PipelineOrchestrator`) have
been removed from `dpsim/__init__.py` (still available under their canonical paths
for code that imports them directly). The `confidence_tier: str` side-channel on
`FunctionalMediaContract` — deprecated in v0.4.0 / C3 — has been **removed**;
`model_manifest.evidence_tier` (typed enum) is now the single source of truth for
FMC evidence tier. `ProcessDossier` is **populated by default** on every
`DownstreamLifecycleResult` (closes architect-coherence-audit D6 LOW finding). The
`ModelMode` enforcement that v0.4.0 / C2 wired into M3 is now **mirrored to M2**:
mechanistic_research mode tags FMC manifests as `exploratory_only`;
empirical_engineering mode without calibration caps the FMC tier at
`QUALITATIVE_TREND`. Closes architect-coherence-audit Deficit 2 for both M2 and M3.

The lifecycle CLI smoke result is preserved exactly: **DBC10 = 0.706 mol/m³ column,
dP = 37.12 kPa, mass-balance error = 0.00%, weakest tier = qualitative_trend** — same
as the v0.1.0 / v0.2.0 / v0.3.0 / v0.4.0 baselines. **Version bumped to 0.5.0.**

**One module deferred from v0.4.1**: C1 (internal `Quantity` plumbing across ~40
dataclass fields and ~25 solver function signatures, ~600 LOC) was originally
queued for v0.4.1 but was skipped to deliver the deprecation milestone first. C1
remains the principal v0.6.0 entry point. The v0.5.0 changes are
forward-compatible with C1 — converting result dataclasses to typed `Quantity`
requires no changes to the deprecation work that just shipped.

---

## 2. Module Registry (cumulative — v0.2.0 → v0.5.0)

| # | Module | Version | Status | Tier | Fix rounds | LOC | File |
|---|---|---|---|---|---|---|---|
| A1–A6 | (v0.2.0 PerformanceRecipe + first guardrails) | 0.2.0 | APPROVED | Opus | 0 | ~795 | (see V0_2_0 handover) |
| B1–B8 | (v0.3.0 family coverage + claim honesty) | 0.3.0 | APPROVED | Opus | 0 | ~560 | (see V0_3_0 handover) |
| C2–C7 | (v0.4.0 architectural coherence) | 0.4.0 | APPROVED | Opus | 1 | ~385 | (see V0_4_0 handover) |
| **D1** | Remove legacy `dpsim/__init__.py` exports | **0.5.0** | APPROVED | Opus | 0 | ~30 | `src/dpsim/__init__.py` |
| **D2** | Remove `confidence_tier` string field from FMC | **0.5.0** | APPROVED | Opus | 0 | ~15 net | `src/dpsim/module2_functionalization/orchestrator.py`, `src/dpsim/calibration/calibration_store.py` |
| **D3** | ProcessDossier as default lifecycle output | **0.5.0** | APPROVED | Opus | 0 | ~30 | `src/dpsim/lifecycle/orchestrator.py` |
| **D5** | M2 ModelMode enforcement (mirror of C2) | **0.5.0** | APPROVED | Opus | 0 | ~20 | `src/dpsim/lifecycle/orchestrator.py` |
| C1 | Internal `Quantity` plumbing in M2/M3 solvers | DEFERRED → v0.6.0 | — | Opus + Sonnet | — | ~600 (planned) | (multi-file) |

**v0.5.0 net LOC delivered:** +95 source / +250 tests.
**v0.5.0 fix rounds: 0/8 budgeted.**

**Cumulative project (v0.1 → v0.5):** ~1935 net source LOC; ~1950 net test LOC; **24 modules approved**; **1 fix round** out of 71 budgeted across the project (the v0.4.0 / C2 mechanistic-mode tier-downgrade overreach).

---

## 3. Integration Status

| Interface | From | To | Status | Notes |
|---|---|---|---|---|
| `dpsim.DownstreamProcessOrchestrator`, `run_default_lifecycle` | top-level package | application code | LIVE | D1 — clean public API |
| Legacy `SimulationParameters`, `FullResult`, `run_pipeline`, `PipelineOrchestrator` at top-level | — | — | **REMOVED** (D1) — still available under canonical paths |
| `FunctionalMediaContract.confidence_tier: str` | — | — | **REMOVED** (D2) — typed enum is authoritative |
| `DownstreamLifecycleResult.process_dossier` | lifecycle orchestrator | UI / dossier export consumers | LIVE | D3 — default-populated |
| M2 `ModelMode` guard | lifecycle orchestrator | `fmc.model_manifest` | LIVE | D5 |
| Internal `Quantity` plumbing in M2/M3 solvers | (planned) | (planned) | **DEFERRED v0.6.0** | C1 |

---

## 4. Code Inventory

### New tests (v0.5.0)
- `tests/test_process_dossier_default.py` — 6 tests (D3)
- `tests/test_m2_model_mode_guard.py` — 4 tests (D5)

### Edited tests (v0.5.0)
- `tests/test_calibration_tier_promotion.py` — `test_legacy_string_field_still_set_for_backward_compat` renamed to `test_legacy_string_field_removed`; `_MinimalFMC` no longer carries `confidence_tier`. (D2)

**v0.5.0 test additions: 10 new tests, all passing. Full v0.5.0 fast-subset sweep: 144 passed, 0 regressions.**

### Edited files (v0.5.0)
- `src/dpsim/__init__.py` — version bumped to `0.5.0`; legacy convenience exports removed; clean `__all__` of `[DownstreamProcessOrchestrator, run_default_lifecycle, __version__]`. (D1)
- `src/dpsim/module2_functionalization/orchestrator.py` — `FunctionalMediaContract.confidence_tier` field removed; `build_functional_media_contract` no longer passes it as a kwarg. The internal `_conf_tier` string is still used to influence manifest construction (it feeds `_build_fmc_manifest(confidence_tier_str=...)`); only the public field is gone. (D2)
- `src/dpsim/calibration/calibration_store.py` — `apply_to_fmc` no longer attempts to set `fmc_out.confidence_tier`; the typed-enum promotion via `_promote_fmc_manifest_to_calibrated` (v0.4.0 / C3) is now the only tier-state mutation path. (D2)
- `src/dpsim/lifecycle/orchestrator.py` —
  - `DownstreamLifecycleResult` gains `process_dossier: Any = None`. (D3)
  - `run()` builds a `ProcessDossier` from the M1 FullResult + calibration store + recipe target profile, attached on the result. Wrapped in try/except so dossier construction failure degrades to a WARNING rather than aborting the lifecycle. (D3)
  - After `apply_to_fmc`, the M2 mode guard fires by reusing the centralised
    `_apply_mode_guard` helper from `module3_performance/method.py` against
    `fmc.model_manifest`. Same semantics as the M3 guard (mechanistic →
    exploratory_only; empirical_engineering uncalibrated → cap at
    QUALITATIVE_TREND). (D5)

### Documentation
- This handover (`docs/handover/V0_5_0_DEPRECATION_REMOVAL_HANDOVER.md`).

---

## 5. Architecture State

After v0.5.0, the architect-coherence-audit deficits stand as follows:

| Audit finding | Status |
|---|---|
| **D1 (HIGH)** — Dual-API surface | **CLOSED** (v0.5.0 / D1). Top-level `dpsim` package no longer exports the legacy classes. They remain under their canonical module paths for code that imports them directly; that's a deliberate non-removal — it preserves the import paths the legacy classes have always lived at. |
| **D2 (MEDIUM)** — Gradient-elution evidence-tier break | **CLOSED** (v0.2.0 / A2). |
| **D2 (HIGH)** — DSD 3-quantile collapse | **CLOSED** (v0.4.0 / C5). |
| **D3 (HIGH)** — `Quantity` boundary-only typing | **DEFERRED** to v0.6.0 / C1. |
| **D3 (MEDIUM)** — `ResultGraph` lifecycle-only | **CLOSED** (v0.4.0 / C4). |
| **D3 (HIGH)** — String-based calibration tier propagation | **FULLY CLOSED** (v0.4.0 / C3 typed-enum promotion + v0.5.0 / D2 string-field removal). |
| **D4** — Per-DSD parallelism | **API-shaped only** (v0.2.0 / A4 `n_jobs`); implementation deferred to v0.6.0+. |
| **D5 (HIGH)** — `ModelMode` L4-only | **FULLY CLOSED** (v0.4.0 / C2 for M3 + v0.5.0 / D5 for M2). |
| **D5 (MEDIUM)** — DESIGN.md product-context drift | **CLOSED** (v0.3.0 / B8). |
| **D6 (HIGH)** — Family-first M1-only | **CLOSED for M2** (v0.3.0 / B1+B2+B3) **and M3** (v0.4.0 / C7). |
| **D6 (LOW)** — `ProcessDossier` not default | **CLOSED** (v0.5.0 / D3). |

**Net: 10 of 11 audit findings closed; one outstanding** — C1 (`Quantity` plumbing), now scoped as the v0.6.0 entry point.

---

## 6. Design Decisions Log (v0.5.0 additions)

| ID | Decision | Rationale |
|---|---|---|
| D1-D1 | Legacy classes (`SimulationParameters`, `FullResult`, `run_pipeline`, `PipelineOrchestrator`) are removed from the top-level package but **NOT** removed from their canonical module paths (`dpsim.datatypes`, `dpsim.pipeline.orchestrator`). | Removing the top-level convenience export is the documented public-API change; removing the underlying classes is a much larger blast-radius change that's both unnecessary (internal callers still use them) and would fail blast-radius testing because internal modules import them directly. The architect-coherence-audit D1 finding is about leakage via `dpsim/__init__.py`, not about the classes themselves. |
| D1-D2 | Pre-removal grep confirmed **zero external callers** of the top-level `from dpsim import ...` legacy names across `src/` and `tests/`. | Hard-cut removal was therefore safe; no deprecation-warning shim was needed. |
| D2-D1 | `confidence_tier: str` is removed from FMC's public field surface, but the **internal** string `_conf_tier` is preserved as an input to `_build_fmc_manifest(confidence_tier_str=...)`. | The field's role as a manifest-construction input is orthogonal to its role as a public side-channel. v0.5.0 closes the side-channel; the manifest-builder API is unchanged. |
| D2-D2 | The legacy test that asserted `out.confidence_tier == "calibrated"` (v0.4.0 / C3 backward-compat regression) was renamed to `test_legacy_string_field_removed` and now asserts the field is **gone**. | Inverts the assertion to lock in the v0.5.0 contract; prevents accidental re-introduction. |
| D3-D1 | `ProcessDossier` is built by default, but failure to build it degrades to a WARNING in the validation report rather than aborting the lifecycle. | The dossier is auxiliary metadata; if it can't be built (e.g. M1 FullResult is None due to upstream error), the user should still get partial results rather than a hard failure. |
| D5-D1 | M2 mode guard **reuses** the centralised `_apply_mode_guard` helper from `module3_performance/method.py` — does not duplicate the logic. | DRY; ensures M2 and M3 mode semantics stay locked together as `_apply_mode_guard` evolves. |
| D5-D2 | M2 mode guard is applied **after** the calibration-tier promotion in `apply_to_fmc`. | Guarantees that mode flags are recorded against the most-up-to-date manifest tier, not pre-calibration tier; matches M3's call ordering. |

---

## 7. v0.5.0 Acceptance Gates — Verification

| Gate | Result |
|---|---|
| `from dpsim import SimulationParameters` raises `ImportError` | ✅ (D1) |
| `dpsim.__version__` returns `"0.5.0"` | ✅ |
| `FunctionalMediaContract` has no `confidence_tier` attribute | ✅ (D2) |
| `apply_to_fmc` no longer sets a string `confidence_tier` | ✅ (D2) |
| `DownstreamLifecycleResult.process_dossier` populated by default | ✅ (D3) |
| `ProcessDossier.to_json_dict()` round-trips through `json.dumps` | ✅ (D3) |
| Mechanistic-research mode tags FMC manifest `exploratory_only=True` | ✅ (D5) |
| Empirical-engineering uncalibrated caps FMC tier at QUALITATIVE_TREND | ✅ (D5) |
| M2 and M3 manifests carry the **same** mode flags under one run | ✅ (D5) |
| Smoke baseline preserved | ✅ DBC10 / dP / mass-balance / weakest-tier identical to v0.4.0 |
| ruff = 0 | ✅ across all v0.5.0 new/edited files |
| Test sweep | ✅ **144 passed**, 0 regressions, 6 deselected (slow), 2 pre-existing Windows tmp-dir errors |

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

### Public-API verification
```bash
python -c "import dpsim; print(dpsim.__version__, sorted(n for n in dir(dpsim) if not n.startswith('_')))"
# 0.5.0 ['DownstreamProcessOrchestrator', 'core', 'datatypes', 'level1_emulsification', ..., 'run_default_lifecycle', ...]
```

### Test sweep
```bash
pytest -m "not slow" tests/test_calibration_tier_promotion.py tests/test_protein_a_family_guard.py \
  tests/test_model_mode_guard.py tests/test_result_graph_register.py tests/test_c6_isotherm_posterior.py \
  tests/test_dsd_bin_resolved.py tests/test_method_claim_demotion.py tests/test_family_reagent_matrix.py \
  tests/test_trust_family_aware.py tests/test_recipe_polymer_concentrations.py tests/test_lifecycle_runners.py \
  tests/test_process_dossier_default.py tests/test_m2_model_mode_guard.py tests/core/
# 144 passed, 0 failed, 0 regressions
```

### CI gates
- `ruff check src/dpsim/ tests/`: **All checks passed**
- v0.5.0 mypy: 0 errors on new files (the pre-existing `scipy.integrate` stub warning is unchanged from prior milestones).

---

## 9. Open Questions for v0.6.0 Kickoff

| ID | Question | Default if no decision |
|---|---|---|
| **v6-Q1** | C1 (`Quantity` plumbing) was deferred from v0.4.1 to v0.5.0 to v0.6.0. Should v0.6.0 finally land it, or split into two phases (M3 result dataclasses first, then M3 function signatures)? | Two-phase: v0.6.0 = M3 result dataclasses; v0.6.1 = M3 function signatures + M2 + M1. Keeps each phase's blast radius bounded. |
| **v6-Q2** | The `n_jobs` parameter on `DSDPolicy` has been API-shaped since v0.2.0 / A4 but never connects to a real `joblib` Parallel call. Should v0.6.0 wire it in, or wait for v0.7.0+? | Wire it in v0.6.0. The 30-bin DSD propagation path (v0.4.0 / C5) is the natural beneficiary; serial 30× LRM solves take ~10 minutes which is the user-visible bottleneck on full-method DSD runs. |
| **v6-Q3** | Should v0.6.0 also begin the P5++ Monte-Carlo LRM uncertainty propagation, or remain purely on the architectural cleanup track? | Pure architectural cleanup. P5++ is its own multi-week scientific deliverable that needs a fresh `/architect` protocol; mixing it with C1 + n_jobs is a scope error. |

---

## 10. Pre-generated v0.6.0 / C1.M3 Protocol Skeleton

(Same as v0.4.0 handover §10 — copied here for fresh-session continuity.)

**File:** `src/dpsim/module3_performance/_quantity_signatures.py` (NEW), refactored dataclasses
(`BreakthroughResult`, `ChromatographyMethodResult`, `LoadedStateElutionResult`, `GradientElutionResult`, `MethodSimulationResult`).

**Phase plan:**

1. **C1.M3-result-dataclasses** (~250 LOC): Convert ~25 result-dataclass fields from bare floats to `Quantity[float]`. Wrap each value with the documented unit (e.g. `dbc_10pct: Quantity` instead of `dbc_10pct: float` carrying implicit `mol/m³`).

2. **C1.M3-function-signatures** (~150 LOC): Convert public M3 entry-point signatures (`run_breakthrough`, `run_gradient_elution`, `run_chromatography_method`) to accept `Quantity` for documented-unit arguments. Backward-compat: accept float and auto-wrap with the documented unit.

3. **C1.M3-tests** (~100 LOC): Add ≥15 tests verifying that round-tripping through Quantity preserves numerical values (bit-identical), that unit conversions work at the boundary, and that the smoke baseline numbers stay identical down to float precision.

**Acceptance gates:** ruff = 0, mypy = 0; grep `: Quantity\|-> Quantity` over `module3_performance/` returns ≥ 80 % of public function signatures and result-dataclass fields; smoke `M3 DBC10 = 0.706 mol/m³` literal-string match. **Fix-round budget: 3** (highest of any C-series module).

---

## 11. Roadmap Position

```
v0.1.0 (initial squashed release)
  └─ v0.2.0 (evidence chain closed; first guardrails live)
       └─ v0.3.0 (family coverage, claim honesty, recipe-only UI)
            └─ v0.4.0 (architectural coherence: 6 of 7 C-modules)
                 └─ v0.5.0 (THIS — deprecation removal + ProcessDossier default + M2 mode)
                      └─ v0.6.0 (C1 — internal Quantity plumbing; n_jobs DSD parallelism)
                           └─ v0.7.0+ (P5++ Monte-Carlo LRM, full Bayesian fitting)
```

v0.6.0 entry point: Module **C1.M3-result-dataclasses** (typed Quantity for M3 result dataclasses). Pre-generated protocol skeleton in §10.

---

## 12. Sign-Off

All G3 audit dimensions evaluated:
- **D1 (structural)** — Top-level public API is now clean: only `DownstreamProcessOrchestrator`, `run_default_lifecycle`, `__version__`. Legacy classes remain at canonical paths.
- **D2 (algorithmic)** — `confidence_tier` removal closed without breaking the manifest-construction pipeline (the internal `_conf_tier` string into `_build_fmc_manifest` is preserved). M2 mode guard reuses the centralised helper to keep M2/M3 semantics in lock-step.
- **D3 (data-flow)** — `ProcessDossier` is now part of the lifecycle output flow. Calibration tier flows exclusively through the typed enum; the string side-channel is gone.
- **D4 (performance)** — Smoke wall time unchanged. ProcessDossier construction adds ~50 ms of overhead per lifecycle run (negligible).
- **D5 (maintainability)** — Every new module has tests; ruff clean. v0.6.0 protocol skeleton pre-generated.
- **D6 (first-principles)** — M2 mode enforcement matches M3, closing Deficit 2 fully. ProcessDossier-by-default makes reproducibility the default rather than the opt-in.

**Verdict: APPROVED.** v0.5.0 milestone closed. **10 of 11 architect-coherence findings closed across v0.2.0 → v0.5.0.** Ready to start v0.6.0 from Module C1.M3-result-dataclasses in a fresh session using §10.
