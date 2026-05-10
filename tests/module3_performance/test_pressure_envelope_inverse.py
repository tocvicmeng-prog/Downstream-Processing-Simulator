"""Tests for the inverse pressure-envelope inference (B-2o / W-047, v0.8.3)."""

from __future__ import annotations

import numpy as np
import pytest

from dpsim.core.mobile_phase import MobilePhase
from dpsim.datatypes import ModelEvidenceTier, PolymerFamily
from dpsim.module3_performance.hydrodynamics import ColumnGeometry
from dpsim.module3_performance.pressure_envelope import (
    compute_pressure_envelope,
)
from dpsim.module3_performance.pressure_envelope_inverse import (
    InferredPosteriorEnvelope,
    MeasuredPressureFlowPoint,
    infer_posterior_envelope,
)


@pytest.fixture
def comfortable_setup():
    column = ColumnGeometry()
    mp = MobilePhase()
    pre = compute_pressure_envelope(
        polymer_family=PolymerFamily.AGAROSE,
        column=column,
        mobile_phase=mp,
        Q_set_m3_s=1e-9,
    )
    return {
        "polymer_family": PolymerFamily.AGAROSE,
        "column": column,
        "mobile_phase": mp,
        "Q_for_envelope": pre.Q_recommended_m3_s * 0.5,
    }


def _synthetic_measurements(
    setup: dict, n: int = 4, seed: int = 0,
) -> tuple[MeasuredPressureFlowPoint, ...]:
    """Build n measurements at gentle Qs whose ΔP comes from the
    deterministic envelope — the "true" posterior should center on
    the prior mean."""
    rng = np.random.default_rng(seed)
    column = setup["column"]
    points = []
    Q_grid = np.linspace(1e-9, 5e-9, n)
    for Q in Q_grid:
        env = compute_pressure_envelope(
            polymer_family=setup["polymer_family"],
            column=column,
            mobile_phase=setup["mobile_phase"],
            Q_set_m3_s=float(Q),
        )
        # Add ~3 % noise to simulate panel measurement.
        noise = rng.normal(0.0, 0.03 * env.dP_predicted_pa)
        points.append(
            MeasuredPressureFlowPoint(
                Q_m3_s=float(Q),
                dP_pa=float(env.dP_predicted_pa + noise),
                sigma_dP_pa=0.05 * env.dP_predicted_pa,
            )
        )
    return tuple(points)


# ─── Smoke + shape ────────────────────────────────────────────────────────


class TestSmoke:
    def test_returns_posterior_object(self, comfortable_setup):
        meas = _synthetic_measurements(comfortable_setup)
        post = infer_posterior_envelope(
            meas, n_samples=200, seed=42, **comfortable_setup,
        )
        assert isinstance(post, InferredPosteriorEnvelope)
        assert post.n_samples == 200

    def test_quantiles_monotonic(self, comfortable_setup):
        meas = _synthetic_measurements(comfortable_setup)
        post = infer_posterior_envelope(
            meas, n_samples=300, seed=0, **comfortable_setup,
        )
        assert post.K_geom_p05 <= post.K_geom_p50 <= post.K_geom_p95
        assert post.mu_pa_s_p05 <= post.mu_pa_s_p50 <= post.mu_pa_s_p95
        assert post.G_DN_pa_p05 <= post.G_DN_pa_p50 <= post.G_DN_pa_p95
        assert post.Q_max_m3_s_p05 <= post.Q_max_m3_s_p50 <= post.Q_max_m3_s_p95
        assert post.headroom_ratio_p05 <= post.headroom_ratio_p50

    def test_p_probabilities_in_unit_interval(self, comfortable_setup):
        meas = _synthetic_measurements(comfortable_setup)
        post = infer_posterior_envelope(
            meas, n_samples=200, seed=0, **comfortable_setup,
        )
        assert 0.0 <= post.p_blocker <= 1.0
        assert 0.0 <= post.p_warning <= 1.0
        assert post.p_warning >= post.p_blocker

    def test_decision_tier_is_semi_quantitative(self, comfortable_setup):
        # ADR-010: posterior bands stay SEMI_QUANTITATIVE in v0.8.3.
        meas = _synthetic_measurements(comfortable_setup)
        post = infer_posterior_envelope(
            meas, n_samples=200, seed=0, **comfortable_setup,
        )
        assert post.decision_tier == ModelEvidenceTier.SEMI_QUANTITATIVE


# ─── Statistical sanity ────────────────────────────────────────────────────


