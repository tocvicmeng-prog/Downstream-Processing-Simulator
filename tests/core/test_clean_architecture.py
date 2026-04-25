import pytest

from dpsim.core import Quantity, ValidationReport, ValidationSeverity
from dpsim.core.process_recipe import LifecycleStage, default_affinity_media_recipe
from dpsim.core.result_graph import ResultGraph, ResultNode
from dpsim.datatypes import M1ExportContract, ModelEvidenceTier, ModelManifest
from dpsim.lifecycle import default_protein_a_functionalization_steps
from dpsim.module2_functionalization import (
    ModificationOrchestrator,
    build_functional_media_contract,
)
from dpsim.module2_functionalization.modification_steps import ModificationStepType


def test_quantity_converts_common_lab_units_to_si():
    assert Quantity(1.0, "mL/min").to_si().unit == "m3/s"
    assert Quantity(1.0, "mL/min").to_si().value == pytest.approx(1e-6 / 60.0)
    assert Quantity(25.0, "degC").as_unit("K").value == pytest.approx(298.15)
    assert Quantity(100.0, "um").to_si().value == pytest.approx(100e-6)
    assert Quantity(60.0, "K/min").to_si().value == pytest.approx(1.0)


def test_default_recipe_has_all_lifecycle_stages():
    recipe = default_affinity_media_recipe()
    stages = {step.stage for step in recipe.steps}
    assert LifecycleStage.M1_FABRICATION in stages
    assert LifecycleStage.M2_FUNCTIONALIZATION in stages
    assert LifecycleStage.M3_PERFORMANCE in stages


def test_result_graph_rolls_up_weakest_evidence():
    graph = ResultGraph()
    graph.add_node(
        ResultNode(
            node_id="M1",
            stage="M1",
            label="fabrication",
            manifest=ModelManifest(
                model_name="M1",
                evidence_tier=ModelEvidenceTier.SEMI_QUANTITATIVE,
            ),
        )
    )
    graph.add_node(
        ResultNode(
            node_id="M2",
            stage="M2",
            label="functionalization",
            manifest=ModelManifest(
                model_name="M2",
                evidence_tier=ModelEvidenceTier.QUALITATIVE_TREND,
            ),
        )
    )
    graph.add_edge("M1", "M2", "contract")
    assert graph.weakest_evidence_tier() == ModelEvidenceTier.QUALITATIVE_TREND
    assert graph.as_summary()["weakest_evidence_tier"] == "qualitative_trend"


def test_validation_report_detects_blockers():
    report = ValidationReport()
    report.add(ValidationSeverity.WARNING, "W1", "warning")
    assert report.ok_for_decision
    report.add(ValidationSeverity.BLOCKER, "B1", "blocker")
    assert not report.ok_for_decision
    assert len(report.blockers) == 1


def test_default_protein_a_steps_are_backend_modification_steps():
    steps = default_protein_a_functionalization_steps()
    assert [s.reagent_key for s in steps] == [
        "ech_activation",
        "wash_buffer",
        "protein_a_coupling",
        "wash_buffer",
        "ethanolamine_quench",
        "wash_buffer",
    ]
    assert [s.step_type for s in steps].count(ModificationStepType.WASHING) == 3


def test_m2_washing_tracks_residual_reagent_contract():
    contract = M1ExportContract(
        bead_radius=50e-6,
        bead_d32=100e-6,
        bead_d50=100e-6,
        pore_size_mean=100e-9,
        pore_size_std=20e-9,
        porosity=0.7,
        l2_model_tier="empirical_calibrated",
        mesh_size_xi=10e-9,
        p_final=0.1,
        primary_crosslinker="genipin",
        nh2_bulk_concentration=100.0,
        oh_bulk_concentration=500.0,
        G_DN=10000.0,
        E_star=30000.0,
        model_used="phenomenological",
        c_agarose=42.0,
        c_chitosan=18.0,
        DDA=0.9,
        trust_level="CAUTION",
    )
    microsphere = ModificationOrchestrator().run(
        contract,
        default_protein_a_functionalization_steps(),
    )
    fmc = build_functional_media_contract(microsphere)

    assert "ech_activation" in fmc.residual_reagent_concentrations
    assert "ethanolamine_quench" in fmc.residual_reagent_concentrations
    assert all(value >= 0.0 for value in fmc.residual_reagent_concentrations.values())
    assert fmc.validate_units() == []
