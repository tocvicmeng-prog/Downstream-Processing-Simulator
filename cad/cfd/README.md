# DPSim CFD-PBE Coupling — OpenFOAM Pipeline

Scaffolding for the spatially-resolved ε-field CFD-PBE coupling that refines
DPSim's M1 breakage-kernel predictions for the 100 mL → 1 L scale-up
trajectory (per 2026-05-01 user direction).

**Status**: Scaffold only. CAD geometry handoff complete (`cad/output/`).
CFD case setup, mesh, solver runs, and PBE coupling are TODO.

**Data contract**: The `zones.json` schema between `extract_epsilon.py`
(OpenFOAM-side) and `src/dpsim/cfd/zonal_pbe.py` (DPSim-side) is locked at
v1.0 — see [`zones_schema.md`](zones_schema.md) for the field-by-field
specification, validation rules, and worked Stirrer A / Stirrer B examples.

---

## Pipeline overview

```
cad/output/*.step   →  cad/cfd/cases/*/  →  snappyHexMesh  →  pimpleDyMFoam (sliding mesh)
                                                                     │
                                                                     ▼
                                                           ε(x), |γ̇|(x), zone partitioning
                                                                     │
                                                                     ▼
                                              src/dpsim/cfd/zonal_pbe.py (CFD-PBE coupling)
                                                                     │
                                                                     ▼
                                                            DPSim M1 → DSD with spatial ε
```

## Scope (from the Scientific Advisor analysis)

- **Approach**: CFD-PBE one-way coupling (NOT full multiphase VOF — that's
  not viable at tank scale for double emulsions; see `scientific-advisor`
  conversation 2026-05-01).
- **Solver**: OpenFOAM (open-source, scriptable, good Python integration
  via PyFoam / fluidfoam).
- **Turbulence**: RANS k-ω SST. LES is the gold standard but ~100× more
  expensive; not justified for 10× scale-up validation.
- **Mesh**: ~5–20 M cells. Resolved impeller swept volume + stator slot
  geometry (Stirrer B). Prism layers on rotor and stator surfaces.
- **Multiphase handling**: Single-phase or low-φ Eulerian-Eulerian.
  Continuous-phase ε field is the deliverable — the PBE solver in DPSim's
  `level1_emulsification/` already handles the dispersed phase.

## Expected effort

~1-2 person-months for a CFD engineer with prior OpenFOAM stirred-tank
experience. Not a multi-year research project. Validation requires one PIV
measurement campaign at the bench scale (one representative RPM per
stirrer) — without PIV, the CFD has a CFD-shaped opinion, not a validation.

## Directory structure

```
cad/cfd/
├── README.md (this file)
├── cases/
│   ├── stirrer_A_beaker_100mL/    # Stirrer A in glass beaker, 100 mL
│   │   ├── 0.org/                 # initial conditions (TODO)
│   │   ├── constant/              # mesh, turbulence, transport (TODO)
│   │   └── system/                # blockMesh, snappyHexMesh, fvSchemes,
│   │                              #   fvSolution, controlDict (TODO)
│   └── stirrer_B_beaker_100mL/    # Stirrer B in glass beaker, 100 mL
│       └── (same structure as above)
└── scripts/
    ├── prepare_geometry.sh         # convert STEP → STL for snappyHexMesh
    ├── run_case.sh                 # mesh + solve pipeline
    └── extract_epsilon.py          # post-process ε field → zonal model

src/dpsim/cfd/
├── __init__.py
├── zonal_pbe.py                    # CFD-PBE coupling: ε(x) → PBE forcing
└── openfoam_io.py                  # OpenFOAM dictionary read/write helpers
```

## TODO (CFD pipeline)

1. **Geometry preparation** (1 day)
   - [ ] `prepare_geometry.sh`: assemble stirrer + beaker in correct
         insertion depth (mid-plane at ~50% liquid height for double
         emulsions; verify with user)
   - [ ] STEP → STL conversion for snappyHexMesh input
   - [ ] Define rotating zone (impeller swept volume) and static zone
         (vessel interior) for sliding-mesh setup

2. **Mesh generation** (3-5 days)
   - [ ] `system/blockMeshDict`: background hex mesh covering the beaker
         volume
   - [ ] `system/snappyHexMeshDict`: castellated mesh + snap + layer
         addition. Refinement levels:
     - Level 5-6 on impeller surfaces (~0.1 mm cells)
     - Level 4 on stator perforation slots (Stirrer B only, ~0.2 mm)
     - Level 2-3 in bulk (~1-2 mm)
   - [ ] Prism layers (5-7 layers, expansion ratio 1.2) on impeller and
         stator surfaces
   - [ ] Verify mesh quality: max non-orthogonality < 65°, max skewness
         < 4, aspect ratio < 100

