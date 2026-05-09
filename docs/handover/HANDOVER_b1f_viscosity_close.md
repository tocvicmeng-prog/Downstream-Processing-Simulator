# B-1f Close — Buffer + Viscosity Foundation

**Date:** 2026-05-10
**Scope:** Closing batch B-1f from `docs/update_workplan_2026-05-10_m3_pressure.md` — first Tier 1 batch of the v0.7.0 M3 back-pressure work; closes W-023 (Δ4 from the /scientific-advisor architecture).
**Branch state at handover:** `main` at `708b48d` (B-0d close commit) + uncommitted B-1f files.
**Authors:** `/scientific-advisor` (literature anchors) + `/architect` (contract design) + `/scientific-coder` (implementation, this session).

---

## 1. Project context

DPSim v0.6.6 hardcoded mobile-phase dynamic viscosity to `μ = 1×10⁻³ Pa·s` (water at 20 °C) inside `module3_performance/hydrodynamics.py`. The /scientific-advisor architecture identified this as one of the three CRITICAL correctness defects in the M3 hydrodynamics module — cold-room runs (5 °C), HIC load buffers (high salt), glycerol-stabilization steps (φ_glycerol = 0.10–0.30), and NaOH/ethanol CIP cycles (φ_ethanol up to 0.70) shift μ by 50–500 % vs water-at-20 °C, silently underestimating ΔP and risking bead crush during sanitization.

B-1f is the **foundational** Tier 1 batch — it establishes the typed `MobilePhase` value object and the `resolve_mobile_phase_viscosity` function that downstream Bundles B (W-020 keystone) and D (W-025 lifecycle wire-in, W-028 G8 gate, W-029 UI section) consume. Independent of the other Tier 1 batches (B-1g d32+frit, B-1h decision_grade extension); shippable alone.

---

## 2. Files delivered

### 2.1 Source (2 new modules)

| File | LOC | Purpose |
|---|---|---|
| `src/dpsim/core/mobile_phase.py` | 76 | `MobilePhase` frozen dataclass per architect §3.1 — name, T_C, c_nacl_M, phi_glycerol, phi_ethanol, pH, custom_mu_pa_s. |
| `src/dpsim/core/viscosity.py` | 244 | `ViscosityResult` frozen dataclass + `water_viscosity_pa_s(T_C)` table + `resolve_mobile_phase_viscosity(mobile_phase, extrapolation_policy)` resolver per architect §3.2. |

### 2.2 Tests (2 new files)

| File | Test cases | Coverage |
|---|---|---|
| `tests/core/test_mobile_phase.py` | 14 | Defaults, frozen behaviour, custom-override field plumbing, four canonical buffer compositions (HIC load, glycerol stabilization wash, cold-room equilibration, IMAC elute). |
| `tests/core/test_viscosity.py` | 55 | Water-T table (12 anchor points + 2 interpolation cases + 2 out-of-range), NaCl additive (3 cases at 0/1/2 M), glycerol additive (20 % anchor, 30 % calibration edge, 40 % extrapolation flag), ethanol additive (20 % anchor, 70 % CIP extrapolation), combined-composition stack (2 cases), cold-room temperature effect (3 cases), custom override path (6 cases), extrapolation policy modes (5 cases — warn/silent/raise/invalid/in-window), tier rollup (3 cases), pathological inputs (7 cases — negative salt/glycerol/ethanol, > 1.0 fractions, T below/above water table), provenance fields (5 cases). |

**Total: 69 new test cases.**

### 2.3 No modifications to existing source files (foundational batch).

---

## 3. Scientific anchors

The literature references for the additive-model coefficients are recorded in the module docstring of `core/viscosity.py`:

| Anchor | Source | Coefficient | Calibration window |
|---|---|---|---|
| μ_water(T) | CRC Handbook 92nd ed. (2011-2012) via Crittenden 2012 App. C | 12-point table at 0/5/10/15/20/25/30/40/50/60/70/80 °C; linear interp between | 0–80 °C |
| α_salt | Out & Los 1980, Jones-Dole-style fit at 1 M anchor (μ/μ_water at 25 °C ≈ 1.099) | 0.10 / M | up to ~2 M (linear regime acknowledged approximate at 2 M) |
| α_gly (glycerol) | Cheng 2008 glycerol-water | 3.5 per unit φ | φ ≤ 0.30 |
| α_etoh (ethanol) | Khattab 2017 ethanol-water | 5.9 per unit φ | φ ≤ 0.30 |

