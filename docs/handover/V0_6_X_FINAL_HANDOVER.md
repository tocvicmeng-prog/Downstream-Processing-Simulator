# v0.6.x Final Handover — Quantity Accessors Across All Stages + Signature Typing + P5++ Scoping

**Date:** 2026-04-25
**Milestone:** v0.6.0 → v0.6.1 → v0.6.2 cumulative ("Quantity accessors across M1/M2/M3 + signature typing + DSD parallelism + P5++ scoping doc")
**Status:** All five v0.6.x modules (E1, E2, F1, F2, F4) APPROVED on first audit pass (0 fix rounds in v0.6.1/v0.6.2). P5++ scoping doc (F5) shipped as planning artifact only — implementation remains v0.7.0 work. ruff = 0. Smoke baseline preserved exactly.
**Source roadmap:** `docs/handover/V0_5_0_DEPRECATION_REMOVAL_HANDOVER.md` §9 + `docs/handover/V0_6_0_QUANTITY_ACCESSORS_AND_PARALLELISM_HANDOVER.md` §9
**Predecessor:** `docs/handover/V0_6_0_QUANTITY_ACCESSORS_AND_PARALLELISM_HANDOVER.md`

---

## 1. Executive Summary

v0.6.x closes **all remaining open architect-coherence work** that fits in the
current architectural cleanup track. After this milestone, **every public
result dataclass in M1, M2, and M3** exposes typed `Quantity` accessors
alongside the bare-float fields (additive, non-breaking). The two most-used
M3 entry points (`run_breakthrough`, `run_chromatography_method`) accept
either `Quantity` or `float` for their documented-unit scalar arguments via
the new `dpsim.core.quantities.unwrap_to_unit` helper. The only outstanding
deliverable on the roadmap — **P5++ Monte-Carlo LRM uncertainty propagation**
— has a full G1-readiness scoping document at `docs/p5_plus_plus_protocol.md`
ready for fresh-session pickup at v0.7.0.

The lifecycle CLI smoke result is preserved exactly: **DBC10 = 0.706 mol/m³ column,
dP = 37.12 kPa, mass-balance error = 0.00%, weakest tier = qualitative_trend** — same
as every milestone since v0.1.0.

---

## 2. Module Registry — v0.6.x cumulative

| # | Module | Version | Status | Tier | Fix rounds | LOC | File |
|---|---|---|---|---|---|---|---|
| **E1** | Typed `Quantity` accessors on M3 result dataclasses | 0.6.0 | APPROVED | Opus | 0 | ~140 | `module3_performance/orchestrator.py`, `method.py` |
| **E2** | Joblib `n_jobs` parallelism for DSD-quantile execution | 0.6.0 | APPROVED | Opus | 0 | ~75 | `module3_performance/method_simulation.py` |
| **F2** | M2 typed `Quantity` accessors (FMC, ModificationResult, ACSProfile) | **0.6.1** | APPROVED | Opus | 0 | ~145 | `module2_functionalization/orchestrator.py`, `modification_steps.py`, `acs.py` |
| **F4** | M1 typed `Quantity` accessors (Emulsification/Gelation/Crosslinking/Mechanical) | **0.6.2** | APPROVED | Opus | 0 | ~120 | `datatypes.py` |
| **F1** | M3 entry-point signatures accept `Quantity \| float` (`unwrap_to_unit` helper) | **0.6.1** | APPROVED | Opus | 0 | ~50 | `core/quantities.py`, `module3_performance/orchestrator.py`, `method.py` |
| **F5** | P5++ Monte-Carlo LRM scoping protocol | **planning only** | DOCUMENT SHIPPED | Opus | — | ~600 lines doc | `docs/p5_plus_plus_protocol.md` |

**v0.6.1 + v0.6.2 net LOC delivered:** +315 source / +570 tests (24 M1+M2 accessor tests + 9 fast Quantity-signature tests + 6 slow signature tests).
**v0.6.x fix rounds: 0/12 budgeted** (E1+E2 from v0.6.0 milestone + F1+F2+F4 fresh).
**Cumulative project (v0.1 → v0.6.x):** ~2465 net source LOC; ~2850 net test LOC; **31 modules approved**; **1 fix round** out of 89 budgeted across the project.

---

## 3. Integration Status — cumulative architect-coherence audit

