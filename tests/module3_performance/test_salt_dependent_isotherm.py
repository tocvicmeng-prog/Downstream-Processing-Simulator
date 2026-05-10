"""Tests for the salt-modulated Langmuir adapter (B-1j / W-034, v0.8.1).

Covers ADR-005 acceptance:

* ``salt_modulation_factor`` math: factor=1 at reference, >1 below, <1
  above; ν exponent applied; floors enforced.
* ``SaltModulatedLangmuir.equilibrium_loading``: no salt → bare base;
  with salt → modulated.
* ``SaltModulatedLangmuir.jacobian``: same modulation as q_eq.
* Tier ladder: ``calibrated_locally`` flag promotes
  SEMI_QUANTITATIVE → CALIBRATED_LOCAL.
* ``EquilibriumAdapter`` routes the new isotherm class through its
  ``salt_concentration`` state field.
"""

from __future__ import annotations

import numpy as np
import pytest

from dpsim.datatypes import ModelEvidenceTier
from dpsim.module3_performance.isotherms.adapter import EquilibriumAdapter
from dpsim.module3_performance.isotherms.langmuir import LangmuirIsotherm
from dpsim.module3_performance.isotherms.salt_dependent import (
    SaltModulatedLangmuir,
    salt_modulation_factor,
)


# ─── salt_modulation_factor (pure math) ─────────────────────────────────────


class TestSaltModulationFactor:
    def test_factor_one_at_reference(self):
        assert salt_modulation_factor(150.0, c_salt_ref_mol_m3=150.0, nu=4.5) == 1.0

    def test_factor_above_one_below_reference(self):
        # Half the reference salt → factor = 2 ** ν
        f = salt_modulation_factor(75.0, c_salt_ref_mol_m3=150.0, nu=4.5)
        assert f == pytest.approx(2.0 ** 4.5, rel=1e-12)
        assert f > 1.0

    def test_factor_below_one_above_reference(self):
        # Double the reference salt → factor = 0.5 ** ν
        f = salt_modulation_factor(300.0, c_salt_ref_mol_m3=150.0, nu=4.5)
        assert f == pytest.approx(0.5 ** 4.5, rel=1e-12)
        assert f < 1.0

    def test_floor_prevents_divide_by_zero(self):
        # c_salt = 0 → factor finite via the 1e-6 floor.
        f = salt_modulation_factor(0.0, c_salt_ref_mol_m3=150.0, nu=4.5)
        assert np.isfinite(f)
        assert f > 1e10  # very large but finite

    def test_nu_exponent_zero_gives_factor_one(self):
        # ν = 0 → log K_a is salt-independent → factor always 1.
        assert salt_modulation_factor(50.0, nu=0.0) == 1.0
        assert salt_modulation_factor(2000.0, nu=0.0) == 1.0

    def test_negative_nu_rejected(self):
        with pytest.raises(ValueError, match="nu="):
            salt_modulation_factor(150.0, nu=-1.0)

    def test_oversized_nu_rejected(self):
        with pytest.raises(ValueError, match="nu="):
            salt_modulation_factor(150.0, nu=25.0)

    def test_nonpositive_reference_rejected(self):
        with pytest.raises(ValueError, match="c_salt_ref_mol_m3="):
            salt_modulation_factor(150.0, c_salt_ref_mol_m3=0.0, nu=4.5)


# ─── SaltModulatedLangmuir adapter ──────────────────────────────────────────


@pytest.fixture
def base_langmuir():
    return LangmuirIsotherm(q_max=100.0, K_L=1.0e3)


class TestSaltModulatedLangmuir:
    def test_no_salt_argument_passes_through(self, base_langmuir):
        sml = SaltModulatedLangmuir(base=base_langmuir)
        # When called without c_salt, behaves exactly like the base.
        assert sml.equilibrium_loading(0.001) == pytest.approx(
            base_langmuir.equilibrium_loading(0.001), rel=1e-12
        )

    def test_salt_at_reference_matches_base(self, base_langmuir):
        sml = SaltModulatedLangmuir(
            base=base_langmuir, c_salt_ref_mol_m3=150.0,
        )
        ref = base_langmuir.equilibrium_loading(0.001)
        modulated = sml.equilibrium_loading(0.001, c_salt_mol_m3=150.0)
        assert modulated == pytest.approx(ref, rel=1e-12)

    def test_low_salt_enhances_loading(self, base_langmuir):
        sml = SaltModulatedLangmuir(
            base=base_langmuir, c_salt_ref_mol_m3=150.0, nu=4.5,
        )
        ref = base_langmuir.equilibrium_loading(0.001)
        load = sml.equilibrium_loading(0.001, c_salt_mol_m3=75.0)
        assert load > ref
        # Quantitative: factor = (150/75)**4.5 = 2**4.5 ≈ 22.6
        assert load == pytest.approx(ref * (2.0 ** 4.5), rel=1e-12)

    def test_high_salt_suppresses_loading(self, base_langmuir):
        sml = SaltModulatedLangmuir(
            base=base_langmuir, c_salt_ref_mol_m3=150.0, nu=4.5,
        )
        ref = base_langmuir.equilibrium_loading(0.001)
        load = sml.equilibrium_loading(0.001, c_salt_mol_m3=300.0)
        assert load < ref
        assert load == pytest.approx(ref * (0.5 ** 4.5), rel=1e-12)

    def test_array_input(self, base_langmuir):
        sml = SaltModulatedLangmuir(
            base=base_langmuir, c_salt_ref_mol_m3=150.0, nu=4.5,
        )
        C = np.array([0.0, 0.0001, 0.001, 0.01])
        load_no_salt = sml.equilibrium_loading(C)
        load_high_salt = sml.equilibrium_loading(C, c_salt_mol_m3=300.0)
        # All elements scale by the same factor.
        ratios = load_high_salt[1:] / load_no_salt[1:]  # skip C=0 → 0/0
        np.testing.assert_allclose(ratios, 0.5 ** 4.5, rtol=1e-12)

    def test_jacobian_modulation_matches_loading(self, base_langmuir):
        sml = SaltModulatedLangmuir(
            base=base_langmuir, c_salt_ref_mol_m3=150.0, nu=4.5,
        )
        # The Jacobian should pick up the same multiplicative factor.
        ref_j = base_langmuir.jacobian(0.001)
        mod_j = sml.jacobian(0.001, c_salt_mol_m3=300.0)
        assert mod_j == pytest.approx(ref_j * (0.5 ** 4.5), rel=1e-12)

    def test_q_max_passes_through(self, base_langmuir):
        sml = SaltModulatedLangmuir(base=base_langmuir)
        assert sml.q_max == base_langmuir.q_max


