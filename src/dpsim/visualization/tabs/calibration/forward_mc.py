"""Forward Monte Carlo pressure-envelope UI panel.

B-2s / W-059 — v0.8.4. Resolves audit defect C3 (Phase 1 §6).

Surfaces the v0.8.2 ADR-007 forward MC machinery as a runnable UI
panel. The headline output is the ``p_blocker`` tail probability — the
README's central pre-flight risk advisory. The 3-band ladder
(GREEN < 0.01, AMBER 0.01–0.05, RED ≥ 0.05) mirrors the streaming
monitor's state-chip vocabulary so users learn one visual grammar.

Per ADR-011, the panel exposes an opt-in ``log_cov`` correlated-prior
toggle that consumes ``st.session_state['posterior_log_cov']`` when
the inverse-inference panel has populated it (the round-trip).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import numpy as np
import streamlit as st

from dpsim.core.decision_grade import OutputType
from dpsim.core.mobile_phase import MobilePhase
from dpsim.datatypes import ModelEvidenceTier, PolymerFamily
from dpsim.module3_performance.hydrodynamics import ColumnGeometry
from dpsim.module3_performance.pressure_envelope_mc import (
    MCEnvelopeBands,
    monte_carlo_pressure_envelope,
)
from dpsim.visualization.decision_grade_render import render_metric


_P_BLOCKER_GREEN_THRESHOLD: float = 0.01
_P_BLOCKER_RED_THRESHOLD: float = 0.05


@dataclass(frozen=True)
class ForwardMCRunInputs:
    """Bundle of inputs the forward-MC panel consumes from session state."""

    polymer_family: PolymerFamily
    column: ColumnGeometry
    mobile_phase: MobilePhase
    Q_set_m3_s: float


def _render_p_blocker_chip(
    container: Any, p_blocker: float, q_recommended: float,
) -> None:
    """3-band advisory chip + 'drop Q' callout."""
    if not np.isfinite(p_blocker):
        container.info("p_blocker = N/A (no finite-headroom draws).")
        return
    if p_blocker < _P_BLOCKER_GREEN_THRESHOLD:
        container.success(
            f"**p_blocker = {p_blocker*100:.1f} %** — operating point is "
            "comfortably inside the envelope under the prior."
        )
    elif p_blocker < _P_BLOCKER_RED_THRESHOLD:
        container.warning(
            f"**p_blocker = {p_blocker*100:.1f} %** — at-risk band. "
            f"Consider dropping Q to Q_recommended "
            f"({q_recommended*1.0e6*60.0:.2f} mL/min)."
        )
    else:
        container.error(
            f"**p_blocker = {p_blocker*100:.1f} % ≥ 5 %** — strong signal "
            f"to drop Q to Q_recommended "
            f"({q_recommended*1.0e6*60.0:.2f} mL/min). The README's "
            "operational guardrail anchors at 5 %."
        )


def render_forward_mc_panel(
    *,
    container: Any = None,
    key_prefix: str = "fmc",
    inputs: Optional[ForwardMCRunInputs] = None,
) -> Optional[MCEnvelopeBands]:
    """Render the forward-MC sub-section of the calibration tab.

    When ``inputs`` is None the panel renders an info banner asking
    the user to run the lifecycle first (so that Q_set + column +
    mobile_phase are all populated). Otherwise, the panel exposes
    n_samples / seed / prior-mode / log_cov controls + a Run button.

    The result is cached on ``st.session_state['forward_mc_bands']`` so
    a re-render of the page does not re-run the simulation.
    """
    target = container if container is not None else st

    target.subheader("Forward Monte Carlo pressure envelope")
    target.caption(
        "Propagates lognormal priors on K_geom / μ / G_DN through the "
        "pre-flight envelope. Reports P05/P50/P95 bands + the p_blocker "
        "tail probability — the README's pre-flight risk advisory."
    )

    if inputs is None:
        target.info(
            "Run the lifecycle first (M1 → M2 → M3) so Q_set + column "
            "geometry + mobile-phase are populated. Once a "
            "PressureEnvelope is on the result, this panel becomes "
            "active."
        )
        return None

    # B-5e (W-077, v0.8.7): single-step vs multi-step coupled MC mode.
    # Multi-step wires monte_carlo_step_program (B-2r / W-050) — draws
    # once and evaluates every step under shared draws so cross-step
    # correlations are preserved. Closes audit defect S-9 / A-8.
    mc_mode = target.radio(
        "MC mode",
        options=["single-step", "multi-step coupled"],
        index=0,
        horizontal=True,
        key=f"{key_prefix}_mcmode",
        help=(
            "single-step: classic forward MC at the current Q_set. "
            "multi-step coupled (B-2r / W-050): shared parameter draws "
            "across a 3-step program (equilibrate / load / wash) so "
            "cross-step correlation is preserved. The worst-step "
            "blocker probability becomes the headline."
        ),
    )

    cols = target.columns(3)
    n_samples = cols[0].slider(
        "Sample count",
        min_value=50, max_value=5000, value=500, step=50,
        key=f"{key_prefix}_n",
        help="500 is the empirical sweet spot for ±2 % stable p_blocker.",
    )
    seed = cols[1].number_input(
        "RNG seed", min_value=0, max_value=2**31 - 1, value=42, step=1,
        key=f"{key_prefix}_seed",
    )
    prior_mode = cols[2].radio(
        "Prior mode",
        options=["literature default", "family priors"],
        index=0,
        key=f"{key_prefix}_priormode",
        help=(
            "literature default → ADR-007 σ_log defaults; family priors "
            "→ FamilyMCPrior registry."
        ),
    )

    use_log_cov = False
    posterior_log_cov = st.session_state.get("posterior_log_cov")
    if posterior_log_cov is not None:
        use_log_cov = target.checkbox(
            "Consume posterior log_cov from inverse-inference round-trip",
            value=False,
            key=f"{key_prefix}_uselogcov",
            help=(
                "Use the 3×3 posterior covariance over (K_geom, μ, G_DN) "
                "instead of the diagonal lognormal priors. Tighter "
                "predictive intervals at the operating point."
            ),
        )

    run = target.button(
        "Run forward MC",
        key=f"{key_prefix}_run",
        type="primary",
    )

    bands_in_state = st.session_state.get("forward_mc_bands")
    if not run and bands_in_state is None:
        return None

    if run:
        # B-5e (W-077, v0.8.7): branch on MC mode. Multi-step uses
        # monte_carlo_step_program with shared parameter draws across
        # a 3-step program (equilibrate / load / wash) — closes
        # audit defect S-9 / A-8.
        try:
            if mc_mode == "multi-step coupled":
                from dataclasses import dataclass as _dc
                from dpsim.module3_performance.pressure_envelope_mc import (
                    monte_carlo_step_program,
                )

                @_dc(frozen=True)
                class _LightweightStep:
                    """Duck-typed PressureStep for monte_carlo_step_program.

                    Has the (name, Q_m3_s, mobile_phase) attributes the
                    function requires; avoids the hard dependency on
                    ``optimization.objectives.PressureStep`` per the
                    docstring's typed-loosely guidance.
                    """
                    name: str
                    Q_m3_s: float
                    mobile_phase: Any

                step_program = (
                    _LightweightStep(
                        name="equilibrate",
                        Q_m3_s=float(inputs.Q_set_m3_s) * 0.5,
                        mobile_phase=inputs.mobile_phase,
                    ),
                    _LightweightStep(
                        name="load",
                        Q_m3_s=float(inputs.Q_set_m3_s),
                        mobile_phase=inputs.mobile_phase,
                    ),
                    _LightweightStep(
                        name="wash",
                        Q_m3_s=float(inputs.Q_set_m3_s) * 0.7,
                        mobile_phase=inputs.mobile_phase,
                    ),
                )
                step_result = monte_carlo_step_program(
                    polymer_family=inputs.polymer_family,
                    column=inputs.column,
                    step_program=step_program,
                    n_samples=int(n_samples),
                    seed=int(seed),
                    use_family_priors=(prior_mode == "family priors"),
                    log_cov=(
                        np.asarray(posterior_log_cov, dtype=float)
                        if use_log_cov else None
                    ),
                )
                # Use the worst-step bands as the panel's headline.
                bands_in_state = step_result.per_step_bands[
                    step_result.worst_step_index
                ]
                st.session_state["forward_mc_step_program_result"] = step_result
            else:
                bands_in_state = monte_carlo_pressure_envelope(
                    polymer_family=inputs.polymer_family,
                    column=inputs.column,
                    mobile_phase=inputs.mobile_phase,
                    Q_set_m3_s=inputs.Q_set_m3_s,
                    n_samples=int(n_samples),
                    seed=int(seed),
                    use_family_priors=(prior_mode == "family priors"),
                    log_cov=(
                        np.asarray(posterior_log_cov, dtype=float)
                        if use_log_cov else None
                    ),
                )
                st.session_state.pop("forward_mc_step_program_result", None)
        except (ValueError, KeyError) as exc:
            target.error(f"Forward MC run failed: {exc}")
            return None
        st.session_state["forward_mc_bands"] = bands_in_state

    if bands_in_state is None:
        return None
    bands: MCEnvelopeBands = bands_in_state

    # ── Result panel ──────────────────────────────────────────────────
    target.markdown("**Posterior bands (P50 with P05–P95 interval)**")
    cols_q = target.columns(3)
    render_metric(
        "Q_max P50",
        value=bands.Q_max_m3_s_p50,
        output_type=OutputType.Q_MAX,
        tier=ModelEvidenceTier.SEMI_QUANTITATIVE,
        unit="mL/min",
        scale=1.0e6 * 60.0,
        container=cols_q[0],
    )
    render_metric(
        "ΔP predicted P50",
        value=bands.dP_predicted_pa_p50,
        output_type=OutputType.PRESSURE_DROP,
        tier=ModelEvidenceTier.SEMI_QUANTITATIVE,
        unit="kPa",
        scale=1.0e-3,
        container=cols_q[1],
    )
    render_metric(
        "Headroom P50",
        value=min(bands.headroom_ratio_p50, 9.99),
        output_type=OutputType.PRESSURE_HEADROOM,
        tier=ModelEvidenceTier.SEMI_QUANTITATIVE,
        unit="%",
        scale=100.0,
        container=cols_q[2],
    )

    target.markdown("**Tail probabilities**")
    cols_p = target.columns(2)
    render_metric(
        "p_blocker",
        value=bands.p_blocker,
        output_type=OutputType.MC_PROBABILITY,
        tier=ModelEvidenceTier.SEMI_QUANTITATIVE,
        unit="%",
        scale=100.0,
        container=cols_p[0],
        help="P[headroom_ratio > 1.0] under the prior.",
    )
    render_metric(
        "p_warning",
        value=bands.p_warning,
        output_type=OutputType.MC_PROBABILITY,
        tier=ModelEvidenceTier.SEMI_QUANTITATIVE,
        unit="%",
        scale=100.0,
        container=cols_p[1],
        help="P[headroom_ratio > 0.7] under the prior.",
    )

    # Q_recommended for the chip callout — half of the median Q_max.
    q_recommended = 0.5 * bands.Q_max_m3_s_p50
    _render_p_blocker_chip(target, bands.p_blocker, q_recommended)

    target.caption(
        f"n={bands.n_samples} draws. Bands stay SEMI_QUANTITATIVE per "
        "ADR-007 — they reflect priors, not measured posteriors."
    )

    # B-5e (W-077, v0.8.7): when multi-step coupled MC ran, surface
    # the per-step blocker probabilities so the worst-step driver
    # is visible at a glance.
    multi_step_result: Any = st.session_state.get("forward_mc_step_program_result")
    if multi_step_result is not None:
        target.markdown("**Per-step blocker probabilities (coupled draws)**")
        target.caption(
            f"Worst step: **{multi_step_result.step_names[multi_step_result.worst_step_index]}** "
            f"with p_blocker = {multi_step_result.worst_step_p_blocker*100:.1f} %. "
            "Shared draws across steps preserve cross-step correlation per "
            "ADR-007 §4."
        )
        step_cols = target.columns(len(multi_step_result.step_names))
        for i, name in enumerate(multi_step_result.step_names):
            render_metric(
                name,
                value=multi_step_result.per_step_bands[i].p_blocker,
                output_type=OutputType.MC_PROBABILITY,
                tier=ModelEvidenceTier.SEMI_QUANTITATIVE,
                unit="%",
                scale=100.0,
                container=step_cols[i],
                help=(
                    f"headroom P50 = "
                    f"{multi_step_result.per_step_bands[i].headroom_ratio_p50*100:.0f} %"
                ),
            )

    return bands


__all__ = ["ForwardMCRunInputs", "render_forward_mc_panel"]
