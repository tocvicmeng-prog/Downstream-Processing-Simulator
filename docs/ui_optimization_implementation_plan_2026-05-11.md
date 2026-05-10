# UI Optimization Implementation Plan

Based on: `docs/ui_audit_2026-05-11.md`  
Plan date: 2026-05-11  
Target application: Downstream Processing Simulator Streamlit UI  
Primary code area: `src/dpsim/visualization`

## Purpose

This plan converts the UI audit findings into an implementable engineering roadmap. The objective is not to redesign the simulator from scratch. The objective is to make the existing scientific UI more reliable, more operator-readable, more bench-actionable, and easier to maintain while preserving the current lifecycle-first workflow.

The plan assumes the simulator remains a research-grade downstream-processing simulation and process-development tool. It does not attempt to convert the UI into a validated GMP batch-record system or live instrument-control HMI.

## Optimization Goals

1. Make scientific state and result provenance unambiguous.
2. Make the Run and M3 stages behave more like expert instrument-console workflows.
3. Make optimization outputs physically actionable for downstream-processing users.
4. Improve responsive layout reliability across desktop, laptop, and narrow displays.
5. Reduce future UI regression risk with visual and contract tests.
6. Reduce maintenance risk by breaking very large UI modules into smaller components.
7. Preserve evidence-tier honesty and avoid false precision.

## Guiding Design Principles

### Lifecycle First

The application should continue to organize around the downstream lifecycle:

`Target -> M1 -> M2 -> M3 -> Run -> Validation -> Calibration`

This lifecycle structure is scientifically correct and should remain the primary navigation model.

### Operator Decision First

Each stage should lead with the decision an experienced DSP user needs to make, then expose diagnostics and advanced controls after the decision context is established.

For example, M3 should lead with:

1. Is the method physically feasible?
2. Is the prediction calibrated enough to use?
3. What is the expected DBC/recovery/pressure result?
4. What experimental action should I take next?

### Evidence Before Precision

Metric rendering must continue to be evidence-tier aware. A weakly supported simulation should never look more precise than the evidence allows.

### Bench-Actionable Before Model-Internal

Optimization and inverse-design outputs should prioritize physical recipe settings such as pH, conductivity, residence time, flow rate, column geometry, loading, gradient slope, and pressure envelope. Normalized model coordinates should be secondary.

### Progressive Disclosure

The UI should show the minimum credible scientific path first. Advanced options, model internals, and diagnostics should remain available but not dominate the default screen.

### Stable Provenance

Every visible result should make clear:

- Which recipe generated it.
- Whether it came from a lifecycle run, direct stage run, cached baseline, imported wet-lab data, or optimizer campaign.
- Whether upstream edits have made it stale.
- Which evidence tier governs its display.

## Audit Finding Traceability

| Audit ID | Audit finding | Plan response |
|---|---|---|
| F1 | Calibration and M3 information architecture is overloaded. | Split stage responsibilities visually and then structurally. |
| F2 | Optimizer output is not bench-actionable enough. | Add physical recipe cards and SOP-ready optimizer output. |
| F3 | Large UI modules increase maintenance risk. | Extract M1/M2/M3/calibration sections into smaller components. |
| F4 | Responsive layout reliability is not proven. | Add browser screenshot tests and responsive rail behavior. |
| F5 | Scientific Mode consequences are not visible enough. | Add mode-aware run preflight and result explanations. |
| F6 | Direct M3 runs and lifecycle runs can create ambiguity. | Add result provenance and stale-output labels. |
| F7 | Inverse inference onboarding conflicts with minimum data requirement. | Seed valid measurement templates and improve sufficiency UI. |
| F8 | Streamlit DOM/CSS coupling may break on upgrades. | Add visual regression suite and Streamlit upgrade checklist. |
| F9 | Accessibility and locked-down lab environment concerns remain. | Add accessibility, font, and contrast hardening. |
| F10 | Production instrument expectations could be misread. | Preserve simulator disclaimers in exports and result summaries. |

## Definition of Done

The UI optimization work is complete when:

