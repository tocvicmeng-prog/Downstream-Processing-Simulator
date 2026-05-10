# Audit — DPSim v0.8.3 UI completeness, coherence, and scientific-workflow alignment

**Phase 1 of joint engagement** — `/scientific-advisor` lead. Phase 2 (`/architect` decomposition) and Phase 3 (`/dev-orchestrator` work plan) consume this document verbatim.
**Date:** 2026-05-10
**Backend baseline:** v0.8.3 (post-pressure-envelope cluster)
**Audit scope:** the Streamlit UI under `src/dpsim/visualization/` against the v0.7.0 → v0.8.3 backend feature set.

---

## §0 Executive verdict (one screen)

The Streamlit UI has fallen substantially behind the backend. **Approximately one-third** of the v0.7 → v0.8.3 user-facing capabilities are reachable through the UI; the remainder are Python-API only. The pre-flight pressure envelope panel and the offline streaming-monitor section landed cleanly, but the **forward Monte Carlo, inverse Bayesian inference, multi-column series, salt/imidazole-modulated isotherm selection, mobile-phase composition input, BO pressure feasibility, and `MonitorSource` Protocol surfaces are entirely absent from the UI**. Tier-gating coverage is partial — strong on the scalar-metric path (`render_metric` in M1/M2/M3 + `render_decision_grade_annotation` on the M1 droplet plot, M3 DBC, M3 Q_max badges) but missing on the `plots_m2.py` surface-area chart, where an ad-hoc "Trust:" badge bypasses the policy. **No stale `max_safe_flow_rate` runtime calls remain in the UI** (one docstring reference is a deliberate deprecation note). The most consequential single defect is **the absence of any `MobilePhase` composition input** — temperature, NaCl, glycerol, and ethanol fractions cannot be edited from the UI, even though the v0.7 viscosity model and ADR-005 salt-modulated elution physics depend on these directly.

For a junior chromatography researcher, the UI presents a coherent screening narrative through M1 → M2 → M3 → pre-flight envelope → breakthrough, then **abruptly dead-ends**. The wet-lab calibration loop (measured Q-vs-ΔP → posterior K_geom → tighter forward bands) is described in the README but unreachable from the UI. The advisory loop (forward MC `p_blocker` → "drop Q to Q_recommended" recommendation) is similarly unreachable.

**Defect counts.** 9 conflicts (C1–C9 below). 14 backend capabilities classified MISSING-IN-UI. 3 capabilities PARTIAL. 2 capabilities MISALIGNED. 0 truly DEPRECATED-IN-UI surfaces (all v0.6.6 references were cleaned in v0.8.0).

---

## §1 Backend capability inventory

Grouped by module. ADR references are canonical when code is not self-documenting.

### 1.1 Lifecycle (`lifecycle/orchestrator.py`)

| ID | Capability | Entry point | User-controllable inputs | User-visible outputs | Use case |
|---|---|---|---|---|---|
| L1 | Run full M1→M2→M3 lifecycle | `DownstreamProcessOrchestrator().run()` | ProcessRecipe (TOML or Python) | `DownstreamLifecycleResult` with M1/M2/M3 sub-results, pressure_envelope, ProcessDossier | First-pass screening |
| L2 | Pre-flight pressure envelope per run | `lifecycle.orchestrator` post-M2 wire-in (W-025) | All M1 + M2 + column geometry; uses default `MobilePhase()` today | `PressureEnvelope` on `result.pressure_envelope` (u_crit, Q_max, headroom, decision_tier) | Reject infeasible recipes before M3 |

### 1.2 M1 — Fabrication

