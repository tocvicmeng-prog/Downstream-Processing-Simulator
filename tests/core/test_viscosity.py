"""B-1f / W-023 tests: BufferViscosityModel resolution behaviour.

Covers:

* Pure-water table from Crittenden 2012 / CRC handbook (5 anchor points).
* NaCl additive contribution from Out & Los 1980 (1 M anchor).
* Glycerol-water from Cheng 2008 (linear regime φ ≤ 0.30).
* Ethanol-water from Khattab 2017 (linear regime φ ≤ 0.30).
* ``custom_mu_pa_s`` override path (tier promotion to CALIBRATED_LOCAL).
* Extrapolation flag and the three ``extrapolation_policy`` modes.
* Tier rollup (additive → SEMI_QUANTITATIVE; override → CALIBRATED_LOCAL).
* Out-of-range / negative / pathological inputs.

The literature anchor values used in the assertions below are recomputed
from the additive model with the coefficients pinned in
:mod:`dpsim.core.viscosity` (α_salt=0.10/M, α_gly=3.5, α_etoh=5.9). When
the coefficients are recalibrated the assertions update in lockstep —
the assertion tolerance ranges are deliberately wide to express the
SEMI_QUANTITATIVE tier intent.
"""

from __future__ import annotations

import math

import pytest

from dpsim.core.mobile_phase import MobilePhase
from dpsim.core.viscosity import (
    resolve_mobile_phase_viscosity,
    water_viscosity_pa_s,
)
from dpsim.datatypes import ModelEvidenceTier


# ─── Pure-water table tests ──────────────────────────────────────────────────


class TestWaterViscosityTable:
    """μ_water(T) must reproduce the CRC handbook anchor values."""

    @pytest.mark.parametrize(
        "T_C, expected_mu",
        [
            (0.0, 1.792e-3),
            (5.0, 1.519e-3),
            (10.0, 1.307e-3),
            (15.0, 1.139e-3),
            (20.0, 1.002e-3),
            (25.0, 0.890e-3),
            (30.0, 0.798e-3),
            (40.0, 0.653e-3),
            (50.0, 0.547e-3),
            (60.0, 0.466e-3),
            (70.0, 0.404e-3),
            (80.0, 0.355e-3),
        ],
    )
    def test_anchor_points(self, T_C: float, expected_mu: float) -> None:
        assert math.isclose(
            water_viscosity_pa_s(T_C), expected_mu, rel_tol=1e-9
        )

    def test_interpolation_between_anchors_22p5C(self) -> None:
        # Between 20 and 25 °C; expect linear-interp midpoint.
        # 0.5 · (1.002e-3 + 0.890e-3) = 0.946e-3
        mu = water_viscosity_pa_s(22.5)
        assert math.isclose(mu, 0.946e-3, rel_tol=1e-9)

    def test_interpolation_between_anchors_3p7C(self) -> None:
        # Between 0 and 5 °C, 74 % toward the 5 °C anchor.
        # μ = 1.792e-3 + 0.74·(1.519e-3 − 1.792e-3) = 1.59e-3
        mu = water_viscosity_pa_s(3.7)
        assert math.isclose(mu, 1.792e-3 + 0.74 * (1.519e-3 - 1.792e-3))

    def test_below_range_raises(self) -> None:
        with pytest.raises(ValueError, match="below water-viscosity"):
            water_viscosity_pa_s(-5.0)

    def test_above_range_raises(self) -> None:
        with pytest.raises(ValueError, match="above water-viscosity"):
            water_viscosity_pa_s(95.0)


# ─── Additive-model: NaCl contribution ───────────────────────────────────────


class TestSaltAdditive:
    """μ/μ_water vs c_NaCl must hit the Out & Los 1980 1 M anchor."""

    def test_zero_salt_at_25C_equals_water(self) -> None:
        mp = MobilePhase(T_C=25.0, c_nacl_M=0.0)
        result = resolve_mobile_phase_viscosity(mp)
        assert math.isclose(result.mu_pa_s, 0.890e-3, rel_tol=1e-9)

    def test_one_molar_nacl_gives_10pct_increase(self) -> None:
        # α_salt=0.10/M pinned → 1 M NaCl ⇒ μ/μ_water = 1.10
        mp = MobilePhase(T_C=25.0, c_nacl_M=1.0)
        result = resolve_mobile_phase_viscosity(mp)
        ratio = result.mu_pa_s / 0.890e-3
        assert math.isclose(ratio, 1.10, rel_tol=1e-9)

    def test_two_molar_nacl_at_25C_doubles_correction(self) -> None:
        # 2 M NaCl ⇒ μ/μ_water = 1.20 (linear-regime extrapolation;
        # acknowledged as approximate at 2 M but in calibration window
        # since no co-solvent triggers the T-window check).
        mp = MobilePhase(T_C=25.0, c_nacl_M=2.0)
        result = resolve_mobile_phase_viscosity(mp)
        ratio = result.mu_pa_s / 0.890e-3
        assert math.isclose(ratio, 1.20, rel_tol=1e-9)


