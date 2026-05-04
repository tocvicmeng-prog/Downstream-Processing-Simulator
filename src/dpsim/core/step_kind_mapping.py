"""Single source of truth for the ProcessStepKind ↔ ModificationStepType
↔ reaction_type allowlist mapping (B-1e / W-005, v0.6.4).

Closes joint-audit MAJOR-2: prior to v0.6.4 the mapping was scattered
across ``recipe_resolver._step_type_from_process_kind`` (kind → step_type)
and ``orchestrator._STEP_ALLOWED_REACTION_TYPES`` (step_type → reagent
reaction_type allowlist). Adding a new step kind required edits in both
places with no enforcement that every ``ProcessStepKind`` member resolved.

This module exposes one mapping table and a thin polymorphism wrapper for
``COUPLE_LIGAND`` (which dispatches to ``PROTEIN_COUPLING`` when the
reagent is a macromolecule, ``LIGAND_COUPLING`` otherwise). The regression
test in ``tests/core/test_step_kind_mapping.py`` asserts:

  * Every ``ProcessStepKind`` member is a key in
    ``PROCESS_KIND_TO_MODIFICATION_TYPE`` (no silent omission).
  * The wrapper returns the same value as the legacy
    ``recipe_resolver._step_type_from_process_kind`` for every kind +
    representative reagent combination (regression-safe refactor).
  * Every ``ModificationStepType`` member is a key in the orchestrator's
    reaction-type allowlist (no orphan step types).

Per the v9.3 enum-by-value rule (CLAUDE.md): all comparisons in this
module are by ``.value`` semantics implicitly via dict-key equality, which
is the official recipe-validated pattern that survives Streamlit
``importlib.reload``.
"""

from __future__ import annotations

from typing import Optional

from dpsim.core.process_recipe import ProcessStepKind
from dpsim.module2_functionalization.modification_steps import ModificationStepType


# ─── Kind groupings (re-exports for the recipe_resolver) ─────────────────────
#
# The wash and quench kinds collapse into a single ModificationStepType
# (WASHING and QUENCHING respectively). Exposing the sets here so downstream
# code does not duplicate the membership decision.

M1_KINDS: frozenset[ProcessStepKind] = frozenset({
    ProcessStepKind.PREPARE_PHASE,
    ProcessStepKind.EMULSIFY,
    ProcessStepKind.COOL_OR_GEL,
})

M3_KINDS: frozenset[ProcessStepKind] = frozenset({
    ProcessStepKind.PACK_COLUMN,
    ProcessStepKind.EQUILIBRATE,
    ProcessStepKind.LOAD,
    ProcessStepKind.ELUTE,
    ProcessStepKind.REGENERATE,
    ProcessStepKind.ASSAY,
})

M2_WASH_KINDS: frozenset[ProcessStepKind] = frozenset({
    ProcessStepKind.WASH,
    ProcessStepKind.STORAGE_BUFFER_EXCHANGE,
})

M2_QUENCH_KINDS: frozenset[ProcessStepKind] = frozenset({
    ProcessStepKind.QUENCH,
    ProcessStepKind.BLOCK_OR_QUENCH,
})