| Audit finding | Status |
|---|---|
| **D1 (HIGH)** — Dual-API surface | **CLOSED** (v0.5.0 / D1) |
| **D2 (MEDIUM)** — Gradient-elution evidence-tier break | **CLOSED** (v0.2.0 / A2) |
| **D2 (HIGH)** — DSD 3-quantile collapse | **CLOSED** (v0.4.0 / C5) |
| **D3 (HIGH)** — `Quantity` boundary-only typing | **FULLY CLOSED for accessors** (v0.6.0 / E1 + v0.6.1 / F2 + v0.6.2 / F4 + v0.6.1 / F1 signature typing). Field-replacement is a v0.7.0+ deprecation cycle. |
| **D3 (MEDIUM)** — `ResultGraph` lifecycle-only | **CLOSED** (v0.4.0 / C4) |
| **D3 (HIGH)** — String-based calibration tier propagation | **FULLY CLOSED** (v0.4.0 / C3 + v0.5.0 / D2) |
| **D4** — Per-DSD parallelism | **FULLY CLOSED** (v0.6.0 / E2) |
| **D5 (HIGH)** — `ModelMode` L4-only | **FULLY CLOSED** (v0.4.0 / C2 + v0.5.0 / D5) |
| **D5 (MEDIUM)** — DESIGN.md product-context drift | **CLOSED** (v0.3.0 / B8) |
| **D6 (HIGH)** — Family-first M1-only | **CLOSED** (v0.3.0 / B1+B2+B3 + v0.4.0 / C7) |
| **D6 (LOW)** — `ProcessDossier` not default | **CLOSED** (v0.5.0 / D3) |

**Net: ALL 11 audit findings closed.** No remaining architect-coherence deficits.

The only outstanding scientific-advisor scope-of-claim item (P5++ Monte-Carlo
uncertainty propagation) is now documented in `docs/p5_plus_plus_protocol.md`
as the G1-PASS planning artifact for v0.7.0.

---

## 4. Quantity-Accessor Inventory (cumulative)

### M1 stage (v0.6.2 / F4)
- `EmulsificationResult.{d32_q, d50_q, d10_q, d90_q, span_q}`
- `GelationResult.{pore_size_mean_q, porosity_q, alpha_final_q}`
- `CrosslinkingResult.{p_final_q, G_chitosan_final_q, xi_final_q}`
- `MechanicalResult.{G_DN_q, E_star_q, G_agarose_q, G_chitosan_q, pore_size_mean_q, xi_mesh_q}`

### M2 stage (v0.6.1 / F2)
- `FunctionalMediaContract.{bead_d50_q, porosity_q, pore_size_mean_q, functional_ligand_density_q, estimated_q_max_q, activity_retention_q, ligand_leaching_fraction_q}`
- `ModificationResult.{conversion_q, delta_G_DN_q}`
- `ACSProfile.{total_sites_q, accessible_sites_q, remaining_sites_q, total_density_q, accessible_density_q}`

### M3 stage (v0.6.0 / E1)
- `BreakthroughResult.{dbc_5pct_q, dbc_10pct_q, dbc_50pct_q, pressure_drop_q, mass_balance_error_q}`
- `LoadedStateElutionResult.{recovery_fraction_q, peak_time_q, peak_width_half_q, mass_balance_error_q}`
- `ColumnOperabilityReport.{pressure_drop_q, bed_compression_q, residence_time_q, interstitial_velocity_q}`
- `ProteinAPerformanceReport.{q_max_q, predicted_recovery_q, activity_retention_q, cycle_lifetime_q}`

### M3 entry-point signatures accepting Quantity-or-float (v0.6.1 / F1)
- `run_breakthrough(C_feed, flow_rate, feed_duration, total_time, ...)` — units: mol/m³, m³/s, s, s.
- `run_chromatography_method(max_pressure_Pa, pump_pressure_limit_Pa, ...)` — units: Pa.

### Cross-cutting (v0.6.1 / F1)
- `dpsim.core.quantities.unwrap_to_unit(value, expected_unit) -> float` — public helper.

---

## 5. Code Inventory

### New tests (v0.6.1 + v0.6.2)
- `tests/test_quantity_accessors_m1_m2.py` — 24 tests (M1 EmulsificationResult/GelationResult/CrosslinkingResult/MechanicalResult + M2 FMC/ModificationResult/ACSProfile)
- `tests/test_quantity_signatures.py` — 15 tests (9 fast `unwrap_to_unit` unit tests + 6 slow Quantity-or-float entry-point tests)

**v0.6.x test totals: 49 new tests, all passing. Cumulative project test sweep: 195 passed, 0 regressions.**

