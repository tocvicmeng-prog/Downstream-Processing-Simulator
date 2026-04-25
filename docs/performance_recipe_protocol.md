# /architect Protocol — PerformanceRecipe + Method Simulation Layer (DPSim v0.2.0)

**Author:** Architect (Claude Opus 4.7)
**Date:** 2026-04-25
**Repo:** `Downstream Processing Simulator` (DPSim) at v0.1.0
**Target release:** v0.2.0
**Closes:** Initial-handover next-task #2 (per-DSD-quantile full breakthrough) and #4 (M3 gradient-elution evidence inheritance from FunctionalMediaContract).

---

## 0. Pre-Flight Check (Phase 0)

### 0.1 Context Budget
Estimated token cost for the inner loop on this milestone:

| Phase | Est. tokens |
|---|---|
| Protocol (this doc) | ~5500 |
| Module 1 (PerformanceRecipe primitive) impl | ~1800 |
| Module 2 (run_method_simulation) impl | ~3500 |
| Module 3 (gradient FMC wiring) impl | ~1200 |
| Module 4 (per-DSD full method) impl | ~3000 |
| Tests across all four modules | ~4500 |
| Audit + 1 fix round | ~3000 |
| Milestone handover | ~3500 |
| **Total** | **~26,000** |

Session is in **GREEN zone** (>60% remaining). No compression required before kickoff. Allocate ~4k tokens for milestone handover after Module 4 approval.

### 0.2 Upstream Dependency Check
All upstream dependencies are APPROVED in v0.1.0:

| Dependency | Status | File |
|---|---|---|
| `ProcessRecipe` / `ProcessStep` / `LifecycleStage` | APPROVED | `src/dpsim/core/process_recipe.py` |
| `ResultGraph` / `ResultNode` | APPROVED | `src/dpsim/core/result_graph.py` |
| `ParameterProvider` / `ResolvedParameter` | APPROVED | `src/dpsim/core/parameters.py` |
| `ValidationReport` / `ValidationSeverity` | APPROVED | `src/dpsim/core/validation.py` |
| `FunctionalMediaContract` (M2 export) | APPROVED (legacy) | `src/dpsim/datatypes.py` |
| `ColumnGeometry` | APPROVED (legacy) | `src/dpsim/module3_performance/hydrodynamics.py` |
| `ChromatographyMethodStep` / `run_chromatography_method` | APPROVED (legacy) | `src/dpsim/module3_performance/method.py` |
| `run_breakthrough` / `run_gradient_elution` | APPROVED (legacy) | `src/dpsim/module3_performance/orchestrator.py` |
| `solve_lrm` (LSODA-or-BDF dispatch) | APPROVED (legacy) | `src/dpsim/module3_performance/transport/lumped_rate.py` |
| `recipe_resolver.m3_method_steps_from_recipe` | APPROVED | `src/dpsim/lifecycle/recipe_resolver.py` |

No re-ordering required.

### 0.3 Model-Tier Selection (per Reference 07 §3)

| Module | Task | Tier | Rationale |
|---|---|---|---|
| Architecture (this doc) | architecture_design | **Opus** | Non-negotiable per Ref 07 §3.2 |
| M1 — `PerformanceRecipe` primitive | implementation, LOW (~80 LOC, dataclass + builder + 1 helper) | **Sonnet** | Domain-aware (Quantity / unit handling) but no novel math. Sonnet, not Haiku, because of unit conversions and recipe semantics. |
| M2 — `run_method_simulation` entry point | implementation, MEDIUM (~150 LOC, refactor + new wrapper) | **Sonnet** | Standard orchestration with domain logic; reuses existing solvers. |
| M3 — `run_gradient_elution(fmc=...)` extension | implementation, MEDIUM (~80 LOC, signature change + manifest wiring) | **Sonnet** | Touches scientific evidence flow; small but evidence-correctness critical. |
| M4 — Per-DSD full method execution | implementation, MEDIUM (~250 LOC, replaces `_run_dsd_downstream_screen`) | **Sonnet** | Loop refactor + mass-weighted aggregation, no novel numerics. |
| Tests (M1+M2+M3+M4) | test_writing, numerical_validation | **Sonnet** | Crosses module boundaries; needs tolerance reasoning. |
| Full audit (Gate G3) | full_audit | **Opus** | Non-negotiable per Ref 07 §3.2 |

If any module needs a 2nd or 3rd fix round driven by algorithm error (e.g. mass-balance regression in M3 or M4), the focused re-audit goes to **Opus** (Ref 07 §3.2: focused_re_audit + algorithmic_fix → Opus).

### 0.4 Milestone Proximity
This milestone (v0.2.0) closes when M1–M4 are APPROVED. Pre-allocate ~4k tokens for the milestone handover. The handover document will live at `docs/handover/V0_2_0_PERFORMANCE_RECIPE_HANDOVER.md` and will include the standard 12 sections.

---

## 1. Requirements

### 1.1 Problem Statement
Today, M3 chromatography in DPSim is wired through two independent code paths:

1. **Method-level path** (`method.py::run_chromatography_method`): reuses `run_breakthrough` for the load step plus a hand-rolled `run_loaded_state_elution` driven by a step-typed `ChromatographyMethodStep[]`. It produces operability, column-efficiency, impurity-clearance, and Protein-A reports. The lifecycle orchestrator calls this once with the d50 representative.
2. **DSD screen** (`lifecycle/orchestrator.py::_run_dsd_downstream_screen`): runs `run_breakthrough` once per DSD quantile (10/50/90 by default) for pressure/DBC sensitivity. It does NOT run the full method (no gradient elute, no operability per quantile, no Protein-A diagnostics per quantile, no loaded-state elution per quantile).

