"""v9.2 Per-polymer ion-gelation registry (A3.1 + A3.2 + A3.4 + A3.5).

This module replaces the alginate-hardcoded Ca²⁺ assumption with a
generalized (polymer, ion) registry. The Tier-1 cycle (M0a) lands the
schema and the new entries CaSO₄ and KCl as data-only additions; the
alginate solver continues to consume the legacy `AlginateGelantProfile`
unchanged.

The M0b refactor (A3.3) is responsible for:
    1. Adding an adapter that wraps `IonGelantProfile` as the legacy
       `AlginateGelantProfile` shape so `level2_gelation.alginate` does
       not need to change its signature.
    2. Or, alternatively, refactoring the alginate solver to consume
       `IonGelantProfile` directly.

In v9.2 M0a we DO NOT touch `reagent_library_alginate.py` or
`level2_gelation.alginate` — only this new module is added.

References
----------
Carrageenan / κ-carrageenan K⁺ gelation:
    Pereira et al. (2021) *Polymers* 13:471 — κ-/ι-carrageenan
        gelation with K⁺ and Ca²⁺; junction-zone-aggregation model.
Gellan gum:
    Morris et al. (2012) *Carbohydr. Polym.* 89:1054 — low-acyl
        gellan gelation with mono- and divalent cations.
Internal Ca²⁺ release using CaSO₄:
    Drury & Mooney (2003) *Biomaterials* 24:4337 — CaSO₄ vs CaCO₃
        as internal Ca²⁺ source; CaSO₄ has higher solubility
        (Ksp ≈ 4.93 × 10⁻⁵ vs 4.8 × 10⁻⁹ for CaCO₃) → faster but
        still controlled release.
"""

from __future__ import annotations

from dataclasses import dataclass

from dpsim.datatypes import PolymerFamily


# ─── A3.1 — IonGelantProfile dataclass ─────────────────────────────────


@dataclass(frozen=True)
class IonGelantProfile:
    """Profile for a (polymer family, gelant-ion) ionic-gelation pair.

    The key insight of v9.2 A3 is that ionic gelation of anionic
    polysaccharides is governed by polymer-specific ion-selectivity rules:

      - Alginate: Ca²⁺ (egg-box junctions in G-blocks); Sr²⁺/Ba²⁺ also
        bind but are not biotherapeutic-safe.
      - κ-Carrageenan: K⁺ (specific helix-aggregation; Na⁺ does NOT gel).
      - ι-Carrageenan: Ca²⁺ (different junction-zone geometry).
      - Gellan: K⁺/Ca²⁺/H⁺ (low-acyl); helix-aggregation with cations.
      - Pectin: Ca²⁺ (degree-of-esterification dependent); only LM pectin
        gels with Ca²⁺.

    A single polymer can have multiple registered profiles (one per
    valid ion). An ion can be registered against multiple polymers.

    Attributes
    ----------
    polymer_family
        The PolymerFamily this profile applies to.
    ion
        Ion symbol with charge, e.g. "Ca2+", "K+", "Na+", "Sr2+".
    mode
        "external_bath" — pre-formed droplets dropped into ion bath.
        "internal_release" — sparingly-soluble salt dispersed in the
        polymer phase, released by acidification or dissolution.
    C_ion_bath
        Bath concentration [mol/m³] for external mode. Zero for internal.
    C_ion_source
        Total available ion concentration [mol/m³] in the polymer phase
        for internal mode. Zero for external.
    k_release
        Effective first-order release rate [1/s] for internal mode.
    junction_zone_energy
        Approximate Gibbs energy per junction zone [kJ/mol]. Used as
        a proxy for gel strength scaling. Conservative literature values:
        Ca²⁺/alginate ≈ -3 to -8 kJ/mol; K⁺/κ-carrageenan ≈ -2 to -5 kJ/mol.
    stoichiometry
        Moles of polymer charge per mole of ion at saturation. Examples:
        2 (Ca²⁺ bridges 2 alginate carboxylates), 1 (K⁺ binds one
        carrageenan sulfate), variable for gellan.
    biotherapeutic_safe
        Whether this ion is acceptable in a biotherapeutic-grade resin.
        False for Al³⁺, Sr²⁺, Ba²⁺ — these would be rejected at G3.
    T_default
        Recommended bath / process temperature [K].
    t_default
        Recommended gelation time [s].
    suitability
        1-10 score for microsphere production at this (polymer, ion) pair.
    notes
        Free-text rationale, suppliers, hazards, references.
    """

    polymer_family: PolymerFamily
    ion: str
    mode: str  # "external_bath" | "internal_release"
    C_ion_bath: float
    C_ion_source: float
    k_release: float
    junction_zone_energy: float
    stoichiometry: float
    biotherapeutic_safe: bool
    T_default: float
    t_default: float
    suitability: int
    notes: str


