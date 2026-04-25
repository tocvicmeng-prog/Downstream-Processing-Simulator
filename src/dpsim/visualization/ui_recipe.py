"""Recipe-native Streamlit state helpers.

The Streamlit pages remain widget-oriented, but P1 requires those widgets to
emit and consume ``ProcessRecipe`` rather than treating the legacy numerical
dataclasses as the lifecycle source of truth. This module keeps that boundary
small and testable: UI code writes user choices into a serialized recipe using
``dpsim.core.recipe_io``; lifecycle resolvers then translate the recipe into
kernel-specific inputs.
"""

from __future__ import annotations

import copy
import math
from collections.abc import MutableMapping, Sequence
from typing import Any

from dpsim.core.process_recipe import (
    LifecycleStage,
    ProcessRecipe,
    ProcessStep,
    ProcessStepKind,
    default_affinity_media_recipe,
)
from dpsim.core.quantities import Quantity
from dpsim.core.recipe_io import process_recipe_from_dict, process_recipe_to_dict
from dpsim.module2_functionalization.modification_steps import (
    ModificationStep,
    ModificationStepType,
)


PROCESS_RECIPE_STATE_KEY = "process_recipe"
UI_SOURCE = "streamlit_ui"
IGG_MW_DA_DEFAULT = 66500.0


def ensure_process_recipe_state(store: MutableMapping[str, Any]) -> ProcessRecipe:
    """Return the session recipe, initializing and serializing it when absent.

    Streamlit session state can persist arbitrary objects, but the recipe is
    intentionally stored as plain serialized data. This mirrors CLI/notebook
    artifacts, exercises ``recipe_io`` on every UI round trip, and prevents a
    stale in-memory dataclass from becoming a hidden second source of truth.
    """

    raw_recipe = store.get(PROCESS_RECIPE_STATE_KEY)
    if isinstance(raw_recipe, ProcessRecipe):
        recipe = copy.deepcopy(raw_recipe)
        store[PROCESS_RECIPE_STATE_KEY] = process_recipe_to_dict(recipe)
        return recipe
    if isinstance(raw_recipe, dict):
        return process_recipe_from_dict(copy.deepcopy(raw_recipe))

    recipe = default_affinity_media_recipe()
    store[PROCESS_RECIPE_STATE_KEY] = process_recipe_to_dict(recipe)
    return recipe


def save_process_recipe_state(
    store: MutableMapping[str, Any],
    recipe: ProcessRecipe,
) -> ProcessRecipe:
    """Persist ``recipe`` in Streamlit state through the recipe IO serializer."""

    store[PROCESS_RECIPE_STATE_KEY] = process_recipe_to_dict(recipe)
    return recipe


