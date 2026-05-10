# DPSim v0.8.2 — Cumulative open-future-work close

**Date:** 2026-05-10 (continuing the same-day patch cluster after v0.7.0 / v0.8.0 / v0.8.1)
**Author:** `/dev-orchestrator`
**Inputs inherited:** `HANDOVER_v0_8_1_release.md` §"Cumulative open future-work items"
**Target release:** v0.8.2 (patch bump per the project versioning policy — minor bumps reserved for matured-status milestones)
**Mode:** project plan; execution interleaved

---

## 1. Scope — close all 10 code-work items from the v0.8.1 cumulative open list

The v0.8.1 release handover catalogued 11 cumulative open items. Of these:

- **10 are pure-coding work** — eligible for a patch-bump close in this batch.
- **1 is user-side wet-lab work** — `wet-lab calibration of K_geom / ν` cannot ship as code; this plan acknowledges it explicitly and leaves it to the user to drive once data is available.

This v0.8.2 plan closes all 10 code items. Where the design space is genuinely open (full SMA promotion, Bayesian propagation, AKTA hardware bridge, multi-column / SMB), an ADR is shipped alongside the code so the chosen scope is auditable.

## 2. Work item ledger — W-036 … W-045

| ID | Severity | Title | Files affected | Bundle |
|---|---|---|---|---|
| **W-036** | LOW | Pre-existing `confidence_tier` test stale-field fix | `tests/test_module3_breakthrough.py::test_breakthrough_inherits_fmc_qualitative_tier` | A |
| **W-037** | LOW | M1 / M2 plot tier-gating extension (mirrors W-035) | `visualization/plots_m2.py`, M1 PBE plot module | A |
| **W-038** | MEDIUM | IMAC imidazole-modulated Langmuir adapter (mirrors W-034) | NEW `module3_performance/isotherms/imidazole_dependent.py`; `isotherms/adapter.py` branch | A |
| **W-039** | MEDIUM | Full SMA promotion adapter | NEW `module3_performance/isotherms/sma_modulated.py`; ADR-006; `isotherms/adapter.py` branch | B |
| **W-040** | MEDIUM | Multi-step pressure feasibility | `optimization/objectives.py` (extend `PressureFeasibilityContext`) | B |
| **W-041** | MEDIUM | Channeling auto-recovery action routing | `module3_performance/pressure_monitor.py` (`RecoveryAction` enum + `recovery_action` field on `PressureMonitorOutput`); `tab_m3_monitor.py` UI surface | B |
| **W-042** | MEDIUM | Multi-component competitive IEX salt modulation | NEW `module3_performance/isotherms/competitive_salt_dependent.py`; `isotherms/adapter.py` branch | B |
| **W-043** | HIGH | Monte Carlo Bayesian envelope wrapper + ADR-007 | NEW `module3_performance/pressure_envelope_mc.py`; ADR-007 | C |
| **W-044** | HIGH | AKTA monitor source abstraction + simulator backend + ADR-008 | NEW `module3_performance/monitor_source.py`; ADR-008. UNICORN socket impl deferred. | C |
| **W-045** | HIGH | Multi-column / SMB pressure series + ADR-009 | NEW `module3_performance/multi_column.py`; ADR-009. Cyclic SMB dynamics deferred. | C |

### 2.1 BLOCKER classification

None. All items are scoped, additive, and reversible.

### 2.2 Explicitly user-side (NOT a v0.8.2 deliverable)

- **Wet-lab calibration of K_geom and ν** — gates promotion from
  SEMI_QUANTITATIVE INTERVAL to CALIBRATED_LOCAL NUMBER render mode
  on the affected outputs. The `calibration_store` argument of
  `compute_pressure_envelope` and the `calibrated_locally` flag of
  `SaltModulatedLangmuir` are the wire-up points; users drive the
  data side. v0.8.2 does NOT manufacture wet-lab values to fake the
  promotion path.

## 3. Sequenced batches

