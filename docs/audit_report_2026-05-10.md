# Downstream Processing Simulator Audit Report

**Date:** 2026-05-10  
**Repository:** `C:\Users\tocvi\OneDrive\文档\Project_Code\EmulSim\Downstream_Processing_Simulator`  
**Inspected branch:** `main`  
**Inspected head:** `815f11c fix(ui): collapse Scientific Mode tooltip to single line`  
**Auditor stance:** downstream-processing practitioner, wet-lab operator, physicochemical reviewer, and computational-simulation scientist.  

## Executive Verdict

DPSim is a serious and unusually broad research-grade screening platform. Its strongest architectural choice is the explicit M1 -> M2 -> M3 lifecycle: fabrication state, functional-media contract, chromatography performance, evidence tiers, wet-lab caveats, calibration hooks, and process dossiers are all represented as first-class concepts. The simulator is already useful for screening, teaching, parameter-space narrowing, and identifying physically impossible recipes before bench work.

It is not yet adequate as a real laboratory decision engine without further hardening. The main issue is not lack of code volume; it is claim discipline and operational completeness. Many numerical paths are mechanistically plausible but uncalibrated, some UI/report paths still do not universally enforce decision-grade rendering, several advertised wet-lab capabilities depend on optional or absent dependencies, and the active support documentation is not fully synchronized with the v0.8.9 codebase.

The current development plan is scientifically valid in direction. It correctly prioritizes calibration, pressure-envelope honesty, mobile-phase/isotherm wiring, UI exposure, SOP export, run comparison, and evidence tiers. However, the plan overstates closure in a few areas. In particular, "wet-lab credible" should be treated as "wet-lab planning credible", not "wet-lab decision validated", until real calibration datasets exist for DSD, pore morphology, ligand density/activity, residuals, pressure-flow, and breakthrough.

## Audit Method

Reviewed:

- top-level documentation: `README.md`, `CHANGELOG.md`, `DESIGN.md`, `docs/current_support_matrix.md`, `docs/DPS_CLEAN_SLATE_ARCHITECTURE.md`, `docs/02_computational_architecture.md`, `docs/03_architecture_modification_plan.md`, and `docs/update_workplan_2026-05-10_v0_9_0.md`;
- lifecycle and contracts: `src/dpsim/lifecycle/orchestrator.py`, `src/dpsim/core/process_recipe.py`, `src/dpsim/core/recipe_validation.py`, `src/dpsim/core/result_graph.py`, `src/dpsim/datatypes.py`;
- M1 physics: emulsification, gelation, wash residual, crosslinking, mechanics, DSD propagation, CFD/PBE coupling;
- M2 chemistry: ACS state tracking, reagent profiles, compatibility matrix, functional-media contract, calibration application;
- M3 operation: hydrodynamics, pressure envelope, isotherm adapters, LRM breakthrough, Protein A method model, gradient/elution plumbing, monitoring and pressure feasibility;
- calibration/dossier/UI: calibration schemas, wet-lab ingestion, spreadsheet import, SOP/session/run-comparison panels, tier rendering, widget mounting gates;
- tests and runtime environment.

Verification performed:

- `.\.venv\Scripts\python --version` -> Python 3.12.10.
- Targeted audit suite:

```text
.\.venv\Scripts\python -m pytest -q tests\test_smoke.py tests\test_process_dossier.py tests\test_model_mode_guard.py tests\test_pressure_feasibility.py tests\visualization\test_widget_mounting.py tests\visualization\test_tier_routing_gate.py tests\test_wetlab_ingestion.py
69 passed in 3.98 s
```

- Full suite attempt:

```text
.\.venv\Scripts\python -m pytest -q
collected 3042 items / 2 errors / 1 skipped
ERROR tests/test_f4b_cvar.py: ModuleNotFoundError: No module named 'torch'
ERROR tests/test_inverse_design_engine.py: ModuleNotFoundError: No module named 'torch'
```

- Full non-optimization attempt excluding those two files timed out after 5 minutes, so it is not recorded as pass or fail.

## Fundamental Practitioner Requirements

A downstream-processing practitioner would expect the simulator to support these basic laboratory decisions:

