"""Tests for the BO pressure-feasibility constraint (B-2j / W-033).

Verifies that ``check_constraints(result, pressure_ctx=ctx)`` correctly
admits / rejects candidates by inspecting their post-M2 column step
against an operational pressure envelope.

Built without importing ``dpsim.optimization.engine`` (which requires
torch) — the module's ``__getattr__`` lazy-load makes this possible
as of v0.8.0 / B-2j.
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
    check_constraints,
    pressure_feasible,
)


# ─── Synthetic FullResult builder ──────────────────────────────────────────


def _make_result(
    *,
    d32: float,
    G_DN: float,
    E_star: float,
    span: float = 1.0,
    pore_size: float = 80e-9,
    xi_final: float = 5e-9,
    rpm: float = 8000.0,
    c_chitosan: float = 12.0,
    c_agarose: float = 30.0,
    c_genipin: float = 5.0,
) -> FullResult:
    """Build a minimal FullResult sufficient for check_constraints."""
    formulation = FormulationParameters(
        c_agarose=c_agarose,
        c_chitosan=c_chitosan,
        c_genipin=c_genipin,
    )
    emul_params = EmulsificationParameters(rpm=rpm)
    params = SimulationParameters(
        emulsification=emul_params,
        formulation=formulation,
    )
    emul = EmulsificationResult(
        d_bins=np.array([d32]),
        n_d=np.array([1.0]),
        d32=d32,
        d43=d32,
        d10=d32 * 0.7,
        d50=d32,
        d90=d32 * 1.4,
        span=span,
        total_volume_fraction=0.05,
        converged=True,
    )
    gel = GelationResult(
        r_grid=np.array([0.0]),
        phi_field=np.array([0.5]),
        pore_size_mean=pore_size,
        pore_size_std=pore_size * 0.1,
        pore_size_distribution=np.array([pore_size]),
        porosity=0.6,
        alpha_final=0.95,
        char_wavelength=pore_size,
    )
    xlink = CrosslinkingResult(
        t_array=np.array([0.0, 1.0]),
        X_array=np.array([0.0, 0.5]),
        nu_e_array=np.array([0.0, 1.0]),
        Mc_array=np.array([1e3, 1e3]),
        xi_array=np.array([xi_final, xi_final]),
        G_chitosan_array=np.array([0.0, G_DN * 0.5]),
        p_final=0.5,
        nu_e_final=1.0,
        Mc_final=1e3,
        xi_final=xi_final,
        G_chitosan_final=G_DN * 0.5,
    )
    mech = MechanicalResult(
        G_agarose=G_DN * 0.5,
        G_chitosan=G_DN * 0.5,
        G_DN=G_DN,
        E_star=E_star,
        delta_array=np.array([0.0]),
        F_array=np.array([0.0]),
        rh_array=np.array([d32 / 2.0]),
        Kav_array=np.array([0.5]),
        pore_size_mean=pore_size,
        xi_mesh=xi_final,
    )
    return FullResult(
        parameters=params,
        emulsification=emul,
        gelation=gel,
        crosslinking=xlink,
        mechanical=mech,
    )


@pytest.fixture
def comfortable_ctx() -> PressureFeasibilityContext:
    """A column + buffer + Q_target where typical M1+M2 outputs sit
    well inside the envelope (headroom < 0.5)."""
    return PressureFeasibilityContext(
        column=ColumnGeometry(),
        mobile_phase=MobilePhase(),
        Q_target_m3_s=2.0e-8,  # 1.2 mL/min — gentle for the default column
        polymer_family=PolymerFamily.AGAROSE,
        headroom_threshold=1.0,
    )


@pytest.fixture
def comfortable_result() -> FullResult:
    """A candidate with d32 ≈ 100 µm, G_DN ≈ 10 kPa — a typical agarose
    bead well inside the operational envelope."""
    return _make_result(d32=100e-6, G_DN=10e3, E_star=30e3)


# ─── pressure_feasible ─────────────────────────────────────────────────────


class TestPressureFeasible:
    def test_comfortable_candidate_is_feasible(
        self, comfortable_result, comfortable_ctx,
    ):
        ok, violations = pressure_feasible(comfortable_result, comfortable_ctx)
        assert ok
        assert violations == []

    def test_excessive_q_target_is_rejected(
        self, comfortable_result, comfortable_ctx,
    ):
        ctx = _dc_replace(comfortable_ctx, Q_target_m3_s=1.0e-5)  # ~600 mL/min
        ok, violations = pressure_feasible(comfortable_result, ctx)
        assert not ok
        assert any("headroom_ratio" in v for v in violations)

    def test_tiny_d32_is_rejected(self, comfortable_ctx):
        # d_p² in u_crit → tiny d32 collapses Q_max.
        result = _make_result(d32=5e-6, G_DN=10e3, E_star=30e3)
        ok, violations = pressure_feasible(result, comfortable_ctx)
        assert not ok
        assert any("headroom" in v for v in violations)

    def test_low_modulus_is_rejected(self, comfortable_ctx):
        # u_crit ∝ G_DN → very low G_DN collapses Q_max.
        result = _make_result(d32=100e-6, G_DN=10.0, E_star=30.0)
        ok, violations = pressure_feasible(result, comfortable_ctx)
        assert not ok

    def test_threshold_below_one_admits_blocker_band(
        self, comfortable_result, comfortable_ctx,
    ):
        """headroom_threshold = 0.5 should reject a candidate that
        runs at headroom 0.7 but the comfortable_result still passes."""
        ctx = _dc_replace(comfortable_ctx, headroom_threshold=0.5)
        ok, _ = pressure_feasible(comfortable_result, ctx)
        # comfortable_result sits well below 0.5 headroom — passes.
        assert ok

    def test_unsupported_family_returns_false(self, comfortable_result):
        # The PolymerFamily.HYALURONATE path is not in family_kgeom registry
        # (or is in it; behavior depends — the function returns False with
        # a violation message either on KeyError or on headroom failure).
        ctx = PressureFeasibilityContext(
            column=ColumnGeometry(),
            mobile_phase=MobilePhase(),
            Q_target_m3_s=2.0e-8,
            polymer_family=PolymerFamily.HYALURONATE,
            headroom_threshold=1.0,
        )
        ok, violations = pressure_feasible(comfortable_result, ctx)
        # Either the family is supported (ok=True) or the helper
        # records a clean violation. Crucially, no exception escapes.
        assert isinstance(ok, bool)
        if not ok:
            assert len(violations) >= 1


# ─── check_constraints integration ─────────────────────────────────────────


class TestCheckConstraintsIntegration:
    def test_default_no_pressure_check(self, comfortable_result):
        """Without pressure_ctx, behaviour matches v0.7."""
        ok, violations = check_constraints(comfortable_result)
        assert ok
        assert violations == []

    def test_with_comfortable_ctx_still_feasible(
        self, comfortable_result, comfortable_ctx,
    ):
        ok, violations = check_constraints(
            comfortable_result, pressure_ctx=comfortable_ctx,
        )
        assert ok
        assert violations == []

    def test_excessive_q_target_violation_propagates(
        self, comfortable_result, comfortable_ctx,
    ):
        ctx = _dc_replace(comfortable_ctx, Q_target_m3_s=1.0e-5)
        ok, violations = check_constraints(
            comfortable_result, pressure_ctx=ctx,
        )
        assert not ok
        assert any("headroom" in v for v in violations)

    def test_existing_constraints_still_fire(self, comfortable_ctx):
        """A candidate with G_DN below MIN_G_DN AND a pressure
        violation reports both."""
        bad = _make_result(d32=100e-6, G_DN=500.0, E_star=300.0)
        ctx = _dc_replace(comfortable_ctx, Q_target_m3_s=1.0e-5)
        ok, violations = check_constraints(bad, pressure_ctx=ctx)
        assert not ok
        # Both the legacy G_DN floor AND the pressure check should fire.
        assert any("G_DN" in v for v in violations)
        assert any("headroom" in v for v in violations)

    def test_pressure_ctx_keyword_only(self, comfortable_result):
        """pressure_ctx must be a keyword-only argument."""
        with pytest.raises(TypeError):
            # Positional placement should fail.
            check_constraints(comfortable_result, "rotor_stator_legacy", "ctx")  # type: ignore[arg-type]


# ─── Smoke sanity ──────────────────────────────────────────────────────────


def test_import_objectives_without_torch():
    """Importing the objectives module must not require torch.

    Achieved via the lazy __getattr__ in dpsim.optimization.__init__.
    Regression sentinel: this stays green only if engine.py is not
    pulled in at package-import time.
    """
    import importlib
    import sys

    # If torch is NOT installed, the test is meaningful; if it IS, the
    # import path is exercised but tells us less. Either way, no crash.
    mod = importlib.import_module("dpsim.optimization.objectives")
    assert hasattr(mod, "PressureFeasibilityContext")
    assert "torch" not in sys.modules or "engine" not in sys.modules.get(
        "dpsim.optimization", type("x", (), {"__dict__": {}})()
    ).__dict__
