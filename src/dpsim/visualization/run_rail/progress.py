"""Run-state machine + cancellation flag.

State transitions:

    idle ──[run]──▶ running ──[stop]──▶ stopping ──[checkpoint]──▶ idle
                          ╰──[done]──▶ done    ──[ack]──▶ idle
                          ╰──[error]─▶ error   ──[ack]──▶ idle

The stop transition does NOT instantly cancel the orchestrator — it
sets ``CANCEL_FLAG_KEY`` and changes the visual state to ``stopping``.
The orchestrator (or the calling rerun) must poll ``cancel_requested``
at its next checkpoint and complete the transition to ``idle``.
"""

from __future__ import annotations

from typing import Final, Literal

import streamlit as st

RunState = Literal["idle", "running", "stopping", "done", "error"]

RUN_STATE_KEY: Final[str] = "_dpsim_run_state"
CANCEL_FLAG_KEY: Final[str] = "_dpsim_run_cancelled"
PROGRESS_KEY: Final[str] = "_dpsim_run_progress"
ERROR_KEY: Final[str] = "_dpsim_run_error_msg"


def get_run_state() -> RunState:
    """Read the current run state from session state."""
    return st.session_state.get(RUN_STATE_KEY, "idle")  # type: ignore[no-any-return]


def set_run_state(state: RunState, *, error_msg: str = "") -> None:
    """Set the run state.

    Args:
        state: New state (one of the RunState literals).
        error_msg: Stored under ``ERROR_KEY`` when transitioning to
            ``error``; cleared otherwise.
    """
    st.session_state[RUN_STATE_KEY] = state
    if state == "error":
        st.session_state[ERROR_KEY] = error_msg
    elif error_msg == "":
        st.session_state[ERROR_KEY] = ""


def get_progress() -> int:
    """Current progress percentage 0..100."""
    return int(st.session_state.get(PROGRESS_KEY, 0))


def set_progress(pct: int) -> None:
    """Set progress percentage; clamps to 0..100."""
    st.session_state[PROGRESS_KEY] = max(0, min(100, int(pct)))


def cancel_requested() -> bool:
    """Check whether a stop has been requested.

    Orchestrator code should poll this at every safe checkpoint (e.g.
    between MC samples, between integrator steps in a long run) and
    raise ``RunCancelledError`` if it returns ``True``.
    """
    return bool(st.session_state.get(CANCEL_FLAG_KEY, False))


def request_cancel() -> None:
    """Set the cancel flag (both surfaces) and transition to ``stopping``.

    Mirrors the write to the threading flag in
    ``dpsim.lifecycle.cancellation.THREAD_CANCEL_FLAG`` so worker
    threads (e.g. scipy ``solve_ivp`` event hooks) see the cancel
    without touching session_state.
    """
    st.session_state[CANCEL_FLAG_KEY] = True
    try:
        from dpsim.lifecycle.cancellation import set_thread_cancel_flag

        set_thread_cancel_flag()
    except ImportError:  # pragma: no cover — lifecycle is always present
        pass
    set_run_state("stopping")


def clear_cancel() -> None:
    """Clear the cancel flag (post-checkpoint cleanup)."""
    st.session_state[CANCEL_FLAG_KEY] = False


def get_error_msg() -> str:
    """Read the last error message; empty string if none."""
    return str(st.session_state.get(ERROR_KEY, ""))


def reset() -> None:
    """Reset to ``idle`` with cleared progress / flags / errors."""
    set_run_state("idle")
    set_progress(0)
    clear_cancel()
    st.session_state[ERROR_KEY] = ""