# ─── A3.2 — Per-polymer ion-gelation registry ──────────────────────────
#
# Keys are (PolymerFamily, ion_string) tuples. Tier-1 v9.2 registers
# the alginate Ca²⁺ entries (mirroring AlginateGelantProfile data) plus
# the new CaSO₄ entry. Tier-2 ion entries (κ-carrageenan + K⁺, gellan +
# K⁺ / Ca²⁺) are placeholder stubs that land in v9.3 alongside the
# Tier-2 polymer families themselves.

ION_GELANT_REGISTRY: dict[tuple[PolymerFamily, str], IonGelantProfile] = {

    # ── ALGINATE + Ca²⁺ ─ external bath (CaCl₂) ────────────────────────
    (PolymerFamily.ALGINATE, "Ca2+ (CaCl2 external)"): IonGelantProfile(
        polymer_family=PolymerFamily.ALGINATE,
        ion="Ca2+",
        mode="external_bath",
        C_ion_bath=100.0,        # 100 mM, standard recipe
        C_ion_source=0.0,
        k_release=0.0,
        junction_zone_energy=-5.0,
        stoichiometry=2.0,        # 2 carboxylates per Ca²⁺ (egg-box)
        biotherapeutic_safe=True,
        T_default=298.15,
        t_default=1800.0,
        suitability=8,
        notes=(
            "Classical CaCl2 external bath; mirrors GELANTS_ALGINATE "
            "['cacl2_external']. Source: Draget 1997. Shrinking-core "
            "kinetics; inhomogeneous gel for beads > 500 µm."
        ),
    ),

    # ── ALGINATE + Ca²⁺ ─ internal release (GDL/CaCO₃) ────────────────
    (PolymerFamily.ALGINATE, "Ca2+ (GDL/CaCO3 internal)"): IonGelantProfile(
        polymer_family=PolymerFamily.ALGINATE,
        ion="Ca2+",
        mode="internal_release",
        C_ion_bath=0.0,
        C_ion_source=20.0,
        k_release=1.5e-4,         # GDL-limited
        junction_zone_energy=-5.0,
        stoichiometry=2.0,
        biotherapeutic_safe=True,
        T_default=298.15,
        t_default=14400.0,        # 4 h
        suitability=7,
        notes=(
            "Mirrors GELANTS_ALGINATE['gdl_caco3_internal']. Source: "
            "Draget 1997. Homogeneous gel; slow."
        ),
    ),

    # ── ALGINATE + Ca²⁺ ─ internal release (CaSO4) — A3.4 NEW ─────────
    (PolymerFamily.ALGINATE, "Ca2+ (CaSO4 internal)"): IonGelantProfile(
        polymer_family=PolymerFamily.ALGINATE,
        ion="Ca2+",
        mode="internal_release",
        C_ion_bath=0.0,
        # CaSO4 is more soluble than CaCO3 (Ksp 4.93e-5 vs 4.8e-9) — at
        # 20 mM dispersed it saturates faster than CaCO3 / GDL but is
        # still controlled. See Drury & Mooney 2003.
        C_ion_source=20.0,
        # CaSO4 dihydrate (gypsum) dissolution rate-limited; effective
        # release rate ≈ 5e-4 /s (≈ 3× faster than GDL/CaCO3).
        k_release=5e-4,
        junction_zone_energy=-5.0,
        stoichiometry=2.0,
        biotherapeutic_safe=True,
        T_default=298.15,
        t_default=3600.0,         # 1 h plateau, vs 4 h for GDL/CaCO3
        suitability=7,
        notes=(
            "CaSO4-dihydrate internal Ca2+ source. Faster than GDL/CaCO3 "
            "(no acidification step needed) but still gives a more "
            "homogeneous gel than external CaCl2. Source: Drury & "
            "Mooney 2003 Biomaterials 24:4337. Lower hazard than CaCl2 "
            "but introduces sulfate counterion that must be washed out "
            "before downstream chromatography."
        ),
    ),

    # ── KAPPA_CARRAGEENAN + K⁺ — v9.3 Tier-2 entry ───────────────────
    (PolymerFamily.KAPPA_CARRAGEENAN, "K+ (KCl external)"): IonGelantProfile(
        polymer_family=PolymerFamily.KAPPA_CARRAGEENAN,
        ion="K+",
        mode="external_bath",
        # κ-carrageenan gels strongly with K⁺ via specific helix
        # aggregation: K⁺ binds inside double-helix junctions at
        # ~100–300 mM (Pereira 2021).
        C_ion_bath=200.0,
        C_ion_source=0.0,
        k_release=0.0,
        # Junction-zone energy is similar magnitude to Ca²⁺/alginate;
        # κ-carrageenan gels are typically softer than alginate.
        junction_zone_energy=-3.5,
        stoichiometry=1.0,             # 1 K⁺ binds one sulfate-pair junction
        biotherapeutic_safe=True,
        T_default=298.15,
        t_default=600.0,                # 10 min — fast K⁺ diffusion
        suitability=7,
        notes=(
            "κ-Carrageenan gels strongly with K⁺ (specific helix-"
            "aggregation; Na⁺ does NOT gel). ι-Carrageenan responds "
            "preferentially to Ca²⁺. Source: Pereira et al. 2021 "
            "Polymers 13:471."
        ),
    ),

    # ── HYALURONATE + Ca²⁺ — v9.3 Tier-2 entry (cation-only gelation
    # is weak for HA; the canonical HA bead chemistry is covalent
    # crosslinking via BDDE/HRP-tyramine/ADH). The entry below records
    # ionic Ca²⁺ as a CO-FACTOR only, with low suitability.
    (PolymerFamily.HYALURONATE, "Ca2+ (cofactor)"): IonGelantProfile(
        polymer_family=PolymerFamily.HYALURONATE,
        ion="Ca2+",
        mode="external_bath",
        C_ion_bath=20.0,
        C_ion_source=0.0,
        k_release=0.0,
        junction_zone_energy=-1.5,     # weak — HA carboxylate density is low
        stoichiometry=2.0,
        biotherapeutic_safe=True,
        T_default=298.15,
        t_default=3600.0,
        suitability=3,                  # low — HA is primarily covalently crosslinked
        notes=(
            "Ca²⁺ provides only weak ionic stabilisation of HA networks "
            "(carboxylate density is much lower than alginate). The "
            "canonical v9.3 HA bead chemistry is covalent crosslinking "
            "(BDDE per Hahn 2006, HRP-tyramine per Sakai 2009, or "
            "oxidized-HA + ADH). Listed here for completeness; suitability "
            "score 3/10."
        ),
    ),

    # ─── v9.4 Tier-3 ionic-gelation entries ───────────────────────────

    # PECTIN + Ca²⁺ — galacturonic-acid carboxylate ionic gelation.
    # Strength depends on degree of esterification (DE): low-methoxy
    # pectin (LM, DE < 50%) gels strongly with Ca²⁺; high-methoxy (HM,
    # DE > 50%) requires acid + sugar (sugar-acid gel).
    # Voragen et al. 2009 Struct. Chem. 20:263.
    (PolymerFamily.PECTIN, "Ca2+ (LM pectin)"): IonGelantProfile(
        polymer_family=PolymerFamily.PECTIN,
        ion="Ca2+",
        mode="external_bath",
        C_ion_bath=50.0,                # 50 mM CaCl2 typical for LM pectin
        C_ion_source=0.0,
        k_release=0.0,
        junction_zone_energy=-4.0,
        stoichiometry=2.0,
        biotherapeutic_safe=True,
        T_default=298.15,
        t_default=1800.0,
        suitability=5,                  # niche bioprocess relevance
        notes=(
            "Low-methoxy pectin (DE < 50%) gels strongly with Ca²⁺ via "
            "egg-box-analogous junction zones in galacturonic-acid "
            "blocks. Voragen 2009. Bioprocess relevance is limited "
            "(food / drug-delivery dominates); suitability 5/10."
        ),
    ),

    # GELLAN + K⁺ — low-acyl gellan helix-aggregation.
    # Morris et al. 2012 Carbohydr. Polym. 89:1054.
    (PolymerFamily.GELLAN, "K+ (low-acyl)"): IonGelantProfile(
        polymer_family=PolymerFamily.GELLAN,
        ion="K+",
        mode="external_bath",
        C_ion_bath=100.0,                # 100 mM KCl typical
        C_ion_source=0.0,
        k_release=0.0,
        junction_zone_energy=-3.5,
        stoichiometry=1.0,
        biotherapeutic_safe=True,
        T_default=298.15,
        t_default=900.0,
        suitability=4,                  # food/drug-delivery dominant
        notes=(
            "Low-acyl gellan helix-aggregation with K⁺ (and Na⁺ to a "
            "lesser extent). Morris 2012. Compositionally similar to "
            "κ-carrageenan + K⁺ but with weaker junction-zone energy. "
            "Food / drug-delivery provenance; suitability 4/10."
        ),
    ),

    # GELLAN + Ca²⁺ — divalent ion variant.
    (PolymerFamily.GELLAN, "Ca2+ (low-acyl)"): IonGelantProfile(
        polymer_family=PolymerFamily.GELLAN,
        ion="Ca2+",
        mode="external_bath",
        C_ion_bath=20.0,
        C_ion_source=0.0,
        k_release=0.0,
        junction_zone_energy=-4.5,     # stronger than K⁺
        stoichiometry=2.0,
        biotherapeutic_safe=True,
        T_default=298.15,
        t_default=600.0,
        suitability=5,
        notes=(
            "Low-acyl gellan + Ca²⁺ — stronger junction zones than K⁺ "
            "but more brittle gel. Morris 2012."
        ),
    ),

    # GELLAN + Al³⁺ — research-mode trivalent ion gelant.
    # Suitability is intentionally low; biotherapeutic_safe=False.
    (PolymerFamily.GELLAN, "Al3+ (research, non-biotherapeutic)"): IonGelantProfile(
        polymer_family=PolymerFamily.GELLAN,
        ion="Al3+",
        mode="external_bath",
        C_ion_bath=10.0,
        C_ion_source=0.0,
        k_release=0.0,
        junction_zone_energy=-7.0,     # strongest — trivalent
        stoichiometry=3.0,
        biotherapeutic_safe=False,      # CRITICAL — Al³⁺ residue regulated by FDA/EP
        T_default=298.15,
        t_default=300.0,
        suitability=2,                  # very low — non-biotherapeutic
        notes=(
            "TRIVALENT GELANT — NOT FOR BIOTHERAPEUTIC RESINS. Strongest "
            "ionic crosslinking (3 carboxylates per Al³⁺) but residual "
            "aluminum is regulated by FDA/EP. Use only for research / "
            "non-biotherapeutic applications. The is_biotherapeutic_safe "
            "gate will block this from default workflows."
        ),
    ),
}


