"""Streaming pressure-monitor UI section (offline replay).

B-2i / W-032 — v0.8.0 streaming-UI epic. Renders a Streamlit section
that lets the operator upload a CSV pressure trace from a previous
run and replay it through
:func:`dpsim.module3_performance.pressure_monitor.evaluate_pressure_trace`
against the active recipe step's pre-flight envelope.

The section is rendered after the pre-flight envelope panel in
``tab_m3.py``. It is *offline only* — the live AKTA UNICORN bridge is
a v0.9 epic.

Visual layout
-------------
1. Compact CSV-format help line + file uploader.
2. After upload: replay-summary metrics row (n readings, final state,
   first BLOCKER time, max headroom, max dΔP/dt).
3. Status timeline plot — the per-reading state shown as colored bars
   over time, plus the ΔP trace overlaid against the operational and
   warning thresholds.
4. Downloadable example CSV button so first-time users have something
   to start from.
"""

from __future__ import annotations

from io import StringIO
from typing import Any, Optional

import numpy as np
import plotly.graph_objects as go

from dpsim.module3_performance.pressure_envelope import PressureEnvelope
from dpsim.module3_performance.pressure_monitor import PressureMonitorState
from dpsim.module3_performance.pressure_monitor_replay import (
    ReplaySummary,
    parse_csv,
    replay,
)


_STATE_COLORS: dict[str, str] = {
    PressureMonitorState.OK.value: "#10B981",       # green-500
    PressureMonitorState.WARNING.value: "#F59E0B",  # amber-500
    PressureMonitorState.BLOCKER.value: "#EF4444",  # red-500
}


# B-2ℓ / W-041 (v0.8.2): operator-facing labels for RecoveryAction.
_RECOVERY_ACTION_LABEL: dict[str, str] = {
    "none": "no action",
    "continue_monitor": "continue & monitor",
    "reduce_flow": "reduce flow to Q_recommended",
    "switch_to_wash": "switch to wash buffer",
    "stop_and_repack": "stop & repack column",
    "emergency_stop": "EMERGENCY STOP",
    "operator_review": "operator review (fouling-suggestive)",
}

_EXAMPLE_CSV: str = (
    "t_s,dP_pa,Q_m3_s\n"
    "0,40000,1.0e-7\n"
    "30,42000,1.0e-7\n"
    "60,43500,1.0e-7\n"
    "90,45000,1.0e-7\n"
    "120,47000,1.0e-7\n"
    "150,49500,1.0e-7\n"
    "180,52000,1.0e-7\n"
    "210,55000,1.0e-7\n"
    "240,58500,1.0e-7\n"
)


def _build_timeline_figure(
    summary: ReplaySummary,
    envelope: PressureEnvelope,
) -> go.Figure:
    """Compose the ΔP trace + state-chip ribbon Plotly figure."""
    times = np.array([r.t_s for r in summary.history], dtype=float)
    dps = np.array([r.dP_pa for r in summary.history], dtype=float)

    fig = go.Figure()

    # ΔP trace.
    fig.add_trace(
        go.Scatter(
            x=times,
            y=dps / 1.0e3,
            mode="lines+markers",
            name="ΔP measured",
            line=dict(color="#0EA5E9", width=2),
        )
    )

    # Operational ceiling (red dashed).
    fig.add_hline(
        y=envelope.dP_max_operational_pa / 1.0e3,
        line_dash="dash",
        line_color="#EF4444",
        annotation_text="ΔP_max operational",
        annotation_position="top right",
    )

    # 70 % warning threshold.
    fig.add_hline(
        y=0.70 * envelope.dP_max_operational_pa / 1.0e3,
        line_dash="dot",
        line_color="#F59E0B",
        annotation_text="70 % headroom",
        annotation_position="top left",
    )

    # State-chip ribbon along the bottom (markers colored by state).
    if summary.state_timeline:
        ts = np.array([t for t, _, _ in summary.state_timeline], dtype=float)
        states = [s for _, s, _ in summary.state_timeline]
        colors = [_STATE_COLORS.get(s, "#9CA3AF") for s in states]
        fig.add_trace(
            go.Scatter(
                x=ts,
                y=np.zeros_like(ts),
                mode="markers",
                name="state",
                marker=dict(size=12, color=colors, symbol="square"),
                hovertext=states,
                hoverinfo="x+text",
                showlegend=False,
            )
        )

    fig.update_layout(
        title="Pressure trace — replay vs. operational envelope",
        xaxis_title="Time (s)",
        yaxis_title="ΔP (kPa)",
        height=380,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
        ),
    )
    return fig