1. Select a polymer/resin family that is chemically compatible with the intended target, buffer, ligand, and column operation.
2. Convert a bench recipe into executable operations: phase preparation, emulsification, gelation, crosslinking, washing, activation, coupling, quench, packing, equilibration, load, wash, elution, regeneration, and assays.
3. Predict whether the bead population is physically packable: DSD, fines/tails, swelling, porosity, compressibility, pressure-flow, bed compression, frit contribution, and pump limit.
4. Predict whether the functionalization chemistry is plausible: reactive-site inventory, pH/time/temperature windows, hydrolysis/side reactions, ligand density, retained activity, free ligand/protein, residual reagents, and wash closure.
5. Predict chromatography behavior within calibrated limits: selected isotherm, mobile phase, residence time, DBC, breakthrough shape, elution recovery, impurity clearance, pressure profile, and lifetime.
6. Tell the user what not to trust: evidence tier, uncertainty, valid domain, calibration source, missing assays, and downgrade reason.
7. Generate bench-usable artifacts: recipe, SOP, calibration import, run comparison, predicted-vs-measured overlays, and process dossier.

DPSim covers the skeleton of this workflow, but quantitative trust depends on wet-lab calibration that is mostly absent from the repository data layer.

## Current Strengths

| Area | Assessment |
|---|---|
| Lifecycle architecture | Strong. `DownstreamProcessOrchestrator` sequences M1 -> M2 -> M3 and stores handoffs in `ResultGraph`. |
| Evidence-tier philosophy | Strong. `ModelEvidenceTier`, `ModelManifest`, `ResultGraph`, and `core/decision_grade.py` express the correct scientific posture. |
| M3 pressure-envelope correction | Strong and scientifically important. The shift from bursting-modulus ceiling to bed-compression runaway is necessary for soft hydrogel media. |
| Recipe guardrails | Good. G1/G3/G4/G5/G6/G7/G8 cover several real wet-lab failure modes. |
| DSD propagation | Improved. `representative`, `adaptive`, and `bin_resolved` modes exist, with tests. |
| M2 chemistry governance | Good for screening. ACS tracking, sequence FSM, family/reagent compatibility, pH windows, and residual warnings are valuable. |
| UI wiring regression gates | Good. Widget-mounting and tier-routing AST tests prevent two prior classes of UI drift. |
| Calibration schema | Good foundation. `CalibrationEntry`, `AssayRecord`, wet-lab YAML ingestion, and spreadsheet import exist. |
| Test surface | Broad. 3000+ tests are collected, with focused tests around core scientific guardrails. |

## Major Findings

### F-001: Support documentation is not synchronized with the current release

**Severity:** High for user trust  
**Evidence:** `pyproject.toml` and `src/dpsim/__init__.py` report v0.8.9; `README.md` badge still says v0.8.3; `docs/current_support_matrix.md` is labelled v0.6.5 and still talks about v0.6.x defaults.  

**Why it matters:** A wet-lab user needs one authoritative answer to "what is live, what is scaffolded, and what is only planned?" Documentation drift is dangerous in scientific software because old claims may be safer or riskier than the current code.

**Required modification:** Promote `docs/current_support_matrix.md` to v0.8.9, reconcile it with `CHANGELOG.md`, and explicitly mark each feature as `live`, `screening`, `requires calibration`, `scaffolded`, `deferred`, or `out of scope`.

### F-002: Full test suite is not reproducible from the declared base/dev install

**Severity:** High operational risk  
**Evidence:** Full pytest collection fails because `src/dpsim/optimization/engine.py` imports `torch`, `botorch`, and `gpytorch` at module import time, while the active venv lacks the optional optimization stack.  

**Why it matters:** Optional scientific modules should not break default test collection. A practitioner or reviewer cannot distinguish "core simulator broken" from "optional BO extra missing".

**Required modification:** Gate optimization tests with `pytest.importorskip("torch")` or move heavy imports inside `OptimizationEngine` execution paths with a clear `OptimizationExtraNotInstalledError`. Add CI jobs for base, UI, dev, and optimization extras separately.

### F-003: The top-level tier banner is mounted but appears to read the wrong lifecycle attributes

**Severity:** Medium to high UI trust risk  
**Evidence:** `src/dpsim/visualization/app.py` derives banner tier from lifecycle attributes `m1_result`, `m2_result`, and `m3_result`; `DownstreamLifecycleResult` actually exposes `m1_result`, `m2_microsphere`, `functional_media_contract`, `m3_method`, and `m3_breakthrough`. Other UI code correctly uses `lifecycle_result.weakest_evidence_tier` or session keys.  

**Why it matters:** The banner is supposed to be the persistent "read this before any number" control. If it silently falls back to `None`, the dashboard looks safer than the evidence chain justifies.

**Required modification:** In `app.py`, use `lifecycle_result.weakest_evidence_tier` directly, or walk `lifecycle_result.graph.model_manifests()`. Add a test that constructs a `DownstreamLifecycleResult` with weak M2/M3 tiers and asserts the banner receives that weakest tier.

### F-004: Decision-grade rendering is not universal

