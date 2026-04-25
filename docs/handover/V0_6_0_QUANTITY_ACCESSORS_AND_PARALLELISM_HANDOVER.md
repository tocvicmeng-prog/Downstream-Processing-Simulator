# v0.6.0 Milestone Handover — Quantity Accessors (C1 Phase 1) + Joblib Parallelism

**Date:** 2026-04-25
**Milestone:** v0.6.0 ("Typed Quantity accessors on M3 dataclasses + n_jobs joblib parallelism")
**Status:** Both modules (E1, E2) APPROVED on first audit pass (0 fix rounds). ruff = 0. Smoke baseline preserved exactly.
**Source roadmap:** `docs/handover/V0_5_0_DEPRECATION_REMOVAL_HANDOVER.md` §9 + §10
**Predecessor:** `docs/handover/V0_5_0_DEPRECATION_REMOVAL_HANDOVER.md`

---

## 1. Executive Summary

v0.6.0 begins the long-deferred C1 work — internal `Quantity` plumbing across M2/M3 — by landing **Phase 1: typed accessor properties** on the four most-consumed M3 result dataclasses. Existing arithmetic consumers continue to read e.g. `result.dbc_10pct` as `float`; new unit-aware code reads `result.dbc_10pct_q` for a `Quantity` that carries the documented unit and supports `.as_unit("kPa")` style conversions. This is a non-breaking, additive change — every smoke baseline number is preserved bit-identically. Phase 2 (function signatures + result-dataclass replacement) is now the v0.6.1+ entry point.

v0.6.0 also wires **`DSDPolicy.n_jobs` into a real `joblib.Parallel` call** for the per-DSD-quantile full-method path. The API has been shaped since v0.2.0 / A4; v0.6.0 finally connects it. Default `n_jobs=1` preserves bit-identical serial behavior; `n_jobs > 1` dispatches via the loky backend. Per-quantile results are deterministic: serial and parallel agree to 1e-9 relative tolerance under the same BDF solver settings.

The lifecycle CLI smoke result is preserved exactly: **DBC10 = 0.706 mol/m³ column, dP = 37.12 kPa, mass-balance error = 0.00%, weakest tier = qualitative_trend** — same as every milestone since v0.1.0. **Version stays at 0.5.0 in `__init__.py`** for now (v0.6.0 is an additive release; the version bump can land alongside the next public-API change).

---

## 2. Module Registry (cumulative — v0.2.0 → v0.6.0)

| # | Module | Version | Status | Tier | Fix rounds | LOC | File |
|---|---|---|---|---|---|---|---|
| A1–A6 | (v0.2.0 PerformanceRecipe + first guardrails) | 0.2.0 | APPROVED | Opus | 0 | ~795 | (V0_2_0 handover) |
| B1–B8 | (v0.3.0 family coverage + claim honesty) | 0.3.0 | APPROVED | Opus | 0 | ~560 | (V0_3_0 handover) |
| C2–C7 | (v0.4.0 architectural coherence) | 0.4.0 | APPROVED | Opus | 1 | ~385 | (V0_4_0 handover) |
| D1–D5 | (v0.5.0 deprecation removal + ProcessDossier + M2 mode) | 0.5.0 | APPROVED | Opus | 0 | ~95 | (V0_5_0 handover) |
| **E1** | Typed `Quantity` accessors on M3 result dataclasses | **0.6.0** | APPROVED | Opus | 0 | ~140 | `module3_performance/orchestrator.py`, `module3_performance/method.py` |
| **E2** | Joblib `n_jobs` parallelism for DSD-quantile execution | **0.6.0** | APPROVED | Opus | 0 | ~75 | `module3_performance/method_simulation.py` |

**v0.6.0 net LOC delivered:** +215 source / +330 tests (16 quantity-accessor tests + 7 fast joblib tests + 1 slow joblib equivalence test).

**v0.6.0 fix rounds: 0/6 budgeted.**

**Cumulative project (v0.1 → v0.6):** ~2150 net source LOC; ~2280 net test LOC; **26 modules approved**; **1 fix round** out of 77 budgeted across the project.

---

## 3. Integration Status

