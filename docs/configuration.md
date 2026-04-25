# Configuration Reference

DPSim has two configuration layers:

1. Legacy solver TOML files such as `configs/default.toml` and
   `configs/fast_smoke.toml`. These still configure inherited M1/L1-L4 solver
   settings and fast smoke runs.
2. Lifecycle `ProcessRecipe` files serialized by `dpsim.core.recipe_io`.
   These are the authoritative source for target product profile, M1
   fabrication operations, M2 functionalization steps, and M3 column method.

For lifecycle work, edit or export a `ProcessRecipe` and validate it before
running:

```bash
python -m dpsim recipe export-default --output recipe.toml
python -m dpsim recipe validate recipe.toml
python -m dpsim lifecycle configs/fast_smoke.toml --recipe recipe.toml
```

Legacy TOML parameters can also be overridden via CLI flags or the Python API.

## `[simulation]`

| Parameter | Default | Type | Description |
|-----------|---------|------|-------------|
| `run_id` | `""` | string | Identifier for this simulation run |
| `notes` | `""` | string | Free-text notes |

## `[emulsification]`

Process parameters for Level 1 (rotor-stator emulsification).

| Parameter | Default | Unit | Description |
|-----------|---------|------|-------------|
| `rpm` | `10000` | rev/min | Rotor speed |
| `t_emulsification` | `60.0` | s | Emulsification duration (time to reach steady-state DSD) |

### `[emulsification.mixer]`

Rotor-stator mixer geometry.

| Parameter | Default | Unit | Description |
|-----------|---------|------|-------------|
| `rotor_diameter` | `0.025` | m | Rotor outer diameter (25 mm) |
| `stator_diameter` | `0.026` | m | Stator inner diameter |
| `gap_width` | `0.0005` | m | Rotor-stator gap (0.5 mm) |
| `tank_volume` | `0.0005` | m^3 | Vessel volume (500 mL) |
| `power_number` | `1.5` | - | Turbulent power number N_P |
| `dissipation_ratio` | `50.0` | - | Ratio of max to mean energy dissipation rate (epsilon_max / epsilon_avg) |

## `[formulation]`

Chemical formulation and process temperatures.

| Parameter | Default | Unit | Description |
|-----------|---------|------|-------------|
| `c_agarose` | `42.0` | kg/m^3 | Agarose concentration (4.2% w/v for 7:3 blend at 6% total) |
| `c_chitosan` | `18.0` | kg/m^3 | Chitosan concentration (1.8% w/v) |
| `c_span80` | `20.0` | kg/m^3 | Span-80 surfactant concentration (~2% w/v) |
| `c_genipin` | `2.0` | mol/m^3 | Genipin crosslinker concentration (~2 mM) |
| `T_oil` | `363.15` | K | Oil bath temperature during emulsification (90 deg C) |
| `cooling_rate` | `0.167` | K/s | Cooling rate after emulsification (~10 deg C/min) |
| `T_crosslink` | `310.15` | K | Crosslinking incubation temperature (37 deg C) |
| `t_crosslink` | `86400.0` | s | Crosslinking incubation time (24 hours) |
| `phi_d` | `0.05` | - | Dispersed phase volume fraction |
| `m1_initial_oil_carryover_fraction` | `0.10` | fraction | Oil retained with collected wet beads before drain/resuspend washing |
| `m1_wash_cycles` | `3` | - | Number of M1 drain/resuspend wash cycles after oil-phase bead collection |
| `m1_wash_volume_ratio` | `3.0` | - | Wash liquid volume per wet bead/slurry volume for each cycle |
| `m1_wash_mixing_efficiency` | `0.80` | fraction | Fractional approach to well-mixed extraction per wash cycle |
| `m1_oil_retention_factor` | `1.0` | - | Lumped extraction retention factor for oil; larger values mean harder removal |
| `m1_surfactant_retention_factor` | `1.5` | - | Lumped extraction retention factor for Span-80; larger values mean harder removal |

### Derived properties

- `agarose_fraction` = `c_agarose / (c_agarose + c_chitosan)` -- mass fraction of agarose in the polymer blend
- `total_polymer` = `c_agarose + c_chitosan` -- total polymer concentration [kg/m^3]
- M1 wash residuals are estimated with a qualitative well-mixed extraction
  model. Calibrate `m1_oil_retention_factor` and
  `m1_surfactant_retention_factor` from residual oil/surfactant assays before
  using wash residuals for release decisions.
