# AUDIT — v0.8.5 end-to-end practitioner walkthrough (Phase 2)

> **Role**: /dev-orchestrator — acting as a discerning, demanding wet-lab practitioner who relies on DPSim to plan and de-risk bench operations.
> **Date**: 2026-05-10 · **Audit scope**: a real-user walkthrough of every dashboard surface at v0.8.5.
> **Companion documents**: Phase 1 scientific (`AUDIT_v0_8_5_e2e_phase1_scientific.md`), Phase 3 architecture (`AUDIT_v0_8_5_e2e_phase3_architecture.md`), joint plan (`update_workplan_2026-05-10_v0_9_0.md`).

---

## §0 — Verdict in one paragraph

A bench scientist firing up DPSim v0.8.5 for the first time encounters a dashboard whose surfaces look mature and whose READMEs promise a coherent *screen → calibrate → tighten* loop, but who in practice cannot operate the simulator at the level of fidelity their wet-lab work demands. They cannot enter the buffer their actual run uses. They cannot pick the isotherm class their actual binding regime warrants. They cannot see the global tier banner that would tell them how much to trust each number. They cannot ask the simulator *"with my actual reagents and constraints, what flow rate / column / ligand density should I try?"* — the optimization engine that answers this question is invisible from the dashboard. The numerical machinery exists; the operator-facing chain to drive it does not. Ten lower-leverage but real friction points — unit chaos, no first-run wizard, no SOP export, no run-comparison view, no in-app calibration editor — compound to make the simulator feel like a research tool rather than a wet-lab planner.

The cumulative effect is that a *demanding* user reaches the conclusion *"the dashboard works, but it isn't telling me my truth"* by the second or third session. This is the audit's central practitioner finding: **DPSim's wet-lab-credibility floor is gated by half-a-dozen wiring fixes and one IA reorganisation**, not by missing science.

---

## §1 — Walkthrough scenario

I will narrate the audit as a single end-to-end walkthrough, assuming the role of an antibody-purification process scientist with bench data on a pilot ProteinA / agarose-chitosan affinity column. The scenario:

> *"I have 5 g/L of crude IgG in PBS, want to load onto a 10×100 mm AGAROSE_CHITOSAN column packed with my 90 µm beads, run the established 6 mM citric-acid step elution, and predict load capacity, breakthrough sharpness, and whether my flow rate will compress the bed."*

Below, each subsection follows what I encounter on each dashboard surface, with friction findings prefixed `U-N`.

---

## §2 — First-run experience

### U-1 · No first-run example or guided wizard

I open <http://localhost:8501>. I see a sidebar with *"Global Settings"* and a *"Calibration"* section. I see tabs / stages laid out per the v0.8.4 IA. There is **no example recipe loader, no "demo with sample data" button, no first-run wizard**. The README's "screen → calibrate → tighten" promise is operationalised in the docs but not in the IA. I have to read the user manual to know which stage to click first.

**Severity**: HIGH for adoption; MEDIUM for repeat users.

### U-2 · "Scientific Mode" radio (empirical / hybrid / mechanistic) is undocumented at the point of use

The top-bar segmented control offers three "Scientific Mode" options. As a first-time user I have no idea what each one toggles. There is a tooltip but it does not explain consequence. *Should I default to mechanistic? Will hybrid hide some of my results?* The README mentions ModelMode but the dashboard does not surface the consequence-on-rerun. The mode switches require a Streamlit rerun (per `app.py:380` URL-param routing); this is fragile when I have unsaved entries elsewhere on the page.

**Severity**: MEDIUM.

---

## §3 — M1 (fabrication) surface

### U-3 · M1 polymer-family selection is good — and I can tell

The Family-First contract pays off. Selecting `AGAROSE_CHITOSAN` correctly hides crosslinker / cooling-rate widgets that don't apply to other families. The `family_selector.py` + 6 family-specific formulation files are the right decomposition. **Pass.**

### U-4 · M1 outputs (G_DN, E_star, mean d50) ship without obvious tier framing

After running M1 I see numerical outputs for the modulus and bead size. Whether each is at SEMI_QUANTITATIVE or CALIBRATED_LOCAL is not next to the number — I have to look at the validation ladder in the Calibration stage to find out. A wet-lab user wants the tier badge **next to the number**, every time.

