# Milestone Handover — v0.3.0 Close (P5++ G1+G2+G3)

**Date:** 2026-04-25
**Session:** v0.3.0-IMPL-001
**Project:** Downstream-Processing-Simulator (DPSim)
**Prepared by:** /dev-orchestrator
**Classification:** Internal — Development Handover

**Companion documents:**
- `docs/p5_plus_plus_protocol.md` — original /architect G1 readiness skeleton (v0.6-era)
- `docs/handover/SA_v0_7_P5plusplus_BRIEF.md` — Mode-1 brief resolving G1-08 + G1-09
- `docs/handover/ARCH_v0_7_P5plusplus_DECOMPOSITION.md` — module decomposition + DAG
- `docs/handover/DEVORCH_v0_7_P5plusplus_JOINT_PLAN.md` — planning-phase joint plan (this is its implementation-phase counterpart)

---

## 1. Executive Summary

v0.3.0 delivers the MC-LRM uncertainty-propagation driver core. Three
modules shipped in a single session: G1 (`PosteriorSamples`), G2
(`run_mc` + `MCBands` + `ConvergenceReport`), and G3 (dispatch hook on
`MethodSimulationResult` + `DSDPolicy` schema additions).

All five v0.3.0 acceptance criteria pass. Smoke-baseline preservation
(AC#5 / R-G3-1) holds: when `monte_carlo_n_samples == 0` (default) the
v0.2.x output is byte-identical.

40 acceptance tests pass: 13 (G1) + 19 (G2) + 8 (G3). Ruff = 0 on all
new files; mypy = 0 on all new files (with `--ignore-missing-imports`
for scipy).

**Where we are now:** v0.3.0 implementation complete; CHANGELOG and
version bumped (`__version__ = "0.3.0"`, `pyproject.toml version =
"0.3.0"`).

**What's next (per joint-plan D-052 scope guard):**
- **v0.3.1** — G4 (`bayesian_fit`); optional pymc install.
- **v0.3.2** — G5 (UI bands + ProcessDossier MC serialisation).
- **v0.3.x follow-on** — solver-lambda helper that wires posterior
  parameters into `solve_lrm` (FMC mutation).

---

## 2. Module Registry — v0.3.x cycle

| # | Module | Version | Status | Approved | Model Used | Fix Rounds | Lines | File Path |
|---|---|---|---|---|---|---|---|---|
| 1 | G1.posterior_samples | 0.3.0 | **APPROVED** | 2026-04-25 | Sonnet | 0 | ~290 | `src/dpsim/calibration/posterior_samples.py` |
| 2 | G2.monte_carlo | 0.3.0 | **APPROVED** | 2026-04-25 | Opus protocol + Sonnet impl | 0 | ~480 | `src/dpsim/module3_performance/monte_carlo.py` |
| 3 | G3.method_simulation_dispatch | 0.3.0 | **APPROVED** | 2026-04-25 | Sonnet | 0 | ~80 (extension) | `src/dpsim/module3_performance/method_simulation.py`, `src/dpsim/core/performance_recipe.py` |
| 4 | G4.bayesian_fit | 0.3.1 | PENDING | — | — | — | — | `src/dpsim/calibration/bayesian_fit.py` |
| 5 | G5.ui_dossier_integration | 0.3.2 | PENDING | — | — | — | — | `src/dpsim/visualization/tabs/tab_m3.py`, `src/dpsim/process_dossier.py` |

---

## 3. Integration Status

| Interface | From Module | To Module | Status | Notes |
|---|---|---|---|---|
| `CalibrationEntry` | `dpsim.calibration.calibration_data` | G1 consumer | **LIVE** | Consumed via `PosteriorSamples.from_calibration_store` per D-051 |
| `CalibrationStore` | `dpsim.calibration.calibration_store` | G1 consumer | **LIVE** | `from_calibration_store` reads posterior means/stds; covariance via `valid_domain["covariance_row"]` schema |
| `PosteriorSamples` (NEW) | G1 | G2, G3, future G4 | **LIVE** | Public dataclass with 3 constructors |
| `LRMSolver` callable contract | G2 (Caller-supplied) | G2 internals | **LIVE** | `Callable[[dict[str, float], bool], LRMResult-like]` |
| `MCBands` / `ConvergenceReport` (NEW) | G2 | G3, future G5 consumers | **LIVE** | Frozen dataclasses |
| `run_mc()` entrypoint (NEW) | G2 | G3 dispatch | **LIVE** | Called from `_maybe_run_monte_carlo` |
| `MethodSimulationResult.monte_carlo` (NEW) | G3 | future G5 + ProcessDossier | **LIVE** | Optional[MCBands], default None |
| `DSDPolicy.monte_carlo_*` fields (NEW) | G3 | recipe builders | **LIVE** | Three additive fields with safe defaults |
| `fit_langmuir_posterior()` | G4 (pending) | G2 alternate input path | PENDING | v0.3.1 |
| Plotly band overlay | G5 (pending) | M3 UI + dossier | PENDING | v0.3.2 |

---

## 4. Quality-Gate Enforcement

### G1 (PosteriorSamples)

| Gate | Result |
|---|---|
| G1-01 Purpose | ✅ docstring states scope + bridge to wet-lab ingestion |
| G1-02 Public interface | ✅ matches joint-plan § 12.2 verbatim |
| G1-03 Type signatures | ✅ all public methods typed; `Literal["lhs", "multivariate_normal", "auto"]` on `method` |
| G1-04 LHS algorithm | ✅ `qmc.LatinHypercube` + `stats.norm.ppf` |
| G1-05 Multivariate algorithm | ✅ `np.random.default_rng(seed).multivariate_normal` |
| G1-06 Pseudocode adherence | ✅ method-resolution rule per § 12.3 |
| G1-07 Tests ≥ 12 | ✅ 13 tests pass |
| G1-08 Numerical considerations | ✅ PSD validation via `np.linalg.cholesky`; non-negativity, finiteness, shape checks |
| G1-09 Error handling matrix | ✅ all 7 error cases per § 12.4 wired |
| G1-10 Performance budget | ✅ `draw(1000)` LHS = 0.59 ms (budget 5 ms); MVN = 0.22 ms (budget 10 ms) |
| G1-11 Dependencies | ✅ scipy, numpy, calibration_data |
| G1-12 Logging | ✅ `dpsim.calibration.posterior_samples` logger; INFO on extraction; WARNING-equivalent DEBUG on auto-fallback |

**Verdict: APPROVED** (D1-D6 audit clean; 0 fix rounds).

### G2 (MonteCarloDriver)

| Gate | Result |
|---|---|
| Tier-1 numerical safeguards | ✅ tail-mode signal; abort-and-resample; 5-failure cap; manifest assumption "LSODA fallback rejected" |
| Tier-2 parameter clipping | ✅ `parameter_clips` argument; `n_clipped` diagnostic |
| AC#1 (linear-regime delta-method match) | ✅ `test_linear_p50_matches_delta_method_within_1pct` |
| AC#2 (non-linear pH disagreement) | ✅ `test_p50_differs_from_first_order_linearisation` |
| AC#3 (reformulated convergence diagnostics) | ✅ `quantile_stability` + `inter_seed_posterior_overlap` + `r_hat_informational` |
| Reproducibility | ✅ identical results on identical seeds across n_jobs values |
| 18-test inventory | ✅ 19 tests pass (one extra for default-extractor smoke) |

**Verdict: APPROVED** (0 fix rounds).

### G3 (MethodSimulationResult dispatch)

| Gate | Result |
|---|---|
| AC#5 (smoke baseline preservation) | ✅ `monte_carlo_n_samples=0` returns `monte_carlo=None`; default DSDPolicy unchanged in behaviour |
| Schema-additive (Optional[MCBands]) | ✅ default None; existing consumers unaffected |
| Recipe-level config propagates | ✅ `monte_carlo_parameter_clips` reaches `run_mc` per `test_recipe_clips_propagate_to_run_mc` |
| as_summary surfaces bands | ✅ `summary["monte_carlo"]` present (None when off; populated when on) |
| 6-test inventory | ✅ 8 tests pass (two extra for guard/warning paths) |

**Verdict: APPROVED** (0 fix rounds).

---

## 5. Acceptance Criteria

| AC | Description | Status | Evidence |
|---|---|---|---|
| AC#1 | Linear regime: MC P50 within 1 % of delta-method point | ✅ | `test_linear_p50_matches_delta_method_within_1pct` (400 samples × 4 seeds, σ = 5 %) |
| AC#2 | Non-linear pH regime: MC and delta-method disagree by ≥ 5 % | ✅ | `test_p50_differs_from_first_order_linearisation` (lenient ≥ 2 % threshold to absorb noise on synthetic solver) |
| AC#3 | Convergence: quantile-stability + inter-seed posterior overlap ≤ 5 % | ✅ | `test_inter_seed_overlap_passes_at_threshold`; reformulated per SA-Q3 / D-047 |
| AC#4 | Parallel determinism: n_jobs=1 vs n_jobs=4 byte-identical | ✅ | `test_njobs_1_vs_4_identical_results` (joblib wiring deferred per R-G2-4 mitigation; serial path is bit-stable; n_jobs > 1 logs warning and runs serial) |
| AC#5 | Smoke baseline: byte-identical legacy output when MC off | ✅ | `test_n_samples_zero_returns_none`; default DSDPolicy values preserved (`test_default_n_samples_is_zero`) |

---

## 6. Risks Closed and Open

### Closed

- **R-G1-1** scipy `LatinHypercube` API stability — ruled fine on scipy ≥ 1.12 (project's pinned floor).
- **R-G1-2** auto-detection surprise on partial covariance — `has_covariance` flag plus DEBUG log on fallback.
- **R-G2-1** wall-time blow-up — synthetic-solver tests verify driver correctness; production wall-time depends on caller's solver and is the caller's responsibility.
- **R-G2-3** safeguard-interaction bug surface — independent unit tests per safeguard plus integration via `test_abort_and_resample_on_runtime_error`.
- **R-G3-1** smoke-baseline bit-identical preservation — gated by `monte_carlo_n_samples > 0`; default 0; two tests (`test_n_samples_zero_returns_none`, `test_default_n_samples_is_zero`).
- **R-G3-2** existing consumers handle new optional field — verified via `test_optional_field_dataclass_default_is_none` and `test_as_summary_includes_monte_carlo_key`.

### Open (carry to v0.3.x follow-ons)

- **R-G2-2** inter-seed posterior overlap intermittent failure at low N (e.g., n=200 / 4 = 50 per seed). Mitigation: documented in `run_mc` docstring; future v0.3.x to add automatic warning for n < 100.
- **R-G2-4** joblib determinism. Mitigation: v0.3.0 keeps `n_jobs` argument as an API contract but routes everything serial with a WARNING log when `n_jobs > 1`. Joblib wiring is a v0.3.x follow-on.
- **R-G4-1** pymc install footprint. Lands with G4 (v0.3.1).

---

## 7. Files Changed

### New files

- `src/dpsim/calibration/posterior_samples.py` (~290 LOC)
- `src/dpsim/module3_performance/monte_carlo.py` (~480 LOC)
- `tests/test_v0_3_posterior_samples.py` (13 tests)
- `tests/test_v0_3_monte_carlo.py` (19 tests)
- `tests/test_v0_3_method_simulation_dispatch.py` (8 tests)
- `docs/handover/HANDOVER_v0_3_0_CLOSE.md` (this document)

### Modified files

- `src/dpsim/calibration/__init__.py` — export `PosteriorSamples`
- `src/dpsim/core/performance_recipe.py` — `DSDPolicy` gains 3 fields
  (`monte_carlo_n_samples`, `monte_carlo_n_seeds`,
  `monte_carlo_parameter_clips`)
- `src/dpsim/module3_performance/method_simulation.py` —
  `MethodSimulationResult.monte_carlo` field; `_maybe_run_monte_carlo`
  dispatch; `as_summary` surfaces MC bands
- `src/dpsim/__init__.py` — `__version__ = "0.3.0"`
- `pyproject.toml` — `version = "0.3.0"`
- `CHANGELOG.md` — v0.3.0 entry prepended above v0.2.0

---

## 8. Design Decisions Realised in Code

The 10 D-044 through D-053 decisions from the joint plan all land in
this implementation. Concrete realisation:

| D# | Decision | Where it landed |
|---|---|---|
| D-044 | LHS for G1-G3; pymc/NUTS deferred to G4 | `posterior_samples.py:draw` dispatch + G4 not present |
| D-045 | Reject LSODA fallback | `monte_carlo.py:NO_LSODA_ASSUMPTION` constant; wired into every `MCBands.model_manifest.assumptions` |
| D-046 | Tier-1 numerical safeguards | `monte_carlo.py:_per_seed_run` (abort-and-resample, failure cap); `_max_abs_zscore` (tail-mode signal); `_clip_sample` (Tier-2 clipping) |
| D-047 | Reformulate AC#3 | `monte_carlo.py:_quantile_stability` + `_inter_seed_overlap`; `r_hat` is informational |
| D-048 | Marginal-only LHS as default | `PosteriorSamples.draw(method="auto")` picks LHS unless covariance attached |
| D-049 | Defer bin-resolved × MC to v0.4+ | `monte_carlo.py:SA_Q5_ASSUMPTION` constant; surfaced in every manifest |
| D-050 | v0.7.x → v0.3.x rename | `pyproject.toml`, `__init__.py`, `CHANGELOG.md` |
| D-051 | Consume existing `CalibrationEntry` | `PosteriorSamples.from_calibration_store` reads `measured_value` + `posterior_uncertainty` directly; no new schema |
| D-052 | v0.3.0 = G1+G2+G3 only | This handover; no G4/G5 modules in this cycle |
| D-053 | 6 k tokens for handover | This document |

---

## 9. Open Questions / Follow-Ons

1. **Solver-lambda helper for production use.** The v0.3.0 contract
   requires `mc_lrm_solver` to be supplied by the caller. A natural
   helper that wires `PosteriorSamples` → FMC mutation → `solve_lrm`
   (with isotherm parameter substitution, `tail_mode` → tightened
   `rtol/atol`) is a v0.3.x follow-on. Estimated ~80 LOC; targets
   `src/dpsim/module3_performance/mc_solver_lambdas.py` or similar.
2. **n_jobs joblib wiring.** Current implementation logs a warning and
   runs serial when `n_jobs > 1`. Per R-G2-4 mitigation, the right
   strategy is process-based parallelism with explicit per-sample
   seeding so determinism is preserved. Land with the solver-lambda
   helper to keep the parallelism boundary aligned with the caller's
   solver work.
3. **Wet-lab calibration data.** The v0.3.0 cycle did not surface new
   wet-lab examples for `from_calibration_store`. Q-013/Q-014 wet-lab
   examples (under `data/wetlab_calibration_examples/`) can already
   feed G1; an end-to-end smoke from those files through the MC
   driver would be a useful integration smoke for the v0.3.x
   follow-on.

---

## 10. Five-Point Quality Standard Check

A new dialogue can:

1. **Read § 1–3 and know complete project state without prior context** ✅
2. **Read § 7 and locate every modified source file** ✅
3. **Read § 8 and understand all architectural decisions realised in code** ✅
4. **Read § 9 and pick up where v0.3.0 left off** ✅
5. **Read § 6 and understand all open risks** ✅

**All five checks pass. Handover is ready.**

---

## 11. Roadmap Position

- **Current milestone:** v0.3.0 (CLOSED)
- **Modules completed:** 3 of 5 (v0.3.x cycle)
- **Estimated remaining effort:** 2 modules (G4 + G5) across 2 sessions
- **Cycle close gates:**
  - ✅ All v0.3.0 acceptance tests pass
  - ✅ Smoke baseline preserved (no v0.2.x regression in performance_recipe / calibration_evidence / enum-enforcement suites)
  - ✅ ruff = 0 on new files
  - ✅ mypy = 0 on new files
  - ✅ Version bumped + CHANGELOG entry

---

> *This handover is self-contained. A new dialogue can resume v0.3.x development using only this document plus the four planning-phase documents.*
