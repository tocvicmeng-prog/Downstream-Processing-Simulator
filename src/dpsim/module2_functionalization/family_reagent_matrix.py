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

    # ─── v9.2 Tier-1 family additions (M0a A2.7) ─────────────────────────
    # AGAROSE: chitosan-free agarose; native -OH only (no -NH2).
    FamilyReagentEntry(
        PolymerFamily.AGAROSE,
        "ech_activation",
        "compatible",
        "Agarose -OH is the canonical ECH substrate (Sundberg & Porath 1974).",
    ),
    FamilyReagentEntry(
        PolymerFamily.AGAROSE,
        "dvs_activation",
        "compatible",
        "Agarose -OH reacts with DVS at pH 11–12 to give vinyl-sulfone-activated agarose.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AGAROSE,
        "edc_nhs_activation",
        "incompatible",
        "Agarose has no native -COOH; EDC/NHS requires carboxyl groups.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AGAROSE,
        "genipin_secondary",
        "incompatible",
        "Genipin requires primary amines; agarose-only beads have no -NH2.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AGAROSE,
        "glutaraldehyde_secondary",
        "incompatible",
        "Glutaraldehyde requires primary amines; agarose-only beads have no -NH2.",
    ),
    # CHITOSAN: chitosan-only beads; native -NH2 + -OH.
    FamilyReagentEntry(
        PolymerFamily.CHITOSAN,
        "ech_activation",
        "qualitative_only",
        "Chitosan -OH and -NH2 both react with ECH; selectivity depends on pH and DDA.",
    ),
    FamilyReagentEntry(
        PolymerFamily.CHITOSAN,
        "dvs_activation",
        "compatible",
        "DVS is a standard chitosan crosslinker via -NH2 (also reacts with -OH).",
    ),
    FamilyReagentEntry(
        PolymerFamily.CHITOSAN,
        "edc_nhs_activation",
        "incompatible",
        "Chitosan has no native -COOH unless carboxymethylated. Use carboxymethyl-chitosan.",
    ),
    FamilyReagentEntry(
        PolymerFamily.CHITOSAN,
        "genipin_secondary",
        "compatible",
        "Genipin is the canonical low-toxicity chitosan crosslinker via -NH2.",
    ),
    FamilyReagentEntry(
        PolymerFamily.CHITOSAN,
        "glutaraldehyde_secondary",
        "compatible",
        "Glutaraldehyde forms Schiff bases with chitosan -NH2; classical chitosan crosslinker.",
    ),
    # DEXTRAN: Sephadex-class; native -OH only (3 per glucose unit).
    FamilyReagentEntry(
        PolymerFamily.DEXTRAN,
        "ech_activation",
        "compatible",
        "Dextran -OH is the canonical ECH substrate (Sephadex preparation).",
    ),
    FamilyReagentEntry(
        PolymerFamily.DEXTRAN,
        "dvs_activation",
        "compatible",
        "Dextran -OH reacts with DVS under alkaline conditions.",
    ),
    FamilyReagentEntry(
        PolymerFamily.DEXTRAN,
        "edc_nhs_activation",
        "incompatible",
        "Native dextran has no -COOH. Use periodate-oxidized or CM-dextran for EDC routes.",
    ),
    FamilyReagentEntry(
        PolymerFamily.DEXTRAN,
        "genipin_secondary",
        "incompatible",
        "Genipin requires primary amines; dextran has no -NH2.",
    ),
    FamilyReagentEntry(
        PolymerFamily.DEXTRAN,
        "glutaraldehyde_secondary",
        "incompatible",
        "Glutaraldehyde requires primary amines; dextran has no -NH2.",
    ),
    # STMP entries for v9.2 Tier-1 families (phosphate-diester crosslinking).
    FamilyReagentEntry(
        PolymerFamily.AGAROSE,
        "stmp_secondary",
        "qualitative_only",
        "STMP can phosphate-crosslink agarose -OH under alkaline conditions, but agarose is more commonly hardened by ECH/DVS/PEGDGE.",
    ),
    FamilyReagentEntry(
        PolymerFamily.CHITOSAN,
        "stmp_secondary",
        "qualitative_only",
        "STMP can react with chitosan -OH/-NH2 mixtures; less common than genipin or glutaraldehyde for chitosan.",
    ),
    FamilyReagentEntry(
        PolymerFamily.DEXTRAN,
        "stmp_secondary",
        "compatible",
        "STMP phosphate-crosslinks dextran -OH; well-established for crosslinked-dextran microbeads.",
    ),
    # M8 B9 — AMYLOSE (material-as-ligand, MBP affinity).
    # Amylose chemistry mirrors dextran (α-1,4 vs α-1,6 glucan, same -OH
    # surface chemistry); ECH crosslinking is canonical (NEB Amylose Resin).
    FamilyReagentEntry(
        PolymerFamily.AMYLOSE,
        "ech_activation",
        "compatible",
        "Amylose -OH is the canonical ECH crosslinking substrate (NEB Amylose Resin).",
    ),
    FamilyReagentEntry(
        PolymerFamily.AMYLOSE,
        "dvs_activation",
        "compatible",
        "Amylose -OH reacts with DVS analogously to dextran/agarose.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AMYLOSE,
        "edc_nhs_activation",
        "incompatible",
        "Native amylose has no -COOH; EDC/NHS requires carboxyl groups.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AMYLOSE,
        "genipin_secondary",
        "incompatible",
        "Genipin requires primary amines; amylose has no -NH2.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AMYLOSE,
        "glutaraldehyde_secondary",
        "incompatible",
        "Glutaraldehyde requires primary amines; amylose has no -NH2.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AMYLOSE,
        "stmp_secondary",
        "compatible",
        "STMP phosphate-crosslinks amylose -OH analogously to dextran.",
    ),

    # ─── v9.3 Tier-2 family promotions ────────────────────────────────
    # HYALURONATE: carboxylate-rich polyelectrolyte; canonical chemistry
    # is BDDE / HRP-tyramine / oxidized-HA + ADH (covalent crosslinking).
    FamilyReagentEntry(
        PolymerFamily.HYALURONATE,
        "ech_activation",
        "qualitative_only",
        "HA -OH can react with ECH but the canonical HA crosslinking is "
        "BDDE; ECH gives a non-canonical HA bead chemistry.",
    ),
    FamilyReagentEntry(
        PolymerFamily.HYALURONATE,
        "dvs_activation",
        "compatible",
        "HA -OH reacts with DVS at alkaline pH; alternative to BDDE.",
    ),
    FamilyReagentEntry(
        PolymerFamily.HYALURONATE,
        "edc_nhs_activation",
        "compatible",
        "HA carboxylate is the canonical EDC/NHS substrate; standard "
        "chemistry for HA-protein conjugates.",
    ),
    FamilyReagentEntry(
        PolymerFamily.HYALURONATE,
        "genipin_secondary",
        "incompatible",
        "Genipin requires primary amines; HA has -COOH and -OH but no -NH2.",
    ),
    FamilyReagentEntry(
        PolymerFamily.HYALURONATE,
        "glutaraldehyde_secondary",
        "incompatible",
        "Glutaraldehyde requires primary amines; HA has none.",
    ),
    FamilyReagentEntry(
        PolymerFamily.HYALURONATE,
        "stmp_secondary",
        "qualitative_only",
        "STMP phosphate-crosslinks HA -OH; less common than BDDE.",
    ),
    # KAPPA_CARRAGEENAN: sulfate-ester ACS chemistry; native carboxylate
    # density is low (κ-carrageenan is mostly sulfate-ester).
    FamilyReagentEntry(
        PolymerFamily.KAPPA_CARRAGEENAN,
        "ech_activation",
        "qualitative_only",
        "κ-Carrageenan -OH reacts with ECH; the K⁺ ionic gelation is "
        "the canonical bead chemistry; ECH is secondary hardening.",
    ),
    FamilyReagentEntry(
        PolymerFamily.KAPPA_CARRAGEENAN,
        "dvs_activation",
        "qualitative_only",
        "DVS can target κ-carrageenan -OH; uncommon in practice.",
    ),
    FamilyReagentEntry(
        PolymerFamily.KAPPA_CARRAGEENAN,
        "edc_nhs_activation",
        "incompatible",
        "κ-Carrageenan has very low carboxylate density (mostly sulfate-"
        "ester); EDC/NHS has nothing to activate.",
    ),
    FamilyReagentEntry(
        PolymerFamily.KAPPA_CARRAGEENAN,
        "genipin_secondary",
        "incompatible",
        "No primary amines.",
    ),
    FamilyReagentEntry(
        PolymerFamily.KAPPA_CARRAGEENAN,
        "glutaraldehyde_secondary",
        "incompatible",
        "No primary amines.",
    ),
    FamilyReagentEntry(
        PolymerFamily.KAPPA_CARRAGEENAN,
        "stmp_secondary",
        "qualitative_only",
        "STMP phosphate-crosslinking is uncommon for κ-carrageenan; the "
        "K⁺ ionic gelation is the standard chemistry.",
    ),
    # AGAROSE_DEXTRAN core-shell: both layers are -OH-rich.
    FamilyReagentEntry(
        PolymerFamily.AGAROSE_DEXTRAN,
        "ech_activation",
        "compatible",
        "ECH crosslinks both agarose core and dextran shell; canonical "
        "Capto-class hardening chemistry.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AGAROSE_DEXTRAN,
        "dvs_activation",
        "compatible",
        "DVS targets both layers' -OH groups.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AGAROSE_DEXTRAN,
        "edc_nhs_activation",
        "incompatible",
        "Both layers lack native -COOH.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AGAROSE_DEXTRAN,
        "genipin_secondary",
        "incompatible",
        "Both layers lack -NH2.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AGAROSE_DEXTRAN,
        "glutaraldehyde_secondary",
        "incompatible",
        "Both layers lack -NH2.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AGAROSE_DEXTRAN,
        "stmp_secondary",
        "compatible",
        "STMP phosphate-crosslinks both -OH-rich layers; less common "
        "than ECH.",
    ),
    # AGAROSE_ALGINATE IPN: agarose -OH + alginate -COOH.
    FamilyReagentEntry(
        PolymerFamily.AGAROSE_ALGINATE,
        "ech_activation",
        "qualitative_only",
        "Targets the agarose -OH; alginate -COOH is unaffected by ECH.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AGAROSE_ALGINATE,
        "dvs_activation",
        "qualitative_only",
        "DVS targets agarose -OH; alginate -COOH unaffected.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AGAROSE_ALGINATE,
        "edc_nhs_activation",
        "compatible",
        "EDC/NHS targets the alginate -COOH; standard chemistry for "
        "ligand coupling on this composite.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AGAROSE_ALGINATE,
        "genipin_secondary",
        "incompatible",
        "Neither agarose nor alginate has -NH2.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AGAROSE_ALGINATE,
        "glutaraldehyde_secondary",
        "incompatible",
        "Neither agarose nor alginate has -NH2.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AGAROSE_ALGINATE,
        "stmp_secondary",
        "qualitative_only",
        "STMP can target agarose -OH; alginate -COOH unaffected.",
    ),
    # ALGINATE_CHITOSAN PEC: alginate -COOH + chitosan -NH2/-OH.
    FamilyReagentEntry(
        PolymerFamily.ALGINATE_CHITOSAN,
        "ech_activation",
        "qualitative_only",
        "ECH targets the chitosan -OH/-NH2; alginate -COOH unaffected.",
    ),
    FamilyReagentEntry(
        PolymerFamily.ALGINATE_CHITOSAN,
        "dvs_activation",
        "compatible",
        "DVS targets both alginate -COOH (after activation) and "
        "chitosan -OH/-NH2.",
    ),
    FamilyReagentEntry(
        PolymerFamily.ALGINATE_CHITOSAN,
        "edc_nhs_activation",
        "compatible",
        "EDC/NHS targets the alginate -COOH; standard ligand coupling.",
    ),
    FamilyReagentEntry(
        PolymerFamily.ALGINATE_CHITOSAN,
        "genipin_secondary",
        "compatible",
        "Genipin crosslinks the chitosan amine network; secondary "
        "hardening of the PEC shell.",
    ),
    FamilyReagentEntry(
        PolymerFamily.ALGINATE_CHITOSAN,
        "glutaraldehyde_secondary",
        "compatible",
        "Glutaraldehyde crosslinks the chitosan amine network.",
    ),
    FamilyReagentEntry(
        PolymerFamily.ALGINATE_CHITOSAN,
        "stmp_secondary",
        "qualitative_only",
        "STMP can target chitosan -OH; less common than genipin.",
    ),
    # CHITIN material-as-ligand (CBD/intein affinity).
    FamilyReagentEntry(
        PolymerFamily.CHITIN,
        "ech_activation",
        "qualitative_only",
        "Chitin -OH/-NHAc reacts with ECH; uncommon — chitin matrix is "
        "the affinity ligand and is typically used unmodified.",
    ),
    FamilyReagentEntry(
        PolymerFamily.CHITIN,
        "dvs_activation",
        "qualitative_only",
        "Possible but uncommon; chitin is usually used in its native form.",
    ),
    FamilyReagentEntry(
        PolymerFamily.CHITIN,
        "edc_nhs_activation",
        "incompatible",
        "Chitin has no native -COOH (though deacetylated chitin = chitosan "
        "with carboxymethylation can carry -COOH).",
    ),
    FamilyReagentEntry(
        PolymerFamily.CHITIN,
        "genipin_secondary",
        "qualitative_only",
        "Genipin can target the small fraction of -NH2 in partially-"
        "deacetylated chitin; rare modification.",
    ),
    FamilyReagentEntry(
        PolymerFamily.CHITIN,
        "glutaraldehyde_secondary",
        "qualitative_only",
        "Glutaraldehyde requires -NH2 which is sparse in native chitin.",
    ),
    FamilyReagentEntry(
        PolymerFamily.CHITIN,
        "stmp_secondary",
        "qualitative_only",
        "STMP can target chitin -OH; rarely needed since chitin matrix "
        "is the affinity ligand directly.",
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
