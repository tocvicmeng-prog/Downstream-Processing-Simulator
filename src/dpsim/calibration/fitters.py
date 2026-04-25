"""Node 20 (v7.0, P1a): calibration fitter scaffold.

Fitters that consume ``AssayRecord`` lists from ``data/validation/`` and emit
``CalibrationEntry`` lists ready for ``CalibrationStore.load_json``.

The L1 DSD path remains a scaffold until Study A data arrive. The P2 M1
washing path performs a direct inverse fit for oil/surfactant retention
factors from residual assays so wash carryover is no longer hard-coded. P2
physical-QC ingest converts pore, porosity, swelling, and compression/modulus
assays into auditable reference entries for lifecycle calibration dossiers. P2
M3 ingest adds static binding capacity, dynamic binding capacity, and optional
single-point Langmuir affinity entries so chromatography calibration can enter
the same RunContext pathway as M1/M2 data. P3 adds M2 functionalization assay
contracts for ligand density, activity retention, ligand leaching, and free
protein in wash fractions. P5 upgrades M2/M3 ingest with replicate-weighted
reference means, weighted least-squares Langmuir isotherm fits, breakthrough
curve integration, and pressure-flow curve fitting with uncertainty and
calibration-domain metadata.
"""

from __future__ import annotations

import json
import logging
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
from scipy.optimize import least_squares

from ..assay_record import AssayKind, AssayRecord
from .calibration_data import CalibrationEntry

logger = logging.getLogger(__name__)


def load_assay_records(directory: Path) -> list[AssayRecord]:
    """Load every ``*.json`` AssayRecord under a validation subdirectory."""
    directory = Path(directory)
    if not directory.exists():
        return []
    records: list[AssayRecord] = []
    for path in sorted(directory.glob("*.json")):
        try:
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
            records.append(AssayRecord.from_dict(d))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            logger.warning("Skipping malformed assay JSON %s: %s", path, exc)
    return records


def fit_l1_dsd_to_calibration_entries(
    records: list[AssayRecord],
    profile_key: str = "rotor_stator_legacy",
) -> list[CalibrationEntry]:
    """Stub L1 DSD fitter (Node 20).

    Real implementation (Node 21) will:
      1. Group records by stirrer_type + surfactant_conc + mu_d.
      2. Build (RPM, mean_d32) tuples; minimise residual against
         ``breakage_rate_dispatch + coalescence_rate_dispatch`` over
         (C1, C2, C3, C4, C5) using scipy.optimize.least_squares.
      3. Compute posterior std via Hessian inversion at the optimum and
         emit ``CalibrationEntry(posterior_uncertainty=...)``.

    For v7.0 scaffold this just emits identity entries — value = mean,
    posterior = sample std — so the data-flow pipeline can be tested
    without crashing on an empty fitter.
    """
    out: list[CalibrationEntry] = []
    dsd_records = [r for r in records if r.kind == AssayKind.DROPLET_SIZE_DISTRIBUTION]
    if not dsd_records:
        logger.info("fit_l1_dsd: no DROPLET_SIZE_DISTRIBUTION records found")
        return out
    # Stub: collapse all records to a single d32 reference value.
    all_values = []
    for r in dsd_records:
        all_values.extend(r.values())
    if not all_values:
        return out
    import statistics
    mean_d32 = float(statistics.mean(all_values))
    std_d32 = float(statistics.stdev(all_values)) if len(all_values) >= 2 else 0.0
    out.append(CalibrationEntry(
        profile_key=profile_key,
        parameter_name="d32_reference",
        measured_value=mean_d32,
        units="m",
        confidence="high" if std_d32 / max(mean_d32, 1e-300) < 0.10 else "medium",
        source_reference=f"L1_DSD fit n={len(all_values)} replicates",
        target_module="L1",
        fit_method="stub_mean",
        posterior_uncertainty=std_d32,
    ))
    return out


def fit_m1_washing_to_calibration_entries(
    records: list[AssayRecord],
    profile_key: str = "m1_washing",
) -> list[CalibrationEntry]:
    """Fit M1 oil/surfactant wash retention factors from residual assays.

    The fitter inverts the qualitative M1 washing model:

    ``residual = initial * (1 - mixing * W / (W + retention)) ** cycles``

    where ``W`` is wash volume ratio. Oil records fit
    ``m1_oil_retention_factor``. Surfactant records fit
    ``m1_surfactant_retention_factor`` after normalising by formulation
    Span-80 concentration and initial oil carryover.
    """

    oil_records = [r for r in records if r.kind == AssayKind.RESIDUAL_OIL]
    surfactant_records = [r for r in records if r.kind == AssayKind.RESIDUAL_SURFACTANT]
    entries: list[CalibrationEntry] = []

    oil_fits = [
        fit for record in oil_records
        if (fit := _fit_retention_from_record(record, kind="oil")) is not None
    ]
    surfactant_fits = [
        fit for record in surfactant_records
        if (fit := _fit_retention_from_record(record, kind="surfactant")) is not None
    ]

    if oil_fits:
        entries.append(_retention_entry(
            fits=oil_fits,
            profile_key=profile_key,
            parameter_name="m1_oil_retention_factor",
            measurement_type="residual_oil",
            source_label="M1 residual oil wash fit",
        ))
    if surfactant_fits:
        entries.append(_retention_entry(
            fits=surfactant_fits,
            profile_key=profile_key,
            parameter_name="m1_surfactant_retention_factor",
            measurement_type="residual_surfactant",
            source_label="M1 residual surfactant wash fit",
        ))
    return entries


def fit_m1_physical_qc_to_calibration_entries(
    records: list[AssayRecord],
    profile_key: str = "m1_physical_qc",
) -> list[CalibrationEntry]:
    """Create M1 physical-QC reference entries from wet-lab assay records.

    These entries are intentionally conservative: they preserve measured pore,
    porosity, swelling, and compression/modulus values with posterior scatter
    and validity-domain metadata. They are immediately useful in dossiers and
    future calibration gates, while avoiding hidden overrides of solver
    parameters whose mechanistic mapping is not yet calibrated.
    """

    specs = {
        AssayKind.PORE_SIZE: ("measured_pore_size_mean", "m", "M1", "pore_size"),
        AssayKind.POROSITY: ("measured_porosity", "1", "M1", "porosity"),
        AssayKind.SWELLING_RATIO: ("measured_swelling_ratio", "1", "M1", "swelling_ratio"),
        AssayKind.BULK_MODULUS: ("measured_bulk_modulus", "Pa", "L4", "bulk_modulus"),
        AssayKind.COMPRESSION_MODULUS: (
            "measured_compression_modulus",
            "Pa",
            "M3",
            "compression_modulus",
        ),
    }
    entries: list[CalibrationEntry] = []
    for kind, (parameter_name, target_unit, target_module, measurement_type) in specs.items():
        kind_records = [record for record in records if record.kind == kind]
        if not kind_records:
            continue
        entry = _reference_entry_from_records(
            kind_records,
            profile_key=profile_key,
            parameter_name=parameter_name,
            target_unit=target_unit,
            target_module=target_module,
            measurement_type=measurement_type,
        )
        if entry is not None:
            entries.append(entry)
    return entries


