# AUDIT — v0.8.5 end-to-end scientific-fidelity review (Phase 1)

> **Role**: /scientific-advisor — acting as a senior downstream-processing technology researcher.
> **Date**: 2026-05-10 · **Audit scope**: end-to-end DPSim at v0.8.5 · **Method**: targeted backend ↔ UI ↔ ADR cross-checks.
> **Companion documents**: Phase 2 (`AUDIT_v0_8_5_e2e_phase2_user.md`), Phase 3 (`AUDIT_v0_8_5_e2e_phase3_architecture.md`), and the joint plan (`update_workplan_2026-05-10_v0_9_0.md`).

---

## §0 — Verdict in one paragraph

DPSim's v0.7 → v0.8.5 cluster massively expanded the backend's scientific surface (per-family u_crit anchor per ADR-004; salt/imidazole/SMA/competitive isotherm adapters per ADR-005/006; forward + inverse Bayesian envelopes per ADR-007/010/011; monitor-source abstraction per ADR-008; multi-column series per ADR-009). However, the v0.8.4 "UI-completeness" pass shipped widgets that are **not actually mounted in production code paths**, and the v0.8.5 release did not retroactively wire them. As a result, the simulator's most consequential scientific knobs — **mobile-phase composition** (which sets μ and the entire pre-flight envelope) and **isotherm class** (which sets the binding regime) — remain hardcoded to defaults at the UI ↔ orchestrator boundary. A user running DPSim at v0.8.5 who sees the dashboard and presses *Run* receives a simulation in which their downstream processing reality (e.g. high-salt elution, IMAC-imidazole gradient, IEX salt step) is **silently replaced by water-at-20 °C with bare Langmuir binding**. This is the single most important finding of the audit.

The scientific machinery is largely sound — the equations, the ADRs, the calibration discipline are coherent. The defect is at the wiring layer between user input and the model. Closing this gap is a small, mechanical change that turns DPSim's scientific surface from "exists" to "reachable", and is the priority work for v0.8.6.

Beyond the wiring, six secondary scientific defects affect tier honesty (some outputs ship without uncertainty-band rendering), regime applicability (HIC, ProteinA, IMAC bare models are not user-selectable), and validation discipline (the Bayesian inverse fit will run on too-few measurements without blocking).

---

## §1 — Tier 1: critical scientific-fidelity defects (v0.8.6 priority)

### S-1 · Mobile-phase composition widget is dead code in production

**Finding.** `src/dpsim/visualization/panels/mobile_phase.py::render_mobile_phase_widget` (v0.8.4 W-053) is defined and unit-tested but is **never called by any production UI file**. Verified by grep: the only references are the definition and the test file `tests/visualization/test_mobile_phase_widget.py`. Inside `tab_m3.py:1054` and equivalent panels, mobile-phase is hardcoded as `MobilePhase()` — water-like at 20 °C, no salt, no glycerol/ethanol, no μ override.

**Why this matters scientifically.**

* μ is the central variable in the Kozeny-Carman pressure prediction (`pressure_envelope.py:357-360`) and in the u_crit operational ceiling per ADR-004 §3.4. Substituting μ_water (≈ 1 mPa·s) for the actual salt-elution viscosity (which can be 30–60 % higher at 1 M NaCl + 10 % glycerol) silently *over-predicts* `Q_max` and silently *under-predicts* ΔP_max,op. A user reads the indicator green when bench reality would have been amber.
* μ also drives the LRM transport solver's mass-transfer coefficient implicitly (`module3_performance/transport/lumped_rate.py`), so breakthrough curve sharpness is mis-modelled in the same direction.
* The `valid_domain_violations` machinery in `pressure_envelope.py:122-125` will not fire if the user's *intended* mobile phase falls outside the calibrated envelope — because the user's intent never reached the envelope.

**Severity**: **CRITICAL**. The v0.8.4 CHANGELOG (lines 13-15) claims this defect (C1) is closed; in practice it is not.

### S-2 · Isotherm selector widget is dead code in production

**Finding.** `src/dpsim/visualization/panels/isotherm_selector.py::render_isotherm_widget` (v0.8.4 W-055) is defined and unit-tested. Eight unit tests in `tests/visualization/test_isotherm_selector.py` exercise it. **Zero production callers.** The module's `IsothermChoice` and `IsothermSpec` types appear nowhere outside this file. The lifecycle orchestrator `src/dpsim/lifecycle/orchestrator.py::DownstreamProcessOrchestrator.run()` does not accept `isotherm_spec`; the M3 sub-orchestrator at `module3_performance/orchestrator.py:247` calls `select_isotherm_from_fmc(fmc_hint)` driven by an internal hint the user cannot set.

