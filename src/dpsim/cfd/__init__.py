"""CFD-PBE coupling for DPSim M1.

Spatially-resolved ε-field forcing for the Alopaeus breakage kernel,
sourced from OpenFOAM CFD runs. Refines DSD predictions for the
100 mL → 1 L scale-up trajectory.

Status: DPSim-side zonal PBE coupling is implemented in ``zonal_pbe``.
OpenFOAM-side scripts and case templates are present, but each geometry and
operating point still needs mesh, convergence, epsilon-extraction, and PIV
validation before CFD-driven predictions are used as quantitative scale-up
evidence. See cad/cfd/README.md.
"""
__all__ = [
    "zonal_pbe",
    "openfoam_io",
]
