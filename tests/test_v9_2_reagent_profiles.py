"""Tests for all v9.2 Tier-1 reagent profiles (M1-M9).

Verifies:
  - Each new profile is registered in REAGENT_PROFILES
  - Each profile's functional_mode is in ALLOWED_FUNCTIONAL_MODES
  - Each profile's chemistry_class is in ALLOWED_CHEMISTRY_CLASSES (or empty)
  - Every profile carries a peer-reviewed calibration source
  - Every profile has a literature-anchored kinetic constant set

Workflow-level tests verify integration coherence:
  - M2 oriented-glycoprotein chain: periodate → ADH → aminooxy
  - M3 dye chain: cyanuric chloride → Cibacron Blue
  - M6 click chain: CuAAC + SPAAC mutual consistency
  - M7 multipoint: glyoxyl → multipoint stability
  - M8 material-as-ligand: amylose+MBP routing
  - M9 boronate: APBA pH-switchable
"""

from __future__ import annotations

import pytest

from dpsim.module2_functionalization.acs import ACSSiteType
from dpsim.module2_functionalization.reactions import (
    CHEMISTRY_CLASS_TO_TEMPLATE,
    kinetic_template_for,
)
from dpsim.module2_functionalization.reagent_profiles import (
    ALLOWED_CHEMISTRY_CLASSES,
    ALLOWED_FUNCTIONAL_MODES,
    REAGENT_PROFILES,
    validate_chemistry_class,
    validate_functional_mode,
)


# v9.2 Tier-1 reagent keys (M1–M9).
V9_2_TIER1_KEYS = [
    # M1 (B1)
    "cnbr_activation",
    "cdi_activation",
    "hexyl_coupling",
    # M2 (B2)
    "periodate_oxidation",
    "adh_hydrazone",
    "aminooxy_peg_linker",
    # M3 (B3)
    "cyanuric_chloride_activation",
    "cibacron_blue_f3ga_coupling",
    "triazine_dye_leakage_advisory",
    # M4 (B4)
    "thiophilic_2me_coupling",
    "mep_hcic_coupling",
    # M5 (B5)
    "bis_epoxide_crosslinking",
    # M6 (B7)
    "cuaac_click_coupling",
    "spaac_click_coupling",
    # M7 (B8)
    "glyoxyl_chained_activation",
    "multipoint_stability_uplift",
    # M8 (B9)
    "amylose_mbp_affinity",
    # M9 (B10)
    "apba_boronate_coupling",
]


class TestV9_2_ProfilesPresent:
    """Every v9.2 Tier-1 profile must be registered."""

    @pytest.mark.parametrize("key", V9_2_TIER1_KEYS)
    def test_profile_registered(self, key):
        assert key in REAGENT_PROFILES, f"Missing v9.2 profile {key!r}"

    @pytest.mark.parametrize("key", V9_2_TIER1_KEYS)
    def test_profile_has_calibration_source(self, key):
        rp = REAGENT_PROFILES[key]
        # Either calibration_source or notes must contain a citation.
        # We require at least a non-empty calibration_source.
        assert rp.calibration_source != "", (
            f"{key!r}: calibration_source is empty; every profile must "
            f"cite a peer-reviewed source"
        )

    @pytest.mark.parametrize("key", V9_2_TIER1_KEYS)
    def test_kinetic_constants_positive(self, key):
        rp = REAGENT_PROFILES[key]
        assert rp.k_forward > 0 or key.endswith("_advisory"), (
            f"{key!r}: k_forward must be > 0 (advisory profiles excepted)"
        )
        assert rp.E_a >= 0, f"{key!r}: E_a must be non-negative"

    @pytest.mark.parametrize("key", V9_2_TIER1_KEYS)
    def test_functional_mode_in_allowed_set(self, key):
        rp = REAGENT_PROFILES[key]
        validate_functional_mode(rp.functional_mode)
        assert rp.functional_mode in ALLOWED_FUNCTIONAL_MODES

    @pytest.mark.parametrize("key", V9_2_TIER1_KEYS)
    def test_chemistry_class_routes_to_template(self, key):
        rp = REAGENT_PROFILES[key]
        validate_chemistry_class(rp.chemistry_class)
        # Empty class is allowed; otherwise must be in template map.
        if rp.chemistry_class:
            template = kinetic_template_for(rp.chemistry_class)
            assert template in {
                "second_order_irreversible",
                "competitive_hydrolysis",
                "steric_binding",
            }


