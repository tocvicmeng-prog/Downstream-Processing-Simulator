"""Run-history list and dropdown.

Each successful run appends a ``RunHistoryEntry`` to
``st.session_state[HISTORY_KEY]``. The list is bounded to the last
``MAX_HISTORY`` entries; older entries are evicted FIFO.

v0.4.2 adds disk persistence: ``save_history_to_disk(path)`` writes the
in-memory list as JSON; ``load_history_from_disk(path)`` reads it back
on startup. The disk format is a list of dicts; the snapshot dict is
stored verbatim. Optional, non-default — the user opts in by passing
``persist_path`` to ``append_history``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final

import streamlit as st

HISTORY_KEY: Final[str] = "_dpsim_run_history"
MAX_HISTORY: Final[int] = 20

# Default disk-persistence path. Per-user, under the runtime cache root.
DEFAULT_HISTORY_PATH: Final[Path] = (
    Path.home() / ".dpsim" / "run_history.json"
)


@dataclass
class RunHistoryEntry:
    """One row in the run history.

    Attributes:
        run_id: Sequence number (1, 2, 3, ...) — assigned at append.
        timestamp_utc: When the run completed.
        recipe_name: Recipe filename or label.
        snapshot: Deep-copied recipe dict (suitable for diffing).
        evidence_min: ``ModelEvidenceTier.value`` of the lifecycle min.
        notes: Optional free-text annotation.
    """

    run_id: int
    timestamp_utc: datetime
    recipe_name: str
    snapshot: dict[str, Any]
    evidence_min: str
    notes: str = ""
    metrics: dict[str, str] = field(default_factory=dict)


def _list() -> list[RunHistoryEntry]:
    """Internal: return the current history list (creating if absent)."""
    hist = st.session_state.get(HISTORY_KEY)
    if hist is None:
        hist = []
        st.session_state[HISTORY_KEY] = hist
    return hist  # type: ignore[no-any-return]


def append_history(
    *,
    recipe_name: str,
    snapshot: dict[str, Any],
    evidence_min: str,
    notes: str = "",
    metrics: dict[str, str] | None = None,
) -> RunHistoryEntry:
    """Append a run to the history. Bounded to ``MAX_HISTORY`` entries."""
    hist = _list()
    next_id = (hist[-1].run_id + 1) if hist else 1
    entry = RunHistoryEntry(
        run_id=next_id,
        timestamp_utc=datetime.now(tz=timezone.utc),
        recipe_name=recipe_name,
        snapshot=snapshot,
        evidence_min=evidence_min,
        notes=notes,
        metrics=metrics or {},
    )
    hist.append(entry)
    # FIFO eviction.
    if len(hist) > MAX_HISTORY:
        del hist[: len(hist) - MAX_HISTORY]
    return entry


def clear_history() -> None:
    """Drop the entire history."""
    st.session_state[HISTORY_KEY] = []


def get_history() -> list[RunHistoryEntry]:
    """Return a snapshot copy of the current history (oldest → newest)."""
    return list(_list())


def latest() -> RunHistoryEntry | None:
    """Return the most recent run, or ``None`` if history is empty."""
    hist = _list()
    return hist[-1] if hist else None


def find(run_id: int) -> RunHistoryEntry | None:
    """Look up a single entry by ``run_id``."""
    for e in _list():
        if e.run_id == run_id:
            return e
    return None


# ── Disk persistence (v0.4.2) ─────────────────────────────────────────


def _entry_to_dict(entry: RunHistoryEntry) -> dict[str, Any]:
    """Serialise one entry to a JSON-safe dict."""
    return {
        "run_id": entry.run_id,
        "timestamp_utc": entry.timestamp_utc.isoformat(),
        "recipe_name": entry.recipe_name,
        "snapshot": entry.snapshot,
        "evidence_min": entry.evidence_min,
        "notes": entry.notes,
        "metrics": entry.metrics,
    }


def _entry_from_dict(d: dict[str, Any]) -> RunHistoryEntry:
    """Deserialise a JSON-loaded dict back into an entry."""
    ts_raw = d.get("timestamp_utc", "")
    try:
        ts = datetime.fromisoformat(ts_raw)
    except (TypeError, ValueError):
        ts = datetime.now(tz=timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return RunHistoryEntry(
        run_id=int(d.get("run_id", 0)),
        timestamp_utc=ts,
        recipe_name=str(d.get("recipe_name", "")),
        snapshot=dict(d.get("snapshot", {})),
        evidence_min=str(d.get("evidence_min", "")),
        notes=str(d.get("notes", "")),
        metrics=dict(d.get("metrics", {})),
    )


def save_history_to_disk(path: Path | None = None) -> Path:
    """Write the current history to disk as JSON.

    Args:
        path: Optional override. Defaults to ``DEFAULT_HISTORY_PATH``
            (``~/.dpsim/run_history.json``).

    Returns:
        The path written to.
    """
    target = path or DEFAULT_HISTORY_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = [_entry_to_dict(e) for e in _list()]
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return target


def load_history_from_disk(path: Path | None = None) -> int:
    """Load history from disk into session state.

    Returns:
        Number of entries loaded. ``0`` if the path does not exist
        (treated as no-history-yet, not an error).
    """
    source = path or DEFAULT_HISTORY_PATH
    if not source.exists():
        return 0
    try:
        raw = json.loads(source.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return 0
    if not isinstance(raw, list):
        return 0
    entries = [_entry_from_dict(d) for d in raw if isinstance(d, dict)]
    # FIFO-cap when loading to honour MAX_HISTORY.
    if len(entries) > MAX_HISTORY:
        entries = entries[-MAX_HISTORY:]
    st.session_state[HISTORY_KEY] = entries
    return len(entries)


def reload_run(entry: RunHistoryEntry, *, recipe: Any) -> None:
    """Apply a historical run's snapshot back onto the live recipe.

    The snapshot is a deep-dict; we walk the live recipe and assign each
    leaf from the matching path. Pydantic / dataclass setattr is best-
    effort — fields that don't exist in the current model are skipped.
    """
    def _apply(target: Any, snapshot: dict[str, Any], path: str = "") -> None:
        for key, value in snapshot.items():
            if not hasattr(target, key):
                continue
            current = getattr(target, key)
            if isinstance(value, dict) and not isinstance(current, dict):
                _apply(current, value, path=f"{path}.{key}" if path else key)
            else:
                try:
                    setattr(target, key, value)
                except (AttributeError, TypeError, ValueError):
                    # Read-only / typed mismatch — skip silently.
                    pass

    _apply(recipe, entry.snapshot)


def _format_relative(ts: datetime) -> str:
    """Human-readable elapsed time (≤ 1 minute precision)."""
    delta = datetime.now(tz=timezone.utc) - ts
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return f"{seconds} s ago"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} min ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} h ago"
    days = hours // 24
    return f"{days} d ago"


def render_history_dropdown(
    *,
    on_select: "Any | None" = None,
    current_recipe: Any = None,
    enable_disk_persistence: bool = True,
) -> RunHistoryEntry | None:
    """Render a Streamlit dropdown of run history with disk + reload UI.

    Use as the ``extra_top_section`` of ``run_rail.render_run_rail``.

    Args:
        on_select: Optional callable invoked with the selected
            ``RunHistoryEntry`` when the user picks a non-current row.
        current_recipe: Live recipe — required for the "Reload" button.
            ``None`` disables reload.
        enable_disk_persistence: Whether to surface the save/load disk
            buttons. Default ``True``.

    Returns:
        The selected entry, or ``None`` if no history exists or no
        selection was made.
    """
    hist = _list()
    if not hist:
        st.html(
            '<div class="dps-mono" style="font-size:11px;'
            'color:var(--dps-text-dim);padding:4px 0;">'
            "no runs yet"
            "</div>"
        )
        if enable_disk_persistence:
            if st.button(
                "↻ Load history from disk",
                key="_dpsim_history_load_disk",
                use_container_width=True,
            ):
                n = load_history_from_disk()
                if n > 0:
                    st.success(f"Loaded {n} entr{'y' if n == 1 else 'ies'} from disk.")
                    st.rerun()
                else:
                    st.info("No saved history found on disk.")
        return None

    # Newest-first option labels.
    options = list(reversed(hist))
    labels = [
        f"Run #{e.run_id} · {_format_relative(e.timestamp_utc)} · {e.recipe_name}"
        for e in options
    ]
    idx = st.selectbox(
        "Run history",
        options=list(range(len(options))),
        format_func=lambda i: labels[i],
        key="_dpsim_run_history_select",
        label_visibility="collapsed",
    )
    selected = options[int(idx)]
    if on_select is not None:
        try:
            on_select(selected)
        except Exception:  # pragma: no cover — non-critical
            pass

    # Reload + persistence controls.
    btn_cols = st.columns([1, 1, 1])
    with btn_cols[0]:
        if current_recipe is not None and st.button(
            "↻ Reload",
            key=f"_dpsim_history_reload_{selected.run_id}",
            use_container_width=True,
            help="Apply this historical run's recipe state to the live recipe.",
        ):
            reload_run(selected, recipe=current_recipe)
            st.success(f"Reloaded run #{selected.run_id}.")
            st.rerun()
    if enable_disk_persistence:
        with btn_cols[1]:
            if st.button(
                "💾 Save",
                key="_dpsim_history_save_disk",
                use_container_width=True,
                help="Persist all history to disk.",
            ):
                target = save_history_to_disk()
                st.success(f"Saved to {target}")
        with btn_cols[2]:
            if st.button(
                "↻ Load",
                key="_dpsim_history_load_disk_existing",
                use_container_width=True,
                help="Reload history from disk (overwrites current session).",
            ):
                n = load_history_from_disk()
                if n > 0:
                    st.success(f"Loaded {n} entries.")
                    st.rerun()

    return selected
