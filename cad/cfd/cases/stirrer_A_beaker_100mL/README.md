# Stirrer A in 100 mL beaker — OpenFOAM case

Bench-scale CFD case for Stirrer A (disk-style 19-tab impeller, Ø 59 mm)
in the standard glass beaker (Ø 100 × 130 mm). Working volume 100 mL.

**Status (2026-05-01):** all dictionaries populated. Geometry preparation
and solver runs not yet executed end-to-end against a real OpenFOAM
install. Treat the dicts as a starting point that you will iterate on
against your specific OpenFOAM build, mesh-quality output, and
operating regime.

## Geometry source

- Impeller: `cad/output/stirrer_A_pitched_blade.step` (verified 2026-05-01)
- Vessel: `cad/output/beaker_100mm.step` (R=10 inner-bottom fillet, R=5
  outer-bottom fillet, 20° outward-flared rim)

## Pipeline

```
prepare_geometry.sh stirrer_A_beaker_100mL    # STEP → STL + patch labels
run_case.sh        stirrer_A_beaker_100mL --cores 8
                                              # blockMesh → snappyHexMesh
                                              # → decomposePar → pimpleDyMFoam
                                              # → reconstructPar → cellCentres
extract_epsilon.py . \                        # → schema-v1.0 zones.json
    --zones zones_config.json \
    --output zones.json \
    --case-name stirrer_A_beaker_100mL \
    --rpm 1500 --rho-c 860 --mu-c 0.05 \
    --d-ref 100e-6
```

## Dictionary contents

| Path | Contents |
|---|---|
| `system/controlDict` | pimpleDyMFoam, deltaT 1e-4, endTime 5 s, run-time field averaging from t=2 s, impeller-power forces function object |
| `system/fvSchemes` | Euler ddt, Gauss linearUpwind for U, limitedLinear for k/ω |
| `system/fvSolution` | GAMG for p, smoothSolver for U/k/ω; PIMPLE 2 outer + 2 inner correctors |
| `system/blockMeshDict` | 24×24×26 background hex (~5 mm cells), domain x,y ∈ [-0.06, 0.06], z ∈ [0, 0.13] |
| `system/snappyHexMeshDict` | level 5 on impeller surface, level 4 in `rotorZone` cylinder, 5 prism layers, mesh-quality gates per README |
| `system/decomposeParDict` | scotch, 8 subdomains |
| `constant/transportProperties` | Newtonian, ν = 5.81e-5 m²/s (paraffin at emulsification T) |
| `constant/turbulenceProperties` | RAS, kOmegaSST |
| `constant/dynamicMeshDict` | solidBody / rotatingMotion at ω = 157.08 rad/s = 1500 RPM |
| `0.org/U`, `p`, `k`, `omega`, `nut` | initial conditions; k/ω from 5 % turbulence intensity at U_tip |
| `zones_config.json` | 3-zone partition (impeller / near_wall / bulk) for `extract_epsilon.py` |

## Patch convention

The dicts assume STL files with the following patch (solid) names, written
by `prepare_geometry.sh`:

- `vessel_wall` — beaker inside surface
- `impeller_wall` — Stirrer A impeller surface
- `rotorZone` — refinement region (cylinder around the impeller swept volume)
  → snappyHexMesh creates a cellZone of the same name, used by `dynamicMeshDict`
  for the AMI sliding mesh.

If you use a different STL naming convention, edit `snappyHexMeshDict`
`refinementSurfaces`, the `boundaryField` entries in `0.org/*`, and
`dynamicMeshDict cellZone`.

## Operating points to simulate (initial scope)

| Run | RPM | Duration | Purpose |
|-----|-----|----------|---------|
| run_01 | 1500 | 5 s | Baseline (default in `controlDict` / `dynamicMeshDict`) |
| run_02 | 1300 | 5 s | Calibrated bench RPM (pre-validation reference) |
| run_03 | 2000 | 5 s | Mid-range |
| run_04 | 2500 | 5 s | Maximum (per `max_rpm = 2500.0` in `datatypes.py`) |

To change RPM: update `dynamicMeshDict::rotatingMotionCoeffs::omega`
(rad/s = RPM / 60 · 2π) and re-run.

## Validation gates

- `checkMesh`: max non-orthogonality < 65°, max skewness < 4 (enforced by
  `snappyHexMeshDict::meshQualityControls`).
- Final solver residual: < 1e-5 (run-time check via `PIMPLE::residualControl`).
- Volume-weighted ε: should reconcile with the empirical Po·N³·D⁵/V_tank
  estimate (Po ≈ 0.35 for this geometry) within ~30 %. The DPSim
  consistency check (`dpsim cfd-zones --legacy-eps`) reports this.
- PIV at bench scale (water, Re ≈ 145 000): ±15 % on impeller swept-volume
  velocity, ±25 % in bulk. Required gate before trusting CFD predictions
  for absolute scale-up — see Appendix K §K.4.6.
