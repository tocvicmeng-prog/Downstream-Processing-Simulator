# Appendix K — M1 CFD-PBE Zonal Coupling

**Edition:** 1.0 (covers DPSim v0.6.0+ CFD-PBE coupling)
**Date:** 2026-05-01
**Audience:** Advanced users, CFD engineers, IP auditors, and developers maintaining or extending the M1 PBE pipeline.
**Companion:** First-edition manual §9 (operator-facing introduction), `cad/cfd/zones_schema.md` (machine-readable contract), `cad/cfd/README.md` (OpenFOAM pipeline roadmap).
**Status:** Implementation specification + operational guidance. The DPSim-side coupling is implemented and tested; the OpenFOAM-side pipeline (Phases 1–4 below) is scaffolded but not yet executed against real geometry — see §K.5.

---

## K.0 Executive Summary

The standard M1 PBE solver in DPSim feeds one scalar dissipation rate ε to the Alopaeus breakage and Coulaloglou-Tavlarides coalescence kernels, computed empirically as `Po · N³ · D⁵ / V_tank`. That single number is the volume-average across the whole vessel, which is adequate for a well-mixed pitched-blade impeller in a calibrated benchtop beaker but underestimates breakage for two important regimes:

1. **Rotor-stator mixers**, where 80–95 % of breakage occurs in stator slot-exit jets (Padron 2005, Hall et al. 2011) — a region too small to volume-average without losing the physics.
2. **Geometric scale-up** (e.g. 100 mL → 1 L), where the Po-based estimate may agree with bench measurement at the reference scale but diverge at the target scale because the relationship between Po and impeller geometry is not strictly Reynolds-invariant.

The CFD-PBE zonal coupling addresses both by replacing the volume-averaged ε with a CFD-resolved field, partitioned into a small number (typically 3–5) of well-mixed compartments, each with its own ε. DPSim reads a `zones.json` file describing the compartment model and integrates the PBE per zone with convective droplet exchange between zones. The breakage and coalescence kernels are unchanged; only the spatial coupling is new.

The implementation is intentionally narrow: variable-N zones, two ε values per zone (one for breakage, one for coalescence; see §K.2), one-way convective exchanges with asymmetric source/target rates. Diffusive exchange and per-zone time-dependent fields are deferred to schema v1.1+. The DPSim-side coupling is fully implemented (`src/dpsim/cfd/zonal_pbe.py`) with 33 pytest tests including a bit-exact reduction to the legacy single-zone solver. The OpenFOAM-side pipeline (geometry preparation through ε extraction) is scaffolded with documented steps but not yet executed end-to-end against the 100 mL bench geometry.

The headline correctness gate is the **single-zone equivalence test**: a `zones.json` with one zone, no exchanges, and identical breakage / coalescence ε reproduces the bare `PBESolver` output to numerical precision (0.000000 % relative error). This guarantees that the zonal coupling adds no numerical drift in the degenerate case.

---

## K.1 Technical Objective and Success Criteria

### K.1.1 Objective

Provide a spatially-resolved upgrade to the M1 PBE that captures sub-zone breakage hotspots, supports 10× scale-up prediction with documented uncertainty, and reduces bit-exactly to the legacy single-zone solver when the CFD field is given as a single uniform zone.

### K.1.2 Success criteria

| Criterion | Status | Evidence |
|---|---|---|
| Schema v1.0 locked, machine-validated | ✅ | `cad/cfd/zones_schema.md`; 11 hard-validation paths in pytest |
| Single-zone equivalence to bare PBE solver | ✅ | `tests/test_cfd_zonal_pbe.py::test_single_zone_reproduces_bare_pbe_solver` (0.000000 % rel error) |
| Total droplet volume conserved | ✅ | < 1e-3 rel error on 3-zone Stirrer A and 4-zone Stirrer B (mass-conservative breakage + coalescence + symmetric exchange transport) |
| Per-zone d32 ordering matches physics | ✅ | Stirrer A: impeller < `near_wall` < bulk; Stirrer B: bulk > `slot_exit` ≈ impeller within the loop |
| Standalone CLI subcommand | ✅ | `dpsim cfd-zones`; 2 subprocess-based smoke tests |
| Cross-check vs legacy empirical ε | ✅ | `consistency_check_with_volume_avg`, 30 % default tolerance |
| OpenFOAM dictionary templates (Phase 1–3) | ⏸ | Stubs in `cad/cfd/cases/`; full dicts deferred to next session |
| `extract_epsilon.py` implementation | ⏸ | Schema target locked; implementation deferred |
| PIV validation campaign at bench scale | ⏸ | Required gate before trusting CFD predictions for absolute scale-up |

