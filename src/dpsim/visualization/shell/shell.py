"""Direction-A shell composition."""

from __future__ import annotations

from collections.abc import Callable
from typing import Final, Literal

import streamlit as st

from dpsim.visualization.design import chrome
from dpsim.visualization.evidence.rollup import (
    StageEvidence,
    render_top_bar_badge,
)

StageId = Literal["target", "m1", "m2", "m3", "run", "validation", "calibrate"]

STAGE_ORDER: Final[list[tuple[str, str]]] = [
    ("target", "Target profile"),
    ("m1", "M1 — Fabrication"),
    ("m2", "M2 — Functionalisation"),
    ("m3", "M3 — Column method"),
    ("run", "Run lifecycle"),
    ("validation", "Validation"),
    ("calibrate", "Calibration"),
]

_STAGE_RECIPE_PATH: Final[dict[str, str]] = {
    "target": "Target product profile",
    "m1": "M1 ProcessRecipe.fabrication",
    "m2": "M2 ProcessRecipe.functionalization",
    "m3": "M3 ProcessRecipe.performance",
    "run": "Lifecycle simulation",
    "validation": "Validation report",
    "calibrate": "Calibration store",
}

ACTIVE_STAGE_KEY: Final[str] = "_dpsim_shell_active_stage"
THEME_KEY: Final[str] = "_dpsim_shell_theme"

ThemeMode = Literal["dark", "light"]


def get_active_stage() -> StageId:
    """Read the active stage from session state (defaults to ``target``)."""
    return st.session_state.get(ACTIVE_STAGE_KEY, "target")  # type: ignore[no-any-return]


def set_active_stage(stage: StageId) -> None:
    """Set the active stage."""
    st.session_state[ACTIVE_STAGE_KEY] = stage


def get_theme() -> ThemeMode:
    """Read the current theme (default ``dark`` per DESIGN.md)."""
    return st.session_state.get(THEME_KEY, "dark")  # type: ignore[no-any-return]


def set_theme(theme: ThemeMode) -> None:
    """Set the theme. Caller is responsible for triggering a rerender."""
    st.session_state[THEME_KEY] = theme


_THEME_QUERY_KEY: Final[str] = "dpsim_theme"


def _consume_theme_query() -> None:
    """Translate ``?dpsim_theme=…`` (set by toggle anchor clicks) into
    a session-state theme update, then delete the query param."""
    raw = st.query_params.get(_THEME_QUERY_KEY)
    if not raw:
        return
    target = raw if isinstance(raw, str) else (raw[0] if raw else "")
    if target in ("dark", "light"):
        set_theme(target)  # type: ignore[arg-type]
    try:
        del st.query_params[_THEME_QUERY_KEY]
    except KeyError:
        pass


def _render_theme_toggle() -> None:
    """Render the theme toggle as a single fidelity-matched button.

    v0.4.19 (B3): matches the canonical Direction-A ``ThemeToggle``
    component exactly — ONE button (not a segmented pill) showing the
    current mode with a colored dot indicator and the mode label.
    Click toggles to the opposite mode.

    Visual:
        Dark mode: ●  DARK    (dot = teal accent)
        Light mode: ●  LIGHT  (dot = amber-500)

    A click sets ``?dpsim_theme={opposite}``;
    ``_consume_theme_query`` updates ``THEME_KEY`` on the next rerun
    so ``inject_global_css`` re-emits the appropriate ``:root`` vars.
    """
    _consume_theme_query()
    theme = get_theme()
    is_light = theme == "light"
    dot_color = (
        "var(--dps-amber-500)" if is_light else "var(--dps-accent)"
    )
    label = "LIGHT" if is_light else "DARK"
    next_theme = "dark" if is_light else "light"
    st.markdown(
        f'<a class="dps-theme-toggle" href="?{_THEME_QUERY_KEY}={next_theme}" '
        f'target="_self" title="Toggle theme" '
        f'style="display:inline-flex;align-items:center;gap:6px;'
        f'padding:0 10px;height:26px;'
        f'background:var(--dps-surface-2);'
        f'border:1px solid var(--dps-border);'
        f'border-radius:4px;color:var(--dps-text-muted);'
        f'font-family:var(--dps-font-mono);font-size:11px;'
        f'font-weight:600;letter-spacing:0.04em;'
        f'text-decoration:none;cursor:pointer;'
        f'transition:all 150ms ease-out;">'
        f'<span style="width:8px;height:8px;border-radius:8px;'
        f'background:{dot_color};display:inline-block;"></span>'
        f"{label}"
        "</a>",
        unsafe_allow_html=True,
    )


