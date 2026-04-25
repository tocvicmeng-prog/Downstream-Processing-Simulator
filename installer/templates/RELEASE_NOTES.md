# DPSim __DPSIM_VERSION__ — Release Notes

**Release date:** 2026-04-25
**Platform:** Windows 11 x64 (Windows 10 x64 also supported)
**Python:** 3.11 or 3.12 (3.13+ unsupported per ADR-001)

This release of the **Downstream Processing Simulator** (DPSim) ships
the cumulative work of the v0.2.0 → v0.3.x cycle. Both an MSI-style
one-click **installer** (`DPSim-__DPSIM_VERSION__-Setup.exe`) and a
**portable ZIP** (`DPSim-__DPSIM_VERSION__-Windows-x64-portable.zip`)
are provided for the same payload.

---

## What's new since the v0.1.0 baseline

### v0.2.0 — Functional optimisation

- Polymer family catalogue extended from 4 to 18 UI-enabled families
  (added: agarose-only, chitosan-only, dextran, amylose,
  hyaluronate, κ-carrageenan, agarose-dextran, agarose-alginate,
  alginate-chitosan, chitin, pectin, gellan, pullulan, starch).
- 50 new M2 reagents shipped: oriented protein-A variants,
  click chemistry (CuAAC + SPAAC), dye pseudo-affinity, mixed-mode
  HCIC, thiophilic, boronate, peptide affinity, oligonucleotide,
  material-as-ligand (amylose/MBP, chitin/CBD-intein), expanded
  spacer-arm and metal-charging libraries.
- Wet-lab calibration ingestion path
  (`dpsim.calibration.wetlab_ingestion`) with strict tier-promotion
  ladder.

### v0.3.0 — P5++ MC-LRM uncertainty propagation

- New Monte-Carlo LRM driver (`dpsim.module3_performance.monte_carlo`)
  drawing posterior samples from a `PosteriorSamples` container and
  re-solving the lumped-rate model at each draw. Tier-1 numerical
  safeguards (tail-aware tolerance tightening, abort-and-resample,
  5-failure cap) and Tier-2 parameter clipping are wired through
  `run_method_simulation` via three new `DSDPolicy` fields.
- Reformulated convergence diagnostics (per the Scientific Advisor's
  Mode-1 brief): quantile-stability plateau + inter-seed posterior
  overlap. R-hat reported informationally only.

### v0.3.1 — Optional Bayesian posterior fitting

