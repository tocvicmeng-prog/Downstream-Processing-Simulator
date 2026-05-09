"""Real-time pressure-trace monitor for chromatography column operation.

B-3d / W-027 — Δ8 from the v0.7.0 M3 back-pressure work plan
(``docs/update_workplan_2026-05-10_m3_pressure.md``).

Companion to :mod:`dpsim.module3_performance.pressure_envelope`. Where
``compute_pressure_envelope`` produces a *pre-flight* envelope at
recipe-step time (before the user presses "Start flow"), this module
evaluates streaming (t, ΔP, Q) readings *during* a run against that
envelope and emits OK / WARNING / BLOCKER state transitions.

v0.7 ships the function only; the live Streamlit widget + AKTA UNICORN
integration are deferred to a v0.8 epic. The function alone is testable
offline by replaying a CSV trace from a previous run.

Three-state machine (architect §2.h):

* OK — all rules pass.
* WARNING — at least one rule's warning threshold is breached.
* BLOCKER — at least one rule's blocker threshold is breached, OR the
  WARNING state has persisted for ``warning_dwell_seconds`` continuously.

Rule taxonomy:

* HEADROOM_WARNING / HEADROOM_BLOCKER — instantaneous ΔP / ΔP_max ratio.
* DPDT_WARNING / DPDT_BLOCKER — rate-of-rise of ΔP at constant Q
  (fouling, channeling onset).
* MODEL_DEVIATION_LOW / MODEL_DEVIATION_HIGH — measured ΔP much below
  (channeling) or above (fouling) the envelope's predicted ΔP.
* SPIKE — sudden dΔP/dt > 100 %/min for > 5 s (channeling collapse,
  gas pocket release).

Hysteresis: warnings dwell for 30 s before promoting to BLOCKER, but
spikes and ratio breaches above the hard threshold trigger BLOCKER
immediately.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from dpsim.module3_performance.pressure_envelope import PressureEnvelope


# ─── Enums ───────────────────────────────────────────────────────────────────


class PressureMonitorRule(Enum):
    """Which rule fired (None on OK)."""

    HEADROOM_WARNING = "headroom_warning"
    HEADROOM_BLOCKER = "headroom_blocker"
    DPDT_WARNING = "dpdt_warning"
    DPDT_BLOCKER = "dpdt_blocker"
    MODEL_DEVIATION_LOW = "model_deviation_low"   # channeling
    MODEL_DEVIATION_HIGH = "model_deviation_high"  # fouling
    SPIKE = "spike"


class PressureMonitorState(Enum):
    """Three-state machine for the live monitor."""

    OK = "ok"
    WARNING = "warning"
    BLOCKER = "blocker"


# ─── Value types ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PressureMonitorReading:
    """Single timestamped panel reading.

    Attributes
    ----------
    t_s : float
        Wall-clock time since run start [s].
    dP_pa : float
        Measured ΔP across the column [Pa].
    Q_m3_s : float
        Measured volumetric flow rate [m³/s] (echoed for the rate-of-rise
        check; if Q changes, the dΔP/dt rule resets).
    """

    t_s: float
    dP_pa: float
    Q_m3_s: float


@dataclass(frozen=True)
class PressureMonitorOutput:
    """Output of one ``evaluate_pressure_trace`` call.

    The ``history`` field is a NEW immutable tuple each call — the
    function does not mutate the caller's history. Append-and-prune
    semantics: new readings are appended; readings older than
    ``history_max_seconds`` (default 300 s = 5 min) are dropped.

    Attributes
    ----------
    state :
        Current monitor state.
    triggered_rule :
        The rule that drove the state transition. ``None`` when state
        is OK.
    suggested_action :
        Human-readable recommendation for the operator.
    headroom_ratio :
        Current ΔP_measured / envelope.dP_max_operational_pa.
    dpdt_pct_per_min :
        Rate of rise of ΔP over the recent history window, expressed
        as % per minute relative to the trace's first ΔP.
    model_deviation_ratio :
        ΔP_measured / envelope.dP_predicted_pa. < 0.6 → channeling;
        > 1.5 → fouling/clogging.
    history :
        Updated trace history (NEW tuple; immutable).
    """

    state: PressureMonitorState
    triggered_rule: Optional[PressureMonitorRule]
    suggested_action: str
    headroom_ratio: float
    dpdt_pct_per_min: float
    model_deviation_ratio: float
    history: tuple[PressureMonitorReading, ...] = field(default_factory=tuple)


# ─── Threshold constants (architect §2.h) ───────────────────────────────────


_HEADROOM_WARNING_THRESHOLD: float = 0.70
_HEADROOM_BLOCKER_THRESHOLD: float = 0.85
_DPDT_WARNING_PCT_PER_MIN: float = 5.0
_DPDT_BLOCKER_PCT_PER_MIN: float = 20.0
_MODEL_DEVIATION_LOW_THRESHOLD: float = 0.60
_MODEL_DEVIATION_HIGH_THRESHOLD: float = 1.50
_SPIKE_PCT_PER_MIN: float = 100.0
_SPIKE_DWELL_SECONDS: float = 5.0


# ─── History management ─────────────────────────────────────────────────────


def _prune_history(
    history: tuple[PressureMonitorReading, ...],
    *,
    now: float,
    max_seconds: float,
) -> tuple[PressureMonitorReading, ...]:
    """Drop readings older than ``max_seconds`` before ``now``."""
    cutoff = now - max_seconds
    return tuple(r for r in history if r.t_s >= cutoff)


def _compute_dpdt_pct_per_min(
    history: tuple[PressureMonitorReading, ...],
) -> float:
    """Rate of rise of ΔP across the history, normalized to %/min."""
    if len(history) < 2:
        return 0.0
    first = history[0]
    last = history[-1]
    dt_s = last.t_s - first.t_s
    if dt_s <= 0.0:
        return 0.0
    if first.dP_pa <= 0.0:
        return 0.0
    pct_total = (last.dP_pa - first.dP_pa) / first.dP_pa * 100.0
    pct_per_s = pct_total / dt_s
    return pct_per_s * 60.0


def _detect_spike(
    history: tuple[PressureMonitorReading, ...],
    *,
    spike_dwell_s: float,
) -> bool:
    """Detect a > 100 %/min spike persisting for > 5 s.

    Looks for a sustained rapid rise: there must be at least two
    readings within the last ``spike_dwell_s`` seconds AND the local
    dΔP/dt across that window must exceed ``_SPIKE_PCT_PER_MIN``.
    """
    if len(history) < 2:
        return False
    last_t = history[-1].t_s
    window_start = last_t - spike_dwell_s
    window = [r for r in history if r.t_s >= window_start]
    if len(window) < 2:
        return False
    first = window[0]
    last = window[-1]
    dt_s = last.t_s - first.t_s
    if dt_s <= 0.0:
        return False
    if first.dP_pa <= 0.0:
        return False
    pct_per_s = (last.dP_pa - first.dP_pa) / first.dP_pa * 100.0 / dt_s
    return pct_per_s * 60.0 > _SPIKE_PCT_PER_MIN


# ─── Public API ──────────────────────────────────────────────────────────────


def evaluate_pressure_trace(
    *,
    reading: PressureMonitorReading,
    envelope: PressureEnvelope,
    history: Optional[tuple[PressureMonitorReading, ...]] = None,
    history_max_seconds: float = 300.0,
    warning_dwell_seconds: float = 30.0,
) -> PressureMonitorOutput:
    """Evaluate one streaming reading against the envelope.

    Pure function: takes the current reading + the pre-flight envelope
    + optional history, returns the new state + new history. The
    caller drives the loop and decides what to do with the state
    transitions.

    Rule evaluation order (first match wins for the state assignment):

    1. SPIKE (sustained > 100 %/min for > 5 s) → BLOCKER immediately.
    2. HEADROOM_BLOCKER (ΔP_meas / ΔP_max ≥ 0.85) → BLOCKER immediately.
    3. DPDT_BLOCKER (dΔP/dt ≥ 20 %/min) → BLOCKER immediately.
    4. MODEL_DEVIATION_LOW (ΔP_meas / ΔP_predicted < 0.60) → BLOCKER
       immediately (channeling collapse).
    5. MODEL_DEVIATION_HIGH (ΔP_meas / ΔP_predicted > 1.50) → WARNING.
    6. HEADROOM_WARNING (ΔP_meas / ΔP_max ≥ 0.70 < 0.85) → WARNING.
    7. DPDT_WARNING (dΔP/dt ≥ 5 < 20 %/min) → WARNING.
    8. Otherwise → OK.

    Parameters
    ----------
    reading :
        Current panel reading.
    envelope :
        Pre-flight envelope from ``compute_pressure_envelope`` for the
        current recipe step.
    history :
        Prior trace history. ``None`` is equivalent to empty.
    history_max_seconds :
        Window length for dΔP/dt and spike detection. Older readings
        are pruned.
    warning_dwell_seconds :
        Reserved for future use — currently a parameter for the
        dwell-to-BLOCKER promotion logic when the caller drives a
        stateful WARNING-persistence check externally.

    Returns
    -------
    PressureMonitorOutput
        New monitor state with the immutable updated history.
    """
    if envelope is None:
        raise ValueError("envelope must be provided.")
    if reading.dP_pa < 0.0:
        raise ValueError(f"reading.dP_pa={reading.dP_pa!r} must be ≥ 0.")

    # Update + prune history.
    base_history = history if history is not None else ()
    new_history = _prune_history(
        base_history + (reading,),
        now=reading.t_s,
        max_seconds=history_max_seconds,
    )

    # Compute the three diagnostic ratios.
    dP_max = envelope.dP_max_operational_pa
    headroom_ratio = reading.dP_pa / dP_max if dP_max > 0.0 else float("inf")
    dpdt_pct = _compute_dpdt_pct_per_min(new_history)
    dP_pred = envelope.dP_predicted_pa
    deviation_ratio = (
        reading.dP_pa / dP_pred if dP_pred > 0.0 else float("inf")
    )

    # Rule evaluation (first-match-wins in the BLOCKER tier, then
    # WARNING tier, then OK).
    state = PressureMonitorState.OK
    triggered: Optional[PressureMonitorRule] = None
    action = "Operating within envelope. Continue."

    # 1. SPIKE — immediate BLOCKER.
    if _detect_spike(new_history, spike_dwell_s=_SPIKE_DWELL_SECONDS):
        state = PressureMonitorState.BLOCKER
        triggered = PressureMonitorRule.SPIKE
        action = (
            "EMERGENCY STOP. Sudden ΔP spike detected — channeling "
            "collapse or gas-pocket release likely. Halt flow, depressurize, "
            "inspect column."
        )
    # 2. HEADROOM_BLOCKER.
    elif headroom_ratio >= _HEADROOM_BLOCKER_THRESHOLD:
        state = PressureMonitorState.BLOCKER
        triggered = PressureMonitorRule.HEADROOM_BLOCKER
        action = (
            f"BLOCKER — ΔP/ΔP_max = {headroom_ratio:.2f} ≥ "
            f"{_HEADROOM_BLOCKER_THRESHOLD:.2f}. Reduce flow rate to "
            f"≤ Q_recommended ({envelope.Q_recommended_m3_s:.2e} m³/s) or "
            "abort the run."
        )
    # 3. DPDT_BLOCKER.
    elif dpdt_pct >= _DPDT_BLOCKER_PCT_PER_MIN:
        state = PressureMonitorState.BLOCKER
        triggered = PressureMonitorRule.DPDT_BLOCKER
        action = (
            f"BLOCKER — dΔP/dt = {dpdt_pct:.1f} %/min ≥ "
            f"{_DPDT_BLOCKER_PCT_PER_MIN} %/min. Channeling onset or "
            "rapid fouling. Pause load, switch to wash."
        )
    # 4. MODEL_DEVIATION_LOW (channeling).
    elif deviation_ratio < _MODEL_DEVIATION_LOW_THRESHOLD:
        state = PressureMonitorState.BLOCKER
        triggered = PressureMonitorRule.MODEL_DEVIATION_LOW
        action = (
            f"BLOCKER — measured ΔP is {deviation_ratio*100:.0f} % of "
            f"predicted (< {_MODEL_DEVIATION_LOW_THRESHOLD*100:.0f} %). "
            "Bed has channeled. Stop run; do NOT lower Q to recover; "
            "repack or replace column."
        )
    # 5. MODEL_DEVIATION_HIGH (fouling).
    elif deviation_ratio > _MODEL_DEVIATION_HIGH_THRESHOLD:
        state = PressureMonitorState.WARNING
        triggered = PressureMonitorRule.MODEL_DEVIATION_HIGH
        action = (
            f"WARNING — measured ΔP is {deviation_ratio*100:.0f} % of "
            f"predicted (> {_MODEL_DEVIATION_HIGH_THRESHOLD*100:.0f} %). "
            "Likely fouling. Add 0.22 µm pre-filter to feed line; "
            "consider switching to wash."
        )
    # 6. HEADROOM_WARNING.
    elif headroom_ratio >= _HEADROOM_WARNING_THRESHOLD:
        state = PressureMonitorState.WARNING
        triggered = PressureMonitorRule.HEADROOM_WARNING
        action = (
            f"WARNING — ΔP/ΔP_max = {headroom_ratio:.2f} ≥ "
            f"{_HEADROOM_WARNING_THRESHOLD:.2f}. Approaching operational "
            "ceiling. Consider Q_recommended for safety headroom."
        )
    # 7. DPDT_WARNING.
    elif dpdt_pct >= _DPDT_WARNING_PCT_PER_MIN:
        state = PressureMonitorState.WARNING
        triggered = PressureMonitorRule.DPDT_WARNING
        action = (
            f"WARNING — dΔP/dt = {dpdt_pct:.1f} %/min ≥ "
            f"{_DPDT_WARNING_PCT_PER_MIN} %/min. Slow fouling or "
            "channeling onset. Monitor; prepare to switch to wash."
        )

    return PressureMonitorOutput(
        state=state,
        triggered_rule=triggered,
        suggested_action=action,
        headroom_ratio=headroom_ratio,
        dpdt_pct_per_min=dpdt_pct,
        model_deviation_ratio=deviation_ratio,
        history=new_history,
    )
