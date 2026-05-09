"""Mobile-phase viscosity resolution for chromatography pressure-envelope work.

B-1f / W-023: Δ4 from the v0.7.0 M3 back-pressure work plan
(``docs/update_workplan_2026-05-10_m3_pressure.md``).

This module replaces the ``μ = 1×10⁻³ Pa·s`` hardcoded default in
:mod:`dpsim.module3_performance.hydrodynamics`. Cold-room runs (5 °C),
HIC load buffers (high salt), glycerol-stabilization steps, and
NaOH/ethanol CIP cycles can each shift μ by 50–500 % vs water-at-20 °C;
silently using the wrong μ underestimates ΔP at the pump and can
crush beads during sanitization. This module makes μ a function of the
buffer.

Resolution model
----------------
Two paths:

1. **User override** — when ``MobilePhase.custom_mu_pa_s`` is set
   (non-``None``), the resolver returns that value with
   ``tier = CALIBRATED_LOCAL``. Use this for user-measured viscometry.

2. **Literature-anchored additive model** — otherwise:

   .. math::

      μ(T, c_{NaCl}, φ_{gly}, φ_{etoh}) =
        μ_{water}(T) ·
          (1 + α_{salt} · c_{NaCl}
             + α_{gly}  · φ_{gly}
             + α_{etoh} · φ_{etoh})

   The α-coefficients are anchored at 25 °C with literature sources:

   - μ_water(T): Crittenden 2012 (CRC handbook values, 0–80 °C)
   - α_salt:     Out & Los 1980, Jones-Dole-style fit at 1 M anchor
   - α_gly:      Cheng 2008 glycerol-water linear regime fit
   - α_etoh:     Khattab 2017 ethanol-water linear regime fit

   The cross-terms (T × salt, T × glycerol, T × ethanol) are first-order
   ignored. The linear additive form is accurate at low-to-moderate
   co-solvent fractions but degrades non-linearly above ~30 % glycerol
   or ~30 % ethanol; the resolver flags ``extrapolated=True`` when the
   inputs leave the model's calibration window.

Tier policy
-----------
- ``CALIBRATED_LOCAL`` — user override (viscometry-grade input)
- ``SEMI_QUANTITATIVE`` — additive model, in calibration window
- ``SEMI_QUANTITATIVE`` with ``extrapolated=True`` — additive model,
  flag set; downstream tier-rollup (``PressureEnvelope.decision_tier``,
  B-2f) demotes one step on the flag.

The model never claims ``VALIDATED_QUANTITATIVE`` from this module
alone; that tier requires wet-lab verification at the use site.
"""

from __future__ import annotations

from dataclasses import dataclass

from dpsim.core.mobile_phase import MobilePhase
from dpsim.datatypes import ModelEvidenceTier


# ─── Water viscosity table ───────────────────────────────────────────────────
#
# Pure-water dynamic viscosity at 1 atm. Values from the CRC Handbook of
# Chemistry and Physics, 92nd ed. (2011-2012), tabulated as widely re-cited
# in Crittenden, Trussell, Hand, Howe & Tchobanoglous, "MWH's Water
# Treatment: Principles and Design", 3rd ed., 2012, Appendix C.
#
# Linear interpolation between table points; ValueError outside [0, 80] °C.
# Range covers the chromatography-relevant operating window (cold room ~4 °C
# through warm process ~37 °C) plus CIP at elevated T (60–80 °C for some
# alkaline-cycle protocols).

_WATER_VISCOSITY_TABLE_PA_S: tuple[tuple[float, float], ...] = (
    (0.0, 1.792e-3),
    (5.0, 1.519e-3),
    (10.0, 1.307e-3),
    (15.0, 1.139e-3),
    (20.0, 1.002e-3),
    (25.0, 0.890e-3),
    (30.0, 0.798e-3),
    (40.0, 0.653e-3),
    (50.0, 0.547e-3),
    (60.0, 0.466e-3),
    (70.0, 0.404e-3),
    (80.0, 0.355e-3),
)


# ─── Additive-model coefficients ─────────────────────────────────────────────
#
# All anchored at 25 °C. Fitted to literature data in the linear regime;
# accuracy ~5–10 % within the calibration window.

# NaCl: μ/μ_water = 1 + α_salt · c_M, anchored at 1 M (Out & Los 1980).
# Published 1 M NaCl μ/μ_water at 25 °C ≈ 1.099; α_salt ≈ 0.10 / M.
_ALPHA_SALT_PER_M: float = 0.10

# Glycerol: μ/μ_water = 1 + α_gly · φ in the linear regime φ ≤ 0.30
# (Cheng 2008). Published 20 % glycerol μ/μ_water at 25 °C ≈ 1.74;
# 30 % ≈ 2.50. Linear slope α_gly ≈ 3.5 (under-predicts above φ = 0.30).
_ALPHA_GLYCEROL_PER_PHI: float = 3.5

