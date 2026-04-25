# Downstream Processing Simulator

Lifecycle simulation of double-emulsification microsphere fabrication,
functional ligand crosslinking, and affinity chromatography performance.

## License And Intellectual Property

The intellectual property in this software, including the source code,
documentation, and accompanying assets, belongs to Holocyte Pty Ltd.

This software is licensed under the GNU General Public License, version 3.0
(GPL-3.0). See `LICENSE` for the full license text and `NOTICE` for the
project ownership notice.

This project is a fork of the upstream microsphere simulation codebase. It
keeps the useful numerical solvers, property models, calibration hooks, M2
chemistry state model, M3 chromatography solvers, and test coverage, but adds a
clean-slate process architecture for downstream processing work:

```text
M1 Fabrication
  emulsion formation -> gelation/morphology -> primary network -> mechanics
        |
        v
M2 Functionalization
  activation -> ligand/protein coupling -> quenching -> functional media
        |
        v
M3 Affinity Chromatography
  column packing -> breakthrough/elution -> pressure/mass balance -> DBC
```

The scientific intent is not to pretend that every number is production-grade.
Every result should carry units, provenance, assumptions, validation warnings,
and the weakest inherited evidence tier.

## Current Fork Status

Version `0.1.0` is an initial architecture fork.

Implemented in this fork:

- Package identity changed to `dpsim`.
- Project name changed to `downstream-processing-simulator`.
- Legacy M1/M2/M3 numerical code retained under the new `dpsim` package.
- New clean architecture primitives under `src/dpsim/core/`.
- New lifecycle orchestrator under `src/dpsim/lifecycle/`.
- New `dpsim lifecycle` CLI command for M1 -> M2 -> M3 simulation.
- Initial DSD quantile propagation screen from M1 into downstream M2/M3
  capacity and hydraulic-risk summaries.
- M2 washing/residual-reagent tracking carried into the
  `FunctionalMediaContract`.
- Handover documentation under `docs/handover/`.

The current lifecycle command reuses:

- M1 fabrication: legacy `PipelineOrchestrator`.
- M2 functionalization: ECH activation -> Protein A coupling -> ethanolamine
  quench with modeled wash steps through `ModificationOrchestrator`.
- M3 performance: LRM breakthrough through `run_breakthrough`, consuming the
  `FunctionalMediaContract`.

## Install

Use a Python 3.11 or 3.12 interpreter. The fork keeps the inherited dependency
policy in `pyproject.toml` because several scientific packages and optimization
extras need explicit compatibility verification before widening the range.

```bash
cd "C:\Users\tocvi\OneDrive\文档\Project_Code\EmulSim\Downstream Processing Simulator"
pip install -e .
```

For a no-install source-tree check in PowerShell:

```powershell
$env:PYTHONPATH = "src"
python -m dpsim lifecycle configs/fast_smoke.toml
```

Optional extras:

```bash
pip install -e ".[dev]"
pip install -e ".[ui]"
pip install -e ".[optimization]"
pip install -e ".[all]"
```

## Run

Run the clean-slate lifecycle path:

```bash
python -m dpsim lifecycle configs/fast_smoke.toml
```

Run the reused legacy fabrication pipeline:

```bash
python -m dpsim run configs/fast_smoke.toml
```

Launch the reused Streamlit UI:

```bash
python -m dpsim ui
```

## Python API

```python
from dpsim.lifecycle import DownstreamProcessOrchestrator

result = DownstreamProcessOrchestrator().run()

print(result.weakest_evidence_tier.value)
print(result.functional_media_contract.installed_ligand)
print(result.m3_breakthrough.dbc_10pct)
```

## Architecture

New clean-slate architecture modules:

```text
src/dpsim/core/
  quantities.py        # unit-aware scalar values
  parameters.py        # resolved parameters and source priority
  process_recipe.py    # wet-lab process recipe objects
  result_graph.py      # M1/M2/M3 result graph and evidence roll-up
  validation.py        # backend validation report objects
  model_registry.py    # model capability registry

src/dpsim/lifecycle/
  orchestrator.py      # high-level M1 -> M2 -> M3 orchestration
```

Reused solver modules:

```text
src/dpsim/pipeline/                    # M1 legacy L1-L4 orchestration
src/dpsim/level1_emulsification/       # PBE and hydrodynamic kernels
src/dpsim/level2_gelation/             # pore/morphology models
src/dpsim/level3_crosslinking/         # primary network kinetics
src/dpsim/level4_mechanical/           # bead mechanics
src/dpsim/module2_functionalization/   # ACS, reactions, reagent profiles
src/dpsim/module3_performance/         # LRM, isotherms, hydrodynamics
src/dpsim/calibration/                 # calibration records and stores
```

## Documentation

Start here:

- `docs/handover/INITIAL_HANDOVER.md`
- `docs/DPS_CLEAN_SLATE_ARCHITECTURE.md`
- `docs/03_architecture_modification_plan.md`

The copied DPSim documents remain as scientific provenance and legacy
reference material. New Downstream Processing Simulator documentation should
prefer the `DPS_*` and `docs/handover/` documents.

## Scientific Operating Rules

- Use SI units internally and convert lab units at the recipe/UI boundary.
- Treat Protein A and other affinity capacities as ranking-only until
  target-specific binding or breakthrough calibration exists.
- Do not let M3 evidence exceed the inherited M2 media-contract evidence.
- Do not use a single bead diameter when a distribution is required for the
  decision; the lifecycle path now performs an initial DSD quantile screen, and
  future production workflows should extend it to full method simulation.
- Block or downgrade any run that violates mass, site, pressure, chemistry, or
  calibration-domain gates.

## Development Notes

This fork intentionally keeps compatibility with the reused solver stack while
new clean architecture layers are added. Prefer adding adapters rather than
rewriting numerical kernels until the lifecycle pathway has its own validation
data.

The immediate next engineering tasks are listed in
`docs/handover/INITIAL_HANDOVER.md`.