---

## K.2 Mathematical Framework

### K.2.1 Population balance (per zone)

Within a single zone of volume V_i, the number-density form of the PBE for droplet count per unit volume N_i(d, t) is:

```
∂N_i(d, t) / ∂t  =  B_breakage(N_i; ε_brk_i) − D_breakage(N_i; ε_brk_i)
                  + B_coalescence(N_i; ε_avg_i) − D_coalescence(N_i; ε_avg_i)
                  + S_exchange_i({N_j}, {Q_ji})
```

The breakage and coalescence terms are evaluated **per zone** with zone-specific ε; the exchange term S_exchange_i is the only inter-zone coupling. DPSim's implementation uses the fixed-pivot discretisation (Kumar & Ramkrishna 1996) with binary equal-volume daughter distribution, identical to the legacy `PBESolver`.

### K.2.2 Why two ε values per zone

The Alopaeus (2002) breakage rate with viscous sub-range correction:

```
g(d, ε) = C₁ · √(ε/ν_c) · exp[ −C₂ · σ / (ρ_c · ε^(2/3) · d^(5/3))  −  C₃ · Vi ]
```

where Vi = µ_d / √(ρ_c · σ · d) is the dimensionless viscosity group and ν_c is the continuous-phase kinematic viscosity. The leading term scales as ε^(1/2) and the surface-tension exponent argument scales as ε^(−2/3). Both make g(d, ε) **convex in ε**.

Apply Jensen's inequality. For a convex function f and a probability measure µ:

```
   <f(ε)>_µ  ≥  f(<ε>_µ)
```

Translating to the PBE: if ε(x) varies inside a zone, the average breakage rate is *strictly greater than* the breakage rate evaluated at the volume-average ε — because the small high-ε hotspots contribute disproportionately. Volume-averaging hides them, biasing predicted droplet sizes upward.

The fix is a **breakage-frequency-weighted ε**. Define a reference diameter `d_ref` (typically the predicted d50) and set:

```
   ε_brk = ∫ g(d_ref, ε(x)) · ε(x) dV / ∫ g(d_ref, ε(x)) dV
```

This is the ε value at which a uniform-ε zone would produce the same total breakage rate as the actual heterogeneous zone (to first order in `d_ref`). It is automatically biased toward hotspots because the weighting function g is itself convex in ε. The weighted ε is then used in place of the volume-average when evaluating the breakage kernel.

The Coulaloglou-Tavlarides (1977) coalescence kernel behaves differently:

```
q(d_i, d_j, ε) = C₄ · ε^(1/3) · (1 + φ_d)^(−1) · (d_i² + d_j²) · √(d_i^(2/3) + d_j^(2/3))
                · exp[ −C₅ · µ_c · ρ_c · ε / σ² · (d_i · d_j / (d_i + d_j))⁴ ]
```

The collision-frequency term scales as ε^(1/3) and the film-drainage exponent argument scales as ε. The product is more nearly linear in ε across realistic operating ranges, and the exponential damps coalescence in high-ε regions where droplets are too far apart to refilm — which is the *correct* physical behaviour. A volume-averaged ε is therefore appropriate for the coalescence kernel.

**The schema enforces ε_brk ≥ ε_avg (within 1 % numerical slack) at load time.** A violation indicates a bug in the post-processing script that emitted the JSON, not a physical regime; the loader rejects such files.

### K.2.3 Convective exchange

For an exchange (i_from → i_to) with continuous-phase volumetric flow Q [m³/s], droplets are carried by the continuous phase at the source-zone instantaneous DSD. The number-density balance is:

