# DPSim Scientific Architecture and Modification Plan

Status: planning document  
Date: 2026-04-24  
Project version inspected: v9.2.2 source tree  
Primary sources inspected:

- `docs/01_scientific_advisor_report.md`
- `docs/02_computational_architecture.md`
- `docs/module2_history.md`
- `docs/ui_evolution.md`
- `README.md`
- `src/dpsim/datatypes.py`
- `src/dpsim/pipeline/orchestrator.py`
- `src/dpsim/module2_functionalization/`
- `src/dpsim/module3_performance/`
- `src/dpsim/calibration/`
- `src/dpsim/trust.py`
- `src/dpsim/visualization/`
- `tests/`

## 1. Executive Summary

DPSim should be developed as a calibrated process-development digital
workbench for porous functional microsphere media, not as an unrestricted
first-principles simulator. The scientific target is a chain of physically
defensible, explicitly qualified predictions:

1. M1: formulation and equipment conditions -> bead size distribution,
   internal morphology, primary network state, bead mechanics.
2. M2: bead state and reactive-site inventory -> functional chemistry history,
   accessible ligand density, residual reagent burden, media contract.
3. M3: functional media and column/process recipe -> pressure drop,
   breakthrough, gradient elution, dynamic binding capacity, yield, purity,
   activity, and lifetime.

The current repository already contains many correct architectural instincts:
family-first M1 dispatch, explicit `M1ExportContract` and
`FunctionalMediaContract`, `ModelManifest`, `RunReport`, evidence tiers, trust
warnings, calibration storage, M2 ACS accounting, M3 LRM chromatography, and a
large regression test suite. These are valuable and should be preserved.

The main weaknesses are structural:

- The platform still treats the full process partly as a sequence of old
  L1-L4 objects plus separate M2/M3 modules, instead of one process graph with
  typed state handoffs.
- Units, parameter provenance, calibration validity domains, and posterior
  uncertainty are not yet central enough.
- M1 often collapses bead size distribution to one representative diameter
  before downstream physics.
- M2 chemistry is useful for screening but still lacks a full reaction-transport
  and wet-lab residue model.
- M3 can run useful LRM studies, but default isotherm parameters remain
  illustrative and M3 is not yet a first-class terminal stage of a unified
  `FullProcessResult`.
- The UI exposes many scientific possibilities faster than the calibration data
  can justify them.

The recommended path is an incremental refactor, not a rewrite. Keep the
working solvers, contracts, tests, and UI, but add a small scientific core that
all modules consume: units/provenance, model registry, process recipe, result
graph, calibration datasets, validation gates, and wet-lab QC links.

## 2. Clean-Slate Target Architecture

If the project were developed from zero, the architecture should start from the
experimental process, not from software modules.

### 2.1 Product Definition

The simulator should answer these user questions:

- Can this formulation and equipment produce stable microspheres in the target
  size range?
- What bead size distribution and internal pore morphology should I expect?
- Which functional chemistry sequence is chemically compatible with the bead?
- How many active ligand sites should remain accessible to a real target
  molecule after washing/quenching?
- What column performance is plausible under a given flow, feed, buffer, and
  gradient program?
- Which experiments are needed to promote a result from screening to
  quantitative use?

The system should not claim universal quantitative prediction until local
calibration exists. Every output must carry:

- value
- unit
- uncertainty
- model name
- valid domain
- evidence tier
- calibration provenance
- assumptions and warnings

### 2.2 Top-Level Process Graph

The fundamental object should be a process graph:

```text
TargetProductProfile
        |
        v
ProcessRecipe
  - material batch
  - equipment profile
  - fabrication steps
  - functionalization steps
  - chromatography steps
        |
        v
M1 Fabrication State
  - bead size distribution
  - morphology distribution
  - network state
  - mechanics
        |
        v
M2 Functional Media State
  - ACS inventory
  - reaction history
  - ligand density
  - residuals
  - media QC
        |
        v
M3 Process Performance State
  - breakthrough
  - elution
  - pressure
  - yield/purity
  - lifetime
        |
        v
Decision Report
  - trust
  - uncertainty
  - next experiments
```

This graph should replace the mental model of "M1 page, M2 page, M3 page" as
independent applications. The pages are UI views over a shared process graph.

### 2.3 Core Domain Objects

Clean-slate object model:

| Object | Role |
|---|---|
| `Quantity` | Numeric value with unit, bounds, source, and uncertainty. |
| `ResolvedParameter` | A model parameter after resolving default, literature, user override, or calibration source. |
| `MaterialBatch` | Polymer, solvent, oil, surfactant, reagent, ligand, target protein lots and measured properties. |
| `EquipmentProfile` | Vessel, stirrer, rotor-stator, column, tubing, detector, pump limits. |
| `ProcessStep` | Wet-lab operation with time, temperature, pH, additions, mixing, washing, sampling. |
| `ModelManifest` | Solver identity, equations, assumptions, valid domain, evidence tier. |
| `ProcessState` | State vector after each step, including balances and uncertainty. |
| `CalibrationDataset` | Raw assay records, fitted parameters, posterior uncertainty, validity domain. |
| `ValidationGate` | Hard blockers and warnings generated from dimensionless groups, chemistry rules, numerical quality, and wet-lab feasibility. |
| `ProcessDossier` | Reproducible run artifact suitable for lab notebook attachment. |