def render_top_bar(
    *,
    version: str = "0.3.8",
    breadcrumb_recipe: str = "protein_a_pilot.toml",
    modified: bool = False,
    evidence_stages: list[StageEvidence] | None = None,
    manual_pdf_button: Callable[[], None] | None = None,
    direction_switch_renderer: Callable[[], None] | None = None,
) -> None:
    """Render the top application bar.

    Composition (left → right) per the canonical Direction-A reference
    (``DPSim UI Optimization _standalone_.html``):

        [brand] [UI A/B switch] [vdiv] [workspace/recipes/<file> + chip]
        [search input] [vdiv] [evidence rollup] [run #N ghost btn]
        [Diff/Evidence/History segmented] [vdiv] [theme] [manual]

    Args:
        version: Application version string.
        breadcrumb_recipe: Currently loaded recipe filename.
        modified: Whether the recipe has unsaved edits (shows amber chip).
        evidence_stages: Optional per-stage evidence summaries for the
            top-bar lifecycle-min badge.
        manual_pdf_button: Optional callable for the manual + appendix
            PDF download button(s). Called in the right-hand top-bar
            slot.
        direction_switch_renderer: Optional callable that renders the
            UI · A | B segmented switch inline in the top bar. When
            provided, the switch sits between brand and breadcrumb to
            match the canonical reference (F-15a).
    """
    # v0.4.16: top-bar restructured to match the canonical Direction-A
    # reference. Adds: inline DirectionSwitch, vertical-divider rules,
    # workspace/ breadcrumb prefix, decorative search input, and a
    # run-history ghost button.
    # v0.4.19 (B2): split cols[7] into theme-toggle (0.9) + manual-icons
    # (0.4) so Manual + Appendix J render as a horizontal icon pair to
    # the right of the DARK/LIGHT pill instead of stacking below it.
    cols = st.columns([0.55, 0.6, 2.4, 1.8, 1.8, 1.6, 1.4, 0.9, 0.4])

    with cols[0]:
        st.html(
            '<div style="display:flex;align-items:center;gap:10px;'
            'padding:6px 0;">'
            '<div style="width:24px;height:24px;border-radius:4px;'
            'background:var(--dps-accent);display:flex;align-items:center;'
            'justify-content:center;color:var(--dps-slate-950);'
            'font-family:var(--dps-font-mono);font-weight:700;'
            'font-size:13px;">D</div>'
            '<div style="display:flex;flex-direction:column;line-height:1.1;">'
            '<span style="font-size:13px;font-weight:600;">DPSim</span>'
            f'<span class="dps-mono" style="font-size:10px;'
            f'color:var(--dps-text-dim);">v{version}</span>'
            '</div></div>'
        )

    with cols[1]:
        # F-15a: DirectionSwitch lives INSIDE the top bar (was below it
        # before). Falls back to a vdivider-only cell if the caller
        # didn't pass a renderer.
        if direction_switch_renderer is not None:
            direction_switch_renderer()
        else:
            st.html(
                '<div class="dps-vdivider" style="height:22px;'
                'margin:6px auto;"></div>'
            )

    with cols[2]:
        # F-14: breadcrumb prefix is now ``workspace/recipes/`` per the
        # canonical reference; the leading ``workspace/`` segment is
        # rendered dim to keep the file name dominant.
        modified_chip = (
            chrome.chip("modified", color="var(--dps-amber-500)")
            if modified
            else ""
        )
        st.html(
            '<div class="dps-mono" style="display:flex;align-items:center;'
            'gap:6px;font-size:12px;color:var(--dps-text-muted);'
            'padding:8px 0;">'
            '<span style="color:var(--dps-text-dim);">workspace</span>'
            '<span style="color:var(--dps-text-dim);">/</span>'
            '<span>recipes</span>'
            '<span style="color:var(--dps-text-dim);">/</span>'
            f'<span style="color:var(--dps-text);">{breadcrumb_recipe}</span>'
            f'{modified_chip}</div>'
        )

    with cols[3]:
        # F-13: decorative global search input ("Search recipes,
        # reagents…"). Wired to a session-state key so future iterations
        # can drive an actual filter; for now it's chrome only.
        st.text_input(
            "Search",
            key="_dpsim_topbar_search",
            label_visibility="collapsed",
            placeholder="Search recipes, reagents…",
        )

    with cols[4]:
        # F-15b: run-history ghost button — clicking it opens the rail
        # extras expander by setting a session-state flag. Cheap; the
        # actual history lives in run_rail.
        _render_run_history_ghost_button()

    with cols[5]:
        if evidence_stages:
            st.html(
                '<div style="display:flex;align-items:center;'
                'justify-content:flex-end;padding:6px 0;">'
                + render_top_bar_badge(evidence_stages)
                + '</div>'
            )

    with cols[6]:
        # Diff / Evidence / History segmented (v0.4.15).
        _render_top_bar_view_segmented()

    with cols[7]:
        # v0.4.19 (B2): theme toggle now lives alone in cols[7]; the
        # manual-icons render in cols[8] to the right.
        _render_theme_toggle()

    with cols[8]:
        # v0.4.19 (B2): icon-only Manual + Appendix-J download buttons
        # in their own column so they share the same row as the
        # DARK/LIGHT pill (matches the canonical Direction-A reference).
        if manual_pdf_button is not None:
            manual_pdf_button()


