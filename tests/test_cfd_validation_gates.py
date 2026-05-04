"""B-2b (W-008) tests: CFD-PBE end-to-end validation gates."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dpsim.cfd.validation import (
    CFDCalibrationStatus,
    assign_cfd_evidence_tier,
    check_epsilon_volume_consistency,
    check_exchange_flow_balance,
    check_mesh_quality,
    check_residual_convergence,
    validate_cfd_payload,
)
from dpsim.cfd.zonal_pbe import CFDZonesPayload, load_zones_json
from dpsim.datatypes import ModelEvidenceTier

REPO_ROOT = Path(__file__).resolve().parent.parent
STIRRER_A_FIXTURE = (
    REPO_ROOT / "cad" / "cfd" / "cases" / "stirrer_A_beaker_100mL"
    / "zones.example.json"
)


@pytest.fixture
def payload() -> CFDZonesPayload:
    return load_zones_json(STIRRER_A_FIXTURE)


@pytest.fixture
def payload_dict() -> dict:
    with open(STIRRER_A_FIXTURE, encoding="utf-8") as f:
        return json.load(f)


# ─── Mesh QA ─────────────────────────────────────────────────────────────────


class TestMeshQA:
    def test_default_thresholds_pass_on_fixture(self, payload):
        total, per_zone = check_mesh_quality(payload)
        assert total.passed
        assert per_zone.passed

    def test_total_cell_threshold_can_fail(self, payload):
        # Way above any realistic bench-mesh size.
        total, _ = check_mesh_quality(payload, total_cells_min=10**9)
        assert not total.passed
        assert total.value < total.threshold

    def test_per_zone_threshold_can_fail(self, payload):
        _, per_zone = check_mesh_quality(payload, per_zone_cells_min=10**9)
        assert not per_zone.passed


# ─── Residual convergence ────────────────────────────────────────────────────


class TestResidualConvergence:
    def test_default_threshold_pass(self, payload):
        gate = check_residual_convergence(payload)
        assert gate.passed

    def test_tight_threshold_can_fail(self, payload):
        # Tighter than the fixture's residual.
        gate = check_residual_convergence(payload, threshold=1e-12)
        assert not gate.passed
        assert "≥" in gate.message


# ─── ε-volume consistency ────────────────────────────────────────────────────


class TestEpsilonConsistency:
    def test_fixture_passes(self, payload):
        gate = check_epsilon_volume_consistency(payload)
        assert gate.passed
        assert gate.value <= 0.01  # within 1%


# ─── Exchange-flow balance ───────────────────────────────────────────────────


class TestExchangeFlowBalance:
    def test_balanced_fixture_passes_per_zone(self, payload):
        gates = check_exchange_flow_balance(payload)
        # Stirrer A is bidirectionally balanced (impeller↔bulk, bulk↔near_wall),
        # so every zone with exchanges should balance.
        for g in gates:
            assert g.passed, g.message


# ─── Composite report ────────────────────────────────────────────────────────


class TestValidateCFDPayload:
    def test_full_pass_on_fixture(self, payload):
        report = validate_cfd_payload(payload)
        assert report.all_passed
        assert report.failed_gates == []
        assert report.case_name == payload.case_metadata.case_name

    def test_failed_gates_surfaced(self, payload):
        report = validate_cfd_payload(payload, total_cells_min=10**9)
        assert not report.all_passed
        assert "mesh_total_cells" in report.failed_gates


# ─── Evidence-tier ladder ────────────────────────────────────────────────────


class TestEvidenceTierLadder:
    def test_no_status_yields_qualitative_trend(self):
        tier = assign_cfd_evidence_tier()
        assert tier == ModelEvidenceTier.QUALITATIVE_TREND

    def test_piv_only_yields_calibrated_local(self):
        tier = assign_cfd_evidence_tier(
            CFDCalibrationStatus(piv_calibrated_at_geometry_and_rpm=True)
        )
        assert tier == ModelEvidenceTier.CALIBRATED_LOCAL

    def test_piv_and_bench_dsd_yields_validated_quantitative(self):
        tier = assign_cfd_evidence_tier(
            CFDCalibrationStatus(
                piv_calibrated_at_geometry_and_rpm=True,
                bench_dsd_validated_in_envelope=True,
            )
        )
        assert tier == ModelEvidenceTier.VALIDATED_QUANTITATIVE

    def test_bench_dsd_alone_does_not_promote_past_qualitative(self):
        """The ladder requires PIV (geometry calibration) before bench DSD
        can promote — DSD-only might be coincidence."""
        tier = assign_cfd_evidence_tier(
            CFDCalibrationStatus(
                piv_calibrated_at_geometry_and_rpm=False,
                bench_dsd_validated_in_envelope=True,
            )
        )
        assert tier == ModelEvidenceTier.QUALITATIVE_TREND

    def test_failed_gates_force_unsupported(self):
        """Bad CFD beats good PIV: any operational gate failure → UNSUPPORTED."""
        tier = assign_cfd_evidence_tier(
            CFDCalibrationStatus(
                piv_calibrated_at_geometry_and_rpm=True,
                bench_dsd_validated_in_envelope=True,
            ),
            gates_passed=False,
        )
        assert tier == ModelEvidenceTier.UNSUPPORTED
