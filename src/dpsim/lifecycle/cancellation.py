"""Cancellation hook for long-running orchestrator stages.

The visualization layer's "Stop run" button (see
``dpsim.visualization.run_rail.progress.request_cancel``) sets a flag
in ``st.session_state["_dpsim_run_cancelled"]``. This module provides
a free-standing checkpoint that the orchestrator polls at stage
boundaries — Streamlit's session_state is read-safe from any thread.

v0.4.7 additions:

- ``make_cancel_event()`` returns a scipy ``solve_ivp``-compatible
  event function with ``terminal=True``. Pass it via ``events=`` to
  enable per-integration-step cancellation INSIDE a single
  ``solve_ivp`` call — the previously-impossible "mid-solve cancel"
  case. Latency drops from "one full solve_ivp" to "one integration
  step" (typically <100 ms).
- ``THREAD_CANCEL_FLAG`` is a module-level ``threading.Event`` that
  worker threads can read independently of Streamlit's session_state.
  The Streamlit script ``set()``s it when ``request_cancel`` fires;
  scipy event functions read it from inside the integration loop.

Design note: the lifecycle layer must NOT depend on the visualization
layer (architecture rule). This module imports ``streamlit`` lazily
inside the function body so non-UI callers (CLI, tests) hit the
no-op fast path without importing Streamlit at all.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any, Final

CANCEL_FLAG_KEY: Final[str] = "_dpsim_run_cancelled"

# Threading event used by scipy event hooks and any worker-thread caller
# that needs cancellation visibility without touching Streamlit. Set by
# ``set_thread_cancel_flag``; read by ``thread_cancel_requested``. The
# Streamlit-side ``request_cancel`` should mirror its writes here.
THREAD_CANCEL_FLAG: Final[threading.Event] = threading.Event()


class RunCancelledError(RuntimeError):
    """Raised when a user-initiated stop is honoured at a checkpoint.

    The orchestrator should propagate this; the UI catches it specifically
    in ``render_lifecycle_run_panel`` and presents a non-error message.
    """


def check_cancel(*, stage: str = "checkpoint") -> None:
    """Raise ``RunCancelledError`` if a stop has been requested.

    Args:
        stage: Optional label for the checkpoint, included in the
            exception message. Used for diagnostics; not routed into
            session state.

    No-op when Streamlit is not importable or the session_state flag is
    not set. Safe to call from any orchestrator stage.
    """
    try:
        import streamlit as st
    except ImportError:
        return
    try:
        if bool(st.session_state.get(CANCEL_FLAG_KEY, False)):
            raise RunCancelledError(f"Run cancelled at {stage}.")
    except RunCancelledError:
        raise
    except Exception:  # pragma: no cover — defensive (e.g. no SessionInfo)
        return


def clear_cancel_flag() -> None:
    """Clear both the Streamlit and threading cancel flags.

    Call at run start to reset state. Mirrors the clear to both
    surfaces so worker threads and the Streamlit script stay in sync.
    """
    THREAD_CANCEL_FLAG.clear()
    try:
        import streamlit as st

        st.session_state[CANCEL_FLAG_KEY] = False
    except (ImportError, Exception):  # pragma: no cover — defensive
        pass


def set_thread_cancel_flag() -> None:
    """Set the threading cancel flag from the Streamlit side.

    Call this from the run-rail's stop-button click handler in addition
    to the existing session-state flag write. Worker threads (e.g.
    ``solve_ivp`` running in a background thread) read this without
    touching Streamlit.
    """
    THREAD_CANCEL_FLAG.set()


def thread_cancel_requested() -> bool:
    """Read the threading cancel flag without touching Streamlit."""
    return THREAD_CANCEL_FLAG.is_set()


def make_cancel_event(
    *,
    flag: threading.Event | None = None,
) -> Callable[[float, Any], float]:
    """Build a scipy ``solve_ivp``-compatible event function.

    The returned callable has ``.terminal = True`` and
    ``.direction = -1`` set as attributes, so scipy halts the
    integration at the first zero crossing in the negative direction.

    The event function returns ``+1.0`` while no cancel is requested
    and ``-1.0`` once it is — guaranteeing exactly one zero crossing.

    Args:
        flag: Threading event to read. ``None`` → use the module-global
            ``THREAD_CANCEL_FLAG`` (back-compat default). Pass a per-
            run ``threading.Event`` to scope cancellation to a single
            background run, which avoids the multi-tab cross-cancel
            bug (audit fix v0.4.9 F-3).

    Usage::

        from dpsim.lifecycle.cancellation import make_cancel_event
        sol = solve_ivp(rhs, t_span, y0, events=[make_cancel_event()])
        if sol.t_events and len(sol.t_events[0]):
            raise RunCancelledError("Cancelled mid-solve.")

    """
    target = flag if flag is not None else THREAD_CANCEL_FLAG

    def _event(t: float, y: Any) -> float:
        return -1.0 if target.is_set() else 1.0

    _event.terminal = True  # type: ignore[attr-defined]
    _event.direction = -1.0  # type: ignore[attr-defined]
    return _event


__all__ = [
    "CANCEL_FLAG_KEY",
    "RunCancelledError",
    "THREAD_CANCEL_FLAG",
    "check_cancel",
    "clear_cancel_flag",
    "make_cancel_event",
    "set_thread_cancel_flag",
    "thread_cancel_requested",
]
