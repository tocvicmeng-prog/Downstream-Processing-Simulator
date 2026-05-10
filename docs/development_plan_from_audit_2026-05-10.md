# DPSim Development Plan From Audit

**Date:** 2026-05-10  
**Source audit:** `docs/audit_report_2026-05-10.md`  
**Purpose:** Convert the scientific, wet-lab, and software-architecture audit findings into a staged development plan for the continued evolution of DPSim.  

## 1. Development Objective

DPSim should evolve from a broad research-grade screening simulator into a wet-lab planning and calibration workbench whose claims are impossible to over-read. The next development stages should not prioritize adding more model breadth. They should prioritize:

1. trust correctness;
2. reproducible runtime and tests;
3. universal evidence-gated response/rendering;
4. calibration-data ingestion and assay governance;
5. family-specific scientific validity;
6. laboratory workflow completeness;
7. maintainable architecture around a single lifecycle spine.

The target operating model is:

```text
ProcessRecipe
  -> first-principles validation
  -> resolved parameters and units
  -> M1 fabrication state
  -> M2 functional media state
  -> M3 process-performance state
  -> result graph
  -> decision claims
  -> dossier / SOP / UI / optimization
```

Every stage must preserve the same invariant:

> Solvers may compute numerical estimates, but the response layer may only present claims justified by evidence tier, valid domain, calibration provenance, and uncertainty.

## 2. Release Structure

The work should be split into six staged releases. Each stage has a scientific goal, coding scope, architectural scope, acceptance criteria, and test gates.

| Stage | Theme | Primary outcome |
|---|---|---|
| S0 | Trust and reproducibility repair | The current system is testable, version-consistent, and does not misreport evidence state. |
| S1 | Decision-claim architecture | Every displayed/exported number passes through one claim policy. |
| S2 | Calibration and assay infrastructure | Wet-lab data can be imported, quality-checked, fitted, and used to promote tiers. |
| S3 | Scientific model hardening | M1/M2/M3 model families gain explicit maturity, valid domains, and calibration gates. |
| S4 | Wet-lab workflow execution | SOP, sample tracking, fraction collection, QC checkpoints, and trace comparison become first-class. |
| S5 | Optimization under evidence constraints | BO/inverse design operate only inside trust and calibration boundaries by default. |

## 3. Stage S0: Trust and Reproducibility Repair

### Scientific Rationale

Before adding features, the system must reliably tell the user what can and cannot be trusted. The audit found documentation version drift, full-suite collection failure due to optional optimization dependencies, and a likely top-level tier-banner attribute mismatch.

### Coding Work

1. **Fix tier-banner evidence extraction**
   - File: `src/dpsim/visualization/app.py`
   - Replace manual lookup of `m1_result`, `m2_result`, and `m3_result` with:
     - `lifecycle_result.weakest_evidence_tier`, or
     - `lifecycle_result.graph.weakest_evidence_tier()`.
   - Add a focused test with a synthetic lifecycle result containing a weak M2 or M3 manifest.

2. **Gate optional optimization imports**
   - Files: `src/dpsim/optimization/engine.py`, `tests/test_f4b_cvar.py`, `tests/test_inverse_design_engine.py`
   - Move `torch`, `botorch`, and `gpytorch` imports behind lazy helper functions.
   - Raise a clear `OptimizationExtraNotInstalledError` with install guidance.
   - Mark optimization tests with `pytest.importorskip("torch")` or an `optimization` marker.

3. **Synchronize version and support documentation**
   - Files: `README.md`, `docs/current_support_matrix.md`, `CHANGELOG.md`
   - Update README badge from v0.8.3 to v0.8.9.
   - Rebuild `current_support_matrix.md` as the current v0.8.9 support ledger.
   - Mark historical documents as non-authoritative unless explicitly current.

