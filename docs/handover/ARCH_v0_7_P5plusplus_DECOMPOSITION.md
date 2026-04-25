# Architect — v0.3.x P5++ Monte-Carlo LRM Uncertainty Propagation: Module Decomposition

**Document ID:** ARCH-v0.3-P5plusplus-001
**Date:** 2026-04-25
**Author role:** Architect (within dev-orchestrator framework)
**Companion documents:**
- `docs/p5_plus_plus_protocol.md` — original G1 readiness skeleton (PARTIAL PASS 10/12)
- `docs/handover/SA_v0_7_P5plusplus_BRIEF.md` — Mode-1 brief resolving G1-08 + G1-09 (12/12 FULL PASS)

**Scope:** Decompose the P5++ initiative into 5 implementation modules across 3 milestones (v0.3.0 / v0.3.1 / v0.3.2). Provide module identity, file path, responsibility, model tier per Reference 02, acceptance criteria per milestone, dependency DAG, and orchestrator handoff notes.

**Coding rules in force (`CLAUDE.md`):** Python pinned `>=3.11,<3.13` per ADR-001; ruff = 0; mypy = 0; Streamlit reload-safe enum comparison via `.value` (now AST-enforced via `tests/test_v9_3_enum_comparison_enforcement.py`); Windows cp1252 stdout pitfall on `print(Path)`.

---

## 0. Phase 0 — Pre-flight

### 0.1 Why this is a separate cycle

P5++ is structurally different from the v0.2.0 functional-optimization cycles:

| Dimension | v0.2.0 modules (typical) | P5++ |
|---|---|---|
| LOC per module | ~50–250 | ~150–400 |
| Wall-time per run | ~ms | seconds–hours per MC realisation set |
| Scientific novelty | additive library extension | new numerical method (MC over stiff ODE) |
| Calibration data needed | none (uses literature anchors) | full Bayesian inference may need new wet-lab data |
| Sessions estimated | 1 per batch | 3–5 sessions across G1–G5; multi-week wall time |
| Risk profile | low (parallel-module pattern guarantees v9.1 preservation) | medium-high (novel sampler + new test infrastructure + parallelism interactions) |

This cycle therefore gets its own milestone series and **explicit deferral of G4/G5** to follow-on releases — the same staging approach the v0.2.0 cycle used for M0a/M0b/M1–M9.

### 0.2 Version naming reconciliation (HIGH priority decision)

The original P5++ protocol targets "v0.7.0 / v0.7.1 / v0.7.2", written when the fork's version was implicit and bled into the upstream simulator's v9.x release line. The v0.2.0 CHANGELOG entry committed today (2026-04-25) explicitly resolved that clash by adopting the **fork-line versioning convention**:

- `v0.x` = DPSim fork version line (v0.1.0 fork → v0.2.0 functional-optimization → v0.3.0 P5++ → ...)
- `v9.x` = upstream simulator's release line (last upstream release v9.2.2 on 2026-04-24)
- Internal cycle labels (e.g. "Tier 1 / Tier 2 / Tier 3", "G1 / G2 / G3 / G4 / G5") are orthogonal to either version line

**Recommended renaming:** P5++ shipping milestones become **v0.3.0 / v0.3.1 / v0.3.2**, with internal G1–G5 module labels preserved verbatim from the original protocol. The original protocol document stays intact as a planning record; this decomposition supersedes its versioning.

### 0.3 Upstream dependency check

All P5++ prerequisites listed in `p5_plus_plus_protocol.md` § 0.2 are **APPROVED** and unchanged by the v0.2.0 cycle (which was schema/dispatch additive only):

| Prerequisite | v0.2.0 impact | Status |
|---|---|---|
| Typed-enum tier promotion through calibration store | unchanged | ✅ |
| `model_manifest.evidence_tier` single source of truth | unchanged | ✅ |
| First-order delta-method posteriors (q_max, K_affinity, pressure-flow) | unchanged | ✅ |
| pH_transition / pH_steepness posterior diagnostics | unchanged | ✅ |
| Joblib `n_jobs` parallelism | unchanged | ✅ |
| `Quantity`-typed accessors | unchanged | ✅ |
| `unwrap_to_unit` helper | unchanged | ✅ |
| ProcessDossier as default lifecycle output | unchanged | ✅ |
| `ResultGraph.register_result` for sub-step provenance | unchanged | ✅ |
| Bin-resolved DSD propagation | unchanged (referenced as v0.4+ extension target) | ✅ |
| Family-aware Protein A scope-of-claim guard | unchanged | ✅ |
| `ModelMode` enforcement in M2 + M3 | unchanged | ✅ |

