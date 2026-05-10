# HANDOVER — v0.8.6 release close

**Date:** 2026-05-10
**Tag:** v0.8.6
**Work plan:** `docs/update_workplan_2026-05-10_v0_9_0.md` §1
**Driving audits:** `docs/handover/AUDIT_v0_8_5_e2e_phase{1,2,3}_*.md`

## Summary

v0.8.6 closes the four CRITICAL wiring breaks identified by the v0.8.5 end-to-end audit. The v0.8.4 release shipped three widgets — mobile-phase composition editor, isotherm selector, SEMI_QUANTITATIVE tier banner — that were defined and unit-tested but **never mounted** in production code. v0.8.4's CHANGELOG entries for defects C1, C2, and W-1 were therefore *theatrically* closed: tests passed, but a user pressing *Run* received simulations in which their actual reagents were silently substituted by water-at-20 °C + bare Langmuir defaults.

v0.8.6 turns the v0.8.4 closure into an *operationally true* closure: five W-items shipped (W-069 → W-073), four new validation gates (42–47) closed, and a new AST gate (W-073) prevents the wiring-break pattern from recurring.

## Per-batch summary

### B-4a (W-069) — Mount `render_mobile_phase_widget`

* `tabs/tab_m3.py:291-339` — new Method-conditions section (border container) hosting both the mobile-phase widget and the isotherm widget.
* User-supplied `MobilePhase` persists to `st.session_state["m3_mobile_phase"]`.

### B-4b (W-070) — Mount `render_isotherm_widget`

* Same Method-conditions container as B-4a.
* Polymer-family resolution: walks `m2_result.polymer_family` then `m2_result.m1_contract.polymer_family`; falls back to `AGAROSE` before M2 has run.
* User-supplied `IsothermSpec` persists to `st.session_state["m3_isotherm_spec"]`.

### B-4c (W-071) — Mount `render_tier_banner`

* `app.py` — the banner renders before `render_shell` / `render_top_bar` dispatch, so it appears at the top of every stage (Direction A and Direction B).
* Worst-tier resolution: walks `lifecycle_result.{m1,m2,m3}_result.model_manifest.evidence_tier` and picks the worst per the `_TIER_RANK` ladder.
* `has_calibration` reads `st.session_state["_cal_store"]`.
* Defensive `try/except` so a missing attribute on the lifecycle result never breaks the page.

### B-4d KEYSTONE (W-072) — Thread user inputs end-to-end

* New `panels/isotherm_selector.py::to_isotherm(spec) -> Any` converter covering all 5 IsothermChoice members:
  * `LANGMUIR` → `LangmuirIsotherm(q_max, K_L)`
  * `SALT_MODULATED_LANGMUIR` → `SaltModulatedLangmuir(base, nu, c_salt_ref_mol_m3)`
  * `IMIDAZOLE_MODULATED_LANGMUIR` → `ImidazoleModulatedLangmuir(base, n, c_imidazole_ref_mol_m3)`
  * `SALT_MODULATED_SMA` → `SaltModulatedSMA(z, sigma, K_eq, Lambda, c_salt_ref_mol_m3)`
  * `SALT_MODULATED_COMPETITIVE_LANGMUIR` → `SaltModulatedCompetitiveLangmuir(base, nu_array, c_salt_ref_mol_m3)`
* `lifecycle/orchestrator.py::DownstreamProcessOrchestrator.run()` gains `isotherm: Any | None = None`. When supplied:
  * The fallback `run_breakthrough` at `orchestrator.py:933` passes `isotherm=` through.
  * After the primary path's `m3_method.load_breakthrough` resolves, the lifecycle re-runs breakthrough with the user's isotherm so the user's choice always wins.
  * A `WARNING`-tier `M3_USER_ISOTHERM_OVERRIDE` validation entry is recorded so the override is auditable.
