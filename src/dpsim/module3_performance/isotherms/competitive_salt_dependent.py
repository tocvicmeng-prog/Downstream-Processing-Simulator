"""Multi-component salt-modulated competitive Langmuir adapter.

B-2m / W-042 — v0.8.2. Multi-component analogue of
:class:`dpsim.module3_performance.isotherms.salt_dependent.SaltModulatedLangmuir`.

Each component carries its own characteristic-charge ν_i, applied
component-wise to the competitive-Langmuir K_L:

    K_L_i(c_salt) = K_L_i_ref · (c_salt_ref / c_salt) ** ν_i

The shared denominator of competitive Langmuir then propagates the
modulation across components — at high salt the strongly-bound
components elute first because their (c_ref/c_salt)^ν_i shrinks
faster than weakly-bound species. This is the textbook IEX
displacement train, captured at SEMI_QUANTITATIVE precision without
requiring the full SMA per-rhs solve.

Use when:

* Multiple proteins co-elute and you need their relative retention
  shifts as salt rises.
* Each protein's ν has been fitted (or guessed from
  charge-z proxies) but σ has not.

Promote to :class:`dpsim.module3_performance.isotherms.sma.SMAIsotherm`
when steric shielding matters or saturation is approached.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Union

import numpy as np

from dpsim.datatypes import ModelEvidenceTier
from dpsim.module3_performance.isotherms.competitive_langmuir import (
    CompetitiveLangmuirIsotherm,
)
from dpsim.module3_performance.isotherms.salt_dependent import (
    salt_modulation_factor,
)


_C_SALT_REF_MOL_M3: float = 150.0
_NU_FLOOR: float = 0.0
_NU_CEILING: float = 20.0


@dataclass(frozen=True)
class SaltModulatedCompetitiveLangmuir:
    """Competitive Langmuir + per-component salt modulation.

    Attributes
    ----------
    base :
        Underlying ``CompetitiveLangmuirIsotherm`` providing q_max
        and K_L per component at the reference salt.
    nu :
        Per-component characteristic-charge array, shape ``(n_comp,)``.
        Each entry behaves like ν in the single-component case from
        ADR-005. Default builds from ``np.full(n_comp, 4.5)``.
    c_salt_ref_mol_m3 :
        Reference salt at which ``base.K_L`` was fitted.
    calibrated_locally :
        Tier promotion flag, mirrors the single-component adapter.
    """

    base: CompetitiveLangmuirIsotherm
    nu: np.ndarray = field(default_factory=lambda: np.array([]))
    c_salt_ref_mol_m3: float = _C_SALT_REF_MOL_M3
    calibrated_locally: bool = False

    def __post_init__(self) -> None:
        # Resolve default ν per component if user didn't pass one.
        nu = np.asarray(self.nu, dtype=float)
        if nu.size == 0:
            nu = np.full(self.base.n_components, 4.5, dtype=float)
        if nu.shape != (self.base.n_components,):
            raise ValueError(
                f"nu shape {nu.shape} must equal (n_comp,) "
                f"= ({self.base.n_components},)."
            )
        # frozen=True: mutate via object.__setattr__.
        object.__setattr__(self, "nu", nu)

    @property
    def q_max(self) -> np.ndarray:
        """Pass-through to the base isotherm."""
        return self.base.q_max

    @property
    def n_components(self) -> int:
        return self.base.n_components

    @property
    def evidence_tier(self) -> ModelEvidenceTier:
        if self.calibrated_locally:
            return ModelEvidenceTier.CALIBRATED_LOCAL
        return ModelEvidenceTier.SEMI_QUANTITATIVE

    def equilibrium_loading(
        self,
        C: Union[np.ndarray, list, float],
        c_salt_mol_m3: Optional[float] = None,
    ) -> np.ndarray:
        """Multi-component q* with per-component salt modulation.

        Implements:

            K_L_i(c_salt) = K_L_i_ref · (c_salt_ref / c_salt) ** ν_i
            q_i = q_max_i · K_L_i(c_salt) · C_i / (1 + Σ K_L_j(c_salt) · C_j)

        When ``c_salt_mol_m3 is None`` the adapter degenerates to the
        bare competitive Langmuir — preserves the legacy
        ``isotherm.equilibrium_loading(C)`` calling convention.
        """
        C_arr = np.asarray(C, dtype=float)
        if c_salt_mol_m3 is None:
            return self.base.equilibrium_loading(C_arr)

        # Build per-component salt-modulated K_L vector.
        factors = np.array(
            [
                salt_modulation_factor(
                    c_salt_mol_m3,
                    c_salt_ref_mol_m3=self.c_salt_ref_mol_m3,
                    nu=float(nu_i),
                )
                for nu_i in self.nu
            ],
            dtype=float,
        )
        K_modulated = self.base.K_L * factors

        # Reproduce the competitive-Langmuir math with K_modulated in
        # place of K_L. We don't mutate base.K_L — instead, write the
        # math out so the adapter is read-only against the base.
        if C_arr.ndim == 1:
            C_safe = np.maximum(C_arr, 0.0)
            denom = 1.0 + np.dot(K_modulated, C_safe)
            q = self.base.q_max * K_modulated * C_safe / denom
        else:
            C_safe = np.maximum(C_arr, 0.0)
            denom = 1.0 + np.einsum("i,ij->j", K_modulated, C_safe)
            q = (
                self.base.q_max[:, np.newaxis]
                * K_modulated[:, np.newaxis]
                * C_safe
            ) / denom[np.newaxis, :]
        return q

    def validate(self) -> list[str]:
        errors: list[str] = []
        for i, nu_i in enumerate(self.nu):
            if nu_i < _NU_FLOOR or nu_i > _NU_CEILING:
                errors.append(
                    f"nu[{i}]={float(nu_i)} outside "
                    f"[{_NU_FLOOR}, {_NU_CEILING}]."
                )
        if self.c_salt_ref_mol_m3 <= 0.0:
            errors.append(
                f"c_salt_ref_mol_m3={self.c_salt_ref_mol_m3} must be > 0."
            )
        return errors


__all__ = ["SaltModulatedCompetitiveLangmuir"]
