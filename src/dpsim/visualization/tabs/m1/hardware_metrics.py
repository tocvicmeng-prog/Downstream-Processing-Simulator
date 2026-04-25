"""Derived hardware metrics for the M1 Hardware card.

Computes tip speed, Reynolds, and Weber numbers from the live RPM and
the actual ``StirrerGeometry.impeller_diameter``. These are display-only
signals that communicate the shear regime; the L1 PBE solver does its
own (more rigorous) calculation. The values surfaced here use
representative paraffin/W/O properties rather than the standalone's
water-like defaults so the regime classification is meaningful for the
DPSim physics.

Public API:
    HardwareMetricsContext: dataclass with v_tip, Re, We, regime label.
    compute_hardware_metrics(rpm, impeller_diameter_m): pure function.
    render_metrics_rail(ctx): emits the vertical metrics rail HTML.
    render_tip_speed_chip(ctx): inline chip HTML for card headers.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

import streamlit as st

from dpsim.visualization.design import chrome

ShearTier = Literal["low", "medium", "high"]

# Representative continuous-phase properties for paraffin oil at hot
# emulsification (T_oil ≈ 80 °C). Used for display-only Re/We so the
# numbers communicate regime, not solver inputs.
_RHO_OIL_KG_M3 = 850.0
_MU_OIL_PA_S = 5.0e-3
_SIGMA_INTERFACIAL_N_M = 0.025


@dataclass(frozen=True)
class HardwareMetricsContext:
    """Live derived hardware metrics for display in the Hardware card."""

    v_tip: float          # m/s
    reynolds: float       # dimensionless
    weber: float          # dimensionless
    regime: ShearTier     # low / medium / high
    impeller_diameter_mm: float


def compute_hardware_metrics(
    rpm: float,
    impeller_diameter_m: float,
    *,
    rho: float = _RHO_OIL_KG_M3,
    mu: float = _MU_OIL_PA_S,
    sigma: float = _SIGMA_INTERFACIAL_N_M,
) -> HardwareMetricsContext:
    """Compute v_tip, Re, We for a stirred vessel at the given RPM.

    Args:
        rpm: Stirrer speed in revolutions per minute.
        impeller_diameter_m: Impeller diameter in metres.
        rho: Continuous-phase density (kg/m³). Default = paraffin oil.
        mu: Continuous-phase dynamic viscosity (Pa·s). Default at 80 °C.
        sigma: Interfacial tension (N/m). Default for span-80 W/O.

    Returns:
        HardwareMetricsContext with v_tip [m/s], Re, We, and a
        regime classification (low / medium / high) based on tip speed
        thresholds (≈ 0.6 / 1.2 m/s).
    """
    n_rps = max(rpm, 0.0) / 60.0
    d = max(impeller_diameter_m, 1e-9)
    v_tip = math.pi * d * n_rps
    reynolds = rho * n_rps * d * d / mu
    weber = rho * n_rps * n_rps * d * d * d / sigma
    if v_tip < 0.6:
        regime: ShearTier = "low"
    elif v_tip < 1.2:
        regime = "medium"
    else:
        regime = "high"
    return HardwareMetricsContext(
        v_tip=v_tip,
        reynolds=reynolds,
        weber=weber,
        regime=regime,
        impeller_diameter_mm=d * 1000.0,
    )


def render_tip_speed_chip(ctx: HardwareMetricsContext) -> str:
    """Return the inline chip HTML for the Hardware card header right slot.

    Colour follows the regime: low = muted, medium = teal accent,
    high = amber. Use as ``card_header_strip(right_html=...)``.
    """
    color = (
        "var(--dps-amber-500)"
        if ctx.regime == "high"
        else "var(--dps-accent)"
        if ctx.regime == "medium"
        else "var(--dps-text-muted)"
    )
    return chrome.chip(f"tip {ctx.v_tip:.2f} m/s", color=color)


def render_metrics_rail(ctx: HardwareMetricsContext) -> None:
    """Render the vertical derived-metrics rail next to the impeller diagram.

    Three stacked cells: v_tip, Re, We. Tabular-numeric so the values
    align as the slider moves.
    """
    rows = [
        ("v_tip", f"{ctx.v_tip:.2f}", "m/s", "tip speed"),
        ("Re", f"{ctx.reynolds:,.0f}", "", "Reynolds"),
        ("We", f"{ctx.weber:,.0f}", "", "Weber"),
    ]
    cells = []
    for i, (key, value, unit, note) in enumerate(rows):
        unit_html = (
            f'<span class="dps-mono" style="font-size:11px;'
            f'color:var(--dps-text-dim);">{unit}</span>'
            if unit
            else ""
        )
        border_top = (
            "" if i == 0 else "border-top:1px solid var(--dps-border);"
        )
        cells.append(
            '<div style="padding:12px 14px;flex:1;display:flex;'
            f'flex-direction:column;justify-content:center;gap:2px;{border_top}">'
            '<span class="dps-mono" style="font-size:10px;'
            "color:var(--dps-text-dim);text-transform:uppercase;"
            f'letter-spacing:0.04em;">{key}</span>'
            '<div style="display:flex;align-items:baseline;gap:4px;">'
            '<span class="dps-mono" style="font-size:18px;'
            "color:var(--dps-text);font-weight:600;"
            f'font-feature-settings:\'tnum\',\'zero\';">{value}</span>'
            f"{unit_html}</div>"
            '<span style="font-size:10px;color:var(--dps-text-dim);">'
            f"{note}</span></div>"
        )
    st.html(
        '<div style="display:flex;flex-direction:column;'
        "background:var(--dps-surface-2);"
        "border:1px solid var(--dps-border);border-radius:4px;"
        'min-width:130px;height:100%;">'
        + "".join(cells)
        + "</div>"
    )


def render_volumes_readout(
    *,
    v_oil_mL: float,
    v_poly_mL: float,
) -> None:
    """Render the derived Total / phi_d / Oil:Water strip.

    Replaces the previous ``st.caption("Total: 500 mL | phi_d = 0.40")``
    with a richer mono-typed strip that includes the O:W ratio. The
    underlying parameters (v_oil_mL, v_poly_mL) remain the solver inputs
    — this is purely a derived display. The standalone's "Oil:water"
    NumInput is intentionally NOT used: the two volume sliders are the
    actual PBE inputs and replacing them with a ratio would lose the
    individual volume context.
    """
    total = v_oil_mL + v_poly_mL
    phi_d = v_poly_mL / total if total > 0 else 0.0
    o_w_ratio = v_oil_mL / v_poly_mL if v_poly_mL > 0 else float("inf")
    ratio_str = f"{o_w_ratio:.2f}:1" if math.isfinite(o_w_ratio) else "—"
    inversion_warn = (
        '<span style="color:var(--dps-amber-500);margin-left:8px;'
        'font-size:10.5px;">⚠ inversion risk (O:W &lt; 1.5)</span>'
        if 0 < o_w_ratio < 1.5
        else ""
    )
    st.html(
        '<div class="dps-mono" style="display:flex;align-items:center;'
        "gap:14px;padding:6px 10px;margin-top:4px;"
        "background:var(--dps-surface-2);"
        "border:1px solid var(--dps-border);border-radius:3px;"
        'font-size:11px;color:var(--dps-text-muted);">'
        f'<span>Total <span style="color:var(--dps-text);">{total:.0f} mL</span></span>'
        f'<span>φ_d <span style="color:var(--dps-text);">{phi_d:.2f}</span></span>'
        f'<span>O:W <span style="color:var(--dps-text);">{ratio_str}</span></span>'
        f"{inversion_warn}"
        "</div>"
    )