- Clean lifecycle runs compare these residuals against recipe target limits
  (`target.max_residual_oil_volume_fraction` and
  `target.max_residual_surfactant_concentration`) before passing M2/M3 results
  as wet-lab feasible screening outputs.

## `[solver.level1]`

Numerical settings for the Population Balance Equation (PBE) solver.

| Parameter | Default | Unit | Description |
|-----------|---------|------|-------------|
| `n_bins` | `20` | - | Number of size bins in the PBE discretization |
| `d_min` | `1e-6` | m | Minimum droplet diameter (1 um) |
| `d_max` | `500e-6` | m | Maximum droplet diameter (500 um). Must exceed premix d32 by >= 3 sigma |
| `rtol` | `1e-6` | - | Relative tolerance for ODE integrator |
| `atol` | `1e-8` | - | Absolute tolerance for ODE integrator |

## `[solver.level2]`

Numerical settings for Level 2 (gelation and phase-field solver).

| Parameter | Default | Unit | Description |
|-----------|---------|------|-------------|
| `n_r` | `1000` | - | Number of radial grid points (1D solver) |
| `n_grid` | `128` | - | 2D grid side length (N x N Cahn-Hilliard solver) |
| `dt_initial` | `1e-4` | s | Initial time step |
| `dt_max` | `1.0` | s | Maximum adaptive time step |
| `arrest_exponent` | `2.5` | - | Gelation arrest exponent beta: mobility ~ (1 - alpha)^beta |

## `[solver.level3]`

Numerical settings for Level 3 (crosslinking ODE kinetics).

| Parameter | Default | Unit | Description |
|-----------|---------|------|-------------|
| `method` | `"Radau"` | - | SciPy ODE solver method (Radau, BDF, RK45, etc.) |
| `rtol` | `1e-8` | - | Relative tolerance |
| `atol` | `1e-10` | - | Absolute tolerance |

## `[optimization]`

Settings for the BoTorch Bayesian optimization campaign.

| Parameter | Default | Unit | Description |
|-----------|---------|------|-------------|
| `n_initial` | `20` | - | Number of Sobol quasi-random initial evaluations |
| `max_iterations` | `200` | - | Maximum optimization iterations |
| `convergence_tol` | `0.01` | - | Relative hypervolume convergence tolerance |

## Material Properties

Material properties are loaded from `data/properties.toml` and are not normally
edited in the run configuration. Key defaults (from `MaterialProperties` dataclass):

| Property | Default | Unit | Description |
|----------|---------|------|-------------|
| `rho_oil` | `850.0` | kg/m^3 | Oil density at 20 deg C (interpolated to T_oil) |
| `mu_oil` | `0.005` | Pa s | Oil dynamic viscosity at 90 deg C |
| `rho_aq` | `1020.0` | kg/m^3 | Aqueous phase density |
| `mu_d` | `1.0` | Pa s | Dispersed phase viscosity at T_oil |
| `sigma` | `5.0e-3` | N/m | Interfacial tension with Span-80 |
| `chi_0` | `0.497` | - | Flory-Huggins interaction parameter at reference T |
| `kappa_CH` | `5.0e-12` | J/m | Cahn-Hilliard gradient energy coefficient |
| `M_0` | `1.0e-9` | m^5/(J s) | Bare mobility (calibrated for 50-100 nm coarsening) |
| `T_gel` | `311.15` | K | Gelation temperature (~38 deg C) |
| `k_gel_0` | `1.0` | 1/s | Avrami rate prefactor |
| `n_avrami` | `2.5` | - | Avrami exponent |
| `k_xlink_0` | `2806.0` | m^3/(mol s) | Crosslinking Arrhenius prefactor |
| `E_a_xlink` | `52000.0` | J/mol | Crosslinking activation energy |
| `DDA` | `0.90` | - | Chitosan degree of deacetylation |
| `G_agarose_prefactor` | `3000.0` | Pa | Agarose gel modulus prefactor at 1% w/v |
| `G_agarose_exponent` | `2.2` | - | Power-law exponent for agarose modulus vs concentration |
| `f_bridge` | `0.4` | - | Fraction of genipin reactions producing elastically active crosslinks |
| `eta_coupling` | `-0.15` | - | IPN coupling coefficient (negative = synergistic) |
| `breakage_C3` | `0.0` | - | Alopaeus viscous correction constant (0 = disabled) |
| `r_fiber` | `1.5e-9` | m | Agarose fiber radius |

