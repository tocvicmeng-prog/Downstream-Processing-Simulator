# HANDOVER — v0.8.9 release close

**Date:** 2026-05-10
**Tag:** v0.8.9
**Work plan:** `docs/update_workplan_2026-05-10_v0_9_0.md` §3 (now fully closed)
**Theme:** Close all 7 W-items deferred at v0.8.8 close.

## Summary

v0.8.9 closes the remaining deferred W-items. With v0.8.9 every W-item from the joint v0.9.0 plan §3 is resolved (cumulative v0.8.8 + v0.8.9). The dashboard has traversed every audit-driven maturation milestone: honest → complete → wet-lab-credible → fully-mature-as-scoped.

## Closed W-items (7)

| W-ID | Title | Audit defect closed |
|---|---|---|
| W-081 | Tier-routing CI gate (baseline-anchored) | S-10, A-15 (companion to AST gate W-073) |
| W-083 | Single source-of-truth for pre-flight envelope | A-12 |
| W-084 | M3 geometry + flow → recipe writethrough | S-13, U-7, A-13 |
| W-087 | `tab_m3.py` refactor — proof-of-pattern (`tabs/m3/`) | A-18 (partial; full split queued for v1.0) |
| W-092 | RecoveryAction → 3 clickable controls + bench-only labels | U-23 |
| W-096 | Unit-conversion crib in measurement editor | U-24 (partial; full sweep queued for v1.0) |
| W-102 | Removed orphan `m3_latest_state` write | A-10 |

## NEW modules

| Path | LOC | Purpose |
|---|---|---|
| `tabs/m3/__init__.py` + `method_conditions_section.py` | ~85 | First proof-of-pattern split of `tab_m3.py` |
| `tests/visualization/test_tier_routing_gate.py` | ~110 | CI gate (baseline 43 bare metric callsites) |

## Modified modules

| Path | Change |
|---|---|
| `tab_m3.py` | Method-conditions section extracted; parallel pre-flight compute consolidated to single source-of-truth via session_state |
| `tab_m3_monitor.py` | Orphan `m3_latest_state` write removed; new `_render_recovery_action_controls` for clickable controls |
| `ui_workflow.py` | Recipe M3 PACK_COLUMN + LOAD steps now updated from session_state before lifecycle invocation |
| `tabs/calibration/inverse_inference.py` | Unit-conversion crib added to measurement editor |

## Verification

- **2 new tests** in `test_tier_routing_gate.py`; **525 tests pass** across visualization + module3_performance + lifecycle + AST-gate scope (up from 523 at v0.8.8).
- ruff: 0 violations.
- mypy: 0 issues on changed source files.
- AST gate (managed-enum comparison): 0 violations.
- Widget-mounting AST gate (W-073): 0 violations.
- Tier-routing CI gate (W-081): passes at baseline 43.

## Public framing

> v0.8.9 ships as **"all v0.9.0 plan items closed"**. The 25-item joint plan §3 (W-079 → W-102) is now fully resolved (v0.8.8 closed 17, v0.8.9 closes the remaining 7 + 1 follow-on). The dashboard has traversed every audit-driven maturation milestone: honest (v0.8.6), complete (v0.8.7), wet-lab-credible (v0.8.8), fully-mature-as-scoped (v0.8.9). The v0.9 maturity tag stays reserved for once the three durable v1.0 deferrals close.

## Remaining (durable v1.0 candidates)

Unchanged from prior releases. Three durable deferrals remain v1.0+ candidates:

- **Live AKTA UNICORN socket** (ADR-008 hardware deferral) — the `MonitorSource.unicorn_socket` UI slot is reserved.
- **MCMC inverse promotion** (ADR-010 dataset-bound) — importance-sampling stays the ceiling until datasets warrant the `pymc` cold-import cost.
- **Cyclic SMB / multi-bed dynamics** (ADR-009 §"Out of scope") — substantial physics scope.

Plus:

- **Full `tab_m3.py` split** (W-087 follow-on) — the proof-of-pattern is in place; extracting every cohesive section queues for v1.0.
- **Full unit standardisation pass** (W-096 follow-on) — the editor crib is in place; the codebase-wide sweep across every numeric input/output queues for v1.0.

## Cumulative v0.8.x patch cluster summary

| Tag | Theme | W-items closed |
|---|---|---|
| v0.8.4 | UI completeness against v0.8.3 backend | W-051 → W-063 (13) |
| v0.8.5 | M3 real-time back-pressure indicator | W-064 → W-068 (5) |
| v0.8.6 | Critical wiring fixes for v0.8.4 widgets | W-069 → W-073 (5) |
| v0.8.7 | Orphan backend exposure | W-074 → W-078 (5) |
| v0.8.8 | Maturation (operator affordances + tier discipline) | 17 of W-079..W-102 |
| **v0.8.9** | **All deferred W-items closed** | **7 of W-079..W-102** |

Total v0.8.x cluster: 50 W-items + 5 audit documents.
