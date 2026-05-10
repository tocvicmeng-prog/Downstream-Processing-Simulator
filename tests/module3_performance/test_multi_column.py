"""Tests for series multi-column envelope (B-3h / W-045, v0.8.2)."""

from __future__ import annotations

import pytest

from dpsim.core.mobile_phase import MobilePhase
from dpsim.datatypes import ModelEvidenceTier, PolymerFamily
from dpsim.module3_performance.hydrodynamics import ColumnGeometry
from dpsim.module3_performance.multi_column import (
    MultiColumnGeometry,
    MultiColumnPressureEnvelope,
    compute_multi_column_envelope,
)
from dpsim.module3_performance.pressure_envelope import (
    compute_pressure_envelope,
)


@pytest.fixture
def two_columns():
    """Two columns: one short and gentle, one taller and stiffer."""
    capture = ColumnGeometry(
        diameter=0.01, bed_height=0.05,
        particle_diameter=100e-6, bed_porosity=0.38,
        G_DN=10000.0, E_star=30000.0,
    )
    polish = ColumnGeometry(
        diameter=0.01, bed_height=0.10,
        particle_diameter=80e-6, bed_porosity=0.38,
        G_DN=15000.0, E_star=40000.0,
    )
    return MultiColumnGeometry(
        columns=(capture, polish),
        polymer_families=(PolymerFamily.AGAROSE, PolymerFamily.AGAROSE),
        name="capture+polish",
    )


# ─── MultiColumnGeometry validation ────────────────────────────────────────


class TestGeometryValidation:
    def test_mismatched_lengths_rejected(self):
        with pytest.raises(ValueError, match="polymer_families"):
            MultiColumnGeometry(
                columns=(ColumnGeometry(),),
                polymer_families=(PolymerFamily.AGAROSE, PolymerFamily.AGAROSE),
            )

    def test_empty_geometry_rejected(self):
        with pytest.raises(ValueError, match="at least one"):
            MultiColumnGeometry(columns=(), polymer_families=())

    def test_n_columns_property(self, two_columns):
        assert two_columns.n_columns == 2


# ─── Aggregation rules ────────────────────────────────────────────────────


class TestAggregation:
    def test_total_dp_sums_per_column(self, two_columns):
        Q_set = 1.0e-9  # very gentle so no envelope hits a runaway
        env = compute_multi_column_envelope(
            geometry=two_columns,
            mobile_phase=MobilePhase(),
            Q_set_m3_s=Q_set,
        )
        expected_sum = sum(e.dP_predicted_pa for e in env.per_column)
        assert env.total_dP_predicted_pa == pytest.approx(
            expected_sum, rel=1e-12,
        )

    def test_series_q_max_is_min_across_columns(self, two_columns):
        env = compute_multi_column_envelope(
            geometry=two_columns,
            mobile_phase=MobilePhase(),
            Q_set_m3_s=1.0e-9,
        )
        per_q_max = [e.Q_max_m3_s for e in env.per_column]
        assert env.series_Q_max_m3_s == pytest.approx(min(per_q_max), rel=1e-12)

    def test_series_q_recommended_is_half_q_max(self, two_columns):
        env = compute_multi_column_envelope(
            geometry=two_columns,
            mobile_phase=MobilePhase(),
            Q_set_m3_s=1.0e-9,
        )
        assert env.series_Q_recommended_m3_s == pytest.approx(
            0.5 * env.series_Q_max_m3_s, rel=1e-12,
        )

    def test_headroom_is_max_across_columns(self, two_columns):
        env = compute_multi_column_envelope(
            geometry=two_columns,
            mobile_phase=MobilePhase(),
            Q_set_m3_s=1.0e-9,
        )
        per_headroom = [e.headroom_ratio for e in env.per_column]
        assert env.series_headroom_ratio == pytest.approx(
            max(per_headroom), rel=1e-12,
        )

    def test_per_column_envelopes_match_independent_calls(self, two_columns):
        Q_set = 1.0e-9
        env = compute_multi_column_envelope(
            geometry=two_columns,
            mobile_phase=MobilePhase(),
            Q_set_m3_s=Q_set,
        )
        # Each per_column envelope must equal what we'd get calling
        # compute_pressure_envelope directly on that column.
        for col, fam, agg_env in zip(
            two_columns.columns, two_columns.polymer_families, env.per_column,
        ):
            direct = compute_pressure_envelope(
                polymer_family=fam,
                column=col,
                mobile_phase=MobilePhase(),
                Q_set_m3_s=Q_set,
            )
            assert agg_env.Q_max_m3_s == pytest.approx(
                direct.Q_max_m3_s, rel=1e-9,
            )


