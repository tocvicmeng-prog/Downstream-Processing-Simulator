# /architect Protocol — P5++ Monte-Carlo LRM Uncertainty Propagation (DPSim v0.7.0)

**Author:** Architect (scoping doc)
**Date:** 2026-04-25
**Status:** **PLANNING ONLY** — no implementation in v0.6.x. This document is the
G1 readiness skeleton for a v0.7.0 milestone that needs its own dedicated session
and a full /scientific-advisor brief before any code lands.

---

## 0. Pre-Flight Check (Phase 0)

### 0.1 Why a separate milestone

P5++ is the only remaining open item from the architect-coherence audit and
sci-advisor §5 deliverables that has **NOT** been implemented across v0.2 → v0.6.
Every other deficit has been closed. P5++ is structurally different from the
v0.2–v0.6 modules:

| Dimension | v0.2–v0.6 modules (typical) | P5++ |
|---|---|---|
| LOC estimate | ~50–250 | ~800–1500 |
| Wall-time per run | seconds | hours per Monte-Carlo realisation set |
| Scientific novelty | architectural cleanup | new numerical method |
| Calibration data needed | none (uses existing posteriors) | full Bayesian inference may need new wet-lab data |
| Fit-for-purpose validation | smoke baseline | requires statistical convergence diagnostics |
| Sessions estimated | 1 each | 3–5 sessions; multi-week wall time |

P5++ is therefore properly scheduled as **v0.7.0 alone** — not bundled with
architectural cleanup. The dev-orchestrator framework's pre-flight check
(Reference 07 §2) recommends compression + a fresh session for any module
above 8000 tokens of inner-loop spend; P5++ is an order of magnitude above that.

### 0.2 Upstream dependencies (confirmed in place)

All P5++ prerequisites land in v0.5.0 / v0.6.0:

| Prerequisite | Where it ships | Status |
|---|---|---|
| Typed-enum tier promotion through calibration store | v0.4.0 / C3 | ✅ |
| `model_manifest.evidence_tier` is the single source of truth | v0.5.0 / D2 | ✅ |
| First-order delta-method posteriors for q_max, K_affinity, pressure-flow | v0.4.0 / C6 + pre-existing P5+ | ✅ |
| pH_transition / pH_steepness posterior diagnostics | v0.4.0 / C6 | ✅ |
| Joblib `n_jobs` parallelism for per-quantile method runs | v0.6.0 / E2 | ✅ |
| `Quantity`-typed accessors for solver result fields | v0.6.0 / E1 + v0.6.1 / F2 + v0.6.2 / F4 | ✅ |
| `unwrap_to_unit` helper for entry-point Quantity-or-float input | v0.6.1 / F1 | ✅ |
| ProcessDossier as default lifecycle output | v0.5.0 / D3 | ✅ |
| `ResultGraph.register_result` for sub-step provenance | v0.4.0 / C4 | ✅ |
| Bin-resolved DSD propagation | v0.4.0 / C5 | ✅ |
| Family-aware Protein A scope-of-claim guard | v0.4.0 / C7 | ✅ |
| `ModelMode` enforcement in M2 + M3 | v0.4.0 / C2 + v0.5.0 / D5 | ✅ |

### 0.3 Model-tier selection (informational — not invoked here)

| P5++ task | Tier | Rationale |
|---|---|---|
| Architecture protocol (this doc + the v0.7.0 protocol) | Opus | Non-negotiable per Reference 07 §3.2 |
| Monte-Carlo loop driver implementation | Sonnet (or Opus if novel sampler) | Standard implementation if the sampler is off-the-shelf (e.g. NUTS / HMC from `pymc`); Opus if a custom adjoint or surrogate is required. |
| Scientific Advisor consultation on proposal distribution / convergence diagnostics | Opus | Sci-advisor escalation is the primary use of Opus tier. |
| Convergence-diagnostic implementation (R-hat, effective sample size, posterior overlap) | Sonnet | Standard scientific code with an established library footprint. |
| Tests + statistical validation | Sonnet | Numerical/scientific validation per Reference 07 §3.2. |

---

## 1. Requirements

### 1.1 Problem Statement

