"""Named recipe baselines.

The v0.4.0 diff module compares against the LAST successful run only.
v0.4.1 extends this with **tagged baselines** — name a recipe state and
compare against it later. Useful for "is my edit closer to the
calibrated reference, or to the screening default?".

Baselines are session-state-scoped (not persisted across restarts);
they coexist with the v0.4.0 ``SNAPSHOT_KEY`` (last-run snapshot),
which stays the default diff target.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Final

import streamlit as st

from dpsim.visualization.diff.snapshot import _to_dict

BASELINES_KEY: Final[str] = "_dpsim_recipe_baselines"


@dataclass(frozen=True)
class Baseline:
    """A named recipe snapshot.

    Attributes:
        name: User-supplied label (e.g. ``"protein_a_pilot.v1"``,
            ``"calibrated_2026-04"``). Names are unique within a
            session; saving with an existing name overwrites.
        snapshot: Deep-copied recipe dict (same shape as
            ``snapshot_recipe`` returns).
        created_utc: When the baseline was tagged.
        note: Optional free-text annotation.
    """

    name: str
    snapshot: dict[str, Any]
    created_utc: datetime
    note: str = ""


def _table() -> dict[str, Baseline]:
    """Internal: return the baselines map (creating if absent)."""
    table = st.session_state.get(BASELINES_KEY)
    if table is None:
        table = {}
        st.session_state[BASELINES_KEY] = table
    return table  # type: ignore[no-any-return]


def save_baseline(*, name: str, recipe: Any, note: str = "") -> Baseline:
    """Save the current recipe as a named baseline.

    Args:
        name: Unique-within-session name. Cannot be empty; cannot be
            the reserved name ``"last_run"``.
        recipe: Live recipe to deep-copy.
        note: Optional annotation.

    Returns:
        The created (or replaced) ``Baseline``.

    Raises:
        ValueError: if name is empty or reserved.
    """
    if not name.strip():
        raise ValueError("baseline name must be non-empty")
    if name == "last_run":
        raise ValueError("'last_run' is reserved for the v0.4.0 snapshot")
    snapshot = copy.deepcopy(_to_dict(recipe))
    baseline = Baseline(
        name=name,
        snapshot=snapshot,  # type: ignore[arg-type]
        created_utc=datetime.now(tz=timezone.utc),
        note=note,
    )
    _table()[name] = baseline
    return baseline


def get_baseline(name: str) -> Baseline | None:
    """Look up a baseline by name. Returns ``None`` if absent."""
    return _table().get(name)


def list_baselines() -> list[Baseline]:
    """Return all baselines, oldest → newest by ``created_utc``."""
    return sorted(_table().values(), key=lambda b: b.created_utc)


def delete_baseline(name: str) -> bool:
    """Remove a baseline by name. Returns ``True`` if it existed."""
    table = _table()
    if name in table:
        del table[name]
        return True
    return False


def baseline_choices(*, include_last_run: bool = True) -> list[str]:
    """Return a list of baseline names usable in an ``st.selectbox``.

    Args:
        include_last_run: Whether to prepend the reserved ``"last_run"``
            entry (the v0.4.0 default snapshot).
    """
    names = [b.name for b in list_baselines()]
    if include_last_run:
        return ["last_run"] + names
    return names


def render_baseline_picker(*, current_recipe: Any) -> str:
    """Render a baseline-management UI.

    Composition:
        1. Selectbox: pick "last_run" or any saved baseline as the diff target.
        2. Text input + button: tag the current recipe as a new baseline.
        3. List of saved baselines with a delete button each.

    Args:
        current_recipe: Live recipe — used as the source for "save".

    Returns:
        The name of the currently selected baseline (defaults to
        ``"last_run"``). Callers can pass this to a diff function that
        knows how to resolve the name.
    """
    choices = baseline_choices(include_last_run=True)
    selected = st.selectbox(
        "Diff baseline",
        options=choices,
        index=0,
        key="_dpsim_baseline_select",
        help="Compare against last-run snapshot or any tagged baseline.",
    )

    with st.expander("Manage baselines"):
        new_name = st.text_input(
            "Baseline name", key="_dpsim_baseline_new_name",
            placeholder="e.g. calibrated_2026-04",
        )
        new_note = st.text_input(
            "Note (optional)", key="_dpsim_baseline_new_note",
            placeholder="e.g. validated against batch 042",
        )
        if st.button("Tag current recipe as baseline",
                     key="_dpsim_baseline_save"):
            if new_name.strip() and new_name.strip() != "last_run":
                try:
                    save_baseline(
                        name=new_name.strip(),
                        recipe=current_recipe,
                        note=new_note,
                    )
                    st.success(f"Saved baseline: {new_name.strip()}")
                except ValueError as exc:
                    st.error(str(exc))
            else:
                st.error(
                    "Baseline name cannot be empty or 'last_run'."
                )

        existing = list_baselines()
        if existing:
            st.caption("Saved baselines:")
            for b in existing:
                cols = st.columns([4, 1])
                with cols[0]:
                    note_str = f" — {b.note}" if b.note else ""
                    st.html(
                        '<div class="dps-mono" style="font-size:11px;'
                        f'color:var(--dps-text-muted);">'
                        f'{b.name}{note_str}'
                        '</div>'
                    )
                with cols[1]:
                    if st.button("✕", key=f"_dpsim_baseline_del_{b.name}"):
                        delete_baseline(b.name)
                        st.rerun()

    return selected
