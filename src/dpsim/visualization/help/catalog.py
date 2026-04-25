"""Per-parameter help-text catalog.

Centralised store of the "what does this do?" text shown by ``Help``
popovers. Keyed by a dotted parameter path so callers can look up help
text without hard-coding strings into the tab files. Adding a new
parameter to a tab means adding one line here.

The catalog is *advisory* — a missing entry is not an error; the
caller's ``param_row(help=...)`` is the source of truth. The catalog
exists to keep help text consistent when the same parameter shows up
in multiple places (e.g. ``stir_rate`` in M1 hardware AND in the
recipe-diff display).
"""

from __future__ import annotations

from typing import Final

# Keys are dotted paths. The convention mirrors ProcessRecipe field
# paths (e.g. ``m1.formulation.agarose_pct``) where applicable.
HELP_CATALOG: Final[dict[str, str]] = {
    # ── M1 polymer-family ──
    "m1.family": (
        "Polymer family is the **first M1 input**. Per SA §B matrix it "
        "determines which crosslinker / gelant / cooling-rate widgets render "
        "below. Changing it resets non-applicable parameters."
    ),

    # ── M1 formulation ──
    "m1.formulation.agarose_pct": (
        "Mass fraction of agarose in the dispersed aqueous phase, % w/v. "
        "Drives helix-coil junctions on cooling and the modulus of the "
        "primary network. Typical 2.0–6.0 % w/v."
    ),
    "m1.formulation.chitosan_pct": (
        "Cationic polysaccharide that forms the secondary covalent network "
        "with the crosslinker. Typical 0.5–3.0 % w/v."
    ),
    "m1.formulation.buffer": (
        "Acetic-acid buffer is required to keep chitosan in solution at "
        "the emulsification temperature. Match buffer to family."
    ),
    "m1.formulation.temperature_C": (
        "Hot emulsification temperature. Must exceed agarose gel point "
        "(~38 °C) by at least 20 °C; otherwise gelation begins before "
        "droplet size stabilises."
    ),

    # ── M1 hardware ──
    "m1.hardware.vessel_mode": (
        "Hardware Mode lives inside M1 Emulsification, NOT Global Settings "
        "(v9.0 family-first contract). Changes the kernel used for "
        "droplet-size prediction."
    ),
    "m1.hardware.stir_rpm": (
        "Sets shear rate in the emulsification kernel; drives bead size "
        "distribution mode. Tip speed v_tip = π · D · N / 60 [m/s]."
    ),
    "m1.hardware.cool_rate": (
        "Cooling rate through the gel point [°C/min]. Slower → larger "
        "junction zones → higher modulus. Outside 0.1–5 °C/min the "
        "model is extrapolating."
    ),
    "m1.hardware.oil_water_ratio": (
        "Continuous-phase volume ratio. Above 4:1 starts inverting; "
        "below 1.5:1 the dispersed phase coalesces during stirring."
    ),
    "m1.hardware.impeller": (
        "Geometry of the agitator. Switches the kernel used for "
        "droplet-size prediction. Rushton 6-blade is the canonical "
        "high-shear emulsification choice (Rushton 1950)."
    ),

    # ── M1 crosslinking ──
    "m1.crosslinker": (
        "Amine-reactive electrophile that locks chitosan into a second IPN. "
        "Genipin is biocompatible but slow (24 h). Glutaraldehyde is "
        "fast but cytotoxic; needs aldehyde-quench."
    ),
    "m1.crosslinker_concentration": (
        "Concentration of the secondary crosslinker in mM. Affects both "
        "modulus and residual aldehyde load. Calibrated range 0.5–10 mM."
    ),
    "m1.reaction_time": (
        "Hold time for the secondary crosslinking reaction. Genipin "
        "typically needs 18–24 h; glutaraldehyde 1–4 h."
    ),
    "m1.pore_model": (
        "Determines how the population balance maps droplet size → bead "
        "pore architecture. Bicontinuous matches NIPS-style cellulose."
    ),

    # ── M2 ligand coupling ──
    "m2.template": (
        "Functionalisation template. Combines an activation chemistry "
        "(epoxy, NHS, divinyl-sulfone, etc.) with a ligand class "
        "(Protein A/G/L, IEX, IMAC, etc.)."
    ),
    "m2.ligand_density": (
        "Surface ligand density (mg ligand / mL packed resin). Drives "
        "DBC10 and selectivity. Typical Protein A range: 4–10 mg/mL."
    ),
    "m2.coupling_pH": (
        "pH at which the coupling reaction runs. Must keep both the "
        "ligand and the activated-bead reactive group in their reactive "
        "ionisation state (e.g. Protein A on epoxy: pH 9.0–9.5)."
    ),
    "m2.spacer": (
        "Spacer arm between the bead surface and the ligand. Reduces "
        "steric hindrance for large analytes. Typical: C6 hexyl."
    ),

    # ── M3 column geometry ──
    "m3.column.length": (
        "Packed-bed length in mm. Lower bound is the minimum HETP × N "
        "for the desired separation; upper bound is pressure budget."
    ),
    "m3.column.diameter": (
        "Packed-bed inner diameter in mm. Together with length defines "
        "bed volume. For lab-scale: 5–25 mm."
    ),
    "m3.flow_rate": (
        "Volumetric flow rate in mL/min. Drives residence time, "
        "pressure drop (Ergun), and DBC10. Above the bed-collapse "
        "Reynolds number, results become unreliable."
    ),
    "m3.bind_pH": (
        "pH at the load step. Selected to maximise binding affinity. "
        "Protein A: pH 7.0–7.4."
    ),
    "m3.elute_pH": (
        "pH at the elute step. Selected to drop binding affinity by "
        "≥3 log units. Protein A: pH 3.0–3.5."
    ),
    "m3.mc_samples": (
        "Number of Monte-Carlo samples for the LRM uncertainty band "
        "(P05/P50/P95). Below ~50 samples the band is not informative; "
        "above ~500 returns diminish."
    ),
}


def get_help(path: str, *, default: str = "") -> str:
    """Look up help text for a parameter path; return ``default`` if missing.

    Args:
        path: Dotted parameter path (e.g. ``"m1.formulation.agarose_pct"``).
        default: Returned when the path is not in the catalog. Empty
            string by convention so a missing entry renders no popover.

    Returns:
        The help text or the default.
    """
    return HELP_CATALOG.get(path, default)
