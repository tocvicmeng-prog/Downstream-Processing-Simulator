"""Downstream Processing Simulator.

The package is a fork of the DPSim scientific stack, reorganized around a
clean-slate process lifecycle: M1 fabrication, M2 functionalization, and M3
affinity chromatography performance. The legacy L1-L4 fabrication solvers are
kept available while new process-recipe and result-graph abstractions are added
for future development.
"""

__version__ = "0.1.0"

from .datatypes import (
    SimulationParameters,
    MaterialProperties,
    BeadSizeDistributionPayload,
    M1WashingResult,
    EmulsificationResult,
    GelationTimingResult,
    GelationResult,
    CrosslinkingResult,
    MechanicalResult,
    FullResult,
)
from .pipeline.orchestrator import PipelineOrchestrator
from .properties.database import PropertyDatabase
from .lifecycle.orchestrator import DownstreamProcessOrchestrator, run_default_lifecycle

__all__ = [
    "SimulationParameters",
    "MaterialProperties",
    "BeadSizeDistributionPayload",
    "M1WashingResult",
    "EmulsificationResult",
    "GelationTimingResult",
    "GelationResult",
    "CrosslinkingResult",
    "MechanicalResult",
    "FullResult",
    "PipelineOrchestrator",
    "PropertyDatabase",
    "DownstreamProcessOrchestrator",
    "run_default_lifecycle",
    "run_pipeline",
    "__version__",
]


def run_pipeline(params: SimulationParameters | None = None, **kwargs) -> FullResult:
    """Run the full L1-L4 simulation pipeline.

    Convenience function for quick usage:
        from dpsim import run_pipeline
        result = run_pipeline()  # uses defaults
        result = run_pipeline(params)  # custom params
    """
    if params is None:
        params = SimulationParameters()
    orch = PipelineOrchestrator()
    return orch.run_single(params, **kwargs)