Cross-terms (T × salt, T × glycerol, T × ethanol) are first-order ignored. The resolver flags `extrapolated=True` in three cases:

1. `|T_C − 25| > 15 °C` AND non-zero co-solvent (`φ_glycerol > 0` or `φ_ethanol > 0`).
2. `phi_glycerol > 0.30` (linear-regime limit).
3. `phi_ethanol > 0.30` (linear-regime limit; also where ethanol-water exhibits a viscosity maximum near φ = 0.40–0.45).

---

## 4. Tier policy

Implemented per architect §6.1 forward audit:

| Resolution path | `tier` | `extrapolated` | `method` | Notes |
|---|---|---|---|---|
| `MobilePhase.custom_mu_pa_s = X > 0` | `CALIBRATED_LOCAL` | `False` (always) | `"custom_override"` | User-supplied viscometry |
| Additive model, in calibration window | `SEMI_QUANTITATIVE` | `False` | `"additive_model"` | Default path |
| Additive model, out of calibration window | `SEMI_QUANTITATIVE` | `True` | `"additive_model"` | Returned with notes string; downstream `PressureEnvelope.decision_tier` rollup (B-2f) reads the flag and demotes one step |

The result-level tier does NOT auto-demote on `extrapolated=True`; that demotion happens in Bundle B's `compute_pressure_envelope` rollup (architect §3.4 / §4 seam #7) and is intentionally separated from this module. Reasoning: the same `ViscosityResult` may be consumed by callers with different tolerance for extrapolation (e.g., a UI badge vs a release-gate check), and forcing the demotion at resolution time would lose information.

---

## 5. Module registry update

| Module | Owner | Status before | Status after |
|---|---|---|---|
| `src/dpsim/core/mobile_phase.py` | architect | NOT STARTED | **APPROVED** (post B-1f) |
| `src/dpsim/core/viscosity.py` | architect | NOT STARTED | **APPROVED** (post B-1f); target tier `SEMI_QUANTITATIVE` for the additive model, `CALIBRATED_LOCAL` on `custom_mu_pa_s` override |

No status changes for existing modules — B-1f is purely additive. Bundle B (B-2f) consumers don't exist yet; integration verified in their respective batches.

---

## 6. Verification matrix

### 6.1 Test runs

| Suite | Result |
|---|---|
| New B-1f suites (`test_mobile_phase.py`, `test_viscosity.py`) | **69/69 passed** in 0.13 s |
| Tier 0 regression baseline (5 files: AST gate, evidence-tier, codex P2-1 fixes, Python preflight, CFD zonal PBE) | **95/95 passed** in ~27 s |
| Combined run (B-1f + Tier 0) | **164/164 passed** in 26.90 s |

### 6.2 Lint / type / AST gate

| Gate | Result |
|---|---|
| ruff on B-1f files (4 paths) | All checks passed ✓ |
| mypy on B-1f source (2 paths) | Success: no issues found in 2 source files |
| AST gate (`tests/test_v9_3_enum_comparison_enforcement.py`) | 3/3 passing — no new `is`/`is not` against PolymerFamily/ACSSiteType/ModelEvidenceTier/ModelMode introduced |

---

## 7. Concrete starting point for next session — B-1g

B-1f is independent of B-1g. The two can ship in the same PR or separately at the user's discretion. Per the work plan, B-1g closes **W-021 (Sauter d32 surfacing) + W-024 (frit / fitting series resistance)**.

### 7.1 W-021 (Δ2) — Sauter d32

Files to touch:

- `src/dpsim/level1_emulsification/solver.py` — surface `bead_d32` and `dsd_sigma_ln` flat fields from the PBE result (currently only `bead_d50` is exposed via `m1_contract`).
- `src/dpsim/module2_functionalization/orchestrator.py` — extend `FunctionalMicrosphere.m1_contract` to carry `bead_d32` and `dsd_sigma_ln`.
- `src/dpsim/module3_performance/method_simulation.py:316` and `:520` — replace `m1.bead_d50` with `m1.bead_d32` in `_column_with_microsphere`.

Expected behaviour: at typical σ_ln = 0.3, `d32 ≈ 0.80 · d50` → ΔP correction factor ≈ 1.56× higher (since ΔP ∝ d_p⁻²). New tests:

- `tests/level1_emulsification/test_d32_emission.py` — assert d32 surfaced from PBE; assert d32 ≈ 0.80·d50 for σ_ln = 0.3 lognormal.
- `tests/module3_performance/test_column_microsphere_wiring.py` — assert `_column_with_microsphere` reads `m1.bead_d32`, not `bead_d50`; ΔP correction factor in expected range.

