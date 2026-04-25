"""Wet-lab aligned M2 functionalization recipe-stage templates.

These templates are intentionally small lists of ``ProcessStep`` objects rather
than full recipes. A developer can drop them into a ``ProcessRecipe`` while
keeping the M1 fabrication and M3 performance sections unchanged.
"""

from __future__ import annotations

import copy
from collections.abc import Callable

from .process_recipe import LifecycleStage, ProcessStep, ProcessStepKind
from .quantities import Quantity


def _q(value: float, unit: str, source: str, note: str = "") -> Quantity:
    return Quantity(value, unit, source=source, note=note)


def _wash(name: str, target_acs: str, *, temperature_c: float = 25.0, hours: float = 1.0) -> ProcessStep:
    return ProcessStep(
        name=name,
        stage=LifecycleStage.M2_FUNCTIONALIZATION,
        kind=ProcessStepKind.WASH,
        parameters={
            "reagent_key": "wash_buffer",
            "target_acs": target_acs,
            "pH": _q(7.4, "1", "template_default"),
            "temperature": _q(temperature_c, "degC", "template_default"),
            "time": _q(hours, "h", "template_default"),
            "reagent_concentration": _q(0.0, "mol/m3", "template_default"),
        },
        qc_required=["Measure residual reagent or free ligand in wash fractions."],
    )


def _storage_exchange(target_acs: str) -> ProcessStep:
    return ProcessStep(
        name="Storage buffer exchange",
        stage=LifecycleStage.M2_FUNCTIONALIZATION,
        kind=ProcessStepKind.STORAGE_BUFFER_EXCHANGE,
        parameters={
            "reagent_key": "wash_buffer",
            "target_acs": target_acs,
            "pH": _q(7.4, "1", "template_default"),
            "temperature": _q(4.0, "degC", "template_default"),
            "time": _q(4.0, "h", "template_default"),
            "reagent_concentration": _q(0.0, "mol/m3", "template_default"),
        },
        qc_required=[
            "Confirm storage-buffer pH and conductivity.",
            "Measure ligand leaching after storage contact time.",
        ],
    )


def epoxy_protein_a_template() -> list[ProcessStep]:
    """ECH activation followed by direct Protein A coupling."""

    return [
        ProcessStep(
            name="ECH activation of hydroxyl groups",
            stage=LifecycleStage.M2_FUNCTIONALIZATION,
            kind=ProcessStepKind.ACTIVATE,
            parameters={
                "reagent_key": "ech_activation",
                "pH": _q(12.0, "1", "template_default"),
                "temperature": _q(25.0, "degC", "template_default"),
                "time": _q(2.0, "h", "template_default"),
                "reagent_concentration": _q(100.0, "mol/m3", "template_default"),
            },
            qc_required=["Confirm activation or minimize hold time before coupling."],
        ),
        _wash("Wash after ECH activation", "epoxide"),
        ProcessStep(
            name="Protein A coupling",
            stage=LifecycleStage.M2_FUNCTIONALIZATION,
            kind=ProcessStepKind.COUPLE_LIGAND,
            parameters={
                "reagent_key": "protein_a_coupling",
                "pH": _q(9.0, "1", "template_default"),
                "temperature": _q(4.0, "degC", "template_default"),
                "time": _q(16.0, "h", "template_default"),
                "reagent_concentration": _q(0.02, "mol/m3", "template_default"),
            },
            qc_required=["Measure coupled Protein A density and retained IgG binding activity."],
        ),
        _wash("Wash after Protein A coupling", "epoxide", temperature_c=4.0),
        ProcessStep(
            name="Block residual epoxide groups",
            stage=LifecycleStage.M2_FUNCTIONALIZATION,
            kind=ProcessStepKind.BLOCK_OR_QUENCH,
            parameters={
                "reagent_key": "ethanolamine_quench",
                "pH": _q(8.5, "1", "template_default"),
                "temperature": _q(25.0, "degC", "template_default"),
                "time": _q(2.0, "h", "template_default"),
                "reagent_concentration": _q(1000.0, "mol/m3", "template_default"),
            },
        ),
        _wash("Final wash after epoxide block", "epoxide", hours=2.0),
        _storage_exchange("epoxide"),
    ]


