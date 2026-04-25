"""Polymer-family selector (v9.0 → v9.2, milestone M0b A2.6).

Renders a polymer-family radio at the top of the M1 tab. The selected
family becomes FormulationParameters.polymer_family and drives every
downstream conditional-rendering decision in tab_m1 and its per-family
modules.

Scientific caption is provided per option (per scientific-advisor §B)
so the user knows which L2 branch each choice dispatches to.

v9.2 (M0b A2.6): family list extended with AGAROSE, CHITOSAN, DEXTRAN
(Tier-1). Tier-2 families (HYALURONATE, KAPPA_CARRAGEENAN, AMYLOSE,
CHITIN, AGAROSE_DEXTRAN, AGAROSE_ALGINATE, ALGINATE_CHITOSAN) are
filtered out by ``is_family_enabled_in_ui`` and remain data-only until
their UI surface lands in v9.3.

Milestone matrix (legacy):
    M3              selector live; A+C formulation unchanged (still in tab_m1)
    M4              A+C formulation extracted to formulation_agarose_chitosan
    M5              alginate branch populated (formulation_alginate)
    M6              cellulose branch populated
    M7              PLGA branch populated
v9.2:
    M0b A2.6        AGAROSE / CHITOSAN / DEXTRAN added to selector
    M0b A2.2/A2.3   AGAROSE / CHITOSAN solver branches populated
    M0b A2.4        DEXTRAN solver branch populated
"""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from dpsim.datatypes import PolymerFamily, is_family_enabled_in_ui