# ─── Additive-model: glycerol contribution ───────────────────────────────────


class TestGlycerolAdditive:
    """μ/μ_water vs φ_glycerol must hit the Cheng 2008 linear-regime anchor."""

    def test_20pct_glycerol_at_25C(self) -> None:
        # α_gly=3.5 pinned → φ=0.20 ⇒ μ/μ_water = 1 + 0.70 = 1.70
        # c_nacl_M=0.0 to isolate the glycerol contribution.
        mp = MobilePhase(T_C=25.0, c_nacl_M=0.0, phi_glycerol=0.20)
        result = resolve_mobile_phase_viscosity(mp)
        ratio = result.mu_pa_s / 0.890e-3
        assert math.isclose(ratio, 1.70, rel_tol=1e-9)
        assert not result.extrapolated

    def test_30pct_glycerol_at_calibration_edge(self) -> None:
        # φ=0.30 is exactly at the linear-regime limit; extrapolated=False.
        mp = MobilePhase(T_C=25.0, phi_glycerol=0.30)
        result = resolve_mobile_phase_viscosity(mp)
        assert not result.extrapolated

    def test_40pct_glycerol_flagged_extrapolated(self) -> None:
        # φ=0.40 above linear-regime limit; flag must trip.
        mp = MobilePhase(T_C=25.0, phi_glycerol=0.40)
        result = resolve_mobile_phase_viscosity(mp)
        assert result.extrapolated
        assert "phi_glycerol" in result.notes


# ─── Additive-model: ethanol contribution ────────────────────────────────────


class TestEthanolAdditive:
    """μ/μ_water vs φ_ethanol must hit the Khattab 2017 linear-regime anchor."""

    def test_20pct_ethanol_at_25C(self) -> None:
        # α_etoh=5.9 pinned → φ=0.20 ⇒ μ/μ_water = 1 + 1.18 = 2.18
        # c_nacl_M=0.0 to isolate the ethanol contribution.
        mp = MobilePhase(T_C=25.0, c_nacl_M=0.0, phi_ethanol=0.20)
        result = resolve_mobile_phase_viscosity(mp)
        ratio = result.mu_pa_s / 0.890e-3
        assert math.isclose(ratio, 2.18, rel_tol=1e-9)
        assert not result.extrapolated

    def test_70pct_ethanol_cip_extrapolated(self) -> None:
        # CIP at 70 % ethanol — far above linear-regime limit.
        mp = MobilePhase(name="cip", T_C=25.0, phi_ethanol=0.70)
        result = resolve_mobile_phase_viscosity(mp)
        assert result.extrapolated
        assert "phi_ethanol" in result.notes


# ─── Combined buffer compositions ────────────────────────────────────────────


class TestCombinedComposition:
    """All three additive contributions stack linearly."""

    def test_glycerol_plus_salt(self) -> None:
        # 0.5 M NaCl + 10 % glycerol at 25 °C
        # μ/μ_water = 1 + 0.10·0.5 + 3.5·0.10 = 1.40
        mp = MobilePhase(T_C=25.0, c_nacl_M=0.5, phi_glycerol=0.10)
        result = resolve_mobile_phase_viscosity(mp)
        ratio = result.mu_pa_s / 0.890e-3
        assert math.isclose(ratio, 1.40, rel_tol=1e-9)

    def test_storage_buffer_20pct_ethanol(self) -> None:
        # 150 mM NaCl + 20 % ethanol at 20 °C — typical column storage buffer
        # μ/μ_water(20°C) = 1 + 0.10·0.15 + 5.9·0.20 = 2.195
        # μ_water(20°C) = 1.002e-3
        mp = MobilePhase(name="storage", phi_ethanol=0.20)
        result = resolve_mobile_phase_viscosity(mp)
        expected = 1.002e-3 * (1.0 + 0.10 * 0.15 + 5.9 * 0.20)
        assert math.isclose(result.mu_pa_s, expected, rel_tol=1e-9)


# ─── Cold-room temperature effect ────────────────────────────────────────────