**Severity:** Medium  
**Evidence:** `tests/visualization/test_tier_routing_gate.py` allows a baseline of 43 bare `.metric(` call sites. The gate prevents new drift but does not prove all existing decision-bearing numbers route through `render_metric` or `render_decision_grade_annotation`.  

**Why it matters:** The simulator's most important safety mechanism is display discipline. Internal numeric values are acceptable; user-facing quantitative claims must be tier-gated.

**Required modification:** Reduce the bare metric baseline to zero or maintain an explicit allowlist with a reason for each exempt non-decision display.

### F-005: "Wet-lab credible" is overstated without calibration datasets

**Severity:** High scientific communication risk  
**Evidence:** `CHANGELOG.md` frames v0.8.8/v0.8.9 as wet-lab credible and mature as scoped. `data/validation/README.md` still states that assay directories contain 0 assays and 0 fits for major calibration areas.  

**Why it matters:** A simulator can be wet-lab useful before it is quantitatively wet-lab credible. The current data layer supports calibration, but the calibration evidence is not present.

**Required modification:** Use stricter language: "wet-lab planning credible with explicit evidence tiers." Reserve "validated" or "decision-grade" for specific outputs with actual assay records and holdout validation.

### F-006: M1 family support remains uneven despite broad UI exposure

**Severity:** Medium scientific risk  
**Evidence:** Multiple L2 family modules remain analogy-based, qualitative, unsupported, or raise `NotImplementedError` for route combinations. Several L4 paths still use agarose-chitosan-like placeholders for broader families.  

**Why it matters:** Different polymer families have different gelation mechanisms, swelling, pH/salt stability, pore structure, and compressibility. A user selecting alginate, cellulose, PLGA, pectin, gellan, starch, chitin, or composites should see a conspicuous route-specific evidence limit.

**Required modification:** Add a family maturity table to the UI and support matrix. For every family, expose: enabled state, route, valid domain, analogy source, calibration data required, pressure-envelope validity, and M3 claim ceiling.

### F-007: M2 chemistry is useful but not yet release-grade

**Severity:** Medium to high scientific risk  
**Evidence:** `FunctionalMediaContract` carries ligand density, activity retention, leaching, free-protein wash fraction, residuals, and model manifest. However, most reagent values are profile defaults or semi-quantitative estimates, and ligand density/activity claims require assays.  

**Why it matters:** In real functional media development, ligand density alone is insufficient. Active ligand, orientation, steric accessibility, hydrolysis, nonspecific adsorption, residual activation chemistry, and leachables drive performance and safety.

**Required additions:** Add or strengthen target-specific assay requirements for ligand density, retained activity, free ligand/protein wash, residual reagent, leaching after storage/CIP, and static binding. Treat missing assays as hard tier ceilings for DBC, recovery, and cycle-life.

### F-008: M3 isotherm selection is structurally good, but several defaults are placeholders

**Severity:** High for quantitative M3 use  
**Evidence:** `select_isotherm_from_fmc` routes by `binding_model_hint`; HIC explicitly marks `K_0` and `m_salt` as placeholders requiring calibration; Protein A uses smooth pH-dependent Langmuir defaults; generic fallback uses Langmuir defaults.  

**Why it matters:** Isotherm choice is one of the dominant determinants of breakthrough and elution. Wrong isotherm constants can produce very smooth but physically misleading curves.

**Required modification:** For each isotherm class, require calibration status and valid-domain checks before reporting DBC/recovery as numbers. Uncalibrated HIC, IMAC, Protein A, IEX, and competitive systems should render as rank/interval screens only.

### F-009: Pressure envelope is one of the strongest parts, but needs experimental anchoring

**Severity:** Medium  
**Evidence:** `compute_pressure_envelope` implements family `K_geom`, mobile-phase viscosity, frit contribution, iterated Kozeny-Carman compression, operational vs structural ceilings, and tier rollup. The default `K_geom` values remain literature/family defaults unless calibrated.  

**Why it matters:** This model can prevent column damage, but only if the material stiffness, packed-bed porosity, particle diameter, frit state, viscosity, and family `K_geom` reflect the actual packed bed.

**Required additions:** Add pressure-flow calibration import as a first-run workflow, not an advanced calibration path. Require at least 3 to 5 measured pressure-flow points before promoting pressure headroom beyond screening for a given family/column/mobile phase.

### F-010: Wet-lab operation model is still incomplete for real bench execution

**Severity:** Medium  
**Missing functions from practitioner perspective:**