### 2.4 Scientific Operating Modes

The current three-mode concept in `docs/01_scientific_advisor_report.md` is
right and should remain:

| Mode | Intended use | Output claims |
|---|---|---|
| Empirical Engineering | Fast design-space screening and recipe ranking. | Relative trend and interpolation inside calibrated ranges. |
| Hybrid Coupled | Default process-development mode. | Semi-quantitative predictions with explicit limits. |
| Mechanistic Research | Hypothesis testing and model development. | Exploratory outputs, not production decisions. |

The UI and optimizer should enforce mode-specific claims. A user can run a
mechanistic branch, but the result is not automatically more trustworthy. A
mechanistic model outside its parameterized domain is lower evidence than a
local empirical model inside its calibration range.

## 3. Architectural Principles

### 3.1 Scientific Role Separation

Each layer must answer one scientific question:

- M1-L1: What droplet/bead population is produced?
- M1-L2: What internal morphology forms inside those droplets?
- M1-L3: What primary network/crosslink state exists?
- M1-L4: What bead-level mechanical and transport descriptors follow?
- M2: What functional surface/volume chemistry has been installed?
- M3: What process performance follows in a column or reactor?

Crosslinking appears in both M1 and M2, but the roles differ:

- M1 crosslinking: primary structure-forming or stabilizing network chemistry.
- M2 functional crosslinking: post-fabrication chemical modification, ligand
  installation, activation, quenching, residue removal, and activity retention.

These must not share one generic "crosslinking" abstraction.

### 3.2 Units and Provenance Are Architecture, Not Documentation

Every public module boundary must pass SI units or a typed unit object. Any
common laboratory unit such as mL/min, mM, percent w/v, percent v/v, mg/mL,
bed volumes, CV, bar, or um should be converted at the UI/config boundary and
stored with provenance.

Required policy:

- No unitless floats in cross-module contracts unless the dimension is truly
  dimensionless.
- Every calibrated parameter carries the conditions under which it was fitted.
- Every output carries the weakest evidence tier inherited from all upstream
  dependencies.

### 3.3 Conservation Laws as Regression Gates

Mass, site, charge, volume, and energy balances should be first-class test
targets:

- M1 PBE: dispersed-phase volume conservation.
- M1 gelation: polymer/solvent mass conservation and phase-field bounds.
- M1 crosslinking: limiting-reactant and reactive-site balance.
- M2 ACS: each accessible site ends in exactly one terminal state.
- M2 washing: residual reagent mass decays by a defined transport model.
- M3 chromatography: injected mass = eluted mass + bound mass + in-column mass.
- M3 catalysis: substrate/product balance with deactivation state tracked.

### 3.4 Distribution Propagation

For real microsphere media, the bead population matters. A single d50 or d32
is not enough for downstream performance.

The default pipeline should propagate at least:

- DSD quantiles or weighted representative bins from M1 to L2/L4.
- Pore distribution, not only mean pore size.
- Ligand-density distribution if reaction access depends on bead size or pore
  structure.
- M3 performance integrated over particle-size and pore-size distributions.

The existing `batch_variability` support is a good foundation, but it should
become the normal process-development path, not an optional side command.

### 3.5 Chemistry Families Must Be Explicit

Chemistries differ in target group, solvent, pH, reversibility, stoichiometry,
diffusion, side reactions, and wet-lab hazards. The architecture should use
chemistry-family plugins:

- amine-covalent
- hydroxyl-covalent
- carboxyl/EDC-NHS
- epoxy opening
- vinyl sulfone Michael addition
- maleimide-thiol
- ionic reversible
- affinity ligand installation
- IMAC chelation and metal charging
- independent polymerization
- washing/quenching/deactivation

Each plugin must define:

- compatible ACS types
- compatible polymer families
- reaction model
- hydrolysis/deactivation model
- pH and temperature domain
- solvent/buffer requirements
- wet-lab protocol block
- QC assay recommendations
- evidence tier and calibration handles

### 3.6 Wet-Lab Operations Are First-Class

The simulator should not only compute outputs. It should represent the
operation a researcher will execute:

- preheat and degas phases
- emulsify under defined equipment geometry
- cool/quench under a defined thermal profile
- wash and solvent exchange
- crosslink/activate/couple/quench
- pack column
- equilibrate/load/wash/elute/regenerate
- collect assays

The protocol generator should read the same `ProcessRecipe` used by the solver.
No separate "protocol text" should drift away from the simulation conditions.

### 3.7 Trust-Aware Optimization

Optimization should not optimize fantasy. It should only rank candidates whose
evidence and trust gates are adequate for the selected mode.

Policy:

- `qualitative_trend` and `unsupported` candidates can be displayed but should
  be excluded from production Pareto fronts by default.
- If a target depends on M3 performance, M3 must actually run and return a
  valid result. A missing M3 result should not be substituted with a fabricated
  proxy.