**Severity**: MEDIUM.

### U-5 · No calibration-store entry promotes M1's tier per-family

If I have wet-lab measurements of `eta_chit` from my own bench, the calibration protocol says I can promote the tier. But the in-dashboard YAML ingestion is in a different tab (Calibration) and the link from M1 → "I have data for this parameter" is missing.

**Severity**: MEDIUM.

---

## §4 — M2 (functionalization) surface

### U-6 · M2 reagent-matrix is family-aware — good — but the EDC/NHS sub-form is generic

The reagent matrix correctly restricts options per family per the v0.8.x ACS work. However, the EDC molar-excess + reaction-time + temperature inputs do not differentiate between the chemistries my actual lab uses (e.g. EDC/sulfo-NHS vs DMTMM vs CDI). I'm forced to map my real protocol to the simulator's idealised form.

**Severity**: MEDIUM.

### U-7 · M2 result fields (ligand density, surface coverage) are not surfaced at the M3 input as confirmation

When I move to M3, the column-geometry section reads `_m2r_bt = st.session_state["m2_result"]` (per `tab_m3.py:1040`) and constructs the column from M2's output. The user is **not shown** *"the column you are about to run uses ligand density X / surface area Y from your M2 result"* — this is implicit. A wet-lab user wants the chain to be visible: *here is what your M1 produced, here is what your M2 added on top, here is the column geometry you'll pack, here is what your M3 will load*.

**Severity**: MEDIUM.

---

## §5 — M3 (chromatography) surface — the audit's largest cluster

### U-8 · I cannot enter my mobile phase

This is the audit's most consequential finding. My run uses **PBS at load** then **6 mM citric acid pH 3.5 at elute**. The dashboard offers no widget to enter mobile-phase composition. The pre-flight envelope and the LRM transport simulation both proceed with `MobilePhase()` — water at 20 °C — silently substituting μ_water for the actual elute viscosity. The pressure indicator's GREEN colour is therefore unreliable (see Phase 1 §S-1).

**Severity**: CRITICAL.

### U-9 · I cannot pick my isotherm class

My binding regime is **ProteinA / IgG**. The dashboard offers no isotherm selector. The simulator silently uses Langmuir (the AGAROSE_CHITOSAN family default). The breakthrough sharpness it returns is therefore a Langmuir prediction, not a ProteinA prediction. I have no way to override it.

**Severity**: CRITICAL.

### U-10 · No global tier banner

I expect a coloured banner at the top of every stage telling me *"your active model tier is SEMI_QUANTITATIVE — calibration required for decision use"*. There isn't one (per Phase 1 §S-3). I have to remember the tier per metric.

**Severity**: HIGH.

### U-11 · Pre-flight pressure envelope is post-Run

I press *Run* with my flow rate. The simulation runs for 90 s. *Then* the pressure envelope panel renders and tells me my Q exceeds Q_max. **I want this BEFORE I press Run.** Per ADR-004 it is a pre-flight check; in the dashboard it is a post-flight verdict.

**Severity**: HIGH.

### U-12 · Pressure indicator (v0.8.5) is well-placed but not interactive

The new digital readout next to the column diagram is a clear UX win. However, when it goes RED I want a button: *"set my flow rate to Q_recommended"*. There is no such button. I must scroll down, find the flow-rate widget, and re-enter the value. The recovery actions in the streaming-monitor expander likewise are text labels with no UI control hooks.

**Severity**: MEDIUM.

### U-13 · I cannot see the UV / conductivity / fluorescence trace

My wet-lab UNICORN run produces UV280, conductivity, and (sometimes) fluorescence traces. DPSim's M3 result page shows breakthrough vs effluent concentration. The detector traces are what I'd actually compare against on the bench (per Phase 1 §S-6). The chain breaks at the comparison step.

**Severity**: HIGH.

### U-14 · The "next steps" affordance points to Calibration but doesn't carry context

After a run completes, the v0.8.4 next-step strip offers *Run forward MC / Fit posterior / Build series geometry*. Clicking *Fit posterior* takes me to the Calibration tab — but the data editor there is empty, so I have to enter my measurements from scratch. The cross-tab jump should pre-populate from the run I just executed.

**Severity**: MEDIUM.

---