```
   dN_from/dt  +=  ... − (Q / V_from) · N_from        # outflow (fractional rate Q/V_from)
   dN_to/dt    +=  ... + (Q / V_to)   · N_from        # inflow (well-mixed dilution into V_to)
```

The fractional rates are **asymmetric** because V_from ≠ V_to in general. The total droplet count moved per second is Q · N_from (count = number-density × volume swept, and Q is volume swept per second). This count is removed from V_from at fractional rate Q/V_from and added to V_to at fractional rate Q/V_to.

**Volume conservation check.** The rate of droplet-volume change in zone i is `Vᵢ · Σⱼ (dNᵢ,ⱼ/dt) · vⱼ` where vⱼ is the bin pivot volume. For the exchange terms:

```
   dV_droplet_from/dt  = −Q · Σⱼ N_from,j · vⱼ  =  −Q · φ_d_from
   dV_droplet_to/dt    = +Q · Σⱼ N_from,j · vⱼ  =  +Q · φ_d_from
```

Net = 0 across any pair. Breakage and coalescence are mass-conservative under fixed-pivot redistribution (Kumar & Ramkrishna 1996). Therefore total droplet volume `Σᵢ Vᵢ · Σⱼ Nᵢ,j · vⱼ` is conserved exactly, modulo numerical integration error. The integrator reports this as `volume_balance_relative_error`; the test gate is < 1e-3.

### K.2.4 Initial condition

At t = 0, every zone is initialised with the same number-density distribution: a log-normal premix DSD scaled to local φ_d. This corresponds to the physical assumption that the pre-emulsion droplets are dispersed uniformly across all zones at the start of high-shear emulsification. Zones then evolve independently (modulo exchange) toward their local steady-state.

The CLI flags `--d32-premix` and `--sigma-premix` control this initial distribution. Defaults match the legacy `solve_stirred_vessel` premix: d32 = 100 µm, σ = 0.5 (broader log-normal). For a CFD-PBE run starting from a coarser premix (rotor-stator typical: 200–500 µm), pass `--d32-premix 200e-6` or larger.

---

## K.3 Schema and Data Contract

The `zones.json` schema is locked at v1.0 in `cad/cfd/zones_schema.md`. This appendix gives operational rationale; refer to the schema doc for the field-by-field specification.

### K.3.1 Top-level structure

```json
{
  "schema_version": "1.0",
  "case_metadata": { ... provenance ... },
  "zones": [ { ... }, { ... } ],
  "exchanges": [ { ... }, { ... } ]
}
```

The `case_metadata` block does not feed the PBE coupling — it carries provenance (case name, RPM, fluid temperature, OpenFOAM solver, time-averaging window, mesh size, convergence residual, volume-weighted ε). The cross-field consistency check verifies that `case_metadata.epsilon_volume_weighted_avg_W_per_kg` matches `Σ(Vᵢ · ε_avg_i) / Σ(Vᵢ)` within 1 %; mismatch above 1 % indicates corrupted JSON or an `extract_epsilon.py` bug and the loader rejects.

### K.3.2 Per-zone fields

| Field | Required | Drives | Notes |
|---|---|---|---|
| `name` | yes | exchange routing | Unique within file; convention `lowercase_snake_case` |
| `kind` | yes | display only | One of `impeller_swept_volume`, `stator_slot_exit`, `near_wall`, `bulk`, `custom` |
| `volume_m3` | yes | exchange rates, aggregation | Must be > 0 |
| `cell_count` | yes | diagnostic | Warn if < 100 |
| `epsilon_avg_W_per_kg` | yes | **coalescence kernel** | Volume average over zone cells |
| `epsilon_breakage_weighted_W_per_kg` | yes | **breakage kernel** | Must be ≥ ε_avg within 1 % slack |
| `shear_rate_avg_per_s` | yes | diagnostic only | Used by viscous-correction sanity gate |
| `centroid_xyz_m` | no | plotting | Geometric centroid, not used by physics |
| `kolmogorov_length_m` | no | diagnostic | η_K = (ν³/ε)^(1/4) at ε_avg |
| `metadata` | no | free-form | Extracted-from notes, boundary defs, etc. |