def _render_run_history_ghost_button() -> None:
    """Top-bar ghost button showing the latest run id + relative time.

    Click flips ``_dpsim_show_history_drawer`` so the rail can react.
    Falls back to a "no runs yet" muted label when history is empty.
    """
    try:
        from dpsim.visualization.run_rail import latest as _latest
    except ImportError:  # pragma: no cover — visualisation always present
        _latest = None  # type: ignore[assignment]
    entry = _latest() if _latest is not None else None
    if entry is None:
        st.html(
            '<div class="dps-mono" style="font-size:11px;'
            'color:var(--dps-text-dim);padding:8px 0;text-align:right;">'
            "↻ no runs yet</div>"
        )
        return
    from datetime import datetime, timezone

    delta = datetime.now(tz=timezone.utc) - entry.timestamp_utc
    seconds = int(delta.total_seconds())
    if seconds < 60:
        rel = f"{seconds}s ago"
    elif seconds < 3600:
        rel = f"{seconds // 60} min ago"
    elif seconds < 86400:
        rel = f"{seconds // 3600} h ago"
    else:
        rel = f"{seconds // 86400} d ago"
    label = f"↻ Run #{entry.run_id} · {rel}"
    if st.button(
        label,
        key="_dpsim_topbar_run_history",
        use_container_width=True,
        help="Open run history & baseline picker",
    ):
        st.session_state["_dpsim_show_history_drawer"] = True
        st.rerun()


_VIEW_MODE_KEY: Final[str] = "_dpsim_topbar_view_mode"
_VIEW_MODE_QUERY_KEY: Final[str] = "dpsim_view"


def _consume_view_mode_query() -> None:
    """Translate ``?dpsim_view=…`` into a session-state view-mode update."""
    raw = st.query_params.get(_VIEW_MODE_QUERY_KEY)
    if not raw:
        return
    target = raw if isinstance(raw, str) else (raw[0] if raw else "")
    if target in ("diff", "evidence", "history"):
        st.session_state[_VIEW_MODE_KEY] = target
    try:
        del st.query_params[_VIEW_MODE_QUERY_KEY]
    except KeyError:
        pass


