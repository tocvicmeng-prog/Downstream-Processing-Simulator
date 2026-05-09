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
        """Maximum flow rate before exceeding bead crushing pressure [m^3/s].

        The crushing pressure is taken as the effective Young's modulus
        (E_star) scaled by the safety factor.  Inverting Kozeny-Carman:

            Q_max = safety * E_star * dp^2 * eps^3 * A
                    / (150 * mu * L * (1-eps)^2)

        Args:
            mu: Dynamic viscosity [Pa.s].
            safety: Safety factor (0-1, default 0.8).

        Returns:
            Maximum safe volumetric flow rate [m^3/s].
        """
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

