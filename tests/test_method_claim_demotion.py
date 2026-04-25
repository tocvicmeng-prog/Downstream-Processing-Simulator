"""Tests for B6 — claim-strength demotion of uncalibrated M3 outputs.

Reference: docs/dev_orchestrator_plan.md, Module B6.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from dpsim.datatypes import ModelEvidenceTier, ModelManifest
from dpsim.module3_performance.method import (
    ImpuritySpeciesReport,
    ProteinAPerformanceReport,
    cycle_lifetime_label,
    is_method_calibrated,
    leaching_label,
    log10_reduction_label,
)


def _pa_report(*, cycles=50.0, leaching=0.005, leaching_risk="low") -> ProteinAPerformanceReport:
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
        cycle_lifetime_to_70pct_capacity=cycles,
        ligand_leaching_fraction_per_cycle=leaching,
        leaching_risk=leaching_risk,
        predicted_elution_recovery_fraction=0.85,
    )


def _impurity(*, log10r=2.0) -> ImpuritySpeciesReport:
    return ImpuritySpeciesReport(
        name="host_cell_protein",
        load_fraction_of_igg=0.05,
        remaining_after_wash_fraction=0.005,
        coelution_fraction_of_igg=0.001,
        log10_reduction=log10r,
    )


@dataclass
class _MockFMC:
    model_manifest: ModelManifest | None = None


# ─── is_method_calibrated ────────────────────────────────────────────────────


class TestIsMethodCalibrated:
    def test_calibrated_local_returns_true(self):
        fmc = _MockFMC(
            model_manifest=ModelManifest(
                model_name="M2", evidence_tier=ModelEvidenceTier.CALIBRATED_LOCAL
            )
        )
        assert is_method_calibrated(fmc) is True

    def test_validated_quantitative_returns_true(self):
        fmc = _MockFMC(
            model_manifest=ModelManifest(
                model_name="M2",
                evidence_tier=ModelEvidenceTier.VALIDATED_QUANTITATIVE,
            )
        )
        assert is_method_calibrated(fmc) is True

    def test_semi_quantitative_returns_false(self):
        fmc = _MockFMC(
            model_manifest=ModelManifest(
                model_name="M2", evidence_tier=ModelEvidenceTier.SEMI_QUANTITATIVE
            )
        )
        assert is_method_calibrated(fmc) is False

    def test_no_manifest_returns_false(self):
        assert is_method_calibrated(_MockFMC(model_manifest=None)) is False

    def test_no_fmc_returns_false(self):
        assert is_method_calibrated(None) is False


# ─── cycle_lifetime_label ────────────────────────────────────────────────────


class TestCycleLifetimeLabel:
    @pytest.mark.parametrize(
        "cycles,expected_bucket",
        [
            (10.0, "<30 cycles (low)"),
            (50.0, "30-100 cycles (moderate)"),
            (200.0, "100-300 cycles (good)"),
            (500.0, ">300 cycles (excellent)"),
        ],
    )
    def test_uncalibrated_bucketed(self, cycles, expected_bucket):
        report = _pa_report(cycles=cycles)
        label = cycle_lifetime_label(report, is_calibrated=False)
        assert expected_bucket in label
        assert "calibration required" in label

    def test_calibrated_shows_precise_number(self):
        report = _pa_report(cycles=147.3)
        label = cycle_lifetime_label(report, is_calibrated=True)
        assert "147" in label
        assert "calibration required" not in label


# ─── log10_reduction_label ───────────────────────────────────────────────────


class TestLog10ReductionLabel:
    @pytest.mark.parametrize(
        "log10r,expected_bucket",
        [
            (0.5, "<1 LRV (poor)"),
            (1.5, "1-2 LRV (moderate)"),
            (3.0, "2-4 LRV (good)"),
            (5.0, ">4 LRV (excellent)"),
        ],
    )
    def test_uncalibrated_bucketed(self, log10r, expected_bucket):
        species = _impurity(log10r=log10r)
        label = log10_reduction_label(species, is_calibrated=False)
        assert expected_bucket in label

    def test_calibrated_shows_precise_lrv(self):
        species = _impurity(log10r=2.7)
        label = log10_reduction_label(species, is_calibrated=True)
        assert "2.7" in label
        assert "calibration required" not in label


# ─── leaching_label ──────────────────────────────────────────────────────────


class TestLeachingLabel:
    def test_uncalibrated_returns_risk_label_only(self):
        report = _pa_report(leaching=0.012, leaching_risk="medium")
        label = leaching_label(report, is_calibrated=False)
        assert "medium" in label
        assert "calibration required" in label
        assert "1.2" not in label  # no false-precision percentage

    def test_calibrated_includes_percentage(self):
        report = _pa_report(leaching=0.012, leaching_risk="medium")
        label = leaching_label(report, is_calibrated=True)
        assert "1.20%" in label
        assert "medium" in label
