# DPSim Unified Documentation Audit And Consolidation

**Audit date:** 2026-04-25  
**Scope:** Downstream Processing Simulator user manual, Appendix J
functionalization protocols, quickstart, configuration reference, and
documentation index.

## Authoritative Documentation Set

The DPSim user-facing documentation set is divided by role:

| Role | Authoritative file |
|---|---|
| Operator manual and lifecycle workflow | `polysaccharide_microsphere_simulator_first_edition.md` |
| Chemical functionalization wet-lab protocols | `appendix_J_functionalization_protocols.md` |
| Installation and first-run guide | `../quickstart.md` |
| TOML and `ProcessRecipe` parameter reference | `../configuration.md` |
| Documentation navigation | `../INDEX.md` |

The current simulator contract is lifecycle-first: target product profile,
M1 fabrication, M2 functionalization, M3 column method, lifecycle run,
validation/evidence review, and calibration comparison. Legacy M1/L1-L4
language remains only as an explanation of inherited numerical kernels.

## Corrections Applied

| Area | Finding | Correction |
|---|---|---|
| Product identity | The manual still described a polysaccharide-only emulsification simulator. | Reframed DPSim as a lifecycle downstream-processing simulator for M1/M2/M3 affinity media. |
| UI workflow | The manual described isolated Module 1/2/3 tabs. | Replaced quickstart with the seven-step lifecycle workflow now implemented in Streamlit. |
| Evidence terminology | Documentation mixed old uppercase shorthand and current enum values. | Defined canonical values: `validated_quantitative`, `calibrated_local`, `semi_quantitative`, `qualitative_trend`, `unsupported`. |
| Recipe source of truth | Some docs implied direct legacy controls were authoritative. | Stated that lifecycle work is driven by `ProcessRecipe` and `dpsim.core.recipe_io`. |
| M2 protocol mapping | Appendix J contained old dropdown names, "not wired" notes, and outdated version labels. | Replaced with implemented M2 templates and `reagent_key` names; external chemistries are explicitly marked non-quantitative. |
| Wet-lab release gates | The manual lacked a consolidated assay gate before using M1/M2/M3 outputs. | Added M1 DSD/residual/pore/mechanics, M2 ligand/site/leaching, and M3 pressure/breakthrough/recovery gates. |
| DCM safety | PLGA protocol understated DCM hazards. | Updated DCM handling to fume-hood, suspected carcinogen/CNS hazard, compatible gloves, halogenated waste, and no odor-based clearance. |
| Epichlorohydrin safety | Appendix J used odor as a wash endpoint. | Replaced with residual check or validated wash endpoint; odor is not a clearance test. |
| EDC/NHS operation | The manual implied PBS wash alone "quenches" after coupling. | Clarified ligand wash, then ethanolamine or Tris quench after intended coupling; azide limitations added. |
| Runtime paths | User-facing docs did not clearly list path overrides. | Added `DPSIM_TMPDIR`, `DPSIM_CACHE_DIR`, and `DPSIM_OUTPUT_DIR`. |
| Calibration linkage | Docs did not state that M3 evidence is capped by M2 media quality. | Added evidence-governance language to manual and Appendix J. |

## Canonical Terms

Use these terms consistently:

| Preferred term | Avoid |
|---|---|
| Downstream Processing Simulator or DPSim | EmulSim branding in user-facing docs |
| functionalization | alternate British spelling in new DPSim docs |
| M1 fabrication | Level 1 as a user workflow |
| M2 functionalization chemistry | Module 2 tab-only workflow |
| M3 column method/performance | mechanical-only chromatography wording |
| `ProcessRecipe` | temporary bridge, form-only state, or implicit UI state |
| reagent key | dropdown key, old module key |
| evidence tier | trust badge without provenance |
| development SOP scaffold | GMP batch record |

## Scientific And Operational Boundaries

DPSim documentation must not imply that simulation alone releases a process
for manufacture, clinical use, or regulated quality decisions. Every lifecycle
result must be interpreted with:

- unit consistency checks;
- pH, temperature, reagent, and buffer compatibility;
- calibration-domain checks;
- M1 residual oil/surfactant carryover limits;
- M2 site and mass balance;
- M2 ligand density, leaching, free-protein wash, and activity-retention assays;
- M3 pressure, compression, Reynolds/Peclet, breakthrough, and recovery checks;
- explicit assumptions and wet-lab caveats.

## Implemented M2 Templates

The documentation now treats these as implemented M2 recipe templates:

| Template | Required bench confirmation |
|---|---|
| `epoxy_protein_a` | Epoxide activation or hold-time control, Protein A density, retained IgG binding, free Protein A in washes |
| `edc_nhs_protein_a` | Carboxyl spacer density, NHS activation freshness, Protein A density/activity, free protein |
| `hydrazide_protein_a` | Hydrazide density, oxidized Protein A handling, activity/leaching |
| `vinyl_sulfone_protein_a` | Vinyl sulfone activation, nucleophile carryover control, thiol/amine coupling activity |
| `nta_imac` | NTA density, nickel loading, metal leaching |
| `ida_imac` | IDA density, nickel loading, higher metal-leaching risk than NTA |

Chemistries without an implemented `ReagentProfile` remain valid wet-lab
protocols when executed by trained researchers, but DPSim must treat their
simulation contribution as external evidence or `unsupported` until calibrated.

## Remaining Documentation Risks

The user-manual set is now aligned to current implementation, but the broader
historical `docs/` tree still contains archival planning files with version
history. Those files are useful for traceability and should not be read as
current operating instructions unless `docs/INDEX.md` marks them as
user-facing or canonical.

Future documentation updates should be gated by:

1. `rg` scan for old branding, old version-specific UI claims, and "not wired"
   language in user-facing docs.
2. Cross-check of every documented reagent key against
   `src/dpsim/module2_functionalization/reagent_profiles.py`.
3. Cross-check of every lifecycle workflow statement against
   `src/dpsim/visualization/app.py` and `src/dpsim/visualization/ui_workflow.py`.
4. PDF rebuild of every Markdown target in `docs/user_manual/build_pdf.py`.
