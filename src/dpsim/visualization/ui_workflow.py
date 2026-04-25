"""Lifecycle-first UI workflow helpers for P6.

P6 moves the user experience from isolated M1/M2/M3 tabs toward one wet-lab
lifecycle: target profile, fabrication recipe, chemistry recipe, column
method, simulation, validation/evidence review, and calibration comparison.
This module provides small pure helpers plus a Streamlit overview panel so the
existing UI can migrate incrementally without losing the recipe-native P1
boundary.
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from dpsim.core.process_recipe import LifecycleStage, ProcessRecipe, ProcessStepKind
from dpsim.core.quantities import Quantity
from dpsim.core.validation import ValidationReport
from dpsim.datatypes import ModelManifest


UI_SOURCE = "streamlit_ui"
RUN_HISTORY_KEY = "_lifecycle_run_history"
MAX_RUN_HISTORY = 10
WORKFLOW_STATUS_COMPLETE = "complete"
WORKFLOW_STATUS_READY = "ready"
WORKFLOW_STATUS_BLOCKED = "blocked"
WORKFLOW_STATUS_PENDING = "pending"


@dataclass(frozen=True)
class WorkflowStepState:
    """One stage in the P6 lifecycle UI workflow."""

    step_id: str
    label: str
    status: str
    detail: str = ""


def build_lifecycle_workflow_state(
    recipe: ProcessRecipe,
    session_state: Mapping[str, Any] | None = None,
) -> list[WorkflowStepState]:
    """Return P6 workflow step readiness from recipe and current UI state."""

    store = session_state or {}
    target_ok = _target_profile_ready(recipe)
    m1_ok = _has_stage_kinds(
        recipe,
        LifecycleStage.M1_FABRICATION,
        {ProcessStepKind.PREPARE_PHASE, ProcessStepKind.EMULSIFY, ProcessStepKind.COOL_OR_GEL},
    )
    m2_ok = _has_stage_kinds(
        recipe,
        LifecycleStage.M2_FUNCTIONALIZATION,
        {ProcessStepKind.ACTIVATE, ProcessStepKind.COUPLE_LIGAND},
    )
    m3_ok = _has_stage_kinds(
        recipe,
        LifecycleStage.M3_PERFORMANCE,
        {
            ProcessStepKind.PACK_COLUMN,
            ProcessStepKind.EQUILIBRATE,
            ProcessStepKind.LOAD,
            ProcessStepKind.WASH,
            ProcessStepKind.ELUTE,
        },
    )
    result_ok = _has_any_result(store)
    validation_ok = _has_validation_or_evidence(store)
    calibration_ok = _calibration_entry_count(store) > 0

    return [
        WorkflowStepState(
            "target",
            "Target product",
            WORKFLOW_STATUS_COMPLETE if target_ok else WORKFLOW_STATUS_PENDING,
            _target_detail(recipe),
        ),
        WorkflowStepState(
            "m1_recipe",
            "M1 fabrication recipe",
            WORKFLOW_STATUS_COMPLETE if m1_ok else WORKFLOW_STATUS_BLOCKED,
            _stage_detail(recipe, LifecycleStage.M1_FABRICATION),
        ),
        WorkflowStepState(
            "m2_recipe",
            "M2 chemistry recipe",
            WORKFLOW_STATUS_COMPLETE if m2_ok else WORKFLOW_STATUS_BLOCKED,
            _stage_detail(recipe, LifecycleStage.M2_FUNCTIONALIZATION),
        ),
        WorkflowStepState(
            "m3_method",
            "M3 column method",
            WORKFLOW_STATUS_COMPLETE if m3_ok else WORKFLOW_STATUS_BLOCKED,
            _stage_detail(recipe, LifecycleStage.M3_PERFORMANCE),
        ),
        WorkflowStepState(
            "run",
            "Run simulation",
            WORKFLOW_STATUS_COMPLETE if result_ok else WORKFLOW_STATUS_READY,
            _run_detail(store),
        ),
        WorkflowStepState(
            "validation",
            "Validation and evidence",
            WORKFLOW_STATUS_COMPLETE if validation_ok else WORKFLOW_STATUS_PENDING,
            _validation_detail(store),
        ),
        WorkflowStepState(
            "calibration",
            "Calibration comparison",
            WORKFLOW_STATUS_COMPLETE if calibration_ok else WORKFLOW_STATUS_PENDING,
            f"{_calibration_entry_count(store)} calibration entries loaded",
        ),
    ]


def validation_report_rows(report: ValidationReport | None) -> list[dict[str, str]]:
    """Convert a backend ``ValidationReport`` into table rows for UI display."""

    if report is None:
        return []
    rows: list[dict[str, str]] = []
    for issue in report.issues:
        rows.append(
            {
                "severity": issue.severity.value,
                "module": issue.module,
                "code": issue.code,
                "message": issue.message,
                "recommendation": issue.recommendation,
            }
        )
    return rows


def update_target_profile(
    recipe: ProcessRecipe,
    *,
    name: str,
    ligand: str,
    analyte: str,
    bead_d50_um: float,
    pore_nm: float,
    min_modulus_kPa: float,
    max_pressure_bar: float,
    max_residual_oil_fraction: float,
    max_residual_surfactant_kg_m3: float,
    notes: str = "",
) -> ProcessRecipe:
    """Update recipe target fields from P6 target-product controls.

    The target profile is a process-development contract, so the UI writes it
    directly into ``ProcessRecipe`` rather than keeping a separate target form
    state. Quantities are tagged with ``streamlit_ui`` provenance so later
    validation, protocol export, and lifecycle orchestration can audit where
    the design intent came from.
    """

    recipe.target.name = str(name).strip() or recipe.target.name
    recipe.target.target_ligand = str(ligand).strip() or recipe.target.target_ligand
    recipe.target.target_analyte = str(analyte).strip() or recipe.target.target_analyte
    recipe.target.bead_d50 = Quantity(float(bead_d50_um), "um", source=UI_SOURCE, lower=0.0)
    recipe.target.pore_size = Quantity(float(pore_nm), "nm", source=UI_SOURCE, lower=0.0)
    recipe.target.min_modulus = Quantity(float(min_modulus_kPa), "kPa", source=UI_SOURCE, lower=0.0)
    recipe.target.max_pressure_drop = Quantity(float(max_pressure_bar), "bar", source=UI_SOURCE, lower=0.0)
    recipe.target.max_residual_oil_volume_fraction = Quantity(
        float(max_residual_oil_fraction),
        "fraction",
        source=UI_SOURCE,
        lower=0.0,
        upper=1.0,
        note="P6 target-product profile limit for M1 wash carryover.",
    )
    recipe.target.max_residual_surfactant_concentration = Quantity(
        float(max_residual_surfactant_kg_m3),
        "kg/m3",
        source=UI_SOURCE,
        lower=0.0,
        note="P6 target-product profile limit for residual surfactant carryover.",
    )
    if notes:
        recipe.target.notes = str(notes)
    return recipe


def store_lifecycle_result(
    session_state: MutableMapping[str, Any],
    lifecycle_result: Any,
    *,
    run_id: str = "",
) -> None:
    """Store a lifecycle run plus legacy aliases consumed by existing panels."""

    session_state["lifecycle_result"] = lifecycle_result
    validation = getattr(lifecycle_result, "validation", None)
    if validation is not None:
        session_state["validation_report"] = validation
    m1_result = getattr(lifecycle_result, "m1_result", None)
    if m1_result is not None:
        session_state["result"] = m1_result
    m2_result = getattr(lifecycle_result, "m2_microsphere", None)
    if m2_result is not None:
        session_state["m2_result"] = m2_result
    m3_method = getattr(lifecycle_result, "m3_method", None)
    if m3_method is not None:
        session_state["m3_result_method"] = m3_method
        load_breakthrough = getattr(m3_method, "load_breakthrough", None)
        if load_breakthrough is not None:
            session_state["m3_result_bt"] = load_breakthrough
    m3_breakthrough = getattr(lifecycle_result, "m3_breakthrough", None)
    if m3_breakthrough is not None:
        session_state["m3_result_bt"] = m3_breakthrough
    _append_lifecycle_run_history(session_state, lifecycle_result, run_id=run_id)


def lifecycle_result_summary_rows(lifecycle_result: Any | None) -> list[dict[str, str]]:
    """Return compact run-summary rows for the P6 result view."""

    if lifecycle_result is None:
        return []
    rows: list[dict[str, str]] = []
    weakest = getattr(lifecycle_result, "weakest_evidence_tier", None)
    if weakest is not None:
        rows.append({"metric": "Weakest evidence tier", "value": getattr(weakest, "value", str(weakest))})
    validation = getattr(lifecycle_result, "validation", None)
    if validation is not None:
        rows.extend(
            [
                {"metric": "Validation blockers", "value": str(len(getattr(validation, "blockers", [])))},
                {"metric": "Validation warnings", "value": str(len(getattr(validation, "warnings", [])))},
            ]
        )
    m3_method = getattr(lifecycle_result, "m3_method", None)
    operability = getattr(m3_method, "operability", None)
    if operability is not None:
        rows.extend(
            [
                {
                    "metric": "M3 pressure drop",
                    "value": f"{getattr(operability, 'pressure_drop_Pa', 0.0) / 1e5:.3g} bar",
                },
                {
                    "metric": "Bed compression",
                    "value": f"{getattr(operability, 'bed_compression_fraction', 0.0):.3g}",
                },
            ]
        )
    return rows


def lifecycle_run_history_rows(session_state: Mapping[str, Any]) -> list[dict[str, str]]:
    """Return recent lifecycle runs stored by the Streamlit workflow."""

    return [dict(row) for row in session_state.get(RUN_HISTORY_KEY, [])]


def scientific_diagnostic_rows(lifecycle_result: Any | None) -> list[dict[str, str]]:
    """Return scientist-facing M1/M2/M3 diagnostics from the result graph."""

    if lifecycle_result is None or getattr(lifecycle_result, "graph", None) is None:
        return []
    graph = lifecycle_result.graph
    rows: list[dict[str, str]] = []
    metric_plan = {
        "M1": [
            ("bead_d50_m", "Bead d50", "um", "DSD target alignment"),
            ("bead_d10_m", "Bead d10", "um", "Fine-particle packing risk"),
            ("bead_d90_m", "Bead d90", "um", "Coarse-tail mass-transfer risk"),
            ("pore_size_m", "Pore size", "nm", "Protein accessibility"),
            ("residual_oil_limit_ratio", "Residual oil / target", "fraction", "M2/M3 carryover gate"),
            ("residual_surfactant_limit_ratio", "Residual surfactant / target", "fraction", "M2/M3 carryover gate"),
        ],
        "M2": [
            ("functional_ligand_density", "Functional ligand density", "mol/m2", "Capacity precursor"),
            ("activity_retention", "Activity retention", "fraction", "Ligand activity"),
            ("ligand_leaching_fraction", "Ligand leaching fraction", "fraction", "Leachables risk"),
            ("free_protein_wash_fraction", "Free protein wash fraction", "fraction", "Coupling/washing completeness"),
            ("estimated_q_max", "Estimated qmax", "mol/m3", "M3 capacity contract"),
        ],
        "FMC": [
            ("estimated_q_max", "Contract qmax", "mol/m3", "M2-to-M3 capacity handoff"),
            ("q_max_confidence", "Qmax confidence", "", "Evidence gate"),
            ("m3_support_level", "M3 support level", "", "Evidence gate"),
        ],
        "DSD": [
            ("n_quantiles", "DSD representatives", "", "Distribution transfer coverage"),
            ("represented_mass_fraction", "Represented mass fraction", "fraction", "DSD transfer coverage"),
            ("d10_m", "DSD d10", "um", "Fine-particle packing risk"),
            ("d50_m", "DSD d50", "um", "Central bead size"),
            ("d90_m", "DSD d90", "um", "Coarse-tail mass-transfer risk"),
            ("pressure_drop_weighted_p95_Pa", "Pressure p95", "bar", "Packed-bed operability"),
            ("max_bed_compression", "Maximum bed compression", "fraction", "Packed-bed operability"),
            ("dbc_10_weighted_p50", "DBC10 p50", "mol/m3", "DSD-resolved capacity"),
            ("dbc_10_weighted_p95", "DBC10 p95", "mol/m3", "DSD-resolved capacity"),
        ],
        "M3": [
            ("dbc_10pct", "DBC10", "mol/m3", "Dynamic capacity"),
            ("method_pressure_drop_Pa", "Pressure drop", "bar", "Column pressure gate"),
            ("method_bed_compression_fraction", "Bed compression", "fraction", "Column compression gate"),
            ("particle_reynolds", "Particle Reynolds", "", "Flow-regime validity"),
            ("axial_peclet", "Axial Peclet", "", "Dispersion validity"),
            ("flow_maldistribution_risk", "Flow maldistribution risk", "", "Packed-bed quality"),
            ("protein_a_q_max_mol_m3", "Protein A qmax", "mol/m3", "Binding model capacity"),
            ("protein_a_cycle_lifetime_to_70pct", "Cycle lifetime to 70pct capacity", "cycles", "Lifetime screen"),
            ("protein_a_leaching_risk", "Protein A leaching risk", "", "Ligand leaching screen"),
            ("loaded_elution_recovery_fraction", "Elution recovery", "fraction", "Elution performance"),
        ],
    }

    for node_id, metrics in metric_plan.items():
        node = graph.nodes.get(node_id)
        if node is None:
            continue
        diagnostics = node.diagnostics or {}
        for key, label, display_unit, interpretation in metrics:
            if key not in diagnostics:
                continue
            value = diagnostics[key]
            rows.append(
                {
                    "stage": node_id,
                    "metric": label,
                    "value": _format_diagnostic_value(value, key, display_unit),
                    "interpretation": interpretation,
                    "wet_lab_followup": _wet_lab_followup_for_metric(node_id, key),
                }
            )
    return rows


def calibration_comparison_rows(
    session_state: Mapping[str, Any],
    lifecycle_result: Any | None = None,
) -> list[dict[str, str]]:
    """Compare loaded calibration entries with simulated lifecycle metrics."""

    result = lifecycle_result or session_state.get("lifecycle_result")
    cal_store = session_state.get("_cal_store")
    rows: list[dict[str, str]] = []
    for entry in getattr(cal_store, "entries", []):
        measured = _safe_float(getattr(entry, "measured_value", None))
        units = str(getattr(entry, "units", ""))
        match = _simulated_metric_for_calibration(entry, result)
        base = {
            "profile": str(getattr(entry, "profile_key", "")),
            "measurement_type": str(getattr(entry, "measurement_type", "")),
            "parameter": str(getattr(entry, "parameter_name", "")),
            "measured": _format_number(measured),
            "units": units,
            "confidence": str(getattr(entry, "confidence", "")),
            "source": str(getattr(entry, "source_reference", "")),
        }
        if match is None:
            rows.append(
                {
                    **base,
                    "simulated": "not_mapped",
                    "absolute_delta": "",
                    "relative_delta_pct": "",
                    "assessment": "No direct simulated metric is mapped for this assay yet.",
                    "action": "Keep as provenance/QC evidence or add a metric mapping.",
                }
            )
            continue
        simulated_value, simulated_unit, label = match
        simulated_display_value, display_units = _convert_simulated_to_display_unit(
            simulated_value,
            simulated_unit,
            units,
        )
        delta = (
            None
            if measured is None or simulated_display_value is None
            else simulated_display_value - measured
        )
        relative = (
            None
            if delta is None or measured is None or abs(measured) <= 1.0e-12
            else 100.0 * delta / measured
        )
        rows.append(
            {
                **base,
                "simulated": f"{_format_number(simulated_display_value)} {display_units}".strip(),
                "absolute_delta": _format_number(delta),
                "relative_delta_pct": _format_number(relative),
                "assessment": _calibration_agreement_assessment(relative),
                "action": _calibration_agreement_action(relative, label),
            }
        )
    return rows


def dsd_distribution_chart_rows(lifecycle_result: Any | None) -> list[dict[str, float | str]]:
    """Return chart-ready M1 bead-size distribution rows."""

    if lifecycle_result is None:
        return []
    contract = getattr(lifecycle_result, "m1_contract", None)
    dsd = getattr(contract, "bead_size_distribution", None)
    if dsd is None:
        return []
    diameters = _to_float_list(getattr(dsd, "diameter_bins_m", []))
    volume_fraction = _to_float_list(getattr(dsd, "volume_fraction", []))
    number_density = _to_float_list(getattr(dsd, "number_density", []))
    volume_cdf = _to_float_list(getattr(dsd, "volume_cdf", []))
    n_rows = min(len(diameters), len(volume_fraction))
    rows: list[dict[str, float | str]] = []
    for index in range(n_rows):
        rows.append(
            {
                "bin": index + 1,
                "bead_diameter_um": diameters[index] * 1.0e6,
                "volume_fraction": volume_fraction[index],
                "number_density": number_density[index] if index < len(number_density) else 0.0,
                "volume_cdf": volume_cdf[index] if index < len(volume_cdf) else 0.0,
                "source": str(getattr(dsd, "source", "")),
            }
        )
    return rows


def dsd_variant_chart_rows(lifecycle_result: Any | None) -> list[dict[str, float | str]]:
    """Return chart-ready DSD downstream representative rows."""

    if lifecycle_result is None:
        return []
    rows: list[dict[str, float | str]] = []
    for variant in getattr(lifecycle_result, "dsd_variants", []) or []:
        rows.append(
            {
                "quantile": float(getattr(variant, "quantile", 0.0)),
                "mass_fraction": float(getattr(variant, "mass_fraction", 0.0)),
                "bead_diameter_um": float(getattr(variant, "bead_diameter_m", 0.0)) * 1.0e6,
                "qmax_mol_m3": float(getattr(variant, "estimated_q_max_mol_m3", 0.0)),
                "pressure_bar": float(getattr(variant, "pressure_drop_Pa", 0.0)) / 1.0e5,
                "bed_compression_fraction": float(getattr(variant, "bed_compression_fraction", 0.0)),
                "dbc10_mol_m3": float(getattr(variant, "dbc_10pct_mol_m3", 0.0)),
                "representative_source": str(getattr(variant, "representative_source", "")),
            }
        )
    return rows


def breakthrough_curve_rows(
    lifecycle_result: Any | None,
    *,
    max_points: int = 500,
) -> list[dict[str, float | str]]:
    """Return chart-ready M3 load breakthrough and elution traces."""

    if lifecycle_result is None:
        return []
    rows: list[dict[str, float | str]] = []
    breakthrough = getattr(lifecycle_result, "m3_breakthrough", None)
    rows.extend(_trace_rows_from_result(breakthrough, "load_breakthrough", max_points=max_points))
    method = getattr(lifecycle_result, "m3_method", None)
    rows.extend(_trace_rows_from_result(getattr(method, "loaded_elution", None), "loaded_elution", max_points=max_points))
    return rows


def pressure_profile_rows(lifecycle_result: Any | None) -> list[dict[str, float | str]]:
    """Return chart-ready pressure/compression rows for M3 method operations."""

    if lifecycle_result is None:
        return []
    method = getattr(lifecycle_result, "m3_method", None)
    rows: list[dict[str, float | str]] = []
    for index, step in enumerate(getattr(method, "step_results", []) or [], 1):
        operation = getattr(step, "operation", "")
        rows.append(
            {
                "step_index": index,
                "step": str(getattr(step, "name", "")),
                "operation": getattr(operation, "value", str(operation)),
                "pressure_bar": float(getattr(step, "pressure_drop_Pa", 0.0)) / 1.0e5,
                "bed_compression_fraction": float(getattr(step, "bed_compression_fraction", 0.0)),
                "residence_time_min": float(getattr(step, "residence_time_s", 0.0)) / 60.0,
                "column_volumes": float(getattr(step, "column_volumes", 0.0)),
                "flow_mL_min": float(getattr(step, "flow_rate_m3_s", 0.0)) * 60.0e6,
            }
        )
    return rows


def ligand_capacity_chart_rows(lifecycle_result: Any | None) -> list[dict[str, float | str]]:
    """Return chart-ready ligand, capacity, and chromatographic performance metrics."""

    diagnostics = _result_graph_diagnostics(lifecycle_result)
    metric_plan = [
        ("M2", "functional_ligand_density", "Functional ligand density", "mol/m2"),
        ("M2", "activity_retention", "Activity retention", "fraction"),
        ("M2", "ligand_leaching_fraction", "Ligand leaching", "fraction"),
        ("M2", "free_protein_wash_fraction", "Free protein wash", "fraction"),
        ("FMC", "estimated_q_max", "FMC qmax", "mol/m3"),
        ("M3", "protein_a_q_max_mol_m3", "M3 Protein A qmax", "mol/m3"),
        ("M3", "dbc_10pct", "DBC10", "mol/m3"),
        ("M3", "loaded_elution_recovery_fraction", "Elution recovery", "fraction"),
    ]
    rows: list[dict[str, float | str]] = []
    for stage, key, label, unit in metric_plan:
        value = _safe_float(diagnostics.get(stage, {}).get(key))
        if value is None:
            continue
        rows.append(
            {
                "stage": stage,
                "metric": label,
                "value": value,
                "units": unit,
            }
        )
    return rows


def calibration_overlay_chart_rows(
    session_state: Mapping[str, Any],
    lifecycle_result: Any | None = None,
) -> list[dict[str, float | str]]:
    """Return chart-ready measured/simulated pairs for mapped calibration entries."""

    result = lifecycle_result or session_state.get("lifecycle_result")
    rows: list[dict[str, float | str]] = []
    cal_store = session_state.get("_cal_store")
    for entry in getattr(cal_store, "entries", []) or []:
        measured = _safe_float(getattr(entry, "measured_value", None))
        match = _simulated_metric_for_calibration(entry, result)
        if measured is None or match is None:
            continue
        simulated_value, simulated_unit, label = match
        units = str(getattr(entry, "units", "")) or simulated_unit
        simulated_display_value, display_units = _convert_simulated_to_display_unit(
            simulated_value,
            simulated_unit,
            units,
        )
        if simulated_display_value is None:
            continue
        metric = f"{label} ({getattr(entry, 'source_reference', '')})".strip()
        rows.append({"metric": metric, "series": "measured", "value": measured, "units": display_units})
        rows.append({"metric": metric, "series": "simulated", "value": simulated_display_value, "units": display_units})
    return rows


def evidence_ladder_rows(
    lifecycle_result: Any | None = None,
    *,
    session_state: Mapping[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Build rows describing evidence tier, assumptions, and calibration refs."""

    rows: list[dict[str, str]] = []
    if lifecycle_result is not None and getattr(lifecycle_result, "graph", None) is not None:
        for node_id, node in lifecycle_result.graph.nodes.items():
            rows.append(_manifest_row(node_id, node.label, node.manifest, node.wet_lab_caveats))
        return rows

    store = session_state or {}
    m1_result = store.get("result")
    if m1_result is not None:
        for node_id, attr, label in (
            ("M1.L1", "emulsification", "M1 emulsification"),
            ("M1.L2", "gelation", "M1 gelation/pore"),
            ("M1.L3", "crosslinking", "M1 reinforcement"),
            ("M1.L4", "mechanical", "M1 mechanics"),
        ):
            result_obj = getattr(m1_result, attr, None)
            rows.append(_manifest_row(node_id, label, getattr(result_obj, "model_manifest", None), []))
    m2_result = store.get("m2_result")
    if m2_result is not None:
        rows.append(_manifest_row("M2", "M2 functionalization", getattr(m2_result, "model_manifest", None), []))
    for key, label in (
        ("m3_result_method", "M3 Protein A method"),
        ("m3_result_bt", "M3 breakthrough"),
        ("m3_result_ge", "M3 gradient elution"),
        ("m3_result_cat", "M3 catalysis"),
    ):
        result_obj = store.get(key)
        if result_obj is not None:
            rows.append(_manifest_row(key, label, getattr(result_obj, "model_manifest", None), []))
    return [row for row in rows if row["evidence_tier"] != "not_available"]