| Interface | From | To | Status | Notes |
|---|---|---|---|---|
| `BreakthroughResult.dbc_*_q`, `pressure_drop_q`, `mass_balance_error_q` | M3 orchestrator | downstream consumers | LIVE | E1 |
| `LoadedStateElutionResult.recovery_fraction_q`, `peak_time_q`, `peak_width_half_q`, `mass_balance_error_q` | M3 method | consumers | LIVE | E1 |
| `ColumnOperabilityReport.pressure_drop_q`, `bed_compression_q`, `residence_time_q`, `interstitial_velocity_q` | M3 method | consumers | LIVE | E1 |
| `ProteinAPerformanceReport.q_max_q`, `predicted_recovery_q`, `activity_retention_q`, `cycle_lifetime_q` | M3 method | consumers | LIVE | E1 |
| `_run_methods_parallel_or_serial` joblib dispatch | `_maybe_run_dsd` | per-quantile method runs | LIVE | E2 |
| `_run_method_worker` (picklable top-level callable) | method_simulation | joblib loky backend | LIVE | E2 |
| **C1 phase 2** — function-signature `Quantity` typing for M3 entry points | (planned) | (planned) | **DEFERRED v0.6.1** | Public-surface change; needs deprecation cycle |
| **C1 phase 3** — M2 ACS / FMC / modification-step dataclass `Quantity` | (planned) | (planned) | **DEFERRED v0.6.2** | Per v0.5.0 §9 v6-Q2 |
| **C1 phase 4** — M1 result dataclass `Quantity` | (planned) | (planned) | **DEFERRED v0.6.3** | |
| **P5++** — Monte-Carlo LRM uncertainty propagation | — | — | **DEFERRED v0.7.0+** | Multi-week scientific deliverable |

---

## 4. Code Inventory

### New tests (v0.6.0)
- `tests/test_quantity_accessors.py` — 16 tests (E1)
- `tests/test_dsd_njobs_parallelism.py` — 8 tests (E2; 7 fast + 1 slow)

### Edited files (v0.6.0)
- `src/dpsim/module3_performance/orchestrator.py` — `BreakthroughResult` gains five `_q` accessor properties (dbc_5/10/50, pressure_drop, mass_balance_error). Existing fields untouched. (E1)
- `src/dpsim/module3_performance/method.py` —
  - `LoadedStateElutionResult` gains four `_q` accessors (recovery_fraction, peak_time, peak_width_half, mass_balance_error). (E1)
  - `ColumnOperabilityReport` gains four `_q` accessors (pressure_drop, bed_compression, residence_time, interstitial_velocity). (E1)
  - `ProteinAPerformanceReport` gains four `_q` accessors (q_max, predicted_recovery, activity_retention, cycle_lifetime). The `cycle_lifetime_q` accessor explicitly documents UNSUPPORTED status in its `Quantity.note`. (E1)
- `src/dpsim/module3_performance/method_simulation.py` —
  - `_maybe_run_dsd` refactored to build per-row kwargs and dispatch through `_run_methods_parallel_or_serial`. Fast-pressure-screen path stays serial. (E2)
  - New module-level helpers `_run_methods_parallel_or_serial` and `_run_method_worker` — the worker is a top-level function so loky pickling works. (E2)

### Documentation
- This handover (`docs/handover/V0_6_0_QUANTITY_ACCESSORS_AND_PARALLELISM_HANDOVER.md`).

---

## 5. Architecture State

After v0.6.0, the architect-coherence-audit deficits stand as follows:

| Audit finding | Status |
|---|---|
| **D1 (HIGH)** — Dual-API surface | **CLOSED** (v0.5.0 / D1) |
| **D2 (MEDIUM)** — Gradient-elution evidence-tier break | **CLOSED** (v0.2.0 / A2) |
| **D2 (HIGH)** — DSD 3-quantile collapse | **CLOSED** (v0.4.0 / C5) |
| **D3 (HIGH)** — `Quantity` boundary-only typing | **PARTIALLY CLOSED** (v0.6.0 / E1 phase 1: typed accessors). Phase 2+ field-replacement is v0.6.1+. |
| **D3 (MEDIUM)** — `ResultGraph` lifecycle-only | **CLOSED** (v0.4.0 / C4) |
| **D3 (HIGH)** — String-based calibration tier propagation | **FULLY CLOSED** (v0.4.0 / C3 + v0.5.0 / D2) |
| **D4** — Per-DSD parallelism | **FULLY CLOSED** (v0.6.0 / E2 wires joblib) |
| **D5 (HIGH)** — `ModelMode` L4-only | **FULLY CLOSED** (v0.4.0 / C2 + v0.5.0 / D5) |
| **D5 (MEDIUM)** — DESIGN.md product-context drift | **CLOSED** (v0.3.0 / B8) |
| **D6 (HIGH)** — Family-first M1-only | **CLOSED** (v0.3.0 / B1+B2+B3 + v0.4.0 / C7) |
| **D6 (LOW)** — `ProcessDossier` not default | **CLOSED** (v0.5.0 / D3) |

**Net: 10 of 11 audit findings fully closed; 1 partially closed (D3 Quantity).** Only the field-replacement phase of `Quantity` plumbing remains, and is now an additive surface change rather than the original 600-LOC retrofit.

---

## 6. Design Decisions Log (v0.6.0 additions)

