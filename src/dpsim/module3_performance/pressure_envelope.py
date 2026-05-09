"""Pre-flight pressure-envelope computation for chromatography columns.

B-2f / W-020 + W-026 — KEYSTONE batch from the v0.7.0 M3 back-pressure
work plan (``docs/update_workplan_2026-05-10_m3_pressure.md``).

The /scientific-advisor architecture identified the v0.6.6
``ColumnGeometry.max_safe_flow_rate(safety=0.8)`` anchor as the most
serious correctness defect in the M3 module: it treats ΔP_max as
``safety × E_star`` (the bursting modulus), but for soft chromatography
media the operational limit is set by *bed-compression runaway*, not
bead bursting. The two are physically distinct and the operational
limit (u_crit) is typically 5–50× lower than the bursting limit.

This module replaces that anchor with a per-family u_crit formulation:

    u_crit ≈ K_geom_family · G_DN · d_p² / (μ · L)

and produces a structured ``PressureEnvelope`` value object that the
recipe-validation layer (G8 gate, B-2h) and the M3 UI section
(B-2h) consume as a *pre-flight* preview before the user presses
"Start flow."

Architectural principles
------------------------
- One PressureEnvelope per recipe step. The envelope captures the
  predicted ΔP, the operational ΔP_max, and the headroom ratio at the
  step's flow rate, viscosity, and column geometry.
- Tier-rollup. The decision tier walks the family's valid_domain and
  the resolved viscosity's extrapolated flag, demoting one step per
  out-of-domain dimension. Floors at QUALITATIVE_TREND.
- Two distinct pressure ceilings. ``dP_max_operational_pa`` is the
  u_crit-based bed-compression limit (the *real* operational ceiling).
  ``dP_max_burst_pa`` is the structural ceiling from E_star, kept as a
  separate diagnostic and explicitly NOT the operational limit.
- Iteration is deferred to B-2g. v0.7's B-2f scaffold uses one-shot
  Kozeny-Carman; B-2g (W-022) adds the ε_b feedback loop without
  changing this module's API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from dpsim.core.mobile_phase import MobilePhase
from dpsim.core.viscosity import (
    ViscosityResult,
    resolve_mobile_phase_viscosity,
)
from dpsim.datatypes import ModelEvidenceTier, PolymerFamily
from dpsim.module3_performance.family_kgeom import (
    check_valid_domain,
    lookup_family_kgeom,
)
from dpsim.module3_performance.hydrodynamics import ColumnGeometry


# ─── Tier ladder helpers (mirrors core.decision_grade._tier_index) ───────────


_TIER_LADDER: tuple[ModelEvidenceTier, ...] = (
    ModelEvidenceTier.VALIDATED_QUANTITATIVE,
    ModelEvidenceTier.CALIBRATED_LOCAL,
    ModelEvidenceTier.SEMI_QUANTITATIVE,
    ModelEvidenceTier.QUALITATIVE_TREND,
    ModelEvidenceTier.UNSUPPORTED,
)


def _tier_index(tier: ModelEvidenceTier) -> int:
    """Return 0-indexed position in the strongest-first ladder.

    Compared by ``.value`` per the v9.0 Family-First UI contract.
    """
    target = str(getattr(tier, "value", tier))
    for idx, member in enumerate(_TIER_LADDER):
        if member.value == target:
            return idx
    return len(_TIER_LADDER) - 1


def _demote_tier(tier: ModelEvidenceTier, steps: int = 1) -> ModelEvidenceTier:
    """Demote ``tier`` by ``steps`` positions, floored at QUALITATIVE_TREND."""
    if steps <= 0:
        return tier
    idx = _tier_index(tier)
    new_idx = min(idx + steps, _tier_index(ModelEvidenceTier.QUALITATIVE_TREND))
    return _TIER_LADDER[new_idx]


# ─── PressureEnvelope value type ────────────────────────────────────────────


@dataclass(frozen=True)
class PressureEnvelope:
    """Per-step pre-flight pressure envelope.

    Produced by ``compute_pressure_envelope`` once per recipe step.
    The recipe-validation G8 gate (B-2h) consumes ``headroom_ratio``
    and ``valid_domain_violations`` to emit BLOCKER / WARNING; the M3
    UI section (B-2h) renders the Q-vs-ΔP envelope before the user
    presses "Start flow".

    Field semantics
    ---------------
    - ``Q_set_m3_s`` is the recipe-step requested flow rate.
    - ``dP_predicted_pa`` is the model's KC prediction at Q_set under
      the resolved μ and column geometry. v0.7 uses one-shot KC; B-2g
      (W-022) adds iteration without changing this field.
    - ``dP_max_operational_pa`` is the u_crit-based bed-compression
      limit — what the user must NEVER exceed. THE operational ceiling.
    - ``dP_max_burst_pa`` is the structural ceiling from E_star; kept
      as a separate diagnostic, NOT the operational limit. Rendered
      with explicit "absolute upper bound" framing.
    - ``Q_max_m3_s`` is u_crit · A_cross — the inverted operational
      ceiling.
    - ``Q_recommended_m3_s`` is 0.5 · Q_max — a 50 % headroom buffer
      for fouling rise across the load phase.
    - ``valid_domain_violations`` is the tuple of human-readable strings
      from the family's valid_domain check; non-empty when any input
      fell outside the calibrated envelope.
    - ``decision_tier`` is the rolled-up tier after walking valid_domain
      and the resolved viscosity's extrapolated flag.
    - ``calibration_provenance`` is the per-field source map for the
      dossier export.
    """

    # ── Inputs (echoed for traceability) ──
    polymer_family: PolymerFamily
    mobile_phase: MobilePhase
    Q_set_m3_s: float
    bed_height_m: float
    column_diameter_m: float
    bead_d32_m: float
    bed_porosity: float
    G_DN_pa: float
    E_star_pa: float

    # ── Resolved viscosity (carried for downstream rendering) ──
    viscosity: ViscosityResult

    # ── Predicted hydrodynamics ──
    dP_predicted_pa: float
    dP_predicted_interval_pa: tuple[float, float]
    dP_frit_pa: float                          # zero when no frit configured

    # ── Operational limits ──
    dP_max_operational_pa: float
    dP_max_operational_interval_pa: tuple[float, float]
    dP_max_burst_pa: float                     # E_star-based; structural ceiling
    u_crit_m_s: float
    Q_max_m3_s: float
    Q_recommended_m3_s: float

    # ── Provenance + decision-grade ──
    K_geom_used: float
    K_geom_source: str                         # "family_default" | "calibrated" | "manufacturer"
    decision_tier: ModelEvidenceTier
    valid_domain_violations: tuple[str, ...]
    calibration_provenance: dict[str, str]
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def headroom_ratio(self) -> float:
        """Q_set / Q_max — 0 means no flow, 1 at the limit, > 1 exceeded.

        The G8 recipe-validation gate (B-2h) consumes this:
        - ``> 1.0`` → BLOCKER ("flow rate exceeds operational ceiling")
        - ``> 0.7`` → WARNING ("approaching operational ceiling")
        - ``≤ 0.7`` → silent pass.
        """
        if self.Q_max_m3_s <= 0.0:
            return float("inf")
        return self.Q_set_m3_s / self.Q_max_m3_s

    @property
    def is_blocker(self) -> bool:
        """True when the recipe step exceeds the operational ceiling."""
        return self.headroom_ratio > 1.0

    @property
    def is_warning(self) -> bool:
        """True when the recipe step is in the warning band (0.7 <= ratio <= 1.0)."""
        return 0.7 < self.headroom_ratio <= 1.0


# ─── Interval-band policy ────────────────────────────────────────────────────


# Default ±factor for SEMI_QUANTITATIVE INTERVAL render. The interval
# tightens at CALIBRATED_LOCAL (±20 %) and is exact at
# VALIDATED_QUANTITATIVE.
_INTERVAL_FACTOR_BY_TIER: dict[str, tuple[float, float]] = {
    ModelEvidenceTier.VALIDATED_QUANTITATIVE.value: (1.0, 1.0),
    ModelEvidenceTier.CALIBRATED_LOCAL.value: (0.80, 1.20),
    ModelEvidenceTier.SEMI_QUANTITATIVE.value: (0.50, 2.00),
    ModelEvidenceTier.QUALITATIVE_TREND.value: (0.25, 4.00),
    ModelEvidenceTier.UNSUPPORTED.value: (0.10, 10.00),
}


def _interval(point: float, tier: ModelEvidenceTier) -> tuple[float, float]:
    """Return (low, high) interval for ``point`` at the given evidence tier."""
    factors = _INTERVAL_FACTOR_BY_TIER.get(
        tier.value,
        _INTERVAL_FACTOR_BY_TIER[ModelEvidenceTier.SEMI_QUANTITATIVE.value],
    )
    lo_f, hi_f = factors
    return (point * lo_f, point * hi_f)


# ─── compute_pressure_envelope ──────────────────────────────────────────────


def compute_pressure_envelope(
    *,
    polymer_family: PolymerFamily,
    column: ColumnGeometry,
    mobile_phase: MobilePhase,
    Q_set_m3_s: float,
    G_DN_pa: Optional[float] = None,
    E_star_pa: Optional[float] = None,
    bead_d32_m: Optional[float] = None,
    calibration_store: Optional[dict] = None,
    extrapolation_policy: str = "warn",
) -> PressureEnvelope:
    """Compute the pre-flight pressure envelope for a recipe step.

    Resolution flow (architect §3.4):

    1. Resolve μ via :func:`resolve_mobile_phase_viscosity`
       (B-1f / W-023).
    2. Look up K_geom for the family via
       :func:`lookup_family_kgeom`. Override from
       ``calibration_store[family.value]["K_geom"]`` when provided.
    3. Compute u_crit = K_geom · G_DN · d_p² / (μ · L).
    4. Invert: Q_max = u_crit · A_cross. Q_recommended = 0.5 · Q_max.
    5. Compute ΔP_predicted at Q_set via Kozeny-Carman (one-shot;
       B-2g adds the ε_b feedback iteration).
    6. Add ΔP_frit when the column has frit fields configured.
    7. Compute ΔP_max_burst from E_star (structural ceiling; separate
       diagnostic from the operational limit).
    8. Tier rollup: walk valid_domain. Demote one step per non-empty
       violations list; demote one more step on viscosity.extrapolated.
       Floor at QUALITATIVE_TREND.
    9. Compute SEMI_QUANTITATIVE intervals (±factor by tier).

    Parameters
    ----------
    polymer_family :
        The bead's PolymerFamily (used as the K_geom registry key).
    column :
        ``ColumnGeometry`` instance — geometry, bed porosity, optional
        frit fields. Modulus fields (G_DN, E_star) are read from the
        explicit ``G_DN_pa`` / ``E_star_pa`` arguments below if those
        are non-None; otherwise from the column itself.
    mobile_phase :
        The recipe-step buffer specification.
    Q_set_m3_s :
        Recipe-step flow rate [m³/s].
    G_DN_pa, E_star_pa, bead_d32_m :
        Optional explicit overrides for the column's modulus and
        Sauter-mean diameter. When None, the column's fields are used.
        These are typically supplied by the lifecycle orchestrator
        (B-2h) after M2 completes — the M2-updated G_DN / E_star and
        the M1 d32.
    calibration_store :
        Optional ``dict[str, dict[str, Any]]`` keyed by
        ``PolymerFamily.value`` with manufacturer pressure-flow curve
        coefficients or local wet-lab calibration entries. When
        ``calibration_store[family.value]["K_geom"]`` is set, it
        overrides the registry default and promotes ``K_geom_source``
        to ``"calibrated"`` (or ``"manufacturer"`` per the entry's
        own metadata).
    extrapolation_policy :
        Forwarded to :func:`resolve_mobile_phase_viscosity` (default
        ``"warn"``).

    Returns
    -------
    PressureEnvelope
        Pre-flight envelope with full provenance for the dossier
        export and the G8 gate.
    """
    if Q_set_m3_s < 0.0:
        raise ValueError(f"Q_set_m3_s={Q_set_m3_s!r} must be ≥ 0.")

    # 1. Viscosity resolution.
    viscosity = resolve_mobile_phase_viscosity(
        mobile_phase, extrapolation_policy=extrapolation_policy
    )
    mu = viscosity.mu_pa_s

    # 2. K_geom lookup, with optional calibration_store override.
    family_kgeom = lookup_family_kgeom(polymer_family)
    K_geom = family_kgeom.K_geom
    K_geom_source = "family_default"
    base_tier = family_kgeom.base_tier

    if calibration_store is not None:
        family_cal = calibration_store.get(polymer_family.value, {})
        if "K_geom" in family_cal:
            K_geom = float(family_cal["K_geom"])
            K_geom_source = str(family_cal.get("source", "calibrated"))
            base_tier = ModelEvidenceTier.CALIBRATED_LOCAL

    # 3. Resolve geometry inputs (explicit overrides win).
    G_DN_resolved = float(G_DN_pa if G_DN_pa is not None else column.G_DN)
    E_star_resolved = float(E_star_pa if E_star_pa is not None else column.E_star)
    d32_resolved = float(
        bead_d32_m if bead_d32_m is not None else column.particle_diameter
    )
    L = column.bed_height
    A = column.cross_section_area

    if d32_resolved <= 0.0:
        raise ValueError(f"bead_d32_m={d32_resolved!r} must be > 0.")
    if L <= 0.0:
        raise ValueError(f"bed_height_m={L!r} must be > 0.")
    if mu <= 0.0:
        raise ValueError(f"resolved μ={mu!r} must be > 0.")
    if G_DN_resolved <= 0.0:
        raise ValueError(f"G_DN_pa={G_DN_resolved!r} must be > 0.")

    # 4. u_crit and Q_max.
    u_crit = K_geom * G_DN_resolved * d32_resolved * d32_resolved / (mu * L)
    Q_max = u_crit * A
    Q_recommended = 0.5 * Q_max

    # 5. ΔP_predicted at Q_set (one-shot KC; B-2g adds iteration).
    # Compose a temporary geometry with the resolved d32 so KC sees the
    # right diameter regardless of whether the caller's column was
    # constructed with d50 (legacy path) or d32 (post-B-1g).
    eps = column.bed_porosity
    u_set = column.superficial_velocity(Q_set_m3_s)
    dP_bed = (
        150.0 * mu * u_set * L * (1.0 - eps) ** 2
        / (d32_resolved ** 2 * eps ** 3)
    )

    # 6. Frit contribution (zero when not configured).
    dP_frit = column.frit_pressure_drop(Q_set_m3_s, mu=mu)
    dP_predicted = dP_bed + dP_frit

    # 7. Operational ceiling and structural ceiling.
    dP_max_operational = (
        150.0 * mu * u_crit * L * (1.0 - eps) ** 2
        / (d32_resolved ** 2 * eps ** 3)
    )
    dP_max_burst = E_star_resolved  # structural diagnostic ONLY

    # 8. Tier rollup.
    violations = check_valid_domain(
        family_kgeom,
        bead_d32_m=d32_resolved,
        bed_height_m=L,
        T_C=mobile_phase.T_C,
        mu_pa_s=mu,
        G_DN_pa=G_DN_resolved,
    )
    decision_tier = base_tier
    demote_steps = 0
    if violations:
        demote_steps += 1
    if viscosity.extrapolated:
        demote_steps += 1
    if demote_steps > 0:
        decision_tier = _demote_tier(decision_tier, demote_steps)

    # 9. Intervals at the resolved tier.
    dP_predicted_interval = _interval(dP_predicted, decision_tier)
    dP_max_operational_interval = _interval(dP_max_operational, decision_tier)

    # Calibration provenance map.
    provenance: dict[str, str] = {
        "K_geom": K_geom_source,
        "K_geom_anchor": family_kgeom.literature_anchor,
        "viscosity_method": viscosity.method,
        "viscosity_tier": viscosity.tier.value,
        "family_base_tier": family_kgeom.base_tier.value,
    }
    if viscosity.extrapolated:
        provenance["viscosity_flag"] = "extrapolated"

    # Notes — tier-rollup explanations.
    notes: list[str] = []
    if violations:
        notes.append(
            f"valid_domain violations ({len(violations)}): "
            + "; ".join(violations)
        )
    if viscosity.extrapolated:
        notes.append(f"viscosity extrapolated: {viscosity.notes}")
    if K_geom_source == "family_default":
        notes.append(
            "K_geom from family_default literature anchor — "
            "supply manufacturer pressure-flow curve via calibration_store "
            "to promote to CALIBRATED_LOCAL render."
        )

    return PressureEnvelope(
        polymer_family=polymer_family,
        mobile_phase=mobile_phase,
        Q_set_m3_s=float(Q_set_m3_s),
        bed_height_m=float(L),
        column_diameter_m=float(column.diameter),
        bead_d32_m=float(d32_resolved),
        bed_porosity=float(eps),
        G_DN_pa=float(G_DN_resolved),
        E_star_pa=float(E_star_resolved),
        viscosity=viscosity,
        dP_predicted_pa=float(dP_predicted),
        dP_predicted_interval_pa=dP_predicted_interval,
        dP_frit_pa=float(dP_frit),
        dP_max_operational_pa=float(dP_max_operational),
        dP_max_operational_interval_pa=dP_max_operational_interval,
        dP_max_burst_pa=float(dP_max_burst),
        u_crit_m_s=float(u_crit),
        Q_max_m3_s=float(Q_max),
        Q_recommended_m3_s=float(Q_recommended),
        K_geom_used=float(K_geom),
        K_geom_source=K_geom_source,
        decision_tier=decision_tier,
        valid_domain_violations=violations,
        calibration_provenance=provenance,
        notes=tuple(notes),
    )
