"""Background-thread orchestrator runner — closes the v0.4.6 platform floor.

The v0.4.6 close handover documented two items as "absolutely cannot
be done": mid-`solve_ivp` cancellation and first-paint triptych
animation. v0.4.7 built the scipy-events hook + threading flag and
the React custom components — but the cancel chain still had a gap:
the Streamlit script blocked synchronously on ``orchestrator.run()``,
so the Stop-button click could not reach Python until the solver
returned.

This module closes that gap. ``run_in_background()`` starts
``orchestrator.run()`` in a daemon thread and returns a
``BackgroundRun`` handle. The Streamlit script polls
``handle.is_running()`` on each rerun and triggers a 500 ms sleep +
``st.rerun()`` while running, which gives the WebSocket layer time to
deliver Stop clicks. When the user clicks Stop, ``request_cancel``
sets ``THREAD_CANCEL_FLAG``, the worker's scipy-event hook reads it
between integration steps, and the solver halts cleanly.

End-to-end cancel latency (worst case): one Streamlit poll interval
(500 ms) + one scipy integration step (≈ 100 ms) ≈ 600 ms.
"""

from __future__ import annotations

import threading
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from dpsim.lifecycle.cancellation import (
    RunCancelledError,
    clear_cancel_flag,
)


@dataclass
class BackgroundRun:
    """Handle to a running orchestrator thread.

    Attributes:
        thread: The daemon ``threading.Thread`` running the orchestrator.
        result: Populated on successful completion. ``None`` if the
            run is in progress or failed.
        exception: Populated on failure. ``None`` if the run is in
            progress or succeeded.
        cancelled: ``True`` if the run was cancelled mid-flight.
        traceback_text: Human-readable traceback when ``exception`` is set.
        started_at: Wall-clock UTC timestamp when the worker started.
        finished_at: Wall-clock UTC timestamp when the worker finished
            (whether by success, failure, or cancellation).
    """

    thread: threading.Thread
    result: Any = None
    exception: BaseException | None = None
    cancelled: bool = False
    traceback_text: str = ""
    started_at: datetime = field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )
    finished_at: datetime | None = None

    def is_running(self) -> bool:
        """``True`` while the worker thread is alive."""
        return self.thread.is_alive()

    def is_done(self) -> bool:
        """``True`` once the worker has finished (any outcome)."""
        return not self.thread.is_alive()

    def succeeded(self) -> bool:
        """``True`` if finished AND no exception AND not cancelled."""
        return self.is_done() and self.exception is None and not self.cancelled

    def elapsed_seconds(self) -> float:
        """Wall-clock seconds since the worker started."""
        end = self.finished_at or datetime.now(tz=timezone.utc)
        return (end - self.started_at).total_seconds()


def run_in_background(
    target: Callable[..., Any],
    *,
    args: tuple = (),
    kwargs: dict[str, Any] | None = None,
    name: str = "dpsim-orchestrator-worker",
) -> BackgroundRun:
    """Start ``target(*args, **kwargs)`` in a daemon thread.

    Clears the cancellation flags before starting so a stale flag from
    a previous run cannot pre-cancel this one. The worker's result and
    any exception are captured into the returned ``BackgroundRun``
    handle; the caller polls ``is_running()`` / ``is_done()``.

    Args:
        target: Callable to run (e.g. ``orchestrator.run``).
        args: Positional arguments.
        kwargs: Keyword arguments.
        name: Thread name (visible in stack traces).

    Returns:
        A ``BackgroundRun`` handle. The thread is already started.
    """
    clear_cancel_flag()
    kwargs = dict(kwargs or {})

    handle = BackgroundRun(thread=None)  # type: ignore[arg-type]

    def _worker() -> None:
        try:
            handle.result = target(*args, **kwargs)
        except RunCancelledError:
            handle.cancelled = True
        except BaseException as exc:  # noqa: BLE001 — capture-and-rethrow is the contract
            handle.exception = exc
            handle.traceback_text = traceback.format_exc()
        finally:
            handle.finished_at = datetime.now(tz=timezone.utc)

    thread = threading.Thread(target=_worker, name=name, daemon=True)
    handle.thread = thread
    thread.start()
    return handle


__all__ = [
    "BackgroundRun",
    "run_in_background",
]
