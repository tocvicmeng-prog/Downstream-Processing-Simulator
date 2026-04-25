"""v0.3.5 — UI audit follow-on tests (fixes 3, 4, 5).

Closes the three remaining items from the v0.3.3 UI audit:

* Fix 3 — Ion-gelant picker: ``ION_GELANT_REGISTRY`` (9 per-family
  entries) + ``FREESTANDING_ION_GELANTS`` (4 entries) are surfaced via
  the new ``ion_gelant_picker`` module.
* Fix 4 — ACSSiteType visibility: every reagent's ``target_acs`` and
  ``product_acs`` are now displayed in the M2 caption; the audit gate
  asserts that ≥ 23 of 25 ``ACSSiteType`` values are referenced via
  some reagent's target or product.
* Fix 5 — Crosslinker registry split: documentation gate asserting
  the cross-reference comments stay in both registries.
"""

from __future__ import annotations

import pytest

from dpsim.datatypes import PolymerFamily
from dpsim.level2_gelation.ion_registry import (
    FREESTANDING_ION_GELANTS,
    ION_GELANT_REGISTRY,
)
from dpsim.module2_functionalization.acs import ACSSiteType
from dpsim.module2_functionalization.reagent_profiles import REAGENT_PROFILES
from dpsim.visualization.tabs.m1.ion_gelant_picker import (
    available_ion_gelants_for_family,
    family_has_ion_gelants,
)


# --------------------------------------------------------------------------- #
# Fix 3: Ion-gelant picker                                                     #
# --------------------------------------------------------------------------- #


class TestIonGelantPicker:
    @pytest.mark.parametrize("family", [
        PolymerFamily.ALGINATE,
        PolymerFamily.KAPPA_CARRAGEENAN,
        PolymerFamily.HYALURONATE,
        PolymerFamily.PECTIN,
        PolymerFamily.GELLAN,
    ])
    def test_ionic_gel_family_surfaces_at_least_one_option(
        self, family: PolymerFamily,
    ) -> None:
        opts = available_ion_gelants_for_family(family)
        assert len(opts) >= 1
        assert family_has_ion_gelants(family) is True

    @pytest.mark.parametrize("family", [
        PolymerFamily.PLGA,
        PolymerFamily.AGAROSE,
        PolymerFamily.CELLULOSE,
        PolymerFamily.DEXTRAN,
    ])
    def test_non_ionic_family_returns_empty_list(
        self, family: PolymerFamily,
    ) -> None:
        opts = available_ion_gelants_for_family(family)
        assert opts == []
        assert family_has_ion_gelants(family) is False

    def test_every_registered_per_family_entry_is_surfaced(self) -> None:
        """Every entry in ION_GELANT_REGISTRY must appear in the
        picker's output for its family — covers the audit's
        '12-of-13-unsurfaced' regression."""
        for (family, ion_key), profile in ION_GELANT_REGISTRY.items():
            opts = available_ion_gelants_for_family(family)
            keys = {o.key for o in opts if not o.is_freestanding}
            assert ion_key in keys, (
                f"({family.value}, {ion_key!r}) missing from picker output"
            )

    def test_freestanding_ion_surfaces_when_a_per_family_entry_uses_same_ion(
        self,
    ) -> None:
        """KCl (freestanding K+) must surface for κ-carrageenan because
        the per-family registry has a K+ entry there."""
        opts = available_ion_gelants_for_family(PolymerFamily.KAPPA_CARRAGEENAN)
        free_keys = {o.key for o in opts if o.is_freestanding}
        assert "kcl" in free_keys

        opts_alginate = available_ion_gelants_for_family(PolymerFamily.ALGINATE)
        alginate_free = {o.key for o in opts_alginate if o.is_freestanding}
        assert "caso4" in alginate_free  # Ca2+ source

    def test_non_biotherapeutic_safe_flag_propagates(self) -> None:
        """Al³⁺ entries (biotherapeutic_safe=False) must carry the flag
        so the UI can surface a warning."""
        opts = available_ion_gelants_for_family(PolymerFamily.GELLAN)
        unsafe = [o for o in opts if not o.biotherapeutic_safe]
        assert len(unsafe) >= 1
        assert any(o.full_profile.ion == "Al3+" for o in unsafe)


# --------------------------------------------------------------------------- #
# Fix 4: ACSSiteType visibility                                                #
# --------------------------------------------------------------------------- #


