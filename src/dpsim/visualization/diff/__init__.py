"""Recipe-diff vs last successful run.

Snapshots the active ``ProcessRecipe`` at run-end into Streamlit session
state, then on every subsequent render compares the *current* recipe
against the snapshot and produces a list of ``DiffEntry(path, prev,
next)`` records, rendered as ``path · prev → next`` lines.
"""

from __future__ import annotations

from dpsim.visualization.diff.baselines import (
    BASELINES_KEY,
    Baseline,
    baseline_choices,
    delete_baseline,
    get_baseline,
    list_baselines,
    render_baseline_picker,
    save_baseline,
)
from dpsim.visualization.diff.render import render_diff_panel
from dpsim.visualization.diff.snapshot import (
    SNAPSHOT_KEY,
    DiffEntry,
    diff_recipes,
    snapshot_recipe,
)

__all__ = [
    "BASELINES_KEY",
    "Baseline",
    "DiffEntry",
    "SNAPSHOT_KEY",
    "baseline_choices",
    "delete_baseline",
    "diff_recipes",
    "get_baseline",
    "list_baselines",
    "render_baseline_picker",
    "render_diff_panel",
    "save_baseline",
    "snapshot_recipe",
]
