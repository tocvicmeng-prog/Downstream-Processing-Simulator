"""Resolve wet-lab process recipes into typed lifecycle solver inputs.

This module is the P1 adapter between the clean recipe layer and the inherited
numeric kernels. ``ProcessRecipe`` remains the single authoritative description
of M1/M2/M3 process inputs; the resolver records every recipe quantity in a
``ParameterProvider`` before converting it into legacy dataclasses.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass

from dpsim.core.parameters import ParameterProvider, ParameterSource, ResolvedParameter
from dpsim.core.process_recipe import (
    LifecycleStage,
    ProcessRecipe,
    ProcessStep,
    ProcessStepKind,
)
from dpsim.core.quantities import Quantity
from dpsim.core.validation import ValidationReport, ValidationSeverity
from dpsim.datatypes import SimulationParameters
from dpsim.module2_functionalization.acs import ACSSiteType
from dpsim.module2_functionalization.modification_steps import (
    ModificationStep,
    ModificationStepType,
)
from dpsim.module2_functionalization.reagent_profiles import REAGENT_PROFILES
from dpsim.module3_performance.hydrodynamics import ColumnGeometry
from dpsim.module3_performance.method import (
    BufferCondition,
    ChromatographyMethodStep,
    ChromatographyOperation,
)


@dataclass
class LifecycleResolvedInputs:
    """All recipe-derived inputs consumed by the lifecycle orchestrator."""

    recipe: ProcessRecipe
    provider: ParameterProvider
    parameters: SimulationParameters
    functionalization_steps: list[ModificationStep]
    column: ColumnGeometry
    m3_method_steps: list[ChromatographyMethodStep]
    m3_feed_concentration: float
    m3_flow_rate: float
    m3_feed_duration: float
    m3_total_time: float
    m3_n_z: int
    max_pressure_drop_Pa: float
    pump_pressure_limit_Pa: float
    max_residual_oil_volume_fraction: float
    max_residual_surfactant_concentration_kg_m3: float
    validation: ValidationReport

    @property
    def resolved_parameters(self) -> dict[str, ResolvedParameter]:
        """Resolved parameter audit trail keyed by stable parameter name."""
        return self.provider.as_dict()


_STAGE_PREFIX = {
    LifecycleStage.M1_FABRICATION: "M1",
    LifecycleStage.M2_FUNCTIONALIZATION: "M2",
    LifecycleStage.M3_PERFORMANCE: "M3",
    LifecycleStage.QC: "QC",
}

_ALIAS_BY_STAGE_KIND_KEY = {
    (LifecycleStage.M1_FABRICATION, ProcessStepKind.PREPARE_PHASE, "oil_temperature"):
        "M1.prepare_phase.oil_temperature",
    (LifecycleStage.M1_FABRICATION, ProcessStepKind.PREPARE_PHASE, "span80"):
        "M1.prepare_phase.span80",
    (LifecycleStage.M1_FABRICATION, ProcessStepKind.PREPARE_PHASE, "c_agarose"):
        "M1.prepare_phase.c_agarose",
    (LifecycleStage.M1_FABRICATION, ProcessStepKind.PREPARE_PHASE, "c_chitosan"):
        "M1.prepare_phase.c_chitosan",
    (LifecycleStage.M1_FABRICATION, ProcessStepKind.PREPARE_PHASE, "c_genipin"):
        "M1.prepare_phase.c_genipin",
    (LifecycleStage.M1_FABRICATION, ProcessStepKind.EMULSIFY, "rpm"):
        "M1.emulsify.rpm",
    (LifecycleStage.M1_FABRICATION, ProcessStepKind.EMULSIFY, "time"):
        "M1.emulsify.time",
    (LifecycleStage.M1_FABRICATION, ProcessStepKind.COOL_OR_GEL, "cooling_rate"):
        "M1.cool_or_gel.cooling_rate",
    (LifecycleStage.M1_FABRICATION, ProcessStepKind.COOL_OR_GEL, "initial_oil_carryover_fraction"):
        "M1.cool_or_gel.initial_oil_carryover_fraction",
    (LifecycleStage.M1_FABRICATION, ProcessStepKind.COOL_OR_GEL, "wash_cycles"):
        "M1.cool_or_gel.wash_cycles",
    (LifecycleStage.M1_FABRICATION, ProcessStepKind.COOL_OR_GEL, "wash_volume_ratio"):
        "M1.cool_or_gel.wash_volume_ratio",
    (LifecycleStage.M1_FABRICATION, ProcessStepKind.COOL_OR_GEL, "wash_mixing_efficiency"):
        "M1.cool_or_gel.wash_mixing_efficiency",
    (LifecycleStage.M1_FABRICATION, ProcessStepKind.COOL_OR_GEL, "oil_retention_factor"):
        "M1.cool_or_gel.oil_retention_factor",
    (LifecycleStage.M1_FABRICATION, ProcessStepKind.COOL_OR_GEL, "surfactant_retention_factor"):
        "M1.cool_or_gel.surfactant_retention_factor",
    (LifecycleStage.M3_PERFORMANCE, ProcessStepKind.PACK_COLUMN, "bed_height"):
        "M3.pack_column.bed_height",
    (LifecycleStage.M3_PERFORMANCE, ProcessStepKind.PACK_COLUMN, "column_diameter"):
        "M3.pack_column.column_diameter",
    (LifecycleStage.M3_PERFORMANCE, ProcessStepKind.PACK_COLUMN, "bed_porosity"):
        "M3.pack_column.bed_porosity",
    (LifecycleStage.M3_PERFORMANCE, ProcessStepKind.PACK_COLUMN, "packing_flow_rate"):
        "M3.pack_column.packing_flow_rate",
    (LifecycleStage.M3_PERFORMANCE, ProcessStepKind.EQUILIBRATE, "pH"):
        "M3.equilibrate.pH",
    (LifecycleStage.M3_PERFORMANCE, ProcessStepKind.EQUILIBRATE, "conductivity"):
        "M3.equilibrate.conductivity",
    (LifecycleStage.M3_PERFORMANCE, ProcessStepKind.EQUILIBRATE, "flow_rate"):
        "M3.equilibrate.flow_rate",
    (LifecycleStage.M3_PERFORMANCE, ProcessStepKind.EQUILIBRATE, "duration"):
        "M3.equilibrate.duration",
    (LifecycleStage.M3_PERFORMANCE, ProcessStepKind.LOAD, "pH"):
        "M3.load.pH",
    (LifecycleStage.M3_PERFORMANCE, ProcessStepKind.LOAD, "conductivity"):
        "M3.load.conductivity",
    (LifecycleStage.M3_PERFORMANCE, ProcessStepKind.LOAD, "feed_concentration"):
        "M3.load.feed_concentration",
    (LifecycleStage.M3_PERFORMANCE, ProcessStepKind.LOAD, "flow_rate"):
        "M3.load.flow_rate",
    (LifecycleStage.M3_PERFORMANCE, ProcessStepKind.LOAD, "feed_duration"):
        "M3.load.feed_duration",
    (LifecycleStage.M3_PERFORMANCE, ProcessStepKind.LOAD, "total_time"):
        "M3.load.total_time",
    (LifecycleStage.M3_PERFORMANCE, ProcessStepKind.LOAD, "residence_time"):
        "M3.load.residence_time",
    (LifecycleStage.M3_PERFORMANCE, ProcessStepKind.WASH, "pH"):
        "M3.wash.pH",
    (LifecycleStage.M3_PERFORMANCE, ProcessStepKind.WASH, "conductivity"):
        "M3.wash.conductivity",
    (LifecycleStage.M3_PERFORMANCE, ProcessStepKind.WASH, "flow_rate"):
        "M3.wash.flow_rate",
    (LifecycleStage.M3_PERFORMANCE, ProcessStepKind.WASH, "duration"):
        "M3.wash.duration",
    (LifecycleStage.M3_PERFORMANCE, ProcessStepKind.ELUTE, "pH"):
        "M3.elute.pH",
    (LifecycleStage.M3_PERFORMANCE, ProcessStepKind.ELUTE, "conductivity"):
        "M3.elute.conductivity",
    (LifecycleStage.M3_PERFORMANCE, ProcessStepKind.ELUTE, "flow_rate"):
        "M3.elute.flow_rate",
    (LifecycleStage.M3_PERFORMANCE, ProcessStepKind.ELUTE, "duration"):
        "M3.elute.duration",
    (LifecycleStage.M3_PERFORMANCE, ProcessStepKind.ELUTE, "gradient_start_pH"):
        "M3.elute.gradient_start_pH",
    (LifecycleStage.M3_PERFORMANCE, ProcessStepKind.ELUTE, "gradient_end_pH"):
        "M3.elute.gradient_end_pH",
}

_M2_WASH_KINDS = {
    ProcessStepKind.WASH,
    ProcessStepKind.STORAGE_BUFFER_EXCHANGE,
}

_M2_QUENCH_KINDS = {
    ProcessStepKind.QUENCH,
    ProcessStepKind.BLOCK_OR_QUENCH,
}

_EXPECTED_UNITS = {
    "oil_temperature": "K",
    "span80": "%",
    "c_agarose": "kg/m3",
    "c_chitosan": "kg/m3",
    "c_genipin": "mol/m3",
    "rpm": "rpm",
    "time": "s",
    "cooling_rate": "K/s",
    "initial_oil_carryover_fraction": "1",
    "wash_cycles": "1",
    "wash_volume_ratio": "1",
    "wash_mixing_efficiency": "1",
    "oil_retention_factor": "1",
    "surfactant_retention_factor": "1",
    "pH": "1",
    "temperature": "K",
    "reagent_concentration": "mol/m3",
    "bed_height": "m",
    "column_diameter": "m",
    "bed_porosity": "1",
    "packing_flow_rate": "m3/s",
    "feed_concentration": "mol/m3",
    "flow_rate": "m3/s",
    "feed_duration": "s",
    "total_time": "s",
    "duration": "s",
    "residence_time": "s",
    "conductivity": "mS/cm",
    "gradient_start_pH": "1",
    "gradient_end_pH": "1",
    "max_residual_oil_volume_fraction": "1",
    "max_residual_surfactant_concentration": "kg/m3",
}


def resolve_lifecycle_inputs(
    recipe: ProcessRecipe,
    base_params: SimulationParameters | None = None,
) -> LifecycleResolvedInputs:
    """Resolve a recipe into M1/M2/M3 solver inputs and validation gates.

    ``base_params`` is copied and used only for legacy fields not yet present in
    the recipe. Any field represented by a recipe ``Quantity`` is overwritten by
    the recipe-resolved value so M1/M2/M3 share one scientific source of truth.
    """

    validation = ValidationReport()
    provider = build_parameter_provider(recipe, validation)
    params = copy.deepcopy(base_params) if base_params is not None else SimulationParameters()

    _apply_m1_recipe_parameters(params, provider, validation)
    functionalization_steps = functionalization_steps_from_recipe(recipe, provider, validation)
    column = column_from_recipe(recipe, provider, validation)
    feed_conc = _resolve_value(
        provider, "M3.load.feed_concentration", "mol/m3", validation, "M3", default=1.0
    )
    flow_rate = _resolve_value(
        provider, "M3.load.flow_rate", "m3/s", validation, "M3", default=1e-8
    )
    feed_duration = _resolve_value(
        provider, "M3.load.feed_duration", "s", validation, "M3", default=600.0
    )
    total_time = _resolve_value(
        provider, "M3.load.total_time", "s", validation, "M3", default=1200.0
    )
    if total_time < feed_duration:
        validation.add(
            ValidationSeverity.BLOCKER,
            "M3_TIME_ORDER",
            "M3 total_time is shorter than feed_duration.",
            module="M3",
            recommendation="Set total_time >= feed_duration so the wash-out tail can be simulated.",
        )
    m3_method_steps = m3_method_steps_from_recipe(
        recipe=recipe,
        provider=provider,
        validation=validation,
        default_flow_rate=flow_rate,
        default_feed_concentration=feed_conc,
        default_feed_duration=feed_duration,
        default_total_time=total_time,
    )

    max_pressure = _resolve_value(
        provider, "target.max_pressure_drop", "Pa", validation, "M3", default=3e5
    )
    pump_limit = _resolve_value(
        provider, "equipment.pump_pressure_limit", "Pa", validation, "M3", default=3e5
    )
    max_residual_oil = _resolve_value(
        provider,
        "target.max_residual_oil_volume_fraction",
        "1",
        validation,
        "M1/M2/M3",
        default=0.01,
    )
    max_residual_surfactant = _resolve_value(
        provider,
        "target.max_residual_surfactant_concentration",
        "kg/m3",
        validation,
        "M1/M2/M3",
        default=0.5,
    )

    return LifecycleResolvedInputs(
        recipe=recipe,
        provider=provider,
        parameters=params,
        functionalization_steps=functionalization_steps,
        column=column,
        m3_method_steps=m3_method_steps,
        m3_feed_concentration=feed_conc,
        m3_flow_rate=flow_rate,
        m3_feed_duration=feed_duration,
        m3_total_time=total_time,
        m3_n_z=30,
        max_pressure_drop_Pa=max_pressure,
        pump_pressure_limit_Pa=pump_limit,
        max_residual_oil_volume_fraction=max_residual_oil,
        max_residual_surfactant_concentration_kg_m3=max_residual_surfactant,
        validation=validation,
    )


def build_parameter_provider(
    recipe: ProcessRecipe,
    validation: ValidationReport | None = None,
) -> ParameterProvider:
    """Register all recipe quantities as resolved parameter candidates."""

    report = validation or ValidationReport()
    provider = ParameterProvider()
    _add_parameter(
        provider,
        "target.max_pressure_drop",
        recipe.target.max_pressure_drop,
        report,
        "M3",
    )
    _add_parameter(
        provider,
        "target.max_residual_oil_volume_fraction",
        recipe.target.max_residual_oil_volume_fraction,
        report,
        "M1/M2/M3",
    )
    _add_parameter(
        provider,
        "target.max_residual_surfactant_concentration",
        recipe.target.max_residual_surfactant_concentration,
        report,
        "M1/M2/M3",
    )
    _add_parameter(
        provider,
        "equipment.pump_pressure_limit",
        recipe.equipment.pump_pressure_limit,
        report,
        "M3",
    )

    for step in recipe.steps:
        step_slug = _slug(step.name)
        stage_prefix = _STAGE_PREFIX.get(step.stage, step.stage.value)
        for key, value in step.parameters.items():
            if not isinstance(value, Quantity):
                continue
            canonical_name = f"{stage_prefix}.{step_slug}.{key}"
            _add_parameter(provider, canonical_name, value, report, stage_prefix)
            alias = _ALIAS_BY_STAGE_KIND_KEY.get((step.stage, step.kind, key))
            if alias:
                _add_parameter(provider, alias, value, report, stage_prefix)
    return provider


def functionalization_steps_from_recipe(
    recipe: ProcessRecipe,
    provider: ParameterProvider,
    validation: ValidationReport,
) -> list[ModificationStep]:
    """Convert M2 recipe operations into backend ``ModificationStep`` objects."""

    steps: list[ModificationStep] = []
    m2_process_steps = recipe.steps_for_stage(LifecycleStage.M2_FUNCTIONALIZATION)
    _validate_m2_stage_coverage(m2_process_steps, validation)
    for index, process_step in enumerate(m2_process_steps):
        step = _build_m2_step(process_step, index, provider, validation)
        if step is not None:
            steps.append(step)
    if not steps:
        validation.add(
            ValidationSeverity.BLOCKER,
            "M2_RECIPE_EMPTY",
            "Recipe contains no M2 functionalization steps.",
            module="M2",
            recommendation="Add activation, coupling, quench, and wash steps to the recipe.",
        )
    return steps


def column_from_recipe(
    recipe: ProcessRecipe,
    provider: ParameterProvider,
    validation: ValidationReport,
) -> ColumnGeometry:
    """Build the M3 column geometry from recipe-resolved parameters."""

    bed_height = _resolve_value(
        provider, "M3.pack_column.bed_height", "m", validation, "M3", default=0.10
    )
    diameter = _resolve_value(
        provider, "M3.pack_column.column_diameter", "m", validation, "M3", default=0.01
    )
    bed_porosity = _resolve_value(
        provider, "M3.pack_column.bed_porosity", "1", validation, "M3", default=0.38
    )
    if bed_height <= 0.0:
        validation.add(
            ValidationSeverity.BLOCKER,
            "M3_COLUMN_GEOMETRY",
            f"Column bed height must be positive, got {bed_height:g} m.",
            module="M3",
        )
        bed_height = 0.10
    if diameter <= 0.0:
        validation.add(
            ValidationSeverity.BLOCKER,
            "M3_COLUMN_GEOMETRY",
            f"Column diameter must be positive, got {diameter:g} m.",
            module="M3",
        )
        diameter = 0.01
    if not (0.20 <= bed_porosity <= 0.60):
        validation.add(
            ValidationSeverity.WARNING,
            "M3_COLUMN_POROSITY",
            (
                f"Bed porosity {bed_porosity:g} is outside the ordinary "
                "packed microsphere screening range [0.20, 0.60]."
            ),
            module="M3",
            recommendation="Confirm packing quality and pressure-flow data before using the M3 result quantitatively.",
        )
    bed_porosity = min(0.95, max(0.05, bed_porosity))
    return ColumnGeometry(diameter=diameter, bed_height=bed_height, bed_porosity=bed_porosity)


def m3_method_steps_from_recipe(
    recipe: ProcessRecipe,
    provider: ParameterProvider,
    validation: ValidationReport,
    *,
    default_flow_rate: float,
    default_feed_concentration: float,
    default_feed_duration: float,
    default_total_time: float,
) -> list[ChromatographyMethodStep]:
    """Convert M3 recipe operations into typed chromatography method steps."""

    method_steps: list[ChromatographyMethodStep] = []
    m3_steps = recipe.steps_for_stage(LifecycleStage.M3_PERFORMANCE)
    _validate_m3_stage_coverage(m3_steps, validation)
    for index, process_step in enumerate(m3_steps):
        operation = _m3_operation_from_kind(process_step.kind)
        if operation is None:
            continue
        step_prefix = f"{_STAGE_PREFIX[LifecycleStage.M3_PERFORMANCE]}.{_slug(process_step.name)}"
        default_duration = _default_m3_step_duration(
            operation,
            default_feed_duration=default_feed_duration,
        )
        duration_key = "feed_duration" if operation == ChromatographyOperation.LOAD else "duration"
        duration = _resolve_step_quantity(
            provider,
            step_prefix,
            duration_key,
            "s",
            validation,
            "M3",
            default=default_duration,
        )
        flow_key = "packing_flow_rate" if operation == ChromatographyOperation.PACK else "flow_rate"
        flow_rate = _resolve_step_quantity(
            provider,
            step_prefix,
            flow_key,
            "m3/s",
            validation,
            "M3",
            default=default_flow_rate,
        )
        if flow_rate <= 0.0:
            validation.add(
                ValidationSeverity.BLOCKER,
                "M3_METHOD_FLOW_RATE",
                f"{process_step.name}: flow rate must be positive, got {flow_rate:g} m3/s.",
                module="M3",
                recommendation="Set each M3 method step flow_rate or packing_flow_rate to a positive value.",
            )
            flow_rate = default_flow_rate
        buffer = BufferCondition(
            name=str(process_step.parameters.get("buffer_name", "")),
            pH=_resolve_step_quantity(
                provider,
                step_prefix,
                "pH",
                "1",
                validation,
                "M3",
                default=_default_m3_step_pH(operation),
            ),
            conductivity_mS_cm=_resolve_step_quantity(
                provider,
                step_prefix,
                "conductivity",
                "mS/cm",
                validation,
                "M3",
                default=_default_m3_step_conductivity(operation),
            ),
        )
        feed_conc = 0.0
        total_time = 0.0
        target_residence = 0.0
        if operation == ChromatographyOperation.LOAD:
            feed_conc = _resolve_step_quantity(
                provider,
                step_prefix,
                "feed_concentration",
                "mol/m3",
                validation,
                "M3",
                default=default_feed_concentration,
            )
            total_time = _resolve_step_quantity(
                provider,
                step_prefix,
                "total_time",
                "s",
                validation,
                "M3",
                default=default_total_time,
            )
            target_residence = _resolve_step_quantity(
                provider,
                step_prefix,
                "residence_time",
                "s",
                validation,
                "M3",
                default=0.0,
            )
        gradient_start = _optional_step_quantity(
            process_step,
            provider,
            step_prefix,
            "gradient_start_pH",
            "1",
            validation,
        )
        gradient_end = _optional_step_quantity(
            process_step,
            provider,
            step_prefix,
            "gradient_end_pH",
            "1",
            validation,
        )
        gradient_field = str(process_step.parameters.get("gradient_field", "")).strip()
        method_steps.append(
            ChromatographyMethodStep(
                name=process_step.name,
                operation=operation,
                duration_s=duration,
                flow_rate_m3_s=flow_rate,
                buffer=buffer,
                feed_concentration_mol_m3=feed_conc,
                total_time_s=total_time,
                gradient_field=gradient_field,
                gradient_start=gradient_start,
                gradient_end=gradient_end,
                target_residence_time_s=target_residence,
                metadata={"recipe_index": index},
            )
        )
    if not method_steps:
        validation.add(
            ValidationSeverity.BLOCKER,
            "M3_METHOD_EMPTY",
            "Recipe contains no M3 chromatography method steps.",
            module="M3",
            recommendation="Add pack, equilibrate, load, wash, and elute steps.",
        )
    return method_steps


def _m3_operation_from_kind(
    kind: ProcessStepKind,
) -> ChromatographyOperation | None:
    """Map recipe operation kind to the M3 method operation enum."""

    if kind == ProcessStepKind.PACK_COLUMN:
        return ChromatographyOperation.PACK
    if kind == ProcessStepKind.EQUILIBRATE:
        return ChromatographyOperation.EQUILIBRATE
    if kind == ProcessStepKind.LOAD:
        return ChromatographyOperation.LOAD
    if kind == ProcessStepKind.WASH:
        return ChromatographyOperation.WASH
    if kind == ProcessStepKind.ELUTE:
        return ChromatographyOperation.ELUTE
    if kind == ProcessStepKind.REGENERATE:
        return ChromatographyOperation.REGENERATE
    return None


def _validate_m3_stage_coverage(
    process_steps: list[ProcessStep],
    validation: ValidationReport,
) -> None:
    """Warn when an M3 recipe omits a core chromatography method stage."""

    kinds = {step.kind for step in process_steps}
    checks = [
        (
            ProcessStepKind.PACK_COLUMN in kinds,
            "M3_STAGE_PACK_MISSING",
            "M3 recipe has no explicit pack step.",
            "Add PACK_COLUMN with bed height, diameter, porosity, and packing-flow metadata.",
        ),
        (
            ProcessStepKind.EQUILIBRATE in kinds,
            "M3_STAGE_EQUILIBRATE_MISSING",
            "M3 recipe has no equilibration step.",
            "Add EQUILIBRATE with buffer pH, conductivity, flow rate, and duration.",
        ),
        (
            ProcessStepKind.LOAD in kinds,
            "M3_STAGE_LOAD_MISSING",
            "M3 recipe has no load step.",
            "Add LOAD with feed concentration, binding-buffer conditions, residence time, and flow rate.",
        ),
        (
            ProcessStepKind.WASH in kinds,
            "M3_STAGE_WASH_MISSING",
            "M3 recipe has no wash step.",
            "Add WASH with buffer pH, conductivity, flow rate, and UV/baseline assay expectations.",
        ),
        (
            ProcessStepKind.ELUTE in kinds,
            "M3_STAGE_ELUTE_MISSING",
            "M3 recipe has no elution step.",
            "Add ELUTE with pH/conductivity or gradient conditions and collection assumptions.",
        ),
    ]
    for ok, code, message, recommendation in checks:
        if not ok:
            validation.add(
                ValidationSeverity.WARNING,
                code,
                message,
                module="M3",
                recommendation=recommendation,
            )


def _default_m3_step_duration(
    operation: ChromatographyOperation,
    *,
    default_feed_duration: float,
) -> float:
    """Return conservative duration fallback for one M3 method operation."""

    if operation == ChromatographyOperation.LOAD:
        return default_feed_duration
    if operation in {
        ChromatographyOperation.EQUILIBRATE,
        ChromatographyOperation.WASH,
        ChromatographyOperation.ELUTE,
    }:
        return 300.0
    return 0.0


def _default_m3_step_pH(operation: ChromatographyOperation) -> float:
    """Return pH fallback for one M3 method operation."""

    if operation == ChromatographyOperation.ELUTE:
        return 3.5
    if operation == ChromatographyOperation.REGENERATE:
        return 13.0
    return 7.4


def _default_m3_step_conductivity(operation: ChromatographyOperation) -> float:
    """Return conductivity fallback [mS/cm] for one M3 method operation."""

    if operation == ChromatographyOperation.ELUTE:
        return 5.0
    return 15.0


def _optional_step_quantity(
    process_step: ProcessStep,
    provider: ParameterProvider,
    step_prefix: str,
    key: str,
    target_unit: str,
    validation: ValidationReport,
) -> float | None:
    """Resolve a step quantity only when the recipe explicitly includes it."""

    if key not in process_step.parameters:
        return None
    return _resolve_step_quantity(
        provider,
        step_prefix,
        key,
        target_unit,
        validation,
        "M3",
        default=0.0,
    )


def _apply_m1_recipe_parameters(
    params: SimulationParameters,
    provider: ParameterProvider,
    validation: ValidationReport,
) -> None:
    """Overwrite M1 legacy parameters with recipe-resolved values."""

    params.emulsification.rpm = _resolve_value(
        provider, "M1.emulsify.rpm", "rpm", validation, "M1", params.emulsification.rpm
    )
    params.emulsification.t_emulsification = _resolve_value(
        provider, "M1.emulsify.time", "s", validation, "M1", params.emulsification.t_emulsification
    )
    params.formulation.T_oil = _resolve_value(
        provider, "M1.prepare_phase.oil_temperature", "K", validation, "M1", params.formulation.T_oil
    )
    params.formulation.cooling_rate = _resolve_value(
        provider, "M1.cool_or_gel.cooling_rate", "K/s", validation, "M1", params.formulation.cooling_rate
    )
    params.formulation.m1_initial_oil_carryover_fraction = _resolve_value(
        provider,
        "M1.cool_or_gel.initial_oil_carryover_fraction",
        "1",
        validation,
        "M1",
        params.formulation.m1_initial_oil_carryover_fraction,
    )
    params.formulation.m1_wash_cycles = int(round(_resolve_value(
        provider,
        "M1.cool_or_gel.wash_cycles",
        "1",
        validation,
        "M1",
        params.formulation.m1_wash_cycles,
    )))
    params.formulation.m1_wash_volume_ratio = _resolve_value(
        provider,
        "M1.cool_or_gel.wash_volume_ratio",
        "1",
        validation,
        "M1",
        params.formulation.m1_wash_volume_ratio,
    )
    params.formulation.m1_wash_mixing_efficiency = _resolve_value(
        provider,
        "M1.cool_or_gel.wash_mixing_efficiency",
        "1",
        validation,
        "M1",
        params.formulation.m1_wash_mixing_efficiency,
    )
    params.formulation.m1_oil_retention_factor = _resolve_value(
        provider,
        "M1.cool_or_gel.oil_retention_factor",
        "1",
        validation,
        "M1",
        params.formulation.m1_oil_retention_factor,
    )
    params.formulation.m1_surfactant_retention_factor = _resolve_value(
        provider,
        "M1.cool_or_gel.surfactant_retention_factor",
        "1",
        validation,
        "M1",
        params.formulation.m1_surfactant_retention_factor,
    )
    _validate_m1_washing_parameters(params, validation)
    span80_pct = _resolve_value(
        provider, "M1.prepare_phase.span80", "%", validation, "M1", params.formulation.c_span80_vol_pct
    )
    params.formulation.c_span80_vol_pct = span80_pct
    params.formulation.c_span80 = params.formulation.c_span80_from_vol_pct

    # v0.3.0 (B4): polymer concentrations promoted into the typed recipe.
    # Recipe is now the single source of truth for c_agarose, c_chitosan, c_genipin.
    params.formulation.c_agarose = _resolve_value(
        provider,
        "M1.prepare_phase.c_agarose",
        "kg/m3",
        validation,
        "M1",
        params.formulation.c_agarose,
    )
    params.formulation.c_chitosan = _resolve_value(
        provider,
        "M1.prepare_phase.c_chitosan",
        "kg/m3",
        validation,
        "M1",
        params.formulation.c_chitosan,
    )
    params.formulation.c_genipin = _resolve_value(
        provider,
        "M1.prepare_phase.c_genipin",
        "mol/m3",
        validation,
        "M1",
        params.formulation.c_genipin,
    )


def _validate_m1_washing_parameters(
    params: SimulationParameters,
    validation: ValidationReport,
) -> None:
    """Validate recipe-owned M1 washing parameters before numerical export."""

    f = params.formulation
    checks = [
        (
            0.0 <= f.m1_initial_oil_carryover_fraction <= 1.0,
            "M1_WASH_INITIAL_OIL",
            "initial_oil_carryover_fraction must be in [0, 1].",
        ),
        (
            f.m1_wash_cycles >= 0,
            "M1_WASH_CYCLES",
            "wash_cycles must be non-negative.",
        ),
        (
            f.m1_wash_volume_ratio >= 0.0,
            "M1_WASH_VOLUME",
            "wash_volume_ratio must be non-negative.",
        ),
        (
            0.0 <= f.m1_wash_mixing_efficiency <= 1.0,
            "M1_WASH_MIXING",
            "wash_mixing_efficiency must be in [0, 1].",
        ),
        (
            f.m1_oil_retention_factor > 0.0,
            "M1_WASH_RETENTION",
            "oil_retention_factor must be positive.",
        ),
        (
            f.m1_surfactant_retention_factor > 0.0,
            "M1_WASH_RETENTION",
            "surfactant_retention_factor must be positive.",
        ),
    ]
    for ok, code, message in checks:
        if not ok:
            validation.add(
                ValidationSeverity.BLOCKER,
                code,
                message,
                module="M1",
                recommendation="Correct the M1 cool/wash recipe before running M2/M3.",
            )


def _build_m2_step(
    process_step: ProcessStep,
    index: int,
    provider: ParameterProvider,
    validation: ValidationReport,
) -> ModificationStep | None:
    """Create one backend chemistry step from one wet-lab recipe operation."""

    reagent_key = str(process_step.parameters.get("reagent_key", "")).strip()
    if not reagent_key and process_step.kind in _M2_WASH_KINDS:
        reagent_key = "wash_buffer"
    reagent_profile = REAGENT_PROFILES.get(reagent_key)
    if reagent_profile is None:
        validation.add(
            ValidationSeverity.BLOCKER,
            "M2_REAGENT_UNKNOWN",
            f"Step {index + 1} references unknown reagent_key {reagent_key!r}.",
            module="M2",
            recommendation="Use a key present in REAGENT_PROFILES or add a validated reagent profile.",
        )
        return None

    step_type = _step_type_from_process_kind(process_step.kind, reagent_profile)
    if step_type is None:
        validation.add(
            ValidationSeverity.WARNING,
            "M2_STEP_SKIPPED",
            f"Step {index + 1} ({process_step.name}) has no backend chemistry mapping.",
            module="M2",
        )
        return None

    target_acs = _target_acs_from_step(process_step, reagent_profile, validation)
    product_acs = reagent_profile.product_acs
    step_prefix = f"{_STAGE_PREFIX[LifecycleStage.M2_FUNCTIONALIZATION]}.{_slug(process_step.name)}"
    temperature = _resolve_step_quantity(
        provider,
        step_prefix,
        "temperature",
        "K",
        validation,
        "M2",
        default=reagent_profile.temperature_default,
    )
    time = _resolve_step_quantity(
        provider,
        step_prefix,
        "time",
        "s",
        validation,
        "M2",
        default=reagent_profile.time_default,
    )
    ph = _resolve_step_quantity(
        provider,
        step_prefix,
        "pH",
        "1",
        validation,
        "M2",
        default=reagent_profile.ph_optimum,
    )
    concentration = _resolve_step_quantity(
        provider,
        step_prefix,
        "reagent_concentration",
        "mol/m3",
        validation,
        "M2",
        default=0.0 if step_type == ModificationStepType.WASHING else 10.0,
    )

    _validate_m2_reaction_window(
        process_step=process_step,
        reagent_key=reagent_key,
        temperature=temperature,
        ph=ph,
        concentration=concentration,
        validation=validation,
    )

    return ModificationStep(
        step_type=step_type,
        reagent_key=reagent_key,
        target_acs=target_acs,
        product_acs=product_acs,
        temperature=temperature,
        time=time,
        ph=ph,
        reagent_concentration=concentration,
        stoichiometry=reagent_profile.stoichiometry,
    )


def _step_type_from_process_kind(
    kind: ProcessStepKind,
    reagent_profile,
) -> ModificationStepType | None:
    """Map process operation kind to the existing M2 backend enum."""

    if kind == ProcessStepKind.CROSSLINK:
        return ModificationStepType.SECONDARY_CROSSLINKING
    if kind == ProcessStepKind.ACTIVATE:
        return ModificationStepType.ACTIVATION
    if kind == ProcessStepKind.INSERT_SPACER:
        return ModificationStepType.SPACER_ARM
    if kind == ProcessStepKind.COUPLE_LIGAND:
        if reagent_profile.reaction_type == "protein_coupling" or reagent_profile.is_macromolecule:
            return ModificationStepType.PROTEIN_COUPLING
        return ModificationStepType.LIGAND_COUPLING
    if kind == ProcessStepKind.METAL_CHARGE:
        return ModificationStepType.METAL_CHARGING
    if kind == ProcessStepKind.PROTEIN_PRETREATMENT:
        return ModificationStepType.PROTEIN_PRETREATMENT
    if kind in _M2_QUENCH_KINDS:
        return ModificationStepType.QUENCHING
    if kind in _M2_WASH_KINDS:
        return ModificationStepType.WASHING
    return None


def _validate_m2_stage_coverage(
    process_steps: list[ProcessStep],
    validation: ValidationReport,
) -> None:
    """Warn when an M2 recipe omits core wet-lab functionalization stages."""

    kinds = {step.kind for step in process_steps}
    checks = [
        (
            ProcessStepKind.ACTIVATE in kinds,
            "M2_STAGE_ACTIVATION_MISSING",
            "M2 recipe has no explicit activation step.",
            "Add an activation operation or document a pre-activated starting matrix.",
        ),
        (
            ProcessStepKind.COUPLE_LIGAND in kinds,
            "M2_STAGE_COUPLING_MISSING",
            "M2 recipe has no ligand/protein coupling step.",
            "Add a COUPLE_LIGAND operation with a validated reagent profile.",
        ),
        (
            bool(kinds.intersection(_M2_QUENCH_KINDS)),
            "M2_STAGE_QUENCH_MISSING",
            "M2 recipe has no blocking/quenching step.",
            "Add QUENCH or BLOCK_OR_QUENCH to cap residual reactive groups.",
        ),
        (
            bool(kinds.intersection(_M2_WASH_KINDS)),
            "M2_STAGE_WASH_MISSING",
            "M2 recipe has no washing or storage buffer exchange step.",
            "Add WASH and final STORAGE_BUFFER_EXCHANGE operations with assay gates.",
        ),
    ]
    for ok, code, message, recommendation in checks:
        if not ok:
            validation.add(
                ValidationSeverity.WARNING,
                code,
                message,
                module="M2",
                recommendation=recommendation,
            )


def _target_acs_from_step(
    process_step: ProcessStep,
    reagent_profile,
    validation: ValidationReport,
) -> ACSSiteType:
    """Resolve a step target ACS, allowing wash steps to state it explicitly."""

    raw_target = process_step.parameters.get("target_acs")
    if isinstance(raw_target, str):
        try:
            return ACSSiteType(raw_target)
        except ValueError:
            validation.add(
                ValidationSeverity.BLOCKER,
                "M2_ACS_TARGET_UNKNOWN",
                f"Step {process_step.name!r} references unknown target_acs {raw_target!r}.",
                module="M2",
            )
    return reagent_profile.target_acs


def _validate_m2_reaction_window(
    process_step: ProcessStep,
    reagent_key: str,
    temperature: float,
    ph: float,
    concentration: float,
    validation: ValidationReport,
) -> None:
    """Add backend validation issues for chemistry and wet-lab constraints."""

    reagent_profile = REAGENT_PROFILES[reagent_key]
    if not (0.0 <= ph <= 14.0):
        validation.add(
            ValidationSeverity.BLOCKER,
            "M2_PH_RANGE",
            f"{process_step.name}: pH {ph:g} is outside physical aqueous range [0, 14].",
            module="M2",
        )
    if ph < reagent_profile.ph_min or ph > reagent_profile.ph_max:
        validation.add(
            ValidationSeverity.WARNING,
            "M2_REAGENT_PH_DOMAIN",
            (
                f"{process_step.name}: pH {ph:g} is outside {reagent_key} "
                f"profile domain [{reagent_profile.ph_min:g}, {reagent_profile.ph_max:g}]."
            ),
            module="M2",
            recommendation="Adjust buffer pH or add calibration data for this reagent window.",
        )
    if not (273.15 <= temperature <= 373.15):
        validation.add(
            ValidationSeverity.BLOCKER,
            "M2_TEMPERATURE_RANGE",
            (
                f"{process_step.name}: temperature {temperature:g} K is outside "
                "ordinary aqueous wet-lab range [273.15, 373.15] K."
            ),
            module="M2",
        )
    if temperature < reagent_profile.temperature_min or temperature > reagent_profile.temperature_max:
        validation.add(
            ValidationSeverity.WARNING,
            "M2_REAGENT_TEMPERATURE_DOMAIN",
            (
                f"{process_step.name}: temperature {temperature:g} K is outside "
                f"{reagent_key} profile domain "
                f"[{reagent_profile.temperature_min:g}, {reagent_profile.temperature_max:g}] K."
            ),
            module="M2",
            recommendation="Use profile-default temperature or provide calibrated kinetics.",
        )
    if concentration < 0.0:
        validation.add(
            ValidationSeverity.BLOCKER,
            "M2_REAGENT_CONCENTRATION",
            f"{process_step.name}: reagent concentration {concentration:g} mol/m3 is negative.",
            module="M2",
        )


def _resolve_step_quantity(
    provider: ParameterProvider,
    step_prefix: str,
    key: str,
    target_unit: str,
    validation: ValidationReport,
    module: str,
    default: float,
) -> float:
    """Resolve a step-local quantity from the provider with a numeric fallback."""

    return _resolve_value(
        provider,
        f"{step_prefix}.{key}",
        target_unit,
        validation,
        module,
        default=default,
    )


def _resolve_value(
    provider: ParameterProvider,
    name: str,
    target_unit: str,
    validation: ValidationReport,
    module: str,
    default: float,
) -> float:
    """Resolve a named parameter and convert it to the required unit."""

    try:
        resolved = provider.resolve(name)
    except KeyError:
        return float(default)
    try:
        return float(resolved.quantity.as_unit(target_unit).value)
    except ValueError:
        validation.add(
            ValidationSeverity.BLOCKER,
            "UNIT_CONSISTENCY",
            f"{name}={resolved.quantity.describe()} cannot be converted to {target_unit}.",
            module=module,
            recommendation="Fix the recipe unit so it matches the expected solver basis.",
        )
        return float(default)


def _add_parameter(
    provider: ParameterProvider,
    name: str,
    quantity: Quantity,
    validation: ValidationReport,
    module: str,
) -> None:
    """Register one quantity and immediately check its expected unit, if known."""

    key = name.rsplit(".", 1)[-1]
    expected_unit = _EXPECTED_UNITS.get(key)
    if expected_unit is not None:
        try:
            quantity.as_unit(expected_unit)
        except ValueError:
            validation.add(
                ValidationSeverity.BLOCKER,
                "UNIT_CONSISTENCY",
                f"{name}={quantity.describe()} cannot be converted to {expected_unit}.",
                module=module,
                recommendation="Use a compatible lab unit before running the lifecycle simulation.",
            )
    provider.add(
        ResolvedParameter(
            name=name,
            quantity=quantity,
            source_kind=_source_kind_from_quantity(quantity),
            evidence_note=quantity.note,
        )
    )


def _source_kind_from_quantity(quantity: Quantity) -> ParameterSource:
    """Infer a provider priority class from recipe quantity provenance text."""

    source = quantity.source.lower()
    if "user" in source or "recipe" in source:
        return ParameterSource.USER_INPUT
    if "calibration" in source:
        return ParameterSource.CALIBRATION
    if "fit" in source:
        return ParameterSource.FITTED
    if "literature" in source or "profile" in source:
        return ParameterSource.LITERATURE
    if "infer" in source:
        return ParameterSource.INFERRED
    return ParameterSource.DEFAULT


def _slug(value: str) -> str:
    """Create a stable provider key segment from a wet-lab step name."""

    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "step"
