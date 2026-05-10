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


# ─── Multi-step coupled MC (B-2r / W-050, v0.8.3) ───────────────────────────


@dataclass(frozen=True)
class StepProgramMCResult:
    """Coupled MC result across a multi-step recipe program.

    Per-step :class:`MCEnvelopeBands` with the **same parameter draws**
    used across all steps — so cross-step correlation is preserved
    (a high-K_geom draw produces consistently lower headroom across
    load + wash + elute, which an independent per-step MC would miss).

    Attributes
    ----------
    step_names :
        Tuple of step names matching the input program.
    per_step_bands :
        ``MCEnvelopeBands`` for each step, ordered to match
        ``step_names``.
    worst_step_p_blocker :
        ``max_i p_blocker_i`` — the worst-step blocker probability,
        the headline "is this recipe risky" diagnostic.
    worst_step_index :
        Index of the step that drives ``worst_step_p_blocker``.
    n_samples :
        Number of MC draws (same across all steps).
    decision_tier :
        ``SEMI_QUANTITATIVE`` per ADR-007.
    """

    step_names: tuple[str, ...]
    per_step_bands: tuple[MCEnvelopeBands, ...]
    worst_step_p_blocker: float
    worst_step_index: int
    n_samples: int
    decision_tier: ModelEvidenceTier


