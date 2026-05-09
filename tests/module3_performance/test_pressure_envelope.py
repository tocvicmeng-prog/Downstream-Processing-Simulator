"""B-2f / W-020 tests: compute_pressure_envelope orchestrator.

The keystone test suite of the v0.7.0 M3 back-pressure work. Verifies:

* End-to-end resolution: family lookup → μ resolution → u_crit →
  Q_max → ΔP_predicted → tier rollup.
* The u_crit-based operational ceiling differs structurally from the
  E_star-based bursting ceiling (the whole point of W-020).
* Tier rollup walks valid_domain + viscosity.extrapolated correctly.
* Manufacturer calibration_store override promotes K_geom_source.
* The headroom_ratio property and is_warning / is_blocker derivation.
* Provenance fields populate for the dossier export.
"""

from __future__ import annotations

import math

import pytest

from dpsim.core.mobile_phase import MobilePhase
from dpsim.datatypes import ModelEvidenceTier, PolymerFamily
from dpsim.module3_performance.hydrodynamics import ColumnGeometry
from dpsim.module3_performance.pressure_envelope import (
    PressureEnvelope,
    compute_pressure_envelope,
)


# ─── Fixtures ────────────────────────────────────────────────────────────────


def _agarose_column() -> ColumnGeometry:
    """Realistic agarose 4-6% column.

    G_DN ≈ 5 kPa is consistent with literature values for Sepharose 4FF /
    6FF; E_star ≈ 3·G_DN (incompressible-rubber Poisson ν ≈ 0.5).
    """
    return ColumnGeometry(
        diameter=0.01,
        bed_height=0.10,
        particle_diameter=90e-6,
        bed_porosity=0.38,
        particle_porosity=0.70,
        G_DN=5000.0,
        E_star=15000.0,
    )


# ─── Smoke / end-to-end ──────────────────────────────────────────────────────


class TestEndToEnd:
    """Smoke test: typical analytical Sepharose run produces a sane envelope."""

    def test_returns_pressure_envelope(self) -> None:
        col = _agarose_column()
        env = compute_pressure_envelope(
            polymer_family=PolymerFamily.AGAROSE,
            column=col,
            mobile_phase=MobilePhase(),
            Q_set_m3_s=1e-7,  # ~6 mL/min
        )
        assert isinstance(env, PressureEnvelope)

    def test_typical_run_yields_safe_headroom(self) -> None:
        # 200 cm/h on a Sepharose-class agarose column: well below u_crit.
        col = _agarose_column()
        Q_set = 200.0 / 100.0 / 3600.0 * col.cross_section_area
        env = compute_pressure_envelope(
            polymer_family=PolymerFamily.AGAROSE,
            column=col,
            mobile_phase=MobilePhase(),
            Q_set_m3_s=Q_set,
        )
        assert env.headroom_ratio < 0.5
        assert not env.is_warning
        assert not env.is_blocker

    def test_u_crit_in_published_sepharose_range(self) -> None:
        # Sci-advisor §B anchor for Sepharose 4-6%: published max linear
        # velocity 300–700 cm/h. Allow generous range for the v0.7
        # SEMI_QUANTITATIVE INTERVAL framing.
        col = _agarose_column()
        env = compute_pressure_envelope(
            polymer_family=PolymerFamily.AGAROSE,
            column=col,
            mobile_phase=MobilePhase(),
            Q_set_m3_s=1e-9,  # negligible — just sampling u_crit
        )
        u_crit_cm_per_h = env.u_crit_m_s * 100.0 * 3600.0
        # Wide envelope — interval-style check, not exact match.
        assert 200 < u_crit_cm_per_h < 1500


# ─── Operational vs structural ceilings ─────────────────────────────────────


class TestOperationalVsBurst:
    """The two pressure ceilings must be distinct fields and have the
    documented relationship (operational < structural cracking)."""

    def test_burst_field_equals_E_star(self) -> None:
        col = _agarose_column()
        env = compute_pressure_envelope(
            polymer_family=PolymerFamily.AGAROSE,
            column=col,
            mobile_phase=MobilePhase(),
            Q_set_m3_s=1e-7,
        )
        # dP_max_burst is the bed elastic-limit diagnostic (E_star);
        # the actual cracking threshold is higher (sci-advisor §B).
        assert env.dP_max_burst_pa == col.E_star

    def test_operational_and_burst_are_different_fields(self) -> None:
        col = _agarose_column()
        env = compute_pressure_envelope(
            polymer_family=PolymerFamily.AGAROSE,
            column=col,
            mobile_phase=MobilePhase(),
            Q_set_m3_s=1e-7,
        )
        # The whole point of W-020: the two ceilings are physically
        # distinct quantities, not the same number.
        assert env.dP_max_operational_pa != env.dP_max_burst_pa


