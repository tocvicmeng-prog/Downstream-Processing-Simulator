"""Sticky right-pane composition for Direction A."""

from __future__ import annotations

import html as _html
from collections.abc import Callable, Iterable
from typing import Any, Final

import streamlit as st

from dpsim.visualization.design import chrome
from dpsim.visualization.diff.render import render_diff_panel
from dpsim.visualization.evidence.rollup import (
    StageEvidence,
    render_evidence_summary,
)
from dpsim.visualization.run_rail.history import latest
from dpsim.visualization.run_rail.progress import (
    get_error_msg,
    get_progress,
    get_run_state,
    request_cancel,
    set_progress,
    set_run_state,
)

# The four headline KPIs shown in the Direction-A rail. Order is
# meaningful — left-to-right, top-to-bottom in a 2x2 grid. Per the
# canonical Direction-A reference (DPSim UI Optimization standalone),
# the rail KPIs are column-performance metrics, not M1 fabrication
# outputs. DSD lives in the M1 stage card; the rail tracks the lifecycle
# end-state (DBC₁₀ + Recovery + HETP + ΔP).
_KPI_KEYS: Final[tuple[str, ...]] = ("dbc10", "recovery", "hetp", "dp")
_KPI_LABEL: Final[dict[str, str]] = {
    "dbc10": "DBC₁₀",
    "recovery": "RECOVERY",
    "hetp": "HETP",
    "dp": "ΔP",
}
_KPI_UNIT: Final[dict[str, str]] = {
    "dbc10": "mg/mL",
    "recovery": "%",
    "hetp": "mm",
    "dp": "MPa",
}


def _run_stop_button(*, key: str = "dpsim_run_button") -> None:
    """Render the run/stop button via the v0.4.7 custom component.

    The component owns the visual state machine (idle / running /
    stopping / done / error) and reports clicks via
    ``Streamlit.setComponentValue``. The click triggers a state
    transition + scipy-events-driven cancellation when the run is in
    progress.
    """
    from dpsim.visualization.components import stop_button

    state = get_run_state()
    pct = get_progress()
    err_msg = get_error_msg() if state == "error" else ""

    # Render the component; ``clicked`` is True exactly on the rerun
    # following the user's click.
    result = stop_button(
        run_state=state,
        progress_pct=pct,
        error_message=err_msg,
        key=key,
    )

    if not result.clicked:
        return

    # Click → state-machine transition.
    if state == "running":
        request_cancel()
        st.rerun()
    elif state == "stopping":
        # Disabled in the visual; defensive no-op.
        return
    elif state in ("done", "error"):
        set_run_state("running")
        set_progress(0)
        st.rerun()
    else:  # idle
        set_run_state("running")
        set_progress(0)
        st.rerun()


def _progress_bar() -> None:
    """Render the progress indicator + state caption."""
    state = get_run_state()
    pct = get_progress()
    if state == "running":
        st.progress(pct / 100, text=f"Running · {pct}%")
    elif state == "stopping":
        st.progress(pct / 100, text=f"Stopping at next checkpoint · {pct}%")
    elif state == "done":
        st.html(
            '<div style="font-size:11px;color:var(--dps-green-500);'
            'font-family:var(--dps-font-mono);padding:4px 0;">'
            "✓ Run complete</div>"
        )
    elif state == "error":
        msg = get_error_msg() or "see logs"
        st.html(
            f'<div style="font-size:11px;color:var(--dps-red-600);'
            f'font-family:var(--dps-font-mono);padding:4px 0;">'
            f"⚠ Run failed · {msg}</div>"
        )


def _format_relative_short(seconds: int) -> str:
    """Compact "6 min ago" / "2 h ago" formatter for the rail header."""
    if seconds < 60:
        return f"{seconds}s ago"
    if seconds < 3600:
        return f"{seconds // 60} min ago"
    if seconds < 86400:
        return f"{seconds // 3600} h ago"
    return f"{seconds // 86400} d ago"


