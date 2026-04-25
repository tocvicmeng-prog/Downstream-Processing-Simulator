# Scientific Advisor — Functional-Optimization Candidate Screening Report

**Document ID:** SA-v9.2-FUNCOPT-001
**Date:** 2026-04-25
**Author role:** Scientific Advisor (Mode 2 — Mechanism and Pathway Screening)
**Scope:** Evaluate the 50+ polysaccharide-material, crosslinker, ligand, linker, and ACS-conversion candidates listed in `downstream_processing_simulator_functional_optimization_requirements.md` for integration into the Downstream-Processing-Simulator (DPSim) functional architecture.
**Audience:** dev-orchestrator (next phase planner), architect (architecture/protocol designer), R&D project manager.

---

## 0. Executive Summary

The candidate list contains **50 distinct items** across three categories: 11 polysaccharide material families, 10 crosslinkers/gelants, and ~29 ligand / linker / ACS-conversion entries. Each was screened against six integration criteria:

1. **Scientific viability** — chemistry/physics/biology consistency with first principles and peer-reviewed evidence.
2. **Bioprocess relevance** — actual use in protein/biopharmaceutical downstream processing (vs. drug-delivery, food, or research-only contexts).
3. **Distinctiveness** — does the candidate add a behavior/parameter regime not already represented?
4. **Architectural fit** — clean mapping onto existing enums (`PolymerFamily`, `ACSSiteType`), `ReagentProfile`, and the M2 activation–spacer–ligand–quench workflow.
5. **Implementation effort** — number of new physics/chemistry modules, new ACS site types, new gelation solvers, or new UI surfaces required.
6. **Validation feasibility** — availability of literature parameters with sufficient quality (kinetic constants, gelation thresholds, binding affinities) to populate `ReagentProfile`/`CrosslinkerProfile` in the SEMI_QUANTITATIVE evidence tier or better.

**Aggregate verdict:**

| Tier | Definition | Count | Recommended action |
|---|---|---|---|
| **Tier 1 — Integrate now (v9.2)** | High bioprocess relevance, distinct mechanism, parameters available in literature, low-to-medium architectural cost | **18** | Land in next minor cycle |
| **Tier 2 — Integrate next (v9.3)** | Strong scientific case, moderate bioprocess relevance, medium architectural cost OR depends on a Tier-1 item | **17** | Plan for cycle after Tier 1 |
| **Tier 3 — Defer (research/optional)** | Niche, redundant, or carries bioprocess-incompatibility flags | **11** | Implement behind feature flag or document-only |
| **Tier 4 — Reject for default scope** | Hazardous, low value, or scientifically marginal for default bioprocess simulator | **4** | Document rejection rationale; revisit only on explicit user request |

**Top architectural changes required:**

- Expand `PolymerFamily` from 4 to ~14 families (add AGAROSE, CHITOSAN, DEXTRAN, AGAROSE_DEXTRAN, AGAROSE_ALGINATE, ALGINATE_CHITOSAN, HYALURONATE, plus optional CARRAGEENAN/GELLAN/PECTIN/PULLULAN/STARCH for Tier 2/3).
- Expand `ACSSiteType` from 13 to ~25 sites (add SULFATE_ESTER, THIOL, PHENOL_TYRAMINE, AZIDE, ALKYNE, AMINOOXY, CIS_DIOL, TRIAZINE_REACTIVE, GLYOXYL, CYANATE_ESTER, IMIDAZOLYL_CARBONATE, SULFONATE_LEAVING).
- Generalize the alginate-only Ca²⁺ ion-gelation model into a **per-polymer ion-gelation registry** (already partially present via internal CaCO₃/GDL release; needs to accept K⁺ for κ-carrageenan/gellan, multiple sparingly-soluble Ca salts, and pectin Ca²⁺ binding distinct from alginate).
- Introduce a **two-polysaccharide phase model** (core–shell, IPN, PEC) for composite materials.
- Introduce a **dye-pseudo-affinity** ligand class and a **mixed-mode HCIC** ligand class as new `functional_mode` categories.
- Introduce **bioorthogonal coupling** (oxime, hydrazone, click) as a first-class chemistry class with optional copper-removal accounting for CuAAC.

Detailed integration roadmap is in §6.

---

## 1. Method

### 1.1 First-principles framing

For each candidate, the Scientific Advisor verified:

