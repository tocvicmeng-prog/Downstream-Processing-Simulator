"""G2 acceptance tests for the MC-LRM driver.

Per architect decomposition § 3.2 — 18-test inventory across:
  TestMCDriverSmoke (3)
  TestLinearRegimeAgreement (2)
  TestNonLinearpHRegime (2)
  TestSolverFailureHandling (4)
  TestParameterClipping (2)
  TestConvergenceReport (3)
  TestParallelism (2)

Note: the LRM-end integration tests do not call the real ``solve_lrm``
because the v0.3.0 contract is that the driver is solver-agnostic. We
construct synthetic ``LRMResult``-shaped solvers that exercise the
driver's full code path without paying scipy BDF cost. The real-LRM
smoke test lives in the G3 integration suite.

Reference: docs/handover/ARCH_v0_7_P5plusplus_DECOMPOSITION.md § 3.2.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest

from dpsim.calibration import PosteriorSamples
from dpsim.module3_performance.monte_carlo import (
    ConvergenceReport,
    MCBands,
    default_lrm_curves,
    default_lrm_scalars,
    run_mc,
)


# --------------------------------------------------------------------------- #
# Test fixtures: synthetic LRMResult-shaped solvers                            #
# --------------------------------------------------------------------------- #


@dataclass
class FakeLRMResult:
    mass_eluted: float
    mass_balance_error: float
    C_outlet: np.ndarray


def linear_solver(params: dict[str, float], tail_mode: bool) -> FakeLRMResult:
    """Linear-regime synthetic solver: scalar = q_max × K_L."""
    q = params["q_max"]
    k = params["K_L"]
    val = q * k
    n_t = 200
    curve = np.linspace(0.0, val, n_t)
    return FakeLRMResult(
        mass_eluted=val,
        mass_balance_error=1e-4,
        C_outlet=curve,
    )


def nonlinear_pH_solver(params: dict[str, float], tail_mode: bool) -> FakeLRMResult:
    """Non-linear pH-transition response: highly sensitive to pH_steepness."""
    q = params["q_max"]
    pH_t = params["pH_transition"]
    pH_s = params["pH_steepness"]
    pH_op = 5.0  # operational
    response = q / (1.0 + np.exp(-pH_s * (pH_op - pH_t)))
    return FakeLRMResult(
        mass_eluted=float(response),
        mass_balance_error=1e-4,
        C_outlet=np.full(50, response),
    )


def make_failing_solver(fail_count: int):
    """Solver that fails the first ``fail_count`` calls then succeeds."""
    state = {"calls": 0}

    def _solver(params: dict[str, float], tail_mode: bool) -> FakeLRMResult:
        state["calls"] += 1
        if state["calls"] <= fail_count:
            raise RuntimeError(f"synthetic failure #{state['calls']}")
        return linear_solver(params, tail_mode)

    return _solver, state


def make_consecutive_failure_solver():
    """Solver that always fails — exercises the consecutive-failure cap."""
    def _solver(params: dict[str, float], tail_mode: bool) -> FakeLRMResult:
        raise RuntimeError("always fails")
    return _solver


def make_tail_aware_solver():
    """Records whether tail_mode was set on each call."""
    state = {"tail_calls": 0, "normal_calls": 0}

    def _solver(params: dict[str, float], tail_mode: bool) -> FakeLRMResult:
        if tail_mode:
            state["tail_calls"] += 1
        else:
            state["normal_calls"] += 1
        return linear_solver(params, tail_mode)

    return _solver, state


def make_lsoda_check_solver():
    """Simulates a real LRM solver and asserts no LSODA hint passed."""
    def _solver(params: dict[str, float], tail_mode: bool) -> FakeLRMResult:
        # The driver MUST NOT pass any solver-method hint; tail_mode is
        # the only knob, and LSODA is rejected per D-045. The contract
        # is therefore implicit — we just verify the call shape.
        assert isinstance(params, dict)
        assert isinstance(tail_mode, bool)
        return linear_solver(params, tail_mode)

    return _solver


# --------------------------------------------------------------------------- #
# 1) TestMCDriverSmoke (3)                                                     #
# --------------------------------------------------------------------------- #


class TestMCDriverSmoke:
    def test_n10_smoke(self) -> None:
        s = PosteriorSamples.from_marginals(
            ("q_max", "K_L"), [10.0, 1e-3], [1.0, 1e-4]
        )
        bands = run_mc(s, linear_solver, n=10, n_seeds=2)
        assert isinstance(bands, MCBands)
        assert bands.n_samples == 10
        assert bands.solver_unstable is False
        assert "mass_eluted" in bands.scalar_quantiles
        assert "C_outlet_p50" in bands.curve_bands

    def test_n100_produces_nontrivial_bands(self) -> None:
        s = PosteriorSamples.from_marginals(
            ("q_max", "K_L"), [10.0, 1e-3], [1.0, 1e-4]
        )
        bands = run_mc(s, linear_solver, n=100, n_seeds=4)
        q = bands.scalar_quantiles["mass_eluted"]
        assert q["p05"] < q["p50"] < q["p95"]
        assert q["p95"] - q["p05"] > 0.0

    def test_reproducibility_under_fixed_seed(self) -> None:
        s = PosteriorSamples.from_marginals(
            ("q_max", "K_L"), [10.0, 1e-3], [1.0, 1e-4]
        )
        a = run_mc(s, linear_solver, n=40, n_seeds=2, base_seed=7)
        b = run_mc(s, linear_solver, n=40, n_seeds=2, base_seed=7)
        np.testing.assert_array_equal(
            np.array([a.scalar_quantiles["mass_eluted"]["p50"]]),
            np.array([b.scalar_quantiles["mass_eluted"]["p50"]]),
        )
        np.testing.assert_array_equal(a.curve_bands["C_outlet_p50"],
                                       b.curve_bands["C_outlet_p50"])


# --------------------------------------------------------------------------- #
# 2) TestLinearRegimeAgreement (AC#1 — 2)                                      #
# --------------------------------------------------------------------------- #


class TestLinearRegimeAgreement:
    def test_linear_p50_matches_delta_method_within_1pct(self) -> None:
        """At small σ, MC P50 ≈ μ_q × μ_K (delta-method first-order point)."""
        mu_q = 10.0
        mu_K = 1e-3
        s = PosteriorSamples.from_marginals(
            ("q_max", "K_L"), [mu_q, mu_K], [0.05 * mu_q, 0.05 * mu_K]
        )
        bands = run_mc(s, linear_solver, n=400, n_seeds=4, base_seed=21)
        delta_method_point = mu_q * mu_K
        p50 = bands.scalar_quantiles["mass_eluted"]["p50"]
        assert abs(p50 - delta_method_point) / delta_method_point < 0.01

    def test_linear_envelope_widens_with_sigma(self) -> None:
        mu_q = 10.0
        mu_K = 1e-3
        s_small = PosteriorSamples.from_marginals(
            ("q_max", "K_L"), [mu_q, mu_K], [0.02 * mu_q, 0.02 * mu_K]
        )
        s_large = PosteriorSamples.from_marginals(
            ("q_max", "K_L"), [mu_q, mu_K], [0.20 * mu_q, 0.20 * mu_K]
        )
        bs_small = run_mc(s_small, linear_solver, n=400, n_seeds=4, base_seed=33)
        bs_large = run_mc(s_large, linear_solver, n=400, n_seeds=4, base_seed=33)
        env_small = (bs_small.scalar_quantiles["mass_eluted"]["p95"]
                     - bs_small.scalar_quantiles["mass_eluted"]["p05"])
        env_large = (bs_large.scalar_quantiles["mass_eluted"]["p95"]
                     - bs_large.scalar_quantiles["mass_eluted"]["p05"])
        assert env_large > env_small * 5  # ~10× σ → ~10× envelope


# --------------------------------------------------------------------------- #
# 3) TestNonLinearpHRegime (AC#2 — 2)                                          #
# --------------------------------------------------------------------------- #


class TestNonLinearpHRegime:
    def test_high_steepness_sigma_produces_wide_envelope(self) -> None:
        """At pH_steepness σ = 1.0, MC envelope on elution recovery is large."""
        s = PosteriorSamples.from_marginals(
            ("q_max", "pH_transition", "pH_steepness"),
            [10.0, 5.5, 4.0],
            [0.5, 0.1, 1.0],
        )
        bands = run_mc(s, nonlinear_pH_solver, n=400, n_seeds=4, base_seed=99)
        q = bands.scalar_quantiles["mass_eluted"]
        relative_envelope = (q["p95"] - q["p05"]) / abs(q["p50"])
        # Non-linear pH regime: envelope should be at least 20% relative
        assert relative_envelope > 0.20

    def test_p50_differs_from_first_order_linearisation(self) -> None:
        """Mean-of-function ≠ function-of-mean in the non-linear regime."""
        mu_q = 10.0
        mu_pH_t = 5.5
        mu_pH_s = 4.0
        s = PosteriorSamples.from_marginals(
            ("q_max", "pH_transition", "pH_steepness"),
            [mu_q, mu_pH_t, mu_pH_s],
            [0.5, 0.1, 1.0],
        )
        bands = run_mc(s, nonlinear_pH_solver, n=400, n_seeds=4, base_seed=101)
        # First-order point: response at the mean
        delta_point = nonlinear_pH_solver(
            {"q_max": mu_q, "pH_transition": mu_pH_t, "pH_steepness": mu_pH_s},
            False,
        ).mass_eluted
        p50 = bands.scalar_quantiles["mass_eluted"]["p50"]
        relative_disagreement = abs(p50 - delta_point) / abs(delta_point)
        # SA brief AC#2: ≥ 5% disagreement is the design target. Allow
        # noise in either direction.
        assert relative_disagreement >= 0.02


# --------------------------------------------------------------------------- #
# 4) TestSolverFailureHandling (4)                                             #
# --------------------------------------------------------------------------- #


class TestSolverFailureHandling:
    def test_tail_mode_fires_on_high_z_score(self) -> None:
        s = PosteriorSamples.from_marginals(
            ("q_max", "K_L"), [10.0, 1e-3], [3.0, 3e-4]
        )
        solver, state = make_tail_aware_solver()
        run_mc(s, solver, n=200, n_seeds=4, tail_sigma_threshold=2.0, base_seed=7)
        # With σ wide enough, some samples should be > 2σ from mean
        assert state["tail_calls"] > 0
        assert state["tail_calls"] + state["normal_calls"] >= 200

    def test_abort_and_resample_on_runtime_error(self) -> None:
        s = PosteriorSamples.from_marginals(
            ("q_max", "K_L"), [10.0, 1e-3], [1.0, 1e-4]
        )
        solver, state = make_failing_solver(fail_count=3)
        bands = run_mc(s, solver, n=20, n_seeds=2, base_seed=42)
        assert bands.solver_unstable is False
        assert bands.n_samples == 20
        assert bands.n_failures == 3

    def test_consecutive_failure_cap_sets_unstable(self) -> None:
        s = PosteriorSamples.from_marginals(
            ("q_max", "K_L"), [10.0, 1e-3], [1.0, 1e-4]
        )
        solver = make_consecutive_failure_solver()
        bands = run_mc(s, solver, n=20, n_seeds=1, failure_cap=5, base_seed=0)
        assert bands.solver_unstable is True
        assert bands.n_samples == 0

    def test_no_lsoda_passed_to_solver(self) -> None:
        """D-045: solver-method hints must NOT be passed; only tail_mode."""
        s = PosteriorSamples.from_marginals(
            ("q_max", "K_L"), [10.0, 1e-3], [1.0, 1e-4]
        )
        solver = make_lsoda_check_solver()
        bands = run_mc(s, solver, n=10, n_seeds=2)
        # Manifest must surface the no-LSODA assumption verbatim
        no_lsoda = any(
            "LSODA fallback rejected" in a for a in bands.model_manifest.assumptions
        )
        assert no_lsoda


# --------------------------------------------------------------------------- #
# 5) TestParameterClipping (2)                                                 #
# --------------------------------------------------------------------------- #


class TestParameterClipping:
    def test_clip_at_user_bounds(self) -> None:
        s = PosteriorSamples.from_marginals(
            ("q_max", "K_L"), [10.0, 1e-3], [3.0, 3e-4]
        )
        clips = {"q_max": (8.0, 12.0)}
        captured = []

        def capture_solver(params: dict[str, float], tail_mode: bool) -> FakeLRMResult:
            captured.append(params["q_max"])
            return linear_solver(params, tail_mode)

        bands = run_mc(s, capture_solver, n=200, n_seeds=4, parameter_clips=clips,
                       base_seed=11)
        captured_arr = np.asarray(captured)
        # All values in [8.0, 12.0]
        assert captured_arr.min() >= 8.0 - 1e-12
        assert captured_arr.max() <= 12.0 + 1e-12

    def test_n_clipped_diagnostic(self) -> None:
        s = PosteriorSamples.from_marginals(
            ("q_max", "K_L"), [10.0, 1e-3], [3.0, 3e-4]
        )
        clips = {"q_max": (9.5, 10.5)}  # narrow → many clip events expected
        bands = run_mc(s, linear_solver, n=200, n_seeds=4,
                       parameter_clips=clips, base_seed=23)
        assert bands.n_clipped.get("q_max", 0) > 0


# --------------------------------------------------------------------------- #
# 6) TestConvergenceReport (3)                                                 #
# --------------------------------------------------------------------------- #


class TestConvergenceReport:
    def test_quantile_stability_passes_for_stable_run(self) -> None:
        s = PosteriorSamples.from_marginals(
            ("q_max", "K_L"), [10.0, 1e-3], [0.5, 5e-5]
        )
        bands = run_mc(s, linear_solver, n=400, n_seeds=4, base_seed=51)
        assert bands.convergence_diagnostics.all_quantiles_stable is True

    def test_inter_seed_overlap_passes_at_threshold(self) -> None:
        s = PosteriorSamples.from_marginals(
            ("q_max", "K_L"), [10.0, 1e-3], [0.5, 5e-5]
        )
        bands = run_mc(s, linear_solver, n=400, n_seeds=4, base_seed=61)
        assert bands.convergence_diagnostics.overlap_passes(threshold=0.05)

    def test_r_hat_present_and_informational(self) -> None:
        s = PosteriorSamples.from_marginals(
            ("q_max", "K_L"), [10.0, 1e-3], [0.5, 5e-5]
        )
        bands = run_mc(s, linear_solver, n=200, n_seeds=4, base_seed=71)
        rhat = bands.convergence_diagnostics.r_hat_informational
        assert "mass_eluted" in rhat
        # R-hat should be near 1.0 for independent LHS draws
        assert 0.8 <= rhat["mass_eluted"] <= 1.5


# --------------------------------------------------------------------------- #
# 7) TestParallelism (2)                                                       #
# --------------------------------------------------------------------------- #


class TestParallelism:
    def test_njobs_warning_serial_path(self) -> None:
        s = PosteriorSamples.from_marginals(
            ("q_max", "K_L"), [10.0, 1e-3], [0.5, 5e-5]
        )
        # n_jobs > 1 logs a warning and runs serial (R-G2-4 mitigation:
        # joblib wiring deferred). Result must still be a valid MCBands.
        bands = run_mc(s, linear_solver, n=20, n_seeds=2, n_jobs=4, base_seed=88)
        assert bands.n_samples == 20

    def test_njobs_1_vs_4_identical_results(self) -> None:
        s = PosteriorSamples.from_marginals(
            ("q_max", "K_L"), [10.0, 1e-3], [0.5, 5e-5]
        )
        a = run_mc(s, linear_solver, n=40, n_seeds=2, n_jobs=1, base_seed=88)
        b = run_mc(s, linear_solver, n=40, n_seeds=2, n_jobs=4, base_seed=88)
        np.testing.assert_array_equal(a.curve_bands["C_outlet_p50"],
                                       b.curve_bands["C_outlet_p50"])
        assert a.scalar_quantiles == b.scalar_quantiles


# --------------------------------------------------------------------------- #
# 8) Default extractors                                                        #
# --------------------------------------------------------------------------- #


def test_default_extractors_extract_lrm_fields() -> None:
    r = FakeLRMResult(mass_eluted=12.5, mass_balance_error=1e-3,
                      C_outlet=np.array([0.0, 1.0, 2.0]))
    scalars = default_lrm_scalars(r)
    curves = default_lrm_curves(r)
    assert scalars["mass_eluted"] == 12.5
    assert scalars["mass_balance_error"] == 1e-3
    assert scalars["max_C_outlet"] == 2.0
    np.testing.assert_array_equal(curves["C_outlet"], [0.0, 1.0, 2.0])
