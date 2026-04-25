# Architecture Specification: DPSim UI Optimization v0.4.0

**Architect role · dev-orchestrator framework**
**Status:** PROPOSED — pending /scientific-advisor scientific review and /dev-orchestrator implementation cycle
**Source bundle:** Claude Design handoff `gyCyXL_Ak0cwMRB0KBAwFA` → `.dpsim_tmp/design_handoff/`
**Date:** 2026-04-26

---

## 1. Overview

### 1.1 Problem statement

The current DPSim Streamlit UI (`src/dpsim/visualization/app.py` + `tabs/`) ships the v0.3.8 design-system CSS injection but retains the default Streamlit information architecture: a sidebar of Global Settings, a single tabset for M1 / M2 / M3, and seven loosely-coupled `render_lifecycle_*` panels. The Claude Design handoff identifies five concrete pain points the current shell does not address:

1. **Workflow legibility** — the 7-stage lifecycle is not visible at a glance.
2. **M1 → M2 → M3 coupling** — stages are siloed; upstream / downstream dependencies are invisible.
3. **Visual polish** — the page still reads as default Streamlit despite the CSS layer.
4. **Density** — too much vertical scrolling; you cannot see the whole lifecycle.
5. **Noisy inputs** — every parameter is visible at once with no progressive disclosure.

Plus three new affordances the user requested:

- Live **recipe diff** vs last run.
- Inline **"what does this do?"** help on every parameter.
- Sticky **breakthrough preview** rail (P05 / P50 / P95 envelope always on screen).

### 1.2 Inputs / outputs

- **Inputs:** the design handoff (`tokens.css`, `components.jsx`, `direction-a.jsx`, `direction-b.jsx`, screenshots, chat transcript), `DESIGN.md`, `CLAUDE.md`, the existing Streamlit shell + tabs.
- **Outputs:** a rebuilt Streamlit shell that ports **Direction A — Pipeline-as-spine** to a Streamlit-native implementation (Python + injected HTML/CSS/SVG, no new JS build pipeline), plus reusable visual primitives that future tabs can adopt.

### 1.3 Architecture summary

A **refactor** (not full re-architecture) of `src/dpsim/visualization/`. The current 7-step `render_lifecycle_workflow_panel` and tab-based recipe editor become the *content* of the new shell; the shell wraps them in a stage-spine + sticky run-rail layout, applies the new component library, and adds the three new affordances. Animated cross-sections (Rushton impeller side-view, packed-bed column with load/wash/elute/CIP phases) ship as `streamlit.components.v1.html` iframes — JavaScript stays sandboxed, the rest of the page remains pure Streamlit.

---

## 2. Requirements

### 2.1 MoSCoW

| Priority | Requirement | Source |
|---|---|---|
| **Must** | Pipeline spine: 7 stages always visible across the top, with active highlight, status colour, and click navigation | Pain #1, design A `<nav>` |
| **Must** | Per-parameter inline help (`?` icon → click-to-pin tooltip) | New affordance #2; design `Help` component |
| **Must** | Sticky right rail: run controls + breakthrough preview + evidence roll-up + recipe diff | New affordance #1, #3, design `RunRail` |
| **Must** | Stage-aggregated **evidence-tier roll-up** at the top, with per-metric badges expandable on hover/click | New affordance #4 |
| **Must** | Strict DESIGN.md compliance: Geist Sans + Geist Mono + JetBrains Mono; slate + teal palette; 4 px radius; no shadows; no entrance animations | DESIGN.md §All |
| **Must** | Run button toggles to orange "Stop" while running and a second click interrupts (matches design state machine) | Design A chat round 3 |
| **Must** | All `PolymerFamily` / `ACSSiteType` / `ModelEvidenceTier` / `ModelMode` comparisons use `.value`, never `is` | CLAUDE.md §enum |
| **Must** | ruff = 0, mypy = 0 on changed files | CLAUDE.md §CI |
| **Must** | Python 3.11 / 3.12 only | ADR-001 |
| **Should** | Animated cross-sections (M1 Rushton impeller side-view, M3 packed-bed column with phase tabs) | Design A M1 + M3 panels |
| **Should** | Live recipe-diff display (`path · prev → next`) toggleable from top bar | New affordance #1 |
| **Should** | A theme toggle (dark / light) where dark is the default | DESIGN.md §dark mode primary |
| **Could** | Direction B (Triptych workbench) as a second-pass refactor after Direction A ships | Design B (deferred) |
| **Could** | A / B direction switcher in the top bar | Design B (deferred) |
| **Won't (this iteration)** | Full pixel-for-pixel React port via Streamlit Custom Component build pipeline | Risk + scope; revisit if Streamlit-native fidelity is insufficient |