| ID | Capability | Entry point | Inputs | Outputs | Use case |
|---|---|---|---|---|---|
| M1-1 | PBE droplet emulsification | `level1_emulsification/solver.py` | RPM, c_span80, T_oil, hardware mode | DSD (d10/d32/d50/d90, σ_ln) | Bead-size design |
| M1-2 | Phase-field gelation (cellulose NIPS, agarose, etc.) | `level2_gelation/composite_dispatch.py::solve_gelation_by_family` | polymer_family, formulation | Pore architecture, porosity | Mechanism dispatch |
| M1-3 | Crosslinking kinetics | `level3_crosslinking/solver.py` | crosslinker, time, temperature | xi_final, p_final | Locking the network |
| M1-4 | Mechanical predictions | `level4_mechanical/` | gelation + crosslinking | G_DN, E* | Modulus envelope |
| M1-5 | CFD-PBE zonal coupling | `cfd/zonal_pbe.py` + `dpsim cfd-zones` CLI | zones.json, kernel preset | Zone-resolved DSD | Scale-up |

### 1.3 M2 — Functionalisation

| ID | Capability | Entry point | Inputs | Outputs | Use case |
|---|---|---|---|---|---|
| M2-1 | ACS-state evolution + sequence FSM | `module2_functionalization/orchestrator.py::ModificationOrchestrator` | Modification sequence (typed steps) | ACS site inventory, ligand density, evidence_tier | Functionalisation design |
| M2-2 | Reagent library (103 entries) | `reagent_library*.py` + `module2_functionalization/reagent_profiles.py` | reagent_key per step | Kinetics, hazards, calibration source | Reagent selection |
| M2-3 | FunctionalMediaContract assembly | `module2_functionalization/orchestrator.py` (post-orchestration) | M1ExportContract + M2 history | q_max estimate, K_a hint, ligand density, model_manifest | M3 input handoff |

### 1.4 M3 — Column performance (the v0.7→v0.8.3 cluster)

