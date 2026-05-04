# Polysaccharide-Based Microsphere Emulsification Simulator — First Edition

**Edition:** 2.0 (covers Downstream Processing Simulator v0.3.6)
**Date:** 2026-04-25
**Audience:** Downstream-processing technicians, junior R&D researchers, and first-time users of the DPSim platform.
**Status:** Active operating manual. Supersedes Edition 1.1.

---

## How To Use This Manual

This document is written for someone who has never made a polysaccharide microsphere or run a process simulator. You are assumed to have college-level chemistry, the ability to follow a written wet-lab protocol, and basic comfort with a computer terminal. No prior experience in emulsification, hydrogel chemistry, chromatography, or numerical modelling is required.

The manual is built in three concentric layers, so you can read only as deep as you need:

| Layer | Section | Time | When to read |
|---|---|---|---|
| Layer 1 — Operator | Part I | 30 min | Before your first run |
| Layer 2 — Selector | Part II | 1 hour | When designing a new recipe |
| Layer 3 — Reference | Part III (Appendix) | as needed | Troubleshooting, audit, deep-dive science |

If you only have ten minutes, read **§ 1 (What the Simulator Does)** and **§ 3 (Five-Minute Quickstart)**, then come back later. If you only have twenty seconds, read the next paragraph.

> **What this is.** DPSim turns a written lifecycle recipe into predicted microsphere-media behavior before you touch the bench. You describe what you want to make and how. DPSim tells you what to expect — bead size, pore structure, modulus, ligand density, breakthrough behavior, pressure drop, and uncertainty — with explicit assumptions, evidence tier, and wet-lab caveats.

---

## Table of Contents

- **Part I — Getting Started**
  - §1 What the Simulator Does
  - §2 Workflow Overview
  - §3 Five-Minute Quickstart
  - §4 Reading Results and Evidence Tiers
- **Part II — Platform Catalogue**
  - §5 Polymer Family Selection
  - §6 M2 Chemistry Catalogue
  - §7 M3 Method and Uncertainty Bands
  - §8 Calibration and Wet-Lab Loop
  - §9 CFD-PBE Zonal Coupling for M1 Scale-up
- **Part III — Appendix (Reference)**
  - A. Detailed Input Requirements
  - B. Process Steps
  - C. Essential Input & Process Checklist
  - D. Frequently Asked Questions
  - E. Architectural Ideas and Working Principles
  - F. Chemical and Physical Principles
  - G. Formulas and Mathematical Theorems
  - H. Standard Wet-Lab Protocols (Cross-Reference)
  - I. Troubleshooting Table

---

# Part I — Getting Started

## §1 What the Simulator Does

The DPSim Downstream Processing Simulator is a multi-scale lifecycle simulator for affinity microsphere media. It models three process modules in sequence:

| Module | Wet-lab stage | Outputs |
|---|---|---|
| **M1** | Double-emulsification microsphere fabrication | Bead size distribution (DSD), d32/d50, pore architecture, mechanical modulus, residual oil/surfactant after wash |
| **M2** | Functionalisation, reinforcement, ligand coupling | Functional-site inventory, ligand density, activity retention, leaching/wash caveats |
| **M3** | Affinity-column performance | Pack/equilibrate/load/wash/elute method behaviour, breakthrough curve, pressure profile, dynamic binding capacity (DBC), recovery, optional Monte-Carlo uncertainty bands |

The current v0.3.6 simulator covers **21 selectable polymer families**, **96 M2 reagents** organised into **17 chemistry buckets**, **13 ion-gelant profiles**, and an optional **Monte-Carlo LRM uncertainty driver** that reports P05/P50/P95 envelopes on key chromatography metrics.

> **New in v0.6.0+:** an optional **CFD-PBE zonal coupling** path lets you replace M1's volume-averaged dissipation rate ε with a CFD-resolved, per-zone ε field (typically 3–4 compartments). This is the recommended path for 10× scale-up predictions and any mixer where breakage hotspots dominate (rotor-stators, stator-slot exits). See **§9** for when to use it and how.

### §1.1 Workflow at a glance

```
┌─────────────────────────────────────────────────────────────────┐
│                    Lifecycle Simulation Flow                     │
└─────────────────────────────────────────────────────────────────┘
   ┌──────────────┐    ┌─────────────┐    ┌─────────────┐
   │  Step 1      │ →  │  Step 2     │ →  │  Step 3     │
   │  Target      │    │  M1 recipe  │    │  M2 recipe  │
   │  product     │    │             │    │             │
   │  profile     │    │             │    │             │
   └──────────────┘    └─────────────┘    └─────────────┘
                                                  │
                                                  ↓
   ┌──────────────┐    ┌─────────────┐    ┌─────────────┐
   │  Step 7      │ ←  │  Step 6     │ ←  │  Step 4     │
   │  Calibration │    │ Validation  │    │  M3 column  │
   │  + wet-lab   │    │ + Evidence  │    │  method     │
   └──────────────┘    └─────────────┘    └─────────────┘
                              ↑                   │
                              │                   ↓
                       ┌──────────────┐    ┌─────────────┐
                       │  Step 5      │ ←  │ ProcessRecipe│
                       │  Run lifecycle│    │              │
                       │  simulation  │    │              │
                       └──────────────┘    └─────────────┘
```

Each step writes into a single in-memory `ProcessRecipe` object. The same object drives the UI, the CLI, the validation layer, and the lifecycle orchestrator — so what you see in the UI is exactly what runs.

### §1.2 What the simulator answers

**M1 (fabrication):**
- What will my bead size distribution be at a given RPM, polymer concentration, and surfactant load?
- What pore size and porosity will my gel have?
- Did my wash schedule reduce residual oil and surfactant below the screening limits I set?
- What modulus will the dry / wet bead have?

**M2 (functionalisation):**
- Will my functionalisation sequence preserve the required reactive-site and mass balance?
- What ligand density, activity retention, and leaching risk should I expect?
- Are my chosen reagents compatible with the polymer family I picked?

**M3 (column performance):**
- What breakthrough, pressure drop, and DBC trend should I expect under the defined method?
- Where in my parameter space am I — calibrated regime, screening regime, or out-of-domain?
- If I run Monte-Carlo uncertainty propagation, what are the P05 / P50 / P95 envelopes on mass eluted, DBC₁₀, and the breakthrough curve?

**Cross-cutting:**
- Which validation blockers, calibration-domain warnings, and wet-lab caveats apply to my run?
- What evidence tier is the weakest assumption in my pipeline?

### §1.3 What the simulator does not do

- It does not substitute for a regulatory tox / stability study.
- It cannot predict the behaviour of a polymer not in its family registry.
- It cannot predict what will happen above the validation regime of its input parameters — it warns you, but it does not refuse to run.
- It does not create a GMP batch record. The exported wet-lab protocol is a development SOP scaffold that must be reviewed under your local safety and quality systems.
- It does not prove a resin is fit for clinical, diagnostic, or manufacturing use without independent calibration, release assays, and process validation.

### §1.4 Trust-tier vocabulary (read before any result)

Every value DPSim reports carries an **evidence tier**. Internalise these five tiers before reading any result:

| Tier | Meaning | When to trust the value |
|---|---|---|
| `validated_quantitative` | Calibrated against the specific system you are running | Suitable for design within the validated domain |
| `calibrated_local` | Fitted to local wet-lab data; not yet broadly cross-validated | Suitable for screening and local interpolation |
| `semi_quantitative` | Literature-parameterised or mechanistically plausible, not locally calibrated | Trends are useful; magnitudes are approximate |
| `qualitative_trend` | Directional or ranking-only | Use for screening and hypothesis generation only |
| `unsupported` | Chemistry, unit, regime, or operation is not represented | **Do not use for decisions** |

The UI marks every reported value with its tier and shows the weakest evidence level across the lifecycle. M3 is never allowed to claim stronger evidence than the M2 media contract that supplies the ligand and site-balance basis. When in doubt, look for the colored badge next to the number.

---

## §2 Workflow Overview

The seven-step workflow is your operating contract:

1. **Target Product Profile.** Define what "success" means for this run: bead d50, pore size, minimum modulus, ligand identity, target analyte, maximum pressure drop, residual-oil and residual-surfactant screening limits.
2. **M1 Fabrication Recipe.** Define phase preparation, emulsification (stirred-tank or microfluidic), cooling/gelation, and wash schedule. Archive measured DSD quantiles if you have laser diffraction or microscopy data.
3. **M2 Chemistry Recipe.** Choose a staged functionalisation template, then edit activation, spacer insertion, coupling, blocking/quenching, washing, and storage-buffer exchange steps.
4. **M3 Column Method.** Define packing, equilibration, load, wash, and elution conditions: pH, conductivity, residence time, bed height, flow rate. (Optional: enable Monte-Carlo uncertainty propagation.)
5. **Run Lifecycle Simulation.** The orchestrator executes M1 → M2 → M3 against the active `ProcessRecipe`.
6. **Validation & Evidence.** Read blockers, warnings, the evidence ladder, scientific diagnostics, and wet-lab caveats.
7. **Calibration and Wet-Lab Comparison.** Compare simulated outputs with bench data and confirm whether the run is inside calibration domains.

The legacy per-module M1/M2/M3 tabs are still in the UI for narrow debugging, but the seven-step lifecycle is the authoritative workflow. **First-time users should never bypass the lifecycle workflow.**

---

## §3 Five-Minute Quickstart

### §3.1 Launching the UI

```bash
python -m dpsim ui
```

This starts the Streamlit dashboard at `http://localhost:8501`. If your browser does not open automatically, paste the URL into a local browser. The Manual PDF and the Appendix J protocol PDF are downloadable from the upper-right corner of the dashboard at any time.

### §3.2 Entering a minimal recipe

Use the workflow pages in order. Each page writes into the active `ProcessRecipe`:

1. **Target Product Profile** → bead d50, pore size, modulus floor, ligand, analyte, pressure ceiling, residual-oil and residual-surfactant screening limits.
2. **M1 Fabrication** → polymer family, formulation %, surfactant choice, RPM, T_oil, cooldown rate, wash schedule. Archive measured DSD if available.
3. **M2 Chemistry** → pick a staged template (e.g. `epoxy_protein_a`) or edit per step: chemistry bucket → reagent → concentration → temperature → time → pH.
4. **M3 Column Method** → column geometry, flow rate, bed porosity, feed concentration, method buffers, optional MC uncertainty (`monte_carlo_n_samples > 0`).
5. **Run Simulation** → execute the lifecycle orchestrator. Wall time depends on M1 family: agarose-chitosan ≈ 2 s, alginate ≈ 5 s, cellulose ≈ 30 s, MC-enabled ≈ minutes.
6. **Validation & Evidence** → inspect blockers (red), warnings (amber), evidence ladder, scientific diagnostics, and wet-lab caveats.
7. **Calibration** → upload measured DSD / DBC / pressure / leaching data; the calibration store applies overrides automatically.

> **First run, every time:** start from the default Protein A affinity-media recipe. It is conservative, well-validated, and intended for training.

### §3.3 Choosing a polymer family (CLI example)

```bash
python -m dpsim run configs/default.toml \
    --polymer-family alginate \
    --gelant cacl2_external
```

Lifecycle recipes use the recipe subcommands:

```bash
python -m dpsim recipe export-default --output recipe.toml
python -m dpsim recipe validate recipe.toml
python -m dpsim lifecycle configs/fast_smoke.toml --recipe recipe.toml --no-dsd
```

By default, runtime output is written under the per-user DPSim runtime directory rather than blocked system temp directories or fragile OneDrive paths. Override these locations when needed:

```bash
set DPSIM_TMPDIR=C:\Users\<you>\DPSimTemp
set DPSIM_OUTPUT_DIR=C:\Users\<you>\DPSimOutput
set DPSIM_CACHE_DIR=C:\Users\<you>\DPSimCache
```

### §3.4 Your first three runs

Do all three on day one before designing your own recipes:

1. **Run the default recipe.** Agarose-chitosan at 8000 RPM, genipin crosslinker, 24 h cure. Study the validation report and the evidence ladder.
2. **Double the RPM.** Observe how `d32` drops roughly as RPM⁻¹·²⁰ — this is Kolmogorov-scaling intuition (see Appendix G).
3. **Export and run the lifecycle default recipe.** Inspect how the M1 DSD, M2 Protein A coupling contract, and M3 column method combine into one validation/evidence report.

After these three runs you are equipped to design your own recipe.

---

## §4 Reading Results and Evidence Tiers

The lifecycle UI reports four kinds of output. Read them in this order every time:

### §4.1 M1 results

- **Bead DSD summary** — d10, d32, d50, d90 with span and modality.
- **DSD quantile curve** — the binned cumulative distribution. Compare visually against any archived measured DSD.
- **Pore and modulus estimates** — pore size mean / std, porosity, G_DN modulus, E* effective modulus.
- **Residual carryover** — oil and surfactant remaining after the wash schedule.

### §4.2 M2 results

- **Functional-site inventory** — site balance (ACS state vector) and reactive-site density.
- **Ligand density** — coupled mass per volume, plus side-reaction and hydrolysis caveats.
- **Activity retention** — fractional retention of the ligand's binding activity post-coupling.
- **Wet-lab assay requirements** — ligand leaching, free-protein wash fraction, hydrolysis-watch caveats.

### §4.3 M3 results

- **Method summary** — every pack / equilibrate / load / wash / elute step with timings and buffer compositions.
- **Breakthrough curve** — C/C₀ vs time at the column outlet.
- **Pressure profile** — operability check against the pump-side limit and the method-target ceiling.
- **DBC and recovery** — DBC₅, DBC₁₀, DBC₅₀, recovery fraction, mass-balance error.
- **Optional MC uncertainty bands** — when `monte_carlo_n_samples > 0`, the P05 / P50 / P95 envelope plot appears with a footer noting the SA-Q4 / SA-Q5 modelling assumptions and the convergence diagnostics.

### §4.4 Cross-cutting views

- **Validation report** — blockers (red, must-fix-before-running), warnings (amber, watch-out), passes (green).
- **Evidence ladder** — the weakest evidence tier reached anywhere in the pipeline. M3 inherits a cap from M2, and M2 inherits a cap from M1.
- **Scientific diagnostics** — Reynolds, Peclet, Thiele, mass-balance closure, calibration-domain status.
- **Wet-lab SOP draft** — a development-grade SOP scaffold pulled from Appendix J's reagent-level protocols.
- **Calibration overlay** — measured-vs-simulated overlay panels for any wet-lab data you have uploaded.
- **Run history** — every run from this session is preserved with its `ProcessRecipe`, hash, evidence tier, and timestamp.

> **Before making any recipe decision, confirm the evidence tier of the specific value you are using.** If the value is `qualitative_trend` or `unsupported`, do not use it for a quantitative decision. Run a wet-lab assay first.

---

# Part II — Platform Catalogue

DPSim supports **21 polymer families**, organised into a v9.1 baseline (4 platforms), a v9.2/v9.3 expansion (10 platforms), a v9.4 niche set (4 platforms), and a v9.5 multi-variant composite set (3 platforms). Each platform has a different gelation mechanism, different suitable crosslinkers / gelants, and different typical applications.

This section is your "which do I pick?" guide.

## §5 Polymer Family Selection

### §5.1 Baseline (v9.1) — choose one of these for your first runs

| Family | Mechanism | Best for | Default crosslinker / gelant |
|---|---|---|---|
| **AGAROSE_CHITOSAN** | Thermal helix + amine bridge | Rigid chromatography beads (default platform) | Genipin |
| **ALGINATE** | Ca²⁺ ionic egg-box | Mild encapsulation, room-T | CaCl₂ external bath |
| **CELLULOSE** | NIPS phase separation | Bicontinuous high-porosity scaffolds | NaOH/urea (default) |
| **PLGA** | Solvent evaporation | Drug-delivery, bioresorbable | DCM/PVA |

### §5.2 Expansion (v9.2 / v9.3 Tier-1 and Tier-2)

| Family | Mechanism | Notes |
|---|---|---|
| **AGAROSE** | Pure thermal helix-coil | Sepharose-class baseline |
| **CHITOSAN** | pH-dependent amine protonation | Acid-solubilised droplet path |
| **DEXTRAN** | ECH-crosslinked α-glucan | Sephadex-class SEC matrix |
| **AMYLOSE** | Material-as-ligand for MBP-tag (B9 pattern) | Eluted by 10 mM maltose |
| **HYALURONATE** | Covalent BDDE / HRP-tyramine | High-swelling polyelectrolyte |
| **KAPPA_CARRAGEENAN** | K⁺-specific helix aggregation | Niche chromatography support |
| **AGAROSE_DEXTRAN** | Core-shell composite | Industrial Capto-class media |
| **AGAROSE_ALGINATE** | IPN, thermal + Ca²⁺ orthogonal | ~30% G_DN reinforcement |
| **ALGINATE_CHITOSAN** | PEC shell on alginate skeleton | pH-dependent stability 5.5–6.5 |
| **CHITIN** | Material-as-ligand for CBD/intein | NEB IMPACT system |

### §5.3 Niche (v9.4 Tier-3, research-mode)

| Family | Mechanism | Why niche |
|---|---|---|
| **PECTIN** | Galacturonic-acid Ca²⁺ ionic | DE-dependent; food/drug-delivery dominant |
| **GELLAN** | K⁺/Ca²⁺ helix aggregation | Food provenance; weaker than κ-carrageenan |
| **PULLULAN** | Neutral α-glucan (ECH/STMP) | Drug-delivery dominant |
| **STARCH** | Neutral α-glucan, porous | Gelatinization / amylase-degradation risk |

### §5.4 Multi-variant composites (v9.5 Tier-3)

| Family | Mechanism | Useful for |
|---|---|---|
| **PECTIN_CHITOSAN** | Pectin Ca²⁺ skeleton + chitosan PEC shell | pH-controlled drug release |
| **GELLAN_ALGINATE** | Dual ionic-gel; alginate dominant + ~20% gellan reinforcement | Food / texture systems |
| **PULLULAN_DEXTRAN** | Neutral α-glucan composite | Drug-delivery |

### §5.5 Polymer family selection chart

```
┌─────────────────────────────────────────────────────────────────┐
│                  Polymer Family Selection Chart                  │
└─────────────────────────────────────────────────────────────────┘

Q1: Do you need high modulus (>500 kPa) and full chromatography?
    ├─ YES → AGAROSE_CHITOSAN (default) or AGAROSE_DEXTRAN (Capto-class)
    └─ NO →  Q2

Q2: Is the application biotherapeutic?
    ├─ YES → Q3
    └─ NO →  PLGA (drug-delivery) or PECTIN (food)

Q3: Is room-T / mild processing required?
    ├─ YES → ALGINATE / CHITOSAN / HYALURONATE
    └─ NO →  AGAROSE / DEXTRAN / CELLULOSE

Q4: Is there a fusion-tag affinity requirement?
    ├─ MBP-tag → AMYLOSE (material-as-ligand)
    ├─ CBD/intein → CHITIN (material-as-ligand)
    └─ NO →  proceed with the Q1-Q3 family
```

### §5.6 Ion-gelants (where applicable)

For the ionic-gel families (alginate, hyaluronate, κ-carrageenan, pectin, gellan), the M1 page exposes an **Ion-gelants registered for [family]** expander listing the per-family registry entries plus compatible freestanding gelants. Coverage:

| Family | Per-family registry entries | Freestanding alternatives |
|---|---|---|
| ALGINATE | Ca²⁺ external CaCl₂; Ca²⁺ internal GDL/CaCO₃; Ca²⁺ internal CaSO₄ | CaSO₄ |
| HYALURONATE | Ca²⁺ cofactor (weak; covalent BDDE is canonical) | CaSO₄ |
| KAPPA_CARRAGEENAN | K⁺ external KCl | KCl |
| PECTIN | Ca²⁺ LM pectin (DE < 50%) | CaSO₄ |
| GELLAN | K⁺ low-acyl; Ca²⁺ low-acyl; Al³⁺ research-only | KCl, CaSO₄, AlCl₃ |

Non-biotherapeutic-safe entries (Al³⁺) surface a red warning in the UI: **do not use them for biotherapeutic resins.** Borax (borate-cis-diol) is registered as a TEMPORARY POROGEN only — its crosslinks dissociate at pH < 8.5, so it must be paired with a covalent secondary crosslink (BDDE / ECH) before downstream packing.

---

## §6 M2 Chemistry Catalogue

DPSim organises **103 reagents** into **18 chemistry buckets** on the M2 page. The reagent set covers every chemistry class shipped through v9.1–v9.5 plus the v0.5.0 ACS-Converter epic and the v0.5.1 deferred-work follow-on. Pick a bucket first, then a reagent within it.

### §6.1 The 18 chemistry buckets

| Bucket | Reagents | Typical use |
|---|---|---|
| Secondary Crosslinking | 8 | Stability post-coupling (genipin, glutaraldehyde, STMP, glyoxal, …) |
| **ACS Conversion** | 13 | Matrix-side ACS swap (CNBr, CDI, ECH, DVS, BDGE, EDC/NHS, Tresyl, Cyanuric chloride, Glyoxyl-chained, Periodate-direct, …). Renamed from "Hydroxyl Activation" in v0.5.0 to surface that the operation changes one polysaccharide ACS into a chemically distinct one — not all targets are -OH (e.g. periodate consumes vicinal diols; EDC/NHS targets -COOH). |
| **Arm-distal Activation** | 1 | Pyridyl-disulfide on a pre-installed amine arm (v0.5.0). Pre-condition: SPACER_ARM step has produced AMINE_DISTAL > 0 OR the polymer family is chitosan-bearing (native -NH2 surface). |
| Ligand Coupling | 12 | IEX, HIC, IMAC, GST-affinity, heparin-affinity ligands |
| Protein Coupling | 21 | Protein A/G/L canonical + Cys-tagged variants on maleimide and pyridyl-disulfide (v0.5.1), streptavidin, lectins |
| Spacer Arm | 19 | DADPA / DAH / EDA / PEG-diamine / SM(PEG)n / hydrazide / cystamine / oligoglycine |
| Metal Charging | 7 | Ni²⁺ / Co²⁺ / Cu²⁺ / Zn²⁺ for IMAC + EDTA stripping |
| Protein Pretreatment | 2 | TCEP / DTT reductions |
| Washing | 2 | Wash buffer; triazine dye-leakage advisory |
| Quenching | 4 | Ethanolamine / 2-mercaptoethanol / NaBH4 / acetic anhydride |
| **Click Chemistry** | 4 | CuAAC / SPAAC (azide-side or alkyne-side resin) |
| **Dye Pseudo-Affinity** | 2 | Cibacron Blue F3GA / Procion Red HE-3B |
| **Mixed-Mode HCIC** | 1 | 4-Mercaptoethylpyridine (MEP HCIC) |
| **Thiophilic** | 1 | 2-Mercaptoethanol thiophilic ligand (T-Sorb / T-Gel) |
| **Boronate** | 1 | m-Aminophenylboronic acid (cis-diol affinity) |
| **Peptide Affinity** | 1 | HWRGWV peptide ligand (Protein-A mimetic) |
| **Oligonucleotide** | 1 | Sequence-specific DNA affinity ligand |
| **Material-as-Ligand** | 2 | Amylose (MBP-tag) / Chitin (CBD-intein) |

The v0.5.0 reorganisation changed the original "Hydroxyl Activation" label to "ACS Conversion" to honour the chemistry — every reagent in this bucket consumes one ACS type and produces another. Pyridyl-disulfide, which is installed on an arm-distal amine rather than directly on the polysaccharide, lives in its own "Arm-distal Activation" bucket. Both legacy `ModificationStepType.ACTIVATION` and the new `ACS_CONVERSION` resolve to the same solver, so v0.4.x recipes that use ECH/DVS continue to load unchanged.