def sync_m1_ui_to_recipe(
    recipe: ProcessRecipe,
    *,
    polymer_family: str,
    is_stirred: bool,
    rpm: float,
    emulsification_time_min: float,
    oil_temperature_C: float,
    span80_percent: float,
    cooling_rate_C_min: float,
    dispersed_phase_fraction: float,
    oil_volume_mL: float,
    polymer_volume_mL: float,
    target_diameter_um: float | None = None,
    target_pore_nm: float | None = None,
    target_modulus_kPa: float | None = None,
    vessel_choice: str = "",
    stirrer_choice: str = "",
    surfactant_key: str = "span80",
    model_mode: str = "",
) -> ProcessRecipe:
    """Update recipe-owned M1 controls from Streamlit widget values."""

    recipe.material_batch.polymer_family = str(polymer_family)
    recipe.equipment.emulsifier = "stirred_vessel" if is_stirred else "rotor_stator_legacy"
    if vessel_choice:
        recipe.equipment.vessel = vessel_choice
    recipe.run_mode = model_mode or recipe.run_mode
    if target_diameter_um is not None:
        recipe.target.bead_d50 = Quantity(float(target_diameter_um), "um", source=UI_SOURCE)
    if target_pore_nm is not None:
        recipe.target.pore_size = Quantity(float(target_pore_nm), "nm", source=UI_SOURCE)
    if target_modulus_kPa is not None:
        recipe.target.min_modulus = Quantity(float(target_modulus_kPa), "kPa", source=UI_SOURCE)

    prepare = _step_for(recipe, LifecycleStage.M1_FABRICATION, ProcessStepKind.PREPARE_PHASE)
    prepare.parameters.update(
        {
            "oil_temperature": Quantity(float(oil_temperature_C), "degC", source=UI_SOURCE),
            "span80": Quantity(
                float(span80_percent),
                "%",
                source=UI_SOURCE,
                note=(
                    "Streamlit M1 surfactant control. Stirred mode uses v/v percent; "
                    "legacy rotor-stator mode uses the displayed w/v percent as a "
                    "Span-80-equivalent screening input."
                ),
            ),
            "surfactant_key": str(surfactant_key),
        }
    )

    emulsify = _step_for(recipe, LifecycleStage.M1_FABRICATION, ProcessStepKind.EMULSIFY)
    emulsify.parameters.update(
        {
            "rpm": Quantity(float(rpm), "rpm", source=UI_SOURCE),
            "time": Quantity(float(emulsification_time_min), "min", source=UI_SOURCE),
            "hardware_mode": recipe.equipment.emulsifier,
            "vessel_choice": str(vessel_choice),
            "stirrer_choice": str(stirrer_choice),
            "dispersed_phase_fraction": Quantity(float(dispersed_phase_fraction), "fraction", source=UI_SOURCE),
            "oil_volume": Quantity(float(oil_volume_mL), "mL", source=UI_SOURCE),
            "polymer_volume": Quantity(float(polymer_volume_mL), "mL", source=UI_SOURCE),
        }
    )

    cool = _step_for(recipe, LifecycleStage.M1_FABRICATION, ProcessStepKind.COOL_OR_GEL)
    cool.parameters["cooling_rate"] = Quantity(float(cooling_rate_C_min), "K/min", source=UI_SOURCE)
    return recipe


def sync_m2_steps_to_recipe(
    recipe: ProcessRecipe,
    steps: Sequence[ModificationStep],
) -> ProcessRecipe:
    """Replace recipe M2 operations with the current Streamlit M2 workflow."""

    retained = [
        step
        for step in recipe.steps
        if step.stage != LifecycleStage.M2_FUNCTIONALIZATION
    ]
    retained.extend(_process_step_from_m2_step(step, index) for index, step in enumerate(steps))
    recipe.steps = retained
    return recipe