Today's M3 calibration uncertainty layer (P5+, shipped before v0.2.0) emits
**first-order delta-method screening intervals** for q_max, K_affinity,
pressure-flow reference, and (after v0.4.0 / C6) ProteinA pH_transition +
pH_steepness. The intervals are honest screening signals but they:

1. Assume **local linearity** of the LRM solver around each posterior mean —
   acceptable for q_max / K_affinity-bounded capacity claims, but increasingly
   wrong for elution-recovery sensitivity to pH_transition / pH_steepness
   (the sigmoid is highly non-linear at the elution pH).
2. Assume **independent posteriors** — they sum quadrature errors, missing the
   correlation structure that calibration data actually carries (e.g. q_max and
   K_affinity are typically negatively correlated when fit jointly to a static
   binding curve).
3. Do **not** propagate through the LRM trajectory itself — the posterior
   width on DBC is a static delta-method extrapolation, not a re-solve of the
   LRM at sampled parameter values.
4. Cannot quantify **breakthrough-curve uncertainty bands** — only point
   intervals on summary scalars.

P5++ replaces this with:
1. A **Monte-Carlo loop** that draws N samples from the joint posterior
   (correlation-preserving when the calibration store carries a covariance
   matrix; falls back to independent quadrature when only marginals are
   available).
2. Per-sample **re-solution of the LRM** (parallelised via `joblib.n_jobs`
   from v0.6.0 / E2).
3. Posterior **bands on the entire breakthrough curve** + scalar summary
   quantiles (P5, P50, P95) on DBC, recovery, cycle-life.
4. **Convergence diagnostics** so the user knows when N is large enough.
5. Optional **full Bayesian fitting** (HMC/NUTS via `pymc` or similar) for
   users who have raw assay data and want to refit posteriors before MC
   propagation.

### 1.2 Goals (MoSCoW)

| Priority | Requirement |
|---|---|
| **Must** | Monte-Carlo LRM driver: draw N samples from a posterior, re-solve LRM at each, aggregate to scalar quantiles + curve bands. |
| **Must** | Joint-posterior support: accept either a covariance matrix or marginal posteriors; correctness-checked against the existing P5+ delta-method on the marginal-only path. |
| **Must** | Convergence diagnostics: R-hat (when chains > 1), effective sample size, posterior interval stability check. |
| **Must** | Joblib parallelism: per-sample LRM solves dispatched via `n_jobs > 1` (uses the v0.6.0 / E2 infrastructure). |
| **Must** | Result schema: extend `MethodSimulationResult` with a new `monte_carlo: MCBands | None` field (default None; populated only when `recipe.dsd_policy.monte_carlo_n_samples > 0`). |
| **Must** | Smoke baseline preservation: when MC is not requested, the existing P5+ delta-method screening interval is unchanged bit-identically. |
| **Should** | Full Bayesian fitting: a new `dpsim.calibration.bayesian_fit` module that takes raw assay records and fits joint posteriors via HMC/NUTS. |
| **Should** | Posterior-band UI rendering: extend the M3 result panel in `tab_m3.py` to show breakthrough curve bands. |
| **Should** | ProcessDossier export of MC results: serialize the posterior bands (compressed) into the dossier's JSON output. |
| **Could** | Adjoint-based variance propagation as a fast approximation when MC is too expensive. |
| **Won't** | Real-time Bayesian updating during a wet-lab run (digital-twin live mode). |

### 1.3 Acceptance Criteria

1. With `MC_N=1000`, posterior P05/P50/P95 bands on DBC10 must satisfy
   `|MC_P50 - delta_method_mean| < 1 % * delta_method_mean` for the linear-regime
   smoke baseline (q_max σ = 10%, K_affinity σ = 10%, no shape-parameter
   posteriors).
2. With pH_transition σ = 0.5 and pH_steepness σ = 1.0 — a regime where the
   delta method is known to be wrong — MC and delta-method must **disagree** by
   ≥ 5% on elution recovery, with MC being the accepted answer.
3. R-hat < 1.05 across 4 independent MC seeds for N=1000 samples.
4. Wall-time scaling: parallel MC at `n_jobs=8` should complete N=1000 samples
   within 5× the serial wall-time of one LRM solve.
5. ruff = 0, mypy = 0; pre-existing tests unchanged; ≥30 new tests covering the
   MC driver, convergence diagnostics, and the joint-vs-marginal posterior
   contract.