def calibration_status_rows(session_state: Mapping[str, Any] | None = None) -> list[dict[str, str]]:
    """Return loaded calibration entries as compact UI rows."""

    store = session_state or {}
    cal_store = store.get("_cal_store")
    rows: list[dict[str, str]] = []
    for entry in getattr(cal_store, "entries", []):
        rows.append(
            {
                "profile": str(getattr(entry, "profile_key", "")),
                "parameter": str(getattr(entry, "parameter_name", "")),
                "value": f"{getattr(entry, 'measured_value', '')}",
                "units": str(getattr(entry, "units", "")),
                "confidence": str(getattr(entry, "confidence", "")),
                "measurement_type": str(getattr(entry, "measurement_type", "")),
                "source": str(getattr(entry, "source_reference", "")),
                "target_module": str(getattr(entry, "target_module", "")),
                "fit_method": str(getattr(entry, "fit_method", "")),
                "posterior_uncertainty": f"{getattr(entry, 'posterior_uncertainty', '')}",
            }
        )
    return rows


def process_recipe_protocol_markdown(
    recipe: ProcessRecipe,
    lifecycle_result: Any | None = None,
) -> str:
    """Export a lifecycle SOP draft from the current recipe and result state."""

    lines = [
        "# DPSim Wet-Lab Protocol Outline",
        "",
        "> SOP draft generated from ProcessRecipe. This is a process-development "
        "protocol scaffold, not a GMP batch record or release specification.",
        "",
        "## Target Product Profile",
        f"- Product: {recipe.target.name}",
        f"- Ligand/analyte: {recipe.target.target_ligand} / {recipe.target.target_analyte}",
        f"- Bead d50 target: {recipe.target.bead_d50.describe()}",
        f"- Pore target: {recipe.target.pore_size.describe()}",
        f"- Minimum modulus: {recipe.target.min_modulus.describe()}",
        f"- Maximum pressure drop: {recipe.target.max_pressure_drop.describe()}",
        f"- Residual oil limit: {recipe.target.max_residual_oil_volume_fraction.describe()}",
        f"- Residual surfactant limit: {recipe.target.max_residual_surfactant_concentration.describe()}",
        f"- Target notes: {recipe.target.notes}",
        "",
        "## Materials And Equipment",
        f"- Polymer family: {recipe.material_batch.polymer_family}",
        f"- Polymer lot: {recipe.material_batch.polymer_lot}",
        f"- Oil lot: {recipe.material_batch.oil_lot}",
        f"- Surfactant lot: {recipe.material_batch.surfactant_lot}",
        f"- Ligand lot: {recipe.material_batch.ligand_lot}",
        f"- Emulsifier: {recipe.equipment.emulsifier}",
        f"- Vessel: {recipe.equipment.vessel}",
        f"- Column: {recipe.equipment.column_id}",
        f"- Pump pressure limit: {recipe.equipment.pump_pressure_limit.describe()}",
        "",
        "## Acceptance Criteria",
        "- M1: bead-size distribution, pore structure, swelling, compression/modulus, residual oil, and residual surfactant must be measured or explicitly waived.",
        "- M2: activation/coupling chemistry must close site balance and provide ligand density, retained activity, leaching, and free-protein wash evidence.",
        "- M3: packed-bed pressure-flow, compression, DBC/breakthrough, elution recovery, ligand leaching, and cycle-lifetime evidence must be reviewed before decision use.",
        "- Evidence tier must not be stronger than the weakest calibrated upstream media contract.",
        "",
        "## Execution Records Required",
        "- Record lot identifiers, actual masses/volumes, pH, conductivity, temperature, start/end times, wash volumes, and operator deviations.",
        "- Preserve raw microscopy or laser-diffraction files, assay calibration curves, chromatograms, pressure traces, and fraction analytics.",
        "- Attach all CalibrationStore entries used for simulation and confirm their valid domains cover this recipe.",
        "",
    ]
    if lifecycle_result is not None:
        rows = lifecycle_result_summary_rows(lifecycle_result)
        if rows:
            lines.append("## Simulated Run Summary")
            for row in rows:
                lines.append(f"- {row['metric']}: {row['value']}")
            lines.append("")

    for stage in (
        LifecycleStage.M1_FABRICATION,
        LifecycleStage.M2_FUNCTIONALIZATION,
        LifecycleStage.M3_PERFORMANCE,
    ):
        lines.append(f"## {stage.value}")
        lines.append(f"- Objective: {_stage_objective(stage)}")
        lines.append(f"- Hold/release gate: {_stage_release_gate(stage)}")
        steps = recipe.steps_for_stage(stage)
        if not steps:
            lines.append("- No steps defined.")
            lines.append("")
            continue
        for index, step in enumerate(steps, 1):
            lines.append(f"### {index}. {step.name}")
            lines.append(f"- Operation: {step.kind.value}")
            for key, value in step.parameters.items():
                if hasattr(value, "describe"):
                    rendered = value.describe()
                else:
                    rendered = str(value)
                lines.append(f"- {key}: {rendered}")
            if step.qc_required:
                lines.append("- QC:")
                for item in step.qc_required:
                    lines.append(f"  - {item}")
            if step.notes:
                lines.append(f"- Notes: {step.notes}")
            lines.append("- Required record: actual setpoint, observed value, time, operator initials, and deviation note.")
            lines.append("")
    if lifecycle_result is not None and getattr(lifecycle_result, "graph", None) is not None:
        lines.append("## Wet-Lab Caveats From Result Graph")
        for node_id, node in lifecycle_result.graph.nodes.items():
            for caveat in getattr(node, "wet_lab_caveats", []):
                lines.append(f"- {node_id}: {caveat}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_target_product_profile_editor(
    recipe: ProcessRecipe,
    session_state: MutableMapping[str, Any],
) -> None:
    """Render target-product controls and persist them into ``ProcessRecipe``."""

    import streamlit as st

    from dpsim.visualization.ui_recipe import save_process_recipe_state

    st.subheader("Target Product Profile")
    st.caption(
        "Define the intended media performance before adjusting fabrication, "
        "functionalization, or column-method details."
    )

    col_a, col_b = st.columns(2)
    with col_a:
        name = st.text_input("Product name", value=recipe.target.name, key="p6_target_name")
        ligand = st.text_input("Affinity ligand", value=recipe.target.target_ligand, key="p6_target_ligand")
        analyte = st.text_input("Target analyte", value=recipe.target.target_analyte, key="p6_target_analyte")
        bead_d50_um = st.number_input(
            "Target bead d50 (um)",
            min_value=1.0,
            max_value=1000.0,
            value=float(recipe.target.bead_d50.value),
            step=5.0,
            key="p6_target_bead_d50_um",
        )
        pore_nm = st.number_input(
            "Target pore size (nm)",
            min_value=1.0,
            max_value=1000.0,
            value=float(recipe.target.pore_size.value),
            step=5.0,
            key="p6_target_pore_nm",
        )
    with col_b:
        min_modulus_kPa = st.number_input(
            "Minimum modulus (kPa)",
            min_value=0.1,
            max_value=10000.0,
            value=float(recipe.target.min_modulus.value),
            step=1.0,
            key="p6_target_modulus_kpa",
        )
        max_pressure_bar = st.number_input(
            "Maximum pressure drop (bar)",
            min_value=0.01,
            max_value=100.0,
            value=float(recipe.target.max_pressure_drop.value),
            step=0.1,
            key="p6_target_pressure_bar",
        )
        max_residual_oil_fraction = st.number_input(
            "Maximum residual oil fraction",
            min_value=0.0,
            max_value=1.0,
            value=float(recipe.target.max_residual_oil_volume_fraction.value),
            step=0.001,
            format="%.4f",
            key="p6_target_oil_fraction",
        )
        max_residual_surfactant_kg_m3 = st.number_input(
            "Maximum residual surfactant (kg/m3)",
            min_value=0.0,
            max_value=100.0,
            value=float(recipe.target.max_residual_surfactant_concentration.value),
            step=0.05,
            key="p6_target_surfactant",
        )
        notes = st.text_area("Target notes", value=recipe.target.notes, key="p6_target_notes")

    if st.button("Apply target profile", type="primary", use_container_width=True):
        update_target_profile(
            recipe,
            name=name,
            ligand=ligand,
            analyte=analyte,
            bead_d50_um=bead_d50_um,
            pore_nm=pore_nm,
            min_modulus_kPa=min_modulus_kPa,
            max_pressure_bar=max_pressure_bar,
            max_residual_oil_fraction=max_residual_oil_fraction,
            max_residual_surfactant_kg_m3=max_residual_surfactant_kg_m3,
            notes=notes,
        )
        save_process_recipe_state(session_state, recipe)
        st.success("Target profile stored in the lifecycle ProcessRecipe.")
        st.rerun()

    st.dataframe(
        [
            {"field": "Product", "value": recipe.target.name},
            {"field": "Ligand/analyte", "value": f"{recipe.target.target_ligand} / {recipe.target.target_analyte}"},
            {"field": "Bead d50", "value": recipe.target.bead_d50.describe()},
            {"field": "Pore size", "value": recipe.target.pore_size.describe()},
            {"field": "Minimum modulus", "value": recipe.target.min_modulus.describe()},
            {"field": "Max pressure drop", "value": recipe.target.max_pressure_drop.describe()},
            {
                "field": "Residual oil limit",
                "value": recipe.target.max_residual_oil_volume_fraction.describe(),
            },
            {
                "field": "Residual surfactant limit",
                "value": recipe.target.max_residual_surfactant_concentration.describe(),
            },
        ],
        hide_index=True,
        use_container_width=True,
    )