**Why this matters scientifically.**

* The five modulated isotherms (`SaltModulatedLangmuir`, `ImidazoleModulatedLangmuir`, `SaltModulatedSMA`, `SaltModulatedCompetitiveLangmuir`, plus bare `Langmuir`) encode physically distinct binding regimes — IEX vs IMAC vs Protein-A vs HIC. Defaulting silently to Langmuir means a user simulating an IEX salt-step gradient gets a *no-modulation* binding curve. The breakthrough, peak elution time, and resolution predictions become meaningless beyond an order-of-magnitude smell check.
* The `calibrated_locally` checkbox per sub-form was the v0.8.4 mechanism for promoting `decision_tier` from SEMI_QUANTITATIVE to CALIBRATED_LOCAL. Because the widget is unmounted, **no path exists to claim CALIBRATED_LOCAL through this surface** — the only promotion path is the wet-lab YAML uploader, which is itself in a different tab (Calibration & Uncertainty) and only sets store-level entries, not the active simulation's isotherm tier.

**Severity**: **CRITICAL**. The v0.8.4 CHANGELOG (line 14) claims C2 is closed; in practice it is not.

### S-3 · Tier banner unmounted — global tier state never surfaced

**Finding.** `src/dpsim/visualization/shell/tier_banner.py::render_tier_banner` (v0.8.4 W-058) is defined and unit-tested. Zero production callers. The CHANGELOG (line 15) and the v0.8.4 release notes claim a SEMI_QUANTITATIVE banner appears on every stage. It does not.

**Why this matters scientifically.** The banner was the v0.8.4 answer to the README's "every output is decision-graded" promise. Its absence means a user looking at the M3 results page sees nothing about the active tier unless they happen to look at a specific metric's annotation. Users are routinely shown SEMI_QUANTITATIVE outputs as if they were CALIBRATED_LOCAL.

**Severity**: **CRITICAL**. v0.8.4 defect W-1 not closed.

### S-4 · Lifecycle pipe lacks user-supplied isotherm; mobile-phase plumbing unused

**Finding.** Even if S-1 and S-2 widgets were mounted, `src/dpsim/visualization/ui_workflow.py::render_lifecycle_run_panel` (the actual lifecycle invocation site) has **zero references to `mobile_phase=` or `isotherm_spec=`**. The orchestrator's `mobile_phase` kwarg added in v0.8.4 W-054 is technically present at `lifecycle/orchestrator.py:782` but no caller passes it.

**Why this matters scientifically.** The chain UI ↔ session_state ↔ orchestrator-call is broken at the orchestrator-call link. The pre-flight envelope panel inside `tab_m3.py:1054` calls `compute_pressure_envelope` directly with `MobilePhase()` defaults — bypassing the lifecycle's W-054 kwarg entirely.

**Severity**: **CRITICAL**. Closes the dependency: S-1 and S-2 cannot be fixed without S-4.

---

## §2 — Tier 2: orphan backend modules (v0.8.7 priority)

### S-5 · Bare isotherms (HIC, ProteinA, bare IMAC, bare SMA, bare Competitive) have no UI selection path

**Finding.** Six classes are defined under `src/dpsim/module3_performance/isotherms/` but absent from `IsothermChoice`:

| Class | File | UI path |
|---|---|---|
| `HICIsotherm` | `hic.py` | None — only via `adapter.select_isotherm_from_fmc("hic_*")` internal hint |
| `ProteinAIsotherm` | `protein_a.py` | None — only via `method.py:25` internal use |
| `IMACCompetitionIsotherm` | `imac.py` | None — wrapped by `imidazole_dependent.py` |
| `SMAIsotherm` | `sma.py` | None — wrapped by `sma_modulated.py` |
| `CompetitiveLangmuirIsotherm` | `competitive_langmuir.py` | None — wrapped by `competitive_salt_dependent.py` |
| `CompetitiveAffinityIsotherm` | `competitive_affinity.py` | None |

