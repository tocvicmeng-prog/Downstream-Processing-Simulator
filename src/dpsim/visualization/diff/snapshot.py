"""Recipe snapshot + diff comparator.

The snapshot stores a deep-copied dict representation of the
``ProcessRecipe`` (or any nested-dataclass / pydantic-model recipe
container) at the moment a successful run completes. The diff walks
the current recipe field-by-field and yields ``DiffEntry`` records
for every leaf-value mismatch.

We use ``dict``-of-leaves (not direct field-name comparison) so the
diff is robust against pydantic schema evolution: a field that exists
in the new model but not in the snapshot reads as ``(absent) → next``
and vice versa.
"""

from __future__ import annotations

import copy
from collections.abc import Iterable
from dataclasses import dataclass, fields, is_dataclass
from typing import Any, Final

# Sentinel object used when a field is absent in one recipe but present
# in the other.
_ABSENT: Final[object] = object()
ABSENT_LABEL: Final[str] = "(absent)"

# Streamlit session-state key. Underscored to mark it private.
SNAPSHOT_KEY: Final[str] = "_dpsim_last_run_recipe"


@dataclass(frozen=True)
class DiffEntry:
    """One leaf-level difference.

    Attributes:
        path: Dotted path to the leaf, e.g. ``m1.formulation.agarose_pct``.
        prev: Previous value (from the snapshot). The sentinel
            ``_ABSENT`` if the field did not exist in the snapshot.
        next: Current value (from the live recipe). The sentinel
            ``_ABSENT`` if the field has been removed.
    """

    path: str
    prev: Any
    next: Any


def _to_dict(obj: Any) -> Any:
    """Recursively convert a recipe object tree to plain Python.

    Handles dataclasses (the DPSim core path), pydantic models (if used
    elsewhere), dicts, lists / tuples, and primitive scalars. Anything
    else is stringified for diff purposes.
    """
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, dict):
        return {str(k): _to_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_dict(item) for item in obj]
    if is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: _to_dict(getattr(obj, f.name)) for f in fields(obj)}
    # pydantic v2: model_dump; v1: dict()
    if hasattr(obj, "model_dump") and callable(obj.model_dump):
        return _to_dict(obj.model_dump())
    if hasattr(obj, "dict") and callable(obj.dict):
        try:
            return _to_dict(obj.dict())
        except TypeError:
            pass  # 'dict' attribute that isn't a method
    if hasattr(obj, "__dict__"):
        return {k: _to_dict(v) for k, v in vars(obj).items() if not k.startswith("_")}
    return str(obj)


def snapshot_recipe(recipe: Any) -> dict[str, Any]:
    """Deep-copy ``recipe`` into a plain-dict snapshot for diff later.

    Args:
        recipe: Any recipe-like object (dataclass, pydantic model,
            dict). Deep-copied so subsequent edits to the live recipe
            do not mutate the snapshot.

    Returns:
        A nested-dict snapshot suitable for passing to ``diff_recipes``.
    """
    return copy.deepcopy(_to_dict(recipe))  # type: ignore[no-any-return]


def _walk(prev: Any, curr: Any, path: str) -> Iterable[DiffEntry]:
    """Recursively yield diff entries between two normalised trees."""
    # If types differ at this level OR either side is a leaf, treat as leaf.
    is_prev_dict = isinstance(prev, dict)
    is_curr_dict = isinstance(curr, dict)
    is_prev_list = isinstance(prev, list)
    is_curr_list = isinstance(curr, list)

    if is_prev_dict and is_curr_dict:
        keys = sorted(set(prev.keys()) | set(curr.keys()))
        for k in keys:
            sub_prev = prev.get(k, _ABSENT)
            sub_curr = curr.get(k, _ABSENT)
            sub_path = f"{path}.{k}" if path else k
            yield from _walk(sub_prev, sub_curr, sub_path)
        return
    if is_prev_list and is_curr_list:
        max_len = max(len(prev), len(curr))
        for i in range(max_len):
            sub_prev = prev[i] if i < len(prev) else _ABSENT
            sub_curr = curr[i] if i < len(curr) else _ABSENT
            yield from _walk(sub_prev, sub_curr, f"{path}[{i}]")
        return
    # Leaf compare.
    if prev != curr:
        yield DiffEntry(path=path, prev=prev, next=curr)


def diff_recipes(prev: Any, curr: Any) -> list[DiffEntry]:
    """Diff two recipe-like objects.

    Args:
        prev: Snapshot of the previous recipe (or ``None`` if no
            baseline exists yet).
        curr: Current recipe.

    Returns:
        Ordered list of ``DiffEntry`` records. Empty if no differences
        or if ``prev`` is ``None``.
    """
    if prev is None:
        return []
    prev_norm = _to_dict(prev) if not isinstance(prev, dict) else prev
    curr_norm = _to_dict(curr)
    return list(_walk(prev_norm, curr_norm, path=""))
