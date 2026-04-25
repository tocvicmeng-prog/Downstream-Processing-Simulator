"""Resolved model parameters and source-priority handling.

Clean-slate architecture requires the simulator to know why a parameter has a
particular value. A calibrated L1 breakage constant, a literature default, and a
UI slider value can all be numerically identical but have very different
scientific meaning. These classes preserve that distinction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .quantities import Quantity


class ParameterSource(Enum):
    """Source class for a parameter value."""

    DEFAULT = "default"
    LITERATURE = "literature"
    USER_INPUT = "user_input"
    CALIBRATION = "calibration"
    FITTED = "fitted"
    INFERRED = "inferred"


_SOURCE_PRIORITY = {
    ParameterSource.DEFAULT: 0,
    ParameterSource.LITERATURE: 1,
    ParameterSource.INFERRED: 2,
    ParameterSource.FITTED: 3,
    ParameterSource.CALIBRATION: 4,
    ParameterSource.USER_INPUT: 5,
}


@dataclass(frozen=True)
class ResolvedParameter:
    """A model parameter after source resolution and unit normalization."""

    name: str
    quantity: Quantity
    source_kind: ParameterSource = ParameterSource.DEFAULT
    valid_domain: dict[str, tuple[float, float] | str] = field(default_factory=dict)
    evidence_note: str = ""

    def si_value(self) -> float:
        """Return numeric value converted to the supported SI basis."""
        return self.quantity.to_si().value


class ParameterProvider:
    """Deterministic parameter resolver with explicit source priority.

    The provider stores candidate values by name and returns the candidate with
    the highest source priority. This is intentionally simple; it provides a
    stable seam for future Bayesian posterior and validity-domain logic.
    """

    def __init__(self) -> None:
        self._values: dict[str, list[ResolvedParameter]] = {}

    def add(self, parameter: ResolvedParameter) -> None:
        """Register a candidate value for later resolution."""
        self._values.setdefault(parameter.name, []).append(parameter)

    def resolve(self, name: str) -> ResolvedParameter:
        """Return the highest-priority candidate for ``name``."""
        candidates = self._values.get(name, [])
        if not candidates:
            raise KeyError(f"No resolved parameter registered for {name!r}")
        return max(candidates, key=lambda p: _SOURCE_PRIORITY[p.source_kind])

    def as_dict(self) -> dict[str, ResolvedParameter]:
        """Resolve all known parameter names into a dictionary."""
        return {name: self.resolve(name) for name in self._values}