- reagent preparation and stability timer tracking;
- equilibration endpoint criteria, not just fixed durations;
- packed-bed quality checks: asymmetry, HETP/tracer, wall effects, bed settling, compression preconditioning;
- harvest/wash fraction accounting with sample IDs;
- cleaning/sanitization/CIP sequence and ligand loss by cycle;
- lot tracking for polymer, ligand, target protein, buffers, column hardware, frits, and detector;
- explicit safety/hazard flags for cyanogen bromide, epichlorohydrin, aldehydes, organic solvents, and low-pH protein handling;
- instrument method export/import for AKTA-like systems;
- raw detector trace ingestion for UV/conductivity/pH/pressure with baseline correction;
- assay result validation rules: replicate count, CV threshold, LOD/LOQ, outlier policy.

**Required addition:** Treat wet-lab operations as an executable protocol state machine with QC checkpoints, not only as solver inputs.

### F-011: Spreadsheet calibration import is useful but dependency handling is incomplete

**Severity:** Medium usability risk  
**Evidence:** The venv has `pandas` but lacks `openpyxl`; the code reports a clear XLSX error, but `openpyxl` is not declared in any optional extra.  

**Why it matters:** Wet-lab users commonly have `.xlsx` exports. A feature marketed as spreadsheet import should have installable dependencies documented and test-covered.

**Required modification:** Add a `calibration-io` or `spreadsheet` extra with `pandas` and `openpyxl`, and test CSV and XLSX paths separately.

### F-012: Process dossier exists, but the dossier is not yet a complete laboratory audit record

**Severity:** Medium  
**Evidence:** `ProcessDossier` exports environment, result summaries, calibration entries, assay records, target profile, and optional MC bands. It summarizes M1 strongly but does not yet fully serialize M2/M3 curves, raw calibration traces, UI choices, SOP text, or all result graph nodes as the authoritative lab record.  

**Required additions:** Make dossier export include the `ResultGraph` summary, M2 functional media contract, pressure envelope, selected mobile phase, isotherm spec, M3 method steps, SOP Markdown, calibration-store hash, and run-history comparison snapshot.

### F-013: Current "responding model" role is correct but must stay non-authoritative

**Interpretation:** The current responding model is the software's decision/response layer: model manifests, evidence tiers, decision-grade rendering, result graph, validation report, and UI/SOP explanations that translate solver output into user-facing claims.

**Assessment:** Its intended function is scientifically sound. It should not alter solver outputs; it should govern what a user is allowed to believe from those outputs. That is the right architecture for a simulator that mixes mechanistic, empirical, analogy, and calibrated modules.

**Concern:** Some response surfaces still bypass or partially bypass the policy layer. The response model must become the mandatory final gate for every number shown in the UI, SOP, dossier, plots, calibration comparison, and optimization output.

**Required modification:** Establish a single `DecisionClaim` object for display/export, containing `value`, `unit`, `output_type`, `evidence_tier`, `render_mode`, `valid_domain_status`, `calibration_ref`, `uncertainty`, `assay_required`, and `claim_allowed`.

## Component-Level Assessment

| Component | Current state | Required modification |
|---|---|---|
| M1 emulsification | PBE + DSD support; CFD/PBE path exists. | Add bench DSD calibration sets; make sub-Kolmogorov/high-viscosity regime warnings unavoidable in UI. |
| M1 gelation/pore | Broad family coverage with mixed fidelity. | Surface family-specific maturity and require pore/porosity assays for quantitative downstream use. |
| M1 mechanics | Provides modulus/compression descriptors. | Require buffer-state compression calibration for pressure-envelope promotion. |
| M1 washing | Good conceptual model and residual fields. | Add validated residual oil/surfactant/reagent assays and LOD/LOQ gates. |
| M2 ACS chemistry | Strong state-machine foundation. | Add reaction-transport limits, steric accessibility, reagent degradation, and stronger assay gating. |
| M2 functional media contract | Good bridge to M3. | Treat active ligand, leaching, free protein, and assay provenance as mandatory for numeric M3 claims. |
| M3 hydrodynamics | Scientifically strong pressure-envelope rewrite. | Calibrate family `K_geom` and bed porosity under real packing protocols. |
| M3 isotherms/LRM | Useful screening engine. | Require target-specific isotherm/breakthrough data before quantitative DBC/recovery. |
| M3 method simulation | Represents pack/equilibrate/load/wash/elute. | Add regenerate/CIP state, repeated cycles, fraction collection, and instrument-trace comparison. |
| Calibration | Good schemas and ingestion hooks. | Add real datasets, fitter outputs, replicate quality rules, and optional dependency extras. |
| UI | Much improved; widgets mounted and tested. | Fix tier-banner tier extraction, reduce bare metrics, finish `tab_m3.py` decomposition. |
| Optimization | Conceptually valuable but optional dependencies break full collection. | Lazy import/gate optional stack; never let BO run on unsupported evidence tiers by default. |
| Documentation | Rich but fragmented and version-drifted. | Make support matrix current and authoritative. Archive historical docs more visibly. |

