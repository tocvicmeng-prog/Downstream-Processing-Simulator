"""Operator-flow summary for the M2 functionalisation stage."""

from __future__ import annotations

from typing import Any

import streamlit as st

from dpsim.visualization.components.operator_flow import operator_flow_html


def m2_operator_flow_rows(store: Any) -> list[dict[str, str]]:
    """Return the operator-facing M2 workflow state rows."""

    has_m1 = "result" in store
    has_m2 = "m2_result" in store
    return [
        {
            "step": "1. M1 handoff",
            "state": "ready" if has_m1 else "blocked",
            "detail": "Requires bead DSD, porosity, and modulus from M1.",
        },
        {
            "step": "2. Chemistry",
            "state": "ready" if has_m1 else "pending",
            "detail": "Select activation, spacer, coupling, quench, and wash sequence.",
        },
        {
            "step": "3. Compatibility",
            "state": "ready" if has_m1 else "pending",
            "detail": "Family-reagent matrix gates incompatible or qualitative-only reagents.",
        },
        {
            "step": "4. Run",
            "state": "ready" if has_m1 else "blocked",
            "detail": "Generates ligand density, retained activity, and media contract.",
        },
        {
            "step": "5. Evidence",
            "state": "ready" if has_m2 else "pending",
            "detail": "Review site balance, coupling evidence, and free-protein wash risk.",
        },
        {
            "step": "6. M3 handoff",
            "state": "ready" if has_m2 else "pending",
            "detail": "Functional media contract feeds M3 column operation.",
        },
    ]


def render_m2_operator_flow(store: Any | None = None) -> None:
    rows = m2_operator_flow_rows(store or st.session_state)
    st.html(operator_flow_html(rows, css_class="dps-stage-flow"))


__all__ = ["m2_operator_flow_rows", "render_m2_operator_flow"]
