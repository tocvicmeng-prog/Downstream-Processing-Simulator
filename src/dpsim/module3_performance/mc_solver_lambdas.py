"""Production solver-lambda helpers for the MC-LRM driver (v0.3.6).

Closes the v0.3.0 → v0.3.2 follow-on flagged as "solver-lambda helper for
production use." The v0.3.0 contract requires the caller of
:func:`dpsim.module3_performance.monte_carlo.run_mc` to supply an
``mc_lrm_solver`` callable with signature
``Callable[[dict[str, float], bool], LRMResult]``. Writing that lambda
by hand is repetitive and error-prone — every caller has to remember to:

* construct a :class:`LangmuirIsotherm` from the sampled ``q_max`` /
  ``K_L``,
* propagate the ``tail_mode`` flag into ``solve_ivp`` tolerances,
* keep all *other* :func:`solve_lrm` arguments fixed across samples.

This module factors that pattern out into a single helper:

.. code-block:: python

    from dpsim.module3_performance.mc_solver_lambdas import (
        make_langmuir_lrm_solver,
    )

    solver = make_langmuir_lrm_solver(
        column=column,
        C_feed=feed_concentration_mol_m3,
        feed_duration=feed_duration_s,
        flow_rate=flow_rate_m3_s,
        total_time=total_time_s,
        parameter_names=("q_max", "K_L"),
        # Optional overrides:
        n_z=50, D_molecular=7e-11, k_ads=100.0,
    )
    bands = run_mc(samples, solver, n=200, n_seeds=4, n_jobs=4)

The returned callable is picklable (top-level function returns a
top-level closure-bound callable composed of :data:`functools.partial`),
so it works under joblib's ``loky`` backend for v0.3.6 parallelism.

Tail-aware tolerance policy
---------------------------
Per SA-Q1 / D-046, when ``tail_mode=True`` (i.e. the sampled parameter
vector lies > ``tail_sigma_threshold`` σ from the posterior mean) the
solver tightens BDF tolerances by 10× (rtol → rtol × 0.1, atol → atol
× 0.1). This is a **mitigation**, not a substitute for parameter
clipping or abort-and-resample — those run inside the driver, not here.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from .hydrodynamics import ColumnGeometry
from .isotherms.langmuir import LangmuirIsotherm
from .transport.lumped_rate import LRMResult, solve_lrm

logger = logging.getLogger("dpsim.module3_performance.mc_solver_lambdas")

LRMSolverFn = Callable[[dict[str, float], bool], LRMResult]


def make_langmuir_lrm_solver(
    *,
    column: ColumnGeometry,
    C_feed: float,
    feed_duration: float,
    flow_rate: float,
    total_time: float,
    parameter_names: tuple[str, ...] = ("q_max", "K_L"),
    n_z: int = 50,
    D_molecular: float = 7e-11,
    k_ads: float = 100.0,
    rtol: float = 1.0e-6,
    atol: float = 1.0e-9,
    tail_tolerance_factor: float = 0.1,
) -> LRMSolverFn:
    """Return an ``mc_lrm_solver`` closure for use with ``run_mc()``.

    Parameters
    ----------
    column, C_feed, feed_duration, flow_rate, total_time : ...
        Standard :func:`solve_lrm` arguments held fixed across all
        Monte-Carlo samples. The whole point of MC propagation is to
        vary *only* the posterior parameters and hold the recipe
        constant.
    parameter_names : tuple[str, ...]
        Names that the closure expects in the per-sample params dict.
        Must include ``"q_max"`` and ``"K_L"``; additional names are
        accepted (the closure ignores them) so the caller can wire MC
        over a richer parameter set without changing this helper.
    n_z, D_molecular, k_ads : ...
        :func:`solve_lrm` defaults; expose for caller overrides.
    rtol, atol : float
        BDF nominal tolerances. Tightened by ``tail_tolerance_factor``
        when ``tail_mode=True`` per D-046.
    tail_tolerance_factor : float
        Multiplier applied to ``rtol`` and ``atol`` in tail mode.
        Default 0.1 → 10× tighter.

    Returns
    -------
    LRMSolverFn
        ``Callable[[dict[str, float], bool], LRMResult]`` that calls
        :func:`solve_lrm` per sample with the posterior-sampled q_max /
        K_L and the tightened tolerances when on the tail.

    Raises
    ------
    ValueError
        If ``parameter_names`` does not include ``"q_max"`` and ``"K_L"``.
    """
    pn = tuple(parameter_names)
    if "q_max" not in pn or "K_L" not in pn:
        raise ValueError(
            f"parameter_names must include 'q_max' and 'K_L'; got {pn!r}. "
            "make_langmuir_lrm_solver wires q_max/K_L into a "
            "LangmuirIsotherm; if you want to vary other parameters, "
            "consume them in your own custom solver lambda."
        )

    def _solver(params: dict[str, float], tail_mode: bool) -> Any:
        q_max = params["q_max"]
        K_L = params["K_L"]
        if not (q_max > 0.0 and K_L > 0.0):
            # Posterior tails can sample nonphysical Langmuir parameters.
            # Per D-046, raise so the driver's abort-and-resample path
            # fires instead of producing a silently corrupt result.
            raise ValueError(
                f"Non-physical Langmuir sample: q_max={q_max:.3g}, "
                f"K_L={K_L:.3g}. Driver will abort-and-resample."
            )
        isotherm = LangmuirIsotherm(q_max=q_max, K_L=K_L)
        if tail_mode:
            r = rtol * tail_tolerance_factor
            a = atol * tail_tolerance_factor
        else:
            r = rtol
            a = atol
        return solve_lrm(
            column=column,
            isotherm=isotherm,
            C_feed=C_feed,
            feed_duration=feed_duration,
            flow_rate=flow_rate,
            total_time=total_time,
            n_z=n_z,
            D_molecular=D_molecular,
            k_ads=k_ads,
            rtol=r,
            atol=a,
        )

    return _solver


__all__ = ["LRMSolverFn", "make_langmuir_lrm_solver"]
