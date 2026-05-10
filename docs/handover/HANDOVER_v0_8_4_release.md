# HANDOVER — v0.8.4 release close

**Date:** 2026-05-10
**Tag:** v0.8.4
**Work plan:** `docs/update_workplan_2026-05-10_v0_8_4.md`
**Driving artefacts:** `docs/handover/AUDIT_v0_8_3_ui_completeness.md` (Phase 1, /scientific-advisor) + `docs/handover/ARCH_v0_8_3_ui_decomposition.md` (Phase 2, /architect)

## Summary

v0.8.4 closes the UI-completeness gap between the v0.7 → v0.8.3 backend and the Streamlit dashboard. **All 13 W-items shipped (W-051 … W-063); all 10 new validation gates (28–37) closed.** This release operationalises the README's *screen → calibrate → tighten* promise from the dashboard for the first time.

## Per-batch summary

### B-0i (W-051, W-052) — Decision-grade extension + AST gate

- `core/decision_grade.py`: 3 new `OutputType` members + 3 policy rows (MC_PROBABILITY → SEMI_QUANTITATIVE; POSTERIOR_PARAMETER → SEMI_QUANTITATIVE per ADR-010; ESS → QUALITATIVE_TREND).
- `tests/test_v9_3_enum_comparison_enforcement.py`: AST scanner extended to enforce `.value` comparisons on `IsothermChoice` + `OutputType`.

### B-1p (W-053, W-054) — Mobile-phase widget + lifecycle override

- NEW `panels/mobile_phase.py`: 5-field T_C / c_NaCl / glycerol / ethanol / μ-override editor.
- `lifecycle/orchestrator.py:781`: optional `MobilePhase` override added; default preserves v0.7 behaviour.
- Resolves audit defect **C1** (the most consequential single defect — pre-flight envelope used silent PBS defaults).

### B-1q (W-055, W-056) — Isotherm selector + plots_m2 tier-gating

- NEW `panels/isotherm_selector.py`: `IsothermChoice` enum + `IsothermSpec` frozen dataclass + 5 conditional sub-forms + family-aware default routing.
- `plots_m2.plot_surface_area_comparison`: optional `tier=` kwarg routing through `render_decision_grade_annotation`.
- Resolves **C2** + **C8**.

### B-1r (W-057, W-058) — Calibration ingestion + tier banner

- NEW `tabs/calibration/wetlab_ingestion.py`: clearly-labelled YAML uploader + tier-promotion preview before commit.
- NEW `shell/tier_banner.py`: persistent 3-state banner surfacing the README guardrail at every stage.
- Resolves **C6** + **W-1**.

### B-2s (W-059, W-060) — KEYSTONE: tab_calibration + forward MC + inverse

- NEW `tabs/tab_calibration.py`: top-level Calibration & Uncertainty stage with 4 sub-tabs.
- NEW `tabs/calibration/forward_mc.py`: forward MC runner + 3-band p_blocker advisory chip.
- NEW `tabs/calibration/inverse_inference.py`: measurement-table editor + ESS chip + posterior bands + log_cov round-trip.
- Resolves **C3** + **C4**.

### B-2t (W-061) — Multi-column series builder

- NEW `tabs/calibration/multi_column.py`: per-column `st.data_editor` + series envelope runner + bottleneck-column highlight.
- Resolves **C5**.

### B-2u (W-062, W-063) — RecoveryAction timeline + next-step affordance

- `tab_m3_monitor.py`: per-rule timeline ribbon + rule-frequency expander.
- NEW `components/next_step_affordance.py`: 3-button "what's next" strip writing the cross-tab jump flag.
- Resolves **C9** + **W-2**.

## Commit chain

```
5dab960 B-2u: RecoveryAction timeline + next-step affordance (W-062, W-063, v0.8.4)
c77c904 B-2t: multi-column series builder UI (W-061, v0.8.4)
31f95d5 B-2s KEYSTONE: tab_calibration + forward MC + inverse Bayesian (W-059, W-060, v0.8.4)
ff577c2 B-1r: tier banner + wet-lab YAML ingestion (W-057, W-058, v0.8.4)
61aad8d B-1q: isotherm selector + plots_m2 tier-gating (W-055, W-056, v0.8.4)
cefe8a8 B-1p: mobile-phase widget + lifecycle MobilePhase override (W-053, W-054, v0.8.4)
36eba4c B-0i: decision_grade extensions + AST gate (W-051, W-052, v0.8.4)
```

## Verification

- 130+ new tests across the seven batches; 104/104 visualization tests pass at v0.8.4 close.
- ruff + mypy clean across all changed paths.
- AST gate: 0 violations on the extended (IsothermChoice + OutputType) enum coverage.

## Validation gates closed (28–37)

All 10 introduced by this plan, summarised in §4.2 of the work plan and the §"Public-communication framing" of the CHANGELOG.

## Public-communication framing

> **v0.8.4 ships as "UI-completeness-closed against the v0.8.3 backend".** Every scientifically meaningful capability shipped in the v0.7.0 → v0.8.3 cluster is now reachable from the dashboard. Tier promotion to CALIBRATED_LOCAL remains a wet-lab-driven path; v0.8.4 ships the *machinery* but not the wet-lab handshake.

## Open future work — exclusively v0.9 candidates

The three hardware/physics deferrals are now the only remaining items in the cumulative open list:

- **AKTA UNICORN live socket backend** — implements the v0.8.2 `MonitorSource` Protocol per ADR-008. Hardware-bound.
- **Cyclic SMB / multi-bed dynamics** — ADR-009 deferral. Substantial physics scope.
- **MCMC inverse inference** — ADR-010 promotion target. Awaiting datasets that warrant the `pymc` cold-import cost.

Plus user-side:

- **Wet-lab calibration of K_geom / ν** — promotes outputs from SEMI_QUANTITATIVE to CALIBRATED_LOCAL via the new ingestion panel. User-driven; not a code deliverable.
