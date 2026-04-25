"""Auto-wire glue between v0.4.0 shell features and the existing run path.

The v0.4.0 shell introduced run history, recipe-diff snapshots, and the
evidence rollup. v0.4.1 added the named-baseline picker and the
breakthrough-curve hook. None of those features had call sites — they
were exported APIs waiting for an integration layer. This module is
that layer.

Strategy: detect run completions by tracking ``lifecycle_result``'s
identity in session state. On every shell render, compare the current
result's ``run_id`` (or its object id as fallback) to the last-seen
value. If different, the run just completed → fire the side-effect
calls (``capture_snapshot``, ``append_history``, etc.).

This avoids modifying ``ui_workflow.render_lifecycle_run_panel`` —
which is the source of truth for the existing tab-based UI and is
consumed elsewhere — and keeps the new v0.4 features additive.
"""

from __future__ import annotations

from typing import Any, Final

import streamlit as st

from dpsim.datatypes import ModelEvidenceTier
from dpsim.visualization.diff.render import capture_snapshot
from dpsim.visualization.evidence.rollup import (
    StageEvidence,
    stages_from_run_report,
)
from dpsim.visualization.run_rail.history import append_history

# Track the last-seen run identifier so we fire wire-up side effects
# exactly once per new run.
_LAST_SEEN_KEY: Final[str] = "_dpsim_autowire_last_seen_run_id"
_LAST_BREAKTHROUGH_KEY: Final[str] = "_dpsim_autowire_breakthrough"


def _identify_run(lifecycle_result: Any) -> str:
    """Return a stable id for the current ``lifecycle_result``.

    Tries the explicit ``run_id`` attribute first, then falls back to
    Python's ``id()`` of the result object — which is stable for the
    lifetime of the object in the Streamlit session.
    """
    rid = getattr(lifecycle_result, "run_id", "") or ""
    if rid:
        return str(rid)
    return f"obj:{id(lifecycle_result)}"


def _extract_run_report(lifecycle_result: Any) -> Any | None:
    """Pull a ``RunReport`` out of the lifecycle result, if present.

    The lifecycle result aggregates per-module reports; the M1 / M2 / M3
    sub-results each carry their own ``run_report``. This helper
    constructs a unified view with ``model_graph`` populated from all
    three.
    """
    # Prefer a top-level run_report if the orchestrator exposes one.
    rr = getattr(lifecycle_result, "run_report", None)
    if rr is not None and hasattr(rr, "model_graph"):
        return rr

    # Otherwise, walk per-module results and merge their model graphs.
    manifests: list[Any] = []
    for attr in ("m1_result", "m2_microsphere", "m3_method"):
        sub = getattr(lifecycle_result, attr, None)
        if sub is None:
            continue
        sub_rr = getattr(sub, "run_report", None)
        if sub_rr is None:
            continue
        graph = getattr(sub_rr, "model_graph", None) or []
        manifests.extend(graph)
    if not manifests:
        return None

    # Construct an ad-hoc RunReport-like object. We only need the
    # `model_graph` attribute since `stages_from_run_report` reads
    # nothing else.
    class _AdHocReport:
        model_graph = manifests

    return _AdHocReport()


