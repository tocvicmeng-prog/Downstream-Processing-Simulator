"""v9.4 Tier-3 polymer-family L2 solvers.

Four new families documented in the SA screening report § 6.3 with
limited bioprocess relevance but real chemistry:

  - PECTIN    → galacturonic-acid carboxylate Ca²⁺ ionic gelation;
                analogous to alginate; degree-of-esterification matters
  - GELLAN    → K⁺/Ca²⁺ helix-aggregation; analogous to κ-carrageenan
  - PULLULAN  → neutral α-glucan; STMP / ECH crosslinked; analogous
                to dextran-ECH
  - STARCH    → neutral α-glucan; STMP / ECH / POCl3 crosslinked;
                degradation/brittleness flagged

All four use the v9.2 / v9.3 parallel-module + delegate-and-retag
pattern (D-016/D-017/D-027) for bit-for-bit equivalence with v9.1
calibrated kernels by construction. Each carries an explicit
QUALITATIVE_TREND or SEMI_QUANTITATIVE evidence tier and a
"research-mode" / "lower priority" note where the SA report
flagged limited bioprocess relevance.

References
----------
Pectin Ca²⁺ gelation:
    Voragen et al. (2009) Struct. Chem. 20:263 — pectin chemistry and
    DE-dependent Ca²⁺ binding.
Gellan K⁺/Ca²⁺ gelation:
    Morris et al. (2012) Carbohydr. Polym. 89:1054.
Pullulan / starch STMP crosslinking:
    Singh & Ali (2008) Int. J. Biol. Macromol. 42:113 — STMP
    crosslinked starch / pullulan.
"""

from __future__ import annotations

import logging
from dataclasses import replace as dataclass_replace

from ..datatypes import (
    GelationResult,
    GelationTimingResult,
    MaterialProperties,
    ModelEvidenceTier,
    ModelManifest,
    PolymerFamily,
    SimulationParameters,
)

logger = logging.getLogger(__name__)


# ─── Internal helpers (mirrored from tier2_families.py) ────────────────


def _delegate_via_dextran_ech(params, props, R_droplet, mode, timing):
    from .dextran_ech import solve_dextran_ech_gelation

    sandbox = dataclass_replace(props, polymer_family=PolymerFamily.DEXTRAN)
    return solve_dextran_ech_gelation(
        params=params, props=sandbox, R_droplet=R_droplet,
        mode=mode, timing=timing,
    )


def _delegate_via_alginate_ionic(params, props, R_droplet, C_ion_bath_mM):
    """Reuse the alginate ionic-Ca solver in a sandbox where the family
    is ALGINATE; C_ion_bath is the ion concentration (Ca²⁺ for pectin,
    K⁺ for gellan)."""
    from .ionic_ca import solve_ionic_ca_gelation

    sandbox = dataclass_replace(props, polymer_family=PolymerFamily.ALGINATE)
    return solve_ionic_ca_gelation(
        params=params, props=sandbox, R_droplet=R_droplet,
        C_Ca_bath=C_ion_bath_mM,
    )


def _retag_tier3(
    result: GelationResult,
    *,
    model_tier: str,
    family_value: str,
    extra_assumptions: list[str],
    extra_diagnostics: dict | None = None,
    evidence_tier: ModelEvidenceTier = ModelEvidenceTier.QUALITATIVE_TREND,
    calibration_ref: str | None = None,
) -> GelationResult:
    """Re-tag delegate result with Tier-3 family provenance. Default
    tier is QUALITATIVE_TREND because v9.4 Tier-3 is research-priority
    only; bioprocess calibration is not anticipated."""
    base_manifest = result.model_manifest
    base_assumptions = (
        list(base_manifest.assumptions) if base_manifest is not None else []
    )
    base_diag = dict(base_manifest.diagnostics) if base_manifest is not None else {}
    if extra_diagnostics is not None:
        base_diag.update(extra_diagnostics)
    base_diag["polymer_family"] = family_value
    base_diag["tier"] = "v9.4_tier_3"

    new_manifest = ModelManifest(
        model_name=f"L2.{family_value}.qualitative_trend_v9_4",
        evidence_tier=evidence_tier,
        calibration_ref=(
            calibration_ref
            if calibration_ref is not None
            else (base_manifest.calibration_ref if base_manifest is not None else "")
        ),
        assumptions=base_assumptions + extra_assumptions,
        diagnostics=base_diag,
    )
    return dataclass_replace(
        result, model_tier=model_tier, model_manifest=new_manifest,
    )


