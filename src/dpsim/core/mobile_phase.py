"""Mobile-phase (buffer) specification for chromatography recipe steps.

B-1f / W-023: Δ4 from the v0.7.0 M3 back-pressure work plan
(``docs/update_workplan_2026-05-10_m3_pressure.md``).

A ``MobilePhase`` is the per-step description of the buffer flowing through
the column at a given moment in the recipe program (equilibration, load,
wash, elute, CIP). Together with temperature it determines the dynamic
viscosity μ that drives Kozeny-Carman pressure drop and u_crit downstream.

The companion module :mod:`dpsim.core.viscosity` consumes this value type
to resolve μ(buffer, T) via either a literature-anchored additive model
(SEMI_QUANTITATIVE) or a user-supplied override (CALIBRATED_LOCAL when
the user has measured μ on a viscometer).

Architectural note
------------------
``MobilePhase`` lives in :mod:`dpsim.core` rather than
:mod:`dpsim.module3_performance` because viscosity resolution will also
be consumed by M1 (washing residuals at non-aqueous solvent fractions)
and M2 (coupling kinetics in glycerol-water mixtures). Placing the
value type in core avoids a future circular dependency.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class MobilePhase:
    """User-facing buffer specification per recipe step.

    Either set the four physico-chemical fields (``T_C``, ``c_nacl_M``,
    ``phi_glycerol``, ``phi_ethanol``) and let the
    :mod:`dpsim.core.viscosity` resolver compute μ, or override entirely
    with ``custom_mu_pa_s`` for an explicit value (e.g. the user has
    measured μ on a viscometer for a non-standard buffer).

    All fields default to "equilibration buffer at 20 °C" semantics —
    150 mM NaCl at neutral pH, no co-solvents, no override.

    Attributes
    ----------
    name :
        Human-readable label used in UI display and recipe diagnostics.
        Suggested values: "equilibration", "load", "wash", "elute",
        "cip", "storage".
    T_C :
        Temperature [°C]. Cold-room runs at 4 °C raise μ by ~50 % vs
        20 °C; this field is the dominant viscosity lever after buffer
        composition.
    c_nacl_M :
        NaCl concentration [mol·L⁻¹]. Approximates the ionic strength
        for HIC load (~2 M (NH₄)₂SO₄ ≈ effective 2.5 M NaCl) and IEX
        elution gradients.
    phi_glycerol :
        Glycerol volume fraction [dimensionless, 0..1]. Stabilization
        buffers and cryo-protective wash steps frequently run at
        φ_gly = 0.10–0.30.
    phi_ethanol :
        Ethanol volume fraction [dimensionless, 0..1]. Storage buffers
        run at 0.20; CIP procedures at 0.70 (the highest viscosity
        excursion most chromatography columns ever see).
    pH :
        Mobile-phase pH. Carried for the G7 reagent-pH-window cross-check
        (B-1a precedent) and for future buffer-capacity diagnostics; not
        consumed by the viscosity resolver in v0.7.0.
    custom_mu_pa_s :
        User-supplied dynamic-viscosity override [Pa·s]. When set
        (non-``None``), bypasses the additive model entirely and the
        resolver returns this value with ``tier = CALIBRATED_LOCAL``.
        Use for buffers outside the model's calibration window
        (e.g. high-arginine refold buffers, custom polymer additives,
        organic-rich purification systems).
    """

    name: str = "equilibration"
    T_C: float = 20.0
    c_nacl_M: float = 0.150
    phi_glycerol: float = 0.0
    phi_ethanol: float = 0.0
    pH: float = 7.4
    custom_mu_pa_s: Optional[float] = None
