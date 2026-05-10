# ADR-007 — Forward Monte Carlo Bayesian envelope: prior choices and aggregation

**Status:** Accepted
**Date:** 2026-05-10
**Decision driver:** v0.8.2 W-043. The v0.7.0 plan §6 deferred "Bayesian uncertainty propagation through the envelope". The v0.8.1 plan inherited it; this ADR + the accompanying ``pressure_envelope_mc.py`` close the code-side commitment. Inverse Bayesian inversion against measured pressure-flow data remains user-side / wet-lab-driven.

## Context

`compute_pressure_envelope` (B-2f / W-020) ships a deterministic
SEMI_QUANTITATIVE INTERVAL render policy: the envelope's tier maps to
a fixed ±factor band per output type, and the user is told that the
*actual* uncertainty depends on the ν / K_geom calibration data they
have not yet supplied. The deterministic policy has two limitations:

1. **Tier intervals are policy-driven, not data-driven.** A
   ±30 % SEMI_QUANTITATIVE band is the same for every column / family —
   it doesn't reflect the actual variability of the underlying physical
   parameters at this operating point.
2. **No tail probabilities.** "Headroom = 0.65" tells the operator
   the central case is safe, but not whether a 5 % salt-mismatch or
   a 10 % bead-modulus error pushes them into BLOCKER territory.

A forward Monte Carlo wrapper around `compute_pressure_envelope`
addresses both limitations: sample from priors over the uncertain
inputs, run the deterministic envelope per draw, and aggregate to
P05/P50/P95 of every output. The user can then see the *probability*
that headroom exceeds 1.0 at this operating point.

## Decision

**Ship `monte_carlo_pressure_envelope` as a thin wrapper around the
deterministic envelope, with these prior choices:**

| Parameter | Prior | Justification |
|---|---|---|
| K_geom multiplicative error | Lognormal(μ=0, σ_log=0.20) | ±20 % CV captures the typical literature spread of K_geom across resin lot, packing-method, and column-aspect-ratio variations; lognormal because K_geom is positive and multiplicative. |
| ν (or K_d) multiplicative error | Lognormal(μ=0, σ_log=0.15) | ±15 % CV typical for protein-resin K_d when fitted from a single batch of breakthrough data. |
| μ (viscosity) multiplicative error | Lognormal(μ=0, σ_log=0.05) | ±5 % CV reflects μ uncertainty from buffer composition rounding (we know temperature; we don't always know the exact NaCl molarity). |
| G_DN multiplicative error | Lognormal(μ=0, σ_log=0.30) | ±30 % CV; bead modulus is the most poorly-known input — small-deformation uniaxial measurements vs in-bed packing stress can differ substantially. |

Defaults are conservative-mid-range. Users with local calibration data
can override per-call.

**Aggregation:** report P05, P50, P95 of `Q_max_m3_s`,
`dP_predicted_pa`, `dP_max_operational_pa`, and `headroom_ratio`.
Plus a derived diagnostic: **P(headroom_ratio > 1.0)** — the
probability that the operating point is BLOCKER under the priors.

**Sample count:** default 500. Empirical: ±2 % stable estimate of the
P95 with 500 samples; users can dial up to 5000 for tail-probability
work without making the wrapper sluggish.

## Why MC vs. analytic / closed-form

- **Closed form** would require linearizing each input's effect through the iterated KC + bed-compression solver. The iteration explicitly captures runaway nonlinearity near u_crit; linearization breaks exactly where the user most cares.
- **Polynomial chaos / MLMC** would amortize cost across many envelopes, but each envelope call is already cheap (~10 ms). A naive MC at N=500 is ~5 s — acceptable for a UI-side preview and a BO inner-loop run alike.
- **Bayesian inference** (vs forward propagation) would invert measured pressure-flow data against the prior to produce a posterior over K_geom / ν. v0.8.2 ships only the forward path; the inverse path is wet-lab-driven and lives in v0.9 with calibration-store integration.

## Decision-grade tier mapping

The MC envelope keeps the same `decision_tier` as the deterministic envelope's representative draw (typically the median input). The MC bands themselves are SEMI_QUANTITATIVE — they reflect the assumed prior, not measured posterior, and a CALIBRATED_LOCAL promotion requires the user to supply their own posterior.

## Out of scope

- **Inverse / posterior inference** (v0.9 candidate).
- **Correlated priors.** v0.8.2 assumes K_geom, ν, μ, G_DN are independent. Real correlations (e.g. hot buffers shift both μ AND ν together) are second-order; document as a known limitation.
- **Per-family priors.** Defaults assume one prior per parameter. Family-specific priors (alginate vs PLGA have very different G_DN spreads) are a v0.9 enhancement.
- **Coupled multi-step propagation.** B-2k handles deterministic multi-step. Applying MC across a step program with correlated draws (the same K_geom across load + wash + elute) is a v0.9 enhancement.

## References

- Nelson, B.L. (2013). *Foundations and Methods of Stochastic Simulation* — Chapter 4 (Monte Carlo prior propagation).
- Lee, P.M. (2012). *Bayesian Statistics: An Introduction* — Section 9 (forward vs inverse propagation).
- ADR-005 — Salt-dependent isotherm: Mollerup-simplified modulator (parameter source for ν).
- ADR-006 — Full SMA promotion path (parameter source for σ when promoted to SMA).
