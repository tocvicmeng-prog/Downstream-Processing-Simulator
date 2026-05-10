"""Mobile-phase composition widget.

B-1p / W-053 — v0.8.4. Resolves audit defect C1 (Phase 1 §6).

Renders a 5-field editor for ``MobilePhase`` whose slider domains
mirror the v0.7 viscosity model's ``valid_domain`` exactly so the
widget cannot generate inputs the model rejects.

ADR-005 anchors elution physics to (T, c_NaCl, glycerol, ethanol).
The widget writes ``st.session_state['mobile_phase']`` so every
downstream panel (pre-flight envelope, forward MC, inverse,
multi-column) reads from one source of truth.
"""

from __future__ import annotations

from typing import Any, Optional

import streamlit as st

from dpsim.core.mobile_phase import MobilePhase


_T_C_MIN: float = 0.0
_T_C_MAX: float = 80.0
_C_NACL_MAX_M: float = 0.5
_PHI_GLY_MAX: float = 0.5
_PHI_ETOH_MAX: float = 0.5
_MU_MIN_PA_S: float = 1.0e-4
_MU_MAX_PA_S: float = 1.0e-2


def render_mobile_phase_widget(
    *,
    container: Any = None,
    key_prefix: str = "mp",
    initial: Optional[MobilePhase] = None,
    show_extrapolation_warning: bool = True,
) -> MobilePhase:
    """Render the 5-field mobile-phase composition editor.

    Field domains (mirrors ``core.viscosity.resolve_mobile_phase_viscosity``
    valid_domain):

    * T_C            slider 0–80 °C, default 25
    * c_nacl_M       slider 0.0–0.5 M, default 0.15 (PBS reference)
    * phi_glycerol   slider 0.0–0.5, default 0.0
    * phi_ethanol    slider 0.0–0.5, default 0.0
    * custom_mu_pa_s number input, optional override toggle

    When the user enables ``custom_mu_pa_s``, the widget tags the
    returned ``MobilePhase`` so callers can promote viscosity tier to
    CALIBRATED_LOCAL.

    Parameters
    ----------
    container :
        Streamlit container. Defaults to ``st``.
    key_prefix :
        Namespace for widget keys; lets the same widget render twice
        on different tabs without state collisions.
    initial :
        Optional seed value. Defaults to ``MobilePhase()`` (water at 20 °C).
    show_extrapolation_warning :
        When True, surface a ``st.caption`` if the user crosses the
        viscosity model's recommended sub-domain (|T-25| > 15 °C with
        non-zero glycerol/ethanol — mirrors the additive-model
        extrapolation flag).

    Returns
    -------
    MobilePhase
        Frozen dataclass instance reflecting the current widget state.
    """
    target = container if container is not None else st
    seed = initial or MobilePhase()

    target.markdown("**Mobile phase composition**")
    target.caption(
        "Buffer temperature + solute fractions used by the v0.7 viscosity "
        "model and the pre-flight pressure envelope. Slider domains match "
        "the model's valid_domain — values outside the domain are "
        "physically meaningful but tier-promotion penalties apply."
    )

    cols = target.columns(2)
    t_c = cols[0].slider(
        "Temperature (°C)",
        min_value=_T_C_MIN, max_value=_T_C_MAX,
        value=float(seed.T_C),
        step=0.5,
        key=f"{key_prefix}_T_C",
        help="0–80 °C (CRC water-table domain).",
    )
    c_nacl = cols[1].slider(
        "NaCl (M)",
        min_value=0.0, max_value=_C_NACL_MAX_M,
        value=float(seed.c_nacl_M),
        step=0.005,
        key=f"{key_prefix}_c_nacl",
        help="0–0.5 M (Out & Los 1980 additive coefficient domain).",
    )

    cols2 = target.columns(2)
    phi_gly = cols2[0].slider(
        "Glycerol fraction φ",
        min_value=0.0, max_value=_PHI_GLY_MAX,
        value=float(seed.phi_glycerol),
        step=0.01,
        key=f"{key_prefix}_phi_gly",
        help="0–0.5 v/v (Cheng 2008 glycerol-water domain).",
    )
    phi_etoh = cols2[1].slider(
        "Ethanol fraction φ",
        min_value=0.0, max_value=_PHI_ETOH_MAX,
        value=float(seed.phi_ethanol),
        step=0.01,
        key=f"{key_prefix}_phi_etoh",
        help="0–0.5 v/v (Khattab 2017 ethanol-water domain).",
    )

    use_custom_mu = target.checkbox(
        "Override μ with measured value",
        value=seed.custom_mu_pa_s is not None,
        key=f"{key_prefix}_use_mu",
        help=(
            "Bypass the additive model and use a directly-measured μ. "
            "Promotes viscosity tier to CALIBRATED_LOCAL."
        ),
    )
    custom_mu: Optional[float] = None
    if use_custom_mu:
        seed_mu = (
            float(seed.custom_mu_pa_s) if seed.custom_mu_pa_s is not None
            else 1.0e-3
        )
        custom_mu = target.number_input(
            "Custom μ (Pa·s)",
            min_value=_MU_MIN_PA_S, max_value=_MU_MAX_PA_S,
            value=seed_mu, step=1.0e-4, format="%.4f",
            key=f"{key_prefix}_mu_value",
        )

    # Extrapolation warning — mirrors the additive-model heuristic in
    # core/viscosity.py (|T-25| > 15 °C with non-zero glycerol/ethanol).
    if show_extrapolation_warning:
        out_of_band = abs(t_c - 25.0) > 15.0 and (phi_gly > 0.0 or phi_etoh > 0.0)
        if out_of_band:
            target.caption(
                "⚠ Outside the additive viscosity model's recommended "
                "sub-domain (|T-25| > 15 °C with non-zero glycerol or "
                "ethanol). The model still runs but tier rolls down."
            )

    return MobilePhase(
        T_C=float(t_c),
        c_nacl_M=float(c_nacl),
        phi_glycerol=float(phi_gly),
        phi_ethanol=float(phi_etoh),
        custom_mu_pa_s=custom_mu,
    )


__all__ = ["render_mobile_phase_widget"]