4. **Define test environment profiles**
   - Update `pyproject.toml` optional extras:
     - `base`
     - `ui`
     - `dev`
     - `optimization`
     - `spreadsheet`
     - `all`
   - Add `openpyxl` to spreadsheet import support.

### Architectural Work

- Create a single support-status vocabulary used in docs and UI:
  - `live`
  - `screening`
  - `requires_calibration`
  - `scaffolded`
  - `deferred`
  - `out_of_scope`
- Add a `FeatureSupportRecord` dataclass or JSON registry that can feed both docs and UI.

### Acceptance Criteria

- Full base/dev test collection does not fail when optimization extras are absent.
- Tier banner reflects the true weakest lifecycle tier.
- README, package version, changelog, and support matrix agree.
- `pytest -q` has either a clean pass for installed extras or clean skips for absent extras.

## 4. Stage S1: Decision-Claim Architecture

### Scientific Rationale

The simulator's safest design principle is that numerical computation and decision presentation are separate. The audit found that decision-grade rendering exists but is not universal, with a remaining baseline of bare `st.metric` call sites.

### Coding Work

1. **Introduce `DecisionClaim`**
   - New file: `src/dpsim/core/decision_claim.py`
   - Fields:
     - `name`
     - `value`
     - `unit`
     - `output_type`
     - `evidence_tier`
     - `render_mode`
     - `valid_domain_status`
     - `uncertainty_interval`
     - `calibration_ref`
     - `assay_required`
     - `claim_allowed`
     - `reason`

2. **Refactor render policy around claims**
   - Existing file: `src/dpsim/core/decision_grade.py`
   - Keep `OutputType`, `RenderMode`, and policy floors.
   - Add `make_decision_claim(...)` as the single entry point for user-facing values.

3. **Replace display call sites**
   - Files:
     - `src/dpsim/visualization/tabs/tab_m1.py`
     - `src/dpsim/visualization/tabs/tab_m2.py`
     - `src/dpsim/visualization/tabs/tab_m3.py`
     - `src/dpsim/visualization/tabs/calibration/*.py`
     - `src/dpsim/visualization/panels/*.py`
   - Replace decision-bearing bare `st.metric` calls with `render_claim` or `render_metric`.
   - Leave non-decision layout counters only with explicit allowlist entries.

4. **Apply claims to exports**
   - Files:
     - `src/dpsim/process_dossier.py`
     - `src/dpsim/visualization/panels/sop_export.py`
     - `src/dpsim/visualization/panels/run_compare.py`
   - Export claims, not raw numbers, for user-facing tables.

### Architectural Work

- Make `DecisionClaim` the boundary between model results and human-facing outputs.
- Dossier and SOP exports should consume the same claim objects as the UI.
- Optimization objective reporting should also consume claims, even if internal optimization uses raw values.

### Acceptance Criteria

- Bare metric baseline reduced to zero or to an allowlist with one documented reason per entry.
- Every M1/M2/M3 numeric user-facing value can be traced to an `OutputType`.
- SOP and dossier exports include render mode and evidence tier for each claim.
- Tests prove `VALIDATED_QUANTITATIVE`, `CALIBRATED_LOCAL`, `SEMI_QUANTITATIVE`, `QUALITATIVE_TREND`, and `UNSUPPORTED` claims render differently.

## 5. Stage S2: Calibration and Assay Infrastructure

### Scientific Rationale

DPSim cannot become quantitatively useful without wet-lab calibration. The current schema is a good foundation, but calibration must become an operator workflow with data quality checks, not just a file import feature.

### Coding Work

1. **Add spreadsheet dependency extra**
   - File: `pyproject.toml`
   - Add:

```toml
spreadsheet = ["pandas>=2.2", "openpyxl>=3.1"]
```

2. **Standardize assay templates**
   - Directory: `data/validation/`
   - Add templates for:
     - L1 DSD
     - interfacial tension
     - dispersed-phase viscosity
     - pore size and porosity
     - swelling ratio
     - modulus/compression
     - ligand density
     - activity retention
     - residual reagent
     - ligand leaching
     - pressure-flow
     - static binding
     - DBC breakthrough

