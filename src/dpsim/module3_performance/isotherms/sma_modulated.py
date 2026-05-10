"""Single-component SMA promotion adapter.

B-1n / W-039 — v0.8.2. Per ADR-006, ships the swap-in promotion target
for ``SaltModulatedLangmuir`` (ADR-005). Same call signature
(``equilibrium_loading(C, c_salt_mol_m3)``) so consumers can promote
without touching the time-domain solver. Internally invokes the full
:class:`dpsim.module3_performance.isotherms.sma.SMAIsotherm` fixed-point
solve at every call.

Use when:

* Bound ``q`` approaches the ionic capacity ``Lambda`` (saturation).
* Steric shielding ``σ`` has been fitted.
* The bare Mollerup-simplified form is missing fidelity that wet-lab
  data demonstrates.

Otherwise stick with ``SaltModulatedLangmuir`` — ADR-006 documents the
cost / precision tradeoff.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Union

import numpy as np

from dpsim.datatypes import ModelEvidenceTier
from dpsim.module3_performance.isotherms.sma import SMAIsotherm


# ─── Defaults ──────────────────────────────────────────────────────────────


_C_SALT_REF_MOL_M3: float = 150.0
_C_SALT_FLOOR_MOL_M3: float = 1.0e-6


@dataclass(frozen=True)
class SaltModulatedSMA:
    """Single-component facade over the multi-component ``SMAIsotherm``.

    Constructor exposes the SMA parameters directly (z, σ, K_eq, Λ)
    so the additional calibration burden vs ``SaltModulatedLangmuir``
    is visible at the call site.

    Attributes
    ----------
    z :
        Characteristic charge of the protein (analogous to ν in the
        Mollerup-simplified form). Default 4.5 — same anchor as
        ADR-005.
    sigma :
        Steric shielding factor. Default 50.0 — typical mid-size IgG.
        SET THIS to your fitted value once wet-lab calibration is
        available; ``σ = 0`` makes SMA fidelity-equivalent to the
        Mollerup-simplified form (no benefit from the SMA cost).
    K_eq :
        Equilibrium constant in SMA's dimensionless convention.
    Lambda :
        Total ionic capacity of the resin [mol/m³ solid]. Default
        1000.0 — typical for strong-cation-exchange resins.
    c_salt_ref_mol_m3 :
        Reference salt concentration. Default 150 mM PBS.
    calibrated_locally :
        Tier promotion flag, mirrors ``SaltModulatedLangmuir``.
    """

    z: float = 4.5
    sigma: float = 50.0
    K_eq: float = 1.0e-3
    Lambda: float = 1000.0
    c_salt_ref_mol_m3: float = _C_SALT_REF_MOL_M3
    calibrated_locally: bool = False

    @property
    def q_max(self) -> float:
        """Capacity ceiling: ``Λ / (z + σ)`` in the single-component limit.

        At full saturation, ``q · (z + σ) = Λ`` — this gives the
        per-component ceiling. Useful as a sanity check that the
        operating point is in the dilute regime where Mollerup-simplified
        would have been sufficient.
        """
        return self.Lambda / (self.z + self.sigma)

    @property
    def evidence_tier(self) -> ModelEvidenceTier:
        if self.calibrated_locally:
            return ModelEvidenceTier.CALIBRATED_LOCAL
        return ModelEvidenceTier.SEMI_QUANTITATIVE

    def _underlying(self) -> SMAIsotherm:
        """Single-component SMAIsotherm built from this adapter's params."""
        return SMAIsotherm(
            Lambda=self.Lambda,
            z=np.array([self.z]),
            sigma=np.array([self.sigma]),
            K_eq=np.array([self.K_eq]),
        )

    def equilibrium_loading(
        self,
        C: Union[np.ndarray, float],
        c_salt_mol_m3: Optional[float] = None,
    ) -> Union[np.ndarray, float]:
        """Equilibrium loading via the SMA fixed-point solve.

        When ``c_salt_mol_m3 is None`` the adapter uses the reference
        salt — degrades to the SMA equilibrium at the calibration
        point, NOT to a bare Langmuir. This matches user intent: if a
        consumer chose this adapter, they want the SMA physics even
        without a live gradient.
        """
        c_salt = (
            self.c_salt_ref_mol_m3
            if c_salt_mol_m3 is None
            else max(float(c_salt_mol_m3), _C_SALT_FLOOR_MOL_M3)
        )
        sma = self._underlying()
        C_arr = np.atleast_1d(np.asarray(C, dtype=float))
        # SMA is multi-component; we run it element-wise for arrays.
        if C_arr.size == 0:
            return np.array([])
        results = np.array(
            [
                float(sma.equilibrium_loading(np.array([float(c)]), c_salt)[0])
                for c in C_arr
            ],
            dtype=float,
        )
        return results.item() if np.isscalar(C) else results

    def jacobian(
        self,
        C: Union[np.ndarray, float],
        c_salt_mol_m3: Optional[float] = None,
        *,
        h_rel: float = 1.0e-6,
    ) -> Union[np.ndarray, float]:
        """Numerical dq*/dC by central differences.

        SMA's analytical Jacobian is non-trivial (depends on the
        converged q_salt fixed point); a numerical derivative at
        ``h_rel * |C|`` is sufficient for the BDF / LSODA solvers
        consumers use. Adjust ``h_rel`` if step-size sensitivity bites.
        """
        C_arr = np.atleast_1d(np.asarray(C, dtype=float))
        h = np.maximum(np.abs(C_arr) * h_rel, 1.0e-15)
        forward = self.equilibrium_loading(C_arr + h, c_salt_mol_m3)
        backward = self.equilibrium_loading(
            np.maximum(C_arr - h, 0.0), c_salt_mol_m3,
        )
        forward_arr = np.atleast_1d(np.asarray(forward, dtype=float))
        backward_arr = np.atleast_1d(np.asarray(backward, dtype=float))
        result = (forward_arr - backward_arr) / (2.0 * h)
        return result.item() if np.isscalar(C) else result

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.z <= 0.0 or self.z > 20.0:
            errors.append(f"z={self.z} outside (0, 20].")
        if self.sigma < 0.0 or self.sigma > 500.0:
            errors.append(f"sigma={self.sigma} outside [0, 500].")
        if self.K_eq <= 0.0:
            errors.append(f"K_eq={self.K_eq} must be > 0.")
        if self.Lambda <= 0.0:
            errors.append(f"Lambda={self.Lambda} must be > 0.")
        if self.c_salt_ref_mol_m3 <= 0.0:
            errors.append(
                f"c_salt_ref_mol_m3={self.c_salt_ref_mol_m3} must be > 0."
            )
        return errors


__all__ = ["SaltModulatedSMA"]
