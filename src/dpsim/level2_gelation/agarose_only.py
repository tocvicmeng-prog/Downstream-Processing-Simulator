"""v9.2 M0b A2.2 — Agarose-only thermal-gelation solver.

A chitosan-free agarose bead is a strict subset of the AGAROSE_CHITOSAN
parameter space: the agarose helix-coil transition is independent of
the chitosan amine network. Concretely, the existing v9.1 empirical
gelation kernel (``solve_gelation_empirical`` in ``solver.py``) already
handles ``c_chitosan = 0`` — it just produces a result without a
chitosan secondary network contribution to G_DN.

Therefore this module is a thin **adapter** that:

  1. Validates the polymer family is AGAROSE.
  2. Delegates to the existing legacy solver with chitosan zeroed.
  3. Tags the result with ``model_tier = "agarose_only_thermal_v9_2"``
     and a ModelManifest indicating the calibration baseline is the
     same as the agarose-chitosan composite (CALIBRATED_LOCAL tier:
     calibration is for the composite system; agarose-only is a strict
     subset of that calibration).

This preserves bit-for-bit numerical equivalence with the legacy path
when called with the same agarose concentration and thermal profile —
the golden-master invariant for A2.2.

References
----------
Manno et al. (2014) *Carbohydr. Polym.* 113:574 — agarose helix-coil
    thermal transition; T_gel ≈ 30–40 °C depending on agarose type.
Cytiva Sepharose Application Note — chitosan-free agarose bead
    (Sepharose 4B, 6B) thermal gelation profile.
"""

from __future__ import annotations

import logging
from dataclasses import replace as dataclass_replace
from typing import TYPE_CHECKING

