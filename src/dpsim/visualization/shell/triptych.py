"""Direction B — Triptych workbench.

M1 / M2 / M3 always co-visible as three side-by-side columns. The
focused column expands to show the full editor; the other two collapse
to summary chips. A bottom dock holds: pending edits · evidence-min
stacked bar · last-run KPIs + Run lifecycle CTA — laid out as three
inline panes per the Direction-B reference.

This is a Streamlit-native rendition of `direction-b.jsx` from the
design handoff. Direction switching is via the top-bar A/B button (see
``shell.shell.render_top_bar`` in v0.4.2+).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Final, Literal

import streamlit as st

from dpsim.datatypes import ModelEvidenceTier
from dpsim.visualization.design import chrome
from dpsim.visualization.evidence.rollup import StageEvidence, aggregate_min_tier

TriptychFocus = Literal["m1", "m2", "m3"]

DIRECTION_KEY: Final[str] = "_dpsim_shell_direction"
TRIPTYCH_FOCUS_KEY: Final[str] = "_dpsim_triptych_focus"

# Local tier→{color, short-label} mappings for the dock evidence bar.
# Mirrors the same data in chrome.py without reaching into its private
# globals (chrome.py exposes the badge primitive, not the raw dicts).
_DOCK_TIER_COLOR: Final[dict[str, str]] = {
    ModelEvidenceTier.VALIDATED_QUANTITATIVE.value: "var(--dps-green-600)",
    ModelEvidenceTier.CALIBRATED_LOCAL.value: "var(--dps-green-500)",
    ModelEvidenceTier.SEMI_QUANTITATIVE.value: "var(--dps-amber-500)",
    ModelEvidenceTier.QUALITATIVE_TREND.value: "var(--dps-orange-500)",
    ModelEvidenceTier.UNSUPPORTED.value: "var(--dps-red-600)",
}
_DOCK_TIER_SHORT: Final[dict[str, str]] = {
    ModelEvidenceTier.VALIDATED_QUANTITATIVE.value: "VAL",
    ModelEvidenceTier.CALIBRATED_LOCAL.value: "CAL",
    ModelEvidenceTier.SEMI_QUANTITATIVE.value: "SEMI",
    ModelEvidenceTier.QUALITATIVE_TREND.value: "QUAL",
    ModelEvidenceTier.UNSUPPORTED.value: "UNS",
}

ShellDirection = Literal["a", "b"]


def get_direction() -> ShellDirection:
    """Read the current shell direction (A = pipeline-spine, B = triptych)."""
    return st.session_state.get(DIRECTION_KEY, "a")  # type: ignore[no-any-return]


def set_direction(direction: ShellDirection) -> None:
    """Set the shell direction; caller triggers rerun."""
    st.session_state[DIRECTION_KEY] = direction


def get_triptych_focus() -> TriptychFocus:
    """Read which column has focus in the triptych (default ``m2``)."""
    return st.session_state.get(TRIPTYCH_FOCUS_KEY, "m2")  # type: ignore[no-any-return]


def set_triptych_focus(focus: TriptychFocus) -> None:
    """Set the triptych's focused column."""
    st.session_state[TRIPTYCH_FOCUS_KEY] = focus


def render_direction_switch() -> None:
    """Render the A/B segmented switch for the top bar."""
    direction = get_direction()
    pair = st.columns([1, 1])
    with pair[0]:
        if st.button(
            "A",
            key="_dpsim_dir_a",
            type="primary" if direction == "a" else "secondary",
            use_container_width=True,
            help="Direction A — Pipeline-as-spine",
        ):
            set_direction("a")
            st.rerun()
    with pair[1]:
        if st.button(
            "B",
            key="_dpsim_dir_b",
            type="primary" if direction == "b" else "secondary",
            use_container_width=True,
            help="Direction B — Triptych workbench",
        ):
            set_direction("b")
            st.rerun()


