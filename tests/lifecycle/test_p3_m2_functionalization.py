from __future__ import annotations

import copy

import pytest

from dpsim.core import Quantity
from dpsim.core.m2_recipe_templates import available_m2_templates, m2_template_steps
from dpsim.core.process_recipe import (
    LifecycleStage,
    ProcessStep,
    ProcessStepKind,
    default_affinity_media_recipe,
)
from dpsim.calibration.calibration_data import CalibrationEntry
from dpsim.calibration.calibration_store import CalibrationStore
from dpsim.datatypes import M1ExportContract
from dpsim.lifecycle import resolve_lifecycle_inputs
from dpsim.lifecycle.orchestrator import _validate_m2_assay_acceptance
from dpsim.module2_functionalization.acs import ACSSiteType
from dpsim.module2_functionalization.modification_steps import (
    ModificationStep,
    ModificationStepType,
)
from dpsim.module2_functionalization.orchestrator import (
    FunctionalMediaContract,
    ModificationOrchestrator,
)


def _make_contract() -> M1ExportContract:
    return M1ExportContract(
        bead_radius=50e-6,
        bead_d32=100e-6,
        bead_d50=100e-6,
        pore_size_mean=100e-9,
        pore_size_std=30e-9,
        porosity=0.7,
        l2_model_tier="empirical_calibrated",
        mesh_size_xi=20e-9,
        p_final=0.5,
        primary_crosslinker="genipin",
        nh2_bulk_concentration=100.0,
        oh_bulk_concentration=400.0,
        G_DN=5000.0,
        E_star=15000.0,
        model_used="phenomenological",
        c_agarose=42.0,
        c_chitosan=18.0,
        DDA=0.90,
        trust_level="CAUTION",
    )


def test_default_recipe_exposes_storage_buffer_exchange_stage():
    recipe = default_affinity_media_recipe()
    m2_steps = recipe.steps_for_stage(LifecycleStage.M2_FUNCTIONALIZATION)

    assert any(step.kind == ProcessStepKind.BLOCK_OR_QUENCH for step in m2_steps)
    assert any(step.kind == ProcessStepKind.STORAGE_BUFFER_EXCHANGE for step in m2_steps)

    resolved = resolve_lifecycle_inputs(recipe)
    assert not resolved.validation.blockers
    assert resolved.functionalization_steps[-1].step_type == ModificationStepType.WASHING
    assert resolved.functionalization_steps[-1].reagent_key == "wash_buffer"


def test_recipe_resolver_maps_explicit_spacer_insertion():
    recipe = copy.deepcopy(default_affinity_media_recipe())
    insert_at = next(
        index + 1
        for index, step in enumerate(recipe.steps)
        if step.stage == LifecycleStage.M2_FUNCTIONALIZATION
        and step.kind == ProcessStepKind.ACTIVATE
    )
    recipe.steps.insert(
        insert_at,
        ProcessStep(
            name="AHA spacer insertion",
            stage=LifecycleStage.M2_FUNCTIONALIZATION,
            kind=ProcessStepKind.INSERT_SPACER,
            parameters={
                "reagent_key": "aha_carboxyl_spacer_arm",
                "pH": Quantity(10.5, "1", source="test"),
                "temperature": Quantity(25.0, "degC", source="test"),
                "time": Quantity(4.0, "h", source="test"),
                "reagent_concentration": Quantity(50.0, "mol/m3", source="test"),
            },
        ),
    )

    resolved = resolve_lifecycle_inputs(recipe)

    spacer_steps = [
        step for step in resolved.functionalization_steps
        if step.reagent_key == "aha_carboxyl_spacer_arm"
    ]
    assert len(spacer_steps) == 1
    assert spacer_steps[0].step_type == ModificationStepType.SPACER_ARM
    assert spacer_steps[0].target_acs == ACSSiteType.EPOXIDE
    assert spacer_steps[0].product_acs == ACSSiteType.CARBOXYL_DISTAL


def test_p3_site_vocabulary_includes_hydrazide_and_imac_sites():
    assert ACSSiteType.HYDRAZIDE.value == "hydrazide"
    assert ACSSiteType.NTA.value == "nta"
    assert ACSSiteType.IDA.value == "ida"


def test_protein_coupling_manifest_exposes_p3_chemistry_diagnostics():
    steps = [
        ModificationStep(
            step_type=ModificationStepType.ACTIVATION,
            reagent_key="ech_activation",
            target_acs=ACSSiteType.HYDROXYL,
            product_acs=ACSSiteType.EPOXIDE,
            temperature=298.15,
            time=7200.0,
            reagent_concentration=100.0,
            ph=12.0,
        ),
        ModificationStep(
            step_type=ModificationStepType.PROTEIN_COUPLING,
            reagent_key="protein_a_coupling",
            target_acs=ACSSiteType.EPOXIDE,
            temperature=298.15,
            time=57600.0,
            reagent_concentration=0.02,
            ph=9.0,
        ),
    ]

    microsphere = ModificationOrchestrator().run(_make_contract(), steps)
    protein_result = microsphere.modification_history[1]
    diagnostics = protein_result.model_manifest.diagnostics

    assert diagnostics["sites_coupled_mol_per_particle"] >= 0.0
    assert 0.0 <= diagnostics["steric_accessibility_fraction"] <= 1.0
    assert diagnostics["activity_retention_factor"] == pytest.approx(0.60)
    assert diagnostics["denaturation_factor"] < 1.0
    assert diagnostics["effective_activity_retention"] < diagnostics["activity_retention_factor"]


