import pytest

from dpsim.assay_record import AssayKind, AssayRecord, Replicate
from dpsim.calibration import (
    CalibrationDataset,
    CalibrationEntry,
    CalibrationFit,
    CalibrationStore,
    QualityGateConfig,
    check_calibration_applicability,
    evaluate_assay_record,
    evaluate_calibration_entry,
)


def _assay(**conditions):
    return AssayRecord(
        record_id="A-001",
        kind=AssayKind.PRESSURE_FLOW_CURVE,
        units="Pa",
        replicates=[
            Replicate(100.0),
            Replicate(105.0),
            Replicate(95.0),
        ],
        process_conditions={
            "temperature_C": 25.0,
            "ph": 7.0,
            "salt_concentration_M": 0.15,
            "target_molecule": "IgG",
            **conditions,
        },
    )


def test_assay_quality_gate_passes_replicated_matching_record():
    report = evaluate_assay_record(
        _assay(),
        QualityGateConfig(
            required_units=("Pa",),
            target_molecule="IgG",
            temperature_C=25.0,
            ph=7.0,
            salt_concentration_M=0.15,
        ),
    )
    assert report.passed
    assert report.metrics["n_replicates"] == 3


def test_assay_quality_gate_rejects_low_replicates_and_wrong_units():
    record = AssayRecord(
        record_id="A-002",
        kind=AssayKind.DYNAMIC_BINDING_CAPACITY,
        units="mg/mL",
        replicates=[Replicate(10.0)],
    )
    report = evaluate_assay_record(record, QualityGateConfig(required_units=("mol/m3",)))
    assert not report.passed
    assert {issue.code for issue in report.errors()} == {"min_replicates", "required_units"}


def test_calibration_entry_requires_domain_for_tier_promotion():
    entry = CalibrationEntry(
        profile_key="m3_binding",
        parameter_name="estimated_q_max",
        measured_value=100.0,
        units="mol/m3",
        replicates=3,
    )
    report = evaluate_calibration_entry(entry)
    assert not report.passed
    assert "valid_domain_missing" in {issue.code for issue in report.errors()}


def test_applicability_checks_target_and_numeric_domain():
    entry = CalibrationEntry(
        profile_key="m3_pressure",
        parameter_name="K_geom",
        measured_value=2.0e-12,
        units="m2",
        target_molecule="IgG",
        valid_domain={"flow_rate_mL_min": (0.2, 2.0)},
        replicates=3,
    )
    ok = check_calibration_applicability(
        entry,
        target_molecule="IgG",
        conditions={"flow_rate_mL_min": 1.0},
    )
    bad = check_calibration_applicability(
        entry,
        target_molecule="BSA",
        conditions={"flow_rate_mL_min": 3.0},
    )
    assert ok.applicable
    assert not bad.applicable
    assert len(bad.reasons) == 2


def test_calibration_store_hash_is_order_stable():
    a = CalibrationEntry("p", "x", 1.0, "1", source_reference="a")
    b = CalibrationEntry("p", "y", 2.0, "1", source_reference="b")
    s1 = CalibrationStore()
    s2 = CalibrationStore()
    s1.add(a)
    s1.add(b)
    s2.add(b)
    s2.add(a)
    assert s1.content_hash() == s2.content_hash()


def test_calibration_dataset_and_fit_hashes_are_deterministic():
    dataset = CalibrationDataset(
        dataset_id="D1",
        assay_ids=("A1", "A2"),
        assay_kind="pressure_flow_curve",
    )
    fit = CalibrationFit(
        fit_id="F1",
        parameter_name="K_geom",
        value=2.0e-12,
        units="m2",
        fit_method="least_squares",
        source_assay_ids=("A1", "A2"),
    )
    assert len(dataset.content_hash) == 64
    assert len(fit.content_hash) == 64
    assert fit.to_dict()["source_assay_ids"] == ["A1", "A2"]
