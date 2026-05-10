# HANDOVER — v0.8.5 release close

**Date:** 2026-05-10
**Tag:** v0.8.5
**Work plan:** `docs/update_workplan_2026-05-10_v0_8_5.md`
**Driving artefact:** the joint /scientific-advisor + /architect + /dev-orchestrator plan delivered in the same workplan document (single-feature scope).

## Summary

v0.8.5 ships a single new affordance: a digital-style **real-time back-pressure indicator** pinned to the right of the M3 *Live phase view* column diagram. The indicator's colour is bound to the bed-compression ceiling (`dP_max_operational_pa` per ADR-004); a `?` popover surfaces the calculation summary and four ranked remediations starting with *lower Q to Q_recommended*. No backend changes — the existing `PressureEnvelope` dataclass already exposes every quantity the indicator needs.

**Five W-items shipped (W-064 → W-068); four new validation gates (38–41) closed.**

## Per-batch summary

### B-3a (W-064, W-065) — Pressure indicator component

- NEW `src/dpsim/visualization/components/pressure_indicator.py` (~230 LOC):
  - `_band(headroom_ratio: float) → "green" | "amber" | "red"` — pure boundary mapping at 0.70 / 1.00.
  - `_resolve_dp(envelope, current_dp_pa) → (dp_pa, source)` — picks live reading or falls back to `envelope.dP_predicted_pa`.
  - `_help_modal_md(envelope) → str` — composes the popover body: operational ceiling at active tier with the tier-aware interval bracket, the `u_crit · K_geom · G_DN · d_p² / (μ · L)` calculation summary, and the 4-rung remediation ladder.
  - `_digit_html(...)` / `_placeholder_html()` — DESIGN.md-compliant inline HTML (Geist Mono 700 / 28 px digit, tabular numerals, semantic colours `#10B981` / `#F59E0B` / `#EF4444`, 4 px border radius, no shadow / gradient / entrance animation).
  - `render_pressure_indicator(*, envelope, current_dp_pa, container, …)` — top-level entry point.
- `src/dpsim/visualization/components/__init__.py` exports `render_pressure_indicator`.

### B-3b (W-066) — M3 live-phase 2-column layout

- `src/dpsim/visualization/tabs/tab_m3.py:211-243` wraps the existing `render_column_xsec(...)` call in `st.columns([3, 1], gap="small")`; indicator renders in the right column.
- `tabs/tab_m3.py:786-792` (post-run pressure-envelope panel) caches the envelope into `st.session_state["m3_pressure_envelope"]` so the live-phase indicator (rendered upstream) picks it up on the next rerun.

### B-3c (W-067) — Live-reading session_state read-through

- `src/dpsim/visualization/tabs/tab_m3_monitor.py` writes `st.session_state["m3_latest_dp_pa"]` and `st.session_state["m3_latest_state"]` after each successful CSV replay. Defensive try/except so unit tests without a Streamlit runtime do not regress.

### B-3d (W-068) — Test suite

- NEW `tests/visualization/test_pressure_indicator.py` (24 tests):
  - **TestBand** — 8 parameterised boundary cases + DESIGN.md palette match.
  - **TestResolveDp** — live-vs-predicted routing.
  - **TestHelpModalMd** — operational ceiling, decision tier, formula, ranked remediations in reversibility order, tier-aware interval.
  - **TestDigitHtml** — colour mapping, Geist Mono / `tnum` compliance.
  - **TestPlaceholderHtml** — gate-41 labelling.
  - **TestRenderIntegration** — stub-container smoke (placeholder vs digit, popover wiring, live override, predicted source).

## Commit chain

```
(this release commit) — release: v0.8.5 — M3 real-time back-pressure indicator
(previous tag)        — release: v0.8.4 — UI completeness against the v0.8.3 backend (beacd0c)
```

## Verification

- **24 new tests**; **128/128 visualization tests pass** (104 prior + 24 new); broader test suite green where torch is not required (the optimization extra is unrelated to this release).
- ruff: 0 violations across all edited paths.
- mypy: 0 issues on `pressure_indicator.py`, `__init__.py`, `tab_m3.py`, `tab_m3_monitor.py`.
- AST gate (`tests/test_v9_3_enum_comparison_enforcement.py`): 0 violations.

## Validation gates closed (38–41)

| Gate | Description | Resolved by |
|---|---|---|
| 38 | Indicator renders to the right of the column diagram | B-3b |
| 39 | Value colour matches band (GREEN < 0.70, AMBER 0.70–1.00, RED ≥ 1.00) | B-3a / B-3d |
| 40 | `?` popover surfaces ceiling at tier + calculation + 4 ranked remediations | B-3a / B-3d |
| 41 | Clearly-labelled placeholder when envelope is absent | B-3a / B-3d |

## Public-communication framing

> v0.8.5 upgrades the **operator-facing situational awareness** during M3 column operation. Where v0.8.4 closed UI completeness for the *configuration* and *post-run analysis* surfaces, v0.8.5 adds a single live-cruise affordance: a digital number whose colour is bound to the bed-compression ceiling, with one-click access to the calculation and the remediation ladder. No backend changes; the v0.9 maturity plateau (live AKTA UNICORN socket, cyclic SMB, MCMC inverse) is unchanged from v0.8.4.

## Open future work — exclusively v0.9 candidates

Unchanged from v0.8.4:

- **AKTA UNICORN live socket backend** — implements the v0.8.2 `MonitorSource` Protocol per ADR-008. Hardware-bound.
- **Cyclic SMB / multi-bed dynamics** — ADR-009 deferral. Substantial physics scope.
- **MCMC inverse inference** — ADR-010 promotion target. Awaiting datasets that warrant the `pymc` cold-import cost.

Plus user-side:

- **Wet-lab calibration of K_geom / ν** — promotes outputs from SEMI_QUANTITATIVE to CALIBRATED_LOCAL via the v0.8.4 ingestion panel. User-driven; not a code deliverable.
