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

    # ─── v9.4 Tier-3 family promotions ────────────────────────────────
    # PECTIN — galacturonic-acid -COOH + ring -OH.
    FamilyReagentEntry(
        PolymerFamily.PECTIN, "ech_activation", "qualitative_only",
        "ECH targets pectin ring -OH; canonical pectin chemistry is "
        "Ca²⁺ ionic gelation + EDC/NHS on the carboxyls.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PECTIN, "dvs_activation", "qualitative_only",
        "DVS targets pectin -OH; uncommon in practice.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PECTIN, "edc_nhs_activation", "compatible",
        "EDC/NHS targets pectin galacturonic-acid -COOH; standard "
        "chemistry for pectin-protein conjugates.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PECTIN, "genipin_secondary", "incompatible",
        "Pectin has no -NH2.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PECTIN, "glutaraldehyde_secondary", "incompatible",
        "Pectin has no -NH2.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PECTIN, "stmp_secondary", "qualitative_only",
        "STMP can target pectin -OH; uncommon.",
    ),
    # GELLAN — anionic glucan; carboxylate-rich.
    FamilyReagentEntry(
        PolymerFamily.GELLAN, "ech_activation", "qualitative_only",
        "Gellan -OH reacts with ECH; primary chemistry is K⁺ ionic "
        "gelation; ECH is secondary hardening.",
    ),
    FamilyReagentEntry(
        PolymerFamily.GELLAN, "dvs_activation", "qualitative_only",
        "Possible but uncommon.",
    ),
    FamilyReagentEntry(
        PolymerFamily.GELLAN, "edc_nhs_activation", "compatible",
        "EDC/NHS targets gellan -COOH (glucuronic acid in repeat unit); "
        "secondary chemistry after K⁺ gelation.",
    ),
    FamilyReagentEntry(
        PolymerFamily.GELLAN, "genipin_secondary", "incompatible",
        "Gellan has no -NH2.",
    ),
    FamilyReagentEntry(
        PolymerFamily.GELLAN, "glutaraldehyde_secondary", "incompatible",
        "Gellan has no -NH2.",
    ),
    FamilyReagentEntry(
        PolymerFamily.GELLAN, "stmp_secondary", "qualitative_only",
        "STMP can target gellan -OH; less common than K⁺ gelation.",
    ),
    # PULLULAN — neutral α-glucan.
    FamilyReagentEntry(
        PolymerFamily.PULLULAN, "ech_activation", "compatible",
        "ECH crosslinks pullulan -OH; standard chemistry.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PULLULAN, "dvs_activation", "compatible",
        "DVS targets pullulan -OH.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PULLULAN, "edc_nhs_activation", "incompatible",
        "Pullulan has no -COOH.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PULLULAN, "genipin_secondary", "incompatible",
        "Pullulan has no -NH2.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PULLULAN, "glutaraldehyde_secondary", "incompatible",
        "Pullulan has no -NH2.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PULLULAN, "stmp_secondary", "compatible",
        "STMP phosphate-crosslinks pullulan -OH; canonical alongside ECH.",
    ),
    # STARCH — neutral α-glucan; gelatinization/retrogradation flagged.
    FamilyReagentEntry(
        PolymerFamily.STARCH, "ech_activation", "compatible",
        "ECH crosslinks starch -OH; well-established for porous starch beads.",
    ),
    FamilyReagentEntry(
        PolymerFamily.STARCH, "dvs_activation", "qualitative_only",
        "DVS targets starch -OH; less common than ECH or STMP.",
    ),
    FamilyReagentEntry(
        PolymerFamily.STARCH, "edc_nhs_activation", "incompatible",
        "Native starch has no -COOH (oxidized starch can carry -COOH).",
    ),
    FamilyReagentEntry(
        PolymerFamily.STARCH, "genipin_secondary", "incompatible",
        "Starch has no -NH2.",
    ),
    FamilyReagentEntry(
        PolymerFamily.STARCH, "glutaraldehyde_secondary", "incompatible",
        "Starch has no -NH2.",
    ),
    FamilyReagentEntry(
        PolymerFamily.STARCH, "stmp_secondary", "compatible",
        "STMP phosphate-crosslinks starch -OH; standard food-grade modification.",
    ),

    # ═══════════════════════════════════════════════════════════════════
    # v0.5.0 — ACS Converter × Family compatibility (closes G4 gap 3).
    # 7 converters × 21 polymer families = 147 entries below.
    # Compatibility patterns (per scientific-advisor M2 audit, 2026-04-27):
    #   HYDROXYL-targeting converters (cnbr, cdi, tresyl, cyanuric, glyoxyl):
    #     C: agarose-class, dextran-class, cellulose, amylose, pullulan, starch
    #     Q: chitosan-bearing, sulfate-rich, carboxylate-rich combos, chitin
    #     I: alginate (no surface -OH), PLGA (chain-end only)
    #   Periodate (vicinal-diol):
    #     C: vicinal-diol-rich (dextran, amylose, pullulan, starch, HA, AD, AC)
    #     Q: trans-diols and partial diols (agarose, cellulose, chitosan)
    #     I: no diols (alginate, PLGA), scission-prone (KC, PC)
    #   Pyridyl-disulfide (arm-distal — requires prior amine arm):
    #     C: native -NH2 or readily-amine-arm families (chitosan-bearing)
    #     Q: any family with a viable amine-arm path (most -OH families)
    #     I: alginate (no amine path), PLGA (low density)
    # ═══════════════════════════════════════════════════════════════════

    # ── cnbr_activation × 21 families ───────────────────────────────────
    FamilyReagentEntry(
        PolymerFamily.AGAROSE_CHITOSAN, "cnbr_activation", "compatible",
        "Canonical CNBr-Sepharose chemistry (Cuatrecasas 1970); agarose -OH dominates the activation.",
    ),
    FamilyReagentEntry(
        PolymerFamily.ALGINATE, "cnbr_activation", "incompatible",
        "Alginate exposes -COOH on the gel surface; ring -OH is inaccessible to CNBr in alkaline aqueous conditions.",
    ),
    FamilyReagentEntry(
        PolymerFamily.CELLULOSE, "cnbr_activation", "compatible",
        "Cellulose -OH is a classical CNBr substrate (regenerated cellulose affinity media).",
    ),
    FamilyReagentEntry(
        PolymerFamily.PLGA, "cnbr_activation", "incompatible",
        "PLGA chain-end -OH density is too low for usable CNBr activation; alkaline pH 11 also degrades the polyester.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AGAROSE, "cnbr_activation", "compatible",
        "Pure agarose -OH is the textbook CNBr substrate (Sepharose 4B).",
    ),
    FamilyReagentEntry(
        PolymerFamily.CHITOSAN, "cnbr_activation", "qualitative_only",
        "Chitosan C3/C6 -OH react, but chitosan -NH2 also reacts with cyanate ester; selectivity poor.",
    ),
    FamilyReagentEntry(
        PolymerFamily.DEXTRAN, "cnbr_activation", "compatible",
        "Dextran -OH activates cleanly under CNBr (Sephadex affinity media).",
    ),
    FamilyReagentEntry(
        PolymerFamily.AMYLOSE, "cnbr_activation", "compatible",
        "Amylose α-1,4-glucan -OH behaves analogously to dextran under CNBr.",
    ),
    FamilyReagentEntry(
        PolymerFamily.HYALURONATE, "cnbr_activation", "qualitative_only",
        "HA -OH activates under CNBr but pH 11 risks chain scission; -COOH side groups also affect surface charge.",
    ),
    FamilyReagentEntry(
        PolymerFamily.KAPPA_CARRAGEENAN, "cnbr_activation", "qualitative_only",
        "κ-Carrageenan -OH reacts but sulfate-ester groups dominate surface chemistry; alkaline conditions risk desulfation.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AGAROSE_DEXTRAN, "cnbr_activation", "compatible",
        "Both agarose and dextran -OH activate under CNBr; canonical Capto-class capping chemistry.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AGAROSE_ALGINATE, "cnbr_activation", "qualitative_only",
        "CNBr targets the agarose -OH only; alginate -COOH is inert and dilutes the activated surface density.",
    ),
    FamilyReagentEntry(
        PolymerFamily.ALGINATE_CHITOSAN, "cnbr_activation", "qualitative_only",
        "CNBr targets chitosan -OH but cyanate-ester selectivity is poor in the presence of -NH2.",
    ),
    FamilyReagentEntry(
        PolymerFamily.CHITIN, "cnbr_activation", "qualitative_only",
        "Native chitin's NHAc dominates; the small -OH fraction does react but yields are low.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PECTIN, "cnbr_activation", "qualitative_only",
        "Pectin galacturonate ring -OH reacts, but -COOH is the dominant native ACS; better routes exist.",
    ),
    FamilyReagentEntry(
        PolymerFamily.GELLAN, "cnbr_activation", "qualitative_only",
        "Gellan -OH activates, but K⁺-gelation chemistry and -COOH dominate the canonical workflow.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PULLULAN, "cnbr_activation", "compatible",
        "Pullulan α-1,4/α-1,6 glucan -OH activates cleanly under CNBr.",
    ),
    FamilyReagentEntry(
        PolymerFamily.STARCH, "cnbr_activation", "compatible",
        "Starch -OH activates under CNBr; classical for porous starch affinity beads.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PECTIN_CHITOSAN, "cnbr_activation", "qualitative_only",
        "PEC carries both pectin -COOH and chitosan -NH2/-OH; CNBr selectivity poor across the composite.",
    ),
    FamilyReagentEntry(
        PolymerFamily.GELLAN_ALGINATE, "cnbr_activation", "qualitative_only",
        "Gellan -OH is the only viable target; alginate -COOH is inert.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PULLULAN_DEXTRAN, "cnbr_activation", "compatible",
        "Both layers expose -OH; pullulan and dextran each activate cleanly under CNBr.",
    ),

    # ── cdi_activation × 21 families ────────────────────────────────────
    FamilyReagentEntry(
        PolymerFamily.AGAROSE_CHITOSAN, "cdi_activation", "compatible",
        "CDI activates agarose -OH in anhydrous DMSO/dioxane; neutral carbamate product (no isourea charge, unlike CNBr).",
    ),
    FamilyReagentEntry(
        PolymerFamily.ALGINATE, "cdi_activation", "incompatible",
        "Alginate -COOH does not react with CDI under standard conditions; ring -OH is inaccessible.",
    ),
    FamilyReagentEntry(
        PolymerFamily.CELLULOSE, "cdi_activation", "compatible",
        "Cellulose -OH activates with CDI; classical for hydrogel-based affinity supports.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PLGA, "cdi_activation", "incompatible",
        "PLGA chain-end -OH density too low; aprotic solvent also dissolves the polyester.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AGAROSE, "cdi_activation", "compatible",
        "Agarose -OH is a textbook CDI substrate (modern alternative to CNBr).",
    ),
    FamilyReagentEntry(
        PolymerFamily.CHITOSAN, "cdi_activation", "qualitative_only",
        "Chitosan -OH activates but -NH2 competes for the imidazolyl carbonate.",
    ),
    FamilyReagentEntry(
        PolymerFamily.DEXTRAN, "cdi_activation", "compatible",
        "Dextran -OH activates with CDI; standard preparation route.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AMYLOSE, "cdi_activation", "compatible",
        "Amylose -OH activates analogously to dextran.",
    ),
    FamilyReagentEntry(
        PolymerFamily.HYALURONATE, "cdi_activation", "qualitative_only",
        "HA -OH activates but -COOH side groups affect downstream coupling kinetics.",
    ),
    FamilyReagentEntry(
        PolymerFamily.KAPPA_CARRAGEENAN, "cdi_activation", "qualitative_only",
        "κ-Carrageenan -OH activates but sulfate-ester chemistry interferes; the K⁺-gelation route is the canonical bead chemistry.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AGAROSE_DEXTRAN, "cdi_activation", "compatible",
        "Both -OH-rich layers activate cleanly with CDI.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AGAROSE_ALGINATE, "cdi_activation", "qualitative_only",
        "CDI targets the agarose -OH only; alginate -COOH is inert.",
    ),
    FamilyReagentEntry(
        PolymerFamily.ALGINATE_CHITOSAN, "cdi_activation", "qualitative_only",
        "CDI targets chitosan -OH; -NH2 competes but at lower rate than CNBr.",
    ),
    FamilyReagentEntry(
        PolymerFamily.CHITIN, "cdi_activation", "qualitative_only",
        "Chitin -OH limited; NHAc dominates surface chemistry.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PECTIN, "cdi_activation", "qualitative_only",
        "Pectin -OH activates but -COOH is the dominant native ACS.",
    ),
    FamilyReagentEntry(
        PolymerFamily.GELLAN, "cdi_activation", "qualitative_only",
        "Gellan -OH activates; secondary chemistry to K⁺-gelation.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PULLULAN, "cdi_activation", "compatible",
        "Pullulan -OH activates cleanly with CDI.",
    ),
    FamilyReagentEntry(
        PolymerFamily.STARCH, "cdi_activation", "compatible",
        "Starch -OH activates with CDI; works for crosslinked starch microbeads.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PECTIN_CHITOSAN, "cdi_activation", "qualitative_only",
        "Mixed -COOH/-NH2/-OH composite; CDI activates -OH but selectivity is poor.",
    ),
    FamilyReagentEntry(
        PolymerFamily.GELLAN_ALGINATE, "cdi_activation", "qualitative_only",
        "Gellan -OH is the only viable target; alginate -COOH inert.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PULLULAN_DEXTRAN, "cdi_activation", "compatible",
        "Both layers -OH-rich; CDI activates uniformly.",
    ),

    # ── tresyl_chloride_activation × 21 families ────────────────────────
    FamilyReagentEntry(
        PolymerFamily.AGAROSE_CHITOSAN, "tresyl_chloride_activation", "compatible",
        "Tresyl chloride activates agarose -OH in anhydrous acetone; SN2 displacement gives stable C-N bond.",
    ),
    FamilyReagentEntry(
        PolymerFamily.ALGINATE, "tresyl_chloride_activation", "incompatible",
        "Alginate -COOH does not react with tresyl chloride; surface -OH inaccessible.",
    ),
    FamilyReagentEntry(
        PolymerFamily.CELLULOSE, "tresyl_chloride_activation", "compatible",
        "Cellulose -OH (C2/C3/C6) activates cleanly with tresyl chloride.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PLGA, "tresyl_chloride_activation", "incompatible",
        "PLGA chain-end -OH density too low; acetone slurry dissolves the polyester.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AGAROSE, "tresyl_chloride_activation", "compatible",
        "Pure agarose -OH activates under tresyl chloride; produces a neutral SN2-substrate similar to CNBr without cyanate-ester decomposition.",
    ),
    FamilyReagentEntry(
        PolymerFamily.CHITOSAN, "tresyl_chloride_activation", "qualitative_only",
        "Chitosan -OH activates but -NH2 also reacts with sulfonyl chloride; selectivity poor.",
    ),
    FamilyReagentEntry(
        PolymerFamily.DEXTRAN, "tresyl_chloride_activation", "compatible",
        "Dextran -OH activates cleanly with tresyl chloride.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AMYLOSE, "tresyl_chloride_activation", "compatible",
        "Amylose -OH analogous to dextran.",
    ),
    FamilyReagentEntry(
        PolymerFamily.HYALURONATE, "tresyl_chloride_activation", "qualitative_only",
        "HA -OH activates but -COOH groups affect surface charge; aprotic solvent slurry can dehydrate gel.",
    ),
    FamilyReagentEntry(
        PolymerFamily.KAPPA_CARRAGEENAN, "tresyl_chloride_activation", "qualitative_only",
        "κ-Carrageenan -OH activates but sulfate-ester groups interfere.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AGAROSE_DEXTRAN, "tresyl_chloride_activation", "compatible",
        "Both layers' -OH activate cleanly under tresyl chloride.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AGAROSE_ALGINATE, "tresyl_chloride_activation", "qualitative_only",
        "Tresyl targets agarose -OH only; alginate -COOH inert.",
    ),
    FamilyReagentEntry(
        PolymerFamily.ALGINATE_CHITOSAN, "tresyl_chloride_activation", "qualitative_only",
        "Tresyl targets chitosan -OH; -NH2 competes.",
    ),
    FamilyReagentEntry(
        PolymerFamily.CHITIN, "tresyl_chloride_activation", "qualitative_only",
        "Chitin -OH limited; NHAc dominant.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PECTIN, "tresyl_chloride_activation", "qualitative_only",
        "Pectin -OH activates but -COOH is the canonical ACS.",
    ),
    FamilyReagentEntry(
        PolymerFamily.GELLAN, "tresyl_chloride_activation", "qualitative_only",
        "Gellan -OH activates; secondary to K⁺-gelation.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PULLULAN, "tresyl_chloride_activation", "compatible",
        "Pullulan -OH activates cleanly with tresyl chloride.",
    ),
    FamilyReagentEntry(
        PolymerFamily.STARCH, "tresyl_chloride_activation", "compatible",
        "Starch -OH activates with tresyl chloride.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PECTIN_CHITOSAN, "tresyl_chloride_activation", "qualitative_only",
        "Mixed composite; tresyl selectivity poor.",
    ),
    FamilyReagentEntry(
        PolymerFamily.GELLAN_ALGINATE, "tresyl_chloride_activation", "qualitative_only",
        "Gellan -OH only viable target.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PULLULAN_DEXTRAN, "tresyl_chloride_activation", "compatible",
        "Both layers -OH-rich.",
    ),

    # ── cyanuric_chloride_activation × 21 families ──────────────────────
    FamilyReagentEntry(
        PolymerFamily.AGAROSE_CHITOSAN, "cyanuric_chloride_activation", "compatible",
        "Cyanuric chloride activates agarose -OH at 0–5 °C; canonical for Reactive Blue 2 / Procion Red HE-3B dye supports.",
    ),
    FamilyReagentEntry(
        PolymerFamily.ALGINATE, "cyanuric_chloride_activation", "incompatible",
        "Alginate ring -OH inaccessible; -COOH does not react with triazine chlorides.",
    ),
    FamilyReagentEntry(
        PolymerFamily.CELLULOSE, "cyanuric_chloride_activation", "compatible",
        "Cellulose -OH is the original cotton-dyeing triazine substrate.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PLGA, "cyanuric_chloride_activation", "incompatible",
        "PLGA chain-end -OH density too low.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AGAROSE, "cyanuric_chloride_activation", "compatible",
        "Pure agarose -OH activates with cyanuric chloride at 0–5 °C; canonical Blue Sepharose chemistry.",
    ),
    FamilyReagentEntry(
        PolymerFamily.CHITOSAN, "cyanuric_chloride_activation", "qualitative_only",
        "Chitosan -OH activates; -NH2 reacts at higher T (second-Cl substitution).",
    ),
    FamilyReagentEntry(
        PolymerFamily.DEXTRAN, "cyanuric_chloride_activation", "compatible",
        "Dextran -OH activates cleanly; classical CDR preparation route.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AMYLOSE, "cyanuric_chloride_activation", "compatible",
        "Amylose -OH analogous to dextran.",
    ),
    FamilyReagentEntry(
        PolymerFamily.HYALURONATE, "cyanuric_chloride_activation", "qualitative_only",
        "HA -OH activates; -COOH side groups dilute the activated surface.",
    ),
    FamilyReagentEntry(
        PolymerFamily.KAPPA_CARRAGEENAN, "cyanuric_chloride_activation", "qualitative_only",
        "κ-Carrageenan -OH activates but sulfate-ester interference is significant.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AGAROSE_DEXTRAN, "cyanuric_chloride_activation", "compatible",
        "Both layers' -OH activate cleanly.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AGAROSE_ALGINATE, "cyanuric_chloride_activation", "qualitative_only",
        "Triazine targets agarose -OH only.",
    ),
    FamilyReagentEntry(
        PolymerFamily.ALGINATE_CHITOSAN, "cyanuric_chloride_activation", "qualitative_only",
        "Triazine targets chitosan -OH; -NH2 reacts at higher T.",
    ),
    FamilyReagentEntry(
        PolymerFamily.CHITIN, "cyanuric_chloride_activation", "qualitative_only",
        "Chitin -OH limited; NHAc inert to triazine.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PECTIN, "cyanuric_chloride_activation", "qualitative_only",
        "Pectin -OH activates; -COOH is the dominant native ACS.",
    ),
    FamilyReagentEntry(
        PolymerFamily.GELLAN, "cyanuric_chloride_activation", "qualitative_only",
        "Gellan -OH activates; secondary to K⁺-gelation.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PULLULAN, "cyanuric_chloride_activation", "compatible",
        "Pullulan -OH activates cleanly with cyanuric chloride.",
    ),
    FamilyReagentEntry(
        PolymerFamily.STARCH, "cyanuric_chloride_activation", "compatible",
        "Starch -OH activates with cyanuric chloride; common in textile-grade modified starch.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PECTIN_CHITOSAN, "cyanuric_chloride_activation", "qualitative_only",
        "Mixed composite; selectivity poor.",
    ),
    FamilyReagentEntry(
        PolymerFamily.GELLAN_ALGINATE, "cyanuric_chloride_activation", "qualitative_only",
        "Gellan -OH only viable target.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PULLULAN_DEXTRAN, "cyanuric_chloride_activation", "compatible",
        "Both layers -OH-rich; uniform triazine activation.",
    ),

    # ── glyoxyl_chained_activation × 21 families ────────────────────────
    FamilyReagentEntry(
        PolymerFamily.AGAROSE_CHITOSAN, "glyoxyl_chained_activation", "compatible",
        "Glyoxyl-agarose is the canonical multipoint enzyme support (Mateo 2007); agarose -OH overlay route.",
    ),
    FamilyReagentEntry(
        PolymerFamily.ALGINATE, "glyoxyl_chained_activation", "incompatible",
        "Alginate ring -OH inaccessible to glycidol; -COOH does not enter the chained route.",
    ),
    FamilyReagentEntry(
        PolymerFamily.CELLULOSE, "glyoxyl_chained_activation", "compatible",
        "Cellulose -OH supports glycidol etherification followed by periodate cleavage.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PLGA, "glyoxyl_chained_activation", "incompatible",
        "PLGA chain-end -OH density too low; alkaline glycidol step degrades the polyester.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AGAROSE, "glyoxyl_chained_activation", "compatible",
        "Pure agarose is the textbook glyoxyl substrate (Mateo et al. 2007 protocol).",
    ),
    FamilyReagentEntry(
        PolymerFamily.CHITOSAN, "glyoxyl_chained_activation", "qualitative_only",
        "Chitosan -OH supports glycidol etherification but -NH2 reacts in parallel; periodate cleavage poor selectivity.",
    ),
    FamilyReagentEntry(
        PolymerFamily.DEXTRAN, "glyoxyl_chained_activation", "compatible",
        "Dextran -OH supports the chained glyoxyl route; less common than agarose but mechanistically equivalent.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AMYLOSE, "glyoxyl_chained_activation", "compatible",
        "Amylose -OH analogous to dextran.",
    ),
    FamilyReagentEntry(
        PolymerFamily.HYALURONATE, "glyoxyl_chained_activation", "qualitative_only",
        "HA -OH supports glycidol but pH 11 step risks chain scission.",
    ),
    FamilyReagentEntry(
        PolymerFamily.KAPPA_CARRAGEENAN, "glyoxyl_chained_activation", "qualitative_only",
        "κ-Carrageenan -OH supports glycidol but periodate step degrades sulfated chain.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AGAROSE_DEXTRAN, "glyoxyl_chained_activation", "compatible",
        "Both layers' -OH support glycidol+periodate; uniform aldehyde density.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AGAROSE_ALGINATE, "glyoxyl_chained_activation", "qualitative_only",
        "Glyoxyl targets agarose -OH only; alginate inert.",
    ),
    FamilyReagentEntry(
        PolymerFamily.ALGINATE_CHITOSAN, "glyoxyl_chained_activation", "qualitative_only",
        "Glycidol targets chitosan -OH; -NH2 competes.",
    ),
    FamilyReagentEntry(
        PolymerFamily.CHITIN, "glyoxyl_chained_activation", "qualitative_only",
        "Chitin -OH limited.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PECTIN, "glyoxyl_chained_activation", "qualitative_only",
        "Pectin -OH supports glycidol; -COOH inert to chained route.",
    ),
    FamilyReagentEntry(
        PolymerFamily.GELLAN, "glyoxyl_chained_activation", "qualitative_only",
        "Gellan -OH supports glycidol; secondary chemistry to K⁺-gelation.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PULLULAN, "glyoxyl_chained_activation", "compatible",
        "Pullulan -OH supports the full glycidol+periodate chained route.",
    ),
    FamilyReagentEntry(
        PolymerFamily.STARCH, "glyoxyl_chained_activation", "compatible",
        "Starch -OH supports glycidol etherification; periodate yields clean glyoxyl.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PECTIN_CHITOSAN, "glyoxyl_chained_activation", "qualitative_only",
        "Mixed composite; selectivity poor.",
    ),
    FamilyReagentEntry(
        PolymerFamily.GELLAN_ALGINATE, "glyoxyl_chained_activation", "qualitative_only",
        "Gellan -OH only viable target.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PULLULAN_DEXTRAN, "glyoxyl_chained_activation", "compatible",
        "Both layers -OH-rich; uniform glyoxyl coverage.",
    ),

    # ── periodate_oxidation × 21 families ───────────────────────────────
    FamilyReagentEntry(
        PolymerFamily.AGAROSE_CHITOSAN, "periodate_oxidation", "compatible",
        "AC has accessible vicinal diols on both layers; periodate gives clean aldehyde with bounded chain scission.",
    ),
    FamilyReagentEntry(
        PolymerFamily.ALGINATE, "periodate_oxidation", "incompatible",
        "Alginate guluronate/mannuronate ring -OH are trans (axial-equatorial); no vicinal-diol pairs for Malaprade cleavage.",
    ),
    FamilyReagentEntry(
        PolymerFamily.CELLULOSE, "periodate_oxidation", "qualitative_only",
        "Cellulose has limited vicinal-diol fraction (mostly C2/C3 trans); oxidation is slow and chain-scission-prone above 30%.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PLGA, "periodate_oxidation", "incompatible",
        "PLGA polyester has no vicinal diols.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AGAROSE, "periodate_oxidation", "qualitative_only",
        "Agarose has some vicinal diols on the 3,6-anhydrogalactose unit but oxidation degrades gel mechanics quickly.",
    ),
    FamilyReagentEntry(
        PolymerFamily.CHITOSAN, "periodate_oxidation", "qualitative_only",
        "Chitosan glucosamine C3-C4 cis-diol oxidises but NHAc on residual chitin units interferes.",
    ),
    FamilyReagentEntry(
        PolymerFamily.DEXTRAN, "periodate_oxidation", "compatible",
        "Dextran α-1,6 backbone exposes abundant vicinal diols on each glucose unit; canonical Malaprade substrate.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AMYLOSE, "periodate_oxidation", "compatible",
        "Amylose α-1,4 backbone has C2-C3 cis-diols on each glucose; standard periodate route.",
    ),
    FamilyReagentEntry(
        PolymerFamily.HYALURONATE, "periodate_oxidation", "compatible",
        "HA glucuronate ring has cis-diols accessible; oxidised HA + ADH is a published hydrogel route.",
    ),
    FamilyReagentEntry(
        PolymerFamily.KAPPA_CARRAGEENAN, "periodate_oxidation", "incompatible",
        "Sulfated galactose; periodate degrades sulfate-ester chain to fragments not coupling-suitable.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AGAROSE_DEXTRAN, "periodate_oxidation", "compatible",
        "Dextran shell oxidises cleanly; agarose core minimally affected at controlled doses.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AGAROSE_ALGINATE, "periodate_oxidation", "qualitative_only",
        "Agarose component has limited diols; alginate inert.",
    ),
    FamilyReagentEntry(
        PolymerFamily.ALGINATE_CHITOSAN, "periodate_oxidation", "qualitative_only",
        "Chitosan glucosamine cis-diol oxidises; alginate inert.",
    ),
    FamilyReagentEntry(
        PolymerFamily.CHITIN, "periodate_oxidation", "qualitative_only",
        "Chitin NHAc dominates; the small glucosamine fraction has cis-diols.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PECTIN, "periodate_oxidation", "qualitative_only",
        "Galacturonate ring has cis-diols; oxidation also opens the ring (chain scission).",
    ),
    FamilyReagentEntry(
        PolymerFamily.GELLAN, "periodate_oxidation", "qualitative_only",
        "Gellan glucose+glucuronate units have diols but glucuronate -COOH affects scission kinetics.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PULLULAN, "periodate_oxidation", "compatible",
        "Pullulan exposes vicinal diols on each glucose; standard periodate substrate.",
    ),
    FamilyReagentEntry(
        PolymerFamily.STARCH, "periodate_oxidation", "compatible",
        "Starch α-1,4 backbone has C2-C3 cis-diols; classical dialdehyde-starch chemistry.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PECTIN_CHITOSAN, "periodate_oxidation", "incompatible",
        "Both components are scission-prone under periodate; PEC integrity degrades unacceptably.",
    ),
    FamilyReagentEntry(
        PolymerFamily.GELLAN_ALGINATE, "periodate_oxidation", "qualitative_only",
        "Gellan diols oxidise; alginate inert.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PULLULAN_DEXTRAN, "periodate_oxidation", "compatible",
        "Both glucan layers expose abundant cis-diols.",
    ),

    # ── pyridyl_disulfide_activation × 21 families (arm-distal) ─────────
    FamilyReagentEntry(
        PolymerFamily.AGAROSE_CHITOSAN, "pyridyl_disulfide_activation", "compatible",
        "Chitosan -NH2 readily supports cystamine/EDA arm; pyridyl-disulfide installs cleanly on the arm-distal -NH2.",
    ),
    FamilyReagentEntry(
        PolymerFamily.ALGINATE, "pyridyl_disulfide_activation", "incompatible",
        "Alginate has no native amine path and no surface -OH to install one; arm-distal activation has no substrate.",
    ),
    FamilyReagentEntry(
        PolymerFamily.CELLULOSE, "pyridyl_disulfide_activation", "qualitative_only",
        "Requires prior ECH/CDI/CNBr + amine-spacer step; pyridyl-disulfide installs on the resulting AMINE_DISTAL.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PLGA, "pyridyl_disulfide_activation", "incompatible",
        "Insufficient amine-arm density achievable on PLGA chain ends.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AGAROSE, "pyridyl_disulfide_activation", "qualitative_only",
        "Requires prior ECH/CDI/CNBr + amine-spacer step before pyridyl-disulfide.",
    ),
    FamilyReagentEntry(
        PolymerFamily.CHITOSAN, "pyridyl_disulfide_activation", "compatible",
        "Native chitosan -NH2 can be directly used as the arm-distal substrate (no spacer needed for surface-bound -NH2).",
    ),
    FamilyReagentEntry(
        PolymerFamily.DEXTRAN, "pyridyl_disulfide_activation", "qualitative_only",
        "Requires prior amine-arm installation via ECH or CDI route.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AMYLOSE, "pyridyl_disulfide_activation", "qualitative_only",
        "Same arm-installation prerequisite as dextran.",
    ),
    FamilyReagentEntry(
        PolymerFamily.HYALURONATE, "pyridyl_disulfide_activation", "qualitative_only",
        "Requires prior EDC/NHS+EDA arm or ECH+amine arm; arm density may be low on HA.",
    ),
    FamilyReagentEntry(
        PolymerFamily.KAPPA_CARRAGEENAN, "pyridyl_disulfide_activation", "qualitative_only",
        "Requires prior amine-arm installation; sulfate-ester chemistry interferes with most arm routes.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AGAROSE_DEXTRAN, "pyridyl_disulfide_activation", "qualitative_only",
        "Requires prior amine-arm; either layer can host the arm.",
    ),
    FamilyReagentEntry(
        PolymerFamily.AGAROSE_ALGINATE, "pyridyl_disulfide_activation", "qualitative_only",
        "Arm installs on agarose -OH route; pyridyl-disulfide then on arm-distal -NH2.",
    ),
    FamilyReagentEntry(
        PolymerFamily.ALGINATE_CHITOSAN, "pyridyl_disulfide_activation", "compatible",
        "Chitosan native -NH2 supports direct pyridyl-disulfide installation.",
    ),
    FamilyReagentEntry(
        PolymerFamily.CHITIN, "pyridyl_disulfide_activation", "qualitative_only",
        "Requires deacetylated patches or amine arm via ECH; viable but uncommon.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PECTIN, "pyridyl_disulfide_activation", "qualitative_only",
        "Requires prior EDC/NHS+EDA arm on -COOH or ECH+amine on -OH.",
    ),
    FamilyReagentEntry(
        PolymerFamily.GELLAN, "pyridyl_disulfide_activation", "qualitative_only",
        "Same arm prerequisite as pectin.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PULLULAN, "pyridyl_disulfide_activation", "qualitative_only",
        "Requires prior amine-arm via ECH/CDI route.",
    ),
    FamilyReagentEntry(
        PolymerFamily.STARCH, "pyridyl_disulfide_activation", "qualitative_only",
        "Requires prior amine-arm; starch + ECH + EDA is a published route.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PECTIN_CHITOSAN, "pyridyl_disulfide_activation", "compatible",
        "Chitosan -NH2 in the PEC supports direct pyridyl-disulfide installation.",
    ),
    FamilyReagentEntry(
        PolymerFamily.GELLAN_ALGINATE, "pyridyl_disulfide_activation", "qualitative_only",
        "Requires arm installation on gellan -OH; alginate inert to arm chemistry.",
    ),
    FamilyReagentEntry(
        PolymerFamily.PULLULAN_DEXTRAN, "pyridyl_disulfide_activation", "qualitative_only",
        "Requires prior amine-arm on either glucan layer.",
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