- Optimization should report the experiment that would most reduce uncertainty,
  not only the next recipe.

## 4. Scientifically Valid Design by Module

### 4.1 M1: Emulsification and Fabrication

M1 should be called "Fabrication", with "Emulsification" as its first physical
stage. The current UI heading already moves in this direction.

#### Required M1 Inputs

M1 needs structured inputs in these groups:

- Formulation: polymer identity, concentration, molecular weight, DDA or block
  composition, solvent, salts, surfactant, dispersed/continuous phase ratio.
- Rheology: temperature-dependent viscosity and shear-thinning model.
- Interface: equilibrium interfacial tension and surfactant adsorption kinetics.
- Equipment: vessel, impeller/rotor-stator geometry, fill volume, baffles,
  temperature control, power number correlation.
- Operation: addition order, preheat time, rpm profile, emulsification time,
  cooling rate, wash steps.
- Targets: bead size, span, pore size, porosity, modulus, pressure limit, and
  intended downstream use.

#### Required M1 Solvers

| Stage | Recommended model |
|---|---|
| Hydrodynamics | Power draw, Re, We, Ca, energy dissipation distribution, optional CFD surrogate. |
| Droplet population | 0D PBE with breakage/coalescence kernels for screening; CFD-PBE only when equipment geometry or scale-up requires it. |
| Thermal history | Lumped or radial heat-transfer model with explicit cooling profile. |
| Gelation/morphology | Platform-specific model: TIPS, ionic gelation, NIPS, solvent extraction, or empirical calibrated correlation. |
| Primary network | Chemistry-family kinetic model with limiting reactant and diffusion check. |
| Bead mechanics | Calibrated phenomenological model by default; mechanistic model only when inputs support it. |

#### M1 Validity Gates

M1 should block or downgrade outputs when:

- dispersed-phase volume fraction approaches inversion;
- viscosity ratio is outside the breakage kernel domain;
- predicted droplet size is below credible turbulent breakup scale;
- surfactant coverage is insufficient for the generated interface;
- thermal history would remelt or prevent gelation;
- phase-field domain is local but downstream uses it as full bead geometry;
- bead size distribution is too broad for chromatography packing;
- model mode and selected L2 model are inconsistent.

#### M1 Wet-Lab Alignment

M1 outputs should map to measurable QC:

- microscopy or laser diffraction DSD;
- emulsion stability and coalescence time;
- SEM/cryo-SEM pore morphology;
- swelling ratio;
- gravimetric solids/porosity;
- AFM or compression modulus;
- residual oil/surfactant after washing.

The simulator should identify which assay is needed to promote each output to
`calibrated_local` or `validated_quantitative`.

### 4.2 M2: Functional Crosslinking and Functionalization

M2 should model post-fabrication chemical operations on the media. The current
ACS state model is a strong basis and should be expanded into a reaction graph.

#### Required M2 Inputs

- M1 media contract: bead size distribution, porosity, pore distribution,
  mesh size, residual reactive groups, mechanical state, trust.
- Functional target: IEX, HIC, IMAC, affinity, enzyme immobilization, spacer
  arm, or stabilizing crosslink.
- Reagent identity: exact compound, concentration, solvent/buffer, pH, T, time.
- Sequence: activation, spacer, ligand coupling, protein coupling, metal
  charging, quenching, washing, storage.
- Target molecule: size, pI, hydrodynamic radius, binding stoichiometry,
  activity sensitivity, required elution condition.

#### Required M2 State Variables

M2 should track:

- total, accessible, activated, coupled, hydrolyzed, quenched, blocked, and
  residual sites;
- site type and chemical environment;
- area basis: external, reagent-accessible, ligand-accessible, or pore-volume
  accessible;
- residual reagent concentration after washing;
- ligand activity retention and uncertainty;
- surface density and bed-volume capacity prior;
- compatibility warnings by polymer family, pH, solvent, and temperature.

#### Required M2 Solvers

| Operation | Recommended model |
|---|---|
| Small-molecule crosslinking | Second-order or pseudo-first-order kinetics with Arrhenius and hydrolysis. |
| EDC/NHS | Two-step activation/coupling with O-acylisourea, NHS ester, hydrolysis, aminolysis. |
| Epoxy/vinyl sulfone | pH-dependent nucleophilic substitution or Michael addition. |
| Protein coupling | Steric and activity-retention model, ranked unless calibrated to target protein. |
| IMAC charging | Metal-loading fraction, chelator density, leaching/residual metal warning. |
| Washing | Diffusion-out or well-mixed wash model with residual threshold. |
| Quenching | Terminal state transition with reagent compatibility and residue burden. |

#### M2 Wet-Lab Alignment

M2 should output:

- exact reagent masses/volumes for a chosen settled bead volume;
- buffer pH, ionic strength, temperature, reaction time;
- wash volume and number of bed volumes;
- safety and compatibility warnings;
- QC assays: TNBS/ninhydrin amine assay, dye ligand assay, FTIR/XPS, elemental
  analysis, ICP-MS for metal, protein binding assay, residual reagent assay.

