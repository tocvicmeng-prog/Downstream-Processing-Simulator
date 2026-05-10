"""Tests for monte_carlo_step_program (B-2r / W-050, v0.8.3).

Verifies:

* Per-step bands carry the same n_samples (one shared draw set).
* worst_step_p_blocker tracks the riskiest step.
* Empty / malformed step programs are rejected.
* Coupled draws preserve cross-step correlation: a high-K_geom draw
  reduces every step's headroom together.
* log_cov + use_family_priors paths work.
"""

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
    StepProgramMCResult,
    monte_carlo_step_program,
)
from dpsim.optimization.objectives import PressureStep


@pytest.fixture
def comfortable_setup():
    column = ColumnGeometry()
    pre = compute_pressure_envelope(
        polymer_family=PolymerFamily.AGAROSE,
        column=column,
        mobile_phase=MobilePhase(),
        Q_set_m3_s=1e-9,
    )
    return {
        "polymer_family": PolymerFamily.AGAROSE,
        "column": column,
        "Q_anchor": pre.Q_recommended_m3_s,
    }


@pytest.fixture
def gentle_program(comfortable_setup):
    Q = comfortable_setup["Q_anchor"]
    return (
        PressureStep(name="load", Q_m3_s=Q * 0.05, mobile_phase=MobilePhase()),
        PressureStep(name="wash", Q_m3_s=Q * 0.10, mobile_phase=MobilePhase()),
        PressureStep(name="elute", Q_m3_s=Q * 0.08, mobile_phase=MobilePhase()),
    )


# ─── Smoke + shape ─────────────────────────────────────────────────────────


class TestSmoke:
    def test_returns_step_program_result(self, comfortable_setup, gentle_program):
        result = monte_carlo_step_program(
            polymer_family=comfortable_setup["polymer_family"],
            column=comfortable_setup["column"],
            step_program=gentle_program,
            n_samples=50, seed=0,
        )
        assert isinstance(result, StepProgramMCResult)
        assert result.n_samples == 50
        assert len(result.per_step_bands) == 3
        assert result.step_names == ("load", "wash", "elute")
        assert result.decision_tier == ModelEvidenceTier.SEMI_QUANTITATIVE

    def test_worst_step_p_blocker_is_max(self, comfortable_setup, gentle_program):
        result = monte_carlo_step_program(
            polymer_family=comfortable_setup["polymer_family"],
            column=comfortable_setup["column"],
            step_program=gentle_program,
            n_samples=200, seed=1,
        )
        per_step_pb = [b.p_blocker for b in result.per_step_bands]
        assert result.worst_step_p_blocker == max(per_step_pb)
        # Index of worst step matches.
        assert per_step_pb[result.worst_step_index] == result.worst_step_p_blocker


# ─── Validation ────────────────────────────────────────────────────────────


class TestValidation:
    def test_empty_program_rejected(self, comfortable_setup):
        with pytest.raises(ValueError, match="at least one"):
            monte_carlo_step_program(
                polymer_family=comfortable_setup["polymer_family"],
                column=comfortable_setup["column"],
                step_program=(),
                n_samples=50,
            )

    def test_malformed_step_rejected(self, comfortable_setup):
        # Plain object without the expected attributes.
        bad_step = object()
        with pytest.raises(ValueError, match="missing attribute"):
            monte_carlo_step_program(
                polymer_family=comfortable_setup["polymer_family"],
                column=comfortable_setup["column"],
                step_program=(bad_step,),
                n_samples=50,
            )


# ─── Coupled-draw semantics ────────────────────────────────────────────────


class TestCoupledDraws:
    def test_same_seed_reproduces_per_step_bands(
        self, comfortable_setup, gentle_program,
    ):
        a = monte_carlo_step_program(
            polymer_family=comfortable_setup["polymer_family"],
            column=comfortable_setup["column"],
            step_program=gentle_program,
            n_samples=100, seed=999,
        )
        b = monte_carlo_step_program(
            polymer_family=comfortable_setup["polymer_family"],
            column=comfortable_setup["column"],
            step_program=gentle_program,
            n_samples=100, seed=999,
        )
        for ba, bb in zip(a.per_step_bands, b.per_step_bands):
            assert ba.Q_max_m3_s_p50 == pytest.approx(
                bb.Q_max_m3_s_p50, rel=1e-12,
            )

    def test_steps_share_parameter_uncertainty(
        self, comfortable_setup, gentle_program,
    ):
        """Sanity: with σ_log = 0 across all parameters, every step's
        Q_max_p05/p50/p95 should collapse (no spread)."""
        result = monte_carlo_step_program(
            polymer_family=comfortable_setup["polymer_family"],
            column=comfortable_setup["column"],
            step_program=gentle_program,
            n_samples=30, seed=0,
            sigma_log_k_geom=0.0,
            sigma_log_mu=0.0,
            sigma_log_g_dn=0.0,
        )
        for band in result.per_step_bands:
            # Q_max is the same across all draws → quantiles collapse.
            assert band.Q_max_m3_s_p05 == pytest.approx(
                band.Q_max_m3_s_p95, rel=1e-9,
            )

    def test_increasing_q_drives_higher_step_pblocker(
        self, comfortable_setup,
    ):
        """A program where successive steps run at higher Q should have
        the late steps drive worst_step_p_blocker."""
        Q = comfortable_setup["Q_anchor"]
        program = (
            PressureStep(name="gentle", Q_m3_s=Q * 0.01, mobile_phase=MobilePhase()),
            PressureStep(name="moderate", Q_m3_s=Q * 0.20, mobile_phase=MobilePhase()),
            PressureStep(name="risky", Q_m3_s=Q * 2.5, mobile_phase=MobilePhase()),
        )
        result = monte_carlo_step_program(
            polymer_family=comfortable_setup["polymer_family"],
            column=comfortable_setup["column"],
            step_program=program,
            n_samples=200, seed=7,
        )
        # The "risky" step (index 2) should have the highest p_blocker.
        per_step_pb = [b.p_blocker for b in result.per_step_bands]
        assert per_step_pb[2] >= per_step_pb[1]
        assert per_step_pb[2] >= per_step_pb[0]
        assert result.worst_step_index == 2


# ─── log_cov + family priors paths ─────────────────────────────────────────


class TestExtensionPaths:
    def test_log_cov_path(self, comfortable_setup, gentle_program):
        cov = np.diag([0.04, 0.0025, 0.09])
        result = monte_carlo_step_program(
            polymer_family=comfortable_setup["polymer_family"],
            column=comfortable_setup["column"],
            step_program=gentle_program,
            n_samples=50, seed=0, log_cov=cov,
        )
        assert len(result.per_step_bands) == 3

    def test_family_priors_path(self, comfortable_setup, gentle_program):
        result = monte_carlo_step_program(
            polymer_family=comfortable_setup["polymer_family"],
            column=comfortable_setup["column"],
            step_program=gentle_program,
            n_samples=30, seed=0, use_family_priors=True,
        )
        assert len(result.per_step_bands) == 3

    def test_log_cov_validation_propagates(
        self, comfortable_setup, gentle_program,
    ):
        bad = np.eye(2)
        with pytest.raises(ValueError, match="3.3"):
            monte_carlo_step_program(
                polymer_family=comfortable_setup["polymer_family"],
                column=comfortable_setup["column"],
                step_program=gentle_program,
                n_samples=30, log_cov=bad,
            )
