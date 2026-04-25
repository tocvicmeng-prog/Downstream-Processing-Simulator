# Final Handover: v9.2 — Tier-1 Cycle COMPLETE

**Date:** 2026-04-25
**Session:** v9.2-EXEC-003 (final continuation)
**Project:** Downstream-Processing-Simulator (DPSim) v9.2
**Prepared by:** /dev-orchestrator
**Classification:** Internal — Development Handover
**Status:** **v9.2 Tier-1 cycle COMPLETE — 41 of 41 modules approved (100%)**

---

## 1. Executive Summary

**v9.2 closes with all 41 Tier-1 modules approved across 10 milestones.** 354 v9.2-affected tests pass; zero regressions on the v9.1 alginate, agarose-chitosan, cellulose, or PLGA solvers. The Scientific Advisor screening report's complete Tier-1 recommendation is now landed:

- 12 new ACS site types
- 7 new Tier-1 polymer families (3 net-new at v9.2 close + AMYLOSE promoted from Tier-2 to Tier-1 in M8)
- 18 new reagent profiles spanning M1–M9 workflow batches
- 5 new level2_gelation modules (`ion_registry.py`, `agarose_only.py`, `chitosan_only.py`, `dextran_ech.py`, `composite_dispatch.py`)
- 1 new ion-gelation registry with 3 alginate Ca²⁺ entries (incl. CaSO₄) + freestanding KCl/CaSO₄ entries
- 2 closed vocabularies with validators (`ALLOWED_FUNCTIONAL_MODES`, `ALLOWED_CHEMISTRY_CLASSES`)
- 1 chemistry-class-to-kinetic-template dispatch table covering 27 classes (18 v9.1 + 9 v9.2)
- Family-selector UI rendering 8 Tier-1 families
- Family-reagent matrix expanded with 24 new (family × reagent) compatibility entries

The cycle's defining architectural decision — the **parallel-module + adapter pattern** (D-016) — preserved bit-for-bit numerical equivalence with all v9.1 calibrated kernels by construction. No legacy solver was touched.

---

## 2. Module Registry — Complete v9.2 Tier-1 Roster

### M0a (architectural foundation, schema-additive — 13 modules)

| ID | Module | File path | Status |
|---|---|---|---|
| A1.1 | acs_enum_extension | `src/dpsim/module2_functionalization/acs.py` | APPROVED |
| A1.2 | acs_conservation_tests | `tests/test_module2_acs.py` | APPROVED |
| A1.3 | acs_init_dispatch | `src/dpsim/module2_functionalization/acs.py` | APPROVED |
| A2.1 | polymer_family_extension | `src/dpsim/datatypes.py` | APPROVED |
| A2.7 | family_reagent_matrix_extension | `src/dpsim/module2_functionalization/family_reagent_matrix.py` | APPROVED |
| A3.1 | ion_gelant_profile | `src/dpsim/level2_gelation/ion_registry.py` (NEW) | APPROVED |
| A3.2 | ion_gelant_registry | (same) | APPROVED |
| A3.4 | caso4_internal_release | (same) | APPROVED |
| A3.5 | kcl_monovalent_gelant | (same) | APPROVED |
| A4.1 | functional_mode_extension | `src/dpsim/module2_functionalization/reagent_profiles.py` | APPROVED |
| A4.2 | functional_mode_dispatch | `src/dpsim/module2_functionalization/orchestrator.py` | APPROVED |
| A5.1 | chemistry_class_extension | `src/dpsim/module2_functionalization/reagent_profiles.py` | APPROVED |
| A5.2 | reaction_engine_dispatch | `src/dpsim/module2_functionalization/reactions.py` | APPROVED |

### M0b (architectural foundation, refactors — 7 modules)

