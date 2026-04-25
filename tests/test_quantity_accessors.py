"""Tests for E1 — typed Quantity accessor properties on M3 result dataclasses.

Reference: docs/handover/V0_5_0_DEPRECATION_REMOVAL_HANDOVER.md §10
(v0.6.0 / C1 phase 1).

Closes architect-coherence-audit Deficit 1 phase 1: result dataclasses now
expose typed ``Quantity`` accessors alongside the existing bare-float fields,
so downstream code can opt into unit-aware reads without breaking arithmetic
consumers.
"""

from __future__ import annotations

import numpy as np
import pytest

from dpsim.core.process_recipe import default_affinity_media_recipe
from dpsim.core.quantities import Quantity
from dpsim.lifecycle import DownstreamProcessOrchestrator
from dpsim.module3_performance.method import (
    ColumnOperabilityReport,
    LoadedStateElutionResult,
    ProteinAPerformanceReport,
)
from dpsim.module3_performance.orchestrator import BreakthroughResult


# ─── BreakthroughResult ──────────────────────────────────────────────────────


def _stub_breakthrough(*, dbc_10=10.0, pressure=37120.0, mb=0.001) -> BreakthroughResult:
    return BreakthroughResult(
        time=np.array([0.0, 1.0]),
        uv_signal=np.array([0.0, 1.0]),
        C_outlet=np.array([0.0, 0.5]),
        dbc_5pct=8.0,
        dbc_10pct=dbc_10,
        dbc_50pct=12.0,
        pressure_drop=pressure,
        mass_balance_error=mb,
    )


class TestBreakthroughResultAccessors:
    def test_dbc_10_accessor_returns_quantity(self):
        bt = _stub_breakthrough(dbc_10=10.5)
        q = bt.dbc_10pct_q
        assert isinstance(q, Quantity)
        assert q.value == pytest.approx(10.5)
        assert q.unit == "mol/m3"

    def test_dbc_5_and_50_accessors(self):
        bt = _stub_breakthrough()
        assert bt.dbc_5pct_q.value == pytest.approx(8.0)
        assert bt.dbc_50pct_q.value == pytest.approx(12.0)
        assert bt.dbc_5pct_q.unit == "mol/m3"
        assert bt.dbc_50pct_q.unit == "mol/m3"

    def test_pressure_drop_accessor_unit_conversion(self):
        bt = _stub_breakthrough(pressure=200000.0)  # 200 kPa
        q = bt.pressure_drop_q
        assert q.unit == "Pa"
        assert q.value == pytest.approx(200000.0)
        # The accessor returns a real Quantity that supports unit conversion.
        kpa = q.as_unit("kPa")
        assert kpa.value == pytest.approx(200.0)

    def test_mass_balance_error_dimensionless(self):
        bt = _stub_breakthrough(mb=0.025)
        q = bt.mass_balance_error_q
        assert q.unit == "1"
        assert q.value == pytest.approx(0.025)

    def test_accessor_value_matches_underlying_float(self):
        """The accessor's .value MUST equal the bare-float field."""
        bt = _stub_breakthrough()
        assert bt.dbc_10pct_q.value == bt.dbc_10pct
        assert bt.pressure_drop_q.value == bt.pressure_drop


# ─── LoadedStateElutionResult ────────────────────────────────────────────────


def _stub_elution() -> LoadedStateElutionResult:
    return LoadedStateElutionResult(
        time=np.array([0.0, 1.0]),
        C_outlet=np.array([0.0, 0.5]),
        uv_signal=np.array([0.0, 1.0]),
        q_average=np.array([0.0]),
        pH_profile=np.array([7.4, 3.5]),
        mass_initial_bound_mol=1e-6,
        mass_eluted_mol=8e-7,
        mass_remaining_bound_mol=2e-7,
        recovery_fraction=0.80,
        peak_time_s=120.0,
        peak_width_half_s=30.0,
        mass_balance_error=0.001,
    )


