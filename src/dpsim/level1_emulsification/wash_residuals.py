"""Bead/water partition-diffusion + first-order hydrolysis wash residual model.

B-2a / W-009, v0.6.5.
Reference: docs/update_workplan_2026-05-04.md §4 → B-2a.

Closes the audit observation that the existing M1 wash mass-balance
guardrail (G1 in core/recipe_validation.py) treats wash efficiency as a
single dimensionless number — adequate for oil/surfactant carryover but
silent on the chemistry-specific question "is the wash long enough to
reduce CNBr-derived isourea/cyanate-ester leakage below the protein-
contact safety limit?".

Physical model (per Scientific Advisor):

  * Each bead is treated as a well-mixed sphere of radius ``R`` with an
    effective intra-bead diffusivity ``D_eff`` and an equilibrium
    partition coefficient ``K_p = C_bead / C_water``. The lumped-sphere
    transport time constant is ``τ_diff ≈ R^2 / (15 · D_eff)`` (Crank
    "Mathematics of Diffusion" 1975, eq 6.21 simplified to first
    eigenmode).
  * Reagent in the bead also hydrolyses by a first-order reaction with
    rate constant ``k_hyd`` (chemistry-specific; CNBr ~5 min half-life
    at pH 11, CDI ~5 h at pH 7, tresyl 1–2 h).
  * Per cycle: solve the coupled ODE for bead and water concentration
    over the cycle duration, then drain and refill (set C_water → 0).

The output is the bead residual concentration after the full wash
sequence, plus pass/fail flags against:
  1. ``target_residual_mol_per_m3`` — the recipe's acceptance limit.
  2. ``assay_detection_limit_mol_per_m3`` — the lab's quantitation limit
     below which residuals are operationally "non-detectable". Carrying
     this on the calibration store (CalibrationEntry) lets the model
     gate confidence-tier on whether the limit is calibrated or
     defaulted.

Literature half-lives (used by ``hydrolysis_rate_for_reagent``):
  * CNBr cyanate ester  : ~5 min at pH 11, 4 °C    (Kohn & Wilchek 1981)
  * CDI imidazolyl carbonate : ~5 h at pH 7, 25 °C (Hearn 1981)
  * Tresyl sulfonate    : ~1–2 h, depending on solvent (Nilsson 1981)
  * Epoxide / vinyl sulfone : no spontaneous hydrolysis on relevant
                              wash timescales
  * Glutaraldehyde      : aldehyde stable; cleared by diffusion only
  * Span-80 / paraffin oil : no hydrolysis (handled by G1)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from scipy.integrate import solve_ivp

from dpsim.datatypes import ModelEvidenceTier, ModelManifest


# ─── Per-reagent first-order hydrolysis rate constants ──────────────────────
#
# Values tabulated at the *typical wash pH and temperature* — i.e. for
# CNBr at pH 11 (the activation pH), the cyanate ester half-life is the
# rate-limiting clearance factor while the bead is still alkaline.
# After the first neutral-pH wash the rate slows (cyanate-ester
# hydrolysis is base-catalysed). The model uses the activation-pH rate
# as a conservative upper bound on hydrolytic clearance — the loss of
# reagent is a *gain* for safety, so over-estimating it is the safe
# direction. A future enhancement could ramp k_hyd with measured wash pH.
#
# Half-life conversion: k_hyd = ln(2) / t_half.

REAGENT_HYDROLYSIS_RATES_PER_S: dict[str, float] = {
    # CNBr-derived cyanate ester — Kohn & Wilchek 1981 Anal. Biochem. 115:375
    "cnbr_activation": math.log(2.0) / (5.0 * 60.0),                # 5 min t1/2
    "generic_amine_to_cyanate_ester": math.log(2.0) / (5.0 * 60.0),
    # CDI-derived imidazolyl carbonate — Hearn 1981 Methods Enzymol. 135:102
    "cdi_activation": math.log(2.0) / (5.0 * 3600.0),               # 5 h t1/2
    "generic_amine_to_imidazolyl_carbonate": math.log(2.0) / (5.0 * 3600.0),
    # Tresyl sulfonate — Nilsson & Mosbach 1981 (mid of 1–2 h range)
    "tresyl_chloride_activation": math.log(2.0) / (5400.0),         # 1.5 h t1/2
    "generic_amine_to_sulfonate": math.log(2.0) / (5400.0),
    # Epoxides — stable on wash timescale; no hydrolysis term.
    "ech_activation": 0.0,
    "dvs_activation": 0.0,
    "bdge_activation": 0.0,
    "bis_epoxide_crosslinking": 0.0,
    # Glutaraldehyde aldehyde — stable; cleared by diffusion only.
    "glutaraldehyde_secondary": 0.0,
    # NaBH4 — fast decomposition above pH ~5; conservative t1/2 = 1 h.
    "nabh4_quench": math.log(2.0) / 3600.0,
}


# ─── Default wash-relevant transport defaults ───────────────────────────────
#
# Bead/water partition coefficient K_p:
#   K_p = 1 → reagent partitions equally (small uncharged molecules in
#             porous gels, e.g. CNBr-derived cyanate after activation)
#   K_p > 1 → reagent prefers the bead (hydrophobic + sticky reagents)
#   K_p < 1 → reagent prefers water (charged or hygroscopic)
# Default K_p = 1.0 is the conservative midpoint for unbiased small
# molecules in agarose-class hydrogels.
#
# Effective diffusivity D_eff in a typical 4 % agarose bead:
#   D_eff ≈ 0.5 × D_water for a small molecule (porosity-tortuosity
#   correction; Westrin & Axelsson 1991 review). At 25 °C, D_water for
#   ~100 Da reagent ~ 1e-9 m^2/s, so D_eff ~ 5e-10 m^2/s.
#
# These are conservative ranking-only defaults; the model degrades to
# QUALITATIVE_TREND when defaults are used.

_DEFAULT_PARTITION_COEFFICIENT: float = 1.0
_DEFAULT_INTRA_BEAD_DIFFUSIVITY_M2_PER_S: float = 5.0e-10
_DEFAULT_BEAD_RADIUS_M: float = 50.0e-6  # 100 µm bead → R = 50 µm


# ─── Specs ──────────────────────────────────────────────────────────────────


@dataclass
class WashResidualSpec:
    """Per-species transport + reaction parameters for a wash residual run.

    All concentrations in mol/m^3 (== mM); diffusivity in m^2/s; rate in 1/s.
    """

    species_name: str
    initial_bead_concentration_mol_per_m3: float
    diffusion_coefficient_m2_per_s: float = _DEFAULT_INTRA_BEAD_DIFFUSIVITY_M2_PER_S
    partition_coefficient_K_p: float = _DEFAULT_PARTITION_COEFFICIENT
    hydrolysis_rate_per_s: float = 0.0
    bead_radius_m: float = _DEFAULT_BEAD_RADIUS_M
    target_residual_mol_per_m3: float = 0.0
    assay_detection_limit_mol_per_m3: float = 0.0

    def __post_init__(self) -> None:
        if self.bead_radius_m <= 0.0:
            raise ValueError(
                f"bead_radius_m must be > 0, got {self.bead_radius_m}"
            )
        if self.diffusion_coefficient_m2_per_s <= 0.0:
            raise ValueError(
                f"diffusion_coefficient_m2_per_s must be > 0, got "
                f"{self.diffusion_coefficient_m2_per_s}"
            )
        if self.partition_coefficient_K_p <= 0.0:
            raise ValueError(
                f"partition_coefficient_K_p must be > 0, got "
                f"{self.partition_coefficient_K_p}"
            )
        if self.hydrolysis_rate_per_s < 0.0:
            raise ValueError(
                f"hydrolysis_rate_per_s must be >= 0, got "
                f"{self.hydrolysis_rate_per_s}"
            )


@dataclass
class WashCycleSpec:
    """Wash sequence parameters."""

    n_cycles: int
    cycle_duration_s: float
    wash_to_bead_volume_ratio: float
    mixing_efficiency: float = 1.0

    def __post_init__(self) -> None:
        if self.n_cycles <= 0:
            raise ValueError(f"n_cycles must be > 0, got {self.n_cycles}")
        if self.cycle_duration_s <= 0.0:
            raise ValueError(
                f"cycle_duration_s must be > 0, got {self.cycle_duration_s}"
            )
        if self.wash_to_bead_volume_ratio <= 0.0:
            raise ValueError(
                f"wash_to_bead_volume_ratio must be > 0, got "
                f"{self.wash_to_bead_volume_ratio}"
            )
        if not (0.0 < self.mixing_efficiency <= 1.0):
            raise ValueError(
                f"mixing_efficiency must be in (0, 1], got {self.mixing_efficiency}"
            )


# ─── Result ─────────────────────────────────────────────────────────────────


@dataclass
class WashResidualResult:
    """Output of ``predict_wash_residuals``."""

    species_name: str
    initial_bead_concentration_mol_per_m3: float
    residual_per_cycle_mol_per_m3: list[float]
    final_residual_mol_per_m3: float
    target_residual_mol_per_m3: float
    assay_detection_limit_mol_per_m3: float
    meets_target: bool
    meets_assay_limit: bool
    cumulative_hydrolysis_loss_fraction: float
    cumulative_diffusion_loss_fraction: float
    n_cycles: int
    cycle_duration_s: float
    wash_to_bead_volume_ratio: float
    diffusion_time_constant_s: float
    hydrolysis_half_life_s: float
    diagnostics: dict = field(default_factory=dict)
    model_manifest: Optional[ModelManifest] = None


# ─── Core solver ────────────────────────────────────────────────────────────


def _solve_one_cycle(
    C_bead_init: float,
    spec: WashResidualSpec,
    cycle: WashCycleSpec,
) -> tuple[float, float, float]:
    """Solve one wash cycle and return (C_bead_end, hydrolysis_loss, diffusion_loss).

    The lumped-sphere ODE system with first-order hydrolysis is:

        d C_b / dt = -(1/τ_diff) · (C_b − K_p · C_w) · η_mix − k_hyd · C_b
        d C_w / dt = +(V_b / V_w · 1/τ_diff) · (C_b − K_p · C_w) · η_mix

    where τ_diff = R^2 / (15 · D_eff) is the first-eigenmode time
    constant, η_mix is the mixing efficiency [0, 1], and V_b/V_w is the
    bead-to-water volume ratio.

    Linear coupled ODE — solved with scipy.integrate.solve_ivp using
    LSODA (matches the project convention). The system can be stiff when
    cycle_duration >> τ_diff (e.g. small beads in a long wash); LSODA
    handles both regimes cleanly.

    State vector: [C_b, C_w, integrated_hydrolysis_loss, integrated_diffusion_loss]
    so the loss-channel integrals are advanced by LSODA's adaptive
    stepper, not post-processed on a coarse output grid (the latter
    over-estimates by orders of magnitude when t_eval misses the
    diffusion equilibration transient).
    """
    tau_diff = (spec.bead_radius_m ** 2) / (15.0 * spec.diffusion_coefficient_m2_per_s)
    eta_mix = cycle.mixing_efficiency
    K_p = spec.partition_coefficient_K_p
    k_hyd = spec.hydrolysis_rate_per_s
    V_b_over_V_w = 1.0 / cycle.wash_to_bead_volume_ratio

    def rhs(t: float, y: np.ndarray) -> np.ndarray:
        C_b, C_w, _H, _D = y[0], y[1], y[2], y[3]
        flux = (C_b - K_p * C_w) / tau_diff * eta_mix
        hyd_rate = k_hyd * C_b
        d_b = -flux - hyd_rate
        d_w = V_b_over_V_w * flux
        return np.array([d_b, d_w, hyd_rate, flux])

    t_span = (0.0, cycle.cycle_duration_s)
    y0 = np.array([C_bead_init, 0.0, 0.0, 0.0])

    sol = solve_ivp(
        rhs, t_span, y0, method="LSODA",
        rtol=1e-8, atol=1e-12,
    )
    if not sol.success:
        raise RuntimeError(f"wash_residuals solve_ivp failed: {sol.message}")

    C_b_final = float(max(sol.y[0, -1], 0.0))
    hydrolysis_loss = float(sol.y[2, -1])
    diffusion_loss = float(sol.y[3, -1])

    return C_b_final, hydrolysis_loss, diffusion_loss


def predict_wash_residuals(
    spec: WashResidualSpec,
    cycle: WashCycleSpec,
) -> WashResidualResult:
    """Predict the bead-side residual concentration after a wash sequence.

    Args:
        spec: per-species transport + reaction parameters.
        cycle: wash sequence parameters.

    Returns:
        WashResidualResult with per-cycle and final residuals plus
        target / assay-limit pass flags. The model_manifest carries an
        evidence tier reflecting whether spec parameters are calibrated
        or rely on conservative defaults.
    """
    C_init = spec.initial_bead_concentration_mol_per_m3
    if C_init <= 0.0:
        # Nothing to wash — short-circuit with a degenerate result.
        return WashResidualResult(
            species_name=spec.species_name,
            initial_bead_concentration_mol_per_m3=0.0,
            residual_per_cycle_mol_per_m3=[0.0] * cycle.n_cycles,
            final_residual_mol_per_m3=0.0,
            target_residual_mol_per_m3=spec.target_residual_mol_per_m3,
            assay_detection_limit_mol_per_m3=spec.assay_detection_limit_mol_per_m3,
            meets_target=True,
            meets_assay_limit=True,
            cumulative_hydrolysis_loss_fraction=0.0,
            cumulative_diffusion_loss_fraction=0.0,
            n_cycles=cycle.n_cycles,
            cycle_duration_s=cycle.cycle_duration_s,
            wash_to_bead_volume_ratio=cycle.wash_to_bead_volume_ratio,
            diffusion_time_constant_s=(
                spec.bead_radius_m ** 2 / (15.0 * spec.diffusion_coefficient_m2_per_s)
            ),
            hydrolysis_half_life_s=(
                math.log(2.0) / spec.hydrolysis_rate_per_s
                if spec.hydrolysis_rate_per_s > 0.0
                else float("inf")
            ),
            model_manifest=ModelManifest(
                model_name="L1.WashResiduals.PartitionDiffusion",
                evidence_tier=ModelEvidenceTier.QUALITATIVE_TREND,
                assumptions=["initial concentration = 0 — degenerate short-circuit"],
            ),
        )

    residuals: list[float] = []
    cumulative_hyd = 0.0
    cumulative_diff = 0.0
    C_b = C_init
    for _ in range(cycle.n_cycles):
        C_b, hyd, diff = _solve_one_cycle(C_b, spec, cycle)
        residuals.append(C_b)
        cumulative_hyd += hyd
        cumulative_diff += diff

    total_loss = max(C_init - C_b, 0.0)
    cum_hyd_frac = cumulative_hyd / C_init if C_init > 0.0 else 0.0
    cum_diff_frac = cumulative_diff / C_init if C_init > 0.0 else 0.0

    final = residuals[-1]
    meets_target = final <= spec.target_residual_mol_per_m3 if spec.target_residual_mol_per_m3 > 0.0 else False
    meets_assay = (
        final <= spec.assay_detection_limit_mol_per_m3
        if spec.assay_detection_limit_mol_per_m3 > 0.0
        else False
    )

    tau_diff = (spec.bead_radius_m ** 2) / (15.0 * spec.diffusion_coefficient_m2_per_s)
    half_life = (
        math.log(2.0) / spec.hydrolysis_rate_per_s
        if spec.hydrolysis_rate_per_s > 0.0
        else float("inf")
    )

    # Evidence tier policy: defaults → QUALITATIVE_TREND; user-supplied
    # transport parameters → SEMI_QUANTITATIVE; user-supplied AND
    # calibrated assay_detection_limit → CALIBRATED_LOCAL.
    using_defaults = (
        spec.diffusion_coefficient_m2_per_s == _DEFAULT_INTRA_BEAD_DIFFUSIVITY_M2_PER_S
        and spec.partition_coefficient_K_p == _DEFAULT_PARTITION_COEFFICIENT
    )
    if spec.assay_detection_limit_mol_per_m3 > 0.0 and not using_defaults:
        tier = ModelEvidenceTier.CALIBRATED_LOCAL
    elif using_defaults:
        tier = ModelEvidenceTier.QUALITATIVE_TREND
    else:
        tier = ModelEvidenceTier.SEMI_QUANTITATIVE

    manifest = ModelManifest(
        model_name="L1.WashResiduals.PartitionDiffusion",
        evidence_tier=tier,
        valid_domain={
            "bead_radius_m": (1e-6, 5e-4),     # 1 µm – 500 µm beads
            "n_cycles": (1, 50),
            "cycle_duration_s": (1.0, 86400.0),  # 1 s – 1 day
            "wash_to_bead_volume_ratio": (0.5, 100.0),
        },
        assumptions=[
            "Lumped-sphere first-eigenmode τ_diff ≈ R²/(15·D_eff) (Crank 1975 §6.21).",
            "Well-mixed water phase per cycle; drained to C_w=0 between cycles.",
            "First-order hydrolysis in the bead; rate constant from "
            "REAGENT_HYDROLYSIS_RATES_PER_S or user-supplied.",
            "Partition equilibrium K_p assumed pH/T-independent within the wash window.",
        ],
        diagnostics={
            "tau_diff_s": float(tau_diff),
            "hydrolysis_half_life_s": float(half_life),
            "fraction_cleared": float(total_loss / C_init) if C_init > 0.0 else 0.0,
            "fraction_hydrolysed": float(cum_hyd_frac),
            "fraction_diffused": float(cum_diff_frac),
            "using_default_transport": bool(using_defaults),
        },
    )

    return WashResidualResult(
        species_name=spec.species_name,
        initial_bead_concentration_mol_per_m3=C_init,
        residual_per_cycle_mol_per_m3=residuals,
        final_residual_mol_per_m3=final,
        target_residual_mol_per_m3=spec.target_residual_mol_per_m3,
        assay_detection_limit_mol_per_m3=spec.assay_detection_limit_mol_per_m3,
        meets_target=bool(meets_target),
        meets_assay_limit=bool(meets_assay),
        cumulative_hydrolysis_loss_fraction=float(cum_hyd_frac),
        cumulative_diffusion_loss_fraction=float(cum_diff_frac),
        n_cycles=cycle.n_cycles,
        cycle_duration_s=cycle.cycle_duration_s,
        wash_to_bead_volume_ratio=cycle.wash_to_bead_volume_ratio,
        diffusion_time_constant_s=float(tau_diff),
        hydrolysis_half_life_s=float(half_life),
        diagnostics=dict(manifest.diagnostics),
        model_manifest=manifest,
    )


# ─── Convenience factory ────────────────────────────────────────────────────


def hydrolysis_rate_for_reagent(reagent_key: str) -> float:
    """Return the literature-anchored first-order hydrolysis rate [1/s].

    Returns 0.0 for reagents that are stable on wash timescales OR for
    unknown reagent keys (the caller should treat unknown as "no
    hydrolysis term, lean on diffusion only" — the conservative direction
    for residual-safety claims).
    """
    return REAGENT_HYDROLYSIS_RATES_PER_S.get(reagent_key, 0.0)


def make_default_spec(
    reagent_key: str,
    species_name: str,
    initial_bead_concentration_mol_per_m3: float,
    *,
    bead_radius_m: float = _DEFAULT_BEAD_RADIUS_M,
    target_residual_mol_per_m3: float = 0.0,
    assay_detection_limit_mol_per_m3: float = 0.0,
) -> WashResidualSpec:
    """Build a WashResidualSpec from a reagent_key with library defaults.

    Conservative defaults (K_p=1, D_eff=5e-10 m²/s, lit hydrolysis rate)
    flag the result as QUALITATIVE_TREND. Pass calibrated transport
    parameters explicitly to upgrade the tier.
    """
    return WashResidualSpec(
        species_name=species_name,
        initial_bead_concentration_mol_per_m3=initial_bead_concentration_mol_per_m3,
        diffusion_coefficient_m2_per_s=_DEFAULT_INTRA_BEAD_DIFFUSIVITY_M2_PER_S,
        partition_coefficient_K_p=_DEFAULT_PARTITION_COEFFICIENT,
        hydrolysis_rate_per_s=hydrolysis_rate_for_reagent(reagent_key),
        bead_radius_m=bead_radius_m,
        target_residual_mol_per_m3=target_residual_mol_per_m3,
        assay_detection_limit_mol_per_m3=assay_detection_limit_mol_per_m3,
    )


__all__ = [
    "REAGENT_HYDROLYSIS_RATES_PER_S",
    "WashCycleSpec",
    "WashResidualResult",
    "WashResidualSpec",
    "hydrolysis_rate_for_reagent",
    "make_default_spec",
    "predict_wash_residuals",
]
