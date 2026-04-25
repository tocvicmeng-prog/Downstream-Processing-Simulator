# ADR-003 — POCl3 Tier-4 Rejection (do not implement)

**Status:** ACCEPTED
**Date:** 2026-04-25
**Cycle:** v9.4 (Tier-3 close)
**Decision authors:** /scientific-advisor + /dev-orchestrator + /architect
**Implements decisions:** SA screening report § 6.4 Tier-4; v9.2 joint plan D-008

---

## Context

The SA screening of 50 candidate crosslinkers placed phosphoryl
chloride (POCl3) in **Tier 4 — reject for default scope** in
`SA_v9_2_FUNCTIONAL_OPTIMIZATION_SCREENING.md` § 3 (crosslinker C7) and
§ 6.4 (Tier 4 ledger).

POCl3 is used industrially for **food-grade starch crosslinking** under
specific conditions. It produces phosphate diester crosslinks via
reaction with starch hydroxyls. The chemistry is real and well-
documented (PMC 8625705 — chemically-modified starch crosslinking
review).

## Decision

**POCl3 is NOT implemented in DPSim.** It will not be added as a
ReagentProfile, ion-gelant entry, or family-reagent matrix entry in
any v9.x release.

This ADR formally records the rejection so future contributors do not
re-introduce POCl3 without revisiting the rationale below. The v9.4
close cycle records this ADR explicitly per the v9.2 joint plan D-008.

## Rationale

### 1. Hazard outweighs value

- POCl3 reacts **violently with water**, producing HCl gas. Any
  exposure to atmospheric humidity during handling is a safety concern.
- Even within an inert-atmosphere setup, POCl3 is corrosive, lachrymatory,
  and presents a serious skin/respiratory hazard.
- These are not mitigatable in a typical bioprocess R&D lab setup
  without specialised infrastructure that DPSim users are not
  expected to have.

### 2. Bioprocess relevance is marginal

- POCl3 starch crosslinking is **food-grade chemistry** (modified
  starch in processed food, encapsulation matrices for non-pharma
  applications), not bioprocess chromatography.
- Two superior alternatives exist for starch hydroxyl phosphate
  crosslinking that are already in DPSim:
  - **STMP** (sodium trimetaphosphate) — much milder, food-grade,
    biotherapeutic-compatible (already a core v9.1 reagent).
  - **ECH** (epichlorohydrin) — broader applicability, modeled in v9.2
    as a Tier-1 reagent.

### 3. Default-scope scope-limit

DPSim's stated scope is **bioprocess downstream-processing simulation**.
Adding a reagent that is hazard-incompatible with typical bioprocess
labs and that has bioprocess-relevance "marginal" per SA's first-
principles assessment dilutes that scope.

## Consequences

### Positive

- DPSim maintains a clean default scope: every implemented reagent is
  reasonable to consider in a bioprocess R&D lab.
- Contributors who want POCl3 starch chemistry can use STMP as a
  drop-in substitute for the same phosphate-diester crosslinking
  outcome.

### Negative

- Users coming from food-science / starch-modification backgrounds
  may expect POCl3 as a default option and be surprised by its
  absence. The family selector preview surface in
  `visualization/tabs/m1/family_selector.py::_TIER2_PREVIEW_ROWS`
  documents the rejection so it's discoverable from the UI.

### Neutral

- This ADR does not preclude future re-evaluation. If a clear
  bioprocess use-case emerges (e.g., specialised starch matrix for a
  niche separation), POCl3 can be added then — but it must be added
  behind a documented hazard flag (analogous to `Al³⁺` with
  `biotherapeutic_safe=False`) and opt-in only.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Implement behind a hazard flag like Al³⁺ | The Al³⁺ flag is for residue regulatory concern (FDA/EP); the POCl3 issue is operational hazard at the point of use, which is qualitatively different. A flag does not mitigate the hazard. |
| Implement as a documentation-only profile (no kinetic constants) | Fails the standard ReagentProfile contract; would create a precedent for half-implemented profiles that is inconsistent with the closed-vocabulary discipline established in v9.2 (D-024). |
| Re-classify to Tier 3 with research-mode flag | The SA assessment was clear: hazard plus marginal value places this firmly in Tier 4, not Tier 3. Tier-3 candidates (Al³⁺, borax, glyoxal) all have demonstrably useful niches; POCl3 does not. |

## References

- `docs/handover/SA_v9_2_FUNCTIONAL_OPTIMIZATION_SCREENING.md` § 3 (C7)
  and § 6.4 (Tier 4 — REJECTED).
- `docs/handover/DEVORCH_v9_2_JOINT_PLAN.md` D-008 (planning-time
  rejection decision).
- PMC 8625705 — chemically-modified starch crosslinking review (lists
  POCl3, STMP, STPP, ECH as alternative phosphate routes; recognises
  STMP as the milder default).

---

> *POCl3 will not be added to DPSim. STMP and ECH cover the bioprocess-
> relevant subset of phosphate-crosslinking chemistry without the hazard
> profile.*
