"""Forward Monte Carlo wrapper around ``compute_pressure_envelope``.

B-2n / W-043 — v0.8.2. Per ADR-007, samples lognormal multiplicative
errors on K_geom, ν / K_a, μ, and G_DN, runs the deterministic envelope
per draw, and returns P05 / P50 / P95 of the key outputs plus the
probability that the operating point exceeds the BLOCKER threshold.

Use this when the user wants tail-probability information ("what is
the chance my recipe blockers at this Q?") rather than the
deterministic policy band. The deterministic envelope remains the
preferred default for fast pre-flight previews; MC is opt-in.

Out of scope (per ADR-007): inverse Bayesian inference, correlated
priors, family-specific defaults, multi-step coupled propagation.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace as _dc_replace
from typing import Optional

import numpy as np

from dpsim.core.mobile_phase import MobilePhase
from dpsim.datatypes import ModelEvidenceTier, PolymerFamily
from dpsim.module3_performance.family_kgeom import lookup_family_kgeom
from dpsim.module3_performance.hydrodynamics import ColumnGeometry
from dpsim.module3_performance.pressure_envelope import (
    compute_pressure_envelope,
)


# ─── Default priors (ADR-007 §"prior choices") ──────────────────────────────


_K_GEOM_SIGMA_LOG: float = 0.20
_NU_SIGMA_LOG: float = 0.15
_MU_SIGMA_LOG: float = 0.05
_G_DN_SIGMA_LOG: float = 0.30


# ─── Per-family prior overrides (B-2p / W-048, v0.8.3) ──────────────────────


@dataclass(frozen=True)
class FamilyMCPrior:
    """Per-family lognormal prior σ_log values for the forward MC.

    Attributes
    ----------
    sigma_log_k_geom :
        K_geom log-space σ. Defaults to the literature mid-range (0.20)
        when the family is not in the registry.
    sigma_log_mu :
        μ log-space σ. Default 0.05 — μ uncertainty is family-independent
        so most entries leave this at the default.
    sigma_log_g_dn :
        G_DN log-space σ. Bead-stiffness uncertainty varies the most
        across families; this is where per-family priors matter most.
    notes :
        Free-form provenance for the chosen σ values.
    """

    sigma_log_k_geom: float = _K_GEOM_SIGMA_LOG
    sigma_log_mu: float = _MU_SIGMA_LOG
    sigma_log_g_dn: float = _G_DN_SIGMA_LOG
    notes: str = ""


# Per-family priors. Values reflect the ranges typically reported in
# the chromatography literature for lot-to-lot variation, packing
# variability, and bead-modulus measurement scatter. Conservative
# choices when published data is sparse.
_FAMILY_MC_PRIORS: dict[str, FamilyMCPrior] = {
    PolymerFamily.AGAROSE.value: FamilyMCPrior(
        sigma_log_k_geom=0.18,
        sigma_log_g_dn=0.25,
        notes="Sepharose-class agarose: tight K_geom across lots; "
        "G_DN tracks the agarose-content × thermal-history scatter.",
    ),
    PolymerFamily.AGAROSE_CHITOSAN.value: FamilyMCPrior(
        sigma_log_k_geom=0.20,
        sigma_log_g_dn=0.35,
        notes="Composite IPN: dual-network modulus has higher scatter "
        "from chitosan crosslink-density variability.",
    ),
    PolymerFamily.CELLULOSE.value: FamilyMCPrior(
        sigma_log_k_geom=0.22,
        sigma_log_g_dn=0.30,
        notes="Cellulose: porosity and surface area more variable "
        "between vendors than agarose.",
    ),
    PolymerFamily.PLGA.value: FamilyMCPrior(
        sigma_log_k_geom=0.30,
        sigma_log_g_dn=0.40,
        notes="Solid PLGA microspheres: K_geom and G_DN both heavily "
        "process-dependent — the most uncertain family.",
    ),
    PolymerFamily.ALGINATE.value: FamilyMCPrior(
        sigma_log_k_geom=0.25,
        sigma_log_g_dn=0.45,
        notes="Calcium-alginate: G_DN strongly depends on M/G ratio + "
        "crosslink density — highest stiffness scatter of the families.",
    ),
}


def lookup_family_mc_prior(family: PolymerFamily) -> FamilyMCPrior:
    """Return the per-family prior or the default mid-range when missing."""
    return _FAMILY_MC_PRIORS.get(family.value, FamilyMCPrior())


@dataclass(frozen=True)
class MCEnvelopeBands:
    """Forward-MC summary bands for the pressure envelope.

    Each scalar output of the deterministic envelope gains a P05 / P50 /
    P95 triple. Tail probabilities (``p_blocker``, ``p_warning``) are
    convenience derivatives of the headroom band.

    Attributes
    ----------
    n_samples :
        Number of MC draws.
    Q_max_m3_s_p05, _p50, _p95 :
        Operational ceiling quantiles [m³/s].
    dP_predicted_pa_p05, _p50, _p95 :
        Predicted ΔP quantiles [Pa].
    dP_max_operational_pa_p05, _p50, _p95 :
        Operational ΔP ceiling quantiles [Pa].
    headroom_ratio_p05, _p50, _p95 :
        ``Q_set / Q_max`` quantiles.
    p_blocker :
        Fraction of draws with ``headroom_ratio > 1.0``.
    p_warning :
        Fraction of draws with ``headroom_ratio > 0.7``.
    decision_tier :
        SEMI_QUANTITATIVE — the bands reflect priors, not posteriors.
    """

    n_samples: int
    Q_max_m3_s_p05: float
    Q_max_m3_s_p50: float
    Q_max_m3_s_p95: float
    dP_predicted_pa_p05: float
    dP_predicted_pa_p50: float
    dP_predicted_pa_p95: float
    dP_max_operational_pa_p05: float
    dP_max_operational_pa_p50: float
    dP_max_operational_pa_p95: float
    headroom_ratio_p05: float
    headroom_ratio_p50: float
    headroom_ratio_p95: float
    p_blocker: float
    p_warning: float
    decision_tier: ModelEvidenceTier


def _quantiles(values: np.ndarray) -> tuple[float, float, float]:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return float("nan"), float("nan"), float("nan")
    return (
        float(np.quantile(finite, 0.05)),
        float(np.quantile(finite, 0.50)),
        float(np.quantile(finite, 0.95)),
    )


def monte_carlo_pressure_envelope(
    *,
    polymer_family: PolymerFamily,
    column: ColumnGeometry,
    mobile_phase: MobilePhase,
    Q_set_m3_s: float,
    n_samples: int = 500,
    sigma_log_k_geom: Optional[float] = None,
    sigma_log_mu: Optional[float] = None,
    sigma_log_g_dn: Optional[float] = None,
    seed: Optional[int] = None,
    G_DN_pa: Optional[float] = None,
    E_star_pa: Optional[float] = None,
    bead_d32_m: Optional[float] = None,
    use_family_priors: bool = False,
    log_cov: Optional[np.ndarray] = None,
) -> MCEnvelopeBands:
    """Forward MC propagation per ADR-007.

    Draws ``n_samples`` lognormal multiplicative errors on K_geom
    (via ``calibration_store`` injection), μ (via a custom
    ``MobilePhase.custom_mu_pa_s`` override), and G_DN (via the
    ``G_DN_pa`` argument to ``compute_pressure_envelope``).

    Parameters
    ----------
    polymer_family, column, mobile_phase, Q_set_m3_s :
        Same shape as ``compute_pressure_envelope``.
    n_samples :
        MC draw count. Default 500.
    sigma_log_k_geom, sigma_log_mu, sigma_log_g_dn :
        Lognormal σ in log-space. ``None`` (default) resolves to:
        - ``use_family_priors=True``: per-family registry value
          via :func:`lookup_family_mc_prior`. (B-2p / W-048, v0.8.3)
        - ``use_family_priors=False``: literature-anchored mid-range
          (ADR-007 defaults: 0.20 / 0.05 / 0.30).
        Explicit floats override the family / default lookup.
    use_family_priors :
        When True (and any σ_log_* is ``None``), resolve the missing
        σ values from the per-family registry. Default ``False`` —
        v0.8.2 / ADR-007 backwards-compatible behaviour.
    log_cov :
        Optional 3×3 log-space covariance matrix per ADR-011
        (B-2q / W-049, v0.8.3). Parameter order ``[K_geom, μ, G_DN]``.
        When supplied, draws come from a multivariate normal in
        log-space and the ``sigma_log_*`` arguments are IGNORED with
        a clear note. Must be symmetric and positive-semi-definite.
    seed :
        Optional RNG seed for reproducibility.
    G_DN_pa, E_star_pa, bead_d32_m :
        Optional explicit overrides forwarded to each per-draw envelope
        call. When ``G_DN_pa`` is supplied, the lognormal error on
        G_DN scales the override; otherwise it scales ``column.G_DN``.

    Returns
    -------
    MCEnvelopeBands
        Quantile bands + tail probabilities + tier.
    """
    if n_samples < 10:
        raise ValueError(f"n_samples={n_samples} must be ≥ 10.")
    rng = np.random.default_rng(seed)

    # ── Resolve effective σ values per ADR-007 / W-048 / W-049 ─────────
    if use_family_priors:
        family_prior = lookup_family_mc_prior(polymer_family)
        eff_sigma_kg = (
            float(sigma_log_k_geom)
            if sigma_log_k_geom is not None
            else family_prior.sigma_log_k_geom
        )
        eff_sigma_mu = (
            float(sigma_log_mu)
            if sigma_log_mu is not None
            else family_prior.sigma_log_mu
        )
        eff_sigma_g = (
            float(sigma_log_g_dn)
            if sigma_log_g_dn is not None
            else family_prior.sigma_log_g_dn
        )
    else:
        eff_sigma_kg = (
            float(sigma_log_k_geom)
            if sigma_log_k_geom is not None
            else _K_GEOM_SIGMA_LOG
        )
        eff_sigma_mu = (
            float(sigma_log_mu) if sigma_log_mu is not None else _MU_SIGMA_LOG
        )
        eff_sigma_g = (
            float(sigma_log_g_dn)
            if sigma_log_g_dn is not None
            else _G_DN_SIGMA_LOG
        )

    # Resolve baseline G_DN that we'll multiplicatively perturb.
    g_dn_base = float(G_DN_pa) if G_DN_pa is not None else float(column.G_DN)

    # Resolve baseline K_geom for this family — we perturb absolute,
    # not factor, so each draw passes a concrete K_geom override
    # through calibration_store["K_geom"].
    base_K_geom = lookup_family_kgeom(polymer_family).K_geom

    # Resolve baseline μ for the lognormal perturb anchor.
    from dpsim.core.viscosity import resolve_mobile_phase_viscosity
    nominal_mu = resolve_mobile_phase_viscosity(mobile_phase).mu_pa_s

    # ── Sample log-space shocks (B-2q / W-049: multivariate path) ──────
    if log_cov is not None:
        cov = np.asarray(log_cov, dtype=float)
        if cov.shape != (3, 3):
            raise ValueError(
                f"log_cov must be 3×3 (parameter order [K_geom, μ, G_DN]); "
                f"got shape {cov.shape}."
            )
        if not np.allclose(cov, cov.T, atol=1e-12):
            raise ValueError("log_cov must be symmetric.")
        eigs = np.linalg.eigvalsh(cov)
        if np.min(eigs) < -1e-9:
            raise ValueError(
                f"log_cov must be positive-semi-definite (min eigvalue "
                f"= {float(np.min(eigs))!r})."
            )
        draws = rng.multivariate_normal(
            mean=np.zeros(3), cov=cov, size=n_samples,
        )
        z_kg = draws[:, 0]
        z_mu = draws[:, 1]
        z_g = draws[:, 2]
    else:
        z_kg = rng.normal(0.0, eff_sigma_kg, size=n_samples)
        z_mu = rng.normal(0.0, eff_sigma_mu, size=n_samples)
        z_g = rng.normal(0.0, eff_sigma_g, size=n_samples)

    Q_max_arr = np.empty(n_samples, dtype=float)
    dP_pred_arr = np.empty(n_samples, dtype=float)
    dP_op_arr = np.empty(n_samples, dtype=float)
    headroom_arr = np.empty(n_samples, dtype=float)

    for i in range(n_samples):
        # Multiplicative shocks.
        kg_factor = float(np.exp(z_kg[i]))
        mu_i = float(nominal_mu * np.exp(z_mu[i]))
        g_dn_i = float(g_dn_base * np.exp(z_g[i]))

        # K_geom shock via calibration_store override (concrete value,
        # since the calibration_store contract is K_geom, not factor).
        cal_store = {
            polymer_family.value: {
                "K_geom": float(base_K_geom * kg_factor),
                "source": "mc_draw",
            },
        }
        # μ shock via a perturbed MobilePhase with custom override.
        mp_i = _dc_replace(mobile_phase, custom_mu_pa_s=mu_i)

        try:
            env = compute_pressure_envelope(
                polymer_family=polymer_family,
                column=column,
                mobile_phase=mp_i,
                Q_set_m3_s=Q_set_m3_s,
                G_DN_pa=g_dn_i,
                E_star_pa=E_star_pa,
                bead_d32_m=bead_d32_m,
                calibration_store=cal_store,
            )
        except (ValueError, KeyError):
            Q_max_arr[i] = np.nan
            dP_pred_arr[i] = np.nan
            dP_op_arr[i] = np.nan
            headroom_arr[i] = np.nan
            continue

        Q_max_arr[i] = env.Q_max_m3_s
        dP_pred_arr[i] = env.dP_predicted_pa
        dP_op_arr[i] = env.dP_max_operational_pa
        headroom_arr[i] = env.headroom_ratio

    p05_qmax, p50_qmax, p95_qmax = _quantiles(Q_max_arr)
    p05_dp, p50_dp, p95_dp = _quantiles(dP_pred_arr)
    p05_op, p50_op, p95_op = _quantiles(dP_op_arr)
    p05_h, p50_h, p95_h = _quantiles(headroom_arr)

    finite_h = headroom_arr[np.isfinite(headroom_arr)]
    if finite_h.size > 0:
        p_blocker = float(np.mean(finite_h > 1.0))
        p_warning = float(np.mean(finite_h > 0.7))
    else:
        p_blocker = float("nan")
        p_warning = float("nan")

    return MCEnvelopeBands(
        n_samples=n_samples,
        Q_max_m3_s_p05=p05_qmax,
        Q_max_m3_s_p50=p50_qmax,
        Q_max_m3_s_p95=p95_qmax,
        dP_predicted_pa_p05=p05_dp,
        dP_predicted_pa_p50=p50_dp,
        dP_predicted_pa_p95=p95_dp,
        dP_max_operational_pa_p05=p05_op,
        dP_max_operational_pa_p50=p50_op,
        dP_max_operational_pa_p95=p95_op,
        headroom_ratio_p05=p05_h,
        headroom_ratio_p50=p50_h,
        headroom_ratio_p95=p95_h,
        p_blocker=p_blocker,
        p_warning=p_warning,
        # ADR-007: MC bands stay SEMI_QUANTITATIVE — they reflect
        # priors, not measured posteriors. Promotion to CALIBRATED_LOCAL
        # is wet-lab driven and lives in v0.9 with inverse inference.
        decision_tier=ModelEvidenceTier.SEMI_QUANTITATIVE,
    )


__all__ = ["MCEnvelopeBands", "monte_carlo_pressure_envelope"]