# ─── PECTIN ────────────────────────────────────────────────────────────


def solve_pectin_gelation(
    params: SimulationParameters,
    props: MaterialProperties,
    R_droplet: float = 1.0e-6,
    mode: str = "empirical",
    timing: GelationTimingResult | None = None,
) -> GelationResult:
    """Pectin Ca²⁺ ionic gelation (galacturonic acid carboxylate).

    Delegates to alginate ionic-Ca solver (analogous shrinking-core
    diffusion physics) with a 50 mM Ca²⁺ bath (typical for low-methoxy
    pectin per Voragen 2009). Re-tags with pectin provenance.
    """
    if props.polymer_family.value != PolymerFamily.PECTIN.value:
        raise ValueError(
            f"solve_pectin_gelation requires polymer_family=PECTIN, "
            f"got {props.polymer_family.value!r}"
        )
    if mode != "empirical":
        raise NotImplementedError(
            f"v9.4 PECTIN solver supports mode='empirical' only; got {mode!r}"
        )

    base = _delegate_via_alginate_ionic(params, props, R_droplet, 50.0)
    return _retag_tier3(
        base,
        model_tier="pectin_Ca_v9_4",
        family_value=PolymerFamily.PECTIN.value,
        extra_assumptions=[
            "Pectin Ca²⁺ ionic gelation modeled by analogy to alginate "
            "shrinking-core diffusion (Voragen 2009). Strength depends on "
            "degree of esterification (DE): low-methoxy pectin (DE < 50 %) "
            "gels strongly with Ca²⁺; high-methoxy pectin requires acid + "
            "sugar (sugar-acid gel mode, not modeled here).",
            "Bioprocess relevance is limited (food / drug-delivery dominate). "
            "Tier-3 SEMI_QUANTITATIVE → QUALITATIVE_TREND.",
        ],
        extra_diagnostics={
            "ion": "Ca2+",
            "C_ion_bath_mM": 50.0,
            "assumed_DE": "low_methoxy (< 50%)",
        },
        evidence_tier=ModelEvidenceTier.QUALITATIVE_TREND,
        calibration_ref="voragen_2009_struct_chem_20_263",
    )


# ─── GELLAN ────────────────────────────────────────────────────────────


def solve_gellan_gelation(
    params: SimulationParameters,
    props: MaterialProperties,
    R_droplet: float = 1.0e-6,
    mode: str = "empirical",
    timing: GelationTimingResult | None = None,
) -> GelationResult:
    """Gellan K⁺/Ca²⁺ helix-aggregation gelation.

    Delegates to alginate ionic-Ca solver with K⁺ at 100 mM (typical
    low-acyl gellan KCl bath per Morris 2012). The κ-carrageenan
    pattern (v9.3 Tier-2) is the closest analog.
    """
    if props.polymer_family.value != PolymerFamily.GELLAN.value:
        raise ValueError(
            f"solve_gellan_gelation requires polymer_family=GELLAN, "
            f"got {props.polymer_family.value!r}"
        )
    if mode != "empirical":
        raise NotImplementedError(
            f"v9.4 GELLAN solver supports mode='empirical' only; got {mode!r}"
        )

    base = _delegate_via_alginate_ionic(params, props, R_droplet, 100.0)
    return _retag_tier3(
        base,
        model_tier="gellan_K_v9_4",
        family_value=PolymerFamily.GELLAN.value,
        extra_assumptions=[
            "Low-acyl gellan + K⁺ helix-aggregation modeled by analogy "
            "to κ-carrageenan + K⁺ (v9.3) and alginate Ca²⁺ shrinking-"
            "core diffusion (Morris 2012). High-acyl gellan has weaker "
            "junction zones and is not modeled separately.",
            "Bioprocess relevance is limited (food / drug-delivery "
            "dominate). Tier-3 QUALITATIVE_TREND.",
            "Trivalent Al³⁺ gellan gelation exists (see ion-gelation "
            "registry entry) but is non-biotherapeutic.",
        ],
        extra_diagnostics={
            "ion": "K+",
            "C_ion_bath_mM": 100.0,
            "subtype": "low_acyl",
        },
        evidence_tier=ModelEvidenceTier.QUALITATIVE_TREND,
        calibration_ref="morris_2012_carbohydr_polym_89_1054",
    )


