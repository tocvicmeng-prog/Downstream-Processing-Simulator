"""B-2f / W-026 tests: per-family K_geom registry + valid_domain.

Covers FAMILY_KGEOM_REGISTRY structure, lookup_family_kgeom dispatch
(including the v9.0 Family-First .value-comparison contract), the
fallback path for unregistered families, and check_valid_domain
violation detection.
"""

from __future__ import annotations

import pytest

from dpsim.datatypes import ModelEvidenceTier, PolymerFamily
from dpsim.module3_performance.family_kgeom import (
    FAMILY_KGEOM_REGISTRY,
    FamilyKGeom,
    check_valid_domain,
    is_family_registered,
    lookup_family_kgeom,
    registered_families,
)


# ─── Registry coverage ───────────────────────────────────────────────────────


class TestRegistryCoverage:
    """The five default-anchor families must all be registered."""

    @pytest.mark.parametrize(
        "family_value",
        ["agarose", "agarose_chitosan", "cellulose", "plga", "alginate"],
    )
    def test_default_anchor_families_registered(self, family_value: str) -> None:
        assert family_value in FAMILY_KGEOM_REGISTRY

    def test_registered_families_returns_all_five(self) -> None:
        # Sorted tuple — alphabetical order.
        assert registered_families() == (
            "agarose", "agarose_chitosan", "alginate", "cellulose", "plga",
        )

    def test_is_family_registered_true_for_agarose(self) -> None:
        assert is_family_registered(PolymerFamily.AGAROSE)

    def test_is_family_registered_false_for_chitosan(self) -> None:
        # Per work plan §6: families beyond the 5 default anchors are
        # explicitly out of scope for v0.7.
        assert not is_family_registered(PolymerFamily.CHITOSAN)


# ─── K_geom anchoring (literature-anchored ordering) ────────────────────────


class TestKGeomOrdering:
    """K_geom values must follow the literature ordering from sci-advisor §B."""

    def test_cellulose_is_stiffest(self) -> None:
        # Rigid fibrous backbone; published u_crit up to ~1000 cm/h.
        cellulose = FAMILY_KGEOM_REGISTRY["cellulose"].K_geom
        assert cellulose >= max(
            FAMILY_KGEOM_REGISTRY["agarose"].K_geom,
            FAMILY_KGEOM_REGISTRY["agarose_chitosan"].K_geom,
            FAMILY_KGEOM_REGISTRY["alginate"].K_geom,
        )

    def test_alginate_is_softest(self) -> None:
        # Ionically crosslinked; lower K_geom than agarose.
        alginate = FAMILY_KGEOM_REGISTRY["alginate"].K_geom
        assert alginate <= FAMILY_KGEOM_REGISTRY["agarose"].K_geom

    def test_agarose_chitosan_above_pure_agarose(self) -> None:
        # IPN composite is stiffer per Pa than pure agarose.
        ac = FAMILY_KGEOM_REGISTRY["agarose_chitosan"].K_geom
        a = FAMILY_KGEOM_REGISTRY["agarose"].K_geom
        assert ac > a

    @pytest.mark.parametrize(
        "family_value",
        ["agarose", "agarose_chitosan", "cellulose", "plga", "alginate"],
    )
    def test_K_geom_in_literature_range(self, family_value: str) -> None:
        # Sci-advisor delivery 2026-05-10 §B: K_geom range ~1e-3 to 2e-2.
        K = FAMILY_KGEOM_REGISTRY[family_value].K_geom
        assert 1e-3 <= K <= 2e-2


# ─── Per-family valid_domain ─────────────────────────────────────────────────


class TestValidDomainFields:
    """Every registered family must expose the 5 standard valid_domain dimensions."""

    @pytest.mark.parametrize(
        "family_value",
        ["agarose", "agarose_chitosan", "cellulose", "plga", "alginate"],
    )
    def test_required_keys_present(self, family_value: str) -> None:
        domain = FAMILY_KGEOM_REGISTRY[family_value].valid_domain
        for key in ["bead_d32_m", "bed_height_m", "T_C", "mu_pa_s", "G_DN_pa"]:
            assert key in domain, f"{family_value!r} missing {key!r}"

    def test_plga_T_window_tightened(self) -> None:
        # PLGA T_C upper bound tightened to 25 °C (T_g-aware).
        plga = FAMILY_KGEOM_REGISTRY["plga"]
        assert plga.valid_domain["T_C"] == (4.0, 25.0)


class TestBaseTier:
    """All registered families carry SEMI_QUANTITATIVE base_tier in v0.7."""

    @pytest.mark.parametrize(
        "family_value",
        ["agarose", "agarose_chitosan", "cellulose", "plga", "alginate"],
    )
    def test_base_tier_is_semi_quantitative(self, family_value: str) -> None:
        assert (
            FAMILY_KGEOM_REGISTRY[family_value].base_tier
            == ModelEvidenceTier.SEMI_QUANTITATIVE
        )


# ─── Lookup dispatch ─────────────────────────────────────────────────────────


