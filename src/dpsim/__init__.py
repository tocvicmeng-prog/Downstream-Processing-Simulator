"""Downstream Processing Simulator.

The package is a fork of the upstream microsphere simulation stack,
re-scoped around a clean-slate process lifecycle: M1 fabrication,
M2 functionalization, and M3 affinity chromatography.

v0.5.0 (D1): the legacy top-level convenience exports
(``SimulationParameters``, ``FullResult``, ``run_pipeline``,
``PipelineOrchestrator``) have been removed from this module's public
API. They are still defined in their respective implementation modules
and remain available under their canonical paths:

  - ``from dpsim.datatypes import SimulationParameters, FullResult``
  - ``from dpsim.pipeline.orchestrator import PipelineOrchestrator``

Application code should use the lifecycle-layer entry points instead:

  - ``from dpsim.lifecycle import run_default_lifecycle, run_m1_from_recipe``
  - ``from dpsim.module3_performance.method_simulation import run_method_simulation``
  - ``from dpsim.core.process_recipe import default_affinity_media_recipe``
  - ``from dpsim.core.performance_recipe import performance_recipe_from_resolved``
"""

__version__ = "0.5.1"

from .lifecycle.orchestrator import (
    DownstreamProcessOrchestrator,
    run_default_lifecycle,
)

__all__ = [
    "DownstreamProcessOrchestrator",
    "run_default_lifecycle",
    "__version__",
]
