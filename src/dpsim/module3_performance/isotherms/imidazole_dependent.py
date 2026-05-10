"""Imidazole-modulated Langmuir adapter for IMAC screening.

B-1m / W-038 — v0.8.2. Companion to ``salt_dependent.py`` for IMAC.

The full :class:`dpsim.module3_performance.isotherms.imac.IMACCompetitionIsotherm`
formulates IMAC as competitive Langmuir between the His-tagged
protein and imidazole at the same metal-chelate sites — strictly more
capable, requires both K_protein and K_imidazole. For *screening* runs
where the user only has a single-component K_d for the protein and
wants to layer an imidazole-driven elution effect on top, this thin
adapter ships the equivalent of ADR-005's Mollerup-simplified form:

    K_a(c_imidazole) = K_a_ref · (c_imid_ref / c_imidazole) ** n

where ``n`` is the protein's effective characteristic charge in the
metal-chelate competition (typically 1–3 for His-tagged proteins on
Ni-NTA / Co-NTA at 50 mM imidazole reference). The full
``IMACCompetitionIsotherm`` remains the canonical promotion path
when multi-species competition matters — e.g. quantifying tail-fraction
elution profiles or imidazole carryover into late-eluting fractions.

Tier ladder mirrors :mod:`dpsim.module3_performance.isotherms.salt_dependent`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Union

import numpy as np

from dpsim.datatypes import ModelEvidenceTier
from dpsim.module3_performance.isotherms.langmuir import LangmuirIsotherm


# ─── Literature-anchored defaults ───────────────────────────────────────────


_N_DEFAULT: float = 1.5             # mid-range for His6 on Ni-NTA
_C_IMIDAZOLE_REF_MOL_M3: float = 50.0  # 50 mM ≈ standard load-buffer reference
_C_IMIDAZOLE_FLOOR_MOL_M3: float = 1.0e-6
_N_FLOOR: float = 0.0
_N_CEILING: float = 10.0


# ─── Pure modulation factor ─────────────────────────────────────────────────


def imidazole_modulation_factor(
    c_imidazole_mol_m3: float,
    *,
    c_imidazole_ref_mol_m3: float = _C_IMIDAZOLE_REF_MOL_M3,
    n: float = _N_DEFAULT,
) -> float:
    """``(c_ref / c_imidazole) ** n`` modulation factor.

    Asymptotics:

    * ``c_imidazole = c_ref`` → factor = 1.0 (reference state).
    * ``c_imidazole < c_ref`` → factor > 1 (low-imidazole load buffer
      enhances binding — the typical IMAC **load** state).
    * ``c_imidazole > c_ref`` → factor < 1 (imidazole step / gradient
      drives elution).

    Floor at 1×10⁻⁶ mol·m⁻³ on the input prevents divide-by-zero;
    callers passing 0 for "imidazole-free buffer" get a finite-but-large
    factor, which is the physically correct extrapolation (no
    competitor → near-irreversible binding).
    """
    if n < _N_FLOOR or n > _N_CEILING:
        raise ValueError(
            f"n={n!r} outside [{_N_FLOOR}, {_N_CEILING}]. Typical "
            f"His6-tag on Ni-NTA falls in [1, 3]."
        )
    if c_imidazole_ref_mol_m3 <= 0.0:
        raise ValueError(
            f"c_imidazole_ref_mol_m3={c_imidazole_ref_mol_m3!r} must be > 0."
        )
    c = max(float(c_imidazole_mol_m3), _C_IMIDAZOLE_FLOOR_MOL_M3)
    return (float(c_imidazole_ref_mol_m3) / c) ** float(n)


# ─── Adapter ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ImidazoleModulatedLangmuir:
    """Single-component Langmuir + imidazole modulator for IMAC screening.

    Attributes
    ----------
    base :
        Underlying ``LangmuirIsotherm`` (q_max, K_L) for the
        His-tagged protein at the imidazole reference.
    n :
        Effective imidazole-competition exponent. Default 1.5
        (mid-range for His6 on Ni-NTA / Co-NTA).
    c_imidazole_ref_mol_m3 :
        Reference imidazole concentration where ``base.K_L`` was
        fitted. Default 50 mM (standard IMAC load buffer).
    calibrated_locally :
        Set ``True`` by callers that have fit ``n`` against their own
        protein-resin pair. Promotes ``evidence_tier`` from
        SEMI_QUANTITATIVE to CALIBRATED_LOCAL.
    """

    base: LangmuirIsotherm
    n: float = _N_DEFAULT
    c_imidazole_ref_mol_m3: float = _C_IMIDAZOLE_REF_MOL_M3
    calibrated_locally: bool = False

    @property
    def q_max(self) -> float:
        """Pass-through to the base — capacity is imidazole-independent."""
        return self.base.q_max

    @property
    def evidence_tier(self) -> ModelEvidenceTier:
        if self.calibrated_locally:
            return ModelEvidenceTier.CALIBRATED_LOCAL
        return ModelEvidenceTier.SEMI_QUANTITATIVE

    def equilibrium_loading(
        self,
        C: Union[np.ndarray, float],
        c_imidazole_mol_m3: Optional[float] = None,
    ) -> Union[np.ndarray, float]:
        """Equilibrium loading with optional imidazole modulation.

        When ``c_imidazole_mol_m3`` is ``None`` the adapter degenerates
        to the bare Langmuir — preserving the existing
        ``isotherm.equilibrium_loading(C)`` calling convention.
        """
        bare = self.base.equilibrium_loading(C)
        if c_imidazole_mol_m3 is None:
            return bare
        factor = imidazole_modulation_factor(
            c_imidazole_mol_m3,
            c_imidazole_ref_mol_m3=self.c_imidazole_ref_mol_m3,
            n=self.n,
        )
        return bare * factor

    def jacobian(
        self,
        C: Union[np.ndarray, float],
        c_imidazole_mol_m3: Optional[float] = None,
    ) -> Union[np.ndarray, float]:
        """dq*/dC, imidazole-modulated. Same factor as ``equilibrium_loading``."""
        bare_j = self.base.jacobian(C)
        if c_imidazole_mol_m3 is None:
            return bare_j
        factor = imidazole_modulation_factor(
            c_imidazole_mol_m3,
            c_imidazole_ref_mol_m3=self.c_imidazole_ref_mol_m3,
            n=self.n,
        )
        return bare_j * factor

    def validate(self) -> list[str]:
        errors: list[str] = list(self.base.validate())
        if self.n < _N_FLOOR or self.n > _N_CEILING:
            errors.append(f"n={self.n} outside [{_N_FLOOR}, {_N_CEILING}].")
        if self.c_imidazole_ref_mol_m3 <= 0.0:
            errors.append(
                f"c_imidazole_ref_mol_m3={self.c_imidazole_ref_mol_m3} must be > 0."
            )
        return errors


__all__ = [
    "ImidazoleModulatedLangmuir",
    "imidazole_modulation_factor",
]
