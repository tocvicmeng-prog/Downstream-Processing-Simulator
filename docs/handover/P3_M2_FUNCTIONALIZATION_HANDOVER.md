# P3 M2 Functionalization Handover

## Scope

P3 strengthens the Module 2 functionalization layer without replacing the
existing chemistry kernels. The work makes wet-lab stages explicit, expands
site bookkeeping vocabulary, exposes reaction diagnostics as structured data,
and adds M2 wet-lab assay ingest contracts.

## Implemented Changes

### P3 Perfection Continuation

The continuation pass added active P3 scientific surfaces beyond the initial
contract work:

- built-in M2 stage templates for `epoxy_protein_a`, `edc_nhs_protein_a`,
  `hydrazide_protein_a`, `vinyl_sulfone_protein_a`, `nta_imac`, and `ida_imac`;
- explicit NTA/IDA product-site tracking after chelator coupling;
- hydrazide, NHS-ester, and vinyl-sulfone Protein A coupling reagent profiles;
- explicit NTA/IDA nickel-charging profiles;
- active FMC updates from M2 calibration entries, including recalculated qmax
  when measured activity or ligand density changes effective ligand density;
- validation gates for ligand leaching, free protein in wash fractions, low
  activity retention, and missing ligand density.

### Explicit M2 ProcessRecipe Stages

`ProcessStepKind` now includes:

- `insert_spacer`
- `block_or_quench`
- `storage_buffer_exchange`
- `metal_charge`

The resolver maps these to existing backend chemistry:

- `insert_spacer` -> `ModificationStepType.SPACER_ARM`
- `block_or_quench` -> `ModificationStepType.QUENCHING`
- `storage_buffer_exchange` -> `ModificationStepType.WASHING`
- `metal_charge` -> `ModificationStepType.METAL_CHARGING`

The default Protein A affinity-media recipe now includes a final storage buffer
exchange after quenching/final wash. This represents the wet-lab handoff into
storage or pre-column equilibration, and its QC checks include pH,
conductivity, ligand leaching, and basic contamination controls.

### ACS Site Vocabulary

`ACSSiteType` now covers the P3 requested site vocabulary:

- hydroxyl
- epoxide
- amine
- aldehyde
- NHS ester
- vinyl sulfone
- hydrazide
- NTA
- IDA

The site-balance implementation remains the existing terminal-state ACS model:
remaining, activation-consumed, hydrolyzed, coupled, blocked, and crosslinked
sites are conserved within each ACS profile.

### Chemistry Diagnostics

`ModificationResult` now carries `reaction_diagnostics`, which is copied into
the per-step `ModelManifest.diagnostics`. This avoids downstream parsing of
human-readable notes.

Protein/ligand coupling diagnostics now include:

- coupled sites
- hydrolyzed/side-reaction sites
- hydrolysis fraction
- reagent remaining fraction
- site-balance residual
- steric accessibility fraction
- activity-retention factor
- denaturation factor
- effective activity retention

The protein denaturation factor is a conservative screening model. It is 1.0
inside the reagent profile pH/temperature domain and decays with out-of-domain
exposure time. It is not a validated stability model; local activity assays are
required before making quantitative release claims.

### Wet-Lab Assay Contracts

`AssayKind` now includes:

- `ligand_density`
- `activity_retention`
- `ligand_leaching`
- `free_protein_wash_fraction`

`dpsim ingest M2` reads `data/validation/m2_capacity/assays/*.json` and writes
a CalibrationStore-compatible fit JSON. The fitter emits:

- `functional_ligand_density` in `mol/m2`
- `activity_retention` as a fraction
- `ligand_leaching_fraction` as a fraction
- `free_protein_wash_fraction` as a fraction

The scaffold now includes:

- `data/validation/m2_capacity/schema.json`
- `data/validation/m2_capacity/assays/.gitkeep`
- `data/validation/m2_capacity/fits/.gitkeep`

## Scientific Caveats

- M2 chemistry remains `semi_quantitative` or weaker unless calibrated against
  target-specific wet-lab assays.
- Protein A activity retention remains profile-derived until replaced by local
  binding/activity assays.
- The denaturation factor is a screening penalty for recipe comparison, not a
  kinetic unfolding model.
- Ligand leaching and free protein wash fractions are ingested as assay
  references. They are not yet fed back into a validated leaching or wash-closure
  mechanistic model.

## Recommended Next Work

1. Add ligand-family-specific long-term stability models for Protein A,
   Protein G, peptide ligands, dyes, IMAC chelators, and hydrazide chemistry.
2. Add validated leaching and free-protein wash closure models that can reduce
   effective M3 capacity only when the assay timing/buffer state matches the
   simulated column operation.
3. Add UI controls for selecting the built-in M2 templates and for entering M2
   assay acceptance limits per product program.
4. Add metal-leaching and regeneration/CIP models for NTA/IDA IMAC operation.