def _summary_chip(k: str, v: str, *, warn: bool = False) -> str:
    """Render one summary key:value chip for a collapsed column."""
    color = "var(--dps-amber-500)" if warn else "var(--dps-text-muted)"
    return (
        '<div style="display:flex;align-items:center;'
        'justify-content:space-between;gap:8px;padding:4px 0;'
        'border-bottom:1px solid var(--dps-border);">'
        f'<span class="dps-mono" style="font-size:10.5px;'
        f'color:var(--dps-text-dim);text-transform:uppercase;'
        f'letter-spacing:0.06em;">{k}</span>'
        f'<span class="dps-mono" style="font-size:11.5px;color:{color};'
        f'font-variant-numeric:tabular-nums;">{v}</span>'
        '</div>'
    )


def _column_card(
    *,
    column_id: TriptychFocus,
    title: str,
    subtitle: str,
    evidence: ModelEvidenceTier | str,
    summary: list[tuple[str, str, bool]],
    focused: bool,
    expanded_renderer: Callable[[], None] | None = None,
) -> None:
    """Render one of the three triptych columns.

    Focused: expanded — header + full editor body (caller-provided).
    Unfocused: collapsed — header + 6 summary chips + click-to-focus button.
    """
    bg = "var(--dps-surface)" if focused else "var(--dps-surface-2)"
    border = (
        "var(--dps-accent)" if focused else "var(--dps-border)"
    )
    badge_html = chrome.evidence_badge(evidence, compact=True)
    st.html(
        f'<div style="background:{bg};border:1px solid {border};'
        f'border-radius:4px;padding:12px 14px;height:100%;'
        f'display:flex;flex-direction:column;gap:8px;">'
        f'<div style="display:flex;align-items:flex-start;'
        f'justify-content:space-between;gap:8px;">'
        f'<div>{chrome.eyebrow(subtitle, accent=focused)}'
        f'<div style="font-size:14px;font-weight:600;'
        f'color:var(--dps-text);margin-top:2px;">{title}</div></div>'
        f'{badge_html}</div></div>'
    )
    if focused:
        if expanded_renderer is not None:
            expanded_renderer()
    else:
        # Summary chips.
        chips_html = "".join(_summary_chip(k, v, warn=warn) for k, v, warn in summary)
        st.html(
            '<div style="display:flex;flex-direction:column;gap:0;'
            'padding:4px 0;">' + chips_html + '</div>'
        )
        if st.button(
            f"Open {title}",
            key=f"_dpsim_triptych_focus_{column_id}",
            use_container_width=True,
        ):
            set_triptych_focus(column_id)
            st.rerun()


def _deep_get(obj: object, *path: str, default: object = None) -> object:
    """Best-effort attribute walk; returns ``default`` if any step is None."""
    cur: object = obj
    for step in path:
        if cur is None:
            return default
        cur = getattr(cur, step, None)
    return cur if cur is not None else default