**Why this matters scientifically.** HIC is a different binding regime from IEX or IMAC and must be selectable explicitly; today it is unreachable. ProteinA is the canonical antibody-capture isotherm (its presence in `method.py` proves the backend can use it) but the UI surfaces only "Langmuir" as the AGAROSE_CHITOSAN default (`isotherm_selector.py:80`) — a Langmuir is *not* a ProteinA. Even if S-2 is closed in v0.8.6 by mounting `render_isotherm_widget`, it would expose only 5 of 11 isotherms.

**Severity**: **HIGH** for HIC and ProteinA (workflow blockers); **MEDIUM** for the bare modulated underlies (the wrappers cover them).

### S-6 · Detection modules are 100 % UI orphans

**Finding.** `src/dpsim/module3_performance/detection/{uv,fluorescence,conductivity,ms}.py` are defined backends with **zero `src/dpsim/visualization/` imports** (verified by grep). Real packed-bed chromatography produces UV / conductivity / fluorescence / mass-spec traces; DPSim models them but never displays them.

**Why this matters scientifically.** The UV trace and conductivity trace are the *primary* operator-facing readouts on a wet-lab UNICORN run. A simulator that produces predictions a wet-lab user cannot directly compare against is operationally inert. Today, DPSim's M3 results page surfaces breakthrough curves and effluent concentrations but not the detector traces a user would see at the bench.

**Severity**: **HIGH**. This is a foundational fidelity gap.

### S-7 · OptimizationEngine (BO under hard pressure constraint) is CLI-only

**Finding.** `src/dpsim/optimization/engine.py::OptimizationEngine` is reachable only via the `dpsim` CLI through `src/dpsim/__main__.py:685, 713`. **Zero UI tabs invoke it.** v0.8 added BO with a hard pressure feasibility constraint per the cumulative open work; the dashboard cannot run optimization.

**Why this matters scientifically.** Inverse design — *given a target DBC and breakthrough sharpness, what column geometry / Q / mobile-phase / ligand density gets me there?* — is the highest-value use of a simulator for wet-lab planning. Without UI exposure, this capability is invisible to most users.

**Severity**: **HIGH**.

### S-8 · MonitorSource Protocol (ADR-008) is unused by the UI

**Finding.** `src/dpsim/module3_performance/monitor_source.py` defines the `MonitorSource` Protocol with three concrete backends (`CSVReplayMonitorSource`, `SimulatedMonitorSource`, `NullMonitorSource`). The Streamlit streaming monitor (`tabs/tab_m3_monitor.py`) uses the legacy `pressure_monitor_replay.parse_csv` + `replay()` directly — bypassing the abstraction. The ADR-008 invariant is implemented but unused.

**Why this matters scientifically.** The Protocol was designed to allow switching between offline replay, simulated-trace test mode, and (eventually) live UNICORN. By bypassing it, the UI today supports only CSV upload — even simulated-trace and null modes (useful for demos and tests) are unreachable.

**Severity**: **MEDIUM**.

### S-9 · `monte_carlo_step_program` (multi-step coupled MC, B-2r/W-050) has no UI consumer

**Finding.** The forward MC panel (`tabs/calibration/forward_mc.py:28`) calls `monte_carlo_pressure_envelope` only — not `monte_carlo_step_program`. The latter draws once and evaluates every recipe step under shared random draws (the v0.8.3 invariant for correlated step-to-step uncertainty). UI users cannot run multi-step coupled MC.

**Severity**: **MEDIUM**.

---

## §3 — Tier 3: tier-honesty + validation-discipline gaps (v0.9 maturation)

### S-10 · Decision-grade rendering is inconsistent across the M3 surface

**Finding.** Some metrics (e.g. `tab_m3.py:798-870` pressure envelope panel) correctly route through `render_metric` with an `OutputType` and a `tier=`. Others use bare `st.metric` with no tier annotation (e.g. `tab_m3.py:1140-1145` cycle lifetime). The new `render_pressure_indicator` (v0.8.5) uses inline colour-by-headroom but does not pass through `render_decision_grade_annotation`, so the indicator's number does not visually carry the SEMI_QUANTITATIVE interval bracket.

**Why this matters scientifically.** The decision-grade tier ladder is DPSim's tier-honesty contract. Inconsistency means users can't tell at a glance whether a number is fully calibrated or order-of-magnitude. The absence is most damaging precisely where the user expects guidance — the live pressure indicator.

**Severity**: **MEDIUM**.

