"""Tests for v0.8.3 MC envelope extensions:

* B-2p / W-048: per-family priors via FamilyMCPrior + use_family_priors flag.
* B-2q / W-049: correlated MC priors via log_cov (multivariate normal).
"""

from __future__ import annotations

import numpy as np
import pytest

from dpsim.core.mobile_phase import MobilePhase
from dpsim.datatypes import PolymerFamily
from dpsim.module3_performance.hydrodynamics import ColumnGeometry
from dpsim.module3_performance.pressure_envelope import (
    compute_pressure_envelope,
)
from dpsim.module3_performance.pressure_envelope_mc import (
    FamilyMCPrior,
    lookup_family_mc_prior,
    monte_carlo_pressure_envelope,
)


@pytest.fixture
def comfortable_inputs():
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
        "Q_set_m3_s": pre.Q_recommended_m3_s * 0.5,
    }


# ─── W-048: per-family priors ─────────────────────────────────────────────


class TestFamilyPriorsLookup:
    def test_returns_default_for_unknown_family(self):
        # HYALURONATE is not in the v0.8.3 _FAMILY_MC_PRIORS registry.
        prior = lookup_family_mc_prior(PolymerFamily.HYALURONATE)
        assert isinstance(prior, FamilyMCPrior)
        assert prior.sigma_log_k_geom == 0.20  # default fallback

    def test_returns_registered_prior_for_known_family(self):
        plga = lookup_family_mc_prior(PolymerFamily.PLGA)
        # PLGA has the widest σ_log_g_dn per the registry.
        assert plga.sigma_log_g_dn > 0.30

    def test_alginate_has_widest_g_dn(self):
        # ALGINATE per registry has σ_log_g_dn = 0.45.
        prior = lookup_family_mc_prior(PolymerFamily.ALGINATE)
        assert prior.sigma_log_g_dn == pytest.approx(0.45)


class TestUseFamilyPriorsFlag:
    def test_flag_off_uses_default_when_sigma_none(self, comfortable_inputs):
        bands = monte_carlo_pressure_envelope(
            **comfortable_inputs, n_samples=50, seed=0,
            use_family_priors=False,
            sigma_log_k_geom=None,
            sigma_log_mu=None,
            sigma_log_g_dn=None,
        )
        # Non-zero spread → bands have width.
        assert bands.Q_max_m3_s_p95 > bands.Q_max_m3_s_p05

    def test_flag_on_picks_up_family_prior(self, comfortable_inputs):
        # AGAROSE's σ_log_g_dn = 0.25 < default 0.30 → narrower G_DN bands.
        narrow = monte_carlo_pressure_envelope(
            **comfortable_inputs, n_samples=300, seed=11,
            use_family_priors=True,
        )
        wide = monte_carlo_pressure_envelope(
            **comfortable_inputs, n_samples=300, seed=11,
            use_family_priors=False,
        )
        # Both run with the same seed so RNG state matches; the σ
        # difference produces a narrower spread on Q_max.
        narrow_iqr = narrow.Q_max_m3_s_p95 - narrow.Q_max_m3_s_p05
        wide_iqr = wide.Q_max_m3_s_p95 - wide.Q_max_m3_s_p05
        # Allow narrow ≤ wide with some tolerance.
        assert narrow_iqr <= wide_iqr * 1.05

    def test_explicit_sigma_overrides_family(self, comfortable_inputs):
        # Even with use_family_priors=True, an explicit σ value wins.
        bands = monte_carlo_pressure_envelope(
            **comfortable_inputs, n_samples=50, seed=0,
            use_family_priors=True,
            sigma_log_k_geom=0.0,
            sigma_log_mu=0.0,
            sigma_log_g_dn=0.0,
        )
        # All zeros → P05 == P95 (no spread).
        assert bands.Q_max_m3_s_p05 == pytest.approx(
            bands.Q_max_m3_s_p95, rel=1e-9,
        )


# ─── W-049: correlated MC priors ──────────────────────────────────────────


