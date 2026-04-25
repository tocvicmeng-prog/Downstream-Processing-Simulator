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
]


def _enabled_rows() -> list[tuple[str, PolymerFamily, str]]:
    """Return only the display rows whose family is UI-enabled in v9.2.

    Tier-2 placeholder families (HYALURONATE, KAPPA_CARRAGEENAN, …) live in
    the PolymerFamily enum but are filtered out here until their UI
    surface lands in v9.3.
    """
    return [row for row in _FAMILY_DISPLAY if is_family_enabled_in_ui(row[1])]


# v9.3 update: Q-012 Tier-2 preview rows have all been promoted to
# selectable Tier-1 status (v9.3 SEMI_QUANTITATIVE). The preview list
# now records v9.4 Tier-3 families that remain data-only / deferred
# pending future cycles. These are documented but not enabled in the
# enum — they exist purely as informational entries here so users can
# see what's on the v9.4 roadmap.
_TIER2_PREVIEW_ROWS: list[tuple[str, str]] = [
    ("Pectin (calcium pectinate, pectin-chitosan PEC)",
     "v9.4 Tier-3: galacturonic-acid carboxylate ionic gelation; "
     "drug-delivery / food provenance, limited bioprocess relevance."),
    ("Gellan gum (low-acyl, gellan-alginate)",
     "v9.4 Tier-3: K⁺/Ca²⁺/H⁺ helix-aggregation gelation; food / "
     "drug-delivery provenance."),
    ("Pullulan / pullulan-dextran",
     "v9.4 Tier-3: neutral α-glucan; STMP-crosslinked; mostly drug-"
     "delivery applications."),
    ("Crosslinked porous starch",
     "v9.4 Tier-3: STMP / ECH / POCl3 routes; food/industrial provenance, "
     "stability and degradation issues for chromatography."),
    ("Trivalent ion gelants (Al³⁺) — non-biotherapeutic flag",
     "v9.4 Tier-3: gellan ionotropic gelation; residual aluminum is "
     "regulated by FDA/EP. NOT default for biotherapeutic resins."),
    ("Reversible borate-cis-diol crosslinking (borax)",
     "v9.4 Tier-3: temporary porogen / model network; reversible under "
     "elution conditions, not suitable for pressure chromatography."),
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
    st.subheader("Polymer Family")
    display_names = [row[0] for row in rows]
    enums = [row[1] for row in rows]
    helps = [row[2] for row in rows]

    sel_name = st.radio(
        "Polymer family",
        display_names,
        index=0,
        horizontal=True,
        key=key,
        help="Selects the L2 gelation pathway and the set of scientifically "
             "applicable formulation inputs. Only fields that enter the "
             "chosen family's equations will be shown below.",
        label_visibility="collapsed",
    )
    idx = display_names.index(sel_name)
    family = enums[idx]
    st.caption(f"**{sel_name}** — {helps[idx]}")

    # v9.3 update: Tier-2 families have all been promoted (selectable
    # above). The preview now lists v9.4 Tier-3 families that remain
    # deferred pending future cycles.
    with st.expander("v9.4 preview: Tier-3 polymer families (deferred)",
                      expanded=False):
        st.caption(
            "These polymer families are documented in the SA screening "
            "report but deferred to v9.4 because of low bioprocess "
            "relevance (drug-delivery / food provenance), or "
            "biotherapeutic-incompatibility flags. Listed here for "
            "roadmap visibility."
        )
        for tier3_name, tier3_help in _TIER2_PREVIEW_ROWS:
            st.markdown(f"- **{tier3_name}** — {tier3_help}")

    return FamilyContext(family=family, display_name=sel_name)

