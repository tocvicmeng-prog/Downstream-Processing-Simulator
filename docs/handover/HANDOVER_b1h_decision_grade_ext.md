# B-1h Close — Decision-Grade Enum Extension

**Date:** 2026-05-10
**Scope:** Closing batch B-1h from `docs/update_workplan_2026-05-10_m3_pressure.md` — third and last Tier 1 batch; closes W-030 (Δ1 follow-on, decoupled prerequisite for B-2f).
**Branch state at handover:** `main` at `df7f236` (B-1g close) + uncommitted B-1h files.
**Authors:** `/architect` (contract), `/scientific-coder` (implementation).

---

## 1. What landed

| File | Change |
|---|---|
| `src/dpsim/core/decision_grade.py` | +24 LOC — added 4 new `OutputType` members (`PRESSURE_LIMIT`, `Q_MAX`, `U_CRIT`, `PRESSURE_HEADROOM`) + 4 rows in `DECISION_GRADE_POLICY`. PRESSURE_LIMIT/Q_MAX/U_CRIT mirror `PRESSURE_DROP` (floor `SEMI_QUANTITATIVE` → INTERVAL render at QUALITATIVE_TREND). PRESSURE_HEADROOM is tier-independent (floor `QUALITATIVE_TREND` → renders as NUMBER for any reasonable envelope tier). |
| `tests/core/test_decision_grade.py` | Updated existing `test_unsupported_always_suppresses` to handle the four new outputs (RANK_BAND for the SEMI-floor trio + INTERVAL for PRESSURE_HEADROOM). |
| `tests/core/test_decision_grade_pressure_outputs.py` (NEW) | 26 cases — enum membership (4), policy table rows (4), render-mode at each ladder step for PRESSURE_LIMIT/Q_MAX/U_CRIT/PRESSURE_HEADROOM (12), cross-policy consistency (2), tier-floor ordering (1). |

**Total: 26 new + 1 updated test cases.**

## 2. Verification

- `tests/core/test_decision_grade_pressure_outputs.py`: 26 passed
- `tests/core/test_decision_grade.py` (existing + 1 updated): 48 passed
- AST gate: 3/3 passing
- Combined sweep (B-1f + B-1g + B-1h + Tier 0): see commit verification command
- ruff: clean on both touched paths
- mypy: 0 issues on `decision_grade.py`

## 3. Module registry update

| Module | Status before | Status after |
|---|---|---|
| `core/decision_grade.py` | APPROVED (post v0.6.6 B-1b) | **APPROVED** (post B-1h enum + policy extension) |

All Tier 1 batches now closed:
- B-1f (`core/mobile_phase.py`, `core/viscosity.py`) — APPROVED
- B-1g (`hydrodynamics.py` frit + `method_simulation.py` d32) — APPROVED
- B-1h (`decision_grade.py` ext) — APPROVED

## 4. Next up — B-2f KEYSTONE (Tier 2)

**B-2f** is the science-fix keystone: replace `max_safe_flow_rate` (`safety × E_star`, scientifically wrong by 5–50× factor) with u_crit-based formula `u_crit = K_geom_family · G_DN · d32² / (μ·L)`. **Milestone handover required at close** per work plan §5.

Sub-modules to create in B-2f:
- `module3_performance/family_kgeom.py` — `FAMILY_KGEOM_REGISTRY` keyed by `PolymerFamily.value` (5 families: alginate, agarose, agarose_chitosan, cellulose, PLGA), each with K_geom, valid_domain, base_tier, literature_anchor.
- `module3_performance/pressure_envelope.py` — `PressureEnvelope` frozen dataclass + `compute_pressure_envelope` orchestrator + tier-rollup walking valid_domain.
- `module3_performance/hydrodynamics.py` — deprecate `max_safe_flow_rate` with `DeprecationWarning`.
- `docs/decisions/ADR-pressure-envelope-anchor.md` — ADR documenting the u_crit derivation.

Test target: ~60 new tests in 3 new files. Estimated context: 70–90K. Model tier: Opus for design refinement; Sonnet for impl + tests.

## 5. Quick links

- v0.7.0 work plan: `docs/update_workplan_2026-05-10_m3_pressure.md`
- Predecessor: `docs/handover/HANDOVER_b1g_d32_frit_close.md`
- This handover: `docs/handover/HANDOVER_b1h_decision_grade_ext.md`
- /architect contract spec: §3.6 (decision_grade extension shape)