| ID | Capability | Entry point | Inputs | Outputs | Use case | ADR |
|---|---|---|---|---|---|---|
| M3-1 | Pre-flight pressure envelope | `module3_performance/pressure_envelope.py::compute_pressure_envelope` | polymer_family, ColumnGeometry, MobilePhase, Q_set, optional G_DN/E*/d32 overrides, optional calibration_store | u_crit, Q_max, Q_recommended, headroom, ΔP ceilings, decision_tier, valid_domain_violations | Pre-run safety check | ADR-004 |
| M3-2 | ε_b iteration (KC + bed-compression coupling) | `module3_performance/hydrodynamics.py::iterate_kc_compression` | flow_rate, μ, max_iter, tol, relaxation | dP_pa, ε_b_final, converged | Capture runaway near u_crit | — |
| M3-3 | Salt-modulated Langmuir isotherm | `isotherms/salt_dependent.py::SaltModulatedLangmuir` | base Langmuir, ν, c_salt_ref | salt-modulated K_a; routed via EquilibriumAdapter | IEX screening | ADR-005 |
| M3-4 | Imidazole-modulated Langmuir | `isotherms/imidazole_dependent.py::ImidazoleModulatedLangmuir` | base Langmuir, n, c_imidazole_ref | imidazole-modulated K_a | IMAC screening | — |
| M3-5 | Full SMA promotion adapter | `isotherms/sma_modulated.py::SaltModulatedSMA` | z, σ, K_eq, Λ, c_salt_ref | full SMA fixed-point loading | When σ is fitted | ADR-006 |
| M3-6 | Multi-component competitive IEX with per-ν shifts | `isotherms/competitive_salt_dependent.py::SaltModulatedCompetitiveLangmuir` | base, ν array, c_salt_ref | salt-modulated co-elution | Multi-protein co-elution screening | — |
| M3-7 | Forward MC envelope bands | `pressure_envelope_mc.py::monte_carlo_pressure_envelope` | priors (σ_log_*), `use_family_priors`, `log_cov`, n_samples, seed | P05/P50/P95 of Q_max, dP_predicted, headroom; **p_blocker, p_warning** | Tail-probability advisory before risky operating points | ADR-007, ADR-011 |
| M3-8 | Per-family MC priors registry | `pressure_envelope_mc.py::lookup_family_mc_prior` | polymer_family | FamilyMCPrior(σ_log_k_geom, σ_log_mu, σ_log_g_dn) | Family-aware uncertainty | ADR-007 |
| M3-9 | Multi-step coupled MC | `pressure_envelope_mc.py::monte_carlo_step_program` | step_program, priors | Per-step MCEnvelopeBands + worst_step_p_blocker | Recipe-wide risk assessment | — |
| M3-10 | Inverse Bayesian inference | `pressure_envelope_inverse.py::infer_posterior_envelope` | measurements (MeasuredPressureFlowPoint tuple), priors, Q_for_envelope | Posterior P05/P50/P95 on K_geom/μ/G_DN, posterior bands on envelope outputs, `log_cov`, ESS, ess_warning | Calibrate K_geom from measured Q-vs-ΔP | ADR-010 |
| M3-11 | Streaming pressure-trace monitor | `pressure_monitor.py::evaluate_pressure_trace` | reading, envelope, history | state, triggered_rule, **recovery_action**, headroom_ratio, dpdt, model_deviation_ratio | In-flight monitoring | — |
| M3-12 | CSV-replay helper | `pressure_monitor_replay.py::parse_csv` + `replay` | CSV path / StringIO + envelope | ReplaySummary | Offline trace review | — |
| M3-13 | MonitorSource Protocol | `monitor_source.py::MonitorSource` + `CSVReplay…` + `Simulated…` + `Null…` | Backend-specific | Stream of `PressureMonitorReading` | Hardware-agnostic monitoring | ADR-008 |
| M3-14 | Multi-column series envelope | `multi_column.py::compute_multi_column_envelope` + `MultiColumnGeometry` | columns tuple + per-column polymer_families + mobile_phase + Q_set | Per-column envelopes + series Q_max + worst headroom + weakest tier | Capture+polish series | ADR-009 |
| M3-15 | Lumped Rate Model breakthrough | `module3_performance/orchestrator.py::run_breakthrough` | column, isotherm, C_feed, Q, time | C_outlet curve, DBC₅/₁₀/₅₀, mass balance | Breakthrough screening | — |
| M3-16 | Gradient elution (multi-component, salt or pH) | `module3_performance/orchestrator.py::run_gradient_elution` | column, gradient program, isotherm, n_z | Peaks, gradient_affects_binding flag | Method scouting | — |
| M3-17 | Loaded-state elution (Protein A low-pH) | `module3_performance/method.py::run_loaded_state_elution` | loaded q profile, elution step | Peak time, peak width, recovery | Protein A method design | — |

### 1.5 Optimization (`optimization/`)

| ID | Capability | Entry point | Inputs | Outputs | Use case |
|---|---|---|---|---|---|
| O-1 | Multi-objective BoTorch optimization | `optimization/engine.py::OptimizationEngine` | bounds, target spec, n_iter | Pareto front | Inverse design |
| O-2 | Pressure-feasibility constraint (single + multi-step) | `optimization/objectives.py::PressureFeasibilityContext`, `PressureStep`, `pressure_feasible` | column, mobile_phase, Q_target OR step_program, polymer_family, headroom_threshold | (feasible, violations) | Drop infeasible BO candidates |

### 1.6 Calibration (`calibration/`)

| ID | Capability | Entry point | Inputs | Outputs | Use case |
|---|---|---|---|---|---|
| C-1 | Calibration store + wet-lab YAML ingestion | `calibration/wetlab_ingestion.py` + store | YAML campaigns | Updated tier on affected outputs | Tier promotion |
| C-2 | Posterior samples loader | `calibration/posterior_samples.py::PosteriorSamples` | marginals or full posterior | PosteriorSamples dataclass | MC propagation upstream of LRM |
| C-3 | Bayesian Langmuir fit (NUTS) | `calibration/bayesian_fit.py::fit_langmuir_posterior` | breakthrough data | Posterior dataclass | Optional `[bayesian]` extra |

