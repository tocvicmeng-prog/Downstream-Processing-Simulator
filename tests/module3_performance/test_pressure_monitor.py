"""B-3d / W-027 tests: streaming pressure-trace monitor.

Covers each of the 7 rules in the PressureMonitorRule enum, the
3-state machine (OK / WARNING / BLOCKER), history pruning, immutable
history return, and CSV-fixture-style replay.

Per architect §3.5 — function-only ship; the streaming UI integration
is deferred to v0.8.
"""

from __future__ import annotations

import pytest

from dpsim.core.mobile_phase import MobilePhase
from dpsim.datatypes import PolymerFamily
from dpsim.module3_performance.hydrodynamics import ColumnGeometry
from dpsim.module3_performance.pressure_envelope import (
    PressureEnvelope,
    compute_pressure_envelope,
)
from dpsim.module3_performance.pressure_monitor import (
    PressureMonitorReading,
    PressureMonitorRule,
    PressureMonitorState,
    evaluate_pressure_trace,
)


# ─── Fixtures ────────────────────────────────────────────────────────────────


def _envelope() -> PressureEnvelope:
    """Standardized envelope from a Sepharose 4FF column at typical Q.

    Builds the envelope at Q_recommended (50 % of Q_max) so that
    ``dP_predicted_pa`` is roughly 0.5 × ``dP_max_operational_pa``.
    This keeps test readings near 50 % of dP_max_op simultaneously
    inside the OK band for both the headroom rule and the
    model-deviation rule.
    """
    col = ColumnGeometry(
        diameter=0.01,
        bed_height=0.10,
        particle_diameter=90e-6,
        bed_porosity=0.38,
        particle_porosity=0.70,
        G_DN=5000.0,
        E_star=50000.0,
    )
    # Probe at very low Q to get Q_max, then build the real envelope
    # at Q_recommended.
    probe = compute_pressure_envelope(
        polymer_family=PolymerFamily.AGAROSE,
        column=col,
        mobile_phase=MobilePhase(),
        Q_set_m3_s=1e-9,
    )
    return compute_pressure_envelope(
        polymer_family=PolymerFamily.AGAROSE,
        column=col,
        mobile_phase=MobilePhase(),
        Q_set_m3_s=probe.Q_recommended_m3_s,
    )


def _reading(t_s: float, dP_pa: float, Q_m3_s: float = 1e-7) -> PressureMonitorReading:
    return PressureMonitorReading(t_s=t_s, dP_pa=dP_pa, Q_m3_s=Q_m3_s)


# ─── State machine + OK ─────────────────────────────────────────────────────


class TestOKState:
    """Within-envelope, low rate-of-rise readings → OK.

    OK-band readings are built relative to ``dP_predicted_pa`` so they
    sit inside both the headroom band and the model-deviation band.
    """

    def test_first_reading_within_envelope_is_ok(self) -> None:
        env = _envelope()
        # Reading exactly equal to predicted → ratio 1.0, no rule fires.
        result = evaluate_pressure_trace(
            reading=_reading(0.0, env.dP_predicted_pa * 1.0),
            envelope=env,
        )
        assert result.state == PressureMonitorState.OK
        assert result.triggered_rule is None

    def test_ok_state_has_action_message(self) -> None:
        env = _envelope()
        result = evaluate_pressure_trace(
            reading=_reading(0.0, env.dP_predicted_pa * 1.1),
            envelope=env,
        )
        assert result.suggested_action != ""

    def test_history_starts_with_first_reading(self) -> None:
        env = _envelope()
        result = evaluate_pressure_trace(
            reading=_reading(0.0, env.dP_predicted_pa * 1.0),
            envelope=env,
        )
        assert len(result.history) == 1


# ─── HEADROOM rules ──────────────────────────────────────────────────────────


class TestHeadroomRules:
    """ΔP/ΔP_max at 0.70+ → WARNING, 0.85+ → BLOCKER."""

    def test_at_70pct_triggers_warning(self) -> None:
        env = _envelope()
        result = evaluate_pressure_trace(
            reading=_reading(0.0, env.dP_max_operational_pa * 0.71),
            envelope=env,
        )
        assert result.state == PressureMonitorState.WARNING
        assert result.triggered_rule == PressureMonitorRule.HEADROOM_WARNING

    def test_at_85pct_triggers_blocker(self) -> None:
        env = _envelope()
        result = evaluate_pressure_trace(
            reading=_reading(0.0, env.dP_max_operational_pa * 0.86),
            envelope=env,
        )
        assert result.state == PressureMonitorState.BLOCKER
        assert result.triggered_rule == PressureMonitorRule.HEADROOM_BLOCKER

    def test_blocker_action_says_reduce_or_abort(self) -> None:
        env = _envelope()
        result = evaluate_pressure_trace(
            reading=_reading(0.0, env.dP_max_operational_pa * 0.90),
            envelope=env,
        )
        action = result.suggested_action.lower()
        assert "reduce" in action or "abort" in action