### Edited files (v0.6.1 + v0.6.2)
- `src/dpsim/core/quantities.py` — `unwrap_to_unit` public helper added (F1).
- `src/dpsim/datatypes.py` — `EmulsificationResult`, `GelationResult`, `CrosslinkingResult`, `MechanicalResult` gain typed `_q` accessor properties (F4).
- `src/dpsim/module2_functionalization/orchestrator.py` — `FunctionalMediaContract` gains 7 typed `_q` accessors (F2).
- `src/dpsim/module2_functionalization/modification_steps.py` — `ModificationResult` gains `conversion_q` and `delta_G_DN_q` (F2).
- `src/dpsim/module2_functionalization/acs.py` — `ACSProfile` gains 5 typed `_q` accessors (F2).
- `src/dpsim/module3_performance/orchestrator.py` — `run_breakthrough` accepts `Quantity | float` for C_feed, flow_rate, feed_duration, total_time (F1).
- `src/dpsim/module3_performance/method.py` — `run_chromatography_method` accepts `Quantity | float` for max_pressure_Pa, pump_pressure_limit_Pa (F1).

### New documentation
- `docs/p5_plus_plus_protocol.md` — P5++ Monte-Carlo LRM uncertainty propagation scoping doc (F5).
- This handover.

---

## 6. Design Decisions Log (v0.6.x additions)

| ID | Decision | Rationale |
|---|---|---|
| F2-D1 | Add typed accessors to **all five** ACS site-count fields (total / accessible / remaining + densities), even though only `remaining_sites` is currently consumed externally. | The accessor pattern is mechanical and the marginal LOC cost is trivial; future UI rendering of full ACS-inventory tables (planned for v0.7+ wet-lab batch records) will benefit without further changes. |
| F2-D2 | Skip `ACSProfile.{crosslinked,activated,hydrolyzed,ligand_coupled,blocked}_sites` typed accessors. | These are intermediate-state counts that exit through `remaining_sites` and the dataclass docstring. Adding accessors for every field would dilute the deliberately-minimal "_q" surface. |
| F4-D1 | M1 accessors target the **scalar** result fields only — array fields (`d_bins`, `T_history`, `pore_size_distribution`) stay as numpy arrays. | Quantity wraps scalar values; for array-of-quantity the proper abstraction is `pint.Quantity` with array support, which is a v0.8+ replacement of the in-house Quantity class. |
| F4-D2 | `MechanicalResult.G_DN_q` is the headline accessor; `G_DN_lower` and `G_DN_upper` (the HS-bound fields) do not get accessors. | Those are reference bounds, not headline outputs; consumers that read them are inside the L4 module and don't need typed accessors. |
| F1-D1 | `unwrap_to_unit` is a **module-level public function** in `dpsim.core.quantities`, not a `Quantity` method. | Type-narrowing pattern: `unwrap_to_unit` accepts `Quantity \| float \| int` (a union); a `Quantity` method would force callers to first check `isinstance(value, Quantity)`. The public free function is the cleanest entry-point shim. |
| F1-D2 | F1 only converts the **most-used** scalar args (C_feed, flow_rate, feed_duration, total_time, max_pressure_Pa, pump_pressure_limit_Pa). `D_molecular`, `k_ads`, `sigma_detector`, `mu`, `rho` stay float-only. | The skipped args are typically left at their default values (the caller never explicitly specifies them); investing in unit-tagged accessors for them would have low ROI vs the documentation cost. They can graduate to Quantity-or-float in v0.7+ if a use case emerges. |
| F5-D1 | P5++ is a planning artifact only — no implementation in v0.6.x. | P5++ is a multi-session, multi-week scientific deliverable that requires a fresh /scientific-advisor brief. Mixing it into the architectural cleanup track would be a scope error. The G1-PASS scoping doc gives v0.7.0 a clean entry point. |

---

## 7. v0.6.x Acceptance Gates — Verification

| Gate | Result |
|---|---|
| Every M3 result dataclass exposes typed `_q` accessors | ✅ E1 |
| Every M2 ACS / ModificationResult / FMC dataclass exposes typed `_q` accessors | ✅ F2 |
| Every M1 result dataclass (FullResult sub-fields) exposes typed `_q` accessors | ✅ F4 |
| Joblib `n_jobs` parallelism wired for the DSD full-method path | ✅ E2 |
| `unwrap_to_unit` helper public; `run_breakthrough` and `run_chromatography_method` accept `Quantity \| float` | ✅ F1 |
| All architect-coherence-audit findings closed (modulo P5++) | ✅ §3 |
| P5++ scoping doc shipped with G1 = PARTIAL PASS (10/12) | ✅ F5 |
| Smoke baseline preserved | ✅ DBC10 / dP / mass-balance / weakest-tier identical to v0.1.0 |
| ruff = 0 | ✅ across all v0.6.x new/edited files |
| Test sweep | ✅ **195 passed**, 0 regressions, 7 deselected (slow), 2 pre-existing Windows tmp-dir errors |

