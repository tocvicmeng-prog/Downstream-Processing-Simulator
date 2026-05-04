"""Tests for G7 — pH window guardrail (B-1a / W-002, v0.6.4).

Reference: docs/handover/HANDOVER_tier_0_close_2026-05-04.md §5.

For each M2 functionalization step, G7 reads the reagent profile's
``ph_min_hard`` / ``ph_max_hard`` / ``ph_min_soft`` / ``ph_max_soft`` and
applies the policy:

  * pH outside hard window  → BLOCKER FP_G7_PH_OUT_OF_HARD_WINDOW
  * pH outside soft, in hard → WARNING FP_G7_PH_RATE_DEGRADED
  * pH inside soft           → silent pass

Profiles without curated windows (ph_min_hard is None), unknown
reagent_keys, and steps with no ``pH`` parameter are silent (backward
compatibility with v0.6.3).
"""

from __future__ import annotations

import pytest

from dpsim.core.process_recipe import (
    LifecycleStage,
    ProcessRecipe,
    ProcessStep,
    ProcessStepKind,
    default_affinity_media_recipe,
)
from dpsim.core.quantities import Quantity
from dpsim.core.recipe_validation import validate_recipe_first_principles
from dpsim.core.validation import ValidationSeverity


def _codes(report) -> list[str]:
    return [issue.code for issue in report.issues]


def _g7_codes(report) -> list[str]:
    return [c for c in _codes(report) if c.startswith("FP_G7_")]


def _g7_severities(report) -> list[ValidationSeverity]:
    return [i.severity for i in report.issues if i.code.startswith("FP_G7_")]


def _make_recipe_with_m2_step(reagent_key: str, ph_value: float) -> ProcessRecipe:
    """Recipe with one M2 ACTIVATE step carrying the given reagent + pH.

    Polymer family is left at the default (agarose_chitosan) so G4 does not
    fire. The step is bare otherwise — sufficient for a focused G7 test.
    """
    recipe = ProcessRecipe()
    recipe.steps.append(
        ProcessStep(
            name=f"G7-test step ({reagent_key} @ pH {ph_value})",
            stage=LifecycleStage.M2_FUNCTIONALIZATION,
            kind=ProcessStepKind.ACTIVATE,
            parameters={
                "reagent_key": reagent_key,
                "pH": Quantity(ph_value, "1", source="test"),
            },
        )
    )
    return recipe


# Per-class test triples: (reagent_key, in_soft_pH, in_hard_outside_soft_pH,
#                          out_of_hard_pH).
#
# All values are chosen to land squarely inside the corresponding band so
# the test does not race a future window-tightening edit by < 0.05 pH.
PH_CLASS_CASES: list[tuple[str, float, float, float]] = [
    # CNBr: hard (10.5, 12.0), soft (11.0, 11.5)
    ("cnbr_activation", 11.2, 10.7, 9.0),
    # CDI: hard (7.0, 10.0), soft (8.0, 9.0)
    ("cdi_activation", 8.5, 7.5, 6.0),
    # Tresyl: hard (7.0, 10.0), soft (7.5, 9.0)
    ("tresyl_chloride_activation", 8.0, 7.2, 11.0),
    # Epoxide ECH: hard (8.0, 13.0), soft (9.0, 13.0)
    ("ech_activation", 11.0, 8.5, 7.0),
    # NaBH4 reductive amination: hard (5.0, 10.0), soft (7.0, 9.0)
    ("nabh4_quench", 8.0, 6.0, 4.0),
    # Boronate: hard (6.0, 10.0), soft (7.0, 9.0)
    ("apba_boronate_coupling", 8.0, 6.5, 5.0),
    # IMAC Ni-NTA charging: hard (4.0, 9.0), soft (7.0, 8.0)
    ("nickel_charging", 7.5, 5.0, 10.0),
    # Protein A: hard (7.0, 10.0), soft (8.5, 9.5)
    ("protein_a_coupling", 9.0, 7.5, 6.0),
    # Borax: hard (7.0, 11.0), soft (8.5, 9.5)
    ("borax_reversible_crosslinking", 9.0, 7.5, 6.0),
    # Glutaraldehyde secondary: hard (5.0, 10.0), soft (7.0, 8.0)
    ("glutaraldehyde_secondary", 7.5, 9.5, 11.0),
]


# ─── Per-class window enforcement ────────────────────────────────────────────


