"""Full method-level chromatography operation for M3.

This module sits above the inherited LRM breakthrough solver. It represents a
wet-lab chromatography method as explicit operations: pack, equilibrate, load,
wash, and elute. The load operation still uses the validated breakthrough
solver, while the surrounding operations add column operability and Protein
A-specific performance diagnostics that a downstream processing scientist
would check before trusting a packed-bed experiment.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any

import numpy as np
from scipy.integrate import solve_ivp

from dpsim.datatypes import ModelManifest

from .detection.uv import apply_detector_broadening, compute_uv_signal
from .hydrodynamics import ColumnGeometry
from .isotherms.protein_a import ProteinAIsotherm
from .orchestrator import (
    BreakthroughResult,
    _build_m3_chrom_manifest,
    run_breakthrough,
)
from .quantitative_gates import GradientContext


class ChromatographyOperation(Enum):
    """Wet-lab operations in a chromatography method."""

    PACK = "pack"
    EQUILIBRATE = "equilibrate"
    LOAD = "load"
    WASH = "wash"
    ELUTE = "elute"
    REGENERATE = "regenerate"


@dataclass
class BufferCondition:
    """Mobile-phase condition for one chromatography method step."""

    name: str = ""
    pH: float = 7.4
    conductivity_mS_cm: float = 15.0
    salt_concentration_mol_m3: float = 0.0
    temperature_K: float = 298.15


@dataclass
class ChromatographyMethodStep:
    """One executable chromatography operation from a ProcessRecipe."""

    name: str
    operation: ChromatographyOperation
    duration_s: float = 0.0
    flow_rate_m3_s: float = 1.0e-8
    buffer: BufferCondition = field(default_factory=BufferCondition)
    feed_concentration_mol_m3: float = 0.0
    total_time_s: float = 0.0
    gradient_field: str = ""
    gradient_start: float | None = None
    gradient_end: float | None = None
    target_residence_time_s: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    # B-2e (W-004) follow-on: typed gradient handle. When set, this carries
    # the canonical gradient parameters (start/end/duration/shape) and the
    # legacy gradient_field / gradient_start / gradient_end fields are kept
    # only for back-compat with v0.6.x callers. New code should populate
    # gradient_context and leave the legacy fields at default.
    gradient_context: GradientContext | None = None


def _resolve_gradient(step: "ChromatographyMethodStep") -> GradientContext | None:
    """Return the active GradientContext for ``step`` (typed-first, legacy-fallback).

    If ``step.gradient_context`` is set and active, returns it directly.
    Otherwise falls back to the legacy ``gradient_field`` / ``gradient_start``
    / ``gradient_end`` fields, building a GradientContext from them on the fly
    so the rest of the M3 code only ever consumes a typed object.
    """
    if step.gradient_context is not None and step.gradient_context.is_active:
        return step.gradient_context
    field_name = (step.gradient_field or "").strip()
    if not field_name:
        return None
    if step.gradient_start is None or step.gradient_end is None:
        return None
    return GradientContext(
        gradient_field=field_name,
        start_value=float(step.gradient_start),
        end_value=float(step.gradient_end),
        duration_s=float(step.duration_s),
        shape="linear",
    )


@dataclass
class ChromatographyStepResult:
    """Operational summary for one method step."""

    name: str
    operation: ChromatographyOperation
    duration_s: float
    flow_rate_m3_s: float
    column_volumes: float
    residence_time_s: float
    pressure_drop_Pa: float
    bed_compression_fraction: float
    buffer: BufferCondition
    diagnostics: dict[str, float | str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


@dataclass
class ColumnOperabilityReport:
    """Hydraulic and mechanical feasibility screen for the method."""

    step_name: str
    pressure_drop_Pa: float
    max_pressure_Pa: float
    pump_pressure_limit_Pa: float
    bed_compression_fraction: float
    particle_reynolds: float
    axial_peclet: float
    residence_time_s: float
    interstitial_velocity_m_s: float
    maldistribution_index: float
    maldistribution_risk: str
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)

    @property
    def issues(self) -> list[str]:
        """All warnings and blockers in display order."""

        return [*self.blockers, *self.warnings]

    # v0.6.0 (E1) — typed Quantity accessors.

    @property
    def pressure_drop_q(self):
        from dpsim.core.quantities import Quantity
        return Quantity(float(self.pressure_drop_Pa), "Pa", source="M3.operability")

    @property
    def bed_compression_q(self):
        from dpsim.core.quantities import Quantity
        return Quantity(
            float(self.bed_compression_fraction), "1",
            source="M3.operability",
            note="Bed-compression fraction (0 = no compression, 1 = full collapse).",
        )

    @property
    def residence_time_q(self):
        from dpsim.core.quantities import Quantity
        return Quantity(float(self.residence_time_s), "s", source="M3.operability")

    @property
    def interstitial_velocity_q(self):
        from dpsim.core.quantities import Quantity
        return Quantity(
            float(self.interstitial_velocity_m_s), "m/s",
            source="M3.operability",
            note="Interstitial liquid velocity (superficial / bed_porosity).",
        )


@dataclass
class ProteinAPerformanceReport:
    """Protein A-specific affinity-column performance diagnostics."""

    q_max_mol_m3: float
    load_pH: float
    elution_pH: float
    K_a_load_m3_mol: float
    K_a_elution_m3_mol: float
    q_equilibrium_load_mol_m3: float
    ligand_accessibility_factor: float
    activity_retention: float
    mass_transfer_coefficient_m_s: float
    mass_transfer_resistance_s: float
    alkaline_degradation_fraction_per_cycle: float
    cycle_lifetime_to_70pct_capacity: float
    ligand_leaching_fraction_per_cycle: float
    leaching_risk: str
    predicted_elution_recovery_fraction: float
    warnings: list[str] = field(default_factory=list)

    # v0.6.0 (E1) — typed Quantity accessors. The float fields above remain
    # authoritative for arithmetic; these expose unit-tagged handles.

    @property
    def q_max_q(self):
        from dpsim.core.quantities import Quantity
        return Quantity(float(self.q_max_mol_m3), "mol/m3", source="M3.protein_a")

    @property
    def predicted_recovery_q(self):
        from dpsim.core.quantities import Quantity
        return Quantity(
            float(self.predicted_elution_recovery_fraction), "1",
            source="M3.protein_a",
            note="Predicted IgG fraction recovered in the elution pool.",
        )

    @property
    def activity_retention_q(self):
        from dpsim.core.quantities import Quantity
        return Quantity(
            float(self.activity_retention), "1",
            source="M3.protein_a",
            note="Coupled-protein activity retention (functional / total density).",
        )

    @property
    def cycle_lifetime_q(self):
        """Bucketed cycle-lifetime estimate (illustrative until calibrated; v0.3.0 / B6)."""
        from dpsim.core.quantities import Quantity
        return Quantity(
            float(self.cycle_lifetime_to_70pct_capacity), "1",
            source="M3.protein_a",
            note=(
                "Illustrative cycle count to 70% capacity loss. UNSUPPORTED as a "
                "quantitative claim without resin-specific cycling data — see "
                "module3_performance.method.cycle_lifetime_label for the "
                "ranking-tier display when uncalibrated."
            ),
        )
    assumptions: list[str] = field(default_factory=list)
    wet_lab_caveats: list[str] = field(default_factory=list)


@dataclass
class LoadedStateElutionResult:
    """Low-pH elution simulation initialized from the loaded bound profile."""

    time: np.ndarray
    C_outlet: np.ndarray
    uv_signal: np.ndarray
    q_average: np.ndarray
    pH_profile: np.ndarray
    mass_initial_bound_mol: float
    mass_eluted_mol: float
    mass_remaining_bound_mol: float
    recovery_fraction: float
    peak_time_s: float
    peak_width_half_s: float
    mass_balance_error: float
    model_note: str = (
        "Loaded-state elution uses the load-step bound profile as initial "
        "condition and switches the inlet to protein-free elution buffer."
    )
    # B-2e incremental scaffolding (v0.6.6): gradient envelope diagnostics
    # exposed for non-pH gradients (salt, imidazole) so downstream plots /
    # render can show the active gradient even though the isotherm physics
    # does not yet consume the value. None when no GradientContext is set
    # OR when the gradient is the pH-driven one (already reflected in
    # pH_profile). When populated, contains the GradientContext fields
    # plus a per-time-sample value array.
    gradient_diagnostics: dict | None = None

    # v0.6.0 (E1) — typed Quantity accessors. Underlying float fields above
    # remain authoritative for arithmetic; these accessors give downstream
    # consumers a typed-unit handle.

    @property
    def recovery_fraction_q(self):
        from dpsim.core.quantities import Quantity
        return Quantity(
            float(self.recovery_fraction),
            "1",
            source="M3.run_loaded_state_elution",
            note="Eluted / initially-bound mass fraction.",
        )

    @property
    def peak_time_q(self):
        from dpsim.core.quantities import Quantity
        return Quantity(float(self.peak_time_s), "s", source="M3.run_loaded_state_elution")

    @property
    def peak_width_half_q(self):
        from dpsim.core.quantities import Quantity
        return Quantity(
            float(self.peak_width_half_s), "s",
            source="M3.run_loaded_state_elution",
            note="Full width at half maximum (FWHM).",
        )

    @property
    def mass_balance_error_q(self):
        from dpsim.core.quantities import Quantity
        return Quantity(
            float(self.mass_balance_error), "1",
            source="M3.run_loaded_state_elution",
            note="Relative mass-balance error (dimensionless fraction).",
        )


@dataclass
class ColumnEfficiencyReport:
    """Screening estimate of packed-column efficiency from transport limits."""

    theoretical_plates: float
    hetp_m: float
    asymmetry_factor: float
    tailing_factor: float
    tracer_residence_time_s: float
    tracer_peak_width_half_s: float
    axial_peclet: float
    warnings: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)


@dataclass
class ImpuritySpeciesReport:
    """Wash and co-elution screen for one impurity class."""

    name: str
    load_fraction_of_igg: float
    remaining_after_wash_fraction: float
    coelution_fraction_of_igg: float
    log10_reduction: float


@dataclass
class ImpurityClearanceReport:
    """Screening wash/co-elution report for common Protein A feed impurities."""

    species: list[ImpuritySpeciesReport]
    wash_column_volumes: float
    total_coelution_fraction_of_igg: float
    risk: str
    warnings: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)


@dataclass
class ChromatographyMethodResult:
    """Complete M3 method simulation result.

    ``load_breakthrough`` remains the quantitative dynamic-load output. The
    method result wraps it with pack/equilibrate/wash/elute operational context,
    column operability limits, and Protein A degradation/leaching checks.
    """

    method_steps: list[ChromatographyMethodStep]
    step_results: list[ChromatographyStepResult]
    load_breakthrough: BreakthroughResult | None
    loaded_elution: LoadedStateElutionResult | None
    operability: ColumnOperabilityReport
    column_efficiency: ColumnEfficiencyReport
    impurity_clearance: ImpurityClearanceReport
    protein_a: ProteinAPerformanceReport
    model_manifest: ModelManifest
    assumptions: list[str] = field(default_factory=list)
    wet_lab_caveats: list[str] = field(default_factory=list)

    @property
    def method_step_names(self) -> list[str]:
        """Names of the method steps in execution order."""

        return [step.name for step in self.method_steps]


def default_protein_a_method_steps(
    *,
    flow_rate: float = 1.0e-8,
    feed_concentration: float = 1.0,
    feed_duration: float = 600.0,
    total_time: float = 1200.0,
) -> list[ChromatographyMethodStep]:
    """Return a conservative Protein A pack/equilibrate/load/wash/elute method."""

    binding = BufferCondition("binding buffer", pH=7.4, conductivity_mS_cm=15.0)
    elution = BufferCondition("low-pH elution buffer", pH=3.5, conductivity_mS_cm=5.0)
    return [
        ChromatographyMethodStep(
            "Pack column",
            ChromatographyOperation.PACK,
            duration_s=0.0,
            flow_rate_m3_s=flow_rate,
            buffer=binding,
        ),
        ChromatographyMethodStep(
            "Equilibrate column",
            ChromatographyOperation.EQUILIBRATE,
            duration_s=300.0,
            flow_rate_m3_s=flow_rate,
            buffer=binding,
        ),
        ChromatographyMethodStep(
            "Load IgG feed",
            ChromatographyOperation.LOAD,
            duration_s=feed_duration,
            flow_rate_m3_s=flow_rate,
            buffer=binding,
            feed_concentration_mol_m3=feed_concentration,
            total_time_s=total_time,
        ),
        ChromatographyMethodStep(
            "Wash unbound protein",
            ChromatographyOperation.WASH,
            duration_s=300.0,
            flow_rate_m3_s=flow_rate,
            buffer=binding,
        ),
        ChromatographyMethodStep(
            "Elute bound IgG",
            ChromatographyOperation.ELUTE,
            duration_s=300.0,
            flow_rate_m3_s=flow_rate,
            buffer=elution,
            gradient_field="ph",
            gradient_start=7.4,
            gradient_end=3.5,
            gradient_context=GradientContext(
                gradient_field="ph",
                start_value=7.4,
                end_value=3.5,
                duration_s=300.0,
                shape="linear",
            ),
        ),
    ]


def run_chromatography_method(
    column: ColumnGeometry,
    method_steps: list[ChromatographyMethodStep] | None = None,
    *,
    fmc=None,
    process_state: dict | None = None,
    max_pressure_Pa=3.0e5,
    pump_pressure_limit_Pa=3.0e5,
    n_z: int = 50,
    D_molecular: float = 7.0e-11,
    k_ads: float = 100.0,
) -> ChromatographyMethodResult:
    """Run a complete method-level M3 Protein A operation simulation.

    v0.6.1 (F1): ``max_pressure_Pa`` and ``pump_pressure_limit_Pa`` accept
    either a ``float`` (assumed Pa) or a ``Quantity`` (auto-converted to Pa).
    """
    # v0.6.1 (F1) — Quantity-or-float entry-point coercion.
    from dpsim.core.quantities import unwrap_to_unit

    max_pressure_Pa = unwrap_to_unit(max_pressure_Pa, "Pa")
    pump_pressure_limit_Pa = unwrap_to_unit(pump_pressure_limit_Pa, "Pa")

    steps = list(method_steps or default_protein_a_method_steps())
    if not steps:
        steps = default_protein_a_method_steps()
    step_results = [
        _summarize_step(column, step)
        for step in steps
    ]
    # v0.4.6: cancel poll between method-step solver calls. The LOAD,
    # WASH, and ELUTE phases each fire an LRM solve; polling between
    # them caps cancel latency at one phase's duration.
    from dpsim.lifecycle.cancellation import check_cancel

    load_step = _first_step(steps, ChromatographyOperation.LOAD)
    wash_step = _first_step_after(steps, ChromatographyOperation.WASH, load_step)
    elute_step = _first_step(steps, ChromatographyOperation.ELUTE)
    load_breakthrough = None
    check_cancel(stage="pre-LOAD-breakthrough")
    if load_step is not None:
        load_state = dict(_process_state_dict(process_state))
        load_state["ph"] = float(load_step.buffer.pH)
        load_state["conductivity"] = float(load_step.buffer.conductivity_mS_cm)
        total_time = load_step.total_time_s
        if total_time <= load_step.duration_s:
            total_time = load_step.duration_s + (wash_step.duration_s if wash_step else 0.0)
        if total_time <= load_step.duration_s:
            total_time = max(2.0 * load_step.duration_s, load_step.duration_s + 60.0)
        load_breakthrough = run_breakthrough(
            column=column,
            C_feed=load_step.feed_concentration_mol_m3,
            flow_rate=load_step.flow_rate_m3_s,
            feed_duration=load_step.duration_s,
            total_time=total_time,
            n_z=n_z,
            D_molecular=D_molecular,
            k_ads=k_ads,
            fmc=fmc,
            process_state=load_state,
            log_flow_warnings=False,
        )
    loaded_elution = None
    if (
        load_breakthrough is not None
        and elute_step is not None
        and load_breakthrough.q_profile_final is not None
    ):
        loaded_elution = run_loaded_state_elution(
            column=column,
            q_initial_profile=load_breakthrough.q_profile_final,
            elution_step=elute_step,
            fmc=fmc,
            process_state=process_state,
            n_z=n_z,
            D_molecular=D_molecular,
            k_ads=k_ads,
        )

    operability = _worst_operability_report(
        column=column,
        steps=steps,
        max_pressure_Pa=max_pressure_Pa,
        pump_pressure_limit_Pa=pump_pressure_limit_Pa,
        D_molecular=D_molecular,
    )
    column_efficiency = evaluate_column_efficiency(
        column=column,
        method_steps=steps,
        operability=operability,
    )
    impurity_clearance = evaluate_impurity_clearance(
        column=column,
        method_steps=steps,
        loaded_elution=loaded_elution,
    )
    protein_a = evaluate_protein_a_performance(
        column=column,
        method_steps=steps,
        fmc=fmc,
        process_state=process_state,
        D_molecular=D_molecular,
        loaded_elution=loaded_elution,
    )
    worst_mass_balance = (
        max(
            load_breakthrough.mass_balance_error,
            0.0 if loaded_elution is None else loaded_elution.mass_balance_error,
        )
        if load_breakthrough is not None
        else 0.0
    )
    protein_isotherm = _protein_a_isotherm_from_state(
        q_max=max(protein_a.q_max_mol_m3, 1.0e-12),
        process_state=process_state,
    )
    manifest = _build_m3_chrom_manifest(
        model_basename="M3.method.ProteinAOperation",
        isotherm=protein_isotherm,
        fmc=fmc,
        worst_mass_balance_error=worst_mass_balance,
        diagnostics_extra={
            "method_steps": [step.operation.value for step in steps],
            "max_pressure_drop_Pa": float(operability.pressure_drop_Pa),
            "max_bed_compression_fraction": float(operability.bed_compression_fraction),
            "particle_reynolds": float(operability.particle_reynolds),
            "axial_peclet": float(operability.axial_peclet),
            "maldistribution_risk": operability.maldistribution_risk,
            "protein_a_K_a_load": float(protein_a.K_a_load_m3_mol),
            "protein_a_K_a_elution": float(protein_a.K_a_elution_m3_mol),
            "protein_a_cycle_lifetime_to_70pct": (
                protein_a.cycle_lifetime_to_70pct_capacity
            ),
            "protein_a_leaching_risk": protein_a.leaching_risk,
            "loaded_elution_recovery_fraction": (
                0.0 if loaded_elution is None else loaded_elution.recovery_fraction
            ),
            "loaded_elution_mass_balance_error": (
                0.0 if loaded_elution is None else loaded_elution.mass_balance_error
            ),
            "column_efficiency_plates": column_efficiency.theoretical_plates,
            "column_efficiency_hetp_m": column_efficiency.hetp_m,
            "column_asymmetry_factor": column_efficiency.asymmetry_factor,
            "impurity_total_coelution_fraction": (
                impurity_clearance.total_coelution_fraction_of_igg
            ),
            "impurity_clearance_risk": impurity_clearance.risk,
        },
    )
    assumptions = [
        "M3 method simulation uses the validated LRM breakthrough solver for the load step.",
        "Elution is initialized from the load-step bound profile and switches to protein-free low-pH buffer.",
        "Protein A elution recovery, alkaline degradation, and leaching are screening correlations until calibrated against resin-lot cycling data.",
        "Column efficiency and impurity clearance are screening estimates until tracer, HETP/asymmetry, HCP, DNA, aggregate, and leaching assays are supplied.",
    ]
    # v0.4.0 (C7): Protein A defaults are A+C-tuned. Non-A+C polymer families
    # use the same isotherm shape illustratively; the manifest tier is capped
    # at QUALITATIVE_TREND when no calibration is loaded so downstream
    # consumers do not read an A+C cycle-life / capacity number off a
    # cellulose / alginate / PLGA recipe.
    _family_warning = _protein_a_family_warning(process_state, fmc=fmc)
    if _family_warning:
        assumptions = [*assumptions, _family_warning]
        manifest = _cap_manifest_for_non_ac_family(manifest, _family_warning)

    # v0.4.0 (C2): ModelMode-conditional manifest gating.
    # empirical_engineering mode without calibration caps tier at
    # QUALITATIVE_TREND; mechanistic_research mode tags result EXPLORATORY.
    manifest = _apply_mode_guard(
        manifest,
        process_state,
        has_calibration=is_method_calibrated(fmc),
    )
    wet_lab_caveats = [
        "Confirm packed-bed pressure-flow behavior, bed height, asymmetry, and plate count before trusting operability margins.",
        "Measure DBC, elution recovery, ligand leaching, and alkaline cleaning capacity loss on the target IgG and buffer set.",
        "Low-pH elution can damage IgG; real methods require immediate neutralization and aggregate monitoring.",
    ]
    manifest = replace(
        manifest,
        assumptions=[*manifest.assumptions, *assumptions],
        diagnostics={
            **manifest.diagnostics,
            "operability_warnings": list(operability.warnings),
            "operability_blockers": list(operability.blockers),
            "protein_a_warnings": list(protein_a.warnings),
            "column_efficiency_warnings": list(column_efficiency.warnings),
            "impurity_clearance_warnings": list(impurity_clearance.warnings),
        },
    )

    # B-2e (W-004): apply the M3 quantitative-output gate when calibration
    # entries are passed via process_state. Backward-compatible — when
    # absent, the manifest tier is unchanged. The gate can only DEMOTE
    # the tier; mode guards and family caps stay authoritative.
    if process_state is not None:
        cal_entries = process_state.get("calibration_entries")
        if cal_entries:
            from dpsim.module3_performance.quantitative_gates import (
                apply_m3_gate_to_manifest,
            )
            manifest = apply_m3_gate_to_manifest(
                manifest,
                cal_entries,
                profile_key=str(process_state.get("calibration_profile_key", "")),
                target_molecule=str(process_state.get("target_molecule", "")),
            )

    return ChromatographyMethodResult(
        method_steps=steps,
        step_results=step_results,
        load_breakthrough=load_breakthrough,
        loaded_elution=loaded_elution,
        operability=operability,
        column_efficiency=column_efficiency,
        impurity_clearance=impurity_clearance,
        protein_a=protein_a,
        model_manifest=manifest,
        assumptions=assumptions,
        wet_lab_caveats=wet_lab_caveats,
    )


def run_loaded_state_elution(
    *,
    column: ColumnGeometry,
    q_initial_profile: np.ndarray,
    elution_step: ChromatographyMethodStep,
    fmc=None,
    process_state: dict | None = None,
    n_z: int = 50,
    D_molecular: float = 7.0e-11,
    k_ads: float = 100.0,
    mu: float = 1.0e-3,
    rho: float = 1000.0,
) -> LoadedStateElutionResult:
    """Simulate low-pH elution from a preloaded axial bound profile.

    This is the first P4+ dynamic elution implementation. It reuses the LRM
    state equations, but starts from the bound profile produced by the load
    step and sets the inlet protein concentration to zero.
    """

    n_z = max(3, int(n_z))
    flow_rate = max(float(elution_step.flow_rate_m3_s), 1.0e-30)
    total_time = max(float(elution_step.duration_s), 1.0)
    raw_q = np.maximum(np.asarray(q_initial_profile, dtype=float), 0.0)
    if raw_q.size != n_z:
        x_old = np.linspace(0.0, 1.0, raw_q.size)
        x_new = np.linspace(0.0, 1.0, n_z)
        q0 = np.interp(x_new, x_old, raw_q)
    else:
        q0 = raw_q.copy()

    q_max = max(_fmc_value(fmc, "estimated_q_max", 0.0), float(np.max(q0)), 1.0e-12)
    K_a_max = max(_state_value(process_state, "K_affinity", 1.0e5), 1.0e-12)
    isotherm = _protein_a_isotherm_from_state(
        q_max=q_max,
        process_state=process_state,
        default_K_a_max=K_a_max,
    )
    # B-2e follow-on: consume the typed GradientContext if available; fall
    # back to legacy fields via the resolver so v0.6.x callers still work.
    _grad_ctx = _resolve_gradient(elution_step)
    if _grad_ctx is not None and _grad_ctx.gradient_field.lower() == "ph":
        pH_start = float(_grad_ctx.start_value)
    else:
        pH_start = float(elution_step.buffer.pH)
    # pH_end is not stored as a local — gradient_value_at_time reads
    # _grad_ctx.end_value directly when the gradient is pH-driven, and
    # _elution_pH is consumed only by external callers via the helper.

    u = column.superficial_velocity(flow_rate)
    eps_b = column.bed_porosity
    eps_p = column.particle_porosity
    R_p = column.particle_radius
    dz = column.bed_height / n_z
    k_f = _film_mass_transfer_coefficient(
        column,
        flow_rate,
        D_molecular,
        mu=mu,
        rho=rho,
    )
    D_ax = max(
        u * column.particle_diameter / (2.0 * max(eps_b, 1.0e-12)),
        D_molecular,
    )
    mass_transfer_coeff = (3.0 / max(R_p, 1.0e-12)) * k_f

    # B-2e incremental scaffolding: generic gradient-value-at-time profile.
    # Returns the active gradient's value at time t (linear ramp; the only
    # shape v0.6.x supports). Used by ph_at_time for the pH-driven path
    # AND exposed in the result.diagnostics for non-pH gradients (salt,
    # imidazole) so downstream consumers can see the active envelope.
    # The isotherm/transport adapter does NOT yet consume non-pH gradient
    # values — that requires a salt-dependent / imidazole-competition
    # isotherm extension and is deferred as a scientific scope item.

    def gradient_value_at_time(t: float) -> float | None:
        """Return the active gradient value at time ``t``, or None if no gradient.

        Honours the GradientContext shape (currently linear only). Caller
        must check the gradient field type before consuming the value.
        """
        if _grad_ctx is None or not _grad_ctx.is_active:
            return None
        ramp = _grad_ctx.duration_s if _grad_ctx.duration_s > 0.0 else total_time
        frac = min(1.0, max(0.0, t / ramp))
        return float(_grad_ctx.start_value) + frac * (
            float(_grad_ctx.end_value) - float(_grad_ctx.start_value)
        )

    def ph_at_time(t: float) -> float:
        # B-2e follow-on: typed GradientContext is the source of truth here.
        if _grad_ctx is None or _grad_ctx.gradient_field.lower() != "ph":
            return float(elution_step.buffer.pH)
        return float(gradient_value_at_time(t) or pH_start)

    def rhs(t: float, y: np.ndarray) -> np.ndarray:
        C = np.maximum(y[:n_z].copy(), 0.0)
        Cp = np.maximum(y[n_z:2 * n_z].copy(), 0.0)
        q = np.maximum(y[2 * n_z:3 * n_z].copy(), 0.0)
        C_in = 0.0

        dCdz = np.empty(n_z)
        dCdz[0] = (C[0] - C_in) / dz
        dCdz[1:] = (C[1:] - C[:-1]) / dz

        d2Cdz2 = np.empty(n_z)
        d2Cdz2[0] = (C[1] - 2.0 * C[0] + C_in) / dz ** 2
        d2Cdz2[1:-1] = (C[2:] - 2.0 * C[1:-1] + C[:-2]) / dz ** 2
        d2Cdz2[-1] = (C[-2] - C[-1]) / dz ** 2

        pH_t = ph_at_time(t)
        q_eq = (
            isotherm.equilibrium_loading(Cp, pH_t)
            * _protein_a_elution_suppression(pH_t, process_state)
        )
        dqdt = k_ads * (q_eq - q)
        film_flux = mass_transfer_coeff * (C - Cp)
        dCdt = (-u * dCdz + D_ax * d2Cdz2 - (1.0 - eps_b) * film_flux) / eps_b
        dCpdt = (film_flux - (1.0 - eps_p) * dqdt) / eps_p
        return np.concatenate([dCdt, dCpdt, dqdt])

    y0 = np.concatenate([np.zeros(n_z), np.zeros(n_z), q0])
    n_eval = min(1200, max(200, int(total_time / 1.0)))
    t_eval = np.linspace(0.0, total_time, n_eval)
    sol = solve_ivp(
        rhs,
        t_span=(0.0, total_time),
        y0=y0,
        method="BDF",
        t_eval=t_eval,
        rtol=1.0e-6,
        atol=1.0e-9,
        max_step=max(total_time / 50.0, 1.0e-6),
    )
    if not sol.success:
        raise RuntimeError(f"Loaded-state elution solver failed: {sol.message}")

    time = sol.t
    C_all = np.maximum(sol.y[:n_z, :], 0.0)
    Cp_all = np.maximum(sol.y[n_z:2 * n_z, :], 0.0)
    q_all = np.maximum(sol.y[2 * n_z:3 * n_z, :], 0.0)
    C_outlet = C_all[-1, :]
    q_average = np.mean(q_all, axis=0)
    uv_signal = apply_detector_broadening(
        compute_uv_signal(C_outlet),
        time,
        sigma_detector=1.0,
    )
    pH_profile = np.asarray([ph_at_time(float(t)) for t in time], dtype=float)

    V_bed = column.bed_volume
    mass_initial = float(np.mean(q0)) * (1.0 - eps_p) * (1.0 - eps_b) * V_bed
    mass_eluted = float(np.trapezoid(C_outlet * flow_rate, time))
    mass_mobile = float(np.mean(C_all[:, -1])) * eps_b * V_bed
    mass_pore = float(np.mean(Cp_all[:, -1])) * eps_p * (1.0 - eps_b) * V_bed
    mass_remaining_bound = float(np.mean(q_all[:, -1])) * (1.0 - eps_p) * (1.0 - eps_b) * V_bed
    if mass_initial > 0.0:
        mass_balance_error = abs(
            mass_initial - mass_eluted - mass_mobile - mass_pore - mass_remaining_bound
        ) / mass_initial
        recovery = mass_eluted / mass_initial
    else:
        mass_balance_error = 0.0
        recovery = 0.0
    peak_time, _, _, peak_width = _peak_stats(time, C_outlet)

    # B-2e scaffolding: expose gradient envelope for non-pH gradients.
    # The isotherm does not yet consume non-pH values, so the field is a
    # diagnostic carrier only — downstream plots / render can show the
    # active gradient even though the binding physics ignores it.
    gradient_diag: dict | None = None
    if _grad_ctx is not None and _grad_ctx.is_active and _grad_ctx.gradient_field.lower() != "ph":
        gradient_diag = {
            "field": _grad_ctx.gradient_field,
            "start_value": float(_grad_ctx.start_value),
            "end_value": float(_grad_ctx.end_value),
            "duration_s": float(_grad_ctx.duration_s),
            "shape": _grad_ctx.shape,
            "values": np.array([gradient_value_at_time(t) or 0.0 for t in time]),
            "isotherm_consumes": False,
            "advisory": (
                f"Gradient field '{_grad_ctx.gradient_field}' time-profile "
                f"is exposed for downstream visualization, but the isotherm "
                f"in this v0.6.x adapter does not consume it. Binding "
                f"behavior reflects buffer pH only. Salt-/imidazole-aware "
                f"isotherm is a future scientific scope item."
            ),
        }

    return LoadedStateElutionResult(
        time=time,
        C_outlet=C_outlet,
        uv_signal=uv_signal,
        q_average=q_average,
        pH_profile=pH_profile,
        mass_initial_bound_mol=float(mass_initial),
        mass_eluted_mol=float(mass_eluted),
        mass_remaining_bound_mol=float(mass_remaining_bound),
        recovery_fraction=float(max(0.0, min(1.5, recovery))),
        peak_time_s=float(peak_time),
        peak_width_half_s=float(peak_width),
        mass_balance_error=float(mass_balance_error),
        gradient_diagnostics=gradient_diag,
    )


def evaluate_column_efficiency(
    *,
    column: ColumnGeometry,
    method_steps: list[ChromatographyMethodStep],
    operability: ColumnOperabilityReport,
) -> ColumnEfficiencyReport:
    """Estimate tracer-pulse efficiency from axial dispersion and packing risk."""

    load_step = _first_step(method_steps, ChromatographyOperation.LOAD)
    flow_rate = load_step.flow_rate_m3_s if load_step else max(column.bed_volume / 600.0, 1.0e-12)
    residence = column.bed_volume / max(flow_rate, 1.0e-30)
    pe = max(float(operability.axial_peclet), 1.0)
    ideal_plates = max(1.0, pe / 2.0)
    packing_penalty = max(
        0.15,
        1.0
        - 0.50 * operability.maldistribution_index
        - min(0.35, operability.bed_compression_fraction),
    )
    plates = max(1.0, ideal_plates * packing_penalty)
    hetp = column.bed_height / plates
    sigma = residence / math.sqrt(plates)
    width_half = 2.355 * sigma
    asymmetry = 1.0 + 1.8 * operability.maldistribution_index + 2.0 * min(
        0.5,
        operability.bed_compression_fraction,
    )
    tailing = 1.0 + 0.5 * (asymmetry - 1.0)
    warnings: list[str] = []
    if plates < 50.0:
        warnings.append(
            f"Estimated plate count is {plates:.0f}; run a tracer pulse before interpreting peak shape."
        )
    if asymmetry > 1.8:
        warnings.append(
            f"Estimated asymmetry factor {asymmetry:.2f} suggests channeling or bed compression risk."
        )
    return ColumnEfficiencyReport(
        theoretical_plates=float(plates),
        hetp_m=float(hetp),
        asymmetry_factor=float(asymmetry),
        tailing_factor=float(tailing),
        tracer_residence_time_s=float(residence),
        tracer_peak_width_half_s=float(width_half),
        axial_peclet=float(pe),
        warnings=warnings,
        assumptions=[
            "Plate count is inferred from axial Peclet number and reduced by compression/maldistribution risk.",
            "Tracer peak width is a screening prediction, not a substitute for acetone/salt tracer testing.",
        ],
    )


def evaluate_impurity_clearance(
    *,
    column: ColumnGeometry,
    method_steps: list[ChromatographyMethodStep],
    loaded_elution: LoadedStateElutionResult | None = None,
) -> ImpurityClearanceReport:
    """Screen HCP, DNA, and aggregate wash clearance and co-elution risk."""

    wash_step = _first_step(method_steps, ChromatographyOperation.WASH)
    wash_cv = 0.0
    if wash_step is not None and column.bed_volume > 0.0:
        wash_cv = wash_step.flow_rate_m3_s * max(wash_step.duration_s, 0.0) / column.bed_volume
    elute_step = _first_step(method_steps, ChromatographyOperation.ELUTE)
    elution_pH = _elution_pH(elute_step)
    low_pH_release = 1.0 + max(0.0, 4.0 - elution_pH) * 0.25
    specs = [
        ("host_cell_protein", 0.050, 1.20, 0.050),
        ("dna", 0.005, 2.00, 0.020),
        ("aggregate", 0.020, 0.40, 0.300),
    ]
    species: list[ImpuritySpeciesReport] = []
    for name, load_fraction, wash_rate, elute_release in specs:
        remaining = load_fraction * math.exp(-wash_rate * wash_cv)
        coelution = remaining * elute_release * low_pH_release
        log_reduction = -math.log10(max(coelution / max(load_fraction, 1.0e-30), 1.0e-12))
        species.append(
            ImpuritySpeciesReport(
                name=name,
                load_fraction_of_igg=float(load_fraction),
                remaining_after_wash_fraction=float(remaining),
                coelution_fraction_of_igg=float(coelution),
                log10_reduction=float(log_reduction),
            )
        )
    total = sum(item.coelution_fraction_of_igg for item in species)
    if loaded_elution is not None and loaded_elution.recovery_fraction < 0.70:
        total *= 1.25
    risk = "high" if total > 0.01 else ("medium" if total > 0.002 else "low")
    warnings: list[str] = []
    if wash_cv < 3.0:
        warnings.append(
            f"Wash volume is {wash_cv:.2f} CV; common Protein A methods usually need measured UV baseline return."
        )
    if risk != "low":
        warnings.append(
            f"Predicted impurity co-elution fraction is {total:.2%} of IgG feed equivalent."
        )
    return ImpurityClearanceReport(
        species=species,
        wash_column_volumes=float(wash_cv),
        total_coelution_fraction_of_igg=float(total),
        risk=risk,
        warnings=warnings,
        assumptions=[
            "Impurity clearance uses normalized HCP/DNA/aggregate feed fractions until measured impurity loads are available.",
            "Wash removal is represented as first-order decay per column volume; co-elution is a low-pH release screen.",
        ],
    )


def evaluate_column_operability(
    column: ColumnGeometry,
    flow_rate: float,
    *,
    step_name: str = "",
    max_pressure_Pa: float = 3.0e5,
    pump_pressure_limit_Pa: float = 3.0e5,
    mu: float = 1.0e-3,
    rho: float = 1000.0,
    D_molecular: float = 7.0e-11,
) -> ColumnOperabilityReport:
    """Evaluate hydraulic and mechanical validity for one flow condition."""

    flow_rate = max(float(flow_rate), 0.0)
    pressure = column.pressure_drop(flow_rate, mu=mu)
    compression = column.bed_compression_fraction(pressure)
    u = column.superficial_velocity(flow_rate) if flow_rate > 0.0 else 0.0
    eps_b = max(column.bed_porosity, 1.0e-12)
    interstitial = u / eps_b
    residence = column.bed_volume / flow_rate if flow_rate > 0.0 else math.inf
    re_p = _particle_reynolds(column, flow_rate, mu=mu, rho=rho)
    pe_ax = _axial_peclet(column, flow_rate, D_molecular=D_molecular)
    maldistribution_index, maldistribution_risk = _maldistribution_risk(
        column=column,
        compression=compression,
        particle_reynolds=re_p,
    )
    warnings: list[str] = []
    blockers: list[str] = []
    if pressure > pump_pressure_limit_Pa:
        blockers.append(
            f"Pressure drop {pressure:.0f} Pa exceeds pump limit {pump_pressure_limit_Pa:.0f} Pa."
        )
    elif pressure > max_pressure_Pa:
        warnings.append(
            f"Pressure drop {pressure:.0f} Pa exceeds method target {max_pressure_Pa:.0f} Pa."
        )
    if compression > 0.50:
        blockers.append(f"Bed compression {compression:.1%} exceeds 50%.")
    elif compression > 0.20:
        warnings.append(f"Bed compression {compression:.1%} exceeds 20%.")
    if re_p > 10.0:
        warnings.append(
            f"Particle Reynolds number {re_p:.2g} exceeds the creeping-flow domain."
        )
    if pe_ax < 20.0:
        warnings.append(
            f"Axial Peclet number {pe_ax:.2g} indicates strong axial dispersion."
        )
    elif pe_ax > 5000.0:
        warnings.append(
            f"Axial Peclet number {pe_ax:.2g} may require finer axial resolution."
        )
    if maldistribution_risk == "high":
        warnings.append(
            "Flow maldistribution risk is high; check column-to-particle diameter ratio, compression, and distributor quality."
        )
    return ColumnOperabilityReport(
        step_name=step_name,
        pressure_drop_Pa=float(pressure),
        max_pressure_Pa=float(max_pressure_Pa),
        pump_pressure_limit_Pa=float(pump_pressure_limit_Pa),
        bed_compression_fraction=float(compression),
        particle_reynolds=float(re_p),
        axial_peclet=float(pe_ax),
        residence_time_s=float(residence),
        interstitial_velocity_m_s=float(interstitial),
        maldistribution_index=float(maldistribution_index),
        maldistribution_risk=maldistribution_risk,
        warnings=warnings,
        blockers=blockers,
    )


def evaluate_protein_a_performance(
    *,
    column: ColumnGeometry,
    method_steps: list[ChromatographyMethodStep],
    fmc=None,
    process_state: dict | None = None,
    D_molecular: float = 7.0e-11,
    loaded_elution: LoadedStateElutionResult | None = None,
) -> ProteinAPerformanceReport:
    """Evaluate Protein A binding, transport, cleaning, and leaching risks."""

    load_step = _first_step(method_steps, ChromatographyOperation.LOAD)
    elute_step = _first_step(method_steps, ChromatographyOperation.ELUTE)
    load_pH = load_step.buffer.pH if load_step else _state_value(process_state, "ph", 7.4)
    elution_pH = _elution_pH(elute_step)
    q_max = _fmc_value(fmc, "estimated_q_max", 60.0)
    if q_max <= 0.0:
        q_max = 60.0
    K_a_max = _state_value(process_state, "K_affinity", 1.0e5)
    isotherm = _protein_a_isotherm_from_state(
        q_max=q_max,
        process_state=process_state,
        default_K_a_max=K_a_max,
    )
    feed_conc = load_step.feed_concentration_mol_m3 if load_step else 1.0
    q_eq_load = float(isotherm.equilibrium_loading(feed_conc, load_pH))
    K_a_load = isotherm.K_a(load_pH)
    K_a_elution = (
        isotherm.K_a(elution_pH)
        * _protein_a_elution_suppression(elution_pH, process_state)
    )
    flow_rate = load_step.flow_rate_m3_s if load_step else 1.0e-8
    k_f = _film_mass_transfer_coefficient(column, flow_rate, D_molecular)
    resistance = column.particle_radius / max(3.0 * k_f, 1.0e-30)
    activity = _activity_retention(fmc)
    ligand_access = _ligand_accessibility_factor(fmc, activity)
    degradation = _alkaline_degradation_fraction(method_steps, process_state)
    leaching = max(
        0.0,
        _state_value(
            process_state,
            "protein_a_leaching_fraction_per_cycle",
            _fmc_value(fmc, "ligand_leaching_fraction", 0.0),
        ),
    )
    calibrated_cycle_loss = _state_value(
        process_state,
        "protein_a_cycle_loss_fraction",
        -1.0,
    )
    if calibrated_cycle_loss >= 0.0:
        cycle_loss = min(0.95, calibrated_cycle_loss)
    else:
        cycle_loss = min(0.95, 1.0 - (1.0 - degradation) * (1.0 - leaching))
    lifetime = _cycle_lifetime_to_fraction(cycle_loss, remaining_fraction=0.70)
    calibrated_lifetime = _state_value(
        process_state,
        "protein_a_cycle_lifetime_to_70pct",
        0.0,
    )
    if calibrated_lifetime > 0.0:
        lifetime = calibrated_lifetime
    residual_affinity = K_a_elution / max(K_a_load, 1.0e-30)
    elution_drive = max(0.0, min(1.0, 1.0 - residual_affinity))
    predicted_recovery = max(
        0.0,
        min(1.0, elution_drive * (1.0 - degradation) * (1.0 - leaching)),
    )
    if loaded_elution is not None and loaded_elution.mass_initial_bound_mol > 0.0:
        predicted_recovery = max(0.0, min(1.0, loaded_elution.recovery_fraction))
    warnings: list[str] = []
    if not (6.0 <= load_pH <= 8.5):
        warnings.append(
            f"Load pH {load_pH:.2g} is outside the usual Protein A IgG binding window."
        )
    if elution_pH > 4.5:
        warnings.append(
            f"Elution pH {elution_pH:.2g} may not suppress Protein A-IgG affinity enough."
        )
    elif elution_pH < 2.8:
        warnings.append(
            f"Elution pH {elution_pH:.2g} raises IgG denaturation and aggregation risk."
        )
    if load_step is not None:
        residence = column.bed_volume / max(load_step.flow_rate_m3_s, 1.0e-30)
        if resistance > residence:
            warnings.append(
                "Film/intraparticle mass-transfer resistance is longer than the load residence time."
            )
    if activity < 0.50:
        warnings.append(
            f"Protein A activity retention is {activity:.1%}; ligand immobilization may be over-harsh."
        )
    if leaching > 0.02:
        warnings.append(
            f"Ligand leaching fraction {leaching:.1%} exceeds a conservative development screen."
        )
    if degradation > 0.05:
        warnings.append(
            f"Alkaline degradation per cycle is {degradation:.1%}; CIP conditions likely shorten resin life."
        )
    if loaded_elution is not None and loaded_elution.mass_balance_error > 0.05:
        warnings.append(
            f"Loaded-state elution mass balance error is {loaded_elution.mass_balance_error:.1%}."
        )
    if loaded_elution is not None and loaded_elution.recovery_fraction < 0.70:
        warnings.append(
            f"Loaded-state elution recovery is {loaded_elution.recovery_fraction:.1%}; extend elution volume or lower effective elution pH."
        )
    return ProteinAPerformanceReport(
        q_max_mol_m3=float(q_max),
        load_pH=float(load_pH),
        elution_pH=float(elution_pH),
        K_a_load_m3_mol=float(K_a_load),
        K_a_elution_m3_mol=float(K_a_elution),
        q_equilibrium_load_mol_m3=float(q_eq_load),
        ligand_accessibility_factor=float(ligand_access),
        activity_retention=float(activity),
        mass_transfer_coefficient_m_s=float(k_f),
        mass_transfer_resistance_s=float(resistance),
        alkaline_degradation_fraction_per_cycle=float(degradation),
        cycle_lifetime_to_70pct_capacity=float(lifetime),
        ligand_leaching_fraction_per_cycle=float(leaching),
        leaching_risk=_leaching_risk(leaching),
        predicted_elution_recovery_fraction=float(predicted_recovery),
        warnings=warnings,
        assumptions=[
            "Protein A binding is represented with a pH-dependent Langmuir-style affinity curve.",
            "Mass-transfer resistance is screened with a Wilson-Geankoplis-style film coefficient.",
            "Cycle lifetime combines alkaline degradation and measured/inferred ligand leaching as independent per-cycle losses.",
        ],
        wet_lab_caveats=[
            "Fit qmax and affinity against static binding and breakthrough data for the target IgG.",
            "Measure ligand leaching under the exact cleaning, elution, and storage buffers.",
            "Validate alkaline cleaning lifetime with cycling data; this screen does not replace resin lifetime studies.",
        ],
    )


def _summarize_step(
    column: ColumnGeometry,
    step: ChromatographyMethodStep,
) -> ChromatographyStepResult:
    flow = max(step.flow_rate_m3_s, 0.0)
    pressure = column.pressure_drop(flow) if flow > 0.0 else 0.0
    residence = column.bed_volume / flow if flow > 0.0 else math.inf
    column_volumes = flow * max(step.duration_s, 0.0) / column.bed_volume if column.bed_volume > 0 else 0.0
    compression = column.bed_compression_fraction(pressure)
    notes: list[str] = []
    if step.target_residence_time_s > 0.0 and math.isfinite(residence):
        relative_error = abs(residence - step.target_residence_time_s) / step.target_residence_time_s
        if relative_error > 0.35:
            notes.append(
                "Actual residence time differs from recipe target by more than 35%."
            )
    return ChromatographyStepResult(
        name=step.name,
        operation=step.operation,
        duration_s=float(step.duration_s),
        flow_rate_m3_s=float(flow),
        column_volumes=float(column_volumes),
        residence_time_s=float(residence),
        pressure_drop_Pa=float(pressure),
        bed_compression_fraction=float(compression),
        buffer=step.buffer,
        diagnostics={
            "buffer_pH": float(step.buffer.pH),
            "buffer_conductivity_mS_cm": float(step.buffer.conductivity_mS_cm),
        },
        notes=notes,
    )


def _worst_operability_report(
    *,
    column: ColumnGeometry,
    steps: list[ChromatographyMethodStep],
    max_pressure_Pa: float,
    pump_pressure_limit_Pa: float,
    D_molecular: float,
) -> ColumnOperabilityReport:
    active_steps = [step for step in steps if step.flow_rate_m3_s > 0.0]
    if not active_steps:
        return evaluate_column_operability(
            column,
            0.0,
            step_name="no-flow method",
            max_pressure_Pa=max_pressure_Pa,
            pump_pressure_limit_Pa=pump_pressure_limit_Pa,
            D_molecular=D_molecular,
        )
    reports = [
        evaluate_column_operability(
            column,
            step.flow_rate_m3_s,
            step_name=step.name,
            max_pressure_Pa=max_pressure_Pa,
            pump_pressure_limit_Pa=pump_pressure_limit_Pa,
            D_molecular=D_molecular,
        )
        for step in active_steps
    ]
    return max(
        reports,
        key=lambda report: (
            len(report.blockers),
            len(report.warnings),
            report.pressure_drop_Pa,
            report.bed_compression_fraction,
        ),
    )


def _first_step(
    steps: list[ChromatographyMethodStep],
    operation: ChromatographyOperation,
) -> ChromatographyMethodStep | None:
    for step in steps:
        if step.operation == operation:
            return step
    return None


def _first_step_after(
    steps: list[ChromatographyMethodStep],
    operation: ChromatographyOperation,
    anchor: ChromatographyMethodStep | None,
) -> ChromatographyMethodStep | None:
    if anchor is None:
        return _first_step(steps, operation)
    seen_anchor = False
    for step in steps:
        if step is anchor:
            seen_anchor = True
            continue
        if seen_anchor and step.operation == operation:
            return step
    return None


def _process_state_dict(process_state) -> dict[str, float]:
    if process_state is None:
        return {}
    if hasattr(process_state, "to_dict"):
        return dict(process_state.to_dict())
    if isinstance(process_state, dict):
        return dict(process_state)
    return {}


def _state_value(process_state, key: str, default: float) -> float:
    state = _process_state_dict(process_state)
    try:
        return float(state.get(key, default))
    except (TypeError, ValueError):
        return float(default)


def _fmc_value(fmc, field_name: str, default: float) -> float:
    try:
        value = getattr(fmc, field_name)
    except AttributeError:
        return float(default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _activity_retention(fmc) -> float:
    value = _fmc_value(fmc, "activity_retention", 1.0)
    if value <= 0.0:
        return 1.0
    return max(0.0, min(1.0, value))


def _protein_a_isotherm_from_state(
    *,
    q_max: float,
    process_state,
    default_K_a_max: float = 1.0e5,
) -> ProteinAIsotherm:
    """Build the operational Protein A isotherm from M3 calibration state."""

    return ProteinAIsotherm(
        q_max=max(float(q_max), 1.0e-12),
        K_a_max=max(_state_value(process_state, "K_affinity", default_K_a_max), 1.0e-12),
        pH_transition=_state_value(process_state, "protein_a_pH_transition", 4.2),
        steepness=max(_state_value(process_state, "protein_a_pH_steepness", 4.0), 1.0e-12),
    )


def _protein_a_elution_suppression(pH: float, process_state) -> float:
    """Return extra low-pH suppression of Protein A-IgG activity."""

    if pH > 4.5:
        return 1.0
    default = 1.0e-5
    value = _state_value(
        process_state,
        "protein_a_elution_residual_activity",
        default,
    )
    return max(0.0, min(1.0, value))


def _ligand_accessibility_factor(fmc, activity: float) -> float:
    reagent_area = _fmc_value(fmc, "reagent_accessible_area_per_bed_volume", 0.0)
    ligand_area = _fmc_value(fmc, "ligand_accessible_area_per_bed_volume", 0.0)
    if reagent_area > 0.0 and ligand_area > 0.0:
        area_factor = max(0.0, min(1.0, ligand_area / reagent_area))
    else:
        area_factor = 1.0
    coupled = _fmc_value(fmc, "total_coupled_density", 0.0)
    active = _fmc_value(fmc, "functional_ligand_density", 0.0)
    if coupled > 0.0 and active >= 0.0:
        active_factor = max(0.0, min(1.0, active / coupled))
    else:
        active_factor = activity
    return max(0.0, min(1.0, area_factor * active_factor))


def _elution_pH(step: ChromatographyMethodStep | None) -> float:
    if step is None:
        return 3.5
    # B-2e follow-on: typed GradientContext takes precedence; legacy fallback.
    grad = _resolve_gradient(step)
    if grad is not None and grad.gradient_field.lower() == "ph":
        return float(grad.end_value)
    return float(step.buffer.pH)


def _alkaline_degradation_fraction(
    steps: list[ChromatographyMethodStep],
    process_state=None,
) -> float:
    exposure = 0.0
    base_rate = _state_value(
        process_state,
        "protein_a_alkaline_rate_s_at_pH13",
        _state_value(process_state, "protein_a_alkaline_degradation_rate_s", 2.0e-5),
    )
    for step in steps:
        pH = float(step.buffer.pH)
        if pH < 10.5 or step.duration_s <= 0.0:
            continue
        # Screening correlation: Protein A degradation rate increases roughly
        # tenfold per pH unit near alkaline cleaning conditions.
        rate_s = max(0.0, base_rate) * 10.0 ** (pH - 13.0)
        exposure += rate_s * step.duration_s
    return max(0.0, min(0.95, 1.0 - math.exp(-exposure)))


def _cycle_lifetime_to_fraction(
    per_cycle_loss: float,
    *,
    remaining_fraction: float,
) -> float:
    if per_cycle_loss <= 1.0e-9:
        return 200.0
    retained = max(1.0e-9, 1.0 - per_cycle_loss)
    return max(1.0, min(1000.0, math.log(remaining_fraction) / math.log(retained)))


def _leaching_risk(leaching_fraction: float) -> str:
    if leaching_fraction > 0.05:
        return "high"
    if leaching_fraction > 0.01:
        return "medium"
    return "low"


def _peak_stats(
    time: np.ndarray,
    concentration: np.ndarray,
) -> tuple[float, float, float, float]:
    """Return peak apex time, height, area, and full width at half maximum."""

    t = np.asarray(time, dtype=float)
    c = np.maximum(np.asarray(concentration, dtype=float), 0.0)
    if t.size == 0 or c.size == 0 or float(np.max(c)) <= 0.0:
        return 0.0, 0.0, 0.0, 0.0
    apex_idx = int(np.argmax(c))
    peak_time = float(t[apex_idx])
    peak_height = float(c[apex_idx])
    area = float(np.trapezoid(c, t))
    half = peak_height / 2.0
    above = np.where(c >= half)[0]
    if above.size < 2:
        return peak_time, peak_height, area, 0.0
    left = int(above[0])
    right = int(above[-1])
    left_t = float(t[left])
    right_t = float(t[right])
    if left > 0 and c[left] > c[left - 1]:
        frac = (half - c[left - 1]) / max(c[left] - c[left - 1], 1.0e-30)
        left_t = float(t[left - 1] + frac * (t[left] - t[left - 1]))
    if right < c.size - 1 and c[right] > c[right + 1]:
        frac = (half - c[right]) / min(c[right + 1] - c[right], -1.0e-30)
        right_t = float(t[right] + frac * (t[right + 1] - t[right]))
    return peak_time, peak_height, area, max(0.0, right_t - left_t)


def _particle_reynolds(
    column: ColumnGeometry,
    flow_rate: float,
    *,
    mu: float,
    rho: float,
) -> float:
    if flow_rate <= 0.0:
        return 0.0
    u = column.superficial_velocity(flow_rate)
    denom = mu * max(1.0 - column.bed_porosity, 1.0e-12)
    return rho * u * column.particle_diameter / denom


def _axial_peclet(
    column: ColumnGeometry,
    flow_rate: float,
    *,
    D_molecular: float,
) -> float:
    if flow_rate <= 0.0:
        return 0.0
    u = column.superficial_velocity(flow_rate)
    dispersion = max(u * column.particle_diameter / (2.0 * max(column.bed_porosity, 1.0e-12)), D_molecular)
    return u * column.bed_height / dispersion


def _film_mass_transfer_coefficient(
    column: ColumnGeometry,
    flow_rate: float,
    D_molecular: float,
    *,
    mu: float = 1.0e-3,
    rho: float = 1000.0,
) -> float:
    if flow_rate <= 0.0:
        return D_molecular / max(column.particle_diameter, 1.0e-12)
    u = column.superficial_velocity(flow_rate)
    re = rho * u * column.particle_diameter / mu
    sc = mu / max(rho * D_molecular, 1.0e-30)
    sh = max(2.0, (1.09 / max(column.bed_porosity, 1.0e-12)) * (re * sc) ** (1.0 / 3.0))
    return sh * D_molecular / max(column.particle_diameter, 1.0e-12)


def _maldistribution_risk(
    *,
    column: ColumnGeometry,
    compression: float,
    particle_reynolds: float,
) -> tuple[float, str]:
    diameter_ratio = column.diameter / max(column.particle_diameter, 1.0e-12)
    ratio_score = 0.0
    if diameter_ratio < 30.0:
        ratio_score = 0.45
    elif diameter_ratio < 50.0:
        ratio_score = 0.25
    compression_score = min(0.35, max(0.0, compression / 0.50) * 0.35)
    re_score = 0.25 if particle_reynolds > 10.0 else (0.10 if particle_reynolds > 2.0 else 0.0)
    score = max(0.0, min(1.0, ratio_score + compression_score + re_score))
    if score >= 0.70:
        risk = "high"
    elif score >= 0.35:
        risk = "medium"
    else:
        risk = "low"
    return score, risk


# ─── v0.4.0 (C2) — ModelMode-conditional output gating ─────────────────────


def _read_model_mode(process_state) -> str:
    """Pull the active ModelMode value from process_state (string form).

    Returns "" when no mode is provided. Compare-by-value per CLAUDE.md
    cp1252/enum-reload note.
    """
    if isinstance(process_state, dict):
        raw = process_state.get("model_mode", "")
    elif process_state is not None:
        raw = getattr(process_state, "model_mode", "")
    else:
        raw = ""
    if raw is None:
        return ""
    return str(getattr(raw, "value", raw)).strip().lower()


def _apply_mode_guard(
    manifest: ModelManifest,
    process_state,
    *,
    has_calibration: bool,
):
    """Apply ModelMode-conditional manifest gating per architect Deficit 2.

    Modes (matched by string value to avoid enum-reload identity issues):
      - "hybrid_coupled" (default): no change.
      - "empirical_engineering" without calibration → cap manifest tier at
        QUALITATIVE_TREND. The scientific-advisor's reading: empirical
        engineering mode is for design-space screening only; without a
        calibrated FMC it cannot defend a numeric DBC / pressure / cycle-life.
      - "mechanistic_research" → tag the result as EXPLORATORY regardless of
        calibration tier. The user is exploring mechanisms, not making a
        process claim. Marker is added via manifest.diagnostics
        ("exploratory_only" = True) and an assumption; the tier itself is
        only downgraded to QUALITATIVE_TREND if it was stronger than that.
    """
    from dataclasses import replace as _replace

    from dpsim.datatypes import ModelEvidenceTier as _Tier

    mode = _read_model_mode(process_state)
    if not mode or mode == "hybrid_coupled":
        return manifest

    order = list(_Tier)
    new_assumptions = list(manifest.assumptions)
    new_diagnostics = dict(manifest.diagnostics)
    new_tier = manifest.evidence_tier

    if mode == "empirical_engineering" and not has_calibration:
        if order.index(manifest.evidence_tier) < order.index(_Tier.QUALITATIVE_TREND):
            new_tier = _Tier.QUALITATIVE_TREND
        new_assumptions.append(
            "ModelMode=empirical_engineering with no calibration — manifest "
            "tier capped at QUALITATIVE_TREND. Empirical mode supports "
            "design-space ranking only; load a CalibrationStore for numeric "
            "DBC / pressure / cycle-life claims."
        )
        new_diagnostics["mode_guard_empirical_uncalibrated"] = True
    elif mode == "mechanistic_research":
        new_diagnostics["exploratory_only"] = True
        new_diagnostics["mode_guard_mechanistic"] = True
        # Mechanistic mode tags the result as exploratory but does NOT
        # downgrade the tier. The exploratory diagnostic is the actionable
        # signal for downstream consumers; the tier still reflects the
        # underlying calibration state.
        new_assumptions.append(
            "ModelMode=mechanistic_research — result is EXPLORATORY ONLY. "
            "Mechanistic-mode runs explore physical mechanisms; they are not "
            "process claims regardless of calibration state."
        )

    return _replace(
        manifest,
        evidence_tier=new_tier,
        assumptions=new_assumptions,
        diagnostics=new_diagnostics,
    )


# ─── v0.4.0 (C7) — family-aware Protein A scope-of-claim guard ──────────────


def _protein_a_family_warning(process_state, *, fmc=None) -> str:
    """Return a scope-of-claim warning when Protein A is run on non-A+C families.

    Reads the polymer family from ``process_state["polymer_family"]`` first,
    then falls back to the FMC's polymer_family attribute when present.
    Empty / agarose_chitosan returns "" (no warning). Other recognised
    families return a tier-downgrade warning string.
    """
    raw = ""
    if isinstance(process_state, dict):
        raw = str(process_state.get("polymer_family", "") or "").strip().lower()
    elif process_state is not None:
        raw = str(getattr(process_state, "polymer_family", "") or "").strip().lower()
    if not raw and fmc is not None:
        raw = str(getattr(fmc, "polymer_family", "") or "").strip().lower()
    if not raw or raw == "agarose_chitosan":
        return ""
    return (
        f"Protein A method runs against polymer_family={raw!r}. The default "
        "ProteinAIsotherm parameters (q_max, K_a_max, pH_transition, steepness) "
        "are tuned for agarose+chitosan substrate. Cycle-life, leaching, and "
        "DBC numbers are illustrative only until calibrated against a "
        "family-specific binding/cycling assay (architect-coherence-audit D6 / "
        "scientific-advisor §4)."
    )


def _cap_manifest_for_non_ac_family(
    manifest: ModelManifest,
    family_warning: str,
):
    """Cap a manifest tier at QUALITATIVE_TREND when family is non-A+C and uncalibrated.

    The cap is conditional on the FMC not being calibrated (i.e. tier is
    SEMI_QUANTITATIVE or weaker). When the upstream FMC carries a
    family-specific calibration (CALIBRATED_LOCAL+), the family-aware tier
    inherits from that calibration and is NOT capped — the calibrated tier
    is the user's claim that the family numbers are decision-grade.
    """
    from dataclasses import replace as _replace

    from dpsim.datatypes import ModelEvidenceTier as _Tier

    current = manifest.evidence_tier
    if current in {_Tier.CALIBRATED_LOCAL, _Tier.VALIDATED_QUANTITATIVE}:
        return manifest  # Calibrated for this family → trust the calibration.
    order = list(_Tier)
    capped = max(
        order.index(current),
        order.index(_Tier.QUALITATIVE_TREND),
    )
    new_tier = order[capped]
    new_assumptions = list(manifest.assumptions) + [
        f"M3 manifest tier capped at {new_tier.value} due to non-A+C family.",
    ]
    new_diagnostics = {
        **manifest.diagnostics,
        "non_ac_family_cap_applied": True,
        "non_ac_family_warning": family_warning,
    }
    return _replace(
        manifest,
        evidence_tier=new_tier,
        assumptions=new_assumptions,
        diagnostics=new_diagnostics,
    )


# ─── v0.3.0 (B6) — claim-strength downgrades for uncalibrated outputs ────────
#
# Per scientific-advisor §3 (M3-S3, M2-S1, evidence-tier scope-of-claim audit):
# cycle-life, impurity log-reduction, and leaching numeric outputs are
# UNSUPPORTED as quantitative claims without resin-specific cycling /
# clearance / leaching assays. The helpers below convert the raw floats
# into bucketed ranking labels when no calibration is available, so UI
# and CLI surfaces do not present false precision.


def is_method_calibrated(fmc) -> bool:
    """Return True iff the FMC carries a CALIBRATED_LOCAL+ manifest tier.

    Uses the typed ``ModelEvidenceTier`` enum on ``fmc.model_manifest``;
    ignores the legacy string ``confidence_tier`` side-channel (architect-
    coherence audit D3 deficit, deferred to v0.4.0 module C3).
    """
    from dpsim.datatypes import ModelEvidenceTier as _Tier

    manifest = getattr(fmc, "model_manifest", None)
    tier = getattr(manifest, "evidence_tier", None)
    if tier is None:
        return False
    return tier in {_Tier.CALIBRATED_LOCAL, _Tier.VALIDATED_QUANTITATIVE}


def cycle_lifetime_label(
    report: ProteinAPerformanceReport,
    *,
    is_calibrated: bool = False,
) -> str:
    """Cycle-lifetime as a bucketed ranking when uncalibrated; precise otherwise."""
    cycles = float(report.cycle_lifetime_to_70pct_capacity)
    if is_calibrated:
        return f"{cycles:.0f} cycles"
    if cycles < 30:
        bucket = "<30 cycles (low)"
    elif cycles < 100:
        bucket = "30-100 cycles (moderate)"
    elif cycles < 300:
        bucket = "100-300 cycles (good)"
    else:
        bucket = ">300 cycles (excellent)"
    return f"{bucket}, illustrative — calibration required"


def log10_reduction_label(
    species: ImpuritySpeciesReport,
    *,
    is_calibrated: bool = False,
) -> str:
    """Impurity log10 reduction as a bucketed ranking when uncalibrated."""
    log10r = float(species.log10_reduction)
    if is_calibrated:
        return f"{log10r:.1f} LRV"
    if log10r < 1.0:
        bucket = "<1 LRV (poor)"
    elif log10r < 2.0:
        bucket = "1-2 LRV (moderate)"
    elif log10r < 4.0:
        bucket = "2-4 LRV (good)"
    else:
        bucket = ">4 LRV (excellent)"
    return f"{bucket}, illustrative — calibration required"


def leaching_label(
    report: ProteinAPerformanceReport,
    *,
    is_calibrated: bool = False,
) -> str:
    """Ligand leaching as a categorical risk label when uncalibrated."""
    frac = float(report.ligand_leaching_fraction_per_cycle)
    if is_calibrated:
        return f"{frac:.2%} per cycle ({report.leaching_risk})"
    return f"{report.leaching_risk} risk, illustrative — calibration required"


__all__ = [
    "BufferCondition",
    "ChromatographyMethodResult",
    "ChromatographyMethodStep",
    "ChromatographyOperation",
    "ChromatographyStepResult",
    "ColumnEfficiencyReport",
    "ColumnOperabilityReport",
    "ImpurityClearanceReport",
    "ImpuritySpeciesReport",
    "LoadedStateElutionResult",
    "ProteinAPerformanceReport",
    "cycle_lifetime_label",
    "default_protein_a_method_steps",
    "evaluate_column_efficiency",
    "evaluate_column_operability",
    "evaluate_impurity_clearance",
    "evaluate_protein_a_performance",
    "is_method_calibrated",
    "leaching_label",
    "log10_reduction_label",
    "run_loaded_state_elution",
    "run_chromatography_method",
]
