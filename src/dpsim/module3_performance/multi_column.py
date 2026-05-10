"""Multi-column (series) pressure envelope aggregation.

B-3h / W-045 — v0.8.2. Per ADR-009, ships the **series**-of-columns
pressure aggregation. Cyclic SMB / multi-bed port-rotation dynamics
are explicitly out of scope and remain a v0.9 candidate.

Aggregation rules (ADR-009 §"Aggregation rules"):

* ``total_dP_predicted_pa`` = Σ_i ΔP_i (KC is linear in Q at fixed ε_b).
* ``series_Q_max_m3_s`` = min_i Q_max_i (the bottleneck column).
* ``series_Q_recommended_m3_s`` = 0.5 · series_Q_max (50 % fouling
  buffer, same convention as the single-column envelope).
* ``series_headroom_ratio`` = max_i headroom_ratio_i (worst column
  drives the verdict).
* ``decision_tier`` = weakest tier across columns.
* ``valid_domain_violations`` = concatenation across columns,
  prefixed with the column name.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from dpsim.core.mobile_phase import MobilePhase
from dpsim.datatypes import ModelEvidenceTier, PolymerFamily
from dpsim.module3_performance.hydrodynamics import ColumnGeometry
from dpsim.module3_performance.pressure_envelope import (
    PressureEnvelope,
    compute_pressure_envelope,
)


# ─── Tier-rollup helper ────────────────────────────────────────────────────


_TIER_LADDER: tuple[ModelEvidenceTier, ...] = (
    ModelEvidenceTier.VALIDATED_QUANTITATIVE,
    ModelEvidenceTier.CALIBRATED_LOCAL,
    ModelEvidenceTier.SEMI_QUANTITATIVE,
    ModelEvidenceTier.QUALITATIVE_TREND,
    ModelEvidenceTier.UNSUPPORTED,
)


def _weakest_tier(tiers: tuple[ModelEvidenceTier, ...]) -> ModelEvidenceTier:
    """Return the weakest tier in the ladder (highest index)."""
    if not tiers:
        return ModelEvidenceTier.SEMI_QUANTITATIVE
    weakest_idx = -1
    weakest = tiers[0]
    for tier in tiers:
        for idx, member in enumerate(_TIER_LADDER):
            if member.value == tier.value and idx > weakest_idx:
                weakest_idx = idx
                weakest = member
                break
    return weakest


# ─── Value types ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class MultiColumnGeometry:
    """A series-of-columns aggregate.

    Attributes
    ----------
    columns :
        Per-column geometry, ordered from inlet to outlet.
    polymer_families :
        One PolymerFamily per column for K_geom lookup. Length must
        match ``columns``.
    name :
        Optional human-readable label for the aggregate (e.g.
        ``"capture+polish"``).
    """

    columns: tuple[ColumnGeometry, ...]
    polymer_families: tuple[PolymerFamily, ...]
    name: str = "series"

    def __post_init__(self) -> None:
        if len(self.columns) != len(self.polymer_families):
            raise ValueError(
                f"columns length {len(self.columns)} != polymer_families "
                f"length {len(self.polymer_families)}."
            )
        if len(self.columns) == 0:
            raise ValueError(
                "MultiColumnGeometry requires at least one column."
            )

    @property
    def n_columns(self) -> int:
        return len(self.columns)


@dataclass(frozen=True)
class MultiColumnPressureEnvelope:
    """Aggregated envelope across a series of columns.

    Attributes
    ----------
    name :
        Echoed from the source ``MultiColumnGeometry``.
    per_column :
        Per-column ``PressureEnvelope`` results, ordered to match
        ``MultiColumnGeometry.columns``.
    Q_set_m3_s :
        The series flow rate (constant through every column).
    total_dP_predicted_pa :
        Sum of ``dP_predicted_pa`` across columns.
    total_dP_max_operational_pa :
        Sum of ``dP_max_operational_pa`` across columns. Note that
        only the bottleneck column is at its local ceiling; the rest
        are operating below — see ADR-009 §"Aggregation rules".
    series_Q_max_m3_s :
        ``min_i Q_max_i`` — the bottleneck column sets the operational
        ceiling.
    series_Q_recommended_m3_s :
        ``0.5 × series_Q_max_m3_s``.
    series_headroom_ratio :
        ``max_i headroom_ratio_i`` — worst column drives verdict.
    decision_tier :
        Weakest tier across columns.
    valid_domain_violations :
        Concatenation across columns, prefixed with column index.
    """

    name: str
    per_column: tuple[PressureEnvelope, ...]
    Q_set_m3_s: float
    total_dP_predicted_pa: float
    total_dP_max_operational_pa: float
    series_Q_max_m3_s: float
    series_Q_recommended_m3_s: float
    series_headroom_ratio: float
    decision_tier: ModelEvidenceTier
    valid_domain_violations: tuple[str, ...]

    @property
    def n_columns(self) -> int:
        return len(self.per_column)

    @property
    def is_blocker(self) -> bool:
        return self.series_headroom_ratio > 1.0

    @property
    def is_warning(self) -> bool:
        return 0.7 < self.series_headroom_ratio <= 1.0


# ─── Public API ───────────────────────────────────────────────────────────


def compute_multi_column_envelope(
    *,
    geometry: MultiColumnGeometry,
    mobile_phase: MobilePhase,
    Q_set_m3_s: float,
    G_DN_pa: Optional[tuple[Optional[float], ...]] = None,
    E_star_pa: Optional[tuple[Optional[float], ...]] = None,
    bead_d32_m: Optional[tuple[Optional[float], ...]] = None,
    calibration_store: Optional[dict] = None,
) -> MultiColumnPressureEnvelope:
    """Compute the series-aggregate pressure envelope.

    Parameters
    ----------
    geometry :
        ``MultiColumnGeometry`` defining columns + per-column families.
    mobile_phase :
        Common mobile phase across all columns. Real downstream
        recipes can have different buffers between columns; that
        falls under v0.9 multi-step series scope.
    Q_set_m3_s :
        Series flow rate (same through every column).
    G_DN_pa, E_star_pa, bead_d32_m :
        Optional per-column overrides forwarded to each column's
        envelope call. Length must match ``geometry.columns``; pass
        ``None`` for entries that should fall through to the column's
        own field.
    calibration_store :
        Forwarded as-is to every per-column envelope call. v0.8.2
        does not support per-column calibration overrides; that's a
        downstream enhancement.

    Returns
    -------
    MultiColumnPressureEnvelope
    """
    n = geometry.n_columns

    def _resolve(seq: Optional[tuple[Optional[float], ...]]) -> tuple[Optional[float], ...]:
        if seq is None:
            return tuple(None for _ in range(n))
        if len(seq) != n:
            raise ValueError(
                f"override sequence length {len(seq)} != n_columns {n}."
            )
        return seq

    g_seq = _resolve(G_DN_pa)
    e_seq = _resolve(E_star_pa)
    d_seq = _resolve(bead_d32_m)

    per_column: list[PressureEnvelope] = []
    for i, (col, fam) in enumerate(zip(
        geometry.columns, geometry.polymer_families,
    )):
        env = compute_pressure_envelope(
            polymer_family=fam,
            column=col,
            mobile_phase=mobile_phase,
            Q_set_m3_s=Q_set_m3_s,
            G_DN_pa=g_seq[i],
            E_star_pa=e_seq[i],
            bead_d32_m=d_seq[i],
            calibration_store=calibration_store,
        )
        per_column.append(env)

    total_dp = sum(e.dP_predicted_pa for e in per_column)
    total_dp_max = sum(e.dP_max_operational_pa for e in per_column)
    series_q_max = min(e.Q_max_m3_s for e in per_column)
    series_q_rec = 0.5 * series_q_max
    series_headroom = max(e.headroom_ratio for e in per_column)
    series_tier = _weakest_tier(tuple(e.decision_tier for e in per_column))

    violations: list[str] = []
    for i, e in enumerate(per_column):
        for v in e.valid_domain_violations:
            violations.append(f"col[{i}]: {v}")

    return MultiColumnPressureEnvelope(
        name=geometry.name,
        per_column=tuple(per_column),
        Q_set_m3_s=Q_set_m3_s,
        total_dP_predicted_pa=total_dp,
        total_dP_max_operational_pa=total_dp_max,
        series_Q_max_m3_s=series_q_max,
        series_Q_recommended_m3_s=series_q_rec,
        series_headroom_ratio=series_headroom,
        decision_tier=series_tier,
        valid_domain_violations=tuple(violations),
    )


__all__ = [
    "MultiColumnGeometry",
    "MultiColumnPressureEnvelope",
    "compute_multi_column_envelope",
]
