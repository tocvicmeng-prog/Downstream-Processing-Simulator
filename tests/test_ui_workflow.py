"""Tests for P6 lifecycle-first UI workflow helpers."""

from __future__ import annotations

from types import SimpleNamespace

from dpsim.core.process_recipe import LifecycleStage, default_affinity_media_recipe
from dpsim.core.result_graph import ResultGraph, ResultNode
from dpsim.core.validation import ValidationReport, ValidationSeverity
from dpsim.datatypes import ModelEvidenceTier, ModelManifest
from dpsim.lifecycle.orchestrator import DownstreamLifecycleResult
from dpsim.visualization.ui_workflow import (
    WORKFLOW_STATUS_COMPLETE,
    build_lifecycle_workflow_state,
    breakthrough_curve_rows,
    calibration_comparison_rows,
    calibration_overlay_chart_rows,
    calibration_status_rows,
    dsd_distribution_chart_rows,
    dsd_variant_chart_rows,
    evidence_ladder_rows,
    ligand_capacity_chart_rows,
    lifecycle_result_summary_rows,
    lifecycle_run_history_rows,
    pressure_profile_rows,
    process_recipe_protocol_markdown,
    scientific_diagnostic_rows,
    stage_recipe_snapshot_rows,
    store_lifecycle_result,
    update_target_profile,
    validation_report_rows,
)


class _FakeCalibrationStore:
    def __init__(self, entries):
        self.entries = entries

    def __len__(self):
        return len(self.entries)


def test_default_recipe_builds_complete_definition_workflow_steps():
    workflow = build_lifecycle_workflow_state(default_affinity_media_recipe(), {})
    by_id = {step.step_id: step for step in workflow}

    assert by_id["target"].status == WORKFLOW_STATUS_COMPLETE
    assert by_id["m1_recipe"].status == WORKFLOW_STATUS_COMPLETE
    assert by_id["m2_recipe"].status == WORKFLOW_STATUS_COMPLETE
    assert by_id["m3_method"].status == WORKFLOW_STATUS_COMPLETE
    assert by_id["run"].status == "ready"


def test_workflow_marks_results_validation_and_calibration_complete():
    report = ValidationReport()
    report.add(
        ValidationSeverity.WARNING,
        "M3_DOMAIN",
        "Example extrapolation.",
        module="M3",
    )
    store = {
        "result": object(),
        "validation_report": report,
        "_cal_store": _FakeCalibrationStore(
            [
                SimpleNamespace(
                    profile_key="protein_a_coupling",
                    parameter_name="estimated_q_max",
                    measured_value=120.0,
                    units="mol/m3",
                    confidence="measured",
                    measurement_type="static_binding",
                    source_reference="bench assay",
                )
            ]
        ),
    }

    by_id = {
        step.step_id: step
        for step in build_lifecycle_workflow_state(default_affinity_media_recipe(), store)
    }

    assert by_id["run"].status == WORKFLOW_STATUS_COMPLETE
    assert by_id["validation"].status == WORKFLOW_STATUS_COMPLETE
    assert by_id["calibration"].status == WORKFLOW_STATUS_COMPLETE


def test_validation_report_rows_preserve_backend_issue_fields():
    report = ValidationReport()
    report.add(
        ValidationSeverity.BLOCKER,
        "M2_REAGENT_UNKNOWN",
        "Unknown reagent.",
        module="M2",
        recommendation="Select a validated reagent profile.",
    )

    rows = validation_report_rows(report)

    assert rows == [
        {
            "severity": "blocker",
            "module": "M2",
            "code": "M2_REAGENT_UNKNOWN",
            "message": "Unknown reagent.",
            "recommendation": "Select a validated reagent profile.",
        }
    ]


