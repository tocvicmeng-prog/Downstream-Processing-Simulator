"""PLGA formulation (v9.0, milestone M7).

Solvent-evaporation platform (DCM depletion). Orchestrator dispatches to
`_run_plga` which applies the grade preset and calls
`solve_solvent_evaporation`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import streamlit as st

from dpsim.reagent_library import SURFACTANTS
from dpsim.properties.plga_defaults import PLGA_GRADE_PRESETS


@dataclass
class PLGAContext:
    phi_PLGA_0: float
    plga_grade: str
    surfactant_key: str
    c_span80_pct: float
    c_span80_vol_pct: float
    T_oil_C: float
    surfactant: Any


def render_formulation_plga(*, is_stirred: bool) -> PLGAContext:
    """Render PLGA inputs."""
    # v0.4.14: subheader removed — wrapping card supplies the header.

    grade_keys = list(PLGA_GRADE_PRESETS.keys())
    grade_display = {
        "50_50": "PLGA 50:50 (fast release, weeks)",
        "75_25": "PLGA 75:25 (moderate release, months)",
        "85_15": "PLGA 85:15 (slow release, 6-12 mo)",
        "pla": "PLA / PLLA (≥1 year, structural)",
    }
    # v0.4.4: PLGA formulation widgets migrated to labeled_widget.
    from dpsim.visualization.help import labeled_widget

    grade_names = [grade_display.get(k, k) for k in grade_keys]
    grade_sel_name = labeled_widget(
        "PLGA grade",
        help="Grade preset sets D_DCM, T_g, modulus, and degradation timescale. 50:50 is the bioresorbable-pharma standard; 75:25 / 85:15 give slower degradation; PLA-only is non-degradable on bioprocess timescales.",
        widget=lambda: st.selectbox(
            "PLGA grade", grade_names, index=0,
            key="m1v9_plga_grade", label_visibility="collapsed",
        ),
    )
    grade_sel_key = grade_keys[grade_names.index(grade_sel_name)]
    grade = PLGA_GRADE_PRESETS[grade_sel_key]
    st.caption(
        f"L-fraction={grade.L_fraction:.2f} | M_n={grade.M_n:.0f} g/mol | "
        f"T_g={grade.T_g_C:.0f}°C | D_DCM={grade.D_DCM:.1e} m²/s"
    )
    from dpsim.visualization.ui_links import build_reagent_link
    st.markdown(
        f"[View mechanism & protocol]({build_reagent_link(key=grade_sel_key, source='plga_grades')})"
    )

    phi_PLGA_pct = labeled_widget(
        "PLGA in DCM",
        help="Initial PLGA volume fraction in the dispersed (DCM) phase. Higher values give larger, slower-to-form microspheres.",
        unit="% v/v",
        widget=lambda: st.slider(
            "PLGA in DCM (% v/v)", 2.0, 30.0, float(grade.phi_PLGA_0_typical) * 100.0,
            step=0.5, key="m1v9_phi_plga", label_visibility="collapsed",
        ),
    )
    phi_PLGA_0 = phi_PLGA_pct / 100.0

    # v0.4.14: surfactant sub-section as a chrome eyebrow.
    from dpsim.visualization.design import chrome as _chrome
    st.html(
        '<div style="margin-top:12px;">'
        + _chrome.eyebrow("Surfactant · PVA / Span (continuous phase)")
        + '</div>'
    )
    surf_keys = list(SURFACTANTS.keys())
    surf_names = [SURFACTANTS[k].name for k in surf_keys]
    surf_sel_name = labeled_widget(
        "Surfactant",
        help="Surfactant for the W/O emulsion. Span-80 is the standard; PVA stabilises larger droplets.",
        widget=lambda: st.selectbox(
            "Surfactant", surf_names, index=surf_keys.index("span80"),
            key="m1v9_plga_surf", label_visibility="collapsed",
        ),
    )
    surf_sel_key = surf_keys[surf_names.index(surf_sel_name)]
    surf = SURFACTANTS[surf_sel_key]
    st.caption(f"HLB={surf.hlb} | {surf.notes[:60]}")

    if is_stirred:
        c_span80_vol_pct = labeled_widget(
            "Surfactant in oil",
            help="Volume fraction of surfactant in the continuous oil phase.",
            unit="% v/v",
            widget=lambda: st.slider(
                "Surfactant in oil (% v/v)", 0.2, 5.0, 1.5, step=0.1,
                key="m1v9_plga_span_vv", label_visibility="collapsed",
            ),
        )
        c_span80_pct = c_span80_vol_pct * 986.0 / 1000.0
        T_oil_C = labeled_widget(
            "Continuous-phase temperature",
            help="Temperature of the continuous phase during emulsification. PLGA solvent-evaporation is typically run at room temperature (≈25 °C).",
            unit="°C",
            widget=lambda: st.slider(
                "Continuous-phase T (°C)", 15, 40, 25, step=1,
                key="m1v9_plga_T_oil", label_visibility="collapsed",
            ),
        )
    else:
        c_span80_pct = labeled_widget(
            "Surfactant",
            help="Mass fraction of surfactant in the continuous phase.",
            unit="% w/v",
            widget=lambda: st.slider(
                "Surfactant (% w/v)", 0.5, 5.0, 2.0, step=0.1,
                key="m1v9_plga_span_wv", label_visibility="collapsed",
            ),
        )
        c_span80_vol_pct = 1.5
        T_oil_C = labeled_widget(
            "Continuous-phase temperature",
            help="Temperature of the continuous phase. Legacy non-AC path.",
            unit="°C",
            widget=lambda: st.slider(
                "Continuous-phase T (°C)", 15, 40, 25, step=1,
                key="m1v9_plga_T_oil_leg", label_visibility="collapsed",
            ),
        )

    return PLGAContext(
        phi_PLGA_0=float(phi_PLGA_0),
        plga_grade=grade_sel_key,
        surfactant_key=surf_sel_key,
        c_span80_pct=float(c_span80_pct),
        c_span80_vol_pct=float(c_span80_vol_pct),
        T_oil_C=float(T_oil_C),
        surfactant=surf,
    )

