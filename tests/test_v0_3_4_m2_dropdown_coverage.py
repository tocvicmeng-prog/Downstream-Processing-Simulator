"""v0.3.4 M2 dropdown coverage gate.

After the v0.3.3 audit found that 44 of 94 backend reagents were
invisible to the M2 UI (the hardcoded 9-bucket if/elif chain only
listed v9.1 baseline reagents), v0.3.4 replaced the hardcoded dicts
with a single ``_reagent_options_for_bucket()`` helper driven by
``REAGENT_PROFILES.functional_mode``.

These tests are a permanent gate against the regression: any future
addition of a new ``functional_mode`` value in
``ALLOWED_FUNCTIONAL_MODES`` must also be added to ``_BUCKET_TO_MODES``
in ``tab_m2.py``, or the suite fails. Likewise, every reagent shipped
in ``REAGENT_PROFILES`` must surface in at least one bucket.
"""

from __future__ import annotations

import pytest

from dpsim.module2_functionalization.reagent_profiles import (
    ALLOWED_FUNCTIONAL_MODES,
    REAGENT_PROFILES,
)
from dpsim.visualization.tabs.tab_m2 import (
    _BUCKET_DISPLAY_ORDER,
    _BUCKET_TO_MODES,
    _reagent_options_for_bucket,
)


class TestBucketTaxonomyCoverage:
    def test_every_allowed_functional_mode_lives_in_exactly_one_bucket(
        self,
    ) -> None:
        """Every value in ALLOWED_FUNCTIONAL_MODES must appear in exactly
        one bucket. New modes added to the closed vocabulary must also
        be added to _BUCKET_TO_MODES, or the M2 dropdown will silently
        hide their reagents."""
        all_modes_in_buckets: list[str] = []
        for modes in _BUCKET_TO_MODES.values():
            all_modes_in_buckets.extend(modes)

        unique = set(all_modes_in_buckets)
        # Every allowed mode is covered
        assert ALLOWED_FUNCTIONAL_MODES.issubset(unique), (
            "These ALLOWED_FUNCTIONAL_MODES values are missing from "
            f"_BUCKET_TO_MODES: {sorted(ALLOWED_FUNCTIONAL_MODES - unique)}"
        )
        # No mode appears in more than one bucket
        duplicates = [m for m in all_modes_in_buckets if all_modes_in_buckets.count(m) > 1]
        assert not duplicates, (
            f"These functional_mode values appear in more than one "
            f"bucket: {sorted(set(duplicates))}"
        )
        # No bucket carries an unknown mode value
        unknown = unique - ALLOWED_FUNCTIONAL_MODES
        assert not unknown, (
            f"These _BUCKET_TO_MODES values are not in "
            f"ALLOWED_FUNCTIONAL_MODES: {sorted(unknown)}"
        )

    def test_display_order_matches_buckets(self) -> None:
        assert set(_BUCKET_DISPLAY_ORDER) == set(_BUCKET_TO_MODES.keys())
        # No duplicates in display order
        assert len(_BUCKET_DISPLAY_ORDER) == len(set(_BUCKET_DISPLAY_ORDER))


class TestReagentCoverage:
    def test_every_reagent_appears_in_at_least_one_bucket(self) -> None:
        """Every key in REAGENT_PROFILES must surface under at least one
        bucket. This is the load-bearing audit gate."""
        surfaced: set[str] = set()
        for bucket in _BUCKET_TO_MODES:
            surfaced.update(_reagent_options_for_bucket(bucket).values())

        missing = set(REAGENT_PROFILES.keys()) - surfaced
        assert not missing, (
            f"These REAGENT_PROFILES keys do not appear in any M2 "
            f"dropdown bucket — UI audit regression: {sorted(missing)}"
        )

    def test_no_phantom_reagents_surfaced(self) -> None:
        """Every key surfaced must exist in REAGENT_PROFILES."""
        for bucket in _BUCKET_TO_MODES:
            for label, key in _reagent_options_for_bucket(bucket).items():
                assert key in REAGENT_PROFILES, (
                    f"Bucket {bucket!r} surfaces reagent_key={key!r} "
                    f"(label={label!r}) which is not in REAGENT_PROFILES"
                )

    def test_each_bucket_non_empty(self) -> None:
        """Every declared bucket must surface at least one reagent."""
        for bucket in _BUCKET_TO_MODES:
            options = _reagent_options_for_bucket(bucket)
            assert options, (
                f"Bucket {bucket!r} surfaces zero reagents — either drop "
                f"the bucket or ship a REAGENT_PROFILES entry for one of "
                f"its modes ({_BUCKET_TO_MODES[bucket]})."
            )


class TestLabelGeneration:
    def test_every_label_non_empty_and_unique_within_bucket(self) -> None:
        for bucket in _BUCKET_TO_MODES:
            options = _reagent_options_for_bucket(bucket)
            assert all(label.strip() for label in options), (
                f"Bucket {bucket!r} has an empty-string label"
            )
            # Labels unique within bucket (Streamlit selectbox uses label
            # as the option identifier)
            assert len(set(options.keys())) == len(options), (
                f"Bucket {bucket!r} has duplicate labels"
            )

    def test_labels_alphabetically_sorted_within_bucket(self) -> None:
        """Predictable order: alphabetical by label (case-insensitive)."""
        for bucket in _BUCKET_TO_MODES:
            options = _reagent_options_for_bucket(bucket)
            labels = list(options.keys())
            assert labels == sorted(labels, key=lambda s: s.lower()), (
                f"Bucket {bucket!r} dropdown is not alphabetically "
                f"sorted; got {labels}"
            )


