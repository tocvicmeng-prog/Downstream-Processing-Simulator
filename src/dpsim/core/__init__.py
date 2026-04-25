"""Core architecture primitives for Downstream Processing Simulator.

The modules in this package are deliberately small and dependency-light. They
provide the clean-slate architecture layer that sits above the reused DPSim
solver stack:

* quantities with units and provenance;
* resolved parameters and source tracking;
* wet-lab process recipes;
* model registries and validation reports;
* result graphs for M1 -> M2 -> M3 lifecycle runs.

Downstream modules should prefer these objects at public boundaries. Existing
legacy solver dataclasses remain available for numerical kernels.
"""

from .quantities import Quantity
from .parameters import ParameterSource, ResolvedParameter, ParameterProvider
from .process_recipe import (
    EquipmentProfile,
    LifecycleStage,
    MaterialBatch,
    ProcessRecipe,
    ProcessStep,
    ProcessStepKind,
    TargetProductProfile,
    default_affinity_media_recipe,
)
from .m2_recipe_templates import available_m2_templates, m2_template_steps
from .result_graph import ResultEdge, ResultGraph, ResultNode
from .recipe_io import (
    RECIPE_SCHEMA_VERSION,
    load_process_recipe,
    process_recipe_from_dict,
    process_recipe_to_dict,
    recipe_from_simulation_parameters,
    save_process_recipe,
)
from .validation import (
    ValidationIssue,
    ValidationReport,
    ValidationSeverity,
    validate_model_manifest_domains,
)

__all__ = [
    "Quantity",
    "ParameterSource",
    "ResolvedParameter",
    "ParameterProvider",
    "EquipmentProfile",
    "LifecycleStage",
    "MaterialBatch",
    "ProcessRecipe",
    "ProcessStep",
    "ProcessStepKind",
    "TargetProductProfile",
    "default_affinity_media_recipe",
    "available_m2_templates",
    "m2_template_steps",
    "ResultEdge",
    "ResultGraph",
    "ResultNode",
    "RECIPE_SCHEMA_VERSION",
    "load_process_recipe",
    "process_recipe_from_dict",
    "process_recipe_to_dict",
    "recipe_from_simulation_parameters",
    "save_process_recipe",
    "ValidationIssue",
    "ValidationReport",
    "ValidationSeverity",
    "validate_model_manifest_domains",
]