M2 should not mark ligand capacity as quantitative unless a binding assay or
breakthrough calibration exists for the target molecule.

### 4.3 M3: Affinity Chromatography and Performance

M3 should be a process-performance simulator consuming the M2 media contract.
For affinity chromatography, the important object is not just `q_max`; it is a
complete process recipe:

- media state from M2;
- packed bed geometry and compression state;
- feed composition;
- buffer pH/salt/imidazole/competitor profile;
- load, wash, elute, strip, regenerate, and storage steps;
- detector response and fraction collection rule.

#### Required M3 Solvers

| Function | Recommended model |
|---|---|
| Pressure drop | Kozeny-Carman/Ergun with bead size distribution and compressibility warning. |
| Breakthrough | LRM default; GRM when intraparticle diffusion is important. |
| Binding isotherm | Select by ligand class: Langmuir, competitive Langmuir, SMA, HIC, IMAC competition, Protein A pH model, custom calibrated affinity. |
| Gradient elution | Time-varying process-state adapter, gradient-sensitive isotherm required for mechanistic claims. |
| Detector | UV/conductivity/fluorescence/MS response with optional noise and baseline. |
| Lifetime | Capacity/activity decay over cycles, CIP damage, leaching, fouling. |

#### M3 Validity Gates

M3 should block or downgrade outputs when:

- mass balance error exceeds threshold;
- pressure drop exceeds mechanical or equipment limit;
- Re or Pe is outside model domain;
- default illustrative isotherm parameters are used for quantitative claims;
- ligand type lacks an M3 binding model;
- q_max was inferred from ligand density for an affinity system without target
  calibration;
- gradient is applied to a non-gradient-sensitive isotherm;
- bead compression is likely at the selected pressure.

#### M3 Wet-Lab Alignment

M3 should map predictions to standard downstream processing readouts:

- DBC5/DBC10 at a stated residence time;
- breakthrough curve and mass balance;
- elution peak width, recovery, purity, resolution;
- pressure-flow curve;
- cleaning/regeneration loss per cycle;
- target molecule and impurity identities.

## 5. Comparison: Generated Architecture vs Current Platform

The generated planning reference in `docs/01_scientific_advisor_report.md`
defines a scientifically coherent chain: emulsification PBE -> gelation and
pore formation -> crosslinking -> mechanics -> validation and optimization.
`docs/02_computational_architecture.md` translates this into a modular Python
pipeline. The current codebase implements much of that plan and extends it to
M2 functionalization and M3 performance.

### 5.1 Current Strengths to Preserve

| Area | Current strength |
|---|---|
| Package structure | Source is organized into solvers, properties, pipeline, M2, M3, optimization, calibration, UI, and tests. |
| M1 family dispatch | `PolymerFamily` routes agarose/chitosan, alginate, cellulose, and PLGA through different formation mechanisms. |
| M1 physics | PBE, hydrodynamic energy dissipation, temperature-dependent properties, gelation, crosslinking, and mechanics exist. |
| M2 contracts | `M1ExportContract`, `FunctionalMicrosphere`, and `FunctionalMediaContract` are the right kind of boundaries. |
| M2 ACS model | Terminal-state ACS accounting is scientifically useful and testable. |
| M3 models | LRM breakthrough, gradient elution, isotherm adapters, catalysis, detection, and mass-balance gates exist. |
| Evidence system | `ModelEvidenceTier`, `ModelManifest`, `RunReport`, and trust penalties are strong foundations. |
| Calibration | `AssayRecord`, `CalibrationStore`, posterior propagation, and `ProcessDossier` exist. |
| UI integration | Streamlit M1/M2/M3 pages call backend paths rather than being display-only. |
| Tests | The suite covers M1 physics, M2 workflows, M3 mass balance, evidence tiers, uncertainty, calibration, and UI contracts. |

### 5.2 Gaps Against the Clean-Slate Target

