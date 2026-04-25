"""Tests for first-principles recipe validation guardrails.

Reference: docs/performance_recipe_protocol.md, Module M3 (A3).
Three guardrails covered: G1 (M1 wash mass-balance closure), G3 (gradient_field
↔ isotherm consistency), G5 (FMC ligand-accessibility ratio).
"""

from __future__ import annotations

from dataclasses import dataclass


from dpsim.core.process_recipe import (
    LifecycleStage,
    ProcessStepKind,
    default_affinity_media_recipe,
)
from dpsim.core.quantities import Quantity
from dpsim.core.recipe_validation import validate_recipe_first_principles
from dpsim.core.validation import ValidationSeverity


def _codes(report) -> list[str]:
    return [issue.code for issue in report.issues]


def _severities_for(report, code: str) -> list[ValidationSeverity]:
    return [issue.severity for issue in report.issues if issue.code == code]


# ─── G1 — wash mass-balance closure ──────────────────────────────────────────


class TestG1WashMassBalance:
    def test_default_recipe_passes_g1(self):
        """Default recipe: 0.10 × (1 − 0.80/1.0)^3 = 0.0008 ≤ 0.01 target."""
        recipe = default_affinity_media_recipe()
        report = validate_recipe_first_principles(recipe)
        assert "FP_G1_WASH_INADEQUATE" not in _codes(report)
        assert "FP_G1_WASH_MARGINAL" not in _codes(report)

    def test_zero_mixing_efficiency_blocks(self):
        """Mixing efficiency = 0 means the wash does nothing → residual = initial."""
        recipe = default_affinity_media_recipe()
        cool_step = next(
            s
            for s in recipe.steps_for_stage(LifecycleStage.M1_FABRICATION)
            if s.kind == ProcessStepKind.COOL_OR_GEL
        )
        cool_step.parameters["wash_mixing_efficiency"] = Quantity(0.0, "fraction", source="test")
        report = validate_recipe_first_principles(recipe)
        # initial=0.10, target=0.01: residual=0.10, ratio=10× → BLOCKER
        assert "FP_G1_WASH_INADEQUATE" in _codes(report)
        assert ValidationSeverity.BLOCKER in _severities_for(report, "FP_G1_WASH_INADEQUATE")

    def test_marginal_residual_warns(self):
        """Residual modestly above target → WARNING, not BLOCKER."""
        recipe = default_affinity_media_recipe()
        cool_step = next(
            s
            for s in recipe.steps_for_stage(LifecycleStage.M1_FABRICATION)
            if s.kind == ProcessStepKind.COOL_OR_GEL
        )
        # Force residual ≈ 2× target: 1 cycle, 0.5 mixing, init=0.04, target=0.01
        cool_step.parameters["initial_oil_carryover_fraction"] = Quantity(0.04, "fraction", source="test")
        cool_step.parameters["wash_cycles"] = Quantity(1.0, "1", source="test")
        cool_step.parameters["wash_mixing_efficiency"] = Quantity(0.5, "fraction", source="test")
        cool_step.parameters["oil_retention_factor"] = Quantity(1.0, "1", source="test")
        report = validate_recipe_first_principles(recipe)
        assert "FP_G1_WASH_MARGINAL" in _codes(report)
        assert ValidationSeverity.WARNING in _severities_for(report, "FP_G1_WASH_MARGINAL")

    def test_no_cool_step_skips(self):
        recipe = default_affinity_media_recipe()
        recipe.steps = [
            s for s in recipe.steps if s.kind != ProcessStepKind.COOL_OR_GEL
        ]
        report = validate_recipe_first_principles(recipe)
        assert "FP_G1_WASH_INADEQUATE" not in _codes(report)
        assert "FP_G1_WASH_MARGINAL" not in _codes(report)


# ─── G3 — gradient_field/isotherm consistency ────────────────────────────────


@dataclass
class _MockIsothermPH:
    @property
    def gradient_sensitive(self) -> bool:
        return True

    @property
    def gradient_field(self) -> str:
        return "ph"


@dataclass
class _MockIsothermSalt:
    @property
    def gradient_sensitive(self) -> bool:
        return True

    @property
    def gradient_field(self) -> str:
        return "salt_concentration"


@dataclass
class _MockIsothermNonSensitive:
    @property
    def gradient_sensitive(self) -> bool:
        return False

    @property
    def gradient_field(self) -> str:
        return ""


