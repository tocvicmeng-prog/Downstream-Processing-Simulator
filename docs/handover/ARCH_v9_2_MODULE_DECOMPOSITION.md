# Architect — v9.2 Module Decomposition (Tier-1)

**Document ID:** ARCH-v9.2-MOD-001
**Date:** 2026-04-25
**Author role:** Architect (within dev-orchestrator framework)
**Companion documents:**
- `SA_v9_2_FUNCTIONAL_OPTIMIZATION_SCREENING.md` — scientific candidate ranking (Tier 1–4)
- `DEVORCH_v9_2_JOINT_PLAN.md` — orchestrator's master plan (assembled separately)

**Scope:** Decompose the 5 architectural prerequisites (A1–A5) and 18 Tier-1 candidate integrations into 41 implementation modules across 10 milestones. Provide module identity, file path, responsibility, model tier, acceptance criteria, dependency edges, and per-batch reference protocol.

**Coding rules in force (from `CLAUDE.md`):** Python 3.11+ < 3.13; ruff-clean and mypy-clean (cap = 0); Streamlit reload-safe enum comparison via `.value`; Windows cp1252 stdout pitfall on `print(Path)` calls.

---

## 1. Decomposition principles applied

Per Reference 02 §2:

- **Follow the data.** New ACS site types appear in `module2_functionalization/acs.py` (where the ACSSiteType enum lives); they propagate through `reagent_profiles.py` and `reactions.py`. New `PolymerFamily` entries appear in `datatypes.py` and propagate into `level2_gelation/`, `level3_crosslinking/`, the UI family selector, and the family-reagent matrix.
- **Separate concerns.** Architectural prerequisites (A1–A5 — schema/registry/dispatch) are decomposed *separately* from candidate integrations (workflow batches B1–B10), even when a batch immediately consumes a prerequisite.
- **Minimise coupling.** New ion-gelation registry (A3) is a thin shim that delegates to existing alginate solver for the legacy entry; new `PolymerFamily` entries are gated by a per-family `is_enabled_in_ui` flag so they can land as data-only without UI surface impact until ready.
- **Identify parallelism early.** Within Milestone 0 (architectural foundation), modules A1.x and A4.x/A5.x are independent; A2.x and A3.x are independent. A1 is on the critical path because every later milestone consumes new ACS site types.

---

## 2. Module Registry — Architectural Prerequisites (Milestone 0)

The Module Registry conforms to Reference 04 §3 of the dev-orchestrator handover template (kept as a Markdown table for orchestrator integration).

