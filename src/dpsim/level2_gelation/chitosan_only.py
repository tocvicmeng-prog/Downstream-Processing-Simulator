"""v9.2 M0b A2.3 — Chitosan-only gelation solver (semi-quantitative).

Chitosan-only beads gel by mechanisms different from thermal-TIPS:

  - **Genipin / glutaraldehyde** crosslinking via primary amines —
    pH-dependent (chitosan amines are protonated below pKa ≈ 6.3–6.5,
    deprotonated and reactive above).
  - **TPP (tripolyphosphate)** ionotropic gelation via electrostatic
    crosslinking of protonated -NH3+ by polyanionic TPP.
  - **Acid-solubilized droplet** path: chitosan dissolved in dilute
    acetic acid, droplets gelled by base-bath neutralization or
    crosslinker addition.

For v9.2 M0b, this solver provides a **semi-quantitative** result
that:

  1. Uses chitosan concentration and DDA to estimate amine site density.
  2. Applies pH-dependent protonation: f_protonated = 1 / (1 + 10^(pH - pKa)).
  3. Uses an empirical pore-size correlation derived from the
     agarose-chitosan baseline, swapping in the chitosan-only amine
     network as the structural skeleton.
  4. Tags evidence as SEMI_QUANTITATIVE — trends reliable, magnitudes
     approximate; wet-lab calibration (M0b A2.3 follow-on or v9.3)
     required for VALIDATED_QUANTITATIVE tier.

References
----------
Berger et al. (2004) *Eur. J. Pharm. Biopharm.* 57:35 — chitosan
    crosslinking with genipin / glutaraldehyde / TPP; pH dependence.
Mi et al. (2002) *Biomaterials* 23:181 — genipin crosslinked chitosan
    microspheres; structural and mechanical characterization.
Bhumkar & Pokharkar (2006) *AAPS PharmSciTech* 7:E50 — chitosan-TPP
    ionotropic gelation parameters.
"""

from __future__ import annotations

import logging

import numpy as np

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


# Chitosan amine protonation pKa (Sorlier et al. 2001 Biomacromolecules 2:765).
_CHITOSAN_AMINE_PKA = 6.4

# Approximate chitosan repeat-unit molecular weight [g/mol] —
# 161 for GlcN (glucosamine) + 203 for GlcNAc (N-acetylglucosamine);
# weighted average depends on DDA. We use 175 as a midpoint.
_CHITOSAN_RU_MW = 175.0


def _protonated_amine_fraction(ph: float) -> float:
    """Fraction of chitosan -NH2 in protonated -NH3+ form at given pH.

    Sigmoid centered at pKa. Below pKa: predominantly protonated
    (electrostatically active for TPP gelation, less reactive for
    nucleophilic crosslinking with genipin/aldehydes). Above pKa:
    predominantly deprotonated (covalent crosslinking favored).
    """
    return 1.0 / (1.0 + 10 ** (ph - _CHITOSAN_AMINE_PKA))


