# Milestone Handover: M-PLAN-v9.2 — Functional-Optimization Joint Plan

**Date:** 2026-04-25
**Session:** v9.2-PLAN-001 (initial)
**Project:** Downstream-Processing-Simulator (DPSim) v9.2
**Prepared by:** /dev-orchestrator (with /architect technical decomposition; based on /scientific-advisor screening report)
**Classification:** Internal — Development Handover

**Companion documents (must accompany this plan):**
- `SA_v9_2_FUNCTIONAL_OPTIMIZATION_SCREENING.md` — scientific candidate screening (Tiers 1–4, dependency graph, batch design)
- `ARCH_v9_2_MODULE_DECOMPOSITION.md` — module-level decomposition, dependency DAG, model-tier rationale, and acceptance-test plan

---

## 1. Executive Summary

The Scientific Advisor's screening of 50 candidate polysaccharide materials, crosslinkers, ligands, linkers, and ACS-conversion molecules placed **18 items in Tier 1** for v9.2 integration, **17 in Tier 2** for v9.3, **11 in Tier 3** (deferred / feature-flagged), and **1 in Tier 4** (rejected — POCl₃, hazard outweighs value).

The Architect decomposed the Tier-1 plan into **41 implementation modules** spanning **5 architectural prerequisites (A1–A5)** and **9 workflow milestones (M1–M9)** mapped to the SA's batch design B1–B12 (B6, B11, B12 fold into the architectural foundation M0). The dependency DAG identifies M0 as the critical-path foundation; M1–M9 are mutually independent given M0 and may be sequenced by risk weight.

The Dev-Orchestrator selects model tiers per Reference 02 (7 Opus, 22 Sonnet, 12 Haiku assignments — projected ~50% token savings vs. all-Opus baseline; lower than the typical 55–65% because Tier 1 is foundation-heavy), enforces the 12-point G1 / 10-point G2 / 6-dimension G3 quality gates, and budgets a milestone-handover after every milestone close (more frequent than default to guard against state loss across the breadth of new chemistry).

**Where we are now:** plan finalized; no code modules implemented yet; this is the planning-phase handover that authorizes the v9.2 implementation cycle to begin.

**What's next:** Execute Milestone 0 (architectural foundation) starting with module A1.1 (`acs_enum_extension`) per the build order in §6. Pre-flight check at the start of M0 confirms model tier, context budget, and milestone proximity.

---

## 2. Module Registry — Initial State (v9.2 cycle)

No modules approved yet. The full proposed registry of 41 modules is documented in `ARCH_v9_2_MODULE_DECOMPOSITION.md` §2–3. Status of every module: **PENDING**. The registry will be updated to APPROVED status as each module clears Phase 5 (Reference 01 §7).

| # | Module | Version | Status | Approved | Model Used | Fix Rounds | Lines | File Path |
|---|---|---|---|---|---|---|---|---|
| — | — | — | PENDING | — | — | — | — | — |

(Empty initial state — registry table format is Reference 04 §3.)

---

## 3. Integration Status — Initial State

| Interface | From Module | To Module | Status | Notes |
|---|---|---|---|---|
| `ACSSiteType` (current) | `acs.py` | `reagent_profiles.py`, `reactions.py` | **LIVE** | 13 site types from v9.1; no changes yet |
| `ACSSiteType` (extended) | `acs.py` | `reagent_profiles.py`, `reactions.py` | PENDING | Lands with A1.1 |
| `PolymerFamily` (current 4) | `datatypes.py` | level2_gelation, M2 family-reagent matrix, UI selector | **LIVE** | v9.1 |
| `PolymerFamily` (extended) | `datatypes.py` | same | PENDING | Lands with A2.1 |
| `IonGelantProfile` | `level2_gelation/ion_registry.py` (new) | `level2_gelation/alginate.py` (refactored) | PENDING | Lands with A3.1 → A3.3 |
| `functional_mode` (extended) | `reagent_profiles.py` | M2 orchestrator | PENDING | Lands with A4.1 |
| `chemistry_class` (extended) | `reactions.py` | reaction-engine dispatch | PENDING | Lands with A5.1 |