def fit_m3_binding_to_calibration_entries(
    records: list[AssayRecord],
    profile_key: str = "m3_binding",
) -> list[CalibrationEntry]:
    """Create M3 calibration entries from capacity and breakthrough assays.

    The fitter intentionally separates three wet-lab concepts:

    * static binding capacity records become ``estimated_q_max`` references
      or a weighted least-squares Langmuir fit when a full isotherm is present,
      which lifecycle can apply to the FunctionalMediaContract before M3;
    * dynamic binding capacity records become threshold-specific
      ``dbc_*_reference`` entries for run-vs-assay diagnostics, including
      integrated raw breakthrough curves when time/fraction arrays are present;
    * pressure-flow records become hydraulic slope references for packed-bed
      operability checks;
    * ``K_affinity`` is emitted from full weighted isotherms, or from the
      earlier single-point inversion only when a static record includes both
      an equilibrium liquid concentration and an explicit qmax reference.
    """

    static_records = [
        record for record in records
        if record.kind == AssayKind.STATIC_BINDING_CAPACITY
    ]
    dynamic_records = [
        record for record in records
        if record.kind == AssayKind.DYNAMIC_BINDING_CAPACITY
    ]
    pressure_records = [
        record for record in records
        if record.kind == AssayKind.PRESSURE_FLOW_CURVE
    ]

    entries: list[CalibrationEntry] = []
    isotherm_entries = _m3_langmuir_wls_entries_from_static_records(
        static_records,
        profile_key=profile_key,
    )
    if isotherm_entries:
        entries.extend(isotherm_entries)
    else:
        static_entry = _m3_capacity_entry_from_records(
            static_records,
            profile_key=profile_key,
            parameter_name="estimated_q_max",
            fit_method="static_capacity_reference_mean",
            measurement_type="static_binding_capacity",
            source_label="M3 static binding capacity",
        )
        if static_entry is not None:
            entries.append(static_entry)

    entries.extend(_m3_dbc_entries_from_records(dynamic_records, profile_key))
    entries.extend(_m3_pressure_flow_entries_from_records(pressure_records, profile_key))

    if not isotherm_entries:
        k_entry = _m3_langmuir_affinity_entry_from_static_records(
            static_records,
            profile_key=profile_key,
        )
        if k_entry is not None:
            entries.append(k_entry)
    return entries


def fit_m2_functionalization_to_calibration_entries(
    records: list[AssayRecord],
    profile_key: str = "m2_functionalization",
) -> list[CalibrationEntry]:
    """Create M2 references from functionalization wet-lab assays.

    The fitter intentionally keeps the assay contracts separate:
    ``functional_ligand_density`` is an installed ligand-density reference,
    ``activity_retention`` is an orthogonal bioactivity reference, and wash /
    storage loss assays report closure terms without silently changing the
    chemistry model until calibrated mapping rules are available.
    """

    specs = {
        AssayKind.LIGAND_DENSITY: (
            "functional_ligand_density",
            "mol/m2",
            "ligand_density",
        ),
        AssayKind.ACTIVITY_RETENTION: (
            "activity_retention",
            "1",
            "activity_retention",
        ),
        AssayKind.LIGAND_LEACHING: (
            "ligand_leaching_fraction",
            "1",
            "ligand_leaching",
        ),
        AssayKind.FREE_PROTEIN_WASH_FRACTION: (
            "free_protein_wash_fraction",
            "1",
            "free_protein_wash_fraction",
        ),
    }
    entries: list[CalibrationEntry] = []
    for kind, (parameter_name, target_unit, measurement_type) in specs.items():
        kind_records = [record for record in records if record.kind == kind]
        if not kind_records:
            continue
        entry = _reference_entry_from_records(
            kind_records,
            profile_key=profile_key,
            parameter_name=parameter_name,
            target_unit=target_unit,
            target_module="M2",
            measurement_type=measurement_type,
            source_label="M2 functionalization assay",
        )
        if entry is not None:
            entries.append(entry)
    return entries


def _fit_retention_from_record(record: AssayRecord, *, kind: str) -> dict | None:
    """Infer one retention factor from one residual assay record."""

    initial = _condition_float(record, "initial_oil_carryover_fraction", 0.10)
    cycles = int(round(_condition_float(record, "wash_cycles", 3.0)))
    wash_volume_ratio = _condition_float(record, "wash_volume_ratio", 3.0)
    mixing_efficiency = _condition_float(record, "wash_mixing_efficiency", 0.80)
    if initial <= 0.0 or cycles <= 0 or wash_volume_ratio <= 0.0 or mixing_efficiency <= 0.0:
        return None

    try:
        residual_value = _record_mean_in_target_unit(
            record,
            "fraction" if kind == "oil" else "kg/m3",
        )
    except ValueError as exc:
        logger.warning("Skipping %s residual assay %s: %s", kind, record.record_id, exc)
        return None
    if not math.isfinite(residual_value) or residual_value < 0.0:
        return None

    if kind == "oil":
        normalized_residual = residual_value / initial
    else:
        c_span80 = _condition_float(
            record,
            "c_span80_kg_m3",
            _condition_float(record, "surfactant_kg_m3", 20.0),
        )
        if c_span80 <= 0.0:
            return None
        normalized_residual = residual_value / (c_span80 * initial)

    retention = _invert_wash_retention(
        normalized_residual=normalized_residual,
        cycles=cycles,
        wash_volume_ratio=wash_volume_ratio,
        mixing_efficiency=mixing_efficiency,
    )
    if retention is None:
        return None
    return {
        "record_id": record.record_id,
        "retention_factor": retention,
        "n_replicates": record.n_replicates(),
        "wash_cycles": float(cycles),
        "wash_volume_ratio": float(wash_volume_ratio),
        "mixing_efficiency": float(mixing_efficiency),
        "initial_oil_carryover_fraction": float(initial),
    }


def _invert_wash_retention(
    *,
    normalized_residual: float,
    cycles: int,
    wash_volume_ratio: float,
    mixing_efficiency: float,
) -> float | None:
    """Invert the M1 wash equation for a retention factor."""

    if cycles <= 0 or wash_volume_ratio <= 0.0 or mixing_efficiency <= 0.0:
        return None
    ratio = min(max(float(normalized_residual), 1e-12), 0.999999999)
    per_cycle_remaining = ratio ** (1.0 / cycles)
    per_cycle_removal = 1.0 - per_cycle_remaining
    if per_cycle_removal <= 0.0:
        return None
    retention = wash_volume_ratio * (mixing_efficiency / per_cycle_removal - 1.0)
    return max(0.05, float(retention))


def _retention_entry(
    *,
    fits: list[dict],
    profile_key: str,
    parameter_name: str,
    measurement_type: str,
    source_label: str,
) -> CalibrationEntry:
    """Collapse per-record retention fits into one CalibrationEntry."""

    values = [float(item["retention_factor"]) for item in fits]
    mean_value = float(statistics.mean(values))
    std_value = float(statistics.stdev(values)) if len(values) >= 2 else 0.0
    cv = std_value / max(abs(mean_value), 1e-12)
    if len(values) >= 3 and cv < 0.15:
        confidence = "high"
    elif cv < 0.35:
        confidence = "medium"
    else:
        confidence = "low"
    return CalibrationEntry(
        profile_key=profile_key,
        parameter_name=parameter_name,
        measured_value=mean_value,
        units="1",
        confidence=confidence,
        source_reference=(
            f"{source_label}; records={','.join(item['record_id'] for item in fits)}"
        ),
        replicates=sum(int(item["n_replicates"]) for item in fits),
        target_module="M1",
        fit_method="inverse_well_mixed_extraction",
        measurement_type=measurement_type,
        valid_domain=_retention_valid_domain(fits),
        posterior_uncertainty=std_value,
    )


