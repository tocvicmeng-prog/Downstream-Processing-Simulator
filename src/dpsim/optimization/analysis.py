"""Pareto front analysis and visualisation utilities."""

from __future__ import annotations

import numpy as np

from ..core.decision_claim import DecisionClaim, make_decision_claim
from ..core.decision_grade import OutputType, RenderMode
from ..datatypes import ModelEvidenceTier
from ..datatypes import OptimizationState
from .objectives import LOG_SCALE_INDICES


_DEFAULT_OBJECTIVE_OUTPUTS: tuple[OutputType, ...] = (
    OutputType.D32,
    OutputType.PORE_SIZE,
    OutputType.MODULUS,
)


def pareto_summary(state: OptimizationState) -> str:
    """Generate a text summary of the Pareto front."""
    lines = [
        "Optimisation Summary",
        f"  Total evaluations: {len(state.X_observed)}",
        f"  Pareto-optimal points: {len(state.pareto_X)}",
        f"  Final hypervolume: {state.hypervolume:.4f}",
        f"  Converged: {state.converged}",
        "",
        "Pareto Front:",
        f"  {'#':>3s}  {'f_d32':>8s}  {'f_pore':>8s}  {'f_G_DN':>8s}  {'RPM':>8s}  {'Span80':>8s}  {'AgarFrac':>8s}  {'T_oil_C':>8s}  {'Cool_C/m':>8s}  {'Genipin':>8s}  {'t_xlink_h':>8s}",
    ]

    for i in range(len(state.pareto_X)):
        x_ss = state.pareto_X[i]
        y = state.pareto_Y[i]
        x = x_ss.copy()
        for j in LOG_SCALE_INDICES:
            x[j] = 10.0 ** x[j]

        lines.append(
            f"  {i+1:3d}"
            f"  {y[0]:8.3f}"
            f"  {y[1]:8.3f}"
            f"  {y[2]:8.3f}"
            f"  {x[0]:8.0f}"
            f"  {x[1]:8.1f}"
            f"  {x[2]:8.3f}"
            f"  {x[3]-273.15:8.1f}"
            f"  {x[4]*60:8.2f}"
            f"  {x[5]:8.2f}"
            f"  {x[6]/3600:8.1f}"
        )

    return "\n".join(lines)


def best_compromise(state: OptimizationState) -> int:
    """Find the best compromise Pareto point (min sum of objectives)."""
    if len(state.pareto_Y) == 0:
        return 0  # fallback
    sums = np.sum(state.pareto_Y, axis=1)
    return int(np.argmin(sums))


def pareto_decision_claims(
    state: OptimizationState,
    *,
    output_types: tuple[OutputType, ...] = _DEFAULT_OBJECTIVE_OUTPUTS,
) -> list[list[DecisionClaim]]:
    """Return decision claims for Pareto objective values.

    Internal BO still uses raw objective values. This function is the reporting
    boundary: every value exposed in a Pareto table can carry an evidence tier,
    render mode, and reason.
    """
    claims_by_candidate: list[list[DecisionClaim]] = []
    tiers = list(getattr(state, "pareto_evidence_tiers", []) or [])
    for i, y in enumerate(np.asarray(state.pareto_Y, dtype=float)):
        tier = _tier_from_string(tiers[i] if i < len(tiers) else "")
        candidate_claims: list[DecisionClaim] = []
        for j, value in enumerate(y[:len(output_types)]):
            output_type = output_types[j]
            candidate_claims.append(
                make_decision_claim(
                    float(value),
                    output_type,
                    tier,
                    name=f"Pareto objective {j + 1} ({output_type.value})",
                    unit="objective",
                    valid_domain_status="optimizer_reported",
                    assay_required=_assay_required_for_output(output_type),
                )
            )
        claims_by_candidate.append(candidate_claims)
    return claims_by_candidate


def pareto_claims_export(state: OptimizationState) -> list[dict]:
    """JSON-safe Pareto claim export."""
    rows: list[dict] = []
    for i, claims in enumerate(pareto_decision_claims(state)):
        rows.append({
            "candidate_index": i,
            "claims": [claim.to_dict() for claim in claims],
            "evidence_tier": (
                state.pareto_evidence_tiers[i]
                if i < len(state.pareto_evidence_tiers) else "semi_quantitative"
            ),
            "missing_calibration": _missing_calibration_for_claims(claims),
            "pressure_feasibility": _pressure_feasibility_for_candidate(state, i),
        })
    return rows


