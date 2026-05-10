"""Multi-step BO pressure feasibility tests (B-2k / W-040, v0.8.2).

Verifies that ``PressureFeasibilityContext`` accepts a ``step_program``
and that ``pressure_feasible`` reports ALL step-level violations across
load / wash / elute / CIP, not just the first.
"""

from __future__ import annotations

from dataclasses import replace as _dc_replace

import numpy as np
import pytest

from dpsim.core.mobile_phase import MobilePhase
from dpsim.datatypes import (
    CrosslinkingResult,
    EmulsificationParameters,
    EmulsificationResult,
    FormulationParameters,
    FullResult,
    GelationResult,
    MechanicalResult,
    PolymerFamily,
    SimulationParameters,
)
from dpsim.module3_performance.hydrodynamics import ColumnGeometry
from dpsim.optimization.objectives import (
    PressureFeasibilityContext,
    PressureStep,
    pressure_feasible,
)


def _make_result(
    *, d32: float = 100e-6, G_DN: float = 10e3, E_star: float = 30e3,
) -> FullResult:
    """Minimal FullResult for the constraint check."""
    formulation = FormulationParameters(
        c_agarose=30.0, c_chitosan=12.0, c_genipin=5.0,
    )
    params = SimulationParameters(
        emulsification=EmulsificationParameters(rpm=8000.0),
        formulation=formulation,
    )
    emul = EmulsificationResult(
        d_bins=np.array([d32]), n_d=np.array([1.0]),
        d32=d32, d43=d32, d10=d32 * 0.7, d50=d32, d90=d32 * 1.4,
        span=1.0, total_volume_fraction=0.05, converged=True,
    )
    gel = GelationResult(
        r_grid=np.array([0.0]), phi_field=np.array([0.5]),
        pore_size_mean=80e-9, pore_size_std=8e-9,
        pore_size_distribution=np.array([80e-9]),
        porosity=0.6, alpha_final=0.95, char_wavelength=80e-9,
    )
    xlink = CrosslinkingResult(
        t_array=np.array([0.0, 1.0]),
        X_array=np.array([0.0, 0.5]),
        nu_e_array=np.array([0.0, 1.0]),
        Mc_array=np.array([1e3, 1e3]),
        xi_array=np.array([5e-9, 5e-9]),
        G_chitosan_array=np.array([0.0, G_DN * 0.5]),
        p_final=0.5, nu_e_final=1.0, Mc_final=1e3,
        xi_final=5e-9, G_chitosan_final=G_DN * 0.5,
    )
    mech = MechanicalResult(
        G_agarose=G_DN * 0.5, G_chitosan=G_DN * 0.5,
        G_DN=G_DN, E_star=E_star,
        delta_array=np.array([0.0]), F_array=np.array([0.0]),
        rh_array=np.array([d32 / 2.0]), Kav_array=np.array([0.5]),
        pore_size_mean=80e-9, xi_mesh=5e-9,
    )
    return FullResult(
        parameters=params, emulsification=emul, gelation=gel,
        crosslinking=xlink, mechanical=mech,
    )


@pytest.fixture
def comfortable_result():
    return _make_result()


@pytest.fixture
def comfortable_program():
    """Three steps where every Q sits well below Q_max."""
    return (
        PressureStep(name="load", Q_m3_s=1.0e-8, mobile_phase=MobilePhase()),
        PressureStep(name="wash", Q_m3_s=2.0e-8, mobile_phase=MobilePhase()),
        PressureStep(name="elute", Q_m3_s=1.5e-8, mobile_phase=MobilePhase()),
    )


@pytest.fixture
def base_ctx(comfortable_program):
    return PressureFeasibilityContext(
        column=ColumnGeometry(),
        mobile_phase=MobilePhase(),  # ignored when step_program supplied
        Q_target_m3_s=1.0e-8,        # ignored when step_program supplied
        polymer_family=PolymerFamily.AGAROSE,
        headroom_threshold=1.0,
        step_program=comfortable_program,
    )


# ─── Single-step backwards compat ──────────────────────────────────────────


class TestSingleStepBackwardCompat:
    def test_no_step_program_falls_back_to_legacy(self, comfortable_result):
        ctx = PressureFeasibilityContext(
            column=ColumnGeometry(),
            mobile_phase=MobilePhase(),
            Q_target_m3_s=1.0e-8,
            polymer_family=PolymerFamily.AGAROSE,
            step_program=None,  # explicit None — legacy path
        )
        ok, violations = pressure_feasible(comfortable_result, ctx)
        assert ok
        assert violations == []

    def test_default_step_program_is_none(self):
        # The default constructor argument for step_program must be None
        # so v0.8.0 callers see no behaviour change.
        ctx = PressureFeasibilityContext(
            column=ColumnGeometry(),
            mobile_phase=MobilePhase(),
            Q_target_m3_s=1.0e-8,
            polymer_family=PolymerFamily.AGAROSE,
        )
        assert ctx.step_program is None


# ─── Multi-step path ───────────────────────────────────────────────────────


class TestMultiStepProgram:
    def test_all_steps_feasible(self, comfortable_result, base_ctx):
        ok, violations = pressure_feasible(comfortable_result, base_ctx)
        assert ok
        assert violations == []

    def test_one_step_violation_caught(self, comfortable_result, base_ctx):
        bad_program = (
            PressureStep(name="load", Q_m3_s=1.0e-8, mobile_phase=MobilePhase()),
            # Wash at an absurdly high flow rate.
            PressureStep(name="wash", Q_m3_s=1.0e-5, mobile_phase=MobilePhase()),
            PressureStep(name="elute", Q_m3_s=1.5e-8, mobile_phase=MobilePhase()),
        )
        ctx = _dc_replace(base_ctx, step_program=bad_program)
        ok, violations = pressure_feasible(comfortable_result, ctx)
        assert not ok
        assert len(violations) == 1
        assert "wash" in violations[0]
        assert "headroom_ratio" in violations[0]

    def test_multiple_step_violations_all_reported(
        self, comfortable_result, base_ctx,
    ):
        bad_program = (
            PressureStep(name="load", Q_m3_s=1.0e-8, mobile_phase=MobilePhase()),
            PressureStep(name="wash", Q_m3_s=1.0e-5, mobile_phase=MobilePhase()),
            PressureStep(name="elute", Q_m3_s=2.0e-5, mobile_phase=MobilePhase()),
        )
        ctx = _dc_replace(base_ctx, step_program=bad_program)
        ok, violations = pressure_feasible(comfortable_result, ctx)
        assert not ok
        # Both violating steps should be reported, not just the first.
        assert len(violations) == 2
        assert any("wash" in v for v in violations)
        assert any("elute" in v for v in violations)

    def test_unsupported_family_per_step(self, comfortable_result, base_ctx):
        # HYALURONATE may or may not be in the K_geom registry; if absent,
        # every step records a clean violation.
        ctx = _dc_replace(base_ctx, polymer_family=PolymerFamily.HYALURONATE)
        ok, violations = pressure_feasible(comfortable_result, ctx)
        assert isinstance(ok, bool)
        if not ok:
            # Every step that hits the missing family must report.
            assert all(
                ("load" in v) or ("wash" in v) or ("elute" in v)
                for v in violations
            )

    def test_empty_step_program(self, comfortable_result, base_ctx):
        # Empty tuple: no steps to screen → trivially feasible.
        ctx = _dc_replace(base_ctx, step_program=())
        ok, violations = pressure_feasible(comfortable_result, ctx)
        assert ok
        assert violations == []
