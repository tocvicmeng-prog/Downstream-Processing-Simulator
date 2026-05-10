"""Scientific-mode preflight copy for run-critical UI surfaces."""

from __future__ import annotations

import html
from typing import Any


_MODE_ROWS: dict[str, dict[str, str]] = {
    "empirical": {
        "label": "Empirical Engineering",
        "pathway": "Fast screening correlations with relaxed model warnings.",
        "calibration": "Uses available calibration but does not require full local closure.",
        "rendering": "Uncalibrated outputs should remain intervals, rank bands, or suppressed.",
        "runtime": "short",
        "next_action": "Use for early recipe triage; promote with wet-lab data before fixed claims.",
    },
    "hybrid": {
        "label": "Hybrid Coupled",
        "pathway": "Calibrated empirical transport with mechanistic pressure and lifecycle checks.",
        "calibration": "Balanced default; missing M2/M3 evidence downgrades decision rendering.",
        "rendering": "Decision-grade renderer selects numbers, intervals, or rank bands by tier.",
        "runtime": "medium",
        "next_action": "Use for process-development decisions when calibration coverage is partial.",
    },
    "mechanistic": {
        "label": "Mechanistic Research",
        "pathway": "Physics-first solve path with stricter trust gates and domain checks.",
        "calibration": "Stricter response to missing calibration and valid-domain violations.",
        "rendering": "Weak evidence is more likely to be suppressed or shown as advisory only.",
        "runtime": "long",
        "next_action": "Use for final sensitivity review after pressure and calibration gaps are closed.",
    },
}


def scientific_mode_preflight_rows(
    mode_key: str,
    *,
    weakest_tier: Any = None,
    has_calibration: bool = False,
) -> list[dict[str, str]]:
    """Return user-facing preflight rows for the selected Scientific Mode."""

    key = str(mode_key or "hybrid").lower()
    cfg = _MODE_ROWS.get(key, _MODE_ROWS["hybrid"])
    tier = getattr(weakest_tier, "value", weakest_tier) or "no run yet"
    calibration_state = "loaded" if has_calibration else "not loaded"
    return [
        {"field": "Mode", "value": cfg["label"]},
        {"field": "Model pathway", "value": cfg["pathway"]},
        {"field": "Calibration effect", "value": cfg["calibration"]},
        {"field": "Output rendering", "value": cfg["rendering"]},
        {"field": "Expected runtime", "value": cfg["runtime"]},
        {"field": "Current evidence", "value": f"{tier}; calibration {calibration_state}"},
        {"field": "Recommended use", "value": cfg["next_action"]},
    ]


def render_scientific_mode_preflight(
    *,
    container: Any,
    mode_key: str,
    weakest_tier: Any = None,
    has_calibration: bool = False,
) -> None:
    """Render a compact mode-preflight panel."""

    rows = scientific_mode_preflight_rows(
        mode_key,
        weakest_tier=weakest_tier,
        has_calibration=has_calibration,
    )
    body = "".join(
        '<div style="display:grid;grid-template-columns:minmax(110px,0.35fr) 1fr;'
        'gap:10px;padding:6px 0;border-top:1px solid var(--dps-border);">'
        '<div class="dps-mono" style="font-size:10.5px;color:var(--dps-text-dim);'
        'text-transform:uppercase;">'
        f'{html.escape(row["field"])}</div>'
        '<div style="font-size:12.5px;color:var(--dps-text);line-height:1.45;">'
        f'{html.escape(row["value"])}</div></div>'
        for row in rows
    )
    container.html(
        '<div style="margin-top:8px;padding:10px 12px;'
        'background:var(--dps-surface-2);border:1px solid var(--dps-border);'
        'border-radius:4px;">'
        '<div class="dps-mono" style="font-size:10.5px;'
        'letter-spacing:0.08em;text-transform:uppercase;'
        'color:var(--dps-accent);font-weight:600;margin-bottom:4px;">'
        "Scientific mode preflight</div>"
        f"{body}</div>"
    )


__all__ = [
    "render_scientific_mode_preflight",
    "scientific_mode_preflight_rows",
]
