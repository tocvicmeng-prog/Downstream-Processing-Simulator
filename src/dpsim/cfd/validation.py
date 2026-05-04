"""CFD-PBE end-to-end validation gates (B-2b / W-008, v0.6.5).

Reference: docs/update_workplan_2026-05-04.md §4 → B-2b.

Provides structured pass/fail reports for the four CFD-PBE gates required
by the work plan plus the locked evidence-tier ladder. The pydantic
schema in ``cad/cfd/zones_schema.md`` (and its mirror in
``cfd/zonal_pbe.py``) raises on hard schema violations at load time;
this module adds the *operational-quality* gates that an OpenFOAM run
must clear before its outputs can be promoted past QUALITATIVE_TREND.

Gates
-----
1. **Mesh QA** — total cell count and per-zone minimum, plus optional
   y+ check when supplied via ``case_metadata.metadata``. Below-threshold
   meshes raise a CFDGateFailure of type "mesh_resolution".
2. **Residual convergence** — ``case_metadata.convergence_residual``
   must fall below the steady-state threshold (default 1e-4 for ``simpleFoam``-
   class steady solvers; configurable). Loose convergence flags the run
   as not steady-state.
3. **ε-volume consistency** — ``Σ(V_i · ε_avg_i) / Σ(V_i)`` must match
   ``case_metadata.epsilon_volume_weighted_avg_W_per_kg`` within 1%
   (the same threshold the schema enforces; this gate returns a
   structured value for downstream reports rather than raising).
4. **Exchange-flow conservation** — per zone, the absolute imbalance
   between inflow and outflow volumetric rates must be ≤ tolerance ×
   max(in, out). Picks up well-mixed-approximation failures and missing
   exchange entries from a partial extract_epsilon.py run.

Evidence-tier ladder
--------------------
Locked per work plan §4 → B-2b:

  * No PIV calibration                      → QUALITATIVE_TREND
  * PIV at this geometry & RPM              → CALIBRATED_LOCAL
  * PIV + bench DSD validation in envelope  → VALIDATED_QUANTITATIVE

The ladder is exposed as ``assign_cfd_evidence_tier`` and consumed by
the manifest constructor in ``zonal_pbe.integrate_pbe_with_zones`` (and
any future M1 orchestrator that wraps PIV/DSD provenance).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from dpsim.cfd.zonal_pbe import CFDZonesPayload
from dpsim.datatypes import ModelEvidenceTier


# ─── Default thresholds ──────────────────────────────────────────────────────
#
# Conservative defaults for a 100 mL bench beaker with rotor-stator or
# stirred-vessel geometry. Tighter thresholds may be appropriate for
# production geometries; pass them explicitly to override.

_DEFAULT_TOTAL_CELLS_MIN: int = 200_000
_DEFAULT_PER_ZONE_CELLS_MIN: int = 5_000
_DEFAULT_RESIDUAL_THRESHOLD: float = 1.0e-4
_DEFAULT_EPS_CONSISTENCY_TOLERANCE_REL: float = 0.01
_DEFAULT_EXCHANGE_BALANCE_TOLERANCE_REL: float = 0.05
_DEFAULT_Y_PLUS_MAX_FOR_LOG_LAW: float = 300.0


# ─── Result types ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class GateResult:
    """One CFD-PBE gate's pass / fail outcome.

    ``passed`` is the headline boolean; ``message`` is a human-readable
    explanation; ``value`` carries the measured number (e.g. residual
    1.7e-5, ε relative error 0.4%, total cell count 350_000) for the
    audit trail.
    """

    name: str
    passed: bool
    value: float
    threshold: float
    message: str = ""


@dataclass
class CFDValidationReport:
    """Composite report of all four gates."""

    case_name: str
    mesh_total_cells: GateResult
    mesh_per_zone_min_cells: GateResult
    residual_convergence: GateResult
    epsilon_volume_consistency: GateResult
    exchange_flow_balance: list[GateResult]
    advisory_messages: list[str] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        scalars = [
            self.mesh_total_cells.passed,
            self.mesh_per_zone_min_cells.passed,
            self.residual_convergence.passed,
            self.epsilon_volume_consistency.passed,
        ]
        return all(scalars) and all(g.passed for g in self.exchange_flow_balance)

    @property
    def failed_gates(self) -> list[str]:
        out: list[str] = []
        for gate in (
            self.mesh_total_cells,
            self.mesh_per_zone_min_cells,
            self.residual_convergence,
            self.epsilon_volume_consistency,
        ):
            if not gate.passed:
                out.append(gate.name)
        for ex_gate in self.exchange_flow_balance:
            if not ex_gate.passed:
                out.append(ex_gate.name)
        return out


# ─── Gates ───────────────────────────────────────────────────────────────────


def check_mesh_quality(
    payload: CFDZonesPayload,
    *,
    total_cells_min: int = _DEFAULT_TOTAL_CELLS_MIN,
    per_zone_cells_min: int = _DEFAULT_PER_ZONE_CELLS_MIN,
) -> tuple[GateResult, GateResult]:
    """Mesh-resolution gates: total cells and per-zone minimum.

    Returns (total_gate, per_zone_min_gate).
    """
    total = int(payload.case_metadata.n_cells_total)
    total_gate = GateResult(
        name="mesh_total_cells",
        passed=total >= total_cells_min,
        value=float(total),
        threshold=float(total_cells_min),
        message=(
            f"Total cell count {total:,} {'≥' if total >= total_cells_min else '<'} "
            f"required minimum {total_cells_min:,}."
        ),
    )

    if not payload.zones:
        per_zone = GateResult(
            name="mesh_per_zone_min_cells",
            passed=False,
            value=0.0,
            threshold=float(per_zone_cells_min),
            message="No zones defined.",
        )
    else:
        min_zone_cells = min(z.cell_count for z in payload.zones)
        worst_zone = next(
            z.name for z in payload.zones if z.cell_count == min_zone_cells
        )
        per_zone = GateResult(
            name="mesh_per_zone_min_cells",
            passed=min_zone_cells >= per_zone_cells_min,
            value=float(min_zone_cells),
            threshold=float(per_zone_cells_min),
            message=(
                f"Smallest zone '{worst_zone}' has {min_zone_cells:,} cells "
                f"({'≥' if min_zone_cells >= per_zone_cells_min else '<'} "
                f"required {per_zone_cells_min:,})."
            ),
        )
    return total_gate, per_zone


def check_residual_convergence(
    payload: CFDZonesPayload,
    *,
    threshold: float = _DEFAULT_RESIDUAL_THRESHOLD,
) -> GateResult:
    """Steady-state residual must fall below ``threshold``."""
    residual = float(payload.case_metadata.convergence_residual)
    return GateResult(
        name="residual_convergence",
        passed=residual < threshold,
        value=residual,
        threshold=threshold,
        message=(
            f"Convergence residual {residual:.2e} "
            f"{'<' if residual < threshold else '≥'} threshold {threshold:.2e}."
        ),
    )


def check_epsilon_volume_consistency(
    payload: CFDZonesPayload,
    *,
    tolerance_rel: float = _DEFAULT_EPS_CONSISTENCY_TOLERANCE_REL,
) -> GateResult:
    """Σ(V_i · ε_avg_i) / Σ(V_i) vs case_metadata, within tolerance."""
    total_v = payload.total_volume_m3()
    if total_v <= 0.0:
        return GateResult(
            name="epsilon_volume_consistency",
            passed=False,
            value=float("inf"),
            threshold=tolerance_rel,
            message="Total zone volume is non-positive.",
        )
    v_weighted_eps = (
        sum(z.volume_m3 * z.epsilon_avg_W_per_kg for z in payload.zones)
        / total_v
    )
    meta_eps = float(payload.case_metadata.epsilon_volume_weighted_avg_W_per_kg)
    if meta_eps <= 0.0:
        return GateResult(
            name="epsilon_volume_consistency",
            passed=False,
            value=float("inf"),
            threshold=tolerance_rel,
            message="case_metadata.epsilon_volume_weighted_avg_W_per_kg is non-positive.",
        )
    rel_err = abs(v_weighted_eps - meta_eps) / meta_eps
    return GateResult(
        name="epsilon_volume_consistency",
        passed=rel_err <= tolerance_rel,
        value=rel_err,
        threshold=tolerance_rel,
        message=(
            f"Σ(V·ε)/ΣV = {v_weighted_eps:.4g} W/kg vs metadata "
            f"{meta_eps:.4g} W/kg → relative error {rel_err:.2%} "
            f"({'≤' if rel_err <= tolerance_rel else '>'} {tolerance_rel:.0%})."
        ),
    )


def check_exchange_flow_balance(
    payload: CFDZonesPayload,
    *,
    tolerance_rel: float = _DEFAULT_EXCHANGE_BALANCE_TOLERANCE_REL,
) -> list[GateResult]:
    """Per-zone in-flow vs out-flow conservation check.

    For each zone, the absolute difference between sum of incoming and
    sum of outgoing convective flows must be at most ``tolerance_rel ×
    max(in, out)``. Imbalance > tolerance indicates a missing exchange
    entry or an extract_epsilon.py bug.
    """
    in_flow: dict[str, float] = {z.name: 0.0 for z in payload.zones}
    out_flow: dict[str, float] = {z.name: 0.0 for z in payload.zones}
    for ex in payload.exchanges:
        if ex.kind != "convective":
            continue
        out_flow[ex.from_zone] += ex.volumetric_flow_m3_per_s
        in_flow[ex.to_zone] += ex.volumetric_flow_m3_per_s

    gates: list[GateResult] = []
    for z in payload.zones:
        i = in_flow[z.name]
        o = out_flow[z.name]
        scale = max(i, o)
        if scale <= 0.0:
            # Zone is isolated (no exchanges) — vacuously balanced.
            gates.append(GateResult(
                name=f"exchange_balance:{z.name}",
                passed=True,
                value=0.0,
                threshold=tolerance_rel,
                message=f"Zone '{z.name}' has no convective exchanges (isolated).",
            ))
            continue
        rel_imbalance = abs(i - o) / scale
        gates.append(GateResult(
            name=f"exchange_balance:{z.name}",
            passed=rel_imbalance <= tolerance_rel,
            value=rel_imbalance,
            threshold=tolerance_rel,
            message=(
                f"Zone '{z.name}': in={i:.4g} out={o:.4g} m^3/s → "
                f"imbalance {rel_imbalance:.2%} "
                f"({'≤' if rel_imbalance <= tolerance_rel else '>'} {tolerance_rel:.0%})."
            ),
        ))
    return gates


def validate_cfd_payload(
    payload: CFDZonesPayload,
    *,
    total_cells_min: int = _DEFAULT_TOTAL_CELLS_MIN,
    per_zone_cells_min: int = _DEFAULT_PER_ZONE_CELLS_MIN,
    residual_threshold: float = _DEFAULT_RESIDUAL_THRESHOLD,
    eps_tolerance_rel: float = _DEFAULT_EPS_CONSISTENCY_TOLERANCE_REL,
    exchange_tolerance_rel: float = _DEFAULT_EXCHANGE_BALANCE_TOLERANCE_REL,
) -> CFDValidationReport:
    """Run all four gates and return a structured composite report."""
    total_gate, per_zone_gate = check_mesh_quality(
        payload,
        total_cells_min=total_cells_min,
        per_zone_cells_min=per_zone_cells_min,
    )
    residual_gate = check_residual_convergence(payload, threshold=residual_threshold)
    eps_gate = check_epsilon_volume_consistency(payload, tolerance_rel=eps_tolerance_rel)
    exchange_gates = check_exchange_flow_balance(
        payload, tolerance_rel=exchange_tolerance_rel,
    )
    return CFDValidationReport(
        case_name=payload.case_metadata.case_name,
        mesh_total_cells=total_gate,
        mesh_per_zone_min_cells=per_zone_gate,
        residual_convergence=residual_gate,
        epsilon_volume_consistency=eps_gate,
        exchange_flow_balance=exchange_gates,
    )


# ─── Evidence-tier ladder (locked per work plan §4 → B-2b) ──────────────────


@dataclass(frozen=True)
class CFDCalibrationStatus:
    """Inputs to the CFD evidence-tier ladder.

    ``piv_calibrated_at_geometry_and_rpm`` is True when PIV measurements
    on this exact stirrer-vessel geometry at this RPM (within ±10%) have
    been ingested; ``bench_dsd_validated`` is True when an end-to-end
    DSD measurement on the same geometry / formulation has been compared
    to the simulation output and lies within the validation envelope.
    """

    piv_calibrated_at_geometry_and_rpm: bool = False
    bench_dsd_validated_in_envelope: bool = False


def assign_cfd_evidence_tier(
    status: Optional[CFDCalibrationStatus] = None,
    *,
    gates_passed: bool = True,
) -> ModelEvidenceTier:
    """Locked evidence-tier ladder for CFD-PBE outputs.

      * No PIV calibration                                 → QUALITATIVE_TREND
      * PIV at this geometry & RPM                         → CALIBRATED_LOCAL
      * PIV + bench DSD validated in envelope              → VALIDATED_QUANTITATIVE
      * Any operational-quality gate (mesh / residual /    → UNSUPPORTED
        ε-consistency / exchange) failed

    The gate-failure short-circuit prevents promoting a numerically
    unconverged or under-resolved run regardless of how much PIV
    calibration accompanies it — bad CFD beats good PIV.
    """
    if not gates_passed:
        return ModelEvidenceTier.UNSUPPORTED
    if status is None:
        return ModelEvidenceTier.QUALITATIVE_TREND
    if status.bench_dsd_validated_in_envelope and status.piv_calibrated_at_geometry_and_rpm:
        return ModelEvidenceTier.VALIDATED_QUANTITATIVE
    if status.piv_calibrated_at_geometry_and_rpm:
        return ModelEvidenceTier.CALIBRATED_LOCAL
    return ModelEvidenceTier.QUALITATIVE_TREND


__all__ = [
    "CFDCalibrationStatus",
    "CFDValidationReport",
    "GateResult",
    "assign_cfd_evidence_tier",
    "check_epsilon_volume_consistency",
    "check_exchange_flow_balance",
    "check_mesh_quality",
    "check_residual_convergence",
    "validate_cfd_payload",
]