# ─── A3.5 — KCl ion gelant entry (data-only; consumer in v9.3) ──────
#
# KCl is registered as a "freestanding" gelant entry that κ-carrageenan
# and gellan will consume in v9.3. Storing it in a separate table from
# the (polymer, ion) registry avoids the Tier-1 / Tier-2 coupling: the
# entry exists so M0b's adapter can validate it, but the registry
# itself does not yet know which polymer to pair it with.

@dataclass(frozen=True)
class FreestandingIonGelant:
    """Standalone ion-gelant chemistry, not yet bound to a specific polymer.

    Used by Tier-2 polymer families which will register pairings in v9.3.
    """

    ion: str                  # e.g. "K+", "Ca2+", "Sr2+", "Al3+"
    cas: str
    biotherapeutic_safe: bool
    typical_C_bath_mM: float  # typical bath concentration range midpoint
    notes: str


FREESTANDING_ION_GELANTS: dict[str, FreestandingIonGelant] = {
    "kcl": FreestandingIonGelant(
        ion="K+",
        cas="7447-40-7",
        biotherapeutic_safe=True,
        typical_C_bath_mM=200.0,
        notes=(
            "K+ specifically gels kappa-carrageenan via helix-aggregation "
            "(K+ binds inside the double-helix junction zones). Na+ does "
            "NOT gel kappa-carrageenan. Also gels gellan and is one of "
            "the choices for low-acyl gellan ionotropic gelation. "
            "Source: Pereira et al. 2021 Polymers 13:471."
        ),
    ),
    "caso4": FreestandingIonGelant(
        ion="Ca2+",
        cas="10101-41-4",  # gypsum / CaSO4·2H2O
        biotherapeutic_safe=True,
        typical_C_bath_mM=20.0,
        notes=(
            "CaSO4-dihydrate (gypsum) — sparingly soluble Ca2+ source for "
            "internal-release alginate gelation. See registry entry "
            "(ALGINATE, 'Ca2+ (CaSO4 internal)') for the bound profile. "
            "Source: Drury & Mooney 2003."
        ),
    ),
    # ─── v9.4 Tier-3 freestanding gelants ────────────────────────────
    "alcl3": FreestandingIonGelant(
        ion="Al3+",
        cas="7446-70-0",
        biotherapeutic_safe=False,      # CRITICAL — FDA/EP regulated
        typical_C_bath_mM=10.0,
        notes=(
            "TRIVALENT IONIC GELANT — NOT FOR BIOTHERAPEUTIC RESINS. "
            "Residual aluminum is regulated by FDA/EP and induces "
            "proteinopathy concerns. Use only for research / non-"
            "biotherapeutic applications. is_biotherapeutic_safe_ion "
            "returns False so the default-workflow gate blocks it."
        ),
    ),
    "borax": FreestandingIonGelant(
        ion="B(OH)4-",
        cas="1303-96-4",
        biotherapeutic_safe=True,        # borate is biotherapeutic-safe
        typical_C_bath_mM=50.0,
        notes=(
            "Borax / borate-cis-diol REVERSIBLE crosslinker. Forms borate "
            "ester with cis-diols at pH > 8.5; dissociates at low pH or "
            "with competing diols/sugars. NOT suitable as a final "
            "chromatography crosslinker because the network dissociates "
            "under normal elution conditions. Useful as TEMPORARY POROGEN "
            "or model network during synthesis, then hardened with "
            "covalent crosslinker (BDDE/ECH). See "
            "borax_reversible_crosslinking ReagentProfile."
        ),
    ),
}


