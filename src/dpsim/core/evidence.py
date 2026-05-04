"""Evidence helpers for clean architecture modules."""

from __future__ import annotations

from dpsim.datatypes import ModelEvidenceTier, ModelManifest


def _tier_value(tier: object) -> str:
    return str(getattr(tier, "value", tier))


def weakest_tier(manifests: list[ModelManifest]) -> ModelEvidenceTier:
    """Return the weakest tier from a list of model manifests."""
    if not manifests:
        return ModelEvidenceTier.UNSUPPORTED
    order = list(ModelEvidenceTier)
    order_values = [tier.value for tier in order]
    worst = 0
    unsupported_idx = order_values.index(ModelEvidenceTier.UNSUPPORTED.value)
    for manifest in manifests:
        value = _tier_value(manifest.evidence_tier)
        idx = order_values.index(value) if value in order_values else unsupported_idx
        worst = max(worst, idx)
    return order[worst]


def merge_assumptions(manifests: list[ModelManifest]) -> list[str]:
    """Merge manifest assumptions while preserving first-seen order."""
    assumptions: list[str] = []
    for manifest in manifests:
        assumptions.extend(manifest.assumptions)
    return list(dict.fromkeys(assumptions))
