# P6 UI Workflow Readiness Review

Date: 2026-04-25

## Review Finding

The scientific/backend foundation is ready for P6: `ProcessRecipe`,
`ValidationReport`, `ResultGraph`, evidence manifests, calibration ingest, and
wet-lab protocol documentation are already present. The gap was UI structure.
The Streamlit app still exposed M1/M2/M3 as isolated legacy tabs with a
`Pipeline Scope` selector, so there was no shared lifecycle-first UI model for:

1. target product profile;
2. M1 fabrication recipe;
3. M2 chemistry recipe;
4. M3 column method;
5. simulation execution;
6. validation/evidence inspection;
7. wet-lab calibration comparison.

## Implemented Readiness Work

- Added `src/dpsim/visualization/ui_workflow.py`.
  - Defines a pure lifecycle workflow state model.
  - Builds validation report rows from backend `ValidationReport`.
  - Builds evidence ladder rows from `DownstreamLifecycleResult.graph` or
    current partial Streamlit session results.
  - Builds calibration status rows from `_cal_store`.
  - Exports a wet-lab protocol outline directly from `ProcessRecipe`.
  - Provides a Streamlit lifecycle overview/review panel.

- Updated `src/dpsim/visualization/app.py`.
  - Renders the lifecycle workflow overview before the legacy tabs.
  - Keeps current tabs operational while establishing the P6 navigation model.

- Updated `src/dpsim/visualization/panels/calibration.py`.
  - Calibration uploads now write temporary JSON files under
    `runtime_temp_dir()` instead of relying on platform temp defaults.

- Added `tests/test_ui_workflow.py`.
  - Covers workflow readiness, validation rows, evidence ladder rows,
    protocol export, and calibration status rows.

## P6 Start Position

P6 can now proceed by replacing the old tab contents step-by-step behind the
new lifecycle workflow surface:

1. Convert the target profile row into an editable target-profile form.
2. Move current M1 controls behind the M1 fabrication recipe step.
3. Move current M2 controls behind the M2 chemistry recipe step.
4. Move current M3 controls behind the M3 column method step.
5. Add a single lifecycle run button that calls `DownstreamProcessOrchestrator`
   with the session `ProcessRecipe`.
6. Promote the `Lifecycle Review` expander into permanent result views for
   validation, evidence, protocol export, and calibration.

## Verification

- Focused UI tests: `97 passed`.
- P6 readiness regression subset: `31 passed`.

## Remaining Risk

- The legacy tabs still own the actual control layout. The new workflow panel
  is a migration scaffold, not the final P6 UI.
- The Streamlit session currently stores partial M1/M2/M3 result keys rather
  than one canonical `lifecycle_result`; P6 should centralize that result.
