"""B-2e (W-004) tests: M3 quantitative-output gating policy."""

from __future__ import annotations

import pytest

from dpsim.calibration.calibration_data import CalibrationEntry
from dpsim.datatypes import ModelEvidenceTier, ModelManifest
from dpsim.module3_performance.quantitative_gates import (
    GradientContext,
    M3CalibrationCoverage,
    apply_m3_gate_to_manifest,
    assess_m3_calibration_coverage,
    assign_m3_evidence_tier,
    gradient_context_from_recipe_params,
)


# ─── Coverage assessment ─────────────────────────────────────────────────────


class TestCoverageAssessment:
    def test_empty_list_yields_zero_coverage(self):
        coverage = assess_m3_calibration_coverage([])
        assert coverage.n_calibrated == 0

    def test_q_max_entry_increments_q_max_only(self):
        entries = [
            {"profile_key": "p", "parameter_name": "q_max", "measured_value": 50.0},
        ]
        coverage = assess_m3_calibration_coverage(entries)
        assert coverage.q_max_calibrated
        assert not coverage.kinetic_constants_calibrated
        assert coverage.n_calibrated == 1

    def test_full_coverage_when_all_four_present(self):
        entries = [
            {"profile_key": "p", "parameter_name": "q_max", "measured_value": 50.0},
            {"profile_key": "p", "parameter_name": "k_l", "measured_value": 0.01},
            {"profile_key": "p", "parameter_name": "permeability", "measured_value": 1e-12},
            {"profile_key": "p", "parameter_name": "cycle_life", "measured_value": 100.0},
        ]
        coverage = assess_m3_calibration_coverage(entries)
        assert coverage.n_calibrated == 4

    def test_keyword_synonyms_recognised(self):
        """Different keys for the same ingredient all count."""
        for key in ("q_max", "qmax", "static_capacity", "binding_capacity"):
            entries = [{"profile_key": "p", "parameter_name": key, "measured_value": 50.0}]
            coverage = assess_m3_calibration_coverage(entries)
            assert coverage.q_max_calibrated, f"key={key}"

    def test_unknown_parameter_name_does_not_count(self):
        entries = [
            {"profile_key": "p", "parameter_name": "completely_made_up_param", "measured_value": 1.0}
        ]
        coverage = assess_m3_calibration_coverage(entries)
        assert coverage.n_calibrated == 0

    def test_profile_key_filter_excludes_other_profiles(self):
        entries = [
            {"profile_key": "protein_a", "parameter_name": "q_max", "measured_value": 50.0},
            {"profile_key": "protein_g", "parameter_name": "k_l",  "measured_value": 0.01},
        ]
        coverage = assess_m3_calibration_coverage(entries, profile_key="protein_a")
        assert coverage.q_max_calibrated
        assert not coverage.kinetic_constants_calibrated

    def test_target_molecule_filter(self):
        entries = [
            {"profile_key": "p", "parameter_name": "q_max", "target_molecule": "IgG", "measured_value": 50.0},
            {"profile_key": "p", "parameter_name": "k_l",  "target_molecule": "BSA", "measured_value": 0.01},
        ]
        coverage = assess_m3_calibration_coverage(entries, target_molecule="IgG")
        assert coverage.q_max_calibrated
        assert not coverage.kinetic_constants_calibrated

    def test_calibration_entry_objects_accepted(self):
        """Builder accepts CalibrationEntry instances, not just dicts."""
        entries = [
            CalibrationEntry(
                profile_key="p", parameter_name="q_max",
                measured_value=50.0, units="mol/m3",
            ),
        ]
        coverage = assess_m3_calibration_coverage(entries)
        assert coverage.q_max_calibrated


# ─── Tier-promotion ladder ───────────────────────────────────────────────────


