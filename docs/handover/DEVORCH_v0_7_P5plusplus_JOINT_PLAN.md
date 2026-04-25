# Milestone Handover: M-PLAN-v0.3 — P5++ MC-LRM Joint Plan

**Date:** 2026-04-25
**Session:** v0.3-PLAN-001 (initial)
**Project:** Downstream-Processing-Simulator (DPSim)
**Prepared by:** /dev-orchestrator (with /architect technical decomposition; based on /scientific-advisor brief that resolved G1-08 + G1-09)
**Classification:** Internal — Development Handover

**Companion documents (must accompany this plan):**
- `docs/p5_plus_plus_protocol.md` — original /architect G1 readiness skeleton (PARTIAL PASS 10/12; v0.6-era)
- `docs/handover/SA_v0_7_P5plusplus_BRIEF.md` — SA Mode-1 design-realisation brief (resolves G1-08 + G1-09; promotes G1 → 12/12 FULL PASS)
- `docs/handover/ARCH_v0_7_P5plusplus_DECOMPOSITION.md` — /architect module-level decomposition + DAG + per-module acceptance tests + plan-level D1–D6 audit

---

## 1. Executive Summary

The Scientific Advisor's Mode-1 brief on the P5++ initiative resolved both deferred G1 items from the original protocol (G1-08 numerical-stability and G1-09 test inventory). The Architect then decomposed the initiative into **5 implementation modules** spanning **3 sequential milestones**:

- **v0.3.0** — G1 (`PosteriorSamples`) + G2 (`MonteCarloDriver`) + G3 (`MethodSimulationResult` MC dispatch). The MC-LRM driver core. Critical-path. ~32 k inner-loop tokens; single-session feasible.
- **v0.3.1** — G4 (`bayesian_fit`) optional, behind `pip install dpsim[bayesian]`. Independent of v0.3.0 critical path; can land any time after G1.
- **v0.3.2** — G5 (UI band rendering + ProcessDossier MC serialisation). Depends on v0.3.0 close.

The cycle inherits the v0.2.0 functional-optimization initiative's pattern (architectural pre-work in M0a/M0b, then per-batch milestones) but is **structurally different**: P5++ is novel numerical method (MC over stiff ODE) rather than additive library extension. Tier-1 modules per cycle: 1–3 (vs 18 for v0.2.0). Wall-time per MC realisation set: hours (vs ms for v0.2.0).

**Where we are now:** plan finalized; no code modules implemented yet. This is the planning-phase handover that authorises the v0.3.0 implementation cycle to begin.

**What's next:** Phase-0 pre-flight check at the start of v0.3.0, then execute G1 (`posterior_samples.py`). The G1 next-module protocol is pre-generated in § 12 of this document.

---

## 2. Module Registry — Initial State (v0.3.x cycle)

No modules approved yet. The full proposed registry of 5 modules across 3 milestones is documented in `ARCH_v0_7_P5plusplus_DECOMPOSITION.md` § 3–5. Status of every module: **PENDING**. The registry will be updated to APPROVED status as each module clears Phase 5.

| # | Module | Version | Status | Approved | Model Used | Fix Rounds | Lines | File Path |
|---|---|---|---|---|---|---|---|---|
| — | — | — | PENDING | — | — | — | — | — |

(Empty initial state — registry table format is Reference 04 § 3.)

---

## 3. Integration Status — Initial State

| Interface | From Module | To Module | Status | Notes |
|---|---|---|---|---|
| `CalibrationEntry` (existing) | `dpsim.calibration.calibration_data` | future G1 consumer | **LIVE** | v0.2-era schema; v0.2.0 wet-lab ingestion module (commit `0cd047d`) extended it with `target_module`, `fit_method`, `posterior_uncertainty`, `valid_domain` fields. G1 should consume this schema directly rather than reinvent. |
| `CalibrationStore` (existing) | `dpsim.calibration.calibration_store` | future G1 consumer | **LIVE** | v0.2-era; G1's `from_calibration_store()` constructor will read posterior means/stds and (when present) covariance |
| `solve_lrm` (existing) | `dpsim.module3_performance.transport.lumped_rate` | future G2 consumer | **LIVE** | v0.6-era; uses `solve_ivp(method="BDF")` with configurable rtol/atol; documents LSODA stalls on high-affinity Langmuir paths |
| `joblib.Parallel` (existing) | v0.6.0 / E2 | future G2 consumer | **LIVE** | n_jobs parallelism already shipped |
| `MethodSimulationResult` (existing) | `dpsim.module3_performance.method` | future G3 extension | **LIVE** | v0.x consumers must handle new `Optional[MCBands]` field via `is None` check |
| `DSDPolicy` (existing) | `dpsim.datatypes` | future G3 extension | **LIVE** | G3 adds new fields `monte_carlo_n_samples: int = 0` (default off), `monte_carlo_n_seeds: int = 4`, `monte_carlo_parameter_clips: dict | None = None` |
| `PosteriorSamples` (NEW) | G1 (pending) | G2 + G4 consumers | PENDING | Lands with G1 |
| `MCBands` / `ConvergenceReport` (NEW) | G2 (pending) | G3 + G5 consumers | PENDING | Lands with G2 |
| `run_mc()` entrypoint (NEW) | G2 (pending) | G3 dispatch (pending) | PENDING | Lands with G2 |
| `MethodSimulationResult.monte_carlo` (NEW) | G3 (pending) | G5 + ProcessDossier | PENDING | Lands with G3 |
| `fit_langmuir_posterior()` (NEW, optional) | G4 (pending) | G2 alternate input path | PENDING | Lands with G4 (v0.3.1) |
| Plotly band overlay + dossier serialisation (NEW) | G5 (pending) | M3 UI + dossier | PENDING | Lands with G5 (v0.3.2) |