---

## 4. Architecture State

The v9.1 architecture is the baseline. The v9.2 cycle introduces **schema-additive** changes (new enum members, new fields with safe defaults, new dataclasses) and **one structural refactor** (A2 PolymerFamily expansion + A3 ion-gelation registry). No interfaces are removed; all v9.1 functionality is preserved by golden-master regression tests.

Architectural changes since the v9.1.x baseline:
- **None at this point** — this is the planning handover. Architecture changes begin landing with M0 module A1.1.

Architectural changes scheduled by this plan are catalogued in `ARCH_v9_2_MODULE_DECOMPOSITION.md` §2.

---

## 5. Design Decisions Log

| # | Decision | Rationale | Date | Alternatives Considered |
|---|---|---|---|---|
| D-001 | Adopt SA-recommended Tier 1 / Tier 2 / Tier 3 / Tier 4 split | Tier weighting balances bioprocess relevance vs. architectural cost; Tier 4 (POCl₃) rejected for hazard/value mismatch | 2026-04-25 | All-in-one v9.2 cycle (rejected — too large for context budget) |
| D-002 | Bundle architectural prerequisites A1–A5 into Milestone 0 ahead of any candidate module | Avoid piecemeal enum migrations; new candidate modules consume already-stable schema | 2026-04-25 | Per-batch enum extension (rejected — fragmentation risk) |
| D-003 | Use `is_enabled_in_ui` flag on `PolymerFamily` for staged rollout | Preserve v9.0 Family-First UI contract; Tier-2 families can land as data without UI surface | 2026-04-25 | Hard-gating new families behind a feature flag (rejected — too coarse) |
| D-004 | Per-polymer ion-gelation registry replaces alginate Ca²⁺ hardcoding | Unlocks Tier-2 ionic materials; clean abstraction | 2026-04-25 | Adding KCl/CaSO₄ as alginate-only special cases (rejected — debt) |
| D-005 | Material-as-ligand pattern via `material_as_ligand: bool = False` flag on PolymerFamily meta | Non-breaking; existing solvers ignore the flag | 2026-04-25 | Separate `AffinityMatrix` class (rejected — duplication) |
| D-006 | Milestone handover after every milestone close (10 handovers across v9.2) | Breadth of new chemistry makes mid-session state loss expensive to reconstruct | 2026-04-25 | Default cadence (every 3+ approved modules) — rejected as insufficient |
| D-007 | Acceptance test per milestone is a published reference protocol (literature-anchored) | Per SA recommendation §8.3; raises the bar above unit tests | 2026-04-25 | Internal regression tests only (rejected — no external benchmark) |
| D-008 | Tier 4 rejection of POCl₃ documented as ADR before any code lands | Prevent re-introduction; scientific rationale recorded | 2026-04-25 | Implement behind hazard flag (rejected — bioprocess scope incompatibility) |
| D-009 | Cu-residue accounting flag on CuAAC reagent profile (B7.1) | ICH Q3D residual-element compliance for biotherapeutic pipelines | 2026-04-25 | Skip Cu accounting (rejected — bioprocess fitness gap) |

---

## 6. Build Order and Milestones

### 6.1 Milestone-level sequence