class TestLookupDispatch:
    """lookup_family_kgeom compares by .value (v9.0 Family-First contract)."""

    def test_lookup_agarose_returns_correct_entry(self) -> None:
        entry = lookup_family_kgeom(PolymerFamily.AGAROSE)
        assert entry.family_value == "agarose"
        assert entry.K_geom == 5e-3

    def test_lookup_uses_value_not_identity(self) -> None:
        # The anti-identity contract: PolymerFamily reload aliasing must
        # not break lookup. Simulate by constructing a fresh enum with
        # the same value (as Streamlit reload would).
        from enum import Enum

        class FreshPolymerFamily(Enum):
            AGAROSE = "agarose"

        # The lookup must succeed because we compare by .value.
        entry = lookup_family_kgeom(FreshPolymerFamily.AGAROSE)  # type: ignore[arg-type]
        assert entry.family_value == "agarose"

    def test_lookup_unregistered_returns_fallback_by_default(self) -> None:
        # CHITOSAN is in the enum but not in the v0.7 registry.
        entry = lookup_family_kgeom(PolymerFamily.CHITOSAN)
        assert entry.family_value == "__fallback__"
        assert entry.base_tier == ModelEvidenceTier.QUALITATIVE_TREND

    def test_lookup_unregistered_raises_when_fallback_disabled(self) -> None:
        with pytest.raises(KeyError, match="No K_geom registered"):
            lookup_family_kgeom(PolymerFamily.CHITOSAN, use_fallback=False)


# ─── Fallback semantics ──────────────────────────────────────────────────────


class TestFallback:
    """Fallback entry must be conservative (lower K_geom + weaker tier)."""

    def test_fallback_K_geom_at_or_below_agarose(self) -> None:
        # Conservative low-end under-predicts u_crit (safer for an
        # operational limit).
        fallback = lookup_family_kgeom(PolymerFamily.HYALURONATE)
        assert fallback.K_geom <= FAMILY_KGEOM_REGISTRY["agarose"].K_geom

    def test_fallback_tier_is_qualitative_trend(self) -> None:
        # Forces downstream rendering to INTERVAL/RANK_BAND, never NUMBER.
        fallback = lookup_family_kgeom(PolymerFamily.AMYLOSE)
        assert fallback.base_tier == ModelEvidenceTier.QUALITATIVE_TREND


# ─── check_valid_domain ──────────────────────────────────────────────────────


class TestCheckValidDomain:
    """Walking valid_domain and detecting out-of-bounds inputs."""

    def test_in_domain_returns_empty(self) -> None:
        agarose = lookup_family_kgeom(PolymerFamily.AGAROSE)
        violations = check_valid_domain(
            agarose,
            bead_d32_m=90e-6,
            bed_height_m=0.10,
            T_C=20.0,
            mu_pa_s=1e-3,
            G_DN_pa=5000.0,
        )
        assert violations == ()

    def test_d32_below_range_violates(self) -> None:
        agarose = lookup_family_kgeom(PolymerFamily.AGAROSE)
        violations = check_valid_domain(
            agarose,
            bead_d32_m=10e-6,  # below 40e-6 lower bound
            bed_height_m=0.10,
            T_C=20.0,
            mu_pa_s=1e-3,
            G_DN_pa=5000.0,
        )
        assert len(violations) == 1
        assert "bead_d32_m" in violations[0]

    def test_T_below_range_violates(self) -> None:
        agarose = lookup_family_kgeom(PolymerFamily.AGAROSE)
        violations = check_valid_domain(
            agarose,
            bead_d32_m=90e-6,
            bed_height_m=0.10,
            T_C=-5.0,  # below 4 °C
            mu_pa_s=1e-3,
            G_DN_pa=5000.0,
        )
        assert any("T_C" in v for v in violations)

    def test_plga_T_window_demoted_at_30C(self) -> None:
        # PLGA's T_C upper bound is tightened to 25 °C (T_g-aware).
        plga = lookup_family_kgeom(PolymerFamily.PLGA)
        violations = check_valid_domain(
            plga,
            bead_d32_m=90e-6,
            bed_height_m=0.10,
            T_C=30.0,  # above PLGA's 25 °C ceiling
            mu_pa_s=1e-3,
            G_DN_pa=5000.0,
        )
        assert any("T_C" in v for v in violations)

    def test_multiple_out_of_bounds_lists_all(self) -> None:
        agarose = lookup_family_kgeom(PolymerFamily.AGAROSE)
        violations = check_valid_domain(
            agarose,
            bead_d32_m=10e-6,   # too small
            bed_height_m=0.001, # too short
            T_C=50.0,           # too hot
            mu_pa_s=10e-3,      # too viscous
            G_DN_pa=1e2,        # too soft
        )
        assert len(violations) == 5


# ─── Frozen contract ─────────────────────────────────────────────────────────


class TestFrozenContract:
    """FamilyKGeom is a frozen dataclass."""

    def test_cannot_mutate(self) -> None:
        from dataclasses import FrozenInstanceError

        entry = lookup_family_kgeom(PolymerFamily.AGAROSE)
        with pytest.raises(FrozenInstanceError):
            entry.K_geom = 999.0  # type: ignore[misc]