| Gap | Current manifestation | Consequence |
|---|---|---|
| No unified full-process result | `FullResult` is M1 L1-L4; M2/M3 results live separately in UI/session flows. | Optimization, dossiers, and evidence roll-up are not naturally M1->M2->M3. |
| Units are comments plus validators | Dataclasses carry floats with unit comments; contracts have sanity checks but not typed units. | Unit mistakes can still pass inside module internals. |
| Parameter provenance is partial | `PropertyValue` exists but `MaterialProperties` mostly stores raw floats; calibration overrides attributes directly. | Hard to audit why a parameter had a value in a given run. |
| Distribution propagation is optional | M1 exports mostly d50/d32; batch variability exists but is not the default M2/M3 path. | Downstream media performance can understate polydispersity and size-dependent pore effects. |
| L2 default remains empirical for agarose/chitosan | The docs correctly label this, but UI users can still see a full-pipeline result. | Risk of overinterpreting pore predictions as mechanistically linked to emulsification. |
| M1 branch trust inconsistency | Alginate/cellulose/PLGA branch reports use `trust_level="medium"` rather than the standard trust vocabulary. | Evidence/trust semantics are inconsistent across polymer families. |
| Calibration validity domains are not enforced deeply | `CalibrationEntry.valid_domain` exists but `apply_to_model_params` mostly checks only attribute names. | A fit can be applied outside the wet-lab range that produced it. |
| M2 reagent transport/residual model is incomplete | ACS and kinetics exist; washing/residuals are present but not yet central to every workflow. | Wet-lab feasibility and downstream contamination risk are under-modeled. |
| M2 affinity q_max remains estimated | `FunctionalMediaContract` maps ligand density to q_max with warnings. | Good for ranking; not quantitative DBC without target-specific calibration. |
| M3 default parameters are illustrative | UI captions warn this, but numeric outputs are still generated. | Users can mistake diagnostic curves for calibrated process predictions. |
| M3 gradient evidence handoff is incomplete | `run_gradient_elution` currently does not accept an FMC argument in its manifest path. | Gradient runs may not inherit upstream M2 evidence tier. |
| UI validators and backend validators are partly duplicated | `ui_validators.py` contains rules that can diverge from backend logic. | Validation drift risk. |
| Property database is too shallow for wet-lab work | It computes T-dependent oil viscosity, dispersed viscosity, IFT, chi, but many values lack source uncertainty and assay provenance. | Quantitative confidence is limited. |
| CLI ingest is only partially expanded | The ingest command wires L1 DSD and P2 M1 washing residuals, but not yet L2/L3/L4/M2/M3 assays. | Calibration loop is not complete for pore, mechanics, capacity, and breakthrough claims. |

## 6. Architecture Modification Plan

The best modification plan is staged. Do not rewrite working solvers first.
Create the missing scientific core, then migrate modules onto it.

### Phase 0: Documentation and Scope Cleanup

Goal: make the platform's scientific claims unambiguous.

Actions:

1. Define official module names:
   - M1 Fabrication Simulator
   - M2 Functionalization Simulator
   - M3 Performance Simulator
2. Keep L1-L4 as internal M1 stages only.
3. Add a glossary for "crosslinking" vs "functionalization" vs "primary
   network" vs "post-fabrication surface chemistry".
4. Update UI and docs to state that default results are semi-quantitative
   unless local calibration is loaded.
5. Mark every output panel with value, unit, evidence tier, and calibration
   status.

Recommended files:

- `docs/03_architecture_modification_plan.md` (this document)
- `docs/INDEX.md`
- `README.md`
- `docs/configuration.md`
- `src/dpsim/visualization/ui_model_metadata.py`

### Phase 1: Add a Scientific Core Layer

Goal: create shared infrastructure for units, provenance, model selection, and
process graphs.

Proposed package:

```text
src/dpsim/core/
  __init__.py
  quantities.py
  parameters.py
  model_registry.py
  process_recipe.py
  result_graph.py
  validation.py
  evidence.py
  units.py
```

Key additions:

| Component | Description |
|---|---|
| `Quantity` | Value, unit, bounds, uncertainty, source. |
| `ResolvedParameter` | Value plus source enum: default, literature, user, calibration, fitted, inferred. |
| `ParameterProvider` | Resolves parameters from defaults, config, reagent profile, calibration, and user overrides in a deterministic order. |
| `ModelRegistry` | Maps a requested scientific task to an implemented solver and returns its valid domain. |
| `ProcessRecipe` | One object for all wet-lab steps across M1/M2/M3. |
| `ResultGraph` | Stores M1, M2, M3 state nodes and edges with model manifests. |
| `ValidationGate` | Backend authority for blockers/warnings; UI renders this instead of duplicating logic. |

Migration policy:

- Do not remove current dataclasses immediately.
- Wrap existing dataclasses with adapters.
- New contracts should use the core objects internally and expose legacy fields
  for compatibility until tests and UI migrate.

### Phase 2: Upgrade Calibration and Data Management

Goal: make experimental data the center of credibility.

Actions:

1. Replace blind attribute override with parameter mapping records:

   ```text
   calibration target:
     module: M1
     model: L1.PBE.FixedPivot.AlopaeusCT
     parameter: breakage_C1
     units: dimensionless
     valid_domain:
       rpm: [800, 9000]
       phi_d: [0.02, 0.30]
       T_oil_K: [333, 363]
       equipment: rotor_stator_small
   ```

2. Enforce validity domains at run time.
3. Store posterior distributions, not only standard deviations.
4. Extend ingest beyond L1:
   - M1 DSD and pore imaging
   - M1 swelling/modulus
   - M2 ligand/site density and residual reagent
   - M3 batch isotherm and breakthrough
5. Add dataset manifests under:

   ```text
   data/validation/
     m1_dsd/
     m1_pore/
     m1_mechanics/
     m2_site_density/
     m2_residuals/
     m3_isotherms/
     m3_breakthrough/
   ```

6. Add calibration report output to `ProcessDossier`.

Near-term repair:

- Update `CalibrationStore.apply_to_model_params` to check units and
  `valid_domain` before applying an entry.
- If outside domain, do not apply the entry; add a trust warning.

### Phase 3: Repair and Strengthen M1

Goal: make fabrication predictions physically linked and distribution-aware.

#### 3.1 Make M1 Branches Share a Standard Result Tail

