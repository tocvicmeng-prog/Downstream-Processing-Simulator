# P6+ UI And Scientific Polish Handover

## Scope

This pass extends the P6 lifecycle-first Streamlit UI without changing the numerical M1/M2/M3 kernels. The goal is to make the interface behave more like a downstream-process development workstation: recipe context, full lifecycle execution, evidence review, wet-lab SOP export, calibration comparison, and run history are visible in one workflow.

## Implemented

- Added lifecycle stage context panels before the reused M1/M2/M3 controls.
- Added run-history storage for recent full lifecycle simulations.
- Added scientific diagnostics extracted from the lifecycle result graph.
- Added measured-vs-simulated calibration comparison rows for common M1/M2/M3 assay types.
- Added visual comparison panels for M1 DSD, DSD representative transfer, M3 breakthrough/elution traces, method pressure/compression, ligand/capacity metrics, and calibration overlay-ready measured/simulated pairs.
- Upgraded the protocol export from a simple outline toward a wet-lab SOP draft with target profile, materials, equipment, acceptance criteria, required records, per-stage hold/release gates, and result-graph caveats.
- Expanded validation/evidence results into dedicated tabs for summary, validation, evidence ladder, scientific diagnostics, SOP export, calibration comparison, and run history.

## Important Files

- `src/dpsim/visualization/app.py`
  Main Streamlit entrypoint. P6+ wires stage context panels into the lifecycle tabs.

- `src/dpsim/visualization/ui_workflow.py`
  Pure UI workflow helpers and Streamlit panels. Keep new scientific UI behavior here when possible.

- `tests/test_ui_workflow.py`
  Unit tests for workflow state, target profile sync, protocol/SOP export, diagnostics, calibration comparison, and run-history helpers.

## Calibration Comparison Coverage

Mapped comparisons currently include:

- M1 DSD: d10, d32, d50, d90 where graph diagnostics expose them.
- M1 physical/wash QC: pore size, residual oil, residual surfactant.
- M2 chemistry assays: functional ligand density, activity retention, ligand leaching, free protein in wash, estimated qmax.
- M3 performance assays: DBC10, qmax, pressure drop, pressure-flow proxy where a direct simulated metric exists.

Entries with no direct simulated metric are still displayed as provenance/QC evidence and flagged as not mapped. This is deliberate: unknown assay types should not be silently interpreted.

## Remaining UI Debt

- The embedded M1/M2/M3 panels still contain legacy headings and some module-local assumptions. A later pass should split their forms into smaller recipe-native components that can be composed directly by the lifecycle page.
- Calibration overlays currently compare scalar assay entries. Full measured breakthrough curves, pressure-flow curves, DSD histograms, ligand-density assay curves, and posterior uncertainty bands should be added when uploaded calibration files preserve structured curve payloads rather than only fitted `CalibrationEntry` scalars.
- SOP export is Markdown only. A regulated-workflow version should emit a controlled batch-record template with signature lines, deviation fields, and explicit assay acceptance tables.
- Streamlit browser QA should be automated once a persistent local server strategy is chosen for this Windows environment.

## Scientific Guardrails

- UI comparisons are screening diagnostics, not calibration fitting.
- Agreement bands are intentionally conservative: within 5 percent is supporting evidence, 5 to 20 percent is model-data tension, above 20 percent blocks decision-grade interpretation until recalibrated.
- Evidence tier inheritance remains enforced by backend lifecycle validation; UI wording should not imply stronger evidence than the weakest M2/M3 media contract.
