# Wet-Lab Calibration Plan — v9.3

**Document ID:** WETLAB-v9.3-CAL-001
**Date:** 2026-04-25
**Author role:** /dev-orchestrator + /scientific-advisor jointly
**Audience:** R&D bench team, /rd-researcher
**Resolves:** Q-013 (chitosan-only / dextran-ECH calibration) and Q-014 (18 v9.2 reagent profile validation) from `HANDOVER_v9_2_CLOSE.md` § 7.

---

## 1. Why this document exists

v9.2 landed every Tier-1 simulator module the SA screening report identified — 41 modules, 354 passing tests, every chemistry profile carrying a peer-reviewed kinetic constant. **What the simulator cannot do without bench data is convert SEMI_QUANTITATIVE evidence tiers into VALIDATED_QUANTITATIVE.** Q-013 and Q-014 are wet-lab work; this document records the calibration plan so the next bench session can pick it up.

This is the only Q-item from the v9.2 close handover that was deferred for material reasons (no instrument time, no reagents in inventory) rather than scope reasons. Q-010, Q-011, Q-012, and Q-015 all closed in code on 2026-04-25.

---

## 2. Q-013 — Solver kernel calibration (HIGH priority)

Two v9.2 L2 solver kernels currently land at SEMI_QUANTITATIVE with explicit ±50 % / ±30 % magnitude uncertainty. Each needs a small wet-lab campaign to promote to CALIBRATED_LOCAL or VALIDATED_QUANTITATIVE tier.

### 2.1 Chitosan-only solver (A2.3)

**Implementation:** `src/dpsim/level2_gelation/chitosan_only.py`
**Current tier:** SEMI_QUANTITATIVE; ±50 % magnitude uncertainty
**Calibration needs:**

| Parameter | Symbol | Current default | Calibration plan |
|---|---|---|---|
| Pore-size scaling prefactor | `50e-9 * (10/c)^0.5` (in m) | 50 nm at 1 % w/v | Make 5 chitosan-only beads (genipin-crosslinked, inverse emulsion) at c = 5, 10, 20, 30, 40 mg/mL, DDA = 0.85 ± 0.02. SEC inverse calibration with dextran probes (0.1, 1, 10, 100, 1000 kDa). Fit pore size, then refit prefactor and exponent. |
| Porosity intercept | 0.85 | linear in c_chitosan | Same beads as above; volumetric porosity by gravimetric water uptake or Hg porosimetry (one bead set sacrificed per c-point). |
| Crosslinking conversion | `alpha_final = 0.95` | constant default | TNBSA assay or NMR for residual primary amines on bead lyophilisate at standard genipin dose (2 mM, 24 h, 37 °C). |
| pKa amine sigmoid | 6.4 (Sorlier 2001) | literature value | Verify by potentiometric titration of the actual lab chitosan stock. |

**Acceptance criterion:** all five fitted parameters land within ±15 % of the current defaults, OR the SEMI_QUANTITATIVE flag is replaced with CALIBRATED_LOCAL with the new fitted values.

**Estimated bench effort:** 1 R&D scientist × 2 weeks. Reagents: chitosan (Sigma 448877; medium MW), genipin (Wako 078-03021), TNBSA assay kit (Pierce 28997), dextran probe set (Polymer Standards Service).

### 2.2 Dextran-ECH solver (A2.4)

**Implementation:** `src/dpsim/level2_gelation/dextran_ech.py`
**Current tier:** SEMI_QUANTITATIVE within `c_dextran ∈ [3, 20] %` and `ECH:OH ∈ [0.02, 0.30]`; degrades to QUALITATIVE_TREND outside
**Calibration needs:**

