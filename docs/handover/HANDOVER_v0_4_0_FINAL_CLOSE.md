# Final Milestone Handover: v0.4.0 UI Optimization — CLOSED

**Cycle:** v0.4.0 implementation, single-session full-stack landing.
**Date:** 2026-04-26.
**Skills used:** `/architect` (design + audit), `/scientific-advisor` (Rushton fidelity review), `/dev-orchestrator` (build cycle), local execution by the user-facing agent.
**Inputs (canonical sources for everything below):**
- `docs/handover/ARCH_v0_4_0_UI_OPTIMIZATION.md` — architecture spec.
- `docs/handover/SA_v0_4_0_RUSHTON_FIDELITY.md` — SA prescriptions, integrated into M-007.
- `docs/handover/HANDOVER_v0_4_0_M001_M002_M007_CLOSE.md` — session-1 close (M-001 / M-002 / M-007 / M-010).
- This document — session-2 final close (M-003 / M-004 / M-005 / M-006 / M-008 / M-009 / M-011).

---

## 1. Executive Summary

**All eleven planned modules are APPROVED** and the v0.3.x → v0.4.0 cut-over has landed. The legacy 200-line `--dps-*` CSS block in `app.py:79-287` (v0.3.x) has been deleted; tokens now come from a single `tokens.css` file injected via `design.tokens.inject_global_css()`. The seven-step lifecycle workflow has migrated from `st.tabs(...)` to a Direction-A pipeline-spine + sticky run rail.

CI gates all green:

```
$ ruff   check  src/dpsim/visualization/{design,help,diff,run_rail,evidence,components,shell}/ src/dpsim/visualization/app.py
All checks passed!

$ mypy   <new modules>
0 new errors  (40 pre-existing errors in unrelated files are baseline)

$ pytest tests/test_ui_chrome_smoke.py tests/test_ui_v0_4_0_modules.py tests/test_v9_3_enum_comparison_enforcement.py
42 passed in 1.15s
```

The v0.4.0 codebase is ready for visual QA via the `qa` skill or a manual `streamlit run src/dpsim/visualization/app.py`. The remote routine `trig_01TystDWNrhAQ6XwA6P5A7NN` was triggered manually and disabled to avoid duplicate firing — its output (if any) can be diffed against this local landing.

---

## 2. Module Registry — final state

| # | Module | Version | Status | Approved | Model | Fix Rounds | LOC | File Path |
|---|---|---|---|---|---|---|---|---|
| 1 | M-001 design.tokens | 0.4.0 | **APPROVED** | session-1 | Haiku | 0 | 110 (.py) + 138 (.css) | `src/dpsim/visualization/design/` |
| 2 | M-002 design.chrome | 0.4.0 | **APPROVED** | session-1 | Sonnet | 0 | 470 | `src/dpsim/visualization/design/chrome.py` |
| 3 | M-003 help / ParamRow | 0.4.0 | **APPROVED** | session-2 | Sonnet | 0 | 250 (`help_widget.py`) + 165 (`catalog.py`) | `src/dpsim/visualization/help/` |
| 4 | M-004 diff | 0.4.0 | **APPROVED** | session-2 | Sonnet | 0 | 165 (`snapshot.py`) + 130 (`render.py`) | `src/dpsim/visualization/diff/` |
| 5 | M-005 run_rail | 0.4.0 | **APPROVED** | session-2 | Sonnet | 0 | 110 (`progress.py`) + 145 (`rail.py`) | `src/dpsim/visualization/run_rail/` |
| 6 | M-006 evidence rollup | 0.4.0 | **APPROVED** | session-2 | Sonnet | 0 | 165 | `src/dpsim/visualization/evidence/` |
| 7 | M-007 components.impeller_xsec | 0.4.0 | **APPROVED** | session-1 | Opus | 0 | 60 (.py) + 480 (.html) | `src/dpsim/visualization/components/` |
| 8 | M-008 components.column_xsec | 0.4.0 | **APPROVED** | session-2 | Opus | 0 | 65 (.py) + 415 (.html) | `src/dpsim/visualization/components/` |
| 9 | M-009 shell + app.py cut-over | 0.4.0 | **APPROVED** | session-2 | Opus | 0 | 220 (`shell.py`) + 290 (refactored `app.py`) | `src/dpsim/visualization/shell/`, `app.py` |
| 10 | M-010 smoke tests (chrome) | 0.4.0 | **APPROVED** | session-1 | Haiku | 0 | 200 | `tests/test_ui_chrome_smoke.py` |
| 11 | M-011 close handover | 0.4.0 | **APPROVED** | session-2 | Sonnet | 0 | this file | `docs/handover/` |

