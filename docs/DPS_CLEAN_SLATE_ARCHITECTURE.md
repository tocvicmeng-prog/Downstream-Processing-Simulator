# Downstream Processing Simulator Clean-Slate Architecture

Status: initial fork architecture  
Date: 2026-04-25

## Purpose

Downstream Processing Simulator models the complete lifecycle of porous
functional microsphere media:

1. double-emulsification or related microsphere preparation;
2. reinforcement and functional ligand crosslinking;
3. affinity-chromatography performance in a packed column.

The project must remain scientifically honest. It is a process-development
workbench, not an unconditional production predictor. Quantitative claims
require calibration data.

## Architectural Spine

```text
ProcessRecipe
  TargetProductProfile
  MaterialBatch
  EquipmentProfile
  ProcessStep[]
        |
        v
DownstreamProcessOrchestrator
        |
        +-- M1 Fabrication Solver Stack
        |      output: M1ExportContract
        |
        +-- M2 Functionalization Solver Stack
        |      output: FunctionalMediaContract
        |
        +-- M3 Performance Solver Stack
               output: BreakthroughResult / future MethodResult
        |
        v
ResultGraph + ValidationReport + ProcessDossier
```

## Module Responsibilities

### `dpsim.core`

The core package holds cross-cutting scientific architecture:

- `Quantity`: scalar value with unit, uncertainty, source, and bounds.
- `ResolvedParameter`: parameter value after source resolution.
- `ProcessRecipe`: wet-lab executable recipe shared by UI, CLI, protocol
  generation, and solver adapters.
- `ResultGraph`: explicit M1 -> M2 -> M3 handoff graph with evidence roll-up.
- `ValidationReport`: backend validation object rendered by all interfaces.
- `ModelRegistry`: declaration of model capabilities and validity domains.

### `dpsim.lifecycle`

The lifecycle package is the clean-slate orchestrator. It uses stable contracts
between stages and records scientific handoffs:

- M1 result -> `M1ExportContract`
- M2 functionalized media -> `FunctionalMediaContract`
- M3 breakthrough result -> process performance node
- M1 DSD quantiles -> downstream capacity/pressure screen

### Legacy Numerical Modules

The fork keeps the mature solver modules from DPSim:

- PBE droplet population models;
- gelation and morphology models;
- crosslinking kinetics;
- mechanical property estimators;
- ACS accounting and functionalization workflows;
- chromatography LRM, isotherms, and pressure-drop models.

These modules are useful numerical engines. The new architecture controls how
they are sequenced, validated, documented, and exposed.

## Evidence Policy

Every lifecycle output must inherit the weakest upstream evidence tier.

Typical starting tiers:

- M1 default fabrication: `semi_quantitative`
- M2 Protein A coupling without target calibration: `qualitative_trend`
- M3 affinity breakthrough from estimated Protein A qmax: no stronger than M2

Evidence may improve only through calibration:

- bead size distribution data for M1 L1;
- pore imaging data for M1 L2;
- swelling/mechanics data for M1 L3/L4;
- ligand-density and activity-retention assays for M2;
- static binding and breakthrough curves for M3.

## Wet-Lab Alignment Requirements

Every future feature should answer:

- What exact wet-lab operation does this model represent?
- Which material lot or reagent identity is assumed?
- Which pH, temperature, time, and concentration are used?
- What side reaction or degradation path is ignored?
- What QC assay validates the output?
- What calibration domain applies?
- What decision is safe from this result?

## Near-Term Technical Direction

1. Move UI validation to backend `ValidationReport`.
2. Add typed parameter resolution into M1/M2/M3 adapters.
3. Extend the initial M1 DSD quantile propagation into full per-quantile M3
   breakthrough/method simulation when decisions depend on batch heterogeneity.
4. Extend M2 washing from advisory residual tracking to calibrated wash-volume
   and assay-based release models.
5. Add M3 method simulation: equilibrate, load, wash, elute, regenerate.
6. Extend calibration ingest beyond L1 to M2 and M3.
