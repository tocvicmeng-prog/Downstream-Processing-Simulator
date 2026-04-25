"""Polymer-family × reagent compatibility matrix.

Reference: docs/handover/V0_2_0_PERFORMANCE_RECIPE_HANDOVER.md §9 (B1 protocol),
docs/dev_orchestrator_plan.md (B1).

Closes scientific-advisor §3 #4: today the lifecycle silently runs ECH on
alginate (no exposed -OH on gel surface), or EDC/NHS on PLGA (vanishing chain-
end -COOH density). Both produce QUALITATIVE_TREND tier results, which is
honest, but the UI lets the user construct the recipe at all. This matrix
encodes the chemical rationale as auditable data so ``validate_recipe_first_principles``
can BLOCK obviously-incompatible (family, reagent_key) combinations as
guardrail G4.

The matrix is intentionally conservative: when in doubt the entry is
``qualitative_only`` (warns) rather than ``incompatible`` (blocks). Wet-lab
counter-examples should be added as new ``compatible`` entries with citations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from dpsim.datatypes import PolymerFamily

Compatibility = Literal["compatible", "qualitative_only", "incompatible"]


@dataclass(frozen=True)
class FamilyReagentEntry:
    """One (polymer family, reagent_key) compatibility datum."""

    polymer_family: PolymerFamily
    reagent_key: str
    compatibility: Compatibility
    rationale: str


# Surface-chemistry assumptions (per scientific-advisor §3 #4):
# - AGAROSE_CHITOSAN: native -OH (agarose) + -NH2 (chitosan).
# - ALGINATE: native -COOH (guluronate/mannuronate) + -OH (ring-locked).
# - CELLULOSE: native -OH (3 per glucose unit), no native -COOH or -NH2.
# - PLGA: hydrophobic polyester; -OH and -COOH only at chain ends, very
#   low surface density relative to the inert bulk.

FAMILY_REAGENT_MATRIX: tuple[FamilyReagentEntry, ...] = (
    # ─── ECH activation (epoxide on -OH) ─────────────────────────────────
    FamilyReagentEntry(
        PolymerFamily.AGAROSE_CHITOSAN,
        "ech_activation",
        "compatible",
        "Agarose -OH is the canonical ECH substrate; chitosan -NH2 also reacts.",
    ),
    FamilyReagentEntry(
        PolymerFamily.ALGINATE,
        "ech_activation",
        "incompatible",
        "Alginate exposes -COOH on the gel surface; ring-locked -OH is inaccessible to ECH. Use carbodiimide on guluronate carboxyls instead.",
    ),
    FamilyReagentEntry(
        PolymerFamily.CELLULOSE,
        "ech_activation",
        "compatible",
        "Cellulose -OH (C2/C3/C6) is the standard ECH substrate; well established.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PLGA,
        "ech_activation",
        "incompatible",
        "PLGA exposes only chain-end -OH at very low density; epoxide activation yield is impractical.",
    ),
    # ─── DVS activation (vinyl sulfone on -OH / -NH2) ────────────────────
    FamilyReagentEntry(
        PolymerFamily.AGAROSE_CHITOSAN,
        "dvs_activation",
        "compatible",
        "Agarose -OH and chitosan -NH2 both react with DVS at pH 11-12.",
    ),
    FamilyReagentEntry(
        PolymerFamily.ALGINATE,
        "dvs_activation",
        "incompatible",
        "Same surface-OH inaccessibility as ECH. -COOH does not react with vinyl sulfone.",
    ),
    FamilyReagentEntry(
        PolymerFamily.CELLULOSE,
        "dvs_activation",
        "compatible",
        "Cellulose -OH reacts with DVS under alkaline conditions.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PLGA,
        "dvs_activation",
        "incompatible",
        "PLGA chain-end -OH density is too low for usable vinyl sulfone activation.",
    ),
    # ─── EDC/NHS activation (carbodiimide on -COOH) ──────────────────────
    FamilyReagentEntry(
        PolymerFamily.AGAROSE_CHITOSAN,
        "edc_nhs_activation",
        "qualitative_only",
        "Native A+C has no -COOH; EDC/NHS only meaningful after pre-carboxylation (e.g. AHA spacer or succinylation).",
    ),
    FamilyReagentEntry(
        PolymerFamily.ALGINATE,
        "edc_nhs_activation",
        "compatible",
        "Alginate guluronate -COOH is the native EDC/NHS substrate; standard carbodiimide chemistry.",
    ),
    FamilyReagentEntry(
        PolymerFamily.CELLULOSE,
        "edc_nhs_activation",
        "qualitative_only",
        "Native cellulose has no -COOH; EDC/NHS only meaningful after TEMPO oxidation or carboxymethylation.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PLGA,
        "edc_nhs_activation",
        "qualitative_only",
        "PLGA chain-end -COOH yields low ligand density; consider surface-modified (e.g. PLGA-PEG-COOH) variants.",
    ),
    # ─── Network crosslinkers (M1 chemistry, listed for completeness) ───
    FamilyReagentEntry(
        PolymerFamily.AGAROSE_CHITOSAN,
        "genipin_secondary",
        "compatible",
        "Genipin crosslinks chitosan -NH2 — canonical A+C secondary network.",
    ),
    FamilyReagentEntry(
        PolymerFamily.ALGINATE,
        "genipin_secondary",
        "incompatible",
        "Alginate has no -NH2; genipin requires primary amines.",
    ),
    FamilyReagentEntry(
        PolymerFamily.CELLULOSE,
        "genipin_secondary",
        "incompatible",
        "Cellulose has no -NH2; genipin requires primary amines.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PLGA,
        "genipin_secondary",
        "incompatible",
        "PLGA has no -NH2; genipin requires primary amines.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AGAROSE_CHITOSAN,
        "stmp_secondary",
        "compatible",
        "STMP forms phosphodiester bridges with agarose -OH and phosphoramide bridges with chitosan -NH2.",
    ),
    FamilyReagentEntry(
        PolymerFamily.ALGINATE,
        "stmp_secondary",
        "incompatible",
        "Alginate -COOH does not react with STMP under standard conditions.",
    ),
    FamilyReagentEntry(
        PolymerFamily.CELLULOSE,
        "stmp_secondary",
        "compatible",
        "Cellulose -OH reacts with STMP to form phosphodiester crosslinks.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PLGA,
        "stmp_secondary",
        "incompatible",
        "PLGA chain-end functional group density is too low for usable STMP crosslinking.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AGAROSE_CHITOSAN,
        "glutaraldehyde_secondary",
        "compatible",
        "Glutaraldehyde forms Schiff bases with chitosan -NH2; standard A+C crosslinker.",
    ),
    FamilyReagentEntry(
        PolymerFamily.ALGINATE,
        "glutaraldehyde_secondary",
        "incompatible",
        "Alginate has no -NH2; glutaraldehyde requires primary amines.",
    ),
    FamilyReagentEntry(
        PolymerFamily.CELLULOSE,
        "glutaraldehyde_secondary",
        "incompatible",
        "Cellulose has no -NH2; glutaraldehyde requires primary amines.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PLGA,
        "glutaraldehyde_secondary",
        "incompatible",
        "PLGA has no -NH2; glutaraldehyde requires primary amines.",
    ),
)


def _matrix_lookup() -> dict[tuple[PolymerFamily, str], FamilyReagentEntry]:
    return {(e.polymer_family, e.reagent_key): e for e in FAMILY_REAGENT_MATRIX}


_MATRIX_LOOKUP = _matrix_lookup()


def check_family_reagent_compatibility(
    polymer_family: PolymerFamily,
    reagent_key: str,
) -> FamilyReagentEntry | None:
    """Return the matrix entry for one (family, reagent) pair, or None.

    A None return means the matrix has no opinion on this combination —
    callers should NOT block on absence; treat it as 'unknown, no data'.
    """
    return _MATRIX_LOOKUP.get((polymer_family, reagent_key.strip().lower()))


__all__ = [
    "Compatibility",
    "FamilyReagentEntry",
    "FAMILY_REAGENT_MATRIX",
    "check_family_reagent_compatibility",
]