| Milestone | Title | Modules | Dependencies | Token est. | Recommended order rationale |
|---|---|---|---|---|---|
| **M0** | Architectural Foundation (A1–A5 + B6, B11, B12) | 19 | — | ~50 k | Critical path; everything else depends on M0 |
| **M1** | Classical Affinity Resin Completion (B1) | 4 | M0 | ~6 k | Stabilize activation/coupling layer first |
| **M2** | Oriented Glycoprotein Immobilization (B2) | 4 | M0 | ~12 k | Validates the periodate–ADH–aminooxy bioorthogonal chain |
| **M5** | Bis-Epoxide Hardening (B5) | 2 | — (independent of M0 ACS work) | ~6 k | Cheap, independent — can interleave anywhere |
| **M3** | Dye Pseudo-Affinity (B3) | 3 | M0 | ~7 k | Validates new functional_mode + triazine path |
| **M4** | Mixed-Mode Antibody Capture (B4) | 2 | M0 | ~9 k | Validates new functional_mode (HCIC) |
| **M6** | Click Chemistry Handle (B7) | 3 | M0 | ~10 k | Modular framework for future plug-ins |
| **M7** | Multipoint Enzyme Immobilization (B8) | 2 | M0 | ~12 k | Highest scientific complexity; sequence after lower-risk wins |
| **M8** | Material-as-Ligand (B9) | 3 | M0 | ~7 k | Pattern that enables Tier-2 chitin-CBD |
| **M9** | Boronate Affinity (B10) | 2 | M0 | ~7 k | Closes the new-functional_mode list |

**Total token estimate (v9.2 cycle):** ~126 k tokens of in-cycle work + ~30 k of milestone-handover overhead = ~156 k. Across at minimum 6 sessions (M0 alone is one session; M1–M9 cluster into ~5 sessions).

### 6.2 Within-milestone build order

For each milestone, follow the per-module sequence in `ARCH_v9_2_MODULE_DECOMPOSITION.md` §3, respecting the dependency edges. Within M0, the recommended sequence is:

```
A1.1 (ACS enum) ──> A1.2 (conservation tests) ──> A1.3 (init dispatch)
A2.1 (PolymerFamily enum) ──> A2.2 (agarose-only solver, Opus)
                            └─> A2.3 (chitosan-only solver)
                            └─> A2.4 (dextran-ECH solver)
                                └─> A2.5 (composite refactor) ──> A2.6 (UI) + A2.7 (matrix)
A3.1 (IonGelantProfile) ──> A3.2 (registry) ──> A3.3 (alginate refactor, Opus)
                                              ├─> A3.4 (CaSO4)
                                              ├─> A3.5 (KCl)
                                              └─> A3.6 (regression suite)
A4.1 (functional_mode) ──> A4.2 (dispatch)
A5.1 (chemistry_class) ──> A5.2 (reaction-engine dispatch)
```

A1.x, A2.x, A3.x are the three independent sub-trees within M0; A4.x and A5.x are independent of all three. A milestone-level pre-flight at M0 start should verify ≥ 60% context (full cycle estimated at 50 k tokens).

---

## 7. Quality-Gate Enforcement

Per Reference 01 §9, every module must pass three gates:

### 7.1 Phase 0 — Pre-Flight Checklist (per module)

- [ ] Context budget ≥ 30% estimated remaining after this module's full inner-loop completion
- [ ] All upstream dependencies APPROVED (per the DAG in `ARCH_v9_2_MODULE_DECOMPOSITION.md` §4)
- [ ] Model tier selected per Reference 02 §3 and recorded in registry
- [ ] If module closes a milestone: handover budget ≥ 6 k tokens pre-allocated

### 7.2 Phase 1 — Protocol G1 (12-point check)

The Architect generates a Protocol document per module before any code is written. G1-01 through G1-12 (Reference 01 §3) must all pass. Special attention for v9.2:

- **G1-06 numerical considerations**: chemistry-class kinetic forms must explicitly state pH dependence, hydrolysis competition, and reversibility regime. Periodate, hydrazone, oxime, and CuAAC all have non-trivial regimes.
- **G1-07 unit tests**: at least one test per module must cite a 1° literature value (the source of the kinetic constant).
- **G1-11 interface versions**: the orchestrator pins ACSSiteType to a versioned schema (v9.1 = 13 sites, v9.2 = 25 sites). All new modules declare which schema version they consume.

### 7.3 Phase 2 — Implementation G2 (10-point check)

Reference 01 §4 G2-01 through G2-10. Project-specific additions per CLAUDE.md:

- All new code must pass `ruff` (cap = 0) and `mypy` (cap = 0) gates.
- Streamlit-touching modules must use `.value` for enum comparison, never `is`.
- Any module that prints `Path` objects must `sys.stdout.reconfigure(encoding="utf-8")` first (cp1252 pitfall).