def _render_last_run_header() -> None:
    """Direction-A "LAST RUN +#NNN · NN min ago" rail header.

    Renders an eyebrow + recipe name + status pill block above the KPI
    grid. Pulls from ``run_rail.history.latest()``; if no run has been
    appended yet, shows a muted "no run yet" placeholder so the
    structural layout is preserved.
    """
    entry = latest()
    if entry is None:
        st.html(
            chrome.eyebrow("Last run · — no run yet", accent=True)
            + '<div class="dps-mono" style="font-size:11.5px;'
            'color:var(--dps-text-dim);padding:4px 0 8px;">'
            "Run the lifecycle to populate KPIs.</div>"
        )
        return

    from datetime import datetime, timezone

    delta = datetime.now(tz=timezone.utc) - entry.timestamp_utc
    rel = _format_relative_short(int(delta.total_seconds()))
    eyebrow_text = f"Last run · #{entry.run_id} · {rel}"
    state = get_run_state()
    status_label = "complete" if state in ("idle", "done") else state
    status_color = (
        "var(--dps-green-500)"
        if state in ("idle", "done")
        else "var(--dps-amber-500)"
        if state in ("running", "stopping")
        else "var(--dps-red-600)"
    )
    st.html(
        chrome.eyebrow(eyebrow_text, accent=True)
        + '<div style="display:flex;align-items:center;'
        'justify-content:space-between;gap:8px;'
        'margin-top:4px;padding:6px 8px;'
        'background:var(--dps-surface-2);'
        'border:1px solid var(--dps-border);border-radius:4px;">'
        '<span class="dps-mono" style="font-size:12px;'
        f'color:var(--dps-text);">{_html.escape(entry.recipe_name)}</span>'
        + chrome.chip(status_label, color=status_color)
        + '</div>'
    )


def _render_kpi_grid() -> None:
    """Render the 2x2 KPI grid: DSD / RECOVERY / DBC / PURITY.

    Reads metrics from ``run_rail.history.latest().metrics`` (a
    ``dict[str, str]`` populated by ``shell.autowire`` at run
    completion). Missing or absent metrics render as "—" so the grid
    layout is stable regardless of which run output is available.

    Each cell shows: KPI label (caps eyebrow) · big mono value · unit
    suffix · optional delta chip.
    """
    entry = latest()
    metrics: dict[str, str] = dict(entry.metrics) if entry is not None else {}

    def _cell(key: str) -> str:
        label = _KPI_LABEL[key]
        unit = _KPI_UNIT[key]
        raw = metrics.get(key, "")
        delta = metrics.get(f"{key}_delta", "")
        delta_dir_raw = metrics.get(f"{key}_delta_dir", "")
        delta_dir: Any = None
        if delta_dir_raw == "up":
            delta_dir = "up"
        elif delta_dir_raw == "down":
            delta_dir = "down"
        value = raw if raw else "—"
        unit_html = unit if value != "—" else ""
        value_html = chrome.metric_value(
            value=value,
            unit=unit_html,
            delta=delta,
            delta_direction=delta_dir,
            size=22,
        )
        return (
            '<div style="background:var(--dps-surface);'
            'border:1px solid var(--dps-border);border-radius:4px;'
            'padding:8px 10px;display:flex;flex-direction:column;'
            'gap:3px;min-width:0;">'
            '<div class="dps-mono" style="font-size:10px;'
            'letter-spacing:0.12em;text-transform:uppercase;'
            f'color:var(--dps-text-dim);font-weight:600;">{label}</div>'
            f'<div style="display:flex;align-items:baseline;gap:4px;">'
            f'{value_html}</div></div>'
        )

    st.html(
        '<div style="display:grid;'
        'grid-template-columns:1fr 1fr;gap:6px;margin-top:8px;">'
        + "".join(_cell(k) for k in _KPI_KEYS)
        + "</div>"
    )


