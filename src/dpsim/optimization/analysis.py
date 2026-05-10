"""Pareto front analysis and visualisation utilities."""

from __future__ import annotations

import numpy as np

from ..core.decision_claim import DecisionClaim, make_decision_claim
from ..core.decision_grade import OutputType
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
        })
    return rows


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

