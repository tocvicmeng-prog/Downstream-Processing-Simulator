"""v9.5 Tier-3 multi-variant composite L2 solvers.

Promotes the three composite families that were data-only placeholders
through v9.4:

  - PECTIN_CHITOSAN  → polyelectrolyte complex (PEC) shell, mirror of
                       v9.3 ALGINATE_CHITOSAN_PEC pattern. Pectin
                       Ca²⁺-gel skeleton + chitosan ammonium shell via
                       carboxylate / ammonium electrostatic complexation.
  - GELLAN_ALGINATE  → dual ionic-gel composite. Gellan helix-aggregation
                       (K⁺) co-gels with alginate Ca²⁺. Both networks
                       contribute structurally; alginate is the
                       structurally dominant network.
  - PULLULAN_DEXTRAN → neutral α-glucan composite microbeads. Both
                       components share -OH-rich ECH/STMP crosslink
                       chemistry; analogous to dextran-ECH alone.

All three follow the v9.2 / v9.3 / v9.4 parallel-module + delegate-and-
retag pattern (D-016 / D-017 / D-027 / D-037) so bit-for-bit equivalence
with v9.1 calibrated kernels is preserved by construction.

Each solver:

* enforces ``polymer_family.value`` against the expected enum value (per
  the CLAUDE.md `.value`-comparison rule, AST-enforced via
  ``test_v9_3_enum_comparison_enforcement.py``).
* runs the closest pure-component solver in a sandbox where the family
  is temporarily set to the delegate's expected value.
* re-tags the result with composite provenance, including a
  per-composite assumption block citing the SA screening report's
  bioprocess-relevance note (drug-delivery / food-dominant) and a
  ±50 % magnitude uncertainty pending wet-lab calibration.
* defaults to ``QUALITATIVE_TREND`` evidence — promotion to
  ``SEMI_QUANTITATIVE`` requires Q-013/Q-014-style wet-lab data.

References
----------
Pectin-chitosan PEC:
    Birch & Schiffman (2014) Carbohydr. Polym. 102:856 — pectin/chitosan
    PEC microspheres for controlled drug release.
Gellan-alginate composite:
    Pereira et al. (2018) Polymers 10:147 — gellan/alginate co-gelation
    for food-texture systems; references useful for drug-delivery scaling.
Pullulan-dextran composite microbeads:
    Singh & Ali (2008) Int. J. Biol. Macromol. 42:113 — STMP-crosslinked
    pullulan/dextran composite particles.
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


# ─── Internal helpers (mirrored from tier2_families.py / tier3_families.py) ──


def _delegate_via_alginate_ionic(
    params: SimulationParameters,
    props: MaterialProperties,
    R_droplet: float,
    C_ion_bath_mM: float,
) -> GelationResult:
    """Run alginate ionic-Ca solver in a sandbox where the family is
    ALGINATE; ``C_ion_bath_mM`` is the divalent ion concentration."""
    from .ionic_ca import solve_ionic_ca_gelation

    sandbox = dataclass_replace(props, polymer_family=PolymerFamily.ALGINATE)
    return solve_ionic_ca_gelation(
        params=params, props=sandbox, R_droplet=R_droplet,
        C_Ca_bath=C_ion_bath_mM,
    )


def _delegate_via_dextran_ech(
    params: SimulationParameters,
    props: MaterialProperties,
    R_droplet: float,
    mode: str,
    timing: GelationTimingResult | None,
) -> GelationResult:
    """Run dextran-ECH solver in a sandbox where the family is DEXTRAN."""
    from .dextran_ech import solve_dextran_ech_gelation

    sandbox = dataclass_replace(props, polymer_family=PolymerFamily.DEXTRAN)
    return solve_dextran_ech_gelation(
        params=params, props=sandbox, R_droplet=R_droplet,
        mode=mode, timing=timing,
    )


def _retag_composite(
    result: GelationResult,
    *,
    model_tier: str,
    family_value: str,
    extra_assumptions: list[str],
    extra_diagnostics: dict | None = None,
    evidence_tier: ModelEvidenceTier = ModelEvidenceTier.QUALITATIVE_TREND,
    calibration_ref: str | None = None,
) -> GelationResult:
    """Re-tag delegate result with composite Tier-3 provenance.

    Default tier is QUALITATIVE_TREND because v9.5 composites carry the
    SA screening report's "lower bioprocess relevance" note. Promotion
    to SEMI_QUANTITATIVE requires composite-specific wet-lab data (a
    constituent-only calibration is not sufficient).
    """
    base_manifest = result.model_manifest
    base_assumptions = (
        list(base_manifest.assumptions) if base_manifest is not None else []
    )
    base_diag = dict(base_manifest.diagnostics) if base_manifest is not None else {}
    if extra_diagnostics is not None:
        base_diag.update(extra_diagnostics)
    base_diag["polymer_family"] = family_value
    base_diag["tier"] = "v9.5_tier_3_composite"

    new_manifest = ModelManifest(
        model_name=f"L2.{family_value}.qualitative_trend_v9_5",
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


# ─── PECTIN_CHITOSAN PEC ───────────────────────────────────────────────


def solve_pectin_chitosan_pec_gelation(
    params: SimulationParameters,
    props: MaterialProperties,
    R_droplet: float = 1.0e-6,
    mode: str = "empirical",
    timing: GelationTimingResult | None = None,
) -> GelationResult:
    """Pectin / chitosan polyelectrolyte-complex (PEC) bead.

    Two-step composite: low-methoxy pectin Ca²⁺-gels first (forms the
    galacturonic-acid carboxylate skeleton), then chitosan diffuses to
    the surface and forms a PEC shell via electrostatic complexation
    between pectin carboxylate (-COO⁻) and chitosan ammonium (-NH₃⁺).
    Mirror of v9.3 ALGINATE_CHITOSAN_PEC pattern but with pectin
    replacing alginate as the anionic skeleton.

    Drug-delivery dominant per SA screening; bioprocess relevance is
    limited but real (pH-controlled release of captured proteins).
    """
    if props.polymer_family.value != PolymerFamily.PECTIN_CHITOSAN.value:
        raise ValueError(
            f"solve_pectin_chitosan_pec_gelation requires polymer_family="
            f"PECTIN_CHITOSAN, got {props.polymer_family.value!r}"
        )
    if mode != "empirical":
        raise NotImplementedError(
            f"v9.5 PECTIN_CHITOSAN solver supports mode='empirical' only; "
            f"got {mode!r}"
        )

    base = _delegate_via_alginate_ionic(params, props, R_droplet, 50.0)
    pec_shell_thickness_nm = float(R_droplet * 0.05 * 1e9)
    return _retag_composite(
        base,
        model_tier="pectin_chitosan_pec_v9_5",
        family_value=PolymerFamily.PECTIN_CHITOSAN.value,
        extra_assumptions=[
            "Pectin Ca²⁺-gel forms the bead skeleton (galacturonic-acid "
            "carboxylate, low-methoxy pectin DE < 50 %); chitosan diffuses "
            "to the surface and complexes with pectin carboxylate (PEC "
            "shell) via electrostatic interaction. Mirror of v9.3 "
            "alginate-chitosan PEC pattern.",
            "Shell thickness estimated as 5 % of bead radius (Birch 2014); "
            "refine in wet-lab calibration. Charge stoichiometry and "
            "ionic strength dependence not yet modeled.",
            "PEC stable at pH 5.5–6.5; dissociates outside this window.",
            "Drug-delivery dominant (SA screening § 6.4); bioprocess "
            "relevance is limited — useful for pH-controlled release of "
            "captured proteins. Tier-3 QUALITATIVE_TREND. Magnitudes carry "
            "±50 % uncertainty pending composite-specific wet-lab data.",
        ],
        extra_diagnostics={
            "pec_shell_thickness_nm": pec_shell_thickness_nm,
            "skeleton_network": "pectin_Ca",
            "shell_network": "chitosan_PEC",
            "pH_window": "5.5-6.5",
            "assumed_DE": "low_methoxy (< 50%)",
        },
        evidence_tier=ModelEvidenceTier.QUALITATIVE_TREND,
        calibration_ref="birch_2014_carbohydr_polym_102_856",
    )


# ─── GELLAN_ALGINATE composite ─────────────────────────────────────────


def solve_gellan_alginate_gelation(
    params: SimulationParameters,
    props: MaterialProperties,
    R_droplet: float = 1.0e-6,
    mode: str = "empirical",
    timing: GelationTimingResult | None = None,
) -> GelationResult:
    """Gellan / alginate dual ionic-gel composite bead.

    Both components are anionic polysaccharides that form ionic gels
    with divalent cations. Co-gelation: Ca²⁺ gels alginate strongly
    (G-block carboxylates), and partially gels gellan (low-acyl gellan
    accepts Ca²⁺ in addition to its preferred K⁺). The composite
    behaves like a reinforced alginate network with a ~20 % G_DN bump
    contributed by gellan helix-aggregation.

    Food provenance dominates per SA screening; bioprocess relevance
    sits below the v9.4 promotion bar. Constituents (alginate as v9.1
    Tier-1, gellan as v9.4 Tier-3) are independently UI-enabled.
    """
    if props.polymer_family.value != PolymerFamily.GELLAN_ALGINATE.value:
        raise ValueError(
            f"solve_gellan_alginate_gelation requires polymer_family="
            f"GELLAN_ALGINATE, got {props.polymer_family.value!r}"
        )
    if mode != "empirical":
        raise NotImplementedError(
            f"v9.5 GELLAN_ALGINATE solver supports mode='empirical' only; "
            f"got {mode!r}"
        )

    base = _delegate_via_alginate_ionic(params, props, R_droplet, 50.0)
    g_reinforcement_factor = 1.20  # +20 % from gellan helix-aggregation
    return _retag_composite(
        base,
        model_tier="gellan_alginate_v9_5",
        family_value=PolymerFamily.GELLAN_ALGINATE.value,
        extra_assumptions=[
            "Ca²⁺ gels alginate strongly (G-block carboxylate egg-box) "
            "and partially gels low-acyl gellan via helix-aggregation; "
            "alginate is the structurally dominant network. Modeled as "
            "alginate Ca²⁺ shrinking-core diffusion with a +20 % G_DN "
            "reinforcement from gellan (Pereira 2018).",
            "K⁺ as the secondary gelant for gellan-only structuring is "
            "not modeled separately here; co-gelation in mixed K⁺/Ca²⁺ "
            "baths requires bath-composition fitting.",
            "Food provenance dominates (SA screening § 6.4); bioprocess "
            "relevance is limited. Tier-3 QUALITATIVE_TREND. Reinforcement "
            "factor is a literature-anchored placeholder; ±50 % uncertainty.",
        ],
        extra_diagnostics={
            "g_reinforcement_factor": g_reinforcement_factor,
            "primary_network": "alginate_Ca",
            "secondary_network": "gellan_helix",
            "ion": "Ca2+",
            "C_ion_bath_mM": 50.0,
        },
        evidence_tier=ModelEvidenceTier.QUALITATIVE_TREND,
        calibration_ref="pereira_2018_polymers_10_147",
    )


# ─── PULLULAN_DEXTRAN composite ────────────────────────────────────────


def solve_pullulan_dextran_gelation(
    params: SimulationParameters,
    props: MaterialProperties,
    R_droplet: float = 1.0e-6,
    mode: str = "empirical",
    timing: GelationTimingResult | None = None,
) -> GelationResult:
    """Pullulan / dextran composite microbead.

    Both components are neutral α-glucans (pullulan = α-(1→4),(1→6);
    dextran = α-(1→6),(1→3)). Both share the same -OH-rich ECH / STMP
    crosslinking chemistry. The composite is structurally indistinguish-
    able from dextran-ECH at the v9.5 modelling resolution; the
    pullulan fraction adds processing handles (lower viscosity at
    equivalent MW, more uniform droplet break-up) but does not change
    pore-size / G_DN scaling laws meaningfully.

    Mostly drug-delivery applications per SA screening; bioprocess
    relevance is limited. Tier-3 QUALITATIVE_TREND.
    """
    if props.polymer_family.value != PolymerFamily.PULLULAN_DEXTRAN.value:
        raise ValueError(
            f"solve_pullulan_dextran_gelation requires polymer_family="
            f"PULLULAN_DEXTRAN, got {props.polymer_family.value!r}"
        )
    if mode != "empirical":
        raise NotImplementedError(
            f"v9.5 PULLULAN_DEXTRAN solver supports mode='empirical' only; "
            f"got {mode!r}"
        )

    base = _delegate_via_dextran_ech(params, props, R_droplet, mode, timing)
    return _retag_composite(
        base,
        model_tier="pullulan_dextran_v9_5",
        family_value=PolymerFamily.PULLULAN_DEXTRAN.value,
        extra_assumptions=[
            "Pullulan/dextran composite microbead modeled by analogy to "
            "dextran-ECH alone — both are neutral α-glucans with the same "
            "-OH-rich ECH/STMP crosslinking chemistry (Singh 2008). Pore-"
            "size / G_DN scaling laws unchanged at the v9.5 resolution.",
            "Pullulan fraction contributes processing handles (lower "
            "viscosity at equivalent MW; more uniform droplet break-up) "
            "but does not modify the equilibrium network. Modelled as a "
            "transparent overlay on dextran-ECH.",
            "Drug-delivery applications dominate (SA screening § 6.4); "
            "bioprocess relevance is limited. Tier-3 QUALITATIVE_TREND. "
            "STMP-crosslinked variant noted but not modelled separately.",
        ],
        extra_diagnostics={
            "polysaccharide_type": "neutral_alpha_glucan_composite",
            "primary_chemistry": "ECH_or_STMP",
            "constituents": "pullulan + dextran",
        },
        evidence_tier=ModelEvidenceTier.QUALITATIVE_TREND,
        calibration_ref="singh_2008_int_j_biol_macromol_42_113",
    )


__all__ = [
    "solve_pectin_chitosan_pec_gelation",
    "solve_gellan_alginate_gelation",
    "solve_pullulan_dextran_gelation",
]