### S-11 · Pre-flight pressure envelope renders POST-run, not PRE-run

**Finding.** The envelope panel at `tab_m3.py:786+` runs after `lifecycle_result` is in session_state. The pressure indicator at `tab_m3.py:247` reads from `m3_pressure_envelope` (cached after the run completes — v0.8.5 B-3b). A user pressing *Run* with an unsafe Q sees the BLOCKER post-hoc; the pre-flight envelope itself is not surfaced *before* the run commits.

**Why this matters scientifically.** Per ADR-004 §3, the bed-compression ceiling is a **pre-flight** check. A user should see "your Q exceeds Q_max — bed will compress" *before* pressing Run, not after a 3-minute simulation. The current UI inverts this: the envelope panel is part of the *results* page, not the *configure* page.

**Severity**: **MEDIUM**.

### S-12 · Bayesian inverse runs on insufficient measurements without blocking

**Finding.** `tabs/calibration/inverse_inference.py` runs `infer_posterior_envelope` on whatever the user enters in the data editor. The ESS chip surfaces post-fit (v0.8.4 W-060). When ESS is low (concentrated posterior relative to prior) the user sees a warning but the result is shown. There is no input-time blocker for "you have only 3 measurements — fit will be ill-posed".

**Why this matters scientifically.** A user fitting on 3 noisy points and treating the posterior as truth is worse than a user who didn't fit at all. Per ADR-010 §"Tier mapping", posteriors at low ESS should be hidden, not just chip-warned.

**Severity**: **MEDIUM**.

### S-13 · M1 → M2 → M3 handoff lacks structural enforcement

**Finding.** A user can configure M1 with `polymer_family=AGAROSE`, M2 with `polymer_family=PLGA` (different `family_reagent_matrix`), and M3 with a column geometry whose porosity is inconsistent with the M1 fabricated bead. The lifecycle orchestrator validates *some* of this (via `validation.add(BLOCKER, ...)`) but the UI itself does not constrain the inputs to flow consistently.

**Why this matters scientifically.** End-to-end physical consistency (the same bead size flows from M1 emulsification → M2 functionalization → M3 packing) is the simulator's value proposition. Allowing the user to enter incompatible cross-stage inputs lets them get plausible-looking results that have no physical referent.

**Severity**: **MEDIUM**.

---

## §4 — Tier 4: lower-leverage but real

### S-14 · Unit chaos at user-input boundaries

* Q is variously **mL/min**, **m³/s**, **L/h** depending on widget.
* ΔP is **Pa**, **kPa**, **bar** across panels.
* Concentrations: **mg/L**, **mol/m³**, **mM** in different sub-forms.

A user has to know the conversions; one mis-entry silently scales the simulation by 60.

### S-15 · No end-to-end demo recipe / guided wizard

The README documents capability; the dashboard offers no on-ramp for a first-time user. *Where do I click first?* The first-run experience requires reading the user manual.

### S-16 · No SOP / wet-lab procedure export

A user-facing "wet-lab procedure PDF" derived from the recipe + envelope + isotherm + calibration store would be the simulator's most operationally valuable artefact for actual lab use. No path exists.

### S-17 · Recovery-action labels are text-only — no UI control linking

The streaming monitor's `RecoveryAction` chip says *"reduce flow to Q_recommended"*. There is no button that does it.

### S-18 · Calibration store ingestion is YAML-only

Users with bench data must hand-author YAML. No in-app editor; no bench-spreadsheet import path.

### S-19 · The "screen → calibrate → tighten" promise has no end-to-end demo

The README's central editorial promise has no guided workflow that walks through it from a fresh dashboard. Every component exists; they don't compose into a story.

### S-20 · No comparison against historical runs / benchmarking

There is no "compare two runs" affordance. A wet-lab user iterating on conditions cannot ask the simulator to overlay their last three configurations.

---

## §5 — Scientific validity by stage