class TestColdRoomEffect:
    """5 °C run vs 20 °C run silently changes μ — the dominant lever."""

    def test_5C_water_vs_20C_water_50pct_higher(self) -> None:
        # 1.519e-3 / 1.002e-3 = 1.516 → ~52 % higher μ at 5 °C
        mu_5 = water_viscosity_pa_s(5.0)
        mu_20 = water_viscosity_pa_s(20.0)
        assert mu_5 / mu_20 > 1.50
        assert mu_5 / mu_20 < 1.55

    def test_cold_equilibration_default_buffer(self) -> None:
        # Default 150 mM NaCl at 5 °C — no co-solvent, so T-window check
        # does NOT trip. extrapolated=False.
        mp = MobilePhase(T_C=5.0)
        result = resolve_mobile_phase_viscosity(mp)
        assert not result.extrapolated
        # μ ≈ 1.519e-3 · 1.015 = 1.542e-3
        assert math.isclose(
            result.mu_pa_s, 1.519e-3 * (1.0 + 0.10 * 0.150), rel_tol=1e-9
        )

    def test_cold_glycerol_buffer_flags_extrapolated(self) -> None:
        # 5 °C + 10 % glycerol — has co-solvent, T-window check trips.
        mp = MobilePhase(T_C=5.0, phi_glycerol=0.10)
        result = resolve_mobile_phase_viscosity(mp)
        assert result.extrapolated
        assert "T − 25" in result.notes


# ─── Custom override path (CALIBRATED_LOCAL) ─────────────────────────────────


class TestCustomOverride:
    """custom_mu_pa_s bypasses the additive model entirely."""

    def test_override_returns_user_value(self) -> None:
        mp = MobilePhase(custom_mu_pa_s=4.2e-3)
        result = resolve_mobile_phase_viscosity(mp)
        assert result.mu_pa_s == 4.2e-3

    def test_override_carries_calibrated_local_tier(self) -> None:
        mp = MobilePhase(custom_mu_pa_s=4.2e-3)
        result = resolve_mobile_phase_viscosity(mp)
        assert result.tier == ModelEvidenceTier.CALIBRATED_LOCAL

    def test_override_method_marker(self) -> None:
        mp = MobilePhase(custom_mu_pa_s=4.2e-3)
        result = resolve_mobile_phase_viscosity(mp)
        assert result.method == "custom_override"

    def test_override_extrapolated_always_false(self) -> None:
        # Even with otherwise out-of-window inputs, override → not extrapolated.
        mp = MobilePhase(
            T_C=70.0, phi_glycerol=0.50, phi_ethanol=0.40, custom_mu_pa_s=8e-3
        )
        result = resolve_mobile_phase_viscosity(mp)
        assert not result.extrapolated

    def test_override_zero_raises(self) -> None:
        mp = MobilePhase(custom_mu_pa_s=0.0)
        with pytest.raises(ValueError, match="must be positive"):
            resolve_mobile_phase_viscosity(mp)

    def test_override_negative_raises(self) -> None:
        mp = MobilePhase(custom_mu_pa_s=-1e-3)
        with pytest.raises(ValueError, match="must be positive"):
            resolve_mobile_phase_viscosity(mp)


# ─── Extrapolation policy modes ──────────────────────────────────────────────


class TestExtrapolationPolicy:
    """The three policy modes (warn / raise / silent) behave correctly."""

    def test_warn_default_returns_with_notes(self) -> None:
        mp = MobilePhase(T_C=25.0, phi_glycerol=0.50)
        result = resolve_mobile_phase_viscosity(mp)
        assert result.extrapolated
        assert result.notes != ""

    def test_silent_returns_with_no_notes(self) -> None:
        mp = MobilePhase(T_C=25.0, phi_glycerol=0.50)
        result = resolve_mobile_phase_viscosity(
            mp, extrapolation_policy="silent"
        )
        assert result.extrapolated
        assert result.notes == ""

    def test_raise_blocks_out_of_window(self) -> None:
        mp = MobilePhase(T_C=25.0, phi_glycerol=0.50)
        with pytest.raises(ValueError, match="outside additive-model"):
            resolve_mobile_phase_viscosity(mp, extrapolation_policy="raise")

    def test_invalid_policy_raises(self) -> None:
        mp = MobilePhase()
        with pytest.raises(ValueError, match="extrapolation_policy"):
            resolve_mobile_phase_viscosity(
                mp, extrapolation_policy="invalid_mode"
            )

    def test_raise_does_not_block_in_window(self) -> None:
        mp = MobilePhase()  # default — fully in window
        result = resolve_mobile_phase_viscosity(
            mp, extrapolation_policy="raise"
        )
        assert not result.extrapolated