from ..datatypes import (
    GelationResult,
    GelationTimingResult,
    MaterialProperties,
    ModelEvidenceTier,
    ModelManifest,
    PolymerFamily,
    SimulationParameters,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def solve_agarose_only_gelation(
    params: SimulationParameters,
    props: MaterialProperties,
    R_droplet: float = 1.0e-6,
    mode: str = "empirical",
    timing: GelationTimingResult | None = None,
) -> GelationResult:
    """Solve agarose-only thermal gelation.

    Delegates to the legacy ``solve_gelation`` with chitosan parameters
    zeroed, then re-tags the result with v9.2 metadata.

    Parameters
    ----------
    params, props : SimulationParameters, MaterialProperties
        Same contract as legacy solver.
    R_droplet : float
        Microsphere radius [m].
    mode : str
        Solver mode (``"empirical"`` is the only validated mode for
        agarose-only in v9.2).
    timing : GelationTimingResult, optional
        Optional pre-computed L2a timing. Same contract as legacy.

    Returns
    -------
    GelationResult
        With ``model_tier = "agarose_only_thermal_v9_2"`` and a
        ModelManifest at CALIBRATED_LOCAL tier (calibration source is
        the AGAROSE_CHITOSAN baseline; agarose-only is a strict subset).

    Notes
    -----
    Per CLAUDE.md, polymer family is compared by ``.value`` to
    survive Streamlit reload-time enum-class minting.
    """
    if props.polymer_family.value != PolymerFamily.AGAROSE.value:
        raise ValueError(
            f"solve_agarose_only_gelation requires polymer_family=AGAROSE, "
            f"got {props.polymer_family.value!r}"
        )

    # Defensive: chitosan must be zero. c_chitosan lives on
    # ``params.formulation``, not on ``props``. We do NOT mutate the
    # user's params; we apply the constraint inside a sandboxed copy.
    if params.formulation.c_chitosan != 0:
        logger.warning(
            "AGAROSE family received c_chitosan=%.3g (expected 0); "
            "zeroing for solver call. Original params not mutated.",
            params.formulation.c_chitosan,
        )

    # Make sandboxed copies with chitosan zeroed and DDA neutralised.
    formulation_sandbox = dataclass_replace(
        params.formulation, c_chitosan=0.0,
    )
    params_sandbox = dataclass_replace(params, formulation=formulation_sandbox)
    props_sandbox = dataclass_replace(props, DDA=0.0)

    # Defer import to avoid circular import at package load time.
    from .solver import solve_gelation

    # Delegate to the legacy solver. Bit-for-bit equivalence with
    # AGAROSE_CHITOSAN(c_chitosan=0) follows because we delegate to the
    # exact same code path.
    result = solve_gelation(
        params=params_sandbox,
        props=props_sandbox,
        R_droplet=R_droplet,
        mode=mode,
        timing=timing,
    )

    # Re-tag the manifest with v9.2 provenance.
    new_manifest = ModelManifest(
        model_name="L2.agarose_only.thermal_v9_2",
        evidence_tier=ModelEvidenceTier.CALIBRATED_LOCAL,
        # B-1c (W-007): operating envelope inherited from the AGAROSE_CHITOSAN
        # baseline calibration with c_chitosan=0. Outside this envelope the
        # delegate solver may extrapolate but the tier should degrade.
        valid_domain={
            "c_agarose_pct_w_v": (1.0, 8.0),
            "T_C": (4.0, 50.0),
            "pH": (5.0, 9.0),
            "ionic_strength_M": (0.0, 0.5),
        },
        calibration_ref=(
            result.model_manifest.calibration_ref
            if result.model_manifest is not None
            else "AGAROSE_CHITOSAN_baseline"
        ),
        assumptions=[
            "Chitosan-free agarose bead is a strict subset of the "
            "AGAROSE_CHITOSAN parameter space (Manno 2014).",
            "Thermal helix-coil gelation only; no covalent secondary "
            "network unless an explicit M2 step requests it.",
            "Calibration source: AGAROSE_CHITOSAN baseline with "
            "c_chitosan=0; tier is CALIBRATED_LOCAL because the "
            "calibration was performed on the composite system.",
        ],
        diagnostics={
            "polymer_family": "agarose",
            "c_agarose": float(formulation_sandbox.c_agarose),
            "c_chitosan": 0.0,
            "DDA": 0.0,
            "delegate_model_tier": result.model_tier,
        },
    )

    # Replace manifest and tag the model_tier string.
    out = dataclass_replace(
        result,
        model_tier="agarose_only_thermal_v9_2",
        model_manifest=new_manifest,
    )
    return out


__all__ = ["solve_agarose_only_gelation", "AGAROSE_REFERENCE_PARAMETERS"]


# ─── M1 B1.1 — Reference parameter set for Sepharose-class beads ───────
#
# Anchors the M1 acceptance test (IgG coupling on CNBr-activated
# Sepharose 4B). Each entry carries gelation, mechanical, and pore-size
# parameters with peer-reviewed citations.

AGAROSE_REFERENCE_PARAMETERS: dict[str, dict] = {
    "agarose_4pct": {
        "c_agarose_kg_m3": 40.0,        # 4 % w/v
        "T_gel_K": 309.15,              # 36 °C
        "young_modulus_Pa": 30000.0,     # ~30 kPa for Sepharose 4B
        "pore_size_mean_nm": 30.0,       # exclusion limit ~ 70 nm (globular)
        "porosity": 0.94,
        "references": [
            "Manno et al. (2014) Carbohydr. Polym. 113:574 — agarose "
            "thermal helix-coil transition and concentration-modulus "
            "scaling.",
            "Cytiva Sepharose 4B Application Note (formerly GE Healthcare "
            "Life Sciences) — bead Young modulus and exclusion limit.",
        ],
    },
    "agarose_6pct": {
        "c_agarose_kg_m3": 60.0,        # 6 % w/v
        "T_gel_K": 311.15,              # 38 °C — slightly higher than 4%
        "young_modulus_Pa": 90000.0,     # ~90 kPa for Sepharose 6B (3× stiffer)
        "pore_size_mean_nm": 18.0,       # tighter mesh
        "porosity": 0.90,
        "references": [
            "Manno et al. (2014) Carbohydr. Polym. 113:574.",
            "Cytiva Sepharose 6B Application Note — exclusion limit "
            "and pressure-flow performance.",
        ],
    },
}