def _render_top_bar_view_segmented() -> None:
    """Render the Diff / Evidence / History segmented as an anchor pill.

    v0.4.19 (A3 follow-on): single HTML block with three anchor links.
    Replaces the previous 3-sub-column ``st.button`` layout, which got
    squashed at typical widescreen widths (each label wrapped to one
    letter per line inside its narrow sub-column).

    Drives ``st.session_state[_VIEW_MODE_KEY]`` ∈ {``diff``, ``evidence``,
    ``history``}; downstream rail / panel render functions read it to
    switch their primary content. Default: ``diff``.
    """
    _consume_view_mode_query()
    current = st.session_state.get(_VIEW_MODE_KEY, "diff")
    options = (("diff", "Diff"), ("evidence", "Evidence"), ("history", "History"))

    def _seg(key: str, label: str) -> str:
        active = key == current
        bg = "var(--dps-accent)" if active else "transparent"
        fg = "var(--dps-slate-950)" if active else "var(--dps-text-muted)"
        return (
            f'<a href="?{_VIEW_MODE_QUERY_KEY}={key}" target="_self" '
            f'style="display:inline-flex;align-items:center;'
            f'justify-content:center;padding:0 10px;height:20px;'
            f'border-radius:3px;background:{bg};color:{fg};'
            f'font-family:var(--dps-font-sans);font-size:11px;'
            f'font-weight:600;text-decoration:none;cursor:pointer;'
            f'letter-spacing:0.02em;transition:background-color 120ms;">'
            f"{label}</a>"
        )

    st.markdown(
        '<div class="dps-view-seg" style="display:inline-flex;'
        "align-items:center;gap:0;padding:2px;height:26px;"
        "background:var(--dps-surface-2);"
        "border:1px solid var(--dps-border);border-radius:4px;\">"
        + "".join(_seg(k, lbl) for k, lbl in options)
        + "</div>",
        unsafe_allow_html=True,
    )


_STAGE_NAV_QUERY_KEY: Final[str] = "dpsim_stage"


def _consume_stage_nav_query() -> None:
    """Translate ``?dpsim_stage=…`` (set by spine anchor clicks) into
    a session-state active-stage update, then delete the query param so
    the URL stays clean for subsequent navigation.

    v0.4.19 (A1): replaces the previous ``st.button``-overlay click
    row. The spine now renders as a single ``<nav>`` of anchor links
    that set this query param; we read it here at the top of each
    rerun and dispatch.
    """
    valid_ids = {sid for sid, _ in STAGE_ORDER}
    raw = st.query_params.get(_STAGE_NAV_QUERY_KEY)
    if not raw:
        return
    target = raw if isinstance(raw, str) else (raw[0] if raw else "")
    if target in valid_ids:
        set_active_stage(target)  # type: ignore[arg-type]
    # Remove the param so reloads / shares don't pin the user to that
    # stage; session state is the source of truth from here on.
    try:
        del st.query_params[_STAGE_NAV_QUERY_KEY]
    except KeyError:
        pass


def render_stage_spine(
    *, status_map: dict[str, str] | None = None,
    evidence_map: dict[str, str] | None = None,
) -> StageId:
    """Render the 7-stage pipeline spine.

    v0.4.19 (A1): single-pass render. Each stage cell is an anchor
    link that sets ``?dpsim_stage={id}``; ``_consume_stage_nav_query``
    (called once at the top of the shell render) reads the param and
    updates ``ACTIVE_STAGE_KEY``. The previous parallel ``st.button``
    row is gone — that overlay was fragile (the CSS scoping selector
    broke against newer Streamlit DOM emissions, leaving a redundant
    plain-text row visible).

    Args:
        status_map: Optional mapping from stage id → status literal
            (``pending`` / ``active`` / ``valid`` / ``warn``). Stages
            not in the map default to ``pending``.
        evidence_map: Optional mapping from stage id → evidence-tier
            string. Renders inline compact badges on the spine cells.

    Returns:
        The currently active stage id.
    """
    _consume_stage_nav_query()
    active = get_active_stage()
    status_map = status_map or {}
    evidence_map = evidence_map or {}
    specs = [
        chrome.StageSpec(
            id=sid,
            label=lbl,
            status=status_map.get(sid, "pending"),  # type: ignore[arg-type]
            evidence=evidence_map.get(sid),
        )
        for sid, lbl in STAGE_ORDER
    ]
    st.markdown(
        chrome.pipeline_spine(
            specs, active_id=active, nav_query_key=_STAGE_NAV_QUERY_KEY,
        ),
        unsafe_allow_html=True,
    )
    return active