## Development Plan Validity

The v0.8.6 -> v0.8.9 plan is valid in sequence:

1. Restore honesty: visible inputs must drive the simulation.
2. Expose existing backend capabilities.
3. Enforce decision-grade display policy.
4. Move pressure envelope before run.
5. Add calibration import, SOP export, session save/load, run comparison, and first-run examples.
6. Keep durable deferrals explicit: live AKTA UNICORN, MCMC inverse, cyclic SMB/multi-bed physics.

The plan is scientifically incomplete only if it is interpreted as validation. It is a good software maturation plan; it is not a substitute for a calibration campaign.

The next plan should be evidence-led:

- Study A: DSD vs RPM/viscosity/surfactant, with microscopy or laser diffraction.
- Study B: pore/porosity/swelling/mechanics vs formulation and gelation route.
- Study C: ligand density/activity/leaching/free-protein/residual reagent assays.
- Study D: pressure-flow curves for packed media across bead family, bed height, viscosity, and flow.
- Study E: static binding and dynamic breakthrough for target proteins and selected mobile phases.
- Study F: cycling/CIP stability and recovery degradation.

Only after these datasets exist should any module be promoted to `CALIBRATED_LOCAL` or `VALIDATED_QUANTITATIVE` for operational decisions.

## Architectural Reliability

The architecture is fundamentally reliable for a research simulator because it has typed contracts, a lifecycle orchestrator, validation reports, model manifests, evidence rollup, explicit caveats, and tests. The biggest reliability risks are:

1. optional dependencies imported at collection time;
2. display paths that bypass evidence gates;
3. documentation drift;
4. calibration data absence;
5. legacy bare-float solver internals with unit conversion only at selected boundaries;
6. UI state/session keys not always matching lifecycle dataclass fields;
7. broad family/reagent/isotherm menus exceeding the calibration evidence base.

The architecture should not be rewritten. It should be tightened around the existing spine:

```text
ProcessRecipe
  -> ValidationReport
  -> ResolvedParameter + Quantity
  -> M1ExportContract
  -> FunctionalMediaContract
  -> M3 Method/Pressure/Isotherm Results
  -> ResultGraph
  -> DecisionClaim
  -> ProcessDossier/SOP/UI
```

## Prioritized Remediation Plan

### P0: Correct trust and reproducibility blockers

1. Fix top-level tier banner to consume `lifecycle_result.weakest_evidence_tier` or `ResultGraph`.
2. Gate optimization imports/tests behind optional dependency checks.
3. Update README badge and `current_support_matrix.md` to v0.8.9.
4. Add a full-suite CI matrix: base, dev, UI, optimization, spreadsheet.

### P1: Make every user-facing number decision-graded

1. Replace remaining decision-bearing bare `st.metric` call sites.
2. Add `DecisionClaim` as the one export/render object.
3. Apply the same policy to SOP export, dossier JSON, plots, calibration comparison, and optimization outputs.

### P2: Make calibration operational

1. Add `spreadsheet` extra with `pandas` and `openpyxl`.
2. Add import templates for DSD, pore, ligand density, activity, pressure-flow, DBC, residuals, and leaching.
3. Enforce replicate count, CV thresholds, LOD/LOQ, and valid-domain checks.
4. Store calibration-store hashes in dossiers.

### P3: Raise scientific fidelity where it matters most

1. Calibrate pressure-flow and `K_geom` for each media family.
2. Require target-specific isotherm data for DBC/recovery claims.
3. Add active ligand and leaching assays to M2.
4. Add pore/porosity/mechanics calibration to M1.
5. Expand regenerative/cycle-life and CIP models only after data exists.

### P4: Improve operator workflow

1. Make the SOP exporter include QC checkpoints and assay acceptance criteria.
2. Add fraction collection and sample-ID tracking.
3. Add instrument trace import with baseline correction and predicted-vs-measured overlays.
4. Keep live instrument control out of scope until safety and hardware validation are formally designed.

## Final Scientific Assessment

DPSim is credible as a physics-aware screening simulator and wet-lab planning assistant. It is not yet a validated process-development decision system. Its architecture is strong enough to become one, provided the team keeps the central rule strict: solvers may compute numbers freely, but the response layer must only present claims that the evidence tier, valid domain, and calibration data justify.

The immediate engineering work is not to add more scientific breadth. The immediate work is to make the existing breadth harder to misuse.
