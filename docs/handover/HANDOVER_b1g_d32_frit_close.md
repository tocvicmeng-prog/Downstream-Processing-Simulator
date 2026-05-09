# B-1g Close — Sauter d32 Surfacing + Frit Resistance

**Date:** 2026-05-10
**Scope:** Closing batch B-1g from `docs/update_workplan_2026-05-10_m3_pressure.md` — second Tier 1 batch of v0.7.0 M3 back-pressure work; closes W-021 (Δ2 Sauter d32) and W-024 (Δ5 frit resistance).
**Branch state at handover:** `main` at `45867ab` (B-1f close commit) + uncommitted B-1g files.
**Authors:** `/scientific-advisor` (d_p source defect) + `/architect` (contract change) + `/scientific-coder` (implementation).

---

## 1. Project context

Two of the three CRITICAL correctness defects that B-1f did NOT address:

- **W-021 (Δ2):** `_column_with_microsphere` and `_column_for_quantile` in `module3_performance/method_simulation.py` sourced `particle_diameter` from `m1.bead_d50` (median). Kozeny-Carman / Ergun derive from the surface-area-equivalent diameter, which for a polydisperse population is the Sauter mean d32 by definition. At typical lognormal DSD width σ_ln = 0.3, d32 ≈ 0.80·d50 → ΔP underestimated by (d50/d32)² ≈ 1.56× systematically.
- **W-024 (Δ5):** `ColumnGeometry` did not represent the frit / distributor / end-fitting series resistance ΔP_frit = μ·u·t_frit / k_f. On small analytical columns at high Q this can be 10–30 % of the total bed ΔP and is silently absent from the operational pressure envelope.

**Notable discovery during pre-flight:** `bead_d32` was already a field on `M1ExportContract` (`datatypes.py:1669`) and `BeadSizeDistributionPayload` (`datatypes.py:1213`). The architect's "must-have" core ask for W-021 collapsed to a two-line swap. The "nice-to-have" `dsd_sigma_ln` field is unnecessary because `BeadSizeDistributionPayload.span` already characterises DSD width.

---

## 2. Files delivered

### 2.1 Source modifications (2 files)

| File | Lines | Change |
|---|---|---|
| `src/dpsim/module3_performance/method_simulation.py` | +14 / -2 | `_column_with_microsphere`: `m1.bead_d50` → `m1.bead_d32`; `_column_for_quantile` fallback: same. Both updated docstrings cite W-021 / B-1g and the (d50/d32)² ≈ 1.56× ΔP correction factor. |
| `src/dpsim/module3_performance/hydrodynamics.py` | +44 | `ColumnGeometry`: added `frit_permeability_m2: Optional[float] = None` and `frit_thickness_m: Optional[float] = None` fields, plus new `frit_pressure_drop(flow_rate, mu)` method computing μ·u·t/k_f. Returns 0.0 if either field is `None` (backwards-compat default). Validates: permeability > 0, thickness ≥ 0. Updated `pressure_drop` docstring to note the bed-only scope. |

### 2.2 Tests (2 new files)

| File | Test cases | Coverage |
|---|---|---|
| `tests/module3_performance/test_hydrodynamics_frit.py` | 13 | Defaults (frit None / `frit_pressure_drop` returns 0.0), partially-configured (only one field set → still 0.0), fully-configured (canonical sintered PE frit, scales linearly with Q, μ; inversely with k_f), validation (zero/negative permeability raises; negative thickness raises; zero thickness returns 0.0). |
| `tests/module3_performance/test_column_microsphere_wiring.py` | 10 | `_column_with_microsphere` reads d32 not d50 (positive + negative assertions); ΔP correction factor (d50/d32)² in 1.50–1.65 range; `microsphere=None` returns input column unchanged; M2-updated G_DN/E_star wiring intact; M1 fallback when M2 sets 0; `_column_for_quantile` fallback to d32 when no diameter; explicit per-quantile diameter wins. |

**Total: 23 new test cases.**

### 2.3 No NEW source modules in this batch.

---

## 3. Module registry update

| Module | Owner | Status before | Status after |
|---|---|---|---|
| `module3_performance/method_simulation.py` | architect | APPROVED | **APPROVED** (post-B-1g d32 swap; integration tests still green) |
| `module3_performance/hydrodynamics.py` | architect | APPROVED-WITH-FIX-LIST (post v0.6.6) | **APPROVED-WITH-FIX-LIST** (B-1g added frit fields; remaining fix-list items are W-020 ΔP_max anchor in B-2f and W-022 iteration in B-2g) |

Module status accumulated to date in v0.7.0:

| Module | Status |
|---|---|
| `core/mobile_phase.py` | APPROVED (B-1f) |
| `core/viscosity.py` | APPROVED (B-1f) |
| `module3_performance/hydrodynamics.py` | APPROVED-WITH-FIX-LIST (B-1g; B-2f + B-2g pending) |
| `module3_performance/method_simulation.py` | APPROVED (B-1g) |
| `core/decision_grade.py` | NOT STARTED (B-1h next) |
| `module3_performance/family_kgeom.py` | NOT STARTED (B-2f) |
| `module3_performance/pressure_envelope.py` | NOT STARTED (B-2f) |
| `module3_performance/pressure_monitor.py` | NOT STARTED (B-3d) |

---

## 4. Verification matrix

### 4.1 Test runs