class TestLogCovValidation:
    def test_wrong_shape_rejected(self, comfortable_inputs):
        bad = np.eye(2) * 0.1  # 2×2, should be 3×3
        with pytest.raises(ValueError, match="3.3"):
            monte_carlo_pressure_envelope(
                **comfortable_inputs, n_samples=30, log_cov=bad,
            )

    def test_non_symmetric_rejected(self, comfortable_inputs):
        bad = np.array([
            [0.04, 0.01, 0.0],
            [0.0, 0.0025, 0.0],   # 0.01 vs 0.0 → non-symmetric
            [0.0, 0.0, 0.09],
        ])
        with pytest.raises(ValueError, match="symmetric"):
            monte_carlo_pressure_envelope(
                **comfortable_inputs, n_samples=30, log_cov=bad,
            )

    def test_non_psd_rejected(self, comfortable_inputs):
        # Negative on the diagonal → NPSD.
        bad = np.array([
            [-0.04, 0.0, 0.0],
            [0.0, 0.0025, 0.0],
            [0.0, 0.0, 0.09],
        ])
        with pytest.raises(ValueError, match="positive-semi-definite"):
            monte_carlo_pressure_envelope(
                **comfortable_inputs, n_samples=30, log_cov=bad,
            )


class TestLogCovDiagonalPath:
    def test_diagonal_matches_independent_path(self, comfortable_inputs):
        """When log_cov is diag(σ²), results should match the independent
        sampling path with the same σ values (same seed)."""
        sigma_kg, sigma_mu, sigma_g = 0.20, 0.05, 0.30
        diag = np.diag([sigma_kg ** 2, sigma_mu ** 2, sigma_g ** 2])

        bands_indep = monte_carlo_pressure_envelope(
            **comfortable_inputs, n_samples=200, seed=42,
            sigma_log_k_geom=sigma_kg,
            sigma_log_mu=sigma_mu,
            sigma_log_g_dn=sigma_g,
        )
        bands_cov = monte_carlo_pressure_envelope(
            **comfortable_inputs, n_samples=200, seed=42, log_cov=diag,
        )
        # Both paths sample lognormal multiplicative shocks; with the
        # SAME diagonal variance, posterior bands are statistically
        # equivalent (same numerical result is not guaranteed because
        # the multivariate-normal RNG path is not identical to three
        # univariate normals, but the bands should agree within 30 %
        # at n=200).
        assert bands_indep.Q_max_m3_s_p50 == pytest.approx(
            bands_cov.Q_max_m3_s_p50, rel=0.30,
        )


class TestLogCovCorrelation:
    def test_strong_positive_correlation_widens_kg_g_joint_band(
        self, comfortable_inputs,
    ):
        """Strong + correlation between K_geom and G_DN → both move
        together → joint spread on Q_max widens vs independent."""
        # Diagonal baseline.
        diag = np.diag([0.04, 0.0025, 0.09])  # σ_kg=0.2, σ_mu=0.05, σ_g=0.3
        # Same diagonal but with strong + correlation between K_geom & G_DN.
        cov_corr = diag.copy()
        rho = 0.9
        cov_corr[0, 2] = rho * 0.2 * 0.3
        cov_corr[2, 0] = cov_corr[0, 2]

        bands_diag = monte_carlo_pressure_envelope(
            **comfortable_inputs, n_samples=400, seed=7, log_cov=diag,
        )
        bands_corr = monte_carlo_pressure_envelope(
            **comfortable_inputs, n_samples=400, seed=7, log_cov=cov_corr,
        )
        diag_iqr = bands_diag.Q_max_m3_s_p95 - bands_diag.Q_max_m3_s_p05
        corr_iqr = bands_corr.Q_max_m3_s_p95 - bands_corr.Q_max_m3_s_p05
        # Both K_geom and G_DN positively scale Q_max, so a + correlation
        # between them widens the Q_max IQR.
        assert corr_iqr > diag_iqr

    def test_seed_reproducibility_with_log_cov(self, comfortable_inputs):
        cov = np.diag([0.04, 0.0025, 0.09])
        a = monte_carlo_pressure_envelope(
            **comfortable_inputs, n_samples=100, seed=999, log_cov=cov,
        )
        b = monte_carlo_pressure_envelope(
            **comfortable_inputs, n_samples=100, seed=999, log_cov=cov,
        )
        assert a.Q_max_m3_s_p50 == pytest.approx(b.Q_max_m3_s_p50, rel=1e-12)
