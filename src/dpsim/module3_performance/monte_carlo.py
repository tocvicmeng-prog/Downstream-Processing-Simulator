"""Monte-Carlo LRM uncertainty-propagation driver (G2 of P5++ initiative).

Implements the v0.3.0 MC-LRM core per:

* DEVORCH joint plan § 6 / § 7  (build order; AC#1–AC#5)
* Architect decomposition § 3.2  (MCBands / ConvergenceReport / run_mc)
* SA Mode-1 brief                 (Tier-1+2 numerical safeguards; reformulated AC#3)

The driver consumes a :class:`~dpsim.calibration.PosteriorSamples` produced
by G1 and a user-supplied ``lrm_solver`` callable that maps a
``dict[parameter_name, value]`` to a domain ``LRMResult`` (or ``None`` to
trigger an abort-and-resample). The driver:

1. **Splits work across ``n_seeds`` independent sub-runs** so that
   inter-seed posterior overlap (SA-Q3 / D-047) can be computed without
   double-counting the same draws.
2. **Applies Tier-2 parameter clipping** when ``parameter_clips`` is
   supplied (SA-Q1).
3. **Detects tail draws** (``max|z| > tail_sigma_threshold``) and signals
   the solver via the ``tail_mode`` argument — the caller's solver decides
   how to tighten BDF tolerances (Tier-1).
4. **Aborts and resamples** on solver exceptions, with a configurable
   consecutive-failure cap (default 5) before declaring the run unstable.
5. **NEVER falls back to LSODA** — the existing LRM code documents that
   LSODA stalls on high-affinity Langmuir paths (`lumped_rate.py` § 372).
6. **Computes convergence diagnostics** per the SA-Q3 reformulation:
   quantile-stability plateau (final 25 % vs first 75 %) plus inter-seed
   posterior overlap; R-hat is reported informationally only.

Output is an :class:`MCBands` aggregating per-scalar quantiles, per-curve
P05/P50/P95 envelopes, the convergence report, and a :class:`ModelManifest`
whose assumptions field surfaces SA-Q4 (marginal-only conservatism) and
SA-Q5 (independence of parameter and DSD geometric variance) verbatim.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

import numpy as np

from dpsim.calibration import PosteriorSamples
from dpsim.datatypes import ModelEvidenceTier, ModelManifest

logger = logging.getLogger("dpsim.module3_performance.monte_carlo")

LRMSolver = Callable[[dict[str, float], bool], Any]
"""Type alias for the user-supplied solver callable.