3. **Solver setup** (2-3 days)
   - [ ] `constant/transportProperties`: continuous phase viscosity for
         polysaccharide solutions (use DPSim's calibrated rheology from
         `level1_emulsification/rheology.py`)
   - [ ] `constant/turbulenceProperties`: kOmegaSST
   - [ ] `constant/dynamicMeshDict`: sliding-mesh setup with rotating
         zone tied to impeller AMI (Arbitrary Mesh Interface)
   - [ ] `0.org/`: U, p, k, omega, nut initial conditions
   - [ ] `system/fvSchemes`: 2nd-order upwind for advection, central for
         diffusion
   - [ ] `system/fvSolution`: PIMPLE with 2 outer correctors, residual
         tolerance 1e-5
   - [ ] `system/controlDict`: deltaT 1e-4 s, write interval 0.1 s,
         end time 5-10 s (covers ~10-50 impeller rotations)

4. **Run and post-process** (1-2 days)
   - [ ] `run_case.sh`: execute the pipeline (blockMesh → snappyHexMesh
         → decomposePar → pimpleDyMFoam → reconstructPar)
   - [ ] Parallelization: 8-32 cores depending on workstation
   - [ ] `extract_epsilon.py`: extract time-averaged ε(x) field, partition
         into compartments (impeller / near-wall / bulk zones), output
         JSON with zone volumes and zone-averaged ε

5. **PBE coupling** (5-7 days)
   - [ ] `src/dpsim/cfd/zonal_pbe.py`: read CFD JSON, build compartment
         model, integrate PBE on each zone with zone-specific ε, exchange
         droplets between zones via convective flow rates
   - [ ] CLI integration: `dpsim run --cfd-zones cad/cfd/cases/.../zones.json`
   - [ ] Compatibility with existing `calibration_store` and Monte Carlo
         driver

6. **Validation** (1 week + bench measurement campaign)
   - [ ] **PIV measurement** at one RPM per stirrer (bench scale, water
         only). Required gate before trusting CFD.
   - [ ] Compare CFD U field against PIV: target ±15% in impeller swept
         volume, ±25% in bulk
   - [ ] Bench DSD time-series comparison: predicted vs. measured d_50
         and d_90 across 4-6 RPM × 2 φ_d × 2 surfactant levels
   - [ ] Document the validation envelope: what range of conditions can
         be extrapolated with confidence?

7. **Scale-up extrapolation** (2 weeks)
   - [ ] Repeat CFD-PBE for 1 L vessel geometry (geometric similarity:
         scale Stirrer B by 2.15× linear, or use larger commercial
         impeller — TBD with user)
   - [ ] Predict DSD at 1 L; flag uncertainty due to extrapolation
   - [ ] Identify any operating regimes where bench calibration is
         required before trusting predictions

## Critical caveats (from Scientific Advisor 2026-05-01)

- **Stator slot geometry matters for Stirrer B**: 80-95% of breakage in
  rotor-stator devices happens in slot exit jets (Padron 2005, Hall 2011).
  The 24 columns × 3 rows (72 holes) perforation pattern has been measured and applied
  to the CAD; CFD must resolve it (mesh refinement level 4+).
- **Viscous correction**: polysaccharide continuous phases have
  viscosity 5-50× water. The Alopaeus kernel's viscous sub-range
  correction is critical and is already in DPSim's
  `level1_emulsification/breakage.py`. Verify it engages correctly when
  fed CFD-resolved ε.
- **PIV is non-negotiable**: without flow-field measurement at the
  bench scale, the CFD provides relative differences (e.g., between
  Stirrer A and B at the same RPM) but not absolute ε accuracy. Don't
  use unvalidated CFD for the 1 L scale-up decision.

## References

- Alopaeus V., Koskinen J., Keskinen K. I., Majander J. (2002).
  *Simulation of the population balances for liquid-liquid systems in a
  nonideal stirred tank.* Chem. Eng. Sci. 57, 1815-1825.
- Padron G. (2005). *Effect of surfactants on drop size distribution in
  a batch, rotor-stator mixer.* PhD thesis, U. of Maryland.
- Wang T., Mao Z.-S. (2005). *CFD-PBE coupling for stirred tanks.*
  Chem. Eng. Sci. 60, 4501-4516.
- Hall S., Cooke M., Pacek A. W., Kowalski A. J., Rothman D. (2011).
  *Scaling-up of silverson rotor-stator mixers.* Can. J. Chem. Eng. 89,
  1040-1050.
