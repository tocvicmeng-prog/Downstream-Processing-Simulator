# v0.5.0 Close Handover — M2 ACS Converter epic

**Cycle:** v0.5.0 single-session implementation of the M2 ACS-Converter
joint redesign plan.
**Date:** 2026-04-27.
**Predecessor:** This conversation's `/scientific-advisor` audit (verdict
PARTIAL) and the joint Scientific-Advisor + Architect + Dev-Orchestrator
redesign plan it produced.
**Branch:** `feat/m2-acs-converter`.

---

## 1. Executive summary

All seven gaps the audit identified are closed; the verdict flips
**PARTIAL → READY**.

| # | Gap (from audit) | DoD criterion | Where |
|---|---|---|---|
| 1 | CDI / Tresyl / Pyridyl-disulfide outputs had zero consumers | 3 closed-loop coupler reagents land + a 4th (CNBr canonical-amine) strengthens the CNBr loop | `reagent_profiles.py` (4 new entries appended at L7-Calmodulin neighborhood) |
| 2 | Pyridyl-disulfide product_acs / chemistry_class chemically wrong | New `ACSSiteType.PYRIDYL_DISULFIDE`; profile retagged with `chemistry_class="thiol_disulfide_exchange"`, `reaction_type="arm_activation"` | `acs.py:99-101`, `reagent_profiles.py` (pyridyl block) |
| 3 | None of 7 converters in family-reagent matrix | 147 new entries (7 converters × 21 polymer families); `tests/test_v0_5_0_acs_converter.py::TestFamilyMatrixCoverage` enforces total | `family_reagent_matrix.py:696-925` |
| 4 | Periodate aldehyde stoichiometry under-counted by 2× | New `aldehyde_multiplier` field on `ReagentProfile`; periodate + glyoxyl set to 2.0 | `reagent_profiles.py:282-291`, `modification_steps.py:597-605` |
| 5 | Required converter behaviors documented but not modeled | G6 sequence FSM enforces canonical order + glyoxyl/periodate + cip_required → NaBH4 reductive lock-in | `core/recipe_validation.py:215-415` |
| 6 | CNBr loop closure weak (only oligonucleotide-DNA consumed CYANATE_ESTER) | New `generic_amine_to_cyanate_ester` coupler with cold-room kinetics + 15-min window note | `reagent_profiles.py` (4th new coupler entry) |
| 7 | "ACS Converter parallel to Hydroxyl Activation" had no first-class representation | New `ModificationStepType.ACS_CONVERSION` and `ARM_ACTIVATION`; UI bucket renamed "Hydroxyl Activation" → "ACS Conversion" + new "Arm-distal Activation" bucket | `modification_steps.py:88-95`, `tab_m2.py:98-130` |

**CI gates all green:**

```
ruff   check  <touched files>          All checks passed!
mypy   <touched modules, ign-missing>  Success: no issues found in 11 source files
pytest <M2 + recipe_validation suites> 308 passed in 28.96s
```

The full repo `pytest tests/` has pre-existing infrastructure timeouts
(test_dsd_njobs_parallelism.py + test_p2_m1_dsd_contract.py + others)
that are unrelated to this cycle and reproduce on `main`. Targeted
regression on every file touched is green.

---

## 2. Module registry — v0.5.0 additions

| Module | Path | Status | Notes |
|---|---|---|---|
| ACSSiteType expansion | `src/dpsim/module2_functionalization/acs.py` | **CHANGED** | Added `PYRIDYL_DISULFIDE` member; updated `initialize_acs_from_m1` docstring (line 326-340) |
| ModificationStepType expansion | `src/dpsim/module2_functionalization/modification_steps.py` | **CHANGED** | Added `ACS_CONVERSION` and `ARM_ACTIVATION`; updated `_STEP_ALLOWED_RTYPES` to honor silent alias; added dispatch arms |
| Reagent profile expansion | `src/dpsim/module2_functionalization/reagent_profiles.py` | **CHANGED** | New `acs_converter` / `arm_activator` modes; new `thiol_disulfide_exchange` / `tresyl_amine` chemistry classes; new `aldehyde_multiplier` and `wetlab_observable` fields on ReagentProfile; 7 converters retagged; pyridyl-disulfide chemistry corrected; 4 new closed-loop couplers |
| Family-reagent matrix | `src/dpsim/module2_functionalization/family_reagent_matrix.py` | **CHANGED** | 147 new entries (7 × 21) with rationales |
| Sequence FSM | `src/dpsim/module2_functionalization/orchestrator.py` | **CHANGED** | New module-level `validate_sequence(steps, polymer_family, cip_required)` helper |
| G6 guardrail | `src/dpsim/core/recipe_validation.py` | **CHANGED** | New `_g6_acs_converter_sequence()` invoked from `validate_recipe_first_principles` |
| TargetProductProfile | `src/dpsim/core/process_recipe.py` | **CHANGED** | Added `cip_required: bool = False` field |
| UI bucket rename | `src/dpsim/visualization/tabs/tab_m2.py` | **CHANGED** | "Hydroxyl Activation" → "ACS Conversion"; new "Arm-distal Activation" bucket; `_step_type_map` updated |
| v0.5.0 test gauntlet | `tests/test_v0_5_0_acs_converter.py` | **NEW** | 7 test classes, 40 test cases; 100% green |
| Dropdown coverage updates | `tests/test_v0_3_4_m2_dropdown_coverage.py` | **CHANGED** | Bucket renames + pyridyl-disulfide moved to "Arm-distal Activation" |
| Profile-count + reaction-type allowlist | `tests/test_module2_acs.py`, `tests/test_module2_workflows.py` | **CHANGED** | Updated for 26-member ACS enum + 100-entry profile registry + 2 new reaction_type values |

