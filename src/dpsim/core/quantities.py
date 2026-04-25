"""Unit-aware scalar values used at clean architecture boundaries.

The reused solver stack is intentionally numeric and SI-heavy for speed. This
module gives the outer process architecture a stricter representation for
values that cross module boundaries, where wet-lab units such as mL/min, mM,
percent w/v, and bar otherwise become a major source of hidden errors.

This is not a full unit algebra package. It covers the high-frequency unit
families needed by M1/M2/M3 recipes and records provenance so future code can
replace it with Pint or another formal unit system without changing the public
concept.

v0.6.1 (F1) — ``unwrap_to_unit`` is the documented helper for entry points
that want to accept either a ``Quantity`` or a bare ``float``. Use it to
normalize a Quantity-or-float input to a plain float in the expected unit.
"""

from __future__ import annotations

from dataclasses import dataclass


_LINEAR_TO_SI: dict[str, tuple[str, float]] = {
    # length
    "m": ("m", 1.0),
    "cm": ("m", 1e-2),
    "mm": ("m", 1e-3),
    "um": ("m", 1e-6),
    "nm": ("m", 1e-9),
    # volume
    "m3": ("m3", 1.0),
    "L": ("m3", 1e-3),
    "mL": ("m3", 1e-6),
    # time
    "s": ("s", 1.0),
    "min": ("s", 60.0),
    "h": ("s", 3600.0),
    # frequency and rotation rates
    "1/s": ("1/s", 1.0),
    "1/min": ("1/s", 1.0 / 60.0),
    "rpm": ("1/s", 1.0 / 60.0),
    # mass concentration
    "kg/m3": ("kg/m3", 1.0),
    "g/L": ("kg/m3", 1.0),
    "mg/mL": ("kg/m3", 1.0),
    # amount and concentration
    "mol": ("mol", 1.0),
    "mol/m3": ("mol/m3", 1.0),
    "mM": ("mol/m3", 1.0),  # 1 mM = 1 mol/m3
    "M": ("mol/m3", 1000.0),
    # pressure and modulus
    "Pa": ("Pa", 1.0),
    "kPa": ("Pa", 1000.0),
    "bar": ("Pa", 1e5),
    # electrical conductivity
    "S/m": ("S/m", 1.0),
    "mS/cm": ("S/m", 0.1),
    # absolute temperature and common ramp rates
    "K": ("K", 1.0),
    "K/s": ("K/s", 1.0),
    "K/min": ("K/s", 1.0 / 60.0),
    "K/h": ("K/s", 1.0 / 3600.0),
    # common flow rates
    "m3/s": ("m3/s", 1.0),
    "mL/min": ("m3/s", 1e-6 / 60.0),
    "mL/h": ("m3/s", 1e-6 / 3600.0),
    # dimensionless labels
    "1": ("1", 1.0),
    "fraction": ("1", 1.0),
    "%": ("1", 0.01),
}