def _summary_for(stage: TriptychFocus) -> list[tuple[str, str, bool]]:
    """Build the collapsed-column summary chips from session state.

    Audit fix (v0.4.9 F-2): the previous implementation walked imagined
    paths like ``recipe.m1.formulation.agarose_pct``. The real
    ``ProcessRecipe`` (see ``dpsim.core.process_recipe``) has a
    process-step shape: ``target`` / ``material_batch`` / ``equipment`` /
    ``steps``. This rewrite uses the actual shape so chips populate
    with real values.
    """
    from dpsim.core.process_recipe import LifecycleStage
    from dpsim.visualization.ui_recipe import ensure_process_recipe_state

    lifecycle_result = st.session_state.get("lifecycle_result")
    try:
        recipe = ensure_process_recipe_state(st.session_state)  # type: ignore[arg-type]
    except Exception:  # pragma: no cover — defensive
        recipe = None

    def _q(quantity: object, *, fmt: str = ".3g") -> str:
        """Format a Quantity-like object as ``value unit``."""
        if quantity is None:
            return "—"
        value = getattr(quantity, "value", None)
        unit = getattr(quantity, "unit", "") or ""
        if value is None:
            return str(quantity)
        if isinstance(value, (int, float)):
            return f"{value:{fmt}} {unit}".strip()
        return f"{value} {unit}".strip()

    def _stage_steps(stage_id: "LifecycleStage") -> list[Any]:
        if recipe is None or not hasattr(recipe, "steps_for_stage"):
            return []
        try:
            return list(recipe.steps_for_stage(stage_id) or [])
        except Exception:  # pragma: no cover — defensive
            return []

    target = getattr(recipe, "target", None)
    material_batch = getattr(recipe, "material_batch", None)
    equipment = getattr(recipe, "equipment", None)

    if stage == "m1":
        family_raw = getattr(material_batch, "polymer_family", "—") if material_batch else "—"
        # Family is stored as a string on the recipe (e.g. "agarose_chitosan");
        # surface uppercased + en-dashed for readability.
        family = str(family_raw or "—").replace("_", " ").upper()
        polymer_lot = getattr(material_batch, "polymer_lot", "unassigned") if material_batch else "unassigned"
        n_steps = len(_stage_steps(LifecycleStage.M1_FABRICATION))
        # Predicted d50 from the M1 result if a run has executed; else
        # fall back to the target d50 from the recipe.
        m1 = getattr(lifecycle_result, "m1_result", None)
        d50_predicted = (
            _deep_get(m1, "bead_size_distribution", "d50_um")
            or _deep_get(m1, "d50")
            or _deep_get(m1, "diagnostics", "d50_um")
        )
        target_d50 = getattr(target, "bead_d50", None) if target else None
        target_modulus = getattr(target, "min_modulus", None) if target else None
        return [
            ("family", family, family == "—"),
            ("polymer lot", str(polymer_lot or "—"),
             polymer_lot in (None, "unassigned", "")),
            ("steps", f"{n_steps}", n_steps == 0),
            ("target d50", _q(target_d50), target_d50 is None),
            ("min modulus", _q(target_modulus), target_modulus is None),
            (
                "predicted d50",
                f"{d50_predicted:.1f} µm" if isinstance(d50_predicted, (int, float)) else "—",
                d50_predicted is None,
            ),
        ]
    if stage == "m2":
        ligand = getattr(target, "target_ligand", "—") if target else "—"
        analyte = getattr(target, "target_analyte", "—") if target else "—"
        ligand_lot = getattr(material_batch, "ligand_lot", "unassigned") if material_batch else "unassigned"
        m2_steps = _stage_steps(LifecycleStage.M2_FUNCTIONALIZATION)
        n_steps = len(m2_steps)
        # Pull the chemistry kinds from the M2 steps (e.g. "couple_ligand",
        # "quench") so the chip surfaces what's actually in the recipe.
        kinds = []
        for s in m2_steps:
            k = getattr(s, "kind", None)
            kinds.append(getattr(k, "value", str(k)))
        kinds_str = ", ".join(kinds[:3]) if kinds else "—"
        m2 = getattr(lifecycle_result, "m2_microsphere", None)
        n_caveats = len(getattr(m2, "caveats", []) or []) if m2 is not None else 0
        realised_density = (
            _deep_get(m2, "ligand_density_mg_mL")
            or _deep_get(m2, "diagnostics", "ligand_density_mg_mL")
        )
        return [
            ("ligand", str(ligand or "—"), ligand in (None, "—")),
            ("analyte", str(analyte or "—"), analyte in (None, "—")),
            ("ligand lot", str(ligand_lot or "—"),
             ligand_lot in (None, "unassigned", "")),
            ("steps", f"{n_steps}", n_steps == 0),
            ("chemistries", kinds_str, kinds_str == "—"),
            (
                "ligand density",
                f"{realised_density:.2g} mg/mL"
                if isinstance(realised_density, (int, float))
                else "—",
                False,
            ),
            ("caveats", str(n_caveats), n_caveats > 0),
        ]
    # m3
    column_id = getattr(equipment, "column_id", "—") if equipment else "—"
    detector = getattr(equipment, "detector", "—") if equipment else "—"
    pump_limit = getattr(equipment, "pump_pressure_limit", None) if equipment else None
    max_dp = getattr(target, "max_pressure_drop", None) if target else None
    m3_steps = _stage_steps(LifecycleStage.M3_PERFORMANCE)
    n_m3_steps = len(m3_steps)
    m3_kinds = []
    for s in m3_steps:
        k = getattr(s, "kind", None)
        m3_kinds.append(getattr(k, "value", str(k)))
    m3_kinds_str = ", ".join(m3_kinds[:4]) if m3_kinds else "—"
    m3 = getattr(lifecycle_result, "m3_method", None)
    dbc10 = (
        _deep_get(m3, "dbc10")
        or _deep_get(m3, "dynamic_binding_capacity_10pct")
        or _deep_get(m3, "diagnostics", "DBC10_mg_mL")
    )
    return [
        ("column", str(column_id or "—"), column_id in (None, "—")),
        ("detector", str(detector or "—"), False),
        ("steps", f"{n_m3_steps}", n_m3_steps == 0),
        ("operations", m3_kinds_str, m3_kinds_str == "—"),
        ("max ΔP target", _q(max_dp), max_dp is None),
        ("pump limit", _q(pump_limit), pump_limit is None),
        ("DBC₁₀", f"{dbc10:.1f} mg/mL" if isinstance(dbc10, (int, float)) else "—",
         dbc10 is None),
    ]


