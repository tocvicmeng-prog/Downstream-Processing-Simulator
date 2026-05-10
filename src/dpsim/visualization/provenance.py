"""Result provenance helpers for the Streamlit UI.

The simulator can expose results from several routes: full lifecycle
runs, direct M3 runs, optimizer candidates, baselines, and wet-lab
imports. This module keeps a compact UI-side provenance record so the
chrome can show source and stale-state without changing scientific
result objects.
"""

from __future__ import annotations

import hashlib
import html
import json
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from typing import Any, Final

from dpsim.visualization.diff.snapshot import snapshot_recipe

PROVENANCE_STATE_KEY: Final[str] = "_dpsim_result_provenance"


@dataclass(frozen=True)
class ResultProvenance:
    """UI provenance for one rendered result object."""

    result_id: str
    source: str
    created_at: str
    recipe_fingerprint: str
    scientific_mode: str
    evidence_tier: str
    stale: bool = False
    stale_reasons: tuple[str, ...] = ()


SOURCE_LABELS: Final[dict[str, str]] = {
    "lifecycle": "Current lifecycle",
    "direct_m3": "Direct M3",
    "optimizer": "Optimizer candidate",
    "wet_lab_import": "Wet-lab import",
    "baseline": "Baseline",
}


def recipe_fingerprint(recipe: Any) -> str:
    """Return a stable short hash for a recipe-like object."""

    snapshot = snapshot_recipe(recipe)
    payload = json.dumps(snapshot, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def build_result_provenance(
    *,
    source: str,
    recipe: Any,
    result: Any | None = None,
    result_id: str = "",
    scientific_mode: str = "",
    evidence_tier: str | None = None,
    created_at: str | None = None,
) -> ResultProvenance:
    """Build a provenance record for a result rendered by the UI."""

    rid = result_id or str(getattr(result, "run_id", "") or "")
    if not rid:
        rid = f"obj:{id(result)}" if result is not None else "manual"
    if evidence_tier is None:
        evidence_tier = _tier_value(
            getattr(result, "weakest_evidence_tier", None)
            or getattr(getattr(result, "model_manifest", None), "evidence_tier", None)
        )
    if not scientific_mode:
        scientific_mode = str(getattr(recipe, "run_mode", "") or "")
    return ResultProvenance(
        result_id=rid,
        source=str(source),
        created_at=created_at or datetime.now(tz=timezone.utc).isoformat(),
        recipe_fingerprint=recipe_fingerprint(recipe),
        scientific_mode=scientific_mode or "unspecified",
        evidence_tier=evidence_tier or "unsupported",
    )


def store_result_provenance(
    store: Any,
    result_key: str,
    provenance: ResultProvenance,
) -> ResultProvenance:
    """Persist provenance by result session-state key."""

    table = dict(store.get(PROVENANCE_STATE_KEY, {}) or {})
    table[str(result_key)] = asdict(provenance) | {
        "stale_reasons": list(provenance.stale_reasons)
    }
    store[PROVENANCE_STATE_KEY] = table
    return provenance


def get_result_provenance(store: Any, result_key: str) -> ResultProvenance | None:
    """Return stored provenance for a result session-state key."""

    raw = (store.get(PROVENANCE_STATE_KEY, {}) or {}).get(str(result_key))
    if raw is None:
        return None
    if isinstance(raw, ResultProvenance):
        return raw
    if not isinstance(raw, dict):
        return None
    try:
        return ResultProvenance(
            result_id=str(raw.get("result_id", "")),
            source=str(raw.get("source", "")),
            created_at=str(raw.get("created_at", "")),
            recipe_fingerprint=str(raw.get("recipe_fingerprint", "")),
            scientific_mode=str(raw.get("scientific_mode", "")),
            evidence_tier=str(raw.get("evidence_tier", "")),
            stale=bool(raw.get("stale", False)),
            stale_reasons=tuple(str(v) for v in raw.get("stale_reasons", ()) or ()),
        )
    except (TypeError, ValueError):
        return None


def with_current_recipe_staleness(
    provenance: ResultProvenance | None,
    current_recipe: Any,
) -> ResultProvenance | None:
    """Mark provenance stale when the live recipe hash differs."""

    if provenance is None:
        return None
    current_hash = recipe_fingerprint(current_recipe)
    if current_hash == provenance.recipe_fingerprint:
        return replace(provenance, stale=False, stale_reasons=())
    reason = (
        "Current recipe differs from the recipe that produced this result "
        f"({provenance.recipe_fingerprint} -> {current_hash})."
    )
    return replace(provenance, stale=True, stale_reasons=(reason,))


def provenance_summary_html(provenance: ResultProvenance | None) -> str:
    """Return compact source/freshness HTML for Streamlit ``st.html``."""

    if provenance is None:
        return (
            '<div class="dps-mono" style="font-size:11px;'
            'color:var(--dps-text-dim);padding-top:6px;">'
            "Result source not recorded yet.</div>"
        )
    label = SOURCE_LABELS.get(provenance.source, provenance.source or "Result")
    stale_chip = _chip(
        "STALE" if provenance.stale else "CURRENT",
        "var(--dps-amber-500)" if provenance.stale else "var(--dps-green-500)",
    )
    source_chip = _chip(label, "var(--dps-accent)")
    tier_chip = _chip(provenance.evidence_tier or "unsupported", "var(--dps-text-muted)")
    mode = html.escape(provenance.scientific_mode or "unspecified")
    fingerprint = html.escape(provenance.recipe_fingerprint)
    reasons = ""
    if provenance.stale_reasons:
        reasons = (
            '<div style="margin-top:4px;color:var(--dps-amber-500);'
            'font-size:10.5px;line-height:1.45;">'
            + "<br>".join(html.escape(r) for r in provenance.stale_reasons)
            + "</div>"
        )
    return (
        '<div style="margin-top:8px;padding:7px 8px;'
        'background:var(--dps-surface-2);border:1px solid var(--dps-border);'
        'border-radius:4px;">'
        '<div style="display:flex;flex-wrap:wrap;gap:5px;align-items:center;">'
        f"{source_chip}{stale_chip}{tier_chip}"
        "</div>"
        '<div class="dps-mono" style="font-size:10.5px;'
        'color:var(--dps-text-dim);padding-top:5px;">'
        f"mode={mode} · recipe={fingerprint}</div>"
        f"{reasons}</div>"
    )


def _tier_value(value: Any) -> str:
    if value is None:
        return "unsupported"
    return str(getattr(value, "value", value))


def _chip(text: str, color: str) -> str:
    return (
        '<span style="display:inline-flex;align-items:center;'
        'padding:1px 7px;border-radius:3px;font-size:10.5px;'
        'font-family:var(--dps-font-mono);font-weight:600;'
        f'color:{color};background:color-mix(in oklab, {color} 12%, transparent);'
        f'border:1px solid color-mix(in oklab, {color} 28%, transparent);">'
        f"{html.escape(text)}</span>"
    )


__all__ = [
    "PROVENANCE_STATE_KEY",
    "ResultProvenance",
    "build_result_provenance",
    "get_result_provenance",
    "provenance_summary_html",
    "recipe_fingerprint",
    "store_result_provenance",
    "with_current_recipe_staleness",
]
