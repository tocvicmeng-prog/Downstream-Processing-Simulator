"""Kozeny-Carman pressure drop and bed compressibility for packed columns.

Architecture: docs/13_module2_module3_final_implementation_plan.md, Phase C.

Models the hydraulic resistance of a packed bed of porous microspheres,
including mechanical compressibility feedback from the double-network
shear modulus (G_DN) and effective Young's modulus (E_star) inherited
from Module 1 / Module 2.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Optional


logger = logging.getLogger(__name__)


@dataclass
class ColumnGeometry:
    """Packed column geometry and hydraulic properties.

    Default values represent a typical analytical-scale column packed
    with 100 um hydrogel microspheres at 38% bed porosity.

    Attributes:
        diameter: Column inner diameter [m].
        bed_height: Packed bed height [m].
        particle_diameter: Sauter mean particle diameter d32 [m] from M1
            (post-B-1g). Use ``M1ExportContract.bead_d32``, not d50,
            because Kozeny-Carman / Ergun derive from the surface-area-
            equivalent diameter — see ``_column_with_microsphere``.
        bed_porosity: Inter-particle void fraction [-].
        particle_porosity: Intra-particle porosity [-].
        G_DN: Double-network shear modulus [Pa] from M1/M2.
        E_star: Effective Young's modulus [Pa] from M1/M2.
        frit_permeability_m2: Optional frit Darcy permeability [m^2]
            (B-1g / W-024). When set together with ``frit_thickness_m``,
            ``frit_pressure_drop`` adds a series resistance
            ΔP_frit = μ·u·t/k_f to the Kozeny-Carman bed contribution.
            For a typical 10 µm sintered PE frit, k_f ≈ 1×10⁻¹³ m².
            Default ``None`` → no frit contribution (backwards compat).
        frit_thickness_m: Optional frit thickness [m]. Both this and
            ``frit_permeability_m2`` must be set (non-``None``) for the
            frit contribution to be non-zero.
    """

    diameter: float = 0.01           # [m]
    bed_height: float = 0.10         # [m]
    particle_diameter: float = 100e-6  # [m]
    bed_porosity: float = 0.38       # [-]
    particle_porosity: float = 0.70  # [-]
    G_DN: float = 10000.0            # [Pa]
    E_star: float = 30000.0          # [Pa]
    frit_permeability_m2: Optional[float] = None  # [m^2]
    frit_thickness_m: Optional[float] = None      # [m]

    @property
    def cross_section_area(self) -> float:
        """Column cross-section area [m^2]."""
        return math.pi / 4.0 * self.diameter ** 2

    @property
    def bed_volume(self) -> float:
        """Total bed volume [m^3]."""
        return self.cross_section_area * self.bed_height

    @property
    def particle_radius(self) -> float:
        """Particle radius [m]."""
        return self.particle_diameter / 2.0

    def superficial_velocity(self, flow_rate: float) -> float:
        """Superficial velocity u = Q / A_cross [m/s].

        Args:
            flow_rate: Volumetric flow rate [m^3/s].
        """
        return flow_rate / self.cross_section_area

    def frit_pressure_drop(self, flow_rate: float, mu: float = 1e-3) -> float:
        """Frit / distributor series-resistance pressure drop [Pa].

        B-1g (W-024, v0.7.0): adds the Darcy-permeability contribution
        ΔP_frit = μ · u · t_frit / k_f when both ``frit_permeability_m2``
        and ``frit_thickness_m`` are set on the geometry. Returns 0.0
        when either field is ``None``, preserving backwards compatibility
        for callers that do not specify a frit.

        On small analytical columns at high flow rates, the frit can
        contribute 10–30 % of the total bed ΔP and must not be ignored
        when computing the operational pressure envelope.

        Args:
            flow_rate: Volumetric flow rate [m^3/s].
            mu: Dynamic viscosity [Pa.s] (default: water at 20 °C).
                In v0.7.0, callers should resolve μ via
                :func:`dpsim.core.viscosity.resolve_mobile_phase_viscosity`
                (B-1f / W-023) rather than relying on this default.

        Returns:
            Frit pressure drop [Pa] (≥ 0). Returns 0.0 when no frit is
            configured.
        """
        if self.frit_permeability_m2 is None or self.frit_thickness_m is None:
            return 0.0
        if self.frit_permeability_m2 <= 0.0 or self.frit_thickness_m < 0.0:
            raise ValueError(
                f"frit_permeability_m2={self.frit_permeability_m2!r}, "
                f"frit_thickness_m={self.frit_thickness_m!r} — "
                "permeability must be > 0 and thickness must be ≥ 0."
            )
        u = self.superficial_velocity(flow_rate)
        return mu * u * self.frit_thickness_m / self.frit_permeability_m2

    def pressure_drop(self, flow_rate: float, mu: float = 1e-3) -> float:
        """Kozeny-Carman pressure drop across the packed bed [Pa].

        dP = 150 * mu * u * L * (1 - eps)^2 / (dp^2 * eps^3)

        Note: this method covers the bed contribution only. The frit /
        distributor series resistance is in :meth:`frit_pressure_drop`;
        ``compute_pressure_envelope`` (B-2f) sums the two for the total
        column ΔP.

        Args:
            flow_rate: Volumetric flow rate [m^3/s].
            mu: Dynamic viscosity [Pa.s] (default: water at 20 C).

        Returns:
            Pressure drop [Pa] (positive value).
        """
        u = self.superficial_velocity(flow_rate)
        eps = self.bed_porosity
        dp = self.particle_diameter
        L = self.bed_height

        dP = 150.0 * mu * u * L * (1.0 - eps) ** 2 / (dp ** 2 * eps ** 3)
        return dP

    def max_safe_flow_rate(self, mu: float = 1e-3, safety: float = 0.8) -> float:
        """**DEPRECATED — use pressure_envelope.compute_pressure_envelope.**

        B-2f (W-020, v0.7.0): this method anchors ΔP_max to
        ``safety × E_star`` (the bursting modulus). For soft
        chromatography media the *operational* limit is set by
        bed-compression u_crit, not by bead bursting; the two are
        physically distinct and u_crit is typically 5–50× lower than
        the bursting limit. Using this method silently underestimates
        bead-crush risk by that factor.

        Replacement: build a :class:`MobilePhase` for the recipe step
        and call
        :func:`dpsim.module3_performance.pressure_envelope.compute_pressure_envelope`,
        then read ``PressureEnvelope.Q_max_m3_s`` (the u_crit-based
        operational ceiling, family-aware via the K_geom registry).

        This method is retained for one release with a
        ``DeprecationWarning`` and will be removed in v0.8. The
        formula here is preserved as the **structural** (bursting)
        ceiling, not the operational one — call sites that genuinely
        need the bursting bound should consume
        ``PressureEnvelope.dP_max_burst_pa`` instead.

        Args:
            mu: Dynamic viscosity [Pa.s].
            safety: Safety factor (0-1, default 0.8).

        Returns:
            Maximum flow rate before bead bursting [m^3/s] — NOT the
            operational ceiling.
        """
        import warnings
        warnings.warn(
            "ColumnGeometry.max_safe_flow_rate is deprecated as of v0.7.0 "
            "(B-2f / W-020). The safety×E_star anchor is the bursting "
            "modulus, not the operational bed-compression ceiling. Use "
            "pressure_envelope.compute_pressure_envelope and read "
            "PressureEnvelope.Q_max_m3_s instead. Removed in v0.8.",
            DeprecationWarning,
            stacklevel=2,
        )
        eps = self.bed_porosity
        dp = self.particle_diameter
        L = self.bed_height
        A = self.cross_section_area

        # Max dP before crushing
        dP_max = safety * self.E_star

        # Invert Kozeny-Carman for u_max then Q_max = u_max * A
        u_max = dP_max * dp ** 2 * eps ** 3 / (150.0 * mu * L * (1.0 - eps) ** 2)
        return u_max * A

    def bed_compression_fraction(self, delta_P: float) -> float:
        """Fractional bed compression under pressure drop.

        delta_L / L = dP / (E_star * (1 - eps))

        Args:
            delta_P: Applied pressure drop [Pa].

        Returns:
            Fractional bed height reduction [-].
        """
        return delta_P / (self.E_star * (1.0 - self.bed_porosity))

    def kc_pressure_drop_at(
        self, flow_rate: float, eps: float, mu: float = 1e-3,
    ) -> float:
        """Kozeny-Carman pressure drop at a specified bed porosity [Pa].

        B-2g (W-022, v0.7.0): companion to :meth:`pressure_drop` that
        accepts an explicit ``eps`` argument so the iterated
        ε_b-feedback loop in
        :func:`iterate_kc_compression` can recompute ΔP after each
        compression update without mutating the dataclass.
        """
        u = self.superficial_velocity(flow_rate)
        return (
            150.0 * mu * u * self.bed_height * (1.0 - eps) ** 2
            / (self.particle_diameter ** 2 * eps ** 3)
        )

    def validate_flow_rate(self, flow_rate: float, mu: float = 1e-3) -> list[str]:
        """Check flow rate against mechanical and physical limits.

        Returns:
            List of warning messages (empty = OK).
        """
        warnings: list[str] = []
        dP = self.pressure_drop(flow_rate, mu)
        Q_max = self.max_safe_flow_rate(mu)

        if flow_rate > Q_max:
            warnings.append(
                f"BLOCKER: Flow rate {flow_rate:.2e} m^3/s exceeds max safe "
                f"{Q_max:.2e} m^3/s (dP={dP:.0f} Pa > E_star={self.E_star:.0f} Pa)"
            )

        compression = self.bed_compression_fraction(dP)
        if compression > 0.20:
            warnings.append(
                f"WARNING: Bed compression {compression:.1%} exceeds 20%."
            )

        # Reynolds number check (creeping flow assumption)
        u = self.superficial_velocity(flow_rate)
        rho = 1000.0  # water density
        Re_p = rho * u * self.particle_diameter / (mu * (1.0 - self.bed_porosity))
        if Re_p > 10.0:
            warnings.append(
                f"WARNING: Particle Re = {Re_p:.1f} > 10; Kozeny-Carman "
                f"assumes creeping flow."
            )

        return warnings


# ─── B-2g (W-022): ε_b iteration ────────────────────────────────────────────


# Floor for ε_b to prevent divide-by-zero in KC and to detect runaway.
_EPS_B_FLOOR: float = 0.10


@dataclass(frozen=True)
class IterationResult:
    """Result of the iterated KC + bed-compression fixed point.

    B-2g (W-022, v0.7.0). Companion value type for
    :func:`iterate_kc_compression`. ``compute_pressure_envelope``
    (B-2f) consumes ``dP_pa`` as the iterated ΔP_predicted; the
    ``converged`` flag drives a tier downgrade when the iteration
    diverged (typically meaning the operating point is at or beyond
    u_crit, where bed-compression runaway is real).

    Attributes
    ----------
    dP_pa :
        Final ΔP across the bed [Pa] at the converged ε_b.
    eps_b_final :
        Compressed bed porosity after iteration. Floored at
        ``_EPS_B_FLOOR`` (= 0.10) to prevent divide-by-zero in KC.
    n_iter :
        Number of iterations executed (capped at ``max_iter``).
    converged :
        ``True`` when |ε_b_new − ε_b_prev| < ``tol`` within
        ``max_iter`` steps. ``False`` indicates either ε_b hit the
        floor (runaway) or iteration ceiling reached without
        convergence.
    """

    dP_pa: float
    eps_b_final: float
    n_iter: int
    converged: bool


def iterate_kc_compression(
    geometry: ColumnGeometry,
    flow_rate: float,
    mu: float,
    *,
    max_iter: int = 50,
    tol: float = 1e-4,
    relaxation: float = 0.5,
) -> IterationResult:
    """Iterate the (ε_b, ΔP) fixed point for KC + bed compression.

    B-2g / W-022 — Δ3 from the v0.7.0 M3 back-pressure work plan.
    Captures the runaway feedback near u_crit that the v0.6.6 one-shot
    formula missed:

        ΔP ↑ → δL/L ↑ → ε_b ↓ → ΔP ↑ (KC ∝ (1-ε)²/ε³)

    Volumetric model
    ----------------
    Total compression δL/L is the *cumulative* state. From the
    small-strain elastic approximation (consistent with v0.6.6
    ``bed_compression_fraction``):

        δL/L = ΔP(ε_b_current) / (E_star · (1 − ε_b_current))

    where the current compressed porosity is recovered from a fixed
    fresh-packed state ε_b_0 by the volumetric balance:

        (1 − ε_b) = (1 − ε_b_0) / (1 − δL/L)

    Picard iteration on this fixed point is mathematically unstable for
    soft chromatography media (the gain dF/dε_b exceeds 1 at the fixed
    point because KC's (1−ε)²/ε³ factor is highly nonlinear). The
    ``relaxation`` parameter under-relaxes the ε_b update:

        ε_b_new = (1 − α) · ε_b_target + α · ε_b_prev   (α = relaxation)

    Default α = 0.5. Lower α (closer to 0) → faster but less stable;
    higher α (closer to 1) → slower but more stable. The iteration
    terminates when |ε_b_new − ε_b_prev| < tol or ``max_iter`` is
    reached. ε_b is floored at 0.10 to detect runaway: when the floor
    is hit, ``converged = False`` and downstream tier rollup demotes
    one step.

    For smooth-flow operating points (well below u_crit), the iteration
    converges in 2–5 steps to a slightly-compressed steady state and
    agrees with the one-shot KC to within ~1 %. Near u_crit, the
    iteration either converges to a heavily-compressed steady-state
    (converged = True) or diverges to the ε_b_floor (converged = False).

    Parameters
    ----------
    geometry :
        ColumnGeometry. ``bed_porosity`` is the FRESH-packed value
        (typically 0.38); the iteration computes the compressed value.
    flow_rate :
        Volumetric flow rate [m³/s].
    mu :
        Dynamic viscosity [Pa·s].
    max_iter :
        Iteration ceiling. Default 50.
    tol :
        Convergence tolerance on |Δε_b| between consecutive iterates.
        Default 1×10⁻⁴.
    relaxation :
        Picard under-relaxation factor in [0, 1). Default 0.5.

    Returns
    -------
    IterationResult
        Iterated ΔP, final ε_b, iteration count, convergence flag.
    """
    if mu <= 0.0:
        raise ValueError(f"mu={mu!r} must be > 0.")
    if flow_rate < 0.0:
        raise ValueError(f"flow_rate={flow_rate!r} must be ≥ 0.")
    if geometry.E_star <= 0.0:
        raise ValueError(
            f"geometry.E_star={geometry.E_star!r} must be > 0 for compression "
            "feedback. Set a positive E_star (typically 3·G_DN for "
            "incompressible-rubber Poisson)."
        )
    if not (0.0 <= relaxation < 1.0):
        raise ValueError(f"relaxation={relaxation!r} must be in [0, 1).")

    eps_b_0 = geometry.bed_porosity     # fresh-packed; immutable reference state
    eps_b = eps_b_0                      # current iterate
    dP = geometry.kc_pressure_drop_at(flow_rate, eps_b, mu=mu)
    converged = False
    n_iter = 0

    # Cap per-iteration compression to stay in the small-strain regime
    # where the linear-elastic δL/L = ΔP/(E_star·(1-ε)) formula is
    # valid. Beyond this cap the formula systematically over-predicts
    # compression (Hertz nonlinearity ignored — see ADR-004 §"Out of
    # scope"). Hitting the cap repeatedly is a runaway signal.
    _COMPRESSION_CAP_PER_ITER: float = 0.03
    cap_hits: int = 0

    for n_iter in range(1, max_iter + 1):
        # Cumulative compression from the elastic restoring at current ε_b.
        compression = dP / (geometry.E_star * (1.0 - eps_b))

        # Detect immediate runaway: compression ≥ 90 % means the bed is
        # essentially gone in one step; floor ε_b and bail.
        if compression >= 0.90:
            eps_b = _EPS_B_FLOOR
            dP = geometry.kc_pressure_drop_at(flow_rate, eps_b, mu=mu)
            converged = False
            break

        # Cap per-iteration compression to the small-strain regime.
        if compression > _COMPRESSION_CAP_PER_ITER:
            compression = _COMPRESSION_CAP_PER_ITER
            cap_hits += 1

        # Volumetric balance from the FRESH-packed reference state.
        eps_b_target = max(_EPS_B_FLOOR, 1.0 - (1.0 - eps_b_0) / (1.0 - compression))

        # Under-relaxed update.
        eps_b_new = (1.0 - relaxation) * eps_b_target + relaxation * eps_b

        # Recompute ΔP at the updated ε_b.
        dP_new = geometry.kc_pressure_drop_at(flow_rate, eps_b_new, mu=mu)

        # Convergence check on ε_b.
        if abs(eps_b_new - eps_b) < tol:
            eps_b = eps_b_new
            dP = dP_new
            # If we needed the compression cap to converge, the operating
            # point is in a regime where the linear-elastic formula is
            # invalid — flag as non-converged for tier-rollup purposes.
            converged = cap_hits == 0 or cap_hits < 3
            break

        # Detect floor hit (runaway) — non-converged.
        if eps_b_new <= _EPS_B_FLOOR + 1e-12:
            eps_b = _EPS_B_FLOOR
            dP = dP_new
            converged = False
            break

        eps_b = eps_b_new
        dP = dP_new
    else:
        # Loop completed without break — max_iter reached.
        # If repeated cap hits, this is the runaway-saturation case.
        converged = False

    return IterationResult(
        dP_pa=float(dP),
        eps_b_final=float(eps_b),
        n_iter=n_iter,
        converged=converged,
    )