Current alginate/cellulose/PLGA branches duplicate summary and run-report code.
They also use `trust_level="medium"`, which is outside the standard trust
vocabulary.

Actions:

1. Create a private `_finalize_m1_result(...)` method in
   `PipelineOrchestrator`.
2. Use it for agarose/chitosan, alginate, cellulose, and PLGA.
3. Always call a family-aware trust assessor.
4. Replace `"medium"` with `TRUSTWORTHY`, `CAUTION`, or `UNRELIABLE`.
5. Include `polymer_family`, skipped stages, and "not applicable" reason in
   `RunReport.diagnostics`.

#### 3.2 Make DSD Propagation Default

Current `R_droplet = d50 / 2` is useful but incomplete.

Actions:

1. Introduce `BeadPopulationResult` with quantile bins:

   ```text
   bead_bins:
     d_lower
     d_mid
     d_upper
     number_fraction
     volume_fraction
     mass_fraction
   ```

2. Run L2/L4 over representative quantiles when the user selects chromatography
   or mechanical targets.
3. Export weighted pore and mechanics distributions to M2.
4. Keep single-bead mode for fast screening, but label it clearly.

#### 3.3 Split L2a and L2b in Code

The scientific advisor report recommends this split. Current code has
`GelationTimingResult`, but the architecture still treats L2 as one result.

Actions:

1. Add explicit result objects:
   - `ThermalGelationResult`
   - `MorphologyResult`
2. Make empirical L2 consume timing and droplet size explicitly.
3. For mechanistic L2, separate local patch domain from bead radius.
4. Make "empirical_uncalibrated" a first-class model manifest assumption, not
   only `model_tier` text.

#### 3.4 Clarify Agarose/Chitosan Mechanistic Scope

The clean scientific target for agarose/chitosan is ternary or multi-network
microstructure, but the current default is empirical.

Actions:

1. Keep empirical L2 as the default for speed.
2. Add a clear "mechanistic pore hypothesis" branch for agarose/chitosan:
   - two polymer components plus solvent;
   - temperature-dependent interaction parameters;
   - gelation arrest;
   - local patch outputs only unless a full bead solve is selected.
3. Until calibrated, mark this branch `MECHANISTIC_RESEARCH` and not
   production.

#### 3.5 Strengthen L1 Hydrodynamic Feasibility

Actions:

1. Add a hydrodynamic diagnostic block:
   - Re
   - We
   - Ca
   - viscosity ratio
   - Kolmogorov length
   - Hinze dmax
   - surfactant area coverage
2. Store this in `ModelManifest.diagnostics`.
3. Use these values in trust gates and UI.
4. Add an option for geometry-specific epsilon maps or CFD surrogate input.

#### 3.6 Improve M1 Wet-Lab Protocol Coupling

Actions:

1. Generate a fabrication protocol directly from M1 input:
   - preheat phase temperatures;
   - addition order;
   - rpm/time profile;
   - cooling profile;
   - wash steps;
   - primary crosslinking conditions;
   - QC sampling plan.
2. Link each recommended QC assay to the calibration parameter it informs.

### Phase 4: Repair and Strengthen M2

Goal: turn M2 from a useful chemistry screening layer into a wet-lab aligned
functional media builder.

#### 4.1 Promote Workflow to Reaction Graph

Current sequential steps are appropriate, but a reaction graph would make side
reactions and products clearer.

Actions:

1. Create `FunctionalizationRecipe` with ordered `ProcessStep`s.
2. Create `ReactionNode` definitions for each chemistry plugin.
3. Track:
   - target ACS
   - product ACS
   - terminal states
   - hydrolysis
   - quench
   - wash-out
   - residual reagent
4. Keep current `ModificationStep` as a compatibility adapter.

#### 4.2 Add Reagent Transport and Washing Models

Actions:

1. Add `module2_functionalization/transport.py`.
2. Model small-molecule diffusion into pores and wash-out from beads.
3. Model macromolecule exclusion using hydrodynamic radius and pore
   distribution.
4. Add residue thresholds and warnings for toxic or reactive reagents:
   glutaraldehyde, ECH, DVS, carbodiimide, NHS ester, metal ions.

#### 4.3 Make pH and Protonation Central

Actions:

1. Add pH-dependent availability for:
   - chitosan amines;
   - carboxyl groups;
   - hydroxyl activation;
   - maleimide-thiol;
   - protein activity.
2. Make pH validity a backend blocker or warning, not only a UI caption.
3. Attach pH to every M2 process step and calibration record.

#### 4.4 Convert Ligand Density to M3 Priors More Carefully

Current `FunctionalMediaContract` maps ligand density to `q_max`. That is
reasonable for IEX screening but weak for affinity systems.

Actions:

1. Split q_max estimate into:
   - geometric capacity prior;
   - active ligand prior;
   - target-specific calibrated capacity;
   - M3 fitted isotherm parameter.
2. For affinity, default to `qualitative_trend` unless target-specific binding
   data exists.
3. Store target molecule identity in the M2->M3 contract.
4. Add `binding_model_hint` and required process-state fields as typed enums.

