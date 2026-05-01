# `zones.json` schema (v1.0)

The contract between the OpenFOAM-side post-processor (`cad/cfd/scripts/extract_epsilon.py`)
and the DPSim-side zonal PBE coupling (`src/dpsim/cfd/zonal_pbe.py`).

**Locked**: 2026-05-01. Bump `schema_version` and document the migration before
breaking changes.

---

## Top-level structure

```json
{
  "schema_version": "1.0",
  "case_metadata": { ... },
  "zones": [ { ... }, { ... } ],
  "exchanges": [ { ... }, { ... } ]
}
```

| Field | Required | Type | Notes |
|---|---|---|---|
| `schema_version` | yes | string | Must equal a known version. Loader rejects unknown versions. |
| `case_metadata` | yes | object | Provenance — see below. |
| `zones` | yes | array (length ≥ 1) | Variable-N. 3 zones is the Stirrer A baseline; 4 zones is the Stirrer B baseline. |
| `exchanges` | yes | array (length ≥ 0) | Convective droplet transfers. Empty array means zones are isolated (degenerate but legal — used in single-zone sanity tests). |

## `case_metadata`

Provenance only — does not feed the PBE coupling. Used by the
consistency check (`consistency_check_with_volume_avg`) and for traceability
in run reports.

| Field | Required | Type | Unit | Notes |
|---|---|---|---|---|
| `case_name` | yes | string | — | e.g. `"stirrer_A_beaker_100mL"`. Matches `cad/cfd/cases/<case_name>/`. |
| `stirrer_type` | yes | string | — | One of `pitched_blade_A`, `rotor_stator_B` (matches `StirrerType.value`). |
| `vessel` | yes | string | — | e.g. `"beaker_100mm"`, `"jacketed_vessel_92mm"` (matches CAD output filenames). |
| `rpm` | yes | float | rev/min | Operating speed at which the CFD was run. |
| `fluid_temperature_K` | yes | float | K | Bulk fluid temperature. RANS is isothermal; this is the constant T used in the run. |
| `openfoam_solver` | yes | string | — | e.g. `"pimpleDyMFoam"`. |
| `time_averaging_window_s` | yes | array[2] of float | s | `[t_start, t_end]` over which ε was time-averaged. Must satisfy `t_end > t_start`. |
| `n_cells_total` | yes | int | — | Total mesh cell count after snappyHexMesh. Reject if `< 1e5` (mesh too coarse). |
| `convergence_residual` | yes | float | — | Final residual achieved (target: `< 1e-5`). |
| `epsilon_volume_weighted_avg_W_per_kg` | yes | float ≥ 0 | W/kg | Σ(zone.volume × zone.ε_avg) / Σ(zone.volume). Loader cross-checks against the per-zone aggregation; mismatch > 1% indicates corrupted data. |

## `zones[i]`

Variable-N. Each zone is a well-mixed compartment with two characteristic ε
values (one for breakage, one for coalescence — see Rationale below) and a
characteristic shear rate.