def render_main_grid(
    *,
    stage_renderer: Callable[[StageId], None],
    rail_renderer: Callable[[], None],
) -> None:
    """Render the 2-column main grid: stage body | sticky run rail.

    Args:
        stage_renderer: Callable that renders the body for a given
            stage. Will be invoked with the current active stage id.
        rail_renderer: Callable that renders the run rail. Invoked with
            no args; uses session state for its inputs.
    """
    cols = st.columns([3, 1.1])
    with cols[0]:
        stage_renderer(get_active_stage())
    with cols[1]:
        # Sticky positioning is best-effort with Streamlit's layout; we
        # rely on the right column being short enough that scrolling
        # the left does not desync the rail visually.
        rail_renderer()


def render_stage_nav_footer() -> None:
    """Render the bottom-of-page "← Stage NN / Stage NN →" navigation.

    Mirrors the pair shown along the foot of the Direction-A reference
    screenshots. The two buttons step the active stage one slot
    backward / forward, wrapping at the ends.
    """
    active = get_active_stage()
    ids = [sid for sid, _ in STAGE_ORDER]
    try:
        idx = ids.index(active)
    except ValueError:
        idx = 0

    prev_idx = idx - 1 if idx > 0 else None
    next_idx = idx + 1 if idx < len(STAGE_ORDER) - 1 else None

    st.html('<div class="dps-divider" style="margin:24px 0 12px 0;"></div>')
    cols = st.columns([1, 4, 1])
    with cols[0]:
        if prev_idx is not None:
            prev_id, prev_label = STAGE_ORDER[prev_idx]
            short = prev_label.split(" — ")[0] if " — " in prev_label else prev_label
            if st.button(
                f"← Stage 0{prev_idx + 1} · {short}",
                key="_dpsim_stage_nav_prev",
                use_container_width=True,
            ):
                set_active_stage(prev_id)  # type: ignore[arg-type]
                st.rerun()
    with cols[1]:
        stage_path = _STAGE_RECIPE_PATH.get(active, "")
        st.html(
            f'<div style="font-family:var(--dps-font-mono);font-size:11px;'
            f'color:var(--dps-text-dim);text-align:center;padding:6px 0;">'
            f"recipe → {stage_path}"
            f"</div>"
        )
    with cols[2]:
        if next_idx is not None:
            next_id, next_label = STAGE_ORDER[next_idx]
            short = next_label.split(" — ")[0] if " — " in next_label else next_label
            if st.button(
                f"Stage 0{next_idx + 1} · {short} →",
                key="_dpsim_stage_nav_next",
                type="primary",
                use_container_width=True,
            ):
                set_active_stage(next_id)  # type: ignore[arg-type]
                st.rerun()


def render_shell(
    *,
    version: str,
    breadcrumb_recipe: str,
    modified: bool,
    evidence_stages: list[StageEvidence],
    stage_renderer: Callable[[StageId], None],
    rail_renderer: Callable[[], None],
    manual_pdf_button: Callable[[], None] | None = None,
    stage_status_map: dict[str, str] | None = None,
    direction_switch_renderer: Callable[[], None] | None = None,
) -> None:
    """Render the full Direction-A shell."""
    render_top_bar(
        version=version,
        breadcrumb_recipe=breadcrumb_recipe,
        modified=modified,
        evidence_stages=evidence_stages,
        manual_pdf_button=manual_pdf_button,
        direction_switch_renderer=direction_switch_renderer,
    )
    # Build per-stage evidence map from evidence_stages so the spine can
    # show inline tier badges.
    evidence_map = {s.stage_id: s.tier for s in evidence_stages}
    render_stage_spine(status_map=stage_status_map, evidence_map=evidence_map)
    render_main_grid(
        stage_renderer=stage_renderer,
        rail_renderer=rail_renderer,
    )
    render_stage_nav_footer()


def default_evidence_stages() -> list[StageEvidence]:
    """Return an empty evidence list for the pre-run state.

    Audit fix (v0.4.9 F-4): the previous implementation returned
    hardcoded CAL/SEMI/SEMI tiers as a "placeholder" — but the
    top-bar badge then displayed those fake tiers as if they were
    real evidence assessments, which is exactly the inheritance-
    violation read the v9.0 evidence model is designed to prevent.

    Return ``[]`` so the top-bar / rail rollup code paths can detect
    "no run yet" and render an honest "—" instead of a fake tier.
    """
    return []


