"""Tests for B4 — polymer concentrations promoted into ProcessRecipe.

Reference: docs/dev_orchestrator_plan.md, Module B4.
"""

from __future__ import annotations

import pytest

from dpsim.core.process_recipe import (
    LifecycleStage,
    ProcessStepKind,
    default_affinity_media_recipe,
)
from dpsim.core.quantities import Quantity
from dpsim.lifecycle.recipe_resolver import resolve_lifecycle_inputs


def _prepare_step(recipe):
    return next(
        s
        for s in recipe.steps_for_stage(LifecycleStage.M1_FABRICATION)
        if s.kind == ProcessStepKind.PREPARE_PHASE
    )


class TestPolymerConcentrationsInRecipe:
    def test_default_recipe_has_concentrations(self):
        recipe = default_affinity_media_recipe()
        prepare = _prepare_step(recipe)
        assert "c_agarose" in prepare.parameters
        assert "c_chitosan" in prepare.parameters
        assert "c_genipin" in prepare.parameters

    def test_default_concentrations_match_legacy(self):
        recipe = default_affinity_media_recipe()
        prepare = _prepare_step(recipe)
        assert float(prepare.parameters["c_agarose"].value) == pytest.approx(42.0)
        assert float(prepare.parameters["c_chitosan"].value) == pytest.approx(18.0)
        assert float(prepare.parameters["c_genipin"].value) == pytest.approx(2.0)

    def test_resolver_applies_recipe_concentrations(self):
        recipe = default_affinity_media_recipe()
        prepare = _prepare_step(recipe)
        prepare.parameters["c_agarose"] = Quantity(35.0, "kg/m3", source="user_recipe")
        prepare.parameters["c_chitosan"] = Quantity(20.0, "kg/m3", source="user_recipe")
        prepare.parameters["c_genipin"] = Quantity(3.5, "mol/m3", source="user_recipe")
        resolved = resolve_lifecycle_inputs(recipe)
        assert resolved.parameters.formulation.c_agarose == pytest.approx(35.0)
        assert resolved.parameters.formulation.c_chitosan == pytest.approx(20.0)
        assert resolved.parameters.formulation.c_genipin == pytest.approx(3.5)

    def test_resolver_falls_back_when_concentrations_missing(self):
        recipe = default_affinity_media_recipe()
        prepare = _prepare_step(recipe)
        # Strip the concentrations from the recipe (simulate older saved recipe).
        for key in ("c_agarose", "c_chitosan", "c_genipin"):
            prepare.parameters.pop(key, None)
        resolved = resolve_lifecycle_inputs(recipe)
        # Should still produce reasonable defaults from SimulationParameters.
        assert resolved.parameters.formulation.c_agarose > 0
        assert resolved.parameters.formulation.c_chitosan > 0
        assert resolved.parameters.formulation.c_genipin > 0

    def test_resolver_smoke_with_default_recipe_unchanged(self):
        """Legacy smoke baseline values must round-trip through the recipe."""
        recipe = default_affinity_media_recipe()
        resolved = resolve_lifecycle_inputs(recipe)
        # Defaults from default_affinity_media_recipe must match legacy
        # SimulationParameters defaults so smoke is bit-identical.
        assert resolved.parameters.formulation.c_agarose == pytest.approx(42.0)
        assert resolved.parameters.formulation.c_chitosan == pytest.approx(18.0)
        assert resolved.parameters.formulation.c_genipin == pytest.approx(2.0)