1. Existing UI and workflow tests pass.
2. Browser-level viewport tests cover at least one representative path through Target, M3, Run, Validation, and Calibration.
3. M3 and Run surfaces show result provenance and stale-output status.
4. Scientific Mode effects are visible before execution and near key outputs.
5. Optimizer results can be read as physical, bench-actionable recipes.
6. Inverse inference opens with a valid minimum-data path.
7. The right rail and top chrome do not crowd or overlap at supported viewport widths.
8. At least the largest M3 responsibilities are split into smaller components without changing simulation behavior.
9. Exported reports or SOP artifacts preserve evidence tier and simulator-use disclaimers.

## Non-Goals

The following are intentionally out of scope for this UI optimization cycle:

- Live instrument control.
- GMP electronic batch records.
- Regulatory validation workflow.
- New chromatography physics or adsorption models.
- Replacing Streamlit with a different frontend framework.
- Full visual rebranding.

## Phase 0 - Baseline Protection

Estimated effort: 2 to 4 engineering days  
Primary goal: prevent UI optimization work from creating silent regressions.

### 0.1 Add Browser Visual Regression Harness

Reason:

The audit identified responsive and custom-CSS risk. Existing tests are strong, but they do not prove actual rendered layout behavior across viewports.

Likely files:

- `tests/visualization/`
- `tests/visualization/test_ui_viewports.py`
- `pyproject.toml` or dependency configuration
- Optional helper: `tests/visualization/streamlit_server.py`

Implementation steps:

1. Add Playwright or an equivalent browser automation test dependency.
2. Start Streamlit on a random available local port for test sessions.
3. Capture screenshots or DOM layout assertions for the main shell.
4. Test these viewports:
   - Wide desktop: `1440 x 1000`
   - Laptop: `1280 x 800`
   - Narrow desktop/tablet: `1024 x 768`
   - Mobile-like narrow smoke: `390 x 844`
5. Cover both light and dark themes if theme can be selected deterministically.
6. Cover Direction A and Direction B.

Acceptance criteria:

- The app loads without blank screens.
- Top bar controls do not overlap.
- Pipeline navigation is visible or intentionally collapsed.
- Run rail is visible, collapsed, or intentionally moved depending on viewport.
- No KPI cards overlap the stage body.
- Screenshots are stored only as test artifacts, not as repository noise unless approved.

### 0.2 Pin Streamlit Layout Upgrade Risk

Reason:

The UI depends on Streamlit rendering behavior, custom CSS, `st.html`, and internal DOM patterns.

Likely files:

- `pyproject.toml`
- `requirements*.txt` if present
- `docs/ui_evolution.md`
- New doc section: Streamlit upgrade checklist

Implementation steps:

1. Identify the current Streamlit version used by the repo.
2. Document the supported version range.
3. Add an upgrade checklist:
   - Run unit/UI tests.
   - Run browser viewport tests.
   - Verify top app bar.
   - Verify rail layout.
   - Verify M3 stage.
   - Verify Calibration stage.
   - Verify exports if affected.

Acceptance criteria:

- Streamlit upgrades have an explicit visual QA process.
- The support matrix or UI evolution doc records the tested version.

### 0.3 Establish Result Provenance Contract

Reason:

The audit identified ambiguity between lifecycle runs, direct M3 runs, cached baselines, and pending edits.

Likely files:

- `src/dpsim/visualization/ui_workflow.py`
- `src/dpsim/visualization/shell/autowire.py`
- `src/dpsim/visualization/run_rail/rail.py`
- `src/dpsim/visualization/tabs/tab_m3.py`
- `src/dpsim/visualization/ui_recipe.py`

Proposed lightweight data contract:

```python
@dataclass(frozen=True)
class ResultProvenance:
    result_id: str
    source: str  # lifecycle, direct_m3, optimizer, wet_lab_import, baseline
    created_at: str
    recipe_fingerprint: str
    scientific_mode: str
    evidence_tier: str
    stale: bool = False
    stale_reasons: tuple[str, ...] = ()
```

Implementation notes:

- Prefer adding a small local model only if existing state helpers do not already provide equivalent structure.
- Use a deterministic recipe fingerprint from serialized `ProcessRecipe`.
- Do not mutate existing result objects if adapters are safer.
- Preserve legacy session-state aliases during the transition.

Acceptance criteria:

- M3 result cards show source and freshness.
- Run rail shows whether displayed KPIs match the current recipe.
- Validation can distinguish current lifecycle results from stale cached results.
- Existing tests continue to pass.

## Phase 1 - Scientific Decision Clarity