# ─── Public query functions ────────────────────────────────────────────


def get_ion_gelant(
    polymer_family: PolymerFamily, gelant_key: str
) -> IonGelantProfile | None:
    """Return the IonGelantProfile for a (family, key) pair, or None."""
    return ION_GELANT_REGISTRY.get((polymer_family, gelant_key))


def list_ion_gelants_for_family(
    polymer_family: PolymerFamily,
) -> tuple[IonGelantProfile, ...]:
    """Return all registered ion-gelant profiles for one polymer family."""
    return tuple(
        p for (fam, _key), p in ION_GELANT_REGISTRY.items()
        if fam.value == polymer_family.value
    )


def is_biotherapeutic_safe_ion(ion_or_key: str) -> bool:
    """Return True if the ion (or freestanding key) is biotherapeutic-safe.

    Returns False for Al³⁺ (residual aluminum regulated by FDA/EP),
    Sr²⁺, Ba²⁺ (residual ion contamination concerns).
    """
    if ion_or_key in FREESTANDING_ION_GELANTS:
        return FREESTANDING_ION_GELANTS[ion_or_key].biotherapeutic_safe
    # Fall through: search registry by ion column
    for profile in ION_GELANT_REGISTRY.values():
        if profile.ion == ion_or_key:
            return profile.biotherapeutic_safe
    # Conservative default: unknown ion is rejected
    return False


