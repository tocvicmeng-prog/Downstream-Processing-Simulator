"""G4 (v0.3.1) acceptance tests — Bayesian posterior fitting.

Per architect § 4.1 — 10 tests across:
  TestPymcAvailable (2)
  TestNUTSFit (4 — skipped when pymc absent)
  TestConvergenceGates (4)

The pymc tests are gated on ``pymc_available()``; they execute in
environments where ``pip install dpsim[bayesian]`` has been run, and
skip cleanly elsewhere. The non-pymc tests verify the lazy-import
boundary and the ``PymcNotInstalledError`` path so the module can be
imported and inspected without pymc installed.

Reference: docs/handover/ARCH_v0_7_P5plusplus_DECOMPOSITION.md § 4.1.
"""

from __future__ import annotations

import numpy as np
import pytest

from dpsim.calibration.bayesian_fit import (
    BayesianFitConvergenceError,
    IsothermPoint,
    PymcNotInstalledError,
    _assays_to_points,
    fit_langmuir_posterior,
    pymc_available,
)


PYMC_OK = pymc_available()
requires_pymc = pytest.mark.skipif(
    not PYMC_OK, reason="pymc + arviz not installed (pip install dpsim[bayesian])"
)


def _synthetic_isotherm_points(
    q_max_true: float = 50.0,
    K_L_true: float = 1e-3,
    n_points: int = 25,
    noise_std: float = 0.5,
    seed: int = 0,
) -> list[IsothermPoint]:
    """Generate a synthetic Langmuir isotherm with Gaussian noise."""
    rng = np.random.default_rng(seed)
    C = np.linspace(50.0, 5000.0, n_points)  # mol/m^3
    q_clean = q_max_true * K_L_true * C / (1.0 + K_L_true * C)
    q_obs = q_clean + rng.normal(0.0, noise_std, size=n_points)
    return [IsothermPoint(float(c), float(q), noise_std)
            for c, q in zip(C, q_obs)]


# --------------------------------------------------------------------------- #
# 1) TestPymcAvailable (2)                                                     #
# --------------------------------------------------------------------------- #


class TestPymcAvailable:
    def test_module_imports_without_pymc(self) -> None:
        """The module must import even when pymc is absent (lazy import)."""
        # If we got this far, the import succeeded.
        from dpsim.calibration import bayesian_fit  # noqa: F401
        assert hasattr(bayesian_fit, "fit_langmuir_posterior")
        assert hasattr(bayesian_fit, "pymc_available")

    def test_no_pymc_raises_clear_error(self) -> None:
        """fit_langmuir_posterior must raise PymcNotInstalledError without pymc."""
        if PYMC_OK:
            pytest.skip("pymc IS installed; this test exercises the error path")
        points = _synthetic_isotherm_points(n_points=10)
        with pytest.raises(PymcNotInstalledError, match="pip install dpsim\\[bayesian\\]"):
            fit_langmuir_posterior(points, n_chains=1, n_samples=10)


# --------------------------------------------------------------------------- #
# 2) TestNUTSFit (4 — skipped when pymc absent)                                #
# --------------------------------------------------------------------------- #


@requires_pymc
class TestNUTSFit:
    def test_q_max_recovery_within_5pct(self) -> None:
        q_max_true = 50.0
        points = _synthetic_isotherm_points(q_max_true=q_max_true, seed=11)
        s = fit_langmuir_posterior(
            points, n_chains=4, n_samples=500, n_tune=500, seed=11
        )
        idx = s.parameter_names.index("q_max")
        assert abs(s.means[idx] - q_max_true) / q_max_true < 0.05

    def test_K_L_recovery_within_50pct(self) -> None:
        K_L_true = 1e-3
        points = _synthetic_isotherm_points(K_L_true=K_L_true, seed=13)
        s = fit_langmuir_posterior(
            points, n_chains=4, n_samples=500, n_tune=500, seed=13
        )
        idx = s.parameter_names.index("K_L")
        # K_L is harder than q_max under Langmuir; loosen tolerance.
        assert abs(s.means[idx] - K_L_true) / K_L_true < 0.50

    def test_covariance_attached(self) -> None:
        points = _synthetic_isotherm_points(seed=17)
        s = fit_langmuir_posterior(
            points, n_chains=4, n_samples=500, n_tune=500, seed=17
        )
        assert s.has_covariance is True
        assert s.covariance.shape == (2, 2)
        # Diagonal of Σ should be > 0
        assert s.covariance[0, 0] > 0
        assert s.covariance[1, 1] > 0

    def test_returns_posterior_samples_with_provenance(self) -> None:
        points = _synthetic_isotherm_points(seed=19)
        s = fit_langmuir_posterior(
            points, n_chains=4, n_samples=500, n_tune=500, seed=19
        )
        # source_calibration_entries carry method tag
        assert len(s.source_calibration_entries) == 2
        for entry in s.source_calibration_entries:
            assert entry.fit_method == "bayesian"
            assert entry.measurement_type == "bayesian_NUTS"


