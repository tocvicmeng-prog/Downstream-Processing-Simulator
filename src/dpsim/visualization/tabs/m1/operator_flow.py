"""Operator-flow summary for the M1 fabrication stage."""

from __future__ import annotations

from typing import Any

import streamlit as st

from dpsim.visualization.components.operator_flow import operator_flow_html


def m1_operator_flow_rows(store: Any) -> list[dict[str, str]]:
    """Return the operator-facing M1 workflow state rows."""

    has_result = "result" in store
    return [
        {
            "step": "1. Family",
            "state": "ready",
            "detail": "Polymer family selects solver dispatch and downstream support.",
        },
        {
            "step": "2. Hardware",
            "state": "ready",
            "detail": "Vessel, impeller, and speed define the fabrication regime.",
        },
        {
            "step": "3. Formulation",
            "state": "ready",
            "detail": "Polymer, surfactant, gelation, and crosslink settings.",
        },
        {
            "step": "4. Run",
            "state": "ready",
            "detail": "Generates DSD, pore, crosslinking, and mechanics outputs.",
        },
        {
            "step": "5. Release",
            "state": "ready" if has_result else "pending",
            "detail": "Review bead size, pore structure, residuals, and modulus.",
        },
        {
            "step": "6. Handoff",
            "state": "ready" if has_result else "pending",
            "detail": "M1 media contract feeds M2 chemistry and M3 pressure checks.",
        },
    ]


def render_m1_operator_flow(store: Any | None = None) -> None:
    rows = m1_operator_flow_rows(store or st.session_state)
    st.html(operator_flow_html(rows, css_class="dps-stage-flow"))


__all__ = ["m1_operator_flow_rows", "render_m1_operator_flow"]
