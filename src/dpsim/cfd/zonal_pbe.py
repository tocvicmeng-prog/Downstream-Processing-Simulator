"""Zonal CFD-PBE coupling: feed CFD-resolved ε field into the M1 PBE solver.

Status: TODO. Replaces the volume-averaged ε in
``level1_emulsification/`` with zone-resolved ε from OpenFOAM runs (see
``cad/cfd/scripts/extract_epsilon.py``).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class CFDZone:
    """A single CFD-derived compartment for PBE integration.

    Fields populated from ``cad/cfd/scripts/extract_epsilon.py`` output JSON.
    """
    name: str
    volume_m3: float
    epsilon_W_per_kg: float            # zone-averaged dissipation rate
    epsilon_breakage_weighted: float   # weighted by g(d, ε(x))
    shear_rate_avg_s: float            # |γ̇|, used by viscous-correction
    cell_count: int = 0
    metadata: dict[str, Any] = None    # type: ignore[assignment]


@dataclass
class CFDZoneExchange:
    """Convective droplet exchange between two zones."""
    from_zone: str
    to_zone: str
    volumetric_flow_m3_s: float


def load_zones_json(path: Path) -> tuple[list[CFDZone], list[CFDZoneExchange]]:
    """Load zones and exchanges from CFD post-processing JSON."""
    raise NotImplementedError(
        "TODO: implement zones.json loader. "
        "See cad/cfd/scripts/extract_epsilon.py for the output schema."
    )


def integrate_pbe_with_zones(
    zones: list[CFDZone],
    exchanges: list[CFDZoneExchange],
    initial_dsd: Any,         # TODO: typed against level1_emulsification
    duration_s: float,
    breakage_kernel: Any = None,
) -> Any:
    """Integrate the PBE on each zone with zone-specific ε, exchanging
    droplets between zones at each timestep.

    The breakage kernel (Alopaeus, with viscous sub-range correction) is
    re-used from ``level1_emulsification/breakage.py``; this function
    drives the spatial coupling, not the kernel form itself.

    Returns the final DSD aggregated across all zones.
    """
    raise NotImplementedError(
        "TODO: integrate the CFD-PBE compartment model. "
        "See cad/cfd/README.md step 5."
    )


def consistency_check_with_volume_avg(
    zones: list[CFDZone],
    legacy_volume_avg_eps: float,
) -> dict[str, float]:
    """Sanity check: volume-weighted ε from CFD zones should equal the
    legacy volume-averaged ε (from `Po N³ D⁵ / V_swept` empirical formula)
    within ~30%. Larger discrepancy indicates CFD setup error or that the
    empirical Po/D values in `datatypes.py` need adjustment.
    """
    raise NotImplementedError(
        "TODO: cross-check CFD-derived volume-avg ε against the empirical "
        "Po-based estimate in datatypes.py."
    )