| Parameter | Current default | Calibration plan |
|---|---|---|
| Sephadex calibration constants K, c_ref, ECH_ref, exponents | K = 10 nm, c_exp = -0.6, ECH_exp = -0.4 | Make 6 dextran-ECH beads at known (c_dextran, ECH:OH) points spanning the calibration window; characterise pore size by SEC inverse calibration (same dextran probe set as 2.1). Refit log-linear correlation. |
| Porosity-pore-size mapping | log-linear (Hagel 1996) | Same beads; pure verification — no expected change from Hagel calibration if the bench lab uses standard ECH conditions. |
| Default ECH:OH if user provides 0.0 | Sephadex G-100 baseline = 0.10 | Verify against in-house G-100-equivalent batch; if lab uses different chemistry (e.g., epoxy-ether instead of ECH), reset baseline. |

**Acceptance criterion:** fitted constants reproduce Sephadex G-25 / G-100 / G-200 calibration anchors to ±10 % pore size.

**Estimated bench effort:** 1 R&D scientist × 1 week (less than 2.1 because Sephadex chemistry is a settled commercial reference).

---

## 3. Q-014 — 18 v9.2 reagent profile validation (MEDIUM priority)

Each of the 18 reagent profiles added in M1–M9 carries a literature-anchored kinetic constant set. Q-014 is to verify that those kinetic predictions match in-house bench results within the ±20 % acceptance band (per Q-003 from the joint plan).

### 3.1 Validation matrix

| # | Profile | Acceptance reference | Bench protocol summary |
|---|---|---|---|
| 1 | `cnbr_activation` | Cytiva Sepharose 4B datasheet | IgG (5 mg/mL, pH 8.3, 4 °C, 16 h) on CNBr-Sepharose; measure DBC at 10 % breakthrough; predicted ≥ 35 mg/mL ±20 %. |
| 2 | `cdi_activation` | Hearn 1981 | Lysozyme (1 mg/mL, pH 9, 25 °C, 4 h) on CDI-agarose; same DBC protocol. |
| 3 | `hexyl_coupling` | Hjertén 1973 | Lysozyme HIC retention factor at 1 M (NH4)2SO4 vs descending salt gradient; compare to butyl/octyl reference. |
| 4 | `periodate_oxidation` | Bobbitt 1956 | NaIO4 5 mM, 1 h, 4 °C on agarose 4 %; measure aldehyde density by DNPH. |
| 5 | `adh_hydrazone` | Liu & Wilcox 1976 | ADH coupling efficiency on oxidized agarose; FTIR/NMR for hydrazone; verify hydrolysis at pH 4 vs pH 7. |
| 6 | `aminooxy_peg_linker` | Kalia & Raines 2008 | Aminooxy-PEG2k coupling on oxidized agarose; oxime stability vs hydrazone in 7-day buffer challenge. |
| 7 | `cyanuric_chloride_activation` | Korpela 1968 | First-Cl substitution at 4 °C; measure activated-site density and second-Cl reactivity. |
| 8 | `cibacron_blue_f3ga_coupling` | Atkinson 1981 | BSA depletion on Blue Sepharose; predicted ≥ 90 % depletion at 1:1 mol ratio ±20 %. |
| 9 | `triazine_dye_leakage_advisory` | Lowe & Pearson 1984 | Bound dye density (A610 spectrophotometric); leach rate during 0.1 N NaOH regeneration; flag if > 1 ppm/cycle. |
| 10 | `thiophilic_2me_coupling` | Porath 1985 | IgG capture in 0.7 M K2SO4; elute in low salt; predicted DBC ≥ 20 mg/mL ±20 %. |
| 11 | `mep_hcic_coupling` | Burton & Harding 1998 | IgG capture pH 7 → elution pH 4; predicted DBC ≥ 25 mg/mL; predicted recovery ≥ 85 % ±20 %. |
| 12 | `bis_epoxide_crosslinking` | Hahn 2006 | HA 1 % + BDDE 2 % (mol/mol HA-OH), 0.25 M NaOH, 25 °C, 4 h; storage modulus G' ≥ 1 kPa ±20 %. |
| 13 | `cuaac_click_coupling` | Quesada-González 2013 | Azide-PEG-COOH on alkyne-agarose at 1 mM CuSO4 / 5 mM ascorbate, 1 h, 25 °C; coupling efficiency ≥ 80 % ±20 %. Residual Cu by ICP-MS post-EDTA wash; ICH Q3D limit. |
| 14 | `spaac_click_coupling` | Agard 2004 | Same protein/handle pair as #13 but DBCO instead of alkyne; copper-free; coupling ≥ 60 % at 4 h ±20 %. |
| 15 | `glyoxyl_chained_activation` | Mateo 2007 | Glycidol on agarose at pH 11 → periodate oxidation; aldehyde density on lyophilisate by DNPH. |
| 16 | `multipoint_stability_uplift` | Mateo 2007 | CALB lipase B immobilization at pH 10, 24 h; T_50 stability uplift vs. soluble enzyme; predicted ≥ 10 °C ±5 °C. |
| 17 | `amylose_mbp_affinity` | NEB amylose-resin protocol | MBP-tagged GFP capture; predicted DBC ≥ 3 mg/mL fusion; maltose-elution recovery ≥ 80 % ±20 %. |
| 18 | `apba_boronate_coupling` | Mallia 1989 | HbA1c capture at pH 8.5; sorbitol-elution recovery ≥ 95 %; resolution from non-glycated Hb ≥ 1.5 ±20 %. |