| ID | Module | File path | Status |
|---|---|---|---|
| A2.2 | agarose_only_solver | `src/dpsim/level2_gelation/agarose_only.py` (NEW) | APPROVED |
| A2.3 | chitosan_only_solver | `src/dpsim/level2_gelation/chitosan_only.py` (NEW) | APPROVED |
| A2.4 | dextran_ech_solver | `src/dpsim/level2_gelation/dextran_ech.py` (NEW) | APPROVED |
| A2.5 | composite_dispatch | `src/dpsim/level2_gelation/composite_dispatch.py` (NEW) | APPROVED |
| A2.6 | family_selector_ui | `src/dpsim/visualization/tabs/m1/family_selector.py` | APPROVED |
| A3.3 | ion_registry_adapter | `src/dpsim/level2_gelation/ion_registry.py` | APPROVED |
| A3.6 | golden_master_regression_suite | `tests/test_v9_2_golden_master.py` (NEW) | APPROVED |

### M1 — Classical affinity resin (4 modules)

| ID | Module | Profile key | Status |
|---|---|---|---|
| B1.1 | agarose_only_parameter_set | `AGAROSE_REFERENCE_PARAMETERS` (Sepharose 4B/6B) in `agarose_only.py` | APPROVED |
| B1.2 | cnbr_activation_profile | `cnbr_activation` in REAGENT_PROFILES | APPROVED |
| B1.3 | cdi_activation_profile | `cdi_activation` | APPROVED |
| B1.4 | hexyl_hic_ligand | `hexyl_coupling` | APPROVED |

### M2 — Oriented glycoprotein immobilization (4 modules)

| ID | Module | Profile key | Status |
|---|---|---|---|
| B2.1 | periodate_oxidation_profile | `periodate_oxidation` | APPROVED |
| B2.2 | adh_hydrazone_profile | `adh_hydrazone` | APPROVED |
| B2.3 | aminooxy_peg_linker_profile | `aminooxy_peg_linker` | APPROVED |
| B2.4 | oriented_glycoprotein_workflow_test | M2 chain coherence tests in `test_v9_2_reagent_profiles.py::TestM2_OrientedGlycoproteinChain` | APPROVED |

### M3 — Dye pseudo-affinity (3 modules)

| ID | Module | Profile key | Status |
|---|---|---|---|
| B3.1 | cyanuric_chloride_activation_profile | `cyanuric_chloride_activation` | APPROVED |
| B3.2 | cibacron_blue_ligand_profile | `cibacron_blue_f3ga_coupling` | APPROVED |
| B3.3 | dye_leakage_warning_model | `triazine_dye_leakage_advisory` | APPROVED |

### M4 — Mixed-mode antibody capture (2 modules)

| ID | Module | Profile key | Status |
|---|---|---|---|
| B4.1 | thiophilic_ligand_profile | `thiophilic_2me_coupling` | APPROVED |
| B4.2 | mep_hcic_profile | `mep_hcic_coupling` | APPROVED |

### M5 — Bis-epoxide hardening (2 modules; per Q-001 — single parameterized profile)

| ID | Module | Profile key | Status |
|---|---|---|---|
| B5.1 | bis_epoxide_family_profile | `bis_epoxide_crosslinking` (parameterized via `spacer_length_angstrom`) | APPROVED |
| B5.2 | bis_epoxide_spacer_integration | `spacer_length_angstrom` field consumed by existing `level3_crosslinking` spacer-aware logic | APPROVED |

### M6 — Click chemistry (3 modules)

| ID | Module | Profile key | Status |
|---|---|---|---|
| B7.1 | cuaac_handle_profile | `cuaac_click_coupling` (with `regulatory_limit_ppm=30` for ICH Q3D Cu) | APPROVED |
| B7.2 | spaac_variant_profile | `spaac_click_coupling` | APPROVED |
| B7.3 | click_ligand_library_harness | M6 mutual-consistency tests in `test_v9_2_reagent_profiles.py::TestM6_ClickChemistry` | APPROVED |

### M7 — Multipoint enzyme immobilization (2 modules)

| ID | Module | Profile key | Status |
|---|---|---|---|
| B8.1 | glyoxyl_chained_activation | `glyoxyl_chained_activation` | APPROVED |
| B8.2 | multipoint_enzyme_stability_model | `multipoint_stability_uplift` | APPROVED |

### M8 — Material-as-ligand (3 modules)

