"""Module 2 functionalization orchestrator.

Phase B+: Full 5-workflow Module 2 with backend validation.
Architecture: docs/18_m2_expansion_final_plan.md.

Provides:
- FunctionalMicrosphere: complete description of a functionalized microsphere
- FunctionalMediaContract: stable M2->M3 bridge with ligand density mapping
- ModificationOrchestrator: sequential execution with ACS tracking + validation
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .acs import ACSSiteType, ACSProfile, initialize_acs_from_m1
from .modification_steps import (
    ModificationResult,
    ModificationStep,
    ModificationStepType,
    solve_modification_step,
)
from .reagent_profiles import REAGENT_PROFILES
from .surface_area import AccessibleSurfaceModel

from typing import Optional

from ..datatypes import ModelEvidenceTier, ModelManifest

if TYPE_CHECKING:
    from dpsim.datatypes import M1ExportContract

logger = logging.getLogger(__name__)


# ─── ProteinPretreatmentState (v5.9.2) ───────────────────────────────

@dataclass
class ProteinPretreatmentState:
    """State of protein after disulfide reduction pretreatment."""
    protein_key: str = ""
    free_thiol_fraction: float = 0.0
    activity_after_reduction: float = 1.0
    reductant_used: str = ""
    excess_reductant_removed: bool = False
    time_since_reduction_s: float = 0.0
    warnings: list[str] = field(default_factory=list)


# ─── FunctionalMicrosphere ────────────────────────────────────────────

@dataclass
class FunctionalMicrosphere:
    """Complete description of a functionalized microsphere.

    Holds the M1 contract, surface model, current ACS state, and the
    full modification history with provenance.

    Attributes:
        m1_contract: Source Module 1 export contract.
        surface_model: Computed accessible surface area model.
        acs_profiles: Current ACS inventory (mutated by modification steps).
        modification_history: Ordered list of completed modification results.
        G_DN_updated: Updated double-network shear modulus [Pa] after
            secondary crosslinking.
        E_star_updated: Updated effective Young's modulus [Pa].
    """
    m1_contract: M1ExportContract
    surface_model: AccessibleSurfaceModel
    acs_profiles: dict[ACSSiteType, ACSProfile]
    modification_history: list[ModificationResult] = field(default_factory=list)
    G_DN_updated: float = 0.0
    E_star_updated: float = 0.0
    # v5.9.2: Protein pretreatment state (set by PROTEIN_PRETREATMENT steps)
    pretreatment_state: ProteinPretreatmentState = field(default_factory=ProteinPretreatmentState)
    # v5.9.4: Residual reagent concentrations after washing
    residual_concentrations: dict = field(default_factory=dict)
    # v6.1 (Node 4): composite manifest summarising all step manifests; the
    # weakest tier across the modification history wins, mirroring how
    # RunReport.compute_min_tier() rolls up M1 levels.
    model_manifest: Optional[ModelManifest] = None

    def validate(self) -> list[str]:
        """Validate ACS conservation across all profiles.

        Returns:
            List of violation messages (empty = all valid).
        """
        errors: list[str] = []
        for profile in self.acs_profiles.values():
            errors.extend(profile.validate())
        return errors


# ─── FunctionalMediaContract (M2→M3 bridge, audit F7) ───────────────

@dataclass
class FunctionalMediaContract:
    """Stable interface between Module 2 and Module 3 for process simulation.

    Maps functional ligand density to estimated chromatographic capacity.
    M3 should consume this contract rather than relying on default isotherm
    parameters when ligand data is available.
    """
    # ── Pass-through from M1 ──
    bead_d50: float = 0.0              # [m]
    porosity: float = 0.0              # [-]
    pore_size_mean: float = 0.0        # [m]

    # ── From M2 ──
    ligand_type: str = "none"          # "iex_anion", "iex_cation", "affinity",
                                       # "imac", "hic", "none"
    installed_ligand: str = ""         # e.g., "DEAE", "Protein A", "Phenyl"
    functional_ligand_density: float = 0.0  # [mol/m^2]
    total_coupled_density: float = 0.0      # [mol/m^2]
    charge_density: float = 0.0        # [mol/m^2] for IEX
    active_protein_density: float = 0.0  # [mol/m^2] for affinity

    # ── Mechanical (pass-through) ──
    G_DN_updated: float = 0.0          # [Pa]
    E_star_updated: float = 0.0        # [Pa]

    # ── Derived M3 parameter estimates ──
    estimated_q_max: float = 0.0       # [mol/m^3 bed] mapped from ligand density
    q_max_confidence: str = "not_mapped"  # "mapped_estimated" | "not_mapped"
    q_max_mapping_notes: str = ""

    # ── Area basis (audit F13) ──
    ligand_density_area_basis: str = ""  # "reagent_accessible", "ligand_accessible", "external"
    q_max_area_basis_note: str = ""      # Human-readable note on q_max derivation

    # ── Binding model hint for M3 (audit F15) ──
    binding_model_hint: str = ""         # Passed from reagent profile for M3 routing

    # ── v5.9.0 FMC v2 fields ──
    reagent_accessible_area_per_bed_volume: float = 0.0  # [m2/m3 bed]
    ligand_accessible_area_per_bed_volume: float = 0.0   # [m2/m3 bed]
    capacity_area_basis: str = ""        # "reagent_accessible" or "ligand_accessible"
    activity_retention_uncertainty: float = 0.0  # +/- on activity_retention
    activity_retention: float = 0.0              # measured or inferred retained activity fraction
    ligand_leaching_fraction: float = 0.0        # measured ligand loss fraction after wash/storage
    free_protein_wash_fraction: float = 0.0      # measured uncoupled protein fraction in wash
    q_max_lower: float = 0.0            # [mol/m3 bed] lower bound
    q_max_upper: float = 0.0            # [mol/m3 bed] upper bound
    m3_support_level: str = "not_mapped"  # "mapped_quantitative", "mapped_estimated",
                                          # "not_mapped", "requires_user_calibration"
    final_ligand_profile_key: str = ""   # Key of the last coupling reagent profile
    process_state_requirements: str = "" # "salt_concentration", "imidazole", ""
    residual_reagent_concentrations: dict[str, float] = field(default_factory=dict)
    residual_reagent_warnings: list[str] = field(default_factory=list)

    # ── Trust ──
    warnings: list[str] = field(default_factory=list)
    # v0.5.0 (D2): the legacy ``confidence_tier: str`` side-channel was removed
    # from the public FMC surface. The typed-enum chain
    # (``model_manifest.evidence_tier``) is now the single source of truth for
    # FMC evidence tier. Downstream consumers should read
    # ``fmc.model_manifest.evidence_tier`` (and use ``.value`` only for
    # human-readable display).
    model_manifest: Optional[ModelManifest] = None

    # v0.6.1 (F2) — typed Quantity accessors. Underlying float fields above
    # remain authoritative for arithmetic; these expose unit-tagged handles.
    # Consumers that want unit-safe reads / unit conversions should use the
    # _q accessors; bare-float reads continue to work for arithmetic and
    # legacy callers.

    @property
    def bead_d50_q(self):
        from dpsim.core.quantities import Quantity
        return Quantity(float(self.bead_d50), "m", source="M1.M2.contract")

    @property
    def porosity_q(self):
        from dpsim.core.quantities import Quantity
        return Quantity(float(self.porosity), "1", source="M1.M2.contract")

    @property
    def pore_size_mean_q(self):
        from dpsim.core.quantities import Quantity
        return Quantity(float(self.pore_size_mean), "m", source="M1.M2.contract")

    @property
    def functional_ligand_density_q(self):
        from dpsim.core.quantities import Quantity
        return Quantity(
            float(self.functional_ligand_density), "mol/m2",
            source="M2.functional_media_contract",
        )

    @property
    def estimated_q_max_q(self):
        from dpsim.core.quantities import Quantity
        return Quantity(
            float(self.estimated_q_max), "mol/m3",
            source="M2.functional_media_contract",
        )

    @property
    def activity_retention_q(self):
        from dpsim.core.quantities import Quantity
        return Quantity(
            float(self.activity_retention), "1",
            source="M2.functional_media_contract",
            note="Coupled-protein activity retention fraction.",
        )

    @property
    def ligand_leaching_fraction_q(self):
        from dpsim.core.quantities import Quantity
        return Quantity(
            float(self.ligand_leaching_fraction), "1",
            source="M2.functional_media_contract",
        )

    def validate_units(self) -> list[str]:
        """Node 10 (F11): boundary-level unit/range sanity checks for M2->M3.

        Same intent as M1ExportContract.validate_units: catch silent unit
        mismatches at the contract boundary. Returns a list of violations
        (empty = pass).
        """
        violations: list[str] = []

        # Geometry inherited from M1.
        if self.bead_d50 != 0.0 and not (1e-7 <= self.bead_d50 <= 1e-2):
            violations.append(
                f"bead_d50={self.bead_d50:g} m outside [1e-7, 1e-2]; wrong unit?"
            )
        if not (0.0 <= self.porosity <= 1.0):
            violations.append(
                f"porosity={self.porosity:g} outside [0, 1]."
            )
        if self.pore_size_mean != 0.0 and not (1e-9 <= self.pore_size_mean <= 1e-5):
            violations.append(
                f"pore_size_mean={self.pore_size_mean:g} m outside [1e-9, 1e-5]."
            )

        # Ligand densities are mol/m^2. Realistic values 1e-7 to 1e-3 mol/m^2.
        for name, val in (
            ("functional_ligand_density", self.functional_ligand_density),
            ("total_coupled_density", self.total_coupled_density),
            ("charge_density", self.charge_density),
            ("active_protein_density", self.active_protein_density),
        ):
            if val < 0.0:
                violations.append(f"{name}={val:g} mol/m^2 must be non-negative.")
            elif val > 1.0:
                violations.append(
                    f"{name}={val:g} mol/m^2 exceeds 1; mol/m^2 vs mol/m^3 confusion?"
                )

        # estimated_q_max is mol/m^3 of bed. Realistic capacities are
        # 0-2000 mol/m^3 for IEX, 0-100 for affinity. Block obviously wrong.
        if self.estimated_q_max < 0.0:
            violations.append(
                f"estimated_q_max={self.estimated_q_max:g} mol/m^3 must be non-negative."
            )
        if self.estimated_q_max > 1e5:
            violations.append(
                f"estimated_q_max={self.estimated_q_max:g} mol/m^3 exceeds 1e5; "
                "wrong unit?"
            )
        if self.q_max_lower > self.q_max_upper and self.q_max_upper > 0.0:
            violations.append(
                f"q_max_lower={self.q_max_lower:g} > q_max_upper={self.q_max_upper:g}; "
                "uncertainty bounds inverted."
            )

        # Mechanical inherited from M1 (Pa).
        if self.G_DN_updated != 0.0 and not (1.0 <= self.G_DN_updated <= 1e9):
            violations.append(
                f"G_DN_updated={self.G_DN_updated:g} Pa outside [1, 1e9]."
            )
        if self.E_star_updated != 0.0 and not (1.0 <= self.E_star_updated <= 1e10):
            violations.append(
                f"E_star_updated={self.E_star_updated:g} Pa outside [1, 1e10]."
            )

        if not (0.0 <= self.activity_retention_uncertainty <= 1.0):
            violations.append(
                f"activity_retention_uncertainty={self.activity_retention_uncertainty:g} "
                "outside [0, 1]."
            )
        for name, value in (
            ("activity_retention", self.activity_retention),
            ("ligand_leaching_fraction", self.ligand_leaching_fraction),
            ("free_protein_wash_fraction", self.free_protein_wash_fraction),
        ):
            if not (0.0 <= value <= 1.0):
                violations.append(f"{name}={value:g} outside [0, 1].")
        for key, value in self.residual_reagent_concentrations.items():
            if value < 0.0:
                violations.append(
                    f"residual_reagent_concentrations[{key!r}]={value:g} "
                    "mol/m^3 must be non-negative."
                )

        return violations


# ─── v0.5.0 ACS Converter sequence FSM (in-module helper) ──────────────────


# Mirrors the recipe-level G6 in core/recipe_validation.py; see that file's
# _g6_acs_converter_sequence for the canonical implementation. This helper
# accepts a ModificationStep list directly, useful for unit tests and any
# M2-internal caller that does not go through ProcessRecipe.
_ARM_DISTAL_REAGENT_KEYS = frozenset({"pyridyl_disulfide_activation"})
_AMINE_ARM_REAGENT_KEYS = frozenset({
    "eda_spacer_arm", "dadpa_spacer_arm", "dah_spacer_arm",
    "aha_spacer", "oligoglycine_spacer", "cystamine_disulfide_spacer",
})
_ALDEHYDE_CONVERTER_KEYS = frozenset({
    "glyoxyl_chained_activation", "periodate_oxidation",
})
_REDUCTIVE_QUENCH_KEYS = frozenset({"nabh4_quench"})


def validate_sequence(
    steps: list[ModificationStep],
    *,
    polymer_family: str = "",
    cip_required: bool = False,
) -> list[str]:
    """Run the ACS-Converter sequence FSM over a list of ModificationStep.

    Returns a list of violation messages (empty = valid). Mirrors the
    recipe-level G6 guardrail without depending on ProcessRecipe.

    Args:
        steps: ordered list of M2 modification steps.
        polymer_family: lowercase PolymerFamily.value for native-amine check.
        cip_required: when True, aldehyde converters require NaBH4 reduction.
    """
    violations: list[str] = []
    if not steps:
        return violations

    _phase_rank = {
        ModificationStepType.ACTIVATION: 1,
        ModificationStepType.ACS_CONVERSION: 1,
        ModificationStepType.ARM_ACTIVATION: 2,
        ModificationStepType.SPACER_ARM: 2,
        ModificationStepType.LIGAND_COUPLING: 3,
        ModificationStepType.PROTEIN_COUPLING: 3,
        ModificationStepType.METAL_CHARGING: 4,
    }

    # Ordering check.
    last_rank = 0
    for step in steps:
        rank = _phase_rank.get(step.step_type)
        if rank is None:
            continue
        if rank < last_rank:
            violations.append(
                f"Step {step.reagent_key!r} ({step.step_type.value}) follows "
                f"a later-phase step. Required: ACS_CONVERSION → SPACER_ARM/"
                f"ARM_ACTIVATION → LIGAND_COUPLING → METAL_CHARGING."
            )
        last_rank = max(last_rank, rank)

    # Arm-distal precondition.
    _native_amine_families = {
        "agarose_chitosan", "chitosan", "alginate_chitosan", "pectin_chitosan",
    }
    has_native_amine = polymer_family.lower() in _native_amine_families
    for idx, step in enumerate(steps):
        if step.reagent_key not in _ARM_DISTAL_REAGENT_KEYS:
            continue
        amine_arm_before = any(
            j_step.step_type == ModificationStepType.SPACER_ARM
            and j_step.reagent_key in _AMINE_ARM_REAGENT_KEYS
            for j_step in steps[:idx]
        )
        if not amine_arm_before and not has_native_amine:
            violations.append(
                f"Step {step.reagent_key!r}: arm-distal activator requires "
                f"a prior SPACER_ARM step with an amine spacer or a native-"
                f"amine polymer family. Family={polymer_family!r}."
            )

    # Metal-charge precondition.
    coupled_before = False
    for step in steps:
        if step.step_type in (ModificationStepType.LIGAND_COUPLING,
                              ModificationStepType.PROTEIN_COUPLING):
            coupled_before = True
        elif step.step_type == ModificationStepType.METAL_CHARGING and not coupled_before:
            violations.append(
                f"Step {step.reagent_key!r}: METAL_CHARGING requires a prior "
                "LIGAND_COUPLING that installed an NTA or IDA chelator."
            )

    # CIP reductive lock-in.
    if cip_required:
        for idx, step in enumerate(steps):
            if step.reagent_key not in _ALDEHYDE_CONVERTER_KEYS:
                continue
            has_reductive_quench = any(
                j_step.reagent_key in _REDUCTIVE_QUENCH_KEYS
                for j_step in steps[idx + 1:]
            )
            if not has_reductive_quench:
                violations.append(
                    f"Step {step.reagent_key!r}: aldehyde converter requires "
                    f"a downstream NaBH4 quench (cip_required=True)."
                )

    return violations


def build_functional_media_contract(
    microsphere: FunctionalMicrosphere,
) -> FunctionalMediaContract:
    """Build M2→M3 bridge contract from a functionalized microsphere.

    Scans modification history to identify the installed ligand type and
    computes functional ligand density for M3 capacity estimation.

    Args:
        microsphere: Completed FunctionalMicrosphere from orchestrator.

    Returns:
        FunctionalMediaContract with ligand mapping.
    """
    contract = microsphere.m1_contract
    surface = microsphere.surface_model
    warnings: list[str] = []

    # Find the last coupling step to determine ligand type
    ligand_type = "none"
    installed_ligand = ""
    _last_coupling_rp = None
    functional_density = 0.0
    coupled_density = 0.0
    confidence = "not_mapped"
    q_max_est = 0.0
    q_max_notes = ""

    for mr in microsphere.modification_history:
        step = mr.step
        if step.step_type in (ModificationStepType.LIGAND_COUPLING,
                              ModificationStepType.PROTEIN_COUPLING):
            rp = REAGENT_PROFILES.get(step.reagent_key)
            if rp is not None:
                installed_ligand = getattr(rp, 'installed_ligand', step.reagent_key)
                fm = getattr(rp, 'functional_mode', '')

                # Map functional_mode to ligand_type
                # Audit F14: use charge_type for IEX instead of string heuristic
                _ct = getattr(rp, 'charge_type', '')
                _mode_map = {
                    "iex_ligand": "iex_anion" if _ct == "anion" else (
                        "iex_cation" if _ct == "cation" else "iex_anion"),
                    "affinity_ligand": "affinity",
                    "imac_chelator": "imac",
                    "hic_ligand": "hic",
                    "gst_affinity": "gst_affinity",
                    "biotin_affinity": "biotin_affinity",
                    "heparin_affinity": "heparin_affinity",
                    # v9.2 specialised M3 ligand_types (Q-015 resolution).
                    # Each mode routes to its own ligand_type branch in
                    # the q_max-computation block below.
                    "dye_pseudo_affinity": "dye_pseudo_affinity",  # B3 — Cibacron Blue
                    "mixed_mode_hcic": "mixed_mode_hcic",          # B4 — MEP
                    "thiophilic": "thiophilic",                    # B4 — T-Sorb
                    "boronate": "boronate",                        # B10 — boronate
                    # v9.4 follow-on specialised dispatches for the
                    # remaining Tier-2 specialty modes.
                    "peptide_affinity": "peptide_affinity",  # HWRGWV / Protein-A mimetic
                    "oligonucleotide": "oligonucleotide",    # sequence-specific DNA ligand
                    "material_as_ligand": "material_as_ligand",  # amylose-MBP / chitin-CBD
                    # `click_handle` is an intermediate (not a final ligand);
                    # map to "none" so M3 ignores until the click ligand
                    # itself is coupled in a subsequent step.
                    "click_handle": "none",              # B7 — CuAAC/SPAAC
                }
                ligand_type = _mode_map.get(fm, "none")
                _last_coupling_rp = rp  # carry for density area selection

    # Compute densities from ACS profiles (audit F13: track area basis)
    _is_macro = getattr(_last_coupling_rp, 'is_macromolecule', False) if _last_coupling_rp is not None else False
    _area_basis = "reagent_accessible"
    for _st, profile in microsphere.acs_profiles.items():
        if profile.ligand_coupled_sites > 0:
            if _is_macro and surface.ligand_accessible_area > 0:
                area = surface.ligand_accessible_area
                _area_basis = "ligand_accessible"
            else:
                area = surface.reagent_accessible_area if surface.reagent_accessible_area > 0 else surface.ligand_accessible_area
                _area_basis = "reagent_accessible" if surface.reagent_accessible_area > 0 else "ligand_accessible"
            if area > 0:
                coupled_density = profile.ligand_coupled_sites / area
                functional_density = profile.ligand_functional_sites / area

    # ── v5.9.0: Compute accessible area per bed volume ──
    d_p = contract.bead_d50
    eps_b = 0.38  # default bed porosity
    _binding_hint = getattr(_last_coupling_rp, 'binding_model_hint', '') if _last_coupling_rp else ''
    _m3_support = getattr(_last_coupling_rp, 'm3_support_level', 'not_mapped') if _last_coupling_rp else 'not_mapped'
    _final_key = getattr(_last_coupling_rp, 'name', '') if _last_coupling_rp else ''
    _act_unc = getattr(_last_coupling_rp, 'activity_retention_uncertainty', 0.0) if _last_coupling_rp else 0.0

    # Accessible area per bed volume (v5.9.0 WN-0b)
    _reagent_a_v = 0.0
    _ligand_a_v = 0.0
    if d_p > 0:
        import math as _math_fmc
        V_particle = (4.0 / 3.0) * _math_fmc.pi * (d_p / 2.0) ** 3
        if V_particle > 0:
            particles_per_bed_vol = (1.0 - eps_b) / V_particle
            _reagent_a_v = surface.reagent_accessible_area * particles_per_bed_vol
            _ligand_a_v = surface.ligand_accessible_area * particles_per_bed_vol

    # Choose appropriate a_v for q_max based on molecule size
    if _is_macro:
        a_v_for_qmax = _ligand_a_v
        _cap_basis = "ligand_accessible"
    else:
        a_v_for_qmax = _reagent_a_v if _reagent_a_v > 0 else _ligand_a_v
        _cap_basis = "reagent_accessible" if _reagent_a_v > 0 else "ligand_accessible"

    _q_max_area_note = f"Area basis: {_area_basis}. Bed a_v({_cap_basis}): {a_v_for_qmax:.0f} m2/m3."

    if d_p > 0 and functional_density > 0 and a_v_for_qmax > 0:

        if ligand_type in ("iex_anion", "iex_cation"):
            q_max_est = functional_density * a_v_for_qmax
            confidence = "mapped_estimated"
            q_max_notes = (
                f"IEX: q_max = ligand_density * a_v = {q_max_est:.2f} mol/m^3. "
                f"a_v = {a_v_for_qmax:.0f} m^2/m^3 ({_cap_basis}). {_q_max_area_note} "
                f"Bed porosity = {eps_b:.2f}."
            )
        elif ligand_type == "affinity":
            binding_stoich = 2.0  # Protein A/G: ~2 IgG per ligand
            q_max_est = functional_density * a_v_for_qmax * binding_stoich
            confidence = "mapped_estimated"
            q_max_notes = (
                f"Affinity (Fc): q_max = density * a_v * stoich({binding_stoich:.0f}). "
                f"{_q_max_area_note} Ranking only."
            )
        elif ligand_type == "imac":
            binding_stoich = 1.0
            _mi = getattr(_last_coupling_rp, 'metal_ion', 'Ni2+') if _last_coupling_rp else 'Ni2+'
            _mlf = getattr(_last_coupling_rp, 'metal_loaded_fraction', 1.0) if _last_coupling_rp else 1.0
            q_max_est = functional_density * a_v_for_qmax * binding_stoich * _mlf
            confidence = "mapped_estimated"
            q_max_notes = (
                f"IMAC: q_max = density * a_v * stoich * metal_frac. "
                f"Assumes fully {_mi}-loaded (frac={_mlf:.0%}), "
                f"no leaching, no competing chelators. {_q_max_area_note}"
            )
        elif ligand_type == "gst_affinity":
            binding_stoich = 1.0  # 1 GST per glutathione
            q_max_est = functional_density * a_v_for_qmax * binding_stoich
            confidence = "mapped_estimated"
            q_max_notes = (
                f"GST affinity: 1:1 GST:glutathione. {_q_max_area_note}"
            )
        elif ligand_type == "biotin_affinity":
            binding_stoich = 2.5  # Audit F7: capped from theoretical 4
            q_max_est = functional_density * a_v_for_qmax * binding_stoich
            confidence = "mapped_estimated"
            q_max_notes = (
                f"Biotin affinity: stoich={binding_stoich} (capped from theoretical 4 "
                f"due to steric occlusion). Near-irreversible binding. {_q_max_area_note}"
            )
        elif ligand_type == "heparin_affinity":
            binding_stoich = 1.0  # approximate, highly target-dependent
            q_max_est = functional_density * a_v_for_qmax * binding_stoich
            confidence = "mapped_estimated"
            q_max_notes = (
                f"Heparin affinity: stoich~1 (approximate, target-dependent). "
                f"Mixed affinity + cation exchange. {_q_max_area_note}"
            )
        elif ligand_type == "hic":
            q_max_notes = (
                f"HIC: q_max not mappable from ligand density alone. "
                f"Requires salt-dependent adsorption isotherm. {_q_max_area_note}"
            )
        elif ligand_type == "dye_pseudo_affinity":
            # Q-015: B3 dye-pseudo-affinity (Cibacron Blue F3GA, Procion Red).
            # Stoichiometry varies by target (1 albumin per dye; ~1 NAD-
            # binding enzyme per dye; some oligomeric proteins bind 2+).
            # Use 1.0 as a conservative ranking estimate.
            binding_stoich = 1.0
            q_max_est = functional_density * a_v_for_qmax * binding_stoich
            confidence = "ranking_only"  # large target-dependent variance
            q_max_notes = (
                f"Dye-pseudo-affinity: q_max = density × a_v × stoich(~1.0). "
                f"Target-dependent (NAD-binding enzymes ~1, albumin ~1, "
                f"some oligomers >1). RANKING ONLY — calibrate with "
                f"actual target. Dye leakage warning: monitor A610 in "
                f"effluent. {_q_max_area_note}"
            )
        elif ligand_type == "mixed_mode_hcic":
            # Q-015: B4 MEP HCIC pH-switchable IgG capture.
            # Stoichiometry: ~1 IgG per MEP at saturating loading
            # (Burton & Harding 1998); pH-dependent.
            binding_stoich = 1.0
            q_max_est = functional_density * a_v_for_qmax * binding_stoich
            confidence = "ranking_only"
            q_max_notes = (
                f"Mixed-mode HCIC (MEP): q_max = density × stoich(1.0 IgG/ligand). "
                f"pH-switchable: loads at pH 7 (uncharged pyridine, hydrophobic "
                f"binding); elutes at pH 4 (cationic pyridinium repels cationic "
                f"IgG). Process state: requires pH gradient (no salt needed). "
                f"{_q_max_area_note}"
            )
        elif ligand_type == "thiophilic":
            # Q-015: B4 thiophilic salt-promoted IgG capture.
            # Stoichiometry: ~1 IgG per ligand pair (thiophilic binding
            # involves cooperative interaction of multiple sulfone groups
            # with the IgG Fc); use 1.0/(2 ligands) ≈ 0.5 effective stoich.
            binding_stoich = 0.5
            q_max_est = functional_density * a_v_for_qmax * binding_stoich
            confidence = "ranking_only"
            q_max_notes = (
                f"Thiophilic (T-Sorb): q_max = density × stoich(~0.5 IgG/ligand). "
                f"Salt-promoted electron-donor/acceptor binding (distinct from "
                f"HIC). Loads at high salt (0.5–1 M K2SO4); elutes at low salt. "
                f"Process state: requires salt gradient (descending). "
                f"{_q_max_area_note}"
            )
        elif ligand_type == "boronate":
            # Q-015: B10 boronate cis-diol affinity.
            # Stoichiometry: ~1 cis-diol pair per boronate ligand at pH > pKa.
            # For glycoproteins with multiple cis-diol sites, multiple
            # boronates can bind one molecule, but for q_max accounting
            # use 1:1 (one binding event per ligand site).
            binding_stoich = 1.0
            q_max_est = functional_density * a_v_for_qmax * binding_stoich
            confidence = "ranking_only"
            q_max_notes = (
                f"Boronate cis-diol: q_max = density × stoich(1.0). "
                f"pH-switchable: binds above boronate pKa (~8.5); elutes "
                f"by sorbitol/fructose competitor or pH < pKa. Targets "
                f"glycoproteins, glycated proteins (HbA1c), nucleotides. "
                f"Process state: requires pH 8.5 + sorbitol/fructose elution. "
                f"{_q_max_area_note}"
            )
        elif ligand_type == "peptide_affinity":
            # v9.4 follow-on: Protein-A-mimetic peptide ligands (HWRGWV
            # class). Stoichiometry: ~1 IgG per peptide ligand at saturating
            # loading (Yang 2009). pH-switchable like Protein-A: loads at
            # neutral pH, elutes at low pH (acetate pH 3-4).
            binding_stoich = 1.0
            q_max_est = functional_density * a_v_for_qmax * binding_stoich
            confidence = "ranking_only"
            q_max_notes = (
                f"Peptide affinity (HWRGWV-class): q_max = density × "
                f"stoich(1.0 IgG/peptide). Protein-A-mimetic; loads at "
                f"pH 7-8, elutes at pH 3-4 (acetate). Cheaper, lower-"
                f"leachable than Protein A; sterilisation-friendly. "
                f"Process state: requires acidic-elution buffer. "
                f"{_q_max_area_note}"
            )
        elif ligand_type == "oligonucleotide":
            # v9.4 follow-on: sequence-specific DNA affinity. Stoichiometry
            # is target-dependent (1:1 for simple TF-DNA recognition;
            # higher for oligomeric DNA-binding complexes). Conservative
            # 1.0 binding site per oligo; ranking_only confidence
            # acknowledges the target-dependent variance.
            binding_stoich = 1.0
            q_max_est = functional_density * a_v_for_qmax * binding_stoich
            confidence = "ranking_only"
            q_max_notes = (
                f"Sequence-specific DNA: q_max = density × stoich(1.0 "
                f"target/oligo). Target-dependent variance — single "
                f"transcription factors ~1:1, oligomeric complexes "
                f"higher. Eluted by salt gradient or competing oligo-"
                f"DNA. Nuclease-stability warning for crude lysate. "
                f"Process state: requires salt gradient (descending). "
                f"{_q_max_area_note}"
            )
        elif ligand_type == "material_as_ligand":
            # v9.4 follow-on: B9 material-as-ligand pattern (amylose-MBP,
            # chitin-CBD). The polymer matrix IS the affinity ligand; no
            # coupled discrete ligand exists. Stoichiometry is per binding
            # site on the polymer surface — assume 1:1 fusion-protein per
            # accessible binding site (Kellermann 1982 for amylose-MBP).
            # Functional density approximates the matrix's intrinsic
            # binding-site density rather than a coupled-ligand density.
            binding_stoich = 1.0
            q_max_est = functional_density * a_v_for_qmax * binding_stoich
            confidence = "ranking_only"
            q_max_notes = (
                f"Material-as-ligand (amylose-MBP / chitin-CBD): q_max = "
                f"matrix_binding_site_density × a_v × stoich(1.0). The "
                f"polymer matrix itself is the affinity ligand; no coupled "
                f"ligand exists. Eluted by tag-specific competitor "
                f"(10 mM maltose for amylose; thiol or pH/T for chitin "
                f"CBD-intein). Process state: requires tag-specific "
                f"eluent. {_q_max_area_note}"
            )
        else:
            q_max_notes = f"Ligand type '{ligand_type}' — q_max mapping not implemented."
            if ligand_type != "none":
                warnings.append(q_max_notes)
    else:
        if ligand_type != "none" and functional_density > 0:
            q_max_notes = "q_max not computed: bead diameter is zero."
        elif ligand_type != "none":
            q_max_notes = "q_max not computed: no functional ligand density."

    # Determine confidence tier
    _ranking_types = {
        "affinity", "biotin_affinity", "heparin_affinity",
        # v9.2 specialised modes (Q-015) carry RANKING_ONLY confidence
        # because target-dependent stoichiometry / pH-switchable binding
        # / salt-dependent adsorption all introduce variance that simple
        # ligand-density × stoich product does not capture.
        "dye_pseudo_affinity", "mixed_mode_hcic", "thiophilic", "boronate",
        # v9.4 follow-on specialised modes — same ranking_only rationale
        # (target-dependent peptide/oligo/material binding variance).
        "peptide_affinity", "oligonucleotide", "material_as_ligand",
    }
    _conf_tier = "ranking_only" if ligand_type in _ranking_types else "semi_quantitative"

    # Compute q_max uncertainty bounds from activity_retention_uncertainty
    _q_lower = 0.0
    _q_upper = 0.0
    if q_max_est > 0 and _act_unc > 0:
        # q_max scales linearly with activity_retention
        _act_ret = getattr(_last_coupling_rp, 'activity_retention', 1.0) if _last_coupling_rp else 1.0
        if _act_ret > 0:
            _q_lower = q_max_est * max(_act_ret - _act_unc, 0.0) / _act_ret
            _q_upper = q_max_est * min(_act_ret + _act_unc, 1.0) / _act_ret

    # Process state requirements for M3 routing
    _proc_req = ""
    if _binding_hint == "charge_exchange":
        _proc_req = "salt_concentration"
    elif _binding_hint == "metal_chelation":
        _proc_req = "imidazole"

    residuals = dict(microsphere.residual_concentrations)
    residual_warnings = _residual_reagent_warnings(residuals)
    warnings.extend(residual_warnings)

    # Build FMC manifest by combining the microsphere composite with the
    # FMC-level mapping evidence (e.g., ranking_only ligand types, m3_support).
    fmc_manifest = _build_fmc_manifest(
        microsphere_manifest=microsphere.model_manifest,
        confidence_tier_str=_conf_tier,
        ligand_type=ligand_type,
        m3_support_level=_m3_support,
        q_max_est=q_max_est,
        q_max_notes=q_max_notes,
        warnings=warnings,
    )

    fmc = FunctionalMediaContract(
        bead_d50=contract.bead_d50,
        porosity=contract.porosity,
        pore_size_mean=contract.pore_size_mean,
        ligand_type=ligand_type,
        installed_ligand=installed_ligand,
        functional_ligand_density=functional_density,
        total_coupled_density=coupled_density,
        charge_density=functional_density if ligand_type.startswith("iex") else 0.0,
        active_protein_density=functional_density if ligand_type in ("affinity", "biotin_affinity") else 0.0,
        G_DN_updated=microsphere.G_DN_updated,
        E_star_updated=microsphere.E_star_updated,
        estimated_q_max=q_max_est,
        q_max_confidence=confidence,
        q_max_mapping_notes=q_max_notes,
        ligand_density_area_basis=_area_basis,
        q_max_area_basis_note=_q_max_area_note,
        binding_model_hint=_binding_hint,
        # v5.9.0 FMC v2 fields
        reagent_accessible_area_per_bed_volume=_reagent_a_v,
        ligand_accessible_area_per_bed_volume=_ligand_a_v,
        capacity_area_basis=_cap_basis,
        activity_retention_uncertainty=_act_unc,
        activity_retention=(
            getattr(_last_coupling_rp, 'activity_retention', 1.0)
            if _last_coupling_rp else 0.0
        ),
        q_max_lower=_q_lower,
        q_max_upper=_q_upper,
        m3_support_level=_m3_support,
        final_ligand_profile_key=_final_key,
        process_state_requirements=_proc_req,
        residual_reagent_concentrations=residuals,
        residual_reagent_warnings=residual_warnings,
        warnings=warnings,
        model_manifest=fmc_manifest,
    )

    # Node 10 (F11): boundary unit/range check at the M2->M3 contract.
    _unit_violations = fmc.validate_units()
    if _unit_violations:
        logger.warning(
            "FunctionalMediaContract failed %d unit/range check(s):\n  %s",
            len(_unit_violations),
            "\n  ".join(_unit_violations),
        )
        fmc.warnings.extend(
            f"FMC unit check: {v}" for v in _unit_violations
        )

    return fmc


def _residual_reagent_warnings(
    residuals: dict[str, float],
    advisory_threshold_mol_m3: float = 1e-2,
) -> list[str]:
    """Return advisory warnings for soluble residuals after modeled washing.

    The model tracks pore-liquid molar concentration, not a validated ppm
    release assay. Therefore these warnings are process-development flags:
    they tell the user where wet-lab residual assays are required before
    chromatography use, not GMP pass/fail decisions.
    """
    warnings: list[str] = []
    for reagent_key, concentration in sorted(residuals.items()):
        if concentration > advisory_threshold_mol_m3:
            warnings.append(
                f"Residual {reagent_key} is {concentration:.3g} mol/m3 after "
                "modeled washing; verify with a residual/leachables assay."
            )
    return warnings


def _build_fmc_manifest(
    microsphere_manifest: Optional[ModelManifest],
    confidence_tier_str: str,
    ligand_type: str,
    m3_support_level: str,
    q_max_est: float,
    q_max_notes: str,
    warnings: list[str],
) -> ModelManifest:
    """Build the FMC manifest combining microsphere evidence with FMC mapping.

    The FMC tier is the weaker of the upstream microsphere tier and the FMC's
    own q_max-mapping confidence. This is the M2->M3 evidence handoff:
    M3 should never claim better evidence than the FMC's worst input.

    Tier mapping for the legacy `confidence_tier` string:
      ranking_only          -> QUALITATIVE_TREND
      semi_quantitative     -> SEMI_QUANTITATIVE
      mapped_estimated      -> SEMI_QUANTITATIVE (q_max from accessibility model,
                              not from a measured isotherm)
      requires_user_calibration -> SEMI_QUANTITATIVE with diagnostic flag
    """
    _STR_TO_TIER = {
        "ranking_only": ModelEvidenceTier.QUALITATIVE_TREND,
        "semi_quantitative": ModelEvidenceTier.SEMI_QUANTITATIVE,
        "mapped_estimated": ModelEvidenceTier.SEMI_QUANTITATIVE,
        "requires_user_calibration": ModelEvidenceTier.SEMI_QUANTITATIVE,
        "not_mapped": ModelEvidenceTier.UNSUPPORTED,
        "validated": ModelEvidenceTier.VALIDATED_QUANTITATIVE,
    }
    fmc_own_tier = _STR_TO_TIER.get(confidence_tier_str, ModelEvidenceTier.SEMI_QUANTITATIVE)

    # If no upstream manifest, we can only attest to FMC-level evidence.
    if microsphere_manifest is None:
        composite_tier = fmc_own_tier
    else:
        # Weakest wins (largest index in the tier list = weakest)
        _ORDER = list(ModelEvidenceTier)
        composite_idx = max(
            _ORDER.index(microsphere_manifest.evidence_tier),
            _ORDER.index(fmc_own_tier),
        )
        composite_tier = _ORDER[composite_idx]

    return ModelManifest(
        model_name=f"M2.FMC.{ligand_type or 'none'}",
        evidence_tier=composite_tier,
        diagnostics={
            "fmc_confidence_tier": confidence_tier_str,
            "m3_support_level": m3_support_level,
            "estimated_q_max": float(q_max_est),
            "ligand_type": ligand_type,
            "n_warnings": len(warnings),
        },
        assumptions=[q_max_notes] if q_max_notes else [],
    )


# ─── ModificationOrchestrator ─────────────────────────────────────────

class ModificationOrchestrator:
    """Execute sequential modification steps on a microsphere.

    Usage:
        orchestrator = ModificationOrchestrator()
        result = orchestrator.run(contract, steps)
        assert result.validate() == []
    """

    def run(
        self,
        contract: M1ExportContract,
        steps: list[ModificationStep],
        *,
        graph: Any = None,
        upstream_node_id: str = "M1",
        node_id_prefix: str = "M2",
    ) -> FunctionalMicrosphere:
        """Execute all modification steps sequentially, tracking ACS.

        Algorithm:
            1. Build AccessibleSurfaceModel from M1 contract.
            2. Initialize ACS inventory from contract + surface model.
            3. For each step: look up reagent, solve, record result.
            4. Accumulate G_DN updates from crosslinking steps.
            5. Return FunctionalMicrosphere with full provenance.

        Args:
            contract: M1ExportContract from Module 1.
            steps: Ordered list of modification steps to execute.
            graph: Optional ``ResultGraph``. When supplied (v0.4.0 / C4),
                each modification step registers its own ``ResultNode``
                so sub-step provenance is preserved instead of collapsed
                into the single M2 node the lifecycle creates.
            upstream_node_id: Id of the node that this M2 sequence depends
                on (default "M1"). Only consulted when ``graph`` is given.
            node_id_prefix: Prefix for sub-step node ids (default "M2").

        Returns:
            FunctionalMicrosphere with updated ACS and modification history.

        Raises:
            KeyError: If a step references an unknown reagent_key.
            ValueError: If a step targets a missing ACS type.
        """
        # --- Build surface model ---
        surface_model = AccessibleSurfaceModel.from_m1_export(contract)

        # --- Initialize ACS from M1 ---
        acs_profiles = initialize_acs_from_m1(contract, surface_model)

        logger.info(
            "ModificationOrchestrator: %d steps, %d ACS types initialized.",
            len(steps), len(acs_profiles),
        )

        # --- Validate workflow ordering (audit F8: backend, not UI-only) ---
        _validate_workflow_ordering(steps, acs_profiles)

        # --- Execute steps sequentially ---
        history: list[ModificationResult] = []
        total_delta_G = 0.0
        residual_concentrations: dict[str, float] = {}

        for i, step in enumerate(steps):
            # Look up reagent profile
            if step.reagent_key not in REAGENT_PROFILES:
                raise KeyError(
                    f"Step {i}: unknown reagent_key '{step.reagent_key}'. "
                    f"Available: {list(REAGENT_PROFILES.keys())}"
                )
            reagent_profile = REAGENT_PROFILES[step.reagent_key]

            logger.info(
                "Step %d/%d: %s with %s on %s",
                i + 1, len(steps), step.step_type.value,
                step.reagent_key, step.target_acs.value,
            )

            result = solve_modification_step(
                step=step,
                acs_state=acs_profiles,
                surface_model=surface_model,
                reagent_profile=reagent_profile,
            )
            history.append(result)
            total_delta_G += result.delta_G_DN
            _update_residual_reagents(
                residual_concentrations=residual_concentrations,
                step=step,
                result=result,
            )

            # v0.4.0 (C4): optional sub-step provenance into a ResultGraph.
            if graph is not None and hasattr(graph, "register_result"):
                _step_node_id = f"{node_id_prefix}.{i + 1:02d}.{step.reagent_key}"
                _previous = (
                    upstream_node_id
                    if i == 0
                    else f"{node_id_prefix}.{i:02d}.{steps[i - 1].reagent_key}"
                )
                _depends = [_previous] if _previous in graph.nodes else []
                graph.register_result(
                    result,
                    node_id=_step_node_id,
                    stage=node_id_prefix,
                    label=f"{step.step_type.value} — {step.reagent_key}",
                    depends_on=_depends,
                    relation="m2_step_sequence",
                )

            logger.info(
                "Step %d: conversion=%.4f, delta_G=%.1f Pa",
                i + 1, result.conversion, result.delta_G_DN,
            )

        # --- Compute updated mechanical properties ---
        G_DN_base = contract.G_DN
        G_DN_updated = G_DN_base + total_delta_G
        # E* ~ 3*G for incompressible rubber (Poisson's ratio ~ 0.5)
        E_star_updated = 3.0 * G_DN_updated

        logger.info(
            "Orchestrator complete: G_DN %.1f -> %.1f Pa (delta=%.1f Pa)",
            G_DN_base, G_DN_updated, total_delta_G,
        )

        # Composite manifest for the microsphere — weakest step tier wins.
        composite_manifest = _build_microsphere_manifest(history)

        return FunctionalMicrosphere(
            m1_contract=contract,
            surface_model=surface_model,
            acs_profiles=acs_profiles,
            modification_history=history,
            G_DN_updated=G_DN_updated,
            E_star_updated=E_star_updated,
            residual_concentrations=residual_concentrations,
            model_manifest=composite_manifest,
        )


def _update_residual_reagents(
    residual_concentrations: dict[str, float],
    step: ModificationStep,
    result: ModificationResult,
) -> None:
    """Update pore-liquid residual concentrations after one M2 step.

    Reaction steps add the unreacted soluble reagent concentration on a
    conservative screening basis. Washing steps multiply every tracked residual
    by the unrecovered fraction from the diffusion-out model.
    """
    if step.step_type == ModificationStepType.WASHING:
        retained_fraction = max(0.0, min(1.0, 1.0 - result.conversion))
        for reagent_key in list(residual_concentrations):
            residual_concentrations[reagent_key] *= retained_fraction
            if residual_concentrations[reagent_key] < 1e-12:
                residual_concentrations[reagent_key] = 0.0
        return

    if step.reagent_concentration <= 0.0:
        return

    unreacted_fraction = max(0.0, min(1.0, 1.0 - result.conversion))
    residual_concentrations[step.reagent_key] = (
        residual_concentrations.get(step.reagent_key, 0.0)
        + step.reagent_concentration * unreacted_fraction
    )


def _build_microsphere_manifest(
    history: list[ModificationResult],
) -> ModelManifest:
    """Aggregate per-step manifests into a single FunctionalMicrosphere manifest.

    Tier rule: the weakest tier across the history wins (UNSUPPORTED >
    QUALITATIVE_TREND > SEMI_QUANTITATIVE > CALIBRATED_LOCAL >
    VALIDATED_QUANTITATIVE). Diagnostics aggregate per-step counts so a
    consumer can tell whether any step was a fallback.

    Empty history returns an UNSUPPORTED manifest — the orchestrator was
    invoked with no chemistry, so no functional surface evidence exists.
    """
    if not history:
        return ModelManifest(
            model_name="M2.composite",
            evidence_tier=ModelEvidenceTier.UNSUPPORTED,
            diagnostics={"n_steps": 0},
            assumptions=["No modification steps executed."],
        )

    _ORDER = list(ModelEvidenceTier)  # validated ... unsupported, in order
    worst_idx = 0
    step_summaries: list[dict] = []
    assumptions: list[str] = []
    for i, mr in enumerate(history):
        m = mr.model_manifest
        if m is None:
            # Defensive: a step without a manifest is treated as the worst tier
            # so the composite cannot be silently upgraded by missing data.
            worst_idx = max(worst_idx, _ORDER.index(ModelEvidenceTier.UNSUPPORTED))
            step_summaries.append({"step": i + 1, "missing_manifest": True})
            continue
        worst_idx = max(worst_idx, _ORDER.index(m.evidence_tier))
        step_summaries.append({
            "step": i + 1,
            "name": m.model_name,
            "tier": m.evidence_tier.value,
            "conversion": m.diagnostics.get("conversion"),
        })
        assumptions.extend(m.assumptions)

    return ModelManifest(
        model_name="M2.composite",
        evidence_tier=_ORDER[worst_idx],
        diagnostics={
            "n_steps": len(history),
            "steps": step_summaries,
            "weakest_tier": _ORDER[worst_idx].value,
        },
        # De-dupe assumptions while preserving order
        assumptions=list(dict.fromkeys(assumptions)),
    )


# ─── Backend Workflow Validation (audit F8) ──────────────────────────

_COUPLING_TYPES = {
    ModificationStepType.LIGAND_COUPLING,
    ModificationStepType.PROTEIN_COUPLING,
}

# Types that require activated sites on target (includes SPACER_ARM)
_REQUIRES_ACTIVATED = _COUPLING_TYPES | {
    ModificationStepType.QUENCHING,
    ModificationStepType.SPACER_ARM,
}

# Rule 4: Allowed reaction_type values per step type (Codex P1-1 fix)
_STEP_ALLOWED_REACTION_TYPES: dict[ModificationStepType, set[str]] = {
    ModificationStepType.SECONDARY_CROSSLINKING: {"crosslinking"},
    ModificationStepType.ACTIVATION: {"activation"},
    ModificationStepType.LIGAND_COUPLING: {"coupling"},
    ModificationStepType.PROTEIN_COUPLING: {"protein_coupling"},
    ModificationStepType.QUENCHING: {"blocking"},
    ModificationStepType.SPACER_ARM: {"spacer_arm", "heterobifunctional"},
    ModificationStepType.METAL_CHARGING: {"metal_charging", "metal_stripping"},
    ModificationStepType.PROTEIN_PRETREATMENT: {"protein_pretreatment"},
    ModificationStepType.WASHING: {"washing"},
}


def _validate_workflow_ordering(
    steps: list[ModificationStep],
    acs_profiles: dict[ACSSiteType, ACSProfile],
) -> None:
    """Validate step ordering before execution (backend authority).

    Rules:
        1. Coupling/quenching requires activated sites on target ACS type.
        2. No steps after quenching on the same target ACS type.
        3. Reagent-target ACS type must match reagent profile's target_acs.
        4. Reagent reaction_type must be compatible with step type.

    Raises:
        ValueError: On blocker-level violations.

    Logs warnings for advisory issues.
    """
    quenched_targets: set[ACSSiteType] = set()

    for i, step in enumerate(steps):
        idx = i + 1

        # Rule 2: No steps after quenching on same target.
        # NOTE: Cross-target workflows (e.g., Quench(EPOXIDE) then Crosslink(AMINE))
        # are intentionally allowed — quenching one group does not block chemistry
        # on a chemically distinct group (validated against wetlab practice).
        if (
            step.target_acs in quenched_targets
            and step.step_type != ModificationStepType.WASHING
        ):
            raise ValueError(
                f"Step {idx}: {step.step_type.value} targets "
                f"{step.target_acs.value} which was already quenched. "
                f"No further chemistry is possible on blocked sites."
            )

        # Rule 1: Coupling/quenching/spacer_arm requires activated sites
        if step.step_type in _REQUIRES_ACTIVATED:
            target_profile = acs_profiles.get(step.target_acs)
            if target_profile is None:
                # Target ACS type doesn't exist yet — may be created by prior step
                prior_produces = any(
                    s.product_acs == step.target_acs
                    for s in steps[:i]
                    if s.step_type in (ModificationStepType.ACTIVATION,
                                       ModificationStepType.SPACER_ARM)
                )
                if not prior_produces:
                    raise ValueError(
                        f"Step {idx}: {step.step_type.value} targets "
                        f"{step.target_acs.value} but no prior activation step "
                        f"produces this site type and it doesn't exist in M1 ACS."
                    )
            elif target_profile.activated_sites <= 0 and target_profile.remaining_activated <= 0:
                # Check if a prior step in this batch will activate it
                prior_activates = any(
                    s.product_acs == step.target_acs
                    for s in steps[:i]
                    if s.step_type in (ModificationStepType.ACTIVATION,
                                       ModificationStepType.SPACER_ARM)
                )
                if not prior_activates:
                    logger.warning(
                        "Step %d: %s targets %s with 0 activated sites. "
                        "Coupling/quenching will have zero conversion.",
                        idx, step.step_type.value, step.target_acs.value,
                    )

        # Rule 3: Reagent profile compatibility
        if step.reagent_key in REAGENT_PROFILES:
            rp = REAGENT_PROFILES[step.reagent_key]
            if step.step_type != ModificationStepType.WASHING and rp.target_acs != step.target_acs:
                raise ValueError(
                    f"Step {idx}: reagent '{step.reagent_key}' targets "
                    f"{rp.target_acs.value} but step targets {step.target_acs.value}. "
                    f"Reagent-target mismatch."
                )

        # Rule 4: Reagent reaction_type must match step type (Codex P1-1 fix)
        if step.reagent_key in REAGENT_PROFILES:
            rp_r4 = REAGENT_PROFILES[step.reagent_key]
            allowed = _STEP_ALLOWED_REACTION_TYPES.get(step.step_type, set())
            if allowed and rp_r4.reaction_type not in allowed:
                raise ValueError(
                    f"Step {idx}: reagent '{step.reagent_key}' has reaction_type "
                    f"'{rp_r4.reaction_type}' which is incompatible with step type "
                    f"'{step.step_type.value}'. Allowed reaction_types: {sorted(allowed)}."
                )

        # Track quenching
        if step.step_type == ModificationStepType.QUENCHING:
            quenched_targets.add(step.target_acs)

