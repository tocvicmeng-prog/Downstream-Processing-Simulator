"""Tests for F1 — M3 entry points accept Quantity-or-float on documented-unit args.

Reference: docs/handover/V0_6_0_QUANTITY_ACCESSORS_AND_PARALLELISM_HANDOVER.md
§9 v6.1-Q2 + §10.

Closes architect-coherence-audit Deficit 1 phase 2 (signature typing). Callers
can now pass either a ``Quantity`` (auto-converted to the expected unit) or
a bare ``float`` (assumed already in the expected unit) to the M3 entry
points. Backward-compatible: existing float-only callers keep working.
"""

from __future__ import annotations

import pytest

from dpsim.core.quantities import Quantity, unwrap_to_unit
from dpsim.module3_performance.hydrodynamics import ColumnGeometry
from dpsim.module3_performance.method import run_chromatography_method
from dpsim.module3_performance.orchestrator import run_breakthrough


def _small_column() -> ColumnGeometry:
    return ColumnGeometry(
        diameter=0.01,
        bed_height=0.05,
        particle_diameter=100e-6,
        bed_porosity=0.38,
        particle_porosity=0.5,
        G_DN=10000.0,
        E_star=30000.0,
    )


# ─── unwrap_to_unit helper ───────────────────────────────────────────────────


class TestUnwrapHelper:
    def test_float_passthrough(self):
        assert unwrap_to_unit(1.5, "mol/m3") == 1.5

    def test_int_passthrough_as_float(self):
        result = unwrap_to_unit(2, "s")
        assert result == 2.0
        assert isinstance(result, float)

    def test_quantity_in_target_unit(self):
        q = Quantity(1.5, "mol/m3", source="test")
        assert unwrap_to_unit(q, "mol/m3") == pytest.approx(1.5)

    def test_quantity_unit_conversion_mM_to_mol_m3(self):
        """1 mM = 1 mol/m3 (per the unit table)."""
        q = Quantity(1.0, "mM", source="test")
        assert unwrap_to_unit(q, "mol/m3") == pytest.approx(1.0)

    def test_quantity_unit_conversion_M_to_mol_m3(self):
        """1 M = 1000 mol/m3."""
        q = Quantity(1.0, "M", source="test")
        assert unwrap_to_unit(q, "mol/m3") == pytest.approx(1000.0)

    def test_quantity_unit_conversion_kpa_to_pa(self):
        q = Quantity(37.12, "kPa", source="test")
        assert unwrap_to_unit(q, "Pa") == pytest.approx(37120.0)

    def test_quantity_unit_conversion_min_to_s(self):
        q = Quantity(2.0, "min", source="test")
        assert unwrap_to_unit(q, "s") == pytest.approx(120.0)

    def test_unsupported_type_raises(self):
        with pytest.raises(TypeError, match="expected Quantity or float"):
            unwrap_to_unit("not_a_number", "mol/m3")  # type: ignore[arg-type]

    def test_incompatible_quantity_unit_raises(self):
        q = Quantity(1.0, "Pa", source="test")
        with pytest.raises(ValueError, match="Cannot convert"):
            unwrap_to_unit(q, "mol/m3")


# ─── run_breakthrough Quantity acceptance ───────────────────────────────────


@pytest.mark.slow
class TestRunBreakthroughQuantity:
    def test_accepts_C_feed_as_quantity_mM(self):
        column = _small_column()
        # 1 mM = 1 mol/m3, so this should produce the same result as
        # passing C_feed=1.0 directly.
        result = run_breakthrough(
            column=column,
            C_feed=Quantity(1.0, "mM"),
            flow_rate=1e-8,
            feed_duration=300.0,
            total_time=600.0,
            n_z=10,
        )
        assert result.dbc_10pct >= 0
        assert result.pressure_drop > 0

    def test_accepts_flow_rate_in_mL_per_min(self):
        column = _small_column()
        # 0.6 mL/min = 1e-8 m3/s, the canonical default.
        flow_q = Quantity(0.6, "mL/min")
        result = run_breakthrough(
            column=column,
            C_feed=1.0,
            flow_rate=flow_q,
            feed_duration=300.0,
            total_time=600.0,
            n_z=10,
        )
        assert result.dbc_10pct >= 0

    def test_accepts_durations_in_min(self):
        column = _small_column()
        result = run_breakthrough(
            column=column,
            C_feed=1.0,
            flow_rate=1e-8,
            feed_duration=Quantity(5.0, "min"),  # 300 s
            total_time=Quantity(10.0, "min"),     # 600 s
            n_z=10,
        )
        assert result.pressure_drop > 0

    def test_float_callers_still_work(self):
        """Backward-compat: existing float-only callers must continue working."""
        column = _small_column()
        result = run_breakthrough(
            column=column,
            C_feed=1.0,
            flow_rate=1e-8,
            feed_duration=300.0,
            total_time=600.0,
            n_z=10,
        )
        assert result.dbc_10pct >= 0


# ─── run_chromatography_method Quantity acceptance ──────────────────────────


@pytest.mark.slow
class TestRunChromatographyMethodQuantity:
    def test_accepts_pressure_limits_in_bar(self):
        column = _small_column()
        # 3 bar = 3e5 Pa, the default.
        result = run_chromatography_method(
            column=column,
            max_pressure_Pa=Quantity(3.0, "bar"),
            pump_pressure_limit_Pa=Quantity(3.0, "bar"),
            n_z=10,
        )
        assert result is not None
        assert result.operability.max_pressure_Pa == pytest.approx(3e5)
        assert result.operability.pump_pressure_limit_Pa == pytest.approx(3e5)

    def test_float_callers_still_work(self):
        """Backward-compat for the existing float-only callers."""
        column = _small_column()
        result = run_chromatography_method(
            column=column,
            max_pressure_Pa=3e5,
            pump_pressure_limit_Pa=3e5,
            n_z=10,
        )
        assert result is not None
