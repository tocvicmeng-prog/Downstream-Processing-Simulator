"""Tests for imidazole-modulated Langmuir adapter (B-1m / W-038, v0.8.2).

Mirrors the W-034 test pattern — math, adapter routing, tier ladder.
"""

from __future__ import annotations

import numpy as np
import pytest

from dpsim.datatypes import ModelEvidenceTier
from dpsim.module3_performance.isotherms.adapter import EquilibriumAdapter
from dpsim.module3_performance.isotherms.imidazole_dependent import (
    ImidazoleModulatedLangmuir,
    imidazole_modulation_factor,
)
from dpsim.module3_performance.isotherms.langmuir import LangmuirIsotherm


# ─── Pure factor math ──────────────────────────────────────────────────────


class TestFactorMath:
    def test_factor_one_at_reference(self):
        assert imidazole_modulation_factor(50.0, c_imidazole_ref_mol_m3=50.0, n=1.5) == 1.0

    def test_factor_above_one_below_reference(self):
        f = imidazole_modulation_factor(25.0, c_imidazole_ref_mol_m3=50.0, n=1.5)
        assert f == pytest.approx(2.0 ** 1.5, rel=1e-12)

    def test_factor_below_one_above_reference(self):
        f = imidazole_modulation_factor(100.0, c_imidazole_ref_mol_m3=50.0, n=1.5)
        assert f == pytest.approx(0.5 ** 1.5, rel=1e-12)

    def test_floor_prevents_divide_by_zero(self):
        f = imidazole_modulation_factor(0.0, c_imidazole_ref_mol_m3=50.0, n=1.5)
        assert np.isfinite(f)
        assert f > 1e3

    def test_n_zero_disables_modulation(self):
        assert imidazole_modulation_factor(20.0, n=0.0) == 1.0

    def test_negative_n_rejected(self):
        with pytest.raises(ValueError, match="n="):
            imidazole_modulation_factor(50.0, n=-1.0)

    def test_oversized_n_rejected(self):
        with pytest.raises(ValueError, match="n="):
            imidazole_modulation_factor(50.0, n=15.0)

    def test_nonpositive_reference_rejected(self):
        with pytest.raises(ValueError, match="c_imidazole_ref"):
            imidazole_modulation_factor(50.0, c_imidazole_ref_mol_m3=0.0, n=1.5)


# ─── Adapter ──────────────────────────────────────────────────────────────


@pytest.fixture
def base_langmuir():
    return LangmuirIsotherm(q_max=80.0, K_L=1.0e4)


class TestAdapter:
    def test_no_imidazole_passes_through(self, base_langmuir):
        ml = ImidazoleModulatedLangmuir(base=base_langmuir)
        assert ml.equilibrium_loading(0.001) == pytest.approx(
            base_langmuir.equilibrium_loading(0.001), rel=1e-12,
        )

    def test_imidazole_at_reference_matches_base(self, base_langmuir):
        ml = ImidazoleModulatedLangmuir(
            base=base_langmuir, c_imidazole_ref_mol_m3=50.0,
        )
        ref = base_langmuir.equilibrium_loading(0.001)
        modulated = ml.equilibrium_loading(0.001, c_imidazole_mol_m3=50.0)
        assert modulated == pytest.approx(ref, rel=1e-12)

    def test_low_imidazole_enhances_loading(self, base_langmuir):
        ml = ImidazoleModulatedLangmuir(
            base=base_langmuir, c_imidazole_ref_mol_m3=50.0, n=1.5,
        )
        ref = base_langmuir.equilibrium_loading(0.001)
        load = ml.equilibrium_loading(0.001, c_imidazole_mol_m3=25.0)
        assert load > ref
        assert load == pytest.approx(ref * (2.0 ** 1.5), rel=1e-12)

    def test_high_imidazole_suppresses_loading(self, base_langmuir):
        ml = ImidazoleModulatedLangmuir(
            base=base_langmuir, c_imidazole_ref_mol_m3=50.0, n=1.5,
        )
        ref = base_langmuir.equilibrium_loading(0.001)
        load = ml.equilibrium_loading(0.001, c_imidazole_mol_m3=200.0)
        assert load < ref
        assert load == pytest.approx(ref * (0.25 ** 1.5), rel=1e-12)

    def test_jacobian_modulation_matches_loading(self, base_langmuir):
        ml = ImidazoleModulatedLangmuir(
            base=base_langmuir, c_imidazole_ref_mol_m3=50.0, n=1.5,
        )
        ref_j = base_langmuir.jacobian(0.001)
        mod_j = ml.jacobian(0.001, c_imidazole_mol_m3=200.0)
        assert mod_j == pytest.approx(ref_j * (0.25 ** 1.5), rel=1e-12)


class TestTierLadder:
    def test_default_semi_quantitative(self, base_langmuir):
        ml = ImidazoleModulatedLangmuir(base=base_langmuir)
        assert ml.evidence_tier == ModelEvidenceTier.SEMI_QUANTITATIVE

    def test_calibrated_flag_promotes(self, base_langmuir):
        ml = ImidazoleModulatedLangmuir(
            base=base_langmuir, calibrated_locally=True,
        )
        assert ml.evidence_tier == ModelEvidenceTier.CALIBRATED_LOCAL


class TestValidate:
    def test_clean_adapter_no_errors(self, base_langmuir):
        assert ImidazoleModulatedLangmuir(base=base_langmuir).validate() == []

    def test_bad_n_flagged(self, base_langmuir):
        ml = ImidazoleModulatedLangmuir(base=base_langmuir, n=-2.0)
        assert any("n=" in e for e in ml.validate())

    def test_zero_reference_flagged(self, base_langmuir):
        ml = ImidazoleModulatedLangmuir(
            base=base_langmuir, c_imidazole_ref_mol_m3=0.0,
        )
        assert any("c_imidazole_ref" in e for e in ml.validate())


# ─── EquilibriumAdapter integration ───────────────────────────────────────


class TestEquilibriumAdapterRouting:
    def test_adapter_routes_imidazole(self, base_langmuir):
        ml = ImidazoleModulatedLangmuir(
            base=base_langmuir, c_imidazole_ref_mol_m3=50.0, n=1.5,
        )
        adapter = EquilibriumAdapter(
            isotherm=ml, process_state={"imidazole": 25.0},
        )
        ref = base_langmuir.equilibrium_loading(0.001)
        modulated = adapter.equilibrium_loading(0.001)
        assert modulated == pytest.approx(ref * (2.0 ** 1.5), rel=1e-12)

    def test_adapter_handles_missing_imidazole(self, base_langmuir):
        ml = ImidazoleModulatedLangmuir(base=base_langmuir)
        adapter = EquilibriumAdapter(isotherm=ml, process_state={})
        ref = base_langmuir.equilibrium_loading(0.001)
        result = adapter.equilibrium_loading(0.001)
        assert result == pytest.approx(ref, rel=1e-12)

    def test_adapter_responds_to_imidazole_step(self, base_langmuir):
        ml = ImidazoleModulatedLangmuir(
            base=base_langmuir, c_imidazole_ref_mol_m3=50.0, n=1.5,
        )
        adapter = EquilibriumAdapter(
            isotherm=ml, process_state={"imidazole": 50.0},
        )
        load_at_ref = adapter.equilibrium_loading(0.001)
        adapter.update_process_state("imidazole", 200.0)
        load_after = adapter.equilibrium_loading(0.001)
        assert load_after < load_at_ref
        assert load_after == pytest.approx(
            load_at_ref * (0.25 ** 1.5), rel=1e-12,
        )
