# ADR-011 — Correlated MC priors: covariance specification + drawing

**Status:** Accepted
**Date:** 2026-05-10
**Decision driver:** v0.8.3 W-049. ADR-007 §"Out of scope" listed
correlated priors as deferred:

> Correlated priors. v0.8.2 assumes K_geom, ν, μ, G_DN are independent.
> Real correlations (e.g. hot buffers shift both μ AND ν together) are
> second-order; document as a known limitation.

This ADR documents the v0.8.3 closure: an opt-in covariance matrix
override on `monte_carlo_pressure_envelope` so users with calibration
data showing a real cross-parameter correlation can supply it.

## Context

The forward MC at v0.8.2 samples K_geom, μ, G_DN independently. Two
classes of real-world correlation matter:

1. **Buffer-driven correlation between μ and K_geom-effective.** A hot
   buffer drops μ AND swells the bead matrix, which shifts the
   effective K_geom. The two move together along the temperature axis
   even if neither is causally tied to the other in the model.
2. **Bead-stiffness correlation between G_DN and K_geom-effective.**
   Stiffer beads pack to a different ε_b which shows up as a K_geom
   shift. Again, separate parameters in the model but the underlying
   physics drives both off the same property.

Independent sampling under-estimates these correlated draws when the
real underlying-property variance is allocated to both parameters
simultaneously. The result: independent MC may either over- or
under-state tail probabilities depending on the sign of the correlation.

A correlation-aware sampler costs essentially nothing extra: numpy's
`multivariate_normal` is the same per-call cost as 3 independent
normals.

## Decision

**Add an optional `log_cov: np.ndarray | None` argument to
`monte_carlo_pressure_envelope`.** When supplied, the MC draws come
from a multivariate normal in log-space with the user's covariance
matrix; when None, fall back to the v0.8.2 independent path.

```python
def monte_carlo_pressure_envelope(
    *,
    polymer_family: PolymerFamily,
    column: ColumnGeometry,
    mobile_phase: MobilePhase,
    Q_set_m3_s: float,
    n_samples: int = 500,
    sigma_log_k_geom: float = 0.20,
    sigma_log_mu: float = 0.05,
    sigma_log_g_dn: float = 0.30,
    log_cov: Optional[np.ndarray] = None,    # NEW (3×3, or None)
    seed: Optional[int] = None,
    ...
) -> MCEnvelopeBands:
```

### Convention

- Parameter order: `[log K_geom, log μ, log G_DN]`. Documented in the
  function docstring.
- When `log_cov` is supplied, the `sigma_log_*` arguments are
  **ignored** with a clear note in the docstring; users who want a
  diagonal can either omit `log_cov` or pass an explicit
  `np.diag([σ_kg², σ_μ², σ_g²])`.
- The covariance matrix MUST be symmetric and positive-semi-definite;
  the function raises `ValueError` on either failure (caught by an
  eigvalsh check ≥ 0).

### Defaults

No correlation in the default path — the v0.8.2 independent assumption
is preserved bit-for-bit when `log_cov is None`.

### Per-family + correlated stack-up

When B-2p (W-048) lands, family-specific σ_log_* defaults can land
under `log_cov` too: a family-specific `log_cov` registry could
ship, but v0.8.3 does NOT ship one — the family priors stay
diagonal in v0.8.3 because no published cross-correlations exist
per-family yet. Future v0.8.x or v0.9 work can extend.

## Consequences

- Users with a fitted covariance from posterior inference (B-2o /
  W-047) can pass that posterior covariance directly into the
  *forward* MC for predictive intervals at a *new* operating point.
  This is the natural Bayesian round-trip: posterior → predictive.
- Independent-sampling consumers see no behaviour change; the
  v0.8.2 contract is preserved.
- The covariance matrix structure is documented at the call site;
  no hidden defaults beyond the diagonal-σ literature anchors.

## Out of scope

- **Family-specific covariance registries** — v0.8.3 keeps family
  priors diagonal (B-2p / W-048).
- **Multi-step correlated draws** — see B-2r / W-050; that is a
  cross-step problem, not a cross-parameter one. Both the
  cross-parameter (this ADR) and cross-step (W-050) machinery can
  compose without conflict.
- **Posterior covariance sampling at high dimensionality.** When
  N_param ≫ 3, importance sampling fidelity drops. Out-of-scope
  for v0.8.3 since the parameter space is fixed-3 here.

## References

- ADR-007 — Forward Monte Carlo Bayesian envelope (the
  independent-sampling precedent).
- ADR-010 — Inverse pressure-envelope inference (importance sampling
  produces the posterior covariance that this ADR's mechanism
  consumes).
- Murphy, K.P. (2012). *Machine Learning: A Probabilistic
  Perspective*, §4.1 (Multivariate Gaussian).