#### 4.5 Expand M2 Calibration Assays

Add ingest support for:

- amine density assay;
- hydroxyl activation assay;
- ligand density assay;
- protein activity retention assay;
- residual reagent assay;
- metal loading/leaching assay;
- batch binding isotherm.

### Phase 5: Repair and Strengthen M3

Goal: make affinity chromatography predictions defensible downstream process
outputs, not isolated curves.

#### 5.1 Make M3 a First-Class Terminal Process Stage

Actions:

1. Add `PerformanceRecipe`:
   - column geometry;
   - packing state;
   - flow method;
   - feed composition;
   - buffer and gradient program;
   - fraction collection;
   - regeneration/CIP.
2. Add `PerformanceResult`:
   - pressure;
   - DBC;
   - breakthrough;
   - elution peaks;
   - yield/purity;
   - mass balance;
   - evidence.
3. Add M3 node to `ResultGraph` and `ProcessDossier`.
4. Keep existing `run_breakthrough` and `run_gradient_elution` as solver
   functions under the new recipe/result interface.

#### 5.2 Repair Evidence Inheritance for Gradient Runs

Current breakthrough can inherit FMC evidence, while gradient elution does not
pass an FMC in its manifest builder path.

Actions:

1. Add optional `fmc: FunctionalMediaContract | None` to
   `run_gradient_elution`.
2. Pass it to `_build_m3_chrom_manifest`.
3. Add tests mirroring breakthrough evidence inheritance.

#### 5.3 Require Calibrated Isotherms for Quantitative Affinity Claims

Actions:

1. Define an `IsothermParameterSet` with:
   - target molecule;
   - ligand;
   - pH;
   - salt/competitor;
   - temperature;
   - units;
   - source;
   - evidence tier.
2. If using default Langmuir values, mark output `qualitative_trend` or
   `semi_quantitative` depending on mode and show "diagnostic only".
3. Add M3 calibration ingest for static binding and breakthrough datasets.

#### 5.4 Add Bed Mechanics and Packing State

Actions:

1. Link M1/M2 bead mechanics to M3 pressure-flow predictions.
2. Add bead compressibility and maximum pressure gate.
3. Incorporate bead size distribution into Kozeny-Carman/Ergun calculations.
4. Warn when predicted pressure implies bead deformation or bed collapse.

#### 5.5 Add Process-Step Simulation

Instead of only breakthrough or gradient functions, M3 should simulate a
method:

```text
equilibrate -> load -> wash -> elute -> strip -> regenerate -> store
```

Each step has buffer composition, duration/CV, flow, and detector response.
This is how downstream processing scientists reason about chromatography.

### Phase 6: UI Refactor Around Process Recipes

Goal: keep the useful Streamlit UI but make it an interface to the backend
process graph.

Actions:

1. Page flow:
   - Define target and mode.
   - Build M1 fabrication recipe.
   - Run M1 and inspect QC/trust.
   - Build M2 functionalization recipe from M1 media.
   - Run M2 and inspect ligand/residue/QC.
   - Build M3 method from M2 media.
   - Run M3 and inspect process metrics.
   - Export dossier and wet-lab protocol.
2. UI should render backend `ValidationGate` results, not duplicate rules.
3. Every numeric result should display:
   - value;
   - unit;
   - evidence;
   - warning badge;
   - calibration link.
4. Hide or disable M3 quantitative claims until M2 supplies a compatible media
   contract and M3 has at least a calibrated or user-supplied isotherm.
5. Keep expert mode for research branches, but label claims clearly.

### Phase 7: Testing and Validation Matrix

Goal: make scientific validity testable.

Add tests in these categories:

| Category | Examples |
|---|---|
| Unit conversion | mM, mg/mL, percent w/v, mL/min, bar, CV. |
| Conservation | PBE volume, ACS terminal states, M3 mass balance. |
| Validity domains | Calibration not applied outside its domain; model gates fire. |
| Distribution propagation | M1 DSD quantiles alter downstream M2/M3 outputs. |
| Evidence inheritance | M3 cannot be stronger than M2; M2 cannot be stronger than M1 where dependent. |
| Wet-lab protocols | Protocol reagent amounts match recipe values. |
| Golden validation | Synthetic and real calibration datasets reproduce expected fitted parameters. |
| UI contracts | UI options match backend chemistry registry and model support. |

Validation datasets should be small but real. A minimal credible package would
include:

- 3-5 DSD measurements across rpm;
- 3 pore-size measurements across cooling rate/formulation;
- 3 crosslinking/swelling measurements;
- 2 ligand-density assays;
- 2 breakthrough curves for one target protein and one ligand chemistry.

## 7. Concrete Code-Level Modification Roadmap

### Immediate Repairs

These are low-risk and should be done first.