### 2.2 Acceptance criteria

- New shell renders correctly on Streamlit ≥ 1.36 with no `unsafe_allow_html` warnings (use `st.html`, not `st.markdown(unsafe_allow_html=True)`).
- All seven existing lifecycle panels (target / M1 / M2 / M3 / run / validation / calibration) load inside the new shell without regression — every existing keyboard-driven workflow continues to function.
- `tests/test_v9_3_enum_comparison_enforcement.py` passes (no `is`-based enum comparisons introduced).
- Smoke baseline: a recipe loaded in v0.3.8 produces the same `RunReport` in v0.4.0 (UI changes are presentation-only).
- Manual visual QA via the `qa` skill: pipeline spine renders, sticky rail does not detach on scroll, theme toggle flips colours within 150 ms.

---

## 3. Architecture Design

### 3.1 Six-dimension audit of the current UI (Reference 05)

| Dimension | Finding | Severity | Evidence |
|---|---|---|---|
| **D1 Structural** | `app.py` mixes shell concerns (CSS injection, page config, sidebar, manual PDF column) with workflow-panel orchestration | MEDIUM | `app.py:79-345` |
| **D1 Structural** | `tab_m1.py` (1300+ LOC), `tab_m2.py` (650+), `tab_m3.py` (900+) each render their own header + body inside a flat tabset — no shared `Card` chrome | MEDIUM | `tabs/tab_m*.py` |
| **D2 Algorithmic** | None — UI does no numerical computation; it delegates to the orchestrator | — | — |
| **D3 Data-flow** | `render_lifecycle_*` panels each pull from `SessionStateManager` independently; no single recipe-diff comparator | HIGH | `ui_workflow.py:render_lifecycle_*` |
| **D3 Data-flow** | No "previous run" snapshot is held in session state — diffing requires adding a snapshot at run-end | HIGH | (absent) |
| **D4 Performance** | Force-reload of all `dpsim` modules on every render (`app.py:24-36`) — slow but intentional for dev workflow | LOW | `app.py:24-36` |
| **D5 Maintainability** | Inline CSS in `app.py` is 200+ lines of `st.html` — maintainable but should be moved to a dedicated module | LOW | `app.py:79-287` |
| **D5 Maintainability** | No shared component library — the same evidence-badge pattern is reimplemented across three tabs | MEDIUM | grep `ModelEvidenceTier` across `tabs/` |
| **D6 First-principles** | UI honours the v9.0 family-first contract (PolymerFamily drives downstream rendering) | — | `tabs/m1/family_selector.py` |

**Verdict per Reference 05 §4:** **Refactor**. The fundamental decomposition (M1 / M2 / M3 stages, lifecycle orchestrator, evidence inheritance) is sound and matches the wet-lab process. The shell and visual chrome are the only things that need restructuring — *not* the underlying recipe / orchestrator / evidence model.

### 3.2 Direction A vs B trade-off

| | Direction A — Pipeline-as-spine | Direction B — Triptych workbench |
|---|---|---|
| **Information architecture** | Stage strip on top; one stage's editor in the main pane | Three columns (M1 / M2 / M3) always co-visible; one is focused, others collapse to summary chips |
| **Streamlit fit** | High — Streamlit's vertical column flow maps naturally; one pane at a time matches `st.tabs` mental model | Low — Streamlit columns do not natively support "expand on focus / collapse on blur"; needs heavy CSS + JS-driven width transitions |
| **Implementation risk** | LOW — about 1500–2500 LOC of Python + injected HTML/CSS/SVG | HIGH — likely needs a Streamlit Custom Component (React + npm build) for the focus-expanding columns |
| **Visual polish ceiling** | High — close to design fidelity for everything except `Help` click-to-pin (substitute with `st.popover`) | Highest — but requires the React build path |
| **Reuse of existing code** | High — `render_lifecycle_*` panels become stage bodies | Medium — needs new "summary chip" renderers per stage |

**Recommendation:** ship Direction A in v0.4.0; revisit B in v0.5.x once A is in users' hands and we have telemetry on whether the triptych is genuinely needed. The chat transcript itself flags A as "closest port of today's Streamlit flow. Single working surface + sticky rail. Lowest implementation risk; reuses existing tab/stage structure."