---

## 2. Architecture (sketched only — full design is v0.7.0 work)

```
ProcessRecipe + DSDPolicy (with monte_carlo_n_samples > 0)
        │
        ▼
PosteriorSamples
  ├─ from CalibrationStore (existing posteriors)
  └─ from BayesianFit (optional new module)
        │
        ▼
[joblib.Parallel n_jobs] for s in samples:
        ├─ apply_to_fmc(sample s)
        ├─ apply mode_guard / family_guard
        ├─ run_chromatography_method (with re-sampled isotherm)
        └─ collect (load_breakthrough.dbc_10pct, .C_outlet, ...)
        │
        ▼
MCBands
  ├─ scalar_quantiles: dict[str, dict[str, float]]   # "dbc_10pct": {"p05": ..., "p50": ..., "p95": ...}
  ├─ curve_bands: dict[str, np.ndarray]              # "C_outlet_p50": (N_t,), "C_outlet_p05": (N_t,), ...
  ├─ rhat: dict[str, float]                          # convergence per metric
  ├─ effective_sample_size: dict[str, float]
  ├─ n_samples: int
  └─ model_manifest: ModelManifest                   # tier inherits weakest across MC samples
        │
        ▼
MethodSimulationResult.monte_carlo (NEW field)
```

### 2.1 Module Decomposition (5 modules)

| # | Module | Tier | LOC est. |
|---|---|---|---|
| **G1** | `dpsim.calibration.posterior_samples` — joint/marginal posterior representation + sampler | Sonnet | ~250 |
| **G2** | `dpsim.module3_performance.monte_carlo` — MC LRM driver + MCBands aggregator + convergence diagnostics | Opus protocol + Sonnet impl | ~400 |
| **G3** | `MethodSimulationResult.monte_carlo` field + `run_method_simulation` MC dispatch | Sonnet | ~150 |
| **G4** | `dpsim.calibration.bayesian_fit` — optional HMC/NUTS fitting via pymc | Opus protocol + Sonnet impl | ~300 |
| **G5** | UI band-rendering in `tab_m3.py` + ProcessDossier MC serialization | Sonnet | ~200 |

**Total v0.7.0 LOC estimate: ~1300 + ~500 tests = ~1800 net LOC**.

### 2.2 Critical Path

G1 → G2 → G3. G4 and G5 are independent of the critical path and can land
in v0.7.1 / v0.7.2 if v0.7.0 scope-bounds at the MC driver.

---

## 3. Risk Register (top 5)

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Wall-time blowup: N=1000 × 6 quantiles × 30 s per LRM = 50 hours serial | High | High | `n_jobs=8` parallelism (E2 already shipped) brings this to ~6 hours; smaller N=100 default keeps the lifecycle smoke under 1 hour even without parallelism. |
| R2 | `pymc` / HMC dependency adds a heavy install footprint | Medium | Medium | Make G4 (Bayesian fit) optional — `pip install dpsim[bayesian]` extra. The MC driver (G1+G2+G3) must work with only the pre-existing posteriors. |
| R3 | Posterior covariance is rarely available in real calibration data | High | Medium | Default to marginal-only posteriors (matches the existing P5+ contract); document covariance as a future enhancement when calibration ingest grows. |
| R4 | Smoke baseline drift if MC default activates inadvertently | Medium | High | Default `monte_carlo_n_samples=0` — MC only fires on explicit opt-in. Mirrors the v0.4.0 / C5 `dsd_mode="bin_resolved"` pattern. |
| R5 | Convergence-diagnostic false negatives (R-hat passes when sampler is biased) | Medium | High | Require **at least 4 independent seeds** when MC is invoked. Add an additional "posterior overlap" check that compares P50 between seed groups. |

---

## 4. Open Questions for v0.7.0 Kickoff

