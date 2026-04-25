"""Direction-A stage 05 / 06 / 07 panel chrome.

Wraps the existing ``ui_workflow.render_lifecycle_run_panel`` /
``render_lifecycle_results_panel`` / ``render_calibration_status_panel``
with the headline visuals shown in the Direction-A reference
screenshots:

- **Stage 05 — Run lifecycle**: pre-flight checklist (recipe valid +
  CAL chip, estimated runtime, memory budget) above the existing run
  controls.
- **Stage 06 — Validation**: evidence ladder (M1 → M2 → M3 capping
  visualization) above the existing 8-tab detail stack.
- **Stage 07 — Calibration**: "Ingest wet-lab measurements" headline
  with an Upload campaign.yaml primary CTA above the existing read-only
  rows.

These wrappers preserve all existing detail surfaces — they only add
the Direction-A headline that was missing.
"""

from __future__ import annotations

import html as _html
from collections.abc import Mapping, MutableMapping
from typing import Any

import streamlit as st

from dpsim.core.process_recipe import ProcessRecipe
from dpsim.datatypes import ModelEvidenceTier
from dpsim.visualization.design import chrome
from dpsim.visualization.ui_workflow import (
    evidence_ladder_rows,
    render_calibration_status_panel,
    render_lifecycle_results_panel,
    render_lifecycle_run_panel,
)


# ─── Stage 05 — Run lifecycle ─────────────────────────────────────────


def _estimate_runtime_seconds(recipe: ProcessRecipe) -> int:
    """Cheap estimator for the rail's pre-flight "Estimated runtime" row.

    Uses the per-stage step counts as a coarse linear proxy. Real
    timings vary by 10× depending on solver mode; this is a UI hint, not
    a guarantee.
    """
    base = 4  # M1 PBE + L2/L3 + M2 mass-action + M3 LRM baseline.
    try:
        from dpsim.core.process_recipe import LifecycleStage

        for stage in (
            LifecycleStage.M1_FABRICATION,
            LifecycleStage.M2_FUNCTIONALIZATION,
            LifecycleStage.M3_PERFORMANCE,
        ):
            base += 2 * len(recipe.steps_for_stage(stage) or [])
    except Exception:  # pragma: no cover — defensive
        pass
    return base


def _estimate_memory_mb(recipe: ProcessRecipe) -> int:
    """Cheap estimator for the rail's pre-flight "Memory budget" row.

    Driven by the M1 grid size (the dominant memory term — phi_field is
    grid×grid×float64). Falls back to a conservative 340 MB when the
    grid size is unknown.
    """
    try:
        # The L2 grid size lives on SimulationParameters.solver, not on
        # the recipe. Use a conservative recipe-derived estimate based
        # on stage breadth instead.
        from dpsim.core.process_recipe import LifecycleStage

        n_total = sum(
            len(recipe.steps_for_stage(s) or [])
            for s in (
                LifecycleStage.M1_FABRICATION,
                LifecycleStage.M2_FUNCTIONALIZATION,
                LifecycleStage.M3_PERFORMANCE,
            )
        )
        # Rough: 200 MB base + 30 MB per step (DSD propagation + traces).
        return 200 + 30 * n_total
    except Exception:  # pragma: no cover — defensive
        return 340


def _validate_recipe_for_preflight(recipe: ProcessRecipe) -> tuple[bool, str]:
    """Run a cheap recipe-level validity probe for the pre-flight row.

    Returns:
        ``(is_valid, message)``. Truthy when the recipe is structurally
        complete enough to attempt a run; the message is the short
        right-hand-side label shown next to the row.
    """
    target = getattr(recipe, "target", None)
    material_batch = getattr(recipe, "material_batch", None)
    if target is None:
        return False, "no target profile"
    if material_batch is None:
        return False, "no material batch"
    family = getattr(material_batch, "polymer_family", None)
    if not family:
        return False, "polymer family unset"
    return True, "all checks pass"