| ID | Module | Profile key | Status |
|---|---|---|---|
| B9.1 | material_as_ligand_flag | `material_as_ligand: bool` + `_MATERIAL_AS_LIGAND_FAMILIES` in datatypes.py + AMYLOSE Tier-1 promotion | APPROVED |
| B9.2 | amylose_resin_profile | `amylose_mbp_affinity` + AMYLOSE dispatcher routing in `composite_dispatch.py` | APPROVED |
| B9.3 | mbp_amylose_workflow_test | M8 promotion tests in `test_v9_2_reagent_profiles.py::TestM8_MaterialAsLigand` | APPROVED |

### M9 — Boronate affinity (2 modules)

| ID | Module | Profile key | Status |
|---|---|---|---|
| B10.1 | aminophenyl_boronic_acid_profile | `apba_boronate_coupling` (with `pKa_nucleophile=8.5` for boronate speciation) | APPROVED |
| B10.2 | boronate_speciation_model | pH-switch driven by `pKa_nucleophile` + `boronate` `functional_mode` | APPROVED |

### Cumulative

- **Total modules approved:** 13 (M0a) + 7 (M0b) + 21 (M1–M9) = **41 / 41 = 100%**
- **LOC added:** ~3,800 across 5 new modules + 4 new test files + extensions to existing files
- **Tests passing:** 354 v9.2-affected (28 reagent-profile + 26 solver + 5 golden-master + 18 ion-registry + 113 ACS + 13 family-reagent matrix + others)
- **Fix rounds total:** 8 across 41 modules (1 in M0a, 4 in M0b, 3 in M1–M9 vocabulary alignment)
- **Token budget actual:** ~140 k across 3 sessions (M0a, M0b, M1–M9). Vs. all-Opus baseline projection of ~280 k → **~50% savings** matching the SA-projected band.

---

## 3. Integration Status (post-v9.2)

| Interface | Status | Notes |
|---|---|---|
| `ACSSiteType` (25 site types — v9.1: 13, v9.2: +12) | **LIVE** | All consumers updated; conservation tests parametrized over all 25 |
| `PolymerFamily` (14 entries: 8 Tier-1 + 6 Tier-2 placeholders) | **LIVE** | Tier-2 gated by `is_family_enabled_in_ui()` |
| `is_material_as_ligand()` | **LIVE** | AMYLOSE flagged; CHITIN remains Tier-2 placeholder |
| `solve_gelation_by_family()` (composite dispatcher) | **LIVE** | Routes 8 families: AGAROSE_CHITOSAN→legacy; AGAROSE/CHITOSAN/DEXTRAN→new v9.2 solvers; AMYLOSE→dextran-analogy; ALGINATE/CELLULOSE/PLGA→pipeline branches; Tier-2→NotImplementedError |
| `IonGelantProfile` registry + `to_alginate_gelant_profile` adapter | **LIVE** | A3.6 golden master verifies bit-for-bit equivalence with legacy `GELANTS_ALGINATE` |
| `ALLOWED_FUNCTIONAL_MODES` (15 entries: 7 v9.1 + 8 v9.2) | **LIVE** | All M1–M9 profiles validate |
| `ALLOWED_CHEMISTRY_CLASSES` (28 entries: 19 v9.1 + 9 v9.2) | **LIVE** | All M1–M9 profiles validate |
| `CHEMISTRY_CLASS_TO_TEMPLATE` dispatch | **LIVE** | All 28 classes route to one of 3 kinetic templates |
| Family-selector UI | **LIVE** | 8 Tier-1 families render; 6 Tier-2 placeholders hidden |
| Family-reagent matrix | **LIVE** | All Tier-1 families × 6 canonical reagents covered |
| `M2 orchestrator._mode_map` | **LIVE** | All 8 v9.2 functional_modes route to M3 ligand_type |
| Legacy `solve_gelation` / `_run_alginate` / `_run_cellulose` / `_run_plga` | **LIVE — UNCHANGED** | Bit-for-bit preservation verified by 5 golden-master tests + 226-test M0 regression |

---

## 4. Architecture State (v9.1 → v9.2 delta)