# ─── u_crit formula ──────────────────────────────────────────────────────────


class TestUCritFormula:
    """u_crit = K_geom · G_DN · d² / (μ · L) — verify each scaling."""

    def test_u_crit_doubles_when_G_DN_doubles(self) -> None:
        col_low = _agarose_column()
        col_high = ColumnGeometry(
            **{**col_low.__dict__, "G_DN": col_low.G_DN * 2.0}
        )
        mp = MobilePhase()
        env_low = compute_pressure_envelope(
            polymer_family=PolymerFamily.AGAROSE,
            column=col_low, mobile_phase=mp, Q_set_m3_s=1e-9,
        )
        env_high = compute_pressure_envelope(
            polymer_family=PolymerFamily.AGAROSE,
            column=col_high, mobile_phase=mp, Q_set_m3_s=1e-9,
        )
        assert math.isclose(env_high.u_crit_m_s / env_low.u_crit_m_s, 2.0, rel_tol=1e-9)

    def test_u_crit_quadruples_when_d32_doubles(self) -> None:
        col_low = _agarose_column()
        col_high = ColumnGeometry(
            **{**col_low.__dict__, "particle_diameter": col_low.particle_diameter * 2.0}
        )
        mp = MobilePhase()
        env_low = compute_pressure_envelope(
            polymer_family=PolymerFamily.AGAROSE,
            column=col_low, mobile_phase=mp, Q_set_m3_s=1e-9,
        )
        env_high = compute_pressure_envelope(
            polymer_family=PolymerFamily.AGAROSE,
            column=col_high, mobile_phase=mp, Q_set_m3_s=1e-9,
        )
        # u_crit ∝ d² → 2² = 4×
        assert math.isclose(env_high.u_crit_m_s / env_low.u_crit_m_s, 4.0, rel_tol=1e-9)

    def test_u_crit_halves_when_L_doubles(self) -> None:
        col_low = _agarose_column()
        col_high = ColumnGeometry(
            **{**col_low.__dict__, "bed_height": col_low.bed_height * 2.0}
        )
        mp = MobilePhase()
        env_low = compute_pressure_envelope(
            polymer_family=PolymerFamily.AGAROSE,
            column=col_low, mobile_phase=mp, Q_set_m3_s=1e-9,
        )
        env_high = compute_pressure_envelope(
            polymer_family=PolymerFamily.AGAROSE,
            column=col_high, mobile_phase=mp, Q_set_m3_s=1e-9,
        )
        # u_crit ∝ 1/L → halves
        assert math.isclose(env_high.u_crit_m_s / env_low.u_crit_m_s, 0.5, rel_tol=1e-9)

    def test_u_crit_halves_when_mu_doubles(self) -> None:
        col = _agarose_column()
        mp_low = MobilePhase(custom_mu_pa_s=1e-3)
        mp_high = MobilePhase(custom_mu_pa_s=2e-3)
        env_low = compute_pressure_envelope(
            polymer_family=PolymerFamily.AGAROSE,
            column=col, mobile_phase=mp_low, Q_set_m3_s=1e-9,
        )
        env_high = compute_pressure_envelope(
            polymer_family=PolymerFamily.AGAROSE,
            column=col, mobile_phase=mp_high, Q_set_m3_s=1e-9,
        )
        # u_crit ∝ 1/μ → halves
        assert math.isclose(env_high.u_crit_m_s / env_low.u_crit_m_s, 0.5, rel_tol=1e-9)


# ─── Q_max + Q_recommended ───────────────────────────────────────────────────


