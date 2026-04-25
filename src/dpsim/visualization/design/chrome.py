"""Chrome primitives — stateless HTML-emitting helpers.

Each helper returns a self-contained ``<span>`` / ``<div>`` / ``<svg>``
HTML string ready to be embedded by ``st.html(...)`` or by another
helper's f-string. No Streamlit widget is emitted here — interactive
inputs live in ``dpsim.visualization.help.help_widget``.

Design source: ``.dpsim_tmp/design_handoff/project/components.jsx``
(EvidenceBadge, Eyebrow, Help, ParamRow, MetricValue, NumInput,
Segmented, Select, Slider, Btn, Chip, Breakthrough, MiniHistogram,
StageNode, Card). Visual conventions and colour mappings follow
``DESIGN.md`` and the ``--dps-*`` tokens in ``tokens.css``.

Critical rule (CLAUDE.md / app.py:73-78): the caller must pass these
strings to ``st.html(...)``, NEVER to ``st.markdown(...,
unsafe_allow_html=True)``. The Markdown parser eats ``*`` characters
inside CSS attribute selectors and corrupts the output.
"""

from __future__ import annotations

import html
import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Final, Literal

from dpsim.datatypes import ModelEvidenceTier

# ── Evidence tier registry ────────────────────────────────────────────
#
# Mirrors ``ModelEvidenceTier`` (SSOT in ``dpsim.datatypes``). Every
# enum member must have an entry here; ``test_design_tokens_match``
# enforces it. The colour values reference the ``--dps-*`` CSS
# variables so theme switches re-tint the badges automatically.

_TIER_LABEL: Final[dict[str, str]] = {
    "validated_quantitative": "validated",
    "calibrated_local": "calibrated",
    "semi_quantitative": "semi-quantitative",
    "qualitative_trend": "qualitative trend",
    "unsupported": "unsupported",
}
_TIER_SHORT: Final[dict[str, str]] = {
    "validated_quantitative": "VAL",
    "calibrated_local": "CAL",
    "semi_quantitative": "SEMI",
    "qualitative_trend": "QUAL",
    "unsupported": "UNS",
}
_TIER_COLOR: Final[dict[str, str]] = {
    "validated_quantitative": "var(--dps-green-600)",
    "calibrated_local": "var(--dps-green-500)",
    "semi_quantitative": "var(--dps-amber-500)",
    "qualitative_trend": "var(--dps-orange-500)",
    "unsupported": "var(--dps-red-600)",
}

# ── Stage-node status registry ────────────────────────────────────────
#
# Maps the four pipeline-spine status values to their dot/ring colour.
StageStatus = Literal["pending", "active", "valid", "warn"]

_STATUS_COLOR: Final[dict[str, dict[str, str]]] = {
    "pending": {"dot": "var(--dps-text-dim)", "ring": "var(--dps-border)"},
    "active": {"dot": "var(--dps-accent)", "ring": "var(--dps-accent)"},
    "valid": {"dot": "var(--dps-green-500)", "ring": "var(--dps-green-500)"},
    "warn": {"dot": "var(--dps-amber-500)", "ring": "var(--dps-amber-500)"},
}


def _esc(value: object) -> str:
    """HTML-escape any value coerced to ``str``.

    Use this for every dynamic value that lands inside an HTML attribute
    or text node. Prevents accidental injection from recipe field names
    that contain `<`, `>`, `&`, `"`, or `'`.
    """
    return html.escape(str(value), quote=True)


def _tier_value(tier: ModelEvidenceTier | str) -> str:
    """Resolve a ``ModelEvidenceTier`` member or string to its `.value`.

    CLAUDE.md mandates ``.value`` comparisons for the four enums
    (PolymerFamily, ACSSiteType, ModelEvidenceTier, ModelMode); the
    AST gate in ``test_v9_3_enum_comparison_enforcement`` enforces it.
    """
    if isinstance(tier, ModelEvidenceTier):
        return tier.value
    return str(tier)


# ──────────────────────────────────────────────────────────────────────
# EvidenceBadge
# ──────────────────────────────────────────────────────────────────────