3. **Add calibration quality gates**
   - New file: `src/dpsim/calibration/quality_gates.py`
   - Gates:
     - minimum replicate count;
     - coefficient of variation threshold;
     - required units;
     - LOD/LOQ handling;
     - valid-domain coverage;
     - holdout dataset availability;
     - target molecule match;
     - mobile-phase and temperature match.

4. **Build fit outputs as first-class artifacts**
   - New or extended files:
     - `src/dpsim/calibration/fitters.py`
     - `src/dpsim/calibration/calibration_store.py`
   - Fit output should include:
     - parameter posterior or standard error;
     - fitted valid domain;
     - source assay IDs;
     - fit method;
     - diagnostics;
     - tier-promotion recommendation.

5. **Calibration-store hash**
   - Add deterministic hash to `CalibrationStore`.
   - Record hash in `ProcessDossier`, SOP export, and run-history snapshots.

### Architectural Work

- Treat calibration as a domain object, not an optional side dictionary.
- Add `CalibrationDataset`, `CalibrationFit`, and `CalibrationApplicability` as separate concepts.
- Tier promotion should be possible only through calibration applicability checks.

### Acceptance Criteria

- A bench user can import a CSV/XLSX assay file and see validation errors before applying it.
- Calibration entries cannot promote tiers if target molecule, pH, salt, temperature, or family are out of domain.
- Process dossier includes assay IDs, calibration hash, and fit diagnostics.
- At least one end-to-end example calibration promotes a single output from `SEMI_QUANTITATIVE` to `CALIBRATED_LOCAL` in tests.

## 6. Stage S3: Scientific Model Hardening

### Scientific Rationale

The simulator covers many polymer families and isotherm classes, but real confidence is uneven. This stage makes model maturity explicit and blocks uncalibrated model transfer from appearing quantitative.

### Coding Work

1. **Create family support registry**
   - New file: `src/dpsim/core/family_support.py`
   - One record per polymer family:
     - fabrication route;
     - L1/L2/L3/L4 model;
     - M2 compatibility level;
     - M3 pressure-envelope support;
     - calibration requirements;
     - maximum uncalibrated evidence tier.

2. **Add family maturity panel**
   - UI file: new `src/dpsim/visualization/panels/family_support.py`
   - Render family support in M1 and M3.

3. **Tighten M1 valid domains**
   - Add unavoidable warnings for:
     - sub-Kolmogorov droplet predictions;
     - high dispersed-phase viscosity outside kernel validity;
     - unvalidated CFD zones;
     - placeholder L4 family transfer.

4. **Tighten M2 assay gates**
   - Numeric ligand density, activity retention, leaching, residual reagent, and free-protein wash claims must require assay evidence for number rendering.

5. **Tighten M3 isotherm gates**
   - For each isotherm class, define:
     - required calibration assay;
     - required mobile-phase fields;
     - valid pH/salt/imidazole domain;
     - target molecule applicability;
     - uncalibrated render ceiling.

6. **Pressure-flow calibration first**
   - Add pressure-flow calibration workflow as a primary M3 setup action.
   - Promote `K_geom` only when measured data cover the operating envelope.

### Architectural Work

- Replace scattered family caveats with a central registry consumed by validators, UI, claims, and SOP export.
- Treat any analogy-based family route as `QUALITATIVE_TREND` unless a calibration fit exists for that family.
- Treat default isotherm parameters as numerical priors, not decision data.

### Acceptance Criteria

- Selecting any family shows its model maturity and maximum claim tier.
- M3 DBC cannot render as a point number from default isotherm constants.
- Pressure-flow calibration can promote pressure-envelope claims for a defined family/column/mobile-phase domain.
- Tests cover at least agarose-chitosan, alginate, cellulose, PLGA, and one composite family.

