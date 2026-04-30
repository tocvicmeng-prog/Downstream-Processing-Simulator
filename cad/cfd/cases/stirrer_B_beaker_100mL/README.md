# Stirrer B (rotor-stator) in 100 mL beaker — OpenFOAM case

Bench-scale CFD case for Stirrer B (Ø 32 mm rotor-stator with 36
peripheral perforations) in the glass beaker. Stator's Ø 3 mm holes must
be mesh-resolved — they are the dominant breakage zones (80-95% of total
breakage in rotor-stator devices, per Padron 2005).

**Status**: Empty scaffold. See `cad/cfd/README.md` for the full TODO list.

## Geometry source

- Stirrer B rotor: `cad/output/stirrer_B_rotor.step` (verified 2026-05-01,
  flat sheet "+" with offset finger pairs, blunt 2 mm flat tips, 1 mm
  fillet at all corners)
- Stirrer B stator: `cad/output/stirrer_B_stator.step` (Ø 32.03 mm × 18 mm,
  3 rows × 12 columns of Ø 3 mm perforations, Ø 10 mm shaft passage in
  closed top)
- Vessel: `cad/output/beaker_100mm.step`

## Critical mesh requirement

Stator perforations (Ø 3 mm) must be resolved with at least 8-10 cells
across each hole diameter (~0.3 mm cells in slot region). Total mesh size
projected at 8-15 M cells.

## Operating points to simulate (initial scope)

| Run | RPM | Duration | Purpose |
|-----|-----|----------|---------|
| run_01 | 5000 | 5 s | Mid-range — Re ≈ 70 000 |
| run_02 | 9000 | 5 s | Maximum (per `max_rpm = 9000.0`) |

PIV validation challenging at high RPM; accept LDV measurement at run_01
as alternative if PIV laser sheet stability is poor.