Estimated effort: 1 to 2 weeks  
Primary goal: make the existing scientific model easier to understand and safer to use.

### 1.1 Add Scientific Mode Preflight Summary

Reason:

Users can select Empirical, Hybrid, or Mechanistic mode, but the consequences should be visible at the point of execution.

Likely files:

- `src/dpsim/visualization/app.py`
- `src/dpsim/visualization/shell/stage_panels.py`
- `src/dpsim/visualization/ui_workflow.py`
- Potential new component: `src/dpsim/visualization/components/mode_preflight.py`

UI behavior:

Near the Run stage and M3 run controls, show a compact preflight summary:

- Active Scientific Mode.
- Expected model pathway.
- Calibration requirements.
- Outputs likely to be exact, interval-based, rank-band, or suppressed.
- Expected runtime category.
- Main uncertainty source.

Example panel content:

```text
Mode: Hybrid
Active pathway: calibrated empirical transport with mechanistic pressure check
Calibration status: M2 semi-quantitative, M3 weak
Expected output rendering: DBC interval, pressure numeric, optimizer rank-band
Recommended next action: add >=8 breakthrough observations to promote M3 confidence
```

Acceptance criteria:

- Mode consequences are visible before long-running execution.
- Text changes when the mode changes.
- The component uses existing evidence-tier and calibration state where possible.
- No unsupported scientific claims are introduced.

### 1.2 Add Result Source Badges

Reason:

Experienced users need to know whether they are looking at a current lifecycle result, a direct stage result, or a cached baseline.

Likely files:

- `src/dpsim/visualization/run_rail/rail.py`
- `src/dpsim/visualization/tabs/tab_m3.py`
- `src/dpsim/visualization/shell/tier_banner.py`
- `src/dpsim/visualization/shell/autowire.py`

Badge types:

- `Current lifecycle`
- `Direct M3`
- `Baseline`
- `Optimizer candidate`
- `Wet-lab import`
- `Stale`
- `Pending edits`

Acceptance criteria:

- Every major result area shows a provenance badge.
- Stale badges include a short reason.
- Badge labels are text-readable, not icon-only.
- Badge status is included in exported reports where applicable.

### 1.3 Add "What Changed Since Last Run" Summary

Reason:

The run rail already tracks pending edits. This should become more actionable for scientific users.

Likely files:

- `src/dpsim/visualization/run_rail/rail.py`
- `src/dpsim/visualization/ui_recipe.py`
- `src/dpsim/visualization/shell/autowire.py`

Implementation steps:

1. Compare current recipe fingerprint with last-run fingerprint.
2. Classify changes by stage:
   - Target
   - M1
   - M2
   - M3
   - Calibration
3. Show high-impact changes first.
4. Avoid showing raw JSON diffs in the default view.

Acceptance criteria:

- Users can see whether a result was invalidated by column geometry, mobile phase, chemistry, or calibration changes.
- The summary fits in the rail without forcing excessive vertical scrolling.

### 1.4 Improve Inverse Inference Starting State

Reason:

The current fitting logic correctly blocks underdetermined inference, but the default table starts below the minimum data requirement.

Likely files:

- `src/dpsim/visualization/tabs/calibration/inverse_inference.py`
- `tests/visualization/`

Implementation steps:

1. Seed the default table with at least 8 rows.
2. Add a small sufficiency indicator:
   - `3/8 observations: add more data`
   - `8/8 observations: ready for posterior fit`
3. Provide a one-click template reset.
4. Keep validation strict.

Acceptance criteria:

- A first-time user can reach a valid fitting shape without manually adding rows.
- Underdetermined data remains blocked.
- Tests cover the minimum-row behavior.

## Phase 2 - Layout and Information Architecture

Estimated effort: 2 to 3 weeks  
Primary goal: reduce panel density and make the UI behave more like an expert scientific instrument console.

### 2.1 Make the Run Rail Responsive

Reason:

The fixed right rail is useful on wide screens but risky on constrained displays.

Likely files:

- `src/dpsim/visualization/design/tokens.css`
- `src/dpsim/visualization/run_rail/rail.py`
- `src/dpsim/visualization/shell/shell.py`

Responsive behavior:

| Viewport | Rail behavior |
|---|---|
| Wide desktop | Full right rail with KPIs, evidence, history. |
| Laptop | Narrow rail with compact KPIs and collapsible details. |
| Narrow tablet/mobile | Bottom drawer or inline collapsed summary. |