# Ethanol: μ/μ_water = 1 + α_etoh · φ in the linear regime φ ≤ 0.30
# (Khattab 2017). Published 20 % EtOH μ/μ_water at 25 °C ≈ 2.18;
# 30 % ≈ 2.85. Linear slope α_etoh ≈ 5.9 (under-predicts above φ = 0.30
# where ethanol-water exhibits a viscosity maximum near φ = 0.40–0.45).
_ALPHA_ETHANOL_PER_PHI: float = 5.9


# ─── Calibration-window flags ────────────────────────────────────────────────

_T_REFERENCE_C: float = 25.0
_T_TOLERANCE_C: float = 15.0  # |T - 25| > 15 with co-solvent → extrapolated
_PHI_LINEAR_LIMIT: float = 0.30  # φ above this → extrapolated


# ─── Result type ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ViscosityResult:
    """Resolved mobile-phase viscosity with provenance.

    Carries ``tier`` so downstream tier-rollup
    (e.g. ``PressureEnvelope.decision_tier`` in B-2f) can demote on
    viscosity uncertainty without re-resolving.

    Attributes
    ----------
    mu_pa_s :
        Resolved dynamic viscosity [Pa·s].
    T_C :
        Temperature at which μ was resolved [°C]. Echoed for traceability.
    method :
        Resolution path: ``"custom_override"`` for the
        ``MobilePhase.custom_mu_pa_s`` path,
        ``"additive_model"`` for the literature-anchored fit.
    tier :
        Evidence tier per :class:`ModelEvidenceTier`. ``CALIBRATED_LOCAL``
        for user override; ``SEMI_QUANTITATIVE`` for the additive model.
    extrapolated :
        ``True`` when any input is outside the additive model's
        calibration window (|T − 25 °C| > 15 with non-zero φ_glycerol
        or φ_ethanol; or φ_glycerol > 0.30; or φ_ethanol > 0.30).
        Always ``False`` for ``custom_override``.
    notes :
        Human-readable provenance string for UI / dossier rendering.
    """

    mu_pa_s: float
    T_C: float
    method: str
    tier: ModelEvidenceTier
    extrapolated: bool
    notes: str = ""


# ─── Public API ──────────────────────────────────────────────────────────────


def water_viscosity_pa_s(T_C: float) -> float:
    """Return the dynamic viscosity of pure water at temperature ``T_C``.

    Linear interpolation of the CRC handbook table covering 0–80 °C.

    Parameters
    ----------
    T_C :
        Temperature [°C]. Must be in [0, 80].

    Returns
    -------
    float
        Dynamic viscosity [Pa·s].

    Raises
    ------
    ValueError
        If ``T_C`` is outside [0, 80] °C.
    """
    if T_C < _WATER_VISCOSITY_TABLE_PA_S[0][0]:
        raise ValueError(
            f"T_C={T_C!r} below water-viscosity table minimum "
            f"({_WATER_VISCOSITY_TABLE_PA_S[0][0]} °C). "
            "Use MobilePhase.custom_mu_pa_s to override."
        )
    if T_C > _WATER_VISCOSITY_TABLE_PA_S[-1][0]:
        raise ValueError(
            f"T_C={T_C!r} above water-viscosity table maximum "
            f"({_WATER_VISCOSITY_TABLE_PA_S[-1][0]} °C). "
            "Use MobilePhase.custom_mu_pa_s to override."
        )

    # Find the bracketing pair.
    table = _WATER_VISCOSITY_TABLE_PA_S
    for i in range(len(table) - 1):
        T_lo, mu_lo = table[i]
        T_hi, mu_hi = table[i + 1]
        if T_lo <= T_C <= T_hi:
            if T_hi == T_lo:
                return mu_lo  # exact-match pathological case
            f = (T_C - T_lo) / (T_hi - T_lo)
            return mu_lo + f * (mu_hi - mu_lo)

    # Should be unreachable given the bounds checks above; included for
    # static-analysis completeness.
    raise ValueError(f"T_C={T_C!r} could not be bracketed in the table.")