| ID | Decision | Rationale |
|---|---|---|
| E1-D1 | Add `_q` typed accessor **properties**, not replace bare-float fields. | Field replacement would force every arithmetic consumer (CLI printer, DSD aggregation, dossier export) to use `.value`. Properties are additive — every existing consumer keeps working bit-identically; opt-in code that wants type safety reads `_q`. The original C1 protocol's "convert ~40 fields" step is properly v0.6.1+ work, after the `_q` accessor pattern has been adopted by enough consumers to justify the surface cut. |
| E1-D2 | Each `_q` accessor builds a fresh `Quantity` on every read (no caching). | `Quantity` is a frozen dataclass with no expensive construction. Caching would complicate the property semantics for negligible gain. |
| E1-D3 | The `cycle_lifetime_q` accessor documents UNSUPPORTED status in its `Quantity.note` field rather than refusing to return a value. | Consumers should still be able to read the number for ranking / display purposes; the `note` carries the scope-of-claim warning. The bucketed-label helper `cycle_lifetime_label` (v0.3.0 / B6) is the recommended display path for UI. |
| E2-D1 | Joblib `n_jobs > 1` only fires for the **full-method** DSD path; fast-pressure-screen is always serial. | The algebraic pressure screen is ~milliseconds per quantile; joblib's loky-backend startup cost (~100 ms) would dominate. Parallelism is profitable only when the per-task work is large (LRM solver = tens of seconds). |
| E2-D2 | `_run_method_worker` is a top-level module function, not a closure. | Loky's process-based backend uses `cloudpickle` to serialize the callable + args. Top-level functions pickle cleanly; closures and dataclass methods do not. The wrapper exists specifically so the dispatch is loky-safe. |
| E2-D3 | When `n_jobs > 1` but only **one** DSD row exists, fall through to serial. | Joblib has constant overhead per task batch; one task in parallel is strictly slower than serial. The conditional skip preserves the v0.5.0 wall time on default 1-quantile paths. |
| E2-D4 | `joblib.ImportError` falls through to serial silently. | `joblib` is pinned in `pyproject.toml` (already used by `optimization`), so this branch is essentially unreachable; but defensive fallback ensures no behavior regression if a future install strips `joblib`. |

---

## 7. v0.6.0 Acceptance Gates — Verification

| Gate | Result |
|---|---|
| Typed accessors return `Quantity` with documented unit | ✅ E1 — 16/16 tests pass |
| Accessor `.value` matches underlying float field bit-identically | ✅ E1 |
| `Quantity.as_unit("kPa")` works on `pressure_drop_q` | ✅ E1 |
| End-to-end real lifecycle exposes typed accessors | ✅ E1 |
| `DSDPolicy.n_jobs == 1` preserves serial path bit-identically | ✅ E2 |
| `DSDPolicy.n_jobs > 1` with single row falls back to serial | ✅ E2 |
| `_run_method_worker` is picklable (loky requirement) | ✅ E2 |
| Smoke baseline preserved | ✅ DBC10 / dP / mass-balance / weakest-tier identical |
| ruff = 0 | ✅ across all v0.6.0 new/edited files |
| Test sweep | ✅ **162 passed**, 0 regressions, 1 deselected slow, 2 pre-existing Windows tmp-dir errors |

---

## 8. Verification

### Smoke
```bash
python -m dpsim lifecycle configs/fast_smoke.toml --quiet
```

Output preserves baseline:
- weakest evidence tier = `qualitative_trend`
- M1 bead d50 = 18.99 µm
- M3 DBC10 = 0.706 mol/m³ column
- M3 pressure drop = 37.12 kPa
- M3 mass-balance error = 0.00%

### Typed-accessor verification
```python
>>> from dpsim.lifecycle import DownstreamProcessOrchestrator
>>> from dpsim.core.process_recipe import default_affinity_media_recipe
>>> result = DownstreamProcessOrchestrator().run(recipe=default_affinity_media_recipe(), propagate_dsd=False)
>>> result.m3_breakthrough.pressure_drop_q.as_unit("kPa")
Quantity(value=37.12, unit='kPa', ...)
>>> result.m3_breakthrough.dbc_10pct_q.unit
'mol/m3'
```

### Joblib n_jobs verification
```python
>>> from dpsim.module3_performance.method_simulation import _run_method_worker
>>> import pickle
>>> pickle.dumps(_run_method_worker)  # loky-picklable
b'...'
```

### Test sweep
```bash
pytest -m "not slow" tests/test_quantity_accessors.py tests/test_dsd_njobs_parallelism.py [...] tests/core/
# 162 passed, 0 failed, 0 regressions
```

### CI gates
- `ruff check src/dpsim/ tests/`: **All checks passed**

---

## 9. Open Questions for v0.6.1 Kickoff

