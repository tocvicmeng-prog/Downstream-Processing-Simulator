"""Targets section (v9.0, milestone M4).

Family-aware optimization target inputs (d32 / d_mode / pore / G_DN).
Per SA §E.1 the physical meaning of pore_size differs per family, so the
help text is family-aware while the widget keys are preserved for
session-state compatibility.

M4 extracts the A+C targets from tab_m1.py. M5-M7 will add per-family
label overrides.
"""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from dpsim.datatypes import PolymerFamily


@dataclass
class TargetsContext:
    target_d32: float       # [um] volume-surface mean (legacy mode)
    target_d_mode: float    # [um] modal diameter (stirred-vessel mode)
    target_pore: float      # [nm] pore / mesh / free-volume scale
    target_G: float         # [kPa] target double-network shear modulus


_PORE_HELP = {
    PolymerFamily.AGAROSE_CHITOSAN: "Mean pore size from Cahn-Hilliard or empirical pore model.",
    PolymerFamily.ALGINATE: "Ionic-gel mesh size (gel-front depth at matched t).",
    PolymerFamily.CELLULOSE: "NIPS spinodal wavelength (characteristic pore).",
    PolymerFamily.PLGA: "Glassy polymer free-volume scale (SAXS-equivalent).",
}


def render_targets_section(*, family: PolymerFamily, is_stirred: bool) -> TargetsContext:
    """Render optimization targets.

    Keys preserved from v8.x:
        m1_tgt_d      (stirred vessel d_mode)
        m1_tgt_d32    (legacy d32)
        m1_tgt_pore   (stirred vessel pore)
        m1_tgt_pore_leg (legacy pore)
        m1_tgt_G      (G_DN)
    """
    # v0.4.4: targets section migrated to labeled_widget.
    from dpsim.visualization.help import labeled_widget

    # v0.4.13: subheader removed — wrapping section card supplies the
    # eyebrow + title via chrome.section_card_header.
    pore_help = _PORE_HELP.get(family, "Characteristic pore / mesh size.")
    if is_stirred:
        target_d_mode = labeled_widget(
            "Target d_mode",
            help="Modal (most-frequent) diameter of microspheres. The optimisation drives the predicted distribution toward this value.",
            unit="µm",
            widget=lambda: st.number_input(
                "Target d_mode (um)", 10.0, 500.0, 100.0, step=10.0,
                key="m1_tgt_d", label_visibility="collapsed",
            ),
        )
        target_d32 = target_d_mode
        target_pore = labeled_widget(
            "Target pore size",
            help=pore_help,
            unit="nm",
            widget=lambda: st.number_input(
                "Target Pore Size (nm)", 10, 500, 100, step=10,
                key="m1_tgt_pore", label_visibility="collapsed",
            ),
        )
    else:
        target_d32 = labeled_widget(
            "Target d32",
            help="Sauter (volume-surface) mean diameter — drives the optimisation in the legacy rotor-stator path.",
            unit="µm",
            widget=lambda: st.number_input(
                "Target d32 (um)", 0.5, 50.0, 2.0, step=0.5,
                key="m1_tgt_d32", label_visibility="collapsed",
            ),
        )
        target_d_mode = target_d32
        target_pore = labeled_widget(
            "Target pore size",
            help=pore_help,
            unit="nm",
            widget=lambda: st.number_input(
                "Target Pore Size (nm)", 10, 500, 80, step=10,
                key="m1_tgt_pore_leg", label_visibility="collapsed",
            ),
        )
    target_G = labeled_widget(
        "Target G_DN",
        help="Target double-network shear modulus. Drives the optimisation toward stiffer/softer beads.",
        unit="kPa",
        widget=lambda: st.number_input(
            "Target G_DN (kPa)", 1.0, 500.0, 10.0, step=1.0,
            key="m1_tgt_G", label_visibility="collapsed",
        ),
    )
    return TargetsContext(
        target_d32=target_d32,
        target_d_mode=target_d_mode,
        target_pore=target_pore,
        target_G=target_G,
    )