# Display rows: (display_name, PolymerFamily, scientific caption).
# v9.2 (A2.6): added AGAROSE / CHITOSAN / DEXTRAN at the end of the
# v9.1 baseline so existing session-state defaults (index=0 →
# AGAROSE_CHITOSAN) remain stable.
_FAMILY_DISPLAY: list[tuple[str, PolymerFamily, str]] = [
    ("Agarose + Chitosan", PolymerFamily.AGAROSE_CHITOSAN,
     "Thermal-TIPS gelation with optional covalent crosslinking "
     "(genipin / glutaraldehyde / EDC-NHS / others). Legacy platform."),
    ("Alginate", PolymerFamily.ALGINATE,
     "Ionotropic Ca²⁺ crosslinking (external CaCl₂ bath or internal "
     "GDL + CaCO₃ release). L3 crosslinking step does not apply."),
    ("Cellulose (NIPS)", PolymerFamily.CELLULOSE,
     "Non-solvent-induced phase separation in NaOH/urea, NMMO, "
     "EMIM-Ac, or DMAc/LiCl. L3 crosslinking step does not apply."),
    ("PLGA (solvent evaporation)", PolymerFamily.PLGA,
     "Glassy microspheres via DCM-depletion-driven solvent evaporation. "
     "L3 crosslinking step does not apply; grade presets 50:50/75:25/85:15/PLA."),
    # v9.2 Tier-1 additions (A2.6).
    ("Agarose only", PolymerFamily.AGAROSE,
     "Chitosan-free agarose: pure thermal helix-coil gelation, "
     "T_gel ≈ 30–40 °C, optional secondary covalent hardening "
     "(ECH / DVS / PEGDGE). Sepharose-class baseline platform."),
    ("Chitosan only", PolymerFamily.CHITOSAN,
     "Agarose-free chitosan beads: pH-dependent amine protonation "
     "(pKa ≈ 6.3–6.5); gelled by genipin / TPP / glutaraldehyde. "
     "Acid-solubilised droplet path."),
    ("Dextran (Sephadex-class)", PolymerFamily.DEXTRAN,
     "ECH-crosslinked dextran beads (Sephadex preparation). "
     "Hydroxyl-rich; tunable crosslink density → pore size; "
     "foundational SEC matrix."),
    ("Amylose (MBP-affinity, B9)", PolymerFamily.AMYLOSE,
     "Crosslinked amylose: the polysaccharide matrix IS the affinity "
     "ligand for MBP-tagged fusion proteins (Kd ≈ 1 µM). Eluted by "
     "10 mM maltose. Material-as-ligand pattern (v9.2 B9)."),
    # v9.3 Tier-2 additions (SA screening § 6.2)
    ("Hyaluronate (HA)", PolymerFamily.HYALURONATE,
     "High-swelling polyelectrolyte hydrogel; canonical chemistry is "
     "covalent crosslinking via BDDE (Hahn 2006), HRP-tyramine, or "
     "oxidized-HA + ADH. Specialty matrix (v9.3 SEMI_QUANTITATIVE)."),
    ("κ-Carrageenan", PolymerFamily.KAPPA_CARRAGEENAN,
     "K⁺-specific helix-aggregation gelation; sulfate-ester ACS chemistry. "
     "Niche chromatography support (v9.3 SEMI_QUANTITATIVE)."),
    ("Agarose-Dextran (Capto-class)", PolymerFamily.AGAROSE_DEXTRAN,
     "Core-shell composite: thermal agarose core + ECH-crosslinked "
     "dextran shell. Industrial Capto-class media (v9.3 SEMI_QUANTITATIVE)."),
    ("Agarose-Alginate IPN", PolymerFamily.AGAROSE_ALGINATE,
     "Interpenetrating network: orthogonal thermal agarose + Ca²⁺ "
     "alginate gelation. ~30 % G_DN reinforcement over agarose-only "
     "(v9.3 SEMI_QUANTITATIVE)."),
    ("Alginate-Chitosan PEC", PolymerFamily.ALGINATE_CHITOSAN,
     "Polyelectrolyte-complex shell: alginate Ca²⁺ skeleton + chitosan "
     "PEC surface. pH-dependent shell stability "
     "(v9.3 SEMI_QUANTITATIVE)."),
    ("Chitin (CBD/intein, B9)", PolymerFamily.CHITIN,
     "Material-as-ligand companion to amylose-MBP: crosslinked chitin "
     "matrix as the affinity ligand for CBD-tagged fusions. NEB IMPACT "
     "system; on-column thiol-induced cleavage (v9.3 SEMI_QUANTITATIVE)."),
    # v9.4 Tier-3 additions (research-mode / lower-priority families)
    ("Pectin (LM, Ca²⁺ gel)", PolymerFamily.PECTIN,
     "Galacturonic-acid carboxylate Ca²⁺ ionic gelation; analogous to "
     "alginate but DE-dependent. Limited bioprocess relevance "
     "(v9.4 QUALITATIVE_TREND, research-mode)."),
    ("Gellan (low-acyl, K⁺/Ca²⁺)", PolymerFamily.GELLAN,
     "Helix-aggregation gelation; cation-dependent (K⁺ standard, Ca²⁺ "
     "stronger). Food / drug-delivery dominant; limited bioprocess "
     "relevance (v9.4 QUALITATIVE_TREND)."),
    ("Pullulan (neutral α-glucan)", PolymerFamily.PULLULAN,
     "α-(1→4),(1→6)-glucan analogous to dextran; STMP / ECH crosslinked. "
     "Drug-delivery dominant (v9.4 QUALITATIVE_TREND)."),
    ("Starch (porous, research-mode)", PolymerFamily.STARCH,
     "Crosslinked porous starch bead; gelatinization, retrogradation, "
     "and amylase-degradation flags. Research-mode only "
     "(v9.4 QUALITATIVE_TREND)."),
    # v9.5 Tier-3 multi-variant composite additions (SA screening § 6.4)
    ("Pectin-Chitosan PEC", PolymerFamily.PECTIN_CHITOSAN,
     "Polyelectrolyte complex: pectin Ca²⁺-gel skeleton + chitosan "
     "ammonium PEC shell. pH-controlled drug-delivery; pH window "
     "5.5–6.5 (v9.5 QUALITATIVE_TREND)."),
    ("Gellan-Alginate composite", PolymerFamily.GELLAN_ALGINATE,
     "Dual ionic-gel composite: alginate Ca²⁺-gel dominant + ~20 % G_DN "
     "reinforcement from gellan helix-aggregation. Food provenance "
     "(v9.5 QUALITATIVE_TREND)."),
    ("Pullulan-Dextran composite", PolymerFamily.PULLULAN_DEXTRAN,
     "Neutral α-glucan composite microbeads; ECH/STMP crosslinked. "
     "Drug-delivery dominant; structurally analogous to dextran-ECH "
     "alone (v9.5 QUALITATIVE_TREND)."),
]


def _enabled_rows() -> list[tuple[str, PolymerFamily, str]]:
    """Return only the display rows whose family is UI-enabled in v9.2.

    Tier-2 placeholder families (HYALURONATE, KAPPA_CARRAGEENAN, …) live in
    the PolymerFamily enum but are filtered out here until their UI
    surface lands in v9.3.
    """
    return [row for row in _FAMILY_DISPLAY if is_family_enabled_in_ui(row[1])]