def _extract_kpi_metrics(lifecycle_result: Any) -> dict[str, str]:
    """Pull the four headline column-performance KPIs from a lifecycle
    result, formatted as display strings for the rail's KPI grid.

    Canonical Direction-A KPIs (per ``DPSim UI Optimization`` reference):

    - ``dbc10``    — Dynamic binding capacity at 10% breakthrough (mg/mL)
    - ``recovery`` — Product recovery from elute pool (%)
    - ``hetp``     — Height equivalent to a theoretical plate (mm)
    - ``dp``       — Pressure drop across packed bed (MPa)

    The lifecycle result aggregates per-module sub-results with
    inconsistent attribute names. This helper probes known paths in
    order and falls back to ``""`` when none are available — the rail
    then renders ``"—"`` for that cell, preserving the grid layout.

    Returns:
        Dict whose keys are the KPI ids plus optional ``<key>_delta``
        and ``<key>_delta_dir`` entries for delta-chip rendering.
    """
    out: dict[str, str] = {}

    m3 = getattr(lifecycle_result, "m3_method", None) or getattr(
        lifecycle_result, "m3_result", None
    )

    # ── DBC₁₀: dynamic binding capacity at 10% breakthrough (mg/mL) ──
    if m3 is not None:
        for attr in ("dbc10_mg_mL", "dbc10", "dbc_10", "dbc"):
            v = getattr(m3, attr, None)
            if v is None:
                continue
            try:
                out["dbc10"] = f"{float(v):.1f}"
                break
            except (TypeError, ValueError):
                pass

    # ── RECOVERY (M3 % product recovered from elute pool) ────────────
    if m3 is not None:
        for attr in ("recovery_pct", "recovery", "yield_pct"):
            v = getattr(m3, attr, None)
            if v is None:
                continue
            try:
                f = float(v)
            except (TypeError, ValueError):
                continue
            pct = f * 100 if f <= 1.5 else f
            out["recovery"] = f"{pct:.1f}"
            break

    # ── HETP (height equivalent to a theoretical plate, mm) ──────────
    if m3 is not None:
        for attr in ("hetp_mm", "hetp", "plate_height_mm"):
            v = getattr(m3, attr, None)
            if v is None:
                continue
            try:
                out["hetp"] = f"{float(v):.2f}"
                break
            except (TypeError, ValueError):
                pass

    # ── ΔP (pressure drop across packed bed, MPa) ────────────────────
    if m3 is not None:
        for attr in ("delta_p_MPa", "dp_MPa", "delta_p", "pressure_drop_MPa"):
            v = getattr(m3, attr, None)
            if v is None:
                continue
            try:
                f = float(v)
            except (TypeError, ValueError):
                continue
            # Heuristic: if value > 10, assume Pa and convert.
            mpa = f / 1e6 if f > 10 else f
            out["dp"] = f"{mpa:.2f}"
            break

    return out


def _extract_breakthrough_curve(lifecycle_result: Any) -> Any | None:
    """Pull a ``BreakthroughCurve``-shaped object from the run, if any.

    Looks at ``lifecycle_result.m3_breakthrough`` and adapts it. If the
    shape doesn't match what ``chrome.breakthrough`` expects, returns
    ``None`` so the synthetic placeholder is used.
    """
    bt = getattr(lifecycle_result, "m3_breakthrough", None)
    if bt is None:
        return None

    # Best-effort adaptation: prefer P05/P50/P95 envelope arrays if
    # present (MC-LRM run), otherwise wrap a single C/C0 curve as a
    # degenerate envelope.
    try:
        from dpsim.visualization.design.chrome import BreakthroughCurve

        x = getattr(bt, "cv_axis", None) or getattr(bt, "x", None)
        p50 = getattr(bt, "p50", None) or getattr(bt, "y", None)
        if x is None or p50 is None:
            return None
        p05 = getattr(bt, "p05", None) or p50
        p95 = getattr(bt, "p95", None) or p50
        return BreakthroughCurve(
            x=list(x),
            p50=list(p50),
            p05=list(p05) if p05 is not None else list(p50),
            p95=list(p95) if p95 is not None else list(p50),
        )
    except Exception:  # pragma: no cover — defensive
        return None


