"""M3 Performance tab — extracted from app.py for UI restructure.

v6.0: Renders the complete M3 Performance Characterization tab including
inputs, run button, and results display. All widget keys preserved exactly
(m3_* prefix). Chromatography and catalysis modes supported.

v0.2.0 (A6): gradient elution call site now inherits FMC tier; M3 result
subpanels render evidence-tier badges next to their headers.
"""

from __future__ import annotations

import numpy as np
import streamlit as st

from dpsim.datatypes import ModelEvidenceTier
from dpsim.lifecycle import resolve_lifecycle_inputs
from dpsim.visualization.ui_recipe import (
    ensure_process_recipe_state,
    mg_mL_to_mol_m3,
    save_process_recipe_state,
    sync_m3_ui_to_recipe,
)


_M3_TIER_COLORS = {
    ModelEvidenceTier.VALIDATED_QUANTITATIVE: ":green[VALIDATED]",
    ModelEvidenceTier.CALIBRATED_LOCAL: ":green[CALIBRATED]",
    ModelEvidenceTier.SEMI_QUANTITATIVE: ":orange[SEMI-QUANTITATIVE]",
    ModelEvidenceTier.QUALITATIVE_TREND: ":red[QUALITATIVE TREND]",
    ModelEvidenceTier.UNSUPPORTED: ":red[UNSUPPORTED]",
}


def _m3_evidence_tier_badge(result_obj) -> str:
    """Return a Streamlit-flavoured tier badge for an M3 result object.

    Mirrors the helper in tab_m1; duplicated here to avoid cross-tab imports
    until v0.3.0 (B3) consolidates evidence-badge UX across tabs.
    """
    manifest = getattr(result_obj, "model_manifest", None)
    if manifest is None:
        return ""
    tier = getattr(manifest, "evidence_tier", None)
    if tier is None:
        return ""
    badge = _M3_TIER_COLORS.get(tier, str(getattr(tier, "value", tier)))
    model_name = getattr(manifest, "model_name", "")
    cal_ref = getattr(manifest, "calibration_ref", "")
    suffix = f" | calibration: `{cal_ref}`" if cal_ref else ""
    return f"Evidence: {badge} | Model: `{model_name}`{suffix}"


