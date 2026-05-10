"""M3 result provenance UI helpers."""

from __future__ import annotations

from typing import Any

import streamlit as st

from dpsim.visualization.provenance import (
    build_result_provenance,
    get_result_provenance,
    provenance_summary_html,
    store_result_provenance,
    with_current_recipe_staleness,
)


def store_direct_m3_provenance(recipe: Any, result_key: str, result_obj: Any) -> None:
    """Attach source/freshness metadata to direct M3 session-state results."""

    provenance = build_result_provenance(
        source="direct_m3",
        recipe=recipe,
        result=result_obj,
    )
    store_result_provenance(st.session_state, result_key, provenance)


def render_m3_result_provenance(recipe: Any, result_key: str) -> None:
    """Render source/freshness metadata for a displayed M3 result."""

    provenance = with_current_recipe_staleness(
        get_result_provenance(st.session_state, result_key),
        recipe,
    )
    st.html(provenance_summary_html(provenance))


__all__ = ["render_m3_result_provenance", "store_direct_m3_provenance"]