| Batch | IDs | Modules | Model tier | Notes |
|---|---|---|---|---|
| **B-0g** | W-036 + this plan | the test fix + the plan doc | n/a | One-line stale-field rename; verifies the test suite returns to clean state. |
| **B-1ℓ** *(W-037)* | W-037 | `plots_m2.py` (and any M1 plot file with chart-anchored numeric badges) | **Sonnet** | Pure UX mirror of W-035. Optional `tier=` kwarg with `tier=None` preserving legacy formatting. |
| **B-1m** *(W-038)* | W-038 | NEW `imidazole_dependent.py`; adapter branch | **Sonnet** | Pattern mirror of W-034 with `c_imidazole_ref_mol_m3` reference and `ν_imidazole` exponent. |
| **B-1n** *(W-039)* | W-039 | NEW `sma_modulated.py`; ADR-006; adapter branch | **Sonnet** | Adapter that wraps the existing `SMAIsotherm` class with the `equilibrium_loading(C, c_salt)` interface. ADR-006 documents the per-rhs cost vs Mollerup-simplified tradeoff. |
| **B-2k** *(W-040)* | W-040 | `optimization/objectives.py` | **Sonnet** | Extend `PressureFeasibilityContext` with an optional `step_program` field; `pressure_feasible` becomes worst-case across the program. Backwards-compatible. |
| **B-2ℓ** *(W-041)* | W-041 | `pressure_monitor.py` + `tab_m3_monitor.py` | **Sonnet** | Add `RecoveryAction` enum and a `recovery_action` field on `PressureMonitorOutput`. The streaming UI's status panel surfaces the structured action chip. |
| **B-2m** *(W-042)* | W-042 | NEW `competitive_salt_dependent.py`; adapter branch | **Sonnet** | Multi-component analogue of W-034. Each component carries its own ν. |
| **B-2n** *(W-043)* | W-043 | NEW `pressure_envelope_mc.py`; ADR-007 | **Opus** for ADR-007; **Sonnet** for the MC wrapper. | First-pass uncertainty propagation. Lognormal on K_geom, beta on ν, lognormal on μ; sample → envelope per draw; aggregate to P05/P50/P95. |
| **B-3g** *(W-044)* | W-044 | NEW `monitor_source.py`; ADR-008 | **Sonnet** | Protocol-typed abstraction. Three concrete backends ship: `CSVReplayMonitorSource`, `SimulatedMonitorSource`, and `NullMonitorSource`. The UNICORN socket implementation is an explicit v0.9 deliverable with hardware-side requirements documented in the ADR. |
| **B-3h** *(W-045)* | W-045 | NEW `multi_column.py`; ADR-009 | **Sonnet** | Series-of-`ColumnGeometry` aggregation. Compute envelopes per-column and return a unified `MultiColumnPressureEnvelope` whose ΔP is the series sum. SMB cyclic dynamics is explicitly out of scope. |
| **B-4a** | — | version bump, CHANGELOG, handovers, tag | n/a | Patch bump 0.8.1 → 0.8.2. |

## 4. Validation gates introduced by v0.8.2

- **Gate 14: M1/M2 plot annotations carry tier labels.** Closed when B-1ℓ lands.
- **Gate 15: IMAC imidazole-driven elution is physics-aware.** Closed when B-1m lands. Mirrors gate 12 for IMAC.
- **Gate 16: Full SMA promotion path is reachable from one constructor.** Closed when B-1n + ADR-006 land.
- **Gate 17: BO can drop candidates infeasible at any step in the recipe.** Closed when B-2k lands.
- **Gate 18: Streaming monitor outputs structured recovery actions.** Closed when B-2ℓ lands.
- **Gate 19: Multi-component competitive IEX consumes salt envelope.** Closed when B-2m lands.
- **Gate 20: Pressure envelope ships P05/P50/P95 uncertainty bands.** Closed when B-2n + ADR-007 land.
- **Gate 21: Monitor source is hardware-agnostic.** Closed when B-3g + ADR-008 land. UNICORN hardware bridge is explicitly the binding-open part of this gate (v0.9 candidate).
- **Gate 22: Multi-column series operations have an envelope.** Closed when B-3h + ADR-009 land. Cyclic SMB dynamics is explicitly the binding-open part of this gate.

## 5. What v0.8.2 does *not* attempt

- **UNICORN live socket bridge** — bound on hardware availability. v0.9 candidate.
- **Cyclic SMB dynamics** — switching valves, multi-column rotation, port migration. v0.9 candidate.
- **Bayesian inversion of wet-lab posteriors** — v0.8.2 ships *forward* MC propagation; running an inverse problem against measured pressure-flow data is wet-lab-driven.
- **Wet-lab K_geom / ν calibration** — explicitly user-side; not a code deliverable.

## 6. Handover targets

- `docs/handover/HANDOVER_v0_8_2_b0g_tech_debt.md` — at end of B-0g
- One handover per Tier-1 / Tier-2 / Tier-3 batch (B-1ℓ … B-3h)
- `docs/handover/HANDOVER_v0_8_2_release.md` — at v0.8.2 tag

## 7. New ADRs in this batch

- ADR-006 — Full SMA promotion path: cost vs precision (B-1n).
- ADR-007 — Forward MC Bayesian envelope: prior choices and aggregation policy (B-2n).
- ADR-008 — Monitor source abstraction: hardware-agnostic surface (B-3g).
- ADR-009 — Multi-column series: scope vs cyclic SMB (B-3h).

---

### Disclaimer

> v0.8.2 closes the cumulative open code work from the v0.8.1 release handover. Where the design space is open (full SMA, MC propagation, AKTA hardware, SMB cyclic dynamics), the chosen scope is documented in an ADR. Wet-lab calibration of K_geom / ν is explicitly user-side and not a v0.8.2 deliverable. None of the new modules ship at higher than `SEMI_QUANTITATIVE` tier without user-supplied calibration data.
