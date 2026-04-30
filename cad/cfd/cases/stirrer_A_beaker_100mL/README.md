# Stirrer A in 100 mL beaker — OpenFOAM case

Bench-scale CFD case for Stirrer A (disk-style 19-tab impeller, Ø 59 mm)
in the standard glass beaker (Ø 100 × 130 mm). Working volume 100 mL
(half-filled, liquid height ~13 mm — below the impeller blade tips, so the
impeller operates near the surface for double-emulsion fabrication).

**Status**: Empty scaffold. See `cad/cfd/README.md` for the full TODO list.

## Geometry source

- Stirrer A: `cad/output/stirrer_A_pitched_blade.step` (verified
  2026-05-01)
- Vessel: `cad/output/beaker_100mm.step` (verified 2026-05-01, with R=10
  inner-bottom fillet, R=5 outer-bottom fillet, 20° outward-flared rim)

## Expected outputs

- Time-averaged ε(x) field on the converged solution (5-10 s simulation
  time)
- ε breakage-weighted volume average: should reconcile with the empirical
  Po=0.35 in `src/dpsim/datatypes.py:323` to within ~30%
- Zonal partitioning: impeller / near-wall / bulk
- ZONES JSON (consumable by `src/dpsim/cfd/zonal_pbe.py`)

## Operating points to simulate (initial scope)

| Run | RPM | Duration | Purpose |
|-----|-----|----------|---------|
| run_01 | 1300 | 5 s | Baseline at calibrated bench RPM |
| run_02 | 2000 | 5 s | Mid-range |
| run_03 | 2500 | 5 s | Maximum (per `max_rpm = 2500.0`) |

PIV validation: one campaign at run_01 conditions (water continuous phase,
single-phase, Re ≈ 145 000).