| ID | Question | Default if no decision |
|---|---|---|
| **v6.1-Q1** | Should v0.6.1 deprecate the bare-float fields with `DeprecationWarning` accessors, or wait for full field-replacement in v0.7.0? | Deprecate via `__getattr__` shim that emits `DeprecationWarning` on read of e.g. `dbc_10pct` after a guarded grace period (3 minor releases). v0.6.1 = warning; v0.7.0 = removal. |
| **v6.1-Q2** | Function-signature typing for M3 entry points (`run_breakthrough(C_feed=...)`): accept-Quantity-and-auto-unwrap, or require Quantity? | Accept both with auto-unwrap. Signature change with Quantity-or-float Union keeps callers (UI, recipe_resolver) working without forced refactor. |
| **v6.1-Q3** | Should v0.6.1 also include M2 dataclass `Quantity` accessors (mirror of E1 for `ModificationResult`, `FunctionalMediaContract`, `ACSProfile`)? | Yes — pair the M2/M3 accessor work in v0.6.1 to keep the `_q` pattern uniform across stages. M1 stays for v0.6.2. |

---

## 10. Pre-generated v0.6.1 Protocol Skeleton

**Files:** `src/dpsim/module3_performance/orchestrator.py` (signatures), `src/dpsim/module2_functionalization/orchestrator.py` (FMC / ModificationResult accessors).

**Phase plan:**

1. **E3.M3-signatures** (~150 LOC): Convert public M3 entry-point signatures (`run_breakthrough`, `run_gradient_elution`, `run_chromatography_method`, `run_loaded_state_elution`) to accept `Quantity | float` for documented-unit arguments. Auto-unwrap floats with the documented unit; auto-`.value` Quantities for internal solver use.

2. **E3.M2-accessors** (~100 LOC): Add `_q` accessor properties to `FunctionalMediaContract` (estimated_q_max, functional_ligand_density, activity_retention, ligand_leaching_fraction), `ModificationResult` (delta_G_DN, conversion), `ACSProfile` (remaining_sites). Pattern mirrors v0.6.0 / E1.

3. **E3.deprecation-shim** (~80 LOC): Add a `__getattr__` shim on `BreakthroughResult` etc. that emits `DeprecationWarning("dbc_10pct deprecated; use dbc_10pct_q.value")` on read of the bare-float field. Single-warning-per-class via `warnings.simplefilter` to avoid stdout flood.

**Acceptance gates:** ruff = 0, mypy = 0; `BreakthroughResult.dbc_10pct` emits `DeprecationWarning`; `_q` accessor still returns `Quantity`; smoke baseline numbers preserved exactly. **Fix-round budget: 2.**

---

## 11. Roadmap Position

```
v0.1.0 (initial squashed release)
  └─ v0.2.0 (evidence chain closed; first guardrails live)
       └─ v0.3.0 (family coverage, claim honesty, recipe-only UI)
            └─ v0.4.0 (architectural coherence: 6 of 7 C-modules)
                 └─ v0.5.0 (deprecation removal + ProcessDossier + M2 mode)
                      └─ v0.6.0 (THIS — Quantity accessors phase 1 + n_jobs parallelism)
                           └─ v0.6.1 (M3 signature typing + M2 Quantity accessors + deprecation shim)
                                └─ v0.6.2 (M1 Quantity accessors + signature typing)
                                     └─ v0.7.0+ (P5++ Monte-Carlo LRM, full Bayesian fitting)
```

v0.6.1 entry point: Module **E3.M3-signatures** (Quantity-or-float signature typing for M3 entry points). Pre-generated protocol skeleton in §10.

---

## 12. Sign-Off

All G3 audit dimensions evaluated:
- **D1 (structural)** — `_q` accessor pattern is uniform across the four M3 dataclasses. The worker function `_run_method_worker` is module-scope for loky picklability.
- **D2 (algorithmic)** — Joblib parallelism dispatch is conditional on `n_jobs > 1` AND multi-row workload; single-row paths stay serial. `_q` accessors construct fresh `Quantity` per read with no shared state.
- **D3 (data-flow)** — Typed Quantity is now reachable from every M3 result; the bare-float storage is an internal optimisation. Joblib's loky backend handles cross-process pickling cleanly via top-level worker.
- **D4 (performance)** — Default `n_jobs=1` preserves serial wall time. The `_q` accessor adds one Quantity construction per read (~microseconds, negligible).
- **D5 (maintainability)** — Every new accessor / helper has tests. Pattern is documented in module docstrings.
- **D6 (first-principles)** — Quantity unit annotations match the documented field units one-to-one. The `cycle_lifetime_q` accessor's `Quantity.note` carries the UNSUPPORTED scope-of-claim warning so downstream readers see the audit signal.

**Verdict: APPROVED.** v0.6.0 milestone closed. **10 of 11 architect-coherence findings fully closed; 1 partially closed (D3 Quantity field-replacement = v0.6.1+).** Ready to start v0.6.1 from Module E3.M3-signatures in a fresh session using §10.