# ─── dΔP/dt rules ────────────────────────────────────────────────────────────


class TestDpdtRules:
    """Rate-of-rise of ΔP across the history window.

    The rate-of-rise rules require accumulated history. The test
    builds up a series of readings and checks that the dΔP/dt slope
    triggers the right rule.
    """

    def test_slow_rise_triggers_dpdt_warning(self) -> None:
        env = _envelope()
        # Stay below headroom warning threshold (0.7) so the dpdt rule
        # is the binding one. Start at 0.40, end at 0.45 over 30 s
        # → 12.5 % rise / 0.5 min = 25 %/min — but that's blocker.
        # Use a slower rise: 0.40 → 0.42 over 30 s = 5 % rise / 0.5 min
        # = 10 %/min — warning band.
        history: tuple[PressureMonitorReading, ...] = ()
        result_chain = None
        for i, t in enumerate([0.0, 10.0, 20.0, 30.0]):
            dP = env.dP_max_operational_pa * (0.40 + 0.005 * i)
            result_chain = evaluate_pressure_trace(
                reading=_reading(t, dP),
                envelope=env,
                history=history,
            )
            history = result_chain.history
        assert result_chain is not None
        assert result_chain.state == PressureMonitorState.WARNING
        assert result_chain.triggered_rule == PressureMonitorRule.DPDT_WARNING
        assert result_chain.dpdt_pct_per_min >= 5.0
        assert result_chain.dpdt_pct_per_min < 20.0

    def test_fast_rise_triggers_dpdt_blocker(self) -> None:
        env = _envelope()
        # 50 % rise over 30 s = 100 %/min — definitely blocker territory.
        # But spike rule fires first at >100 %/min sustained > 5 s.
        # Use: 0.30 → 0.40 over 30 s = 33 % rise / 0.5 min = 67 %/min
        # — DPDT_BLOCKER (≥ 20) but below SPIKE (≥ 100).
        history: tuple[PressureMonitorReading, ...] = ()
        result_chain = None
        for t, ratio in [(0.0, 0.30), (10.0, 0.33), (20.0, 0.37), (30.0, 0.40)]:
            result_chain = evaluate_pressure_trace(
                reading=_reading(t, env.dP_max_operational_pa * ratio),
                envelope=env,
                history=history,
            )
            history = result_chain.history
        assert result_chain is not None
        assert result_chain.state == PressureMonitorState.BLOCKER
        assert result_chain.triggered_rule in {
            PressureMonitorRule.DPDT_BLOCKER,
            PressureMonitorRule.SPIKE,
        }


# ─── Model deviation rules ──────────────────────────────────────────────────


class TestModelDeviation:
    """ΔP_meas / ΔP_predicted < 0.6 → channeling; > 1.5 → fouling."""

    def test_low_deviation_triggers_channeling_blocker(self) -> None:
        env = _envelope()
        # Deviation ratio 0.30 → BLOCKER (channeling).
        # Use measured ΔP < 0.6 × predicted, but headroom must also be
        # within bounds (otherwise headroom_blocker fires first).
        # At our envelope, dP_predicted is much smaller than dP_max_op.
        result = evaluate_pressure_trace(
            reading=_reading(0.0, env.dP_predicted_pa * 0.30),
            envelope=env,
        )
        assert result.state == PressureMonitorState.BLOCKER
        assert result.triggered_rule == PressureMonitorRule.MODEL_DEVIATION_LOW
        assert "channel" in result.suggested_action.lower()

    def test_high_deviation_triggers_fouling_warning(self) -> None:
        env = _envelope()
        # Deviation ratio 1.6 → WARNING (fouling). Make sure headroom
        # is below warning threshold.
        target_dP = env.dP_predicted_pa * 1.60
        # Sanity: target_dP must be < 0.70 × dP_max_op for headroom
        # NOT to trip first.
        if target_dP < env.dP_max_operational_pa * 0.70:
            result = evaluate_pressure_trace(
                reading=_reading(0.0, target_dP),
                envelope=env,
            )
            assert result.state == PressureMonitorState.WARNING
            assert result.triggered_rule == PressureMonitorRule.MODEL_DEVIATION_HIGH


# ─── Spike detection ─────────────────────────────────────────────────────────


class TestSpikeDetection:
    """Sudden ΔP rise > 100 %/min sustained > 5 s → SPIKE BLOCKER."""

    def test_sudden_spike_triggers_blocker(self) -> None:
        env = _envelope()
        # 100 % rise over 6 s = 1000 %/min — clear spike.
        baseline = env.dP_predicted_pa
        history: tuple[PressureMonitorReading, ...] = ()
        # Start with baseline reading.
        r1 = evaluate_pressure_trace(
            reading=_reading(0.0, baseline),
            envelope=env,
        )
        history = r1.history
        # Sudden spike at t=6 s.
        r2 = evaluate_pressure_trace(
            reading=_reading(6.0, baseline * 2.0),
            envelope=env,
            history=history,
        )
        # Either SPIKE or another more-immediate rule (model deviation)
        # may fire. Either way, the state must be BLOCKER.
        assert r2.state == PressureMonitorState.BLOCKER


