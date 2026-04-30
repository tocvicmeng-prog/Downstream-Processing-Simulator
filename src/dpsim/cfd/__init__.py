"""CFD-PBE coupling for DPSim M1.

Spatially-resolved ε-field forcing for the Alopaeus breakage kernel,
sourced from OpenFOAM CFD runs. Refines DSD predictions for the
100 mL → 1 L scale-up trajectory.

Status: scaffolding. CAD geometry handoff complete (cad/output/);
CFD pipeline and PBE coupling are TODO. See cad/cfd/README.md.
"""
__all__ = [
    "zonal_pbe",
    "openfoam_io",
]
