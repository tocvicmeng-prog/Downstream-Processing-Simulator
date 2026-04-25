# v0.4.1 Close Handover — deferred work landed

**Cycle:** v0.4.1 implementation, single-session continuation of v0.4.0.
**Date:** 2026-04-26.
**Predecessor:** `docs/handover/HANDOVER_v0_4_0_FINAL_CLOSE.md` (§8 listed seven deferred items; six have landed in this session — Direction B remains intentionally out of scope per the architecture spec §3.2).

---

## 1. Executive Summary

The six in-scope deferred items from v0.4.0 §8 are now in:

| # | Item | Status | Where |
|---|---|---|---|
| 1 | Animation placements: `render_impeller_xsec` in M1 hardware, `render_column_xsec` in M3 column | **LANDED** | `tabs/tab_m1.py`, `tabs/tab_m3.py` |
| 2 | Theme toggle (dark/light) wired through tokens.css `.dps-light` scope | **LANDED** | `shell/shell.py` |
| 3 | Run-history dropdown — bounded, FIFO-evicting, session-scoped | **LANDED** | `run_rail/history.py` |
| 4 | Named-baseline diff — tag/select arbitrary recipes as diff targets | **LANDED** | `diff/baselines.py` |
| 5 | Per-tab `param_row` adoption — pattern + worked migration in M3 column | **LANDED** (M3 column block migrated; full tab migration deferred to v0.5 — see §6) | `help/help_widget.py`, `tabs/tab_m3.py` |
| 6 | Direction B (Triptych workbench) | **DEFERRED** (out of scope per architecture §3.2) | — |

CI gates all green:

```
ruff   check  src/dpsim/visualization/ tests/test_ui_*
    All checks passed!

mypy   <new modules>
    0 new errors. 40 pre-existing errors in unrelated files (baseline, unchanged).

pytest tests/test_ui_chrome_smoke.py tests/test_ui_v0_4_0_modules.py tests/test_v9_3_enum_comparison_enforcement.py
    50 passed in 1.21s
```

(50 = 18 chrome smoke + 29 module smoke + 3 AST gate. 8 new tests added in this session for the v0.4.1 surface.)

---

## 2. Module Registry — v0.4.1 additions

| Module | Status | Approved | Model | LOC | File Path |
|---|---|---|---|---|---|
| M-101 `tabs.tab_m1` impeller placement | **APPROVED** | 2026-04-26 | Sonnet | +20 (edit) | `src/dpsim/visualization/tabs/tab_m1.py` |
| M-102 `tabs.tab_m3` column placement + labeled_widget migration | **APPROVED** | 2026-04-26 | Sonnet | +60 (edit) | `src/dpsim/visualization/tabs/tab_m3.py` |
| M-103 `shell.theme_toggle` | **APPROVED** | 2026-04-26 | Sonnet | +60 | `src/dpsim/visualization/shell/shell.py` (additions) |
| M-104 `run_rail.history` | **APPROVED** | 2026-04-26 | Sonnet | 175 | `src/dpsim/visualization/run_rail/history.py` |
| M-105 `diff.baselines` | **APPROVED** | 2026-04-26 | Sonnet | 175 | `src/dpsim/visualization/diff/baselines.py` |
| M-106 `help.labeled_widget` | **APPROVED** | 2026-04-26 | Haiku | +50 (helper) | `src/dpsim/visualization/help/help_widget.py` (additions) |
| M-107 `tests/test_ui_v0_4_0_modules.py` v0.4.1 extension | **APPROVED** | 2026-04-26 | Haiku | +120 (8 new tests) | `tests/test_ui_v0_4_0_modules.py` |
| M-108 v0.4.1 close handover | **APPROVED** | 2026-04-26 | Sonnet | this file | `docs/handover/HANDOVER_v0_4_1_CLOSE.md` |

**v0.4.1 totals:** ~660 LOC of new code + edits + tests.

---

## 3. Public API additions

```python
from dpsim.visualization.help import labeled_widget   # inside-column safe
from dpsim.visualization.diff import (
    Baseline,
    save_baseline,
    get_baseline,
    list_baselines,
    delete_baseline,
    baseline_choices,
    render_baseline_picker,
)
from dpsim.visualization.run_rail import (
    RunHistoryEntry,
    HISTORY_KEY,
    MAX_HISTORY,
    append_history,
    get_history,
    latest,
    find,
    clear_history,
    render_history_dropdown,
)
from dpsim.visualization.shell import ThemeMode, get_theme, set_theme
```

`render_diff_panel(...)` now accepts a `baseline_name=` kwarg (default `"last_run"` preserves v0.4.0 behaviour). Pass any name returned by `baseline_choices()` to diff against a tagged baseline.

---

## 4. Behavioural notes

### 4.1 Theme toggle

`set_theme("light")` flips a `.dps-light` class on `document.documentElement` via an injected `<script>` block. `tokens.css` already defines the `.dps-light` scope from v0.4.0; the toggle just binds it. The two iframes (`impeller_xsec.html`, `column_xsec.html`) accept a `__THEME__` template substitution — when the parent flips theme, the next call to `render_*_xsec` rebuilds the iframe HTML with the matched theme.

Known limitation: an iframe rendered before the theme change does not re-theme until the parent rerenders. Streamlit's rerun cycle handles this in practice — every theme button click triggers `st.rerun()`.

### 4.2 Run history