### 7.4 Phase 3 — Audit G3 (six-dimension)

Reference 01 §5 D1–D6 plus G3-01 through G3-08. Project-specific audit emphases:

- **D2 algorithmic**: every new chemistry-class kinetic law cites at least one peer-reviewed source.
- **D6 first-principles**: any module producing predictions outside literature-reported ranges must escalate to /scientific-advisor (Reference 06).
- **D4 performance**: existing M2 reaction wall-time must not regress more than 10% (existing v9.1 calibrated baseline is the reference).

### 7.5 Milestone-level acceptance

A milestone is closed when **all of**:
1. Every module in the milestone is APPROVED in the registry (registry status = APPROVED)
2. The milestone's reference-protocol acceptance test (per `ARCH_v9_2_MODULE_DECOMPOSITION.md` §5) passes within the documented quantitative tolerance
3. Existing v9.1 regression suite passes unchanged (`pytest -q`)
4. CI gates pass (ruff = 0, mypy = 0)
5. Milestone handover document produced (Reference 04 template)

---

## 8. Model-Tier Selection Policy (consolidated)

Per Reference 02 §2, Reference 02 §3 decision tree, and the per-module assignments in `ARCH_v9_2_MODULE_DECOMPOSITION.md` §6:

| Always Opus (non-negotiable) | Sonnet default | Haiku default |
|---|---|---|
| Architecture design (A2.2, A3.3 refactors) | Standard module implementation (50–200 LOC) | Boilerplate (config, enum extension, parameter blocks) |
| Full six-dimension audit (every Phase 3) | Routine audit (after non-algorithmic fix) | Cosmetic re-audit |
| Milestone handover (every M0–M9 boundary) | Numerical/scientific test writing | Simple-assertion tests, doc polish |
| Novel-algorithm protocol (B4.2 MEP-HCIC, B7.1 CuAAC, B8.x glyoxyl + multipoint) | Standard protocol generation | — |

**Aggregate v9.2 tier counts (per `ARCH_v9_2_MODULE_DECOMPOSITION.md` §6):** 7 Opus implementation modules, 22 Sonnet modules, 12 Haiku modules. Plus 41 audits @ Opus, 10 milestone handovers @ Opus, ~2 fix-cycle re-audits per Opus module (estimated 14 re-audits → 14 × Sonnet given non-algorithmic fixes).

**Upgrade triggers** to be enforced per Reference 02 §6:
- If audit returns >3 HIGH severity findings → upgrade implementation tier on the next similar module
- If a module requires >2 fix rounds → flag for tier review and consider Opus on next similar module
- If scientific equation is discovered mid-implementation that was not in the protocol → upgrade immediately

**Downgrade triggers:**
- Module simpler than initially assessed → downgrade only if the next module in the same family has the same simpler structure
- Re-audit after cosmetic fix → Haiku
- Documentation-only updates → Haiku

**Tracking:** the orchestrator updates the Module Registry's `Model Used` and `Fix Rounds` columns at every Phase 5 close; if `Upgrade Needed` appears for >20% of modules, complexity heuristics need recalibration before the next milestone starts.

---

## 9. Dialogue Compression and Context-Budget Policy

Per Reference 03:

### 9.1 Per-session budget zones

The orchestrator tracks budget after every phase close per the running-estimate template in Reference 03 §5. Compression is triggered when the next planned phase would push the dialogue from YELLOW into RED.

### 9.2 Pre-large-work compression rule for v9.2

Modules with estimated full-loop token cost >10 k:
- A2.2 `agarose_only_solver` (Opus + 220 LOC + golden-master test ~ 12 k)
- A3.3 `alginate_solver_via_registry` (Opus + 180 LOC + regression test ~ 11 k)
- B2.4 `oriented_glycoprotein_workflow_test` (Opus + 180 LOC + cross-module integration ~ 14 k)
- B4.2 `mep_hcic_profile` (Opus + 200 LOC + novel science ~ 13 k)
- B7.1 `cuaac_handle_profile` (Opus + 180 LOC + novel chemistry + Cu accounting ~ 13 k)
- B8.1 `glyoxyl_chained_activation` (Opus + 200 LOC ~ 12 k)
- B8.2 `multipoint_enzyme_stability_model` (Opus + 180 LOC + novel science ~ 13 k)

