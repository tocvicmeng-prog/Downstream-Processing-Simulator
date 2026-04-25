# DPSim — Downstream Processing Simulator

**Polysaccharide-microsphere fabrication, functionalisation, and affinity-chromatography lifecycle simulator.**

[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%20|%203.12-3776AB.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/Version-0.3.8-2DD4BF.svg)](CHANGELOG.md)
[![Platform](https://img.shields.io/badge/Platform-Windows%2011%20x64-0078D4.svg)](https://github.com/tocvicmeng-prog/Downstream-Processing-Simulator/releases)

> Turn a written lifecycle recipe into predicted microsphere-media behaviour **before** you touch the bench. Predictions carry units, evidence tier, assumptions, validation gates, and wet-lab caveats — every value tells you exactly how much to trust it.

---

## Table of Contents

- [What DPSim Does](#what-dpsim-does)
- [Functionalities at a Glance](#functionalities-at-a-glance)
- [Installation](#installation)
- [System Requirements](#system-requirements)
- [Quickstart](#quickstart)
- [Repository Structure](#repository-structure)
- [Microsphere Fabrication Pathways](#microsphere-fabrication-pathways)
- [Operating Principles](#operating-principles)
- [Development Philosophy](#development-philosophy)
- [Usage Considerations](#usage-considerations)
- [Documentation Map](#documentation-map)
- [Version History](#version-history)
- [Intellectual Property and Licence](#intellectual-property-and-licence)
- [Citation](#citation)
- [Contributing and Support](#contributing-and-support)
- [Disclaimer](#disclaimer)

---

## What DPSim Does

DPSim is a **lifecycle simulator** for polysaccharide-based affinity microsphere media. It models three sequential process modules:

| Module | Wet-lab stage | Predicted outputs |
|---|---|---|
| **M1** | Double-emulsification microsphere fabrication | Bead size distribution (DSD), d10/d32/d50/d90, pore architecture, mechanical modulus, residual oil/surfactant after wash |
| **M2** | Functionalisation, reinforcement, ligand coupling | Reactive-site inventory (ACS state vector), ligand density, activity retention, leaching/wash caveats |
| **M3** | Affinity-column performance | Pack/equilibrate/load/wash/elute behaviour, breakthrough curve, pressure profile, dynamic binding capacity (DBC), recovery, optional Monte-Carlo uncertainty bands |

The simulator exists for one reason: **screening**. It tells you what to expect, with explicit uncertainty, so you can narrow your bench parameter space, predict failure modes, and plan calibration experiments before consuming reagents and operator time.

---

## Functionalities at a Glance

### Modelling capabilities (v0.3.8)

- **21 selectable polymer families** spanning the v9.1 baseline (agarose-chitosan, alginate, cellulose-NIPS, PLGA), the v9.2/v9.3 expansion (10 families), the v9.4 niche set (4 families), and the v9.5 multi-variant composites (3 families).
- **96 functionalisation reagents** across **17 chemistry buckets** — secondary crosslinking, hydroxyl activation, ligand coupling (IEX/HIC/IMAC/GST/heparin), protein coupling (Protein A/G/L, streptavidin, lectins, oriented Cys variants), spacer arms, metal charging, protein pretreatment, washing, quenching, plus eight specialty buckets (click, dye pseudo-affinity, mixed-mode HCIC, thiophilic, boronate, peptide-affinity, oligonucleotide, material-as-ligand).
- **13 ion-gelant profiles** (per-family + freestanding) with biotherapeutic-safety flags.
- **25 surface-chemistry site types** tracked through the M2 ACS state vector.
- **Lumped Rate Model (LRM)** chromatography solver with axial-dispersion + film-mass-transfer + Langmuir adsorption physics.
- **Monte-Carlo LRM uncertainty driver** (v0.3.0) — propagates posterior uncertainty in q_max / K_L / pH parameters through the LRM and reports P05/P50/P95 envelopes on every metric and curve, with reformulated convergence diagnostics (quantile-stability + inter-seed posterior overlap).
- **Optional Bayesian posterior fitting** (v0.3.1) — fit Langmuir parameters from raw isotherm assay data via pymc/NUTS with mandatory R-hat / ESS / divergence convergence gates.
- **Calibration store** for ingesting wet-lab measurements and overriding screening defaults.
- **Evidence-tier inheritance** — every predicted value carries one of five tiers (validated_quantitative → calibrated_local → semi_quantitative → qualitative_trend → unsupported). M3 cannot claim stronger evidence than its M2 inputs; M2 cannot claim stronger than its M1 inputs.

### User-facing surfaces

- **Streamlit dashboard** at `localhost:8501` — seven-step lifecycle workflow with interactive inputs, per-module result panels, validation report, evidence ladder, and run history.
- **CLI** — `python -m dpsim run|lifecycle|recipe|ui` for batch processing and CI integration.
- **Python API** — direct access to `DownstreamProcessOrchestrator`, `run_method_simulation`, `run_mc`, `fit_langmuir_posterior`, and the calibration store.
- **Bundled documentation** — First Edition manual + Appendix J wet-lab protocols accessible via the upper-right corner of the dashboard.

---

## Installation

DPSim ships **three** installation paths. Pick the one that matches your situation.

### 1. One-click Windows installer (recommended for end-users)

Download from the GitHub Releases page:

> [**Releases → DPSim-0.3.8-Setup.exe**](https://github.com/tocvicmeng-prog/Downstream-Processing-Simulator/releases/latest)

Double-click the `.exe`. The installer:

1. Shows the EULA page first — Holocyte Pty Ltd IP, GPL-3.0, GitHub source URL.
2. Installs to `%LOCALAPPDATA%\Programs\DPSim` (per-user; no admin needed).
3. Detects whether Python 3.11/3.12 is on PATH and offers to open the python.org download page if missing.
4. Creates an isolated `.venv\` and pip-installs the bundled wheel.
5. Adds Start-Menu and (optional) desktop shortcuts.
6. Offers to launch the dashboard immediately.

### 2. Portable ZIP (no installation)

Download from the same Releases page:

> [**Releases → DPSim-0.3.8-Windows-x64-portable.zip**](https://github.com/tocvicmeng-prog/Downstream-Processing-Simulator/releases/latest)

Extract anywhere (e.g. `D:\Apps\DPSim`). Run `install.bat` once, then `launch_ui.bat` to start. To uninstall, delete the folder — no registry or Start-Menu trace.

### 3. Source install (developers)

```bash
git clone https://github.com/tocvicmeng-prog/Downstream-Processing-Simulator
cd "Downstream-Processing-Simulator"
pip install -e .
```

Optional extras:

```bash
pip install -e ".[dev]"           # tests + linting
pip install -e ".[ui]"            # streamlit + plotly
pip install -e ".[optimization]"  # botorch + gpytorch + torch
pip install -e ".[bayesian]"      # pymc + arviz (G4 NUTS posterior fit)
pip install -e ".[all]"           # everything
```

For an in-place check without installing:

```powershell
$env:PYTHONPATH = "src"
python -m dpsim lifecycle configs/fast_smoke.toml
```

---

## System Requirements

| Requirement | Supported | Notes |
|---|---|---|
| Operating system | Windows 11 x64 (Windows 10 x64 also works) | macOS / Linux work for the source install but no native installer is shipped |
| Python | **3.11 or 3.12** | 3.13+ unsupported per [`docs/decisions/ADR-001`](docs/decisions/) (scipy BDF + numba JIT cache issues) |
| RAM | 8 GB recommended (4 GB minimum) | MC-LRM with N≥1000 samples can use 1-2 GB |
| Disk | 2 GB free for the local `.venv\` | Wheel itself is ≈ 2 MB |
| Network | Internet during first install | pip downloads ~1 GB of scientific dependencies (numpy, scipy, plotly, streamlit, …) |
| GPU | Not required | Optional for `[optimization]` extra (botorch on CUDA) |

---

## Quickstart

### Launch the dashboard

```bash
python -m dpsim ui
```

The dashboard binds to `http://localhost:8501`. Your default browser should open automatically.

### First-run recipe

The default recipe is **agarose-chitosan + Protein A**, calibrated for first-time users:

1. Open the **Polymer Family** tab on M1, leave AGAROSE_CHITOSAN selected.
2. Open M2, pick the `epoxy_protein_a` template.
3. Open M3, leave the default Protein A method (bind pH 7.4, elute pH 3.5).
4. Click **Run Lifecycle Simulation**.
5. Review the **Validation & Evidence** panel — every numeric output carries its evidence tier.

### CLI examples

```bash
python -m dpsim run configs/default.toml
python -m dpsim recipe export-default --output recipe.toml
python -m dpsim lifecycle configs/fast_smoke.toml --recipe recipe.toml
```

### Python API

```python
from dpsim.lifecycle import DownstreamProcessOrchestrator

result = DownstreamProcessOrchestrator().run()
print(result.weakest_evidence_tier.value)
print(result.functional_media_contract.installed_ligand)
print(result.m3_breakthrough.dbc_10pct)
```

### Monte-Carlo uncertainty (advanced)

```python
from dpsim.calibration import PosteriorSamples
from dpsim.module3_performance.mc_solver_lambdas import make_langmuir_lrm_solver
from dpsim.module3_performance.monte_carlo import run_mc

samples = PosteriorSamples.from_marginals(
    parameter_names=("q_max", "K_L"),
    means=[50.0, 1e-3],
    stds=[2.5, 1e-4],
)
solver = make_langmuir_lrm_solver(column=col, C_feed=1.0, ...)
bands = run_mc(samples, solver, n=200, n_seeds=4, n_jobs=4)
print(bands.scalar_quantiles["mass_eluted"])  # P05/P50/P95
```

---

## Repository Structure

```
Downstream-Processing-Simulator/
├── src/dpsim/                          # Production source
│   ├── core/                           # Quantities, parameters, ProcessRecipe, evidence roll-up
│   ├── lifecycle/                      # M1→M2→M3 orchestrator
│   ├── pipeline/                       # M1 fabrication pipeline (legacy L1-L4 kernels)
│   ├── level1_emulsification/          # Population balance + hydrodynamics
│   ├── level2_gelation/                # Polymer-family L2 solvers + composite dispatch + ion registry
│   ├── level3_crosslinking/            # Primary network kinetics
│   ├── level4_mechanical/              # Bead mechanics
│   ├── module2_functionalization/      # ACS state, reagent profiles (96 entries), reactions
│   ├── module3_performance/            # LRM, isotherms, hydrodynamics, MC-LRM driver, solver-lambdas
│   ├── calibration/                    # Calibration data, store, wet-lab ingestion, posterior samples, Bayesian fit
│   ├── visualization/                  # Streamlit app, M1/M2/M3 tabs, plot modules
│   ├── optimization/                   # Bayesian optimisation (optional [optimization] extra)
│   ├── reagent_library*.py             # M1 crosslinker / surfactant / gelant registries
│   └── datatypes.py                    # PolymerFamily, ACSSiteType, ModelEvidenceTier, ModelMode enums
│
├── tests/                              # 510+ tests across all modules + AST gates
├── configs/                            # Default + smoke + stirred-vessel TOML recipes
├── data/wetlab_calibration_examples/   # Q-013/Q-014 example campaigns (YAML)
├── docs/
│   ├── user_manual/                    # First Edition manual + Appendix J + PDFs
│   ├── handover/                       # Cycle handovers (planning + close documents)
│   ├── decisions/                      # ADRs
│   └── *.md                            # Topic-specific design notes
├── installer/                          # Inno Setup .iss + build script + EULA + templates
├── DESIGN.md                           # Visual / UI design system (read before any UI change)
├── CLAUDE.md                           # Project-specific contributor guidelines
├── CHANGELOG.md                        # Version history
├── LICENSE                             # GPL-3.0 full text
├── NOTICE                              # IP attribution (Holocyte Pty Ltd)
└── pyproject.toml                      # Package metadata, dependencies, extras
```

---

## Microsphere Fabrication Pathways

DPSim covers **four classes** of polysaccharide-microsphere fabrication chemistry. Pick a pathway based on your application.

### Pathway 1 — Thermal helix-coil + covalent secondary network

**Mechanism.** A hot polysaccharide solution (typically agarose ± chitosan) is emulsified into oil with a surfactant. On cooling below the gel temperature (~38 °C for agarose), helix-coil junction zones form. A subsequent amine-reactive crosslinker (genipin / glutaraldehyde / epichlorohydrin / DVS / BDDE / STMP) covalently locks chitosan into a second interpenetrating network.

**Polymer families:** AGAROSE_CHITOSAN (default, the v9.1 baseline), AGAROSE (Sepharose-class baseline), CHITOSAN, AGAROSE_DEXTRAN (Capto-class core-shell).

**Strengths.** High modulus (1–10 MPa), well-validated, protein-compatible.
**Trade-offs.** Slow crosslinking (24 h for genipin), hot emulsification, blue tint from genipin.

### Pathway 2 — Ionotropic gelation (egg-box / helix aggregation)

**Mechanism.** An anionic polysaccharide solution is emulsified or extruded as droplets, which contact a multivalent cation bath. The cation bridges paired carboxylate or sulfate residues into junction zones, forming a gel near-instantly. No covalent chemistry.

**Variants and ions:**

| Family | Ion | Mechanism reference |
|---|---|---|
| ALGINATE | Ca²⁺ (CaCl₂ external bath, GDL/CaCO₃ internal release, or CaSO₄ internal release) | Egg-box of G-block guluronate (Draget 1997) |
| KAPPA_CARRAGEENAN | K⁺ (specific helix aggregation) | Pereira 2021 |
| PECTIN | Ca²⁺ (low-methoxy, DE < 50%) | Voragen 2009 |
| GELLAN | K⁺ or Ca²⁺ (low-acyl) | Morris 2012 |
| HYALURONATE | Ca²⁺ (cofactor only; covalent BDDE is canonical) | Hahn 2006 |

**Strengths.** Room-temperature processing, mild on biology, food-grade options.
**Trade-offs.** Ionic crosslinks dissolve in saline / pH extremes; lower modulus (~10–50 kPa) than covalent systems. Trivalent gelants (Al³⁺) are stronger but biotherapeutic-unsafe (FDA/EP residue regulation).

### Pathway 3 — Non-Solvent-Induced Phase Separation (NIPS)

**Mechanism.** Cellulose is dissolved in a solvent (NaOH/urea, NMMO, ionic liquid, DMAc/LiCl) and emulsified. Droplets contact a non-solvent (water), which diffuses in and triggers phase separation via a Cahn-Hilliard free-energy functional. Quench depth controls morphology — shallow gives cellular gels, deep gives bicontinuous porous networks.

**Polymer families:** CELLULOSE (NIPS) — sub-routes: `naoh_urea` (default), `nmmo`, `emim_ac`, `dmac_licl`.

**Strengths.** Bicontinuous porosity (open structure), excellent protein compatibility, no covalent crosslinker needed.
**Trade-offs.** Solvent recovery dominates cost; the Cahn-Hilliard L2 solver is the simulator's most numerically demanding model.

### Pathway 4 — Solvent-evaporation glassy microspheres

**Mechanism.** PLGA dissolved in DCM is emulsified into an aqueous PVA phase. DCM diffuses out, evaporates, and PLGA concentration rises until it vitrifies into a glassy microsphere. No crosslinking — mechanical stability comes from the entangled glassy state below T_g.

**Polymer families:** PLGA — grade presets 50:50, 75:25, 85:15, 100:0 (PLA).

**Strengths.** Bioresorbable, FDA-familiar, tunable degradation.
**Trade-offs.** Organic-solvent handling; potential drug degradation during evaporation; glassy mechanics (1 GPa+).

### Pathway 5 — Material-as-ligand (B9 pattern)

**Mechanism.** The polymer matrix IS the affinity ligand. No coupling chemistry required; M3 elution uses a competitive-eluent workflow.

| Family | Captures | Eluent |
|---|---|---|
| AMYLOSE | MBP-tagged fusion proteins | 10 mM maltose |
| CHITIN | CBD/intein-tagged fusions (NEB IMPACT) | 50 mM DTT triggers self-cleavage |

### Pathway 6 — Multi-variant composites (v9.5)

For pH-controlled drug delivery and food-texture systems:

| Family | Components | Notes |
|---|---|---|
| AGAROSE_ALGINATE | Thermal agarose + Ca²⁺ alginate IPN | ~30% G_DN reinforcement (Chen 2022) |
| ALGINATE_CHITOSAN | Alginate Ca²⁺ skeleton + chitosan PEC shell | pH window 5.5–6.5 (Liu 2017) |
| PECTIN_CHITOSAN | Pectin Ca²⁺ skeleton + chitosan PEC shell | DE-dependent (Birch 2014) |
| GELLAN_ALGINATE | Dual ionic-gel; alginate dominant | +20% gellan helix reinforcement (Pereira 2018) |
| PULLULAN_DEXTRAN | Neutral α-glucan composite | ECH or STMP crosslinking (Singh 2008) |

The full polymer-family selection chart, with chemistry-to-application mapping, is in [`docs/user_manual/polysaccharide_microsphere_simulator_first_edition.md`](docs/user_manual/polysaccharide_microsphere_simulator_first_edition.md) §5.5.

---

## Operating Principles

DPSim's seven-step lifecycle workflow is the authoritative user contract:

```
┌──────────────────────────────────────────────────────────────────┐
│                Lifecycle Simulation Flow                         │
└──────────────────────────────────────────────────────────────────┘
   ┌──────────────┐    ┌─────────────┐    ┌─────────────┐
   │  Step 1      │ →  │  Step 2     │ →  │  Step 3     │
   │  Target      │    │  M1 recipe  │    │  M2 recipe  │
   │  product     │    │             │    │             │
   │  profile     │    │             │    │             │
   └──────────────┘    └─────────────┘    └─────────────┘
                                                  │
                                                  ↓
   ┌──────────────┐    ┌─────────────┐    ┌─────────────┐
   │  Step 7      │ ←  │  Step 6     │ ←  │  Step 4     │
   │  Calibration │    │ Validation  │    │  M3 column  │
   │  + wet-lab   │    │ + Evidence  │    │  method     │
   └──────────────┘    └─────────────┘    └─────────────┘
                              ↑                   │
                              │                   ↓
                       ┌──────────────┐    ┌─────────────┐
                       │  Step 5      │ ←  │ProcessRecipe│
                       │  Run lifecyc.│    │             │
                       └──────────────┘    └─────────────┘
```

Each step writes into a single in-memory `ProcessRecipe` object — the same object drives the UI, CLI, validation layer, and lifecycle orchestrator. **What you see in the UI is exactly what runs.**

### Five-tier evidence vocabulary

Internalise these before reading any DPSim result:

| Tier | Meaning | When to trust |
|---|---|---|
| `validated_quantitative` | Calibrated against this specific system | Suitable for design within the validated domain |
| `calibrated_local` | Fitted to local wet-lab data; not yet broadly cross-validated | Suitable for screening and local interpolation |
| `semi_quantitative` | Literature-parameterised or mechanistically plausible | Trends are useful; magnitudes are approximate |
| `qualitative_trend` | Directional or ranking-only | Use for screening and hypothesis generation only |
| `unsupported` | Chemistry, unit, regime, or operation not represented | **Do not use for decisions** |

### Evidence-tier inheritance rule

```
M1 calibration tier   ──cap──→   M2 calibration tier
                                      │
                                      ↓ cap
                                M3 calibration tier
```

If M1 is `qualitative_trend`, the entire downstream pipeline is capped at `qualitative_trend`. The simulator does not allow M2 or M3 to claim more confidence than their inputs. This rule is enforced in `RunReport.compute_min_tier`.

### Numerical solver matrix

| Model | Default solver | Rationale |
|---|---|---|
| Population balance (M1 emulsification) | scipy LSODA | Non-stiff PBE moments |
| Cahn-Hilliard NIPS (cellulose) | Spectral semi-implicit | Stiff fourth-order PDE |
| Lumped Rate Model (M3, default) | scipy `solve_ivp(method="BDF")` | Non-gradient case |
| LRM with gradient elution | BDF | LSODA oscillates with time-varying binding equilibrium |
| Catalysis packed bed (PFR + Michaelis-Menten) | LSODA | ~700× faster than BDF on non-stiff problem |
| MC-LRM tail samples | BDF with 10× tightened tolerances | Tier-1 numerical safeguard per SA-Q1 / D-046 |

LSODA fallback for high-affinity Langmuir paths is **explicitly rejected** — the codebase has documented LSODA stalls there.

---

## Development Philosophy

DPSim is built on five principles. They permeate the codebase:

1. **First-principles decomposition.** Every model is reasoned from physics or chemistry first; convention follows analysis. Algorithm choices are justified by complexity, convergence, and numerical stability.

2. **Modularity and parallel-module pattern.** Adding a new polymer family does **not** modify existing solvers. Instead, a new file is created alongside, the new family delegates to the closest existing solver in a sandbox, then re-tags the result with family-specific manifest provenance. This guarantees bit-for-bit equivalence with calibrated kernels by construction (D-016 / D-017 / D-027 / D-037).

3. **Evidence as a first-class citizen.** Every value carries a tier. Every assumption is surfaced. Every model has a `ModelManifest` with `evidence_tier`, `valid_domain`, `assumptions`, `diagnostics`, and `calibration_ref` fields. The UI displays them; users cannot accidentally use an `unsupported` value.

4. **Computational economics.** Every design decision considers compute / memory / time cost against the value of the output. Over-engineering is a defect. Solver tolerances and integration bounds are tuned per model (CLAUDE.md pins the matrix).

5. **Reproducibility and auditability.** Every pipeline run produces deterministic or statistically-characterised outputs. All parameters, seeds, and environmental dependencies are documented. Any result can be reproduced from the `ProcessRecipe`.

### Quality gates (CI-enforced)

- **ruff = 0** — zero lint warnings.
- **mypy = 0** — zero type errors on new files.
- **AST gate** — `tests/test_v9_3_enum_comparison_enforcement.py` walks `src/dpsim/` and `tests/`, failing the build on any `is`/`is not` comparison against `PolymerFamily`, `ACSSiteType`, `ModelEvidenceTier`, or `ModelMode`. (Reason: Streamlit reloads `dpsim.datatypes` on every rerun, minting a new enum class — identity comparisons silently break after the first rerun.)
- **Smoke baseline preservation** — every release verifies that legacy v0.2.x output is byte-identical when the new feature is opted out (e.g. `monte_carlo_n_samples=0`).
- **Coverage gates** — every reagent in `REAGENT_PROFILES` must surface in at least one M2 dropdown bucket; every value in `ALLOWED_FUNCTIONAL_MODES` must live in exactly one bucket.

---

## Usage Considerations

### When to trust DPSim's number

| Decision | Required evidence tier |
|---|---|
| Hypothesis generation, parameter-space narrowing | `qualitative_trend` is enough |
| Design choice between two screening alternatives | `semi_quantitative` |
| Quantitative process design (e.g. column scale-up) | `calibrated_local` or `validated_quantitative` |
| Regulatory submission or release | DPSim is **never** sufficient on its own |

### What DPSim is not

- Not a regulatory tox / stability study substitute.
- Not a GMP batch-record generator (the exported wet-lab SOP is a development scaffold).
- Not a guarantee of clinical / diagnostic / manufacturing fitness.
- Not a predictor for novel polymers outside the family registry.
- Not a refusal engine — it warns you when you exceed validation regimes, but it still runs.

### The wet-lab loop

DPSim is a screening tool first. The wet-lab loop turns it into a quantitative tool for your specific system:

1. Run a screening simulation. Get `semi_quantitative` magnitudes.
2. DPSim's wet-lab caveats and validation report tell you which assays will most reduce uncertainty.
3. Upload measured data into the calibration store.
4. Re-run. The simulator now reports `calibrated_local` evidence within the validated domain.

### Hazard considerations

The reagent library covers 96 chemistries. Several are classified as carcinogenic, mutagenic, reproductively toxic, or strongly sensitising (e.g. CNBr, glutaraldehyde, DCM, cyanuric chloride, AlCl₃, borax). Every reagent profile carries a `hazard_class` field that the UI surfaces, and Appendix J carries SDS-lite blocks for every reagent. **Always consult your institution's safety office and the reagent's full SDS before bench work.**

---

## Documentation Map

### User-facing documentation (start here)

| File | Audience | Purpose |
|---|---|---|
| [`docs/user_manual/polysaccharide_microsphere_simulator_first_edition.md`](docs/user_manual/polysaccharide_microsphere_simulator_first_edition.md) | Operators, junior researchers | Comprehensive instruction manual: workflow, polymer families, M2 chemistry, M3 / MC, calibration, formulas, troubleshooting |
| [`docs/user_manual/appendix_J_functionalization_protocols.md`](docs/user_manual/appendix_J_functionalization_protocols.md) | Wet-lab researchers | 96-reagent functionalisation protocols with SDS-lite hazard blocks |
| [`docs/quickstart.md`](docs/quickstart.md) | First-time users | One-page getting-started |
| [`docs/configuration.md`](docs/configuration.md) | All users | TOML and `ProcessRecipe` parameter reference |
| [`docs/INDEX.md`](docs/INDEX.md) | All users | Documentation navigation |
| `docs/user_manual/*.pdf` | All users | Built PDF versions of the manual + Appendix J — also accessible from the dashboard's upper-right corner |

### Developer documentation

| File | Audience | Purpose |
|---|---|---|
| [`CLAUDE.md`](CLAUDE.md) | Contributors | Project-specific contributor guidelines, solver matrix, AST gate, quirks |
| [`DESIGN.md`](DESIGN.md) | UI contributors | Visual / UI design system (typography, palette, semantic colours) |
| [`CHANGELOG.md`](CHANGELOG.md) | All | Per-release feature log |
| [`docs/handover/`](docs/handover/) | Maintainers | Per-cycle handover documents (planning + close) |
| [`docs/decisions/`](docs/decisions/) | Maintainers | Architecture Decision Records (ADRs) |
| [`docs/DPS_CLEAN_SLATE_ARCHITECTURE.md`](docs/DPS_CLEAN_SLATE_ARCHITECTURE.md) | Architects | Clean-slate architecture reference |
| [`installer/README.md`](installer/README.md) | Release engineers | Windows installer + portable ZIP build pipeline |

---

## Version History

DPSim follows a **fork-line versioning** convention: `v0.x` is the DPSim fork's release line; `v9.x` is the upstream simulator's release line (last upstream release `v9.2.2` on 2026-04-24). Internal cycle labels (Tier-1/2/3 batches, G1–G5 module groups) are orthogonal to either version line.

| Version | Date | Headline | Key additions |
|---|---|---|---|
| **v0.1.0** | 2026-04-19 | Initial DPSim fork | Package rename `dpsim`, lifecycle CLI, clean-slate architecture primitives |
| **v0.2.0** | 2026-04-25 | Functional-Optimization (Tiers 1-3) | 50 SA-screened candidates processed; 14 polymer families promoted; 50 reagent profiles added; ACS site types extended to 25; closed-vocabulary discipline established |
| **v0.3.0** | 2026-04-25 | P5++ MC-LRM core | `PosteriorSamples` G1 + `run_mc()` G2 + `MethodSimulationResult.monte_carlo` G3 dispatch; Tier-1 numerical safeguards; reformulated convergence diagnostics |
| **v0.3.1** | 2026-04-25 | Optional Bayesian fit (G4) | `fit_langmuir_posterior()` via pymc/NUTS, behind `[bayesian]` extra; mandatory R-hat / ESS / divergence gates |
| **v0.3.2** | 2026-04-25 | UI bands + dossier MC (G5) | Plotly P05/P50/P95 envelope plot; ProcessDossier MC export with curve decimation |
| **v0.3.3** | 2026-04-25 | v9.5 multi-variant composites | PECTIN_CHITOSAN, GELLAN_ALGINATE, PULLULAN_DEXTRAN promoted; borax reversibility warning |
| **v0.3.4** | 2026-04-25 | M2 dropdown audit fix | M2 reagent coverage 50/94 → 94/94 (100%); 8 new chemistry buckets |
| **v0.3.5** | 2026-04-25 | Audit follow-ons | Ion-gelant picker (1/13 → 13/13); ACS visibility (≤9/25 → 23/25); crosslinker registry split documented |
| **v0.3.6** | 2026-04-25 | Closed all v0.3.x follow-ons | Click alkyne reference (24/25); low-N MC warning; joblib parallelism wired; solver-lambda helper; pectin DE / gellan K⁺ / pullulan STMP variants |
| **v0.3.7** | 2026-04-25 | First Edition manual refresh | ~1100-line manual rewrite; Appendix J § J.11 addendum (13 new SDS-lite protocol stubs) |
| **v0.3.8** | 2026-04-25 | Release tooling | Windows installer + portable ZIP build pipeline; `__DPSIM_VERSION__` placeholder discipline |

The full per-release change log is in [`CHANGELOG.md`](CHANGELOG.md).

---

## Intellectual Property and Licence

### Intellectual property

The intellectual property in this software, including the source code, documentation, simulator architecture, M2 chemistry state model, M3 chromatography solvers, calibration framework, MC-LRM uncertainty driver, and accompanying assets, **belongs to Holocyte Pty Ltd**.

See [`NOTICE`](NOTICE) for the full project ownership notice.

### Licence

DPSim is distributed under the **GNU General Public License, version 3.0 (GPL-3.0)**. The full licence text is in [`LICENSE`](LICENSE) and is also available at <https://www.gnu.org/licenses/gpl-3.0.en.html>.

The key user rights granted by GPL-3.0 are:

- the freedom to **run** the program for any purpose,
- the freedom to **study** how the program works and adapt it,
- the freedom to **redistribute** copies, and
- the freedom to **modify** and release improved versions.

Redistributions and derivative works must themselves be licensed under GPL-3.0 and must make their source code available.

### Source code availability

The canonical source-code repository is published on GitHub at:

> <https://github.com/tocvicmeng-prog/Downstream-Processing-Simulator>

Each tagged release is available under the **Releases** tab.

### Third-party licences

Bundled dependencies retain their upstream licences:

- numpy, scipy, pandas, matplotlib (BSD)
- streamlit, plotly (Apache 2.0 / MIT)
- pydantic, h5py (MIT / BSD)
- botorch, gpytorch, pytorch (BSD / MIT) — optional `[optimization]` extra
- pymc, arviz (Apache 2.0) — optional `[bayesian]` extra

See `pyproject.toml` for the pinned versions.

---

## Citation

If you use DPSim in published work, please cite:

```
Holocyte Pty Ltd. (2026). DPSim — Downstream Processing Simulator (v0.3.8).
GNU General Public License v3.0.
https://github.com/tocvicmeng-prog/Downstream-Processing-Simulator
```

For the underlying scientific methods, please also cite the primary literature referenced in Appendix J and in each `ReagentProfile.calibration_source` field.

---

## Contributing and Support

### Reporting issues

Open an issue at the GitHub repository:

> <https://github.com/tocvicmeng-prog/Downstream-Processing-Simulator/issues>

Include:
- DPSim version (`python -c "import dpsim; print(dpsim.__version__)"`)
- Python version (`python --version`)
- Operating system
- Reproducer recipe (TOML or Python snippet)
- Expected vs observed behaviour
- Full traceback if applicable

### Pull requests

Please read [`CLAUDE.md`](CLAUDE.md) and [`DESIGN.md`](DESIGN.md) before submitting a PR. Key gates:

- ruff = 0 and mypy = 0 on changed files
- Tests pass locally on Python 3.11 or 3.12
- AST enum-comparison gate clean
- Smoke baseline preserved (legacy paths byte-identical when the new feature is opted out)
- DESIGN.md compliance for any UI change

### Wet-lab calibration data

If you have wet-lab data that could improve DPSim's parameterisation, please open an issue describing the assay, conditions, and result. The calibration-ingestion path (`dpsim.calibration.wetlab_ingestion`) accepts YAML campaigns; example campaigns are in `data/wetlab_calibration_examples/`.

### Commercial support

Commercial users requiring SLA-backed support, custom calibration campaigns, or non-GPL licensing should contact Holocyte Pty Ltd directly via the channels listed on the GitHub repository.

---

## Disclaimer

DPSim and its documentation are provided **for informational, research, and screening purposes only**. They do not constitute professional engineering advice, medical advice, regulatory submission, or formal peer review.

Every result must be interpreted with explicit unit consistency checks; pH, temperature, reagent, and buffer compatibility checks; calibration-domain checks; M1 residual oil / surfactant carryover limits; M2 site and mass balance; M2 ligand density / leaching / free-protein wash / activity-retention assays; M3 pressure / compression / Reynolds-Peclet / breakthrough / recovery checks; explicit assumptions; and wet-lab caveats.

DPSim does **not** prove a resin is fit for clinical, diagnostic, or manufacturing use without independent calibration, release assays, and process validation. The exported wet-lab SOP is a **development scaffold** that must be reviewed under your local safety and quality systems before bench execution.

---

*DPSim is © Holocyte Pty Ltd, 2026. Released under GNU GPL-3.0. Source: <https://github.com/tocvicmeng-prog/Downstream-Processing-Simulator>.*