def render_lifecycle_run_panel(
    recipe: ProcessRecipe,
    session_state: MutableMapping[str, Any],
) -> None:
    """Render the full lifecycle run control using ``ProcessRecipe`` directly."""

    import streamlit as st

    from dpsim.datatypes import RunContext
    from dpsim.lifecycle import DownstreamProcessOrchestrator
    from dpsim.runtime_paths import default_output_dir

    st.subheader("Run Lifecycle Simulation")
    st.caption(
        "Executes M1 fabrication, M2 chemistry, and M3 column performance from "
        "the current ProcessRecipe. Calibration entries loaded in the UI are "
        "passed through RunContext."
    )

    options = st.columns(3)
    with options[0]:
        propagate_dsd = st.checkbox(
            "Propagate bead-size distribution",
            value=True,
            key="p6_run_propagate_dsd",
        )
    with options[1]:
        dsd_mode = st.selectbox(
            "DSD transfer mode",
            ["representative", "adaptive"],
            index=0,
            key="p6_run_dsd_mode",
        )
    with options[2]:
        dsd_run_breakthrough = st.checkbox(
            "Run DSD breakthrough screen",
            value=False,
            key="p6_run_dsd_breakthrough",
        )

    # v0.4.8: threaded orchestrator path. The previous synchronous
    # `orchestrator.run(...)` blocked the Streamlit script for 5–30 s,
    # so Stop clicks couldn't reach Python during a solve. We now run
    # the orchestrator in a background daemon thread and poll its
    # state on each rerun, sleeping 500 ms between polls. The Stop
    # button delivers its click on the next rerun, request_cancel()
    # sets the threading flag, the scipy-events hook in solve_ivp
    # sees it on the next integration step, and the solve halts.
    import time

    from dpsim.lifecycle.cancellation import RunCancelledError
    from dpsim.lifecycle.threaded_runner import (
        BackgroundRun,
        run_in_background,
    )

    BG_RUN_KEY = "_dpsim_background_run"
    POLL_INTERVAL_S = 0.5

    if st.button("Run full lifecycle", type="primary", use_container_width=True,
                 disabled=session_state.get(BG_RUN_KEY) is not None):
        run_id = "streamlit-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        context = RunContext(
            calibration_store=session_state.get("_cal_store"),
            run_id=run_id,
            notes="P6 lifecycle workflow run from Streamlit.",
        )
        orchestrator = DownstreamProcessOrchestrator(
            output_dir=default_output_dir("streamlit_lifecycle"),
        )
        bg_run = run_in_background(
            orchestrator.run,
            kwargs=dict(
                recipe=recipe,
                run_context=context,
                propagate_dsd=propagate_dsd,
                dsd_mode=dsd_mode,
                dsd_run_breakthrough=dsd_run_breakthrough,
            ),
        )
        session_state[BG_RUN_KEY] = bg_run
        session_state["_dpsim_run_id"] = run_id
        try:
            from dpsim.visualization.run_rail import set_run_state

            set_run_state("running")
        except ImportError:  # pragma: no cover — visualization always present
            pass
        st.rerun()

    # Poll the background run on every rerun. While alive, sleep then
    # rerun so the WebSocket layer can deliver Stop clicks; on
    # completion, capture the result + reset state.
    bg_run: BackgroundRun | None = session_state.get(BG_RUN_KEY)
    if bg_run is not None:
        if bg_run.is_running():
            elapsed = bg_run.elapsed_seconds()
            st.info(f"Running M1 → M2 → M3 lifecycle · {elapsed:.1f} s elapsed. "
                    "Click Stop in the run rail to cancel.")
            # Brief sleep, then rerun so click events get a chance to
            # land. The 500 ms cadence balances responsiveness with
            # CPU cost.
            time.sleep(POLL_INTERVAL_S)
            st.rerun()
        else:
            # Worker finished — collect outcome.
            del session_state[BG_RUN_KEY]
            run_id = session_state.pop("_dpsim_run_id", "")
            try:
                from dpsim.visualization.run_rail import (
                    clear_cancel,
                    set_run_state,
                )
            except ImportError:  # pragma: no cover
                clear_cancel = lambda: None  # noqa: E731
                set_run_state = lambda _s: None  # noqa: E731

            if bg_run.cancelled:
                st.info("Run cancelled by user (mid-solve).")
                clear_cancel()
                set_run_state("idle")
            elif bg_run.exception is not None:
                # Re-raise to preserve the existing error contract for
                # test / dev workflows; production users see the trace.
                st.error(f"Lifecycle simulation failed: {bg_run.exception}")
                set_run_state("error", error_msg=str(bg_run.exception))
                if not isinstance(bg_run.exception, RunCancelledError):
                    raise bg_run.exception  # pragma: no cover - defensive
            else:
                store_lifecycle_result(
                    session_state, bg_run.result, run_id=run_id,
                )
                st.success(
                    f"Lifecycle simulation completed in "
                    f"{bg_run.elapsed_seconds():.1f} s."
                )
                set_run_state("done")
                clear_cancel()

    result = session_state.get("lifecycle_result")
    rows = lifecycle_result_summary_rows(result)
    if rows:
        st.dataframe(rows, hide_index=True, use_container_width=True)
    else:
        st.info("No full lifecycle run has been executed in this session.")


