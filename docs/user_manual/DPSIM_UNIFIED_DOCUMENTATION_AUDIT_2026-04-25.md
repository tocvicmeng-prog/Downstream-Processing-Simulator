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

---

## Addendum — Changes since 2026-04-25 (added 2026-05-01)

This addendum records material changes to the documentation set that occurred
*after* the 2026-04-25 audit was finalised. The audit body above is preserved
as a point-in-time snapshot; this section is append-only.

### Scope additions to the authoritative documentation set

| Role | New authoritative file | Status |
|---|---|---|
| M1 CFD-PBE zonal coupling — operator chapter | `polysaccharide_microsphere_simulator_first_edition.md` §9 | New chapter inserted between §8 (Calibration) and Part III (Appendix) |
| M1 CFD-PBE zonal coupling — advanced reference | `appendix_K_cfd_pbe_zonal_coupling.md` | New sibling appendix; registered in `build_pdf.py` BUILD_TARGETS |
| `zones.json` schema v1.0 contract | `cad/cfd/zones_schema.md` | Locked 2026-05-01; semantic versioning policy documented |

### Releases since the audit

| Version | Date | Highlights |
|---|---|---|
| v0.6.0 | 2026-05-01 | CAD geometry source-of-truth for the 5 wetted parts (Stirrer A pitched-blade with 19-tab disk geometry verified by photo + manual review; Stirrer B rotor + stator with 36 perforations × 3 rows; 100 mm beaker; jacketed 92 mm vessel). OpenFOAM CFD-PBE pipeline scaffolding (`cad/cfd/`, `src/dpsim/cfd/`). Live Stirrer A cross-section animation with physically faithful flow / droplet behaviour |
| post-v0.6.0 (commit a5d984c, 2026-05-01) | 2026-05-01 | DPSim-side CFD-PBE zonal coupling: schema v1.0, Pydantic-validated loader (11 hard-validation paths), `integrate_pbe_with_zones` integrator with bit-exact 1-zone reduction to legacy `PBESolver`, `consistency_check_with_volume_avg`, 31 library tests + 2 CLI smoke tests, `dpsim cfd-zones` subcommand |

### Canonical-term additions

In addition to the canonical terms listed above, the following terms are now
authoritative in user-facing documentation:

| Preferred term | Avoid |
|---|---|
| `epsilon_avg_W_per_kg` (volume-average ε, drives coalescence) | "average epsilon" without the per-kernel role |
| `epsilon_breakage_weighted_W_per_kg` (breakage-frequency-weighted ε, drives breakage) | "weighted epsilon", "biased epsilon" |
| Zone (well-mixed compartment in the CFD-PBE coupling) | "compartment" used loosely; reserve "compartment" for CFD-mesh subdivisions before zonal aggregation |
| Convective exchange (one-way well-mixed droplet transport between zones) | "mixing flow", "circulation" |
| Slot exit (rotor-stator-specific high-shear region just outside each stator hole) | "slot region", "stator zone" |
| `qualitative_trend` evidence for unvalidated CFD predictions | implying CFD predictions are quantitatively reliable before PIV validation |

### Scientific and operational boundaries (extension)

The 2026-04-25 audit listed eight interpretation gates for lifecycle results.
The CFD-PBE coupling adds three more, applicable when M1 is run via the
zonal path:

- PIV validation status of the underlying CFD field (no PIV → predictions inherit `qualitative_trend`).
- `volume_balance_relative_error` < 1e-3 (mass conservation across breakage / coalescence / exchange).
- Consistency check vs the legacy Po·N³·D⁵/V_tank empirical estimate (default 30 % relative tolerance per Scientific Advisor guidance, 2026-05-01).

### Documentation-update gating (extension)

In addition to the four gates listed above, future updates that touch the
CFD-PBE coupling should be gated by:

5. Re-run of `tests/test_cfd_zonal_pbe.py` (33 tests, ~32 s wall time).
6. Cross-check of `cad/cfd/zones_schema.md` against the Pydantic models
   in `src/dpsim/cfd/zonal_pbe.py` — the schema doc is the contract; the
   models are the implementation; drift between them is a documentation bug.
7. PDF rebuild of `appendix_K_cfd_pbe_zonal_coupling.md` alongside the
   first-edition manual.

### Remaining work (Phase C and beyond)

The audit's "remaining documentation risks" section noted that the broader
historical `docs/` tree contains archival planning files. As of 2026-05-01,
the CFD-PBE coupling has the following items not yet documented in
user-facing material because the upstream pipeline has not been executed
end-to-end:

- OpenFOAM dictionary templates for Stirrer A and Stirrer B cases (Phase 1–3).
- `extract_epsilon.py` implementation (Phase 4).
- `openfoam_io.py` helper functions.
- A worked end-to-end example with real (rather than synthetic-fixture) `zones.json`.
- PIV validation campaign results.

These will be folded in either via a new audit (`DPSIM_UNIFIED_DOCUMENTATION_AUDIT_<date>.md`) or as a follow-up addendum to this document, depending on whether the broader documentation set has shifted by then.