## §6 — Calibration & Uncertainty surface

### U-15 · Forward MC is properly wired — good — but advisory only on `p_blocker`

The forward MC panel surfaces `p_blocker` against the 3-band threshold. It does not, however, tell me *what to change* to reduce `p_blocker` from RED to AMBER — *increase column ID? lower flow? reduce particle size?* A demanding user wants the advisory to be actionable.

**Severity**: MEDIUM.

### U-16 · Inverse Bayesian runs on insufficient data without blocking

The data editor accepts as few as 1 measurement. The fit runs, the ESS chip eventually warns post-hoc. As a wet-lab user I would prefer an input-time blocker: *"3 measurements is insufficient for posterior — please supply ≥ 8 or upgrade to MCMC"*.

**Severity**: HIGH (this lets users mistake noise for posterior).

### U-17 · The "round-trip log_cov into forward MC" button is hidden in a sub-tab

The closing of the Bayesian loop is the simulator's most differentiating feature. It is buried behind two clicks (Calibration tab → Inverse posterior sub-tab → button). The discoverability is poor.

**Severity**: MEDIUM.

### U-18 · Multi-column series builder is in the Calibration tab — wrong IA

This is a design-time tool (*"will my Capto + MMC pair be bottlenecked by the second column?"*) not a calibration activity. Placing it in the Calibration tab implies it requires a calibration step. It should be either a top-level *Series Design* stage or a sub-section of M3.

**Severity**: LOW.

### U-19 · Wet-lab YAML ingestion has no in-app editor; bench-spreadsheet import path is missing

To promote a parameter to CALIBRATED_LOCAL I must hand-author YAML with the right schema. A typical bench user has Excel or CSV. There is no *"upload your spreadsheet, map the columns"* path.

**Severity**: HIGH.

---

## §7 — Optimization (missing surface entirely)

### U-20 · I cannot ask the simulator to design my run

*"Given my IgG target capacity 25 g/L resin, breakthrough sharpness ≥ 80 %, and pressure budget 5 bar — find me the column geometry and flow that meets all three."* This is the highest-value question a simulator can answer. The OptimizationEngine in `src/dpsim/optimization/engine.py` can answer it. The dashboard cannot invoke it (per Phase 1 §S-7). The CLI can, but a bench user does not learn the CLI.

**Severity**: HIGH.

---

## §8 — Streaming monitor (offline replay)

### U-21 · CSV upload works — good — but no live feed scaffold

The replay path (per v0.8.0 W-032 + v0.8.4 W-062 timeline ribbon) is sound. However, the ADR-008 MonitorSource Protocol exists for live-feed support and the dashboard exposes none of it (per Phase 1 §S-8). Even a simulated-feed mode for demos would be useful.

**Severity**: MEDIUM.

### U-22 · No comparison overlay between predicted and measured

After uploading my UNICORN trace, I see the measured ΔP overlaid on the operational threshold. I do **not** see the *predicted* ΔP from the simulator alongside it. The comparison — the simulator's most operationally valuable view — has no path.

**Severity**: HIGH.

### U-23 · Recovery actions are labels — no UI control linking

`tab_m3_monitor.py:50-58` defines text labels: *"reduce flow to Q_recommended"*, *"switch to wash buffer"*. None of these are clickable controls that change the simulator state.

**Severity**: MEDIUM.

---

## §9 — Cross-cutting friction

### U-24 · Unit chaos at user-input boundaries

* Q is mL/min on some widgets, m³/s on others, L/h elsewhere.
* ΔP shows in Pa, kPa, bar across panels.
* Concentrations: mg/L, mol/m³, mM in different sub-forms.

A bench user has to know each conversion. One fat-finger mis-entry (mL/min vs m³/s — 10⁸×) silently breaks the simulation.

**Severity**: HIGH.

### U-25 · No "save my session" / "load my previous run"

Streamlit's session_state is the only persistence. Refreshing the page resets everything except the legacy uploaded YAML. There is no *"snapshot this run, restore later"* affordance. A user who came back to the dashboard the next day cannot pick up where they left off.

**Severity**: HIGH.

### U-26 · No SOP / wet-lab procedure export

I would pay good money for a *Generate wet-lab SOP PDF* button that turns the configured recipe + envelope + isotherm choice + calibration store + uncertainty bands into a procedure document I can take to the bench. No path exists.

