"""Alginate formulation (v9.0, milestone M5).

Renders ionotropic Ca²⁺ gelation inputs. L3 crosslinking does NOT apply
(ionic gelation IS the crosslinking); orchestrator dispatches to
`_run_alginate` which calls `solve_ionic_ca_gelation`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import streamlit as st

from dpsim.reagent_library import SURFACTANTS
from dpsim.reagent_library_alginate import GELANTS_ALGINATE


@dataclass
class AlginateContext:
    c_alginate_kg_m3: float
    gelant_key: str
    c_Ca_bath_mM: float       # [mol/m³] used when mode=external_bath
    C_Ca_source_mM: float     # [mol/m³] used when mode=internal_release
    k_release_1_s: float      # [1/s]
    T_bath_C: float
    surfactant_key: str
    c_span80_pct: float
    c_span80_vol_pct: float
    T_oil_C: float
    surfactant: Any


def render_formulation_alginate(*, is_stirred: bool) -> AlginateContext:
    """Render alginate + gelant + surfactant inputs."""
    # v0.4.4: alginate formulation widgets migrated to labeled_widget.
    from dpsim.visualization.help import labeled_widget

    # v0.4.14: subheader removed — wrapping card supplies the header.

    c_alginate_pct = labeled_widget(
        "Alginate concentration",
        help="Typical sodium-alginate microsphere recipes: 1–3 % w/v. Drives both viscosity (emulsion stability) and gel modulus.",
        unit="% w/v",
        widget=lambda: st.number_input(
            "Alginate (% w/v)", 0.5, 5.0, 1.5, step=0.1,
            key="m1v9_c_alg", label_visibility="collapsed",
        ),
    )

    gelant_keys = list(GELANTS_ALGINATE.keys())
    gelant_names = [GELANTS_ALGINATE[k].name for k in gelant_keys]
    gel_sel_name = labeled_widget(
        "Gelant",
        help="External bath: pre-formed droplets fall into CaCl₂ (shrinking-core gelation). Internal release: GDL+CaCO₃ dispersed in the alginate phase gives a homogeneous gel.",
        widget=lambda: st.selectbox(
            "Gelant", gelant_names, index=0,
            key="m1v9_alg_gelant", label_visibility="collapsed",
        ),
    )
    gel_sel_key = gelant_keys[gelant_names.index(gel_sel_name)]
    gelant = GELANTS_ALGINATE[gel_sel_key]
    st.caption(f"Mode: {gelant.mode} | T_default={gelant.T_default-273.15:.0f}°C | Suitability: {gelant.suitability}/10")
    from dpsim.visualization.ui_links import build_reagent_link
    st.markdown(
        f"[View mechanism & protocol]({build_reagent_link(key=gel_sel_key, source='alginate_gelants', T_K=gelant.T_default, t_s=gelant.t_default, c_mM=gelant.C_Ca_bath)})"
    )

    if gelant.mode == "external_bath":
        c_Ca_bath_mM = labeled_widget(
            "External CaCl₂ bath",
            help="External calcium bath concentration. Higher [Ca²⁺] gives faster shrinking-core gelation and stiffer beads.",
            unit="mM",
            widget=lambda: st.slider(
                "External CaCl₂ bath (mM)", 20.0, 500.0, float(gelant.C_Ca_bath),
                step=5.0, key="m1v9_c_Ca_bath", label_visibility="collapsed",
            ),
        )
        C_Ca_source_mM = 0.0
        k_release = 0.0
    else:
        c_Ca_bath_mM = 0.0
        C_Ca_source_mM = labeled_widget(
            "Internal Ca²⁺ source",
            help="Equivalent Ca²⁺ release from internal CaCO₃ pre-loading. Drives homogeneous gelation rate.",
            unit="mM",
            widget=lambda: st.slider(
                "Internal Ca²⁺ source (mM, CaCO₃ equivalent)",
                5.0, 100.0, float(gelant.C_Ca_source), step=1.0,
                key="m1v9_C_Ca_source", label_visibility="collapsed",
            ),
        )
        k_release = labeled_widget(
            "GDL release rate k",
            help="GDL hydrolysis rate constant. Controls how fast Ca²⁺ becomes available — sets the homogeneous gelation timescale.",
            unit="1/s",
            widget=lambda: st.number_input(
                "GDL release rate k (1/s)", 1e-5, 1e-2,
                float(gelant.k_release), format="%.1e",
                key="m1v9_k_release", label_visibility="collapsed",
            ),
        )

    T_bath_C = labeled_widget(
        "Bath temperature",
        help="Gelation bath temperature. Affects Ca²⁺ activity, alginate solubility, and gel kinetics.",
        unit="°C",
        widget=lambda: st.slider(
            "Bath temperature (°C)", 4, 80, int(gelant.T_default - 273.15), step=1,
            key="m1v9_T_bath", label_visibility="collapsed",
        ),
    )

    # v0.4.14: surfactant sub-section as a chrome eyebrow.
    from dpsim.visualization.design import chrome as _chrome
    st.html(
        '<div style="margin-top:12px;">'
        + _chrome.eyebrow("Surfactant")
        + '</div>'
    )
    surf_keys = list(SURFACTANTS.keys())
    surf_names = [SURFACTANTS[k].name for k in surf_keys]
    surf_sel_name = labeled_widget(
        "Surfactant",
        help="Surfactant for the W/O emulsion. Span-80 is the standard choice for alginate.",
        widget=lambda: st.selectbox(
            "Surfactant", surf_names, index=surf_keys.index("span80"),
            key="m1v9_alg_surf", label_visibility="collapsed",
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
                key="m1v9_alg_span_vv", label_visibility="collapsed",
            ),
        )
        c_span80_pct = c_span80_vol_pct * 986.0 / 1000.0
        T_oil_C = labeled_widget(
            "Continuous-phase temperature",
            unit="°C",
            widget=lambda: st.slider(
                "Continuous-phase T (°C)", 20, 60, 25, step=1,
                key="m1v9_alg_T_oil", label_visibility="collapsed",
            ),
        )
    else:
        c_span80_pct = labeled_widget(
            "Surfactant",
            unit="% w/v",
            widget=lambda: st.slider(
                "Surfactant (% w/v)", 0.5, 5.0, 2.0, step=0.1,
                key="m1v9_alg_span_wv", label_visibility="collapsed",
            ),
        )
        c_span80_vol_pct = 1.5
        T_oil_C = labeled_widget(
            "Continuous-phase temperature",
            unit="°C",
            widget=lambda: st.slider(
                "Continuous-phase T (°C)", 20, 60, 25, step=1,
                key="m1v9_alg_T_oil_leg", label_visibility="collapsed",
            ),
        )

    return AlginateContext(
        c_alginate_kg_m3=float(c_alginate_pct * 10.0),
        gelant_key=gel_sel_key,
        c_Ca_bath_mM=float(c_Ca_bath_mM),
        C_Ca_source_mM=float(C_Ca_source_mM),
        k_release_1_s=float(k_release),
        T_bath_C=float(T_bath_C),
        surfactant_key=surf_sel_key,
        c_span80_pct=float(c_span80_pct),
        c_span80_vol_pct=float(c_span80_vol_pct),
        T_oil_C=float(T_oil_C),
        surfactant=surf,
    )