| Suite | Result |
|---|---|
| New B-1g suites (`test_hydrodynamics_frit.py`, `test_column_microsphere_wiring.py`) | **23/23 passed** in 1.58 s |
| Wide regression (B-1f + B-1g + Tier 0 baseline + all `tests/module3_performance/` + `tests/lifecycle/` + `tests/core/test_recipe_validation*.py`) | **316/316 passed** in 88.9 s |

### 4.2 Lint / type / AST gate

| Gate | Result |
|---|---|
| ruff on B-1g files (4 paths) | All checks passed ✓ |
| mypy on `hydrodynamics.py` | Success: no issues found in 1 source file |
| AST gate (`tests/test_v9_3_enum_comparison_enforcement.py`) | 3/3 passing |

---

## 5. Concrete starting point for next session — B-1h

B-1h is the third and last Tier 1 batch — a small (≤ 30 LOC) decision-grade enum extension that prepares the render-mode policy for B-2f's pressure-envelope outputs.

### 5.1 W-030 (Δ1 follow-on) — Decision-grade enum extension

Files to touch:

- `src/dpsim/core/decision_grade.py` — extend `OutputType` enum with four new members:
  - `PRESSURE_LIMIT` — operational ΔP_max ceiling
  - `Q_MAX` — max safe flow rate (inverted u_crit)
  - `U_CRIT` — critical superficial velocity
  - `PRESSURE_HEADROOM` — ΔP / ΔP_max ratio (always rendered)

  Plus four rows in `DECISION_GRADE_POLICY` mirroring the existing `PRESSURE_DROP` policy (min tier `SEMI_QUANTITATIVE` → INTERVAL render; promote to NUMBER at `CALIBRATED_LOCAL`).

  `PRESSURE_HEADROOM` is tier-independent (always renders as percentage; the *threshold* for warning/blocker is what depends on tier).

- `tests/core/test_decision_grade_pressure_outputs.py` (NEW) — ~12 cases covering each new OutputType's policy-table behaviour and the tier-dependent render mode.

### 5.2 Pre-flight before B-1h

1. Confirm head: `git log -1 --oneline` should show this commit (B-1g close).
2. Read the existing `core/decision_grade.py` policy table for `PRESSURE_DROP` — mirror its shape exactly.
3. Decide on PRESSURE_HEADROOM rendering: per architect §3.6 it's tier-independent. The simplest implementation extends `decide_render_mode` with a sentinel; the alternative is a separate `decide_headroom_render_mode` function. Go with the simpler path.

---

## 6. Constraints to remember (anti-stale-context anchors)

- **`bead_d32` is sourced from `M1ExportContract.bead_d32`** (already on the dataclass — no new field added). The PBE solver (`level1_emulsification/solver.py`) already computes d32 in `_compute_statistics` and exports it through `EmulsificationResult`; no upstream change was needed.
- **`dsd_sigma_ln` was DECIDED NOT IMPLEMENTED.** The architect's "nice-to-have" sigma_ln is redundant given that `BeadSizeDistributionPayload.span` already exposes (d90 - d10) / d50 — an equivalent DSD-width characterization for the back-pressure work's purposes. Future fines-fraction work can derive σ_ln from span if needed.
- **Frit fields are `Optional[float] = None`** (default) — this preserves the existing 494-test baseline. Callers must explicitly set both fields (and the permeability must be > 0; thickness can be 0 but not negative) to activate the contribution. `frit_pressure_drop` returns 0.0 in all "no frit configured" cases.
- **The `pressure_drop` method is now BED-ONLY scope.** Total column ΔP = `pressure_drop(Q, μ)` + `frit_pressure_drop(Q, μ)`. B-2f's `compute_pressure_envelope` will sum the two; existing callers of `pressure_drop` continue to get bed-only ΔP unchanged.

---

## 7. Verification commands

```powershell
# B-1g new suites alone
.\.venv\Scripts\python -m pytest -q `
    tests\module3_performance\test_hydrodynamics_frit.py `
    tests\module3_performance\test_column_microsphere_wiring.py `
    -p no:cacheprovider
# Expected: 23 passed.

# Wide regression
.\.venv\Scripts\python -m pytest -q `
    tests\core\test_mobile_phase.py `
    tests\core\test_viscosity.py `
    tests\module3_performance\ `
    tests\test_v9_3_enum_comparison_enforcement.py `
    tests\test_evidence_tier.py `
    tests\test_v0_5_2_codex_fixes.py `
    tests\test_python_version_preflight.py `
    tests\test_cfd_zonal_pbe.py `
    tests\lifecycle\ `
    tests\core\test_recipe_validation.py `
    tests\core\test_recipe_validation_g7_ph.py `
    -p no:cacheprovider
# Expected: 316 passed.

# Lint / type
.\.venv\Scripts\python -m ruff check `
    src\dpsim\module3_performance\hydrodynamics.py `
    src\dpsim\module3_performance\method_simulation.py `
    tests\module3_performance\test_hydrodynamics_frit.py `
    tests\module3_performance\test_column_microsphere_wiring.py
.\.venv\Scripts\python -m mypy `
    src\dpsim\module3_performance\hydrodynamics.py
# Expected: ruff clean; mypy "Success: no issues found in 1 source file".
```

---

## 8. Quick links

- v0.7.0 work plan: `docs/update_workplan_2026-05-10_m3_pressure.md`
- Predecessor: `docs/handover/HANDOVER_b1f_viscosity_close.md`
- This handover: `docs/handover/HANDOVER_b1g_d32_frit_close.md`
- /scientific-advisor architecture: §A (KC + d_p source), §F (M1/M2 field map)
- /architect contract spec: §4 seam #2 (W-021), §4 seam #5 (W-024)