## 7. Stage S4: Wet-Lab Workflow Execution

### Scientific Rationale

A real downstream-processing platform must represent what the operator will physically do, measure, and record. The current platform has SOP/session/run-comparison support, but laboratory execution state should be made explicit.

### Coding Work

1. **Extend `ProcessStep` execution metadata**
   - Add fields or structured parameters for:
     - material lot;
     - sample ID;
     - operator;
     - instrument ID;
     - acceptance criteria;
     - QC assay link;
     - fraction ID;
     - hazard note;
     - stop/go condition.

2. **Add QC checkpoint model**
   - New file: `src/dpsim/core/qc_checkpoint.py`
   - Checkpoints:
     - DSD measured;
     - residual oil/surfactant measured;
     - ligand density measured;
     - residual reagent measured;
     - pressure-flow measured;
     - breakthrough measured;
     - leaching/cycle test measured.

3. **Fraction collection and trace ingestion**
   - Add objects:
     - `DetectorTrace`
     - `FractionCollection`
     - `TraceAlignment`
   - Support UV, conductivity, pressure, pH, and optional fluorescence/MS.

4. **SOP export upgrade**
   - SOP should include:
     - reagent preparation;
     - hazard flags;
     - timers;
     - sampling points;
     - required assays;
     - acceptance criteria;
     - fallback actions when pressure or breakthrough deviates.

5. **Predicted-vs-measured workflow**
   - Extend current pressure overlay to include:
     - breakthrough curve overlay;
     - elution peak overlay;
     - calibration residual plots;
     - measured vs predicted DBC and pressure-flow.

### Architectural Work

- Wet-lab operations should be first-class objects, not just UI text.
- Every SOP line should be traceable to `ProcessRecipe` and every measured result to `AssayRecord`.
- The system should support a "screen -> run -> measure -> calibrate -> rerun" loop.

### Acceptance Criteria

- SOP export contains QC checkpoints and assay templates.
- A run can attach measured pressure and breakthrough traces.
- Dossier records sample IDs, fraction IDs, instrument IDs, and calibration linkage.
- UI shows which QC checkpoints are missing before allowing stronger claims.

## 8. Stage S5: Optimization Under Evidence Constraints

### Scientific Rationale

Optimization is valuable only if it does not optimize fantasy. BO and inverse design must respect evidence tiers, calibration domains, pressure limits, family compatibility, and wet-lab feasibility.

### Coding Work

1. **Lazy-load optimization stack**
   - Complete S0 optional import work.

2. **Trust-aware objective filtering**
   - Ensure `compute_objectives_trust_aware` excludes:
     - `UNSUPPORTED`;
     - uncalibrated quantitative objectives;
     - out-of-domain candidates;
     - pressure-envelope blockers;
     - invalid chemistry sequences.

3. **Optimization claim reporting**
   - Candidate outputs must be `DecisionClaim` objects.
   - Pareto fronts should show evidence tier per candidate.

4. **Wet-lab actionability score**
   - Add objective or constraint for:
     - number of missing assays;
     - reagent hazard;
     - protocol duration;
     - pressure headroom;
     - calibration distance.

5. **Inverse design safeguards**
   - Require minimum data count and ESS threshold.
   - Mark importance-sampling inverse results as advisory unless supported by enough measurements.

### Architectural Work

- Optimizer should consume the same validation and decision-claim layer as the UI.
- Optimization should not have a private interpretation of trust.
- Candidate ranking should separate "best predicted" from "best actionable".

### Acceptance Criteria

- Optimization tests skip cleanly when extras are absent.
- With extras installed, BO refuses unsupported or uncalibrated objectives by default.
- Pareto candidate export includes evidence tier, missing calibration, and pressure feasibility.
- Inverse design reports when posterior information is too weak to support a recommendation.

## 9. Cross-Stage Test Strategy

### Unit Tests