### 3.3 Module decomposition

The proposed package layout slots cleanly into the existing `src/dpsim/visualization/` tree without breaking imports:

```
src/dpsim/visualization/
├─ design/                            ← NEW
│   ├─ __init__.py
│   ├─ tokens.py        (M-001) Python-side token constants
│   ├─ tokens.css       (M-001) Verbatim from design handoff
│   └─ chrome.py        (M-002) st.html helpers — Card / Eyebrow / Chip / EvidenceBadge / StageNode / MetricValue / MiniHistogram / Breakthrough
├─ help/                              ← NEW
│   ├─ __init__.py
│   ├─ help_widget.py   (M-003) ParamRow + Help (st.popover-backed)
│   └─ catalog.py       (M-003) Per-parameter help-text catalog
├─ diff/                              ← NEW
│   ├─ __init__.py
│   ├─ snapshot.py      (M-004) Recipe snapshot + diff comparator
│   └─ render.py        (M-004) Render diff as "path · prev → next" lines
├─ run_rail/                          ← NEW
│   ├─ __init__.py
│   ├─ rail.py          (M-005) Sticky right-rail composition
│   └─ progress.py      (M-005) Run state machine (idle / running / stopping / done) + orange "Stop" button
├─ evidence/                          ← NEW
│   ├─ __init__.py
│   ├─ rollup.py        (M-006) Aggregate min-tier across stages
│   └─ badge.py         (M-006) Per-metric expandable badge
├─ components/                        ← NEW
│   ├─ __init__.py
│   ├─ impeller_xsec.py (M-007) Side-view Rushton — st.components.v1.html iframe
│   ├─ column_xsec.py   (M-008) Packed-bed cross-section — st.components.v1.html iframe
│   └─ assets/
│       ├─ impeller_xsec.html      Pre-rendered HTML body (vendored from design)
│       └─ column_xsec.html        Pre-rendered HTML body (vendored from design)
├─ shell/                             ← NEW
│   ├─ __init__.py
│   └─ shell.py         (M-009) New top app bar + stage spine + main grid + rail wiring
├─ app.py                             ← REFACTORED — pulls shell + delegates to existing tabs
├─ tabs/                              ← unchanged (rendered as stage bodies)
└─ … (rest unchanged)
```

### 3.4 Data-flow diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                       Streamlit page render                      │
└──────────────────────────────────────────────────────────────────┘
                                │
       ┌────────────────────────┴───────────────────────┐
       │                                                │
       ▼                                                ▼
[design.chrome.inject_global_css]              [SessionStateManager]
       │                                                │
       │                                                ▼
       │                                       [diff.snapshot.previous_run]
       │                                                │
       ▼                                                ▼
[shell.shell.render]  ←───────  active stage,  recipe, run state
       │
       ├─ TopBar (brand · DirectionSwitch · breadcrumb · run-history · diff/evidence/history toggle · theme · Manual)
       ├─ StageSpine (7 StageNode buttons — uses chrome.StageNode)
       ├─ Main grid (2 cols)
       │    ├─ left: stage body  ← delegates to tabs.render_tab_m1 / m2 / m3 OR
       │    │                       ui_workflow.render_lifecycle_*  for non-recipe stages
       │    └─ right: run_rail.rail.render
       │              ├─ run_rail.progress (Run / Stop button + progress bar)
       │              ├─ chrome.Breakthrough (P05/P50/P95 envelope)
       │              ├─ evidence.rollup (min-tier badge + drill-down)
       │              └─ diff.render (path · prev → next list)
       └─ (no footer in Direction A)
