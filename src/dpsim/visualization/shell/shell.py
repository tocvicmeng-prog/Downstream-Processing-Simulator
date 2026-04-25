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


def _render_theme_toggle() -> None:
    """Render the dark/light segmented switch and apply the body class.

    The segmented switch is two ``st.button`` calls in a tight column
    pair so a click flips the session-state theme. The class flip on
    ``document.documentElement`` is performed via an injected ``<script>``
    each render — Streamlit's iframe boundary forces the JS to re-run on
    every page render, but the operation is idempotent.
    """
    theme = get_theme()
    pair = st.columns([1, 1])
    with pair[0]:
        if st.button(
            "DARK",
            key="_dpsim_theme_dark",
            type="primary" if theme == "dark" else "secondary",
            use_container_width=True,
        ):
            set_theme("dark")
            st.rerun()
    with pair[1]:
        if st.button(
            "LIGHT",
            key="_dpsim_theme_light",
            type="primary" if theme == "light" else "secondary",
            use_container_width=True,
        ):
            set_theme("light")
            st.rerun()
    # JS: apply / remove the .dps-light class on the document element so
    # the iframe-side tokens.css responds. Idempotent on every render.
    add_or_remove = "add" if theme == "light" else "remove"
    st.html(
        f"<script>"
        f"document.documentElement.classList.{add_or_remove}('dps-light');"
        f"</script>"
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
    # run-history ghost button. Column ratios chosen so each cell has
    # enough breathing room at typical widescreen widths.
    cols = st.columns([0.55, 0.6, 2.4, 1.8, 1.8, 1.6, 1.4, 1.2])

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
        # Theme toggle + manual stacked into a tight 2-row cell so the
        # right edge stays compact at common widescreen widths.
        _render_theme_toggle()
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


def _render_top_bar_view_segmented() -> None:
    """Render the Diff / Evidence / History segmented control.

    Drives ``st.session_state[_VIEW_MODE_KEY]`` ∈ {``diff``, ``evidence``,
    ``history``}; downstream rail / panel render functions can read it to
    switch their primary content. Default: ``diff`` (the recipe-edit
    cockpit view).
    """
    current = st.session_state.get(_VIEW_MODE_KEY, "diff")
    cols = st.columns(3)
    options = (("diff", "Diff"), ("evidence", "Evidence"), ("history", "History"))
    for i, (key, label) in enumerate(options):
        with cols[i]:
            if st.button(
                label,
                key=f"_dpsim_topbar_view_{key}",
                type="primary" if current == key else "secondary",
                use_container_width=True,
            ):
                st.session_state[_VIEW_MODE_KEY] = key
                st.rerun()


def render_stage_spine(
    *, status_map: dict[str, str] | None = None,
    evidence_map: dict[str, str] | None = None,
) -> StageId:
    """Render the 7-stage pipeline spine and handle click navigation.

    Two-pass rendering:
        1. The visual chrome (``chrome.pipeline_spine``) painted via st.html.
        2. A row of ``st.button`` for click handling underneath the
           visual chrome.

    Args:
        status_map: Optional mapping from stage id → status literal
            (``pending`` / ``active`` / ``valid`` / ``warn``). Stages
            not in the map default to ``pending``. Drives stage-node
            colouring. ``None`` is equivalent to all-pending (the
            v0.4.0 behaviour).
        evidence_map: Optional mapping from stage id → evidence-tier
            string. Renders inline compact badges on the spine cells.

    Returns:
        The currently active stage id.
    """
    active = get_active_stage()
    status_map = status_map or {}
    evidence_map = evidence_map or {}
    # Layer 1: visual chrome — derive each stage's status.
    specs = [
        chrome.StageSpec(
            id=sid,
            label=lbl,
            status=status_map.get(sid, "pending"),  # type: ignore[arg-type]
            evidence=evidence_map.get(sid),
        )
        for sid, lbl in STAGE_ORDER
    ]
    # Anchor marker so app.py's CSS can scope the click-row overlay.
    st.html('<div class="dps-spine-marker"></div>')
    st.html(chrome.pipeline_spine(specs, active_id=active))

    # Layer 2: click handlers — minimal-text buttons in a 7-column row.
    cols = st.columns(len(STAGE_ORDER))
    for i, (sid, lbl) in enumerate(STAGE_ORDER):
        with cols[i]:
            short = lbl.split(" — ")[0] if " — " in lbl else lbl
            if st.button(short, key=f"_dpsim_stage_btn_{sid}",
                         use_container_width=True):
                set_active_stage(sid)  # type: ignore[arg-type]
                st.rerun()
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


