# HANDOVER — B-1k plotly annotation tier-gating (v0.8.1)

**Batch:** B-1k
**Work item:** W-035 (LOW priority, pure UX)
**Source delta:** 2026-05-04 incremental-close handover §"Future scientific scope" item 3
**Date:** 2026-05-10

## Summary

Closes the long-deferred "B-1b plot annotations" item. Decision-grade
gating — which previously only affected `st.metric` widgets via
`render_metric` — now also gates the text content of plotly chart
annotations. Vertical / horizontal threshold lines remain tier-blind
(they're the chart geometry, not the claim).

## Files added/modified

| File | Change |
|---|---|
| `src/dpsim/visualization/decision_grade_render.py` | New `render_decision_grade_annotation` helper. Routes `value` through `format_decision_graded`, picks an unobtrusive color hint based on render mode, appends `[INTERVAL]` / `[RANK]` mode tag suffix (toggleable via `show_mode_tag`). Returns the chosen `RenderMode` so callers can branch on `SUPPRESS` to draw a "data not available" badge instead. |
| `src/dpsim/visualization/plots_m3.py` | `plot_breakthrough_curve` gains optional `tier` kwarg; when set, the three DBC value annotations route through the new helper. `plot_pressure_flow_curve` gains the same kwarg for the Q_max badge. `tier=None` preserves legacy formatting bit-for-bit so existing callers aren't disturbed. |
| `tests/visualization/test_render_decision_grade_annotation.py` | NEW. 13 tests covering all four render modes, color override path, extra-kwargs forwarding, and the wire-up in both plot functions. |

## Acceptance — DBC at typical M3 evidence tiers

| Tier | DBC mode | Annotation text shape |
|---|---|---|
| `VALIDATED_QUANTITATIVE` | NUMBER | `DBC₁₀=42.3 mol/m³` |
| `CALIBRATED_LOCAL` | INTERVAL | `DBC₁₀=30–55 mol/m³ [INTERVAL]` |
| `SEMI_QUANTITATIVE` | RANK_BAND | `DBC₁₀=HIGH [RANK]` |
| `QUALITATIVE_TREND` | SUPPRESS | (no text drawn — the helper returns SUPPRESS without calling `add_annotation`) |

`Q_MAX` floor is one tier lower (SEMI_QUANTITATIVE) so the same tiers
shift up by one in the Q_max badge.

## Out of scope (deferred)

- **M1 / M2 plot tier-gating.** Only M3 plots wired. Symmetric extension
  to `plots_m2.py` and the M1 PBE plots is incremental v0.8.2 work — no
  blocker.
- **Suppression badges.** When the policy returns `SUPPRESS`, the plot
  drops the annotation silently. A more user-explicit path would draw
  a faint "data not yet available" badge in the same anchor position.
  Deferred — single-line caller pattern is cleaner.
- **Animation-aware tier transitions.** When a tier changes mid-run
  (recipe step transition), the plot annotation does not animate.
  Deferred to v0.9 with the live AKTA bridge.

## Notes for future maintainers

The `_MODE_TAG` and `_MODE_COLOR_HINT` mappings in
`decision_grade_render.py` are the single source of truth for how
plotly annotations express render modes. Adding a new mode (unlikely
but possible) requires extending both maps. The `show_mode_tag=False`
escape hatch is intentional — some chart layouts can't accommodate the
text suffix without truncation, and callers in those layouts should
suppress the tag and rely on the color hint alone.
