"""Measured chromatography traces, fraction collection, and alignment."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np


@dataclass(frozen=True)
class DetectorTrace:
    """One measured or predicted detector trace."""

    trace_id: str
    signal_type: str
    time_s: tuple[float, ...]
    values: tuple[float, ...]
    units: str
    source: str = "measured"
    instrument_id: str = ""
    sample_id: str = ""

    def __post_init__(self) -> None:
        if len(self.time_s) != len(self.values):
            raise ValueError("time_s and values must have the same length")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FractionCollection:
    """Fraction collection window and associated sample identity."""

    fraction_id: str
    start_s: float
    end_s: float
    volume_mL: float
    pool: str = ""
    assay_record_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["assay_record_ids"] = list(self.assay_record_ids)
        return data


@dataclass(frozen=True)
class TraceAlignment:
    """Predicted-vs-measured trace comparison summary."""

    predicted_trace_id: str
    measured_trace_id: str
    signal_type: str
    rmse: float
    max_abs_error: float
    n_points: int
    notes: str = ""
    residuals: tuple[float, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["residuals"] = list(self.residuals)
        return data


def align_traces(
    predicted: DetectorTrace,
    measured: DetectorTrace,
    *,
    signal_type: str = "",
) -> TraceAlignment:
    """Interpolate predicted trace onto measured times and compute residuals."""
    if predicted.signal_type != measured.signal_type:
        raise ValueError("Cannot align traces with different signal_type values")
    x_pred = np.asarray(predicted.time_s, dtype=float)
    y_pred = np.asarray(predicted.values, dtype=float)
    x_meas = np.asarray(measured.time_s, dtype=float)
    y_meas = np.asarray(measured.values, dtype=float)
    if x_pred.size < 2 or x_meas.size == 0:
        raise ValueError("Trace alignment requires at least two predicted points and one measured point")
    interp = np.interp(x_meas, x_pred, y_pred)
    residuals = y_meas - interp
    rmse = math.sqrt(float(np.mean(np.square(residuals))))
    return TraceAlignment(
        predicted_trace_id=predicted.trace_id,
        measured_trace_id=measured.trace_id,
        signal_type=signal_type or predicted.signal_type,
        rmse=rmse,
        max_abs_error=float(np.max(np.abs(residuals))),
        n_points=int(x_meas.size),
        residuals=tuple(float(value) for value in residuals),
    )


__all__ = [
    "DetectorTrace",
    "FractionCollection",
    "TraceAlignment",
    "align_traces",
]
