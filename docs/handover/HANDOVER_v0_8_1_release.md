# HANDOVER — v0.8.1 release close

**Date:** 2026-05-10 (same day as v0.7.0 / v0.8.0 ship — patch cluster)
**Tag:** v0.8.1
**Work plan:** `docs/update_workplan_2026-05-10_v0_8_1.md`

## Summary

v0.8.1 closes the two long-deferred items from the 2026-05-04
incremental-close handover §"Future scientific scope":

- **W-034 (B-1j):** salt-dependent isotherm physics — Mollerup-simplified
  salt modulator (ADR-005) wired through the `EquilibriumAdapter` so
  `run_gradient_elution` consumes the salt envelope at every rhs step.
- **W-035 (B-1k):** plotly annotation tier-gating — DBC values and
  Q_max badges now route through the same decision-grade ladder that
  gates `st.metric` widgets.

Per the user's versioning policy stated 2026-05-10: minor bumps are
reserved for matured-status milestones; ordinary feature batches
should be patch bumps. v0.9 stays available for a meaningful plateau.

## Commit chain

```
48603cc B-1k: plotly annotation tier-gating (W-035, v0.8.1)
1184505 B-1j: salt-modulated Langmuir adapter (W-034, v0.8.1)
9cdc0fb (tag: v0.8.0) release: v0.8.0 — pressure-envelope operationalization
fa159c8 B-2j: pressure-feasibility BO constraint (W-033, v0.8.0)
1aa9ac3 B-2i: streaming pressure-monitor UI + CSV-replay (W-032, v0.8.0)
4d21290 B-1i: remove deprecated max_safe_flow_rate (W-031, v0.8.0)
```

## Verification

- 269 tests passing in v0.8.1-relevant scope (visualization + module3_performance), plus the 681 from v0.8.0-relevant scope unchanged.
- ruff + mypy clean across all changed paths.
- AST gate: no new `is` / `is not` comparisons against managed enums.

## Validation gates closed in this release

- **Gate 12:** salt-driven elution dynamics are physics-aware (B-1j).
- **Gate 13:** plotly annotations are tier-gated (B-1k).

## Public-communication framing

> v0.8.1 ships the Mollerup-simplified salt modulator at SEMI_QUANTITATIVE tier with literature-anchored ν defaults. Quantitative protein-specific elution recoveries require local wet-lab calibration. The plotly annotation extension is purely cosmetic — it does not change any numerical computation; it ensures chart labels carry the same evidence-tier caveats as metric widgets.

## Cumulative open future-work items (post-v0.8.1)

These items remain deferred, candidates for the eventual v0.9 matured-status plateau:

- **Live AKTA UNICORN integration** — WebSocket bridge to UNICORN data stream (v0.9 epic from v0.8.0 plan).
- **Multi-step pressure feasibility** — worst-case BO drop across load / wash / elute / CIP (v0.8.0 §6).
- **Multi-column / SMB pressure modelling** (v0.7.0 §6).
- **Bayesian uncertainty propagation through the envelope** (v0.7.0 §6).
- **Channeling auto-recovery** — currently only detected, not auto-handled (v0.7.0 §6).
- **Full SMA promotion** — replace the Mollerup-simplified salt modulator with the per-rhs fixed-point SMA solver once wet-lab ν / σ data warrants the cost (v0.8.1 §5 / ADR-005 §"Out of scope").
- **IMAC imidazole-competition isotherm** — analogous physics scope to W-034 (2026-05-04 future scope item 2).
- **Multi-component competitive IEX elution** (v0.8.1 §5).
- **M1/M2 plot tier-gating** — symmetric extension of W-035 to non-M3 plot families (v0.8.1 §5).
- **Wet-lab calibration of K_geom / ν** — gates promotion to CALIBRATED_LOCAL (user-side).
- **Pre-existing `confidence_tier` test stale-field fix** in `test_breakthrough_inherits_fmc_qualitative_tier` (one-line fix; cosmetic).
