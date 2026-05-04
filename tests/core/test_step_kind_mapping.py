"""B-1e (W-005) regression: explicit ProcessStepKind ↔ ModificationStepType
mapping coverage.

Closes joint-audit MAJOR-2. Asserts the contract described in the docstring
of ``core/step_kind_mapping.py``:

  1. Every ``ProcessStepKind`` member is a key in
     ``PROCESS_KIND_TO_MODIFICATION_TYPE``.
  2. Every ``ModificationStepType`` value used in the mapping table is a
     real enum member (no typo / no orphan).
  3. ``process_kind_to_modification_type`` returns the same value as the
     legacy ``recipe_resolver._step_type_from_process_kind`` for every
     (kind, reagent-shape) combination — regression-safe refactor.
  4. Every ``ModificationStepType`` has a row in the orchestrator's
     reaction-type allowlist (no orphan step types).

The test will fail loudly the next time someone adds a ProcessStepKind
member without also extending the mapping table — exactly the failure
mode the audit was raised to prevent.
"""

from __future__ import annotations

import pytest

from dpsim.core.process_recipe import ProcessStepKind
from dpsim.core.step_kind_mapping import (
    PROCESS_KIND_TO_MODIFICATION_TYPE,
    get_allowed_reaction_types,
    is_m2_step_kind,
    process_kind_to_modification_type,
)
from dpsim.module2_functionalization.modification_steps import ModificationStepType


# ─── Coverage of every ProcessStepKind member ────────────────────────────────


@pytest.mark.parametrize("kind", list(ProcessStepKind))
def test_every_process_kind_in_mapping(kind):
    """Every ProcessStepKind member must be a key in the mapping table.

    This is the central audit-MAJOR-2 enforcement: silent omission was the
    failure mode that allowed v0.5.x recipes to dispatch incorrectly.
    """
    assert kind in PROCESS_KIND_TO_MODIFICATION_TYPE, (
        f"ProcessStepKind.{kind.name} is missing from "
        f"PROCESS_KIND_TO_MODIFICATION_TYPE — add it (with explicit None for "
        f"non-M2 kinds) in src/dpsim/core/step_kind_mapping.py."
    )


def test_mapping_values_are_real_enum_members():
    """Every non-None value in the mapping must be a ModificationStepType."""
    valid_values = {None, *ModificationStepType}
    for kind, value in PROCESS_KIND_TO_MODIFICATION_TYPE.items():
        assert value in valid_values, (
            f"PROCESS_KIND_TO_MODIFICATION_TYPE[{kind.name}] = {value!r} "
            f"is not a ModificationStepType member."
        )


# ─── Polymorphism wrapper ────────────────────────────────────────────────────


class _LigandReagent:
    """Small-molecule ligand reagent (LIGAND_COUPLING dispatch)."""
    reaction_type = "coupling"
    is_macromolecule = False


class _ProteinReagent:
    """Protein/macromolecule reagent (PROTEIN_COUPLING dispatch)."""
    reaction_type = "protein_coupling"
    is_macromolecule = True


class _MacromoleculeNonProteinReagent:
    """Non-protein macromolecule (PROTEIN_COUPLING via is_macromolecule)."""
    reaction_type = "coupling"
    is_macromolecule = True


class TestPolymorphism:
    """COUPLE_LIGAND dispatches based on reagent profile shape."""

    def test_couple_ligand_default_is_ligand_coupling(self):
        result = process_kind_to_modification_type(ProcessStepKind.COUPLE_LIGAND)
        assert result == ModificationStepType.LIGAND_COUPLING

    def test_couple_ligand_small_molecule_is_ligand_coupling(self):
        result = process_kind_to_modification_type(
            ProcessStepKind.COUPLE_LIGAND, reagent_profile=_LigandReagent()
        )
        assert result == ModificationStepType.LIGAND_COUPLING

    def test_couple_ligand_protein_is_protein_coupling(self):
        result = process_kind_to_modification_type(
            ProcessStepKind.COUPLE_LIGAND, reagent_profile=_ProteinReagent()
        )
        assert result == ModificationStepType.PROTEIN_COUPLING

    def test_couple_ligand_macromolecule_is_protein_coupling(self):
        """is_macromolecule=True alone (without protein_coupling reaction_type)
        must still trigger the PROTEIN_COUPLING dispatch."""
        result = process_kind_to_modification_type(
            ProcessStepKind.COUPLE_LIGAND,
            reagent_profile=_MacromoleculeNonProteinReagent(),
        )
        assert result == ModificationStepType.PROTEIN_COUPLING

    def test_non_couple_kind_ignores_reagent(self):
        """Non-COUPLE_LIGAND kinds must not be polymorphic on reagent."""
        result = process_kind_to_modification_type(
            ProcessStepKind.ACTIVATE, reagent_profile=_ProteinReagent()
        )
        assert result == ModificationStepType.ACTIVATION


