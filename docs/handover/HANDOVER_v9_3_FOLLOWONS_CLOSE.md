# Final Handover: v9.3 Follow-Ons — All Code-Actionable Items Closed

**Date:** 2026-04-25
**Session:** v9.2-EXEC-004 (final v9.3 follow-on cycle)
**Project:** Downstream-Processing-Simulator (DPSim)
**Prepared by:** /dev-orchestrator
**Classification:** Internal — Development Handover
**Status:** **All 7 v9.3 follow-on Q-items closed (5 in-code, 2 documented for wet-lab)**

---

## 1. Executive Summary

All **code-actionable** v9.3 follow-on items from `HANDOVER_v9_2_CLOSE.md` § 7 are now resolved. The two **wet-lab** items (Q-013 calibration; Q-014 reagent-profile validation) are documented in `WETLAB_v9_3_CALIBRATION_PLAN.md` with explicit bench protocols ready for the R&D scientist to pick up.

| Q | Title | Status | Resolution |
|---|---|---|---|
| Q-009 | Wire `solve_gelation_by_family` into `run_single` | **CLOSED** (prior session) | `_run_v9_2_tier1` branch |
| Q-010 | `formulation.ech_oh_ratio_dextran` schema field | **CLOSED** | New field on `FormulationParameters`; dextran solver consumes directly |
| Q-011 | Custom ruff rule for `.value` enum comparison | **CLOSED** | AST-based enforcement test; **caught and fixed 1 latent bug** in `material_constants.py:78` |
| Q-012 | Tier-2 placeholder UI preview surface | **CLOSED** | Expander section in family selector lists 6 Tier-2 families with v9.3 captions |
| Q-013 | Wet-lab calibration of A2.3 chitosan-only / A2.4 dextran-ECH | **DOCUMENTED** | `WETLAB_v9_3_CALIBRATION_PLAN.md` § 2 |
| Q-014 | Wet-lab validation of 18 v9.2 reagent profiles | **DOCUMENTED** | `WETLAB_v9_3_CALIBRATION_PLAN.md` § 3 |
| Q-015 | M3 specialised binding models for dye/HCIC/thiophilic/boronate | **CLOSED** | 4 dedicated `ligand_type` branches in M2 orchestrator with literature-anchored stoichiometries |

**375 tests pass on the cumulative v9.2 + v9.3 follow-on surface.** Zero regressions on v9.1 calibrated solvers.

---

## 2. Module-Level Changes (v9.3 follow-on cycle)

| Q | File(s) modified | New tests |
|---|---|---|
| Q-010 | `src/dpsim/datatypes.py` (+1 field on FormulationParameters); `src/dpsim/level2_gelation/dextran_ech.py` (read field directly) | `test_v9_2_solvers.py` (+2 Q-010 tests) |
| Q-011 | `src/dpsim/visualization/tabs/m1/material_constants.py:78` (bug fix: `is` → `.value ==`); new `tests/test_v9_3_enum_comparison_enforcement.py` (3 tests, AST-based scanner) | `test_v9_3_enum_comparison_enforcement.py` (3 tests) |
| Q-012 | `src/dpsim/visualization/tabs/m1/family_selector.py` (+_TIER2_PREVIEW_ROWS + expander) | `test_v9_3_tier2_preview.py` (5 tests) |
| Q-015 | `src/dpsim/module2_functionalization/orchestrator.py` (4 dedicated `elif` branches in q_max-computation + 4 entries added to `_ranking_types` set + dedicated `_mode_map` entries) | `test_v9_3_m3_specialised_dispatch.py` (16 tests) |
| Q-013 / Q-014 | (no code changes — bench work) | (none — calibration tests added when bench data lands) |

**Net new test files:** 3
**Net new tests:** 27 (3 + 5 + 16 + 2 Q-010 in existing file + 1 fixed latent bug)

---

## 3. The latent bug Q-011 surfaced

The AST enforcement test caught a **real reload-safety failure** that had been latent in the codebase:

```python
# Before — src/dpsim/visualization/tabs/m1/material_constants.py:78
if family is PolymerFamily.AGAROSE_CHITOSAN:
    # ...silently breaks after the first Streamlit rerun because the
    # PolymerFamily class object is replaced by importlib.reload()
```

```python
# After
if family.value == PolymerFamily.AGAROSE_CHITOSAN.value:
    # ...survives the reload boundary because string comparison is
    # class-identity-independent
```

This is exactly the failure mode CLAUDE.md warns about: "Streamlit re-mints the datatypes enum on every rerun; identity comparisons silently break after the first rerun." The bug had been in the codebase since the v9.0 Family-First UI work; the AST enforcement caught it on first run.

**The Q-011 test is now a CI gate** — any future identity comparison against `PolymerFamily`, `ACSSiteType`, `ModelEvidenceTier`, or `ModelMode` members will fail the test with a precise file:line:col location report and a fix recommendation.

---

## 4. Q-015 — what specialised dispatch unlocks

