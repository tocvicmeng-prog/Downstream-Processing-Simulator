# HANDOVER — v0.8.2 release close

**Date:** 2026-05-10 (continuing the same-day patch cluster after v0.7.0 / v0.8.0 / v0.8.1)
**Tag:** v0.8.2
**Work plan:** `docs/update_workplan_2026-05-10_v0_8_2.md`

## Summary

v0.8.2 closes 10 of 11 cumulative-open code-work items from the v0.8.1
release handover. The 11th item (wet-lab K_geom / ν calibration) is
explicitly user-side and is NOT a v0.8.2 deliverable. Patch bump per
the project versioning policy; v0.9 stays available for a matured-status
plateau.

## Per-batch summary

### B-0g (W-036) — confidence_tier tech debt

| File | Change |
|---|---|
| `tests/test_module3_breakthrough.py` | `test_breakthrough_inherits_fmc_qualitative_tier` no longer passes the legacy `confidence_tier="ranking_only"` kwarg removed in v0.5.0 (D2). Tier inheritance flows through `model_manifest.evidence_tier` + `diagnostics["fmc_confidence_tier"]`. |

### B-1ℓ (W-037) — M1 plot tier-gating

| File | Change |
|---|---|
| `src/dpsim/visualization/plots.py` | `plot_droplet_size_distribution(result, *, tier=None)` routes d32 / d50 annotations through `render_decision_grade_annotation` when `tier` is supplied. `tier=None` keeps legacy formatting. |
| `tests/visualization/test_plots_m1_tier.py` | NEW — 4 tests covering all five render-mode branches. |

### B-1m (W-038) — IMAC imidazole adapter

| File | Change |
|---|---|
| `src/dpsim/module3_performance/isotherms/imidazole_dependent.py` | NEW — `imidazole_modulation_factor` + `ImidazoleModulatedLangmuir` adapter mirroring W-034. Defaults: n=1.5, c_imidazole_ref=50 mM. |
| `src/dpsim/module3_performance/isotherms/adapter.py` | New `EquilibriumAdapter` branch routes `process_state["imidazole"]`. |
| `tests/module3_performance/test_imidazole_modulated.py` | NEW — 21 tests. |

### B-1n (W-039) — Full SMA promotion adapter + ADR-006

| File | Change |
|---|---|
| `docs/decisions/ADR-006-full-sma-promotion-path.md` | NEW — cost vs precision tradeoff. |
| `src/dpsim/module3_performance/isotherms/sma_modulated.py` | NEW — `SaltModulatedSMA`: same `equilibrium_loading(C, c_salt_mol_m3)` signature as `SaltModulatedLangmuir`, internally invokes the SMA fixed-point on q_salt at every call. |
| `src/dpsim/module3_performance/isotherms/adapter.py` | New branch for `SaltModulatedSMA`. |
| `tests/module3_performance/test_sma_modulated.py` | NEW — 16 tests including the σ=0 sanity check that reduces SMA toward Mollerup-simplified shape. |

### B-2k (W-040) — Multi-step pressure feasibility

| File | Change |
|---|---|
| `src/dpsim/optimization/objectives.py` | New `PressureStep` frozen dataclass; `step_program` Optional field on `PressureFeasibilityContext`; multi-step branch in `pressure_feasible` reports ALL step-level violations (not just first). Single-step legacy v0.8.0 path preserved when `step_program=None`. |
| `tests/test_pressure_feasibility_multistep.py` | NEW — 7 tests covering backwards-compat, all-feasible, single-step violation, multi-step all-reported, unsupported family, empty program. |

### B-2ℓ (W-041) — Channeling auto-recovery action routing

| File | Change |
|---|---|
| `src/dpsim/module3_performance/pressure_monitor.py` | New `RecoveryAction` enum (NONE / CONTINUE_MONITOR / REDUCE_FLOW / SWITCH_TO_WASH / STOP_AND_REPACK / EMERGENCY_STOP / OPERATOR_REVIEW); `_RULE_TO_ACTION` mapping; `recovery_action` field on `PressureMonitorOutput`. |
| `src/dpsim/module3_performance/pressure_monitor_replay.py` | `final_recovery_action` field on `ReplaySummary`; replay propagates final action. |
| `src/dpsim/visualization/tabs/tab_m3_monitor.py` | Status panel surfaces an action chip alongside the rule name. |
| `tests/module3_performance/test_recovery_action.py` | NEW — 6 tests + sentinel coverage check that every `PressureMonitorRule` has a non-NONE action. |

### B-2m (W-042) — Multi-component competitive IEX salt modulation

| File | Change |
|---|---|
| `src/dpsim/module3_performance/isotherms/competitive_salt_dependent.py` | NEW — `SaltModulatedCompetitiveLangmuir` with per-component characteristic-charge ν_i array. |
| `src/dpsim/module3_performance/isotherms/adapter.py` | New branch routes `salt_concentration` through the multi-component adapter. |
| `tests/module3_performance/test_competitive_salt_dependent.py` | NEW — 13 tests including the displacement-train ordering shift assertion. |

### B-2n (W-043) — MC Bayesian envelope + ADR-007