### §6.1.1 The canonical ACS Converter → Arm → Ligand → Ion-charging workflow (v0.5.0 G6 FSM)

The simulator enforces a four-phase order for any recipe:

```
   ACS Conversion  →  Spacer Arm     →  Ligand Coupling  →  Metal Charging
   (matrix-side       (optional;        (small ligand or    (only for
    ACS swap;         skipped for       protein, direct or  NTA / IDA
    e.g. -OH →        direct-couple     arm-mediated)       chelators)
    epoxide)          ligands)
        │                 │                  │                   │
        ↓                 ↓                  ↓                   ↓
   Quench/Wash → Quench → Quench → Quench (allowed at any post-INITIAL state)
```

Skips are allowed: a triazine-dye support skips arm; a HIC alkyl-amine ligand skips arm; a non-IMAC ligand skips metal charging. The G6 guardrail (`core/recipe_validation.py::_g6_acs_converter_sequence`) emits BLOCKER on illegal orderings (ligand-before-converter) and on missing preconditions (METAL_CHARGE without prior LIGAND_COUPLING that installed an NTA/IDA chelator; ARM_ACTIVATION without a prior amine arm OR a chitosan-bearing family).

Two converter-specific safety rules are also encoded:

- **CIP reductive lock-in (v0.5.0).** When `target.cip_required=True` and the recipe uses an aldehyde-producing converter (`glyoxyl_chained_activation` or `periodate_oxidation`), a downstream `nabh4_quench` step is mandatory. Without it, CIP cycles will hydrolyse the unreduced Schiff bases.
- **CNBr 15-min coupling window (v0.5.1).** When CNBr activation precedes a ligand coupling step, the cumulative duration of any intervening steps (washes, equilibrations) is summed. > 15 min ⇒ BLOCKER (`FP_G6_CNBR_HYDROLYSIS_LOSS`); 7.5–15 min ⇒ WARNING (`FP_G6_CNBR_WINDOW_AT_RISK`); ≤ 7.5 min passes silently. Cyanate ester half-life at 4 °C / pH 11 is ~5 min, so longer gaps wipe out essentially all activated sites before coupling can run.

### §6.1.2 Cyanuric chloride 3-stage staged kinetics (v0.5.1)

Cyanuric chloride bears three sequentially substitutable Cl atoms, each ~10× slower than the previous due to electron donation from the already-installed substituents. To model this, `ReagentProfile.staged_kinetics` carries three `(k_forward, E_a)` tuples and `ModificationStep.temperature_stage` (1-based) selects the active one:

| Stage | Temperature | k_forward (m³/(mol·s)) | E_a (kJ/mol) | Bench step |
|---|---|---|---|---|
| 1 | 0–5 °C | 3 × 10⁻³ | 30 | Install dichlorotriazine handle on the polysaccharide -OH |
| 2 | 25 °C | 3 × 10⁻⁴ | 50 | Couple a small ligand (dye, amine) at the second Cl |
| 3 | 60–80 °C | 3 × 10⁻⁵ | 70 | Drive the third Cl to completion (e.g. quench with glycine) |

Recipes that drive only the first substitution leave `temperature_stage=0` and use the base `k_forward`. Per Lowe & Pearson (1984) *Methods Enzymol.* 104:97; Korpela & Mäntsälä (1968) *Anal. Biochem.* 23:381.

### §6.1.3 Periodate / glyoxyl chain-scission penalty (v0.5.1)

Above ~30 % oxidation, periodate progressively cleaves the polysaccharide backbone (uronic-acid release into supernatant; loss of bead mechanical integrity). The simulator captures this as a multiplicative G_DN penalty applied AFTER the additive rubber-elasticity sum from secondary crosslinking:

| Reagent | Threshold | Max G_DN loss | Source |
|---|---|---|---|
| `periodate_oxidation` | 30 % conversion | 70 % at saturation | Bobbitt 1956; Painter 1973 |
| `glyoxyl_chained_activation` | 40 % conversion | 50 % at saturation | Mateo 2007 (the glycidol overlay protects the backbone, raising the threshold) |

The penalty composes multiplicatively across multiple oxidative steps: two 30 % scission events in series give a residual G_DN of 0.70 × 0.70 = 0.49 of nominal, not 0.40. Recipes that drive periodate to high conversion should expect a soft, scission-prone bead.

### §6.2 Chemistry-bucket workflow chart

```
┌─────────────────────────────────────────────────────────────────┐
│                    M2 Step Configuration                         │
└─────────────────────────────────────────────────────────────────┘

  Polymer family is fixed by M1.
                │
                ↓
  Step 1: Pick a Chemistry bucket from the 17 above.
                │
                ↓
  Step 2: Pick a reagent within that bucket.
          (UI labels read from each ReagentProfile.name)
                │
                ↓
  Step 3: Read the caption:
          "k=...  E_a=...  Surface chemistry: target_acs → product_acs"
          "Confidence: ...  Hazard: ..."
                │
                ↓
  Step 4: Set concentration / temperature / time / pH.
          (Defaults pulled from the reagent's profile.)
                │
                ↓
  Step 5 (optional): Pick a spacer arm if Ligand Coupling
                     or Protein Coupling.
                │
                ↓
  Step 6: Repeat from Step 1 to add additional steps
          (typical sequence: Activate → Spacer → Couple →
           Block / Quench → Wash).
```

### §6.3 Family-reagent compatibility

The simulator's family-reagent matrix knows the canonical compatibility of certain (family × reagent) pairs:

| Compatibility | Effect on dropdown |
|---|---|
| `compatible` | Reagent label unchanged |
| `qualitative_only` | Suffix "⚠ qualitative-only" added to label |
| `incompatible` | Reagent dropped from the dropdown |
| (no entry) | Reagent kept; no opinion surfaced |

Most reagent / family pairs have no explicit matrix opinion, in which case the dropdown shows the reagent without comment. The G4 guardrail blocks an actually incompatible run at submission time.

### §6.4 Staged templates

Five v9.1 staged templates remain the default starting points for new users:

| Template | Steps | Required bench confirmation |
|---|---|---|
| `epoxy_protein_a` | Activate (BDGE/ECH/DVS) → quench → couple Protein A → block | Epoxide hold-time, Protein A density, retained IgG binding, free Protein A in washes |
| `edc_nhs_protein_a` | Carboxylate activation (EDC/NHS) → couple Protein A | Carboxyl spacer density, NHS activation freshness, Protein A density / activity, free protein |
| `hydrazide_protein_a` | Hydrazide spacer → oxidised Protein A coupling → reduction | Hydrazide density, oxidised Protein A handling, activity / leaching |
| `vinyl_sulfone_protein_a` | DVS activation → couple Protein A | VS activation, nucleophile carryover control, thiol/amine coupling activity |
| `nta_imac` / `ida_imac` | Activate → couple chelator → metal charge | Chelator density, nickel loading, metal leaching (IDA leaches more than NTA) |

Chemistries without an implemented `ReagentProfile` remain valid wet-lab protocols when executed by a trained researcher, but the simulator tags their contribution as `unsupported` until calibrated against local data.

---

## §7 M3 Method and Uncertainty Bands

M3 covers the affinity-column life of the bead: pack, equilibrate, load, wash, elute. In v0.3.6 the M3 layer adds an **optional Monte-Carlo LRM uncertainty driver** that turns a posterior over Langmuir parameters (q_max, K_L, …) into envelope bands on every scalar metric and every breakthrough curve.

### §7.1 The M3 default flow

```
┌─────────────────────────────────────────────────────────────────┐
│                  M3 Column Method (Default)                      │
└─────────────────────────────────────────────────────────────────┘

  Pack       → axial diffusion, bed-compression diagnostic
                          ↓
  Equilibrate → buffer compatibility, conductivity check
                          ↓
  Load        → Lumped Rate Model (LRM) breakthrough
                          ↓
  Wash        → mass-balance closure
                          ↓
  Elute       → loaded-state low-pH OR competitive-gradient
                          ↓
  Report      → DBC₅/₁₀/₅₀, pressure profile, recovery,
                operability gates, Protein A leaching report
```

The LRM uses `solve_ivp(method="BDF")` for stability; LSODA fallback is **explicitly rejected** for high-affinity Langmuir paths because the codebase has documented LSODA stalls there.

### §7.2 Monte-Carlo uncertainty driver (v0.3.0 / G2)

When you set `recipe.dsd_policy.monte_carlo_n_samples > 0` (the default is 0, off), DPSim activates the MC-LRM driver. It:

1. Draws **N posterior samples** of (q_max, K_L, …) from a `PosteriorSamples` object — either built from your `CalibrationStore` or fitted via the optional Bayesian path.
2. Re-solves the LRM at each sampled parameter value, splitting work across `n_seeds` independent sub-runs (default 4).
3. Applies **Tier-1 numerical safeguards**: tail-aware tolerance tightening, abort-and-resample on solver exceptions, and a 5-failure consecutive-cap that flags the run as `solver_unstable`.
4. Applies **Tier-2 parameter clipping** to user-supplied `(lo, hi)` bounds (e.g. clip `q_max` to physiological range).
5. Reports **scalar quantiles** (P05 / P50 / P95) on every metric, **curve bands** on every output curve, and **convergence diagnostics**:
   - Quantile-stability plateau (final 25% vs first 75%)
   - Inter-seed posterior overlap (max-min P50 across seeds, normalised by median)
   - R-hat (informational only — LHS draws are independent by construction).

### §7.3 MC workflow chart

```
┌─────────────────────────────────────────────────────────────────┐
│             MC-LRM Uncertainty Propagation Flow                  │
└─────────────────────────────────────────────────────────────────┘

  PosteriorSamples ─┐
  (means, stds,    │
   covariance)     │
                    ↓
  draw(n) → LHS or multivariate-normal
                    │
                    ↓
  Per sample:  ┌──────────────────┐
               │ tail_mode = |z|  │
               │ > sigma_threshold│
               └────────┬─────────┘
                        ↓
               ┌──────────────────┐
               │ apply Tier-2     │
               │ parameter_clips  │
               └────────┬─────────┘
                        ↓
               ┌──────────────────┐
               │ solve_lrm with   │
               │ tightened tol if │
               │ tail_mode (10×)  │
               └────────┬─────────┘
                        ↓
               ┌──────────────────┐
               │ on RuntimeError: │
               │ resample; cap=5  │
               └────────┬─────────┘
                        ↓
  Aggregate per-seed → MCBands (P05/P50/P95)
                        ↓
  ConvergenceReport: quantile_stability,
                     inter_seed_posterior_overlap,
                     r_hat_informational
                        ↓
  ProcessDossier.mc_bands (JSON-serialisable;
                           curves decimated to 100 pts by default)
```

### §7.4 Optional: Bayesian fit (v0.3.1 / G4)

If you have raw isotherm-curve data (e.g. static-binding capacity assays) instead of pre-fitted calibration entries, install the optional extra:

```bash
pip install dpsim[bayesian]
```

Then call `fit_langmuir_posterior(assay_data)` from `dpsim.calibration.bayesian_fit`. The function runs NUTS via pymc, applies mandatory convergence gates (R-hat < 1.05, ESS > N/4, divergence rate < 1%), and returns a `PosteriorSamples` with full covariance attached. The MC-LRM driver auto-detects the covariance and switches to multivariate-normal sampling.

> **The base install does not require pymc.** Calling `fit_langmuir_posterior` without the `[bayesian]` extra raises `PymcNotInstalledError` with the install command. The module imports cleanly without pymc, so type-checking and inspection still work.

### §7.5 Reading MC bands in the UI (v0.3.2 / G5)

When `monte_carlo_n_samples > 0` and the run completes, the M3 view adds:

- A **P05 / P50 / P95 envelope plot** on the breakthrough curve. Median uses teal-500 (#14B8A6) per the design system; the P05–P95 fill uses slate-400 at 18% opacity.
- A **footer annotation** carrying the SA-Q4 marginal-only conservatism note and the SA-Q5 DSD-independence note. Both are load-bearing for screening claims.
- A **scalar-quantile table** with P05 / P50 / P95 / mean / std for every extracted metric (mass eluted, mass-balance error, max C_outlet).
- A **convergence pass / fail flag** in the dossier export.

### §7.6 ProcessDossier MC export

`ProcessDossier.from_run(..., mc_bands=bands).to_json_dict()["mc_bands"]` produces a JSON-safe dict at schema version `mc_bands.1.0`. Curves are decimated to 100 points per metric by default (override via `_mc_bands_to_dict(decimate_curves_to=N)`). The dossier carries scalar quantiles, curve bands, full convergence diagnostics, and the manifest assumptions / diagnostics — everything needed to reproduce the band envelope from the recipe.

---

## §8 Calibration and Wet-Lab Loop

DPSim is a screening tool first. The wet-lab loop turns it into a quantitative tool for your specific system. The loop has three steps:

1. **Run a screening simulation.** Get `semi_quantitative` magnitudes and `qualitative_trend` rankings.
2. **Pick the bench experiments worth running.** DPSim's wet-lab caveats and validation report tell you which assays will most reduce uncertainty.
3. **Upload measured data into the calibration store.** Re-run; the simulator reports `calibrated_local` evidence within the validated domain.

### §8.1 What the calibration store accepts

The `CalibrationEntry` schema (in `dpsim.calibration.calibration_data`) records:

- `profile_key` — which reagent / material profile this entry applies to.
- `parameter_name` — the parameter being calibrated (e.g. `q_max`, `K_L`, `activity_retention`, `estimated_q_max`).
- `measured_value` + `units`.
- `target_module` — `"L1"`, `"L2"`, `"L3"`, `"L4"`, `"M2"`, `"M3"`, or `""` (FMC default).
- `fit_method` — `"manual"`, `"least_squares"`, or `"bayesian"`.
- `posterior_uncertainty` — standard deviation of the fitted parameter.
- `valid_domain` — parameter ranges where the calibration applies.
- `confidence` — `"measured"`, `"literature"`, or `"estimated"`.

### §8.2 Wet-lab ingestion (v0.2.0)

Bench data lives in `data/wetlab_calibration_examples/*.yaml` files. The ingestion module (`dpsim.calibration.wetlab_ingestion`) loads a campaign, validates against tier-promotion rules, and applies overrides via a strict whitelist (immutable identity fields like `name` / `cas` / `target_acs` are forbidden). Q-013 (chitosan kernel) and Q-014 (v9.2 profile validation) are the canonical example campaigns.

### §8.3 The evidence-tier inheritance rule

M3 is **never** allowed to claim stronger evidence than the M2 media contract that supplies its ligand and site-balance basis. Likewise, M2 caps to M1's calibration tier. This is enforced via `RunReport.compute_min_tier` and surfaced in the evidence ladder. **If you see your M3 result drop to `qualitative_trend`, look up the chain at M2 and M1 — the cause lives there.**

---

## §9 CFD-PBE Zonal Coupling for M1 Scale-up

The standard M1 solver feeds the population balance equation (PBE) one scalar dissipation rate ε computed from `P / (ρ · V_tank) = Po · N³ · D⁵ / V_tank` (see Appendix G). That single number is the volume-average over the whole vessel. For a well-mixed pitched-blade impeller in a benchtop beaker, it is good enough. For a rotor-stator, a 1 L scale-up, or any mixer whose breakage is dominated by a small high-shear region, **the volume average underestimates breakage** — and underestimating breakage leads to over-predicted droplet sizes, which is the wrong direction for a screening tool.

The CFD-PBE zonal coupling, introduced in v0.6.0, replaces the single ε with a CFD-resolved, per-compartment ε field. You run an OpenFOAM steady-state RANS simulation of your geometry (CAD provided in `cad/output/`), partition the fluid domain into zones, extract per-zone ε, and feed `dpsim cfd-zones` a `zones.json` file. DPSim then solves the PBE per zone with zone-specific kernels and convective droplet exchange between zones.

> **What this is.** A spatially-resolved upgrade to the M1 PBE that captures sub-zone breakage hotspots. Same kernels (Alopaeus breakage, Coulaloglou-Tavlarides coalescence). Same fixed-pivot grid. Different ε per zone, plus convective mass exchange. **Bit-exact reduction to the legacy single-zone solver when you give it one zone.**

### §9.1 When to use CFD-PBE coupling (decision tree)

```
Are you doing one of the following?

   ┌─ 10× scale-up prediction (e.g. 100 mL → 1 L)        → YES → §9.4
   ├─ Rotor-stator with stator slots (Stirrer B family)  → YES → §9.5
   ├─ Geometry that differs significantly from           → YES → §9.4
   │  the standard pitched-blade calibration regime
   ├─ Comparing predicted DSD across two stirrer types   → YES → §9.4
   │  at the same nominal P/V
   ├─ Investigating "why is d32 not falling with RPM     → YES → §9.4
   │  the way the legacy solver predicts?"
   ├─ Bench validation already done, default kernel      → NO  → use legacy
   │  predictions match measurement within 15 %                  M1 path
   └─ Standard pitched-blade in a calibrated beaker      → NO  → use legacy
      (within the validation envelope)                             M1 path
```

If your answer is "I am within the validation envelope of the legacy single-ε solver and my measured DSD agrees with the prediction," **you do not need CFD-PBE coupling.** Use the legacy path. The zonal coupling is an extension, not a replacement.

If your answer is "my geometry is unusual, my scale-up is non-trivial, or my breakage is happening somewhere other than the volume-average implies," CFD-PBE coupling will give you a better-grounded prediction — provided you back it with PIV-measured velocity (see §9.8).

### §9.2 Why volume-averaged ε underestimates breakage

The Alopaeus breakage rate is

```
g(d, ε) = C₁ · √(ε/ν_c) · exp[ -C₂·σ / (ρ_c · ε^(2/3) · d^(5/3)) - C₃·Vi ]
```

The leading term goes as **ε^(1/2)** and the exponent argument is **divided by ε^(2/3)** — both of which mean that g(d, ε) is **convex in ε**. By Jensen's inequality, `<g(ε)>_volume > g(<ε>_volume)`. In plain English: *if a small fraction of the vessel volume has 10× the average ε, that small fraction does much more than 10× the breakage of an equal-volume bulk region*. Volume-averaging hides this entirely.

Coalescence behaves differently. The Coulaloglou-Tavlarides collision-frequency / film-drainage product is more linear in ε, and the dominant ε-dependence shows up in the film drainage exponent, which damps coalescence in high-ε regions where droplets are too far apart to refilm. A volume-averaged ε is therefore the correct scalar for the coalescence kernel.

The zonal coupling resolves this with a **two-ε scheme**. Each zone exports two ε values:

- **`epsilon_avg_W_per_kg`** — the standard volume average over zone cells. **Drives coalescence.**
- **`epsilon_breakage_weighted_W_per_kg`** — biased toward sub-zone hotspots via the breakage-frequency function itself: `<ε>_g = ∫ g(d_ref, ε(x)) · ε(x) dV / ∫ g(d_ref, ε(x)) dV`. **Drives breakage.**

Figure 9.1 shows the geometry of the bias.

```
Within a single CFD zone, ε(x) is heterogeneous:

     ε(x)
      │              ╭─╮ hotspot (rare, large)
      │             ╱   ╲
      │           ╱       ╲
      │         ╱           ╲           bulk of cells
      │       ╱     ╭───╮     ╲      ╭──────────────╮
      │     ╱     ╱     ╲       ╲   ╱
      │___╱_____╱         ╲      ╲_╱
      │
      └────────────────────────────────────────► position x

  Volume average (used for COALESCENCE):
        ε_avg = ∫ ε(x) dV / ∫ dV

  Breakage-weighted average (used for BREAKAGE):
        ε_brk = ∫ g(d_ref, ε(x)) · ε(x) dV / ∫ g(d_ref, ε(x)) dV

  By construction:  ε_brk ≥ ε_avg.
```

**Figure 9.1.** Why the two-ε scheme is needed. The continuous ε field has hotspots that dominate breakage rate g(d, ε) but contribute little to the volume average. The schema enforces `epsilon_breakage_weighted_W_per_kg ≥ epsilon_avg_W_per_kg` (within 1 % numerical slack) at load time; a violation indicates a bug in the post-processing script.

### §9.3 The variable-N compartment model

A `zones.json` file describes a CFD-derived compartment model with a variable number of zones. Each zone is a well-mixed region of the vessel; pairs of zones are connected by directional convective flows that transport droplets between them.

The model has two design choices worth understanding:

**1. Variable-N.** The schema lets you use any number of zones from 1 (degenerate single-zone case, equivalent to the legacy solver) up to as many as your CFD partitioning warrants. The validated baseline configurations are 3 zones for an open impeller (impeller / `near_wall` / bulk, see §9.4) and 4 zones for a rotor-stator (impeller / `slot_exit` / `near_wall` / bulk, see §9.5). More zones add resolution but also add load on `extract_epsilon.py`; in practice, 3–5 zones capture the relevant physics.

**2. Asymmetric exchange.** A convective flow from zone A to zone B with rate Q [m³/s] does not give the two zones a symmetric coupling, because they have different volumes. The number-density balance is:

```
   dN_A/dt += ... - (Q/V_A) · N_A          # outflow from A
   dN_B/dt += ... + (Q/V_B) · N_A          # inflow to B (well-mixed)
```

Different denominators. The same droplet count leaves A and arrives at B per unit time, but their fractional rates of change differ because of the volume disparity. This matters most for rotor-stators where the `slot_exit` zone has volume O(0.5 µL) while the bulk has O(80 mL) — the `slot_exit` fills and empties hundreds of times per second.

To represent net asymmetric flow (e.g., an impeller pumps strongly in one direction), include both directions explicitly in the `exchanges[]` list with their respective flow rates.

### §9.4 Worked example — Stirrer A (3 zones)

Stirrer A is a pitched-blade open impeller in a 100 mL beaker (see `cad/output/stirrer_A_pitched_blade`). The canonical partition is three zones:

```
        ┌────────── Beaker (V = 100 mL, Ø100 mm) ──────────┐
        │                                                  │
        │       ┌─── near_wall ──┐  (ε_avg = 8.5 W/kg)     │
        │       │                │   slow exchange         │
        │       │  ┌──────┐      │   Q = 4.2 µL/s          │
        │       │  │ bulk │ ◄──► │                         │
        │       │  │      │      │                         │
        │       │  │      │      │   (ε_avg = 4.8)         │
        │       │  └──┬───┘      │                         │
        │       │     │ ▲        │                         │
        │       │     │ │ Q = 16 │                         │
        │       │     │ │ µL/s   │                         │
        │       │     ▼ │        │                         │
        │       │  ┌─────────┐   │                         │
        │       │  │impeller │   │   ε_avg = 75            │
        │       │  │  (HIGH ε│   │   ε_brk = 110           │
        │       │  │  zone)  │   │   (breakage hotspot)    │
        │       │  └─────────┘   │                         │
        │       └────────────────┘                         │
        └──────────────────────────────────────────────────┘
```

**Figure 9.2.** Stirrer A 3-zone compartment model. Bidirectional exchange arrows show convective droplet flow between zones. The impeller zone (highest ε) is the dominant breakage region; bulk acts as the sink and `near_wall` is weakly coupled. ε values are in W/kg; flows in µL/s. The values shown are the canonical example fixture at `cad/cfd/cases/stirrer_A_beaker_100mL/zones.example.json`.

**Per-zone ε ordering:** impeller (75 W/kg) ≫ `near_wall` (8.5) > bulk (4.8). Volume-weighted average is 9.0 W/kg, close to the legacy Po·N³·D⁵/V_tank estimate at 1500 RPM.

**Steady-state d32 ordering** (after several seconds of integration): `d32_impeller` < `d32_near_wall` < `d32_bulk`. The impeller zone breaks droplets fastest; bulk is the sink that receives them and lets them coalesce; `near_wall` sits in between. This ordering is enforced as a regression test in `tests/test_cfd_zonal_pbe.py::test_breakage_zone_bias_stirrer_a`.

### §9.5 Worked example — Stirrer B (4 zones, rotor-stator loop)

Stirrer B is a small rotor-stator with 72 stator perforations (24 columns × 3 rows; see `cad/output/stirrer_B_rotor` and `stirrer_B_stator`). The defining feature is the **slot exit jet**: 80–95 % of breakage events in rotor-stator devices happen in the small region just outside each stator hole, where the rotating fluid blasts through the gap and dissipates suddenly (Padron 2005; Hall et al. 2011). That region is too small to volume-average away — it gets its own zone.

```
                 BREAKAGE LOOP (Q = 84 µL/s, all 3 edges)
              ┌──────────────────────────────────────┐
              │                                      │
              │   ┌──────────┐     ┌─────────────┐  │
              ▼   │ impeller │ ───►│  slot_exit  │  │
       ┌──────────┤ ε_avg=220├     │ ε_avg=850   │  │
       │   bulk   │ ε_brk=350│     │ ε_brk=1200  │──┘
       │ε_avg=8.5 │          │     │ (DOMINANT   │
       │ε_brk=11  └──────────┘     │  BREAKAGE)  │
       │                            └──────┬──────┘
       │                                   │
       │ ◄─────────────────────────────────┘
       │      Q = 84 µL/s (slot exit jets)
       │
       │   Q = 9.8 µL/s    ┌────────────┐
       └──────────────────►│ near_wall  │
       ◄──────────────────┤ ε_avg = 18 │
       │   (weak coupling) │ ε_brk = 25 │
       │                   └────────────┘
       └──────────────────────────────────
```

**Figure 9.3.** Stirrer B 4-zone compartment model. The impeller→`slot_exit`→bulk→impeller circulation is the **breakage loop**. Slot_exit has the highest ε (850 / 1200 W/kg) but very small volume (0.45 µL), giving a residence time of roughly 5 ms — droplets are dominated by inflow from impeller, not by local breakage during transit. The `near_wall` zone is weakly coupled (Q one order of magnitude lower than the loop edges) and drifts independently. Q values are volumetric flows; ε in W/kg. Canonical fixture at `cad/cfd/cases/stirrer_B_beaker_100mL/zones.example.json`.

**Counter-intuitive consequence:** at steady state the per-zone d32 ordering is **bulk > `slot_exit` ≈ impeller** (within the loop), with `near_wall` an outlier. The `slot_exit` zone does most of the breakage *work*, but its short residence time prevents the local d32 from dropping much below the loop average. Bulk is consistently the largest because it is the sink. This is correctly captured by the integrator and asserted as `tests/test_cfd_zonal_pbe.py::test_breakage_zone_bias_stirrer_b_loop_below_bulk`.

### §9.6 Running it: `dpsim cfd-zones`

The `dpsim cfd-zones` subcommand is the standalone runner for a zonal simulation. It does **not** modify the standard `run` / `lifecycle` pipeline.

**Minimal invocation** (Stirrer A example fixture):

```
dpsim cfd-zones cad/cfd/cases/stirrer_A_beaker_100mL/zones.example.json \
    --kernels pitched_blade \
    --duration 30 \
    --output results.json
```

**Full flag reference:**

| Flag | Default | Meaning |
|---|---|---|
| `zones_json` (positional) | required | Path to zones.json (schema v1.0) |
| `--kernels` | `pitched_blade` | KernelConfig preset. Use `pitched_blade` for Stirrer A, `rotor_stator_small` for Stirrer B, `rotor_stator_legacy` for the original homogeniser calibration |
| `--rho-oil` | from `MaterialProperties` | Continuous-phase density [kg/m³] |
| `--mu-oil` | from `MaterialProperties` | Continuous-phase viscosity [Pa·s] |
| `--rho-aq` | from `MaterialProperties` | Aqueous density [kg/m³] |
| `--mu-d` | from `MaterialProperties` | Dispersed-phase viscosity [Pa·s] |
| `--sigma` | from `MaterialProperties` | Interfacial tension [N/m] |
| `--phi-d` | 0.05 | Dispersed-phase volume fraction |
| `--duration` | 30.0 | Integration duration [s]; no adaptive extension — call again with longer if d32 has not stabilised |
| `--n-bins` | 50 | Fixed-pivot diameter grid bins |
| `--d-min`, `--d-max` | 1e-7, 5e-4 | Grid bounds [m] |
| `--d32-premix`, `--sigma-premix` | 100e-6, 0.5 | Initial log-normal premix DSD |
| `--legacy-eps` | (none) | Optional empirical ε [W/kg] for the consistency cross-check (§9.7) |
| `--consistency-tol` | 0.30 | Relative tolerance for the cross-check |
| `--output` | (none) | Path to write the results JSON (else stdout summary only) |
| `--quiet` | off | Suppress the per-zone summary print |

**Sanity-check invocation** (run with consistency gate):

```
dpsim cfd-zones zones.json \
    --kernels pitched_blade \
    --rho-oil 860 --mu-oil 0.05 --mu-d 0.05 --sigma 5e-3 \
    --phi-d 0.05 --duration 30 --d32-premix 200e-6 \
    --legacy-eps 9.0 \
    --output results.json
```

The `--legacy-eps` flag triggers the §9.7 cross-check against the empirical Po·N³·D⁵/V_tank value; a failure logs a clearly-marked WARNING but does not stop the run.

### §9.7 Reading the output

The integrator emits an aggregated DSD across all zones plus a per-zone breakdown. The console summary covers the headline numbers; the JSON output adds the structured fields you need for downstream analysis.

**Aggregated DSD** is the volume-weighted convolution: `aggregated_counts[j] = Σᵢ Vᵢ · N_{i,j}`, total droplet count in bin j across all zones. d10/d32/d50/d90 and span are computed from this. **Compare aggregated d32 against your measured DSD** — that is the bench-comparable number.

**Per-zone d32** tells you where the breakage is happening. For a healthy run you expect (a) the highest-ε zone to have the smallest d32 (open impeller) or (b) the bulk/sink zone to have the largest d32 with the high-ε loop-members clustered close together (rotor-stator). If the per-zone ordering looks inverted, your CFD inputs are probably wrong — see §9.8.

**Volume balance** (`volume_balance.relative_error`): the total droplet volume ΣᵢVᵢΣⱼN_{i,j}vⱼ should be exactly conserved. The integrator reports the relative error against the initial droplet volume (`phi_d · V_total`). **Fail gate: > 1e-3.** Breakage and coalescence are mass-conservative under fixed-pivot redistribution; convective exchange has equal source-loss / target-gain rates by construction. A volume-balance error above 1e-3 indicates either a bug in the integrator or a pathologically stiff parameter regime — file an issue if you hit it.

**Consistency check** (only when `--legacy-eps` was passed): cross-checks Σ(Vᵢ·εᵢ)/Σ(Vᵢ) against the empirical legacy estimate. The default 30 % tolerance is the irreducible Po-correlation uncertainty for non-standard impeller geometries (Scientific Advisor guidance, 2026-05-01). A pass means your CFD setup is consistent with first-principles power draw; a fail means **either** your CFD's RPM/viscosity/convergence is wrong, **or** the empirical Po and impeller D in `datatypes.py` need adjustment. Investigate before trusting the per-zone results.

```
Aggregated DSD:
  d10 = 73.57 um
  d32 = 112.37 um
  d50 = 105.45 um
  d90 = 148.56 um
  span = 0.711

Per-zone d32:
  impeller             = 108.83 um
  near_wall            = 110.77 um
  bulk                 = 112.84 um

Volume balance:
  initial    = 5.0000e-06 m^3
  final      = 5.0000e-06 m^3
  rel. error = 0.00%

Consistency check vs legacy empirical eps:
  eps_cfd     = 9.03 W/kg
  eps_legacy  = 9   W/kg
  rel_err     = 0.39% (tol=30%)
  passed      = True
```

**Figure 9.4.** Example console output for Stirrer A at 1500 RPM, 10 s integration, paraffin/aqueous-polymer system. The per-zone d32 spread is small here (~4 µm) because the impeller↔bulk exchange equilibrates the loop on a timescale shorter than the breakage relaxation; the spread grows for poorly-coupled or higher-disparity geometries.

### §9.8 Validation status and limitations

The CFD-PBE coupling is currently in a **scaffolded** state: the DPSim-side coupling, integrator, schema, and CLI are implemented and tested (33 pytest tests, including bit-exact 1-zone reduction to the legacy solver). The OpenFOAM-side pipeline that produces `zones.json` is documented but not yet executed against real geometry — see Appendix K and `cad/cfd/README.md` for the 7-phase OpenFOAM roadmap.

Until you have run a PIV measurement at bench scale on the geometry you are simulating, the CFD field is **unvalidated**. Treat predictions accordingly:

| Use | Acceptable use of zonal CFD-PBE |
|---|---|
| Relative comparison of two stirrer types at matched P/V | **Yes** — relative differences are robust to absolute ε accuracy |
| Predicting trends with RPM, φ_d, surfactant load | **Yes** — trends are kernel-driven, not absolute-ε-driven |
| Predicting absolute d32 at a new scale (1 L from 100 mL) | **Only with PIV validation at the bench scale.** Without it, treat the prediction as `qualitative_trend`. |
| Replacing wet-lab DSD measurement | **No.** Same as for the legacy M1 path. |

**Other limitations:**

- **Single-phase Eulerian.** The CFD treats only the continuous-phase ε field. Dispersed-phase φ_d is assumed homogeneous across zones at t=0. For highly inhomogeneous concentrated emulsions (φ_d > 0.4 with strong segregation) this assumption breaks; deferred to schema v1.1.
- **Steady-state RANS.** Time-resolved transients (start-up, shut-down, RPM ramp) are not captured. Use end-of-integration steady values only.
- **k-ω SST turbulence.** RANS is the appropriate cost-accuracy point for ε-field validation; LES would be 100× more expensive and is not justified for 10× scale-up validation.
- **Inertial sub-range assumption.** Both Alopaeus breakage (with C₃ = 0) and Coulaloglou-Tavlarides coalescence assume `d ≫ η_K` (Kolmogorov scale). If your `d_mode/η_K < 5` in any zone, the CT kernel is marginal; the integrator does not warn for the zonal case (the legacy stirred-vessel path does — port deferred).
- **No adaptive extension.** Unlike the legacy `solve_stirred_vessel`, `integrate_pbe_with_zones` does not auto-extend until d32 stabilises. If your last 10 % of integration time still shows d32 changing, re-run with a longer `--duration`.

**Evidence-tier policy:** until validated, M1 results from the zonal path inherit `qualitative_trend` evidence in the lifecycle ladder. Calibration of the CFD field via PIV moves it to `calibrated_local`; full bench DSD calibration moves it to `validated_quantitative`. The same inheritance rule (§8.3) applies.

### §9.9 Pointers and references

**Source-of-truth files:**

| Topic | File |
|---|---|
| `zones.json` schema v1.0 | `cad/cfd/zones_schema.md` |
| OpenFOAM 7-phase pipeline roadmap | `cad/cfd/README.md` |
| DPSim-side coupling implementation | `src/dpsim/cfd/zonal_pbe.py` |
| CLI subcommand | `src/dpsim/__main__.py` (`_cmd_cfd_zones`) |
| Pytest suite (33 tests, including 1-zone equivalence) | `tests/test_cfd_zonal_pbe.py` |
| Stirrer A 3-zone canonical fixture | `cad/cfd/cases/stirrer_A_beaker_100mL/zones.example.json` |
| Stirrer B 4-zone canonical fixture | `cad/cfd/cases/stirrer_B_beaker_100mL/zones.example.json` |
| Advanced reference (deep-dive, OpenFOAM dicts, references) | `appendix_K_cfd_pbe_zonal_coupling.md` |

**Foundational references:**

- Alopaeus V., Koskinen J., Keskinen K. I., Majander J. (2002). *Simulation of the population balances for liquid-liquid systems in a nonideal stirred tank.* Chem. Eng. Sci. 57, 1815–1825.
- Coulaloglou C. A., Tavlarides L. L. (1977). *Description of interaction processes in agitated liquid-liquid dispersions.* Chem. Eng. Sci. 32, 1289–1297.
- Padron G. (2005). *Effect of surfactants on drop size distribution in a batch, rotor-stator mixer.* PhD thesis, U. of Maryland. — **Slot-exit dominance of rotor-stator breakage.**
- Hall S., Cooke M., Pacek A. W., Kowalski A. J., Rothman D. (2011). *Scaling-up of silverson rotor-stator mixers.* Can. J. Chem. Eng. 89, 1040–1050. — **80–95 % of breakage in slot exit jets.**
- Wang T., Mao Z.-S. (2005). *CFD-PBE coupling for stirred tanks.* Chem. Eng. Sci. 60, 4501–4516.
- Kumar S., Ramkrishna D. (1996). *On the solution of population balance equations by discretization — I. A fixed pivot technique.* Chem. Eng. Sci. 51, 1311–1332.

---

# Part III — Appendix (Reference)

## A. Detailed Input Requirements

### A.1 Target Product Profile

| Field | Type | Range | Notes |
|---|---|---|---|
| `target_d50_um` | float | 5–500 | Nominal microsphere diameter [µm] |
| `target_pore_nm` | float | 1–200 | Mean pore size in the wet gel [nm] |
| `target_G_DN_kPa` | float | 1–5000 | Minimum acceptable bulk modulus [kPa] |
| `ligand` | str | enum | `protein_a`, `nta`, `ida`, `deae`, `q`, `cm`, `sp`, `phenyl`, `streptavidin`, `protein_g`, `glutathione`, `heparin`, `apba`, `mep_hcic`, `cibacron_blue`, … |
| `analyte` | str | free-form | The molecule you want to capture / analyse |
| `max_pressure_drop_Pa` | float | 1e4–5e6 | Method-target ceiling |
| `residual_oil_ppm` | float | 0–1000 | Acceptable oil carryover after wash |
| `residual_surfactant_ppm` | float | 0–1000 | Acceptable surfactant carryover |

### A.2 M1 Fabrication Recipe

Common to every polymer family:

| Field | Type | Notes |
|---|---|---|
| `polymer_family` | enum (21 values) | See §5 |
| `c_polymer_pct` | float | Polymer w/v % (family-specific range) |
| `surfactant_key` | str | From `SURFACTANTS` registry (Span-80, PVA, Tween, …) |
| `c_surfactant` | float | Surfactant load in oil or aqueous phase |
| `T_oil_C` / `T_aq_C` | float | Phase temperatures [°C] |
| `RPM` | float | Stirred-tank impeller speed |
| `is_stirred` | bool | True for stirred-tank, False for microfluidic |
| `t_emulsify_s` | float | Emulsification residence time |
| `t_cooldown_min` | float | Cooldown duration |
| `wash_cycles` | int | Number of wash cycles |
| `wash_volume_per_cycle_mL` | float | Volume per cycle |

Family-specific additional fields are documented in the corresponding formulation-page docstrings (see `src/dpsim/visualization/tabs/m1/formulation_*.py`).

### A.3 M2 Chemistry Recipe

Per step:

| Field | Type | Notes |
|---|---|---|
| `step_type` | enum (17 buckets) | See §6.1 |
| `reagent_key` | str | From `REAGENT_PROFILES` (96 entries) |
| `concentration_mM` | float | Reagent concentration |
| `temperature_C` | float | Reaction temperature |
| `time_h` | float | Reaction time |
| `pH` | float | Buffer pH |
| `spacer_key` | str (optional) | For Ligand / Protein Coupling steps |

Maximum 3 sequential steps per recipe in v0.3.x.

### A.4 M3 Column Method

| Field | Type | Notes |
|---|---|---|
| `column_diameter_mm` | float | Inner diameter |
| `bed_height_cm` | float | Packed-bed height |
| `bed_porosity` | float (0.25–0.50) | Inter-particle void fraction |
| `flow_rate_mL_min` | float | Linear flow per minute |
| `feed_concentration_mg_mL` | float | Load step feed |
| `feed_duration_min` | float | Load step duration |
| `total_time_min` | float | Total simulation horizon |
| `q_max` / `K_L` | float | Default Langmuir; user calibration recommended |
| `bind_pH` / `bind_cond_mS_cm` | float | Bind/wash buffer |
| `elute_pH` / `elute_cond_mS_cm` | float | Elution buffer |
| `gradient_start_mM` / `gradient_end_mM` | float | Salt or pH gradient |
| `monte_carlo_n_samples` | int (default 0) | MC-LRM driver activation; > 0 enables uncertainty bands |
| `monte_carlo_n_seeds` | int (default 4) | Inter-seed posterior overlap diagnostic |
| `monte_carlo_parameter_clips` | dict | Tier-2 clipping `{name: (lo, hi)}` |

---

## B. Process Steps

The lifecycle orchestrator runs these steps in order. Each writes its output into the `LifecycleResult` and applies its evidence cap.

```
┌─────────────────────────────────────────────────────────────────┐
│                  Lifecycle Orchestrator Flow                     │
└─────────────────────────────────────────────────────────────────┘

[1] resolve_lifecycle_inputs(recipe)
        ↓ produces LifecycleResolvedInputs
[2] run M1 family pipeline
        ↓ MicrosphereResult (DSD, pore, modulus, residuals)
[3] apply M2 functionalisation steps in order
        ↓ FunctionalMicrosphere (FMC, ACS state, ligand contract)
[4] build PerformanceRecipe from resolved + FMC
        ↓ ColumnGeometry, method steps, isotherm defaults
[5] run_method_simulation(recipe, fmc, microsphere)
        ↓ MethodSimulationResult
        ↓   - representative chromatography
        ↓   - optional gradient elution
        ↓   - optional DSD per-quantile screening
        ↓   - optional MC LRM bands (when n_samples > 0)
[6] roll up evidence ladder; cap to weakest tier
        ↓ FullResult / RunReport
[7] export to ProcessDossier (when requested)
```

Step 5 is the load-bearing chromatography step. Its model selection is documented in CLAUDE.md and pinned in `module3_performance/transport/lumped_rate.py`:

| Model | Default solver | Rationale |
|---|---|---|
| `packed_bed.py` (PFR + Michaelis-Menten) | LSODA | Non-stiff; ~700× faster than BDF |
| `lumped_rate.py::solve_lrm` (default) | LSODA | Non-gradient case |
| `lumped_rate.py::solve_lrm` (gradient + adapter) | BDF | LSODA oscillates modes when binding equilibrium is time-varying |
| `orchestrator.py::run_gradient_elution` | BDF | Always gradient path |

---

## C. Essential Input & Process Checklist

Use this checklist before pressing **Run Lifecycle Simulation**:

### C.1 Pre-flight

- [ ] Polymer family selected. (UI radio at top of M1 tab.)
- [ ] Polymer concentration is inside the family's recommended range.
- [ ] Surfactant choice is HLB-compatible with the chosen oil phase.
- [ ] Ion-gelant chosen (for ionic-gel families) or crosslinker chosen (for covalent families).
- [ ] M1 wash schedule is specified (number of cycles + volume per cycle).
- [ ] M2 staged template chosen — or each step's chemistry bucket and reagent are explicitly set.
- [ ] M2 reagent concentration / temperature / time / pH are inside the reagent's `(min, max)` envelope (UI shows red if not).
- [ ] Spacer arm specified for Ligand Coupling and Protein Coupling steps (or "None" explicitly).
- [ ] M3 column geometry, bed porosity, flow rate, and feed concentration are set.
- [ ] M3 method buffers (bind/wash + elute) carry pH and conductivity.
- [ ] If MC-LRM is enabled: `monte_carlo_n_samples ≥ 100` (otherwise the inter-seed overlap diagnostic becomes noisy and the run logs a `WARNING`).
- [ ] Posterior samples passed to `run_method_simulation` if MC enabled.
- [ ] `mc_lrm_solver` callable provided if MC enabled (or use `make_langmuir_lrm_solver` from `mc_solver_lambdas`).

### C.2 Result review

- [ ] Validation report has zero blockers (red).
- [ ] Evidence ladder reports the weakest tier; you understand why.
- [ ] M1 residual oil and surfactant are below your screening limits.
- [ ] M2 ligand density and activity retention are reported with their evidence tier.
- [ ] M3 pressure profile is below your method-target ceiling.
- [ ] M3 mass balance closure is < 2%.
- [ ] If MC enabled: `convergence_pass = True` (quantile-stability and inter-seed overlap both passed).

### C.3 Wet-lab readiness

- [ ] The exported wet-lab SOP is reviewed by the responsible scientist.
- [ ] All reagents have current SDS / safety briefs (Appendix J carries SDS-lite blocks for the v9.1 set).
- [ ] Hazard flags from each `ReagentProfile.hazard_class` are surfaced to the operator.
- [ ] Buffer compatibilities cross-checked against `buffer_incompatibilities` field.
- [ ] Calibration data uploaded for any locally-known parameter.

---

## D. Frequently Asked Questions

### D.1 General

**Q. Is DPSim a replacement for wet-lab work?**
No. DPSim is a screening simulator. Use it to design experiments, narrow parameter space, and predict failure modes. The wet-lab loop validates the simulator's predictions against your specific system.

**Q. What evidence tier should I demand before making a recipe decision?**
For a screening / hypothesis-generation decision: `qualitative_trend` is enough. For a quantitative process-design decision: `calibrated_local` or `validated_quantitative`. Never act on `unsupported`.

**Q. How long does a run take?**
Agarose-chitosan ≈ 2 s; alginate ≈ 5 s; cellulose NIPS ≈ 30 s (the Cahn-Hilliard solver is the slowest); MC-LRM enabled adds minutes proportional to `n_samples × per-sample LRM solve time`.

### D.2 First-time use

**Q. Where do I start?**
Day 1: run the default Protein A affinity-media recipe; double the RPM; export and run the lifecycle default. After those three runs you understand the workflow.

**Q. The UI says "Module 1 has not been run yet" on the M2 tab. Why?**
The lifecycle workflow is sequential. M2 needs M1's `MicrosphereResult` (DSD, pore, modulus) to compute reactive-site density. Run M1 first, then M2.

**Q. Can I skip M1 if I just want to test M3 method changes?**
You can run the legacy per-module M3 tab with manually-supplied isotherm parameters, but the lifecycle workflow always runs M1 → M2 → M3. The legacy tabs are debug-only.

### D.3 Polymer families

**Q. I picked PECTIN_CHITOSAN with `degree_of_esterification = 0.7`. The result says `evidence_tier = unsupported`. Why?**
High-methoxy pectin (DE > 0.5) requires sugar-acid co-gelation (typically 65% w/w sucrose + low pH), which is fundamentally different chemistry from the Ca²⁺ egg-box model the v9.5 solver implements. Use DE ≤ 0.5 (low-methoxy) for a `qualitative_trend` result, or treat HM pectin as a wet-lab-only protocol.

**Q. Do all 21 polymer families have full UI formulation pages?**
No. The v9.1 baseline (agarose-chitosan, alginate, cellulose, PLGA) has dedicated formulation pages. The v9.2–v9.5 expansion families currently route through the alginate-style flow via `composite_dispatch.solve_gelation_by_family`. Dedicated formulation pages for the expansion families are tracked as a v0.4+ follow-on.

**Q. Can I use AlCl₃ as a gelant?**
Technically yes, but the UI surfaces a red warning because Al³⁺ residue is FDA/EP-regulated for biotherapeutic resins. The `biotherapeutic_safe = False` flag will block AlCl₃ from default workflows. Use only for research / non-biotherapeutic applications.

**Q. Borax is listed as a "REVERSIBILITY WARNING" item. Can I use it?**
Borax forms borate-cis-diol crosslinks that dissociate at pH < 8.5 or in the presence of competing diols/sugars. It is NOT suitable as a final crosslinker for chromatography — the network would dissociate under normal elution. Use only as a temporary porogen / model network, then pair with a covalent secondary crosslink (BDDE / ECH) before downstream packing.

### D.4 M2 chemistry

**Q. The dropdown only used to show 3 options under "Hydroxyl Activation." Now there are 11. What changed?**
The v0.3.4 audit fix replaced the hardcoded reagent dicts with a generated dispatch driven by `REAGENT_PROFILES.functional_mode`. Every reagent shipped in `REAGENT_PROFILES` now auto-surfaces — 50/94 → 94/94 coverage. New chemistry buckets (Click Chemistry, Dye Pseudo-Affinity, Mixed-Mode HCIC, Thiophilic, Boronate, Peptide Affinity, Oligonucleotide, Material-as-Ligand) were added at the same time.

**Q. EDC/NHS doesn't seem to work on agarose-chitosan. Why?**
EDC/NHS requires surface COOH groups. Pure chitosan / pure agarose have essentially none. The simulator runs a `qualitative_trend`-tier fallback and will not produce a trustworthy modulus. Pre-modify the matrix (e.g., carboxymethyl chitosan or succinylation) and set `MaterialProperties.surface_cooh_concentration > 0` to activate the mechanistic EDC/NHS path.

**Q. CuAAC click is shown twice in the dropdown. Why?**
Click reactions are bidirectional with respect to which partner sits on the resin. `cuaac_click_coupling` targets an azide-functionalised resin (alkyne ligand). `cuaac_click_alkyne_side` targets an alkyne-functionalised resin (azide ligand). Pick the one matching how you activated the bead.

### D.5 M3 and uncertainty

**Q. What does `monte_carlo_n_samples = 0` do?**
It disables the MC-LRM driver entirely. The legacy v0.2.x `MethodSimulationResult` is byte-identical when `n_samples = 0`, so default behaviour is preserved.

**Q. The MC run reports `solver_unstable = True`. What does that mean?**
The driver hit its consecutive-failure cap (default 5) on `solve_lrm` exceptions. The bands are incomplete. Check posterior bounds — if `q_max` or `K_L` can sample at unphysical values (negative or zero), set `monte_carlo_parameter_clips` to clip them. The `make_langmuir_lrm_solver` helper raises `ValueError` on non-physical samples, which triggers the abort-and-resample path automatically.

**Q. Why is `n_jobs` parallelism only effective when `n_seeds > 1`?**
v0.3.6 dispatches per-seed sub-runs to joblib. With one seed, there's nothing to parallelise. Use the default `n_seeds = 4` (or larger) to benefit from `n_jobs > 1`.

**Q. R-hat is reported as informational only. Why?**
LHS draws are independent by construction, so R-hat reduces to a restatement of inter-seed posterior overlap. The reformulated AC#3 (per SA-Q3 / D-047) uses **quantile-stability plateau** + **inter-seed posterior overlap** as the load-bearing diagnostics. R-hat near 1.0 is expected for any well-mixed run.

### D.6 Calibration

**Q. How do I add my own DBC measurement?**
Create a `CalibrationEntry` with `parameter_name = "estimated_q_max"`, `target_module = "M3"`, `fit_method = "manual"`, and `measured_value = your_q_max`. Save to a JSON file via `CalibrationStore.save_json`, then load it on the next run.

**Q. I have a binding-isotherm curve. Can DPSim fit q_max and K_L for me?**
Yes — install the optional `[bayesian]` extra and use `fit_langmuir_posterior(assay_data)`. The function applies mandatory R-hat / ESS / divergence convergence gates and returns a `PosteriorSamples` with full covariance.

---

## E. Architectural Ideas and Working Principles

### E.1 First principles

DPSim is built on five architectural principles. Internalise them and the rest of the manual will read easily:

1. **First-principles decomposition.** Every M1/M2/M3 model is reasoned from physics or chemistry first; convention follows analysis.
2. **Modularity and separation of concerns.** Every processing step is a discrete module with typed inputs, typed outputs, and a single well-scoped responsibility.
3. **Algorithmic rigour.** Algorithm choices are justified by complexity, convergence properties, and numerical stability. Solver method matrices are pinned (CLAUDE.md).
4. **Computational economics.** Every design decision considers compute / memory / time cost against the value of the output. Over-engineering is a defect.
5. **Reproducibility and auditability.** Every pipeline produces deterministic or statistically characterised outputs. All parameters, seeds, and environmental dependencies are documented. Any result can be reproduced from the `ProcessRecipe`.

### E.2 The lifecycle orchestrator

The `DownstreamProcessOrchestrator` is the load-bearing class. Its contract:

```python
orch = DownstreamProcessOrchestrator()
result = orch.run(recipe)            # FullResult
report = result.run_report           # RunReport with evidence ladder
```

Internally:

1. `resolve_lifecycle_inputs(recipe)` typechecks the recipe against the `ProcessRecipe` schema.
2. `_run_<family>(...)` dispatches to the family-specific M1 pipeline (alginate, cellulose, PLGA, or `_run_v9_2_tier1` for the 10 composite families that route through `composite_dispatch`).
3. `M2 orchestrator` consumes the `MicrosphereResult` and runs the staged functionalisation.
4. `run_method_simulation` consumes the resulting `FunctionalMicrosphere` plus a `PerformanceRecipe` and produces the `MethodSimulationResult`.
5. The `RunReport` rolls up evidence tiers via `compute_min_tier` and surfaces the weakest tier as the run's headline.

### E.3 The parallel-module + delegate-and-retag pattern

Adding a new polymer family to DPSim follows a strict pattern (D-016 / D-017 / D-027 / D-037):

1. **Create a new file** in `src/dpsim/level2_gelation/` rather than modifying an existing solver.
2. **Delegate to the closest existing solver** in a sandbox where the family is temporarily set to the delegate's expected value.
3. **Re-tag the result** with the new family's manifest (`L2.<family>.<tier>_v<cycle>` model_name, family-specific `assumptions`, family-specific `calibration_ref`).

This pattern guarantees bit-for-bit equivalence with the v9.1 calibrated kernels by construction. Adding a family does not perturb existing-family results.

### E.4 The evidence-tier inheritance rule

```
M1 calibration tier   ──cap──→   M2 calibration tier
                                      │
                                      ↓ cap
                                M3 calibration tier
```

If M1 reports `qualitative_trend`, the entire downstream pipeline is capped at `qualitative_trend`. The simulator does not allow M2 or M3 to "claim more confidence than its inputs." This rule is enforced in `RunReport.compute_min_tier` and surfaced in the evidence ladder UI.

### E.5 The `.value` enum-comparison rule

Streamlit reloads `dpsim.datatypes` on every rerun, minting a new enum class. Identity comparisons (`is` / `is not`) silently break after the first rerun. **Always compare enum members by `.value`.** This rule is AST-enforced by `tests/test_v9_3_enum_comparison_enforcement.py`, which scans `src/dpsim/` and `tests/` and fails the build on any `is` comparison against `PolymerFamily`, `ACSSiteType`, `ModelEvidenceTier`, or `ModelMode`.

---

## F. Chemical and Physical Principles

### F.1 M1 emulsification

**Kolmogorov turbulence.** In a stirred tank, the smallest eddy size is set by the Kolmogorov microscale `η = (ν³/ε)^(1/4)`, where `ν` is kinematic viscosity and `ε = 2π·N³·D²·N_p` is the mass-specific energy dissipation rate (impeller speed `N` [rev/s], impeller diameter `D` [m], power number `N_p`). Stable droplets cannot be smaller than `η`.

**Surface tension and Weber number.** Droplet break-up occurs when the inertial stress (proportional to `ρu²`) exceeds the cohesive stress from interfacial tension `σ`. The critical Weber number is `We_crit ≈ 1` (Hinze 1955). The equilibrium d32 in a stirred tank scales as `d32 ∝ ε^(-2/5) · σ^(3/5) · ρ_c^(-1/5)` (Hinze-Kolmogorov).

**Surfactant action.** Surfactants reduce `σ` (typically 30–50 mN/m → 1–10 mN/m for paraffin/water with Span-80) and stabilise droplets against coalescence by Marangoni stresses. The equilibrium film thickness is set by surfactant diffusion + drainage timescales.

### F.2 M1 gelation (L2 mechanisms)

**Thermal helix-coil (agarose).** Cooling below T_gel ≈ 38 °C drives a helix-coil transition with a sharp first-order signature. The order parameter follows a tanh-like temperature dependence; junction-zone density scales as `~ exp(-ΔH/kT)`.

**Ionic egg-box (alginate Ca²⁺).** Ca²⁺ bridges pairs of guluronate ("G-block") residues with a Gibbs energy of approximately −5 kJ/mol per junction. Shrinking-core diffusion controls the gel-front advance: `r_front(t) ≈ R · √(1 - t/τ)` where `τ = R² · ε / (6·D_Ca·c_Ca,bath)`.

**NIPS phase separation (cellulose).** Spinodal decomposition under a Cahn-Hilliard free-energy functional `F[φ] = ∫(W(φ) + ½κ|∇φ|²)dV`. Bicontinuous morphology emerges from a deep quench (high χ); cellular morphology from a shallow quench. The simulator's most demanding solver — see Appendix G.

**Solvent evaporation (PLGA).** DCM diffuses out of polymer-rich droplets into the aqueous phase. PLGA concentration follows `dc/dt = D · ∇²c - k_evap · (c - c_eq)`. Vitrification freezes the morphology when the local Tg crosses ambient temperature.

### F.3 M2 chemistry

**Reactive-site density.** Surface OH, NH₂, COOH, etc. concentrations are computed from the M1 ligand-accessible area and the polymer's intrinsic functional-group density per monomer. The reactive-site state is tracked as an **ACS state vector** indexed by `ACSSiteType`.

**Coupling kinetics.** Every reagent profile carries an Arrhenius rate constant `k(T) = A · exp(-E_a/RT)`. The default coupling kinetics are second-order: `dq/dt = k · [reagent] · [site]`. Hydrolysis competes with coupling for hydrolysable reagents (e.g. NHS esters) at rate `k_hydrolysis · [reagent] · [H₂O]`.

**Activity retention.** The fraction of bound ligand whose binding-pocket activity is preserved post-coupling. Modelled as a temperature- and pH-dependent factor with a default of 0.85 for protein affinity ligands. Wet-lab calibration is strongly recommended.

**Site balance and mass balance.** Every reactive site consumed must appear as a product site (or a hydrolysis caveat). Validation checks `Σ(targets_consumed) == Σ(products_formed) + losses` to within the M2 mass-balance tolerance.

### F.4 M3 chromatography

**Lumped Rate Model (LRM).** The packed column is modelled as a 1-D advection-dispersion-adsorption system:

```
∂C/∂t + u·∂C/∂z = D_ax·∂²C/∂z² + (1-ε)·k_f·(C_p - C)
∂C_p/∂t = k_f·(C - C_p) - (1-ε_p)·k_ads·(C_p · q_max·K_L/(1+K_L·C_p) - q)
∂q/∂t = k_ads·(q* - q)
```

with `q* = q_max·K_L·C_p / (1 + K_L·C_p)` (Langmuir isotherm). The system is semi-discretised over `n_z` axial cells and integrated by `solve_ivp`.

**Pressure drop.** Kozeny-Carman correlation:
```
ΔP/L = 150 · (1-ε)² / ε³ · μ·u / d_p² + 1.75 · (1-ε) / ε³ · ρ·u² / d_p
```

**Bed compression.** A first-order linear elastic model: `ε(σ) = ε₀ · (1 - σ/E*)` where `E*` is the effective bed modulus. Bed compression is reported alongside pressure drop in the operability gates.

**Dynamic Binding Capacity (DBC).** DBC₅, DBC₁₀, DBC₅₀ are the loaded amounts at which the breakthrough C/C₀ first exceeds 5%, 10%, 50% respectively. Computed by integrating the breakthrough curve.

### F.5 MC-LRM uncertainty propagation

**Latin Hypercube Sampling (LHS).** Stratified sampling that guarantees better-than-IID convergence on monotone integrands (McKay 1979). For independent marginals, LHS is the default; for full posterior covariance, multivariate-normal sampling is used.

**Tail-aware tolerance tightening.** When a sampled parameter vector lies > `tail_sigma_threshold · σ` from the posterior mean, BDF tolerances are tightened by 10× (rtol → rtol × 0.1, atol → atol × 0.1). This is a Tier-1 numerical safeguard, not a substitute for clipping.

**Reformulated AC#3 (SA-Q3 / D-047).** R-hat does not apply to LHS draws (which are independent by construction). The load-bearing convergence diagnostics are:

- **Quantile-stability plateau.** Compare P50 over the final 25% of samples vs the first 75%. Pass if relative difference < 1%.
- **Inter-seed posterior overlap.** `(max - min) P50 across seeds / |median P50|`. Pass if ≤ 5%.

R-hat is reported informationally — it should be near 1.0 for any well-mixed run.

---

## G. Formulas and Mathematical Theorems

### G.1 Kolmogorov scaling (M1 d32)

For stirred-tank emulsification in the inertial-subrange regime:

```
d32 = C_K · (σ / ρ_c)^(3/5) · ε^(-2/5)
```

with `C_K ≈ 0.06` (Hinze 1955; Kolmogorov 1949). This gives `d32 ∝ N^(-1.2) · D^(-0.8)` when ε is expressed via impeller power.

### G.2 Egg-box gel front (alginate Ca²⁺)

Shrinking-core diffusion of Ca²⁺ into an alginate droplet of radius R:

```
1 - 3·(r/R)² + 2·(r/R)³ = (6 · D_Ca · c_Ca,bath / (ε · R²)) · t
```

where `r` is the unreacted-core radius, `D_Ca ≈ 1.0 × 10⁻⁹ m²/s` (Ca²⁺ in dilute aqueous), and `ε` is the alginate ion-binding stoichiometry (2 per Ca²⁺).

### G.3 Cahn-Hilliard NIPS

The free-energy functional:

```
F[φ] = ∫_V (W(φ) + (κ/2)|∇φ|²) dV
```

with `W(φ) = a·φ²·(1-φ)²` (double-well). The evolution is:

```
∂φ/∂t = M · ∇²(δF/δφ) = M · ∇²(W'(φ) - κ·∇²φ)
```

Numerical integration: the reference DPSim solver uses semi-implicit Fourier spectral integration for stability. Bicontinuous structure emerges spontaneously when the initial composition lies inside the spinodal (`d²W/dφ² < 0`).

### G.4 Langmuir isotherm

```
q* = q_max · K_L · C / (1 + K_L · C)
```

Linearisation in the dilute regime: `q* ≈ q_max · K_L · C` (slope = `q_max · K_L`). Saturation in the concentrated regime: `q* → q_max`.

### G.5 Kozeny-Carman pressure drop

```
ΔP/L = 150 · (1-ε)² / ε³ · μ·u / d_p²    (Darcy / viscous-dominant)
       + 1.75 · (1-ε) / ε³ · ρ·u² / d_p    (Forchheimer / inertial-dominant)
```

where `u` is the superficial velocity, `μ` and `ρ` are fluid properties, `d_p` is the bead diameter.

### G.6 Reynolds and Peclet numbers

For an LRM column:

```
Re_p = ρ · u · d_p / μ                  (particle Reynolds)
Pe   = u · L / D_ax                     (axial Peclet)
Bo   = u · d_p / D_p                    (Bodenstein)
```

DPSim flags `Pe < 50` (axial dispersion dominates over advection) and `Re_p > 10` (laminar approximation breaks down) as scientific diagnostics.

### G.7 Gelman-Rubin R-hat (informational)

```
R_hat = sqrt( (n-1)/n · W + (1/n) · B ) / W
```

where `n` is per-chain length, `W` is within-chain variance, `B` is between-chain variance. For LHS draws, `R_hat → 1.0` because chains are independent. **DPSim treats R-hat as informational only.**

### G.8 LHS variance reduction (McKay 1979)

For a monotone integrand `g(x)`, LHS estimator variance is bounded above by IID estimator variance:

```
Var(I_LHS) ≤ Var(I_IID)
```

Empirically, the variance ratio at n=20 on a linear integrand is ≥ 1.5× tighter for LHS — this is the test floor in `test_lhs_variance_reduction_vs_iid_at_low_n`.

---

## H. Standard Wet-Lab Protocols (Cross-Reference)

The full SDS-lite wet-lab protocols live in **Appendix J — Functionalisation Wet-Lab Protocols** (separate PDF, downloadable from the dashboard). Appendix J is keyed by `reagent_key` and covers:

| Bucket | Protocols in Appendix J | Status |
|---|---|---|
| Hydroxyl Activation | ECH, DVS, BDGE, EDC/NHS, CDI, CNBr, periodate, glyoxyl, tresyl, cyanuric, pyridyl-disulfide | Full SDS-lite + recipe |
| Ligand Coupling | DEAE / Q / CM / SP / IDA / NTA / phenyl / butyl / octyl / hexyl / glutathione / heparin | Full |
| Protein Coupling | Protein A / G / A/G / L / streptavidin / Con A / WGA / oriented Cys variants / lectins / calmodulin / boronate / peptide-affinity / oligonucleotide / amylose / chitin | Full |
| Spacer Arm | DADPA / DAH / EDA / PEG-diamine / SM(PEG)n / hydrazide / cystamine / oligoglycine / aminooxy / succinic anhydride | Full |
| Metal Charging | Ni²⁺ / Co²⁺ / Cu²⁺ / Zn²⁺ + EDTA stripping | Full |
| Protein Pretreatment | TCEP / DTT | Full |
| Washing | wash buffer + triazine dye-leakage advisory | Full |
| Quenching | ethanolamine / 2-mercaptoethanol / NaBH4 / acetic anhydride | Full |
| **Click Chemistry** | CuAAC + SPAAC (azide-side and alkyne-side variants) | v0.3.7 update |
| **Dye Pseudo-Affinity** | Cibacron Blue F3GA / Procion Red HE-3B | v0.3.7 update |
| **Mixed-Mode HCIC** | MEP HCIC | v0.3.7 update |
| **Thiophilic** | 2-Mercaptoethanol thiophilic | v0.3.7 update |
| **Boronate** | m-Aminophenylboronic acid | v0.3.7 update |
| **Peptide Affinity** | HWRGWV peptide ligand | v0.3.7 update |
| **Secondary Crosslinking** (M2 stage) | Genipin / glutaraldehyde / STMP / glyoxal / borax / HRP-tyramine / bis-epoxide / AlCl₃ | v0.3.7 update |

Every Appendix J entry contains: SDS-lite hazard block, buffer composition, reagent-prep recipe, reaction protocol, post-reaction wash, mass-balance check, common failure modes, and the `ReagentProfile` parameter mapping.

> **Always read the SDS-lite block before handling a reagent. The simulator's `hazard_class` field is a screening flag, not a substitute for a full local risk assessment.**

---

## I. Troubleshooting Table

| Symptom | Likely cause | Action |
|---|---|---|
| UI shows "Module 1 has not been run yet" on M2/M3 tab | Sequential workflow violation | Run M1 first, then M2, then M3 |
| Validation report has a red blocker on "Polymer family unknown" | Picked a family without a UI formulation page | Switch to a family with a dedicated page (agarose-chitosan, alginate, cellulose, PLGA) or use the lifecycle workflow which routes the others through composite_dispatch |
| Evidence ladder reports `qualitative_trend` everywhere | M1 calibration tier capped the chain | Check `MicrosphereResult.model_manifest.evidence_tier` — calibrate M1 first |
| `evidence_tier = unsupported` on PECTIN_CHITOSAN | `degree_of_esterification > 0.5` | High-methoxy pectin is not modelled; use DE ≤ 0.5 or treat as wet-lab-only |
| Run wall-time > 60 s | Cellulose NIPS solver | Expected — Cahn-Hilliard is the slowest M1 family |
| MC-LRM logs `n=50 < 100` warning | Too few MC samples | Use `monte_carlo_n_samples ≥ 200` for reliable bands |
| MC-LRM reports `solver_unstable = True` | Posterior tails sample non-physical values | Set `monte_carlo_parameter_clips` or use `make_langmuir_lrm_solver` (raises ValueError on non-physical → driver resamples) |
| MC-LRM `convergence_pass = False` | Inter-seed posterior overlap > 5% | Increase `n_samples`; check posterior spread is not pathologically wide |
| `n_jobs=4` does not parallelise | `n_seeds = 1` | Joblib parallelism dispatches per-seed; use `n_seeds ≥ 2` (default 4) |
| `PymcNotInstalledError` on `fit_langmuir_posterior` | Optional `[bayesian]` extra missing | `pip install dpsim[bayesian]` |
| `BayesianFitConvergenceError` with "R-hat > 1.05" | NUTS chain not mixed | Increase `n_tune`; reduce prior tightness; check observed-data scaling |
| `BayesianFitConvergenceError` with "ESS < N/4" | Posterior is highly correlated | Use a non-centred parameterisation; or report and accept as-is |
| Pressure drop exceeds operability gate | Bed compression at high flow rate or low E* | Reduce flow rate; upgrade matrix to a higher-modulus family (agarose-chitosan, AGAROSE_DEXTRAN) |
| Mass-balance error > 2% | LRM solver tolerance too loose | Reduce `rtol` / `atol`; check `feed_duration` ≤ `total_time` |
| M2 `unsupported` evidence on EDC/NHS | No surface COOH groups on selected matrix | Use a COOH-bearing pre-modification (carboxymethyl chitosan, succinylation) and set `surface_cooh_concentration > 0` |
| Reagent dropdown is empty | No reagents in selected bucket for active polymer family | Family-compatibility matrix dropped all options; check the matrix opinion via `check_family_reagent_compatibility` |
| AlCl₃ ion-gelant has a red warning | `biotherapeutic_safe = False` | Use only for research; do not deploy to biotherapeutic resin manufacture |
| Borax row in preview lists "REVERSIBILITY WARNING" | Borax-cis-diol crosslinks dissociate at pH < 8.5 | Treat as temporary porogen; pair with covalent secondary crosslink (BDDE/ECH) |
| ProcessDossier `mc_bands` field is `null` | MC was not enabled or mc_bands not passed | Set `monte_carlo_n_samples > 0` and pass `posterior_samples` + `mc_lrm_solver` to `run_method_simulation` |
| Streamlit UI: enum identity comparison appears to fail after rerun | `is` instead of `.value` comparison | CLAUDE.md rule: always compare by `.value`; AST gate enforces this |
| Print of an absolute path crashes on Windows | cp1252 encoding + `文档` (Chinese) in repo path | Add `sys.stdout.reconfigure(encoding="utf-8")` at top of any path-printing script |
| Python 3.14 + scipy BDF tests timeout | Project pinned to `>=3.11,<3.13` per ADR-001 | Use the supported Python range; 3.14 is unsupported |

---

## Disclaimer

This manual and the DPSim simulator are provided for informational, research, and screening purposes. Every result must be interpreted with explicit unit consistency checks; pH / temperature / reagent / buffer compatibility checks; calibration-domain checks; M1 residual oil / surfactant carryover limits; M2 site and mass balance; M2 ligand density / leaching / free-protein wash / activity-retention assays; M3 pressure / compression / Reynolds-Peclet / breakthrough / recovery checks; explicit assumptions; and wet-lab caveats.

DPSim does not constitute regulatory, clinical, or manufacturing release. The exported wet-lab SOP is a development scaffold that must be reviewed under your local safety and quality systems before bench execution.

---

*End of Polysaccharide-Based Microsphere Emulsification Simulator — First Edition (Edition 2.0).*