# ─── PULLULAN ──────────────────────────────────────────────────────────


def solve_pullulan_gelation(
    params: SimulationParameters,
    props: MaterialProperties,
    R_droplet: float = 1.0e-6,
    mode: str = "empirical",
    timing: GelationTimingResult | None = None,
) -> GelationResult:
    """Pullulan STMP/ECH-crosslinked bead.

    Pullulan is a neutral α-(1→4),(1→6)-glucan analogous to dextran in
    -OH-rich chemistry. Delegates to dextran-ECH solver and re-tags.
    """
    if props.polymer_family.value != PolymerFamily.PULLULAN.value:
        raise ValueError(
            f"solve_pullulan_gelation requires polymer_family=PULLULAN, "
            f"got {props.polymer_family.value!r}"
        )
    if mode != "empirical":
        raise NotImplementedError(
            f"v9.4 PULLULAN solver supports mode='empirical' only; got {mode!r}"
        )

    base = _delegate_via_dextran_ech(params, props, R_droplet, mode, timing)
    return _retag_tier3(
        base,
        model_tier="pullulan_ech_v9_4",
        family_value=PolymerFamily.PULLULAN.value,
        extra_assumptions=[
            "Pullulan is a neutral α-(1→4),(1→6)-glucan analogous to "
            "dextran's -OH-rich chemistry; pore-size scaling follows "
            "the same ECH-crosslink-density correlation. STMP-crosslinked "
            "pullulan is also documented (Singh 2008) but not modeled "
            "separately here.",
            "Mostly drug-delivery applications; lower bioprocess relevance. "
            "Tier-3 QUALITATIVE_TREND.",
        ],
        extra_diagnostics={
            "polysaccharide_type": "neutral_alpha_glucan",
            "primary_chemistry": "ECH_or_STMP",
        },
        evidence_tier=ModelEvidenceTier.QUALITATIVE_TREND,
        calibration_ref="singh_2008_int_j_biol_macromol_42_113",
    )


# ─── STARCH ────────────────────────────────────────────────────────────


def solve_starch_gelation(
    params: SimulationParameters,
    props: MaterialProperties,
    R_droplet: float = 1.0e-6,
    mode: str = "empirical",
    timing: GelationTimingResult | None = None,
) -> GelationResult:
    """Starch crosslinked porous bead.

    Like pullulan, starch is a neutral α-glucan; STMP / ECH crosslinking
    chemistry is the same. Delegates to dextran-ECH and re-tags with
    starch-specific warnings about gelatinization, retrogradation, and
    enzymatic degradation.
    """
    if props.polymer_family.value != PolymerFamily.STARCH.value:
        raise ValueError(
            f"solve_starch_gelation requires polymer_family=STARCH, "
            f"got {props.polymer_family.value!r}"
        )
    if mode != "empirical":
        raise NotImplementedError(
            f"v9.4 STARCH solver supports mode='empirical' only; got {mode!r}"
        )

    base = _delegate_via_dextran_ech(params, props, R_droplet, mode, timing)
    return _retag_tier3(
        base,
        model_tier="starch_porous_v9_4",
        family_value=PolymerFamily.STARCH.value,
        extra_assumptions=[
            "Starch crosslinked porous bead modeled by analogy to "
            "dextran-ECH (same neutral α-glucan -OH-rich chemistry).",
            "Starch carries gelatinization (≥ 60 °C destructures the "
            "granules irreversibly) and retrogradation (slow recrystal-"
            "lization) flags; downstream M2/M3 should warn about long-"
            "term storage stability.",
            "Enzymatic degradation by α-amylase is a known mode of failure; "
            "starch beads are NOT recommended for crude-lysate work where "
            "endogenous amylases may be present.",
            "Food/industrial provenance dominates; bioprocess relevance "
            "is limited. Tier-3 QUALITATIVE_TREND. Research-mode use only.",
        ],
        extra_diagnostics={
            "polysaccharide_type": "neutral_alpha_glucan",
            "gelatinization_T_celsius": 60,
            "amylase_susceptibility": "high",
            "research_mode_only": True,
        },
        evidence_tier=ModelEvidenceTier.QUALITATIVE_TREND,
        calibration_ref="singh_2008_int_j_biol_macromol_42_113",
    )


__all__ = [
    "solve_pectin_gelation",
    "solve_gellan_gelation",
    "solve_pullulan_gelation",
    "solve_starch_gelation",
]