---

## §2 UI surface inventory

### 2.1 Top-level shell

| Surface | File | Purpose |
|---|---|---|
| `app.py` | Page config + sidebar + scientific-mode top bar + stage rail + per-stage panels | Top-level dashboard entry |
| `shell/shell.py`, `shell/triptych.py`, `shell/stage_panels.py` | Stage routing | M1/M2/M3 navigation |
| `shell/autowire.py` | Auto-binding session state | Cross-tab state |
| `nav.py`, `pages/` | Streamlit multipage routing | Reagent-detail and suggestion-detail subpages |
| `help/help_widget.py` + `catalog.py` | In-UI help popovers | Junior-researcher orientation |

### 2.2 M1 surface (`tabs/tab_m1.py` + `tabs/m1/`)

- Polymer family selector (`tabs/m1/family_selector.py` per CLAUDE.md v9.0 contract — first M1 input)
- Hardware mode selector (Stirrer A / Stirrer B / glass beaker / jacketed vessel)
- Live cross-section animation in the Hardware · Emulsification box
- DSD plot (`plots.plot_droplet_size_distribution`) — **tier-gated since v0.8.3** (W-037)
- Phase field, crosslinking kinetics, Hertz, Kav curve, modulus comparison plots
- Result metrics rail with `render_metric` for d_mode, d32, etc.
- M1 optimization targets (`tabs/m1/targets_section.py`) — d32 / d_mode / pore / G_DN target inputs

### 2.3 M2 surface (`tabs/tab_m2.py`)

- Family-filtered reagent dropdowns (v0.3.0 B3, line 7+)
- Sequence FSM visualisation (the 4-stage chemistry chevron)
- ACS waterfall chart (`plots_m2.plot_acs_waterfall`)
- Surface-area comparison chart (`plots_m2.plot_surface_area_comparison`) — **NOT tier-gated** through render_metric / render_decision_grade_annotation; uses an ad-hoc `Trust:` badge
- G_DN / E* update metrics — **tier-gated since v0.8.3** (W-046, lines 744–745)
- ACS site inventory (per-site mol/particle)
- Modification history (per-step badge + caption)

### 2.4 M3 surface (`tabs/tab_m3.py` + `tabs/tab_m3_monitor.py`)

- Column geometry inputs (diameter, bed_height, bed_porosity, particle_porosity)
- Flow-rate slider in mL/min
- Single isotherm parameter inputs: q_max, K_L (line 360–377) — **only Langmuir is exposed**
- Feed concentration input
- Gradient elution opt-in (linear salt or pH ramp)
- Breakthrough panel: DBC₅/₁₀/₅₀ tier-gated metrics, breakthrough curve, chromatogram, **Q-vs-ΔP plot with envelope-derived Q_max** (recomputes envelope inline at line ~1005)
- Pressure envelope (pre-flight) section — `compute_pressure_envelope` exposed (subheader at line 790; W-025 wire-in)
- Streaming pressure monitor (offline replay) section — `tab_m3_monitor.render_pressure_monitor_section` (line 908)
- Gradient elution sub-panel (per-component peak table)
- Protein A method operation panel
- Catalysis sub-panel

### 2.5 Streaming monitor (`tab_m3_monitor.py`)

- CSV file uploader
- Downloadable example CSV (the operator-facing primer)
- Replay summary metric row (n readings, final state, first BLOCKER time, max headroom, max dΔP/dt)
- ΔP-vs-time plot with operational and 70% warning thresholds + per-reading state chips
- **`RecoveryAction` action chip** integrated in the final-state advisory (v0.8.2 W-041)

### 2.6 Calibration / dossier panels (`panels/calibration.py`, `panels/`)

- Generic file uploader at `panels/calibration.py:42` — purpose unclear; not labelled as the wet-lab YAML ingestion path
- Generic file uploader at `shell/stage_panels.py:387` — separate entry, also unlabelled

