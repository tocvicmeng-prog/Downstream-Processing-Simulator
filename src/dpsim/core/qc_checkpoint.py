"""Wet-lab QC checkpoint model for executable downstream workflows."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class QCCheckpointKind(Enum):
    DSD_MEASURED = "dsd_measured"
    RESIDUAL_OIL_SURFACTANT_MEASURED = "residual_oil_surfactant_measured"
    LIGAND_DENSITY_MEASURED = "ligand_density_measured"
    RESIDUAL_REAGENT_MEASURED = "residual_reagent_measured"
    PRESSURE_FLOW_MEASURED = "pressure_flow_measured"
    BREAKTHROUGH_MEASURED = "breakthrough_measured"
    LEACHING_CYCLE_TEST_MEASURED = "leaching_cycle_test_measured"


@dataclass(frozen=True)
class QCCheckpoint:
    """One required wet-lab measurement gate."""

    checkpoint_id: str
    kind: QCCheckpointKind
    required_assay_kind: str
    stage: str
    acceptance_criteria: str = ""
    assay_record_id: str = ""
    status: str = "missing"
    notes: str = ""

    @property
    def satisfied(self) -> bool:
        return self.status in {"passed", "accepted"} and bool(self.assay_record_id)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["kind"] = self.kind.value
        data["satisfied"] = self.satisfied
        return data


DEFAULT_QC_CHECKPOINTS: tuple[QCCheckpoint, ...] = (
    QCCheckpoint("qc_dsd", QCCheckpointKind.DSD_MEASURED, "droplet_size_distribution", "M1"),
    QCCheckpoint("qc_residuals", QCCheckpointKind.RESIDUAL_OIL_SURFACTANT_MEASURED, "residual_oil/residual_surfactant", "M1"),
    QCCheckpoint("qc_ligand_density", QCCheckpointKind.LIGAND_DENSITY_MEASURED, "ligand_density", "M2"),
    QCCheckpoint("qc_residual_reagent", QCCheckpointKind.RESIDUAL_REAGENT_MEASURED, "residual_reagent", "M2"),
    QCCheckpoint("qc_pressure_flow", QCCheckpointKind.PRESSURE_FLOW_MEASURED, "pressure_flow_curve", "M3"),
    QCCheckpoint("qc_breakthrough", QCCheckpointKind.BREAKTHROUGH_MEASURED, "dynamic_binding_capacity", "M3"),
    QCCheckpoint("qc_leaching", QCCheckpointKind.LEACHING_CYCLE_TEST_MEASURED, "ligand_leaching", "M3"),
)


def missing_required_checkpoints(
    checkpoints: tuple[QCCheckpoint, ...] | list[QCCheckpoint],
) -> tuple[QCCheckpoint, ...]:
    """Return unsatisfied checkpoints."""
    return tuple(checkpoint for checkpoint in checkpoints if not checkpoint.satisfied)


__all__ = [
    "DEFAULT_QC_CHECKPOINTS",
    "QCCheckpoint",
    "QCCheckpointKind",
    "missing_required_checkpoints",
]