__all__ = [
    "IonGelantProfile",
    "ION_GELANT_REGISTRY",
    "FreestandingIonGelant",
    "FREESTANDING_ION_GELANTS",
    "get_ion_gelant",
    "list_ion_gelants_for_family",
    "is_biotherapeutic_safe_ion",
    # A3.3 adapter
    "to_alginate_gelant_profile",
]


# ─── A3.3 — IonGelantProfile → legacy AlginateGelantProfile adapter ────
#
# The existing alginate solver (level2_gelation.ionic_ca,
# reagent_library_alginate.GELANTS_ALGINATE) consumes the legacy
# AlginateGelantProfile shape. Rather than refactor the solver and risk
# breaking calibrated v9.1 behaviour, we provide an adapter that
# translates a registry IonGelantProfile to the legacy shape. This is
# the schema-equivalence guarantee for A3.3:
#
#   For every (PolymerFamily.ALGINATE, key) entry in ION_GELANT_REGISTRY
#   that has a corresponding entry in GELANTS_ALGINATE, the adapter
#   produces an AlginateGelantProfile with bit-for-bit-equivalent
#   numerical fields (C_Ca_bath, C_Ca_source, k_release, T_default,
#   t_default).
#
# A3.6 (regression suite) verifies this invariant on the existing
# legacy entries.


