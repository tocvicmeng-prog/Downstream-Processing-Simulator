# ADR-009 — Multi-column series pressure: scope vs cyclic SMB

**Status:** Accepted
**Date:** 2026-05-10
**Decision driver:** v0.8.2 W-045. The v0.7.0 plan §6 deferred "Multi-column / parallel-bed pressure modelling" naming SMB / CC8 as v0.9 epics. This ADR + the accompanying ``multi_column.py`` close the **series-of-columns** code path; full cyclic SMB dynamics (port valves, rotation schedule, multi-bed elution-displacement-coupling) remains the explicit v0.9 binding-open scope.

## Context

DPSim's `ColumnGeometry` and `compute_pressure_envelope` are
single-column-only. A common downstream-process configuration uses
**two or more columns in series** — a common-mode practice for
sequential-mechanism purification (e.g., capture-on-Protein-A
followed by polish-IEX in series, or two stacked columns to extend
bed length). For these configurations the user wants:

1. The total ΔP across the series.
2. The worst-case `headroom_ratio` across columns (the binding column).
3. The series Q_max — set by the *most-restrictive* column.
4. A unified envelope for UI display + BO feasibility consumption.

**Series** is mathematically simple: pressure drops add, flow rate is
the same through every column. It is amenable to a forward
aggregation pass over the existing `compute_pressure_envelope` output.

**Parallel** beds (true multi-column SMB / CC8 with synchronous
port-rotation and inter-column displacement) are NOT amenable to the
same simple aggregation:
- Each column's bound profile depends on the upstream column's outlet,
  which changes every port-switch cycle.
- The "envelope" concept itself becomes time-varying; a pre-flight
  scalar headroom is misleading when the load column rotates every
  10 minutes.
- Realistic simulation requires a coupled multi-bed solver with
  port-switch event handling.

## Decision

**Ship `MultiColumnGeometry` and `compute_multi_column_envelope` for
the series case in v0.8.2.** Defer cyclic SMB dynamics to v0.9.

```python
@dataclass(frozen=True)
class MultiColumnGeometry:
    columns: tuple[ColumnGeometry, ...]
    polymer_families: tuple[PolymerFamily, ...]   # one per column
    name: str = "series"

@dataclass(frozen=True)
class MultiColumnPressureEnvelope:
    columns: tuple[ColumnGeometry, ...]
    per_column_envelopes: tuple[PressureEnvelope, ...]
    total_dP_predicted_pa: float
    total_dP_max_operational_pa: float    # min across cols × ?? — see §rule
    series_Q_max_m3_s: float              # min across columns
    series_Q_recommended_m3_s: float      # 0.5 × series_Q_max
    series_headroom_ratio: float          # max across columns
    decision_tier: ModelEvidenceTier      # weakest across columns
    valid_domain_violations: tuple[str, ...]
```

### Aggregation rules

- **Total ΔP_predicted_pa** = Σ_i ΔP_predicted_pa_i. Pressure drops
  add in series; this is exact for the linear KC regime.
- **Series Q_max_m3_s** = min_i Q_max_m3_s_i. The bottleneck column
  sets the operational ceiling.
- **Series Q_recommended_m3_s** = 0.5 × series Q_max — same 50 %
  fouling-headroom convention as the single-column envelope.
- **Total ΔP_max_operational_pa** = Σ_i ΔP_max_operational_pa_i
  evaluated **at the series Q_max**, not at each column's local
  Q_max. The series ΔP at Q_max is ≤ Σ ΔP_max because columns
  with higher Q_max are operating below their local ceiling.
- **Headroom ratio** = max_i headroom_ratio_i. The worst column drives
  the verdict.
- **Decision tier** = weakest tier across columns (per the existing
  `_demote_tier` helper logic).
- **Valid domain violations** = concatenation across columns, prefixed
  with the column name.

These rules make the series envelope **conservative** — never more
permissive than the bottleneck column.

## Consequences

- Users with two columns in series can now run a unified BO feasibility
  check via the existing `PressureFeasibilityContext` (extended with
  an optional `multi_column` reference) or via direct
  `compute_multi_column_envelope` consumption.
- The UI side of multi-column display is left to v0.9 — the
  `MultiColumnPressureEnvelope` dataclass exists and is fully tested
  but not rendered in `tab_m3.py` yet. Adding the render is purely
  additive when the demand arises.
- Pre-flight envelope per column is the ground truth; aggregation does
  NOT recompute physics — it just sums and finds extremes.

## Out of scope

- **True SMB** — port-switching, rotation schedule, multi-bed
  elution-displacement coupling. v0.9 candidate.
- **Parallel beds (Pall CC8 in parallel mode)** — same Q split N
  ways instead of summed in series. The math is dual to series
  (Q_total = Σ Q_i, ΔP shared); a `MultiColumnGeometry(parallel=True)`
  variant could ship later but doesn't fit the typical use case.
- **Time-varying envelope** — series envelope is steady-state; the
  cyclic-SMB envelope has to be expressed as a per-cycle band.

## References

- v0.7.0 work plan §6 — original deferral of "Multi-column / parallel-bed pressure modelling".
- v0.8.0 release handover §"Cumulative open future-work items" — restated for v0.8.1 / v0.8.2 inheritance.
- ADR-004 — Pressure envelope anchor (the single-column physics that this aggregation builds on).
