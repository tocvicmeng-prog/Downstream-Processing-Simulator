"""Stop button — declare_component-based Streamlit Custom Component.

Replaces ``st.button("■ Stop run", ...)`` with a real custom component
that:

1. Renders a teal "▶ Run lifecycle" / orange "■ Stop run" / dim
   "■ Stopping…" / red "↻ Try again" button keyed on the current
   run state.
2. Sends a click event back to Python via
   ``Streamlit.setComponentValue(...)`` — same delivery semantics as
   ``st.button`` returning ``True``.
3. Displays a sub-second click animation that stays in sync with the
   visual state, even between Streamlit reruns (the previous
   ``st.button`` flickered briefly during reruns).

The bidirectional plumbing is what makes this a "real" custom component
rather than a one-way iframe: the component writes a value, Python
reads it on the next rerun.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

import streamlit.components.v1 as components

_ASSET_DIR: Final[Path] = Path(__file__).parents[1] / "assets" / "stop_button"

# `declare_component` returns a callable that, when invoked, renders
# the component and returns its current value. Cached at module import
# so the iframe is registered exactly once per Streamlit session.
_stop_button_component = components.declare_component(
    "dpsim_stop_button",
    path=str(_ASSET_DIR),
)


RunStateLiteral = Literal["idle", "running", "stopping", "done", "error"]


@dataclass(frozen=True)
class StopButtonState:
    """Decoded component value.

    Attributes:
        clicked: Whether the user clicked the button this rerun cycle.
        click_count: Monotonic click counter — useful when the same
            visual state has been seen across multiple reruns.
    """

    clicked: bool
    click_count: int


def stop_button(
    *,
    run_state: RunStateLiteral = "idle",
    progress_pct: int = 0,
    error_message: str = "",
    height: int = 80,
    key: str = "dpsim_stop_button",
) -> StopButtonState:
    """Render the stop button and return its click state.

    Args:
        run_state: Current run state. Drives label + colour:
            ``idle`` → teal "▶ Run lifecycle".
            ``running`` → orange "■ Stop run" with a subtle pulse.
            ``stopping`` → dim "■ Stopping…" (disabled).
            ``done`` → teal "↻ Re-run".
            ``error`` → red "↻ Try again".
        progress_pct: 0–100. Drawn as a thin progress bar at the
            bottom of the button when ``run_state == "running"``.
        error_message: Shown beneath the button when
            ``run_state == "error"``. Empty string suppresses.
        height: Iframe height in px. Default 80 fits the rail.
        key: Streamlit widget key. Should be unique per render.

    Returns:
        ``StopButtonState`` with ``clicked=True`` exactly on the rerun
        that follows the user's click; ``False`` on every other rerun.
    """
    raw = _stop_button_component(
        runState=run_state,
        progressPct=int(progress_pct),
        errorMessage=str(error_message),
        height=int(height),
        default={"click_count": 0},
        key=key,
    )
    if raw is None:
        return StopButtonState(clicked=False, click_count=0)
    click_count = int(raw.get("click_count", 0))
    # Streamlit delivers the component value verbatim across reruns;
    # we detect a "fresh click" by comparing against the previous count.
    import streamlit as st

    last_seen_key = f"_dpsim_stop_button_last_count_{key}"
    last_seen = int(st.session_state.get(last_seen_key, 0))
    clicked = click_count > last_seen
    if clicked:
        st.session_state[last_seen_key] = click_count
    return StopButtonState(clicked=clicked, click_count=click_count)
