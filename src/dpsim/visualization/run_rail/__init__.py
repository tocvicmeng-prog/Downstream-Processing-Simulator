"""Sticky run rail — right-pane composition for Direction A.

Composes: run/stop button (orange while running, ■ icon, click cancels),
progress indicator, breakthrough preview, evidence rollup, recipe diff.

State machine: ``idle / running / stopping / done / error``.

Cancellation note: Streamlit reruns are not preemptible (architecture
spec §9 R-03). The "stop" click sets a session-state flag; the
orchestrator must poll that flag at its next checkpoint. We honour the
visual state immediately so the user sees the orange button flip back,
but the actual cancellation happens at the next checkpoint inside the
running orchestrator. The tooltip explains this.
"""

from __future__ import annotations

from dpsim.visualization.run_rail.history import (
    DEFAULT_HISTORY_PATH,
    HISTORY_KEY,
    MAX_HISTORY,
    RunHistoryEntry,
    append_history,
    clear_history,
    find,
    get_history,
    latest,
    load_history_from_disk,
    reload_run,
    render_history_dropdown,
    save_history_to_disk,
)
from dpsim.visualization.run_rail.progress import (
    CANCEL_FLAG_KEY,
    RUN_STATE_KEY,
    RunState,
    cancel_requested,
    clear_cancel,
    get_error_msg,
    get_progress,
    get_run_state,
    request_cancel,
    reset,
    set_progress,
    set_run_state,
)
from dpsim.visualization.run_rail.rail import render_run_rail

__all__ = [
    "CANCEL_FLAG_KEY",
    "DEFAULT_HISTORY_PATH",
    "HISTORY_KEY",
    "MAX_HISTORY",
    "RUN_STATE_KEY",
    "RunHistoryEntry",
    "RunState",
    "append_history",
    "cancel_requested",
    "clear_cancel",
    "clear_history",
    "find",
    "get_error_msg",
    "get_history",
    "get_progress",
    "get_run_state",
    "latest",
    "load_history_from_disk",
    "reload_run",
    "render_history_dropdown",
    "render_run_rail",
    "request_cancel",
    "reset",
    "save_history_to_disk",
    "set_progress",
    "set_run_state",
]
