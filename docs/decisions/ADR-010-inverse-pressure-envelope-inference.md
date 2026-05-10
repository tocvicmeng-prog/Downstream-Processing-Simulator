# ADR-010 — Inverse pressure-envelope inference: importance sampling vs MCMC

**Status:** Accepted
**Date:** 2026-05-10
**Decision driver:** v0.8.3 W-047. ADR-007 closed the **forward** Monte Carlo wrapper at v0.8.2 and explicitly deferred the **inverse** path: "inverse Bayesian inference against measured pressure-flow data is wet-lab driven and lives in v0.9 with calibration-store integration." This ADR + the accompanying `pressure_envelope_inverse.py` close the *machinery* in v0.8.3; the wet-lab handshake (mapping a fitted posterior into a CALIBRATED_LOCAL tier promotion) remains user-side.

## Context

A user with measured `(Q_observed, ΔP_observed)` pairs from a real run
(or a manufacturer pressure-flow specification sheet) wants to know:
- What does the data tell me about K_geom for *this* column?
- Given that posterior, what does the operational headroom look like at my Q_target?

ADR-007's forward MC produces P05/P50/P95 bands under a *prior* over
K_geom / μ / G_DN. The forward bands are the right answer when no data
is available; once data lands, the user wants a *posterior* — narrower
bands centered on the data-implied mode.

Three implementation strategies are available:

| Strategy | Cost | Library deps | Notes |
|---|---|---|---|
| **Importance sampling** | O(N · cost(forward draw)) | numpy only | Reuses v0.8.2 forward MC; weights samples by likelihood. |
| **MCMC (NUTS / MH)** | O(N_chain · cost(forward draw)) where N_chain is typically 1k–10k+ | pymc / arviz (already pinned via dev deps) | Strictly better tail coverage; needs warmup; deps add ~30 s import time. |
| **Variational inference** | O(N_iter · cost(forward draw) + gradient overhead) | pymc | Cheapest tail coverage when posteriors are roughly Gaussian. |

ADR-007 chose importance sampling for the forward MC because per-draw
cost (~10 ms) is already cheap; the inverse version inherits that same
property.

## Decision

**Ship importance sampling as the v0.8.3 inverse-inference baseline.**
MCMC promotion stays a v0.8.4+ candidate.

```python
def infer_posterior_envelope(
    measurements: tuple[MeasuredPressureFlowPoint, ...],
    *,
    polymer_family: PolymerFamily,
    column: ColumnGeometry,
    mobile_phase: MobilePhase,
    Q_for_envelope: float,
    n_samples: int = 2000,
    sigma_log_k_geom: float = 0.20,
    sigma_log_mu: float = 0.05,
    sigma_log_g_dn: float = 0.30,
    seed: Optional[int] = None,
) -> InferredPosteriorEnvelope:
    """Importance-sample the posterior over K_geom / μ / G_DN."""
```

The procedure:

1. **Forward MC draw.** Sample `n_samples` parameter triples from the
   prior (same lognormal priors as ADR-007).
2. **Per-sample likelihood.** For each draw, evaluate
   `compute_pressure_envelope` at every `Q_observed` and compute
   `p(ΔP_observed | sample) ∝ exp(-Σ_k (ΔP_pred,k − ΔP_obs,k)² /
   (2 σ_dP,k²))`.
3. **Importance weights.** Normalize to `w_i = L_i / Σ L_j`.
4. **Effective sample size diagnostic.** `ESS = 1 / Σ w_i²`. Flag
   when `ESS < 0.10 · n_samples` — that's when MCMC would actually
   help; v0.8.3 ships a clear warning rather than silently producing
   poor estimates.
5. **Posterior moments + bands.** Weighted mean / quantiles of the
   parameter draws AND of the envelope outputs at `Q_for_envelope`.

### Why importance sampling for v0.8.3

1. **No new dependencies.** numpy + the existing forward-MC module.
2. **Determinism.** Given a seed and prior, the posterior is exact —
   reproducibility is trivial.
3. **No warm-up / burn-in tuning.** Important for a CI-friendly module.
4. **ESS gives a clean upgrade signal.** When ESS drops, the user is
   told to either widen priors, supply better measurement noise σ, or
   wait for v0.8.4 MCMC.

### Why not MCMC in v0.8.3

- pymc / arviz are dev-time deps (and gated by Python pin per CLAUDE.md
  ADR-001 / ADR-002), but the *runtime* import cost is real (~30 s on
  cold venv) and would dominate test wall time.
- MCMC tuning (step size, mass matrix, target accept rate) introduces
  configuration surface that demands a richer test harness than a
  patch release supports.
- The 3-parameter posterior (K_geom, μ, G_DN) is low-dimensional and
  unimodal under the lognormal priors. Importance sampling is more
  than adequate here; MCMC's advantages dominate at higher
  dimensionality.

### Tier mapping

The posterior bands stay **SEMI_QUANTITATIVE** in v0.8.3. Promotion to
CALIBRATED_LOCAL requires:
1. The user explicitly registers the posterior into the
   `calibration_store` for the family + column pair (machinery
   already exists for K_geom; v0.8.3 adds a docstring example for
   the round-trip).
2. The wet-lab handshake — a separate run validating that the
   posterior predicts a held-out (Q, ΔP) pair within a wet-lab-defined
   tolerance. This step is user-side; v0.8.3 does not ship the
   automation.

## Out of scope

- **MCMC inverse inference** (v0.8.4+ candidate).
- **Auto-promotion of CALIBRATED_LOCAL tier** based on posterior fit
  alone — see "Tier mapping" above.
- **Posterior over ν** in the salt-modulated isotherm — the inverse
  envelope addresses K_geom / μ / G_DN. ν calibration via the
  isotherm-side `calibrated_locally` flag remains a separate user-side
  flow.
- **Hierarchical / multi-column inference.** Each column gets its own
  posterior in v0.8.3.

## References

- ADR-007 — Forward Monte Carlo Bayesian envelope (forward path).
- Robert, C.P. & Casella, G. (2004). *Monte Carlo Statistical Methods*, 2nd ed., §3.3 (Importance Sampling).
- Owen, A.B. (2013). *Monte Carlo theory, methods and examples*, ch. 9 (Importance Sampling and Effective Sample Size).
- Hoffman, M.D. & Gelman, A. (2014). The No-U-Turn Sampler. *J. Mach. Learn. Res.* 15. — context for the MCMC-deferred path.
