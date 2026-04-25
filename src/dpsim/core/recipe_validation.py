"""First-principles validation guardrails for ProcessRecipe.

Reference: docs/performance_recipe_protocol.md, Module M3 (A3).

The lifecycle orchestrator calls ``validate_recipe_first_principles`` before
``resolve_lifecycle_inputs`` to reject scientifically invalid recipes at the
entry point — recipes that the existing per-stage validation tolerates but
which the scientific-advisor flags as unable to produce decision-grade output.

Four guardrails (numbered per the scientific-advisor's audit §3):

  G1: M1 wash mass-balance closure — predicted residual oil after wash must
      not exceed the target's ``max_residual_oil_volume_fraction``.
  G3: Elute ``gradient_field`` ↔ isotherm ``gradient_field`` consistency —
      a recipe that declares e.g. ``gradient_field="ph"`` cannot be safely
      run with a competitive Langmuir isotherm whose ``gradient_sensitive``
      is False.
  G4: Polymer-family × reagent compatibility — recipes that pair ECH on
      alginate, glutaraldehyde on cellulose, etc. are scientifically
      infeasible and should be blocked at the recipe layer (added v0.3.0
      via B1).
  G5: Surface-area inheritance — when an FMC is supplied, the M3 capacity
      claim is only quantitative when ``ligand_accessible_area`` is at least
      10 % of ``reagent_accessible_area``.

Guardrail 2 (pH/pKa window) is deferred to v0.4.0+.
"""

from __future__ import annotations

from typing import Any

from .process_recipe import (
    LifecycleStage,
    ProcessRecipe,
    ProcessStep,
    ProcessStepKind,
)
from .quantities import Quantity
from .validation import ValidationReport, ValidationSeverity

# G1 — wash mass-balance gate constants
_MIN_WASH_MIXING_EFFICIENCY = 1e-6  # avoid (1 − 0)^N short-circuiting

# G5 — ligand-accessibility gate threshold (per scientific-advisor §3)
_LIGAND_ACCESSIBILITY_FLOOR = 0.10


def validate_recipe_first_principles(
    recipe: ProcessRecipe,
    *,
    isotherm: Any | None = None,
    fmc: Any | None = None,
) -> ValidationReport:
    """Apply first-principles guardrails to a ProcessRecipe.

    Each guardrail is evaluated only when its inputs are present; missing
    inputs yield no issue, so the function is safe to call at any stage of
    the lifecycle pipeline (pre-resolution with ``recipe`` only, or
    post-resolution with ``isotherm`` + ``fmc`` supplied).

    Args:
        recipe: ProcessRecipe to inspect.
        isotherm: Optional resolved isotherm (any class with
            ``gradient_sensitive: bool`` and ``gradient_field: str``
            properties — e.g. ``ProteinAIsotherm``, ``HICIsotherm``,
            ``CompetitiveLangmuirIsotherm``).
        fmc: Optional resolved FunctionalMediaContract carrying
            ``ligand_accessible_area_per_bed_volume`` and
            ``reagent_accessible_area_per_bed_volume`` fields.

    Returns:
        ValidationReport with BLOCKER and WARNING issues.
    """
    report = ValidationReport()
    _g1_wash_mass_balance(recipe, report)
    _g3_gradient_field_isotherm(recipe, isotherm, report)
    _g4_family_reagent_compatibility(recipe, report)
    _g5_surface_area_inheritance(fmc, report)
    return report


# ─── G1 — M1 wash mass-balance closure ───────────────────────────────────────


