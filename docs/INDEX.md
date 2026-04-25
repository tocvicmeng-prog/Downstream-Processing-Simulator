# Downstream Processing Simulator Documentation Index

> Navigation map for `docs/`. Maintained post-audit (2026-04-25). Policy: every `.md` file in this
> directory is listed below. If you add a new doc, add an entry.

## User-facing

| File | Purpose |
|---|---|
| [`INDEX.md`](INDEX.md) | Documentation navigation map and consolidation policy |
| [`quickstart.md`](quickstart.md) | First simulation in five minutes, including lifecycle UI and runtime paths |
| [`configuration.md`](configuration.md) | Legacy TOML and lifecycle `ProcessRecipe` fields with units and physical meaning |
| [`04_calibration_protocol.md`](04_calibration_protocol.md) | 5-study wet-lab calibration plan |

## Scientific foundation

| File | Purpose |
|---|---|
| [`01_scientific_advisor_report.md`](01_scientific_advisor_report.md) | First-principles physics/chemistry decomposition (L1–L4). **Canonical scientific reference.** Includes appendices consolidated from older review/audit/brief docs in the 2026-04-24 content audit. |
| [`02_computational_architecture.md`](02_computational_architecture.md) | Software design, data flow, solver implementations |
| [`03_architecture_modification_plan.md`](03_architecture_modification_plan.md) | Clean-slate scientific target architecture plus current-platform comparison and staged modification plan for M1/M2/M3 |
| [`DPS_CLEAN_SLATE_ARCHITECTURE.md`](DPS_CLEAN_SLATE_ARCHITECTURE.md) | Fork-specific clean-slate architecture for the Downstream Processing Simulator lifecycle platform |
| [`01_scientific_advisor_report.md` §A.7](01_scientific_advisor_report.md) | Crosslinker library scientific provenance (preserved from the 2026-04-16 SA-DPSIM-XL-001 report as an appendix of the main scientific reference) |

## Architecture Decision Records

| File | Purpose |
|---|---|
| [`decisions/ADR-001-python-version-policy.md`](decisions/ADR-001-python-version-policy.md) | Why Python is pinned to `>=3.11,<3.13` |
| [`decisions/ADR-002-optimization-stack-pin.md`](decisions/ADR-002-optimization-stack-pin.md) | Why botorch / gpytorch / torch are version-pinned |

## Platform / family deep-dives

| File | Purpose |
|---|---|
| [`f1a_alginate_protocol.md`](f1a_alginate_protocol.md) | Alginate ionic-Ca gelation |
| [`f1b_cellulose_nips_protocol.md`](f1b_cellulose_nips_protocol.md) | Cellulose NIPS |
| [`f1c_plga_protocol.md`](f1c_plga_protocol.md) | PLGA solvent evaporation |
| [`f2_digital_twin_protocol.md`](f2_digital_twin_protocol.md) | Digital twin / EnKF replay |
| [`f4b_cvar_protocol.md`](f4b_cvar_protocol.md) | CVaR-robust Bayesian optimization |
| [`f5_md_ingest_protocol.md`](f5_md_ingest_protocol.md) | MARTINI MD parameter ingest |

## M2 chemistry design references

| File | Purpose |
|---|---|
| [`19_ligand_protein_coupling_candidates.md`](19_ligand_protein_coupling_candidates.md) | Candidate ligands/protein coupling routes and calibration caveats |
| [`20_linker_arm_candidates.md`](20_linker_arm_candidates.md) | Candidate linker/spacer arms and activity-retention caveats |

## User manual

| File | Purpose |
|---|---|
| [`user_manual/polysaccharide_microsphere_simulator_first_edition.md`](user_manual/polysaccharide_microsphere_simulator_first_edition.md) | First Edition v1.1 — lifecycle workflow, platform catalogue, validation/evidence, Appendices A–I |
| [`user_manual/appendix_J_functionalization_protocols.md`](user_manual/appendix_J_functionalization_protocols.md) | Wet-lab functionalization protocols with current `ProcessRecipe`/reagent-key mapping and SDS-lite safety blocks |
| [`user_manual/DPSIM_UNIFIED_DOCUMENTATION_AUDIT_2026-04-25.md`](user_manual/DPSIM_UNIFIED_DOCUMENTATION_AUDIT_2026-04-25.md) | Authoritative audit record and consolidation policy for the user-facing documentation set |