def _format_runtime(seconds: int) -> str:
    """Human-readable runtime: '~14 s' / '~2 min' / '~1.2 h'."""
    if seconds < 90:
        return f"~{seconds} s"
    minutes = seconds / 60.0
    if minutes < 90:
        return f"~{minutes:.0f} min"
    hours = minutes / 60.0
    return f"~{hours:.1f} h"


def _preflight_row(label: str, *, value: str, badge_html: str = "") -> str:
    """Render one pre-flight row: label · optional badge · right-aligned value.

    Returns HTML; emit via ``st.html``.
    """
    return (
        '<div style="display:flex;align-items:center;'
        'justify-content:space-between;gap:12px;'
        'padding:8px 12px;background:var(--dps-surface);'
        'border:1px solid var(--dps-border);border-radius:4px;'
        'margin-bottom:6px;">'
        '<div style="display:flex;align-items:center;gap:8px;">'
        f'<span style="font-size:13px;color:var(--dps-text);">'
        f"{_html.escape(label)}</span>{badge_html}</div>"
        '<span class="dps-mono" style="font-size:13px;'
        'color:var(--dps-text-muted);font-variant-numeric:tabular-nums;">'
        f"{_html.escape(value)}</span></div>"
    )


def render_run_lifecycle_stage(
    recipe: ProcessRecipe,
    session_state: MutableMapping[str, Any],
) -> None:
    """Stage 05 panel — Direction-A pre-flight headline + existing run UI.

    Renders the pre-flight checklist (Recipe valid · Estimated runtime ·
    Memory budget) above the v0.4.8 threaded-orchestrator run controls.
    """
    st.html(chrome.eyebrow("Stage 05 · Run", accent=True))
    st.html(
        '<h1 style="margin:0 0 4px 0;">Run lifecycle simulation</h1>'
    )
    st.html(chrome.eyebrow("Pre-flight"))

    is_valid, valid_msg = _validate_recipe_for_preflight(recipe)
    runtime_s = _estimate_runtime_seconds(recipe)
    memory_mb = _estimate_memory_mb(recipe)

    valid_badge = chrome.evidence_badge(
        ModelEvidenceTier.CALIBRATED_LOCAL.value if is_valid else
        ModelEvidenceTier.UNSUPPORTED.value,
        compact=True,
    )

    st.html(
        '<div style="margin-top:6px;">'
        + _preflight_row(
            "Recipe valid",
            value=valid_msg,
            badge_html=valid_badge,
        )
        + _preflight_row(
            "Estimated runtime",
            value=_format_runtime(runtime_s),
        )
        + _preflight_row(
            "Memory budget",
            value=f"~{memory_mb} MB",
        )
        + "</div>"
    )

    # Existing run controls (threaded orchestrator + 3 option checkboxes
    # + Run button + summary dataframe). Wrapped in an expander so the
    # pre-flight is the first thing the eye lands on, but the original
    # control surface remains available.
    st.html(chrome.eyebrow("Run controls"))
    render_lifecycle_run_panel(recipe, session_state)


# ─── Stage 06 — Validation: Evidence ladder ───────────────────────────


_LADDER_STAGES: tuple[tuple[str, str], ...] = (
    ("m1", "M1 — fabrication"),
    ("m2", "M2 — functionalisation"),
    ("m3", "M3 — column method"),
)
_TIER_RANK: dict[str, int] = {
    ModelEvidenceTier.VALIDATED_QUANTITATIVE.value: 0,
    ModelEvidenceTier.CALIBRATED_LOCAL.value: 1,
    ModelEvidenceTier.SEMI_QUANTITATIVE.value: 2,
    ModelEvidenceTier.QUALITATIVE_TREND.value: 3,
    ModelEvidenceTier.UNSUPPORTED.value: 4,
}
_TIER_SHORT: dict[str, str] = {
    ModelEvidenceTier.VALIDATED_QUANTITATIVE.value: "VAL",
    ModelEvidenceTier.CALIBRATED_LOCAL.value: "CAL",
    ModelEvidenceTier.SEMI_QUANTITATIVE.value: "SEMI",
    ModelEvidenceTier.QUALITATIVE_TREND.value: "QUAL",
    ModelEvidenceTier.UNSUPPORTED.value: "UNS",
}