| Stage | Backend physics | UI exposure | Fidelity verdict |
|---|---|---|---|
| **M1 emulsification** | Energy-dissipation kernels (Rushton + rotor-stator); thermal ramps; per-family validation envelopes; family-aware widget hiding via `family_selector.py` | `tab_m1.py` + 16 sub-files under `tabs/m1/` | **PASS** with one note: the gelation pore-model selection is implicit (single-phase vs ternary) — could be more explicit |
| **M2 functionalization** | EDC/NHS kinetics (`edc_nhs_kinetics.py`); ACS site converter; surface-area model; family reagent matrix | `tab_m2.py` + reagent-profile imports | **PARTIAL** — M2's ligand density output IS consumed by M3 (`tab_m3.py:711, 1043`) ✓; but M2 input widgets do not surface decision-grade tier per metric |
| **M3 chromatography** | Per-family u_crit anchor (ADR-004); 5 modulated isotherms (ADR-005/006); LRM transport with BDF/LSODA mode-switch; forward + inverse Bayesian envelopes (ADR-007/010/011); multi-column series (ADR-009) | `tab_m3.py` + 4 calibration sub-tabs | **FAIL** — see S-1, S-2, S-3, S-4 above; the central scientific knobs are unwired |
| **Calibration & Uncertainty** | Forward MC, inverse importance-sampling, ESS diagnostic, posterior `log_cov` round-trip, multi-column series, wet-lab YAML ingestion | `tab_calibration.py` + 4 sub-files | **PASS** — this stage is properly wired (post v0.8.4 B-2s KEYSTONE); only S-9 (multi-step coupled MC) and S-12 (insufficient-data blocker) remain |
| **Optimization** | BO under hard pressure constraint | None | **FAIL** — see S-7 |
| **Streaming monitor** | CSV replay + `MonitorSource` Protocol | CSV upload only | **PARTIAL** — see S-8, S-17 |
| **Detection** | UV / fluorescence / conductivity / MS models | None | **FAIL** — see S-6 |
| **Resin lifetime** | Empirical first-order deactivation | `panels/lifetime.py` → `tab_m3.py:289` | **PASS** |

---

## §6 — Recommended remediation hierarchy

The defects above split cleanly into three release horizons.

### v0.8.6 — Wiring fixes (CRITICAL)

Close S-1, S-2, S-3, S-4 — mount the unmounted v0.8.4 widgets into production code paths and thread them through the lifecycle. Mechanical work; no new science needed.

### v0.8.7 — Orphan exposure (HIGH)

Close S-5 (HIC + ProteinA in selector); S-6 (detection traces in M3 results); S-7 (OptimizationEngine UI tab); S-8 (MonitorSource Protocol UI); S-9 (`monte_carlo_step_program` UI).

### v0.9.0 — Maturation (MEDIUM + LOW)

Close S-10 (decision-grade consistency); S-11 (pre-flight envelope relocated to pre-Run); S-12 (input-time inverse-fit blockers); S-13 (M1→M2→M3 enforcement); S-14 (unit standardisation); S-15 (guided wizard / first-run example); S-16 (SOP export); S-17 (action→control linking); S-18 (in-app calibration editor); S-19 (end-to-end demo); S-20 (run-vs-run comparison).

The full sequenced plan with W-IDs, batches, model-tier assignments, and validation gates is in `docs/update_workplan_2026-05-10_v0_9_0.md`.

---

## §7 — What this audit does NOT challenge

The following are **scientifically sound and properly implemented** — flag them so the v0.9 maturation does not regress:

* The per-family u_crit anchor (ADR-004) is correct and the formulation is honest.
* The salt-modulated SMA promotion path (ADR-006) is theoretically defensible.
* The importance-sampling inverse fit (ADR-010) is a reasonable v0.8 stop short of MCMC.
* The decision-grade tier ladder (NUMBER → INTERVAL → RANK_BAND → SUPPRESS) is the right policy primitive.
* The Family-First UI contract (CLAUDE.md) is the right invariant for cross-family widget hiding.
* The AST gate (`tests/test_v9_3_enum_comparison_enforcement.py`) is the right enforcement mechanism.
* The wet-lab YAML ingestion path (v0.8.4 W-057, properly wired at `tab_calibration.py:156`) is sound.
* The RecoveryAction taxonomy (`tab_m3_monitor.py:50-58`) is operationally correct.
* The pressure envelope dataclass (`pressure_envelope.py:97-188`) exposes the right fields.

The audit's findings are wiring and exposure defects, not scientific defects in the math.

---

## §8 — Disclaimer

This scientific analysis is provided for informational, research, and advisory purposes only. It does not constitute professional engineering advice. The findings above were derived by static cross-checking of source files in the v0.8.5 tagged commit; some defects may be context-dependent or have masking workarounds not visible from grep alone. All proposed remediations should be validated by running the dashboard end-to-end before being shipped.
