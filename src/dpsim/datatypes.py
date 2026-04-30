"""Core data structures for the emulsification simulation pipeline.

Supports two hardware modes:
  - Legacy rotor-stator homogeniser (original, 2 µm target)
  - Stirred-vessel double-emulsification (new, 100 µm target)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import numpy as np


# ─── Platform / polymer family ───────────────────────────────────────────


class PolymerFamily(Enum):
    """Microsphere polymer family (Node F1-a, v8.0).

    Drives L2 gelation-solver dispatch. AGAROSE_CHITOSAN is the legacy
    v7.x platform (thermal TIPS + optional covalent crosslinking);
    ALGINATE uses diffusion-limited Ca²⁺ ionic gelation; CELLULOSE and
    PLGA are stubs for future F1-b / F1-c work.

    v9.2 additions (Tier-1; SA screening § 6.1):
        AGAROSE       — chitosan-free thermal-gelation agarose beads (M1)
        CHITOSAN      — agarose-free chitosan beads with pH-protonation model (M2)
        DEXTRAN       — Sephadex-class ECH-crosslinked dextran beads (M3)

    v9.2 placeholder enum members (data-only; not enabled in UI yet — Tier 2):
        HYALURONATE, KAPPA_CARRAGEENAN, AGAROSE_DEXTRAN, AGAROSE_ALGINATE,
        ALGINATE_CHITOSAN, AMYLOSE, CHITIN

    Per CLAUDE.md, ALWAYS compare PolymerFamily members by ``.value``,
    never by identity (``is``). The Streamlit app reloads ``dpsim.datatypes``
    on every rerun, minting a new enum class; identity comparisons silently
    break after the first rerun.
    """
    # v9.1 baseline (4)
    AGAROSE_CHITOSAN = "agarose_chitosan"
    ALGINATE = "alginate"
    CELLULOSE = "cellulose"
    PLGA = "plga"

    # v9.2 Tier-1 additions (3)
    AGAROSE = "agarose"
    CHITOSAN = "chitosan"
    DEXTRAN = "dextran"

    # v9.2 Tier-2 placeholders (data-only; is_enabled_in_ui = False)
    HYALURONATE = "hyaluronate"
    KAPPA_CARRAGEENAN = "kappa_carrageenan"
    AGAROSE_DEXTRAN = "agarose_dextran"
    AGAROSE_ALGINATE = "agarose_alginate"
    ALGINATE_CHITOSAN = "alginate_chitosan"
    AMYLOSE = "amylose"
    CHITIN = "chitin"

    # v9.4 Tier-3 additions (SA screening report § 6.3)
    PECTIN = "pectin"                       # galacturonic-acid Ca²⁺ ionic gelation
    GELLAN = "gellan"                       # K⁺/Ca²⁺ helix-aggregation
    PULLULAN = "pullulan"                   # neutral α-glucan; STMP / ECH crosslinked
    STARCH = "starch"                       # neutral α-glucan; degradation/brittleness flagged
    # v9.4 Tier-3 multi-variant composites (less common but documented in SA report)
    PECTIN_CHITOSAN = "pectin_chitosan"     # pectin-chitosan PEC
    GELLAN_ALGINATE = "gellan_alginate"     # gellan-alginate composite
    PULLULAN_DEXTRAN = "pullulan_dextran"   # pullulan-dextran composite


# ─── PolymerFamily metadata (v9.2 family-flag system) ───────────────────
#
# A2.1 + B9.1: per-family metadata flags that guard which families are
# rendered in the v9.0 Family-First UI and which carry the material-as-
# ligand pattern (amylose/chitin). Stored externally to the Enum so that
# the Enum itself stays a thin string-valued vocabulary (which preserves
# the `.value`-comparison reload semantics).

# Tier-1 v9.2 families that should appear in the M1 family selector.
# AMYLOSE is Tier-1 because B9 (material-as-ligand for MBP-tag) is in
# Tier-1 of the SA screening report.
#
# v9.3 Tier-2 promotions: HYALURONATE, KAPPA_CARRAGEENAN, AGAROSE_DEXTRAN,
# AGAROSE_ALGINATE, ALGINATE_CHITOSAN, CHITIN — promoted from data-only
# placeholders (v9.2) to UI-enabled (v9.3) as their L2 solvers and
# reagent profiles land. Each carries SEMI_QUANTITATIVE evidence tier
# pending wet-lab calibration (Q-013/Q-014).
_TIER1_UI_FAMILIES: frozenset[str] = frozenset({
    # v9.1 baseline
    PolymerFamily.AGAROSE_CHITOSAN.value,
    PolymerFamily.ALGINATE.value,
    PolymerFamily.CELLULOSE.value,
    PolymerFamily.PLGA.value,
    # v9.2 Tier-1 additions
    PolymerFamily.AGAROSE.value,
    PolymerFamily.CHITOSAN.value,
    PolymerFamily.DEXTRAN.value,
    PolymerFamily.AMYLOSE.value,        # M8 B9 material-as-ligand
    # v9.3 Tier-2 promotions (SA screening § 6.2)
    PolymerFamily.HYALURONATE.value,
    PolymerFamily.KAPPA_CARRAGEENAN.value,
    PolymerFamily.AGAROSE_DEXTRAN.value,
    PolymerFamily.AGAROSE_ALGINATE.value,
    PolymerFamily.ALGINATE_CHITOSAN.value,
    PolymerFamily.CHITIN.value,
    # v9.4 Tier-3 promotions (SA screening § 6.3) — niche / lower
    # bioprocess relevance, but UI-enabled with QUALITATIVE_TREND or
    # SEMI_QUANTITATIVE evidence and explicit "research-mode only"
    # warnings where appropriate.
    PolymerFamily.PECTIN.value,
    PolymerFamily.GELLAN.value,
    PolymerFamily.PULLULAN.value,
    PolymerFamily.STARCH.value,
    # v9.5 Tier-3 multi-variant composite promotions (SA screening § 6.4) —
    # promoted from data-only placeholder status. Each carries
    # QUALITATIVE_TREND evidence pending composite-specific wet-lab data;
    # constituents are independently UI-enabled.
    PolymerFamily.PECTIN_CHITOSAN.value,
    PolymerFamily.GELLAN_ALGINATE.value,
    PolymerFamily.PULLULAN_DEXTRAN.value,
})

# Families where the polymer IS the affinity matrix (B9 pattern).
_MATERIAL_AS_LIGAND_FAMILIES: frozenset[str] = frozenset({
    PolymerFamily.AMYLOSE.value,    # MBP affinity (v9.2 Tier-1)
    PolymerFamily.CHITIN.value,     # CBD/intein (v9.3 Tier-2 — UI promoted)
})


def is_family_enabled_in_ui(family: PolymerFamily) -> bool:
    """Return True if ``family`` should be rendered in the v9.0 Family-First UI.

    Tier-2 placeholder families return False; they exist as data-only enum
    members until their UI surface lands in v9.3.
    """
    return family.value in _TIER1_UI_FAMILIES


def is_material_as_ligand(family: PolymerFamily) -> bool:
    """Return True if ``family`` is itself an affinity matrix (B9 pattern).

    For these families, the polymer (e.g. amylose, chitin) IS the affinity
    ligand; M2 ligand-coupling steps are bypassed and replaced by
    competitive-eluent elution workflows in M3.
    """
    return family.value in _MATERIAL_AS_LIGAND_FAMILIES


# ─── Equipment Enums ─────────────────────────────────────────────────────

class VesselType(Enum):
    """Reaction vessel type for the double-emulsification process."""
    GLASS_BEAKER = "glass_beaker"
    JACKETED_VESSEL = "jacketed_vessel"


class StirrerType(Enum):
    """Stirrer/impeller type."""
    PITCHED_BLADE = "pitched_blade"             # Stirrer A — 19-tab disk impeller, ≤2500 RPM
    ROTOR_STATOR_SMALL = "rotor_stator_small"   # Stirrer B — small homogeniser, ≤9000 RPM
    ROTOR_STATOR_LEGACY = "rotor_stator_legacy" # Original 25 mm rotor-stator


class HeatingStrategy(Enum):
    """Heating/cooling strategy during emulsification."""
    FLAT_PLATE = "flat_plate"           # External hot plate (beaker only)
    HOT_WATER_JACKET = "hot_water_jacket"  # Circulating jacket (jacketed vessel only)
    ISOTHERMAL = "isothermal"           # Constant T_oil (legacy mode)


class ModelEvidenceTier(Enum):
    """Evidence quality tier for a model output.

    Every numeric result should carry an evidence tier indicating how
    much the prediction can be trusted for decision-making.
    Ordered from strongest to weakest.
    """
    VALIDATED_QUANTITATIVE = "validated_quantitative"
    """Calibrated against experimental data for this specific system."""

    CALIBRATED_LOCAL = "calibrated_local"
    """Calibrated against data from an analogous system."""

    SEMI_QUANTITATIVE = "semi_quantitative"
    """Empirical model, not locally calibrated. Trends reliable, magnitudes approximate."""

    QUALITATIVE_TREND = "qualitative_trend"
    """Directional predictions only. Numeric values are order-of-magnitude estimates."""

    UNSUPPORTED = "unsupported"
    """Model not applicable to this chemistry or regime. Output should not be used."""


class ModelMode(Enum):
    """Scientific operating mode for the simulation pipeline.

    Controls which model types are permitted and what claims are defensible.
    """
    EMPIRICAL_ENGINEERING = "empirical_engineering"
    """Fast screening. Calibration-driven. Only trend/ranking claims allowed."""

    HYBRID_COUPLED = "hybrid_coupled"
    """Main production mode. Empirical where evidence exists, mechanistic
    where coupling is defensible. Default."""

    MECHANISTIC_RESEARCH = "mechanistic_research"
    """Exploratory hypothesis-testing. Slower. Not for production decisions."""


# ─── Equipment Geometry Dataclasses ──────────────────────────────────────

@dataclass
class VesselGeometry:
    """Reaction vessel geometry.

    Working liquid = paraffin oil + polysaccharide solution + surfactant.
    """
    vessel_type: VesselType = VesselType.GLASS_BEAKER
    inner_diameter: float = 0.100       # [m]
    wall_thickness: float = 0.0015      # [m]
    height: float = 0.130               # [m]
    material: str = "borosilicate_glass"
    working_volume: float = 0.0005      # [m³] (500 mL default)
    working_volume_min: float = 0.00025 # [m³] (250 mL)
    working_volume_max: float = 0.0007  # [m³] (700 mL)

    @property
    def cross_section_area(self) -> float:
        """Internal cross-section area [m²]."""
        return np.pi / 4 * self.inner_diameter ** 2

    @property
    def liquid_height(self) -> float:
        """Height of working liquid in the vessel [m]."""
        return self.working_volume / self.cross_section_area

    @classmethod
    def glass_beaker(cls, working_volume: float = 0.0005) -> VesselGeometry:
        """Factory: standard glass beaker (Ø100 mm × 130 mm)."""
        return cls(
            vessel_type=VesselType.GLASS_BEAKER,
            inner_diameter=0.100,       # 10 cm
            wall_thickness=0.0015,      # 1.5 mm
            height=0.130,               # 13 cm
            material="borosilicate_glass",
            working_volume=working_volume,
            working_volume_min=0.00025, # 250 mL
            working_volume_max=0.0007,  # 700 mL
        )

    @classmethod
    def jacketed_vessel(cls, working_volume: float = 0.0005) -> VesselGeometry:
        """Factory: jacketed glass vessel (Ø92 mm × 160 mm)."""
        return cls(
            vessel_type=VesselType.JACKETED_VESSEL,
            inner_diameter=0.092,       # 9.2 cm
            wall_thickness=0.002,       # 2 mm (inner + outer wall)
            height=0.160,               # 16 cm
            material="borosilicate_glass",
            working_volume=working_volume,
            working_volume_min=0.0002,  # 200 mL
            working_volume_max=0.0007,  # 700 mL
        )


@dataclass
class StirrerGeometry:
    """Stirrer/impeller geometry for the emulsification process.

    Dimensions from measurement photographs (2026-03-27).
    Supports pitched-blade (Stirrer A), small rotor-stator (Stirrer B),
    and legacy rotor-stator (original 25 mm) configurations.
    """
    stirrer_type: StirrerType = StirrerType.PITCHED_BLADE
    impeller_diameter: float = 0.059    # [m] outer diameter of active element
    shaft_diameter: float = 0.008       # [m]
    blade_count: int = 6                # [-] number of blades/fins
    blade_angle: float = 10.0           # [°] angle relative to tangent
    blade_thickness: float = 0.001      # [m]
    blade_height: float = 0.010         # [m] parallel to axis
    blade_length: float = 0.009         # [m] perpendicular to axis (fin length)
    power_number: float = 0.35          # [-] estimated for 10° pitched, alternately bent
    max_rpm: float = 2000.0             # [rev/min]
    # Rotor-stator specific fields (0 for open impellers)
    has_stator: bool = False
    stator_diameter: float = 0.0        # [m]
    gap_width: float = 0.0              # [m]
    wall_height: float = 0.0            # [m] outer wall height (Stirrer B)
    wall_thickness: float = 0.0         # [m] outer wall thickness
    perforation_diameter: float = 0.0   # [m] hole diameter in perforated stator
    # Computed from stirrer_type, not user-set
    dissipation_ratio: float = 5.0      # ε_max / ε_avg

    @property
    def tip_speed(self) -> float:
        """Maximum tip speed [m/s] at max_rpm."""
        return np.pi * self.impeller_diameter * self.max_rpm / 60.0

    @classmethod
    def pitched_blade_A(cls) -> StirrerGeometry:
        """Factory: Stirrer A — disk-style 19-tab impeller.

        Verified against 2026-03-27 measurement photos and 2026-05-01 CAD
        review (see cad/README.md):
          - Disk Ø59 mm × 1 mm thick, central shaft Ø8 mm
          - 19 tabs at the disk perimeter: 10 bent UP, 9 bent DOWN,
            alternating around the circumference
          - Each tab is bent perpendicular (90°) to the disk plane —
            creates a tangential-facing wall
          - Tab face has 10° tangential pitch from the radial line
            (fan-blade angle, drives flow on rotation; arrow on disk
            indicates rotation direction)
          - Tab dimensions: 9 mm tangential × 8.5 mm axial × 1 mm thick
          - Outer Ø 59 mm at the tip; total axial span 18 mm (top of UP
            tips to bottom of DOWN tips)
        """
        return cls(
            stirrer_type=StirrerType.PITCHED_BLADE,
            impeller_diameter=0.059,        # Ø59 mm outer (tip-to-tip)
            shaft_diameter=0.008,           # Ø8 mm
            blade_count=19,                 # 10 UP + 9 DOWN, alternating
            blade_angle=10.0,               # tangential pitch from radial
            blade_thickness=0.001,          # 1 mm sheet metal
            blade_height=0.0085,            # 8.5 mm axial (per 18 mm span)
            blade_length=0.009,             # 9 mm tangential width of tab
            # ASSUMPTION: Np ≈ 0.35 for small-angle (10°) tangentially-pitched
            # tabs in alternating axial direction. Literature Np for 45° PBT
            # is ~1.3; the disk-style 19-tab geometry with 10° fan pitch and
            # alternating up/down acts more like a flat disc turbine with
            # mixed axial pumping. Pending CFD validation (see cad/cfd/).
            power_number=0.35,
            max_rpm=2500.0,
            has_stator=False,
            dissipation_ratio=5.0,          # typical for open impellers
        )

    @classmethod
    def rotor_stator_B(cls) -> StirrerGeometry:
        """Factory: Stirrer B — small rotor-stator homogeniser.

        Measured dimensions:
          - Outer wall Ø32.03 mm, wall thickness 2.2 mm, wall height 18 mm
          - Cross blade root Ø8.5 mm, blade edge Ø25.7 mm, blade thickness 2 mm
          - Perforated outer wall with Ø3 mm holes
          - Closed top, open bottom — centrifugal ejection through peripheral holes
        """
        return cls(
            stirrer_type=StirrerType.ROTOR_STATOR_SMALL,
            impeller_diameter=0.0257,       # 25.7 mm cross-blade edge (active rotor)
            shaft_diameter=0.0085,          # 8.5 mm root diameter
            blade_count=4,                  # cross-shaped (4 arms)
            blade_angle=0.0,                # radial (cross blade)
            blade_thickness=0.002,          # 2 mm
            blade_height=0.018,             # 18 mm (outer wall height)
            blade_length=0.0,               # not applicable for cross-blade
            power_number=2.0,               # rotor-stator, estimated from Padron (2005)
            max_rpm=9000.0,
            has_stator=True,
            stator_diameter=0.03203,        # 32.03 mm outer wall
            gap_width=(0.03203 - 0.0257) / 2,  # ~3.2 mm radial gap
            wall_height=0.018,              # 18 mm
            wall_thickness=0.0022,          # 2.2 mm
            perforation_diameter=0.003,     # 3 mm holes
            dissipation_ratio=25.0,         # intermediate: open perforations reduce confinement
        )

    @classmethod
    def rotor_stator_legacy(cls) -> StirrerGeometry:
        """Factory: original 25 mm rotor-stator (backward compatibility)."""
        return cls(
            stirrer_type=StirrerType.ROTOR_STATOR_LEGACY,
            impeller_diameter=0.025,
            shaft_diameter=0.008,
            blade_count=4,
            blade_angle=0.0,
            blade_thickness=0.001,
            blade_height=0.010,
            blade_length=0.0,
            power_number=1.5,
            max_rpm=25000.0,
            has_stator=True,
            stator_diameter=0.026,
            gap_width=0.0005,
            wall_height=0.010,
            wall_thickness=0.001,
            perforation_diameter=0.0,
            dissipation_ratio=50.0,
        )


@dataclass
class HeatingConfig:
    """Heating/cooling configuration during emulsification.

    Empirical calibration data:
      - Flat plate at 150°C → 300 mL oil/Span80 reaches 80°C steady state
      - After off: 500 mL cools 80°C → 20°C in ~1.5 hours
      - Jacket at 85°C circulating → 300 mL oil/Span80 reaches 80°C steady state
    """
    strategy: HeatingStrategy = HeatingStrategy.FLAT_PLATE
    heater_temperature: float = 423.15  # [K] (150°C for flat plate)
    T_initial: float = 353.15           # [K] (80°C — oil temp at mixing start)
    T_final: float = 293.15             # [K] (20°C — ambient)
    cooldown_time: float = 5400.0       # [s] (1.5 hours for 500 mL with flat plate)
    jacket_water_temperature: float = 358.15  # [K] (85°C circulating water)

    @classmethod
    def flat_plate(cls) -> HeatingConfig:
        """Factory: flat-plate heater (for glass beaker only)."""
        return cls(
            strategy=HeatingStrategy.FLAT_PLATE,
            heater_temperature=423.15,      # 150°C
            T_initial=353.15,               # 80°C
            T_final=293.15,                 # 20°C
            cooldown_time=5400.0,           # 1.5 h
        )

    @classmethod
    def hot_water_jacket(cls) -> HeatingConfig:
        """Factory: hot-water jacket (for jacketed vessel only)."""
        return cls(
            strategy=HeatingStrategy.HOT_WATER_JACKET,
            heater_temperature=0.0,         # not used
            T_initial=353.15,               # 80°C
            T_final=293.15,                 # 20°C
            cooldown_time=7200.0,           # ASSUMPTION: ~2 h for jacket cooling (slower)
            jacket_water_temperature=358.15,  # 85°C
        )

    @classmethod
    def isothermal(cls, T: float = 363.15) -> HeatingConfig:
        """Factory: constant temperature (legacy mode)."""
        return cls(
            strategy=HeatingStrategy.ISOTHERMAL,
            heater_temperature=0.0,
            T_initial=T,
            T_final=T,
            cooldown_time=0.0,
        )


# ─── Kernel Configuration ────────────────────────────────────────────────

class BreakageModel(Enum):
    """Breakage kernel model selection."""
    ALOPAEUS = "alopaeus"               # Alopaeus et al. — suited for rotor-stator
    COULALOGLOU_TAVLARIDES = "coulaloglou_tavlarides"  # CT (1977) original — suited for stirred vessels


class CoalescenceModel(Enum):
    """Coalescence kernel model selection."""
    COULALOGLOU_TAVLARIDES = "coulaloglou_tavlarides"  # Standard CT coalescence


@dataclass
class KernelConfig:
    """Breakage and coalescence kernel configuration.

    Constants are system-dependent.  Factory methods provide calibrated
    defaults for each stirrer type.

    Uncertainty bands (Liao & Lucas, 2009 review):
      - Alopaeus C1: [0.5, 2.0] (default 0.986)
      - Alopaeus C2: [0.005, 0.03] (default 0.0115)
      - CT breakage C1: [0.003, 0.01] (default 0.00481)
      - CT breakage C2: [0.05, 0.15] (default 0.08)
      - CT coalescence C4: [1e-4, 5e-4] (default 2.17e-4)
      - CT coalescence C5: [1e13, 5e13] (default 2.28e13)
    These ranges span published values across different systems.
    Calibration against experimental DSD data is recommended.
    """
    breakage_model: BreakageModel = BreakageModel.ALOPAEUS
    coalescence_model: CoalescenceModel = CoalescenceModel.COULALOGLOU_TAVLARIDES
    # Breakage constants
    breakage_C1: float = 0.986          # [-] Alopaeus default; range [0.5, 2.0]
    breakage_C2: float = 0.0115         # [-] Alopaeus default; range [0.005, 0.03]
    breakage_C3: float = 0.0            # [-] Alopaeus viscous correction. Default 0.0: for aqueous
                                         # dispersed phases (mu_d ~ 0.01-0.1 Pa·s at emulsification T),
                                         # the viscous correction is physically negligible. The Vi cap
                                         # in breakage_rate_alopaeus() prevents exponential blowout for
                                         # any C3 > 0 value. Set C3 > 0 only for highly viscous
                                         # dispersed phases (mu_d > 1 Pa·s) after calibration.
    # Coalescence constants (Coulaloglou-Tavlarides)
    coalescence_C4: float = 2.17e-4     # [-]; range [1e-4, 5e-4]
    coalescence_C5: float = 2.28e13     # [-]; range [1e13, 5e13]
    # Concentrated-emulsion correction
    phi_d_correction: bool = False       # enable coalescence damping
    coalescence_exponent: int = 1        # coalescence ~ 1/(1+phi_d)^n; n=1 legacy, n=2 recommended for phi_d>0.3

    @classmethod
    def for_rotor_stator_legacy(cls) -> KernelConfig:
        """Factory: original rotor-stator calibration (Alopaeus breakage).

        F1 fix (2026-04-17): phi_d_correction and coalescence_exponent=2 are
        now enabled to match the for_rotor_stator_small preset. With them
        disabled (the prior default), high-RPM runs at viscous-dispersed-phase
        conditions exhibited a nonphysical d32 increase with RPM because
        coalescence damping `exp(-C5*mu_c*rho*eps/sigma^2 * d_h^4)` collapses
        for small d_h and the bare CT collision frequency dominates. The
        crowding correction `1/(1+phi_d)^2` adds the missing damping at small
        scales without changing the well-behaved behaviour at low RPM.
        """
        return cls(
            breakage_model=BreakageModel.ALOPAEUS,
            breakage_C1=0.986,
            breakage_C2=0.0115,
            breakage_C3=0.0,                # disabled for aqueous dispersed phases (Vi cap handles high-mu_d)
            coalescence_C4=2.17e-4,
            coalescence_C5=2.28e13,
            phi_d_correction=True,
            coalescence_exponent=2,
        )

    @classmethod
    def for_pitched_blade(cls) -> KernelConfig:
        """Factory: stirred-vessel with pitched-blade impeller.

        Uses Alopaeus breakage kernel (with viscous sub-range correction)
        instead of CT, because at typical stirred-vessel conditions
        d_mode ~ eta_K (Kolmogorov scale), placing droplets in the
        viscous/transitional breakage regime where the CT inertial
        assumption (d >> eta_K) breaks down.

        Alopaeus C1/C2 are reduced from the rotor-stator defaults to
        reflect the lower turbulent intensity in stirred vessels.

        Coalescence exponent n=2 for concentrated emulsions (phi_d~0.40).
        """
        return cls(
            breakage_model=BreakageModel.ALOPAEUS,
            breakage_C1=0.04,               # reduced ~25x from rotor-stator (0.986)
            breakage_C2=0.0115,             # Alopaeus default surface-tension term
            breakage_C3=2.0,                # strong viscous correction: suppresses breakage of small droplets
            coalescence_C4=2.17e-4,
            coalescence_C5=2.28e13,
            phi_d_correction=True,
            coalescence_exponent=2,         # 1/(1+phi_d)^2 for phi_d~0.40
        )

    @classmethod
    def for_rotor_stator_small(cls) -> KernelConfig:
        """Factory: small rotor-stator (Stirrer B) — intermediate calibration."""
        return cls(
            breakage_model=BreakageModel.ALOPAEUS,
            breakage_C1=0.986,
            breakage_C2=0.0115,
            breakage_C3=0.0,
            coalescence_C4=2.17e-4,
            coalescence_C5=2.28e13,
            phi_d_correction=True,
            coalescence_exponent=2,
        )

    @classmethod
    def for_stirrer_type(cls, stirrer_type: StirrerType) -> KernelConfig:
        """Select kernel config based on stirrer type."""
        _dispatch = {
            StirrerType.PITCHED_BLADE: cls.for_pitched_blade,
            StirrerType.ROTOR_STATOR_SMALL: cls.for_rotor_stator_small,
            StirrerType.ROTOR_STATOR_LEGACY: cls.for_rotor_stator_legacy,
        }
        return _dispatch[stirrer_type]()


# ─── Simulation Parameters ───────────────────────────────────────────────

@dataclass
class MixerGeometry:
    """Rotor-stator mixer geometry (legacy — kept for backward compatibility).

    New code should use StirrerGeometry + VesselGeometry instead.
    """
    rotor_diameter: float = 0.025       # [m] (25 mm default)
    stator_diameter: float = 0.026      # [m]
    gap_width: float = 0.0005           # [m] (0.5 mm)
    tank_volume: float = 0.0005         # [m³] (500 mL)
    power_number: float = 1.5           # [-]
    dissipation_ratio: float = 50.0     # ε_max / ε_avg


@dataclass
class EmulsificationParameters:
    """Process parameters for Level 1.

    Supports two modes:
      - Legacy: uses ``mixer`` (MixerGeometry) — rotor-stator at 10,000 RPM
      - Stirred-vessel: uses ``vessel``, ``stirrer``, ``heating``, ``kernels``
    The ``mode`` field selects which set of fields the solver reads.
    """
    mode: str = "rotor_stator_legacy"   # "rotor_stator_legacy" or "stirred_vessel"
    rpm: float = 10000.0                # [rev/min]
    t_emulsification: float = 60.0      # [s]
    # Legacy fields
    mixer: MixerGeometry = field(default_factory=MixerGeometry)
    # New stirred-vessel fields
    vessel: Optional[VesselGeometry] = None
    stirrer: Optional[StirrerGeometry] = None
    heating: Optional[HeatingConfig] = None
    kernels: Optional[KernelConfig] = None

    def __post_init__(self) -> None:
        """Auto-populate stirred-vessel fields if mode is set."""
        if self.mode == "stirred_vessel":
            if self.vessel is None:
                self.vessel = VesselGeometry.glass_beaker()
            if self.stirrer is None:
                self.stirrer = StirrerGeometry.pitched_blade_A()
            if self.heating is None:
                # Pick vessel-compatible heating strategy
                if (self.vessel is not None
                        and getattr(self.vessel.vessel_type, 'value', '') == "jacketed_vessel"):
                    self.heating = HeatingConfig.hot_water_jacket()
                else:
                    self.heating = HeatingConfig.flat_plate()
            if self.kernels is None:
                self.kernels = KernelConfig.for_stirrer_type(
                    self.stirrer.stirrer_type
                )

    @property
    def effective_tank_volume(self) -> float:
        """Tank volume [m³] from either legacy mixer or new vessel."""
        if self.mode == "stirred_vessel" and self.vessel is not None:
            return self.vessel.working_volume
        return self.mixer.tank_volume

    @property
    def effective_impeller_diameter(self) -> float:
        """Impeller/rotor diameter [m] from either legacy or new stirrer."""
        if self.mode == "stirred_vessel" and self.stirrer is not None:
            return self.stirrer.impeller_diameter
        return self.mixer.rotor_diameter

    @property
    def effective_power_number(self) -> float:
        """Power number [-] from either legacy or new stirrer."""
        if self.mode == "stirred_vessel" and self.stirrer is not None:
            return self.stirrer.power_number
        return self.mixer.power_number

    @property
    def effective_dissipation_ratio(self) -> float:
        """ε_max / ε_avg from either legacy or new stirrer."""
        if self.mode == "stirred_vessel" and self.stirrer is not None:
            return self.stirrer.dissipation_ratio
        return self.mixer.dissipation_ratio


@dataclass
class FormulationParameters:
    """Chemical formulation parameters.

    In stirred-vessel mode, the surfactant concentration and dispersed-phase
    volume fraction are computed from volumetric quantities (v_oil_span80_mL,
    v_polysaccharide_mL, c_span80_vol_pct).
    """
    c_agarose: float = 42.0             # [kg/m³] (4.2% w/v)
    c_chitosan: float = 18.0            # [kg/m³] (1.8% w/v)
    c_alginate: float = 0.0             # [kg/m³] Node F1-a; 0 = not-alginate
    phi_cellulose_0: float = 0.0        # [-] Node F1-b; initial cellulose vol. fraction
    solvent_system: str = ""            # [Node F1-b] cellulose solvent preset key; "" = skip
    phi_PLGA_0: float = 0.0             # [-] Node F1-c; initial PLGA vol. fraction in droplet
    plga_grade: str = ""                # [Node F1-c] PLGA grade preset key ("" = skip)
    c_span80: float = 20.0              # [kg/m³] (~2% w/v)
    c_genipin: float = 2.0              # [mol/m³] (~2 mM)
    c_Ca_bath: float = 100.0            # [mol/m³] Node F1-a; external CaCl₂ bath
    T_oil: float = 363.15              # [K] (90°C)
    cooling_rate: float = 0.167         # [K/s] (~10°C/min)
    T_crosslink: float = 310.15         # [K] (37°C)
    t_crosslink: float = 86400.0        # [s] (24 hours)
    phi_d: float = 0.05                 # [-] dispersed phase volume fraction
    pH: float = 7.0                     # [-] reaction pH (Node 31; EDC/NHS + future pH-dependent chemistries)
    # ── Stirred-vessel volumetric fields ──
    c_span80_vol_pct: float = 1.5       # [% v/v] Span-80 in paraffin oil
    v_oil_span80_mL: float = 300.0      # [mL] volume of oil + Span-80 mixture
    v_polysaccharide_mL: float = 200.0  # [mL] max volume of polysaccharide solution
    # ── M1 post-gel washing / oil-removal model ──
    m1_initial_oil_carryover_fraction: float = 0.10  # [-] oil retained after bead collection, before washes
    m1_wash_cycles: int = 3                          # [-] discrete drain/resuspend wash cycles
    m1_wash_volume_ratio: float = 3.0                 # [-] wash liquid volume per wet bead/slurry volume
    m1_wash_mixing_efficiency: float = 0.80           # [-] approach to well-mixed extraction per cycle
    m1_oil_retention_factor: float = 1.0              # [-] larger = oil harder to extract
    m1_surfactant_retention_factor: float = 1.5       # [-] larger = surfactant harder to extract
    # ── v9.2 Q-010: dextran-ECH crosslink-density parameter ──
    # ECH:OH molar ratio for the DEXTRAN family L2 solver. Sephadex
    # G-class baselines: G-25 ≈ 0.15 (high crosslink), G-100 ≈ 0.10,
    # G-200 ≈ 0.04 (low crosslink). Default 0.0 means "use Sephadex
    # G-100 baseline" via the dextran solver's getattr fallback. Range
    # validated by the solver as [0.02, 0.30] before tier degrades to
    # QUALITATIVE_TREND. See `level2_gelation/dextran_ech.py`.
    ech_oh_ratio_dextran: float = 0.0    # [-] dextran ECH:OH ratio; 0 = Sephadex G-100 default

    @property
    def agarose_fraction(self) -> float:
        """Agarose mass fraction in polymer blend."""
        total = self.c_agarose + self.c_chitosan
        if total == 0:
            return 0.0
        return self.c_agarose / total

    @property
    def total_polymer(self) -> float:
        """Total polymer concentration [kg/m³]."""
        return self.c_agarose + self.c_chitosan

    @property
    def c_span80_from_vol_pct(self) -> float:
        """Span-80 concentration [kg/m^3] derived from volumetric %.

        c_span80 = rho_span80 * (vol_pct / 100)
        where rho_span80 ~ 986 kg/m^3 (Sigma-Aldrich).
        """
        RHO_SPAN80 = 986.0  # [kg/m^3]
        return RHO_SPAN80 * self.c_span80_vol_pct / 100.0

    @property
    def total_working_volume_mL(self) -> float:
        """Total working liquid volume [mL]."""
        return self.v_oil_span80_mL + self.v_polysaccharide_mL

    @property
    def phi_d_from_volumes(self) -> float:
        """Dispersed-phase volume fraction computed from volumetric quantities.

        In W/O emulsion: polysaccharide solution is the dispersed phase.
        """
        total = self.total_working_volume_mL
        if total <= 0:
            return 0.0
        return self.v_polysaccharide_mL / total


@dataclass
class SolverSettings:
    """Numerical solver settings."""
    # Level 1
    l1_n_bins: int = 20
    l1_d_min: float = 1e-6             # [m]
    l1_d_max: float = 500e-6           # [m] (must exceed premix d32 by ≥3σ)
    l1_rtol: float = 1e-6
    l1_atol: float = 1e-8
    # Level 2
    l2_n_r: int = 1000
    l2_n_grid: int = 128               # 2D grid side length (N×N)
    l2_dt_initial: float = 1e-4        # [s]
    l2_dt_max: float = 1.0             # [s]
    l2_arrest_exponent: float = 2.5
    # Level 3
    l3_method: str = "Radau"
    l3_rtol: float = 1e-8
    l3_atol: float = 1e-10
    # Level 1 adaptive convergence
    l1_t_max: float = 600.0            # [s] absolute max emulsification time for adaptive extensions
    l1_conv_tol: float = 0.01          # [-] relative d32 variation threshold for convergence
    l1_max_extensions: int = 2         # [-] max number of adaptive time extensions


@dataclass
class SimulationParameters:
    """Top-level parameter container for the full pipeline."""
    model_mode: ModelMode = ModelMode.HYBRID_COUPLED
    emulsification: EmulsificationParameters = field(default_factory=EmulsificationParameters)
    formulation: FormulationParameters = field(default_factory=FormulationParameters)
    solver: SolverSettings = field(default_factory=SolverSettings)
    run_id: str = ""
    notes: str = ""

    def validate(self) -> list[str]:
        """Validate parameters. Returns list of error messages (empty = valid)."""
        errors = []
        e = self.emulsification
        f = self.formulation
        s = self.solver

        # ── Common checks ──
        if e.rpm <= 0:
            errors.append(f"RPM must be positive, got {e.rpm}")
        if e.t_emulsification <= 0:
            errors.append("Emulsification time must be positive")
        if f.c_agarose < 0:
            errors.append("c_agarose must be non-negative")
        if f.c_chitosan < 0:
            errors.append("c_chitosan must be non-negative")
        if f.c_span80 < 0:
            errors.append("c_span80 must be non-negative")
        if f.c_genipin < 0:
            errors.append("c_genipin must be non-negative")
        if f.T_oil <= 0:
            errors.append(f"T_oil must be positive (Kelvin), got {f.T_oil}")
        if f.T_crosslink <= 0:
            errors.append(f"T_crosslink must be positive (Kelvin), got {f.T_crosslink}")
        if f.cooling_rate <= 0:
            errors.append("cooling_rate must be positive")
        if f.t_crosslink <= 0:
            errors.append("t_crosslink must be positive")
        if not (0 < f.phi_d < 1):
            errors.append(f"phi_d must be in (0, 1), got {f.phi_d}")
        if not (0.0 <= f.m1_initial_oil_carryover_fraction <= 1.0):
            errors.append("m1_initial_oil_carryover_fraction must be in [0, 1]")
        if f.m1_wash_cycles < 0:
            errors.append("m1_wash_cycles must be non-negative")
        if f.m1_wash_volume_ratio < 0.0:
            errors.append("m1_wash_volume_ratio must be non-negative")
        if not (0.0 <= f.m1_wash_mixing_efficiency <= 1.0):
            errors.append("m1_wash_mixing_efficiency must be in [0, 1]")
        if f.m1_oil_retention_factor <= 0.0:
            errors.append("m1_oil_retention_factor must be positive")
        if f.m1_surfactant_retention_factor <= 0.0:
            errors.append("m1_surfactant_retention_factor must be positive")
        if s.l1_n_bins < 5:
            errors.append("l1_n_bins must be >= 5")
        if s.l1_d_min <= 0:
            errors.append("l1_d_min must be positive")
        if s.l1_d_max <= s.l1_d_min:
            errors.append("l1_d_max must exceed l1_d_min")

        # ── Mode-specific checks ──
        if e.mode == "rotor_stator_legacy":
            m = e.mixer
            if m.gap_width <= 0:
                errors.append("Mixer gap_width must be positive")
            if m.tank_volume <= 0:
                errors.append("Mixer tank_volume must be positive")
            if m.rotor_diameter <= 0:
                errors.append("Mixer rotor_diameter must be positive")

        elif e.mode == "stirred_vessel":
            # Stirrer must be populated
            if e.stirrer is None:
                errors.append("Stirred-vessel mode requires stirrer")
            else:
                if e.rpm > e.stirrer.max_rpm:
                    errors.append(
                        f"RPM {e.rpm} exceeds stirrer max {e.stirrer.max_rpm}"
                    )
                if e.stirrer.impeller_diameter <= 0:
                    errors.append("Stirrer impeller_diameter must be positive")
            # Vessel must be populated
            if e.vessel is None:
                errors.append("Stirred-vessel mode requires vessel")
            else:
                v = e.vessel
                if not (v.working_volume_min <= v.working_volume <= v.working_volume_max):
                    errors.append(
                        f"Working volume {v.working_volume*1e6:.0f} mL outside "
                        f"range [{v.working_volume_min*1e6:.0f}, "
                        f"{v.working_volume_max*1e6:.0f}] mL"
                    )
                if v.liquid_height > v.height:
                    errors.append(
                        f"Liquid height {v.liquid_height*1000:.1f} mm exceeds "
                        f"vessel height {v.height*1000:.0f} mm"
                    )
            # Heating-vessel compatibility
            if e.heating is not None and e.vessel is not None:
                h_val = getattr(e.heating.strategy, 'value', str(e.heating.strategy))
                v_val = getattr(e.vessel.vessel_type, 'value', str(e.vessel.vessel_type))
                if h_val == "flat_plate" and v_val != "glass_beaker":
                    errors.append(
                        "Flat-plate heating is only compatible with glass beaker"
                    )
                if h_val == "hot_water_jacket" and v_val != "jacketed_vessel":
                    errors.append(
                        "Hot-water jacket requires jacketed vessel"
                    )
            # Volumetric consistency
            total_mL = f.total_working_volume_mL
            if e.vessel is not None:
                vessel_mL = e.vessel.working_volume * 1e6
                if abs(total_mL - vessel_mL) > 1.0:  # tolerance 1 mL
                    errors.append(
                        f"Formulation volumes ({total_mL:.0f} mL) != "
                        f"vessel working volume ({vessel_mL:.0f} mL)"
                    )
        else:
            errors.append(
                f"Unknown emulsification mode: '{e.mode}'. "
                f"Use 'rotor_stator_legacy' or 'stirred_vessel'."
            )

        return errors

    def to_optimization_vector(self) -> np.ndarray:
        """Flatten to 7D vector for BoTorch."""
        return np.array([
            self.emulsification.rpm,
            self.formulation.c_span80,
            self.formulation.agarose_fraction,
            self.formulation.T_oil,
            self.formulation.cooling_rate,
            self.formulation.c_genipin,
            self.formulation.t_crosslink,
        ])

    @classmethod
    def from_optimization_vector(
        cls, x: np.ndarray, template: SimulationParameters
    ) -> SimulationParameters:
        """Reconstruct from 7D vector + template for fixed params."""
        import copy
        params = copy.deepcopy(template)
        params.emulsification.rpm = float(x[0])
        params.formulation.c_span80 = float(x[1])
        # Reconstruct agarose/chitosan from fraction and total
        frac = float(x[2])
        total = params.formulation.total_polymer
        params.formulation.c_agarose = frac * total
        params.formulation.c_chitosan = (1.0 - frac) * total
        params.formulation.T_oil = float(x[3])
        params.formulation.cooling_rate = float(x[4])
        params.formulation.c_genipin = float(x[5])
        params.formulation.t_crosslink = float(x[6])
        return params


# ─── Material Properties ─────────────────────────────────────────────────

@dataclass
class PropertyValue:
    """A single material property with metadata."""
    value: float
    unit: str
    uncertainty: float = 0.0
    source: str = ""
    T_ref: float = 298.15              # [K]


@dataclass
class MaterialProperties:
    """Aggregated material properties for the simulation."""
    # Oil phase
    rho_oil: float = 850.0              # [kg/m³] at 20°C reference (interpolated to T_oil by PropertyDatabase)
    mu_oil: float = 0.005               # [Pa·s] at 90°C reference (interpolated to T_oil by PropertyDatabase)

    # Aqueous / dispersed phase
    rho_aq: float = 1020.0              # [kg/m³]
    mu_d: float = 1.0                   # [Pa·s] dispersed phase viscosity at T_oil

    # Interfacial
    sigma: float = 5.0e-3               # [N/m] interfacial tension with Span-80

    # Thermodynamic
    chi_0: float = 0.497                # Flory-Huggins χ at reference T
    chi_T_coeffs: tuple = (515.5, -0.720)  # (A, B) for χ(T) = A/T + B; spinodal ~325 K for Np=10
    kappa_CH: float = 5.0e-12           # [J/m] Cahn-Hilliard gradient coefficient
    M_0: float = 1.0e-9                # [m⁵/(J·s)] bare mobility (calibrated for 50-100 nm coarsening)

    # Gelation
    T_gel: float = 311.15               # [K] (~38°C)
    k_gel_0: float = 1.0                # [1/s] Avrami rate prefactor
    n_avrami: float = 2.5               # [-]
    gel_arrest_exponent: float = 2.5    # β

    # Crosslinking
    k_xlink_0: float = 2806.0          # [m³/(mol·s)] calibrated: k(37°C)=5e-3 L/(mol·s)
    E_a_xlink: float = 52000.0         # [J/mol]
    DDA: float = 0.90                   # degree of deacetylation
    M_GlcN: float = 161.16             # [g/mol] glucosamine molar mass
    M_genipin: float = 226.23          # [g/mol]

    # Agarose gel
    G_agarose_prefactor: float = 3000.0  # [Pa] at 1% w/v
    G_agarose_exponent: float = 2.2      # power law exponent

    # Crosslinking bridge efficiency
    f_bridge: float = 0.4              # fraction of genipin reactions producing elastically active crosslinks

    # IPN coupling
    eta_coupling: float = -0.15        # IPN coupling coefficient

    # Chitosan viscosity
    eta_intr_chit: float = 800.0       # [mL/g] intrinsic viscosity of chitosan

    # Shear-thinning (Cross model) — set to enable non-Newtonian dispersed phase
    cross_mu_0: float = 0.0       # [Pa.s] zero-shear viscosity (0 = disabled, use constant mu_d)
    cross_mu_inf: float = 0.001   # [Pa.s] infinite-shear viscosity
    cross_K: float = 0.01         # [s] relaxation time
    cross_n: float = 0.6          # [-] power-law index

    # Breakage kernel
    breakage_C3: float = 0.0           # [-] Alopaeus viscous correction. Default 0.0: for aqueous
                                        # dispersed phases (mu_d ~ 0.01-0.1 Pa·s at emulsification T),
                                        # the viscous correction is physically negligible. The Vi cap
                                        # in breakage_rate_alopaeus() prevents exponential blowout for
                                        # any C3 > 0. Set C3 > 0 only for highly viscous dispersed
                                        # phases (mu_d > 1 Pa·s) after calibration.

    # Network / pore
    r_fiber: float = 1.5e-9            # [m] agarose fiber radius

    # Surface carboxyl (Node 31): introduced by prior M2 steps (e.g.
    # succinylation of chitosan NH2 -> NH-CO-CH2-CH2-COOH). Zero on
    # native chitosan/agarose; non-zero gates L3 EDC/NHS to run the
    # mechanistic path instead of falling back to QUALITATIVE_TREND.
    surface_cooh_concentration: float = 0.0  # [mol/m^3] grafted COOH sites

    # Platform / polymer family (Node F1-a, v8.0): drives L2 solver
    # dispatch. Default keeps legacy chitosan/agarose behaviour.
    polymer_family: PolymerFamily = PolymerFamily.AGAROSE_CHITOSAN

    # Alginate-specific defaults (F1-a). Harmless for other families.
    f_guluronate: float = 0.5          # [-] guluronate fraction (G-block)
    D_Ca: float = 1.0e-9               # [m²/s] Ca²⁺ diffusivity in alginate gel
    k_bind_Ca: float = 1.0e3           # [M⁻²·s⁻¹] Ca²⁺ + 2 COO⁻ binding rate
    K_alg_modulus: float = 30.0e3      # [Pa] modulus prefactor (Kong 2004)
    n_alg_modulus: float = 2.0         # [-] modulus exponent

    # Cellulose-specific defaults (F1-b Phase 1, NaOH/urea). Harmless for
    # other families. See docs/f1b_cellulose_nips_protocol.md §5.
    N_p_cellulose: float = 370.0           # [-] degree of polymerisation (M_n/M_AGU)
    chi_PS_cellulose: float = 0.45         # [-] χ polymer-solvent
    chi_PN_cellulose: float = 0.85         # [-] χ polymer-nonsolvent (water)
    chi_SN_cellulose: float = 0.30         # [-] χ solvent-nonsolvent
    D_solvent_cellulose: float = 5.0e-11   # [m²/s] solvent self-diffusion in gel
    D_nonsolvent_cellulose: float = 1.0e-10  # [m²/s] water self-diffusion in gel
    kappa_CH_cellulose: float = 1.0e-17    # [J·m⁻¹] Cahn-Hilliard gradient energy coef
    K_cell_modulus: float = 5.0e5          # [Pa] modulus prefactor (Zhang 2020)
    alpha_cell_modulus: float = 2.25       # [-] modulus exponent (entangled regime)

    # PLGA-specific defaults (F1-c Phase 1, PLGA 50:50). Harmless for
    # other families. See docs/f1c_plga_protocol.md §5.
    D_DCM_plga: float = 1.0e-9             # [m²/s] DCM effective diffusivity in PLGA/DCM
    phi_DCM_eq: float = 0.005              # [-] bath-equilibrium DCM fraction (Henry)
    G_glassy_plga: float = 7.0e8           # [Pa] PLGA glassy-state shear modulus
    n_plga_modulus: float = 2.0            # [-] Gibson-Ashby exponent


# ─── Model Evidence and Provenance ────────────────────────────────────────

@dataclass
class ModelManifest:
    """Provenance record for a single model/solver used in a pipeline level.

    Attached to each result object to make evidence tier, assumptions, and
    validity domain traceable without reading source code.
    """
    model_name: str                         # e.g. "L1.PBE.FixedPivot.AlopaeusCT"
    evidence_tier: ModelEvidenceTier = ModelEvidenceTier.SEMI_QUANTITATIVE
    valid_domain: dict = field(default_factory=dict)  # {"Re": (100, 1e6), ...}
    calibration_ref: str = ""               # "" or CalibrationEntry ID
    assumptions: list[str] = field(default_factory=list)
    diagnostics: dict = field(default_factory=dict)   # {"thiele": 0.3, "mass_conservation": 0.999}


@dataclass
class RunReport:
    """Structured report for a complete pipeline run.

    Collects model manifests from all levels plus trust assessment and
    solver diagnostics. Suitable for JSON export and lab notebook attachment.
    """
    model_graph: list[ModelManifest] = field(default_factory=list)
    trust_level: str = ""                   # "TRUSTWORTHY" | "CAUTION" | "UNRELIABLE"
    trust_warnings: list[str] = field(default_factory=list)
    trust_blockers: list[str] = field(default_factory=list)
    diagnostics: dict = field(default_factory=dict)   # aggregated diagnostics
    min_evidence_tier: str = ""             # weakest tier across all levels

    def compute_min_tier(self) -> ModelEvidenceTier:
        """Return the weakest evidence tier across all models in the graph."""
        if not self.model_graph:
            return ModelEvidenceTier.UNSUPPORTED
        # Tier ordering: validated > calibrated > semi > qualitative > unsupported
        _ORDER = list(ModelEvidenceTier)
        # Compare by .value (string), not identity, so manifests created
        # against a stale class object (e.g. after importlib.reload of this
        # module by the Streamlit app) still match the current enum members.
        _order_values = [t.value for t in _ORDER]
        worst_idx = 0
        for m in self.model_graph:
            tier = m.evidence_tier
            tier_value = getattr(tier, "value", tier)
            try:
                idx = _order_values.index(str(tier_value))
            except ValueError:
                idx = _order_values.index(ModelEvidenceTier.UNSUPPORTED.value)
            if idx > worst_idx:
                worst_idx = idx
        return _ORDER[worst_idx]


# ─── Cross-cutting Run Context (Node 7, v6.1) ─────────────────────────────


@dataclass
class RunContext:
    """Cross-cutting inputs to a pipeline run.

    Carries optional services that the orchestrator should consult before
    invoking the per-level solvers. Designed to be backward-compatible:
    ``run_context=None`` reproduces the v6.0 behaviour exactly.

    v6.1 scope (Node 7): only ``calibration_store`` is wired. Future
    additions (random_seed routing, output_policy, uncertainty_spec) follow
    the same opt-in pattern — pass them in to enable; omit to keep current
    behaviour. The richer ``ParameterProvider`` with full provenance
    tracking (ResolvedParameter source/uncertainty) is deferred to v7.0.
    """
    calibration_store: Optional[Any] = None
    run_id: str = ""
    notes: str = ""


# ─── Result Structures ────────────────────────────────────────────────────

@dataclass
class EmulsificationResult:
    """Output of Level 1: PBE solver."""
    d_bins: np.ndarray                  # [m] pivot diameters (N_bins,)
    n_d: np.ndarray                     # [#/m³] number density (N_bins,)
    d32: float                          # [m] Sauter mean diameter
    d43: float                          # [m] volume-weighted mean
    d10: float                          # [m] 10th percentile
    d50: float                          # [m] median
    d90: float                          # [m] 90th percentile
    span: float                         # [-] (d90 - d10) / d50
    total_volume_fraction: float        # [-]
    converged: bool
    d_mode: float = 0.0                 # [m] modal diameter (volume-weighted)
    t_history: Optional[np.ndarray] = None
    n_d_history: Optional[np.ndarray] = None
    t_converged: Optional[float] = None # [s] time at which d32 convergence was first achieved (None if never)
    n_extensions: int = 0               # [-] number of adaptive extensions performed
    model_manifest: Optional[ModelManifest] = None  # v6.1: evidence provenance

    # v0.6.2 (F4) — typed Quantity accessors. Float fields above remain
    # authoritative for arithmetic; these expose unit-tagged handles.

    @property
    def d32_q(self):
        from dpsim.core.quantities import Quantity
        return Quantity(float(self.d32), "m", source="M1.L1.PBE",
                        note="Sauter mean diameter.")

    @property
    def d50_q(self):
        from dpsim.core.quantities import Quantity
        return Quantity(float(self.d50), "m", source="M1.L1.PBE",
                        note="Median (50th percentile) diameter.")

    @property
    def d10_q(self):
        from dpsim.core.quantities import Quantity
        return Quantity(float(self.d10), "m", source="M1.L1.PBE")

    @property
    def d90_q(self):
        from dpsim.core.quantities import Quantity
        return Quantity(float(self.d90), "m", source="M1.L1.PBE")

    @property
    def span_q(self):
        from dpsim.core.quantities import Quantity
        return Quantity(
            float(self.span), "1", source="M1.L1.PBE",
            note="(d90 - d10) / d50 — distribution width (dimensionless).",
        )


def _default_dsd_calibration_hooks() -> list[str]:
    """Wet-lab measurements that can replace or calibrate the simulated DSD."""

    return [
        "microscopy_image_analysis",
        "laser_diffraction_distribution",
    ]


def _default_m1_calibration_hooks() -> dict[str, list[str]]:
    """Canonical wet-lab hooks for M1 outputs consumed by M2/M3."""

    return {
        "bead_size_distribution": [
            "microscopy_image_analysis",
            "laser_diffraction_distribution",
        ],
        "pore_structure": [
            "cryo_sem_or_confocal_pore_image_analysis",
            "sec_inverse_size_calibration",
        ],
        "swelling": [
            "wet_dry_swelling_ratio",
        ],
        "mechanics": [
            "single_bead_compression",
            "bulk_compression_or_oscillatory_modulus",
        ],
        "wash_residuals": [
            "toc_or_gravimetric_oil_assay",
            "surfactant_colorimetric_or_hplc_assay",
        ],
    }


@dataclass
class BeadSizeDistributionPayload:
    """Full M1 bead size distribution exported at the M1->M2 boundary.

    The lifecycle simulator uses volume-weighted quantiles because bead mass,
    bed packing, pressure drop, and capacity scale with particle volume, not
    with the count median alone. Arrays are stored as plain lists so the M1
    contract remains JSON-friendly and easy to write into dossiers.
    """

    diameter_bins_m: list[float]
    number_density: list[float]
    volume_fraction: list[float]
    volume_cdf: list[float]
    total_volume_fraction: float
    d10_m: float
    d32_m: float
    d43_m: float
    d50_m: float
    d90_m: float
    span: float
    d_mode_m: float = 0.0
    source: str = "M1.PBE"
    evidence_tier: str = "semi_quantitative"
    calibration_hooks: list[str] = field(default_factory=_default_dsd_calibration_hooks)

    @classmethod
    def from_emulsification_result(
        cls,
        result: EmulsificationResult,
        *,
        source: str = "M1.PBE",
        evidence_tier: str | None = None,
        total_volume_fraction: float | None = None,
    ) -> "BeadSizeDistributionPayload":
        """Build a distribution payload from the Level-1 PBE result."""

        d = np.asarray(result.d_bins, dtype=float).reshape(-1)
        n = np.asarray(result.n_d, dtype=float).reshape(-1)
        size = min(d.size, n.size)
        if size == 0:
            d = np.asarray([float(result.d50)], dtype=float)
            n = np.asarray([1.0], dtype=float)
        else:
            d = d[:size]
            n = n[:size]

        d_safe = np.where(np.isfinite(d) & (d > 0.0), d, float(result.d50))
        n_safe = np.where(np.isfinite(n) & (n > 0.0), n, 0.0)
        volume_weights = n_safe * (d_safe ** 3)
        if float(np.sum(volume_weights)) <= 0.0:
            volume_fraction = np.full(d_safe.size, 1.0 / d_safe.size, dtype=float)
        else:
            volume_fraction = volume_weights / float(np.sum(volume_weights))
        volume_cdf = np.cumsum(volume_fraction)
        if volume_cdf.size:
            volume_cdf[-1] = 1.0

        tier = evidence_tier
        if tier is None and result.model_manifest is not None:
            tier = result.model_manifest.evidence_tier.value
        if tier is None:
            tier = "semi_quantitative"

        if total_volume_fraction is None:
            total_volume_fraction = float(result.total_volume_fraction)

        return cls(
            diameter_bins_m=[float(x) for x in d_safe],
            number_density=[float(x) for x in n_safe],
            volume_fraction=[float(x) for x in volume_fraction],
            volume_cdf=[float(x) for x in volume_cdf],
            total_volume_fraction=float(total_volume_fraction),
            d10_m=float(result.d10),
            d32_m=float(result.d32),
            d43_m=float(result.d43),
            d50_m=float(result.d50),
            d90_m=float(result.d90),
            span=float(result.span),
            d_mode_m=float(result.d_mode or 0.0),
            source=source,
            evidence_tier=str(tier),
        )

    def validate(self) -> list[str]:
        """Return data-integrity violations for the exported distribution."""

        violations: list[str] = []
        n_bins = len(self.diameter_bins_m)
        if n_bins == 0:
            violations.append("bead_size_distribution has no diameter bins.")
            return violations
        if len(self.number_density) != n_bins:
            violations.append("bead_size_distribution number_density length mismatch.")
        if len(self.volume_fraction) != n_bins:
            violations.append("bead_size_distribution volume_fraction length mismatch.")
        if len(self.volume_cdf) != n_bins:
            violations.append("bead_size_distribution volume_cdf length mismatch.")

        diam = np.asarray(self.diameter_bins_m, dtype=float)
        if not np.all(np.isfinite(diam)) or np.any(diam <= 0.0):
            violations.append("bead_size_distribution diameters must be finite and positive.")
        elif not (1e-7 <= float(np.nanmedian(diam)) <= 1e-2):
            violations.append("bead_size_distribution median diameter is outside [1e-7, 1e-2] m.")

        dens = np.asarray(self.number_density, dtype=float)
        if dens.size and (not np.all(np.isfinite(dens)) or np.any(dens < 0.0)):
            violations.append("bead_size_distribution number_density must be finite and non-negative.")

        vf = np.asarray(self.volume_fraction, dtype=float)
        if vf.size and (not np.all(np.isfinite(vf)) or np.any(vf < 0.0)):
            violations.append("bead_size_distribution volume_fraction must be finite and non-negative.")
        if vf.size and abs(float(np.sum(vf)) - 1.0) > 1e-6:
            violations.append("bead_size_distribution volume_fraction must sum to 1.")

        cdf = np.asarray(self.volume_cdf, dtype=float)
        if cdf.size:
            if not np.all(np.isfinite(cdf)):
                violations.append("bead_size_distribution volume_cdf must be finite.")
            if np.any(np.diff(cdf) < -1e-12):
                violations.append("bead_size_distribution volume_cdf must be monotonic.")
            if abs(float(cdf[-1]) - 1.0) > 1e-6:
                violations.append("bead_size_distribution volume_cdf must end at 1.")

        if not (0.0 <= self.total_volume_fraction <= 1.0):
            violations.append("bead_size_distribution total_volume_fraction outside [0, 1].")
        for name, value in (
            ("d10_m", self.d10_m),
            ("d32_m", self.d32_m),
            ("d43_m", self.d43_m),
            ("d50_m", self.d50_m),
            ("d90_m", self.d90_m),
        ):
            if not (np.isfinite(value) and 1e-9 <= float(value) <= 1e-2):
                violations.append(f"bead_size_distribution {name} outside [1e-9, 1e-2] m.")
        if self.span < 0.0:
            violations.append("bead_size_distribution span must be non-negative.")

        return violations

    def quantile_diameter(self, quantile: float) -> float:
        """Return the volume-weighted diameter at ``quantile``."""

        if not (0.0 <= quantile <= 1.0):
            raise ValueError("DSD quantile must be in [0, 1].")
        if not self.diameter_bins_m:
            raise ValueError("Cannot compute a DSD quantile without diameter bins.")
        cdf = np.asarray(self.volume_cdf, dtype=float)
        d = np.asarray(self.diameter_bins_m, dtype=float)
        if cdf.size != d.size or cdf.size == 0:
            raise ValueError("DSD payload has inconsistent diameter/CDF arrays.")
        idx = int(np.searchsorted(cdf, quantile, side="left"))
        idx = max(0, min(idx, d.size - 1))
        return float(d[idx])

    def quantile_table(
        self,
        quantiles: tuple[float, ...] | list[float] = (0.10, 0.50, 0.90),
    ) -> list[dict[str, float]]:
        """Return representative radii and mass fractions for DSD transfer.

        Mass fractions are midpoint partitions of the requested quantiles,
        matching the existing batch-variability convention.
        """

        if not quantiles:
            raise ValueError("At least one DSD quantile is required.")
        qs = tuple(sorted({float(q) for q in quantiles}))
        if not all(0.0 < q < 1.0 for q in qs):
            raise ValueError("DSD transfer quantiles must be in (0, 1).")
        q_arr = np.asarray(qs, dtype=float)
        edges = np.concatenate(([0.0], (q_arr[:-1] + q_arr[1:]) / 2.0, [1.0]))
        mass = np.diff(edges)
        rows: list[dict[str, float]] = []
        for q, mass_fraction in zip(qs, mass):
            diameter = self.quantile_diameter(q)
            rows.append(
                {
                    "quantile": float(q),
                    "diameter_m": float(diameter),
                    "radius_m": float(diameter / 2.0),
                    "mass_fraction": float(mass_fraction),
                }
            )
        return rows


@dataclass
class M1WashingResult:
    """Screening M1 oil/surfactant wash-out state.

    This is an auditable approximation of drain/resuspend washing after
    microsphere collection. It is deliberately parameterized by lab operations
    rather than a hidden constant so residual oil/surfactant assays can later
    calibrate the retention factors.
    """

    model_name: str
    initial_oil_volume_fraction: float
    wash_cycles: int
    wash_volume_ratio: float
    mixing_efficiency: float
    oil_retention_factor: float
    surfactant_retention_factor: float
    per_cycle_oil_removal: float
    per_cycle_surfactant_removal: float
    oil_removal_efficiency: float
    residual_oil_volume_fraction: float
    residual_surfactant_concentration_kg_m3: float
    evidence_tier: str = ModelEvidenceTier.QUALITATIVE_TREND.value
    assumptions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    calibration_hooks: list[str] = field(default_factory=lambda: [
        "toc_or_gravimetric_oil_assay",
        "surfactant_colorimetric_or_hplc_assay",
        "wash_fraction_mass_balance",
    ])
    model_manifest: Optional[ModelManifest] = None

    def validate(self) -> list[str]:
        """Return range violations for the wash-out result and inputs."""

        violations: list[str] = []
        if not (0.0 <= self.initial_oil_volume_fraction <= 1.0):
            violations.append("M1WashingResult initial_oil_volume_fraction outside [0, 1].")
        if self.wash_cycles < 0:
            violations.append("M1WashingResult wash_cycles must be non-negative.")
        if self.wash_volume_ratio < 0.0:
            violations.append("M1WashingResult wash_volume_ratio must be non-negative.")
        if not (0.0 <= self.mixing_efficiency <= 1.0):
            violations.append("M1WashingResult mixing_efficiency outside [0, 1].")
        if self.oil_retention_factor <= 0.0:
            violations.append("M1WashingResult oil_retention_factor must be positive.")
        if self.surfactant_retention_factor <= 0.0:
            violations.append("M1WashingResult surfactant_retention_factor must be positive.")
        for name, value in (
            ("per_cycle_oil_removal", self.per_cycle_oil_removal),
            ("per_cycle_surfactant_removal", self.per_cycle_surfactant_removal),
            ("oil_removal_efficiency", self.oil_removal_efficiency),
            ("residual_oil_volume_fraction", self.residual_oil_volume_fraction),
        ):
            if not (0.0 <= value <= 1.0):
                violations.append(f"M1WashingResult {name} outside [0, 1].")
        if self.residual_surfactant_concentration_kg_m3 < 0.0:
            violations.append("M1WashingResult residual_surfactant_concentration_kg_m3 must be non-negative.")
        return violations


@dataclass
class GelationTimingResult:
    """Output of Level 2a: Gelation timing and arrest.

    Describes WHEN and HOW FAST gelation occurs, separate from
    what microstructure forms (Level 2b).
    """
    T_history: np.ndarray           # [K] temperature history (N_t,)
    t_gel_onset: float              # [s] time at which gelation starts
    alpha_final: float              # [-] final gelation fraction (0-1)
    mobility_arrest_factor: float   # [-] how much mobility is reduced at arrest
    cooling_rate_effective: float   # [K/s] effective cooling rate (may be size-dependent)


@dataclass
class GelationResult:
    """Output of Level 2: Phase-field solver.

    Supports both 1D radial (legacy) and 2D Cartesian solvers.
    For 1D: r_grid is (N_r,), phi_field is (N_r,).
    For 2D: r_grid is (N,) coordinate array, phi_field is (N, N).
    """
    r_grid: np.ndarray                  # [m] (N_r,) or (N,) for 2D coords
    phi_field: np.ndarray               # [-] (N_r,) or (N, N)
    pore_size_mean: float               # [m]
    pore_size_std: float                # [m]
    pore_size_distribution: np.ndarray  # [m]
    porosity: float                     # [-]
    alpha_final: float                  # [-]
    char_wavelength: float              # [m]
    T_history: Optional[np.ndarray] = None
    phi_snapshots: Optional[np.ndarray] = None
    L_domain: float = 0.0              # [m] domain side length (2D solver)
    grid_spacing: float = 0.0          # [m] uniform grid spacing
    # Morphology descriptors (v3.0)
    bicontinuous_score: float = 0.5   # [-] 0-1
    anisotropy: float = 0.0           # [-] 0-1
    connectivity: float = 1.0         # [-] 0-1, fraction of pore space connected
    chord_skewness: float = 0.0       # [-] skewness of chord length distribution
    model_tier: str = "unknown"       # "empirical_calibrated" or "mechanistic" — identifies L2 model type
    model_manifest: Optional[ModelManifest] = None  # v6.1: evidence provenance

    # v0.6.2 (F4) — typed Quantity accessors.

    @property
    def pore_size_mean_q(self):
        from dpsim.core.quantities import Quantity
        return Quantity(float(self.pore_size_mean), "m", source="M1.L2.gelation")

    @property
    def porosity_q(self):
        from dpsim.core.quantities import Quantity
        return Quantity(float(self.porosity), "1", source="M1.L2.gelation")

    @property
    def alpha_final_q(self):
        from dpsim.core.quantities import Quantity
        return Quantity(
            float(self.alpha_final), "1", source="M1.L2.gelation",
            note="Final gelation conversion fraction.",
        )


@dataclass
class NetworkTypeMetadata:
    """Describes what network was formed by crosslinking."""
    solver_family: str = "amine_covalent"
    network_target: str = "chitosan"      # "chitosan", "agarose", "independent", "mixed"
    bond_type: str = "covalent"           # "covalent", "ionic", "reversible"
    is_true_second_network: bool = True   # True for IPN, False for reinforcement
    eta_coupling_recommended: float = -0.15  # [-] per-chemistry IPN coupling coefficient from CrosslinkerProfile


@dataclass
class CrosslinkingResult:
    """Output of Level 3: ODE kinetics."""
    t_array: np.ndarray                 # [s] (N_t,)
    X_array: np.ndarray                 # [mol/m³] (N_t,)
    nu_e_array: np.ndarray              # [1/m³] (N_t,)
    Mc_array: np.ndarray                # [g/mol] (N_t,)
    xi_array: np.ndarray                # [m] (N_t,)
    G_chitosan_array: np.ndarray        # [Pa] (N_t,)
    p_final: float                      # [-]
    nu_e_final: float                   # [1/m³]
    Mc_final: float                     # [g/mol]
    xi_final: float                     # [m]
    G_chitosan_final: float             # [Pa]
    network_metadata: Optional[NetworkTypeMetadata] = None
    model_manifest: Optional[ModelManifest] = None  # v6.1: evidence provenance
    # v6.1: solver diagnostics
    thiele_modulus: float = 0.0         # [-] Phi (0 = not computed)
    regime: str = "unknown"             # "reaction_limited", "borderline", "diffusion_limited", "unknown"
    stoichiometric_ceiling: float = 1.0 # [-] max conversion given reagent/reactive-group ratio
    residual_reactive_groups: float = 0.0  # [mol/m3] unreacted -NH2 or -OH after crosslinking
    # v9.2.2: split diagnostics for dual-track crosslinkers (STMP).
    # Remain 0.0 for single-track crosslinkers (genipin, glutaraldehyde, ECH, DVS).
    G_chit_diester: float = 0.0           # [Pa] contribution from agarose-OH phosphate diesters
    G_chit_phosphoramide: float = 0.0     # [Pa] contribution from chitosan-NH2 phosphoramides
    p_final_nh2: float = 0.0              # [-] NH2 conversion fraction (STMP dual-track)

    # v0.6.2 (F4) — typed Quantity accessors.

    @property
    def p_final_q(self):
        from dpsim.core.quantities import Quantity
        return Quantity(
            float(self.p_final), "1", source="M1.L3.crosslinking",
            note="Crosslinking conversion fraction (dimensionless).",
        )

    @property
    def G_chitosan_final_q(self):
        from dpsim.core.quantities import Quantity
        return Quantity(
            float(self.G_chitosan_final), "Pa", source="M1.L3.crosslinking",
            note="Chitosan-network shear modulus from crosslinking kinetics.",
        )

    @property
    def xi_final_q(self):
        from dpsim.core.quantities import Quantity
        return Quantity(
            float(self.xi_final), "m", source="M1.L3.crosslinking",
            note="Final mesh size of the crosslinked network.",
        )


@dataclass
class MechanicalResult:
    """Output of Level 4: Property prediction."""
    G_agarose: float                    # [Pa]
    G_chitosan: float                   # [Pa]
    G_DN: float                         # [Pa]
    E_star: float                       # [Pa]
    delta_array: np.ndarray             # [m]
    F_array: np.ndarray                 # [N]
    rh_array: np.ndarray                # [m]
    Kav_array: np.ndarray               # [-]
    pore_size_mean: float               # [m]
    xi_mesh: float                      # [m]
    model_used: str = "phenomenological"  # which modulus model produced G_DN
    G_DN_lower: float = 0.0             # [Pa] Single-phase composite reference (HS bounds, not applicable to IPN)
    G_DN_upper: float = 0.0             # [Pa] Single-phase composite reference (HS bounds, not applicable to IPN)
    model_manifest: Optional[ModelManifest] = None  # v6.1: evidence provenance
    network_type: str = "unknown"       # v6.1: "true_IPN", "semi_IPN", "independent_network", "ionic_reinforced", "unknown"

    # v0.6.2 (F4) — typed Quantity accessors.

    @property
    def G_DN_q(self):
        from dpsim.core.quantities import Quantity
        return Quantity(
            float(self.G_DN), "Pa", source="M1.L4.mechanical",
            note="Double-network shear modulus.",
        )

    @property
    def E_star_q(self):
        from dpsim.core.quantities import Quantity
        return Quantity(
            float(self.E_star), "Pa", source="M1.L4.mechanical",
            note="Effective Young's modulus.",
        )

    @property
    def G_agarose_q(self):
        from dpsim.core.quantities import Quantity
        return Quantity(
            float(self.G_agarose), "Pa", source="M1.L4.mechanical",
            note="Agarose-network shear modulus.",
        )

    @property
    def G_chitosan_q(self):
        from dpsim.core.quantities import Quantity
        return Quantity(
            float(self.G_chitosan), "Pa", source="M1.L4.mechanical",
            note="Chitosan-network shear modulus (post-mechanical-coupling).",
        )

    @property
    def pore_size_mean_q(self):
        from dpsim.core.quantities import Quantity
        return Quantity(
            float(self.pore_size_mean), "m", source="M1.L4.mechanical",
        )

    @property
    def xi_mesh_q(self):
        from dpsim.core.quantities import Quantity
        return Quantity(float(self.xi_mesh), "m", source="M1.L4.mechanical")


@dataclass
class FullResult:
    """Complete pipeline output."""
    parameters: SimulationParameters
    emulsification: EmulsificationResult
    gelation: GelationResult
    crosslinking: CrosslinkingResult
    mechanical: MechanicalResult
    gelation_timing: Optional[GelationTimingResult] = None
    run_report: Optional[RunReport] = None  # v6.1: model evidence + diagnostics

    def objective_vector(self) -> np.ndarray:
        """Compute the 3 objective values for optimization.

        Delegates to the canonical implementation in
        ``dpsim.optimization.objectives.compute_objectives``.
        """
        from dpsim.optimization.objectives import compute_objectives
        return compute_objectives(self)


@dataclass
class M1ExportContract:
    """Stable interface between Module 1 (fabrication) and Module 2 (functionalization).

    Contains all Module 1 outputs needed by Module 2, with explicit units,
    types, and trust metadata. This is the ONLY object Module 2 should read
    from Module 1 — it decouples the two modules.
    """
    # ── Geometry (from L1) ──
    bead_radius: float              # [m] from d50/2
    bead_d32: float                 # [m] Sauter mean diameter
    bead_d50: float                 # [m] median diameter

    # ── Pore structure (from L2) ──
    pore_size_mean: float           # [m] mean pore diameter
    pore_size_std: float            # [m] standard deviation of pore sizes
    porosity: float                 # [-] particle porosity (fraction void)
    l2_model_tier: str              # "empirical_calibrated" or "mechanistic"

    # ── Network structure (from L3) ──
    mesh_size_xi: float             # [m] crosslinked network mesh size
    p_final: float                  # [-] crosslinking conversion fraction
    primary_crosslinker: str        # e.g., "genipin", "dvs"

    # ── Residual reactive groups (from L3 + formulation) ──
    nh2_bulk_concentration: float   # [mol/m^3] residual NH2 after primary crosslinking
    oh_bulk_concentration: float    # [mol/m^3] total agarose OH

    # ── Mechanical properties (from L4) ──
    G_DN: float                     # [Pa] double-network shear modulus
    E_star: float                   # [Pa] effective Young's modulus
    model_used: str                 # "phenomenological" or "flory_rehner_affine"

    # ── Formulation (source parameters) ──
    c_agarose: float                # [kg/m^3] agarose concentration
    c_chitosan: float               # [kg/m^3] chitosan concentration
    DDA: float                      # [-] degree of deacetylation

    # ── Trust and uncertainty ──
    trust_level: str                # "TRUSTWORTHY", "CAUTION", "UNRELIABLE"
    trust_warnings: list[str] = field(default_factory=list)
    uncertainty_notes: str = ""     # Human-readable uncertainty description
    bead_size_distribution: Optional[BeadSizeDistributionPayload] = None
    calibration_hooks: dict[str, list[str]] = field(default_factory=_default_m1_calibration_hooks)
    oil_removal_efficiency: float = 1.0  # [-] fraction of continuous oil removed by washing
    residual_oil_volume_fraction: float = 0.0  # [-] screening carryover in wet packed media
    residual_surfactant_concentration_kg_m3: float = 0.0  # [kg/m^3] retained surfactant
    washing_assumptions: list[str] = field(default_factory=list)
    washing_model: Optional[M1WashingResult] = None

    def validate_units(self) -> list[str]:
        """Node 10 (F11): boundary-level unit/range sanity checks.

        Returns a list of violation messages (empty = pass). Catches the
        common silent-failure modes of someone shoving a value in the wrong
        unit through the M1->M2 contract: e.g. a bead_radius in microns
        instead of meters, a pH in mol/m^3, a concentration in g/L.

        These are *order-of-magnitude* guards, not scientific calibration —
        a reasonable polysaccharide microsphere lives entirely inside every
        bound checked here. Failing one of these means the value is
        physically impossible for our system, not just unusual.
        """
        violations: list[str] = []

        # Geometry: SI metres. A µm number passed as m would land at 1e-6;
        # a cm value would land at 1e-2.
        if not (1e-7 <= self.bead_radius <= 5e-3):
            violations.append(
                f"bead_radius={self.bead_radius:g} m outside [1e-7, 5e-3]; "
                "wrong unit (µm vs m)?"
            )
        if not (1e-7 <= self.bead_d50 <= 1e-2):
            violations.append(
                f"bead_d50={self.bead_d50:g} m outside [1e-7, 1e-2]; wrong unit?"
            )
        if not (1e-9 <= self.pore_size_mean <= 1e-5):
            violations.append(
                f"pore_size_mean={self.pore_size_mean:g} m outside [1e-9, 1e-5]; "
                "did you pass nm as m?"
            )
        if self.pore_size_std < 0:
            violations.append(
                f"pore_size_std={self.pore_size_std:g} must be non-negative."
            )
        if not (0.0 <= self.porosity <= 1.0):
            violations.append(
                f"porosity={self.porosity:g} outside [0, 1]; must be a fraction."
            )
        if not (1e-10 <= self.mesh_size_xi <= 1e-5):
            violations.append(
                f"mesh_size_xi={self.mesh_size_xi:g} m outside [1e-10, 1e-5]."
            )
        if not (0.0 <= self.p_final <= 1.0):
            violations.append(
                f"p_final={self.p_final:g} outside [0, 1]; conversion fraction."
            )

        # Concentrations: mol/m^3. Native chitosan amine sits ~50-150 mol/m^3
        # for a 1-3% w/v solution. Pushing 1e5 means kg/m^3 was passed
        # as mol/m^3.
        if not (0.0 <= self.nh2_bulk_concentration <= 1e4):
            violations.append(
                f"nh2_bulk_concentration={self.nh2_bulk_concentration:g} mol/m^3 "
                "outside [0, 1e4]; wrong unit (mM vs mol/m^3)?"
            )
        if not (0.0 <= self.oh_bulk_concentration <= 1e5):
            violations.append(
                f"oh_bulk_concentration={self.oh_bulk_concentration:g} mol/m^3 "
                "outside [0, 1e5]."
            )

        # Mechanical: Pa. Gel modulus 1e3-1e6 Pa. 1 GPa would be a steel
        # bead; 1e-3 Pa would be water.
        if not (1.0 <= self.G_DN <= 1e9):
            violations.append(
                f"G_DN={self.G_DN:g} Pa outside [1, 1e9]; wrong unit (kPa vs Pa)?"
            )
        if not (1.0 <= self.E_star <= 1e10):
            violations.append(
                f"E_star={self.E_star:g} Pa outside [1, 1e10]."
            )

        # Formulation: kg/m^3 (i.e. g/L). 0-200 kg/m^3 covers every
        # processable polysaccharide gel. A value passed in % w/v would
        # land in [0, 20] which we cannot distinguish; only flag obvious
        # nonsense (negative, >300 kg/m^3 = 30% which is unprocessable).
        for name, val in (("c_agarose", self.c_agarose),
                          ("c_chitosan", self.c_chitosan)):
            if not (0.0 <= val <= 300.0):
                violations.append(
                    f"{name}={val:g} kg/m^3 outside [0, 300]."
                )

        if not (0.0 <= self.DDA <= 1.0):
            violations.append(
                f"DDA={self.DDA:g} outside [0, 1]; degree of deacetylation."
            )

        if self.bead_size_distribution is not None:
            violations.extend(self.bead_size_distribution.validate())

        if not (0.0 <= self.oil_removal_efficiency <= 1.0):
            violations.append(
                f"oil_removal_efficiency={self.oil_removal_efficiency:g} outside [0, 1]."
            )
        if not (0.0 <= self.residual_oil_volume_fraction <= 1.0):
            violations.append(
                f"residual_oil_volume_fraction={self.residual_oil_volume_fraction:g} "
                "outside [0, 1]."
            )
        if self.residual_surfactant_concentration_kg_m3 < 0.0:
            violations.append(
                "residual_surfactant_concentration_kg_m3 must be non-negative."
            )
        if self.washing_model is not None:
            violations.extend(self.washing_model.validate())

        return violations


@dataclass
class OptimizationState:
    """State of the Bayesian optimization campaign."""
    X_observed: np.ndarray              # (N_eval, 7)
    Y_observed: np.ndarray              # (N_eval, 3)
    pareto_X: np.ndarray
    pareto_Y: np.ndarray
    iteration: int
    hypervolume: float
    hypervolume_history: list = field(default_factory=list)
    converged: bool = False
    gp_state: Optional[dict] = None
    # Node 6 (v6.1): per-Pareto-candidate weakest evidence tier (string form,
    # JSON-friendly). Empty when no run_report was attached. Length matches
    # pareto_X.shape[0].
    pareto_evidence_tiers: list[str] = field(default_factory=list)