def to_alginate_gelant_profile(profile: IonGelantProfile):
    """Translate an alginate IonGelantProfile to the legacy
    AlginateGelantProfile shape.

    Raises ValueError if the profile is not for alginate or if its ion
    is not Ca²⁺ (the legacy AlginateGelantProfile shape only models
    calcium gelation).

    The returned object is a real `AlginateGelantProfile` (imported
    lazily to avoid circular import at package load).
    """
    from dpsim.reagent_library_alginate import AlginateGelantProfile

    if profile.polymer_family.value != PolymerFamily.ALGINATE.value:
        raise ValueError(
            f"AlginateGelantProfile adapter only supports ALGINATE "
            f"profiles, got {profile.polymer_family.value!r}"
        )
    if profile.ion != "Ca2+":
        raise ValueError(
            f"AlginateGelantProfile shape models Ca2+ only, got "
            f"{profile.ion!r}"
        )

    return AlginateGelantProfile(
        name=f"[adapter] {profile.ion} ({profile.mode})",
        cas="(via ion-registry adapter)",
        mode=profile.mode,
        C_Ca_bath=profile.C_ion_bath,
        C_Ca_source=profile.C_ion_source,
        k_release=profile.k_release,
        T_default=profile.T_default,
        t_default=profile.t_default,
        suitability=profile.suitability,
        notes=(
            f"v9.2 ion-registry adapter (A3.3). Original: "
            f"{profile.notes}"
        ),
    )