- `fit_langmuir_posterior()` via pymc/NUTS, behind a new
  `pip install dpsim[bayesian]` extra (~700 MB; not pulled by the
  installer's default `[ui,optimization]` extras).
- Mandatory R-hat / ESS / divergence convergence gates raise
  `BayesianFitConvergenceError` on failure.

### v0.3.2 — UI bands + dossier MC export

- Plotly P05/P50/P95 envelope plot on the M3 breakthrough view.
  SA-Q4 / SA-Q5 modelling assumptions surfaced as a footer
  annotation.
- `ProcessDossier.mc_bands` field with JSON-serialisable schema
  `mc_bands.1.0`; curves decimated to 100 points by default.

### v0.3.3 — v9.5 Tier-3 multi-variant composites

- Three composite families promoted from data-only placeholder
  status: pectin-chitosan PEC, gellan-alginate composite,
  pullulan-dextran composite. Total UI-enabled polymer families
  is now 21.
- Borax reversibility warning surfaced more prominently in the
  M1 page preview.

### v0.3.4 — M2 reagent dropdown audit fix

- Replaced the hardcoded if/elif chain in tab_m2.py with a
  declarative `_BUCKET_TO_MODES` map. The 17-bucket Chemistry
  dropdown now auto-surfaces every reagent shipped in
  `REAGENT_PROFILES`. Coverage: 50/94 → **94/94 (100%)**.
- 8 new chemistry buckets (Click Chemistry, Dye Pseudo-Affinity,
  Mixed-Mode HCIC, Thiophilic, Boronate, Peptide Affinity,
  Oligonucleotide, Material-as-Ligand).

### v0.3.5 — Ion-gelant picker + ACS visibility + crosslinker docs

- New ion-gelant expander on the M1 page surfaces all 13 entries
  from `ION_GELANT_REGISTRY` + `FREESTANDING_ION_GELANTS`. Was 1/13
  surfaced; now **13/13**. Non-biotherapeutic-safe (Al³⁺) entries
  carry a red UI warning.
- M2 reagent caption now reads `target_acs → product_acs` for every
  selected reagent. ACS coverage 23/25 (only the passive
  `sulfate_ester` and `alkyne` remain unreferenced — see v0.3.6).
- Cross-reference comments document the intentional split between
  `dpsim.reagent_library.CROSSLINKERS` (M1 / L3 covalent hardening)
  and `REAGENT_PROFILES[mode='crosslinker']` (M2 secondary).

### v0.3.6 — Closed all tracked v0.3.x follow-ons

- Click chemistry alkyne reference closed: added inverse-direction
  `cuaac_click_alkyne_side` and `spaac_click_alkyne_side` reagents
  (target_acs=ALKYNE). REAGENT_PROFILES count: 94 → 96. ACS
  coverage 23/25 → **24/25** (only the passive carrageenan
  sulfate-ester remains unreferenced, by design).
- `run_mc(n<100)` now emits a low-N warning per the R-G2-2
  mitigation.
- Joblib parallelism wired in `run_mc` (was log-warning-only):
  per-seed sub-runs dispatch via `joblib.Parallel(backend='loky')`
  when `n_jobs > 1`. AC#4 byte-identical determinism preserved.
- New `mc_solver_lambdas.make_langmuir_lrm_solver()` helper —
  production MC users no longer write the LRM solver lambda by hand.
- Pectin DE-dependence: `solve_pectin_chitosan_pec_gelation` accepts
  `degree_of_esterification`; HM (DE>0.5) routes to
  `evidence_tier=UNSUPPORTED` with an explicit warning.
- Gellan-alginate: accepts `c_K_bath_mM`; logistic K⁺ saturation
  lifts the gellan-helix reinforcement factor (Morris 2012 curve).
- Pullulan-dextran: accepts `crosslink_chemistry` literal (`"ech"`
  | `"stmp"`); STMP path applies a 1/0.85× pore-size expansion per
  Singh 2008 phosphate-triester data.

### v0.3.7 — First Edition manual refresh + Appendix J v0.3.x addendum

- User manual (`docs/User_Manual_First_Edition.pdf`) rewritten from
  the v9.1 baseline. New structure: Part I (Operator quickstart),
  Part II (Platform Catalogue, M2 Chemistry, M3 / MC, Calibration
  loop), Part III (9-section Reference Appendix). Workflow charts
  paired with complex procedural terminology throughout.
- Appendix J (`docs/Appendix_J_Functionalization_Protocols.pdf`)
  extended with § J.11 v0.3.x Addendum: cross-reference table for
  every v0.3.x reagent_key + 13 new SDS-lite protocol stubs
  (cyanuric chloride, genipin, borax reversibility warning, HRP /
  H₂O₂ / tyramine, AlCl₃ non-biotherapeutic warning, glutathione/
  GST-tag, calmodulin/TAP-tag, Cibacron Blue / Procion Red, MEP
  HCIC, thiophilic 2-ME, m-APBA boronate, oligonucleotide DNA,
  material-as-ligand).

---

## Installer features

- **EULA-first wizard** — the very first installer page shows the
  intellectual-property + GPL-3.0 + GitHub-source statement
  (`LICENSE_AND_IP.txt`). User must accept before any files are
  written.
- **Per-user install** — default location is
  `%LOCALAPPDATA%\Programs\DPSim`. No admin elevation required;
  the post-install `install.bat` step can create the local
  `.venv\` without privilege escalation.
- **Python presence check** — if Python 3.11/3.12 is not on
  PATH, the wizard offers to open the python.org Windows download
  page in your default browser before installing.
- **Optional Start-Menu group + desktop shortcut** —
  user-selectable in the Tasks page.
- **Bundled documentation** — both the First Edition manual and
  Appendix J ship as PDFs in `docs\`. They are also reachable via
  the upper-right corner of the Streamlit dashboard.
- **Clean uninstaller** — removes `.venv\` plus every file the
  installer placed. Leaves user data and any files outside the
  install directory untouched.

## Portable ZIP features

For users who prefer unzip-and-run:

- Same payload as the installer (wheel, configs, docs, launchers,
  EULA, LICENSE).
- Extracts to a self-contained `DPSim-X.Y.Z-Windows-x64\` folder.
- Run `install.bat` once inside the unzipped folder to create the
  `.venv\` and pip-install the bundled wheel.
- Run `launch_ui.bat` to start the Streamlit dashboard.
- Delete the folder to remove (no Start Menu / registry footprint
  to clean up).

## System requirements

- Windows 11 x64 (Windows 10 x64 also supported).
- Python 3.11 or 3.12.
- 2 GB free disk for the local `.venv\`.
- 8 GB RAM recommended (4 GB minimum).
- Internet during first install (downloads dependencies from PyPI).

## Source code

The canonical source-code repository is published on GitHub at
<https://github.com/tocvicmeng-prog/Downstream-Processing-Simulator>.
Each tagged release is available under the **Releases** tab.

## Licence

GNU General Public License v3.0 (GPL-3.0). Full text in
`LICENSE.txt`. Intellectual property in this software belongs to
**Holocyte Pty Ltd**. By installing or using DPSim you accept the
GPL-3.0 terms.