### K.3.3 Per-exchange fields

| Field | Required | Notes |
|---|---|---|
| `from_zone`, `to_zone` | yes | Must reference existing zones; `from_zone ≠ to_zone` |
| `volumetric_flow_m3_per_s` | yes | One-way; bidirectional flow = two entries |
| `kind` | no | `convective` (default) or `diffusive`; diffusive raises NotImplementedError in v1.0 |

### K.3.4 Validation rules (loader-enforced)

1. `schema_version == "1.0"`.
2. All zone names unique.
3. All exchange endpoints reference existing zone names; `from ≠ to`.
4. All numeric fields satisfy declared signs.
5. ε_brk ≥ ε_avg per zone (1 % numerical slack).
6. `case_metadata` ε ≈ Σ(V·ε_avg)/ΣV within 1 %.
7. `time_averaging_window_s`[1] > [0].
8. Total zone volume > 0; zones list non-empty.

Soft (warning-only) gates: under-resolved zones (`cell_count` < 100), sub-mm³ zones, mesh < 1e5 cells total, convergence residual > 1e-4.

### K.3.5 Schema evolution policy

| Bump | Trigger | Compatibility |
|---|---|---|
| Patch (1.0.x) | Clarifications, additional optional fields | v1.0 files remain valid |
| Minor (1.x.0) | New required fields with sensible defaults | Loader provides automatic migration with deprecation warning |
| Major (x.0.0) | Breaking changes | Hard error; migration script required |

Known v1.0 deferrals (candidates for v1.1):
- Per-zone time-averaged temperature (when non-isothermal CFD lands).
- Time-resolved ε snapshots (transient coupling).
- Per-zone velocity statistics (advanced collision-frequency models).
- Per-zone φ_d (concentrated emulsions with strong segregation).

---

## K.4 OpenFOAM Pipeline (Phases 1–7)

The OpenFOAM-side pipeline produces `zones.json` from a CAD model and CFD case. It runs **once per geometry × operating point** (e.g. once for Stirrer A at 1500 RPM, once for Stirrer B at 6000 RPM); the resulting JSON is then reused for many DPSim runs varying material and recipe parameters. Estimated effort: 1–2 person-months for a CFD engineer with prior OpenFOAM stirred-tank experience, plus one PIV measurement campaign.

### K.4.1 Phase 1 — Geometry preparation (1 day)

**Inputs:** `cad/output/*.step` (parametric STEP files for the 5 wetted parts, generated by `cad/scripts/build_geometry.py`).

**Tasks:**

1. Assemble the stirrer + beaker pair at the correct insertion depth. The default for double emulsions is mid-plane at ~50 % liquid height; verify against your protocol.
2. Convert STEP → STL for `snappyHexMesh` consumption (FreeCAD CLI or gmsh both work).
3. Define the rotating zone (impeller swept volume) and the static zone (vessel interior less swept) for the sliding-mesh setup.
4. Helper: `cad/cfd/scripts/prepare_geometry.sh`.

### K.4.2 Phase 2 — Mesh generation (3–5 days)

**Tasks:**

1. `system/blockMeshDict` — background hex mesh covering the beaker volume.
2. `system/snappyHexMeshDict` — castellated mesh + snap + layer addition with refinement levels:
   - **Level 5–6** on impeller surfaces (~0.1 mm cells) — needed to resolve the boundary layer that drives breakage.
   - **Level 4** on stator perforation slots (Stirrer B only, ~0.2 mm) — required to resolve the slot-exit jets that carry 80–95 % of breakage.
   - **Level 2–3** in bulk (~1–2 mm).
3. Prism layers (5–7 layers, expansion ratio 1.2) on impeller and stator surfaces.
4. Mesh-quality gates: max non-orthogonality < 65°, max skewness < 4, aspect ratio < 100.

Total mesh size typically lands at 5–20 M cells. Stirrer B at high refinement may exceed 12 M cells.

### K.4.3 Phase 3 — Solver setup (2–3 days)