# ─── Tier rollup ─────────────────────────────────────────────────────────────


class TestTierRollup:
    """Tier assignment must reflect the resolution path."""

    def test_additive_model_in_window_is_semi_quantitative(self) -> None:
        mp = MobilePhase()
        result = resolve_mobile_phase_viscosity(mp)
        assert result.tier == ModelEvidenceTier.SEMI_QUANTITATIVE

    def test_additive_model_extrapolated_still_semi_quantitative(self) -> None:
        # The result-level tier doesn't auto-demote here; the
        # downstream PressureEnvelope.decision_tier rollup (B-2f) is
        # what reads the extrapolated flag and demotes one step.
        mp = MobilePhase(phi_ethanol=0.50)
        result = resolve_mobile_phase_viscosity(mp)
        assert result.tier == ModelEvidenceTier.SEMI_QUANTITATIVE
        assert result.extrapolated

    def test_override_promotes_to_calibrated_local(self) -> None:
        mp = MobilePhase(custom_mu_pa_s=2e-3)
        result = resolve_mobile_phase_viscosity(mp)
        assert result.tier == ModelEvidenceTier.CALIBRATED_LOCAL


# ─── Pathological inputs ─────────────────────────────────────────────────────


class TestPathologicalInputs:
    """Negative / out-of-range physical inputs must be rejected."""

    def test_negative_salt_raises(self) -> None:
        mp = MobilePhase(c_nacl_M=-0.1)
        with pytest.raises(ValueError, match="c_nacl_M"):
            resolve_mobile_phase_viscosity(mp)

    def test_negative_glycerol_raises(self) -> None:
        mp = MobilePhase(phi_glycerol=-0.1)
        with pytest.raises(ValueError, match="phi_glycerol"):
            resolve_mobile_phase_viscosity(mp)

    def test_negative_ethanol_raises(self) -> None:
        mp = MobilePhase(phi_ethanol=-0.1)
        with pytest.raises(ValueError, match="phi_ethanol"):
            resolve_mobile_phase_viscosity(mp)

    def test_glycerol_above_unity_raises(self) -> None:
        mp = MobilePhase(phi_glycerol=1.5)
        with pytest.raises(ValueError, match="phi_glycerol"):
            resolve_mobile_phase_viscosity(mp)

    def test_ethanol_above_unity_raises(self) -> None:
        mp = MobilePhase(phi_ethanol=1.5)
        with pytest.raises(ValueError, match="phi_ethanol"):
            resolve_mobile_phase_viscosity(mp)

    def test_T_below_water_table_raises_via_water_call(self) -> None:
        # The water-table bounds check fires before the additive correction.
        mp = MobilePhase(T_C=-10.0)
        with pytest.raises(ValueError, match="below water-viscosity"):
            resolve_mobile_phase_viscosity(mp)

    def test_T_above_water_table_raises_via_water_call(self) -> None:
        mp = MobilePhase(T_C=95.0)
        with pytest.raises(ValueError, match="above water-viscosity"):
            resolve_mobile_phase_viscosity(mp)


# ─── Provenance fields ───────────────────────────────────────────────────────


class TestProvenanceFields:
    """ViscosityResult fields must echo the inputs for traceability."""

    def test_T_C_echoed(self) -> None:
        mp = MobilePhase(T_C=4.0)
        result = resolve_mobile_phase_viscosity(mp)
        assert result.T_C == 4.0

    def test_T_C_echoed_for_override(self) -> None:
        mp = MobilePhase(T_C=4.0, custom_mu_pa_s=2e-3)
        result = resolve_mobile_phase_viscosity(mp)
        assert result.T_C == 4.0

    def test_method_marker_for_additive(self) -> None:
        result = resolve_mobile_phase_viscosity(MobilePhase())
        assert result.method == "additive_model"

    def test_result_is_frozen(self) -> None:
        from dataclasses import FrozenInstanceError

        result = resolve_mobile_phase_viscosity(MobilePhase())
        with pytest.raises(FrozenInstanceError):
            result.mu_pa_s = 0.0  # type: ignore[misc]

    def test_buffer_name_in_override_notes(self) -> None:
        mp = MobilePhase(name="custom_arg_refold", custom_mu_pa_s=3e-3)
        result = resolve_mobile_phase_viscosity(mp)
        assert "custom_arg_refold" in result.notes