```

### 3.5 Critical path

`design.tokens` → `design.chrome` → `shell.shell` is the spine. Everything else is a leaf and can be parallelised after `chrome` is APPROVED. Estimated end-to-end: 5–7 module cycles.

### 3.6 Parallelism map

After M-001 (tokens) and M-002 (chrome) are APPROVED, the following can run concurrently in parallel build threads:

- M-003 (help) — depends only on M-002.
- M-004 (diff) — depends only on M-002 and `SessionStateManager`.
- M-005 (run_rail) — depends on M-002 and the `Breakthrough` SVG primitive in M-002.
- M-006 (evidence) — depends only on M-002 and `ModelEvidenceTier`.
- M-007 (impeller_xsec) — independent; vendored HTML asset.
- M-008 (column_xsec) — independent; vendored HTML asset.

M-009 (shell) integrates all of the above and must be last.

---

## 4. Module Specifications

### 4.1 M-001 — Design tokens

**Responsibility.** Single source of truth for design tokens (palette, type scale, spacing, radii). Tokens live in two forms: a `.css` file injected globally, and a Python dict so server-side renderers (`chrome.MetricValue`, `chrome.MiniHistogram`) can reference the same constants without duplication.

| Field | Value |
|---|---|
| Inputs | None (constants) |
| Outputs | `TOKENS: Final[dict[str, str]]`, `CSS_PATH: Final[Path]` |
| Algorithm | Direct port of `.dpsim_tmp/design_handoff/project/tokens.css`; verbatim except namespace prefix changes from `--` to `--dps-` for compatibility with the existing CSS layer in `app.py:79-287` |
| Complexity | O(1) load |
| Dependencies | None |
| Tests | M-001-T1: snapshot test that `tokens.css` matches the design handoff byte-for-byte (modulo prefix); M-001-T2: every `--dps-*` variable used in `chrome.py` exists in `tokens.css` |

### 4.2 M-002 — Chrome primitives (st.html-backed)

**Responsibility.** Stateless rendering helpers that emit one self-contained `<div>` of HTML+inline-CSS+SVG per call. No Streamlit widgets are emitted (those go in `help_widget.py`). Each helper takes Python-side data and returns either a string (for embedding) or calls `st.html(...)` directly.

**API surface (mirrors `components.jsx`):**

```python
def stage_node(*, index: int, label: str, status: str, active: bool,
               evidence: ModelEvidenceTier | None, complete: bool) -> str: ...
def card(*, eyebrow: str, title: str, right: str = "", body: str = "",
         padding: int = 16) -> str: ...
def evidence_badge(tier: ModelEvidenceTier, *, compact: bool = False) -> str: ...
def eyebrow(text: str, *, accent: bool = False) -> str: ...
def chip(text: str, *, color: str = "var(--dps-text-muted)", filled: bool = False) -> str: ...
def metric_value(value: str, unit: str = "", delta: str = "",
                 delta_direction: Literal["up", "down", None] = None) -> str: ...
def mini_histogram(bins: Sequence[float], *, accent: str = "var(--dps-accent)") -> str: ...
def breakthrough(curve: BreakthroughCurve, *, width: int = 320, height: int = 86) -> str: ...
```

Critical detail from CLAUDE.md and `app.py:73-78`: **never** route HTML through `st.markdown(unsafe_allow_html=True)`. The Markdown parser eats `*` characters in CSS attribute selectors. Use `st.html(...)` for any block containing `[class*=…]` patterns.

**Tests.** Snapshot tests (HTML output equality) for each primitive; visual diff via `qa` skill against the design handoff screenshots.

### 4.3 M-003 — Help / ParamRow

**Responsibility.** Wrap a Streamlit input widget with a left-side label, optional `?` help icon (rendered as `st.popover`), optional unit suffix, optional inline evidence badge. Replace the plain `st.slider` / `st.number_input` / `st.selectbox` calls scattered across `tabs/`.

```python
def param_row(label: str, *, help: str = "", unit: str = "",
              evidence: ModelEvidenceTier | None = None,
              widget: Callable[[], T]) -> T: ...