There is no first-class typed primitive that names "the M3 method" the way `ProcessRecipe` names the wet-lab lifecycle. The recipe→method-step adapter lives inline in `recipe_resolver.m3_method_steps_from_recipe` and is not directly addressable from CLI/UI/tests.

In addition, `run_gradient_elution` (the multi-component competitive-Langmuir solver in `orchestrator.py:602–918`) hardcodes `fmc=None` in its manifest builder. Its evidence tier is therefore floored at SEMI_QUANTITATIVE regardless of upstream M2 calibration state. This breaks the M2→M3 evidence chain that `run_breakthrough` already implements (`orchestrator.py:283–354`).

### 1.2 Goals
| ID | Goal | Closes |
|---|---|---|
| G1 | Introduce `PerformanceRecipe` as the typed, addressable M3-method primitive — built once from `ProcessRecipe` and consumed by all M3 entry points. | User framing |
| G2 | Provide a single `run_method_simulation(...)` entry point that subsumes `run_chromatography_method`, optionally runs the full method per DSD quantile, and produces one `MethodSimulationResult` with rolled-up evidence. | Handover #2, user framing |
| G3 | Extend `run_gradient_elution` to accept an optional `fmc=` argument and propagate the upstream M2 manifest tier through `_build_m3_chrom_manifest` exactly as `run_breakthrough` does. | Handover #4 |
| G4 | Wire the gradient-elute step through the method layer when `ChromatographyMethodStep.gradient_field` is set, so multi-component competitive-Langmuir elution is reachable from a `ProcessRecipe`. | Handover #4 |
| G5 | Replace the lifecycle's `_run_dsd_downstream_screen` with a per-DSD call into `run_method_simulation`; preserve the cheap pressure-drop screen as a fast-path flag for cost-bounded UI loops. | Handover #2 |

