"""ParamRow + Help widget.

Renders a label + click-to-pin help bubble + a Streamlit input widget +
optional unit + optional evidence badge in a compact horizontal row.

The Help bubble is a real Streamlit ``st.popover`` — click to open, click
outside to dismiss. This is the simplest available Streamlit primitive
that matches the design's "click to pin" behaviour without requiring a
custom React component.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

import streamlit as st

from dpsim.datatypes import ModelEvidenceTier
from dpsim.visualization.design import chrome

T = TypeVar("T")


def render_help(text: str, *, key: str | None = None) -> None:
    """Render a single ``?`` popover with help text.

    Args:
        text: Help text to display in the popover. Supports markdown.
        key: Optional Streamlit key. Should be unique per popover when
            rendered multiple times on the same page.
    """
    with st.popover("?", help="What does this do?", use_container_width=False):
        st.markdown(text)


def labeled_widget(
    label: str,
    *,
    widget: Callable[[], T],
    help: str = "",
    unit: str = "",
    evidence: ModelEvidenceTier | str | None = None,
) -> T:
    """Inline-friendly version of ``param_row`` for use INSIDE a column.

    Streamlit allows only one level of column nesting. The full
    ``param_row`` creates four columns internally, which collides with
    the existing tab layouts that already render widgets inside
    ``st.columns``. ``labeled_widget`` instead renders the widget
    naturally and emits a small inline ``[label] [?] [evidence] [unit]``
    annotation strip ABOVE the widget. Functionally equivalent for the
    user but layout-safe.

    Args:
        label: Parameter label.
        widget: Zero-arg callable that emits the Streamlit input.
        help: Optional help text — renders as a ``?`` popover.
        unit: Optional unit suffix.
        evidence: Optional evidence tier badge.

    Returns:
        The widget's return value.
    """
    badge_html = (
        chrome.evidence_badge(evidence, compact=True) if evidence is not None else ""
    )
    unit_html = (
        f'<span class="dps-mono" style="font-size:11px;'
        f'color:var(--dps-text-dim);margin-left:6px;">{unit}</span>'
        if unit
        else ""
    )
    st.html(
        f'<div style="display:flex;align-items:center;gap:6px;'
        f'margin-top:2px;font-size:12.5px;color:var(--dps-text-muted);'
        f'font-weight:500;">'
        f'<span>{label}</span>{badge_html}{unit_html}</div>'
    )
    if help:
        render_help(help)
    return widget()


def param_row(
    label: str,
    *,
    widget: Callable[[], T],
    help: str = "",
    unit: str = "",
    evidence: ModelEvidenceTier | str | None = None,
    key_suffix: str = "",
) -> T:
    """Render a labeled input row with optional help, unit, and evidence.

    Layout (left → right):
        [label] [?] [evidence_badge] [widget] [unit]

    Args:
        label: Parameter label (e.g. "Stir rate").
        widget: A zero-arg callable that emits ONE Streamlit input
            and returns its value. Examples:

                lambda: st.slider("Stir rate", 100, 1200, 420, key="m1_stir")
                lambda: st.number_input("Conc.", 0.5, 200.0, 10.0)

            The widget is rendered in the third column. Its label is
            visible; pass ``label_visibility="collapsed"`` inside the
            lambda if you want the row's ``label`` to be the only one.
        help: Optional help text (markdown). Renders as a ``?`` popover
            next to the label.
        unit: Optional unit suffix shown right of the widget (e.g.
            "rpm", "°C/min", "% w/v").
        evidence: Optional evidence tier badge inline with the label.
        key_suffix: Disambiguator if the same parameter is rendered in
            multiple places (e.g. once per reagent step).

    Returns:
        The widget's return value.

    Notes:
        - Uses ``st.columns([2.5, 0.4, 4, 0.8])`` for label / help /
          widget / unit. The ratios are tuned so that typical labels
          ("Stir rate", "Concentration", "Reaction time", "Pore model")
          do not truncate at standard Streamlit widths.
        - Evidence badge, when present, slots between the label and
          help icon.
    """
    cols = st.columns([2.5, 0.4, 4, 0.8])
    with cols[0]:
        if evidence is not None:
            badge_html = chrome.evidence_badge(evidence, compact=True)
            st.html(
                f'<div style="display:flex;align-items:center;gap:6px;'
                f"padding-top:4px;font-size:13px;color:var(--dps-text-muted);"
                f'font-weight:500;">{label}{badge_html}</div>'
            )
        else:
            st.html(
                f'<div style="padding-top:4px;font-size:13px;'
                f"color:var(--dps-text-muted);font-weight:500;\">{label}</div>"
            )
    with cols[1]:
        if help:
            render_help(help, key=f"help_{label}_{key_suffix}")
    with cols[2]:
        value = widget()
    with cols[3]:
        if unit:
            st.html(
                f'<div class="dps-mono" style="padding-top:8px;'
                f'font-size:11px;color:var(--dps-text-dim);">{unit}</div>'
            )
    return value