def test_remaining_p3_templates_resolve_to_backend_steps():
    assert set(available_m2_templates()) >= {
        "epoxy_protein_a",
        "edc_nhs_protein_a",
        "hydrazide_protein_a",
        "vinyl_sulfone_protein_a",
        "nta_imac",
        "ida_imac",
    }

    for name in available_m2_templates():
        recipe = default_affinity_media_recipe()
        recipe.steps = [
            step for step in recipe.steps
            if step.stage != LifecycleStage.M2_FUNCTIONALIZATION
        ]
        recipe.steps.extend(m2_template_steps(name))
        resolved = resolve_lifecycle_inputs(recipe)
        assert not resolved.validation.blockers, name
        assert resolved.functionalization_steps, name


def test_nta_template_tracks_chelator_site_and_metal_loading():
    recipe = default_affinity_media_recipe()
    recipe.steps = [
        step for step in recipe.steps
        if step.stage != LifecycleStage.M2_FUNCTIONALIZATION
    ]
    recipe.steps.extend(m2_template_steps("nta_imac"))
    resolved = resolve_lifecycle_inputs(recipe)

    microsphere = ModificationOrchestrator().run(
        _make_contract(),
        resolved.functionalization_steps,
    )

    assert ACSSiteType.NTA in microsphere.acs_profiles
    nta = microsphere.acs_profiles[ACSSiteType.NTA]
    assert nta.accessible_sites > 0.0
    assert nta.metal_loaded_fraction > 0.99


def test_m2_calibration_entries_recompute_fmc_capacity_and_store_assay_state():
    fmc = FunctionalMediaContract(
        ligand_type="affinity",
        installed_ligand="Protein A",
        functional_ligand_density=1.2e-6,
        total_coupled_density=2.0e-6,
        estimated_q_max=0.24,
        reagent_accessible_area_per_bed_volume=1.0e5,
        ligand_accessible_area_per_bed_volume=8.0e4,
        capacity_area_basis="reagent_accessible",
        activity_retention=0.60,
    )
    store = CalibrationStore()
    store.add(CalibrationEntry(
        profile_key="m2_functionalization",
        parameter_name="activity_retention",
        measured_value=0.50,
        units="1",
        confidence="high",
        source_reference="synthetic M2 activity assay",
        target_module="M2",
        fit_method="assay_reference_mean",
    ))
    store.add(CalibrationEntry(
        profile_key="m2_functionalization",
        parameter_name="ligand_leaching_fraction",
        measured_value=0.02,
        units="1",
        confidence="medium",
        source_reference="synthetic leaching assay",
        target_module="M2",
        fit_method="assay_reference_mean",
    ))
    store.add(CalibrationEntry(
        profile_key="m2_functionalization",
        parameter_name="free_protein_wash_fraction",
        measured_value=0.03,
        units="1",
        confidence="medium",
        source_reference="synthetic wash assay",
        target_module="M2",
        fit_method="assay_reference_mean",
    ))

    calibrated, overrides = store.apply_to_fmc(fmc)

    assert calibrated.activity_retention == pytest.approx(0.50)
    assert calibrated.functional_ligand_density == pytest.approx(1.0e-6)
    assert calibrated.estimated_q_max == pytest.approx(0.20)
    assert calibrated.ligand_leaching_fraction == pytest.approx(0.02)
    assert calibrated.free_protein_wash_fraction == pytest.approx(0.03)
    assert any("DERIVED: estimated_q_max" in item for item in overrides)


def test_m2_assay_acceptance_gates_flag_leaching_and_wash_protein():
    from dpsim.core.validation import ValidationReport

    fmc = FunctionalMediaContract(
        ligand_type="affinity",
        installed_ligand="Protein A",
        functional_ligand_density=1e-6,
        ligand_leaching_fraction=0.06,
        free_protein_wash_fraction=0.02,
        activity_retention=0.25,
    )
    report = ValidationReport()

    _validate_m2_assay_acceptance(fmc, report)

    by_code = {issue.code: issue for issue in report.issues}
    assert by_code["M2_LIGAND_LEACHING"].severity.value == "blocker"
    assert by_code["M2_FREE_PROTEIN_WASH"].severity.value == "warning"
    assert by_code["M2_ACTIVITY_RETENTION_LOW"].severity.value == "warning"