| ID | Module | File path | Responsibility | LOC est. | Complexity | Model tier | Depends on |
|---|---|---|---|---|---|---|---|
| **A1.1** | `acs_enum_extension` | `src/dpsim/module2_functionalization/acs.py` | Add 12 new `ACSSiteType` enum members (SULFATE_ESTER, THIOL, PHENOL_TYRAMINE, AZIDE, ALKYNE, AMINOOXY, CIS_DIOL, TRIAZINE_REACTIVE, GLYOXYL, CYANATE_ESTER, IMIDAZOLYL_CARBONATE, SULFONATE_LEAVING) with docstrings citing ref 1° literature. | 30 | LOW | **Haiku** | — |
| **A1.2** | `acs_conservation_tests` | `tests/module2_functionalization/test_acs_conservation.py` | Extend conservation-law unit tests (`terminal_sum ≤ accessible_sites`) to cover all 25 site types. | 120 | LOW–MEDIUM | **Sonnet** | A1.1 |
| **A1.3** | `acs_init_dispatch` | `src/dpsim/module2_functionalization/acs.py::initialize_acs_from_m1` | Update default-initialization logic to populate new sites at zero density when a polymer family does not natively expose them; preserve backward compatibility. | 60 | MEDIUM | **Sonnet** | A1.1 |
| **A2.1** | `polymer_family_extension` | `src/dpsim/datatypes.py::PolymerFamily` | Add `AGAROSE`, `CHITOSAN`, `DEXTRAN` enum members (and 7 more disabled-by-default for Tier 2). Add `is_enabled_in_ui` flag mechanism. Preserve `.value` comparison semantics per CLAUDE.md. | 80 | LOW–MEDIUM | **Sonnet** | — |
| **A2.2** | `agarose_only_solver` | `src/dpsim/level2_gelation/agarose_only.py` (new) | Refactor agarose helix-coil thermal gelation kernel (T_gel ≈ 30–40 °C) out of the composite agarose-chitosan solver. Must reproduce existing AGAROSE_CHITOSAN behaviour when chitosan track is zero (regression invariant). | 220 | **HIGH** | **Opus** | A2.1 |
| **A2.3** | `chitosan_only_solver` | `src/dpsim/level2_gelation/chitosan_only.py` (new) | Chitosan-only gelation kernel with pH-dependent amine protonation (pKa ≈ 6.3–6.5) and acid-solubilized droplet viscosity. | 180 | MEDIUM–HIGH | **Sonnet** | A2.1 |
| **A2.4** | `dextran_ech_solver` | `src/dpsim/level2_gelation/dextran_ech.py` (new) | Dextran ECH alkaline crosslinking kinetics; first-order in dextran-OH and ECH; produces glyceryl ether bridges; tunable crosslink-density-to-pore-size mapping. | 200 | MEDIUM–HIGH | **Sonnet** | A2.1 |
| **A2.5** | `composite_agarose_chitosan` | `src/dpsim/level2_gelation/agarose_chitosan.py` (refactor) | Composite solver delegating to A2.2 + A2.3. Strict regression invariant: identical numeric outputs to the pre-refactor solver on the legacy parameter set (golden-master test). | 120 | MEDIUM | **Sonnet** | A2.2, A2.3 |
| **A2.6** | `family_selector_ui` | `src/dpsim/streamlit_app/tabs/m1/family_selector.py` (extend) | Render new families with the v9.0 Family-First UI contract; respect `is_enabled_in_ui`; never render crosslinker/cooling widgets for families that do not require them. | 90 | MEDIUM | **Sonnet** | A2.1 |
| **A2.7** | `family_reagent_matrix_extension` | `src/dpsim/module2_functionalization/family_reagent_matrix.py` (extend) | Add (family, reagent)-allowed columns for the 3 new Tier-1 families. | 60 | LOW | **Haiku** | A2.1 |
| **A3.1** | `ion_gelant_profile` | `src/dpsim/reagent_library_alginate.py` (extend) or new `reagent_library_ionic.py` | Define `IonGelantProfile` dataclass: `(polymer, ion, k_binding, junction_zone_energy, stoichiometry, slow_release_source)`. | 90 | MEDIUM | **Sonnet** | — |
| **A3.2** | `ion_gelant_registry` | `src/dpsim/level2_gelation/ion_registry.py` (new) | Per-(polymer, ion) registry with lookup, validation, and fallback. | 110 | MEDIUM | **Sonnet** | A3.1 |
| **A3.3** | `alginate_solver_via_registry` | `src/dpsim/level2_gelation/alginate.py` (refactor) | Refactor existing alginate Ca²⁺ solver to consume the registry. **Critical regression invariant: identical outputs to legacy on the existing alginate calibration suite**. | 180 | **HIGH** | **Opus** | A3.2 |
| **A3.4** | `caso4_internal_release` | `src/dpsim/reagent_library.py` (extend) | Add CaSO₄ slow-internal-release variant alongside existing CaCO₃/GDL. | 70 | MEDIUM | **Sonnet** | A3.2 |
| **A3.5** | `kcl_monovalent_gelant` | `src/dpsim/reagent_library.py` (extend) | KCl ionic gelant entry; pre-wires κ-carrageenan/gellan as Tier-2 consumers. | 50 | LOW | **Haiku** | A3.2 |
| **A3.6** | `ion_registry_regression_suite` | `tests/level2_gelation/test_ion_registry_regression.py` (new) | Golden-master regression: alginate-via-registry vs pre-refactor solver on full calibration set; numeric tolerance ≤ 1e-6 relative. | 200 | MEDIUM | **Sonnet** | A3.3 |
| **A4.1** | `functional_mode_extension` | `src/dpsim/module2_functionalization/reagent_profiles.py` (extend) | Add `functional_mode` allowed values: `dye_pseudo_affinity`, `mixed_mode_hcic`, `thiophilic`, `peptide_affinity`, `boronate`, `oligonucleotide`, `click_handle`, `material_as_ligand`. | 30 | LOW | **Haiku** | — |
| **A4.2** | `functional_mode_dispatch` | `src/dpsim/module2_functionalization/orchestrator.py` (extend) | Validation + dispatch logic that routes new modes to appropriate workflow handlers. | 110 | MEDIUM | **Sonnet** | A4.1 |
| **A5.1** | `chemistry_class_extension` | `src/dpsim/module2_functionalization/reactions.py` (extend) | Add `chemistry_class` allowed values: `oxime`, `hydrazone`, `cuaac`, `spaac`, `dye_triazine`, `cnbr_amine`, `cdi_amine`, `glyoxyl_multipoint`, `phenol_radical`. | 30 | LOW | **Haiku** | — |
| **A5.2** | `reaction_engine_dispatch` | `src/dpsim/module2_functionalization/reactions.py` (extend) | Reaction-engine kinetic-law selector for each new chemistry class. | 180 | MEDIUM | **Sonnet** | A5.1 |