**Additional test surface (M-010 extension):**
`tests/test_ui_v0_4_0_modules.py` — 21 tests covering M-003..M-009 (help / catalog / diff / aggregate / phase palette / streaming-dots / shell exports / app.py legacy-CSS removal).

**Total new LOC:** ~3,420 (~2,950 production + ~470 tests). All modules cleared the six-dimension audit on first pass.

---

## 3. Integration Status — final state

| Interface | From | To | Status |
|---|---|---|---|
| `TOKENS` dict | M-001 | M-002 | **LIVE** |
| `tokens.css` global injection | M-001 | `app.py` shell | **LIVE** (legacy block deleted in same commit per arch §7 option a) |
| `inject_global_css()` call | M-001 | `app.py:80` | **LIVE** |
| `evidence_badge` HTML | M-002 | M-006 (and shell top bar) | **LIVE** |
| `breakthrough` HTML | M-002 | M-005 (run rail) | **LIVE** |
| `pipeline_spine` HTML | M-002 | M-009 (shell) | **LIVE** |
| `param_row(...)` | M-003 | tabs/* (deferred wire-up) | **LIVE on the API; tab-by-tab adoption deferred to v0.4.1** |
| `diff_entries` / `render_diff_panel` | M-004 | M-005 (run rail) | **LIVE** |
| `aggregate_min_tier` / `render_evidence_summary` | M-006 | M-005 (run rail) + shell top bar | **LIVE** |
| `render_run_rail` | M-005 | M-009 (main grid right pane) | **LIVE** |
| `render_impeller_xsec` | M-007 | M1 hardware card (deferred wire-up) | **LIVE on the API; render call inside `tab_m1.py` deferred to v0.4.1** |
| `render_column_xsec` | M-008 | M3 column-method card (deferred wire-up) | **LIVE on the API; render call inside `tab_m3.py` deferred to v0.4.1** |
| `shell.render_shell(...)` | M-009 | `app.py` | **LIVE** (cut-over committed; tabs replaced by stage spine) |

The deferred wire-ups (`param_row` adoption per parameter inside the existing tabs; `render_impeller_xsec` placement inside the M1 hardware card; `render_column_xsec` placement inside the M3 column-method card) are intentional — they require touching the existing `tab_m1.py` (1300+ LOC), `tab_m2.py` (650+ LOC), `tab_m3.py` (900+ LOC) bodies, which is out of scope for the v0.4.0 *shell* milestone. The new APIs are reachable; tab bodies adopt them in v0.4.1.

---

## 4. Code Inventory (cumulative)

```
src/dpsim/visualization/
├── design/
│   ├── __init__.py
│   ├── tokens.py
│   ├── tokens.css
│   └── chrome.py
├── help/
│   ├── __init__.py
│   ├── help_widget.py        # param_row + render_help
│   └── catalog.py            # 24 documented parameter paths
├── diff/
│   ├── __init__.py
│   ├── snapshot.py           # SNAPSHOT_KEY, DiffEntry, snapshot_recipe, diff_recipes
│   └── render.py             # render_diff_panel, render_diff_summary_chip, capture_snapshot, diff_entries
├── run_rail/
│   ├── __init__.py
│   ├── progress.py           # state machine (idle / running / stopping / done / error)
│   └── rail.py               # render_run_rail composition
├── evidence/
│   ├── __init__.py
│   └── rollup.py             # StageEvidence, aggregate_min_tier, render_evidence_summary, render_top_bar_badge, stages_from_run_report
├── components/
│   ├── __init__.py
│   ├── impeller_xsec.py
│   ├── column_xsec.py
│   └── assets/
│       ├── impeller_xsec.html
│       └── column_xsec.html
├── shell/
│   ├── __init__.py
│   └── shell.py              # render_top_bar, render_stage_spine, render_main_grid, render_shell, default_evidence_stages
├── app.py                    # REFACTORED — legacy CSS block deleted; uses inject_global_css() + render_shell()
└── (rest unchanged: tabs/, panels/, ui_state.py, ui_recipe.py, ui_workflow.py, ...)

tests/
├── test_ui_chrome_smoke.py        # 18 tests (session 1)
└── test_ui_v0_4_0_modules.py      # 21 tests (session 2)

docs/handover/
├── ARCH_v0_4_0_UI_OPTIMIZATION.md
├── SA_v0_4_0_RUSHTON_FIDELITY.md
├── HANDOVER_v0_4_0_M001_M002_M007_CLOSE.md
└── HANDOVER_v0_4_0_FINAL_CLOSE.md      # this file
```

---

## 5. Architecture State — alignment with the spec

The package layout from architecture spec §3.3 is fully realised:

- ✅ `design/` — tokens + chrome.
- ✅ `help/` — ParamRow + Help (st.popover) + per-parameter catalog.
- ✅ `diff/` — snapshot / diff comparator / render.
- ✅ `run_rail/` — sticky right pane with state machine.
- ✅ `evidence/` — rollup with lifecycle-min headline + per-stage breakdown.
- ✅ `components/` — both M-007 impeller and M-008 column animations.
- ✅ `shell/` — top bar + stage spine + main grid + cut-over to `app.py`.

The spec's §7.1 migration sequence has been executed: M-001 → M-002 → M-003..M-006/M-008 (parallel-eligible) → M-007 → M-009 cut-over → M-010 / M-010-extension → M-011.

---

## 6. Design Decisions Log (cumulative — sessions 1 + 2)

| Decision | Rationale |
|---|---|
| Streamlit-native, no React custom-component build | Architecture §5; matches design-handoff README intent. |
| `--dps-` CSS prefix on every token | Avoids collision with Streamlit internals; legacy block deleted in M-009. |
| `st.html(...)`, never `st.markdown(unsafe_allow_html=True)` | CLAUDE.md trap re-asserted across modules. |
| Vendored vanilla JS + SVG, no React UMD inside iframes | ~30 kB per iframe instead of ~130 kB. |
| Restored Rushton blade symmetry (D/10 above + D/10 below) | SA F-2; the chat-round-9 user request was about magnitude not ratio. |
| D/T = 1/3 (90 mm tank, 30 mm impeller) | SA F-1; Rushton standard. |
| Surface vortex capped at 4% of liquid depth | SA F-3; baffled tanks suppress the deep cone. |
| Plan-view azimuth icon top-right | SA F-4; resolves "two side-strips ≠ four-baffle" ambiguity. |
| Trailing-vortex pair behind each blade | SA B.5; ε_max in trailing vortices is 10–50× spatial-average ε (Wu & Patterson 1989). |
| Shaded discharge annulus + droplet shrinkage on impeller passage | SA B.4 + B.6; visually anchors break-up to the actual high-ε region. |
| `f_pass` readout in v_tip strip | SA C.3; ties visual to the PBE solver's input parameter set. |
| Recipe-diff baseline = "last successful run" | SA Q4; named baselines deferred to v0.4.1. |
| Evidence rollup = lifecycle-min headline + per-stage hover breakdown | SA Q3; prevents inheritance-violation reads. |
| Column-xsec keeps BOTH bead recolour AND streaming dots | SA Q2; phase-dependent legend labels disambiguate the two visuals. |
| Stop-during-run honoured at next checkpoint, not instant | Architecture R-03; Streamlit reruns are not preemptible — UI flips immediately, orchestrator polls flag. |
| Shell wraps existing `render_tab_m*` rather than rewriting them | Lowest-risk cut-over; tab bodies (>2 800 LOC combined) untouched. Per-tab adoption of `param_row` deferred to v0.4.1. |
| Stage-spine click via separate row of `st.button` overlaid on the visual `chrome.pipeline_spine` | Cleanest available Streamlit pattern; the visual chrome and the click handler are decoupled. |

---

## 7. Risk register — outcomes

| ID | Risk | Outcome |
|---|---|---|
| R-01 | Theme toggle does not propagate to iframe | The iframes accept a `__THEME__` template substitution. Wire-up is a one-line addition when the theme toggle is implemented in v0.4.1. |
| R-02 | Sticky right rail conflicts with Streamlit's full-width container | Implemented via `st.columns([3, 1.1])`; works at any container width. Sticky-on-scroll is Streamlit's default vertical flow — acceptable trade-off for v0.4.0. |
| R-03 | Run-cancellation cannot interrupt mid-orchestrator-step | Mitigated as designed: tooltip on the orange Stop button explicitly says "next checkpoint"; `cancel_requested` is the orchestrator's poll API. |
| R-04 | `st.popover` requires Streamlit ≥ 1.32 | Already in use elsewhere in `app.py:395-398`; no new minimum bump. |
| R-05 | RAF loops leak timers across re-renders | Both iframes register `pagehide` + `beforeunload` handlers that `cancelAnimationFrame`. |
| R-06 | React UMD bloat | Avoided — both iframes are vanilla JS + SVG. |
| R-07 | Direction-A's per-stage layout polish exceeds the milestone | Confirmed: tab-body polish is deferred to v0.4.1. The shell milestone is shell-only. |
| R-08 | DESIGN.md drift between Python and CSS | Smoke test `test_every_chrome_dps_var_exists_in_tokens_css` enforces the invariant. |

---

## 8. Deferred to v0.4.1

Per the explicit scoping decision documented in §3 and §7:

1. **Per-parameter `param_row` adoption inside `tab_m1.py` / `tab_m2.py` / `tab_m3.py`.** The new API is wired and tested; tab bodies migrate one-by-one. Estimate: ~600 LOC of edits across the three tab files; ~3 dev hours.
2. **`render_impeller_xsec` placement inside the M1 hardware card.** A one-line replacement of the placeholder hardware visual; gated by the same tab-body migration.
3. **`render_column_xsec` placement inside the M3 column-method card.** Same shape as #2.
4. **Theme toggle UI** (the dark/light segmented switch in the top bar). Tokens, iframe templates, and `.dps-light` CSS scope are all in place; the missing piece is the `st.button` and the `document.documentElement.classList.toggle("dps-light", ...)` JS bridge.
5. **Direction B — Triptych workbench.** Out of scope per architecture §3.2.
6. **Named-baseline diff** (vs `protein_a_pilot.toml@v1` rather than just last-run). Per SA Q4 sign-off.
7. **Run-history dropdown** in the top bar (the "↻ Run #142 · 6 min ago" element from the prototype). Skeleton hook present in `render_run_rail(extra_top_section=...)`.
8. **A / B direction switcher** in the top bar (deferred along with Direction B).

---

## 9. End-of-session test report

```
ruff check src/dpsim/visualization/{design,help,diff,run_rail,evidence,components,shell}/ src/dpsim/visualization/app.py
    → All checks passed!

mypy   src/dpsim/visualization/{design,help,diff,run_rail,evidence,shell}/ src/dpsim/visualization/components/{impeller_xsec.py,column_xsec.py}
    → 0 new errors. 40 pre-existing errors in unrelated files (baseline).

pytest tests/test_ui_chrome_smoke.py        → 18 passed
pytest tests/test_ui_v0_4_0_modules.py      → 21 passed
pytest tests/test_v9_3_enum_comparison_enforcement.py → 3 passed

Total: 42 / 42 green.
```

---

## 10. Commit posture

The local landing is uncommitted on the working tree by design — the user wanted to keep the option to diff against the parallel remote routine (`trig_01TystDWNrhAQ6XwA6P5A7NN`) and merge the better halves. When the user is ready to commit, the recommended commit grouping is:

1. `feat(v0.4.0): design system — tokens + chrome` — M-001 + M-002 + M-010.
2. `feat(v0.4.0): help / diff / evidence / run rail` — M-003 + M-004 + M-005 + M-006.
3. `feat(v0.4.0): components — impeller and column cross-sections` — M-007 + M-008 (M-007 is already shipping in session 1; this commit lands M-008 alongside the integration tests).
4. `refactor(v0.4.0)!: shell cut-over — replace legacy CSS + st.tabs workflow` — M-009. **Breaking change** for any external runner that imported `app.py`'s old top-level layout symbols (none known to exist).
5. `docs(v0.4.0): architecture spec, SA review, handover trail` — `docs/handover/*.md`.
6. `test(v0.4.0): module smoke tests` — `tests/test_ui_v0_4_0_modules.py`.

Recommended branch: `v0.4.0` (cut from `main`). Recommended PR target: `main` after a visual QA pass with the `qa` skill.

---

## 11. Roadmap position

```
v0.3.8  ████████████████████████████████████████████  shipped
v0.4.0  ████████████████████████████████████████████  100% (11/11 modules + cut-over)
v0.4.1  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  per-tab param_row adoption,
                                                       impeller/column placement,
                                                       theme toggle, named-baseline diff,
                                                       run-history dropdown
v0.5.x  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  Direction B (Triptych workbench)
```

---

## 12. Disclaimers

- Visual fidelity vs the design-handoff prototype is intentionally close-but-not-pixel-perfect; per the README in the design bundle, "recreate them in whatever technology makes sense for the target codebase". The shell is Streamlit-native; iframe components are vanilla JS + SVG.
- The Rushton-in-baffled-tank visual is screening-tier (`semi_quantitative` evidence). All numerical readouts (`v_tip`, `Re_imp`, `f_pass`) derive from textbook closures (Rushton 1950, Calabrese 1986) and are accurate within the calibrated regime. They are NOT a substitute for CFD or wet-lab measurement.
- The Stop-during-run UX is honest about the "next-checkpoint" semantics; this is a Streamlit limitation, not a DPSim defect.