class TestQMax:
    """Q_max = u_crit · A; Q_recommended = 0.5 · Q_max."""

    def test_Q_max_equals_u_crit_times_area(self) -> None:
        col = _agarose_column()
        env = compute_pressure_envelope(
            polymer_family=PolymerFamily.AGAROSE,
            column=col, mobile_phase=MobilePhase(), Q_set_m3_s=1e-9,
        )
        assert math.isclose(
            env.Q_max_m3_s, env.u_crit_m_s * col.cross_section_area, rel_tol=1e-9
        )

    def test_Q_recommended_is_half_Q_max(self) -> None:
        col = _agarose_column()
        env = compute_pressure_envelope(
            polymer_family=PolymerFamily.AGAROSE,
            column=col, mobile_phase=MobilePhase(), Q_set_m3_s=1e-9,
        )
        assert math.isclose(env.Q_recommended_m3_s, 0.5 * env.Q_max_m3_s)


# ─── Headroom + warning/blocker ──────────────────────────────────────────────


class TestHeadroomAndAlarms:
    """headroom_ratio property + is_warning / is_blocker derivation."""

    def test_zero_flow_zero_headroom(self) -> None:
        col = _agarose_column()
        env = compute_pressure_envelope(
            polymer_family=PolymerFamily.AGAROSE,
            column=col, mobile_phase=MobilePhase(), Q_set_m3_s=0.0,
        )
        assert env.headroom_ratio == 0.0
        assert not env.is_warning
        assert not env.is_blocker

    def test_at_Q_max_headroom_one_blocker_borderline(self) -> None:
        col = _agarose_column()
        env_probe = compute_pressure_envelope(
            polymer_family=PolymerFamily.AGAROSE,
            column=col, mobile_phase=MobilePhase(), Q_set_m3_s=1e-9,
        )
        env_at_limit = compute_pressure_envelope(
            polymer_family=PolymerFamily.AGAROSE,
            column=col, mobile_phase=MobilePhase(),
            Q_set_m3_s=env_probe.Q_max_m3_s,
        )
        assert math.isclose(env_at_limit.headroom_ratio, 1.0, rel_tol=1e-9)
        assert env_at_limit.is_warning
        assert not env_at_limit.is_blocker

    def test_above_Q_max_is_blocker(self) -> None:
        col = _agarose_column()
        env_probe = compute_pressure_envelope(
            polymer_family=PolymerFamily.AGAROSE,
            column=col, mobile_phase=MobilePhase(), Q_set_m3_s=1e-9,
        )
        env_over = compute_pressure_envelope(
            polymer_family=PolymerFamily.AGAROSE,
            column=col, mobile_phase=MobilePhase(),
            Q_set_m3_s=env_probe.Q_max_m3_s * 1.5,
        )
        assert env_over.headroom_ratio > 1.0
        assert env_over.is_blocker

    def test_warning_band_is_70_to_100_pct(self) -> None:
        col = _agarose_column()
        env_probe = compute_pressure_envelope(
            polymer_family=PolymerFamily.AGAROSE,
            column=col, mobile_phase=MobilePhase(), Q_set_m3_s=1e-9,
        )
        env_warn = compute_pressure_envelope(
            polymer_family=PolymerFamily.AGAROSE,
            column=col, mobile_phase=MobilePhase(),
            Q_set_m3_s=env_probe.Q_max_m3_s * 0.85,
        )
        assert env_warn.is_warning
        assert not env_warn.is_blocker

    def test_below_70_pct_is_safe(self) -> None:
        col = _agarose_column()
        env_probe = compute_pressure_envelope(
            polymer_family=PolymerFamily.AGAROSE,
            column=col, mobile_phase=MobilePhase(), Q_set_m3_s=1e-9,
        )
        env_safe = compute_pressure_envelope(
            polymer_family=PolymerFamily.AGAROSE,
            column=col, mobile_phase=MobilePhase(),
            Q_set_m3_s=env_probe.Q_max_m3_s * 0.50,
        )
        assert not env_safe.is_warning
        assert not env_safe.is_blocker


# ─── Tier rollup ─────────────────────────────────────────────────────────────