Implementation notes:

- Avoid relying only on `:has(...)` for critical layout behavior.
- Use CSS variables for rail width.
- Keep rail content order stable.
- Ensure run/stop controls remain reachable.

Acceptance criteria:

- No overlap at `1440`, `1280`, `1024`, and `390` px widths.
- KPI cards keep stable dimensions.
- Buttons remain legible and clickable.

### 2.2 Simplify the Top Bar Under Constrained Widths

Reason:

The top app bar carries many controls. It should preserve scientific status without crowding.

Likely files:

- `src/dpsim/visualization/shell/shell.py`
- `src/dpsim/visualization/design/tokens.css`
- `src/dpsim/visualization/app.py`

Implementation steps:

1. Identify controls that must always remain visible:
   - App identity.
   - Scientific Mode.
   - Evidence state.
   - Active stage.
2. Move secondary controls into a compact menu at narrower widths:
   - Manual/help.
   - View direction if needed.
   - Theme.
3. Preserve keyboard access and tooltips.

Acceptance criteria:

- Top bar does not wrap into incoherent rows.
- Scientific Mode and evidence tier remain visible.
- Secondary controls remain discoverable.

### 2.3 Reorganize M3 Around the Operator Flow

Reason:

M3 is scientifically central but currently dense. The content should follow column-operation decision order.

Likely files:

- `src/dpsim/visualization/tabs/tab_m3.py`
- New candidate modules:
  - `src/dpsim/visualization/tabs/m3/setup_panel.py`
  - `src/dpsim/visualization/tabs/m3/feasibility_panel.py`
  - `src/dpsim/visualization/tabs/m3/run_controls.py`
  - `src/dpsim/visualization/tabs/m3/decision_summary.py`
  - `src/dpsim/visualization/tabs/m3/diagnostics_panel.py`
  - `src/dpsim/visualization/tabs/m3/export_panel.py`

Target order:

1. Column and method setup.
2. Pressure and feasibility envelope.
3. Run controls.
4. Decision summary.
5. Diagnostic traces.
6. SOP, export, and comparison.

Acceptance criteria:

- A user can determine physical feasibility before running.
- A user can see the key decision result before diagnostic plots.
- SOP/export is reachable but does not interrupt method setup.
- Existing M3 scientific calculations remain unchanged.

### 2.4 Separate Calibration, Inverse Design, and Series Design

Reason:

Calibration currently contains tools that are not all calibration tasks.

Short-term implementation:

- Keep the existing Stage 07 route.
- Introduce clearer subtabs or section headings:
  - Calibration data
  - Uncertainty propagation
  - Inverse inference
  - Series design
  - Optimization

Longer-term implementation:

- Consider adding a dedicated "Design" or "Optimize" stage after Validation.
- Keep Calibration focused on data and parameter confidence.

Likely files:

- `src/dpsim/visualization/tabs/tab_calibration.py`
- `src/dpsim/visualization/shell/shell.py`
- `src/dpsim/visualization/shell/stage_panels.py`
- `src/dpsim/visualization/tabs/tab_optimization.py`

Acceptance criteria:

- Users can distinguish calibration from inverse design.
- Multi-column design no longer appears mislabeled as calibration.
- Existing query-param navigation continues to work.

## Phase 3 - Bench-Actionable Optimization

Estimated effort: 2 to 4 weeks  
Primary goal: make optimization results usable by a downstream scientist without decoding model internals.

### 3.1 Add Physical Recipe Cards for Optimizer Results

Reason:

The audit found that normalized 7-D coordinates are not sufficient as the primary optimizer output.

Likely files:

- `src/dpsim/visualization/tabs/tab_optimization.py`
- `src/dpsim/visualization/decision_grade_render.py`
- `src/dpsim/visualization/ui_recipe.py`
- Existing optimization search-space utilities

Primary recipe card fields:

- Product/target context.
- Matrix and ligand summary.
- Column diameter and bed height.
- Bed volume.
- Flow rate.
- Residence time.
- Load density.
- pH.
- Conductivity or salt condition.
- Gradient slope or step condition.
- Expected DBC10.
- Expected recovery.
- Expected pressure.
- Evidence tier.
- Feasibility status.
- Main uncertainty driver.

Acceptance criteria:

- The top optimizer result can be read directly as a physical method proposal.
- Normalized coordinates are moved to an advanced/debug view.
- Decision-grade rendering still governs displayed metrics.

### 3.2 Add Actionability Gates

Reason:

"Best predicted" is not necessarily "best actionable."

Actionability gates:

- Pressure feasible.
- Evidence tier acceptable.
- Calibration sufficiency acceptable.
- No missing M1/M2/M3 dependency.
- Operating point inside supported model domain.
- SOP export possible.

Acceptance criteria:

- The UI explains why a candidate is not actionable.
- Ranking distinguishes predicted objective value from deployability.
- Users can filter to actionable candidates.

### 3.3 Connect Optimization to SOP Export

Reason:

The scientific goal of optimization is an executable experimental method.

Likely files:

- `src/dpsim/visualization/tabs/tab_optimization.py`
- M3 SOP export utilities
- `src/dpsim/visualization/tabs/tab_m3.py`

Implementation steps:

1. Allow a selected optimizer candidate to populate a pending `ProcessRecipe`.
2. Mark it as pending until the user accepts it.
3. Route to M3 feasibility and SOP export.
4. Preserve provenance as `optimizer_candidate`.

Acceptance criteria:

- A user can go from optimizer result to M3 feasibility check.
- SOP export includes candidate provenance and evidence tier.
- The original recipe is not overwritten without an explicit action.

## Phase 4 - Maintainability Refactor

Estimated effort: 3 to 6 weeks, can run incrementally  
Primary goal: reduce the cost and risk of future UI work.

### 4.1 Split M3 First

Reason:

M3 is scientifically central and has the highest panel-density risk.

Approach:

1. Extract pure display components first.
2. Avoid changing simulation logic.
3. Preserve existing session-state keys.
4. Add tests after each extraction.

Proposed modules:

```text
src/dpsim/visualization/tabs/m3/
  __init__.py
  setup_panel.py
  feasibility_panel.py
  run_controls.py
  decision_summary.py
  diagnostics_panel.py
  export_panel.py
  view_models.py
```

Acceptance criteria:

- `tab_m3.py` becomes an orchestration layer rather than a large all-in-one file.
- No behavior changes are introduced by extraction.
- Existing M3 tests pass after each slice.

### 4.2 Introduce Typed View Models

Reason:

Large Streamlit functions become fragile when they directly read and mutate session state.

Candidate view models:

```python
@dataclass(frozen=True)
class M3SetupView:
    column_diameter_cm: float
    bed_height_cm: float
    flow_rate_ml_min: float
    residence_time_min: float
    mobile_phase_summary: str

@dataclass(frozen=True)
class DecisionSummaryView:
    dbc10: object
    recovery: object
    pressure: object
    evidence_tier: str
    render_mode: str
    provenance: object
```

Implementation notes:

- Keep view models close to the UI layer.
- Do not leak Streamlit session state into lower scientific modules.
- Use adapters around existing results rather than rewriting core results.

Acceptance criteria:

- Component tests can instantiate view models without Streamlit.
- Result cards can be tested as pure formatting decisions.

### 4.3 Split M1 and M2 After M3 Pattern Is Proven

Reason:

M1 and M2 are also large but less immediately operator-critical than M3.

Target extraction:

- M1 required descriptors.
- M1 fabrication controls.
- M1 derived properties.
- M2 chemistry controls.
- M2 evidence summary.
- M2 downstream impact summary.

Acceptance criteria:

- Stage files become easier to review.
- Stage-specific tests remain focused.
- No unrelated scientific behavior changes occur.

## Phase 5 - Accessibility and Lab Readiness

Estimated effort: 1 to 2 weeks  
Primary goal: make the UI more robust in real scientific computing environments.

### 5.1 Add Local Font Fallback

Reason:

Locked-down lab machines may block external font loading.

Likely files:

- `src/dpsim/visualization/design/tokens.css`

Implementation steps:

1. Keep current typography if available.
2. Add robust local fallback stack.
3. Avoid layout shifts if the external font fails.

Acceptance criteria:

- UI remains readable without network access to font providers.
- No major metric/card layout changes occur when fallback fonts render.

### 5.2 Review Contrast and Small Text

Reason:

Scientific dashboards often rely on dense secondary text. This can harm usability in labs and on projectors.

Likely files:

- `src/dpsim/visualization/design/tokens.css`
- Reusable components under `src/dpsim/visualization/components`

Implementation steps:

1. Identify text below 12 px.
2. Check dark and light theme contrast.
3. Increase critical labels where needed.
4. Keep compact density for secondary metadata only.

Acceptance criteria:

- Critical controls and result labels are readable at laptop resolution.
- Secondary text does not carry critical decision information alone.

### 5.3 Strengthen Accessible Labels

Reason:

Icon-heavy scientific tools need explicit labels for screen readers, keyboard users, and non-primary users.

Implementation steps:

1. Audit icon-only buttons.
2. Add tooltips and accessible text labels.
3. Ensure disabled controls explain why they are disabled.
4. Preserve keyboard reachability.

Acceptance criteria:

- Important commands are not icon-only without an accessible label.
- Disabled run actions include scientific blockers.

## Implementation Backlog

| Task ID | Priority | Area | Main files | Acceptance criteria |
|---|---|---|---|---|
| UI-001 | P0 | Browser visual tests | `tests/visualization/` | Viewport smoke tests pass for main shell and M3. |
| UI-002 | P0 | Streamlit upgrade checklist | `docs/ui_evolution.md`, dependency files | Version and upgrade QA process documented. |
| UI-003 | P0 | Result provenance contract | `ui_workflow.py`, `autowire.py`, `rail.py` | Major results show source and stale state. |
| UI-004 | P1 | Scientific Mode preflight | `stage_panels.py`, new component | Run stage explains mode consequences. |
| UI-005 | P1 | Result source badges | `rail.py`, `tab_m3.py` | Lifecycle/direct/baseline/stale badges visible. |
| UI-006 | P1 | What changed since last run | `rail.py`, `ui_recipe.py` | Pending edits grouped by lifecycle stage. |
| UI-007 | P1 | Inverse inference template | `inverse_inference.py` | Default data path satisfies row-count requirement. |
| UI-008 | P1 | Responsive rail | `tokens.css`, `rail.py`, `shell.py` | No overlap at supported viewports. |
| UI-009 | P1 | Compact top bar | `shell.py`, `tokens.css` | Critical controls remain visible under constrained width. |
| UI-010 | P1 | M3 operator flow | `tab_m3.py`, `tabs/m3/*` | M3 reads setup -> feasibility -> run -> decision -> diagnostics -> export. |
| UI-011 | P2 | Calibration IA cleanup | `tab_calibration.py`, `stage_panels.py` | Calibration vs inverse design is clearly labeled. |
| UI-012 | P2 | Optimizer physical recipe cards | `tab_optimization.py` | Top candidates are readable as bench methods. |
| UI-013 | P2 | Optimizer actionability gates | `tab_optimization.py` | Candidate ranking explains non-actionable states. |
| UI-014 | P2 | Optimizer to SOP route | `tab_optimization.py`, `tab_m3.py` | Candidate can populate pending recipe and route to M3/SOP. |
| UI-015 | P2 | Split M3 module | `tabs/m3/*`, `tab_m3.py` | `tab_m3.py` becomes orchestration-focused. |
| UI-016 | P3 | M1/M2 component extraction | `tabs/m1/*`, `tabs/m2/*` | Large modules reduced without behavior changes. |
| UI-017 | P3 | Local font fallback | `tokens.css` | UI remains stable without external fonts. |
| UI-018 | P3 | Accessibility labels | Components and stage tabs | Icon-only controls have labels/tooltips. |
| UI-019 | P3 | Contrast and small text review | `tokens.css` | Critical scientific labels are readable. |

## Suggested Milestones

| Milestone | Scope | Expected result |
|---|---|---|
| M0 | Visual test harness and provenance contract | Future UI edits are safer. |
| M1 | Mode preflight, stale labels, inverse template | Users understand current scientific state better. |
| M2 | Responsive rail and top bar | App becomes more robust across screens. |
| M3 | M3 operator-flow reorganization | Column-operation workflow becomes clearer. |
| M4 | Optimizer physical recipe cards | Optimization becomes bench-actionable. |
| M5 | M3 refactor and component extraction | UI becomes easier to maintain. |
| M6 | Accessibility and lab-readiness polish | UI is more reliable in real scientific environments. |

## Test Strategy

### Existing Tests To Keep Running

