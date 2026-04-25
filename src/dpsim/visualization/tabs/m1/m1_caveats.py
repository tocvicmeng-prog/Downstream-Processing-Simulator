"""Wet-lab caveats card for M1 (v0.4.17, milestone P3).

Pre-Run predictive caveats — surfaces blockers and warnings BEFORE the
user clicks Run, so the issue is visible at the point of decision. The
existing ``validate_m1_inputs`` already returns the canonical 9-rule
``ValidationResult``; this module renders that result inside a styled
card matching the Direction-A reference's ``Wet-lab caveats`` /
``CaveatRow`` pattern.

Public API:
    render_m1_caveats_card(validation, *, family, ...): emits a card.
"""

from __future__ import annotations

import html as _html

import streamlit as st

from dpsim.datatypes import PolymerFamily
from dpsim.visualization.design import chrome
from dpsim.visualization.ui_validators import ValidationResult


_LEVEL_COLOR = {
    "blocker": "var(--dps-red-600)",
    "warning": "var(--dps-amber-500)",
    "info": "var(--dps-sky-600)",
}


def _caveat_row_html(level: str, msg: str, cite: str = "") -> str:
    """Render a single caveat row matching the standalone CaveatRow.

    Args:
        level: One of ``"blocker"``, ``"warning"``, ``"info"``.
        msg: Caveat message.
        cite: Optional citation slug rendered as ``↳ {cite}`` underneath.
    """
    color = _LEVEL_COLOR.get(level, _LEVEL_COLOR["info"])
    cite_html = (
        '<div class="dps-mono" style="font-size:11px;'
        f'color:var(--dps-text-dim);margin-top:2px;">↳ {_html.escape(cite)}</div>'
        if cite
        else ""
    )
    return (
        '<div style="display:flex;gap:10px;padding:8px 0;'
        'border-bottom:1px solid var(--dps-border);">'
        '<span class="dps-mono" style="font-size:10px;font-weight:700;'
        f"color:{color};padding:2px 6px;border:1px solid {color};"
        'border-radius:2px;height:fit-content;letter-spacing:0.06em;">'
        f"{level.upper()}</span>"
        '<div style="flex:1;font-size:12.5px;color:var(--dps-text);'
        f'line-height:1.5;">{_html.escape(msg)}{cite_html}</div>'
        "</div>"
    )


def render_m1_caveats_card(
    validation: ValidationResult,
    *,
    family: PolymerFamily,
    crosslinker_key: str = "",
    rpm: float = 0.0,
    T_oil_C: float = 80.0,
    phi_d: float = 0.0,
) -> None:
    """Render the M1 wet-lab-caveats card.

    Composes ``ValidationResult.blockers`` / ``.warnings`` from
    ``validate_m1_inputs`` with a small set of family-aware
    pre-run advisories that are not yet covered by that validator.

    Args:
        validation: Result from ``validate_m1_inputs``.
        family: Active polymer family (drives family-specific advisories).
        crosslinker_key: Active crosslinker key (e.g. "stmp", "genipin").
        rpm: Current stirrer RPM.
        T_oil_C: Current oil temperature [°C].
        phi_d: Current dispersed-phase fraction.
    """
    rows: list[tuple[str, str, str]] = []
    for blocker in validation.blockers:
        rows.append(("blocker", str(blocker), ""))
    for warning in validation.warnings:
        rows.append(("warning", str(warning), ""))

    family_value = getattr(family, "value", family)
    if family_value == PolymerFamily.AGAROSE_CHITOSAN.value and T_oil_C < 58.0:
        rows.append((
            "warning",
            f"Oil temperature {T_oil_C:.0f} °C is below the recommended "
            "T_gel + 20 °C floor (≈ 58 °C for standard agarose). "
            "Gelation may begin before droplet size stabilises.",
            "SA §A · agarose helix-coil kinetics",
        ))
    if 0 < phi_d < 0.05 and rpm > 0:
        rows.append((
            "info",
            f"φ_d = {phi_d:.2f} is low; expect dilute dispersion and "
            "potentially noisy DSD statistics.",
            "",
        ))
    if crosslinker_key == "stmp":
        rows.append((
            "info",
            "STMP crosslinker is selected. Watch for skin-core homogeneity "
            "loss when bead radius exceeds ~500 µm (Thiele modulus > 1). "
            "If predicted d50/2 exceeds 500 µm post-Run, reduce bead size "
            "or shorten Phase B activation.",
            "Appendix J.1.7",
        ))

    n_blockers = sum(1 for r in rows if r[0] == "blocker")
    n_warnings = sum(1 for r in rows if r[0] == "warning")
    if n_blockers > 0:
        chip_color = "var(--dps-red-600)"
        chip_label = f"{n_blockers} blocker{'s' if n_blockers != 1 else ''}"
    elif n_warnings > 0:
        chip_color = "var(--dps-amber-500)"
        chip_label = f"{n_warnings} caveat{'s' if n_warnings != 1 else ''}"
    elif rows:
        chip_color = "var(--dps-sky-600)"
        chip_label = "advisory"
    else:
        chip_color = "var(--dps-green-500)"
        chip_label = "all checks pass"

    with st.container(border=True):
        st.html(
            chrome.card_header_strip(
                eyebrow_text="Wet-lab caveats",
                title="Pre-run validation report",
                right_html=chrome.chip(chip_label, color=chip_color),
            )
        )
        if not rows:
            st.html(
                '<div style="padding:8px 0;font-size:12.5px;'
                'color:var(--dps-text-muted);">'
                "No issues detected by the M1 input validator. Run the "
                "lifecycle to see post-run trust assessment.</div>"
            )
            return
        st.html("".join(_caveat_row_html(level, msg, cite) for level, msg, cite in rows))
