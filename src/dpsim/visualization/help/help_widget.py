"""ParamRow + Help widget — Direction-A canonical inline rendering.

Renders a label + inline help icon + Streamlit input + optional unit +
optional evidence badge in a compact horizontal row.

The help icon is a 14×14 px inline ``<details>`` element. The
``<summary>`` is the ``?`` glyph; toggling it opens an absolute-
positioned 260 px bubble. ``<details>`` keeps its state natively,
so there is no Streamlit rerun overhead and the icon adds zero
vertical space — replacing the previous ``st.popover``-based
implementation that forced a full row.
"""

from __future__ import annotations

import html as _html
import re
from collections.abc import Callable
from typing import TypeVar

import streamlit as st

from dpsim.datatypes import ModelEvidenceTier
from dpsim.visualization.design import chrome

T = TypeVar("T")


def _markdown_lite(text: str) -> str:
    """Escape ``text`` for HTML and render a minimal markdown subset.

    Supported: ``**bold**`` → ``<strong>``, single-backtick ``code`` →
    ``<code>``, and newline → ``<br>``. Anything else is left as plain
    text. The full markdown grammar is intentionally not supported —
    help strings in ``catalog.py`` use this subset.
    """
    safe = _html.escape(text)
    safe = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", safe)
    safe = re.sub(r"`([^`]+)`", r"<code>\1</code>", safe)
    safe = safe.replace("\n", "<br>")
    return safe


def _help_html(text: str, side: str = "right") -> str:
    """Return the inline 14 px ``?`` ``<details>`` block HTML.

    Args:
        text: Help text (plain or minimal markdown).
        side: ``"right"`` (default) opens the bubble to the right of
            the icon. Use ``"left"`` near the right edge of a card
            so the bubble doesn't clip.
    """
    body = _markdown_lite(text)
    side_cls = "dps-help-left" if side == "left" else "dps-help-right"
    return (
        '<details class="dps-help-inline">'
        '<summary aria-label="What does this do?">?</summary>'
        f'<div class="dps-help-bubble {side_cls}">{body}</div>'
        "</details>"
    )


def render_help(text: str, *, key: str | None = None, side: str = "right") -> None:
    """Render a single inline 14 px ``?`` help bubble.

    Args:
        text: Help text. Supports ``**bold**`` and ``​`code​``
            but not the full markdown grammar.
        key: Ignored. Kept for backwards compatibility with the
            previous ``st.popover``-based signature.
        side: Bubble side. ``"right"`` (default) or ``"left"``.
    """
    del key
    st.html(_help_html(text, side=side))


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
    naturally and emits a single-line ``[label] [?] [evidence] [unit]``
    annotation strip ABOVE the widget. The help bubble is inline so
    the strip stays one row tall (~22 px) regardless of help length.

    Args:
        label: Parameter label.
        widget: Zero-arg callable that emits the Streamlit input.
        help: Optional help text — renders as a 14 px inline ``?``.
        unit: Optional unit suffix.
        evidence: Optional evidence tier badge.

    Returns:
        The widget's return value.
    """
    badge_html = (
        chrome.evidence_badge(evidence, compact=True)
        if evidence is not None
        else ""
    )
    unit_html = (
        f'<span class="dps-mono" style="font-size:11px;'
        f'color:var(--dps-text-dim);margin-left:auto;">{_html.escape(unit)}</span>'
        if unit
        else ""
    )
    help_html_str = _help_html(help) if help else ""
    st.html(
        '<div style="display:flex;align-items:center;gap:6px;'
        'margin-top:2px;font-size:12.5px;color:var(--dps-text-muted);'
        'font-weight:500;line-height:1.4;">'
        f'<span>{_html.escape(label)}</span>'
        f"{help_html_str}{badge_html}{unit_html}"
        "</div>"
    )
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
        [label · ? · evidence_badge] [widget] [unit]

    The help icon now sits INSIDE the label cell as an inline 14 px
    glyph, so the row collapses from 4 columns to 3.

    Args:
        label: Parameter label (e.g. "Stir rate").
        widget: A zero-arg callable that emits ONE Streamlit input
            and returns its value.
        help: Optional help text — supports ``**bold**`` and
            single-backtick ``code``.
        unit: Optional unit suffix (e.g. "rpm", "°C/min").
        evidence: Optional evidence tier badge inline with the label.
        key_suffix: Disambiguator if the same parameter is rendered in
            multiple places (e.g. once per reagent step).

    Returns:
        The widget's return value.
    """
    del key_suffix
    cols = st.columns([2.9, 4, 0.8])
    with cols[0]:
        badge_html = (
            chrome.evidence_badge(evidence, compact=True)
            if evidence is not None
            else ""
        )
        help_html_str = _help_html(help) if help else ""
        st.html(
            '<div style="display:flex;align-items:center;gap:6px;'
            'padding-top:4px;font-size:13px;color:var(--dps-text-muted);'
            'font-weight:500;line-height:1.4;">'
            f'<span>{_html.escape(label)}</span>'
            f"{help_html_str}{badge_html}"
            "</div>"
        )
    with cols[1]:
        value = widget()
    with cols[2]:
        if unit:
            st.html(
                '<div class="dps-mono" style="padding-top:8px;'
                'font-size:11px;color:var(--dps-text-dim);">'
                f'{_html.escape(unit)}</div>'
            )
    return value