def autowire_shell_state(
    *,
    current_recipe: Any,
) -> tuple[list[StageEvidence], Any | None]:
    """Detect new run completions and fire the v0.4 wire-up side effects.

    Returns:
        ``(evidence_stages, breakthrough_curve)`` — the values the shell
        should render. Falls back to placeholder lists / ``None`` if no
        run has completed in this session yet.
    """
    lifecycle_result = st.session_state.get("lifecycle_result")
    if lifecycle_result is None:
        return [], None

    current_id = _identify_run(lifecycle_result)
    last_seen = st.session_state.get(_LAST_SEEN_KEY)

    if current_id != last_seen:
        # New run detected — fire side effects exactly once.
        st.session_state[_LAST_SEEN_KEY] = current_id

        # 1. Snapshot the recipe so the diff panel populates.
        try:
            capture_snapshot(current_recipe)
        except Exception:  # pragma: no cover — diff is non-critical
            pass

        # 2. Append to run history.
        try:
            tier = getattr(lifecycle_result, "weakest_evidence_tier", None)
            tier_value = (
                getattr(tier, "value", tier)
                if tier is not None
                else ModelEvidenceTier.UNSUPPORTED.value
            )
            from dpsim.visualization.diff.snapshot import snapshot_recipe

            append_history(
                recipe_name=getattr(current_recipe, "name", None) or "current",
                snapshot=snapshot_recipe(current_recipe),  # type: ignore[arg-type]
                evidence_min=str(tier_value),
                notes="Auto-captured at run completion.",
                metrics=_extract_kpi_metrics(lifecycle_result),
            )
        except Exception:  # pragma: no cover — defensive
            pass

        # 3. Cache the breakthrough curve for the rail.
        st.session_state[_LAST_BREAKTHROUGH_KEY] = _extract_breakthrough_curve(
            lifecycle_result
        )

    # Build the evidence rollup from the current result every render
    # (cheap; enables the rollup to follow the result without flashing).
    rr = _extract_run_report(lifecycle_result)
    evidence_stages: list[StageEvidence] = []
    if rr is not None:
        evidence_stages = stages_from_run_report(rr)

    # Pretty-name the per-stage labels using the canonical short labels.
    label_map = {
        "M1_fabrication": "M1 — Fabrication",
        "M2_functionalization": "M2 — Functionalisation",
        "M3_performance": "M3 — Column method",
        "QC": "QC",
    }
    evidence_stages = [
        StageEvidence(
            stage_id=s.stage_id,
            label=label_map.get(s.stage_id, s.label),
            tier=s.tier,
            note=s.note,
        )
        for s in evidence_stages
    ]

    return evidence_stages, st.session_state.get(_LAST_BREAKTHROUGH_KEY)


def derive_stage_status(*, current_recipe: Any) -> dict[str, str]:
    """Derive per-stage status (pending / active / valid / warn) from state.

    Used by ``shell.render_stage_spine`` to colour the stage nodes
    correctly. Reads ``lifecycle_result``, the validation report (if
    any), and the active stage to assign each of the seven stages a
    status.

    Args:
        current_recipe: Live recipe (used only for fallback signals).

    Returns:
        Dict from stage id → status literal (``pending`` / ``active`` /
        ``valid`` / ``warn``). Stages not in the dict default to
        ``pending``.
    """
    from dpsim.visualization.shell.shell import get_active_stage

    out: dict[str, str] = {}
    active = get_active_stage()
    out[active] = "active"

    lifecycle_result = st.session_state.get("lifecycle_result")
    if lifecycle_result is None:
        return out

    # Validation outcome → warn / valid.
    validation = getattr(lifecycle_result, "validation", None)
    n_blockers = (
        len(getattr(validation, "blockers", [])) if validation is not None else 0
    )
    n_warnings = (
        len(getattr(validation, "warnings", [])) if validation is not None else 0
    )

    # Per-module sub-result presence → that stage has run.
    if getattr(lifecycle_result, "m1_result", None) is not None:
        out.setdefault("m1", "valid")
    if getattr(lifecycle_result, "m2_microsphere", None) is not None:
        out.setdefault("m2", "valid" if n_blockers == 0 else "warn")
    if getattr(lifecycle_result, "m3_method", None) is not None:
        out.setdefault("m3", "valid" if n_blockers == 0 else "warn")

    if validation is not None:
        out.setdefault("validation", "warn" if n_warnings or n_blockers else "valid")
    if lifecycle_result is not None:
        out.setdefault("run", "valid")

    # Active stage colour wins over status colour.
    out[active] = "active"
    return out