def evidence_badge(
    tier: ModelEvidenceTier | str,
    *,
    compact: bool = False,
) -> str:
    """Render a small evidence-tier badge.

    Args:
        tier: A ``ModelEvidenceTier`` member or its `.value` string.
        compact: When ``True``, use the 3-letter short label (``VAL`` /
            ``CAL`` / ``SEMI`` / ``QUAL`` / ``UNS``) and tighter
            padding. Used inline in ``ParamRow`` and ``StageNode``.

    Returns:
        A self-contained ``<span>`` HTML string.
    """
    key = _tier_value(tier)
    label = _TIER_LABEL.get(key, key)
    short = _TIER_SHORT.get(key, key.upper()[:4])
    color = _TIER_COLOR.get(key, "var(--dps-text-muted)")
    text = short if compact else label
    pad = "1px 5px" if compact else "2px 7px"
    font_size = "10px" if compact else "11px"
    return (
        f'<span title="{_esc(label)}" '
        f'style="display:inline-flex;align-items:center;gap:4px;'
        f"padding:{pad};border-radius:2px;"
        f"background:color-mix(in oklab, {color} 14%, transparent);"
        f"color:{color};font-family:var(--dps-font-mono);"
        f"font-size:{font_size};font-weight:600;letter-spacing:0.02em;"
        f'white-space:nowrap;">'
        f'<span style="width:5px;height:5px;border-radius:5px;'
        f'background:{color};display:inline-block;"></span>'
        f"{_esc(text)}</span>"
    )


# ──────────────────────────────────────────────────────────────────────
# Eyebrow — uppercase mono micro-header
# ──────────────────────────────────────────────────────────────────────


def eyebrow(text: str, *, accent: bool = False) -> str:
    """Render a 10.5px uppercase letter-spaced label.

    Used above section titles ("Stage 02 · M1", "Predicted M1 outputs",
    etc.). Set ``accent=True`` to colour with ``--dps-accent`` instead
    of ``--dps-text-dim``.
    """
    color = "var(--dps-accent)" if accent else "var(--dps-text-dim)"
    return (
        f'<div class="dps-mono" '
        f'style="font-size:10.5px;letter-spacing:0.14em;'
        f"text-transform:uppercase;color:{color};font-weight:600;\">"
        f"{_esc(text)}</div>"
    )


# ──────────────────────────────────────────────────────────────────────
# Chip — small filled / outlined tag
# ──────────────────────────────────────────────────────────────────────


def chip(
    text: str,
    *,
    color: str = "var(--dps-text-muted)",
    filled: bool = False,
) -> str:
    """Render a tag/chip.

    Args:
        text: Chip label.
        color: Any CSS colour expression. Defaults to muted text.
        filled: When ``True``, fill with ``color``; otherwise tinted
            background at 12% alpha.
    """
    if filled:
        bg = color
        fg = "var(--dps-surface)"
        border = color
    else:
        bg = f"color-mix(in oklab, {color} 12%, transparent)"
        fg = color
        border = f"color-mix(in oklab, {color} 28%, transparent)"
    return (
        f'<span style="display:inline-flex;align-items:center;gap:4px;'
        f"padding:1px 7px;border-radius:3px;font-size:11px;"
        f"font-family:var(--dps-font-mono);font-weight:500;"
        f"color:{fg};background:{bg};border:1px solid {border};"
        f'letter-spacing:0.01em;">{_esc(text)}</span>'
    )


# ──────────────────────────────────────────────────────────────────────
# StageNode — pipeline-spine button
# ──────────────────────────────────────────────────────────────────────