### 2.7 Decision-grade rendering helpers

- `decision_grade_render.render_metric` — used 12 times across M1/M2/M3
- `decision_grade_render.render_decision_grade_annotation` — used 6 times (M1 droplet plot, M3 DBC, M3 Q_max badge); both `plot_breakthrough_curve` and `plot_pressure_flow_curve` accept a `tier=` kwarg

---

## §3 Mapping matrix — backend ↔ UI

| Backend ID | Capability | UI verdict | Specific gap (where applicable) |
|---|---|---|---|
| L1 | Lifecycle run | **FULL** | — |
| L2 | Pre-flight envelope (auto) | **PARTIAL** | Result panel exposed; **no input for `MobilePhase` composition** — uses `MobilePhase()` defaults silently. See C1. |
| M1-1 | PBE emulsification | **FULL** | — |
| M1-2 | Phase-field L2 dispatch | **FULL** | Family-First contract enforced |
| M1-3 | Crosslinking | **FULL** | — |
| M1-4 | Mechanical | **FULL** | — |
| M1-5 | CFD-PBE zones.json | **PARTIAL** | CLI works; UI does not surface the zones.json upload / per-zone ε editing |
| M2-1 | ACS sequence FSM | **FULL** | — |
| M2-2 | Reagent library | **FULL** | Family-filtered dropdowns |
| M2-3 | FunctionalMediaContract | **FULL** | — |
| M3-1 | Pre-flight envelope | **PARTIAL** | Output exposed; `mobile_phase` not editable; `calibration_store` injection point not exposed (no UI to override `K_geom`) |
| M3-2 | ε_b iteration | **FULL** (transparent) | — |
| M3-3 | SaltModulatedLangmuir | **MISSING** | No UI selector for IEX salt-modulated isotherm. Only Langmuir + competitive Langmuir reachable. |
| M3-4 | ImidazoleModulatedLangmuir | **MISSING** | No UI selector for IMAC screening |
| M3-5 | SaltModulatedSMA | **MISSING** | No UI for the σ-fitted SMA promotion path |
| M3-6 | SaltModulatedCompetitiveLangmuir | **MISSING** | Multi-component IEX with per-ν shifts is Python-API only |
| M3-7 | Forward MC envelope | **MISSING** | No UI button to run MC and surface `p_blocker` / `p_warning` advisory |
| M3-8 | Per-family MC priors | **MISSING** | No UI to inspect / override σ_log_* per family |
| M3-9 | Multi-step coupled MC | **MISSING** | No UI surface for `monte_carlo_step_program` |
| M3-10 | Inverse Bayesian inference | **MISSING** | No UI to enter measured (Q,ΔP) pairs, fit posterior, view ESS, round-trip into forward MC |
| M3-11 | Streaming monitor function | **FULL** (via M3-12) | — |
| M3-12 | CSV-replay UI | **FULL** | — |
| M3-13 | MonitorSource Protocol | **MISSING** | UI bypasses the abstraction; talks directly to `parse_csv`. No `SimulatedMonitorSource` training mode in UI. |
| M3-14 | Multi-column series | **MISSING** | No UI for `MultiColumnGeometry` or series envelope display |
| M3-15 | LRM breakthrough | **FULL** | — |
| M3-16 | Gradient elution | **FULL** | — |
| M3-17 | Loaded-state Protein A elution | **FULL** | — |
| O-1 | BoTorch optimization | **PARTIAL** | M1 targets section exists; full BO run UI orchestration unclear |
| O-2 | Pressure-feasibility constraint | **MISSING** | `PressureFeasibilityContext` and multi-step variant not wired into the optimization-side UI |
| C-1 | Wet-lab YAML ingestion | **PARTIAL / UNCLEAR** | Two generic file uploaders exist (`panels/calibration.py:42`, `shell/stage_panels.py:387`); neither is clearly labelled as the `wetlab_ingestion` campaign path |
| C-2 | PosteriorSamples loader | **MISSING** | No UI to load a posterior into the MC pipeline |
| C-3 | Bayesian Langmuir fit | **MISSING / UNKNOWN** | Optional extra; no obvious UI surface |

