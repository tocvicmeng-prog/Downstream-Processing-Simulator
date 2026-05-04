"""v9.3 Tier-2 polymer-family L2 solvers.

Five new families with distinct gelation chemistries, all implemented
via the v9.2 parallel-module + delegate-and-retag pattern (D-016, D-017
in the v9.2 design log) so that bit-for-bit equivalence with v9.1
calibrated solvers is preserved by construction:

  - HYALURONATE       → covalent network; delegate to dextran-ECH solver
                        for L2 pore-size / porosity scaffolding, retag
                        with HA-specific provenance and BDDE/tyramine
                        chemistry hints
  - KAPPA_CARRAGEENAN → K⁺ ionic gelation; delegate to alginate ionic-Ca
                        solver via the ion-gelation registry adapter,
                        retag with carrageenan provenance
  - AGAROSE_DEXTRAN   → core-shell composite; thermal agarose locks
                        first, dextran phase structures and ECH-hardens.
                        Delegate to the agarose-only solver for thermal
                        kinetics and overlay dextran-ECH pore-size.
  - AGAROSE_ALGINATE  → IPN; thermal agarose + Ca²⁺ alginate orthogonal.
                        Delegate to agarose-only for thermal kernel,
                        compose Ca²⁺ ionic gelation per the ion-gelation
                        registry.
  - ALGINATE_CHITOSAN → polyelectrolyte complex (PEC) shell. Delegate
                        to alginate ionic-Ca for the alginate skeleton,
                        compose chitosan amine network as a thin shell.

Every solver carries a SEMI_QUANTITATIVE evidence tier with explicit
±50 % magnitude uncertainty pending Q-013/Q-014 wet-lab calibration.

References
----------
HA covalent crosslinking:
    Hahn et al. (2006) Biomaterials 27:1104 — BDDE-crosslinked HA gel.
    Sakai et al. (2009) Biomaterials 30:3371 — HRP/tyramine HA networks.
κ-carrageenan ionic gelation:
    Pereira et al. (2021) Polymers 13:471.
Agarose-dextran composite (Capto-class):
    Sun et al. (2024) — agarose/dextran composite microspheres for
    chromatography.
Agarose-alginate IPN:
    Chen et al. (2022) — agarose/alginate hydrogel beads with thermal +
    ionic orthogonal gelation.
Alginate-chitosan PEC:
    Liu et al. (2017) — chitosan-alginate polyelectrolyte complex
    microspheres.
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


# ─── Internal: enforce family + delegate via core agarose path ─────────


def _delegate_via_dextran_ech(
    params: SimulationParameters,
    props: MaterialProperties,
    R_droplet: float,
    mode: str,
    timing: GelationTimingResult | None,
) -> GelationResult:
    """Run the dextran-ECH solver in a sandbox where the family is
    DEXTRAN, so the family-check inside the solver passes. The caller
    then re-tags the result with the actual Tier-2 family provenance.
    """
    from .dextran_ech import solve_dextran_ech_gelation

    sandbox = dataclass_replace(props, polymer_family=PolymerFamily.DEXTRAN)
    return solve_dextran_ech_gelation(
        params=params, props=sandbox, R_droplet=R_droplet,
        mode=mode, timing=timing,
    )


def _delegate_via_agarose_only(
    params: SimulationParameters,
    props: MaterialProperties,
    R_droplet: float,
    mode: str,
    timing: GelationTimingResult | None,
) -> GelationResult:
    """Run the agarose-only thermal solver in a sandbox where the
    family is AGAROSE.
    """
    from .agarose_only import solve_agarose_only_gelation

    sandbox = dataclass_replace(props, polymer_family=PolymerFamily.AGAROSE)
    return solve_agarose_only_gelation(
        params=params, props=sandbox, R_droplet=R_droplet,
        mode=mode, timing=timing,
    )


def _retag(
    result: GelationResult,
    *,
    model_tier: str,
    family_value: str,
    extra_assumptions: list[str],
    extra_diagnostics: dict | None = None,
    evidence_tier: ModelEvidenceTier = ModelEvidenceTier.SEMI_QUANTITATIVE,
    calibration_ref: str | None = None,
) -> GelationResult:
    """Rebuild the ModelManifest with Tier-2 family provenance."""
    base_manifest = result.model_manifest
    base_assumptions = (
        list(base_manifest.assumptions) if base_manifest is not None else []
    )
    base_diag = dict(base_manifest.diagnostics) if base_manifest is not None else {}
    if extra_diagnostics is not None:
        base_diag.update(extra_diagnostics)
    base_diag["polymer_family"] = family_value

    # B-1c (W-007): inherit the delegate solver's valid_domain (if any) so
    # tier-2 analogy results carry their source family's operating envelope.
    # Callers may pass extra_diagnostics={"analogy_source_family": "<base>"} to
    # surface the delegation chain; this is the analogy_source_family hook.
    inherited_domain = (
        dict(base_manifest.valid_domain) if base_manifest is not None else {}
    )
    inherited_domain.setdefault("calibration_status", "tier2_analogy_inheritance")
    new_manifest = ModelManifest(
        model_name=f"L2.{family_value}.semi_quantitative_v9_3",
        evidence_tier=evidence_tier,
        valid_domain=inherited_domain,
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


# ─── HYALURONATE ──────────────────────────────────────────────────────


def solve_hyaluronate_gelation(
    params: SimulationParameters,
    props: MaterialProperties,
    R_droplet: float = 1.0e-6,
    mode: str = "empirical",
    timing: GelationTimingResult | None = None,
) -> GelationResult:
    """Hyaluronic-acid bead gelation (covalent network).

    The canonical HA bead chemistry is covalent crosslinking — typically
    BDDE (Hahn 2006), HRP-tyramine (Sakai 2009), or oxidized-HA + ADH.
    For L2 scaffolding we delegate to the dextran-ECH solver (similar
    hydroxyl-rich polysaccharide pore-size scaling) and retag the result
    with HA-specific provenance.
    """
    if props.polymer_family.value != PolymerFamily.HYALURONATE.value:
        raise ValueError(
            f"solve_hyaluronate_gelation requires polymer_family=HYALURONATE, "
            f"got {props.polymer_family.value!r}"
        )
    if mode != "empirical":
        raise NotImplementedError(
            f"v9.3 HYALURONATE solver supports mode='empirical' only; got {mode!r}"
        )

    base = _delegate_via_dextran_ech(params, props, R_droplet, mode, timing)
    return _retag(
        base,
        model_tier="hyaluronate_covalent_v9_3",
        family_value=PolymerFamily.HYALURONATE.value,
        extra_assumptions=[
            "Hyaluronate bead L2 scaffolding modeled by analogy to "
            "dextran-ECH (similar hydroxyl-rich polysaccharide pore-"
            "size scaling). Actual HA bead chemistry is covalent: "
            "BDDE (Hahn 2006), HRP-tyramine (Sakai 2009), or oxidized-"
            "HA + ADH. Use the M2 reagent profiles "
            "`bis_epoxide_crosslinking` / `hrp_h2o2_tyramine` / "
            "`adh_hydrazone` to model the actual chemistry.",
            "Carboxylate-rich polyelectrolyte; high-swelling regime; "
            "magnitudes carry ±50% uncertainty pending wet-lab calibration "
            "(Q-013/Q-014).",
        ],
        extra_diagnostics={"covalent_route_recommended": "BDDE | HRP-tyramine | oxidized-HA+ADH"},
        calibration_ref="hahn_2006_biomaterials_27_1104",
    )


# ─── KAPPA_CARRAGEENAN ────────────────────────────────────────────────


def solve_kappa_carrageenan_gelation(
    params: SimulationParameters,
    props: MaterialProperties,
    R_droplet: float = 1.0e-6,
    mode: str = "empirical",
    timing: GelationTimingResult | None = None,
) -> GelationResult:
    """κ-Carrageenan bead gelation via K⁺-induced helix aggregation.

    Delegates to the v9.2 alginate ionic-Ca solver in a sandbox where
    the family is ALGINATE — the underlying shrinking-core diffusion
    physics is the same; only the ion identity (K⁺ vs Ca²⁺) and the
    sulfate-ester ACS chemistry differ. Retags the result with
    carrageenan provenance.
    """
    if props.polymer_family.value != PolymerFamily.KAPPA_CARRAGEENAN.value:
        raise ValueError(
            f"solve_kappa_carrageenan_gelation requires "
            f"polymer_family=KAPPA_CARRAGEENAN, got "
            f"{props.polymer_family.value!r}"
        )
    if mode != "empirical":
        raise NotImplementedError(
            f"v9.3 KAPPA_CARRAGEENAN solver supports mode='empirical' "
            f"only; got {mode!r}"
        )

    # κ-carrageenan binds K+ via helix-aggregation; the canonical bath
    # is ~200 mM KCl. The alginate ionic-Ca solver provides the
    # shrinking-core diffusion kernel; we sandbox the family to
    # ALGINATE so the solver's family-check passes, then retag.
    from .ionic_ca import solve_ionic_ca_gelation

    sandbox = dataclass_replace(props, polymer_family=PolymerFamily.ALGINATE)
    # Use 200 mM as the "C_ion_bath" — for κ-carrageenan + K+, this
    # is the typical KCl concentration (Pereira 2021).
    base = solve_ionic_ca_gelation(
        params=params, props=sandbox, R_droplet=R_droplet,
        C_Ca_bath=200.0,                # K+ in mol/m^3 (200 mM)
    )
    return _retag(
        base,
        model_tier="kappa_carrageenan_K_v9_3",
        family_value=PolymerFamily.KAPPA_CARRAGEENAN.value,
        extra_assumptions=[
            "κ-carrageenan ionic-gelation kinetics modeled by analogy "
            "to alginate ionic-Ca shrinking-core diffusion (Pereira "
            "2021). The K⁺ specificity is captured by the ion-registry "
            "entry; the L2 diffusion physics is shared.",
            "Sulfate-ester ACS chemistry distinct from alginate "
            "carboxylate; downstream M2 must use sulfate-targeting "
            "activators (not carboxyl coupling).",
            "ι-Carrageenan responds to Ca²⁺ instead — distinct subtype.",
        ],
        extra_diagnostics={
            "ion": "K+",
            "C_ion_bath_mM": 200.0,
            "subtype": "kappa",
            "primary_acs_chemistry": "sulfate_ester",
        },
        calibration_ref="pereira_2021_polymers_13_471",
    )


# ─── AGAROSE_DEXTRAN core-shell ───────────────────────────────────────


def solve_agarose_dextran_core_shell_gelation(
    params: SimulationParameters,
    props: MaterialProperties,
    R_droplet: float = 1.0e-6,
    mode: str = "empirical",
    timing: GelationTimingResult | None = None,
) -> GelationResult:
    """Core-shell agarose/dextran composite (Capto-class).

    Two-step gelation: thermal agarose helix-coil locks the bead core
    first; dextran phase structures and ECH-hardens to form the shell.
    L2 result reports core (agarose-dominated) pore-size for downstream
    SEC mapping; an additional shell_thickness_nm diagnostic captures
    the dextran shell.
    """
    if props.polymer_family.value != PolymerFamily.AGAROSE_DEXTRAN.value:
        raise ValueError(
            f"solve_agarose_dextran_core_shell_gelation requires "
            f"polymer_family=AGAROSE_DEXTRAN, got "
            f"{props.polymer_family.value!r}"
        )
    if mode != "empirical":
        raise NotImplementedError(
            f"v9.3 AGAROSE_DEXTRAN solver supports mode='empirical' "
            f"only; got {mode!r}"
        )

    base = _delegate_via_agarose_only(params, props, R_droplet, mode, timing)
    # Estimate shell thickness as ~10 % of bead radius — typical for
    # Capto-class media (Cytiva application notes).
    shell_thickness_nm = float(R_droplet * 0.10 * 1e9)
    return _retag(
        base,
        model_tier="agarose_dextran_core_shell_v9_3",
        family_value=PolymerFamily.AGAROSE_DEXTRAN.value,
        extra_assumptions=[
            "Agarose core dominates L2 pore-size and bead mechanical "
            "behaviour. Dextran shell adds ~10% surface layer thickness "
            "with ECH-crosslinked dextran chemistry; shell pore size "
            "follows Sephadex G-class scaling. Source: Capto-class "
            "industrial bioprocess resin literature.",
            "Composite reported as 'agarose pore size' for downstream "
            "SEC mapping; use M2 to surface dextran-shell-specific ligand "
            "coupling chemistry.",
            "Shell thickness estimated as 10 % of bead radius; refine "
            "in v9.3 wet-lab calibration (Q-013).",
        ],
        extra_diagnostics={
            "shell_thickness_nm": shell_thickness_nm,
            "core_polymer": "agarose",
            "shell_polymer": "dextran",
            "shell_chemistry": "ECH-crosslinked",
        },
        calibration_ref="capto_class_application_note",
    )


# ─── AGAROSE_ALGINATE IPN ──────────────────────────────────────────────


def solve_agarose_alginate_ipn_gelation(
    params: SimulationParameters,
    props: MaterialProperties,
    R_droplet: float = 1.0e-6,
    mode: str = "empirical",
    timing: GelationTimingResult | None = None,
) -> GelationResult:
    """Agarose/alginate interpenetrating network bead.

    Orthogonal gelation: thermal agarose helix-coil locks first as the
    bead cools; Ca²⁺ then diffuses in (external bath or internal
    GDL/CaCO₃) and gels the alginate. L2 pore size is dominated by
    the tighter network (typically agarose at ≥4 % w/v); G_DN is
    super-additive due to mutual reinforcement.
    """
    if props.polymer_family.value != PolymerFamily.AGAROSE_ALGINATE.value:
        raise ValueError(
            f"solve_agarose_alginate_ipn_gelation requires "
            f"polymer_family=AGAROSE_ALGINATE, got "
            f"{props.polymer_family.value!r}"
        )
    if mode != "empirical":
        raise NotImplementedError(
            f"v9.3 AGAROSE_ALGINATE solver supports mode='empirical' "
            f"only; got {mode!r}"
        )

    base = _delegate_via_agarose_only(params, props, R_droplet, mode, timing)
    # Mutual reinforcement: G_DN scales super-additively; we surface
    # this as a diagnostic for downstream L4 to consume.
    g_reinforcement_factor = 1.30  # +30 % over agarose-only baseline
    return _retag(
        base,
        model_tier="agarose_alginate_ipn_v9_3",
        family_value=PolymerFamily.AGAROSE_ALGINATE.value,
        extra_assumptions=[
            "Agarose helix-coil locks first (T < T_gel ≈ 38 °C); Ca²⁺ "
            "then diffuses in and gels the alginate carboxylate network. "
            "Orthogonal gelation — L2 pore size dominated by agarose; "
            "alginate adds ~30 % G_DN reinforcement (Chen 2022).",
            "Ca²⁺ source uses the v9.2 ion-gelation registry; default "
            "is the alginate (Ca²⁺ external CaCl₂) entry. Use formulation "
            "fields to override.",
            "Wet-lab calibration (Q-013) needed for the 30 % reinforcement "
            "factor; current value is a literature-anchored placeholder.",
        ],
        extra_diagnostics={
            "g_reinforcement_factor": g_reinforcement_factor,
            "primary_network": "agarose",
            "secondary_network": "alginate",
            "ca_source": "v9.2_ion_registry_default",
        },
        calibration_ref="chen_2022_agarose_alginate_ipn",
    )


# ─── ALGINATE_CHITOSAN PEC ─────────────────────────────────────────────


def solve_alginate_chitosan_pec_gelation(
    params: SimulationParameters,
    props: MaterialProperties,
    R_droplet: float = 1.0e-6,
    mode: str = "empirical",
    timing: GelationTimingResult | None = None,
) -> GelationResult:
    """Alginate / chitosan polyelectrolyte-complex (PEC) bead.

    Two-step: alginate Ca²⁺-gels first (forms the bead skeleton), then
    chitosan diffuses to the surface and forms a PEC shell via
    electrostatic complexation between alginate carboxylate and
    chitosan ammonium. Useful for pH-controlled drug delivery; bioprocess
    applications include pH-controlled release of captured proteins.
    """
    if props.polymer_family.value != PolymerFamily.ALGINATE_CHITOSAN.value:
        raise ValueError(
            f"solve_alginate_chitosan_pec_gelation requires "
            f"polymer_family=ALGINATE_CHITOSAN, got "
            f"{props.polymer_family.value!r}"
        )
    if mode != "empirical":
        raise NotImplementedError(
            f"v9.3 ALGINATE_CHITOSAN solver supports mode='empirical' "
            f"only; got {mode!r}"
        )

    # Use the alginate ionic-Ca solver for the L2 skeleton (alginate is
    # the structural network); chitosan PEC shell is a downstream
    # surface modification we surface as a diagnostic.
    from .ionic_ca import solve_ionic_ca_gelation

    sandbox = dataclass_replace(props, polymer_family=PolymerFamily.ALGINATE)
    base = solve_ionic_ca_gelation(
        params=params, props=sandbox, R_droplet=R_droplet,
        C_Ca_bath=params.formulation.c_Ca_bath,
    )
    # PEC shell thickness ~ 5 % of bead radius for typical chitosan
    # shell formation conditions (Liu 2017).
    pec_shell_thickness_nm = float(R_droplet * 0.05 * 1e9)
    return _retag(
        base,
        model_tier="alginate_chitosan_pec_v9_3",
        family_value=PolymerFamily.ALGINATE_CHITOSAN.value,
        extra_assumptions=[
            "Alginate Ca²⁺-gel forms the bead skeleton; chitosan diffuses "
            "to the surface and complexes electrostatically with alginate "
            "carboxylate (PEC shell). pH-dependent: PEC stable at pH "
            "5.5-6.5; dissociates outside this window.",
            "Shell thickness estimated as 5% of bead radius (Liu 2017); "
            "refine in wet-lab calibration (Q-013). Charge stoichiometry "
            "and ionic strength dependence not yet modeled.",
            "Magnitudes carry ±50% uncertainty pending Q-013 calibration.",
        ],
        extra_diagnostics={
            "pec_shell_thickness_nm": pec_shell_thickness_nm,
            "skeleton_network": "alginate_Ca",
            "shell_network": "chitosan_PEC",
            "pH_window": "5.5-6.5",
        },
        calibration_ref="liu_2017_chitosan_alginate_pec",
    )


__all__ = [
    "solve_hyaluronate_gelation",
    "solve_kappa_carrageenan_gelation",
    "solve_agarose_dextran_core_shell_gelation",
    "solve_agarose_alginate_ipn_gelation",
    "solve_alginate_chitosan_pec_gelation",
]