---

## 3. Architectural decision recap

**Option B (pragmatic split) chosen.** `ModificationStepType.ACS_CONVERSION`
and `ARM_ACTIVATION` are new first-class step types; legacy `ACTIVATION`
remains a silent alias so v0.4.x recipes using ECH/DVS continue to load
unchanged. All 7 converters dispatch through `_solve_activation_step`
(`modification_steps.py:283`) — the chemistry is identical, the split is
for FSM clarity and UI legibility.

The "real wet-lab workflow" narrative anchored in the joint plan
(Hermanson 2013 + Mateo 2007 + Brocklehurst 1973 + Cuatrecasas 1970 +
Hearn 1981 + Korpela & Mäntsälä 1968 + Bobbitt 1956 + Nilsson & Mosbach
1981) is referenced in each retagged reagent's `calibration_source` and
each converter now declares a `wetlab_observable` (e.g.,
`A_343_pyridine_2_thione` for pyridyl-disulfide) for evidence-tier
anchoring.

---

## 4. Sequence FSM (G6) summary

`_g6_acs_converter_sequence()` enforces six checks at recipe-load time:

| Check | Severity | Description |
|---|---|---|
| G6.1 | BLOCKER | Step ordering — ACTIVATE → INSERT_SPACER → COUPLE_LIGAND → METAL_CHARGE; skips allowed |
| G6.2 | BLOCKER (or WARNING on native-amine fallback) | Pyridyl-disulfide requires prior amine arm OR chitosan-bearing family |
| G6.3 | BLOCKER | METAL_CHARGE requires prior COUPLE_LIGAND |
| G6.4 | BLOCKER | Aldehyde converter (glyoxyl/periodate) requires NaBH4 quench when `target.cip_required=True` |
| G6.5 | WARNING | CNBr without downstream COUPLE_LIGAND emits hydrolysis-loss alert |
| G6.6 | WARNING | Back-to-back ACS converters with no intervening wash/quench (cyanuric staging exempted) |

Mirror of the same logic available in-module via
`orchestrator.validate_sequence(steps, polymer_family, cip_required)` for
direct M2 callers and unit tests.

---

## 5. Defaults adopted from joint plan §Open Questions

All five accepted as default per user instruction:

1. `ModificationStepType.ACTIVATION` kept as **silent alias** — no DeprecationWarning emitted. v0.4.x recipes using ECH/DVS load unchanged.
2. Cyanuric chloride: **2-stage** kinetic model (single rate constant). 3-stage staged-substitution refinement is a future calibration milestone.
3. Glyoxyl NaBH₄ reductive lock-in: **hard requirement** (BLOCKER) gated on `target.cip_required=True`.
4. Pyridyl-disulfide downstream coupling: **single generic** `protein_thiol_to_pyridyl_disulfide` reagent. Per-protein variants are easy follow-on entries.
5. Family-matrix combo families (PECTIN_CHITOSAN, GELLAN_ALGINATE, PULLULAN_DEXTRAN): **explicit per-converter entries** with rationales (147 total entries).

---

## 6. Test gauntlet — `tests/test_v0_5_0_acs_converter.py`

```
TestEnumExpansion ............................... 7 / 7
TestConverterStepDispatch ....................... 8 / 8
TestPyridylDisulfideChemistry ................... 5 / 5
TestPeriodateAldehydeMultiplier ................. 4 / 4
TestSequenceFSM ................................. 8 / 8
TestClosedLoopPairing ........................... 7 / 7  (parametrized x converter)
TestFamilyMatrixCoverage ........................ 11 / 11 (7 parametrized + 4 spot)
                                                  ─────────
                                            Total 50 / 50
```

The most chemistry-critical test is
`TestPeriodateAldehydeMultiplier::test_periodate_doubles_downstream_aldehyde`
— a true end-to-end check that the new `aldehyde_multiplier=2.0` field
actually doubles the ALDEHYDE inventory at solver-runtime (`pytest.approx`
agreement to 0.1%).