@dataclass(frozen=True)
class Quantity:
    """Scalar value with unit, provenance, optional uncertainty, and bounds.

    Attributes:
        value: Numeric value in the stated ``unit``.
        unit: Unit label. Prefer SI at internal boundaries; common lab units
            are accepted at recipe/UI boundaries.
        uncertainty: One-sigma uncertainty in the same unit. Use ``0`` when
            unknown rather than pretending the parameter is exact.
        source: Human-readable source such as ``default``, ``literature``,
            ``user_input``, ``calibration:<id>``, or a lab notebook reference.
        lower: Optional lower validity bound in the same unit.
        upper: Optional upper validity bound in the same unit.
        note: Short scientific or wet-lab caveat.
    """

    value: float
    unit: str
    uncertainty: float = 0.0
    source: str = "unspecified"
    lower: float | None = None
    upper: float | None = None
    note: str = ""

    def to_si(self) -> "Quantity":
        """Return the quantity converted to the local SI basis.

        Temperature requires an offset conversion and is therefore handled by
        ``as_unit`` directly. For all linear units, bounds and uncertainty are
        scaled together with the value.
        """
        if self.unit == "degC":
            return self.as_unit("K")
        try:
            si_unit, scale = _LINEAR_TO_SI[self.unit]
        except KeyError as exc:
            raise ValueError(f"Unsupported unit for SI conversion: {self.unit}") from exc
        return Quantity(
            value=self.value * scale,
            unit=si_unit,
            uncertainty=self.uncertainty * abs(scale),
            source=self.source,
            lower=None if self.lower is None else self.lower * scale,
            upper=None if self.upper is None else self.upper * scale,
            note=self.note,
        )

    def as_unit(self, target_unit: str) -> "Quantity":
        """Convert to ``target_unit`` when both units share a supported basis."""
        if self.unit == target_unit:
            return self
        if self.unit == "degC" and target_unit == "K":
            return Quantity(
                self.value + 273.15,
                "K",
                self.uncertainty,
                self.source,
                None if self.lower is None else self.lower + 273.15,
                None if self.upper is None else self.upper + 273.15,
                self.note,
            )
        if self.unit == "K" and target_unit == "degC":
            return Quantity(
                self.value - 273.15,
                "degC",
                self.uncertainty,
                self.source,
                None if self.lower is None else self.lower - 273.15,
                None if self.upper is None else self.upper - 273.15,
                self.note,
            )

        src_unit, src_scale = _LINEAR_TO_SI.get(self.unit, (None, None))
        dst_unit, dst_scale = _LINEAR_TO_SI.get(target_unit, (None, None))
        if src_unit is None or dst_unit is None or src_unit != dst_unit:
            raise ValueError(f"Cannot convert {self.unit!r} to {target_unit!r}")
        factor = src_scale / dst_scale
        return Quantity(
            value=self.value * factor,
            unit=target_unit,
            uncertainty=self.uncertainty * abs(factor),
            source=self.source,
            lower=None if self.lower is None else self.lower * factor,
            upper=None if self.upper is None else self.upper * factor,
            note=self.note,
        )

    def is_within_bounds(self) -> bool:
        """Return True when the value is inside its optional validity bounds."""
        if self.lower is not None and self.value < self.lower:
            return False
        if self.upper is not None and self.value > self.upper:
            return False
        return True

    def describe(self) -> str:
        """Compact human-readable representation for reports and handovers."""
        base = f"{self.value:g} {self.unit}"
        if self.uncertainty:
            base += f" +/- {self.uncertainty:g}"
        if self.source:
            base += f" ({self.source})"
        return base


def unwrap_to_unit(value, expected_unit: str) -> float:
    """Coerce a ``Quantity | float | int`` argument into a float in ``expected_unit``.

    v0.6.1 (F1) — entry points (``run_breakthrough``, ``run_chromatography_method``,
    etc.) call this helper at the start of their bodies so callers can pass
    either a typed ``Quantity`` (auto-converted to the expected unit) or a
    bare ``float`` (assumed already in the expected unit).

    Args:
        value: Either a ``Quantity``, ``float``, or ``int``.
        expected_unit: The unit the solver internals expect (e.g. "mol/m3",
            "m3/s", "s", "Pa"). Must be a unit recognised by ``Quantity.as_unit``
            for the Quantity-input branch.

    Returns:
        A plain ``float`` in ``expected_unit``.

    Raises:
        ValueError: When a ``Quantity`` is passed and its unit cannot be
            converted to ``expected_unit``.
        TypeError: When ``value`` is neither numeric nor a ``Quantity``.
    """
    if isinstance(value, Quantity):
        return float(value.as_unit(expected_unit).value)
    if isinstance(value, (int, float)):
        return float(value)
    raise TypeError(
        f"unwrap_to_unit: expected Quantity or float, got {type(value).__name__}"
    )
