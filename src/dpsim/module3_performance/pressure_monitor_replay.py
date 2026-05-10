"""CSV-replay helper for the streaming pressure monitor.

B-2i / W-032 — v0.8.0 streaming-UI epic. Companion to
:mod:`dpsim.module3_performance.pressure_monitor`. Where
``evaluate_pressure_trace`` evaluates a single live reading, this
module provides the offline replay path: parse a CSV trace, replay
it through ``evaluate_pressure_trace`` step-by-step, and produce a
summary suitable for UI display or training-mode validation.

CSV format (canonical SI columns)
---------------------------------
The CSV must have a header row with at least these three columns:

* ``t_s``      — time since run start [s]
* ``dP_pa``    — column ΔP [Pa]
* ``Q_m3_s``   — volumetric flow rate [m³/s]

Extra columns are ignored. ``parse_csv`` also accepts a small set of
common AKTA-style aliases; see :func:`parse_csv` for the mapping.

Live-hardware integration (AKTA UNICORN, real-time WebSocket) is a
v0.9 epic; v0.8 ships only the offline-replay path.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from io import StringIO
from typing import Optional, Union

from dpsim.module3_performance.pressure_envelope import PressureEnvelope
from dpsim.module3_performance.pressure_monitor import (
    PressureMonitorOutput,
    PressureMonitorReading,
    PressureMonitorRule,
    PressureMonitorState,
    RecoveryAction,
    evaluate_pressure_trace,
)


# ─── Column-name aliases ────────────────────────────────────────────────────


_TIME_ALIASES: tuple[tuple[str, float], ...] = (
    ("t_s", 1.0),
    ("time_s", 1.0),
    ("time(s)", 1.0),
    ("time", 1.0),
    ("t_min", 60.0),
    ("time_min", 60.0),
    ("time(min)", 60.0),
)

_DP_ALIASES: tuple[tuple[str, float], ...] = (
    ("dP_pa", 1.0),
    ("dp_pa", 1.0),
    ("delta_p_pa", 1.0),
    ("dP_kpa", 1.0e3),
    ("dp_kpa", 1.0e3),
    ("dP_mpa", 1.0e6),
    ("dp_mpa", 1.0e6),
    ("dP_bar", 1.0e5),
    ("dp_bar", 1.0e5),
    ("pressure_pa", 1.0),
    ("pressure_kpa", 1.0e3),
    ("pressure_mpa", 1.0e6),
    ("pressure_bar", 1.0e5),
)

_Q_ALIASES: tuple[tuple[str, float], ...] = (
    ("Q_m3_s", 1.0),
    ("q_m3_s", 1.0),
    ("flow_m3_s", 1.0),
    # mL/min → m³/s : divide by 60e6
    ("Q_mL_min", 1.0 / 60.0e6),
    ("q_ml_min", 1.0 / 60.0e6),
    ("flow_ml_min", 1.0 / 60.0e6),
    ("flow_mlmin", 1.0 / 60.0e6),
    ("Q_mlmin", 1.0 / 60.0e6),
)


def _resolve_column(
    fieldnames: list[str],
    aliases: tuple[tuple[str, float], ...],
) -> tuple[str, float]:
    lower_map = {fn.strip().lower(): fn for fn in fieldnames}
    for alias, scale in aliases:
        if alias.lower() in lower_map:
            return lower_map[alias.lower()], scale
    raise ValueError(
        f"None of the expected column names {[a for a, _ in aliases]!r} "
        f"were found in the CSV header. Got: {fieldnames!r}."
    )


# ─── Parsing ────────────────────────────────────────────────────────────────


def parse_csv(
    source: Union[str, StringIO],
) -> tuple[PressureMonitorReading, ...]:
    """Parse a pressure-trace CSV into a tuple of readings.

    Accepts either a path-like string (treated as a file path) or an
    in-memory StringIO buffer (used by the Streamlit uploader).

    The header is required; column names are matched case-insensitively
    against :data:`_TIME_ALIASES`, :data:`_DP_ALIASES`, :data:`_Q_ALIASES`,
    with each alias carrying its own SI conversion factor.

    Rows whose time/ΔP/Q cells fail to parse as floats are skipped with
    no error raised (a one-line log is emitted at DEBUG). Rows where ΔP
    is negative are also skipped — chromatography panels never read
    negative ΔP under normal operation.

    Returns
    -------
    tuple[PressureMonitorReading, ...]
        Readings sorted by ascending ``t_s``.

    Raises
    ------
    ValueError
        If the header is missing required columns, or no rows were
        parseable.
    """
    if isinstance(source, str):
        with open(source, encoding="utf-8") as handle:
            text = handle.read()
    else:
        text = source.getvalue() if hasattr(source, "getvalue") else source.read()

    reader = csv.DictReader(StringIO(text))
    if reader.fieldnames is None:
        raise ValueError("CSV is empty or missing a header row.")

    t_col, t_scale = _resolve_column(list(reader.fieldnames), _TIME_ALIASES)
    dp_col, dp_scale = _resolve_column(list(reader.fieldnames), _DP_ALIASES)
    q_col, q_scale = _resolve_column(list(reader.fieldnames), _Q_ALIASES)

    readings: list[PressureMonitorReading] = []
    for row in reader:
        try:
            t_s = float(row[t_col]) * t_scale
            dp_pa = float(row[dp_col]) * dp_scale
            q_m3_s = float(row[q_col]) * q_scale
        except (TypeError, ValueError):
            continue
        if dp_pa < 0.0:
            continue
        readings.append(
            PressureMonitorReading(t_s=t_s, dP_pa=dp_pa, Q_m3_s=q_m3_s)
        )

    if not readings:
        raise ValueError("CSV contained no parseable readings.")

    readings.sort(key=lambda r: r.t_s)
    return tuple(readings)


# ─── Replay ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ReplaySummary:
    """Summary of a complete replay through ``evaluate_pressure_trace``.

    Attributes
    ----------
    final_state :
        Monitor state at the last reading.
    final_rule :
        Rule that drove the final state (``None`` on OK).
    n_readings :
        Total readings replayed.
    blocker_first_t_s :
        Time of the first BLOCKER transition (``None`` if never).
    blocker_first_rule :
        Rule that produced the first BLOCKER (``None`` if never).
    warning_first_t_s :
        Time of the first WARNING transition (``None`` if never).
    max_headroom_ratio :
        Maximum ΔP / ΔP_max_operational across the replay.
    max_dpdt_pct_per_min :
        Maximum dΔP/dt across the replay.
    history :
        Accumulated reading history at the end of the replay (immutable).
    state_timeline :
        Per-reading (t_s, state, triggered_rule) so the UI can draw
        a status-chip ribbon. Each entry is ``(t_s, state.value,
        rule.value or None)``.
    """

    final_state: PressureMonitorState
    final_rule: Optional[PressureMonitorRule]
    n_readings: int
    blocker_first_t_s: Optional[float]
    blocker_first_rule: Optional[PressureMonitorRule]
    warning_first_t_s: Optional[float]
    max_headroom_ratio: float
    max_dpdt_pct_per_min: float
    history: tuple[PressureMonitorReading, ...]
    state_timeline: tuple[tuple[float, str, Optional[str]], ...]
    final_recovery_action: RecoveryAction = RecoveryAction.NONE


def replay(
    readings: tuple[PressureMonitorReading, ...],
    envelope: PressureEnvelope,
    *,
    history_max_seconds: float = 300.0,
    warning_dwell_seconds: float = 30.0,
) -> ReplaySummary:
    """Replay a reading sequence through ``evaluate_pressure_trace``.

    Threads the immutable history through each call and accumulates the
    state-timeline + diagnostic maxima for UI display.

    Parameters
    ----------
    readings :
        Pre-parsed reading tuple from :func:`parse_csv`.
    envelope :
        Pre-flight envelope from
        ``compute_pressure_envelope`` (one envelope used across the
        whole replay; the v0.8 UI replays one recipe step at a time).
    history_max_seconds, warning_dwell_seconds :
        Forwarded to :func:`evaluate_pressure_trace`.

    Returns
    -------
    ReplaySummary
        Final state, first-blocker / first-warning anchors, max
        ratios, and the per-reading state timeline.

    Raises
    ------
    ValueError
        If ``readings`` is empty.
    """
    if not readings:
        raise ValueError("readings must contain at least one reading.")

    history: tuple[PressureMonitorReading, ...] = ()
    blocker_first_t: Optional[float] = None
    blocker_first_rule: Optional[PressureMonitorRule] = None
    warning_first_t: Optional[float] = None
    max_headroom = 0.0
    max_dpdt = 0.0
    timeline: list[tuple[float, str, Optional[str]]] = []
    output: PressureMonitorOutput

    for r in readings:
        output = evaluate_pressure_trace(
            reading=r,
            envelope=envelope,
            history=history,
            history_max_seconds=history_max_seconds,
            warning_dwell_seconds=warning_dwell_seconds,
        )
        history = output.history
        if output.headroom_ratio > max_headroom:
            max_headroom = output.headroom_ratio
        if output.dpdt_pct_per_min > max_dpdt:
            max_dpdt = output.dpdt_pct_per_min
        if (
            blocker_first_t is None
            and output.state == PressureMonitorState.BLOCKER
        ):
            blocker_first_t = r.t_s
            blocker_first_rule = output.triggered_rule
        if (
            warning_first_t is None
            and output.state in (
                PressureMonitorState.WARNING,
                PressureMonitorState.BLOCKER,
            )
        ):
            warning_first_t = r.t_s
        timeline.append(
            (
                r.t_s,
                output.state.value,
                output.triggered_rule.value if output.triggered_rule else None,
            )
        )

    return ReplaySummary(
        final_state=output.state,
        final_rule=output.triggered_rule,
        n_readings=len(readings),
        blocker_first_t_s=blocker_first_t,
        blocker_first_rule=blocker_first_rule,
        warning_first_t_s=warning_first_t,
        max_headroom_ratio=max_headroom,
        max_dpdt_pct_per_min=max_dpdt,
        history=history,
        state_timeline=tuple(timeline),
        final_recovery_action=output.recovery_action,
    )


__all__ = [
    "ReplaySummary",
    "parse_csv",
    "replay",
]
