# B-2f Close — Pressure Envelope Science Fix (KEYSTONE)

**Date:** 2026-05-10
**Scope:** Closing batch B-2f from `docs/update_workplan_2026-05-10_m3_pressure.md` — the keystone Tier 2 batch of v0.7.0 M3 back-pressure work; closes W-020 (Δ1 ΔP_max anchor replacement) and W-026 (Δ7 per-family valid_domain).
**Branch state at handover:** `main` at `f9bb5c7` (B-1h close) + uncommitted B-2f files.
**Authors:** `/scientific-advisor` (u_crit derivation, K_geom anchors), `/architect` (contract design + tier rollup), `/scientific-coder` (implementation).
**Milestone status:** **CRITICAL milestone reached.** This is the architecturally largest batch of v0.7.0; all subsequent batches (B-2g, B-2h, B-3d) consume the `PressureEnvelope` value type and `compute_pressure_envelope` orchestrator delivered here.

---

## 1. The defect this batch closes

DPSim v0.6.6 anchored ΔP_max to `safety × E_star` (the bursting modulus). For soft chromatography media the *operational* limit is set by **bed-compression u_crit**, not by **bead bursting**; the two are physically distinct and u_crit is typically 5–50× lower than the bursting limit. The v0.6.6 code silently approved flow rates that would crush beads in real operation. ADR-004 documents the full decision rationale.

This was the most serious correctness defect identified in the M3 hydrodynamics module by the /scientific-advisor architecture review on 2026-05-10.

---

## 2. Files delivered

### 2.1 New source modules (2)

| File | LOC | Purpose |
|---|---|---|
| `src/dpsim/module3_performance/family_kgeom.py` | 245 | Per-PolymerFamily K_geom registry + valid_domain + lookup dispatch by `.value` (v9.0 Family-First contract). 5 default-anchor families (agarose, agarose_chitosan, cellulose, plga, alginate) at SEMI_QUANTITATIVE base_tier. Conservative fallback at QUALITATIVE_TREND for unregistered families. |
| `src/dpsim/module3_performance/pressure_envelope.py` | 332 | `PressureEnvelope` frozen dataclass + `compute_pressure_envelope` orchestrator. Resolves μ via B-1f viscosity model, looks up K_geom, computes u_crit, inverts to Q_max, evaluates KC ΔP_predicted, sums frit contribution from B-1g, walks valid_domain + viscosity.extrapolated for tier rollup, populates calibration provenance map for the dossier export. |

### 2.2 Source modifications (2)

| File | Change |
|---|---|
| `src/dpsim/module3_performance/hydrodynamics.py` | Deprecated `max_safe_flow_rate` with `DeprecationWarning`. Method retained for one release (v0.7.x); removed in v0.8. Docstring rewritten to point at `compute_pressure_envelope`. |
| `src/dpsim/module3_performance/__init__.py` | Exported `FAMILY_KGEOM_REGISTRY`, `FamilyKGeom`, `PressureEnvelope`, `check_valid_domain`, `compute_pressure_envelope`, `is_family_registered`, `lookup_family_kgeom`, `registered_families`. |

### 2.3 New tests (3 files, 79 cases)

| File | Test cases |
|---|---|
| `tests/module3_performance/test_family_kgeom.py` | 39 (registry coverage, K_geom ordering vs literature, valid_domain field shapes, base_tier, lookup dispatch by .value, fallback, check_valid_domain violation detection, frozen contract) |
| `tests/module3_performance/test_pressure_envelope.py` | 33 (end-to-end smoke, operational vs burst ceilings, u_crit scaling laws, Q_max + Q_recommended, headroom ratio + warning/blocker derivation, tier rollup, calibration_store override, frit contribution, provenance fields, pathological inputs, frozen contract) |
| `tests/module3_performance/test_hydrodynamics_deprecation.py` | 7 (DeprecationWarning emission, replacement reference in warning + docstring, value still computed during deprecation window) |

### 2.4 New ADR

| File | Purpose |
|---|---|
| `docs/decisions/ADR-004-pressure-envelope-anchor.md` | Full decision rationale: defect → replacement → consequences → validation → references. Documents the per-family K_geom anchor table and the SEMI_QUANTITATIVE → CALIBRATED_LOCAL promotion path. |

---

## 3. Verification matrix

### 3.1 Test runs

| Suite | Result |
|---|---|
| New B-2f suites alone (3 files) | **79/79 passed** in 0.17 s |
| Wide regression: B-1f + B-1g + B-1h + B-2f + Tier 0 baseline + lifecycle + recipe_validation + all `tests/core/` | **637/637 passed** in 92.79 s |

### 3.2 Lint / type / AST gate

