"""Inverse Bayesian inference UI panel.

B-2s / W-060 — v0.8.4. Resolves audit defect C4 (Phase 1 §6).

Surfaces the v0.8.3 ADR-010 importance-sampling inverse machinery as
a runnable UI panel. The user enters measured (Q, ΔP, σ_dP) tuples in
a table editor, picks n_samples + seed + Q_for_envelope, and runs.
The panel reports posterior bands on (K_geom, μ, G_DN) + the envelope
outputs at the selected operating point + the ESS diagnostic.

The "Round-trip log_cov into forward MC" button writes the 3×3 posterior
covariance to ``st.session_state['posterior_log_cov']``; the forward-MC
panel detects it and offers the correlated-prior toggle.

Per ADR-010 §"Tier mapping" the posterior bands stay SEMI_QUANTITATIVE
in v0.8.4 — promotion to CALIBRATED_LOCAL is wet-lab-driven and lives
in the wetlab_ingestion panel (W-057), not here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import numpy as np
import pandas as pd
import streamlit as st

from dpsim.core.decision_grade import OutputType
from dpsim.core.mobile_phase import MobilePhase
from dpsim.datatypes import ModelEvidenceTier, PolymerFamily
from dpsim.module3_performance.hydrodynamics import ColumnGeometry
from dpsim.module3_performance.pressure_envelope_inverse import (
    InferredPosteriorEnvelope,
    MeasuredPressureFlowPoint,
    infer_posterior_envelope,
)
from dpsim.visualization.decision_grade_render import render_metric


@dataclass(frozen=True)
class InverseRunInputs:
    """Bundle of inputs the inverse panel consumes from the calling tab."""

    polymer_family: PolymerFamily
    column: ColumnGeometry
    mobile_phase: MobilePhase
    Q_for_envelope: float


_DEFAULT_MEASUREMENTS = [
    {"Q_m3_s": 1.0e-9, "dP_pa": 2_500.0, "sigma_dP_pa": 125.0},
    {"Q_m3_s": 3.0e-9, "dP_pa": 7_400.0, "sigma_dP_pa": 370.0},
    {"Q_m3_s": 5.0e-9, "dP_pa": 12_300.0, "sigma_dP_pa": 620.0},
]


def _parse_measurements(
    df: pd.DataFrame,
) -> tuple[tuple[MeasuredPressureFlowPoint, ...], list[str]]:
    """Validate + convert the editor DataFrame into a measurement tuple.

    Returns (points_tuple, errors). Skips malformed rows; surfaces a
    one-line error per skipped row.
    """
    out: list[MeasuredPressureFlowPoint] = []
    errors: list[str] = []
    for idx, row in df.iterrows():
        try:
            q = float(row["Q_m3_s"])
            dp = float(row["dP_pa"])
            sigma = float(row["sigma_dP_pa"])
        except (TypeError, ValueError, KeyError) as exc:
            errors.append(f"Row {idx}: malformed cell — {exc}")
            continue
        if q <= 0.0:
            errors.append(f"Row {idx}: Q_m3_s must be > 0")
            continue
        if dp < 0.0:
            errors.append(f"Row {idx}: dP_pa must be ≥ 0")
            continue
        if sigma <= 0.0:
            errors.append(f"Row {idx}: sigma_dP_pa must be > 0")
            continue
        out.append(MeasuredPressureFlowPoint(
            Q_m3_s=q, dP_pa=dp, sigma_dP_pa=sigma,
        ))
    return tuple(out), errors


def render_inverse_inference_panel(
    *,
    container: Any = None,
    key_prefix: str = "inv",
    inputs: Optional[InverseRunInputs] = None,
) -> Optional[InferredPosteriorEnvelope]:
    """Render the inverse Bayesian inference sub-section.

    Result is cached on ``st.session_state['posterior_envelope']``.
    The round-trip button writes ``st.session_state['posterior_log_cov']``
    so the forward-MC panel can consume it.
    """
    target = container if container is not None else st

    target.subheader("Inverse Bayesian inference")
    target.caption(
        "Importance-sample the posterior over (K_geom, μ, G_DN) given "
        "measured (Q, ΔP) pairs. ESS-flagged when the posterior is "
        "concentrated. Round-trip the posterior log_cov into the "
        "forward-MC panel for tighter predictive intervals."
    )

    if inputs is None:
        target.info(
            "Run the lifecycle first so column + mobile_phase + "
            "Q_for_envelope are populated. Once available, this panel "
            "becomes active."
        )
        return None

    # ── Measurement table editor ──────────────────────────────────────
    target.markdown("**Measured (Q, ΔP, σ) data points**")
    # W-096 (v0.8.9): unit-conversion crib for the SI-anchored columns.
    # Closes audit defect U-24 partial — bench data is typically in
    # mL/min and kPa, but the SI schema (Q_m3_s, dP_pa) requires
    # conversion. The crib makes the conversions one-glance obvious.
    target.caption(
        ":material/calculate: **Unit conversions** — "
        "1 mL/min = 1.667 × 10⁻⁸ m³/s · "
        "1 kPa = 1000 Pa · "
        "1 bar = 1.0 × 10⁵ Pa."
    )
    seed_df = pd.DataFrame(
        st.session_state.get(
            f"{key_prefix}_measurements_df", _DEFAULT_MEASUREMENTS,
        )
    )
    edited_df = target.data_editor(
        seed_df,
        num_rows="dynamic",
        column_config={
            "Q_m3_s": st.column_config.NumberColumn(
                "Q (m³/s)",
                help=(
                    "Measured volumetric flow rate in m³/s. "
                    "To convert from mL/min, divide by 6.0e7."
                ),
                min_value=0.0, format="%.3e",
            ),
            "dP_pa": st.column_config.NumberColumn(
                "ΔP (Pa)",
                help=(
                    "Measured pressure drop in Pa. "
                    "To convert from kPa, multiply by 1000."
                ),
                min_value=0.0, format="%.0f",
            ),
            "sigma_dP_pa": st.column_config.NumberColumn(
                "σ_ΔP (Pa)",
                help="1 σ measurement noise on ΔP. ~5 % of dP_pa is typical.",
                min_value=0.0, format="%.0f",
            ),
        },
        key=f"{key_prefix}_editor",
        use_container_width=True,
    )
    st.session_state[f"{key_prefix}_measurements_df"] = (
        edited_df.to_dict(orient="records")
    )

    # ── Run controls ──────────────────────────────────────────────────
    cols = target.columns(2)
    n_samples = cols[0].slider(
        "Sample count",
        min_value=200, max_value=5000, value=2000, step=200,
        key=f"{key_prefix}_n",
        help="2000 is the empirical default for ±5 % stable posterior P50.",
    )
    seed = cols[1].number_input(
        "RNG seed",
        min_value=0, max_value=2**31 - 1, value=0, step=1,
        key=f"{key_prefix}_seed",
    )

    run = target.button(
        "Fit posterior",
        key=f"{key_prefix}_run",
        type="primary",
    )

    posterior_in_state: Optional[InferredPosteriorEnvelope] = (
        st.session_state.get("posterior_envelope")
    )
    if not run and posterior_in_state is None:
        return None

    if run:
        measurements, parse_errors = _parse_measurements(edited_df)
        if parse_errors:
            with target.expander("Parse errors"):
                for e in parse_errors:
                    target.warning(e)
        if not measurements:
            target.error(
                "No valid measurements parsed — populate the table with "
                "at least one row of positive Q + non-negative ΔP + "
                "positive σ_ΔP."
            )
            return None

        # W-088 (v0.8.8): input-time blocker for under-determined fits.
        # Per audit defect S-12 / U-16: a posterior fit on < 8 measurements
        # is ill-posed — ESS will be near 1 and the result misleads. The
        # ADR-010 §"Tier mapping" guidance recommends MCMC for low-N data;
        # for the importance-sampling path we block at the input.
        _MIN_MEASUREMENTS = 8
        if len(measurements) < _MIN_MEASUREMENTS:
            target.error(
                f":material/block: **{len(measurements)} measurement(s) is "
                f"insufficient for the importance-sampling posterior fit.** "
                f"Minimum recommended: {_MIN_MEASUREMENTS} (Q, ΔP, σ) rows. "
                "Below this, ESS collapses and the posterior is dominated "
                "by the prior — the result misleads. Either add more "
                "measurement rows above, or wait for the v1.0 MCMC path "
                "(ADR-010 §Tier mapping)."
            )
            return None

        try:
            posterior_in_state = infer_posterior_envelope(
                measurements,
                polymer_family=inputs.polymer_family,
                column=inputs.column,
                mobile_phase=inputs.mobile_phase,
                Q_for_envelope=inputs.Q_for_envelope,
                n_samples=int(n_samples),
                seed=int(seed),
            )
        except (ValueError, KeyError) as exc:
            target.error(f"Posterior fit failed: {exc}")
            return None
        st.session_state["posterior_envelope"] = posterior_in_state

    if posterior_in_state is None:
        return None
    posterior: InferredPosteriorEnvelope = posterior_in_state

    # ── Posterior parameter bands ────────────────────────────────────
    target.markdown("**Posterior parameter quantiles (P05–P50–P95)**")
    cols_p = target.columns(3)
    render_metric(
        "K_geom P50",
        value=posterior.K_geom_p50,
        output_type=OutputType.POSTERIOR_PARAMETER,
        tier=posterior.decision_tier,
        unit="—",
        container=cols_p[0],
    )
    render_metric(
        "μ P50 (Pa·s)",
        value=posterior.mu_pa_s_p50,
        output_type=OutputType.POSTERIOR_PARAMETER,
        tier=posterior.decision_tier,
        unit="Pa·s",
        container=cols_p[1],
    )
    render_metric(
        "G_DN P50 (kPa)",
        value=posterior.G_DN_pa_p50,
        output_type=OutputType.POSTERIOR_PARAMETER,
        tier=posterior.decision_tier,
        unit="kPa",
        scale=1.0e-3,
        container=cols_p[2],
    )

    # ── ESS diagnostic ────────────────────────────────────────────────
    cols_d = target.columns(2)
    render_metric(
        "ESS",
        value=posterior.effective_sample_size,
        output_type=OutputType.ESS,
        tier=ModelEvidenceTier.QUALITATIVE_TREND,
        unit="",
        container=cols_d[0],
        help=(
            "Effective sample size from importance sampling. ESS < 10 % "
            "of n_samples → posterior is concentrated; widen priors or "
            "tighten σ_ΔP."
        ),
    )
    cols_d[1].metric(
        "n_samples", f"{posterior.n_samples}",
    )
    if posterior.ess_warning:
        target.warning(posterior.ess_warning)

    # ── Envelope bands at Q_for_envelope ─────────────────────────────
    target.markdown(
        f"**Envelope at Q={inputs.Q_for_envelope*1.0e6*60.0:.2f} mL/min** "
        "(posterior-weighted)"
    )
    cols_e = target.columns(3)
    render_metric(
        "Q_max P50",
        value=posterior.Q_max_m3_s_p50,
        output_type=OutputType.Q_MAX,
        tier=posterior.decision_tier,
        unit="mL/min",
        scale=1.0e6 * 60.0,
        container=cols_e[0],
    )
    render_metric(
        "Headroom P50",
        value=min(posterior.headroom_ratio_p50, 9.99),
        output_type=OutputType.PRESSURE_HEADROOM,
        tier=posterior.decision_tier,
        unit="%",
        scale=100.0,
        container=cols_e[1],
    )
    render_metric(
        "Posterior p_blocker",
        value=posterior.p_blocker,
        output_type=OutputType.MC_PROBABILITY,
        tier=posterior.decision_tier,
        unit="%",
        scale=100.0,
        container=cols_e[2],
    )

    # ── Round-trip button ────────────────────────────────────────────
    target.divider()
    if target.button(
        "Round-trip posterior log_cov into forward MC",
        key=f"{key_prefix}_roundtrip",
        type="secondary",
        help=(
            "Writes the 3×3 posterior covariance to the session state. "
            "The forward-MC panel will offer a correlated-prior toggle "
            "that consumes it for predictive intervals at a new Q."
        ),
    ):
        st.session_state["posterior_log_cov"] = np.asarray(
            posterior.log_cov, dtype=float,
        )
        target.success(
            "Posterior log_cov written. Switch to the forward-MC panel "
            "and tick 'Consume posterior log_cov' to use it."
        )

    target.caption(
        "Posterior bands stay SEMI_QUANTITATIVE per ADR-010 §Tier mapping. "
        "CALIBRATED_LOCAL promotion happens via the wet-lab YAML "
        "ingestion panel, not here."
    )

    return posterior


__all__ = ["InverseRunInputs", "render_inverse_inference_panel"]
