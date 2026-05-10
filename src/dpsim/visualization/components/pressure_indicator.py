"""PressureIndicator — digital-style real-time back-pressure readout.

B-3a / W-064 + W-065 (v0.8.5) — UI affordance pinned to the right of the
M3 *Live phase view* column diagram. Reads the active step's
``PressureEnvelope`` and surfaces the current ΔP as a digital number
coloured by headroom band:

* GREEN at ``headroom_ratio < 0.70`` — comfortable cruise.
* AMBER at ``0.70 ≤ headroom_ratio < 1.00`` — approaching ceiling.
* RED at ``headroom_ratio ≥ 1.00`` — operational ceiling exceeded.

The ``?`` popover surfaces (a) the operational ceiling at the active
``decision_tier`` with the tier-aware interval bracket, (b) the
``u_crit · K_geom · G_DN · d_p² / (μ · L)`` calculation summary, and
(c) the four ranked remediations starting with *lower Q to
Q_recommended*. See ``docs/update_workplan_2026-05-10_v0_8_5.md`` §1
for the scientific framing.

Colour values are the existing semantic tokens from ``DESIGN.md`` and
``tab_m3_monitor.py:_STATE_COLORS`` — no new palette entries are
introduced.
"""

from __future__ import annotations

from typing import Any, Final, Literal, Optional

from dpsim.module3_performance.pressure_envelope import PressureEnvelope

_Band = Literal["green", "amber", "red"]


# Mirrors ``tab_m3_monitor._STATE_COLORS``; redefined locally to keep
# the components layer free of upward dependencies on tabs/.
_BAND_COLOR: Final[dict[str, str]] = {
    "green": "#10B981",  # green-500
    "amber": "#F59E0B",  # amber-500
    "red": "#EF4444",    # red-500
}


# Tier-aware interval factors (mirrors
# ``pressure_envelope._INTERVAL_FACTOR_BY_TIER``). The ``?`` popover
# surfaces the bracket so the operator never reads the ceiling as a
# hard truth at SEMI_QUANTITATIVE.
_INTERVAL_FACTOR: Final[dict[str, tuple[float, float]]] = {
    "validated_quantitative": (1.0, 1.0),
    "calibrated_local": (0.80, 1.20),
    "semi_quantitative": (0.50, 2.00),
    "qualitative_trend": (0.25, 4.00),
    "unsupported": (0.10, 10.00),
}


def _band(headroom_ratio: float) -> _Band:
    """Pure mapping: ``< 0.70`` → green, ``< 1.00`` → amber, else red.

    The boundaries match the existing G8 recipe-validation gate
    (``PressureEnvelope.is_warning`` triggers above 0.70;
    ``is_blocker`` triggers above 1.00) and the streaming monitor's
    state colours.
    """
    if headroom_ratio < 0.70:
        return "green"
    if headroom_ratio < 1.00:
        return "amber"
    return "red"


def _resolve_dp(
    envelope: PressureEnvelope, current_dp_pa: Optional[float]
) -> tuple[float, str]:
    """Pick the value to display: live reading if available, else predicted.

    Returns ``(dp_pa, source_label)`` where ``source_label`` is the
    short tag rendered under the digit ("live" or "predicted").
    """
    if current_dp_pa is not None:
        return (float(current_dp_pa), "live")
    return (float(envelope.dP_predicted_pa), "predicted")