class TestTierPromotionLadder:
    def test_all_four_yields_validated_quantitative(self):
        coverage = M3CalibrationCoverage(
            q_max_calibrated=True,
            kinetic_constants_calibrated=True,
            pressure_flow_calibrated=True,
            cycle_life_calibrated=True,
        )
        assert assign_m3_evidence_tier(coverage) == ModelEvidenceTier.VALIDATED_QUANTITATIVE

    def test_three_of_four_yields_calibrated_local(self):
        coverage = M3CalibrationCoverage(
            q_max_calibrated=True,
            kinetic_constants_calibrated=True,
            pressure_flow_calibrated=True,
            cycle_life_calibrated=False,
        )
        assert assign_m3_evidence_tier(coverage) == ModelEvidenceTier.CALIBRATED_LOCAL

    @pytest.mark.parametrize("n_true", [1, 2])
    def test_partial_yields_semi_quantitative(self, n_true):
        flags = [True] * n_true + [False] * (4 - n_true)
        coverage = M3CalibrationCoverage(
            q_max_calibrated=flags[0],
            kinetic_constants_calibrated=flags[1],
            pressure_flow_calibrated=flags[2],
            cycle_life_calibrated=flags[3],
        )
        assert assign_m3_evidence_tier(coverage) == ModelEvidenceTier.SEMI_QUANTITATIVE

    def test_zero_yields_qualitative_trend(self):
        coverage = M3CalibrationCoverage()
        assert assign_m3_evidence_tier(coverage) == ModelEvidenceTier.QUALITATIVE_TREND


# ─── GradientContext ────────────────────────────────────────────────────────


class TestGradientContext:
    def test_default_inactive(self):
        ctx = GradientContext()
        assert not ctx.is_active

    def test_active_when_field_and_duration_set(self):
        ctx = GradientContext(gradient_field="ph", duration_s=300.0,
                              start_value=7.4, end_value=3.5)
        assert ctx.is_active

    def test_active_requires_positive_duration(self):
        ctx = GradientContext(gradient_field="ph", duration_s=0.0)
        assert not ctx.is_active


class TestGradientContextFromRecipeParams:
    def test_no_gradient_field_returns_none(self):
        assert gradient_context_from_recipe_params({}) is None
        assert gradient_context_from_recipe_params({"gradient_field": ""}) is None

    def test_pH_gradient_uses_pH_keys(self):
        params = {
            "gradient_field": "ph",
            "gradient_start_pH": 7.4,
            "gradient_end_pH": 3.5,
            "duration": 300.0,
        }
        ctx = gradient_context_from_recipe_params(params)
        assert ctx is not None
        assert ctx.gradient_field == "ph"
        assert ctx.start_value == pytest.approx(7.4)
        assert ctx.end_value == pytest.approx(3.5)
        assert ctx.duration_s == 300.0
        assert ctx.is_active

    def test_salt_gradient_uses_value_keys(self):
        params = {
            "gradient_field": "salt_concentration",
            "gradient_start_value": 50.0,
            "gradient_end_value": 1000.0,
            "duration": 600.0,
        }
        ctx = gradient_context_from_recipe_params(params)
        assert ctx is not None
        assert ctx.start_value == 50.0
        assert ctx.end_value == 1000.0

    def test_quantity_like_objects_accepted(self):
        """Inputs with a .value attribute (Quantity duck-typing) work."""
        class _QLike:
            def __init__(self, v): self.value = v
        params = {
            "gradient_field": "ph",
            "gradient_start_pH": _QLike(7.4),
            "gradient_end_pH": _QLike(3.5),
            "duration": _QLike(300.0),
        }
        ctx = gradient_context_from_recipe_params(params)
        assert ctx.start_value == pytest.approx(7.4)
        assert ctx.end_value == pytest.approx(3.5)

    def test_default_shape_is_linear(self):
        ctx = gradient_context_from_recipe_params({"gradient_field": "ph", "duration": 60.0})
        assert ctx.shape == "linear"


# ─── Manifest gating ────────────────────────────────────────────────────────


