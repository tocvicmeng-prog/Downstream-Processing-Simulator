# Quickstart Guide

## Installation

```bash
git clone https://github.com/tocvicmeng-prog/Downstream-Processing-Simulator.git
cd Downstream-Processing-Simulator
pip install -e .
```

## Your First Simulation

### Option 1: Command Line
```bash
# Show default parameters
python -m dpsim info

# Fast smoke (~1 s) — useful for verifying the install and CI gates
python -m dpsim run configs/fast_smoke.toml --quiet

# Full default research run (~4 min, dominated by L2 phase-field)
python -m dpsim run

# Run with custom RPM
python -m dpsim run --rpm 15000
```

### Expected baseline output

`fast_smoke.toml` should reliably produce (within rounding):

```
=== Simulation Results ===
  L1 Emulsification:  d32 = 22.08 um   span = 1.04
  L2 Gelation:        pore = 180.9 nm  porosity = 0.871
  L3 Crosslinking:    p = 0.040        G_chit = 2062 Pa
  L4 Mechanical:      G_DN = 70766 Pa  E* = 257332 Pa
```

These are uncalibrated semi-quantitative outputs (see Calibration below).
The `tests/test_smoke.py` gate (`pytest -m smoke`) verifies these stay
inside generous sanity bounds across releases. If you see materially
different values, the model defaults have drifted.

### Option 2: Web UI
```bash
python -m dpsim ui
# Open http://localhost:8501
```

The current UI is lifecycle-first. Work through:

1. Target Product Profile
2. M1 Fabrication
3. M2 Chemistry
4. M3 Column Method
5. Run Lifecycle Simulation
6. Validation & Evidence
7. Calibration

Each control writes into the active `ProcessRecipe`; the validation report,
evidence ladder, wet-lab SOP draft, and calibration comparison all read from
the same recipe.

### Option 3: Python API
```python
from dpsim import run_pipeline
result = run_pipeline()
print(f"d32 = {result.emulsification.d32*1e6:.1f} µm")
print(f"pore = {result.gelation.pore_size_mean*1e9:.0f} nm")
print(f"G_DN = {result.mechanical.G_DN/1000:.1f} kPa")
```

## Editing Parameters

Edit `configs/default.toml` or pass values via the CLI/UI:

```toml
[emulsification]
rpm = 15000
t_emulsification = 60.0

[formulation]
c_agarose = 42.0      # kg/m³ (4.2% w/v)
c_chitosan = 18.0     # kg/m³ (1.8% w/v)
c_span80 = 20.0       # kg/m³ (2.0% w/v)
phi_d = 0.05           # dispersed phase volume fraction

[solver.level1]
n_bins = 20
```

## Choosing Reagents

The legacy M1 path provides selectors for fabrication crosslinkers and
surfactants. The lifecycle path represents M2 chemistry as staged
`ProcessRecipe` steps:

- activation
- spacer/linker insertion
- ligand/protein coupling
- blocking/quenching
- washing
- storage-buffer exchange

Use built-in M2 templates such as `epoxy_protein_a`,
`edc_nhs_protein_a`, `hydrazide_protein_a`, `vinyl_sulfone_protein_a`,
`nta_imac`, and `ida_imac` when you need chemistry aligned to implemented
site-balance and evidence gates. If a wet-lab protocol is not represented by
an implemented `reagent_key`, document it as an external operation and do
not treat the simulator output as quantitative for that step.

## Interpreting Results

| Output | What it means | Target range |
|--------|--------------|--------------|
| d32 | Sauter mean droplet diameter | 50-150 µm for packed affinity media; smaller beads raise pressure sharply |
| Pore size | Mean macropore diameter | 60-150 nm for many protein-accessible hydrogel beads |
| G_DN | Double-network shear modulus | >10 kPa for column packing |
| Span | Size distribution width | <2.0 for uniformity |

## Running Optimization

```bash
python -m dpsim optimize --n-initial 15 --max-iter 100
```

## Uncertainty Quantification

```bash
python -m dpsim uncertainty --n-samples 20
```