def _format_seconds(seconds: Optional[float]) -> str:
    if seconds is None:
        return "—"
    if seconds < 60.0:
        return f"{seconds:.0f} s"
    if seconds < 3600.0:
        return f"{seconds/60.0:.1f} min"
    return f"{seconds/3600.0:.2f} h"


def render_pressure_monitor_section(
    *,
    envelope: PressureEnvelope,
    container: Any,
) -> None:
    """Render the streaming pressure-monitor UI section.

    Pure presentation. The function reads from Streamlit's session
    state for the uploaded CSV bytes (so the upload survives reruns)
    and writes nothing back. Errors during parsing or replay surface
    as ``st.error`` messages without raising.

    Parameters
    ----------
    envelope :
        The active recipe step's pre-flight envelope. Used as the
        reference for headroom / model-deviation evaluation.
    container :
        Streamlit container (typically the module-level ``st`` or a
        column from ``st.columns``). Bypassed during unit tests by
        passing a stub object that exposes the same method names —
        see ``tests/visualization/test_tab_m3_monitor.py``.
    """
    container.subheader("Streaming pressure monitor (offline replay)")
    container.caption(
        "Upload a CSV pressure trace from a prior run to replay it "
        "against the active envelope. The function ships v0.8 — live "
        "AKTA UNICORN integration is a v0.9 epic. Accepted columns: "
        "`t_s` (or `t_min`), `dP_pa` (or `dP_kpa` / `dP_mpa` / `dP_bar`), "
        "`Q_m3_s` (or `Q_mL_min`)."
    )

    container.download_button(
        label="Download example trace.csv",
        data=_EXAMPLE_CSV,
        file_name="pressure_trace_example.csv",
        mime="text/csv",
        key="pressure_monitor_example_download",
    )

    uploaded = container.file_uploader(
        label="Upload pressure trace CSV",
        type=["csv"],
        key="pressure_monitor_csv_upload",
    )
    if uploaded is None:
        container.info(
            "No trace uploaded yet. The example CSV above shows the "
            "expected format and a comfortable smooth-flow trace."
        )
        return

    # Decode the uploaded bytes to text.
    try:
        text = uploaded.getvalue().decode("utf-8")
    except (UnicodeDecodeError, AttributeError) as exc:
        container.error(f"Could not decode uploaded file as UTF-8: {exc!r}")
        return

    try:
        readings = parse_csv(StringIO(text))
    except ValueError as exc:
        container.error(f"CSV parse failed: {exc}")
        return

    try:
        summary = replay(readings, envelope)
    except (ValueError, ZeroDivisionError) as exc:
        container.error(f"Replay failed: {exc}")
        return

    # Summary metrics row.
    cols = container.columns(5)
    cols[0].metric("Readings", f"{summary.n_readings}")
    cols[1].metric(
        "Final state",
        summary.final_state.value.upper(),
    )
    cols[2].metric(
        "First BLOCKER",
        _format_seconds(summary.blocker_first_t_s),
        help=(
            f"Rule: {summary.blocker_first_rule.value}"
            if summary.blocker_first_rule is not None
            else "No BLOCKER tripped during the trace."
        ),
    )
    cols[3].metric(
        "Max headroom",
        f"{summary.max_headroom_ratio*100:.0f} %",
        help="Peak ΔP / ΔP_max_operational across the replay.",
    )
    cols[4].metric(
        "Max dΔP/dt",
        f"{summary.max_dpdt_pct_per_min:.1f} %/min",
        help="Peak rate-of-rise across the replay.",
    )

    # Final-state advisory chip.
    # B-2ℓ / W-041: structured recovery-action chip alongside the
    # legacy advisory message.
    action_label = _RECOVERY_ACTION_LABEL.get(
        summary.final_recovery_action.value,
        summary.final_recovery_action.value.replace("_", " ").title(),
    )

    if summary.final_state == PressureMonitorState.BLOCKER:
        rule = (
            summary.final_rule.value
            if summary.final_rule is not None
            else "(unknown)"
        )
        container.error(
            f"Final state BLOCKER (rule: `{rule}`, action: **{action_label}**). "
            "The trace reached an operational ceiling or a fouling / "
            "channeling rule fired."
        )
    elif summary.final_state == PressureMonitorState.WARNING:
        rule = (
            summary.final_rule.value
            if summary.final_rule is not None
            else "(unknown)"
        )
        container.warning(
            f"Final state WARNING (rule: `{rule}`, action: **{action_label}**). "
            "Trace ended in the advisory zone — the run is not safe to "
            "continue without operator review."
        )
    else:
        container.success(
            f"Final state OK (action: **{action_label}**). Replay stayed "
            f"within the operational envelope across all "
            f"{summary.n_readings} readings."
        )

    # Trace plot.
    fig = _build_timeline_figure(summary, envelope)
    container.plotly_chart(fig, width="stretch")

    # B-2u / W-062 (v0.8.4): per-rule RecoveryAction timeline. Surfaces
    # the seven-rule taxonomy historically (which rule fired at which
    # timestamp) so the operator can audit the run, not just see the
    # final state.
    _render_recovery_action_timeline(container=container, summary=summary)


