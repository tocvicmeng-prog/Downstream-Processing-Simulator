# Scientific Advisor Brief — v0.7.x P5++ Monte-Carlo LRM Uncertainty Propagation

**Document ID:** SA-v0.7-P5plusplus-001
**Date:** 2026-04-25
**Author role:** Scientific Advisor (Mode 1 — Design Realisation Support)
**Audience:** /architect, /dev-orchestrator (joint plan assembly)
**Resolves:** P5++ protocol § 5 G1-08 (numerical-stability) and § 7.3.b (full G1 readiness pending SA brief)
**Companion:** `docs/p5_plus_plus_protocol.md`

---

## 1. Scope and method

The P5++ protocol ships a planning skeleton at G1 = 10/12 PARTIAL PASS. Two G1 items are deliberately deferred pending this brief:

- **G1-08 — numerical-stability considerations.** What does the BDF-LRM solver do when calibration parameters are sampled at the tail of their posteriors?
- **G1-09 — per-module test inventory.** Cannot be finalised until the sampler choice (this brief) and the convergence diagnostics (this brief) are settled.

This brief is a Mode-1 design-realisation analysis (Reference 07 §1) of the **5 questions** the architect identified, framed as concrete recommendations for the v0.7.0 protocol session. Each section ends with an explicit `RECOMMENDATION:` line that the joint plan can lift verbatim.

---

## 2. Q1 — LRM numerical regime under random parameter draws

### 2.1 First-principles assessment

The LRM (`src/dpsim/module3_performance/transport/lumped_rate.py`) is a stiff coupled ODE system:

```
dC/dt = -u·dC/dz - (1-εb)/εb · k_eff · (Cp - C)        (mobile phase)
dCp/dt = k_eff · (C - Cp) - dq/dt                       (pore phase)
dq/dt = governed by isotherm(Cp, q_max, K_L, ...)       (stationary)
```

Solver: scipy `solve_ivp(method="BDF")` with configurable `rtol`/`atol` and `max_step=total_time/20`.

The existing implementation (line 372–386) **explicitly warns that LSODA stalls on high-affinity Langmuir and gradient paths on the current Python/SciPy runtime, blocking full-suite execution**. This is a critical constraint: **LSODA is NOT a safe fallback for tail-sampled parameters** — the project has already learned that LSODA is less robust than BDF on this problem.

### 2.2 Failure modes under tail sampling

| Parameter | Tail behavior | Solver impact |
|---|---|---|
| `q_max` upper tail | High capacity → faster saturation front; steeper gradient in z | BDF Newton iteration ill-conditioned; needs finer dz or tighter tolerances |
| `K_L` (= `K_affinity`) upper tail | Near-irreversible binding; isotherm `q = q_max·K_L·C/(1+K_L·C)` saturates sharply | Jacobian becomes poorly scaled; max_step constraint may be insufficient |
| `K_L` lower tail | Linear-isotherm regime | Stable but trivial (no front); MC correctly low-information here |
| `pH_steepness` upper tail (>10) | Sigmoid → step function | Discontinuity; BDF chokes |
| `pH_transition` near elution pH | Small numerator/denominator in sigmoid derivative | Same step-function pathology if combined with high `pH_steepness` |

**Order-of-magnitude estimate of failure rate.** For Gaussian-approximate posteriors with σ as documented (q_max σ=10%, K_L σ=10%, pH_steepness σ=1.0), Monte-Carlo at N=1000 draws places ~3 samples beyond ±3σ. Empirically, BDF converges robustly within ±2σ but begins to struggle at ±3σ on stiff Langmuir systems (Schiesser 1991 *Numerical Method of Lines*; Hindmarsh & Petzold 2005 *Sundials*). Expected failure rate at N=1000: **~0.5–1.5%** (5–15 samples per 1000), concentrated at the tails.

### 2.3 Numerical-stability strategy (recommended)

**Tier 1 — first-line robustness (mandatory for v0.7.0):**

1. **Tail-aware tolerance tightening.** Detect when a sampled parameter is >2σ from its posterior mean; if so, tighten `rtol` from default 1e-3 to 1e-6 and `atol` proportionally. Cost: ~2–3× slower per solve, applied to the ~5% of samples that need it.
2. **Per-sample try/except with abort-and-resample.** If `solve_ivp` raises `RuntimeError`, log a warning with the sample index and parameter values, then draw a replacement sample from the SAME posterior (not the tail). The replacement preserves the posterior's central mass; the failure log records bias risk for audit.
3. **Hard cap on consecutive failures.** If 5+ samples fail consecutively, abort that seed group with `MCBands.solver_unstable=True` flag, and recommend the user re-run with a tightened posterior or a different RNG seed.

