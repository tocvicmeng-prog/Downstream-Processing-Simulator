"""B-1g / W-021 tests: Sauter d32 wiring in _column_with_microsphere.

Pre-B-1g, ``_column_with_microsphere`` and ``_column_for_quantile`` set
``ColumnGeometry.particle_diameter`` from ``M1ExportContract.bead_d50``
(median diameter). Kozeny-Carman / Ergun derive from the surface-area-
equivalent diameter, which for a polydisperse population is the Sauter
mean d32 by definition. For a typical lognormal DSD with σ_ln = 0.3,
d32 ≈ 0.80 · d50 → ΔP underestimated by (d50/d32)² ≈ 1.56× when d50 is
used in place of d32.

These tests assert the swap is in place: the column constructed by
each helper reads ``m1.bead_d32``, not ``m1.bead_d50``.
"""

from __future__ import annotations

from types import SimpleNamespace

from dpsim.datatypes import M1ExportContract
from dpsim.module3_performance.hydrodynamics import ColumnGeometry
from dpsim.module3_performance.method_simulation import (
    _column_for_quantile,
    _column_with_microsphere,
)


# ─── Test fixtures ───────────────────────────────────────────────────────────


def _make_contract(*, bead_d32: float, bead_d50: float) -> M1ExportContract:
    """Minimal M1ExportContract with d32 ≠ d50 to verify the wiring."""
    return M1ExportContract(
        bead_radius=bead_d50 / 2.0,
        bead_d32=bead_d32,
        bead_d50=bead_d50,
        pore_size_mean=100e-9,
        pore_size_std=30e-9,
        porosity=0.70,
        l2_model_tier="empirical_calibrated",
        mesh_size_xi=20e-9,
        p_final=0.5,
        primary_crosslinker="genipin",
        nh2_bulk_concentration=100.0,
        oh_bulk_concentration=400.0,
        G_DN=5000.0,
        E_star=15000.0,
        model_used="phenomenological",
        c_agarose=42.0,
        c_chitosan=18.0,
        DDA=0.90,
        trust_level="CAUTION",
    )


def _make_microsphere_stub(
    *, contract: M1ExportContract, G_DN_updated: float = 0.0,
    E_star_updated: float = 0.0,
) -> SimpleNamespace:
    """Lightweight stub satisfying ``_column_with_microsphere``'s duck
    contract: only ``m1_contract``, ``G_DN_updated``, ``E_star_updated``
    are read by the helper.

    Using SimpleNamespace rather than constructing a full
    ``FunctionalMicrosphere`` keeps this test focused on the wiring;
    the integration cases in tests/test_module2_workflows.py exercise
    the full type.
    """
    return SimpleNamespace(
        m1_contract=contract,
        G_DN_updated=G_DN_updated,
        E_star_updated=E_star_updated,
    )


# ─── _column_with_microsphere ────────────────────────────────────────────────


class TestColumnWithMicrosphere:
    """The headline d32 swap — main consumption point for B-2f."""

    def test_particle_diameter_uses_d32_not_d50(self) -> None:
        contract = _make_contract(bead_d32=80e-6, bead_d50=100e-6)
        microsphere = _make_microsphere_stub(contract=contract)
        base = ColumnGeometry()  # default
        result = _column_with_microsphere(base, microsphere)
        assert result.particle_diameter == 80e-6

    def test_particle_diameter_does_not_silently_use_d50(self) -> None:
        contract = _make_contract(bead_d32=80e-6, bead_d50=100e-6)
        microsphere = _make_microsphere_stub(contract=contract)
        result = _column_with_microsphere(ColumnGeometry(), microsphere)
        # The whole point of W-021: this assertion would have failed
        # against pre-B-1g code.
        assert result.particle_diameter != 100e-6

    def test_dP_correction_factor_d50_to_d32(self) -> None:
        """At σ_ln = 0.3, d32 ≈ 0.80 · d50 → ΔP correction (d50/d32)² ≈ 1.56×."""
        contract = _make_contract(bead_d32=80e-6, bead_d50=100e-6)
        microsphere = _make_microsphere_stub(contract=contract)
        col_correct = _column_with_microsphere(ColumnGeometry(), microsphere)
        col_legacy = ColumnGeometry(particle_diameter=100e-6)  # what the bug
                                                                # would have given
        # ΔP scales as d_p⁻². At equal Q and μ, the ratio is (d_legacy/d_correct)².
        ratio = (col_legacy.particle_diameter / col_correct.particle_diameter) ** 2
        # 100e-6 / 80e-6 = 1.25 → ratio = 1.5625
        assert 1.50 < ratio < 1.65

    def test_returns_unchanged_column_when_microsphere_none(self) -> None:
        # Backwards compat: ``microsphere=None`` returns the input column.
        base = ColumnGeometry(particle_diameter=200e-6)
        assert _column_with_microsphere(base, None) is base

    def test_uses_m2_updated_modulus_when_set(self) -> None:
        # Crosscheck with existing G_DN / E_star wiring to confirm the
        # rest of the helper still works after the d32 swap.
        contract = _make_contract(bead_d32=80e-6, bead_d50=100e-6)
        microsphere = _make_microsphere_stub(
            contract=contract, G_DN_updated=12345.0, E_star_updated=37000.0
        )
        result = _column_with_microsphere(ColumnGeometry(), microsphere)
        assert result.G_DN == 12345.0
        assert result.E_star == 37000.0

    def test_falls_back_to_m1_modulus_when_m2_zero(self) -> None:
        contract = _make_contract(bead_d32=80e-6, bead_d50=100e-6)
        # G_DN_updated=0.0 → falsy → falls back to m1.G_DN
        microsphere = _make_microsphere_stub(contract=contract)
        result = _column_with_microsphere(ColumnGeometry(), microsphere)
        assert result.G_DN == contract.G_DN  # 5000.0
        assert result.E_star == contract.E_star  # 15000.0


# ─── _column_for_quantile ────────────────────────────────────────────────────


class TestColumnForQuantile:
    """The fallback path also reads d32 (not d50) when no quantile is supplied."""

    def test_fallback_to_d32_when_no_diameter(self) -> None:
        contract = _make_contract(bead_d32=70e-6, bead_d50=90e-6)
        microsphere = _make_microsphere_stub(contract=contract)
        result = _column_for_quantile(ColumnGeometry(), microsphere, 0.0)
        assert result.particle_diameter == 70e-6

    def test_fallback_to_d32_when_negative_diameter(self) -> None:
        contract = _make_contract(bead_d32=70e-6, bead_d50=90e-6)
        microsphere = _make_microsphere_stub(contract=contract)
        # diameter_m <= 0 → use the m1.bead_d32 fallback
        result = _column_for_quantile(ColumnGeometry(), microsphere, -1.0)
        assert result.particle_diameter == 70e-6

    def test_explicit_quantile_diameter_wins(self) -> None:
        contract = _make_contract(bead_d32=70e-6, bead_d50=90e-6)
        microsphere = _make_microsphere_stub(contract=contract)
        # User-supplied per-quantile diameter overrides the fallback.
        result = _column_for_quantile(ColumnGeometry(), microsphere, 110e-6)
        assert result.particle_diameter == 110e-6

    def test_no_microsphere_uses_base_particle_diameter(self) -> None:
        base = ColumnGeometry(particle_diameter=120e-6)
        result = _column_for_quantile(base, None, 0.0)
        assert result.particle_diameter == 120e-6