| Gate | Result |
|---|---|
| ruff on B-2f files (7 paths) | All checks passed ✓ (after 1-line F401 fix) |
| mypy on B-2f source (3 paths) | Success: no issues found in 3 source files |
| AST gate (`tests/test_v9_3_enum_comparison_enforcement.py`) | 3/3 passing — no new `is`/`is not` against PolymerFamily/ACSSiteType/ModelEvidenceTier/ModelMode |

### 3.3 Smoke test

Realistic Sepharose 4FF analytical column (D = 1 cm, L = 10 cm, d32 = 90 µm, G_DN = 5 kPa, water at 20 °C):

- u_crit ≈ **717 cm/h** — within the published Sepharose envelope (300–700 cm/h ✓).
- At 200 cm/h operating: headroom = 0.28 (safe ✓).
- At 600 cm/h operating: headroom = 0.84 (warning band ✓).
- Above u_crit: headroom > 1.0 (blocker ✓).

---

## 4. Module registry update

| Module | Owner | Status before | Status after |
|---|---|---|---|
| `module3_performance/family_kgeom.py` | architect | NOT STARTED | **APPROVED** (post-B-2f) |
| `module3_performance/pressure_envelope.py` | architect | NOT STARTED | **APPROVED** (post-B-2f); B-2g (W-022) will add iteration without API change |
| `module3_performance/hydrodynamics.py` | architect | APPROVED-WITH-FIX-LIST | **APPROVED** (post-B-2f deprecation; B-2g iterate_kc_compression follow-on does not change existing API) |

All Tier 1 + the keystone Tier 2 batch closed. v0.7.0 progress: 5/11 W-items (W-021, W-023, W-024, W-030, W-020+W-026 closed; W-022 / W-025 / W-027 / W-028 / W-029 remain).

---

## 5. Concrete starting point for next session — B-2g

B-2g is the iteration refinement: replace the one-shot Kozeny-Carman in `compute_pressure_envelope` with a fixed-point ε_b feedback loop. Captures runaway behaviour near u_crit. Sonnet tier; ~80 LOC + 15 tests.

### 5.1 W-022 (Δ3) — ε_b iteration

Files to touch:

- `src/dpsim/module3_performance/hydrodynamics.py` — add `iterate_kc_compression(geometry, Q, μ, max_iter=50, tol=1e-4) → tuple[ΔP, ε_b_final, n_iter, converged]`. Iterate the (ε_b, ΔP) fixed point: starting from `ε_b_0`, compute ΔP via KC, compute compression `δL/L = ΔP/(E_star·(1-ε_b))`, derive new `ε_b_new` from the volumetric balance (bed shortens, particles stay; new ε_b is lower), repeat until `|ε_b_new - ε_b_prev| < tol` or iteration ceiling. Floor ε_b at 0.10 to prevent divide-by-zero. Set `converged = False` if iteration ceiling hit; this triggers tier downgrade in the envelope.

- `src/dpsim/module3_performance/pressure_envelope.py::compute_pressure_envelope` — consume the new iterated form. **API does not change** — `dP_predicted_pa` simply becomes the iterated value.

- `tests/module3_performance/test_pressure_envelope_iteration.py` (NEW) — 15 cases (convergence within tol, max_iter ceiling enforced, ε_b floor, runaway detection, smooth-flow agreement with one-shot to within 0.5 % when far from u_crit).

### 5.2 Pre-flight before B-2g

1. Confirm head: `git log -1 --oneline` should show this commit (B-2f close).
2. Re-run the new test suite (79 cases) to confirm baseline before adding iteration.
3. Decide on the iteration's volumetric model: simplest is "bed shortens, A constant, particles unchanged". Alternative is "ε_b, ε_p both decrease" — defer this to a future ADR if needed.

### 5.3 After B-2g

B-2h (UX wiring: lifecycle/orchestrator.py post-M2 wire-in + G8 gate in recipe_validation.py + tab_m3.py UI section). This is the largest UX-facing batch. Plan for `/qa-only` triple-tier pass before merge per work plan §3.3.

Then B-3d (pressure_monitor.py streaming function, Tier 3 maintenance). v0.7.0 release follows.

---

## 6. Constraints to remember (anti-stale-context anchors)

