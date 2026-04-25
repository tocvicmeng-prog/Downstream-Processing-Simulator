import pytest

from dpsim.core import Quantity
from dpsim.core.process_recipe import ProcessStepKind, default_affinity_media_recipe
from dpsim.datatypes import RunContext, SimulationParameters
from dpsim.calibration import CalibrationEntry, CalibrationStore
from dpsim.config import load_config
from dpsim.level1_emulsification.washing import solve_m1_washing
from dpsim.lifecycle import DownstreamProcessOrchestrator, resolve_lifecycle_inputs
from dpsim.pipeline.orchestrator import PipelineOrchestrator


def test_washing_model_responds_to_wash_intensity():
    weak = SimulationParameters()
    weak.formulation.m1_wash_cycles = 1
    weak.formulation.m1_wash_volume_ratio = 1.0

    strong = SimulationParameters()
    strong.formulation.m1_wash_cycles = 6
    strong.formulation.m1_wash_volume_ratio = 5.0

    weak_result = solve_m1_washing(weak)
    strong_result = solve_m1_washing(strong)

    assert weak_result.validate() == []
    assert strong_result.validate() == []
    assert strong_result.residual_oil_volume_fraction < weak_result.residual_oil_volume_fraction
    assert (
        strong_result.residual_surfactant_concentration_kg_m3
        < weak_result.residual_surfactant_concentration_kg_m3
    )
    assert strong_result.oil_removal_efficiency > weak_result.oil_removal_efficiency


def test_recipe_resolver_routes_m1_washing_parameters():
    recipe = default_affinity_media_recipe()
    wash_step = next(step for step in recipe.steps if step.kind == ProcessStepKind.COOL_OR_GEL)
    wash_step.parameters["wash_cycles"] = Quantity(5.0, "1", source="user_recipe")
    wash_step.parameters["wash_volume_ratio"] = Quantity(4.0, "1", source="user_recipe")
    wash_step.parameters["wash_mixing_efficiency"] = Quantity(0.9, "fraction", source="user_recipe")

    resolved = resolve_lifecycle_inputs(recipe)

    assert resolved.validation.blockers == []
    assert resolved.parameters.formulation.m1_wash_cycles == 5
    assert resolved.parameters.formulation.m1_wash_volume_ratio == pytest.approx(4.0)
    assert resolved.parameters.formulation.m1_wash_mixing_efficiency == pytest.approx(0.9)
    assert "M1.cool_or_gel.wash_cycles" in resolved.resolved_parameters
    assert "M1.cool_or_gel.wash_volume_ratio" in resolved.resolved_parameters


def test_recipe_resolver_blocks_invalid_m1_washing_parameter():
    recipe = default_affinity_media_recipe()
    wash_step = next(step for step in recipe.steps if step.kind == ProcessStepKind.COOL_OR_GEL)
    wash_step.parameters["wash_mixing_efficiency"] = Quantity(1.5, "fraction", source="user_recipe")

    resolved = resolve_lifecycle_inputs(recipe)

    codes = {issue.code for issue in resolved.validation.blockers}
    assert "M1_WASH_MIXING" in codes


def test_m1_washing_calibration_applies_to_pipeline_params(tmp_path):
    params = load_config("configs/fast_smoke.toml")
    store = CalibrationStore()
    store.add(CalibrationEntry(
        profile_key="m1_washing",
        parameter_name="m1_oil_retention_factor",
        measured_value=4.0,
        units="1",
        confidence="medium",
        source_reference="synthetic residual oil assay",
        target_module="M1",
        fit_method="inverse_well_mixed_extraction",
        posterior_uncertainty=0.2,
    ))

    result = PipelineOrchestrator(output_dir=tmp_path).run_single(
        params,
        run_context=RunContext(calibration_store=store),
    )

    assert result.parameters.formulation.m1_oil_retention_factor == pytest.approx(4.0)
    assert result.run_report.diagnostics["calibration_count"] >= 1
    assert any(
        "m1_oil_retention_factor" in item
        for item in result.run_report.diagnostics["calibrations_applied"]
    )


def test_lifecycle_run_context_applies_m1_wash_calibration(tmp_path):
    params = load_config("configs/fast_smoke.toml")
    store = CalibrationStore()
    store.add(CalibrationEntry(
        profile_key="m1_washing",
        parameter_name="m1_oil_retention_factor",
        measured_value=4.0,
        units="1",
        confidence="medium",
        source_reference="synthetic residual oil assay",
        target_module="M1",
        fit_method="inverse_well_mixed_extraction",
        posterior_uncertainty=0.2,
    ))

    result = DownstreamProcessOrchestrator(output_dir=tmp_path).run(
        params=params,
        run_context=RunContext(calibration_store=store),
        propagate_dsd=False,
    )

    assert result.m1_contract.washing_model.oil_retention_factor == pytest.approx(4.0)
    assert result.m1_result.run_report.diagnostics["calibration_count"] >= 1
    assert result.graph.nodes["M2"].diagnostics["m1_residual_oil_limit"] > 0.0


def test_lifecycle_flags_m1_carryover_against_recipe_targets(tmp_path):
    params = load_config("configs/fast_smoke.toml")
    recipe = default_affinity_media_recipe()
    recipe.target.max_residual_oil_volume_fraction = Quantity(
        0.001,
        "fraction",
        source="target",
    )
    recipe.target.max_residual_surfactant_concentration = Quantity(
        0.01,
        "kg/m3",
        source="target",
    )

    result = DownstreamProcessOrchestrator(output_dir=tmp_path).run(
        recipe=recipe,
        params=params,
        propagate_dsd=False,
    )

    codes = {issue.code for issue in result.validation.issues}
    assert "M1_RESIDUAL_OIL_CARRYOVER" in codes
    assert "M1_RESIDUAL_SURFACTANT_CARRYOVER" in codes
    assert result.graph.nodes["M2"].diagnostics["residual_oil_limit_ratio"] > 1.0
    assert result.graph.nodes["M3"].diagnostics["residual_surfactant_limit_ratio"] > 1.0