def render_triptych(
    *,
    m1_renderer: Callable[[], None],
    m2_renderer: Callable[[], None],
    m3_renderer: Callable[[], None],
    evidence_stages: list[StageEvidence],
    dock_renderer: Callable[[], None] | None = None,
) -> None:
    """Render the Direction-B triptych.

    Args:
        m1_renderer: Callable that renders the M1 editor body when M1
            is the focused column.
        m2_renderer: Same for M2.
        m3_renderer: Same for M3.
        evidence_stages: Per-stage evidence summaries; used to colour
            each column's badge.
        dock_renderer: Optional bottom-dock callable (run controls,
            breakthrough preview, evidence ladder).
    """
    focus = get_triptych_focus()
    # Column-flex ratios depend on which is focused; the focused column
    # expands to ~2.4× the collapsed siblings (matches direction-b.jsx).
    if focus == "m1":
        ratios = [2.4, 1.0, 1.0]
    elif focus == "m2":
        ratios = [1.0, 2.4, 1.0]
    else:
        ratios = [1.0, 1.0, 2.4]
    # Anchor marker so app.py's CSS can scope the column-width
    # transition to this triptych and not affect every st.columns() in
    # the app. Renders as a zero-height invisible div.
    st.html('<div class="dps-triptych-marker" style="height:0;"></div>')
    cols = st.columns(ratios)

    # Map stage_id → tier for quick lookup.
    tier_map = {s.stage_id: s.tier for s in evidence_stages}
    m1_tier = tier_map.get("m1", ModelEvidenceTier.SEMI_QUANTITATIVE.value)
    m2_tier = tier_map.get("m2", ModelEvidenceTier.SEMI_QUANTITATIVE.value)
    m3_tier = tier_map.get("m3", ModelEvidenceTier.SEMI_QUANTITATIVE.value)

    with cols[0]:
        _column_card(
            column_id="m1",
            title="Fabrication",
            subtitle="M1 · 21 polymer families",
            evidence=m1_tier,
            summary=_summary_for("m1"),
            focused=focus == "m1",
            expanded_renderer=m1_renderer,
        )
    with cols[1]:
        _column_card(
            column_id="m2",
            title="Functionalisation",
            subtitle="M2 · 96 reagents · 17 buckets",
            evidence=m2_tier,
            summary=_summary_for("m2"),
            focused=focus == "m2",
            expanded_renderer=m2_renderer,
        )
    with cols[2]:
        _column_card(
            column_id="m3",
            title="Column method",
            subtitle="M3 · LRM · BDF · MC",
            evidence=m3_tier,
            summary=_summary_for("m3"),
            focused=focus == "m3",
            expanded_renderer=m3_renderer,
        )

    if dock_renderer is not None:
        # Triptych dock — horizontal 3-pane fixed at the bottom of the
        # workbench per the Direction-B reference. Pane 1: pending
        # edits. Pane 2: lifecycle-min evidence stacked bar. Pane 3:
        # last-run KPIs + ▶ Run lifecycle CTA.
        st.html('<div class="dps-divider" style="margin:16px 0 8px 0;"></div>')
        render_triptych_dock(
            evidence_stages=evidence_stages,
            dock_renderer=dock_renderer,
        )


