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
        st.header("Module 3: Performance Characterization")

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
        m3_app_mode = st.radio("Application", ["Chromatography", "Catalysis"], key="m3_mode")

        st.subheader("Column/Reactor")
        _m3c1, _m3c2 = st.columns(2)
        with _m3c1:
            col_diam_mm = st.number_input("Column I.D. (mm)", 1.0, 50.0, 10.0, key="m3_col_d")
            bed_height_cm = st.number_input("Bed height (cm)", 1.0, 30.0, 10.0, key="m3_bed_h")
        with _m3c2:
            bed_porosity = st.slider("Bed porosity", 0.25, 0.50, 0.38, step=0.01, key="m3_eps_b")
            flow_rate_mL = st.number_input("Flow rate (mL/min)", 0.01, 20.0, 1.0, step=0.1, key="m3_flow")

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
            chrom_mode = st.radio(
                "Mode",
                ["Breakthrough", "Gradient Elution", "Protein A Method"],
                key="m3_chrom_mode",
            )

            st.subheader("Feed")
            C_feed_mg = st.number_input("Feed conc. (mg/mL)", 0.01, 50.0, 1.0, key="m3_Cfeed")
            feed_dur_min = st.number_input("Feed duration (min)", 1.0, 60.0, 10.0, key="m3_feed_dur")
            total_time_min = st.number_input("Total time (min)", 5.0, 120.0, 20.0, key="m3_total_t")

            st.subheader("Isotherm")
            q_max = st.number_input("q_max (mol/m\u00b3)", 1.0, 500.0, 100.0, key="m3_qmax")
            K_L_m3 = st.number_input("K_L (m\u00b3/mol)", 10.0, 1e5, 1000.0, key="m3_KL")
            st.caption("Default isotherm parameters are illustrative \u2014 user calibration required.")

            ext_coeff = st.number_input(
                "\u03b5\u2082\u2088\u2080 (1/(M\u00b7cm))", 1000.0, 200000.0, 36000.0, key="m3_ext"
            )

            if chrom_mode == "Gradient Elution":
                st.subheader("Gradient")
                grad_start = st.number_input("Start (mM)", 0.0, 1000.0, 0.0, key="m3_grad_start")
                grad_end = st.number_input("End (mM)", 0.0, 1000.0, 500.0, key="m3_grad_end")
                grad_dur_min = st.number_input("Duration (min)", 1.0, 60.0, 10.0, key="m3_grad_dur")
            elif chrom_mode == "Protein A Method":
                st.subheader("Method Buffers")
                _m3m1, _m3m2 = st.columns(2)
                with _m3m1:
                    bind_pH = st.number_input("Bind/wash pH", 5.0, 9.5, 7.4, step=0.1, key="m3_bind_pH")
                    bind_cond = st.number_input("Bind/wash conductivity (mS/cm)", 1.0, 40.0, 15.0, step=0.5, key="m3_bind_cond")
                    wash_dur_min = st.number_input("Wash duration (min)", 1.0, 60.0, 5.0, key="m3_wash_dur")
                with _m3m2:
                    elute_pH = st.number_input("Elution pH", 2.5, 5.0, 3.5, step=0.1, key="m3_elute_pH")
                    elute_cond = st.number_input("Elution conductivity (mS/cm)", 1.0, 40.0, 5.0, step=0.5, key="m3_elute_cond")
                    elute_dur_min = st.number_input("Elution duration (min)", 1.0, 60.0, 5.0, key="m3_elute_dur")

        elif m3_app_mode == "Catalysis":
            st.subheader("Enzyme Kinetics")
            V_max = st.number_input("V_max (mol/(m\u00b3\u00b7s))", 0.001, 100.0, 1.0, key="m3_Vmax")
            K_m = st.number_input("K_m (mM)", 0.01, 100.0, 1.0, key="m3_Km")
            S_feed = st.number_input("Substrate feed (mM)", 0.1, 100.0, 10.0, key="m3_Sfeed")
            D_eff = st.number_input("D_eff (m\u00b2/s)", 1e-12, 1e-8, 1e-10, format="%.1e", key="m3_Deff")
            k_deact = st.number_input("k_d (1/s)", 0.0, 1e-3, 0.0, format="%.1e", key="m3_kd")
            cat_time_h = st.number_input("Sim. time (h)", 0.1, 48.0, 1.0, key="m3_cat_t")

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
            st.header("\U0001f4ca M3 Results")

            # Build sub-tabs for M3 results
            _m3_sub_labels = []
            if _show_m3_bt:
                _m3_sub_labels.append("\U0001f4ca Breakthrough")
            if _show_m3_ge:
                _m3_sub_labels.append("\U0001f4ca Gradient Elution")
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