def _help_modal_md(envelope: PressureEnvelope) -> str:
    """Compose the ``?`` popover body.

    Surfaces the operational ceiling, the calculation summary, and the
    ranked remediations. Markdown so Streamlit renders it natively
    inside ``st.popover``.
    """
    op_pa = envelope.dP_max_operational_pa
    op_kpa = op_pa / 1.0e3
    tier_value = envelope.decision_tier.value
    lo_f, hi_f = _INTERVAL_FACTOR.get(tier_value, (0.50, 2.00))
    lo_kpa = (op_pa * lo_f) / 1.0e3
    hi_kpa = (op_pa * hi_f) / 1.0e3
    q_rec_ml_min = envelope.Q_recommended_m3_s * 60.0 * 1.0e6
    family = envelope.polymer_family.value

    lines = [
        "### Maximum safe back pressure",
        "",
        f"**{op_kpa:.1f} kPa** (operational ceiling at the current "
        f"decision tier `{tier_value}`).",
        "",
        f"Tier-aware interval: **{lo_kpa:.1f} – {hi_kpa:.1f} kPa**.",
        "",
        "### How this is calculated",
        "",
        "The ceiling is the bed-compression limit derived per ADR-004:",
        "",
        "```",
        "u_crit = K_geom · G_DN · d_p² / (μ · L)",
        "ΔP_max,op = 150 · μ · u_crit · L · (1−ε)² / (ε³ · d_p²) + ΔP_frit",
        "```",
        "",
        f"Resolved values — family `{family}`, "
        f"K_geom source `{envelope.K_geom_source}`, "
        f"u_crit `{envelope.u_crit_m_s:.3e} m/s`, "
        f"Q_max `{envelope.Q_max_m3_s * 60.0 * 1.0e6:.2f} mL/min`.",
        "",
        "Exceeding ΔP_max,op causes **irreversible bed compression**. "
        "The structural burst ceiling (`E_star`) is far higher and is "
        "**not** the operational reference.",
        "",
        "### How to bring back pressure down — ranked by reversibility",
        "",
        f"1. **Lower Q to Q_recommended** "
        f"(≈ {q_rec_ml_min:.2f} mL/min) — restores ~50 % headroom by "
        "definition. First action; fully reversible.",
        "2. **Switch to wash buffer** — reduces μ via mobile-phase "
        "change; only useful when fouling is suspected.",
        "3. **Stop flow and repack column** — when a clogged frit or "
        "channelled bed is suspected.",
        "4. **Emergency stop** — when dΔP/dt rises faster than the "
        "rate threshold (bed about to compress).",
    ]
    return "\n".join(lines)


def _format_dp_with_tier(dp_pa: float, tier_value: str) -> str:
    """W-079 (v0.8.8): tier-aware formatting via the decision-grade policy.

    Uses ``format_decision_graded`` so the SEMI_QUANTITATIVE displayed
    digit carries the tier-aware INTERVAL bracket. Closes audit defect
    A-14 — at v0.8.7 the indicator computed colour-by-headroom but
    bypassed the decision-grade policy ladder.
    """
    try:
        from dpsim.core.decision_grade import OutputType
        from dpsim.datatypes import ModelEvidenceTier
        from dpsim.visualization.decision_grade_render import (
            format_decision_graded,
        )
        # Resolve the tier enum from the value string.
        tier = next(
            (t for t in ModelEvidenceTier if t.value == tier_value),
            ModelEvidenceTier.SEMI_QUANTITATIVE,
        )
        _mode, formatted = format_decision_graded(
            dp_pa,
            OutputType.PRESSURE_DROP,
            tier,
            unit="kPa",
            scale=1.0e-3,
        )
        return formatted
    except Exception:  # noqa: BLE001 — fall back to bare display
        return f"{dp_pa / 1.0e3:.1f} kPa"


def _digit_html(
    *,
    dp_pa: float,
    op_max_pa: float,
    ratio: float,
    band: _Band,
    decision_tier: str,
    source: str,
) -> str:
    """Compose the digital-readout HTML fragment.

    DESIGN.md compliance:
      * Geist Mono, 700 weight, 28 px digit (per "Metric cards" §).
      * Tabular numerals enabled.
      * 4 px border radius, 1 px slate border.
      * No drop shadow, no gradient, no entrance animation.
      * 150 ms ease-out colour transition allowed under §"Motion".
    """
    color = _BAND_COLOR[band]
    dp_kpa = dp_pa / 1.0e3
    op_kpa = op_max_pa / 1.0e3
    headroom_pct = max(0.0, (1.0 - ratio) * 100.0)
    # W-079 (v0.8.8): tier-aware bracket from the decision-grade policy.
    tier_bracket = _format_dp_with_tier(dp_pa, decision_tier)
    return (
        '<div style="'
        'border:1px solid rgba(148,163,184,0.30);'
        'border-radius:4px;'
        'padding:12px 8px;'
        'text-align:center;'
        'font-family:\'Geist Sans\',ui-sans-serif,system-ui,sans-serif;'
        '">'
        '<div style="'
        'font-family:\'Geist Mono\',ui-monospace,SFMono-Regular,monospace;'
        'font-feature-settings:\'tnum\';'
        'font-weight:700;'
        'font-size:28px;'
        'line-height:1.1;'
        f'color:{color};'
        'transition:color 150ms ease-out;'
        '">'
        f'{dp_kpa:.1f}'
        '<span style="font-size:13px;color:rgba(148,163,184,0.85);'
        'margin-left:4px;font-weight:500;">kPa</span>'
        '</div>'
        '<div style="'
        'font-family:\'Geist Mono\',ui-monospace,monospace;'
        'font-feature-settings:\'tnum\';'
        'font-size:10px;'
        'color:rgba(148,163,184,0.85);'
        'margin-top:2px;'
        '">'
        f'tier interval: {tier_bracket}'
        '</div>'
        '<div style="'
        'font-family:\'Geist Mono\',ui-monospace,monospace;'
        'font-feature-settings:\'tnum\';'
        'font-size:11px;'
        'color:rgba(148,163,184,0.85);'
        'margin-top:4px;'
        '">'
        f'headroom {headroom_pct:.0f} % · {source}'
        '</div>'
        '<div style="'
        'font-size:11px;'
        'color:rgba(148,163,184,0.85);'
        'margin-top:6px;'
        'border-top:1px dashed rgba(148,163,184,0.20);'
        'padding-top:6px;'
        '">'
        f'max safe: {op_kpa:.1f} kPa'
        '<br/>'
        f'<span style="font-size:10px;">tier · {decision_tier}</span>'
        '</div>'
        '</div>'
    )


