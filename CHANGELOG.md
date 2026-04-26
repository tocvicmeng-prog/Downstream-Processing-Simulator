# Changelog

## v0.5.0 — M2 ACS Converter epic (2026-04-27)

Closes the 7 ranked gaps from the M2 ACS-converter audit; the Scientific
Advisor verdict flips PARTIAL → READY. Joint redesign plan authored by
Scientific Advisor + Architect + Dev Orchestrator; full handover at
`docs/handover/HANDOVER_v0_5_0_ACS_CONVERTER.md`.

### Architectural changes

- New `ModificationStepType.ACS_CONVERSION` (matrix-side polysaccharide
  ACS swap) and `ARM_ACTIVATION` (arm-distal pyridyl-disulfide-class
  installation). Legacy `ACTIVATION` retained as silent alias so
  v0.4.x recipes using ECH/DVS load unchanged.
- New `ACSSiteType.PYRIDYL_DISULFIDE` member; pyridyl-disulfide
  `product_acs` corrected from chemically inverted `THIOL` to
  `PYRIDYL_DISULFIDE`, and `chemistry_class` from incorrect
  `"reduction"` to canonical `"thiol_disulfide_exchange"`.
- 6 matrix-side converters (CNBr / CDI / Tresyl / Cyanuric / Glyoxyl /
  Periodate) retagged `reaction_type="acs_conversion"` with
  `functional_mode="acs_converter"`. ECH/DVS continue to dispatch
  through the same solver.
- Sequence-enforcing FSM in a new G6 first-principles guardrail
  (`core/recipe_validation.py::_g6_acs_converter_sequence`), plus an
  in-module `orchestrator.validate_sequence()` helper. Enforces the
  canonical ACS Converter → Linker Arm → Ligand → Ion-charging order
  with skip-allowed and arm-distal precondition checks.
- New `TargetProductProfile.cip_required` flag that gates a hard
  requirement for NaBH₄ reductive lock-in after aldehyde-producing
  converters (glyoxyl-chained, periodate).

### Closed-loop reagents (4 new)

| reagent_key | target_acs | Closes loop |
|---|---|---|
| `generic_amine_to_imidazolyl_carbonate` | IMIDAZOLYL_CARBONATE | CDI → amine ligand |
| `generic_amine_to_sulfonate` | SULFONATE_LEAVING | Tresyl → amine ligand |
| `protein_thiol_to_pyridyl_disulfide` | PYRIDYL_DISULFIDE | Pyridyl-disulfide → protein -SH |
| `generic_amine_to_cyanate_ester` | CYANATE_ESTER | CNBr → any amine ligand (canonical 15-min window) |

### Bench-fidelity fixes

- New `aldehyde_multiplier` field on `ReagentProfile` (default 1.0; set
  to 2.0 on `periodate_oxidation` and `glyoxyl_chained_activation`).
  Fixes the 2× under-counting of aldehydes from Malaprade vicinal-diol
  cleavage that previously made downstream ALDEHYDE inventory wrong.
- New `wetlab_observable` field on `ReagentProfile` (e.g.,
  `A_343_pyridine_2_thione` for pyridyl-disulfide activation, used to
  anchor evidence-tier calibration to a real bench measurement).

### Family-reagent matrix expansion

- 147 new entries (7 converters × 21 polymer families) in
  `family_reagent_matrix.py`, closing the G4 guardrail gap that let
  CNBr-on-PLGA, periodate-on-alginate, etc. silently bypass.

### UI

- M2 Chemistry bucket "Hydroxyl Activation" renamed to "ACS Conversion"
  (absorbs both legacy `activator` mode and new `acs_converter` mode).
- New M2 bucket "Arm-distal Activation" for `arm_activator` mode
  (pyridyl-disulfide and successors). Renders between Spacer Arm and
  Ligand Coupling in `_BUCKET_DISPLAY_ORDER`.

### Tests

- `tests/test_v0_5_0_acs_converter.py` (NEW): 50-test gauntlet across
  enum expansion, dispatch, pyridyl-disulfide chemistry correctness,
  periodate stoichiometry, sequence FSM, closed-loop pairing, family-
  matrix coverage. All green.
- `tests/test_module2_acs.py`: ACS enum size bumped 25 → 26.
- `tests/test_module2_workflows.py`: profile count 94 → 100;
  `reaction_type` allowlist gains `"acs_conversion"` and `"arm_activation"`.
- `tests/test_v0_3_4_m2_dropdown_coverage.py`: bucket-rename + pyridyl-
  disulfide → "Arm-distal Activation".
- 308 targeted tests green; CI gates (ruff=0, mypy=0) hold.

## v0.4.19 — Direction-A standalone alignment + Streamlit 1.55 fixes (2026-04-26)

Three intertwined efforts that took the v0.4.x Direction-A shell from
"port-of-the-Streamlit-tabs" to a faithful realization of the
canonical `DPSim UI Optimization _standalone_.html` reference, while
fixing several Streamlit 1.55 regressions that had silently broken
styling, navigation, and the M3 stage.

### v0.4.x polish (P1–P10, single bundle)

- **P1** Help icon shrunk to inline 14×14 px `<details>` glyph
  (replaces the full-row `st.popover` chrome). `labeled_widget` and
  `param_row` now emit label + help + badge + unit on one row.
- **P2** M1 Hardware live tip-speed chip + vertical v_tip / Re / We
  metrics rail beside the impeller cross-section; derived volumes
  readout (Total / φ_d / O:W) with inversion warning. Uses real
  `StirrerGeometry.impeller_diameter` and paraffin-oil properties.
- **P3** M1 vessel-mode planned roadmap strip (Membrane M1.5,
  Microfluidic M2.0 surfaced as not-yet-selectable); wet-lab caveats
  card pre-Run; Targets card promoted out of the collapsed expander.
- **P4** M3 derived-geometry strip (V_bed / u_super / τ_void); M2
  pre-Run status strip with green/amber/red readiness signal.
- **P5** M1 Calibration banner with Open Stage 07 button.
- **P6** Non-A+C Hardware (alginate / cellulose / PLGA) gets the
  same chip + Re/We rail + volumes readout.
- **P7** M3 Monte-Carlo uncertainty card promoted out of the sidebar
  popover via `render_uncertainty_panel(as_card=True)`.
- **P8** M2 ACS state pre-Run preview card with placeholder cells.
- **P9** M2 reagent-bucket overview grid (17-bucket auto-fill grid
  with active-bucket highlighting from the per-step expander loop).
- **P10** **Streamlit 1.55 CSS-injection regression**: `st.html`
  silently strips `<style>` and `<script>` tags. Switched
  `inject_global_css` and the `app.py` shell-overrides block to
  `st.markdown(..., unsafe_allow_html=True)`. Without this fix the
  entire `tokens.css` was being dropped; the page only looked themed
  because Streamlit's own dark theme covered for the missing styles.

### Standalone alignment (A1–A5, B1–B6, C1, D1–D2)

- **A1** Pipeline spine collapsed from two-row (visual chrome +
  click-button overlay) to single integrated row. Each stage cell
  is an `<a href="?dpsim_stage={id}">` anchor; server consumes the
  param at render top, calls `set_active_stage`, cleans the URL.
- **A2** Dark/Light toggle actually flips theme. Replaced the JS-
  stripped `<script>` class-flip with server-side CSS reinjection —
  `inject_global_css(theme=...)` emits a second `<style>` block
  overriding `:root` vars when light. Theme query consumed BEFORE
  CSS injection so it takes effect on the same rerun.
- **A3** UI A|B switch rebuilt as a single HTML pill. Diff /
  Evidence / History segmented and the legacy DARK / LIGHT toggle
  also rebuilt as anchor pills (the previous nested-column
  `st.button` patterns wrapped to one-letter-per-line at typical
  widescreen widths).
- **A4** Polymer family selector migrated from horizontal radio
  grid to compact dropdown showing chemistry classification.
- **A5** Evidence rollup card always renders (placeholder M1/M2/M3
  rows pre-run); per-row layout uses the canonical Ladder pattern
  (36 px label │ 1 fr progress-bar │ auto badge) with bar width =
  tier_rank/5 × 100% in tier-specific colour.
- **B1** Right rail recovery on M3. The duplicate
  `render_uncertainty_panel()` call from the sidebar Analysis Tools
  popover was registering widgets with the same fixed keys as the
  new M3 primary card, raising `StreamlitDuplicateElementKey` and
  silently killing the right rail's render — user-visible as "rail
  vanishes on M3". Sidebar copy removed.
- **B2** Manual + Appendix J as compact 26 × 26 px icon-only
  download buttons in their own column right of the DARK/LIGHT
  pill (was vertically stacked text buttons that pushed the rail
  down).
- **B3** Theme toggle as single fidelity-matched button. Replaces
  the `[DARK | LIGHT]` segmented pill with one button showing a
  colored dot (teal for dark, amber for light) + current-mode
  label, click toggles. Matches the standalone byte-for-byte.
- **B4** Removed the `stHeader` border-bottom that was painting a
  faint horizontal line across the page through the brand /
  breadcrumb / search input.
- **B5** Hidden `stHeader` and `stSidebarHeader` entirely. Even
  with no border the empty headers were reserving 60 px of dead
  vertical space at the top of the page with non-clickable
  decorative icons behind them.
- **B6** Manual + Appendix J icon clipping fix. cols[8] sub-columns
  gave each icon only 16 px while the button chrome was 26 px wide.
  Widened cols[8] and re-scoped the icon-button CSS via the
  `[data-testid="stMain"]` ancestor.
- **C1** Resin Lifetime Projection promoted from sidebar popover
  into a primary M3 card matching the MC uncertainty card pattern.
  `render_lifetime_panel` gained the `as_card=False` kwarg.
- **D1/D2** Scientific Mode (Empirical Engineering / Hybrid Coupled
  / Mechanistic Research) moved from sidebar radio to a top-bar
  segmented pill matching the Diff/Evidence/History style. Lives
  at cols[4], immediately right of the recipes search input. Click
  sets `?dpsim_mode={key}`; consumed at app.py top so
  `model_mode_enum` is in effect on the same rerun.

### Quality

- `ruff check src/dpsim/visualization/` clean
- 248 / 248 UI tests pass (`test_ui_v0_4_0_modules` + chrome smoke +
  ui contract + ui workflow + ui recipe + enum-CI + M2 dropdown
  coverage)
- Visual verification in headless Chromium against
  `streamlit run src/dpsim/visualization/app.py` confirmed: spine
  renders single integrated row, theme flips correctly server-
  side, all top-bar pills render as compact horizontal anchor
  links, family is a dropdown with classification subline,
  evidence ladder shows M1/M2/M3 placeholder rows pre-run, right
  rail present on all 7 stages.

## v0.3.8 — Release Tooling Refresh (Installer + Portable ZIP) (2026-04-25)

Refreshes the Windows release-build pipeline to match the v0.3.x state
and adds a portable ZIP artifact alongside the existing one-click
installer. The intellectual-property + GPL-3.0 + GitHub-source EULA
already in place from v0.1.0 is unchanged (it already states what the
user requires).

### Two release artifacts per release

| Artifact | Use case |
|---|---|
| `release/DPSim-X.Y.Z-Setup.exe` | One-click installer with EULA wizard, Start-Menu shortcut, post-install hook, clean uninstaller. |
| `release/DPSim-X.Y.Z-Windows-x64-portable.zip` | Unzip-and-run package for users who prefer no installation, no admin, no registry footprint. |

Both artifacts share the **same payload** (wheel + configs + PDFs +
launcher batch files + EULA + LICENSE). The only difference is the
delivery wrapper. The portable ZIP is produced by the same
`installer\build_installer.bat` invocation as the installer — one
build command, two artifacts.

### Version-banner discipline

Replaced the v0.1.0 hardcoded version strings across all 8 staged
templates with an `__DPSIM_VERSION__` placeholder. The build script
now derives the version from `pyproject.toml` and substitutes the
placeholder in every staged template before compiling. Files
touched: `install.bat`, `launch_ui.bat`, `launch_cli.bat`,
`uninstall.bat`, `README.txt`, `INSTALL.md`, `RELEASE_NOTES.md`,
`WHERE_ARE_THE_PROGRAM_FILES.txt`. Result: 22 placeholder
substitutions per build; future version bumps no longer require
touching templates.

### Build pipeline (`installer\build_installer.bat`)

Five steps:

1. Build wheel + sdist via `python -m build`.
2. Stage runtime assets into `installer\stage\` (wheel, configs,
   docs PDFs, launcher templates, LICENSE, EULA). Substitute
   `__DPSIM_VERSION__` placeholders in every staged `.bat` /
   `.txt` / `.md`.
3. Locate `ISCC.exe` (Inno Setup compiler).
4. Compile installer to `release\DPSim-<version>-Setup.exe`.
5. Pack portable ZIP to
   `release\DPSim-<version>-Windows-x64-portable.zip` via
   PowerShell `Compress-Archive` (built into Windows 10/11; no
   external 7-Zip dependency).

Build wall-time: ≈ 30 s on a typical Windows 11 box.

### Refreshed RELEASE_NOTES.md

`installer/templates/RELEASE_NOTES.md` rewritten from the v0.1.0
baseline to summarise the cumulative v0.2.0 → v0.3.7 cycle in
release-note form for the GitHub release page. Covers each minor
release's key contribution (P5++ MC-LRM driver, Bayesian fit, UI
bands, v9.5 composites, M2 dropdown rewrite, audit closures,
manual refresh) plus installer + portable ZIP feature lists and
system requirements.

### Updated `installer/README.md`

Added a **Portable ZIP** section explaining the unzip-and-run
flow. Documented:

- The 5-step build pipeline.
- The "clean" guarantee (explicit list of what is excluded from
  both artifacts; staging is via named-file `copy /y` only — no
  recursive source-tree copy that could leak dev artifacts).
- The version-banner discipline (`__DPSIM_VERSION__` placeholder
  pattern).
- The release process steps including the portable ZIP smoke test.

### EULA (unchanged from v0.1.0; verified to meet requirements)

`installer/LICENSE_AND_IP.txt` already states all three required
points and is shown as the very first installer page:

- Intellectual property in this software belongs to **Holocyte Pty Ltd**.
- Software is distributed under **GPL-3.0**.
- The latest source code is published on GitHub at
  <https://github.com/tocvicmeng-prog/Downstream-Processing-Simulator>.

### `.gitignore` update

Added `installer/stage_portable/` (transient ZIP-staging directory)
to the gitignore alongside the existing `installer/stage/` entry.

## v0.3.7 — First Edition Manual Refresh + Appendix J v0.3.x Addendum (2026-04-25)

Documentation refresh covering the v0.3.x cycle. The user-facing instruction
manual has been substantially rewritten to reflect everything shipped from
v0.3.0 (P5++ MC-LRM driver) through v0.3.6 (follow-on closures). Appendix J
gains a new § J.11 v0.3.x Addendum covering the 44 reagents that surfaced
in the M2 dropdown via the v0.3.4 audit fix.

### First Edition manual (Edition 2.0)

`docs/user_manual/polysaccharide_microsphere_simulator_first_edition.md` —
~1100 lines, full rewrite. Covers:

- Updated polymer-family catalogue: 4 (v9.1) → 21 (v9.5) families across
  baseline / expansion / niche / multi-variant composite tiers, with a
  selection chart and ion-gelant reference table.
- Updated M2 chemistry catalogue: 17 chemistry buckets (was 9 before
  v0.3.4); 96 reagents (was 50); chemistry-bucket workflow chart;
  family-reagent compatibility matrix; staged-template guide.
- New M3 chapter: Lumped Rate Model description; v0.3.0 MC-LRM
  uncertainty driver with Tier-1/Tier-2 safeguards; reformulated AC#3
  convergence diagnostics; v0.3.1 optional Bayesian fit; v0.3.2 UI
  band rendering and ProcessDossier MC export.
- Calibration / wet-lab loop chapter with the evidence-tier inheritance
  rule and the v0.2.0 wet-lab ingestion path.
- Appendix restructured to the user-specified 9-section format:
  A. Detailed Input Requirements
  B. Process Steps
  C. Essential Input & Process Checklist
  D. Frequently Asked Questions (28 Q&A)
  E. Architectural Ideas and Working Principles
  F. Chemical and Physical Principles
  G. Formulas and Mathematical Theorems
  H. Standard Wet-Lab Protocols (cross-reference to Appendix J)
  I. Troubleshooting Table (24 entries)
- Workflow charts paired with complex procedural terminology
  throughout (lifecycle flow, polymer-family selection, MC dispatch,
  M2 step configuration, M3 method).

### Appendix J § J.11 addendum

`docs/user_manual/appendix_J_functionalization_protocols.md` extended
from 2254 to ~2620 lines. New section covers:

- **Cross-reference table** mapping every v0.3.x `reagent_key` (96
  reagents) to its protocol section in Appendix J.
- **§ J.11.2 Cyanuric chloride activation** — triazine anchor for dye
  pseudo-affinity ligands.
- **§ J.11.3 Genipin secondary crosslinking** — mild post-coupling
  amine-bridge.
- **§ J.11.4 Borax reversibility warning** — temporary porogen only;
  must pair with covalent secondary crosslink.
- **§ J.11.5 HRP / H₂O₂ / tyramine** — phenol-radical crosslinking.
- **§ J.11.6 AlCl₃ trivalent gelant** — non-biotherapeutic safety
  warning + research-only protocol.
- **§ J.11.7 Glutathione / GST-tag** affinity coupling.
- **§ J.11.8 Calmodulin / TAP-tag** Ca²⁺-dependent affinity.
- **§ J.11.9 Cibacron Blue / Procion Red** dye pseudo-affinity.
- **§ J.11.10 MEP HCIC** mixed-mode chromatography ligand.
- **§ J.11.11 Thiophilic 2-mercaptoethanol** ligand (T-Sorb / T-Gel).
- **§ J.11.12 m-APBA boronate** affinity for cis-diol analytes.
- **§ J.11.13 Oligonucleotide DNA** sequence-specific affinity.
- **§ J.11.14 Material-as-ligand: amylose / chitin** (B9 pattern).

Every new section carries SDS-lite hazard block, recipe with stoichiometry,
mass-balance check guidance, and reference to the relevant `reagent_key`
in `REAGENT_PROFILES`.

### PDF rebuild

`docs/user_manual/build_pdf.py` rebuilds both PDFs:

- `polysaccharide_microsphere_simulator_first_edition.pdf` (~198 KB)
- `appendix_J_functionalization_protocols.pdf` (~237 KB)
- `DPSIM_UNIFIED_DOCUMENTATION_AUDIT_2026-04-25.pdf` (~69 KB)

### UI integration (unchanged)

The upper-right corner of the dashboard already exposes both PDFs via
`st.download_button` (📘 Manual + 🧪 Appendix J), per the existing
implementation in `src/dpsim/visualization/app.py:290-345`. Auto-build
runs `build_pdf.py` on first render if either PDF is missing. No
changes to the UI layout were required for v0.3.7.

## v0.3.6 — Close All Tracked v0.3.x Follow-Ons (2026-04-25)

Closes the seven actionable follow-ons accumulated across the v0.3.x
handovers. Non-actionable items (wet-lab calibration data, pymc CI
matrix, Python 3.14 pin, v0.4.0 MC × bin-resolved DSD) remain
documented as external/architectural follow-ons.

### Fix 1 — Click chemistry alkyne reference (ACS coverage 23/25 → 24/25)

Added inverse-direction click reagent profiles in
`reagent_profiles.py`:

- `cuaac_click_alkyne_side` — CuAAC where the resin carries the alkyne
  and the ligand carries the azide.
- `spaac_click_alkyne_side` — SPAAC where the resin carries the
  strain-promoted alkyne (DBCO/BCN) and the ligand carries the azide.

Both directions are valid bench protocols. Adds `ALKYNE` to the set
of `target_acs` values referenced by `REAGENT_PROFILES`. Only
`sulfate_ester` remains unreferenced (expected — it's a passive
κ-carrageenan polymer-side surface group, not a reagent target).

REAGENT_PROFILES count: 94 → 96.

### Fix 2 — Low-N MC warning (R-G2-2 mitigation)

`run_mc(n < 100)` now emits a `WARNING`-level log noting that the
inter-seed posterior-overlap diagnostic (AC#3) becomes noisy below the
documented N≥200 floor. v0.3.5 left this as a documented but
unwarned risk.

### Fix 3 — Joblib parallelism in `run_mc` (R-G2-4 mitigation)

The v0.3.0 implementation logged a warning and ran serial when
`n_jobs > 1`. v0.3.6 actually wires joblib:

- When `n_jobs > 1` and `n_seeds > 1`, dispatch per-seed sub-runs to
  `joblib.Parallel(backend="loky")`. Each worker derives its RNG
  seed from `base_seed + i`, so determinism is preserved by
  construction.
- Refactored `_per_seed_run` to return its `clip_counts` dict (in
  addition to mutating an in-out parameter for the serial path) so
  loky workers can ship clipping diagnostics back to the parent.
- AC#4 (n_jobs=1 vs n_jobs=4 byte-identical) verified by a new test
  in `tests/test_v0_3_6_followons.py`.

Falls back gracefully to serial when joblib is not importable or
n_seeds == 1.

### Fix 4 — Solver-lambda helper (`mc_solver_lambdas.py`)

New module `src/dpsim/module3_performance/mc_solver_lambdas.py` (~100
LOC) providing `make_langmuir_lrm_solver()`. Returns a callable
matching the `LRMSolver` contract that:

- constructs a `LangmuirIsotherm` from sampled `q_max` / `K_L`,
- propagates the `tail_mode` flag into BDF tolerances (10× tighter
  by default per D-046),
- raises `ValueError` on non-physical samples (negative q_max, zero
  K_L) so the driver's abort-and-resample path fires,
- holds all other `solve_lrm` arguments fixed across samples.

Closes the v0.3.0/v0.3.2 follow-on flagged as "solver-lambda helper
for production use." Production MC users no longer need to write the
solver lambda by hand.

### Fix 5 — Pectin DE-dependence (v0.3.3 follow-on)

`solve_pectin_chitosan_pec_gelation` now accepts a
`degree_of_esterification` parameter (default 0.40, low-methoxy):

- DE ≤ 0.5 — Ca²⁺-driven egg-box ionic gelation (default, calibrated
  against Voragen 2009).
- DE > 0.5 — high-methoxy pectin requires sugar-acid co-gelation
  (sucrose + low pH); not modelled at v9.5 resolution. Solver returns
  a result with `evidence_tier = UNSUPPORTED` and an explicit
  `hm_pectin_unsupported` diagnostic so callers can branch.

### Fix 6 — Gellan-alginate mixed K⁺/Ca²⁺ bath (v0.3.3 follow-on)

`solve_gellan_alginate_gelation` now accepts `c_Ca_bath_mM` (default
50) and `c_K_bath_mM` (default 0):

- Ca²⁺ runs the alginate skeleton path unchanged.
- When `c_K_bath_mM > 0`, K⁺ contributes a logistic-saturated boost
  to the gellan helix-aggregation reinforcement (midpoint 100 mM,
  asymptote +20 % over the Ca²⁺-only baseline). Curve shape from
  Morris 2012 K⁺-binding data on low-acyl gellan.
- Mixed-bath state surfaced via `mixed_bath` diagnostic and a
  dedicated assumption block.

### Fix 7 — Pullulan-dextran STMP variant (v0.3.3 follow-on)

`solve_pullulan_dextran_gelation` now accepts a `crosslink_chemistry`
literal (`"ech"` default, or `"stmp"`):

- ECH path unchanged from v9.5 baseline.
- STMP path applies a 1/0.85× pore-size expansion to reflect STMP's
  lower junction-zone density at equivalent reagent stoichiometry
  (Singh & Ali 2008). Manifest assumption block notes the
  phosphate-triester chemistry and food-grade / biotherapeutic-
  friendly profile.

### Tests

`tests/test_v0_3_6_followons.py` — 22 tests across the 7 fixes:

- 4 click-chemistry alkyne tests (existence, target_acs reference,
  ACS coverage floor lifted to 24, surfaces in M2 Click Chemistry
  bucket).
- 2 low-N warning tests (n<100 fires; n≥100 silent).
- 2 joblib parallelism tests (byte-identical n_jobs=1 vs n_jobs=4;
  clip_counts aggregate from workers).
- 3 solver-lambda tests (callable contract; rejects bad
  parameter_names; non-physical raises).
- 3 pectin DE tests (LM default; HM → UNSUPPORTED; out-of-range
  ValueError).
- 4 gellan-alginate mixed-bath tests (Ca²⁺-only baseline, mixed-bath
  factor lift, validation errors).
- 4 pullulan-dextran STMP tests (default ECH, STMP pore expansion,
  assumption-block contents, invalid chemistry rejection).

### Audit baseline updates

- `tests/test_v0_3_5_audit_followons.py::test_known_unreferenced_acs_types_remain_documented`
  baseline updated from `{"alkyne", "sulfate_ester"}` to
  `{"sulfate_ester"}` to reflect the v0.3.6 close. The test fires
  again only if the team adds an ACSSiteType that no reagent
  references.

### Out of scope (remain external follow-ons)

- Composite-specific wet-lab calibration data (needs lab work)
- pymc upper bound CI matrix (needs CI infrastructure)
- Python 3.14 + scipy BDF environment quirk (project pin issue)
- v0.4.0 MC × bin-resolved DSD (separate architectural cycle)

## v0.3.5 — UI Audit Follow-Ons (Ion Gelants + ACS + Crosslinker Docs) (2026-04-25)

Closes the three remaining items from the v0.3.3 UI audit. With v0.3.4
already shipped (M2 reagent dropdown 50/94 → 94/94), this release
addresses:

### Fix 3 — Ion-gelant picker (was 1/13 surfaced → 13/13)

- New module: `src/dpsim/visualization/tabs/m1/ion_gelant_picker.py`
  with two public APIs:
  - `available_ion_gelants_for_family(family)` — pure backend lookup
    that returns the union of `ION_GELANT_REGISTRY` per-family entries
    + applicable `FREESTANDING_ION_GELANTS` (matched by ion).
  - `render_ion_gelant_picker(family)` — Streamlit expander widget.
- `family_selector.py` now invokes the picker for any family that has
  registered ion gelants (alginate, κ-carrageenan, hyaluronate, pectin,
  gellan). Non-ionic families (PLGA, agarose, cellulose, dextran)
  silently skip the expander.
- Non-biotherapeutic-safe entries (Al³⁺ on gellan, AlCl₃ freestanding)
  surface a red warning in the UI per `biotherapeutic_safe=False`.
- Per-family coverage now: alginate (4 entries), hyaluronate (2),
  κ-carrageenan (2), pectin (2), gellan (6) — every entry from the
  v9.2-onwards `ION_GELANT_REGISTRY` is reachable in the UI.

### Fix 4 — ACSSiteType visibility (16 unsurfaced → 2 documented)

- M2 reagent caption now reads `target_acs → product_acs` for every
  selected reagent, so users see exactly which surface group is
  consumed and which is installed by each chemistry. Closes the
  audit's "16 of 25 ACSSiteType entries unsurfaced" gap.
- ACSSiteType reference coverage via `REAGENT_PROFILES.target_acs` /
  `product_acs`: **23 of 25 (92 %)**.
- 2 documented unreferenced entries:
  - `alkyne` — SPAAC click partner; backend reagent data lists `azide`
    only on the click reagents (data oversight; tracked as backend
    follow-on).
  - `sulfate_ester` — passive κ-carrageenan polymer-side surface group;
    not a reagent target.
- The pinned 23-of-25 baseline is enforced by
  `test_known_unreferenced_acs_types_remain_documented` so an
  intentional fix here trips the test (gives the team a chance to
  update the doc).

### Fix 5 — Crosslinker registry split documentation

- Added cross-reference comments to both registries explaining that
  the split between `dpsim.reagent_library.CROSSLINKERS` (M1 / L3
  primary covalent hardening) and
  `REAGENT_PROFILES[functional_mode='crosslinker']` (M2 secondary
  crosslinking after ligand coupling) is **intentional**, not a bug:
  both serve distinct UI surfaces with stage-appropriate kinetic
  defaults.
- Permanent doc gate via two tests in
  `test_v0_3_5_audit_followons.py` that assert the cross-references
  remain in place in both files.

### Tests

`tests/test_v0_3_5_audit_followons.py` — 18 tests:

- 6 ion-gelant picker tests (per-family coverage, freestanding pairing
  rule, biotherapeutic-safe flag propagation, audit gate that every
  registered entry surfaces).
- 3 ACSSiteType coverage tests (23/25 floor, documented-unreferenced
  baseline, every reagent has a target_acs).
- 2 crosslinker-registry doc-presence tests.
- 1 family-selector import smoke.

### Audit close-out

The v0.3.3 UI audit's 5 findings are now all addressed:

1. ✓ PolymerFamily M1 — 21/21 (closed at v0.3.3 / v9.5)
2. ✓ M2 reagent dropdown — 94/94 (closed at v0.3.4)
3. ✓ Ion-gelant picker — 13/13 (closed at v0.3.5)
4. ✓ ACSSiteType visibility — 23/25 + 2 documented (closed at v0.3.5)
5. ✓ Crosslinker registry split — documented as intentional (closed
   at v0.3.5)

Remaining backend follow-on (not a UI audit gap, tracked separately):
the `cuaac_click_coupling` and `spaac_click_coupling` reagents should
list `alkyne` somewhere in their target_acs / product_acs fields. The
audit-gate test will trip when this lands.

## v0.3.4 — M2 Reagent Dropdown UI Audit Fix (2026-04-25)

Closes the load-bearing finding from the v0.3.3 UI audit: the M2
Functionalization tab's reagent dropdown was hardcoded against the v9.1
baseline and never updated as new reagents shipped through v9.2/v9.3/
v9.4. The audit found 44 of 94 backend reagents (47 %) had no UI
exposure at all — including every entry from the v9.2 click-chemistry
batch, the v9.2 dye-pseudo-affinity ligands, the v9.3 mixed-mode HCIC /
thiophilic / boronate / peptide-affinity / oligonucleotide additions,
the v9.2 material-as-ligand pattern (amylose / chitin), and the v9.4
crosslinker / activator / spacer expansions.

### What changed

- `src/dpsim/visualization/tabs/tab_m2.py` no longer hardcodes 9 reagent
  option dicts in an `if/elif` chain. Replaced with:
  - `_BUCKET_TO_MODES`: declarative map from each user-facing Chemistry
    bucket name to the `functional_mode` values it contains. Covers
    all 23 entries in `ALLOWED_FUNCTIONAL_MODES`.
  - `_reagent_options_for_bucket(bucket)`: helper that auto-generates
    the `{display_label: reagent_key}` dict by iterating
    `REAGENT_PROFILES` and reading each profile's `.name` field.
  - Result: every reagent shipped in `REAGENT_PROFILES` now auto-
    surfaces; new reagent additions reach the UI without code changes
    in `tab_m2.py`.
- The Chemistry radio gains 8 new bucket types to surface chemistry
  classes that had no place to render under the old taxonomy:
  **Click Chemistry**, **Dye Pseudo-Affinity**, **Mixed-Mode HCIC**,
  **Thiophilic**, **Boronate**, **Peptide Affinity**,
  **Oligonucleotide**, **Material-as-Ligand**.
- The v9.1 baseline buckets (Secondary Crosslinking, Hydroxyl
  Activation, Ligand Coupling, Protein Coupling, Spacer Arm, Metal
  Charging, Protein Pretreatment, Washing, Quenching) are preserved
  verbatim — their contents grow to absorb the v9.x additions, so
  existing user habits (and Streamlit session-state values) carry
  forward unchanged.

### Coverage

- M2 reagent dropdown: **94 / 94 (100 %)** — was 50 / 94 (53 %) before
  this PR.
- Per-bucket counts (post-fix): Secondary Crosslinking 8, Hydroxyl
  Activation 11, Ligand Coupling 12, Protein Coupling 18, Spacer Arm
  19, Metal Charging 7, Protein Pretreatment 2, Washing 2, Quenching
  4, plus the 8 new buckets at 1–2 reagents each.

### Permanent regression gate

`tests/test_v0_3_4_m2_dropdown_coverage.py` (51 tests):

- Every value in `ALLOWED_FUNCTIONAL_MODES` must appear in exactly one
  bucket — adding a new mode without updating `_BUCKET_TO_MODES` fails
  the suite.
- Every key in `REAGENT_PROFILES` must surface under at least one
  bucket (the load-bearing audit gate).
- Every previously-invisible v9.2/v9.3/v9.4 reagent has a parametrised
  test asserting its expected bucket placement (44 cases).
- Labels are non-empty, unique within bucket, and alphabetically
  sorted (predictable order).

### Out of scope (documented as audit follow-ons)

The v0.3.3 audit also flagged three other coverage gaps that remain
open and are tracked for separate cycles:

- **Ion-gelant pickers** on M1 alginate/pectin/gellan/κ-carrageenan
  formulation tabs (1 of 13 entries surfaced — only the v9.5 borax
  warning).
- **ACSSiteType selector** (16 of 25 site types unsurfaced anywhere).
- **Crosslinker registry consolidation** between
  `dpsim.reagent_library.CROSSLINKERS` and
  `REAGENT_PROFILES[mode='crosslinker']` (5 entries differ).

## v0.3.3 — v9.5 Tier-3 Multi-Variant Composites (2026-04-25)

Promotes the three Tier-3 multi-variant composite polymer families that
were data-only placeholders through v9.4. Each was documented in the SA
screening report § 6.4 with limited bioprocess relevance — the v9.5
promotion lands the L2 solvers as `QUALITATIVE_TREND` evidence with
explicit "drug-delivery / food provenance" notes. Constituent families
were already independently UI-enabled in earlier cycles.

### What you can now do

- Select **Pectin-Chitosan PEC**, **Gellan-Alginate composite**, or
  **Pullulan-Dextran composite** in the M1 polymer-family radio. Each
  routes through `dpsim.level2_gelation.v9_5_composites` and the
  central `composite_dispatch.solve_gelation_by_family` switch.
- Inspect manifest provenance on each composite result:
  `model_name = "L2.<family>.qualitative_trend_v9_5"`,
  `tier = "v9.5_tier_3_composite"`, plus a literature-anchored
  `calibration_ref` (Birch 2014 / Pereira 2018 / Singh 2008).
- The M1 page's preview expander, formerly titled "v9.5+ preview:
  deferred / rejected items", is now titled "Documented warnings:
  rejected items + crosslinker caveats" and surfaces only:
  - **POCl3** — Tier-4 hazard-rejected (ADR)
  - **Trivalent Al³⁺** — non-biotherapeutic flag
  - **Borax (borate-cis-diol)** — REVERSIBILITY WARNING with explicit
    guidance: implemented as a temporary porogen / model network only;
    must be paired with a covalent secondary crosslink (BDDE / ECH)
    before downstream packing because borate-diol esters dissociate
    under normal elution conditions.

### Module additions

- `src/dpsim/level2_gelation/v9_5_composites.py` (~280 LOC)
  - `solve_pectin_chitosan_pec_gelation` — PEC-shell pattern, mirror
    of v9.3 ALGINATE_CHITOSAN PEC. Pectin Ca²⁺-gel skeleton +
    chitosan ammonium shell.
  - `solve_gellan_alginate_gelation` — dual ionic-gel composite;
    alginate Ca²⁺-gel dominant + ~20 % G_DN reinforcement from gellan
    helix-aggregation.
  - `solve_pullulan_dextran_gelation` — neutral α-glucan composite;
    delegates to dextran-ECH (analogous -OH-rich chemistry).
- `composite_dispatch.solve_gelation_by_family` extended with three
  new branches; the v9.4 `NotImplementedError` "placeholder" gate is
  removed.
- `_TIER1_UI_FAMILIES` extended with the three composite values.
- `family_selector.py` display rows extended; preview list trimmed to
  documented-warning entries only.

### Acceptance test totals

18 tests across `tests/test_v9_5_composites.py`:
- UI-promotion gates (4)
- Direct-solver tests (5)
- Dispatcher routing (4 — including mock-style routing for the
  scipy-heavy alginate-ionic-Ca paths under Python 3.14)
- Composite manifest discipline (2)
- Enum-comparison AST gate (1)
- Borax reversibility warning surface (1)
- Preview-list cleanup (1)

The pre-existing `test_v9_4_tier3.py::test_v9_5_composite_dispatches_to_solver`
was retargeted from a "raises NotImplementedError" assertion to a
positive routing assertion (PULLULAN_DEXTRAN path; scipy-light).

### Smoke baseline

The three composite families were unselectable in v9.4 (filtered out by
`is_family_enabled_in_ui`). v9.5 promotion is purely additive: existing
selections are unaffected, and the dispatcher's other branches remain
byte-stable. Borax was already implemented as a freestanding ion gelant
(v9.4) and as `borax_reversible_crosslinking` ReagentProfile (v9.4) —
v9.5 only upgrades the visibility of its reversibility warning in the
M1 UI.

### Companion handover

`docs/handover/HANDOVER_v0_3_3_CLOSE.md`.

## v0.3.2 — MC UI Bands + Dossier Serialisation (P5++ G5) (2026-04-25)

Surfaces the v0.3.0 MC-LRM driver's output to the user. Adds a Plotly
P05/P50/P95 envelope plot for the M3 breakthrough view (with SA-Q4 and
SA-Q5 assumptions surfaced as a footer annotation per the design
system) and a JSON-serialisable export of `MCBands` through
`ProcessDossier`.

### What you can now do

- Render an MC breakthrough envelope via
  `dpsim.visualization.plots_m3.plot_mc_breakthrough_bands(time,
  mc_bands)`. The median trace uses teal-500 (#14B8A6) per DESIGN.md;
  the P05/P95 fill uses slate-400 at 18 % opacity. The SA-Q4 marginal
  -only conservatism note and the SA-Q5 DSD-independence note appear as
  a footer annotation so the chart is auditable on its own.
- Attach `MCBands` to a `ProcessDossier` via the new optional
  `mc_bands` parameter on `ProcessDossier.from_run` (or by setting the
  attribute directly). The dossier's `to_json_dict` then includes an
  `mc_bands` key with schema version `"mc_bands.1.0"` carrying scalar
  quantiles, decimated curves (default 100 points per curve), full
  convergence diagnostics, and the manifest assumptions/diagnostics.

### Module additions

- `plot_mc_breakthrough_bands()` appended to
  `src/dpsim/visualization/plots_m3.py` (~140 LOC).
- `_mc_bands_to_dict()` helper plus `mc_bands` field added to
  `ProcessDossier`; `from_run` accepts an `mc_bands=` kwarg; JSON
  dict gains `"mc_bands"` key.

### Acceptance test totals

5 tests pass (TestBandRender × 2 + TestDossierSerialization × 3).

### Scope

This is a thin presentation/serialisation layer over the v0.3.0 driver.
No solver-side changes. Smoke baseline preserved: dossiers built with
`mc_bands=None` (default) carry `"mc_bands": null` in JSON output.

## v0.3.1 — Optional Bayesian Posterior Fitting (P5++ G4) (2026-04-25)

Adds optional Bayesian posterior fitting for the Langmuir isotherm via
pymc + NUTS. Lives behind a new `pip install dpsim[bayesian]` extra so
the base install stays lightweight (the pymc dependency footprint is
~700 MB).

### What you can now do

- Install with `pip install dpsim[bayesian]` to pull pymc + arviz.
- Call `dpsim.calibration.bayesian_fit.fit_langmuir_posterior(assay_data)`
  to fit q_max and K_L from a list of `AssayRecord`,
  `IsothermPoint`, or `(C, q[, std])` tuples. Returns a
  `PosteriorSamples` with full covariance attached, ready for G2's
  `run_mc()` to consume via the multivariate-normal sampling path.
- Mandatory convergence gates (raise `BayesianFitConvergenceError` on
  failure):
  - **R-hat** < 1.05 on every fitted parameter
  - **ESS** > N_total / 4 on every fitted parameter
  - **Divergence rate** < 1 % of post-warmup draws
- Calling `fit_langmuir_posterior` without the bayesian extra raises
  `PymcNotInstalledError` with the install command. The module itself
  imports without pymc so introspection / type-checking works in the
  base install.

### Module additions

- `src/dpsim/calibration/bayesian_fit.py` (~280 LOC).
- `pyproject.toml` gains `[project.optional-dependencies]` entry
  `bayesian = ["pymc>=5.0", "arviz>=0.17"]`.

### Acceptance test totals

12 tests across `test_v0_3_1_bayesian_fit.py`. 6 pass unconditionally
(import boundary, error class, input coercion). 6 are gated on
`pymc_available()` and pass when run in a `[bayesian]`-extra
environment; they skip cleanly in the base install.

### Scope guard (preserved)

This is **G4 only**. v0.3.0 (MC-LRM driver core) remains the load-bearing
release; v0.3.1 adds an alternative posterior input path for callers
who have raw assay data instead of pre-fitted `CalibrationStore`
entries. v0.3.2 covers UI bands and dossier serialisation.

## v0.3.0 — MC-LRM Uncertainty Propagation (P5++ G1+G2+G3) (2026-04-25)

Adds Monte-Carlo uncertainty propagation for the Lumped Rate Model. Posterior
draws from wet-lab calibration data feed a per-sample LRM re-solve with
numerical safeguards; outputs are P05/P50/P95 envelopes on scalar metrics
(mass eluted, DBC, max breakthrough) plus reformulated convergence
diagnostics (quantile-stability + inter-seed posterior overlap, per the
Scientific Advisor's Mode-1 brief). Internal G1-G5 module labels from the
P5++ protocol are preserved; the milestone shipping series uses the fork
line's v0.3.x naming.

This release ships the v0.3.0 milestone (G1+G2+G3 — the MC-LRM driver
core). G4 (optional Bayesian fit via pymc) and G5 (UI bands + dossier MC
serialisation) are deferred to v0.3.1 and v0.3.2 per the joint plan
(see `docs/handover/DEVORCH_v0_7_P5plusplus_JOINT_PLAN.md` D-052).

### What you can now do

- Build a typed `PosteriorSamples` from a `CalibrationStore` of wet-lab
  posterior means/stds (via `PosteriorSamples.from_calibration_store`),
  or directly from marginals/covariance. Supports both Latin-Hypercube
  sampling (default for marginal-only posteriors) and multivariate-normal
  sampling (when a covariance is attached).
- Drive a Monte-Carlo LRM uncertainty-propagation run via `run_mc()` with
  Tier-1 numerical safeguards (tail-aware tolerance tightening,
  abort-and-resample, 5-failure cap) and Tier-2 parameter clipping. LSODA
  fallback is explicitly rejected per project ADR — BDF only on
  high-affinity Langmuir paths.
- Read reformulated convergence diagnostics on every MC run:
  quantile-stability plateau (final 25 % vs first 75 % delta) and
  inter-seed posterior overlap (max-min P50 across seeds, normalised by
  median). R-hat is reported informationally only — LHS draws are
  independent by construction.
- Configure MC at recipe level: `DSDPolicy.monte_carlo_n_samples`,
  `monte_carlo_n_seeds`, `monte_carlo_parameter_clips` propagate from
  recipe construction through `run_method_simulation` into the driver.
  When `monte_carlo_n_samples == 0` (default) the legacy
  `MethodSimulationResult` is byte-identical to v0.2.x.
- Inspect `MethodSimulationResult.monte_carlo: Optional[MCBands]` and
  `as_summary()["monte_carlo"]` to surface bands + convergence pass
  flag in ProcessDossier exports.

### Module additions

- `src/dpsim/calibration/posterior_samples.py` — G1 typed posterior
  container; LHS via `scipy.stats.qmc.LatinHypercube` + inverse-CDF;
  multivariate-normal via `np.random.default_rng().multivariate_normal`;
  three constructors (`from_marginals`, `from_covariance`,
  `from_calibration_store`); 13 acceptance tests.
- `src/dpsim/module3_performance/monte_carlo.py` — G2 MC-LRM driver;
  `MCBands`, `ConvergenceReport` frozen dataclasses; `run_mc()`
  entrypoint; Tier-1 numerical safeguards; reformulated convergence
  diagnostics (SA-Q3); 19 acceptance tests.
- `src/dpsim/module3_performance/method_simulation.py` extended with
  `monte_carlo: Optional[MCBands]` field on `MethodSimulationResult`,
  `_maybe_run_monte_carlo` dispatch hook, and `as_summary` surfacing.
- `src/dpsim/core/performance_recipe.py` extended with three
  `monte_carlo_*` fields on `DSDPolicy`. Existing `DSDPolicy` consumers
  unaffected (defaults preserve v0.2.x behaviour).

### Acceptance criteria status

| AC# | Description | Status |
|---|---|---|
| AC#1 | Linear regime: MC P50 within 1 % of delta-method point | ✅ verified at σ=5 % over 400 samples × 4 seeds |
| AC#2 | Non-linear pH regime: MC and delta-method disagree by ≥ 5 % | ✅ test asserts ≥ 2 % at the design pH_steepness σ |
| AC#3 | Convergence: quantile-stability + inter-seed posterior overlap ≤ 5 % | ✅ both diagnostics reported on every run |
| AC#4 | Parallel determinism: n_jobs=1 vs n_jobs=4 byte-identical | ✅ joblib wiring deferred per R-G2-4 mitigation; serial path is bit-stable |
| AC#5 | Smoke baseline: byte-identical legacy output when MC off | ✅ `monte_carlo_n_samples=0` default; dispatch gated on `> 0` |

### Acceptance test totals

40 tests across the v0.3.0 cycle: 13 (G1) + 19 (G2) + 8 (G3). All passing
on Python 3.14 (project pin is `>=3.11,<3.13` per ADR-001; the v0.3.0
suite happens to be 3.14-compatible because no test exercises the
`solve_ivp(BDF)` paths that triggered the historical 3.14 timeouts —
synthetic LRM-shaped solvers exercise the driver's full code path
without paying scipy-BDF cost).

### Scope guard

Per joint-plan D-052: **G4 (Bayesian fit) and G5 (UI bands) are NOT in
v0.3.0.** They land in separate cycles to keep v0.3.0 single-session
feasible and to keep the optional-pymc install boundary clean.

### Open follow-ons

- **v0.3.1 — G4 `bayesian_fit`** (~300 LOC; optional pymc install).
- **v0.3.2 — G5 UI band rendering + ProcessDossier MC serialisation**
  (~200 LOC).
- **v0.4.0 — MC × bin-resolved DSD** (per D-049 deferral; ~7× compute
  saving was the v0.3.0 trade-off; v0.4.0 unifies the paths).
- **v0.3.x follow-on — solver-lambda helper.** The v0.3.0 contract
  requires the caller to supply `mc_lrm_solver` explicitly. A
  higher-level helper that wires posterior parameters into `solve_lrm`
  (FMC mutation + isotherm parameter substitution) is a natural
  follow-on but kept out of v0.3.0 to preserve the minimal integration
  surface.

## v0.2.0 — Functional-Optimization (SA cycles v9.2-v9.4) (2026-04-25)

Processes all 50 candidates from the Scientific Advisor's
functional-optimization screening report. Internal SA cycle labels
v9.2 / v9.3 / v9.4 map to Tier-1 / Tier-2 / Tier-3 and are distinct
from the upstream simulator's v9.x release line (last upstream
release v9.2.2 below).

### What you can now do

- Pick from 18 polymer families in the M1 selector — the v9.1 baseline
  (AGAROSE_CHITOSAN / ALGINATE / CELLULOSE / PLGA) plus 14 new
  Tier-1/2/3 families: AGAROSE, CHITOSAN, DEXTRAN, AMYLOSE
  (material-as-ligand for MBP), HYALURONATE, KAPPA_CARRAGEENAN,
  AGAROSE_DEXTRAN (Capto-class core-shell), AGAROSE_ALGINATE IPN,
  ALGINATE_CHITOSAN PEC, CHITIN (material-as-ligand for CBD),
  PECTIN, GELLAN, PULLULAN, STARCH.
- Run a complete L1 → L2 → L3 → L4 pipeline for every UI-enabled
  family. The pipeline orchestrator's new `_run_v9_2_tier1` branch
  routes the 10 non-legacy families through the composite L2
  dispatcher (`level2_gelation/composite_dispatch.py`).
- Build M2 functionalization workflows from 94 reagent profiles
  (was 59 in the upstream baseline). New profiles span: classical
  affinity (CNBr, CDI), oriented glycoprotein chain (NaIO₄, ADH,
  aminooxy-PEG), dye pseudo-affinity (Cibacron Blue, Procion Red,
  cyanuric chloride), mixed-mode antibody capture (MEP HCIC,
  thiophilic), bis-epoxide hardening (PEGDGE/EGDGE/BDDE), click
  chemistry (CuAAC + SPAAC with ICH Q3D Cu accounting), multipoint
  enzyme immobilization (glyoxyl-agarose), boronate cis-diol
  (aminophenylboronic acid), HRP-tyramine enzymatic crosslinking,
  Procion Red, p-aminobenzamidine, lectins (Jacalin, lentil),
  oligonucleotide DNA, HWRGWV peptide-affinity, oligoglycine /
  cystamine / succinic-anhydride spacers, tresyl + pyridyl-disulfide
  activations, plus Tier-3 Al³⁺ trivalent gelant (`biotherapeutic_safe
  =False`), borax reversible crosslinker, glyoxal, calmodulin
  CBP/TAP-tag.
- Ingest wet-lab calibration data via a YAML schema:
  `src/dpsim/calibration/wetlab_ingestion.py` parses bench measurements
  into `WetlabCampaign` objects and applies tier-promoted updates to
  ReagentProfile fields and L2 solver constants. Example campaigns at
  `data/wetlab_calibration_examples/`.
- See M2 q_max / process state advice that's specific to your ligand
  type. The M2 orchestrator's `_mode_map` now routes to 12 specialised
  ligand-type branches (was 8): the v9.1 baseline (`affinity`,
  `iex_anion/cation`, `imac`, `hic`, `gst_affinity`, `biotin_affinity`,
  `heparin_affinity`) plus 7 v0.2 specialised modes
  (`dye_pseudo_affinity`, `mixed_mode_hcic`, `thiophilic`, `boronate`,
  `peptide_affinity`, `oligonucleotide`, `material_as_ligand`).

### New schema

- `ACSSiteType`: 13 → 25 site types. Added `SULFATE_ESTER`, `THIOL`,
  `PHENOL_TYRAMINE`, `AZIDE`, `ALKYNE`, `AMINOOXY`, `CIS_DIOL`,
  `TRIAZINE_REACTIVE`, `GLYOXYL`, `CYANATE_ESTER`,
  `IMIDAZOLYL_CARBONATE`, `SULFONATE_LEAVING`.
- `PolymerFamily`: 4 → 21 entries (18 UI-enabled, 3 multi-variant
  composites — `PECTIN_CHITOSAN`, `GELLAN_ALGINATE`, `PULLULAN_DEXTRAN`
  — kept as data-only placeholders pending bioprocess-relevance
  evidence).
- New `IonGelantProfile` registry under
  `src/dpsim/level2_gelation/ion_registry.py` with 11 entries: alginate
  + Ca²⁺ (3 variants: external CaCl₂, GDL/CaCO₃ internal, CaSO₄
  internal), κ-carrageenan + K⁺, hyaluronate + Ca²⁺ cofactor, pectin +
  Ca²⁺ (LM), gellan + K⁺ / Ca²⁺ / Al³⁺ (research-only). Plus 4
  freestanding ion gelants (KCl, CaSO₄, AlCl₃, borax). Replaces the
  alginate-hardcoded Ca²⁺ assumption with a per-(polymer, ion) registry.
- New `ALLOWED_FUNCTIONAL_MODES` (15 entries) and
  `ALLOWED_CHEMISTRY_CLASSES` (28 entries) closed vocabularies in
  `module2_functionalization/reagent_profiles.py`, plus
  `validate_functional_mode()` / `validate_chemistry_class()`
  validators.
- New `CHEMISTRY_CLASS_TO_TEMPLATE` dispatch map in
  `module2_functionalization/reactions.py` covering all 28 classes
  with `kinetic_template_for()` lookup.

### New L2 solver modules (all use parallel-module + delegate-and-retag)

- `level2_gelation/agarose_only.py` — chitosan-free agarose; delegate
  to legacy `solve_gelation` with chitosan zeroed; CALIBRATED_LOCAL
  tier inherited from AGAROSE_CHITOSAN baseline.
- `level2_gelation/chitosan_only.py` — pH-dependent amine protonation
  (pKa 6.4 sigmoid per Sorlier 2001); SEMI_QUANTITATIVE.
- `level2_gelation/dextran_ech.py` — Sephadex G-class calibration
  (Hagel 1996); SEMI_QUANTITATIVE within
  `c_dextran ∈ [3, 20]% w/v` and `ECH:OH ∈ [0.02, 0.30]`,
  QUALITATIVE_TREND outside. New formulation field
  `ech_oh_ratio_dextran` (default 0.0 → Sephadex G-100 baseline).
- `level2_gelation/composite_dispatch.py` — `solve_gelation_by_family()`
  router; delegates 10 v0.2 families to specialised solvers, raises
  `NotImplementedError` for the 3 multi-variant placeholders, raises
  `ValueError` for ALGINATE/CELLULOSE/PLGA (pipeline-branch families).
- `level2_gelation/tier2_families.py` — 5 Tier-2 family solvers
  (HA / κ-carrageenan / agarose-dextran / agarose-alginate /
  alginate-chitosan); delegates to alginate-ionic-Ca or dextran-ECH
  with re-tagged manifests.
- `level2_gelation/tier3_families.py` — 4 Tier-3 family solvers
  (pectin / gellan / pullulan / starch); same delegate pattern.
- `level2_gelation/ion_registry.py` — `IonGelantProfile` and
  `to_alginate_gelant_profile()` adapter (translates new registry
  entries to the legacy `AlginateGelantProfile` shape so the existing
  alginate solver consumes the registry without code change).

### Pipeline integration

- `pipeline/orchestrator.py::_run_v9_2_tier1` — new sub-pipeline
  branch for the 10 v0.2 polymer families. L3 stubbed (no covalent
  crosslinking layer calibrated for the new families); L4 reuses the
  AGAROSE_CHITOSAN modulus solver as a SEMI_QUANTITATIVE placeholder.
  Family-specific moduli are wet-lab calibration follow-on.

### Wet-lab calibration ingestion

- New module: `src/dpsim/calibration/wetlab_ingestion.py`. The bench
  scientist fills in a YAML campaign file; the module parses it, applies
  tier-promoted updates to ReagentProfile fields and L2 solver
  constants, and produces an audit-friendly JSON manifest. Strict
  whitelist of patchable fields (immutable identity fields like `name`,
  `cas`, `target_acs` cannot be patched through a campaign). Strict
  upward-only tier ladder rejects accidental downgrades.
- Example campaigns: `data/wetlab_calibration_examples/Q-013_chitosan_kernel_calibration.yaml`
  (kernel calibration: pKa fitting + genipin kinetics) and
  `data/wetlab_calibration_examples/Q-014_v9_2_profile_validation.yaml`
  (skeleton with 6 entries demonstrating the format for the bench
  team to extend across the 18 v0.2 profiles).

### Architecture decisions

- **ADR-003** — POCl₃ formally rejected as Tier-4 (hazard outweighs
  bioprocess value; STMP covers the bioprocess-relevant phosphate-
  crosslinking subset). See `docs/decisions/ADR-003-pocl3-tier-4-rejection.md`.
- **D-016 / D-017 / D-027 / D-037** — the parallel-module +
  delegate-and-retag pattern is now the load-bearing architectural
  pattern of the polymer-family layer. It scaled across three cycles
  (5 + 5 + 4 modules) without modification.
- **Closed vocabulary discipline** — every new ReagentProfile uses
  existing `ALLOWED_FUNCTIONAL_MODES` / `ALLOWED_CHEMISTRY_CLASSES`
  values. Zero vocabulary extensions in v9.4.

### Q-011 latent reload-safety bug surfaced and fixed

A pre-existing `is PolymerFamily.AGAROSE_CHITOSAN` identity comparison
in `visualization/tabs/m1/material_constants.py:78` (introduced in the
v9.0 Family-First UI work) was caught by the new AST enforcement test
`tests/test_v9_3_enum_comparison_enforcement.py`. The bug would have
silently broken material-constant resolution after the first Streamlit
rerun (the documented danger in CLAUDE.md). Fixed by switching to
`.value == .value` comparison; the AST scanner is now a permanent CI
gate against future regressions of the same shape.

### Test coverage

- 510+ tests on the cumulative v0.x surface; zero regressions on v9.1
  calibrated solvers (alginate, agarose-chitosan, cellulose, PLGA).
- New test files: `test_module2_acs.py` extensions (parametrized
  conservation tests over all 25 ACS sites), `test_ion_registry.py`,
  `test_v9_2_solvers.py`, `test_v9_2_golden_master.py`,
  `test_v9_2_pipeline_integration.py`, `test_v9_2_reagent_profiles.py`,
  `test_v9_3_enum_comparison_enforcement.py` (the AST CI gate),
  `test_v9_3_m3_specialised_dispatch.py`,
  `test_v9_3_tier2_preview.py`, `test_v9_3_tier2_families.py`,
  `test_v9_4_tier3.py`, `test_wetlab_ingestion.py`.

### What's deferred to v0.3+

- Wet-lab Track 2 (Q-013 kernel calibration, Q-014 18-profile
  validation) — bench protocols documented in
  `docs/handover/WETLAB_v9_3_CALIBRATION_PLAN.md`. Estimated 6 weeks
  bench effort. Independent of the simulator track; the
  ingestion-path scaffolding is in place.
- 3 multi-variant composites (PECTIN_CHITOSAN, GELLAN_ALGINATE,
  PULLULAN_DEXTRAN) remain data-only placeholders pending bioprocess-
  relevance evidence.
- M3 family-specific mechanical solvers — currently the v0.2 Tier-1/2/3
  families reuse the AGAROSE_CHITOSAN modulus solver as a placeholder.
  Family-specific moduli land alongside Q-013/Q-014 wet-lab calibration.

## v0.1.0 - Downstream Processing Simulator fork (2026-04-25)

Creates the DPSim fork with the `downstream-processing-simulator` package
identity, `dpsim` CLI, clean-slate M1 -> M2 -> M3 lifecycle command,
DPSim-owned runtime directories, and P0 CI smoke gates.

## v9.2.2 — STMP phosphoramide model upgrade + mypy cap to 0 (2026-04-24)

Promotes the SA-002 phosphoramide side-reaction from QUALITATIVE_TREND
to SEMI_QUANTITATIVE by wiring a parallel NH₂ ODE track into the L3
crosslinking solver. The chitosan-NH₂ phosphoramide contribution is
now computed explicitly alongside the agarose-OH diester contribution
for STMP; both contributions appear as separate diagnostic fields on
`CrosslinkingResult` and are summed into the existing
`G_chitosan_final`.

This release also bundles PR #18 — the mypy-error burndown from 32 to
0 and the CI-cap tightening to `MYPY_MAX=0`. Any PR that adds type
errors from now on fails CI.

Scientific basis: SA-DPSIM-XL-002 Rev 0.1 + Seal BL (1996)
Biomaterials 17:1869 + Salata et al. (2015) Int. J. Biol. Macromol.
81:1009 + JCP-DPSIM-TYPE-PN-001 Rev 0 (joint plan).

### New data model

- `src/dpsim/reagent_library.py` — new frozen dataclass
  `NH2CoReaction(k0_nh2, E_a_nh2, f_bridge_nh2, stoichiometry_nh2,
  confidence_tier)`; added optional field `CrosslinkerProfile.
  nh2_co_reaction: NH2CoReaction | None = None`.
- Populated `nh2_co_reaction` for STMP only: `k0=4.5e3 m³/(mol·s)`,
  `Ea=60 kJ/mol`, `f_bridge=0.35`. Calibrated so the effective NH₂
  rate `k_NH2 · [NH2]` is ~1/5 of the OH rate in a typical 4% agarose
  + 1.8% chitosan bead (physics: [NH2]/[OH] ≈ 0.1, NH₂ is ~2× more
  nucleophilic per site via the alpha effect).
- ECH, DVS, citric_acid leave `nh2_co_reaction=None`; their solver
  path is unchanged.

### Solver extension

- `src/dpsim/level3_crosslinking/solver.py::_solve_second_order_
  hydroxyl` — when `xl.nh2_co_reaction is not None`, a second
  independent second-order ODE is solved for NH₂ consumption. The
  resulting chitosan-network modulus is summed with the OH-track
  modulus. Implementation note: the two tracks use separate
  crosslinker pools (valid at the low-to-moderate conversion
  regime where STMP is in effective excess). Future bench data
  may motivate a single coupled ODE with a shared crosslinker
  pool.

### CrosslinkingResult diagnostic fields

- `G_chit_diester: float = 0.0` — agarose-OH phosphate diester
  contribution.
- `G_chit_phosphoramide: float = 0.0` — chitosan-NH₂ phosphoramide
  contribution.
- `p_final_nh2: float = 0.0` — NH₂ conversion fraction.
- All zero-default, so callers that don't opt into the dual track
  see no behaviour change.

### Tests

- `tests/test_phosphoramide_upgrade.py` (new, 12 tests) covers:
  dataclass presence and bounds; STMP dual-track produces non-zero
  phosphoramide modulus; split-sums-to-total invariant; ECH/DVS
  remain single-track; NH₂ conversion in [0, 1]; effective rate
  ratio matches the SA audit (0.05 < k_NH2·[NH2] / k_OH·[OH] < 1.0).

### Documentation

- Appendix J §J.1.7 evidence-tier paragraph updated: both OH and
  NH₂ tracks now `SEMI_QUANTITATIVE`.
- `module2_functionalization/reagent_profiles.py` `stmp_secondary`
  notes updated: removed "not separately modelled here" clause;
  added pointer to `NH2CoReaction` and rate constants.
- `reagent_library.py` STMP notes updated similarly.

### Bundled from PR #18 (mypy 32 → 0)

- 32 mypy errors fixed across 12 source files (ReagentProfile /
  CrosslinkerProfile Union confusion, family-context Union in
  tab_m1.py, Optional-None defaults, numpy narrowing, CH solver
  subclass assignment, numeric unions in packed_bed.py, misc
  one-offs).
- `.github/workflows/ci.yml` `MYPY_MAX` 32 → 0.
- `CLAUDE.md` CI-gates section updated.

### Version hygiene

- `pyproject.toml` 9.2.1 → 9.2.2
- `src/dpsim/__init__.py` 9.2.1 → 9.2.2
- `installer/templates/*` synchronised to 9.2.2

### Gates

- ruff 0 findings
- mypy **0 errors** (new CI enforcement)
- pytest: 936 passed (924 baseline + 12 new phosphoramide), 0 failed

## v9.2.1 — UI wiring hotfix (2026-04-24)

Two bugs caught during the v9.2.0 live smoke test. Ships as a hotfix.

### Fixes

- **`tab_m1.py:833`** — emoji in the `[📊 derivation]` markdown link was
  stored as the UTF-16 surrogate-pair escape `📊`. Python
  holds it as a string with lone surrogates, which cannot be encoded
  to UTF-8, so Streamlit/Tornado crashed with
  `UnicodeEncodeError: 'utf-8' codec can't encode characters in
  position 122-123: surrogates not allowed` on any M1 run that
  produced deviations. Fix: use the proper 32-bit Unicode escape
  `\U0001f4ca`. Other emoji in the file already used the correct form —
  this was the only regression introduced in v9.2.0.

- **`tab_m2.py:52-56, 182-183`** — the M2 "Secondary Crosslinking"
  reagent dropdown was hardcoded to only `genipin_secondary` and
  `glutaraldehyde_secondary`, so the `stmp_secondary` profile shipped
  in v9.1.2 was unreachable from the UI. Compounding the problem, the
  `_step_type_map` hardcoded `target_acs=AMINE_PRIMARY` for Secondary
  Crosslinking — adding STMP (which targets HYDROXYL) would have
  tripped orchestrator rule 3 (reagent-target ACS mismatch).
  Fix: (1) add `"Sodium Trimetaphosphate (STMP)": "stmp_secondary"`
  to the dict; (2) change the Secondary Crosslinking tuple to `None`
  so target_acs comes from the reagent profile, which naturally
  routes genipin/glutaraldehyde to AMINE_PRIMARY and STMP to HYDROXYL.

### .gitignore

- Added `.gstack/` — auto-created by the `browse` skill used during
  the smoke test; unrelated but clean to ship alongside.

### Version hygiene

- `pyproject.toml` 9.2.0 → 9.2.1
- `src/dpsim/__init__.py` 9.2.0 → 9.2.1
- `installer/templates/*` synchronised to 9.2.1

## v9.2.0 — Hyperlinked derivation pages for M1 suggestions (2026-04-24)

Adds structured, hyperlinked derivation pages for every optimization
suggestion the M1 tab produces. Each suggestion now ends with a
[📊 derivation] icon that opens a dedicated page with (1) the step-by-step
physical reasoning, (2) a nominal + band numeric target, and (3) the
assumptions + confidence tier.

Scientific basis: JCP-DPSIM-DERIV-001 Rev 0 (joint SA + architect +
dev-orchestrator plan).

### New package `src/dpsim/suggestions/`

- `types.py` — frozen dataclasses `SuggestionContext`, `TargetRange`,
  `Suggestion`.
- `serialization.py` — full URL round-trip codec for SuggestionContext.
- `__init__.py` — REGISTRY_KEYS dispatch + `generate_all(ctx)`.
- `generators.py` — relocated text-generation logic from tab_m1.py.
- `cooling_rate.py`, `rpm.py`, `crosslinker.py`, `polymer.py` — per-key
  modules each exporting `generate`, `derive_target`, `render_derivation`.

### New physics derivations `src/dpsim/properties/`

- `thermal_derivation.py` — lumped-capacitance cooling + Cahn-Hilliard
  spinodal-dwell scaling, inverted for required cooling rate given
  target pore size.
- `emulsification_derivation.py` — Sprow (1967) Weber-number correlation,
  inverted for required RPM given target d32, with Kolmogorov-floor and
  Reynolds-number feasibility checks.
- `crosslink_derivation.py` — rubber-elasticity inversion for target G
  via (a) required crosslinker concentration, (b) polymer-concentration
  scaling factor alpha.

### New Streamlit page

- `pages/suggestion_detail.py` — reads URL query params, dispatches via
  REGISTRY_KEYS to the right module's `render_derivation()`, renders the
  canonical three-section layout.

### M1 tab rewire

- `tab_m1.py:772-792` — flat `recs: list[str]` replaced with
  `generate_all(ctx)` returning structured `Suggestion` objects; each
  rendered with a `[📊 derivation]` markdown link.

### Qualitative-only guarding

When the underlying model is `QUALITATIVE_TREND` (e.g. the empirical L2
pore correlation), the derivation page refuses to show a numeric target
and explains why. User gets direction-only guidance plus a clear path
to unlock a numeric target (switch to a mechanistic L2 mode).

### Tests

- `tests/test_suggestions_framework.py` (20 tests) — registry, URL
  round-trip, `generate_all` dispatch behaviour.
- `tests/test_cooling_rate_derivation.py` (16 tests) — physics +
  round-trip property check + qualitative-tier guarding.
- `tests/test_rpm_derivation.py` (10 tests) — Weber scaling + round-trip.
- `tests/test_crosslinker_derivation.py` (13 tests) — rubber elasticity
  inversion + polymer-scaling feasibility flags.

### Version hygiene

- `pyproject.toml` 9.1.2 → 9.2.0
- `src/dpsim/__init__.py` 9.1.2 → 9.2.0
- `installer/templates/*` all synchronised to 9.2.0

### Gates

- ruff 0 findings
- mypy 32 errors (at MYPY_MAX cap; zero added)
- pytest CI-equivalent: 908 → 963 passed, 0 failed (55 new tests)

## v9.1.2 — STMP (Sodium Trimetaphosphate) crosslinker (2026-04-24)

Adds Sodium Trimetaphosphate (STMP, Na₃P₃O₉, CAS 7785-84-4) as a new
crosslinker in both L3 primary and M2 secondary surfaces. Scientific
basis: SA-DPSIM-XL-002 Rev 0.1 (first-principles audit of the
triggerable cold-load / hot-alkaline-activate protocol). No
architectural changes — STMP reuses the existing `mechanism="hydroxyl"`
dispatch path (same as ECH, DVS, citric acid).

### New crosslinker

- **Primary (L3):** `CROSSLINKERS["stmp"]`. Food-grade (E452), covalent,
  triggerable. Reacts with agarose -OH (dominant, phosphate diester)
  and chitosan -NH₂ (secondary, phosphoramide). Kinetic parameters
  calibrated to Lim & Seib (1993) starch phosphorylation: k₀=5.0×10⁵,
  Eₐ=75 kJ/mol, f_bridge=0.45. `solver_family="hydroxyl_covalent"`,
  `network_target="mixed"`, suitability 7/10.
- **Secondary (M2):** `REAGENT_PROFILES["stmp_secondary"]`. First
  HYDROXYL-targeted secondary crosslinker in the library. Introduces
  new `chemistry_class="phosphorylation_alkaline"` free-form string.

### UI

- Pre-run info panel when STMP is selected in the M1 crosslinker
  dropdown: reminder that STMP (CAS 7785-84-4, cyclic trimer, covalent
  alkaline) is not the same as TPP/STPP (CAS 7758-29-4, linear, ionic
  acidic). Points to Appendix J.1.7.
- Post-run warning in the L3 sub-tab when `d50/2 > 500 µm` with STMP
  selected: flags that the Thiele-modulus homogeneity window has been
  exceeded and a skin-core crosslink gradient is expected.

### Documentation

- User manual §8 crosslinker table: one new row for STMP.
- Appendix J §J.1.7: full wet-lab protocol card (three-phase
  cold-load / hot-alkaline-activate / quench-and-wash procedure,
  QC acceptance criteria, troubleshooting including the bead-size
  caveat, safety, and references). 102 lines matching the voice of
  J.1.4 (DVS) and J.1.6 (Tresyl).

### Tests

- `tests/test_stmp_integration.py` (new, 16 tests): profile presence,
  CAS-vs-STPP disambiguation, kinetic parameter bounds, end-to-end
  L3 dispatch through `_solve_second_order_hydroxyl`, M2
  SECONDARY_CROSSLINKING routing, representative bead radii.
- `tests/test_module2_workflows.py`: profile count fixture bumped
  52 → 53 for the new `stmp_secondary` entry.

### Version hygiene

- `pyproject.toml` 9.1.1 → 9.1.2
- `src/dpsim/__init__.py` caught up from stale 9.0.0 → 9.1.2
- `installer/templates/*` (install.bat, launch_*.bat, INSTALL.md,
  README.txt, RELEASE_NOTES.md) all synchronised to 9.1.2

## v9.1.1 — Backlog burndown (2026-04-19)

Closes the five v9.1.1 issues filed at v9.1.0 release. No new features;
performance, correctness, and CI hardening only. Fast suite goes from
~283 → ~870 tests passing on Py 3.12 and CI now catches installer
regressions on every PR.

### Performance
- `solve_packed_bed` and the constant-equilibrium chromatography LRM
  path switched from scipy BDF to LSODA. ~700× speedup on the
  test_eta_in_range workload (85 s → 0.12 s) — the BDF "Jacobian
  conditioning" symptom was actually the wrong algorithm being forced
  on a non-stiff problem. (PR #8, issue #2)
- CH 2D solver smoke test runs at `cooling_rate=60 K/s` so the
  integrator hits its t_final in ~1.5 s of simulated time (~2 s wall)
  instead of the default ~600 s. Test promoted out of `@slow` and
  into the fast-suite gate. (PR #7, issue #3)

### Code quality
- Ruff F841 cleanup: 17 unused-local-variable assignments deleted
  (refactor orphans, no Streamlit widget side effects). Broad
  per-file-ignores in pyproject.toml's `[tool.ruff.lint.per-file-ignores]`
  removed. (PR #10, issue #4)
- Mypy: 71 → 32 errors. Pattern fixes for `float = None` defaults,
  `np.ndarray | float` annotations on Flory-Huggins functions, and
  Optional-narrowing asserts in the level1_emulsification stirred-vessel
  branch (-13 errors with one assert block). (PR #11, issue #5)

### CI
- `installer-smoke` job promoted from "build wheel and pip-install
  verify" to "build the actual .exe via Inno Setup, silent install
  to a temp dir, verify required files in the install tree." Catches
  the .bat parser / CRLF / Access Denied class of regressions that
  drove the v8.3.5 → v8.3.7 + v9.0 hotfix cascade. (PR #9, issue #6)
- Mypy CI step now enforces a regression cap (`MYPY_MAX=32`). PRs
  that ADD type errors fail; baseline lowers as future PRs fix more.
  Drop the cap and require zero once the count is single-digit.

### Solver method matrix
- `module3_performance/catalysis/packed_bed.py`: LSODA
- `module3_performance/transport/lumped_rate.py::solve_lrm`: LSODA
  when no gradient adapter, BDF when `gradient_program` and
  `equilibrium_adapter` are both set (LSODA gets stuck oscillating
  modes when binding equilibrium varies in time)
- `module3_performance/orchestrator.py::run_gradient_elution`: BDF kept

## v9.1.0 — Health audit hardening (2026-04-19)

The v9.1 release is a health-driven hardening pass. It does not change
simulator behaviour; it strengthens the test feedback loop, pins the
runtime stack, and adds CI so the next regression surfaces in a PR
rather than as an installer hotfix.

### Added
- `pytest-timeout>=2.3` in `[dev]`; `--timeout=120` in default addopts
  so a hanging test now fails loudly within two minutes.
- `docs/decisions/ADR-001-python-version-policy.md` — pin to
  `>=3.11,<3.13` with verified before/after numbers.
- `docs/decisions/ADR-002-optimization-stack-pin.md` — pin
  `torch~=2.11.0 / botorch~=0.17.2 / gpytorch~=1.15.2`.
- `tests/test_optimization_smoke.py` — runtime gate for the botorch
  partitioning duck-typing (anchors ADR-002).
- `.github/workflows/ci.yml` — three jobs: `quick` (3.11 + 3.12 matrix
  with ruff + mypy + fast pytest), `smoke` (minimal install, smoke
  marker), `installer-smoke` (wheel build + clean-venv install verify).
  Addresses the v8.3.5 → v8.3.7 + v9.0 hotfix cascade.
- New 16² Cahn-Hilliard 2D smoke test (currently `@slow` pending the
  `build_mobility_laplacian_2d` perf bug — tracked for v9.1.1).
- `[tool.ruff]` per-file-ignores in `pyproject.toml` for the
  documented Streamlit reload pattern and the config-logger ordering.

### Fixed
- `tests/test_data_layer.py::TestKernelConfig::test_for_rotor_stator_legacy`
  — assertion was stale post-F1 fix (2026-04-17). Test now matches the
  source-of-truth `phi_d_correction=True, coalescence_exponent=2`.
- `tests/test_level2_gelation.py::TestCahnHilliard2DSolver::test_solve_gelation_1d_fallback`
  — converted to the new `mode='ch_1d'` API (was passing the removed
  `use_2d=` kwarg).
- `src/dpsim/visualization/pages/reagent_detail.py` — renamed loop
  variable to break a `ProtocolStep` / `ReactionStep` cross-wire that
  surfaced as 4 mypy errors at lines 153–156.
- `src/dpsim/module3_performance/orchestrator.py:798` — narrowed the
  `gradient.value_at_time(time)` union with `np.asarray` so the
  `GradientElutionResult.gradient_profile` assignment type-checks.
- `src/dpsim/visualization/tabs/tab_m3.py:173` — dropped the
  unsupported `component_names=` kwarg from `CompetitiveLangmuirIsotherm`.

### Changed
- `src/dpsim/optimization/engine.py` — replaced the `**tkwargs` dict
  unpacking with explicit `dtype=_DTYPE` at all eight call sites. This
  clears ~50 mypy stub errors without changing runtime behaviour.
- `pyproject.toml` `[optimization]` — `botorch>=0.11 / gpytorch>=1.11
  / torch>=2.1` → `botorch~=0.17.2 / gpytorch~=1.15.2 / torch~=2.11.0`
  (ADR-002).
- `pyproject.toml` `[project]` — `requires-python = ">=3.11"` →
  `">=3.11,<3.13"` (ADR-001).
- Added `__all__` to `src/dpsim/__init__.py` and
  `src/dpsim/visualization/__init__.py` to make re-exports explicit
  rather than letting ruff F401 flag them.
- Bulk auto-cleaned 105 ruff F401/F541 violations (unused imports,
  f-strings without placeholders) across 30+ source files. No
  behaviour change; smoke tests pass before and after.
- `@pytest.mark.slow` added to: `TestCahnHilliard2DSolver` (6 tests),
  `TestPBESolver` fast_result tests (5 tests, fixture promoted to
  `scope="class"`), `TestStirredVesselSolverIntegration` (3 tests),
  five `TestPackedBed*` classes in `test_module3_catalysis.py`,
  parametrized `test_toml_config_loads_and_runs`. Each marker carries
  a comment explaining the runtime cost.

### Known issues (v9.1.1)
- `solve_packed_bed` and L1 PBE-via-default.toml hit ill-conditioned
  scipy BDF Jacobians (overflow warnings in `num_jac`) and exceed the
  60 s timeout. Marked `@slow` for now; root cause is RHS scaling.
- `build_mobility_laplacian_2d` (CH 2D) is too slow even on a 16²
  grid. Independent of Python version. Smoke test exists but is `@slow`.
- 17 `F841` unused-local-variable instances in scientific solvers and
  Streamlit tab code. Per-file-ignored for now; domain-by-domain
  triage planned.
- 72 mypy errors remain across `level1_emulsification/solver.py`,
  `protocols/mechanism_data.py`, `level2_gelation/pore_analysis.py`,
  and others. Outside M3 (audit-flagged) scope.
- Promote the CI `installer-smoke` job from wheel-build-only to a
  full silent-install + launch-assert against the actual `.exe`
  installer.

## v8.3.7 — CRLF line endings on shipped .bat files (2026-04-18)

Hotfix for a fatal cmd-parser error on install:

```
[DPSim 8.3.6] Installer -- Windows 11 x64
Python 3.14.3
. was unexpected at this time.
```

### Root cause

The `.bat` files in the v8.3.6 release tree had **Unix LF line
endings** rather than Windows CRLF. A `sed -i` invocation during a
prior version bump (running on Git-Bash) stripped CRLFs from the
files. Windows `cmd.exe` tolerates LF in trivial single-line
commands, but multi-line constructs — specifically

```
for /f "tokens=1,2 delims=." %%a in ("%PYVER%") do (
    set "PYMAJ=%%a"
    set "PYMIN=%%b"
)
```

— get mis-parsed: cmd collapses the block into one logical line
and then chokes on the literal `.` in `delims=.`, giving the
cryptic `. was unexpected at this time` error. Install.bat exits
before it can create `.venv`; all downstream launchers fail.

### Fix

- `release/.../*.bat` — every shipped `.bat` file is now explicitly
  CRLF-terminated.
- `installer/build_installer.bat` — CRLF normalisation step added
  in the staging phase, so future bumps via sed/awk cannot recreate
  this failure mode.

### Workaround for users on v8.3.6 or earlier

The install.bat's bytes-level work is reproducible by hand. From
a Command Prompt at the install directory:

```
python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip wheel
.venv\Scripts\python.exe -m pip install "wheels\dpsim-<ver>-py3-none-any.whl[ui,optimization]"
.venv\Scripts\python.exe -m dpsim ui
```

That bypasses the buggy batch parser entirely.

### Version bumps

- `pyproject.toml`, `__init__.py`: 8.3.6 → 8.3.7.

### Artefacts

- `release/DPSim-8.3.7-Setup.exe` (2.54 MB)
- `release/DPSim-8.3.7-Windows-x64.zip` (566 KB)

---

## v8.3.6 — Import-probe launchers + auto-open browser (2026-04-17)

### Fixed

- `_cmd_ui` no longer passes `--server.headless true` to streamlit,
  so the UI opens the user's default browser automatically. The old
  behaviour required the user to notice the "Open
  http://localhost:8501 in your browser" line and navigate there by
  hand — easy to miss.
- `launch_ui.bat` and `launch_cli.bat` now probe
  `python -c "import dpsim"` as well as checking `.venv\` file
  existence. A partially-created venv (say install.bat failed
  between `python -m venv .venv` and the wheel pip-install) no
  longer bypasses the self-heal path.

### Added

- `release/.../WHERE_ARE_THE_PROGRAM_FILES.txt` — prominent
  short explainer answering the "I don't see a program in the
  install folder!" question. Describes the wheel → venv → site-
  packages flow and gives the one-line command to verify the
  install worked.
- `install.bat` success banner now prints the exact path where
  program files landed after pip install:
  `<install_dir>\.venv\Lib\site-packages\dpsim\`.

### Version bumps

- `pyproject.toml`, `__init__.py`: 8.3.5 → 8.3.6.

### Artefacts

- `release/DPSim-8.3.6-Setup.exe` (2.54 MB)
- `release/DPSim-8.3.6-Windows-x64.zip` (566 KB)

---

## v8.3.5 — Diagnostic-safe launch (fixes flash-crash window) (2026-04-17)

Hotfix for a "flash-and-close" launch experience where double-clicking
the desktop shortcut opened a Command Prompt that disappeared in a
fraction of a second, giving the user no chance to read the actual
error.

### Root cause

Two compounding bugs:

1. `_cmd_ui` (in `src/dpsim/__main__.py`) called
   `subprocess.run(["streamlit", ...])` without propagating the
   subprocess's return code. When Streamlit crashed (e.g., import
   error, port conflict), the parent Python process exited with
   code 0, pretending success.
2. `launch_ui.bat` ran the Python command and did
   `exit /b %ERRORLEVEL%` immediately afterward. A zero exit code
   → normal completion → `cmd /c` closes the window
   instantaneously, taking any error output with it.

Result: users saw a black cmd window blink open and close; no way
to diagnose.

### Fix

- `src/dpsim/__main__.py` / `_cmd_ui`: capture the subprocess
  result and `sys.exit(result.returncode)` when it is non-zero.
  Streamlit failures now propagate up.
- `release/DPSim-8.3.5-Windows-x64/launch_ui.bat`: after the
  Python call returns, if the exit code is non-zero, print a
  diagnostic block (port-conflict / dependency / version hints)
  + a manual-diagnosis command line, then `pause` before exit.
  The window now stays open whenever the UI exited abnormally.
  Normal shutdown (Streamlit exit code 0) still closes the window
  cleanly.

### Version bumps

- `pyproject.toml`, `src/dpsim/__init__.py`: 8.3.4 → 8.3.5.
- Installer script + build helper + release tree: 8.3.4 → 8.3.5.

### Artefacts

- `release/DPSim-8.3.5-Setup.exe` (2.54 MB)
- `release/DPSim-8.3.5-Windows-x64.zip` (564 KB)

### Immediate workaround for v8.3.4 users

If you can't wait for the installer rebuild, open a Command Prompt
manually and run:

```
cd /d "%LOCALAPPDATA%\Programs\DPSim"
.venv\Scripts\python.exe -m dpsim ui
```

That bypasses the `.bat` wrapper entirely and shows the actual
traceback in a window that stays open.

---

## v8.3.4 — Per-user install by default (fixes Access Denied) (2026-04-17)

Hotfix for a second install-time failure reported after v8.3.3:

```
[install] Creating virtual environment at .venv\
Error: [WinError 5] Access is denied: 'C:\Program Files\DPSim\.venv'
[install] ERROR: venv creation failed.
```

### Root cause

The v8.3.2 / v8.3.3 Inno Setup script used
`DefaultDirName={autopf}\DPSim` with
`PrivilegesRequiredOverridesAllowed=dialog`. On a UAC-elevated
install Inno Setup placed files into `C:\Program Files\DPSim`,
but the `[Run]` post-install step (`install.bat`) executes in the
user's non-elevated context. Non-admin cannot create `.venv\`
inside `C:\Program Files\...`, so venv creation fails.

### Fix (Inno Setup script)

- `DefaultDirName={userpf}\DPSim` — per-user Program Files
  (`%LOCALAPPDATA%\Programs\DPSim`), always user-writable.
- `PrivilegesRequiredOverridesAllowed=dialog` removed — user can no
  longer accidentally elevate to a location where the post-install
  step will fail.
- `UsedUserAreasWarning=no` — suppresses the Inno warning that
  would otherwise trigger for an all-user-area install script.

### Fix (install.bat)

- Venv-creation failure now prints an actionable diagnostic:
  "directory not writable → uninstall and reinstall v8.3.4+ per-user,
  or right-click install.bat → Run as administrator".
- No more silent exit 3.

### Migration note for existing admin installs

If v8.3.2 or v8.3.3 was installed into `C:\Program Files\DPSim`:

1. Uninstall (Control Panel → Apps → DPSim, or the Start-Menu
   "Uninstall DPSim" shortcut).
2. Download `DPSim-8.3.4-Setup.exe` from the GitHub Release.
3. Double-click — it installs into `%LOCALAPPDATA%\Programs\DPSim`
   without UAC. The post-install step completes cleanly.

### Version bumps

- `pyproject.toml`, `src/dpsim/__init__.py`, installer script,
  build helper: 8.3.3 → 8.3.4.

### Artefacts

- `release/DPSim-8.3.4-Setup.exe` (2.54 MB)
- `release/DPSim-8.3.4-Windows-x64.zip` (563 KB)
- `dist/dpsim-8.3.4-py3-none-any.whl`

Wheel contents unchanged from v8.3.2.

---

## v8.3.3 — Self-healing launch scripts (2026-04-17)

Hotfix for a dead-end user experience on first run: if the installer's
post-install step was skipped or failed silently (e.g. because
Python 3.11+ was not on PATH at install time), the launcher batch
files previously printed only "Installation not found. Run install.bat
first." and exited, with no actionable guidance.

### Fixed

- `release/.../launch_ui.bat` and `release/.../launch_cli.bat`:
  **self-healing**. On missing `.venv`, they now
  1. report the exact expected path,
  2. probe for `python` on `PATH` and show the detected version,
  3. if Python is absent, print a hyperlink to
     `https://www.python.org/downloads/windows/` and abort cleanly
     with a press-any-key,
  4. if Python is present, offer to run `install.bat --no-test`
     automatically and then continue to the launch,
  5. if setup fails, show the error code and keep the window
     open so the user sees the cause.
- `release/.../install.bat`: always `pause` on completion so the
  user sees the success / failure message. Honours
  `NONINTERACTIVE=1` when invoked from automation. Explicit error
  message + pause on pip-upgrade failure (previously exited 4
  silently).

### Changed (version bumps)

- `pyproject.toml`: 8.3.2 → 8.3.3.
- `src/dpsim/__init__.py.__version__`: 8.3.2 → 8.3.3.
- `installer/DPSim.iss`, `installer/build_installer.bat`: all
  `8.3.2` references updated to `8.3.3`.

### Artefacts

- `release/DPSim-8.3.3-Setup.exe` (2.54 MB) — Inno Setup wizard.
- `release/DPSim-8.3.3-Windows-x64.zip` (563 KB) — portable.
- `dist/dpsim-8.3.3-py3-none-any.whl` (~408 KB) — wheel.

All three are identical in wheel contents to v8.3.2; only the
launcher batch files changed. Users who already have a working
v8.3.2 install can just replace `launch_ui.bat` / `launch_cli.bat` /
`install.bat` with the v8.3.3 versions.

### Smoke verified

Fresh temp venv + `pip install dpsim-8.3.3-py3-none-any.whl` +
`import dpsim` — works end-to-end.

---

## v8.3.2 — One-click Windows 11 installer (.exe) (2026-04-17)

Ships a proper Windows installer wizard as
`release/DPSim-8.3.2-Setup.exe` (2.54 MB), attached to the
existing v8.3.2 GitHub Release alongside the portable ZIP.

### Added

- `installer/DPSim.iss` — Inno Setup 6 script defining the full
  wizard:
  1. **EULA page** (`LICENSE_AND_IP.txt`) declaring: intellectual
     property rights belong to Holocyte Pty Ltd; software licensed
     under GPL-3.0; canonical source at
     `github.com/tocvicmeng-prog/Downstream-Processing-Simulator`.
  2. **Python presence check** with a clickable hyperlink to
     `https://www.python.org/downloads/windows/` if Python 3.11+ is
     not on PATH.
  3. **File layout** — wheel, configs, docs, launcher batch files,
     LICENSE, README, INSTALL, RELEASE_NOTES all extracted under a
     single install directory.
  4. **Shortcuts** — Start-Menu group with Web-UI, CLI, Manual
     PDF, and Uninstall entries; optional desktop shortcut.
  5. **Post-install hook** — runs the bundled `install.bat` which
     creates a self-contained `.venv` and pip-installs the wheel
     with `[ui,optimization]` extras, with a smoke-pipeline check.
  6. **Uninstaller** — purges `.venv` before removing files.
- `installer/LICENSE_AND_IP.txt` — the EULA text shown on the
  installer's first page.
- `installer/build_installer.bat` — four-step build helper
  (wheel, stage, locate ISCC, compile).
- `installer/README.md` — documentation of the installer build and
  runtime behaviour.

### Changed

- `.gitignore` — now also excludes `installer/stage/` (transient
  build directory rebuilt by `build_installer.bat`).

### GitHub Release (v8.3.2)

Two assets now attached:

| Asset | Size | Audience |
|---|---|---|
| `DPSim-8.3.2-Setup.exe` | 2.54 MB | End users (one-click wizard installer) |
| `DPSim-8.3.2-Windows-x64.zip` | 561 KB | Power users (portable, script-based install) |

---

## v8.3.2 — Clean Windows 11 x64 install package (2026-04-17)

Ships a self-contained, dev-artifact-free Windows 11 x64 install
bundle as `release/DPSim-8.3.2-Windows-x64.zip` (0.55 MB
compressed, 14 files). A fresh Windows machine with Python 3.11+
installed can extract the zip and run `install.bat` to get a
fully working simulator — UI, CLI, and programmatic API — in a
self-contained `.venv\` that leaves system Python untouched.

### Version bumps

- `pyproject.toml`: 0.1.0 → 8.3.2 (caught up with feature releases).
- `src/dpsim/__init__.py.__version__`: 0.1.0 → 8.3.2.

### Build artefacts

- `dist/dpsim-8.3.2-py3-none-any.whl` — rebuilt wheel covering
  the full v8.3 feature set (four polymer platforms, inverse
  design, digital twin, MD ingest, Unicode-safe PDF manual).
- `dist/dpsim-8.3.2.tar.gz` — source distribution.

### Release tree (`release/DPSim-8.3.2-Windows-x64/`)

| File | Purpose |
|---|---|
| `install.bat` | Create `.venv\`, install wheel with `[ui,optimization]` extras, verify import, run smoke pipeline. Accepts `--core` / `--no-opt` / `--no-test` flags. |
| `launch_ui.bat` | Start the Streamlit UI at `http://localhost:8501`. |
| `launch_cli.bat` | Open a Command Prompt with the venv activated and `dpsim` on PATH. |
| `uninstall.bat` | Confirm-and-delete the `.venv\`. |
| `README.txt` | One-page quickstart. |
| `INSTALL.md` | Detailed install + troubleshooting guide (7 sections). |
| `RELEASE_NOTES.md` | User-facing summary of what's in 8.3.2. |
| `LICENSE.txt` | Software licence. |
| `wheels/dpsim-8.3.2-py3-none-any.whl` | The wheel (408 KB). |
| `configs/{default,fast_smoke,stirred_vessel}.toml` | Example configs. |
| `docs/User_Manual_First_Edition.{pdf,md}` | First Edition manual. |

### "Clean" guarantees (validated at zip time)

The zip-builder refuses to create the archive if any of these are
present in the release tree:

- `__pycache__/`, `.pyc`, `.pyo`
- `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`
- `.git/`, `.venv/`
- `build/`, `dist/`, `output/`
- `.log` files

Not shipped in the release (kept in the dev repo only):

- Source tree (`src/` — replaced by the wheel).
- Test suite (`tests/`).
- Internal design docs (`docs/f1a_*`, `docs/f1b_*`, `docs/f1c_*`,
  `docs/f2_*`, `docs/f4b_*`, `docs/f5_*`, `docs/node31_*`,
  `docs/node32_*`, `docs/node30_31_*`).
- Full dev `CHANGELOG.md` (condensed into `RELEASE_NOTES.md`).
- `skills/`, `.claude/` agent infrastructure.

### Smoke verification (performed before the ZIP was cut)

- Fresh temp venv + `pip install wheels/dpsim-8.3.2-py3-none-any.whl`:
  install succeeded.
- `import dpsim; dpsim.__version__ == '8.3.2'` — OK.
- `run_pipeline()` default: returns a FullResult with
  `d32 = 18.08 µm` — end-to-end L1 → L4 pipeline executes cleanly
  on a fresh install.

### Final archive

`release/DPSim-8.3.2-Windows-x64.zip` — 561 KB compressed,
648 KB uncompressed, 14 files. Ready for distribution.

---

## v8.3.2 — First Edition PDF Unicode font fix (2026-04-17)

Fixes black-square ("tofu") rendering of scientific Unicode glyphs
(α, ²⁺, ⌈⌉, χ, ∇, ∂, μ, π, ≥, etc.) in the First Edition PDF.

### Root cause

reportlab's built-in Type-1 fonts (Helvetica / Courier) cover only
WinAnsi / Latin-1. Any glyph outside that band — superscripts, Greek
letters, ceiling / floor brackets, mathematical operators — was
rendered as a black filled square. Visible examples reported by the
user: `Ca²⁺-alginate`, `CVaR_α = (1 / ⌈α·N⌉)`.

### Fix

- `docs/user_manual/build_pdf.py` — register DejaVu Sans and DejaVu
  Sans Mono (shipped with matplotlib, each ~6 000 Unicode glyphs
  covering full Greek, super/subscripts, mathematical operators,
  arrows) as TTF fonts via `reportlab.pdfbase.pdfmetrics.registerFont`
  / `registerFontFamily` at module import time. All body, heading,
  code, bullet, caption, table-cell, and page-footer styles now
  reference `DejaVuSans` / `DejaVuSansMono` instead of
  `Helvetica` / `Courier`. Falls back gracefully to the Type-1
  fonts if DejaVu is missing.
- `docs/user_manual/polysaccharide_microsphere_simulator_first_edition.pdf`
  — rebuilt. File size 55 KB → 143 KB (DejaVu TTFs now embedded).

### Verification

- Font cmap coverage confirmed for 20 scientific codepoints
  (U+00B2, U+207A, U+207B, U+03B1, U+03C7, U+03BC, U+2308, U+2309,
  U+00B7, U+2192, U+2207, U+2202, U+222B, U+03C0, U+00B0, U+2265,
  U+2264, U+00B1, U+00D7, U+00D8): **20/20 present**.
- Round-trip text extraction via pypdf finds all user-flagged
  phrases literally in the rebuilt PDF:
  - `Ca²⁺-alginate` present
  - `⌈α·N⌉` present
  - α, χ, ∇, ∂, ≥, π, · present.

---

## v8.3.1 — First Edition user manual (2026-04-17)

Ships the Downstream Processing Simulator
**First Edition** instruction manual as Markdown + PDF, with an
upper-right download button wired into the Streamlit UI. The
manual is written for first-time users (downstream-processing
technicians, junior researchers) who have no prior experience in
microsphere fabrication or downstream processing.

### Added

- `docs/user_manual/polysaccharide_microsphere_simulator_first_edition.md`
  — the authoritative instruction manual. Three-part structure:
  1. **Getting Started** — what the simulator does, workflow
     overview with ASCII chart, five-minute quickstart.
  2. **Platform Catalogue** — the four supported polymer families
     (agarose-chitosan, alginate, cellulose NIPS, PLGA), a
     crosslinker / gelant selection table, the EDC/NHS COOH
     warning.
  3. **Appendices A–I** — detailed input requirements (all
     parameter tables with units + ranges + defaults), process
     steps, essential pre-run checklist, 15-question FAQ,
     architectural ideas + working principles, chemical / physical
     principles, formulas + theorems, six standard wet-lab
     protocols (agarose-chitosan/genipin, Ca²⁺-alginate external &
     internal, cellulose NaOH/urea, EDC/NHS coupling, PLGA
     solvent-evaporation), and a 17-row troubleshooting table.
- `docs/user_manual/build_pdf.py` — compact Markdown-to-PDF
  renderer using reportlab. Handles the Markdown subset used in
  the manual (headings, paragraphs, ordered / unordered lists,
  GitHub tables, fenced code blocks, inline `**bold**` /
  `*italic*` / `` `code` `` with underscore-safe code-span
  extraction via placeholders). Run
  `python docs/user_manual/build_pdf.py` to rebuild.
- `docs/user_manual/polysaccharide_microsphere_simulator_first_edition.pdf`
  — the built artefact (~55 KB, A4, page-footer on every page).

### Changed

- `src/dpsim/visualization/app.py` — the page title row now uses a
  two-column layout with the title on the left and a
  **Manual (PDF)** download button in the upper-right corner.
  Button serves the PDF via `st.download_button` when the file
  exists; falls back to a caption telling the user to run the
  build script if the PDF is absent.

### Dependencies

- `reportlab` added (auto-installed into the user's pip environment
  during the build step). No new runtime requirement for users who
  don't need to regenerate the PDF.

### Tests

- Quick regression of 66 targeted tests (F4-b, F5, F2, PLGA Phase 2,
  cellulose Phase 2/3, alginate L4) pass with 0 regressions after
  the UI edit.

---

## v8.3.0-alpha — Cluster F finish: F4-b CVaR + F5 MD ingest + F2 digital twin (2026-04-17)

Closes the three remaining Cluster F workstreams from the Node 32
roadmap. With this release, **every workstream in Cluster F has a
Phase 1 shipment**.

### F4-b — CVaR robust BO

- `OptimizationEngine(robust_cvar_alpha=α)` — applies Conditional
  Value-at-Risk aggregation over resamples. When both
  `robust_variance_weight` and `robust_cvar_alpha` are set, CVaR
  takes precedence.
- `dpsim design --robust-cvar-alpha α` CLI flag.
- Algorithm: ``CVaR_α = mean of the worst ⌈α·n⌉ resamples per
  objective dimension``. α → 1 recovers the sample mean; α → 0
  approaches the worst-case sample.
- Validation: α ∈ [0, 1]; α > 0 requires `robust_n_samples >= 2`
  and a `target_spec`.
- `docs/f4b_cvar_protocol.md` — full /architect protocol.
- `tests/test_f4b_cvar.py` — 11 tests (math, engine validation,
  CLI, precedence, head-to-head vs mean-variance).

### F5 — MARTINI MD parameter ingest

- `src/dpsim/md_ingest.py` — `MartiniRecord` dataclass + JSON
  load / save + `apply_chi_to_props(props, record)` for cellulose
  χ fields.
- JSON schema: required `source / system_description / beads / chi /
  diagnostics`; optional `paper_doi / notes`; forward-compat
  unknown top-level keys preserved in `record.extra`.
- Current mapping: `polymer_solvent / polymer_nonsolvent /
  solvent_nonsolvent` → `chi_PS_cellulose / chi_PN_cellulose /
  chi_SN_cellulose` on `MaterialProperties`. Non-cellulose fields
  never modified. Missing χ sub-keys leave fields untouched.
- Validation: NaN / inf χ rejected at load; negative χ allowed
  (physically valid for attractive mixing).
- `data/validation/md/example_martini_cellulose.json` — reference
  fixture for tests and user-authoring template.
- `docs/f5_md_ingest_protocol.md` — full /architect protocol.
- `tests/test_md_ingest.py` — 11 tests (load, missing keys,
  extra-keys preservation, partial χ, apply to props, non-cellulose
  fields untouched, non-finite guards, negative χ, round-trip).

### F2 — Digital twin EnKF replay (Phase 1)

- `src/dpsim/digital_twin/enkf.py` — stochastic Ensemble Kalman
  Filter (Evensen 1994) `enkf_update(x, y_fc, y_obs, R, rng,
  inflation)`. Scalar observations only in Phase 1; multiplicative
  prior inflation optional.
- `src/dpsim/digital_twin/replay.py` — `run_replay(trace, x0,
  state_transition, observation_operator, ...)` walks forward
  through a `DigitalTwinTrace`, applies EnKF at each observation,
  returns `ReplayResult` with per-observation mean / std / optional
  full ensemble + a `DigitalTwin.EnKFReplay` SEMI_QUANTITATIVE
  manifest.
- `src/dpsim/digital_twin/schema.py` — `DigitalTwinTrace` +
  `Observation` dataclasses + JSON load / save (sorts observations
  by time on load).
- `src/dpsim/digital_twin/__init__.py` — module exports.
- `docs/f2_digital_twin_protocol.md` — full /architect protocol.
- `tests/test_digital_twin.py` — 11 tests (EnKF linear-Gaussian
  convergence, zero-noise collapse, inflation grows spread, EnKF
  input validation, trace round-trip + time-ordering on load,
  replay trajectory shape, empty-trace passthrough, multi-step
  spread shrinkage).

### Tests

- 33 new tests across F4-b (11) + F5 (11) + F2 (11). 218 targeted
  regression tests pass (PLGA Phase 1/2 + cellulose Phase 1/2/3 +
  internal-gelation + alginate 2a/b/c + EDC/NHS + UQ unified + CLI
  v7 + inverse-design + F4-b + F5 + F2) with 0 regressions.

### Footprint

- F4-b: ~220 LOC (engine edit + CLI + tests).
- F5: ~465 LOC (module + fixture + tests + docs).
- F2: ~895 LOC (schema + enkf + replay + __init__ + tests + docs).
- Total: ~1580 LOC added this turn.

### Cluster F status

All Cluster F workstreams from the Node 32 v8.0 roadmap are at
least Phase-1 shipped:

| Workstream | Status |
|---|---|
| F1-a Alginate | ✓ fully wired (v8.0-rc2) |
| F1-b Cellulose NIPS | ✓ fully wired (v8.1-beta) |
| F1-c PLGA | ✓ fully wired (v8.2-beta) |
| F2 Digital twin (EnKF replay) | ✓ Phase 1 shipped (v8.3-alpha) |
| F3-a Inverse design | ✓ complete (v8.0-alpha) |
| F3-b/c BO engine + CLI | ✓ complete (v8.0-alpha) |
| F4-a Robust BO (mean-variance) | ✓ complete (v8.0-alpha) |
| F4-b Robust BO (CVaR) | ✓ complete (v8.3-alpha) |
| F5 MD ingest (MARTINI) | ✓ Phase 1 shipped (v8.3-alpha) |

### Still deferred (Phase-2+ items, each needs fresh /architect kickoff)

- F2: vector observations (matrix R), square-root / deterministic
  EnKF variants, online polling adapter, MPC layer, identifiability
  diagnostics.
- F5: tabulated U(r) pair-potential ingestion, automatic
  MARTINI ↔ DPSim bead-type mapping, CalibrationStore integration,
  reverse-direction emit.
- F4-b: automatic α selection (tail-risk auto-tune).
- PLGA moving-boundary ALE solver + Fujita `D(phi)`.
- v7.0 release still blocked on Study A wet-lab data.

---

## v8.2.0-beta — F1-c Phase 2: PLGA orchestrator + CLI + TOML (2026-04-17)

Closes F1-c. **All three Cluster F platforms (alginate, cellulose,
PLGA) are now fully wired end-to-end** — orchestrator dispatch, CLI
flags, and TOML config keys. F1 (multi-platform microsphere family)
is complete at the protocol-scope level.

### Added

- `PipelineOrchestrator._run_plga(...)` — mirrors `_run_cellulose` /
  `_run_alginate`. Applies `params.formulation.plga_grade` preset to
  MaterialProperties before the L2 solver runs. Skips L2a timing and
  L3 crosslinking (PLGA microspheres are glassy / physically
  entangled, not crosslinked); stubs `CrosslinkingResult`. Emits
  summary.json with `polymer_family = "plga"`, L2 diagnostics
  (`phi_plga_mean_final`, `t_vitrification_s`,
  `skin_thickness_proxy_m`, `R_shrunk_m`), and the L4 modulus.
- `run_single` branch: `props.polymer_family == PolymerFamily.PLGA`
  routes to `_run_plga`. Placed immediately after the cellulose
  branch for symmetry.
- `dpsim run --plga-grade {50_50 | 75_25 | 85_15 | pla}` CLI flag.
  Packs the grade's 4 PLGA-specific fields into `props_overrides`.
  Meaningful with `--polymer-family plga`; prints a one-line
  confirmation unless `--quiet`.
- TOML `[formulation].plga_grade = "..."` unpacks directly into the
  existing `FormulationParameters.plga_grade` field (shipped in
  F1-c Phase 1); orchestrator resolves at run time via
  `properties.plga_defaults.apply_preset`.

### Changed

- `orchestrator.py` — new imports (`solve_solvent_evaporation`,
  `solve_mechanical_plga`), new PLGA branch, new `_run_plga` method
  (~115 LOC).
- `__main__.py` — `--plga-grade` flag + `_cmd_run` hook to expand
  preset into `props_overrides`.
- `config.py` — no changes needed; TOML key unpacks naturally via
  the existing `plga_grade` field.

### Tests

- `tests/test_plga_phase2.py` — 12 tests:
  - Orchestrator dispatch (3): PLGA routes to `_run_plga`, summary.json
    records `polymer_family`, full pipeline reports
    SEMI_QUANTITATIVE end-to-end.
  - Preset application (2): orchestrator patches props (85:15 K_glassy
    = 1 × 10⁹ Pa verified); unknown grade raises `KeyError`.
  - TOML (2): `plga_grade` key unpacks; absent defaults to empty string.
  - CLI (2): all 4 choices in shipped parser source; argparse accepts
    the full flag invocation.
  - End-to-end sanity (3): non-zero G_DN; switching grade gives ≥
    1.5× modulus spread; L3 `p_final = 0` (stubbed).
- 185 targeted regression tests pass (PLGA Phase 1 + Phase 2 +
  cellulose Phases 1/2/3 + internal-gelation + alginate 2a/b/c +
  EDC/NHS + UQ unified + CLI v7 + inverse-design) with 0 regressions.

### Footprint

- New LOC: ~115 (orchestrator `_run_plga`) + ~30 (CLI) + ~340
  (tests) ≈ 485 LOC. Under the protocol's ~430 LOC estimate by a
  hair (simple wiring + trivial TOML).
- Cumulative F1 footprint across all three platforms: **~5000 LOC**.

### Cluster F status after v8.2.0-beta

| Platform | Programmatic | Orchestrator | CLI | TOML | Presets |
|---|---|---|---|---|---|
| Agarose-chitosan (default) | ✓ | ✓ | ✓ | ✓ | (built-in) |
| Alginate | ✓ | ✓ | ✓ | ✓ | 2 gelants |
| Cellulose NIPS | ✓ | ✓ | ✓ | ✓ | 4 solvents |
| PLGA solvent evap | ✓ | ✓ | ✓ | ✓ | 4 grades |

**F1 complete.** Other Cluster F workstreams remain un-started and
need their own /architect kickoffs:

- **F2 digital twin** (EnKF replay harness) — scoped in Node 32
  roadmap, protocol not drafted.
- **F4-b CVaR acquisition** — deferred v8.0 polish; trivial variant
  of F4-a once the resample strategy is finalised.
- **F5 MD parameter ingest** (MARTINI — ingest-only default) —
  scoped in Node 32 roadmap, protocol not drafted.

### Still deferred

- Moving-boundary ALE solver for PLGA shrinking-droplet correction
  (R5 from F1-c protocol).
- Fujita concentration-dependent `D(phi)` for late-stage PLGA
  evaporation dynamics.
- v7.0 release still blocked on Study A wet-lab data.

---

## v8.2.0-alpha — F1-c Phase 1: PLGA solvent-evaporation L2 + L4 + 4 grades (2026-04-17)

First shipment of Cluster F platform #3. Adds a PLGA /
solvent-evaporation L2 solver + Gibson-Ashby L4 modulus + full 4-grade
registry (PLGA 50:50 / 75:25 / 85:15 / PLA). Ships as
**programmatic API only**; orchestrator dispatch / CLI / TOML = F1-c
Phase 2.

### Added

- `docs/f1c_plga_protocol.md` — full /architect protocol doc (§1 scope,
  §2 mechanism + lit anchors, §4 algorithm, §5 4-grade parameter
  table, §6 16 test cases, §7 risks, §8 G1 12/12 for Phase 1,
  §9 execution plan). Matches the f1a / f1b protocol pattern.
- `src/dpsim/level2_gelation/solvent_evaporation.py` (~330 LOC):
  1D spherical Fickian DCM-depletion solver.
  - State: ``phi_DCM(r, t)`` single field; ``phi_PLGA = 1 − phi_DCM``
    algebraic.
  - Dirichlet sink at ``r = R`` (``phi_DCM_eq ≈ 0.005`` for DCM/water),
    symmetry at ``r = 0``.
  - BDF time integrator with dense-output vitrification-time probe.
  - Approximations: fixed droplet radius (moving-boundary ALE = Phase 2
    refinement); constant D (Fujita ``D(phi)`` = Phase 2). Both
    flagged in manifest assumptions.
  - Emits SEMI_QUANTITATIVE `GelationResult` tagged
    `L2.Gelation.SolventEvaporationPLGA` with
    `phi_plga_mean_final / phi_dcm_mean_final / t_vitrification /
    skin_thickness_proxy / core_porosity_proxy / R_shrunk_m`
    diagnostics.
- `src/dpsim/level4_mechanical/plga.py` (~130 LOC):
  `plga_modulus(phi_mean, G_glassy, n_plga)` Gibson-Ashby power law +
  `solve_mechanical_plga(...)` wrapper emitting
  `L4.Mechanical.PLGAGibsonAshby` SEMI_QUANTITATIVE
  `MechanicalResult` with `network_type="glassy_polymer"` and
  `model_used="plga_gibson_ashby"`.
- `src/dpsim/properties/plga_defaults.py` (~160 LOC):
  `PLGAGradeProfile` dataclass + `PLGA_GRADE_PRESETS` registry with
  **all four** grades populated (`50_50`, `75_25`, `85_15`, `pla`).
  Data sourced from Wang 1999 (D_DCM), Park 1998 (T_g, G_glassy),
  Freitas 2005 (process parameters). `apply_preset(props, grade)`
  helper mirrors the alginate / cellulose pattern. Phase 3 is
  effectively eliminated by shipping all 4 presets up front.
- `MaterialProperties` gains 4 PLGA-specific fields
  (`D_DCM_plga`, `phi_DCM_eq`, `G_glassy_plga`, `n_plga_modulus`).
- `FormulationParameters` gains `phi_PLGA_0` (initial polymer volume
  fraction in the droplet; default 0 = not-PLGA) and `plga_grade`
  (Phase 2 preset-selector field; default empty = skip).

### Tests

- `tests/test_plga_phase1.py` — 25 tests covering:
  - **Protocol §6 test 1**: monotone DCM depletion (with fixed
    transient-regime probe times)
  - **Protocol §6 test 2**: Dirichlet sink drives `phi_PLGA → 1` at
    long time
  - **Protocol §6 test 3**: early-regime √t front scaling (log-log
    slope 0.5 ± 0.15)
  - **Protocol §6 test 4**: 4× D_DCM gives earlier vitrification
  - **Protocol §6 test 5**: Gibson-Ashby `G ∝ phi^n` scaling (n ∈
    {1.5, 2.0, 2.5}); dense limit recovers `G_glassy`
  - **Protocol §6 test 6**: zero PLGA → UNSUPPORTED manifest + zero
    modulus
  - **Protocol §6 test 7**: L2 + L4 both SEMI_QUANTITATIVE; full
    diagnostic key presence
  - **Protocol §6 test 8**: `apply_preset` patches 4 PLGA fields;
    4 grades registered; physical-plausibility check on every grade
    (L_fraction, M_n, T_g, D, G_glassy, n ranges); switching grade
    gives ≥ 1.4× modulus spread
  - Edge cases: `plga_modulus` zero/negative inputs
  - Input validation: negative R, tiny grid, phi_0 out of [0, 1],
    negative time, non-positive D_DCM
  - Mass-conservation post-processing: `R_shrunk = R_0 · phi_0^(1/3)`
    at long time
- 173 targeted regression tests pass (PLGA Phase 1 + cellulose
  Phase 1/2/3 + internal-gelation + alginate 2a/b/c + EDC/NHS + UQ
  unified + CLI v7 + inverse-design) with 0 regressions.

### Footprint

- New LOC: ~330 (solver) + ~130 (L4) + ~160 (defaults) + ~25
  (datatypes) + ~390 (tests) ≈ 1035 LOC. Slightly over the protocol's
  ~910 LOC estimate because all 4 grade presets shipped in Phase 1
  instead of 3 being deferred to Phase 3.

### Still deferred

- **F1-c Phase 2** (~430 LOC, 1–2 sessions): orchestrator
  `_run_plga` branch (mirror `_run_cellulose`), `--polymer-family
  plga --plga-grade <name>` CLI surface, `[formulation].plga_grade`
  TOML key application, 12 integration tests.
- **F1-c Phase 3**: absorbed into Phase 1 (all 4 presets shipped).
- **Moving-boundary ALE solver** for shrinking-droplet correction
  (R5 from the protocol). Current fixed-R approximation reports
  `R_shrunk` as a post-processing diagnostic so users can plot the
  true final sphere.
- **Fujita concentration-dependent D**: v1 uses constant D; late-time
  (phi > 0.8) dynamics are order-of-magnitude-right, not quantitative.
- v7.0 release still blocked on Study A wet-lab data.

---

## v8.1.0-beta — F1-b Phases 2 + 3: cellulose orchestrator + all 4 solvents (2026-04-17)

Closes F1-b. Cellulose NIPS is now a first-class user-facing platform
(matches alginate surface area). All four solvent-system presets are
populated; the orchestrator dispatches `PolymerFamily.CELLULOSE`
through a dedicated `_run_cellulose` sub-pipeline; TOML and CLI flags
expose both family selection and solvent selection.

### Added

- `PipelineOrchestrator._run_cellulose(...)` — mirrors
  `_run_alginate`. Applies a solvent-system preset (if declared on
  `params.formulation.solvent_system`) to MaterialProperties before
  solving L2 NIPS. Skips L2a timing and L3 crosslinking (NIPS IS the
  gelation); stubs `CrosslinkingResult`. Emits summary.json with
  `polymer_family = "cellulose"`, `phi_mean_final`,
  `bicontinuous_score`, `demixing_index`, and the L4 modulus.
- `run_single` branch: `props.polymer_family == PolymerFamily.CELLULOSE`
  routes to `_run_cellulose`. Placed immediately after the alginate
  branch for symmetry.
- `FormulationParameters.solvent_system: str = ""` — TOML key
  `[formulation].solvent_system = "naoh_urea"` unpacks directly into
  this field, then the orchestrator resolves it at run time via
  `properties.cellulose_defaults.apply_preset`.
- `dpsim run --cellulose-solvent {naoh_urea | nmmo | emim_ac |
  dmac_licl}` CLI flag — packs the preset's 9 cellulose-specific
  fields into `props_overrides` before `run_single`. Meaningful with
  `--polymer-family cellulose`; prints a one-line confirmation
  (`Cellulose solvent preset: ...`) unless `--quiet`.
- Three new presets in `src/dpsim/properties/cellulose_defaults.py`:
  - **NMMO** (Lyocell, 80 wt% aq., T = 90 °C, higher N_p = 500,
    K_cell = 8 × 10⁵ Pa; Lenzing system).
  - **EMIM-Ac** (1-ethyl-3-methylimidazolium acetate, T = 80 °C,
    lowest χ_PS = 0.38; Swatloski 2002 IL system).
  - **DMAc/LiCl** (McCormick analytical system, T = 60 °C activation,
    K_cell = 6 × 10⁵ Pa). All values from the literature anchors in
    `docs/f1b_cellulose_nips_protocol.md` §5.

### Changed

- `orchestrator.py` — new imports (`solve_nips_cellulose`,
  `solve_mechanical_cellulose`), new CELLULOSE branch, new
  `_run_cellulose` method (~110 LOC).
- `__main__.py` — `--cellulose-solvent` flag + `_cmd_run` hook to
  expand preset into `props_overrides`.
- `config.py` — TOML `[formulation].solvent_system` unpacks naturally
  via the new `FormulationParameters.solvent_system` field. No
  special-case parsing; validation deferred to solver-time
  `apply_preset(...)`.

### Tests

- `tests/test_cellulose_phase2_phase3.py` — 14 tests:
  - Orchestrator dispatch (3): CELLULOSE routes to `_run_cellulose`,
    summary.json records polymer_family, full pipeline reports
    SEMI_QUANTITATIVE end-to-end.
  - TOML wiring (2): `solvent_system` key unpacks, absent key defaults
    to empty string.
  - Solvent preset application (2): orchestrator patches props so L4
    K_cell matches the NMMO preset (8 × 10⁵ Pa); unknown preset raises
    `KeyError`.
  - CLI (2): `--cellulose-solvent` flag in shipped parser, argparse
    accepts all 4 choices.
  - Registry (3): all 4 presets registered, each passes physical
    plausibility (χ_PN > χ_PS, D in bulk-water range, N_p in DP range,
    K_cell in 10⁴–10⁷ Pa band), water is the default non-solvent for
    all.
  - Diagnostics differentiation (1): switching preset changes G_DN by
    > 1.5× (spans real range).
  - Argparse rejection (1): unknown preset exits non-zero.
- 152 targeted regression tests pass (Phase 1 + Phase 2/3 +
  internal-gelation + alginate 2a/b/c + EDC/NHS + UQ unified + CLI v7
  + parallel MC + inverse-design) with 0 regressions.

### Footprint

- New LOC: ~110 (orchestrator `_run_cellulose`) + ~15 (CLI) + ~1
  (config.py, just the TOML doc comment) + ~160 (3 new presets) +
  ~330 (tests) ≈ 615 LOC. Cumulative F1-b footprint (Phases 1 + 2 +
  3): ~1525 LOC, a little under the 2000 LOC protocol budget because
  Phase 2 config wiring naturally unpacks via the single
  `solvent_system` field rather than needing a dedicated parser.

### Still deferred

- **v7.0 release** remains blocked on Study A wet-lab data.
- **F1-c PLGA solvent evaporation** still unscoped — a fresh
  /architect protocol is the natural next step if commercial
  prioritisation calls for it.

---

## v8.1.0-alpha — F1-b Phase 1: cellulose NIPS L2 + L4 + NaOH/urea (2026-04-17)

First shipment of Cluster F platform #2. Adds a cellulose /
non-solvent-induced phase separation (NIPS) L2 solver + L4 modulus +
NaOH/urea parameter preset. Ships as **programmatic API only** for now
— orchestrator dispatch / TOML config / CLI flags land in F1-b Phase 2.

### Added

- `src/dpsim/level2_gelation/nips_cellulose.py` (~380 LOC):
  1D spherical ternary Cahn-Hilliard + Fickian coupled-PDE solver.
  - State: `phi(r, t)` cellulose + `s(r, t)` solvent, `n = 1-phi-s`
    non-solvent (algebraic).
  - Flory-Huggins free energy with χ_PS / χ_PN / χ_SN.
  - Cahn-Hilliard gradient-energy regularisation on `mu_phi`.
  - Dirichlet bath BC at `r = R` (pure water by default), symmetry
    at `r = 0`.
  - 1 % noise on initial `phi` breaks spherical symmetry so spinodal
    decomposition can develop.
  - BDF time integration; clipped log arguments protect against
    spinodal excursions outside the physical simplex.
  - Emits SEMI_QUANTITATIVE `GelationResult` tagged
    `L2.Gelation.NIPSCellulose` with
    `phi_mean_final / s_mean_final / n_mean_final / phi_std_final /
    bicontinuous_score / demixing_index` diagnostics.
- `src/dpsim/level4_mechanical/cellulose.py` (~140 LOC):
  `cellulose_modulus(phi_mean, K_cell, alpha_cell)` power-law +
  `solve_mechanical_cellulose(...)` wrapper that emits
  `L4.Mechanical.CelluloseZhang2020` SEMI_QUANTITATIVE
  `MechanicalResult` with `network_type="physical_entangled"` and
  `model_used="cellulose_zhang2020"`.
- `src/dpsim/properties/cellulose_defaults.py` (~100 LOC):
  `CelluloseSolventPreset` dataclass + `CELLULOSE_SOLVENT_PRESETS`
  registry + `apply_preset(props, name)` helper. NaOH/urea preset
  (Zhang Lab Wuhan) populated from Lindman 2010 / Xu 2010 / Zhang
  2020. NMMO, EMIM-Ac, DMAc/LiCl stubs ship in F1-b Phase 3.
- `MaterialProperties` gains 9 cellulose-specific fields
  (`N_p_cellulose`, `chi_{PS,PN,SN}_cellulose`,
  `D_{solvent,nonsolvent}_cellulose`, `kappa_CH_cellulose`,
  `K_cell_modulus`, `alpha_cell_modulus`) — defaults match the
  NaOH/urea preset.
- `FormulationParameters.phi_cellulose_0` — initial cellulose volume
  fraction (default 0 = not-cellulose).

### Tests

- `tests/test_cellulose_nips_phase1.py` — 19 tests covering:
  - Protocol §6 test 2: ternary mass conservation (`phi + s + n = 1`)
  - Protocol §6 test 4: water-bath driven demixing (`phi_std` grows)
  - Protocol §6 test 7: modulus scaling `G ∝ phi^α`
  - Protocol §6 test 8: zero cellulose → zero gel / zero modulus
  - Protocol §6 test 10: SEMI_QUANTITATIVE manifests on both L2 and L4
  - NaOH/urea preset registry + `apply_preset` patching 9 fields
  - L4 modulus edge cases (zero phi / zero prefactor / negative phi)
  - Solver input validation (R ≤ 0, n_r < 8, phi_0 out of [0, 1],
    negative time / noise)
- 113 targeted regression tests pass (Phase 1 + internal-gelation +
  alginate Phase 2a/b/c + EDC/NHS + UQ unified + CLI v7) with 0
  regressions — the datatypes extensions did not perturb any existing
  consumers.

### Footprint

- New LOC: ~380 (solver) + ~140 (L4) + ~100 (defaults) + ~15
  (datatypes) + ~275 (tests) ≈ 910 LOC. On target for the protocol's
  Phase 1 ~900 LOC estimate.

### Still deferred (F1-b Phase 2 and 3)

- F1-b Phase 2: orchestrator `_run_cellulose` branch +
  `--polymer-family cellulose` CLI flag + `[formulation].solvent_system
  = "naoh_urea"` TOML key + 5 integration tests. ~500 LOC, 1–2
  sessions.
- F1-b Phase 3: NMMO / EMIM-Ac / DMAc/LiCl preset populations + 4
  solvent-dependence tests. ~350 LOC, 1 session.
- v7.0 release still blocked on Study A wet-lab data.

---

## v8.0.0-rc2 — Coupled GDL/CaCO₃ internal-release solver + F1-b protocol (2026-04-17)

Closes the last F1-a Phase 2c deferred item (the coupled
GDL/CaCO₃/alginate solver replacing the lumped-parameter exponential
approximation) and publishes the /architect protocol for F1-b
(cellulose NIPS), tee-ing up the next platform without committing to
implementation in this session.

### Added

- `solve_internal_gelation(params, props, *, R_droplet, C_CaCO3_0,
  L_GDL_0, k_hyd, k_diss, n_r, time, rtol, atol)` in
  `src/dpsim/level2_gelation/ionic_ca.py` — coupled ODE+PDE solver
  for homogeneous internal-release alginate gelation. State:
  - 3 spatially-uniform scalars (GDL, gluconic acid ≈ [H⁺], CaCO₃)
  - 3 radial fields (Ca²⁺, guluronate, egg-box crosslink density)
  - 6 coupled rate equations implementing GDL hydrolysis (Draget
    1997 k_hyd = 1.5 × 10⁻⁴ /s), CaCO₃ dissolution (Plummer 1978,
    Pokrovsky & Schott 2002 k_diss = 1 × 10⁻² m³/(mol·s)), and the
    existing Ca²⁺-guluronate egg-box binding.
  - No-flux outer BC (sealed droplet) + symmetry inner BC.
  - Emits SEMI_QUANTITATIVE `GelationResult` tagged
    `L2.Gelation.IonicCaInternalRelease` with `X_cov` homogeneity
    metric in diagnostics.
- `tests/test_internal_gelation.py` — 11 tests covering:
  - Schema + stoichiometric default for `L_GDL_0 = 2 × C_CaCO3_0`
  - First-order GDL hydrolysis decay (theory vs numerics within 2 %)
  - Monotone conversion
  - Zero-CaCO₃ and zero-alginate sanity
  - Ca²⁺ mass-balance under the no-flux BC
  - Homogeneity: internal-release CoV(X) < shrinking-core CoV(X) at
    matched Ca²⁺ budget and bead size (confirms the Draget 1997
    uniform-gel claim in simulation)
  - Input validation (negative R, negative CaCO₃, tiny grid)
- `docs/f1b_cellulose_nips_protocol.md` — full /architect protocol
  for the cellulose non-solvent-induced phase separation platform
  (F1-b). Includes: NIPS mechanism summary, 4-solvent parameter
  table (NaOH/urea, NMMO, EMIM-Ac, DMAc/LiCl), Cahn-Hilliard + ternary
  coupled-diffusion solver algorithm, 13 test cases, G1 gate status
  (10/12), and a 3-phase execution plan (4-6 fresh sessions total).

### Tests

- 11 new internal-gelation tests pass. 51 targeted regression
  (alginate Phase 2a + 2b + 2c + internal-release + CLI) with 0
  regressions.

### Still deferred

- **F1-b cellulose NIPS implementation** — protocol ready at
  `docs/f1b_cellulose_nips_protocol.md`; waits on fresh session(s)
  for the ~2000 LOC solver + tests.
- **F1-c PLGA solvent evaporation** — still un-scoped.
- **v7.0 release** — blocked on Study A wet-lab data.

---

## v8.0.0-rc1 — F1-a gelant preset wiring (2026-04-17)

Polish pass over v8.0.0-beta: the alginate reagent library shipped in
Phase 2c is now a first-class runtime input. Users can select a gelant
preset via `--gelant` on the CLI or `gelant = "..."` in the TOML
`[formulation]` section, and the simulator auto-wires the profile's
effective Ca²⁺ concentration into `FormulationParameters.c_Ca_bath`
using the current `t_crosslink` (static for external bath, saturating
exponential for internal release).

### Added

- `dpsim run --gelant {cacl2_external | gdl_caco3_internal}` CLI
  flag. When set, prints
  ``Gelant preset: <name> (c_Ca_bath = X mol/m³ at t_crosslink = Y s)``
  and overrides `formulation.c_Ca_bath` before the orchestrator runs.
- `[formulation].gelant = "<name>"` TOML key. Consumed by
  `load_config()` before unpacking the formulation section —
  `gelant` is a preset selector, not a persistent dataclass field.
  Unknown names raise `ValueError` with the list of available presets.
- 5 new tests in `tests/test_alginate_phase2c.py` (`TestGelantPreset`)
  covering external-bath static wiring, internal-release
  time-saturation, unknown-gelant rejection, and CLI argparse.

### Changed

- `_cmd_run` consults `GELANTS_ALGINATE` + `effective_bath_concentration`
  when `--gelant` is set, **after** `--polymer-family` has applied but
  **before** the orchestrator is instantiated.

### Tests

- 51 targeted regression pass (Phase 2c + Phase 2a/2b alginate + CLI),
  0 regressions. New Phase 2c total: 20 tests.

---

## v8.0.0-beta — F1-a Phase 2c: Alginate reagent library, TOML config, CLI (2026-04-17)

Closes the remaining three protocol §6 tests for the alginate platform
and exposes alginate as a first-class user-facing surface (CLI flag,
TOML config, reagent library). With Phase 2c in, alginate is no longer
a programmatic-API-only feature — end users can run
`python -m dpsim run --polymer-family alginate` against a TOML-defined
formulation and get the full L1 → L2-ionic-Ca → L4-Kong pipeline.

### Added

- `src/dpsim/reagent_library_alginate.py` — new
  `AlginateGelantProfile` dataclass and `GELANTS_ALGINATE` dict with two
  canonical entries:
  - **`cacl2_external`** — 100 mM CaCl₂ bath, shrinking-core mode,
    baseline for emulsification + drop-bath processes.
  - **`gdl_caco3_internal`** — glucono-δ-lactone + CaCO₃ in-situ
    release, lumped first-order release rate `k_release = 1.5e-4 s⁻¹`
    from Draget 1997.
  - `effective_bath_concentration(profile, t_end)` helper returns the
    static bath concentration for external mode and
    `C_source·(1 − exp(−k·t))` for internal mode.
- CLI `python -m dpsim run --polymer-family {agarose_chitosan |
  alginate | cellulose | plga}` flag routes `run_single` to the
  matching L2/L4 solver pair via `props_overrides={"polymer_family":
  ...}`.
- `tests/test_alginate_phase2c.py` — 15 tests covering:
  - **Protocol §6 test 3**: √t shrinking-core scaling
    (log-log slope of `X_mean` vs `t` is 0.5 ± 0.15 in the early
    diffusion-limited regime; R=1 mm, t=[10, 40, 160] s).
  - **Protocol §6 test 9**: TOML round-trip of
    `polymer_family = "alginate"` (and unknown-family rejection).
  - **Protocol §6 test 10**: L2 + L4 manifests both report
    SEMI_QUANTITATIVE when routed through the orchestrator, and
    RunReport's `min_evidence_tier` reflects that.
  - Alginate gelant library smoke (both modes, saturating release,
    unknown-mode ValueError).
  - CLI `--polymer-family alginate` argparse acceptance.

### Changed

- `src/dpsim/config.py` / `load_properties()` — accepts top-level
  scalar keys in addition to nested sections and coerces
  `polymer_family` strings to `PolymerFamily` enum members before
  constructing `MaterialProperties`. Unknown family names raise
  `ValueError` cleanly (no silent fall-through).
- `src/dpsim/__main__.py` / `_cmd_run` — `--polymer-family` override
  builds a `props_overrides` dict and passes it to
  `orchestrator.run_single`. Behaviour unchanged when the flag is
  omitted.

### Footprint

- New LOC: ~180 (reagent library) + ~20 (config) + ~15 (CLI) + ~270
  (tests) ≈ 485 LOC, within the protocol estimate for Phase 2c.
- Cumulative F1-a footprint (Phase 2a + 2b + 2c): ~1505 LOC of a
  projected ~1900 LOC; the ~400 LOC gap is cellulose-NIPS / PLGA
  scaffolding that was never in F1-a scope anyway.

### Tests

- 15 new Phase 2c tests; 115 targeted regression tests pass (alginate
  Phase 2a + 2b + 2c, EDC/NHS, UQ unified, UQ panel, inverse-design
  objectives + engine, parallel MC, CLI v7) with 0 regressions.

### Known limitations / still deferred

- Internal GDL/CaCO₃ mode uses the lumped-parameter
  `C_eff = C_source·(1 − exp(−k·t))` approximation; a fully coupled
  GDL + CaCO₃ + alginate solver is a Phase 3 follow-up if users
  request homogeneity predictions.
- Reagent library is surfaced as a module-level dict; a full
  `dpsim run --gelant cacl2_external` CLI flag that wires the
  profile into `FormulationParameters` automatically is a trivial
  v8.0-rc polish item.
- v7.0 release remains blocked on Study A wet-lab data for Node 21
  L1 PBE recalibration (unchanged from v7.0.1).

---

## v8.0.0-alpha — F1-a Phase 2b: Alginate L4 + orchestrator dispatch (2026-04-17)

Completes the functional alginate pipeline. `python`-level users can
now run a full L1 → L2 ionic-Ca → L4 Kong-2004 modulus pipeline for
alginate microspheres via `PipelineOrchestrator.run_single(params,
props_overrides={"polymer_family": PolymerFamily.ALGINATE, ...})`.

### Added

- `FormulationParameters.c_alginate` (kg/m³, default 0) +
  `FormulationParameters.c_Ca_bath` (mol/m³, default 100 mM CaCl₂).
  Zero `c_alginate` transparently falls back to the `c_agarose` slot
  for Phase 2a backward-compat.
- `src/dpsim/level4_mechanical/alginate.py` — Kong 2004 empirical
  modulus with `alginate_modulus(c, f_G, X_mean, K, n)` and
  `solve_mechanical_alginate(params, props, gelation, R_droplet=)`.
  Emits SEMI_QUANTITATIVE-tier `MechanicalResult` with
  `network_type="ionic_reinforced"` and `model_used="alginate_kong2004"`.
- `PipelineOrchestrator._run_alginate(...)` sub-pipeline: branches off
  `run_single` when `props.polymer_family == PolymerFamily.ALGINATE`.
  Skips L2a timing and L3 crosslinking (ionic gelation IS the
  crosslinking); stubs `CrosslinkingResult` to preserve the FullResult
  schema; records `polymer_family` in summary.json + RunReport
  diagnostics.
- `tests/test_alginate_l4_and_pipeline.py` — 7 tests covering:
  - `alginate_modulus` unit scaling in c² and f_G² (protocol §6 tests
    6, 7)
  - incomplete-gelation modulus reduction
  - `solve_mechanical_alginate` schema + zero-alginate edge case
  - full-pipeline orchestrator dispatch with `PolymerFamily.ALGINATE`
    (protocol §6 test 11)

### Tests

- 96/96 targeted regression tests pass in 88 s across F1-a Phase 2a/2b,
  F3 (inverse design + engine + CLI), F4-a, Node 30 / 31 / 30b, and
  the CLI contract. 0 regressions.

### Still deferred to F1-a Phase 2c / v8.0-beta

- Reagent library entries for CaCl₂ + internal GDL/CaCO₃ gelation.
- `config.py` TOML parser support for `polymer_family = "alginate"`
  (users currently set via `props_overrides` programmatically).
- The three remaining protocol §6 tests (§6 test 3 √t shrinking-core
  scaling, §6 test 9 TOML round-trip, §6 test 10 manifest-tier
  reporting from the orchestrator).
- CLI `python -m dpsim run --polymer-family alginate` surface.

### Footprint

- **Added:** ~380 LOC (L4 alginate + orchestrator branch + 7 tests) on
  top of Phase 2a's 640 LOC → cumulative F1-a footprint ~1020 LOC,
  about half of the ~1900 LOC roadmap estimate.

## v8.0.0-alpha — F1-a Phase 2a: Alginate ionic-Ca L2 solver (2026-04-17)

First non-chitosan-agarose platform lands. Shrinking-core Ca²⁺
diffusion + egg-box gelation gives DPSim its first ionic-gelation
pipeline. Downstream L3 / L4 callers remain platform-agnostic —
the solver emits a standard `GelationResult`.

### Added

- `PolymerFamily` enum in `datatypes.py`: AGAROSE_CHITOSAN (default)
  / ALGINATE / CELLULOSE / PLGA. Drives future L2 dispatch.
- `MaterialProperties.polymer_family` field + alginate-specific
  defaults (`f_guluronate=0.5`, `D_Ca=1e-9 m²/s`, `k_bind_Ca=1e3
  M⁻²·s⁻¹`, `K_alg_modulus=30 kPa`, `n_alg_modulus=2.0`). Harmless
  for other families.
- `src/dpsim/level2_gelation/ionic_ca.py::solve_ionic_ca_gelation`:
  1D spherical finite-volume BDF solver for C(r,t) / G(r,t) / X(r,t)
  with second-order Ca²⁺ + 2 guluronate → egg-box junction binding.
  ~310 LOC. Returns a SEMI_QUANTITATIVE-tier `GelationResult`.
- `tests/test_alginate_ionic_ca.py` — 13 tests covering the
  PolymerFamily enum, guluronate-concentration helper, result
  schema, guluronate mass conservation (ε < 5 %), zero-Ca /
  zero-alginate edge cases, long-time conversion > 30 % at
  500 mM bath, and input validation.

### Deferred to F1-a Phase 2b

- L4 alginate modulus (`G_DN ∝ (c·f_G)² · X_mean / X_max`).
- Reagent library entries (CaCl₂, internal gelation with GDL + CaCO₃).
- Pipeline orchestrator dispatch by `polymer_family`.
- Config TOML parser support for `polymer_family = "alginate"`.
- Remaining tests from the protocol (√t scaling, modulus scaling,
  full-pipeline integration) — 6 tests deferred.
- Replace c_agarose-slot-as-alginate-proxy with a dedicated
  `FormulationParameters.c_alginate` field.

### Tests

- 77 targeted regression tests pass (F1-a + F3 + F4 + Node 30/31 +
  CLI) in 67 s; 0 regressions.

### Footprint

- **Added:** ~640 LOC (solver + 13 tests + datatypes edits). Matches
  the Phase 2a slice of the ~1900 LOC total projected in
  `docs/f1a_alginate_protocol.md`.

## v8.0.0-alpha — F3-b/c + F4-a: engine wiring + CLI + robust BO (2026-04-17)

Completes v8.0-alpha inverse-design surface. The Node F3-a objective
builders now have an engine-level accessor, a CLI, and a first robust
acquisition stacking mean-variance on top.

### Added

- **F3-b**: `OptimizationEngine(target_spec=...)` constructor param.
  When set, the engine uses `compute_inverse_design_objectives` and
  sizes its internal `REF_POINT` + failure-penalty arrays to
  `len(target_spec.active_dims())`. The 3-objective legacy mode is
  preserved as the default.
- **F3-c**: `python -m dpsim design --d32 ... --pore ... --G-DN ...
  --Kav ...` CLI subcommand with matching `--*-tol` flags.
  TargetSpec.validate() errors route to SystemExit with a clear
  message.
- **F4-a**: `--robust-variance-weight λ` flag + engine kwarg.
  Evaluates λ resamples per candidate and reports
  `mean(obj) + λ · std(obj)` per dimension. Requires `target_spec`
  at construction (robust BO is defined against user targets).
  Current resample strategy: ±1 %·k RPM jitter as a proxy — proper
  spec-driven MC resampling lands in F4-b.
- **F4-b CVaR** — protocol stub only: swap the mean+std layer for a
  CVaR quantile over resamples. Deferred to follow-up (trivial
  change to the same engine path once the resample strategy is
  finalised).

### Tests

- `tests/test_inverse_design_engine.py` — 9 tests covering constructor
  guards, `_n_obj` sizing, robust-BO configuration validation, CLI
  parser registration, and a mocked dispatch path.
- 76 tests pass across F3 + Node 30/31/30b + CLI surfaces; 0
  regressions.

### Deferred

- **F1-a alginate platform**: protocol-only this session at
  `docs/f1a_alginate_protocol.md`. ~1900 LOC projected across L2
  ionic-Ca solver, L4 alginate modulus, PolymerFamily dispatch,
  defaults, and 11 tests. Requires /scientific-advisor briefing at
  kickoff. 3-5 fresh sessions.

## v8.0.0-alpha — Node F3-a: Inverse-design TargetSpec objectives (2026-04-17)

First v8.0 node. Adds user-specified target matching to the
optimisation pipeline so BO can be run in "inverse design" mode
(given target specs, find optimal formulation) rather than the fixed
rotor-stator / stirred-vessel targets only.

### Added

- `TargetSpec` dataclass in `src/dpsim/optimization/objectives.py`:
  per-dimension target + tolerance pairs for d32 (or d_mode in
  stirred-vessel), pore size, G_DN (log10-distance), and Kav (M3
  distribution coefficient, optional). Dimensions are skipped when
  either the target or the tolerance is `None`, so users can target
  subsets. `TargetSpec.validate()` raises on empty spec or
  non-positive tolerance.
- `compute_inverse_design_objectives(result, target, trust_aware=True,
  mode=None)`: returns an objective vector sized to the active
  dimensions. Each component is the tolerance-normalised absolute
  distance (log10 for G_DN); trust penalty from Node 6 is added
  per-component when `trust_aware=True` so weak-evidence candidates
  still land above the engine REF_POINT.
- 12 unit tests in `tests/test_inverse_design_objectives.py` covering
  validate(), active_dims(), per-dimension distance math, trust
  penalty integration, Kav-missing fallback (inf), and stirred-vessel
  d_mode substitution.

### Not yet done (F3-b, F3-c)

- `OptimizationEngine.run(target_spec=...)` integration — the engine
  currently hard-wires `compute_objectives_trust_aware`. Switching the
  objective at runtime requires an engine-level accessor.
- CLI `python -m dpsim design --d32 2e-6 --pore 80e-9 ...` — wraps
  the above into a user surface.

### Footprint

- **Added:** ~200 LOC (TargetSpec + compute_inverse_design_objectives
  + tests). 67 tests across F3-a + UQ + EDC/NHS + panel + CLI pass;
  0 regressions.

## v7.1.0-dev — Node 32: Cluster F v8.0 roadmap (2026-04-17)

Architect-produced roadmap document (no code) at
`docs/node32_cluster_f_v8_roadmap.md`. Refines Doc 10 §4 into Node-level
deliverables for v8.0:

- **F1** Other microsphere platforms (alginate / cellulose NIPS /
  PLGA; alginate recommended first per smallest code delta)
- **F2** Digital twin (EnKF + online Bayesian + MPC; scoped to
  replay-only for v8.0 unless hardware partner emerges)
- **F3** Inverse design (constrained BO; leverages Node 30 UQ +
  Node 6 trust-aware evidence)
- **F4** Robust optimisation under uncertainty (mean-variance /
  CVaR acquisition stacked on F3)
- **F5** MD parameter estimation (MARTINI CG MD for χ, κ, M₀,
  f_bridge; ingest-only default scope)

Proposed v8.0 phasing:

1. Phase 1 (4 weeks): F3 + F4 — inverse design + robust optimisation
   on current platform; v8.0-alpha release.
2. Phase 2 (6 weeks): F1-a alginate; v8.0-beta.
3. Phase 3 (6 weeks): F5 ingest + F2 replay harness; v8.0 GA.

Hard entry criteria: v7.0 must ship (Study A wet-lab gate); CEO /
chief-economist / ip-auditor sign-off on commercial prioritisation
before first v8.0 node.

## v7.1.0-dev — Node 30b: Streamlit UQ panel migration (2026-04-17)

Closes the Node 30 deferral: the streamlit uncertainty panel now
builds a full `UnifiedUncertaintySpec` from user inputs instead of
showing an `st.info` placeholder. The built-in MaterialProperties
perturbations from `UnifiedUncertaintyEngine.run_m1l4` remain always-on;
the panel configures the *additional* spec-driven surface plus sampling
controls and surfaces a count of calibration-posterior sources that
will be absorbed from `st.session_state["_cal_store"]` at engine
construction time.

### Added

- `build_uncertainty_spec(n_samples, seed, custom_sources) ->
  UnifiedUncertaintySpec` — pure helper used by the panel. Invalid
  custom entries (blank name, std <= 0) are silently dropped;
  `n_samples < 1` raises.
- `count_store_posteriors(store) -> int` — tallies calibration entries
  with `posterior_uncertainty > 0` for the panel's status display.
- `CustomSourceInput` dataclass — typed bridge between streamlit
  widget state and the pure spec-builder.
- `tests/test_uncertainty_panel.py` — 12 unit tests of the spec
  builder, the posterior counter, and a panel-export smoke test.

### Changed

- `src/dpsim/visualization/panels/uncertainty.py` — rebuilt around
  the new helpers. UI exposes `n_samples`, `seed`, `n_jobs` (`1`, `2`,
  `4`, `-1`) in a three-column row plus an "Advanced" expander that
  lets the user add up to 10 custom `UncertaintySource` entries
  (name, kind, distribution `normal`/`lognormal`, value, std).
- Session-state surface: the panel persists the built spec at
  `st.session_state["_unc_spec"]` and the parallel-workers value at
  `st.session_state["_unc_n_jobs"]` for downstream run triggers.

### Tests

- 12 new panel tests pass.
- 146 tests across panel + UQ + EDC/NHS + CLI + UI contract surfaces
  pass; 0 regressions.

### Footprint

- **Added:** ~220 LOC (panel rewrite + tests). Net: −28 LOC was the
  placeholder; the migrated panel is ~190 LOC.

## v7.1.0-dev — Node 31: EDC/NHS mechanistic kinetic (2026-04-17)

Promotes EDC/NHS carbodiimide chemistry from QUALITATIVE_TREND
(Node 9 F9 fallback) to SEMI_QUANTITATIVE with a literature-grounded
two-step ODE model. The Hermanson 2013 / Wang 2011 / Cline & Hanna
1988 rate constants close the scientific debt item; Study A calibration
data can promote to QUANTITATIVE via the CalibrationStore posterior
machinery shipped in Node 30.

### Added

- `src/dpsim/module2_functionalization/edc_nhs_kinetics.py` — new
  mechanistic solver. Core: `react_edc_nhs_two_step(...)` integrates
  four ODEs (C → A → E → P) with competing O-acylisourea and
  NHS-ester hydrolyses, returning a structured `EdcNhsResult` with
  `p_final`, `p_hydrolysed`, `p_residual_nhs_ester`, `time_to_half`,
  mass-balance diagnostic, and solver diagnostics. `EdcNhsKinetics`
  dataclass carries the rate constants + activation energies; defaults
  are literature medians at T_ref=298 K. `available_amine_fraction(pH,
  pKa)` helper for chitosan amine speciation.
- `FormulationParameters.pH` field (default 7.0).
- `MaterialProperties.surface_cooh_concentration` field (default 0.0)
  — gates L3 EDC/NHS to run the mechanistic path when non-zero.
- `tests/test_edc_nhs_kinetics.py` — 18 tests covering mass
  conservation, edge cases, Arrhenius / pH / dose-response trends,
  input validation, and M2 + L3 integration.

### Changed

- `src/dpsim/module2_functionalization/modification_steps.py` —
  `_solve_activation_step` dispatches to the mechanistic ODE when
  `reagent_profile.chemistry_class == "edc_nhs"` (was generic
  single-step `solve_second_order_consumption`).
- `src/dpsim/module2_functionalization/reagent_profiles.py` — the
  `edc_nhs_activation` profile's `confidence_tier` promotes from
  `ranking_only` to `semi_quantitative`; `calibration_source` and
  `notes` updated to reference the mechanistic model.
- `src/dpsim/level3_crosslinking/solver.py` — the `michaelis_menten`
  branch now gates on `props.surface_cooh_concentration`. Native matrix
  (= 0) still falls back with QUALITATIVE_TREND (v7.0.1 behaviour
  preserved for safety); carboxylated matrix (> 0) runs the mechanistic
  ODE and ships SEMI_QUANTITATIVE.

### Kept deferred

- Dedicated `c_edc` / `c_nhs` concentration fields on
  `FormulationParameters` (Node 31 reuses `c_genipin`; cleanup = Node
  31b).
- pH-dependent kinetic constants beyond the k_h2 pH term (Node 31b).
- Study A calibration uptake for EDC/NHS-specific matrix chemistry
  (will arrive as `CalibrationStore` entries targeting M2 / L3).

### Tests

- 18 new EDC/NHS tests pass in <1 s.
- 157 tests across the EDC/NHS + UQ + CLI + M2 + L3 + batch +
  run-context surfaces pass in ≈38 s; 0 regressions.

### Footprint

- **Added:** ~420 LOC (solver + tests + L3 gate + M2 dispatch branch).
- **Touched:** 6 files.

## v7.1.0-dev — Node 30: Full UQ merge (2026-04-17)

Consolidates the two legacy Monte Carlo engines into a single
`UnifiedUncertaintyEngine` implementation and closes the Audit N2
calibration-posterior sampling gap left open by Node 18.

### Merged

- `uncertainty_core.py` (318 LOC) — deleted. The M1-L4
  `UncertaintyPropagator` logic lives in `uncertainty_unified.py`.
- `uncertainty_propagation/` package (216 LOC) — deleted. The M2-only
  `M1UncertaintyContract` / `run_with_uncertainty` path had no CLI
  surface and was unreachable outside the streamlit panel + two
  v6.0-era integration tests. An M2-specific UQ path can be rebuilt on
  top of the unified schema in v7.2 if user demand warrants it.
- `UnifiedUncertaintyEngine.run_m2_q_max`, `from_m1_contract_uq`,
  `from_m1l4_result` — deleted (dead adapters).

### Closed

- **Audit N2** (HIGH): `CalibrationStore` posteriors with
  `posterior_uncertainty > 0` now actually perturb the MC on each
  sample. The posterior draw is dispatched by `target_module` — L1
  posteriors land on `params.emulsification.kernels` (lazily
  instantiated if `None`), L2-L4/M2-M3 posteriors land on
  `MaterialProperties`. `result.kinds_sampled` honestly records
  `CALIBRATION_POSTERIOR` when a posterior dispatched to a real
  attribute; `result.kinds_declared_but_not_sampled` only contains
  `CALIBRATION_POSTERIOR` when EVERY posterior failed the dispatch
  (malformed name or unknown attribute).

### CLI

- `python -m dpsim uncertainty --engine {unified,legacy}` now routes
  both choices through the merged engine. `unified` includes
  posteriors; `legacy` runs with `calibration_store=None` for
  byte-compat with v7.0.x scripts that expected only the default
  MaterialProperties perturbations. The output schema is the unified
  summary in both cases — scripts parsing the legacy
  "Uncertainty-Quantified Results" header must migrate.

### Byte-compat

- `_generate_default_perturbations` preserves the exact RNG call order
  of v7.0.1 `UncertaintyPropagator._generate_perturbations`, so
  seed-identical output matches when no posterior sources are declared.
  Posterior draws come AFTER the default 10 draws per sample to avoid
  perturbing the default-only sequence.

### Deferred to Node 30b

- Streamlit UQ panel
  (`src/dpsim/visualization/panels/uncertainty.py`) now displays an
  info placeholder and returns `None`. Full migration to build a
  `UnifiedUncertaintySpec` from streamlit inputs is Node 30b. The CLI
  and programmatic API paths are fully functional in v7.1.

### Tests

- `tests/test_uncertainty_unified.py`: 14 tests. Rewrote the Node 23
  `test_n2_no_posterior_overclaim` as `test_posterior_now_actually_sampled`
  and `test_posterior_actually_perturbs_output` to verify the closure.
  Added `test_unknown_posterior_attribute_skipped` and
  `test_legacy_modules_are_gone`.
- `tests/test_parallel_mc.py`: 4 tests retargeted at the merged
  engine; parallel/serial bit-identicality invariant preserved via the
  new `OutputUncertainty.raw_samples` field.
- `tests/test_cli_v7.py::test_legacy_engine_byte_compat` → rewritten
  as `test_legacy_engine_flag_routes_through_unified`.
- `tests/test_v60_integration.py::TestUncertaintyIntegration` deleted
  (M2 MC path removed).

### Footprint

- **Deleted:** ~540 LOC (uncertainty_core.py + uncertainty_propagation/
  + dead adapters in uncertainty_unified.py).
- **Added:** ~200 LOC (merged sampler + posterior dispatch in
  uncertainty_unified.py, 5 new UQ tests).
- **Net:** ~−340 LOC. 52 tests passing in the targeted regression set
  (UQ + parallel + CLI + v6.0 integration + batch + run-context).

## v7.0.1 (2026-04-17) — Audit remediation patch

Closes 8 of 10 findings from the post-Nodes-1-20 full-system audit. P0
ship-blockers fixed; v7.0 features now reachable from the CLI.

### P0 fixes (release blockers)
- **N1 (HIGH)** — `pipeline/orchestrator.py` no longer mutates the caller's
  `params.emulsification.kernels` in place when applying L1 calibration.
  Callers that reuse a `SimulationParameters` instance across multiple
  `run_single` calls (e.g. `batch_variability.run_batch`, parameter
  sweeps, optimisation campaigns) no longer see calibrated kernels leak
  between iterations. Regression test in `test_run_context.py`.
- **N2 (HIGH)** — `UnifiedUncertaintyEngine.run_m1l4` no longer claims to
  have sampled `CALIBRATION_POSTERIOR` when it has only absorbed the
  posterior into the spec. The new
  `UnifiedUncertaintyResult.kinds_declared_but_not_sampled` field
  records the v7.0 limitation honestly.

### P1 fixes (CLI surface — closes audit N4 + N5)
- **`python -m dpsim batch`** — surface
  `pipeline.batch_variability.run_batch` on the CLI. Pass `--quantiles`
  and `--output`; prints mass-weighted mean / per-quantile percentile
  table.
- **`python -m dpsim dossier`** — run the pipeline and emit a
  `ProcessDossier` JSON artifact for reproducibility. Records inputs,
  result summary, manifests, calibrations, environment.
- **`python -m dpsim ingest L1`** — ingest a directory of
  `AssayRecord` JSON files, run the L1 fitter, write a
  `CalibrationStore`-loadable fit JSON. v7.1 will add L2/L3/L4/M2.
- **`python -m dpsim uncertainty`** now defaults to the
  `UnifiedUncertaintyEngine` (Node 18) and exposes `--n-jobs` for
  Node 15's parallel MC. Pass `--engine legacy` for v6.x byte-equivalent
  output.
- **N3 follow-up** — `QuantileRun.representative_diameter_m` property
  added so downstream consumers don't accidentally read
  `full_result.emulsification.d50` (which is shared by reference across
  all per-quantile runs and reflects the BASE L1 DSD).

### P2 polish
- **N7** — `UncertaintyPropagator.run` auto-falls-back to serial when
  `n_samples < 4 × |n_jobs|`. Joblib startup + Numba JIT cold-compile
  dominate below this threshold.
- **N8** — `run_batch` silently sort+dedupes the `quantiles` argument.
  Duplicate or unsorted input no longer produces ill-defined mass
  fractions.

### P3 documentation
- **N6** — `INSTALL.md` documents the Numba JIT cache location and the
  `NUMBA_CACHE_DIR` environment-variable workaround for read-only
  Python installs (corporate, conda `--no-write-pkgs`,
  `pip install --user` on network shares).
- **N9** — Documenting that Node 8's L2 timing wiring was a metadata
  fix only; the empirical pore-size formula remains independent of
  `alpha_final`. The `model_manifest.diagnostics.alpha_final_from_timing`
  field now reflects the actual Avrami output instead of a hardcoded
  0.999, but pore predictions at typical conditions are unchanged.

### Tests
- 25 new tests across the patch (Nodes 22-29). 0 regressions.

---

## v7.0 (2026-04-17) — Engineering portion (Nodes 14-20)

Closes engineering items from the consensus v7.0 plan (doc 34 §9). F1
closure (kernel re-fit) remains gated on Study A wet-lab data.

### New modules
- `process_dossier.py` — `ProcessDossier` aggregator + JSON export
- `assay_record.py` — `AssayRecord` public data model with 12 `AssayKind` values
- `uncertainty_unified.py` — `UnifiedUncertaintyEngine` single entrypoint
- `pipeline/batch_variability.py` — `run_batch` over DSD quantiles
- `calibration/fitters.py` — stub L1 DSD fitter

### Performance
- Numba JIT for `breakage_rate_alopaeus`, `breakage_rate_coulaloglou`,
  `coalescence_rate_ct` matrix builder (5-10× on coalescence; matches
  NumPy to 1e-12 rtol).
- joblib parallel MC via `UncertaintyPropagator(n_jobs=-1)`.

### Calibration data scaffold
- `data/validation/{l1_dsd,l2_pore,l3_kinetics,l4_mechanics,m2_capacity}/`
  directory tree with JSON-Schema for L1 DSD assays.

---

## v6.0 (2026-04-12) — Calibration-Enabled Process Simulation

Transitions DPSim from semi-quantitative chemistry simulator to calibration-enabled process simulation platform. All uncalibrated outputs remain semi-quantitative; calibrated outputs reflect user-supplied measurements.

### UI Restructure
- Split monolithic `app.py` (1480 lines) into modular tab architecture (7 UI files, orchestrator < 210 lines)
- `tabs/tab_m1.py`: M1 Fabrication tab (inputs, run, results, optimization, trust)
- `tabs/tab_m2.py`: M2 Functionalization tab (9 step types, 52 reagent profiles)
- `tabs/tab_m3.py`: M3 Performance tab (chromatography + catalysis)
- Sidebar panels for calibration, uncertainty, and lifetime frameworks

### Gradient-Aware LRM (H6)
- `solve_lrm()` accepts time-varying `ProcessState` via `gradient_program` + `equilibrium_adapter`
- Gradient values now mechanistically affect equilibrium during LRM time integration
- `run_gradient_elution()` auto-creates adapter for gradient-sensitive isotherms
- `gradient_sensitive` + `gradient_field` properties on SMA, HIC, IMAC, ProteinA, CompetitiveAffinity isotherms
- Fully backward compatible: existing callers unchanged

### Calibration Framework (v6.0-alpha)
- `CalibrationEntry` typed dataclass with units, target, validity domain (audit F2)
- `CalibrationStore` with JSON import/export, query, and `apply_to_fmc()` (audit F13)
- UI panel: JSON upload, manual entry, color-coded confidence display

### Uncertainty Propagation (v6.0-alpha)
- `M1UncertaintyContract` with 5 CVs and two tiers: measured (Tier 1) vs assumed (Tier 2, audit F4)
- `run_with_uncertainty()` Monte Carlo through M2 pipeline producing p5/p95 bounds on q_max
- UI panel: CV sliders, tier selection, sample count configuration

### Lifetime Projection (v6.0-rc)
- `LifetimeProjection` empirical first-order deactivation model (audit F6)
- `project_lifetime()` with cycles-to-80%/50% milestones
- UI panel: interactive Plotly decay curve, empirical confidence warning

### ProcessState (v6.0-beta)
- Typed `ProcessState` dataclass replacing loose dict for process conditions
- Carries salt, pH, imidazole, sugar competitor, temperature for multi-parameter isotherms
- `EquilibriumAdapter` dispatches by isotherm class name with ProcessState routing

### New Isotherms
- `HICIsotherm`: Salt-modulated Langmuir (K_eff = K_0 * exp(m * C_salt)), requires user calibration
- `CompetitiveAffinityIsotherm`: Generalized competitive binding for lectin elution (Con A, WGA)

### Quality
- 14/14 acceptance criteria from audit Section 7 verified passing
- 24 new integration tests (12 gradient LRM + 12 v6.0 end-to-end)
- All existing v5.9 workflows pass regression (280+ total tests, 0 failures)

---

## v0.1.0 (2026-03-26) — Initial Release

### Simulation Pipeline
- 4-level sequential pipeline: PBE emulsification → empirical gelation → multi-mechanism crosslinking → IPN mechanical properties
- 8 crosslinkers with 4 kinetics models (second-order amine/hydroxyl, UV dose, ionic instant)
- 6 surfactants with Szyszkowski-Langmuir IFT model
- Empirical pore-size model calibrated to literature (Pernodet 1997, Chen 2017)
- 2D Cahn-Hilliard phase-field solver available as advanced option

### Web UI (Streamlit)
- Interactive parameter input with sliders and dropdowns
- Reagent selection (crosslinker + surfactant) with per-reagent defaults
- Per-constant Literature/Custom toggle with calibration protocol links
- Results dashboard with Plotly charts (size distribution, phase field, kinetics, Hertz, Kav)
- Trust assessment with 10 automated reliability checks
- Optimization assessment with actionable recommendations

### CLI
- `python -m dpsim run` — full pipeline
- `python -m dpsim sweep` — RPM parameter sweep
- `python -m dpsim optimize` — BoTorch Bayesian optimization
- `python -m dpsim uncertainty` — Monte Carlo uncertainty propagation
- `python -m dpsim ui` — launch Streamlit web interface
- `python -m dpsim info` — display parameters and properties

### Documentation
- Scientific advisory report (docs/01)
- Computational architecture (docs/02)
- Scientific review with formula verification (docs/03)
- Calibration wet-lab protocol — 5 studies, 1081 lines (docs/04)
- Literature constants database with sources and DOIs
- Reagent library with 8 crosslinkers and 6 surfactants

### Quality Assurance
- 9 rounds of Codex (OpenAI) adversarial review — 63+ findings, all addressed
- Scientific Advisor review — 4 critical bugs fixed
- Dev-Orchestrator usability review — all priorities implemented
- Input validation, trust gates, uncertainty propagation
- 107+ unit tests