**Tier 2 — domain-aware clipping (recommended; defensible):**

4. **Parameter clipping at physiological limits.** If a sampled parameter would exceed a documented physiological range (e.g., `pH_steepness > 20` is non-physical for any real ligand), clip to the upper bound with a logged warning. This trades posterior fidelity for solver reliability — defensible because the posterior beyond the clip range is itself unreliable (the original calibration data did not cover that regime).

**Tier 3 — out of v0.7.0 scope:**

5. **Adaptive z-grid.** Increase `n_z` when the front becomes steep. Substantial code change to `lumped_rate.py`; defer to v0.8+ if Tier 1+2 prove insufficient.
6. **LSODA fallback.** **REJECTED** — the existing code's comment establishes LSODA is less robust here. Do not introduce as a fallback.

> **RECOMMENDATION:** Implement Tier 1 (tolerance tightening + abort-and-resample + consecutive-failure cap) and Tier 2 (parameter clipping at documented physiological limits). Reject LSODA fallback. Defer adaptive z-grid to v0.8+.

---

## 3. Q2 — Sampler choice

### 3.1 The two distinct sampling problems

The protocol's G1–G3 (MC driver) and G4 (Bayesian fitting) solve **different statistical problems**. Conflating them produces a heavyweight stack where a lightweight one suffices.

| Task | Statistical problem | Right tool |
|---|---|---|
| **G1–G3** | Forward UQ from a **known** posterior | Stratified / LHS / direct sampling |
| **G4** | Fit posterior from **raw assay data** | HMC / NUTS via pymc |

### 3.2 First-principles trade-offs

**Off-the-shelf pymc + NUTS:**
- Strength: gold standard for HMC; handles correlated multimodal posteriors; well-tested R-hat / ESS diagnostics built in.
- Weakness: heavy install (~700 MB with backend; pulls in pytensor / numpyro / arviz); license is Apache 2.0 (compatible with project GPL-3.0); slow startup on cold cache.
- **Match to G1–G3**: overkill. NUTS is for sampling intractable posteriors. G1–G3 has a known posterior and just needs draws.
- **Match to G4**: correct. NUTS is exactly the tool for fitting a posterior to a likelihood + prior.

**Latin Hypercube Sampling (LHS) / stratified sampling:**
- Strength: zero new dependency (`scipy.stats.qmc.LatinHypercube` already available); deterministic given seed; better-than-IID variance reduction at low N (per McKay et al. 1979 *Technometrics* 21:239); easy to interpret.
- Weakness: cannot fit a new posterior; requires the user to provide marginals + optional covariance.
- **Match to G1–G3**: optimal. The MC driver receives a posterior and draws from it; LHS is the right primitive.
- **Match to G4**: not applicable.

**Direct multivariate normal sampling:**
- Strength: trivial implementation when covariance is available (`numpy.random.multivariate_normal`); no QMC machinery; standard practice.
- Weakness: pure pseudo-random; needs larger N than LHS for the same variance reduction.
- **Match to G1–G3**: acceptable; LHS is strictly better at the same N.

**Custom adjoint sensitivity:**
- Strength: O(N_param) vs O(N_sample) for first-order moments — potentially 100× faster.
- Weakness: requires writing the LRM adjoint solver (Cao et al. 2003 *SIAM J. Sci. Comput.* 24:1076; substantial mathematical and engineering work). Only gives local linear sensitivities — does NOT capture posterior shape, multimodality, or non-linearity. Equivalent to the existing P5+ delta-method, just faster.
- **Match to G1–G3**: rejected. Adjoint gives the same information P5+ already provides; the whole point of P5++ is to capture non-linear regimes the delta-method misses.

### 3.3 Recommendation

> **RECOMMENDATION (G1–G3 MC driver):** Use `scipy.stats.qmc.LatinHypercube` for marginal-only sampling, `numpy.random.multivariate_normal` when a covariance matrix is available. Zero new dependency. Both backends in the same wrapper, selected by the `PosteriorSamples` schema's `has_covariance` flag.