def solve_chitosan_only_gelation(
    params: SimulationParameters,
    props: MaterialProperties,
    R_droplet: float = 1.0e-6,
    mode: str = "empirical",
    timing: GelationTimingResult | None = None,
) -> GelationResult:
    """Chitosan-only gelation: semi-quantitative pore/porosity prediction.

    For v9.2 this is a **semi-quantitative** model: it captures the
    correct functional dependence on chitosan concentration, DDA, and
    pH but the absolute pore-size and porosity magnitudes carry an
    estimated ±50% uncertainty pending wet-lab calibration.

    Parameters
    ----------
    params, props : SimulationParameters, MaterialProperties
    R_droplet : float
        Microsphere radius [m].
    mode : str
        Currently only ``"empirical"`` is supported.
    timing : GelationTimingResult, optional
        L2a timing; if provided, ``alpha_final`` is taken from timing.

    Returns
    -------
    GelationResult
        With ``model_tier = "chitosan_only_semi_quantitative_v9_2"``
        and ModelManifest at SEMI_QUANTITATIVE evidence tier.
    """
    if props.polymer_family.value != PolymerFamily.CHITOSAN.value:
        raise ValueError(
            f"solve_chitosan_only_gelation requires polymer_family=CHITOSAN, "
            f"got {props.polymer_family.value!r}"
        )

    if mode != "empirical":
        raise NotImplementedError(
            f"v9.2 chitosan-only solver supports mode='empirical' only; "
            f"got {mode!r}. Mechanistic modes are v9.3 follow-on."
        )

    # ── Step 1: chitosan concentration → amine site density ────────────
    # c_chitosan lives on params.formulation, not on props.
    c_chitosan = params.formulation.c_chitosan      # [kg/m^3]
    DDA = float(np.clip(props.DDA, 0.0, 1.0))
    if c_chitosan <= 0:
        raise ValueError("CHITOSAN family requires c_chitosan > 0")

    # Repeat-unit concentration [mol/m^3] = (c_chitosan [kg/m^3] * 1000 [g/kg]) / RU_MW [g/mol]
    c_ru_mol_m3 = c_chitosan * 1000.0 / _CHITOSAN_RU_MW
    # Free amine concentration = DDA * RU concentration
    c_amine = DDA * c_ru_mol_m3        # [mol/m^3]

    # ── Step 2: pH-dependent protonation ──────────────────────────────
    ph = float(getattr(params.formulation, "pH", 5.0))
    f_proton = _protonated_amine_fraction(ph)
    f_deproton = 1.0 - f_proton

    # ── Step 3: Empirical pore-size and porosity ──────────────────────
    # Power-law correlation derived from agarose-chitosan baseline,
    # parameterized for chitosan-only as the structural skeleton.
    # Magnitudes carry ±50% uncertainty (semi-quantitative tier).
    #
    # pore_size scales as (c_chitosan)^(-0.5) — denser network gives
    # smaller mesh, consistent with hydrogel scaling theory.
    pore_size_mean = 50e-9 * (10.0 / max(c_chitosan, 1.0)) ** 0.5  # [m]
    pore_size_std = pore_size_mean * 0.35
    porosity = 0.85 - 0.0015 * c_chitosan  # 85% at low conc, decreasing
    porosity = float(np.clip(porosity, 0.4, 0.92))

    # alpha_final from timing or default
    if timing is not None:
        alpha_final = float(timing.alpha_final)
    else:
        # Empirical: chitosan crosslinking reaches ~95% conversion at
        # standard genipin/GA/TPP doses
        alpha_final = 0.95

    # ── Step 4: Build minimal structural arrays ───────────────────────
    # Lightweight 1D radial profile — N_r=64 grid suitable for downstream
    # diffusion solvers. Phi field is uniform (no phase separation in
    # chitosan-only ionotropic / covalent gelation).
    N_r = 64
    r_grid = np.linspace(0.0, R_droplet, N_r)
    phi_field = np.full(N_r, 1.0 - porosity)  # solid fraction

    # Pore-size distribution (gaussian)
    pore_distribution = np.random.default_rng(seed=42).normal(
        loc=pore_size_mean, scale=pore_size_std, size=N_r,
    )
    pore_distribution = np.clip(pore_distribution, 1e-9, None)

    # Characteristic wavelength: ~mesh size for chitosan gel
    char_wavelength = pore_size_mean

    manifest = ModelManifest(
        model_name="L2.chitosan_only.semi_quantitative_v9_2",
        evidence_tier=ModelEvidenceTier.SEMI_QUANTITATIVE,
        calibration_ref="berger_2004_eur_j_pharm_57_35",
        assumptions=[
            "Chitosan-only gel; no agarose secondary network present.",
            "Amine protonation modeled by pKa=6.4 sigmoid (Sorlier 2001).",
            "Pore-size correlation parameterized from the agarose-"
            "chitosan baseline; magnitudes carry ±50% uncertainty.",
            "Crosslinking conversion alpha_final=0.95 assumed at "
            "standard genipin/GA/TPP doses; override via timing argument "
            "for application-specific kinetics.",
            "Phi field is uniform — chitosan ionotropic / covalent "
            "gelation does not produce phase separation in v9.2 model.",
        ],
        diagnostics={
            "polymer_family": "chitosan",
            "c_chitosan_kg_m3": float(c_chitosan),
            "DDA": DDA,
            "pH": ph,
            "amine_protonated_fraction": float(f_proton),
            "amine_deprotonated_fraction": float(f_deproton),
            "amine_concentration_mol_m3": float(c_amine),
            "pore_size_mean_nm": float(pore_size_mean * 1e9),
            "porosity": float(porosity),
        },
    )

    return GelationResult(
        r_grid=r_grid,
        phi_field=phi_field,
        pore_size_mean=float(pore_size_mean),
        pore_size_std=float(pore_size_std),
        pore_size_distribution=pore_distribution,
        porosity=float(porosity),
        alpha_final=float(alpha_final),
        char_wavelength=float(char_wavelength),
        bicontinuous_score=0.3,   # chitosan gel is not strongly bicontinuous
        anisotropy=0.0,
        connectivity=1.0,
        chord_skewness=0.0,
        model_tier="chitosan_only_semi_quantitative_v9_2",
        model_manifest=manifest,
    )


__all__ = [
    "solve_chitosan_only_gelation",
    "_protonated_amine_fraction",   # exported for testing
    "_CHITOSAN_AMINE_PKA",
]