---

## 4. Architecture State

The v0.2.0 architecture is the baseline. The v0.3.x cycle introduces **schema-additive** changes (new `MCBands` dataclass, `Optional[MCBands]` field on `MethodSimulationResult`, three new `DSDPolicy` fields) and **two new modules** (G1 + G2 + G3 are co-located in existing packages but introduce new files). No interfaces are removed; all v0.2.0 functionality is preserved by the smoke-baseline preservation gate (v0.3.0 AC#5).

Architectural changes since the v0.2.0 baseline:
- **None at this point** — this is the planning handover. Architecture changes begin landing with G1.

Architectural changes scheduled by this plan are catalogued in `ARCH_v0_7_P5plusplus_DECOMPOSITION.md` § 3–5.

---

## 5. Design Decisions Log

| # | Decision | Rationale | Date | Alternatives Considered |
|---|---|---|---|---|
| D-044 | Adopt SA-recommended sampler-tier split: LHS / multivariate-normal for G1–G3; pymc + NUTS for G4 only behind optional install | LHS suffices for forward UQ from a known posterior; NUTS is overkill there. NUTS is the right tool for G4's posterior-fitting problem. Optional-install pattern keeps the base install lightweight. | 2026-04-25 | All-pymc baseline (rejected — heavy install for the common path); custom adjoint sensitivity (rejected — duplicates existing P5+ delta-method without addressing the non-linear-regime gap that motivates P5++) |
| D-045 | Reject LSODA fallback for solver failures | The existing LRM code (`lumped_rate.py:372–376`) explicitly documents LSODA stalls on high-affinity Langmuir paths. Falling back to LSODA would trade one failure mode for another, less predictable, one. | 2026-04-25 | LSODA fallback (rejected — codebase has prior negative experience); BDF retry with looser tolerances (rejected — undermines accuracy gate AC#1) |
| D-046 | Adopt Tier-1 numerical safeguards in G2: tail-aware tolerance tightening + abort-and-resample + 5-failure cap; Tier-2 parameter clipping | Posterior tails will fail at ~0.5–1.5% rate per SA brief § 2.2. Abort-and-resample preserves the posterior's central mass while keeping the run alive. The 5-failure cap signals genuine instability vs. one-off outliers. | 2026-04-25 | Strict-failure mode (rejected — would fail many runs at N=1000); silent skip (rejected — biases the posterior toward the centre without recording it) |
| D-047 | Reformulate AC#3 from "R-hat < 1.05" to "quantile-stability plateau + inter-seed posterior overlap ≤ 5%" | R-hat is for correlated MCMC chains. LHS draws are independent by construction; R-hat-on-LHS reduces to a posterior-overlap restatement. Better to compute the right diagnostic by name. | 2026-04-25 | Keep R-hat (rejected — misnamed for the diagnostic actually being computed; would mislead future contributors) |
| D-048 | Marginal-only LHS as default; opt-in covariance via `multivariate_normal` when `CalibrationStore` carries Σ | Conservative-by-default: marginal-only overestimates uncertainty when ρ negative (typical case per Karlsson 1998); the right side to err on for screening claims. Covariance is rare in real calibration data; making it default would surprise users. | 2026-04-25 | Default-covariance mode (rejected — Σ rarely available); imputed-correlation prior (deferred to v0.4+ as enhancement) |
| D-049 | ACCEPT v7-Q3 deferral of bin-resolved DSD × MC to v0.4+ | Two variance sources (parameter, geometric) are largely independent to first order; ~20% second-order coupling bounded for 30–100 µm beads. 7× compute saving for screening-quality bands is the right v0.3 trade-off. | 2026-04-25 | Bundle into v0.3.0 (rejected — 7× walltime; not the v0.3.0 contract); custom adjoint to absorb the cost (rejected per D-044) |
| D-050 (resolves user-item a) | Rename P5++ ship targets v0.7.0/v0.7.1/v0.7.2 → v0.3.0/v0.3.1/v0.3.2 (continuing the fork-line) | Mirrors the v0.2.0 CHANGELOG resolution (D-002 family). The "v0.7.x" labels in the original protocol pre-date the explicit fork-line versioning convention adopted today. Internal G1–G5 module labels are preserved verbatim. | 2026-04-25 | Keep v0.7.x labels (rejected — would re-introduce the upstream-line clash that the v0.2.0 CHANGELOG entry just resolved); use a new label entirely (rejected — v0.3.0 is the natural fork-line MINOR bump from v0.2.0) |
| D-051 (resolves user-item b) | G1's `PosteriorSamples` consumes `CalibrationEntry` from the v0.2.0 wet-lab ingestion module (commit `0cd047d`) directly | Reuse beats reinvention. The wet-lab `CalibrationEntry` schema already carries `target_module`, `fit_method`, `posterior_uncertainty` — exactly what G1 needs. Inverting the relationship (G1 produces a NEW schema, then we'd need to migrate `wetlab_ingestion`) would orphan the ingestion module. | 2026-04-25 | Define an independent G1 schema (rejected — reinvention) |
| D-052 (resolves user-item c) | v0.3.0 milestone scope is FINAL at G1 + G2 + G3 — DO NOT bundle G4 or G5 | G4 (Bayesian fit, ~11 k tokens) and G5 (UI bands, ~7 k tokens) would push v0.3.0 past 50 k inner-loop tokens. Single-session safety margin per Reference 03 § 4 requires single-milestone session at ≤ 40 k. The architect's decomposition § 0.4 token budget pins this constraint. | 2026-04-25 | Bundle G4 (rejected — risks RED-zone overrun); bundle G5 (rejected — depends on G3 close, no compression benefit) |
| D-053 | Pre-allocate ~6 k tokens for milestone handover at v0.3.0 close | Per Reference 04 § 1: every milestone close gets a handover. Budget per Reference 03 § 2 estimator: 3 k–6 k. Use the ceiling. | 2026-04-25 | Skip handover (rejected — violates Reference 04 § 2 mandatory triggers); 3 k tight (rejected — leaves no slack) |

---

## 6. Build Order and Milestones

### 6.1 Milestone-level sequence

| Milestone | Title | Modules | Dependencies | Token est. (full inner-loop) | Recommended order rationale |
|---|---|---|---|---|---|
| **v0.3.0** | MC-LRM driver core | G1 + G2 + G3 | wet-lab ingestion `CalibrationEntry` (LIVE); existing LRM solver; joblib | ~32 k + 6 k handover ≈ 38 k | Critical path; G4/G5 do NOT bundle here per D-052 |
| **v0.3.1** | Optional Bayesian posterior fitting | G4 | G1 (LIVE after v0.3.0) | ~11 k + 4 k handover ≈ 15 k | Independent of v0.3.0 critical path; lands any time after v0.3.0 close. Optional-install pattern (`pip install dpsim[bayesian]`); base install must work without it |
| **v0.3.2** | UI bands + dossier MC serialisation | G5 | G3 (LIVE after v0.3.0) | ~7 k + 3 k handover ≈ 10 k | Surface-level extension; smaller cycle |

**Total v0.3.x cycle estimate:** ~63 k tokens across 3 sessions. v0.3.1 and v0.3.2 can be interleaved or sequenced based on user priority; both depend only on v0.3.0 close.

### 6.2 Within-v0.3.0 build order

Per the architect's DAG (`ARCH_v0_7_P5plusplus_DECOMPOSITION.md` § 6):

```
G1.posterior_samples ──> G2.monte_carlo ──> G3.method_simulation_dispatch
(Sonnet, ~250 LOC)       (Opus protocol +    (Sonnet, ~150 LOC)
                          Sonnet impl,
                          ~400 LOC)
```

Strict sequential order — G2 depends on G1's `PosteriorSamples` interface; G3 depends on G2's `run_mc()` entrypoint.

A milestone-level pre-flight at v0.3.0 start should verify ≥ 60% context (full cycle estimated at 38 k tokens; safety margin × 1.5 = 57 k tokens).

---

## 7. Quality-Gate Enforcement

Per Reference 01 § 9, every module must pass three gates:

### 7.1 Phase 0 — Pre-Flight Checklist (per module)

- [ ] Context budget ≥ 30% estimated remaining after this module's full inner-loop completion (Reference 03 § 1)
- [ ] All upstream dependencies APPROVED (per the DAG in `ARCH_v0_7_P5plusplus_DECOMPOSITION.md` § 6)
- [ ] Model tier selected per Reference 02 § 3 and recorded in registry
- [ ] If module closes a milestone: handover budget ≥ 6 k tokens pre-allocated (Reference 04 § 3)

### 7.2 Phase 1 — Protocol G1 (12-point check)

The Architect generates a Protocol document per module before any code is written. G1-01 through G1-12 (Reference 01 § 3) must all pass. Special attention for v0.3.x:

- **G1-06 numerical considerations**: G2 specifically must document the Tier-1+2 safeguards (tolerance tightening, abort-and-resample, parameter clipping) inline with citations to SA brief § 2.3 and code comments tagged `# SA-Q1` for future contributor traceability.
- **G1-07 unit tests**: each new G1/G2/G3 module declares its test classes from the architect's per-module table (`ARCH_v0_7_P5plusplus_DECOMPOSITION.md` § 3).
- **G1-08 numerical-stability**: closed by SA brief § 2; the architect's protocol must cite the SA brief and include the four risk callouts (R-G2-1 walltime, R-G2-2 N-floor, R-G2-3 safeguard interaction, R-G2-4 joblib determinism).
- **G1-09 test inventory**: closed by SA brief § 7 (~50 tests across G1–G5).
- **G1-11 interface versions**: G3's `MethodSimulationResult.monte_carlo` is a new optional field; the protocol must declare backward-compatibility contract (`Optional[MCBands]` with `default=None`).

### 7.3 Phase 2 — Implementation G2 (10-point check)

Reference 01 § 4 G2-01 through G2-10. Project-specific additions per CLAUDE.md:

- All new code must pass `ruff` (cap = 0) and `mypy` (cap = 0) gates.
- Streamlit-touching modules (G5 only) must use `.value` for enum comparison, never `is`. AST gate at `tests/test_v9_3_enum_comparison_enforcement.py` enforces.
- G2 must NOT introduce a `solve_ivp(..., method="LSODA")` call — D-045 audit rule. Architect's audit checks via `grep -n 'method="LSODA"' src/dpsim/module3_performance/monte_carlo.py` returning empty.
- G2 must use `np.random.default_rng(seed)` per-sample seeding (NOT global `np.random.seed()`) to support the joblib-determinism test (R-G2-4 mitigation).

### 7.4 Phase 3 — Audit G3 (six-dimension)

Reference 01 § 5 D1–D6 plus G3-01 through G3-08. Project-specific audit emphases for v0.3.x:

- **D2 algorithmic**: G2's MC driver carries the largest first-principles attack surface. Every kinetic / stochastic claim cites SA brief § 2–6.
- **D4 performance**: G2's `TestParallelism` (AC#4 enforcement) — wall-time scaling at n_jobs=8 ≤ 5× single LRM solve. Failure here triggers SA escalation per architect § 10.
- **D6 first-principles**: G2's MC vs. delta-method agreement test (AC#1 + AC#2) is the principal scientific-validity gate. The 1% agreement threshold (AC#1) is tight; expect at least one fix-cycle round.

### 7.5 Milestone-level acceptance

A milestone is closed when **all of**:

1. Every module in the milestone is APPROVED in the registry
2. The milestone's acceptance test (per `ARCH_v0_7_P5plusplus_DECOMPOSITION.md` § 7) passes within the documented quantitative tolerance
3. Existing v0.2.0 regression suite passes unchanged (`pytest -q`)
4. CI gates pass (ruff = 0, mypy = 0)
5. v0.3.0 specifically: smoke-baseline bit-identical preservation when `monte_carlo_n_samples=0` (golden-master test in G3.TestDispatch)
6. Milestone handover document produced (Reference 04 template)

---

## 8. Model-Tier Selection Policy (consolidated)

Per Reference 02 § 2, Reference 02 § 3 decision tree, and the per-module assignments in `ARCH_v0_7_P5plusplus_DECOMPOSITION.md` § 8:

| Always Opus (non-negotiable) | Sonnet default | Haiku default |
|---|---|---|
| G2 protocol generation (novel-algorithm; MC over stiff ODE) | G1 protocol + impl (standard scipy/numpy) | (none in v0.3.x — no Haiku-tier modules in this cycle) |
| G4 protocol generation (novel-science; HMC/NUTS) | G2 implementation (once protocol pinned; standard scipy/joblib) | |
| Full six-dimension audit on every module (G1–G5) | G3 protocol + impl (schema-additive + dispatch hook) | |
| Milestone handover at each of v0.3.0/v0.3.1/v0.3.2 | G4 implementation (off-the-shelf pymc API) | |
| | G5 protocol + impl (UI/serialisation) | |

**Aggregate v0.3.x tier counts** (per `ARCH_v0_7_P5plusplus_DECOMPOSITION.md` § 8):
- Opus implementation: 0 modules (G2 has Opus protocol but Sonnet impl)
- Opus protocol generation: 2 (G2, G4)
- Opus audit: 5 (one per module)
- Opus milestone handover: 3 (one per milestone)
- Sonnet implementation: 5 modules
- Sonnet test writing: all of G1–G5 numerical/scientific tests

**Token-savings projection** (per Reference 02 § 5): the cycle is light on Haiku-tier work (no boilerplate modules) but Opus is reserved for protocols + audits + handovers, which is the cheapest viable pattern. Estimated savings vs. all-Opus baseline: ~50–55%, matching the v0.2.0 cycle.

**Upgrade triggers** to be enforced per Reference 02 § 6:
- If G2 audit returns >3 HIGH-severity findings → upgrade G2 implementation to Opus on the next fix round.
- If any module requires >2 fix rounds → flag for tier review on the next milestone.
- If SA escalation fires (per § 10 below) → re-engage /scientific-advisor at Opus.

**Downgrade triggers:** none expected in v0.3.x (no Haiku-tier modules; no cosmetic re-audits).

**Tracking:** the orchestrator updates the Module Registry's `Model Used` and `Fix Rounds` columns at every Phase 5 close.

---

## 9. Dialogue Compression and Context-Budget Policy

Per Reference 03:

### 9.1 Per-session budget zones

The orchestrator tracks budget after every phase close per the running-estimate template in Reference 03 § 5. Compression is triggered when the next planned phase would push the dialogue from YELLOW into RED.

### 9.2 Pre-large-work compression rule for v0.3.x

Modules with estimated full-loop token cost >10 k that require pre-flight compression check:

- **G2** (Opus protocol + Sonnet impl + Opus audit ≈ 14 k inner-loop tokens) — mandatory compression check before G2 protocol-generation start.
- **G4** (Opus protocol + Sonnet impl + Opus audit ≈ 11 k inner-loop tokens) — same rule; G4 lands in its own session per D-052 anyway.

G1 (~10 k), G3 (~6 k), G5 (~7 k) are below the threshold and proceed without pre-compression.

### 9.3 Mandatory milestone-handover compression

At the close of every milestone (v0.3.0 / v0.3.1 / v0.3.2), produce a milestone handover (Reference 04 template). This is a hard rule for v0.3.x — losing a milestone's worth of state would be expensive to reconstruct given the novel numerical method.

### 9.4 Emergency-handover threshold

If the dialogue reaches EMERGENCY (<15%) mid-implementation, produce the abbreviated emergency handover per Reference 03 § 6 / Reference 04 § 5 immediately and end the session. Resume in a new dialogue with the emergency handover plus this plan plus the architect decomposition as context.

---

## 10. Scientific-Advisor Escalation Paths

Per architect `ARCH_v0_7_P5plusplus_DECOMPOSITION.md` § 10 — re-engage /scientific-advisor if any of these surface during v0.3.0 implementation (resolves user-item d):

| Trigger | Response | SA Mode |
|---|---|---|
| Empirical solver failure rate > 2% during G2 implementation testing (SA brief § 2.2 estimated 0.5–1.5%) | Re-engage SA Mode-3 (Detective) — investigate whether tail handling needs Tier-3 (adaptive z-grid) advance from v0.4 | Mode 3 |
| Inter-seed posterior overlap fails > 5% even at N=1000 across 4 seeds | Re-engage SA Mode-1 — the threshold may need calibration; the sampler may have a determinism bug | Mode 1 |
| MC vs delta-method agreement signature in linear regime > 1% (AC#1 fail) | Re-engage SA Mode-3 — bias in sampler, numerical drift in BDF-LRM, or MCBands aggregator bug | Mode 3 |
| MC vs delta-method disagreement in non-linear pH regime < 5% (AC#2 fail) | Re-engage SA Mode-1 — the regime may not be triggering non-linearity; pH_steepness σ may be too low | Mode 1 |
| Bayesian fit (G4) fails NUTS gates on synthetic Langmuir data (R-hat ≥ 1.05 or ESS < N/4) | Re-engage SA Mode-3 — prior mis-specification, data scaling, or pymc backend issue | Mode 3 |
| Joblib parallelism produces non-deterministic results (R-G2-4 violation) | Re-engage SA Mode-1 — may need backend switch (`backend="threading"` vs `backend="loky"`) or per-sample seeding refactor | Mode 1 |

The orchestrator routes SA escalations through the architect (per Reference 06) and updates the Open Questions table (§ 11) for any issue that doesn't immediately resolve.

---

## 11. IP and Constraint Notes

| Constraint | Source | Affects |
|---|---|---|
| Python pin `>=3.11,<3.13` (ADR-001) | Project ADR | All modules; particularly G2 (scipy BDF stability) and G4 (pymc compatibility) |
| Optimization stack pin (botorch / gpytorch / torch) (ADR-002) | Project ADR | None — v0.3.x does not touch the optimisation stack |
| pymc license (Apache 2.0) | Library | G4 only; compatible with project GPL-3.0 |
| `tests/test_v9_3_enum_comparison_enforcement.py` AST gate | v0.2.0 cycle | G5 (the only Streamlit-touching module in v0.3.x) — must use `.value` enum comparison |
| Smoke-baseline preservation (v0.2.0 → v0.3.x) | Project gate | All modules; G3 specifically — `monte_carlo_n_samples=0` must produce byte-identical legacy output |
| ICH Q3D residual-element compliance | Regulatory standard | None directly; v0.3.x does not introduce new chemistry (the existing v0.2.0 CuAAC Cu-residual flag is unaffected) |
| Bayesian extra (`pip install dpsim[bayesian]`) optional install (D-044) | Project policy | G4 only; CI must run both with-pymc and without-pymc paths |

No new IP issues identified at planning phase.

---

## 12. Next Module Protocol — G1 `posterior_samples`

Per Reference 04 § 3 Section 9, the next module's protocol is pre-generated so a fresh dialogue can begin implementation immediately. This satisfies G1-01 through G1-12 (Reference 01 § 3 Phase 1 protocol checklist).

### 12.1 Purpose (G1-01)

Provide a typed `PosteriorSamples` container and sampling primitive for the v0.3.0 Monte-Carlo LRM uncertainty-propagation driver (G2). Bridges the existing `CalibrationEntry` schema (from `dpsim.calibration.calibration_data`) and the v0.2.0 wet-lab ingestion path (from `dpsim.calibration.wetlab_ingestion`) to G2's per-sample LRM solves.

### 12.2 Interface specification (G1-02 + G1-03)

**Module:** `src/dpsim/calibration/posterior_samples.py` (NEW file)

**Public exports:**

```python
@dataclass
class PosteriorSamples:
    parameter_names: tuple[str, ...]      # e.g. ("q_max", "K_affinity", "pH_transition")
    means: np.ndarray                     # shape (n_params,), units carried in source_calibration_entries
    stds: np.ndarray                      # shape (n_params,), marginal σ
    covariance: np.ndarray | None         # shape (n_params, n_params) or None for marginal-only
    source_calibration_entries: list[CalibrationEntry]  # provenance

    @property
    def has_covariance(self) -> bool:
        """True iff a covariance matrix is attached (NOT just diagonal Σ)."""
        ...

    def draw(
        self,
        n: int,
        seed: int = 0,
        method: Literal["lhs", "multivariate_normal", "auto"] = "auto",
    ) -> np.ndarray:
        """Return shape (n, n_params). 'auto' = multivariate_normal if has_covariance else lhs."""
        ...

    def to_dict(self) -> dict: ...

    @classmethod
    def from_dict(cls, d: dict) -> PosteriorSamples: ...

    @classmethod
    def from_calibration_store(
        cls,
        store: CalibrationStore,
        parameter_names: tuple[str, ...],
    ) -> PosteriorSamples:
        """Read posterior means/stds and (when present) covariance from calibration_store."""
        ...

    @classmethod
    def from_marginals(
        cls,
        parameter_names: tuple[str, ...],
        means: np.ndarray,
        stds: np.ndarray,
        source_entries: list[CalibrationEntry] | None = None,
    ) -> PosteriorSamples: ...

    @classmethod
    def from_covariance(
        cls,
        parameter_names: tuple[str, ...],
        means: np.ndarray,
        covariance: np.ndarray,
        source_entries: list[CalibrationEntry] | None = None,
    ) -> PosteriorSamples: ...
```

### 12.3 Algorithm (G1-04 + G1-05 + G1-06)

**LHS path** (default for marginal-only): use `scipy.stats.qmc.LatinHypercube(d=n_params, seed=seed)` to produce a unit-cube design, then transform via the inverse-CDF of `scipy.stats.norm(mean, std)` per parameter. Time complexity: O(n × n_params). Space: O(n × n_params). Numerically stable across the entire posterior support.

**Multivariate-normal path** (covariance available): use `np.random.default_rng(seed).multivariate_normal(means, covariance, size=n)`. Time complexity: O(n × n_params²) for the Cholesky factorisation + O(n × n_params) for the draws. Space: O(n × n_params + n_params²). Stable under positive-definite Σ; raises `np.linalg.LinAlgError` on ill-conditioned Σ.

**Auto-detection rule**: `method="auto"` returns `multivariate_normal` if `self.has_covariance` else `lhs`. Explicit override available for testing.

Pseudocode for `draw()`:

```
def draw(n, seed, method):
    method = resolve_method(method, self.has_covariance)
    rng = np.random.default_rng(seed)
    if method == "lhs":
        sampler = scipy.stats.qmc.LatinHypercube(d=len(parameter_names), seed=seed)
        u = sampler.random(n)                              # (n, n_params), uniform in [0, 1)
        return scipy.stats.norm.ppf(u, loc=means, scale=stds)
    elif method == "multivariate_normal":
        return rng.multivariate_normal(means, covariance, size=n)
    else:
        raise ValueError(f"Unknown method {method!r}")
```

**Numerical considerations**: `scipy.stats.norm.ppf` returns `+/- inf` for u in `{0, 1}`; `LatinHypercube` does not produce exact 0 or 1 by construction (sampled in centred sub-intervals). No clipping needed at this layer.

### 12.4 Error handling (G1-09)

| Condition | Detection | Response |
|---|---|---|
| `parameter_names` empty or duplicate | Constructor `__post_init__` | Raise `ValueError` |
| `means.shape != (n_params,)` | Constructor `__post_init__` | Raise `ValueError` with shape mismatch detail |
| `stds.shape != (n_params,)` or any `< 0` | Constructor `__post_init__` | Raise `ValueError` |
| `covariance.shape != (n_params, n_params)` or non-PSD | Constructor `__post_init__` | Raise `ValueError` (PSD check via `np.linalg.cholesky` round-trip) |
| `draw(n=0)` | `draw()` | Raise `ValueError("n must be > 0")` |
| `from_calibration_store` cannot find a parameter name | `from_calibration_store` | Raise `KeyError` with the missing name |

### 12.5 Test cases (G1-07 + G1-08 — 12 tests, per architect § 3.1)

| Class | Test | Concrete check |
|---|---|---|
| `TestPosteriorSamplesSchema` | `test_marginal_construction_valid` | `from_marginals(("a","b"), [1,2], [0.1,0.2])` returns object with `has_covariance=False` |
| | `test_covariance_construction_valid` | `from_covariance(("a","b"), [1,2], [[0.01,0],[0,0.04]])` returns object with `has_covariance=True` |
| | `test_schema_validation_rejects_bad_inputs` | Mismatched shape, negative std, non-PSD Σ each raise `ValueError` |
| | `test_round_trip_to_from_dict` | `from_dict(samples.to_dict())` recovers all fields |
| `TestLHSDraw` | `test_reproducibility_under_fixed_seed` | Two `draw(100, seed=42)` calls return identical arrays |
| | `test_correct_shape` | `draw(50)` returns `(50, n_params)` |
| | `test_matches_scipy_lhs_reference` | Direct `LatinHypercube` call with same seed produces same uniform design after inverse-CDF transform |
| | `test_lhs_variance_reduction_vs_iid_at_low_n` | At n=20, LHS Monte-Carlo error on a known integral is < IID Monte-Carlo error (factor ≥ 1.5; cite McKay 1979) |
| `TestMultivariateNormalDraw` | `test_sample_mean_recovery` | At n=10000, fitted mean within 1% of true mean |
| | `test_sample_covariance_recovery` | At n=10000, fitted Σ within 5% of true Σ |
| | `test_reproducibility_under_fixed_seed` | Two `draw(100, seed=42, method="multivariate_normal")` calls return identical arrays |
| `TestCalibrationStoreIngestion` | `test_from_calibration_store` | Mock `CalibrationStore` with two parameters; `from_calibration_store()` correctly extracts means/stds and covariance (when present) |

### 12.6 Performance budget (G1-10)

- `draw(n=1000)` LHS path: ≤ 5 ms wall-time on CI runner.
- `draw(n=1000)` multivariate-normal path: ≤ 10 ms.
- Memory: ≤ 8 × n × n_params bytes (float64).

### 12.7 Dependencies (G1-11)

- **Upstream**: scipy ≥ 1.12 (for `scipy.stats.qmc.LatinHypercube`); numpy; existing `dpsim.calibration.calibration_data.CalibrationEntry`.
- **Downstream**: G2 (`run_mc()`) consumes via the public interface in § 12.2.

### 12.8 Logging and monitoring (G1-12)

- `logger = logging.getLogger("dpsim.calibration.posterior_samples")` at module level.
- `INFO` log on `from_calibration_store` extraction with parameter names + has_covariance flag.
- `WARNING` log when `method="auto"` falls back to LHS because covariance is absent (helps users notice they're getting marginal-only).

### 12.9 Model selection

- Tier: **Sonnet** (Tier 2 — standard scipy/numpy primitives; no novel math; clear interface)
- Rationale: 50–250 LOC, well-bounded; matches Reference 02 § 4 standard implementation profile
- Complexity: MEDIUM — the dispatch logic (auto + explicit) and the `from_*` constructors carry moderate branching

### 12.10 Estimated tokens

~1.8 k protocol + ~1.0 k implementation + ~0.8 k tests + ~1.5 k audit + ~0.8 k handoff = **~5.9 k total** (close to architect's § 0.4 estimate of 6.5 k).

---

## 13. Context Compression Summary

This is the planning-phase handover; no implementation context to compress yet.

**Carry forward verbatim:**
- The Module Registry initial state (§ 2)
- The Integration Status table (§ 3)
- The Design Decisions log D-044 through D-053 (§ 5)
- The build order (§ 6) and milestone-acceptance gates (§ 7.5)
- The model-tier policy (§ 8)
- The pre-large-work compression list (§ 9.2)
- The SA escalation paths (§ 10)
- The G1 next-module protocol (§ 12)

**Compressed (one-line summaries):**
- Scientific-Advisor brief recommendations (full at `SA_v0_7_P5plusplus_BRIEF.md`).
- Architect module decomposition (full at `ARCH_v0_7_P5plusplus_DECOMPOSITION.md`).
- Original P5++ protocol's detailed scientific rationale (full at `docs/p5_plus_plus_protocol.md`).

**Dropped:** None (this is the initial handover; nothing to drop).

---

## 14. Model Selection History

| Task | Model Used | Tokens (est.) | Outcome |
|---|---|---|---|
| Scientific Advisor brief (Mode 1) | Opus | ~5 k | Resolved G1-08 + G1-09; promoted protocol to 12/12 FULL PASS |
| Architect module decomposition | Opus | ~7 k | Produced 5-module decomposition with DAG, model tiers, plan-level D1–D6 audit |
| Dev-Orchestrator joint plan assembly | Opus | ~6 k | This document |

**Total tokens this session: ~18 k.**
**Token savings vs. all-Opus baseline:** 0% (all planning tasks per Reference 02 are Opus-mandated). Savings begin at module-implementation phase.

---

## 15. Roadmap Position

- **Current milestone:** Pre-v0.3.0 (planning complete; this handover authorises v0.3.0 kickoff)
- **Modules completed:** 0 of 5 (v0.3.x cycle)
- **Estimated remaining effort:** 5 modules across 3 sessions; ~63 k tokens total inner-loop work
- **v0.4+ follow-on:** MC × bin-resolved DSD (per D-049 deferral); adjoint sensitivity (revisit if walltime bottleneck after v0.3.0); digital-twin live mode (out of scope per protocol § 1.2)
- **Wet-lab Track 2 (Q-013/Q-014)** continues independently of v0.3.x; the v0.3.x simulator-side scaffolding (G4 + G1's `from_calibration_store`) is what ingests the bench data when it lands

### Process observations

This is the first planning-phase handover for the v0.3.x cycle, so no prior session retrospective applies. Two observations going forward:

1. **The G2 module is the cycle's risk concentration.** It carries: (i) novel MC-over-stiff-ODE driver, (ii) Tier-1+2 numerical safeguards from SA-Q1, (iii) joblib parallelism with determinism gate, (iv) reformulated convergence diagnostics from SA-Q3. The architect's plan-level D1–D6 audit (§ 9 of `ARCH_v0_7_P5plusplus_DECOMPOSITION.md`) flagged all four as MEDIUM-to-HIGH risks. The orchestrator should anticipate at least one fix-cycle round on G2 and budget Opus-tier audit time accordingly.

2. **D-052 scope guard is load-bearing.** The 38 k token budget for v0.3.0 leaves ~22 k of safety margin in a 60 k single-session window — generous, but bundling G4 (+ ~11 k) and G5 (+ ~7 k) would push to 56 k, which is YELLOW-zone exit. The scope guard must be defended in the v0.3.0 session even if a contributor proposes "since we're here, just add G4 too."

---

## 16. Five-Point Quality Standard Check (Reference 04 § 4)

A new dialogue can:

1. **Read § 1–3 and know the complete project state without any prior context** — ✅ § 1 executive summary; § 2 module registry initial state; § 3 integration status.
2. **Read § 4 and locate every approved source file** — ✅ § 4 architecture-state ref to `ARCH_v0_7_P5plusplus_DECOMPOSITION.md` § 3–5 with explicit file paths per module.
3. **Read § 5–10 and understand all architectural and design decisions** — ✅ § 5 design decisions log (D-044 through D-053); § 10 SA escalation paths; § 11 IP/constraint notes.
4. **Read § 12 and begin implementing the next module immediately** — ✅ § 12 contains full G1 protocol satisfying G1-01 through G1-12.
5. **Read § 13 and have the full compressed history of the project** — ✅ § 13 compression summary; companion documents named for context expansion.

**All five checks pass. Handover is ready.**

---

## 17. Filing

```
docs/handover/
├── SA_v0_7_P5plusplus_BRIEF.md                 (Mode-1 brief; resolves G1-08 + G1-09)
├── ARCH_v0_7_P5plusplus_DECOMPOSITION.md       (5-module decomposition + DAG + per-module tests)
└── DEVORCH_v0_7_P5plusplus_JOINT_PLAN.md       ← this file
```

The trio is self-contained. A new dialogue resuming v0.3.0 development needs only these three documents plus the project source tree, the original `docs/p5_plus_plus_protocol.md`, and the v0.2.0 close handover (`docs/handover/HANDOVER_v9_2_CLOSE.md` and `HANDOVER_v9_3_CLOSE.md`, `HANDOVER_v9_4_CLOSE.md`) for legacy context.

---

> *This handover is self-contained. A new dialogue can resume development using only this document plus the SA brief and the Architect decomposition document.*
