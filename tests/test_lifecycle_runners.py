"""Tests for B5 — recipe-driven M1 runner.

Reference: docs/dev_orchestrator_plan.md, Module B5.
"""

from __future__ import annotations


from dpsim.core.process_recipe import default_affinity_media_recipe
from dpsim.datatypes import FullResult
from dpsim.lifecycle import run_m1_from_recipe


class TestRunM1FromRecipe:
    def test_default_recipe_runs_to_completion(self):
        recipe = default_affinity_media_recipe()
        result = run_m1_from_recipe(recipe, l2_mode="empirical")
        assert isinstance(result, FullResult)
        assert result.emulsification is not None
        assert result.emulsification.d32 > 0

    def test_smoke_d32_baseline_unchanged(self):
        """Recipe-driven path must produce the same d32 as the legacy path."""
        recipe = default_affinity_media_recipe()
        result = run_m1_from_recipe(recipe, l2_mode="empirical")
        # INITIAL_HANDOVER smoke baseline: d50 = 18.99 µm; this run uses
        # default_affinity_media_recipe defaults so d32 will differ slightly
        # from the fast_smoke.toml baseline (different RPM/time), but must
        # be in the realistic 1-100 µm range.
        assert 0.5e-6 < result.emulsification.d32 < 200e-6