```

`help` is rendered via `st.popover("?")` (a native Streamlit primitive that gives click-to-pin behaviour without bespoke JS).

**Tests.** M-003-T1: `param_row(..., widget=lambda: st.slider("x", 0, 10, 5))` returns the slider's value. M-003-T2: catalog entries exist for every parameter rendered in `tab_m1.py` / `tab_m2.py` / `tab_m3.py` (coverage gate).

### 4.4 M-004 — Recipe diff

**Responsibility.** At run-end, deep-snapshot the `ProcessRecipe` into `st.session_state["_dpsim_last_run_recipe"]`. On every subsequent render, diff the *current* recipe against the snapshot and produce a list of `DiffEntry(path: str, prev: Any, next: Any)` records. Render those via `chrome.eyebrow + monospace path · prev → next` rows.

**Algorithm.** Recursive walk over `ProcessRecipe`'s pydantic model, comparing field-by-field; at leaves, format with the same units the editor uses. O(n) in the number of recipe fields (≈100).

**Tests.** M-004-T1: snapshot identical recipe → empty diff. M-004-T2: change `agarose_pct` 4.0 → 3.5 → diff yields exactly `m1.formulation.agarose_pct: 4.0 → 3.5`. M-004-T3: pydantic schema evolution (new field added) → existing snapshots do not crash, the new field shows as `(absent) → next`.

### 4.5 M-005 — Run rail + run-state machine

**Responsibility.** Sticky right-pane composition with the run/stop button (orange while running per the chat round-3 fix), progress bar, breakthrough preview, evidence roll-up, and recipe diff. Wraps the existing `render_lifecycle_run_panel` and `render_lifecycle_results_panel`.

State machine (matches `direction-a.jsx:16-35`):
- `idle` — button shows "Run lifecycle" (teal)
- `running` — button shows "Stop run" with `■` icon (orange / `--dps-warning`); a click here cancels
- `stopping` — transitional, suppress click for 200 ms
- `done` — transitions back to `idle` after results render; if last run errored, button is `--dps-error` red

Streamlit-side cancellation uses `st.session_state["_dpsim_run_cancelled"] = True` and a polling check in the orchestrator. **Risk:** Streamlit reruns are not preemptible. The "Stop" button can only be honoured at the next checkpoint inside the orchestrator's iteration loop. Document this in the handover; the visual state matches user expectation but cancellation is not instant.

**Tests.** M-005-T1: idle → running on click. M-005-T2: running + click → stopping → idle within 1 s. M-005-T3: button colour matches state machine via DOM inspection.

### 4.6 M-006 — Evidence roll-up

**Responsibility.** Read `RunReport.compute_min_tier` (already implemented per CLAUDE.md) and surface the lifecycle-min tier in the top bar; per-metric badges in the run-rail expand on click to show the inheritance chain.

**Tests.** M-006-T1: M1 calibrated_local + M2 semi_quantitative + M3 calibrated_local → top-bar min = semi_quantitative. M-006-T2: drill-down on M3 DBC10 metric shows the min was inherited from M2.

### 4.7 M-007 — ImpellerCrossSection (component)

**Responsibility.** Embed the side-view Rushton-turbine animated SVG from `components.jsx:804-1168` as a self-contained HTML asset and render it via `st.components.v1.html(html, height=h)`. The component takes `rpm` as a prop and renders a self-contained iframe — JavaScript stays sandboxed.

**Implementation.** Vendor `components.jsx` ImpellerCrossSection into `assets/impeller_xsec.html`, wrap with React UMD bundle (or a hand-rolled minimal vanilla equivalent — preferable to avoid the React dependency for one component). Recommend the vanilla path: convert RAF animation loop → `requestAnimationFrame` directly, replace JSX with `Element.innerHTML` once and SVG attribute updates each frame.

**Risk.** RAF loops in iframes work but can leak timers if Streamlit re-renders the iframe. Mitigation: register a `pagehide` listener to cancel the RAF.

**Tests.** M-007-T1: render with `rpm=420` → iframe loads without JS errors. M-007-T2: HTML asset is < 30 kB to keep the page weight reasonable.

### 4.8 M-008 — ColumnCrossSection (component)

Same pattern as M-007, vendoring `components.jsx:482-781`. Phase tabs (`load` / `wash` / `elute` / `cip`) controlled via a `streamlit.components.v1` message handler (or via a `?phase=` query param re-render on change — simpler).

### 4.9 M-009 — Shell

**Responsibility.** The new top-level page render. Replaces the body of `app.py` with calls to:

```python
shell.render_top_bar(...)              # brand + breadcrumb + run history + diff toggle + theme + Manual
shell.render_stage_spine(active=...)   # 7 StageNode buttons
shell.render_main_grid(active, recipe, run_state)
    └─ left: dispatch to existing render_tab_m1 / m2 / m3 / render_lifecycle_*
    └─ right: run_rail.render(...)