def test_update_target_profile_writes_recipe_quantities_with_ui_provenance():
    recipe = default_affinity_media_recipe()

    update_target_profile(
        recipe,
        name="Large-pore Protein A screening media",
        ligand="alkali-stable Protein A",
        analyte="mAb",
        bead_d50_um=90.0,
        pore_nm=180.0,
        min_modulus_kPa=25.0,
        max_pressure_bar=2.5,
        max_residual_oil_fraction=0.002,
        max_residual_surfactant_kg_m3=0.1,
        notes="screening target",
    )

    assert recipe.target.name == "Large-pore Protein A screening media"
    assert recipe.target.target_ligand == "alkali-stable Protein A"
    assert recipe.target.target_analyte == "mAb"
    assert recipe.target.bead_d50.value == 90.0
    assert recipe.target.bead_d50.unit == "um"
    assert recipe.target.bead_d50.source == "streamlit_ui"
    assert recipe.target.max_residual_oil_volume_fraction.upper == 1.0


def test_store_lifecycle_result_sets_workflow_and_legacy_aliases():
    result = DownstreamLifecycleResult(
        recipe=default_affinity_media_recipe(),
        graph=ResultGraph(),
        validation=ValidationReport(),
        m1_result=object(),
        m2_microsphere=object(),
        m3_breakthrough=object(),
    )
    store = {}

    store_lifecycle_result(store, result)

    assert store["lifecycle_result"] is result
    assert store["validation_report"] is result.validation
    assert store["result"] is result.m1_result
    assert store["m2_result"] is result.m2_microsphere
    assert store["m3_result_bt"] is result.m3_breakthrough
    assert lifecycle_run_history_rows(store)[0]["run_id"] == "run-1"


def test_lifecycle_result_summary_rows_include_evidence_and_validation_counts():
    report = ValidationReport()
    report.add(
        ValidationSeverity.WARNING,
        "M3_DOMAIN",
        "Example extrapolation.",
        module="M3",
    )
    result = DownstreamLifecycleResult(
        recipe=default_affinity_media_recipe(),
        graph=ResultGraph(),
        validation=report,
    )

    rows = lifecycle_result_summary_rows(result)
    by_metric = {row["metric"]: row["value"] for row in rows}

    assert by_metric["Weakest evidence tier"] == "unsupported"
    assert by_metric["Validation blockers"] == "0"
    assert by_metric["Validation warnings"] == "1"


def test_scientific_diagnostic_rows_expose_graph_metrics_with_wet_lab_followup():
    graph = ResultGraph()
    graph.add_node(
        ResultNode(
            node_id="M3",
            stage="M3_performance",
            label="Protein A method",
            diagnostics={
                "dbc_10pct": 42.0,
                "method_pressure_drop_Pa": 150000.0,
                "method_bed_compression_fraction": 0.02,
            },
        )
    )
    result = DownstreamLifecycleResult(
        recipe=default_affinity_media_recipe(),
        graph=graph,
        validation=ValidationReport(),
    )

    rows = scientific_diagnostic_rows(result)
    by_metric = {row["metric"]: row for row in rows}

    assert by_metric["DBC10"]["value"] == "42 mol/m3"
    assert by_metric["Pressure drop"]["value"] == "1.5 bar"
    assert "Breakthrough curve" in by_metric["DBC10"]["wet_lab_followup"]