Before each of these modules: compress dialogue if context < YELLOW.

### 9.3 Mandatory milestone-handover compression

At the close of every milestone, a milestone handover (Reference 04 template) is produced. This is a hard rule for v9.2 (D-006 above) — more frequent than the default cadence.

### 9.4 Emergency-handover threshold

If the dialogue reaches EMERGENCY (<15%) mid-implementation, produce the abbreviated emergency handover per Reference 03 §6 / Reference 04 §5 immediately and end the session. Resume in a new dialogue with the emergency handover plus the Module Registry plus this plan as context.

---

## 10. IP and Constraint Notes

| Constraint | Source | Affects |
|---|---|---|
| ICH Q3D residual-element limits | Regulatory standard | B7.1 CuAAC Cu-residue accounting |
| ICH Q3C residual-solvent limits | Regulatory standard | All organic-solvent activation reagents (CDI in DMF, tresyl in dioxane) — flag in profile metadata |
| FDA/EP aluminum limits in biotherapeutics | Regulatory | Tier-3 C6 Al³⁺ gelant — non-biotherapeutic flag must be enforced |
| CNBr hazard (HCN release) | OSHA / lab safety | B1.2 must carry a hazard_class string and surface the hazard in M2 process dossier |
| POCl₃ hazard | OSHA | C7 rejected (Tier 4) — ADR must record |
| No proprietary/closed datasets | Project policy | All reference-protocol acceptance tests use peer-reviewed open literature; no Cytiva/Pall data lifted from confidential sources beyond cited application notes |

No new IP issues identified at planning phase.

---

## 11. Open Questions / Unresolved Issues — RESOLVED 2026-04-25

| # | Question | Resolution |
|---|---|---|
| Q-001 | PEGDGE/EGDGE/BDDE: single parameterized profile vs. three discrete? | **Single parameterized profile** (one `ReagentProfile` with `spacer_length_angstrom` parameter). Per /project-director 2026-04-25. |
| Q-002 | Tier-3: data-only in v9.2 or defer to v9.4? | **Defer to v9.4.** v9.2 cycle scope strictly Tier 1; v9.3 covers Tier 2; Tier 3 not loaded into the data tree until v9.4. Per /project-director 2026-04-25. |
| Q-003 | Acceptance-test ±20% fallback band. | **Confirmed acceptable.** Per /project-director 2026-04-25. |
| Q-004 | Split M0 into M0a (schema) + M0b (refactor)? | **Split confirmed.** See §6.0 (new). Per /project-director 2026-04-25. |
| Q-005 | `.value`-comparison enforcement: custom ruff rule? | **Custom ruff rule.** To be added to project ruff config under `dpsim.streamlit_safe_enum_comparison` (or similar). Per /project-director 2026-04-25. |

## 6.0 Milestone-0 split (per Q-004 resolution)

| Milestone | Title | Modules | Token est. | Acceptance |
|---|---|---|---|---|
| **M0a** | Architectural foundation — schema-additive | A1.1, A1.2, A1.3, A4.1, A4.2, A5.1, A5.2, A2.1, A2.7, A3.1, A3.2, A3.4, A3.5 | ~25 k | Existing v9.1 regression suite passes unchanged; new ACS conservation invariants pass for all 25 site types; ALLOWED_FUNCTIONAL_MODES / ALLOWED_CHEMISTRY_CLASSES validators reject unknown values |
| **M0b** | Architectural foundation — refactors with golden masters | A2.2, A2.3, A2.4, A2.5, A2.6, A3.3, A3.6 | ~25 k | Golden-master regression: agarose-chitosan composite reproduces v9.1 outputs to ≤ 1e-6 relative tolerance; alginate-via-registry reproduces v9.1 outputs to ≤ 1e-6 relative tolerance |