# ─── Regression vs the legacy recipe_resolver helper ─────────────────────────


def _legacy_mapping(kind, reagent_profile=None):
    """Re-implementation of the pre-B-1e logic for parity testing.

    Frozen at the recipe_resolver._step_type_from_process_kind v0.6.3
    behaviour. Any divergence indicates a regression in the new module.
    """
    if kind == ProcessStepKind.CROSSLINK:
        return ModificationStepType.SECONDARY_CROSSLINKING
    if kind == ProcessStepKind.ACTIVATE:
        return ModificationStepType.ACTIVATION
    if kind == ProcessStepKind.INSERT_SPACER:
        return ModificationStepType.SPACER_ARM
    if kind == ProcessStepKind.COUPLE_LIGAND:
        if reagent_profile is None:
            return ModificationStepType.LIGAND_COUPLING
        if (
            getattr(reagent_profile, "reaction_type", "") == "protein_coupling"
            or getattr(reagent_profile, "is_macromolecule", False)
        ):
            return ModificationStepType.PROTEIN_COUPLING
        return ModificationStepType.LIGAND_COUPLING
    if kind == ProcessStepKind.METAL_CHARGE:
        return ModificationStepType.METAL_CHARGING
    if kind == ProcessStepKind.PROTEIN_PRETREATMENT:
        return ModificationStepType.PROTEIN_PRETREATMENT
    if kind in {ProcessStepKind.QUENCH, ProcessStepKind.BLOCK_OR_QUENCH}:
        return ModificationStepType.QUENCHING
    if kind in {ProcessStepKind.WASH, ProcessStepKind.STORAGE_BUFFER_EXCHANGE}:
        return ModificationStepType.WASHING
    return None


@pytest.mark.parametrize("kind", list(ProcessStepKind))
def test_no_reagent_matches_legacy(kind):
    """For every kind, calling without a reagent must match v0.6.3 behaviour.

    NOTE: B-1e adds explicit ARM_ACTIVATE → ARM_ACTIVATION which the legacy
    helper did not encode (it returned None, then fell into the orchestrator's
    silent pass). The new mapping is more correct; this test documents that
    intentional change rather than treating it as a regression.
    """
    if kind == ProcessStepKind.ARM_ACTIVATE:
        # Intentional B-1e improvement — mapping now explicit.
        assert process_kind_to_modification_type(kind) == ModificationStepType.ARM_ACTIVATION
        return
    legacy = _legacy_mapping(kind)
    new = process_kind_to_modification_type(kind)
    assert new == legacy, f"{kind.name}: legacy={legacy}, new={new}"


@pytest.mark.parametrize(
    "reagent",
    [_LigandReagent(), _ProteinReagent(), _MacromoleculeNonProteinReagent(), None],
    ids=["ligand", "protein", "macromolecule", "none"],
)
def test_couple_ligand_polymorphism_matches_legacy(reagent):
    legacy = _legacy_mapping(ProcessStepKind.COUPLE_LIGAND, reagent)
    new = process_kind_to_modification_type(
        ProcessStepKind.COUPLE_LIGAND, reagent_profile=reagent,
    )
    assert new == legacy


# ─── Allowlist coverage ──────────────────────────────────────────────────────


def test_every_modification_step_type_has_allowlist_row():
    """The orchestrator's reaction-type allowlist must cover every step type."""
    allowlist = get_allowed_reaction_types()
    missing = [
        st for st in ModificationStepType if st not in allowlist
    ]
    assert not missing, (
        f"ModificationStepType members missing from orchestrator's "
        f"_STEP_ALLOWED_REACTION_TYPES: {[m.name for m in missing]}. "
        f"Add them in src/dpsim/module2_functionalization/orchestrator.py."
    )


# ─── is_m2_step_kind accessor ────────────────────────────────────────────────


def test_is_m2_step_kind_classifies_correctly():
    # Sample of expected M2 kinds
    assert is_m2_step_kind(ProcessStepKind.ACTIVATE)
    assert is_m2_step_kind(ProcessStepKind.COUPLE_LIGAND)
    assert is_m2_step_kind(ProcessStepKind.QUENCH)
    # Sample of expected non-M2 kinds
    assert not is_m2_step_kind(ProcessStepKind.PREPARE_PHASE)
    assert not is_m2_step_kind(ProcessStepKind.LOAD)
    assert not is_m2_step_kind(ProcessStepKind.ELUTE)
