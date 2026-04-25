"""Trust gates -- assess reliability of simulation predictions.

v0.3.0 (B2): the gate is now family-aware. Checks that depend on agarose +
chitosan surface chemistry (NH2 ratio, agarose calibration range, chitosan
side reactions, IPN eta_coupling) only fire when ``props.polymer_family ==
AGAROSE_CHITOSAN``. Non-A+C families receive an advisory warning that the
trust gate is calibrated primarily against the A+C platform until per-family
trust gates land in v0.4.0+.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .datatypes import (
    FullResult,
    MaterialProperties,
    ModelMode,
    PolymerFamily,
    SimulationParameters,
)


@dataclass
class TrustAssessment:
    """Assessment of prediction reliability."""
    trustworthy: bool
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    upstream_trust_level: str = ""  # Inherited from upstream module (empty if this IS the first module)

    @property
    def level(self) -> str:
        if self.blockers:
            return "UNRELIABLE"
        if self.warnings:
            return "CAUTION"
        return "TRUSTWORTHY"

    def summary(self) -> str:
        lines = [f"Trust Level: {self.level}"]
        for b in self.blockers:
            lines.append(f"  [BLOCKER] {b}")
        for w in self.warnings:
            lines.append(f"  [WARNING] {w}")
        if not self.blockers and not self.warnings:
            lines.append("  All checks passed.")
        return "\n".join(lines)


def assess_trust(result: FullResult, params: SimulationParameters,
                 props: MaterialProperties,
                 crosslinker_key: str = 'genipin',
                 l2_mode: str = 'empirical') -> TrustAssessment:
    """Evaluate whether the simulation results should be trusted.

    Checks for conditions where the model assumptions break down.

    Parameters
    ----------
    crosslinker_key : str
        Key into CROSSLINKERS library, used for chemistry-specific warnings.
    """
    warnings = []
    blockers = []

    # v0.3.0 (B2): family-aware gating. Compare by .value (per CLAUDE.md
    # quirk note: enum identity breaks across importlib.reload boundaries).
    family_value = getattr(getattr(props, "polymer_family", None), "value", "agarose_chitosan")
    is_ac = family_value == PolymerFamily.AGAROSE_CHITOSAN.value

    e = result.emulsification
    g = result.gelation
    x = result.crosslinking
    m = result.mechanical

    if not is_ac:
        warnings.append(
            f"Trust gate is calibrated primarily against the agarose+chitosan platform; "
            f"polymer_family={family_value!r} runs are screened with universal physics "
            "checks only. Family-specific trust gates land in v0.4.0+."
        )

    # 1. Droplet size outside model validity
    if e.d32 < 0.5e-6:
        blockers.append(
            f"d32={e.d32*1e6:.2f} um is below 0.5 um -- sub-Kolmogorov regime, "
            "PBE breakage kernels not validated at this scale"
        )
    if e.d32 > 100e-6:
        warnings.append(
            f"d32={e.d32*1e6:.0f} um -- very large droplets, may not form stable microspheres"
        )

    # 2. PBE convergence
    if not e.converged:
        warnings.append("PBE solver did not reach steady state -- increase emulsification time")

    # 3. Size distribution too broad
    if e.span > 2.0:
        warnings.append(
            f"Span={e.span:.1f} -- very polydisperse, not suitable for chromatographic media"
        )

    # 4. Pore size outside useful range for chromatography
    if g.pore_size_mean < 20e-9:
        warnings.append(
            f"Pore size={g.pore_size_mean*1e9:.0f} nm -- too small for protein access"
        )
    if g.pore_size_mean > 1000e-9:
        warnings.append(
            f"Pore size={g.pore_size_mean*1e9:.0f} nm -- too large for SEC resolution"
        )

    # 5. Gelation incomplete
    if g.alpha_final < 0.8:
        blockers.append(
            f"Gelation only {g.alpha_final:.0%} complete -- microspheres may not form properly. "
            "Check cooling rate and T_gel."
        )

    # 6. Crosslinking stoichiometry-limited (A+C secondary network specific)
    if is_ac and x.p_final < 0.01:
        warnings.append(
            f"Crosslinking fraction={x.p_final:.1%} -- very low, increase crosslinker concentration"
        )

    # 7. Crosslinker is limiting reagent \u2014 A+C only (chitosan -NH2 stoichiometry)
    if is_ac:
        from .level3_crosslinking.solver import recommended_crosslinker_concentration
        NH2_total = params.formulation.c_chitosan * 1000 * props.DDA / props.M_GlcN
        if NH2_total > 0 and params.formulation.c_genipin / NH2_total < 0.05:
            c_min = recommended_crosslinker_concentration(
                params.formulation.c_chitosan, props.DDA, props.M_GlcN,
                target_p=0.10,
            )
            warnings.append(
                f"Crosslinker/NH2 ratio = {params.formulation.c_genipin/NH2_total:.3f} -- "
                f"crosslinker-limited. Increase to at least {c_min:.1f} mol/m\u00b3 for ratio \u2265 0.05. "
                "Increasing crosslinking time will not help."
            )

    # 8. Mechanical properties unreasonable
    if m.G_DN < 100:
        blockers.append(
            f"G_DN={m.G_DN:.0f} Pa -- too soft for column packing"
        )
    if m.G_DN > 1e6:
        warnings.append(
            f"G_DN={m.G_DN/1000:.0f} kPa -- unusually stiff, check agarose concentration"
        )

    # 9. Viscosity ratio extreme
    if props.mu_d > 0 and props.mu_oil > 0:
        ratio = props.mu_d / props.mu_oil
        if ratio > 100:
            warnings.append(
                f"Viscosity ratio mu_d/mu_c={ratio:.0f} -- extreme, breakage predictions uncertain. "
                "Consider enabling C3 viscous correction."
            )

    # 10. Empirical pore model outside calibration range — A+C only (agarose%)
    if is_ac:
        c_agar_pct = params.formulation.c_agarose / 10.0
        if c_agar_pct < 1.0 or c_agar_pct > 8.0:
            warnings.append(
                f"Agarose={c_agar_pct:.1f}% -- outside empirical pore model calibration range (1-8%)"
            )

    # Fix 7: Crosslinker chemistry-specific warnings
    from .reagent_library import CROSSLINKERS
    xl = CROSSLINKERS.get(crosslinker_key)
    if xl:
        if xl.mechanism == 'amine_bridge' and xl.name.startswith('EDC/NHS'):
            warnings.append("EDC/NHS requires carboxyl (-COOH) groups that standard chitosan lacks. "
                            "Results may not be physically meaningful.")
        if xl.kinetics_model == 'uv_dose':
            warnings.append("PEGDA+UV requires photoinitiator and UV penetration -- "
                            "verify these are present in your formulation.")
        if xl.kinetics_model == 'ionic_instant':
            warnings.append("TPP ionic crosslinks are reversible and unstable in buffered "
                            "salt solutions used in chromatography.")
        if xl.mechanism in ('hydroxyl', 'michael_addition'):
            warnings.append(f"{xl.name} requires alkaline conditions (pH 11-12) that may "
                            "partially dissolve agarose helices.")
        if xl.mechanism == 'ester_bond':
            warnings.append("Citric acid heat cure (80-120C) may partially melt agarose gel. "
                            "Ester bonds are hydrolytically unstable at pH>10.")

    # 11. Hydroxyl crosslinker simplification (chitosan-NH2 side reactions) — A+C only
    if is_ac and crosslinker_key in ('ech', 'dvs', 'citric_acid') and params.formulation.c_chitosan > 0:
        warnings.append(
            "Hydroxyl crosslinker model is simplified — assumes agarose-OH only targeting. "
            "Real chemistry also reacts with chitosan-NH2. Results may underestimate crosslink density."
        )

    # 12. Phenomenological DN modulus (mode-aware)
    _model_mode_for_w3 = getattr(params, 'model_mode', None)
    _model_used = getattr(m, 'model_used', None)
    _suppress_w3 = (
        _model_mode_for_w3 == ModelMode.EMPIRICAL_ENGINEERING
        or _model_used == 'flory_rehner_affine'
    )
    if not _suppress_w3:
        _w3_msg = (
            "G_DN uses phenomenological coupling formula (G1 + G2 + eta*sqrt(G1*G2)). "
            "Suitable for formulation ranking, not absolute mechanical prediction."
        )
        if _model_mode_for_w3 == ModelMode.MECHANISTIC_RESEARCH:
            blockers.append(_w3_msg)
        else:
            # hybrid_coupled and all other modes: keep as warning
            warnings.append(_w3_msg)

    # 13. Model mode mismatch (mechanistic_research requested but empirical L2 used)
    model_mode = getattr(params, 'model_mode', None)
    if model_mode == ModelMode.MECHANISTIC_RESEARCH and l2_mode == 'empirical':
        warnings.append(
            "Mechanistic research mode requested but empirical L2 pore model was used. "
            "Switch to ch_2d for mechanistic consistency."
        )

    # 14. Non-specific eta_coupling — A+C only (IPN coupling coefficient)
    if is_ac:
        _network_meta = getattr(x, 'network_metadata', None)
        _per_chem_eta_active = (
            _network_meta is not None
            and hasattr(_network_meta, 'eta_coupling_recommended')
        )
        if not _per_chem_eta_active and props.eta_coupling == -0.15:
            warnings.append(
                "IPN coupling coefficient (eta=-0.15) is the same default for all crosslinker types. "
                "Per-chemistry eta values would improve accuracy."
            )

    trustworthy = len(blockers) == 0

    return TrustAssessment(
        trustworthy=trustworthy,
        warnings=warnings,
        blockers=blockers,
    )

