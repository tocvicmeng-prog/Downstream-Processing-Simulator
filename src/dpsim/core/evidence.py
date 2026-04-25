"""Evidence helpers for clean architecture modules."""

from __future__ import annotations

from dpsim.datatypes import ModelEvidenceTier, ModelManifest


def weakest_tier(manifests: list[ModelManifest]) -> ModelEvidenceTier:
    """Return the weakest tier from a list of model manifests."""
    if not manifests:
        return ModelEvidenceTier.UNSUPPORTED
    order = list(ModelEvidenceTier)
    return order[max(order.index(m.evidence_tier) for m in manifests)]


def merge_assumptions(manifests: list[ModelManifest]) -> list[str]:
    """Merge manifest assumptions while preserving first-seen order."""
    assumptions: list[str] = []
    for manifest in manifests:
        assumptions.extend(manifest.assumptions)
    return list(dict.fromkeys(assumptions))