> **RECOMMENDATION (G4 Bayesian fitting):** Use `pymc` + NUTS, behind an optional install extra `pip install dpsim[bayesian]`. The MC driver in G1–G3 must function without `pymc` installed.

> **RECOMMENDATION (adjoint):** Reject for v0.7.0. Adjoint gives the same information as the existing P5+ delta-method. Re-evaluate in v0.9+ as a fast-path for the bin-resolved × MC scenario (Q5) if MC walltime becomes the bottleneck.

---

## 4. Q3 — Convergence diagnostics

### 4.1 First-principles framing

The protocol's acceptance criterion AC#3 (`R-hat < 1.05 across 4 independent MC seeds for N=1000 samples`) conflates two diagnostics from different settings:

- **R-hat (Gelman & Rubin 1992)** is designed for **MCMC chains** where samples are correlated within a chain. For LHS or independent MC, samples are **independent by construction**, so R-hat between seed groups reduces to a **posterior-overlap** check — useful but misnamed.
- **ESS (effective sample size)** for independent samples equals the nominal N. The diagnostic is informative for HMC chains, not for the G1–G3 MC driver.

### 4.2 The right diagnostics for each path

**G1–G3 MC driver (LHS / multivariate-normal samples; samples are independent):**

1. **Quantile stability** (primary). Plot P05, P50, P95 vs. cumulative N for each output metric (DBC, recovery, etc.). Convergence requires the curve to plateau before the user-requested N is reached. Threshold: ΔP50 over the last 25% of the run < 1% of the running mean.
2. **Inter-seed posterior overlap** (gating). Run 4 independent RNG seeds, each with N/4 samples. Compute |P50_i - P50_j| / median(P50) for all pairs. Pass if max < 5% on all output metrics. This is the protocol's AC#3 reformulated correctly — it's a posterior-overlap check, not R-hat.
3. **Inter-seed quantile envelope** (informational). Report the spread of P05 and P95 across seeds. If the envelope exceeds 10% of the median, sampling is unreliable; recommend N ↑ or check for solver instability.

**G4 NUTS (correlated within-chain samples):**

1. **R-hat < 1.05** (mandatory). Standard Gelman-Rubin across ≥4 chains.
2. **ESS > N/4** (mandatory). Per chain.
3. **Divergence count** (mandatory). NUTS divergences indicate non-Gaussian posterior geometry; >1% of samples divergent should fail the calibration.

### 4.3 Recommendation

> **RECOMMENDATION (G1–G3):** Replace the protocol's AC#3 R-hat criterion with: (a) quantile-stability plateau check at < 1% over last 25% of run, AND (b) inter-seed posterior-overlap ≤ 5% across 4 RNG seeds. Compute R-hat as an informational diagnostic only; document explicitly that for independent samples R-hat is approximately a posterior-overlap restatement.

> **RECOMMENDATION (G4):** Keep R-hat < 1.05, ESS > N/4, divergences < 1% as mandatory NUTS gates.

---

## 5. Q4 — Posterior covariance handling

### 5.1 The science of joint vs marginal posteriors

For static-binding-curve fits (Langmuir / Hill / SMA), the joint posterior is **typically negatively correlated** between `q_max` and `K_L`. The reason is identifiability: at low `K_L` the curve flattens, so a higher `q_max` compensates; at high `K_L` the curve saturates earlier, so a lower `q_max` fits. The literature value (Karlsson et al. 1998 *J. Chromatogr. A* 824:1) is correlation coefficient ρ ≈ −0.5 to −0.8 for typical assay data.

**Implication of ignoring covariance:**
- Independent marginal sampling assumes ρ=0.
- Real ρ is typically negative.
- A negative correlation reduces the variance of `q_max·K_L` (the binding-strength product); independent sampling **overestimates** the variance on this product.
- Therefore **marginal-only MC is conservative** for capacity claims (DBC) — wider bands than reality. Acceptable for screening.
- **Marginal-only MC is anti-conservative** for cases where positive correlation exists (rare; e.g. hot-spot binding modes where higher q_max correlates with stronger affinity).

### 5.2 Recommended fallback hierarchy