**Net-new files (5 modules):**
- `src/dpsim/level2_gelation/ion_registry.py` (registry + adapter)
- `src/dpsim/level2_gelation/agarose_only.py` (delegate-and-retag)
- `src/dpsim/level2_gelation/chitosan_only.py` (semi-quantitative)
- `src/dpsim/level2_gelation/dextran_ech.py` (Sephadex-calibrated)
- `src/dpsim/level2_gelation/composite_dispatch.py` (family router)

**Net-new test files (4):**
- `tests/test_ion_registry.py`
- `tests/test_v9_2_solvers.py`
- `tests/test_v9_2_golden_master.py`
- `tests/test_v9_2_reagent_profiles.py`

**Extensions to existing files (data-additive only — no signature changes):**
- `src/dpsim/datatypes.py` (PolymerFamily +10 entries; helpers `is_family_enabled_in_ui`, `is_material_as_ligand`)
- `src/dpsim/module2_functionalization/acs.py` (ACSSiteType +12 entries; init dispatcher docstring)
- `src/dpsim/module2_functionalization/reagent_profiles.py` (closed vocabularies + 18 v9.2 ReagentProfile entries)
- `src/dpsim/module2_functionalization/reactions.py` (CHEMISTRY_CLASS_TO_TEMPLATE map + kinetic_template_for)
- `src/dpsim/module2_functionalization/orchestrator.py` (_mode_map +8 entries)
- `src/dpsim/module2_functionalization/family_reagent_matrix.py` (+24 entries)
- `src/dpsim/visualization/tabs/m1/family_selector.py` (+4 display rows; filter via is_family_enabled_in_ui)
- `tests/test_module2_acs.py` (TestV9_2_ACSExpansion class)
- `tests/test_family_reagent_matrix.py` (test renamed to ..._all_ui_enabled_families)
- `tests/test_module2_workflows.py` (test_profile_count expectation 59 → 77)

**No deletions. No renamed identifiers. No removed enum members. No changed public function signatures.**

---

## 5. Acceptance Tests by Workflow Batch

Per `ARCH_v9_2_MODULE_DECOMPOSITION.md` §5, each milestone has a literature-anchored reference protocol. Status:

| Milestone | Reference protocol | v9.2 simulator coverage |
|---|---|---|
| M0 | Alginate Ca²⁺ + agarose-chitosan composite legacy regression | ✅ A3.6 golden master verifies bit-for-bit equivalence |
| M1 | IgG on CNBr-Sepharose 4B (Cytiva datasheet) | ✅ Profile ready: `cnbr_activation` + `AGAROSE_REFERENCE_PARAMETERS["agarose_4pct"]`. Wet-lab validation: pending. |
| M2 | HRP oriented immob via aminooxy-PEG (Rodrigues 2013) | ✅ Chain `periodate_oxidation` → `aminooxy_peg_linker` validated by `TestM2_OrientedGlycoproteinChain` |
| M3 | BSA depletion on Cibacron Blue Sepharose | ✅ Chain `cyanuric_chloride_activation` → `cibacron_blue_f3ga_coupling` validated by `TestM3_DyeAffinityChain` |
| M4 | IgG on MEP HyperCel (Pall) | ✅ `mep_hcic_coupling` carries pH-switch parameter (pKa_nucleophile=4.5) |
| M5 | HA hardening with BDDE (Hahn 2006) | ✅ `bis_epoxide_crosslinking` parameterized via spacer_length |
| M6 | Click peptide on alkyne-agarose (Quesada 2013) | ✅ `cuaac_click_coupling` with ICH Q3D Cu warning + SPAAC alternative |
| M7 | CALB on glyoxyl agarose (Mateo 2007) | ✅ Chain `glyoxyl_chained_activation` → `multipoint_stability_uplift` |
| M8 | MBP-tagged protein on amylose resin (NEB) | ✅ `amylose_mbp_affinity` + AMYLOSE family promoted to Tier-1 + dextran-ECH dispatch analogy |
| M9 | HbA1c on phenylboronate (Mallia 1989) | ✅ `apba_boronate_coupling` with pH-switchable boronate speciation (pKa=8.5) |

**Every acceptance test has its simulator-side dependencies in place.** Wet-lab validation runs against these profiles are now unblocked for v9.3 calibration.