* `ui_workflow.render_lifecycle_run_panel` reads both session_state keys, converts the spec to a backend isotherm, and passes `mobile_phase=` + `isotherm=` to the orchestrator's threaded run. Defensive `try/except` so a malformed spec never blocks the run.
* `tabs/tab_m3.py:1054` — in-page pre-flight envelope now reads `m3_mobile_phase` from session_state instead of `MobilePhase()` defaults.

### B-4e (W-073) — Widget-mounting AST gate

* New `tests/visualization/test_widget_mounting.py` (3 tests):
  * `test_collected_render_defs_is_nonempty` — sanity that the scanner finds widgets.
  * `test_every_render_def_has_a_production_caller` — the gate; iterates every `def render_*` in `panels/` + `shell/`, asserts ≥ 1 caller in `tabs/` + `app.py` + `shell/` (excluding `__init__.py` re-exports).
  * `test_pragma_no_mount_skips_widget` — verifies the `# pragma: no-mount` escape hatch.
* Caught one true orphan: `panels/calibration.py::render_calibration_panel` (v6.0-rc legacy JSON uploader, superseded by v0.8.4 W-057's wet-lab YAML ingestion). Documented with `# pragma: no-mount` and a deprecation note.

## Commit chain

```
(this release commit) — release: v0.8.6 — wiring fixes for v0.8.4 widgets
ba2ac56 (v0.8.5)        — release: v0.8.5 — M3 real-time back-pressure indicator
beacd0c (v0.8.4)        — release: v0.8.4 — UI completeness against the v0.8.3 backend
```

## Verification

* **3 new tests** in `tests/visualization/test_widget_mounting.py`; **134/134 visualization tests pass** (131 prior + 3 new).
* **518 tests pass** across the visualization + module3_performance + lifecycle + AST-gate scope (up from 515 at v0.8.5).
* ruff: 0 violations.
* mypy: 0 issues across the 5 changed paths.
* AST gate: 0 violations on the existing managed enums.
* `to_isotherm` smoke-tested end-to-end against all 5 IsothermChoice members.

## Validation gates closed (42 → 47)

| Gate | Description | Resolved by |
|---|---|---|
| 42 | Mobile-phase widget renders in M3 input | B-4a |
| 43 | Isotherm widget renders in M3 input | B-4b |
| 44 | Tier banner renders at app top-of-page | B-4c |
| 45 | User mobile phase changes pre-flight envelope | B-4d (tab_m3.py:1054) |
| 46 | User isotherm class changes breakthrough curve | B-4d (orchestrator override + to_isotherm) |
| 47 | AST gate prevents widget-mounting regressions | B-4e |

## Public-communication framing

> v0.8.6 ships as **"the dashboard becomes honest"**. The v0.8.4 CHANGELOG's claims for defects C1, C2, and W-1 were not structurally accurate at v0.8.5; v0.8.6 makes them so. A user picking SaltModulatedSMA + 1 M NaCl + 10 % glycerol in the M3 tab now sees those choices flow into the breakthrough curve, the pressure envelope, and the post-run validation. The v0.9 maturity plateau (live AKTA UNICORN, cyclic SMB, MCMC inverse) is unchanged.

## Open future work — v0.8.7 + v0.9.0 candidates

Per `docs/update_workplan_2026-05-10_v0_9_0.md`:

* **v0.8.7** — Orphan backend exposure (W-074 → W-078): detector traces UI, OptimizationEngine top-level tab, MonitorSource Protocol UI dropdown, multi-step coupled MC, HIC + ProteinA isotherms in the selector.
* **v0.9.0** — Maturation milestone (W-079 → W-102): decision-grade consistency, pre-flight envelope relocation to pre-Run, M2 → M3 chain confirmation, inverse-Bayesian input-time blocker, spreadsheet calibration import, save/load sessions, SOP PDF export, run-vs-run comparison, unit standardisation, first-run example loader, predicted-vs-measured ΔP overlay.