def pareto_candidate_rankings(state: OptimizationState) -> dict[str, dict | None]:
    """Return separate best-predicted and best-actionable Pareto candidates.

    ``best_predicted`` is purely objective-based. ``best_actionable`` requires
    decision-grade point-number claims and an evaluated, passing pressure
    feasibility screen.
    """
    rows = pareto_claims_export(state)
    if not rows:
        return {"best_predicted": None, "best_actionable": None}

    objectives = np.asarray(state.pareto_Y, dtype=float)
    objective_sums = np.sum(objectives, axis=1)
    best_predicted_idx = int(np.argmin(objective_sums))
    best_actionable_idx: int | None = None
    best_actionable_score = float("inf")
    for row in rows:
        idx = int(row["candidate_index"])
        if _actionability_gaps(row):
            continue
        score = float(objective_sums[idx])
        if score < best_actionable_score:
            best_actionable_score = score
            best_actionable_idx = idx

    return {
        "best_predicted": _ranking_record(
            rows[best_predicted_idx],
            objective_sum=float(objective_sums[best_predicted_idx]),
        ),
        "best_actionable": (
            _ranking_record(
                rows[best_actionable_idx],
                objective_sum=float(objective_sums[best_actionable_idx]),
            )
            if best_actionable_idx is not None else None
        ),
    }


def wetlab_actionability_score(
    *,
    missing_assays: int,
    reagent_hazard_score: float,
    protocol_duration_h: float,
    pressure_headroom: float,
    calibration_distance: float,
) -> float:
    """Score 0..1 where higher means easier to take to the bench."""
    missing_penalty = min(max(int(missing_assays), 0), 10) / 10.0
    hazard_penalty = min(max(float(reagent_hazard_score), 0.0), 5.0) / 5.0
    duration_penalty = min(max(float(protocol_duration_h), 0.0), 48.0) / 48.0
    pressure_penalty = min(max(float(pressure_headroom), 0.0), 1.5) / 1.5
    calibration_penalty = min(max(float(calibration_distance), 0.0), 1.0)
    raw_penalty = (
        0.30 * missing_penalty
        + 0.20 * hazard_penalty
        + 0.15 * duration_penalty
        + 0.20 * pressure_penalty
        + 0.15 * calibration_penalty
    )
    return max(0.0, min(1.0, 1.0 - raw_penalty))


def inverse_design_quality_label(
    *,
    n_measurements: int,
    ess: float,
    min_measurements: int = 8,
    min_ess: float = 100.0,
) -> str:
    """Return advisory/calibrated label for inverse-design posterior quality."""
    if n_measurements < min_measurements:
        return "advisory_insufficient_measurements"
    if ess < min_ess:
        return "advisory_low_ess"
    return "calibration_supported"


def _tier_from_string(value: str) -> ModelEvidenceTier:
    try:
        return ModelEvidenceTier(str(value))
    except ValueError:
        return ModelEvidenceTier.SEMI_QUANTITATIVE


def _assay_required_for_output(output_type: OutputType) -> str:
    if output_type == OutputType.D32:
        return "DSD"
    if output_type == OutputType.PORE_SIZE:
        return "pore size and porosity"
    if output_type == OutputType.MODULUS:
        return "modulus/compression"
    if output_type in {OutputType.PRESSURE_DROP, OutputType.PRESSURE_LIMIT, OutputType.Q_MAX}:
        return "pressure-flow curve"
    if output_type == OutputType.DBC:
        return "DBC breakthrough"
    return "calibration assay"


def _missing_calibration_for_claims(claims: list[DecisionClaim]) -> list[dict]:
    """Return claim-level calibration gaps blocking point-value display."""
    missing: list[dict] = []
    for claim in claims:
        if claim.render_mode == RenderMode.NUMBER:
            continue
        missing.append({
            "output_type": claim.output_type.value,
            "assay_required": claim.assay_required or "calibration assay",
            "evidence_tier": claim.evidence_tier.value,
            "required_tier": claim.required_tier.value,
            "render_mode": claim.render_mode.value,
        })
    return missing


def _pressure_feasibility_for_candidate(
    state: OptimizationState,
    candidate_index: int,
) -> dict:
    """Return JSON-safe pressure feasibility for one Pareto candidate."""
    feasible_values = list(getattr(state, "pareto_pressure_feasible", []) or [])
    violation_values = list(getattr(state, "pareto_pressure_violations", []) or [])
    violations = (
        list(violation_values[candidate_index])
        if candidate_index < len(violation_values) else []
    )
    if candidate_index >= len(feasible_values) or feasible_values[candidate_index] is None:
        return {
            "status": "not_evaluated",
            "feasible": None,
            "violations": violations,
        }
    feasible = bool(feasible_values[candidate_index])
    return {
        "status": "feasible" if feasible else "blocked",
        "feasible": feasible,
        "violations": violations,
    }


def _actionability_gaps(row: dict) -> list[str]:
    gaps: list[str] = []
    if row.get("missing_calibration"):
        gaps.append("missing_calibration")
    pressure_status = row.get("pressure_feasibility", {}).get("status")
    if pressure_status == "blocked":
        gaps.append("pressure_blocked")
    elif pressure_status != "feasible":
        gaps.append("pressure_feasibility_not_evaluated")
    return gaps


def _ranking_record(row: dict, *, objective_sum: float) -> dict:
    return {
        "candidate_index": int(row["candidate_index"]),
        "objective_sum": objective_sum,
        "evidence_tier": row["evidence_tier"],
        "missing_calibration_count": len(row.get("missing_calibration", [])),
        "pressure_status": row.get("pressure_feasibility", {}).get("status"),
        "actionability_gaps": _actionability_gaps(row),
    }