class TestG7PerClassWindows:
    """One in-optimum, one rate-degraded, one out-of-hard per reagent class.

    Covers the 10 chemistries listed in handover §5: CNBr, CDI, tresyl,
    epoxide, aldehyde+reductive amination (via NaBH4), boronate, IMAC,
    Protein A/EDC, borax, glutaraldehyde.
    """

    @pytest.mark.parametrize("reagent_key,ph,_warn,_block", PH_CLASS_CASES)
    def test_in_optimum_silent_pass(self, reagent_key, ph, _warn, _block):
        recipe = _make_recipe_with_m2_step(reagent_key, ph)
        report = validate_recipe_first_principles(recipe)
        assert _g7_codes(report) == [], (
            f"{reagent_key} @ pH {ph} should be in soft window; got {_g7_codes(report)}"
        )

    @pytest.mark.parametrize("reagent_key,_pass,ph,_block", PH_CLASS_CASES)
    def test_outside_soft_inside_hard_warns(self, reagent_key, _pass, ph, _block):
        recipe = _make_recipe_with_m2_step(reagent_key, ph)
        report = validate_recipe_first_principles(recipe)
        assert "FP_G7_PH_RATE_DEGRADED" in _g7_codes(report), (
            f"{reagent_key} @ pH {ph} should warn (in hard, outside soft); "
            f"got {_g7_codes(report)}"
        )
        assert ValidationSeverity.WARNING in _g7_severities(report)
        assert "FP_G7_PH_OUT_OF_HARD_WINDOW" not in _g7_codes(report)

    @pytest.mark.parametrize("reagent_key,_pass,_warn,ph", PH_CLASS_CASES)
    def test_outside_hard_blocks(self, reagent_key, _pass, _warn, ph):
        recipe = _make_recipe_with_m2_step(reagent_key, ph)
        report = validate_recipe_first_principles(recipe)
        assert "FP_G7_PH_OUT_OF_HARD_WINDOW" in _g7_codes(report), (
            f"{reagent_key} @ pH {ph} should block (outside hard); "
            f"got {_g7_codes(report)}"
        )
        assert ValidationSeverity.BLOCKER in _g7_severities(report)
        # Outside-hard suppresses the rate-degraded warning per the policy
        # (one diagnosis per step; the BLOCKER subsumes the WARNING).
        assert "FP_G7_PH_RATE_DEGRADED" not in _g7_codes(report)


# ─── Backward-compatibility silent-skip cases ────────────────────────────────


class TestG7BackwardCompatSkips:
    """G7 must not fire on cases the v0.6.3 baseline accepted silently."""

    def test_default_recipe_has_no_g7_issues(self):
        """Default affinity-media recipe was certified clean at v0.6.3.

        With G7 active, ECH at pH 12 falls in the soft band (9-13),
        Protein A at pH 9 falls in the soft band (8.5-9.5), and
        ethanolamine quench at pH 8.5 falls in the soft band (8.0-9.5).
        No G7 issues should be raised.
        """
        recipe = default_affinity_media_recipe()
        report = validate_recipe_first_principles(recipe)
        assert _g7_codes(report) == []
        # Stronger guarantee: no NEW BLOCKER on the default recipe (the
        # release-gate-critical assertion).
        assert report.ok_for_decision

    def test_unknown_reagent_key_silent_skip(self):
        """A reagent_key not in REAGENT_PROFILES is silently ignored."""
        recipe = _make_recipe_with_m2_step("nonexistent_reagent_xyz", 1.5)
        report = validate_recipe_first_principles(recipe)
        assert _g7_codes(report) == []

    def test_uncurated_profile_silent_skip(self):
        """Profiles with no pH windows declared (e.g. wash_buffer) skip silently."""
        # wash_buffer is in REAGENT_PROFILES but is informational; ph_*_hard
        # are None. Even an absurd pH must not raise G7.
        recipe = _make_recipe_with_m2_step("wash_buffer", 0.5)
        report = validate_recipe_first_principles(recipe)
        assert _g7_codes(report) == []

    def test_step_without_pH_silent_skip(self):
        """A step missing the ``pH`` parameter is silently skipped."""
        recipe = ProcessRecipe()
        recipe.steps.append(
            ProcessStep(
                name="No-pH activation step",
                stage=LifecycleStage.M2_FUNCTIONALIZATION,
                kind=ProcessStepKind.ACTIVATE,
                parameters={"reagent_key": "cnbr_activation"},  # no "pH"
            )
        )
        report = validate_recipe_first_principles(recipe)
        assert _g7_codes(report) == []

    def test_step_without_reagent_key_silent_skip(self):
        """A step with empty ``reagent_key`` is silently skipped."""
        recipe = ProcessRecipe()
        recipe.steps.append(
            ProcessStep(
                name="Bare wash step (no reagent_key)",
                stage=LifecycleStage.M2_FUNCTIONALIZATION,
                kind=ProcessStepKind.WASH,
                parameters={"pH": Quantity(7.4, "1", source="test")},
            )
        )
        report = validate_recipe_first_principles(recipe)
        assert _g7_codes(report) == []