def _m3_capacity_entry_from_records(
    records: list[AssayRecord],
    *,
    profile_key: str,
    parameter_name: str,
    fit_method: str,
    measurement_type: str,
    source_label: str,
) -> CalibrationEntry | None:
    """Collapse M3 binding-capacity records into one calibration entry."""

    if not records:
        return None
    values: list[float] = []
    sigmas: list[float] = []
    record_ids: list[str] = []
    for record in records:
        try:
            record_values, record_sigmas = _record_weighted_values_in_target_unit(
                record,
                "mol/m3",
            )
        except ValueError as exc:
            logger.warning(
                "Skipping M3 capacity assay %s: %s",
                record.record_id,
                exc,
            )
            continue
        values.extend(record_values)
        sigmas.extend(record_sigmas)
        record_ids.append(record.record_id)
    filtered = [
        (value, sigma)
        for value, sigma in zip(values, sigmas)
        if math.isfinite(value) and value >= 0.0
    ]
    values = [item[0] for item in filtered]
    sigmas = [item[1] for item in filtered]
    if not values:
        return None

    mean_value, std_value = _weighted_summary(values, sigmas)
    metadata = _calibration_metadata_from_records(records)
    return CalibrationEntry(
        profile_key=profile_key,
        parameter_name=parameter_name,
        measured_value=mean_value,
        units="mol/m3",
        confidence=_confidence_from_values(values),
        source_reference=f"{source_label}; records={','.join(record_ids)}",
        replicates=len(values),
        target_module="M3",
        fit_method=fit_method,
        measurement_type=measurement_type,
        valid_domain=_assay_valid_domain(records),
        posterior_uncertainty=std_value,
        **metadata,
    )


def _m3_dbc_entries_from_records(
    records: list[AssayRecord],
    profile_key: str,
) -> list[CalibrationEntry]:
    """Group DBC values or raw breakthrough curves by threshold."""

    grouped: dict[tuple[str, str, float], list[dict]] = {}
    for record in records:
        curve_measurements = _dbc_curve_measurements_from_record(record)
        if curve_measurements:
            measurements = curve_measurements
        else:
            measurements = _dbc_replicate_measurements_from_record(record)
        for measurement in measurements:
            threshold = float(measurement["threshold"])
            parameter_name = _dbc_parameter_name(threshold)
            measurement_type = f"dynamic_binding_capacity_{threshold * 100:.0f}pct"
            grouped.setdefault(
                (parameter_name, measurement_type, threshold),
                [],
            ).append(measurement)

    entries: list[CalibrationEntry] = []
    for (parameter_name, measurement_type, threshold), threshold_records in sorted(
        grouped.items(),
        key=lambda item: item[0][2],
    ):
        entry = _m3_dbc_entry_from_measurements(
            threshold_records,
            profile_key=profile_key,
            parameter_name=parameter_name,
            fit_method="dbc_reference_weighted_mean",
            measurement_type=measurement_type,
            source_label=f"M3 DBC{threshold * 100:.0f} breakthrough capacity",
        )
        if entry is not None:
            entry.valid_domain = dict(entry.valid_domain)
            entry.valid_domain["breakthrough_threshold_fraction"] = (
                threshold,
                threshold,
            )
            entries.append(entry)
    return entries


def _m3_dbc_entry_from_measurements(
    measurements: list[dict],
    *,
    profile_key: str,
    parameter_name: str,
    fit_method: str,
    measurement_type: str,
    source_label: str,
) -> CalibrationEntry | None:
    """Collapse DBC point estimates from replicate assays or raw curves."""

    values = [
        float(item["value"])
        for item in measurements
        if math.isfinite(float(item["value"])) and float(item["value"]) >= 0.0
    ]
    sigmas = [
        float(item.get("sigma", 0.0))
        for item in measurements
        if math.isfinite(float(item["value"])) and float(item["value"]) >= 0.0
    ]
    if not values:
        return None
    mean_value, std_value = _weighted_summary(values, sigmas)
    record_ids = sorted({str(item["record_id"]) for item in measurements})
    curve_based = any(str(item.get("source", "")) == "breakthrough_curve" for item in measurements)
    weighted = any(float(item.get("sigma", 0.0)) > 0.0 for item in measurements)
    method = (
        "breakthrough_curve_integration"
        if curve_based
        else (fit_method if weighted else "dbc_reference_mean")
    )
    confidence = _confidence_from_values(values)
    metadata_records = [
        item.get("record")
        for item in measurements
        if isinstance(item.get("record"), AssayRecord)
    ]
    metadata = _calibration_metadata_from_records(metadata_records)
    return CalibrationEntry(
        profile_key=profile_key,
        parameter_name=parameter_name,
        measured_value=mean_value,
        units="mol/m3",
        confidence=confidence,
        source_reference=f"{source_label}; records={','.join(record_ids)}",
        replicates=len(values),
        target_module="M3",
        fit_method=method,
        measurement_type=measurement_type,
        valid_domain=_measurements_valid_domain(measurements),
        posterior_uncertainty=std_value,
        **metadata,
    )


def _dbc_replicate_measurements_from_record(record: AssayRecord) -> list[dict]:
    """Return DBC measurements from a record whose replicates are capacities."""

    threshold = _dbc_threshold_fraction(record)
    try:
        values, sigmas = _record_weighted_values_in_target_unit(record, "mol/m3")
    except ValueError as exc:
        logger.warning("Skipping DBC assay %s: %s", record.record_id, exc)
        return []
    return [
        {
            "threshold": threshold,
            "value": value,
            "sigma": sigma,
            "record_id": record.record_id,
            "record": record,
            "source": "replicate_capacity",
            "domain": _assay_valid_domain([record]),
        }
        for value, sigma in zip(values, sigmas)
        if math.isfinite(value) and value >= 0.0
    ]