```powershell
.venv\Scripts\python -m pytest -q tests/visualization tests/test_ui_workflow.py tests/test_ui_contract.py tests/test_ui_chrome_smoke.py tests/test_ui_recipe.py tests/test_v0_3_2_g5_ui_dossier.py
```

### New Test Classes

Browser viewport tests:

- App shell loads.
- Top bar does not overlap.
- Run rail is present or intentionally collapsed.
- M3 operator flow renders.
- Calibration stage renders.

State provenance tests:

- Lifecycle result provenance is recorded.
- Direct M3 result provenance is recorded.
- Recipe edits mark older result stale.
- Run rail displays stale reason.

Scientific Mode tests:

- Preflight summary changes by mode.
- Mechanistic mode shows stricter calibration implications.
- Empirical mode does not overstate evidence.

Optimizer tests:

- Physical recipe card renders required fields.
- Non-actionable candidate explains why.
- Candidate-to-M3 handoff preserves provenance.

Accessibility checks:

- Icon-only controls expose labels.
- Disabled run buttons expose blocker text.
- Critical result labels are text-readable.

## Release Strategy

Recommended release grouping:

### Patch Release

Safe to include:

- Documentation.
- Test harness.
- Minor labels.
- Inverse inference template.
- Result badges if low-risk.

### Minor Release

Best for:

- Responsive shell behavior.
- M3 layout reorganization.
- Optimizer physical recipe cards.
- Calibration IA changes.

### Major or Pre-1.0 Feature Release

Consider for:

- Adding a new dedicated Design/Optimization stage.
- Large navigation changes.
- Significant component extraction if user-facing layout changes materially.

## Risk Management

| Risk | Mitigation |
|---|---|
| UI refactor changes scientific behavior. | Extract display components first; keep simulation calls untouched. |
| Streamlit CSS changes break layout. | Add browser screenshot tests and upgrade checklist. |
| Provenance labels confuse users. | Use short labels with tooltips and consistent badge language. |
| Optimizer physical recipes oversimplify uncertainty. | Preserve decision-grade rendering and evidence annotations. |
| Responsive rail hides critical controls. | Keep run/stop controls reachable in every viewport mode. |
| Component extraction breaks session state. | Preserve existing session-state keys and add adapter tests. |

## Implementation Order

Recommended order:

1. Add visual test harness.
2. Add result provenance contract.
3. Add source and stale badges to run rail and M3.
4. Add Scientific Mode preflight.
5. Improve inverse inference default template.
6. Make rail responsive.
7. Compact top bar behavior.
8. Reorganize M3 operator flow.
9. Add optimizer physical recipe cards.
10. Add optimizer actionability gates and SOP handoff.
11. Extract M3 components.
12. Extract M1/M2 components.
13. Add accessibility and lab-readiness polish.

This order reduces risk because it creates test coverage and state clarity before larger layout and refactor work begins.

## Final Target State

After implementation, the UI should feel like a disciplined scientific process-development console:

- The user sees the lifecycle context immediately.
- The active scientific mode and evidence tier are always understandable.
- Results clearly state their source and freshness.
- M3 operation follows a column-method decision flow.
- Optimization returns physical methods rather than only model coordinates.
- Calibration tells the user how to improve confidence.
- The rail and top bar remain stable across supported displays.
- Large UI modules are decomposed enough for safe future development.

The optimized UI should preserve the simulator's strongest scientific qualities while making day-to-day expert use faster, clearer, and less error-prone.

## Completion Status - 2026-05-11

The full optimization cycle described by this plan has been implemented for the
current Streamlit architecture. Larger framework replacement, GMP batch-record
behavior, live instrument control, and a full page-by-page M3 rewrite remain
outside the stated non-goals.

Implemented:

- Result provenance contract with recipe fingerprinting and stale-state detection.
- Provenance display in the run rail and M3 result subtabs.
- Direct M3 result provenance storage for breakthrough, Protein A method, gradient elution, and catalysis outputs.
- Grouped "what changed since last run" edit summary in the run rail.
- Scientific Mode preflight panel on the Run stage.
- Inverse-inference measurement template expanded to the minimum fit-ready 8 rows, with sufficiency feedback.
- Responsive rail/top-bar CSS hardening for 1180 px, 960 px, and 720 px breakpoints.
- Local font fallback and removal of negative heading letter spacing.
- Calibration tab labels clarified to distinguish uncertainty MC, inverse calibration, series design, and wet-lab calibration.
- Optimizer physical recipe cards with pressure, evidence tier, actionability gaps, and bench-readable settings.
- Actionable-only optimizer filter.
- Optimizer candidate Markdown export.
- Optimizer candidate staging for method review.
- Optimizer-to-M1 recipe application for the physical M1 settings.
- Optimizer-to-M3 method-review handoff for feasibility and SOP/export review.
- M3 display of staged optimizer candidates.
- M3 operator-flow strip for setup, feasibility, run, decision, diagnostics, and SOP/export state.
- M1 and M2 operator-flow strips.
- Shared operator-flow component extraction.
- M3 result-provenance component extraction.
- Optional browser viewport and representative stage-route smoke-test harness gated behind `DPSIM_RUN_BROWSER_TESTS=1`.
- Streamlit support and upgrade checklist in `docs/ui_evolution.md`, verified against Streamlit 1.57.0.
- Accessibility hardening for icon-only baseline deletion and disabled/blocked scientific states.
- SOP/protocol export now includes simulation-use constraints and result provenance.

Backlog closure:

| Task ID | Status | Completion note |
|---|---|---|
| UI-001 | Complete | Browser smoke covers 1440, 1280, 1024, and 390 px viewports plus Target, M3, Run, Validation, and Calibration stage routes. |
| UI-002 | Complete | Streamlit upgrade checklist added to `docs/ui_evolution.md`; local verification captured for Streamlit 1.57.0. |
| UI-003 | Complete | `ResultProvenance` contract added with recipe fingerprint and stale-state helpers. |
| UI-004 | Complete | Scientific Mode preflight rendered before lifecycle execution. |
| UI-005 | Complete | Lifecycle/direct/stale provenance labels rendered near major M3 and rail outputs. |
| UI-006 | Complete | Pending edits grouped by lifecycle stage in the run rail. |
| UI-007 | Complete | Inverse inference opens with a fit-ready 8-row template and readiness status. |
| UI-008 | Complete | Rail width, wrapping, and responsive behavior covered by CSS and browser smoke. |
| UI-009 | Complete | Top chrome remains usable under the supported viewport smoke set. |
| UI-010 | Complete | M3 now presents the operator decision flow before dense method panels. |
| UI-011 | Complete | Calibration IA labels distinguish calibration from design/series work. |
| UI-012 | Complete | Optimizer results render physical recipe cards before raw search-space coordinates. |
| UI-013 | Complete | Candidate ranking reports actionability gaps and supports actionable-only filtering. |
| UI-014 | Complete | Candidates can be staged, applied to M1 recipe settings, and routed to M3 review/SOP surfaces. |
| UI-015 | Complete for this cycle | M3 result provenance, operator flow, and method-condition responsibilities are split out; a total M3 rewrite remains a future major refactor, not required for this optimization cycle. |
| UI-016 | Complete for this cycle | M1/M2 operator-flow components extracted without changing solver behavior. |
| UI-017 | Complete | Local font fallback added to design tokens. |
| UI-018 | Complete | Icon-only baseline deletion has a tooltip; scientific blockers remain text-readable. |
| UI-019 | Complete | Critical text and layout checks are covered by CSS contract tests and browser smoke. |

Verification completed:

```powershell
.venv\Scripts\python -m pytest -q tests/visualization tests/test_ui_workflow.py tests/test_ui_contract.py tests/test_ui_chrome_smoke.py tests/test_ui_recipe.py tests/test_v0_3_2_g5_ui_dossier.py tests/test_optimization_claim_reporting.py tests/test_optimization_optional_dependency.py tests/test_optimization.py
```

Result:

```text
309 passed, 8 skipped in 6.70s
```

Optional browser verification:

```powershell
$env:DPSIM_RUN_BROWSER_TESTS='1'; $env:PYTHONIOENCODING='utf-8'; .venv\Scripts\python -m pytest -q tests/visualization/test_viewport_smoke.py
```

Result:

```text
5 passed in 34.41s
```

Additional checks:

```powershell
.venv\Scripts\python -m compileall -q src\dpsim\visualization src\dpsim\optimization
```

Streamlit health boot:

```text
http://127.0.0.1:8508/_stcore/health -> 200 ok
```
