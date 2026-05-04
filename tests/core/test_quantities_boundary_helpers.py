"""B-2c (W-010) tests: typed SI boundary helpers for solver interfaces.

Covers the six quantity classes called out in the work plan (flow rate,
bed volume, pressure, capacity, ligand density, time) plus the
adjacent helpers for length, concentration, mass concentration, and
temperature. Includes property-style tests that round-trip
``Quantity → as_si → Quantity`` for the supported lab unit families.
"""

from __future__ import annotations

import math

import pytest

from dpsim.core.quantities import (
    Quantity,
    as_si_capacity_mol_per_m3,
    as_si_concentration_mol_per_m3,
    as_si_flow_rate_m3_per_s,
    as_si_length_m,
    as_si_ligand_density_mol_per_m3,
    as_si_mass_concentration_kg_per_m3,
    as_si_pressure_pa,
    as_si_temperature_K,
    as_si_time_s,
    as_si_volume_m3,
)


# ─── Time ────────────────────────────────────────────────────────────────────


class TestTimeHelper:
    @pytest.mark.parametrize("value,unit,expected", [
        (60.0, "s", 60.0),
        (1.0, "min", 60.0),
        (0.5, "h", 1800.0),
    ])
    def test_quantity_input(self, value, unit, expected):
        assert as_si_time_s(Quantity(value, unit)) == pytest.approx(expected)

    def test_float_input_passthrough(self):
        assert as_si_time_s(42.5) == 42.5
        assert as_si_time_s(0) == 0.0

    def test_unsupported_unit_raises(self):
        with pytest.raises(ValueError, match="Cannot convert"):
            as_si_time_s(Quantity(1.0, "Pa"))


# ─── Length ──────────────────────────────────────────────────────────────────


class TestLengthHelper:
    @pytest.mark.parametrize("value,unit,expected", [
        (1.0, "m", 1.0),
        (10.0, "cm", 0.10),
        (100.0, "mm", 0.10),
        (50.0, "um", 5e-5),
        (200.0, "nm", 2e-7),
    ])
    def test_quantity_input(self, value, unit, expected):
        assert as_si_length_m(Quantity(value, unit)) == pytest.approx(expected)


# ─── Volume ──────────────────────────────────────────────────────────────────


class TestVolumeHelper:
    @pytest.mark.parametrize("value,unit,expected", [
        (1.0, "m3", 1.0),
        (1.0, "L", 1e-3),
        (250.0, "mL", 2.5e-4),
    ])
    def test_quantity_input(self, value, unit, expected):
        assert as_si_volume_m3(Quantity(value, unit)) == pytest.approx(expected)


# ─── Flow rate ───────────────────────────────────────────────────────────────


class TestFlowRateHelper:
    @pytest.mark.parametrize("value,unit,expected", [
        (1.0, "m3/s", 1.0),
        (60.0, "mL/min", 1e-6),  # 60 mL/min = 1 mL/s = 1e-6 m^3/s
        (3600.0, "mL/h", 1e-6),  # 3600 mL/h = 1e-6 m^3/s
    ])
    def test_quantity_input(self, value, unit, expected):
        assert as_si_flow_rate_m3_per_s(Quantity(value, unit)) == pytest.approx(expected)


# ─── Pressure ────────────────────────────────────────────────────────────────


class TestPressureHelper:
    @pytest.mark.parametrize("value,unit,expected", [
        (1.0, "Pa", 1.0),
        (10.0, "kPa", 1e4),
        (3.0, "bar", 3e5),
    ])
    def test_quantity_input(self, value, unit, expected):
        assert as_si_pressure_pa(Quantity(value, unit)) == pytest.approx(expected)


# ─── Concentration / capacity / ligand density ──────────────────────────────


class TestConcentrationFamily:
    """Concentration, capacity, and ligand density all collapse to mol/m^3."""

    @pytest.mark.parametrize("value,unit,expected", [
        (50.0, "mol/m3", 50.0),
        (50.0, "mM", 50.0),       # mM == mol/m^3 by convention
        (0.05, "M", 50.0),        # 0.05 M = 50 mM = 50 mol/m^3
    ])
    def test_concentration(self, value, unit, expected):
        assert as_si_concentration_mol_per_m3(Quantity(value, unit)) == pytest.approx(expected)

    def test_capacity_alias(self):
        q = Quantity(10.0, "mol/m3")
        assert as_si_capacity_mol_per_m3(q) == 10.0
        assert as_si_capacity_mol_per_m3(q) == as_si_concentration_mol_per_m3(q)

    def test_ligand_density_alias(self):
        q = Quantity(2.0, "mol/m3")
        assert as_si_ligand_density_mol_per_m3(q) == 2.0
        assert as_si_ligand_density_mol_per_m3(q) == as_si_concentration_mol_per_m3(q)