**Tasks:**

1. `constant/transportProperties` — continuous-phase viscosity. Reuse DPSim's calibrated rheology from `level1_emulsification/rheology.py` if you have polysaccharide-solution data; default to water for first-pass.
2. `constant/turbulenceProperties` — `kOmegaSST`. RANS is the appropriate cost-accuracy point for ε-field validation; LES would be ~100× more expensive and is not justified for 10× scale-up validation.
3. `constant/dynamicMeshDict` — sliding-mesh setup with rotating zone tied to impeller AMI (Arbitrary Mesh Interface).
4. `0.org/` — initial conditions for U, p, k, omega, nu_t.
5. `system/fvSchemes` — 2nd-order upwind for advection, central for diffusion.
6. `system/fvSolution` — PIMPLE with 2 outer correctors, residual tolerance 1e-5.
7. `system/controlDict` — deltaT 1e-4 s, write interval 0.1 s, end time 5–10 s (covers 10–50 impeller rotations).

### K.4.4 Phase 4 — Run and post-process (1–2 days)

**Tasks:**

1. `cad/cfd/scripts/run_case.sh` — execute the full pipeline (`blockMesh` → `snappyHexMesh` → `decomposePar` → `pimpleDyMFoam` → `reconstructPar`).
2. Parallelisation: 8–32 cores depending on workstation.
3. `cad/cfd/scripts/extract_epsilon.py` — extract time-averaged ε(x) field, partition cells into compartments (impeller / `near_wall` / bulk / [`slot_exit` for Stirrer B]), compute per-zone:
   - Volume.
   - Cell count.
   - Volume-averaged ε.
   - Breakage-frequency-weighted ε at `d_ref` = expected d50 (either user-supplied or estimated as Hinze `d_max`).
   - Volume-averaged shear rate.
   - Kolmogorov length at ε_avg.
4. Compute exchange flow rates between zones from the velocity field crossing zone boundaries.
5. Emit `zones.json` matching the schema v1.0 contract.

Recommended Python dependencies: `fluidfoam` for clean OpenFOAM field readers, `numpy` and `scipy` for the partitioning math.

### K.4.5 Phase 5 — DPSim integration (5–7 days)

**Status: implemented (commit a5d984c).**

`src/dpsim/cfd/zonal_pbe.py` provides:

- `load_zones_json()` — Pydantic v2 validator with 11 hard-validation paths and soft advisory warnings.
- `integrate_pbe_with_zones()` — N-zone PBE integrator on a flattened (n_zones × n_bins,) state via LSODA; reuses Alopaeus / CT kernels from `level1_emulsification`.
- `consistency_check_with_volume_avg()` — 30 %-tolerance gate against the legacy Po·N³·D⁵/V_tank empirical estimate.
- `dpsim cfd-zones` CLI subcommand (see first-edition manual §9.6).

### K.4.6 Phase 6 — Validation (1 week + bench measurement campaign)

**This is the gate that turns CFD predictions from `qualitative_trend` into `calibrated_local`.**

**PIV measurement** at one representative RPM per stirrer (water only, bench scale). Required inputs:

- Velocity-field magnitude in a vertical plane through the impeller axis.
- Spatial resolution sufficient to resolve the impeller swept volume and the stator slot exits (Stirrer B).

**Comparison gates:**

- CFD U field vs PIV: ±15 % in impeller swept volume, ±25 % in bulk.
- DPSim DSD prediction vs measured d50 / d90 across 4–6 RPM × 2 φ_d × 2 surfactant levels.

**Deliverable:** a documented validation envelope — what range of conditions can be extrapolated from this CFD calibration with confidence?

### K.4.7 Phase 7 — Scale-up extrapolation (2 weeks)

Once Phase 6 has set the validation envelope, repeat the CFD-PBE pipeline for the 1 L vessel geometry (geometric similarity: scale Stirrer B by 2.15× linear, or use a larger commercial impeller — choice depends on what you intend to manufacture at). Predict DSD at 1 L; flag uncertainty due to extrapolation; identify operating regimes where bench calibration is required before trusting predictions.

