"""Tests for pressure_monitor_replay (B-2i / W-032).

Covers:

* CSV header alias resolution (canonical SI + a small set of common
  AKTA-style aliases).
* Numeric scaling (kPa → Pa, MPa → Pa, mL/min → m³/s, min → s).
* Skip rules: unparseable rows, negative ΔP rows.
* End-to-end replay returning a ReplaySummary with the correct
  blocker / warning anchors and state timeline.
"""

from __future__ import annotations

from io import StringIO

import pytest

from dpsim.core.mobile_phase import MobilePhase
from dpsim.datatypes import PolymerFamily
from dpsim.module3_performance.hydrodynamics import ColumnGeometry
from dpsim.module3_performance.pressure_envelope import (
    compute_pressure_envelope,
)
from dpsim.module3_performance.pressure_monitor import (
    PressureMonitorReading,
    PressureMonitorRule,
    PressureMonitorState,
)
from dpsim.module3_performance.pressure_monitor_replay import (
    parse_csv,
    replay,
)


# ─── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def default_envelope():
    """An envelope sized for a comfortable operating point (~6 % headroom).

    Uses AGAROSE with the default ColumnGeometry. Q_set = 0.1 × Q_recommended
    so the iterated ε_b stays in the linear-elastic regime; ΔP_predicted
    is then well below the operational ceiling and the live readings
    in the tests can simulate stable, marginal, or excessive operation
    by scaling against ``dP_max_operational_pa`` directly.
    """
    column = ColumnGeometry()
    mp = MobilePhase()
    pre = compute_pressure_envelope(
        polymer_family=PolymerFamily.AGAROSE,
        column=column,
        mobile_phase=mp,
        Q_set_m3_s=1e-9,  # placeholder
    )
    return compute_pressure_envelope(
        polymer_family=PolymerFamily.AGAROSE,
        column=column,
        mobile_phase=mp,
        Q_set_m3_s=pre.Q_recommended_m3_s * 0.1,
    )


# ─── parse_csv ──────────────────────────────────────────────────────────────


class TestParseCsvCanonical:
    def test_canonical_si_columns(self):
        text = (
            "t_s,dP_pa,Q_m3_s\n"
            "0.0,10000,1.0e-8\n"
            "1.0,11000,1.0e-8\n"
            "2.0,12000,1.0e-8\n"
        )
        readings = parse_csv(StringIO(text))
        assert len(readings) == 3
        assert readings[0].t_s == 0.0
        assert readings[0].dP_pa == 10000.0
        assert readings[2].dP_pa == 12000.0

    def test_returns_tuple(self):
        text = "t_s,dP_pa,Q_m3_s\n0.0,1000,1e-8\n"
        readings = parse_csv(StringIO(text))
        assert isinstance(readings, tuple)


class TestParseCsvAliases:
    def test_time_min_to_seconds(self):
        text = (
            "t_min,dP_pa,Q_m3_s\n"
            "0.0,1000,1e-8\n"
            "1.0,2000,1e-8\n"
        )
        readings = parse_csv(StringIO(text))
        assert readings[0].t_s == 0.0
        assert readings[1].t_s == 60.0  # 1 min → 60 s

    def test_dp_kpa_to_pa(self):
        text = "t_s,dP_kpa,Q_m3_s\n0.0,10.0,1e-8\n"
        readings = parse_csv(StringIO(text))
        assert readings[0].dP_pa == 10000.0

    def test_dp_mpa_to_pa(self):
        text = "t_s,dP_mpa,Q_m3_s\n0.0,0.5,1e-8\n"
        readings = parse_csv(StringIO(text))
        assert readings[0].dP_pa == pytest.approx(500000.0)

    def test_dp_bar_to_pa(self):
        text = "t_s,dP_bar,Q_m3_s\n0.0,1.0,1e-8\n"
        readings = parse_csv(StringIO(text))
        assert readings[0].dP_pa == 100000.0

    def test_q_ml_min_to_m3_s(self):
        text = "t_s,dP_pa,Q_mL_min\n0.0,1000,60.0\n"
        readings = parse_csv(StringIO(text))
        # 60 mL/min = 1 mL/s = 1e-6 m³/s
        assert readings[0].Q_m3_s == pytest.approx(1.0e-6, rel=1e-12)

    def test_pressure_pa_alias(self):
        text = "t_s,pressure_pa,Q_m3_s\n0.0,9999,1e-8\n"
        readings = parse_csv(StringIO(text))
        assert readings[0].dP_pa == 9999.0

    def test_case_insensitive(self):
        text = "T_S,DP_PA,Q_M3_S\n0.0,1000,1e-8\n"
        readings = parse_csv(StringIO(text))
        assert readings[0].dP_pa == 1000.0


class TestParseCsvSkipRules:
    def test_skip_unparseable_rows(self):
        text = (
            "t_s,dP_pa,Q_m3_s\n"
            "0.0,1000,1e-8\n"
            "junk,bad,row\n"
            "2.0,3000,1e-8\n"
        )
        readings = parse_csv(StringIO(text))
        assert len(readings) == 2
        assert readings[0].t_s == 0.0
        assert readings[1].t_s == 2.0

    def test_skip_negative_dp(self):
        text = (
            "t_s,dP_pa,Q_m3_s\n"
            "0.0,-100,1e-8\n"
            "1.0,1000,1e-8\n"
        )
        readings = parse_csv(StringIO(text))
        assert len(readings) == 1
        assert readings[0].t_s == 1.0

    def test_sorts_by_time_ascending(self):
        text = (
            "t_s,dP_pa,Q_m3_s\n"
            "5.0,5000,1e-8\n"
            "1.0,1000,1e-8\n"
            "3.0,3000,1e-8\n"
        )
        readings = parse_csv(StringIO(text))
        assert [r.t_s for r in readings] == [1.0, 3.0, 5.0]

    def test_empty_csv_raises(self):
        with pytest.raises(ValueError, match="empty"):
            parse_csv(StringIO(""))

    def test_missing_required_column_raises(self):
        text = "t_s,dP_pa\n0.0,1000\n"
        with pytest.raises(ValueError, match="Q_m3_s"):
            parse_csv(StringIO(text))

    def test_no_parseable_rows_raises(self):
        text = (
            "t_s,dP_pa,Q_m3_s\n"
            "junk,bad,row\n"
        )
        with pytest.raises(ValueError, match="no parseable readings"):
            parse_csv(StringIO(text))