class TestM2_OrientedGlycoproteinChain:
    """M2 acceptance: periodate → ADH → aminooxy chain coherence."""

    def test_periodate_produces_aldehyde(self):
        rp = REAGENT_PROFILES["periodate_oxidation"]
        assert rp.target_acs.value == ACSSiteType.HYDROXYL.value
        assert rp.product_acs.value == ACSSiteType.ALDEHYDE.value

    def test_adh_consumes_aldehyde_produces_hydrazide(self):
        rp = REAGENT_PROFILES["adh_hydrazone"]
        assert rp.target_acs.value == ACSSiteType.ALDEHYDE.value
        assert rp.product_acs.value == ACSSiteType.HYDRAZIDE.value

    def test_aminooxy_consumes_aldehyde_produces_aminooxy(self):
        rp = REAGENT_PROFILES["aminooxy_peg_linker"]
        assert rp.target_acs.value == ACSSiteType.ALDEHYDE.value
        assert rp.product_acs.value == ACSSiteType.AMINOOXY.value

    def test_oxime_more_stable_than_hydrazone(self):
        """Oxime (aminooxy) hydrolysis rate must be lower than hydrazone (ADH)
        — that's the whole point of using oxime ligation."""
        oxime = REAGENT_PROFILES["aminooxy_peg_linker"]
        hydrazone = REAGENT_PROFILES["adh_hydrazone"]
        assert oxime.hydrolysis_rate < hydrazone.hydrolysis_rate


class TestM3_DyeAffinityChain:
    """M3: cyanuric chloride → Cibacron Blue chain."""

    def test_cyanuric_chloride_produces_triazine_reactive(self):
        rp = REAGENT_PROFILES["cyanuric_chloride_activation"]
        assert rp.product_acs.value == ACSSiteType.TRIAZINE_REACTIVE.value

    def test_cibacron_blue_consumes_triazine_reactive(self):
        rp = REAGENT_PROFILES["cibacron_blue_f3ga_coupling"]
        assert rp.target_acs.value == ACSSiteType.TRIAZINE_REACTIVE.value
        assert rp.functional_mode == "dye_pseudo_affinity"


class TestM4_MixedModeHCIC:
    """M4: MEP HCIC pH-switchable model."""

    def test_mep_carries_pka_for_pH_switch(self):
        rp = REAGENT_PROFILES["mep_hcic_coupling"]
        # MEP pyridine pKa ≈ 4.5 drives the elution switch
        assert 4.0 <= rp.pKa_nucleophile <= 5.0
        assert rp.functional_mode == "mixed_mode_hcic"

    def test_thiophilic_uses_vs_chemistry(self):
        rp = REAGENT_PROFILES["thiophilic_2me_coupling"]
        assert rp.target_acs.value == ACSSiteType.VINYL_SULFONE.value
        assert rp.chemistry_class == "vs_thiol"


class TestM5_BisEpoxide:
    """M5: single parameterized bis-epoxide profile (Q-001)."""

    def test_bis_epoxide_carries_spacer_length(self):
        rp = REAGENT_PROFILES["bis_epoxide_crosslinking"]
        # Default spacer_length should be set (BDDE ≈ 12 Å)
        assert rp.spacer_length_angstrom > 0
        assert rp.functional_mode == "crosslinker"