1. **Best path (when available):** Use the covariance matrix from `CalibrationStore` if the calibration entry carries one. Sample via `numpy.random.multivariate_normal`.
2. **Conservative fallback (default in v0.7.0):** Marginal-only sampling via LHS. Flag in `MCBands.model_manifest.assumptions` as `"marginal-only posterior; bands may overestimate uncertainty when q_max × K_L correlation is non-zero (typical literature: ρ ≈ −0.5 to −0.8 per Karlsson 1998)"`. This is auditable and conservative.
3. **Future enhancement (v0.8+):** Imputed-correlation sampling. When covariance is unavailable, draw correlated samples using a literature prior (Karlsson 1998 ρ = −0.7 default; user-configurable). Run twice (independent + imputed) and report the spread as a covariance-sensitivity diagnostic.

### 5.3 Recommendation

> **RECOMMENDATION:** Implement (1) and (2) in v0.7.0. Defer (3) to v0.8+. The default in v0.7.0 is conservative (overestimates uncertainty when correlation is negative, as it usually is) — this is the right side to err on for screening claims.

---

## 6. Q5 — Bin-resolved DSD × MC interaction (v7-Q3)

### 6.1 The two sources of variance

**Variance source A — calibration uncertainty (parameter-driven).** What MC propagates: q_max, K_L, pH_transition, etc. are uncertain because the static-binding curve fit only constrains them to within their posterior σ.

**Variance source B — bead-population geometry (DSD-driven).** What bin-resolved DSD captures: the actual bead population has a distribution of radii; smaller beads have higher specific surface area → higher q_max-per-gram and faster mass transfer. The 3-quantile path approximates this with three representative bead sizes (P05, P50, P95 of the DSD).

### 6.2 First-principles independence assessment

Are the two variance sources independent?

- **Bead radius is a geometric/process variable** (set by emulsification parameters: stir speed, surfactant load, T_oil).
- **q_max and K_L are chemistry variables** (set by ligand density, ligand identity, target protein affinity).

To first order, these are physically independent. Bead size doesn't determine ligand chemistry; ligand chemistry doesn't change during emulsification.

**Second-order coupling exists:**
- Smaller beads have higher specific surface area → at constant ligand loading per surface area, higher q_max-per-gram. So a smaller-bead distribution has a higher mean q_max.
- This is captured implicitly because q_max in the calibration store is a per-volume quantity already calibrated against a particular bead size; the calibration store maps bead size → q_max.
- The second-order effect is bounded: literature data (Boi 2007 *J. Chromatogr. B* 848:19; Etzel 1995 *Bioseparation* 5:73) suggests <20% variation in q_max per decade of bead radius for typical 30–100 µm beads.

### 6.3 Defensibility of the v0.7.0 / v0.8.0 split

The protocol defers MC × bin-resolved DSD to v0.8.0 with cost = O(N × bins × LRM_solve), ~7× more expensive than 3-quantile MC.

**Defensible because:**
1. The two variance sources are largely independent (first-order); cross-coupling is bounded at ~20%.
2. 3-quantile MC gives screening-quality bands at tractable cost (~hours).
3. v0.8.0+ MC × bin-resolved is opt-in for users who need tighter bands.
4. The independence assumption can be **explicitly stated** in `MCBands.model_manifest.assumptions` so users know what they're getting.

**Indefensible if:**
- The application is a target with extreme bead-radius × q_max coupling (e.g., < 10 µm beads where surface-area scaling dominates).
- The user requires combined uncertainty bands for regulatory submission (where the independence assumption itself becomes a vulnerability).

### 6.4 Recommendation

> **RECOMMENDATION:** ACCEPT the v7-Q3 deferral to v0.8.0. Document the independence assumption in `MCBands.model_manifest.assumptions` as: `"MC parameter variance and bin-resolved DSD geometric variance treated as independent; valid to <20% accuracy for bead radii in 30–100 µm; v0.8+ unifies the paths for cases where this assumption is challenged."` Surface this assumption in the `tab_m3.py` band-rendering UI as a footnote.

---

## 7. Test inventory (resolves protocol G1-09)

The protocol's G1-09 was deferred until sampler choice was fixed. With LHS / multivariate normal as the answer (Q2), the per-module test inventory firms up:

### G1 `dpsim.calibration.posterior_samples` (~12 tests)

| Test class | Coverage |
|---|---|
| `TestPosteriorSamplesSchema` | Marginal-only construction; covariance construction; schema validation rejects bad inputs |
| `TestLHSDraw` | Reproducibility under fixed seed; matches scipy LHS output; correct shape (N, n_params) |
| `TestMultivariateNormalDraw` | Mean recovery to ≤ 1% at N=10000; covariance recovery to ≤ 5%; reproducibility |
| `TestSerialization` | Round-trip via `to_dict` / `from_dict` |