def render_lifecycle_results_panel(
    recipe: ProcessRecipe,
    session_state: Mapping[str, Any],
) -> None:
    """Render permanent P6 validation, evidence, protocol, and calibration views."""

    import streamlit as st

    result = session_state.get("lifecycle_result")
    validation_report = _session_validation_report(session_state)
    evidence_rows = evidence_ladder_rows(result, session_state=session_state)
    diagnostic_rows = scientific_diagnostic_rows(result)
    protocol_md = process_recipe_protocol_markdown(recipe, result)
    history_rows = lifecycle_run_history_rows(session_state)

    st.subheader("Validation And Evidence")
    summary_rows = lifecycle_result_summary_rows(result)
    if summary_rows:
        st.dataframe(summary_rows, hide_index=True, use_container_width=True)

    tabs = st.tabs(
        [
            "Run summary",
            "Validation report",
            "Evidence ladder",
            "Scientific diagnostics",
            "Visual comparisons",
            "Wet-lab SOP",
            "Calibration comparison",
            "Run history",
        ]
    )
    with tabs[0]:
        if summary_rows:
            st.dataframe(summary_rows, hide_index=True, use_container_width=True)
        else:
            st.info("No full lifecycle run has been executed in this session.")
    with tabs[1]:
        rows = validation_report_rows(validation_report)
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.info("No validation report is available yet. Run the full lifecycle simulation first.")
    with tabs[2]:
        if evidence_rows:
            st.dataframe(evidence_rows, use_container_width=True, hide_index=True)
        else:
            st.info("No model evidence manifests are available yet.")
    with tabs[3]:
        if diagnostic_rows:
            st.dataframe(diagnostic_rows, use_container_width=True, hide_index=True)
        else:
            st.info("No lifecycle diagnostics are available yet.")
    with tabs[4]:
        render_scientific_visuals_panel(session_state)
    with tabs[5]:
        st.download_button(
            "Export wet-lab SOP draft",
            data=protocol_md,
            file_name="dpsim_wet_lab_sop_draft.md",
            mime="text/markdown",
            key="p6_protocol_download_results",
            use_container_width=True,
        )
        st.code(protocol_md[:6000], language="markdown")
    with tabs[6]:
        render_calibration_status_panel(session_state)
    with tabs[7]:
        if history_rows:
            st.dataframe(history_rows, use_container_width=True, hide_index=True)
        else:
            st.info("No lifecycle run history is available yet.")


