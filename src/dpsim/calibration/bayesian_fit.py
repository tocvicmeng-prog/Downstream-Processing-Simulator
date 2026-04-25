"""Optional Bayesian posterior fitting via pymc/NUTS (G4 of P5++).

v0.3.1 module. Provides :func:`fit_langmuir_posterior` — a NUTS-based
Bayesian fit of the single-component Langmuir isotherm

    q* = q_max · K_L · C / (1 + K_L · C)

from a list of :class:`~dpsim.assay_record.AssayRecord` objects (or
``IsothermPoint`` tuples). The returned :class:`PosteriorSamples`
carries the posterior covariance (Σ via the joint chain), so G2's
``run_mc()`` can sample with the multivariate-normal path automatically.

The pymc dependency is **optional**. The base ``dpsim`` install does not
require pymc. Calling :func:`fit_langmuir_posterior` without pymc
installed raises a clear :class:`PymcNotInstalledError` with the
remediation command. Install via:

.. code-block:: shell

   pip install dpsim[bayesian]

Convergence gates (mandatory, per SA-Q3 / D-047):

* **R-hat** < 1.05 on every fitted parameter.
* **ESS** > N_total / 4 on every fitted parameter.
* **Divergence rate** < 1 % of post-warmup samples.

A failure on any gate raises :class:`BayesianFitConvergenceError`.

Reference: `docs/handover/ARCH_v0_7_P5plusplus_DECOMPOSITION.md` § 4.1.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np

from .calibration_data import CalibrationEntry
from .posterior_samples import PosteriorSamples

if TYPE_CHECKING:
    pass

logger = logging.getLogger("dpsim.calibration.bayesian_fit")


class PymcNotInstalledError(ImportError):
    """Raised when fit_langmuir_posterior is called without pymc installed."""


class BayesianFitConvergenceError(RuntimeError):
    """Raised when NUTS sampling fails any of the mandatory convergence gates.

    Attributes
    ----------
    r_hat : dict[str, float]
        Per-parameter R-hat values.
    ess : dict[str, float]
        Per-parameter effective sample sizes.
    divergence_rate : float
        Fraction of post-warmup draws that diverged.
    failures : list[str]
        Human-readable list of which gates failed.
    """

    def __init__(
        self,
        r_hat: dict[str, float],
        ess: dict[str, float],
        divergence_rate: float,
        failures: list[str],
    ) -> None:
        self.r_hat = r_hat
        self.ess = ess
        self.divergence_rate = divergence_rate
        self.failures = failures
        super().__init__(
            "Bayesian fit failed convergence gates: " + "; ".join(failures)
        )


@dataclass
class IsothermPoint:
    """One (C, q) isotherm measurement.

    Used as a lightweight alternative to :class:`AssayRecord` when the
    caller already has cleaned (concentration, loading) pairs.
    """

    concentration: float       # [mol/m^3]
    loading: float             # [mol/m^3]
    measurement_std: float = 0.0


def pymc_available() -> bool:
    """Return True iff pymc is importable in the current environment."""
    try:
        import pymc  # noqa: F401
        import arviz  # noqa: F401
    except ImportError:
        return False
    return True


def _require_pymc() -> tuple[Any, Any]:
    """Lazy-import pymc + arviz, raising :class:`PymcNotInstalledError` otherwise."""
    try:
        import arviz as az
        import pymc as pm
    except ImportError as exc:
        raise PymcNotInstalledError(
            "fit_langmuir_posterior requires pymc + arviz. "
            "Install via: pip install dpsim[bayesian]"
        ) from exc
    return pm, az


def _assays_to_points(assay_data: list[Any]) -> list[IsothermPoint]:
    """Coerce a heterogeneous list (AssayRecord | IsothermPoint | tuple) to points.

    For ``AssayRecord``: each replicate becomes one IsothermPoint, with
    concentration pulled from ``process_conditions["concentration_mol_m3"]``
    and loading taken from the replicate value. The replicate's ``std``
    propagates as ``measurement_std``.
    """
    points: list[IsothermPoint] = []
    for item in assay_data:
        if isinstance(item, IsothermPoint):
            points.append(item)
            continue
        if isinstance(item, tuple) and len(item) >= 2:
            std = float(item[2]) if len(item) >= 3 else 0.0
            points.append(IsothermPoint(float(item[0]), float(item[1]), std))
            continue
        # Duck-type AssayRecord
        replicates = getattr(item, "replicates", None)
        conditions = getattr(item, "process_conditions", None)
        if replicates is None or conditions is None:
            raise TypeError(
                f"Cannot coerce {type(item).__name__} to IsothermPoint; "
                "expected AssayRecord, IsothermPoint, or (C, q[, std]) tuple."
            )
        C = float(conditions.get("concentration_mol_m3", 0.0))
        for r in replicates:
            if getattr(r, "flag", "") == "outlier":
                continue
            points.append(
                IsothermPoint(C, float(r.value), float(getattr(r, "std", 0.0)))
            )
    if not points:
        raise ValueError("No isotherm points after coercion (assay_data empty?)")
    return points


def _build_calibration_entries(
    points: list[IsothermPoint],
    posterior_means: dict[str, float],
    posterior_stds: dict[str, float],
) -> list[CalibrationEntry]:
    """One CalibrationEntry per fitted parameter (for provenance)."""
    n_points = len(points)
    return [
        CalibrationEntry(
            profile_key="bayesian_langmuir_fit",
            parameter_name=name,
            measured_value=float(posterior_means[name]),
            units="mol/m^3" if name == "q_max" else "m^3/mol",
            measurement_type="bayesian_NUTS",
            confidence="measured",
            source_reference=f"NUTS fit on {n_points} isotherm points",
            target_module="M3",
            fit_method="bayesian",
            posterior_uncertainty=float(posterior_stds[name]),
        )
        for name in ("q_max", "K_L")
    ]


_DEFAULT_PRIOR: dict[str, tuple[float, float]] = {
    "q_max": (50.0, 50.0),   # weakly-informative: mean=50 mol/m^3, σ=50
    "K_L": (1e-3, 1e-3),     # weakly-informative on K_L [m^3/mol]
}


def fit_langmuir_posterior(
    assay_data: list[Any],
    prior: dict[str, tuple[float, float]] | None = None,
    n_chains: int = 4,
    n_samples: int = 1000,
    n_tune: int = 1000,
    target_accept: float = 0.95,
    seed: int = 42,
    rhat_threshold: float = 1.05,
    ess_threshold_fraction: float = 0.25,
    divergence_threshold: float = 0.01,
) -> PosteriorSamples:
    """Fit q_max, K_L from an isotherm assay using NUTS.

    Parameters
    ----------
    assay_data : list
        Heterogeneous list of :class:`AssayRecord`, :class:`IsothermPoint`,
        or ``(C, q)`` / ``(C, q, std)`` tuples.
    prior : dict[str, tuple[float, float]] | None
        Optional override of the default weakly-informative prior. Keys
        ``"q_max"`` and ``"K_L"``; values are ``(mean, std)`` of the
        log-normal prior on each parameter (specified on the natural
        scale; converted to log-scale internally).
    n_chains : int
        Number of independent MCMC chains for R-hat.
    n_samples : int
        Post-warmup draws per chain.
    n_tune : int
        Warmup (tuning) draws per chain.
    target_accept : float
        NUTS dual-averaging target acceptance probability.
    seed : int
        RNG seed for reproducibility.
    rhat_threshold : float
        Fail the run if any parameter's R-hat exceeds this. Default 1.05
        per SA-Q3.
    ess_threshold_fraction : float
        Fail the run if any parameter's ESS < ``ess_threshold_fraction
        * n_chains * n_samples``. Default 0.25.
    divergence_threshold : float
        Fail the run if the divergence rate exceeds this fraction of
        post-warmup draws. Default 0.01 (1 %).

    Returns
    -------
    PosteriorSamples
        Mean / std / covariance over (q_max, K_L), with provenance
        :class:`CalibrationEntry` objects in
        ``source_calibration_entries``. Use
        :meth:`PosteriorSamples.draw` with ``method="auto"`` (or
        ``"multivariate_normal"``) to sample from the joint posterior.

    Raises
    ------
    PymcNotInstalledError
        If pymc + arviz are not importable.
    BayesianFitConvergenceError
        If R-hat / ESS / divergence gates fail.
    ValueError
        If ``assay_data`` yields no usable points.
    """
    pm, az = _require_pymc()

    points = _assays_to_points(assay_data)
    C_obs = np.asarray([p.concentration for p in points], dtype=float)
    q_obs = np.asarray([p.loading for p in points], dtype=float)
    q_std_obs = np.asarray([p.measurement_std for p in points], dtype=float)

    used_prior = dict(_DEFAULT_PRIOR)
    if prior:
        for key, value in prior.items():
            if key not in used_prior:
                raise ValueError(
                    f"Unknown prior parameter {key!r}; expected one of {list(used_prior)}"
                )
            used_prior[key] = (float(value[0]), float(value[1]))

    log_q_max_mu = math.log(used_prior["q_max"][0])
    log_q_max_sigma = used_prior["q_max"][1] / used_prior["q_max"][0]
    log_K_L_mu = math.log(used_prior["K_L"][0])
    log_K_L_sigma = used_prior["K_L"][1] / used_prior["K_L"][0]

    measurement_sigma_default = max(float(np.std(q_obs)) * 0.1, 1e-6)
    if np.any(q_std_obs > 0):
        measurement_sigma_default = float(np.median(q_std_obs[q_std_obs > 0]))

    with pm.Model():
        log_q_max = pm.Normal("log_q_max", mu=log_q_max_mu, sigma=log_q_max_sigma)
        log_K_L = pm.Normal("log_K_L", mu=log_K_L_mu, sigma=log_K_L_sigma)
        q_max = pm.Deterministic("q_max", pm.math.exp(log_q_max))
        K_L = pm.Deterministic("K_L", pm.math.exp(log_K_L))
        sigma = pm.HalfNormal("sigma", sigma=measurement_sigma_default)

        q_pred = q_max * K_L * C_obs / (1.0 + K_L * C_obs)
        pm.Normal("q_obs", mu=q_pred, sigma=sigma, observed=q_obs)

        idata = pm.sample(
            draws=n_samples,
            tune=n_tune,
            chains=n_chains,
            target_accept=target_accept,
            random_seed=seed,
            progressbar=False,
            return_inferencedata=True,
        )

    rhat = az.rhat(idata, var_names=["q_max", "K_L"])
    ess = az.ess(idata, var_names=["q_max", "K_L"])

    rhat_vals = {name: float(rhat[name].values) for name in ("q_max", "K_L")}
    ess_vals = {name: float(ess[name].values) for name in ("q_max", "K_L")}

    n_total = n_chains * n_samples
    ess_floor = ess_threshold_fraction * n_total

    diverging = idata.sample_stats.get("diverging") if hasattr(idata, "sample_stats") else None
    if diverging is not None:
        divergence_rate = float(np.asarray(diverging).sum() / n_total)
    else:
        divergence_rate = 0.0

    failures: list[str] = []
    for name, rhat_val in rhat_vals.items():
        if rhat_val > rhat_threshold or not np.isfinite(rhat_val):
            failures.append(
                f"R-hat({name})={rhat_val:.4f} > {rhat_threshold}"
            )
    for name, ess_val in ess_vals.items():
        if ess_val < ess_floor or not np.isfinite(ess_val):
            failures.append(
                f"ESS({name})={ess_val:.0f} < {ess_floor:.0f}"
            )
    if divergence_rate > divergence_threshold:
        failures.append(
            f"divergence_rate={divergence_rate:.3%} > {divergence_threshold:.1%}"
        )

    if failures:
        raise BayesianFitConvergenceError(
            r_hat=rhat_vals,
            ess=ess_vals,
            divergence_rate=divergence_rate,
            failures=failures,
        )

    posterior = idata.posterior
    q_max_samples = np.asarray(posterior["q_max"].values).flatten()
    K_L_samples = np.asarray(posterior["K_L"].values).flatten()

    means = np.array([q_max_samples.mean(), K_L_samples.mean()])
    stds = np.array([q_max_samples.std(ddof=1), K_L_samples.std(ddof=1)])
    cov = np.cov(np.vstack([q_max_samples, K_L_samples]))

    entries = _build_calibration_entries(
        points,
        posterior_means={"q_max": means[0], "K_L": means[1]},
        posterior_stds={"q_max": stds[0], "K_L": stds[1]},
    )

    logger.info(
        "Bayesian fit converged: q_max=%.4g±%.4g, K_L=%.4g±%.4g, "
        "R-hat=%s, ESS=%s, divergences=%.2f%%",
        means[0], stds[0], means[1], stds[1],
        {k: f"{v:.4f}" for k, v in rhat_vals.items()},
        {k: f"{v:.0f}" for k, v in ess_vals.items()},
        divergence_rate * 100,
    )

    return PosteriorSamples.from_covariance(
        parameter_names=("q_max", "K_L"),
        means=means,
        covariance=cov,
        source_entries=entries,
    )


__all__ = [
    "BayesianFitConvergenceError",
    "IsothermPoint",
    "PymcNotInstalledError",
    "fit_langmuir_posterior",
    "pymc_available",
]
