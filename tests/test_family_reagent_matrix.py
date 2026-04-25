"""Tests for B1 — family × reagent compatibility matrix + G4 guardrail.

Reference: docs/handover/V0_2_0_PERFORMANCE_RECIPE_HANDOVER.md §9.
"""

from __future__ import annotations


from dpsim.core.process_recipe import (
    LifecycleStage,
    default_affinity_media_recipe,
)
from dpsim.core.recipe_validation import validate_recipe_first_principles
from dpsim.core.validation import ValidationSeverity
from dpsim.datatypes import PolymerFamily
from dpsim.module2_functionalization.family_reagent_matrix import (
    FAMILY_REAGENT_MATRIX,
    check_family_reagent_compatibility,
)


def _codes(report) -> list[str]:
    return [issue.code for issue in report.issues]


# ─── Matrix structure ────────────────────────────────────────────────────────


class TestMatrixStructure:
    def test_matrix_nonempty(self):
        assert len(FAMILY_REAGENT_MATRIX) > 0

    def test_each_canonical_reagent_covers_all_4_families(self):
        canonical_reagents = {
            "ech_activation",
            "dvs_activation",
            "edc_nhs_activation",
            "genipin_secondary",
            "stmp_secondary",
            "glutaraldehyde_secondary",
        }
        all_families = set(PolymerFamily)
        by_reagent: dict[str, set[PolymerFamily]] = {}
        for entry in FAMILY_REAGENT_MATRIX:
            by_reagent.setdefault(entry.reagent_key, set()).add(entry.polymer_family)
        for reagent in canonical_reagents:
            covered = by_reagent.get(reagent, set())
            missing = all_families - covered
            assert not missing, (
                f"reagent {reagent!r} missing matrix entries for {missing}"
            )

    def test_no_duplicate_keys(self):
        seen: set[tuple[PolymerFamily, str]] = set()
        for entry in FAMILY_REAGENT_MATRIX:
            key = (entry.polymer_family, entry.reagent_key)
            assert key not in seen, f"duplicate matrix entry for {key}"
            seen.add(key)


# ─── check_family_reagent_compatibility ──────────────────────────────────────


class TestCheckCompatibility:
    def test_a_c_plus_ech_is_compatible(self):
        entry = check_family_reagent_compatibility(
            PolymerFamily.AGAROSE_CHITOSAN, "ech_activation"
        )
        assert entry is not None
        assert entry.compatibility == "compatible"

    def test_alginate_plus_ech_is_incompatible(self):
        entry = check_family_reagent_compatibility(
            PolymerFamily.ALGINATE, "ech_activation"
        )
        assert entry is not None
        assert entry.compatibility == "incompatible"

    def test_cellulose_plus_edc_is_qualitative(self):
        entry = check_family_reagent_compatibility(
            PolymerFamily.CELLULOSE, "edc_nhs_activation"
        )
        assert entry is not None
        assert entry.compatibility == "qualitative_only"

    def test_unknown_reagent_returns_none(self):
        entry = check_family_reagent_compatibility(
            PolymerFamily.AGAROSE_CHITOSAN, "this_reagent_does_not_exist"
        )
        assert entry is None

    def test_reagent_key_normalised_lowercase_strip(self):
        entry = check_family_reagent_compatibility(
            PolymerFamily.AGAROSE_CHITOSAN, "  ECH_ACTIVATION  "
        )
        assert entry is not None
        assert entry.compatibility == "compatible"


# ─── G4 integration via validate_recipe_first_principles ─────────────────────


class TestG4Integration:
    def test_default_recipe_passes_g4(self):
        # Default recipe is A+C with ECH activation — compatible.
        recipe = default_affinity_media_recipe()
        report = validate_recipe_first_principles(recipe)
        codes = _codes(report)
        assert "FP_G4_FAMILY_REAGENT_INCOMPATIBLE" not in codes

    def test_alginate_with_ech_blocks(self):
        recipe = default_affinity_media_recipe()
        recipe.material_batch.polymer_family = "alginate"
        report = validate_recipe_first_principles(recipe)
        codes = _codes(report)
        assert "FP_G4_FAMILY_REAGENT_INCOMPATIBLE" in codes
        blockers = [
            i for i in report.issues
            if i.code == "FP_G4_FAMILY_REAGENT_INCOMPATIBLE"
            and i.severity == ValidationSeverity.BLOCKER
        ]
        assert blockers
        assert "alginate" in blockers[0].message.lower()

    def test_cellulose_with_edc_warns(self):
        # Build a recipe with cellulose family and EDC/NHS activation.
        recipe = default_affinity_media_recipe()
        recipe.material_batch.polymer_family = "cellulose"
        # Replace the ECH step with EDC/NHS for the test
        for step in recipe.steps_for_stage(LifecycleStage.M2_FUNCTIONALIZATION):
            if step.parameters.get("reagent_key") == "ech_activation":
                step.parameters["reagent_key"] = "edc_nhs_activation"
                break
        report = validate_recipe_first_principles(recipe)
        codes = _codes(report)
        assert "FP_G4_FAMILY_REAGENT_QUALITATIVE" in codes

    def test_unknown_polymer_family_skips(self):
        recipe = default_affinity_media_recipe()
        recipe.material_batch.polymer_family = "polyethylene_glycol"  # not in enum
        report = validate_recipe_first_principles(recipe)
        codes = _codes(report)
        assert "FP_G4_FAMILY_REAGENT_INCOMPATIBLE" not in codes
        assert "FP_G4_FAMILY_REAGENT_QUALITATIVE" not in codes

    def test_empty_polymer_family_skips(self):
        recipe = default_affinity_media_recipe()
        recipe.material_batch.polymer_family = ""
        report = validate_recipe_first_principles(recipe)
        codes = _codes(report)
        assert "FP_G4_FAMILY_REAGENT_INCOMPATIBLE" not in codes