def render_calibration_status_panel(session_state: Mapping[str, Any]) -> None:
    """Render loaded calibration entries and their workflow role."""

    import streamlit as st

    rows = calibration_status_rows(session_state)
    if rows:
        st.markdown("**Loaded calibration entries**")
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info(
            "No calibration entries are loaded. Add wet-lab calibration data "
            "before claiming calibrated evidence tiers."
        )
    comparison_rows = calibration_comparison_rows(session_state)
    if comparison_rows:
        st.markdown("**Measured vs simulated comparison**")
        st.dataframe(comparison_rows, use_container_width=True, hide_index=True)


def render_scientific_visuals_panel(session_state: Mapping[str, Any]) -> None:
    """Render P6+ visual scientific comparisons from lifecycle result payloads."""

    import streamlit as st

    result = session_state.get("lifecycle_result")
    dsd_rows = dsd_distribution_chart_rows(result)
    variant_rows = dsd_variant_chart_rows(result)
    breakthrough_rows = breakthrough_curve_rows(result)
    pressure_rows = pressure_profile_rows(result)
    ligand_rows = ligand_capacity_chart_rows(result)
    overlay_rows = calibration_overlay_chart_rows(session_state, result)

    tabs = st.tabs(["DSD", "Breakthrough", "Pressure", "Ligand/Capacity", "Calibration Overlay"])
    with tabs[0]:
        if dsd_rows:
            dsd_df = _dataframe_or_rows(dsd_rows)
            st.markdown("**M1 bead-size distribution**")
            st.bar_chart(dsd_df, x="bead_diameter_um", y="volume_fraction")
            st.line_chart(dsd_df, x="bead_diameter_um", y="volume_cdf")
            st.dataframe(dsd_rows, use_container_width=True, hide_index=True)
        else:
            st.info("No M1 bead-size distribution payload is available yet.")
        if variant_rows:
            variant_df = _dataframe_or_rows(variant_rows)
            st.markdown("**DSD representative transfer into M3**")
            st.line_chart(variant_df, x="bead_diameter_um", y=["qmax_mol_m3", "dbc10_mol_m3"])
            st.line_chart(variant_df, x="bead_diameter_um", y=["pressure_bar", "bed_compression_fraction"])
            st.dataframe(variant_rows, use_container_width=True, hide_index=True)
    with tabs[1]:
        if breakthrough_rows:
            bt_df = _dataframe_or_rows(breakthrough_rows)
            st.markdown("**M3 concentration traces**")
            st.line_chart(bt_df, x="time_min", y="C_outlet_mol_m3", color="trace")
            st.markdown("**M3 normalized outlet and UV traces**")
            st.line_chart(bt_df, x="time_min", y=["normalized_concentration", "uv_signal_mAU"])
            st.dataframe(breakthrough_rows, use_container_width=True, hide_index=True)
        else:
            st.info("No M3 breakthrough or loaded-elution trace is available yet.")
    with tabs[2]:
        if pressure_rows:
            pressure_df = _dataframe_or_rows(pressure_rows)
            st.markdown("**Method pressure and compression by operation**")
            st.bar_chart(pressure_df, x="step", y="pressure_bar")
            st.line_chart(pressure_df, x="step_index", y=["bed_compression_fraction", "residence_time_min"])
            st.dataframe(pressure_rows, use_container_width=True, hide_index=True)
        else:
            st.info("No method step pressure profile is available yet.")
    with tabs[3]:
        if ligand_rows:
            st.markdown("**Ligand, capacity, and performance metrics**")
            for units in sorted({str(row["units"]) for row in ligand_rows}):
                subset = [row for row in ligand_rows if row["units"] == units]
                st.caption(units)
                st.bar_chart(_dataframe_or_rows(subset), x="metric", y="value")
            st.dataframe(ligand_rows, use_container_width=True, hide_index=True)
        else:
            st.info("No M2/M3 ligand-capacity diagnostics are available yet.")
    with tabs[4]:
        if overlay_rows:
            st.markdown("**Calibration overlay-ready measured/simulated pairs**")
            for units in sorted({str(row["units"]) for row in overlay_rows}):
                subset = [row for row in overlay_rows if row["units"] == units]
                st.caption(units)
                st.bar_chart(_dataframe_or_rows(subset), x="metric", y="value", color="series")
            st.dataframe(overlay_rows, use_container_width=True, hide_index=True)
        else:
            st.info("No mapped calibration entries are available for visual overlay.")


