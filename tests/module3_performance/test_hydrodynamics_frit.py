"""B-1g / W-024 tests: frit / distributor series resistance.

Covers the new ``ColumnGeometry.frit_permeability_m2`` /
``frit_thickness_m`` Optional fields and the
``frit_pressure_drop`` method.

Backwards-compat invariant: the default ``ColumnGeometry()`` carries
``frit_permeability_m2 = None`` and ``frit_thickness_m = None``; the
existing 494-test baseline must remain green after this change.
"""

from __future__ import annotations

import math

import pytest

from dpsim.module3_performance.hydrodynamics import ColumnGeometry


class TestFritDefaults:
    """Default ColumnGeometry has no frit configured (backwards compat)."""

    def test_default_frit_permeability_is_none(self) -> None:
        col = ColumnGeometry()
        assert col.frit_permeability_m2 is None

    def test_default_frit_thickness_is_none(self) -> None:
        col = ColumnGeometry()
        assert col.frit_thickness_m is None

    def test_default_frit_pressure_drop_is_zero(self) -> None:
        col = ColumnGeometry()
        # At a typical analytical-scale flow (1 mL/min)
        Q = 1e-6 / 60.0  # m^3/s
        assert col.frit_pressure_drop(Q) == 0.0


class TestFritPartiallyConfigured:
    """Setting only one of the two frit fields → still returns 0.0.

    Both must be set (non-None) for the contribution to be active.
    """

    def test_only_permeability_set_returns_zero(self) -> None:
        col = ColumnGeometry(frit_permeability_m2=1e-13)
        assert col.frit_pressure_drop(1e-7) == 0.0

    def test_only_thickness_set_returns_zero(self) -> None:
        col = ColumnGeometry(frit_thickness_m=1e-3)
        assert col.frit_pressure_drop(1e-7) == 0.0


class TestFritFullyConfigured:
    """Both fields set → ΔP_frit = μ · u · t / k_f."""

    def test_canonical_sintered_PE_frit(self) -> None:
        # 10 µm sintered PE frit: k_f ≈ 1×10⁻¹³ m², t ≈ 1 mm.
        # Analytical column: D_c = 1 cm → A = π/4 · (1e-2)² = 7.854e-5 m².
        # Q = 1 mL/min = 1.667e-8 m³/s → u = 2.122e-4 m/s.
        # μ = 1e-3 Pa·s (water).
        # ΔP_frit = 1e-3 · 2.122e-4 · 1e-3 / 1e-13 = 2.122 Pa.
        # (Small in absolute terms; on a clean column where bed ΔP
        # might be ~50 kPa the frit is < 1 % of total — but on a high-
        # flow preparative column the ratio shifts toward 10–30 %.)
        col = ColumnGeometry(
            frit_permeability_m2=1e-13,
            frit_thickness_m=1e-3,
        )
        Q = 1e-6 / 60.0
        dP_frit = col.frit_pressure_drop(Q, mu=1e-3)
        u = Q / col.cross_section_area
        expected = 1e-3 * u * 1e-3 / 1e-13
        assert math.isclose(dP_frit, expected, rel_tol=1e-9)

    def test_scales_linearly_with_flow(self) -> None:
        col = ColumnGeometry(
            frit_permeability_m2=1e-13,
            frit_thickness_m=1e-3,
        )
        dP_low = col.frit_pressure_drop(1e-8, mu=1e-3)
        dP_high = col.frit_pressure_drop(1e-7, mu=1e-3)
        assert math.isclose(dP_high / dP_low, 10.0, rel_tol=1e-9)

    def test_scales_linearly_with_viscosity(self) -> None:
        col = ColumnGeometry(
            frit_permeability_m2=1e-13,
            frit_thickness_m=1e-3,
        )
        Q = 1e-7
        dP_water = col.frit_pressure_drop(Q, mu=1e-3)
        dP_glycerol = col.frit_pressure_drop(Q, mu=2e-3)
        assert math.isclose(dP_glycerol / dP_water, 2.0, rel_tol=1e-9)

    def test_scales_inversely_with_permeability(self) -> None:
        # Tighter frit (smaller k_f) → higher ΔP_frit.
        col_tight = ColumnGeometry(
            frit_permeability_m2=1e-14,
            frit_thickness_m=1e-3,
        )
        col_loose = ColumnGeometry(
            frit_permeability_m2=1e-13,
            frit_thickness_m=1e-3,
        )
        Q = 1e-7
        assert col_tight.frit_pressure_drop(Q) == 10.0 * col_loose.frit_pressure_drop(Q)


class TestFritValidation:
    """Pathological inputs raise ValueError."""

    def test_zero_permeability_raises(self) -> None:
        col = ColumnGeometry(
            frit_permeability_m2=0.0,
            frit_thickness_m=1e-3,
        )
        with pytest.raises(ValueError, match="permeability must be > 0"):
            col.frit_pressure_drop(1e-7)

    def test_negative_permeability_raises(self) -> None:
        col = ColumnGeometry(
            frit_permeability_m2=-1e-13,
            frit_thickness_m=1e-3,
        )
        with pytest.raises(ValueError, match="permeability must be > 0"):
            col.frit_pressure_drop(1e-7)

    def test_negative_thickness_raises(self) -> None:
        col = ColumnGeometry(
            frit_permeability_m2=1e-13,
            frit_thickness_m=-1e-3,
        )
        with pytest.raises(ValueError, match="thickness must be ≥ 0"):
            col.frit_pressure_drop(1e-7)

    def test_zero_thickness_returns_zero(self) -> None:
        # Zero thickness is physically meaningful (no frit at all);
        # contribution should be exactly zero, not an error.
        col = ColumnGeometry(
            frit_permeability_m2=1e-13,
            frit_thickness_m=0.0,
        )
        assert col.frit_pressure_drop(1e-7) == 0.0
