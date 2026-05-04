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
    _g6_acs_converter_sequence(recipe, report)
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


# ─── G6 — ACS Converter sequence FSM (v0.5.0) ───────────────────────────────


# Reagent keys that install AMINE_DISTAL on the matrix via the SPACER_ARM step.
# Used by G6 to verify that arm-distal activations have a viable substrate.
_AMINE_ARM_REAGENT_KEYS: frozenset[str] = frozenset({
    "eda_spacer_arm",
    "dadpa_spacer_arm",
    "dah_spacer_arm",
    "aha_spacer",
    "oligoglycine_spacer",
    "cystamine_disulfide_spacer",
})

# Reagent keys whose target ACS is an arm-distal nucleophile, requiring a
# prior INSERT_SPACER step (or a polymer family with native amine-distal
# accessibility, e.g. chitosan-bearing).
_ARM_DISTAL_ACTIVATOR_KEYS: frozenset[str] = frozenset({
    "pyridyl_disulfide_activation",
})

# Aldehyde-producing converters that require NaBH4 reductive lock-in when the
# target's cip_required=True. The check is for the presence of any reductive
# quench reagent in the M2 step list following the converter.
_ALDEHYDE_CONVERTER_KEYS: frozenset[str] = frozenset({
    "glyoxyl_chained_activation",
    "periodate_oxidation",
})
_REDUCTIVE_QUENCH_KEYS: frozenset[str] = frozenset({
    "nabh4_quench",
})

# Polymer families with native amine accessibility — pyridyl-disulfide can
# install without an explicit INSERT_SPACER step on these.
_NATIVE_AMINE_FAMILIES: frozenset[str] = frozenset({
    "agarose_chitosan",
    "chitosan",
    "alginate_chitosan",
    "pectin_chitosan",
})