class TestLoadedStateElutionAccessors:
    def test_recovery_fraction_q(self):
        e = _stub_elution()
        assert e.recovery_fraction_q.value == pytest.approx(0.80)
        assert e.recovery_fraction_q.unit == "1"

    def test_peak_time_q_unit_conversion(self):
        e = _stub_elution()
        assert e.peak_time_q.value == pytest.approx(120.0)
        assert e.peak_time_q.unit == "s"
        assert e.peak_time_q.as_unit("min").value == pytest.approx(2.0)

    def test_peak_width_half_q(self):
        e = _stub_elution()
        assert e.peak_width_half_q.value == pytest.approx(30.0)
        assert e.peak_width_half_q.unit == "s"


# ─── ColumnOperabilityReport ─────────────────────────────────────────────────


def _stub_operability() -> ColumnOperabilityReport:
    return ColumnOperabilityReport(
        step_name="load",
        pressure_drop_Pa=37120.0,
        max_pressure_Pa=300000.0,
        pump_pressure_limit_Pa=300000.0,
        bed_compression_fraction=0.05,
        particle_reynolds=0.5,
        axial_peclet=200.0,
        residence_time_s=600.0,
        interstitial_velocity_m_s=1e-4,
        maldistribution_index=0.1,
        maldistribution_risk="low",
    )


class TestColumnOperabilityAccessors:
    def test_pressure_drop_q_kpa_conversion(self):
        op = _stub_operability()
        assert op.pressure_drop_q.unit == "Pa"
        assert op.pressure_drop_q.as_unit("kPa").value == pytest.approx(37.12)

    def test_residence_time_q_min_conversion(self):
        op = _stub_operability()
        assert op.residence_time_q.as_unit("min").value == pytest.approx(10.0)

    def test_bed_compression_dimensionless(self):
        op = _stub_operability()
        assert op.bed_compression_q.unit == "1"
        assert op.bed_compression_q.value == pytest.approx(0.05)


# ─── ProteinAPerformanceReport ──────────────────────────────────────────────


def _stub_protein_a() -> ProteinAPerformanceReport:
    return ProteinAPerformanceReport(
        q_max_mol_m3=60.0,
        load_pH=7.4,
        elution_pH=3.5,
        K_a_load_m3_mol=1e5,
        K_a_elution_m3_mol=1.0,
        q_equilibrium_load_mol_m3=50.0,
        ligand_accessibility_factor=0.8,
        activity_retention=0.85,
        mass_transfer_coefficient_m_s=1e-5,
        mass_transfer_resistance_s=1.0,
        alkaline_degradation_fraction_per_cycle=0.01,
        cycle_lifetime_to_70pct_capacity=200.0,
        ligand_leaching_fraction_per_cycle=0.005,
        leaching_risk="low",
        predicted_elution_recovery_fraction=0.85,
    )


class TestProteinAAccessors:
    def test_q_max_q(self):
        pa = _stub_protein_a()
        assert pa.q_max_q.value == pytest.approx(60.0)
        assert pa.q_max_q.unit == "mol/m3"

    def test_predicted_recovery_q(self):
        pa = _stub_protein_a()
        assert pa.predicted_recovery_q.value == pytest.approx(0.85)
        assert pa.predicted_recovery_q.unit == "1"

    def test_activity_retention_q(self):
        pa = _stub_protein_a()
        assert pa.activity_retention_q.value == pytest.approx(0.85)
        assert pa.activity_retention_q.unit == "1"

    def test_cycle_lifetime_q_documents_unsupported_status(self):
        pa = _stub_protein_a()
        q = pa.cycle_lifetime_q
        assert q.value == pytest.approx(200.0)
        assert "UNSUPPORTED" in q.note


# ─── End-to-end: lifecycle result accessors work after a real run ────────────


class TestLifecycleEndToEnd:
    def test_real_lifecycle_run_quantity_accessors(self):
        """Confirm the typed accessors work on a real DownstreamLifecycleResult."""
        recipe = default_affinity_media_recipe()
        orch = DownstreamProcessOrchestrator()
        result = orch.run(recipe=recipe, propagate_dsd=False)
        assert result.m3_breakthrough is not None
        bt = result.m3_breakthrough
        # Underlying float and accessor agree
        assert bt.dbc_10pct_q.value == pytest.approx(bt.dbc_10pct)
        # Unit conversion works on the real result
        kpa = bt.pressure_drop_q.as_unit("kPa")
        assert kpa.unit == "kPa"
        assert kpa.value > 0
