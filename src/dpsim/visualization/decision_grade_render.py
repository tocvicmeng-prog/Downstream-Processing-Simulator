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

from dpsim.core.decision_claim import DecisionClaim, make_decision_claim
from dpsim.core.decision_grade import (
    OutputType,
    RenderMode,
    decide_render_mode,
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
    claim = format_decision_claim(
        value,
        output_type,
        tier,
        unit=unit,
        scale=scale,
        rank_reference=rank_reference,
    )
    return claim.render_mode, claim.display


def format_decision_claim(
    value: float,
    output_type: OutputType,
    tier: ModelEvidenceTier,
    *,
    name: str = "",
    unit: str = "",
    scale: float = 1.0,
    rank_reference: Optional[float] = None,
    valid_domain_status: str = "unknown",
    uncertainty_interval: Optional[tuple[float, float]] = None,
    calibration_ref: str = "",
    assay_required: str = "",
    reason: str = "",
) -> DecisionClaim:
    """Return the structured decision claim for a displayed value."""
    return make_decision_claim(
        value,
        output_type,
        tier,
        name=name,
        unit=unit,
        scale=scale,
        rank_reference=rank_reference,
        valid_domain_status=valid_domain_status,
        uncertainty_interval=uncertainty_interval,
        calibration_ref=calibration_ref,
        assay_required=assay_required,
        reason=reason,
    )


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
    delta: Optional[str] = None,
    delta_color: str = "normal",
    container=None,
) -> None:
    """``st.metric`` wrapper that routes through the decision-grade gate.

    The metric value is the formatted string returned by
    :func:`format_decision_graded`. The help tooltip carries the
    mode-specific caption (so the user can hover and see "rendered as ±30%
    interval" instead of having to read the dossier).

    Kwargs ``delta``, ``delta_color``, ``container`` are passthroughs:
      * ``delta`` and ``delta_color`` go directly to ``st.metric`` (used by
        existing M1 dashboard sites for "X% from target").
      * ``container`` lets the caller route the metric into a column /
        container without having to ``with col:`` — passing
        ``container=col`` is equivalent to ``col.metric(...)``.
    """
    mode, display = format_decision_graded(
        value, output_type, tier,
        unit=unit, scale=scale, rank_reference=rank_reference,
    )
    extra = caption_for_mode(mode)
    composed_help = "\n\n".join(p for p in (help, extra) if p)
    target = container if container is not None else st
    target.metric(
        label, display,
        delta=delta, delta_color=delta_color,
        help=composed_help or None,
    )


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


# ─── Plotly annotation tier-gating (B-1k / W-035, v0.8.1) ───────────────────


_MODE_TAG: dict[RenderMode, str] = {
    RenderMode.NUMBER: "",
    RenderMode.INTERVAL: " [INTERVAL]",
    RenderMode.RANK_BAND: " [RANK]",
    RenderMode.SUPPRESS: "",  # not annotated; gate skips drawing
}

_MODE_COLOR_HINT: dict[RenderMode, str] = {
    RenderMode.NUMBER: "",
    RenderMode.INTERVAL: "rgba(120, 120, 120, 0.85)",     # de-saturated grey
    RenderMode.RANK_BAND: "rgba(160, 100, 0, 0.85)",      # caution amber
    RenderMode.SUPPRESS: "rgba(180, 180, 180, 0.55)",
}


def render_decision_grade_annotation(
    fig,
    *,
    label: str,
    value: float,
    output_type: OutputType,
    tier: ModelEvidenceTier,
    unit: str = "",
    scale: float = 1.0,
    rank_reference: Optional[float] = None,
    color_override: Optional[str] = None,
    show_mode_tag: bool = True,
    **annotation_kwargs,
) -> Optional[RenderMode]:
    """Add a tier-gated text annotation to a Plotly figure.

    Companion to :func:`render_metric` for plotly chart overlays.
    Routes ``value`` through :func:`format_decision_graded`, picks a
    color hint based on the chosen render mode, and emits a
    ``fig.add_annotation`` call carrying the formatted display string.

    Suppress branch: when the policy returns ``RenderMode.SUPPRESS`` the
    function returns the mode without drawing — callers that want to
    visibly mark suppression should branch on the return value and add
    a "data not available" badge instead.

    Parameters
    ----------
    fig :
        ``plotly.graph_objects.Figure`` (or any object accepting
        ``add_annotation``). Annotation is drawn in-place.
    label :
        Prefix shown in the annotation text (e.g. ``"DBC₁₀"``).
    value :
        Raw numeric value before scale.
    output_type :
        Decision-grade output type that gates the policy.
    tier :
        Current evidence tier.
    unit :
        Unit string for display (e.g. ``"mol/m³"``, ``"kPa"``).
    scale :
        Multiplicative scale applied to ``value`` before formatting,
        per the same convention as :func:`format_decision_graded`.
    rank_reference :
        Optional rank-band anchor when the mode lands at RANK_BAND.
    color_override :
        Optional explicit annotation font color; when None, the helper
        picks an unobtrusive color hint based on mode.
    show_mode_tag :
        When True, append a ``[INTERVAL]`` / ``[RANK]`` suffix so users
        reading the chart see the render mode without hovering.
    **annotation_kwargs :
        Extra kwargs forwarded to ``fig.add_annotation`` — typically
        ``x``, ``y``, ``xref``, ``yref``, ``showarrow``, ``font``, etc.

    Returns
    -------
    RenderMode or None
        The render mode chosen by the policy, or ``None`` when no
        annotation was drawn (only happens if the caller had passed
        an explicit ``annotation_text`` that overrode the formatted
        display — in current usage, always returns a RenderMode).
    """
    mode, display = format_decision_graded(
        value, output_type, tier,
        unit=unit, scale=scale, rank_reference=rank_reference,
    )
    if mode == RenderMode.SUPPRESS:
        return mode

    tag = _MODE_TAG[mode] if show_mode_tag else ""
    text = f"{label}={display}{tag}" if label else f"{display}{tag}"
    color = (
        color_override
        if color_override is not None
        else _MODE_COLOR_HINT.get(mode) or None
    )

    kwargs = {
        "text": text,
        "showarrow": False,
    }
    if color:
        font = annotation_kwargs.pop("font", None) or {}
        if "color" not in font:
            font = {**font, "color": color}
        kwargs["font"] = font
    kwargs.update(annotation_kwargs)
    fig.add_annotation(**kwargs)
    return mode


__all__ = [
    "caption_for_mode",
    "format_decision_claim",
    "format_decision_graded",
    "gate_decision_for",
    "render_decision_grade_annotation",
    "render_metric",
]
