"""Evidence-tier aggregation and rendering."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Final

import streamlit as st

from dpsim.datatypes import ModelEvidenceTier
from dpsim.visualization.design import chrome

# Strongest-to-weakest order. Identical to ``ModelEvidenceTier``'s
# definition order — duplicated here only so the rollup can compute a
# min without importing the orchestrator's RunReport for trivial cases.
_ORDER: Final[list[str]] = [t.value for t in ModelEvidenceTier]


@dataclass(frozen=True)
class StageEvidence:
    """One stage's evidence summary.

    Attributes:
        stage_id: Stable id (e.g. ``"m1"``).
        label: Display label (e.g. ``"M1 — Fabrication"``).
        tier: This stage's worst tier across its own models. Use the
            string value (``ModelEvidenceTier.X.value``) per CLAUDE.md
            enum-comparison rules.
        note: Optional one-line note on what's driving the tier (e.g.
            ``"Pectin DE outside calibration range"``).
    """

    stage_id: str
    label: str
    tier: str
    note: str = ""


def aggregate_min_tier(stages: Iterable[StageEvidence]) -> str:
    """Compute the lifecycle-min tier across stages.

    Args:
        stages: Iterable of ``StageEvidence``. May be empty (returns
            ``unsupported``).

    Returns:
        The ``.value`` of the weakest tier present.
    """
    items = list(stages)
    if not items:
        return ModelEvidenceTier.UNSUPPORTED.value
    worst_idx = 0
    for s in items:
        try:
            idx = _ORDER.index(str(s.tier))
        except ValueError:
            idx = _ORDER.index(ModelEvidenceTier.UNSUPPORTED.value)
        if idx > worst_idx:
            worst_idx = idx
    return _ORDER[worst_idx]


def render_top_bar_badge(stages: Iterable[StageEvidence]) -> str:
    """Render the lifecycle-min evidence badge for the top bar.

    Audit fix (v0.4.9 F-4): when ``stages`` is empty (no run has
    executed yet), render an honest "no run yet" state instead of
    the previous behaviour where ``aggregate_min_tier([])`` returned
    ``UNSUPPORTED`` and the top bar showed a red UNS badge as if a
    run had failed.

    Returns:
        HTML string ready to embed via ``st.html``.
    """
    items = list(stages)
    if not items:
        return (
            '<div style="display:inline-flex;align-items:center;gap:6px;">'
            f'{chrome.eyebrow("Lifecycle evidence")}'
            '<span class="dps-mono" style="font-size:11px;'
            'color:var(--dps-text-dim);font-weight:500;'
            'letter-spacing:0.04em;">— no run yet</span></div>'
        )
    min_tier = aggregate_min_tier(items)
    badge = chrome.evidence_badge(min_tier)
    return (
        '<div style="display:inline-flex;align-items:center;gap:6px;">'
        f'{chrome.eyebrow("Lifecycle evidence")}{badge}</div>'
    )


def render_evidence_summary(stages: Iterable[StageEvidence]) -> None:
    """Render the lifecycle-min headline + per-stage breakdown.

    Outputs into the current Streamlit slot. Composition:
        [eyebrow + lifecycle-min badge]
        [for each stage: stage label · per-stage badge · optional note]

    Per SA Q3: this is the architect's option-3 layout (lifecycle
    aggregated as headline; per-stage as diagnostic).
    """
    items = list(stages)
    min_tier = aggregate_min_tier(items)
    headline = chrome.evidence_badge(min_tier)
    rows = "".join(_format_stage_row(s, min_tier) for s in items)
    st.html(
        chrome.eyebrow("Evidence rollup", accent=True)
        + f'<div style="margin-top:6px;display:flex;flex-direction:column;'
        f'gap:6px;">'
        f'<div style="display:flex;align-items:center;gap:8px;'
        f'padding:6px 8px;background:var(--dps-surface-2);'
        f'border:1px solid var(--dps-border);border-radius:4px;">'
        f'<span style="font-size:11px;color:var(--dps-text-muted);">'
        f'Lifecycle min</span>{headline}</div>'
        f'<div style="display:flex;flex-direction:column;gap:3px;'
        f'padding:0 4px;">{rows}</div>'
        f'</div>'
    )


def _format_stage_row(stage: StageEvidence, lifecycle_min: str) -> str:
    """One stage row in the per-stage breakdown.

    The row dims slightly when the stage's tier is *better* than the
    lifecycle min (i.e. it is not the bottleneck) so the eye lands on
    the rate-limiting stage(s).
    """
    is_bottleneck = stage.tier == lifecycle_min
    badge = chrome.evidence_badge(stage.tier, compact=True)
    label_color = (
        "var(--dps-text)" if is_bottleneck else "var(--dps-text-muted)"
    )
    note_html = (
        f'<span style="font-size:10.5px;color:var(--dps-text-dim);'
        f'font-family:var(--dps-font-mono);">{stage.note}</span>'
        if stage.note
        else ""
    )
    return (
        f'<div style="display:flex;align-items:center;gap:6px;'
        f'min-height:18px;">'
        f'<span style="font-size:11.5px;color:{label_color};'
        f'min-width:130px;">{stage.label}</span>'
        f'{badge}{note_html}</div>'
    )


def stages_from_run_report(run_report: object) -> list[StageEvidence]:
    """Convenience: build per-stage list from a ``RunReport``.

    Args:
        run_report: A ``RunReport`` instance with a ``model_graph``
            attribute (list of ``ModelManifest``). Each manifest must
            have ``stage`` and ``evidence_tier`` attributes.

    Returns:
        Deduplicated list of ``StageEvidence``, one per stage,
        carrying that stage's worst tier.
    """
    by_stage: dict[str, StageEvidence] = {}
    graph = getattr(run_report, "model_graph", []) or []
    for manifest in graph:
        stage = getattr(manifest, "stage", None)
        if stage is None:
            continue
        stage_id = getattr(stage, "value", stage)
        tier = getattr(manifest, "evidence_tier", None)
        tier_value = getattr(tier, "value", tier)
        existing = by_stage.get(str(stage_id))
        # Take the worst tier seen so far for this stage.
        if existing is None:
            by_stage[str(stage_id)] = StageEvidence(
                stage_id=str(stage_id),
                label=str(stage_id),
                tier=str(tier_value or ModelEvidenceTier.UNSUPPORTED.value),
            )
        else:
            curr = existing.tier
            try:
                curr_idx = _ORDER.index(curr)
                new_idx = _ORDER.index(str(tier_value))
            except ValueError:
                continue
            if new_idx > curr_idx:
                by_stage[str(stage_id)] = StageEvidence(
                    stage_id=existing.stage_id,
                    label=existing.label,
                    tier=str(tier_value),
                )
    return list(by_stage.values())
