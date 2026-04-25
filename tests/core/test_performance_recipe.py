"""Tests for PerformanceRecipe — the typed M3 method primitive.

Reference: docs/performance_recipe_protocol.md, Module M1 (A1).
Test IDs M1-T01 .. M1-T04 mirror the protocol's test plan.
"""

from __future__ import annotations

import dataclasses

import pytest

from dpsim.core.performance_recipe import (
    DSDPolicy,
    performance_recipe_from_resolved,
)
from dpsim.core.process_recipe import (
    LifecycleStage,
    ProcessRecipe,
    default_affinity_media_recipe,
)
from dpsim.lifecycle.recipe_resolver import resolve_lifecycle_inputs
from dpsim.module3_performance.method import ChromatographyOperation


def _resolve_default():
    """Resolve the default affinity-media recipe end-to-end."""
    recipe = default_affinity_media_recipe()
    return resolve_lifecycle_inputs(recipe)


# ─── M1-T01 — round-trip from default_affinity_media_recipe ──────────────────


class TestPerformanceRecipeFromDefault:
    """Default recipe round-trips into a populated PerformanceRecipe."""

    def test_column_bed_height_default(self):
        perf = performance_recipe_from_resolved(_resolve_default())
        assert perf.column.bed_height == pytest.approx(0.10, rel=1e-6)

    def test_column_diameter_default(self):
        perf = performance_recipe_from_resolved(_resolve_default())
        assert perf.column.diameter == pytest.approx(0.01, rel=1e-6)

    def test_method_step_count(self):
        perf = performance_recipe_from_resolved(_resolve_default())
        # default recipe defines pack, equilibrate, load, wash, elute
        assert len(perf.method_steps) == 5

    def test_method_step_order(self):
        perf = performance_recipe_from_resolved(_resolve_default())
        ops = [s.operation for s in perf.method_steps]
        assert ops == [
            ChromatographyOperation.PACK,
            ChromatographyOperation.EQUILIBRATE,
            ChromatographyOperation.LOAD,
            ChromatographyOperation.WASH,
            ChromatographyOperation.ELUTE,
        ]

    def test_has_gradient_elute_true_on_default(self):
        # default elute step sets gradient_field="ph"
        perf = performance_recipe_from_resolved(_resolve_default())
        assert perf.has_gradient_elute() is True

    def test_load_step_returns_load(self):
        perf = performance_recipe_from_resolved(_resolve_default())
        load = perf.load_step()
        assert load is not None
        assert load.operation == ChromatographyOperation.LOAD

    def test_elute_step_returns_elute(self):
        perf = performance_recipe_from_resolved(_resolve_default())
        elute = perf.elute_step()
        assert elute is not None
        assert elute.operation == ChromatographyOperation.ELUTE

    def test_pack_step_returns_pack(self):
        perf = performance_recipe_from_resolved(_resolve_default())
        pack = perf.pack_step()
        assert pack is not None
        assert pack.operation == ChromatographyOperation.PACK

    def test_feed_carried_from_recipe(self):
        perf = performance_recipe_from_resolved(_resolve_default())
        assert perf.feed_concentration_mol_m3 > 0
        assert perf.feed_duration_s > 0
        assert perf.total_time_s >= perf.feed_duration_s

    def test_operability_gates_carried_from_recipe(self):
        perf = performance_recipe_from_resolved(_resolve_default())
        assert perf.max_pressure_drop_Pa > 0
        assert perf.pump_pressure_limit_Pa > 0

    def test_n_z_inherits_resolver_default(self):
        # recipe_resolver sets m3_n_z=30
        perf = performance_recipe_from_resolved(_resolve_default())
        assert perf.n_z == 30


# ─── M1-T02 — empty M3 stage / missing PACK or LOAD ──────────────────────────