**Milestone 0 totals:** 19 modules, ~2,200 LOC, **3 Opus + 11 Sonnet + 5 Haiku** assignments.

---

## 3. Module Registry — Workflow Batches (Milestones 1–9)

### 3.1 Milestone 1 — B1 Classical Affinity Resin Completion

| ID | Module | File path | Responsibility | LOC | Complexity | Model | Depends on |
|---|---|---|---|---|---|---|---|
| B1.1 | `agarose_only_parameter_set` | `src/dpsim/level2_gelation/agarose_only.py` (data block) | Reference parameters for unmodified agarose 4% / 6% beads (helix-coil T_gel, Young's modulus, pore size). Cite Cytiva Sepharose Application Note + Hagberg 2022 for kinetic constants. | 80 | LOW | **Haiku** | A2.2 |
| B1.2 | `cnbr_activation_profile` | `src/dpsim/module2_functionalization/reagent_profiles.py` (extend) | CNBr → CYANATE_ESTER ACS site; high-toxicity hazard flag; short activated-site half-life model; alkaline-hydrolysis competition. Cite Kohn & Wilchek 1981. | 110 | MEDIUM | **Sonnet** | A1.1, A4.1 |
| B1.3 | `cdi_activation_profile` | `src/dpsim/module2_functionalization/reagent_profiles.py` (extend) | CDI → IMIDAZOLYL_CARBONATE ACS; neutral activated matrix; carbamate kinetics. Cite Hearn 1981. | 100 | MEDIUM | **Sonnet** | A1.1, A4.1 |
| B1.4 | `hexyl_hic_ligand` | `src/dpsim/module2_functionalization/reagent_profiles.py` (extend) | Hexyl HIC ligand — pure parameter-only addition, alkyl-chain length 6 between butyl(4) and octyl(8). | 30 | LOW | **Haiku** | — |

**M1 totals:** 4 modules, ~320 LOC; **2 Sonnet + 2 Haiku**. Token estimate: ~6 k.

### 3.2 Milestone 2 — B2 Oriented-Glycoprotein Immobilization

| ID | Module | File path | Responsibility | LOC | Complexity | Model | Depends on |
|---|---|---|---|---|---|---|---|
| B2.1 | `periodate_oxidation_profile` | `src/dpsim/module2_functionalization/reagent_profiles.py` (extend) | NaIO₄ Malaprade kinetics (vicinal diol → aldehyde); oxidation-degree → aldehyde-density linear regime; chain-scission penalty above ~30–50% conversion. | 140 | MEDIUM–HIGH | **Sonnet** | A1.1, A5.1 |
| B2.2 | `adh_hydrazone_profile` | `src/dpsim/module2_functionalization/reagent_profiles.py` (extend) | ADH (adipic acid dihydrazide) hydrazone-coupling kinetics; reversible at pH < 5; reduction by NaBH₃CN gives covalent stability (existing NaBH₄ profile applies). | 120 | MEDIUM | **Sonnet** | A1.1 (HYDRAZIDE), A5.1 |
| B2.3 | `aminooxy_peg_linker_profile` | `src/dpsim/module2_functionalization/reagent_profiles.py` (extend) | Aminooxy-PEG linker; oxime ligation kinetics with aldehyde supports; bioorthogonality assertion. | 100 | MEDIUM | **Sonnet** | A1.1 (AMINOOXY), A5.1 |
| B2.4 | `oriented_glycoprotein_workflow_test` | `tests/module2_functionalization/test_workflow_oriented_glycoprotein.py` (new) | End-to-end workflow regression: agarose → periodate → ADH → glycoprotein-via-oxime; verify ligand-coupled-sites and activity-retention against published HRP-on-Sepharose data. | 180 | **HIGH** | **Opus** | B2.1, B2.2, B2.3 |

**M2 totals:** 4 modules, ~540 LOC; **1 Opus + 3 Sonnet**. Token estimate: ~12 k.

### 3.3 Milestone 3 — B3 Dye Pseudo-Affinity

| ID | Module | File path | Responsibility | LOC | Complexity | Model | Depends on |
|---|---|---|---|---|---|---|---|
| B3.1 | `cyanuric_chloride_activation_profile` | `src/dpsim/module2_functionalization/reagent_profiles.py` (extend) | Cyanuric chloride → TRIAZINE_REACTIVE ACS; staged substitution chemistry (mono-, di-, tri-substituted forms); hydrolysis competition. | 130 | MEDIUM | **Sonnet** | A1.1 (TRIAZINE_REACTIVE), A5.1 |
| B3.2 | `cibacron_blue_ligand_profile` | `src/dpsim/module2_functionalization/reagent_profiles.py` (extend) | Cibacron Blue F3GA: triazine-coupling, dye_pseudo_affinity functional_mode, salt/pH elution model, nonspecific-binding warning. | 130 | MEDIUM | **Sonnet** | B3.1, A4.1 |
| B3.3 | `dye_leakage_warning_model` | `src/dpsim/module2_functionalization/reagent_profiles.py` (extend) or `lifetime/leakage.py` (extend) | Dye-specific leakage model under regeneration; warning surface in M3 process dossier. | 100 | MEDIUM | **Sonnet** | B3.2 |

**M3 totals:** 3 modules, ~360 LOC; **3 Sonnet**. Token estimate: ~7 k.

### 3.4 Milestone 4 — B4 Mixed-Mode Antibody Capture

| ID | Module | File path | Responsibility | LOC | Complexity | Model | Depends on |
|---|---|---|---|---|---|---|---|
| B4.1 | `thiophilic_ligand_profile` | `src/dpsim/module2_functionalization/reagent_profiles.py` (extend) | DVS-mercaptoethanol thiophilic ligand; salt-promoted binding; thiophilic functional_mode. Reuses existing DVS activation. | 100 | MEDIUM | **Sonnet** | A4.1 |
| B4.2 | `mep_hcic_profile` | `src/dpsim/module2_functionalization/reagent_profiles.py` (extend) | 4-mercaptoethylpyridine HCIC: pH-switchable hydrophobic→cationic transition (pKa ≈ 4.5 of pyridinium); IgG-specific binding model; antibody-elution dispatcher. | 200 | **HIGH** | **Opus** | A4.1, A5.1 |

**M4 totals:** 2 modules, ~300 LOC; **1 Opus + 1 Sonnet**. Token estimate: ~9 k.

### 3.5 Milestone 5 — B5 Bis-Epoxide Hardening

| ID | Module | File path | Responsibility | LOC | Complexity | Model | Depends on |
|---|---|---|---|---|---|---|---|
| B5.1 | `bis_epoxide_family_profile` | `src/dpsim/reagent_library.py` (extend) — `CrosslinkerProfile` | PEGDGE / EGDGE / BDDE bis-epoxide profiles with spacer-length parameter; alkaline-pH-dependent kinetics; hydrolysis-competition; residual-epoxide prediction. | 160 | MEDIUM | **Sonnet** | — |
| B5.2 | `bis_epoxide_spacer_integration` | `src/dpsim/level3_crosslinking/spacer_aware.py` (extend or new) | Spacer-length-aware ligand-display model that consumes bis-epoxide spacer as both crosslinker and pseudo-spacer. | 120 | MEDIUM | **Sonnet** | B5.1 |

**M5 totals:** 2 modules, ~280 LOC; **2 Sonnet**. Token estimate: ~6 k.

### 3.6 Milestone 6 — B7 Click Chemistry Handle

| ID | Module | File path | Responsibility | LOC | Complexity | Model | Depends on |
|---|---|---|---|---|---|---|---|
| B7.1 | `cuaac_handle_profile` | `src/dpsim/module2_functionalization/reagent_profiles.py` (extend) | CuAAC azide+alkyne click chemistry; Cu(I) catalysis kinetics; Cu-residue tracking flag (ICH Q3D compliance). | 180 | **HIGH** | **Opus** | A1.1 (AZIDE, ALKYNE), A5.1 |
| B7.2 | `spaac_variant_profile` | `src/dpsim/module2_functionalization/reagent_profiles.py` (extend) | SPAAC strain-promoted variant (DBCO/BCN); copper-free; slower kinetics; biotherapeutic-compatible. | 120 | MEDIUM | **Sonnet** | B7.1 |
| B7.3 | `click_ligand_library_harness` | `tests/module2_functionalization/test_click_ligand_library.py` (new) | Modular ligand-library plug-in test harness: any ligand-with-azide-handle should integrate via the same code path. | 130 | MEDIUM | **Sonnet** | B7.1, B7.2 |

**M6 totals:** 3 modules, ~430 LOC; **1 Opus + 2 Sonnet**. Token estimate: ~10 k.

### 3.7 Milestone 7 — B8 Multipoint Enzyme Immobilization

| ID | Module | File path | Responsibility | LOC | Complexity | Model | Depends on |
|---|---|---|---|---|---|---|---|
| B8.1 | `glyoxyl_chained_activation` | `src/dpsim/module2_functionalization/reagent_profiles.py` (extend) | Two-step activation chain: glycidol → glyceryl-ether → periodate → glyoxyl. Aldehyde-density tunable via glycidol density × periodate dose. | 200 | **HIGH** | **Opus** | A1.1 (GLYOXYL), A5.1 |
| B8.2 | `multipoint_enzyme_stability_model` | `src/dpsim/module3_performance/catalysis/multipoint_immobilization.py` (new) | Multi-Lys covalent anchoring → operational/thermal stability uplift; reduce thermal-deactivation rate constant as function of anchor count. | 180 | **HIGH** | **Opus** | B8.1 |

**M7 totals:** 2 modules, ~380 LOC; **2 Opus**. Token estimate: ~12 k.

### 3.8 Milestone 8 — B9 Material-as-Ligand Pattern

| ID | Module | File path | Responsibility | LOC | Complexity | Model | Depends on |
|---|---|---|---|---|---|---|---|
| B9.1 | `material_as_ligand_flag` | `src/dpsim/datatypes.py::PolymerFamily` (extend) | Add `material_as_ligand: bool = False` and `competitive_eluent: Optional[str] = None` fields on family meta. Existing solvers ignore the flag (non-breaking). | 60 | LOW | **Haiku** | A2.1 |
| B9.2 | `amylose_resin_profile` | `src/dpsim/module2_functionalization/reagent_profiles.py` (extend) — material-mode | AMYLOSE family + MBP-tag affinity binding; maltose-competitive elution kinetics. | 150 | MEDIUM | **Sonnet** | B9.1, A4.1 |
| B9.3 | `mbp_amylose_workflow_test` | `tests/module3_performance/test_mbp_amylose_workflow.py` (new) | End-to-end workflow: bind MBP-tagged protein on amylose; wash; elute with maltose gradient; compare DBC and yield to NEB protocol. | 120 | MEDIUM | **Sonnet** | B9.2 |

**M8 totals:** 3 modules, ~330 LOC; **2 Sonnet + 1 Haiku**. Token estimate: ~7 k.

### 3.9 Milestone 9 — B10 Boronate Affinity

| ID | Module | File path | Responsibility | LOC | Complexity | Model | Depends on |
|---|---|---|---|---|---|---|---|
| B10.1 | `aminophenyl_boronic_acid_profile` | `src/dpsim/module2_functionalization/reagent_profiles.py` (extend) | APBA ligand profile with cis-diol target; pH-dependent boronate speciation (pKa ≈ 8.5); boronate functional_mode. | 160 | MEDIUM–HIGH | **Sonnet** | A1.1 (CIS_DIOL), A4.1 |
| B10.2 | `boronate_speciation_model` | `src/dpsim/module2_functionalization/reactions.py` (extend) — phenol_radical/boronate path | Tetrahedral/trigonal boronate equilibrium as a function of pH; cis-diol esterification kinetics. | 180 | MEDIUM–HIGH | **Sonnet** | B10.1, A5.1 |

**M9 totals:** 2 modules, ~340 LOC; **2 Sonnet**. Token estimate: ~7 k.

---

## 4. Module Dependency DAG

```
─── Milestone 0 (Architectural Foundation) ───────────────────────────────────

A1.1 ──┬─> A1.2
       ├─> A1.3
       ├─> A4.1 ─> A4.2
       └─> A5.1 ─> A5.2

A2.1 ──┬─> A2.2 ─┐
       ├─> A2.3 ─┼─> A2.5 (composite refactor)
       │         │
       ├─> A2.4  │
       ├─> A2.6  │
       └─> A2.7  │
                 │
A3.1 ──> A3.2 ───┼─> A3.3 ─> A3.6
                 │   ├─> A3.4
                 │   └─> A3.5

─── Milestones 1–9 (Workflow Batches) ────────────────────────────────────────

A1.1 + A4.1 ─────┬─> M1 (B1: classical affinity)
                 ├─> M2 (B2: oriented glycoprotein)
A1.1 + A5.1 ─────┤   │
                 ├─> M3 (B3: dye affinity)        ──┐
                 ├─> M4 (B4: mixed-mode HCIC)       │
A2.2 ────────────┤   │                              │
                 ├─> M6 (B7: click chemistry)       │ All
                 ├─> M7 (B8: multipoint enzyme)     │ Tier-2
                 ├─> M8 (B9: material-as-ligand)    │ batches
A4.1 ────────────┤   │                              │ depend on
                 └─> M9 (B10: boronate affinity)  ──┘ M0 only

(none) ──────────> M5 (B5: bis-epoxide hardening — independent)
```

**Critical path** (longest dependency chain): A2.1 → A2.2 → A2.5 → (any of M1–M9) ≈ 4 hops + 1 batch.

**Parallelism opportunity:** Milestones 1–9 are mutually independent given M0 — they can be sequenced in any order or interleaved. Recommended sequence is **risk-weighted ordering** (M1 first to consume A1+A4 quickly and stabilize the activation/coupling layer; M2 second to validate the bioorthogonal chain; M5 anywhere because it has no M0 dependencies beyond the existing crosslinker library).

---

## 5. Per-Milestone Acceptance Tests

Each milestone must pass an **end-to-end published reference protocol** before the milestone is closed. Generic unit/regression tests (pytest) live alongside the modules; the acceptance test exercises the entire workflow against a literature-anchored quantitative target.

| Milestone | Reference protocol | Quantitative target | Source |
|---|---|---|---|
| **M0** | Alginate Ca²⁺ gelation regression on existing v9.1 calibration set; agarose-chitosan composite must reproduce legacy outputs to ≤ 1e-6 relative tolerance | Numeric identity on golden master | Internal calibration suite |
| **M1** | IgG coupling on CNBr-activated Sepharose 4B at saturating loading | DBC ≥ 35 mg IgG / mL resin (target ±20%) | Cytiva Sepharose 4B Datasheet |
| **M2** | HRP coupling to oxidized agarose via aminooxy-PEG (oriented immobilization) | Activity retention ≥ 70% (vs. random Lys-coupled on glyoxyl as baseline) | Rodrigues et al., Biotechnol. Adv. 2013 |
| **M3** | BSA depletion on Cibacron Blue Sepharose at pH 7 | ≥ 90% BSA depletion at 1:1 mol ratio | Cytiva Blue Sepharose 6 FF datasheet |
| **M4** | IgG capture on MEP HyperCel-equivalent at pH 7, elution at pH 4 | DBC ≥ 25 mg IgG / mL; elution recovery ≥ 85% | Pall MEP HyperCel application note |
| **M5** | HA (1 wt%) hardening with BDDE 2% (mol/mol HA-OH) in 0.25 M NaOH, 25 °C, 4 h | Storage modulus G' ≥ 1 kPa post-cure | Hahn et al., Biomaterials 2006 |
| **M6** | Azide-functionalized peptide coupling to alkyne-agarose via CuAAC | Coupling efficiency ≥ 80% at 1 mM CuSO₄ + 5 mM ascorbate, 25 °C, 1 h | Quesada-González et al., Bioconjug. Chem. 2013 |
| **M7** | Lipase B (CALB) immobilization on glyoxyl-agarose; thermostability uplift | T₅₀ uplift ≥ 10 °C vs. soluble enzyme | Mateo et al., Biotechnol. Bioeng. 2007 |
| **M8** | MBP-tagged protein on amylose resin; maltose elution | DBC ≥ 3 mg MBP-fusion / mL; elution recovery ≥ 80% with 10 mM maltose | NEB amylose resin protocol |
| **M9** | HbA1c (glycated hemoglobin) capture on phenylboronate at pH 8.5; sorbitol elution | ≥ 95% recovery; resolution from non-glycated Hb ≥ 1.5 | Mallia et al., J. Chromatogr. A 1989 |

Acceptance tests run on the simulator pipeline (M1 → M2 → M3) using the parameters claimed by the source publication. Pass criterion: predicted observable within the source's reported uncertainty band, OR within ±20% if uncertainty is not reported.

---

## 6. Per-Module Model-Tier Rationale (audit-ready)

Per Reference 02 §3 decision procedure:

**Opus assignments** (always-Opus tasks + HIGH-complexity modules):

| Module | Complexity drivers | Why Opus |
|---|---|---|
| A2.2 `agarose_only_solver` | Refactor of foundational gelation kernel; preservation of legacy numerics is non-negotiable | Risk of breaking calibrated v9.1 behaviour |
| A3.3 `alginate_solver_via_registry` | Foundation refactor; same legacy-preservation risk | Same |
| B2.4 `oriented_glycoprotein_workflow_test` | Cross-module integration test — exercises M0 + M2 modules | Multi-module logic + scientific validation |
| B4.2 `mep_hcic_profile` | Novel pH-switchable mixed-mode physics | Domain-specific science |
| B7.1 `cuaac_handle_profile` | Novel ligand-coupling chemistry; Cu-residue tracking | Domain + new abstraction |
| B8.1 `glyoxyl_chained_activation` | Two-step activation chain; new abstraction | Multi-step novel chemistry |
| B8.2 `multipoint_enzyme_stability_model` | New scientific model (multi-anchor → thermostability) | Domain expertise |

**Audits (always Opus per Reference 02):**
- Phase 3 six-dimension audit on every module
- Milestone handover at each of M0–M9 boundary

**Sonnet assignments:** standard reagent-profile additions (50–200 LOC, well-bounded chemistry, established kinetic forms), regression tests, dispatch-layer extensions. Total: 22 modules.

**Haiku assignments:** enum extensions, parameter-block additions, family-reagent matrix columns. Total: 7 modules.

**Token-savings projection** (per Reference 02 §5): 41 modules × 1 Opus / 22 Sonnet / 7 Haiku → estimated **~50% savings vs. all-Opus baseline** (versus the 55–65% target). Lower than the ideal because Tier-1 carries 7 Opus assignments (compared to the typical 5/25 in the reference projection); this reflects the foundational nature of the v9.2 cycle.

---

## 7. Architect's Risk Audit (D1–D6 against the plan)

Pre-emptive audit of the *plan itself* across the six dimensions per Reference 05.

| Dim | Risk | Severity | Mitigation |
|---|---|---|---|
| **D1 Structural** | A2 PolymerFamily expansion may break the v9.0 Family-First UI rendering matrix when it sees an unfamiliar family value. | HIGH | `is_enabled_in_ui` flag (A2.1) + UI-side acceptance test + the Streamlit reload-safe `.value` comparison from CLAUDE.md. |
| **D2 Algorithmic** | A3 ion-registry refactor changes the calling shape of the alginate solver; calibrated kinetic constants must be preserved exactly. | HIGH | A3.6 golden-master regression suite at numeric tolerance ≤ 1e-6 relative; alginate-via-registry must reproduce legacy outputs bit-for-bit on the existing calibration set. |
| **D3 Data-flow** | New `ACSSiteType` members propagate through `ACSProfile` conservation accounting; bookkeeping bugs would silently violate the conservation law. | HIGH | A1.2 conservation-law unit tests gated at the `_CONSERVATION_TOL` threshold (1.001) for all 25 site types. |
| **D4 Performance** | The reaction-engine dispatch (A5.2) adds branches per chemistry class; could regress hot-path performance for the existing ECH/EDC paths. | MEDIUM | Performance budget: existing M2 reactions must complete in ≤ 110% of v9.1 wall-time. Audit gate at G3-04. |
| **D5 Maintainability** | 41 modules across 10 milestones is a large surface; documentation drift between protocols and code is likely. | MEDIUM | Each milestone's Approval phase (Phase 5) includes a docs synchronization step; protocols are checked into `docs/protocols/` before Phase 2 starts. |
| **D6 First-principles** | New chemistry classes (oxime, hydrazone, CuAAC) carry domain-specific kinetic forms; wrong rate-law selection would silently produce non-physical predictions. | HIGH | Each new `chemistry_class` value (A5.1) requires a one-paragraph scientific justification citing 1° literature in the module docstring. Scientific Advisor escalation per Reference 06 if any class is uncertain. |

---

## 8. Architect's Notes for the Orchestrator

- **Pre-flight context check** for each milestone start: estimate ≈ 6–12 k tokens per workflow batch; M0 estimated 35–50 k tokens (the architectural foundation is the largest milestone). The orchestrator should plan a milestone handover *immediately after* M0 closes, before M1 begins, because M0 alone consumes a full session budget.

- **Compression triggers:** at the end of every workflow milestone (M1, M2, …), produce a milestone handover. This is more frequent than the dev-orchestrator default but is justified by the breadth of new chemistry — losing a milestone's worth of state mid-session would be expensive to reconstruct.

- **Fix-cycle expectation:** A2.2, A3.3, B2.4, B4.2, B7.1, B8.1, B8.2 are the high-risk modules. Budget 2 fix rounds per Opus module on average (vs. the 1-round target).

- **Escalation paths:** the Scientific Advisor should be re-engaged if (a) M2 oxime workflow produces non-physical activity-retention values, (b) M4 MEP pH-switch model produces binding curves inconsistent with the Cytiva application note, (c) M7 multipoint stability model produces T₅₀ uplifts above 30 °C (would indicate the model is over-correcting).

- **Tier-2 staging:** when M0 closes and Tier 2 begins, the architect's first action is to publish a Tier-2 amendment document. The data-only library extensions (M7, M8 parameter packs, plus all the polysaccharide-extension materials) require no further architectural change once M0 is APPROVED.

---

## 9. Architect's deliverable checklist (against Reference 03)

- [x] Module Implementation Protocol scaffolding for each of 41 modules (file path, responsibility, dependency, complexity, tier)
- [x] Interface specifications declared via existing dataclasses (`ACSSiteType`, `ReagentProfile`, `IonGelantProfile`)
- [x] Algorithm references cited via 1° literature in §3 / §5
- [x] Acceptance tests defined per milestone in §5
- [x] Build order with dependency DAG in §4
- [x] Model tier rationale per Reference 02 §3 in §6
- [x] D1–D6 plan-level audit in §7
- [x] Orchestrator handoff notes in §8

The detailed Phase-1 protocols (G1 12-point check) are deferred to the start of each module's pre-flight (Phase 0). This decomposition document is the input to those protocols; the orchestrator will sequence them.

---

> **Architect's disclaimer:** This decomposition is the design authority's view. Implementation-time deviations must be raised back to /architect for protocol revision, not silently absorbed by /scientific-coder. Per Reference 05, fix cycles are capped at 3 rounds per module before REDESIGN escalation.