### G2 `dpsim.module3_performance.monte_carlo` (~18 tests)

| Test class | Coverage |
|---|---|
| `TestMCDriver` | N=10 smoke; N=1000 in linear regime matches delta-method P50 to ≤ 1%; N=1000 in non-linear pH regime disagrees from delta-method by ≥ 5% (per AC#2) |
| `TestSolverFailureHandling` | Tail-sample tolerance tightening fires when |Δ| > 2σ; abort-and-resample on RuntimeError; consecutive-failure cap (5) trips correctly |
| `TestParameterClipping` | Clipping at documented physiological limits; warning logged; clip rate diagnostic captured |
| `TestConvergenceDiagnostics` | Quantile stability (plateau check); inter-seed posterior overlap; R-hat informational only for independent samples |
| `TestMCBandsAggregation` | Scalar quantile computation matches numpy reference; curve bands have correct shape; manifest tier inherits weakest |
| `TestParallelism` | n_jobs=1 vs n_jobs=8 produce identical numeric results; wall-time scaling per AC#4 |

### G3 `MethodSimulationResult.monte_carlo` field + dispatch (~6 tests)

| Test class | Coverage |
|---|---|
| `TestDispatch` | `monte_carlo_n_samples=0` → `monte_carlo=None` (smoke baseline preserved bit-identically per AC#5); `> 0` → populated MCBands |
| `TestSchemaCompat` | All v0.x consumers handle the new field via `Optional[MCBands]` |

### G4 (optional Bayesian fitting; v0.7.1) (~10 tests)

| Test class | Coverage |
|---|---|
| `TestPymcAvailable` | Skip suite if pymc not installed |
| `TestNUTSFit` | Fit a synthetic Langmuir curve; recover q_max / K_L within 5% of ground truth |
| `TestConvergenceGates` | R-hat < 1.05 mandatory; ESS > N/4 mandatory; divergence count < 1% |

### G5 (UI band rendering; v0.7.2) (~4 tests)

| Test class | Coverage |
|---|---|
| `TestBandRender` | Plotly band overlay with P05/P50/P95; ProcessDossier MC serialization round-trip |

**Total v0.7.x test budget: ~50 tests** (vs the protocol's ≥30 acceptance gate AC#5).

---

## 8. Summary of recommendations

| ID | Recommendation | Resolves |
|---|---|---|
| SA-Q1 | Implement Tier-1 (tolerance tightening + abort-and-resample + failure cap) and Tier-2 (parameter clipping). REJECT LSODA fallback. Defer adaptive z-grid. | G1-08 numerical-stability |
| SA-Q2 | LHS / multivariate-normal for G1–G3 (zero new deps). pymc + NUTS for G4 only, behind `pip install dpsim[bayesian]`. REJECT custom adjoint for v0.7. | Sampler choice |
| SA-Q3 | Reformulate AC#3: quantile-stability plateau + inter-seed posterior overlap (4 seeds, < 5% on all metrics). R-hat informational only. | Convergence diagnostics |
| SA-Q4 | Implement marginal-only LHS as default; opt-in covariance via `numpy.random.multivariate_normal` when `CalibrationStore` carries Σ. Document independence flag in `MCBands.assumptions`. | Posterior covariance handling |
| SA-Q5 | ACCEPT v7-Q3 deferral to v0.8.0. Document independence assumption explicitly in MCBands manifest and surface in M3 UI footnote. | Bin-resolved × MC interaction |
| SA-G1-09 | ~50 tests across G1-G5, distributed per § 7. | Test inventory |

These six recommendations close G1-08 and G1-09. With them applied, the v0.7.0 protocol's G1 readiness moves from 10/12 PARTIAL PASS to 12/12 FULL PASS — sufficient to enter the per-module protocol-generation phase.

---

> **Disclaimer:** This scientific analysis is provided for informational, research, and advisory purposes only. The numerical-stability recommendations are based on first-principles analysis of the existing BDF-LRM solver and published literature on stiff ODE integration; they should be validated against synthetic tail-sample test cases before being declared production-ready. The sampler-choice recommendation is based on the documented statistical-method literature (McKay 1979, Karlsson 1998, Cao 2003, Gelman & Rubin 1992) and trade-off analysis; it should be revisited if the v0.7.0 protocol session uncovers project-specific constraints not visible to this brief.
