# HANDOVER — B-2i streaming UI close (v0.8.0)

**Batch:** B-2i
**Work item:** W-032 (HIGH)
**Source delta:** v0.7.0 plan §6 streaming-UI epic
**Date:** 2026-05-10

## Summary

Operationalizes `evaluate_pressure_trace` (v0.7 / B-3d) for end-users
via two new modules: a CSV-replay helper and a Streamlit UI section.
The live AKTA UNICORN bridge is still a v0.9 epic — v0.8 ships the
offline-replay path, sufficient for training and after-action review.

## Files changed

| File | Change |
|---|---|
| `src/dpsim/module3_performance/pressure_monitor_replay.py` | NEW. `parse_csv` (canonical SI columns + AKTA-style aliases for t/dP/Q with unit-aware scaling). `replay` (threads history through `evaluate_pressure_trace`, accumulates state-timeline + diagnostic maxima). `ReplaySummary` frozen dataclass. |
| `src/dpsim/visualization/tabs/tab_m3_monitor.py` | NEW. `render_pressure_monitor_section` — file uploader, summary metric row (n readings, final state, first BLOCKER, max headroom, max dΔP/dt), ΔP-vs-time plot with operational + 70 % warning lines and per-reading state chips, downloadable example CSV. |
| `src/dpsim/visualization/tabs/tab_m3.py` | Wire-in: invokes `render_pressure_monitor_section` after the pre-flight envelope panel. |
| `tests/module3_performance/test_pressure_monitor_replay.py` | NEW — 22 tests covering parse alias / scaling / skip rules + replay timeline / blocker anchors / max ratios / immutability. |
| `tests/visualization/test_tab_m3_monitor.py` | NEW — 6 UI smoke tests using a stub Streamlit container (no live runtime needed). |

## Acceptance

- CSV alias resolution covers t_s / t_min, dP_pa / dP_kpa / dP_mpa / dP_bar / pressure_*, Q_m3_s / Q_mL_min.
- Skip rules: unparseable rows + negative ΔP rows.
- Sort-by-ascending-time invariant.
- Empty CSV / missing required column / no parseable rows raise clear `ValueError`.
- `ReplaySummary` populates `state_timeline` with one entry per reading.
- 28/28 new tests pass; ruff + mypy clean.

## Out of scope (deferred)

- Live AKTA UNICORN WebSocket bridge — v0.9.
- Real-time waveform animation — v0.9.
- Multi-step replay across recipe transitions — v0.9 (currently the UI replays one envelope at a time).