def test_calibration_comparison_rows_compare_loaded_assays_to_graph_metrics():
    graph = ResultGraph()
    graph.add_node(
        ResultNode(
            node_id="M3",
            stage="M3_performance",
            label="Protein A method",
            diagnostics={
                "dbc_10pct": 40.0,
                "method_pressure_drop_Pa": 200000.0,
            },
        )
    )
    result = DownstreamLifecycleResult(
        recipe=default_affinity_media_recipe(),
        graph=graph,
        validation=ValidationReport(),
    )
    store = {
        "lifecycle_result": result,
        "_cal_store": _FakeCalibrationStore(
            [
                SimpleNamespace(
                    profile_key="m3_binding",
                    parameter_name="DBC10",
                    measured_value=42.0,
                    units="mol/m3",
                    confidence="measured",
                    measurement_type="dynamic_binding_capacity_10pct",
                    source_reference="run 12",
                ),
                SimpleNamespace(
                    profile_key="m3_pressure",
                    parameter_name="pressure_drop",
                    measured_value=2.0,
                    units="bar",
                    confidence="measured",
                    measurement_type="pressure_flow_curve",
                    source_reference="run 13",
                ),
            ]
        ),
    }

    rows = calibration_comparison_rows(store)

    assert rows[0]["simulated"] == "40 mol/m3"
    assert rows[0]["relative_delta_pct"] == "-4.762"
    assert rows[0]["assessment"] == "Agreement within screening tolerance."
    assert rows[1]["simulated"] == "2 bar"


def test_stage_recipe_snapshot_rows_show_operation_and_qc_counts():
    recipe = default_affinity_media_recipe()

    rows = stage_recipe_snapshot_rows(recipe, LifecycleStage.M2_FUNCTIONALIZATION)

    assert any(row["operation"] == "couple_ligand" for row in rows)
    assert all("qc_items" in row for row in rows)


def test_dsd_distribution_and_variant_chart_rows_are_unit_converted():
    result = DownstreamLifecycleResult(
        recipe=default_affinity_media_recipe(),
        graph=ResultGraph(),
        validation=ValidationReport(),
        m1_contract=SimpleNamespace(
            bead_size_distribution=SimpleNamespace(
                diameter_bins_m=[50e-6, 100e-6],
                volume_fraction=[0.25, 0.75],
                number_density=[1.0e9, 2.0e9],
                volume_cdf=[0.25, 1.0],
                source="test_dsd",
            )
        ),
        dsd_variants=[
            SimpleNamespace(
                quantile=0.5,
                mass_fraction=1.0,
                bead_diameter_m=100e-6,
                estimated_q_max_mol_m3=55.0,
                pressure_drop_Pa=150000.0,
                bed_compression_fraction=0.03,
                dbc_10pct_mol_m3=40.0,
                representative_source="quantile",
            )
        ],
    )

    dsd_rows = dsd_distribution_chart_rows(result)
    variant_rows = dsd_variant_chart_rows(result)

    assert dsd_rows[0]["bead_diameter_um"] == 50.0
    assert dsd_rows[1]["volume_cdf"] == 1.0
    assert variant_rows[0]["bead_diameter_um"] == 100.0
    assert variant_rows[0]["pressure_bar"] == 1.5


def test_breakthrough_pressure_and_ligand_chart_rows_from_lifecycle_payloads():
    graph = ResultGraph()
    graph.add_node(
        ResultNode(
            node_id="M2",
            stage="M2_functionalization",
            label="M2",
            diagnostics={
                "activity_retention": 0.8,
                "functional_ligand_density": 1.0e-6,
                "estimated_q_max": 60.0,
            },
        )
    )
    graph.add_node(
        ResultNode(
            node_id="M3",
            stage="M3_performance",
            label="M3",
            diagnostics={
                "dbc_10pct": 42.0,
                "protein_a_q_max_mol_m3": 65.0,
            },
        )
    )
    result = DownstreamLifecycleResult(
        recipe=default_affinity_media_recipe(),
        graph=graph,
        validation=ValidationReport(),
        m3_breakthrough=SimpleNamespace(
            time=[0.0, 60.0, 120.0],
            C_outlet=[0.0, 0.5, 1.0],
            uv_signal=[0.0, 10.0, 20.0],
        ),
        m3_method=SimpleNamespace(
            loaded_elution=None,
            step_results=[
                SimpleNamespace(
                    name="Load",
                    operation=SimpleNamespace(value="load"),
                    pressure_drop_Pa=250000.0,
                    bed_compression_fraction=0.04,
                    residence_time_s=120.0,
                    column_volumes=2.0,
                    flow_rate_m3_s=1.0e-8,
                )
            ],
        ),
    )

    breakthrough_rows = breakthrough_curve_rows(result)
    pressure_rows = pressure_profile_rows(result)
    ligand_rows = ligand_capacity_chart_rows(result)

    assert breakthrough_rows[-1]["normalized_concentration"] == 1.0
    assert pressure_rows[0]["pressure_bar"] == 2.5
    assert pressure_rows[0]["flow_mL_min"] == 0.6
    assert {row["metric"] for row in ligand_rows} >= {"Activity retention", "DBC10"}