class TestPerformanceRecipeBuilderErrors:
    """Builder rejects degenerate resolved states."""

    def test_empty_recipe_raises_value_error(self):
        recipe = ProcessRecipe()
        # resolve_lifecycle_inputs adds a BLOCKER to the validation report when
        # the M3 stage is empty; resolution itself does not raise. The clean-
        # slate primitive escalates to a hard ValueError.
        resolved = resolve_lifecycle_inputs(recipe)
        with pytest.raises(ValueError, match=r"PACK|LOAD"):
            performance_recipe_from_resolved(resolved)

    def test_missing_load_step_raises(self):
        # Build a recipe that has every M3 step except LOAD.
        recipe = default_affinity_media_recipe()
        recipe.steps = [
            step
            for step in recipe.steps
            if not (
                step.stage == LifecycleStage.M3_PERFORMANCE
                and step.kind.value == "load"
            )
        ]
        resolved = resolve_lifecycle_inputs(recipe)
        with pytest.raises(ValueError, match="LOAD"):
            performance_recipe_from_resolved(resolved)

    def test_missing_pack_step_raises(self):
        recipe = default_affinity_media_recipe()
        recipe.steps = [
            step
            for step in recipe.steps
            if not (
                step.stage == LifecycleStage.M3_PERFORMANCE
                and step.kind.value == "pack_column"
            )
        ]
        resolved = resolve_lifecycle_inputs(recipe)
        with pytest.raises(ValueError, match="PACK"):
            performance_recipe_from_resolved(resolved)


# ─── M1-T03 — has_gradient_elute correctly detects absence of gradient_field ─


class TestHasGradientEluteFalse:
    """has_gradient_elute is False when elute step has no gradient_field."""

    def test_no_gradient_field_returns_false(self):
        recipe = default_affinity_media_recipe()
        # Strip gradient_field on the elute step.
        for step in recipe.steps_for_stage(LifecycleStage.M3_PERFORMANCE):
            if "gradient_field" in step.parameters:
                step.parameters.pop("gradient_field", None)
        resolved = resolve_lifecycle_inputs(recipe)
        perf = performance_recipe_from_resolved(resolved)
        assert perf.has_gradient_elute() is False

    def test_blank_gradient_field_returns_false(self):
        recipe = default_affinity_media_recipe()
        for step in recipe.steps_for_stage(LifecycleStage.M3_PERFORMANCE):
            if "gradient_field" in step.parameters:
                step.parameters["gradient_field"] = "   "
        resolved = resolve_lifecycle_inputs(recipe)
        perf = performance_recipe_from_resolved(resolved)
        assert perf.has_gradient_elute() is False


# ─── M1-T04 — DSDPolicy round-trip ───────────────────────────────────────────


class TestDSDPolicyRoundTrip:
    """Custom DSDPolicy is preserved end-to-end through the builder."""

    def test_default_policy_values(self):
        policy = DSDPolicy()
        assert policy.quantiles == (0.10, 0.50, 0.90)
        assert policy.run_full_method is False
        assert policy.fast_pressure_screen is True
        assert policy.n_jobs == 1

    def test_custom_policy_is_preserved(self):
        custom = DSDPolicy(
            quantiles=(0.05, 0.25, 0.50, 0.75, 0.95),
            run_full_method=True,
            fast_pressure_screen=False,
            n_jobs=4,
        )
        perf = performance_recipe_from_resolved(
            _resolve_default(), dsd_policy=custom
        )
        assert perf.dsd_policy is custom
        assert perf.dsd_policy.quantiles == (0.05, 0.25, 0.50, 0.75, 0.95)
        assert perf.dsd_policy.run_full_method is True
        assert perf.dsd_policy.fast_pressure_screen is False
        assert perf.dsd_policy.n_jobs == 4

    def test_dsd_policy_is_frozen(self):
        policy = DSDPolicy()
        with pytest.raises(dataclasses.FrozenInstanceError):
            policy.run_full_method = True  # type: ignore[misc]

    def test_none_policy_yields_default(self):
        perf = performance_recipe_from_resolved(
            _resolve_default(), dsd_policy=None
        )
        assert perf.dsd_policy == DSDPolicy()