The post-validation extrapolation policy is conservative: any prediction outside the documented PIV-validated envelope returns to `qualitative_trend` evidence.

---

## K.5 Validation Status (2026-05-01)

| Phase | Status | Blocking item |
|---|---|---|
| 1. Geometry preparation | scaffolded | `prepare_geometry.sh` is a stub; needs end-to-end test with FreeCAD / gmsh |
| 2. Mesh generation | scaffolded | OpenFOAM dicts are placeholders; no mesh-quality dry-run yet |
| 3. Solver setup | scaffolded | Same as Phase 2 |
| 4. Run + post-process | scaffolded | `extract_epsilon.py` is a stub printing the algorithm |
| 5. DPSim integration | **implemented + tested** | 33 pytest tests, single-zone equivalence verified bit-exactly |
| 6. PIV validation | not started | Bench measurement campaign required |
| 7. Scale-up extrapolation | not started | Gated on Phase 6 |

The DPSim-side coupling can be exercised today against any `zones.json` you provide (the example fixtures at `cad/cfd/cases/*/zones.example.json` are illustrative synthetic data). What is **not yet validated** is the upstream CFD pipeline that produces real `zones.json` files. Until that lands and is PIV-gated, predictions from this path inherit `qualitative_trend` evidence in the lifecycle ladder.

---

## K.6 Limitations and Risks

### K.6.1 Physical limitations of the v1.0 coupling

| Limitation | Where it bites | Workaround |
|---|---|---|
| Single-phase Eulerian | Highly inhomogeneous concentrated emulsions (φ_d > 0.4 with segregation) | Defer to schema v1.1 with per-zone φ_d |
| Steady-state RANS only | Transient start-up, RPM ramps, shut-down | Use end-of-integration steady values only |
| RANS k-ω SST turbulence model | Boundary-layer separation, swirling flows near LES regime | Validation envelope from Phase 6 captures this |
| Inertial sub-range assumption (CT and Alopaeus C₃=0) | Highly viscous dispersed phases (µ_d > 1 Pa·s), or zones with d_mode/η_K < 5 | Set MaterialProperties.`breakage_C3` > 0 (Alopaeus viscous correction); see §K.7 |
| No adaptive integration extension | Slow-equilibrating systems where d32 hasn't stabilised by `--duration` | Re-run with longer `--duration`, or implement adaptive extension (deferred) |
| Convective exchange only (no diffusive) | Highly diffusive transport regimes (rare for stirred tanks) | Schema v1.1 will add diffusive kind |
| Single `d_ref` for ε_brk weighting | Polydisperse systems where breakage rate is bimodal | Use the predicted d50 as `d_ref`; iterate if necessary |

### K.6.2 Schema and pipeline risks

| Risk | Mitigation |
|---|---|
| `extract_epsilon.py` bug emits ε_brk < ε_avg | Schema rejects at load time |
| `extract_epsilon.py` bug emits inconsistent volumes vs `case_metadata` | Cross-field consistency check rejects at load time |
| Bad CFD convergence undetected | `convergence_residual > 1e-4` triggers warning |
| Under-resolved zones (`slot_exit` too coarse) | `cell_count < 100` triggers warning |
| Mesh too coarse overall | `n_cells_total < 1e5` triggers warning |
| User runs against unvalidated CFD | Documented in §9.8; evidence tier defaults to `qualitative_trend` |
| Schema evolution breaks existing JSON | Versioning policy (§K.3.5); loader migration provided for minor bumps |

### K.6.3 Evidence-tier policy

| Validation state | Evidence tier |
|---|---|
| No PIV calibration | `qualitative_trend` |
| PIV-calibrated CFD field for this geometry × operating point | `calibrated_local` for trends and relative comparisons |
| PIV + bench DSD calibration across an operating envelope | `validated_quantitative` within the documented envelope |
| Outside the validated envelope | drops back to `qualitative_trend` |

---

## K.7 The Vi Viscous-Correction Caveat

