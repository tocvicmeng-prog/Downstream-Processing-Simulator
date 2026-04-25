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

Version `0.2.0` — Functional-Optimization initiative (Tiers 1–3) complete.

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

### Functional-Optimization initiative (v0.2.0)

Three SA-screened candidate cycles delivered between 2026-04-25
sessions, processing all 50 candidates from the Scientific Advisor's
functional-optimization screening:

- **Tier 1** (18 candidates) — schema expansion + 18 reagent profiles
  spanning M1–M9 workflow batches (CNBr / CDI / hexyl HIC; periodate /
  ADH / aminooxy-PEG glycoprotein chain; Cibacron Blue dye-affinity;
  MEP HCIC + thiophilic mixed-mode antibody capture; PEGDGE/EGDGE/BDDE
  bis-epoxide hardening; CuAAC + SPAAC click chemistry; glyoxyl-agarose
  multipoint enzyme immobilization; amylose-MBP material-as-ligand;
  aminophenylboronic-acid boronate affinity).
- **Tier 2** (17 candidates) — 6 polymer families promoted to UI
  (HYALURONATE, KAPPA_CARRAGEENAN, AGAROSE_DEXTRAN, AGAROSE_ALGINATE,
  ALGINATE_CHITOSAN, CHITIN) + 13 supporting reagent profiles (Procion
  Red, p-aminobenzamidine, Jacalin, lentil lectin, oligonucleotide,
  HWRGWV peptide-affinity, HRP-tyramine, oligoglycine / cystamine /
  succinic-anhydride spacers, tresyl + pyridyl-disulfide activations).
- **Tier 3** (11 candidates) — 4 polymer families promoted (PECTIN,
  GELLAN, PULLULAN, STARCH) + Al³⁺ trivalent gelant
  (`biotherapeutic_safe=False`), borax reversible crosslinker, glyoxal
  dialdehyde, calmodulin CBP/TAP-tag.
- **Tier 4** — POCl₃ formally rejected via `docs/decisions/ADR-003`
  (hazard outweighs value; STMP covers the bioprocess subset).

Cumulative state: 25 ACS site types · 21 PolymerFamily entries (18
UI-enabled) · 94 ReagentProfile entries · 11 ion-gelation registry
entries · 7 new L2 solver modules · 3 ADRs · 510+ tests.

Wet-lab Track 2 (Q-013/Q-014) remains scheduled bench work; the
simulator's calibration-ingestion path is implemented in
`src/dpsim/calibration/wetlab_ingestion.py` with a YAML schema and
example campaigns under `data/wetlab_calibration_examples/`.

### What the lifecycle command reuses

- M1 fabrication: legacy `PipelineOrchestrator` (now with
  `_run_v9_2_tier1` branch routing the 10 v0.2 polymer families through
  `level2_gelation/composite_dispatch.py`).
- M2 functionalization: 12 specialised ligand-type branches
  (`affinity`, `iex_anion/cation`, `imac`, `hic`, `gst_affinity`,
  `biotin_affinity`, `heparin_affinity`, `dye_pseudo_affinity`,
  `mixed_mode_hcic`, `thiophilic`, `boronate`, `peptide_affinity`,
  `oligonucleotide`, `material_as_ligand`) via
  `ModificationOrchestrator`.
- M3 performance: LRM breakthrough through `run_breakthrough`, consuming
  the `FunctionalMediaContract`.

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

- `docs/handover/INITIAL_HANDOVER.md` — fork kickoff
- `docs/DPS_CLEAN_SLATE_ARCHITECTURE.md` — clean-slate architecture
- `docs/03_architecture_modification_plan.md` — architecture modification plan

### v0.2.0 Functional-Optimization handover trail

The v0.2 functional-optimization initiative produced a self-contained
handover series that records the full design → implementation → close
arc for the SA Tier-1, Tier-2, and Tier-3 cycles:

- `docs/handover/SA_v9_2_FUNCTIONAL_OPTIMIZATION_SCREENING.md` —
  Scientific Advisor candidate ranking (50 candidates → 4 tiers).
- `docs/handover/ARCH_v9_2_MODULE_DECOMPOSITION.md` — Architect
  module-level decomposition for Tier 1.
- `docs/handover/DEVORCH_v9_2_JOINT_PLAN.md` — orchestrator master plan.
- `docs/handover/HANDOVER_v9_2_M0a.md` / `M0b.md` /
  `HANDOVER_v9_2_CLOSE.md` — Tier-1 cycle (foundation +
  refactors + close).
- `docs/handover/HANDOVER_v9_3_FOLLOWONS_CLOSE.md` /
  `HANDOVER_v9_3_CLOSE.md` — Tier-2 cycle.
- `docs/handover/HANDOVER_v9_4_CLOSE.md` — Tier-3 cycle close.
- `docs/handover/WETLAB_v9_3_CALIBRATION_PLAN.md` — wet-lab calibration
  brief (Q-013/Q-014); pending bench execution.
- `docs/decisions/ADR-003-pocl3-tier-4-rejection.md` — Tier-4 rejection.

> **Naming note:** the handover documents use internal cycle names
> `v9.2`/`v9.3`/`v9.4` to label the Tier-1/Tier-2/Tier-3 SA cycles.
> These are **internal cycle labels**, not project versions — the
> project's effective version is `v0.2.0`. The upstream simulator's
> v9.x release line (last release `v9.2.2` on 2026-04-24) is a
> separate numbering scheme that pre-dates the SA cycles.

The copied DPSim documents remain as scientific provenance and legacy
reference material. New Downstream Processing Simulator documentation should
prefer the `DPS_*`, `docs/handover/`, and `docs/decisions/` documents.

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