### 3.2 Pass criterion

Per Q-003 resolution in `DEVORCH_v9_2_JOINT_PLAN.md` § 11: predicted observable within the source's reported uncertainty band, OR within ±20 % when source uncertainty is not reported.

### 3.3 Estimated bench effort

18 profiles × 0.5–2 days each = ~3–4 weeks for one R&D scientist. Most are short-cycle column experiments; #12 (BDDE-HA) and #16 (CALB thermostability) are the longer-cycle items.

---

## 4. Bench-side preconditions before this calibration begins

These are not blockers, but the campaign goes faster if these are in place first:

- [ ] `Q-009` is shipped (it is — wired into pipeline orchestrator on 2026-04-25). Without Q-009, the simulator cannot produce a full pipeline result for AGAROSE / CHITOSAN / DEXTRAN to compare against bench data.
- [ ] Local Python environment fixed to 3.11–3.13 per the project pin (currently 3.14 locally — see CLAUDE.md ADR-001). Without this, the M3 breakthrough simulator times out under scipy BDF on the test bench.
- [ ] Lab chitosan stock characterised for actual DDA (potentiometric titration) — affects 2.1 calibration accuracy.
- [ ] ICP-MS access scheduled for #13 Cu residual measurement.

---

## 5. Reporting back — concrete ingestion procedure (v9.4 follow-on)

The simulator-side ingestion path is now implemented (v9.4 follow-on
commit). The bench scientist does NOT need to touch Python code: a
YAML campaign file documents the bench measurements, and the
ingestion module updates ReagentProfile / solver constants with
provenance recording and tier promotion.

### 5.1 Workflow

1. **Bench scientist** fills in a YAML campaign file based on either:
   - `data/wetlab_calibration_examples/Q-013_chitosan_kernel_calibration.yaml`
     — for Q-013 kernel calibrations (chitosan-only, dextran-ECH).
   - `data/wetlab_calibration_examples/Q-014_v9_2_profile_validation.yaml`
     — for Q-014 ReagentProfile validations.
2. **Ingestion check** (no permanent changes yet):

   ```python
   from pathlib import Path
   from dpsim.calibration.wetlab_ingestion import (
       load_campaign, apply_campaign, propose_solver_constant_patches,
   )

   campaign = load_campaign(Path("path/to/your_campaign.yaml"))
   result = apply_campaign(campaign)
   print(result.manifest())          # JSON summary
   print(f"Tier promotions: {result.tier_promotions}")
   print(f"Solver-constant patches: {propose_solver_constant_patches(campaign)}")
   ```

   This validates the YAML, applies updates **in memory** (the global
   `REAGENT_PROFILES` dict is NOT mutated), and reports which profiles
   were updated, which were skipped (unknown profile keys), and which
   failed (unpatchable parameters). The `manifest()` JSON is suitable
   for audit-log archival.

