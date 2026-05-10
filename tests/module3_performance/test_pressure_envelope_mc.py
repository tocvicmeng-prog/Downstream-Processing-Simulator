"""Tests for the MC pressure envelope wrapper (B-2n / W-043, v0.8.2)."""

from __future__ import annotations

import numpy as np
import pytest

from dpsim.core.mobile_phase import MobilePhase
from dpsim.datatypes import ModelEvidenceTier, PolymerFamily
from dpsim.module3_performance.hydrodynamics import ColumnGeometry
from dpsim.module3_performance.pressure_envelope import (
    compute_pressure_envelope,
)
from dpsim.module3_performance.pressure_envelope_mc import (
    monte_carlo_pressure_envelope,
)


@pytest.fixture
def comfortable_inputs():
    """Inputs that produce a non-blocker headroom ratio in the deterministic
    envelope so MC bands span both feasible and tail-blocker draws."""
    column = ColumnGeometry()
    mp = MobilePhase()
    pre = compute_pressure_envelope(
        polymer_family=PolymerFamily.AGAROSE,
        column=column,
        mobile_phase=mp,
        Q_set_m3_s=1.0e-9,
    )
    return {
        "polymer_family": PolymerFamily.AGAROSE,
        "column": column,
        "mobile_phase": mp,
        "Q_set_m3_s": pre.Q_recommended_m3_s * 0.5,
    }


# ─── Smoke + shape ────────────────────────────────────────────────────────


class TestSmoke:
    def test_returns_bands_object(self, comfortable_inputs):
        bands = monte_carlo_pressure_envelope(
            **comfortable_inputs, n_samples=50, seed=42,
        )
        assert bands.n_samples == 50
        # Quantile triples are ordered.
        assert bands.Q_max_m3_s_p05 <= bands.Q_max_m3_s_p50 <= bands.Q_max_m3_s_p95
        assert bands.dP_predicted_pa_p05 <= bands.dP_predicted_pa_p50
        assert bands.headroom_ratio_p05 <= bands.headroom_ratio_p50 <= bands.headroom_ratio_p95

    def test_p_blocker_is_a_probability(self, comfortable_inputs):
        bands = monte_carlo_pressure_envelope(
            **comfortable_inputs, n_samples=100, seed=1,
        )
        assert 0.0 <= bands.p_blocker <= 1.0
        assert 0.0 <= bands.p_warning <= 1.0
        # Warning band always covers blocker band.
        assert bands.p_warning >= bands.p_blocker

    def test_decision_tier_is_semi_quantitative(self, comfortable_inputs):
        # Per ADR-007 — MC reflects priors, not posteriors.
        bands = monte_carlo_pressure_envelope(
            **comfortable_inputs, n_samples=30, seed=0,
        )
        assert bands.decision_tier == ModelEvidenceTier.SEMI_QUANTITATIVE


# ─── Statistical sanity ────────────────────────────────────────────────────


class TestStatisticalSanity:
    def test_p50_close_to_deterministic(self, comfortable_inputs):
        """The MC P50 should approximate the deterministic envelope."""
        det = compute_pressure_envelope(**comfortable_inputs)
        bands = monte_carlo_pressure_envelope(
            **comfortable_inputs, n_samples=300, seed=7,
        )
        # Allow 30 % tolerance — lognormal P50 differs slightly from
        # the median input due to KC nonlinearity.
        assert bands.Q_max_m3_s_p50 == pytest.approx(
            det.Q_max_m3_s, rel=0.30,
        )
        assert bands.headroom_ratio_p50 == pytest.approx(
            det.headroom_ratio, rel=0.30,
        )

    def test_zero_sigma_collapses_to_deterministic(self, comfortable_inputs):
        """When all priors are σ=0, every draw yields the deterministic
        envelope and P05 = P50 = P95."""
        det = compute_pressure_envelope(**comfortable_inputs)
        bands = monte_carlo_pressure_envelope(
            **comfortable_inputs,
            n_samples=20, seed=123,
            sigma_log_k_geom=0.0,
            sigma_log_mu=0.0,
            sigma_log_g_dn=0.0,
        )
        assert bands.Q_max_m3_s_p05 == pytest.approx(
            bands.Q_max_m3_s_p95, rel=1e-9,
        )
        assert bands.Q_max_m3_s_p50 == pytest.approx(
            det.Q_max_m3_s, rel=1e-3,
        )

    def test_higher_sigma_widens_bands(self, comfortable_inputs):
        narrow = monte_carlo_pressure_envelope(
            **comfortable_inputs,
            n_samples=200, seed=42,
            sigma_log_k_geom=0.05, sigma_log_mu=0.05, sigma_log_g_dn=0.05,
        )
        wide = monte_carlo_pressure_envelope(
            **comfortable_inputs,
            n_samples=200, seed=42,
            sigma_log_k_geom=0.5, sigma_log_mu=0.5, sigma_log_g_dn=0.5,
        )
        narrow_iqr = narrow.Q_max_m3_s_p95 - narrow.Q_max_m3_s_p05
        wide_iqr = wide.Q_max_m3_s_p95 - wide.Q_max_m3_s_p05
        assert wide_iqr > narrow_iqr

    def test_seed_reproducibility(self, comfortable_inputs):
        bands_a = monte_carlo_pressure_envelope(
            **comfortable_inputs, n_samples=50, seed=999,
        )
        bands_b = monte_carlo_pressure_envelope(
            **comfortable_inputs, n_samples=50, seed=999,
        )
        assert bands_a.Q_max_m3_s_p50 == pytest.approx(
            bands_b.Q_max_m3_s_p50, rel=1e-12,
        )

    def test_high_q_drives_tail_probability(self, comfortable_inputs):
        """At Q_set near Q_recommended, p_blocker should be small.
        At Q_set well above Q_max, p_blocker should be near 1."""
        det = compute_pressure_envelope(**comfortable_inputs)
        # Far above Q_max — should blocker every draw.
        risky_inputs = dict(comfortable_inputs)
        risky_inputs["Q_set_m3_s"] = det.Q_max_m3_s * 5.0
        bands = monte_carlo_pressure_envelope(
            **risky_inputs, n_samples=100, seed=11,
        )
        assert bands.p_blocker > 0.9


# ─── Validation ──────────────────────────────────────────────────────────


class TestValidation:
    def test_rejects_too_few_samples(self, comfortable_inputs):
        with pytest.raises(ValueError, match="n_samples"):
            monte_carlo_pressure_envelope(
                **comfortable_inputs, n_samples=5,
            )
