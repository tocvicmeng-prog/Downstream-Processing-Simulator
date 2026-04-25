"""Render a recipe-diff panel as ``path · prev → next`` lines."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import streamlit as st

from dpsim.visualization.design import chrome
from dpsim.visualization.diff.snapshot import (
    ABSENT_LABEL,
    SNAPSHOT_KEY,
    DiffEntry,
    diff_recipes,
)


def _format_value(value: Any) -> str:
    """Format a leaf value for display, including the ``(absent)`` sentinel.

    Floats are formatted with up to 4 significant figures so the diff
    stays readable when, e.g., a slider edits 4.0 → 4.000001 due to
    float round-trip noise. The threshold for "really changed" is left
    to the caller; this function is purely display.
    """
    if value is None:
        return "—"
    # Sentinel comes through as the literal _ABSENT object; check by repr.
    if repr(value).startswith("<object object at "):
        return ABSENT_LABEL
    if isinstance(value, float):
        if abs(value) < 1e-4 or abs(value) > 1e6:
            return f"{value:.4g}"
        return f"{value:.4g}"
    if isinstance(value, str):
        return value if len(value) <= 36 else value[:33] + "…"
    return str(value)


def render_diff_panel(
    *,
    current_recipe: Any,
    title: str = "Pending edits vs last run",
    baseline_name: str = "last_run",
) -> int:
    """Render the recipe-diff panel into the current Streamlit slot.

    Args:
        current_recipe: The live ``ProcessRecipe`` (or any
            ``snapshot_recipe``-compatible object).
        title: Panel title (eyebrow text).
        baseline_name: Diff target. ``"last_run"`` (default) uses the
            v0.4.0 ``SNAPSHOT_KEY`` snapshot; any other name resolves
            to a tagged baseline via ``diff.baselines.get_baseline``.

    Returns:
        Number of diff entries shown.
    """
    if baseline_name == "last_run":
        snapshot = st.session_state.get(SNAPSHOT_KEY)
    else:
        from dpsim.visualization.diff.baselines import get_baseline
        baseline = get_baseline(baseline_name)
        snapshot = baseline.snapshot if baseline is not None else None
        if snapshot is not None:
            title = f"Pending edits vs {baseline_name}"
    if snapshot is None:
        st.html(
            chrome.eyebrow(title)
            + '<div style="margin-top:6px;font-size:11.5px;'
            'color:var(--dps-text-dim);font-family:var(--dps-font-mono);">'
            "no baseline yet — run the lifecycle once to enable diff"
            "</div>"
        )
        return 0

    entries = diff_recipes(snapshot, current_recipe)
    if not entries:
        st.html(
            chrome.eyebrow(title)
            + '<div style="margin-top:6px;font-size:11.5px;'
            'color:var(--dps-text-dim);font-family:var(--dps-font-mono);">'
            "no pending edits"
            "</div>"
        )
        return 0

    rows = "".join(_format_row(e) for e in entries)
    st.html(
        chrome.eyebrow(title, accent=True)
        + f'<div style="margin-top:6px;display:flex;flex-direction:column;'
        f'gap:3px;font-family:var(--dps-font-mono);font-size:11px;'
        f'line-height:1.5;">{rows}</div>'
    )
    return len(entries)


def _format_row(entry: DiffEntry) -> str:
    prev_s = _format_value(entry.prev)
    next_s = _format_value(entry.next)
    return (
        f'<div style="display:flex;gap:6px;align-items:baseline;">'
        f'<span style="color:var(--dps-text-dim);">{entry.path}</span>'
        f'<span style="color:var(--dps-text-dim);">·</span>'
        f'<span style="color:var(--dps-red-600);text-decoration:line-through;'
        f'opacity:0.7;">{prev_s}</span>'
        f'<span style="color:var(--dps-text-dim);">→</span>'
        f'<span style="color:var(--dps-green-500);">{next_s}</span>'
        f"</div>"
    )


def render_diff_summary_chip(*, current_recipe: Any) -> str:
    """Compact one-line summary, returns chip HTML for inline use.

    Used by the top-bar "modified" indicator. Returns an empty string if
    no baseline exists or no diffs are pending.
    """
    snapshot = st.session_state.get(SNAPSHOT_KEY)
    if snapshot is None:
        return ""
    entries = diff_recipes(snapshot, current_recipe)
    if not entries:
        return ""
    n = len(entries)
    label = f"{n} edit" if n == 1 else f"{n} edits"
    return chrome.chip(label, color="var(--dps-amber-500)")


# Convenience: capture a snapshot at run-end. Called by run_rail when a run completes.
def capture_snapshot(recipe: Any) -> None:
    """Snapshot the recipe into ``st.session_state[SNAPSHOT_KEY]``.

    Call this from the run-rail's "run completed" handler, never on
    every render — the snapshot is the *post-run* baseline against
    which future edits are diffed.
    """
    from dpsim.visualization.diff.snapshot import snapshot_recipe as _snap

    st.session_state[SNAPSHOT_KEY] = _snap(recipe)


def diff_entries(current_recipe: Any) -> Sequence[DiffEntry]:
    """Get the list of ``DiffEntry`` records without rendering.

    Useful for the run-rail to gate its "you have N pending edits"
    indicator on whether the diff is empty.
    """
    snapshot = st.session_state.get(SNAPSHOT_KEY)
    return diff_recipes(snapshot, current_recipe)