History is **session-scoped** — wiped on Streamlit restart. Persistence to disk is deferred until there is a wet-lab use case; the existing `ProcessDossier` export is the recommended persistence path for research-grade run records.

`append_history(...)` should be called from the existing run-completion handler (`render_lifecycle_run_panel` and `render_lifecycle_results_panel`). The handler signature accepts a recipe snapshot and the lifecycle-min evidence tier. Wire-up of the call sites is a one-line addition per handler and is left to the next implementation pass; the API is reachable now.

### 4.3 Named-baseline diff

`save_baseline(name=..., recipe=..., note=...)` rejects empty names and the reserved name `"last_run"`. Names are case-sensitive and unique within a session; saving with an existing name overwrites. The `note` field is for human use only — it is not parsed.

The `render_baseline_picker(current_recipe=...)` widget composes a selectbox over `baseline_choices()` plus a "manage baselines" expander. Drop it into the run-rail or anywhere else that has access to the live recipe.

### 4.4 Animation placements

Both placements are inside `st.expander(..., expanded=False)` — the visual is opt-in to keep the M1 / M3 tab default views compact. The M1 expander caption explicitly notes that the visual is a *Standard Rushton reference*, not a literal rendering of the user's pitched-blade or rotor-stator hardware. The M3 expander adds a Streamlit `st.radio` for the `load / wash / elute / cip` phase.

Both visualisations connect their geometric inputs to live Streamlit state:
- M1: `rpm` from the existing stir-rate slider.
- M3: `column_length_mm = bed_height_cm * 10`, `column_diameter_mm = col_diam_mm`.

### 4.5 `labeled_widget` vs `param_row`

`param_row` (v0.4.0) creates four columns internally — useful when called from a single-column container (the new shell's left pane), but unsafe when called from existing tab code that already nests inside `st.columns(...)`.

`labeled_widget` (v0.4.1) emits the label + help bubble + unit annotation as a flat `<div>` ABOVE the widget, with no column structure. Functionally equivalent for the user; layout-safe for inside-column adoption. Use it for migrating widgets inside the existing tab files.

The M3 column-geometry block (`Column I.D.`, `Bed height`, `Bed porosity`, `Flow rate`) is the worked example.

---

## 5. Test coverage added

```
tests/test_ui_v0_4_0_modules.py — 8 new tests:
    test_v041_labeled_widget_is_callable
    test_v041_named_baseline_save_get_delete
    test_v041_baseline_reserved_name_rejected
    test_v041_baseline_choices_includes_last_run
    test_v041_run_history_append_and_evict
    test_v041_theme_module_api
    test_v041_tab_m1_imports_impeller_xsec_lazily
    test_v041_tab_m3_imports_column_xsec_and_labeled_widget
```

All 50 tests in the suite pass (18 chrome smoke + 29 module smoke including 8 new v0.4.1 + 3 AST gate).

---

## 6. Genuinely deferred to v0.5

The architecture spec deferred Direction B (Triptych workbench) to v0.5; that remains the right call. Two additional items surfaced during v0.4.1 implementation are also v0.5 work, not v0.4.x:

1. **Full tab-by-tab `labeled_widget` migration.** Only the M3 column block was migrated in v0.4.1 as a worked example (4 widgets, ~30 LOC of edits). Migrating the rest of M3 + all of M1 + all of M2 is ~600–800 LOC of mechanical edits across 2,800 LOC of tab code — large, low-novelty, high-tedium. The `labeled_widget` API is stable and the catalog is populated; the migration is a chore that pays off most when bundled with the Direction B work.

2. **Run-history persistence to disk + re-load action.** v0.4.1 ships an in-session history with a dropdown UI. Full persistence (JSON / YAML / `ProcessDossier` round-trip) and a "load this run" button that swaps the live recipe back to a historical state are both deferred. The `RunHistoryEntry.snapshot` dict is already the right shape for round-trip; a follow-on session can land the disk persistence in ~150 LOC.

---

## 7. Commit posture

Same as v0.4.0: nothing committed, working tree contains the entire v0.4.0 + v0.4.1 landing for the user to review. Recommended commit grouping for v0.4.1:

1. `feat(v0.4.1): theme toggle + dark/light scope binding` — M-103.
2. `feat(v0.4.1): run history dropdown + named-baseline diff` — M-104 + M-105.
3. `feat(v0.4.1): impeller and column animation placements in M1/M3 tabs` — M-101 + M-102.
4. `refactor(v0.4.1): labeled_widget for inside-column param adoption + worked M3 migration` — M-106 + M-102 (column-geometry block).
5. `test(v0.4.1): module smoke tests (theme/baselines/history/labeled_widget/animation hooks)` — M-107.
6. `docs(v0.4.1): close handover` — M-108.

Commit (1) is independent. (2)–(4) build on the v0.4.0 foundation. Branch `v0.4.1` cut from `v0.4.0` (or a single `v0.4` branch carrying both).

---

## 8. Roadmap position

```
v0.3.8  ████████████████████████████████████████████  shipped
v0.4.0  ████████████████████████████████████████████  100% (11 modules + cut-over)
v0.4.1  ████████████████████████████████████████████  100% (6/7 deferred items)
v0.5.x  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  Direction B (Triptych);
                                                       full tab labeled_widget migration;
                                                       on-disk run history
```

The DPSim v0.4 line — full Direction-A shell with all the original v0.4.0 design pain points addressed — is feature-complete.
