import pytest

from dpsim.module3_performance.hydrodynamics import ColumnGeometry
from dpsim.module3_performance.method import (
    BufferCondition,
    ChromatographyMethodResult,
    ChromatographyMethodStep,
    ChromatographyOperation,
    default_protein_a_method_steps,
    evaluate_column_operability,
    evaluate_protein_a_performance,
    run_chromatography_method,
)


def test_default_protein_a_method_has_full_operation_sequence():
    steps = default_protein_a_method_steps(
        flow_rate=1.0e-8,
        feed_concentration=1.0,
        feed_duration=120.0,
        total_time=240.0,
    )

    assert [step.operation for step in steps] == [
        ChromatographyOperation.PACK,
        ChromatographyOperation.EQUILIBRATE,
        ChromatographyOperation.LOAD,
        ChromatographyOperation.WASH,
        ChromatographyOperation.ELUTE,
    ]
    assert steps[2].buffer.pH == pytest.approx(7.4)
    assert steps[4].gradient_field == "ph"
    assert steps[4].gradient_end == pytest.approx(3.5)


def test_run_chromatography_method_wraps_breakthrough_and_operability():
    column = ColumnGeometry(bed_height=0.04)
    steps = default_protein_a_method_steps(
        flow_rate=1.0e-8,
        feed_concentration=1.0,
        feed_duration=80.0,
        total_time=160.0,
    )
    result = run_chromatography_method(
        column,
        method_steps=steps,
        n_z=12,
        max_pressure_Pa=3.0e5,
        pump_pressure_limit_Pa=3.0e5,
    )

    assert isinstance(result, ChromatographyMethodResult)
    assert result.load_breakthrough is not None
    assert result.loaded_elution is not None
    assert result.load_breakthrough.dbc_10pct >= 0.0
    assert result.load_breakthrough.q_profile_final is not None
    assert result.loaded_elution.mass_initial_bound_mol >= 0.0
    assert result.loaded_elution.mass_balance_error >= 0.0
    assert result.operability.pressure_drop_Pa > 0.0
    assert result.operability.axial_peclet > 0.0
    assert result.column_efficiency.theoretical_plates > 0.0
    assert result.column_efficiency.hetp_m > 0.0
    assert result.impurity_clearance.wash_column_volumes >= 0.0
    assert result.impurity_clearance.risk in {"low", "medium", "high"}
    assert result.protein_a.K_a_load_m3_mol > result.protein_a.K_a_elution_m3_mol
    assert result.protein_a.predicted_elution_recovery_fraction >= 0.0
    assert result.model_manifest.model_name == "M3.method.ProteinAOperation"
    assert "method_steps" in result.model_manifest.diagnostics
    assert "loaded_elution_recovery_fraction" in result.model_manifest.diagnostics
    assert "column_efficiency_plates" in result.model_manifest.diagnostics
    assert "impurity_clearance_risk" in result.model_manifest.diagnostics


def test_column_operability_flags_pressure_compression_and_flow_domain():
    column = ColumnGeometry(
        diameter=0.005,
        bed_height=0.20,
        particle_diameter=25e-6,
        bed_porosity=0.32,
        E_star=8000.0,
    )

    report = evaluate_column_operability(
        column,
        flow_rate=2.0e-7,
        step_name="stress load",
        max_pressure_Pa=2.0e4,
        pump_pressure_limit_Pa=5.0e4,
    )

    assert report.pressure_drop_Pa > report.max_pressure_Pa
    assert report.warnings or report.blockers
    assert report.bed_compression_fraction > 0.0
    assert report.particle_reynolds >= 0.0
    assert report.maldistribution_risk in {"low", "medium", "high"}


def test_protein_a_report_responds_to_alkaline_regeneration():
    column = ColumnGeometry()
    steps = default_protein_a_method_steps(feed_duration=60.0, total_time=120.0)
    steps.append(
        ChromatographyMethodStep(
            name="NaOH regeneration",
            operation=ChromatographyOperation.REGENERATE,
            duration_s=3600.0,
            flow_rate_m3_s=1.0e-8,
            buffer=BufferCondition(name="NaOH CIP", pH=13.0, conductivity_mS_cm=40.0),
        )
    )

    report = evaluate_protein_a_performance(
        column=column,
        method_steps=steps,
        process_state={"K_affinity": 1.0e5},
    )

    assert report.alkaline_degradation_fraction_per_cycle > 0.0
    assert report.cycle_lifetime_to_70pct_capacity < 200.0
    assert any("Alkaline degradation" in warning for warning in report.warnings)


def test_protein_a_cycling_calibration_overrides_degradation_and_leaching():
    column = ColumnGeometry()
    steps = default_protein_a_method_steps(feed_duration=60.0, total_time=120.0)

    report = evaluate_protein_a_performance(
        column=column,
        method_steps=steps,
        process_state={
            "protein_a_cycle_loss_fraction": 0.02,
            "protein_a_leaching_fraction_per_cycle": 0.015,
            "protein_a_cycle_lifetime_to_70pct": 42.0,
        },
    )

    assert report.ligand_leaching_fraction_per_cycle == pytest.approx(0.015)
    assert report.cycle_lifetime_to_70pct_capacity == pytest.approx(42.0)
    assert report.leaching_risk == "medium"