def edc_nhs_protein_a_template() -> list[ProcessStep]:
    """AHA spacer insertion, EDC/NHS activation, and Protein A coupling."""

    return [
        epoxy_protein_a_template()[0],
        ProcessStep(
            name="AHA carboxyl spacer insertion",
            stage=LifecycleStage.M2_FUNCTIONALIZATION,
            kind=ProcessStepKind.INSERT_SPACER,
            parameters={
                "reagent_key": "aha_carboxyl_spacer_arm",
                "pH": _q(10.5, "1", "template_default"),
                "temperature": _q(25.0, "degC", "template_default"),
                "time": _q(4.0, "h", "template_default"),
                "reagent_concentration": _q(50.0, "mol/m3", "template_default"),
            },
            qc_required=["Confirm spacer density or carboxyl content before EDC/NHS activation."],
        ),
        _wash("Wash after AHA spacer insertion", "carboxyl_distal"),
        ProcessStep(
            name="EDC/NHS activation of carboxyl spacer",
            stage=LifecycleStage.M2_FUNCTIONALIZATION,
            kind=ProcessStepKind.ACTIVATE,
            parameters={
                "reagent_key": "edc_nhs_activation",
                "pH": _q(5.5, "1", "template_default"),
                "temperature": _q(25.0, "degC", "template_default"),
                "time": _q(15.0, "min", "template_default"),
                "reagent_concentration": _q(20.0, "mol/m3", "template_default"),
            },
            qc_required=["Avoid primary-amine buffers and minimize NHS ester hold time."],
        ),
        ProcessStep(
            name="Protein A coupling to NHS ester",
            stage=LifecycleStage.M2_FUNCTIONALIZATION,
            kind=ProcessStepKind.COUPLE_LIGAND,
            parameters={
                "reagent_key": "protein_a_nhs_coupling",
                "pH": _q(7.5, "1", "template_default"),
                "temperature": _q(4.0, "degC", "template_default"),
                "time": _q(4.0, "h", "template_default"),
                "reagent_concentration": _q(0.02, "mol/m3", "template_default"),
            },
            qc_required=["Measure ligand density, residual free protein, and activity retention."],
        ),
        _wash("Wash after NHS coupling", "nhs_ester", temperature_c=4.0),
        _storage_exchange("nhs_ester"),
    ]


def hydrazide_protein_a_template() -> list[ProcessStep]:
    """Epoxide hydrazide insertion followed by aldehyde/glycan Protein A capture."""

    return [
        epoxy_protein_a_template()[0],
        ProcessStep(
            name="Hydrazide spacer insertion",
            stage=LifecycleStage.M2_FUNCTIONALIZATION,
            kind=ProcessStepKind.INSERT_SPACER,
            parameters={
                "reagent_key": "hydrazide_spacer_arm",
                "pH": _q(9.5, "1", "template_default"),
                "temperature": _q(25.0, "degC", "template_default"),
                "time": _q(4.0, "h", "template_default"),
                "reagent_concentration": _q(50.0, "mol/m3", "template_default"),
            },
            qc_required=["Confirm hydrazide density before aldehyde/protein coupling."],
        ),
        _wash("Wash after hydrazide spacer insertion", "hydrazide"),
        ProcessStep(
            name="Oxidized Protein A coupling to hydrazide",
            stage=LifecycleStage.M2_FUNCTIONALIZATION,
            kind=ProcessStepKind.COUPLE_LIGAND,
            parameters={
                "reagent_key": "protein_a_hydrazide_coupling",
                "pH": _q(5.5, "1", "template_default"),
                "temperature": _q(4.0, "degC", "template_default"),
                "time": _q(16.0, "h", "template_default"),
                "reagent_concentration": _q(0.02, "mol/m3", "template_default"),
            },
            qc_required=["Measure ligand density, leaching, and retained Fc binding activity."],
        ),
        _wash("Wash after hydrazide Protein A coupling", "hydrazide", temperature_c=4.0),
        _storage_exchange("hydrazide"),
    ]


def vinyl_sulfone_protein_a_template() -> list[ProcessStep]:
    """DVS activation followed by Protein A coupling and thiol quench."""

    return [
        ProcessStep(
            name="DVS activation of hydroxyl groups",
            stage=LifecycleStage.M2_FUNCTIONALIZATION,
            kind=ProcessStepKind.ACTIVATE,
            parameters={
                "reagent_key": "dvs_activation",
                "pH": _q(12.0, "1", "template_default"),
                "temperature": _q(25.0, "degC", "template_default"),
                "time": _q(2.0, "h", "template_default"),
                "reagent_concentration": _q(50.0, "mol/m3", "template_default"),
            },
            qc_required=["Confirm vinyl sulfone activation and avoid nucleophilic buffer carryover."],
        ),
        _wash("Wash after DVS activation", "vinyl_sulfone"),
        ProcessStep(
            name="Protein A coupling to vinyl sulfone",
            stage=LifecycleStage.M2_FUNCTIONALIZATION,
            kind=ProcessStepKind.COUPLE_LIGAND,
            parameters={
                "reagent_key": "protein_a_vs_coupling",
                "pH": _q(8.5, "1", "template_default"),
                "temperature": _q(4.0, "degC", "template_default"),
                "time": _q(8.0, "h", "template_default"),
                "reagent_concentration": _q(0.02, "mol/m3", "template_default"),
            },
            qc_required=["Measure free Protein A in wash fractions and retained activity."],
        ),
        ProcessStep(
            name="Block residual vinyl sulfone groups",
            stage=LifecycleStage.M2_FUNCTIONALIZATION,
            kind=ProcessStepKind.BLOCK_OR_QUENCH,
            parameters={
                "reagent_key": "mercaptoethanol_quench",
                "pH": _q(6.5, "1", "template_default"),
                "temperature": _q(25.0, "degC", "template_default"),
                "time": _q(1.0, "h", "template_default"),
                "reagent_concentration": _q(100.0, "mol/m3", "template_default"),
            },
        ),
        _wash("Final wash after vinyl sulfone block", "vinyl_sulfone", hours=2.0),
        _storage_exchange("vinyl_sulfone"),
    ]