class TestACSSiteTypeCoverage:
    def test_at_least_23_of_25_acs_types_referenced_via_reagents(self) -> None:
        """Every reagent now displays target_acs / product_acs in the
        M2 caption; the audit gate is that ≥ 23 of 25 ACSSiteType
        values appear as a target or product on at least one reagent.

        The 2 unreferenced are documented backend follow-ons:
        - ``alkyne`` — SPAAC click partner; reagent backend lists
          ``azide`` only on the click reagents (data oversight).
        - ``sulfate_ester`` — passive κ-carrageenan polymer-side surface
          group; not a reagent target.
        """
        referenced: set[str] = set()
        for profile in REAGENT_PROFILES.values():
            target = getattr(profile, "target_acs", None)
            product = getattr(profile, "product_acs", None)
            if target is not None:
                referenced.add(getattr(target, "value", str(target)))
            if product is not None:
                referenced.add(getattr(product, "value", str(product)))

        all_acs = {st.value for st in ACSSiteType}
        coverage = len(referenced & all_acs) / len(all_acs)
        assert coverage >= 23 / 25, (
            f"ACSSiteType reference coverage regressed to {coverage:.1%}; "
            f"unreferenced: {sorted(all_acs - referenced)}"
        )

    def test_known_unreferenced_acs_types_remain_documented(self) -> None:
        """Spot-check the documented unreferenced set so a future
        addition that closes one of these gaps trips the test (the
        team should celebrate AND update the doc)."""
        documented_unreferenced = {"alkyne", "sulfate_ester"}

        referenced: set[str] = set()
        for profile in REAGENT_PROFILES.values():
            for attr in ("target_acs", "product_acs"):
                v = getattr(profile, attr, None)
                if v is not None:
                    referenced.add(getattr(v, "value", str(v)))

        all_acs = {st.value for st in ACSSiteType}
        actual_unreferenced = all_acs - referenced
        assert actual_unreferenced == documented_unreferenced, (
            f"Unreferenced ACSSiteType set drifted from the documented "
            f"baseline. Update the docstring + this test if you "
            f"intentionally added/closed a gap. "
            f"Documented: {sorted(documented_unreferenced)}; "
            f"Actual: {sorted(actual_unreferenced)}"
        )

    def test_every_reagent_has_target_acs(self) -> None:
        """Every reagent must declare ``target_acs`` so the M2 caption
        has something to render."""
        missing = []
        for key, profile in REAGENT_PROFILES.items():
            if getattr(profile, "target_acs", None) is None:
                missing.append(key)
        assert not missing, f"Reagents missing target_acs: {sorted(missing)}"


# --------------------------------------------------------------------------- #
# Fix 5: Crosslinker registry docs                                             #
# --------------------------------------------------------------------------- #


class TestCrosslinkerRegistrySplitDocs:
    def test_reagent_library_documents_split(self) -> None:
        """``CROSSLINKERS`` must carry the v0.3.5 cross-reference
        comment so future contributors don't accidentally consolidate
        the two registries."""
        from pathlib import Path
        text = Path("src/dpsim/reagent_library.py").read_text(encoding="utf-8")
        assert "L3 / M1 covalent-hardening" in text
        assert "REAGENT_PROFILES[mode='crosslinker']" in text
        assert "Do not consolidate" in text

    def test_reagent_profiles_documents_split(self) -> None:
        """``REAGENT_PROFILES`` module docstring must carry the
        cross-reference back to ``CROSSLINKERS``."""
        from pathlib import Path
        text = Path(
            "src/dpsim/module2_functionalization/reagent_profiles.py"
        ).read_text(encoding="utf-8")
        assert "M2 secondary-crosslinking step" in text
        assert "dpsim.reagent_library.CROSSLINKERS" in text
        assert "Do not consolidate" in text


# --------------------------------------------------------------------------- #
# Smoke: family selector still imports cleanly with the new picker hook       #
# --------------------------------------------------------------------------- #


def test_family_selector_imports_with_picker() -> None:
    """The v0.3.5 ion-gelant picker is invoked from family_selector.py;
    the import must remain clean."""
    from dpsim.visualization.tabs.m1 import family_selector  # noqa: F401
    from dpsim.visualization.tabs.m1 import ion_gelant_picker  # noqa: F401
    # Both modules export their public API
    assert hasattr(ion_gelant_picker, "render_ion_gelant_picker")
    assert hasattr(ion_gelant_picker, "available_ion_gelants_for_family")
    assert hasattr(ion_gelant_picker, "family_has_ion_gelants")