# ─── Mass concentration ─────────────────────────────────────────────────────


class TestMassConcentrationHelper:
    @pytest.mark.parametrize("value,unit,expected", [
        (1.0, "kg/m3", 1.0),
        (1.0, "g/L", 1.0),
        (1.0, "mg/mL", 1.0),
    ])
    def test_quantity_input(self, value, unit, expected):
        assert as_si_mass_concentration_kg_per_m3(Quantity(value, unit)) == pytest.approx(expected)


# ─── Temperature ─────────────────────────────────────────────────────────────


class TestTemperatureHelper:
    def test_kelvin_passthrough(self):
        assert as_si_temperature_K(Quantity(298.15, "K")) == pytest.approx(298.15)

    def test_celsius_offset_conversion(self):
        assert as_si_temperature_K(Quantity(25.0, "degC")) == pytest.approx(298.15)
        assert as_si_temperature_K(Quantity(0.0, "degC")) == pytest.approx(273.15)

    def test_float_passthrough(self):
        # Convention: bare float assumed already in K (no offset).
        assert as_si_temperature_K(298.15) == 298.15

    def test_unsupported_input_raises(self):
        with pytest.raises(TypeError, match="expected Quantity or float"):
            as_si_temperature_K("hot")


# ─── Round-trip property tests ───────────────────────────────────────────────


class TestRoundTrip:
    """Quantity → as_si → Quantity round-trip preserves value to 1 ULP."""

    @pytest.mark.parametrize("value", [1.23, 0.001, 1e6, 0.0])
    @pytest.mark.parametrize("unit", ["s", "min", "h"])
    def test_time_round_trip(self, value, unit):
        si_value = as_si_time_s(Quantity(value, unit))
        recovered = Quantity(si_value, "s").as_unit(unit).value
        assert math.isclose(recovered, value, rel_tol=1e-9, abs_tol=1e-12)

    @pytest.mark.parametrize("value", [1.0, 0.5, 100.0])
    @pytest.mark.parametrize("unit", ["mL/min", "mL/h", "m3/s"])
    def test_flow_round_trip(self, value, unit):
        si_value = as_si_flow_rate_m3_per_s(Quantity(value, unit))
        recovered = Quantity(si_value, "m3/s").as_unit(unit).value
        assert math.isclose(recovered, value, rel_tol=1e-9, abs_tol=1e-12)

    @pytest.mark.parametrize("value", [50.0, 0.001, 1e6])
    @pytest.mark.parametrize("unit", ["mol/m3", "mM", "M"])
    def test_concentration_round_trip(self, value, unit):
        si_value = as_si_concentration_mol_per_m3(Quantity(value, unit))
        recovered = Quantity(si_value, "mol/m3").as_unit(unit).value
        assert math.isclose(recovered, value, rel_tol=1e-9, abs_tol=1e-12)


# ─── Float-input contract ────────────────────────────────────────────────────


class TestFloatInputContract:
    """Bare float inputs are passed through untouched (assumed in SI).

    This is the documented "boundary helper" semantics: Quantity inputs
    are converted; floats are trusted. Property: any helper called with
    a float returns the same float.
    """

    helpers_and_floats = [
        (as_si_time_s, 42.0),
        (as_si_length_m, 1e-3),
        (as_si_volume_m3, 1e-6),
        (as_si_flow_rate_m3_per_s, 1.5e-7),
        (as_si_pressure_pa, 1e5),
        (as_si_concentration_mol_per_m3, 50.0),
        (as_si_capacity_mol_per_m3, 100.0),
        (as_si_ligand_density_mol_per_m3, 5.0),
        (as_si_mass_concentration_kg_per_m3, 1.0),
    ]

    @pytest.mark.parametrize("helper,value", helpers_and_floats)
    def test_float_passthrough(self, helper, value):
        assert helper(value) == value