The Alopaeus breakage kernel includes an optional viscous correction term `−C₃ · Vi` in the exponent, where Vi = µ_d / √(ρ_c · σ · d). For aqueous dispersed phases at typical emulsification temperatures (µ_d ~ 0.01–0.1 Pa·s), this correction is physically negligible and `breakage_C3 = 0.0` is the appropriate setting (the default). For highly viscous dispersed phases (µ_d > 1 Pa·s) — typically encountered in non-aqueous polymer dispersions — `breakage_C3` should be increased after calibration.

Two defensive measures are already in place:

1. **Vi cap**: in `breakage_rate_alopaeus()`, Vi is capped at 100 to prevent `exp(−C₃ · Vi)` from underflowing for sub-micron droplets. Without this cap, sub-micron droplets see Vi > 50, the breakage rate goes to zero, and a nonphysical RPM → d32 feedback loop appears (the F1 audit, 2026-04-17). The cap is preserved across the JIT and NumPy paths.

2. **Default of zero**: `MaterialProperties.breakage_C3 = 0.0` and `KernelConfig.for_pitched_blade().breakage_C3 = 2.0` only when explicitly selected. Most M1 calibrations therefore run with the viscous term disabled, relying purely on the surface-tension term for breakage suppression at small d.

When using the zonal coupling, the Vi behaviour is unchanged. Each zone sees the same `MaterialProperties.breakage_C3` and `KernelConfig` parameters; only ε differs. If you suspect the viscous regime matters for your dispersed phase, calibrate `breakage_C3` against bench DSD measurements on the legacy single-zone solver *first*, then port the calibrated value to the zonal run.

---

## K.8 Reproducibility Checklist

Before reporting results from a CFD-PBE coupled run:

- [ ] CFD case converged with residual < 1e-5.
- [ ] Mesh quality gates pass (non-orthogonality, skewness, aspect ratio).
- [ ] PIV validation completed at the bench scale; documented envelope attached.
- [ ] `zones.json` `schema_version` = "1.0" and all hard-validation paths pass.
- [ ] `--legacy-eps` consistency check passes within 30 % (or the failure is investigated and explained).
- [ ] `volume_balance_relative_error < 1e-3`.
- [ ] Per-zone d32 ordering matches expected physics (high-ε zones smaller, sink zones largest).
- [ ] Integration duration is long enough for d32 to stabilise (`--duration` × 2 reproduces the same result within 1 %).
- [ ] MaterialProperties match the bench validation calibration.
- [ ] Predicted DSD compared against bench measurement and the difference quantified.
- [ ] Evidence tier explicitly assigned in the run report.

---

## K.9 References

### Foundational

- **Alopaeus V., Koskinen J., Keskinen K. I., Majander J. (2002).** *Simulation of the population balances for liquid-liquid systems in a nonideal stirred tank.* Chem. Eng. Sci. 57, 1815–1825. — Source of the Alopaeus breakage kernel; viscous sub-range correction.
- **Coulaloglou C. A., Tavlarides L. L. (1977).** *Description of interaction processes in agitated liquid-liquid dispersions.* Chem. Eng. Sci. 32, 1289–1297. — Source of the CT coalescence kernel.
- **Kumar S., Ramkrishna D. (1996).** *On the solution of population balance equations by discretization — I. A fixed pivot technique.* Chem. Eng. Sci. 51, 1311–1332. — Fixed-pivot discretisation method used by `PBESolver`.

### CFD-PBE coupling

- **Wang T., Mao Z.-S. (2005).** *CFD-PBE coupling for stirred tanks.* Chem. Eng. Sci. 60, 4501–4516. — One-way CFD-PBE coupling methodology; the architectural template for the present work.

### Rotor-stator breakage

- **Padron G. (2005).** *Effect of surfactants on drop size distribution in a batch, rotor-stator mixer.* PhD thesis, University of Maryland. — The 80–95 % slot-exit dominance figure.
- **Hall S., Cooke M., Pacek A. W., Kowalski A. J., Rothman D. (2011).** *Scaling-up of silverson rotor-stator mixers.* Can. J. Chem. Eng. 89, 1040–1050. — Confirmation across rotor-stator scales; basis for the dedicated `slot_exit` zone in the Stirrer B baseline.

