"""Wet-lab aligned process recipe objects for M1/M2/M3 lifecycle simulation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .quantities import Quantity


class LifecycleStage(Enum):
    """Major process stages in the Downstream Processing Simulator."""

    M1_FABRICATION = "M1_fabrication"
    M2_FUNCTIONALIZATION = "M2_functionalization"
    M3_PERFORMANCE = "M3_performance"
    QC = "QC"


class ProcessStepKind(Enum):
    """Wet-lab operation categories used by recipe and protocol layers."""

    PREPARE_PHASE = "prepare_phase"
    EMULSIFY = "emulsify"
    COOL_OR_GEL = "cool_or_gel"
    WASH = "wash"
    CROSSLINK = "crosslink"
    ACTIVATE = "activate"
    INSERT_SPACER = "insert_spacer"
    COUPLE_LIGAND = "couple_ligand"
    METAL_CHARGE = "metal_charge"
    PROTEIN_PRETREATMENT = "protein_pretreatment"
    QUENCH = "quench"
    BLOCK_OR_QUENCH = "block_or_quench"
    STORAGE_BUFFER_EXCHANGE = "storage_buffer_exchange"
    PACK_COLUMN = "pack_column"
    EQUILIBRATE = "equilibrate"
    LOAD = "load"
    ELUTE = "elute"
    REGENERATE = "regenerate"
    ASSAY = "assay"


@dataclass
class TargetProductProfile:
    """Design target for the complete microsphere media lifecycle."""

    name: str = "Protein A affinity microsphere media"
    bead_d50: Quantity = field(default_factory=lambda: Quantity(100.0, "um", source="target"))
    pore_size: Quantity = field(default_factory=lambda: Quantity(100.0, "nm", source="target"))
    min_modulus: Quantity = field(default_factory=lambda: Quantity(10.0, "kPa", source="target"))
    target_ligand: str = "Protein A"
    target_analyte: str = "IgG"
    max_pressure_drop: Quantity = field(default_factory=lambda: Quantity(3.0, "bar", source="target"))
    max_residual_oil_volume_fraction: Quantity = field(
        default_factory=lambda: Quantity(
            0.01,
            "fraction",
            source="target",
            lower=0.0,
            upper=1.0,
            note=(
                "Development-screening limit for oil carried from M1 into M2/M3. "
                "Not a GMP release specification."
            ),
        )
    )
    max_residual_surfactant_concentration: Quantity = field(
        default_factory=lambda: Quantity(
            0.5,
            "kg/m3",
            source="target",
            lower=0.0,
            note=(
                "Development-screening limit for retained Span-80-equivalent "
                "surfactant carried from M1 into functionalization and column use."
            ),
        )
    )
    notes: str = (
        "Targets describe process-development intent; they are not evidence "
        "that a formulation is achievable without calibration."
    )


@dataclass
class MaterialBatch:
    """Material lot and property metadata needed for reproducible simulation."""

    polymer_family: str = "agarose_chitosan"
    polymer_lot: str = "unassigned"
    oil_lot: str = "unassigned"
    surfactant_lot: str = "unassigned"
    ligand_lot: str = "unassigned"
    target_molecule: str = "IgG"
    properties: dict[str, Quantity] = field(default_factory=dict)


@dataclass
class EquipmentProfile:
    """Equipment metadata spanning fabrication and chromatography."""

    emulsifier: str = "rotor_stator_legacy"
    vessel: str = "glass_beaker"
    column_id: str = "analytical_column_10mm"
    detector: str = "UV280"
    pump_pressure_limit: Quantity = field(default_factory=lambda: Quantity(3.0, "bar", source="equipment_default"))
    notes: str = ""


@dataclass
class ProcessStep:
    """One operation in the lab-executable lifecycle recipe.

    ``parameters`` stores operation-specific quantities and string descriptors.
    Keeping steps generic allows the protocol layer, UI, and solver adapters to
    share a single recipe object while the numerical kernels keep their
    specialized dataclasses.
    """

    name: str
    stage: LifecycleStage
    kind: ProcessStepKind
    parameters: dict[str, Quantity | str | float | int] = field(default_factory=dict)
    notes: str = ""
    qc_required: list[str] = field(default_factory=list)


@dataclass
class ProcessRecipe:
    """Full lifecycle recipe from microsphere fabrication to column use."""

    target: TargetProductProfile = field(default_factory=TargetProductProfile)
    material_batch: MaterialBatch = field(default_factory=MaterialBatch)
    equipment: EquipmentProfile = field(default_factory=EquipmentProfile)
    steps: list[ProcessStep] = field(default_factory=list)
    run_mode: str = "hybrid_coupled"
    owner: str = ""
    notes: str = ""

    def steps_for_stage(self, stage: LifecycleStage) -> list[ProcessStep]:
        """Return recipe steps belonging to one lifecycle stage."""
        return [step for step in self.steps if step.stage == stage]


def default_affinity_media_recipe() -> ProcessRecipe:
    """Return a conservative default recipe for Protein A affinity media.

    The values are intentionally ordinary screening defaults, not optimized
    production settings. They give the new lifecycle orchestrator a realistic
    wet-lab storyline while preserving evidence-tier warnings from the legacy
    solvers.
    """

    recipe = ProcessRecipe()
    recipe.steps.extend(
        [
            ProcessStep(
                name="Prepare hot aqueous polymer phase and oil/surfactant phase",
                stage=LifecycleStage.M1_FABRICATION,
                kind=ProcessStepKind.PREPARE_PHASE,
                parameters={
                    "oil_temperature": Quantity(90.0, "degC", source="screening_default"),
                    "span80": Quantity(1.5, "%", source="screening_default"),
                    # v0.3.0 (B4): polymer concentrations promoted into the recipe
                    # so the recipe layer is the single source of truth for
                    # M1 formulation. The A+C defaults below match the legacy
                    # SimulationParameters defaults (4.2% agarose, 1.8% chitosan,
                    # 2 mM genipin) for backward compatibility with smoke runs.
                    "c_agarose": Quantity(42.0, "kg/m3", source="screening_default"),
                    "c_chitosan": Quantity(18.0, "kg/m3", source="screening_default"),
                    "c_genipin": Quantity(2.0, "mol/m3", source="screening_default"),
                },
                qc_required=["Record phase clarity and viscosity before emulsification."],
            ),
            ProcessStep(
                name="Rotor-stator emulsification",
                stage=LifecycleStage.M1_FABRICATION,
                kind=ProcessStepKind.EMULSIFY,
                parameters={
                    "rpm": Quantity(10000.0, "rpm", source="screening_default"),
                    "time": Quantity(60.0, "s", source="screening_default"),
                },
                qc_required=[
                    "Measure bead size distribution by microscopy or laser diffraction.",
                    "Archive the measured DSD quantile table for M2/M3 propagation.",
                ],
            ),
            ProcessStep(
                name="Cool to gel and wash microspheres",
                stage=LifecycleStage.M1_FABRICATION,
                kind=ProcessStepKind.COOL_OR_GEL,
                parameters={
                    "cooling_rate": Quantity(10.0, "K/min", source="screening_default"),
                    "initial_oil_carryover_fraction": Quantity(
                        0.10,
                        "fraction",
                        source="screening_default",
                        lower=0.0,
                        upper=1.0,
                        note="Oil retained with collected wet beads before drain/resuspend washing.",
                    ),
                    "wash_cycles": Quantity(
                        3.0,
                        "1",
                        source="screening_default",
                        lower=0.0,
                        note="Number of drain/resuspend washes after oil-phase bead collection.",
                    ),
                    "wash_volume_ratio": Quantity(
                        3.0,
                        "1",
                        source="screening_default",
                        lower=0.0,
                        note="Wash liquid volume per wet bead/slurry volume for each cycle.",
                    ),
                    "wash_mixing_efficiency": Quantity(
                        0.80,
                        "fraction",
                        source="screening_default",
                        lower=0.0,
                        upper=1.0,
                        note="Fractional approach to well-mixed extraction per wash cycle.",
                    ),
                    "oil_retention_factor": Quantity(
                        1.0,
                        "1",
                        source="screening_default",
                        lower=0.05,
                        note="Lumped extraction retention factor for oil; larger means harder to remove.",
                    ),
                    "surfactant_retention_factor": Quantity(
                        1.5,
                        "1",
                        source="screening_default",
                        lower=0.05,
                        note="Lumped extraction retention factor for Span-80; larger means harder to remove.",
                    ),
                },
                qc_required=[
                    "Inspect bead integrity after oil removal.",
                    "Measure pore structure by pore imaging or SEC inverse-size calibration.",
                    "Measure swelling ratio in the intended chromatography buffer.",
                    "Measure single-bead compression or bulk modulus before column packing.",
                    "Measure residual oil and residual surfactant after washing.",
                ],
            ),
            ProcessStep(
                name="ECH activation of hydroxyl groups",
                stage=LifecycleStage.M2_FUNCTIONALIZATION,
                kind=ProcessStepKind.ACTIVATE,
                parameters={
                    "reagent_key": "ech_activation",
                    "pH": Quantity(12.0, "1", source="profile_default"),
                    "temperature": Quantity(25.0, "degC", source="profile_default"),
                    "time": Quantity(2.0, "h", source="profile_default"),
                    "reagent_concentration": Quantity(100.0, "mol/m3", source="profile_default"),
                },
                qc_required=["Confirm activation or proceed immediately to coupling to limit hydrolysis."],
            ),
            ProcessStep(
                name="Wash after activation",
                stage=LifecycleStage.M2_FUNCTIONALIZATION,
                kind=ProcessStepKind.WASH,
                parameters={
                    "reagent_key": "wash_buffer",
                    "target_acs": "epoxide",
                    "pH": Quantity(7.4, "1", source="profile_default"),
                    "temperature": Quantity(25.0, "degC", source="profile_default"),
                    "time": Quantity(1.0, "h", source="profile_default"),
                    "reagent_concentration": Quantity(0.0, "mol/m3", source="profile_default"),
                },
                qc_required=["Wash until activation reagent residuals are assay-ready."],
            ),
            ProcessStep(
                name="Protein A coupling",
                stage=LifecycleStage.M2_FUNCTIONALIZATION,
                kind=ProcessStepKind.COUPLE_LIGAND,
                parameters={
                    "reagent_key": "protein_a_coupling",
                    "pH": Quantity(9.0, "1", source="profile_default"),
                    "temperature": Quantity(4.0, "degC", source="profile_default"),
                    "time": Quantity(16.0, "h", source="profile_default"),
                    "reagent_concentration": Quantity(0.02, "mol/m3", source="profile_default"),
                },
                qc_required=["Measure coupled protein and retained IgG binding activity."],
            ),
            ProcessStep(
                name="Wash after Protein A coupling",
                stage=LifecycleStage.M2_FUNCTIONALIZATION,
                kind=ProcessStepKind.WASH,
                parameters={
                    "reagent_key": "wash_buffer",
                    "target_acs": "epoxide",
                    "pH": Quantity(7.4, "1", source="profile_default"),
                    "temperature": Quantity(4.0, "degC", source="profile_default"),
                    "time": Quantity(1.0, "h", source="profile_default"),
                    "reagent_concentration": Quantity(0.0, "mol/m3", source="profile_default"),
                },
                qc_required=["Measure free Protein A or UV280 in wash fractions."],
            ),
            ProcessStep(
                name="Ethanolamine quench",
                stage=LifecycleStage.M2_FUNCTIONALIZATION,
                kind=ProcessStepKind.BLOCK_OR_QUENCH,
                parameters={
                    "reagent_key": "ethanolamine_quench",
                    "pH": Quantity(8.5, "1", source="profile_default"),
                    "temperature": Quantity(25.0, "degC", source="profile_default"),
                    "time": Quantity(2.0, "h", source="profile_default"),
                    "reagent_concentration": Quantity(1000.0, "mol/m3", source="profile_default"),
                },
                qc_required=["Wash until residual reactive groups and free ligand are below acceptance threshold."],
            ),
            ProcessStep(
                name="Final wash after quench",
                stage=LifecycleStage.M2_FUNCTIONALIZATION,
                kind=ProcessStepKind.WASH,
                parameters={
                    "reagent_key": "wash_buffer",
                    "target_acs": "epoxide",
                    "pH": Quantity(7.4, "1", source="profile_default"),
                    "temperature": Quantity(25.0, "degC", source="profile_default"),
                    "time": Quantity(2.0, "h", source="profile_default"),
                    "reagent_concentration": Quantity(0.0, "mol/m3", source="profile_default"),
                },
                qc_required=["Release only after residual reagent assay is below acceptance threshold."],
            ),
            ProcessStep(
                name="Storage buffer exchange",
                stage=LifecycleStage.M2_FUNCTIONALIZATION,
                kind=ProcessStepKind.STORAGE_BUFFER_EXCHANGE,
                parameters={
                    "reagent_key": "wash_buffer",
                    "target_acs": "epoxide",
                    "pH": Quantity(7.4, "1", source="storage_default"),
                    "temperature": Quantity(4.0, "degC", source="storage_default"),
                    "time": Quantity(
                        4.0,
                        "h",
                        source="storage_default",
                        note="Buffer exchange/equilibration into storage buffer before column packing.",
                    ),
                    "reagent_concentration": Quantity(0.0, "mol/m3", source="storage_default"),
                },
                qc_required=[
                    "Confirm storage-buffer pH and conductivity.",
                    "Measure ligand leaching after storage contact time.",
                    "Check bioburden/endotoxin according to intended use.",
                ],
            ),
            ProcessStep(
                name="Pack analytical Protein A affinity column",
                stage=LifecycleStage.M3_PERFORMANCE,
                kind=ProcessStepKind.PACK_COLUMN,
                parameters={
                    "column_id": "analytical_10mm_x_100mm",
                    "column_diameter": Quantity(10.0, "mm", source="user_recipe"),
                    "bed_height": Quantity(10.0, "cm", source="user_recipe"),
                    "bed_porosity": Quantity(0.38, "fraction", source="screening_default"),
                    "packing_flow_rate": Quantity(0.3, "mL/min", source="screening_default"),
                },
                qc_required=[
                    "Record settled bed height, bed symmetry, and pressure-flow curve.",
                    "Confirm no visible channeling, cracks, or bed lift before loading.",
                ],
            ),
            ProcessStep(
                name="Equilibrate Protein A column",
                stage=LifecycleStage.M3_PERFORMANCE,
                kind=ProcessStepKind.EQUILIBRATE,
                parameters={
                    "buffer_name": "PBS-equivalent equilibration buffer",
                    "pH": Quantity(7.4, "1", source="screening_default"),
                    "conductivity": Quantity(15.0, "mS/cm", source="screening_default"),
                    "flow_rate": Quantity(0.6, "mL/min", source="screening_default"),
                    "duration": Quantity(5.0, "min", source="screening_default"),
                },
                qc_required=["Confirm column outlet pH and conductivity match inlet buffer."],
            ),
            ProcessStep(
                name="Load IgG feed onto Protein A column",
                stage=LifecycleStage.M3_PERFORMANCE,
                kind=ProcessStepKind.LOAD,
                parameters={
                    "buffer_name": "clarified IgG feed in binding buffer",
                    "pH": Quantity(7.4, "1", source="screening_default"),
                    "conductivity": Quantity(15.0, "mS/cm", source="screening_default"),
                    "feed_concentration": Quantity(1.0, "mol/m3", source="screening_default"),
                    "flow_rate": Quantity(0.6, "mL/min", source="screening_default"),
                    "feed_duration": Quantity(10.0, "min", source="screening_default"),
                    "total_time": Quantity(20.0, "min", source="screening_default"),
                    "residence_time": Quantity(
                        13.1,
                        "min",
                        source="derived_screening_target",
                        note="Approximate bed-volume residence time for a 10 mm x 100 mm bed at 0.6 mL/min.",
                    ),
                },
                qc_required=["Compare predicted DBC10 with measured breakthrough curve."],
            ),
            ProcessStep(
                name="Wash unbound protein from Protein A column",
                stage=LifecycleStage.M3_PERFORMANCE,
                kind=ProcessStepKind.WASH,
                parameters={
                    "buffer_name": "PBS-equivalent wash buffer",
                    "pH": Quantity(7.4, "1", source="screening_default"),
                    "conductivity": Quantity(15.0, "mS/cm", source="screening_default"),
                    "flow_rate": Quantity(0.6, "mL/min", source="screening_default"),
                    "duration": Quantity(5.0, "min", source="screening_default"),
                },
                qc_required=[
                    "Collect wash fractions until UV280 returns to baseline.",
                    "Assay free Protein A or host-cell protein if required by the use case.",
                ],
            ),
            ProcessStep(
                name="Elute bound IgG from Protein A column",
                stage=LifecycleStage.M3_PERFORMANCE,
                kind=ProcessStepKind.ELUTE,
                parameters={
                    "buffer_name": "low-pH glycine-equivalent elution buffer",
                    "pH": Quantity(3.5, "1", source="screening_default"),
                    "conductivity": Quantity(5.0, "mS/cm", source="screening_default"),
                    "flow_rate": Quantity(0.6, "mL/min", source="screening_default"),
                    "duration": Quantity(5.0, "min", source="screening_default"),
                    "gradient_field": "ph",
                    "gradient_start_pH": Quantity(7.4, "1", source="screening_default"),
                    "gradient_end_pH": Quantity(3.5, "1", source="screening_default"),
                },
                qc_required=[
                    "Collect elution peak fractions and neutralize promptly.",
                    "Measure IgG recovery, aggregate risk, and ligand leaching in elution pool.",
                ],
            ),
        ]
    )
    return recipe