def render_tab_m3(tab_container) -> None:
    """Render the M3 Performance tab inside the given Streamlit container.

    Args:
        tab_container: Streamlit tab container from st.tabs().
    """
    with tab_container:
        # v0.4.14: Direction-A page-header pair replacing legacy st.header.
        from dpsim.visualization.design import chrome as _chrome_top
        st.html(_chrome_top.eyebrow("Stage 04 · M3", accent=True))
        st.html('<h1 style="margin:0 0 12px 0;">Column method</h1>')

        # ── Upstream M2 Status Banner ────────────────────────────────────
        if "m2_result" not in st.session_state:
            st.warning("\u26a0\ufe0f Module 2 has not been run yet. Run M1 then M2 first to provide upstream data.")
        else:
            _m2r_banner = st.session_state["m2_result"]
            st.success(
                f"\u2705 M2 data available \u2014 G_DN={_m2r_banner.G_DN_updated/1000:.1f} kPa | "
                f"E*={_m2r_banner.E_star_updated/1000:.1f} kPa | "
                f"Steps={len(_m2r_banner.modification_history)}"
            )

        # ── M3 Inputs ───────────────────────────────────────────────────
        # v0.4.5: top-level mode pickers migrated to labeled_widget.
        from dpsim.visualization.help import labeled_widget as _lw_m3_top
        m3_app_mode = _lw_m3_top(
            "Application",
            help="Chromatography: separations / capture (LRM solver). Catalysis: enzyme reactor (Michaelis–Menten + Thiele).",
            widget=lambda: st.radio(
                "Application", ["Chromatography", "Catalysis"],
                key="m3_mode", label_visibility="collapsed",
            ),
        )

        with st.container(border=True):
            st.html(
                _chrome_top.card_header_strip(
                    eyebrow_text="Column geometry",
                    title="Packed bed",
                )
            )
            # v0.4.1: migrated to labeled_widget for inline help. Each widget
            # picks up its tooltip from the central HELP_CATALOG, so help text
            # stays consistent across the UI and is editable in one place.
            from dpsim.visualization.help import get_help, labeled_widget
            _m3c1, _m3c2 = st.columns(2)
            with _m3c1:
                col_diam_mm = labeled_widget(
                    "Column I.D.",
                    help=get_help("m3.column.diameter"),
                    unit="mm",
                    widget=lambda: st.number_input(
                        "Column I.D. (mm)", 1.0, 50.0, 10.0,
                        key="m3_col_d", label_visibility="collapsed",
                    ),
                )
                bed_height_cm = labeled_widget(
                    "Bed height",
                    help=get_help("m3.column.length"),
                    unit="cm",
                    widget=lambda: st.number_input(
                        "Bed height (cm)", 1.0, 30.0, 10.0,
                        key="m3_bed_h", label_visibility="collapsed",
                    ),
                )
            with _m3c2:
                bed_porosity = labeled_widget(
                    "Bed porosity",
                    widget=lambda: st.slider(
                        "Bed porosity", 0.25, 0.50, 0.38, step=0.01,
                        key="m3_eps_b", label_visibility="collapsed",
                    ),
                )
                flow_rate_mL = labeled_widget(
                    "Flow rate",
                    help=get_help("m3.flow_rate"),
                    unit="mL/min",
                    widget=lambda: st.number_input(
                        "Flow rate (mL/min)", 0.01, 20.0, 1.0, step=0.1,
                        key="m3_flow", label_visibility="collapsed",
                    ),
                )

            # v0.4.17 (P4): derived-geometry strip — bed volume,
            # superficial linear velocity (cm/h), and one-CV residence
            # time. These are read-only derivations from the inputs
            # above; the LRM solver does its own rigorous calculation
            # but surfacing them at the input site lets the operator
            # sanity-check method conditions before Run.
            import math as _math_m3
            _r_cm = (col_diam_mm / 10.0) / 2.0
            _bed_volume_mL = _math_m3.pi * _r_cm * _r_cm * bed_height_cm
            _area_cm2 = _math_m3.pi * _r_cm * _r_cm
            _u_super_cm_h = (
                (flow_rate_mL * 60.0) / _area_cm2 if _area_cm2 > 0 else 0.0
            )
            _void_volume_mL = _bed_volume_mL * float(bed_porosity)
            _tau_void_min = (
                _void_volume_mL / flow_rate_mL if flow_rate_mL > 0 else 0.0
            )
            st.html(
                '<div class="dps-mono" style="display:flex;align-items:center;'
                "gap:14px;padding:6px 10px;margin-top:6px;"
                "background:var(--dps-surface-2);"
                "border:1px solid var(--dps-border);border-radius:3px;"
                'font-size:11px;color:var(--dps-text-muted);">'
                '<span>V_bed <span style="color:var(--dps-text);">'
                f'{_bed_volume_mL:.2f} mL</span></span>'
                '<span>u_super <span style="color:var(--dps-text);">'
                f'{_u_super_cm_h:.0f} cm/h</span></span>'
                '<span>τ_void <span style="color:var(--dps-text);">'
                f'{_tau_void_min:.2f} min</span></span>'
                '<span style="margin-left:auto;color:var(--dps-text-dim);">'
                "derived</span>"
                "</div>"
            )

            # Pressure preview
            if "m2_result" in st.session_state:
                from dpsim.module3_performance.hydrodynamics import ColumnGeometry as _CG_preview
                m2r_prev = st.session_state["m2_result"]
                _preview_col = _CG_preview(
                    diameter=col_diam_mm / 1000, bed_height=bed_height_cm / 100,
                    particle_diameter=m2r_prev.m1_contract.bead_d50,
                    bed_porosity=bed_porosity,
                    G_DN=m2r_prev.G_DN_updated, E_star=m2r_prev.E_star_updated)
                _dP = _preview_col.pressure_drop(flow_rate_mL / 60e6)
                st.metric("Estimated Pressure Drop", f"{_dP / 1000:.1f} kPa")

        # v0.4.11: Live phase view — rendered inline at full size to match
        # the Direction-A reference (was hidden in a collapsed expander
        # since v0.4.1). The phase animation IS the column-method
        # affordance; per the SA Q2 sign-off in
        # SA_v0_4_0_RUSHTON_FIDELITY.md §3, the visual keeps BOTH bead
        # recolour (bound payload concentration on resin) AND streaming
        # dots (eluate / wash / CIP outflow), with phase-dependent
        # legend labels.
        from dpsim.visualization.components import render_column_xsec
        from dpsim.visualization.design import chrome as _chrome
        from dpsim.visualization.help import labeled_widget as _lw_xsec
        st.html(_chrome.eyebrow("Live phase view"))
        _phase = _lw_xsec(
            "Phase",
            help=(
                "load: target binds resin · wash: impurities flushed · "
                "elute: bound target releases · cip: stripped residuals."
            ),
            widget=lambda: st.radio(
                "Phase",
                ["load", "wash", "elute", "cip"],
                horizontal=True,
                key="m3_xsec_phase",
                label_visibility="collapsed",
            ),
        )
        render_column_xsec(
            phase=_phase,  # type: ignore[arg-type]
            column_length_mm=float(bed_height_cm * 10),
            column_diameter_mm=float(col_diam_mm),
        )

        # v0.4.17 (P7): Monte-Carlo uncertainty card — promoted from
        # the sidebar popover into a primary M3 card per the canonical
        # Direction-A reference. The panel writes _unc_spec /
        # _unc_n_jobs into session state; the M3 Run button below
        # picks them up automatically.
        from dpsim.visualization.panels import (
            render_lifetime_panel,
            render_uncertainty_panel,
        )
        with st.container(border=True):
            st.html(
                _chrome_top.card_header_strip(
                    eyebrow_text="Monte-Carlo uncertainty",
                    title="LRM with posterior propagation",
                    right_html=_chrome_top.chip(
                        "P05–P95", color="var(--dps-accent)",
                    ),
                )
            )
            render_uncertainty_panel(as_card=True)

        # v0.4.19 (C1): Resin lifetime projection — promoted from the
        # sidebar popover into a primary M3 card matching the MC
        # uncertainty card pattern. Empirical first-order deactivation
        # (capacity vs cycle count); user-calibrated k from cycle
        # studies. Sits next to the MC card so column-method tuning
        # and lifetime forecasting share one stage.
        with st.container(border=True):
            st.html(
                _chrome_top.card_header_strip(
                    eyebrow_text="Resin lifetime",
                    title="Empirical first-order deactivation",
                    right_html=_chrome_top.chip(
                        "user-calibrated k", color="var(--dps-text-muted)",
                    ),
                )
            )
            render_lifetime_panel(as_card=True)

        # Mode-specific inputs
        chrom_mode = "Breakthrough"
        C_feed_mg = 1.0
        feed_dur_min = 10.0
        total_time_min = 20.0
        q_max = 100.0
        K_L_m3 = 1000.0
        ext_coeff = 36000.0
        grad_start = 0.0
        grad_end = 500.0
        grad_dur_min = 10.0
        bind_pH = 7.4
        bind_cond = 15.0
        elute_pH = 3.5
        elute_cond = 5.0
        wash_dur_min = 5.0
        elute_dur_min = 5.0
        V_max = 1.0
        K_m = 1.0
        S_feed = 10.0
        D_eff = 1e-10
        k_deact = 0.0
        cat_time_h = 1.0

        if m3_app_mode == "Chromatography":
            chrom_mode = _lw_m3_top(
                "Chromatography mode",
                help=(
                    "Breakthrough: simple load + LRM. Gradient Elution: "
                    "linear salt ramp. Protein A Method: full bind / wash / "
                    "low-pH elute cycle with realistic buffer conditions."
                ),
                widget=lambda: st.radio(
                    "Mode",
                    ["Breakthrough", "Gradient Elution", "Protein A Method"],
                    key="m3_chrom_mode", label_visibility="collapsed",
                ),
            )

            with st.container(border=True):
                st.html(
                    _chrome_top.card_header_strip(
                        eyebrow_text="Feed",
                        title="Inlet stream",
                    )
                )
                # v0.4.3: feed + isotherm migrated to labeled_widget.
                from dpsim.visualization.help import labeled_widget as _lw_m3
                C_feed_mg = _lw_m3(
                    "Feed concentration",
                    help=(
                        "Total target concentration in the feed stream. "
                        "Drives load-step mass balance and DBC10 calculation."
                    ),
                    unit="mg/mL",
                    widget=lambda: st.number_input(
                        "Feed conc. (mg/mL)", 0.01, 50.0, 1.0,
                        key="m3_Cfeed", label_visibility="collapsed",
                    ),
                )
                feed_dur_min = _lw_m3(
                    "Feed duration",
                    help="Duration of the load step. Sets the integral mass loaded onto the bed.",
                    unit="min",
                    widget=lambda: st.number_input(
                        "Feed duration (min)", 1.0, 60.0, 10.0,
                        key="m3_feed_dur", label_visibility="collapsed",
                    ),
                )
                total_time_min = _lw_m3(
                    "Total time",
                    help="Total simulation time, including post-load tail. Must exceed feed duration.",
                    unit="min",
                    widget=lambda: st.number_input(
                        "Total time (min)", 5.0, 120.0, 20.0,
                        key="m3_total_t", label_visibility="collapsed",
                    ),
                )

            with st.container(border=True):
                st.html(
                    _chrome_top.card_header_strip(
                        eyebrow_text="Isotherm",
                        title="Binding model",
                    )
                )
                q_max = _lw_m3(
                    "q_max",
                    help=(
                        "Langmuir saturation capacity in mol/m\u00b3. "
                        "Drives the high-load asymptote of binding capacity."
                    ),
                    unit="mol/m\u00b3",
                    widget=lambda: st.number_input(
                        "q_max (mol/m\u00b3)", 1.0, 500.0, 100.0,
                        key="m3_qmax", label_visibility="collapsed",
                    ),
                )
                K_L_m3 = _lw_m3(
                    "K_L",
                    help=(
                        "Langmuir affinity constant in m\u00b3/mol. "
                        "Higher K_L = sharper breakthrough; the DBC\u2081\u2080 "
                        "metric depends on K_L \u00d7 q_max."
                    ),
                    unit="m\u00b3/mol",
                    widget=lambda: st.number_input(
                        "K_L (m\u00b3/mol)", 10.0, 1e5, 1000.0,
                        key="m3_KL", label_visibility="collapsed",
                    ),
                )
                st.caption("Default isotherm parameters are illustrative \u2014 user calibration required.")

                # v0.4.5: \u03b5\u2082\u2088\u2080 + gradient + Protein A + catalysis migrated.
                ext_coeff = _lw_m3(
                    "\u03b5\u2082\u2088\u2080",
                    help=(
                        "Molar extinction coefficient of the target at 280 nm "
                        "in M\u207b\u00b9\u00b7cm\u207b\u00b9. Used to convert absorbance traces to "
                        "concentration. **Default 36 000 fits ~50 kDa "
                        "proteins (e.g. BSA \u2248 43 800)**. For IgG use \u2248 "
                        "210 000 (Pace 1995, \u03b5^1% \u2248 1.4 mL\u00b7mg\u207b\u00b9\u00b7cm\u207b\u00b9 \u00d7 "
                        "MW 150 kDa); for sdAb / nanobody use \u2248 28 000. "
                        "Mismatched \u03b5 scales the C\u2082\u2088\u2080 trace linearly, so "
                        "DBC\u2081\u2080 scales the same way \u2014 set this correctly "
                        "before reading binding capacities."
                    ),
                    unit="1/(M\u00b7cm)",
                    widget=lambda: st.number_input(
                        "\u03b5\u2082\u2088\u2080 (1/(M\u00b7cm))", 1000.0, 250000.0, 36000.0,
                        key="m3_ext", label_visibility="collapsed",
                    ),
                )

            if chrom_mode == "Gradient Elution":
                with st.container(border=True):
                    st.html(
                        _chrome_top.card_header_strip(
                            eyebrow_text="Gradient",
                            title="Salt / pH ramp",
                        )
                    )
                    grad_start = _lw_m3(
                        "Gradient start",
                        help="Salt / modifier concentration at gradient start. Linear ramp from start to end over the gradient duration.",
                        unit="mM",
                        widget=lambda: st.number_input(
                            "Start (mM)", 0.0, 1000.0, 0.0,
                            key="m3_grad_start", label_visibility="collapsed",
                        ),
                    )
                    grad_end = _lw_m3(
                        "Gradient end",
                        help="Salt / modifier concentration at gradient end. Higher end = harsher elution = sharper peaks but worse selectivity.",
                        unit="mM",
                        widget=lambda: st.number_input(
                            "End (mM)", 0.0, 1000.0, 500.0,
                            key="m3_grad_end", label_visibility="collapsed",
                        ),
                    )
                    grad_dur_min = _lw_m3(
                        "Gradient duration",
                        help="Time over which the salt ramp runs. Longer gradients give better resolution at the cost of process time.",
                        unit="min",
                        widget=lambda: st.number_input(
                            "Duration (min)", 1.0, 60.0, 10.0,
                            key="m3_grad_dur", label_visibility="collapsed",
                        ),
                    )
            elif chrom_mode == "Protein A Method":
                with st.container(border=True):
                    st.html(
                        _chrome_top.card_header_strip(
                            eyebrow_text="Method buffers",
                            title="Bind · wash · elute",
                        )
                    )
                    _m3m1, _m3m2 = st.columns(2)
                    with _m3m1:
                        from dpsim.visualization.help import get_help as _gh3
                        bind_pH = _lw_m3(
                            "Bind/wash pH",
                            help=_gh3("m3.bind_pH"),
                            widget=lambda: st.number_input(
                                "Bind/wash pH", 5.0, 9.5, 7.4, step=0.1,
                                key="m3_bind_pH", label_visibility="collapsed",
                            ),
                        )
                        bind_cond = _lw_m3(
                            "Bind/wash conductivity",
                            help="Salt-equivalent conductivity of the load + wash buffers. Typical Protein A: 10–20 mS/cm.",
                            unit="mS/cm",
                            widget=lambda: st.number_input(
                                "Bind/wash conductivity (mS/cm)", 1.0, 40.0, 15.0, step=0.5,
                                key="m3_bind_cond", label_visibility="collapsed",
                            ),
                        )
                        wash_dur_min = _lw_m3(
                            "Wash duration",
                            help="Wash-step duration (post-load, pre-elute). Longer washes flush more impurities at the cost of process time.",
                            unit="min",
                            widget=lambda: st.number_input(
                                "Wash duration (min)", 1.0, 60.0, 5.0,
                                key="m3_wash_dur", label_visibility="collapsed",
                            ),
                        )
                    with _m3m2:
                        elute_pH = _lw_m3(
                            "Elution pH",
                            help=_gh3("m3.elute_pH"),
                            widget=lambda: st.number_input(
                                "Elution pH", 2.5, 5.0, 3.5, step=0.1,
                                key="m3_elute_pH", label_visibility="collapsed",
                            ),
                        )
                        elute_cond = _lw_m3(
                            "Elution conductivity",
                            help="Salt-equivalent conductivity of the elute buffer. Typical Protein A elute: 5–10 mS/cm.",
                            unit="mS/cm",
                            widget=lambda: st.number_input(
                                "Elution conductivity (mS/cm)", 1.0, 40.0, 5.0, step=0.5,
                                key="m3_elute_cond", label_visibility="collapsed",
                            ),
                        )
                        elute_dur_min = _lw_m3(
                            "Elution duration",
                            help="Elution-step duration. Long enough to sweep one bed volume of elute through the bed.",
                            unit="min",
                            widget=lambda: st.number_input(
                                "Elution duration (min)", 1.0, 60.0, 5.0,
                                key="m3_elute_dur", label_visibility="collapsed",
                            ),
                        )
        elif m3_app_mode == "Catalysis":
            from dpsim.visualization.help import labeled_widget as _lw_m3
            with st.container(border=True):
                st.html(
                    _chrome_top.card_header_strip(
                        eyebrow_text="Enzyme kinetics",
                        title="Michaelis–Menten parameters",
                    )
                )
                V_max = _lw_m3(
                    "V_max",
                    help="Maximum specific reaction rate at saturating substrate. Drives the high-substrate plateau in the Michaelis–Menten kinetics.",
                    unit="mol/(m³·s)",
                    widget=lambda: st.number_input(
                        "V_max (mol/(m³·s))", 0.001, 100.0, 1.0,
                        key="m3_Vmax", label_visibility="collapsed",
                    ),
                )
                K_m = _lw_m3(
                    "K_m",
                    help="Michaelis constant — substrate concentration at which the reaction rate is V_max/2. Lower K_m = higher apparent affinity.",
                    unit="mM",
                    widget=lambda: st.number_input(
                        "K_m (mM)", 0.01, 100.0, 1.0,
                        key="m3_Km", label_visibility="collapsed",
                    ),
                )
                S_feed = _lw_m3(
                    "Substrate feed",
                    help="Substrate concentration at the reactor inlet. Drives both conversion and effective rate (saturation behaviour).",
                    unit="mM",
                    widget=lambda: st.number_input(
                        "Substrate feed (mM)", 0.1, 100.0, 10.0,
                        key="m3_Sfeed", label_visibility="collapsed",
                    ),
                )
                D_eff = _lw_m3(
                    "Effective diffusivity",
                    help="Intra-particle effective diffusivity of substrate. Drives the Thiele modulus and internal effectiveness factor.",
                    unit="m²/s",
                    widget=lambda: st.number_input(
                        "D_eff (m²/s)", 1e-12, 1e-8, 1e-10, format="%.1e",
                        key="m3_Deff", label_visibility="collapsed",
                    ),
                )
                k_deact = _lw_m3(
                    "Deactivation rate k_d",
                    help="First-order enzyme deactivation rate constant. 0 → no decay (idealised).",
                    unit="1/s",
                    widget=lambda: st.number_input(
                        "k_d (1/s)", 0.0, 1e-3, 0.0, format="%.1e",
                        key="m3_kd", label_visibility="collapsed",
                    ),
                )
                cat_time_h = _lw_m3(
                    "Simulation time",
                    help="Total reaction time horizon for the catalysis simulation.",
                    unit="h",
                    widget=lambda: st.number_input(
                        "Sim. time (h)", 0.1, 48.0, 1.0,
                        key="m3_cat_t", label_visibility="collapsed",
                    ),
                )
        _recipe = ensure_process_recipe_state(st.session_state)
        _recipe = sync_m3_ui_to_recipe(
            _recipe,
            application_mode=m3_app_mode,
            chromatography_mode=chrom_mode,
            column_diameter_mm=float(col_diam_mm),
            bed_height_cm=float(bed_height_cm),
            bed_porosity=float(bed_porosity),
            flow_rate_mL_min=float(flow_rate_mL),
            feed_concentration_mg_mL=float(C_feed_mg),
            feed_duration_min=float(feed_dur_min),
            total_time_min=float(total_time_min),
            bind_pH=float(bind_pH),
            bind_conductivity_mS_cm=float(bind_cond),
            wash_duration_min=float(wash_dur_min),
            elute_pH=float(elute_pH),
            elute_conductivity_mS_cm=float(elute_cond),
            elute_duration_min=float(elute_dur_min),
            gradient_start_mM=float(grad_start),
            gradient_end_mM=float(grad_end),
            gradient_duration_min=float(grad_dur_min),
        )
        save_process_recipe_state(st.session_state, _recipe)

        # ── Run M3 Button ────────────────────────────────────────────────
        st.divider()
        _m3_can_run = "m2_result" in st.session_state
        m3_run_btn = st.button("\u25b6 Run M3: Performance Simulation", type="primary",
                                use_container_width=True, disabled=not _m3_can_run)

        if m3_run_btn:
            with st.spinner("Running Module 3: Performance simulation..."):
                from dpsim.module3_performance.hydrodynamics import ColumnGeometry
                m2r = st.session_state["m2_result"]
                _recipe = ensure_process_recipe_state(st.session_state)
                _recipe = sync_m3_ui_to_recipe(
                    _recipe,
                    application_mode=m3_app_mode,
                    chromatography_mode=chrom_mode,
                    column_diameter_mm=float(col_diam_mm),
                    bed_height_cm=float(bed_height_cm),
                    bed_porosity=float(bed_porosity),
                    flow_rate_mL_min=float(flow_rate_mL),
                    feed_concentration_mg_mL=float(C_feed_mg),
                    feed_duration_min=float(feed_dur_min),
                    total_time_min=float(total_time_min),
                    bind_pH=float(bind_pH),
                    bind_conductivity_mS_cm=float(bind_cond),
                    wash_duration_min=float(wash_dur_min),
                    elute_pH=float(elute_pH),
                    elute_conductivity_mS_cm=float(elute_cond),
                    elute_duration_min=float(elute_dur_min),
                    gradient_start_mM=float(grad_start),
                    gradient_end_mM=float(grad_end),
                    gradient_duration_min=float(grad_dur_min),
                )
                _resolved = resolve_lifecycle_inputs(
                    _recipe,
                    base_params=st.session_state.get("params"),
                )
                if _resolved.validation.blockers:
                    for _issue in _resolved.validation.blockers:
                        st.error(f"Recipe blocker: {_issue.module} {_issue.code}: {_issue.message}")
                    st.stop()
                save_process_recipe_state(st.session_state, _recipe)
                _recipe_column = _resolved.column
                column = ColumnGeometry(
                    diameter=_recipe_column.diameter,
                    bed_height=_recipe_column.bed_height,
                    particle_diameter=m2r.m1_contract.bead_d50,
                    bed_porosity=_recipe_column.bed_porosity,
                    particle_porosity=m2r.m1_contract.porosity,
                    G_DN=m2r.G_DN_updated,
                    E_star=m2r.E_star_updated,
                )
                _recipe_flow_rate = _resolved.m3_flow_rate
                _recipe_feed_conc = _resolved.m3_feed_concentration
                _recipe_feed_duration = _resolved.m3_feed_duration
                _recipe_total_time = _resolved.m3_total_time
                st.session_state["m3_feed_concentration_mol_m3"] = _recipe_feed_conc
                st.session_state.pop("m3_result_bt", None)
                st.session_state.pop("m3_result_ge", None)
                st.session_state.pop("m3_result_method", None)
                st.session_state.pop("m3_result_cat", None)

                if m3_app_mode == "Chromatography":
                    from dpsim.module3_performance import (
                        run_breakthrough,
                        CompetitiveLangmuirIsotherm, run_gradient_elution,
                        run_chromatography_method,
                    )
                    from dpsim.module3_performance.gradient import make_linear_gradient
                    from dpsim.visualization.ui_validators import validate_m3_chromatography, validate_m3_result
                    C_feed_mol = _recipe_feed_conc

                    _is_grad = (chrom_mode == "Gradient Elution")
                    _col_val = validate_m3_chromatography(
                        flow_rate=_recipe_flow_rate, column=column,
                        isotherm_type="competitive_langmuir" if _is_grad else "langmuir",
                        gradient_enabled=_is_grad,
                    )
                    for _blk in _col_val.blockers:
                        st.warning(f"M3 input blocker: {_blk}")
                    for _wrn in _col_val.warnings:
                        st.info(f"M3 note: {_wrn}")

                    if not _col_val.blockers:
                        try:
                            if chrom_mode == "Breakthrough":
                                bt = run_breakthrough(
                                    column, microsphere=m2r,
                                    C_feed=C_feed_mol, flow_rate=_recipe_flow_rate,
                                    feed_duration=_recipe_feed_duration,
                                    total_time=_recipe_total_time,
                                    extinction_coeff=ext_coeff,
                                )
                                st.session_state["m3_result_bt"] = bt
                                _res_val = validate_m3_result(
                                    mass_balance_error=bt.mass_balance_error,
                                    pressure_drop=bt.pressure_drop,
                                )
                                st.session_state["m3_result_val"] = _res_val
                            elif chrom_mode == "Protein A Method":
                                try:
                                    from dpsim.module2_functionalization.orchestrator import (
                                        build_functional_media_contract,
                                    )
                                    _fmc_ui = build_functional_media_contract(m2r)
                                except Exception:
                                    _fmc_ui = None
                                method = run_chromatography_method(
                                    column,
                                    method_steps=_resolved.m3_method_steps,
                                    fmc=_fmc_ui,
                                )
                                st.session_state["m3_result_method"] = method
                                if method.load_breakthrough is not None:
                                    st.session_state["m3_result_bt"] = method.load_breakthrough
                            else:
                                gradient = make_linear_gradient(
                                    grad_start / 1000.0, grad_end / 1000.0, 0, grad_dur_min * 60
                                )
                                comp_iso = CompetitiveLangmuirIsotherm(
                                    q_max=np.array([q_max]),
                                    K_L=np.array([K_L_m3]),
                                )
                                # v0.2.0 (A6): pass FMC so the gradient-elution
                                # manifest tier inherits from M2 calibration
                                # state instead of being floored at
                                # SEMI_QUANTITATIVE.
                                ge = run_gradient_elution(
                                    column,
                                    C_feed=np.array([C_feed_mol]),
                                    gradient=gradient,
                                    flow_rate=_recipe_flow_rate,
                                    total_time=_recipe_total_time,
                                    isotherm=comp_iso,
                                    feed_duration=_recipe_feed_duration,
                                    fmc=_fmc_ui,
                                )
                                st.session_state["m3_result_ge"] = ge
                        except Exception as _m3_ex:
                            st.error(f"Module 3 chromatography failed: {_m3_ex}")

                elif m3_app_mode == "Catalysis":
                    from dpsim.module3_performance.catalysis.packed_bed import solve_packed_bed
                    K_m_mol = K_m
                    S_feed_mol = S_feed
                    try:
                        cat = solve_packed_bed(
                            bed_length=bed_height_cm / 100,
                            bed_diameter=col_diam_mm / 1000,
                            particle_diameter=m2r.m1_contract.bead_d50,
                            bed_porosity=bed_porosity,
                            particle_porosity=m2r.m1_contract.porosity,
                            V_max=V_max, K_m=K_m_mol, S_feed=S_feed_mol,
                            flow_rate=flow_rate_mL / 60e6,
                            D_eff=D_eff, k_deact=k_deact,
                            total_time=cat_time_h * 3600,
                        )
                        st.session_state["m3_result_cat"] = cat
                    except Exception as _m3_ex:
                        st.error(f"Module 3 catalysis failed: {_m3_ex}")
            st.rerun()

        # ── M3 Results Display ───────────────────────────────────────────
        from dpsim.visualization.plots_m3 import (
            plot_chromatogram, plot_breakthrough_curve, plot_peak_table,
            plot_michaelis_menten, plot_effectiveness_factor, plot_activity_decay,
            plot_conversion_vs_time, plot_pressure_flow_curve,
        )

        _show_m3_bt = "m3_result_bt" in st.session_state
        _show_m3_ge = "m3_result_ge" in st.session_state
        _show_m3_method = "m3_result_method" in st.session_state
        _show_m3_cat = "m3_result_cat" in st.session_state

        if _show_m3_bt or _show_m3_ge or _show_m3_method or _show_m3_cat:
            st.divider()
            st.header("M3 Results")

            # Build sub-tabs for M3 results
            _m3_sub_labels = []
            if _show_m3_bt:
                _m3_sub_labels.append("Breakthrough")
            if _show_m3_ge:
                _m3_sub_labels.append("Gradient Elution")
            if _show_m3_method:
                _m3_sub_labels.append("Protein A Method")
            if _show_m3_cat:
                _m3_sub_labels.append("\u2697\ufe0f Catalysis")

            _m3_subs = st.tabs(_m3_sub_labels)
            _m3_idx = 0

            if _show_m3_bt:
                with _m3_subs[_m3_idx]:
                    from dpsim.visualization.ui_validators import validate_m3_result as _val_m3_res
                    _bt = st.session_state["m3_result_bt"]
                    st.subheader("Breakthrough Chromatography")
                    _bt_badge = _m3_evidence_tier_badge(_bt)
                    if _bt_badge:
                        st.caption(_bt_badge)

                    _mb_pct = abs(_bt.mass_balance_error) * 100.0
                    if _mb_pct > 5.0:
                        st.error(f"Mass balance error = {_mb_pct:.1f}% \u2014 results numerically unreliable.")
                    elif _mb_pct > 2.0:
                        st.warning(f"Mass balance error = {_mb_pct:.1f}% \u2014 treat with caution.")
                    else:
                        st.success(f"Mass balance error = {_mb_pct:.2f}% \u2014 acceptable.")

                    _bt_val = _val_m3_res(mass_balance_error=_bt.mass_balance_error,
                                          pressure_drop=_bt.pressure_drop)
                    if _bt_val.blockers:
                        for _blk in _bt_val.blockers:
                            st.error(f"Blocker: {_blk}")

                    _dbc_c1, _dbc_c2, _dbc_c3, _dbc_c4 = st.columns(4)
                    _dbc_c1.metric("DBC\u2085%", f"{_bt.dbc_5pct:.1f} mol/m\u00b3" if not np.isnan(_bt.dbc_5pct) else "N/A")
                    _dbc_c2.metric("DBC\u2081\u2080%", f"{_bt.dbc_10pct:.1f} mol/m\u00b3" if not np.isnan(_bt.dbc_10pct) else "N/A")
                    _dbc_c3.metric("DBC\u2085\u2080%", f"{_bt.dbc_50pct:.1f} mol/m\u00b3" if not np.isnan(_bt.dbc_50pct) else "N/A")
                    _dbc_c4.metric("Pressure drop", f"{_bt.pressure_drop / 1000:.1f} kPa")

                    st.divider()
                    _C_feed_mol_bt = st.session_state.get(
                        "m3_feed_concentration_mol_m3",
                        mg_mL_to_mol_m3(C_feed_mg, 66500.0),
                    )
                    st.plotly_chart(
                        plot_breakthrough_curve(
                            time=_bt.time, C_outlet=_bt.C_outlet, C_feed=_C_feed_mol_bt,
                            dbc_5=_bt.dbc_5pct, dbc_10=_bt.dbc_10pct, dbc_50=_bt.dbc_50pct,
                        ), use_container_width=True,
                    )
                    st.plotly_chart(
                        plot_chromatogram(time=_bt.time, uv_signal=_bt.uv_signal),
                        use_container_width=True,
                    )

                    if "m2_result" in st.session_state:
                        from dpsim.module3_performance.hydrodynamics import ColumnGeometry as _CG_bt
                        _m2r_bt = st.session_state["m2_result"]
                        _col_bt = _CG_bt(
                            diameter=col_diam_mm / 1000, bed_height=bed_height_cm / 100,
                            particle_diameter=_m2r_bt.m1_contract.bead_d50,
                            bed_porosity=bed_porosity,
                            particle_porosity=_m2r_bt.m1_contract.porosity,
                            G_DN=_m2r_bt.G_DN_updated, E_star=_m2r_bt.E_star_updated,
                        )
                        st.plotly_chart(plot_pressure_flow_curve(_col_bt), use_container_width=True)

                    st.caption(
                        "Mechanistic prediction: Lumped Rate Model (LRM) with Langmuir isotherm. "
                        "DBC values are model-based \u2014 calibrate isotherm parameters with batch uptake experiments."
                    )
                _m3_idx += 1

            if _show_m3_ge:
                with _m3_subs[_m3_idx]:
                    _ge = st.session_state["m3_result_ge"]
                    st.subheader("Gradient Elution Chromatography")
                    _ge_badge = _m3_evidence_tier_badge(_ge)
                    if _ge_badge:
                        st.caption(_ge_badge)

                    _grad_affects = getattr(_ge, "gradient_affects_binding", False)
                    if _grad_affects:
                        st.success("Gradient affects binding: YES - selected isotherm is gradient-sensitive.")
                    else:
                        st.info("Gradient affects binding: NO - plain competitive Langmuir is diagnostic/display only.")

                    _ge_time = getattr(_ge, "time", None)
                    _ge_uv = getattr(_ge, "uv_signal", None)
                    _ge_grad = getattr(_ge, "gradient_values", None)
                    if _ge_time is not None and _ge_uv is not None:
                        st.plotly_chart(
                            plot_chromatogram(
                                time=_ge_time, uv_signal=_ge_uv,
                                gradient_values=_ge_grad, gradient_affects_binding=_grad_affects,
                            ), use_container_width=True,
                        )

                    _ge_peaks = getattr(_ge, "peaks", [])
                    st.plotly_chart(plot_peak_table(_ge_peaks), use_container_width=True)

                    st.caption(
                        "Ranking only - gradient-sensitive adapters update binding during elution; "
                        "plain competitive Langmuir remains diagnostic. Quantitative yields require "
                        "isotherm calibration."
                    )
                _m3_idx += 1

            if _show_m3_method:
                with _m3_subs[_m3_idx]:
                    _method = st.session_state["m3_result_method"]
                    st.subheader("Protein A Method Operation")
                    _method_badge = _m3_evidence_tier_badge(_method)
                    if _method_badge:
                        st.caption(_method_badge)
                    _pa = _method.protein_a
                    _op = _method.operability
                    _eff = _method.column_efficiency
                    _imp = _method.impurity_clearance
                    # v0.3.0 (B6): cycle-life as bucketed ranking when no
                    # calibration is loaded, so users do not read a precise
                    # number off a screening correlation that is UNSUPPORTED
                    # without resin-cycling assays.
                    from dpsim.module3_performance.method import (
                        cycle_lifetime_label,
                        is_method_calibrated,
                    )
                    _calibrated = is_method_calibrated(_fmc_ui)
                    _pm1, _pm2, _pm3, _pm4 = st.columns(4)
                    _pm1.metric("Elution recovery", f"{_pa.predicted_elution_recovery_fraction:.1%}")
                    if _calibrated:
                        _pm2.metric(
                            "Cycle lifetime",
                            f"{_pa.cycle_lifetime_to_70pct_capacity:.0f}",
                        )
                    else:
                        _pm2.metric(
                            "Cycle lifetime",
                            cycle_lifetime_label(_pa, is_calibrated=False),
                        )
                    _pm3.metric("Asymmetry", f"{_eff.asymmetry_factor:.2f}")
                    _pm4.metric("Impurity risk", _imp.risk)
                    st.caption(
                        f"Pressure={_op.pressure_drop_Pa / 1000:.1f} kPa; "
                        f"N={_eff.theoretical_plates:.0f}; "
                        f"HETP={_eff.hetp_m * 1000:.2f} mm; "
                        f"wash={_imp.wash_column_volumes:.2f} CV."
                    )
                    if _method.loaded_elution is not None:
                        _elu = _method.loaded_elution
                        st.plotly_chart(
                            plot_chromatogram(
                                time=_elu.time,
                                uv_signal=_elu.uv_signal,
                                gradient_values=_elu.pH_profile,
                                gradient_affects_binding=True,
                            ),
                            use_container_width=True,
                        )
                    for _wrn in _pa.warnings + _eff.warnings + _imp.warnings:
                        st.info(_wrn)
                _m3_idx += 1

            if _show_m3_cat:
                with _m3_subs[_m3_idx]:
                    _cat = st.session_state["m3_result_cat"]
                    st.subheader("Packed-Bed Catalytic Reactor")

                    _cat_c1, _cat_c2, _cat_c3, _cat_c4 = st.columns(4)
                    _cat_c1.metric("Final Conversion", f"{_cat.conversion:.1%}")
                    _cat_c2.metric("Effectiveness Factor \u03b7", f"{_cat.effectiveness_factor:.3f}")
                    _cat_c3.metric("Thiele Modulus \u03a6", f"{_cat.thiele_modulus:.2f}")
                    _cat_c4.metric("Productivity", f"{_cat.productivity:.3e} mol/(m\u00b3\u00b7s)")

                    _mb_cat_pct = abs(_cat.mass_balance_error) * 100.0
                    if _mb_cat_pct > 5.0:
                        st.error(f"Catalysis mass balance error = {_mb_cat_pct:.1f}% \u2014 results unreliable.")
                    elif _mb_cat_pct > 2.0:
                        st.warning(f"Catalysis mass balance error = {_mb_cat_pct:.1f}% \u2014 treat with caution.")
                    else:
                        st.success(f"Catalysis mass balance error = {_mb_cat_pct:.2f}% \u2014 acceptable.")

                    st.divider()
                    _time_h_cat = _cat.time / 3600.0
                    _S_in = float(_cat.S_outlet[0]) if len(_cat.S_outlet) > 0 else 1.0
                    if _S_in <= 0:
                        _S_in = S_feed
                    _conversion_arr = np.clip(1.0 - _cat.S_outlet / max(_S_in, 1e-12), 0.0, 1.0)
                    st.plotly_chart(
                        plot_conversion_vs_time(time_hours=_time_h_cat, conversion=_conversion_arr),
                        use_container_width=True,
                    )

                    _S_range_mm = np.linspace(0.01, max(S_feed * 3, 10.0), 200)
                    st.plotly_chart(
                        plot_michaelis_menten(
                            S_range=_S_range_mm, V_max=V_max, K_m=K_m,
                            eta=_cat.effectiveness_factor,
                        ), use_container_width=True,
                    )

                    _phi_range = np.logspace(-2, 2, 200)
                    st.plotly_chart(plot_effectiveness_factor(_phi_range), use_container_width=True)

                    if hasattr(_cat, "activity_history") and len(_cat.activity_history) > 0:
                        st.plotly_chart(
                            plot_activity_decay(time_hours=_time_h_cat, activity=_cat.activity_history),
                            use_container_width=True,
                        )

                    _phi_val = _cat.thiele_modulus
                    if _phi_val < 0.3:
                        st.success(f"Thiele modulus \u03a6 = {_phi_val:.2f} \u2014 kinetic regime (no diffusion limitation).")
                    elif _phi_val < 3.0:
                        st.warning(f"Thiele modulus \u03a6 = {_phi_val:.2f} \u2014 transition regime (partial diffusion limitation).")
                    else:
                        st.error(f"Thiele modulus \u03a6 = {_phi_val:.2f} \u2014 diffusion-limited regime. "
                                 "Effectiveness factor \u03b7 is significantly < 1. Consider smaller particles or higher D_eff.")

                    st.caption(
                        "Mechanistic prediction: Transient PFR with Michaelis-Menten kinetics, "
                        "Thiele modulus effectiveness factor, and first-order deactivation. "
                        "K_m and V_max require calibration against your specific enzyme."
                    )