## CLI Overrides

Common parameters can be overridden directly on the command line:

```bash
python -m dpsim run --rpm 15000 --phi-d 0.08
python -m dpsim run configs/custom.toml --rpm 12000
```

The precedence order is: CLI flags > TOML file > dataclass defaults.

## Lifecycle `ProcessRecipe` Parameters

Lifecycle recipes are serialized TOML artifacts containing `target`,
`material_batch`, `equipment`, and ordered `steps`. Each step has a
`stage`, `kind`, `parameters`, notes, and required QC records.

### Target product profile

| Field | Unit | Meaning |
|---|---|---|
| `target.bead_d50` | um | Design median bead diameter for fabrication and pressure-risk checks |
| `target.pore_size` | nm | Design pore size or accessibility scale for protein transport |
| `target.min_modulus` | kPa | Minimum mechanical target before column packing |
| `target.target_ligand` | text | Ligand intended for M2, e.g. Protein A |
| `target.target_analyte` | text | Molecule captured in M3, e.g. IgG |
| `target.max_pressure_drop` | bar | Method operability limit |
| `target.max_residual_oil_volume_fraction` | fraction | Development screening limit for M1 oil carryover |
| `target.max_residual_surfactant_concentration` | kg/m^3 | Development screening limit for retained surfactant |

### M1 fabrication steps

| Step kind | Required parameters | Operational requirement |
|---|---|---|
| `prepare_phase` | oil temperature, surfactant concentration | Record phase clarity, viscosity, and lot identity |
| `emulsify` | rpm, time | Measure DSD by microscopy or laser diffraction |
| `cool_or_gel` | cooling rate, wash cycles, wash volume ratio, wash mixing efficiency, oil/surfactant retention factors | Assay residual oil/surfactant, swelling, pore structure, and modulus |

### M2 functionalization steps

| Step kind | Required parameters | Operational requirement |
|---|---|---|
| `activate` | `reagent_key`, pH, temperature, time, reagent concentration | Confirm unit consistency and reagent validity; avoid incompatible buffers |
| `insert_spacer` | `reagent_key`, pH, temperature, time, reagent concentration | Confirm spacer/site density before coupling |
| `couple_ligand` | `reagent_key`, pH, temperature, time, ligand concentration | Measure ligand density, free ligand/protein in wash fractions, and activity retention |
| `block_or_quench` / `quench` | `reagent_key`, pH, temperature, time, quench concentration | Verify residual reactive sites are below the lab threshold |
| `wash` | buffer identity, pH, temperature, time | Keep incompatible reagents out of the next step |
| `storage_buffer_exchange` | buffer identity, pH, conductivity where available, temperature, time | Confirm storage pH/conductivity and leaching risk |

### M3 column method steps

| Step kind | Required parameters | Operational requirement |
|---|---|---|
| `pack_column` | column diameter, bed height, bed porosity, packing flow rate | Record settled bed height, bed compression, and pressure-flow curve |
| `equilibrate` | buffer pH, conductivity, flow rate, duration | Confirm outlet pH/conductivity match inlet |
| `load` | feed concentration, pH, conductivity, flow rate, feed duration, residence time | Compare predicted DBC/breakthrough with measured breakthrough |
| `wash` | pH, conductivity, flow rate, duration | Collect wash fractions until UV returns to baseline |
| `elute` | pH or gradient field, conductivity, flow rate, duration | Collect and neutralize fractions promptly; assay recovery and ligand leaching |

## Runtime Path Environment Variables

| Variable | Meaning |
|---|---|
| `DPSIM_TMPDIR` | Writable temporary directory used by UI uploads and tests |
| `DPSIM_CACHE_DIR` | Writable cache directory |
| `DPSIM_OUTPUT_DIR` | Base output directory for CLI, lifecycle, calibration, optimization, and UI runs |
