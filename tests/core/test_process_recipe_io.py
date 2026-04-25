import tomllib

import pytest

from dpsim.config import load_config
from dpsim.core import Quantity
from dpsim.core.process_recipe import ProcessStepKind, default_affinity_media_recipe
from dpsim.core.recipe_io import (
    load_process_recipe,
    process_recipe_from_dict,
    process_recipe_to_dict,
    recipe_from_simulation_parameters,
    save_process_recipe,
)
from dpsim.lifecycle import resolve_lifecycle_inputs


def test_process_recipe_json_round_trip(tmp_path):
    recipe = default_affinity_media_recipe()
    path = tmp_path / "recipe.json"

    save_process_recipe(recipe, path)
    loaded = load_process_recipe(path)

    assert len(loaded.steps) == len(recipe.steps)
    assert loaded.target.name == recipe.target.name
    assert resolve_lifecycle_inputs(loaded).m3_flow_rate == pytest.approx(1.0e-8)


def test_process_recipe_toml_round_trip(tmp_path):
    recipe = default_affinity_media_recipe()
    path = tmp_path / "recipe.toml"

    save_process_recipe(recipe, path)
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    loaded = process_recipe_from_dict(raw)

    assert loaded.steps[0].parameters["oil_temperature"].as_unit("K").value == pytest.approx(363.15)
    assert loaded.steps_for_stage(loaded.steps[0].stage)


def test_process_recipe_dict_preserves_quantities_and_primitives():
    recipe = default_affinity_media_recipe()

    data = process_recipe_to_dict(recipe)
    loaded = process_recipe_from_dict(data)

    coupling = next(step for step in loaded.steps if step.kind == ProcessStepKind.COUPLE_LIGAND)
    assert coupling.parameters["reagent_key"] == "protein_a_coupling"
    assert isinstance(coupling.parameters["pH"], Quantity)
    assert coupling.parameters["reagent_concentration"].unit == "mol/m3"


def test_legacy_simulation_parameters_bridge_updates_m1_recipe_fields():
    params = load_config("configs/fast_smoke.toml")

    recipe = recipe_from_simulation_parameters(params)
    resolved = resolve_lifecycle_inputs(recipe, base_params=params)

    assert resolved.parameters.emulsification.t_emulsification == pytest.approx(10.0)
    assert resolved.parameters.emulsification.rpm == pytest.approx(10000.0)
    assert resolved.parameters.formulation.c_span80 == pytest.approx(20.0)
    assert resolved.parameters.formulation.m1_wash_cycles == params.formulation.m1_wash_cycles
    assert resolved.parameters.formulation.m1_wash_volume_ratio == pytest.approx(
        params.formulation.m1_wash_volume_ratio
    )