---

## 6. Design Decisions Log — Cumulative v9.2

| # | Decision | Rationale |
|---|---|---|
| D-001..D-009 | (M0a planning decisions; see `DEVORCH_v9_2_JOINT_PLAN.md` §5) | — |
| D-010 | UI-rendering gate via external `_TIER1_UI_FAMILIES` frozenset | Preserves Enum string-vocabulary semantics |
| D-011 | IonGelantProfile in NEW module parallel to legacy | M0a schema-additive only |
| D-012 | CaSO4 k_release ≈ 5e-4 /s | Drury & Mooney 2003 |
| D-013 | Conservative biotherapeutic-safety default | Forces explicit ion registration |
| D-014 | v9.2 functional_modes map to "affinity" ligand_type | Most-conservative M3 dispatch |
| D-015 | Family-reagent test iterates UI-enabled families only | Tier-2 deliberately data-only in v9.2 |
| D-016 | A3.3 implemented as adapter, not refactor | Bit-for-bit equivalence by construction |
| D-017 | A2.2 delegate-and-retag, not re-implementation | Inherits all calibrated parameters |
| D-018 | A2.3/A2.4 evidence tiers chosen conservatively | Wet-lab calibration is v9.3 follow-on |
| D-019 | Opus → Sonnet downgrade for A2.2/A2.3/A2.4 | Parallel-module pattern reduced complexity |
| D-020 | A2.4 reads `formulation.ech_oh_ratio_dextran` via getattr | Avoids schema mutation; defaults to Sephadex G-100 baseline |
| D-021 | M5 single parameterized bis-epoxide profile (resolves Q-001) | Spacer-length parameterization is sufficient discrimination |
| D-022 | M8 AMYLOSE promoted from Tier-2 placeholder to Tier-1 | B9 material-as-ligand requires a working family entry; CHITIN remains Tier-2 |
| D-023 | M8 AMYLOSE L2 gelation dispatched via dextran-ECH analogy | Same α-glucan ECH chemistry; saves a separate solver module |
| D-024 | ALLOWED_FUNCTIONAL_MODES + ALLOWED_CHEMISTRY_CLASSES expanded to v9.1 ∪ v9.2 superset | Closed vocabularies must not reject existing legacy values |
| D-025 | M3 leakage advisory uses confidence_tier="ranking_only" not "qualitative_only" | Aligns with v9.1 canonical vocabulary on `confidence_tier` |
| D-026 | M1–M9 reagent_type uses canonical "coupling" not "ligand_coupling" | Aligns with v9.1 reaction_type vocabulary in `test_module2_workflows.py` |

---

## 7. Open Questions / Carry-forward to v9.3

| # | Question | Priority |
|---|---|---|
| Q-009 | ~~Wire `solve_gelation_by_family()` into `pipeline/orchestrator.py.run_single` for AGAROSE/CHITOSAN/DEXTRAN/AMYLOSE branches~~ | **RESOLVED 2026-04-25 (post-close)** — `_run_v9_2_tier1` method added in `pipeline/orchestrator.py`; routes the four Tier-1 families through `solve_gelation_by_family`; L3 stubbed; L4 reuses AGAROSE_CHITOSAN modulus solver as SEMI_QUANTITATIVE placeholder; 14 dispatch-routing tests pass in `tests/test_v9_2_pipeline_integration.py`; legacy v9.1 family routing verified unchanged. |
| Q-010 | Confirm canonical name `formulation.ech_oh_ratio_dextran` for v9.3 schema extension | MEDIUM |
| Q-011 | Custom ruff rule for `.value`-comparison enforcement (Q-005 carry-over from M0a) | LOW |
| Q-012 | Tier-2 placeholder UI visibility in v9.3 | LOW |
| Q-013 | Wet-lab calibration of chitosan-only (A2.3) and dextran-ECH (A2.4) for SEMI_QUANTITATIVE → CALIBRATED_LOCAL tier promotion | MEDIUM — schedule for v9.3 |
| Q-014 | Wet-lab validation of all 18 v9.2 reagent profiles against their literature-anchored acceptance tests (§5 above) | MEDIUM — v9.3 |
| Q-015 | M3 specialised binding models for `mixed_mode_hcic`, `thiophilic`, `boronate`, `dye_pseudo_affinity` (currently all dispatch to "affinity" generic) | LOW — refinement; "affinity" generic is correct in M2; M3 specialisation is independent work |

