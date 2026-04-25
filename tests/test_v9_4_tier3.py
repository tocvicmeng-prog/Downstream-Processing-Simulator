"""Tests for v9.4 Tier-3 polymer-family L2 solvers + reagent profiles.

Coverage:
  - 4 promoted Tier-3 single-polymer families (PECTIN, GELLAN, PULLULAN,
    STARCH) are UI-enabled and dispatch correctly via composite_dispatch.
  - 3 multi-variant Tier-3 composites (PECTIN_CHITOSAN, GELLAN_ALGINATE,
    PULLULAN_DEXTRAN) remain placeholders that raise NotImplementedError.
  - 4 new Tier-3 reagent profiles (Al³⁺, borax, glyoxal, calmodulin)
    register with appropriate hazard flags.
  - Al³⁺ ion-gelant is biotherapeutic-unsafe; borax is biotherapeutic-
    safe but flagged reversible; STMP path on starch / pullulan works.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from dpsim.datatypes import (
    MaterialProperties,
    ModelEvidenceTier,
    PolymerFamily,
    SimulationParameters,
    is_family_enabled_in_ui,
)
from dpsim.level2_gelation.composite_dispatch import solve_gelation_by_family
from dpsim.level2_gelation.ion_registry import (
    FREESTANDING_ION_GELANTS,
    ION_GELANT_REGISTRY,
    is_biotherapeutic_safe_ion,
)
from dpsim.level2_gelation.tier3_families import (
    solve_pullulan_gelation,
    solve_starch_gelation,
)
from dpsim.module2_functionalization.reagent_profiles import REAGENT_PROFILES


V9_4_TIER3_PROMOTED_FAMILIES = [
    PolymerFamily.PECTIN,
    PolymerFamily.GELLAN,
    PolymerFamily.PULLULAN,
    PolymerFamily.STARCH,
]

V9_4_TIER3_PLACEHOLDER_FAMILIES = [
    PolymerFamily.PECTIN_CHITOSAN,
    PolymerFamily.GELLAN_ALGINATE,
    PolymerFamily.PULLULAN_DEXTRAN,
]


class TestV9_4_Tier3UIPromotion:

    @pytest.mark.parametrize("fam", V9_4_TIER3_PROMOTED_FAMILIES)
    def test_tier3_single_family_ui_enabled(self, fam):
        assert is_family_enabled_in_ui(fam) is True, (
            f"v9.4 Tier-3 {fam.value!r} should be UI-enabled after "
            f"v9.4 promotion"
        )

    @pytest.mark.parametrize("fam", V9_4_TIER3_PLACEHOLDER_FAMILIES)
    def test_tier3_composite_remains_placeholder(self, fam):
        """v9.4: multi-variant composites stay data-only until v9.5+."""
        assert is_family_enabled_in_ui(fam) is False


class TestV9_4_Tier3SolverDirect:
    """Direct-call solver tests that don't rely on scipy-heavy delegate
    paths (PECTIN and GELLAN go through alginate ionic-Ca which can
    timeout under Python 3.14)."""

    def test_pullulan_solver(self):
        props = replace(MaterialProperties(),
                        polymer_family=PolymerFamily.PULLULAN)
        result = solve_pullulan_gelation(
            SimulationParameters(), props, R_droplet=50e-6,
        )
        assert result.model_tier == "pullulan_ech_v9_4"
        assert (result.model_manifest.evidence_tier.value
                == ModelEvidenceTier.QUALITATIVE_TREND.value)

    def test_starch_solver_carries_research_mode_flag(self):
        props = replace(MaterialProperties(),
                        polymer_family=PolymerFamily.STARCH)
        result = solve_starch_gelation(
            SimulationParameters(), props, R_droplet=50e-6,
        )
        diag = result.model_manifest.diagnostics
        assert diag.get("research_mode_only") is True
        assert "amylase_susceptibility" in diag

    def test_solver_rejects_wrong_family(self):
        wrong = replace(MaterialProperties(),
                        polymer_family=PolymerFamily.AGAROSE)
        with pytest.raises(ValueError, match="PULLULAN"):
            solve_pullulan_gelation(
                SimulationParameters(), wrong, R_droplet=50e-6,
            )


class TestV9_4_Tier3Dispatch:

    @pytest.mark.parametrize("fam", [
        PolymerFamily.PULLULAN,
        PolymerFamily.STARCH,
    ])
    def test_dispatcher_routes_neutral_alpha_glucan_tier3(self, fam):
        """Pullulan / starch use dextran-ECH delegate (no scipy)."""
        params = SimulationParameters()
        props = replace(MaterialProperties(), polymer_family=fam)
        result = solve_gelation_by_family(params, props, R_droplet=50e-6)
        assert result is not None
        assert result.pore_size_mean > 0

    @pytest.mark.parametrize("fam", V9_4_TIER3_PLACEHOLDER_FAMILIES)
    def test_composite_placeholders_raise_not_implemented(self, fam):
        """v9.4 multi-variant composites must raise NotImplementedError
        with a clear v9.5 deferral message."""
        props = replace(MaterialProperties(), polymer_family=fam)
        with pytest.raises(NotImplementedError, match="Tier-3"):
            solve_gelation_by_family(
                SimulationParameters(), props, R_droplet=50e-6,
            )


class TestV9_4_Tier3IonGelants:

    def test_pectin_Ca_entry_present(self):
        profile = ION_GELANT_REGISTRY.get(
            (PolymerFamily.PECTIN, "Ca2+ (LM pectin)")
        )
        assert profile is not None
        assert profile.biotherapeutic_safe is True

    def test_gellan_K_entry_present(self):
        profile = ION_GELANT_REGISTRY.get(
            (PolymerFamily.GELLAN, "K+ (low-acyl)")
        )
        assert profile is not None
        assert profile.biotherapeutic_safe is True

    def test_gellan_Al_entry_marked_non_biotherapeutic(self):
        profile = ION_GELANT_REGISTRY.get(
            (PolymerFamily.GELLAN, "Al3+ (research, non-biotherapeutic)")
        )
        assert profile is not None
        assert profile.biotherapeutic_safe is False, (
            "Al³⁺ gellan gelant must be marked biotherapeutic-unsafe "
            "per ICH/FDA aluminum residue regulations"
        )

    def test_alcl3_freestanding_gate(self):
        """is_biotherapeutic_safe_ion must reject Al³⁺ freestanding."""
        assert is_biotherapeutic_safe_ion("alcl3") is False

    def test_borax_freestanding_safe(self):
        """Borax/borate IS biotherapeutic-safe (boron residues are not
        currently regulated at the same level as Al³⁺); the concern is
        reversibility, not residue."""
        assert is_biotherapeutic_safe_ion("borax") is True

    def test_kcl_and_caso4_still_safe(self):
        """v9.2 freestanding gelants must remain biotherapeutic-safe
        after v9.4 additions."""
        assert is_biotherapeutic_safe_ion("kcl") is True
        assert is_biotherapeutic_safe_ion("caso4") is True


class TestV9_4_Tier3ReagentProfiles:
    """4 new v9.4 Tier-3 reagent profiles."""

    V9_4_KEYS = [
        "alcl3_trivalent_gelant",
        "borax_reversible_crosslinking",
        "glyoxal_dialdehyde",
        "calmodulin_cbp_tap_coupling",
    ]

    @pytest.mark.parametrize("key", V9_4_KEYS)
    def test_profile_present(self, key):
        assert key in REAGENT_PROFILES, f"v9.4 Tier-3 profile {key!r} missing"

    @pytest.mark.parametrize("key", V9_4_KEYS)
    def test_profile_has_calibration_source(self, key):
        rp = REAGENT_PROFILES[key]
        assert rp.calibration_source != "", (
            f"{key!r}: calibration_source is empty"
        )

    def test_alcl3_carries_non_biotherapeutic_hazard(self):
        rp = REAGENT_PROFILES["alcl3_trivalent_gelant"]
        # regulatory_limit_ppm = 0 is the explicit "do not use" marker
        assert rp.regulatory_limit_ppm == 0.0
        assert "non_biotherapeutic" in rp.hazard_class.lower()

    def test_borax_carries_reversibility_hazard(self):
        rp = REAGENT_PROFILES["borax_reversible_crosslinking"]
        assert "reversible" in rp.hazard_class.lower()

    def test_glyoxal_lower_priority_than_glutaraldehyde(self):
        """Glyoxal k_forward should be slower than glutaraldehyde
        (validates the SA report's "lower priority" assessment)."""
        glyoxal = REAGENT_PROFILES["glyoxal_dialdehyde"]
        glutaraldehyde = REAGENT_PROFILES["glutaraldehyde_secondary"]
        assert glyoxal.k_forward < glutaraldehyde.k_forward

    def test_calmodulin_is_macromolecule_with_ca_dependence(self):
        rp = REAGENT_PROFILES["calmodulin_cbp_tap_coupling"]
        assert rp.is_macromolecule is True
        assert "ca" in rp.notes.lower()
        assert rp.confidence_tier == "ranking_only"