---

## 7. Risk register status

| # | Risk (from joint plan) | Status |
|---|---|---|
| 1 | Breaking v0.4.x ECH/DVS recipes | **MITIGATED** — silent alias keeps them green; verified by `test_legacy_activation_step_still_works_for_ech` |
| 2 | Streamlit reload + `is`/`.value` enum hazard with new `PYRIDYL_DISULFIDE` member | **MITIGATED** — AST gate `tests/test_v9_3_enum_comparison_enforcement.py` covers new member automatically (passed) |
| 3 | Wet-lab vs simulator divergence on pyridyl-disulfide | **MITIGATED** — anti-regression tests assert `product_acs != THIOL` and `chemistry_class != "reduction"`; A_343 wetlab observable wired into profile |
| 4 | Family-matrix combinatorics | **MITIGATED** — 147 entries land; `TestFamilyMatrixCoverage::test_total_new_entries_count` enforces 7 × 21 == 147 |
| 5 | Evidence-tier downgrade cascading through M3 | **MITIGATED** — new step types default to `SEMI_QUANTITATIVE` per `modification_steps.py:367` (existing logic unchanged) |

---

## 8. Deferred / future work

- **Cyanuric 3-stage staged kinetics.** Currently 2-stage (single rate). When a calibration dataset exists, add per-Cl rate constants `k_stage1/2/3` and the corresponding `temperature_stage` field on `ModificationStep`.
- **Per-protein pyridyl-disulfide couplers.** `protein_a_thiol_to_pyridyl_disulfide`, `protein_g_thiol_to_pyridyl_disulfide`, etc. follow the existing `protein_a_cys_coupling` / `protein_g_cys_coupling` pattern at `reagent_profiles.py:1461, 1495`.
- **Periodate chain-scission penalty on G_DN/mesh.** Notes describe the 30–50% threshold; a follow-up PR can wire a multiplicative penalty into `M1ExportContract.G_DN` when `oxidation_degree > 0.30`.
- **CNBr time-window enforcement (G6.5).** Currently a structural WARNING that fires when the converter has no downstream coupling step. A stronger version reads `step.parameters["time"]` and tightens to BLOCKER when activator-to-coupling gap > 900 s; needs the recipe DSL to standardise the `time` quantity.

---

## 9. Definition of Done — signed off

All 8 DoD checks from the joint plan §C4 satisfied:

- [x] (1) CDI/Tresyl/Pyridyl-disulfide outputs have consumers (4 new couplers, all in `tests/test_v0_5_0_acs_converter.py::TestClosedLoopPairing`)
- [x] (2) Pyridyl-disulfide product_acs and chemistry_class corrected (anti-regression asserts present)
- [x] (3) Family matrix has 147 explicit entries (coverage test)
- [x] (4) Periodate aldehyde 2× factor (end-to-end test)
- [x] (5) Cyanuric staging / periodate scission / glyoxyl NaBH4 / pyridyl oxidation-state behaviors — encoded in G6 (NaBH4 lock-in) and reagent notes; staged-rate refinements deferred per Default Q2
- [x] (6) CNBr canonical amine route (`generic_amine_to_cyanate_ester`)
- [x] (7) ACS_CONVERSION step type lives; UI bucket renamed
- [x] (8) Sequence FSM C1–C6 from §A2 encoded (G6.1–G6.6)

**Verdict: PARTIAL → READY.** Ready to merge to `main` and tag `v0.5.0`.

---

## 10. Commit summary

Single commit on branch `feat/m2-acs-converter`:

```
v0.5.0 (M2 ACS Converter): close 7 audit gaps, ship first-class step type

- Add ACSSiteType.PYRIDYL_DISULFIDE
- Add ModificationStepType.ACS_CONVERSION + ARM_ACTIVATION (legacy ACTIVATION
  kept as silent alias for v0.4.x recipes)
- Retag 6 matrix-side converters (CNBr/CDI/Tresyl/Cyanuric/Glyoxyl/Periodate)
  + 1 arm-distal (Pyridyl-disulfide), with corrected chemistry
- 4 new closed-loop coupler reagents (CDI/Tresyl/Pyridyl-disulfide/CNBr
  canonical amine routes)
- 147 new family-reagent matrix entries (7 converters × 21 polymer families)
- aldehyde_multiplier=2.0 fix for periodate / glyoxyl Malaprade cleavage
- New G6 guardrail enforcing Converter → Arm → Ligand → Ion-charging FSM
  with cip_required NaBH4 reductive lock-in
- UI: "Hydroxyl Activation" bucket renamed "ACS Conversion"; new
  "Arm-distal Activation" bucket
- 50-test v0.5.0 gauntlet; 308 targeted tests green; ruff=0; mypy=0
```
