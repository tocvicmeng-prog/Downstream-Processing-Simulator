"""B-1f / W-023 tests: MobilePhase value-type contract.

Covers default semantics, frozen behaviour, and the ``custom_mu_pa_s``
override field plumbing. The viscosity-resolution behaviour is tested
in :mod:`tests.core.test_viscosity`; this file only exercises the
``MobilePhase`` shape itself.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from dpsim.core.mobile_phase import MobilePhase


class TestMobilePhaseDefaults:
    """Default values must describe an "equilibration buffer at 20 °C"."""

    def test_default_name(self) -> None:
        assert MobilePhase().name == "equilibration"

    def test_default_temperature(self) -> None:
        assert MobilePhase().T_C == 20.0

    def test_default_nacl_concentration(self) -> None:
        assert MobilePhase().c_nacl_M == 0.150

    def test_default_co_solvents_zero(self) -> None:
        mp = MobilePhase()
        assert mp.phi_glycerol == 0.0
        assert mp.phi_ethanol == 0.0

    def test_default_pH_neutral(self) -> None:
        assert MobilePhase().pH == 7.4

    def test_default_no_custom_override(self) -> None:
        assert MobilePhase().custom_mu_pa_s is None


class TestMobilePhaseFrozen:
    """The dataclass must be immutable for safe value-object use."""

    def test_cannot_mutate_T_C(self) -> None:
        mp = MobilePhase()
        with pytest.raises(FrozenInstanceError):
            mp.T_C = 4.0  # type: ignore[misc]

    def test_cannot_mutate_custom_override(self) -> None:
        mp = MobilePhase()
        with pytest.raises(FrozenInstanceError):
            mp.custom_mu_pa_s = 2e-3  # type: ignore[misc]


class TestMobilePhaseCustomOverride:
    """The ``custom_mu_pa_s`` field carries through unchanged."""

    def test_custom_override_set(self) -> None:
        mp = MobilePhase(custom_mu_pa_s=2.5e-3)
        assert mp.custom_mu_pa_s == 2.5e-3

    def test_custom_override_preserved_with_other_fields(self) -> None:
        mp = MobilePhase(
            name="cip",
            T_C=4.0,
            phi_ethanol=0.70,
            custom_mu_pa_s=9e-3,
        )
        assert mp.name == "cip"
        assert mp.T_C == 4.0
        assert mp.phi_ethanol == 0.70
        assert mp.custom_mu_pa_s == 9e-3


class TestMobilePhaseSpecificRecipes:
    """Sanity-construct the canonical buffer types DPSim users will see."""

    def test_hic_load_buffer(self) -> None:
        # 2 M (NH₄)₂SO₄ approximated as 2 M NaCl for ionic-strength purposes.
        mp = MobilePhase(name="hic_load", c_nacl_M=2.0)
        assert mp.c_nacl_M == 2.0
        assert mp.phi_glycerol == 0.0

    def test_glycerol_stabilization_wash(self) -> None:
        mp = MobilePhase(name="wash", phi_glycerol=0.20)
        assert mp.phi_glycerol == 0.20

    def test_cold_room_equilibration(self) -> None:
        mp = MobilePhase(name="equilibration", T_C=4.0)
        assert mp.T_C == 4.0

    def test_imac_elute(self) -> None:
        # 500 mM imidazole approximated as 500 mM NaCl for ionic strength.
        mp = MobilePhase(name="elute", c_nacl_M=0.500, pH=4.0)
        assert mp.pH == 4.0
        assert mp.c_nacl_M == 0.500