def stage_node(
    *,
    index: int,
    label: str,
    status: StageStatus,
    active: bool,
    evidence: ModelEvidenceTier | str | None = None,
    complete: bool = False,
) -> str:
    """Render one node in the pipeline spine.

    Direction-A spine has 7 of these. Click handling is upstream — the
    caller wraps this in an ``st.button`` or a query-param link. This
    helper renders only the visual.

    Args:
        index: 1-based stage number; shown inside the ring unless
            ``complete=True``, in which case a check mark replaces it.
        label: Stage name (e.g. "M1 — Fabrication").
        status: One of ``pending`` / ``active`` / ``valid`` / ``warn``.
        active: Whether this is the currently focused stage. Drives
            background, border, and label colour. Independent of
            ``status`` so ``active`` highlight can override.
        evidence: Optional evidence tier; renders an inline compact
            badge below the label.
        complete: When ``True``, replace the index with ``✓``.
    """
    c = _STATUS_COLOR.get(status, _STATUS_COLOR["pending"])
    bg = "var(--dps-surface-2)" if active else "transparent"
    border_color = c["ring"] if active else "transparent"
    label_color = "var(--dps-text)" if active else "var(--dps-text-muted)"
    ring_bg = (
        f"color-mix(in oklab, {c['dot']} 18%, transparent)"
        if active
        else "transparent"
    )
    inner = "✓" if complete else str(index)
    badge_html = (
        evidence_badge(evidence, compact=True) if evidence is not None else ""
    )
    return (
        f'<div style="display:flex;align-items:center;gap:10px;'
        f"padding:8px 12px;background:{bg};"
        f"border:1px solid {border_color};border-radius:4px;"
        f"transition:all 150ms ease-out;text-align:left;"
        f'flex:1;min-width:0;">'
        f'<span style="width:22px;height:22px;border-radius:22px;'
        f"border:1.5px solid {c['ring']};display:inline-flex;"
        f"align-items:center;justify-content:center;"
        f"font-family:var(--dps-font-mono);font-size:11px;"
        f"font-weight:600;color:{c['dot']};background:{ring_bg};\">"
        f"{_esc(inner)}</span>"
        f'<span style="display:flex;flex-direction:column;gap:1px;'
        f'min-width:0;">'
        f'<span style="font-size:12.5px;font-weight:600;'
        f'color:{label_color};">{_esc(label)}</span>'
        f"{badge_html}</span></div>"
    )


# ──────────────────────────────────────────────────────────────────────
# card_header_strip — canonical Card header (separate <header> + body)
# ──────────────────────────────────────────────────────────────────────


def card_header_strip(
    *,
    eyebrow_text: str = "",
    title: str = "",
    right_html: str = "",
    badge_html: str = "",
) -> str:
    """Render the canonical Direction-A Card header strip.

    Mirrors the React `Card` component's `<header>` element from
    ``DPSim UI Optimization _standalone_.html``: a horizontal flex row
    with the eyebrow + title on the left and an optional `right` slot
    (Chip / Btn / EvidenceBadge) on the right, separated from the body
    by a 1px border-bottom rule.

    Pair with ``st.container(border=True)`` so the surface chrome comes
    from Streamlit's container border and this strip provides only the
    header content + bottom rule:

        with st.container(border=True):
            st.html(card_header_strip(
                eyebrow_text="Hardware",
                title="Stirred vessel · v9.0 in-M1",
                right_html=chip("tip 0.66 m/s"),
            ))
            # ... body widgets ...

    Use ``card_header_strip`` for new code; the older
    ``section_card_header`` is retained for back-compat with v0.4.13
    call sites.

    Args:
        eyebrow_text: Optional uppercase mono micro-label.
        title: Card title in plain case (14px Geist Sans 600).
        right_html: Optional HTML rendered right-aligned in the header
            row (Chip / Btn / EvidenceBadge / etc).
        badge_html: Optional inline badge in the title row, between
            title and right slot.
    """
    eyebrow_html = eyebrow(eyebrow_text) if eyebrow_text else ""
    title_html = (
        f'<div style="font-size:13.5px;font-weight:600;'
        f'color:var(--dps-text);">{_esc(title)}</div>'
        if title
        else ""
    )
    right_block = ""
    if badge_html or right_html:
        right_block = (
            '<div style="display:flex;align-items:center;gap:8px;'
            'margin-left:auto;">'
            f"{badge_html}{right_html}</div>"
        )
    return (
        '<div style="display:flex;align-items:center;'
        'justify-content:space-between;gap:12px;'
        'margin:-14px -14px 12px -14px;'
        'padding:10px 14px;'
        'border-bottom:1px solid var(--dps-border);">'
        '<div style="display:flex;flex-direction:column;gap:2px;'
        'min-width:0;">'
        f"{eyebrow_html}{title_html}</div>"
        f"{right_block}</div>"
    )