3. **Code commit** (permanent changes): once the bench team is
   satisfied with the ingestion result, an engineer translates the
   campaign into source-code edits:

   - For each `result.profile_updates[key]`: edit
     `src/dpsim/module2_functionalization/reagent_profiles.py` to
     update the kinetic constants on the corresponding profile and
     promote `confidence_tier` per the campaign.
   - For each `propose_solver_constant_patches()` entry: edit the
     module-level constant in the corresponding `level2_gelation/*.py`
     file with the new value and a `# CALIBRATED v9.x: <campaign_id>`
     comment.
   - Add a regression test under `tests/test_v9_x_calibration_*.py`
     pinning the new value (delta-vs-default within the bench's
     posterior σ).

4. **Audit trail**: the `IngestionResult.manifest()` JSON is committed
   alongside the source-code changes, and the campaign YAML file is
   committed under `data/wetlab_calibration_runs/<campaign_id>.yaml`
   (separate directory from the `_examples`).

### 5.2 What can be patched

The wet-lab ingestion module enforces a strict whitelist of patchable
fields in `wetlab_ingestion.py::_PATCHABLE_NUMERIC_FIELDS` and
`_PATCHABLE_STRING_FIELDS`. **Identity fields** (`name`, `cas`,
`target_acs`, `chemistry_class`, etc.) are deliberately NOT patchable —
the bench scientist cannot accidentally rename a profile or change
its CAS number through a calibration campaign. If a new patchable
field is needed, the engineer adds it to the whitelist in a code
commit (so the change is reviewable).

### 5.3 Tier promotion rules

The ingestion module enforces an upward-only tier ladder:

```
unsupported < ranking_only < qualitative_trend < semi_quantitative
            < calibrated_local < validated_quantitative
```

A campaign can only **promote** a profile up the ladder. Attempting
to downgrade (e.g., assigning `qualitative_trend` to a profile that
is already `calibrated_local`) raises `ValueError` in strict mode.
This is a deliberate data-integrity guard: a real bench measurement
should never decrease evidence quality below the literature-anchored
default. (Non-strict mode is available for the rare measurement-error
retraction case.)

### 5.4 Test coverage

`tests/test_wetlab_ingestion.py` covers:
- YAML/dict loading + schema validation (4 tests)
- Profile patching + provenance recording (6 tests)
- Tier promotion (3 tests)
- End-to-end campaign application + manifest serialisation (5 tests)
- Solver-constant patch proposals (4 tests)
- Whitelist coverage (2 parameterised tests)

34 tests total; all pass on the v9.x surface.

---

## 6. Status

| Q-item | Status | Code-actionable | Wet-lab actionable |
|---|---|---|---|
| Q-009 | RESOLVED 2026-04-25 (in-code: `_run_v9_2_tier1` branch) | ✅ | — |
| Q-010 | RESOLVED 2026-04-25 (in-code: `formulation.ech_oh_ratio_dextran` field) | ✅ | — |
| Q-011 | RESOLVED 2026-04-25 (in-code: AST enforcement test; 1 latent bug fixed in `material_constants.py:78`) | ✅ | — |
| Q-012 | RESOLVED 2026-04-25 (in-code: Tier-2 preview expander in family selector) | ✅ | — |
| Q-013 | **PENDING — wet-lab work; this document is the plan** | — | ⏳ |
| Q-014 | **PENDING — wet-lab work; this document is the plan** | — | ⏳ |
| Q-015 | RESOLVED 2026-04-25 (in-code: 4 specialised M3 ligand-type branches) | ✅ | — |

---

> *Q-013 and Q-014 are hand-off to the bench. The simulator-side scaffolding to receive the calibration data is in place; the campaign is now scheduling- and reagent-limited, not code-limited.*