# ─── Two-step / multi-phase coverage ─────────────────────────────────────────


class TestG7MultiPhase:
    """Recipes with multiple M2 steps must check each phase independently."""

    def test_two_step_recipe_both_phases_checked(self):
        """Aldehyde-formation step in-optimum + reductive-amination step
        out-of-hard → only the bad phase produces a BLOCKER.

        Uses ECH activation (in soft band 9-13, pH 11) followed by NaBH4
        quench at pH 4 (below hard min 5.0). Verifies that G7 does not
        short-circuit on the first step's success.
        """
        recipe = ProcessRecipe()
        recipe.steps.extend([
            ProcessStep(
                name="Phase 1: ECH activation (in optimum)",
                stage=LifecycleStage.M2_FUNCTIONALIZATION,
                kind=ProcessStepKind.ACTIVATE,
                parameters={
                    "reagent_key": "ech_activation",
                    "pH": Quantity(11.0, "1", source="test"),
                },
            ),
            ProcessStep(
                name="Phase 2: NaBH4 reductive amination (out of hard)",
                stage=LifecycleStage.M2_FUNCTIONALIZATION,
                kind=ProcessStepKind.QUENCH,
                parameters={
                    "reagent_key": "nabh4_quench",
                    "pH": Quantity(4.0, "1", source="test"),
                },
            ),
        ])
        report = validate_recipe_first_principles(recipe)
        g7_blockers = [
            i for i in report.issues
            if i.code == "FP_G7_PH_OUT_OF_HARD_WINDOW"
        ]
        assert len(g7_blockers) == 1, (
            f"expected one G7 BLOCKER on the NaBH4 phase; got {g7_blockers}"
        )
        # The blocker message must name the offending step so the user
        # can act on it without inspecting the recipe.
        assert "NaBH4" in g7_blockers[0].message

    def test_two_step_recipe_both_in_optimum_silent(self):
        """Two M2 steps both in their soft bands → G7 silent on both."""
        recipe = ProcessRecipe()
        recipe.steps.extend([
            ProcessStep(
                name="ECH activation (pH 11)",
                stage=LifecycleStage.M2_FUNCTIONALIZATION,
                kind=ProcessStepKind.ACTIVATE,
                parameters={
                    "reagent_key": "ech_activation",
                    "pH": Quantity(11.0, "1", source="test"),
                },
            ),
            ProcessStep(
                name="Protein A coupling (pH 9)",
                stage=LifecycleStage.M2_FUNCTIONALIZATION,
                kind=ProcessStepKind.COUPLE_LIGAND,
                parameters={
                    "reagent_key": "protein_a_coupling",
                    "pH": Quantity(9.0, "1", source="test"),
                },
            ),
        ])
        report = validate_recipe_first_principles(recipe)
        assert _g7_codes(report) == []


# ─── Boundary semantics ──────────────────────────────────────────────────────


class TestG7BoundarySemantics:
    """Inclusive vs exclusive boundary behaviour at the window edges."""

    def test_pH_exactly_at_hard_min_passes(self):
        """pH == ph_min_hard is accepted (inclusive boundary).

        cnbr_activation: hard min 10.5. At exactly 10.5, the step must
        not block; it should warn (outside soft 11.0-11.5 but at the
        hard floor).
        """
        recipe = _make_recipe_with_m2_step("cnbr_activation", 10.5)
        report = validate_recipe_first_principles(recipe)
        assert "FP_G7_PH_OUT_OF_HARD_WINDOW" not in _g7_codes(report)
        assert "FP_G7_PH_RATE_DEGRADED" in _g7_codes(report)

    def test_pH_exactly_at_soft_max_passes_silent(self):
        """pH == ph_max_soft is in the optimum band → silent.

        cdi_activation: soft max 9.0. At exactly 9.0, no warning, no
        blocker, no diagnostic.
        """
        recipe = _make_recipe_with_m2_step("cdi_activation", 9.0)
        report = validate_recipe_first_principles(recipe)
        assert _g7_codes(report) == []

    def test_pH_just_above_hard_max_blocks(self):
        """pH slightly above ph_max_hard → BLOCKER.

        cnbr_activation: hard max 12.0. At 12.01 the step must block.
        """
        recipe = _make_recipe_with_m2_step("cnbr_activation", 12.01)
        report = validate_recipe_first_principles(recipe)
        assert "FP_G7_PH_OUT_OF_HARD_WINDOW" in _g7_codes(report)
