# DPSim v0.8.1 — Salt-aware elution + plotly annotation tier-gating

**Date:** 2026-05-10 (same day as v0.7.0 / v0.8.0 ship)
**Author:** `/dev-orchestrator` (continuation of the v0.8.0 plan)
**Inputs inherited:** `docs/handover/HANDOVER_incremental_close_2026-05-04.md` §"Future scientific scope" items 1 + 3
**Target release:** v0.8.1 (patch bump per the user's versioning policy — minor bumps reserved for matured-status milestones)
**Mode:** project plan; execution interleaved

---

## 1. Scope — two long-deferred items from the 2026-05-04 incremental close

The 2026-05-04 incremental close handover §"Future scientific scope (requires Scientific Advisor + ADR)" listed:

1. **Salt-dependent isotherm physics** — stoichiometric displacement model (SDM) or Mollerup-style ion-exchange. The B-2e scaffolding (`LoadedStateElutionResult.gradient_diagnostics`) has been ready since v0.6.6; the consumer wire-up was deferred pending a science decision and ADR.
3. **B-1b plot annotations** — wire `decision_grade` decisions into plotly chart annotations (not just `st.metric` widgets). UX exploration; lower priority.

(Item 2 — IMAC imidazole competition — remains deferred to v0.9 because it requires a separate isotherm class, not just an adapter layer.)

This v0.8.1 plan operationalizes both items. Item 1 ships the **science decision (ADR-005) + Mollerup-simplified salt modulator** wired through the loaded-state elution. Item 2 ships **`render_decision_grade_annotation`** alongside the existing `render_metric` and applies it to the M3 chart family.

## 2. Work item ledger — W-034 + W-035

| ID | Severity | Title | Files affected | Bundle |
|---|---|---|---|---|
| **W-034** | HIGH | Salt-aware K_a wired through loaded-state elution | `docs/decisions/ADR-005-salt-dependent-isotherm.md` (NEW), `module3_performance/isotherms/salt_dependent.py` (NEW), `module3_performance/method.py` (rhs salt-modulation branch + `salt_at_time` mirror of `ph_at_time`), 12+ tests | A |
| **W-035** | LOW | Tier-aware plotly annotation helper + M3 chart wire-up | `visualization/decision_grade_render.py` (add `render_decision_grade_annotation` + `format_decision_graded` already exists), `visualization/plots_m3.py` (DBC + Q_max + gradient-badge sites), 10+ tests | B |

### 2.1 BLOCKER classification

None. Both are scoped, additive, and reversible.

## 3. Sequenced batches

| Batch | IDs | Modules | Model tier | Notes |
|---|---|---|---|---|
| **B-0f** *Plan + ADR-005* | (this doc) + ADR-005 | `docs/decisions/ADR-005-salt-dependent-isotherm.md` | n/a | The science decision: Mollerup-simplified single-component salt modulator (functionally identical to SDM in the dilute limit), tier `SEMI_QUANTITATIVE` until ν calibrated wet-lab. The full SMA isotherm (already in `isotherms/sma.py`) is documented as the eventual promotion path. |
| **B-1j** *(W-034)* | W-034 | NEW `isotherms/salt_dependent.py`; extend `method.py` rhs with a salt-modulator factor mirroring `_protein_a_elution_suppression`; tests | **Sonnet** | The minimum-touch wire-up. The factor is `(c_salt_ref / c_salt_t) ** ν` per Mollerup formalism, applied multiplicatively to the existing isotherm equilibrium_loading. Returns 1.0 when no salt gradient is active — no behavior change for non-salt elution paths. |
| **B-1k** *(W-035)* | W-035 | `decision_grade_render.py` + `plots_m3.py` + tests | **Sonnet** | Pure UX. Tier-aware fig.add_annotation that renders NUMBER / INTERVAL / RANK_BAND / SUPPRESS in the plotly chart's annotation layer, mirroring the existing `render_metric` policy. |
| **B-3f** *Release* | — | `pyproject.toml` (0.8.0 → 0.8.1), CHANGELOG, handovers | n/a | Patch bump. |

## 4. Validation gates introduced by v0.8.1

- **Gate 12: salt-driven elution dynamics are physics-aware.** Closed when B-1j lands. The previous v0.8.0 state was: salt gradient envelope was in `gradient_diagnostics` but did not drive the isotherm. After v0.8.1, the elution rhs sees the active salt concentration at time t and modulates K_a via the Mollerup factor. Tier remains SEMI_QUANTITATIVE until manufacturer / wet-lab ν values land in the calibration store.
- **Gate 13: plotly annotations are tier-gated.** Closed when B-1k lands. Plot overlays no longer assert tier-blind numeric badges; values are formatted through the same decision-grade ladder that gates `st.metric` widgets.

## 5. What v0.8.1 does *not* attempt

- Full SMA mass-action solve at every timestep — that's the eventual promotion path documented in ADR-005, but it requires per-rhs fixed-point iteration on the bound counterion concentration. Costly enough to defer until wet-lab ν / σ data demand the precision.
- IMAC imidazole-competition isotherm — analogous physics scope; v0.9 candidate.
- Multi-component competitive-IEX — out of scope until single-component path is validated.
- Plotly annotation tier-gating in non-M3 modules (e.g., M1 PBE plots) — incremental work; v0.8.2 if useful.

## 6. Handover targets

- `docs/handover/HANDOVER_v0_8_1_b1j_salt_modulator.md` — at end of B-1j
- `docs/handover/HANDOVER_v0_8_1_b1k_plotly_annotations.md` — at end of B-1k
- `docs/handover/HANDOVER_v0_8_1_release.md` — at v0.8.1 tag

---

### Disclaimer

> v0.8.1 ships the Mollerup-simplified salt modulator at SEMI_QUANTITATIVE tier with literature-anchored ν defaults. Quantitative protein-specific elution recoveries require local wet-lab calibration of ν, ν / charge, and the reference salt concentration. The plotly annotation extension is purely cosmetic — it does not change any numerical computation.