### Hydrodynamics

- **Metzner A. B., Otto R. E. (1957).** *Agitation of non-Newtonian fluids.* AIChE J. 3, 3–10. — Source of the average shear rate γ̇ = k_s · N correlation used in `level1_emulsification/energy.py`.
- **Utomo A. T., Baker M., Pacek A. W. (2009).** *The effect of stator geometry on the flow pattern and energy dissipation rate in a rotor-stator mixer.* Chem. Eng. Sci. 64, 4426–4439. — Stator-geometry / Np correlations.

### Hinze-Kolmogorov stable size

- **Calabrese R. V., Chang T. P. K., Dang P. T. (1986).** *Drop breakup in turbulent stirred-tank contactors. Part I: Effect of dispersed-phase viscosity.* AIChE J. 32, 657–666. — Viscous correction to the classical Hinze `d_max`.

---

## K.10 Glossary

| Term | Meaning |
|---|---|
| `ε_avg` (`epsilon_avg_W_per_kg`) | Volume-averaged turbulent dissipation rate over zone cells. Drives the coalescence kernel. |
| `ε_brk` (`epsilon_breakage_weighted_W_per_kg`) | Breakage-frequency-weighted ε. Drives the breakage kernel. By construction, ε_brk ≥ ε_avg. |
| Compartment / zone | A well-mixed region of the vessel with internally constant ε_avg and ε_brk. |
| Convective exchange | One-way droplet transport between two zones at rate Q [m³/s]. Asymmetric source / target fractional rates because V_from ≠ V_to in general. |
| d32 | Sauter mean diameter, Σ N·d³ / Σ N·d². The bench-comparable headline DSD number. |
| Fixed-pivot | The Kumar-Ramkrishna 1996 PBE discretisation. Bins are defined by their pivot diameter (geometric mean of edges); breakage / coalescence products are redistributed onto neighbouring pivots with mass-conservative weights. |
| Hinze `d_max` | Classical maximum stable droplet size in turbulent dispersion. `d_max` = C · (σ/ρ)^(3/5) · ε^(−2/5). Sets the lower bound on steady-state DSD. |
| Jensen's inequality | For a convex f and probability measure µ: <f(ε)>_µ ≥ f(<ε>_µ). The reason volume-averaging underestimates breakage. |
| η_K | Kolmogorov microscale, (ν³/ε)^(1/4). Smallest scale of turbulence; below this, energy dissipates as heat. The CT kernel assumes d ≫ η_K (inertial sub-range). |
| LSODA | Livermore Solver for ODEs, Adams + BDF automatic stiffness detection. The default for `solve_ivp` in DPSim's PBE path; ~700× faster than BDF on the non-stiff PFR + Michaelis-Menten path; switches to BDF on coalescence-dominated stiffness. |
| PIMPLE | OpenFOAM's coupled PISO + SIMPLE algorithm for transient incompressible flow with sliding meshes. |
| Po | Power number, P / (ρ · N³ · D⁵). Dimensionless impeller power draw; geometry-dependent constant in the turbulent regime. |
| Schema v1.0 | The locked `zones.json` contract (`cad/cfd/zones_schema.md`). |
| Sliding mesh | A CFD technique where part of the mesh rotates relative to the rest, with field interpolation at the AMI (Arbitrary Mesh Interface). Used to resolve impellers without remeshing every timestep. |
| `Vi` | µ_d / √(ρ_c · σ · d). Dimensionless viscosity group in the Alopaeus viscous correction term. |

---

## Disclaimer

This appendix documents the v1.0 CFD-PBE zonal coupling implementation as of 2026-05-01. The DPSim-side coupling is implemented and tested; the OpenFOAM-side pipeline that produces real `zones.json` files is scaffolded but not yet executed end-to-end. Any prediction made through this path inherits `qualitative_trend` evidence in the lifecycle ladder until PIV validation at the relevant bench scale is documented. All scientific analysis is provided for informational, research, and advisory purposes only and should be validated through appropriate laboratory experimentation and CFD verification before being used for regulatory or manufacturing decisions.