# ──────────────────────────────────────────────────────────────────────
# section_card_header — eyebrow + title + optional trust badge
# ──────────────────────────────────────────────────────────────────────


def section_card_header(
    *,
    eyebrow_text: str,
    title: str,
    badge_html: str = "",
    right_html: str = "",
) -> str:
    """Compose the standard section-card header strip.

    Pattern matches the Direction-A reference: small uppercase mono
    eyebrow above a 14px Geist-Sans title, with an optional trust
    badge (or any HTML) right-aligned in the same row as the title.

    Use inside ``st.container(border=True)`` blocks to wrap subsystem
    forms (Polymer family, Formulation, Crosslinking, Hardware,
    Targets, etc.) so each surface gets the same header rhythm.

    Args:
        eyebrow_text: The uppercase mono micro-label (no need to
            uppercase manually; CSS does it).
        title: The section title in plain case (e.g. "Aqueous polymer
            phase"). Rendered at 14px Geist Sans 600.
        badge_html: Optional HTML for an inline evidence/trust badge
            in the title row. Pass the result of
            ``evidence_badge(tier, compact=True)``.
        right_html: Optional extra HTML at the far right of the title
            row (e.g. a tip-speed pill in the Hardware card).

    Returns:
        Self-contained HTML — emit via ``st.html``.
    """
    eyebrow_html = eyebrow(eyebrow_text)
    title_row_right = ""
    if badge_html or right_html:
        title_row_right = (
            '<div style="display:flex;align-items:center;gap:8px;'
            'margin-left:auto;">'
            f"{badge_html}{right_html}</div>"
        )
    return (
        '<div style="display:flex;flex-direction:column;gap:2px;'
        'margin-bottom:10px;">'
        f"{eyebrow_html}"
        '<div style="display:flex;align-items:center;gap:8px;'
        'min-width:0;">'
        f'<span style="font-size:14px;font-weight:600;'
        f'color:var(--dps-text);line-height:1.25;">{_esc(title)}</span>'
        f"{title_row_right}</div></div>"
    )


# ──────────────────────────────────────────────────────────────────────
# Card — surface with optional header
# ──────────────────────────────────────────────────────────────────────


def card(
    *,
    title: str = "",
    eyebrow_text: str = "",
    right: str = "",
    body: str = "",
    padding: int = 16,
    extra_style: str = "",
) -> str:
    """Render a section/card with optional header strip.

    Args:
        title: Card title (13.5px bold).
        eyebrow_text: Optional uppercase eyebrow above the title.
        right: HTML to render in the top-right header cell (e.g. a
            ``Chip`` or ``EvidenceBadge``).
        body: HTML to render inside the card body.
        padding: Body padding in px (default 16).
        extra_style: Optional CSS to merge onto the outer ``<section>``
            (e.g. ``"grid-column:2;grid-row:1/span 4;"``).
    """
    has_header = bool(title or eyebrow_text or right)
    eyebrow_html = eyebrow(eyebrow_text) if eyebrow_text else ""
    title_html = (
        f'<div style="font-size:13.5px;font-weight:600;'
        f'color:var(--dps-text);">{_esc(title)}</div>'
        if title
        else ""
    )
    header_html = (
        f'<header style="display:flex;align-items:center;'
        f"justify-content:space-between;gap:12px;padding:10px 14px;"
        f'border-bottom:1px solid var(--dps-border);">'
        f'<div style="display:flex;flex-direction:column;gap:2px;'
        f'min-width:0;">{eyebrow_html}{title_html}</div>'
        f"{right}</header>"
        if has_header
        else ""
    )
    return (
        f'<section class="dps-surface" '
        f'style="background:var(--dps-surface);{extra_style}">'
        f"{header_html}"
        f'<div style="padding:{int(padding)}px;">{body}</div>'
        f"</section>"
    )


