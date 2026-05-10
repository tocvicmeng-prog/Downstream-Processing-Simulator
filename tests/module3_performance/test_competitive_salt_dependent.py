"""Tests for SaltModulatedCompetitiveLangmuir (B-2m / W-042, v0.8.2)."""

from __future__ import annotations

import numpy as np
import pytest

from dpsim.datatypes import ModelEvidenceTier
from dpsim.module3_performance.isotherms.adapter import EquilibriumAdapter
from dpsim.module3_performance.isotherms.competitive_langmuir import (
    CompetitiveLangmuirIsotherm,
)
from dpsim.module3_performance.isotherms.competitive_salt_dependent import (
    SaltModulatedCompetitiveLangmuir,
)


@pytest.fixture
def two_component_base():
    return CompetitiveLangmuirIsotherm(
        q_max=np.array([100.0, 80.0]),
        K_L=np.array([1.0e3, 5.0e2]),
    )


class TestNuVector:
    def test_default_nu_per_component(self, two_component_base):
        sml = SaltModulatedCompetitiveLangmuir(base=two_component_base)
        assert sml.nu.shape == (2,)
        assert np.allclose(sml.nu, 4.5)

    def test_custom_nu_per_component(self, two_component_base):
        sml = SaltModulatedCompetitiveLangmuir(
            base=two_component_base, nu=np.array([6.0, 3.0]),
        )
        assert np.allclose(sml.nu, [6.0, 3.0])

    def test_wrong_shape_rejected(self, two_component_base):
        with pytest.raises(ValueError, match="nu shape"):
            SaltModulatedCompetitiveLangmuir(
                base=two_component_base, nu=np.array([1.0, 2.0, 3.0]),
            )


class TestEquilibriumLoading:
    def test_no_salt_passes_through(self, two_component_base):
        sml = SaltModulatedCompetitiveLangmuir(base=two_component_base)
        C = np.array([0.001, 0.001])
        out = sml.equilibrium_loading(C)
        ref = two_component_base.equilibrium_loading(C)
        assert np.allclose(out, ref)

    def test_salt_at_reference_matches_base(self, two_component_base):
        sml = SaltModulatedCompetitiveLangmuir(
            base=two_component_base, c_salt_ref_mol_m3=150.0,
        )
        C = np.array([0.001, 0.001])
        out = sml.equilibrium_loading(C, c_salt_mol_m3=150.0)
        ref = two_component_base.equilibrium_loading(C)
        assert np.allclose(out, ref)

    def test_high_salt_displaces_strongly_bound_first(self, two_component_base):
        """Component 0 has higher K_L (more strongly bound) and equal ν → at
        elevated salt, the relative loading shifts toward component 1.

        With ν_0 = ν_1, the per-component factor is identical, so the
        relative ordering doesn't change. Use ν_0 > ν_1 to mimic SDM
        physics where higher-charge proteins lose binding faster."""
        sml = SaltModulatedCompetitiveLangmuir(
            base=two_component_base,
            nu=np.array([6.0, 3.0]),
            c_salt_ref_mol_m3=150.0,
        )
        C = np.array([0.001, 0.001])
        load_at_ref = sml.equilibrium_loading(C, c_salt_mol_m3=150.0)
        load_at_high = sml.equilibrium_loading(C, c_salt_mol_m3=600.0)
        # At high salt, both loadings drop, but component 0 (higher ν)
        # drops faster.
        ratio_at_ref = load_at_ref[0] / load_at_ref[1]
        ratio_at_high = load_at_high[0] / load_at_high[1]
        assert ratio_at_high < ratio_at_ref
        # Both loadings are smaller at high salt.
        assert load_at_high[0] < load_at_ref[0]
        assert load_at_high[1] < load_at_ref[1]

    def test_array_input_2d_shape(self, two_component_base):
        sml = SaltModulatedCompetitiveLangmuir(base=two_component_base)
        # 2 components, 5 spatial cells
        C = np.array([[0.001] * 5, [0.001] * 5])
        out = sml.equilibrium_loading(C, c_salt_mol_m3=150.0)
        assert out.shape == (2, 5)

    def test_low_salt_increases_loading(self, two_component_base):
        sml = SaltModulatedCompetitiveLangmuir(
            base=two_component_base, c_salt_ref_mol_m3=150.0,
        )
        C = np.array([0.0001, 0.0001])
        load_at_ref = sml.equilibrium_loading(C, c_salt_mol_m3=150.0)
        load_at_low = sml.equilibrium_loading(C, c_salt_mol_m3=50.0)
        assert np.all(load_at_low > load_at_ref)


class TestTierLadder:
    def test_default_semi_quantitative(self, two_component_base):
        sml = SaltModulatedCompetitiveLangmuir(base=two_component_base)
        assert sml.evidence_tier == ModelEvidenceTier.SEMI_QUANTITATIVE

    def test_calibrated_promotes(self, two_component_base):
        sml = SaltModulatedCompetitiveLangmuir(
            base=two_component_base, calibrated_locally=True,
        )
        assert sml.evidence_tier == ModelEvidenceTier.CALIBRATED_LOCAL


class TestValidate:
    def test_clean_no_errors(self, two_component_base):
        sml = SaltModulatedCompetitiveLangmuir(base=two_component_base)
        assert sml.validate() == []

    def test_oversized_nu_flagged(self, two_component_base):
        sml = SaltModulatedCompetitiveLangmuir(
            base=two_component_base, nu=np.array([4.5, 25.0]),
        )
        assert any("nu[1]" in e for e in sml.validate())


class TestAdapterRouting:
    def test_routes_through_equilibrium_adapter(self, two_component_base):
        sml = SaltModulatedCompetitiveLangmuir(
            base=two_component_base,
            nu=np.array([6.0, 3.0]),
            c_salt_ref_mol_m3=150.0,
        )
        adapter = EquilibriumAdapter(
            isotherm=sml, process_state={"salt_concentration": 150.0},
        )
        C = np.array([0.001, 0.001])
        out_ref = adapter.equilibrium_loading(C)
        # Switch to high salt — both loadings should drop.
        adapter.update_process_state("salt_concentration", 600.0)
        out_high = adapter.equilibrium_loading(C)
        assert np.all(out_high < out_ref)
