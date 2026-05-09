# B-0d Close — Residual Hygiene Verification

**Date:** 2026-05-10
**Scope:** Closing the Tier 0 batch from `docs/update_workplan_2026-05-10_m3_pressure.md` — verification-only pass on the five "residual" W-items from the 2026-05-04 plan.
**Branch state at handover:** `main` at `650859e` (v0.6.6 release tag) + uncommitted one-line ruff fix on `tests/test_v9_3_enum_comparison_enforcement.py`.
**Authors:** `/scientific-advisor` + `/architect` + `/dev-orchestrator` (joint, this session).

---

## 1. Project context

DPSim v0.6.6 — clean main, 494 tests passing at release. The 2026-05-04 work plan §3 listed 19 open work items; v0.6.6 closed 14 of them and the plan itself listed five as "remaining" (W-012, W-013, W-014, W-015, W-018). Re-reading the closure record on 2026-05-10 showed that all five were in fact closed prior to v0.6.6 shipping — the "remaining 5" framing reflected the count at plan-authorship time (early 2026-05-04), not the closure state at release time (late 2026-05-04).

The new v0.7.0 work plan (`docs/update_workplan_2026-05-10_m3_pressure.md`) was authored 2026-05-10 to land the M3 back-pressure optimization (11 new W-items: W-020 … W-030). B-0d is the prerequisite-and-hygiene batch in that new plan; on inspection, it collapsed to verification-only.

---

## 2. Verification matrix

### 2.1 Per-W-item closure verification

| W-item | Source | Closure mechanism | File:line evidence | Status |
|---|---|---|---|---|
| **W-012** | doc MAJOR-4 | Resolved without new edit by F-arch A-007 prior to v0.6.6 | `core/recipe_validation.py:376–387` — comment correctly states "ARM_ACTIVATE has phase rank 3" matching the dict mapping `ARM_ACTIVATE: 3` | ✅ CLOSED |
| **W-013** | doc MINOR-3 | Commit `6303464` (B-0b) replaced the stale "datatypes.py mismatches" block | `cad/README.md` — grep for "datatypes.py mismatches" returns no matches | ✅ CLOSED |
| **W-014** | doc MINOR-1+2 | Commit `6303464` renamed the test fn + `EXEMPT_FILES` is referenced (not orphan) | `tests/test_v9_3_enum_comparison_enforcement.py:48` (defines `EXEMPT_FILES`), `:110` (`if rel in EXEMPT_FILES: return []`) | ✅ CLOSED |
| **W-015** | doc MINOR-4 | Commit `6303464` rewrote the gap-numbered rule list | `cfd/zonal_pbe.py` — grep for "Rule [1-6]" returns no matches | ✅ CLOSED |
| **W-018** | doc MINOR-7 (residual) | Inventory in `HANDOVER_tier_0_close_2026-05-04.md` §2 found all hits class-(a) legitimate references or class-(c) downgrade sentinels; B-3b cancelled | `optimization/objectives.py` — 6 `ModelEvidenceTier` literal sites; `module3_performance/catalysis/packed_bed.py` — 3 sites; total 9 (vs 11 in original inventory due to minor unrelated refactors). All sites class-(a)/class-(c) | ✅ CLOSED |

### 2.2 Incidental cleanup landed in this session (one line)

| File | Change | Reason |
|---|---|---|
| `tests/test_v9_3_enum_comparison_enforcement.py:31` | Removed unused `import pytest` | Pre-existing ruff F401 finding; one-line removal in the spirit of B-0d hygiene. AST-gate test still 3/3 passing after removal. |

### 2.3 Regression baseline (Tier 0 trio + AST gate + preflight + CFD)

```powershell
.\.venv\Scripts\python -m pytest -q `
    tests\test_v9_3_enum_comparison_enforcement.py `
    tests\test_evidence_tier.py `
    tests\test_v0_5_2_codex_fixes.py `
    tests\test_python_version_preflight.py `
    tests\test_cfd_zonal_pbe.py `
    -p no:cacheprovider
```

