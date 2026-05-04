# DPSim CFD Geometry — Review Handoff

Generated `2026-05-01` from `src/dpsim/datatypes.py` factory dimensions and
2026-03-27 measurement photos in
`C:\Users\tocvi\Downloads\Measurement photos of stirrer\`.

**Status**: Draft. Awaiting manual review of dimensions and details before
assembly + meshing.

**Decision context (2026-05-01)**:
- Scale-up trajectory: bench 100 mL → max **1 L** (~10× volume, ~2.15× linear)
- CFD-PBE coupling investment is **justified** for this extrapolation range —
  10× linear is well within the validity envelope for ε-field-driven kernel
  refinement and is a reasonable 1-2 month CFD project (not a multi-year
  research effort)
- Geometry → CFD → coupled validation pipeline is the right next step after
  this review.

**Excluded from this build**: the legacy 25 mm rotor-stator
(`rotor_stator_legacy`). User instruction 2026-05-01 — abandoned from 3D
modelling.

## Files

All in `cad/output/`. Each part exports as both STEP AP242 (parametric, fully
editable in SolidWorks 2018+) and STL (faceted at 0.05 mm deflection
tolerance, visualization only).

| Part | STEP | STL | Source |
|------|------|-----|--------|
| Stirrer A — disk-style 12-tab impeller Ø59 mm | `stirrer_A_pitched_blade.step` | `.stl` | `StirrerGeometry.pitched_blade_A()` + photos |
| Stirrer B — rotor (4-arm cross blade) | `stirrer_B_rotor.step` | `.stl` | `StirrerGeometry.rotor_stator_B()` |
| Stirrer B — stator (Ø32 × 18 mm, 72 perforations) | `stirrer_B_stator.step` | `.stl` | same + photo |
| Beaker Ø100 × 130 mm | `beaker_100mm.step` | `.stl` | `VesselGeometry.glass_beaker()` |
| Jacketed vessel Ø92 × 160 mm | `jacketed_vessel_92mm.step` | `.stl` | `VesselGeometry.jacketed_vessel()` |

## Dimensions Summary

### Stirrer A — disk-style 19-tab impeller (v2 — 2026-05-01 corrections)

Per user's measurement-photo-based corrections: a flat disk Ø59 mm × 1 mm
thick with **19 tabs** at the perimeter. **10 tabs bend UP** (above disk
plane), **9 tabs bend DOWN**, **alternating** around the circumference. Each
tab is bent **perpendicular** (90°) to the disk plane (no axial pitch). The
tab face is tilted **10° tangentially** from the radial line — this is the
"fan blade" angle that drives flow when the disk rotates. **No outer lip;
no gap between tab base and disk** (tabs are integrally formed by cutting +
bending the disk material).

The 18 mm "opposite fin tip distance" = the total axial span from the top of
UP-bent fin tips to the bottom of DOWN-bent fin tips. Subtracting the 1 mm
disk thickness, each fin's axial height ≈ 8.5 mm.

| Feature | Value | Source |
|---------|-------|--------|
| Disk outer Ø | 59 mm | datatypes.py:313 + photo |
| Shaft Ø | 8 mm | datatypes.py:314 |
| Disk thickness | 1 mm | inferred from photos |
| Tab count | 19 (10 UP + 9 DOWN, alternating) | user 2026-05-01 |
| Tab radial width | 9 mm | datatypes.py:319 |
| Tab axial height | 8.5 mm | derived from 18 mm span (user 2026-05-01) |
| Tab thickness | 1 mm | datatypes.py:317 |
| Tangential pitch (fin face from radial) | 10° | user 2026-05-01 (re-interpretation) |
| Bend angle (axial) | 90° (perpendicular) | user 2026-05-01 |

**`datatypes.py` alignment** (resolved in v0.6.0; geometry now matches the
table above):
- `blade_height = 0.0085` (1 mm disk + 2 × 8.5 mm fins → 18 mm tip-to-tip)
- `blade_count = 19` (10 UP + 9 DOWN, alternating perpendicular bend)
- `blade_angle = 10.0` is interpreted as **tangential** fan-pitch from radial,
  not axial pitch
- "alternately bent" denotes alternating **±axial direction** (UP / DOWN),
  not alternating axial-pitch sign

### Stirrer B — small rotor-stator

Photo-confirmed: closed top, open bottom, 72 peripheral perforations in a
regular rectangular grid (3 rows × 24 columns, NOT staggered).
Per 2026-05-04 user correction (column count revised 12 → 24).

| Feature | Value | Source |
|---------|-------|--------|
| Stator outer Ø | 32.03 mm | datatypes.py:351 + photo |
| Stator wall thickness | 2.2 mm | datatypes.py:354 + photo |
| Stator height | 18 mm | datatypes.py:353 + photo |
| Stator hole Ø | 3 mm | datatypes.py:355 + photo |
| Stator hole pattern | 3 rows × 24 columns rectangular grid (72 holes) | photo + user 2026-05-04 |
| Rotor cross-blade tip Ø | 25.7 mm | datatypes.py:341 + photo |
| Rotor root Ø | 8.5 mm | datatypes.py:342 + photo |
| Rotor blade count | 4 (cross) | datatypes.py:343 + photo |
| Rotor blade thickness | 2 mm | datatypes.py:345 + photo |
| Rotor-stator gap (radial) | 3.165 mm | datatypes.py:352 (computed) |

### Beaker

| Feature | Value | Source |
|---------|-------|--------|
| Inner Ø | 100 mm | datatypes.py:244 |
| Wall thickness | 1.5 mm | datatypes.py:245 |
| Height | 130 mm | datatypes.py:246 |

### Jacketed vessel

| Feature | Value | Source |
|---------|-------|--------|
| Inner Ø | 92 mm | datatypes.py:258 |
| Total wall thickness | 2 mm | datatypes.py:259 |
| Height | 160 mm | datatypes.py:260 |

## Review Checklist

### Resolved-from-spec / photo (verify dimensions match physical part)

- [ ] **Stirrer A** disk Ø 59 mm
- [ ] **Stirrer A** shaft Ø 8 mm
- [ ] **Stirrer A** 12 tabs alternating ±10°
- [ ] **Stirrer A** tab dimensions 9 × 10 × 1 mm
- [ ] **Stirrer B** stator Ø 32.03 × 18 mm, wall 2.2 mm
- [ ] **Stirrer B** stator 72 holes Ø 3 mm in 3 × 24 rectangular grid
- [ ] **Stirrer B** rotor 4-arm cross, Ø8.5 root → Ø25.7 tip, 2 mm thick
- [ ] **Beaker** Ø 100 × 130 mm, wall 1.5 mm
- [ ] **Jacket vessel** Ø 92 × 160 mm

### Assumed (not in spec — verify or correct before CFD)

- [ ] **Stirrer A** — `Opposite fin tip distance 18 mm` (datatypes.py:309 +
      photo) is **NOT modeled**. The current 12-tab disk geometry has no
      feature corresponding to this 18 mm dimension. The 18 mm caliper
      photo shows an inner gap that may be (a) the disk's central hub
      through-hole, (b) an inner-fold lip on the blade tips that I missed,
      or (c) a specific clearance feature between the bent tabs. **Please
      identify what the 18 mm caliper was actually gripping** and provide
      a feature description so the model can be updated.
- [ ] **Stirrer A** — outer lip fold length 3 mm assumed. The side-view
      photos show each tab has a small outward-folded lip at its top, but
      its length wasn't measured. Verify and correct if needed.
- [ ] **Stirrer A** — disk hub geometry (around the central shaft hole)
      modeled as a flat through-disk. Real impeller may have a raised hub
      or boss for shaft attachment.
- [ ] **Stirrer A** — total shaft length 120 mm assumed.
- [x] **Stirrer B** — 72 perforations (24 columns × 3 rows) confirmed by
      user 2026-05-04 (revised from earlier 36-hole / 12-column estimate).
      Pattern is a uniform rectangular grid; hole Ø 3 mm; chamfers /
      countersinks, if any, still TBD.
- [ ] **Stirrer B** — closed-top thickness 1.5 mm assumed.
- [ ] **Stirrer B** — rotor cross-blade axial height = stator height
      (18 mm) assumed. Bottom-view photo doesn't reveal axial extent;
      real rotor may be shorter for top/bottom end-cap clearance (typical
      0.5–1 mm gap each side).
- [ ] **Stirrer B** — drive shaft above rotor: 80 mm length, Ø 8.5 mm,
      assumed.
- [ ] **Beaker** — base thickness 2.5 mm assumed (typical borosilicate).
      No spout, handle, or graduations modeled.
- [ ] **Jacketed vessel** — internal split into inner glass (1 mm wall),
      jacket cavity (8 mm gap), outer wall (1 mm) is **assumed**. The data
      model only specifies the 2 mm combined wall — the actual jacket
      cavity dimensions affect cooling rate and need physical-part
      measurement.
- [ ] **Jacketed vessel** — water inlet/outlet hose stubs (Ø8 mm × 25 mm
      at z = 30 mm and z = 130 mm, 180° apart) are illustrative only.

## How to Review

1. **Quick visual check** — open the `.stl` files in Windows 3D Viewer
   (right-click → Open with → 3D Viewer). STL is visualization-only.
2. **Dimension verification** — open the `.step` files in SolidWorks. Use
   *Measure* tool to confirm dimensions match the physical part within
   ≤0.1 mm.
3. **Edit in place** — STEP imports as solid bodies; convert to features
   to modify. Any changes should also be reflected in
   `src/dpsim/datatypes.py` to keep the simulator's flow-physics aligned.
4. **Flag corrections** in this checklist OR amend `datatypes.py` directly
   and re-run the regeneration command below.

## Regenerating

After any update to `datatypes.py` factory methods or to the build script:

```bash
.venv/Scripts/python.exe cad/scripts/build_geometry.py
```

Outputs overwrite the existing files in `cad/output/`.

## Next stage (after geometry approval)

With user-confirmed scale-up trajectory beyond 100 mL, the recommended
pipeline is:

1. **This stage** — manual review and dimension corrections
2. Update `src/dpsim/datatypes.py` if any dimensions need adjustment
3. Regenerate STEP files
4. **Assembly** — vessel + stirrer at correct insertion depth (typically
   stirrer mid-plane at vessel half-height for double emulsions; verify
   with user). Output assembled STEP.
5. **Flow domain extraction** — boolean-subtract the stirrer + shaft from
   the vessel internal volume. This negative-volume region is what gets
   meshed for CFD.
6. **Mesh** — `snappyHexMesh` (OpenFOAM) or ANSYS Meshing. Target ~5–20 M
   cells with prism layers on the impeller and stator perforation walls.
7. **Sliding-mesh RANS** — k-ω SST single-phase, simulate steady-state
   ε(x), |γ̇|(x), and circulation pattern.
8. **CFD-PBE coupling** — extract ε field into a 5–30 zone compartment
   model; feed as spatial forcing into the existing DPSim PBE solver as a
   new alternative to the volume-averaged ε kernel call.
9. **Validation** — compare predicted DSD time-series against bench data
   in the calibrated regime; if cross-validation passes, use for scale-up
   extrapolation.

PIV measurement at one representative RPM per stirrer is the gate before
trusting CFD ε fields for scale-up. Without PIV, the CFD has a CFD-shaped
opinion, not a validation.