**Verdict counts.** FULL = 13. PARTIAL = 5. MISSING = 14. MISALIGNED = 0 (none caught — all hits are MISSING outright rather than misaligned). UNKNOWN = 1.

---

## §4 Conflicts and outdated elements

### C1 — Mobile-phase composition has no UI input (CRITICAL)

**Where:** `tabs/tab_m3.py` instantiates `MobilePhase()` with defaults at line 1002 and the lifecycle orchestrator does the same at the post-M2 wire-in. The only UI path for editing `T_C`, `c_nacl_M`, `phi_glycerol`, `phi_ethanol`, or `custom_mu_pa_s` is `pages/reagent_detail.py:56` (a per-reagent T slider — not the operating buffer). **No M3 / lifecycle / recipe-form widget exposes the operating mobile-phase composition.**

**Why critical:** ADR-005 anchors elution physics to (T, c_NaCl, glycerol, ethanol). The v0.7 viscosity model in `core/viscosity.py` covers the full water-T table 0–80 °C and additive corrections to ~500 mM NaCl, ~50 % glycerol/ethanol. A user changing T or salt has no UI path; the pre-flight envelope silently uses 25 °C / 150 mM PBS-equivalent regardless of recipe intent.

### C2 — Isotherm selector exposes only base Langmuir + competitive Langmuir

**Where:** `tabs/tab_m3.py:360–377` shows q_max + K_L sliders. Gradient elution at line 658+ uses `CompetitiveLangmuirIsotherm`. None of the four v0.8.1 / v0.8.2 isotherm adapters (M3-3, M3-4, M3-5, M3-6) is selectable.

**Why:** The M3 backend supports IEX, IMAC, full SMA, multi-component IEX with per-ν shifts. The UI cannot route the user into any of these. A user wanting to screen an IEX gradient against a salt-modulated isotherm has to drop to Python.

### C3 — Forward MC envelope has no UI surface

**Where:** `monte_carlo_pressure_envelope` is referenced 0 times under `src/dpsim/visualization/`. There is no button, no panel, no advisory chip displaying `p_blocker`.

**Why critical:** The README and ADR-007 explicitly recommend running forward MC near the headroom band and treating `p_blocker > 0.05` as a strong signal. The UI cannot deliver this advisory because it has no MC trigger.

### C4 — Inverse Bayesian inference has no UI surface

**Where:** `infer_posterior_envelope`, `MeasuredPressureFlowPoint` referenced 0 times under viz. The wet-lab loop documented in the README ("upload measured (Q,ΔP) → fit posterior → round-trip log_cov into forward MC") is unreachable from the UI.

**Why:** v0.8.3 / ADR-010 ships the machinery; the README points at it as the canonical wet-lab handshake. Without a UI surface, the handshake exists in name only.

### C5 — Multi-column series envelope has no UI surface

**Where:** `compute_multi_column_envelope`, `MultiColumnGeometry` referenced 0 times under viz. ADR-009 ships series aggregation; users wanting capture+polish or two-stack series operations cannot represent that geometry from the UI.

### C6 — Calibration-store ingestion path is unclear in the UI

**Where:** Two file uploaders exist (`panels/calibration.py:42`, `shell/stage_panels.py:387`) but no label or workflow makes clear which (if either) is the `wetlab_ingestion.py` YAML-campaign path that promotes K_geom from SEMI_QUANTITATIVE → CALIBRATED_LOCAL.

**Why:** This is the headline tier-promotion path of the entire system. Without a clear UI affordance the user cannot promote tiers from inside the dashboard.