| ID | Question | Default if no decision |
|---|---|---|
| **v7-Q1** | Should v0.7.0 ship the optional Bayesian fitting (G4) or scope to MC driver only? | MC driver only. G4 = v0.7.1 alone. |
| **v7-Q2** | Default `monte_carlo_n_samples` when user opts in? | 200. R1 cost analysis says 200 × 30 s × 3 quantiles = 5 hours serial / 40 minutes at n_jobs=8. |
| **v7-Q3** | Should MC support the bin-resolved DSD path (v0.4.0 / C5)? Cost = O(N × bins × LRM_solve), potentially 100× more expensive than 3-quantile MC. | No for v0.7.0. MC + 3-quantile is the v0.7.0 contract; MC + bin-resolved is v0.8.0+. |
| **v7-Q4** | Posterior representation: a list of sample dicts, or a `PosteriorSamples` dataclass with a `numpy.ndarray` + parameter-name index? | Dataclass with ndarray. ndarray supports vectorised quantile computation; sample-dicts force per-sample loops. |

---

## 5. G1 Readiness Check (Architect's Self-Audit — Phase 0 Output)

| # | Criterion | Pass? | Note |
|---|---|---|---|
| G1-01 | Problem statement and goals captured | ✅ | §1.1 + §1.2 |
| G1-02 | MoSCoW prioritisation present | ✅ | §1.2 |
| G1-03 | Acceptance criteria measurable | ✅ | §1.3 |
| G1-04 | Module decomposition present | ✅ | §2.1 |
| G1-05 | Upstream dependencies APPROVED | ✅ | §0.2 — all 12 prerequisites green |
| G1-06 | Data contracts described at type level | ✅ | §2 (MCBands schema) — full field-level spec is v0.7.0 work |
| G1-07 | Algorithm complexity stated | ✅ | §3 R1 |
| G1-08 | Numerical-stability considerations identified | ⚠️ Partial | Sigmoid non-linearity flagged (§1.1 #1); convergence diagnostics required (§1.2 Must). Full numerical-method choice is v0.7.0 work. |
| G1-09 | Test plan covers happy path + edge cases | ⚠️ Partial | Listed at §1.3; full per-module test inventory is v0.7.0 work. |
| G1-10 | Model-tier selection per module | ✅ | §0.3 |
| G1-11 | Backward-compatibility statement | ✅ | §3 R4 — default off, smoke unchanged |
| G1-12 | Risk register present | ✅ | §3 |

**Verdict: G1 = PARTIAL PASS (10/12).** Sufficient for **planning** purposes —
the v0.7.0 milestone has a clear scope, dependencies, and acceptance gate. Two
items (G1-08 numerical-stability, G1-09 test inventory) are deliberately
deferred to the v0.7.0 protocol session because they require:

- A /scientific-advisor brief on the LRM solver's numerical regime under
  random parameter draws (the BDF solver may need tighter tolerances when
  k_ads or K_affinity are sampled at the tail of their posteriors).
- A full per-module test inventory that depends on the chosen MC sampler
  (off-the-shelf `pymc` vs custom adjoint).

Both are properly v0.7.0 design decisions, not v0.6.x scoping decisions.

---

## 6. Roadmap Forward

```
v0.6.0 → v0.6.1 → v0.6.2 (THIS SESSION — Quantity accessors + signature typing)
  └─ v0.7.0 (P5++ MC driver — G1+G2+G3 modules above)
       └─ v0.7.1 (P5++ Bayesian fitting — G4)
            └─ v0.7.2 (P5++ UI band rendering + dossier serialization — G5)
                 └─ v0.8.0+ (MC + bin-resolved DSD; digital-twin live mode)
```

---

## 7. What Happens Next

1. **Park this document under `docs/p5_plus_plus_protocol.md`** for fresh-session pickup.
2. **Do not start G1 implementation in v0.6.x.** This is the v0.7.0 entry point.
3. When v0.7.0 begins, the architect should:
   a. Re-validate §0.2 dependencies (refresh the table against current state).
   b. Re-run G1 with the full §G1-08 / G1-09 details once /scientific-advisor has been briefed.
   c. Pick the sampler (off-the-shelf vs custom).
   d. Generate per-module protocols for G1, G2, G3 (G4 / G5 in subsequent milestones).

---

## 8. Disclaimer

> This protocol is informational and architectural only. P5++ involves new
> numerical methods (Monte-Carlo over a stiff ODE solver, Bayesian inference
> on calibration posteriors) whose convergence and accuracy must be validated
> against synthetic ground truth and real assay data before any production
> use. The architecture above is a planning skeleton — full G1 readiness for
> implementation requires the additional /scientific-advisor brief noted in
> §5 G1-08 and the per-module test inventory noted in §5 G1-09.
