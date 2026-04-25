"""Triptych panel — declare_component-based Streamlit Custom Component.

Renders the Direction-B triptych chrome (3 columns, focused-column
expansion, summary chips, evidence badges) entirely on the React side.
Animation is owned by the component, so:

1. **First-paint animation works** — when the iframe mounts, React can
   start in a "neutral" state and animate into the focused state. The
   pure-CSS `transition` approach in v0.4.6 only animates between
   subsequent states because there's no "from" on first paint.
2. **Focus changes are instantaneous from the user's perspective** —
   the React component updates its own state immediately on click and
   reports the new focus to Python via ``setComponentValue``. Python
   doesn't need to rerun for the visual to update.
3. **The body of each focused column is rendered in Python**, NOT in
   the component. This keeps the existing tab renderers reusable. The
   component reports which column has focus; Python then renders the
   matching column body in its own slot beneath.

The component returns the focused column id (``"m1"`` / ``"m2"`` /
``"m3"``). Caller dispatches stage-body rendering based on this value.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

import streamlit.components.v1 as components

from dpsim.datatypes import ModelEvidenceTier

_ASSET_DIR: Final[Path] = (
    Path(__file__).parents[1] / "assets" / "triptych_panel"
)

_triptych_component = components.declare_component(
    "dpsim_triptych_panel",
    path=str(_ASSET_DIR),
)


def _normalise_chip(c: Any) -> dict[str, Any]:
    """Coerce a chip tuple/dict into the dict the JS side expects."""
    if isinstance(c, dict):
        return {
            "k": str(c.get("k", "")),
            "v": str(c.get("v", "")),
            "warn": bool(c.get("warn", False)),
        }
    # Tuple form: (key, value) or (key, value, warn)
    if isinstance(c, (list, tuple)):
        if len(c) == 2:
            return {"k": str(c[0]), "v": str(c[1]), "warn": False}
        if len(c) >= 3:
            return {"k": str(c[0]), "v": str(c[1]), "warn": bool(c[2])}
    return {"k": "", "v": str(c), "warn": False}


def _normalise_tier(tier: Any) -> str:
    if isinstance(tier, ModelEvidenceTier):
        return tier.value
    return str(tier or ModelEvidenceTier.UNSUPPORTED.value)


def triptych_panel(
    *,
    focus: str = "m2",
    m1: dict[str, Any] | None = None,
    m2: dict[str, Any] | None = None,
    m3: dict[str, Any] | None = None,
    height: int = 240,
    key: str = "dpsim_triptych_panel",
) -> str:
    """Render the triptych panel and return the focused column id.

    Args:
        focus: Initial focused column id (``"m1"`` / ``"m2"`` / ``"m3"``).
        m1, m2, m3: Per-stage dicts. Each dict accepts the keys:
            ``title`` (str): main heading.
            ``subtitle`` (str): muted caption.
            ``evidence`` (str | ModelEvidenceTier): tier value.
            ``summary`` (Sequence): list of (key, value) or (key, value, warn).
        height: Iframe height in px. Default 240 fits the chrome.
        key: Streamlit widget key.

    Returns:
        The currently focused column id. Updated on every rerun so
        the caller can dispatch body rendering accordingly.
    """
    def _stage(d: dict[str, Any] | None, default_title: str) -> dict[str, Any]:
        d = d or {}
        return {
            "title": str(d.get("title", default_title)),
            "subtitle": str(d.get("subtitle", "")),
            "evidence": _normalise_tier(d.get("evidence")),
            "summary": [_normalise_chip(c) for c in d.get("summary", []) or []],
        }

    payload = {
        "initialFocus": focus,
        "m1": _stage(m1, "Fabrication"),
        "m2": _stage(m2, "Functionalisation"),
        "m3": _stage(m3, "Column method"),
    }

    raw = _triptych_component(
        payloadJson=json.dumps(payload),
        height=int(height),
        default={"focus": focus},
        key=key,
    )
    if isinstance(raw, dict):
        focus_value = str(raw.get("focus", focus))
        if focus_value in ("m1", "m2", "m3"):
            return focus_value
    return focus


def chip(key: str, value: str, *, warn: bool = False) -> tuple[str, str, bool]:
    """Convenience helper for building summary-chip lists."""
    return (key, value, warn)


__all__ = ["chip", "triptych_panel"]
