"""Salt-modulated Langmuir adapter (Mollerup-simplified / SDM equivalent).

B-1j / W-034 — v0.8.1. Per ADR-005, the canonical formulation for the
single-component dilute IEX regime is:

    K_a(c_salt) = K_a_ref · (c_salt_ref / c_salt) ** ν

Functionally identical to the Stoichiometric Displacement Model
(Velayudhan & Horváth 1986) in the dilute limit; functionally identical
to Mollerup's framework when activity coefficients γ ≈ 1. The full
Steric Mass Action solver
(:class:`dpsim.module3_performance.isotherms.sma.SMAIsotherm`) is the
documented promotion target once wet-lab ν / σ data warrants per-rhs
fixed-point cost.

Wire-in pattern (from `method.py::run_loaded_state_elution`)
------------------------------------------------------------

The rhs mirrors the existing ``_protein_a_elution_suppression`` shape:
the isotherm computes equilibrium loading at the protein-A pH, then
the salt modulator multiplies the result by a dimensionless factor.
When no salt gradient is active, the factor is 1.0 — preserving every
non-salt elution path bit-for-bit.

Tier ladder
-----------

* No ``c_salt_ref_mol_m3`` / ``nu`` calibration → ``SEMI_QUANTITATIVE``
  (literature-anchored defaults: ν = 4.5, c_salt_ref = 150 mM).
* ``calibrated_locally = True`` (set by callers that fit ν against
  manufacturer or wet-lab data) → ``CALIBRATED_LOCAL``.
* If ν is fitted against a wet-lab holdout per the same protein-resin
  pair → ``VALIDATED_QUANTITATIVE``. Caller responsibility to set the
  flag; this module does not run statistical tests.

The default constants follow ADR-005 §"Why ν = 4.5 is the literature
default" + §"Why c_salt_ref = 150 mM".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Union

import numpy as np

from dpsim.datatypes import ModelEvidenceTier
from dpsim.module3_performance.isotherms.langmuir import LangmuirIsotherm


# ─── Literature-anchored defaults (ADR-005 §"defaults") ─────────────────────


_NU_DEFAULT: float = 4.5            # characteristic charge for ~50 kDa IgG-class
_C_SALT_REF_MOL_M3: float = 150.0   # 150 mM ≈ phosphate-buffered saline reference
_C_SALT_FLOOR_MOL_M3: float = 1.0e-6  # avoid divide-by-zero on c_salt_t=0
_NU_FLOOR: float = 0.0
_NU_CEILING: float = 20.0


# ─── Pure modulation factor (testable without an isotherm) ──────────────────


def salt_modulation_factor(
    c_salt_mol_m3: float,
    *,
    c_salt_ref_mol_m3: float = _C_SALT_REF_MOL_M3,
    nu: float = _NU_DEFAULT,
) -> float:
    """Mollerup-simplified K_a modulator: ``(c_ref / c_salt) ** ν``.

    Returns the dimensionless factor by which the bare Langmuir K_a
    should be scaled at the current salt concentration.

    Asymptotics:

    * ``c_salt_mol_m3 == c_salt_ref_mol_m3`` → factor = 1.0
      (the reference state where the bare K_a applies as-fitted).
    * ``c_salt_mol_m3 < c_salt_ref_mol_m3`` → factor > 1
      (low-salt buffer enhances binding, the typical IEX **load** state).
    * ``c_salt_mol_m3 > c_salt_ref_mol_m3`` → factor < 1
      (high-salt buffer drives elution).

    A floor at 1×10⁻⁶ mol·m⁻³ on ``c_salt_mol_m3`` prevents divide-by-zero
    when callers pass 0 for "salt-free water"; the resulting factor is
    enormous but finite, which is the physically correct extrapolation
    (binding is irreversible in the absence of the displacing ion).
    """
    if nu < _NU_FLOOR or nu > _NU_CEILING:
        raise ValueError(
            f"nu={nu!r} outside [{_NU_FLOOR}, {_NU_CEILING}]. Typical "
            f"protein characteristic charges fall in [2, 8]."
        )
    if c_salt_ref_mol_m3 <= 0.0:
        raise ValueError(
            f"c_salt_ref_mol_m3={c_salt_ref_mol_m3!r} must be > 0."
        )
    c = max(float(c_salt_mol_m3), _C_SALT_FLOOR_MOL_M3)
    return (float(c_salt_ref_mol_m3) / c) ** float(nu)


# ─── Adapter dataclass ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class SaltModulatedLangmuir:
    """Adapter that wraps a base Langmuir isotherm with salt-dependent K_a.

    Attributes
    ----------
    base :
        Underlying single-component ``LangmuirIsotherm`` providing q_max
        and the reference-state K_L.
    nu :
        Characteristic charge per Mollerup / SDM. Default 4.5 (mid-range
        of the 30–60 kDa protein band).
    c_salt_ref_mol_m3 :
        Reference salt concentration at which ``base.K_L`` was fitted
        (or is assumed to apply). Default 150 mM PBS-equivalent.
    calibrated_locally :
        Set ``True`` by callers that have fit ν against their own
        protein-resin pair (e.g. via the calibration_store path). Drives
        ``evidence_tier`` from ``SEMI_QUANTITATIVE`` to ``CALIBRATED_LOCAL``.
        Default ``False``.
    """

    base: LangmuirIsotherm
    nu: float = _NU_DEFAULT
    c_salt_ref_mol_m3: float = _C_SALT_REF_MOL_M3
    calibrated_locally: bool = False

    @property
    def q_max(self) -> float:
        """Pass-through to the base isotherm — q_max is salt-independent."""
        return self.base.q_max

    @property
    def evidence_tier(self) -> ModelEvidenceTier:
        """Tier ladder per ADR-005."""
        if self.calibrated_locally:
            return ModelEvidenceTier.CALIBRATED_LOCAL
        return ModelEvidenceTier.SEMI_QUANTITATIVE

    def equilibrium_loading(
        self,
        C: Union[np.ndarray, float],
        c_salt_mol_m3: Optional[float] = None,
    ) -> Union[np.ndarray, float]:
        """Equilibrium loading with optional salt modulation.

        When ``c_salt_mol_m3`` is None the adapter degenerates to the
        bare Langmuir (factor 1.0) — preserves the existing
        ``isotherm.equilibrium_loading(C)`` calling convention used by
        callers that don't yet thread the salt envelope.

        When ``c_salt_mol_m3`` is supplied, the bare loading is
        multiplied by :func:`salt_modulation_factor` evaluated at the
        adapter's calibration parameters.
        """
        bare = self.base.equilibrium_loading(C)
        if c_salt_mol_m3 is None:
            return bare
        factor = salt_modulation_factor(
            c_salt_mol_m3,
            c_salt_ref_mol_m3=self.c_salt_ref_mol_m3,
            nu=self.nu,
        )
        return bare * factor

    def jacobian(
        self,
        C: Union[np.ndarray, float],
        c_salt_mol_m3: Optional[float] = None,
    ) -> Union[np.ndarray, float]:
        """dq*/dC, salt-modulated. Delegates to the base Jacobian.

        Justification: K_a-modulation appears as a multiplicative
        constant on q*, not on C, so the Jacobian shares the same
        salt factor. Callers that solve linearly-implicit time-stepping
        schemes against this adapter consume the salt-modulated
        Jacobian directly.
        """
        bare_j = self.base.jacobian(C)
        if c_salt_mol_m3 is None:
            return bare_j
        factor = salt_modulation_factor(
            c_salt_mol_m3,
            c_salt_ref_mol_m3=self.c_salt_ref_mol_m3,
            nu=self.nu,
        )
        return bare_j * factor

    def validate(self) -> list[str]:
        """Range-check the adapter parameters."""
        errors: list[str] = list(self.base.validate())
        if self.nu < _NU_FLOOR or self.nu > _NU_CEILING:
            errors.append(
                f"nu={self.nu} outside [{_NU_FLOOR}, {_NU_CEILING}]."
            )
        if self.c_salt_ref_mol_m3 <= 0.0:
            errors.append(
                f"c_salt_ref_mol_m3={self.c_salt_ref_mol_m3} must be > 0."
            )
        return errors


__all__ = [
    "SaltModulatedLangmuir",
    "salt_modulation_factor",
]