The first argument is a ``dict`` mapping parameter names (matching
``PosteriorSamples.parameter_names``) to sampled values. The second
argument is ``tail_mode``; the caller should tighten ``rtol/atol`` when
``True``. The callable should return any object understood by
``extract_scalars`` and ``extract_curves`` — typically an ``LRMResult``
— or raise ``RuntimeError`` / ``np.linalg.LinAlgError`` to trigger
abort-and-resample.
"""

ScalarExtractor = Callable[[Any], dict[str, float]]
CurveExtractor = Callable[[Any], dict[str, np.ndarray]]


# --------------------------------------------------------------------------- #
# Result dataclasses                                                          #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ConvergenceReport:
    """Per-metric convergence summary (SA-Q3 / D-047).

    ``quantile_stability``
        For each scalar metric, ``True`` if ``|P50_final - P50_first_three_quarters|
        / |P50_first_three_quarters| < quantile_stability_threshold``.

    ``inter_seed_posterior_overlap``
        For each scalar metric, ``(max P50 across seeds - min P50 across
        seeds) / |median(P50 across seeds)|``. Pass gate is ``≤ 0.05``.

    ``inter_seed_envelope``
        Informational; ``(P95 - P05)`` averaged across seeds and
        normalised by ``|median|``.

    ``r_hat_informational``
        Classic Gelman-Rubin R-hat across seeds. Reported only — LHS
        draws are independent by construction so R-hat reduces to a
        restatement of inter-seed posterior overlap.
    """

    quantile_stability: dict[str, bool]
    inter_seed_posterior_overlap: dict[str, float]
    inter_seed_envelope: dict[str, float]
    r_hat_informational: dict[str, float]

    @property
    def all_quantiles_stable(self) -> bool:
        return all(self.quantile_stability.values())

    def overlap_passes(self, threshold: float = 0.05) -> bool:
        return all(v <= threshold for v in self.inter_seed_posterior_overlap.values())


@dataclass(frozen=True)
class MCBands:
    """Output of an MC LRM uncertainty-propagation run."""

    n_samples: int
    n_failures: int
    n_resampled: int
    scalar_quantiles: dict[str, dict[str, float]]
    curve_bands: dict[str, np.ndarray]
    convergence_diagnostics: ConvergenceReport
    model_manifest: ModelManifest
    solver_unstable: bool = False
    n_clipped: dict[str, int] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Default extractors (LRMResult-shaped)                                       #
# --------------------------------------------------------------------------- #


def default_lrm_scalars(result: Any) -> dict[str, float]:
    """Default scalar extractor for ``LRMResult``-shaped objects."""
    out: dict[str, float] = {}
    if hasattr(result, "mass_eluted"):
        out["mass_eluted"] = float(result.mass_eluted)
    if hasattr(result, "mass_balance_error"):
        out["mass_balance_error"] = float(result.mass_balance_error)
    if hasattr(result, "C_outlet"):
        out["max_C_outlet"] = float(np.max(np.asarray(result.C_outlet)))
    return out


def default_lrm_curves(result: Any) -> dict[str, np.ndarray]:
    """Default curve extractor for ``LRMResult``-shaped objects."""
    out: dict[str, np.ndarray] = {}
    if hasattr(result, "C_outlet"):
        out["C_outlet"] = np.asarray(result.C_outlet, dtype=float)
    return out


# --------------------------------------------------------------------------- #
# Internal helpers                                                            #
# --------------------------------------------------------------------------- #


def _clip_sample(
    sample: np.ndarray,
    parameter_names: tuple[str, ...],
    parameter_clips: Mapping[str, tuple[float, float]] | None,
    clip_counts: dict[str, int],
) -> np.ndarray:
    """Clip ``sample`` in place against ``parameter_clips``; mutate ``clip_counts``."""
    if not parameter_clips:
        return sample
    out = sample.copy()
    for j, name in enumerate(parameter_names):
        if name not in parameter_clips:
            continue
        lo, hi = parameter_clips[name]
        if out[j] < lo:
            out[j] = lo
            clip_counts[name] = clip_counts.get(name, 0) + 1
        elif out[j] > hi:
            out[j] = hi
            clip_counts[name] = clip_counts.get(name, 0) + 1
    return out


def _max_abs_zscore(
    sample: np.ndarray,
    means: np.ndarray,
    stds: np.ndarray,
) -> float:
    """Maximum |(value - mean) / std| across parameters; 0 when std == 0."""
    safe_stds = np.where(stds > 0, stds, np.inf)
    z = np.abs((sample - means) / safe_stds)
    return float(np.max(z))


def _solve_one(
    sample: np.ndarray,
    parameter_names: tuple[str, ...],
    means: np.ndarray,
    stds: np.ndarray,
    lrm_solver: LRMSolver,
    tail_sigma_threshold: float,
) -> Any:
    """Run the user solver on one sample row; let exceptions propagate."""
    params = {name: float(sample[j]) for j, name in enumerate(parameter_names)}
    tail_mode = _max_abs_zscore(sample, means, stds) > tail_sigma_threshold
    return lrm_solver(params, tail_mode)


def _per_seed_run(
    seed: int,
    n_per_seed: int,
    samples: PosteriorSamples,
    lrm_solver: LRMSolver,
    parameter_clips: Mapping[str, tuple[float, float]] | None,
    failure_cap: int,
    tail_sigma_threshold: float,
    extract_scalars: ScalarExtractor,
    extract_curves: CurveExtractor,
    clip_counts: dict[str, int],
) -> tuple[list[dict[str, float]], list[dict[str, np.ndarray]], int, int, bool]:
    """Run a single seed's worth of MC samples.

    Returns
    -------
    (scalar_records, curve_records, n_failures, n_resampled, unstable_flag)
    """
    pool = samples.draw(n_per_seed, seed=seed, method="auto")
    scalar_records: list[dict[str, float]] = []
    curve_records: list[dict[str, np.ndarray]] = []
    n_failures = 0
    n_resampled = 0
    consecutive_failures = 0
    unstable = False

    replacement_seed = seed + 10_000
    pool_idx = 0

    target = n_per_seed
    while len(scalar_records) < target:
        if pool_idx < len(pool):
            sample = pool[pool_idx]
            pool_idx += 1
        else:
            extra = samples.draw(8, seed=replacement_seed, method="auto")
            replacement_seed += 1
            pool = np.vstack([pool, extra])
            sample = pool[pool_idx]
            pool_idx += 1
            n_resampled += 1

        sample = _clip_sample(
            sample, samples.parameter_names, parameter_clips, clip_counts
        )

        try:
            result = _solve_one(
                sample,
                samples.parameter_names,
                samples.means,
                samples.stds,
                lrm_solver,
                tail_sigma_threshold,
            )
        except (RuntimeError, np.linalg.LinAlgError, ValueError, FloatingPointError) as exc:
            n_failures += 1
            consecutive_failures += 1
            logger.warning(
                "MC sample failed (seed=%d, idx=%d): %s. Resampling.",
                seed, len(scalar_records), exc,
            )
            if consecutive_failures >= failure_cap:
                logger.error(
                    "MC abort: %d consecutive failures at seed=%d (cap=%d). "
                    "Solver unstable; check posterior bounds and parameter_clips.",
                    consecutive_failures, seed, failure_cap,
                )
                unstable = True
                break
            continue

        if result is None:
            n_failures += 1
            consecutive_failures += 1
            if consecutive_failures >= failure_cap:
                unstable = True
                break
            continue

        consecutive_failures = 0
        scalar_records.append(extract_scalars(result))
        curve_records.append(extract_curves(result))

    return scalar_records, curve_records, n_failures, n_resampled, unstable


# --------------------------------------------------------------------------- #
# Convergence diagnostics                                                     #
# --------------------------------------------------------------------------- #


def _quantile_stability(
    values: np.ndarray, threshold: float
) -> bool:
    """ΔP50 over the final 25 % vs the first 75 % < threshold (relative)."""
    n = len(values)
    if n < 8:
        return True
    cut = max(1, int(n * 0.75))
    first = np.median(values[:cut])
    final = np.median(values)
    if abs(first) < 1e-300:
        return abs(final - first) < threshold
    return abs(final - first) / abs(first) < threshold


def _inter_seed_overlap(per_seed_p50s: np.ndarray) -> float:
    """(max - min) / |median| across seed-wise P50s."""
    if len(per_seed_p50s) <= 1:
        return 0.0
    med = float(np.median(per_seed_p50s))
    span = float(per_seed_p50s.max() - per_seed_p50s.min())
    if abs(med) < 1e-300:
        return float(span)
    return span / abs(med)


def _inter_seed_envelope(per_seed_p05_p95: list[tuple[float, float]]) -> float:
    """Average per-seed (P95 - P05) normalised by |median(P50)|."""
    if not per_seed_p05_p95:
        return 0.0
    spans = np.asarray([hi - lo for lo, hi in per_seed_p05_p95])
    return float(np.mean(spans))


def _r_hat(per_seed_chains: list[np.ndarray]) -> float:
    """Gelman-Rubin R-hat across seed-wise chains.

    Note: LHS draws are independent. R-hat is reported informationally
    per SA-Q3 / D-047.
    """
    if len(per_seed_chains) < 2:
        return 1.0
    lengths = {len(c) for c in per_seed_chains}
    if len(lengths) > 1:
        n_min = min(lengths)
        per_seed_chains = [c[:n_min] for c in per_seed_chains]
    n = len(per_seed_chains[0])
    if n < 2:
        return 1.0
    m = len(per_seed_chains)
    chain_means = np.asarray([np.mean(c) for c in per_seed_chains])
    chain_vars = np.asarray([np.var(c, ddof=1) for c in per_seed_chains])
    grand = float(np.mean(chain_means))
    B = (n / (m - 1)) * float(np.sum((chain_means - grand) ** 2))
    W = float(np.mean(chain_vars))
    if W <= 0:
        return 1.0
    var_hat = ((n - 1) / n) * W + (1 / n) * B
    return math.sqrt(var_hat / W)


def _build_convergence_report(
    per_seed_scalar_arrays: dict[str, list[np.ndarray]],
    quantile_stability_threshold: float,
) -> ConvergenceReport:
    quant_stable: dict[str, bool] = {}
    overlap: dict[str, float] = {}
    envelope: dict[str, float] = {}
    rhat: dict[str, float] = {}

    for metric, per_seed_chains in per_seed_scalar_arrays.items():
        all_vals = np.concatenate(per_seed_chains) if per_seed_chains else np.array([])
        quant_stable[metric] = _quantile_stability(all_vals, quantile_stability_threshold)

        per_seed_p50s = np.asarray([np.median(c) for c in per_seed_chains if len(c) > 0])
        overlap[metric] = _inter_seed_overlap(per_seed_p50s)

        per_seed_pairs = [
            (float(np.quantile(c, 0.05)), float(np.quantile(c, 0.95)))
            for c in per_seed_chains if len(c) >= 4
        ]
        med_p50 = float(np.median(per_seed_p50s)) if len(per_seed_p50s) else 0.0
        env = _inter_seed_envelope(per_seed_pairs)
        envelope[metric] = env / abs(med_p50) if abs(med_p50) > 1e-300 else env

        rhat[metric] = _r_hat(per_seed_chains)

    return ConvergenceReport(
        quantile_stability=quant_stable,
        inter_seed_posterior_overlap=overlap,
        inter_seed_envelope=envelope,
        r_hat_informational=rhat,
    )


# --------------------------------------------------------------------------- #
# Public entrypoint                                                           #
# --------------------------------------------------------------------------- #


SA_Q4_ASSUMPTION = (
    "Posterior treated as marginal-only (independent parameters); per "
    "Karlsson 1998 this overestimates uncertainty when posterior "
    "correlations are negative — the conservative side for screening."
)
SA_Q4_COVARIANCE_ASSUMPTION = (
    "Posterior covariance attached; multivariate-normal sampling used."
)
SA_Q5_ASSUMPTION = (
    "MC parameter variance and DSD geometric variance treated as "
    "independent; valid to <20% accuracy for bead radii in 30–100 µm. "
    "v0.4+ unifies the paths (per D-049)."
)
NO_LSODA_ASSUMPTION = (
    "Solver: BDF only; LSODA fallback rejected per D-045 "
    "(documented stall on high-affinity Langmuir paths)."
)


def run_mc(
    samples: PosteriorSamples,
    lrm_solver: LRMSolver,
    *,
    n: int = 200,
    n_seeds: int = 4,
    n_jobs: int = 1,
    failure_cap: int = 5,
    tail_sigma_threshold: float = 2.0,
    parameter_clips: Mapping[str, tuple[float, float]] | None = None,
    extract_scalars: ScalarExtractor | None = None,
    extract_curves: CurveExtractor | None = None,
    base_seed: int = 0,
    quantile_stability_threshold: float = 0.01,
    convergence_overlap_threshold: float = 0.05,
) -> MCBands:
    """Drive a Monte-Carlo LRM uncertainty-propagation run.

    Parameters
    ----------
    samples : PosteriorSamples
        Posterior produced by G1.
    lrm_solver : LRMSolver
        ``Callable[[dict, bool], LRMResult-like]``. The dict maps
        parameter names to sampled values; the bool is ``tail_mode``,
        which the caller should use to tighten BDF tolerances.
    n : int
        Total number of samples requested; distributed evenly across
        ``n_seeds``.
    n_seeds : int
        Number of independent seed-wise sub-runs for inter-seed posterior
        overlap (SA-Q3). Must be ≥ 2 for meaningful diagnostics.
    n_jobs : int
        Reserved for future joblib parallelism; currently always serial.
    failure_cap : int
        Consecutive-failure cap before declaring the run unstable.
    tail_sigma_threshold : float
        |z|-score above which ``tail_mode=True`` is signalled to the solver.
    parameter_clips : Mapping[str, tuple[float, float]] | None
        Optional Tier-2 clipping; ``{name: (lo, hi)}``.
    extract_scalars : Callable | None
        Maps each solver result to ``dict[str, float]`` (scalars to
        quantile). Defaults to :func:`default_lrm_scalars`.
    extract_curves : Callable | None
        Maps each solver result to ``dict[str, np.ndarray]`` (curves to
        envelope). Defaults to :func:`default_lrm_curves`.
    base_seed : int
        Seed for the first sub-run; subsequent sub-runs use
        ``base_seed + i``.
    quantile_stability_threshold : float
        Relative tolerance for the quantile-stability check (default 1 %).
    convergence_overlap_threshold : float
        Threshold for inter-seed posterior overlap (default 5 %); stored
        in the manifest's ``diagnostics`` for downstream gating.

    Returns
    -------
    MCBands
    """
    if n <= 0:
        raise ValueError(f"n must be > 0, got {n}")
    if n_seeds < 1:
        raise ValueError(f"n_seeds must be ≥ 1, got {n_seeds}")
    if failure_cap < 1:
        raise ValueError(f"failure_cap must be ≥ 1, got {failure_cap}")
    if n_jobs != 1:
        logger.warning(
            "n_jobs > 1 not yet implemented; running serial. (joblib "
            "wiring deferred to v0.3.0 close per R-G2-4 mitigation.)"
        )

    extract_scalars = extract_scalars or default_lrm_scalars
    extract_curves = extract_curves or default_lrm_curves

    n_per_seed = max(1, n // n_seeds)

    clip_counts: dict[str, int] = {}
    per_seed_scalar_records: list[list[dict[str, float]]] = []
    per_seed_curve_records: list[list[dict[str, np.ndarray]]] = []
    total_failures = 0
    total_resampled = 0
    unstable = False

    for i in range(n_seeds):
        seed_i = base_seed + i
        scalars_i, curves_i, fails_i, resampled_i, unstable_i = _per_seed_run(
            seed=seed_i,
            n_per_seed=n_per_seed,
            samples=samples,
            lrm_solver=lrm_solver,
            parameter_clips=parameter_clips,
            failure_cap=failure_cap,
            tail_sigma_threshold=tail_sigma_threshold,
            extract_scalars=extract_scalars,
            extract_curves=extract_curves,
            clip_counts=clip_counts,
        )
        per_seed_scalar_records.append(scalars_i)
        per_seed_curve_records.append(curves_i)
        total_failures += fails_i
        total_resampled += resampled_i
        if unstable_i:
            unstable = True

    flat_scalars = [r for seed_records in per_seed_scalar_records for r in seed_records]
    flat_curves = [r for seed_records in per_seed_curve_records for r in seed_records]
    n_success = len(flat_scalars)

    scalar_quantiles: dict[str, dict[str, float]] = {}
    if flat_scalars:
        all_metric_names = sorted(set().union(*(r.keys() for r in flat_scalars)))
        for metric in all_metric_names:
            vals = np.asarray(
                [r[metric] for r in flat_scalars if metric in r], dtype=float
            )
            if vals.size == 0:
                continue
            scalar_quantiles[metric] = {
                "p05": float(np.quantile(vals, 0.05)),
                "p50": float(np.quantile(vals, 0.50)),
                "p95": float(np.quantile(vals, 0.95)),
                "mean": float(np.mean(vals)),
                "std": float(np.std(vals, ddof=1)) if vals.size > 1 else 0.0,
            }

    curve_bands: dict[str, np.ndarray] = {}
    if flat_curves:
        all_curve_names = sorted(set().union(*(r.keys() for r in flat_curves)))
        for cname in all_curve_names:
            curves = [r[cname] for r in flat_curves if cname in r]
            if not curves:
                continue
            min_len = min(len(c) for c in curves)
            stacked = np.asarray([c[:min_len] for c in curves], dtype=float)
            curve_bands[f"{cname}_p05"] = np.quantile(stacked, 0.05, axis=0)
            curve_bands[f"{cname}_p50"] = np.quantile(stacked, 0.50, axis=0)
            curve_bands[f"{cname}_p95"] = np.quantile(stacked, 0.95, axis=0)

    per_seed_scalar_arrays: dict[str, list[np.ndarray]] = {}
    if flat_scalars:
        all_metric_names = sorted(set().union(*(r.keys() for r in flat_scalars)))
        for metric in all_metric_names:
            chains: list[np.ndarray] = []
            for seed_records in per_seed_scalar_records:
                arr = np.asarray(
                    [r[metric] for r in seed_records if metric in r], dtype=float
                )
                if len(arr) > 0:
                    chains.append(arr)
            per_seed_scalar_arrays[metric] = chains

    convergence = _build_convergence_report(
        per_seed_scalar_arrays, quantile_stability_threshold
    )

    assumptions = [
        SA_Q4_COVARIANCE_ASSUMPTION if samples.has_covariance else SA_Q4_ASSUMPTION,
        SA_Q5_ASSUMPTION,
        NO_LSODA_ASSUMPTION,
    ]
    if unstable:
        assumptions.append(
            f"WARNING: solver unstable (consecutive-failure cap of "
            f"{failure_cap} reached); bands incomplete."
        )

    manifest = ModelManifest(
        model_name="dpsim.module3_performance.monte_carlo.run_mc",
        evidence_tier=ModelEvidenceTier.SEMI_QUANTITATIVE,
        valid_domain={
            "n_samples_target": n,
            "n_seeds": n_seeds,
            "tail_sigma_threshold": tail_sigma_threshold,
            "convergence_overlap_threshold": convergence_overlap_threshold,
            "quantile_stability_threshold": quantile_stability_threshold,
        },
        calibration_ref=";".join(
            sorted({
                e.source_reference
                for e in samples.source_calibration_entries
                if e.source_reference
            })
        ),
        assumptions=assumptions,
        diagnostics={
            "n_success": n_success,
            "n_failures": total_failures,
            "n_resampled": total_resampled,
            "n_clipped": dict(clip_counts),
            "solver_unstable": unstable,
            "all_quantiles_stable": convergence.all_quantiles_stable,
            "overlap_passes": convergence.overlap_passes(convergence_overlap_threshold),
        },
    )

    return MCBands(
        n_samples=n_success,
        n_failures=total_failures,
        n_resampled=total_resampled,
        scalar_quantiles=scalar_quantiles,
        curve_bands=curve_bands,
        convergence_diagnostics=convergence,
        model_manifest=manifest,
        solver_unstable=unstable,
        n_clipped=dict(clip_counts),
    )


__all__ = [
    "ConvergenceReport",
    "MCBands",
    "LRMSolver",
    "ScalarExtractor",
    "CurveExtractor",
    "run_mc",
    "default_lrm_scalars",
    "default_lrm_curves",
]