```

Crucially, the existing `tab_m1.py` / `tab_m2.py` / `tab_m3.py` files are **not rewritten** in this milestone. The shell wraps them; their internal layout receives the new `param_row`-based `Help` polish in a follow-on milestone (v0.4.1).

### 4.10 M-010 — Smoke tests

**Responsibility.** New tests in `tests/test_ui_chrome_smoke.py`:

- T-S-01: importing the new `dpsim.visualization.design` / `…shell` packages does not error.
- T-S-02: `chrome.evidence_badge(ModelEvidenceTier.CALIBRATED_LOCAL)` returns valid HTML containing `class="dps-badge"` and the tier label.
- T-S-03: `app.py` still imports cleanly (regression catch).
- T-S-04: AST gate (`test_v9_3_enum_comparison_enforcement.py`) still passes after the new modules land.

### 4.11 M-011 — Handover document

This file, finalised after the implementation cycle: a "what shipped, what didn't, what's next" record + the design log of every divergence from the React prototype.

---

## 5. Algorithm Justifications

The implementation has no novel numerical content — every primitive is a layout / template / DOM manipulation. The only judgement calls are:

- **Streamlit-native vs Streamlit Custom Component (React + npm).** Chosen Streamlit-native because: (a) the user has not asked for pixel-perfect React port; the design handoff README explicitly says "*Recreate them pixel-perfectly in whatever technology makes sense*"; (b) no other DPSim subsystem uses npm — adding it has a build-pipeline tax and bus-factor cost; (c) Streamlit-native keeps the entire codebase Python + a CSS file, which matches the existing `tabs/` ergonomic. **Trade-off:** click-to-pin help, focus-expanding columns (Direction B), and instant theme-toggle are slightly degraded. Direction B is deferred precisely so this trade-off does not block v0.4.0.
- **Animated SVG via `st.components.v1.html` iframe** rather than inline `st.html`. iframes sandbox the RAF loops and avoid namespace collisions with Streamlit's own React tree. Slightly more weight per component (+~10 kB iframe scaffolding) but operationally cleaner.

---

## 6. Data Representation Specification

| Data flow | Type | Encoding | Notes |
|---|---|---|---|
| Design tokens | `dict[str, str]` | Python const + `.css` file | Slate / teal hex strings; spacing in `px` |
| Stage status | `Literal["pending", "active", "valid", "warn"]` | Python enum-like literal | Maps 1:1 to `chrome.stage_node` colour table |
| Recipe diff | `list[DiffEntry(path, prev, next)]` | dataclass | `path` is a dotted string e.g. `m1.formulation.agarose_pct` |
| Run state | `Literal["idle", "running", "stopping", "done", "error"]` | Python literal | Stored at `st.session_state["_dpsim_run_state"]` |
| Evidence tier | `ModelEvidenceTier` | existing enum | **Always compare via `.value` per CLAUDE.md** |
| Cross-section RPM | `float` | iframe URL param `?rpm=` | Plain int round-trip is fine |
| Cross-section phase | `Literal["load", "wash", "elute", "cip"]` | iframe URL param `?phase=` | Reset animation on change |

---

## 7. Integration Specification

### 7.1 Migration sequence

1. Land M-001 (tokens). The new `tokens.css` is added but not yet referenced by `app.py`. CI green.
2. Land M-002 (chrome). Unit tests and snapshot tests for each primitive. CI green.
3. Land M-003–M-006 in any order (parallelisable). Each introduces a new module with its own tests; **none modify `app.py` yet**.
4. Land M-007, M-008 (components). Each ships the iframe HTML asset.
5. Land M-009 (shell). This is the cut-over: `app.py` is refactored to call `shell.render_top_bar(...)` etc. The old code path is deleted in the same commit.
6. Land M-010 (smoke tests).
7. Land M-011 (handover document, finalised).

### 7.2 Backward-compatibility contract

The existing public API of `dpsim.visualization` (the `render_*` functions exposed via `tabs/__init__.py` and `panels/__init__.py`) **must not change** during this refactor. They are now called from inside the shell rather than directly from the Streamlit script, but their signatures are stable. This protects external runners (CLI `python -m dpsim ui`, IDE tooling, automated tests).

### 7.3 Logging and monitoring

No new logging surface. The existing `logger` in `app.py` is preserved; the new modules log under `logging.getLogger("dpsim.visualization.<submodule>")` to keep CLAUDE.md's diagnostic story coherent.

---

## 8. Performance Analysis

| Measurement | v0.3.8 baseline | v0.4.0 target | Why |
|---|---|---|---|
| First paint (cold load) | ~3.5 s | ≤ 4.5 s (+1 s budget) | New iframes add network + JS bootstrap; budget intentionally loose for v0.4.0 |
| Re-render after slider drag | ~0.6 s | ≤ 0.7 s | One extra `chrome.*` call per affected ParamRow |
| Recipe-diff compute | n/a | < 5 ms | Pydantic field walk over ~100 fields |
| Iframe HTML asset weight | n/a | ≤ 30 kB each | Vanilla SVG + RAF, no React UMD |
| Page weight delta | — | +50–80 kB total | Two iframes + new CSS module + Geist already loaded |

If first-paint regresses past 4.5 s, fall back to lazy-loading the M1/M3 cross-sections behind a "Show animation" expander — the science is in the numbers, not the visual.

---

## 9. Risk Register

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-01 | Streamlit theme toggle does not propagate to iframe contents | HIGH | MEDIUM | Pass current theme as URL param to iframes (`?theme=dark`); iframe applies the matching `.dps-light` body class |
| R-02 | Sticky right rail conflicts with Streamlit's full-width `block-container` | MEDIUM | HIGH | Use `position: sticky; top: <px>` with explicit min-width on the left pane; verify on Streamlit ≥ 1.36 |
| R-03 | Stop-during-run cannot interrupt mid-orchestrator-step | HIGH | LOW | Document the "next checkpoint" semantics in the run-rail tooltip; do not promise instant cancel |
| R-04 | `st.popover` (used for inline help) requires Streamlit ≥ 1.32 | LOW | MEDIUM | Bump `streamlit` minimum in `pyproject.toml` if needed; gate behind a fallback `st.expander` for older versions (probably unnecessary — repo is on a recent Streamlit) |
| R-05 | RAF loops in iframes leak timers across Streamlit re-renders | MEDIUM | LOW | Listen for `pagehide` / `unload` and `cancelAnimationFrame` |
| R-06 | Vendoring React UMD into iframes adds 130 kB | MEDIUM | MEDIUM | Use vanilla JS + manual SVG attr updates; do not ship React |
| R-07 | The 968 LOC of `direction-a.jsx` is more nuance than this plan captures | HIGH | LOW | Plan covers shell + primitives; per-stage layout polish is deferred to v0.4.1 follow-on; smoke baseline protects against regressions |
| R-08 | DESIGN.md drift — somebody hand-edits a hex string in `chrome.py` | MEDIUM | LOW | Add a CI check: `tests/test_design_tokens_match.py` reads `tokens.css` and verifies the Python `TOKENS` dict and `chrome.py` only reference values from that file |

---

## 10. Module Registry (initial state)

Per Reference 07 §5. Empty until M-001 is APPROVED — the orchestrator populates this as modules clear the audit gate.

```
| # | Module | Version | Status   | Approved Date | Model Used | Fix Rounds | Lines | File Path |
|---|--------|---------|----------|---------------|------------|------------|-------|-----------|
| 1 | M-001 design.tokens         | 0.4.0 | PENDING | — | Haiku  | — | ~150 | src/dpsim/visualization/design/ |
| 2 | M-002 design.chrome         | 0.4.0 | PENDING | — | Sonnet | — | ~600 | src/dpsim/visualization/design/chrome.py |
| 3 | M-003 help                  | 0.4.0 | PENDING | — | Sonnet | — | ~400 | src/dpsim/visualization/help/ |
| 4 | M-004 diff                  | 0.4.0 | PENDING | — | Sonnet | — | ~300 | src/dpsim/visualization/diff/ |
| 5 | M-005 run_rail              | 0.4.0 | PENDING | — | Sonnet | — | ~350 | src/dpsim/visualization/run_rail/ |
| 6 | M-006 evidence              | 0.4.0 | PENDING | — | Sonnet | — | ~250 | src/dpsim/visualization/evidence/ |
| 7 | M-007 components.impeller   | 0.4.0 | PENDING | — | Opus   | — | ~400 (HTML+JS) | src/dpsim/visualization/components/ |
| 8 | M-008 components.column     | 0.4.0 | PENDING | — | Opus   | — | ~500 (HTML+JS) | src/dpsim/visualization/components/ |
| 9 | M-009 shell                 | 0.4.0 | PENDING | — | Opus   | — | ~400 | src/dpsim/visualization/shell/ |
|10 | M-010 smoke tests           | 0.4.0 | PENDING | — | Haiku  | — | ~200 | tests/test_ui_chrome_smoke.py |
|11 | M-011 handover doc          | 0.4.0 | PENDING | — | Sonnet | — | ~400 | docs/handover/ARCH_v0_4_0_UI_OPTIMIZATION_CLOSE.md |
```

Model tier rationale per Reference 07 §3:

- **Haiku**: M-001 (constants), M-010 (boilerplate tests).
- **Sonnet**: M-002, M-003, M-004, M-005, M-006, M-011 — domain-aware code with standard logic, 200–600 LOC.
- **Opus**: M-007, M-008 (animated SVG with RAF + physical-meaning visuals — needs care to keep flow direction physically correct, see chat round 8 about Rushton flow direction); M-009 (shell — integrates everything, novel composition, ≥200 LOC of integration work).

---

## 11. Integration Status (initial)

```
| Interface                 | From Module | To Module | Status   | Notes |
|---------------------------|-------------|-----------|----------|-------|
| TOKENS dict               | M-001       | M-002     | PENDING  | Token names must match tokens.css |
| evidence_badge HTML       | M-002       | M-006     | PENDING  | Reuse, do not reimplement |
| breakthrough HTML         | M-002       | M-005     | PENDING  | Run rail consumes it |
| param_row(...)            | M-003       | tabs/*    | PENDING  | v0.4.1 follow-on; not in this milestone's tabs rewrite |
| diff_entries              | M-004       | M-005     | PENDING  | Rail renders the diff list |
| min_tier                  | M-006       | shell.top_bar | PENDING | Top-bar evidence-tier display |
| iframe HTML payloads      | M-007/M-008 | shell    | PENDING  | st.components.v1.html embed |
| shell.render_*            | M-009       | app.py    | PENDING  | Cut-over commit |
```

---

## 12. Open Questions for /scientific-advisor

These are domain questions that benefit from a scientific second opinion before we hand off to the implementation cycle:

1. **Cross-section physical accuracy.** The chat round 7–8 already corrected the Rushton flow-direction model (radial discharge → upper/lower loops returning along the wall). Before we vendor the SVG, please re-verify the flow loop direction matches Rushton physics for emulsification (not just stirring). Confirm: upper loop = up the wall, across the surface to the shaft, down to the disk; lower loop mirrors. Confirm: blade height ratio (`bladeAbove ≈ 2 × bladeBelow`) is consistent with a Rushton-disk turbine where the disk is mounted at mid-blade-height.
2. **Column cross-section semantics.** During elution, our prototype shows bound payload "releasing into the eluate" by recolouring beads back to surface-3. Is this physically accurate enough for a screening UI, or should we show the displaced payload as moving distinct dots flowing out the bottom (the way wash and CIP already do)? The current code mixes both — bead recolour AND distinct streaming dots — but only for elute / cip / wash.
3. **Evidence inheritance UX.** Currently `RunReport.compute_min_tier` returns the *lifecycle* min. Should the top-bar badge show the lifecycle min (current plan), the worst per-stage min as separate chips (more informative but louder), or both with the lifecycle aggregated and a hover-revealed per-stage breakdown? Recommend the third — please confirm.
4. **Recipe diff comparison basis.** Diff vs *last successful run* (current plan), vs *last run regardless of success*, or vs *named baseline* (e.g. tagged `protein_a_pilot.toml@v1`)? The third is clearly more powerful but increases scope; please rule on whether v0.4.0 should ship the simpler "last run" semantics with v0.4.1 adding named baselines.

---

## 13. Pre-flight check (orchestration framework — Reference 07)

| Item | Status |
|---|---|
| Context budget | GREEN — current dialogue at ~30% used; this plan + handoff fits comfortably. |
| Upstream dependencies | None — this is the first cycle in the v0.4.0 milestone. |
| Model selection | This plan: Opus (architecture). Implementation tier ladder is in §10. |
| Milestone proximity | v0.4.0 is itself a milestone; the close-handover (M-011) is pre-allocated. |

---

## 14. Next steps

1. **/scientific-advisor** — review §12 questions; sign off on cross-section physical fidelity and evidence-aggregation UX.
2. **/dev-orchestrator** — open the v0.4.0 milestone, register modules per §10, start the M-001 → M-009 build sequence.
3. **First implementation cycle** — `/scientific-coder` builds M-001 against this protocol; Architect re-audits per Reference 07 §4.
4. **Cut-over commit** — once M-009 is APPROVED, the `app.py` refactor lands as a single atomic PR with the smoke tests (M-010).
5. **/qa or /design-review** — visual QA against the design handoff screenshots once the shell is live.
6. **Close handover** — finalise M-011 with the actual fix-round counts, diffs from this protocol, and any deferred items.

---

## 15. Revision history

| Version | Date | Changes |
|---|---|---|
| 0.1 | 2026-04-26 | Initial draft from /architect skill. Pending /scientific-advisor review. |