### 7.2 W-024 (Δ5) — Frit resistance

Files to touch:

- `src/dpsim/module3_performance/hydrodynamics.py:21` — add `Optional` `frit_permeability_m2` and `frit_thickness_m` fields to `ColumnGeometry` (default `None`); add new method `frit_pressure_drop(Q, μ) → float` returning `μ·u·t/k_f` if both fields set, else `0.0`.

New tests:

- `tests/module3_performance/test_hydrodynamics_frit.py` — 8 cases (frit on/off, ΔP_frit additivity, default `Optional = None` preserves backwards compat).

### 7.3 Pre-flight before B-1g

1. Confirm head: `git log -1 --oneline` should show this commit (B-1f close).
2. Re-run the Tier 0 baseline: 95 tests passing (sanity).
3. Read /scientific-advisor §A (the d_p source defect — d50 vs d32, ~1.56× ΔP correction) and /architect §4 seams #2 + #5.

---

## 8. Constraints to remember (anti-stale-context anchors)

- **Default `MobilePhase()` is "equilibration buffer at 20 °C"** — name="equilibration", T_C=20.0, c_nacl_M=0.150, phi_gly=0.0, phi_etoh=0.0, pH=7.4, custom_mu_pa_s=None. Use this as the implicit default for any recipe step that doesn't override the buffer.
- **`custom_mu_pa_s` is the escape hatch** for any buffer outside the additive model's calibration window — high-arginine refold buffers, custom polymer additives, non-standard ionic strengths. Setting it bypasses the additive model entirely and promotes tier to CALIBRATED_LOCAL.
- **The resolver does NOT consume `pH`** in v0.7.0. The pH field is carried for the G7 reagent-pH-window cross-check (B-1a precedent) and for future buffer-capacity diagnostics. Don't add pH-dependent μ corrections without an ADR.
- **Cross-terms (T × co-solvent) are first-order ignored.** If a future use case requires accuracy at e.g. 50 % glycerol at 5 °C, add the `extrapolated=True` flag handling first; do not silently fold cross-terms into the linear coefficients.
- **The water-table range is [0, 80] °C.** Outside this raises `ValueError`. CIP at 90 °C is rare but possible — if a use case appears, extend the table from CRC handbook values (90 °C: ~3.15e-4 Pa·s) rather than allowing extrapolation.
- **`extrapolated=True` does NOT auto-demote tier** at the result level. The demotion happens in B-2f's `PressureEnvelope.decision_tier` rollup. If a different consumer needs the demotion at result level, wrap the call site rather than changing this module.

---

## 9. Verification commands

```powershell
# B-1f new suites alone
.\.venv\Scripts\python -m pytest -q `
    tests\core\test_mobile_phase.py `
    tests\core\test_viscosity.py `
    -p no:cacheprovider
# Expected: 69 passed.

# B-1f + Tier 0 baseline
.\.venv\Scripts\python -m pytest -q `
    tests\core\test_mobile_phase.py `
    tests\core\test_viscosity.py `
    tests\test_v9_3_enum_comparison_enforcement.py `
    tests\test_evidence_tier.py `
    tests\test_v0_5_2_codex_fixes.py `
    tests\test_python_version_preflight.py `
    tests\test_cfd_zonal_pbe.py `
    -p no:cacheprovider
# Expected: 164 passed.

# Lint / type
.\.venv\Scripts\python -m ruff check `
    src\dpsim\core\mobile_phase.py `
    src\dpsim\core\viscosity.py `
    tests\core\test_mobile_phase.py `
    tests\core\test_viscosity.py
.\.venv\Scripts\python -m mypy `
    src\dpsim\core\mobile_phase.py `
    src\dpsim\core\viscosity.py
# Expected: ruff clean; mypy "Success: no issues found in 2 source files".
```

---

## 10. Quick links

- v0.7.0 work plan: `docs/update_workplan_2026-05-10_m3_pressure.md`
- B-0d close (this batch's predecessor): `docs/handover/HANDOVER_b0d_residual_hygiene_close.md`
- This handover: `docs/handover/HANDOVER_b1f_viscosity_close.md`
- /scientific-advisor architecture: §D (mobile-phase factors / viscosity table) — delivered upstream in the 2026-05-10 conversation
- /architect contract spec: §3.1 (`MobilePhase`), §3.2 (`BufferViscosityModel` + `ViscosityResult`)
- Validation release-gate ladder: §4 of v0.7.0 plan + §5 of 2026-05-04 plan
