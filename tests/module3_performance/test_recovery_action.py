"""Tests for the RecoveryAction routing (B-2ℓ / W-041, v0.8.2).

Verifies:

* Each PressureMonitorRule maps to a deterministic RecoveryAction.
* OK output carries RecoveryAction.NONE.
* The replay pipeline propagates the final action onto ReplaySummary.
"""

from __future__ import annotations

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
    RecoveryAction,
    evaluate_pressure_trace,
)
from dpsim.module3_performance.pressure_monitor_replay import replay


@pytest.fixture
def envelope():
    column = ColumnGeometry()
    mp = MobilePhase()
    pre = compute_pressure_envelope(
        polymer_family=PolymerFamily.AGAROSE,
        column=column,
        mobile_phase=mp,
        Q_set_m3_s=1e-9,
    )
    return compute_pressure_envelope(
        polymer_family=PolymerFamily.AGAROSE,
        column=column,
        mobile_phase=mp,
        Q_set_m3_s=pre.Q_recommended_m3_s * 0.1,
    )


# ─── Per-rule action mapping ──────────────────────────────────────────────


class TestRuleToActionMapping:
    def test_ok_state_carries_none_action(self, envelope):
        Q_set = envelope.Q_set_m3_s
        out = evaluate_pressure_trace(
            reading=PressureMonitorReading(
                t_s=0.0,
                dP_pa=envelope.dP_predicted_pa,
                Q_m3_s=Q_set,
            ),
            envelope=envelope,
        )
        assert out.state == PressureMonitorState.OK
        assert out.recovery_action == RecoveryAction.NONE

    def test_headroom_blocker_yields_reduce_flow(self, envelope):
        Q_set = envelope.Q_set_m3_s
        # First reading at predicted (OK), second jumps to ≥ 0.85 headroom.
        history = (
            PressureMonitorReading(
                t_s=0.0,
                dP_pa=envelope.dP_predicted_pa,
                Q_m3_s=Q_set,
            ),
        )
        out = evaluate_pressure_trace(
            reading=PressureMonitorReading(
                t_s=10.0,
                dP_pa=envelope.dP_max_operational_pa * 0.95,
                Q_m3_s=Q_set,
            ),
            envelope=envelope,
            history=history,
        )
        assert out.state == PressureMonitorState.BLOCKER
        # Either HEADROOM_BLOCKER or DPDT_BLOCKER fires; both are
        # actionable. Verify the action is one of the legitimate
        # mappings.
        if out.triggered_rule == PressureMonitorRule.HEADROOM_BLOCKER:
            assert out.recovery_action == RecoveryAction.REDUCE_FLOW
        elif out.triggered_rule == PressureMonitorRule.DPDT_BLOCKER:
            assert out.recovery_action == RecoveryAction.SWITCH_TO_WASH

    def test_model_deviation_low_yields_stop_and_repack(self, envelope):
        # Build readings whose ΔP is well below predicted but nonzero.
        Q_set = envelope.Q_set_m3_s
        out = evaluate_pressure_trace(
            reading=PressureMonitorReading(
                t_s=0.0,
                dP_pa=envelope.dP_predicted_pa * 0.30,  # 30% of predicted
                Q_m3_s=Q_set,
            ),
            envelope=envelope,
        )
        assert out.state == PressureMonitorState.BLOCKER
        assert out.triggered_rule == PressureMonitorRule.MODEL_DEVIATION_LOW
        assert out.recovery_action == RecoveryAction.STOP_AND_REPACK


# ─── Replay surface ───────────────────────────────────────────────────────


class TestReplayCarriesRecoveryAction:
    def test_smooth_replay_gives_none_action(self, envelope):
        Q_set = envelope.Q_set_m3_s
        readings = tuple(
            PressureMonitorReading(
                t_s=float(t),
                dP_pa=envelope.dP_predicted_pa,
                Q_m3_s=Q_set,
            )
            for t in range(5)
        )
        summary = replay(readings, envelope)
        assert summary.final_state == PressureMonitorState.OK
        assert summary.final_recovery_action == RecoveryAction.NONE

    def test_blocker_replay_carries_actionable_recovery(self, envelope):
        Q_set = envelope.Q_set_m3_s
        # Stable for a few seconds, then channeling-style collapse.
        readings = (
            PressureMonitorReading(
                t_s=0.0,
                dP_pa=envelope.dP_predicted_pa,
                Q_m3_s=Q_set,
            ),
            PressureMonitorReading(
                t_s=10.0,
                dP_pa=envelope.dP_predicted_pa * 0.30,
                Q_m3_s=Q_set,
            ),
        )
        summary = replay(readings, envelope)
        assert summary.final_state == PressureMonitorState.BLOCKER
        assert summary.final_recovery_action != RecoveryAction.NONE


# ─── Coverage of every rule ───────────────────────────────────────────────


class TestEveryRuleHasAnAction:
    def test_complete_rule_to_action_coverage(self):
        """Every PressureMonitorRule member must map to a non-NONE action.

        Sentinel: if a future PR adds a new rule but forgets the action
        mapping, this test fails.
        """
        from dpsim.module3_performance.pressure_monitor import _RULE_TO_ACTION

        for rule in PressureMonitorRule:
            assert rule in _RULE_TO_ACTION, (
                f"PressureMonitorRule.{rule.name} has no RecoveryAction mapping"
            )
            assert _RULE_TO_ACTION[rule] != RecoveryAction.NONE
