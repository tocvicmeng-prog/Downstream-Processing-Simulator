"""Calibration & Uncertainty top-level tab.

B-2s / W-059 — v0.8.4. Resolves audit defects C3, C4, C5, C6.

This tab is a peer to M1, M2, M3 in the dashboard's top-level tab
strip. It hosts four sub-sections, each documented in the audit's
defect catalogue:

* Forward MC envelope (W-059 / C3) — `tabs/calibration/forward_mc.py`
* Inverse Bayesian inference (W-060 / C4) — `tabs/calibration/inverse_inference.py`
* Multi-column series builder (W-061 / C5) — `tabs/calibration/multi_column.py`
* Wet-lab calibration ingestion (W-057 / C6) — `tabs/calibration/wetlab_ingestion.py`

Sub-section dispatch is via `st.tabs(...)`. The next-step affordance
(W-063) on the M3 tab can write
``st.session_state['_jump_to_calibration_section']`` to one of
{"forward_mc", "inverse", "multi_column"}; this dispatcher honours
the flag on first render then clears it (one-shot read-and-clear).
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from dpsim.core.mobile_phase import MobilePhase


_SECTION_NAMES: tuple[str, ...] = (
    "Uncertainty MC",
    "Inverse calibration",
    "Series design",
    "Wet-lab calibration",
)
_SECTION_KEYS: tuple[str, ...] = (
    "forward_mc",
    "inverse",
    "multi_column",
    "wetlab",
)


def _resolve_inputs_from_session() -> tuple[Any, Any]:
    """Pull (forward_mc_inputs, inverse_inputs) from session state.

    Returns (None, None) when the lifecycle has not been run yet —
    the sub-panels render their own "run lifecycle first" info banners.
    """
    lifecycle_result = st.session_state.get("lifecycle_result")
    if lifecycle_result is None:
        return None, None

    envelope = getattr(lifecycle_result, "pressure_envelope", None)
    if envelope is None:
        return None, None

    column = getattr(envelope, "_column", None)
    # PressureEnvelope echoes its inputs but not the original column;
    # try to recover from session state populated by tab_m3.
    if column is None:
        column = st.session_state.get("_m3_column_for_envelope")

    mobile_phase = (
        st.session_state.get("mobile_phase") or MobilePhase()
    )
    Q_set = float(getattr(envelope, "Q_set_m3_s", 0.0))
    polymer_family = getattr(envelope, "polymer_family", None)

    if column is None or polymer_family is None or Q_set <= 0.0:
        return None, None

    from dpsim.visualization.tabs.calibration.forward_mc import (
        ForwardMCRunInputs,
    )
    from dpsim.visualization.tabs.calibration.inverse_inference import (
        InverseRunInputs,
    )

    forward = ForwardMCRunInputs(
        polymer_family=polymer_family,
        column=column,
        mobile_phase=mobile_phase,
        Q_set_m3_s=Q_set,
    )
    inverse = InverseRunInputs(
        polymer_family=polymer_family,
        column=column,
        mobile_phase=mobile_phase,
        Q_for_envelope=Q_set,
    )
    return forward, inverse


def render_tab_calibration() -> None:
    """Top-level Calibration & Uncertainty tab.

    Dispatches to four sub-sections via st.tabs(). Honours the
    next-step jump flag from the M3 tab.
    """
    st.header("Calibration & Uncertainty")
    st.caption(
        "Calibration data, uncertainty propagation, inverse posterior "
        "fitting, and design-time series checks. The bands in this tab "
        "respect ADR-010 §Tier mapping — they stay SEMI_QUANTITATIVE "
        "until the wet-lab YAML handshake promotes them. Series design "
        "is labelled separately because it is not itself a calibration task."
    )

    # Honour the M3 next-step jump flag (one-shot).
    jump_target = st.session_state.pop("_jump_to_calibration_section", None)
    default_index = 0
    if jump_target in _SECTION_KEYS:
        default_index = _SECTION_KEYS.index(jump_target)

    tabs = st.tabs(list(_SECTION_NAMES))
    forward_inputs, inverse_inputs = _resolve_inputs_from_session()

    # Sub-section 0 — Forward MC.
    with tabs[0]:
        if default_index == 0:
            st.caption("(jumped from the M3 next-step affordance)")
        from dpsim.visualization.tabs.calibration.forward_mc import (
            render_forward_mc_panel,
        )
        render_forward_mc_panel(inputs=forward_inputs)

    # Sub-section 1 — Inverse posterior.
    with tabs[1]:
        if default_index == 1:
            st.caption("(jumped from the M3 next-step affordance)")
        from dpsim.visualization.tabs.calibration.inverse_inference import (
            render_inverse_inference_panel,
        )
        render_inverse_inference_panel(inputs=inverse_inputs)

    # Sub-section 2 — Multi-column series.
    with tabs[2]:
        # W-085 (v0.8.8): clarifying caption — multi-column is a
        # design-time tool, not a calibration activity. Per audit
        # defect A-16 / U-18. Full IA hoist into a dedicated *Series
        # Design* stage is queued for the v1.0 IA refactor; for
        # v0.8.8 the caption corrects the misleading-by-placement
        # framing.
        st.warning(
            ":material/architecture: **Design-time tool** — this is the "
            "multi-column series envelope builder, not a calibration "
            "activity. Use it during column-train layout planning. "
            "(IA hoist into a dedicated *Series Design* stage is queued "
            "for v1.0 per the joint plan §3 Bundle Z.)"
        )
        if default_index == 2:
            st.caption("(jumped from the M3 next-step affordance)")
        try:
            from dpsim.visualization.tabs.calibration.multi_column import (
                render_multi_column_builder,
            )
            render_multi_column_builder()
        except ImportError:
            # B-2t hasn't shipped yet at the time of B-2s — defensive.
            st.info(
                "Multi-column series builder lands at B-2t. Stub for now."
            )

    # Sub-section 3 — Wet-lab ingestion.
    with tabs[3]:
        from dpsim.visualization.tabs.calibration.wetlab_ingestion import (
            render_wetlab_ingestion_panel,
        )
        render_wetlab_ingestion_panel()

        # W-089 (v0.8.8): spreadsheet (CSV / XLSX) calibration import
        # with column-mapping wizard. Closes audit defect U-19 / S-18.
        st.divider()
        from dpsim.visualization.panels import (
            render_spreadsheet_calibration_import_panel,
        )
        render_spreadsheet_calibration_import_panel()


__all__ = ["render_tab_calibration"]