| Field | Required | Type | Unit | Notes |
|---|---|---|---|---|
| `name` | yes | string | — | Unique within the file. Used as the key in exchange edges. Convention: lowercase snake_case (`impeller`, `slot_exit`, `near_wall`, `bulk`). |
| `kind` | yes | string | — | One of `impeller_swept_volume`, `stator_slot_exit`, `near_wall`, `bulk`, `custom`. Free-form classifier — does not affect physics, used for plotting and reports. |
| `volume_m3` | yes | float > 0 | m³ | Sum of cell volumes assigned to this zone. |
| `cell_count` | yes | int ≥ 1 | — | Number of CFD cells in this zone. Diagnostic only — flag if `cell_count < 100` (zone is under-resolved). |
| `epsilon_avg_W_per_kg` | yes | float ≥ 0 | W/kg | Volume-weighted average dissipation rate over zone cells. **Drives coalescence kernel.** |
| `epsilon_breakage_weighted_W_per_kg` | yes | float ≥ 0 | W/kg | Breakage-frequency-weighted ε: `<ε>_g = ∫ g(d_ref, ε(x)) ε(x) dV / ∫ g(d_ref, ε(x)) dV`, evaluated at `d_ref = d50` of the expected DSD. **Drives breakage kernel.** Must satisfy `≥ epsilon_avg_W_per_kg` (breakage weighting biases toward high-ε hotspots). |
| `shear_rate_avg_per_s` | yes | float ≥ 0 | 1/s | Volume-averaged \|γ̇\|. Diagnostic — used by the viscous-correction sanity gate (Vi = µ_d / √(ρ_c·σ·d), should not blow up at zone-characteristic shear). |
| `centroid_xyz_m` | no | array[3] of float | m | Geometric centroid in the CAD coordinate system. Used for plotting; not for physics. |
| `kolmogorov_length_m` | no | float > 0 | m | η_K = (ν³/ε)^(1/4) at `epsilon_avg`. Diagnostic — flag if any zone's `d50_predicted < 5·η_K` (CT kernel inertial-subrange assumption breaks). |
| `metadata` | no | object | — | Free-form. Suggested keys: `notes`, `boundary_definition`, `cfd_extraction_method`. Not validated. |

### Two-ε rationale

The continuous ε(x) field has substantial sub-zone variability — even within
the bulk zone, a few high-ε hotspots dominate breakage because g(d, ε) ~ ε^(1/2)
in the Alopaeus form, while coalescence rate is more linear in ε. Using a single
volume-averaged ε underestimates breakage. The two-ε scheme captures this
without adding sub-zones:

- `epsilon_avg_W_per_kg` — true volume average. Drives `coalescence_rate_dispatch`.
- `epsilon_breakage_weighted_W_per_kg` — biased toward high-ε regions via
  the breakage frequency function itself. Drives `breakage_rate_dispatch`.

In a perfectly homogeneous zone, both values coincide.

## `exchanges[i]`

One-way well-mixed convective droplet transfer between two zones. To represent
asymmetric net flow (e.g., impeller pumps strongly outward), include both
directions as separate entries with their respective rates.

| Field | Required | Type | Unit | Notes |
|---|---|---|---|---|
| `from_zone` | yes | string | — | Must match an existing `zones[].name`. |
| `to_zone` | yes | string | — | Must match an existing `zones[].name`. Must differ from `from_zone`. |
| `volumetric_flow_m3_per_s` | yes | float ≥ 0 | m³/s | Continuous-phase flow leaving `from_zone` toward `to_zone`. |
| `kind` | no | string | — | One of `convective`, `diffusive`. Default `convective`. Diffusive transfers are not yet implemented in the integrator (will raise `NotImplementedError` if used). |

## Validation rules (loader-enforced)

The loader (`load_zones_json`) MUST reject any input violating:

1. `schema_version` ∈ {known versions}.
2. All `zones[].name` unique.
3. All `exchanges[].{from_zone, to_zone}` reference existing zone names; `from_zone ≠ to_zone`.
4. All numeric fields satisfy their declared signs (volume > 0, ε ≥ 0, flow ≥ 0, etc.).
5. `epsilon_breakage_weighted_W_per_kg ≥ epsilon_avg_W_per_kg` for every zone (within 1% relative tolerance to absorb numerical noise).
6. `case_metadata.epsilon_volume_weighted_avg_W_per_kg` ≈ Σ(V_i × ε_avg_i) / Σ(V_i) within 1% — sanity gate.
7. `case_metadata.time_averaging_window_s[1] > case_metadata.time_averaging_window_s[0]`.
8. Total zone volume Σ(V_i) > 0. (No upper bound enforced — caller may compare to vessel working volume in a separate check.)

## Validation rules (advisory — warn, don't reject)

The loader emits warnings for:

