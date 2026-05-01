"""M1 Fabrication tab — extracted from app.py for UI restructure.

v6.0: Renders the complete M1 Fabrication tab including inputs, run button,
results display, optimization assessment, trust assessment, and calibration.
All widget keys preserved exactly (m1_* prefix).
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import streamlit as st

from dpsim.datatypes import (
    SimulationParameters, FormulationParameters,
    EmulsificationParameters, MixerGeometry, SolverSettings,
    VesselGeometry, StirrerGeometry, HeatingConfig, KernelConfig,
    ModelMode, ModelEvidenceTier,
)


def _evidence_badge(result_obj) -> str:
    """Return a colored evidence tier badge string for UI display."""
    manifest = getattr(result_obj, "model_manifest", None)
    if manifest is None:
        return ""
    tier = manifest.evidence_tier
    _COLORS = {
        ModelEvidenceTier.VALIDATED_QUANTITATIVE: ":green[VALIDATED]",
        ModelEvidenceTier.CALIBRATED_LOCAL: ":green[CALIBRATED]",
        ModelEvidenceTier.SEMI_QUANTITATIVE: ":orange[SEMI-QUANTITATIVE]",
        ModelEvidenceTier.QUALITATIVE_TREND: ":red[QUALITATIVE TREND]",
        ModelEvidenceTier.UNSUPPORTED: ":red[UNSUPPORTED]",
    }
    badge = _COLORS.get(tier, str(tier.value))
    model_name = manifest.model_name
    return f"Evidence: {badge} | Model: `{model_name}`"
from dpsim.properties.database import PropertyDatabase
from dpsim.trust import assess_trust
# v0.3.0 (B5): M1 runs route through the lifecycle layer's recipe-driven
# helper rather than importing PipelineOrchestrator directly. This satisfies
# the architect-coherence-audit D1 finding (dual-API surface in tab_m1).
from dpsim.lifecycle import resolve_lifecycle_inputs, run_m1_from_recipe
from dpsim.visualization.plots import (
    plot_droplet_size_distribution,
    plot_phase_field,
    plot_crosslinking_kinetics,
    plot_hertz_contact,
    plot_kav_curve,
    plot_results_dashboard,
    plot_modulus_comparison,
)
from dpsim.visualization.ui_recipe import (
    ensure_process_recipe_state,
    save_process_recipe_state,
    sync_m1_ui_to_recipe,
)
from dpsim.visualization.ui_validators import validate_m1_inputs as _validate_m1


def _render_non_ac_family(*, tab_container, family, is_stirred_default, model_mode_enum, _smgr) -> None:
    """Render the M1 tab for alginate / cellulose / PLGA (v9.0 M5-M7).

    Shares Hardware Mode + shared L1 inputs (RPM, time, phi_d, v_oil/v_poly)
    with the A+C path, but dispatches to the family-specific formulation
    module and builds SimulationParameters with polymer_family set so the
    orchestrator routes through _run_alginate / _run_cellulose / _run_plga.
    """
    from dpsim.visualization.tabs.m1.hardware_section import render_hardware_mode_radio
    from dpsim.datatypes import PolymerFamily

    from dpsim.visualization.design import chrome as _chrome_nac
    m1_col_left, m1_col_right = st.columns(2)
    with m1_col_left:
        with st.container(border=True):
            # v0.4.17 (P6): deferred header for non-A+C parity with the
            # A+C path. The tip-speed chip on the header right slot needs
            # the live RPM + stirrer geometry that the widgets below own.
            _hw_header_slot_nac = st.empty()
            is_stirred = render_hardware_mode_radio()
            from dpsim.visualization.tabs.m1.vessel_mode import (
                render_planned_modes_strip as _planned_strip_nac,
            )
            _planned_strip_nac()

            # v0.4.5: non-AC family path migrated to labeled_widget for parity
            # with the AC stirred branch.
            from dpsim.visualization.help import get_help, labeled_widget as _lw_nac
            if is_stirred:
                vessel_choice = _lw_nac(
                    "Vessel",
                    help="Glass beaker uses flat-plate heating; jacketed vessel uses circulating hot water with steadier setpoint control.",
                    widget=lambda: st.selectbox(
                        "Vessel", ["Glass Beaker (100 mm)", "Jacketed Vessel (92 mm)"],
                        key="m1_vessel", label_visibility="collapsed",
                    ),
                )
                stirrer_choice = _lw_nac(
                    "Stirrer",
                    help="Pitched-blade (Stirrer A): mixed axial+radial flow, moderate shear. Rotor-stator (Stirrer B): high-shear annular zone — used for fine emulsification.",
                    widget=lambda: st.selectbox(
                        "Stirrer", ["Stirrer A - Pitched Blade (59 mm)", "Stirrer B - Rotor-Stator (32 mm)"],
                        key="m1_stirrer", label_visibility="collapsed",
                    ),
                )
                is_stirrer_A = "Pitched" in stirrer_choice
                rpm = _lw_nac(
                    "Stirrer speed",
                    help=get_help("m1.hardware.stir_rpm"),
                    unit="rpm",
                    widget=lambda: st.slider(
                        "Stirrer Speed (RPM)", 800, 2500 if is_stirrer_A else 9000,
                        1300 if is_stirrer_A else 1800,
                        step=50 if is_stirrer_A else 100,
                        key="m1_rpm" if is_stirrer_A else "m1_rpm_rs",
                        label_visibility="collapsed",
                    ),
                )
                t_emul = _lw_nac(
                    "Emulsification time",
                    help="Hold time at full stirring. Drives PBE convergence.",
                    unit="min",
                    widget=lambda: st.number_input(
                        "Emulsification Time (min)", 1, 60, 10,
                        key="m1_t_emul", label_visibility="collapsed",
                    ),
                )
                v_oil_mL = _lw_nac(
                    "Oil + surfactant",
                    help="Continuous-phase volume.",
                    unit="mL",
                    widget=lambda: st.slider(
                        "Oil + surfactant (mL)", 100, 500, 300, step=10,
                        key="m1_v_oil", label_visibility="collapsed",
                    ),
                )
                v_poly_mL = _lw_nac(
                    "Dispersed phase",
                    help="Dispersed-phase volume (polysaccharide / PLGA-DCM / cellulose-solvent).",
                    unit="mL",
                    widget=lambda: st.slider(
                        "Dispersed phase (mL)", 50, 300, 200, step=10,
                        key="m1_v_poly", label_visibility="collapsed",
                    ),
                )
                total_mL = v_oil_mL + v_poly_mL
                phi_d = v_poly_mL / total_mL
                # v0.4.17 (P6): non-A+C Hardware metrics — chip in
                # deferred header, derived-metrics rail, volumes readout.
                from dpsim.visualization.tabs.m1.hardware_metrics import (
                    compute_hardware_metrics,
                    render_metrics_rail,
                    render_tip_speed_chip,
                    render_volumes_readout,
                )
                _impeller_d_m_nac = 0.059 if is_stirrer_A else 0.0257
                _hw_ctx_nac = compute_hardware_metrics(
                    rpm=float(rpm),
                    impeller_diameter_m=_impeller_d_m_nac,
                )
                render_metrics_rail(_hw_ctx_nac)
                render_volumes_readout(
                    v_oil_mL=v_oil_mL, v_poly_mL=v_poly_mL,
                )
                _hw_header_slot_nac.html(
                    _chrome_nac.card_header_strip(
                        eyebrow_text="Hardware · Emulsification (L1)",
                        title="Stirred vessel · v9.0 in-M1",
                        right_html=render_tip_speed_chip(_hw_ctx_nac),
                    )
                )
            else:
                rpm = _lw_nac(
                    "Rotor speed",
                    help="Rotor-stator RPM (legacy path). Driver of high-shear zone in the annular gap.",
                    unit="rpm",
                    widget=lambda: st.slider(
                        "Rotor Speed (RPM)", 3000, 25000, 10000, step=500,
                        key="m1_rpm_leg", label_visibility="collapsed",
                    ),
                )
                t_emul = _lw_nac(
                    "Emulsification time",
                    unit="min",
                    widget=lambda: st.number_input(
                        "Emulsification Time (min)", 1, 60, 10,
                        key="m1_t_emul_leg", label_visibility="collapsed",
                    ),
                )
                phi_d = _lw_nac(
                    "Dispersed-phase fraction (φ_d)",
                    help="Volume fraction of the dispersed (aqueous polymer) phase. Above ~0.30 the emulsion is prone to inversion.",
                    widget=lambda: st.slider(
                        "Dispersed Phase Fraction (phi_d)", 0.01, 0.30, 0.05, step=0.01,
                        key="m1_phi_d", label_visibility="collapsed",
                    ),
                )
                v_oil_mL, v_poly_mL, total_mL = 300, 200, 500
                # v0.4.17 (P6): fill deferred header for non-A+C legacy
                # rotor-stator branch. No chip — gap-driven shear, no
                # deterministic impeller diameter to compute v_tip from.
                _hw_header_slot_nac.html(
                    _chrome_nac.card_header_strip(
                        eyebrow_text="Hardware · Emulsification (L1)",
                        title="Rotor-stator (legacy)",
                    )
                )

    # Compare families by .value to survive importlib.reload of datatypes
    # (see tab_m1.py family-dispatch comment and RunReport.compute_min_tier).
    family_value = getattr(family, "value", family)
    # Type annotation as a Union so mypy accepts each of the three assignments
    # below and so downstream code can use isinstance-narrowing to access
    # family-specific fields.
    from typing import Union
    from dpsim.visualization.tabs.m1.formulation_alginate import (
        AlginateContext,
        render_formulation_alginate,
    )
    from dpsim.visualization.tabs.m1.formulation_cellulose import (
        CelluloseContext,
        render_formulation_cellulose,
    )
    from dpsim.visualization.tabs.m1.formulation_plga import (
        PLGAContext,
        render_formulation_plga,
    )
    fctx: Union[AlginateContext, CelluloseContext, PLGAContext]
    _family_titles = {
        PolymerFamily.ALGINATE.value: ("Formulation · Alginate", "Ionotropic gelation phase"),
        PolymerFamily.CELLULOSE.value: ("Formulation · Cellulose (NIPS)", "Solvent-non-solvent phase"),
        PolymerFamily.PLGA.value: ("Formulation · PLGA", "Solvent-evaporation phase"),
    }
    _eyebrow, _title = _family_titles.get(
        family_value, ("Formulation", str(family_value)),
    )
    with m1_col_right:
        with st.container(border=True):
            st.html(
                _chrome_nac.card_header_strip(
                    eyebrow_text=_eyebrow,
                    title=_title,
                )
            )
            if family_value == PolymerFamily.ALGINATE.value:
                fctx = render_formulation_alginate(is_stirred=is_stirred)
            elif family_value == PolymerFamily.CELLULOSE.value:
                fctx = render_formulation_cellulose(is_stirred=is_stirred)
            elif family_value == PolymerFamily.PLGA.value:
                fctx = render_formulation_plga(is_stirred=is_stirred)
            else:
                st.error(f"Unknown family: {family_value}")
                return

    st.divider()
    run_btn = st.button(
        "\u25b6 Run M1: Fabrication Pipeline", type="primary",
        use_container_width=True, key="m1v9_run_non_ac",
    )
    if not run_btn:
        return

    # ── Build SimulationParameters for the selected family ──────────────
    if is_stirred:
        if "Beaker" in vessel_choice:
            vessel = VesselGeometry.glass_beaker(working_volume=total_mL * 1e-6)
            heating = HeatingConfig.flat_plate()
        else:
            vessel = VesselGeometry.jacketed_vessel(working_volume=total_mL * 1e-6)
            heating = HeatingConfig.hot_water_jacket()
        stirrer = StirrerGeometry.pitched_blade_A() if is_stirrer_A else StirrerGeometry.rotor_stator_B()
        heating.T_initial = fctx.T_oil_C + 273.15
        kernels = KernelConfig.for_stirrer_type(stirrer.stirrer_type)
        emul = EmulsificationParameters(
            mode="stirred_vessel", rpm=float(rpm),
            t_emulsification=float(t_emul * 60),
            vessel=vessel, stirrer=stirrer, heating=heating, kernels=kernels,
        )
    else:
        emul = EmulsificationParameters(
            mode="rotor_stator_legacy", rpm=float(rpm),
            t_emulsification=float(t_emul * 60),
            mixer=MixerGeometry(),
        )

    formulation = FormulationParameters(
        c_span80=fctx.c_span80_pct * 10.0,
        T_oil=fctx.T_oil_C + 273.15,
        phi_d=phi_d,
        c_span80_vol_pct=fctx.c_span80_vol_pct,
        v_oil_span80_mL=float(v_oil_mL),
        v_polysaccharide_mL=float(v_poly_mL),
    )

    props_overrides: dict = {"polymer_family": family}
    if family_value == PolymerFamily.ALGINATE.value and isinstance(fctx, AlginateContext):
        formulation.c_alginate = fctx.c_alginate_kg_m3
        if fctx.c_Ca_bath_mM > 0:
            # External CaCl2 bath: direct concentration.
            formulation.c_Ca_bath = fctx.c_Ca_bath_mM
        else:
            # Internal release (GDL+CaCO3): lumped-parameter approximation
            # c_eff(t) = C_source * (1 - exp(-k*t)) per Draget 1997. Use the
            # gelant profile's recommended t_default as the process time.
            from dpsim.reagent_library_alginate import (
                GELANTS_ALGINATE,
                effective_bath_concentration,
            )
            profile = GELANTS_ALGINATE.get(fctx.gelant_key)
            if profile is not None and profile.mode == "internal_release":
                # Recompute with the UI-provided k_release (which overrides
                # profile.k_release when the user adjusts it) by building a
                # synthetic profile with the current widget values.
                from dataclasses import replace
                live_profile = replace(
                    profile,
                    C_Ca_source=fctx.C_Ca_source_mM,
                    k_release=fctx.k_release_1_s,
                )
                formulation.c_Ca_bath = effective_bath_concentration(
                    live_profile, profile.t_default,
                )
            else:
                formulation.c_Ca_bath = fctx.C_Ca_source_mM
    elif family_value == PolymerFamily.CELLULOSE.value and isinstance(fctx, CelluloseContext):
        formulation.phi_cellulose_0 = fctx.phi_cellulose_0
        formulation.solvent_system = fctx.solvent_system
        formulation.cooling_rate = fctx.cooling_rate_Cmin / 60.0 if fctx.cooling_rate_Cmin > 0 else 0.0
    elif family_value == PolymerFamily.PLGA.value and isinstance(fctx, PLGAContext):
        formulation.phi_PLGA_0 = fctx.phi_PLGA_0
        formulation.plga_grade = fctx.plga_grade

    params = SimulationParameters(
        model_mode=model_mode_enum,
        emulsification=emul,
        formulation=formulation,
        solver=SolverSettings(l2_n_grid=64),
    )
    _recipe = ensure_process_recipe_state(st.session_state)
    _recipe = sync_m1_ui_to_recipe(
        _recipe,
        polymer_family=str(family_value),
        is_stirred=bool(is_stirred),
        rpm=float(rpm),
        emulsification_time_min=float(t_emul),
        oil_temperature_C=float(fctx.T_oil_C),
        span80_percent=float(fctx.c_span80_vol_pct if is_stirred else fctx.c_span80_pct),
        cooling_rate_C_min=float(getattr(fctx, "cooling_rate_Cmin", 0.0)),
        dispersed_phase_fraction=float(phi_d),
        oil_volume_mL=float(v_oil_mL),
        polymer_volume_mL=float(v_poly_mL),
        vessel_choice=vessel_choice if is_stirred else "legacy rotor-stator vessel",
        stirrer_choice=stirrer_choice if is_stirred else "legacy rotor-stator",
        surfactant_key=str(fctx.surfactant_key),
        model_mode=str(model_mode_enum.value),
    )
    _resolved = resolve_lifecycle_inputs(_recipe, base_params=params)
    _recipe_blockers = [issue for issue in _resolved.validation.blockers if issue.module == "M1"]
    if _recipe_blockers:
        for _issue in _recipe_blockers:
            st.error(f"Recipe blocker: {_issue.message}")
        return
    params = _resolved.parameters
    save_process_recipe_state(st.session_state, _recipe)

    _smgr.invalidate_downstream(from_module=1)
    with st.spinner(f"Running L1→L2→L4 pipeline for {family.value}..."):
        t_start = time.time()
        db = PropertyDatabase()
        try:
            result = run_m1_from_recipe(
                _recipe,
                base_params=params,
                db=db,
                l2_mode="empirical",
                props_overrides=props_overrides,
                crosslinker_key="genipin",  # ignored for non-A+C families
                uv_intensity=0.0,
            )
        except Exception as ex:
            st.error(f"Simulation failed: {ex}")
            st.exception(ex)
            return
        elapsed = time.time() - t_start

    st.success(f"Pipeline complete in {elapsed:.1f}s")

    # ── Family-neutral results display ────────────────────────────────
    e, g, m = result.emulsification, result.gelation, result.mechanical
    c1, c2, c3, c4 = st.columns(4)
    d_mode = getattr(e, "d_mode", 0.0)
    c1.metric("d_mode", f"{d_mode*1e6:.1f} µm" if d_mode > 0 else f"d32 {e.d32*1e6:.2f} µm")
    c2.metric("Pore size", f"{g.pore_size_mean*1e9:.1f} nm")
    c3.metric("Porosity", f"{g.porosity:.2f}")
    c4.metric("G (modulus)", f"{m.G_DN/1000:.1f} kPa")

    e_mf = getattr(e, "model_manifest", None)
    if e_mf is not None:
        st.caption(f"L1 model: `{e_mf.model_name}` ({e_mf.evidence_tier.value})")
    g_mf = getattr(g, "model_manifest", None)
    if g_mf is not None:
        st.caption(f"L2 model: `{g_mf.model_name}` ({g_mf.evidence_tier.value})")
    m_mf = getattr(m, "model_manifest", None)
    if m_mf is not None:
        st.caption(f"L4 model: `{m_mf.model_name}` ({m_mf.evidence_tier.value})")

    # Save to session state so tabs M2/M3 can consume the result
    st.session_state["result"] = result
    st.session_state["elapsed"] = elapsed
    st.session_state["params"] = params


def render_tab_m1(
    tab_container,
    is_stirred: bool | None,
    model_mode_enum: ModelMode,
    _smgr,
    _const_input,
    _proto_sections: dict,
) -> None:
    """Render the M1 Fabrication tab inside the given Streamlit container.

    Args:
        tab_container: Streamlit tab container from st.tabs().
        is_stirred: Whether stirred vessel mode is selected. Pass ``None``
            (v9.0 default) to render the Hardware Mode radio locally at
            the top of the Emulsification section.
        model_mode_enum: Scientific mode enum.
        _smgr: SessionStateManager instance.
        _const_input: Callable for rendering per-constant selector with protocol link.
        _proto_sections: Dict of calibration protocol sections.
    """
    from dpsim.visualization.tabs.m1.hardware_section import render_hardware_mode_radio
    from dpsim.visualization.tabs.m1.family_selector import render_family_selector
    from dpsim.datatypes import PolymerFamily as _PF

    with tab_container:
        # v0.4.13: page header replaced by an eyebrow + title pair
        # matching the Direction-A "STAGE 02 · M1 / Microsphere
        # fabrication" reference. The card chrome supplies the
        # structural visual rhythm; the wrapping section_context
        # already prints the stage badge from app.py.
        from dpsim.visualization.design import chrome as _chrome
        st.html(_chrome.eyebrow("Stage 02 · M1", accent=True))
        st.html('<h1 style="margin:0 0 12px 0;">Microsphere fabrication</h1>')

        # ── Polymer family (v9.0) — drives L2 dispatch and downstream rendering ──
        with st.container(border=True):
            st.html(
                _chrome.card_header_strip(
                    eyebrow_text="Polymer family",
                    title="Drives downstream rendering",
                )
            )
            _family_ctx = render_family_selector()
        _family = _family_ctx.family

        # v9.0 M5-M7: dispatch non-A+C families to the family-specific runner.
        # Compare by .value (string), not enum identity — app.py reloads
        # dpsim.datatypes on every rerun, producing a new PolymerFamily
        # class. m1.family_selector is not in the reload list, so it returns
        # a stale-class enum member. Identity comparison would mis-classify
        # every family after the first rerun. See also
        # RunReport.compute_min_tier for the same hazard.
        if getattr(_family, "value", _family) != _PF.AGAROSE_CHITOSAN.value:
            _render_non_ac_family(
                tab_container=tab_container,
                family=_family,
                is_stirred_default=None,  # hardware_mode_radio already rendered in app.py sidebar v8 or by us in M2
                model_mode_enum=model_mode_enum,
                _smgr=_smgr,
            )
            return

        # ── M1 INPUT SECTION ─────────────────────────────────────────────────
        # Direction-A canonical layout: LEFT = Formulation / Crosslinking /
        # Predicted-outputs; RIGHT = Hardware (spans all rows).
        m1_col_left, m1_col_right = st.columns(2)

        # ── Right column: Hardware (big container, spans all rows) ──────────
        with m1_col_right:
            # v0.4.14: hardware/emulsification fully wrapped in a section
            # card to match the Direction-A reference. All hardware
            # widgets (vessel mode radio, vessel/stirrer pickers, RPM
            # slider, impeller cross-section, advanced PBE) live inside
            # this container.
            with st.container(border=True):
                # v0.4.17 (P2): deferred header. The tip-speed chip on the
                # right of the strip needs the live RPM + stirrer geometry,
                # which the widgets below own. Reserve the header slot
                # with st.empty() and fill it after the widgets render —
                # this is the standard Streamlit pattern for "header
                # depends on body state".
                _hw_header_slot = st.empty()

                # v9.0: Hardware Mode relocated from Global Settings sidebar
                # into the M1 Emulsification section (see scientific-advisor
                # audit §C). Back-compat: if caller still passes a bool,
                # honour it; otherwise render the radio here.
                if is_stirred is None:
                    is_stirred = render_hardware_mode_radio()
                    # v0.4.17 (P3): visible roadmap strip beneath the
                    # binary radio. The L1 PBE solver does NOT yet
                    # support Membrane / Microfluidic; surfacing them
                    # as planned (not selectable) keeps the user in
                    # sync with the canonical Direction-A reference
                    # without making a science-claim violation.
                    from dpsim.visualization.tabs.m1.vessel_mode import (
                        render_planned_modes_strip,
                    )
                    render_planned_modes_strip()

                if is_stirred:
                    # v0.4.3: vessel + stirrer migrated to labeled_widget.
                    from dpsim.visualization.help import labeled_widget
                    vessel_choice = labeled_widget(
                        "Vessel",
                        help=(
                            "Vessel geometry. Glass beaker uses flat-plate "
                            "heating; jacketed vessel uses circulating hot "
                            "water with steadier setpoint control."
                        ),
                        widget=lambda: st.selectbox(
                            "Vessel",
                            ["Glass Beaker (100 mm)", "Jacketed Vessel (92 mm)"],
                            key="m1_vessel", label_visibility="collapsed",
                        ),
                    )
                    stirrer_choice = labeled_widget(
                        "Stirrer",
                        help=(
                            "Pitched-blade (Stirrer A): mixed axial+radial flow, "
                            "moderate shear. Rotor-stator (Stirrer B): high-shear "
                            "annular zone — used for fine emulsification."
                        ),
                        widget=lambda: st.selectbox(
                            "Stirrer",
                            ["Stirrer A - Pitched Blade (59 mm)", "Stirrer B - Rotor-Stator (32 mm)"],
                            key="m1_stirrer", label_visibility="collapsed",
                        ),
                    )
                    is_stirrer_A = "Pitched" in stirrer_choice

                    # v0.4.2: stirrer-speed slider migrated to labeled_widget
                    # so the inline help describes the relationship between
                    # RPM, tip speed, and shear regime (drives the kernel
                    # selection in the L1 PBE solver).
                    from dpsim.visualization.help import get_help, labeled_widget
                    if is_stirrer_A:
                        rpm = labeled_widget(
                            "Stirrer speed",
                            help=get_help("m1.hardware.stir_rpm"),
                            unit="rpm",
                            widget=lambda: st.slider(
                                "Stirrer Speed (RPM)", 800, 2500, 1300, step=50,
                                key="m1_rpm", label_visibility="collapsed",
                            ),
                        )
                    else:
                        rpm = labeled_widget(
                            "Stirrer speed",
                            help=get_help("m1.hardware.stir_rpm"),
                            unit="rpm",
                            widget=lambda: st.slider(
                                "Stirrer Speed (RPM)", 800, 9000, 1800, step=100,
                                key="m1_rpm_rs", label_visibility="collapsed",
                            ),
                        )

                    # v0.4.17 (P2): Rushton cross-section paired with a
                    # vertical derived-metrics rail (v_tip / Re / We) per
                    # the canonical Direction-A reference. Re/We are
                    # display-only; the L1 PBE solver does its own
                    # rigorous calculation. Properties used here are
                    # representative paraffin-oil at hot emulsification
                    # (see hardware_metrics module for values).
                    from dpsim.visualization.components import (
                        render_impeller_xsec_v2_2,
                        render_impeller_xsec_v3,
                    )
                    from dpsim.visualization.design import chrome
                    from dpsim.visualization.tabs.m1.hardware_metrics import (
                        compute_hardware_metrics,
                        render_metrics_rail,
                    )
                    _impeller_d_m = 0.059 if is_stirrer_A else 0.0257
                    _hw_ctx = compute_hardware_metrics(
                        rpm=float(rpm),
                        impeller_diameter_m=_impeller_d_m,
                    )
                    if is_stirrer_A:
                        st.html(chrome.eyebrow(
                            "Stirrer A · 19-tab disk in 100 mL beaker · live"
                        ))
                    else:
                        st.html(chrome.eyebrow(
                            "Stirrer B · rotor-stator in 100 mL beaker · live"
                        ))
                    _xsec_col, _rail_col = st.columns([1, 0.42])
                    with _xsec_col:
                        if is_stirrer_A:
                            # v0.6.3 (this commit): replaces the v0.6.0 v2
                            # animation. Corrected beaker rim (20° outward
                            # flare, 5 mm height), corrected Stirrer A
                            # cross-section (1 mm disk + 2 perimeter tabs
                            # only — left UP, right DOWN; was a comb-like
                            # bar with tabs across the full diameter),
                            # added zone-shaded backgrounds matching v0.6.2
                            # zones.json schema, and three collision types
                            # (★ break / ✦ wall / ⊕ coalesce) per
                            # first-principles fluid mechanics. See
                            # impeller_xsec_v2_2.py docstring for the
                            # full revision notes vs v2.
                            render_impeller_xsec_v2_2(rpm=float(rpm))
                        else:
                            # v0.6.3: replaces the legacy Rushton-style
                            # animation (which drew the wrong instrument
                            # entirely — a 6-blade Rushton in a baffled
                            # BSTR rather than the rotor-stator with 36
                            # perforations Stirrer B actually is). The new
                            # v3 component renders the cross rotor inside
                            # the perforated stator, the bench-loop
                            # circulation, the 36 slot-exit jets, and the
                            # collision types with break-up dominantly at
                            # the slot exits per Padron 2005 / Hall 2011.
                            render_impeller_xsec_v3(rpm=float(rpm))
                    with _rail_col:
                        render_metrics_rail(_hw_ctx)
                    if is_stirrer_A:
                        st.caption(
                            "Disk-style impeller (Ø 59 mm × 1 mm sheet) with "
                            "19 perimeter tabs alternating UP/DOWN, each at "
                            "10° tangential pitch. The 10 UP / 9 DOWN tab "
                            "imbalance gives a small net upward axial bias; "
                            "the dominant flow pattern is **radial discharge** "
                            "at the impeller plane with figure-8 recirculation "
                            "above and below (Tatterson 1991). Toggle (top-"
                            "right) cycles through 4 views; transparent "
                            "modes show the per-zone ε partitioning matching "
                            "v0.6.2 ``zones.json`` schema and three collision "
                            "types: ★ break · ✦ wall · ⊕ coalesce."
                        )
                    else:
                        st.caption(
                            "Cross rotor (Ø 25.7 mm × 16 mm) inside a "
                            "perforated stator housing (Ø 32.03 mm, 36 × Ø 3 mm "
                            "perforations in a 3 × 12 grid). Rotor pumps fluid "
                            "axially through the open stator bottom; "
                            "centrifugal acceleration ejects it radially as 36 "
                            "slot-exit jets where 80–95 % of breakage occurs "
                            "(Padron 2005, Hall 2011). The transparent view "
                            "shows the bench-loop circulation: rotor inlet → "
                            "slot exits → bulk → return. ε_brk in slot-exit "
                            "shells reaches ~1200 W/kg, ~5× the impeller "
                            "swept-volume ε_brk."
                        )

                    t_emul = labeled_widget(
                        "Emulsification time",
                        help=(
                            "Hold time at full stirring. Drives the PBE "
                            "convergence — too short and bead size hasn't "
                            "stabilised; too long is wasted process time."
                        ),
                        unit="min",
                        widget=lambda: st.number_input(
                            "Emulsification Time (min)", 1, 60, 10,
                            key="m1_t_emul", label_visibility="collapsed",
                        ),
                    )

                    st.caption("Working liquid volumes")
                    v_oil_mL = labeled_widget(
                        "Oil + surfactant",
                        help="Continuous-phase volume (oil + Span-80). Default 300 mL.",
                        unit="mL",
                        widget=lambda: st.slider(
                            "Oil + Span-80 (mL)", 100, 500, 300, step=10,
                            key="m1_v_oil", label_visibility="collapsed",
                        ),
                    )
                    v_poly_mL = labeled_widget(
                        "Polysaccharide phase",
                        help="Dispersed-phase volume (aqueous polysaccharide). Default 200 mL.",
                        unit="mL",
                        widget=lambda: st.slider(
                            "Polysaccharide solution (mL)", 50, 300, 200, step=10,
                            key="m1_v_poly", label_visibility="collapsed",
                        ),
                    )
                    total_mL = v_oil_mL + v_poly_mL
                    phi_d = v_poly_mL / total_mL
                    from dpsim.visualization.tabs.m1.hardware_metrics import (
                        render_volumes_readout,
                    )
                    render_volumes_readout(v_oil_mL=v_oil_mL, v_poly_mL=v_poly_mL)

                    if "Beaker" in vessel_choice:
                        st.caption("Heating: flat-plate (150C -> 80C oil)")
                    else:
                        st.caption("Heating: jacket (85C circulating water)")

                    # v0.4.17 (P2): now that all live values are bound,
                    # fill in the deferred header with the tip-speed chip.
                    from dpsim.visualization.tabs.m1.hardware_metrics import (
                        render_tip_speed_chip,
                    )
                    _hw_header_slot.html(
                        _chrome.card_header_strip(
                            eyebrow_text="Hardware · Emulsification (L1)",
                            title="Stirred vessel · v9.0 in-M1",
                            right_html=render_tip_speed_chip(_hw_ctx),
                        )
                    )
                else:
                    # v0.4.5: AC legacy rotor-stator branch + advanced PBE
                    # settings migrated to labeled_widget.
                    from dpsim.visualization.help import labeled_widget as _lw_ac_leg
                    rpm = _lw_ac_leg(
                        "Rotor speed",
                        help="Rotor-stator legacy path. High-shear annular gap.",
                        unit="rpm",
                        widget=lambda: st.slider(
                            "Rotor Speed (RPM)", 3000, 25000, 10000, step=500,
                            key="m1_rpm_leg", label_visibility="collapsed",
                        ),
                    )
                    t_emul = _lw_ac_leg(
                        "Emulsification time",
                        unit="min",
                        widget=lambda: st.number_input(
                            "Emulsification Time (min)", 1, 60, 10,
                            key="m1_t_emul_leg", label_visibility="collapsed",
                        ),
                    )
                    phi_d = _lw_ac_leg(
                        "Dispersed-phase fraction (φ_d)",
                        help="Volume fraction of the dispersed phase.",
                        widget=lambda: st.slider(
                            "Dispersed Phase Fraction (phi_d)", 0.01, 0.30, 0.05, step=0.01,
                            key="m1_phi_d", label_visibility="collapsed",
                        ),
                    )
                    v_oil_mL = 300
                    v_poly_mL = 200
                    total_mL = 500

                    # v0.4.17 (P2): fill the deferred header for the
                    # legacy rotor-stator branch. No tip-speed chip here
                    # — the legacy path does not expose a deterministic
                    # impeller diameter (gap-driven shear instead). The
                    # header still labels the card distinctly.
                    _hw_header_slot.html(
                        _chrome.card_header_strip(
                            eyebrow_text="Hardware · Emulsification (L1)",
                            title="Rotor-stator (legacy)",
                        )
                    )

                if model_mode_enum != ModelMode.EMPIRICAL_ENGINEERING:
                    with st.expander("Advanced PBE Settings",
                                      expanded=(model_mode_enum == ModelMode.MECHANISTIC_RESEARCH)):
                        from dpsim.visualization.help import labeled_widget as _lw_pbe
                        l1_t_max = _lw_pbe(
                            "Max emulsification time",
                            help="Absolute ceiling for adaptive time extensions in the L1 PBE solver.",
                            unit="s",
                            widget=lambda: st.slider(
                                "Max emulsification time (s)", 60, 1800, 600, step=60,
                                key="m1_t_max", label_visibility="collapsed",
                            ),
                        )
                        l1_conv_tol = _lw_pbe(
                            "Convergence tolerance",
                            help="Relative d32 variation threshold for steady state. Below this, the solver declares the PBE converged.",
                            widget=lambda: st.slider(
                                "Convergence tolerance", 0.005, 0.10, 0.01, step=0.005,
                                format="%.3f", key="m1_conv_tol",
                                label_visibility="collapsed",
                            ),
                        )
                        l1_max_ext = _lw_pbe(
                            "Max extensions",
                            help="Number of half-interval extensions allowed if the PBE has not converged within the time bound.",
                            widget=lambda: st.number_input(
                                "Max extensions", 0, 5, 2,
                                key="m1_max_ext", label_visibility="collapsed",
                            ),
                        )
                else:
                    l1_t_max = 600
                    l1_conv_tol = 0.01
                    l1_max_ext = 2

        # ── Left column: Formulation → Crosslinking → Predicted outputs ─────
        # Import formulation renderer here (was previously imported inside the
        # Hardware container at end of the left column block).
        from dpsim.visualization.tabs.m1.formulation_agarose_chitosan import (
            render_formulation_section as _render_ac_formulation,
        )
        with m1_col_left:
            with st.container(border=True):
                st.html(
                    _chrome.card_header_strip(
                        eyebrow_text="Formulation",
                        title="Aqueous polymer phase",
                    )
                )
                _ac_ctx = _render_ac_formulation(is_stirred=is_stirred)
            c_agarose_pct = _ac_ctx.c_agarose_pct
            c_chitosan_pct = _ac_ctx.c_chitosan_pct
            _surf_sel_key = _ac_ctx.surfactant_key
            c_span80_pct = _ac_ctx.c_span80_pct
            c_span80_vol_pct = _ac_ctx.c_span80_vol_pct
            T_oil_C = _ac_ctx.T_oil_C
            cooling_rate_Cmin = _ac_ctx.cooling_rate_Cmin
            l2_mode = _ac_ctx.l2_mode
            grid_size = _ac_ctx.grid_size
            surf = _ac_ctx.surfactant

            # v9.0 M4: crosslinking section moved into module.
            from dpsim.visualization.tabs.m1.crosslinking_section import (
                render_crosslinking_section as _render_crosslinking,
            )
            _DDA_out: list = []
            with st.container(border=True):
                st.html(
                    _chrome.card_header_strip(
                        eyebrow_text="Crosslinking · L3",
                        title="Secondary covalent network",
                    )
                )
                _xl_ctx = _render_crosslinking(
                    c_chitosan_pct=c_chitosan_pct, DDA_out=_DDA_out,
                )
            _xl_sel_key = _xl_ctx.crosslinker_key
            c_genipin_mM = _xl_ctx.c_genipin_mM
            T_xlink_C = _xl_ctx.T_xlink_C
            t_xlink_h = _xl_ctx.t_xlink_h
            uv_intensity = _xl_ctx.uv_intensity
            xl = _xl_ctx.crosslinker
            _DDA = _DDA_out[0] if _DDA_out else 0.85

            # v0.4.15: Predicted outputs card — DSD histogram + 4 D-
            # percentile cells. Mirrors the Direction-A canonical
            # "Predicted M1 outputs / Bead size distribution" card.
            # Reads the emulsification result if a run has executed in
            # this session; otherwise renders the histogram with
            # synthetic placeholder bins so the card is never blank.
            _pred_eval = st.session_state.get("result")
            _pred_e = (
                getattr(_pred_eval, "emulsification", None)
                if _pred_eval is not None else None
            )
            _pred_evidence = (
                _chrome.evidence_badge("calibrated_local", compact=True)
                if _pred_e is not None else
                _chrome.evidence_badge("unsupported", compact=True)
            )
            with st.container(border=True):
                st.html(
                    _chrome.card_header_strip(
                        eyebrow_text="Predicted M1 outputs",
                        title="Bead size distribution",
                        right_html=_pred_evidence,
                    )
                )
                # Histogram preview — synthetic gaussian-ish bins; the
                # actual DSD plotly chart still renders in the L1 sub-
                # tab below when results are available.
                import math as _m
                _bins = [
                    _m.exp(-((i - 11) / 6) ** 2 * 0.7)
                    * (0.85 + 0.3 * _m.sin(i))
                    for i in range(24)
                ]
                st.html(
                    '<div style="display:flex;justify-content:center;'
                    'padding:4px 0 8px;">'
                    + _chrome.mini_histogram(_bins, width=300, height=64)
                    + '</div>'
                )
                # 4-cell D-percentile grid.
                if _pred_e is not None:
                    _d10 = float(getattr(_pred_e, "d10", 0.0)) * 1e6
                    _d32 = float(getattr(_pred_e, "d32", 0.0)) * 1e6
                    _d50 = float(getattr(_pred_e, "d50", 0.0)) * 1e6
                    _d90 = float(getattr(_pred_e, "d90", 0.0)) * 1e6
                    _cells = [
                        ("d10", f"{_d10:.1f}", "µm"),
                        ("d32", f"{_d32:.1f}", "µm"),
                        ("d50", f"{_d50:.1f}", "µm"),
                        ("d90", f"{_d90:.1f}", "µm"),
                    ]
                else:
                    _cells = [
                        ("d10", "—", ""), ("d32", "—", ""),
                        ("d50", "—", ""), ("d90", "—", ""),
                    ]
                _grid = "".join(
                    '<div style="padding:8px 10px;'
                    'background:var(--dps-surface-2);'
                    'border:1px solid var(--dps-border);'
                    'border-radius:4px;">'
                    + _chrome.eyebrow(label)
                    + '<div style="margin-top:2px;">'
                    + _chrome.metric_value(value=value, unit=unit, size=16)
                    + '</div></div>'
                    for label, value, unit in _cells
                )
                st.html(
                    '<div style="display:grid;'
                    'grid-template-columns:repeat(4,1fr);gap:8px;">'
                    + _grid
                    + '</div>'
                )

            # v0.4.17 (P3): Targets card promoted out of the
            # collapsed-by-default expander into the LEFT column. The
            # targets drive the Optimisation Assessment f1/f2/f3
            # objectives — they are scientific specification, not
            # advanced settings. Material constants stay collapsed.
            from dpsim.visualization.tabs.m1.targets_section import (
                render_targets_section as _render_targets,
            )
            with st.container(border=True):
                st.html(
                    _chrome.card_header_strip(
                        eyebrow_text="Targets",
                        title="Optimisation objectives",
                    )
                )
                _tgt_ctx = _render_targets(family=_family, is_stirred=is_stirred)
            target_d32 = _tgt_ctx.target_d32
            target_d_mode = _tgt_ctx.target_d_mode
            target_pore = _tgt_ctx.target_pore
            target_G = _tgt_ctx.target_G

            # v0.4.17 (P5): Calibration link banner. Surfaces the
            # 5-study wet-lab protocol pre-Run so the user knows a
            # calibrated_local evidence tier is achievable. Clicking
            # navigates to Stage 07 via session-state.
            st.html(
                '<div style="display:flex;align-items:center;gap:10px;'
                "padding:10px 14px;margin-top:4px;"
                "background:var(--dps-surface);"
                "border:1px solid var(--dps-border);"
                "border-left:3px solid var(--dps-accent);"
                'border-radius:4px;">'
                '<span class="dps-mono" style="font-size:10px;'
                "color:var(--dps-accent);font-weight:700;"
                'letter-spacing:0.06em;">CALIBRATION</span>'
                '<span style="flex:1;font-size:12px;'
                'color:var(--dps-text-muted);line-height:1.45;">'
                "5-study wet-lab protocol available · run it to lift "
                "M1 evidence from "
                '<span style="color:var(--dps-amber-500);">SEMI</span> to '
                '<span style="color:var(--dps-green-500);">CALIBRATED</span>'
                "</span>"
                "</div>"
            )
            if st.button(
                "Open Stage 07 · Calibration",
                key="m1_open_calibration_stage",
                use_container_width=True,
            ):
                st.session_state["_dpsim_shell_active_stage"] = "calibrate"
                st.rerun()

        # ── Advanced expander: Material-constants overrides ──────────────────
        # These calibration overrides remain collapsed because they're
        # truly advanced (per-constant Literature/Custom dispatch driven
        # by docs/04_calibration_protocol.md). Targets were moved out
        # in v0.4.17 (P3) — see m1_col_left block above.
        with st.expander("Material-constants overrides — advanced", expanded=False):
            # v9.0 M4: material constants moved into module (family-aware).
            from dpsim.visualization.tabs.m1.material_constants import (
                render_material_constants as _render_material_constants,
            )
            with st.container(border=True):
                st.html(
                    _chrome.card_header_strip(
                        eyebrow_text="Material constants",
                        title="Calibration overrides",
                    )
                )
                _mat_overrides = _render_material_constants(
                    family=_family,
                    surfactant=surf,
                    crosslinker=xl,
                    const_input=_const_input,
                    T_oil_C=T_oil_C,
                    c_span80_pct=c_span80_pct,
                )

        # ── M1 Validation ────────────────────────────────────────────────────
        _m1_val = _validate_m1(
            rpm=float(rpm),
            phi_d=phi_d,
            c_agarose=c_agarose_pct,
            c_chitosan=c_chitosan_pct,
            dda=_DDA,
            crosslinker_key=_xl_sel_key,
            crosslinker_conc=float(c_genipin_mM),
            T_crosslink=float(T_xlink_C),
            T_oil=float(T_oil_C),
        )
        # v0.4.17 (P3): wet-lab caveats card — pre-Run predictive
        # blockers / warnings, surfaced BEFORE the Run button so the
        # issue is visible at the point of decision (matches the
        # canonical Direction-A reference's Wet-lab caveats card).
        from dpsim.visualization.tabs.m1.m1_caveats import (
            render_m1_caveats_card,
        )
        render_m1_caveats_card(
            _m1_val,
            family=_family,
            crosslinker_key=str(_xl_sel_key),
            rpm=float(rpm),
            T_oil_C=float(T_oil_C),
            phi_d=float(phi_d),
        )

        # ── Build Parameters ─────────────────────────────────────────────────
        if is_stirred:
            if "Beaker" in vessel_choice:
                _vessel = VesselGeometry.glass_beaker(working_volume=total_mL * 1e-6)
            else:
                _vessel = VesselGeometry.jacketed_vessel(working_volume=total_mL * 1e-6)

            if is_stirrer_A:
                _stirrer = StirrerGeometry.pitched_blade_A()
            else:
                _stirrer = StirrerGeometry.rotor_stator_B()

            if "Beaker" in vessel_choice:
                _heating = HeatingConfig.flat_plate()
            else:
                _heating = HeatingConfig.hot_water_jacket()
            _heating.T_initial = T_oil_C + 273.15
            _kernels = KernelConfig.for_stirrer_type(_stirrer.stirrer_type)

            params = SimulationParameters(
                model_mode=model_mode_enum,
                emulsification=EmulsificationParameters(
                    mode="stirred_vessel",
                    rpm=float(rpm),
                    t_emulsification=float(t_emul * 60),
                    vessel=_vessel,
                    stirrer=_stirrer,
                    heating=_heating,
                    kernels=_kernels,
                ),
                formulation=FormulationParameters(
                    c_agarose=c_agarose_pct * 10.0,
                    c_chitosan=c_chitosan_pct * 10.0,
                    c_span80=c_span80_pct * 10.0,
                    c_genipin=float(c_genipin_mM),
                    T_oil=T_oil_C + 273.15,
                    cooling_rate=cooling_rate_Cmin / 60.0,
                    T_crosslink=T_xlink_C + 273.15,
                    t_crosslink=float(t_xlink_h * 3600),
                    phi_d=phi_d,
                    c_span80_vol_pct=c_span80_vol_pct,
                    v_oil_span80_mL=float(v_oil_mL),
                    v_polysaccharide_mL=float(v_poly_mL),
                ),
                solver=SolverSettings(
                    l1_n_bins=40, l1_d_min=1e-6, l1_d_max=2000e-6,
                    l2_n_grid=grid_size,
                    l1_t_max=float(l1_t_max),
                    l1_conv_tol=float(l1_conv_tol),
                    l1_max_extensions=int(l1_max_ext),
                ),
            )
        else:
            params = SimulationParameters(
                model_mode=model_mode_enum,
                emulsification=EmulsificationParameters(
                    mode="rotor_stator_legacy",
                    rpm=float(rpm),
                    t_emulsification=float(t_emul * 60),
                    mixer=MixerGeometry(),
                ),
                formulation=FormulationParameters(
                    c_agarose=c_agarose_pct * 10.0,
                    c_chitosan=c_chitosan_pct * 10.0,
                    c_span80=c_span80_pct * 10.0,
                    c_genipin=float(c_genipin_mM),
                    T_oil=T_oil_C + 273.15,
                    cooling_rate=cooling_rate_Cmin / 60.0,
                    T_crosslink=T_xlink_C + 273.15,
                    t_crosslink=float(t_xlink_h * 3600),
                    phi_d=phi_d,
                ),
                solver=SolverSettings(
                    l2_n_grid=grid_size,
                    l1_t_max=float(l1_t_max),
                    l1_conv_tol=float(l1_conv_tol),
                    l1_max_extensions=int(l1_max_ext),
                ),
            )

        # Material constants overrides (v9.0 M4: sourced from material_constants module)
        _custom_props_overrides = dict(_mat_overrides)
        _custom_props_overrides['k_xlink_0'] = xl.k_xlink_0
        _custom_props_overrides['E_a_xlink'] = xl.E_a_xlink
        _custom_props_overrides['f_bridge'] = xl.f_bridge

        _recipe = ensure_process_recipe_state(st.session_state)
        _recipe = sync_m1_ui_to_recipe(
            _recipe,
            polymer_family=str(getattr(_family, "value", _family)),
            is_stirred=bool(is_stirred),
            rpm=float(rpm),
            emulsification_time_min=float(t_emul),
            oil_temperature_C=float(T_oil_C),
            span80_percent=float(c_span80_vol_pct if is_stirred else c_span80_pct),
            cooling_rate_C_min=float(cooling_rate_Cmin),
            dispersed_phase_fraction=float(phi_d),
            oil_volume_mL=float(v_oil_mL),
            polymer_volume_mL=float(v_poly_mL),
            target_diameter_um=float(target_d_mode if is_stirred else target_d32),
            target_pore_nm=float(target_pore),
            target_modulus_kPa=float(target_G),
            vessel_choice=vessel_choice if is_stirred else "legacy rotor-stator vessel",
            stirrer_choice=stirrer_choice if is_stirred else "legacy rotor-stator",
            surfactant_key=str(_surf_sel_key),
            model_mode=str(model_mode_enum.value),
        )
        _resolved = resolve_lifecycle_inputs(_recipe, base_params=params)
        _recipe_blockers = [issue for issue in _resolved.validation.blockers if issue.module == "M1"]
        if _recipe_blockers:
            for _issue in _recipe_blockers:
                st.error(f"Recipe blocker: {_issue.message}")
        params = _resolved.parameters
        save_process_recipe_state(st.session_state, _recipe)

        # ── Run M1 Button ────────────────────────────────────────────────────
        st.divider()
        m1_run_btn = st.button("\u25b6 Run M1: Fabrication Pipeline", type="primary",
                                use_container_width=True,
                                disabled=bool(_m1_val.blockers or _recipe_blockers))

        if m1_run_btn:
            _smgr.invalidate_downstream(from_module=1)
            with st.spinner("Running L1\u2192L2\u2192L3\u2192L4 pipeline..."):
                t_start = time.time()
                db = PropertyDatabase()
                progress = st.progress(0, text="Level 1: Emulsification (PBE solver)...")

                try:
                    result = run_m1_from_recipe(
                        _recipe,
                        base_params=params,
                        db=db,
                        l2_mode=l2_mode,
                        props_overrides=_custom_props_overrides,
                        crosslinker_key=_xl_sel_key,
                        uv_intensity=uv_intensity,
                    )
                except Exception as ex:
                    st.error(f"Simulation failed: {ex}")
                    st.exception(ex)
                    st.stop()
                elapsed = time.time() - t_start
                progress.progress(100, text=f"M1 complete in {elapsed:.1f}s")

            st.session_state["result"] = result
            st.session_state["elapsed"] = elapsed
            st.session_state["params"] = params
            st.session_state["targets"] = (target_d32, target_pore, target_G)
            st.session_state["m1_overrides"] = _custom_props_overrides
            st.session_state["m1_xl_key"] = _xl_sel_key
            st.session_state["m1_l2_mode"] = l2_mode

            db_trust = PropertyDatabase()
            props_trust = db_trust.update_for_conditions(
                params.formulation.T_oil, params.formulation.c_agarose,
                params.formulation.c_chitosan, params.formulation.c_span80,
            )
            for _k, _v in _custom_props_overrides.items():
                if hasattr(props_trust, _k):
                    setattr(props_trust, _k, _v)
            st.session_state["trust"] = assess_trust(result, params, props_trust,
                                                        crosslinker_key=_xl_sel_key,
                                                        l2_mode=l2_mode)
            st.rerun()

        # ── M1 Results Display ───────────────────────────────────────────────
        if "result" in st.session_state:
            result = st.session_state["result"]
            elapsed = st.session_state["elapsed"]
            target_d32, target_pore, target_G = st.session_state["targets"]

            e = result.emulsification
            g = result.gelation
            x = result.crosslinking
            m = result.mechanical

            st.header("M1 Results")

            # KPI cards
            col1, col2, col3, col4 = st.columns(4)
            _d_mode = getattr(e, 'd_mode', 0.0)

            if is_stirred:
                d_primary_dev = abs(_d_mode * 1e6 - target_d_mode) / target_d_mode * 100
            else:
                d_primary_dev = abs(e.d32 * 1e6 - target_d32) / target_d32 * 100
            pore_dev = abs(g.pore_size_mean * 1e9 - target_pore) / target_pore * 100
            G_dev = abs(m.G_DN / 1000 - target_G) / target_G * 100

            if is_stirred:
                col1.metric("d_mode", f"{_d_mode*1e6:.1f} um",
                            delta=f"{d_primary_dev:.0f}% from target", delta_color="inverse")
            else:
                col1.metric("d32", f"{e.d32*1e6:.2f} um",
                            delta=f"{d_primary_dev:.0f}% from target", delta_color="inverse")
            col2.metric("Pore Size", f"{g.pore_size_mean*1e9:.1f} nm",
                        delta=f"{pore_dev:.0f}% from target", delta_color="inverse")
            _hs_lo = getattr(m, 'G_DN_lower', 0.0)
            _hs_hi = getattr(m, 'G_DN_upper', 0.0)
            if _hs_lo > 0 and _hs_hi > 0:
                col3.metric("G_DN", f"{m.G_DN/1000:.1f} kPa",
                            delta=f"Ref: [{_hs_lo/1000:.1f}, {_hs_hi/1000:.1f}] kPa (single-phase)",
                            delta_color="off")
            else:
                col3.metric("G_DN", f"{m.G_DN/1000:.1f} kPa",
                            delta=f"{G_dev:.0f}% from target", delta_color="inverse")
            col4.metric("Pipeline Time", f"{elapsed:.1f}s")

            col5, col6, col7, col8 = st.columns(4)
            col5.metric("Span", f"{e.span:.2f}")
            col6.metric("Porosity", f"{g.porosity:.1%}")
            col7.metric("Crosslink %", f"{x.p_final:.1%}")
            col8.metric("E*", f"{m.E_star/1000:.1f} kPa")

            st.divider()

            # ── L1-L4 Sub-tabs ───────────────────────────────────────────────
            _sub_labels = ["Dashboard", "L1: Emulsification", "L2: Gelation",
                           "L3: Crosslinking", "L4: Mechanical"]
            sub1, sub2, sub3, sub4, sub5 = st.tabs(_sub_labels)

            with sub1:
                st.plotly_chart(plot_results_dashboard(result), use_container_width=True)

            with sub2:
                st.subheader("Level 1: Emulsification -- Droplet Size Distribution")
                st.plotly_chart(plot_droplet_size_distribution(e), use_container_width=True)
                c1, c2, c3 = st.columns(3)
                c1.write(f"**d10** = {e.d10*1e6:.2f} um")
                c1.write(f"**d32** = {e.d32*1e6:.2f} um")
                if _d_mode > 0:
                    c1.write(f"**d_mode** = {_d_mode*1e6:.1f} um")
                c2.write(f"**d50** = {e.d50*1e6:.2f} um")
                c2.write(f"**d90** = {e.d90*1e6:.2f} um")
                c3.write(f"**d43** = {e.d43*1e6:.2f} um")
                c3.write(f"**Span** = {e.span:.3f}")
                _conv_icon = "\u2705 Yes" if e.converged else "\u26a0\ufe0f No (still evolving)"
                st.write(f"**Converged:** {_conv_icon}")
                _t_conv = getattr(e, 't_converged', None)
                _n_ext = getattr(e, 'n_extensions', 0)
                if _t_conv is not None:
                    st.write(f"Converged at t = {_t_conv:.1f} s")
                if _n_ext > 0:
                    st.write(f"Adaptive extensions: {_n_ext}")
                _l1_badge = _evidence_badge(e)
                if _l1_badge:
                    st.caption(_l1_badge)
                if is_stirred:
                    st.caption(
                        f"Mode: stirred-vessel | "
                        f"Vessel: {vessel_choice.split('(')[0].strip()} | "
                        f"Stirrer: {stirrer_choice.split('-')[0].strip()} | "
                        f"phi_d = {phi_d:.2f}"
                    )

            with sub3:
                st.subheader("Level 2: Gelation \u2014 Pore Structure")
                st.plotly_chart(plot_phase_field(g), use_container_width=True)
                c1, c2, c3 = st.columns(3)
                c1.write(f"**Pore size** = {g.pore_size_mean*1e9:.1f} nm")
                c2.write(f"**Porosity** = {g.porosity:.3f}")
                c3.write(f"**Gelation \u03b1** = {g.alpha_final:.4f}")
                if g.phi_field.ndim == 2:
                    st.write(f"Grid: {g.phi_field.shape[0]}\u00d7{g.phi_field.shape[1]}, "
                             f"spacing = {g.grid_spacing*1e9:.1f} nm, "
                             f"\u03c6 range: [{g.phi_field.min():.4f}, {g.phi_field.max():.4f}]")
                _l2_badge = _evidence_badge(g)
                if _l2_badge:
                    st.caption(_l2_badge)

            with sub4:
                st.subheader("Level 3: Crosslinking Kinetics")
                st.plotly_chart(plot_crosslinking_kinetics(x), use_container_width=True)
                c1, c2, c3 = st.columns(3)
                c1.write(f"**Crosslink fraction** = {x.p_final:.4f}")
                c1.write(f"**G_crosslinked** = {x.G_chitosan_final:.0f} Pa")
                c2.write(f"**Mesh size \u03be** = {x.xi_final*1e9:.1f} nm")
                c2.write(f"**M_c** = {x.Mc_final:.0f} g/mol")
                c3.write(f"**\u03bd_e** = {x.nu_e_final:.2e} /m\u00b3")
                # v6.1: L3 diagnostics
                if getattr(x, 'regime', 'unknown') != 'unknown':
                    st.caption(f"Regime: {x.regime} | Thiele: {x.thiele_modulus:.2f} | Stoich. ceiling: {x.stoichiometric_ceiling:.2f}")
                _l3_badge = _evidence_badge(x)
                if _l3_badge:
                    st.caption(_l3_badge)
                # STMP homogeneity window (see Appendix J.1.7): Thiele ~1 at R=500 um
                if _xl_sel_key == "stmp" and (e.d50 / 2.0) > 500e-6:
                    st.warning(
                        f"STMP homogeneity window exceeded: bead radius "
                        f"d50/2 = {e.d50 / 2.0 * 1e6:.0f} µm > 500 µm. "
                        f"Expect a skin-core crosslink gradient. Either reduce bead "
                        f"size (raise rpm or surfactant) or shorten Phase B activation. "
                        f"See Appendix J.1.7 troubleshooting."
                    )

            with sub5:
                st.subheader("Level 4: Mechanical Properties")
                _model_label = getattr(m, 'model_used', 'phenomenological')
                st.caption(f"Model: {_model_label}")
                if _model_label == "flory_rehner_affine":
                    st.success("Flory-Rehner affine IPN model converged \u2014 mechanistic crosslink density used.")
                elif _model_label == "phenomenological":
                    if model_mode_enum == ModelMode.MECHANISTIC_RESEARCH:
                        st.info("Using phenomenological model. Switch to Mechanistic Research mode to enable Flory-Rehner affine IPN.")
                    else:
                        st.info("Phenomenological DN model (G1 + G2 + \u03b7\u221a(G1\u00b7G2)). Switch to Mechanistic Research for affine IPN.")

                left, right = st.columns(2)
                with left:
                    st.plotly_chart(plot_hertz_contact(m), use_container_width=True)
                with right:
                    st.plotly_chart(plot_kav_curve(m), use_container_width=True)
                st.plotly_chart(plot_modulus_comparison(m), use_container_width=True)
                # v6.1: network classification + evidence badge
                _ntype = getattr(m, 'network_type', 'unknown')
                if _ntype != 'unknown':
                    st.caption(f"Network type: {_ntype}")
                _l4_badge = _evidence_badge(m)
                if _l4_badge:
                    st.caption(_l4_badge)

                c1, c2, c3 = st.columns(3)
                c1.write(f"**G_agarose** = {m.G_agarose:.0f} Pa ({m.G_agarose/1000:.1f} kPa)")
                c2.write(f"**G_crosslinked** = {m.G_chitosan:.0f} Pa ({m.G_chitosan/1000:.1f} kPa)")
                c3.write(f"**G_DN** = {m.G_DN:.0f} Pa ({m.G_DN/1000:.1f} kPa)")
                if _hs_lo > 0 and _hs_hi > 0:
                    st.write(f"**Single-phase reference (HS composite bounds, not IPN bounds):** [{_hs_lo/1000:.1f}, {_hs_hi/1000:.1f}] kPa")
                st.caption(f"Model: {_model_label}")

                if model_mode_enum == ModelMode.MECHANISTIC_RESEARCH:
                    st.write("**Model Comparison:**")
                    from dpsim.level4_mechanical.solver import double_network_modulus as _dnm
                    _eta_comp = getattr(x.network_metadata, 'eta_coupling_recommended', -0.15) if x.network_metadata else -0.15
                    _G_pheno = _dnm(m.G_agarose, m.G_chitosan, _eta_comp)
                    st.write(
                        f"Phenomenological: {_G_pheno/1000:.1f} kPa | "
                        f"{'Affine IPN' if _model_label == 'flory_rehner_affine' else _model_label}: {m.G_DN/1000:.1f} kPa"
                    )

            # ── Optimization Assessment ──────────────────────────────────────
            st.divider()
            st.header("Optimization Assessment")

            if is_stirred:
                d_obj_val = _d_mode * 1e6
                d_obj_target = target_d_mode
                d_obj_label = "f_1 (d_mode deviation)"
                d_obj_help = f"|d_mode - {target_d_mode} um| / {target_d_mode} um"
            else:
                d_obj_val = e.d32 * 1e6
                d_obj_target = target_d32
                d_obj_label = "f_1 (d32 deviation)"
                d_obj_help = f"|d32 - {target_d32} um| / {target_d32} um"

            d_dev_obj = abs(d_obj_val - d_obj_target) / d_obj_target
            pore_dev_obj = abs(g.pore_size_mean * 1e9 - target_pore) / target_pore
            G_dev_obj = abs(np.log10(max(m.G_DN, 1)) - np.log10(target_G * 1000))
            obj = np.array([d_dev_obj, pore_dev_obj, G_dev_obj])

            st.write("**Objective Values** (lower = closer to target):")
            oc1, oc2, oc3 = st.columns(3)
            oc1.metric(d_obj_label, f"{obj[0]:.3f}", help=d_obj_help)
            oc2.metric("f_2 (pore deviation)", f"{obj[1]:.3f}",
                       help=f"|pore - {target_pore} nm| / {target_pore} nm")
            oc3.metric("f_3 (modulus deviation)", f"{obj[2]:.3f}",
                       help=f"|log10(G_DN) - log10({target_G*1000})|")

            overall = np.mean(obj)
            if overall < 0.3:
                st.success(f"**Excellent match** (avg. deviation = {overall:.3f}). Parameters are near-optimal.")
            elif overall < 1.0:
                st.warning(f"**Moderate match** (avg. deviation = {overall:.3f}). Consider optimization.")
            else:
                st.error(f"**Poor match** (avg. deviation = {overall:.3f}). Significant parameter adjustment needed.")

            # Structured suggestions with derivation-page hyperlinks (v9.2.0).
            # Each Suggestion carries its own SuggestionContext snapshot so the
            # /suggestion_detail page can reconstruct the full derivation.
            # The orchestrator does not expose the MaterialProperties it built;
            # we reconstruct a fresh defaults instance (same values the solver
            # used since the A+C path only overrides polymer_family).
            from dpsim.datatypes import MaterialProperties as _MP
            from dpsim.suggestions import generate_all
            from dpsim.suggestions.serialization import suggestion_to_url
            from dpsim.suggestions.types import SuggestionContext

            _mp = _MP()
            _sugg_ctx = SuggestionContext(
                family=str(getattr(_family, 'value', _family)),
                d32_actual=float(e.d32),
                d50_actual=float(e.d50),
                pore_actual=float(g.pore_size_mean),
                l2_mode=str(locals().get('l2_mode', 'empirical')),
                cooling_rate_effective=float(getattr(g, 'cooling_rate_effective', params.formulation.cooling_rate)),
                p_final=float(x.p_final),
                G_DN_actual=float(m.G_DN),
                target_d32=float(target_d32) * 1e-6,
                target_pore=float(target_pore) * 1e-9,
                target_G=float(target_G) * 1000.0,
                rpm=float(rpm),
                T_oil=float(params.formulation.T_oil),
                cooling_rate_input=float(params.formulation.cooling_rate),
                c_agarose=float(params.formulation.c_agarose),
                c_chitosan=float(params.formulation.c_chitosan),
                c_crosslinker_mM=float(c_genipin_mM),
                crosslinker_key=str(_xl_sel_key),
                rho_oil=float(getattr(_mp, 'rho_oil', 850.0)),
                mu_oil=float(getattr(_mp, 'mu_oil', 0.005)),
                rho_d=float(getattr(_mp, 'rho_d', 1000.0)),
                cp_d=float(getattr(_mp, 'cp_d', 4180.0)),
                k_oil=float(getattr(_mp, 'k_oil', 0.15)),
                h_coeff=float(getattr(_mp, 'h_coeff', 500.0)),
                T_bath=float(getattr(_mp, 'T_bath', 293.15)),
                T_gel=float(getattr(_mp, 'T_gel', 311.15)),
                DDA=float(getattr(_mp, 'DDA', 0.85)),
                M_GlcN=float(getattr(_mp, 'M_GlcN', 161.16)),
                f_bridge=float(getattr(_mp, 'f_bridge', 0.4)),
                impeller_D=float(getattr(params.emulsification, 'impeller_D', 0.05)),
                phi_d=float(params.formulation.phi_d),
                run_id=str(getattr(params, 'run_id', '')),
            )
            _suggestions = generate_all(_sugg_ctx)
            if not _suggestions:
                st.write("All objectives are within acceptable range. No adjustments needed.")
            else:
                for i, _s in enumerate(_suggestions, 1):
                    _url = suggestion_to_url(_s)
                    st.markdown(f"{i}. {_s.display_text} [derivation →]({_url})")

            # ── Trust Assessment ─────────────────────────────────────────────
            if "trust" in st.session_state:
                st.divider()
                st.header("Trust Assessment")
                trust = st.session_state["trust"]
                _mode_desc = {
                    "empirical_engineering": "Empirical Engineering \u2014 trust warnings relaxed for screening",
                    "hybrid_coupled": "Hybrid Coupled \u2014 phenomenological models with trust warnings",
                    "mechanistic_research": "Mechanistic Research \u2014 strictest gates, Flory-Rehner when available",
                }
                st.caption(f"Mode: {_mode_desc.get(model_mode_enum.value, model_mode_enum.value)}")
                if trust.level == "TRUSTWORTHY":
                    st.success(f"**{trust.level}** -- All checks passed.")
                elif trust.level == "CAUTION":
                    st.warning(f"**{trust.level}** -- Some conditions are outside ideal range.")
                else:
                    st.error(f"**{trust.level}** -- Results should not be used for decisions.")
                if trust.blockers:
                    st.subheader("Blockers")
                    for b in trust.blockers:
                        st.error(b)
                if trust.warnings:
                    st.subheader("Warnings")
                    for w in trust.warnings:
                        st.warning(w)

            # ── Calibration Protocol ─────────────────────────────────────────
            st.divider()
            st.header("Calibration & Validation")
            cal_path = Path(__file__).resolve().parents[4] / "docs" / "04_calibration_protocol.md"
            if cal_path.exists():
                with st.expander("View Calibration Wet-Lab Protocol"):
                    st.markdown(cal_path.read_text(encoding="utf-8"))
            st.info(
                "The simulation uses literature-estimated constants that should be calibrated "
                "against your specific materials. See **docs/04_calibration_protocol.md** for "
                "a 5-study, ~30-preparation wet-lab protocol covering: interfacial tension "
                "(K_L, \u0393\u221e), chitosan viscosity (\u03b7_intr), breakage dynamics (C3), "
                "pore structure (empirical coefficients), and IPN mechanics (\u03b7_coupling)."
            )

