# Milestone Handover — v0.3.2 Close (P5++ G5)

**Date:** 2026-04-25
**Session:** v0.3.2-IMPL-001
**Project:** Downstream-Processing-Simulator (DPSim)
**Prepared by:** /dev-orchestrator
**Classification:** Internal — Development Handover

**Companion documents:**
- `docs/handover/SA_v0_7_P5plusplus_BRIEF.md` — SA Mode-1 brief
- `docs/handover/ARCH_v0_7_P5plusplus_DECOMPOSITION.md` — module decomposition
- `docs/handover/DEVORCH_v0_7_P5plusplus_JOINT_PLAN.md` — joint plan
- `docs/handover/HANDOVER_v0_3_0_CLOSE.md` — v0.3.0 close
- `docs/handover/HANDOVER_v0_3_1_CLOSE.md` — v0.3.1 close

---

## 1. Executive Summary

v0.3.2 delivers G5 — the user-facing surface for v0.3.0's MC-LRM driver.
Two extensions: a Plotly P05/P50/P95 envelope plot for the M3
breakthrough view, and a JSON-serialisable export of `MCBands` through
`ProcessDossier`.

5 acceptance tests pass. Smoke baseline preserved: dossiers built with
`mc_bands=None` (default) carry `"mc_bands": null` in JSON output, and
the legacy v0.2.x dossier shape is byte-stable except for the new key.

**This closes the v0.3.x cycle.** All five P5++ modules (G1–G5) are
shipped. The full v0.3.x cycle delivered 57 acceptance tests (13 G1 +
19 G2 + 8 G3 + 12 G4 + 5 G5) across three milestones.

---

## 2. Module Registry — v0.3.2 add (cycle complete)

| # | Module | Version | Status | Approved | Model Used | Fix Rounds | Lines | File Path |
|---|---|---|---|---|---|---|---|---|
| 1 | G1.posterior_samples | 0.3.0 | **APPROVED** | 2026-04-25 | Sonnet | 0 | ~290 | `src/dpsim/calibration/posterior_samples.py` |
| 2 | G2.monte_carlo | 0.3.0 | **APPROVED** | 2026-04-25 | Opus protocol + Sonnet impl | 0 | ~480 | `src/dpsim/module3_performance/monte_carlo.py` |
| 3 | G3.method_simulation_dispatch | 0.3.0 | **APPROVED** | 2026-04-25 | Sonnet | 0 | ~80 ext | `module3_performance/method_simulation.py`, `core/performance_recipe.py` |
| 4 | G4.bayesian_fit | 0.3.1 | **APPROVED** | 2026-04-25 | Opus protocol + Sonnet impl | 1 | ~280 | `src/dpsim/calibration/bayesian_fit.py` |
| 5 | G5.ui_dossier_integration | 0.3.2 | **APPROVED** | 2026-04-25 | Sonnet | 0 | ~210 ext | `visualization/plots_m3.py`, `process_dossier.py` |

---

## 3. Integration Status

| Interface | From Module | To Module | Status | Notes |
|---|---|---|---|---|
| `plot_mc_breakthrough_bands()` | G5 | M3 UI / tab_m3 | **LIVE** | Renders `MCBands.curve_bands` quantiles; design-system compliant (teal-500 / slate-400 only) |
| `_mc_bands_to_dict()` | G5 helper | dossier exporters | **LIVE** | Schema version `mc_bands.1.0`; default decimation 100 points/curve |
| `ProcessDossier.mc_bands` field | G5 | dossier consumers | **LIVE** | Optional; default `None`; preserves v0.2.x byte layout when unused |
| `ProcessDossier.from_run(mc_bands=...)` | G5 | run-completion code | **LIVE** | Optional kwarg |

All v0.3.x integration points are now LIVE.

---

## 4. Quality-Gate Enforcement

### G5 (UI bands + dossier)