def _g1_wash_mass_balance(
    recipe: ProcessRecipe,
    report: ValidationReport,
) -> None:
    """Predicted residual oil after wash vs target maximum.

    Mass-balance approximation:
        residual = initial_oil × (1 − mixing_efficiency × retention⁻¹)^cycles

    Where ``retention`` lumps oil-phase persistence into a single number
    (matches recipe_resolver convention). When ``mixing_efficiency`` is 0,
    the wash does nothing and the residual equals ``initial_oil``.
    """
    cool_step = _first_step(recipe, LifecycleStage.M1_FABRICATION, ProcessStepKind.COOL_OR_GEL)
    if cool_step is None:
        return
    initial_oil = _qty_value(cool_step.parameters.get("initial_oil_carryover_fraction"))
    if initial_oil is None:
        return
    wash_cycles = _qty_value(cool_step.parameters.get("wash_cycles"))
    mixing_eff = _qty_value(cool_step.parameters.get("wash_mixing_efficiency"))
    retention = _qty_value(cool_step.parameters.get("oil_retention_factor")) or 1.0
    target = _qty_value(recipe.target.max_residual_oil_volume_fraction)
    if target is None or wash_cycles is None or mixing_eff is None:
        return
    eff = max(min(mixing_eff / max(retention, 1e-9), 1.0), 0.0)
    residual = initial_oil * (1.0 - eff) ** max(wash_cycles, 0.0)
    if residual <= target:
        return
    if residual > 5.0 * target:
        report.add(
            ValidationSeverity.BLOCKER,
            "FP_G1_WASH_INADEQUATE",
            (
                f"Predicted residual oil fraction {residual:.4g} exceeds target "
                f"{target:.4g} by more than 5×. Wash sequence is mass-balance-"
                "infeasible for the declared target."
            ),
            module="M1",
            recommendation=(
                "Increase wash_cycles, raise wash_mixing_efficiency, lower "
                "oil_retention_factor, or relax target.max_residual_oil_volume_fraction."
            ),
        )
    else:
        report.add(
            ValidationSeverity.WARNING,
            "FP_G1_WASH_MARGINAL",
            (
                f"Predicted residual oil fraction {residual:.4g} exceeds target "
                f"{target:.4g}. Result will pass through but downstream M2/M3 "
                "claims should be tier-downgraded."
            ),
            module="M1",
            recommendation="Add a wash cycle or measure residual oil before relying on M3 numbers.",
        )


# ─── G3 — gradient_field ↔ isotherm consistency ──────────────────────────────


def _g3_gradient_field_isotherm(
    recipe: ProcessRecipe,
    isotherm: Any | None,
    report: ValidationReport,
) -> None:
    """Recipe-declared gradient_field must match isotherm capability."""
    elute_steps = [
        s
        for s in recipe.steps_for_stage(LifecycleStage.M3_PERFORMANCE)
        if s.kind == ProcessStepKind.ELUTE
    ]
    if not elute_steps:
        return
    elute = elute_steps[0]
    raw = elute.parameters.get("gradient_field", "")
    declared = str(raw).strip() if isinstance(raw, str) else ""
    if not declared:
        return
    if isotherm is None:
        # Recipe declares intent; isotherm not yet resolved. Defer with INFO-
        # equivalent WARNING (BLOCKER would be premature).
        report.add(
            ValidationSeverity.WARNING,
            "FP_G3_GRADIENT_FIELD_DEFERRED",
            (
                f"Elute step declares gradient_field={declared!r} but no isotherm "
                "was supplied to the validator. Compatibility will be checked "
                "after isotherm resolution."
            ),
            module="M3",
        )
        return
    isotherm_field = str(getattr(isotherm, "gradient_field", "")).strip()
    is_sensitive = bool(getattr(isotherm, "gradient_sensitive", False))
    if not is_sensitive:
        report.add(
            ValidationSeverity.BLOCKER,
            "FP_G3_ISOTHERM_NOT_GRADIENT_SENSITIVE",
            (
                f"Elute step declares gradient_field={declared!r} but isotherm "
                f"{type(isotherm).__name__} is not gradient-sensitive. The "
                "gradient program would run but the binding equilibrium would "
                "not respond."
            ),
            module="M3",
            recommendation=(
                "Use ProteinAIsotherm (pH), HICIsotherm/SMA (salt), "
                "IMACCompetitionIsotherm (imidazole), or remove gradient_field."
            ),
        )
        return
    if isotherm_field and isotherm_field != declared:
        report.add(
            ValidationSeverity.BLOCKER,
            "FP_G3_GRADIENT_FIELD_MISMATCH",
            (
                f"Elute step declares gradient_field={declared!r} but isotherm "
                f"{type(isotherm).__name__} responds to {isotherm_field!r}."
            ),
            module="M3",
            recommendation=(
                f"Change recipe gradient_field to {isotherm_field!r}, or pick an "
                "isotherm that responds to the recipe's gradient field."
            ),
        )


# ─── G4 — polymer-family × reagent compatibility ────────────────────────────


