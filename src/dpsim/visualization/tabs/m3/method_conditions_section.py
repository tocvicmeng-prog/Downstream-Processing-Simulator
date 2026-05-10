"""M3 *Method conditions* section — mobile phase + isotherm widgets.

W-087 (v0.8.9) — proof-of-pattern extraction from ``tab_m3.py``. The
audit defect A-18 flagged ``tab_m3.py`` at 1198 LOC as too large; this
file pulls one cohesive section out into its own module to validate
the refactor pattern before the v1.0 full split. The behaviour is
unchanged — the function is called from the same point in the M3 tab.
"""

from __future__ import annotations

from typing import Any


def render_method_conditions_section(*, container: Any) -> None:
    """Render the mobile-phase + isotherm method-conditions card.

    B-4a + B-4b (W-069 + W-070, v0.8.6): mount the mobile-phase
    composition editor + isotherm selector. The v0.8.4 widgets
    were defined and unit-tested but never mounted in production —
    AUDIT_v0_8_5_e2e_phase3_architecture.md §A-1, §A-2. Mounting
    here threads user choices into st.session_state so the
    pre-flight envelope and the lifecycle invocation honour them.

    W-087 (v0.8.9): extracted into this module from tab_m3.py.
    """
    import streamlit as st
    from dpsim.datatypes import PolymerFamily
    from dpsim.visualization.design import chrome as _chrome
    from dpsim.visualization.panels.isotherm_selector import (
        render_isotherm_widget,
    )
    from dpsim.visualization.panels.mobile_phase import (
        render_mobile_phase_widget,
    )

    with container.container(border=True):
        st.html(
            _chrome.card_header_strip(
                eyebrow_text="Method conditions",
                title="Mobile phase + isotherm",
                right_html=_chrome.chip(
                    "drives pressure envelope + breakthrough",
                    color="var(--dps-text-muted)",
                ),
            )
        )
        _mp_user = render_mobile_phase_widget(
            key_prefix="m3_mp",
            initial=st.session_state.get("m3_mobile_phase"),
        )
        st.session_state["m3_mobile_phase"] = _mp_user

        # Resolve the polymer family for family-aware isotherm default
        # routing. Fall back to AGAROSE before M2 has run.
        _fam_for_iso = PolymerFamily.AGAROSE
        _m2r_iso = st.session_state.get("m2_result")
        if _m2r_iso is not None:
            _candidate = getattr(_m2r_iso, "polymer_family", None)
            if _candidate is None:
                _m1_contract = getattr(_m2r_iso, "m1_contract", None)
                _candidate = getattr(_m1_contract, "polymer_family", None)
            if isinstance(_candidate, PolymerFamily):
                _fam_for_iso = _candidate
        _iso_spec_user = render_isotherm_widget(
            key_prefix="m3_iso",
            polymer_family=_fam_for_iso,
            initial=st.session_state.get("m3_isotherm_spec"),
        )
        st.session_state["m3_isotherm_spec"] = _iso_spec_user


__all__ = ["render_method_conditions_section"]