def _dbc_curve_measurements_from_record(record: AssayRecord) -> list[dict]:
    """Integrate a raw breakthrough curve into DBC threshold references.

    The wet-lab contract accepts either normalized outlet fractions
    (``C_over_C0`` aliases) or absolute outlet concentrations plus a feed
    concentration. Capacity is integrated as
    ``Q * C_feed * integral(1 - C/C0) dt / bed_volume`` up to the threshold
    crossing.
    """

    time_s = _condition_float_list(record, ("time_s", "elapsed_time_s", "t_s"))
    if len(time_s) < 2:
        return []
    fraction = _condition_float_list(
        record,
        (
            "C_over_C0",
            "c_over_c0",
            "outlet_fraction",
            "breakthrough_fraction_profile",
        ),
    )
    c_out = []
    if not fraction:
        c_out = _condition_float_list(
            record,
            ("C_outlet_mol_m3", "c_outlet_mol_m3", "outlet_concentration_mol_m3"),
        )
    c_feed = _feed_concentration_mol_m3(record)
    if not fraction:
        if not c_out or c_feed is None or c_feed <= 0.0:
            return []
        fraction = [value / c_feed for value in c_out]
    flow_rate = _flow_rate_m3_s(record)
    bed_volume = _bed_volume_m3(record)
    if flow_rate is None or flow_rate <= 0.0 or bed_volume is None or bed_volume <= 0.0:
        return []
    if c_feed is None or c_feed <= 0.0:
        c_feed = _condition_float_or_none(record, "feed_concentration_mM")
    if c_feed is None or c_feed <= 0.0:
        return []

    pairs = sorted(
        (float(t), min(max(float(y), 0.0), 5.0))
        for t, y in zip(time_s, fraction)
        if math.isfinite(float(t)) and math.isfinite(float(y))
    )
    if len(pairs) < 2:
        return []
    t = np.asarray([item[0] for item in pairs], dtype=float)
    y = np.asarray([item[1] for item in pairs], dtype=float)
    thresholds = _dbc_thresholds_from_record(record, raw_curve=True)
    capacity_sigma = _condition_float_or_none(record, "dbc_std_mol_m3") or 0.0
    measurements: list[dict] = []
    base_domain = _assay_valid_domain([record])
    base_domain.update({
        "flow_rate_m3_s": (float(flow_rate), float(flow_rate)),
        "feed_concentration_mol_m3": (float(c_feed), float(c_feed)),
        "bed_volume_m3": (float(bed_volume), float(bed_volume)),
    })
    for threshold in thresholds:
        if threshold <= 0.0 or threshold >= 1.0:
            continue
        if np.nanmax(y) < threshold:
            continue
        crossing_time = _first_threshold_crossing_time(t, y, threshold)
        if crossing_time is None or crossing_time <= t[0]:
            continue
        t_eval, y_eval = _curve_prefix_with_crossing(t, y, crossing_time, threshold)
        uptake_area_s = float(np.trapezoid(np.maximum(1.0 - y_eval, 0.0), t_eval))
        capacity = c_feed * flow_rate * uptake_area_s / bed_volume
        if math.isfinite(capacity) and capacity >= 0.0:
            measurements.append({
                "threshold": float(threshold),
                "value": float(capacity),
                "sigma": float(capacity_sigma),
                "record_id": record.record_id,
                "record": record,
                "source": "breakthrough_curve",
                "domain": dict(base_domain),
            })
    return measurements


def _first_threshold_crossing_time(
    t: np.ndarray,
    y: np.ndarray,
    threshold: float,
) -> float | None:
    """Return the first linearly interpolated time where y crosses threshold."""

    for idx in range(1, len(t)):
        y0 = float(y[idx - 1])
        y1 = float(y[idx])
        if y0 >= threshold:
            return float(t[idx - 1])
        if y1 < threshold:
            continue
        if y1 == y0:
            return float(t[idx])
        frac = (threshold - y0) / (y1 - y0)
        return float(t[idx - 1] + frac * (t[idx] - t[idx - 1]))
    return None