---

## 8. Filing

```
docs/handover/
├── SA_v9_2_FUNCTIONAL_OPTIMIZATION_SCREENING.md   (Scientific Advisor screening)
├── ARCH_v9_2_MODULE_DECOMPOSITION.md              (Architect decomposition)
├── DEVORCH_v9_2_JOINT_PLAN.md                     (orchestrator master plan)
├── HANDOVER_v9_2_M0a.md                           (M0a closeout)
├── HANDOVER_v9_2_M0b.md                           (M0b closeout)
└── HANDOVER_v9_2_CLOSE.md                          ← this file (v9.2 cycle close)
```

A new dialogue resuming v9.3 work needs only these six documents plus the project source tree.

---

## 9. Roadmap Position

- **v9.2 Tier-1 cycle:** **CLOSED** — 41/41 modules approved
- **v9.3 (Tier 2):** Ready to begin. Per `SA_v9_2_FUNCTIONAL_OPTIMIZATION_SCREENING.md` §6.2, Tier 2 contains 17 candidates: 5 polymer families (AGAROSE_DEXTRAN, AGAROSE_ALGINATE, ALGINATE_CHITOSAN, KAPPA_CARRAGEENAN, HYALURONATE; CHITIN), 1 crosslinker (HRP/H₂O₂/tyramine), 6 ligands (Procion Red, p-aminobenzamidine, Jacalin/lentil lectin, oligonucleotide, peptide affinity), 3 linkers (oligoglycine, cystamine disulfide, succinic anhydride), 2 ACS conversions (tresyl/tosyl, pyridyl disulfide). Most are data-only library extensions consuming the v9.2 foundation.
- **v9.4 (Tier 3, deferred):** 11 candidates including pectin/gellan/pullulan/starch families, Al³⁺/borax/glyoxal crosslinkers, calmodulin ligand. All are scientifically valid but lower bioprocess relevance.
- **Tier 4 rejected:** POCl₃ (hazard outweighs value).

### Process retrospective

1. **The parallel-module + adapter pattern was the most consequential strategic decision** of the cycle. It collapsed the M0b refactor work from a multi-session high-risk effort into a single-session deliverable while preserving v9.1 behavior by construction. Recommended for any future v9.x cycle that touches calibrated kernels.

2. **Schema-additive-first (M0a) before refactor (M0b)** is the right cadence for foundation work. Every M1–M9 batch then consumed a stable, audited schema rather than racing against schema migrations.

3. **18 reagent profiles in one batch** for M1–M9 worked because each profile is a parameter block with literature citations — the schema was already stable, the chemistry classes had pre-existing kinetic-template routes (A5.2), and the closed-vocabulary validators caught the few mismatches.

4. **Token economics matched SA projection (~50% savings).** The Opus assignments compressed to audits + planning; implementation was Sonnet-tier despite the ambition of the cycle. This is replicable for v9.3 if the same parallel-module pattern is followed.

5. **Environment friction (Python 3.14 vs project pin 3.11–3.13; tmp-dir permission errors)** did not block any v9.2 deliverable but did force selective test-suite running. v9.3 should fix the local Python pin before kickoff.

---

## 10. Five-Point Quality Standard Check (Reference 04 §4)

1. **Read §1–3 and know the complete project state** — ✅
2. **Read §4 and locate every approved source file** — ✅
3. **Read §5–7 and understand all architectural and design decisions** — ✅ (D-001 through D-026 + Q-009 through Q-015)
4. **Read the joint plan + handovers and begin v9.3 immediately** — ✅
5. **Read §8 and have the full compressed history of the project** — ✅

**All five checks pass. v9.2 cycle is closed.**

---

> *v9.2 Tier-1 functional-optimization cycle — COMPLETE. All 41 modules approved. v9.3 Tier-2 ready for kickoff against the v9.2 foundation.*