def render_lifecycle_workflow_panel(recipe: ProcessRecipe, session_state: Mapping[str, Any]) -> None:
    """Render the P6 lifecycle workflow scaffold in Streamlit."""

    import streamlit as st

    workflow = build_lifecycle_workflow_state(recipe, session_state)
    st.subheader("Lifecycle Workflow")
    st.dataframe(
        [
            {"step": step.label, "status": step.status, "detail": step.detail}
            for step in workflow
        ],
        use_container_width=True,
        hide_index=True,
    )

    with st.expander("Lifecycle Review", expanded=False):
        validation_report = _session_validation_report(session_state)
        lifecycle_result = session_state.get("lifecycle_result")
        evidence_rows = evidence_ladder_rows(lifecycle_result, session_state=session_state)
        calibration_rows = calibration_status_rows(session_state)
        protocol_md = process_recipe_protocol_markdown(recipe, lifecycle_result)

        review_tabs = st.tabs(["Validation", "Evidence", "Protocol", "Calibration"])
        with review_tabs[0]:
            rows = validation_report_rows(validation_report)
            if rows:
                st.dataframe(rows, use_container_width=True, hide_index=True)
            else:
                st.info("No lifecycle validation report is available yet.")
        with review_tabs[1]:
            if evidence_rows:
                st.dataframe(evidence_rows, use_container_width=True, hide_index=True)
            else:
                st.info("No model evidence manifests are available yet.")
        with review_tabs[2]:
            st.download_button(
                "Export wet-lab SOP draft",
                data=protocol_md,
                file_name="dpsim_wet_lab_sop_draft.md",
                mime="text/markdown",
                key="p6_protocol_download_overview",
                use_container_width=True,
            )
            st.code(protocol_md[:4000], language="markdown")
        with review_tabs[3]:
            if calibration_rows:
                st.dataframe(calibration_rows, use_container_width=True, hide_index=True)
            else:
                st.info("No calibration entries are loaded.")


def stage_recipe_snapshot_rows(recipe: ProcessRecipe, stage: LifecycleStage) -> list[dict[str, str]]:
    """Return compact rows that make reused M1/M2/M3 panels feel workflow-bound."""

    rows: list[dict[str, str]] = []
    for index, step in enumerate(recipe.steps_for_stage(stage), 1):
        rows.append(
            {
                "step": str(index),
                "operation": step.kind.value,
                "name": step.name,
                "parameters": str(len(step.parameters)),
                "qc_items": str(len(step.qc_required)),
                "notes": step.notes[:120],
            }
        )
    return rows


def render_stage_context_panel(recipe: ProcessRecipe, stage: LifecycleStage) -> None:
    """Render lifecycle context before an embedded module UI."""

    import streamlit as st

    stage_label = {
        LifecycleStage.M1_FABRICATION: "M1 Fabrication Recipe Context",
        LifecycleStage.M2_FUNCTIONALIZATION: "M2 Chemistry Recipe Context",
        LifecycleStage.M3_PERFORMANCE: "M3 Column Method Context",
    }.get(stage, stage.value)
    st.subheader(stage_label)
    rows = stage_recipe_snapshot_rows(recipe, stage)
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("No recipe steps are currently defined for this lifecycle stage.")