### 1.3 Non-Goals (won't have in v0.2.0)
- Full per-DSD-bin execution (>3 representatives) — out of scope; defer to v0.3+.
- Per-quantile uncertainty propagation (parametric MC over each DSD bin) — defer.
- Calibration ingest for M3 breakthrough/gradient (handover #5) — defer.
- Streamlit UI migration to `PerformanceRecipe` (handover #6) — defer; UI keeps consuming `ChromatographyMethodResult` until v0.3.
- New isotherm physics; no new transport models.

### 1.4 MoSCoW

| Priority | Requirement |
|---|---|
| **Must** | `PerformanceRecipe` dataclass with `column`, `method_steps`, `feed`, `dsd_policy`, validation gates. |
| **Must** | `run_method_simulation` orchestrates pack→equilibrate→load→wash→elute over the full method, with optional per-DSD repetition. |
| **Must** | `MethodSimulationResult` carries the d50 result, the per-DSD result list (when requested), the mass-weighted aggregate diagnostics, and a single `ModelManifest` reflecting the weakest-tier roll-up. |
| **Must** | `run_gradient_elution` takes `fmc: FunctionalMediaContract | None = None` and feeds it to `_build_m3_chrom_manifest`. The manifest's tier inherits from FMC and is capped by the worst-component mass-balance gate. |
| **Must** | When `ChromatographyMethodStep.gradient_field` is set on the elute step, `run_method_simulation` dispatches to `run_gradient_elution` rather than `run_loaded_state_elution`. The two-component competitive Langmuir defaults from `run_gradient_elution` are reused; no new physics. |
| **Must** | Lifecycle orchestrator is refactored to call `run_method_simulation` once instead of `run_chromatography_method` + `_run_dsd_downstream_screen`. |
| **Must** | All existing tests in `tests/test_module3_method.py`, `tests/test_module3_breakthrough.py`, `tests/test_gradient_lrm.py`, `tests/lifecycle/...`, and `tests/core/test_clean_architecture.py` must pass with at most mechanical signature updates (verified by Phase 5). |
| **Must** | New tests cover: (a) PerformanceRecipe round-trip from ProcessRecipe; (b) gradient-elution FMC inheritance; (c) gradient elute via the method layer; (d) per-DSD method aggregation; (e) mass-weighted percentile correctness against `_weighted_percentile`. |
| **Must** | CI gates hold: ruff = 0, mypy = 0. |
| **Should** | A `PerformanceRecipe.fast_screen=True` mode preserves the cheap pressure-drop-only screen across DSD quantiles (skips load/elute solvers), so UI iteration loops keep their <2s response. |
| **Should** | `MethodSimulationResult.as_summary()` returns a JSON-serializable dict suitable for `ProcessDossier`. |
| **Could** | Per-DSD progress callback hook (`progress_callback: Callable[[int, int], None] | None`) so long lifecycles can report progress. |
| **Won't** | New isotherm models, calibration ingest, UI migration, per-DSD MC. |

### 1.5 Acceptance Criteria
1. `python -m dpsim lifecycle configs/fast_smoke.toml` completes in ≤ 1.5× v0.1.0 wall time on the same hardware (no DSD full method by default — `dsd_full_method=False`).
2. `python -m dpsim lifecycle configs/fast_smoke.toml --dsd-full-method` runs the full method for all three default DSD quantiles and reports rolled-up DBC10 + pressure spread + worst mass-balance error in the same console summary as today.
3. The smoke result table from INITIAL_HANDOVER.md still produces `weakest_tier=qualitative_trend`, `M3 DBC10 ≈ 0.706 mol/m³ column`, `M3 pressure drop ≈ 37 kPa`, `mass-balance error = 0.00%` for the d50 path within ±5%.
4. A new smoke configures the elute step with `gradient_field="ph"` and produces a non-zero `gradient_elution.peak_area`, `model_manifest.evidence_tier` ≤ FMC tier, and matching FMC `calibration_ref` propagation.
5. `pytest -q tests/` passes; new tests are at least 18 cases across the four modules.
6. ruff = 0, mypy = 0.
7. No backward-incompatible changes to `ProcessRecipe`, `ResultGraph`, or `FunctionalMediaContract`.

---

## 2. Architecture

### 2.1 Data-Flow Diagram

```
                         ProcessRecipe  (existing, unchanged)
                                │
                                ▼
                  recipe_resolver.LifecycleResolvedInputs   (existing)
                                │
                ┌───────────────┼─────────────────────┐
                ▼               ▼                     ▼
            M1 inputs       M2 inputs        ┌──────────────────────┐
              │              │               │  PerformanceRecipe   │  ← NEW (M1)
              │              │               │  (column, method,    │
              │              │               │   feed, dsd_policy,  │
              │              │               │   target_gates)      │
              │              │               └──────────┬───────────┘
              ▼              ▼                          │
        FullResult    FunctionalMedia                   │
              │       Contract (FMC)                    │
              └───────────┬──┴──────────────┬───────────┘
                          ▼                 ▼
                  ┌────────────────────────────────────┐
                  │ run_method_simulation(             │  ← NEW (M2)
                  │   recipe=PerformanceRecipe,        │
                  │   microsphere=FunctionalMicrosphere│
                  │   fmc=FMC,                         │
                  │   dsd_quantiles=(0.10,0.50,0.90),  │
                  │   dsd_full_method=True/False,      │
                  │ )                                  │
                  └─────────┬─────────────┬────────────┘
                            │             │
                  ┌─────────▼─────┐ ┌─────▼──────────────────┐
                  │ d50 method    │ │ per-quantile sub-loop  │
                  │ (load+elute)  │ │ (skip if not requested)│
                  └─────┬─────────┘ └──┬─────────────────────┘
                        │              │
                        │       ┌──────▼──────────┐
                        │       │ for each q:     │
                        │       │   run method    │
                        │       │   OR fast screen│
                        │       └──────┬──────────┘
                        │              │
                  ┌─────▼──────────────▼──────────┐
                  │ MethodSimulationResult        │  ← NEW (M2)
                  │  + manifest (weakest-tier)    │
                  │  + dsd aggregate              │
                  │  + per-quantile sub-results   │
                  └──────────────┬────────────────┘
                                 ▼
                            ResultGraph node "M3"
                                 │
                                 ▼
                      DownstreamLifecycleResult
```

Inside `run_method_simulation`, the elute step branches:

```
if elute_step.gradient_field set:
   → run_gradient_elution(..., fmc=fmc)        # M3 — extended
else:
   → run_loaded_state_elution(...)              # M2 — already wired
```

### 2.2 Module Decomposition

| # | Module | New file? | Responsibility | LOC est. |
|---|---|---|---|---|
| **M1** | `dpsim.core.performance_recipe` | NEW | `PerformanceRecipe` dataclass + `from_process_recipe(recipe, resolved_inputs)` builder. | ~120 |
| **M2** | `dpsim.module3_performance.method_simulation` | NEW | `run_method_simulation` + `MethodSimulationResult` + DSD aggregation. Refactors `run_chromatography_method` into a private d50 helper. | ~250 |
| **M3** | `dpsim.module3_performance.orchestrator` | edit | `run_gradient_elution(..., fmc=None)` — add arg, route to `_build_m3_chrom_manifest`, propagate calibration_ref + assumptions. | ~30 |
| **M4** | `dpsim.lifecycle.orchestrator` | edit | Replace `_run_dsd_downstream_screen` and the dual M3 calls with a single `run_method_simulation`. | ~150 net (delete ~120, add ~270) |

### 2.3 Critical Path
M1 → M2 → M3 → M4. M3 can theoretically run in parallel with M1 (independent file), but Phase-5 integration tests for M4 need M2 + M3 both done. Build linearly to keep the audit cycle simple.

### 2.4 Parallelism Map
- **Internal to M2**: per-DSD-quantile method runs are embarrassingly parallel and trivially `joblib`-parallelizable. v0.2.0 keeps them serial; expose a `n_jobs: int = 1` arg shaped to allow joblib injection later. **Do not** use joblib in v0.2.0 — the architect-approved tier is "shape the API for it, defer the implementation."
- **External to M2**: a per-DSD method run is independent of M2 functionalization output; future versions could parallelize across DSD bins, but the FMC handle is shared and read-only so no contention.

---

## 3. Module Protocols

### 3.1 Module M1 — `PerformanceRecipe` primitive

**File:** `src/dpsim/core/performance_recipe.py`

#### Purpose
A typed compiled view over the M3 portion of a `ProcessRecipe`. Owns the column geometry, the executable method-step list, the load feed conditions, the DSD policy, and the operability gates that today are scattered across `LifecycleResolvedInputs` and the lifecycle orchestrator's run() arguments.

#### Interface

```python
@dataclass(frozen=True)
class DSDPolicy:
    """How M3 should consume M1's representative DSD quantiles."""
    quantiles: tuple[float, ...] = (0.10, 0.50, 0.90)
    run_full_method: bool = False
    fast_pressure_screen: bool = True
    n_jobs: int = 1  # reserved; not used in v0.2.0

@dataclass
class PerformanceRecipe:
    """Compiled M3 method specification — the canonical input to run_method_simulation."""
    column: ColumnGeometry
    method_steps: list[ChromatographyMethodStep]
    feed_concentration_mol_m3: float
    feed_duration_s: float
    total_time_s: float
    n_z: int = 30
    dsd_policy: DSDPolicy = field(default_factory=DSDPolicy)
    max_pressure_drop_Pa: float = 3.0e5
    pump_pressure_limit_Pa: float = 3.0e5
    D_molecular: float = 7.0e-11
    k_ads: float = 100.0
    notes: str = ""

    def load_step(self) -> ChromatographyMethodStep | None: ...
    def elute_step(self) -> ChromatographyMethodStep | None: ...
    def has_gradient_elute(self) -> bool: ...

def performance_recipe_from_resolved(
    resolved: LifecycleResolvedInputs,
    *,
    dsd_policy: DSDPolicy | None = None,
) -> PerformanceRecipe:
    """Build a PerformanceRecipe from the existing recipe-resolver output."""
```

#### Algorithm
Trivial assembly. The builder pulls fields already computed by `resolve_lifecycle_inputs`:
- `column = resolved.column`
- `method_steps = resolved.m3_method_steps`
- feed/duration/total_time from the same provider keys
- `max_pressure_drop_Pa = resolved.max_pressure_drop_Pa`
- `pump_pressure_limit_Pa = resolved.pump_pressure_limit_Pa`
- `n_z = resolved.m3_n_z`

`has_gradient_elute()` returns `True` iff the elute step's `gradient_field` is non-empty.

#### Complexity
O(n_steps), O(n_steps) memory. Negligible.

#### Errors
- Missing PACK or LOAD step → raise `ValueError` with the canonical recipe key list. (Today the lifecycle silently tolerates this; the protocol upgrades it because the typed primitive should not allow a degenerate state.)

#### Tests
| ID | Input | Expected |
|---|---|---|
| M1-T01 | `default_affinity_media_recipe()` → resolve → from_resolved | `PerformanceRecipe.column.bed_height ≈ 0.10 m`, 5 method steps, `has_gradient_elute()` returns False (default recipe uses `gradient_field="ph"` on elute, so this should be **True** — verify and adjust expectation accordingly). |
| M1-T02 | Recipe with empty M3 stage | `ValueError` raised from `performance_recipe_from_resolved` |
| M1-T03 | Recipe with `gradient_field="ph"` on elute | `has_gradient_elute() == True` |
| M1-T04 | Custom DSDPolicy | round-trip preserves quantiles, run_full_method, fast_pressure_screen |

---

### 3.2 Module M2 — `run_method_simulation` entry point

**File:** `src/dpsim/module3_performance/method_simulation.py`

#### Purpose
Single function that simulates a complete chromatography method (today's `run_chromatography_method`) and optionally repeats it across DSD quantiles. Replaces the dual-path lifecycle orchestration. Produces one rolled-up result with a single weakest-tier manifest.

#### Interface

```python
@dataclass
class DSDQuantileResult:
    """Per-DSD-quantile method outcome (full method or fast screen)."""
    quantile: float
    bead_d50_m: float
    method_result: ChromatographyMethodResult | None  # None when fast_pressure_screen ran
    pressure_drop_Pa: float
    bed_compression_fraction: float
    dbc_10pct_mol_m3: float | None
    mass_balance_error: float | None
    weakest_tier: ModelEvidenceTier
    diagnostics: dict[str, float | str]

@dataclass
class MethodSimulationResult:
    """Aggregated M3 result spanning the d50 method and (optional) DSD quantiles."""
    representative: ChromatographyMethodResult
    dsd_quantile_results: list[DSDQuantileResult]      # empty when DSD path off
    dsd_summary: DSDPropagationSummary | None          # None when DSD path off
    gradient_elution: GradientElutionResult | None     # populated when elute is gradient
    model_manifest: ModelManifest                      # weakest-tier roll-up
    assumptions: list[str]
    wet_lab_caveats: list[str]

    def as_summary(self) -> dict[str, Any]: ...

def run_method_simulation(
    recipe: PerformanceRecipe,
    *,
    microsphere: FunctionalMicrosphere | None = None,
    fmc: FunctionalMediaContract | None = None,
    process_state: ProcessState | dict | None = None,
    dsd_payload: dict | None = None,                 # M1 DSD distribution (optional)
) -> MethodSimulationResult:
    ...
```

#### Algorithm

```text
1.  d50 path:
    column = _column_with_microsphere(recipe.column, microsphere)
    representative = _run_one_method(column, recipe, fmc, process_state)

2.  Gradient elute branch (in _run_one_method):
    elute = recipe.elute_step()
    if elute and elute.gradient_field:
        gradient = _build_gradient_program_from_step(elute)
        ge_result = run_gradient_elution(
            column=column,
            C_feed=np.array([recipe.feed_concentration_mol_m3]),
            gradient=gradient,
            flow_rate=elute.flow_rate_m3_s,
            total_time=elute.duration_s + load_step.duration_s,
            feed_duration=load_step.duration_s,
            isotherm=None,                        # default 2-component competitive Langmuir
            fmc=fmc,                              # NEW (Module M3)
            process_state=process_state,
        )
        # Replace ChromatographyMethodResult.loaded_elution semantics with gradient peak metrics
        # in the wet-lab summary; keep both objects on MethodSimulationResult
    else:
        # existing run_loaded_state_elution path inside run_chromatography_method

3.  DSD path:
    if recipe.dsd_policy.run_full_method and dsd_payload is not None:
        rows = _dsd_representative_rows(dsd_payload, recipe.dsd_policy.quantiles)
        for row in rows:
            col_q = column with particle_diameter = row.diameter
            if recipe.dsd_policy.fast_pressure_screen and not full_method_per_q:
                qres = _fast_pressure_screen(col_q, recipe)
            else:
                method_q = _run_one_method(col_q, recipe, fmc, process_state)
                qres = DSDQuantileResult(... from method_q ...)
            dsd_quantile_results.append(qres)
        dsd_summary = _summarize_dsd_variants(dsd_quantile_results)

4.  Manifest roll-up:
    weakest_tier = max over [representative.manifest, gradient_elution.manifest, dsd_q.manifest...]
    diagnostics = merged dict
    return MethodSimulationResult(...)
```

#### Complexity
- d50 path: same as today — `O(n_z × n_t × n_comp)` LRM solve.
- DSD path: `O(|quantiles|) × O(d50_path)` when `run_full_method=True`. With default `(0.10, 0.50, 0.90)`, ~3× the d50 cost. Fast screen path is O(|quantiles|) algebraic — negligible.

#### Numerical Considerations
- `_column_with_microsphere` already exists in lifecycle/orchestrator; **lift verbatim** (do not rewrite). Move from lifecycle/orchestrator.py to method_simulation.py and re-import in lifecycle.
- `_build_gradient_program_from_step` is new but trivial: linear two-segment program from `gradient_start` to `gradient_end` over `duration_s`. Reuse `module3_performance.gradient.GradientProgram`.
- For DSD path, the column's `bed_porosity` does NOT change with `d50` (already enforced in `_column_with_microsphere`); only `particle_diameter` changes. **Do not** re-derive bed porosity from DSD; that would silently shift hydraulic regimes.

#### Errors
- Missing load step → raise.
- Missing column → raise.
- Mass-balance > 5% on d50 → log WARNING, allow result but rely on `_build_m3_chrom_manifest` to cap the tier at QUALITATIVE_TREND.
- `run_full_method=True` but `dsd_payload is None` → raise `ValueError("DSD full method requires a DSD payload from M1")`.

#### Tests
| ID | Input | Expected |
|---|---|---|
| M2-T01 | Default `PerformanceRecipe`, no DSD | `representative.load_breakthrough.dbc_10pct > 0`; `dsd_quantile_results == []`; manifest tier inherits FMC. |
| M2-T02 | Default + `run_full_method=True`, fake DSD payload (3 quantiles) | `len(dsd_quantile_results) == 3`; each `method_result` is non-None; weakest tier is the max across all four manifests. |
| M2-T03 | Default + `fast_pressure_screen=True` | `dsd_quantile_results[i].method_result is None`; `pressure_drop_Pa > 0`; runs in <0.2 s. |
| M2-T04 | Recipe with elute gradient_field="ph" | `gradient_elution is not None`; `gradient_elution.peaks[0].peak_area > 0`. |
| M2-T05 | Mass-balance > 5% (forced via tiny n_z=3) | Manifest tier capped at QUALITATIVE_TREND with `mass_balance_status="blocker"`. |
| M2-T06 | `run_full_method=True` with `dsd_payload=None` | `ValueError`. |
| M2-T07 | as_summary() | dict is JSON-serializable; round-trips through `json.dumps`. |

---

### 3.3 Module M3 — `run_gradient_elution(fmc=...)`

**File:** `src/dpsim/module3_performance/orchestrator.py` (edit)

#### Purpose
Close handover task #4. The function currently builds its manifest with `fmc=None` hardcoded, which floors the M3 gradient evidence tier at SEMI_QUANTITATIVE regardless of M2 calibration state. Mirror the `run_breakthrough` pattern.

#### Interface change

```python
def run_gradient_elution(
    column: ColumnGeometry,
    C_feed: np.ndarray,
    gradient: GradientProgram,
    flow_rate: float,
    total_time: float,
    feed_duration: float | None = None,
    isotherm: CompetitiveLangmuirIsotherm | None = None,
    n_z: int = 50,
    D_molecular: float | np.ndarray = 7e-11,
    k_ads: float | np.ndarray = 100.0,
    extinction_coeffs: np.ndarray | None = None,
    sigma_detector: float = 1.0,
    mu: float = 1e-3,
    rho: float = 1000.0,
    rtol: float = 1e-5,
    atol: float = 1e-8,
    process_state=None,
    gradient_field: str | None = None,
    fmc=None,                                # NEW — keyword-only acceptable
) -> GradientElutionResult:
```

The single semantic change is the manifest builder call:

```python
manifest = _build_m3_chrom_manifest(
    model_basename="M3.gradient_elution.LRM",
    isotherm=isotherm,
    fmc=fmc,                                 # was None
    worst_mass_balance_error=worst_mb,
    diagnostics_extra={...},
)
```

No algorithmic change. No solver change. Tier inheritance and mass-balance gate already work because `_build_m3_chrom_manifest` is shared.

#### Tests
| ID | Input | Expected |
|---|---|---|
| M3-T01 | `run_gradient_elution(..., fmc=None)` | manifest tier == SEMI_QUANTITATIVE (regression of current behaviour). |
| M3-T02 | `run_gradient_elution(..., fmc=fake_fmc_calibrated)` | manifest tier == fake_fmc.tier; `calibration_ref` propagated; assumptions list contains FMC's assumptions. |
| M3-T03 | `run_gradient_elution(..., fmc=fake_fmc_qualitative)` | manifest tier == QUALITATIVE_TREND (M3 cannot exceed upstream). |
| M3-T04 | Forced mass-balance >5% (n_z=3) with calibrated FMC | manifest tier capped at QUALITATIVE_TREND; `calibration_ref` still propagated. |

#### Errors
None new. Existing `RuntimeError` paths preserved.

---

### 3.4 Module M4 — Lifecycle orchestrator refactor

**File:** `src/dpsim/lifecycle/orchestrator.py` (edit)

#### Purpose
Replace the parallel `run_chromatography_method` + `_run_dsd_downstream_screen` calls with a single `run_method_simulation`. Delete `_run_dsd_downstream_screen` body and replace with a thin shim that builds the DSDPolicy from kwargs and delegates.

#### Specification
1. After `resolve_lifecycle_inputs` returns, build:
   ```python
   recipe = performance_recipe_from_resolved(
       resolved,
       dsd_policy=DSDPolicy(
           quantiles=dsd_quantiles,
           run_full_method=dsd_full_method,            # NEW kwarg, default False
           fast_pressure_screen=dsd_run_breakthrough,  # rename meaning slightly
       ),
   )
   ```
2. Replace the two M3 call sites (lines ~660 and ~738) with a single `run_method_simulation(recipe, microsphere=microsphere, fmc=fmc, process_state=ps, dsd_payload=dsd_payload)`.
3. Map the result back to `DownstreamLifecycleResult`:
   - `m3_method` ← `result.representative`
   - `dsd_variants` ← derived from `result.dsd_quantile_results` (use existing `DSDMediaVariant` shape; conversion is straightforward since `DSDQuantileResult` is a strict superset).
   - `dsd_summary` ← `result.dsd_summary`
   - Add `result.gradient_elution` to `DownstreamLifecycleResult` as `m3_gradient_elution: GradientElutionResult | None = None`.
4. ResultGraph node `M3` payload becomes the `MethodSimulationResult`. Manifest already weakest-tier-rolled.
5. Validation roll-up: existing `_add_m3_pressure_flow_validation`, `_validate_m1_carryover_for_downstream`, `_add_m3_dbc_reference_validation`, `_add_m3_calibration_uncertainty_validation` keep their current call sites.
6. **Delete** `_run_dsd_downstream_screen` after M2 absorbs its logic; keep `_summarize_dsd_variants` and `_dsd_representative_rows` (move them to method_simulation.py; lifecycle imports them).

#### Tests
| ID | Input | Expected |
|---|---|---|
| M4-T01 | Smoke lifecycle (`fast_smoke.toml`) — DSD off | identical d50 outputs vs v0.1.0 (within ±5%). |
| M4-T02 | Smoke lifecycle — DSD fast screen | pressure-spread range matches v0.1.0 within float tolerance. |
| M4-T03 | Smoke lifecycle — DSD full method (NEW path) | per-quantile DBC10 list non-empty; mass-weighted DBC10 p50 within 10% of d50 result. |
| M4-T04 | Smoke lifecycle with elute gradient_field="ph" | `m3_gradient_elution` populated; weakest tier roll-up unchanged when FMC tier == QUALITATIVE_TREND. |
| M4-T05 | Existing `tests/lifecycle/...` regressions | all pass with at most signature-change updates. |

---

## 4. Data Contracts

### 4.1 PerformanceRecipe (NEW, M1)
| Field | Type | Units | Source | Constraints |
|---|---|---|---|---|
| `column` | `ColumnGeometry` | — | resolver | bed_height>0, diameter>0, 0.05≤bed_porosity≤0.95 |
| `method_steps` | `list[ChromatographyMethodStep]` | — | resolver | non-empty; first step is PACK; LOAD present |
| `feed_concentration_mol_m3` | float | mol/m³ | resolver | ≥0 |
| `feed_duration_s` | float | s | resolver | >0 |
| `total_time_s` | float | s | resolver | ≥ feed_duration_s |
| `n_z` | int | — | resolver | ≥3 (recommended ≥30) |
| `dsd_policy` | `DSDPolicy` | — | builder | quantiles ⊆ (0,1) |
| `max_pressure_drop_Pa` | float | Pa | resolver | >0 |
| `pump_pressure_limit_Pa` | float | Pa | resolver | >0 |
| `D_molecular` | float | m²/s | hardcoded for v0.2.0 | >0 |
| `k_ads` | float | 1/s | hardcoded for v0.2.0 | >0 |

### 4.2 MethodSimulationResult (NEW, M2)
| Field | Type | Notes |
|---|---|---|
| `representative` | `ChromatographyMethodResult` | d50 path; existing object reused verbatim. |
| `dsd_quantile_results` | `list[DSDQuantileResult]` | empty unless `recipe.dsd_policy.run_full_method` or `fast_pressure_screen`. |
| `dsd_summary` | `DSDPropagationSummary | None` | reuse existing dataclass from lifecycle. |
| `gradient_elution` | `GradientElutionResult | None` | populated when elute is gradient. |
| `model_manifest` | `ModelManifest` | weakest tier across (representative, gradient, all DSD). Mass-balance gate uses worst error. |
| `assumptions` | `list[str]` | union of representative + gradient + DSD assumptions. |
| `wet_lab_caveats` | `list[str]` | union. |

### 4.3 DSDQuantileResult (NEW, M2)
Strict superset of today's `DSDMediaVariant`. Lifecycle will keep `DSDMediaVariant` as a converter target (consumed by validation helpers); we don't break those.

### 4.4 Manifest Tier Inheritance (Cross-cutting)
Reaffirmed from `_build_m3_chrom_manifest`:

```text
tier(M3) = max_index_of(
    upstream_FMC_tier,                    # weakest of M2 contributors
    QUALITATIVE_TREND if mb_error > 5% else GRAY_PASSTHROUGH,
)
```

After v0.2.0 this rule applies uniformly to:
- `run_breakthrough` (already does)
- `run_gradient_elution` (NEW via Module M3)
- `MethodSimulationResult.model_manifest` (rolls up across both + per-DSD)

---

## 5. Test Plan

### 5.1 Test Files
| File | New / Edit | Scope |
|---|---|---|
| `tests/core/test_performance_recipe.py` | NEW | M1 (4 tests, T01–T04) |
| `tests/test_module3_method_simulation.py` | NEW | M2 (7 tests, T01–T07) |
| `tests/test_gradient_lrm.py` | EDIT | add M3-T01..T04 (FMC inheritance) |
| `tests/lifecycle/test_lifecycle_method_simulation.py` | NEW | M4 (5 tests, T01–T05) |
| Existing: `tests/test_module3_method.py`, `test_module3_breakthrough.py`, `test_module3_multicomponent.py`, `test_v60_integration.py`, `test_validation_pipeline.py` | UNCHANGED-OR-MINOR | regression; expect at most signature renames. |

### 5.2 Acceptance Test (CLI smoke)
The `python -m dpsim lifecycle configs/fast_smoke.toml` command must continue to print the lifecycle summary block from `INITIAL_HANDOVER.md` §"Verification Performed", with these allowed deltas:
- `weakest evidence tier` unchanged: `qualitative_trend`.
- `M3 DBC10` within ±5% of `0.706 mol/m3 column`.
- `M3 pressure drop` within ±5% of `37.12 kPa`.
- `M3 mass-balance error` ≤ 0.5% (was 0.00%; the gradient-elute path has its own MB so zero may not survive).
- `DSD screen: 3 quantiles, pressure-drop range` unchanged when `--dsd-full-method` not passed.
- New: when `--dsd-full-method` is passed, the DSD screen line includes `mass-weighted DBC10 p10/p50/p90` triple.

### 5.3 CI Gates
Hard ruff-0 / mypy-0 (per CLAUDE.md v9.1.x decisions). The new files inherit the project's existing `# type: ignore[arg-type]` policy from optimization smoke; we expect zero such tags in this milestone.

---

## 6. G1 Readiness Check (Architect's Self-Audit)

| # | Criterion | Pass? | Note |
|---|---|---|---|
| G1-01 | Problem and goals stated unambiguously | ✅ | §1.1, §1.2 |
| G1-02 | MoSCoW prioritisation captured | ✅ | §1.4 |
| G1-03 | Acceptance criteria measurable | ✅ | §1.5, §5.2 |
| G1-04 | Module decomposition complete | ✅ | §2.2 |
| G1-05 | All external dependencies APPROVED upstream | ✅ | §0.2 |
| G1-06 | Data contracts specified with units and constraints | ✅ | §4 |
| G1-07 | Algorithm complexity stated for each module | ✅ | §3.1–3.4 |
| G1-08 | Numerical-stability considerations identified | ✅ | §3.2 (n_z, BDF vs LSODA inheritance, _column_with_microsphere) |
| G1-09 | Test plan covers happy path + edge cases + regressions | ✅ | §5 |
| G1-10 | Model-tier selection documented per module | ✅ | §0.3 |
| G1-11 | Backward compatibility of existing public surfaces | ✅ | §1.3 (won't): no breaking change to ProcessRecipe / FMC / ResultGraph |
| G1-12 | Risk register present | ✅ | §7 |

**Verdict: G1 = PASS (12/12).** Ready to begin Phase 4 (protocol delivery) and hand to /scientific-coder for Module M1 implementation.

---

## 7. Risk Register

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | DSD full-method tripled wall time blows the smoke gate | M | M | Default `dsd_full_method=False`; fast pressure screen stays the lifecycle default. Acceptance criterion 1 enforces ≤1.5× wall time. |
| R2 | Gradient-elution-via-method changes the d50 smoke baseline (was loaded-state elution) | M | H | Keep `run_loaded_state_elution` path active when `gradient_field` empty. Default recipe DOES set `gradient_field="ph"` — so the d50 baseline WILL change. Update `INITIAL_HANDOVER.md`'s smoke-result table in the same PR; acceptance criterion 3 allows ±5% drift but the pressure number may move more (gradient run is longer). **Decision needed before M2 implementation: do we keep loaded-state elution as the default for v0.2.0 and gate the gradient path on an explicit recipe flag?** Recommend yes — see §8 Open Questions Q1. |
| R3 | Mass-balance gate trips more often once gradient elute is real | M | L | Already handled by `_build_m3_chrom_manifest`; tier degrades to QUALITATIVE_TREND but result is still produced. Document in CHANGELOG. |
| R4 | `_dsd_representative_rows` refactor breaks an undocumented caller | L | M | Move-and-re-export from `method_simulation.py`; keep the symbol available from `lifecycle.orchestrator` via `from .. import _dsd_representative_rows` for one release. |
| R5 | mypy=0 cap broken by new dataclasses | L | M | Use `from __future__ import annotations` and explicit `field(default_factory=...)`; pre-existing patterns hold. |
| R6 | Per-DSD method runs share a non-thread-safe solver state | L | H | scipy `solve_ivp` is reentrant; n_jobs stays 1 in v0.2.0; the API is shaped for future parallelism but not enabled. |

---

## 8. Open Questions for Project Manager

| ID | Question | Why it matters |
|---|---|---|
| **Q1** | Should v0.2.0's default elute path stay as the existing `run_loaded_state_elution` (low-pH single-component drop) or switch to `run_gradient_elution` (multi-component competitive Langmuir) when `gradient_field="ph"` is set on the recipe? | Determines whether the d50 smoke result moves. Recommendation: **stay on loaded-state by default; gate gradient-via-method on a new recipe flag** `dsim run --m3-gradient-elute` for v0.2.0. Switch the default in v0.3.0 once UI + dossier match. |
| **Q2** | Should `dsd_full_method` become the default once tests pass, or stay opt-in? | UX vs CI cost. Recommendation: opt-in for v0.2.0; revisit after performance benchmarking. |
| **Q3** | Do we want a thin `python -m dpsim method <recipe.toml>` CLI subcommand that bypasses M1+M2 and runs the M3 method only against a saved FMC JSON? | Feature scope. Out-of-scope for v0.2.0; flag for v0.3.0 if the UI migration (handover #6) needs it. |

---

## 9. Build Order

| Step | Module | Tier | Audit gate | Estimated wall time |
|---|---|---|---|---|
| 1 | M1 — `PerformanceRecipe` primitive + tests | Sonnet | G3 (1 round) | 30 min |
| 2 | M3 — `run_gradient_elution(fmc=...)` + tests | Sonnet | G3 (1 round) | 20 min |
| 3 | M2 — `run_method_simulation` + tests | Sonnet | G3 (≤2 rounds) | 60 min |
| 4 | M4 — lifecycle refactor + smoke + regression tests | Sonnet | G3 (≤2 rounds) | 60 min |
| 5 | Architect full audit + milestone handover | Opus | — | 30 min |

Total estimated implementation effort: ~3.5 hours of coder-session time + 30 min of architect time. Net LOC: ~+550, ~−120, **+430 net**.

---

## 10. Revision History
| Version | Date | Author | Notes |
|---|---|---|---|
| 0.1 | 2026-04-25 | Architect | Initial scoping; G1 = PASS (12/12). Awaiting PM decision on Q1–Q3 before kicking off Module M1 implementation. |
| 0.2 | 2026-04-25 | PM + Architect | Q1, Q2, Q3 resolved (see §11). Module A1 (PerformanceRecipe primitive) implementation kicked off. |

---

## 11. Decisions Logged

### Q1 — RESOLVED 2026-04-25
**Decision:** v0.2.0 keeps `run_loaded_state_elution` as the default elute path. The gradient-via-method path (`run_gradient_elution`) is gated on an explicit recipe-level opt-in: `elute.metadata["competitive_gradient"] = True` (or equivalent typed flag, finalised in module A4).

**Implication for A1:** `PerformanceRecipe.has_gradient_elute()` reports recipe-level *intent* (non-empty `gradient_field`); it does **not** force gradient dispatch. The dispatch decision lives in module A4's `run_method_simulation`.

**Implication for v0.3.0:** The default flips in v0.3.0 alongside the M2/M3 evidence-tier UI work. `INITIAL_HANDOVER.md` smoke-result table is updated in the same PR that flips the default.

**Why:** The default recipe sets `gradient_field="ph"`. Auto-dispatching to gradient elution in v0.2.0 would silently move the d50 smoke baseline (DBC10, pressure, mass-balance) at the same time as the architecture refactor lands, conflating the diff. Two-step rollout isolates the architectural change from the scientific-baseline change.

### Q2 — RESOLVED 2026-04-25
**Decision:** `--dsd-full-method` is opt-in for v0.2.0. Default lifecycle behaviour is unchanged (3-quantile fast pressure screen, no per-quantile method).

**Why:** Avoids the 3× wall-time hit on the v0.2.0 smoke gate.

### Q3 — RESOLVED 2026-04-25
**Decision:** `python -m dpsim method <recipe.toml>` standalone CLI is **out of scope** for v0.2.0 + v0.3.0. Deferred to v0.4.0+ alongside the UI migration.
