"""ProcessRecipe import/export helpers.

P1 makes ``ProcessRecipe`` the lifecycle input authority. These helpers provide
stable JSON/TOML artifacts so CLI, UI, notebooks, and future automation can
exchange the same wet-lab recipe object instead of rebuilding lifecycle inputs
from legacy solver dataclasses.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

from .process_recipe import (
    EquipmentProfile,
    LifecycleStage,
    MaterialBatch,
    ProcessRecipe,
    ProcessStep,
    ProcessStepKind,
    TargetProductProfile,
    default_affinity_media_recipe,
)
from .quantities import Quantity


RECIPE_SCHEMA_VERSION = "1.0"
_SPAN80_DENSITY_KG_M3 = 986.0


def quantity_to_dict(quantity: Quantity) -> dict[str, Any]:
    """Return a JSON/TOML-safe representation of a ``Quantity``."""

    data: dict[str, Any] = {
        "value": quantity.value,
        "unit": quantity.unit,
        "uncertainty": quantity.uncertainty,
        "source": quantity.source,
        "note": quantity.note,
    }
    if quantity.lower is not None:
        data["lower"] = quantity.lower
    if quantity.upper is not None:
        data["upper"] = quantity.upper
    return data


def quantity_from_dict(data: dict[str, Any]) -> Quantity:
    """Build a ``Quantity`` from a serialized representation."""

    return Quantity(
        value=float(data["value"]),
        unit=str(data["unit"]),
        uncertainty=float(data.get("uncertainty", 0.0)),
        source=str(data.get("source", "unspecified")),
        lower=None if data.get("lower") is None else float(data["lower"]),
        upper=None if data.get("upper") is None else float(data["upper"]),
        note=str(data.get("note", "")),
    )


def process_recipe_to_dict(recipe: ProcessRecipe) -> dict[str, Any]:
    """Serialize a ``ProcessRecipe`` into plain Python data."""

    return {
        "schema_version": RECIPE_SCHEMA_VERSION,
        "run_mode": recipe.run_mode,
        "owner": recipe.owner,
        "notes": recipe.notes,
        "target": _target_to_dict(recipe.target),
        "material_batch": _material_batch_to_dict(recipe.material_batch),
        "equipment": _equipment_to_dict(recipe.equipment),
        "steps": [_step_to_dict(step) for step in recipe.steps],
    }


def process_recipe_from_dict(data: dict[str, Any]) -> ProcessRecipe:
    """Deserialize a ``ProcessRecipe`` from plain Python data."""

    version = str(data.get("schema_version", RECIPE_SCHEMA_VERSION))
    if version != RECIPE_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported ProcessRecipe schema_version {version!r}; "
            f"expected {RECIPE_SCHEMA_VERSION!r}."
        )
    return ProcessRecipe(
        target=_target_from_dict(data.get("target", {})),
        material_batch=_material_batch_from_dict(data.get("material_batch", {})),
        equipment=_equipment_from_dict(data.get("equipment", {})),
        steps=[_step_from_dict(item) for item in data.get("steps", [])],
        run_mode=str(data.get("run_mode", "hybrid_coupled")),
        owner=str(data.get("owner", "")),
        notes=str(data.get("notes", "")),
    )


def load_process_recipe(path: str | Path) -> ProcessRecipe:
    """Load a recipe from `.json` or `.toml`."""

    recipe_path = Path(path)
    suffix = recipe_path.suffix.lower()
    if suffix == ".json":
        with recipe_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    elif suffix == ".toml":
        import tomllib

        with recipe_path.open("rb") as handle:
            data = tomllib.load(handle)
    else:
        raise ValueError(f"Unsupported recipe extension {suffix!r}; use .json or .toml.")
    return process_recipe_from_dict(data)


def save_process_recipe(recipe: ProcessRecipe, path: str | Path) -> Path:
    """Write a recipe to `.json` or `.toml` and return the written path."""

    recipe_path = Path(path)
    recipe_path.parent.mkdir(parents=True, exist_ok=True)
    suffix = recipe_path.suffix.lower()
    if suffix == ".json":
        with recipe_path.open("w", encoding="utf-8") as handle:
            json.dump(process_recipe_to_dict(recipe), handle, indent=2)
            handle.write("\n")
    elif suffix == ".toml":
        recipe_path.write_text(process_recipe_to_toml(recipe), encoding="utf-8")
    else:
        raise ValueError(f"Unsupported recipe extension {suffix!r}; use .json or .toml.")
    return recipe_path


def process_recipe_to_toml(recipe: ProcessRecipe) -> str:
    """Return a human-editable TOML representation of a recipe."""

    lines: list[str] = [
        f"schema_version = {_toml_value(RECIPE_SCHEMA_VERSION)}",
        f"run_mode = {_toml_value(recipe.run_mode)}",
        f"owner = {_toml_value(recipe.owner)}",
        f"notes = {_toml_value(recipe.notes)}",
        "",
        "[target]",
    ]
    _write_scalar_fields(
        lines,
        _target_to_dict(recipe.target),
        exclude={"bead_d50", "pore_size", "min_modulus", "max_pressure_drop"},
    )
    for key in ("bead_d50", "pore_size", "min_modulus", "max_pressure_drop"):
        _write_quantity_section(lines, ("target", key), getattr(recipe.target, key))

    lines.extend(["", "[material_batch]"])
    material_data = _material_batch_to_dict(recipe.material_batch)
    _write_scalar_fields(lines, material_data, exclude={"properties"})
    for key, value in recipe.material_batch.properties.items():
        _write_quantity_section(lines, ("material_batch", "properties", key), value)

    lines.extend(["", "[equipment]"])
    equipment_data = _equipment_to_dict(recipe.equipment)
    _write_scalar_fields(lines, equipment_data, exclude={"pump_pressure_limit"})
    _write_quantity_section(lines, ("equipment", "pump_pressure_limit"), recipe.equipment.pump_pressure_limit)

    for step in recipe.steps:
        lines.extend(["", "[[steps]]"])
        step_data = _step_to_dict(step)
        _write_scalar_fields(lines, step_data, exclude={"parameters"})
        primitive_params = {
            key: value
            for key, value in step.parameters.items()
            if not isinstance(value, Quantity)
        }
        if primitive_params:
            lines.extend(["", "[steps.parameters]"])
            _write_scalar_fields(lines, primitive_params)
        for key, value in step.parameters.items():
            if isinstance(value, Quantity):
                _write_quantity_section(lines, ("steps", "parameters", key), value)

    return "\n".join(lines).rstrip() + "\n"


def recipe_from_simulation_parameters(
    params,
    base_recipe: ProcessRecipe | None = None,
) -> ProcessRecipe:
    """Create a lifecycle recipe from legacy ``SimulationParameters``.

    This is a migration bridge for CLI/UI callers that still expose legacy M1
    forms. It updates only recipe fields represented by ``SimulationParameters``;
    M2 and M3 remain from the base recipe until those UI/CLI controls are
    recipe-native.
    """

    recipe = copy.deepcopy(base_recipe) if base_recipe is not None else default_affinity_media_recipe()
    for step in recipe.steps:
        if step.stage == LifecycleStage.M1_FABRICATION and step.kind == ProcessStepKind.EMULSIFY:
            step.parameters["rpm"] = Quantity(
                float(params.emulsification.rpm),
                "rpm",
                source="legacy_config_bridge",
                note="Migrated from SimulationParameters.emulsification.rpm.",
            )
            step.parameters["time"] = Quantity(
                float(params.emulsification.t_emulsification),
                "s",
                source="legacy_config_bridge",
                note="Migrated from SimulationParameters.emulsification.t_emulsification.",
            )
        elif step.stage == LifecycleStage.M1_FABRICATION and step.kind == ProcessStepKind.PREPARE_PHASE:
            step.parameters["oil_temperature"] = Quantity(
                float(params.formulation.T_oil),
                "K",
                source="legacy_config_bridge",
                note="Migrated from SimulationParameters.formulation.T_oil.",
            )
            span80_pct = float(params.formulation.c_span80) / _SPAN80_DENSITY_KG_M3 * 100.0
            step.parameters["span80"] = Quantity(
                span80_pct,
                "%",
                source="legacy_config_bridge",
                note=(
                    "Approximate v/v percent migrated from "
                    "SimulationParameters.formulation.c_span80 using "
                    "rho_span80=986 kg/m3."
                ),
            )
        elif step.stage == LifecycleStage.M1_FABRICATION and step.kind == ProcessStepKind.COOL_OR_GEL:
            step.parameters["cooling_rate"] = Quantity(
                float(params.formulation.cooling_rate),
                "K/s",
                source="legacy_config_bridge",
                note="Migrated from SimulationParameters.formulation.cooling_rate.",
            )
            step.parameters["initial_oil_carryover_fraction"] = Quantity(
                float(params.formulation.m1_initial_oil_carryover_fraction),
                "fraction",
                source="legacy_config_bridge",
                note="Migrated from SimulationParameters.formulation.m1_initial_oil_carryover_fraction.",
            )
            step.parameters["wash_cycles"] = Quantity(
                float(params.formulation.m1_wash_cycles),
                "1",
                source="legacy_config_bridge",
                note="Migrated from SimulationParameters.formulation.m1_wash_cycles.",
            )
            step.parameters["wash_volume_ratio"] = Quantity(
                float(params.formulation.m1_wash_volume_ratio),
                "1",
                source="legacy_config_bridge",
                note="Migrated from SimulationParameters.formulation.m1_wash_volume_ratio.",
            )
            step.parameters["wash_mixing_efficiency"] = Quantity(
                float(params.formulation.m1_wash_mixing_efficiency),
                "fraction",
                source="legacy_config_bridge",
                note="Migrated from SimulationParameters.formulation.m1_wash_mixing_efficiency.",
            )
            step.parameters["oil_retention_factor"] = Quantity(
                float(params.formulation.m1_oil_retention_factor),
                "1",
                source="legacy_config_bridge",
                note="Migrated from SimulationParameters.formulation.m1_oil_retention_factor.",
            )
            step.parameters["surfactant_retention_factor"] = Quantity(
                float(params.formulation.m1_surfactant_retention_factor),
                "1",
                source="legacy_config_bridge",
                note="Migrated from SimulationParameters.formulation.m1_surfactant_retention_factor.",
            )
    return recipe


def _target_to_dict(target: TargetProductProfile) -> dict[str, Any]:
    return {
        "name": target.name,
        "bead_d50": quantity_to_dict(target.bead_d50),
        "pore_size": quantity_to_dict(target.pore_size),
        "min_modulus": quantity_to_dict(target.min_modulus),
        "target_ligand": target.target_ligand,
        "target_analyte": target.target_analyte,
        "max_pressure_drop": quantity_to_dict(target.max_pressure_drop),
        "notes": target.notes,
    }


def _target_from_dict(data: dict[str, Any]) -> TargetProductProfile:
    default = TargetProductProfile()
    return TargetProductProfile(
        name=str(data.get("name", default.name)),
        bead_d50=_quantity_or_default(data, "bead_d50", default.bead_d50),
        pore_size=_quantity_or_default(data, "pore_size", default.pore_size),
        min_modulus=_quantity_or_default(data, "min_modulus", default.min_modulus),
        target_ligand=str(data.get("target_ligand", default.target_ligand)),
        target_analyte=str(data.get("target_analyte", default.target_analyte)),
        max_pressure_drop=_quantity_or_default(data, "max_pressure_drop", default.max_pressure_drop),
        notes=str(data.get("notes", default.notes)),
    )


def _material_batch_to_dict(batch: MaterialBatch) -> dict[str, Any]:
    return {
        "polymer_family": batch.polymer_family,
        "polymer_lot": batch.polymer_lot,
        "oil_lot": batch.oil_lot,
        "surfactant_lot": batch.surfactant_lot,
        "ligand_lot": batch.ligand_lot,
        "target_molecule": batch.target_molecule,
        "properties": {
            key: quantity_to_dict(value)
            for key, value in batch.properties.items()
        },
    }


def _material_batch_from_dict(data: dict[str, Any]) -> MaterialBatch:
    default = MaterialBatch()
    return MaterialBatch(
        polymer_family=str(data.get("polymer_family", default.polymer_family)),
        polymer_lot=str(data.get("polymer_lot", default.polymer_lot)),
        oil_lot=str(data.get("oil_lot", default.oil_lot)),
        surfactant_lot=str(data.get("surfactant_lot", default.surfactant_lot)),
        ligand_lot=str(data.get("ligand_lot", default.ligand_lot)),
        target_molecule=str(data.get("target_molecule", default.target_molecule)),
        properties={
            str(key): quantity_from_dict(value)
            for key, value in data.get("properties", {}).items()
        },
    )


def _equipment_to_dict(equipment: EquipmentProfile) -> dict[str, Any]:
    return {
        "emulsifier": equipment.emulsifier,
        "vessel": equipment.vessel,
        "column_id": equipment.column_id,
        "detector": equipment.detector,
        "pump_pressure_limit": quantity_to_dict(equipment.pump_pressure_limit),
        "notes": equipment.notes,
    }


def _equipment_from_dict(data: dict[str, Any]) -> EquipmentProfile:
    default = EquipmentProfile()
    return EquipmentProfile(
        emulsifier=str(data.get("emulsifier", default.emulsifier)),
        vessel=str(data.get("vessel", default.vessel)),
        column_id=str(data.get("column_id", default.column_id)),
        detector=str(data.get("detector", default.detector)),
        pump_pressure_limit=_quantity_or_default(
            data, "pump_pressure_limit", default.pump_pressure_limit
        ),
        notes=str(data.get("notes", default.notes)),
    )


def _step_to_dict(step: ProcessStep) -> dict[str, Any]:
    return {
        "name": step.name,
        "stage": step.stage.value,
        "kind": step.kind.value,
        "parameters": {
            key: quantity_to_dict(value) if isinstance(value, Quantity) else value
            for key, value in step.parameters.items()
        },
        "notes": step.notes,
        "qc_required": list(step.qc_required),
    }


def _step_from_dict(data: dict[str, Any]) -> ProcessStep:
    return ProcessStep(
        name=str(data["name"]),
        stage=LifecycleStage(str(data["stage"])),
        kind=ProcessStepKind(str(data["kind"])),
        parameters={
            str(key): quantity_from_dict(value) if _looks_like_quantity(value) else value
            for key, value in data.get("parameters", {}).items()
        },
        notes=str(data.get("notes", "")),
        qc_required=[str(item) for item in data.get("qc_required", [])],
    )


def _quantity_or_default(data: dict[str, Any], key: str, default: Quantity) -> Quantity:
    value = data.get(key)
    if value is None:
        return default
    if not _looks_like_quantity(value):
        raise ValueError(f"Expected serialized Quantity for {key!r}.")
    return quantity_from_dict(value)


def _looks_like_quantity(value: Any) -> bool:
    return isinstance(value, dict) and "value" in value and "unit" in value


def _write_quantity_section(
    lines: list[str],
    path: tuple[str, ...],
    quantity: Quantity,
) -> None:
    lines.extend(["", f"[{_toml_path(path)}]"])
    _write_scalar_fields(lines, quantity_to_dict(quantity))


def _write_scalar_fields(
    lines: list[str],
    data: dict[str, Any],
    exclude: set[str] | None = None,
) -> None:
    excluded = exclude or set()
    for key, value in data.items():
        if key in excluded or isinstance(value, dict) or value is None:
            continue
        lines.append(f"{_toml_key(key)} = {_toml_value(value)}")


def _toml_path(parts: tuple[str, ...]) -> str:
    return ".".join(_toml_key(part) for part in parts)


def _toml_key(key: str) -> str:
    key = str(key)
    if re.fullmatch(r"[A-Za-z0-9_-]+", key):
        return key
    return json.dumps(key)


def _toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_toml_value(item) for item in value) + "]"
    return json.dumps(str(value))
