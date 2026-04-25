"""Tests for the wet-lab calibration ingestion module
(Q-013/Q-014 follow-on).

Covers:
  - YAML/dict campaign loading + schema validation
  - patch_reagent_profile: parameter updates + provenance recording
  - tier promotion (strict mode rejects downgrades)
  - apply_campaign: end-to-end ingestion with mixed success/skip/failure
  - propose_solver_constant_patches: kernel-level Q-013 path
  - manifest serialisation for audit logging
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from dpsim.calibration.calibration_data import CalibrationEntry
from dpsim.calibration.wetlab_ingestion import (
    IngestionResult,
    SolverConstantPatch,
    WetlabCampaign,
    WetlabDataPoint,
    _PATCHABLE_NUMERIC_FIELDS,
    _tier_rank,
    apply_campaign,
    load_campaign,
    patch_reagent_profile,
    propose_solver_constant_patches,
)
from dpsim.module2_functionalization.reagent_profiles import REAGENT_PROFILES


# ─── Tier rank ───────────────────────────────────────────────────────


class TestTierRank:

    def test_validated_strongest(self):
        assert _tier_rank("validated_quantitative") > _tier_rank("calibrated_local")

    def test_calibrated_above_semi(self):
        assert _tier_rank("calibrated_local") > _tier_rank("semi_quantitative")

    def test_semi_above_qualitative(self):
        assert _tier_rank("semi_quantitative") > _tier_rank("qualitative_trend")

    def test_unknown_returns_negative(self):
        assert _tier_rank("not_a_real_tier") < 0

    def test_legacy_synonym_qualitative_only(self):
        assert _tier_rank("qualitative_only") == _tier_rank("qualitative_trend")


# ─── YAML / dict loading ────────────────────────────────────────────


class TestLoadCampaign:

    def _minimal_dict(self) -> dict:
        return {
            "campaign_id": "test_campaign",
            "operator": "test-operator",
            "lab": "test-lab",
            "entries": [
                {
                    "profile_key": "cnbr_activation",
                    "parameter_name": "k_forward",
                    "measured_value": 1.2e-3,
                    "units": "m^3/(mol*s)",
                    "target_molecule": "IgG",
                    "temperature_C": 4.0,
                    "ph": 11.0,
                    "replicates": 3,
                    "fit_method": "least_squares",
                    "posterior_uncertainty": 1.5e-4,
                    "promote_to_tier": "calibrated_local",
                    "bench_date": "2026-08-15",
                },
            ],
        }

    def test_load_from_dict(self):
        campaign = load_campaign(self._minimal_dict())
        assert campaign.campaign_id == "test_campaign"
        assert campaign.operator == "test-operator"
        assert len(campaign.data_points) == 1
        p = campaign.data_points[0]
        assert p.entry.profile_key == "cnbr_activation"
        assert p.promote_to_tier == "calibrated_local"
        assert p.bench_date == "2026-08-15"

    def test_missing_campaign_id_raises(self):
        with pytest.raises(ValueError, match="campaign_id is required"):
            load_campaign({"entries": []})

    def test_unknown_promote_to_tier_raises(self):
        d = self._minimal_dict()
        d["entries"][0]["promote_to_tier"] = "imaginary_tier"
        with pytest.raises(ValueError, match="promote_to_tier"):
            load_campaign(d)

    def test_malformed_entry_raises(self):
        d = self._minimal_dict()
        del d["entries"][0]["profile_key"]
        with pytest.raises(ValueError, match="malformed"):
            load_campaign(d)


# ─── Profile patching ───────────────────────────────────────────────


class TestPatchReagentProfile:

    def _entry(self, **overrides) -> WetlabDataPoint:
        defaults = {
            "profile_key": "periodate_oxidation",
            "parameter_name": "k_forward",
            "measured_value": 3.5e-3,         # bench-fitted (literature 2e-3)
            "units": "1/s",
            "target_molecule": "agarose 4%",
            "temperature_C": 4.0,
            "ph": 5.0,
            "replicates": 3,
            "fit_method": "least_squares",
            "posterior_uncertainty": 5e-4,
        }
        defaults.update(overrides)
        promote = defaults.pop("promote_to_tier", "calibrated_local")
        bench_date = defaults.pop("bench_date", "2026-08-12")
        return WetlabDataPoint(
            entry=CalibrationEntry(**defaults),
            promote_to_tier=promote,
            bench_date=bench_date,
        )

    def test_numeric_parameter_updated(self):
        original = REAGENT_PROFILES["periodate_oxidation"]
        point = self._entry()
        patched = patch_reagent_profile(original, point)
        assert patched.k_forward == pytest.approx(3.5e-3)
        # Original is unchanged
        assert original.k_forward == pytest.approx(2e-3)

    def test_calibration_source_records_provenance(self):
        original = REAGENT_PROFILES["periodate_oxidation"]
        point = self._entry(source_reference="Lab notebook 2026-08-12 p. 7")
        patched = patch_reagent_profile(original, point)
        assert "wetlab campaign" in patched.calibration_source
        assert "2026-08-12" in patched.calibration_source
        assert "fit least_squares" in patched.calibration_source
        assert "Lab notebook 2026-08-12" in patched.calibration_source

    def test_tier_promotion_semi_to_calibrated(self):
        original = REAGENT_PROFILES["periodate_oxidation"]
        assert original.confidence_tier == "semi_quantitative"
        point = self._entry()
        patched = patch_reagent_profile(original, point)
        assert patched.confidence_tier == "calibrated_local"

    def test_tier_promotion_to_validated(self):
        original = REAGENT_PROFILES["periodate_oxidation"]
        point = self._entry(**{"promote_to_tier": "validated_quantitative"})
        patched = patch_reagent_profile(original, point)
        assert patched.confidence_tier == "validated_quantitative"

    def test_strict_rejects_downgrade(self):
        # First promote to calibrated_local, then try to "patch" with a
        # qualitative_trend tier — this is a downgrade and must fail in
        # strict mode.
        promoted = replace(
            REAGENT_PROFILES["periodate_oxidation"],
            confidence_tier="calibrated_local",
        )
        point = self._entry(**{"promote_to_tier": "qualitative_trend"})
        with pytest.raises(ValueError, match="downgrade"):
            patch_reagent_profile(promoted, point, strict=True)

    def test_non_strict_allows_downgrade(self):
        promoted = replace(
            REAGENT_PROFILES["periodate_oxidation"],
            confidence_tier="calibrated_local",
        )
        point = self._entry(**{"promote_to_tier": "qualitative_trend"})
        # Non-strict still does NOT downgrade (the function only ever
        # writes a NEW tier when target_rank > current_rank). But it
        # also does not raise, so the caller's parameter update lands.
        patched = patch_reagent_profile(promoted, point, strict=False)
        # Numeric update applied
        assert patched.k_forward == pytest.approx(3.5e-3)
        # Tier preserved (no upgrade because target rank is lower)
        assert patched.confidence_tier == "calibrated_local"

    def test_non_patchable_parameter_rejected(self):
        original = REAGENT_PROFILES["periodate_oxidation"]
        # `name` is an immutable identity field; patching is forbidden.
        point = self._entry(parameter_name="name", measured_value=0.0)
        with pytest.raises(ValueError, match="not whitelisted"):
            patch_reagent_profile(original, point)


# ─── Campaign application end-to-end ────────────────────────────────


class TestApplyCampaign:

    def test_simple_campaign_apply(self):
        campaign = load_campaign({
            "campaign_id": "Q-014_smoke_test",
            "entries": [
                {
                    "profile_key": "periodate_oxidation",
                    "parameter_name": "k_forward",
                    "measured_value": 2.4e-3,
                    "units": "1/s",
                    "replicates": 4,
                    "promote_to_tier": "calibrated_local",
                    "bench_date": "2026-09-01",
                },
            ],
        })
        result = apply_campaign(campaign)
        assert result.points_total == 1
        assert result.points_applied == 1
        assert result.points_skipped == 0
        assert result.points_failed == 0
        assert "periodate_oxidation" in result.profile_updates
        assert result.tier_promotions == [
            ("periodate_oxidation", "semi_quantitative", "calibrated_local")
        ]

    def test_unknown_profile_key_skipped(self):
        campaign = load_campaign({
            "campaign_id": "test",
            "entries": [
                {
                    "profile_key": "nonexistent_profile_xyz",
                    "parameter_name": "k_forward",
                    "measured_value": 1.0,
                    "units": "1/s",
                },
            ],
        })
        result = apply_campaign(campaign)
        assert result.points_skipped == 1
        assert result.points_applied == 0
        assert any("nonexistent_profile_xyz" in r for _, r in result.skipped)

    def test_failure_recorded_not_raised(self):
        # Non-patchable parameter — should be recorded as failure, not raised.
        campaign = load_campaign({
            "campaign_id": "test",
            "entries": [
                {
                    "profile_key": "periodate_oxidation",
                    "parameter_name": "name",      # immutable; not patchable
                    "measured_value": 0.0,
                    "units": "",
                },
            ],
        })
        result = apply_campaign(campaign)
        assert result.points_failed == 1
        assert any("not whitelisted" in r for _, r in result.failures)

    def test_does_not_mutate_global_registry(self):
        original_k = REAGENT_PROFILES["periodate_oxidation"].k_forward
        campaign = load_campaign({
            "campaign_id": "test",
            "entries": [
                {
                    "profile_key": "periodate_oxidation",
                    "parameter_name": "k_forward",
                    "measured_value": 99.0,        # absurd value — must NOT land in registry
                    "units": "1/s",
                },
            ],
        })
        apply_campaign(campaign)
        assert REAGENT_PROFILES["periodate_oxidation"].k_forward == pytest.approx(original_k)

    def test_manifest_is_json_friendly(self):
        import json
        campaign = load_campaign({
            "campaign_id": "Q-013_kernel_calibration_2026Q3",
            "entries": [
                {
                    "profile_key": "cnbr_activation",
                    "parameter_name": "k_forward",
                    "measured_value": 1.5e-3,
                    "units": "m^3/(mol*s)",
                },
            ],
        })
        result = apply_campaign(campaign)
        manifest = result.manifest()
        # Round-trip through JSON
        text = json.dumps(manifest)
        parsed = json.loads(text)
        assert parsed["campaign_id"] == "Q-013_kernel_calibration_2026Q3"
        assert "ingested_at" in parsed
        assert parsed["points_applied"] == 1


# ─── Solver-constant patch proposals (Q-013 kernel path) ────────────


class TestSolverConstantPatches:

    def test_solver_constant_proposal(self):
        campaign = load_campaign({
            "campaign_id": "Q-013_chitosan_pKa",
            "entries": [
                {
                    "profile_key": "solver:dpsim.level2_gelation.chitosan_only",
                    "parameter_name": "_CHITOSAN_AMINE_PKA",
                    "measured_value": 6.55,
                    "units": "pH",
                    "fit_method": "potentiometric_titration",
                    "posterior_uncertainty": 0.05,
                    "bench_date": "2026-08-20",
                },
            ],
        })
        patches = propose_solver_constant_patches(campaign)
        assert len(patches) == 1
        p = patches[0]
        assert isinstance(p, SolverConstantPatch)
        assert p.constant_name == "_CHITOSAN_AMINE_PKA"
        assert p.proposed_value == pytest.approx(6.55)
        assert p.current_value == pytest.approx(6.4)   # literature default
        assert "Q-013" in p.bench_provenance

    def test_relative_change_signed(self):
        patch = SolverConstantPatch(
            module_path="dpsim.level2_gelation.chitosan_only",
            constant_name="_CHITOSAN_AMINE_PKA",
            current_value=6.4,
            proposed_value=6.55,
            bench_provenance="test",
        )
        # +0.15 / 6.4 ≈ +2.34%
        assert patch.relative_change == pytest.approx(0.15 / 6.4, rel=1e-9)

    def test_unknown_module_skipped_not_raised(self):
        campaign = load_campaign({
            "campaign_id": "test",
            "entries": [
                {
                    "profile_key": "solver:dpsim.does.not.exist",
                    "parameter_name": "_FAKE_CONSTANT",
                    "measured_value": 1.0,
                    "units": "",
                },
            ],
        })
        patches = propose_solver_constant_patches(campaign)
        assert patches == []

    def test_non_solver_entries_filtered_out(self):
        # Mixed campaign: 1 ReagentProfile entry + 1 solver entry.
        campaign = load_campaign({
            "campaign_id": "test",
            "entries": [
                {
                    "profile_key": "periodate_oxidation",       # ReagentProfile
                    "parameter_name": "k_forward",
                    "measured_value": 2e-3,
                    "units": "1/s",
                },
                {
                    "profile_key": "solver:dpsim.level2_gelation.chitosan_only",
                    "parameter_name": "_CHITOSAN_AMINE_PKA",
                    "measured_value": 6.5,
                    "units": "pH",
                },
            ],
        })
        patches = propose_solver_constant_patches(campaign)
        # Only the solver entry counts
        assert len(patches) == 1
        assert patches[0].constant_name == "_CHITOSAN_AMINE_PKA"


# ─── Whitelist coverage ──────────────────────────────────────────────


class TestPatchableFieldWhitelist:
    """Sanity: the whitelist covers the parameters the bench scientist
    is expected to fit (from WETLAB_v9_3_CALIBRATION_PLAN.md § 3)."""

    @pytest.mark.parametrize("expected", [
        "k_forward", "E_a", "stoichiometry", "hydrolysis_rate",
        "ph_optimum", "activity_retention",
        "spacer_length_angstrom", "pKa_nucleophile",
    ])
    def test_canonical_fittable_parameters_in_whitelist(self, expected):
        assert expected in _PATCHABLE_NUMERIC_FIELDS, (
            f"Parameter {expected!r} should be patchable from wet-lab "
            f"campaigns per WETLAB_v9_3_CALIBRATION_PLAN.md § 3"
        )

    def test_immutable_identity_fields_NOT_in_whitelist(self):
        # The bench scientist must not be able to rename a profile or
        # change its CAS number through a calibration campaign.
        from dpsim.calibration.wetlab_ingestion import (
            _PATCHABLE_NUMERIC_FIELDS as numeric,
            _PATCHABLE_STRING_FIELDS as strings,
        )
        forbidden = ("name", "cas", "target_acs", "product_acs",
                     "reaction_type", "chemistry_class", "functional_mode")
        for field in forbidden:
            assert field not in numeric and field not in strings, (
                f"Identity field {field!r} must not be patchable"
            )