class TestBlockerVerdict:
    def test_q_above_min_q_max_triggers_blocker(self, two_columns):
        # First find the bottleneck Q_max.
        gentle = compute_multi_column_envelope(
            geometry=two_columns,
            mobile_phase=MobilePhase(),
            Q_set_m3_s=1.0e-9,
        )
        # Now run at 2× the bottleneck Q_max — should blocker.
        risky = compute_multi_column_envelope(
            geometry=two_columns,
            mobile_phase=MobilePhase(),
            Q_set_m3_s=gentle.series_Q_max_m3_s * 2.0,
        )
        assert risky.is_blocker
        assert risky.series_headroom_ratio > 1.0


# ─── Decision tier rollup ─────────────────────────────────────────────────


class TestTierRollup:
    def test_tier_is_weakest_across_columns(self, two_columns):
        # Both columns will land at the same tier (SEMI_QUANTITATIVE
        # default) so the rollup returns SEMI_QUANTITATIVE.
        env = compute_multi_column_envelope(
            geometry=two_columns,
            mobile_phase=MobilePhase(),
            Q_set_m3_s=1.0e-9,
        )
        assert env.decision_tier in (
            ModelEvidenceTier.SEMI_QUANTITATIVE,
            ModelEvidenceTier.QUALITATIVE_TREND,
        )


# ─── Valid-domain violation prefix ────────────────────────────────────────


class TestValidDomain:
    def test_violations_carry_column_prefix(self, two_columns):
        env = compute_multi_column_envelope(
            geometry=two_columns,
            mobile_phase=MobilePhase(),
            Q_set_m3_s=1.0e-9,
        )
        # Each violation entry should carry "col[i]:" prefix.
        for v in env.valid_domain_violations:
            assert v.startswith("col[")


# ─── Override sequences ──────────────────────────────────────────────────


class TestOverrides:
    def test_override_sequence_length_validation(self, two_columns):
        with pytest.raises(ValueError, match="override sequence length"):
            compute_multi_column_envelope(
                geometry=two_columns,
                mobile_phase=MobilePhase(),
                Q_set_m3_s=1.0e-9,
                G_DN_pa=(20000.0,),  # too short — should be length 2
            )

    def test_per_column_g_dn_override(self, two_columns):
        env_default = compute_multi_column_envelope(
            geometry=two_columns,
            mobile_phase=MobilePhase(),
            Q_set_m3_s=1.0e-9,
        )
        # Boost G_DN of column 0 only.
        env_boost = compute_multi_column_envelope(
            geometry=two_columns,
            mobile_phase=MobilePhase(),
            Q_set_m3_s=1.0e-9,
            G_DN_pa=(50000.0, None),
        )
        # Column 0's Q_max should rise (proportional to G_DN); column 1
        # unchanged.
        assert env_boost.per_column[0].Q_max_m3_s > env_default.per_column[0].Q_max_m3_s
        assert env_boost.per_column[1].Q_max_m3_s == pytest.approx(
            env_default.per_column[1].Q_max_m3_s, rel=1e-12,
        )


# ─── Result type ──────────────────────────────────────────────────────────


class TestResultType:
    def test_returns_correct_type(self, two_columns):
        env = compute_multi_column_envelope(
            geometry=two_columns,
            mobile_phase=MobilePhase(),
            Q_set_m3_s=1.0e-9,
        )
        assert isinstance(env, MultiColumnPressureEnvelope)
        assert env.n_columns == 2
        assert env.name == "capture+polish"
