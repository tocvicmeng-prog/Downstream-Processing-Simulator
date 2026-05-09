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
    if summary.final_state == PressureMonitorState.BLOCKER:
        rule = (
            summary.final_rule.value
            if summary.final_rule is not None
            else "(unknown)"
        )
        container.error(
            f"Final state BLOCKER (rule: `{rule}`). The trace reached an "
            "operational ceiling or a fouling / channeling rule fired."
        )
    elif summary.final_state == PressureMonitorState.WARNING:
        rule = (
            summary.final_rule.value
            if summary.final_rule is not None
            else "(unknown)"
        )
        container.warning(
            f"Final state WARNING (rule: `{rule}`). Trace ended in the "
            "advisory zone — the run is not safe to continue without "
            "operator review."
        )
    else:
        container.success(
            f"Final state OK. Replay stayed within the operational "
            f"envelope across all {summary.n_readings} readings."
        )

    # Trace plot.
    fig = _build_timeline_figure(summary, envelope)
    container.plotly_chart(fig, width="stretch")


__all__ = ["render_pressure_monitor_section"]
