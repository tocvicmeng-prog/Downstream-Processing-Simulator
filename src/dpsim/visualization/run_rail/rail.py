"""Sticky right-pane composition for Direction A."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

import streamlit as st

from dpsim.visualization.design import chrome
from dpsim.visualization.diff.render import render_diff_panel
from dpsim.visualization.evidence.rollup import (
    StageEvidence,
    render_evidence_summary,
)
from dpsim.visualization.run_rail.progress import (
    get_error_msg,
    get_progress,
    get_run_state,
    request_cancel,
    set_progress,
    set_run_state,
)


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


def render_run_rail(
    *,
    current_recipe: Any | None = None,
    stages: Iterable[StageEvidence] = (),
    breakthrough_curve: Any = None,
    extra_top_section: Callable[[], None] | None = None,
) -> None:
    """Render the sticky run rail into the current Streamlit slot.

    Composition (top → bottom):
        1. Run / Stop button + progress
        2. Breakthrough preview (P05/P50/P95 envelope)
        3. Evidence rollup (lifecycle min + per-stage)
        4. Recipe diff vs last successful run

    Args:
        current_recipe: Live recipe for diff. ``None`` skips the diff
            panel.
        stages: Per-stage evidence summaries. Empty skips the rollup.
        breakthrough_curve: Optional ``BreakthroughCurve`` from the
            chrome module. ``None`` shows the synthetic placeholder.
        extra_top_section: Optional callable rendered between the run
            controls and the breakthrough preview. Use for surfacing
            run-history shortcuts or other rail-scoped extras.
    """
    # Anchor marker so app.py's CSS can apply position: sticky to this
    # column. Renders an empty zero-height div with the marker class.
    st.html('<div class="dps-rail-marker" style="height:0;"></div>')

    # Top: run controls
    st.html(chrome.eyebrow("Run controls", accent=True))
    _run_stop_button()
    _progress_bar()

    if extra_top_section is not None:
        extra_top_section()

    st.html('<div class="dps-divider" style="margin:12px 0;"></div>')

    # Breakthrough preview
    st.html(chrome.eyebrow("Breakthrough · P05 / P50 / P95"))
    st.html(
        '<div style="margin-top:4px;padding:8px;'
        'background:var(--dps-surface-2);'
        'border:1px solid var(--dps-border);border-radius:4px;">'
        + chrome.breakthrough(curve=breakthrough_curve, width=320, height=86)
        + '</div>'
    )

    st.html('<div class="dps-divider" style="margin:12px 0;"></div>')

    # Evidence rollup
    if list(stages):
        render_evidence_summary(stages)
        st.html('<div class="dps-divider" style="margin:12px 0;"></div>')

    # Recipe diff — honour the active baseline name from session state,
    # so the named-baseline picker actually drives the diff target.
    if current_recipe is not None:
        baseline_name = st.session_state.get(
            "_dpsim_diff_baseline_name", "last_run"
        )
        render_diff_panel(
            current_recipe=current_recipe,
            baseline_name=baseline_name,
        )