The M0a → M0b boundary is a hard milestone-handover point (Reference 04). M0a lands schema additions that are **safe by construction** (additive enum members, additive constant sets, additive enum values gated by `is_enabled_in_ui`); M0b lands the **refactors with regression risk** (A2.2 agarose-only solver, A3.3 alginate solver via registry). Splitting at this boundary keeps the dialogue's high-risk Opus modules in a fresh-context session.

---

## 12. Next Module Protocol — A1.1 `acs_enum_extension`

Per Reference 04 §3 Section 9, the next module's protocol is pre-generated so a fresh dialogue can begin implementation immediately.

### Purpose
Add 12 new `ACSSiteType` enum members in `src/dpsim/module2_functionalization/acs.py` to expand the simulator's chemistry coverage to 25 site types in support of v9.2 Tier-1 candidates.

### Interface specification

**Input:** None (this is a schema-additive change).

**Output (added to existing enum):**

| Enum member | String value | Purpose |
|---|---|---|
| `SULFATE_ESTER` | `"sulfate_ester"` | Sulfate-ester groups on κ-/ι-carrageenan; supports Tier-2 carrageenan family |
| `THIOL` | `"thiol"` | Free –SH groups (cysteine residues, post-reduction supports) |
| `PHENOL_TYRAMINE` | `"phenol_tyramine"` | Phenolic side group for HRP-radical coupling |
| `AZIDE` | `"azide"` | Azide handle for CuAAC/SPAAC click chemistry |
| `ALKYNE` | `"alkyne"` | Terminal alkyne handle for CuAAC |
| `AMINOOXY` | `"aminooxy"` | –ONH₂ for oxime ligation with aldehydes/ketones |
| `CIS_DIOL` | `"cis_diol"` | Target chemistry for boronate-affinity ligands |
| `TRIAZINE_REACTIVE` | `"triazine_reactive"` | Cyanuric-chloride-derived activated support |
| `GLYOXYL` | `"glyoxyl"` | Aldehyde-bearing support after glycidol→periodate sequence |
| `CYANATE_ESTER` | `"cyanate_ester"` | CNBr-activated agarose intermediate |
| `IMIDAZOLYL_CARBONATE` | `"imidazolyl_carbonate"` | CDI-activated support |
| `SULFONATE_LEAVING` | `"sulfonate_leaving"` | Tresyl/tosyl-activated support |

### Algorithm
N/A — pure enum extension.

### Test cases
- T-A1.1-01: All 12 new enum members are accessible by name and produce the expected `.value` strings.
- T-A1.1-02: `len(ACSSiteType)` equals 25 (13 v9.1 + 12 new).
- T-A1.1-03: All members appear in serialization round-trips (JSON via `.value`).
- T-A1.1-04: No collision with existing enum values.

### Performance budget
N/A — schema-only change.

### Dependencies
- Upstream: none.
- Downstream: A1.2 (conservation tests must extend), A1.3 (initialization dispatch), every Tier-1 reagent profile module.

### Logging
N/A.

### Model selection
- Tier: **Haiku** (Tier 3 — boilerplate)
- Rationale: pure enum extension with existing pattern; <50 LOC; no algorithm or domain logic
- Complexity: LOW — list of identifiers + docstrings

### Estimated tokens
~1.5 k for protocol + 0.5 k for implementation + 1 k for tests + 0.8 k for audit + 0.5 k for handoff = **~4.3 k total**.

---

## 13. Context Compression Summary

This is the planning-phase handover; no implementation context to compress yet.

**Carry forward verbatim:**
- The Module Registry initial state (§2)
- The DAG and build order (`ARCH_v9_2_MODULE_DECOMPOSITION.md` §4 + §6 of this doc)
- The model-tier policy (§8)
- The pre-large-work compression list (§9.2)
- The next-module protocol (§12)