- **u_crit formula:** `u_crit = K_geom_family · G_DN · d32² / (μ · L)`. The dimensional-check matches m/s. For agarose 4% at L = 10 cm, μ = 1×10⁻³, G_DN = 5 kPa, d32 = 90 µm with K_geom = 5×10⁻³ → u_crit ≈ 720 cm/h. THIS IS THE OPERATIONAL CEILING. The bursting ceiling (E_star) is a SEPARATE diagnostic.
- **Two distinct pressure ceilings.** `PressureEnvelope.dP_max_operational_pa` is the u_crit-based bed-compression limit (the operational ceiling, what the user must NEVER exceed). `PressureEnvelope.dP_max_burst_pa` = `E_star` is the bed elastic-limit diagnostic, NOT the actual cracking threshold (which is 5–10× higher per Hertz contact / K_IC scaling — out of v0.7 scope per ADR-004 §"Out of scope").
- **K_geom anchors are literature defaults, not wet-lab calibrations.** Per validation release-gate 7 (work plan §4.2) and the public-communication framing constraint at §4.3, DPSim v0.7 must NEVER be communicated as "validated for back-pressure-safe column operation" — only as "research-grade screening simulator with first-principles back-pressure envelopes". Tier promotion to CALIBRATED_LOCAL requires `calibration_store` entries with manufacturer pressure-flow curves OR local wet-lab data.
- **Tier rollup demotes one step per dimension.** valid_domain violation → 1 step demote. viscosity.extrapolated=True → 1 step demote. Both → 2 steps. Floor at QUALITATIVE_TREND. The fallback registry entry (for unregistered families) carries QUALITATIVE_TREND base_tier, so any demotion immediately floors.
- **PolymerFamily comparison by `.value`** per v9.0 Family-First contract, enforced by AST gate. The lookup function `lookup_family_kgeom` follows this contract; never compare PolymerFamily members by `is` or by direct equality on the enum object.
- **Deprecated `max_safe_flow_rate` is RETAINED for v0.7.x.** It still works, returns the bursting bound, and emits a `DeprecationWarning`. Do NOT remove it in this release; v0.8 removal needs a separate audit of internal call sites (some are still in `method_simulation.py` and similar). 23 deprecation warnings fire in the existing test suite — these are EXPECTED, not regressions.

---

## 7. Verification commands

```powershell
# B-2f new suites alone
.\.venv\Scripts\python -m pytest -q `
    tests\module3_performance\test_family_kgeom.py `
    tests\module3_performance\test_pressure_envelope.py `
    tests\module3_performance\test_hydrodynamics_deprecation.py `
    -p no:cacheprovider
# Expected: 79 passed.

# Wide regression (B-1f + B-1g + B-1h + B-2f + Tier 0 baseline + lifecycle)
.\.venv\Scripts\python -m pytest -q `
    tests\core\ tests\module3_performance\ `
    tests\test_v9_3_enum_comparison_enforcement.py `
    tests\test_evidence_tier.py tests\test_v0_5_2_codex_fixes.py `
    tests\test_python_version_preflight.py tests\test_cfd_zonal_pbe.py `
    tests\lifecycle\ -p no:cacheprovider
# Expected: 637 passed (with 23 expected DeprecationWarnings).

# Lint / type
.\.venv\Scripts\python -m ruff check src\dpsim\module3_performance\family_kgeom.py `
    src\dpsim\module3_performance\pressure_envelope.py `
    src\dpsim\module3_performance\hydrodynamics.py `
    src\dpsim\module3_performance\__init__.py
.\.venv\Scripts\python -m mypy src\dpsim\module3_performance\family_kgeom.py `
    src\dpsim\module3_performance\pressure_envelope.py `
    src\dpsim\module3_performance\hydrodynamics.py
# Expected: ruff clean; mypy 0 issues.

# Smoke test (interactive)
.\.venv\Scripts\python -c "
from dpsim.core.mobile_phase import MobilePhase
from dpsim.datatypes import PolymerFamily
from dpsim.module3_performance import ColumnGeometry, compute_pressure_envelope
col = ColumnGeometry(diameter=0.01, bed_height=0.10, particle_diameter=90e-6,
    bed_porosity=0.38, particle_porosity=0.70, G_DN=5000.0, E_star=15000.0)
env = compute_pressure_envelope(polymer_family=PolymerFamily.AGAROSE,
    column=col, mobile_phase=MobilePhase(), Q_set_m3_s=1e-9)
print(f'u_crit: {env.u_crit_m_s*100*3600:.0f} cm/h, tier: {env.decision_tier.value}')
"
# Expected: u_crit ≈ 717 cm/h, tier: semi_quantitative
```

---

## 8. Quick links

- v0.7.0 work plan: `docs/update_workplan_2026-05-10_m3_pressure.md`
- ADR for the anchor swap: `docs/decisions/ADR-004-pressure-envelope-anchor.md`
- Predecessor handover: `docs/handover/HANDOVER_b1h_decision_grade_ext.md`
- This handover: `docs/handover/HANDOVER_v0_7_b2f_pressure_envelope_KEYSTONE.md`
- /scientific-advisor architecture: §A (KC physics), §B (u_crit derivation), §F (M1/M2 field map), §G (decision-grade tier rollup)
- /architect contract spec: §3.3 (PressureEnvelope), §3.4 (compute_pressure_envelope), §3.7 (FamilyKGeom), §4 seam #1 + #7
