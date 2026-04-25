"""Reagent profiles for Module 2 functionalization chemistry.

Phase B: Minimal Module 2 — 2 Workflows.
Architecture: module2_module3_final_implementation_plan.md, Phase B.

Only 4 reagent profiles needed for Phase B:
  - genipin_secondary: Secondary amine crosslinking (genipin)
  - glutaraldehyde_secondary: Secondary amine crosslinking (glutaraldehyde)
  - ech_activation: Hydroxyl activation with epichlorohydrin
  - dvs_activation: Hydroxyl activation with divinyl sulfone

Phase 2 expansion (Module 2 extension) adds 10 further profiles:
  Ligand coupling (4): deae_coupling, ida_coupling, phenyl_coupling, sp_coupling
  Protein coupling (2): protein_a_coupling, protein_g_coupling
  Quenching (4): ethanolamine_quench, mercaptoethanol_quench, nabh4_quench,
                 acetic_anhydride_quench

Follows the CrosslinkerProfile pattern from reagent_library.py.
Literature values sourced from the Scientific Advisor report.

Crosslinker registry split (v0.3.5 documentation, UI audit fix 5)
-----------------------------------------------------------------
DPSim carries TWO crosslinker registries with non-overlapping content:

  1. ``dpsim.reagent_library.CROSSLINKERS`` — drives the **L3 / M1
     covalent-hardening** step (primary crosslinking applied during
     gelation or post-gelation hardening of the polymer matrix
     itself). Consumed by the M1 crosslinking_section.py widget.
  2. ``REAGENT_PROFILES[functional_mode='crosslinker']`` (this module)
     — drives the **M2 secondary-crosslinking step** (additional
     crosslinking applied AFTER ligand coupling for stability).
     Consumed by the M2 "Secondary Crosslinking" bucket via
     ``visualization.tabs.tab_m2._BUCKET_TO_MODES``.

The split is intentional. Some chemistries (genipin, glutaraldehyde,
STMP) appear in both registries with different parameter contexts: L3
entries carry M1-stage kinetic defaults, while M2 ``_secondary``
variants carry post-coupling stage defaults. This lets the same
chemistry be tuned independently for primary vs secondary crosslinking.

Do not consolidate without first identifying every consumer of each
registry; the v0.3.3 audit confirmed both are load-bearing for
distinct UI surfaces.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .acs import ACSSiteType


# ─── v9.2 vocabulary constants (A4.1 + A5.1) ───────────────────────────
#
# `functional_mode` and `chemistry_class` are open strings on ReagentProfile
# for forward compatibility, but every value must come from these closed
# vocabularies. New values must be added here AND documented in the SA
# screening report § 6.1 before any new ReagentProfile entry uses them.

ALLOWED_FUNCTIONAL_MODES: frozenset[str] = frozenset({
    # v9.1 baseline (full canonical set including specialised modes
    # already in REAGENT_PROFILES at v9.1 close)
    "crosslinker",
    "activator",
    "iex_ligand",
    "affinity_ligand",
    "hic_ligand",
    "imac_chelator",
    "quencher",
    "spacer",
    "washing",
    "metal_charging",
    "protein_pretreatment",
    "biotin_affinity",
    "gst_affinity",
    "heparin_affinity",
    "heterobifunctional_crosslinker",
    # v9.2 additions (SA screening § 6.1)
    "dye_pseudo_affinity",   # Cibacron Blue, Procion Red — triazine dye ligands
    "mixed_mode_hcic",       # MEP HyperCel — pH-switchable hydrophobic↔cationic
    "thiophilic",            # T-Sorb / T-Gel salt-promoted IgG capture
    "peptide_affinity",      # HWRGWV-class peptide ligands
    "boronate",              # aminophenylboronic-acid cis-diol affinity
    "oligonucleotide",       # sequence-specific DNA/RNA affinity
    "click_handle",          # CuAAC / SPAAC modular ligand-library handles
    "material_as_ligand",    # amylose-MBP, chitin-CBD — polymer is the affinity matrix
})

ALLOWED_CHEMISTRY_CLASSES: frozenset[str] = frozenset({
    # v9.1 baseline (full canonical set, including specialised classes
    # used by existing REAGENT_PROFILES entries at v9.1 close)
    "epoxide_amine",
    "epoxide_amine_spacer",
    "epoxide_thiol",
    "epoxide_hydrazide",
    "vs_amine",
    "vs_amine_thiol",
    "vs_thiol",
    "aldehyde_amine",
    "hydrazide_aldehyde",
    "reduction",
    "acetylation",
    "amine_covalent",
    "edc_nhs",
    "nhs_amine",
    "maleimide_thiol",
    "metal_chelation",
    "phosphorylation_alkaline",
    "diffusion_out",
    # v9.2 additions (SA screening § 6.1)
    "oxime",                 # aldehyde + aminooxy → oxime (more stable than hydrazone)
    "hydrazone",             # aldehyde + hydrazide → hydrazone (reversible at low pH)
    "cuaac",                 # Cu-catalyzed azide-alkyne cycloaddition
    "spaac",                 # strain-promoted azide-alkyne cycloaddition (copper-free)
    "dye_triazine",          # cyanuric-chloride-based dye attachment
    "cnbr_amine",            # CNBr-activated cyanate ester + amine ligand
    "cdi_amine",             # CDI-activated imidazolyl carbonate + amine ligand
    "glyoxyl_multipoint",    # multi-point Lys coupling via glyoxyl-agarose
    "phenol_radical",        # HRP/H2O2 tyramine-radical coupling
})


def validate_functional_mode(mode: str) -> None:
    """Raise ValueError if ``mode`` is not in ALLOWED_FUNCTIONAL_MODES.

    Empty string is allowed (means "unspecified"); any other value must be
    in the closed vocabulary.
    """
    if mode and mode not in ALLOWED_FUNCTIONAL_MODES:
        raise ValueError(
            f"Unknown functional_mode {mode!r}. "
            f"Add to ALLOWED_FUNCTIONAL_MODES (reagent_profiles.py) "
            f"and document in SA screening report before use."
        )


def validate_chemistry_class(cls: str) -> None:
    """Raise ValueError if ``cls`` is not in ALLOWED_CHEMISTRY_CLASSES.

    Empty string is allowed (means "unspecified"); any other value must be
    in the closed vocabulary.
    """
    if cls and cls not in ALLOWED_CHEMISTRY_CLASSES:
        raise ValueError(
            f"Unknown chemistry_class {cls!r}. "
            f"Add to ALLOWED_CHEMISTRY_CLASSES (reagent_profiles.py) "
            f"and document in SA screening report before use."
        )


@dataclass
class ReagentProfile:
    """Profile for a Module 2 functionalization reagent.

    Maps directly to the reaction engine inputs in reactions.py.
    Follows the CrosslinkerProfile pattern from reagent_library.py.

    Attributes:
        name: Human-readable reagent name.
        cas: CAS registry number.
        reaction_type: Chemistry category ("crosslinking", "activation", "blocking").
        target_acs: ACS site type consumed by this reagent.
        product_acs: ACS site type produced (None for crosslinking).
        k_forward: Forward rate constant at reference T [m^3/(mol*s)].
        E_a: Activation energy [J/mol].
        stoichiometry: Moles reagent consumed per mole ACS consumed [-].
        hydrolysis_rate: First-order hydrolysis rate constant [1/s].
        ph_optimum: Optimal pH for reaction [-].
        temperature_default: Default reaction temperature [K].
        time_default: Default reaction time [s].
        notes: Literature references and notes.

        # ── Extended identity (Phase 2) ──
        reagent_identity: Chemical name of actual reactive form.
        installed_ligand: Functional group after coupling.
        functional_mode: One of "crosslinker", "activator", "iex_ligand",
            "affinity_ligand", "hic_ligand", "imac_chelator", "quencher".
        chemistry_class: One of "epoxide_amine", "epoxide_thiol", "vs_amine",
            "vs_thiol", "aldehyde_amine", "reduction", "acetylation",
            "amine_covalent".

        # ── Validity windows ──
        ph_min: Minimum valid pH [-].
        ph_max: Maximum valid pH [-].
        temperature_min: Minimum valid temperature [K].
        temperature_max: Maximum valid temperature [K].

        # ── Macromolecule fields ──
        ligand_mw: Ligand molecular weight [Da].
        ligand_r_h: Hydrodynamic radius [m].
        is_macromolecule: True if ligand is a macromolecule (protein, etc.).
        activity_retention: Fraction of activity retained after coupling [0, 1].
        activity_retention_uncertainty: Uncertainty on activity_retention [0, 1].
        max_surface_density: Steric jamming limit [mol/m^2].

        # ── Metadata ──
        confidence_tier: "semi_quantitative" or "ranking_only".
        calibration_source: Source or rationale for kinetic parameters.
        hazard_class: GHS / lab hazard descriptor string.
    """
    name: str
    cas: str
    reaction_type: str
    target_acs: ACSSiteType
    product_acs: Optional[ACSSiteType]
    k_forward: float         # [m^3/(mol*s)] at reference T
    E_a: float               # [J/mol]
    stoichiometry: float     # [-]
    hydrolysis_rate: float = 0.0   # [1/s]
    ph_optimum: float = 7.0
    temperature_default: float = 298.15  # [K]
    time_default: float = 3600.0         # [s]
    notes: str = ""

    # ── Extended identity (Phase 2) ──
    reagent_identity: str = ""         # Chemical name of actual reactive form
    installed_ligand: str = ""         # Functional group after coupling
    functional_mode: str = ""          # "crosslinker", "activator", "iex_ligand", "affinity_ligand", "hic_ligand", "imac_chelator", "quencher"
    chemistry_class: str = ""          # "epoxide_amine", "epoxide_thiol", "vs_amine", "vs_thiol", "aldehyde_amine", "reduction", "acetylation"

    # ── Validity windows ──
    ph_min: float = 0.0
    ph_max: float = 14.0
    temperature_min: float = 273.15    # [K]
    temperature_max: float = 373.15    # [K]

    # ── Macromolecule fields ──
    ligand_mw: float = 0.0            # [Da]
    ligand_r_h: float = 0.5e-9        # [m] hydrodynamic radius
    is_macromolecule: bool = False
    activity_retention: float = 1.0    # [0,1]
    activity_retention_uncertainty: float = 0.0
    max_surface_density: float = 0.0   # [mol/m^2] steric jamming limit

    # ── Spacer arm support (Phase 1 multiplier model) ──
    spacer_key: str = ""                    # Reference to spacer profile key (empty = direct)
    spacer_length_angstrom: float = 0.0     # Spacer length [angstrom]
    spacer_activity_multiplier: float = 1.0 # Multiplier on activity_retention [>=1.0]

    # ── Charge type for IEX (audit F14) ──
    charge_type: str = ""                   # "anion", "cation", ""

    # ── IMAC metal state (audit F5) ──
    metal_ion: str = ""                     # "Ni2+", "Co2+", "Cu2+", "Zn2+", ""
    metal_loaded_fraction: float = 1.0      # [0,1] assumed metal loading

    # ── Binding model hint for M3 (audit F15) ──
    binding_model_hint: str = ""            # "charge_exchange", "metal_chelation",
                                            # "salt_promoted", "fc_affinity",
                                            # "gst_glutathione", "near_irreversible",
                                            # "mixed_mode", ""

    # ── v5.8 fields (audit F2/F3/F4/F5/F10/F15) ──
    profile_role: str = "final_ligand"      # "native", "activated", "spacer_intermediate",
                                             # "heterobifunctional_intermediate", "final_ligand",
                                             # "spacer_metadata", "quencher"
    m3_support_level: str = "mapped_estimated"  # "mapped_quantitative", "mapped_estimated",
                                                 # "not_mapped", "requires_user_calibration"
    distal_group_yield: float = 1.0         # Fraction consumed sites producing distal group [0,1]
    maleimide_decay_rate: float = 0.0       # [1/s] first-order hydrolysis of immobilized maleimide
    buffer_incompatibilities: str = ""      # Comma-separated: "Tris,glycine,DTT"
    requires_reduced_thiol: bool = False    # True for maleimide-thiol coupling
    thiol_accessibility_fraction: float = 1.0  # Fraction of protein Cys accessible [0,1]

    # ── v5.9.1-5.9.4 fields ──
    metal_association_constant: float = 0.0  # [m3/mol] metal-chelator association constant
    reduction_efficiency: float = 0.95       # [0,1] protein pretreatment efficiency
    regulatory_limit_ppm: float = 0.0        # [ppm] for washing compliance check
    pKa_nucleophile: float = 0.0             # pH scaling (0 = disabled)

    # ── Metadata ──
    confidence_tier: str = "semi_quantitative"
    calibration_source: str = ""
    hazard_class: str = ""


# ─── Phase B Reagent Library (4 profiles) ─────────────────────────────

REAGENT_PROFILES: dict[str, ReagentProfile] = {

    # ── 1. Genipin secondary crosslinking ─────────────────────────────
    # Butler et al. (2003): k ~ 0.002 L/(mol*s) = 2e-6 m^3/(mol*s) at 37 degC
    # E_a ~ 45-55 kJ/mol.  1 genipin bridges 2 NH2 groups (stoich = 0.5).
    "genipin_secondary": ReagentProfile(
        name="Genipin (secondary crosslinking)",
        cas="6902-77-8",
        reaction_type="crosslinking",
        target_acs=ACSSiteType.AMINE_PRIMARY,
        product_acs=None,
        k_forward=2e-6,          # [m^3/(mol*s)] at 37 degC
        E_a=45000.0,             # [J/mol]
        stoichiometry=0.5,       # 1 genipin per 2 NH2
        hydrolysis_rate=0.0,
        ph_optimum=7.4,
        temperature_default=310.15,  # 37 degC
        time_default=14400.0,        # 4 h
        functional_mode="crosslinker",
        chemistry_class="amine_covalent",
        ph_min=6.0,
        ph_max=9.0,
        notes=(
            "Secondary crosslinking after primary L3 genipin cure. "
            "Butler et al. (2003) J. Polym. Sci. A: Polym. Chem. 41:3941. "
            "Low cytotoxicity, FDA-approved colorant."
        ),
    ),

    # ── 2. Glutaraldehyde secondary crosslinking ──────────────────────
    # Migneault et al. (2004): k ~ 0.01 L/(mol*s) = 1e-5 m^3/(mol*s)
    # E_a ~ 35-40 kJ/mol.  1 glutaraldehyde bridges 2 NH2 (Schiff base).
    "glutaraldehyde_secondary": ReagentProfile(
        name="Glutaraldehyde (secondary crosslinking)",
        cas="111-30-8",
        reaction_type="crosslinking",
        target_acs=ACSSiteType.AMINE_PRIMARY,
        product_acs=None,
        k_forward=1e-5,          # [m^3/(mol*s)]
        E_a=40000.0,             # [J/mol]
        stoichiometry=0.5,       # 1 GA per 2 NH2 (Schiff base bridge)
        hydrolysis_rate=0.0,
        ph_optimum=7.0,
        temperature_default=298.15,  # 25 degC
        time_default=3600.0,         # 1 h
        functional_mode="crosslinker",
        chemistry_class="amine_covalent",
        ph_min=6.0,
        ph_max=8.0,
        hazard_class="toxic",
        notes=(
            "Schiff base crosslinking of primary amines. Fast kinetics. "
            "Migneault et al. (2004) BioTechniques 37:790."
        ),
    ),

    # ── 3. Epichlorohydrin (ECH) activation ───────────────────────────
    # Sundberg & Porath (1974): ECH reacts with OH under alkaline conditions
    # to introduce epoxide groups.  Significant hydrolysis at pH > 11.
    # k ~ 1.5e-5 m^3/(mol*s), E_a ~ 60 kJ/mol.
    # Hydrolysis rate ~ 1e-4 /s at pH 12, 25 degC.
    "ech_activation": ReagentProfile(
        name="Epichlorohydrin (OH activation)",
        cas="106-89-8",
        reaction_type="activation",
        target_acs=ACSSiteType.HYDROXYL,
        product_acs=ACSSiteType.EPOXIDE,
        k_forward=1.5e-5,        # [m^3/(mol*s)]
        E_a=60000.0,             # [J/mol]
        stoichiometry=1.0,       # 1 ECH per OH consumed
        hydrolysis_rate=1e-4,    # [1/s] at pH 12
        ph_optimum=12.0,
        temperature_default=298.15,  # 25 degC
        time_default=7200.0,         # 2 h
        functional_mode="activator",
        chemistry_class="epoxide_amine",
        ph_min=10.0,
        ph_max=13.0,
        hazard_class="toxic_carcinogen",
        notes=(
            "Alkaline activation of agarose hydroxyl groups. "
            "Introduces epoxide for subsequent ligand coupling. "
            "Sundberg & Porath (1974) J. Chromatogr. 90:87. "
            "Competing hydrolysis significant at pH > 11."
        ),
    ),

    # ── 4. Divinyl sulfone (DVS) activation ───────────────────────────
    # Porath & Fornstedt (1970): DVS reacts with OH to introduce vinyl
    # sulfone groups.  More stable than ECH epoxides (no hydrolysis).
    # k ~ 5e-6 m^3/(mol*s), E_a ~ 55 kJ/mol.
    "dvs_activation": ReagentProfile(
        name="Divinyl sulfone (OH activation)",
        cas="77-77-0",
        reaction_type="activation",
        target_acs=ACSSiteType.HYDROXYL,
        product_acs=ACSSiteType.VINYL_SULFONE,
        k_forward=5e-6,          # [m^3/(mol*s)]
        E_a=55000.0,             # [J/mol]
        stoichiometry=1.0,       # 1 DVS per OH consumed
        hydrolysis_rate=0.0,     # Negligible hydrolysis
        ph_optimum=11.0,
        temperature_default=298.15,  # 25 degC
        time_default=3600.0,         # 1 h
        functional_mode="activator",
        chemistry_class="vs_amine",
        ph_min=10.0,
        ph_max=12.0,
        hazard_class="toxic",
        notes=(
            "Alkaline activation of agarose hydroxyl groups. "
            "Introduces vinyl sulfone for nucleophilic coupling. "
            "Porath & Fornstedt (1970) J. Chromatogr. 51:479. "
            "More hydrolytically stable than ECH epoxides."
        ),
    ),

    # ── 4b. Sodium Trimetaphosphate (STMP) secondary crosslinking ─────
    # STMP (Na3P3O9, CAS 7785-84-4) is the cyclic trimetaphosphate (NOT
    # the linear tripolyphosphate STPP / CAS 7758-29-4). Under alkaline
    # conditions (pH 10-12, T 40-70 degC), it ring-opens and crosslinks
    # agarose -OH groups via phosphate diesters (dominant) with a slower
    # phosphoramide side-reaction on chitosan -NH2. Triggerable protocol
    # (cold/neutral load, hot/alkaline activate) permits homogeneous
    # crosslinking of pre-gelled beads; see Appendix J.1.7 for the full
    # wet-lab procedure.
    #
    # Kinetic parameters calibrated to Lim & Seib (1993) Cereal Chem.
    # 70:137: k(60 degC, pH 11) ~ 1e-4 m^3/(mol*s); Ea ~ 75 kJ/mol.
    # Stoichiometry 0.5 = 1 STMP bridges 2 -OH.
    "stmp_secondary": ReagentProfile(
        name="Sodium Trimetaphosphate (STMP, secondary crosslinking)",
        cas="7785-84-4",
        reaction_type="crosslinking",
        target_acs=ACSSiteType.HYDROXYL,
        product_acs=None,
        k_forward=1e-4,          # [m^3/(mol*s)] at T_ref = 60 degC
        E_a=75000.0,             # [J/mol] ring-opening barrier
        stoichiometry=0.5,       # 1 STMP bridges 2 -OH (diester crosslink)
        hydrolysis_rate=1e-5,    # [1/s] at pH 11, 60 degC (Van Wazer 1958)
        ph_optimum=11.0,
        temperature_default=333.15,  # 60 degC (Phase B activation)
        time_default=9000.0,         # 2.5 h (0.5 h Phase A + 2 h Phase B)
        functional_mode="crosslinker",
        chemistry_class="phosphorylation_alkaline",
        ph_min=10.0,
        ph_max=11.5,
        temperature_min=277.15,      # 4 degC (Phase A loading)
        temperature_max=343.15,      # 70 degC (safe cap; 90 degC hard limit)
        confidence_tier="semi_quantitative",
        calibration_source=(
            "Lim & Seib (1993) Cereal Chem. 70:137 starch phosphorylation; "
            "Kasemsuwan & Jane (1996) Cereal Chem. 73:702 diester yield; "
            "Lack et al. (2004) Carbohydr. Res. 339:2391 hyaluronan."
        ),
        notes=(
            "Food-grade (E452) triggerable covalent crosslinker. First "
            "HYDROXYL-targeted secondary crosslinker in the library. "
            "Two-phase protocol: cold/neutral loading (4 degC, pH 7) then "
            "hot/alkaline activation (60 degC, pH 11). Thiele-modulus "
            "homogeneous for bead radius < 500 um. Co-reacts with "
            "chitosan -NH2 via phosphoramide (SEMI_QUANTITATIVE as of "
            "v9.2.2 -- parallel NH2 ODE track in the L3 solver with "
            "k0=4.5e3, Ea=60 kJ/mol, f_bridge=0.35; see reagent_library."
            "NH2CoReaction and SA-DPSIM-XL-002 Rev 0.1). Distinguish "
            "from 'tpp' (STPP, ionic, acidic pH). See Appendix J.1.7."
        ),
    ),

    # ─── Phase 2 Expansion — Ligand Coupling (4) ──────────────────────

    # ── 5. DEAE coupling ──────────────────────────────────────────────
    "deae_coupling": ReagentProfile(
        name="DEAE (weak anion exchange)",
        cas="100-36-7",
        reagent_identity="2-(Diethylamino)ethylamine",
        installed_ligand="DEAE",
        functional_mode="iex_ligand",
        reaction_type="coupling",
        chemistry_class="epoxide_amine",
        target_acs=ACSSiteType.EPOXIDE,
        product_acs=None,
        k_forward=5e-5,
        E_a=50000.0,
        stoichiometry=1.0,
        hydrolysis_rate=1e-5,
        ph_optimum=10.5,
        ph_min=9.0, ph_max=12.0,
        temperature_default=298.15,
        temperature_min=288.15, temperature_max=313.15,
        time_default=14400.0,
        ligand_mw=116.0,
        ligand_r_h=0.4e-9,
        charge_type="anion",
        binding_model_hint="charge_exchange",
        confidence_tier="semi_quantitative",
        calibration_source="Estimated from general epoxide-amine kinetics",
        notes="Weak anion exchanger; pKa ~11.5; fully charged below pH 9",
    ),

    # ── 6. IDA coupling ───────────────────────────────────────────────
    "ida_coupling": ReagentProfile(
        name="IDA (IMAC chelator)",
        cas="142-73-4",
        reagent_identity="Iminodiacetic acid",
        installed_ligand="IDA",
        functional_mode="imac_chelator",
        reaction_type="coupling",
        chemistry_class="epoxide_amine",
        target_acs=ACSSiteType.EPOXIDE,
        product_acs=ACSSiteType.IDA,
        k_forward=2e-5,
        E_a=45000.0,
        stoichiometry=1.0,
        hydrolysis_rate=1e-5,
        ph_optimum=10.5,
        ph_min=9.0, ph_max=12.0,
        temperature_default=298.15,
        temperature_min=288.15, temperature_max=313.15,
        time_default=21600.0,
        ligand_mw=133.0,
        ligand_r_h=0.4e-9,
        metal_ion="Ni2+",
        metal_loaded_fraction=1.0,
        binding_model_hint="metal_chelation",
        confidence_tier="semi_quantitative",
        calibration_source="Estimated from general epoxide-amine kinetics",
        notes="IMAC chelator; creates explicit IDA site inventory for metal charging; no metal leaching modeled",
    ),

    # ── 7. Phenyl coupling ────────────────────────────────────────────
    "phenyl_coupling": ReagentProfile(
        name="Phenyl (HIC ligand)",
        cas="62-53-3",
        reagent_identity="Phenylamine (aniline)",
        installed_ligand="Phenyl",
        functional_mode="hic_ligand",
        reaction_type="coupling",
        chemistry_class="epoxide_amine",
        target_acs=ACSSiteType.EPOXIDE,
        product_acs=None,
        k_forward=3e-5,
        E_a=48000.0,
        stoichiometry=1.0,
        hydrolysis_rate=5e-6,
        ph_optimum=9.5,
        ph_min=8.0, ph_max=11.0,
        temperature_default=298.15,
        temperature_min=288.15, temperature_max=313.15,
        time_default=14400.0,
        ligand_mw=93.0,
        ligand_r_h=0.3e-9,
        binding_model_hint="salt_promoted",
        confidence_tier="semi_quantitative",
        calibration_source="Estimated from aniline-epoxide kinetics",
        hazard_class="toxic",
        notes="HIC ligand; weak nucleophile; hydrophobic interaction depends on salt concentration",
    ),

    # ── 8. Sulfopropyl coupling ───────────────────────────────────────
    "sp_coupling": ReagentProfile(
        name="Sulfopropyl (strong cation exchange)",
        cas="1120-71-4",
        reagent_identity="1,3-Propane sultone",
        installed_ligand="Sulfopropyl",
        functional_mode="iex_ligand",
        reaction_type="coupling",
        chemistry_class="epoxide_amine",
        target_acs=ACSSiteType.EPOXIDE,
        product_acs=None,
        k_forward=4e-5,
        E_a=50000.0,
        stoichiometry=1.0,
        hydrolysis_rate=1e-5,
        ph_optimum=10.5,
        ph_min=9.0, ph_max=12.0,
        temperature_default=298.15,
        temperature_min=288.15, temperature_max=313.15,
        time_default=14400.0,
        ligand_mw=122.0,
        ligand_r_h=0.4e-9,
        charge_type="cation",
        binding_model_hint="charge_exchange",
        confidence_tier="semi_quantitative",
        calibration_source="Estimated from sultone ring-opening kinetics",
        hazard_class="toxic",
        notes="Strong cation exchanger; permanently charged sulfonate at all pH",
    ),

    # ─── Phase 2 Expansion — Protein Coupling (2) ─────────────────────

    # ── 9. Protein A coupling ─────────────────────────────────────────
    "protein_a_coupling": ReagentProfile(
        name="Protein A (IgG affinity)",
        cas="91932-65-9",
        reagent_identity="Recombinant Protein A (rSPA)",
        installed_ligand="Protein A",
        functional_mode="affinity_ligand",
        reaction_type="protein_coupling",
        chemistry_class="epoxide_amine",
        target_acs=ACSSiteType.EPOXIDE,
        product_acs=None,
        k_forward=5e-7,
        E_a=25000.0,
        stoichiometry=1.0,
        hydrolysis_rate=0.0,
        ph_optimum=9.0,
        ph_min=7.5, ph_max=10.0,
        temperature_default=277.15,
        temperature_min=273.15, temperature_max=283.15,
        time_default=57600.0,
        ligand_mw=42000.0,
        ligand_r_h=2.5e-9,
        is_macromolecule=True,
        activity_retention=0.60,
        activity_retention_uncertainty=0.15,
        max_surface_density=2e-8,
        binding_model_hint="fc_affinity",
        confidence_tier="ranking_only",
        calibration_source="Estimated; activity retention from Cytiva Protein A Sepharose literature",
        notes="Couple at 4C to preserve folding; 1 Protein A binds 2 IgG Fc; ranking_only unless calibrated",
    ),

    # ── 10. Protein G coupling ────────────────────────────────────────
    "protein_g_coupling": ReagentProfile(
        name="Protein G (IgG affinity, broad subclass)",
        cas="122441-07-8",
        reagent_identity="Recombinant Protein G (rSPG)",
        installed_ligand="Protein G",
        functional_mode="affinity_ligand",
        reaction_type="protein_coupling",
        chemistry_class="epoxide_amine",
        target_acs=ACSSiteType.EPOXIDE,
        product_acs=None,
        k_forward=5e-7,
        E_a=25000.0,
        stoichiometry=1.0,
        hydrolysis_rate=0.0,
        ph_optimum=9.0,
        ph_min=7.5, ph_max=10.0,
        temperature_default=277.15,
        temperature_min=273.15, temperature_max=283.15,
        time_default=57600.0,
        ligand_mw=22000.0,
        ligand_r_h=2.0e-9,
        is_macromolecule=True,
        activity_retention=0.65,
        activity_retention_uncertainty=0.15,
        max_surface_density=3e-8,
        binding_model_hint="fc_affinity",
        confidence_tier="ranking_only",
        calibration_source="Estimated; broader IgG subclass coverage than Protein A",
        notes="Couple at 4C; broader subclass binding; ranking_only unless calibrated",
    ),

    # ─── Phase 2 Expansion — Quenching (4) ────────────────────────────

    # ── 11. Ethanolamine quench ───────────────────────────────────────
    "ethanolamine_quench": ReagentProfile(
        name="Ethanolamine (epoxide quench)",
        cas="141-43-5",
        reagent_identity="Ethanolamine",
        installed_ligand="beta-hydroxyethylamine (blocked)",
        functional_mode="quencher",
        reaction_type="blocking",
        chemistry_class="epoxide_amine",
        target_acs=ACSSiteType.EPOXIDE,
        product_acs=None,
        k_forward=1e-3,
        E_a=30000.0,
        stoichiometry=1.0,
        hydrolysis_rate=0.0,
        ph_optimum=8.5,
        ph_min=7.0, ph_max=10.0,
        temperature_default=298.15,
        time_default=7200.0,
        confidence_tier="semi_quantitative",
        calibration_source="Standard Sepharose quenching protocol",
        notes="Standard quench for epoxide-activated media; 1M concentration typical",
    ),

    # ── 12. 2-Mercaptoethanol quench ──────────────────────────────────
    "mercaptoethanol_quench": ReagentProfile(
        name="2-Mercaptoethanol (VS quench)",
        cas="60-24-2",
        reagent_identity="2-Mercaptoethanol",
        installed_ligand="Thioether (blocked)",
        functional_mode="quencher",
        reaction_type="blocking",
        chemistry_class="vs_thiol",
        target_acs=ACSSiteType.VINYL_SULFONE,
        product_acs=None,
        k_forward=5e-3,
        E_a=25000.0,
        stoichiometry=1.0,
        hydrolysis_rate=0.0,
        ph_optimum=6.5,
        ph_min=5.0, ph_max=8.0,
        temperature_default=298.15,
        time_default=3600.0,
        confidence_tier="semi_quantitative",
        hazard_class="toxic_malodorous",
        notes="Fast thiol-VS Michael addition; handle in fume hood",
    ),

    # ── 13. Sodium borohydride quench ─────────────────────────────────
    "nabh4_quench": ReagentProfile(
        name="Sodium borohydride (aldehyde quench)",
        cas="16940-66-2",
        reagent_identity="Sodium borohydride (NaBH4)",
        installed_ligand="Alcohol -CH2OH (blocked)",
        functional_mode="quencher",
        reaction_type="blocking",
        chemistry_class="reduction",
        target_acs=ACSSiteType.ALDEHYDE,
        product_acs=None,
        k_forward=1e-1,
        E_a=15000.0,
        stoichiometry=1.0,
        hydrolysis_rate=0.0,
        ph_optimum=7.5,
        ph_min=6.0, ph_max=9.0,
        temperature_default=298.15,
        time_default=1800.0,
        confidence_tier="semi_quantitative",
        hazard_class="flammable_corrosive",
        notes="Also reduces Schiff base (imine) linkages to stable secondary amines",
    ),

    # ── 14. Acetic anhydride quench ───────────────────────────────────
    "acetic_anhydride_quench": ReagentProfile(
        name="Acetic anhydride (amine quench)",
        cas="108-24-7",
        reagent_identity="Acetic anhydride",
        installed_ligand="Acetamide (blocked)",
        functional_mode="quencher",
        reaction_type="blocking",
        chemistry_class="acetylation",
        target_acs=ACSSiteType.AMINE_PRIMARY,
        product_acs=None,
        k_forward=5e-3,
        E_a=25000.0,
        stoichiometry=1.0,
        hydrolysis_rate=0.0,
        ph_optimum=7.5,
        ph_min=6.0, ph_max=9.0,
        temperature_default=298.15,
        time_default=3600.0,
        confidence_tier="semi_quantitative",
        hazard_class="corrosive_flammable",
        notes="Caps free amines to reduce non-specific binding",
    ),

    # ═══════════════════════════════════════════════════════════════════
    # v5.7 Expansion — 6 new ligand coupling profiles (WN-2)
    # ═══════════════════════════════════════════════════════════════════

    "q_coupling": ReagentProfile(
        name="Q (strong anion exchange)",
        cas="3033-77-0",
        reagent_identity="Glycidyltrimethylammonium chloride",
        installed_ligand="Q",
        functional_mode="iex_ligand",
        reaction_type="coupling",
        chemistry_class="epoxide_amine",
        target_acs=ACSSiteType.EPOXIDE,
        product_acs=None,
        k_forward=6e-5,
        E_a=50000.0,
        stoichiometry=1.0,
        hydrolysis_rate=1e-5,
        ph_optimum=10.5,
        ph_min=9.0, ph_max=12.0,
        temperature_default=298.15,
        time_default=14400.0,
        ligand_mw=152.0,
        ligand_r_h=0.4e-9,
        charge_type="anion",
        binding_model_hint="charge_exchange",
        confidence_tier="semi_quantitative",
        calibration_source="Estimated from epoxide-amine kinetics",
        notes="Strong anion exchanger; permanent positive charge at all pH",
    ),

    "cm_coupling": ReagentProfile(
        name="CM (weak cation exchange)",
        cas="79-11-8",
        reagent_identity="Chloroacetic acid + amino spacer",
        installed_ligand="CM-like carboxymethyl",
        functional_mode="iex_ligand",
        reaction_type="coupling",
        chemistry_class="epoxide_amine",
        target_acs=ACSSiteType.EPOXIDE,
        product_acs=None,
        k_forward=3e-5,
        E_a=45000.0,
        stoichiometry=1.0,
        hydrolysis_rate=1e-5,
        ph_optimum=10.5,
        ph_min=9.0, ph_max=12.0,
        temperature_default=298.15,
        time_default=21600.0,
        ligand_mw=94.0,
        ligand_r_h=0.4e-9,
        charge_type="cation",
        binding_model_hint="charge_exchange",
        confidence_tier="semi_quantitative",
        calibration_source="Estimated; CM-like via amino-carboxyl ligand coupling",
        notes="Weak cation exchanger; charged above pH ~4 (carboxyl pKa)",
    ),

    "nta_coupling": ReagentProfile(
        name="NTA (IMAC chelator, His-tag)",
        cas="139-13-9",
        reagent_identity="Nitrilotriacetic acid",
        installed_ligand="NTA",
        functional_mode="imac_chelator",
        reaction_type="coupling",
        chemistry_class="epoxide_amine",
        target_acs=ACSSiteType.EPOXIDE,
        product_acs=ACSSiteType.NTA,
        k_forward=2e-5,
        E_a=45000.0,
        stoichiometry=1.0,
        hydrolysis_rate=1e-5,
        ph_optimum=10.5,
        ph_min=9.0, ph_max=12.0,
        temperature_default=298.15,
        time_default=21600.0,
        ligand_mw=191.0,
        ligand_r_h=0.5e-9,
        metal_ion="Ni2+",
        metal_loaded_fraction=1.0,
        binding_model_hint="metal_chelation",
        confidence_tier="semi_quantitative",
        calibration_source="Estimated from epoxide-amine kinetics",
        notes="Tetradentate IMAC chelator; creates explicit NTA site inventory for metal charging; higher specificity than IDA",
    ),

    "butyl_coupling": ReagentProfile(
        name="Butyl (HIC, mild)",
        cas="109-73-9",
        reagent_identity="n-Butylamine",
        installed_ligand="Butyl",
        functional_mode="hic_ligand",
        reaction_type="coupling",
        chemistry_class="epoxide_amine",
        target_acs=ACSSiteType.EPOXIDE,
        product_acs=None,
        k_forward=4e-5,
        E_a=48000.0,
        stoichiometry=1.0,
        hydrolysis_rate=5e-6,
        ph_optimum=9.5,
        ph_min=8.0, ph_max=11.0,
        temperature_default=298.15,
        time_default=14400.0,
        ligand_mw=73.0,
        ligand_r_h=0.3e-9,
        binding_model_hint="salt_promoted",
        confidence_tier="semi_quantitative",
        calibration_source="Estimated from alkylamine-epoxide kinetics",
        notes="Mild HIC ligand; lower hydrophobicity than Phenyl; gentler elution conditions",
    ),

    "glutathione_coupling": ReagentProfile(
        name="Glutathione (GST-tag affinity)",
        cas="70-18-8",
        reagent_identity="Glutathione reduced (GSH)",
        installed_ligand="Glutathione",
        functional_mode="gst_affinity",
        reaction_type="coupling",
        chemistry_class="epoxide_amine",
        target_acs=ACSSiteType.EPOXIDE,
        product_acs=None,
        k_forward=3e-5,
        E_a=45000.0,
        stoichiometry=1.0,
        hydrolysis_rate=1e-5,
        ph_optimum=9.5,
        ph_min=8.0, ph_max=11.0,
        temperature_default=298.15,
        time_default=14400.0,
        ligand_mw=307.0,
        ligand_r_h=0.5e-9,
        activity_retention=0.80,
        activity_retention_uncertainty=0.15,
        spacer_key="aha_spacer",
        spacer_activity_multiplier=1.15,
        binding_model_hint="gst_glutathione",
        confidence_tier="semi_quantitative",
        calibration_source="Estimated; orientation-sensitive coupling",
        notes="Orientation-sensitive; activity_retention=0.80 reflects random coupling penalty",
    ),

    "heparin_coupling": ReagentProfile(
        name="Heparin (affinity + IEX)",
        cas="9005-49-6",
        reagent_identity="Heparin sodium (porcine intestinal)",
        installed_ligand="Heparin",
        functional_mode="heparin_affinity",
        reaction_type="coupling",
        chemistry_class="epoxide_amine",
        target_acs=ACSSiteType.EPOXIDE,
        product_acs=None,
        k_forward=1e-5,
        E_a=40000.0,
        stoichiometry=1.0,
        hydrolysis_rate=5e-6,
        ph_optimum=9.5,
        ph_min=8.0, ph_max=11.0,
        temperature_default=298.15,
        time_default=28800.0,
        ligand_mw=14000.0,
        ligand_r_h=3.0e-9,
        is_macromolecule=True,
        spacer_key="dadpa_spacer",
        spacer_activity_multiplier=1.22,
        binding_model_hint="mixed_mode",
        confidence_tier="ranking_only",
        calibration_source="Estimated; macromolecular polysaccharide",
        notes="Mixed affinity + cation exchange; q_max highly target-dependent; macromolecule",
    ),

    # ═══════════════════════════════════════════════════════════════════
    # v5.7 Expansion — 2 new protein coupling profiles (WN-3)
    # ═══════════════════════════════════════════════════════════════════

    "protein_ag_coupling": ReagentProfile(
        name="Protein A/G Fusion (broadest IgG)",
        cas="N/A",
        reagent_identity="Recombinant Protein A/G",
        installed_ligand="Protein A/G",
        functional_mode="affinity_ligand",
        reaction_type="protein_coupling",
        chemistry_class="epoxide_amine",
        target_acs=ACSSiteType.EPOXIDE,
        product_acs=None,
        k_forward=5e-7,
        E_a=25000.0,
        stoichiometry=1.0,
        ph_optimum=9.0,
        ph_min=7.5, ph_max=10.0,
        temperature_default=277.15,
        temperature_min=273.15, temperature_max=283.15,
        time_default=57600.0,
        ligand_mw=51000.0,
        ligand_r_h=2.8e-9,
        is_macromolecule=True,
        activity_retention=0.55,
        activity_retention_uncertainty=0.15,
        max_surface_density=2e-8,
        spacer_key="dadpa_spacer",
        spacer_activity_multiplier=1.22,
        binding_model_hint="fc_affinity",
        confidence_tier="ranking_only",
        calibration_source="Estimated; broadest IgG coverage via A+G domains",
        notes="Fusion of Protein A + G binding domains; ranking_only unless calibrated",
    ),

    "streptavidin_coupling": ReagentProfile(
        name="Streptavidin (biotin-tag)",
        cas="9013-20-1",
        reagent_identity="Streptavidin (S. avidinii)",
        installed_ligand="Streptavidin",
        functional_mode="biotin_affinity",
        reaction_type="protein_coupling",
        chemistry_class="epoxide_amine",
        target_acs=ACSSiteType.EPOXIDE,
        product_acs=None,
        k_forward=4e-7,
        E_a=25000.0,
        stoichiometry=1.0,
        ph_optimum=9.0,
        ph_min=7.5, ph_max=10.0,
        temperature_default=277.15,
        temperature_min=273.15, temperature_max=283.15,
        time_default=57600.0,
        ligand_mw=53000.0,
        ligand_r_h=2.8e-9,
        is_macromolecule=True,
        activity_retention=0.70,
        activity_retention_uncertainty=0.10,
        max_surface_density=3e-8,
        spacer_key="dadpa_spacer",
        spacer_activity_multiplier=1.22,
        binding_model_hint="near_irreversible",
        confidence_tier="ranking_only",
        calibration_source="Estimated; Kd ~10^-15 M streptavidin-biotin",
        notes="Near-irreversible binding; effective stoichiometry capped at 2.5 (not theoretical 4)",
    ),

    # ═══════════════════════════════════════════════════════════════════
    # v5.7 Expansion — 3 spacer arm metadata profiles (WN-3)
    # These are NOT executable as modification steps. They serve as
    # lookup records for spacer_key on coupling profiles.
    # ═══════════════════════════════════════════════════════════════════

    "dadpa_spacer": ReagentProfile(
        name="DADPA spacer (13 A, EAH-standard)",
        cas="56-18-8",
        reagent_identity="Diaminodipropylamine",
        installed_ligand="DADPA spacer arm",
        functional_mode="spacer",
        reaction_type="spacer",
        chemistry_class="epoxide_amine",
        target_acs=ACSSiteType.EPOXIDE,
        product_acs=None,
        k_forward=0.0,
        E_a=0.0,
        stoichiometry=1.0,
        spacer_length_angstrom=13.0,
        spacer_activity_multiplier=1.22,
        confidence_tier="semi_quantitative",
        calibration_source="EAH-Sepharose standard; multiplier from Protein A literature",
        hazard_class="irritant",
        notes="9-atom amine spacer; industry standard for protein ligand immobilization",
    ),

    "aha_spacer": ReagentProfile(
        name="AHA spacer (10 A, NHS-standard)",
        cas="60-32-2",
        reagent_identity="6-Aminohexanoic acid",
        installed_ligand="AHA spacer arm",
        functional_mode="spacer",
        reaction_type="spacer",
        chemistry_class="epoxide_amine",
        target_acs=ACSSiteType.EPOXIDE,
        product_acs=None,
        k_forward=0.0,
        E_a=0.0,
        stoichiometry=1.0,
        spacer_length_angstrom=10.0,
        spacer_activity_multiplier=1.15,
        confidence_tier="semi_quantitative",
        calibration_source="NHS-Sepharose HP standard; multiplier from affinity literature",
        hazard_class="low_hazard",
        notes="7-atom acid spacer; provides -COOH distal group (EDC/NHS path not modeled in Phase 1)",
    ),

    "dah_spacer": ReagentProfile(
        name="DAH spacer (9 A, AH-standard)",
        cas="124-09-4",
        reagent_identity="1,6-Diaminohexane",
        installed_ligand="DAH spacer arm",
        functional_mode="spacer",
        reaction_type="spacer",
        chemistry_class="epoxide_amine",
        target_acs=ACSSiteType.EPOXIDE,
        product_acs=None,
        k_forward=0.0,
        E_a=0.0,
        stoichiometry=1.0,
        spacer_length_angstrom=9.0,
        spacer_activity_multiplier=1.08,
        confidence_tier="semi_quantitative",
        calibration_source="AH-Sepharose 4B standard; shorter than DADPA",
        hazard_class="irritant",
        notes="6-atom diamine spacer; simpler than DADPA but more hydrophobic",
    ),

    # ═══════════════════════════════════════════════════════════════════
    # v5.8 Phase 1 — 6 deferred profiles (WN-0)
    # ═══════════════════════════════════════════════════════════════════

    "protein_l_coupling": ReagentProfile(
        name="Protein L (kappa light chain)",
        cas="N/A",
        reagent_identity="Recombinant Protein L (Peptostreptococcus magnus)",
        installed_ligand="Protein L",
        functional_mode="affinity_ligand",
        reaction_type="protein_coupling",
        chemistry_class="epoxide_amine",
        target_acs=ACSSiteType.EPOXIDE,
        product_acs=None,
        k_forward=5e-7,
        E_a=25000.0,
        stoichiometry=1.0,
        ph_optimum=9.0,
        ph_min=7.5, ph_max=10.0,
        temperature_default=277.15,
        temperature_min=273.15, temperature_max=283.15,
        time_default=57600.0,
        ligand_mw=36000.0,
        ligand_r_h=2.3e-9,
        is_macromolecule=True,
        activity_retention=0.55,
        activity_retention_uncertainty=0.15,
        max_surface_density=3e-8,
        spacer_key="dadpa_spacer",
        spacer_activity_multiplier=1.20,
        binding_model_hint="kappa_light_chain_affinity",
        profile_role="final_ligand",
        m3_support_level="requires_user_calibration",
        confidence_tier="ranking_only",
        calibration_source="Estimated; Fab/scFv purification via kappa light chain",
        notes="Binds kappa light chains; useful for Fab, scFv, single-domain antibodies",
    ),

    "con_a_coupling": ReagentProfile(
        name="Concanavalin A (lectin, mannose/glucose)",
        cas="11028-71-0",
        reagent_identity="Concanavalin A (Canavalia ensiformis)",
        installed_ligand="Con A",
        functional_mode="affinity_ligand",
        reaction_type="protein_coupling",
        chemistry_class="epoxide_amine",
        target_acs=ACSSiteType.EPOXIDE,
        product_acs=None,
        k_forward=2e-7,
        E_a=25000.0,
        stoichiometry=1.0,
        ph_optimum=8.5,
        ph_min=7.0, ph_max=9.5,
        temperature_default=277.15,
        temperature_min=273.15, temperature_max=283.15,
        time_default=57600.0,
        ligand_mw=104000.0,
        ligand_r_h=4.0e-9,
        is_macromolecule=True,
        activity_retention=0.40,
        activity_retention_uncertainty=0.20,
        max_surface_density=1e-8,
        spacer_key="peg600_spacer",
        spacer_activity_multiplier=1.35,
        binding_model_hint="lectin_mannose_glucose",
        profile_role="final_ligand",
        m3_support_level="requires_user_calibration",
        confidence_tier="ranking_only",
        calibration_source="Estimated; lectin affinity literature",
        notes="Tetramer at pH>7; requires Ca2+/Mn2+ cofactors; sugar-competition elution",
    ),

    "octyl_coupling": ReagentProfile(
        name="Octyl (HIC, strong)",
        cas="111-86-4",
        reagent_identity="n-Octylamine",
        installed_ligand="Octyl",
        functional_mode="hic_ligand",
        reaction_type="coupling",
        chemistry_class="epoxide_amine",
        target_acs=ACSSiteType.EPOXIDE,
        product_acs=None,
        k_forward=4e-5,
        E_a=48000.0,
        stoichiometry=1.0,
        hydrolysis_rate=5e-6,
        ph_optimum=9.5,
        ph_min=8.0, ph_max=11.0,
        temperature_default=298.15,
        time_default=14400.0,
        ligand_mw=129.0,
        ligand_r_h=0.4e-9,
        binding_model_hint="salt_promoted",
        profile_role="final_ligand",
        m3_support_level="not_mapped",
        confidence_tier="semi_quantitative",
        calibration_source="Estimated from alkylamine-epoxide kinetics",
        notes="Very hydrophobic HIC; risk of irreversible binding at high density",
    ),

    "wga_coupling": ReagentProfile(
        name="WGA (wheat germ agglutinin, GlcNAc/sialic)",
        cas="9001-31-2",
        reagent_identity="Wheat Germ Agglutinin",
        installed_ligand="WGA",
        functional_mode="affinity_ligand",
        reaction_type="protein_coupling",
        chemistry_class="epoxide_amine",
        target_acs=ACSSiteType.EPOXIDE,
        product_acs=None,
        k_forward=4e-7,
        E_a=25000.0,
        stoichiometry=1.0,
        ph_optimum=8.5,
        ph_min=7.0, ph_max=9.5,
        temperature_default=277.15,
        temperature_min=273.15, temperature_max=283.15,
        time_default=57600.0,
        ligand_mw=36000.0,
        ligand_r_h=2.3e-9,
        is_macromolecule=True,
        activity_retention=0.50,
        activity_retention_uncertainty=0.15,
        max_surface_density=3e-8,
        spacer_key="dadpa_spacer",
        spacer_activity_multiplier=1.20,
        binding_model_hint="lectin_glcnac_sialic",
        profile_role="final_ligand",
        m3_support_level="requires_user_calibration",
        confidence_tier="ranking_only",
        calibration_source="Estimated; lectin affinity literature",
        notes="Dimer 2x18kDa; binds GlcNAc and sialic acid; sugar-competition elution",
    ),

    "peg600_spacer": ReagentProfile(
        name="PEG-diamine Mn 600 spacer (35 A)",
        cas="929-59-9",
        reagent_identity="Bis(aminopropyl) PEG Mn 600",
        installed_ligand="PEG-diamine spacer arm",
        functional_mode="spacer",
        reaction_type="spacer",
        chemistry_class="epoxide_amine",
        target_acs=ACSSiteType.EPOXIDE,
        product_acs=None,
        k_forward=0.0,
        E_a=0.0,
        stoichiometry=1.0,
        spacer_length_angstrom=35.0,
        spacer_activity_multiplier=1.35,
        ligand_mw=600.0,
        profile_role="spacer_metadata",
        m3_support_level="not_mapped",
        confidence_tier="semi_quantitative",
        calibration_source="Estimated; PEG-diamine literature",
        notes="Long hydrophilic PEG spacer; critical for large proteins (>50 kDa)",
    ),

    "bdge_activation": ReagentProfile(
        name="BDGE activation (18 A spacer epoxide)",
        cas="2425-79-8",
        reagent_identity="1,4-Butanediol diglycidyl ether",
        installed_ligand="Epoxide (long-arm)",
        functional_mode="activator",
        reaction_type="activation",
        chemistry_class="epoxide_amine",
        target_acs=ACSSiteType.HYDROXYL,
        product_acs=ACSSiteType.EPOXIDE,
        k_forward=1.2e-5,
        E_a=60000.0,
        stoichiometry=1.0,
        hydrolysis_rate=5e-5,
        ph_optimum=11.5,
        ph_min=10.0, ph_max=13.0,
        temperature_default=298.15,
        time_default=14400.0,
        spacer_length_angstrom=18.0,
        profile_role="activated",
        m3_support_level="not_mapped",
        confidence_tier="semi_quantitative",
        calibration_source="Estimated; bis-epoxide activation literature",
        hazard_class="irritant",
        notes="Bis-epoxide; creates long-arm epoxide (18A vs ECH ~5A)",
    ),

    # ═══════════════════════════════════════════════════════════════════
    # v5.8 Phase 2 — SPACER_ARM executable profiles (WN-5)
    # ═══════════════════════════════════════════════════════════════════

    # ── Diamine spacer-arm profiles (EPOXIDE → AMINE_DISTAL) ──

    "eda_spacer_arm": ReagentProfile(
        name="EDA spacer arm (3 A, shortest)",
        cas="107-15-3",
        reagent_identity="Ethylenediamine",
        installed_ligand="EDA spacer (distal -NH2)",
        functional_mode="spacer",
        reaction_type="spacer_arm",
        chemistry_class="epoxide_amine_spacer",
        target_acs=ACSSiteType.EPOXIDE,
        product_acs=ACSSiteType.AMINE_DISTAL,
        k_forward=8e-5,
        E_a=45000.0,
        stoichiometry=1.0,
        ph_optimum=10.5,
        ph_min=9.0, ph_max=12.0,
        temperature_default=298.15,
        time_default=14400.0,
        spacer_length_angstrom=3.0,
        distal_group_yield=0.60,
        profile_role="spacer_intermediate",
        m3_support_level="not_mapped",
        confidence_tier="semi_quantitative",
        calibration_source="Estimated; high bridging risk for short diamine",
        notes="Shortest diamine; 60% distal yield (40% bridging)",
    ),

    "dadpa_spacer_arm": ReagentProfile(
        name="DADPA spacer arm (13 A)",
        cas="56-18-8",
        reagent_identity="Diaminodipropylamine",
        installed_ligand="DADPA spacer (distal -NH2)",
        functional_mode="spacer",
        reaction_type="spacer_arm",
        chemistry_class="epoxide_amine_spacer",
        target_acs=ACSSiteType.EPOXIDE,
        product_acs=ACSSiteType.AMINE_DISTAL,
        k_forward=5e-5,
        E_a=45000.0,
        stoichiometry=1.0,
        ph_optimum=10.5,
        ph_min=9.0, ph_max=12.0,
        temperature_default=298.15,
        time_default=14400.0,
        spacer_length_angstrom=13.0,
        distal_group_yield=0.80,
        profile_role="spacer_intermediate",
        m3_support_level="not_mapped",
        confidence_tier="semi_quantitative",
        calibration_source="EAH-Sepharose standard; internal amine reduces bridging",
        notes="Industry standard protein spacer; 80% distal yield",
    ),

    "dah_spacer_arm": ReagentProfile(
        name="DAH spacer arm (9 A)",
        cas="124-09-4",
        reagent_identity="1,6-Diaminohexane",
        installed_ligand="DAH spacer (distal -NH2)",
        functional_mode="spacer",
        reaction_type="spacer_arm",
        chemistry_class="epoxide_amine_spacer",
        target_acs=ACSSiteType.EPOXIDE,
        product_acs=ACSSiteType.AMINE_DISTAL,
        k_forward=6e-5,
        E_a=45000.0,
        stoichiometry=1.0,
        ph_optimum=10.5,
        ph_min=9.0, ph_max=12.0,
        temperature_default=298.15,
        time_default=14400.0,
        spacer_length_angstrom=9.0,
        distal_group_yield=0.70,
        profile_role="spacer_intermediate",
        m3_support_level="not_mapped",
        confidence_tier="semi_quantitative",
        calibration_source="AH-Sepharose standard",
        hazard_class="irritant",
        notes="Simple diamine spacer; 70% distal yield (more hydrophobic than DADPA)",
    ),

    "peg600_spacer_arm": ReagentProfile(
        name="PEG-diamine Mn 600 spacer arm (35 A)",
        cas="929-59-9",
        reagent_identity="Bis(aminopropyl) PEG Mn 600",
        installed_ligand="PEG spacer (distal -NH2)",
        functional_mode="spacer",
        reaction_type="spacer_arm",
        chemistry_class="epoxide_amine_spacer",
        target_acs=ACSSiteType.EPOXIDE,
        product_acs=ACSSiteType.AMINE_DISTAL,
        k_forward=2e-5,
        E_a=45000.0,
        stoichiometry=1.0,
        ph_optimum=10.5,
        ph_min=9.0, ph_max=12.0,
        temperature_default=298.15,
        time_default=21600.0,
        spacer_length_angstrom=35.0,
        distal_group_yield=0.90,
        ligand_mw=600.0,
        profile_role="spacer_intermediate",
        m3_support_level="not_mapped",
        confidence_tier="semi_quantitative",
        calibration_source="PEG-diamine literature; PEG flexibility favors monoattachment",
        notes="Long hydrophilic PEG spacer; 90% distal yield; critical for large proteins",
    ),

    # ── SM(PEG)n heterobifunctional crosslinkers (AMINE_DISTAL → MALEIMIDE) ──

    "sm_peg2": ReagentProfile(
        name="SM(PEG)2 (NHS-PEG2-Maleimide, 18 A)",
        cas="1334179-85-1",
        reagent_identity="Succinimidyl-[(N-maleimidopropionamido)-diethyleneglycol] ester",
        installed_ligand="Maleimide (PEG2 arm)",
        functional_mode="heterobifunctional_crosslinker",
        reaction_type="heterobifunctional",
        chemistry_class="nhs_amine",
        target_acs=ACSSiteType.AMINE_DISTAL,
        product_acs=ACSSiteType.MALEIMIDE,
        k_forward=1e-3,
        E_a=35000.0,
        stoichiometry=1.0,
        hydrolysis_rate=1e-3,
        ph_optimum=7.4,
        ph_min=7.0, ph_max=7.5,
        temperature_default=298.15,
        time_default=1800.0,
        spacer_length_angstrom=18.0,
        ligand_mw=425.0,
        distal_group_yield=0.85,
        maleimide_decay_rate=1e-5,
        buffer_incompatibilities="Tris,glycine,primary_amine_buffers",
        profile_role="heterobifunctional_intermediate",
        m3_support_level="not_mapped",
        confidence_tier="semi_quantitative",
        calibration_source="Thermo Fisher SM(PEG)n protocols; NHS hydrolysis from Hermanson",
        notes="NHS half-life ~10 min at pH 7.4; react quickly after dissolving",
    ),

    "sm_peg4": ReagentProfile(
        name="SM(PEG)4 (NHS-PEG4-Maleimide, 32 A)",
        cas="1229578-42-6",
        reagent_identity="Succinimidyl-[(N-maleimidopropionamido)-tetraethyleneglycol] ester",
        installed_ligand="Maleimide (PEG4 arm)",
        functional_mode="heterobifunctional_crosslinker",
        reaction_type="heterobifunctional",
        chemistry_class="nhs_amine",
        target_acs=ACSSiteType.AMINE_DISTAL,
        product_acs=ACSSiteType.MALEIMIDE,
        k_forward=1e-3,
        E_a=35000.0,
        stoichiometry=1.0,
        hydrolysis_rate=1e-3,
        ph_optimum=7.4,
        ph_min=7.0, ph_max=7.5,
        temperature_default=298.15,
        time_default=1800.0,
        spacer_length_angstrom=32.0,
        ligand_mw=513.0,
        distal_group_yield=0.85,
        maleimide_decay_rate=1e-5,
        buffer_incompatibilities="Tris,glycine,primary_amine_buffers",
        profile_role="heterobifunctional_intermediate",
        m3_support_level="not_mapped",
        confidence_tier="semi_quantitative",
        calibration_source="Thermo Fisher SM(PEG)n protocols",
        notes="Most commonly used SM(PEG)n variant; good balance of length and solubility",
    ),

    "sm_peg12": ReagentProfile(
        name="SM(PEG)12 (NHS-PEG12-Maleimide, 60 A)",
        cas="1334179-86-2",
        reagent_identity="Succinimidyl-[(N-maleimidopropionamido)-dodecaethyleneglycol] ester",
        installed_ligand="Maleimide (PEG12 arm)",
        functional_mode="heterobifunctional_crosslinker",
        reaction_type="heterobifunctional",
        chemistry_class="nhs_amine",
        target_acs=ACSSiteType.AMINE_DISTAL,
        product_acs=ACSSiteType.MALEIMIDE,
        k_forward=1e-3,
        E_a=35000.0,
        stoichiometry=1.0,
        hydrolysis_rate=1e-3,
        ph_optimum=7.4,
        ph_min=7.0, ph_max=7.5,
        temperature_default=298.15,
        time_default=1800.0,
        spacer_length_angstrom=60.0,
        ligand_mw=865.0,
        distal_group_yield=0.85,
        maleimide_decay_rate=1e-5,
        buffer_incompatibilities="Tris,glycine,primary_amine_buffers",
        profile_role="heterobifunctional_intermediate",
        m3_support_level="not_mapped",
        confidence_tier="semi_quantitative",
        calibration_source="Thermo Fisher SM(PEG)n protocols",
        notes="Long PEG arm for maximum protein conformational freedom",
    ),

    "sm_peg24": ReagentProfile(
        name="SM(PEG)24 (NHS-PEG24-Maleimide, 95 A)",
        cas="1334179-87-3",
        reagent_identity="Succinimidyl-[(N-maleimidopropionamido)-tetracosaethyleneglycol] ester",
        installed_ligand="Maleimide (PEG24 arm)",
        functional_mode="heterobifunctional_crosslinker",
        reaction_type="heterobifunctional",
        chemistry_class="nhs_amine",
        target_acs=ACSSiteType.AMINE_DISTAL,
        product_acs=ACSSiteType.MALEIMIDE,
        k_forward=1e-3,
        E_a=35000.0,
        stoichiometry=1.0,
        hydrolysis_rate=1e-3,
        ph_optimum=7.4,
        ph_min=7.0, ph_max=7.5,
        temperature_default=298.15,
        time_default=1800.0,
        spacer_length_angstrom=95.0,
        ligand_mw=1393.0,
        distal_group_yield=0.85,
        maleimide_decay_rate=1e-5,
        buffer_incompatibilities="Tris,glycine,primary_amine_buffers",
        profile_role="heterobifunctional_intermediate",
        m3_support_level="not_mapped",
        confidence_tier="semi_quantitative",
        calibration_source="Thermo Fisher SM(PEG)n protocols",
        notes="Longest SM(PEG)n variant; ~95 A; may introduce excess flexibility",
    ),

    # ── Protein-Cys coupling profiles (MALEIMIDE → thioether) ──

    "protein_a_cys_coupling": ReagentProfile(
        name="Protein A-Cys (oriented, maleimide-thiol)",
        cas="91932-65-9",
        reagent_identity="Recombinant Protein A with engineered C-terminal Cys",
        installed_ligand="Protein A (oriented)",
        functional_mode="affinity_ligand",
        reaction_type="protein_coupling",
        chemistry_class="maleimide_thiol",
        target_acs=ACSSiteType.MALEIMIDE,
        product_acs=None,
        k_forward=5e-2,
        E_a=20000.0,
        stoichiometry=1.0,
        ph_optimum=7.0,
        ph_min=6.5, ph_max=7.5,
        temperature_default=298.15,
        time_default=7200.0,
        ligand_mw=42000.0,
        ligand_r_h=2.5e-9,
        is_macromolecule=True,
        activity_retention=0.80,
        activity_retention_uncertainty=0.10,
        max_surface_density=2e-8,
        requires_reduced_thiol=True,
        thiol_accessibility_fraction=0.90,
        binding_model_hint="fc_affinity",
        buffer_incompatibilities="DTT,beta-mercaptoethanol,TCEP,free_thiols",
        profile_role="final_ligand",
        m3_support_level="mapped_estimated",
        confidence_tier="ranking_only",
        calibration_source="Site-specific conjugation literature; improved activity over random",
        notes="Oriented immobilization via C-terminal Cys; ~80% activity (vs 60% random)",
    ),

    "protein_g_cys_coupling": ReagentProfile(
        name="Protein G-Cys (oriented, maleimide-thiol)",
        cas="122441-07-8",
        reagent_identity="Recombinant Protein G with engineered C-terminal Cys",
        installed_ligand="Protein G (oriented)",
        functional_mode="affinity_ligand",
        reaction_type="protein_coupling",
        chemistry_class="maleimide_thiol",
        target_acs=ACSSiteType.MALEIMIDE,
        product_acs=None,
        k_forward=5e-2,
        E_a=20000.0,
        stoichiometry=1.0,
        ph_optimum=7.0,
        ph_min=6.5, ph_max=7.5,
        temperature_default=298.15,
        time_default=7200.0,
        ligand_mw=22000.0,
        ligand_r_h=2.0e-9,
        is_macromolecule=True,
        activity_retention=0.85,
        activity_retention_uncertainty=0.10,
        max_surface_density=3e-8,
        requires_reduced_thiol=True,
        thiol_accessibility_fraction=0.90,
        binding_model_hint="fc_affinity",
        buffer_incompatibilities="DTT,beta-mercaptoethanol,TCEP,free_thiols",
        profile_role="final_ligand",
        m3_support_level="mapped_estimated",
        confidence_tier="ranking_only",
        calibration_source="Site-specific conjugation literature",
        notes="Oriented Protein G via Cys; broader subclass than Protein A",
    ),

    "generic_cys_protein_coupling": ReagentProfile(
        name="Generic Cys-protein (oriented, maleimide-thiol)",
        cas="N/A",
        reagent_identity="User-supplied Cys-tagged protein",
        installed_ligand="Cys-protein (oriented)",
        functional_mode="affinity_ligand",
        reaction_type="protein_coupling",
        chemistry_class="maleimide_thiol",
        target_acs=ACSSiteType.MALEIMIDE,
        product_acs=None,
        k_forward=5e-2,
        E_a=20000.0,
        stoichiometry=1.0,
        ph_optimum=7.0,
        ph_min=6.5, ph_max=7.5,
        temperature_default=298.15,
        time_default=7200.0,
        ligand_mw=50000.0,
        ligand_r_h=2.5e-9,
        is_macromolecule=True,
        activity_retention=0.70,
        activity_retention_uncertainty=0.15,
        max_surface_density=2e-8,
        requires_reduced_thiol=True,
        thiol_accessibility_fraction=0.80,
        binding_model_hint="fc_affinity",
        buffer_incompatibilities="DTT,beta-mercaptoethanol,TCEP,free_thiols",
        profile_role="final_ligand",
        m3_support_level="requires_user_calibration",
        confidence_tier="ranking_only",
        calibration_source="Generic; user must provide target-specific parameters",
        notes="Generic maleimide-thiol coupling; user must specify protein MW and activity",
    ),

    # ═══════════════════════════════════════════════════════════════════
    # v5.9.1 — IMAC Metal Charging (5 profiles)
    # ═══════════════════════════════════════════════════════════════════

    "nickel_charging": ReagentProfile(
        name="Nickel(II) charging (Ni-NTA/IDA)",
        cas="7786-81-4", reagent_identity="Nickel(II) sulfate",
        installed_ligand="Ni2+-loaded chelator",
        functional_mode="metal_charging", reaction_type="metal_charging",
        chemistry_class="metal_chelation",
        target_acs=ACSSiteType.EPOXIDE, product_acs=None,
        k_forward=0.0, E_a=0.0, stoichiometry=1.0,
        metal_ion="Ni2+", metal_association_constant=3e11,
        ph_optimum=7.0, ph_min=5.0, ph_max=8.0,
        temperature_default=298.15, time_default=1800.0,
        profile_role="native", m3_support_level="mapped_estimated",
        confidence_tier="semi_quantitative",
        calibration_source="log K(NTA-Ni)=11.5; Martell & Smith Critical Stability Constants",
        notes="Standard Ni2+ charging for His-tag IMAC; 50 mM NiSO4 typical",
    ),
    "cobalt_charging": ReagentProfile(
        name="Cobalt(II) charging (Co-NTA/IDA)",
        cas="10026-24-1", reagent_identity="Cobalt(II) chloride",
        installed_ligand="Co2+-loaded chelator",
        functional_mode="metal_charging", reaction_type="metal_charging",
        chemistry_class="metal_chelation",
        target_acs=ACSSiteType.EPOXIDE, product_acs=None,
        k_forward=0.0, E_a=0.0, stoichiometry=1.0,
        metal_ion="Co2+", metal_association_constant=1e10,
        ph_optimum=7.0, ph_min=5.0, ph_max=8.0,
        temperature_default=298.15, time_default=1800.0,
        profile_role="native", m3_support_level="mapped_estimated",
        confidence_tier="semi_quantitative",
        calibration_source="Estimated; Co2+ has higher specificity than Ni2+",
        notes="Higher specificity, lower capacity than Ni2+",
    ),
    "copper_charging": ReagentProfile(
        name="Copper(II) charging (Cu-IDA)",
        cas="7758-99-8", reagent_identity="Copper(II) sulfate",
        installed_ligand="Cu2+-loaded chelator",
        functional_mode="metal_charging", reaction_type="metal_charging",
        chemistry_class="metal_chelation",
        target_acs=ACSSiteType.EPOXIDE, product_acs=None,
        k_forward=0.0, E_a=0.0, stoichiometry=1.0,
        metal_ion="Cu2+", metal_association_constant=1e13,
        ph_optimum=7.0, ph_min=4.0, ph_max=8.0,
        temperature_default=298.15, time_default=1800.0,
        profile_role="native", m3_support_level="mapped_estimated",
        confidence_tier="semi_quantitative",
        calibration_source="log K(IDA-Cu)=10.6; strongest divalent binding",
        notes="Highest affinity but lowest specificity; more non-specific binding",
    ),
    "zinc_charging": ReagentProfile(
        name="Zinc(II) charging (Zn-NTA/IDA)",
        cas="7446-20-0", reagent_identity="Zinc(II) sulfate",
        installed_ligand="Zn2+-loaded chelator",
        functional_mode="metal_charging", reaction_type="metal_charging",
        chemistry_class="metal_chelation",
        target_acs=ACSSiteType.EPOXIDE, product_acs=None,
        k_forward=0.0, E_a=0.0, stoichiometry=1.0,
        metal_ion="Zn2+", metal_association_constant=1e10,
        ph_optimum=7.0, ph_min=5.0, ph_max=8.0,
        temperature_default=298.15, time_default=1800.0,
        profile_role="native", m3_support_level="mapped_estimated",
        confidence_tier="semi_quantitative",
        calibration_source="Estimated; Zn2+ used for some phosphopeptide IMAC",
    ),
    "edta_stripping": ReagentProfile(
        name="EDTA metal stripping",
        cas="60-00-4", reagent_identity="EDTA disodium salt",
        installed_ligand="Metal-free chelator",
        functional_mode="metal_charging", reaction_type="metal_stripping",
        chemistry_class="metal_chelation",
        target_acs=ACSSiteType.EPOXIDE, product_acs=None,
        k_forward=0.0, E_a=0.0, stoichiometry=1.0,
        ph_optimum=7.5, ph_min=6.0, ph_max=9.0,
        temperature_default=298.15, time_default=1800.0,
        profile_role="native", m3_support_level="not_mapped",
        confidence_tier="semi_quantitative",
        calibration_source="Standard EDTA stripping; 50 mM strips >99% Ni/Co/Cu",
        notes="Strips loaded metal for regeneration or metal switching",
    ),

    # ═══════════════════════════════════════════════════════════════════
    # v5.9.2 — Protein Pretreatment (2 profiles)
    # ═══════════════════════════════════════════════════════════════════

    "tcep_reduction": ReagentProfile(
        name="TCEP disulfide reduction",
        cas="51805-45-9", reagent_identity="TCEP-HCl",
        installed_ligand="Reduced protein (free -SH)",
        functional_mode="protein_pretreatment", reaction_type="protein_pretreatment",
        chemistry_class="reduction",
        target_acs=ACSSiteType.MALEIMIDE, product_acs=None,
        k_forward=0.01, E_a=20000.0, stoichiometry=1.0,
        ph_optimum=7.0, ph_min=6.0, ph_max=8.0,
        temperature_default=298.15, time_default=1800.0,
        reduction_efficiency=0.95,
        activity_retention=0.95,
        profile_role="native", m3_support_level="not_mapped",
        confidence_tier="semi_quantitative",
        calibration_source="Hermanson Bioconjugate Techniques; TCEP is maleimide-compatible",
        notes="Preferred over DTT; does not interfere with maleimide coupling",
    ),
    "dtt_reduction": ReagentProfile(
        name="DTT disulfide reduction",
        cas="3483-12-3", reagent_identity="Dithiothreitol",
        installed_ligand="Reduced protein (free -SH)",
        functional_mode="protein_pretreatment", reaction_type="protein_pretreatment",
        chemistry_class="reduction",
        target_acs=ACSSiteType.MALEIMIDE, product_acs=None,
        k_forward=0.005, E_a=20000.0, stoichiometry=1.0,
        ph_optimum=7.5, ph_min=6.5, ph_max=8.5,
        temperature_default=298.15, time_default=1800.0,
        reduction_efficiency=0.90,
        activity_retention=0.90,
        buffer_incompatibilities="maleimide,free_thiols_in_coupling_buffer",
        profile_role="native", m3_support_level="not_mapped",
        confidence_tier="semi_quantitative",
        calibration_source="Standard DTT reduction; must remove excess before maleimide",
        hazard_class="irritant",
        notes="Must remove DTT before maleimide coupling (desalt or dialysis)",
    ),

    # ═══════════════════════════════════════════════════════════════════
    # v5.9.3 — EDC/NHS Chemistry (2 profiles)
    # ═══════════════════════════════════════════════════════════════════

    "aha_carboxyl_spacer_arm": ReagentProfile(
        name="AHA spacer arm (EPOXIDE -> CARBOXYL_DISTAL)",
        cas="60-32-2",
        reagent_identity="6-Aminohexanoic acid",
        installed_ligand="AHA spacer (distal -COOH)",
        functional_mode="spacer",
        reaction_type="spacer_arm",
        chemistry_class="epoxide_amine_spacer",
        target_acs=ACSSiteType.EPOXIDE,
        product_acs=ACSSiteType.CARBOXYL_DISTAL,
        k_forward=3e-5,
        E_a=45000.0,
        stoichiometry=1.0,
        ph_optimum=10.5,
        ph_min=9.0, ph_max=12.0,
        temperature_default=298.15,
        time_default=14400.0,
        spacer_length_angstrom=10.0,
        distal_group_yield=0.85,
        profile_role="spacer_intermediate",
        m3_support_level="not_mapped",
        confidence_tier="semi_quantitative",
        calibration_source="NHS-Sepharose HP standard; AHA provides -COOH distal",
        notes="Creates carboxyl terminus for EDC/NHS activation pathway",
    ),
    "edc_nhs_activation": ReagentProfile(
        name="EDC/NHS carboxyl activation",
        cas="25952-53-8",
        reagent_identity="EDC (1-Ethyl-3-(3-dimethylaminopropyl)carbodiimide) + NHS",
        installed_ligand="NHS ester (amine-reactive)",
        functional_mode="activator",
        reaction_type="activation",
        chemistry_class="edc_nhs",
        target_acs=ACSSiteType.CARBOXYL_DISTAL,
        product_acs=ACSSiteType.NHS_ESTER,
        k_forward=0.1,
        E_a=30000.0,
        stoichiometry=1.0,
        hydrolysis_rate=1e-4,
        ph_optimum=5.5,
        ph_min=4.5, ph_max=6.5,
        temperature_default=298.15,
        time_default=900.0,
        buffer_incompatibilities="Tris,glycine,primary_amine_buffers",
        profile_role="activated",
        m3_support_level="not_mapped",
        confidence_tier="semi_quantitative",
        calibration_source=(
            "Node 31 mechanistic two-step ODE; Hermanson 2013, Wang 2011, "
            "Cline & Hanna 1988 literature rate constants. Promotes to "
            "quantitative tier via CalibrationStore posteriors (Node 30) "
            "after Study A."
        ),
        notes=(
            "Node 31 (v7.1): mechanistic two-step kinetic (4-ODE) with "
            "competitive hydrolysis. See edc_nhs_kinetics.react_edc_nhs_two_step."
        ),
    ),

    # ═══════════════════════════════════════════════════════════════════
    # P3 — explicit alternate affinity-coupling chemistries
    # ═══════════════════════════════════════════════════════════════════

    "protein_a_nhs_coupling": ReagentProfile(
        name="Protein A NHS-ester coupling",
        cas="91932-65-9",
        reagent_identity="Recombinant Protein A primary amines",
        installed_ligand="Protein A",
        functional_mode="affinity_ligand",
        reaction_type="protein_coupling",
        chemistry_class="nhs_amine",
        target_acs=ACSSiteType.NHS_ESTER,
        product_acs=None,
        k_forward=2e-6,
        E_a=22000.0,
        stoichiometry=1.0,
        hydrolysis_rate=2e-5,
        ph_optimum=7.5,
        ph_min=6.8, ph_max=8.5,
        temperature_default=277.15,
        temperature_min=273.15, temperature_max=283.15,
        time_default=14400.0,
        ligand_mw=42000.0,
        ligand_r_h=2.5e-9,
        is_macromolecule=True,
        activity_retention=0.55,
        activity_retention_uncertainty=0.15,
        max_surface_density=2e-8,
        binding_model_hint="fc_affinity",
        confidence_tier="ranking_only",
        calibration_source="Estimated NHS-amine protein coupling; requires local ligand density/activity assays",
        notes="Use after EDC/NHS activation; NHS ester hydrolysis competes strongly with protein coupling.",
    ),

    "hydrazide_spacer_arm": ReagentProfile(
        name="Hydrazide spacer arm (EPOXIDE -> HYDRAZIDE)",
        cas="60-34-4",
        reagent_identity="Adipic acid dihydrazide / hydrazide spacer equivalent",
        installed_ligand="Hydrazide spacer",
        functional_mode="spacer",
        reaction_type="spacer_arm",
        chemistry_class="epoxide_hydrazide",
        target_acs=ACSSiteType.EPOXIDE,
        product_acs=ACSSiteType.HYDRAZIDE,
        k_forward=2e-5,
        E_a=42000.0,
        stoichiometry=1.0,
        hydrolysis_rate=5e-6,
        ph_optimum=9.5,
        ph_min=8.0, ph_max=11.0,
        temperature_default=298.15,
        time_default=14400.0,
        spacer_length_angstrom=8.0,
        distal_group_yield=0.80,
        profile_role="spacer_intermediate",
        m3_support_level="not_mapped",
        confidence_tier="semi_quantitative",
        calibration_source="Estimated epoxide-hydrazide spacer installation kinetics",
        notes="Creates hydrazide sites for aldehyde/glycan capture; local hydrazide density assay required.",
    ),

    "protein_a_hydrazide_coupling": ReagentProfile(
        name="Oxidized Protein A hydrazide coupling",
        cas="91932-65-9",
        reagent_identity="Periodate-oxidized Protein A aldehydes",
        installed_ligand="Protein A",
        functional_mode="affinity_ligand",
        reaction_type="protein_coupling",
        chemistry_class="hydrazide_aldehyde",
        target_acs=ACSSiteType.HYDRAZIDE,
        product_acs=None,
        k_forward=8e-7,
        E_a=20000.0,
        stoichiometry=1.0,
        hydrolysis_rate=1e-6,
        ph_optimum=5.5,
        ph_min=4.5, ph_max=6.5,
        temperature_default=277.15,
        temperature_min=273.15, temperature_max=283.15,
        time_default=57600.0,
        ligand_mw=42000.0,
        ligand_r_h=2.5e-9,
        is_macromolecule=True,
        activity_retention=0.70,
        activity_retention_uncertainty=0.15,
        max_surface_density=2e-8,
        binding_model_hint="fc_affinity",
        confidence_tier="ranking_only",
        calibration_source="Estimated hydrazone/Schiff-base immobilization; requires retained-activity assay",
        notes="Models oriented glycan/aldehyde capture onto hydrazide media; reduction stabilization is not yet explicit.",
    ),

    "protein_a_vs_coupling": ReagentProfile(
        name="Protein A vinyl-sulfone coupling",
        cas="91932-65-9",
        reagent_identity="Protein A nucleophiles",
        installed_ligand="Protein A",
        functional_mode="affinity_ligand",
        reaction_type="protein_coupling",
        chemistry_class="vs_amine_thiol",
        target_acs=ACSSiteType.VINYL_SULFONE,
        product_acs=None,
        k_forward=1e-6,
        E_a=23000.0,
        stoichiometry=1.0,
        hydrolysis_rate=1e-6,
        ph_optimum=8.5,
        ph_min=7.0, ph_max=9.5,
        temperature_default=277.15,
        temperature_min=273.15, temperature_max=283.15,
        time_default=28800.0,
        ligand_mw=42000.0,
        ligand_r_h=2.5e-9,
        is_macromolecule=True,
        activity_retention=0.60,
        activity_retention_uncertainty=0.15,
        max_surface_density=2e-8,
        binding_model_hint="fc_affinity",
        confidence_tier="ranking_only",
        calibration_source="Estimated vinyl-sulfone protein immobilization; requires ligand density/activity assay",
        notes="Vinyl sulfone reacts with amine/thiol nucleophiles; buffer nucleophiles can compete.",
    ),

    "nickel_charging_nta": ReagentProfile(
        name="Nickel(II) charging of NTA sites",
        cas="7786-81-4",
        reagent_identity="Nickel(II) sulfate",
        installed_ligand="Ni2+-NTA",
        functional_mode="metal_charging",
        reaction_type="metal_charging",
        chemistry_class="metal_chelation",
        target_acs=ACSSiteType.NTA,
        product_acs=None,
        k_forward=0.0,
        E_a=0.0,
        stoichiometry=1.0,
        metal_ion="Ni2+",
        metal_association_constant=3e11,
        ph_optimum=7.0,
        ph_min=5.0, ph_max=8.0,
        temperature_default=298.15,
        time_default=1800.0,
        profile_role="native",
        m3_support_level="mapped_estimated",
        confidence_tier="semi_quantitative",
        calibration_source="NTA-Ni stability constant; metal loading requires ICP or colorimetric assay",
        notes="Charges explicit NTA site inventory; assumes no competing chelators in buffer.",
    ),

    "nickel_charging_ida": ReagentProfile(
        name="Nickel(II) charging of IDA sites",
        cas="7786-81-4",
        reagent_identity="Nickel(II) sulfate",
        installed_ligand="Ni2+-IDA",
        functional_mode="metal_charging",
        reaction_type="metal_charging",
        chemistry_class="metal_chelation",
        target_acs=ACSSiteType.IDA,
        product_acs=None,
        k_forward=0.0,
        E_a=0.0,
        stoichiometry=1.0,
        metal_ion="Ni2+",
        metal_association_constant=5e9,
        ph_optimum=7.0,
        ph_min=5.0, ph_max=8.0,
        temperature_default=298.15,
        time_default=1800.0,
        profile_role="native",
        m3_support_level="mapped_estimated",
        confidence_tier="semi_quantitative",
        calibration_source="IDA-Ni stability estimate; metal loading requires ICP or colorimetric assay",
        notes="Charges explicit IDA site inventory; lower specificity than NTA and more metal-leaching risk.",
    ),

    # ═══════════════════════════════════════════════════════════════════
    # v5.9.4 — Washing (1 profile)
    # ═══════════════════════════════════════════════════════════════════

    "wash_buffer": ReagentProfile(
        name="Wash buffer (advisory residual removal)",
        cas="N/A",
        reagent_identity="Phosphate buffer pH 7.4",
        installed_ligand="N/A",
        functional_mode="washing",
        reaction_type="washing",
        chemistry_class="diffusion_out",
        target_acs=ACSSiteType.EPOXIDE, product_acs=None,
        k_forward=0.0, E_a=0.0, stoichiometry=1.0,
        ph_optimum=7.4,
        temperature_default=298.15,
        time_default=3600.0,
        regulatory_limit_ppm=1.0,
        profile_role="native",
        m3_support_level="not_mapped",
        confidence_tier="semi_quantitative",
        calibration_source="Advisory diffusion-out screening model",
        notes="Advisory only; does not claim GMP pass/fail without validated residual assays",
    ),

    # ═══════════════════════════════════════════════════════════════════
    # v9.2 Tier-1 reagent additions (M1–M9)
    # ═══════════════════════════════════════════════════════════════════

    # ── M1 (B1) — Classical affinity-resin completion ─────────────────

    # B1.2 CNBr activation. Kohn & Wilchek 1981 Anal. Biochem. 115:375.
    # k ~ 1e-3 m^3/(mol*s) at pH 11, 4 °C; E_a ~ 35 kJ/mol.
    # CNBr is HIGHLY TOXIC (HCN release on hydrolysis) — hazard surfaced.
    "cnbr_activation": ReagentProfile(
        name="Cyanogen bromide (OH activation)",
        cas="506-68-3",
        reaction_type="activation",
        target_acs=ACSSiteType.HYDROXYL,
        product_acs=ACSSiteType.CYANATE_ESTER,
        k_forward=1e-3,
        E_a=35000.0,
        stoichiometry=1.0,
        hydrolysis_rate=2e-3,         # short activated-site half-life
        ph_optimum=11.0,
        temperature_default=277.15,    # 4 °C — low T to suppress hydrolysis
        time_default=600.0,            # 10 min
        functional_mode="activator",
        chemistry_class="cnbr_amine",
        ph_min=10.0, ph_max=12.0,
        temperature_min=273.15, temperature_max=283.15,
        confidence_tier="semi_quantitative",
        calibration_source="Kohn & Wilchek (1981) Anal. Biochem. 115:375",
        hazard_class="acute_toxic_carcinogen",
        notes=(
            "Classic Sepharose affinity activation. CNBr forms cyanate "
            "ester / imidocarbonate intermediate that couples primary "
            "amines via isourea linkage. EXTREME HAZARD: HCN release "
            "on hydrolysis; perform in fume hood with constant pH "
            "monitoring. Short activated-site half-life (~5 min at 4 °C, "
            "pH 11) — couple ligand immediately after activation."
        ),
    ),

    # B1.3 CDI activation. Hearn 1981 Methods Enzymol. 135:102.
    # CDI gives a neutral imidazolyl-carbonate activated matrix; reacts
    # with primary amines to form a carbamate (no charge).
    # k ~ 5e-4 m^3/(mol*s) at pH 9, 25 °C; E_a ~ 50 kJ/mol.
    "cdi_activation": ReagentProfile(
        name="1,1′-Carbonyldiimidazole (OH activation)",
        cas="530-62-1",
        reaction_type="activation",
        target_acs=ACSSiteType.HYDROXYL,
        product_acs=ACSSiteType.IMIDAZOLYL_CARBONATE,
        k_forward=5e-4,
        E_a=50000.0,
        stoichiometry=1.0,
        hydrolysis_rate=3e-4,
        ph_optimum=9.0,
        temperature_default=298.15,
        time_default=3600.0,
        functional_mode="activator",
        chemistry_class="cdi_amine",
        ph_min=7.5, ph_max=10.0,
        confidence_tier="semi_quantitative",
        calibration_source="Hearn (1981) Methods Enzymol. 135:102",
        hazard_class="moisture_sensitive",
        notes=(
            "Modern CNBr alternative. CDI activates hydroxyls in "
            "anhydrous DMSO/dioxane to imidazolyl carbonate, which "
            "couples primary amines giving a neutral carbamate (no "
            "isourea charge). Lower hazard than CNBr. Reagent is "
            "moisture-sensitive — use freshly opened CDI."
        ),
    ),

    # B1.4 Hexyl HIC ligand. Fills the gap between butyl(C4) and octyl(C8).
    # Hjertén 1973 J. Chromatogr. 87:325 (canonical alkyl-HIC reference).
    "hexyl_coupling": ReagentProfile(
        name="Hexylamine HIC ligand (C6 alkyl)",
        cas="111-26-2",
        reaction_type="coupling",
        target_acs=ACSSiteType.EPOXIDE,
        product_acs=None,
        k_forward=2e-4,
        E_a=40000.0,
        stoichiometry=1.0,
        hydrolysis_rate=1e-5,
        ph_optimum=9.5,
        temperature_default=298.15,
        time_default=14400.0,        # 4 h
        functional_mode="hic_ligand",
        chemistry_class="epoxide_amine",
        installed_ligand="hexyl_C6",
        ph_min=8.0, ph_max=11.0,
        binding_model_hint="salt_promoted",
        confidence_tier="semi_quantitative",
        calibration_source="Hjertén (1973) J. Chromatogr. 87:325",
        notes=(
            "Hexyl (C6) alkyl HIC ligand — interpolates HIC selectivity "
            "between butyl (C4) and octyl (C8). Coupled to epoxide- or "
            "DVS-activated agarose via hexylamine. Salt-promoted "
            "hydrophobic binding; eluted by descending salt gradient."
        ),
    ),

    # ── M2 (B2) — Oriented-glycoprotein immobilization workflow ───────

    # B2.1 Sodium periodate (vicinal diol → aldehyde via Malaprade).
    # Bobbitt 1956 Adv. Carbohydr. Chem. 11:1.
    # Effective oxidation rate is pseudo-first-order in NaIO4 at typical
    # 5–20 mM doses; k ~ 2e-3 /s at pH 5, 4 °C.
    "periodate_oxidation": ReagentProfile(
        name="Sodium periodate (vicinal diol → aldehyde)",
        cas="7790-28-5",
        reaction_type="activation",
        target_acs=ACSSiteType.HYDROXYL,    # vicinal diol; consumed pair
        product_acs=ACSSiteType.ALDEHYDE,
        k_forward=2e-3,
        E_a=40000.0,
        stoichiometry=1.0,             # 1 NaIO4 per vicinal-diol cleavage → 2 CHO
        hydrolysis_rate=0.0,
        ph_optimum=5.0,
        temperature_default=277.15,    # 4 °C — slow chain scission
        time_default=3600.0,
        functional_mode="activator",
        chemistry_class="aldehyde_amine",   # downstream coupling is via aldehyde
        ph_min=3.5, ph_max=7.0,
        temperature_min=273.15, temperature_max=298.15,
        confidence_tier="semi_quantitative",
        calibration_source="Bobbitt (1956) Adv. Carbohydr. Chem. 11:1",
        hazard_class="strong_oxidizer",
        notes=(
            "Malaprade oxidation: cleaves vicinal diols (2 OH on adjacent "
            "carbons) to a pair of aldehydes. Foundational for oriented "
            "glycoprotein immobilization (B2 workflow): oxidize glycan "
            "→ couple via hydrazide/aminooxy. Aldehyde density tracks "
            "oxidation degree linearly until ~30–50% conversion, beyond "
            "which chain scission dominates and the polymer mechanical "
            "integrity degrades."
        ),
    ),

    # B2.2 Adipic acid dihydrazide (ADH). Forms hydrazone with aldehydes.
    # Liu & Wilcox 1976 Biochim. Biophys. Acta 426:373.
    "adh_hydrazone": ReagentProfile(
        name="Adipic acid dihydrazide (ADH)",
        cas="1071-93-8",
        reaction_type="coupling",
        target_acs=ACSSiteType.ALDEHYDE,
        product_acs=ACSSiteType.HYDRAZIDE,    # distal hydrazide remains for next step
        k_forward=5e-3,
        E_a=35000.0,
        stoichiometry=1.0,
        hydrolysis_rate=5e-4,         # hydrazone hydrolyses at low pH
        ph_optimum=5.5,
        temperature_default=298.15,
        time_default=14400.0,         # 4 h
        functional_mode="spacer",
        chemistry_class="hydrazone",
        installed_ligand="hydrazide_distal",
        ph_min=4.5, ph_max=7.5,
        confidence_tier="semi_quantitative",
        calibration_source="Liu & Wilcox (1976) Biochim. Biophys. Acta 426:373",
        notes=(
            "Bifunctional hydrazide: one end forms hydrazone with "
            "support aldehyde (e.g. periodate-oxidized agarose), the "
            "other end remains free for downstream glycoprotein/aldehyde "
            "coupling. Hydrazone is reversible at pH < 5 — for permanent "
            "linkage, follow with NaBH3CN reduction to alkylhydrazide."
        ),
    ),

    # B2.3 Aminooxy-PEG linker. Forms oxime (more stable than hydrazone).
    # Kalia & Raines 2008 Angew. Chem. Int. Ed. 47:7523.
    "aminooxy_peg_linker": ReagentProfile(
        name="Aminooxy-PEG linker (oxime ligation)",
        cas="N/A (PEG oligomer)",
        reaction_type="coupling",
        target_acs=ACSSiteType.ALDEHYDE,
        product_acs=ACSSiteType.AMINOOXY,
        k_forward=8e-3,
        E_a=30000.0,
        stoichiometry=1.0,
        hydrolysis_rate=2e-5,         # oxime is very stable; minimal hydrolysis
        ph_optimum=4.5,                # acidic catalysis accelerates oxime ligation
        temperature_default=298.15,
        time_default=7200.0,
        functional_mode="spacer",
        chemistry_class="oxime",
        installed_ligand="aminooxy_distal",
        ligand_mw=2000.0,              # PEG2k variant typical
        ph_min=3.5, ph_max=7.0,
        confidence_tier="semi_quantitative",
        calibration_source="Kalia & Raines (2008) Angew. Chem. Int. Ed. 47:7523",
        notes=(
            "Bioorthogonal oxime ligation. Aminooxy reacts with "
            "aldehyde/ketone forming oxime — more hydrolytically "
            "stable than hydrazone (Liu 1976) by ~100×. PEG spacer "
            "minimises matrix-protein steric interactions. Optimal "
            "pH 4.5 with acetate or aniline catalysis. Aminooxy is "
            "naturally absent in proteins → bioorthogonal in crude lysate."
        ),
    ),

    # ── M3 (B3) — Dye pseudo-affinity ─────────────────────────────────

    # B3.1 Cyanuric chloride (triazine activation).
    # Korpela & Mäntsälä 1968 Anal. Biochem. 23:381.
    "cyanuric_chloride_activation": ReagentProfile(
        name="Cyanuric chloride (triazine activation)",
        cas="108-77-0",
        reaction_type="activation",
        target_acs=ACSSiteType.HYDROXYL,
        product_acs=ACSSiteType.TRIAZINE_REACTIVE,
        k_forward=3e-3,                # very fast at first chloride
        E_a=30000.0,
        stoichiometry=1.0,
        hydrolysis_rate=5e-4,
        ph_optimum=9.0,
        temperature_default=277.15,    # 4 °C — slow di/trisubstitution
        time_default=1800.0,
        functional_mode="activator",
        chemistry_class="dye_triazine",
        ph_min=8.0, ph_max=10.5,
        temperature_min=273.15, temperature_max=288.15,
        confidence_tier="semi_quantitative",
        calibration_source="Korpela & Mäntsälä (1968) Anal. Biochem. 23:381",
        hazard_class="reactive_corrosive",
        notes=(
            "2,4,6-Trichloro-1,3,5-triazine activation of polysaccharide "
            "OH gives a dichlorotriazine support. The remaining 2 chlorines "
            "are then sequentially substituted by dye/amine ligands. "
            "Reactivity drops with each substitution — first Cl reacts at "
            "0–5 °C, second at 25 °C, third at 60–80 °C."
        ),
    ),

    # B3.2 Cibacron Blue F3GA — industrial pseudo-affinity dye.
    # Atkinson et al. 1981 Biochem. Soc. Trans. 9:290.
    "cibacron_blue_f3ga_coupling": ReagentProfile(
        name="Cibacron Blue F3GA (Reactive Blue 2)",
        cas="12236-82-7",
        reaction_type="coupling",
        target_acs=ACSSiteType.TRIAZINE_REACTIVE,
        product_acs=None,
        k_forward=1e-3,
        E_a=40000.0,
        stoichiometry=1.0,
        hydrolysis_rate=1e-5,
        ph_optimum=10.0,
        temperature_default=313.15,    # 40 °C — drives second-Cl substitution
        time_default=14400.0,
        functional_mode="dye_pseudo_affinity",
        chemistry_class="dye_triazine",
        installed_ligand="cibacron_blue_f3ga",
        ligand_mw=773.0,
        ph_min=9.0, ph_max=11.0,
        binding_model_hint="affinity",
        confidence_tier="semi_quantitative",
        calibration_source="Atkinson et al. (1981) Biochem. Soc. Trans. 9:290",
        notes=(
            "Industrial pseudo-affinity dye for nucleotide-binding "
            "proteins, albumin, and many enzymes. Mechanism is mixed: "
            "anthraquinone hydrophobic stacking + sulfonate ionic "
            "interactions + sequence-specific recognition by NAD-binding "
            "clefts. Couples to triazine-activated agarose via the "
            "remaining chlorine. Industrial standard (Blue Sepharose). "
            "WARNING: dye leakage under harsh elution; monitor effluent "
            "absorbance at 610 nm."
        ),
    ),

    # B3.3 Triazine-dye leakage warning profile (advisory).
    # Lowe & Pearson 1984 Methods Enzymol. 104:97.
    "triazine_dye_leakage_advisory": ReagentProfile(
        name="Triazine dye leakage (advisory monitor)",
        cas="N/A",
        reaction_type="washing",
        target_acs=ACSSiteType.TRIAZINE_REACTIVE,
        product_acs=None,
        k_forward=1e-7,
        E_a=80000.0,
        stoichiometry=1.0,
        hydrolysis_rate=1e-7,           # very slow at neutral pH
        ph_optimum=7.0,
        temperature_default=298.15,
        time_default=3600.0,
        functional_mode="washing",
        chemistry_class="diffusion_out",
        regulatory_limit_ppm=1.0,
        profile_role="native",
        m3_support_level="not_mapped",
        confidence_tier="ranking_only",
        calibration_source="Lowe & Pearson (1984) Methods Enzymol. 104:97",
        notes=(
            "Advisory profile: monitors residual triazine-dye leakage "
            "during elution / regeneration. Triazine-dye supports "
            "(Cibacron Blue, Procion Red) leak measurable dye on harsh "
            "regeneration with NaOH or chaotrope; measure A610 in flow-"
            "through. Does NOT make a GMP claim; advisory only."
        ),
    ),

    # ── M4 (B4) — Mixed-mode antibody capture ─────────────────────────

    # B4.1 Thiophilic ligand (DVS + 2-mercaptoethanol).
    # Porath et al. 1985 FEBS Lett. 185:306.
    "thiophilic_2me_coupling": ReagentProfile(
        name="2-Mercaptoethanol thiophilic ligand (T-Sorb / T-Gel)",
        cas="60-24-2",
        reaction_type="coupling",
        target_acs=ACSSiteType.VINYL_SULFONE,
        product_acs=None,
        k_forward=8e-4,
        E_a=35000.0,
        stoichiometry=1.0,
        hydrolysis_rate=1e-6,
        ph_optimum=9.0,
        temperature_default=298.15,
        time_default=14400.0,
        functional_mode="thiophilic",
        chemistry_class="vs_thiol",
        installed_ligand="thiophilic_2me",
        ligand_mw=78.13,
        ph_min=7.0, ph_max=10.0,
        binding_model_hint="salt_promoted",
        confidence_tier="semi_quantitative",
        calibration_source="Porath et al. (1985) FEBS Lett. 185:306",
        notes=(
            "Salt-promoted thiophilic IgG capture (T-Sorb, T-Gel). "
            "Couples mercaptoethanol thiol to DVS-activated agarose via "
            "Michael addition. Binding mechanism is electron-donor/"
            "acceptor at the sulfone-aromatic interface — distinct from "
            "hydrophobic burial in HIC. Loaded at high salt (0.5–1 M "
            "K2SO4 or Na2SO4); eluted at low salt."
        ),
    ),

    # B4.2 MEP HCIC (4-mercaptoethylpyridine).
    # Burton & Harding 1998 J. Chromatogr. A 814:71.
    "mep_hcic_coupling": ReagentProfile(
        name="4-Mercaptoethylpyridine (MEP HCIC)",
        cas="2127-04-2",
        reaction_type="coupling",
        target_acs=ACSSiteType.VINYL_SULFONE,
        product_acs=None,
        k_forward=6e-4,
        E_a=38000.0,
        stoichiometry=1.0,
        hydrolysis_rate=1e-6,
        ph_optimum=9.5,                # coupling at high pH (pyridine deprotonated)
        temperature_default=298.15,
        time_default=14400.0,
        functional_mode="mixed_mode_hcic",
        chemistry_class="vs_thiol",
        installed_ligand="mep_4mep",
        ligand_mw=139.22,
        ph_min=8.0, ph_max=11.0,
        pKa_nucleophile=4.5,           # pyridine pKa ≈ 4.5 — drives elution switch
        binding_model_hint="mixed_mode",
        confidence_tier="semi_quantitative",
        calibration_source="Burton & Harding (1998) J. Chromatogr. A 814:71",
        notes=(
            "Hydrophobic Charge-Induction Chromatography (HCIC). At "
            "loading pH (7.0) the pyridine is uncharged → IgG binds "
            "hydrophobically without salt addition. At elution pH (4) "
            "the pyridinium becomes cationic and electrostatically "
            "repels the now-cationic IgG, eluting it. Industrial "
            "antibody-capture mixed-mode (Pall MEP HyperCel / Cytiva "
            "MEP). pKa_nucleophile=4.5 drives the M3 pH-switchable "
            "binding model."
        ),
    ),

    # ── M5 (B5) — Bis-epoxide hardening (Q-001 resolution: single profile) ──

    # B5.1 Bis-epoxide family — single parameterized profile per Q-001.
    # Spacer length is a parameter. PEGDGE / EGDGE / BDDE are different
    # spacer-length variants of the same chemistry class (epoxide-amine /
    # epoxide-hydroxyl alkaline crosslinking).
    # Hahn et al. 2006 Biomaterials 27:1104.
    "bis_epoxide_crosslinking": ReagentProfile(
        name="Bis-epoxide family (PEGDGE/EGDGE/BDDE)",
        cas="2425-79-8 (BDDE) / 1675-54-3 (EGDGE) / variable (PEGDGE)",
        reaction_type="crosslinking",
        target_acs=ACSSiteType.HYDROXYL,
        product_acs=None,
        k_forward=1e-5,
        E_a=55000.0,
        stoichiometry=0.5,             # 1 bis-epoxide bridges 2 OH
        hydrolysis_rate=2e-5,           # alkaline hydrolysis competition
        ph_optimum=12.0,
        temperature_default=298.15,
        time_default=14400.0,
        functional_mode="crosslinker",
        chemistry_class="epoxide_amine",
        spacer_length_angstrom=12.0,    # default = BDDE (1,4-butanediol diglycidyl ether ≈ 12 Å)
        ph_min=10.0, ph_max=13.0,
        hazard_class="skin_sensitizer",
        confidence_tier="semi_quantitative",
        calibration_source="Hahn et al. (2006) Biomaterials 27:1104",
        notes=(
            "Bis-epoxide family — single parameterized profile per Q-001. "
            "Spacer length set via spacer_length_angstrom: BDDE≈12 Å, "
            "EGDGE≈8 Å, PEGDGE-200≈30 Å, PEGDGE-600≈80 Å. Workhorse for "
            "polysaccharide hardening (BDDE for HA dermal fillers, "
            "PEGDGE for agarose). Alkaline activation drives epoxide "
            "ring-opening; alkaline hydrolysis is a competing reaction."
        ),
    ),

    # ── M6 (B7) — Click chemistry (CuAAC + SPAAC) ─────────────────────

    # B7.1 CuAAC handle. Kolb et al. 2001 Angew. Chem. Int. Ed. 40:2004.
    # Cu(I) catalysed; effective k ~ 10 m^3/(mol*s) for typical alkyne+
    # azide concentrations. ICH Q3D limit on residual Cu in biotherapeutics
    # ≈ 30 µg/day → flag for downstream removal.
    "cuaac_click_coupling": ReagentProfile(
        name="CuAAC click handle (Cu-catalysed azide-alkyne)",
        cas="N/A (chemistry class)",
        reaction_type="coupling",
        target_acs=ACSSiteType.AZIDE,
        product_acs=None,
        k_forward=10.0,                # very fast with Cu(I) catalyst
        E_a=20000.0,
        stoichiometry=1.0,
        hydrolysis_rate=0.0,            # triazole is essentially inert
        ph_optimum=7.4,
        temperature_default=298.15,
        time_default=3600.0,
        functional_mode="click_handle",
        chemistry_class="cuaac",
        installed_ligand="triazole",
        regulatory_limit_ppm=30.0,      # ICH Q3D residual Cu
        ph_min=4.0, ph_max=9.0,
        confidence_tier="semi_quantitative",
        calibration_source="Kolb et al. (2001) Angew. Chem. Int. Ed. 40:2004",
        hazard_class="cu_residual_ich_q3d",
        notes=(
            "Cu(I)-catalysed azide-alkyne cycloaddition. Forms 1,4-"
            "disubstituted 1,2,3-triazole — essentially irreversible. "
            "Very fast under saturating CuSO4 + ascorbate. CRITICAL for "
            "biotherapeutic resins: residual Cu must meet ICH Q3D oral "
            "exposure limits (PDE 30 µg/day → typical ~10 ppm bound Cu "
            "after EDTA wash). For Cu-sensitive applications, use SPAAC "
            "(see spaac_click_coupling)."
        ),
    ),

    # B7.2 SPAAC handle (strain-promoted; copper-free).
    # Agard et al. 2004 J. Am. Chem. Soc. 126:15046.
    "spaac_click_coupling": ReagentProfile(
        name="SPAAC click handle (strain-promoted; Cu-free)",
        cas="N/A (chemistry class)",
        reaction_type="coupling",
        target_acs=ACSSiteType.AZIDE,
        product_acs=None,
        k_forward=0.5,                 # ~20× slower than CuAAC; no catalyst needed
        E_a=25000.0,
        stoichiometry=1.0,
        hydrolysis_rate=0.0,
        ph_optimum=7.4,
        temperature_default=298.15,
        time_default=14400.0,
        functional_mode="click_handle",
        chemistry_class="spaac",
        installed_ligand="triazole_spaac",
        ph_min=5.0, ph_max=9.0,
        confidence_tier="semi_quantitative",
        calibration_source="Agard et al. (2004) J. Am. Chem. Soc. 126:15046",
        notes=(
            "Strain-promoted azide-alkyne cycloaddition (SPAAC). "
            "Uses cyclooctyne (DBCO/BCN) + azide; no Cu catalyst needed. "
            "Slower than CuAAC (~0.5 vs 10 m^3/mol/s) but biotherapeutic-"
            "compatible without Cu-removal step. Preferred for live-cell "
            "or Cu-sensitive protein conjugation."
        ),
    ),

    # ── v0.3.6: inverse-direction click reagents ──────────────────────
    # Click reactions are bidirectional w.r.t. which partner sits on the
    # resin vs the ligand. The two profiles above (cuaac_click_coupling
    # / spaac_click_coupling) target AZIDE-functionalised resin. The
    # two below target ALKYNE-functionalised resin — equally common in
    # practice. Adding both directions also closes the v0.3.5 audit gap
    # where ALKYNE was unreferenced via target_acs / product_acs.

    # CuAAC, alkyne-on-resin direction.
    "cuaac_click_alkyne_side": ReagentProfile(
        name="CuAAC click handle (alkyne on resin; azide ligand)",
        cas="N/A (chemistry class)",
        reaction_type="coupling",
        target_acs=ACSSiteType.ALKYNE,
        product_acs=None,
        k_forward=10.0,
        E_a=20000.0,
        stoichiometry=1.0,
        hydrolysis_rate=0.0,
        ph_optimum=7.4,
        temperature_default=298.15,
        time_default=3600.0,
        functional_mode="click_handle",
        chemistry_class="cuaac",
        installed_ligand="triazole",
        regulatory_limit_ppm=30.0,
        ph_min=4.0, ph_max=9.0,
        confidence_tier="semi_quantitative",
        calibration_source="Kolb et al. (2001) Angew. Chem. Int. Ed. 40:2004",
        hazard_class="cu_residual_ich_q3d",
        notes=(
            "CuAAC, with the alkyne functional group on the resin and "
            "the azide on the ligand. Same chemistry / kinetics / Cu "
            "residual concern as cuaac_click_coupling; choose this "
            "profile when the resin was alkyne-activated (e.g. propargyl "
            "ether ECH route)."
        ),
    ),

    # SPAAC, alkyne-on-resin direction.
    "spaac_click_alkyne_side": ReagentProfile(
        name="SPAAC click handle (DBCO/BCN on resin; azide ligand)",
        cas="N/A (chemistry class)",
        reaction_type="coupling",
        target_acs=ACSSiteType.ALKYNE,
        product_acs=None,
        k_forward=0.5,
        E_a=25000.0,
        stoichiometry=1.0,
        hydrolysis_rate=0.0,
        ph_optimum=7.4,
        temperature_default=298.15,
        time_default=14400.0,
        functional_mode="click_handle",
        chemistry_class="spaac",
        installed_ligand="triazole_spaac",
        ph_min=5.0, ph_max=9.0,
        confidence_tier="semi_quantitative",
        calibration_source="Agard et al. (2004) J. Am. Chem. Soc. 126:15046",
        notes=(
            "SPAAC, with the strain-promoted alkyne (DBCO or BCN) "
            "pre-installed on the resin via an NHS-ester or amine "
            "linker; the ligand is azide-functionalised. Same kinetics "
            "and biotherapeutic-compatibility profile as "
            "spaac_click_coupling."
        ),
    ),

    # ── M7 (B8) — Multipoint enzyme immobilization ────────────────────

    # B8.1 Glyoxyl-agarose (chained: glycidol → diol → periodate → glyoxyl).
    # Mateo et al. 2007 Biotechnol. Bioeng. 96:5.
    "glyoxyl_chained_activation": ReagentProfile(
        name="Glyoxyl-agarose (multipoint enzyme support)",
        cas="N/A (composite chemistry)",
        reaction_type="activation",
        target_acs=ACSSiteType.HYDROXYL,
        product_acs=ACSSiteType.GLYOXYL,
        k_forward=1e-3,                # rate-limiting periodate step
        E_a=45000.0,
        stoichiometry=1.0,
        hydrolysis_rate=1e-4,
        ph_optimum=10.0,                # multipoint Lys coupling at high pH
        temperature_default=298.15,
        time_default=14400.0,
        functional_mode="activator",
        chemistry_class="glyoxyl_multipoint",
        ph_min=9.5, ph_max=11.0,
        confidence_tier="semi_quantitative",
        calibration_source="Mateo et al. (2007) Biotechnol. Bioeng. 96:5",
        notes=(
            "Two-step activation: glycidol coats agarose -OH with "
            "glyceryl ether (giving 1,2-diol termini); periodate then "
            "cleaves to glyoxyl (-CHO). Used for MULTIPOINT covalent "
            "enzyme immobilization (lipase, penicillin-G acylase, CALB). "
            "Multiple Lys residues anchor simultaneously at pH 10; "
            "subsequent NaBH4 reduction makes anchors permanent. "
            "Yields T_50 uplifts of 10–20 °C vs. single-point coupling."
        ),
    ),

    # B8.2 Multipoint stability uplift profile (advisory; consumed by M3).
    # Mateo et al. 2007 Biotechnol. Bioeng. 96:5; Pessela et al. 2003.
    "multipoint_stability_uplift": ReagentProfile(
        name="Multipoint Lys-anchor stability model",
        cas="N/A (model)",
        reaction_type="coupling",
        target_acs=ACSSiteType.GLYOXYL,
        product_acs=None,
        k_forward=5e-4,
        E_a=40000.0,
        stoichiometry=1.0,             # per anchor
        hydrolysis_rate=1e-7,
        ph_optimum=10.0,
        temperature_default=298.15,
        time_default=86400.0,           # 24 h for full multipoint coupling
        functional_mode="affinity_ligand",
        chemistry_class="glyoxyl_multipoint",
        installed_ligand="multipoint_anchored_enzyme",
        is_macromolecule=True,
        ligand_mw=33000.0,             # CALB-class model enzyme
        activity_retention=0.85,        # multipoint preserves 85% under stable conditions
        activity_retention_uncertainty=0.10,
        binding_model_hint="near_irreversible",
        confidence_tier="ranking_only",
        calibration_source="Mateo et al. (2007) Biotechnol. Bioeng. 96:5",
        notes=(
            "Multipoint Lys-anchored enzyme: T_50 uplift = 5 + 5×n_anchors "
            "°C (qualitative trend; calibration is wet-lab). M3 thermal-"
            "deactivation rate constant should be reduced by exp(-n_anchor "
            "× E_anchor / RT). For CALB-class lipase: n_anchors typically "
            "3–5 at pH 10, 24 h."
        ),
    ),

    # ── M8 (B9) — Material-as-ligand: amylose-MBP ─────────────────────

    # B9.2 Amylose resin profile — material itself is the affinity matrix.
    # Kellermann & Ferenci 1982 Methods Enzymol. 90:459 (amylose+MBP).
    "amylose_mbp_affinity": ReagentProfile(
        name="Amylose resin (MBP-tag affinity)",
        cas="9005-82-7",
        reaction_type="coupling",
        target_acs=ACSSiteType.HYDROXYL,    # hydroxyl-rich amylose backbone IS the matrix
        product_acs=None,
        k_forward=1e-2,                # fast binding; MBP-amylose Kd ~ 1 µM
        E_a=20000.0,
        stoichiometry=1.0,
        hydrolysis_rate=0.0,
        ph_optimum=7.4,
        temperature_default=277.15,    # 4 °C standard for MBP work
        time_default=1800.0,
        functional_mode="material_as_ligand",
        chemistry_class="amine_covalent",   # placeholder; binding is non-covalent
        installed_ligand="amylose_matrix_for_mbp",
        is_macromolecule=True,
        ligand_mw=42500.0,             # MBP partner protein
        binding_model_hint="affinity",
        confidence_tier="semi_quantitative",
        calibration_source="Kellermann & Ferenci (1982) Methods Enzymol. 90:459",
        notes=(
            "Material-as-ligand pattern (B9): the polysaccharide matrix "
            "(crosslinked amylose) IS the affinity ligand. MBP-tagged "
            "fusion proteins bind reversibly; eluted with 10 mM maltose. "
            "Kd ~ 1 µM. Very high specificity for MBP. Note: matrix-"
            "associated bacterial contaminants are reported (Riggs 2000) "
            "— pre-equilibrate with column wash to mitigate."
        ),
    ),

    # ── M9 (B10) — Boronate affinity ──────────────────────────────────

    # B10.1 + B10.2 Aminophenylboronic acid (APBA) — boronate cis-diol affinity.
    # Mallia et al. 1989 J. Chromatogr. 480:201.
    "apba_boronate_coupling": ReagentProfile(
        name="m-Aminophenylboronic acid (boronate affinity)",
        cas="206658-89-1",
        reaction_type="coupling",
        target_acs=ACSSiteType.EPOXIDE,
        product_acs=None,
        k_forward=3e-4,
        E_a=40000.0,
        stoichiometry=1.0,
        hydrolysis_rate=1e-5,
        ph_optimum=9.0,                # coupling step
        temperature_default=298.15,
        time_default=14400.0,
        functional_mode="boronate",
        chemistry_class="epoxide_amine",
        installed_ligand="apba_boronate",
        ligand_mw=136.94,
        pKa_nucleophile=8.5,            # boronate pKa — drives cis-diol binding switch
        binding_model_hint="affinity",
        ph_min=7.5, ph_max=10.5,
        confidence_tier="semi_quantitative",
        calibration_source="Mallia et al. (1989) J. Chromatogr. 480:201",
        notes=(
            "Boronate affinity ligand. At pH > pKa_boronate (~8.5) the "
            "tetrahedral boronate reversibly esterifies cis-diols on "
            "glycoproteins, glycated proteins (HbA1c), and nucleotides. "
            "Loaded at pH 8.5; eluted by sorbitol or fructose competitor "
            "or by lowering pH. Industrial use: HbA1c capture, "
            "glycoprotein enrichment. M3 binding model uses pKa_nucleophile "
            "for the pH-switchable speciation."
        ),
    ),

    # ═══════════════════════════════════════════════════════════════════
    # v9.3 Tier-2 reagent additions (SA screening report § 6.2)
    # ═══════════════════════════════════════════════════════════════════

    # ── L2 Procion Red HE-3B (Reactive Red 120) — companion to Cibacron Blue
    # Lowe & Pearson 1984 Methods Enzymol. 104:97.
    "procion_red_he3b_coupling": ReagentProfile(
        name="Procion Red HE-3B (Reactive Red 120)",
        cas="61951-82-4",
        reaction_type="coupling",
        target_acs=ACSSiteType.TRIAZINE_REACTIVE,
        product_acs=None,
        k_forward=8e-4,
        E_a=42000.0,
        stoichiometry=1.0,
        hydrolysis_rate=1e-5,
        ph_optimum=10.0,
        temperature_default=313.15,    # 40 °C — drives 2nd-Cl substitution
        time_default=14400.0,
        functional_mode="dye_pseudo_affinity",
        chemistry_class="dye_triazine",
        installed_ligand="procion_red_he3b",
        ligand_mw=1338.0,
        ph_min=9.0, ph_max=11.0,
        binding_model_hint="affinity",
        confidence_tier="semi_quantitative",
        calibration_source="Lowe & Pearson (1984) Methods Enzymol. 104:97",
        notes=(
            "Triazine dye companion to Cibacron Blue. Specificity "
            "lean toward dehydrogenase / hydrogenase / oxidoreductase "
            "families (vs. NAD-binding clefts for Cibacron Blue). "
            "Dye leakage warning under harsh regeneration; literature "
            "explicitly raises concern about leached material under "
            "drastic regeneration."
        ),
    ),

    # ── L4 p-Aminobenzamidine — trypsin-like serine protease affinity.
    # Hofstee 1973 Biochim. Biophys. Acta 327:484.
    "p_aminobenzamidine_coupling": ReagentProfile(
        name="p-Aminobenzamidine (protease affinity)",
        cas="2498-50-2",
        reaction_type="coupling",
        target_acs=ACSSiteType.EPOXIDE,
        product_acs=None,
        k_forward=4e-4,
        E_a=38000.0,
        stoichiometry=1.0,
        hydrolysis_rate=1e-6,
        ph_optimum=9.0,
        temperature_default=298.15,
        time_default=14400.0,
        functional_mode="affinity_ligand",
        chemistry_class="epoxide_amine",
        installed_ligand="p_aminobenzamidine",
        ligand_mw=135.17,
        binding_model_hint="affinity",
        ph_min=7.0, ph_max=10.5,
        confidence_tier="semi_quantitative",
        calibration_source="Hofstee (1973) Biochim. Biophys. Acta 327:484",
        notes=(
            "Affinity ligand for trypsin-like serine proteases. Binds "
            "the S1 specificity pocket. Eluted by competitive arginine "
            "or benzamidine. Narrow target spectrum but high specificity "
            "(thrombin, plasmin, urokinase, trypsin, factor Xa)."
        ),
    ),

    # ── L6 Chitin-binding domain (CBD) / intein system — material-as-ligand.
    # Chong et al. 1997 Gene 192:271 (NEB IMPACT reference).
    "chitin_cbd_intein": ReagentProfile(
        name="Chitin / CBD-intein affinity (NEB IMPACT)",
        cas="N/A (system)",
        reaction_type="coupling",
        target_acs=ACSSiteType.HYDROXYL,    # chitin matrix is the affinity ligand itself
        product_acs=None,
        k_forward=5e-3,
        E_a=20000.0,
        stoichiometry=1.0,
        hydrolysis_rate=0.0,
        ph_optimum=8.0,
        temperature_default=277.15,    # 4 °C standard for IMPACT
        time_default=3600.0,
        functional_mode="material_as_ligand",
        chemistry_class="amine_covalent",   # placeholder; binding is non-covalent
        installed_ligand="chitin_matrix_for_cbd",
        is_macromolecule=True,
        ligand_mw=4500.0,             # CBD partner protein
        binding_model_hint="affinity",
        confidence_tier="semi_quantitative",
        calibration_source="Chong et al. (1997) Gene 192:271 (NEB IMPACT)",
        notes=(
            "Material-as-ligand pattern (B9 companion to amylose-MBP). "
            "Crosslinked chitin matrix IS the affinity ligand for CBD-"
            "tagged fusion proteins. Cleavage is on-column: thiol "
            "(DTT/MESNA) or pH/temperature-induced intein cleavage "
            "releases the untagged target. NEB IMPACT system."
        ),
    ),

    # ── L8a Jacalin lectin — O-linked glycoprotein affinity.
    # Sastry et al. 1986 J. Biol. Chem. 261:11726.
    "jacalin_coupling": ReagentProfile(
        name="Jacalin (O-linked glycoprotein lectin)",
        cas="9061-50-9",
        reaction_type="coupling",
        target_acs=ACSSiteType.EPOXIDE,
        product_acs=None,
        k_forward=5e-4,
        E_a=35000.0,
        stoichiometry=1.0,
        hydrolysis_rate=1e-6,
        ph_optimum=8.5,
        temperature_default=277.15,    # 4 °C — preserve lectin activity
        time_default=14400.0,
        functional_mode="affinity_ligand",
        chemistry_class="epoxide_amine",
        installed_ligand="jacalin",
        is_macromolecule=True,
        ligand_mw=66000.0,
        activity_retention=0.70,        # lectin coupling typically loses 30 % activity
        activity_retention_uncertainty=0.10,
        binding_model_hint="affinity",
        ph_min=7.0, ph_max=9.0,
        confidence_tier="semi_quantitative",
        calibration_source="Sastry et al. (1986) J. Biol. Chem. 261:11726",
        notes=(
            "Lectin from jackfruit; binds O-linked Galβ1-3GalNAc (Tn "
            "antigen). Used for IgA1 enrichment, mucin-class glycoprotein "
            "fractionation. Eluted by 0.1 M melibiose or galactose."
        ),
    ),

    # ── L8b Lentil lectin (LCA) — high-mannose / glycopeptide affinity.
    # Howard & Sage 1969 Biochim. Biophys. Acta 200:536.
    "lentil_lectin_coupling": ReagentProfile(
        name="Lentil lectin / LCA (high-mannose lectin)",
        cas="9013-32-3",
        reaction_type="coupling",
        target_acs=ACSSiteType.EPOXIDE,
        product_acs=None,
        k_forward=5e-4,
        E_a=35000.0,
        stoichiometry=1.0,
        hydrolysis_rate=1e-6,
        ph_optimum=8.5,
        temperature_default=277.15,
        time_default=14400.0,
        functional_mode="affinity_ligand",
        chemistry_class="epoxide_amine",
        installed_ligand="lentil_lectin",
        is_macromolecule=True,
        ligand_mw=49000.0,
        activity_retention=0.70,
        activity_retention_uncertainty=0.10,
        binding_model_hint="affinity",
        ph_min=7.0, ph_max=9.0,
        confidence_tier="semi_quantitative",
        calibration_source="Howard & Sage (1969) Biochim. Biophys. Acta 200:536",
        notes=(
            "Lectin from Lens culinaris. Binds α-mannose, α-glucose, "
            "and high-mannose / hybrid N-glycans. Requires Mn²⁺/Ca²⁺ "
            "cofactors. Eluted by 0.5 M α-methyl-mannoside."
        ),
    ),

    # ── L12 Sequence-specific oligonucleotide / DNA affinity.
    # Gadgil et al. 2001 Methods 23:113.
    "oligonucleotide_dna_coupling": ReagentProfile(
        name="Sequence-specific DNA affinity ligand",
        cas="N/A (oligo sequence)",
        reaction_type="coupling",
        target_acs=ACSSiteType.CYANATE_ESTER,
        product_acs=None,
        k_forward=2e-3,
        E_a=25000.0,
        stoichiometry=1.0,
        hydrolysis_rate=0.0,
        ph_optimum=8.3,
        temperature_default=277.15,
        time_default=14400.0,
        functional_mode="oligonucleotide",
        chemistry_class="cnbr_amine",
        installed_ligand="dna_oligo_sequence_specific",
        is_macromolecule=True,
        ligand_mw=20000.0,             # ~30 bp dsDNA placeholder
        binding_model_hint="affinity",
        ph_min=7.0, ph_max=9.5,
        confidence_tier="semi_quantitative",
        calibration_source="Gadgil et al. (2001) Methods 23:113",
        notes=(
            "Sequence-specific DNA affinity. Aminated dsDNA oligo "
            "coupled to CNBr-Sepharose; binds transcription factors / "
            "DNA-binding enzymes / nucleic-acid-binding proteins. Salt "
            "elution; competing oligo-DNA elution. Nuclease-stability "
            "warning for crude lysate work."
        ),
    ),

    # ── L13 Peptide-affinity ligand (HWRGWV class) — Protein-A alternative.
    # Yang et al. 2009 J. Chromatogr. A 1216:910.
    "peptide_affinity_hwrgwv": ReagentProfile(
        name="HWRGWV peptide ligand (Protein-A mimetic)",
        cas="N/A (peptide sequence)",
        reaction_type="coupling",
        target_acs=ACSSiteType.EPOXIDE,
        product_acs=None,
        k_forward=8e-4,
        E_a=30000.0,
        stoichiometry=1.0,
        hydrolysis_rate=1e-6,
        ph_optimum=8.5,
        temperature_default=298.15,
        time_default=14400.0,
        functional_mode="peptide_affinity",
        chemistry_class="epoxide_amine",
        installed_ligand="peptide_hwrgwv",
        ligand_mw=856.0,                # HWRGWV + spacer ≈ 856 Da
        binding_model_hint="affinity",
        ph_min=7.0, ph_max=10.0,
        confidence_tier="semi_quantitative",
        calibration_source="Yang et al. (2009) J. Chromatogr. A 1216:910",
        notes=(
            "Hexapeptide affinity ligand for IgG Fc — Protein-A "
            "alternative. Cheaper, lower-leachable, easier sterilisation. "
            "Coupled via N-terminal amine to epoxide-activated agarose. "
            "Eluted at low pH (acetate, pH 3-4)."
        ),
    ),

    # ── C9 HRP / H2O2 / tyramine — enzymatic phenol-radical crosslinking.
    # Sakai et al. 2009 Biomaterials 30:3371.
    "hrp_h2o2_tyramine": ReagentProfile(
        name="HRP / H2O2 / tyramine (enzymatic phenol radical)",
        cas="N/A (enzymatic system)",
        reaction_type="crosslinking",
        target_acs=ACSSiteType.PHENOL_TYRAMINE,
        product_acs=None,
        k_forward=5e-2,                # very fast under saturating H2O2
        E_a=30000.0,
        stoichiometry=0.5,             # 2 phenols → 1 dityramine
        hydrolysis_rate=0.0,
        ph_optimum=7.4,                # physiological — mild
        temperature_default=310.15,    # 37 °C
        time_default=600.0,             # 10 min — very fast crosslink
        functional_mode="crosslinker",
        chemistry_class="phenol_radical",
        ph_min=6.0, ph_max=8.5,
        confidence_tier="semi_quantitative",
        calibration_source="Sakai et al. (2009) Biomaterials 30:3371",
        hazard_class="oxidant_h2o2",
        notes=(
            "Enzymatic phenol-radical coupling. HRP + H2O2 oxidises "
            "tyramine-functionalized polysaccharides (HA-tyramine, "
            "alginate-tyramine, dextran-tyramine) to dityramine "
            "crosslinks. Mild conditions (pH 7.4, 37 °C) compatible "
            "with bioactive ligand co-immobilization. Requires "
            "tyramine-functionalized polymer as starting material."
        ),
    ),

    # ── K2 Oligoglycine spacer (Gly, GlyGly, Gly4) — hydrophilic spacer.
    # Hilbrig & Freitag 2003 Biotechnol. Adv. 21:561.
    "oligoglycine_spacer": ReagentProfile(
        name="Oligoglycine spacer arm (Gly1-4)",
        cas="556-50-3 (Gly), 556-50-3 (Gly2), 16194-48-2 (Gly4)",
        reaction_type="spacer",
        target_acs=ACSSiteType.EPOXIDE,
        product_acs=ACSSiteType.AMINE_DISTAL,
        k_forward=1e-3,
        E_a=35000.0,
        stoichiometry=1.0,
        hydrolysis_rate=1e-6,
        ph_optimum=9.0,
        temperature_default=298.15,
        time_default=14400.0,
        functional_mode="spacer",
        chemistry_class="epoxide_amine_spacer",
        installed_ligand="oligoglycine_distal_amine",
        spacer_length_angstrom=12.0,    # default = Gly4 ≈ 12 Å
        spacer_activity_multiplier=1.10,
        ph_min=8.0, ph_max=11.0,
        confidence_tier="semi_quantitative",
        calibration_source="Hilbrig & Freitag (2003) Biotechnol. Adv. 21:561",
        notes=(
            "Hydrophilic oligoglycine spacer; minimises matrix-protein "
            "steric and hydrophobic background. Useful in conjunction "
            "with peptide ligands (HWRGWV) where spacer must not "
            "contribute its own binding. Spacer length: Gly1 ≈ 3 Å, "
            "Gly2 ≈ 6 Å, Gly4 ≈ 12 Å (set via spacer_length_angstrom)."
        ),
    ),

    # ── K3 Cystamine disulfide spacer — reducible / cleavable.
    # Egelhoff & Spudich 1991 Methods Enzymol. 196:319.
    "cystamine_disulfide_spacer": ReagentProfile(
        name="Cystamine disulfide spacer (reducible)",
        cas="51-85-4 (cystamine 2HCl)",
        reaction_type="spacer",
        target_acs=ACSSiteType.EPOXIDE,
        product_acs=ACSSiteType.AMINE_DISTAL,
        k_forward=8e-4,
        E_a=35000.0,
        stoichiometry=1.0,
        hydrolysis_rate=1e-6,
        ph_optimum=9.0,
        temperature_default=298.15,
        time_default=14400.0,
        functional_mode="spacer",
        chemistry_class="epoxide_amine_spacer",
        installed_ligand="cystamine_disulfide_distal",
        spacer_length_angstrom=10.0,
        spacer_activity_multiplier=1.05,
        ph_min=8.0, ph_max=11.0,
        confidence_tier="semi_quantitative",
        calibration_source="Egelhoff & Spudich (1991) Methods Enzymol. 196:319",
        notes=(
            "Reducible / cleavable spacer. Cystamine disulfide releases "
            "with 10 mM DTT or TCEP, giving a free thiol on the support "
            "and an analytical capture-and-release workflow. Lower "
            "priority for permanent process resins (the disulfide "
            "limits stability under reducing buffers in process)."
        ),
    ),

    # ── K6 Succinic / glutaric anhydride — distal-amine → distal-carboxyl.
    # Hjertén & Mosbach 1962 Anal. Biochem. 3:109.
    "succinic_anhydride_carboxylation": ReagentProfile(
        name="Succinic anhydride (amine → carboxyl)",
        cas="108-30-5",
        reaction_type="coupling",
        target_acs=ACSSiteType.AMINE_DISTAL,
        product_acs=ACSSiteType.CARBOXYL_DISTAL,
        k_forward=2e-3,
        E_a=30000.0,
        stoichiometry=1.0,
        hydrolysis_rate=1e-4,
        ph_optimum=8.5,
        temperature_default=277.15,    # 4 °C — slow hydrolysis
        time_default=3600.0,
        functional_mode="spacer",
        chemistry_class="acetylation",  # N-acylation
        installed_ligand="succinyl_distal_carboxyl",
        ph_min=7.5, ph_max=9.5,
        confidence_tier="semi_quantitative",
        calibration_source="Hjertén & Mosbach (1962) Anal. Biochem. 3:109",
        hazard_class="moisture_sensitive",
        notes=(
            "N-acylation with succinic anhydride converts a distal "
            "primary amine into a distal carboxyl (terminal -COOH). "
            "Inverts the coupling polarity: after introducing an "
            "amine spacer, succinylate to expose -COOH for EDC/NHS "
            "coupling. Adds nonspecific ion-exchange background."
        ),
    ),

    # ── AC3 Tresyl chloride activation — sulfonate leaving group.
    # Nilsson & Mosbach 1981 Methods Enzymol. 104:56.
    "tresyl_chloride_activation": ReagentProfile(
        name="Tresyl chloride (OH → sulfonate leaving)",
        cas="1648-55-7",
        reaction_type="activation",
        target_acs=ACSSiteType.HYDROXYL,
        product_acs=ACSSiteType.SULFONATE_LEAVING,
        k_forward=2e-3,
        E_a=35000.0,
        stoichiometry=1.0,
        hydrolysis_rate=8e-4,
        ph_optimum=8.0,
        temperature_default=277.15,    # low T to suppress hydrolysis
        time_default=600.0,
        functional_mode="activator",
        chemistry_class="amine_covalent",
        ph_min=7.0, ph_max=9.0,
        temperature_min=273.15, temperature_max=283.15,
        confidence_tier="semi_quantitative",
        calibration_source="Nilsson & Mosbach (1981) Methods Enzymol. 104:56",
        hazard_class="reactive_corrosive",
        notes=(
            "2,2,2-Trifluoroethanesulfonyl chloride activation of "
            "hydroxyls. Couples primary amines (and thiols) directly "
            "via SN2 displacement of the sulfonate. Less common than "
            "CDI but produces a neutral support similar to CNBr without "
            "the cyanate-ester decomposition pathway."
        ),
    ),

    # ── AC6 Pyridyl disulfide activation — reversible thiol capture.
    # Brocklehurst et al. 1973 Biochem. J. 133:573.
    "pyridyl_disulfide_activation": ReagentProfile(
        name="Pyridyl disulfide activation (reversible thiol)",
        cas="2127-03-9 (DTNB family)",
        reaction_type="activation",
        target_acs=ACSSiteType.AMINE_DISTAL,
        product_acs=ACSSiteType.THIOL,
        k_forward=1e-3,
        E_a=30000.0,
        stoichiometry=1.0,
        hydrolysis_rate=1e-7,
        ph_optimum=7.5,
        temperature_default=298.15,
        time_default=3600.0,
        functional_mode="activator",
        chemistry_class="reduction",
        ph_min=6.5, ph_max=8.5,
        confidence_tier="semi_quantitative",
        calibration_source="Brocklehurst et al. (1973) Biochem. J. 133:573",
        notes=(
            "Activated thiol-Sepharose. Pyridyl disulfide on distal "
            "amine spacer captures protein thiols via disulfide exchange "
            "(releases pyridine-2-thione, A343 detectable). Captured "
            "protein released by 10 mM DTT or 5 mM TCEP. Useful for "
            "analytical capture-and-release; pairs with K3 cystamine "
            "spacer."
        ),
    ),

    # ═══════════════════════════════════════════════════════════════════
    # v9.4 Tier-3 reagent additions (SA screening report § 6.3)
    # All Tier-3 entries carry research-mode / non-biotherapeutic flags
    # or lower-priority warnings, per the SA Tier-3 prescription.
    # ═══════════════════════════════════════════════════════════════════

    # ── C6 Aluminum chloride trivalent gelant — NON-BIOTHERAPEUTIC.
    # Picker-Freyer & Schmidt 2004 Pharm. Dev. Technol. 9:35.
    "alcl3_trivalent_gelant": ReagentProfile(
        name="Aluminum chloride (trivalent ionic gelant; research-mode)",
        cas="7446-70-0",
        reaction_type="crosslinking",
        target_acs=ACSSiteType.CARBOXYL,
        product_acs=None,
        k_forward=2e-3,                # very fast — trivalent ion
        E_a=20000.0,
        stoichiometry=3.0,             # 1 Al³⁺ binds 3 carboxylates
        hydrolysis_rate=0.0,
        ph_optimum=4.5,                # narrow window — Al(OH)3 precipitates above
        temperature_default=298.15,
        time_default=600.0,
        functional_mode="crosslinker",
        chemistry_class="metal_chelation",
        regulatory_limit_ppm=0.0,       # 0 = explicit "do not use for biotherapeutic"
        ph_min=3.5, ph_max=5.5,
        confidence_tier="ranking_only",
        calibration_source="Picker-Freyer & Schmidt (2004) Pharm. Dev. Technol. 9:35",
        hazard_class="non_biotherapeutic_residual_aluminum",
        notes=(
            "TRIVALENT IONIC GELANT — NOT FOR BIOTHERAPEUTIC RESINS. "
            "Residual aluminum is regulated by FDA/EP; Al³⁺ induces "
            "proteinopathy concerns. Use only for research / non-"
            "biotherapeutic applications. Gels gellan and other anionic "
            "polysaccharides via stronger triple-bridging than Ca²⁺. "
            "Narrow pH window (3.5-5.5); above this, Al(OH)3 precipitates. "
            "Will be rejected at G3 audit gate for biotherapeutic targets."
        ),
    ),

    # ── C8 Borax / borate — reversible cis-diol crosslinking.
    # Pezron et al. 1988 Macromolecules 21:1126.
    "borax_reversible_crosslinking": ReagentProfile(
        name="Borax (reversible cis-diol crosslinker; research/temp porogen)",
        cas="1303-96-4",
        reaction_type="crosslinking",
        target_acs=ACSSiteType.CIS_DIOL,
        product_acs=None,
        k_forward=5e-2,                # very fast
        E_a=15000.0,
        stoichiometry=0.5,             # 1 borate bridges 2 cis-diols
        hydrolysis_rate=1e-2,           # very high — equilibrium-limited
        ph_optimum=9.5,
        temperature_default=298.15,
        time_default=300.0,             # 5 min — equilibrium reached fast
        functional_mode="crosslinker",
        chemistry_class="reduction",   # placeholder — reversible borate-diol
        ph_min=8.5, ph_max=11.0,
        confidence_tier="ranking_only",
        calibration_source="Pezron et al. (1988) Macromolecules 21:1126",
        hazard_class="reversible_not_for_pressure_chromatography",
        notes=(
            "REVERSIBLE crosslinker — UNSUITABLE for pressure "
            "chromatography. Borate-cis-diol equilibrium is pH-dependent "
            "(forms at pH > 8.5; dissociates at acidic pH or with "
            "competing diols/sugars). Useful as TEMPORARY POROGEN or "
            "model network during synthesis, but the network MUST be "
            "subsequently hardened with a covalent crosslinker (BDDE, "
            "ECH, etc.) before any flow-through application."
        ),
    ),

    # ── C10 Glyoxal — small dialdehyde (lower priority vs glutaraldehyde).
    # Lee et al. 2011 Carbohydr. Polym. 84:571.
    "glyoxal_dialdehyde": ReagentProfile(
        name="Glyoxal (small dialdehyde; lower priority)",
        cas="107-22-2",
        reaction_type="crosslinking",
        target_acs=ACSSiteType.AMINE_PRIMARY,
        product_acs=None,
        # Glutaraldehyde k≈1e-5; glyoxal is ~3-5× slower because of its
        # short tether (–CHO–CHO has no methylene spacer) — Schiff-base
        # equilibria sit further left without the longer linker.
        k_forward=3e-6,
        E_a=42000.0,
        stoichiometry=0.5,             # 1 glyoxal bridges 2 amines
        hydrolysis_rate=5e-4,           # higher than glutaraldehyde
        ph_optimum=7.0,
        temperature_default=298.15,
        time_default=7200.0,
        functional_mode="crosslinker",
        chemistry_class="aldehyde_amine",
        ph_min=6.0, ph_max=8.5,
        confidence_tier="ranking_only",
        calibration_source="Lee et al. (2011) Carbohydr. Polym. 84:571",
        hazard_class="reactive_short_tether_unstable",
        notes=(
            "Lower-priority alternative to glutaraldehyde. Very short "
            "tether (–CHO–CHO) gives less stable Schiff-base bridges; "
            "residual aldehyde control is harder. Recommended ONLY when "
            "followed by reduction (NaBH4 / NaBH3CN) to lock the network. "
            "For most chitosan-amine crosslinking, glutaraldehyde or "
            "genipin is preferred."
        ),
    ),

    # ── L7 Calmodulin — Ca²⁺-dependent CBP/TAP-tag affinity.
    # Stofko-Hahn et al. 1992 FEBS Lett. 302:274.
    "calmodulin_cbp_tap_coupling": ReagentProfile(
        name="Calmodulin (CBP/TAP-tag, Ca²⁺-dependent)",
        cas="9070-71-1",
        reaction_type="coupling",
        target_acs=ACSSiteType.EPOXIDE,
        product_acs=None,
        k_forward=4e-4,
        E_a=35000.0,
        stoichiometry=1.0,
        hydrolysis_rate=1e-7,
        ph_optimum=8.5,
        temperature_default=277.15,
        time_default=14400.0,
        functional_mode="affinity_ligand",
        chemistry_class="epoxide_amine",
        installed_ligand="calmodulin",
        is_macromolecule=True,
        ligand_mw=16700.0,
        activity_retention=0.65,        # Ca²⁺-dependent activity loss on coupling
        activity_retention_uncertainty=0.15,
        binding_model_hint="affinity",
        ph_min=7.0, ph_max=10.0,
        confidence_tier="ranking_only",
        calibration_source="Stofko-Hahn et al. (1992) FEBS Lett. 302:274",
        notes=(
            "Calmodulin (CaM) ligand for CBP-tagged or TAP-tagged "
            "fusion proteins. Ca²⁺-dependent: binds in presence of "
            "≥ 0.1 mM Ca²⁺; eluted by EGTA/EDTA chelation. Mostly "
            "research / proteomics use (TAP tag); limited industrial "
            "bioprocess relevance. M2/M3 must surface CIP sensitivity — "
            "harsh-base regeneration denatures CaM."
        ),
    ),
}

