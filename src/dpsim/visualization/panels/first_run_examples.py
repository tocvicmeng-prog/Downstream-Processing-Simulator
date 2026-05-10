"""First-run example loader — three canonical recipes.

W-097 / v0.8.8 — closes audit defect U-1 / U-15 / S-15 / S-19 from the
v0.8.5 audit phases. Bench users firing up DPSim for the first time
have no on-ramp; the dashboard is data-rich but doesn't say *"start
here"*. This panel surfaces three canonical recipes with one-click
load:

* **Protein A capture** — AGAROSE_CHITOSAN base, ProteinA isotherm,
  PBS load + low-pH elute.
* **IEX polish** — ALGINATE base, salt-modulated Langmuir,
  load → wash → salt-step gradient.
* **IMAC capture** — AGAROSE base, imidazole-modulated Langmuir,
  load → wash → imidazole step.

Each click writes the appropriate session_state keys so the dashboard
populates with a wet-lab-realistic starting point. The user can then
modify and Run.

Mounted in the sidebar above the Sessions panel so it is the first
thing a fresh dashboard shows.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from dpsim.core.mobile_phase import MobilePhase
from dpsim.datatypes import ModelEvidenceTier
from dpsim.visualization.panels.isotherm_selector import (
    IsothermChoice,
    IsothermSpec,
)


def _apply_protein_a_capture() -> None:
    """Canonical Protein A IgG capture recipe."""
    st.session_state["m3_mobile_phase"] = MobilePhase(
        T_C=22.0, c_nacl_M=0.15, phi_glycerol=0.0, phi_ethanol=0.0,
    )
    st.session_state["m3_isotherm_spec"] = IsothermSpec(
        choice=IsothermChoice.PROTEIN_A,
        params={
            "q_max_mol_m3": 60.0,
            "K_a_max_m3_mol": 1.0e5,
            "pH_transition": 3.5,
            "steepness": 5.0,
            "calibrated_locally": False,
        },
        estimated_tier=ModelEvidenceTier.SEMI_QUANTITATIVE,
    )
    # Geometry + flow defaults — typical lab Protein A column.
    st.session_state["m3_col_d"] = 11.0       # mm
    st.session_state["m3_bed_h"] = 10.0       # cm
    st.session_state["m3_eps_b"] = 0.38
    st.session_state["m3_flow"] = 1.0          # mL/min
    # Polymer family hint via M2 result — but if no M2 yet, the
    # widget falls back to AGAROSE; user can re-pick AGAROSE_CHITOSAN
    # in M1.
    st.toast(
        "Loaded: Protein A capture · MabSelect-class column · 1 mL/min",
        icon=":material/check_circle:",
    )


def _apply_iex_polish() -> None:
    """Canonical IEX polish recipe with salt-modulated Langmuir."""
    st.session_state["m3_mobile_phase"] = MobilePhase(
        T_C=22.0, c_nacl_M=0.025, phi_glycerol=0.0, phi_ethanol=0.0,
    )
    st.session_state["m3_isotherm_spec"] = IsothermSpec(
        choice=IsothermChoice.SALT_MODULATED_LANGMUIR,
        params={
            "q_max_mol_m3": 100.0,
            "K_L_m3_mol": 5.0e3,
            "nu": 4.5,
            "c_salt_ref_mol_m3": 150.0,
            "calibrated_locally": False,
        },
        estimated_tier=ModelEvidenceTier.SEMI_QUANTITATIVE,
    )
    st.session_state["m3_col_d"] = 16.0
    st.session_state["m3_bed_h"] = 15.0
    st.session_state["m3_eps_b"] = 0.40
    st.session_state["m3_flow"] = 2.5
    st.toast(
        "Loaded: IEX polish · Q-class column · low-salt load → salt step",
        icon=":material/check_circle:",
    )


def _apply_imac_capture() -> None:
    """Canonical IMAC capture recipe (His-tagged protein on Ni-NTA)."""
    st.session_state["m3_mobile_phase"] = MobilePhase(
        T_C=22.0, c_nacl_M=0.5, phi_glycerol=0.0, phi_ethanol=0.0,
    )
    st.session_state["m3_isotherm_spec"] = IsothermSpec(
        choice=IsothermChoice.IMIDAZOLE_MODULATED_LANGMUIR,
        params={
            "q_max_mol_m3": 80.0,
            "K_L_m3_mol": 1.0e4,
            "n": 1.5,
            "c_imidazole_ref_mol_m3": 50.0,
            "calibrated_locally": False,
        },
        estimated_tier=ModelEvidenceTier.SEMI_QUANTITATIVE,
    )
    st.session_state["m3_col_d"] = 11.0
    st.session_state["m3_bed_h"] = 8.0
    st.session_state["m3_eps_b"] = 0.38
    st.session_state["m3_flow"] = 1.0
    st.toast(
        "Loaded: IMAC capture · Ni-NTA · 50 → 250 mM imidazole step",
        icon=":material/check_circle:",
    )


_RECIPE_LOADERS: dict[str, Any] = {
    "protein_a": _apply_protein_a_capture,
    "iex_polish": _apply_iex_polish,
    "imac": _apply_imac_capture,
}


def render_first_run_examples_panel(*, container: Any = None) -> None:
    """Render three canonical-recipe load buttons.

    W-097 (v0.8.8). Place in the sidebar near the top so first-run
    users see an obvious on-ramp.
    """
    target = container if container is not None else st.sidebar

    target.divider()
    target.markdown("**:material/lightbulb: First-run examples**")
    target.caption(
        "One-click load wet-lab-realistic starting points. Modifies "
        "the M3 method-conditions inputs; re-run to see the effect."
    )

    if target.button(
        "Protein A capture (IgG)", key="ex_protein_a",
        use_container_width=True,
        help="MabSelect-class column · neutral PBS load · low-pH elute",
    ):
        _apply_protein_a_capture()
        try:
            st.rerun()
        except Exception:  # noqa: BLE001
            pass

    if target.button(
        "IEX polish (Q-class)", key="ex_iex_polish",
        use_container_width=True,
        help="Salt-modulated Langmuir · 25 mM load → 1 M elute",
    ):
        _apply_iex_polish()
        try:
            st.rerun()
        except Exception:  # noqa: BLE001
            pass

    if target.button(
        "IMAC capture (His-tag)", key="ex_imac",
        use_container_width=True,
        help="Imidazole-modulated · 50 → 250 mM imidazole gradient",
    ):
        _apply_imac_capture()
        try:
            st.rerun()
        except Exception:  # noqa: BLE001
            pass


__all__ = ["render_first_run_examples_panel"]