# ──────────────────────────────────────────────────────────────────────
# MetricValue — numeric value with optional unit + delta
# ──────────────────────────────────────────────────────────────────────


def metric_value(
    value: str,
    *,
    unit: str = "",
    delta: str = "",
    delta_direction: Literal["up", "down", None] = None,
    size: int = 14,
    mono: bool = True,
) -> str:
    """Render a single tabular-numerals metric value.

    Args:
        value: The number as a string (caller controls precision).
        unit: Optional unit suffix (rendered in mono dim).
        delta: Optional change vs previous run (e.g. ``"+2.4 µm"``).
        delta_direction: ``up`` paints green, ``down`` paints red,
            ``None`` paints dim.
        size: Font size in px for the value (default 14).
        mono: Whether to use the mono font family.
    """
    if delta_direction == "up":
        d_color = "var(--dps-green-500)"
        d_glyph = "▲"
    elif delta_direction == "down":
        d_color = "var(--dps-red-600)"
        d_glyph = "▼"
    else:
        d_color = "var(--dps-text-dim)"
        d_glyph = "·"
    mono_class = "dps-mono" if mono else ""
    unit_html = (
        f'<span class="dps-mono" '
        f'style="font-size:11px;color:var(--dps-text-dim);">'
        f"{_esc(unit)}</span>"
        if unit
        else ""
    )
    delta_html = (
        f'<span class="dps-mono" '
        f'style="font-size:11px;color:{d_color};font-weight:500;">'
        f"{d_glyph} {_esc(delta)}</span>"
        if delta
        else ""
    )
    return (
        f'<span style="display:inline-flex;align-items:baseline;gap:4px;">'
        f'<span class="{mono_class}" '
        f'style="font-size:{int(size)}px;font-weight:600;'
        f"color:var(--dps-text);font-variant-numeric:tabular-nums;\">"
        f"{_esc(value)}</span>{unit_html}{delta_html}</span>"
    )


# ──────────────────────────────────────────────────────────────────────
# MiniHistogram — small bar-chart preview (for DSD / etc.)
# ──────────────────────────────────────────────────────────────────────


def mini_histogram(
    bins: Sequence[float],
    *,
    width: int = 200,
    height: int = 60,
    accent: str = "var(--dps-accent)",
) -> str:
    """Render a tiny bar-histogram SVG.

    Used as the M1 bead-size-distribution preview. The caller passes
    pre-computed bin heights; rendering does not interpret them
    quantitatively.

    Args:
        bins: A sequence of bin heights (any positive floats — values
            are normalised to the maximum).
        width: SVG width in px.
        height: SVG height in px.
        accent: Bar fill colour (CSS).
    """
    bins = list(bins) if bins else [0.0]
    max_h = max(bins) or 1.0
    n = len(bins)
    bw = (width - 4) / n
    bars: list[str] = []
    for i, v in enumerate(bins):
        h = v / max_h * (height - 8)
        x = 2 + i * bw
        y = height - 4 - h
        opacity = 0.55 + 0.45 * (v / max_h)
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" '
            f'width="{bw - 1.5:.1f}" height="{h:.1f}" '
            f'fill="{accent}" opacity="{opacity:.2f}"/>'
        )
    baseline = (
        f'<line x1="0" x2="{width}" y1="{height - 4}" y2="{height - 4}" '
        f'stroke="var(--dps-border)" stroke-width="0.5"/>'
    )
    return (
        f'<svg width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" '
        f'style="display:block;">'
        f"{''.join(bars)}{baseline}</svg>"
    )


# ──────────────────────────────────────────────────────────────────────
# Breakthrough — sparkline / breakthrough-curve preview
# ──────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class BreakthroughCurve:
    """Pre-sampled P05/P50/P95 envelope for a column breakthrough plot.

    All three sequences must be the same length and indexed by the
    same dimensionless x-axis (column volumes, CV).

    Attributes:
        x: Dimensionless CV positions in [0, 1].
        p50: Median C/C0 trajectory (same length as ``x``).
        p05: Lower envelope (P05); same length.
        p95: Upper envelope (P95); same length.
    """

    x: Sequence[float]
    p50: Sequence[float]
    p05: Sequence[float]
    p95: Sequence[float]


