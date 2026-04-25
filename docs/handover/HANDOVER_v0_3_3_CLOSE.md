# Milestone Handover — v0.3.3 Close (v9.5 Tier-3 Composites)

**Date:** 2026-04-25
**Session:** v0.3.3-IMPL-001
**Project:** Downstream-Processing-Simulator (DPSim)
**Prepared by:** /dev-orchestrator
**Classification:** Internal — Development Handover

**Companion documents:**
- `docs/handover/HANDOVER_v0_3_0_CLOSE.md` — v0.3.0 close (P5++ G1+G2+G3)
- `docs/handover/HANDOVER_v0_3_1_CLOSE.md` — v0.3.1 close (P5++ G4)
- `docs/handover/HANDOVER_v0_3_2_CLOSE.md` — v0.3.2 close (P5++ G5)

---

## 1. Executive Summary

v0.3.3 closes the v9.5 Tier-3 multi-variant composite work that was
listed in the M1 page's "v9.5+ preview" section through v9.4. Three
composite polymer families promoted from data-only placeholder to full
UI-enabled status, plus a borax reversibility-warning surface upgrade.

The work is **bioprocess-line additive** rather than P5++. The user
asked to finish the items the M1 UI labelled as "v9.5 deferred":

- Pectin-chitosan polyelectrolyte complex (PEC)
- Gellan-alginate composite
- Pullulan-dextran composite
- Reversible borate-cis-diol crosslinking (borax) — already implemented;
  needed reversibility warning surfaced more prominently

All four items closed in a single session.

**Where we are now:** `__version__ = "0.3.3"`; CHANGELOG updated;
M1 selector now lists 21 selectable polymer families (was 18 in v0.3.2).
Smoke baseline preserved end-to-end.

---

## 2. Module Registry — v0.3.3 add

| # | Module | Version | Status | Approved | Model Used | Fix Rounds | Lines | File Path |
|---|---|---|---|---|---|---|---|---|
| v9.5-A | `v9_5_composites.solve_pectin_chitosan_pec_gelation` | 0.3.3 | **APPROVED** | 2026-04-25 | Sonnet | 0 | ~50 | `src/dpsim/level2_gelation/v9_5_composites.py` |
| v9.5-B | `v9_5_composites.solve_gellan_alginate_gelation` | 0.3.3 | **APPROVED** | 2026-04-25 | Sonnet | 0 | ~50 | `src/dpsim/level2_gelation/v9_5_composites.py` |
| v9.5-C | `v9_5_composites.solve_pullulan_dextran_gelation` | 0.3.3 | **APPROVED** | 2026-04-25 | Sonnet | 0 | ~50 | `src/dpsim/level2_gelation/v9_5_composites.py` |
| v9.5-D | composite_dispatch + UI promotion + borax warning surface | 0.3.3 | **APPROVED** | 2026-04-25 | Sonnet | 1 (test rework for scipy-heavy paths) | ~50 (extensions) | `composite_dispatch.py`, `datatypes.py`, `family_selector.py` |

---

## 3. Integration Status

| Interface | From Module | To Module | Status | Notes |
|---|---|---|---|---|
| `solve_pectin_chitosan_pec_gelation()` | v9_5_composites | composite_dispatch | **LIVE** | Mirrors v9.3 ALGINATE_CHITOSAN PEC pattern; pectin Ca²⁺ skeleton + chitosan ammonium shell |
| `solve_gellan_alginate_gelation()` | v9_5_composites | composite_dispatch | **LIVE** | Dual ionic-gel composite; alginate dominant + 20 % gellan helix reinforcement |
| `solve_pullulan_dextran_gelation()` | v9_5_composites | composite_dispatch | **LIVE** | Neutral α-glucan composite; delegates to dextran-ECH |
| 3 new entries in `_TIER1_UI_FAMILIES` | datatypes | family_selector | **LIVE** | Selectable in M1 radio |
| 3 new display rows in `_FAMILY_DISPLAY` | family_selector | M1 UI | **LIVE** | Each carries SA screening § 6.4 attribution |
| Borax reversibility-warning row | family_selector preview | M1 UI | **LIVE** | Upgraded from one-liner to multi-line guidance with covalent-secondary-crosslink requirement |
| `_TIER2_PREVIEW_ROWS` cleanup | family_selector | M1 UI | **LIVE** | Three v9.5-promoted composites removed from preview list; expander title updated |