**Result: 95 passed in 27.87 s.** (Higher than the 76 the 2026-05-04 handover quoted — additional tests have been added through Tier 1 / Tier 2 closures since.)

### 2.4 Lint / type

| Gate | Command | Result |
|---|---|---|
| ruff | `ruff check src/dpsim/core/recipe_validation.py src/dpsim/cfd/zonal_pbe.py src/dpsim/optimization/objectives.py src/dpsim/module3_performance/catalysis/packed_bed.py tests/test_v9_3_enum_comparison_enforcement.py` | All checks passed ✓ (post the one-line `import pytest` removal) |
| mypy | `mypy src/dpsim/core/recipe_validation.py src/dpsim/cfd/zonal_pbe.py src/dpsim/optimization/objectives.py src/dpsim/module3_performance/catalysis/packed_bed.py` | 2 errors on `packed_bed.py` — both "Library stubs not installed for scipy.integrate" (`import-untyped`). Documented baseline noise per CLAUDE.md (v9.1.x decisions §3) — unchanged from v0.6.6. **Acceptable.** |

---

## 3. Module registry — current state

No module status changes from this batch. All v0.6.6 verdicts carry forward:

| Module | Verdict | Linked work items |
|---|---|---|
| `core/recipe_validation.py` | **APPROVED-WITH-FIX-LIST** (post v0.6.6 G7) — next status change at B-2h (G8 gate) | W-028 |
| `cad/README.md` | **APPROVED** (post W-013) | — |
| `tests/test_v9_3_enum_comparison_enforcement.py` | **APPROVED** (post W-014 + 2026-05-10 ruff fix) | — |
| `cfd/zonal_pbe.py` | **APPROVED** (post W-015) | — |
| `optimization/objectives.py` | **APPROVED** (W-018 inventory cleared 2026-05-04) | — |
| `module3_performance/catalysis/packed_bed.py` | **APPROVED** (W-018 inventory cleared 2026-05-04) | — |

---

## 4. Concrete starting point for next session — Tier 1, Bundle A

The M3 back-pressure optimization begins now. Three Tier 1 batches available, each independent:

### 4.1 Recommended ordering (foundation → consumers)

1. **B-1f (W-023)** — Buffer + viscosity foundation. New `core/mobile_phase.py` + `core/viscosity.py`. **Sonnet.** Independent quick win; ~150 LOC + lookup tables. **Recommended first** because Bundles B + D consume `MobilePhase` / `ViscosityResult`.
2. **B-1g (W-021 + W-024)** — Sauter d32 surfacing + frit fields. Cross-module M1 contract change (d32) + additive `Optional` fields on `ColumnGeometry`. **Sonnet for d32, Haiku for frit.** Can ship as one PR.
3. **B-1h (W-030)** — Decision-grade enum extension (`PRESSURE_LIMIT`, `Q_MAX`, `U_CRIT`, `PRESSURE_HEADROOM` OutputTypes + four policy rows). **Haiku.** Decoupled prerequisite for B-2f's render-path plumbing.

### 4.2 Pre-flight before B-1f

1. Confirm head is `650859e` (v0.6.6) or later: `git log -1 --oneline`.
2. Confirm working tree state: `git status` — should show only the 2026-05-10 ruff fix (`tests/test_v9_3_enum_comparison_enforcement.py`) + the new docs (`docs/update_workplan_2026-05-10_m3_pressure.md`, `docs/handover/HANDOVER_b0d_residual_hygiene_close.md`) as uncommitted.
3. Decide on commit cadence: optionally land B-0d's one-line lint fix + the new docs as a single hygiene commit before starting B-1f, OR roll into the B-1f PR.
4. Re-read the new work plan: `docs/update_workplan_2026-05-10_m3_pressure.md` §3.2 (Tier 1 batches).
5. Read the relevant scientific-advisor section (delivered upstream in this conversation) §D for the buffer-μ table; cross-check 1–2 coefficients against PubMed before declaring the protocol final.

### 4.3 Optional: commit B-0d before B-1f

