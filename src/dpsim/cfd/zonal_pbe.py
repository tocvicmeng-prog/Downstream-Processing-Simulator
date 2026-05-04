"""Zonal CFD-PBE coupling: feed CFD-resolved ε field into the M1 PBE solver.

Loads ``zones.json`` (locked schema v1.0, see ``cad/cfd/zones_schema.md``),
validates against the spec via Pydantic v2, and integrates the population
balance equation across N CFD-derived compartments with zone-specific ε.

The schema is the contract between OpenFOAM-side post-processing
(``cad/cfd/scripts/extract_epsilon.py``) and the DPSim-side coupling. Hard
validation runs at load time; advisory checks emit warnings without failing.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Self

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from scipy.integrate import solve_ivp

from ..datatypes import KernelConfig, MaterialProperties
from ..level1_emulsification.kernels import (
    breakage_rate_dispatch,
    coalescence_rate_dispatch,
)
from ..level1_emulsification.solver import PBESolver

logger = logging.getLogger(__name__)


SCHEMA_VERSION_SUPPORTED = "1.0"

ZoneKind = Literal[
    "impeller_swept_volume",
    "stator_slot_exit",
    "near_wall",
    "bulk",
    "custom",
]

ExchangeKind = Literal["convective", "diffusive"]


class CFDCaseMetadata(BaseModel):
    """Provenance for a CFD run. Does not feed the PBE coupling directly;
    used by the consistency check and for run-report traceability.
    """

    model_config = ConfigDict(extra="forbid")

    case_name: str
    stirrer_type: str
    vessel: str
    rpm: float = Field(gt=0)
    fluid_temperature_K: float = Field(gt=0)
    openfoam_solver: str
    time_averaging_window_s: tuple[float, float]
    n_cells_total: int = Field(ge=1)
    convergence_residual: float = Field(ge=0)
    epsilon_volume_weighted_avg_W_per_kg: float = Field(ge=0)

    @field_validator("time_averaging_window_s")
    @classmethod
    def _window_ordered(cls, v: tuple[float, float]) -> tuple[float, float]:
        if not (v[1] > v[0]):
            raise ValueError(
                f"time_averaging_window_s[1] ({v[1]}) must be > [0] ({v[0]})"
            )
        return v


class CFDZone(BaseModel):
    """A single CFD-derived compartment for PBE integration.

    Two ε values per zone — see ``cad/cfd/zones_schema.md`` §"Two-ε rationale":

    - ``epsilon_avg_W_per_kg``: drives the coalescence kernel.
    - ``epsilon_breakage_weighted_W_per_kg``: biased toward high-ε
      hotspots within the zone, drives the breakage kernel.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    kind: ZoneKind
    volume_m3: float = Field(gt=0)
    cell_count: int = Field(ge=1)
    epsilon_avg_W_per_kg: float = Field(ge=0)
    epsilon_breakage_weighted_W_per_kg: float = Field(ge=0)
    shear_rate_avg_per_s: float = Field(ge=0)
    centroid_xyz_m: tuple[float, float, float] | None = None
    kolmogorov_length_m: float | None = Field(default=None, gt=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _breakage_weighted_geq_avg(self) -> Self:
        # Breakage weighting biases toward high-ε regions, so the weighted
        # value can never legitimately fall below the volume-average. Allow
        # 1% slack to absorb numerical noise from CFD post-processing.
        eps_avg = self.epsilon_avg_W_per_kg
        eps_brk = self.epsilon_breakage_weighted_W_per_kg
        if eps_brk + 1e-12 < 0.99 * eps_avg:
            raise ValueError(
                f"Zone '{self.name}': epsilon_breakage_weighted_W_per_kg "
                f"({eps_brk:.4g}) must be >= epsilon_avg_W_per_kg "
                f"({eps_avg:.4g}) within 1% slack. Breakage-frequency "
                f"weighting biases toward high-ε regions; weighted < average "
                f"indicates a bug in extract_epsilon.py."
            )
        return self


class CFDZoneExchange(BaseModel):
    """Convective droplet transfer between two zones.

    One-way and well-mixed: droplets leaving ``from_zone`` carry the source
    zone's instantaneous DSD. Bidirectional flow is represented as two
    separate entries.
    """

    model_config = ConfigDict(extra="forbid")

    from_zone: str
    to_zone: str
    volumetric_flow_m3_per_s: float = Field(ge=0)
    kind: ExchangeKind = "convective"

    @model_validator(mode="after")
    def _from_neq_to(self) -> Self:
        if self.from_zone == self.to_zone:
            raise ValueError(
                f"Exchange has from_zone == to_zone == '{self.from_zone}'"
            )
        return self


class CFDZonesPayload(BaseModel):
    """Top-level zones.json payload (schema v1.0)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str
    case_metadata: CFDCaseMetadata
    zones: list[CFDZone] = Field(min_length=1)
    exchanges: list[CFDZoneExchange] = Field(default_factory=list)

    @field_validator("schema_version")
    @classmethod
    def _supported_version(cls, v: str) -> str:
        if v != SCHEMA_VERSION_SUPPORTED:
            raise ValueError(
                f"Unsupported schema_version '{v}'. Loader supports "
                f"'{SCHEMA_VERSION_SUPPORTED}'. See cad/cfd/zones_schema.md "
                f"§'Versioning policy' for the migration policy."
            )
        return v

    @model_validator(mode="after")
    def _cross_field_consistency(self) -> Self:
        """Cross-field validation rules. Field-local rules (schema_version,
        per-zone ε_brk ≥ ε_avg, exchange from_zone ≠ to_zone, time-window
        ordering) live on the individual model validators above; the rules
        below need access to multiple zones / exchanges at once.
        """
        names = [z.name for z in self.zones]

        # Unique zone names — exchanges and the per-zone state vector are
        # name-keyed, so duplicates would silently alias.
        if len(set(names)) != len(names):
            dupes = sorted({n for n in names if names.count(n) > 1})
            raise ValueError(f"Duplicate zone name(s): {dupes}")

        # Exchange endpoints reference existing zones — guards against
        # phantom-zone exchanges produced by a partial extract_epsilon.py run.
        valid = set(names)
        for i, ex in enumerate(self.exchanges):
            if ex.from_zone not in valid:
                raise ValueError(
                    f"exchanges[{i}].from_zone='{ex.from_zone}' "
                    f"not in zone names {sorted(valid)}"
                )
            if ex.to_zone not in valid:
                raise ValueError(
                    f"exchanges[{i}].to_zone='{ex.to_zone}' "
                    f"not in zone names {sorted(valid)}"
                )

        # Volume-weighted ε aggregation matches the case metadata
        # within 1 % — `case_metadata.epsilon_volume_weighted_avg_W_per_kg`
        # must equal Σ(V_i × ε_avg_i) / Σ(V_i) modulo CFD post-processing
        # noise. Wider drift indicates corrupted JSON or an extract_epsilon
        # bug.
        total_v = sum(z.volume_m3 for z in self.zones)
        if total_v <= 0:
            raise ValueError("Total zone volume is non-positive")
        v_weighted_eps = (
            sum(z.volume_m3 * z.epsilon_avg_W_per_kg for z in self.zones)
            / total_v
        )
        meta_eps = self.case_metadata.epsilon_volume_weighted_avg_W_per_kg
        if meta_eps > 0:
            rel_err = abs(v_weighted_eps - meta_eps) / meta_eps
            if rel_err > 0.01:
                raise ValueError(
                    f"case_metadata.epsilon_volume_weighted_avg_W_per_kg "
                    f"({meta_eps:.4g}) inconsistent with zone aggregation "
                    f"Σ(V·ε)/ΣV = {v_weighted_eps:.4g}; relative error "
                    f"{rel_err:.1%} exceeds the 1% sanity gate. Likely "
                    f"corrupted JSON or extract_epsilon.py bug."
                )

        return self

    def total_volume_m3(self) -> float:
        return sum(z.volume_m3 for z in self.zones)

    def zone_by_name(self, name: str) -> CFDZone:
        for z in self.zones:
            if z.name == name:
                return z
        raise KeyError(f"No zone named '{name}'; have {[z.name for z in self.zones]}")


def load_zones_json(path: Path) -> CFDZonesPayload:
    """Load and validate ``zones.json`` against the locked v1.0 schema.

    Hard validation is enforced by Pydantic (see :class:`CFDZonesPayload` and
    nested models). Soft advisory checks (under-resolved zones, loose
    convergence, etc.) emit log warnings without failing the load.

    Raises
    ------
    pydantic.ValidationError
        On any hard schema violation (missing field, wrong sign, unknown
        zone reference, schema_version mismatch, breakage-weighted ε
        below volume-average, etc.).
    json.JSONDecodeError
        On malformed JSON.
    FileNotFoundError
        If ``path`` does not exist.

    See ``cad/cfd/zones_schema.md`` for the full field-by-field
    specification.
    """
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    payload = CFDZonesPayload.model_validate(raw)
    _emit_advisory_warnings(payload)
    return payload


def _emit_advisory_warnings(p: CFDZonesPayload) -> None:
    """Soft sanity checks — warn but don't fail. See zones_schema.md
    §"Validation rules (advisory)"."""
    if p.case_metadata.n_cells_total < 100_000:
        logger.warning(
            "CFD mesh is coarse: n_cells_total=%d (< 1e5). "
            "Zone-averaged ε may be unreliable.",
            p.case_metadata.n_cells_total,
        )
    if p.case_metadata.convergence_residual > 1e-4:
        logger.warning(
            "CFD convergence residual %.2e exceeds the 1e-4 advisory "
            "threshold. ε field may not be fully converged.",
            p.case_metadata.convergence_residual,
        )
    for z in p.zones:
        if z.cell_count < 100:
            logger.warning(
                "Zone '%s' is under-resolved: cell_count=%d (< 100).",
                z.name,
                z.cell_count,
            )
        if z.volume_m3 < 1e-9:
            logger.warning(
                "Zone '%s' has sub-mm³ volume %.2e m³; likely meshing artifact.",
                z.name,
                z.volume_m3,
            )


@dataclass
class ZonalEmulsificationResult:
    """Result of a zonal CFD-PBE integration.

    The aggregated DSD is the volume-weighted concatenation of per-zone
    DSDs: ``aggregated_counts[j] = Σ_i V_i × N_i,j`` (total droplet count
    in bin j across all zones). Per-zone DSDs are stored as number
    densities ``N_i [count/m³]`` so they remain comparable to the legacy
    single-zone solver output.
    """

    d_pivots: np.ndarray
    aggregated_counts: np.ndarray
    N_per_zone: dict[str, np.ndarray]
    aggregated_d32: float
    aggregated_d43: float
    aggregated_d10: float
    aggregated_d50: float
    aggregated_d90: float
    aggregated_span: float
    aggregated_total_droplet_volume_m3: float
    per_zone_d32: dict[str, float]
    converged: bool
    n_zones: int
    integration_time_s: float
    solver_message: str
    initial_total_droplet_volume_m3: float = 0.0
    volume_balance_relative_error: float = 0.0
    diagnostics: dict[str, Any] = field(default_factory=dict)


def integrate_pbe_with_zones(
    payload: CFDZonesPayload,
    material: MaterialProperties,
    kernels: KernelConfig,
    phi_d: float,
    duration_s: float,
    *,
    n_bins: int = 50,
    d_min: float = 0.1e-6,
    d_max: float = 500e-6,
    d32_premix: float = 100e-6,
    sigma_premix: float = 0.5,
    rtol: float = 1e-5,
    atol: float = 1e-15,
) -> ZonalEmulsificationResult:
    """Integrate the PBE on each zone with zone-specific ε, exchanging
    droplets between zones via convective flow.

    Reuses the canonical Alopaeus breakage kernel and Coulaloglou-Tavlarides
    coalescence kernel from ``level1_emulsification``; this function only
    drives the spatial coupling.

    State vector
    ------------
    ``state`` is a flattened ``(n_zones × n_bins,)`` array where
    ``state[i*n_bins + j] = N_i,j`` is the number density [count/m³] of
    droplets of bin ``j`` in zone ``i``. Each zone uses the same
    fixed-pivot diameter grid.

    Per-zone kernel selection
    -------------------------
    - Breakage kernel uses ``zone.epsilon_breakage_weighted_W_per_kg``.
      Biased toward sub-zone hotspots — captures the fact that g(d, ε)
      is convex in ε so the average ε underestimates breakage.
    - Coalescence kernel uses ``zone.epsilon_avg_W_per_kg``. The
      collision-frequency / film-drainage product is more linear in ε
      and the volume-average is the appropriate scalar.

    Convective exchange
    -------------------
    For an exchange ``i_from → i_to`` with volumetric flow ``Q`` [m³/s],
    droplet number density evolves as::

        dN_from/dt += ... - (Q/V_from) × N_from        # outflow
        dN_to/dt   += ... + (Q/V_to)   × N_from        # inflow (well-mixed)

    Different denominators capture that the source zone loses fractional
    volume per second while the target zone gains the same absolute count
    distributed over its (different) volume.

    Parameters
    ----------
    payload : CFDZonesPayload
        Validated ``zones.json`` from :func:`load_zones_json`.
    material : MaterialProperties
        Continuous- and dispersed-phase fluid properties.
    kernels : KernelConfig
        Breakage / coalescence model selection and constants.
    phi_d : float
        Dispersed-phase volume fraction (0, 1). Treated as the local
        fraction in every zone at t=0.
    duration_s : float
        Integration duration [s]. No adaptive extension — call again
        with a longer duration if d32 has not stabilised.
    n_bins, d_min, d_max : int, float, float
        Fixed-pivot diameter grid configuration. Defaults match
        :class:`PBESolver`.
    d32_premix, sigma_premix : float, float
        Initial log-normal premix DSD parameters (same in every zone).
    rtol, atol : float, float
        LSODA tolerances.

    Returns
    -------
    ZonalEmulsificationResult

    Notes
    -----
    Internal coupling: this function uses :meth:`PBESolver._build_breakage_matrix`
    and :meth:`PBESolver._compute_rhs`. If those internals change, this
    function must be updated in lockstep. The alternative — duplicating
    the fixed-pivot redistribution math — was rejected to keep the
    breakage / coalescence physics in a single source of truth.
    """
    if duration_s <= 0:
        raise ValueError(f"duration_s must be > 0, got {duration_s}")
    if not (0.0 < phi_d < 1.0):
        raise ValueError(f"phi_d must be in (0, 1), got {phi_d}")

    solver = PBESolver(n_bins=n_bins, d_min=d_min, d_max=d_max)
    d_pivots = solver.d_pivots
    v_pivots = solver.v_pivots
    n_zones = len(payload.zones)

    nu_c = material.mu_oil / material.rho_oil if material.rho_oil > 0 else None

    # Apply the MaterialProperties.breakage_C3 override the legacy solver
    # honours (uncertainty perturbations / reagent overrides). Done once
    # per call — kernels object is not mutated.
    if material.breakage_C3 != 0.0:
        kernels = KernelConfig(
            breakage_model=kernels.breakage_model,
            coalescence_model=kernels.coalescence_model,
            breakage_C1=kernels.breakage_C1,
            breakage_C2=kernels.breakage_C2,
            breakage_C3=material.breakage_C3,
            coalescence_C4=kernels.coalescence_C4,
            coalescence_C5=kernels.coalescence_C5,
            phi_d_correction=kernels.phi_d_correction,
            coalescence_exponent=kernels.coalescence_exponent,
        )

    # Precompute per-zone kernels and breakage matrices.
    g_list: list[np.ndarray] = []
    Q_list: list[np.ndarray] = []
    birth_list: list[np.ndarray] = []
    death_list: list[np.ndarray] = []

    for z in payload.zones:
        g = breakage_rate_dispatch(
            d_pivots,
            z.epsilon_breakage_weighted_W_per_kg,
            material.sigma,
            material.rho_oil,
            material.mu_d,
            kernels,
            nu_c=nu_c,
        )
        Q = coalescence_rate_dispatch(
            d_pivots,
            z.epsilon_avg_W_per_kg,
            material.sigma,
            material.rho_oil,
            kernels,
            phi_d=phi_d,
            mu_c=material.mu_oil,
        )
        birth, death = solver._build_breakage_matrix(g)
        g_list.append(g)
        Q_list.append(Q)
        birth_list.append(birth)
        death_list.append(death)

    # Precompute exchange rate constants.
    # Each entry: (i_from, i_to, k_out, k_in) where
    #   k_out = Q_flow / V_from   (fractional outflow rate from source zone)
    #   k_in  = Q_flow / V_to     (fractional inflow rate into target zone)
    zone_idx = {z.name: i for i, z in enumerate(payload.zones)}
    exch_tuples: list[tuple[int, int, float, float]] = []
    for ex in payload.exchanges:
        if ex.kind != "convective":
            raise NotImplementedError(
                f"Exchange kind '{ex.kind}' not supported in v1.0 "
                f"(only 'convective')"
            )
        i_from = zone_idx[ex.from_zone]
        i_to = zone_idx[ex.to_zone]
        v_from = payload.zones[i_from].volume_m3
        v_to = payload.zones[i_to].volume_m3
        exch_tuples.append((
            i_from,
            i_to,
            ex.volumetric_flow_m3_per_s / v_from,
            ex.volumetric_flow_m3_per_s / v_to,
        ))

    # Initial DSD: identical in every zone (local phi_d in every zone).
    n0 = solver._initial_distribution(
        phi_d, d32_premix=d32_premix, sigma_premix=sigma_premix
    )
    state0 = np.tile(n0, n_zones)

    # Total initial droplet volume across all zones [m³] = phi_d × Σ V_i.
    initial_total_volume = phi_d * payload.total_volume_m3()

    def rhs(t: float, state: np.ndarray) -> np.ndarray:
        state = np.maximum(state, 0.0)
        dstate = np.zeros_like(state)
        # Per-zone breakage + coalescence — delegated to PBESolver internals
        # so the kernel arithmetic stays single-sourced.
        for i in range(n_zones):
            sl = slice(i * n_bins, (i + 1) * n_bins)
            dstate[sl] = solver._compute_rhs(
                t, state[sl], birth_list[i], death_list[i], Q_list[i],
            )
        # Convective exchange: well-mixed source DSD carried by Q_flow.
        for i_from, i_to, k_out, k_in in exch_tuples:
            sl_from = slice(i_from * n_bins, (i_from + 1) * n_bins)
            sl_to = slice(i_to * n_bins, (i_to + 1) * n_bins)
            n_from = state[sl_from]
            dstate[sl_from] -= k_out * n_from
            dstate[sl_to] += k_in * n_from
        return dstate

    sol = solve_ivp(
        rhs,
        (0.0, duration_s),
        state0,
        method="LSODA",
        rtol=rtol,
        atol=atol,
        max_step=duration_s / 10.0,
    )

    if not sol.success:
        logger.warning(
            "Zonal PBE solver did not converge for case '%s': %s",
            payload.case_metadata.case_name,
            sol.message,
        )

    # Disaggregate the final state.
    final = np.maximum(sol.y[:, -1], 0.0)
    n_per_zone: dict[str, np.ndarray] = {}
    per_zone_d32: dict[str, float] = {}
    aggregated_counts = np.zeros(n_bins)
    for i, z in enumerate(payload.zones):
        n_i = final[i * n_bins : (i + 1) * n_bins]
        n_per_zone[z.name] = n_i.copy()
        num = float(np.sum(n_i * d_pivots ** 3))
        den = float(np.sum(n_i * d_pivots ** 2))
        per_zone_d32[z.name] = num / den if den > 0.0 else 0.0
        # Aggregate: total count in bin j = Σ_i V_i × N_i,j.
        aggregated_counts += z.volume_m3 * n_i

    # Aggregated statistics (from total counts — Sauter etc. are ratios so
    # the unit of `aggregated_counts` doesn't matter, only the shape).
    den32 = float(np.sum(aggregated_counts * d_pivots ** 2))
    den43 = float(np.sum(aggregated_counts * d_pivots ** 3))
    d32_agg = (
        float(np.sum(aggregated_counts * d_pivots ** 3)) / den32
        if den32 > 0.0 else 0.0
    )
    d43_agg = (
        float(np.sum(aggregated_counts * d_pivots ** 4)) / den43
        if den43 > 0.0 else 0.0
    )
    vol_per_bin = aggregated_counts * v_pivots
    total_vol = float(np.sum(vol_per_bin))
    if total_vol > 0.0:
        cum_vol = np.cumsum(vol_per_bin) / total_vol
        d10_agg = float(np.interp(0.1, cum_vol, d_pivots))
        d50_agg = float(np.interp(0.5, cum_vol, d_pivots))
        d90_agg = float(np.interp(0.9, cum_vol, d_pivots))
        span_agg = (d90_agg - d10_agg) / d50_agg if d50_agg > 0.0 else 0.0
    else:
        d10_agg = d50_agg = d90_agg = span_agg = 0.0

    if initial_total_volume > 0.0:
        vol_balance_err = abs(total_vol - initial_total_volume) / initial_total_volume
    else:
        vol_balance_err = 0.0

    # ─── B-1d (W-006) M1 PBE regime guards ──────────────────────────────────
    # d/η_K ratio places each zone on the inertial-vs-viscous breakage map:
    #   d/η_K << 1  : sub-Kolmogorov; viscous breakage dominates and the
    #                 standard inertial kernel (CT) loses physical meaning.
    #                 Alopaeus C3 viscous correction is the recommended fix.
    #   d/η_K ~ 5–10: transitional regime — typical of stirred-vessel
    #                 emulsifications.
    #   d/η_K >> 10 : inertial subrange; standard kernels apply.
    # Below the warning threshold the aggregated d32 should be treated as
    # ranking-only by the render path (B-1b decision_grade gate). The
    # threshold value mirrors the Liao & Lucas 2009 review.
    _SUB_KOLMOGOROV_RATIO = 5.0

    eta_K_per_zone: dict[str, float] = {}
    d32_over_eta_K_per_zone: dict[str, float] = {}
    sub_kolmogorov_zones: list[str] = []
    for zone in payload.zones:
        eps_break = float(zone.epsilon_breakage_weighted_W_per_kg)
        # Prefer the CFD-supplied Kolmogorov length when present; recompute
        # from the breakage-weighted ε otherwise (consistent with kernel use).
        if zone.kolmogorov_length_m is not None and zone.kolmogorov_length_m > 0.0:
            eta_K = float(zone.kolmogorov_length_m)
        elif nu_c is not None and eps_break > 0.0:
            eta_K = (nu_c ** 3 / eps_break) ** 0.25
        else:
            eta_K = 0.0
        eta_K_per_zone[zone.name] = eta_K
        d32_z = per_zone_d32.get(zone.name, 0.0)
        ratio = d32_z / eta_K if eta_K > 0.0 and d32_z > 0.0 else 0.0
        d32_over_eta_K_per_zone[zone.name] = ratio
        if 0.0 < ratio < _SUB_KOLMOGOROV_RATIO:
            sub_kolmogorov_zones.append(zone.name)

    finite_ratios = [r for r in d32_over_eta_K_per_zone.values() if r > 0.0]
    d32_over_eta_K_aggregated_min = min(finite_ratios) if finite_ratios else 0.0

    regime_guard_warnings: list[str] = []
    if sub_kolmogorov_zones:
        regime_guard_warnings.append(
            f"Sub-Kolmogorov regime in zone(s) {sorted(sub_kolmogorov_zones)}: "
            f"d32/eta_K < {_SUB_KOLMOGOROV_RATIO:.1f}. Inertial breakage kernels "
            f"(CT) lose accuracy here. Use Alopaeus with breakage_C3 > 0 "
            f"(currently breakage_C3={float(kernels.breakage_C3):.3g}) or treat "
            f"d32 as ranking-only."
        )
    aggregated_d32_local = d32_agg
    if (
        aggregated_d32_local > 0.0
        and d32_over_eta_K_aggregated_min > 0.0
        and d32_over_eta_K_aggregated_min < _SUB_KOLMOGOROV_RATIO
    ):
        regime_guard_warnings.append(
            f"Aggregated d32 ({aggregated_d32_local * 1e6:.2f} µm) sits at "
            f"d32/eta_K_min = {d32_over_eta_K_aggregated_min:.2f}; below the "
            f"{_SUB_KOLMOGOROV_RATIO:.1f} inertial-subrange threshold."
        )

    return ZonalEmulsificationResult(
        d_pivots=d_pivots.copy(),
        aggregated_counts=aggregated_counts,
        N_per_zone=n_per_zone,
        aggregated_d32=d32_agg,
        aggregated_d43=d43_agg,
        aggregated_d10=d10_agg,
        aggregated_d50=d50_agg,
        aggregated_d90=d90_agg,
        aggregated_span=span_agg,
        aggregated_total_droplet_volume_m3=total_vol,
        per_zone_d32=per_zone_d32,
        converged=bool(sol.success),
        n_zones=n_zones,
        integration_time_s=float(duration_s),
        solver_message=str(sol.message),
        initial_total_droplet_volume_m3=initial_total_volume,
        volume_balance_relative_error=vol_balance_err,
        diagnostics={
            "n_eval_points": int(sol.t.size),
            "n_zones": n_zones,
            "n_bins": n_bins,
            "n_exchanges": len(exch_tuples),
            # B-1d (W-006) regime guards on the zonal CFD-PBE path.
            "eta_K_per_zone_m": eta_K_per_zone,
            "d32_over_eta_K_per_zone": d32_over_eta_K_per_zone,
            "d32_over_eta_K_aggregated_min": d32_over_eta_K_aggregated_min,
            "sub_kolmogorov_zones": sub_kolmogorov_zones,
            "sub_kolmogorov_ratio_threshold": _SUB_KOLMOGOROV_RATIO,
            "breakage_C3": float(kernels.breakage_C3),
            "breakage_model": kernels.breakage_model.value,
            "regime_guard_warnings": regime_guard_warnings,
        },
    )


def consistency_check_with_volume_avg(
    payload: CFDZonesPayload,
    legacy_volume_avg_eps: float,
    tolerance_rel: float = 0.30,
) -> dict[str, float | bool]:
    """Sanity gate: CFD volume-weighted ε vs the legacy empirical estimate.

    The legacy DPSim PBE solver derives ε_avg from
    ``P / (ρ · V_tank) = Po · N³ · D⁵ / V_tank`` (see
    ``level1_emulsification/energy.py::average_dissipation``). The CFD zonal
    aggregation Σ(V_i · ε_avg_i) / Σ(V_i) should match this within ~30%
    (per Scientific Advisor 2026-05-01 guidance).

    A larger discrepancy indicates one of:

    - CFD setup error (wrong RPM, wrong viscosity, incomplete convergence).
    - Empirical Po and impeller D in ``datatypes.py`` need adjustment.
    - Zone partitioning in ``extract_epsilon.py`` is missing volume.

    Parameters
    ----------
    payload : CFDZonesPayload
        Validated zones.json contents.
    legacy_volume_avg_eps : float
        Empirical ε_avg [W/kg] from ``average_dissipation``. Must be >= 0.
    tolerance_rel : float, default 0.30
        Relative-error threshold above which the check fails. The 0.30
        default reflects the irreducible Po-correlation uncertainty for
        non-standard impeller geometries.

    Returns
    -------
    dict with keys
        ``epsilon_cfd_volume_weighted_W_per_kg``, ``epsilon_legacy_W_per_kg``,
        ``absolute_error_W_per_kg``, ``relative_error``, ``tolerance_rel``,
        ``passed`` (bool).

    Raises
    ------
    ValueError
        If ``legacy_volume_avg_eps`` is negative.
    """
    if legacy_volume_avg_eps < 0:
        raise ValueError(
            f"legacy_volume_avg_eps must be >= 0, got {legacy_volume_avg_eps}"
        )

    total_v = payload.total_volume_m3()
    eps_cfd = (
        sum(z.volume_m3 * z.epsilon_avg_W_per_kg for z in payload.zones)
        / total_v
    )
    abs_err = abs(eps_cfd - legacy_volume_avg_eps)
    if legacy_volume_avg_eps > 0:
        rel_err = abs_err / legacy_volume_avg_eps
    else:
        rel_err = float("inf") if eps_cfd > 0 else 0.0

    passed = rel_err <= tolerance_rel

    if not passed:
        logger.warning(
            "CFD-vs-legacy ε consistency check FAILED for case '%s': "
            "ε_cfd=%.3g, ε_legacy=%.3g, rel_err=%.1f%% > tol=%.0f%%. "
            "Likely CFD setup error or empirical Po/D needs adjustment.",
            payload.case_metadata.case_name,
            eps_cfd, legacy_volume_avg_eps,
            rel_err * 100.0, tolerance_rel * 100.0,
        )

    return {
        "epsilon_cfd_volume_weighted_W_per_kg": float(eps_cfd),
        "epsilon_legacy_W_per_kg": float(legacy_volume_avg_eps),
        "absolute_error_W_per_kg": float(abs_err),
        "relative_error": float(rel_err),
        "tolerance_rel": float(tolerance_rel),
        "passed": passed,
    }