- Evidence-tier comparison by `.value`.
- `DecisionClaim` render modes.
- Calibration quality gates.
- Family support registry.
- Isotherm calibration requirements.
- Optional dependency errors.

### Integration Tests

- Default lifecycle smoke.
- Lifecycle with calibration store.
- UI mobile phase/isotherm selection affects M3.
- Pressure-flow calibration promotes pressure-envelope tier.
- Spreadsheet import -> calibration store -> lifecycle -> dossier.
- DSD bin-resolved propagation into M3.

### Scientific Regression Tests

- Mass balance:
  - PBE dispersed phase;
  - M2 ACS sites;
  - M3 LRM breakthrough;
  - elution recovery.
- Units:
  - mL/min -> m3/s;
  - kPa/bar -> Pa;
  - mM/M -> mol/m3 where appropriate;
  - mg/mL protein -> mol/m3 with molecular weight.
- Valid-domain demotion:
  - pH;
  - salt;
  - temperature;
  - polymer concentration;
  - bead diameter;
  - pressure-flow range.

### CI Matrix

| Job | Install | Expected behavior |
|---|---|---|
| base | `pip install -e .` | Core import and smoke tests pass. |
| dev | `pip install -e ".[dev]"` | Non-optional test suite passes/skips cleanly. |
| ui | `pip install -e ".[ui,dev]"` | Streamlit/UI tests pass. |
| spreadsheet | `pip install -e ".[ui,spreadsheet,dev]"` | CSV/XLSX calibration tests pass. |
| optimization | `pip install -e ".[optimization,dev]"` | BO and inverse-design tests pass. |
| all | `pip install -e ".[all]"` | Full suite passes within defined timeout. |

## 10. Data and Calibration Campaign Plan

The software roadmap should be paired with six wet-lab campaigns.

| Campaign | Calibrates | Minimum dataset |
|---|---|---|
| A: DSD | L1 PBE kernels and DSD prediction | 2 impellers x 3 RPM x 2 viscosities x triplicate DSD. |
| B: morphology | L2 pore/porosity/swelling | 3 formulations x 2 gelation conditions x pore and swelling assays. |
| C: mechanics | L4 modulus and pressure state | single-bead or packed-bed compression across buffer states. |
| D: functionalization | M2 ligand density/activity/residuals | ligand density, activity retention, free ligand/protein wash, leaching, residual reagent. |
| E: packed-bed hydraulics | M3 pressure envelope and `K_geom` | pressure-flow curves across flow, bed height, viscosity, and family. |
| F: binding/performance | M3 isotherm, breakthrough, recovery, lifetime | static binding, DBC breakthrough, elution recovery, cycle/leaching data. |

The software should not promote any output above `SEMI_QUANTITATIVE` unless its campaign-specific fit exists and the current recipe lies inside that fit domain.

## 11. Architectural End State

The desired end state is not a larger simulator. It is a stricter simulator.

Required end-state properties:

- One recipe object drives solver, SOP, UI, dossier, and calibration comparison.
- One result graph records every dependency.
- One decision-claim layer governs every displayed/exported number.
- One support registry describes model maturity by family, reagent, isotherm, and operation.
- One calibration pipeline converts assay records into bounded tier promotions.
- Optimization consumes the same trust model as human-facing outputs.
- Unsupported or uncalibrated physics can still be explored, but cannot masquerade as operational guidance.

## 12. Immediate Next Coding Batch

Recommended first batch after this plan:

1. Fix `app.py` tier-banner evidence source.
2. Lazy-load optional optimization dependencies and skip optimization tests cleanly.
3. Update README and `current_support_matrix.md` to v0.8.9.
4. Add `spreadsheet` optional extra with `openpyxl`.
5. Start `DecisionClaim` in `src/dpsim/core/decision_claim.py`.
6. Convert one M3 result panel to claim-based rendering as a reference pattern.

This first batch is small enough to land safely and directly addresses the highest-risk audit findings.