def sync_m3_ui_to_recipe(
    recipe: ProcessRecipe,
    *,
    application_mode: str,
    chromatography_mode: str,
    column_diameter_mm: float,
    bed_height_cm: float,
    bed_porosity: float,
    flow_rate_mL_min: float,
    feed_concentration_mg_mL: float,
    feed_duration_min: float,
    total_time_min: float,
    bind_pH: float,
    bind_conductivity_mS_cm: float,
    wash_duration_min: float,
    elute_pH: float,
    elute_conductivity_mS_cm: float,
    elute_duration_min: float,
    gradient_start_mM: float = 0.0,
    gradient_end_mM: float = 0.0,
    gradient_duration_min: float = 0.0,
    feed_mw_Da: float = IGG_MW_DA_DEFAULT,
) -> ProcessRecipe:
    """Update recipe-owned M3 column and chromatography method controls."""

    recipe.equipment.column_id = f"streamlit_{column_diameter_mm:g}mm_x_{bed_height_cm:g}cm"
    recipe.material_batch.target_molecule = "IgG" if application_mode == "Chromatography" else "substrate"
    feed_conc_mol_m3 = mg_mL_to_mol_m3(feed_concentration_mg_mL, feed_mw_Da)
    residence_time_min = _bed_volume_mL(column_diameter_mm, bed_height_cm) / max(flow_rate_mL_min, 1e-12)

    pack = _step_for(recipe, LifecycleStage.M3_PERFORMANCE, ProcessStepKind.PACK_COLUMN)
    pack.parameters.update(
        {
            "column_id": recipe.equipment.column_id,
            "column_diameter": Quantity(float(column_diameter_mm), "mm", source=UI_SOURCE),
            "bed_height": Quantity(float(bed_height_cm), "cm", source=UI_SOURCE),
            "bed_porosity": Quantity(float(bed_porosity), "fraction", source=UI_SOURCE),
            "packing_flow_rate": Quantity(float(flow_rate_mL_min), "mL/min", source=UI_SOURCE),
        }
    )

    equilibrate = _step_for(recipe, LifecycleStage.M3_PERFORMANCE, ProcessStepKind.EQUILIBRATE)
    equilibrate.parameters.update(
        {
            "buffer_name": "binding/equilibration buffer",
            "pH": Quantity(float(bind_pH), "1", source=UI_SOURCE),
            "conductivity": Quantity(float(bind_conductivity_mS_cm), "mS/cm", source=UI_SOURCE),
            "flow_rate": Quantity(float(flow_rate_mL_min), "mL/min", source=UI_SOURCE),
            "duration": Quantity(float(wash_duration_min), "min", source=UI_SOURCE),
        }
    )

    load = _step_for(recipe, LifecycleStage.M3_PERFORMANCE, ProcessStepKind.LOAD)
    load.parameters.update(
        {
            "buffer_name": "feed in binding buffer",
            "pH": Quantity(float(bind_pH), "1", source=UI_SOURCE),
            "conductivity": Quantity(float(bind_conductivity_mS_cm), "mS/cm", source=UI_SOURCE),
            "feed_concentration": Quantity(feed_conc_mol_m3, "mol/m3", source=UI_SOURCE),
            "flow_rate": Quantity(float(flow_rate_mL_min), "mL/min", source=UI_SOURCE),
            "feed_duration": Quantity(float(feed_duration_min), "min", source=UI_SOURCE),
            "total_time": Quantity(float(total_time_min), "min", source=UI_SOURCE),
            "residence_time": Quantity(residence_time_min, "min", source="streamlit_ui_derived"),
            "feed_concentration_input": Quantity(float(feed_concentration_mg_mL), "mg/mL", source=UI_SOURCE),
            "feed_mw_Da": float(feed_mw_Da),
            "chromatography_mode": str(chromatography_mode),
        }
    )

    wash = _step_for(recipe, LifecycleStage.M3_PERFORMANCE, ProcessStepKind.WASH)
    wash.parameters.update(
        {
            "buffer_name": "wash buffer",
            "pH": Quantity(float(bind_pH), "1", source=UI_SOURCE),
            "conductivity": Quantity(float(bind_conductivity_mS_cm), "mS/cm", source=UI_SOURCE),
            "flow_rate": Quantity(float(flow_rate_mL_min), "mL/min", source=UI_SOURCE),
            "duration": Quantity(float(wash_duration_min), "min", source=UI_SOURCE),
        }
    )

    elute = _step_for(recipe, LifecycleStage.M3_PERFORMANCE, ProcessStepKind.ELUTE)
    elute.parameters.update(
        {
            "buffer_name": "elution buffer",
            "pH": Quantity(float(elute_pH), "1", source=UI_SOURCE),
            "conductivity": Quantity(float(elute_conductivity_mS_cm), "mS/cm", source=UI_SOURCE),
            "flow_rate": Quantity(float(flow_rate_mL_min), "mL/min", source=UI_SOURCE),
            "duration": Quantity(float(elute_dur_or_gradient(chromatography_mode, elute_duration_min, gradient_duration_min)), "min", source=UI_SOURCE),
        }
    )
    if chromatography_mode == "Protein A Method":
        elute.parameters.update(
            {
                "gradient_field": "ph",
                "gradient_start_pH": Quantity(float(bind_pH), "1", source=UI_SOURCE),
                "gradient_end_pH": Quantity(float(elute_pH), "1", source=UI_SOURCE),
            }
        )
    elif chromatography_mode == "Gradient Elution":
        elute.parameters.update(
            {
                "gradient_field": "conductivity",
                "gradient_start_concentration": Quantity(float(gradient_start_mM), "mM", source=UI_SOURCE),
                "gradient_end_concentration": Quantity(float(gradient_end_mM), "mM", source=UI_SOURCE),
            }
        )
    return recipe