def _synthetic_breakthrough_curve(n: int = 60) -> BreakthroughCurve:
    """Synthetic sigmoid breakthrough used when no real curve is given."""
    xs = [i / (n - 1) for i in range(n)]
    k, x0 = 12.0, 0.62
    p50 = [1.0 / (1.0 + math.exp(-k * (x - x0))) for x in xs]
    osc = [0.02 * math.sin(i * 0.6) for i in range(n)]
    p05 = [max(0.0, p - 0.06 - osc[i]) for i, p in enumerate(p50)]
    p95 = [min(1.0, p + 0.06 + osc[i]) for i, p in enumerate(p50)]
    return BreakthroughCurve(x=xs, p50=p50, p05=p05, p95=p95)


def breakthrough(
    curve: BreakthroughCurve | None = None,
    *,
    width: int = 320,
    height: int = 86,
    show_axis: bool = True,
    accent: str = "var(--dps-accent)",
    dbc_marker_at: float = 0.55,
    show_pre_pos: bool = True,
) -> str:
    """Render a small breakthrough-curve preview.

    Args:
        curve: Optional pre-sampled envelope. ``None`` → synthetic
            sigmoid for the prototype/empty-state.
        width: SVG width in px.
        height: SVG height in px.
        show_axis: Whether to label C/C₀ and CV axes.
        accent: P50 line + uncertainty-band tint colour.
        dbc_marker_at: x position (0..1) at which to drop the DBC10
            indicator.
        show_pre_pos: When ``True``, label the pre- and post-breakthrough
            ends of the curve (matches the Direction-A reference rail
            chart). PRE = below DBC threshold; POS = past breakthrough.
    """
    c = curve if curve is not None else _synthetic_breakthrough_curve()
    pad_l = 22
    pad_r = 6
    pad_t = 6
    pad_b = 14 if show_axis else 4

    def xs(d: float) -> float:
        return pad_l + d * (width - pad_l - pad_r)

    def ys(v: float) -> float:
        return height - pad_b - v * (height - pad_t - pad_b)

    def path_of(seq: Sequence[float]) -> str:
        parts = []
        for i, x in enumerate(c.x):
            verb = "M" if i == 0 else "L"
            parts.append(f"{verb}{xs(x):.1f},{ys(seq[i]):.1f}")
        return " ".join(parts)

    band_top = " L".join(f"{xs(x):.1f},{ys(c.p95[i]):.1f}" for i, x in enumerate(c.x))
    band_bot = " L".join(
        f"{xs(x):.1f},{ys(c.p05[i]):.1f}" for i, x in reversed(list(enumerate(c.x)))
    )
    band = f"M{band_top} L{band_bot} Z"

    grid: list[str] = []
    for g in (0.0, 0.5, 1.0):
        dasharray = "0" if g == 0.0 else "2 3"
        grid.append(
            f'<line x1="{pad_l}" x2="{width - pad_r}" '
            f'y1="{ys(g):.1f}" y2="{ys(g):.1f}" '
            f'stroke="var(--dps-border)" stroke-width="0.5" '
            f'stroke-dasharray="{dasharray}"/>'
        )

    axis_html = ""
    if show_axis:
        axis_html = (
            f'<text x="{pad_l - 4}" y="{ys(0) + 3:.1f}" '
            f'text-anchor="end" font-size="9" '
            f'fill="var(--dps-text-dim)" '
            f'font-family="var(--dps-font-mono)">0</text>'
            f'<text x="{pad_l - 4}" y="{ys(1) + 3:.1f}" '
            f'text-anchor="end" font-size="9" '
            f'fill="var(--dps-text-dim)" '
            f'font-family="var(--dps-font-mono)">1</text>'
            f'<text x="{pad_l - 4}" y="{(ys(0) + ys(1)) / 2 + 3:.1f}" '
            f'text-anchor="end" font-size="9" '
            f'fill="var(--dps-text-dim)" '
            f'font-family="var(--dps-font-mono)">C/C₀</text>'
            f'<text x="{width - pad_r}" y="{height - 2}" '
            f'text-anchor="end" font-size="9" '
            f'fill="var(--dps-text-dim)" '
            f'font-family="var(--dps-font-mono)">CV</text>'
        )

    dbc_html = (
        f'<line x1="{xs(dbc_marker_at):.1f}" '
        f'x2="{xs(dbc_marker_at):.1f}" '
        f'y1="{ys(0.1):.1f}" y2="{ys(0):.1f}" '
        f'stroke="{accent}" stroke-width="0.8" '
        f'stroke-dasharray="2 2"/>'
        f'<circle cx="{xs(dbc_marker_at):.1f}" '
        f'cy="{ys(0.1):.1f}" r="2.4" fill="{accent}"/>'
    )

    pre_pos_html = ""
    if show_pre_pos:
        # PRE label sits just inside the left edge near the baseline;
        # POS sits just inside the right edge near the plateau. Colour
        # matches the axis-label colour family so they read as labels,
        # not data.
        pre_pos_html = (
            f'<text x="{xs(0.02):.1f}" y="{ys(0.06):.1f}" '
            f'text-anchor="start" font-size="9" font-weight="600" '
            f'fill="var(--dps-text-muted)" '
            f'font-family="var(--dps-font-mono)" '
            f'letter-spacing="0.08em">PRE</text>'
            f'<text x="{xs(0.98):.1f}" y="{ys(0.94):.1f}" '
            f'text-anchor="end" font-size="9" font-weight="600" '
            f'fill="var(--dps-text-muted)" '
            f'font-family="var(--dps-font-mono)" '
            f'letter-spacing="0.08em">POS</text>'
        )

    return (
        f'<svg width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" style="display:block;">'
        f"{''.join(grid)}"
        f'<path d="{band}" fill="{accent}" fill-opacity="0.16"/>'
        f'<path d="{path_of(c.p50)}" fill="none" '
        f'stroke="{accent}" stroke-width="1.5"/>'
        f"{axis_html}{dbc_html}{pre_pos_html}</svg>"
    )


