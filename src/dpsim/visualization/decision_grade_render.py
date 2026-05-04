"""Streamlit-side glue for B-1b decision-grade rendering.

Wraps ``core.decision_grade.render_value`` in helpers that play nicely with
``st.metric`` and friends. Threading the gate through every M1/M2/M3 display
site is incremental work; this module provides the canonical pattern that
future per-site PRs should follow.

Usage pattern at a display site::

    from dpsim.core.decision_grade import OutputType
    from dpsim.visualization.decision_grade_render import render_metric

    render_metric(
        "Estimated Pressure Drop",
        value=delta_p_pa,
        output_type=OutputType.PRESSURE_DROP,
        tier=manifest.evidence_tier,
        unit="kPa",
        scale=1.0 / 1000.0,           # convert Pa → kPa for display only
    )

The helper:
  * Computes the render mode via ``core.decision_grade.decide_render_mode``.
  * Formats the value as NUMBER, INTERVAL, RANK_BAND, or SUPPRESS.
  * Emits a ``st.metric`` with a render-mode-derived help-text caption so
    the user can see *why* a number is rendered as an interval / rank /
    suppressed without reading the dossier.
"""

from __future__ import annotations

from typing import Optional

import streamlit as st

from dpsim.core.decision_grade import (
    OutputType,
    RenderMode,
    decide_render_mode,
    render_value,
)
from dpsim.datatypes import ModelEvidenceTier


# ─── Pure formatting (testable without Streamlit) ───────────────────────────


def format_decision_graded(
    value: float,
    output_type: OutputType,
    tier: ModelEvidenceTier,
    *,
    unit: str = "",
    scale: float = 1.0,
    rank_reference: Optional[float] = None,
) -> tuple[RenderMode, str]:
    """Format ``value`` per the decision-grade policy.

    ``scale`` lets the caller pre-multiply the value (typically a unit
    conversion: Pa → kPa = ``1/1000``, m → µm = ``1e6``, fraction → % =
    ``100``). Scaling is applied BEFORE the gate decides on a render mode,
    so the policy floor still gates on the (scientifically meaningful)
    raw-value tier — the scale only affects the display string.

    Returns ``(mode, display_string)`` so callers can branch on the mode
    if needed (e.g., add an "interval" caption only when degraded).
    """
    scaled = float(value) * float(scale)
    rv = render_value(
        scaled, output_type, tier,
        unit=unit,
        rank_reference=rank_reference,
    )
    return rv.mode, rv.display


def caption_for_mode(mode: RenderMode) -> str:
    """One-line caption explaining why a value is displayed in a non-NUMBER mode.

    Returns an empty string for NUMBER mode (no caption needed).
    """
    if mode == RenderMode.NUMBER:
        return ""
    if mode == RenderMode.INTERVAL:
        return "Rendered as ±30 % interval — calibration is one tier below the policy floor for this output."
    if mode == RenderMode.RANK_BAND:
        return "Rendered as rank band — calibration is two tiers below the policy floor; treat as ranking only."
    return "Suppressed — no decision-grade calibration available for this output type."


# ─── Streamlit wrappers ──────────────────────────────────────────────────────


def render_metric(
    label: str,
    *,
    value: float,
    output_type: OutputType,
    tier: ModelEvidenceTier,
    unit: str = "",
    scale: float = 1.0,
    rank_reference: Optional[float] = None,
    help: Optional[str] = None,
) -> None:
    """``st.metric`` wrapper that routes through the decision-grade gate.

    The metric value is the formatted string returned by
    :func:`format_decision_graded`. The help tooltip carries the
    mode-specific caption (so the user can hover and see "rendered as ±30%
    interval" instead of having to read the dossier).
    """
    mode, display = format_decision_graded(
        value, output_type, tier,
        unit=unit, scale=scale, rank_reference=rank_reference,
    )
    extra = caption_for_mode(mode)
    composed_help = "\n\n".join(p for p in (help, extra) if p)
    st.metric(label, display, help=composed_help or None)


def gate_decision_for(
    output_type: OutputType,
    tier: ModelEvidenceTier,
) -> RenderMode:
    """Convenience: which render mode would the policy choose for this pair.

    Useful for callers that want to skip an entire chart / table when the
    output would have been SUPPRESSED anyway (e.g. don't draw a breakthrough
    curve when the model is QUALITATIVE_TREND).
    """
    return decide_render_mode(output_type, tier)


__all__ = [
    "caption_for_mode",
    "format_decision_graded",
    "gate_decision_for",
    "render_metric",
]
