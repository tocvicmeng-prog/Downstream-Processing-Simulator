"""M1 post-emulsification washing and residual carryover model.

The fabrication pipeline previously exposed oil/surfactant residuals as fixed
screening constants. This module replaces that with a small wet-lab operation
model: repeated drain/resuspend washes remove a fraction of retained oil and
surfactant according to wash volume, mixing efficiency, and retention factors.

The equations are intentionally simple. They are meant to make assumptions
explicit and calibratable, not to claim release-quality leachables prediction.
"""

from __future__ import annotations

from dpsim.datatypes import (
    M1WashingResult,
    ModelEvidenceTier,
    ModelManifest,
    SimulationParameters,
)


_MODEL_NAME = "M1.washing.well_mixed_extraction"


def solve_m1_washing(params: SimulationParameters) -> M1WashingResult:
    """Estimate residual oil and surfactant after M1 drain/resuspend washing.

    The model treats each wash as a well-mixed extraction stage. For a given
    retained species, the per-cycle removal fraction is:

    ``mixing_efficiency * wash_volume_ratio / (wash_volume_ratio + retention)``

    where ``retention`` is a calibratable lumped factor. Larger retention means
    the species is harder to extract from bead surfaces and pore liquid.
    """

    f = params.formulation
    cycles = max(0, int(round(float(f.m1_wash_cycles))))
    initial_oil = _clip_fraction(float(f.m1_initial_oil_carryover_fraction))
    wash_volume_ratio = max(0.0, float(f.m1_wash_volume_ratio))
    mixing_efficiency = _clip_fraction(float(f.m1_wash_mixing_efficiency))
    oil_retention = max(1e-12, float(f.m1_oil_retention_factor))
    surfactant_retention = max(1e-12, float(f.m1_surfactant_retention_factor))

    oil_cycle_removal = _per_cycle_removal(
        wash_volume_ratio=wash_volume_ratio,
        mixing_efficiency=mixing_efficiency,
        retention_factor=oil_retention,
    )
    surfactant_cycle_removal = _per_cycle_removal(
        wash_volume_ratio=wash_volume_ratio,
        mixing_efficiency=mixing_efficiency,
        retention_factor=surfactant_retention,
    )

    residual_oil = initial_oil * ((1.0 - oil_cycle_removal) ** cycles)
    surfactant_carryover_fraction = initial_oil * (
        (1.0 - surfactant_cycle_removal) ** cycles
    )
    residual_surfactant = max(0.0, float(f.c_span80)) * surfactant_carryover_fraction
    oil_removal_efficiency = 0.0
    if initial_oil > 0.0:
        oil_removal_efficiency = 1.0 - residual_oil / initial_oil

    assumptions = [
        "Drain/resuspend washes are represented as identical well-mixed extraction stages.",
        "Oil and surfactant retention factors are lumped empirical parameters until residual assays are fitted.",
        "Residual surfactant concentration scales from formulation Span-80 concentration and modeled carryover fraction.",
    ]
    warnings: list[str] = []
    if cycles < 3:
        warnings.append("Fewer than 3 M1 wash cycles; residual oil/surfactant risk is high.")
    if wash_volume_ratio < 1.0:
        warnings.append("M1 wash volume ratio below 1; extraction model is outside ordinary wet-lab practice.")
    if mixing_efficiency < 0.5:
        warnings.append("M1 wash mixing efficiency below 0.5; residual estimates are highly uncertain.")

    manifest = ModelManifest(
        model_name=_MODEL_NAME,
        evidence_tier=ModelEvidenceTier.QUALITATIVE_TREND,
        valid_domain={
            "wash_cycles": (0.0, 20.0),
            "wash_volume_ratio": (0.0, 20.0),
            "mixing_efficiency": (0.0, 1.0),
            "retention_factor": (0.05, 20.0),
        },
        assumptions=list(assumptions),
        diagnostics={
            "wash_cycles": cycles,
            "wash_volume_ratio": wash_volume_ratio,
            "mixing_efficiency": mixing_efficiency,
            "oil_retention_factor": oil_retention,
            "surfactant_retention_factor": surfactant_retention,
            "per_cycle_oil_removal": oil_cycle_removal,
            "per_cycle_surfactant_removal": surfactant_cycle_removal,
        },
    )

    return M1WashingResult(
        model_name=_MODEL_NAME,
        initial_oil_volume_fraction=initial_oil,
        wash_cycles=cycles,
        wash_volume_ratio=wash_volume_ratio,
        mixing_efficiency=mixing_efficiency,
        oil_retention_factor=oil_retention,
        surfactant_retention_factor=surfactant_retention,
        per_cycle_oil_removal=oil_cycle_removal,
        per_cycle_surfactant_removal=surfactant_cycle_removal,
        oil_removal_efficiency=float(oil_removal_efficiency),
        residual_oil_volume_fraction=float(residual_oil),
        residual_surfactant_concentration_kg_m3=float(residual_surfactant),
        assumptions=assumptions,
        warnings=warnings,
        model_manifest=manifest,
    )


def _per_cycle_removal(
    *,
    wash_volume_ratio: float,
    mixing_efficiency: float,
    retention_factor: float,
) -> float:
    """Return one-cycle extraction fraction in [0, 1)."""

    if wash_volume_ratio <= 0.0 or mixing_efficiency <= 0.0:
        return 0.0
    extraction = wash_volume_ratio / (wash_volume_ratio + max(retention_factor, 1e-12))
    return min(0.999999, max(0.0, mixing_efficiency * extraction))


def _clip_fraction(value: float) -> float:
    """Clip a scalar to the closed unit interval."""

    return min(1.0, max(0.0, value))
