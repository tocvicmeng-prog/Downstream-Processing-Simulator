"""Streamlit UI for the Downstream Processing Simulator.

Launch: streamlit run src/dpsim/visualization/app.py

v0.4.0 Direction-A shell: top app bar + 7-stage pipeline spine +
2-column main grid (stage body | sticky run rail). The legacy
``--dps-*`` CSS block (v0.3.x) has been replaced by
``design.tokens.inject_global_css()``, which sources DESIGN.md tokens
from a single ``tokens.css`` file. Existing render functions
(``render_tab_m1`` / ``m2`` / ``m3`` / ``render_lifecycle_*``) are
wrapped, not rewritten.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import streamlit as st

logger = logging.getLogger(__name__)

# Ensure the package is importable and force-reload to pick up code changes.
_root = Path(__file__).resolve().parents[3]
if str(_root / "src") not in sys.path:
    sys.path.insert(0, str(_root / "src"))

# Force reload of ALL core modules to avoid Streamlit's import cache.
# Order matters: reload dependencies before dependents.
import importlib
import dpsim.datatypes as _dt_mod; importlib.reload(_dt_mod)
import dpsim.level1_emulsification.thermal as _th_mod; importlib.reload(_th_mod)
import dpsim.level1_emulsification.energy as _en_mod; importlib.reload(_en_mod)
import dpsim.level1_emulsification.kernels as _kr_mod; importlib.reload(_kr_mod)
import dpsim.level1_emulsification.validation as _vl_mod; importlib.reload(_vl_mod)
import dpsim.level1_emulsification.solver as _sv_mod; importlib.reload(_sv_mod)
import dpsim.properties.database as _db_mod; importlib.reload(_db_mod)
import dpsim.pipeline.orchestrator as _orch_mod; importlib.reload(_orch_mod)
import dpsim.trust as _trust_mod; importlib.reload(_trust_mod)
import dpsim.level3_crosslinking.solver as _xl_mod; importlib.reload(_xl_mod)

from dpsim.core.process_recipe import LifecycleStage
from dpsim.datatypes import ModelMode
from dpsim.visualization.design import inject_global_css
from dpsim.visualization.diff.render import diff_entries
from dpsim.visualization.run_rail import render_run_rail
from dpsim.visualization.shell import (
    StageId,
    autowire_shell_state,
    derive_stage_status,
    get_direction,
    render_direction_switch,
    render_shell,
    render_triptych,
)
from dpsim.visualization.shell.shell import default_evidence_stages
from dpsim.visualization.ui_state import SessionStateManager
from dpsim.visualization.ui_recipe import ensure_process_recipe_state
from dpsim.visualization.shell.stage_panels import (
    render_calibration_stage,
    render_run_lifecycle_stage,
    render_validation_stage,
)
from dpsim.visualization.ui_workflow import (
    render_stage_context_panel,
    render_target_product_profile_editor,
)
from dpsim.visualization.tabs import render_tab_m1, render_tab_m2, render_tab_m3
# v0.4.19 (C1): render_lifetime_panel moved from sidebar popover into
# tab_m3 as a primary M3 card. The import lives in tab_m3.py now.

# ─── Page Config ──────────────────────────────────────────────────────────

st.set_page_config(
    page_title="dpsim — Downstream Processing Simulator",
    page_icon="\U0001f52c",
    layout="wide",
)

# v0.4.0: design tokens from `design/tokens.css` are injected here as a
# single global stylesheet.
# v0.4.19 (A2/A3): consume the navigation query params BEFORE injecting
# CSS so theme/stage/view changes take effect on the same rerun. The
# alternative (consume during widget render) would emit dark CSS first
# and the new theme would only apply on the second click.
from dpsim.visualization.shell.shell import get_theme as _get_theme_for_css
# Theme query: ?dpsim_theme=light flips to light theme.
_theme_q = st.query_params.get("dpsim_theme")
if _theme_q in ("dark", "light"):
    from dpsim.visualization.shell.shell import set_theme as _set_theme_top
    _set_theme_top(_theme_q)  # type: ignore[arg-type]
    try:
        del st.query_params["dpsim_theme"]
    except KeyError:
        pass
inject_global_css(theme=_get_theme_for_css())

# Streamlit shell-specific overrides that DON'T belong in the shared
# token file: hide Streamlit's auto-page nav, hide the Deploy button,
# tighten widget margins, etc. Kept compact since the bulk of the
# styling now lives in tokens.css.
# v0.4.18 (P10): switched from st.html to st.markdown — Streamlit 1.55
# strips <style> tags from st.html output (see tokens.py docstring).
st.markdown(
    """
    <style>
    /* Hide Streamlit's auto-page nav (v9.0 M8). */
    [data-testid="stSidebarNav"] { display: none; }
    /* Hide the Deploy button — DPSim is local, not Streamlit Cloud. */
    [data-testid="stAppDeployButton"],
    [data-testid="stDeployButton"],
    .stAppDeployButton, .stDeployButton,
    [data-testid="stToolbar"] button[kind="headerNoPadding"]:first-child {
        display: none !important;
    }
    /* Streamlit slider needs vertical clearance for its value bubble. */
    [data-testid="stSlider"] {
        padding-top: 1.25rem !important;
        padding-bottom: 0.75rem !important;
    }
    /* Tighten the page container width allowance for the wide shell. */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 3rem !important;
        max-width: none !important;
    }
    /* Apply Geist + Geist Mono to the Streamlit content surface. */
    html, body, .stApp {
        font-family: "Geist", -apple-system, BlinkMacSystemFont, "Segoe UI",
                     system-ui, sans-serif;
        font-feature-settings: "ss01", "cv11";
    }
    .material-symbols-rounded, .material-symbols-outlined, .material-icons,
    [class*="material-symbols"], [class*="material-icons"],
    span[data-testid="stIconMaterial"] {
        font-family: "Material Symbols Rounded", "Material Symbols Outlined",
                     "Material Icons" !important;
    }
    code, pre, kbd, samp, .stCode pre {
        font-family: "JetBrains Mono", "Geist Mono", Menlo, Monaco,
                     "Cascadia Code", monospace !important;
    }
    [data-testid="stMetricValue"], [data-testid="stDataFrame"] td,
    [data-testid="stTable"] td, [data-testid="stDataFrame"] th {
        font-family: "Geist Mono", "JetBrains Mono", Menlo, monospace !important;
        font-feature-settings: "tnum", "zero";
    }
    .stButton > button { border-radius: 4px !important; font-weight: 500 !important; }
    .stButton > button[kind="primary"] {
        background-color: var(--dps-accent) !important;
        color: var(--dps-slate-950) !important;
        border-color: var(--dps-accent) !important;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: var(--dps-accent-hover) !important;
        border-color: var(--dps-accent-hover) !important;
    }
    /* v0.4.19 (D2): Scientific Mode segmented pill hover affordance. */
    .dps-mode-seg a:hover {
        background: var(--dps-surface-3) !important;
    }

    /* v0.4.19 (B2/B6): top-bar download buttons (Manual + Appendix J)
     * render as compact icon-only squares. The previous ``aria-label``
     * and ``data-testid``-keyed selectors didn't match because
     * ``st.download_button`` exposes neither (the ``key`` arg is for
     * Streamlit-internal state, not the DOM). Scope to ``stMain`` so
     * the rule only hits top-bar download buttons (the run rail and
     * other content panes don't use download_button). */
    [data-testid="stMain"] [data-testid="stDownloadButton"] button {
        padding: 0 !important;
        height: 26px !important;
        min-width: 26px !important;
        font-size: 14px !important;
        line-height: 1 !important;
    }
    /* Streamlit emits download_button as a stack with extra top-margin
     * — neutralise it so the icon row aligns with the DARK/LIGHT pill. */
    [data-testid="stMain"] [data-testid="stDownloadButton"] {
        margin-top: 0 !important;
        height: 26px !important;
    }

    /* v0.4.2: sticky right rail. Tag the second top-level horizontal
     * column with a sticky position. Streamlit doesn't expose a class
     * we can target by name, but the right rail is rendered as the
     * smallest-flex sibling under the main grid, so we scope to the
     * deepest-second column.
     */
    div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(2)
        > div[data-testid="stVerticalBlock"]:has(.dps-rail-marker) {
        position: sticky;
        top: 0.75rem;
        align-self: flex-start;
        max-height: calc(100vh - 1.5rem);
        overflow-y: auto;
    }

    /* v0.4.19 (A1): the previous .dps-spine-marker rules overlaid an
     * invisible click row on top of the visual chrome. The spine is
     * now a single anchor-link row (chrome.pipeline_spine emits
     * <a href="?dpsim_stage=...">), so no overlay is needed. */
    .dps-spine-link { cursor: pointer; }
    .dps-spine-link:hover > div {
        background: var(--dps-surface-2) !important;
    }

    /* v0.4.19 (A3): direction-switch hover affordance only.
     * The pill itself is rendered as a single HTML <div> with anchor
     * links by render_direction_switch — no Streamlit columns, so
     * no :has cascading-up issue. */
    .dps-dir-switch a:hover {
        background: var(--dps-surface-3) !important;
    }

    /* v0.4.6: triptych column-width animation. Streamlit columns are
     * flex children with `flex: <ratio> 1 0px`. Adding a transition on
     * `flex-grow` makes the focused-column expansion animate smoothly
     * (~200 ms). The `:has()` selector scopes the transition to
     * triptych contexts only; other column layouts stay instantaneous.
     */
    div[data-testid="stHorizontalBlock"]:has(.dps-triptych-marker)
        > div[data-testid="stColumn"] {
        transition: flex-grow 220ms cubic-bezier(0.2, 0, 0.2, 1),
                    flex-basis 220ms cubic-bezier(0.2, 0, 0.2, 1) !important;
    }
    /* Fallback for browsers that don't support :has() — apply globally;
     * the animation is too small to be disruptive elsewhere. */
    @supports not selector(:has(*)) {
        div[data-testid="stColumn"] {
            transition: flex-grow 220ms ease-out !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ─── Manual PDF helpers (preserved from v0.3.x) ──────────────────────────


def _render_manual_pdf_buttons() -> None:
    """Render the Manual + Appendix-J PDF download icons.

    v0.4.19 (B2): rendered as a horizontal pair of icon-only download
    buttons (24×24 px each) so they sit on the same top-bar row as the
    UI A|B switch and the DARK/LIGHT toggle, matching the canonical
    Direction-A reference's compact top bar. The previous version used
    full-width text-labelled buttons that stacked vertically and
    pushed the rail down at standard widescreen widths.
    """
    _um_dir = _root / "docs" / "user_manual"
    _manual_pdf = _um_dir / "polysaccharide_microsphere_simulator_first_edition.pdf"
    _appendix_j_pdf = _um_dir / "appendix_J_functionalization_protocols.pdf"

    if not _manual_pdf.exists() or not _appendix_j_pdf.exists():
        _build_script = _um_dir / "build_pdf.py"
        if _build_script.exists():
            try:
                import runpy
                runpy.run_path(str(_build_script), run_name="__main__")
            except Exception as _build_ex:  # pragma: no cover — defensive
                logger.warning("PDF auto-build failed: %s", _build_ex)

    icon_cols = st.columns([1, 1])
    with icon_cols[0]:
        if _manual_pdf.exists():
            with open(_manual_pdf, "rb") as _f:
                st.download_button(
                    label="\U0001F4D8",
                    data=_f.read(),
                    file_name="dpsim_First_Edition.pdf",
                    mime="application/pdf",
                    help="DPSim First-Edition instruction manual.",
                    key="_dpsim_manual_icon",
                    width="stretch",
                )
    with icon_cols[1]:
        if _appendix_j_pdf.exists():
            with open(_appendix_j_pdf, "rb") as _f:
                st.download_button(
                    label="\U0001F9EA",
                    data=_f.read(),
                    file_name="dpsim_Appendix_J_Functionalization.pdf",
                    mime="application/pdf",
                    help="Appendix J — Functionalisation Wet-Lab Protocols (44 reagents).",
                    key="_dpsim_appendix_j_icon",
                    width="stretch",
                )


# ─── Session state init ───────────────────────────────────────────────────

if "_state_mgr" not in st.session_state:
    st.session_state["_state_mgr"] = SessionStateManager()
    st.session_state["_state_mgr"].bind_store(st.session_state)
_smgr: SessionStateManager = st.session_state["_state_mgr"]
_workflow_recipe = ensure_process_recipe_state(st.session_state)

# v0.4.3: auto-load run history from disk on first render of the
# session. Idempotent — only runs once per session, gated on a session-
# state flag.
if "_dpsim_history_autoloaded" not in st.session_state:
    st.session_state["_dpsim_history_autoloaded"] = True
    try:
        from dpsim.visualization.run_rail import load_history_from_disk
        _autoload_n = load_history_from_disk()
        if _autoload_n > 0:
            logger.info("Auto-loaded %d run history entries from disk.", _autoload_n)
    except Exception as _autoload_exc:  # pragma: no cover — non-critical
        logger.debug("Run-history auto-load skipped: %s", _autoload_exc)


# ─── Scientific Mode (top-bar widget; replaces sidebar radio) ─────────────
# v0.4.19 (D2): rendered as an anchor-pill segmented control matching
# the Diff/Evidence/History style — three buttons inside one rounded
# pill, active button filled with the accent colour. Click sets
# ``?dpsim_mode={key}``; we consume the param at the top of app.py
# (before inject_global_css / render_shell) so the new mode flows into
# ``model_mode_enum`` on the same rerun.
_SCIENTIFIC_MODE_KEY = "dpsim_scientific_mode"
_SCIENTIFIC_MODE_QUERY = "dpsim_mode"
_SCIENTIFIC_MODE_OPTIONS: tuple[tuple[str, str, str], ...] = (
    ("empirical", "Empirical Engineering", ModelMode.EMPIRICAL_ENGINEERING.value),
    ("hybrid", "Hybrid Coupled", ModelMode.HYBRID_COUPLED.value),
    ("mechanistic", "Mechanistic Research", ModelMode.MECHANISTIC_RESEARCH.value),
)
_SCIENTIFIC_MODE_HELP = (
    "Empirical Engineering: fast screening, suppresses model warnings. "
    "Hybrid Coupled (default): phenomenological DN model with trust "
    "warnings. Mechanistic Research: Flory-Rehner affine IPN model, "
    "strictest trust gates."
)

# Consume ?dpsim_mode=… written by anchor clicks.
_mode_q = st.query_params.get(_SCIENTIFIC_MODE_QUERY)
if _mode_q in {k for k, _, _ in _SCIENTIFIC_MODE_OPTIONS}:
    st.session_state[_SCIENTIFIC_MODE_KEY] = _mode_q
    try:
        del st.query_params[_SCIENTIFIC_MODE_QUERY]
    except KeyError:
        pass

# Back-compat: previous radio stored the human label; coerce to key.
_legacy_label_to_key = {
    "Empirical Engineering": "empirical",
    "Empirical": "empirical",
    "Hybrid Coupled": "hybrid",
    "Hybrid": "hybrid",
    "Mechanistic Research": "mechanistic",
    "Mechanistic": "mechanistic",
}
_current_mode_key = st.session_state.get(_SCIENTIFIC_MODE_KEY, "hybrid")
if _current_mode_key in _legacy_label_to_key:
    _current_mode_key = _legacy_label_to_key[_current_mode_key]
    st.session_state[_SCIENTIFIC_MODE_KEY] = _current_mode_key

_mode_map = {
    "empirical": ModelMode.EMPIRICAL_ENGINEERING,
    "hybrid": ModelMode.HYBRID_COUPLED,
    "mechanistic": ModelMode.MECHANISTIC_RESEARCH,
}
model_mode_enum = _mode_map[_current_mode_key]


def _render_scientific_mode_radio() -> None:
    """Render the Scientific Mode anchor-pill in the top bar.

    Visual style mirrors the Diff/Evidence/History segmented control:
    one rounded pill enclosing three anchor-link buttons, with the
    active option filled in the accent colour. Click on a non-active
    option sets ``?dpsim_mode={key}`` and Streamlit reruns; the
    consume block at the top of app.py reads the param before
    ``inject_global_css`` / ``render_shell``, so the new mode is in
    effect on the same rerun.
    """
    current = st.session_state.get(_SCIENTIFIC_MODE_KEY, "hybrid")

    def _seg(key: str, label: str) -> str:
        import html as _h
        active = key == current
        bg = "var(--dps-accent)" if active else "transparent"
        fg = "var(--dps-slate-950)" if active else "var(--dps-text-muted)"
        return (
            f'<a href="?{_SCIENTIFIC_MODE_QUERY}={key}" target="_self" '
            f'title="{_h.escape(_SCIENTIFIC_MODE_HELP)}" '
            f'style="display:inline-flex;align-items:center;'
            f'justify-content:center;padding:0 10px;height:20px;'
            f'border-radius:3px;background:{bg};color:{fg};'
            f'font-family:var(--dps-font-sans);font-size:11px;'
            f'font-weight:600;text-decoration:none;cursor:pointer;'
            f'letter-spacing:0.02em;transition:background-color 120ms;'
            f'white-space:nowrap;">{label}</a>'
        )

    st.markdown(
        '<div class="dps-mode-seg" style="display:inline-flex;'
        "align-items:center;gap:0;padding:2px;height:26px;"
        "background:var(--dps-surface-2);"
        "border:1px solid var(--dps-border);border-radius:4px;"
        'max-width:100%;overflow:hidden;">'
        + "".join(_seg(k, lbl) for k, lbl, _ in _SCIENTIFIC_MODE_OPTIONS)
        + "</div>",
        unsafe_allow_html=True,
    )


# ─── Sidebar (now lean — scientific mode lives in the top bar) ────────────

st.sidebar.header("Global Settings")
st.sidebar.caption(
    "Scientific Mode now lives at the top of the page — see the radio "
    "row right of the recipes search input."
)

with st.sidebar:
    st.divider()
    st.caption("ANALYSIS TOOLS")
    st.caption("Calibration data is loaded and reviewed in workflow step 7.")
    # v0.4.19 (B1/C1): Both Uncertainty MC and Resin lifetime projection
    # have been promoted to primary M3 cards (see tab_m3.py). Keeping
    # the sidebar popovers caused StreamlitDuplicateElementKey crashes
    # on M3 since both panels register widgets with fixed keys.


# ─── Calibration Protocol Loader ─────────────────────────────────────────

_proto_path = Path(__file__).resolve().parents[3] / "docs" / "04_calibration_protocol.md"
_proto_sections: dict = {}
if _proto_path.exists():
    try:
        _proto_text = _proto_path.read_text(encoding="utf-8")
        _study_map = {
            "K_L":        ("Study 1 -- Interfacial Tension", "## 2. Study 1", "## 3. Study 2"),
            "Gamma_inf":  ("Study 1 -- Interfacial Tension", "## 2. Study 1", "## 3. Study 2"),
            "eta_chit":   ("Study 2 -- Chitosan Viscosity",  "## 3. Study 2", "## 4. Study 3"),
            "C3":         ("Study 3 -- Viscous Breakage",     "## 4. Study 3", "## 5. Study 4"),
            "pore":       ("Study 4 -- Pore Structure",       "## 5. Study 4", "## 6. Study 5"),
            "eta_coup":   ("Study 5 -- IPN Coupling",         "## 6. Study 5", "## 7. Inputting"),
        }
        for key, (title, start_marker, end_marker) in _study_map.items():
            s_idx = _proto_text.find(start_marker)
            e_idx = _proto_text.find(end_marker)
            if s_idx >= 0:
                section = _proto_text[s_idx:e_idx] if e_idx > s_idx else _proto_text[s_idx:]
                _proto_sections[key] = (title, section)
                if e_idx <= s_idx:
                    logger.warning(
                        "Calibration protocol end marker %r not found for %s; "
                        "serving from start marker to end of document.",
                        end_marker, key,
                    )
            else:
                logger.warning(
                    "Calibration protocol start marker %r not found for %s; "
                    "popover disabled.",
                    start_marker, key,
                )
    except Exception as exc:  # pragma: no cover — defensive: file was read once at import
        logger.warning("Could not parse calibration protocol %s: %s", _proto_path, exc)
        _proto_sections = {}


def _const_input(container, label, key, lit_val, unit, source_short, lo, hi, step,
                  proto_key, fmt="%.3f"):
    """Render per-constant selector with protocol link inside a given container."""
    if proto_key in _proto_sections:
        title, section_md = _proto_sections[proto_key]
        with container.popover(f"\U0001f4cb {label}"):
            st.markdown(f"### Calibration Protocol: {title}")
            st.markdown(section_md[:3000])
            if len(section_md) > 3000:
                st.caption("... (see full protocol in docs/04_calibration_protocol.md)")
    else:
        container.markdown(f"**{label}**")

    src = container.radio(
        "Source",
        ["Literature", "Custom"],
        index=0, horizontal=True, key=f"src_{key}",
        label_visibility="collapsed",
    )
    if src == "Literature":
        container.caption(f"  = {lit_val} {unit}  ({source_short})")
        return lit_val
    return container.number_input(
        f"{label} ({unit})", lo, hi, float(lit_val), step=step,
        format=fmt, key=f"val_{key}",
    )


# ═════════════════════════════════════════════════════════════════════════
# v0.4.0 Direction-A shell rendering
# ═════════════════════════════════════════════════════════════════════════
#
# v0.4.2: the legacy `render_lifecycle_workflow_panel` strip used to
# render above the shell here. It is now redundant with the new stage
# spine and has been removed; the spine itself is the lifecycle status
# strip. Stage statuses are derived from the live lifecycle_result via
# `derive_stage_status`.


def _render_stage(active: StageId) -> None:
    """Dispatch to the right per-stage renderer for the active stage.

    Each existing ``render_tab_m*`` is wrapped inside a fresh
    ``st.container()`` (passed as ``tab_container=`` for backwards
    compatibility with the original tab-based call sites).
    """
    recipe = ensure_process_recipe_state(st.session_state)
    if active == "target":
        render_target_product_profile_editor(recipe, st.session_state)
        return
    if active == "m1":
        container = st.container()
        with container:
            render_stage_context_panel(recipe, LifecycleStage.M1_FABRICATION)
        render_tab_m1(
            tab_container=container,
            is_stirred=None,
            model_mode_enum=model_mode_enum,
            _smgr=_smgr,
            _const_input=_const_input,
            _proto_sections=_proto_sections,
        )
        return
    if active == "m2":
        container = st.container()
        with container:
            render_stage_context_panel(recipe, LifecycleStage.M2_FUNCTIONALIZATION)
        render_tab_m2(tab_container=container, _smgr=_smgr)
        return
    if active == "m3":
        container = st.container()
        with container:
            render_stage_context_panel(recipe, LifecycleStage.M3_PERFORMANCE)
        render_tab_m3(tab_container=container)
        return
    if active == "run":
        render_run_lifecycle_stage(recipe, st.session_state)
        return
    if active == "validation":
        render_validation_stage(recipe, st.session_state)
        return
    if active == "calibrate":
        render_calibration_stage(recipe, st.session_state)
        return


# Auto-wire: detect run completion → snapshot recipe, append history,
# build evidence rollup, cache breakthrough curve. Returns the values
# the rail and top-bar should render right now.
_evidence_stages, _breakthrough = autowire_shell_state(
    current_recipe=_workflow_recipe
)
# Fall back to placeholders only when no run has completed yet.
if not _evidence_stages:
    _evidence_stages = default_evidence_stages()


def _render_rail() -> None:
    """Sticky right-pane rail. Shows run controls, breakthrough preview,
    evidence, recipe diff, named-baseline picker, and run history with
    disk persistence + reload action.
    """
    from dpsim.visualization.diff import render_baseline_picker
    from dpsim.visualization.run_rail import render_history_dropdown

    def _rail_extras() -> None:
        # 1. Run history (auto-loaded from disk on session start; user
        #    can save / reload-this-run / reload-from-disk here).
        render_history_dropdown(
            current_recipe=_workflow_recipe,
            enable_disk_persistence=True,
        )
        # 2. Named-baseline picker; selected name drives the diff target
        #    via session_state, consumed by render_diff_panel below.
        selected = render_baseline_picker(current_recipe=_workflow_recipe)
        st.session_state["_dpsim_diff_baseline_name"] = selected

    render_run_rail(
        current_recipe=_workflow_recipe,
        stages=_evidence_stages,
        breakthrough_curve=_breakthrough,
        extra_top_section=_rail_extras,
    )


# Compute "modified" state for the breadcrumb chip.
try:
    _diffs_pending = len(diff_entries(_workflow_recipe))
except Exception:  # pragma: no cover — diff is non-critical
    _diffs_pending = 0

# Derive per-stage status from lifecycle_result (defaults to all-pending
# when nothing has run yet).
_status_map = derive_stage_status(current_recipe=_workflow_recipe)

# v0.4.2: A/B direction switch. Direction A = pipeline-as-spine (the
# v0.4.0 shell). Direction B = triptych workbench — three columns
# always visible, focused column expands.
_direction = get_direction()

if _direction == "a":
    render_shell(
        version="0.4.2",
        breadcrumb_recipe="protein_a_pilot.toml",
        modified=_diffs_pending > 0,
        evidence_stages=_evidence_stages,
        stage_renderer=_render_stage,
        rail_renderer=_render_rail,
        manual_pdf_button=_render_manual_pdf_buttons,
        stage_status_map=_status_map,
        direction_switch_renderer=render_direction_switch,
        scientific_mode_renderer=_render_scientific_mode_radio,
    )
else:
    # Direction B — triptych. v0.4.12: the 7-stage tab strip is now
    # rendered above the triptych (matches the reference screenshots).
    # Behaviour: clicking M1/M2/M3 focuses that triptych column;
    # clicking a non-triptych stage (Target/Run/Validate/Calibrate)
    # falls back to a single-stage view, same as Direction A.
    from dpsim.visualization.shell.shell import (
        render_stage_spine as _render_stage_spine,
        render_top_bar as _render_top_bar,
    )
    from dpsim.visualization.shell.triptych import (
        get_triptych_focus,
        set_triptych_focus,
    )
    _render_top_bar(
        version="0.4.2",
        breadcrumb_recipe="protein_a_pilot.toml",
        modified=_diffs_pending > 0,
        evidence_stages=_evidence_stages,
        manual_pdf_button=_render_manual_pdf_buttons,
        direction_switch_renderer=render_direction_switch,
        scientific_mode_renderer=_render_scientific_mode_radio,
    )
    _b_evidence_map = {s.stage_id: s.tier for s in _evidence_stages}
    _b_active = _render_stage_spine(
        status_map=_status_map,
        evidence_map=_b_evidence_map,
    )

    # If a triptych stage is active, sync the focus and render the
    # triptych. Otherwise render the single-stage body (Target / Run /
    # Validate / Calibrate are not part of the triptych).
    if _b_active in ("m1", "m2", "m3"):
        if get_triptych_focus() != _b_active:
            set_triptych_focus(_b_active)  # type: ignore[arg-type]

    def _b_m1() -> None:
        _render_stage("m1")

    def _b_m2() -> None:
        _render_stage("m2")

    def _b_m3() -> None:
        _render_stage("m3")

    def _b_dock() -> None:
        _render_rail()

    if _b_active not in ("m1", "m2", "m3"):
        # Single-stage view for non-triptych stages; reuse the same
        # main grid so the rail still appears on the right.
        from dpsim.visualization.shell.shell import render_main_grid
        render_main_grid(
            stage_renderer=_render_stage,
            rail_renderer=_render_rail,
        )
    else:
        render_triptych(
            m1_renderer=_b_m1,
            m2_renderer=_b_m2,
            m3_renderer=_b_m3,
            evidence_stages=_evidence_stages,
            dock_renderer=_b_dock,
        )