def _curve_prefix_with_crossing(
    t: np.ndarray,
    y: np.ndarray,
    crossing_time: float,
    threshold: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Return curve points from the start through the threshold crossing."""

    keep = t < crossing_time
    t_eval = list(t[keep])
    y_eval = list(y[keep])
    if not t_eval or t_eval[-1] != crossing_time:
        t_eval.append(float(crossing_time))
        y_eval.append(float(threshold))
    return np.asarray(t_eval, dtype=float), np.asarray(y_eval, dtype=float)


def _m3_langmuir_affinity_entry_from_static_records(
    records: list[AssayRecord],
    *,
    profile_key: str,
) -> CalibrationEntry | None:
    """Infer Langmuir ``K_affinity`` from static records with full context."""

    fits: list[dict[str, float | str | int]] = []
    for record in records:
        try:
            q_value = _record_mean_in_target_unit(record, "mol/m3")
        except ValueError:
            continue
        c_eq = _equilibrium_concentration_mol_m3(record)
        q_max = _qmax_reference_mol_m3(record)
        if c_eq is None or q_max is None:
            continue
        if q_value <= 0.0 or c_eq <= 0.0 or q_max <= q_value:
            continue
        k_affinity = q_value / (c_eq * (q_max - q_value))
        if math.isfinite(k_affinity) and k_affinity > 0.0:
            fits.append({
                "record_id": record.record_id,
                "K_affinity": float(k_affinity),
                "n_replicates": record.n_replicates(),
                "equilibrium_concentration_mol_m3": float(c_eq),
                "q_max_reference_mol_m3": float(q_max),
            })

    if not fits:
        return None
    values = [float(item["K_affinity"]) for item in fits]
    mean_value = float(statistics.mean(values))
    std_value = float(statistics.stdev(values)) if len(values) >= 2 else 0.0
    metadata = _calibration_metadata_from_records(records)
    return CalibrationEntry(
        profile_key=profile_key,
        parameter_name="K_affinity",
        measured_value=mean_value,
        units="m3/mol",
        confidence=_confidence_from_values(values),
        source_reference=(
            "M3 Langmuir affinity from static binding records="
            f"{','.join(str(item['record_id']) for item in fits)}"
        ),
        replicates=sum(int(item["n_replicates"]) for item in fits),
        target_module="M3",
        fit_method="langmuir_single_point_from_static_capacity",
        measurement_type="static_binding_isotherm",
        valid_domain=_m3_k_affinity_valid_domain(fits),
        posterior_uncertainty=std_value,
        **metadata,
    )


def _m3_langmuir_wls_entries_from_static_records(
    records: list[AssayRecord],
    *,
    profile_key: str,
) -> list[CalibrationEntry]:
    """Fit qmax and K_affinity from a multi-point static isotherm.

    A minimum of three independent equilibrium concentrations is required.
    Otherwise the fitter falls back to the historical static-capacity mean
    and optional single-point K inversion.
    """

    points: list[dict] = []
    for record in records:
        c_eq = _equilibrium_concentration_mol_m3(record)
        if c_eq is None or c_eq <= 0.0:
            continue
        try:
            values, sigmas = _record_weighted_values_in_target_unit(record, "mol/m3")
        except ValueError as exc:
            logger.warning("Skipping static isotherm point %s: %s", record.record_id, exc)
            continue
        mean_q, q_sigma = _weighted_summary(values, sigmas)
        if not math.isfinite(mean_q) or mean_q <= 0.0:
            continue
        if q_sigma <= 0.0:
            q_sigma = max(abs(mean_q) * 0.05, 1.0e-9)
        points.append({
            "record_id": record.record_id,
            "record": record,
            "c_eq": float(c_eq),
            "q": float(mean_q),
            "sigma": float(q_sigma),
            "n_replicates": record.n_replicates(),
        })

    unique_c = {round(float(point["c_eq"]), 12) for point in points}
    if len(points) < 3 or len(unique_c) < 3:
        return []

    c = np.asarray([float(point["c_eq"]) for point in points], dtype=float)
    q = np.asarray([float(point["q"]) for point in points], dtype=float)
    sigma = np.asarray([float(point["sigma"]) for point in points], dtype=float)
    sigma = np.where(sigma > 0.0, sigma, np.maximum(0.05 * np.abs(q), 1.0e-9))
    q0 = max(float(np.max(q)) * 1.2, 1.0e-12)
    explicit_qmax = [
        value for point in points
        if (value := _qmax_reference_mol_m3(point["record"])) is not None
    ]
    if explicit_qmax:
        q0 = max(q0, float(statistics.mean(explicit_qmax)))
    k_guesses = [
        q_i / (c_i * max(q0 - q_i, 1.0e-12))
        for c_i, q_i in zip(c, q)
        if c_i > 0.0 and q0 > q_i
    ]
    k0 = float(statistics.median(k_guesses)) if k_guesses else 1.0
    x0 = np.asarray([q0, max(k0, 1.0e-12)], dtype=float)

    def residuals(x: np.ndarray) -> np.ndarray:
        qmax, k_affinity = x
        predicted = qmax * k_affinity * c / (1.0 + k_affinity * c)
        return (predicted - q) / sigma

    try:
        result = least_squares(
            residuals,
            x0=x0,
            bounds=([max(float(np.max(q)) * 1.000001, 1.0e-12), 1.0e-12], [np.inf, np.inf]),
            method="trf",
        )
    except ValueError as exc:
        logger.warning("Langmuir WLS fit failed: %s", exc)
        return []
    if not result.success:
        logger.warning("Langmuir WLS fit did not converge: %s", result.message)
        return []

    qmax_fit, k_fit = [float(value) for value in result.x]
    if not all(math.isfinite(value) and value > 0.0 for value in (qmax_fit, k_fit)):
        return []
    qmax_std, k_std = _least_squares_parameter_std(result.jac, result.fun, n_params=2)
    record_ids = ",".join(str(point["record_id"]) for point in points)
    metadata = _calibration_metadata_from_records([point["record"] for point in points])
    domain = _assay_valid_domain([point["record"] for point in points])
    domain["equilibrium_concentration_mol_m3"] = (float(np.min(c)), float(np.max(c)))
    domain["static_binding_capacity_mol_m3"] = (float(np.min(q)), float(np.max(q)))
    confidence = _confidence_from_fit(
        n_points=len(points),
        measured_value=qmax_fit,
        uncertainty=qmax_std,
    )
    common = {
        "profile_key": profile_key,
        "confidence": confidence,
        "source_reference": f"M3 Langmuir WLS static isotherm; records={record_ids}",
        "replicates": int(sum(int(point["n_replicates"]) for point in points)),
        "target_module": "M3",
        "fit_method": "weighted_least_squares_langmuir",
        "measurement_type": "static_binding_isotherm",
        "valid_domain": domain,
        **metadata,
    }
    return [
        CalibrationEntry(
            parameter_name="estimated_q_max",
            measured_value=qmax_fit,
            units="mol/m3",
            posterior_uncertainty=qmax_std,
            **common,
        ),
        CalibrationEntry(
            parameter_name="K_affinity",
            measured_value=k_fit,
            units="m3/mol",
            posterior_uncertainty=k_std,
            **common,
        ),
    ]


def _m3_k_affinity_valid_domain(fits: list[dict[str, float | str | int]]) -> dict:
    """Build a domain envelope for inferred Langmuir affinity constants."""

    domain: dict[str, tuple[float, float]] = {}
    for key in ("equilibrium_concentration_mol_m3", "q_max_reference_mol_m3"):
        values = [float(item[key]) for item in fits]
        domain[key] = (min(values), max(values))
    return domain


def _m3_pressure_flow_entries_from_records(
    records: list[AssayRecord],
    profile_key: str,
) -> list[CalibrationEntry]:
    """Fit packed-bed pressure-flow slope from hydraulic QC records."""

    points: list[dict] = []
    for record in records:
        points.extend(_pressure_flow_points_from_record(record))
    if len(points) < 2:
        return []
    q = np.asarray([float(point["flow_rate_m3_s"]) for point in points], dtype=float)
    dp = np.asarray([float(point["pressure_drop_Pa"]) for point in points], dtype=float)
    sigma = np.asarray([float(point.get("sigma_Pa", 0.0)) for point in points], dtype=float)
    valid = np.isfinite(q) & np.isfinite(dp) & (q > 0.0) & (dp >= 0.0)
    if int(np.sum(valid)) < 2:
        return []
    q = q[valid]
    dp = dp[valid]
    sigma = sigma[valid]
    sigma = np.where(sigma > 0.0, sigma, np.maximum(0.05 * np.maximum(dp, 1.0), 1.0))
    weights = 1.0 / np.square(sigma)
    denominator = float(np.sum(weights * np.square(q)))
    if denominator <= 0.0:
        return []
    slope = float(np.sum(weights * q * dp) / denominator)
    residual = (slope * q - dp) / sigma
    dof = max(1, len(q) - 1)
    reduced_chi2 = float(np.sum(np.square(residual)) / dof)
    slope_std = math.sqrt(1.0 / denominator) * max(1.0, math.sqrt(reduced_chi2))
    record_ids = sorted({str(point["record_id"]) for point in points})
    source_records = [
        point.get("record")
        for point in points
        if isinstance(point.get("record"), AssayRecord)
    ]
    metadata = _calibration_metadata_from_records(source_records)
    domain = _measurements_valid_domain([
        {
            "domain": {
                "flow_rate_m3_s": (
                    float(point["flow_rate_m3_s"]),
                    float(point["flow_rate_m3_s"]),
                ),
                "pressure_drop_Pa": (
                    float(point["pressure_drop_Pa"]),
                    float(point["pressure_drop_Pa"]),
                ),
                **dict(point.get("domain", {})),
            }
        }
        for point in points
    ])
    entry = CalibrationEntry(
        profile_key=profile_key,
        parameter_name="pressure_flow_slope_Pa_per_m3_s",
        measured_value=slope,
        units="Pa/(m3/s)",
        confidence=_confidence_from_fit(len(q), slope, slope_std),
        source_reference=f"M3 pressure-flow WLS; records={','.join(record_ids)}",
        replicates=len(q),
        target_module="M3",
        fit_method="weighted_least_squares_pressure_flow",
        measurement_type="pressure_flow_curve",
        valid_domain=domain,
        posterior_uncertainty=float(slope_std),
        **metadata,
    )
    return [entry]


def _pressure_flow_points_from_record(record: AssayRecord) -> list[dict]:
    """Return pressure-flow fit points from a curve record or single-flow assay."""

    flow_values = _condition_float_list(
        record,
        ("flow_rate_m3_s", "flow_rates_m3_s", "Q_m3_s", "Q_values_m3_s"),
    )
    if not flow_values:
        flow_values = _condition_float_list(
            record,
            ("flow_rate_mL_min", "flow_rates_mL_min", "flow_rate_ml_min"),
        )
        flow_values = [value * 1.0e-6 / 60.0 for value in flow_values]
    pressure_values = _pressure_drop_list_from_record(record)
    sigma_values = _condition_float_list(
        record,
        ("pressure_drop_std_Pa", "pressure_std_Pa", "deltaP_std_Pa"),
    )
    if flow_values and pressure_values:
        points: list[dict] = []
        for idx, (flow_rate, pressure_drop) in enumerate(zip(flow_values, pressure_values)):
            sigma = sigma_values[idx] if idx < len(sigma_values) else 0.0
            if math.isfinite(flow_rate) and math.isfinite(pressure_drop):
                points.append({
                    "flow_rate_m3_s": float(flow_rate),
                    "pressure_drop_Pa": float(pressure_drop),
                    "sigma_Pa": float(max(sigma, 0.0)),
                    "record_id": record.record_id,
                    "record": record,
                    "domain": _assay_valid_domain([record]),
                })
        return points

    flow_rate = _flow_rate_m3_s(record)
    if flow_rate is None or flow_rate <= 0.0:
        return []
    try:
        values, sigmas = _record_weighted_values_in_target_unit(record, "Pa")
    except ValueError as exc:
        logger.warning("Skipping pressure-flow assay %s: %s", record.record_id, exc)
        return []
    return [
        {
            "flow_rate_m3_s": float(flow_rate),
            "pressure_drop_Pa": float(value),
            "sigma_Pa": float(max(sigma, 0.0)),
            "record_id": record.record_id,
            "record": record,
            "domain": _assay_valid_domain([record]),
        }
        for value, sigma in zip(values, sigmas)
        if math.isfinite(value) and value >= 0.0
    ]


def _pressure_drop_list_from_record(record: AssayRecord) -> list[float]:
    """Read pressure-drop arrays from common process-condition keys."""

    values = _condition_float_list(
        record,
        ("pressure_drop_Pa", "pressure_drops_Pa", "deltaP_Pa", "deltaP_values_Pa"),
    )
    if values:
        return values
    values = _condition_float_list(
        record,
        ("pressure_drop_kPa", "pressure_drops_kPa", "deltaP_kPa"),
    )
    if values:
        return [value * 1.0e3 for value in values]
    values = _condition_float_list(
        record,
        ("pressure_drop_bar", "pressure_drops_bar", "deltaP_bar"),
    )
    if values:
        return [value * 1.0e5 for value in values]
    return []


def _dbc_threshold_fraction(record: AssayRecord) -> float:
    """Return the DBC breakthrough threshold encoded in a record."""

    for key in (
        "breakthrough_threshold_fraction",
        "breakthrough_fraction",
        "dbc_threshold_fraction",
        "dbc_fraction",
    ):
        value = _condition_float_or_none(record, key)
        if value is None:
            continue
        if value > 1.0:
            value *= 0.01
        if 0.0 < value < 1.0:
            return float(value)
    return 0.10


def _dbc_thresholds_from_record(
    record: AssayRecord,
    *,
    raw_curve: bool = False,
) -> list[float]:
    """Return one or more DBC threshold fractions encoded in a record."""

    values = _condition_float_list(
        record,
        (
            "breakthrough_threshold_fractions",
            "breakthrough_fractions",
            "dbc_threshold_fractions",
        ),
    )
    thresholds: list[float] = []
    for value in values:
        if value > 1.0:
            value *= 0.01
        if 0.0 < value < 1.0:
            thresholds.append(float(value))
    if thresholds:
        return sorted(set(thresholds))
    if raw_curve:
        return [0.05, 0.10, 0.50]
    return [_dbc_threshold_fraction(record)]


def _dbc_parameter_name(threshold: float) -> str:
    """Map common DBC thresholds to stable calibration parameter names."""

    if abs(threshold - 0.05) <= 0.01:
        return "dbc_5_reference"
    if abs(threshold - 0.10) <= 0.015:
        return "dbc_10_reference"
    if abs(threshold - 0.50) <= 0.03:
        return "dbc_50_reference"
    return f"dbc_{int(round(threshold * 100))}_reference"


def _equilibrium_concentration_mol_m3(record: AssayRecord) -> float | None:
    """Read equilibrium liquid concentration from common condition keys."""

    for key in (
        "equilibrium_concentration_mol_m3",
        "C_eq_mol_m3",
        "c_eq_mol_m3",
        "protein_concentration_mol_m3",
    ):
        value = _condition_float_or_none(record, key)
        if value is not None:
            return value
    for key in ("C_eq_mM", "c_eq_mM", "equilibrium_concentration_mM"):
        value = _condition_float_or_none(record, key)
        if value is not None:
            return value
    for key in ("C_eq_M", "c_eq_M", "equilibrium_concentration_M"):
        value = _condition_float_or_none(record, key)
        if value is not None:
            return value * 1000.0
    return None


def _qmax_reference_mol_m3(record: AssayRecord) -> float | None:
    """Read explicit qmax reference needed for single-point Langmuir K."""

    for key in (
        "q_max_reference_mol_m3",
        "qmax_reference_mol_m3",
        "estimated_q_max_mol_m3",
    ):
        value = _condition_float_or_none(record, key)
        if value is not None:
            return value
    return None


def _retention_valid_domain(fits: list[dict]) -> dict:
    """Build a simple validity-domain envelope from records used in a fit."""

    domain: dict[str, tuple[float, float]] = {}
    for key in (
        "wash_cycles",
        "wash_volume_ratio",
        "mixing_efficiency",
        "initial_oil_carryover_fraction",
    ):
        values = [float(item[key]) for item in fits]
        domain[key] = (min(values), max(values))
    return domain


def _reference_entry_from_records(
    records: list[AssayRecord],
    *,
    profile_key: str,
    parameter_name: str,
    target_unit: str,
    target_module: str,
    measurement_type: str,
    source_label: str = "M1 physical QC",
) -> CalibrationEntry | None:
    """Collapse homogeneous physical-QC assays into one reference entry."""

    values: list[float] = []
    sigmas: list[float] = []
    record_ids: list[str] = []
    for record in records:
        try:
            record_values, record_sigmas = _record_weighted_values_in_target_unit(
                record,
                target_unit,
            )
        except ValueError as exc:
            logger.warning(
                "Skipping %s physical-QC assay %s: %s",
                measurement_type,
                record.record_id,
                exc,
            )
            continue
        values.extend(record_values)
        sigmas.extend(record_sigmas)
        record_ids.append(record.record_id)
    filtered = [
        (value, sigma)
        for value, sigma in zip(values, sigmas)
        if math.isfinite(value)
    ]
    values = [item[0] for item in filtered]
    sigmas = [item[1] for item in filtered]
    if not values:
        return None

    mean_value, std_value = _weighted_summary(values, sigmas)
    cv = (float(statistics.stdev(values)) if len(values) >= 2 else 0.0) / max(
        abs(mean_value),
        1e-12,
    )
    confidence = "high" if len(values) >= 3 and cv < 0.10 else (
        "medium" if cv < 0.30 else "low"
    )
    weighted = any(sigma > 0.0 for sigma in sigmas)
    return CalibrationEntry(
        profile_key=profile_key,
        parameter_name=parameter_name,
        measured_value=mean_value,
        units=target_unit,
        confidence=confidence,
        source_reference=(
            f"{source_label} {measurement_type}; records={','.join(record_ids)}"
        ),
        replicates=len(values),
        target_module=target_module,
        fit_method="weighted_assay_reference_mean" if weighted else "assay_reference_mean",
        measurement_type=measurement_type,
        valid_domain=_assay_valid_domain(records),
        posterior_uncertainty=std_value,
    )


def _assay_valid_domain(records: list[AssayRecord]) -> dict:
    """Build a numeric condition envelope for assay-derived references."""

    numeric_by_key: dict[str, list[float]] = {}
    for record in records:
        for key, value in record.process_conditions.items():
            try:
                numeric_by_key.setdefault(key, []).append(float(value))
            except (TypeError, ValueError):
                continue
    return {
        key: (min(values), max(values))
        for key, values in sorted(numeric_by_key.items())
        if values
    }


def _measurements_valid_domain(measurements: list[dict]) -> dict:
    """Merge per-record validity-domain envelopes from derived measurements."""

    numeric_by_key: dict[str, list[float]] = {}
    for measurement in measurements:
        domain = measurement.get("domain", {})
        if not isinstance(domain, dict):
            continue
        for key, bounds in domain.items():
            if not isinstance(bounds, (tuple, list)) or len(bounds) != 2:
                continue
            try:
                lower = float(bounds[0])
                upper = float(bounds[1])
            except (TypeError, ValueError):
                continue
            numeric_by_key.setdefault(key, []).extend([lower, upper])
    return {
        key: (min(values), max(values))
        for key, values in sorted(numeric_by_key.items())
        if values
    }


def _record_weighted_values_in_target_unit(
    record: AssayRecord,
    target_unit: str,
) -> tuple[list[float], list[float]]:
    """Convert replicate values and per-replicate std values to target units."""

    raw_values = record.values()
    if not raw_values:
        return [], []
    converted_mean = _record_mean_in_target_unit(record, target_unit)
    mean_value = record.mean()
    scale = 1.0
    if math.isfinite(mean_value) and abs(mean_value) >= 1.0e-300:
        scale = converted_mean / mean_value
    values: list[float] = []
    sigmas: list[float] = []
    for replicate in record.replicates:
        if replicate.flag == "outlier":
            continue
        values.append(float(replicate.value) * scale)
        sigmas.append(abs(float(replicate.std)) * abs(scale))
    return values, sigmas


def _weighted_summary(values: list[float], sigmas: list[float]) -> tuple[float, float]:
    """Return weighted mean and uncertainty, falling back to sample scatter."""

    clean = [
        (float(value), float(sigma))
        for value, sigma in zip(values, sigmas)
        if math.isfinite(float(value))
    ]
    if not clean:
        return float("nan"), 0.0
    y = np.asarray([item[0] for item in clean], dtype=float)
    sigma = np.asarray([item[1] for item in clean], dtype=float)
    if np.any(sigma > 0.0):
        sigma = np.where(sigma > 0.0, sigma, np.nan)
        fallback = float(np.nanmedian(sigma))
        if not math.isfinite(fallback) or fallback <= 0.0:
            fallback = max(float(np.std(y, ddof=1)) if len(y) >= 2 else 0.0, 1.0e-12)
        sigma = np.where(np.isfinite(sigma) & (sigma > 0.0), sigma, fallback)
        weights = 1.0 / np.square(sigma)
        mean = float(np.sum(weights * y) / np.sum(weights))
        posterior = math.sqrt(1.0 / float(np.sum(weights)))
        if len(y) >= 2:
            reduced_chi2 = float(
                np.sum(weights * np.square(y - mean)) / max(1, len(y) - 1)
            )
            posterior *= max(1.0, math.sqrt(reduced_chi2))
        return mean, float(posterior)
    mean = float(statistics.mean([float(value) for value in y]))
    std = float(statistics.stdev([float(value) for value in y])) if len(y) >= 2 else 0.0
    return mean, std


def _least_squares_parameter_std(
    jacobian: np.ndarray,
    residuals: np.ndarray,
    *,
    n_params: int,
) -> tuple[float, ...]:
    """Estimate parameter standard deviations from a WLS Jacobian."""

    try:
        jtj_inv = np.linalg.pinv(np.asarray(jacobian, dtype=float).T @ np.asarray(jacobian, dtype=float))
        dof = max(1, int(len(residuals)) - int(n_params))
        scale = float(np.sum(np.square(residuals)) / dof)
        cov = jtj_inv * max(scale, 1.0)
        std = np.sqrt(np.maximum(np.diag(cov), 0.0))
        return tuple(float(value) for value in std[:n_params])
    except np.linalg.LinAlgError:
        return tuple(0.0 for _ in range(n_params))


def _confidence_from_fit(
    n_points: int,
    measured_value: float,
    uncertainty: float,
) -> str:
    """Assign calibration confidence from fit count and relative uncertainty."""

    rel = abs(float(uncertainty)) / max(abs(float(measured_value)), 1.0e-12)
    if n_points >= 5 and rel < 0.15:
        return "high"
    if n_points >= 3 and rel < 0.35:
        return "medium"
    return "low"


def _record_values_in_target_unit(record: AssayRecord, target_unit: str) -> list[float]:
    """Convert every non-outlier replicate into a target unit."""

    values = record.values()
    if not values:
        return []
    converted_mean = _record_mean_in_target_unit(record, target_unit)
    mean_value = record.mean()
    if not math.isfinite(mean_value) or abs(mean_value) < 1e-300:
        return [converted_mean for _ in values]
    scale = converted_mean / mean_value
    return [float(value) * scale for value in values]


def _record_mean_in_target_unit(record: AssayRecord, target_unit: str) -> float:
    """Convert an AssayRecord mean to the limited units used by P2 fitters."""

    mean_value = record.mean()
    unit = record.units
    unit_norm = _normalise_unit(unit)
    if target_unit == "m":
        if unit == "m":
            return float(mean_value)
        if unit == "um":
            return float(mean_value) * 1e-6
        if unit == "nm":
            return float(mean_value) * 1e-9
    if target_unit == "Pa":
        if unit == "Pa" or unit_norm == "pa":
            return float(mean_value)
        if unit == "kPa" or unit_norm == "kpa":
            return float(mean_value) * 1e3
        if unit == "MPa" or unit_norm == "mpa":
            return float(mean_value) * 1e6
        if unit_norm == "bar":
            return float(mean_value) * 1e5
    if target_unit == "1":
        if unit in ("fraction", "1", "-"):
            return float(mean_value)
        if unit == "%":
            return float(mean_value) * 0.01
    if target_unit == "fraction":
        if unit in ("fraction", "1", "-"):
            return float(mean_value)
        if unit == "%":
            return float(mean_value) * 0.01
    if target_unit == "kg/m3":
        if unit in ("kg/m3", "g/L", "mg/mL"):
            return float(mean_value)
        if unit == "mg/L":
            return float(mean_value) * 1e-3
    if target_unit == "mol/m3":
        if unit_norm in ("mol/m3", "mol/m^3"):
            return float(mean_value)
        if unit_norm in ("m", "mol/l", "molar"):
            return float(mean_value) * 1000.0
        if unit_norm in ("mm", "mmol/l", "umol/ml"):
            return float(mean_value)
        if unit_norm in ("um", "umol/l"):
            return float(mean_value) * 1e-3
        if unit_norm in ("nm", "nmol/l"):
            return float(mean_value) * 1e-6
        mass_kg_m3: float | None = None
        if unit_norm.startswith("kg/m3"):
            mass_kg_m3 = float(mean_value)
        elif unit_norm.startswith("g/l") or unit_norm.startswith("mg/ml"):
            mass_kg_m3 = float(mean_value)
        elif unit_norm.startswith("mg/l"):
            mass_kg_m3 = float(mean_value) * 1e-3
        if mass_kg_m3 is not None:
            molecular_weight = _molecular_weight_kg_per_mol(record)
            if molecular_weight is None or molecular_weight <= 0.0:
                raise ValueError(
                    "Mass-capacity units require process_conditions "
                    "molecular_weight_kDa, molecular_weight_g_mol, or "
                    "molecular_weight_kg_mol for mol/m3 conversion."
                )
            return mass_kg_m3 / molecular_weight
    if target_unit == "m3/mol":
        if unit_norm in ("m3/mol", "m^3/mol", "1/(mol/m3)"):
            return float(mean_value)
        if unit_norm in ("l/mol", "1/m", "m^-1"):
            return float(mean_value) * 1e-3
        if unit_norm in ("1/mm", "mm^-1", "l/mmol"):
            return float(mean_value)
    if target_unit == "mol/m2":
        if unit_norm in ("mol/m2", "mol/m^2"):
            return float(mean_value)
        if unit_norm in ("umol/m2", "umol/m^2"):
            return float(mean_value) * 1e-6
        if unit_norm in ("nmol/m2", "nmol/m^2"):
            return float(mean_value) * 1e-9
        if unit_norm in ("nmol/cm2", "nmol/cm^2"):
            return float(mean_value) * 1e-5
        if unit_norm in ("pmol/cm2", "pmol/cm^2"):
            return float(mean_value) * 1e-8
    raise ValueError(
        f"Unsupported {record.kind.value} units {unit!r}; expected {target_unit}."
    )


def _normalise_unit(unit: str) -> str:
    """Normalize unit spellings used by wet-lab assay records."""

    return (
        str(unit)
        .strip()
        .replace(" ", "")
        .replace("_", "")
        .replace("µ", "u")
        .replace("μ", "u")
        .lower()
    )


def _molecular_weight_kg_per_mol(record: AssayRecord) -> float | None:
    """Read target analyte molecular weight for mass-to-molar capacity."""

    for key in ("molecular_weight_kg_mol", "molecular_weight_kg_per_mol"):
        value = _condition_float_or_none(record, key)
        if value is not None:
            return value
    value = _condition_float_or_none(record, "molecular_weight_kDa")
    if value is not None:
        return value
    value = _condition_float_or_none(record, "molecular_weight_g_mol")
    if value is not None:
        return value * 1e-3
    return None


def _confidence_from_values(values: list[float]) -> str:
    """Assign a conservative confidence label from replicate scatter."""

    if not values:
        return "low"
    mean_value = float(statistics.mean(values))
    std_value = float(statistics.stdev(values)) if len(values) >= 2 else 0.0
    cv = std_value / max(abs(mean_value), 1e-12)
    if len(values) >= 3 and cv < 0.10:
        return "high"
    if cv < 0.30:
        return "medium"
    return "low"


def _calibration_metadata_from_records(records: list[AssayRecord]) -> dict:
    """Extract common M3 calibration metadata from assay conditions."""

    metadata: dict[str, float | str] = {}
    temperature = _condition_mean(
        records,
        ("temperature_C", "temperature_c", "temperature_degC"),
    )
    if temperature is not None:
        metadata["temperature_C"] = temperature
    ph = _condition_mean(records, ("ph", "pH", "buffer_pH"))
    if ph is not None:
        metadata["ph"] = ph
    salt = _condition_mean(
        records,
        ("salt_concentration_M", "salt_M", "ionic_strength_M"),
    )
    if salt is not None:
        metadata["salt_concentration_M"] = salt
    salt_type = _condition_first_string(records, ("salt_type", "salt", "buffer_salt"))
    if salt_type:
        metadata["salt_type"] = salt_type
    target = _condition_first_string(
        records,
        ("target_molecule", "target_analyte", "protein_name"),
    )
    if target:
        metadata["target_molecule"] = target
    return metadata


def _condition_mean(
    records: list[AssayRecord],
    keys: tuple[str, ...],
) -> float | None:
    """Mean of numeric process-condition values over common key aliases."""

    values: list[float] = []
    for record in records:
        for key in keys:
            value = _condition_float_or_none(record, key)
            if value is not None:
                values.append(value)
                break
    if not values:
        return None
    return float(statistics.mean(values))


def _condition_first_string(
    records: list[AssayRecord],
    keys: tuple[str, ...],
) -> str:
    """First non-empty string process condition over common key aliases."""

    for record in records:
        for key in keys:
            value = record.process_conditions.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def _condition_float(record: AssayRecord, key: str, default: float) -> float:
    """Read a numeric process condition with a default."""

    value = record.process_conditions.get(key, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _condition_float_or_none(record: AssayRecord, key: str) -> float | None:
    """Read a numeric process condition, returning None when absent/invalid."""

    if key not in record.process_conditions:
        return None
    try:
        return float(record.process_conditions[key])
    except (TypeError, ValueError):
        return None


def _condition_float_list(
    record: AssayRecord,
    keys: tuple[str, ...],
) -> list[float]:
    """Read a numeric list from common process-condition aliases."""

    for key in keys:
        if key not in record.process_conditions:
            continue
        value = record.process_conditions[key]
        if isinstance(value, (list, tuple)):
            out: list[float] = []
            for item in value:
                try:
                    out.append(float(item))
                except (TypeError, ValueError):
                    continue
            return out
        try:
            return [float(value)]
        except (TypeError, ValueError):
            return []
    return []


def _flow_rate_m3_s(record: AssayRecord) -> float | None:
    """Read volumetric flow rate from common assay-condition units."""

    for key in ("flow_rate_m3_s", "Q_m3_s", "volumetric_flow_rate_m3_s"):
        value = _condition_float_or_none(record, key)
        if value is not None:
            return value
    for key in ("flow_rate_mL_min", "flow_rate_ml_min", "Q_mL_min"):
        value = _condition_float_or_none(record, key)
        if value is not None:
            return value * 1.0e-6 / 60.0
    return None


def _feed_concentration_mol_m3(record: AssayRecord) -> float | None:
    """Read feed concentration in mol/m3 from common keys."""

    for key in (
        "feed_concentration_mol_m3",
        "C_feed_mol_m3",
        "c_feed_mol_m3",
        "protein_concentration_mol_m3",
    ):
        value = _condition_float_or_none(record, key)
        if value is not None:
            return value
    for key in ("feed_concentration_mM", "C_feed_mM", "c_feed_mM"):
        value = _condition_float_or_none(record, key)
        if value is not None:
            return value
    for key in ("feed_concentration_M", "C_feed_M", "c_feed_M"):
        value = _condition_float_or_none(record, key)
        if value is not None:
            return value * 1000.0
    return None


def _bed_volume_m3(record: AssayRecord) -> float | None:
    """Read packed-bed volume, or derive it from diameter and bed height."""

    for key in ("bed_volume_m3", "column_volume_m3", "CV_m3"):
        value = _condition_float_or_none(record, key)
        if value is not None:
            return value
    diameter = _condition_float_or_none(record, "column_diameter_m")
    height = _condition_float_or_none(record, "bed_height_m")
    if diameter is not None and height is not None and diameter > 0.0 and height > 0.0:
        return math.pi * 0.25 * diameter * diameter * height
    return None


def write_calibration_json(
    entries: list[CalibrationEntry],
    output_path: Path,
    fit_metadata: Optional[dict] = None,
) -> Path:
    """Write a fits/ JSON loadable by ``CalibrationStore.load_json``."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = [e.to_dict() for e in entries]
    # CalibrationStore.load_json expects a top-level list. Carry fit
    # metadata in a sidecar file alongside the fit JSON.
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    if fit_metadata:
        sidecar = output_path.with_suffix(".meta.json")
        meta = dict(fit_metadata)
        meta["timestamp_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        meta["entry_count"] = len(entries)
        with open(sidecar, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
    return output_path

