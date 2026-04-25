"""High-level M1 -> M2 -> M3 lifecycle orchestration.

This module is the first implementation of the clean-slate target architecture.
It deliberately reuses the validated legacy numerical kernels instead of
rewriting them. The new responsibility here is scientific sequencing:

1. Run M1 fabrication and export only the stable M1->M2 contract.
2. Run M2 functionalization as an ordered wet-lab chemistry sequence.
3. Convert functional media to an M2->M3 contract.
4. Run M3 affinity chromatography performance using the media contract.
5. Store all handoffs in a result graph with inherited evidence tiers.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from dpsim.core.parameters import ResolvedParameter
from dpsim.core.performance_recipe import (
    PerformanceRecipe,
    performance_recipe_from_resolved,
)
from dpsim.core.process_recipe import ProcessRecipe, default_affinity_media_recipe
from dpsim.core.recipe_validation import validate_recipe_first_principles
from dpsim.core.result_graph import ResultGraph, ResultNode
from dpsim.core.validation import (
    ValidationReport,
    ValidationSeverity,
    validate_model_manifest_domains,
)
from dpsim.datatypes import (
    FullResult,
    M1ExportContract,
    ModelEvidenceTier,
    ModelManifest,
    RunContext,
    SimulationParameters,
)
from dpsim.lifecycle.recipe_resolver import resolve_lifecycle_inputs
from dpsim.runtime_paths import default_output_dir
from dpsim.module2_functionalization.acs import ACSSiteType
from dpsim.module2_functionalization.modification_steps import (
    ModificationStep,
    ModificationStepType,
)
from dpsim.module2_functionalization.orchestrator import (
    FunctionalMediaContract,
    FunctionalMicrosphere,
    ModificationOrchestrator,
    build_functional_media_contract,
)
from dpsim.module3_performance.hydrodynamics import ColumnGeometry
from dpsim.module3_performance.method import (
    ChromatographyMethodResult,
    run_chromatography_method,
)
from dpsim.module3_performance.orchestrator import BreakthroughResult, run_breakthrough
from dpsim.pipeline.orchestrator import PipelineOrchestrator, export_for_module2
from dpsim.properties.database import PropertyDatabase
from dpsim.trust import assess_trust


@dataclass
class DownstreamLifecycleResult:
    """Complete lifecycle output for one process recipe.

    Attributes are intentionally explicit rather than hidden in dictionaries so
    downstream developers can audit exactly which handoff object was consumed
    by each stage.
    """

    recipe: ProcessRecipe
    graph: ResultGraph
    validation: ValidationReport
    m1_result: FullResult | None = None
    m1_contract: object | None = None
    m2_microsphere: FunctionalMicrosphere | None = None
    functional_media_contract: FunctionalMediaContract | None = None
    m3_method: ChromatographyMethodResult | None = None
    m3_breakthrough: BreakthroughResult | None = None
    dsd_variants: list["DSDMediaVariant"] = field(default_factory=list)
    dsd_summary: "DSDPropagationSummary | None" = None
    # v0.2.0 (A5): typed M3 primitive exposed for downstream UI/dossier
    # consumers. The lifecycle orchestrator still drives M3 via the
    # legacy dual-path (run_chromatography_method + _run_dsd_downstream_screen);
    # full replacement with run_method_simulation is v0.3.0 module B5 work.
    performance_recipe: PerformanceRecipe | None = None
    # v0.5.0 (D3): ProcessDossier is the default reproducible-run artifact.
    # Built from the M1 FullResult + calibration store + recipe target profile.
    # ``None`` only when M1 itself failed to produce a result.
    process_dossier: Any = None
    resolved_parameters: dict[str, ResolvedParameter] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    @property
    def weakest_evidence_tier(self) -> ModelEvidenceTier:
        """Weakest evidence tier across lifecycle nodes."""
        return self.graph.weakest_evidence_tier()


@dataclass
class DSDMediaVariant:
    """One downstream media estimate for a representative M1 size quantile."""

    quantile: float
    mass_fraction: float
    bead_diameter_m: float
    pore_size_m: float
    porosity: float
    G_DN_Pa: float
    E_star_Pa: float
    estimated_q_max_mol_m3: float
    pressure_drop_Pa: float
    bed_compression_fraction: float
    representative_source: str = "quantile"
    breakthrough_simulated: bool = False
    dbc_5pct_mol_m3: float = 0.0
    dbc_10pct_mol_m3: float = 0.0
    dbc_50pct_mol_m3: float = 0.0
    breakthrough_mass_balance_error: float = 0.0
    residual_reagent_concentrations: dict[str, float] = field(default_factory=dict)
    residual_warnings: list[str] = field(default_factory=list)


@dataclass
class DSDPropagationSummary:
    """Mass-weighted downstream summary across representative DSD quantiles."""

    n_quantiles: int
    q_max_weighted_mean_mol_m3: float
    q_max_weighted_p05_mol_m3: float
    q_max_weighted_p50_mol_m3: float
    q_max_weighted_p95_mol_m3: float
    q_max_min_mol_m3: float
    q_max_max_mol_m3: float
    pressure_drop_min_Pa: float
    pressure_drop_weighted_p50_Pa: float
    pressure_drop_weighted_p95_Pa: float
    pressure_drop_max_Pa: float
    bed_compression_weighted_p50_fraction: float
    bed_compression_weighted_p95_fraction: float
    max_bed_compression_fraction: float
    max_residual_concentration_mol_m3: float
    breakthrough_simulated: bool = False
    dbc_10_weighted_mean_mol_m3: float = 0.0
    dbc_10_weighted_p05_mol_m3: float = 0.0
    dbc_10_weighted_p50_mol_m3: float = 0.0
    dbc_10_weighted_p95_mol_m3: float = 0.0
    max_breakthrough_mass_balance_error: float = 0.0
    quantile_selection: str = "representative"
    represented_mass_fraction: float = 1.0
    dsd_source: str = ""
    n_dsd_bins: int = 0
    d10_m: float = 0.0
    d50_m: float = 0.0
    d90_m: float = 0.0
    warnings: list[str] = field(default_factory=list)


def default_protein_a_functionalization_steps() -> list[ModificationStep]:
    """Return a wet-lab plausible ECH -> Protein A -> quench sequence.

    The values mirror reagent-profile defaults. Protein A coupling remains
    ranking-only until target-specific binding data are calibrated, and the M3
    result inherits that weak evidence tier through the FunctionalMediaContract.
    """

    return [
        ModificationStep(
            step_type=ModificationStepType.ACTIVATION,
            reagent_key="ech_activation",
            target_acs=ACSSiteType.HYDROXYL,
            product_acs=ACSSiteType.EPOXIDE,
            temperature=298.15,
            time=7200.0,
            ph=12.0,
            reagent_concentration=100.0,
        ),
        ModificationStep(
            step_type=ModificationStepType.WASHING,
            reagent_key="wash_buffer",
            target_acs=ACSSiteType.EPOXIDE,
            temperature=298.15,
            time=3600.0,
            ph=7.4,
            reagent_concentration=0.0,
        ),
        ModificationStep(
            step_type=ModificationStepType.PROTEIN_COUPLING,
            reagent_key="protein_a_coupling",
            target_acs=ACSSiteType.EPOXIDE,
            temperature=277.15,
            time=57600.0,
            ph=9.0,
            reagent_concentration=0.02,
        ),
        ModificationStep(
            step_type=ModificationStepType.WASHING,
            reagent_key="wash_buffer",
            target_acs=ACSSiteType.EPOXIDE,
            temperature=277.15,
            time=3600.0,
            ph=7.4,
            reagent_concentration=0.0,
        ),
        ModificationStep(
            step_type=ModificationStepType.QUENCHING,
            reagent_key="ethanolamine_quench",
            target_acs=ACSSiteType.EPOXIDE,
            temperature=298.15,
            time=7200.0,
            ph=8.5,
            reagent_concentration=1000.0,
        ),
        ModificationStep(
            step_type=ModificationStepType.WASHING,
            reagent_key="wash_buffer",
            target_acs=ACSSiteType.EPOXIDE,
            temperature=298.15,
            time=7200.0,
            ph=7.4,
            reagent_concentration=0.0,
        ),
    ]


class DownstreamProcessOrchestrator:
    """Coordinate complete lifecycle simulation using stable handoff contracts."""

    def __init__(
        self,
        db: PropertyDatabase | None = None,
        output_dir: str | Path | None = None,
    ) -> None:
        self.db = db or PropertyDatabase()
        self.output_dir = Path(output_dir) if output_dir else default_output_dir("downstream_lifecycle")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(
        self,
        recipe: ProcessRecipe | None = None,
        params: SimulationParameters | None = None,
        functionalization_steps: list[ModificationStep] | None = None,
        column: ColumnGeometry | None = None,
        run_context: RunContext | None = None,
        propagate_dsd: bool = True,
        dsd_mode: str = "representative",
        dsd_max_representatives: int = 9,
        dsd_run_breakthrough: bool = False,
        dsd_quantiles: tuple[float, ...] = (0.10, 0.50, 0.90),
    ) -> DownstreamLifecycleResult:
        """Run M1 fabrication, M2 Protein A functionalization, and M3 breakthrough.

        The method is intentionally conservative: it records warnings instead
        of suppressing them and uses the legacy evidence-tier system to keep
        affinity predictions from appearing more quantitative than the M2 data
        justify.
        """

        recipe = recipe or default_affinity_media_recipe()

        # v0.2.0 (A5): first-principles guardrails run BEFORE recipe resolution.
        # Findings (BLOCKER/WARNING) are merged into the lifecycle validation
        # report so downstream consumers see them alongside per-stage issues.
        # The pre-resolution pass evaluates G1 (M1 wash mass-balance) and emits
        # G3 deferred-warning when an elute gradient_field is declared without
        # a resolved isotherm. G5 is checked again post-FMC below.
        fp_report = validate_recipe_first_principles(recipe)

        resolved_inputs = resolve_lifecycle_inputs(recipe, base_params=params)
        params = resolved_inputs.parameters

        graph = ResultGraph()
        validation = ValidationReport()
        validation.extend(fp_report)
        validation.extend(resolved_inputs.validation)

        # v0.2.0 (A5): expose the typed M3 primitive on the lifecycle result.
        # UI / ProcessDossier consumers can pass this to run_method_simulation.
        performance_recipe: PerformanceRecipe | None = None
        try:
            performance_recipe = performance_recipe_from_resolved(resolved_inputs)
        except ValueError as exc:
            validation.add(
                ValidationSeverity.WARNING,
                "PERFORMANCE_RECIPE_UNAVAILABLE",
                (
                    f"PerformanceRecipe could not be built from the resolved "
                    f"recipe: {exc}. Lifecycle continues, but downstream M3 "
                    "consumers expecting the typed primitive will see None."
                ),
                module="M3",
            )
        notes: list[str] = []
        calibration_store = getattr(run_context, "calibration_store", None)

        if functionalization_steps is None:
            functionalization_steps = resolved_inputs.functionalization_steps
        else:
            validation.add(
                ValidationSeverity.WARNING,
                "RECIPE_OVERRIDE",
                "Explicit functionalization_steps were supplied; M2 is not fully recipe-derived.",
                module="M2",
                recommendation="Move M2 step definitions into ProcessRecipe for auditable production use.",
            )
        if column is None:
            column = resolved_inputs.column
        else:
            validation.add(
                ValidationSeverity.WARNING,
                "RECIPE_OVERRIDE",
                "Explicit column geometry was supplied; M3 packing geometry is not fully recipe-derived.",
                module="M3",
                recommendation="Move column geometry into ProcessRecipe for auditable production use.",
            )

        # M1: fabrication is delegated to the reused validated pipeline. The
        # clean architecture boundary is the M1ExportContract produced below.
        m1_orch = PipelineOrchestrator(db=self.db, output_dir=self.output_dir / "m1")
        m1_result = m1_orch.run_single(params, run_context=run_context)
        # Use the parameter object returned by the M1 pipeline from here on.
        # It may include RunContext calibration overrides, including P2 M1 wash
        # retention factors, that must carry into DSD and downstream gates.
        params = m1_result.parameters
        props = self.db.update_for_conditions(
            T_oil=params.formulation.T_oil,
            c_agarose=params.formulation.c_agarose,
            c_chitosan=params.formulation.c_chitosan,
            c_span80=params.formulation.c_span80,
        )
        trust = assess_trust(m1_result, params, props)
        m1_contract = export_for_module2(m1_result, trust, props=props)
        m1_contract, m1_physical_qc_overrides, m1_physical_qc_diagnostics = (
            _apply_m1_physical_qc_to_contract(m1_contract, calibration_store)
        )
        if m1_physical_qc_overrides:
            validation.add(
                ValidationSeverity.INFO,
                "M1_PHYSICAL_QC_APPLIED",
                "Measured M1 physical-QC entries were applied to the M1 handoff contract.",
                module="M1",
                recommendation=(
                    "Confirm the measured lot, buffer state, swelling state, "
                    "and assay method match the simulated process recipe."
                ),
            )
            _add_m1_physical_qc_shift_validation(
                validation=validation,
                diagnostics=m1_physical_qc_diagnostics,
            )
        for violation in m1_contract.validate_units():
            validation.add(
                ValidationSeverity.BLOCKER,
                "M1_CONTRACT_UNITS",
                violation,
                module="M1",
                recommendation="Inspect the M1 export contract before passing it to M2.",
            )
        carryover_diagnostics = _m1_carryover_diagnostics(m1_contract, resolved_inputs)
        _validate_m1_carryover_for_downstream(
            m1_contract=m1_contract,
            resolved_inputs=resolved_inputs,
            validation=validation,
        )

        graph.add_node(
            ResultNode(
                node_id="M1",
                stage="M1_fabrication",
                label="Microsphere fabrication",
                payload=m1_result,
                manifest=_composite_manifest_from_m1(m1_result),
                diagnostics={
                    "trust_level": trust.level,
                    "bead_d50_m": m1_contract.bead_d50,
                    "bead_d10_m": (
                        0.0 if m1_contract.bead_size_distribution is None
                        else m1_contract.bead_size_distribution.d10_m
                    ),
                    "bead_d90_m": (
                        0.0 if m1_contract.bead_size_distribution is None
                        else m1_contract.bead_size_distribution.d90_m
                    ),
                    "n_dsd_bins": (
                        0 if m1_contract.bead_size_distribution is None
                        else len(m1_contract.bead_size_distribution.diameter_bins_m)
                    ),
                    "pore_size_m": m1_contract.pore_size_mean,
                    "residual_oil_volume_fraction": m1_contract.residual_oil_volume_fraction,
                    "residual_surfactant_kg_m3": (
                        m1_contract.residual_surfactant_concentration_kg_m3
                    ),
                    "residual_oil_limit": (
                        resolved_inputs.max_residual_oil_volume_fraction
                    ),
                    "residual_surfactant_limit_kg_m3": (
                        resolved_inputs.max_residual_surfactant_concentration_kg_m3
                    ),
                    "residual_oil_limit_ratio": (
                        carryover_diagnostics["residual_oil_limit_ratio"]
                    ),
                    "residual_surfactant_limit_ratio": (
                        carryover_diagnostics["residual_surfactant_limit_ratio"]
                    ),
                    "wash_cycles": (
                        0 if m1_contract.washing_model is None
                        else m1_contract.washing_model.wash_cycles
                    ),
                    "wash_volume_ratio": (
                        0.0 if m1_contract.washing_model is None
                        else m1_contract.washing_model.wash_volume_ratio
                    ),
                    "oil_removal_efficiency": m1_contract.oil_removal_efficiency,
                    "physical_qc_overrides": list(m1_physical_qc_overrides),
                    **m1_physical_qc_diagnostics,
                },
                wet_lab_caveats=[
                    "M1 bead-size, pore, swelling, mechanics, and wash-residual predictions require microscopy or laser diffraction, pore imaging or SEC inverse-size calibration, swelling ratio, compression/modulus testing, and residual oil/surfactant assays before release decisions.",
                ],
            )
        )
        for warning in trust.warnings:
            validation.add(
                ValidationSeverity.WARNING,
                "M1_TRUST_WARNING",
                warning,
                module="M1",
            )
        for blocker in trust.blockers:
            validation.add(
                ValidationSeverity.BLOCKER,
                "M1_TRUST_BLOCKER",
                blocker,
                module="M1",
            )

        # M2: execute the post-fabrication chemistry sequence and build the
        # stable media contract that M3 should consume.
        m2_orch = ModificationOrchestrator()
        microsphere = m2_orch.run(m1_contract, functionalization_steps)
        microsphere, m3_physical_qc_overrides, m3_physical_qc_diagnostics = (
            _apply_m3_physical_qc_to_microsphere(microsphere, calibration_store)
        )
        if m3_physical_qc_overrides:
            validation.add(
                ValidationSeverity.INFO,
                "M3_PHYSICAL_QC_APPLIED",
                "Measured compression/modulus QC was applied to the M3 mechanical state.",
                module="M3",
                recommendation=(
                    "Use compression data measured in the intended column buffer "
                    "and packing state before relying on pressure/compression limits."
                ),
            )
        fmc = build_functional_media_contract(microsphere)
        fmc_calibration_overrides: list[str] = []
        if calibration_store is not None:
            fmc, fmc_calibration_overrides = calibration_store.apply_to_fmc(fmc)

        # v0.5.0 (D5): apply ModelMode guard to the FMC manifest. Mirrors
        # the v0.4.0 / C2 M3 mode guard, finishing the architect-coherence
        # Deficit 2 cleanup. Reuses the centralised helper in method.py so
        # M2 and M3 share the same mode-conditional gating semantics.
        from dpsim.module3_performance.method import (
            _apply_mode_guard as _m3_mode_guard,
            is_method_calibrated,
        )

        _mode_value = getattr(getattr(params, "model_mode", None), "value", "")
        if fmc.model_manifest is not None and _mode_value:
            fmc.model_manifest = _m3_mode_guard(
                fmc.model_manifest,
                {"model_mode": _mode_value},
                has_calibration=is_method_calibrated(fmc),
            )

        # v0.2.0 (A5): re-run first-principles guardrails now that the FMC is
        # built. This catches G5 (ligand-accessibility floor) which the
        # pre-resolution pass cannot evaluate. G1 issues from the first pass
        # are already in `validation`; re-running G1 would duplicate them.
        fp_post_report = validate_recipe_first_principles(recipe, fmc=fmc)
        for issue in fp_post_report.issues:
            if issue.code.startswith("FP_G5_"):
                validation.add(
                    issue.severity,
                    issue.code,
                    issue.message,
                    module=issue.module,
                    recommendation=issue.recommendation,
                )
        m3_process_state, m3_process_state_overrides = (
            _m3_process_state_from_calibration_store(calibration_store)
        )
        # v0.4.0 (C7): inject polymer_family into the M3 process state so the
        # family-aware Protein A scope-of-claim guard in method.py can read it.
        # Compare by .value per CLAUDE.md cp1252/enum-reload quirk note.
        _family_value = getattr(getattr(props, "polymer_family", None), "value", "")
        if _family_value:
            m3_process_state["polymer_family"] = _family_value
        # v0.4.0 (C2): inject ModelMode so the M3 mode guard can fire.
        _mode_value = getattr(getattr(params, "model_mode", None), "value", "")
        if _mode_value:
            m3_process_state["model_mode"] = _mode_value
        m3_reference_dbc = _m3_reference_dbc_from_calibration_store(calibration_store)
        if fmc_calibration_overrides or m3_process_state_overrides:
            _annotate_fmc_m3_calibration(
                fmc,
                fmc_calibration_overrides=fmc_calibration_overrides,
                m3_process_state=m3_process_state,
                m3_process_state_overrides=m3_process_state_overrides,
            )
            validation.add(
                ValidationSeverity.INFO,
                "M3_CALIBRATION_APPLIED",
                (
                    "RunContext calibration entries were applied to the "
                    "M2-to-M3 media contract and/or M3 isotherm process state."
                ),
                module="M3",
                recommendation=(
                    "Confirm the calibration valid_domain covers the selected "
                    "pH, temperature, salt, residence time, and packed-bed state."
                ),
            )
        for violation in microsphere.validate():
            validation.add(
                ValidationSeverity.BLOCKER,
                "M2_SITE_BALANCE",
                violation,
                module="M2",
                recommendation="Repair ACS bookkeeping or chemistry ordering before using M2/M3 results.",
            )
        for step_result in microsphere.modification_history:
            manifest = step_result.model_manifest
            if manifest is None:
                continue
            for violation in manifest.diagnostics.get("conservation_violations", []):
                validation.add(
                    ValidationSeverity.BLOCKER,
                    "M2_SITE_BALANCE",
                    str(violation),
                    module="M2",
                    recommendation="Inspect the offending modification step and reagent stoichiometry.",
                )
        for violation in fmc.validate_units():
            validation.add(
                ValidationSeverity.BLOCKER,
                "M2_CONTRACT_UNITS",
                violation,
                module="M2",
                recommendation="Inspect FunctionalMediaContract before M3 consumes capacity/mechanics values.",
            )
        _validate_m2_assay_acceptance(fmc, validation)

        graph.add_node(
            ResultNode(
                node_id="M2",
                stage="M2_functionalization",
                label="Protein A functionalization",
                payload=microsphere,
                manifest=microsphere.model_manifest,
                diagnostics={
                    "n_steps": len(functionalization_steps),
                    "installed_ligand": fmc.installed_ligand,
                    "functional_ligand_density": fmc.functional_ligand_density,
                    "activity_retention": fmc.activity_retention,
                    "ligand_leaching_fraction": fmc.ligand_leaching_fraction,
                    "free_protein_wash_fraction": fmc.free_protein_wash_fraction,
                    "estimated_q_max": fmc.estimated_q_max,
                    "calibrations_applied": list(fmc_calibration_overrides),
                    "m3_physical_qc_overrides": list(m3_physical_qc_overrides),
                    "m3_process_state_calibrations": list(m3_process_state_overrides),
                    **carryover_diagnostics,
                },
                wet_lab_caveats=[
                    "M2 activation, coupling, quenching, and washing need residual reagent, free ligand, and retained-activity assays.",
                    "M1 oil and surfactant carryover can suppress activation/coupling or change nonspecific adsorption; residual assays should confirm carryover below the recipe target.",
                ],
            )
        )
        graph.add_node(
            ResultNode(
                node_id="FMC",
                stage="M2_to_M3_contract",
                label="Functional media contract",
                payload=fmc,
                manifest=fmc.model_manifest,
                diagnostics={
                    "ligand_type": fmc.ligand_type,
                    "m3_support_level": fmc.m3_support_level,
                    "q_max_confidence": fmc.q_max_confidence,
                    "estimated_q_max": fmc.estimated_q_max,
                    "activity_retention": fmc.activity_retention,
                    "ligand_leaching_fraction": fmc.ligand_leaching_fraction,
                    "free_protein_wash_fraction": fmc.free_protein_wash_fraction,
                    "calibrations_applied": list(fmc_calibration_overrides),
                    "m3_process_state": dict(m3_process_state),
                    "m3_process_state_calibrations": list(m3_process_state_overrides),
                    "m3_physical_qc_overrides": list(m3_physical_qc_overrides),
                    **m3_physical_qc_diagnostics,
                    **carryover_diagnostics,
                },
                wet_lab_caveats=[
                    "FunctionalMediaContract capacity is screening-grade unless q_max and binding activity are calibrated against the target analyte.",
                    "Measured ligand leaching and free-protein wash fractions should be reviewed before using the media in a column; high values imply capacity drift, fouling risk, and extractables risk.",
                ],
            )
        )
        graph.add_edge("M1", "M2", "M1ExportContract")
        graph.add_edge("M2", "FMC", "FunctionalMediaContract")

        residual_warning_set = set(fmc.residual_reagent_warnings)
        if fmc.warnings:
            for warning in fmc.warnings:
                if warning in residual_warning_set:
                    continue
                validation.add(
                    ValidationSeverity.WARNING,
                    "FMC_WARNING",
                    warning,
                    module="M2",
                )
        for warning in fmc.residual_reagent_warnings:
            validation.add(
                ValidationSeverity.WARNING,
                "M2_RESIDUAL_REAGENT",
                warning,
                module="M2",
                recommendation=(
                    "Add a validated wash assay or increase wash time/volume "
                    "before treating M3 performance as wet-lab ready."
                ),
            )

        dsd_variants: list[DSDMediaVariant] = []
        dsd_summary: DSDPropagationSummary | None = None
        if propagate_dsd:
            dsd_variants, dsd_summary = self._run_dsd_downstream_screen(
                params=params,
                props=props,
                trust=trust,
                base_result=m1_result,
                m1_contract=m1_contract,
                m1_orchestrator=m1_orch,
                functionalization_steps=functionalization_steps,
                column=column,
                flow_rate=resolved_inputs.m3_flow_rate,
                feed_concentration=resolved_inputs.m3_feed_concentration,
                feed_duration=resolved_inputs.m3_feed_duration,
                total_time=resolved_inputs.m3_total_time,
                n_z=resolved_inputs.m3_n_z,
                quantiles=dsd_quantiles,
                mode=dsd_mode,
                max_representatives=dsd_max_representatives,
                run_breakthrough_screen=dsd_run_breakthrough,
                calibration_store=calibration_store,
                m3_process_state=m3_process_state,
            )
            dsd_reference_diagnostics = _dsd_dbc_reference_diagnostics(
                dsd_summary,
                m3_reference_dbc,
            )
            graph.add_node(
                ResultNode(
                    node_id="DSD",
                    stage="M1_distribution_to_M3_screen",
                    label="DSD downstream propagation screen",
                    payload=dsd_summary,
                    manifest=_composite_manifest_from_m1(m1_result),
                    diagnostics={
                        "n_quantiles": dsd_summary.n_quantiles,
                        "q_max_weighted_mean": dsd_summary.q_max_weighted_mean_mol_m3,
                        "dbc_10_weighted_mean": dsd_summary.dbc_10_weighted_mean_mol_m3,
                        "dbc_10_weighted_p50": dsd_summary.dbc_10_weighted_p50_mol_m3,
                        "dbc_10_weighted_p95": dsd_summary.dbc_10_weighted_p95_mol_m3,
                        "breakthrough_simulated": dsd_summary.breakthrough_simulated,
                        "max_breakthrough_mass_balance_error": (
                            dsd_summary.max_breakthrough_mass_balance_error
                        ),
                        "pressure_drop_min_Pa": dsd_summary.pressure_drop_min_Pa,
                        "pressure_drop_weighted_p50_Pa": dsd_summary.pressure_drop_weighted_p50_Pa,
                        "pressure_drop_weighted_p95_Pa": dsd_summary.pressure_drop_weighted_p95_Pa,
                        "pressure_drop_max_Pa": dsd_summary.pressure_drop_max_Pa,
                        "bed_compression_weighted_p50": (
                            dsd_summary.bed_compression_weighted_p50_fraction
                        ),
                        "bed_compression_weighted_p95": (
                            dsd_summary.bed_compression_weighted_p95_fraction
                        ),
                        "max_bed_compression": dsd_summary.max_bed_compression_fraction,
                        "dsd_source": dsd_summary.dsd_source,
                        "quantile_selection": dsd_summary.quantile_selection,
                        "represented_mass_fraction": dsd_summary.represented_mass_fraction,
                        "n_dsd_bins": dsd_summary.n_dsd_bins,
                        "d10_m": dsd_summary.d10_m,
                        "d50_m": dsd_summary.d50_m,
                        "d90_m": dsd_summary.d90_m,
                        **dsd_reference_diagnostics,
                    },
                    wet_lab_caveats=[
                        "DSD propagation transfers M1 volume-weighted representatives into M2/M3; it does not replace measured size-resolved packing and breakthrough experiments.",
                    ],
                )
            )
            graph.add_edge("M1", "DSD", "M1 DSD quantile propagation")
            for warning in dsd_summary.warnings:
                validation.add(
                    ValidationSeverity.WARNING,
                    "DSD_DOWNSTREAM_SPREAD",
                    warning,
                    module="M1/M3",
                    recommendation=(
                        "Use DSD-resolved M3 method screening or classify/sieve "
                        "the microsphere batch before column packing."
                    ),
                )

        # M3: run the full method-level affinity operation. The load step uses
        # the inherited LRM breakthrough solver, while pack/equilibrate/wash/
        # elute steps add wet-lab operability and Protein A-specific diagnostics.
        m3_flow_rate = resolved_inputs.m3_flow_rate
        m3_column = _column_with_microsphere(column, microsphere)
        for warning in m3_column.validate_flow_rate(m3_flow_rate):
            severity = (
                ValidationSeverity.BLOCKER
                if warning.startswith("BLOCKER:")
                else ValidationSeverity.WARNING
            )
            validation.add(
                severity,
                "M3_FLOW_DOMAIN",
                warning.replace("BLOCKER: ", "").replace("WARNING: ", ""),
                module="M3",
                recommendation=(
                    "Reduce flow rate, increase bed porosity, use larger/stiffer "
                    "particles, or shorten the bed before treating DBC as wet-lab feasible."
                ),
            )

        m3_method = run_chromatography_method(
            column=m3_column,
            n_z=resolved_inputs.m3_n_z,
            fmc=fmc,
            method_steps=resolved_inputs.m3_method_steps,
            process_state=m3_process_state,
            max_pressure_Pa=resolved_inputs.max_pressure_drop_Pa,
            pump_pressure_limit_Pa=resolved_inputs.pump_pressure_limit_Pa,
        )
        for blocker in m3_method.operability.blockers:
            validation.add(
                ValidationSeverity.BLOCKER,
                "M3_OPERABILITY_LIMIT",
                blocker,
                module="M3",
                recommendation=(
                    "Revise column geometry, packing quality, particle stiffness, "
                    "or method flow before running this chromatography operation."
                ),
            )
        for warning in m3_method.operability.warnings:
            validation.add(
                ValidationSeverity.WARNING,
                "M3_OPERABILITY_LIMIT",
                warning,
                module="M3",
                recommendation=(
                    "Confirm pressure-flow, residence-time, and column efficiency "
                    "experimentally before treating the M3 result as quantitative."
                ),
            )
        for warning in m3_method.protein_a.warnings:
            validation.add(
                ValidationSeverity.WARNING,
                "M3_PROTEIN_A_METHOD",
                warning,
                module="M3",
                recommendation=(
                    "Adjust Protein A method pH, residence time, cleaning, or "
                    "ligand chemistry and calibrate against cycling/breakthrough data."
                ),
            )
        for warning in m3_method.column_efficiency.warnings:
            validation.add(
                ValidationSeverity.WARNING,
                "M3_COLUMN_EFFICIENCY",
                warning,
                module="M3",
                recommendation=(
                    "Run tracer-pulse plate count, asymmetry, and HETP tests on "
                    "the packed bed before relying on peak-shape predictions."
                ),
            )
        for warning in m3_method.impurity_clearance.warnings:
            validation.add(
                ValidationSeverity.WARNING,
                "M3_IMPURITY_CLEARANCE",
                warning,
                module="M3",
                recommendation=(
                    "Measure HCP, DNA, aggregate, and leached ligand in wash "
                    "and elution fractions for the target feedstock."
                ),
            )

        # Keep the legacy breakthrough field as the dynamic-load result used by
        # existing callers. A missing LOAD step remains a recipe issue, but a
        # fallback breakthrough is generated so reports and CLI output stay
        # structurally complete during migration.
        m3_result = m3_method.load_breakthrough
        if m3_result is None:
            validation.add(
                ValidationSeverity.BLOCKER,
                "M3_METHOD_LOAD_MISSING",
                "M3 method did not produce a load-step breakthrough result.",
                module="M3",
                recommendation="Add a LOAD method step with feed concentration, flow rate, and duration.",
            )
            m3_result = run_breakthrough(
                column=m3_column,
                C_feed=resolved_inputs.m3_feed_concentration,
                flow_rate=m3_flow_rate,
                feed_duration=resolved_inputs.m3_feed_duration,
                total_time=resolved_inputs.m3_total_time,
                n_z=resolved_inputs.m3_n_z,
                fmc=fmc,
                process_state=m3_process_state,
                log_flow_warnings=False,
            )
        m3_pressure_diagnostics = _m3_pressure_flow_diagnostics(
            calibration_store,
            m3_method,
        )
        _add_m3_pressure_flow_validation(
            validation=validation,
            diagnostics=m3_pressure_diagnostics,
        )
        m3_domain_diagnostics = _apply_m3_calibration_domain_gates(
            calibration_store=calibration_store,
            method=m3_method,
            fmc=fmc,
            validation=validation,
        )
        _enforce_m3_media_evidence_cap(
            method=m3_method,
            fmc=fmc,
            validation=validation,
        )
        m3_reference_diagnostics = _m3_dbc_reference_diagnostics(
            m3_result,
            m3_reference_dbc,
        )
        _add_m3_dbc_reference_validation(
            validation=validation,
            diagnostics=m3_reference_diagnostics,
        )
        m3_uncertainty_diagnostics = _m3_calibration_posterior_diagnostics(
            calibration_store=calibration_store,
            m3_result=m3_result,
            method=m3_method,
            fmc=fmc,
        )
        _add_m3_calibration_uncertainty_validation(
            validation=validation,
            diagnostics=m3_uncertainty_diagnostics,
        )
        _annotate_m3_calibration_uncertainty(
            method=m3_method,
            diagnostics=m3_uncertainty_diagnostics,
        )
        graph.add_node(
            ResultNode(
                node_id="M3",
                stage="M3_performance",
                label="Protein A chromatography method",
                payload=m3_method,
                manifest=m3_method.model_manifest,
                diagnostics={
                    "dbc_10pct": float(m3_result.dbc_10pct),
                    "pressure_drop_Pa": float(m3_result.pressure_drop),
                    "mass_balance_error": float(m3_result.mass_balance_error),
                    "method_steps": [
                        step.operation.value for step in m3_method.method_steps
                    ],
                    "method_step_names": list(m3_method.method_step_names),
                    "method_pressure_drop_Pa": float(
                        m3_method.operability.pressure_drop_Pa
                    ),
                    "method_bed_compression_fraction": float(
                        m3_method.operability.bed_compression_fraction
                    ),
                    "particle_reynolds": float(m3_method.operability.particle_reynolds),
                    "axial_peclet": float(m3_method.operability.axial_peclet),
                    "flow_maldistribution_risk": (
                        m3_method.operability.maldistribution_risk
                    ),
                    "load_residence_time_s": float(
                        m3_method.operability.residence_time_s
                    ),
                    "protein_a_q_max_mol_m3": float(
                        m3_method.protein_a.q_max_mol_m3
                    ),
                    "protein_a_q_equilibrium_load_mol_m3": float(
                        m3_method.protein_a.q_equilibrium_load_mol_m3
                    ),
                    "protein_a_load_pH": float(m3_method.protein_a.load_pH),
                    "protein_a_elution_pH": float(m3_method.protein_a.elution_pH),
                    "protein_a_mass_transfer_resistance_s": float(
                        m3_method.protein_a.mass_transfer_resistance_s
                    ),
                    "protein_a_ligand_accessibility_factor": float(
                        m3_method.protein_a.ligand_accessibility_factor
                    ),
                    "protein_a_alkaline_degradation_fraction_per_cycle": float(
                        m3_method.protein_a.alkaline_degradation_fraction_per_cycle
                    ),
                    "protein_a_cycle_lifetime_to_70pct": float(
                        m3_method.protein_a.cycle_lifetime_to_70pct_capacity
                    ),
                    "protein_a_ligand_leaching_fraction_per_cycle": float(
                        m3_method.protein_a.ligand_leaching_fraction_per_cycle
                    ),
                    "protein_a_leaching_risk": m3_method.protein_a.leaching_risk,
                    "protein_a_predicted_elution_recovery_fraction": float(
                        m3_method.protein_a.predicted_elution_recovery_fraction
                    ),
                    "loaded_elution_recovery_fraction": (
                        0.0 if m3_method.loaded_elution is None
                        else float(m3_method.loaded_elution.recovery_fraction)
                    ),
                    "loaded_elution_peak_time_s": (
                        0.0 if m3_method.loaded_elution is None
                        else float(m3_method.loaded_elution.peak_time_s)
                    ),
                    "loaded_elution_mass_balance_error": (
                        0.0 if m3_method.loaded_elution is None
                        else float(m3_method.loaded_elution.mass_balance_error)
                    ),
                    "column_theoretical_plates": float(
                        m3_method.column_efficiency.theoretical_plates
                    ),
                    "column_hetp_m": float(m3_method.column_efficiency.hetp_m),
                    "column_asymmetry_factor": float(
                        m3_method.column_efficiency.asymmetry_factor
                    ),
                    "column_tailing_factor": float(
                        m3_method.column_efficiency.tailing_factor
                    ),
                    "impurity_wash_column_volumes": float(
                        m3_method.impurity_clearance.wash_column_volumes
                    ),
                    "impurity_total_coelution_fraction_of_igg": float(
                        m3_method.impurity_clearance.total_coelution_fraction_of_igg
                    ),
                    "impurity_clearance_risk": m3_method.impurity_clearance.risk,
                    "m3_process_state": dict(m3_process_state),
                    "m3_process_state_calibrations": list(m3_process_state_overrides),
                    "m3_physical_qc_overrides": list(m3_physical_qc_overrides),
                    "ligand_leaching_fraction": fmc.ligand_leaching_fraction,
                    "free_protein_wash_fraction": fmc.free_protein_wash_fraction,
                    **m3_physical_qc_diagnostics,
                    **m3_pressure_diagnostics,
                    **m3_domain_diagnostics,
                    **m3_reference_diagnostics,
                    **m3_uncertainty_diagnostics,
                    **carryover_diagnostics,
                },
                wet_lab_caveats=[
                    "M3 breakthrough and DBC predictions are screening outputs until pressure-flow and breakthrough curves are measured on packed media.",
                    "Residual oil/surfactant carried from M1 can alter wet packing, fouling, nonspecific binding, and detector baseline; treat M3 results as screening until residuals are assayed.",
                    "M2 ligand leaching or residual free protein in wash fractions can bias breakthrough capacity and column fouling; M3 output assumes these are inside acceptance limits.",
                    *m3_method.wet_lab_caveats,
                    *m3_method.protein_a.wet_lab_caveats,
                ],
            )
        )
        graph.add_edge("FMC", "M3", "M3 consumes calibrated/estimated media contract")
        if dsd_summary is not None:
            graph.add_edge("DSD", "M3", "Hydraulic/capacity sensitivity screen")

        if m3_result.pressure_drop > resolved_inputs.pump_pressure_limit_Pa:
            validation.add(
                ValidationSeverity.BLOCKER,
                "M3_PRESSURE_LIMIT",
                (
                    f"M3 pressure drop {m3_result.pressure_drop:.0f} Pa exceeds "
                    f"pump limit {resolved_inputs.pump_pressure_limit_Pa:.0f} Pa."
                ),
                module="M3",
                recommendation="Reduce flow, shorten bed, use larger particles, or select a higher-pressure-rated system.",
            )
        elif m3_result.pressure_drop > resolved_inputs.max_pressure_drop_Pa:
            validation.add(
                ValidationSeverity.WARNING,
                "M3_PRESSURE_TARGET",
                (
                    f"M3 pressure drop {m3_result.pressure_drop:.0f} Pa exceeds "
                    f"recipe target {resolved_inputs.max_pressure_drop_Pa:.0f} Pa."
                ),
                module="M3",
                recommendation="Treat DBC as outside the intended wet-lab operating envelope.",
            )
        compression = m3_column.bed_compression_fraction(m3_result.pressure_drop)
        if compression > 0.50:
            validation.add(
                ValidationSeverity.BLOCKER,
                "M3_COMPRESSION_LIMIT",
                f"M3 bed compression {compression:.1%} exceeds 50%.",
                module="M3",
                recommendation="Use stiffer or larger particles before packing this media under the selected flow.",
            )

        if m3_result.mass_balance_error > 0.05:
            validation.add(
                ValidationSeverity.BLOCKER,
                "M3_MASS_BALANCE",
                f"M3 mass balance error is {m3_result.mass_balance_error:.1%}.",
                module="M3",
                recommendation="Increase M3 spatial resolution or tighten solver tolerances.",
            )
        elif m3_result.mass_balance_error > 0.02:
            validation.add(
                ValidationSeverity.WARNING,
                "M3_MASS_BALANCE",
                f"M3 mass balance error is {m3_result.mass_balance_error:.1%}.",
                module="M3",
            )

        validation.extend(
            validate_model_manifest_domains(
                _collect_lifecycle_manifests(m1_result, microsphere, graph),
                module="M1/M2/M3",
            )
        )

        notes.append(
            "Protein A capacity is ranking-only unless calibrated with target-specific "
            "static binding or breakthrough data."
        )

        # v0.5.0 (D3): build the ProcessDossier as the default lifecycle
        # output. Closes architect-coherence-audit D6 (LOW). The dossier is
        # built from the M1 FullResult plus calibration entries; downstream
        # consumers (UI dossier export, regulated batch records) can
        # serialize it directly via .to_json_dict() without rebuilding.
        process_dossier: Any = None
        try:
            from dpsim.process_dossier import ProcessDossier as _ProcessDossier

            process_dossier = _ProcessDossier.from_run(
                m1_result,
                calibration_store=calibration_store,
                target_profile=recipe.target,
                notes=" | ".join(notes) if notes else "",
            )
        except Exception as _dossier_exc:
            validation.add(
                ValidationSeverity.WARNING,
                "PROCESS_DOSSIER_UNAVAILABLE",
                (
                    f"ProcessDossier could not be built: {_dossier_exc}. "
                    "Lifecycle continues; downstream dossier consumers will "
                    "see ``process_dossier=None``."
                ),
                module="lifecycle",
            )

        return DownstreamLifecycleResult(
            recipe=recipe,
            graph=graph,
            validation=validation,
            m1_result=m1_result,
            m1_contract=m1_contract,
            m2_microsphere=microsphere,
            functional_media_contract=fmc,
            m3_method=m3_method,
            m3_breakthrough=m3_result,
            dsd_variants=dsd_variants,
            dsd_summary=dsd_summary,
            performance_recipe=performance_recipe,
            process_dossier=process_dossier,
            resolved_parameters=resolved_inputs.resolved_parameters,
            notes=notes,
        )

    def _run_dsd_downstream_screen(
        self,
        params: SimulationParameters,
        props,
        trust,
        base_result: FullResult,
        m1_contract: M1ExportContract,
        m1_orchestrator: PipelineOrchestrator,
        functionalization_steps: list[ModificationStep],
        column: ColumnGeometry,
        flow_rate: float,
        feed_concentration: float,
        feed_duration: float,
        total_time: float,
        n_z: int,
        quantiles: tuple[float, ...],
        mode: str,
        max_representatives: int,
        run_breakthrough_screen: bool,
        calibration_store,
        m3_process_state: dict[str, float],
    ) -> tuple[list[DSDMediaVariant], DSDPropagationSummary]:
        """Propagate DSD representatives through M2 and M3 screens."""
        from dpsim.pipeline.batch_variability import (
            _representative_radii_from_dsd,
            _run_l2_l4_at_R,
        )

        mode = mode.lower().strip()
        if not quantiles and mode == "representative":
            raise ValueError("At least one DSD quantile is required.")
        if mode in {"representative", "adaptive"} and max_representatives <= 0:
            raise ValueError("dsd_max_representatives must be positive.")
        if mode not in {"representative", "adaptive", "bin_resolved"}:
            raise ValueError(
                "dsd_mode must be 'representative', 'adaptive', or "
                "'bin_resolved' (v0.4.0 / C5)."
            )
        quantiles = tuple(sorted(set(quantiles)))
        dsd_payload = getattr(m1_contract, "bead_size_distribution", None)
        representative_rows: list[dict[str, float | str]]
        quantile_selection = "representative"
        if dsd_payload is not None and not dsd_payload.validate():
            representative_rows, quantile_selection = _dsd_representative_rows(
                dsd_payload,
                quantiles=quantiles,
                mode=mode,
                max_representatives=max_representatives,
            )
        else:
            radii, mass_fractions = _representative_radii_from_dsd(base_result, quantiles)
            representative_rows = [
                {
                    "quantile": float(q),
                    "diameter_m": float(2.0 * radius),
                    "radius_m": float(radius),
                    "mass_fraction": float(mass_fraction),
                    "representative_source": "legacy_quantile",
                }
                for q, radius, mass_fraction in zip(quantiles, radii, mass_fractions)
            ]
            quantile_selection = "legacy_quantile"

        variants: list[DSDMediaVariant] = []
        m2_orch = ModificationOrchestrator()
        for row in representative_rows:
            quantile = float(row["quantile"])
            radius = float(row["radius_m"])
            mass_fraction = float(row["mass_fraction"])
            q_result = _run_l2_l4_at_R(
                m1_orchestrator,
                params,
                self.db,
                base_result,
                float(radius),
                None,
                "genipin",
                "empirical",
            )
            q_contract = export_for_module2(q_result, trust, props=props)
            q_contract = replace(
                q_contract,
                bead_radius=float(radius),
                bead_d50=float(2.0 * radius),
                bead_d32=float(2.0 * radius),
            )
            q_microsphere = m2_orch.run(q_contract, functionalization_steps)
            q_microsphere, _, _ = _apply_m3_physical_qc_to_microsphere(
                q_microsphere,
                calibration_store,
            )
            q_fmc = build_functional_media_contract(q_microsphere)
            if calibration_store is not None:
                q_fmc, _ = calibration_store.apply_to_fmc(q_fmc)
            q_column = _column_with_microsphere(column, q_microsphere)
            pressure_drop = q_column.pressure_drop(flow_rate)
            compression = q_column.bed_compression_fraction(pressure_drop)
            breakthrough = None
            if run_breakthrough_screen:
                breakthrough = run_breakthrough(
                    column=q_column,
                    C_feed=feed_concentration,
                    flow_rate=flow_rate,
                    feed_duration=feed_duration,
                    total_time=total_time,
                    n_z=n_z,
                    fmc=q_fmc,
                    process_state=m3_process_state,
                    log_flow_warnings=False,
                )
            variants.append(
                DSDMediaVariant(
                    quantile=float(quantile),
                    mass_fraction=float(mass_fraction),
                    bead_diameter_m=q_contract.bead_d50,
                    pore_size_m=q_contract.pore_size_mean,
                    porosity=q_contract.porosity,
                    G_DN_Pa=q_contract.G_DN,
                    E_star_Pa=q_contract.E_star,
                    estimated_q_max_mol_m3=q_fmc.estimated_q_max,
                    pressure_drop_Pa=pressure_drop,
                    bed_compression_fraction=compression,
                    representative_source=str(row["representative_source"]),
                    breakthrough_simulated=breakthrough is not None,
                    dbc_5pct_mol_m3=(
                        0.0 if breakthrough is None else float(breakthrough.dbc_5pct)
                    ),
                    dbc_10pct_mol_m3=(
                        0.0 if breakthrough is None else float(breakthrough.dbc_10pct)
                    ),
                    dbc_50pct_mol_m3=(
                        0.0 if breakthrough is None else float(breakthrough.dbc_50pct)
                    ),
                    breakthrough_mass_balance_error=(
                        0.0 if breakthrough is None
                        else float(breakthrough.mass_balance_error)
                    ),
                    residual_reagent_concentrations=dict(
                        q_fmc.residual_reagent_concentrations
                    ),
                    residual_warnings=list(q_fmc.residual_reagent_warnings),
                )
            )

        summary = _summarize_dsd_variants(variants)
        summary.quantile_selection = quantile_selection
        if dsd_payload is not None:
            summary.dsd_source = dsd_payload.source
            summary.n_dsd_bins = len(dsd_payload.diameter_bins_m)
            summary.d10_m = dsd_payload.d10_m
            summary.d50_m = dsd_payload.d50_m
            summary.d90_m = dsd_payload.d90_m
        return variants, summary


def _dsd_representative_rows(
    dsd_payload,
    *,
    quantiles: tuple[float, ...],
    mode: str,
    max_representatives: int,
) -> tuple[list[dict[str, float | str]], str]:
    """Select DSD rows for downstream M2/M3 propagation.

    ``representative`` preserves the historical user-selected quantiles.
    ``adaptive`` uses every non-zero DSD bin when the distribution is small
    enough; otherwise it collapses the distribution to evenly spaced
    volume-probability representatives. This gives a bounded-cost path from
    d50/d90-style screening toward true DSD-resolved packed-bed risk.
    ``bin_resolved`` (v0.4.0 / C5) always returns every non-zero bin with no
    downsampling — closes architect-coherence-audit Deficit 3 by removing
    the 3-quantile collapse on the lifecycle orchestration path. Bin count
    is the M1 DSD payload's volume_fraction length (typically 10-30).
    """

    if mode == "representative":
        rows = dsd_payload.quantile_table(list(quantiles))
        for row in rows:
            row["representative_source"] = "requested_quantile"
        return rows, "representative"

    if mode == "bin_resolved":
        bin_rows = _dsd_distribution_bin_rows(dsd_payload)
        return bin_rows, f"bin_resolved_{len(bin_rows)}_bins"

    bin_rows = _dsd_distribution_bin_rows(dsd_payload)
    if len(bin_rows) <= max_representatives:
        return bin_rows, "distribution_bins"

    n_rows = max(1, int(max_representatives))
    adaptive_quantiles = tuple((i + 0.5) / n_rows for i in range(n_rows))
    rows = dsd_payload.quantile_table(list(adaptive_quantiles))
    for row in rows:
        row["representative_source"] = "adaptive_quantile"
    return rows, f"adaptive_quantiles_{n_rows}_of_{len(bin_rows)}_bins"


def _dsd_distribution_bin_rows(dsd_payload) -> list[dict[str, float | str]]:
    """Return one representative per non-zero DSD volume-fraction bin."""

    diameters = [float(x) for x in dsd_payload.diameter_bins_m]
    weights = [max(0.0, float(x)) for x in dsd_payload.volume_fraction]
    rows: list[dict[str, float | str]] = []
    cdf_left = 0.0
    for diameter, weight in zip(diameters, weights):
        if weight <= 1e-12:
            cdf_left += weight
            continue
        q_mid = min(0.999999999, max(1e-12, cdf_left + 0.5 * weight))
        rows.append(
            {
                "quantile": float(q_mid),
                "diameter_m": float(diameter),
                "radius_m": float(0.5 * diameter),
                "mass_fraction": float(weight),
                "representative_source": "distribution_bin",
            }
        )
        cdf_left += weight
    if rows:
        total = sum(float(row["mass_fraction"]) for row in rows)
        if total > 0.0:
            for row in rows:
                row["mass_fraction"] = float(row["mass_fraction"]) / total
    return rows


def _composite_manifest_from_m1(result: FullResult) -> ModelManifest:
    """Build a single node manifest from a legacy FullResult RunReport."""
    rr = getattr(result, "run_report", None)
    if rr is None:
        return ModelManifest(
            model_name="M1.legacy_pipeline",
            evidence_tier=ModelEvidenceTier.SEMI_QUANTITATIVE,
            assumptions=["Legacy M1 result did not provide RunReport."],
        )
    return ModelManifest(
        model_name="M1.fabrication.composite",
        evidence_tier=rr.compute_min_tier(),
        assumptions=[
            "Composite M1 node inherits weakest tier from L1/L2/L3/L4 run report."
        ],
        diagnostics=dict(rr.diagnostics),
    )


def _collect_lifecycle_manifests(
    m1_result: FullResult,
    microsphere: FunctionalMicrosphere,
    graph: ResultGraph,
) -> list[ModelManifest]:
    """Collect model manifests from all lifecycle layers for domain gates."""

    manifests: list[ModelManifest] = []
    rr = getattr(m1_result, "run_report", None)
    if rr is not None:
        manifests.extend(rr.model_graph)
    for step_result in microsphere.modification_history:
        if step_result.model_manifest is not None:
            manifests.append(step_result.model_manifest)
    manifests.extend(graph.model_manifests())
    return manifests


def _column_with_microsphere(
    column: ColumnGeometry,
    microsphere: FunctionalMicrosphere,
) -> ColumnGeometry:
    """Return the M3 column geometry after applying M1/M2 media properties."""
    m1 = microsphere.m1_contract
    return ColumnGeometry(
        diameter=column.diameter,
        bed_height=column.bed_height,
        particle_diameter=m1.bead_d50,
        bed_porosity=column.bed_porosity,
        particle_porosity=m1.porosity,
        G_DN=microsphere.G_DN_updated or m1.G_DN,
        E_star=microsphere.E_star_updated or m1.E_star,
    )


def _apply_m1_physical_qc_to_contract(
    m1_contract: M1ExportContract,
    calibration_store,
) -> tuple[M1ExportContract, list[str], dict[str, float | str]]:
    """Apply measured M1 lot-state QC values to the M1 handoff contract.

    Only direct state replacements are applied here. Pore size and porosity
    are measured properties of the bead lot and directly affect M2 accessible
    surface estimates. Swelling ratio and bulk modulus remain diagnostics until
    a calibrated mapping to contract fields is available.
    """

    if calibration_store is None:
        return m1_contract, [], {}
    field_map = {
        "measured_pore_size_mean": ("pore_size_mean", "m"),
        "measured_porosity": ("porosity", "1"),
    }
    updates: dict[str, float] = {}
    overrides: list[str] = []
    diagnostics: dict[str, float | str] = {}
    for entry in getattr(calibration_store, "entries", []):
        if entry.target_module not in ("", "M1"):
            continue
        value = float(entry.measured_value)
        if entry.parameter_name in field_map:
            field_name, unit = field_map[entry.parameter_name]
            old_value = float(getattr(m1_contract, field_name))
            updates[field_name] = value
            diagnostics[f"{field_name}_predicted_before_physical_qc"] = old_value
            diagnostics[f"{field_name}_physical_qc_value"] = value
            diagnostics[f"{field_name}_physical_qc_units"] = unit
            diagnostics[f"{field_name}_physical_qc_relative_shift"] = (
                _relative_error(value, old_value)
            )
            overrides.append(
                f"{field_name} {old_value:.4g} -> {value:.4g} "
                f"({entry.units}, {entry.confidence}, {entry.source_reference})"
            )
        elif entry.parameter_name in {
            "measured_swelling_ratio",
            "measured_bulk_modulus",
        }:
            diagnostics[entry.parameter_name] = value
    if updates:
        m1_contract = replace(m1_contract, **updates)
    return m1_contract, overrides, diagnostics


def _apply_m3_physical_qc_to_microsphere(
    microsphere: FunctionalMicrosphere,
    calibration_store,
) -> tuple[FunctionalMicrosphere, list[str], dict[str, float | str]]:
    """Apply measured packed-bed compression modulus to M3 mechanics."""

    if calibration_store is None:
        return microsphere, [], {}
    overrides: list[str] = []
    diagnostics: dict[str, float | str] = {}
    updated = microsphere
    for entry in getattr(calibration_store, "entries", []):
        if entry.target_module not in ("", "M3"):
            continue
        if entry.parameter_name != "measured_compression_modulus":
            continue
        value = float(entry.measured_value)
        old_value = float(microsphere.E_star_updated or microsphere.m1_contract.E_star)
        updated = replace(updated, E_star_updated=value)
        diagnostics["E_star_predicted_before_physical_qc"] = old_value
        diagnostics["E_star_physical_qc_value"] = value
        diagnostics["E_star_physical_qc_relative_shift"] = _relative_error(
            value,
            old_value,
        )
        overrides.append(
            f"E_star {old_value:.4g} -> {value:.4g} "
            f"({entry.units}, {entry.confidence}, {entry.source_reference})"
        )
    return updated, overrides, diagnostics


def _validate_m2_assay_acceptance(
    fmc: FunctionalMediaContract,
    validation: ValidationReport,
) -> None:
    """Apply conservative M2 wet-lab assay acceptance gates."""

    if fmc.ligand_type != "none" and fmc.functional_ligand_density <= 0.0:
        validation.add(
            ValidationSeverity.WARNING,
            "M2_LIGAND_DENSITY_MISSING",
            "Functional media has a ligand type but no functional ligand density.",
            module="M2",
            recommendation="Add a ligand-density assay or calibrate qmax directly before quantitative M3 use.",
        )
    if 0.0 < fmc.activity_retention < 0.30:
        validation.add(
            ValidationSeverity.WARNING,
            "M2_ACTIVITY_RETENTION_LOW",
            f"M2 activity retention is {fmc.activity_retention:.1%}.",
            module="M2",
            recommendation="Adjust coupling pH/temperature/time or use an orientation-preserving chemistry.",
        )
    _fraction_gate(
        validation,
        value=fmc.ligand_leaching_fraction,
        code="M2_LIGAND_LEACHING",
        label="ligand leaching",
        warning_limit=0.01,
        blocker_limit=0.05,
        recommendation=(
            "Improve blocking, washing, storage buffer, or coupling chemistry; "
            "confirm leaching under intended storage/CIP/contact-time conditions."
        ),
    )
    _fraction_gate(
        validation,
        value=fmc.free_protein_wash_fraction,
        code="M2_FREE_PROTEIN_WASH",
        label="free protein in wash fractions",
        warning_limit=0.01,
        blocker_limit=0.05,
        recommendation=(
            "Increase post-coupling washing or reduce coupling excess before "
            "using the media in M3 column operation."
        ),
    )


def _fraction_gate(
    validation: ValidationReport,
    *,
    value: float,
    code: str,
    label: str,
    warning_limit: float,
    blocker_limit: float,
    recommendation: str,
) -> None:
    """Add warning/blocker for measured M2 assay fractions."""

    if value <= warning_limit:
        return
    severity = ValidationSeverity.BLOCKER if value > blocker_limit else ValidationSeverity.WARNING
    validation.add(
        severity,
        code,
        f"Measured {label} is {value:.1%}; warning limit is {warning_limit:.1%} and blocker limit is {blocker_limit:.1%}.",
        module="M2",
        recommendation=recommendation,
    )


def _add_m1_physical_qc_shift_validation(
    *,
    validation: ValidationReport,
    diagnostics: dict[str, float | str],
) -> None:
    """Warn when measured physical-QC values strongly shift predictions."""

    labels = {
        "pore_size_mean": "M1 pore size",
        "porosity": "M1 porosity",
    }
    for field_name, label in labels.items():
        key = f"{field_name}_physical_qc_relative_shift"
        error = diagnostics.get(key)
        if not isinstance(error, float) or abs(error) <= 0.30:
            continue
        validation.add(
            ValidationSeverity.WARNING,
            "M1_PHYSICAL_QC_SHIFT",
            (
                f"Measured {label} shifts the simulated handoff value by "
                f"{error:.1%}."
            ),
            module="M1",
            recommendation=(
                "Treat this run as measured-lot-conditioned and recalibrate "
                "the upstream M1 solver before using the uncorrected prediction "
                "for process design."
            ),
        )


def _m3_process_state_from_calibration_store(
    calibration_store,
) -> tuple[dict[str, float], list[str]]:
    """Extract M3 isotherm process-state overrides from calibration entries."""

    if calibration_store is None:
        return {}, []
    parameter_map = {
        "K_L": "K_affinity",
        "K_affinity": "K_affinity",
        "K_0": "K_0",
        "m_salt": "m_salt",
        "K_eq": "K_eq",
        "z": "z",
        "sigma": "sigma",
        "K_competitor": "K_competitor",
        "protein_a_alkaline_rate_s_at_pH13": "protein_a_alkaline_rate_s_at_pH13",
        "protein_a_alkaline_degradation_rate_s": "protein_a_alkaline_degradation_rate_s",
        "protein_a_leaching_fraction_per_cycle": "protein_a_leaching_fraction_per_cycle",
        "protein_a_cycle_loss_fraction": "protein_a_cycle_loss_fraction",
        "protein_a_cycle_lifetime_to_70pct": "protein_a_cycle_lifetime_to_70pct",
        "protein_a_pH_transition": "protein_a_pH_transition",
        "protein_a_pH_steepness": "protein_a_pH_steepness",
        "protein_a_elution_residual_activity": "protein_a_elution_residual_activity",
    }
    state: dict[str, float] = {}
    overrides: list[str] = []
    for entry in getattr(calibration_store, "entries", []):
        if entry.target_module not in ("", "M3"):
            continue
        state_name = parameter_map.get(entry.parameter_name)
        if state_name is None:
            continue
        value = float(entry.measured_value)
        if value <= 0.0:
            continue
        state[state_name] = value
        overrides.append(
            f"{state_name}={value:.4g} ({entry.units}, "
            f"{entry.confidence}, {entry.source_reference})"
        )
    return state, overrides


def _m3_reference_dbc_from_calibration_store(
    calibration_store,
) -> dict[str, float]:
    """Return measured DBC reference values from M3 calibration entries."""

    if calibration_store is None:
        return {}
    supported = {
        "dbc_5_reference",
        "dbc_10_reference",
        "dbc_50_reference",
    }
    grouped: dict[str, list[float]] = {}
    for entry in getattr(calibration_store, "entries", []):
        if entry.target_module not in ("", "M3"):
            continue
        if entry.parameter_name not in supported:
            continue
        value = float(entry.measured_value)
        if value >= 0.0:
            grouped.setdefault(entry.parameter_name, []).append(value)
    return {
        key: sum(values) / len(values)
        for key, values in grouped.items()
        if values
    }


def _m3_pressure_flow_diagnostics(
    calibration_store,
    method: ChromatographyMethodResult,
) -> dict[str, float]:
    """Compare simulated M3 pressure drop against pressure-flow calibration."""

    if calibration_store is None:
        return {}
    entries = [
        entry for entry in getattr(calibration_store, "entries", [])
        if entry.target_module in ("", "M3")
        and entry.parameter_name == "pressure_flow_slope_Pa_per_m3_s"
        and float(entry.measured_value) > 0.0
    ]
    if not entries:
        return {}
    weights = [
        1.0 / max(float(entry.posterior_uncertainty), 1.0e-30) ** 2
        if float(entry.posterior_uncertainty) > 0.0
        else 1.0
        for entry in entries
    ]
    slope = sum(w * float(entry.measured_value) for w, entry in zip(weights, entries)) / sum(weights)
    step = max(
        method.step_results,
        key=lambda item: float(item.pressure_drop_Pa),
        default=None,
    )
    if step is None:
        return {}
    reference_pressure = slope * float(step.flow_rate_m3_s)
    simulated_pressure = float(step.pressure_drop_Pa)
    return {
        "pressure_flow_slope_calibrated_Pa_per_m3_s": float(slope),
        "pressure_flow_reference_pressure_Pa": float(reference_pressure),
        "pressure_flow_simulated_pressure_Pa": simulated_pressure,
        "pressure_flow_relative_error": _relative_error(
            simulated_pressure,
            reference_pressure,
        ),
    }


def _add_m3_pressure_flow_validation(
    *,
    validation: ValidationReport,
    diagnostics: dict[str, float],
) -> None:
    """Warn when simulated pressure-flow behavior disagrees with assay slope."""

    error = diagnostics.get("pressure_flow_relative_error")
    if error is None or not math.isfinite(error) or abs(error) <= 0.30:
        return
    validation.add(
        ValidationSeverity.WARNING,
        "M3_PRESSURE_FLOW_REFERENCE_MISMATCH",
        f"Simulated packed-bed pressure differs from pressure-flow calibration by {error:.1%}.",
        module="M3",
        recommendation=(
            "Recheck bed porosity, particle diameter distribution, compression "
            "state, viscosity, and packing quality before trusting operability margins."
        ),
    )


def _m3_calibration_posterior_diagnostics(
    *,
    calibration_store,
    m3_result: BreakthroughResult,
    method: ChromatographyMethodResult,
    fmc: FunctionalMediaContract,
) -> dict[str, float | int | str | list[str]]:
    """Propagate calibration posterior widths into M3 screening intervals.

    This is a first-order delta-method layer. It deliberately stays
    conservative: it does not claim a full stochastic chromatography solve, but
    it gives downstream users a visible interval when the calibration store
    carries parameter posteriors.
    """

    if calibration_store is None:
        return {}
    entries = [
        entry for entry in getattr(calibration_store, "entries", [])
        if entry.target_module in ("", "M2", "M3")
        and float(getattr(entry, "posterior_uncertainty", 0.0) or 0.0) > 0.0
        and abs(float(entry.measured_value)) > 0.0
    ]
    if not entries:
        return {}

    qmax = _posterior_summary_for_parameters(entries, {"estimated_q_max", "q_max"})
    density = _posterior_summary_for_parameters(entries, {"functional_ligand_density"})
    activity = _posterior_summary_for_parameters(entries, {"activity_retention"})
    affinity = _posterior_summary_for_parameters(entries, {"K_affinity", "K_L"})
    pressure_slope = _posterior_summary_for_parameters(
        entries,
        {"pressure_flow_slope_Pa_per_m3_s"},
    )
    dbc_10_reference = _posterior_summary_for_parameters(entries, {"dbc_10_reference"})

    diagnostics: dict[str, float | int | str | list[str]] = {
        "calibration_posterior_count": len(entries),
        "calibration_posterior_parameters": sorted(
            {str(entry.parameter_name) for entry in entries}
        ),
        "calibration_uncertainty_model": "first_order_delta_method",
    }
    relative_values: list[float] = []

    capacity_terms: list[float] = []
    if qmax is not None:
        diagnostics["estimated_q_max_calibration_sigma_mol_m3"] = qmax["sigma"]
        diagnostics["estimated_q_max_calibration_relative_uncertainty"] = qmax["rel"]
        capacity_terms.append(qmax["rel"])
        relative_values.append(qmax["rel"])
    else:
        if density is not None:
            diagnostics["functional_ligand_density_calibration_relative_uncertainty"] = (
                density["rel"]
            )
            capacity_terms.append(density["rel"])
            relative_values.append(density["rel"])
        if activity is not None:
            diagnostics["activity_retention_calibration_relative_uncertainty"] = (
                activity["rel"]
            )
            capacity_terms.append(activity["rel"])
            relative_values.append(activity["rel"])

    if affinity is not None:
        diagnostics["K_affinity_calibration_relative_uncertainty"] = affinity["rel"]
        # DBC is less sensitive to K_affinity than qmax in strongly binding
        # affinity operation; keep this as a conservative screening factor.
        capacity_terms.append(0.25 * affinity["rel"])
        relative_values.append(affinity["rel"])

    # v0.4.0 (C6): expose Protein A pH-shape posterior widths.
    # Closes scientific-advisor §5 P5+ scope gap. Full sensitivity into
    # elution recovery is deferred to v0.5.0 (P5++ Monte Carlo); for now
    # the relative widths are emitted so consumers see the visible interval.
    pH_transition_post = _posterior_summary_for_parameters(
        entries, {"protein_a_pH_transition"}
    )
    if pH_transition_post is not None:
        diagnostics["protein_a_pH_transition_calibration_sigma"] = (
            pH_transition_post["sigma"]
        )
        diagnostics["protein_a_pH_transition_calibration_relative_uncertainty"] = (
            pH_transition_post["rel"]
        )
        relative_values.append(pH_transition_post["rel"])
    pH_steepness_post = _posterior_summary_for_parameters(
        entries, {"protein_a_pH_steepness"}
    )
    if pH_steepness_post is not None:
        diagnostics["protein_a_pH_steepness_calibration_sigma"] = (
            pH_steepness_post["sigma"]
        )
        diagnostics["protein_a_pH_steepness_calibration_relative_uncertainty"] = (
            pH_steepness_post["rel"]
        )
        relative_values.append(pH_steepness_post["rel"])

    combined_capacity_rel = _quadrature(capacity_terms)
    if combined_capacity_rel > 0.0:
        _add_interval_diagnostics(
            diagnostics,
            prefix="dbc_10pct_calibration",
            center=float(m3_result.dbc_10pct),
            rel_sigma=combined_capacity_rel,
            units_suffix="mol_m3",
        )
        _add_interval_diagnostics(
            diagnostics,
            prefix="estimated_q_max_calibration",
            center=float(fmc.estimated_q_max),
            rel_sigma=combined_capacity_rel,
            units_suffix="mol_m3",
        )
        diagnostics["m3_capacity_calibration_relative_uncertainty"] = (
            combined_capacity_rel
        )
        relative_values.append(combined_capacity_rel)

    if dbc_10_reference is not None:
        diagnostics["dbc_10_reference_calibration_sigma_mol_m3"] = (
            dbc_10_reference["sigma"]
        )
        diagnostics["dbc_10_reference_calibration_relative_uncertainty"] = (
            dbc_10_reference["rel"]
        )
        relative_values.append(dbc_10_reference["rel"])

    if pressure_slope is not None:
        step = max(
            method.step_results,
            key=lambda item: float(item.pressure_drop_Pa),
            default=None,
        )
        if step is not None:
            reference_pressure = float(pressure_slope["value"]) * float(
                step.flow_rate_m3_s
            )
            sigma_pressure = float(pressure_slope["sigma"]) * float(
                step.flow_rate_m3_s
            )
            rel = abs(sigma_pressure) / max(abs(reference_pressure), 1.0e-12)
            diagnostics["pressure_flow_reference_pressure_sigma_Pa"] = sigma_pressure
            diagnostics["pressure_flow_reference_pressure_relative_uncertainty"] = rel
            _add_interval_diagnostics(
                diagnostics,
                prefix="pressure_flow_reference_pressure",
                center=reference_pressure,
                rel_sigma=rel,
                units_suffix="Pa",
            )
            relative_values.append(rel)

    if relative_values:
        diagnostics["calibration_posterior_relative_uncertainty_max"] = max(
            relative_values
        )
    return diagnostics


def _add_m3_calibration_uncertainty_validation(
    *,
    validation: ValidationReport,
    diagnostics: dict[str, float | int | str | list[str]],
) -> None:
    """Warn when calibration posterior width makes M3 outputs broad."""

    rel = diagnostics.get("m3_capacity_calibration_relative_uncertainty")
    if isinstance(rel, float) and rel > 0.30:
        validation.add(
            ValidationSeverity.WARNING,
            "M3_CALIBRATION_UNCERTAINTY_HIGH",
            f"M3 DBC capacity uncertainty propagated from calibration posteriors is {rel:.1%}.",
            module="M3",
            recommendation=(
                "Collect more static binding, activity-retention, and breakthrough "
                "replicates in this operating window before using DBC quantitatively."
            ),
        )
    pressure_rel = diagnostics.get("pressure_flow_reference_pressure_relative_uncertainty")
    if isinstance(pressure_rel, float) and pressure_rel > 0.30:
        validation.add(
            ValidationSeverity.WARNING,
            "M3_PRESSURE_FLOW_UNCERTAINTY_HIGH",
            (
                "Pressure-flow calibration uncertainty propagated to pressure "
                f"reference is {pressure_rel:.1%}."
            ),
            module="M3",
            recommendation=(
                "Repeat pressure-flow measurements across the intended flow range "
                "and packed-bed compression state."
            ),
        )


def _annotate_m3_calibration_uncertainty(
    *,
    method: ChromatographyMethodResult,
    diagnostics: dict[str, float | int | str | list[str]],
) -> None:
    """Attach P5+ posterior-propagation diagnostics to the M3 manifest."""

    if not diagnostics or method.model_manifest is None:
        return
    manifest = method.model_manifest
    method.model_manifest = replace(
        manifest,
        diagnostics={**manifest.diagnostics, **diagnostics},
        assumptions=[
            *manifest.assumptions,
            "Calibration posterior intervals are first-order screening estimates; they do not replace a full stochastic chromatography solve.",
        ],
    )


def _posterior_summary_for_parameters(
    entries: list,
    names: set[str],
) -> dict[str, float] | None:
    """Return inverse-variance posterior summary for one parameter family."""

    matches = [
        entry for entry in entries
        if entry.parameter_name in names
        and float(getattr(entry, "posterior_uncertainty", 0.0) or 0.0) > 0.0
    ]
    if not matches:
        return None
    if len(matches) == 1:
        value = float(matches[0].measured_value)
        sigma = abs(float(matches[0].posterior_uncertainty))
    else:
        weights = [
            1.0 / max(abs(float(entry.posterior_uncertainty)), 1.0e-30) ** 2
            for entry in matches
        ]
        value = sum(w * float(entry.measured_value) for w, entry in zip(weights, matches)) / sum(weights)
        sigma = math.sqrt(1.0 / sum(weights))
    if not math.isfinite(value) or not math.isfinite(sigma) or value == 0.0:
        return None
    return {
        "value": value,
        "sigma": sigma,
        "rel": abs(sigma) / max(abs(value), 1.0e-12),
    }


def _quadrature(values: list[float]) -> float:
    """Return root-sum-square for independent relative uncertainties."""

    clean = [float(value) for value in values if math.isfinite(float(value)) and value > 0.0]
    if not clean:
        return 0.0
    return math.sqrt(sum(value * value for value in clean))


def _add_interval_diagnostics(
    diagnostics: dict[str, float | int | str | list[str]],
    *,
    prefix: str,
    center: float,
    rel_sigma: float,
    units_suffix: str,
) -> None:
    """Add one-sigma and approximate 95 percent interval diagnostics."""

    sigma = abs(float(center)) * abs(float(rel_sigma))
    lower = max(0.0, float(center) - 1.96 * sigma)
    upper = float(center) + 1.96 * sigma
    diagnostics[f"{prefix}_sigma_{units_suffix}"] = sigma
    diagnostics[f"{prefix}_p95_lower_{units_suffix}"] = lower
    diagnostics[f"{prefix}_p95_upper_{units_suffix}"] = upper


def _apply_m3_calibration_domain_gates(
    *,
    calibration_store,
    method: ChromatographyMethodResult,
    fmc: FunctionalMediaContract,
    validation: ValidationReport,
) -> dict[str, float | bool]:
    """Warn and downgrade M3 when calibrated entries are used outside domain."""

    if calibration_store is None or method.model_manifest is None:
        return {"calibration_domain_extrapolated": False, "calibration_domain_extrapolation_count": 0}
    context = _m3_calibration_context(method, fmc)
    exits: list[dict[str, float | str]] = []
    for entry in getattr(calibration_store, "entries", []):
        if entry.target_module not in ("", "M2", "M3"):
            continue
        for key, domain in (entry.valid_domain or {}).items():
            if entry.target_module == "M2" and not _is_m2_contract_domain_key(key):
                continue
            bounds = _numeric_domain_bounds(domain)
            if bounds is None:
                continue
            value = _context_value_for_domain_key(context, key)
            if value is None:
                continue
            lower, upper = bounds
            if lower <= value <= upper:
                continue
            exit_item = {
                "parameter": entry.parameter_name,
                "target_module": entry.target_module or "FMC",
                "domain_key": str(key),
                "value": float(value),
                "lower": float(lower),
                "upper": float(upper),
            }
            exits.append(exit_item)
            validation.add(
                ValidationSeverity.WARNING,
                "M3_CALIBRATION_DOMAIN_EXTRAPOLATION",
                (
                    f"{entry.parameter_name} calibration domain {key}=[{lower:g}, {upper:g}] "
                    f"does not cover lifecycle value {value:g}."
                ),
                module="M3",
                recommendation=(
                    "Treat the M3 result as extrapolative and extend the "
                    "calibration campaign in this operating window."
                ),
            )
    if not exits:
        return {"calibration_domain_extrapolated": False, "calibration_domain_extrapolation_count": 0}

    manifest = method.model_manifest
    diagnostics = dict(manifest.diagnostics or {})
    diagnostics["calibration_domain_extrapolations"] = exits
    method.model_manifest = replace(
        manifest,
        evidence_tier=_weaker_tier(
            manifest.evidence_tier,
            ModelEvidenceTier.QUALITATIVE_TREND,
        ),
        assumptions=[
            *manifest.assumptions,
            "At least one applied M2/M3 calibration entry is outside its valid_domain; M3 outputs are downgraded to qualitative trend evidence.",
        ],
        diagnostics=diagnostics,
    )
    return {
        "calibration_domain_extrapolated": True,
        "calibration_domain_extrapolation_count": len(exits),
    }


def _enforce_m3_media_evidence_cap(
    *,
    method: ChromatographyMethodResult,
    fmc: FunctionalMediaContract,
    validation: ValidationReport,
) -> None:
    """Guarantee M3 never advertises stronger evidence than the M2 media contract."""

    if method.model_manifest is None or fmc.model_manifest is None:
        return
    m3_tier = method.model_manifest.evidence_tier
    fmc_tier = fmc.model_manifest.evidence_tier
    if _tier_rank(m3_tier) >= _tier_rank(fmc_tier):
        return
    method.model_manifest = replace(
        method.model_manifest,
        evidence_tier=fmc_tier,
        assumptions=[
            *method.model_manifest.assumptions,
            "M3 evidence tier was automatically capped to the upstream M2 FunctionalMediaContract tier.",
        ],
    )
    validation.add(
        ValidationSeverity.INFO,
        "M3_EVIDENCE_CAPPED_TO_M2",
        "M3 evidence tier was capped to the upstream M2 media contract.",
        module="M3",
    )


def _m3_calibration_context(
    method: ChromatographyMethodResult,
    fmc: FunctionalMediaContract,
) -> dict[str, float]:
    """Build lifecycle operating context used for calibration-domain checks."""

    context: dict[str, float] = {
        "functional_ligand_density": float(fmc.functional_ligand_density),
        "activity_retention": float(fmc.activity_retention),
        "ligand_leaching_fraction": float(fmc.ligand_leaching_fraction),
        "free_protein_wash_fraction": float(fmc.free_protein_wash_fraction),
        "estimated_q_max": float(fmc.estimated_q_max),
    }
    load_step = next(
        (
            step for step in method.method_steps
            if step.operation.value == "load"
        ),
        method.method_steps[0] if method.method_steps else None,
    )
    if load_step is not None:
        context.update({
            "pH": float(load_step.buffer.pH),
            "ph": float(load_step.buffer.pH),
            "buffer_pH": float(load_step.buffer.pH),
            "temperature_K": float(load_step.buffer.temperature_K),
            "temperature_C": float(load_step.buffer.temperature_K - 273.15),
            "conductivity_mS_cm": float(load_step.buffer.conductivity_mS_cm),
            "salt_concentration_mol_m3": float(load_step.buffer.salt_concentration_mol_m3),
            "salt_concentration_M": float(load_step.buffer.salt_concentration_mol_m3 / 1000.0),
            "flow_rate_m3_s": float(load_step.flow_rate_m3_s),
            "feed_concentration_mol_m3": float(load_step.feed_concentration_mol_m3),
            "equilibrium_concentration_mol_m3": float(load_step.feed_concentration_mol_m3),
        })
    if method.operability is not None:
        context.update({
            "pressure_drop_Pa": float(method.operability.pressure_drop_Pa),
            "residence_time_s": float(method.operability.residence_time_s),
            "particle_reynolds": float(method.operability.particle_reynolds),
            "axial_peclet": float(method.operability.axial_peclet),
            "bed_compression_fraction": float(method.operability.bed_compression_fraction),
        })
    return context


def _is_m2_contract_domain_key(key: str) -> bool:
    """Return True for M2 domains that can be checked from the FMC state."""

    normalized = str(key).replace("_", "").lower()
    return normalized in {
        "functionalliganddensity",
        "activityretention",
        "ligandleachingfraction",
        "freeproteinwashfraction",
        "estimatedqmax",
    }


def _numeric_domain_bounds(domain) -> tuple[float, float] | None:
    """Return numeric lower/upper bounds from a calibration valid_domain value."""

    if not isinstance(domain, (tuple, list)) or len(domain) != 2:
        return None
    try:
        lower = float(domain[0])
        upper = float(domain[1])
    except (TypeError, ValueError):
        return None
    return min(lower, upper), max(lower, upper)


def _context_value_for_domain_key(
    context: dict[str, float],
    key: str,
) -> float | None:
    """Resolve common calibration-domain aliases to lifecycle context values."""

    if key in context:
        return context[key]
    normalized = str(key).replace("_", "").lower()
    aliases = {
        "ph": "pH",
        "bufferph": "pH",
        "temperaturec": "temperature_C",
        "temperaturedegc": "temperature_C",
        "temperaturek": "temperature_K",
        "conductivitymscm": "conductivity_mS_cm",
        "saltconcentrationm": "salt_concentration_M",
        "ionicstrengthm": "salt_concentration_M",
        "saltconcentrationmolm3": "salt_concentration_mol_m3",
        "flowratem3s": "flow_rate_m3_s",
        "residencetimes": "residence_time_s",
        "feedconcentrationmolm3": "feed_concentration_mol_m3",
        "equilibriumconcentrationmolm3": "equilibrium_concentration_mol_m3",
        "pressuredroppa": "pressure_drop_Pa",
        "bedcompressionfraction": "bed_compression_fraction",
    }
    alias = aliases.get(normalized)
    return context.get(alias) if alias else None


def _tier_rank(tier) -> int:
    """Return canonical evidence-tier rank; larger means weaker."""

    values = [item.value for item in ModelEvidenceTier]
    tier_value = getattr(tier, "value", tier)
    try:
        return values.index(str(tier_value))
    except ValueError:
        return values.index(ModelEvidenceTier.UNSUPPORTED.value)


def _weaker_tier(current, cap: ModelEvidenceTier) -> ModelEvidenceTier:
    """Return the weaker of the current tier and a maximum allowed tier."""

    order = list(ModelEvidenceTier)
    return order[max(_tier_rank(current), _tier_rank(cap))]


def _annotate_fmc_m3_calibration(
    fmc: FunctionalMediaContract,
    *,
    fmc_calibration_overrides: list[str],
    m3_process_state: dict[str, float],
    m3_process_state_overrides: list[str],
) -> None:
    """Attach applied M3 calibration provenance to the FMC manifest."""

    if fmc.model_manifest is None:
        return
    diagnostics = dict(fmc.model_manifest.diagnostics or {})
    diagnostics["calibrations_applied"] = list(fmc_calibration_overrides)
    diagnostics["m3_process_state"] = dict(m3_process_state)
    diagnostics["m3_process_state_calibrations"] = list(m3_process_state_overrides)
    assumptions = list(fmc.model_manifest.assumptions)
    assumptions.append(
        "M3 lifecycle run consumed RunContext calibration entries for qmax "
        "and/or isotherm process-state parameters where available."
    )
    calibration_ref = "; ".join(
        fmc_calibration_overrides + m3_process_state_overrides
    )
    fmc.model_manifest = replace(
        fmc.model_manifest,
        diagnostics=diagnostics,
        assumptions=assumptions,
        calibration_ref=calibration_ref[:500],
    )


def _m3_dbc_reference_diagnostics(
    m3_result: BreakthroughResult,
    references: dict[str, float],
) -> dict[str, float]:
    """Compare simulated M3 DBC values with measured DBC references."""

    mapping = {
        "dbc_5_reference": ("dbc_5", float(m3_result.dbc_5pct)),
        "dbc_10_reference": ("dbc_10", float(m3_result.dbc_10pct)),
        "dbc_50_reference": ("dbc_50", float(m3_result.dbc_50pct)),
    }
    diagnostics: dict[str, float] = {}
    for reference_name, (metric, simulated) in mapping.items():
        reference = references.get(reference_name)
        if reference is None:
            continue
        diagnostics[f"{metric}_reference_mol_m3"] = float(reference)
        diagnostics[f"{metric}_simulated_mol_m3"] = simulated
        diagnostics[f"{metric}_relative_error"] = _relative_error(simulated, reference)
    return diagnostics


def _dsd_dbc_reference_diagnostics(
    dsd_summary: DSDPropagationSummary,
    references: dict[str, float],
) -> dict[str, float]:
    """Compare DSD-resolved DBC10 p50 with a measured DBC10 reference."""

    if not dsd_summary.breakthrough_simulated:
        return {}
    reference = references.get("dbc_10_reference")
    if reference is None:
        return {}
    simulated = float(dsd_summary.dbc_10_weighted_p50_mol_m3)
    return {
        "dbc_10_reference_mol_m3": float(reference),
        "dbc_10_weighted_p50_relative_error": _relative_error(
            simulated,
            reference,
        ),
    }


def _add_m3_dbc_reference_validation(
    *,
    validation: ValidationReport,
    diagnostics: dict[str, float],
) -> None:
    """Warn when simulated M3 DBC differs strongly from measured DBC."""

    for metric in ("dbc_5", "dbc_10", "dbc_50"):
        key = f"{metric}_relative_error"
        if key not in diagnostics:
            continue
        error = diagnostics[key]
        if abs(error) <= 0.30:
            continue
        validation.add(
            ValidationSeverity.WARNING,
            "M3_DBC_REFERENCE_MISMATCH",
            (
                f"Simulated {metric.upper()} differs from the measured "
                f"reference by {error:.1%}."
            ),
            module="M3",
            recommendation=(
                "Refit qmax/K_affinity or adjust residence time, packing, "
                "mass-transfer, and assay-domain metadata before using DBC "
                "as a quantitative release metric."
            ),
        )


def _relative_error(simulated: float, reference: float) -> float:
    """Return signed relative error against a measured reference."""

    if reference == 0.0:
        return 0.0 if simulated == 0.0 else float("inf")
    return (float(simulated) - float(reference)) / abs(float(reference))


def _m1_carryover_diagnostics(
    m1_contract: M1ExportContract,
    resolved_inputs,
) -> dict[str, float]:
    """Return normalized M1 residual carryover diagnostics for M2/M3 nodes."""

    oil_limit = resolved_inputs.max_residual_oil_volume_fraction
    surfactant_limit = resolved_inputs.max_residual_surfactant_concentration_kg_m3
    return {
        "m1_residual_oil_volume_fraction": float(
            m1_contract.residual_oil_volume_fraction
        ),
        "m1_residual_oil_limit": float(oil_limit),
        "residual_oil_limit_ratio": _safe_ratio(
            m1_contract.residual_oil_volume_fraction,
            oil_limit,
        ),
        "m1_residual_surfactant_kg_m3": float(
            m1_contract.residual_surfactant_concentration_kg_m3
        ),
        "m1_residual_surfactant_limit_kg_m3": float(surfactant_limit),
        "residual_surfactant_limit_ratio": _safe_ratio(
            m1_contract.residual_surfactant_concentration_kg_m3,
            surfactant_limit,
        ),
    }


def _validate_m1_carryover_for_downstream(
    *,
    m1_contract: M1ExportContract,
    resolved_inputs,
    validation: ValidationReport,
) -> None:
    """Gate M2/M3 use against recipe-owned M1 residual carryover limits.

    These limits are development screening targets. They do not replace
    validated residual oil, residual surfactant, leachables, or column fouling
    assays, but they prevent a visibly under-washed M1 state from silently
    flowing into M2 ligand coupling and M3 breakthrough claims.
    """

    oil_limit = float(resolved_inputs.max_residual_oil_volume_fraction)
    surfactant_limit = float(
        resolved_inputs.max_residual_surfactant_concentration_kg_m3
    )
    if oil_limit < 0.0:
        validation.add(
            ValidationSeverity.BLOCKER,
            "TARGET_RESIDUAL_LIMIT",
            "target.max_residual_oil_volume_fraction must be non-negative.",
            module="M1/M2/M3",
            recommendation="Correct the target product profile residual-oil limit.",
        )
    if surfactant_limit < 0.0:
        validation.add(
            ValidationSeverity.BLOCKER,
            "TARGET_RESIDUAL_LIMIT",
            "target.max_residual_surfactant_concentration must be non-negative.",
            module="M1/M2/M3",
            recommendation="Correct the target product profile residual-surfactant limit.",
        )

    washing = getattr(m1_contract, "washing_model", None)
    if washing is not None:
        for warning in washing.warnings:
            validation.add(
                ValidationSeverity.WARNING,
                "M1_WASH_MODEL",
                warning,
                module="M1",
                recommendation=(
                    "Increase wash cycles/volume/mixing or fit the M1 washing "
                    "model to residual oil and surfactant assays."
                ),
            )

    oil = float(m1_contract.residual_oil_volume_fraction)
    surfactant = float(m1_contract.residual_surfactant_concentration_kg_m3)
    _add_carryover_threshold_issue(
        validation=validation,
        value=oil,
        limit=oil_limit,
        code="M1_RESIDUAL_OIL_CARRYOVER",
        unit="fraction",
        label="residual oil volume fraction",
        downstream_risk=(
            "oil carryover can alter bead wetting, M2 reagent access, column "
            "packing, pressure-flow behavior, and nonspecific binding"
        ),
    )
    _add_carryover_threshold_issue(
        validation=validation,
        value=surfactant,
        limit=surfactant_limit,
        code="M1_RESIDUAL_SURFACTANT_CARRYOVER",
        unit="kg/m3",
        label="residual surfactant concentration",
        downstream_risk=(
            "retained surfactant can suppress ligand coupling, perturb protein "
            "binding, and introduce chromatography baseline or leachables risk"
        ),
    )


def _add_carryover_threshold_issue(
    *,
    validation: ValidationReport,
    value: float,
    limit: float,
    code: str,
    unit: str,
    label: str,
    downstream_risk: str,
) -> None:
    """Add a warning/blocker when a carryover metric exceeds its target."""

    if limit < 0.0 or value <= limit:
        return
    ratio = _safe_ratio(value, limit)
    severity = ValidationSeverity.BLOCKER if ratio >= 5.0 else ValidationSeverity.WARNING
    validation.add(
        severity,
        code,
        (
            f"M1 {label} is {value:.3g} {unit}, above the recipe target "
            f"{limit:.3g} {unit}; {downstream_risk}."
        ),
        module="M1/M2/M3",
        recommendation=(
            "Increase M1 wash cycles, wash volume, or mixing efficiency; then "
            "confirm residual oil/surfactant by assay before relying on M2/M3 "
            "performance predictions."
        ),
    )


def _safe_ratio(value: float, limit: float) -> float:
    """Return value / limit, handling zero-limit targets explicitly."""

    if limit > 0.0:
        return float(value) / float(limit)
    return 0.0 if value <= 0.0 else float("inf")


def _summarize_dsd_variants(
    variants: list[DSDMediaVariant],
) -> DSDPropagationSummary:
    """Create a mass-weighted DSD downstream summary."""
    if not variants:
        return DSDPropagationSummary(
            n_quantiles=0,
            q_max_weighted_mean_mol_m3=0.0,
            q_max_weighted_p05_mol_m3=0.0,
            q_max_weighted_p50_mol_m3=0.0,
            q_max_weighted_p95_mol_m3=0.0,
            q_max_min_mol_m3=0.0,
            q_max_max_mol_m3=0.0,
            pressure_drop_min_Pa=0.0,
            pressure_drop_weighted_p50_Pa=0.0,
            pressure_drop_weighted_p95_Pa=0.0,
            pressure_drop_max_Pa=0.0,
            bed_compression_weighted_p50_fraction=0.0,
            bed_compression_weighted_p95_fraction=0.0,
            max_bed_compression_fraction=0.0,
            max_residual_concentration_mol_m3=0.0,
            breakthrough_simulated=False,
            dbc_10_weighted_mean_mol_m3=0.0,
            dbc_10_weighted_p05_mol_m3=0.0,
            dbc_10_weighted_p50_mol_m3=0.0,
            dbc_10_weighted_p95_mol_m3=0.0,
            max_breakthrough_mass_balance_error=0.0,
            represented_mass_fraction=0.0,
            warnings=["DSD propagation requested but no variants were produced."],
        )

    weights = [max(v.mass_fraction, 0.0) for v in variants]
    total_weight = sum(weights) or 1.0
    q_values = [v.estimated_q_max_mol_m3 for v in variants]
    pressure_values = [v.pressure_drop_Pa for v in variants]
    compression_values = [v.bed_compression_fraction for v in variants]
    residual_values = [
        value
        for variant in variants
        for value in variant.residual_reagent_concentrations.values()
    ]
    q_mean = sum(v.estimated_q_max_mol_m3 * w for v, w in zip(variants, weights)) / total_weight
    q_p05 = _weighted_percentile(q_values, weights, 0.05)
    q_p50 = _weighted_percentile(q_values, weights, 0.50)
    q_p95 = _weighted_percentile(q_values, weights, 0.95)
    pressure_p50 = _weighted_percentile(pressure_values, weights, 0.50)
    pressure_p95 = _weighted_percentile(pressure_values, weights, 0.95)
    compression_p50 = _weighted_percentile(compression_values, weights, 0.50)
    compression_p95 = _weighted_percentile(compression_values, weights, 0.95)
    breakthrough_simulated = any(v.breakthrough_simulated for v in variants)
    dbc_10_values = [v.dbc_10pct_mol_m3 for v in variants]
    dbc_10_mean = 0.0
    dbc_10_p05 = 0.0
    dbc_10_p50 = 0.0
    dbc_10_p95 = 0.0
    max_bt_mass_balance = 0.0
    if breakthrough_simulated:
        dbc_10_mean = sum(v.dbc_10pct_mol_m3 * w for v, w in zip(variants, weights)) / total_weight
        dbc_10_p05 = _weighted_percentile(dbc_10_values, weights, 0.05)
        dbc_10_p50 = _weighted_percentile(dbc_10_values, weights, 0.50)
        dbc_10_p95 = _weighted_percentile(dbc_10_values, weights, 0.95)
        max_bt_mass_balance = max(
            v.breakthrough_mass_balance_error
            for v in variants
            if v.breakthrough_simulated
        )
    warnings: list[str] = []
    if min(pressure_values) > 0 and max(pressure_values) / min(pressure_values) > 2.0:
        warnings.append(
            "DSD quantiles produce more than 2x pressure-drop spread; d50-only "
            "M3 screening may hide hydraulic risk."
        )
    if pressure_p95 > 1.5 * pressure_p50 and pressure_p50 > 0.0:
        warnings.append(
            "DSD-weighted p95 pressure drop is more than 1.5x the median; "
            "packing risk is controlled by the fine-particle tail."
        )
    if compression_p95 > 0.20:
        warnings.append(
            f"DSD-weighted p95 bed compression is {compression_p95:.1%}; "
            "tail particles may compact or foul before the median bead does."
        )
    if max_bt_mass_balance > 0.05:
        warnings.append(
            f"DSD-resolved breakthrough mass-balance error reaches "
            f"{max_bt_mass_balance:.1%}; DBC tail metrics are not decision-grade."
        )
    elif max_bt_mass_balance > 0.02:
        warnings.append(
            f"DSD-resolved breakthrough mass-balance error reaches "
            f"{max_bt_mass_balance:.1%}; treat DBC tail metrics as cautionary."
        )
    for variant in variants:
        if variant.bed_compression_fraction > 0.20:
            warnings.append(
                f"Quantile {variant.quantile:.2f} bed compression is "
                f"{variant.bed_compression_fraction:.1%}."
            )
    return DSDPropagationSummary(
        n_quantiles=len(variants),
        q_max_weighted_mean_mol_m3=float(q_mean),
        q_max_weighted_p05_mol_m3=float(q_p05),
        q_max_weighted_p50_mol_m3=float(q_p50),
        q_max_weighted_p95_mol_m3=float(q_p95),
        q_max_min_mol_m3=float(min(q_values)),
        q_max_max_mol_m3=float(max(q_values)),
        pressure_drop_min_Pa=float(min(pressure_values)),
        pressure_drop_weighted_p50_Pa=float(pressure_p50),
        pressure_drop_weighted_p95_Pa=float(pressure_p95),
        pressure_drop_max_Pa=float(max(pressure_values)),
        bed_compression_weighted_p50_fraction=float(compression_p50),
        bed_compression_weighted_p95_fraction=float(compression_p95),
        max_bed_compression_fraction=float(
            max(v.bed_compression_fraction for v in variants)
        ),
        max_residual_concentration_mol_m3=float(max(residual_values or [0.0])),
        breakthrough_simulated=bool(breakthrough_simulated),
        dbc_10_weighted_mean_mol_m3=float(dbc_10_mean),
        dbc_10_weighted_p05_mol_m3=float(dbc_10_p05),
        dbc_10_weighted_p50_mol_m3=float(dbc_10_p50),
        dbc_10_weighted_p95_mol_m3=float(dbc_10_p95),
        max_breakthrough_mass_balance_error=float(max_bt_mass_balance),
        represented_mass_fraction=float(sum(weights)),
        warnings=warnings,
    )


def _weighted_percentile(
    values: list[float],
    weights: list[float],
    quantile: float,
) -> float:
    """Return a weighted percentile for small DSD representative lists."""

    if not values:
        return 0.0
    pairs = sorted(
        (float(value), max(0.0, float(weight)))
        for value, weight in zip(values, weights)
    )
    total = sum(weight for _, weight in pairs)
    if total <= 0.0:
        idx = int(round(min(1.0, max(0.0, quantile)) * (len(pairs) - 1)))
        return float(pairs[idx][0])
    target = min(1.0, max(0.0, quantile)) * total
    cumulative = 0.0
    for value, weight in pairs:
        cumulative += weight
        if cumulative >= target:
            return float(value)
    return float(pairs[-1][0])


def run_default_lifecycle(**kwargs) -> DownstreamLifecycleResult:
    """Convenience entry point for quick lifecycle simulation."""
    return DownstreamProcessOrchestrator().run(**kwargs)