def _render_recovery_action_timeline(
    *,
    container: Any,
    summary: ReplaySummary,
) -> None:
    """Per-reading state-chip + triggered-rule timeline ribbon.

    B-2u / W-062 (v0.8.4). The streaming monitor's `state_timeline`
    already carries (t_s, state.value, rule.value or None) tuples; this
    helper renders them as a horizontal scatter strip below the ΔP
    trace plot so the operator can see *which* rule fired at *which*
    timestamp during replay. Hover-text shows the triggered rule.
    """
    if not summary.state_timeline:
        return
    container.markdown("**Per-rule action timeline**")
    container.caption(
        "Hover any chip for the triggered rule + recovery action. "
        "Chips below the time axis show the state machine's history."
    )
    times = np.array([t for t, _, _ in summary.state_timeline], dtype=float)
    states = [s for _, s, _ in summary.state_timeline]
    rules = [r for _, _, r in summary.state_timeline]
    colors = [_STATE_COLORS.get(s, "#9CA3AF") for s in states]

    # Build per-chip hover text mapping rule → recovery action label.
    from dpsim.module3_performance.pressure_monitor import _RULE_TO_ACTION
    hover: list[str] = []
    for s, r in zip(states, rules):
        if r is None:
            hover.append(f"{s.upper()} — no rule fired")
        else:
            try:
                from dpsim.module3_performance.pressure_monitor import (
                    PressureMonitorRule,
                )
                action = _RULE_TO_ACTION[PressureMonitorRule(r)]
                action_label = _RECOVERY_ACTION_LABEL.get(
                    action.value, action.value,
                )
            except (KeyError, ValueError):
                action_label = "(unknown action)"
            hover.append(f"{s.upper()} — rule={r}; action={action_label}")

    fig_timeline = go.Figure()
    fig_timeline.add_trace(
        go.Scatter(
            x=times,
            y=np.zeros_like(times),
            mode="markers",
            marker=dict(size=14, color=colors, symbol="square"),
            hovertext=hover,
            hoverinfo="x+text",
            showlegend=False,
        )
    )
    fig_timeline.update_layout(
        title=None,
        xaxis_title="Time (s)",
        yaxis=dict(visible=False, range=[-1, 1]),
        height=120,
        margin=dict(l=10, r=10, t=10, b=30),
    )
    container.plotly_chart(fig_timeline, width="stretch")

    # Per-rule histogram below the chip strip — counts of each
    # triggered-rule occurrence across the replay.
    rule_counts: dict[str, int] = {}
    for r in rules:
        if r is None:
            continue
        rule_counts[r] = rule_counts.get(r, 0) + 1
    if rule_counts:
        with container.expander(
            f"Rule frequency ({sum(rule_counts.values())} total triggers)"
        ):
            for rule_name, count in sorted(
                rule_counts.items(), key=lambda kv: kv[1], reverse=True,
            ):
                try:
                    from dpsim.module3_performance.pressure_monitor import (
                        PressureMonitorRule,
                    )
                    action = _RULE_TO_ACTION[PressureMonitorRule(rule_name)]
                    action_label = _RECOVERY_ACTION_LABEL.get(
                        action.value, action.value,
                    )
                except (KeyError, ValueError):
                    action_label = "(unknown action)"
                container.write(
                    f"• `{rule_name}` ×{count} → action: **{action_label}**"
                )


__all__ = ["render_pressure_monitor_section"]