## Handover

| File | Purpose |
|---|---|
| [`handover/INITIAL_HANDOVER.md`](handover/INITIAL_HANDOVER.md) | Initial fork handover, implemented components, evidence limits, and next tasks |
| [`handover/P0_STABILIZATION_HANDOVER.md`](handover/P0_STABILIZATION_HANDOVER.md) | Python 3.12 stabilization, runtime path policy, CI gates, and full inherited-suite verification |
| [`handover/P1_SCIENTIFIC_BOUNDARIES_HANDOVER.md`](handover/P1_SCIENTIFIC_BOUNDARIES_HANDOVER.md) | Recipe-resolved lifecycle inputs, scientific validation gates, provenance, and caveats |
| [`handover/P1_UI_RECIPE_NATIVE_HANDOVER.md`](handover/P1_UI_RECIPE_NATIVE_HANDOVER.md) | UI controls migrated toward native `ProcessRecipe` state |
| [`handover/P2_M1_DSD_AND_WASHING_HANDOVER.md`](handover/P2_M1_DSD_AND_WASHING_HANDOVER.md) | Full M1 bead-size distribution handoff, DSD quantile transfer, wet-lab calibration hooks, and wash-residual representation |
| [`handover/P3_M2_FUNCTIONALIZATION_HANDOVER.md`](handover/P3_M2_FUNCTIONALIZATION_HANDOVER.md) | M2 functionalization stages, site balance, side reactions, and assay contracts |
| [`handover/P4_M3_CHROMATOGRAPHY_OPERATION_HANDOVER.md`](handover/P4_M3_CHROMATOGRAPHY_OPERATION_HANDOVER.md) | Full M3 chromatography method simulation |
| [`handover/P4_PLUS_M3_SCIENTIFIC_DEEPENING_HANDOVER.md`](handover/P4_PLUS_M3_SCIENTIFIC_DEEPENING_HANDOVER.md) | M3 Protein A and operability deepening |
| [`handover/P5_CALIBRATION_EVIDENCE_UPGRADE_HANDOVER.md`](handover/P5_CALIBRATION_EVIDENCE_UPGRADE_HANDOVER.md) | M2/M3 calibration ingest and evidence governance |
| [`handover/P5_PLUS_CALIBRATION_UNCERTAINTY_HANDOVER.md`](handover/P5_PLUS_CALIBRATION_UNCERTAINTY_HANDOVER.md) | Calibration uncertainty propagation and overlay support |
| [`handover/P6_UI_WORKFLOW_READINESS_REVIEW.md`](handover/P6_UI_WORKFLOW_READINESS_REVIEW.md) | UI readiness review before lifecycle workflow implementation |
| [`handover/P6_PLUS_UI_SCIENTIFIC_POLISH_HANDOVER.md`](handover/P6_PLUS_UI_SCIENTIFIC_POLISH_HANDOVER.md) | P6+ lifecycle UI scientific diagnostics, SOP export, calibration comparison, and run-history handover |

## Module / feature history

These files capture development history preserved for traceability. Current state lives in `src/` and CHANGELOG.

| File | Purpose |
|---|---|
| `module2_history.md` (created in PR-E) | Consolidated M2 expansion history (fold of 12 prior iteration docs) |
| `ui_evolution.md` (created in PR-E) | UI alignment / Family-First evolution |

## Policy

Version-specific planning documents for superseded releases (v5.x/v6.x/v7.x/v8.x) were removed in the 2026-04-24 content audit. The pre-audit snapshot lives at tag `v9.2.2-pre-docs-audit`. User-facing history is in `CHANGELOG.md`.
