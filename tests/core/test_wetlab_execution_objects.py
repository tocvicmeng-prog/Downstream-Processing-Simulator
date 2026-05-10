import pytest

from dpsim.core.chromatography_trace import (
    DetectorTrace,
    FractionCollection,
    align_traces,
)
from dpsim.core.qc_checkpoint import (
    DEFAULT_QC_CHECKPOINTS,
    QCCheckpoint,
    QCCheckpointKind,
    missing_required_checkpoints,
)


def test_qc_checkpoint_satisfaction_requires_status_and_assay_id():
    missing = QCCheckpoint(
        "qc_pressure",
        QCCheckpointKind.PRESSURE_FLOW_MEASURED,
        "pressure_flow_curve",
        "M3",
        status="passed",
    )
    passed = QCCheckpoint(
        "qc_pressure",
        QCCheckpointKind.PRESSURE_FLOW_MEASURED,
        "pressure_flow_curve",
        "M3",
        status="passed",
        assay_record_id="PF-001",
    )
    assert not missing.satisfied
    assert passed.satisfied
    assert passed.to_dict()["satisfied"] is True


def test_default_qc_checkpoints_cover_dsd_pressure_and_breakthrough():
    kinds = {checkpoint.kind for checkpoint in DEFAULT_QC_CHECKPOINTS}
    assert QCCheckpointKind.DSD_MEASURED in kinds
    assert QCCheckpointKind.PRESSURE_FLOW_MEASURED in kinds
    assert QCCheckpointKind.BREAKTHROUGH_MEASURED in kinds
    assert missing_required_checkpoints(DEFAULT_QC_CHECKPOINTS)


def test_detector_trace_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        DetectorTrace("bad", "uv", (0.0, 1.0), (1.0,), "mAU")


def test_trace_alignment_computes_residuals_on_measured_timebase():
    predicted = DetectorTrace("pred", "uv", (0.0, 1.0, 2.0), (0.0, 1.0, 2.0), "mAU")
    measured = DetectorTrace("meas", "uv", (0.5, 1.5), (0.6, 1.4), "mAU")
    alignment = align_traces(predicted, measured)
    assert alignment.n_points == 2
    assert alignment.max_abs_error == pytest.approx(0.1)
    assert alignment.rmse == pytest.approx(0.1)


def test_fraction_collection_is_exportable():
    fraction = FractionCollection("F1", 10.0, 20.0, 1.5, pool="elution", assay_record_ids=("A1",))
    assert fraction.to_dict()["assay_record_ids"] == ["A1"]