def _g4_family_reagent_compatibility(
    recipe: ProcessRecipe,
    report: ValidationReport,
) -> None:
    """BLOCK incompatible (polymer family, reagent) combinations.

    Reads ``recipe.material_batch.polymer_family`` (a string) and resolves it
    against ``PolymerFamily`` enum values. For each M2 process step that
    declares a ``reagent_key``, looks up the family-reagent matrix and emits
    a BLOCKER on ``incompatible`` or a WARNING on ``qualitative_only``.
    Unknown matrix entries are silently passed through.
    """
    from dpsim.datatypes import PolymerFamily
    from dpsim.module2_functionalization.family_reagent_matrix import (
        check_family_reagent_compatibility,
    )

    family_raw = (recipe.material_batch.polymer_family or "").strip().lower()
    if not family_raw:
        return
    try:
        family = PolymerFamily(family_raw)
    except ValueError:
        return  # Unknown polymer family string — skip the check.

    for step in recipe.steps_for_stage(LifecycleStage.M2_FUNCTIONALIZATION):
        reagent_key = str(step.parameters.get("reagent_key", "")).strip()
        if not reagent_key:
            continue
        entry = check_family_reagent_compatibility(family, reagent_key)
        if entry is None:
            continue
        if entry.compatibility == "incompatible":
            report.add(
                ValidationSeverity.BLOCKER,
                "FP_G4_FAMILY_REAGENT_INCOMPATIBLE",
                (
                    f"Step {step.name!r}: reagent {reagent_key!r} is "
                    f"incompatible with polymer family {family.value!r}. "
                    f"Rationale: {entry.rationale}"
                ),
                module="M2",
                recommendation=(
                    "Remove this step, switch to a compatible reagent, or "
                    "change the polymer family."
                ),
            )
        elif entry.compatibility == "qualitative_only":
            report.add(
                ValidationSeverity.WARNING,
                "FP_G4_FAMILY_REAGENT_QUALITATIVE",
                (
                    f"Step {step.name!r}: reagent {reagent_key!r} on polymer "
                    f"family {family.value!r} is qualitative-only. "
                    f"Rationale: {entry.rationale}"
                ),
                module="M2",
                recommendation=(
                    "Calibrate against a static-binding or coupling-yield "
                    "assay before treating M2/M3 numbers as quantitative."
                ),
            )


# ─── G5 — surface-area inheritance ───────────────────────────────────────────


def _g5_surface_area_inheritance(
    fmc: Any | None,
    report: ValidationReport,
) -> None:
    """FMC ligand accessibility floor — gate quantitative M3 capacity claims."""
    if fmc is None:
        return
    reagent = _safe_float(getattr(fmc, "reagent_accessible_area_per_bed_volume", 0.0))
    ligand = _safe_float(getattr(fmc, "ligand_accessible_area_per_bed_volume", 0.0))
    if reagent <= 0.0:
        return
    ratio = ligand / reagent
    if ratio >= _LIGAND_ACCESSIBILITY_FLOOR:
        return
    report.add(
        ValidationSeverity.WARNING,
        "FP_G5_LIGAND_ACCESSIBILITY_LOW",
        (
            f"FMC ligand-accessible area is {ratio:.1%} of reagent-accessible "
            f"area (floor is {_LIGAND_ACCESSIBILITY_FLOOR:.0%}). M3 q_max claims "
            "should be tier-downgraded to ranking-only."
        ),
        module="M3",
        recommendation=(
            "Calibrate ligand density against a static-binding assay before "
            "interpreting M3 DBC numerically."
        ),
    )


# ─── helpers ─────────────────────────────────────────────────────────────────


def _first_step(
    recipe: ProcessRecipe,
    stage: LifecycleStage,
    kind: ProcessStepKind,
) -> ProcessStep | None:
    for step in recipe.steps_for_stage(stage):
        if step.kind == kind:
            return step
    return None


def _qty_value(parameter: Any) -> float | None:
    """Coerce a recipe parameter (Quantity / float / int / None) into a float.

    Quantities are read as their declared magnitude (no unit conversion). The
    guardrails that depend on units are dimensionless fractions, so this is
    safe for the current G1/G5 scope.
    """
    if parameter is None:
        return None
    if isinstance(parameter, Quantity):
        return float(parameter.value)
    if isinstance(parameter, (int, float)):
        return float(parameter)
    return None


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


__all__ = ["validate_recipe_first_principles"]