def test_calibration_overlay_chart_rows_emit_measured_and_simulated_pairs():
    graph = ResultGraph()
    graph.add_node(
        ResultNode(
            node_id="M3",
            stage="M3_performance",
            label="Protein A method",
            diagnostics={"method_pressure_drop_Pa": 200000.0},
        )
    )
    result = DownstreamLifecycleResult(
        recipe=default_affinity_media_recipe(),
        graph=graph,
        validation=ValidationReport(),
    )
    store = {
        "lifecycle_result": result,
        "_cal_store": _FakeCalibrationStore(
            [
                SimpleNamespace(
                    profile_key="m3_pressure",
                    parameter_name="pressure_drop",
                    measured_value=2.0,
                    units="bar",
                    confidence="measured",
                    measurement_type="pressure_flow_curve",
                    source_reference="run 13",
                )
            ]
        ),
    }

    rows = calibration_overlay_chart_rows(store)

    assert [row["series"] for row in rows] == ["measured", "simulated"]
    assert rows[1]["value"] == 2.0
    assert rows[1]["units"] == "bar"


def test_evidence_ladder_rows_from_lifecycle_graph():
    graph = ResultGraph()
    graph.add_node(
        ResultNode(
            node_id="M3",
            stage="M3_performance",
            label="Protein A method",
            manifest=ModelManifest(
                model_name="M3.method.ProteinAOperation",
                evidence_tier=ModelEvidenceTier.QUALITATIVE_TREND,
                calibration_ref="CAL-DBC10",
                assumptions=["LRM", "Protein A activity retention estimated"],
            ),
            wet_lab_caveats=["DBC requires local breakthrough calibration."],
        )
    )
    result = DownstreamLifecycleResult(
        recipe=default_affinity_media_recipe(),
        graph=graph,
        validation=ValidationReport(),
    )

    rows = evidence_ladder_rows(result)

    assert rows[0]["node"] == "M3"
    assert rows[0]["evidence_tier"] == "qualitative_trend"
    assert rows[0]["calibration_ref"] == "CAL-DBC10"
    assert "breakthrough calibration" in rows[0]["wet_lab_caveats"]


def test_protocol_export_contains_target_and_all_lifecycle_sections():
    text = process_recipe_protocol_markdown(default_affinity_media_recipe())

    assert "# DPSim Wet-Lab Protocol Outline" in text
    assert "## Target Product Profile" in text
    assert "## M1_fabrication" in text
    assert "## M2_functionalization" in text
    assert "## M3_performance" in text
    assert "## Acceptance Criteria" in text
    assert "Hold/release gate" in text
    assert "Required record" in text
    assert "Protein A coupling" in text
    assert "Pack analytical Protein A affinity column" in text


def test_calibration_status_rows_from_session_store():
    store = {
        "_cal_store": _FakeCalibrationStore(
            [
                SimpleNamespace(
                    profile_key="m3_breakthrough",
                    parameter_name="DBC10",
                    measured_value=42.0,
                    units="mol/m3",
                    confidence="measured",
                    measurement_type="breakthrough_curve",
                    source_reference="run 12",
                )
            ]
        )
    }

    rows = calibration_status_rows(store)

    assert rows[0]["profile"] == "m3_breakthrough"
    assert rows[0]["parameter"] == "DBC10"
    assert rows[0]["confidence"] == "measured"
