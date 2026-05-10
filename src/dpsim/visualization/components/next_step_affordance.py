"""Post-lifecycle "what's next" affordance.

B-2u / W-063 — v0.8.4. Resolves audit defect W-2 (Phase 1 §6).

Renders a 3-button strip after the M3 breakthrough panel suggesting
the three obvious next operations once a lifecycle run completes:

1. **Run forward MC** — surface tail-probability advisory at a tighter
   confidence than the deterministic envelope. Jumps to the
   forward_mc sub-tab of the Calibration & Uncertainty stage.
2. **Fit posterior K_geom** — open the inverse Bayesian inference
   panel and feed it measured (Q, ΔP) data. Jumps to the inverse
   sub-tab.
3. **Build series geometry** — author a multi-column series. Jumps
   to the multi_column sub-tab.

Each button writes ``st.session_state['_jump_to_calibration_section']``
to one of {"forward_mc", "inverse", "multi_column"}; the
``tab_calibration`` dispatcher honours the flag on first render and
clears it (one-shot read-and-clear).
"""

from __future__ import annotations

from typing import Any, Optional

import streamlit as st


def render_next_step_affordance(
    *,
    container: Any = None,
    key_prefix: str = "nxt",
    lifecycle_result: Optional[Any] = None,
) -> None:
    """Render the 3-button "what's next" strip.

    Renders only when ``lifecycle_result`` is non-None (silently
    no-op otherwise — there is no useful affordance until a run
    completes).
    """
    target = container if container is not None else st

    if lifecycle_result is None:
        return

    target.markdown("---")
    target.markdown("**What's next?**")
    target.caption(
        "The lifecycle run completed. Three operations are typically "
        "useful from here — switch to the Calibration & Uncertainty "
        "stage to run them."
    )
    cols = target.columns(3)

    if cols[0].button(
        "Run forward MC",
        key=f"{key_prefix}_fmc",
        help=(
            "Propagate lognormal priors on K_geom / μ / G_DN and surface "
            "the p_blocker tail probability before risky operating "
            "decisions."
        ),
    ):
        st.session_state["_jump_to_calibration_section"] = "forward_mc"

    if cols[1].button(
        "Fit posterior K_geom",
        key=f"{key_prefix}_inv",
        help=(
            "Importance-sample a posterior over (K_geom, μ, G_DN) given "
            "measured (Q, ΔP) data. Round-trip log_cov into forward MC."
        ),
    ):
        st.session_state["_jump_to_calibration_section"] = "inverse"

    if cols[2].button(
        "Build series geometry",
        key=f"{key_prefix}_mcg",
        help=(
            "Add a polish (or capture) column in series with the current "
            "column and inspect the rolled-up envelope."
        ),
    ):
        st.session_state["_jump_to_calibration_section"] = "multi_column"


__all__ = ["render_next_step_affordance"]