def _placeholder_html() -> str:
    """Render the no-envelope-yet placeholder.

    Surfaces a clearly-labelled state per gate 41 — never a misleading
    zero or NaN.
    """
    return (
        '<div style="'
        'border:1px dashed rgba(148,163,184,0.40);'
        'border-radius:4px;'
        'padding:24px 8px;'
        'text-align:center;'
        'font-family:\'Geist Sans\',ui-sans-serif,system-ui,sans-serif;'
        'font-size:12px;'
        'color:rgba(148,163,184,0.85);'
        '">'
        'Back pressure'
        '<br/>'
        '<span style="font-size:11px;">'
        '(envelope not yet computed —<br/>run the M3 lifecycle first)'
        '</span>'
        '</div>'
    )


def render_pressure_indicator(
    *,
    envelope: Optional[PressureEnvelope],
    current_dp_pa: Optional[float] = None,
    container: Any = None,
    width_px: int = 220,
    height_px: int = 360,
) -> None:
    """Render the digital-style back-pressure indicator.

    Args:
        envelope: Active step's pre-flight envelope. ``None`` before
            the M3 lifecycle has been run — the indicator renders a
            clearly-labelled placeholder in that case.
        current_dp_pa: Latest measured ΔP from the streaming monitor.
            ``None`` outside the offline-replay path; the indicator
            then falls back to ``envelope.dP_predicted_pa``.
        container: Streamlit container to render into. Defaults to the
            module-level ``st`` (the active rerun's root container).
        width_px / height_px: Reserved sizing knobs (currently unused
            by the inline-HTML path; kept in the signature so the
            component can later swap to an iframe asset without an
            API break).
    """
    if container is None:
        import streamlit as st
        container = st

    # Header row: label on the left, "?" popover on the right. Keep the
    # popover in a Streamlit column rather than embedding it in the
    # inline HTML — st.popover renders a real button with proper focus
    # handling that custom HTML cannot replicate.
    cols = container.columns([4, 1])
    cols[0].caption("Back pressure")
    if envelope is not None:
        _pop = cols[1].popover("?", use_container_width=True)
        _pop.markdown(_help_modal_md(envelope))
    else:
        cols[1].caption(":grey[?]")

    if envelope is None:
        container.html(_placeholder_html())
        return

    dp_pa, source = _resolve_dp(envelope, current_dp_pa)
    op_max = envelope.dP_max_operational_pa
    ratio = (dp_pa / op_max) if op_max > 0 else float("inf")
    band = _band(ratio)
    container.html(
        _digit_html(
            dp_pa=dp_pa,
            op_max_pa=op_max,
            ratio=ratio,
            band=band,
            decision_tier=envelope.decision_tier.value,
            source=source,
        )
    )

    # W-091 (v0.8.8): action affordance — when the indicator is amber
    # or red, surface a one-click button that sets the M3 flow rate to
    # Q_recommended. Closes audit defect U-12 / U-23: the streaming
    # monitor's RecoveryAction labels were text-only at v0.8.7; this
    # is the first clickable remediation control. Writing to the
    # widget's session_state key lets the next rerun pick up the
    # value before the widget re-renders.
    if band in ("amber", "red"):
        q_rec_ml_min = float(envelope.Q_recommended_m3_s) * 60.0 * 1.0e6
        try:
            import streamlit as _st_btn
            label = (
                f"⤓ Set Q to Q_recommended ({q_rec_ml_min:.2f} mL/min)"
            )
            if container.button(
                label,
                key="pi_set_q_rec",
                use_container_width=True,
            ):
                _st_btn.session_state["m3_flow"] = float(q_rec_ml_min)
                _st_btn.rerun()
        except Exception:  # noqa: BLE001 — never let action affordance break the page
            pass


__all__ = ["render_pressure_indicator"]