**One new prerequisite from v0.2.0 cycle to track:**
- Wet-lab ingestion module (`dpsim.calibration.wetlab_ingestion`) shipped in commit `0cd047d`. Its `CalibrationEntry` schema is the natural input shape for G1's `PosteriorSamples`. G1 should consume `CalibrationEntry` rather than reinvent the schema.

### 0.4 Token budget estimate

Per Reference 03 § 2 (orchestrator dialogue management):

| Phase | G1 | G2 | G3 | G4 | G5 | Total |
|---|---|---|---|---|---|---|
| Protocol | 2.0 k | 3.0 k | 1.5 k | 2.5 k | 1.5 k | 10.5 k |
| Implementation | 1.0 k | 1.6 k | 0.6 k | 1.2 k | 0.8 k | 5.2 k |
| Tests | 0.8 k | 1.2 k | 0.4 k | 0.8 k | 0.4 k | 3.6 k |
| Audit | 1.5 k | 2.0 k | 1.0 k | 1.5 k | 1.0 k | 7.0 k |
| Fix cycles (~1 round avg) | 0.4 k | 0.8 k | 0.2 k | 0.5 k | 0.3 k | 2.2 k |
| Handoff | 0.8 k | 1.0 k | 0.6 k | 0.8 k | 0.6 k | 3.8 k |
| Sub-total | 6.5 k | 9.6 k | 4.3 k | 7.3 k | 4.6 k | 32.3 k |
| × 1.5 safety | 9.8 k | 14.4 k | 6.5 k | 11.0 k | 6.9 k | 48.6 k |

v0.3.0 (G1 + G2 + G3) projected at **~31 k tokens** of inner-loop work + ~6 k milestone handover ≈ 37 k. Single-session feasible if context starts in GREEN. v0.3.1 (G4) and v0.3.2 (G5) are separate sessions per orchestrator framework's milestone-handover discipline.

---

## 1. Decomposition principles applied

Per Reference 02 § 2:

- **Follow the data.** The MC pipeline data flow is explicit in protocol § 2: `(ProcessRecipe + DSDPolicy)` → `PosteriorSamples` → joblib-parallel `[for s in samples: re-solve LRM with s]` → `MCBands` → `MethodSimulationResult.monte_carlo`. Each arrow is a module boundary.
- **Separate concerns.** Sampling (G1) is statistically independent from MC orchestration (G2) which is independent from result schema integration (G3). Keep them in separate modules so each can be tested in isolation.
- **Minimise coupling.** G2 consumes `PosteriorSamples` via the dataclass interface, NOT via direct knowledge of how the samples were drawn. This makes G4 (Bayesian-fit posteriors) interchangeable with G1 (CalibrationStore posteriors) downstream.
- **Identify parallelism early.** G2's per-sample LRM solves are embarrassingly parallel. Joblib `n_jobs` (already shipped via v0.6.0 / E2) is the right primitive.
- **Numerical robustness as a first-class concern.** Per the SA brief § 2, ~0.5–1.5 % of samples will fail at the tail under Gaussian σ=10% posteriors. This must be designed into G2, not bolted on. The tier-1 numerical safeguards are listed in § 3.2 below as an explicit module responsibility, not a footnote.

---

## 2. SA brief recommendations — integration map

The architect's decomposition embeds the SA brief's six recommendations as explicit module responsibilities or test gates:

| SA-ID | SA recommendation | Lands in | How embedded |
|---|---|---|---|
| SA-Q1 | Tier-1 (tolerance tightening + abort-and-resample + 5-failure cap) + Tier-2 (parameter clipping). REJECT LSODA. | G2 module responsibility | New helper `_tail_aware_solve()` wraps `solve_ivp(method="BDF")` with tolerance bands; abort-and-resample loop in `run_mc()`; explicit "no LSODA fallback" comment + audit gate |
| SA-Q2 | LHS for G1–G3; pymc + NUTS for G4 only; REJECT adjoint | G1 sampler choice | `PosteriorSamples.draw()` dispatches to `scipy.stats.qmc.LatinHypercube` (marginal-only) or `numpy.random.multivariate_normal` (covariance available); `pymc` confined to G4 with optional install extra |
| SA-Q3 | Reformulated convergence diagnostics: quantile-stability plateau + inter-seed posterior overlap; R-hat informational only | G2 acceptance test (AC#3) | `MCBands.convergence_diagnostics: ConvergenceReport` with explicit `quantile_stability_check` + `inter_seed_posterior_overlap`; R-hat field present but documented as informational |
| SA-Q4 | Marginal-only LHS as default (conservative); opt-in covariance; document independence flag in MCBands.assumptions | G1 + G2 | `PosteriorSamples.has_covariance: bool` flag; G2 records the flag in `MCBands.model_manifest.assumptions` automatically |
| SA-Q5 | ACCEPT v7-Q3 deferral of bin-resolved × MC to v0.4+ | v0.3.0 scope decision | `MCBands.model_manifest.assumptions` carries `"MC parameter variance and DSD geometric variance treated as independent; valid to <20% accuracy for bead radii in 30–100 µm; v0.4+ unifies the paths"` |
| SA-G1-09 | ~50 tests across G1–G5 | Per-module test inventory | Each module's test class enumerated in § 3 below; total exceeds the protocol's ≥30 gate (AC#5) |

---

## 3. Module Registry — Milestone v0.3.0 (G1 + G2 + G3)

Module Registry table conforms to Reference 04 § 3 of the dev-orchestrator handover template.

### 3.1 G1 — `posterior_samples` (Sonnet)

| Field | Value |
|---|---|
| Module ID | `G1.posterior_samples` |
| File path | `src/dpsim/calibration/posterior_samples.py` (NEW) |
| Responsibility | Define `PosteriorSamples` dataclass + LHS / multivariate-normal sampler + serialisation; consume `CalibrationEntry` from existing wet-lab ingestion module |
| LOC est. | ~250 |
| Complexity | MEDIUM (standard scipy/numpy primitives; no novel algorithm) |
| Model tier | **Sonnet** — per Reference 02 § 4: standard implementation 50–250 LOC, no novel math |
| Depends on | scipy ≥ 1.12 (for `scipy.stats.qmc.LatinHypercube`); numpy; existing `dpsim.calibration.calibration_data.CalibrationEntry` |
| Downstream | G2 consumes via `PosteriorSamples.draw(n)` interface |

**Public interface:**

```python
@dataclass
class PosteriorSamples:
    """N-dimensional posterior sample container, marginal- or covariance-aware."""
    parameter_names: tuple[str, ...]      # e.g. ("q_max", "K_affinity", "pH_transition")
    means: np.ndarray                     # shape (n_params,)
    stds: np.ndarray                      # shape (n_params,) — marginal σ
    covariance: np.ndarray | None         # shape (n_params, n_params) or None
    source_calibration_entries: list[CalibrationEntry]  # provenance from wetlab_ingestion

    @property
    def has_covariance(self) -> bool: ...

    def draw(
        self,
        n: int,
        seed: int = 0,
        method: Literal["lhs", "multivariate_normal", "auto"] = "auto",
    ) -> np.ndarray:
        """Return shape (n, n_params)."""
        ...

    def to_dict(self) -> dict: ...

    @classmethod
    def from_calibration_store(cls, store, parameter_names) -> PosteriorSamples: ...

    @classmethod
    def from_marginals(
        cls, parameter_names, means, stds,
        source_entries=None,
    ) -> PosteriorSamples: ...

    @classmethod
    def from_covariance(
        cls, parameter_names, means, covariance,
        source_entries=None,
    ) -> PosteriorSamples: ...
```

**Per-module acceptance tests** (12 tests, per SA brief § 7):

| Class | Tests | Coverage |
|---|---|---|
| `TestPosteriorSamplesSchema` | 4 | Marginal-only construction; covariance construction; schema validation; round-trip via `to_dict` / `from_dict` |
| `TestLHSDraw` | 4 | Reproducibility under fixed seed; correct shape (N, n_params); matches `scipy.stats.qmc.LatinHypercube` reference output; LHS variance reduction vs IID at low N |
| `TestMultivariateNormalDraw` | 3 | Sample mean recovery to ≤ 1% at N=10,000; covariance recovery to ≤ 5%; reproducibility under fixed seed |
| `TestCalibrationStoreIngestion` | 1 | `from_calibration_store()` correctly extracts means/stds and (when present) covariance |

**Risks:**
- **R-G1-1** (LOW): `scipy.stats.qmc.LatinHypercube` API stability — locked to scipy ≥ 1.12 in `pyproject.toml`; CI gate verifies. Mitigation: documented version pin.
- **R-G1-2** (LOW): Auto-detection of `method="auto"` may surprise users when covariance is partially specified (e.g., diagonal-only Σ). Mitigation: explicit warning + return path in docstring.

### 3.2 G2 — `monte_carlo` (Opus protocol + Sonnet impl)

| Field | Value |
|---|---|
| Module ID | `G2.monte_carlo` |
| File path | `src/dpsim/module3_performance/monte_carlo.py` (NEW) |
| Responsibility | MC LRM driver: parallel re-solution of LRM at sampled parameter values; numerical safeguards (SA-Q1 Tier-1+2); convergence diagnostics (SA-Q3); MCBands aggregator |
| LOC est. | ~400 |
| Complexity | **HIGH** — novel scientific code; numerical-stability gates; parallelism interactions; convergence diagnostics |
| Model tier | **Opus protocol generation** (per Reference 02 § 2: novel-algorithm protocol always Opus); **Sonnet implementation** (standard scipy/joblib primitives once protocol pinned); **Opus audit** (per Reference 07 § 3.2: full audit always Opus) |
| Depends on | G1; existing `module3_performance.transport.lumped_rate.solve_lrm`; `joblib.Parallel` (v0.6.0 / E2); existing `module3_performance.method.run_chromatography_method` |
| Downstream | G3 consumes via `run_mc()` entrypoint |

**Public interface:**

```python
@dataclass(frozen=True)
class MCBands:
    """Output of an MC LRM uncertainty-propagation run."""
    n_samples: int
    n_failures: int
    n_resampled: int
    scalar_quantiles: dict[str, dict[str, float]]   # e.g. {"dbc_10pct": {"p05": 23.1, "p50": 35.4, "p95": 48.7}}
    curve_bands: dict[str, np.ndarray]              # e.g. {"C_outlet_p05": (N_t,), "C_outlet_p50": (N_t,), "C_outlet_p95": (N_t,)}
    convergence_diagnostics: ConvergenceReport
    model_manifest: ModelManifest                   # tier inherits weakest across MC samples; SA-Q4/Q5 assumptions surfaced here


@dataclass(frozen=True)
class ConvergenceReport:
    """Per-metric convergence summary, per SA-Q3 reformulation."""
    quantile_stability: dict[str, bool]                 # e.g. {"dbc_10pct": True} — pass if ΔP50 over last 25% < 1% of running mean
    inter_seed_posterior_overlap: dict[str, float]      # e.g. {"dbc_10pct": 0.03} — max |ΔP50_ij| / median(P50)
    inter_seed_envelope: dict[str, float]               # e.g. {"dbc_10pct": 0.08} — informational
    r_hat_informational: dict[str, float]               # informational only; documented as not applicable to LHS-independent samples


def run_mc(
    samples: PosteriorSamples,
    base_recipe: ProcessRecipe,
    n: int = 200,
    n_seeds: int = 4,
    n_jobs: int = 1,
    failure_cap: int = 5,
    tail_sigma_threshold: float = 2.0,
    parameter_clips: dict[str, tuple[float, float]] | None = None,
) -> MCBands:
    """
    Draw n samples from `samples`, re-solve LRM at each, aggregate to MCBands.

    Numerical safeguards (SA-Q1):
      - Tail-aware tolerance tightening when |z-score| > tail_sigma_threshold
      - Abort-and-resample on solve_ivp RuntimeError
      - Hard failure cap (5 consecutive); sets MCBands.solver_unstable=True
      - Parameter clipping at parameter_clips (default: physiological limits)
      - NO LSODA fallback (codebase has documented LSODA stalls)

    Convergence (SA-Q3):
      - 4 RNG seeds, each n/4 samples, joined into one MCBands
      - Quantile-stability plateau check across cumulative N
      - Inter-seed posterior overlap (gating: max |ΔP50_ij| / median(P50) ≤ 5%)
      - R-hat reported informationally
    """
    ...
```

**Per-module acceptance tests** (18 tests, per SA brief § 7):

| Class | Tests | Coverage |
|---|---|---|
| `TestMCDriverSmoke` | 3 | N=10 smoke; N=100 produces non-trivial bands; reproducibility under fixed seed |
| `TestLinearRegimeAgreement` | 2 | At linear-isotherm regime + small σ, MC P50 matches delta-method to ≤ 1% (AC#1) |
| `TestNonLinearpHRegime` | 2 | At pH_steepness σ = 1.0, MC and delta-method disagree by ≥ 5% on elution recovery (AC#2) |
| `TestSolverFailureHandling` | 4 | Tail-tolerance tightening fires at \|z\| > 2σ; abort-and-resample on RuntimeError; consecutive-failure cap (5) sets `solver_unstable=True`; rejection of LSODA fallback (test that `method="LSODA"` is not in the call sites) |
| `TestParameterClipping` | 2 | Clipping at user-supplied bounds; warning logged; `n_clipped` diagnostic captured |
| `TestConvergenceReport` | 3 | Quantile-stability plateau check; inter-seed posterior overlap pass/fail at threshold; R-hat present but flagged informational |
| `TestParallelism` | 2 | n_jobs=1 vs n_jobs=8 produce identical numeric results (deterministic); wall-time scaling per AC#4 (parallel ≤ 5× serial-of-one-solve) |

**Risks:**
- **R-G2-1** (HIGH): Wall-time blowup at N=1000 × 6 quantiles × 30 s/solve = 50 hours serial. **Mitigation:** `n_jobs=8` parallelism brings to ~6 hours; default `n=200` keeps lifecycle smoke under 1 hour serial. Already mitigated in protocol § 3 R1.
- **R-G2-2** (MEDIUM): Inter-seed posterior overlap may fail intermittently at low N (e.g., n=200 with 4 seeds = 50 samples per seed). **Mitigation:** Document N ≥ 200 as the supported floor; raise warning for N < 100.
- **R-G2-3** (HIGH): Numerical safeguards interact in complex ways (tightened tolerances + abort-and-resample + clipping). Bug surface is large. **Mitigation:** Each safeguard is independently unit-tested; integration test exercises all three under tail-heavy synthetic posterior.
- **R-G2-4** (MEDIUM): Joblib parallel determinism — joblib's `Parallel(backend="loky")` does NOT guarantee bit-identical results across `n_jobs`. **Mitigation:** Use `backend="threading"` or seed each per-sample LRM solve explicitly; test verifies bit-identical output.

### 3.3 G3 — `MethodSimulationResult.monte_carlo` field + dispatch (Sonnet)

| Field | Value |
|---|---|
| Module ID | `G3.method_simulation_dispatch` |
| File paths | `src/dpsim/module3_performance/method.py` (extend `MethodSimulationResult`); `src/dpsim/module3_performance/method_simulation.py` (extend `run_method_simulation`); `src/dpsim/datatypes.py` (extend `DSDPolicy.monte_carlo_n_samples`, `monte_carlo_n_seeds`, `monte_carlo_parameter_clips`) |
| Responsibility | Optional `MCBands` field on `MethodSimulationResult`; dispatch in `run_method_simulation` triggered by `recipe.dsd_policy.monte_carlo_n_samples > 0` |
| LOC est. | ~150 |
| Complexity | MEDIUM (schema-additive + dispatch hook; mirrors v0.2.0 pattern) |
| Model tier | **Sonnet** — schema/dispatch additive |
| Depends on | G1, G2 |
| Downstream | G5 (UI band rendering) consumes via `MethodSimulationResult.monte_carlo` |

**Per-module acceptance tests** (6 tests):

| Class | Tests | Coverage |
|---|---|---|
| `TestDispatch` | 3 | `monte_carlo_n_samples=0` → `monte_carlo=None` (smoke baseline preserved bit-identically per AC#5); `> 0` → populated MCBands; default value 0 |
| `TestSchemaCompat` | 2 | All v0.x consumers handle the new optional field via `Optional[MCBands]`; serialisation round-trip via existing ProcessDossier paths |
| `TestRecipeIntegration` | 1 | Recipe-level configuration of `monte_carlo_n_samples` + `monte_carlo_parameter_clips` propagates to `run_mc()` correctly |

**Risks:**
- **R-G3-1** (HIGH): Smoke-baseline bit-identical preservation when `monte_carlo_n_samples=0`. **Mitigation:** Default value is 0; dispatch is gated by `> 0` check; golden-master test asserts byte-identical `MethodSimulationResult` for legacy code paths.
- **R-G3-2** (LOW): Existing v0.2.0 consumers may not handle `Optional[MCBands]` cleanly. **Mitigation:** Test `TestSchemaCompat` exercises lifecycle/orchestrator/dossier paths.

---

## 4. Module Registry — Milestone v0.3.1 (G4, optional follow-on)

### 4.1 G4 — `bayesian_fit` (Opus protocol + Sonnet impl)

| Field | Value |
|---|---|
| Module ID | `G4.bayesian_fit` |
| File path | `src/dpsim/calibration/bayesian_fit.py` (NEW); `pyproject.toml` (add `bayesian` extra) |
| Responsibility | HMC/NUTS posterior fitting via pymc; takes raw assay records (e.g. static-binding curves) and returns `PosteriorSamples` |
| LOC est. | ~300 |
| Complexity | HIGH (novel; optional install) |
| Model tier | **Opus protocol generation** (novel sampling chain); **Sonnet implementation** (off-the-shelf pymc API); **Opus audit** |
| Depends on | G1; pymc ≥ 5.0 (optional install via `pip install dpsim[bayesian]`); G2 (consumer) |
| Downstream | G2 (uses fitted PosteriorSamples instead of `from_calibration_store()`) |

**Public interface:**

```python
def fit_langmuir_posterior(
    assay_data: AssayRecord,           # existing dpsim type
    prior: dict[str, tuple[float, float]] | None = None,
    n_chains: int = 4,
    n_samples: int = 1000,
    target_accept: float = 0.95,
) -> PosteriorSamples:
    """
    Fit q_max, K_L from a static-binding-curve assay using NUTS.
    Returns a PosteriorSamples with covariance.

    Mandatory convergence gates (SA-Q3):
      - R-hat < 1.05
      - ESS > N/4 per chain
      - Divergence count < 1%
    Raises BayesianFitConvergenceError if any gate fails.
    """
    ...
```

**Per-module acceptance tests** (10 tests, per SA brief § 7):

| Class | Tests | Coverage |
|---|---|---|
| `TestPymcAvailable` | 2 | Skip suite if pymc not installed; `import dpsim.calibration.bayesian_fit` does not fail when extra absent (lazy import) |
| `TestNUTSFit` | 4 | Synthetic Langmuir recovery: q_max within 5%; K_L within 5%; covariance recovery; R-hat < 1.05 on all parameters |
| `TestConvergenceGates` | 4 | R-hat > 1.05 raises `BayesianFitConvergenceError`; ESS < N/4 raises; divergence > 1% raises; warning vs error escalation per gate |

**Risks:**
- **R-G4-1** (MEDIUM): pymc dependency footprint (~700 MB). **Mitigation:** Optional install extra; G2 must function without pymc; CI runs both with-pymc and without-pymc paths.
- **R-G4-2** (LOW): pymc API drift across versions. **Mitigation:** Version pin in `bayesian` extra; CI gate verifies fit on synthetic Langmuir at each pymc minor version bump.

---

## 5. Module Registry — Milestone v0.3.2 (G5, optional follow-on)

### 5.1 G5 — UI band rendering + ProcessDossier MC serialization (Sonnet)

| Field | Value |
|---|---|
| Module ID | `G5.ui_dossier_integration` |
| File paths | `src/dpsim/visualization/tabs/tab_m3.py` (extend with band rendering); `src/dpsim/process_dossier.py` (extend with MC serialization) |
| Responsibility | Plotly band overlay (P05/P50/P95) on M3 breakthrough curve view; ProcessDossier compressed export of MCBands |
| LOC est. | ~200 |
| Complexity | MEDIUM (UI extension + JSON serialization) |
| Model tier | **Sonnet** (standard UI/serialization) |
| Depends on | G3 |
| Downstream | M3 process dossier consumers |

**Per-module acceptance tests** (4 tests):

| Class | Tests | Coverage |
|---|---|---|
| `TestBandRender` | 2 | Plotly band overlay renders P05/P50/P95; SA-Q4/Q5 assumptions surfaced as UI footnote |
| `TestDossierSerialization` | 2 | MCBands round-trips through ProcessDossier JSON; size compression (e.g. quantile-only export when full curves are too large) |

**Risks:**
- **R-G5-1** (LOW): Plotly version drift. Mitigation: existing version pin in `pyproject.toml`.
- **R-G5-2** (LOW): MCBands JSON size at full curve resolution can be large (curve_bands per metric × N_t per curve). **Mitigation:** Optional decimation flag in serialization; default decimates to 100 points for dossier, full-resolution for in-memory UI.

---

## 6. Dependency DAG

```
─── v0.3.0 critical path ─────────────────────────────────────────────

[CalibrationStore / wetlab_ingestion] ─┐
                                        │
                                        ▼
                            G1.posterior_samples
                            (Sonnet, ~250 LOC)
                                        │
                                        ▼
                            G2.monte_carlo
                            (Opus protocol + Sonnet impl, ~400 LOC)
                                        │
                                        ▼
                            G3.method_simulation_dispatch
                            (Sonnet, ~150 LOC)
                                        │
                                        ▼
                            [v0.3.0 close]

─── v0.3.1 (independent of v0.3.0 critical path; lands separately) ──

G1 ──> G4.bayesian_fit (Opus protocol + Sonnet impl, ~300 LOC, optional install)

─── v0.3.2 (depends on v0.3.0 close) ────────────────────────────────

G3 ──> G5.ui_dossier_integration (Sonnet, ~200 LOC)

─── v0.4+ deferred (out of P5++ scope; recorded for roadmap) ────────

- MC × bin-resolved DSD (SA-Q5 deferral; ~7× walltime cost over 3-quantile MC)
- Adjoint-based variance propagation (rejected by SA-Q2 for v0.3; revisit if MC walltime bottleneck after v0.3.0)
- Digital-twin live-mode Bayesian updating (out of v0.7 scope per protocol § 1.2 Won't)
```

**Critical path** (longest dependency chain): G1 → G2 → G3 = 3 modules across one milestone. v0.3.0 ships when all three are APPROVED.

**Parallelism opportunity:** G4 and G5 are independent of each other and only depend on already-shipped (G1) or already-shipped (G3). They can be sequenced in any order or interleaved if context budget allows.

---

## 7. Per-milestone acceptance tests

Each milestone passes a literature-anchored or specification-anchored end-to-end check before close, mirroring the v0.2.0 cycle's per-batch acceptance tests.

| Milestone | Acceptance test | Source |
|---|---|---|
| **v0.3.0** (G1 + G2 + G3) | At linear-isotherm regime (q_max σ=10%, K σ=10%, no shape posteriors), MC N=1000 P50 matches delta-method P50 to ≤ 1% of delta-method mean | Protocol § 1.3 AC#1 |
| | At pH-switchable regime (pH_transition σ=0.5, pH_steepness σ=1.0), MC and delta-method disagree by ≥ 5% on elution recovery | Protocol § 1.3 AC#2 |
| | Inter-seed posterior overlap ≤ 5% on all output metrics across 4 RNG seeds at N=1000 | SA-Q3 reformulated AC#3 |
| | Wall-time scaling: parallel MC at n_jobs=8 completes N=1000 in ≤ 5× serial wall-time of one LRM solve | Protocol § 1.3 AC#4 |
| | ruff = 0; mypy = 0; pre-existing tests unchanged; ≥ 30 new tests | Protocol § 1.3 AC#5 |
| **v0.3.1** (G4) | NUTS recovers synthetic Langmuir q_max / K_L within ±5% of ground truth; R-hat < 1.05; ESS > N/4; divergence < 1% | SA brief § 7 |
| **v0.3.2** (G5) | M3 tab renders P05/P50/P95 bands; ProcessDossier MC round-trip preserves quantile values to ≤ 1e-6 relative tolerance | SA brief § 7 |

---

## 8. Per-module model-tier rationale

Per Reference 02 § 3 decision tree:

| Module | Tier | Rationale |
|---|---|---|
| G1 protocol | Sonnet | Standard scipy/numpy primitives; no novel algorithm — Reference 02 § 2 "Standard protocol generation = Sonnet" |
| G1 implementation | Sonnet | Reference 02 § 4: 50–200 LOC standard Python = Sonnet |
| G2 protocol | **Opus** | Reference 02 § 2: novel-algorithm protocol = Opus (this is the project's first Monte-Carlo-over-stiff-ODE driver; numerical-stability gates and convergence diagnostics are scientific-domain decisions) |
| G2 implementation | Sonnet | Once protocol is pinned, the implementation is standard scipy/joblib code; numerical safeguards are well-bounded |
| G3 protocol + implementation | Sonnet | Schema-additive with dispatch hook; mirrors many v0.2.0 modules |
| G4 protocol | **Opus** | Reference 02 § 2: novel-science (HMC/NUTS) protocol = Opus |
| G4 implementation | Sonnet | Off-the-shelf pymc API |
| G5 protocol + implementation | Sonnet | UI/serialization only |
| All audits (G1–G5) | **Opus** | Reference 02: full audits always Opus |
| All milestone handovers (v0.3.0/.1/.2) | **Opus** | Reference 04: handovers always Opus |

**Aggregate:** 1 Opus implementation module (G2 protocol gen) + 4 Sonnet implementation modules + 5 Opus audits + 3 Opus handovers ≈ matches the v0.2.0 cycle's ~50% token-savings projection.

---

## 9. Plan-level audit (D1–D6 against this decomposition)

Pre-emptive architect audit per Reference 05:

| Dim | Risk | Severity | Mitigation |
|---|---|---|---|
| **D1 Structural** | G2's combined responsibilities (sampler dispatch + numerical safeguards + convergence) approach single-responsibility limit. | MEDIUM | Internal helpers `_tail_aware_solve()`, `_check_convergence()`, `_aggregate_bands()` factor responsibilities; G2 module cohesion is "MC orchestration" — defensible |
| **D2 Algorithmic** | LHS variance reduction is well-established (McKay 1979) but for non-uniform posteriors needs care. SA-Q4 covariance handling has subtle correctness implications. | HIGH | G1's `TestMultivariateNormalDraw` (3 tests) + `TestLHSDraw` (4 tests) directly verify sample mean / variance / covariance recovery against ground truth |
| **D3 Data-flow** | MCBands `curve_bands` can be large (per metric × N_t × bands). At N_t = 1000 and 6 metrics × 3 bands = 18,000 floats per run = 144 kB. Manageable but need to be aware. | LOW | Default JSON serialization decimation in G5; in-memory paths use full resolution |
| **D4 Performance** | R-G2-1 MC walltime at N=1000 × n_jobs=8. Already the most-flagged risk in the protocol. | HIGH | Protocol § 3 R1 mitigation in place (parallelism + low default N); G2's `TestParallelism` AC#4 verifies the scaling target |
| **D5 Maintainability** | Numerical safeguards (Tier-1 tolerance / Tier-2 clipping) are subtle. Future contributors may misuse. | MEDIUM | Each safeguard has inline citation to SA brief § 2.3; integration test in G2 exercises all three under tail-heavy posterior; safeguards documented in module docstring with "do not remove without re-running SA-Q1 analysis" notice |
| **D6 First-principles** | Reformulated AC#3 (inter-seed posterior overlap) has a soft 5% threshold that the literature does not pin. | LOW | SA brief § 4.2 documents the 5% threshold as a project-specific calibration; it is auditable and adjustable |

---

## 10. Architect's notes for the orchestrator

- **v0.3.0 milestone scope is final** at G1 + G2 + G3. G4 and G5 are NOT in v0.3.0 scope; bundling them risks the 32 k token budget overrun.

- **Compression triggers per Reference 03 § 4:**
  - Before G2 implementation start (Opus protocol + Sonnet impl ≈ 14 k tokens): mandatory compression check; if context < YELLOW, compress first.
  - At G3 close (= v0.3.0 close): mandatory milestone handover. Pre-allocate ~6 k tokens.

- **Fix-cycle expectations:** G2 is the high-risk module (HIGH complexity per § 3.2). Budget 2 fix rounds (per Reference 02 § 6: "If a module requires >2 fix rounds → flag for tier review and consider Opus on next similar module"). G1, G3, G4, G5 budget 1 fix round each.

- **Scientific Advisor escalation paths:** if any of these surface during G2 implementation, re-engage SA per Reference 06:
  - Empirical solver failure rate > 2% (SA brief § 2.2 estimated 0.5–1.5%); may indicate posterior-tail handling needs revision
  - Inter-seed posterior overlap fails > 5% even at N=1000 (suggests sampling is genuinely unstable, not just under-sampled)
  - MC vs delta-method disagreement signature in linear regime > 1% (suggests bias in sampler or numerical drift)
  - Bayesian fit (G4) fails NUTS gates on synthetic data (suggests prior mis-specification)

- **The v0.3.0 milestone unblocks** users who today are forced to interpret first-order delta-method intervals as if they were full posterior bands. The downstream impact is in M3 process-dossier reporting, where capacity claims (DBC) and elution-recovery claims (the regime where delta-method is most wrong) get correctly-sized uncertainty bands instead of artificially narrow ones.

- **The v0.4+ deferred items** (MC × bin-resolved DSD; adjoint sensitivity; digital-twin live mode) carry forward unchanged from the protocol § 1.2 "Won't (this iteration)" list. They are not in v0.3.x scope.

---

## 11. Architect's deliverable checklist

- [x] Module Implementation Protocol scaffolding for each of 5 modules (file path, responsibility, dependency, complexity, tier)
- [x] Interface specifications for G1 `PosteriorSamples` and G2 `MCBands` / `ConvergenceReport` / `run_mc()` declared at type level
- [x] Acceptance tests defined per milestone in § 7 (matches AC#1–AC#5 from protocol + SA-Q3 reformulated)
- [x] Build order with dependency DAG in § 6
- [x] Model-tier rationale per Reference 02 § 3 in § 8
- [x] D1–D6 plan-level audit in § 9
- [x] SA brief recommendations integration map in § 2
- [x] Version naming reconciliation in § 0.2 (v0.7.x → v0.3.x; rationale matches v0.2.0 cycle's CHANGELOG resolution)
- [x] Token budget estimate per Reference 03 § 2 in § 0.4
- [x] Orchestrator handoff notes in § 10

The detailed Phase-1 protocols (G1 12-point check) for each of G1 / G2 / G3 are deferred to the start of each module's pre-flight (Phase 0) in the v0.3.0 implementation session. This decomposition is the input to those protocols; the orchestrator will sequence them.

---

> **Architect's disclaimer:** This decomposition is the design authority's view, refined against the SA brief's first-principles analysis. Implementation-time deviations must be raised back to /architect for protocol revision, not silently absorbed by /scientific-coder. Per Reference 05, fix cycles are capped at 3 rounds per module before REDESIGN escalation. The numerical safeguards in G2 (Tier-1 tolerance, abort-and-resample, Tier-2 clipping) are research-grade design choices grounded in published BDF-stiff-ODE literature; they should be re-validated against the chosen synthetic tail-sample test cases before being declared production-ready.
