"""Calibration quality gates for assay records and calibration entries."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Iterable

from dpsim.assay_record import AssayRecord
from dpsim.calibration.calibration_data import (
    CalibrationApplicability,
    CalibrationEntry,
)


@dataclass(frozen=True)
class QualityGateConfig:
    """Thresholds for deciding whether wet-lab data can support calibration."""

    min_replicates: int = 3
    max_cv: float = 0.20
    required_units: tuple[str, ...] = ()
    require_holdout: bool = False
    require_valid_domain: bool = True
    target_molecule: str = ""
    mobile_phase: str = ""
    temperature_C: float | None = None
    temperature_tolerance_C: float = 2.0
    ph: float | None = None
    ph_tolerance: float = 0.25
    salt_concentration_M: float | None = None
    salt_tolerance_M: float = 0.05


@dataclass(frozen=True)
class QualityGateIssue:
    """One quality-gate finding."""

    code: str
    severity: str
    message: str


@dataclass(frozen=True)
class CalibrationQualityReport:
    """Quality-gate result for one assay or calibration entry."""

    passed: bool
    issues: tuple[QualityGateIssue, ...] = ()
    metrics: dict[str, Any] = field(default_factory=dict)

    def errors(self) -> tuple[QualityGateIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "error")

    def warnings(self) -> tuple[QualityGateIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "warning")

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "issues": [issue.__dict__ for issue in self.issues],
            "metrics": dict(self.metrics),
        }


def evaluate_assay_record(
    record: AssayRecord,
    config: QualityGateConfig | None = None,
) -> CalibrationQualityReport:
    """Evaluate replicate count, CV, units, LOD/LOQ flags, and context match."""
    cfg = config or QualityGateConfig()
    issues: list[QualityGateIssue] = []
    metrics = {
        "n_replicates": record.n_replicates(),
        "cv": record.cv(),
        "units": record.units,
    }

    if record.n_replicates() < cfg.min_replicates:
        issues.append(QualityGateIssue(
            "min_replicates",
            "error",
            f"Requires at least {cfg.min_replicates} usable replicates.",
        ))

    cv = record.cv()
    if math.isfinite(cv) and cv > cfg.max_cv:
        issues.append(QualityGateIssue(
            "cv_threshold",
            "error",
            f"CV {cv:.3g} exceeds threshold {cfg.max_cv:.3g}.",
        ))

    if cfg.required_units and record.units not in cfg.required_units:
        issues.append(QualityGateIssue(
            "required_units",
            "error",
            f"Units {record.units!r} not in required set {cfg.required_units!r}.",
        ))

    for rep in record.replicates:
        if rep.flag in {"censored_low", "censored_high"}:
            issues.append(QualityGateIssue(
                "censored_value",
                "warning",
                "LOD/LOQ-censored replicate present; fit must handle censoring explicitly.",
            ))
            break

    issues.extend(_context_issues(record.process_conditions, cfg))
    return CalibrationQualityReport(
        passed=not any(issue.severity == "error" for issue in issues),
        issues=tuple(issues),
        metrics=metrics,
    )


def evaluate_calibration_entry(
    entry: CalibrationEntry,
    config: QualityGateConfig | None = None,
) -> CalibrationQualityReport:
    """Evaluate a fitted/manual calibration entry before tier promotion."""
    cfg = config or QualityGateConfig()
    issues: list[QualityGateIssue] = []
    metrics = {
        "replicates": entry.replicates,
        "units": entry.units,
        "posterior_uncertainty": entry.posterior_uncertainty,
    }

    if entry.replicates < cfg.min_replicates:
        issues.append(QualityGateIssue(
            "min_replicates",
            "error",
            f"Calibration entry has {entry.replicates} replicate(s); {cfg.min_replicates} required.",
        ))
    if cfg.required_units and entry.units not in cfg.required_units:
        issues.append(QualityGateIssue(
            "required_units",
            "error",
            f"Calibration units {entry.units!r} not in required set {cfg.required_units!r}.",
        ))
    if cfg.require_valid_domain and not entry.valid_domain:
        issues.append(QualityGateIssue(
            "valid_domain_missing",
            "error",
            "Calibration entry must declare a valid_domain before tier promotion.",
        ))
    if cfg.target_molecule and entry.target_molecule:
        if _norm(entry.target_molecule) != _norm(cfg.target_molecule):
            issues.append(QualityGateIssue(
                "target_molecule_mismatch",
                "error",
                f"Calibration target {entry.target_molecule!r} does not match {cfg.target_molecule!r}.",
            ))

    conditions = {
        "temperature_C": entry.temperature_C,
        "ph": entry.ph,
        "salt_concentration_M": entry.salt_concentration_M,
    }
    issues.extend(_context_issues(conditions, cfg))
    return CalibrationQualityReport(
        passed=not any(issue.severity == "error" for issue in issues),
        issues=tuple(issues),
        metrics=metrics,
    )


def check_calibration_applicability(
    entry: CalibrationEntry,
    *,
    target_molecule: str = "",
    conditions: dict[str, Any] | None = None,
) -> CalibrationApplicability:
    """Check target and numeric valid-domain coverage for a recipe context."""
    reasons: list[str] = []
    conditions = dict(conditions or {})
    if target_molecule and entry.target_molecule:
        if _norm(target_molecule) != _norm(entry.target_molecule):
            reasons.append(
                f"target_molecule {target_molecule!r} outside calibration target {entry.target_molecule!r}"
            )
    for key, bounds in entry.valid_domain.items():
        if key not in conditions:
            reasons.append(f"missing condition {key!r} required by calibration domain")
            continue
        try:
            value = float(conditions[key])
            low, high = _bounds(bounds)
        except (TypeError, ValueError):
            continue
        if value < low or value > high:
            reasons.append(f"{key}={value:.4g} outside [{low:.4g}, {high:.4g}]")
    return CalibrationApplicability(
        applicable=not reasons,
        status="applicable" if not reasons else "not_applicable",
        reasons=tuple(reasons),
        matched_domain=dict(entry.valid_domain),
    )


def _context_issues(
    conditions: dict[str, Any],
    cfg: QualityGateConfig,
) -> tuple[QualityGateIssue, ...]:
    issues: list[QualityGateIssue] = []
    _numeric_context_gate(
        issues,
        conditions,
        "temperature_C",
        cfg.temperature_C,
        cfg.temperature_tolerance_C,
        "temperature_mismatch",
    )
    _numeric_context_gate(
        issues,
        conditions,
        "ph",
        cfg.ph,
        cfg.ph_tolerance,
        "ph_mismatch",
    )
    _numeric_context_gate(
        issues,
        conditions,
        "salt_concentration_M",
        cfg.salt_concentration_M,
        cfg.salt_tolerance_M,
        "salt_mismatch",
    )
    if cfg.target_molecule:
        observed = _first_string(conditions, ("target_molecule", "target_analyte", "protein_name"))
        if observed and _norm(observed) != _norm(cfg.target_molecule):
            issues.append(QualityGateIssue(
                "target_molecule_mismatch",
                "error",
                f"Assay target {observed!r} does not match {cfg.target_molecule!r}.",
            ))
    if cfg.mobile_phase:
        observed = _first_string(conditions, ("mobile_phase", "buffer", "buffer_name"))
        if observed and _norm(observed) != _norm(cfg.mobile_phase):
            issues.append(QualityGateIssue(
                "mobile_phase_mismatch",
                "error",
                f"Mobile phase {observed!r} does not match {cfg.mobile_phase!r}.",
            ))
    return tuple(issues)


def _numeric_context_gate(
    issues: list[QualityGateIssue],
    conditions: dict[str, Any],
    key: str,
    expected: float | None,
    tolerance: float,
    code: str,
) -> None:
    if expected is None:
        return
    if key not in conditions:
        issues.append(QualityGateIssue(code, "warning", f"Missing {key} condition."))
        return
    try:
        observed = float(conditions[key])
    except (TypeError, ValueError):
        issues.append(QualityGateIssue(code, "error", f"Non-numeric {key} condition."))
        return
    if abs(observed - expected) > tolerance:
        issues.append(QualityGateIssue(
            code,
            "error",
            f"{key}={observed:.4g} differs from required {expected:.4g} by more than {tolerance:.4g}.",
        ))


def _bounds(bounds: Any) -> tuple[float, float]:
    if isinstance(bounds, dict):
        return float(bounds["min"]), float(bounds["max"])
    if isinstance(bounds, Iterable):
        values = list(bounds)
        return float(values[0]), float(values[1])
    raise TypeError("bounds must be a two-value iterable or dict")


def _first_string(data: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _norm(value: str) -> str:
    return str(value).strip().casefold().replace(" ", "")


__all__ = [
    "CalibrationQualityReport",
    "QualityGateConfig",
    "QualityGateIssue",
    "check_calibration_applicability",
    "evaluate_assay_record",
    "evaluate_calibration_entry",
]