# ──────────────────────────────────────────────────────────────────────
# Convenience: pipeline spine assembly
# ──────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class StageSpec:
    """One stage in the pipeline spine.

    Attributes:
        id: Stable identifier (e.g. ``"m1"``); used as the routing key.
        label: Display label.
        status: Current status (drives colour).
        evidence: Optional inherited evidence tier; rendered as a
            compact badge.
    """

    id: str
    label: str
    status: StageStatus = "pending"
    evidence: ModelEvidenceTier | str | None = None


def pipeline_spine(stages: Iterable[StageSpec], *, active_id: str) -> str:
    """Compose a horizontal pipeline spine from a list of ``StageSpec``.

    Renders N ``stage_node`` cells with ``→`` mono separators between
    them, matching the canonical Direction-A reference layout. Click
    handling is the caller's responsibility (typically a row of
    ``st.button`` overlaid via column layout, with this helper rendering
    the visual chrome behind them).

    Args:
        stages: Ordered list of ``StageSpec``.
        active_id: ``id`` of the stage to highlight as active.
    """
    cells: list[str] = []
    items = list(stages)
    for i, s in enumerate(items):
        is_active = s.id == active_id
        node = stage_node(
            index=i + 1,
            label=s.label,
            status="active" if is_active else s.status,
            active=is_active,
            evidence=s.evidence,
            complete=s.status == "valid",
        )
        cells.append(node)
        if i < len(items) - 1:
            # Mono "→" separator between stage nodes — canonical pattern.
            cells.append(
                '<div style="align-self:center;flex:0 0 auto;'
                "color:var(--dps-text-dim);"
                "font-family:var(--dps-font-mono);"
                'font-size:14px;line-height:1;padding:0 2px;">→</div>'
            )
    return (
        '<nav style="display:flex;align-items:stretch;'
        "padding:10px 16px;gap:4px;"
        "border-bottom:1px solid var(--dps-border);"
        "background:var(--dps-surface);overflow-x:auto;\">"
        f"{''.join(cells)}</nav>"
    )
