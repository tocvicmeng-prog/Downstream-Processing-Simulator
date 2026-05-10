# DPSim v0.8.3 — Pure-coding open work close (post-v0.8.2)

**Date:** 2026-05-10 (continuing the same-day patch cluster)
**Author:** `/dev-orchestrator`
**Inputs inherited:** `HANDOVER_v0_8_2_release.md` §"Open future work after v0.8.2"
**Target release:** v0.8.3 (patch bump per the project versioning policy)

---

## 1. Scope — close every remaining pure-coding item

The v0.8.2 release handover catalogued 6 open items. Of these:

- **2 are bound on hardware or deep physics, deferred to v0.9** —
  - AKTA UNICORN live socket bridge (ADR-008): hardware access required.
  - Cyclic SMB / multi-bed dynamics (ADR-009): substantial physics scope; ADR-009 explicitly defers.
- **1 is user-side and not a code deliverable** — wet-lab K_geom / ν calibration.
- **3 are pure code work** — eligible for a patch close in this batch:
  - Inverse Bayesian inference (ADR-007 §"Out of scope" — inverse path).
  - Per-family priors for the MC envelope.
  - Correlated MC priors + multi-step coupled MC propagation (ADR-007 §"Out of scope" lists both).
- **1 was conditionally-deferred, conditional now met** — M2 plot/widget tier-gating: `tab_m2.py:744-745` has 2 raw `st.metric` calls for G_DN / E_star that are `OutputType.MODULUS` candidates. Conditional from v0.8.2 §"Open future work" is satisfied.

Plus a small cleanup: split correlated MC + multi-step coupled MC since
they're independent and ship cleanly separately.

## 2. Work item ledger — W-046 … W-050

| ID | Severity | Title | Files affected | ADR |
|---|---|---|---|---|
| **W-046** | LOW | M2 widget tier-gating (G_DN / E_star metrics) | `visualization/tabs/tab_m2.py` (route through `render_metric`) | — |
| **W-047** | HIGH | Inverse Bayesian inference via importance sampling | NEW `module3_performance/pressure_envelope_inverse.py`; ADR-010 | ADR-010 |
| **W-048** | MEDIUM | Per-family MC priors registry | `module3_performance/pressure_envelope_mc.py` (extend with `FAMILY_MC_PRIORS`) | (extends ADR-007) |
| **W-049** | MEDIUM | Correlated MC priors via covariance matrix | `module3_performance/pressure_envelope_mc.py` (add `log_cov` argument); ADR-011 | ADR-011 |
| **W-050** | MEDIUM | Multi-step coupled MC propagation | NEW `monte_carlo_step_program` in `pressure_envelope_mc.py` | (extends ADR-007 / W-040) |

## 3. Sequenced batches

| Batch | IDs | Modules | Notes |
|---|---|---|---|
| **B-0h** | this plan + ADR-010 + ADR-011 | docs only | Single-shot scoping commit. |
| **B-1o** *(W-046)* | W-046 | `tab_m2.py` | 2-line edit + tests. |
| **B-2o** *(W-047)* | W-047 | NEW `pressure_envelope_inverse.py`; ADR-010 | Importance-sampling posterior inference (NOT MCMC; ADR-010 documents why). |
| **B-2p** *(W-048)* | W-048 | extend `pressure_envelope_mc.py` | Family priors registry + auto-routing. |
| **B-2q** *(W-049)* | W-049 | extend `pressure_envelope_mc.py`; ADR-011 | Covariance-matrix sampling path. |
| **B-2r** *(W-050)* | W-050 | extend `pressure_envelope_mc.py` | New `monte_carlo_step_program` keeps draw-once semantics. |
| **B-4b** | — | release tag | Patch bump. |

## 4. Validation gates introduced by v0.8.3

- **Gate 23:** M2 widget annotations carry tier labels (B-1o).
- **Gate 24:** Inverse pressure-envelope inference is reachable from one constructor (B-2o + ADR-010). Wet-lab promotion path remains user-side (per ADR-007 §"Tier mapping"); v0.8.3 ships the *machinery*, not the promotion.
- **Gate 25:** MC envelope honours per-family priors (B-2p).
- **Gate 26:** MC envelope accepts an explicit covariance matrix (B-2q + ADR-011).
- **Gate 27:** MC envelope produces a coupled multi-step program with shared draws (B-2r).

## 5. What v0.8.3 does *not* attempt

- **Live AKTA UNICORN socket bridge** — hardware-bound (ADR-008). v0.9 candidate.
- **Cyclic SMB dynamics** — physics-deep (ADR-009). v0.9 candidate.
- **MCMC inverse inference** — ADR-010 chooses importance sampling over MCMC for v0.8.3; MCMC promotion is a v0.8.4+ candidate when measurement datasets are large enough that ESS becomes a binding constraint.
- **Wet-lab K_geom / ν calibration** — explicitly user-side; not a code deliverable.

## 6. Handover targets

- `docs/handover/HANDOVER_v0_8_3_release.md` — single combined release-level handover (continuing the v0.8.2 consolidation pattern; per-batch detail consolidated to keep the handover surface manageable across the rapid same-day patch cluster).

## 7. New ADRs

- **ADR-010** — Inverse pressure-envelope inference: importance sampling vs MCMC.
- **ADR-011** — Correlated MC priors: covariance specification + drawing.

---

### Disclaimer

> v0.8.3 closes the remaining pure-coding items from the v0.8.2 cumulative open list. The hardware-bound (AKTA UNICORN) and physics-deep (cyclic SMB) items are explicitly deferred to v0.9, where the maturity plateau is defined. Inverse inference ships SEMI_QUANTITATIVE — it produces a posterior under prior assumptions, but does not auto-promote tier without a wet-lab calibration handshake.