**Severity**: HIGH.

### U-27 · No run-vs-run comparison view

I configured run A and run B. I want to overlay them. The dashboard does not support this; each run replaces the previous in `lifecycle_result`.

**Severity**: MEDIUM.

### U-28 · Help text promises behaviour that the code does not actually do

(Per Phase 1 §S-1, S-2, S-3 — the v0.8.4 widgets that are unmounted in production but advertised in the CHANGELOG.)

**Severity**: HIGH (it erodes trust).

### U-29 · No dose-bound advisor for the calibration ladder

When my parameter is at SEMI_QUANTITATIVE the dashboard tells me what tier I'm at but not *what specific experiment* would promote me to CALIBRATED_LOCAL. The calibration protocol document `docs/04_calibration_protocol.md` lists studies; the IA does not surface this from the parameter.

**Severity**: MEDIUM.

### U-30 · No reagent ↔ ADR ↔ tier traceability per output

The dashboard does not surface, for any displayed output, *which calibration source* drove its tier. I have to read the ADRs to know.

**Severity**: LOW.

---

## §10 — What works well (don't regress)

To keep the v0.9 maturation honest, here is what already meets a demanding wet-lab user's bar at v0.8.5:

* **Family-First UI contract** — when correctly applied, the cross-family widget hiding is exactly right.
* **Resin lifetime panel** — well-placed at `tab_m3.py:289`, well-documented, tier-honest.
* **Forward MC** with `p_blocker` 3-band advisory chip — the chip is the right kind of operator-facing surface.
* **Pressure indicator** (v0.8.5) — colour-coded digital readout at the column diagram is the right pattern; once the help-modal popover gives the calculation, the pattern is wet-lab-credible.
* **The decision-grade tier ladder** as a primitive — the right substrate; the gap is in consistent application.
* **Calibration store + ingestion path** — when properly wired (`tab_calibration.py:156`), the YAML uploader with tier-promotion preview is exactly the right surface.
* **AST gate** for enum comparison — the right kind of CI guardrail.
* **The README's editorial promise** — *screen → calibrate → tighten* — is the right framing once the chain is operationally testable.

---

## §11 — Severity ranking — top 10 friction points

By practitioner-impact (the user's likelihood to reach for a different tool):

| Rank | ID | Title | Severity | Phase |
|---|---|---|---|---|
| 1 | U-8 | Cannot enter mobile phase | CRITICAL | v0.8.6 |
| 2 | U-9 | Cannot pick isotherm class | CRITICAL | v0.8.6 |
| 3 | U-20 | Cannot run optimization from dashboard | HIGH | v0.8.7 |
| 4 | U-13 | No detector traces in M3 results | HIGH | v0.8.7 |
| 5 | U-22 | No predicted-vs-measured ΔP overlay | HIGH | v0.9.0 |
| 6 | U-26 | No SOP / wet-lab procedure export | HIGH | v0.9.0 |
| 7 | U-25 | No save-session / load-previous-run | HIGH | v0.9.0 |
| 8 | U-19 | No spreadsheet → calibration store import | HIGH | v0.9.0 |
| 9 | U-11 | Pre-flight envelope is post-Run | HIGH | v0.9.0 |
| 10 | U-24 | Unit chaos at user-input boundaries | HIGH | v0.9.0 |

---

## §12 — Wet-lab-credibility verdict

A demanding bench user at v0.8.5 reaches the verdict *"the dashboard looks mature, but the central physical knobs that drive my real-world prediction (mobile phase, isotherm) are silently overridden — and the dashboard cannot tell me what conditions would meet my targets"*. The simulator is **operationally inert** for actual lab planning until the wiring fixes in v0.8.6 land. With those fixes plus the v0.8.7 orphan exposure, the dashboard reaches *minimum wet-lab-credible*. The v0.9 maturation work makes it *wet-lab-preferred*.

---

## §13 — Disclaimer

This walkthrough was conducted by a /dev-orchestrator role acting as a discerning bench user, based on static code reads of the v0.8.5 tagged commit. Some items may be context-dependent (e.g. specific to one polymer family, one binding mode). Where applicable, the joint plan validates each finding by first reproducing the friction in a real Streamlit session before committing to a fix.
