from types import SimpleNamespace

from dpsim.calibration import CalibrationEntry, CalibrationStore
from dpsim.core.validation import ValidationReport
from dpsim.datatypes import ModelEvidenceTier, ModelManifest
from dpsim.lifecycle.orchestrator import (
    _add_m3_calibration_uncertainty_validation,
    _apply_m3_calibration_domain_gates,
    _enforce_m3_media_evidence_cap,
    _m3_calibration_posterior_diagnostics,
)


def test_m3_evidence_is_capped_to_m2_media_contract():
    method = SimpleNamespace(
        model_manifest=ModelManifest(
            model_name="M3.method",
            evidence_tier=ModelEvidenceTier.VALIDATED_QUANTITATIVE,
        )
    )
    fmc = SimpleNamespace(
        model_manifest=ModelManifest(
            model_name="M2.FMC",
            evidence_tier=ModelEvidenceTier.QUALITATIVE_TREND,
        )
    )
    validation = ValidationReport()

    _enforce_m3_media_evidence_cap(
        method=method,
        fmc=fmc,
        validation=validation,
    )

    assert method.model_manifest.evidence_tier == ModelEvidenceTier.QUALITATIVE_TREND
    assert {issue.code for issue in validation.issues} == {"M3_EVIDENCE_CAPPED_TO_M2"}


def test_m3_calibration_domain_exit_downgrades_manifest():
    store = CalibrationStore()
    store.add(
        CalibrationEntry(
            profile_key="m3_binding",
            parameter_name="K_affinity",
            measured_value=1.0,
            units="m3/mol",
            target_module="M3",
            valid_domain={"flow_rate_m3_s": (1.0e-9, 2.0e-9)},
            posterior_uncertainty=0.1,
        )
    )
    load_step = SimpleNamespace(
        operation=SimpleNamespace(value="load"),
        buffer=SimpleNamespace(
            pH=7.4,
            temperature_K=298.15,
            conductivity_mS_cm=15.0,
            salt_concentration_mol_m3=150.0,
        ),
        flow_rate_m3_s=1.0e-8,
        feed_concentration_mol_m3=1.0,
    )
    method = SimpleNamespace(
        method_steps=[load_step],
        operability=SimpleNamespace(
            pressure_drop_Pa=5000.0,
            residence_time_s=240.0,
            particle_reynolds=0.1,
            axial_peclet=100.0,
            bed_compression_fraction=0.05,
        ),
        model_manifest=ModelManifest(
            model_name="M3.method",
            evidence_tier=ModelEvidenceTier.CALIBRATED_LOCAL,
        ),
    )
    fmc = SimpleNamespace(
        functional_ligand_density=1.0e-6,
        activity_retention=0.8,
        ligand_leaching_fraction=0.0,
        free_protein_wash_fraction=0.0,
        estimated_q_max=100.0,
    )
    validation = ValidationReport()

    diagnostics = _apply_m3_calibration_domain_gates(
        calibration_store=store,
        method=method,
        fmc=fmc,
        validation=validation,
    )

    assert diagnostics["calibration_domain_extrapolated"] is True
    assert diagnostics["calibration_domain_extrapolation_count"] == 1
    assert method.model_manifest.evidence_tier == ModelEvidenceTier.QUALITATIVE_TREND
    assert method.model_manifest.diagnostics["calibration_domain_extrapolations"][0]["parameter"] == "K_affinity"
    assert "M3_CALIBRATION_DOMAIN_EXTRAPOLATION" in {issue.code for issue in validation.warnings}


def test_m3_calibration_posteriors_produce_dbc_and_pressure_intervals():
    store = CalibrationStore()
    store.add(
        CalibrationEntry(
            profile_key="m3_binding",
            parameter_name="estimated_q_max",
            measured_value=100.0,
            units="mol/m3",
            target_module="M3",
            posterior_uncertainty=25.0,
        )
    )
    store.add(
        CalibrationEntry(
            profile_key="m3_binding",
            parameter_name="K_affinity",
            measured_value=1.0,
            units="m3/mol",
            target_module="M3",
            posterior_uncertainty=0.8,
        )
    )
    store.add(
        CalibrationEntry(
            profile_key="m3_binding",
            parameter_name="pressure_flow_slope_Pa_per_m3_s",
            measured_value=1.0e11,
            units="Pa/(m3/s)",
            target_module="M3",
            posterior_uncertainty=4.0e10,
        )
    )
    method = SimpleNamespace(
        step_results=[
            SimpleNamespace(flow_rate_m3_s=1.0e-8, pressure_drop_Pa=900.0),
        ],
    )
    fmc = SimpleNamespace(estimated_q_max=100.0)
    m3_result = SimpleNamespace(dbc_10pct=45.0)

    diagnostics = _m3_calibration_posterior_diagnostics(
        calibration_store=store,
        m3_result=m3_result,
        method=method,
        fmc=fmc,
    )

    assert diagnostics["calibration_posterior_count"] == 3
    assert diagnostics["dbc_10pct_calibration_sigma_mol_m3"] > 0.0
    assert diagnostics["dbc_10pct_calibration_p95_lower_mol_m3"] < 45.0
    assert diagnostics["dbc_10pct_calibration_p95_upper_mol_m3"] > 45.0
    assert diagnostics["pressure_flow_reference_pressure_sigma_Pa"] == 400.0

    validation = ValidationReport()
    _add_m3_calibration_uncertainty_validation(
        validation=validation,
        diagnostics=diagnostics,
    )

    codes = {issue.code for issue in validation.warnings}
    assert "M3_CALIBRATION_UNCERTAINTY_HIGH" in codes
    assert "M3_PRESSURE_FLOW_UNCERTAINTY_HIGH" in codes