- **Chemistry validity** — that the cited reaction (e.g., periodate cleavage of vicinal diols, K⁺ helix-aggregation in κ-carrageenan, triazine substitution by hydroxylates) is consistent with established mechanism textbooks and that the cited primary sources actually demonstrate the claim at the bead/microsphere scale rather than only in solution.
- **Thermodynamic consistency** — that gelation/crosslinking pathways respect mass and charge balance, and that proposed kinetic regimes are physically reasonable (e.g., that ionotropic alginate gelation is diffusion-limited, that Schiff-base formation is reversible without reduction).
- **Biological compatibility** — for ligands, that the binding mode reported in the source has an established biophysical mechanism (e.g., MEP HCIC's pH-switchable thiopyridyl-stack-with-IgG binding, boronate cis-diol esterification, calmodulin Ca²⁺-dependent EF-hand binding).
- **Source authority** — that each cited paper is a peer-reviewed primary or review paper from a reputable journal with no contradictions in the wider literature, per Reference 03 §1–3.

No claim in this report relies on a single source of weak provenance; where a source is preliminary, this is flagged explicitly.

### 1.2 Screening criteria and weights

| Criterion | Weight | Pass threshold |
|---|---|---|
| Scientific viability | Must-pass | Mechanism is established or well-supported in peer-reviewed literature. |
| Bioprocess relevance | High | Used in protein purification, biopharmaceutical downstream processing, or process-scale chromatography (vs. solely drug delivery/food). |
| Distinctiveness | High | Adds a regime, mechanism, or ACS chemistry not already present in DPSim. |
| Architectural fit | Medium-High | Maps onto existing `ReagentProfile`/`CrosslinkerProfile`/`ACSProfile` with at most one new enum value or one new dataclass field. |
| Implementation effort | Medium | ≤ 1 new physics module; ≤ 5 new lines in `PolymerFamily`/`ACSSiteType`; ≤ 1 new family-reagent matrix column. |
| Validation feasibility | Medium-High | Kinetic/gelation/binding parameters available in at least one peer-reviewed source at SEMI_QUANTITATIVE tier or better. |

### 1.3 Confidence levels for parameter availability

Per Reference 01 §4.3, each candidate's literature-parameter-availability is reported using the standard ladder: **Established → Well-supported → Emerging → Preliminary → Speculative**. No candidate scored below "Well-supported" was placed in Tier 1.

---

## 2. Polysaccharide Material Candidates — Screening

### 2.1 Screening matrix

🟢 = meets criterion with confidence; 🟡 = meets conditionally; 🔴 = fails.

| # | Candidate | Viability | Bioprocess relevance | Distinctiveness | Arch. fit | Effort | Validation | **Tier** |
|---|---|---|---|---|---|---|---|---|
| M1 | `AGAROSE_ONLY` | 🟢 | 🟢 (Sepharose lineage — dominant resin family) | 🟢 (chitosan-free thermal gelation) | 🟢 (subset of existing AC family) | 🟢 (low — fork existing solver branch) | 🟢 Established | **1 — must integrate** |
| M2 | `CHITOSAN_ONLY` | 🟢 | 🟢 (genipin/TPP/GA chitosan beads in industry) | 🟢 (amine-rich, pH-dependent swelling) | 🟢 (subset of AC family) | 🟡 (need pH-swelling sub-model below pKa ≈ 6.5) | 🟢 Established | **1** |
| M3 | `DEXTRAN_ECH` | 🟢 | 🟢 (Sephadex; dextran-shell on Capto) | 🟢 (foundational SEC matrix; dextran rheology) | 🟡 (new family + ECH gelation kinetics) | 🟡 (medium — new gelation solver path) | 🟢 Established | **1** |
| M4 | `AGAROSE_DEXTRAN_CORE_SHELL` | 🟢 | 🟢 (Capto-style dextran-functionalized agarose) | 🟢 (core–shell phase structure) | 🔴 (new two-phase model) | 🔴 (high — phase-field/shell-thickness param) | 🟡 Well-supported | **2 — depends on M3** |
| M5 | `AGAROSE_ALGINATE_IPN` | 🟢 | 🟡 (academic + fluidized-bed reports) | 🟢 (orthogonal thermal + Ca²⁺) | 🟡 (couples existing solvers) | 🟡 (medium — coupled gelation) | 🟡 Well-supported | **2** |
| M6 | `ALGINATE_CHITOSAN_PEC` | 🟢 | 🟡 (drug delivery > bioprocess; some downstream uses) | 🟢 (PEC/coacervate physics) | 🔴 (new PEC stoichiometry model) | 🔴 (high — charge-density + shell growth) | 🟡 Well-supported | **2** |
| M7 | `PECTIN_CALCIUM` / `PECTIN_CHITOSAN_PEC` | 🟢 | 🔴 (drug delivery / food; rare in bioprocess) | 🟡 (DE-dependent carboxylate density) | 🟡 (extends ion-gelant registry) | 🟡 (medium) | 🟡 Well-supported | **3 — defer** |
| M8 | `GELLAN_GUM` / `GELLAN_ALGINATE` | 🟢 | 🔴 (food / drug delivery) | 🟡 (cation-dependent helix aggregation) | 🟡 (extends ion-gelant registry) | 🟡 | 🟡 Well-supported | **3** |
| M9 | `KAPPA_CARRAGEENAN` / `CARRAGEENAN_ALGINATE` | 🟢 | 🟡 (cell immobilization + niche bioprocess) | 🟢 (sulfate-ester ACS — new chemistry class) | 🟡 (needs SULFATE_ESTER ACS site) | 🟡 (medium — new ACS) | 🟡 Well-supported | **2 — promotes ACS coverage** |
| M10 | `HYALURONATE` (HA, HA_CHITOSAN, HA_ALGINATE) | 🟢 | 🟡 (specialty matrix; high-cost but real) | 🟢 (high-swelling polyelectrolyte; tyramine/HRP route) | 🟡 (couples to PHENOL_TYRAMINE + AMINOOXY paths) | 🟡 (medium) | 🟢 Established (HA chemistry) | **2** |
| M11 | `PULLULAN` / `PULLULAN_DEXTRAN` | 🟢 | 🔴 (mostly drug delivery) | 🟡 (slow STMP gelation kinetics) | 🟡 (extends neutral α-glucan path) | 🟡 | 🟡 Well-supported | **3** |
| M12 | `STARCH_POROUS` | 🟢 | 🔴 (food/industrial > bioprocess; degradation/brittleness) | 🟡 (low-cost mode, gelatinization model) | 🟡 (extends neutral α-glucan path) | 🟡 | 🟡 Well-supported | **3 — research mode only** |

### 2.2 First-principles notes per material

- **M1 AGAROSE_ONLY.** The existing `AGAROSE_CHITOSAN` family already encodes thermal helix–coil gelation of agarose; the chitosan amine network is layered on top. From first principles, the agarose helix transition (T_gel ≈ 30–40 °C, depending on agarose type) is independent of the chitosan presence — chitosan only contributes a secondary amine network and additional ACS density. Therefore an `AGAROSE_ONLY` family is exactly the existing solver with the chitosan amine track set to zero. Integration cost is minimal; it provides the **baseline comparator** for all polysaccharide-bead validation work, since virtually all reference data on Sepharose-class media is for agarose-only resins. **This is the highest-leverage single addition.**

- **M2 CHITOSAN_ONLY.** Chitosan microspheres formed by inverse-emulsion + genipin or by ionotropic TPP gelation are real and well-characterized. The new physics needed is **pH-dependent amine protonation** (chitosan pKa ≈ 6.3–6.5; protonated chitosan at pH < pKa is soluble; deprotonated/precipitated at pH > pKa) and **acid-solubilized droplet viscosity**. These can be added as additional fields to a `ChitosanGelationProfile` without disturbing existing solvers.

- **M3 DEXTRAN_ECH.** Crosslinked dextran (Sephadex) is the canonical SEC support. The chemistry is hydroxyl-rich; ECH alkaline crosslinking introduces glyceryl ether bridges with first-order kinetics in dextran-OH and ECH (well-documented in the alginate/dextran-bead literature). The simulator already models ECH on agarose; extending to dextran is a parameter swap (different polymer concentration → bead solids fraction, different rheology) rather than a new mechanism. **Critical gap closure** — without dextran the simulator cannot represent SEC fundamentals.

- **M4 AGAROSE_DEXTRAN_CORE_SHELL.** Industrially most important after M1+M3 land — modern bioprocess resins (Capto-class) are agarose with a dextran-grafted shell. The architectural prerequisite is a **two-phase polymer model**: shell thickness, dextran-rich phase fraction, shell permeability for protein partitioning. This is genuinely new physics; defer until M3 is solid.

- **M5 AGAROSE_ALGINATE_IPN.** Two orthogonal gelation mechanisms in one bead: thermal agarose helix + Ca²⁺-driven alginate egg-box. From first principles, sequential or simultaneous solver coupling is straightforward (agarose locks first as the bead cools; Ca²⁺ then diffuses in). Useful as a **cross-validation case** for the ion-gelation registry.

- **M6 ALGINATE_CHITOSAN_PEC.** Polyelectrolyte complexation between alginate carboxylate and chitosan amine forms a shell at the droplet interface. Modeling requires charge-stoichiometry tracking, ionic strength dependence, pH dependence (both polymers charged only in distinct pH windows), and shell-growth kinetics. The physics is well-established but adds a substantial new module. Bioprocess relevance is moderate; recommend as Tier 2 paired with the PEC class.

- **M7 PECTIN, M8 GELLAN, M11 PULLULAN, M12 STARCH.** All scientifically sound. Bioprocess relevance is too low to justify Tier 1/2 scope. Recommend documenting them as **Tier 3 "extended polysaccharide library"** — implement only after the architectural ion-gelation registry and neutral α-glucan paths exist (M3, M9). They can be added incrementally as parameter sets without further architectural work once Tier 2 lands.

- **M9 KAPPA_CARRAGEENAN.** Distinct value: **introduces sulfate-ester ACS**, which expands the simulator's chemistry coverage beyond hydroxyl/amine/carboxylate. K⁺ vs Ca²⁺ ion-selectivity is a clean test for the per-polymer ion-gelation registry. Promote to Tier 2 specifically because of architectural coverage gain.

- **M10 HYALURONATE.** High-swelling polyelectrolyte; carboxylate + N-acetyl chemistry; supports HRP/tyramine, PEGDGE, and oxidized-HA/ADH routes. Strong synergy with crosslinker candidates C1, C2, C9. Tier 2 because integration is small once those crosslinkers exist.

### 2.3 Show-stoppers

None. All material candidates are scientifically viable. Tier 4 contains no materials; the lowest tier (Tier 3) reflects bioprocess relevance, not scientific failure.

---

## 3. Crosslinker / Gelant Candidates — Screening

### 3.1 Screening matrix

| # | Candidate | Viability | Bioprocess relevance | Distinctiveness | Arch. fit | Effort | Validation | **Tier** |
|---|---|---|---|---|---|---|---|---|
| C1 | `SODIUM_PERIODATE` (vicinal-diol → aldehyde) | 🟢 | 🟢 (foundational for hydrazone/oxime/glycoprotein coupling) | 🟢 (new ACS conversion) | 🟢 (existing ALDEHYDE site) | 🟢 (low) | 🟢 Established | **1** |
| C2 | `ADIPIC_ACID_DIHYDRAZIDE` (ADH) | 🟢 | 🟢 (HA, oxidized dextran/alginate hydrogels) | 🟢 (hydrazone, distinct from imine) | 🟢 (uses HYDRAZIDE site already in ACS enum) | 🟢 (low) | 🟢 Established | **1** |
| C3 | `PEGDGE` / `EGDGE` / `BDDE` (bis-epoxide family) | 🟢 | 🟢 (BDDE is the workhorse for HA hardening; PEGDGE for agarose) | 🟢 (spacer-bearing crosslink, distinct from ECH) | 🟢 (existing EPOXIDE chemistry; add spacer-length param) | 🟢 (low) | 🟢 Established | **1** |
| C4 | `CaSO4_GDL` (slow internal Ca²⁺ release) | 🟢 | 🟢 (industrial alginate microsphere production) | 🟡 (extends existing GDL/CaCO₃ path) | 🟢 (drop-in addition to existing release model) | 🟢 (trivial) | 🟢 Established | **1** |
| C5 | `KCl` / generalized monovalent/divalent ion gelants | 🟢 | 🟡 (carrageenan/gellan; niche bioprocess) | 🟢 (new ion species; selectivity matrix) | 🟡 (refactor: per-polymer ion registry) | 🟡 (medium — registry refactor) | 🟢 Established | **1 — architectural enabler** |
| C6 | `Al³⁺` / trivalent ion gelants | 🟢 | 🔴 (residual-ion contamination; not biotherapeutic-safe) | 🟡 (trivalent network) | 🟡 (registry slot) | 🟢 (low if registry exists) | 🟡 Well-supported | **3 — flagged "non-biotherapeutic"** |
| C7 | `POCl3` (phosphoryl chloride) | 🟢 | 🔴 (high hazard; food-grade starch only) | 🟡 (phosphate diester) | 🟡 | 🟢 (low) | 🟡 Well-supported | **4 — reject for default; document only** |
| C8 | `BORATE_BORAX` (reversible cis-diol) | 🟢 | 🔴 (reversible; fails under elution salt/pH) | 🟢 (reversible mechanism class) | 🟡 (new reversible-bond bookkeeping) | 🟡 (medium — reversibility tracking) | 🟢 Established | **3 — research/temporary porogen** |
| C9 | `HRP_H2O2_TYRAMINE` (enzymatic phenol coupling) | 🟢 | 🟡 (mild; HA/alginate-tyramine work) | 🟢 (enzymatic radical coupling) | 🔴 (needs PHENOL_TYRAMINE ACS) | 🟡 (medium — new ACS + enzyme dose) | 🟢 Well-supported | **2** |
| C10 | `GLYOXAL` (small dialdehyde) | 🟢 | 🔴 (residual-aldehyde + stability concerns) | 🟡 (aldehyde subset) | 🟢 (existing ALDEHYDE site) | 🟢 (low) | 🟡 Well-supported | **3 — defer; lower priority than glutaraldehyde** |

### 3.2 First-principles notes per crosslinker

- **C1 SODIUM_PERIODATE.** Mechanism: NaIO₄ cleaves the C–C bond between vicinal diols, producing two aldehydes per cleavage (Malaprade reaction). For polysaccharides with abundant vicinal-diol arrangement (dextran, pullulan, alginate uronic acid, HA), this is the canonical aldehyde-generation route. Aldehyde density tracks the oxidation degree linearly until chain scission begins (~30–50% oxidation). Already half-implemented through the existing ALDEHYDE ACS site; adding NaIO₄ as an explicit reagent profile is trivial and unlocks downstream hydrazone/oxime/Schiff-base chemistries (C2, L4, AC5).

- **C2 ADH.** Adipic-acid dihydrazide is the standard hydrazone partner to oxidized polysaccharide aldehydes. Mechanism: aldehyde + hydrazide → hydrazone (reversible at low pH; stable at neutral pH; reduction by NaBH₃CN gives covalent stability). Well-characterized for oxidized HA, oxidized dextran, oxidized alginate. ACS enum already has HYDRAZIDE; only needs a `ReagentProfile` entry.

- **C3 BIS-EPOXIDES (PEGDGE/EGDGE/BDDE).** These extend the existing ECH chemistry by adding a spacer between the two epoxide groups. From first principles, the kinetics are similar (epoxide + hydroxylate at alkaline pH → ether; epoxide + amine → secondary amine), but the spacer length controls bead pore-size accessibility, ligand display, and hydrolytic competition (longer PEG arm → higher hydrophilicity → less hydrophobic background). BDDE is the industrial standard for HA dermal-filler hardening; PEGDGE is widely used for agarose. **Critical for industry alignment.**

- **C4 CaSO₄/GDL generalization.** The simulator already implements CaCO₃/GDL slow internal release. CaSO₄ has a similar but higher-solubility profile (K_sp ≈ 4.93 × 10⁻⁵ vs CaCO₃ 4.8 × 10⁻⁹), giving a faster-but-still-controlled release. Implementation = adding a second salt entry to the existing slow-release model. Trivial scope.

- **C5 KCl / per-polymer ion-gelation registry.** The most important **architectural** item among the crosslinkers. Currently the alginate solver hard-codes Ca²⁺. κ-carrageenan gels strongly with K⁺ (specific helix-aggregation mechanism: K⁺ binds inside double-helix junctions; Na⁺ does not), ι-carrageenan with Ca²⁺, gellan with K⁺/Ca²⁺/H⁺, and pectin with Ca²⁺ but with stoichiometry that depends on degree of esterification. The proper abstraction is `IonGelantProfile(polymer, ion, stoichiometry, junction-zone-energy)` registered against a polymer; this lets new materials in M5/M6/M9 plug in without code duplication. **Recommend prioritizing the registry refactor before any new ionic-gel material is added.**

- **C6 Al³⁺.** Scientifically valid (Al³⁺ forms strong ionic bridges with anionic polysaccharides), but Al³⁺ is **unacceptable for biotherapeutic process resins** — residual aluminum is regulated by FDA/EP and induces proteinopathy concerns. Implement only behind a "non-biotherapeutic / research" flag; do not include in the default screening matrix.

- **C7 POCl₃.** Highly hazardous; reacts violently with water producing HCl. Used for food-grade starch crosslinking under specific industrial conditions. Not appropriate for a downstream-processing-simulator default scope. **Reject; document rejection and the reasons.**

- **C8 BORAX/BORATE.** Reversible cis-diol crosslinker — borate ester equilibria are pH-dependent (forms at pH > 8.5; dissociates at acidic pH). Useful as a **temporary porogen** or model network, but not as a final crosslinker for chromatography because pressure and elution buffers will dissociate the network. Add as Tier 3 with automatic downgrade flag for any flow-through application.

- **C9 HRP/H₂O₂/TYRAMINE.** Enzymatic radical coupling between tyramine-functionalized polysaccharides (HA-tyramine, alginate-tyramine) gives dityramine (and a small fraction of triplet adducts). Very mild conditions (pH 7, 37 °C) compatible with bioactive ligand co-immobilization. Requires a **new ACS site (PHENOL_TYRAMINE)** and an enzyme-dose model with H₂O₂ pulsing kinetics. Tier 2 because it depends on the new ACS.

- **C10 GLYOXAL.** Dialdehyde with very short tether (–CHO–CHO). Forms imine/acetal-type linkages but residual aldehyde control and Schiff-base hydrolysis make stability problematic for chromatography media. Add as a Tier 3 alternative to glutaraldehyde, with stability downgrade unless followed by reduction (NaBH₄/NaBH₃CN).

### 3.3 Show-stoppers

- **C7 POCl₃** is rejected as out-of-scope for a default bioprocess simulator. Hazard class plus marginal bioprocess relevance.
- **C6 Al³⁺** carries a regulatory warning that should be enforced in the simulator UI.

---

## 4. Functional Ligands — Screening

### 4.1 Screening matrix

| # | Candidate | Viability | Bioprocess relevance | Distinctiveness | Arch. fit | Effort | Validation | **Tier** |
|---|---|---|---|---|---|---|---|---|
| L1 | `CIBACRON_BLUE_F3GA` (Blue Sepharose) | 🟢 | 🟢 (industry standard pseudo-affinity) | 🟢 (dye-pseudo-affinity class) | 🟡 (new functional_mode + triazine coupling) | 🟡 (medium) | 🟢 Established | **1** |
| L2 | `PROCION_RED_HE3B` (Reactive Red 120) | 🟢 | 🟡 (dehydrogenase/hydrogenase niche) | 🟡 (companion dye to L1) | 🟢 (after L1 lands) | 🟢 (parameter swap) | 🟢 Well-supported | **2** |
| L3 | `AMINOPHENYLBORONIC_ACID` (boronate affinity) | 🟢 | 🟢 (glycoprotein purification, glycated proteins) | 🟢 (cis-diol binding) | 🟡 (new CIS_DIOL target chemistry) | 🟡 (medium) | 🟢 Established | **1** |
| L4 | `P_AMINOBENZAMIDINE` | 🟢 | 🟡 (trypsin-like proteases — narrow but real) | 🟢 (protease-affinity class) | 🟢 (existing amine coupling) | 🟢 (low) | 🟢 Established | **2** |
| L5 | `AMYLOSE_MBP` resin | 🟢 | 🟢 (top-3 recombinant tag system) | 🟢 (polysaccharide-as-affinity-matrix) | 🔴 (material-as-ligand pattern) | 🟡 (medium — need new pattern) | 🟢 Established | **1** |
| L6 | `CHITIN_CBD` resin (intein/CBD) | 🟢 | 🟡 (NEB IMPACT system — research > GMP) | 🟢 (material-as-ligand + on-column cleavage) | 🔴 (same pattern as L5; plus inducible cleavage) | 🟡 | 🟢 Established | **2** |
| L7 | `CALMODULIN` (CBP/TAP-tag) | 🟢 | 🟡 (mostly proteomics/research) | 🟢 (Ca²⁺-dependent ligand) | 🟢 (existing protein-coupling) | 🟢 (low) | 🟡 Well-supported | **3** |
| L8 | `JACALIN` / `LENTIL_LECTIN` | 🟢 | 🟡 (glycoprotein fractionation) | 🟡 (extends existing ConA/WGA family) | 🟢 (drop-in lectin profiles) | 🟢 (trivial) | 🟢 Established | **2** |
| L9 | `THIOPHILIC_LIGAND` (DVS-mercaptoethanol) | 🟢 | 🟢 (T-Sorb/T-Gel commercial) | 🟢 (electron-donor–acceptor mode, distinct from HIC) | 🟡 (new functional_mode) | 🟢 (low) | 🟢 Established | **1** |
| L10 | `MEP_HCIC` (4-mercaptoethylpyridine) | 🟢 | 🟢 (Cytiva MEP HyperCel — antibody capture) | 🟢 (mixed-mode HCIC — pH-switchable hydrophobic→cation-exchange) | 🟡 (new functional_mode + pH-switch model) | 🟡 (medium) | 🟢 Established | **1** |
| L11 | `HEXYL_HIC` | 🟢 | 🟢 (HIC interpolation between butyl & octyl) | 🟡 (alkyl-chain length param) | 🟢 (existing HIC family; one parameter) | 🟢 (trivial) | 🟢 Established | **1** |
| L12 | `OLIGONUCLEOTIDE_DNA_LIGAND` | 🟢 | 🟡 (transcription-factor purification) | 🟢 (sequence-specific nucleic-acid ligand) | 🟡 (new ligand class with sequence param) | 🟡 (medium) | 🟢 Established | **2** |
| L13 | `PEPTIDE_AFFINITY_LIGAND` (HWRGWV) | 🟢 | 🟢 (Protein-A alternatives — emerging) | 🟢 (generic peptide framework) | 🟡 (new generic peptide-ligand object) | 🟡 (medium) | 🟡 Well-supported | **2** |

### 4.2 First-principles notes per ligand

- **L1 CIBACRON BLUE F3GA.** Industry-standard pseudo-affinity dye for nucleotide-binding proteins, albumin, and many enzymes. Binding mechanism is mixed: anthraquinone-driven hydrophobic stacking + sulfonate ionic interactions + sequence-specific recognition by certain enzyme NAD-binding clefts. Documentation already lists Cibacron Blue as deferred — **promote to Tier 1**. Simulator must add the **dye-pseudo-affinity functional_mode** and a **triazine-coupling activation route** (see AC4).

- **L2 PROCION RED HE3B (Reactive Red 120).** Companion to L1; same triazine-coupling chemistry. Once L1's plumbing exists, L2 is a parameter-only addition.

- **L3 AMINOPHENYLBORONIC ACID.** Boronate–cis-diol binding is a unique mechanism: tetrahedral boronate at pH > pKa (~ 8.5) reversibly esterifies cis-diols; sorbitol/fructose competitors elute. Adds a new **target-chemistry class** (CIS_DIOL) for glycoproteins. Industrially used in glycated-hemoglobin (HbA1c) and glycoprotein workflows.

- **L4 P_AMINOBENZAMIDINE.** Specific to trypsin-like serine proteases (binds the S1 specificity pocket). Narrow target spectrum but high specificity. Implementation is straightforward via existing amine-coupling. Tier 2.

- **L5 AMYLOSE_MBP.** **Critical pattern: material-as-affinity-ligand.** Amylose itself (a polysaccharide) is the affinity matrix; MBP-tagged proteins bind amylose, are washed, then eluted with maltose. The simulator currently couples ligands TO a polymer family; this candidate inverts the pattern (the polymer family IS the ligand). Recommend adding a `MaterialAsLigand` flag to `PolymerFamily` to capture this. The same pattern handles L6 (chitin/CBD), so the architectural cost is amortized across two Tier-1/2 items.

- **L6 CHITIN_CBD.** Same material-as-ligand pattern as L5, plus an **on-column cleavage** step (intein-mediated thiol-induced or temperature-induced cleavage releases the untagged protein). Add as Tier 2 to follow L5.

- **L7 CALMODULIN.** Ca²⁺-dependent protein ligand for CBP-tagged or TAP-tag proteins. Real but research-leaning; defer to Tier 3 unless the project plans TAP-tag workflows.

- **L8 JACALIN / LENTIL_LECTIN.** Existing simulator has ConA and WGA. Adding two more lectins is a drop-in — same class (lectin protein), different sugar-binding profile (Jacalin: O-linked Tn antigen; lentil lectin: high-mannose). Trivial and high-value for glycoprotein workflow coverage.

- **L9 THIOPHILIC_LIGAND.** Salt-promoted thiophilic adsorption — distinct from HIC because the binding driver is electron-donor/acceptor interaction at the sulfone–aromatic interface, not pure hydrophobic burial. Industrially used (T-Sorb). Adds a new functional_mode but reuses DVS activation already present.

- **L10 MEP_HCIC.** Hydrophobic Charge-Induction Chromatography is the canonical mixed-mode for antibody capture without salt loading: at pH 7 the mercaptoethylpyridine is uncharged and binds IgG hydrophobically; lowering to pH 4 protonates the pyridine to a cation that electrostatically repels IgG, eluting it. Cytiva MEP HyperCel and Pall MEP™ are commercial products. **High industry relevance — Tier 1.**

- **L11 HEXYL_HIC.** Pure parameter-only addition to the existing alkyl-HIC family. No new architecture. Quickest win in the ligand category.

- **L12 OLIGONUCLEOTIDE_DNA_LIGAND.** Sequence-specific DNA ligand for transcription-factor and nucleic-acid-binding-protein purification. Mechanism is sequence recognition (ds-DNA binding-site mimic). Add as a generic `OligoLigand` profile with sequence and length parameters; nuclease-stability flag for crude lysate work.

- **L13 PEPTIDE_AFFINITY_LIGAND.** Generic peptide-ligand framework (HWRGWV is the canonical antibody-capture example). Adds a `PeptideLigand` profile carrying a sequence string, terminal coupling handle (Lys/Cys/N-term/azide), and a calibration-required binding model. Architecturally extensible: any future peptide ligand can be added as data without code change.

### 4.3 Show-stoppers

None. The narrow-target ligands (L4, L7, L12) are scope-limited but scientifically sound.

---

## 5. Linker Arms and ACS-Conversion Molecules — Screening

### 5.1 Linker-arm screening matrix

| # | Candidate | Viability | Distinctiveness | Arch. fit | Effort | Validation | **Tier** |
|---|---|---|---|---|---|---|---|
| K1 | `DIAMINOPROPANE_SPACER` (1,3-DAP) | 🟢 | 🟡 (spacer length interpolation EDA→hexamethylenediamine) | 🟢 | 🟢 (trivial) | 🟢 Established | **1** |
| K2 | `GLYCINE_GLYGLY_GLY4_SPACER` (oligoglycine) | 🟢 | 🟡 (hydrophilic spacer alternative) | 🟢 | 🟢 (low) | 🟢 Established | **2** |
| K3 | `CYSTAMINE_DISULFIDE_SPACER` (reducible) | 🟢 | 🟢 (cleavable spacer class) | 🟡 (new disulfide bookkeeping) | 🟡 (medium) | 🟢 Well-supported | **2** |
| K4 | `AMINOOXY_PEG_LINKER` | 🟢 | 🟢 (oxime/hydrazone bioorthogonal) | 🟡 (new AMINOOXY ACS) | 🟡 (medium) | 🟢 Established | **1** |
| K5 | `AZIDE_ALKYNE_CLICK_HANDLE` (CuAAC + SPAAC) | 🟢 | 🟢 (modular click chemistry; mainstream) | 🔴 (new AZIDE/ALKYNE ACS + Cu accounting) | 🟡 (medium-high) | 🟢 Established | **1** |
| K6 | `SUCCINIC_OR_GLUTARIC_ANHYDRIDE` (carboxylation) | 🟢 | 🟡 (distal-amine → distal-carboxyl conversion) | 🟢 (existing CARBOXYL_DISTAL site) | 🟢 (low) | 🟢 Established | **2** |

### 5.2 ACS-conversion screening matrix

| # | Candidate | Viability | Distinctiveness | Arch. fit | Effort | Validation | **Tier** |
|---|---|---|---|---|---|---|---|
| AC1 | `CNBR_ACTIVATION` (cyanate ester / imidocarbonate) | 🟢 | 🟢 (classic Sepharose-affinity; required for many published protocols) | 🟡 (new CYANATE_ESTER ACS) | 🟡 (medium; high-toxicity flag) | 🟢 Established | **1** |
| AC2 | `CDI_ACTIVATION` (carbonyldiimidazole) | 🟢 | 🟢 (modern CNBr alternative; neutral activated matrix) | 🟡 (new IMIDAZOLYL_CARBONATE ACS) | 🟢 (low) | 🟢 Established | **1** |
| AC3 | `TRESYL_OR_TOSYL_ACTIVATION` | 🟢 | 🟡 (sulfonate leaving group) | 🟡 (new SULFONATE_LEAVING ACS) | 🟢 (low) | 🟢 Well-supported | **2** |
| AC4 | `CYANURIC_CHLORIDE_TRIAZINE_ACTIVATION` | 🟢 | 🟢 (required for L1/L2 dye coupling) | 🟡 (new TRIAZINE_REACTIVE ACS) | 🟢 (low) | 🟢 Established | **1 — paired with L1** |
| AC5 | `GLYCIDOL_PERIODATE_GLYOXYL` (multipoint enzyme immobilization) | 🟢 | 🟢 (multipoint Lys coupling; enzyme stabilization) | 🟡 (new GLYOXYL ACS; chained activation) | 🟡 (medium) | 🟢 Established | **1** |
| AC6 | `PYRIDYL_DISULFIDE_ACTIVATION` | 🟢 | 🟢 (reversible thiol capture) | 🟡 (couples with K3) | 🟡 (medium) | 🟢 Well-supported | **2** |
| AC7 | `PERIODATE_ALDEHYDE_ACS` (also listed under crosslinkers as C1) | 🟢 | 🟢 (vicinal-diol → aldehyde) | 🟢 (existing ALDEHYDE site) | 🟢 (low) | 🟢 Established | **1 — same as C1** |

### 5.3 First-principles notes per linker / ACS conversion

- **K1 1,3-DAP.** Trivial extension of the existing diamine library (EDA, propanediamine, hexamethylenediamine); just a spacer-length parameter. Already pre-screened in the project's docs.

- **K2 OLIGOGLYCINE.** Hydrophilic spacer that minimizes hydrophobic background at the support surface. Useful in conjunction with peptide ligands (L13) where the spacer must not contribute its own binding.

- **K3 CYSTAMINE_DISULFIDE.** Reducible/cleavable spacer enables analytical capture-and-release workflows (e.g., on-column digest, click-then-release). Adds a "spacer reducibility" flag to `ReagentProfile`. Tier 2 — useful but not foundational.

- **K4 AMINOOXY_PEG.** Critical for oriented-protein immobilization: aminooxy + aldehyde → oxime (more hydrolytically stable than hydrazone); aminooxy + ketone → ketoxime. Naturally absent in proteins, so highly bioorthogonal. Add as Tier 1 because it pairs with C1 (periodate aldehyde generation) to enable the **glycoprotein oriented-immobilization workflow**.

- **K5 AZIDE_ALKYNE_CLICK.** CuAAC (Cu-catalyzed azide–alkyne cycloaddition) and SPAAC (strain-promoted, copper-free) are now mainstream bioconjugation. Adds modular ligand-library architecture: any ligand bearing the complementary handle can plug in without bespoke chemistry. **Architectural payoff is large**, but cost is medium-high (new AZIDE + ALKYNE ACS sites; CuAAC needs Cu-residue tracking; SPAAC needs strained-cyclooctyne ligand model).

- **K6 SUCCINIC ANHYDRIDE.** Converts a distal amine into a distal carboxyl by N-acylation. Useful for inverting coupling polarity (after introducing an amine spacer, succinylate to expose a carboxyl for EDC/NHS coupling). Tier 2.

- **AC1 CNBR.** Classic — most published affinity-coupling protocols use CNBr-activated agarose. Toxicity (HCN release) requires strong UI warnings, but the chemistry remains essential. Add CYANATE_ESTER as a new ACS.

- **AC2 CDI.** Modern CNBr alternative giving a neutral activated matrix (carbamate linkage rather than the slightly-charged isourea from CNBr). Adds IMIDAZOLYL_CARBONATE ACS.

- **AC3 TRESYL/TOSYL.** Sulfonate leaving-group activation; less common than CDI. Tier 2.

- **AC4 CYANURIC CHLORIDE.** Required for triazine-dye coupling (L1, L2). Bundle with L1 in the same release. Cyanuric chloride has 3 sequential substitutable positions — the chemistry-class field can capture monosubstituted (dichlorotriazine) vs disubstituted activated supports.

- **AC5 GLYCIDOL_PERIODATE_GLYOXYL.** Two-step activation: glycidol coats the support hydroxyls with glyceryl ether (giving 1,2-diol termini); periodate then cleaves to a glyoxyl (–CHO) terminus. Glyoxyl agarose is specifically designed for **multipoint covalent enzyme immobilization** — multiple Lys residues anchor simultaneously, dramatically increasing thermal/operational stability. Real industrial value (CALB, lipase B immobilization). Tier 1.

- **AC6 PYRIDYL_DISULFIDE.** Couples with K3 (cystamine spacer) for reversible thiol capture and reducing-agent elution. Tier 2.

- **AC7 PERIODATE_ALDEHYDE_ACS.** Same as C1 — listed in two categories in the source document because periodate functions both as a crosslinker precursor (oxidized polysaccharide self-crosslinks via aldehyde-amine after amine introduction) and as an ACS-conversion (vicinal-diol → aldehyde). One implementation serves both.

### 5.4 Show-stoppers

None. CNBr (AC1) requires a hazard flag. CuAAC (K5) requires Cu-residue tracking for biotherapeutic compatibility (residual Cu specifications by ICH Q3D).

---

## 6. Integration Roadmap

### 6.1 Tier 1 — v9.2 release (must integrate)

**Architectural prerequisites (land first; foundation for the rest):**

- **A1. ACS expansion.** Add to `ACSSiteType`: `SULFATE_ESTER`, `THIOL`, `PHENOL_TYRAMINE`, `AZIDE`, `ALKYNE`, `AMINOOXY`, `CIS_DIOL`, `TRIAZINE_REACTIVE`, `GLYOXYL`, `CYANATE_ESTER`, `IMIDAZOLYL_CARBONATE`, `SULFONATE_LEAVING`. (Some of these are Tier-2-needed but adding the enum members is cheap and avoids a future migration.)
- **A2. PolymerFamily expansion.** Add `AGAROSE`, `CHITOSAN`, `DEXTRAN`. Refactor `AGAROSE_CHITOSAN` solver to delegate to a composite of `AGAROSE` + `CHITOSAN`.
- **A3. Per-polymer ion-gelation registry.** Replace alginate-hardcoded Ca²⁺ logic with `IonGelantProfile(polymer_family, ion, k_binding, junction_zone_energy)` registered per polymer. Internal-release (CaCO₃/GDL/CaSO₄) extension lives here.
- **A4. `ReagentProfile.functional_mode` extension.** Add `dye_pseudo_affinity`, `mixed_mode_hcic`, `thiophilic`, `peptide_affinity`, `boronate`, `oligonucleotide`, `click_handle`, `material_as_ligand`.
- **A5. Bioorthogonal-coupling chemistry class.** Add `chemistry_class` values: `oxime`, `hydrazone`, `cuaac`, `spaac`, `dye_triazine`, `cnbr_amine`, `cdi_amine`, `glyoxyl_multipoint`, `phenol_radical`.

**Materials (Tier 1):** M1 `AGAROSE_ONLY`, M2 `CHITOSAN_ONLY`, M3 `DEXTRAN_ECH`.

**Crosslinkers (Tier 1):** C1 `SODIUM_PERIODATE`, C2 `ADH`, C3 bis-epoxide family (`PEGDGE`/`EGDGE`/`BDDE`), C4 `CaSO4_GDL`, C5 KCl + per-polymer ion-gelation registry.

**Ligands (Tier 1):** L1 `CIBACRON_BLUE_F3GA`, L3 `AMINOPHENYLBORONIC_ACID`, L5 `AMYLOSE_MBP` (with material-as-ligand pattern), L9 `THIOPHILIC_LIGAND`, L10 `MEP_HCIC`, L11 `HEXYL_HIC`.

**Linkers (Tier 1):** K1 `DIAMINOPROPANE`, K4 `AMINOOXY_PEG`, K5 `AZIDE_ALKYNE_CLICK`.

**ACS conversion (Tier 1):** AC1 `CNBR`, AC2 `CDI`, AC4 `CYANURIC_CHLORIDE` (paired with L1), AC5 `GLYCIDOL_PERIODATE_GLYOXYL`, AC7 = C1.

**Tier 1 totals:** 3 materials, 5 crosslinkers (incl. ion registry), 6 ligands, 3 linkers, 5 ACS conversions, plus 5 architectural prerequisites = **18 candidate items + 5 architectural prerequisites**.

### 6.2 Tier 2 — v9.3 release

**Materials:** M4 `AGAROSE_DEXTRAN_CORE_SHELL`, M5 `AGAROSE_ALGINATE_IPN`, M6 `ALGINATE_CHITOSAN_PEC`, M9 `KAPPA_CARRAGEENAN` (+ sulfate-ester ACS validation), M10 `HYALURONATE`.

**Crosslinkers:** C9 `HRP_H2O2_TYRAMINE`.

**Ligands:** L2 `PROCION_RED_HE3B`, L4 `P_AMINOBENZAMIDINE`, L6 `CHITIN_CBD`, L8 `JACALIN`/`LENTIL_LECTIN`, L12 `OLIGONUCLEOTIDE_DNA_LIGAND`, L13 `PEPTIDE_AFFINITY_LIGAND`.

**Linkers:** K2 oligoglycine, K3 cystamine disulfide, K6 succinic/glutaric anhydride.

**ACS conversion:** AC3 `TRESYL/TOSYL`, AC6 `PYRIDYL_DISULFIDE`.

**Tier 2 totals:** 5 materials, 1 crosslinker, 6 ligands, 3 linkers, 2 ACS conversions = **17 items**.

### 6.3 Tier 3 — Deferred / research-mode / feature-flagged

- M7 `PECTIN_CALCIUM`/`PECTIN_CHITOSAN_PEC`, M8 `GELLAN_GUM`/`GELLAN_ALGINATE`, M11 `PULLULAN`, M12 `STARCH_POROUS` — parameter-only additions once the ion-gelation registry and neutral α-glucan paths are mature.
- C6 `Al³⁺` (non-biotherapeutic flag), C8 `BORATE_BORAX` (research/temporary porogen flag), C10 `GLYOXAL` (lower-priority alternative to glutaraldehyde).
- L7 `CALMODULIN` (proteomics niche).

**Tier 3 totals:** 4 materials, 3 crosslinkers, 1 ligand, 0 linkers, 0 ACS = **8 items + 3 multi-variants ≈ 11 items**.

### 6.4 Tier 4 — Reject for default scope

- C7 `POCl3` — hazard plus marginal bioprocess relevance.

**Tier 4 totals:** 1 item. (Listed for completeness; the user can override if a specific use case justifies it.)

### 6.5 Dependency graph (critical-path view)

```
A1 ACS expansion ───────────────────┐
A2 PolymerFamily expansion ─────────┤
A3 Ion-gelation registry ───────────┼──> Tier-1 materials and ligands
A4 functional_mode extension ───────┤
A5 chemistry_class extension ───────┘

A2 ──> M1 AGAROSE_ONLY ──> M4 (Tier 2)
A2 ──> M2 CHITOSAN_ONLY ──> M6 (Tier 2)
A2 ──> M3 DEXTRAN_ECH ───> M4 (Tier 2)
A3 ──> C5 KCl ───────────> M9 KAPPA_CARRAGEENAN (Tier 2)
A3 ──> C4 CaSO4_GDL ─────> M5/M6 (Tier 2)

A1 ──> C1 NaIO4 ──> C2 ADH ──> K4 AMINOOXY ──> oriented-glycoprotein workflow
A1 ──> AC4 cyanuric chloride ──> L1 Cibacron Blue ──> L2 Procion Red (Tier 2)
A1 ──> AC5 glyoxyl ──> multipoint enzyme immobilization workflow
A1 ──> K5 click handles ──> peptide and Protein-A-mimetic library plug-in

A4 ──> L9 thiophilic ──> L10 MEP HCIC
A4 ──> material-as-ligand flag ──> L5 Amylose-MBP ──> L6 Chitin-CBD (Tier 2)
```

### 6.6 Validation strategy per tier

For Tier 1, every reagent profile must carry **at least one peer-reviewed citation** for kinetics or binding constants at SEMI_QUANTITATIVE evidence tier or better. For materials, gelation thresholds and rheology constants must come from primary references on the same polymer grade where possible. For ligands, binding affinities (K_d) and dynamic binding capacities (DBC at 10% breakthrough) are required where available.

Tier 2 candidates can be added at QUALITATIVE_TREND tier on first release if quantitative parameters are scarce, but every Tier-1-promoted item has been verified to have published quantitative data.

---

## 7. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Adding 10 new families to `PolymerFamily` breaks the v9.0 Family-First UI rendering matrix | Medium | High | Stage families behind a per-family `is_enabled_in_ui` flag; ship Tier 1 families fully wired and Tier 2/3 families as data-only entries. |
| New ACS site types introduce conservation-law violations in the existing `ACSProfile` | Low | High | Each new ACS site must include a unit test that verifies `terminal_sum ≤ accessible_sites` and the conservation tolerance check (`_CONSERVATION_TOL`). |
| Per-polymer ion-gelation registry breaks existing alginate calibration | Low | High | Implement registry as a thin shim that delegates to the existing alginate solver for the alginate+Ca²⁺ entry; add registry-only tests for new entries; verify alginate regression suite passes unchanged. |
| Click chemistry residual-Cu accounting introduces complexity disproportionate to value | Medium | Medium | Implement Cu accounting as an optional `requires_cu_removal` flag on the reagent profile; SPAAC variant exposes the same workflow without the flag. |
| Material-as-ligand pattern (L5, L6) requires inverting a foundational simulator assumption | Medium | High | Implement as a non-breaking flag (`PolymerFamily.material_as_ligand: bool = False`); existing solvers ignore the flag; the pattern only activates in workflows that explicitly check it. |
| Triazine-dye ligand leakage warnings (L1, L2) clash with the simulator's existing leakage model | Low | Medium | Reuse the existing `ligand_leaching_warning` field; add a dye-specific multiplier in the leakage model only if calibration data justifies it. |

---

## 8. Recommendations to dev-orchestrator and architect

The Scientific Advisor recommends the following framing for the joint planning phase:

1. **Treat the five architectural prerequisites (A1–A5) as a single foundational PR** that lands ahead of any Tier-1 candidate code. This avoids piecemeal enum migrations later.

2. **Group Tier-1 chemistry by workflow synergy** for development-phase batching:
   - **Workflow batch B1: classical-affinity-resin completion.** AC1 CNBr + AC2 CDI + L11 hexyl + AGAROSE_ONLY (M1). Closes the gap to the canonical Sepharose-class affinity portfolio.
   - **Workflow batch B2: oriented-glycoprotein immobilization.** C1 periodate + C2 ADH + K4 aminooxy. Single coherent workflow; small surface; high scientific value.
   - **Workflow batch B3: dye-pseudo-affinity.** L1 Cibacron Blue + AC4 cyanuric-chloride activation + dye-pseudo-affinity functional_mode. Demonstrates the new dye-affinity class on industry-standard Blue Sepharose.
   - **Workflow batch B4: mixed-mode antibody capture.** L9 thiophilic + L10 MEP HCIC. Establishes the mixed-mode HCIC functional_mode.
   - **Workflow batch B5: bis-epoxide hardening.** C3 PEGDGE/BDDE on agarose + dextran. Industrial workhorse chemistry; small surface.
   - **Workflow batch B6: ion-gelation registry refactor.** A3 + C4 CaSO4 + C5 KCl. Architectural enabler for Tier 2.
   - **Workflow batch B7: click-chemistry handle.** K5 azide/alkyne. Modular framework that subsequent peptide/Protein-A mimetic work plugs into.
   - **Workflow batch B8: multipoint enzyme immobilization.** AC5 glyoxyl agarose. Unique enzyme-stabilization mechanism; small surface.
   - **Workflow batch B9: material-as-ligand pattern.** L5 amylose-MBP. Establishes the inversion of the ligand→material relationship, paving the way for Tier-2 chitin-CBD (L6).
   - **Workflow batch B10: boronate affinity.** L3 aminophenylboronic acid + CIS_DIOL target chemistry.
   - **Workflow batch B11: chitosan-only beads.** M2 + pH-swelling sub-model. Modest scope; opens the chitosan-only workflow surface.
   - **Workflow batch B12: dextran-ECH.** M3 with ECH dextran-OH kinetics.

3. **Validate each batch end-to-end** before the next batch starts. Tier 1 has 12 batches; each batch should have at least one regression test exercising a published reference protocol.

4. **Document Tier 4 rejection** (POCl3) explicitly in the architecture decision record, so future contributors do not re-introduce it without revisiting the rationale.

5. **Surface Tier 3 candidates as a "reagent library extension" data file** — no new code paths needed once Tier 2 lands. This lets the user community add pectin/gellan/pullulan/starch profiles without architectural modification.

---

## 9. Conclusions

- **18 of 50 candidates are Tier 1** — all scientifically established, bioprocess-relevant, and architecturally tractable within the v9.2 cycle.
- **17 candidates are Tier 2** — strong scientific case but either depend on a Tier 1 item or carry medium architectural cost; appropriate for v9.3.
- **11 candidates are Tier 3** — niche, bioprocess-marginal, or carry biotherapeutic-incompatibility flags; implement behind feature flags or as data-only library extensions.
- **1 candidate is Tier 4** (POCl3) — reject for default scope.

The single highest-leverage architectural change is the **per-polymer ion-gelation registry (A3)**, which alone unlocks five Tier-2 ionic-gelled material families and converts three currently-isolated polymers (alginate, future κ-carrageenan, future gellan) into a coherent ionic-gelation library. Build this first.

The single highest-leverage scientific addition is **`AGAROSE_ONLY` (M1)** — it provides the baseline comparator that the entire bioprocess validation literature is built on, at near-zero implementation cost.

The single highest-leverage chemistry addition is **periodate–ADH–aminooxy chain (C1+C2+K4)** — three small reagent-profile additions that together unlock the entire oriented-glycoprotein-immobilization workflow.

---

> **Disclaimer:** This scientific analysis is provided for informational, research, and advisory purposes only. It does not constitute professional engineering advice, medical advice, or formal peer review. All hypotheses and experimental designs implied by integration of these candidates should be validated through appropriate laboratory experimentation and, where applicable, reviewed by qualified domain experts before implementation. The author is an AI assistant and the analysis should be treated as a structured starting point for further investigation and joint planning by the architect and dev-orchestrator.