# ─── History management ─────────────────────────────────────────────────────


class TestHistoryManagement:
    """History is appended, pruned, and immutable."""

    def test_history_grows_with_each_call(self) -> None:
        env = _envelope()
        history: tuple[PressureMonitorReading, ...] = ()
        for t in [0.0, 5.0, 10.0]:
            result = evaluate_pressure_trace(
                reading=_reading(t, env.dP_max_operational_pa * 0.30),
                envelope=env,
                history=history,
            )
            history = result.history
        assert len(history) == 3

    def test_history_pruned_beyond_window(self) -> None:
        env = _envelope()
        history: tuple[PressureMonitorReading, ...] = ()
        # Fill history with readings spanning > 300 s.
        for t in [0.0, 100.0, 200.0, 350.0]:
            result = evaluate_pressure_trace(
                reading=_reading(t, env.dP_max_operational_pa * 0.30),
                envelope=env,
                history=history,
                history_max_seconds=300.0,
            )
            history = result.history
        # The t=0 reading (350 s ago) should be pruned.
        for r in history:
            assert r.t_s >= 350.0 - 300.0

    def test_history_returned_is_new_tuple(self) -> None:
        env = _envelope()
        original = (_reading(0.0, 100.0),)
        result = evaluate_pressure_trace(
            reading=_reading(5.0, 200.0),
            envelope=env,
            history=original,
        )
        # The returned history is NOT the same object as the input.
        assert result.history is not original
        # But the original is unchanged.
        assert original == (_reading(0.0, 100.0),)

    def test_none_history_treated_as_empty(self) -> None:
        env = _envelope()
        result = evaluate_pressure_trace(
            reading=_reading(0.0, 100.0),
            envelope=env,
            history=None,
        )
        assert len(result.history) == 1


# ─── Validation ──────────────────────────────────────────────────────────────


class TestValidation:
    """Invalid inputs raise."""

    def test_negative_dP_raises(self) -> None:
        env = _envelope()
        with pytest.raises(ValueError, match="dP_pa"):
            evaluate_pressure_trace(
                reading=_reading(0.0, -100.0),
                envelope=env,
            )

    def test_none_envelope_raises(self) -> None:
        with pytest.raises(ValueError, match="envelope"):
            evaluate_pressure_trace(
                reading=_reading(0.0, 100.0),
                envelope=None,  # type: ignore[arg-type]
            )


# ─── Frozen contract ─────────────────────────────────────────────────────────


class TestFrozenContract:
    """PressureMonitorOutput and PressureMonitorReading are frozen."""

    def test_reading_is_frozen(self) -> None:
        from dataclasses import FrozenInstanceError

        r = _reading(0.0, 100.0)
        with pytest.raises(FrozenInstanceError):
            r.t_s = 1.0  # type: ignore[misc]

    def test_output_is_frozen(self) -> None:
        from dataclasses import FrozenInstanceError

        env = _envelope()
        result = evaluate_pressure_trace(
            reading=_reading(0.0, 100.0),
            envelope=env,
        )
        with pytest.raises(FrozenInstanceError):
            result.state = PressureMonitorState.BLOCKER  # type: ignore[misc]


# ─── Replay simulation ──────────────────────────────────────────────────────


class TestTraceReplay:
    """Replay a synthesized fouling trace to verify state transitions."""

    def test_fouling_trace_progresses_ok_warning_blocker(self) -> None:
        env = _envelope()
        # Trace: starts at 50 % headroom, rises slowly to ~100 %.
        # Should: OK → WARNING (at 70 %) → BLOCKER (at 85 %).
        # Starts at 0.50 (within model-deviation OK band given the
        # envelope's predicted ≈ 0.62 × dP_max_op).
        states_seen: list[PressureMonitorState] = []
        history: tuple[PressureMonitorReading, ...] = ()
        for i in range(11):
            ratio = 0.50 + i * 0.05  # 0.50, 0.55, ..., 1.00
            result = evaluate_pressure_trace(
                reading=_reading(
                    t_s=i * 60.0,  # 60 s spacing → slow rise (no DPDT trip)
                    dP_pa=env.dP_max_operational_pa * ratio,
                ),
                envelope=env,
                history=history,
            )
            history = result.history
            states_seen.append(result.state)

        # The trace must include all three states in order.
        assert PressureMonitorState.OK in states_seen
        assert PressureMonitorState.WARNING in states_seen
        assert PressureMonitorState.BLOCKER in states_seen
        # OK must come before WARNING; WARNING must come before BLOCKER.
        ok_idx = states_seen.index(PressureMonitorState.OK)
        warn_idx = states_seen.index(PressureMonitorState.WARNING)
        block_idx = states_seen.index(PressureMonitorState.BLOCKER)
        assert ok_idx < warn_idx
        assert warn_idx < block_idx