def monte_carlo_step_program(
    *,
    polymer_family: PolymerFamily,
    column: ColumnGeometry,
    step_program: tuple,
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
) -> StepProgramMCResult:
    """MC propagation across a multi-step recipe with shared draws.

    Draw N parameter triples ONCE, then evaluate every step in
    ``step_program`` under the same draws. Independent per-step MC
    would miss the cross-step correlation (a "bad" K_geom draw drives
    all steps simultaneously); this function preserves it.

    Parameters
    ----------
    polymer_family, column :
        Same shape as :func:`monte_carlo_pressure_envelope`.
    step_program :
        Tuple of ``PressureStep``-like objects (each with ``name``,
        ``Q_m3_s``, ``mobile_phase`` attributes). Typed loosely
        because :class:`dpsim.optimization.objectives.PressureStep`
        lives in the optimization layer; the expected shape is
        documented but not formally typed here to avoid a hard
        dependency.
    n_samples, sigma_log_*, seed, use_family_priors, log_cov :
        Same as :func:`monte_carlo_pressure_envelope`.
    G_DN_pa, E_star_pa, bead_d32_m :
        Optional explicit overrides. Applied per-step (same value
        across the program — recipe steps don't change column physics).

    Returns
    -------
    StepProgramMCResult
        Per-step bands + worst-step blocker probability.

    Raises
    ------
    ValueError
        If ``step_program`` is empty or any step lacks the expected
        ``Q_m3_s`` / ``mobile_phase`` attribute.
    """
    if not step_program:
        raise ValueError("step_program must contain at least one step.")
    for step in step_program:
        for attr in ("name", "Q_m3_s", "mobile_phase"):
            if not hasattr(step, attr):
                raise ValueError(
                    f"step_program element missing attribute {attr!r}; "
                    f"got {type(step).__name__}."
                )

    rng = np.random.default_rng(seed)

    # ── Resolve effective σ exactly the same way as the single-step MC.
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

    base_K_geom = lookup_family_kgeom(polymer_family).K_geom
    g_dn_base = float(G_DN_pa) if G_DN_pa is not None else float(column.G_DN)

    # ── Sample shocks ONCE — shared across all steps ───────────────────
    if log_cov is not None:
        cov = np.asarray(log_cov, dtype=float)
        if cov.shape != (3, 3):
            raise ValueError(
                f"log_cov must be 3×3; got shape {cov.shape}."
            )
        if not np.allclose(cov, cov.T, atol=1e-12):
            raise ValueError("log_cov must be symmetric.")
        eigs = np.linalg.eigvalsh(cov)
        if np.min(eigs) < -1e-9:
            raise ValueError(
                "log_cov must be positive-semi-definite "
                f"(min eigvalue = {float(np.min(eigs))!r})."
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

    # Pre-compute draw-by-parameter arrays; shared across step loop.
    K_geom_draws = base_K_geom * np.exp(z_kg)
    g_dn_draws = g_dn_base * np.exp(z_g)
    mu_factors = np.exp(z_mu)

    # ── Per-step aggregation ───────────────────────────────────────────
    from dpsim.core.viscosity import resolve_mobile_phase_viscosity

    step_names: list[str] = []
    per_step_bands: list[MCEnvelopeBands] = []

    for step in step_program:
        step_names.append(str(step.name))
        nominal_mu = resolve_mobile_phase_viscosity(step.mobile_phase).mu_pa_s
        mu_draws = nominal_mu * mu_factors

        Q_max_arr = np.empty(n_samples, dtype=float)
        dP_pred_arr = np.empty(n_samples, dtype=float)
        dP_op_arr = np.empty(n_samples, dtype=float)
        headroom_arr = np.empty(n_samples, dtype=float)

        for i in range(n_samples):
            cal_store = {
                polymer_family.value: {
                    "K_geom": float(K_geom_draws[i]),
                    "source": "mc_draw",
                },
            }
            mp_i = _dc_replace(
                step.mobile_phase, custom_mu_pa_s=float(mu_draws[i]),
            )
            try:
                env = compute_pressure_envelope(
                    polymer_family=polymer_family,
                    column=column,
                    mobile_phase=mp_i,
                    Q_set_m3_s=max(float(step.Q_m3_s), 1.0e-15),
                    G_DN_pa=float(g_dn_draws[i]),
                    E_star_pa=E_star_pa,
                    bead_d32_m=bead_d32_m,
                    calibration_store=cal_store,
                )
                Q_max_arr[i] = env.Q_max_m3_s
                dP_pred_arr[i] = env.dP_predicted_pa
                dP_op_arr[i] = env.dP_max_operational_pa
                headroom_arr[i] = env.headroom_ratio
            except (ValueError, KeyError):
                Q_max_arr[i] = np.nan
                dP_pred_arr[i] = np.nan
                dP_op_arr[i] = np.nan
                headroom_arr[i] = np.nan

        p05_q, p50_q, p95_q = _quantiles(Q_max_arr)
        p05_d, p50_d, p95_d = _quantiles(dP_pred_arr)
        p05_o, p50_o, p95_o = _quantiles(dP_op_arr)
        p05_h, p50_h, p95_h = _quantiles(headroom_arr)
        finite_h = headroom_arr[np.isfinite(headroom_arr)]
        if finite_h.size > 0:
            p_b = float(np.mean(finite_h > 1.0))
            p_w = float(np.mean(finite_h > 0.7))
        else:
            p_b = float("nan")
            p_w = float("nan")
        per_step_bands.append(MCEnvelopeBands(
            n_samples=n_samples,
            Q_max_m3_s_p05=p05_q, Q_max_m3_s_p50=p50_q, Q_max_m3_s_p95=p95_q,
            dP_predicted_pa_p05=p05_d,
            dP_predicted_pa_p50=p50_d,
            dP_predicted_pa_p95=p95_d,
            dP_max_operational_pa_p05=p05_o,
            dP_max_operational_pa_p50=p50_o,
            dP_max_operational_pa_p95=p95_o,
            headroom_ratio_p05=p05_h,
            headroom_ratio_p50=p50_h,
            headroom_ratio_p95=p95_h,
            p_blocker=p_b,
            p_warning=p_w,
            decision_tier=ModelEvidenceTier.SEMI_QUANTITATIVE,
        ))

    p_blockers = [b.p_blocker for b in per_step_bands]
    finite_pb = [(i, p) for i, p in enumerate(p_blockers) if np.isfinite(p)]
    if finite_pb:
        worst_idx, worst_p = max(finite_pb, key=lambda iv: iv[1])
    else:
        worst_idx, worst_p = 0, float("nan")

    return StepProgramMCResult(
        step_names=tuple(step_names),
        per_step_bands=tuple(per_step_bands),
        worst_step_p_blocker=worst_p,
        worst_step_index=worst_idx,
        n_samples=n_samples,
        decision_tier=ModelEvidenceTier.SEMI_QUANTITATIVE,
    )


__all__ = [
    "FamilyMCPrior",
    "MCEnvelopeBands",
    "StepProgramMCResult",
    "lookup_family_mc_prior",
    "monte_carlo_pressure_envelope",
    "monte_carlo_step_program",
]
