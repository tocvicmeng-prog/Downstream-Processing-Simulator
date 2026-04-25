from pathlib import Path

import pytest

from dpsim.calibration import CalibrationEntry, CalibrationStore
from dpsim.config import load_config
from dpsim.datatypes import RunContext
from dpsim.lifecycle import DownstreamProcessOrchestrator, resolve_lifecycle_inputs
from dpsim.core.process_recipe import default_affinity_media_recipe
from dpsim.module3_performance.method import ChromatographyOperation


def test_recipe_resolver_emits_full_m3_method_steps():
    resolved = resolve_lifecycle_inputs(default_affinity_media_recipe())

    assert [step.operation for step in resolved.m3_method_steps] == [
        ChromatographyOperation.PACK,
        ChromatographyOperation.EQUILIBRATE,
        ChromatographyOperation.LOAD,
        ChromatographyOperation.WASH,
        ChromatographyOperation.ELUTE,
    ]
    assert "M3.equilibrate.conductivity" in resolved.resolved_parameters
    assert "M3.elute.gradient_end_pH" in resolved.resolved_parameters
    assert resolved.column.diameter == pytest.approx(0.01)
    assert resolved.column.bed_height == pytest.approx(0.10)


def test_lifecycle_m3_uses_method_result_and_keeps_breakthrough_alias(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    params = load_config(repo_root / "configs" / "fast_smoke.toml")

    result = DownstreamProcessOrchestrator(output_dir=tmp_path).run(
        params=params,
        propagate_dsd=False,
    )

    assert result.m3_method is not None
    assert result.m3_breakthrough is result.m3_method.load_breakthrough
    m3_node = result.graph.nodes["M3"]
    diagnostics = m3_node.diagnostics
    assert diagnostics["method_steps"] == [
        "pack",
        "equilibrate",
        "load",
        "wash",
        "elute",
    ]
    assert diagnostics["protein_a_elution_pH"] == pytest.approx(3.5)
    assert diagnostics["protein_a_cycle_lifetime_to_70pct"] >= 1.0
    assert diagnostics["flow_maldistribution_risk"] in {"low", "medium", "high"}
    assert "loaded_elution_recovery_fraction" in diagnostics
    assert "loaded_elution_mass_balance_error" in diagnostics
    assert diagnostics["column_theoretical_plates"] > 0.0
    assert diagnostics["column_hetp_m"] > 0.0
    assert diagnostics["impurity_clearance_risk"] in {"low", "medium", "high"}
    assert m3_node.manifest.model_name == "M3.method.ProteinAOperation"


def test_lifecycle_m3_consumes_protein_a_cycling_calibration(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    params = load_config(repo_root / "configs" / "fast_smoke.toml")
    store = CalibrationStore()
    store.add(CalibrationEntry(
        profile_key="protein_a_cycle_study",
        parameter_name="protein_a_cycle_loss_fraction",
        measured_value=0.02,
        units="fraction/cycle",
        confidence="medium",
        source_reference="synthetic cycling study",
        target_module="M3",
        measurement_type="capacity_loss_per_cycle",
    ))
    store.add(CalibrationEntry(
        profile_key="protein_a_leaching",
        parameter_name="protein_a_leaching_fraction_per_cycle",
        measured_value=0.015,
        units="fraction/cycle",
        confidence="medium",
        source_reference="synthetic leaching ELISA",
        target_module="M3",
        measurement_type="protein_a_leaching",
    ))

    result = DownstreamProcessOrchestrator(output_dir=tmp_path).run(
        params=params,
        run_context=RunContext(calibration_store=store),
        propagate_dsd=False,
    )

    diagnostics = result.graph.nodes["M3"].diagnostics
    assert diagnostics["m3_process_state"]["protein_a_cycle_loss_fraction"] == pytest.approx(0.02)
    assert diagnostics["protein_a_ligand_leaching_fraction_per_cycle"] == pytest.approx(0.015)
    assert result.m3_method.protein_a.leaching_risk == "medium"
