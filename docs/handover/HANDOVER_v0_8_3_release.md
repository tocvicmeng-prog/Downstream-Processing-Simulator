# HANDOVER — v0.8.3 release close

**Date:** 2026-05-10 (continuing the same-day patch cluster)
**Tag:** v0.8.3
**Work plan:** `docs/update_workplan_2026-05-10_v0_8_3.md`

## Summary

v0.8.3 closes 5/5 pure-coding items remaining from the v0.8.2 cumulative open list. AKTA UNICORN live socket and cyclic SMB dynamics stay v0.9 candidates per ADR-008 / ADR-009. Wet-lab K_geom / ν calibration is user-side. Patch bump per the project versioning policy.

## Per-batch summary

### B-1o (W-046) — M2 widget tier-gating

| File | Change |
|---|---|
| `src/dpsim/visualization/tabs/tab_m2.py` | Two raw `st.metric` calls (lines 744-745) for `G_DN_updated` and `E_star_updated` now route through `render_metric` with `OutputType.MODULUS` and the FunctionalMicrosphere's `model_manifest.evidence_tier`. Defensive fall-through to SEMI_QUANTITATIVE when no manifest. |

### B-2o (W-047) — Inverse Bayesian inference + ADR-010

| File | Change |
|---|---|
| `docs/decisions/ADR-010-inverse-pressure-envelope-inference.md` | NEW — choice of importance sampling over MCMC for v0.8.3. |
| `src/dpsim/module3_performance/pressure_envelope_inverse.py` | NEW — `infer_posterior_envelope` + `MeasuredPressureFlowPoint` + `InferredPosteriorEnvelope`. ESS diagnostic + warning. Posterior log_cov consumable by the W-049 forward-MC log_cov path. |
| `tests/module3_performance/test_pressure_envelope_inverse.py` | NEW — 14 tests. |

### B-2p (W-048) — Per-family MC priors

| File | Change |
|---|---|
| `src/dpsim/module3_performance/pressure_envelope_mc.py` | New `FamilyMCPrior` dataclass + `_FAMILY_MC_PRIORS` registry + `lookup_family_mc_prior` helper. `monte_carlo_pressure_envelope` gains `use_family_priors=False` flag; `sigma_log_*` args become `Optional[float]` with `None` as fall-back sentinel. |

### B-2q (W-049) — Correlated MC priors + ADR-011

| File | Change |
|---|---|
| `docs/decisions/ADR-011-correlated-mc-priors.md` | NEW — covariance specification, parameter order, validation contract. |
| `src/dpsim/module3_performance/pressure_envelope_mc.py` | New `log_cov: Optional[np.ndarray]` argument. Shape / symmetry / PSD validation. Multivariate-normal sampling path when supplied; v0.8.2 independent path preserved when `log_cov is None`. |

### B-2r (W-050) — Multi-step coupled MC

| File | Change |
|---|---|
| `src/dpsim/module3_performance/pressure_envelope_mc.py` | New `monte_carlo_step_program` draws N parameter triples ONCE and re-uses them across all steps. Returns `StepProgramMCResult` (per-step `MCEnvelopeBands` + `worst_step_p_blocker` + `worst_step_index`). Honours `use_family_priors` + `log_cov`. |

### Combined tests for B-2p + B-2q + B-2r

| File | Change |
|---|---|
| `tests/module3_performance/test_mc_family_priors_and_cov.py` | NEW — 12 tests for W-048 + W-049. |
| `tests/module3_performance/test_mc_step_program.py` | NEW — 10 tests for W-050. |

## Commit chain

```
b4adbb0 B-2r: multi-step coupled MC propagation (W-050, v0.8.3)
71c7720 B-2p + B-2q: per-family MC priors + correlated MC priors (W-048 + W-049, v0.8.3)
fc7ba4f B-2o: inverse Bayesian inference via importance sampling (W-047, v0.8.3) + ADR-010
1636bbf B-1o: M2 widget tier-gating (W-046, v0.8.3)
997160f B-0h: v0.8.3 plan + ADR-010 + ADR-011
```

## Aggregate verification

- 36 new tests across W-047 / W-048 / W-049 / W-050; plus 4 for W-046.
- ruff + mypy clean on all new source files.
- AST gate: no new `is` / `is not` comparisons against managed enums.

## Validation gates closed

- **23:** M2 widget annotations carry tier labels.
- **24:** Inverse pressure-envelope inference is reachable from one constructor.
- **25:** MC envelope honours per-family priors.
- **26:** MC envelope accepts an explicit covariance matrix.
- **27:** MC envelope produces a coupled multi-step program with shared draws.

## Public-communication framing

> v0.8.3 closes the residual pure-coding items from the v0.8.2 cumulative open list. Hardware-bound (AKTA UNICORN — ADR-008) and physics-deep (cyclic SMB — ADR-009) items remain v0.9 candidates. Wet-lab K_geom / ν calibration stays user-side. None of the new modules ship above SEMI_QUANTITATIVE tier; the inverse-inference module ships the *machinery* for posterior fitting, not the wet-lab handshake that promotes the tier.

## Open future work after v0.8.3 (potential v0.9 candidates)

- **AKTA UNICORN live socket backend** — implements `MonitorSource` per ADR-008. Hardware-bound.
- **Cyclic SMB / multi-bed dynamics** — port-rotation, displacement coupling, time-varying envelope. ADR-009 deferral.
- **MCMC inverse inference** — promotion path from importance sampling per ADR-010 §"Why not MCMC".
- **Family-specific covariance registries** — ADR-011 §"Out of scope".
- **Tier auto-promotion to CALIBRATED_LOCAL** based on inverse-inference posterior fit + wet-lab handshake.
- **Wet-lab calibration of K_geom / ν** — user-side; gates the auto-promotion above.
- **Hierarchical / multi-column inference** — ADR-010 §"Out of scope". Each column gets its own posterior in v0.8.3.

The v0.9 maturity plateau is shaped by these items: when wet-lab data lands, calibration auto-promotion + MCMC inference + UNICORN bridge form a coherent matured-status release.