- Any zone with `cell_count < 100` (under-resolved).
- Any zone with `volume_m3 < 1e-9` (sub-mm³ — likely meshing artifact).
- `n_cells_total < 1e5` (whole mesh too coarse).
- `convergence_residual > 1e-4` (CFD didn't converge tightly).
- Total Σ(V_i) deviates > 5% from the implied vessel working volume.

---

## Example 1 — Stirrer A, 3 zones (impeller / near-wall / bulk)

Pitched-blade impeller in 100 mL beaker. No stator slots, so the partition
is the canonical 3-compartment model.

```json
{
  "schema_version": "1.0",
  "case_metadata": {
    "case_name": "stirrer_A_beaker_100mL",
    "stirrer_type": "pitched_blade_A",
    "vessel": "beaker_100mm",
    "rpm": 1500,
    "fluid_temperature_K": 298.15,
    "openfoam_solver": "pimpleDyMFoam",
    "time_averaging_window_s": [2.0, 5.0],
    "n_cells_total": 4500000,
    "convergence_residual": 8.4e-6,
    "epsilon_volume_weighted_avg_W_per_kg": 12.4
  },
  "zones": [
    {
      "name": "impeller",
      "kind": "impeller_swept_volume",
      "volume_m3": 5.4e-6,
      "cell_count": 280000,
      "epsilon_avg_W_per_kg": 75.0,
      "epsilon_breakage_weighted_W_per_kg": 110.0,
      "shear_rate_avg_per_s": 5500.0,
      "centroid_xyz_m": [0.0, 0.0, 0.025],
      "kolmogorov_length_m": 1.5e-5,
      "metadata": {"notes": "Disk Ø 59mm × 1mm with 19 perimeter tabs"}
    },
    {
      "name": "near_wall",
      "kind": "near_wall",
      "volume_m3": 1.2e-5,
      "cell_count": 720000,
      "epsilon_avg_W_per_kg": 8.5,
      "epsilon_breakage_weighted_W_per_kg": 12.0,
      "shear_rate_avg_per_s": 950.0,
      "centroid_xyz_m": [0.045, 0.0, 0.04],
      "kolmogorov_length_m": 4.5e-5
    },
    {
      "name": "bulk",
      "kind": "bulk",
      "volume_m3": 8.26e-5,
      "cell_count": 3500000,
      "epsilon_avg_W_per_kg": 4.8,
      "epsilon_breakage_weighted_W_per_kg": 6.2,
      "shear_rate_avg_per_s": 380.0,
      "centroid_xyz_m": [0.0, 0.0, 0.06],
      "kolmogorov_length_m": 5.6e-5
    }
  ],
  "exchanges": [
    {"from_zone": "impeller", "to_zone": "bulk", "volumetric_flow_m3_per_s": 1.6e-5, "kind": "convective"},
    {"from_zone": "bulk", "to_zone": "impeller", "volumetric_flow_m3_per_s": 1.6e-5, "kind": "convective"},
    {"from_zone": "bulk", "to_zone": "near_wall", "volumetric_flow_m3_per_s": 4.2e-6, "kind": "convective"},
    {"from_zone": "near_wall", "to_zone": "bulk", "volumetric_flow_m3_per_s": 4.2e-6, "kind": "convective"}
  ]
}
```

Volume check: `5.4 + 12.0 + 82.6 = 100.0 cm³` → matches the 100 mL working volume.

Volume-weighted ε: `(5.4·75 + 12.0·8.5 + 82.6·4.8) / 100.0 = 9.0 W/kg` —
inconsistent with the metadata `12.4 W/kg`; loader would warn (this example
is illustrative only, real data will pass). For tests, generate the metadata
from the zones programmatically.

## Example 2 — Stirrer B, 4 zones (impeller / slot_exit / near_wall / bulk)

Rotor-stator with 36 stator perforations. Slot-exit jets carry 80–95% of
breakage events (Padron 2005, Hall 2011), so they get a dedicated zone.

```json
{
  "schema_version": "1.0",
  "case_metadata": {
    "case_name": "stirrer_B_beaker_100mL",
    "stirrer_type": "rotor_stator_B",
    "vessel": "beaker_100mm",
    "rpm": 6000,
    "fluid_temperature_K": 298.15,
    "openfoam_solver": "pimpleDyMFoam",
    "time_averaging_window_s": [1.0, 3.0],
    "n_cells_total": 12500000,
    "convergence_residual": 6.1e-6,
    "epsilon_volume_weighted_avg_W_per_kg": 48.7
  },
  "zones": [
    {
      "name": "impeller",
      "kind": "impeller_swept_volume",
      "volume_m3": 1.8e-6,
      "cell_count": 380000,
      "epsilon_avg_W_per_kg": 220.0,
      "epsilon_breakage_weighted_W_per_kg": 350.0,
      "shear_rate_avg_per_s": 22000.0,
      "centroid_xyz_m": [0.0, 0.0, 0.015],
      "kolmogorov_length_m": 8.7e-6
    },
    {
      "name": "slot_exit",
      "kind": "stator_slot_exit",
      "volume_m3": 4.5e-7,
      "cell_count": 95000,
      "epsilon_avg_W_per_kg": 850.0,
      "epsilon_breakage_weighted_W_per_kg": 1200.0,
      "shear_rate_avg_per_s": 38000.0,
      "centroid_xyz_m": [0.018, 0.0, 0.015],
      "kolmogorov_length_m": 5.2e-6,
      "metadata": {"notes": "36 stator holes × 3 rows; ε aggregated within 2mm of slot exit on stator outside"}
    },
    {
      "name": "near_wall",
      "kind": "near_wall",
      "volume_m3": 1.45e-5,
      "cell_count": 1800000,
      "epsilon_avg_W_per_kg": 18.0,
      "epsilon_breakage_weighted_W_per_kg": 25.0,
      "shear_rate_avg_per_s": 1400.0,
      "centroid_xyz_m": [0.045, 0.0, 0.04],
      "kolmogorov_length_m": 3.1e-5
    },
    {
      "name": "bulk",
      "kind": "bulk",
      "volume_m3": 8.327e-5,
      "cell_count": 10225000,
      "epsilon_avg_W_per_kg": 8.5,
      "epsilon_breakage_weighted_W_per_kg": 11.0,
      "shear_rate_avg_per_s": 480.0,
      "centroid_xyz_m": [0.0, 0.0, 0.06],
      "kolmogorov_length_m": 4.5e-5
    }
  ],
  "exchanges": [
    {"from_zone": "impeller", "to_zone": "slot_exit", "volumetric_flow_m3_per_s": 8.4e-5, "kind": "convective"},
    {"from_zone": "slot_exit", "to_zone": "bulk", "volumetric_flow_m3_per_s": 8.4e-5, "kind": "convective"},
    {"from_zone": "bulk", "to_zone": "impeller", "volumetric_flow_m3_per_s": 8.4e-5, "kind": "convective"},
    {"from_zone": "bulk", "to_zone": "near_wall", "volumetric_flow_m3_per_s": 9.8e-6, "kind": "convective"},
    {"from_zone": "near_wall", "to_zone": "bulk", "volumetric_flow_m3_per_s": 9.8e-6, "kind": "convective"}
  ]
}
```

Note the **flow loop** `impeller → slot_exit → bulk → impeller`: this is the
defining circulation pattern of a rotor-stator mixer. Exchange rates between
the loop and the near-wall zone are an order of magnitude lower because the
near-wall region is a recirculation eddy, not part of the main loop.

---

## Versioning policy

`schema_version: "1.0"` is the initial locked contract. Bump rules:

- **Patch** (`1.0.x`) — clarifications, additional optional fields, advisory warnings. Existing v1.0 files remain valid.
- **Minor** (`1.x.0`) — new required fields with sensible defaults inferable from existing data. Loader provides automatic migration with a deprecation warning.
- **Major** (`x.0.0`) — breaking changes. Loader emits a hard error and points to the migration script.

Known future extensions deferred from v1.0:

- Per-zone time-averaged temperature (when non-isothermal CFD is added).
- Time-resolved ε snapshots (when transient PBE coupling is added).
- Per-zone velocity statistics (for advanced collision-frequency models that don't follow CT-1977).
- Dispersed-phase fraction `phi_d_local` per zone (for highly inhomogeneous concentrated emulsions).