def _per_stage_tiers(
    recipe: ProcessRecipe,
    session_state: Mapping[str, Any],
) -> dict[str, str]:
    """Aggregate per-stage worst evidence tiers from the run report.

    Returns a dict ``{m1, m2, m3}`` → ``ModelEvidenceTier.value``.
    Stages without an evaluated model fall back to UNSUPPORTED.
    """
    out = {sid: ModelEvidenceTier.UNSUPPORTED.value for sid, _ in _LADDER_STAGES}
    rows = evidence_ladder_rows(
        session_state.get("lifecycle_result"),
        session_state=session_state,
    )
    for row in rows:
        # The dataframe uses arbitrary column names; probe a few
        # common candidates so the ladder works regardless of which
        # version of evidence_ladder_rows produced the rows.
        stage_id = (
            row.get("stage")
            or row.get("module")
            or row.get("Stage")
            or ""
        )
        tier = (
            row.get("evidence_tier")
            or row.get("tier")
            or row.get("Evidence")
            or ""
        )
        sid_lower = str(stage_id).lower()
        for canonical, _label in _LADDER_STAGES:
            if canonical in sid_lower:
                tier_value = str(tier).strip().lower().replace(" ", "_").replace("-", "_")
                if tier_value in _TIER_RANK and (
                    _TIER_RANK[tier_value] > _TIER_RANK.get(out[canonical], 4)
                ):
                    out[canonical] = tier_value
                break
    return out


def _ladder_row(
    *,
    stage_label: str,
    own_tier: str,
    capped_tier: str,
    is_capped: bool,
) -> str:
    """One evidence-ladder row.

    Layout: [stage label + own tier badge]  · · · · ·  [final capped tier]
    """
    own_badge = chrome.evidence_badge(own_tier, compact=True)
    capped_short = _TIER_SHORT.get(capped_tier, capped_tier.upper()[:4])
    capped_color = (
        "var(--dps-amber-500)" if is_capped else "var(--dps-text-muted)"
    )
    capped_html = (
        f'<span class="dps-mono" style="font-size:12px;'
        f"font-weight:600;color:{capped_color};\">"
        f"{capped_short}{' ↓ (capped)' if is_capped else ''}</span>"
    )
    return (
        '<div style="display:flex;align-items:center;'
        'justify-content:space-between;gap:12px;'
        'padding:10px 14px;background:var(--dps-surface);'
        'border:1px solid var(--dps-border);border-radius:4px;'
        'margin-bottom:6px;">'
        '<div style="display:flex;align-items:center;gap:10px;">'
        f'<span style="font-size:13px;color:var(--dps-text);">'
        f"{_html.escape(stage_label)}</span>{own_badge}</div>"
        f"{capped_html}</div>"
    )