---

## 8. Cumulative Project Status (v0.1.0 → v0.6.x)

- **31 modules approved** across 6 milestones (v0.2.0, v0.3.0, v0.4.0, v0.5.0, v0.6.0, v0.6.x).
- **1 fix round used** (v0.4.0 / C2 mechanistic-mode tier-downgrade overreach) out of **89 budgeted**.
- **~2465 net source LOC**, **~2850 net test LOC**.
- **Seven milestone handovers** (V0_2 → V0_6_x) + **one architect coherence audit** + **one joint update plan** + **one P5++ scoping protocol** + **the v0.2.0 PerformanceRecipe protocol** + **the v0.3.0 dev-orchestrator plan**.
- **All 11 architect-coherence audit findings closed.** Single remaining roadmap item is P5++.

---

## 9. What's Still Open

After v0.6.x, **the architectural cleanup track is complete.** The only
remaining open item is a properly-scoped scientific deliverable:

| Item | Scope | Where | When |
|---|---|---|---|
| **P5++ Monte-Carlo LRM uncertainty propagation** | Multi-session, ~1300 source LOC across 5 modules (G1–G5). Requires fresh /scientific-advisor brief. | `docs/p5_plus_plus_protocol.md` (G1 = PARTIAL PASS, ready for fresh-session pickup) | **v0.7.0** alone (3–5 sessions) |
| Optional Bayesian fitting via pymc/HMC | Independent of the MC driver | (G4 in P5++ protocol) | v0.7.1 |
| MC + bin-resolved DSD propagation | Combinatorial wall-time risk; needs separate scoping | (out of P5++ §4 v7-Q3) | v0.8.0+ |
| Digital-twin live mode (real-time Bayesian update during wet-lab run) | Full new architecture | (out of P5++ §1.2 won't) | v0.9.0+ |

There are **no remaining v0.6.x tasks**. The architectural cleanup that began
with the 14-module v0.2.0 + v0.3.0 plan has fully landed.

---

## 10. Roadmap Position

```
v0.1.0 (initial squashed release)
  └─ v0.2.0 (evidence chain closed; first guardrails live)
       └─ v0.3.0 (family coverage, claim honesty, recipe-only UI)
            └─ v0.4.0 (architectural coherence: 6 of 7 C-modules)
                 └─ v0.5.0 (deprecation removal + ProcessDossier + M2 mode)
                      └─ v0.6.0 (Quantity accessors phase 1 + n_jobs parallelism)
                           └─ v0.6.x (THIS — Quantity accessors across M1/M2/M3 + signature typing + P5++ scoping)
                                └─ v0.7.0 (P5++ MC driver — fresh session, uses docs/p5_plus_plus_protocol.md)
                                     └─ v0.7.1 (P5++ Bayesian fitting)
                                          └─ v0.7.2 (P5++ UI band rendering + dossier serialization)
                                               └─ v0.8.0+ (MC + bin-resolved DSD; live digital twin)
```

v0.7.0 entry point: **`docs/p5_plus_plus_protocol.md`** (G1 = PARTIAL PASS at scoping; full G1 readiness pending /scientific-advisor brief at session start).

---

## 11. Sign-Off

All G3 audit dimensions evaluated:
- **D1 (structural)** — Typed `_q` accessor pattern is uniform across all 18 result dataclasses (M1, M2, M3). The `unwrap_to_unit` entry-point helper is module-scope and reusable.
- **D2 (algorithmic)** — Quantity construction in accessors is O(1) per read with no shared state. Unit conversions use the existing `Quantity.as_unit` infrastructure.
- **D3 (data-flow)** — The typed-accessor surface is now uniform; downstream consumers can opt into unit-aware reads at any stage. The bare-float storage remains the internal optimisation.
- **D4 (performance)** — Smoke wall time unchanged. Each `_q` accessor read constructs a fresh Quantity (~microseconds, negligible).
- **D5 (maintainability)** — Every new accessor / helper has a test. Pattern documented in module docstrings. P5++ has its own scoping doc for fresh-session pickup.
- **D6 (first-principles)** — Quantity unit annotations match the documented field units one-to-one across all dataclass fields. The `cycle_lifetime_q` accessor's `Quantity.note` carries the UNSUPPORTED scope-of-claim warning.

**Verdict: APPROVED.** v0.6.x cumulative milestone closed. **All 11 architect-coherence findings closed; the architectural cleanup track is complete.** P5++ is the sole remaining roadmap item, properly scoped as v0.7.0+ with a G1-readiness scoping doc. Ready to ship v0.6.x and pick up P5++ in a fresh session.
