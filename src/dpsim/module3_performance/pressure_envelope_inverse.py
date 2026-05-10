"""Inverse Bayesian inference of the pressure envelope via importance sampling.

B-2o / W-047 — v0.8.3. Per ADR-010, ships the **inverse** counterpart
to ``pressure_envelope_mc.py``: given measured ``(Q_observed, ΔP_observed)``
pairs from a real run (or a manufacturer pressure-flow specification),
update the prior over K_geom / μ / G_DN to a posterior consistent with
the data and report posterior bands on the envelope outputs at a
user-specified ``Q_for_envelope``.

The implementation is importance sampling (NOT MCMC) — ADR-010
documents the choice. The procedure inherits the per-draw cost of
the v0.8.2 forward MC and adds only a per-sample likelihood call.

ESS (effective sample size) is reported as a diagnostic; when ESS
drops below 10 % of n_samples the helper emits a clear warning that
the posterior is concentrated (importance sampling fidelity drops)
and that v0.8.4+ MCMC is the upgrade path.

Tier mapping
-----------

Posterior bands stay SEMI_QUANTITATIVE in v0.8.3. CALIBRATED_LOCAL
promotion requires the user-side wet-lab handshake described in
ADR-010 §"Tier mapping" — v0.8.3 ships the *machinery*, not the
promotion.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, replace as _dc_replace
from typing import Optional

import numpy as np

from dpsim.core.mobile_phase import MobilePhase
from dpsim.datatypes import ModelEvidenceTier, PolymerFamily
from dpsim.module3_performance.family_kgeom import lookup_family_kgeom
from dpsim.module3_performance.hydrodynamics import ColumnGeometry
from dpsim.module3_performance.pressure_envelope import (
    compute_pressure_envelope,
)


# ─── Defaults — same anchors as ADR-007 forward path ────────────────────────


_K_GEOM_SIGMA_LOG: float = 0.20
_MU_SIGMA_LOG: float = 0.05
_G_DN_SIGMA_LOG: float = 0.30


# ─── Value types ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class MeasuredPressureFlowPoint:
    """One measured (Q, ΔP) point for posterior inference.

    Attributes
    ----------
    Q_m3_s :
        Measured volumetric flow rate [m³/s].
    dP_pa :
        Measured ΔP across the column [Pa].
    sigma_dP_pa :
        Measurement noise (1 σ) on ΔP [Pa]. Used in the Gaussian
        likelihood. Set to ~5–10 % of ``dP_pa`` for typical AKTA
        panel data; tighter bounds when fitting against a specification
        sheet.
    """

    Q_m3_s: float
    dP_pa: float
    sigma_dP_pa: float


@dataclass(frozen=True)
class InferredPosteriorEnvelope:
    """Posterior summary from importance-sampled inverse inference.

    Carries posterior moments / quantiles for the three parameters,
    posterior bands for the envelope outputs at ``Q_for_envelope``,
    and the ESS diagnostic.

    Attributes
    ----------
    n_samples :
        Number of draws used.
    effective_sample_size :
        ``1 / Σ w_i²``. When < 0.1 · n_samples, the posterior is
        peaky and importance-sampling fidelity drops; ``ess_warning``
        captures the recommendation.
    ess_warning :
        Human-readable warning string (empty when ESS is healthy).

    K_geom_p05, _p50, _p95 :
        Posterior quantiles of K_geom.
    mu_pa_s_p05, _p50, _p95 :
        Posterior quantiles of μ.
    G_DN_pa_p05, _p50, _p95 :
        Posterior quantiles of G_DN.

    Q_max_m3_s_p05, _p50, _p95 :
        Posterior bands on Q_max at ``Q_for_envelope``.
    dP_predicted_pa_p05, _p50, _p95 :
        Posterior bands on predicted ΔP.
    headroom_ratio_p05, _p50, _p95 :
        Posterior bands on Q_for_envelope / Q_max.
    p_blocker :
        Posterior P[headroom_ratio > 1.0].
    p_warning :
        Posterior P[headroom_ratio > 0.7].

    log_cov :
        Posterior log-space covariance matrix (3×3, parameter order
        [K_geom, μ, G_DN]). Suitable for round-trip into
        ``monte_carlo_pressure_envelope(log_cov=...)`` for
        predictive intervals at a NEW operating point.

    decision_tier :
        ``SEMI_QUANTITATIVE`` per ADR-010 §"Tier mapping". Promotion
        to CALIBRATED_LOCAL is wet-lab-driven and lives outside this
        function.
    """

    n_samples: int
    effective_sample_size: float
    ess_warning: str

    K_geom_p05: float
    K_geom_p50: float
    K_geom_p95: float
    mu_pa_s_p05: float
    mu_pa_s_p50: float
    mu_pa_s_p95: float
    G_DN_pa_p05: float
    G_DN_pa_p50: float
    G_DN_pa_p95: float

    Q_max_m3_s_p05: float
    Q_max_m3_s_p50: float
    Q_max_m3_s_p95: float
    dP_predicted_pa_p05: float
    dP_predicted_pa_p50: float
    dP_predicted_pa_p95: float
    headroom_ratio_p05: float
    headroom_ratio_p50: float
    headroom_ratio_p95: float
    p_blocker: float
    p_warning: float

    log_cov: np.ndarray

    decision_tier: ModelEvidenceTier


# ─── Weighted quantile helper ──────────────────────────────────────────────


def _weighted_quantiles(
    values: np.ndarray, weights: np.ndarray, qs: tuple[float, ...],
) -> tuple[float, ...]:
    """Return weighted quantiles for an array.

    Drops non-finite values and renormalizes; returns NaN per quantile
    when no finite values remain.
    """
    finite_mask = np.isfinite(values) & np.isfinite(weights)
    v = values[finite_mask]
    w = weights[finite_mask]
    if v.size == 0 or w.sum() <= 0.0:
        return tuple(float("nan") for _ in qs)
    w = w / w.sum()
    order = np.argsort(v)
    v_sorted = v[order]
    w_sorted = w[order]
    cum = np.cumsum(w_sorted)
    out: list[float] = []
    for q in qs:
        idx = int(np.searchsorted(cum, q))
        idx = min(max(idx, 0), v_sorted.size - 1)
        out.append(float(v_sorted[idx]))
    return tuple(out)


def _weighted_log_cov(
    log_samples: np.ndarray, weights: np.ndarray,
) -> np.ndarray:
    """Weighted covariance of log-space samples (rows = parameters)."""
    w = weights / weights.sum()
    mean = (log_samples * w).sum(axis=1)
    diff = log_samples - mean[:, np.newaxis]
    return diff @ (diff * w).T


# ─── Public API ────────────────────────────────────────────────────────────


def infer_posterior_envelope(
    measurements: tuple[MeasuredPressureFlowPoint, ...],
    *,
    polymer_family: PolymerFamily,
    column: ColumnGeometry,
    mobile_phase: MobilePhase,
    Q_for_envelope: float,
    n_samples: int = 2000,
    sigma_log_k_geom: float = _K_GEOM_SIGMA_LOG,
    sigma_log_mu: float = _MU_SIGMA_LOG,
    sigma_log_g_dn: float = _G_DN_SIGMA_LOG,
    seed: Optional[int] = None,
    G_DN_pa: Optional[float] = None,
    E_star_pa: Optional[float] = None,
    bead_d32_m: Optional[float] = None,
) -> InferredPosteriorEnvelope:
    """Importance-sample the posterior over (K_geom, μ, G_DN).

    Parameters
    ----------
    measurements :
        Non-empty tuple of ``MeasuredPressureFlowPoint``. Each carries
        a Q, a ΔP, and a measurement-noise σ.
    polymer_family, column, mobile_phase, Q_for_envelope :
        Envelope evaluation parameters. ``Q_for_envelope`` is where
        posterior envelope bands are reported (typically the user's
        target operating Q, separate from any of the measured Q's).
    n_samples :
        Number of importance draws. Default 2000 — empirically enough
        for ±5 % stable posterior quantile estimates with the default
        priors and 3–5 measurement points.
    sigma_log_* :
        Lognormal prior σ in log-space. Defaults from ADR-007.
    seed :
        Optional RNG seed for reproducibility.
    G_DN_pa, E_star_pa, bead_d32_m :
        Optional explicit overrides forwarded to each per-draw envelope
        call. Mirrors ``compute_pressure_envelope``.

    Returns
    -------
    InferredPosteriorEnvelope
        Posterior summary + ESS diagnostic.

    Raises
    ------
    ValueError
        If ``measurements`` is empty, or any ``sigma_dP_pa`` is ≤ 0.
    """
    if not measurements:
        raise ValueError("measurements must contain at least one point.")
    if n_samples < 100:
        raise ValueError(
            f"n_samples={n_samples} must be ≥ 100 for stable importance "
            "sampling. Use the forward MC for sub-100 draws."
        )
    for m in measurements:
        if m.sigma_dP_pa <= 0.0:
            raise ValueError(
                f"sigma_dP_pa={m.sigma_dP_pa!r} must be > 0."
            )

    rng = np.random.default_rng(seed)

    base_K_geom = float(lookup_family_kgeom(polymer_family).K_geom)
    g_dn_base = float(G_DN_pa) if G_DN_pa is not None else float(column.G_DN)
    from dpsim.core.viscosity import resolve_mobile_phase_viscosity
    nominal_mu = resolve_mobile_phase_viscosity(mobile_phase).mu_pa_s

    # ── Prior draws (lognormal multiplicative shocks) ────────────────────
    z_kg = rng.normal(0.0, sigma_log_k_geom, size=n_samples)
    z_mu = rng.normal(0.0, sigma_log_mu, size=n_samples)
    z_g = rng.normal(0.0, sigma_log_g_dn, size=n_samples)

    K_geom_draws = base_K_geom * np.exp(z_kg)
    mu_draws = nominal_mu * np.exp(z_mu)
    g_dn_draws = g_dn_base * np.exp(z_g)

    # ── Per-sample log-likelihood across all measurements ────────────────
    log_w = np.zeros(n_samples, dtype=float)

    for i in range(n_samples):
        cal_store = {
            polymer_family.value: {
                "K_geom": float(K_geom_draws[i]),
                "source": "is_draw",
            },
        }
        mp_i = _dc_replace(mobile_phase, custom_mu_pa_s=float(mu_draws[i]))
        ll = 0.0
        for m in measurements:
            try:
                env = compute_pressure_envelope(
                    polymer_family=polymer_family,
                    column=column,
                    mobile_phase=mp_i,
                    Q_set_m3_s=max(m.Q_m3_s, 1e-15),
                    G_DN_pa=float(g_dn_draws[i]),
                    E_star_pa=E_star_pa,
                    bead_d32_m=bead_d32_m,
                    calibration_store=cal_store,
                )
            except (ValueError, KeyError):
                ll = -np.inf
                break
            resid = (env.dP_predicted_pa - m.dP_pa) / m.sigma_dP_pa
            ll += -0.5 * resid * resid
        log_w[i] = ll

    # ── Normalize importance weights ───────────────────────────────────
    finite = np.isfinite(log_w)
    if not np.any(finite):
        raise ValueError(
            "All importance weights are -inf — every prior draw failed "
            "envelope evaluation. Check measurement Q range vs column "
            "geometry."
        )
    log_w_max = float(np.max(log_w[finite]))
    weights = np.where(finite, np.exp(log_w - log_w_max), 0.0)
    weights = weights / weights.sum()

    ess = float(1.0 / (weights * weights).sum())
    ess_warning = ""
    if ess < 0.10 * n_samples:
        ess_warning = (
            f"ESS={ess:.0f} is below 10% of n_samples ({n_samples}); "
            "the posterior is concentrated relative to the prior. "
            "Consider widening priors, supplying tighter sigma_dP_pa, "
            "or upgrading to MCMC (v0.8.4+ candidate)."
        )
        warnings.warn(ess_warning, stacklevel=2)

    # ── Posterior bands on parameters ───────────────────────────────────
    p_kg = _weighted_quantiles(K_geom_draws, weights, (0.05, 0.50, 0.95))
    p_mu = _weighted_quantiles(mu_draws, weights, (0.05, 0.50, 0.95))
    p_g = _weighted_quantiles(g_dn_draws, weights, (0.05, 0.50, 0.95))

    # ── Posterior log-space covariance for round-trip into forward MC ──
    log_samples = np.vstack([z_kg, z_mu, z_g])
    log_cov = _weighted_log_cov(log_samples, weights)

    # ── Posterior bands on envelope outputs at Q_for_envelope ──────────
    q_max_arr = np.empty(n_samples, dtype=float)
    dp_pred_arr = np.empty(n_samples, dtype=float)
    headroom_arr = np.empty(n_samples, dtype=float)
    for i in range(n_samples):
        if not finite[i]:
            q_max_arr[i] = np.nan
            dp_pred_arr[i] = np.nan
            headroom_arr[i] = np.nan
            continue
        cal_store = {
            polymer_family.value: {
                "K_geom": float(K_geom_draws[i]),
                "source": "is_draw",
            },
        }
        mp_i = _dc_replace(mobile_phase, custom_mu_pa_s=float(mu_draws[i]))
        try:
            env = compute_pressure_envelope(
                polymer_family=polymer_family,
                column=column,
                mobile_phase=mp_i,
                Q_set_m3_s=max(Q_for_envelope, 1e-15),
                G_DN_pa=float(g_dn_draws[i]),
                E_star_pa=E_star_pa,
                bead_d32_m=bead_d32_m,
                calibration_store=cal_store,
            )
            q_max_arr[i] = env.Q_max_m3_s
            dp_pred_arr[i] = env.dP_predicted_pa
            headroom_arr[i] = env.headroom_ratio
        except (ValueError, KeyError):
            q_max_arr[i] = np.nan
            dp_pred_arr[i] = np.nan
            headroom_arr[i] = np.nan

    p_qmax = _weighted_quantiles(q_max_arr, weights, (0.05, 0.50, 0.95))
    p_dp = _weighted_quantiles(dp_pred_arr, weights, (0.05, 0.50, 0.95))
    p_h = _weighted_quantiles(headroom_arr, weights, (0.05, 0.50, 0.95))

    # Tail probabilities under the posterior weights.
    finite_h = np.isfinite(headroom_arr)
    if np.any(finite_h):
        wh = weights[finite_h]
        wh = wh / wh.sum() if wh.sum() > 0 else wh
        h = headroom_arr[finite_h]
        p_blocker = float((wh * (h > 1.0).astype(float)).sum())
        p_warning = float((wh * (h > 0.7).astype(float)).sum())
    else:
        p_blocker = float("nan")
        p_warning = float("nan")

    return InferredPosteriorEnvelope(
        n_samples=n_samples,
        effective_sample_size=ess,
        ess_warning=ess_warning,
        K_geom_p05=p_kg[0], K_geom_p50=p_kg[1], K_geom_p95=p_kg[2],
        mu_pa_s_p05=p_mu[0], mu_pa_s_p50=p_mu[1], mu_pa_s_p95=p_mu[2],
        G_DN_pa_p05=p_g[0], G_DN_pa_p50=p_g[1], G_DN_pa_p95=p_g[2],
        Q_max_m3_s_p05=p_qmax[0],
        Q_max_m3_s_p50=p_qmax[1],
        Q_max_m3_s_p95=p_qmax[2],
        dP_predicted_pa_p05=p_dp[0],
        dP_predicted_pa_p50=p_dp[1],
        dP_predicted_pa_p95=p_dp[2],
        headroom_ratio_p05=p_h[0],
        headroom_ratio_p50=p_h[1],
        headroom_ratio_p95=p_h[2],
        p_blocker=p_blocker,
        p_warning=p_warning,
        log_cov=log_cov,
        decision_tier=ModelEvidenceTier.SEMI_QUANTITATIVE,
    )


__all__ = [
    "InferredPosteriorEnvelope",
    "MeasuredPressureFlowPoint",
    "infer_posterior_envelope",
]