class TestEvidenceTier:
    def test_default_is_semi_quantitative(self, base_langmuir):
        sml = SaltModulatedLangmuir(base=base_langmuir)
        assert sml.evidence_tier == ModelEvidenceTier.SEMI_QUANTITATIVE

    def test_calibrated_flag_promotes_tier(self, base_langmuir):
        sml = SaltModulatedLangmuir(
            base=base_langmuir, calibrated_locally=True,
        )
        assert sml.evidence_tier == ModelEvidenceTier.CALIBRATED_LOCAL


class TestValidate:
    def test_clean_adapter_has_no_errors(self, base_langmuir):
        sml = SaltModulatedLangmuir(base=base_langmuir)
        assert sml.validate() == []

    def test_bad_nu_flagged(self, base_langmuir):
        sml = SaltModulatedLangmuir(base=base_langmuir, nu=-2.0)
        errors = sml.validate()
        assert any("nu" in e for e in errors)

    def test_zero_reference_flagged(self, base_langmuir):
        sml = SaltModulatedLangmuir(base=base_langmuir, c_salt_ref_mol_m3=0.0)
        errors = sml.validate()
        assert any("c_salt_ref_mol_m3" in e for e in errors)


# ─── EquilibriumAdapter integration ────────────────────────────────────────


class TestEquilibriumAdapterRouting:
    def test_adapter_routes_salt_concentration(self, base_langmuir):
        """The LRM-side adapter passes salt_concentration into the new isotherm."""
        sml = SaltModulatedLangmuir(
            base=base_langmuir, c_salt_ref_mol_m3=150.0, nu=4.5,
        )
        adapter = EquilibriumAdapter(
            isotherm=sml,
            process_state={"salt_concentration": 75.0},
        )
        ref = base_langmuir.equilibrium_loading(0.001)
        modulated = adapter.equilibrium_loading(0.001)
        # 75 mM is half the reference 150 → factor 2**4.5.
        assert modulated == pytest.approx(ref * (2.0 ** 4.5), rel=1e-12)

    def test_adapter_handles_missing_salt_state(self, base_langmuir):
        """Missing salt_concentration in state degrades to bare base behavior."""
        sml = SaltModulatedLangmuir(base=base_langmuir)
        adapter = EquilibriumAdapter(isotherm=sml, process_state={})
        ref = base_langmuir.equilibrium_loading(0.001)
        # adapter.equilibrium_loading passes salt=None to the modulated
        # isotherm's equilibrium_loading, which degrades to bare base.
        result = adapter.equilibrium_loading(0.001)
        assert result == pytest.approx(ref, rel=1e-12)

    def test_adapter_responds_to_state_updates(self, base_langmuir):
        """Updating the salt field through update_process_state changes the loading."""
        sml = SaltModulatedLangmuir(
            base=base_langmuir, c_salt_ref_mol_m3=150.0, nu=4.5,
        )
        adapter = EquilibriumAdapter(
            isotherm=sml,
            process_state={"salt_concentration": 150.0},
        )
        load_at_ref = adapter.equilibrium_loading(0.001)
        adapter.update_process_state("salt_concentration", 300.0)
        load_after = adapter.equilibrium_loading(0.001)
        assert load_after < load_at_ref
        assert load_after == pytest.approx(
            load_at_ref * (0.5 ** 4.5), rel=1e-12,
        )

    def test_adapter_q_max_passthrough_for_modulated(self, base_langmuir):
        sml = SaltModulatedLangmuir(base=base_langmuir)
        adapter = EquilibriumAdapter(isotherm=sml)
        assert adapter.q_max == base_langmuir.q_max
