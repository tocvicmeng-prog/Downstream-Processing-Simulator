# Stirrer B (rotor-stator) in 100 mL beaker — OpenFOAM case

Bench-scale CFD case for Stirrer B (Ø 32 mm rotor-stator with 72 peripheral
perforations across 3 rows of 24) in the glass beaker. Stator Ø 3 mm holes
must be mesh-resolved — they are the dominant breakage zones (80–95 % of
total breakage in rotor-stator devices, per Padron 2005, Hall 2011).

**Status (2026-05-01):** dictionaries populated as deltas from Stirrer A.
Geometry preparation and solver runs not yet executed end-to-end.

## Geometry source

- Rotor: `cad/output/stirrer_B_rotor.step` (flat sheet "+" with offset
  finger pairs, blunt 2 mm flat tips, R=1 mm fillets)
- Stator: `cad/output/stirrer_B_stator.step` (Ø 32.03 × 18 mm, 3 × 24
  Ø 3 mm perforations, Ø 10 mm shaft passage in closed top)
- Vessel: `cad/output/beaker_100mm.step`

## Files in this directory

This case directory contains only the dicts that **differ** from
`stirrer_A_beaker_100mL/`. Copy the rest from there before running.

| File | Source for this case |
|---|---|
| `system/controlDict` | **Local** — endTime 3 s, deltaT 2.5e-5 s (4× higher RPM needs tighter dt) |
| `system/snappyHexMeshDict` | **Local** — adds `stator_wall` patch, `slotExitZone` cellZone, level 6 on impeller, level 4 in slot-exit shell |
| `zones_config.json` | **Local** — 4 zones (impeller / slot_exit / near_wall / bulk) |
| `system/fvSchemes` | Copy from `../stirrer_A_beaker_100mL/system/fvSchemes` |
| `system/fvSolution` | Copy from `../stirrer_A_beaker_100mL/system/fvSolution` |
| `system/blockMeshDict` | Copy from `../stirrer_A_beaker_100mL/system/blockMeshDict` |
| `system/decomposeParDict` | Copy from `../stirrer_A_beaker_100mL/system/decomposeParDict` (consider 16+ subdomains for the larger Stirrer B mesh) |
| `constant/transportProperties` | Copy from Stirrer A — same fluid |
| `constant/turbulenceProperties` | Copy from Stirrer A — same model |
| `constant/dynamicMeshDict` | Copy from Stirrer A but **change `omega` to `628.3185`** (= 6000 RPM) and **`origin` to `(0 0 0.015)`** (Stirrer B impeller axial position) |
| `0.org/U`, `p`, `k`, `omega`, `nut` | Copy from Stirrer A but **add a `stator_wall` boundary entry to each, mirroring `vessel_wall`'s noSlip + wall-function**. Re-estimate `k` and `omega` initial values for the higher tip speed (U_tip = π·D·N = π · 0.032 · 100 = 10.05 m/s; k_init ≈ 0.38 m²/s²; omega_init ≈ 425 1/s). |

The convenience copy command:

```
cd cad/cfd/cases/stirrer_B_beaker_100mL
for f in system/fvSchemes system/fvSolution system/blockMeshDict \
         system/decomposeParDict constant/transportProperties \
         constant/turbulenceProperties; do
    cp ../stirrer_A_beaker_100mL/$f $f
done
# Then patch dynamicMeshDict and 0.org/* manually for the higher-RPM /
# stator_wall boundary entries — see notes above.
```

## Critical mesh requirement

Stator perforations (Ø 3 mm) must be resolved with at least 8–10 cells across
each hole diameter (~0.3–0.4 mm cells). The `snappyHexMeshDict` here uses
level-5 surface refinement on `stator_wall` and level-4 in the `slotExitZone`
cylinder; together this puts ~0.15–0.3 mm cells in the slot vicinity. Total
mesh size projected at 8–15 M cells.

## Pipeline

```
prepare_geometry.sh stirrer_B_beaker_100mL    # STEP → STL with stator_wall
run_case.sh        stirrer_B_beaker_100mL --cores 16
                                              # blockMesh → snappyHexMesh
                                              # → decomposePar → pimpleDyMFoam
                                              # → reconstructPar → cellCentres
extract_epsilon.py . \                        # → schema-v1.0 zones.json
    --zones zones_config.json \
    --output zones.json \
    --case-name stirrer_B_beaker_100mL \
    --stirrer-type rotor_stator_B \
    --rpm 6000 --rho-c 860 --mu-c 0.05 \
    --d-ref 50e-6                             # smaller d_ref due to finer DSD
```

## Operating points to simulate (initial scope)

| Run | RPM | Duration | Purpose |
|-----|-----|----------|---------|
| run_01 | 5000 | 3 s | Mid-range — Re ≈ 70 000 |
| run_02 | 6000 | 3 s | Baseline (default in `controlDict` / `dynamicMeshDict`) |
| run_03 | 9000 | 3 s | Maximum (per `max_rpm = 9000.0`) |

To change RPM: update `dynamicMeshDict::rotatingMotionCoeffs::omega`
(rad/s = RPM / 60 · 2π) and re-run. Larger rotor → tighter dt: re-check
`maxCo < 0.5` in `controlDict::adjustTimeStep`.

PIV validation challenging at 6000+ RPM; accept LDV at 5000 RPM as
alternative if PIV laser-sheet stability is poor. The PIV envelope must
include a slot-exit measurement station to validate the dominant
breakage region.

## Validation gates

- Same as Stirrer A (`checkMesh`, residual < 1e-5, ε consistency check).
- Additional gate: slot_exit ε must be > 5× impeller ε in the converged
  CFD output. If not, the slot-refinement is under-resolved or the
  `slotExitZone` cellZone is mispositioned.