def nta_imac_template() -> list[ProcessStep]:
    """ECH activation, NTA coupling, nickel charging, and storage exchange."""

    return [
        epoxy_protein_a_template()[0],
        ProcessStep(
            name="NTA chelator coupling",
            stage=LifecycleStage.M2_FUNCTIONALIZATION,
            kind=ProcessStepKind.COUPLE_LIGAND,
            parameters={
                "reagent_key": "nta_coupling",
                "pH": _q(10.5, "1", "template_default"),
                "temperature": _q(25.0, "degC", "template_default"),
                "time": _q(6.0, "h", "template_default"),
                "reagent_concentration": _q(50.0, "mol/m3", "template_default"),
            },
            qc_required=["Measure chelator density before metal charging."],
        ),
        _wash("Wash after NTA coupling", "epoxide"),
        ProcessStep(
            name="Nickel charge NTA sites",
            stage=LifecycleStage.M2_FUNCTIONALIZATION,
            kind=ProcessStepKind.METAL_CHARGE,
            parameters={
                "reagent_key": "nickel_charging_nta",
                "pH": _q(7.0, "1", "template_default"),
                "temperature": _q(25.0, "degC", "template_default"),
                "time": _q(0.5, "h", "template_default"),
                "reagent_concentration": _q(50.0, "mol/m3", "template_default"),
            },
            qc_required=["Measure metal loading and metal leaching risk."],
        ),
        _storage_exchange("nta"),
    ]


def ida_imac_template() -> list[ProcessStep]:
    """ECH activation, IDA coupling, nickel charging, and storage exchange."""

    steps = nta_imac_template()
    steps[1] = ProcessStep(
        name="IDA chelator coupling",
        stage=LifecycleStage.M2_FUNCTIONALIZATION,
        kind=ProcessStepKind.COUPLE_LIGAND,
        parameters={
            "reagent_key": "ida_coupling",
            "pH": _q(10.5, "1", "template_default"),
            "temperature": _q(25.0, "degC", "template_default"),
            "time": _q(6.0, "h", "template_default"),
            "reagent_concentration": _q(50.0, "mol/m3", "template_default"),
        },
        qc_required=["Measure chelator density before metal charging."],
    )
    steps[3] = ProcessStep(
        name="Nickel charge IDA sites",
        stage=LifecycleStage.M2_FUNCTIONALIZATION,
        kind=ProcessStepKind.METAL_CHARGE,
        parameters={
            "reagent_key": "nickel_charging_ida",
            "pH": _q(7.0, "1", "template_default"),
            "temperature": _q(25.0, "degC", "template_default"),
            "time": _q(0.5, "h", "template_default"),
            "reagent_concentration": _q(50.0, "mol/m3", "template_default"),
        },
        qc_required=["Measure metal loading and metal leaching risk."],
    )
    steps[4] = _storage_exchange("ida")
    return steps


_TEMPLATES: dict[str, Callable[[], list[ProcessStep]]] = {
    "epoxy_protein_a": epoxy_protein_a_template,
    "edc_nhs_protein_a": edc_nhs_protein_a_template,
    "hydrazide_protein_a": hydrazide_protein_a_template,
    "vinyl_sulfone_protein_a": vinyl_sulfone_protein_a_template,
    "nta_imac": nta_imac_template,
    "ida_imac": ida_imac_template,
}


def available_m2_templates() -> tuple[str, ...]:
    """Return stable names for the built-in M2 stage templates."""

    return tuple(sorted(_TEMPLATES))


def m2_template_steps(name: str) -> list[ProcessStep]:
    """Return a deep-copied M2 template by stable name."""

    key = name.strip().lower()
    if key not in _TEMPLATES:
        raise KeyError(f"Unknown M2 template {name!r}; available={available_m2_templates()}")
    return copy.deepcopy(_TEMPLATES[key]())