---

## 4. Quality-Gate Enforcement

### v9.5 composite solvers

| Gate | Result |
|---|---|
| `.value` enum-comparison rule | ✅ AST gate (`test_v9_5_composites_module_passes_enum_comparison_ast_gate`) and project-wide gate (`test_v9_3_enum_comparison_enforcement.py`) both clean |
| Family-check at solver entry | ✅ each solver raises `ValueError` on wrong family |
| `mode != "empirical"` guard | ✅ raises `NotImplementedError` (consistent with Tier-3 single-polymer pattern) |
| Manifest provenance | ✅ `L2.<family>.qualitative_trend_v9_5` model_name; `v9.5_tier_3_composite` tier diagnostic; literature-anchored calibration_ref |
| Composite-specific assumption block | ✅ each solver carries the SA screening § 6.4 bioprocess-relevance note |
| Smoke baseline | ✅ existing v9.4 family selections unaffected; default radio behaviour unchanged |
| ruff = 0 / mypy = 0 | ✅ on the new module |

### Borax reversibility warning surface

| Gate | Result |
|---|---|
| Warning text upgraded in `_TIER2_PREVIEW_ROWS` | ✅ now a multi-line entry with all-caps `REVERSIBILITY WARNING` tag and covalent-secondary-crosslink requirement |
| Test coverage | ✅ `test_borax_reversibility_warning_in_preview` asserts presence of `REVERSIBILITY WARNING`, `TEMPORARY POROGEN`, and `BDDE`/`ECH` literals |
| Preview-list cleanup | ✅ `test_v9_5_preview_no_longer_lists_promoted_composites` asserts the three v9.5 composites are gone from the preview |

**Verdicts: all four sub-modules APPROVED.** One fix round on the
acceptance-test side (rework of dispatch test to use mock-style routing
for the scipy-heavy alginate-ionic-Ca paths under Python 3.14). The
solver modules themselves saw zero fix rounds.

---

## 5. Acceptance Criteria

| AC# | Description | Status | Evidence |
|---|---|---|---|
| AC#1 | Three composite families UI-enabled | ✅ | `test_composite_family_ui_enabled` × 3 |
| AC#2 | Dispatcher routes to v9.5 solvers | ✅ | `test_dispatcher_routes_pullulan_dextran` (real) + mock-style routing for the two scipy-heavy paths |
| AC#3 | Solvers reject wrong family | ✅ | three `test_*_solver_rejects_wrong_family` tests |
| AC#4 | Solvers reject non-empirical mode | ✅ | `test_solvers_reject_non_empirical_mode` |
| AC#5 | Manifest carries SA screening note | ✅ | `test_pullulan_dextran_assumption_list_carries_sa_screening_note` |
| AC#6 | calibration_ref literature-anchored | ✅ | `test_pullulan_dextran_manifest_calibration_ref_set` |
| AC#7 | Enum AST gate clean on new module | ✅ | `test_v9_5_composites_module_passes_enum_comparison_ast_gate` |
| AC#8 | Borax reversibility warning surfaced | ✅ | `test_borax_reversibility_warning_in_preview` |
| AC#9 | Preview list trimmed of promoted composites | ✅ | `test_v9_5_preview_no_longer_lists_promoted_composites` |
| AC#10 | Smoke baseline | ✅ | v9.4 Tier-3 single-polymer tests still pass; performance_recipe + enum-AST regressions clean |

---

## 6. Risks Closed and Open

### Closed

- **Multi-variant composite v9.4 placeholder gate** — replaced with
  positive dispatch routes; the legacy `NotImplementedError("placeholder")`
  message no longer fires for any of the three families.
