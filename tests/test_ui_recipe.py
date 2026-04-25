"""Tests for Streamlit recipe-native state helpers."""

from __future__ import annotations

import pytest

from dpsim.core.process_recipe import (
    LifecycleStage,
    ProcessStepKind,
    default_affinity_media_recipe,
)
from dpsim.lifecycle import resolve_lifecycle_inputs
from dpsim.module2_functionalization.acs import ACSSiteType
from dpsim.module2_functionalization.modification_steps import (
    ModificationStep,
    ModificationStepType,
)
from dpsim.visualization.ui_recipe import (
    PROCESS_RECIPE_STATE_KEY,
    ensure_process_recipe_state,
    save_process_recipe_state,
    sync_m1_ui_to_recipe,
    sync_m2_steps_to_recipe,
    sync_m3_ui_to_recipe,
)


def test_streamlit_recipe_state_round_trips_through_recipe_io():
    store = {}

    recipe = ensure_process_recipe_state(store)
    recipe.owner = "ui-test"
    save_process_recipe_state(store, recipe)
    loaded = ensure_process_recipe_state(store)

    assert PROCESS_RECIPE_STATE_KEY in store
    assert isinstance(store[PROCESS_RECIPE_STATE_KEY], dict)
    assert loaded.owner == "ui-test"


def test_m1_ui_controls_update_resolved_recipe_parameters():
    recipe = sync_m1_ui_to_recipe(
        default_affinity_media_recipe(),
        polymer_family="agarose_chitosan",
        is_stirred=True,
        rpm=1450.0,
        emulsification_time_min=12.0,
        oil_temperature_C=82.0,
        span80_percent=1.7,
        cooling_rate_C_min=0.8,
        dispersed_phase_fraction=0.38,
        oil_volume_mL=320.0,
        polymer_volume_mL=200.0,
        target_diameter_um=125.0,
        target_pore_nm=90.0,
        target_modulus_kPa=18.0,
        vessel_choice="Glass Beaker (100 mm)",
        stirrer_choice="Stirrer A - Pitched Blade (59 mm)",
        surfactant_key="span80",
        model_mode="hybrid_coupled",
    )

    resolved = resolve_lifecycle_inputs(recipe)

    assert resolved.parameters.emulsification.rpm == pytest.approx(1450.0)
    assert resolved.parameters.emulsification.t_emulsification == pytest.approx(720.0)
    assert resolved.parameters.formulation.T_oil == pytest.approx(355.15)
    assert resolved.parameters.formulation.cooling_rate == pytest.approx(0.8 / 60.0)
    assert recipe.target.bead_d50.value == pytest.approx(125.0)


def test_m2_ui_steps_replace_recipe_and_resolve_backend_steps():
    recipe = sync_m2_steps_to_recipe(
        default_affinity_media_recipe(),
        [
            ModificationStep(
                step_type=ModificationStepType.ACTIVATION,
                reagent_key="ech_activation",
                target_acs=ACSSiteType.HYDROXYL,
                product_acs=ACSSiteType.EPOXIDE,
                temperature=303.15,
                time=1800.0,
                ph=12.5,
                reagent_concentration=25.0,
            ),
            ModificationStep(
                step_type=ModificationStepType.PROTEIN_PRETREATMENT,
                reagent_key="tcep_reduction",
                target_acs=ACSSiteType.MALEIMIDE,
                product_acs=None,
                temperature=298.15,
                time=900.0,
                ph=7.0,
                reagent_concentration=5.0,
            ),
        ],
    )

    m2_recipe_steps = recipe.steps_for_stage(LifecycleStage.M2_FUNCTIONALIZATION)
    resolved = resolve_lifecycle_inputs(recipe)

    assert [step.kind for step in m2_recipe_steps] == [
        ProcessStepKind.ACTIVATE,
        ProcessStepKind.PROTEIN_PRETREATMENT,
    ]
    assert [step.step_type for step in resolved.functionalization_steps] == [
        ModificationStepType.ACTIVATION,
        ModificationStepType.PROTEIN_PRETREATMENT,
    ]
    assert resolved.functionalization_steps[0].reagent_concentration == pytest.approx(25.0)


def test_m3_ui_controls_update_recipe_method_and_resolved_column():
    recipe = sync_m3_ui_to_recipe(
        default_affinity_media_recipe(),
        application_mode="Chromatography",
        chromatography_mode="Protein A Method",
        column_diameter_mm=8.0,
        bed_height_cm=12.0,
        bed_porosity=0.41,
        flow_rate_mL_min=0.75,
        feed_concentration_mg_mL=2.0,
        feed_duration_min=15.0,
        total_time_min=35.0,
        bind_pH=7.2,
        bind_conductivity_mS_cm=12.0,
        wash_duration_min=6.0,
        elute_pH=3.4,
        elute_conductivity_mS_cm=4.0,
        elute_duration_min=7.0,
    )

    resolved = resolve_lifecycle_inputs(recipe)
    elute_steps = [
        step
        for step in recipe.steps_for_stage(LifecycleStage.M3_PERFORMANCE)
        if step.kind == ProcessStepKind.ELUTE
    ]

    assert resolved.column.diameter == pytest.approx(0.008)
    assert resolved.column.bed_height == pytest.approx(0.12)
    assert resolved.m3_flow_rate == pytest.approx(0.75e-6 / 60.0)
    assert resolved.m3_feed_duration == pytest.approx(900.0)
    assert resolved.m3_feed_concentration == pytest.approx(2.0 / (66500.0 * 1e-3))
    assert elute_steps[0].parameters["gradient_field"] == "ph"
    assert resolved.m3_method_steps[-1].gradient_end == pytest.approx(3.4)