def _g6_acs_converter_sequence(
    recipe: ProcessRecipe,
    report: ValidationReport,
) -> None:
    """Enforce the canonical ACS-Converter → Arm → Ligand → Ion-charging FSM.

    Six checks, all run against ``recipe.steps_for_stage(M2_FUNCTIONALIZATION)``:

      G6.1 Step ordering — ACTIVATE (or ACS-conversion equivalent) must precede
           INSERT_SPACER, which must precede COUPLE_LIGAND, which must precede
           METAL_CHARGE. Skips are allowed (direct-coupling ligands skip arm;
           non-IMAC ligands skip metal charging).
      G6.2 Arm-distal activator precondition — pyridyl_disulfide_activation
           requires a prior INSERT_SPACER step using an amine spacer, OR a
           polymer family with native amine accessibility.
      G6.3 Metal-charge precondition — METAL_CHARGE requires a prior
           COUPLE_LIGAND step. (The ligand-class match against NTA/IDA is
           caller-side; here we enforce only the ordering.)
      G6.4 CIP reductive lock-in — when target.cip_required=True, an aldehyde
           converter (glyoxyl_chained_activation, periodate_oxidation) requires
           a downstream NaBH4 reductive quench. BLOCKER otherwise.
      G6.5 CNBr coupling-window — CNBr activation immediately followed by a
           coupling step >15 min later (>900 s) emits a hydrolysis-loss WARNING.
           Wet-lab cyanate-ester half-life is ~5 min.
      G6.6 ACS_CONVERSION duplicate-without-context — two consecutive
           ACS conversions with no intervening wash/quench step is a
           sequence smell (Cyanuric chloride staged substitution is the
           accepted exception; it is silently allowed). Other paired
           converters emit WARNING.
    """
    steps = list(recipe.steps_for_stage(LifecycleStage.M2_FUNCTIONALIZATION))
    if not steps:
        return

    # Materialise the kind-and-reagent timeline once.
    timeline: list[tuple[int, ProcessStep, ProcessStepKind, str]] = []
    for idx, step in enumerate(steps):
        rkey = str(step.parameters.get("reagent_key", "")).strip()
        timeline.append((idx, step, step.kind, rkey))

    # G6.1 — ordering check.
    # v0.5.2 (codex P2-1 fix): ARM_ACTIVATE has phase rank 3 (after
    # rank-2 INSERT_SPACER, before rank-4 COUPLE_LIGAND). Recipes that
    # encode pyridyl-disulfide as the legacy ACTIVATE kind (pre-v0.5.2)
    # get the same treatment via the reagent-key override below, so
    # existing recipes don't start failing G6.1 once ARM_ACTIVATE lands.
    _phase_rank: dict[ProcessStepKind, int] = {
        ProcessStepKind.ACTIVATE: 1,
        ProcessStepKind.INSERT_SPACER: 2,
        ProcessStepKind.ARM_ACTIVATE: 3,
        ProcessStepKind.COUPLE_LIGAND: 4,
        ProcessStepKind.METAL_CHARGE: 5,
    }
    last_rank = 0
    for idx, step, kind, rkey in timeline:
        rank = _phase_rank.get(kind)
        # v0.5.2 (codex P2-1): backward-compat — if a step is encoded with
        # ProcessStepKind.ACTIVATE but its reagent_key is an arm-distal
        # activator, treat it as phase 3 (post-arm). This rescues legacy
        # recipes that used the only kind available before ARM_ACTIVATE
        # was added.
        if rank == 1 and rkey in _ARM_DISTAL_ACTIVATOR_KEYS:
            rank = 3
        if rank is None:
            continue
        if rank < last_rank:
            report.add(
                ValidationSeverity.BLOCKER,
                "FP_G6_SEQUENCE_OUT_OF_ORDER",
                (
                    f"Step {step.name!r} (kind={kind.value!r}) appears AFTER a "
                    f"later-phase step. Required order: ACTIVATE → INSERT_SPACER "
                    f"→ ARM_ACTIVATE → COUPLE_LIGAND → METAL_CHARGE."
                ),
                module="M2",
                recommendation=(
                    "Reorder M2 steps to follow the converter→arm→ligand→ion-"
                    "charging convention."
                ),
            )
        last_rank = max(last_rank, rank)

    # G6.2 — arm-distal activator precondition.
    family_raw = (recipe.material_batch.polymer_family or "").strip().lower()
    has_native_amine = family_raw in _NATIVE_AMINE_FAMILIES
    for idx, step, kind, rkey in timeline:
        if rkey not in _ARM_DISTAL_ACTIVATOR_KEYS:
            continue
        # Compute whether amine was installed BEFORE this step.
        amine_arm_before = any(
            j_kind == ProcessStepKind.INSERT_SPACER
            and j_rkey in _AMINE_ARM_REAGENT_KEYS
            for j_idx, _, j_kind, j_rkey in timeline
            if j_idx < idx
        )
        if not amine_arm_before and not has_native_amine:
            report.add(
                ValidationSeverity.BLOCKER,
                "FP_G6_ARM_DISTAL_PRECONDITION",
                (
                    f"Step {step.name!r}: reagent {rkey!r} requires either a "
                    f"prior INSERT_SPACER step with an amine spacer, or a "
                    f"polymer family with native amine accessibility "
                    f"(chitosan-bearing). Family is {family_raw!r}; arm "
                    f"installed before this step: {amine_arm_before}."
                ),
                module="M2",
                recommendation=(
                    "Insert a SPACER_ARM step (e.g. eda_spacer_arm or "
                    "cystamine_disulfide_spacer) before the arm-distal "
                    "activation, or switch to a chitosan-bearing family."
                ),
            )
        elif (
            not amine_arm_before
            and has_native_amine
            and any(
                j_idx > idx and j_kind == ProcessStepKind.COUPLE_LIGAND
                for j_idx, _, j_kind, _ in timeline
            )
        ):
            # Native-amine path is qualitative — surface the caveat.
            report.add(
                ValidationSeverity.WARNING,
                "FP_G6_ARM_DISTAL_NATIVE_AMINE",
                (
                    f"Step {step.name!r}: reagent {rkey!r} runs on native "
                    f"matrix amine ({family_raw!r}); coupling density depends "
                    f"on the family's accessible -NH2 surface, not on a "
                    "calibrated spacer length."
                ),
                module="M2",
                recommendation=(
                    "Treat downstream M3 capacity numbers as ranking-only "
                    "unless calibrated against a static-binding assay."
                ),
            )

    # G6.3 — metal-charge precondition.
    coupled_before_metal = False
    for idx, step, kind, _ in timeline:
        if kind == ProcessStepKind.COUPLE_LIGAND:
            coupled_before_metal = True
        elif kind == ProcessStepKind.METAL_CHARGE and not coupled_before_metal:
            report.add(
                ValidationSeverity.BLOCKER,
                "FP_G6_METAL_CHARGE_NO_LIGAND",
                (
                    f"Step {step.name!r}: METAL_CHARGE requires a prior "
                    f"COUPLE_LIGAND step that installed an NTA or IDA chelator."
                ),
                module="M2",
                recommendation=(
                    "Insert an NTA/IDA chelator coupling step (nta_coupling, "
                    "ida_coupling) before metal charging."
                ),
            )

    # G6.4 — CIP reductive lock-in.
    cip_required = bool(getattr(recipe.target, "cip_required", False))
    if cip_required:
        aldehyde_converter_indices = [
            idx for idx, _, _, rkey in timeline if rkey in _ALDEHYDE_CONVERTER_KEYS
        ]
        for ald_idx in aldehyde_converter_indices:
            has_reductive_quench_after = any(
                j_idx > ald_idx and j_rkey in _REDUCTIVE_QUENCH_KEYS
                for j_idx, _, _, j_rkey in timeline
            )
            if not has_reductive_quench_after:
                step = timeline[ald_idx][1]
                report.add(
                    ValidationSeverity.BLOCKER,
                    "FP_G6_CIP_REDUCTIVE_LOCK_IN",
                    (
                        f"Step {step.name!r}: aldehyde-producing converter "
                        f"requires a downstream NaBH4 reductive quench when "
                        f"target.cip_required=True. CIP cycles will hydrolyse "
                        f"unreduced Schiff bases."
                    ),
                    module="M2",
                    recommendation=(
                        "Add a QUENCH step with reagent_key='nabh4_quench' "
                        "after the aldehyde converter, or set "
                        "target.cip_required=False for a non-CIP resin."
                    ),
                )

    # G6.5 — CNBr coupling window.
    # Cyanate ester half-life at 4 °C / pH 11 is ~5 min (k ≈ 2e-3 /s),
    # so any gap between CNBr activation and the next ligand coupling
    # longer than 15 min wipes out essentially all activated sites
    # (Kohn & Wilchek 1981 Anal. Biochem. 115:375).
    _CNBR_WINDOW_S = 900.0  # 15 minutes
    for idx, step, _, rkey in timeline:
        if rkey != "cnbr_activation":
            continue
        # Find the next coupling step.
        next_couple = next(
            (
                (j_idx, j_step)
                for j_idx, j_step, j_kind, _ in timeline
                if j_idx > idx and j_kind == ProcessStepKind.COUPLE_LIGAND
            ),
            None,
        )
        if next_couple is None:
            report.add(
                ValidationSeverity.WARNING,
                "FP_G6_CNBR_NO_COUPLING_FOLLOWUP",
                (
                    f"Step {step.name!r}: CNBr activation has no downstream "
                    f"COUPLE_LIGAND step. Cyanate ester hydrolyses with "
                    f"k≈2e-3/s — couple within 15 min or the activator is wasted."
                ),
                module="M2",
            )
            continue
        # v0.5.1 — strengthened time-window check. Sum the durations of
        # all steps strictly between the converter and the next coupling.
        # The activation step's own duration is part of the activation
        # plateau (the activator is being consumed), so it does NOT count
        # against the post-activation hydrolysis window. If any step in
        # between lacks a "time" field we cannot quantify the gap and
        # fall back to the pre-existing structural WARNING.
        # v0.5.2 (codex P2-2 fix): use _qty_to_seconds so a recipe
        # declaring `Quantity(30, "min")` is treated as 1800 s, not 30 s.
        # The previous _qty_value() call dropped units silently and let
        # 30-min washes slip past the 15-min hydrolysis blocker.
        next_idx, next_step = next_couple
        intervening_time_s = 0.0
        time_quantified = True
        for j_idx, j_step, _, _ in timeline:
            if j_idx <= idx or j_idx >= next_idx:
                continue
            t = _qty_to_seconds(j_step.parameters.get("time"))
            if t is None:
                time_quantified = False
                break
            intervening_time_s += float(t)
        if time_quantified and intervening_time_s > _CNBR_WINDOW_S:
            report.add(
                ValidationSeverity.BLOCKER,
                "FP_G6_CNBR_HYDROLYSIS_LOSS",
                (
                    f"Step {step.name!r}: cumulative time between CNBr "
                    f"activation and next coupling step is "
                    f"{intervening_time_s / 60:.1f} min "
                    f"(>{_CNBR_WINDOW_S / 60:.0f} min limit). Cyanate "
                    f"ester half-life is ~5 min at 4 °C / pH 11; the "
                    f"activator is consumed by hydrolysis before ligand "
                    f"coupling can run."
                ),
                module="M2",
                recommendation=(
                    "Move CNBr activation immediately before the coupling "
                    "step (no intervening washes longer than ~10 min "
                    "total), or accept the hydrolysis loss as a "
                    "qualitative-only result."
                ),
            )
        elif time_quantified and intervening_time_s > 0.5 * _CNBR_WINDOW_S:
            report.add(
                ValidationSeverity.WARNING,
                "FP_G6_CNBR_WINDOW_AT_RISK",
                (
                    f"Step {step.name!r}: intervening duration "
                    f"{intervening_time_s / 60:.1f} min is approaching the "
                    f"15 min CNBr hydrolysis window. Cyanate-ester yield "
                    f"will be degraded by competing hydrolysis."
                ),
                module="M2",
            )

    # G6.6 — back-to-back converter smell (excluding cyanuric staging).
    prev_was_converter = False
    prev_rkey = ""
    for idx, step, kind, rkey in timeline:
        is_converter = (
            kind == ProcessStepKind.ACTIVATE
            and rkey
            in {
                "cnbr_activation",
                "cdi_activation",
                "tresyl_chloride_activation",
                "cyanuric_chloride_activation",
                "glyoxyl_chained_activation",
                "periodate_oxidation",
                "ech_activation",
                "dvs_activation",
            }
        )
        if is_converter and prev_was_converter and prev_rkey != rkey:
            # Staged cyanuric is allowed; flag any other adjacency.
            report.add(
                ValidationSeverity.WARNING,
                "FP_G6_BACK_TO_BACK_CONVERTERS",
                (
                    f"Step {step.name!r}: ACS converter {rkey!r} runs "
                    f"immediately after another converter {prev_rkey!r} with "
                    f"no intervening wash/quench. Verify this is intentional."
                ),
                module="M2",
            )
        prev_was_converter = is_converter
        prev_rkey = rkey


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