class TestApplyM3GateToManifest:
    """Gate can only DEMOTE the manifest tier; never promote."""

    def _manifest(self, tier: ModelEvidenceTier) -> ModelManifest:
        return ModelManifest(model_name="M3.test", evidence_tier=tier)

    def test_no_calibration_demotes_to_qualitative(self):
        manifest = self._manifest(ModelEvidenceTier.VALIDATED_QUANTITATIVE)
        gated = apply_m3_gate_to_manifest(manifest, calibration_entries=[])
        assert gated.evidence_tier == ModelEvidenceTier.QUALITATIVE_TREND
        assert gated.diagnostics["m3_gate_coverage_n"] == 0

    def test_full_calibration_preserves_validated(self):
        manifest = self._manifest(ModelEvidenceTier.VALIDATED_QUANTITATIVE)
        entries = [
            {"profile_key": "p", "parameter_name": "q_max", "measured_value": 50.0},
            {"profile_key": "p", "parameter_name": "k_l", "measured_value": 0.01},
            {"profile_key": "p", "parameter_name": "permeability", "measured_value": 1e-12},
            {"profile_key": "p", "parameter_name": "cycle_life", "measured_value": 100.0},
        ]
        gated = apply_m3_gate_to_manifest(manifest, calibration_entries=entries)
        assert gated.evidence_tier == ModelEvidenceTier.VALIDATED_QUANTITATIVE
        assert gated.diagnostics["m3_gate_coverage_n"] == 4

    def test_gate_cannot_promote_above_existing_tier(self):
        """Existing manifest at SEMI_QUANTITATIVE; full calibration would
        produce VALIDATED_QUANTITATIVE — but the gate is demote-only."""
        manifest = self._manifest(ModelEvidenceTier.SEMI_QUANTITATIVE)
        entries = [
            {"profile_key": "p", "parameter_name": "q_max", "measured_value": 50.0},
            {"profile_key": "p", "parameter_name": "k_l", "measured_value": 0.01},
            {"profile_key": "p", "parameter_name": "permeability", "measured_value": 1e-12},
            {"profile_key": "p", "parameter_name": "cycle_life", "measured_value": 100.0},
        ]
        gated = apply_m3_gate_to_manifest(manifest, calibration_entries=entries)
        # Should stay at SEMI — the gate is demote-only.
        assert gated.evidence_tier == ModelEvidenceTier.SEMI_QUANTITATIVE
        # But the gate's own assessment should still be reported.
        assert gated.diagnostics["m3_gate_tier_only"] == ModelEvidenceTier.VALIDATED_QUANTITATIVE.value

    def test_input_manifest_not_mutated(self):
        manifest = self._manifest(ModelEvidenceTier.VALIDATED_QUANTITATIVE)
        gated = apply_m3_gate_to_manifest(manifest, calibration_entries=[])
        assert manifest.evidence_tier == ModelEvidenceTier.VALIDATED_QUANTITATIVE
        assert gated is not manifest

    def test_filter_by_profile_key(self):
        """Entries for a different profile must not contribute coverage."""
        manifest = self._manifest(ModelEvidenceTier.VALIDATED_QUANTITATIVE)
        entries = [
            # Wrong profile — should be ignored.
            {"profile_key": "wrong_profile", "parameter_name": "q_max",
             "measured_value": 50.0},
        ]
        gated = apply_m3_gate_to_manifest(
            manifest, entries, profile_key="protein_a_coupling",
        )
        assert gated.evidence_tier == ModelEvidenceTier.QUALITATIVE_TREND

    def test_calibration_entry_objects_accepted(self):
        manifest = self._manifest(ModelEvidenceTier.VALIDATED_QUANTITATIVE)
        entries = [
            CalibrationEntry(profile_key="p", parameter_name="q_max",
                             measured_value=50.0, units="mol/m3"),
        ]
        gated = apply_m3_gate_to_manifest(manifest, entries)
        assert gated.diagnostics["m3_gate_q_max"] is True