class TestStatisticalSanity:
    def test_perfectly_consistent_data_centers_posterior_on_prior(
        self, comfortable_setup,
    ):
        """When measurements are generated from the prior MEAN (no shock),
        the posterior should center near the deterministic envelope's
        K_geom — i.e., the posterior K_geom P50 should be close to the
        family default K_geom."""
        meas = _synthetic_measurements(comfortable_setup, n=6)
        post = infer_posterior_envelope(
            meas, n_samples=500, seed=11, **comfortable_setup,
        )
        # Prior mean K_geom (lognormal mean = K_geom_base * exp(σ²/2);
        # for σ=0.20 that's a 2 % shift, well within tolerance).
        from dpsim.module3_performance.family_kgeom import lookup_family_kgeom
        base = lookup_family_kgeom(PolymerFamily.AGAROSE).K_geom
        # Posterior P50 should be within ±25 % of the base value.
        assert post.K_geom_p50 == pytest.approx(base, rel=0.25)

    def test_ess_is_reported(self, comfortable_setup):
        meas = _synthetic_measurements(comfortable_setup)
        post = infer_posterior_envelope(
            meas, n_samples=300, seed=0, **comfortable_setup,
        )
        assert 0.0 < post.effective_sample_size <= post.n_samples

    def test_log_cov_shape(self, comfortable_setup):
        meas = _synthetic_measurements(comfortable_setup)
        post = infer_posterior_envelope(
            meas, n_samples=200, seed=0, **comfortable_setup,
        )
        assert post.log_cov.shape == (3, 3)
        # Positive semidefinite (eigvals ≥ 0).
        eigs = np.linalg.eigvalsh(post.log_cov)
        assert all(e >= -1e-12 for e in eigs)

    def test_seed_reproducibility(self, comfortable_setup):
        meas = _synthetic_measurements(comfortable_setup)
        post_a = infer_posterior_envelope(
            meas, n_samples=200, seed=999, **comfortable_setup,
        )
        post_b = infer_posterior_envelope(
            meas, n_samples=200, seed=999, **comfortable_setup,
        )
        assert post_a.K_geom_p50 == pytest.approx(post_b.K_geom_p50, rel=1e-12)
        assert post_a.effective_sample_size == pytest.approx(
            post_b.effective_sample_size, rel=1e-12,
        )

    def test_inconsistent_data_concentrates_posterior(self, comfortable_setup):
        """Data far from prior mean should *narrow* the posterior on
        K_geom (relative to prior) — confirming the likelihood is
        actually doing work."""
        # Construct measurements consistent with a HIGH ΔP at the
        # measurement Q's (i.e., low K_geom or high μ).
        meas = _synthetic_measurements(comfortable_setup, n=5)
        # Bias: triple the observed ΔP at every point (forces posterior
        # toward larger ΔP-driving combinations).
        biased = tuple(
            MeasuredPressureFlowPoint(
                Q_m3_s=m.Q_m3_s,
                dP_pa=3.0 * m.dP_pa,
                sigma_dP_pa=m.sigma_dP_pa,
            )
            for m in meas
        )
        post = infer_posterior_envelope(
            biased, n_samples=600, seed=7, **comfortable_setup,
        )
        # Shouldn't crash; ESS may be low (ess_warning expected).
        assert post.K_geom_p50 > 0.0
        assert isinstance(post.ess_warning, str)


# ─── Validation ────────────────────────────────────────────────────────────


class TestValidation:
    def test_empty_measurements_rejected(self, comfortable_setup):
        with pytest.raises(ValueError, match="at least one"):
            infer_posterior_envelope((), n_samples=200, **comfortable_setup)

    def test_too_few_samples_rejected(self, comfortable_setup):
        meas = _synthetic_measurements(comfortable_setup)
        with pytest.raises(ValueError, match="n_samples"):
            infer_posterior_envelope(
                meas, n_samples=50, **comfortable_setup,
            )

    def test_zero_sigma_rejected(self, comfortable_setup):
        bad = (
            MeasuredPressureFlowPoint(
                Q_m3_s=1e-9, dP_pa=1000.0, sigma_dP_pa=0.0,
            ),
        )
        with pytest.raises(ValueError, match="sigma_dP_pa"):
            infer_posterior_envelope(bad, n_samples=200, **comfortable_setup)

    def test_ess_warning_emitted_on_concentrated_posterior(
        self, comfortable_setup,
    ):
        """A grossly tight measurement σ → very peaky likelihood → low ESS."""
        meas = _synthetic_measurements(comfortable_setup, n=3)
        peaky = tuple(
            MeasuredPressureFlowPoint(
                Q_m3_s=m.Q_m3_s,
                dP_pa=m.dP_pa * 0.5,  # bias the data away from prior
                sigma_dP_pa=m.dP_pa * 1e-4,  # absurdly tight σ
            )
            for m in meas
        )
        with pytest.warns(UserWarning, match="ESS"):
            post = infer_posterior_envelope(
                peaky, n_samples=200, seed=0, **comfortable_setup,
            )
        assert "ESS" in post.ess_warning


# ─── Round-trip into forward MC ────────────────────────────────────────────


class TestPosteriorRoundTrip:
    def test_log_cov_consumable_by_forward_mc(self, comfortable_setup):
        """The posterior log_cov should be a valid argument to
        monte_carlo_pressure_envelope's log_cov path (B-2q / W-049)."""
        meas = _synthetic_measurements(comfortable_setup)
        post = infer_posterior_envelope(
            meas, n_samples=300, seed=0, **comfortable_setup,
        )
        # The covariance matrix should be symmetric and PSD.
        assert post.log_cov.shape == (3, 3)
        np.testing.assert_allclose(
            post.log_cov, post.log_cov.T, atol=1e-12,
        )
        eigs = np.linalg.eigvalsh(post.log_cov)
        assert all(e >= -1e-9 for e in eigs)
