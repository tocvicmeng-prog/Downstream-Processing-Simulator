"""Backend validation reports shared by UI, CLI, and process orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from numbers import Real
from typing import Any

from dpsim.datatypes import ModelManifest


class ValidationSeverity(Enum):
    """Severity class for a scientific, numerical, or wet-lab validation issue."""

    INFO = "info"
    WARNING = "warning"
    BLOCKER = "blocker"


@dataclass(frozen=True)
class ValidationIssue:
    """One validation finding with explicit scientific context."""

    severity: ValidationSeverity
    code: str
    message: str
    module: str = ""
    recommendation: str = ""


@dataclass
class ValidationReport:
    """Collection of validation issues.

    Reports are used instead of raising exceptions for scientific warnings so a
    user can still inspect exploratory results while blockers remain machine
    detectable.
    """

    issues: list[ValidationIssue] = field(default_factory=list)

    def add(
        self,
        severity: ValidationSeverity,
        code: str,
        message: str,
        module: str = "",
        recommendation: str = "",
    ) -> None:
        """Append a validation issue."""
        self.issues.append(
            ValidationIssue(
                severity=severity,
                code=code,
                message=message,
                module=module,
                recommendation=recommendation,
            )
        )

    @property
    def blockers(self) -> list[ValidationIssue]:
        """Blocking issues that should prevent decision use."""
        return [i for i in self.issues if i.severity == ValidationSeverity.BLOCKER]

    @property
    def warnings(self) -> list[ValidationIssue]:
        """Non-blocking issues that downgrade confidence."""
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]

    @property
    def ok_for_decision(self) -> bool:
        """True when no blockers are present."""
        return not self.blockers

    def extend(self, other: "ValidationReport") -> None:
        """Append all issues from another report."""
        self.issues.extend(other.issues)


def validate_model_manifest_domains(
    manifests: list[ModelManifest],
    module: str = "",
) -> ValidationReport:
    """Check manifest diagnostics against declared model validity domains.

    A manifest can state a ``valid_domain`` such as ``{"Re": (100, 1e6)}``.
    This helper looks for matching diagnostic values, including values nested
    one dictionary level down, and reports warning-level domain exits. Domain
    warnings are deliberately not blockers because many exploratory simulations
    still produce useful qualitative trends outside the fitted range.
    """

    report = ValidationReport()
    for manifest in manifests:
        diagnostics = manifest.diagnostics or {}
        for key, domain in (manifest.valid_domain or {}).items():
            bounds = _as_numeric_bounds(domain)
            if bounds is None:
                continue
            value = _find_diagnostic_value(diagnostics, key)
            if value is None:
                continue
            lower, upper = bounds
            if lower <= value <= upper:
                continue
            code = "CALIBRATION_DOMAIN" if manifest.calibration_ref else "MODEL_DOMAIN"
            report.add(
                ValidationSeverity.WARNING,
                code,
                (
                    f"{manifest.model_name} diagnostic {key}={value:g} is "
                    f"outside declared domain [{lower:g}, {upper:g}]."
                ),
                module=module,
                recommendation=(
                    "Treat this result as extrapolative until the relevant "
                    "model is calibrated in this operating window."
                ),
            )
    return report


def _as_numeric_bounds(domain: Any) -> tuple[float, float] | None:
    """Return numeric lower/upper bounds when ``domain`` encodes a range."""
    if not isinstance(domain, (tuple, list)) or len(domain) != 2:
        return None
    lower, upper = domain
    if not isinstance(lower, Real) or not isinstance(upper, Real):
        return None
    return float(lower), float(upper)


def _find_diagnostic_value(diagnostics: dict[str, Any], key: str) -> float | None:
    """Find a numeric diagnostic value at top level or one nested dict level."""
    value = diagnostics.get(key)
    if isinstance(value, Real):
        return float(value)
    for nested in diagnostics.values():
        if isinstance(nested, dict):
            value = nested.get(key)
            if isinstance(value, Real):
                return float(value)
    return None