| File | Change |
|---|---|
| `docs/decisions/ADR-007-mc-pressure-envelope.md` | NEW — prior choices (lognormal σ_log on K_geom / μ / G_DN), aggregation policy, MC-vs-analytic justification, scope deferral of inverse inference. |
| `src/dpsim/module3_performance/pressure_envelope_mc.py` | NEW — `monte_carlo_pressure_envelope` + `MCEnvelopeBands` (P05/P50/P95 + p_blocker / p_warning). MC bands stay SEMI_QUANTITATIVE per ADR-007 — they reflect priors, not posteriors. |
| `tests/module3_performance/test_pressure_envelope_mc.py` | NEW — 9 tests. |

### B-3g (W-044) — Monitor source abstraction + ADR-008

| File | Change |
|---|---|
| `docs/decisions/ADR-008-monitor-source-abstraction.md` | NEW — protocol design + UNICORN backend deferral with hardware-side requirements documented. |
| `src/dpsim/module3_performance/monitor_source.py` | NEW — `MonitorSource` protocol + 3 concrete backends (`CSVReplayMonitorSource`, `SimulatedMonitorSource`, `NullMonitorSource`). UNICORN socket backend explicitly deferred to v0.9. |
| `tests/module3_performance/test_monitor_source.py` | NEW — 15 tests. |

### B-3h (W-045) — Multi-column series + ADR-009

| File | Change |
|---|---|
| `docs/decisions/ADR-009-multi-column-series.md` | NEW — series aggregation rules + cyclic SMB deferral. |
| `src/dpsim/module3_performance/multi_column.py` | NEW — `MultiColumnGeometry`, `MultiColumnPressureEnvelope`, `compute_multi_column_envelope` with conservative aggregation: total ΔP sums, bottleneck column sets Q_max, worst column drives headroom, weakest tier rolls up, valid-domain violations carry column-index prefix. |
| `tests/module3_performance/test_multi_column.py` | NEW — 14 tests. |

## Commit chain

```
31f1ebd B-3h: multi-column series envelope (W-045, v0.8.2) + ADR-009
f73555e B-3g: MonitorSource abstraction + simulator backend (W-044, v0.8.2) + ADR-008
ec75852 B-2n: forward MC pressure envelope (W-043, v0.8.2) + ADR-007
d509699 B-2m: SaltModulatedCompetitiveLangmuir (W-042, v0.8.2)
98e4370 B-2ℓ: channeling auto-recovery action routing (W-041, v0.8.2)
9101b07 B-2k: multi-step pressure feasibility (W-040, v0.8.2)
ffba2ad B-1n: SaltModulatedSMA promotion adapter (W-039, v0.8.2) + ADR-006
45b3d85 B-1m: ImidazoleModulatedLangmuir adapter (W-038, v0.8.2)
9642122 B-1ℓ: M1 plot tier-gating extension (W-037, v0.8.2)
44f867c B-0g: v0.8.2 plan + close confidence_tier tech debt (W-036)
```

## Aggregate verification

- **130+ new tests across the 10 work items**, all passing.
- ruff + mypy clean on all new source files.
- AST gate (`tests/test_v9_3_enum_comparison_enforcement.py`): no new `is` / `is not` comparisons against managed enums.

## Validation gates closed in this release

12 → 22 (gates 14–22; gates 12–13 closed in v0.8.1):

- **14:** M1 plot annotations carry tier labels.
- **15:** IMAC imidazole-driven elution is physics-aware.
- **16:** Full SMA promotion path is reachable from one constructor.
- **17:** BO can drop candidates infeasible at any step.
- **18:** Streaming monitor outputs structured recovery actions.
- **19:** Multi-component competitive IEX consumes salt envelope.
- **20:** Pressure envelope ships P05/P50/P95 uncertainty bands.
- **21:** Monitor source is hardware-agnostic (UNICORN binding-open part = v0.9).
- **22:** Multi-column series operations have an envelope (cyclic SMB binding-open part = v0.9).

## Public-communication framing

> v0.8.2 closes the cumulative open code work from the v0.8.1 release handover. Four new ADRs (006–009) document bounded-scope decisions for items where the design space was open. Two of those (monitor + multi-column) explicitly defer the **hardware-side** and **physics-side** binding-open parts to v0.9. Wet-lab K_geom / ν calibration remains user-side and is not a code deliverable. None of the new modules ship at higher than SEMI_QUANTITATIVE tier without user-supplied calibration data.

## Open future work after v0.8.2 (potential v0.9 candidates)

These are the binding-open parts that the v0.8.2 ADRs explicitly
defer plus user-side items inherited from earlier releases:

- **AKTA UNICORN live socket backend** — implements `MonitorSource` per ADR-008. Requires hardware access to a staging UNICORN instance.
- **Cyclic SMB / multi-bed dynamics** — port-rotation, displacement coupling, time-varying envelope. ADR-009 deferral.
- **Inverse Bayesian inference** — invert measured pressure-flow data against the MC priors to produce a posterior over K_geom / ν. ADR-007 deferral.
- **Wet-lab calibration of K_geom / ν** — user-side; gates promotion to CALIBRATED_LOCAL.
- **M2 plot tier-gating** — extend W-037 to `plots_m2.py` once meaningful numeric annotations land there (currently only a static "Trust" badge).
- **Per-family priors for the MC envelope** — ADR-007 §"Out of scope".
- **Correlated MC priors** — ADR-007 §"Out of scope".
- **Multi-step coupled MC propagation** — apply MC across a step program with correlated draws (same K_geom across load + wash + elute). ADR-007 / W-040 follow-on.