| Priority | Change | Files |
|---|---|---|
| P0 | Standardize non-agarose M1 branch trust reports. Replace `trust_level="medium"` with standard trust assessment. | `src/dpsim/pipeline/orchestrator.py`, tests |
| P0 | Add `fmc` argument to gradient elution and inherit evidence tier. | `src/dpsim/module3_performance/orchestrator.py`, tests |
| P0 | Stop mutating caller `SimulationParameters` inside `run_single` when syncing Span-80 from vol pct. Use a working copy. | `src/dpsim/pipeline/orchestrator.py` |
| P0 | Enforce `CalibrationEntry.valid_domain` before applying calibration entries. | `src/dpsim/calibration/calibration_store.py`, tests |
| P0 | Add backend validation service and have UI validators call it where possible. | `src/dpsim/core/validation.py`, `src/dpsim/visualization/ui_validators.py` |

### Short-Term Refactors

| Priority | Change | Files/modules |
|---|---|---|
| P1 | Split `datatypes.py` into domain files while keeping re-export compatibility. | `src/dpsim/datatypes/` or `src/dpsim/core/` |
| P1 | Add `BeadPopulationResult` and default DSD quantile propagation option. | `src/dpsim/datatypes.py`, `pipeline/batch_variability.py`, M2 contract |
| P1 | Add `FunctionalizationRecipe` wrapper over `ModificationStep`. | `src/dpsim/module2_functionalization/` |
| P1 | Add `PerformanceRecipe` and `PerformanceResult`. | `src/dpsim/module3_performance/` |
| P1 | Add M2/M3 result nodes to `ProcessDossier`. | `src/dpsim/process_dossier.py` |
| P1 | Add calibration ingest for M3 isotherm and breakthrough data. | `src/dpsim/calibration/fitters.py`, `src/dpsim/__main__.py` |

### Medium-Term Scientific Upgrades

| Priority | Change |
|---|---|
| P2 | Add surfactant coverage and adsorption kinetics diagnostics to M1. |
| P2 | Implement agarose/chitosan ternary morphology branch as research mode. |
| P2 | Add M2 pH/protonation and wash-out models. |
| P2 | Add target-specific affinity calibration workflow. |
| P2 | Add bed compression and bead-size-distribution pressure model in M3. |
| P2 | Add process-step chromatography method simulation. |

### Long-Term Research Upgrades

| Priority | Change |
|---|---|
| P3 | CFD-derived epsilon map import for equipment-specific PBE. |
| P3 | GRM chromatography with intraparticle diffusion and pore-size distribution. |
| P3 | Bayesian model averaging for structural uncertainty. |
| P3 | Digital twin feedback from wet-lab batches to update calibration posteriors. |
| P3 | Multi-cycle resin lifetime calibrated to CIP and storage studies. |

## 8. Recommended New/Changed Directory Structure

Target structure after migration:

```text
src/dpsim/
  core/
    quantities.py
    parameters.py
    evidence.py
    model_registry.py
    process_recipe.py
    result_graph.py
    validation.py
  m1_fabrication/
    contracts.py
    population.py
    emulsification/
    thermal/
    morphology/
    network/
    mechanics/
  module2_functionalization/
    contracts.py
    recipe.py
    acs.py
    reactions.py
    transport.py
    residuals.py
    qc.py
    orchestrator.py
  module3_performance/
    contracts.py
    recipe.py
    column.py
    packing.py
    isotherms/
    transport/
    methods.py
    orchestrator.py
  calibration/
    assay_record.py
    datasets.py
    fitters.py
    calibration_store.py
  pipeline/
    process_orchestrator.py
    legacy_m1_orchestrator.py
  visualization/
    ...
```

Do not rename existing modules abruptly. Add adapters and deprecation aliases.
The existing tests are a safety net and should continue passing during
migration.

## 9. Real-World Wet-Lab Alignment Checklist

Before any model output is allowed to present as more than screening, the
platform should answer:

- What material lot and property values were used?
- What exact wet-lab steps does this recipe imply?
- Are reagent amounts and volumes feasible at the selected bead volume?
- Is the pH/temperature compatible with the polymer, linker, ligand, and target
  protein?
- Are washing and quenching adequate for the reagent hazard and downstream use?
- Which QC assay validates each key output?
- What model domain was used and was the run inside it?
- What mass/site balance error was produced?
- What calibration data supported the quantitative claim?
- What decision is safe to make from this result?

If the answer is not available, the result should stay in a lower evidence tier.

## 10. Final Architectural Recommendation

The current DPSim platform should not be discarded. It already contains the
right scientific scaffolding: modular solvers, family dispatch, ACS accounting,
M2/M3 contracts, evidence tiers, trust gates, calibration hooks, and tests.

The best path is to strengthen it in this order:

1. Unify M1/M2/M3 under a process recipe and result graph.
2. Make units, provenance, calibration validity, and evidence tier impossible
   to bypass.
3. Promote DSD and morphology distributions to first-class downstream inputs.
4. Treat M2 as a wet-lab reaction and washing process, not only a ligand-density
   calculator.
5. Treat M3 as a complete chromatography method simulation, not only individual
   breakthrough/gradient functions.
6. Expand wet-lab calibration ingestion until each important numeric claim has
   a clear path from assay to parameter to output uncertainty.

This turns DPSim into a scientifically honest process-development simulator:
fast enough for design exploration, explicit about uncertainty, connected to
wet-lab operations, and progressively improvable as calibration data accumulates.
