from pathlib import Path

import pytest

from dpsim.config import load_config
from dpsim.core import Quantity, validate_model_manifest_domains
from dpsim.core.process_recipe import ProcessStepKind, default_affinity_media_recipe
from dpsim.datatypes import ModelEvidenceTier, ModelManifest
from dpsim.lifecycle import DownstreamProcessOrchestrator, resolve_lifecycle_inputs
from dpsim.module2_functionalization.modification_steps import ModificationStepType


def test_process_recipe_resolves_m1_m2_m3_inputs():
    recipe = default_affinity_media_recipe()

    resolved = resolve_lifecycle_inputs(recipe)

    assert resolved.parameters.emulsification.rpm == pytest.approx(10000.0)
    assert resolved.parameters.emulsification.t_emulsification == pytest.approx(60.0)
    assert resolved.parameters.formulation.T_oil == pytest.approx(363.15)
    assert resolved.parameters.formulation.cooling_rate == pytest.approx(10.0 / 60.0)
    assert resolved.parameters.formulation.c_span80_vol_pct == pytest.approx(1.5)
    assert resolved.parameters.formulation.m1_wash_cycles == 3
    assert resolved.parameters.formulation.m1_wash_volume_ratio == pytest.approx(3.0)
    assert [step.reagent_key for step in resolved.functionalization_steps] == [
        "ech_activation",
        "wash_buffer",
        "protein_a_coupling",
        "wash_buffer",
        "ethanolamine_quench",
        "wash_buffer",
        "wash_buffer",
    ]
    assert [step.step_type for step in resolved.functionalization_steps].count(
        ModificationStepType.WASHING
    ) == 4
    assert resolved.column.bed_height == pytest.approx(0.10)
    assert resolved.m3_flow_rate == pytest.approx(1.0e-8)
    assert resolved.max_residual_oil_volume_fraction == pytest.approx(0.01)
    assert resolved.max_residual_surfactant_concentration_kg_m3 == pytest.approx(0.5)
    assert "M1.emulsify.rpm" in resolved.resolved_parameters
    assert "M1.cool_or_gel.wash_cycles" in resolved.resolved_parameters
    assert "M3.load.flow_rate" in resolved.resolved_parameters
    assert "target.max_residual_oil_volume_fraction" in resolved.resolved_parameters
    assert "target.max_residual_surfactant_concentration" in resolved.resolved_parameters


def test_recipe_validation_flags_bad_reagent_domain():
    recipe = default_affinity_media_recipe()
    for step in recipe.steps:
        if step.kind == ProcessStepKind.COUPLE_LIGAND:
            step.parameters["pH"] = Quantity(2.0, "1", source="user_recipe")

    resolved = resolve_lifecycle_inputs(recipe)

    codes = {issue.code for issue in resolved.validation.issues}
    assert "M2_REAGENT_PH_DOMAIN" in codes


def test_manifest_domain_validator_flags_extrapolation():
    manifest = ModelManifest(
        model_name="test.domain",
        evidence_tier=ModelEvidenceTier.SEMI_QUANTITATIVE,
        valid_domain={"Re": (100.0, 1000.0)},
        diagnostics={"dimensionless_groups": {"Re": 10.0}},
    )

    report = validate_model_manifest_domains([manifest], module="M1")

    assert len(report.warnings) == 1
    assert report.warnings[0].code == "MODEL_DOMAIN"


def test_lifecycle_result_exposes_recipe_provenance_and_caveats(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    params = load_config(repo_root / "configs" / "fast_smoke.toml")
    recipe = default_affinity_media_recipe()
    for step in recipe.steps:
        if step.kind == ProcessStepKind.EMULSIFY:
            step.parameters["time"] = Quantity(10.0, "s", source="user_recipe")

    result = DownstreamProcessOrchestrator(output_dir=tmp_path).run(
        recipe=recipe,
        params=params,
        propagate_dsd=False,
    )

    summary_nodes = result.graph.as_summary()["nodes"]
    assert result.resolved_parameters["M1.emulsify.time"].quantity.value == pytest.approx(10.0)
    assert result.m3_breakthrough is not None
    assert all(node["manifest"] is not None for node in summary_nodes)
    assert all(node["wet_lab_caveats"] for node in summary_nodes)
    assert all("evidence_tier" in node["manifest"] for node in summary_nodes)