def render_validation_stage(
    recipe: ProcessRecipe,
    session_state: Mapping[str, Any],
) -> None:
    """Stage 06 panel — Direction-A evidence-ladder headline + existing
    8-tab detail stack.
    """
    st.html(chrome.eyebrow("Stage 06 · Validation", accent=True))
    st.html('<h1 style="margin:0 0 4px 0;">Validation &amp; evidence</h1>')
    st.html(chrome.eyebrow("Evidence ladder · M1 → M2 → M3"))
    st.html(
        '<div class="dps-mono" style="font-size:11.5px;'
        'color:var(--dps-text-muted);margin:4px 0 12px;">'
        "M3 cannot claim stronger evidence than its M2 inputs; "
        "M2 cannot claim stronger than M1.</div>"
    )

    per_stage = _per_stage_tiers(recipe, session_state)
    # Walk the ladder applying the cap rule: each stage's effective
    # tier is the worst (highest rank) of its own tier and the previous
    # stage's effective tier.
    rolling = ModelEvidenceTier.VALIDATED_QUANTITATIVE.value
    capped: dict[str, tuple[str, bool]] = {}
    for sid, _label in _LADDER_STAGES:
        own = per_stage[sid]
        own_rank = _TIER_RANK.get(own, 4)
        rolling_rank = _TIER_RANK.get(rolling, 4)
        effective = own if own_rank >= rolling_rank else rolling
        is_capped = (effective != own) and (sid != "m1")
        capped[sid] = (effective, is_capped)
        rolling = effective

    rows_html = "".join(
        _ladder_row(
            stage_label=label,
            own_tier=per_stage[sid],
            capped_tier=capped[sid][0],
            is_capped=capped[sid][1],
        )
        for sid, label in _LADDER_STAGES
    )
    # Lifecycle-min row at the bottom.
    min_tier = max(
        (per_stage[sid] for sid, _ in _LADDER_STAGES),
        key=lambda t: _TIER_RANK.get(t, 4),
    )
    rows_html += (
        '<div style="display:flex;align-items:center;'
        'justify-content:space-between;gap:12px;'
        'padding:10px 14px;background:var(--dps-surface-2);'
        'border:1px solid var(--dps-border-strong);border-radius:4px;'
        'margin-top:8px;">'
        '<span style="font-size:13px;font-weight:600;color:var(--dps-text);">'
        "Lifecycle min tier</span>"
        + chrome.evidence_badge(min_tier, compact=True)
        + "</div>"
    )
    st.html(rows_html)

    # Existing 8-tab detail stack inside an expander so the ladder is
    # the headline.
    with st.expander("Open detail tabs (run summary · validation report · "
                     "diagnostics · visuals · SOP · calibration · history)",
                     expanded=False):
        render_lifecycle_results_panel(recipe, session_state)


# ─── Stage 07 — Calibration: Upload campaign ──────────────────────────


def render_calibration_stage(
    recipe: ProcessRecipe,  # noqa: ARG001 — kept for API symmetry
    session_state: MutableMapping[str, Any],
) -> None:
    """Stage 07 panel — Direction-A "Ingest wet-lab measurements" CTA +
    existing read-only calibration table.

    Also fixes the latent app.py call-site bug where the legacy
    ``render_calibration_status_panel(recipe, session_state)`` invocation
    passed two args to a one-arg function.
    """
    st.html(chrome.eyebrow("Stage 07 · Calibration", accent=True))
    st.html(
        '<h1 style="margin:0 0 4px 0;">Calibration store · wet-lab loop</h1>'
    )
    st.html(chrome.eyebrow("Ingest wet-lab measurements"))
    st.html(
        '<div style="font-size:13px;color:var(--dps-text-muted);'
        'line-height:1.55;margin:4px 0 12px;max-width:760px;">'
        "Upload a YAML campaign to override screening defaults. The "
        "simulator will then report calibrated, local evidence for "
        "parameters within the validated domain.</div>"
    )

    upload = st.file_uploader(
        "campaign.yaml",
        type=["yaml", "yml"],
        key="_dpsim_calibration_campaign_upload",
        label_visibility="collapsed",
    )
    if upload is not None:
        try:
            payload = upload.read().decode("utf-8")
            # Stash the raw text in session state; downstream loader
            # can parse it. We don't parse here so this module stays
            # decoupled from the calibration store schema.
            session_state["_dpsim_calibration_campaign_raw"] = payload
            st.success(
                f"Loaded {upload.name} ({len(payload):,} bytes). "
                "Restart the run to apply."
            )
        except Exception as exc:  # pragma: no cover — defensive
            st.error(f"Could not read uploaded file: {exc}")

    # Existing read-only calibration entries (loaded entries dataframe +
    # measured-vs-simulated comparison). Pass only session_state — the
    # underlying function takes one arg. This corrects the latent bug
    # at app.py:416 where two args were passed.
    st.html('<div class="dps-divider" style="margin:16px 0;"></div>')
    render_calibration_status_panel(session_state)


__all__ = [
    "render_calibration_stage",
    "render_run_lifecycle_stage",
    "render_validation_stage",
]