class TestPreviouslyMissingReagentsNowSurface:
    """Spot-checks for the v9.2/v9.3/v9.4 reagents that the audit found
    to be invisible. Each must now appear under exactly one bucket."""

    @pytest.mark.parametrize("reagent_key,expected_bucket", [
        ("cuaac_click_coupling", "Click Chemistry"),
        ("spaac_click_coupling", "Click Chemistry"),
        ("cibacron_blue_f3ga_coupling", "Dye Pseudo-Affinity"),
        ("procion_red_he3b_coupling", "Dye Pseudo-Affinity"),
        ("mep_hcic_coupling", "Mixed-Mode HCIC"),
        ("thiophilic_2me_coupling", "Thiophilic"),
        ("apba_boronate_coupling", "Boronate"),
        ("peptide_affinity_hwrgwv", "Peptide Affinity"),
        ("oligonucleotide_dna_coupling", "Oligonucleotide"),
        ("amylose_mbp_affinity", "Material-as-Ligand"),
        ("chitin_cbd_intein", "Material-as-Ligand"),
        # v9.x crosslinkers folded into existing Secondary Crosslinking bucket
        ("alcl3_trivalent_gelant", "Secondary Crosslinking"),
        ("borax_reversible_crosslinking", "Secondary Crosslinking"),
        ("glyoxal_dialdehyde", "Secondary Crosslinking"),
        ("hrp_h2o2_tyramine", "Secondary Crosslinking"),
        ("bis_epoxide_crosslinking", "Secondary Crosslinking"),
        # v0.5.0: "Hydroxyl Activation" renamed to "ACS Conversion"; the
        # bucket now absorbs both the legacy "activator" mode (ECH/DVS,
        # EDC/NHS) and the new "acs_converter" mode (CNBr/CDI/Tresyl/
        # Cyanuric/Glyoxyl/Periodate). Pyridyl-disulfide moves to
        # "Arm-distal Activation" (it is an arm-distal activator, not a
        # matrix-side ACS converter).
        ("cnbr_activation", "ACS Conversion"),
        ("cdi_activation", "ACS Conversion"),
        ("edc_nhs_activation", "ACS Conversion"),
        ("periodate_oxidation", "ACS Conversion"),
        ("tresyl_chloride_activation", "ACS Conversion"),
        ("cyanuric_chloride_activation", "ACS Conversion"),
        ("glyoxyl_chained_activation", "ACS Conversion"),
        ("pyridyl_disulfide_activation", "Arm-distal Activation"),
        # v9.x affinity ligands folded into existing Protein Coupling bucket
        ("calmodulin_cbp_tap_coupling", "Protein Coupling"),
        ("jacalin_coupling", "Protein Coupling"),
        ("lentil_lectin_coupling", "Protein Coupling"),
        ("p_aminobenzamidine_coupling", "Protein Coupling"),
        ("protein_a_hydrazide_coupling", "Protein Coupling"),
        ("protein_a_nhs_coupling", "Protein Coupling"),
        ("protein_a_vs_coupling", "Protein Coupling"),
        # HIC: hexyl was missing
        ("hexyl_coupling", "Ligand Coupling"),
        # Spacers (8 missing)
        ("adh_hydrazone", "Spacer Arm"),
        ("aha_carboxyl_spacer_arm", "Spacer Arm"),
        ("aminooxy_peg_linker", "Spacer Arm"),
        ("cystamine_disulfide_spacer", "Spacer Arm"),
        ("hydrazide_spacer_arm", "Spacer Arm"),
        ("oligoglycine_spacer", "Spacer Arm"),
        ("peg600_spacer", "Spacer Arm"),
        ("succinic_anhydride_carboxylation", "Spacer Arm"),
        # Metal charging variants
        ("nickel_charging_ida", "Metal Charging"),
        ("nickel_charging_nta", "Metal Charging"),
        # Washing
        ("triazine_dye_leakage_advisory", "Washing"),
    ])
    def test_reagent_surfaces_under_expected_bucket(
        self, reagent_key: str, expected_bucket: str,
    ) -> None:
        options = _reagent_options_for_bucket(expected_bucket)
        assert reagent_key in options.values(), (
            f"Reagent {reagent_key!r} (previously invisible per v0.3.3 "
            f"audit) should surface under bucket {expected_bucket!r}; "
            f"found values: {sorted(options.values())}"
        )


class TestCoverageMetric:
    """Sanity-check that the audit-flagged 44/94 gap is closed."""

    def test_total_unique_surfaced_equals_reagent_profile_count(self) -> None:
        surfaced: set[str] = set()
        for bucket in _BUCKET_TO_MODES:
            surfaced.update(_reagent_options_for_bucket(bucket).values())
        # Must surface every reagent (no exclusion list in v0.3.4)
        assert len(surfaced) == len(REAGENT_PROFILES), (
            f"Surfaced {len(surfaced)} of {len(REAGENT_PROFILES)} "
            f"reagents; gap = {len(REAGENT_PROFILES) - len(surfaced)}"
        )