class TestTierRollup:
    """decision_tier walks valid_domain + viscosity.extrapolated."""

    def test_in_domain_carries_base_tier(self) -> None:
        col = _agarose_column()
        env = compute_pressure_envelope(
            polymer_family=PolymerFamily.AGAROSE,
            column=col, mobile_phase=MobilePhase(), Q_set_m3_s=1e-9,
        )
        # Base tier from family default (SEMI_QUANTITATIVE) — no
        # demotion since defaults are in-domain and μ is in-window.
        assert env.decision_tier == ModelEvidenceTier.SEMI_QUANTITATIVE
        assert env.valid_domain_violations == ()

    def test_out_of_domain_demotes_one_step(self) -> None:
        # Tiny bead → outside agarose's bead_d32_m lower bound (40 µm).
        col = ColumnGeometry(
            **{**_agarose_column().__dict__, "particle_diameter": 20e-6}
        )
        env = compute_pressure_envelope(
            polymer_family=PolymerFamily.AGAROSE,
            column=col, mobile_phase=MobilePhase(), Q_set_m3_s=1e-9,
        )
        assert len(env.valid_domain_violations) >= 1
        assert env.decision_tier == ModelEvidenceTier.QUALITATIVE_TREND

    def test_extrapolated_viscosity_demotes_one_step(self) -> None:
        # 50% glycerol forces viscosity.extrapolated=True.
        col = _agarose_column()
        mp = MobilePhase(c_nacl_M=0.0, phi_glycerol=0.50)
        env = compute_pressure_envelope(
            polymer_family=PolymerFamily.AGAROSE,
            column=col, mobile_phase=mp, Q_set_m3_s=1e-9,
        )
        assert env.viscosity.extrapolated
        # SEMI_QUANTITATIVE → QUALITATIVE_TREND (one step)
        assert env.decision_tier == ModelEvidenceTier.QUALITATIVE_TREND

    def test_tier_floors_at_qualitative_trend(self) -> None:
        # Both demotions stack but the floor holds.
        col = ColumnGeometry(
            **{**_agarose_column().__dict__, "particle_diameter": 20e-6}
        )
        mp = MobilePhase(c_nacl_M=0.0, phi_glycerol=0.50)
        env = compute_pressure_envelope(
            polymer_family=PolymerFamily.AGAROSE,
            column=col, mobile_phase=mp, Q_set_m3_s=1e-9,
        )
        assert env.decision_tier == ModelEvidenceTier.QUALITATIVE_TREND


# ─── Calibration store override ──────────────────────────────────────────────


class TestCalibrationStore:
    """User-supplied calibration_store overrides the family default K_geom."""

    def test_calibration_override_applies(self) -> None:
        col = _agarose_column()
        cal = {"agarose": {"K_geom": 1e-3, "source": "manufacturer_GE"}}
        env = compute_pressure_envelope(
            polymer_family=PolymerFamily.AGAROSE,
            column=col, mobile_phase=MobilePhase(),
            Q_set_m3_s=1e-9, calibration_store=cal,
        )
        assert env.K_geom_used == 1e-3
        assert env.K_geom_source == "manufacturer_GE"

    def test_calibration_promotes_tier_to_calibrated_local(self) -> None:
        col = _agarose_column()
        cal = {"agarose": {"K_geom": 1e-3, "source": "manufacturer_GE"}}
        env = compute_pressure_envelope(
            polymer_family=PolymerFamily.AGAROSE,
            column=col, mobile_phase=MobilePhase(),
            Q_set_m3_s=1e-9, calibration_store=cal,
        )
        assert env.decision_tier == ModelEvidenceTier.CALIBRATED_LOCAL

    def test_no_calibration_uses_family_default(self) -> None:
        col = _agarose_column()
        env = compute_pressure_envelope(
            polymer_family=PolymerFamily.AGAROSE,
            column=col, mobile_phase=MobilePhase(), Q_set_m3_s=1e-9,
        )
        assert env.K_geom_source == "family_default"


# ─── Frit contribution ───────────────────────────────────────────────────────


class TestFritContribution:
    """When the column has frit fields, ΔP_predicted includes ΔP_frit."""

    def test_with_frit_dP_predicted_increases(self) -> None:
        col_no_frit = _agarose_column()
        col_with_frit = ColumnGeometry(
            **{
                **_agarose_column().__dict__,
                "frit_permeability_m2": 1e-13,
                "frit_thickness_m": 1e-3,
            }
        )
        Q = 1e-7
        env_no = compute_pressure_envelope(
            polymer_family=PolymerFamily.AGAROSE,
            column=col_no_frit, mobile_phase=MobilePhase(), Q_set_m3_s=Q,
        )
        env_with = compute_pressure_envelope(
            polymer_family=PolymerFamily.AGAROSE,
            column=col_with_frit, mobile_phase=MobilePhase(), Q_set_m3_s=Q,
        )
        assert env_with.dP_predicted_pa > env_no.dP_predicted_pa
        assert env_no.dP_frit_pa == 0.0
        assert env_with.dP_frit_pa > 0.0