```powershell
git add tests/test_v9_3_enum_comparison_enforcement.py docs/update_workplan_2026-05-10_m3_pressure.md docs/handover/HANDOVER_b0d_residual_hygiene_close.md
git commit -m "B-0d: residual hygiene verification + v0.7.0 plan + one-line ruff fix"
```

(User decision on commit timing; not auto-committed.)

---

## 5. Constraints to remember (anti-stale-context anchors for the v0.7.0 work)

- **The "5 residual items" claim in the 2026-05-04 plan §3 was outdated by v0.6.6 release time** — all five were closed. Future work plans should re-verify residual lists against the matching close-handover before treating any item as open.
- **mypy baseline noise is `scipy-stubs` library-not-installed warnings only** (CLAUDE.md v9.1.x decisions §3). The CI cap is "0 NEW issues on changed source files"; the baseline noise must remain unchanged through the v0.7.0 work.
- **Family-First UI contract (v9.0)** — all PolymerFamily / ACSSiteType / ModelEvidenceTier / ModelMode comparisons by `.value`, never `is` / `is not`. Enforced by the AST gate at `tests/test_v9_3_enum_comparison_enforcement.py`.
- **B-2c SI boundary helpers** (`as_si_flow_rate_m3_per_s`, `as_si_pressure_pa`, `as_si_volume_m3`, etc.) — used at all new recipe-input boundaries in the v0.7.0 work. Do not invent parallel SI conversion paths.
- **B-2e M3 quantitative gates** already track `pressure_flow_calibrated`. The v0.7.0 work plan reuses this dimension for tier promotion; do not introduce a parallel mechanism.
- **B-2e `LoadedStateElutionResult.gradient_diagnostics`** is the typed handle for per-step μ_peak in elution. The v0.7.0 work plan reads from this field; do not duplicate in the new pressure-envelope code.
- **Validation release-gate ladder** — work plan §4 of `docs/update_workplan_2026-05-10_m3_pressure.md` adds gates 6, 7, 8 specific to back-pressure. Public-communication framing constraint at §4.3 — DPSim v0.7.0 ships as **"research-grade screening simulator with first-principles back-pressure envelopes"**, never as "validated for back-pressure-safe column operation."

---

## 6. Verification commands (for resume / cold-start sanity check)

```powershell
# Confirm head + clean tree intent
git log -3 --oneline
git status

# Confirm version + preflight live
.\.venv\Scripts\python -c "import dpsim; print(f'dpsim {dpsim.__version__} on Python {__import__(\"sys\").version_info[:2]}')"
# Expected: dpsim 0.6.6 on Python (3, 12)

# Tier 0 regression baseline (this batch's regression target)
.\.venv\Scripts\python -m pytest -q `
    tests\test_v9_3_enum_comparison_enforcement.py `
    tests\test_evidence_tier.py `
    tests\test_v0_5_2_codex_fixes.py `
    tests\test_python_version_preflight.py `
    tests\test_cfd_zonal_pbe.py `
    -p no:cacheprovider
# Expected: 95 passed in ~30 s.

# ruff on the touched paths
.\.venv\Scripts\python -m ruff check `
    src/dpsim/core/recipe_validation.py `
    src/dpsim/cfd/zonal_pbe.py `
    src/dpsim/optimization/objectives.py `
    src/dpsim/module3_performance/catalysis/packed_bed.py `
    tests/test_v9_3_enum_comparison_enforcement.py
# Expected: All checks passed!
```

---

## 7. Quick links

- v0.7.0 work plan: `docs/update_workplan_2026-05-10_m3_pressure.md`
- Prior plan: `docs/update_workplan_2026-05-04.md`
- Prior Tier 0 close (the actual W-012..W-018 closure record): `docs/handover/HANDOVER_tier_0_close_2026-05-04.md`
- This handover: `docs/handover/HANDOVER_b0d_residual_hygiene_close.md`
- Validation release-gate ladder: §4 of v0.7.0 plan + §5 of 2026-05-04 plan