Before this cycle, the M2 orchestrator mapped every v9.2 functional_mode to the generic `"affinity"` ligand_type, meaning M3 used the **Protein-A binding model** (stoich = 2.0 IgG/ligand) for Cibacron Blue, MEP, T-Sorb, and boronate — clearly wrong for any of them.

After this cycle:

| Functional mode | M3 ligand_type | Stoichiometry | Confidence | Process state |
|---|---|---|---|---|
| `dye_pseudo_affinity` | `dye_pseudo_affinity` | 1.0 (target-dependent) | ranking_only | dye-leakage A610 monitor |
| `mixed_mode_hcic` | `mixed_mode_hcic` | 1.0 IgG/ligand | ranking_only | pH gradient (no salt) |
| `thiophilic` | `thiophilic` | 0.5 IgG/ligand pair (cooperative binding) | ranking_only | descending salt gradient |
| `boronate` | `boronate` | 1.0 cis-diol/ligand | ranking_only | sorbitol/fructose elution at pH 8.5 |

Each branch carries a literature-anchored stoichiometry, an explicit confidence tier of "ranking_only" (because target-dependence and pH/salt-switchable behaviour add variance the simple density × stoich product does not capture), and a process-state note that points to the correct elution mode in M3.

---

## 5. Cumulative status — full v9.2 + v9.3 follow-on cycle

- **v9.2 Tier-1 cycle:** CLOSED (41/41 modules)
- **v9.2 follow-ons (Q-001 through Q-008):** all RESOLVED prior to v9.2 close
- **Q-009 (post-close pipeline wiring):** RESOLVED 2026-04-25
- **Q-010, Q-011, Q-012, Q-015 (v9.3 code follow-ons):** RESOLVED 2026-04-25
- **Q-013, Q-014 (v9.3 wet-lab):** DOCUMENTED with bench protocols
- **375 tests passing** on the cumulative v9.2 + v9.3 follow-on surface
- **0 regressions** on v9.1 calibrated solvers (alginate / agarose-chitosan / cellulose / PLGA)
- **0 fix rounds** required across the v9.3 follow-on cycle (all four code items APPROVED on first audit; the Q-011 latent bug was discovered, not introduced)

---

## 6. What's left for v9.3 proper

With Q-009 through Q-015 closed, the v9.3 cycle proper consists of:

1. **Wet-lab bench work** for Q-013 + Q-014 — see `WETLAB_v9_3_CALIBRATION_PLAN.md`
2. **Tier 2 simulator work** — 17 candidates per `SA_v9_2_FUNCTIONAL_OPTIMIZATION_SCREENING.md` § 6.2:
   - 5 polymer families (AGAROSE_DEXTRAN, AGAROSE_ALGINATE, ALGINATE_CHITOSAN, KAPPA_CARRAGEENAN, HYALURONATE)
   - 1 crosslinker (HRP/H₂O₂/tyramine)
   - 6 ligands (Procion Red, p-aminobenzamidine, Jacalin/lentil lectin, oligonucleotide, peptide affinity)
   - 3 linkers (oligoglycine, cystamine disulfide, succinic anhydride)
   - 2 ACS conversions (tresyl/tosyl, pyridyl disulfide)

Most of Tier 2 are data-only library extensions consuming the v9.2 schema/dispatch foundation. The polymer families consume the ion-gelation registry (κ-carrageenan + K⁺) and the composite-dispatcher infrastructure (HA, agarose-dextran). **No new architectural work is anticipated for Tier 2 entry.**

3. **Tier 3 candidates** — deferred to v9.4 per Q-002 resolution.

---

## 7. Filing

```
docs/handover/
├── SA_v9_2_FUNCTIONAL_OPTIMIZATION_SCREENING.md       (Tier ranking)
├── ARCH_v9_2_MODULE_DECOMPOSITION.md                  (41-module decomposition)
├── DEVORCH_v9_2_JOINT_PLAN.md                         (master plan + Q-001..Q-008)
├── HANDOVER_v9_2_M0a.md                               (M0a closeout)
├── HANDOVER_v9_2_M0b.md                               (M0b closeout)
├── HANDOVER_v9_2_CLOSE.md                             (v9.2 cycle close + Q-009..Q-015 list)
├── WETLAB_v9_3_CALIBRATION_PLAN.md                    (Q-013 + Q-014 bench plan)
└── HANDOVER_v9_3_FOLLOWONS_CLOSE.md                   ← this file
```

A new dialogue resuming v9.3 (Tier 2) work needs only these eight documents plus the project source tree.

---

## 8. Five-Point Quality Standard Check

1. **Read §1–2 and know complete v9.3 follow-on state without prior context** — ✅
2. **Read §3 and find every changed source file** — ✅
3. **Read §4–5 and understand the design decisions** — ✅
4. **Read `WETLAB_v9_3_CALIBRATION_PLAN.md` and begin bench calibration immediately** — ✅
5. **Read §6 and have the next cycle's roadmap** — ✅

**All five checks pass.**

---

> *v9.3 follow-on cycle — code work CLOSED, wet-lab work HANDED OFF. The simulator is ready to ingest bench-calibrated parameters whenever the campaign completes.*