| Gate | Result |
|---|---|
| DESIGN.md compliance | ✅ teal-500 (#14B8A6) median; slate-400 (rgba(148,163,184,...)) envelope; no purple, no gradient, no decorative animation |
| SA-Q4/Q5 surfaced in UI | ✅ footer annotation parses `mc_bands.model_manifest.assumptions` for the "marginal-only" and "DSD geometric variance" lines |
| Dossier round-trip via JSON | ✅ `test_mc_bands_round_trip_through_dossier_json` |
| Curve decimation bounds JSON size | ✅ `test_curve_decimation_bounds_dossier_size` (100-point default; pass `None` for full-resolution) |
| Smoke baseline preserved | ✅ `mc_bands=None` produces `"mc_bands": null` in JSON; existing dossier consumers untouched |
| 4-test inventory | ✅ 5 tests (one extra for the None-mc_bands smoke) |

**Verdict: APPROVED** (0 fix rounds).

---

## 5. v0.3.x Cycle Summary

### Cycle close metrics

| Metric | Value |
|---|---|
| Milestones | 3 (v0.3.0 + v0.3.1 + v0.3.2) |
| Modules | 5 (G1 + G2 + G3 + G4 + G5) |
| Tests added | 57 (13 + 19 + 8 + 12 + 5) |
| LOC added (src) | ~1340 |
| Average fix rounds | 0.2 (1 round across 5 modules) |
| Audit verdicts | 5/5 APPROVED, no REVISION or REDESIGN required |
| ruff = 0 | ✅ on all new files |
| mypy = 0 | ✅ on all new files (with `--ignore-missing-imports` for scipy/pymc) |
| Smoke baseline preserved | ✅ default behaviours preserve v0.2.x output |

### Acceptance criteria coverage

The five v0.3.0 ACs (linear-regime delta-method match, non-linear pH
disagreement, reformulated convergence diagnostics, parallel
determinism, byte-identical smoke baseline) all carry through v0.3.1
and v0.3.2 unchanged. The v0.3.1 G4 ACs (q_max within 5 %, K_L within
50 %, covariance attached, R-hat/ESS/divergence gates fire, base
install works without pymc) are gated on the bayesian extra and run
in CI matrices that install it. The v0.3.2 G5 ACs (P05/P50/P95 traces
render with design-system colors; SA-Q4/Q5 surfaced in footer; dossier
round-trip; curve decimation; smoke baseline) all pass.

---

## 6. Risks Closed and Open

### Closed at v0.3.x cycle close

- All R-G1, R-G2, R-G3, R-G4, R-G5 risks from the architect's
  decomposition either closed or carried as documented follow-ons.
- Smoke baseline preservation across all three milestones — verified
  through three independent gates (`monte_carlo_n_samples=0`,
  `mc_bands=None` in dossier, lazy pymc import).

### Open (carry to v0.4.0+)

- **MC × bin-resolved DSD** (D-049). 7× compute saving was the v0.3
  trade-off; v0.4+ unifies the paths.
- **Solver-lambda helper.** Higher-level helper that wires
  `PosteriorSamples` → FMC mutation → `solve_lrm` (with isotherm
  parameter substitution + `tail_mode` → tightened tolerances). Targets
  `src/dpsim/module3_performance/mc_solver_lambdas.py`. ~80 LOC.
- **Joblib parallelism in run_mc.** R-G2-4 mitigation deferred the
  joblib wiring; serial path is bit-stable. Land with the
  solver-lambda helper.
- **pymc upper bound.** Add a CI matrix run when pymc 6.x ships.

---

## 7. Files Changed (v0.3.2 only — see prior handovers for v0.3.0/v0.3.1)

### Modified files

- `src/dpsim/visualization/plots_m3.py` — appended
  `plot_mc_breakthrough_bands()` (~140 LOC)
- `src/dpsim/process_dossier.py` — added `_mc_bands_to_dict` helper +
  `mc_bands` field on `ProcessDossier` + `from_run` kwarg + `to_json_dict`
  surfaces it
- `src/dpsim/__init__.py` — `__version__ = "0.3.2"`
- `pyproject.toml` — `version = "0.3.2"`
- `CHANGELOG.md` — v0.3.1 + v0.3.2 entries prepended

### New files

- `tests/test_v0_3_2_g5_ui_dossier.py` (5 tests)
- `docs/handover/HANDOVER_v0_3_2_CLOSE.md` (this document)

---

## 8. Five-Point Quality Standard Check

1. ✅ § 1–3 carry the v0.3.x cycle close state in isolation
2. ✅ § 7 lists every v0.3.2 file change; § 5 references prior handovers
3. ✅ § 4–6 cover design / acceptance / risk surface
4. ✅ next-cycle work (v0.4.0 follow-ons) listed in § 6
5. ✅ companion docs cover all upstream context

**All five checks pass. Handover is ready.**

---

## 9. Roadmap Position

- **Current cycle:** v0.3.x **CLOSED** (5/5 modules approved)
- **Next cycle:** v0.4.0 — MC × bin-resolved DSD unification (per
  D-049). Estimated 1 module, ~300 LOC, 1 session. Architecture
  decomposition not yet drafted; would require a new SA brief on the
  variance-coupling treatment.
- **Adjacent v0.3.x follow-on:** solver-lambda helper for production
  MC use against the real `solve_lrm`. ~80 LOC; lands as v0.3.3 or
  rolls into v0.4.0.