def _has_stage_kinds(
    recipe: ProcessRecipe,
    stage: LifecycleStage,
    required_kinds: set[ProcessStepKind],
) -> bool:
    kinds = {step.kind for step in recipe.steps_for_stage(stage)}
    return required_kinds.issubset(kinds)


def _target_profile_ready(recipe: ProcessRecipe) -> bool:
    return (
        bool(recipe.target.name)
        and recipe.target.bead_d50.value > 0
        and recipe.target.pore_size.value > 0
        and recipe.target.min_modulus.value > 0
        and bool(recipe.target.target_ligand)
        and bool(recipe.target.target_analyte)
    )


def _target_detail(recipe: ProcessRecipe) -> str:
    return (
        f"{recipe.target.target_ligand} / {recipe.target.target_analyte}; "
        f"d50 {recipe.target.bead_d50.value:g} {recipe.target.bead_d50.unit}"
    )


def _stage_detail(recipe: ProcessRecipe, stage: LifecycleStage) -> str:
    steps = recipe.steps_for_stage(stage)
    return f"{len(steps)} recipe steps"


def _has_any_result(store: Mapping[str, Any]) -> bool:
    return any(
        key in store
        for key in (
            "lifecycle_result",
            "result",
            "m2_result",
            "m3_result_method",
            "m3_result_bt",
            "m3_result_ge",
            "m3_result_cat",
        )
    )


def _has_validation_or_evidence(store: Mapping[str, Any]) -> bool:
    if _session_validation_report(store) is not None:
        return True
    return bool(evidence_ladder_rows(store.get("lifecycle_result"), session_state=store))


def _run_detail(store: Mapping[str, Any]) -> str:
    if "lifecycle_result" in store:
        return "Full lifecycle result available"
    if "m3_result_method" in store or "m3_result_bt" in store or "m3_result_ge" in store:
        return "M3 result available"
    if "m2_result" in store:
        return "M2 result available"
    if "result" in store:
        return "M1 result available"
    return "Ready after recipe review"


def _validation_detail(store: Mapping[str, Any]) -> str:
    report = _session_validation_report(store)
    if report is None:
        return "Pending simulation"
    return f"{len(report.blockers)} blockers; {len(report.warnings)} warnings"


def _calibration_entry_count(store: Mapping[str, Any]) -> int:
    cal_store = store.get("_cal_store")
    try:
        return len(cal_store) if cal_store is not None else 0
    except TypeError:
        return len(getattr(cal_store, "entries", []))


def _session_validation_report(store: Mapping[str, Any]) -> ValidationReport | None:
    lifecycle_result = store.get("lifecycle_result")
    if lifecycle_result is not None and getattr(lifecycle_result, "validation", None) is not None:
        return lifecycle_result.validation
    report = store.get("validation_report")
    if isinstance(report, ValidationReport):
        return report
    return None


def _stage_objective(stage: LifecycleStage) -> str:
    return {
        LifecycleStage.M1_FABRICATION: (
            "Prepare washed microspheres with controlled DSD, pore state, "
            "mechanics, and low oil/surfactant carryover."
        ),
        LifecycleStage.M2_FUNCTIONALIZATION: (
            "Install functional ligand through validated activation, spacer, "
            "coupling, quench, wash, and storage-buffer operations."
        ),
        LifecycleStage.M3_PERFORMANCE: (
            "Operate a packed affinity column through pack, equilibrate, load, "
            "wash, and elute steps while respecting pressure and compression limits."
        ),
    }.get(stage, "Execute the defined process stage.")


def _stage_release_gate(stage: LifecycleStage) -> str:
    return {
        LifecycleStage.M1_FABRICATION: (
            "Measured DSD, pore, swelling, modulus, residual oil, and residual "
            "surfactant data reviewed against the target product profile."
        ),
        LifecycleStage.M2_FUNCTIONALIZATION: (
            "Site balance closes; ligand density/activity/leaching/free-protein "
            "assays are present or evidence is downgraded."
        ),
        LifecycleStage.M3_PERFORMANCE: (
            "Pressure-flow, packed-bed compression, DBC, recovery, leaching, "
            "and fraction analytics are inside accepted operating limits."
        ),
    }.get(stage, "Stage evidence reviewed.")


def _append_lifecycle_run_history(
    session_state: MutableMapping[str, Any],
    lifecycle_result: Any,
    *,
    run_id: str = "",
) -> None:
    history = list(session_state.get(RUN_HISTORY_KEY, []))
    validation = getattr(lifecycle_result, "validation", None)
    breakthrough = getattr(lifecycle_result, "m3_breakthrough", None)
    method = getattr(lifecycle_result, "m3_method", None)
    operability = getattr(method, "operability", None)
    weakest = getattr(lifecycle_result, "weakest_evidence_tier", None)
    recipe = getattr(lifecycle_result, "recipe", None)
    target = getattr(recipe, "target", None)
    pressure_pa = None if operability is None else _safe_float(getattr(operability, "pressure_drop_Pa", None))
    row = {
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "run_id": run_id or f"run-{len(history) + 1}",
        "product": str(getattr(target, "name", "")),
        "weakest_evidence_tier": getattr(weakest, "value", str(weakest)) if weakest is not None else "",
        "blockers": str(len(getattr(validation, "blockers", []))) if validation is not None else "",
        "warnings": str(len(getattr(validation, "warnings", []))) if validation is not None else "",
        "dbc10_mol_m3": _format_number(_safe_float(getattr(breakthrough, "dbc_10pct", None))),
        "pressure_bar": _format_number(None if pressure_pa is None else pressure_pa / 1.0e5),
    }
    history.insert(0, row)
    session_state[RUN_HISTORY_KEY] = history[:MAX_RUN_HISTORY]


def _result_graph_diagnostics(lifecycle_result: Any | None) -> dict[str, dict[str, Any]]:
    if lifecycle_result is None or getattr(lifecycle_result, "graph", None) is None:
        return {}
    return {
        node_id: dict(getattr(node, "diagnostics", {}) or {})
        for node_id, node in lifecycle_result.graph.nodes.items()
    }


def _simulated_metric_for_calibration(entry: Any, lifecycle_result: Any | None) -> tuple[float, str, str] | None:
    diagnostics = _result_graph_diagnostics(lifecycle_result)
    if not diagnostics:
        return None
    for node_id, key, unit, label in _metric_candidates_for_calibration(entry):
        node_diag = diagnostics.get(node_id, {})
        if key not in node_diag:
            continue
        value = _safe_float(node_diag[key])
        if value is not None:
            return value, unit, label
    return None