# ─── The canonical mapping table ─────────────────────────────────────────────
#
# Every ProcessStepKind member MUST appear here. Members that do not trigger
# M2 chemistry (M1 fabrication, M3 chromatography) map to None.
#
# COUPLE_LIGAND maps to LIGAND_COUPLING by default; the polymorphism wrapper
# below substitutes PROTEIN_COUPLING when the reagent is a macromolecule.
# This is the ONLY context-dependent entry; everything else is one-to-one.
PROCESS_KIND_TO_MODIFICATION_TYPE: dict[
    ProcessStepKind, Optional[ModificationStepType]
] = {
    # M1 fabrication — physical operations, no M2 chemistry
    ProcessStepKind.PREPARE_PHASE: None,
    ProcessStepKind.EMULSIFY: None,
    ProcessStepKind.COOL_OR_GEL: None,
    # M2 functionalization chemistry
    ProcessStepKind.CROSSLINK: ModificationStepType.SECONDARY_CROSSLINKING,
    ProcessStepKind.ACTIVATE: ModificationStepType.ACTIVATION,
    ProcessStepKind.INSERT_SPACER: ModificationStepType.SPACER_ARM,
    ProcessStepKind.ARM_ACTIVATE: ModificationStepType.ARM_ACTIVATION,
    ProcessStepKind.COUPLE_LIGAND: ModificationStepType.LIGAND_COUPLING,
    ProcessStepKind.METAL_CHARGE: ModificationStepType.METAL_CHARGING,
    ProcessStepKind.PROTEIN_PRETREATMENT: ModificationStepType.PROTEIN_PRETREATMENT,
    ProcessStepKind.QUENCH: ModificationStepType.QUENCHING,
    ProcessStepKind.BLOCK_OR_QUENCH: ModificationStepType.QUENCHING,
    ProcessStepKind.WASH: ModificationStepType.WASHING,
    ProcessStepKind.STORAGE_BUFFER_EXCHANGE: ModificationStepType.WASHING,
    # M3 chromatography — handled by the M3 method/orchestrator, not M2
    ProcessStepKind.PACK_COLUMN: None,
    ProcessStepKind.EQUILIBRATE: None,
    ProcessStepKind.LOAD: None,
    ProcessStepKind.ELUTE: None,
    ProcessStepKind.REGENERATE: None,
    ProcessStepKind.ASSAY: None,
}


# ─── Polymorphism wrapper ────────────────────────────────────────────────────


def process_kind_to_modification_type(
    kind: ProcessStepKind,
    reagent_profile=None,
) -> Optional[ModificationStepType]:
    """Map a ProcessStepKind to its ModificationStepType, with COUPLE_LIGAND
    polymorphism.

    For most kinds the mapping is one-to-one (table lookup). The single
    exception is COUPLE_LIGAND: when the reagent is a protein / macromolecule
    (``reagent_profile.reaction_type == "protein_coupling"`` or
    ``reagent_profile.is_macromolecule``), the dispatch is
    PROTEIN_COUPLING instead of the default LIGAND_COUPLING.

    Args:
        kind: ProcessStepKind from the recipe.
        reagent_profile: ReagentProfile (or any object exposing
            ``reaction_type: str`` and ``is_macromolecule: bool``). Required
            only for COUPLE_LIGAND polymorphism; ignored for all other kinds.

    Returns:
        The mapped ModificationStepType, or None if ``kind`` has no
        M2-stage chemistry.
    """
    base = PROCESS_KIND_TO_MODIFICATION_TYPE.get(kind)
    if base != ModificationStepType.LIGAND_COUPLING:
        return base
    if reagent_profile is None:
        return base
    if (
        getattr(reagent_profile, "reaction_type", "") == "protein_coupling"
        or getattr(reagent_profile, "is_macromolecule", False)
    ):
        return ModificationStepType.PROTEIN_COUPLING
    return base


def is_m2_step_kind(kind: ProcessStepKind) -> bool:
    """True iff ``kind`` triggers M2-stage chemistry (non-None mapping)."""
    return PROCESS_KIND_TO_MODIFICATION_TYPE.get(kind) is not None


def get_allowed_reaction_types() -> dict[ModificationStepType, set[str]]:
    """Return a fresh copy of the orchestrator's reaction-type allowlist.

    Lazy import to avoid the recipe_validation → orchestrator → core cycle
    that would otherwise bite at module-load time.
    """
    from dpsim.module2_functionalization.orchestrator import (
        _STEP_ALLOWED_REACTION_TYPES,
    )
    return {k: set(v) for k, v in _STEP_ALLOWED_REACTION_TYPES.items()}


__all__ = [
    "M1_KINDS",
    "M2_QUENCH_KINDS",
    "M2_WASH_KINDS",
    "M3_KINDS",
    "PROCESS_KIND_TO_MODIFICATION_TYPE",
    "get_allowed_reaction_types",
    "is_m2_step_kind",
    "process_kind_to_modification_type",
]