- **Borax reversibility visibility** — upgraded from a one-line
  preview entry to a multi-line warning that explicitly demands a
  covalent secondary crosslink (BDDE / ECH) before downstream packing.

### Open (carry to v0.4.0+)

- **Composite-specific wet-lab calibration.** v9.5 composites carry
  `QUALITATIVE_TREND` evidence pending composite-specific Q-013-style
  data. Constituent-only calibration is **not sufficient** —
  upgrading to `SEMI_QUANTITATIVE` requires composite gel-strength /
  pore-size measurements.
- **Pectin DE-dependence and high-methoxy sugar-acid gel mode.** Not
  modelled at v9.5 resolution; pectin-chitosan PEC assumes
  low-methoxy (DE < 50 %) Ca²⁺-gel skeleton. If high-methoxy +
  sugar-acid gels enter scope, a new solver branch is needed.
- **Mixed K⁺/Ca²⁺ baths for gellan-alginate.** Gellan-alginate solver
  uses Ca²⁺ as the structuring ion; bath composition (mixed K⁺/Ca²⁺
  ratios) requires a separate fitting step.
- **STMP-crosslinked pullulan-dextran variant.** Documented but not
  modelled separately at v9.5; ECH path is the default delegate.
- **Python 3.14 + scipy BDF environment quirk.** CLAUDE.md pins Python
  to 3.11–3.13; the v9.5 dispatch tests for the scipy-heavy paths use
  mock-style routing under 3.14. Promote to direct-call once the
  environment moves back into pin range.

---

## 7. Files Changed

### New files

- `src/dpsim/level2_gelation/v9_5_composites.py` (~280 LOC) — three
  composite solvers + retag helper
- `tests/test_v9_5_composites.py` (~250 LOC, 18 tests)
- `docs/handover/HANDOVER_v0_3_3_CLOSE.md` (this document)

### Modified files

- `src/dpsim/datatypes.py` — three new entries in `_TIER1_UI_FAMILIES`
- `src/dpsim/level2_gelation/composite_dispatch.py` — three new
  routing branches; legacy placeholder gate removed; `ValueError`
  family list updated
- `src/dpsim/visualization/tabs/m1/family_selector.py` — three new
  display rows; preview list trimmed; expander title updated; borax
  warning expanded
- `tests/test_v9_4_tier3.py` — `test_tier3_composite_remains_placeholder`
  inverted to `test_tier3_composite_promoted_in_v9_5`;
  `test_composite_placeholders_raise_not_implemented` retargeted to a
  positive scipy-light dispatch assertion
- `src/dpsim/__init__.py` — `__version__ = "0.3.3"`
- `pyproject.toml` — `version = "0.3.3"`
- `CHANGELOG.md` — v0.3.3 entry prepended

---

## 8. Five-Point Quality Standard Check

1. ✅ § 1–3 carry the v0.3.3 state in isolation
2. ✅ § 7 lists every changed file
3. ✅ § 4–6 cover design / acceptance / risk surface
4. ✅ open follow-ons documented in § 6
5. ✅ companion handovers cover upstream context

**All five checks pass. Handover is ready.**

---

## 9. Roadmap Position

- **Current cycle:** v0.3.x **EXTENDED** with v0.3.3 bioprocess-line
  composite work
- **v0.3.x cycle modules to date:** 5 P5++ + 3 v9.5 = 8 modules
- **Selectable polymer families on M1:** 21 (was 18 at v0.3.2)
- **Next cycle candidate:** v0.4.0 — MC × bin-resolved DSD unification
  (per D-049 deferral); estimated 1 module ~300 LOC; requires new SA
  brief on the variance-coupling treatment.
- **v9.5+ candidate work:** composite-specific wet-lab calibration
  campaigns to promote any of the three v9.5 composites from
  `QUALITATIVE_TREND` to `SEMI_QUANTITATIVE`. No simulator-side work
  needed until that data lands.
