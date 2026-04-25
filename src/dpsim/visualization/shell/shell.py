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
) -> None:
    """Render the top application bar.

    Composition (left → right):
        [brand mark] [version] | [breadcrumb] [modified chip]
        ──── flex spacer ────
        [evidence rollup badge] | [manual PDF download]

    Args:
        version: Application version string.
        breadcrumb_recipe: Currently loaded recipe filename.
        modified: Whether the recipe has unsaved edits (shows amber chip).
        evidence_stages: Optional per-stage evidence summaries for the
            top-bar lifecycle-min badge.
        manual_pdf_button: Optional callable that emits the Streamlit
            download button(s) for the manual + appendix PDFs. Called
            in the right-hand top-bar column.
    """
    cols = st.columns([0.6, 3.6, 2.4, 1.4, 1.5])

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
            f'color:var(--dps-text-dim);">v{version} · downstream simulator</span>'
            '</div></div>'
        )

    with cols[1]:
        modified_chip = (
            chrome.chip("modified", color="var(--dps-amber-500)")
            if modified
            else ""
        )
        st.html(
            '<div class="dps-mono" style="display:flex;align-items:center;'
            'gap:8px;font-size:12px;color:var(--dps-text-muted);'
            'padding:8px 0;">'
            '<span>recipes/</span>'
            f'<span style="color:var(--dps-text);">{breadcrumb_recipe}</span>'
            f'{modified_chip}</div>'
        )

    with cols[2]:
        if evidence_stages:
            st.html(
                '<div style="display:flex;align-items:center;'
                'justify-content:flex-end;padding:6px 0;">'
                + render_top_bar_badge(evidence_stages)
                + '</div>'
            )

    with cols[3]:
        # Theme toggle (v0.4.1). Tokens already support .dps-light scope;
        # this binds it to a clickable segmented switch.
        _render_theme_toggle()

    with cols[4]:
        if manual_pdf_button is not None:
            manual_pdf_button()


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
) -> None:
    """Render the full Direction-A shell."""
    render_top_bar(
        version=version,
        breadcrumb_recipe=breadcrumb_recipe,
        modified=modified,
        evidence_stages=evidence_stages,
        manual_pdf_button=manual_pdf_button,
    )
    # Build per-stage evidence map from evidence_stages so the spine can
    # show inline tier badges.
    evidence_map = {s.stage_id: s.tier for s in evidence_stages}
    render_stage_spine(status_map=stage_status_map, evidence_map=evidence_map)
    render_main_grid(
        stage_renderer=stage_renderer,
        rail_renderer=rail_renderer,
    )


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