def render_run_rail(
    *,
    current_recipe: Any | None = None,
    stages: Iterable[StageEvidence] = (),
    breakthrough_curve: Any = None,
    extra_top_section: Callable[[], None] | None = None,
) -> None:
    """Render the sticky run rail into the current Streamlit slot.

    Composition — 4 discrete ``st.container(border=True)`` cards,
    matching the canonical Direction-A reference (RunRail in
    eb686cbe.js):

        Card 1: "Last run · #N" eyebrow + recipe-name title +
                "complete" status chip. Body: 2x2 KPI grid.
        Card 2: "Breakthrough" eyebrow + "C/C₀ vs CV · MC-LRM" title +
                "P05–P95" chip. Body: breakthrough SVG.
        Card 3: "Evidence roll-up" eyebrow + lifecycle-min title +
                EvidenceBadge right. Body: per-stage ladder.
                Omitted entirely when no stages are present.
        Card 4: No eyebrow/title strip — "Pending edits" surface with
                diff panel, then run/stop button + keyboard hint.

    Args:
        current_recipe: Live recipe for diff. ``None`` skips the diff
            panel.
        stages: Per-stage evidence summaries. Empty skips Card 3.
        breakthrough_curve: Optional ``BreakthroughCurve`` from the
            chrome module. ``None`` shows the synthetic placeholder.
        extra_top_section: Optional callable rendered at the bottom of
            the rail (history shortcuts, baseline picker). The name is
            preserved for backward compatibility but its position has
            moved to the foot per the Direction-A reference.
    """
    # Anchor marker so app.py's CSS can apply position: sticky to this
    # column. Renders an empty zero-height div with the marker class.
    st.html('<div class="dps-rail-marker" style="height:0;"></div>')

    # ── Card 1: Last run + KPI grid ───────────────────────────────────
    entry = latest()
    state = get_run_state()
    status_label = "complete" if state in ("idle", "done") else state
    status_color = (
        "var(--dps-green-500)"
        if state in ("idle", "done")
        else "var(--dps-amber-500)"
        if state in ("running", "stopping")
        else "var(--dps-red-600)"
    )
    if entry is not None:
        from datetime import datetime, timezone

        delta = datetime.now(tz=timezone.utc) - entry.timestamp_utc
        rel = _format_relative_short(int(delta.total_seconds()))
        card1_eyebrow = f"Last run · #{entry.run_id} · {rel}"
        card1_title = entry.recipe_name
    else:
        card1_eyebrow = "Last run · —"
        card1_title = "No run yet"

    with st.container(border=True):
        st.html(
            chrome.card_header_strip(
                eyebrow_text=card1_eyebrow,
                title=card1_title,
                right_html=chrome.chip(status_label, color=status_color),
            )
        )
        _render_kpi_grid()

    # ── Card 2: Breakthrough preview ─────────────────────────────────
    with st.container(border=True):
        st.html(
            chrome.card_header_strip(
                eyebrow_text="Breakthrough",
                title="C/C₀ vs CV · MC-LRM",
                right_html=chrome.chip("P05–P95"),
            )
        )
        st.html(
            '<div style="padding:4px 0;">'
            + chrome.breakthrough(
                curve=breakthrough_curve, width=320, height=86
            )
            + "</div>"
        )

    # ── Card 3: Evidence roll-up ─────────────────────────────────────
    # v0.4.19 (A5): always render — pre-run shows a placeholder ladder
    # with M1/M2/M3 at "unsupported" tier so the rail layout matches the
    # canonical Direction-A reference at every state. The previous
    # "skip when empty" branch made the rail collapse vertically before
    # any run, which the standalone reference does not do.
    from dpsim.visualization.evidence.rollup import aggregate_min_tier
    from dpsim.visualization.evidence import StageEvidence as _StageEv
    stages_list = list(stages)
    if stages_list:
        min_tier = aggregate_min_tier(stages_list)
        ladder_stages = stages_list
    else:
        min_tier = "unsupported"
        ladder_stages = [
            _StageEv(stage_id="m1", label="M1", tier="unsupported"),
            _StageEv(stage_id="m2", label="M2", tier="unsupported"),
            _StageEv(stage_id="m3", label="M3", tier="unsupported"),
        ]
    tier_short = min_tier.upper().split("_")[0]
    with st.container(border=True):
        st.html(
            chrome.card_header_strip(
                eyebrow_text="Evidence roll-up",
                title=(
                    f"Lifecycle min: {tier_short}"
                    if stages_list
                    else "No run yet"
                ),
                right_html=chrome.evidence_badge(min_tier, compact=True),
            )
        )
        render_evidence_summary(ladder_stages)

    # ── Card 4: Pending edits + run/stop CTA ─────────────────────────
    with st.container(border=True):
        # Compute pending-edits count for the eyebrow chip
        if current_recipe is not None:
            baseline_name = st.session_state.get(
                "_dpsim_diff_baseline_name", "last_run"
            )
            st.html(
                chrome.card_header_strip(
                    eyebrow_text="Pending edits",
                )
            )
            render_diff_panel(
                current_recipe=current_recipe,
                baseline_name=baseline_name,
            )
        else:
            st.html(
                chrome.card_header_strip(
                    eyebrow_text="Re-run lifecycle",
                )
            )
        _run_stop_button()
        _progress_bar()
        st.html(
            '<div class="dps-mono" style="font-size:10.5px;'
            "color:var(--dps-text-dim);text-align:center;"
            'padding-top:4px;">'
            "↵ Enter to run · Esc to cancel</div>"
        )

    # Optional rail extras (history dropdown, baseline picker) —
    # tucked under a collapsed expander so they don't clutter the
    # primary state surfaces above.
    if extra_top_section is not None:
        with st.expander("Run history & baselines", expanded=False):
            extra_top_section()