# v0.5.2 (codex P2-2 fix) — time-aware coercion. _qty_value() explicitly
# strips units, which is fine for dimensionless fractions but wrong for
# the CNBr 15-min coupling-window check in G6.5: a wash declared as
# Quantity(30, "min") was being treated as 30 seconds and bypassing the
# blocker.
#
# This mirrors the unit registry the rest of the codebase uses: seconds
# are the SI canonical, minutes and hours are the common lab variants
# the recipe DSL accepts.
_TIME_UNIT_TO_SECONDS: dict[str, float] = {
    "": 1.0,           # bare float / Quantity with empty unit -> assume seconds
    "s": 1.0,
    "sec": 1.0,
    "second": 1.0,
    "seconds": 1.0,
    "min": 60.0,
    "minute": 60.0,
    "minutes": 60.0,
    "h": 3600.0,
    "hr": 3600.0,
    "hour": 3600.0,
    "hours": 3600.0,
    "ms": 1e-3,
    "millisecond": 1e-3,
}


def _qty_to_seconds(parameter: Any) -> float | None:
    """Coerce a duration parameter to seconds, honouring the unit field.

    Returns None if the parameter is missing OR carries a unit that is not
    in the known time-unit registry (callers can decide whether to treat
    that as 'unknown' and skip the check, or as 'invalid' and raise).
    """
    if parameter is None:
        return None
    if isinstance(parameter, Quantity):
        unit = (getattr(parameter, "unit", "") or "").strip().lower()
        factor = _TIME_UNIT_TO_SECONDS.get(unit)
        if factor is None:
            return None  # Unknown unit — caller decides how to handle.
        return float(parameter.value) * factor
    if isinstance(parameter, (int, float)):
        # Bare number — assume seconds (the SI canonical for this code path).
        return float(parameter)
    return None


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


__all__ = ["validate_recipe_first_principles"]
