"""B-2a (W-009) tests: wash residual diffusion-partition + hydrolysis model."""

from __future__ import annotations

import math

import pytest

from dpsim.calibration.calibration_data import CalibrationEntry
from dpsim.datatypes import ModelEvidenceTier
from dpsim.level1_emulsification.wash_residuals import (
    WashCycleSpec,
    WashResidualSpec,
    hydrolysis_rate_for_reagent,
    make_default_spec,
    predict_wash_residuals,
)


# ─── Spec validation ────────────────────────────────────────────────────────


class TestSpecValidation:
    @pytest.mark.parametrize("bad_radius", [0.0, -1.0e-6])
    def test_negative_or_zero_bead_radius_rejected(self, bad_radius):
        with pytest.raises(ValueError, match="bead_radius_m"):
            WashResidualSpec(
                species_name="x",
                initial_bead_concentration_mol_per_m3=1.0,
                bead_radius_m=bad_radius,
            )

    @pytest.mark.parametrize("bad_d", [0.0, -1e-10])
    def test_invalid_diffusivity_rejected(self, bad_d):
        with pytest.raises(ValueError, match="diffusion_coefficient"):
            WashResidualSpec(
                species_name="x",
                initial_bead_concentration_mol_per_m3=1.0,
                diffusion_coefficient_m2_per_s=bad_d,
            )

    def test_negative_hydrolysis_rejected(self):
        with pytest.raises(ValueError, match="hydrolysis_rate_per_s"):
            WashResidualSpec(
                species_name="x",
                initial_bead_concentration_mol_per_m3=1.0,
                hydrolysis_rate_per_s=-1.0,
            )

    @pytest.mark.parametrize("bad_n", [0, -3])
    def test_invalid_n_cycles_rejected(self, bad_n):
        with pytest.raises(ValueError, match="n_cycles"):
            WashCycleSpec(n_cycles=bad_n, cycle_duration_s=60.0, wash_to_bead_volume_ratio=3.0)

    @pytest.mark.parametrize("bad_eta", [0.0, -0.5, 1.5])
    def test_invalid_mixing_efficiency_rejected(self, bad_eta):
        with pytest.raises(ValueError, match="mixing_efficiency"):
            WashCycleSpec(
                n_cycles=3, cycle_duration_s=60.0,
                wash_to_bead_volume_ratio=3.0, mixing_efficiency=bad_eta,
            )


# ─── Hydrolysis library ─────────────────────────────────────────────────────


class TestHydrolysisLibrary:
    """Anchor literature half-lives stay correct across edits."""

    def test_cnbr_half_life_5_min_at_pH_11(self):
        k = hydrolysis_rate_for_reagent("cnbr_activation")
        t_half = math.log(2.0) / k
        assert t_half == pytest.approx(5.0 * 60.0, rel=1e-9)

    def test_cdi_half_life_5_h(self):
        k = hydrolysis_rate_for_reagent("cdi_activation")
        t_half = math.log(2.0) / k
        assert t_half == pytest.approx(5.0 * 3600.0, rel=1e-9)

    def test_tresyl_half_life_1_5_h(self):
        k = hydrolysis_rate_for_reagent("tresyl_chloride_activation")
        t_half = math.log(2.0) / k
        assert t_half == pytest.approx(5400.0, rel=1e-9)

    def test_unknown_reagent_returns_zero(self):
        assert hydrolysis_rate_for_reagent("nonexistent_xyz") == 0.0

    def test_epoxide_no_hydrolysis(self):
        for key in ("ech_activation", "dvs_activation", "bdge_activation"):
            assert hydrolysis_rate_for_reagent(key) == 0.0


# ─── Model behaviour ────────────────────────────────────────────────────────


