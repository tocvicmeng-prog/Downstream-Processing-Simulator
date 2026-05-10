"""Detector-trace overlay panel — UV / fluorescence / conductivity (B-5b).

W-074 / v0.8.7. Closes the v0.8.5 audit defect S-6 (Phase 1 §S-6) and
A-5 (Phase 3 §A-5): the detection module family
(``module3_performance/detection/{uv,fluorescence,conductivity,ms}``)
has zero UI consumers at v0.8.6. Real chromatography produces UV /
conductivity / fluorescence traces that operators read directly off
the UNICORN console; DPSim has the models for these but never
displayed them.

This component renders, after every M3 run, the same detector traces
a wet-lab user would see at the bench, overlaid against the
breakthrough curve. The panel is rendered as a sub-section of the
M3 results page.
"""

from __future__ import annotations

from typing import Any, Optional

import numpy as np
import plotly.graph_objects as go

from dpsim.module3_performance.detection.conductivity import (
    compute_chromatogram_conductivity,
)
from dpsim.module3_performance.detection.fluorescence import (
    compute_fluorescence_signal,
)
from dpsim.module3_performance.detection.uv import (
    apply_detector_broadening,
    compute_uv_signal,
)


def _build_detector_figure(
    *,
    time_s: np.ndarray,
    C_outlet: np.ndarray,
    extinction_coeff: float,
    path_length_m: float,
    sigma_detector_s: float,
    show_fluorescence: bool,
    quantum_yield: float,
    fluor_extinction: float,
    salt_profile: Optional[np.ndarray],
) -> go.Figure:
    """Compose the multi-trace overlay figure.

    Each trace is rendered on its own y-axis to keep the units
    honest — UV (mAU), fluorescence (RFU), conductivity (mS/cm).
    """
    time_min = np.asarray(time_s, dtype=float) / 60.0

    # UV — primary y axis.
    uv_raw = compute_uv_signal(
        np.asarray(C_outlet, dtype=float),
        extinction_coeff=extinction_coeff,
        path_length=path_length_m,
    )
    uv = apply_detector_broadening(uv_raw, time_s, sigma_detector=sigma_detector_s)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=time_min, y=uv, mode="lines",
            name="UV (mAU)",
            line=dict(color="#0EA5E9", width=2),
            yaxis="y1",
        )
    )

    if show_fluorescence:
        fluor = compute_fluorescence_signal(
            np.asarray(C_outlet, dtype=float),
            quantum_yield=quantum_yield,
            extinction_coeff=fluor_extinction,
            path_length=path_length_m,
        )
        fig.add_trace(
            go.Scatter(
                x=time_min, y=fluor, mode="lines",
                name="Fluorescence (RFU)",
                line=dict(color="#10B981", width=2, dash="dot"),
                yaxis="y2",
            )
        )

    if salt_profile is not None:
        cond = compute_chromatogram_conductivity(
            np.asarray(salt_profile, dtype=float),
            report_units="mS/cm",
        )
        fig.add_trace(
            go.Scatter(
                x=time_min, y=cond, mode="lines",
                name="Conductivity (mS/cm)",
                line=dict(color="#F59E0B", width=2, dash="dash"),
                yaxis="y3",
            )
        )

    layout: dict[str, Any] = dict(
        title="Detector traces — predicted (B-5b / W-074)",
        xaxis=dict(title="Time (min)"),
        yaxis=dict(title="UV (mAU)", side="left"),
        height=420,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="right", x=1,
        ),
    )
    if show_fluorescence:
        layout["yaxis2"] = dict(
            title="Fluorescence (RFU)",
            overlaying="y", side="right", anchor="free", position=1.0,
            showgrid=False,
        )
    if salt_profile is not None:
        layout["yaxis3"] = dict(
            title="Conductivity (mS/cm)",
            overlaying="y", side="right", anchor="free", position=0.95,
            showgrid=False,
        )
    fig.update_layout(**layout)
    return fig


def render_detector_traces(
    *,
    breakthrough_result: Any,
    container: Any = None,
    salt_profile: Optional[np.ndarray] = None,
    extinction_coeff: float = 36000.0,
    path_length_m: float = 0.01,
    sigma_detector_s: float = 1.0,
    quantum_yield: float = 0.92,
    fluor_extinction: float = 76900.0,
) -> None:
    """Render the detector-trace overlay panel.

    Parameters
    ----------
    breakthrough_result :
        BreakthroughResult-like with ``.time`` and ``.C_outlet`` attributes.
    container :
        Streamlit container; defaults to the active streamlit module.
    salt_profile :
        Optional salt concentration vs time [mol/m³] for the conductivity
        trace. None → conductivity trace is omitted.
    extinction_coeff :
        Molar extinction at the UV detection wavelength [1/(M·cm)]. The
        default 36 000 is BSA at 280 nm. Editable from the UI.
    path_length_m :
        Detector flow cell path length [m]. Default 0.01 (1 cm cuvette).
    sigma_detector_s :
        Gaussian broadening time constant for extra-column dispersion [s].
    quantum_yield, fluor_extinction :
        Fluorescence-trace parameters. Defaults map to fluorescein.
    """
    if container is None:
        import streamlit as st
        container = st

    container.subheader("Detector traces (predicted)")
    container.caption(
        "Predicted UV / fluorescence / conductivity overlays — what an "
        "AKTA UNICORN trace would show for this run. Compare against "
        "your wet-lab UNICORN export when validating the simulation."
    )

    time_s = np.asarray(getattr(breakthrough_result, "time", []), dtype=float)
    C_outlet = np.asarray(getattr(breakthrough_result, "C_outlet", []), dtype=float)
    if time_s.size == 0 or C_outlet.size == 0:
        container.info(
            "Run the M3 lifecycle to populate the breakthrough trace; "
            "detector overlays will then render here."
        )
        return

    cols = container.columns(3)
    user_eps = cols[0].number_input(
        "ε (UV, 1/M/cm)",
        min_value=100.0, max_value=1.0e6,
        value=float(extinction_coeff), step=1000.0, format="%.0f",
        key="m3_det_eps",
        help="Molar extinction at the detection wavelength.",
    )
    user_path = cols[1].number_input(
        "path length (cm)",
        min_value=0.1, max_value=10.0,
        value=float(path_length_m * 100.0), step=0.1,
        key="m3_det_path",
    )
    user_sigma = cols[2].number_input(
        "σ_detector (s)",
        min_value=0.0, max_value=60.0,
        value=float(sigma_detector_s), step=0.5,
        key="m3_det_sigma",
        help="Gaussian extra-column broadening time constant.",
    )

    show_fluor = container.checkbox(
        "Overlay fluorescence trace", value=False, key="m3_det_show_fluor",
        help=(
            "Adds a fluorescence trace using the fluorescein quantum-yield "
            "+ extinction defaults. Toggle on when your method tags the "
            "target with a fluorophore."
        ),
    )

    fig = _build_detector_figure(
        time_s=time_s,
        C_outlet=C_outlet,
        extinction_coeff=float(user_eps),
        path_length_m=float(user_path) / 100.0,
        sigma_detector_s=float(user_sigma),
        show_fluorescence=bool(show_fluor),
        quantum_yield=quantum_yield,
        fluor_extinction=fluor_extinction,
        salt_profile=salt_profile,
    )
    container.plotly_chart(fig, width="stretch")


__all__ = ["render_detector_traces"]
