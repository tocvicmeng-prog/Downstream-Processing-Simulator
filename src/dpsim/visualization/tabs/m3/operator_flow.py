"""Operator-flow summary for the M3 column-method stage."""

from __future__ import annotations

from typing import Any

import streamlit as st

from dpsim.visualization.components.operator_flow import operator_flow_html


def m3_operator_flow_rows(store: Any) -> list[dict[str, str]]:
    """Return the operator-facing M3 workflow state rows."""

    envelope = store.get("m3_pressure_envelope")
    has_result = any(
        key in store
        for key in (
            "m3_result_bt",
            "m3_result_ge",
            "m3_result_method",
            "m3_result_cat",
        )
    )
    if envelope is None:
        feasibility_state = "pending"
        feasibility_detail = "No pressure envelope cached yet."
    elif getattr(envelope, "is_blocker", False):
        feasibility_state = "blocked"
        feasibility_detail = "Flow exceeds the pressure envelope."
    elif getattr(envelope, "is_warning", False):
        feasibility_state = "warning"
        feasibility_detail = "Flow is close to the pressure envelope."
    else:
        feasibility_state = "ready"
        feasibility_detail = "Pressure envelope is acceptable."

    return [
        {
            "step": "1. Setup",
            "state": "ready",
            "detail": "Column geometry, mobile phase, loading, and elution controls.",
        },
        {
            "step": "2. Feasibility",
            "state": feasibility_state,
            "detail": feasibility_detail,
        },
        {
            "step": "3. Run",
            "state": "ready" if "m2_result" in store else "blocked",
            "detail": "Requires upstream M2 media contract.",
        },
        {
            "step": "4. Decision",
            "state": "ready" if has_result else "pending",
            "detail": "DBC, recovery, pressure, and evidence-tier summary.",
        },
        {
            "step": "5. Diagnostics",
            "state": "ready" if has_result else "pending",
            "detail": "Breakthrough, detector traces, pressure-flow, and warnings.",
        },
        {
            "step": "6. SOP/export",
            "state": "ready" if has_result else "pending",
            "detail": "Use only after evidence and pressure state are reviewed.",
        },
    ]


def render_m3_operator_flow(store: Any | None = None) -> None:
    """Render the M3 setup -> export operator-flow strip."""

    rows = m3_operator_flow_rows(store or st.session_state)
    st.html(operator_flow_html(rows, css_class="dps-m3-flow"))


__all__ = ["m3_operator_flow_rows", "render_m3_operator_flow"]