class TestG3GradientFieldConsistency:
    def test_pH_gradient_with_pH_isotherm_passes(self):
        recipe = default_affinity_media_recipe()
        report = validate_recipe_first_principles(recipe, isotherm=_MockIsothermPH())
        assert all(not c.startswith("FP_G3_") for c in _codes(report))

    def test_pH_gradient_with_salt_isotherm_blocks(self):
        recipe = default_affinity_media_recipe()
        report = validate_recipe_first_principles(recipe, isotherm=_MockIsothermSalt())
        assert "FP_G3_GRADIENT_FIELD_MISMATCH" in _codes(report)
        assert ValidationSeverity.BLOCKER in _severities_for(
            report, "FP_G3_GRADIENT_FIELD_MISMATCH"
        )

    def test_pH_gradient_with_non_sensitive_isotherm_blocks(self):
        recipe = default_affinity_media_recipe()
        report = validate_recipe_first_principles(
            recipe, isotherm=_MockIsothermNonSensitive()
        )
        assert "FP_G3_ISOTHERM_NOT_GRADIENT_SENSITIVE" in _codes(report)
        assert ValidationSeverity.BLOCKER in _severities_for(
            report, "FP_G3_ISOTHERM_NOT_GRADIENT_SENSITIVE"
        )

    def test_no_gradient_field_skips(self):
        recipe = default_affinity_media_recipe()
        for s in recipe.steps_for_stage(LifecycleStage.M3_PERFORMANCE):
            s.parameters.pop("gradient_field", None)
        report = validate_recipe_first_principles(recipe, isotherm=_MockIsothermSalt())
        assert all(not c.startswith("FP_G3_") for c in _codes(report))

    def test_gradient_declared_no_isotherm_defers_with_warning(self):
        recipe = default_affinity_media_recipe()
        report = validate_recipe_first_principles(recipe)  # no isotherm
        assert "FP_G3_GRADIENT_FIELD_DEFERRED" in _codes(report)
        assert ValidationSeverity.WARNING in _severities_for(
            report, "FP_G3_GRADIENT_FIELD_DEFERRED"
        )


# ─── G5 — surface-area inheritance ───────────────────────────────────────────


@dataclass
class _MockFMC:
    reagent_accessible_area_per_bed_volume: float = 1000.0
    ligand_accessible_area_per_bed_volume: float = 200.0


class TestG5SurfaceAreaInheritance:
    def test_high_accessibility_passes(self):
        recipe = default_affinity_media_recipe()
        fmc = _MockFMC(
            reagent_accessible_area_per_bed_volume=1000.0,
            ligand_accessible_area_per_bed_volume=500.0,  # 50%
        )
        report = validate_recipe_first_principles(recipe, fmc=fmc)
        assert "FP_G5_LIGAND_ACCESSIBILITY_LOW" not in _codes(report)

    def test_low_accessibility_warns(self):
        recipe = default_affinity_media_recipe()
        fmc = _MockFMC(
            reagent_accessible_area_per_bed_volume=1000.0,
            ligand_accessible_area_per_bed_volume=50.0,  # 5%
        )
        report = validate_recipe_first_principles(recipe, fmc=fmc)
        assert "FP_G5_LIGAND_ACCESSIBILITY_LOW" in _codes(report)
        assert ValidationSeverity.WARNING in _severities_for(
            report, "FP_G5_LIGAND_ACCESSIBILITY_LOW"
        )

    def test_zero_reagent_area_skips(self):
        recipe = default_affinity_media_recipe()
        fmc = _MockFMC(
            reagent_accessible_area_per_bed_volume=0.0,
            ligand_accessible_area_per_bed_volume=0.0,
        )
        report = validate_recipe_first_principles(recipe, fmc=fmc)
        assert "FP_G5_LIGAND_ACCESSIBILITY_LOW" not in _codes(report)

    def test_no_fmc_skips(self):
        recipe = default_affinity_media_recipe()
        report = validate_recipe_first_principles(recipe, fmc=None)
        assert "FP_G5_LIGAND_ACCESSIBILITY_LOW" not in _codes(report)


# ─── Combined ────────────────────────────────────────────────────────────────


class TestValidateRecipeFirstPrinciplesIntegration:
    def test_default_recipe_no_blockers(self):
        recipe = default_affinity_media_recipe()
        report = validate_recipe_first_principles(
            recipe, isotherm=_MockIsothermPH()
        )
        blockers = [
            i for i in report.issues if i.severity == ValidationSeverity.BLOCKER
        ]
        assert blockers == [], (
            f"default recipe should not produce first-principles blockers; got {blockers}"
        )

    def test_returns_validation_report(self):
        recipe = default_affinity_media_recipe()
        report = validate_recipe_first_principles(recipe)
        # ValidationReport has .issues, .blockers, .warnings, .add per existing API
        assert hasattr(report, "issues")
        assert hasattr(report, "add")