class TestM6_ClickChemistry:
    """M6: CuAAC + SPAAC mutual consistency."""

    def test_cuaac_carries_cu_residual_warning(self):
        rp = REAGENT_PROFILES["cuaac_click_coupling"]
        assert rp.regulatory_limit_ppm > 0
        assert "cu" in rp.hazard_class.lower()

    def test_spaac_no_cu_warning(self):
        rp = REAGENT_PROFILES["spaac_click_coupling"]
        # SPAAC is copper-free → no Cu residual constraint
        assert rp.regulatory_limit_ppm == 0.0

    def test_cuaac_faster_than_spaac(self):
        """CuAAC k_forward should be much higher than SPAAC (Cu catalysis)."""
        cuaac = REAGENT_PROFILES["cuaac_click_coupling"]
        spaac = REAGENT_PROFILES["spaac_click_coupling"]
        assert cuaac.k_forward > spaac.k_forward * 10


class TestM7_MultipointEnzyme:
    """M7: glyoxyl → multipoint stability chain."""

    def test_glyoxyl_produces_glyoxyl_acs(self):
        rp = REAGENT_PROFILES["glyoxyl_chained_activation"]
        assert rp.product_acs.value == ACSSiteType.GLYOXYL.value

    def test_multipoint_stability_consumes_glyoxyl(self):
        rp = REAGENT_PROFILES["multipoint_stability_uplift"]
        assert rp.target_acs.value == ACSSiteType.GLYOXYL.value
        assert rp.is_macromolecule is True
        assert 0 < rp.activity_retention <= 1.0


class TestM8_MaterialAsLigand:
    """M8: amylose-MBP material-as-ligand pattern."""

    def test_amylose_profile_uses_material_as_ligand_mode(self):
        rp = REAGENT_PROFILES["amylose_mbp_affinity"]
        assert rp.functional_mode == "material_as_ligand"

    def test_amylose_promoted_to_tier_1(self):
        """B9.1 + Tier-1 promotion: AMYLOSE is now UI-enabled."""
        from dpsim.datatypes import (
            PolymerFamily,
            is_family_enabled_in_ui,
            is_material_as_ligand,
        )
        assert is_family_enabled_in_ui(PolymerFamily.AMYLOSE) is True
        assert is_material_as_ligand(PolymerFamily.AMYLOSE) is True


class TestM9_BoronateAffinity:
    """M9: aminophenylboronic acid pH-switchable cis-diol affinity."""

    def test_apba_carries_boronate_pka(self):
        rp = REAGENT_PROFILES["apba_boronate_coupling"]
        # Boronate pKa ≈ 8.5 — must be in the boronate range
        assert 7.5 <= rp.pKa_nucleophile <= 10.0
        assert rp.functional_mode == "boronate"


class TestVocabularyCoverage:
    """Sanity: every v9.2 functional_mode and chemistry_class is exercised
    by at least one v9.2 reagent profile (no dead vocabulary entries)."""

    def test_v9_2_functional_modes_all_used(self):
        v9_2_modes = {
            "dye_pseudo_affinity", "mixed_mode_hcic", "thiophilic",
            "boronate", "click_handle", "material_as_ligand",
        }
        used_modes = {
            REAGENT_PROFILES[k].functional_mode for k in V9_2_TIER1_KEYS
        }
        # Every v9.2 mode (except peptide_affinity, oligonucleotide
        # which are Tier-2) must be used by at least one Tier-1 profile.
        unused = v9_2_modes - used_modes
        assert not unused, f"Unused v9.2 functional_modes: {unused}"

    def test_v9_2_chemistry_classes_all_used(self):
        v9_2_classes = {
            "oxime", "hydrazone", "cuaac", "spaac",
            "dye_triazine", "cnbr_amine", "cdi_amine",
            "glyoxyl_multipoint",
        }
        used_classes = {
            REAGENT_PROFILES[k].chemistry_class for k in V9_2_TIER1_KEYS
        }
        unused = v9_2_classes - used_classes
        # phenol_radical is Tier-2 (HRP/H2O2 — C9 in SA Tier-2)
        assert not unused, f"Unused v9.2 chemistry_classes: {unused}"