def mg_mL_to_mol_m3(concentration_mg_mL: float, mw_Da: float) -> float:
    """Convert protein concentration from mg/mL to mol/m3 using MW in Da."""

    if mw_Da <= 0.0:
        raise ValueError("Molecular weight must be positive.")
    return float(concentration_mg_mL) / (float(mw_Da) * 1e-3)


def elute_dur_or_gradient(
    chromatography_mode: str,
    elute_duration_min: float,
    gradient_duration_min: float,
) -> float:
    """Return the recipe elution duration appropriate to the selected mode."""

    if chromatography_mode == "Gradient Elution" and gradient_duration_min > 0:
        return float(gradient_duration_min)
    return float(elute_duration_min)


def _step_for(
    recipe: ProcessRecipe,
    stage: LifecycleStage,
    kind: ProcessStepKind,
) -> ProcessStep:
    """Return the first matching step, creating a named step if needed."""

    for step in recipe.steps:
        if step.stage == stage and step.kind == kind:
            return step
    step = ProcessStep(
        name=_default_step_name(stage, kind),
        stage=stage,
        kind=kind,
    )
    recipe.steps.append(step)
    return step


def _default_step_name(stage: LifecycleStage, kind: ProcessStepKind) -> str:
    stage_label = stage.value.split("_", 1)[0]
    return f"{stage_label} {kind.value.replace('_', ' ')}"


def _process_step_from_m2_step(step: ModificationStep, index: int) -> ProcessStep:
    kind = _M2_KIND_BY_STEP_TYPE[step.step_type]
    name = f"{index + 1}. {step.step_type.value.replace('_', ' ')} - {step.reagent_key}"
    return ProcessStep(
        name=name,
        stage=LifecycleStage.M2_FUNCTIONALIZATION,
        kind=kind,
        parameters={
            "reagent_key": step.reagent_key,
            "target_acs": step.target_acs.value,
            "pH": Quantity(float(step.ph), "1", source=UI_SOURCE),
            "temperature": Quantity(float(step.temperature), "K", source=UI_SOURCE),
            "time": Quantity(float(step.time), "s", source=UI_SOURCE),
            "reagent_concentration": Quantity(float(step.reagent_concentration), "mol/m3", source=UI_SOURCE),
        },
    )


_M2_KIND_BY_STEP_TYPE = {
    ModificationStepType.SECONDARY_CROSSLINKING: ProcessStepKind.CROSSLINK,
    ModificationStepType.ACTIVATION: ProcessStepKind.ACTIVATE,
    ModificationStepType.LIGAND_COUPLING: ProcessStepKind.COUPLE_LIGAND,
    ModificationStepType.PROTEIN_COUPLING: ProcessStepKind.COUPLE_LIGAND,
    ModificationStepType.QUENCHING: ProcessStepKind.BLOCK_OR_QUENCH,
    ModificationStepType.SPACER_ARM: ProcessStepKind.INSERT_SPACER,
    ModificationStepType.METAL_CHARGING: ProcessStepKind.METAL_CHARGE,
    ModificationStepType.PROTEIN_PRETREATMENT: ProcessStepKind.PROTEIN_PRETREATMENT,
    ModificationStepType.WASHING: ProcessStepKind.WASH,
}


def _bed_volume_mL(column_diameter_mm: float, bed_height_cm: float) -> float:
    diameter_cm = float(column_diameter_mm) / 10.0
    return math.pi * (diameter_cm / 2.0) ** 2 * float(bed_height_cm)