# ─── replay ────────────────────────────────────────────────────────────────


class TestReplay:
    def test_empty_readings_raises(self, default_envelope):
        with pytest.raises(ValueError, match="at least one"):
            replay((), default_envelope)

    def test_smooth_run_stays_ok(self, default_envelope):
        """A smooth run at ~50 % headroom and within the model band stays OK.

        Uses ΔP at exactly the predicted value so deviation_ratio = 1.0
        (in the [0.6, 1.5] OK band) and headroom = predicted/operational
        (well below 0.70 by construction of the fixture).
        """
        Q_set = default_envelope.Q_set_m3_s
        dp = default_envelope.dP_predicted_pa
        readings = tuple(
            PressureMonitorReading(t_s=float(t), dP_pa=dp, Q_m3_s=Q_set)
            for t in range(0, 60, 5)
        )
        summary = replay(readings, default_envelope)
        assert summary.final_state == PressureMonitorState.OK
        assert summary.blocker_first_t_s is None
        assert summary.warning_first_t_s is None
        assert summary.n_readings == 12

    def test_headroom_blocker_is_caught(self, default_envelope):
        """A reading at headroom = 0.95 → BLOCKER on first hit."""
        Q_set = default_envelope.Q_set_m3_s
        dp_pred = default_envelope.dP_predicted_pa
        dp_blocker = default_envelope.dP_max_operational_pa * 0.95
        readings = (
            # First reading: at predicted (OK in deviation + headroom).
            PressureMonitorReading(t_s=0.0, dP_pa=dp_pred, Q_m3_s=Q_set),
            # Second: spike to blocker headroom. The dPdt rule may also
            # fire here because of the rapid jump; either path is BLOCKER.
            PressureMonitorReading(t_s=10.0, dP_pa=dp_blocker, Q_m3_s=Q_set),
        )
        summary = replay(readings, default_envelope)
        assert summary.final_state == PressureMonitorState.BLOCKER
        assert summary.blocker_first_t_s == 10.0
        # Either HEADROOM_BLOCKER (≥ 0.85 ratio) or DPDT_BLOCKER /
        # MODEL_DEVIATION_HIGH from the rapid rise satisfies the rule.
        assert summary.blocker_first_rule in (
            PressureMonitorRule.HEADROOM_BLOCKER,
            PressureMonitorRule.DPDT_BLOCKER,
            PressureMonitorRule.MODEL_DEVIATION_HIGH,
            PressureMonitorRule.SPIKE,
        )

    def test_state_timeline_has_one_entry_per_reading(self, default_envelope):
        Q_set = default_envelope.Q_set_m3_s
        dp = default_envelope.dP_predicted_pa
        readings = tuple(
            PressureMonitorReading(t_s=float(t), dP_pa=dp, Q_m3_s=Q_set)
            for t in range(5)
        )
        summary = replay(readings, default_envelope)
        assert len(summary.state_timeline) == 5
        assert summary.state_timeline[0][0] == 0.0
        assert summary.state_timeline[-1][0] == 4.0

    def test_max_headroom_tracks_peak(self, default_envelope):
        Q_set = default_envelope.Q_set_m3_s
        peak = default_envelope.dP_max_operational_pa * 0.6
        readings = (
            PressureMonitorReading(t_s=0.0, dP_pa=peak * 0.3, Q_m3_s=Q_set),
            PressureMonitorReading(t_s=5.0, dP_pa=peak, Q_m3_s=Q_set),
            PressureMonitorReading(t_s=10.0, dP_pa=peak * 0.5, Q_m3_s=Q_set),
        )
        summary = replay(readings, default_envelope)
        # Peak headroom = peak / dP_max_operational ≈ 0.6
        assert summary.max_headroom_ratio == pytest.approx(0.6, rel=1e-9)

    def test_history_is_immutable_through_replay(self, default_envelope):
        Q_set = default_envelope.Q_set_m3_s
        dp = default_envelope.dP_predicted_pa
        readings = tuple(
            PressureMonitorReading(t_s=float(t), dP_pa=dp, Q_m3_s=Q_set)
            for t in range(3)
        )
        summary = replay(readings, default_envelope)
        # Returned history is a tuple — immutable.
        assert isinstance(summary.history, tuple)
        assert len(summary.history) == 3


class TestReplayParseAndChain:
    def test_csv_to_replay_round_trip(self, default_envelope):
        Q_set = default_envelope.Q_set_m3_s
        dp = default_envelope.dP_predicted_pa
        # Synthesise a CSV with three readings at the predicted operating
        # point — should stay OK across all three.
        text = "t_s,dP_pa,Q_m3_s\n"
        for t in range(3):
            text += f"{float(t)},{dp},{Q_set}\n"
        readings = parse_csv(StringIO(text))
        summary = replay(readings, default_envelope)
        assert summary.n_readings == 3
        assert summary.final_state == PressureMonitorState.OK