### C7 — `MonitorSource` Protocol abstraction not surfaced; no simulator/training mode

**Where:** `tabs/tab_m3_monitor.py` calls `parse_csv` and `replay` directly (line 200–207). The `MonitorSource` typing.Protocol and the `SimulatedMonitorSource` (operator-training synthetic stream) are not wired.

**Why:** ADR-008 defines the abstraction precisely so a future v0.9 UNICORN backend can drop in. Today a junior researcher cannot select a synthetic source for training without dropping to Python.

### C8 — `plots_m2.py` surface-area chart bypasses tier-gating policy

**Where:** `plots_m2.py:136` writes the tier into a chart title via f-string interpolation, and at `plots_m2.py:144–146` adds a free-form `"Trust:"` annotation. Neither routes through `render_decision_grade_annotation`. This is the M2 analogue of W-037 / W-035 that was deferred at v0.8.2 §"Out of scope".

### C9 — No per-rule `RecoveryAction` breakdown in the UI; only the final-state chip is shown

**Where:** `tab_m3_monitor.py` surfaces the **final** `RecoveryAction` after replay completes. The seven-rule taxonomy (HEADROOM / DPDT / MODEL_DEVIATION / SPIKE × WARNING/BLOCKER) is not exposed; the user cannot see which rule fired at which timestamp during replay.

### Stale / deprecated references — none

`max_safe_flow_rate` has one source-file occurrence in `plots_m3.py:663` — a docstring deprecation note, not a runtime call. Clean.

---

## §5 Scientific-workflow coherence

### What the junior-researcher path looks like today

A new user opens the dashboard and meets a coherent screening narrative through the first six steps:

1. **M1 family selector** → `polymer_family` set (v9.0 contract enforced).
2. **M1 hardware** → animation appears; reasonable defaults.
3. **M1 run** → DSD + tiers visible.
4. **M2 sequence** → reagent dropdowns filtered by family; FSM visualisation makes the chemistry order legible.
5. **M3 column + flow rate** → pre-flight envelope panel renders; the user sees u_crit, Q_max, headroom, and a green/amber/red status chip.
6. **M3 breakthrough** → DBC values render with their tier badges.

This is good. Through step 6 the user has built a tier-aware mental model and seen a complete first-order screening result.

### Where the path dead-ends

After step 6 the user typically wants one of three things:

- **"Is this risky?"** — they want forward Monte Carlo bands and a `p_blocker` tail probability. **The UI offers no path.**
- **"Can I make this prediction tighter?"** — they want to upload measured Q-vs-ΔP data and see a posterior K_geom. **The UI offers no path.**
- **"Can I run this as a series with my polishing column?"** — they want multi-column envelope. **The UI offers no path.**

Each of these is documented in the README as a v0.8.3 capability. Each is reachable only from Python. The handshake from "screen → calibrate → tighten" — the central editorial promise of the new README — is **only half-implemented in the UI**.

### Tier and hazard surfacing

Tier badges are surfaced consistently in M1 / M2 metrics and in the M3 breakthrough panel. Hazard classes from the reagent library are surfaced via the family-filtered M2 dropdowns. **However**, the SEMI_QUANTITATIVE INTERVAL framing that the v0.8.x CHANGELOGs treat as canonical communication is not surfaced as a top-of-page banner — a junior user could scroll past several panels before realising every value is at INTERVAL precision until calibration is loaded.

The README explicitly forbids the word "validated" in any communication unless the calibration store has been loaded. The dashboard does not enforce or surface this guardrail at all — a screenshot-grabbing user could publish a "DPSim says DBC₁₀ = 42.3 mol/m³" claim without seeing the tier caveat.

### "What do I do next" affordance

There is no in-UI guidance after the lifecycle run completes. A junior researcher who has reached the M3 breakthrough panel has no on-screen prompt to:

1. Try forward MC to estimate `p_blocker`.
2. Upload AKTA pressure-flow data to fit a posterior K_geom.
3. Re-run with the calibrated K_geom to get tighter predictions.

These are the three obvious next steps and the dashboard surfaces none of them as affordances.

### v0.9 candidate hooks — none prematurely exposed

- Live AKTA UNICORN socket — no UI hook; ADR-008 deferral is honoured.
- Cyclic SMB dynamics — no UI hook; ADR-009 deferral is honoured.
- MCMC inverse — no UI hook; ADR-010 promotion target deferral honoured.
- Hierarchical multi-column inference — no UI hook.

The UI does not prematurely expose any v0.9 backend that is not yet implemented. This is correct.

---

## §6 Summary defect catalogue (input to /architect Phase 2)

| Defect | Category | Severity | Backend ref | UI ref |
|---|---|---|---|---|
| C1 | Mobile-phase composition not editable | **CRITICAL** | ADR-005, `core/mobile_phase.py`, `core/viscosity.py` | `tabs/tab_m3.py` (no widget) |
| C2 | Salt/imidazole/SMA isotherm adapters not selectable | **HIGH** | M3-3, M3-4, M3-5, M3-6 | `tabs/tab_m3.py:360-377` |
| C3 | Forward MC envelope + p_blocker advisory not exposed | **HIGH** | M3-7, ADR-007, ADR-011 | (no UI surface) |
| C4 | Inverse Bayesian inference not exposed | **HIGH** | M3-10, ADR-010 | (no UI surface) |
| C5 | Multi-column series envelope not exposed | **MEDIUM** | M3-14, ADR-009 | (no UI surface) |
| C6 | Calibration-store ingestion path unclear | **HIGH** | C-1 | `panels/calibration.py:42` (unlabelled) |
| C7 | MonitorSource Protocol + SimulatedMonitorSource not surfaced | **MEDIUM** | M3-13, ADR-008 | `tabs/tab_m3_monitor.py` (bypasses Protocol) |
| C8 | plots_m2.py surface-area chart not tier-gated | **LOW** | render_decision_grade_annotation | `plots_m2.py:136, 144–146` |
| C9 | No per-rule RecoveryAction breakdown / timeline | **LOW** | `pressure_monitor.py::PressureMonitorRule` | `tabs/tab_m3_monitor.py` (final-state only) |
| W-1 | No top-of-page SEMI_QUANTITATIVE banner | **MEDIUM** | CHANGELOG framing | `app.py` (no top banner) |
| W-2 | No "next-step" affordance after lifecycle completes | **MEDIUM** | UX-only | (post-M3 area in app.py / shell) |

---

## §7 Hand-off note to /architect (Phase 2)

The defect catalogue in §6 is input. /architect should produce: (a) module decomposition for the upgraded UI — which new tabs/panels, which existing panels gain widgets, where the cross-tab state lives; (b) signature contracts for the new MC / inverse / multi-column / mobile-phase / isotherm-selector components; (c) a six-dimension audit verdict on the existing visualization surface (correctness / completeness / modularity / scalability / maintainability / scientific provenance); (d) integration-seam map to current `tab_m3.py` and `tab_m3_monitor.py`. /dev-orchestrator (Phase 3) consumes /architect's output and produces the W-numbered batched work plan.

The most important architectural question /architect must resolve is **whether the new MC/inverse/multi-column work belongs as additional sections inside `tab_m3.py` or as new top-level tabs**. The current `tab_m3.py` is 1198 lines and adding four more sections will be unwieldy.

---

> **Disclaimer**: This audit is provided for informational, research, and advisory purposes only. It does not constitute formal code review or architectural sign-off. All recommended UI changes should be reviewed by the project's UI/UX owner under DESIGN.md compliance and validated by qualified domain users (junior chromatography researchers + wet-lab operators) before being treated as canonical. The author is an AI assistant and the analysis should be treated as a structured starting point for the subsequent /architect and /dev-orchestrator phases.