## Lifecycle And Calibration CLI Commands

Beyond `run`/`sweep`/`optimize`/`uncertainty`/`info`/`ui`, DPSim includes:

```bash
# Run L2-L4 across DSD quantiles (batch variability, Node 19)
python -m dpsim batch --quantiles 0.10,0.50,0.90 configs/default.toml

# Emit a ProcessDossier JSON for reproducibility (Node 16)
python -m dpsim dossier configs/default.toml --output dossier.json

# Ingest wet-lab AssayRecord JSONs into a CalibrationStore fit JSON (Node 20)
python -m dpsim ingest L1 --assay-dir data/validation/l1_dsd/assays \
    --output data/validation/l1_dsd/fits/fit.json

# Fit M1 oil/surfactant wash-retention factors from residual assays
python -m dpsim ingest M1 --assay-dir data/validation/m1_washing/assays \
    --output data/validation/m1_washing/fits/fit.json

# Convert M1 physical QC assays into calibration/reference entries
python -m dpsim ingest M1QC --assay-dir data/validation/m1_physical_qc/assays \
    --output data/validation/m1_physical_qc/fits/fit.json

# Convert M2 ligand-density, activity-retention, leaching, and wash assays
python -m dpsim ingest M2 --assay-dir data/validation/m2_capacity/assays \
    --output data/validation/m2_capacity/fits/fit.json

# Convert M3 static binding, breakthrough curves, pressure-flow, and Langmuir assays
python -m dpsim ingest M3 --assay-dir data/validation/m3_binding/assays \
    --output data/validation/m3_binding/fits/fit.json

# Default uncertainty now uses the unified engine + parallel MC
python -m dpsim uncertainty --n-samples 50 --n-jobs 4
```

The default `uncertainty` engine is now `UnifiedUncertaintyEngine`
(consistent schema, calibration-store posterior absorption); pass
`--engine legacy` for v6.x byte-equivalent output.

## ProcessRecipe Lifecycle Inputs

The clean M1/M2/M3 lifecycle path can now run from a first-class wet-lab
`ProcessRecipe` artifact instead of only legacy solver TOML:

```bash
# Export the default Protein A affinity-media recipe
python -m dpsim recipe export-default --output recipe.toml

# Validate units, reagent windows, and resolver-level scientific gates
python -m dpsim recipe validate recipe.toml

# Run lifecycle from that recipe; legacy config still supplies solver settings
python -m dpsim lifecycle configs/fast_smoke.toml --recipe recipe.toml --no-dsd
```

If `dpsim lifecycle` receives a legacy config without `--recipe`, the CLI
bridges M1 fields such as rpm, emulsification time, oil temperature, Span-80,
cooling rate, and M1 wash settings into a `ProcessRecipe` before the backend
run. Lifecycle output now reports M1 DSD quantiles plus the qualitative
oil/surfactant wash residual estimate.

The lifecycle target product profile also owns downstream carryover limits:
`target.max_residual_oil_volume_fraction` and
`target.max_residual_surfactant_concentration`. The backend compares modeled
M1 wash residuals against these limits before M2/M3 claims are treated as
wet-lab feasible.

## Runtime Paths

DPSim avoids blocked system temp directories and fragile synchronized folders
for routine outputs. Override locations explicitly when needed:

```bash
set DPSIM_TMPDIR=C:\Users\<you>\DPSimTemp
set DPSIM_CACHE_DIR=C:\Users\<you>\DPSimCache
set DPSIM_OUTPUT_DIR=C:\Users\<you>\DPSimOutput
```

For deeper DSD propagation, use adaptive mode:

```bash
python -m dpsim lifecycle configs/fast_smoke.toml \
    --dsd-mode adaptive --dsd-max-representatives 9
```

Adaptive mode uses non-zero DSD bins when the requested maximum permits it;
otherwise it collapses the DSD to bounded volume-probability representatives
and reports weighted pressure/compression tail metrics.

To run full M3 LRM breakthrough for each DSD representative:

```bash
python -m dpsim lifecycle configs/fast_smoke.toml \
    --dsd-mode adaptive --dsd-max-representatives 3 --dsd-breakthrough
```

This reports DSD-weighted DBC10 mean/p50/p95 and the worst per-representative
mass-balance error. Keep the representative count small for smoke runs.

## Calibration

See `docs/04_calibration_protocol.md` for a 5-study wet-lab protocol to calibrate the simulation constants against your specific materials.

> **Note on Node 8 (v6.1):** The L2 empirical pore-size formula is
> independent of `alpha_final`. Node 8 wired `solve_gelation_empirical`
> to receive the actual Avrami output via `timing=` and reflect it in
> `model_manifest.diagnostics["alpha_final_from_timing"]`, but
> the pore-size prediction itself depends only on concentration +
> cooling rate + bead radius. Users will not see different pore numbers
> after Node 8 — the change is honest metadata reporting, not a physics
> update.

Once you have calibration data, supply it via `RunContext` (Node 7):

```python
from dpsim.calibration.calibration_store import CalibrationStore
from dpsim.datatypes import RunContext
from dpsim.pipeline.orchestrator import PipelineOrchestrator

store = CalibrationStore()
store.load_json("my_calibration.json")
ctx = RunContext(calibration_store=store)
result = PipelineOrchestrator().run_single(params, run_context=ctx)
# result.run_report.diagnostics["calibrations_applied"] lists every override.
```

The same `RunContext` can be supplied to the clean lifecycle orchestrator:

```python
from dpsim.lifecycle import DownstreamProcessOrchestrator

result = DownstreamProcessOrchestrator().run(
    params=params,
    run_context=ctx,
)
```

Calibration entries with `target_module="L1"` rewrite `KernelConfig` constants
(breakage_C1/C2/C3, coalescence_C4/C5); `"M1"` rewrites formulation/process
fields such as M1 wash retention factors; `"L2"`, `"L3"`, and `"L4"` rewrite
`MaterialProperties` fields. Lifecycle also uses M1 physical-QC entries:
`measured_pore_size_mean` and `measured_porosity` condition the M1-to-M2
handoff, while `measured_swelling_ratio` and `measured_bulk_modulus` remain
explicit diagnostics until a calibrated mapping is added. Lifecycle M3
consumes `target_module="M3"` entries: `measured_compression_modulus`
conditions the packed-bed mechanical state, `estimated_q_max` calibrates the
FunctionalMediaContract, `K_affinity`/`K_L` feed the Langmuir process state,
and `dbc_5_reference`/`dbc_10_reference`/`dbc_50_reference` are reported as
measured breakthrough references in the M3 graph diagnostics. Entries with
`posterior_uncertainty > 0` are also absorbed by `UnifiedUncertaintyEngine`.
For M1 wash fits, the uncertainty outputs include residual oil volume fraction
and residual surfactant concentration. Apply order is documented in
`pipeline/orchestrator.py` and `lifecycle/orchestrator.py`.

## Runtime expectations

| Config | Approximate runtime | When to use |
|---|---|---|
| `configs/fast_smoke.toml` | ~0.2 s | CI smoke gate, first install verification |
| `configs/default.toml` | ~4 minutes (n_grid=128 phase field) | Production research run |
| `configs/stirred_vessel.toml` | varies | Stirred-vessel mode comparison |

Set `[solver.level2].n_grid` lower (e.g. 32) to make the default config
finish in under a minute at the cost of pore-morphology resolution.

## Evidence tiers

Every `FullResult` and lifecycle result carries the weakest evidence tier
across the contributing models:

- `validated_quantitative` — calibrated against your specific system
- `calibrated_local` — calibrated against an analogous local system
- `semi_quantitative` — empirical or literature-based, not locally calibrated
- `qualitative_trend` — directional only
- `unsupported` — model not applicable to this chemistry/regime

The Bayesian optimizer (`python -m dpsim optimize`) excludes
`qualitative_trend` and `unsupported` candidates from the Pareto front by
default; each surviving Pareto point is labelled with its weakest tier in
`output/optimization/optimization_results.json`.