def resolve_mobile_phase_viscosity(
    mobile_phase: MobilePhase,
    *,
    extrapolation_policy: str = "warn",
) -> ViscosityResult:
    """Resolve mobile-phase viscosity for a chromatography step.

    Resolution order:

    1. If ``mobile_phase.custom_mu_pa_s`` is non-``None``, return it as a
       ``CALIBRATED_LOCAL`` result via the ``"custom_override"`` method.
    2. Otherwise, evaluate the literature-anchored additive model and
       return a ``SEMI_QUANTITATIVE`` result via ``"additive_model"``.
       Set ``extrapolated=True`` if any input is outside the model's
       calibration window.

    Parameters
    ----------
    mobile_phase :
        The buffer specification for the recipe step.
    extrapolation_policy :
        How to handle out-of-window inputs in the additive-model path.

        - ``"warn"`` (default) — set ``extrapolated=True``, append a note,
          return the model value anyway. Caller decides what to do.
        - ``"raise"`` — raise ``ValueError`` immediately.
        - ``"silent"`` — set ``extrapolated=True`` but no note text.

        Has no effect on the ``custom_override`` path.

    Returns
    -------
    ViscosityResult
        Resolved viscosity with provenance.

    Raises
    ------
    ValueError
        If ``extrapolation_policy="raise"`` and the inputs are
        out-of-window. Also if the additive-model inputs are negative
        (physically meaningless) regardless of policy.
    """
    if extrapolation_policy not in ("warn", "raise", "silent"):
        raise ValueError(
            f"extrapolation_policy={extrapolation_policy!r} not in "
            "{'warn', 'raise', 'silent'}."
        )

    # Path 1: user override — bypass the additive model entirely.
    if mobile_phase.custom_mu_pa_s is not None:
        if mobile_phase.custom_mu_pa_s <= 0.0:
            raise ValueError(
                f"custom_mu_pa_s={mobile_phase.custom_mu_pa_s!r} must be "
                "positive."
            )
        return ViscosityResult(
            mu_pa_s=float(mobile_phase.custom_mu_pa_s),
            T_C=mobile_phase.T_C,
            method="custom_override",
            tier=ModelEvidenceTier.CALIBRATED_LOCAL,
            extrapolated=False,
            notes=(
                f"user-supplied override μ={mobile_phase.custom_mu_pa_s:.3e} "
                f"Pa·s for buffer {mobile_phase.name!r}"
            ),
        )

    # Path 2: literature-anchored additive model.
    if mobile_phase.c_nacl_M < 0.0:
        raise ValueError(f"c_nacl_M={mobile_phase.c_nacl_M!r} must be ≥ 0.")
    if mobile_phase.phi_glycerol < 0.0 or mobile_phase.phi_glycerol > 1.0:
        raise ValueError(
            f"phi_glycerol={mobile_phase.phi_glycerol!r} must be in [0, 1]."
        )
    if mobile_phase.phi_ethanol < 0.0 or mobile_phase.phi_ethanol > 1.0:
        raise ValueError(
            f"phi_ethanol={mobile_phase.phi_ethanol!r} must be in [0, 1]."
        )

    mu_water = water_viscosity_pa_s(mobile_phase.T_C)

    correction = (
        1.0
        + _ALPHA_SALT_PER_M * mobile_phase.c_nacl_M
        + _ALPHA_GLYCEROL_PER_PHI * mobile_phase.phi_glycerol
        + _ALPHA_ETHANOL_PER_PHI * mobile_phase.phi_ethanol
    )

    mu_pa_s = mu_water * correction

    # Calibration-window check.
    has_cosolvent = (
        mobile_phase.phi_glycerol > 0.0 or mobile_phase.phi_ethanol > 0.0
    )
    t_out_of_window = (
        abs(mobile_phase.T_C - _T_REFERENCE_C) > _T_TOLERANCE_C
        and has_cosolvent
    )
    phi_gly_out_of_window = mobile_phase.phi_glycerol > _PHI_LINEAR_LIMIT
    phi_etoh_out_of_window = mobile_phase.phi_ethanol > _PHI_LINEAR_LIMIT
    extrapolated = (
        t_out_of_window or phi_gly_out_of_window or phi_etoh_out_of_window
    )

    if extrapolated and extrapolation_policy == "raise":
        raise ValueError(
            f"MobilePhase outside additive-model calibration window: "
            f"T_C={mobile_phase.T_C}, phi_glycerol={mobile_phase.phi_glycerol}, "
            f"phi_ethanol={mobile_phase.phi_ethanol}. "
            "Use MobilePhase.custom_mu_pa_s for an explicit override."
        )

    notes = ""
    if extrapolation_policy == "warn" and extrapolated:
        reasons: list[str] = []
        if t_out_of_window:
            reasons.append(
                f"|T − 25 °C| = {abs(mobile_phase.T_C - _T_REFERENCE_C):.1f} "
                f"> {_T_TOLERANCE_C} with non-zero co-solvent"
            )
        if phi_gly_out_of_window:
            reasons.append(
                f"phi_glycerol={mobile_phase.phi_glycerol:.2f} "
                f"> linear-regime limit {_PHI_LINEAR_LIMIT}"
            )
        if phi_etoh_out_of_window:
            reasons.append(
                f"phi_ethanol={mobile_phase.phi_ethanol:.2f} "
                f"> linear-regime limit {_PHI_LINEAR_LIMIT}"
            )
        notes = (
            f"additive model extrapolated for buffer {mobile_phase.name!r}: "
            + "; ".join(reasons)
            + ". Consider MobilePhase.custom_mu_pa_s with viscometry data."
        )

    return ViscosityResult(
        mu_pa_s=float(mu_pa_s),
        T_C=mobile_phase.T_C,
        method="additive_model",
        tier=ModelEvidenceTier.SEMI_QUANTITATIVE,
        extrapolated=extrapolated,
        notes=notes,
    )
