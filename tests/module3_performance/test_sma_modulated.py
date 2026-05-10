"""Tests for SaltModulatedSMA promotion adapter (B-1n / W-039, v0.8.2).

Verifies the swap-in promotion target documented in ADR-006:

* Same call signature as SaltModulatedLangmuir → drop-in replacement.
* Routes through EquilibriumAdapter.salt_concentration field.
* Validation rejects invalid SMA params.
* When σ = 0, behaviour reduces toward the Mollerup-simplified shape
  (sanity check that the SMA cost vanishes at σ = 0).
"""

from __future__ import annotations

import numpy as np
import pytest

from dpsim.datatypes import ModelEvidenceTier
from dpsim.module3_performance.isotherms.adapter import EquilibriumAdapter
from dpsim.module3_performance.isotherms.sma_modulated import SaltModulatedSMA


class TestEquilibriumLoading:
    def test_scalar_input_returns_scalar(self):
        sma = SaltModulatedSMA(z=4.5, sigma=50.0, K_eq=1e-3, Lambda=1000.0)
        out = sma.equilibrium_loading(0.001, c_salt_mol_m3=150.0)
        assert isinstance(out, float)
        assert out >= 0.0
        assert np.isfinite(out)

    def test_array_input_returns_array(self):
        sma = SaltModulatedSMA(z=4.5, sigma=50.0, K_eq=1e-3, Lambda=1000.0)
        out = sma.equilibrium_loading(
            np.array([0.0, 0.001, 0.01]), c_salt_mol_m3=150.0,
        )
        assert isinstance(out, np.ndarray)
        assert out.shape == (3,)
        assert np.all(out >= 0.0)

    def test_low_salt_increases_loading(self):
        sma = SaltModulatedSMA(z=4.5, sigma=50.0, K_eq=1e-3, Lambda=1000.0)
        load_high = sma.equilibrium_loading(0.001, c_salt_mol_m3=300.0)
        load_low = sma.equilibrium_loading(0.001, c_salt_mol_m3=75.0)
        assert load_low > load_high

    def test_default_salt_uses_reference(self):
        sma = SaltModulatedSMA(c_salt_ref_mol_m3=200.0)
        # No salt arg → uses 200 mM reference.
        out_default = sma.equilibrium_loading(0.001)
        out_explicit = sma.equilibrium_loading(0.001, c_salt_mol_m3=200.0)
        assert out_default == pytest.approx(out_explicit, rel=1e-9)

    def test_q_max_property(self):
        sma = SaltModulatedSMA(z=5.0, sigma=15.0, K_eq=1e-3, Lambda=1000.0)
        # q_max = Lambda / (z + sigma) = 1000 / 20 = 50
        assert sma.q_max == pytest.approx(50.0, rel=1e-12)

    def test_jacobian_returns_positive(self):
        sma = SaltModulatedSMA()
        j = sma.jacobian(0.001, c_salt_mol_m3=150.0)
        assert j > 0.0


class TestTierLadder:
    def test_default_semi_quantitative(self):
        sma = SaltModulatedSMA()
        assert sma.evidence_tier == ModelEvidenceTier.SEMI_QUANTITATIVE

    def test_calibrated_flag_promotes(self):
        sma = SaltModulatedSMA(calibrated_locally=True)
        assert sma.evidence_tier == ModelEvidenceTier.CALIBRATED_LOCAL


class TestValidate:
    def test_clean_adapter_no_errors(self):
        assert SaltModulatedSMA().validate() == []

    def test_negative_z_flagged(self):
        sma = SaltModulatedSMA(z=-1.0)
        assert any("z=" in e for e in sma.validate())

    def test_negative_sigma_flagged(self):
        sma = SaltModulatedSMA(sigma=-5.0)
        assert any("sigma" in e for e in sma.validate())

    def test_zero_K_eq_flagged(self):
        sma = SaltModulatedSMA(K_eq=0.0)
        assert any("K_eq" in e for e in sma.validate())

    def test_zero_Lambda_flagged(self):
        sma = SaltModulatedSMA(Lambda=0.0)
        assert any("Lambda" in e for e in sma.validate())

    def test_zero_reference_flagged(self):
        sma = SaltModulatedSMA(c_salt_ref_mol_m3=0.0)
        assert any("c_salt_ref" in e for e in sma.validate())


class TestAdapterRouting:
    def test_routes_salt_concentration_through_adapter(self):
        sma = SaltModulatedSMA(z=4.5, sigma=50.0, K_eq=1e-3, Lambda=1000.0)
        adapter = EquilibriumAdapter(
            isotherm=sma, process_state={"salt_concentration": 75.0},
        )
        load_low = adapter.equilibrium_loading(0.001)
        adapter.update_process_state("salt_concentration", 300.0)
        load_high = adapter.equilibrium_loading(0.001)
        assert load_low > load_high


class TestADR006Sanity:
    def test_sigma_zero_high_dilution_collapses_to_simple_form(self):
        """At σ=0 and dilute C, SMA should give ~ K_eq · C · (Λ/C_salt)^z.

        This is the signature that ADR-006 calls out: σ=0 makes the
        SMA equivalent to the Mollerup-simplified expression — confirming
        the cost / precision tradeoff isn't doing anything when σ=0.
        """
        sma = SaltModulatedSMA(z=2.0, sigma=0.0, K_eq=1e-3, Lambda=1000.0)
        C = 1.0e-6  # very dilute
        c_salt = 100.0
        out = sma.equilibrium_loading(C, c_salt_mol_m3=c_salt)
        # Expected shape: K_eq · C · (Λ/c_salt)**z = 1e-3 · 1e-6 · 100 = 1e-7
        # (since Λ/c_salt=10 and z=2)
        expected = 1.0e-3 * 1.0e-6 * (1000.0 / c_salt) ** 2.0
        # Some bias from the fixed-point (q_salt < Λ even at low load)
        # but should be within ~10 % of the dilute closed-form.
        assert out == pytest.approx(expected, rel=0.1)
