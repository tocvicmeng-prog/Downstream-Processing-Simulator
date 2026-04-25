"""Recipe-driven runners exposed at the lifecycle layer (v0.3.0 module B5).

The legacy ``PipelineOrchestrator`` from ``dpsim.pipeline.orchestrator`` is the
authoritative M1 simulation engine. This module wraps it with a recipe-driven
entry point so UI / CLI consumers can run M1 from a ``ProcessRecipe`` without
importing the legacy class directly. Routing through this layer satisfies the
architect-coherence-audit D1 finding (dual-API surface) for the M1 path.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dpsim.core.process_recipe import ProcessRecipe
from dpsim.datatypes import FullResult, RunContext, SimulationParameters
from dpsim.pipeline.orchestrator import PipelineOrchestrator
from dpsim.properties.database import PropertyDatabase

from .recipe_resolver import resolve_lifecycle_inputs

if TYPE_CHECKING:
    from pathlib import Path


def run_m1_from_recipe(
    recipe: ProcessRecipe,
    *,
    base_params: SimulationParameters | None = None,
    db: PropertyDatabase | None = None,
    output_dir: "Path | None" = None,
    run_context: RunContext | None = None,
    l2_mode: str = "empirical",
    crosslinker_key: str = "genipin",
    uv_intensity: float = 0.0,
    props_overrides: dict | None = None,
) -> FullResult:
    """Resolve a recipe and run M1 fabrication only.

    Convenience wrapper that pairs ``resolve_lifecycle_inputs`` with the
    legacy ``PipelineOrchestrator.run_single``. Intended as the single
    M1-only entry point for UI tabs and small CLI tools that should not
    drag in the full lifecycle orchestrator.

    Args:
        recipe: ProcessRecipe to resolve.
        base_params: Optional ``SimulationParameters`` to start from. Recipe
            quantities overwrite the relevant fields.
        db: Optional ``PropertyDatabase`` (default: a fresh one).
        output_dir: Optional output directory for ``PipelineOrchestrator``.
        run_context: Optional ``RunContext`` carrying calibration etc.
        l2_mode: L2 gelation solver mode ("empirical" / "ch_2d" / etc.).
        crosslinker_key: M1 crosslinker key (ignored for non-A+C families).
        uv_intensity: UV intensity for PEGDA-style crosslinkers.
        props_overrides: Per-family material-property overrides.

    Returns:
        A populated ``FullResult`` from the legacy pipeline.
    """
    resolved = resolve_lifecycle_inputs(recipe, base_params=base_params)
    params = resolved.parameters
    orchestrator = PipelineOrchestrator(db=db, output_dir=output_dir)
    return orchestrator.run_single(
        params,
        l2_mode=l2_mode,
        crosslinker_key=crosslinker_key,
        uv_intensity=uv_intensity,
        props_overrides=props_overrides,
        run_context=run_context,
    )


__all__ = ["run_m1_from_recipe"]