**Compressed (one-line summaries):**
- Scientific-Advisor screening rationale (full report at `SA_v9_2_FUNCTIONAL_OPTIMIZATION_SCREENING.md`).
- Per-module file paths and complexity (full table at `ARCH_v9_2_MODULE_DECOMPOSITION.md` §2–3).
- Per-milestone reference protocols and acceptance criteria (full table at `ARCH_v9_2_MODULE_DECOMPOSITION.md` §5).

**Dropped:** None (this is the initial handover; nothing to drop).

---

## 14. Model Selection History

| Task | Model Used | Tokens (est.) | Outcome |
|---|---|---|---|
| Scientific Advisor screening (Mode 2) | Opus | ~25 k | Produced SA report; 50 candidates → 4 tiers |
| Architect module decomposition | Opus | ~22 k | Produced 41-module decomposition |
| Dev-Orchestrator joint plan assembly | Opus | ~18 k | This document |

**Total tokens this session:** ~65 k
**Token savings vs. all-Opus baseline:** 0% (all planning tasks per Reference 02 are Opus-mandated). Savings begin at module-implementation phase.

---

## 15. Roadmap Position

- **Current milestone:** Pre-M0 (planning complete)
- **Modules completed:** 0 of 41 (Tier 1)
- **Estimated remaining effort:** 41 modules across ~6 sessions; roughly 4–6 weeks at one session per ≈3 days
- **Tier 2 (v9.3) follow-on:** ~17 candidate items + ~5 enabling modules ≈ 22 modules; target 1 quarter after v9.2 close
- **Tier 3 (v9.4 or feature-flagged):** ~11 items; data-only library extensions; minimal architectural cost once v9.2 lands
- **Tier 4 rejection:** POCl₃ — ADR to be recorded on first commit of v9.2 cycle

### Process observations (retrospective)

This is the first planning-phase handover, so no prior session retrospective applies. Two observations going forward:

1. **The architect's plan-level audit (Reference 05 D1–D6 against the plan itself, in `ARCH_v9_2_MODULE_DECOMPOSITION.md` §7)** flagged HIGH risks in D1 (UI rendering matrix), D2 (alginate regression invariant), D3 (ACS conservation accounting), and D6 (chemistry-class kinetic-law correctness). All four are gated by explicit tests in this plan. The orchestrator should not allow any of these gates to be bypassed even if the schedule pressures it.

2. **The model-tier mix (7 Opus implementation modules)** is heavier than the Reference 02 §5 reference projection. This is a feature, not a bug — v9.2 is foundation-heavy. Token savings will compound in v9.3 when most modules are Sonnet/Haiku data-only library extensions on top of the v9.2 foundation.

---

## 16. Five-Point Quality Standard Check (Reference 04 §4)

A new dialogue can:

1. **Read §1–3 and know the complete project state without any prior context** — ✅ §1 executive summary; §2 module registry initial state; §3 integration status.
2. **Read §4 and locate every approved source file** — ✅ §4 architecture-state ref to `ARCH_v9_2_MODULE_DECOMPOSITION.md` §2–3 with explicit file paths per module.
3. **Read §5–10 and understand all architectural and design decisions** — ✅ §5 design decisions log (D-001 through D-009); §10 IP/constraint notes.
4. **Read §12 and begin implementing the next module immediately** — ✅ §12 contains full A1.1 protocol satisfying G1-01 through G1-12.
5. **Read §13 and have the full compressed history of the project** — ✅ §13 compression summary; companion documents named for context expansion.

**All five checks pass. Handover is ready.**

---

## 17. Filing

This document, the SA report, and the Architect decomposition are saved to:

```
docs/handover/
├── SA_v9_2_FUNCTIONAL_OPTIMIZATION_SCREENING.md
├── ARCH_v9_2_MODULE_DECOMPOSITION.md
└── DEVORCH_v9_2_JOINT_PLAN.md  ← this file
```

The trio is self-contained. A new dialogue resuming v9.2 development needs only these three documents plus the project source tree.

---

> *This handover is self-contained. A new dialogue can resume development using only this document plus the SA screening report and the Architect decomposition document.*