def _metric_candidates_for_calibration(entry: Any) -> list[tuple[str, str, str, str]]:
    parameter = str(getattr(entry, "parameter_name", "") or "").strip().lower()
    measurement = str(getattr(entry, "measurement_type", "") or "").strip().lower()
    tokens = {parameter, measurement}
    candidates: list[tuple[str, str, str, str]] = []

    def add(node_id: str, key: str, unit: str, label: str) -> None:
        item = (node_id, key, unit, label)
        if item not in candidates:
            candidates.append(item)

    if tokens & {"d10", "d10_m", "bead_d10", "bead_d10_m"}:
        add("M1", "bead_d10_m", "m", "M1 bead d10")
    if tokens & {"d32", "d32_m", "bead_d32", "mean_d32"}:
        add("M1", "bead_d32_m", "m", "M1 bead d32")
    if tokens & {"d50", "d50_m", "bead_d50", "bead_d50_m", "median_diameter"}:
        add("M1", "bead_d50_m", "m", "M1 bead d50")
        add("DSD", "d50_m", "m", "DSD d50")
    if tokens & {"d90", "d90_m", "bead_d90", "bead_d90_m"}:
        add("M1", "bead_d90_m", "m", "M1 bead d90")
        add("DSD", "d90_m", "m", "DSD d90")
    if "pore" in parameter or "pore" in measurement:
        add("M1", "pore_size_m", "m", "M1 pore size")
    if tokens & {"residual_oil", "oil_carryover", "residual_oil_fraction"}:
        add("M1", "residual_oil_volume_fraction", "fraction", "M1 residual oil")
    if tokens & {"residual_surfactant", "surfactant_carryover"}:
        add("M1", "residual_surfactant_kg_m3", "kg/m3", "M1 residual surfactant")
    if tokens & {"functional_ligand_density", "ligand_density"}:
        add("M2", "functional_ligand_density", "mol/m2", "M2 functional ligand density")
    if tokens & {"activity_retention", "retained_activity"}:
        add("M2", "activity_retention", "fraction", "M2 activity retention")
        add("FMC", "activity_retention", "fraction", "FMC activity retention")
    if tokens & {"ligand_leaching_fraction", "ligand_leaching"}:
        add("M2", "ligand_leaching_fraction", "fraction", "M2 ligand leaching")
        add("FMC", "ligand_leaching_fraction", "fraction", "FMC ligand leaching")
    if tokens & {"free_protein_wash_fraction", "free_protein"}:
        add("M2", "free_protein_wash_fraction", "fraction", "M2 free protein wash")
        add("FMC", "free_protein_wash_fraction", "fraction", "FMC free protein wash")
    if tokens & {"estimated_q_max", "q_max", "qmax", "static_binding_capacity", "static_binding_isotherm"}:
        add("FMC", "estimated_q_max", "mol/m3", "FMC estimated qmax")
        add("M2", "estimated_q_max", "mol/m3", "M2 estimated qmax")
        add("M3", "protein_a_q_max_mol_m3", "mol/m3", "M3 Protein A qmax")
    if (
        "dbc" in parameter
        or "dynamic_binding_capacity" in measurement
        or measurement in {"dbc10", "dbc_10pct", "breakthrough_curve"}
    ):
        add("M3", "dbc_10pct", "mol/m3", "M3 DBC10")
        add("DSD", "dbc_10_weighted_p50", "mol/m3", "DSD DBC10 p50")
    if "pressure" in parameter or "pressure" in measurement:
        add("M3", "method_pressure_drop_Pa", "Pa", "M3 pressure drop")
        add("M3", "pressure_drop_Pa", "Pa", "M3 pressure drop")
        add("DSD", "pressure_drop_weighted_p95_Pa", "Pa", "DSD pressure p95")
    return candidates


def _convert_simulated_to_display_unit(
    value: float,
    simulated_unit: str,
    requested_unit: str,
) -> tuple[float | None, str]:
    if not requested_unit or requested_unit == simulated_unit:
        return value, simulated_unit
    try:
        return Quantity(value, simulated_unit).as_unit(requested_unit).value, requested_unit
    except ValueError:
        return value, simulated_unit


def _calibration_agreement_assessment(relative_delta_pct: float | None) -> str:
    if relative_delta_pct is None:
        return "Loaded; comparison needs a nonzero measured value."
    magnitude = abs(relative_delta_pct)
    if magnitude <= 5.0:
        return "Agreement within screening tolerance."
    if magnitude <= 20.0:
        return "Moderate model-data tension."
    return "Large model-data discrepancy."


def _calibration_agreement_action(relative_delta_pct: float | None, label: str) -> str:
    if relative_delta_pct is None:
        return f"Review {label} units and replicate statistics."
    magnitude = abs(relative_delta_pct)
    if magnitude <= 5.0:
        return "Record as supporting evidence; keep calibration domain visible."
    if magnitude <= 20.0:
        return "Check calibration domain, assay state, and recipe-equipment match."
    return "Do not treat this prediction as decision-grade until recalibrated."


def _format_diagnostic_value(value: Any, key: str, display_unit: str) -> str:
    numeric = _safe_float(value)
    if numeric is None:
        return str(value)
    source_unit = ""
    if key.endswith("_m"):
        source_unit = "m"
    elif key.endswith("_Pa"):
        source_unit = "Pa"
    elif key.endswith("_kg_m3"):
        source_unit = "kg/m3"
    elif "mol_m3" in key or key.endswith("q_max") or key.endswith("dbc_10pct"):
        source_unit = "mol/m3"
    elif "fraction" in key or "ratio" in key:
        source_unit = "fraction"
    if display_unit and source_unit:
        converted, unit = _convert_simulated_to_display_unit(numeric, source_unit, display_unit)
        return f"{_format_number(converted)} {unit}".strip()
    if display_unit:
        return f"{_format_number(numeric)} {display_unit}".strip()
    return _format_number(numeric)


def _trace_rows_from_result(
    trace_result: Any | None,
    trace_label: str,
    *,
    max_points: int,
) -> list[dict[str, float | str]]:
    if trace_result is None:
        return []
    time_s = _to_float_list(getattr(trace_result, "time", []))
    concentration = _to_float_list(getattr(trace_result, "C_outlet", []))
    uv_signal = _to_float_list(getattr(trace_result, "uv_signal", []))
    n_rows = min(len(time_s), len(concentration))
    if n_rows == 0:
        return []
    stride = max(1, (n_rows + max(max_points, 1) - 1) // max(max_points, 1))
    max_concentration = max((abs(value) for value in concentration[:n_rows]), default=0.0)
    if max_concentration <= 0.0:
        max_concentration = 1.0
    rows: list[dict[str, float | str]] = []
    for index in range(0, n_rows, stride):
        concentration_value = concentration[index]
        rows.append(
            {
                "trace": trace_label,
                "time_min": time_s[index] / 60.0,
                "C_outlet_mol_m3": concentration_value,
                "normalized_concentration": concentration_value / max_concentration,
                "uv_signal_mAU": uv_signal[index] if index < len(uv_signal) else 0.0,
            }
        )
    return rows


def _to_float_list(values: Any) -> list[float]:
    if values is None:
        return []
    if hasattr(values, "reshape") and hasattr(values, "tolist"):
        try:
            values = values.reshape(-1).tolist()
        except Exception:
            values = values.tolist()
    try:
        return [float(value) for value in values]
    except TypeError:
        return [float(values)]
    except ValueError:
        return []


def _dataframe_or_rows(rows: list[dict[str, Any]]) -> Any:
    try:
        import pandas as pd

        return pd.DataFrame(rows)
    except Exception:
        return rows


def _wet_lab_followup_for_metric(node_id: str, key: str) -> str:
    if node_id == "M1" and "bead" in key:
        return "Microscopy or laser diffraction DSD."
    if node_id == "M1" and "pore" in key:
        return "Pore imaging or SEC inverse-size calibration."
    if node_id == "M1" and "residual" in key:
        return "Residual oil/surfactant assay after washing."
    if node_id in {"M2", "FMC"} and "ligand" in key:
        return "Ligand density/activity/leaching assay."
    if node_id in {"M2", "FMC"} and "protein" in key:
        return "Quantify free protein in wash fractions."
    if node_id == "DSD":
        return "Size-resolved packing and breakthrough experiment."
    if node_id == "M3" and ("pressure" in key or "compression" in key):
        return "Pressure-flow and bed-compression test."
    if node_id == "M3" and "dbc" in key:
        return "Breakthrough curve on target feedstock."
    if node_id == "M3" and "leaching" in key:
        return "Protein A leaching assay over cycles."
    return "Document assay method, lot, buffer, temperature, and acceptance criteria."


def _format_number(value: float | None) -> str:
    if value is None:
        return ""
    if abs(value) >= 1000 or (0 < abs(value) < 0.001):
        return f"{value:.3e}"
    return f"{value:.4g}"


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _manifest_row(
    node_id: str,
    label: str,
    manifest: ModelManifest | None,
    caveats: list[str],
) -> dict[str, str]:
    if manifest is None:
        return {
            "node": node_id,
            "label": label,
            "model": "not_available",
            "evidence_tier": "not_available",
            "calibration_ref": "",
            "assumptions": "",
            "wet_lab_caveats": "; ".join(caveats),
        }
    tier = getattr(manifest.evidence_tier, "value", str(manifest.evidence_tier))
    return {
        "node": node_id,
        "label": label,
        "model": manifest.model_name,
        "evidence_tier": tier,
        "calibration_ref": manifest.calibration_ref,
        "assumptions": "; ".join(manifest.assumptions),
        "wet_lab_caveats": "; ".join(caveats),
    }