def _render_dock_pending_edits() -> None:
    """Dock pane 1: pending recipe edits (compact)."""
    from dpsim.visualization.diff.render import render_diff_panel
    from dpsim.visualization.ui_recipe import ensure_process_recipe_state

    try:
        recipe = ensure_process_recipe_state(st.session_state)
    except Exception:  # pragma: no cover — defensive
        st.html(
            chrome.eyebrow("Pending edits")
            + '<div class="dps-mono" style="font-size:11px;'
            'color:var(--dps-text-dim);">'
            "no recipe in session</div>"
        )
        return
    baseline_name = st.session_state.get(
        "_dpsim_diff_baseline_name", "last_run"
    )
    render_diff_panel(
        current_recipe=recipe,
        baseline_name=baseline_name,
    )


def _render_dock_evidence_bar(evidence_stages: list[StageEvidence]) -> None:
    """Dock pane 2: lifecycle-min evidence as a horizontal stacked bar.

    Three equal-width segments (M1 / M2 / M3) tinted by each stage's
    own tier; below them, a "Lifecycle min" label + the aggregated
    badge. Matches the bar visualization shown along the dock in the
    Direction-B reference screenshots.
    """
    tier_map = {s.stage_id: s.tier for s in evidence_stages}
    seg_html = []
    for sid, label in (("m1", "M1"), ("m2", "M2"), ("m3", "M3")):
        tier = tier_map.get(sid, ModelEvidenceTier.UNSUPPORTED.value)
        color = _DOCK_TIER_COLOR.get(tier, "var(--dps-text-dim)")
        short = _DOCK_TIER_SHORT.get(tier, tier.upper()[:4])
        seg_html.append(
            '<div style="flex:1;padding:6px 8px;'
            f"background:color-mix(in oklab, {color} 22%, transparent);"
            f"border:1px solid {color};border-radius:3px;"
            'display:flex;align-items:center;'
            'justify-content:space-between;gap:6px;">'
            f'<span class="dps-mono" style="font-size:10.5px;'
            f'color:var(--dps-text-muted);font-weight:600;">{label}</span>'
            f'<span class="dps-mono" style="font-size:10.5px;'
            f'color:{color};font-weight:600;">{short}</span></div>'
        )
    min_tier = aggregate_min_tier(evidence_stages or [])
    min_badge = chrome.evidence_badge(min_tier)
    st.html(
        chrome.eyebrow("Evidence · lifecycle min", accent=True)
        + '<div style="display:flex;gap:4px;margin-top:6px;">'
        + "".join(seg_html)
        + '</div>'
        + '<div style="display:flex;align-items:center;'
        'justify-content:space-between;gap:8px;margin-top:8px;">'
        '<span class="dps-mono" style="font-size:11px;'
        'color:var(--dps-text-muted);text-transform:uppercase;'
        'letter-spacing:0.06em;">Lifecycle min</span>'
        f"{min_badge}</div>"
    )


def _render_dock_run_pane(dock_renderer: Callable[[], None]) -> None:
    """Dock pane 3: last-run KPI strip + Run lifecycle CTA.

    Reuses the rail's KPI grid + run-controls rendering by invoking
    ``dock_renderer`` (which the caller wires to ``render_run_rail``).
    The result here visually compresses the rail into a horizontal
    pane the dock width can accommodate.
    """
    st.html(chrome.eyebrow("Last run · KPIs · run controls", accent=True))
    dock_renderer()


def render_triptych_dock(
    *,
    evidence_stages: list[StageEvidence],
    dock_renderer: Callable[[], None],
) -> None:
    """Render the 3-pane horizontal dock at the foot of the triptych.

    Composition: [pending edits] · [evidence-min bar] · [last-run + CTA]

    Args:
        evidence_stages: Per-stage evidence summaries used by pane 2.
        dock_renderer: The rail callable used by pane 3 to render
            last-run KPIs + run controls.
    """
    cols = st.columns([1.2, 1.0, 1.6])
    with cols[0]:
        _render_dock_pending_edits()
    with cols[1]:
        _render_dock_evidence_bar(evidence_stages)
    with cols[2]:
        _render_dock_run_pane(dock_renderer)


__all__ = [
    "DIRECTION_KEY",
    "ShellDirection",
    "TRIPTYCH_FOCUS_KEY",
    "TriptychFocus",
    "get_direction",
    "get_triptych_focus",
    "render_direction_switch",
    "render_triptych",
    "render_triptych_dock",
    "set_direction",
    "set_triptych_focus",
]
