"""Minimal model registry for lifecycle-aware solver selection."""

from __future__ import annotations

from dataclasses import dataclass, field

from dpsim.datatypes import ModelEvidenceTier


@dataclass(frozen=True)
class ModelCapability:
    """Describes what a model can validly do."""

    key: str
    stage: str
    description: str
    evidence_tier: ModelEvidenceTier
    valid_domain: dict[str, tuple[float, float] | str] = field(default_factory=dict)
    assumptions: tuple[str, ...] = ()


class ModelRegistry:
    """Runtime registry of available scientific models.

    The first implementation is intentionally in-memory. It gives future
    contributors a single location to declare model validity and lets UI/CLI
    code ask what is scientifically available instead of hard-coding options.
    """

    def __init__(self) -> None:
        self._models: dict[str, ModelCapability] = {}

    def register(self, capability: ModelCapability) -> None:
        """Register or replace a model capability."""
        self._models[capability.key] = capability

    def get(self, key: str) -> ModelCapability:
        """Return a model by key."""
        return self._models[key]

    def by_stage(self, stage: str) -> list[ModelCapability]:
        """Return all models declared for one lifecycle stage."""
        return [m for m in self._models.values() if m.stage == stage]