class TestModelBehaviour:
    def test_zero_initial_concentration_short_circuits(self):
        spec = make_default_spec("cnbr_activation", "cyanate_ester", 0.0)
        cycle = WashCycleSpec(n_cycles=3, cycle_duration_s=300.0, wash_to_bead_volume_ratio=3.0)
        result = predict_wash_residuals(spec, cycle)
        assert result.final_residual_mol_per_m3 == 0.0
        assert result.meets_target  # vacuously true (target=0, residual=0)
        assert result.meets_assay_limit

    def test_residual_decreases_monotonically_per_cycle(self):
        spec = make_default_spec("cnbr_activation", "cyanate_ester", 100.0)
        cycle = WashCycleSpec(n_cycles=5, cycle_duration_s=600.0, wash_to_bead_volume_ratio=5.0)
        result = predict_wash_residuals(spec, cycle)
        residuals = result.residual_per_cycle_mol_per_m3
        assert len(residuals) == 5
        # Residual must strictly decrease cycle to cycle (both diffusion
        # and hydrolysis are loss channels with no production).
        for i in range(1, len(residuals)):
            assert residuals[i] < residuals[i - 1]
        assert result.final_residual_mol_per_m3 < 100.0

    def test_hydrolysis_dominates_for_cnbr_in_long_wash(self):
        """5-min half-life CNBr with 5x wash ratio (K_p=1): the effective
        depletion half-life is t_half × (1 + V_w/V_b · K_p) = 5 × 6 = 30 min
        (water reservoir refills bead as hydrolysis depletes it).

        After 1 effective half-life the bead-side concentration is ~50% of
        equilibrium (which is C_init/6 ≈ 16.7), so ~8 mol/m³. With more
        cycles, the depletion compounds.
        """
        spec = make_default_spec("cnbr_activation", "cyanate_ester", 100.0)
        cycle = WashCycleSpec(n_cycles=3, cycle_duration_s=1800.0, wash_to_bead_volume_ratio=5.0)
        result = predict_wash_residuals(spec, cycle)
        assert result.cumulative_hydrolysis_loss_fraction > 0.5
        # After 3 wash cycles of 30 min each, residual should be << initial.
        assert result.final_residual_mol_per_m3 < 5.0

    def test_no_hydrolysis_loss_for_epoxide(self):
        """Epoxide is stable on wash timescale; loss must be diffusion-only."""
        spec = make_default_spec("ech_activation", "epoxide", 100.0)
        cycle = WashCycleSpec(n_cycles=3, cycle_duration_s=600.0, wash_to_bead_volume_ratio=10.0)
        result = predict_wash_residuals(spec, cycle)
        assert result.cumulative_hydrolysis_loss_fraction == pytest.approx(0.0, abs=1e-12)
        assert result.cumulative_diffusion_loss_fraction > 0.0
        assert result.hydrolysis_half_life_s == float("inf")

    def test_meets_target_flag(self):
        """Aggressive wash schedule meets a moderate target."""
        spec = WashResidualSpec(
            species_name="cyanate",
            initial_bead_concentration_mol_per_m3=100.0,
            hydrolysis_rate_per_s=hydrolysis_rate_for_reagent("cnbr_activation"),
            target_residual_mol_per_m3=1.0,
        )
        cycle = WashCycleSpec(n_cycles=5, cycle_duration_s=600.0, wash_to_bead_volume_ratio=10.0)
        result = predict_wash_residuals(spec, cycle)
        assert result.meets_target

    def test_does_not_meet_target_when_too_short(self):
        spec = WashResidualSpec(
            species_name="cyanate",
            initial_bead_concentration_mol_per_m3=100.0,
            hydrolysis_rate_per_s=0.0,  # no hydrolysis to help
            target_residual_mol_per_m3=0.001,  # very tight target
        )
        cycle = WashCycleSpec(n_cycles=1, cycle_duration_s=10.0, wash_to_bead_volume_ratio=2.0)
        result = predict_wash_residuals(spec, cycle)
        assert not result.meets_target


# ─── Evidence-tier policy ───────────────────────────────────────────────────


class TestEvidenceTierPolicy:
    def test_default_transport_yields_qualitative_trend(self):
        spec = make_default_spec("cnbr_activation", "cyanate_ester", 100.0)
        cycle = WashCycleSpec(n_cycles=3, cycle_duration_s=600.0, wash_to_bead_volume_ratio=5.0)
        result = predict_wash_residuals(spec, cycle)
        assert result.model_manifest.evidence_tier == ModelEvidenceTier.QUALITATIVE_TREND

    def test_user_supplied_transport_yields_semi_quantitative(self):
        spec = WashResidualSpec(
            species_name="cyanate",
            initial_bead_concentration_mol_per_m3=100.0,
            diffusion_coefficient_m2_per_s=2e-10,    # explicitly user-supplied
            partition_coefficient_K_p=1.5,
            hydrolysis_rate_per_s=hydrolysis_rate_for_reagent("cnbr_activation"),
        )
        cycle = WashCycleSpec(n_cycles=3, cycle_duration_s=600.0, wash_to_bead_volume_ratio=5.0)
        result = predict_wash_residuals(spec, cycle)
        assert result.model_manifest.evidence_tier == ModelEvidenceTier.SEMI_QUANTITATIVE

    def test_calibrated_assay_limit_yields_calibrated_local(self):
        spec = WashResidualSpec(
            species_name="cyanate",
            initial_bead_concentration_mol_per_m3=100.0,
            diffusion_coefficient_m2_per_s=2e-10,
            partition_coefficient_K_p=1.2,
            hydrolysis_rate_per_s=hydrolysis_rate_for_reagent("cnbr_activation"),
            assay_detection_limit_mol_per_m3=0.01,
        )
        cycle = WashCycleSpec(n_cycles=5, cycle_duration_s=600.0, wash_to_bead_volume_ratio=10.0)
        result = predict_wash_residuals(spec, cycle)
        assert result.model_manifest.evidence_tier == ModelEvidenceTier.CALIBRATED_LOCAL


# ─── CalibrationEntry assay-limit fields ────────────────────────────────────


class TestCalibrationEntryAssayLimits:
    """B-2a: CalibrationEntry must carry assay_detection_limit + LOQ."""

    def test_assay_limit_fields_default_zero(self):
        entry = CalibrationEntry(
            profile_key="cnbr_activation",
            parameter_name="cyanate_residual",
            measured_value=0.05,
            units="mol/m3",
        )
        assert entry.assay_detection_limit == 0.0
        assert entry.assay_quantitation_limit == 0.0

    def test_assay_limit_round_trip_dict(self):
        entry = CalibrationEntry(
            profile_key="cnbr_activation",
            parameter_name="cyanate_residual",
            measured_value=0.05,
            units="mol/m3",
            assay_detection_limit=0.01,
            assay_quantitation_limit=0.03,
        )
        round_tripped = CalibrationEntry.from_dict(entry.to_dict())
        assert round_tripped.assay_detection_limit == 0.01
        assert round_tripped.assay_quantitation_limit == 0.03

    def test_legacy_dict_without_assay_fields_loads(self):
        """Old calibration JSON (pre-v0.6.5) must still load."""
        legacy = {
            "profile_key": "cnbr_activation",
            "parameter_name": "cyanate_residual",
            "measured_value": 0.05,
            "units": "mol/m3",
        }
        entry = CalibrationEntry.from_dict(legacy)
        assert entry.assay_detection_limit == 0.0
        assert entry.assay_quantitation_limit == 0.0