# v9.5 update: Tier-3 multi-variant composites (PECTIN_CHITOSAN,
# GELLAN_ALGINATE, PULLULAN_DEXTRAN) have been promoted to selectable
# status with their solver lambdas in
# ``src/dpsim/level2_gelation/v9_5_composites.py``. The preview list now
# records only the items that remain documented-warning entries: the
# rejected Tier-4 reagent (POCl3), and crosslinker flags that contributors
# should be aware of when configuring formulations (Al³⁺ non-biotherapeutic,
# borax reversibility).
_TIER2_PREVIEW_ROWS: list[tuple[str, str]] = [
    ("POCl3 (phosphoryl chloride) — Tier-4 REJECTED",
     "Hazard-rejected: violent reaction with water (HCl release); "
     "food-grade starch context only. Documented as ADR; not implemented."),
    ("Trivalent Al³⁺ gelant — non-biotherapeutic flag",
     "v9.4 Tier-3 implemented behind biotherapeutic_safe=False gate; "
     "documented here for awareness."),
    ("Reversible borate-cis-diol crosslinking (borax) — REVERSIBILITY WARNING",
     "Implemented as a freestanding ion gelant (v9.4 Tier-3) and as a "
     "ReagentProfile (borax_reversible_crosslinking) for use as a "
     "TEMPORARY POROGEN or model network during synthesis. Borate-diol "
     "esters dissociate at pH < 8.5 or in the presence of competing "
     "diols/sugars, so borax is NOT suitable as the FINAL crosslinker on "
     "a chromatography matrix — the network would dissociate under "
     "normal elution. Always pair with a covalent secondary crosslink "
     "(BDDE / ECH) before downstream packing."),
]


@dataclass
class FamilyContext:
    """Shared context emitted by the family selector."""

    family: PolymerFamily
    display_name: str


def render_family_selector(*, key: str = "m1v9_polymer_family") -> FamilyContext:
    """Render the polymer-family radio at the top of the M1 tab.

    Default is AGAROSE_CHITOSAN (legacy behaviour, session-state compatible).

    v9.2 (A2.6): the radio shows only UI-enabled families. Tier-2
    placeholder families exist in PolymerFamily but are hidden until v9.3.
    """
    rows = _enabled_rows()
    # v0.4.13: subheader removed — the wrapping section card in tab_m1.py
    # supplies the eyebrow + title via chrome.section_card_header.
    display_names = [row[0] for row in rows]
    enums = [row[1] for row in rows]
    helps = [row[2] for row in rows]

    # v0.4.5: polymer-family selector migrated to labeled_widget.
    from dpsim.visualization.help import get_help, labeled_widget

    sel_name = labeled_widget(
        "Polymer family",
        help=get_help("m1.family"),
        widget=lambda: st.radio(
            "Polymer family",
            display_names,
            index=0,
            horizontal=True,
            key=key,
            label_visibility="collapsed",
        ),
    )
    idx = display_names.index(sel_name)
    family = enums[idx]
    st.caption(f"**{sel_name}** — {helps[idx]}")

    # v0.3.5 (UI audit fix 3): surface ion-gelant registry entries for
    # ionic-gel families. The expander only renders for families that
    # have at least one ION_GELANT_REGISTRY entry; PLGA / agarose-only /
    # dextran etc. skip silently.
    from dpsim.visualization.tabs.m1.ion_gelant_picker import (
        family_has_ion_gelants,
        render_ion_gelant_picker,
    )
    if family_has_ion_gelants(family):
        render_ion_gelant_picker(family, expanded=False, key_prefix=key)

    # v9.5 update: the three Tier-3 multi-variant composites
    # (pectin-chitosan, gellan-alginate, pullulan-dextran) are now
    # selectable above. The preview now records only documented
    # warnings: hazard-rejected Tier-4 chemistries and crosslinker
    # caveats (Al³⁺ non-biotherapeutic, borax reversibility) that
    # contributors should be aware of when configuring formulations.
    with st.expander("Documented warnings: rejected items + crosslinker caveats",
                      expanded=False):
        st.caption(
            "Items documented in the SA screening report as warnings or "
            "rejections rather than separate selectable families. POCl3 "
            "is hazard-rejected (Tier-4 ADR). Al³⁺ trivalent gelation is "
            "implemented but biotherapeutic_safe=False. Borax (borate-"
            "cis-diol) is implemented as a TEMPORARY POROGEN only — its "
            "crosslinks dissociate under normal elution, so it must be "
            "followed by a covalent secondary crosslink (BDDE/ECH) "
            "before downstream packing. Listed here for contributor "
            "awareness."
        )
        for row_name, row_help in _TIER2_PREVIEW_ROWS:
            st.markdown(f"- **{row_name}** — {row_help}")

    return FamilyContext(family=family, display_name=sel_name)