# ─── Provenance ──────────────────────────────────────────────────────────────


class TestProvenance:
    """Provenance fields populate for the dossier export."""

    def test_K_geom_provenance_recorded(self) -> None:
        col = _agarose_column()
        env = compute_pressure_envelope(
            polymer_family=PolymerFamily.AGAROSE,
            column=col, mobile_phase=MobilePhase(), Q_set_m3_s=1e-9,
        )
        assert env.calibration_provenance["K_geom"] == "family_default"
        assert env.calibration_provenance["K_geom_anchor"] == "Stickel2001"

    def test_viscosity_method_recorded(self) -> None:
        col = _agarose_column()
        env = compute_pressure_envelope(
            polymer_family=PolymerFamily.AGAROSE,
            column=col, mobile_phase=MobilePhase(), Q_set_m3_s=1e-9,
        )
        assert env.calibration_provenance["viscosity_method"] == "additive_model"

    def test_extrapolated_flag_in_provenance(self) -> None:
        col = _agarose_column()
        mp = MobilePhase(c_nacl_M=0.0, phi_glycerol=0.50)
        env = compute_pressure_envelope(
            polymer_family=PolymerFamily.AGAROSE,
            column=col, mobile_phase=mp, Q_set_m3_s=1e-9,
        )
        assert env.calibration_provenance.get("viscosity_flag") == "extrapolated"

    def test_inputs_echoed(self) -> None:
        col = _agarose_column()
        mp = MobilePhase(name="hic_load", c_nacl_M=2.0)
        env = compute_pressure_envelope(
            polymer_family=PolymerFamily.AGAROSE,
            column=col, mobile_phase=mp, Q_set_m3_s=1e-7,
        )
        assert env.polymer_family.value == "agarose"
        assert env.mobile_phase.name == "hic_load"
        assert env.Q_set_m3_s == 1e-7

    def test_notes_explain_default_anchor(self) -> None:
        col = _agarose_column()
        env = compute_pressure_envelope(
            polymer_family=PolymerFamily.AGAROSE,
            column=col, mobile_phase=MobilePhase(), Q_set_m3_s=1e-9,
        )
        # The "supply manufacturer pressure-flow curve" advisory note.
        assert any("manufacturer" in n for n in env.notes)


# ─── Pathological inputs ─────────────────────────────────────────────────────


class TestPathologicalInputs:
    """Negative / zero inputs raise ValueError."""

    def test_negative_Q_set_raises(self) -> None:
        col = _agarose_column()
        with pytest.raises(ValueError, match="Q_set_m3_s"):
            compute_pressure_envelope(
                polymer_family=PolymerFamily.AGAROSE,
                column=col, mobile_phase=MobilePhase(), Q_set_m3_s=-1e-7,
            )

    def test_zero_d32_raises(self) -> None:
        col = ColumnGeometry(**{**_agarose_column().__dict__, "particle_diameter": 0.0})
        with pytest.raises(ValueError, match="bead_d32_m"):
            compute_pressure_envelope(
                polymer_family=PolymerFamily.AGAROSE,
                column=col, mobile_phase=MobilePhase(), Q_set_m3_s=1e-9,
            )

    def test_zero_G_DN_raises(self) -> None:
        col = ColumnGeometry(**{**_agarose_column().__dict__, "G_DN": 0.0})
        with pytest.raises(ValueError, match="G_DN_pa"):
            compute_pressure_envelope(
                polymer_family=PolymerFamily.AGAROSE,
                column=col, mobile_phase=MobilePhase(), Q_set_m3_s=1e-9,
            )


# ─── Frozen contract ─────────────────────────────────────────────────────────


class TestFrozen:
    """PressureEnvelope is a frozen dataclass."""

    def test_cannot_mutate(self) -> None:
        from dataclasses import FrozenInstanceError

        col = _agarose_column()
        env = compute_pressure_envelope(
            polymer_family=PolymerFamily.AGAROSE,
            column=col, mobile_phase=MobilePhase(), Q_set_m3_s=1e-9,
        )
        with pytest.raises(FrozenInstanceError):
            env.Q_max_m3_s = 0.0  # type: ignore[misc]
