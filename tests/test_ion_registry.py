"""Tests for the v9.2 per-polymer ion-gelation registry (A3.1, A3.2, A3.4, A3.5).

This module is schema-additive only; it does NOT touch the existing
alginate solver. The M0b alginate-via-registry refactor is a separate
piece of work (A3.3) and gets its own golden-master regression test.
"""

from __future__ import annotations

import pytest

from dpsim.datatypes import PolymerFamily
from dpsim.level2_gelation.ion_registry import (
    FREESTANDING_ION_GELANTS,
    ION_GELANT_REGISTRY,
    FreestandingIonGelant,
    IonGelantProfile,
    get_ion_gelant,
    is_biotherapeutic_safe_ion,
    list_ion_gelants_for_family,
)


class TestIonGelantProfile:

    def test_dataclass_is_frozen(self):
        """IonGelantProfile must be immutable (registry consumers expect this)."""
        profile = next(iter(ION_GELANT_REGISTRY.values()))
        with pytest.raises(Exception):
            profile.ion = "Na+"  # type: ignore[misc]

    def test_alginate_cacl2_external_present(self):
        profile = get_ion_gelant(PolymerFamily.ALGINATE, "Ca2+ (CaCl2 external)")
        assert profile is not None
        assert profile.mode == "external_bath"
        assert profile.C_ion_bath == pytest.approx(100.0)
        assert profile.biotherapeutic_safe is True

    def test_alginate_caso4_internal_present(self):
        """A3.4 — new CaSO4 internal-release entry."""
        profile = get_ion_gelant(PolymerFamily.ALGINATE, "Ca2+ (CaSO4 internal)")
        assert profile is not None
        assert profile.mode == "internal_release"
        assert profile.k_release > 0
        # CaSO4 should be faster than GDL/CaCO3 (~1.5e-4) but still slow
        assert profile.k_release == pytest.approx(5e-4)

    def test_alginate_gdl_caco3_internal_present(self):
        profile = get_ion_gelant(PolymerFamily.ALGINATE, "Ca2+ (GDL/CaCO3 internal)")
        assert profile is not None
        assert profile.mode == "internal_release"

    def test_unknown_pair_returns_none(self):
        # AGAROSE has no native ionic gelation; should return None.
        assert get_ion_gelant(PolymerFamily.AGAROSE, "Ca2+") is None

    def test_list_for_alginate_returns_three(self):
        # External CaCl2 + GDL/CaCO3 internal + CaSO4 internal = 3
        profiles = list_ion_gelants_for_family(PolymerFamily.ALGINATE)
        assert len(profiles) == 3

    def test_list_for_unknown_family_returns_empty(self):
        assert list_ion_gelants_for_family(PolymerFamily.AGAROSE) == ()

    # ── v9.3 Tier-2 ion-gelation entries ──────────────────────────────

    def test_kappa_carrageenan_K_entry_present(self):
        """v9.3: κ-carrageenan + K+ is the canonical Tier-2 ionic-gelation pair."""
        profile = get_ion_gelant(PolymerFamily.KAPPA_CARRAGEENAN, "K+ (KCl external)")
        assert profile is not None
        assert profile.ion == "K+"
        assert profile.mode == "external_bath"
        assert profile.C_ion_bath == pytest.approx(200.0)
        assert profile.biotherapeutic_safe is True

    def test_hyaluronate_Ca_cofactor_entry_present(self):
        """v9.3: HA + Ca²⁺ is registered with low suitability (HA is
        primarily covalently crosslinked)."""
        profile = get_ion_gelant(PolymerFamily.HYALURONATE, "Ca2+ (cofactor)")
        assert profile is not None
        assert profile.suitability <= 5, (
            "HA + Ca²⁺ should carry low suitability — HA is primarily "
            "covalently crosslinked via BDDE/HRP-tyramine/ADH, not "
            "ionically gelled"
        )


class TestFreestandingIonGelants:
    """A3.5 — KCl + CaSO4 freestanding entries (consumed in v9.3 by Tier-2 families)."""

    def test_kcl_present(self):
        gel = FREESTANDING_ION_GELANTS["kcl"]
        assert isinstance(gel, FreestandingIonGelant)
        assert gel.ion == "K+"
        assert gel.biotherapeutic_safe is True

    def test_caso4_present(self):
        gel = FREESTANDING_ION_GELANTS["caso4"]
        assert gel.ion == "Ca2+"
        assert gel.biotherapeutic_safe is True


class TestBiotherapeuticSafety:

    def test_kcl_is_safe(self):
        assert is_biotherapeutic_safe_ion("kcl") is True

    def test_caso4_is_safe(self):
        assert is_biotherapeutic_safe_ion("caso4") is True

    def test_ca2plus_via_registry_is_safe(self):
        assert is_biotherapeutic_safe_ion("Ca2+") is True

    def test_unknown_ion_is_rejected(self):
        # Conservative default: unknown ion is NOT biotherapeutic-safe.
        # Per SA report, this is the gate that blocks Al3+ from default
        # workflows when registered (Tier-3, biotherapeutic_safe=False).
        assert is_biotherapeutic_safe_ion("Al3+") is False
        assert is_biotherapeutic_safe_ion("Sr2+") is False


class TestRegistryInvariants:

    def test_no_negative_concentrations(self):
        for profile in ION_GELANT_REGISTRY.values():
            assert profile.C_ion_bath >= 0
            assert profile.C_ion_source >= 0
            assert profile.k_release >= 0

    def test_modes_are_valid(self):
        valid = {"external_bath", "internal_release"}
        for profile in ION_GELANT_REGISTRY.values():
            assert profile.mode in valid, f"{profile.ion}: bad mode {profile.mode!r}"

    def test_external_mode_uses_C_ion_bath_only(self):
        for profile in ION_GELANT_REGISTRY.values():
            if profile.mode == "external_bath":
                assert profile.C_ion_bath > 0
                assert profile.C_ion_source == 0
                assert profile.k_release == 0

    def test_internal_mode_uses_release_path(self):
        for profile in ION_GELANT_REGISTRY.values():
            if profile.mode == "internal_release":
                assert profile.C_ion_source > 0
                assert profile.k_release > 0
                assert profile.C_ion_bath == 0

    def test_polymer_family_matches_key(self):
        for (key_family, _key_label), profile in ION_GELANT_REGISTRY.items():
            assert key_family.value == profile.polymer_family.value