# --------------------------------------------------------------------------- #
# 3) TestConvergenceGates (4)                                                  #
# --------------------------------------------------------------------------- #


class TestConvergenceGates:
    def test_error_class_carries_diagnostic_payload(self) -> None:
        """BayesianFitConvergenceError must carry r_hat, ess, divergence_rate, failures."""
        err = BayesianFitConvergenceError(
            r_hat={"q_max": 1.20, "K_L": 1.30},
            ess={"q_max": 50, "K_L": 40},
            divergence_rate=0.05,
            failures=["R-hat(q_max)=1.2000 > 1.05",
                      "ESS(K_L)=40 < 1000"],
        )
        assert err.r_hat == {"q_max": 1.20, "K_L": 1.30}
        assert err.ess == {"q_max": 50, "K_L": 40}
        assert err.divergence_rate == 0.05
        assert "R-hat(q_max)" in str(err)
        assert "ESS(K_L)" in str(err)

    @requires_pymc
    def test_rhat_gate_fires_when_chains_too_short(self) -> None:
        """An impossibly short chain must trip the R-hat gate (or ESS gate)."""
        points = _synthetic_isotherm_points(seed=23)
        # 1 chain + 5 draws => R-hat undefined / ESS far below floor =>
        # convergence error must fire.
        with pytest.raises(BayesianFitConvergenceError):
            fit_langmuir_posterior(
                points,
                n_chains=2,
                n_samples=5,
                n_tune=10,
                seed=23,
                rhat_threshold=1.05,
                ess_threshold_fraction=0.25,
            )

    @requires_pymc
    def test_ess_gate_fires_under_tight_threshold(self) -> None:
        """A deliberately tight ESS floor must fail even on a well-mixed chain."""
        points = _synthetic_isotherm_points(seed=29)
        with pytest.raises(BayesianFitConvergenceError) as excinfo:
            fit_langmuir_posterior(
                points,
                n_chains=4,
                n_samples=200,
                n_tune=300,
                seed=29,
                rhat_threshold=2.0,           # accept anything
                ess_threshold_fraction=10.0,  # impossible
            )
        msg = str(excinfo.value)
        assert "ESS" in msg

    def test_assays_to_points_handles_three_input_shapes(self) -> None:
        """The coercion helper must accept AssayRecord, IsothermPoint, and tuples."""
        from dpsim.assay_record import AssayKind, AssayRecord, Replicate

        ar = AssayRecord(
            record_id="test-1",
            kind=AssayKind.STATIC_BINDING_CAPACITY,
            units="mol/m^3",
            replicates=[Replicate(value=2.5, std=0.1), Replicate(value=2.7, std=0.1)],
            process_conditions={"concentration_mol_m3": 100.0},
        )
        ip = IsothermPoint(50.0, 1.5, 0.05)
        tup = (200.0, 5.0)
        tup_with_std = (300.0, 7.0, 0.2)

        points = _assays_to_points([ar, ip, tup, tup_with_std])
        # AssayRecord with 2 replicates → 2 points; IsothermPoint → 1;
        # 2 tuples → 2; total = 5.
        assert len(points) == 5
        # 0/1: AssayRecord replicates
        assert points[0].concentration == 100.0 and points[0].loading == 2.5
        assert points[1].concentration == 100.0 and points[1].loading == 2.7
        # 2: IsothermPoint passthrough
        assert points[2].concentration == 50.0 and points[2].loading == 1.5
        # 3/4: tuples
        assert points[3].concentration == 200.0 and points[3].loading == 5.0
        assert points[4].concentration == 300.0 and points[4].measurement_std == 0.2

    def test_assays_to_points_rejects_unknown_input(self) -> None:
        with pytest.raises(TypeError, match="Cannot coerce"):
            _assays_to_points([object()])

    def test_assays_to_points_rejects_empty(self) -> None:
        from dpsim.assay_record import AssayKind, AssayRecord
        ar = AssayRecord(
            record_id="empty",
            kind=AssayKind.STATIC_BINDING_CAPACITY,
            units="mol/m^3",
            replicates=[],
            process_conditions={"concentration_mol_m3": 100.0},
        )
        with pytest.raises(ValueError, match="empty"):
            _assays_to_points([ar])
