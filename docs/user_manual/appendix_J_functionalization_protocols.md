# Appendix J — Functionalization Wet-Lab Protocols

*First Edition supplement to the Downstream Processing Simulator user manual.
Written for first-time users, downstream-processing technicians, and R&D
researchers who need to connect DPSim M2 chemistry to executable bench work.
Every protocol is self-contained, but simulation claims are authoritative only
when the protocol chain is represented by the active `ProcessRecipe` and its
validation/evidence report.*

**How to use this appendix**

1. Decide the final function: Protein A capture, IMAC, ion exchange, HIC,
   enzyme immobilization, or a research-only coupling route.
2. Build the M2 chain in wet-lab order: activation, optional spacer/linker
   insertion, ligand/protein coupling, blocking/quenching, washing, and
   storage-buffer exchange.
3. Confirm the chain is represented in the active `ProcessRecipe`. If a
   chemistry below has no implemented reagent key, document it as an external
   bench operation and do not claim a quantitative M2 prediction from DPSim.
4. Execute the chosen protocols with a wash between chemically incompatible
   steps. Do not carry primary-amine buffers into NHS chemistry, reducing
   agents into maleimide chemistry, chelators into IMAC charging, or high-pH
   activation liquor into protein coupling.
5. Assay ligand density, retained activity, free ligand/protein in wash
   fractions, residual reactive sites, and leaching. These assays are the M2
   media contract passed to M3.

**Conventions used throughout**

- **"CV"** = column volume. One CV of a 1 mL gel bed = 1 mL of buffer.
- **"wet gel"** = drained polysaccharide matrix (agarose, sepharose, cellulose).
  When a protocol says "10 mL wet gel", it means gel drained to a damp cake
  with no free supernatant. Weigh or measure by volume in a graduated cylinder.
- **"Evidence tier"** mirrors the simulator's `ModelEvidenceTier` values
  for documentation consistency, but protocol literature strength does not
  automatically upgrade a simulation output:
  `validated_quantitative`, `calibrated_local`, `semi_quantitative`,
  `qualitative_trend`, and `unsupported`.
- **"DPSim M2 key"** means the implemented `reagent_key` used inside a
  `ProcessRecipe` step. It is not a legacy UI dropdown label. If a protocol
  says "not implemented", the wet-lab method may still be valid, but DPSim
  must treat that operation as external evidence unless a calibrated
  `ReagentProfile` is added.
- **Temperature** is in °C. **"RT"** = room temperature ≈ 20-25 °C unless
  the protocol specifies otherwise.
- **pH** is measured with a calibrated pH meter, not indicator strips, unless
  indicated.
- **Water** means ultrapure ≥18 MΩ·cm (e.g., MilliQ), not tap or DI water,
  for every protocol.

**Universal safety reminder** (read once, remember every time)

- Nitrile gloves, safety glasses, and a buttoned lab coat are the minimum PPE
  for every protocol in this appendix. Long trousers, closed-toe shoes.
- Work in a certified fume hood for any step that evolves fumes, handles
  volatile organics, or uses reagents marked "fume hood required" below.
- Every reagent box below has GHS pictograms and H-codes. If you cannot
  identify a pictogram, read the SDS for that reagent **before** you handle it.
- Waste: never mix halogenated, non-halogenated, aqueous, and solid waste.
  Each protocol names its waste stream. If in doubt, ask your lab's safety
  officer before disposing.
- If you spill, splash, or inhale anything: stop, rinse skin/eyes for 15
  minutes at the nearest safety shower or eyewash, notify a supervisor,
  consult the SDS, do not finish the protocol without clearance.

**Current simulator mapping**

The built-in M2 stage templates are:

| Template | Implemented chain | Main reagent keys |
|---|---|---|
| `epoxy_protein_a` | ECH activation, Protein A coupling, epoxide block, wash, storage exchange | `ech_activation`, `protein_a_coupling`, `ethanolamine_quench` |
| `edc_nhs_protein_a` | ECH activation, AHA spacer, EDC/NHS activation, Protein A NHS coupling, wash, storage exchange | `ech_activation`, `aha_carboxyl_spacer_arm`, `edc_nhs_activation`, `protein_a_nhs_coupling` |
| `hydrazide_protein_a` | ECH activation, hydrazide spacer, oxidized Protein A coupling, wash, storage exchange | `ech_activation`, `hydrazide_spacer_arm`, `protein_a_hydrazide_coupling` |
| `vinyl_sulfone_protein_a` | DVS activation, Protein A vinyl-sulfone coupling, thiol block, wash, storage exchange | `dvs_activation`, `protein_a_vs_coupling`, `mercaptoethanol_quench` |
| `nta_imac` | ECH activation, NTA coupling, nickel charging, storage exchange | `ech_activation`, `nta_coupling`, `nickel_charging_nta` |
| `ida_imac` | ECH activation, IDA coupling, nickel charging, storage exchange | `ech_activation`, `ida_coupling`, `nickel_charging_ida` |

Other implemented reagent keys include `genipin_secondary`,
`glutaraldehyde_secondary`, `stmp_secondary`, `bdge_activation`,
`deae_coupling`, `q_coupling`, `cm_coupling`, `phenyl_coupling`,
`sp_coupling`, `butyl_coupling`, `octyl_coupling`, `glutathione_coupling`,
`protein_g_coupling`, `protein_ag_coupling`, `protein_l_coupling`,
`streptavidin_coupling`, `heparin_coupling`, `con_a_coupling`,
`wga_coupling`, `eda_spacer_arm`, `dadpa_spacer_arm`, `dah_spacer_arm`,
`peg600_spacer_arm`, `sm_peg2`, `sm_peg4`, `sm_peg12`, `sm_peg24`,
`protein_a_cys_coupling`, `tcep_reduction`, `dtt_reduction`,
`nickel_charging`, `cobalt_charging`, `copper_charging`, `zinc_charging`,
and `edta_stripping`. M3 evidence is capped by the weakest M2 media
contract and calibration domain.

---

## J.1 ACS Conversion (formerly "Hydroxyl Activation")

> **v0.5.0 rename note.** Up to v0.4.x this section was titled "Hydroxyl
> Activation" because most of the canonical protocols (CNBr, CDI, ECH,
> DVS, BDDE, Tresyl) start from a polysaccharide -OH. The v0.5.0 ACS
> Converter epic generalises the framing: every protocol below converts
> one ACS (Available Crosslinking Site) into a chemically distinct one,
> and not all targets are -OH (periodate consumes vicinal diols; EDC/NHS
> targets -COOH). The Streamlit dashboard surfaces this as the **ACS
> Conversion** chemistry bucket. Pyridyl-disulfide, which is installed
> on a pre-existing arm-distal amine rather than directly on the
> polysaccharide, has its own protocol in §J.4.7 (Arm-distal Activation).

Polysaccharide matrices (agarose, sepharose, cellulose, dextran) present
hydroxyl, carboxyl, vicinal-diol, or amine functional groups on every sugar
ring depending on the polymer family. These groups are usually chemically
inert under mild conditions. Activation converts the matrix-side ACS into a
leaving group or a reactive electrophile so that downstream coupling
(amine, thiol, hydroxyl, carboxyl) can proceed at room temperature and
near-neutral pH.

Pick **one** activator. More aggressive activators = higher ligand-coupling
density but also more matrix damage and more residual reactivity after
coupling (so a bigger quench step at the end).

---

### J.1.1  Hydroxyl Activation — CNBr (cyanogen bromide)

**Purpose:** Activate -OH on agarose / sepharose so that primary amines can
couple directly. The classical gold-standard protocol since 1967.

**Evidence tier:** `validated_quantitative`

**DPSim M2 key:** not implemented as a quantitative built-in
`ReagentProfile`. Use vendor CNBr-activated media as an external M2
starting material, record ligand-density/activity assays, and cap evidence
at `qualitative_trend` unless local calibration is ingested.

**Based on:** Axén, Porath & Ernback (*Nature* 1967, 214:1302); Kohn & Wilchek
(*Appl. Biochem. Biotechnol.* 1984, 9:285); Hermanson *Bioconjugate Techniques*
3rd ed. Ch. 15.3.1.

#### Safety — READ BEFORE HANDLING

CNBr is **highly toxic**. Most labs buy sepharose pre-activated with CNBr
("CNBr-activated Sepharose 4B", Cytiva) instead of activating in-house.
Follow the Cytiva protocol if you use pre-activated gel.

If you must activate in-house:
- GHS pictograms: skull-and-crossbones, corrosive, environmental hazard.
- H-codes: H300 (fatal if swallowed), H311 (toxic in contact with skin),
  H330 (fatal if inhaled), H314 (causes severe skin burns and eye damage),
  H410 (very toxic to aquatic life).
- PPE: double nitrile gloves, face shield over safety glasses, chemical-
  resistant apron, lab coat. Fume hood mandatory, never handle on the bench.
- CNBr releases HCN on hydrolysis. Keep a cyanide test kit and a supply of
  sodium thiosulfate + sodium hydroxide on hand for accidental decomposition.
- Waste: collect all CNBr-contaminated aqueous waste in a labelled carboy
  containing 1 M NaOH. Let it neutralise for ≥ 24 h before disposal via your
  institution's hazardous-chemical-waste stream. Solid waste (gloves, towels)
  goes in a sealed container labelled "CNBr contaminated".

**Strong recommendation:** use pre-activated sepharose. The in-house
activation is documented here only for lab completeness.

#### What you need (pre-activated-sepharose route)

- 10 mL CNBr-activated Sepharose 4B, supplied as freeze-dried powder
- 200 mL cold 1 mM HCl (ice bath)
- 50 mL coupling buffer: 0.1 M NaHCO₃, 0.5 M NaCl, pH 8.3
- Sintered glass funnel (porosity 2, 40-100 μm), vacuum flask, vacuum source
- End-over-end rotator
- pH meter

#### Procedure (pre-activated-sepharose route)

1. Put on the PPE listed above. Confirm the fume hood sash is at the
   recommended working height.
2. Weigh 3 g of freeze-dried CNBr-activated Sepharose 4B powder into a 50 mL
   conical tube. This swells to ≈10 mL wet gel.
3. Add 30 mL cold 1 mM HCl. Cap the tube. Invert gently 5 times to disperse.
4. Pour the suspension into the sintered glass funnel. Apply gentle vacuum to
   drain. Wash with 6 × 30 mL 1 mM HCl (total 200 mL). Keep on ice. Do **not**
   let the gel dry out — stop vacuum when the surface just loses its shine.
5. Immediately transfer the damp gel to a fresh 50 mL tube and add the ligand
   solution in coupling buffer (§J.2). Proceed to coupling within 15 min. If
   you cannot couple immediately, transfer to 1 mM HCl and store at 4 °C for
   no more than 2 h — activity decays rapidly at neutral pH.

#### Quality control

- Activation density: 12-16 μmol reactive sites per mL wet gel (specification
  from Cytiva; each lot has a Certificate of Analysis).
- Visual: gel is off-white and translucent; any brown or yellow colour
  indicates hydrolysis. Reject.

#### Troubleshooting

- **Low coupling yield (< 50 %):** gel was over-washed or sat too long in
  coupling buffer before ligand addition. Move faster.
- **Ligand activity lost after coupling:** CNBr creates an isourea bond that
  is slightly positively charged at neutral pH. For charge-sensitive ligands,
  use CDI or BDDE (§J.1.5, §J.1.3) instead.
- **Matrix turns yellow/brown:** hydrolysis. Start over with fresh gel.

#### References

Axén R, Porath J, Ernback S (1967) *Nature* 214:1302. Kohn J, Wilchek M (1984)
*Appl. Biochem. Biotechnol.* 9:285. Hermanson GT (2013) *Bioconjugate
Techniques* 3rd ed., Academic Press, Ch. 15.3.1.

---

### J.1.2  Hydroxyl Activation — Epichlorohydrin

**Purpose:** Activate -OH groups to epoxides. The epoxide can couple amines,
thiols, and hydroxyls directly. Also introduces a small 3-atom spacer.

**Evidence tier:** `validated_quantitative`

**DPSim M2 key:** `ech_activation`. Epichlorohydrin is a restricted CMR
reagent in many institutions; written risk assessment and supervisor
approval are usually required.

**Based on:** Matsumoto et al. (*J. Chromatogr.* 1980, 188:457); Sundberg &
Porath (*J. Chromatogr.* 1974, 90:87); Hermanson Ch. 15.3.4.

#### Safety — READ BEFORE HANDLING

- GHS pictograms: skull-and-crossbones, corrosive, health hazard (CMR).
- H-codes: H301 (toxic if swallowed), H311 (toxic in contact with skin),
  H331 (toxic if inhaled), H314 (severe burns), H317 (skin sensitisation),
  H350 (may cause cancer), H341 (suspected mutagen), H361 (suspected
  reproductive toxin).
- PPE: double nitrile gloves (change every 30 min; epichlorohydrin permeates
  nitrile within ~1 h), face shield, chemical-resistant apron, lab coat.
  Fume hood mandatory.
- Epichlorohydrin is a confirmed animal carcinogen and probable human
  carcinogen (IARC Group 2A). Some institutions require a written risk
  assessment and supervisor sign-off before use.
- Waste: halogenated organic aqueous waste. Collect in a dedicated labelled
  carboy. Never pour down the drain.

#### What you need (per 10 mL wet gel)

| Reagent | Amount | CAS | Storage |
|---|---|---|---|
| Epichlorohydrin | 2 mL | 106-89-8 | RT, tightly capped, fume hood cabinet |
| 2 M NaOH | 10 mL | 1310-73-2 | RT |
| Sodium borohydride (NaBH₄) | 20 mg | 16940-66-2 | Desiccator, RT |
| Water (for washes) | ≥ 200 mL | — | RT |

Equipment: 50 mL screw-cap polypropylene tube; end-over-end rotator; water
bath at 40 °C; sintered glass funnel; pH meter.

#### Procedure

1. PPE on. Open the fume hood sash. Verify airflow (test with a tissue at the
   sash face — it should draw inward).
2. Wash 10 mL wet gel with 5 × 30 mL water on a sintered glass funnel. Drain
   to a damp cake.
3. Transfer drained gel to the 50 mL screw-cap tube. Add 10 mL 2 M NaOH and
   20 mg NaBH₄ (the NaBH₄ suppresses Maillard-like side reactions).
4. In the fume hood, add 2 mL epichlorohydrin. Cap tightly. Mix by inversion
   (10 inversions).
5. Rotate end-over-end at 40 °C, 2 h.
6. Transfer to the sintered glass funnel. Wash with 10 × 30 mL water until
   the filtrate pH is ≤ 8 and the laboratory residual-epichlorohydrin check
   or validated wash endpoint is acceptable. Do not use odor as a clearance
   test.
7. Drain to a damp cake. The gel is now epoxide-activated and ready for
   coupling (§J.2.2).

#### Quality control

- Epoxide density: 15-25 μmol epoxide per mL wet gel. Titrate by reacting a
  100 μL aliquot with 2 mL 1.3 M Na₂S₂O₃ pH 7.0 for 30 min at RT, then
  back-titrating the liberated NaOH with 0.1 M HCl to pH 7.0 (Sundberg &
  Porath 1974).

#### Troubleshooting

- **Gel becomes yellow / brown:** over-reaction or NaBH₄ missing. Restart.
- **Low epoxide density:** epichlorohydrin bottle open too long (hydrolysed).
  Use a fresh, unopened bottle. Epichlorohydrin hydrolyses on air exposure.
- **Coupling fails after activation:** activated gel was stored. Epoxide
  hydrolyses in water over 24 h. Couple the same day.

#### References

Matsumoto I, Mizuno Y, Seno N (1980) *J. Chromatogr.* 188:457. Sundberg L,
Porath J (1974) *J. Chromatogr.* 90:87. Hermanson (2013) Ch. 15.3.4.

---

### J.1.3  Hydroxyl Activation — BDDE (1,4-butanediol diglycidyl ether, "bisoxirane")

**Purpose:** Activate -OH with a bifunctional epoxide. Adds a 12-atom
flexible spacer in the same step. The free end couples to amine / thiol /
hydroxyl ligands. Milder than epichlorohydrin, no halogen.

**Evidence tier:** `semi_quantitative`

**DPSim M2 key:** `bdge_activation` for the built-in diglycidyl-ether
activation profile. If the exact vendor reagent differs from BDGE/BDDE,
record it in the recipe notes and calibration metadata.

**Based on:** Sundberg & Porath (*J. Chromatogr.* 1974, 90:87); Hermanson Ch. 15.3.5.

#### Safety

- GHS pictograms: exclamation mark, health hazard.
- H-codes: H315 (skin irritant), H319 (eye irritant), H317 (skin sensitiser).
- Not a carcinogen in the epichlorohydrin sense, but a known sensitiser —
  repeated exposure causes contact dermatitis.
- PPE: nitrile gloves, safety glasses, lab coat. Fume hood recommended.
- Waste: non-halogenated organic-aqueous stream.

#### What you need (per 10 mL wet gel)

| Reagent | Amount | CAS | Storage |
|---|---|---|---|
| BDDE | 1 mL | 2425-79-8 | 4 °C, tightly capped |
| 0.6 M NaOH | 10 mL | 1310-73-2 | RT |
| NaBH₄ | 20 mg | 16940-66-2 | Desiccator |

#### Procedure

1. PPE on. Fume hood recommended but not mandatory.
2. Drain 10 mL wet gel on the sintered funnel, wash with 5 × 30 mL water.
3. Transfer to a 50 mL tube. Add 10 mL 0.6 M NaOH and 20 mg NaBH₄.
4. Add 1 mL BDDE. Cap, invert 10 times.
5. Rotate at 25 °C (RT), 8 h (or overnight).
6. Wash with 10 × 30 mL water, then 3 × 30 mL acetone (to remove unreacted
   BDDE), then 3 × 30 mL water.
7. Drain to damp cake. Ready for coupling (§J.2.2).

#### Quality control

- Epoxide density: 10-20 μmol/mL wet gel (lower than epichlorohydrin but
  steric access is better thanks to the spacer).

#### Troubleshooting

- **Low density:** NaOH too dilute or too cold. Verify NaOH concentration
  with a standard HCl titration.
- **Two-sided crosslinking (gel shrinks):** too much BDDE relative to matrix.
  Halve the BDDE next time.

#### References

Sundberg & Porath (1974) *J. Chromatogr.* 90:87. Hermanson (2013) Ch. 15.3.5.

---

### J.1.4  Hydroxyl Activation — DVS (divinyl sulfone)

**Purpose:** Activate -OH with a vinyl sulfone. Reacts via Michael addition
with amines (fast at pH 9-11), thiols (fast at pH 7-9), and hydroxyls
(slow, pH 10-12). One-step coupling from vinyl sulfone.

**Evidence tier:** `semi_quantitative`

**DPSim M2 key:** `dvs_activation`. Protein A coupling to this activated
site is represented by `protein_a_vs_coupling`; generic ligand-specific DVS
couplings require local assay support.

**Based on:** Porath et al. (*J. Chromatogr.* 1975, 103:49); Mateo et al.
(*Enzyme Microb. Technol.* 2007, 39:274); Hermanson Ch. 15.3.6.

#### Safety

- GHS pictograms: skull-and-crossbones, corrosive, health hazard.
- H-codes: H300 (fatal if swallowed), H330 (fatal if inhaled), H314 (severe
  burns), H317 (strong skin sensitiser — a small repeated exposure can
  produce a persistent allergy).
- PPE: double nitrile gloves (change hourly), face shield, chemical apron,
  lab coat. Fume hood mandatory.
- DVS is volatile. Keep tightly capped. Do not weigh on an open balance
  outside the hood.
- Waste: non-halogenated organic-aqueous. Before disposal, quench by adding
  excess ethanolamine (1 M) and letting stand ≥ 4 h.

#### What you need (per 10 mL wet gel)

| Reagent | Amount | CAS | Storage |
|---|---|---|---|
| DVS | 1 mL | 77-77-0 | 4 °C, ampoule |
| 0.5 M Na₂CO₃ pH 11 | 10 mL | — | RT (freshly prepared) |

#### Procedure

1. PPE on. Fume hood sash at working height.
2. Drain 10 mL wet gel, wash with 5 × 30 mL water, then 2 × 30 mL 0.5 M Na₂CO₃.
3. Transfer to a 50 mL tube. Add 10 mL 0.5 M Na₂CO₃ pH 11.
4. In the hood, add 1 mL DVS dropwise via 1 mL serological pipette. Cap.
5. Rotate end-over-end at RT, 70 min. Exact time matters — over-activation
   produces crosslinks that reduce coupling density.
6. Wash rapidly with 10 × 30 mL water on the sintered funnel. Drain damp.
7. Gel is now vinyl-sulfone activated. Proceed to coupling (§J.2.3) within
   30 minutes — activated sites hydrolyse over hours at neutral pH.

#### Quality control

- Vinyl-sulfone density: 20-40 μmol/mL wet gel (titrate by reaction with
  excess cysteine, then quantify free thiol with Ellman's reagent; Hermanson
  Ch. 15.3.6 details).

#### Troubleshooting

- **Gel crosslinks / shrinks during activation:** DVS concentration too high
  or reaction time too long. Reduce DVS to 0.5 mL and time to 60 min.
- **Coupling fails:** activated gel was stored > 30 min before use. Plan
  ligand to be ready before starting activation.

#### References

Porath J, Låås T, Janson J-C (1975) *J. Chromatogr.* 103:49. Mateo C et al.
(2007) *Enzyme Microb. Technol.* 39:274. Hermanson (2013) Ch. 15.3.6.

---

### J.1.5  Hydroxyl Activation — CDI (1,1'-carbonyldiimidazole)

**Purpose:** Activate -OH to an imidazole carbamate. Couples primary amines
at pH 9-10 forming a stable N-alkyl carbamate. Milder than CNBr, no charged
isourea. Good for charge-sensitive ligands.

**Evidence tier:** `validated_quantitative`

**DPSim M2 key:** not implemented as a quantitative built-in profile. Treat
CDI activation as an external operation unless a calibrated `ReagentProfile`
is added.

**Based on:** Hearn (*Meth. Enzymol.* 1987, 135:102); Bethell et al.
(*J. Biol. Chem.* 1979, 254:2572); Hermanson Ch. 15.3.2.

#### Safety

- GHS pictograms: exclamation mark.
- H-codes: H315 (skin irritant), H319 (eye irritant), H335 (respiratory
  irritant). No CMR classification.
- PPE: nitrile gloves, safety glasses, lab coat. Fume hood recommended for
  powder weighing.
- CDI is moisture-sensitive. Store tightly capped in a desiccator. Weigh
  quickly.
- Waste: non-halogenated organic-aqueous.

#### What you need (per 10 mL wet gel)

| Reagent | Amount | CAS | Storage |
|---|---|---|---|
| CDI | 200 mg | 530-62-1 | –20 °C, desiccated |
| Anhydrous acetone | 30 mL | 67-64-1 | RT, over molecular sieves |
| Anhydrous dioxane | 30 mL | 123-91-1 | RT; peroxide-tested within 12 months |

#### Procedure

1. PPE on.
2. Drain 10 mL wet gel on the sintered funnel. Wash with 5 × 30 mL water,
   then dehydrate with an acetone gradient: 2 × 30 mL 30 % acetone, 2 × 30 mL
   60 % acetone, 3 × 30 mL 100 % acetone, 2 × 30 mL anhydrous acetone, then
   2 × 30 mL anhydrous dioxane. **This step is essential: CDI hydrolyses
   instantly in water.** The gel must be in a water-free solvent.
4. Transfer drained dioxane-exchanged gel to a 50 mL tube. Add 10 mL
   anhydrous dioxane.
5. Add 200 mg CDI (weigh in the fume hood, transfer quickly).
6. Rotate at RT, 30-60 min. CO₂ evolves visibly (small bubbles).
7. Wash with 5 × 30 mL anhydrous dioxane, then reverse the gradient back to
   water: 2 × 30 mL 100 % acetone, 2 × 30 mL 60 % acetone, 2 × 30 mL 30 %
   acetone, 2 × 30 mL water.
8. The gel is now imidazole-carbamate-activated. Proceed to coupling (§J.2).

#### Quality control

- Activation density: 20-80 μmol/mL wet gel (titrate by release of imidazole
  at 280 nm after reaction with excess glycine).

#### Troubleshooting

- **Almost no activation:** gel was not fully dehydrated. Check the gradient
  wash step; the last acetone wash should pour off clear and the gel should
  be visibly less swollen.
- **Gel shrinks catastrophically:** rapid dehydration. Slow the acetone
  gradient next time (smaller steps).

#### References

Hearn MTW (1987) *Meth. Enzymol.* 135:102. Bethell GS, Ayers JS, Hancock WS,
Hearn MTW (1979) *J. Biol. Chem.* 254:2572. Hermanson (2013) Ch. 15.3.2.

---

### J.1.6  Hydroxyl Activation — Tresyl chloride (2,2,2-trifluoroethanesulfonyl chloride)

**Purpose:** Activate -OH to a tresyl ester. Couples primary amines under
very mild conditions (pH 7-9, RT). The linkage is a secondary amine with
no charge. Ideal for labile / charge-sensitive proteins.

**Evidence tier:** `semi_quantitative`

**DPSim M2 key:** not implemented as a quantitative built-in profile. Treat
tresyl activation as external evidence unless local calibration is ingested.

**Based on:** Nilsson & Mosbach (*Meth. Enzymol.* 1984, 104:56); Hermanson
Ch. 15.3.3.

#### Safety

- GHS pictograms: corrosive, exclamation mark.
- H-codes: H314 (severe burns), H335 (respiratory irritant), H330 (fatal
  if inhaled — mainly from the HCl it releases on hydrolysis).
- PPE: double nitrile gloves, face shield, chemical apron, lab coat. Fume
  hood mandatory.
- Store under dry argon or nitrogen. Reacts violently with water.
- Waste: halogenated organic-aqueous. Neutralise aqueous rinses with solid
  sodium bicarbonate before pooling.

#### What you need (per 10 mL wet gel)

| Reagent | Amount | CAS | Storage |
|---|---|---|---|
| Tresyl chloride | 100 μL | 1648-99-3 | 4 °C, under dry inert gas |
| Anhydrous acetone | 30 mL | 67-64-1 | RT, over sieves |
| Pyridine | 100 μL | 110-86-1 | RT (peroxide-tested) |

#### Procedure

1. PPE on. Fume hood mandatory.
2. Dehydrate 10 mL wet gel through an acetone gradient (as in §J.1.5 steps
   2-3) ending in anhydrous acetone.
3. Transfer dehydrated gel to a 50 mL tube with 10 mL anhydrous acetone.
4. Add 100 μL pyridine (acid scavenger), then 100 μL tresyl chloride dropwise
   in the hood with gentle swirling.
5. Rotate at 0-4 °C (on ice), 10 min.
6. Wash in the funnel: 5 × 30 mL ice-cold acetone (not water — hydrolysis),
   then 5 × 30 mL ice-cold 1 mM HCl, then 3 × 30 mL cold coupling buffer.
7. Proceed to coupling (§J.2) immediately. Tresyl-activated matrix has a
   half-life of ≈ 1 h at 4 °C, pH 7.

#### Quality control

- Activation density: 10-30 μmol/mL wet gel (approximated from subsequent
  amine coupling yield; direct titration is difficult).

#### Troubleshooting

- **Very low coupling yield:** tresyl chloride bottle was opened before. It
  absorbs moisture rapidly. Use a fresh ampoule.
- **Gel turns yellow:** pyridine is discoloured (old). Use fresh pyridine.

#### References

Nilsson K, Mosbach K (1984) *Meth. Enzymol.* 104:56. Hermanson (2013) Ch. 15.3.3.

---

### J.1.7  Hydroxyl Activation — STMP (Sodium Trimetaphosphate, triggerable dual-network)

**Purpose:** Crosslink **both** agarose hydroxyls (dominant, phosphate diester)
and chitosan primary amines (secondary, phosphoramide) in the *same* bead, in a
thermally- and pH-triggerable two-phase reaction. Phase A loads STMP into the
pre-gelled bead at 4 °C / pH 7 (no reaction). Phase B raises to 60 °C / pH 11
and the ring-opened trimetaphosphate crosslinks the polymer networks. The
two-phase design gives a uniform radial crosslink profile (Thiele modulus ~0.35
for a 250 µm bead radius) — the "dip in acid TPP" ionic-gelation approach gives
a skin-core structure instead.

**Do not confuse STMP with STPP.** Sodium **Tri**metaphosphate (STMP,
Na₃P₃O₉, CAS **7785-84-4**) is the *cyclic* trimer used here — covalent,
alkaline pH, triggerable. Sodium **Tripolyphosphate** (STPP, Na₅P₃O₁₀, CAS
7758-29-4) is the *linear* ionic crosslinker in DPSim's `tpp` entry —
different chemistry, different pH window, reversible. Check the CAS on every
reagent bottle before you weigh anything.

**Evidence tier:** `semi_quantitative` unless local STMP conversion,
phosphate content, and modulus data are ingested. Literature supports the
directional chemistry, but matrix lot, pH history, bead size, and washout
strongly affect the practical conversion.

**DPSim M2 key:** `stmp_secondary` for secondary reinforcement. Legacy M1/L3
crosslinker selection may expose an STMP option for primary network modeling,
but lifecycle M2 recipes should use the `ProcessRecipe` step key above.

**Based on:** Lim & Seib (*Cereal Chem.* 1993, 70:137); Kasemsuwan & Jane
(*Cereal Chem.* 1996, 73:702); Lack et al. (*Carbohydr. Res.* 2004, 339:2391);
Seal (*Biomaterials* 1996, 17:1869); Salata et al. (*Int. J. Biol. Macromol.*
2015, 81:1009); SA-DPSIM-XL-002 Rev 0.1.

#### Safety

- GHS pictograms: exclamation mark (mild irritant). Food-grade additive E452.
- H-codes: H315 (skin irritation), H319 (eye irritation). No acute-toxicity
  or carcinogenicity codes.
- PPE: single nitrile gloves, safety glasses, lab coat. Bench work is fine;
  fume hood not required for STMP itself, but Phase B uses NaOH/Na₂CO₃
  (corrosive) — wear a face shield when pipetting the pH 11 buffer hot.
- Waste: aqueous-neutral after quenching with HCl. Dispose as non-halogenated
  aqueous waste. The quenched solution contains orthophosphate — if your
  institution caps phosphate discharge, collect for chemical waste instead.

#### What you need (per 10 mL wet gel)

| Reagent | Amount | CAS | Storage |
|---|---|---|---|
| Sodium trimetaphosphate (Na₃P₃O₉) | 200 mg | 7785-84-4 | RT, dry |
| 0.1 M HEPES pH 7.0 | 20 mL | 7365-45-9 | 4 °C (freshly prepared) |
| 0.5 M Na₂CO₃ + 0.5 M NaOH pH 11.0 | 15 mL | 497-19-8 / 1310-73-2 | RT (freshly prepared, ≤ 4 h) |
| 0.1 M HCl (ice-cold) | 20 mL | 7647-01-0 | 4 °C |
| 10 mM EDTA pH 8 (wash) | 15 mL | 60-00-4 | RT |

#### Procedure

1. PPE on. Bench work.
2. Drain 10 mL wet gel on a sintered funnel, wash with 3 × 20 mL water.
3. **Phase A — cold loading.** Transfer gel into a 50 mL tube. Add 10 mL
   cold 0.1 M HEPES pH 7.0 and dissolve 200 mg STMP in the tube
   (final 2 % w/v). Rotate end-over-end at 4 °C, 30 min. Expected state:
   STMP is uniformly distributed throughout the bead volume; negligible
   reaction has occurred (pH 7, 4 °C).
4. Drain quickly on the sintered funnel. Do **not** wash at this stage —
   washing removes the uniformly-loaded STMP.
5. **Phase B — hot alkaline activation.** Pre-warm 15 mL 0.5 M Na₂CO₃ +
   0.5 M NaOH pH 11.0 buffer to 60 °C in a water bath. Transfer gel into
   the warm buffer. Rotate end-over-end in a 60 °C incubator, 2 h.
   Exact time matters — over-activation produces a brittle gel.
6. **Phase C — quench + wash.** Transfer gel into 20 mL ice-cold 0.1 M HCl
   on the sintered funnel (drops local pH to ~4, terminates phosphoramide
   formation). Wait 2 min. Then wash: 10 × 20 mL water (drain between each);
   3 × 20 mL 10 mM EDTA pH 8 (strips phosphate-chelated metals); 5 × 20 mL
   water. Drain damp.
7. Gel is now phosphate-diester crosslinked. Store in 20 % ethanol / 0.1 M
   NaCl pH 7 at 4 °C. Use within 3 months.

#### Quality control

- Bulk phosphorus (ICP-OES after acid digestion of a dried 10 mg aliquot):
  1.5–3.5 mmol P / g dry matrix (≈ 5–10 % crosslink conversion).
- FTIR (ATR, dried powder): P=O stretch at 1230 cm⁻¹ and P-O-C ester band
  at 990 cm⁻¹ both present.
- Equilibrium swelling (water, 24 h): ratio drops 20–40 % vs. uncrosslinked
  control from the same lot.
- Storage modulus (DMA, 1 Hz, swollen bead): 2–5× increase vs. control.

#### Troubleshooting

- **Skin-core structure (brittle outer shell, soft centre):** bead radius
  too large for the Phase B time. STMP is homogeneous for `d50/2 < 500 µm`
  (Thiele modulus < 1). If your L1 output shows d50/2 > 500 µm, either
  reduce bead size (raise rpm or add surfactant in L1) or shorten Phase B
  to 60 min and compensate with a second STMP cycle.
- **Gel melts / liquefies during Phase B:** temperature exceeded 80 °C
  or pH exceeded 12. Agarose double-helix is hydrolysed above these
  thresholds. Re-run with thermometer-verified 60 °C and a freshly
  pH-calibrated buffer. Do not exceed 70 °C without a pilot-scale
  validation of your specific matrix.
- **No measurable crosslinking (FTIR P-bands absent):** Phase A was
  too long (≥ 2 h) and the STMP reacted at pH 7 before transfer; or
  Phase B buffer drifted below pH 10. Freshly prepare both buffers on
  the day of use and keep Phase A at or below 30 min.
- **Downstream IMAC column loses metal:** unwashed phosphate residues
  chelate the loading ion. Extend the EDTA wash to 5 × 20 mL before
  metal charging.
- **The M1 UI shows `STMP homogeneity window exceeded` warning after
  the run:** d50/2 > 500 µm; see the skin-core entry above. The
  simulation result is still valid; the warning flags that the
  homogeneity assumption behind the kinetic fit may not hold.

#### References

Lim S, Seib PA (1993) *Cereal Chem.* 70:137. Kasemsuwan T, Jane J (1996)
*Cereal Chem.* 73:702. Lack S, Dulong V, Picton L, Le Cerf D, Condamine E
(2004) *Carbohydr. Res.* 339:2391. Seal BL (1996) *Biomaterials* 17:1869.
Salata GC, Kim JH, Chen C-H, McClements DJ (2015) *Int. J. Biol. Macromol.*
81:1009. Van Wazer JR (1958) *Phosphorus and its Compounds*, vol. I.

---

### J.1.8  ACS Conversion — Cyanuric chloride (3-stage triazine substitution)

**Purpose:** Activate matrix -OH to a dichlorotriazine handle, then
sequentially substitute the remaining 2 Cl atoms — typically the second
with a small ligand (dye, amine) and the third with a glycine quench.
Canonical chemistry for Reactive Blue 2 / Procion Red HE-3B affinity
supports.

**Evidence tier:** `semi_quantitative` (per-stage rate constants are
literature-anchored, not locally calibrated).

**DPSim M2 key:** `cyanuric_chloride_activation`. v0.5.1 ships per-stage
`(k_forward, E_a)` tuples on `ReagentProfile.staged_kinetics` and
`ModificationStep.temperature_stage` (1-based) selects the active stage.
`temperature_stage=0` falls back to base k_forward.

**Based on:** Korpela & Mäntsälä (1968) *Anal. Biochem.* 23:381; Lowe &
Pearson (1984) *Methods Enzymol.* 104:97; Hermanson Ch. 15.5.

#### Safety — READ BEFORE HANDLING

- GHS pictograms: corrosive, exclamation mark, environmental hazard.
- H-codes: H302 (harmful if swallowed), H314 (severe burns), H335
  (respiratory irritant), H410 (very toxic to aquatic life).
- PPE: nitrile gloves (double), face shield, chemical apron, lab coat.
  Fume hood mandatory.
- Reacts violently with water → HCl release. Store under dry argon or
  nitrogen; weigh quickly in the hood.
- Waste: chlorinated organic-aqueous; neutralise rinses with solid
  NaHCO₃ before pooling.

#### What you need (per 10 mL wet gel)

| Reagent | Amount | CAS | Storage |
|---|---|---|---|
| Cyanuric chloride (TCT) | 100–500 mg | 108-77-0 | 4 °C, dry, in dark |
| Anhydrous acetone | 30 mL | 67-64-1 | Over molecular sieves |
| Reactive dye (e.g. Cibacron Blue F3GA) | 50 mg | 12236-82-7 | 4 °C, dark |
| Glycine | 200 mg | 56-40-6 | RT |

#### Procedure (3-stage)

**Stage 1 — install dichlorotriazine handle (1st Cl, 0–5 °C, k≈3×10⁻³).**

1. PPE on. Fume hood mandatory.
2. Dehydrate 10 mL wet gel through an acetone gradient (water → 30 % →
   60 % → 100 % → anhydrous acetone, 30 mL each).
3. Weigh 100–500 mg cyanuric chloride into a separate vial **in the
   hood**. Dissolve in 5 mL ice-cold anhydrous acetone.
4. Pour the dissolved TCT onto the dehydrated gel. Add 0.5 M Na₂CO₃
   dropwise (~1 mL) to keep pH 9–10 as HCl is released.
5. Rotate at 0–5 °C (ice bath), 30 min. Solution will turn pale yellow
   as the dichlorotriazine accumulates.
6. Wash with 5 × 30 mL ice-cold acetone, then 5 × 30 mL ice-cold water
   to remove unreacted TCT. **Step 1 product: dichlorotriazine-loaded
   matrix; surface this in the simulator with `temperature_stage=1`.**

**Stage 2 — couple ligand (2nd Cl, 25 °C, k≈3×10⁻⁴).**

7. Suspend the dichlorotriazine matrix in 10 mL pH 10.0 buffer (0.1 M
   carbonate). Add the dye (50 mg) or amine ligand pre-dissolved in 5
   mL of the same buffer.
8. Rotate at 25 °C, 2 h. (For dyes, monitor A_λ_max of the supernatant;
   uptake plateaus when the second Cl is consumed.)
9. Wash with 5 × 30 mL water, then 5 × 30 mL 1 M NaCl, then 5 × 30 mL
   water. Salt washes remove non-covalently adsorbed dye. **Step 2
   product: monochlorotriazine-loaded ligand support; simulator
   `temperature_stage=2`.**

**Stage 3 — quench remaining Cl (3rd Cl, 60–80 °C, k≈3×10⁻⁵).**

10. Add 200 mg glycine in 10 mL pH 9.0 carbonate buffer.
11. Rotate at 60 °C (water bath), 4 h. Glycine consumes the third Cl,
    converting it to a neutral N-glycyl bond.
12. Wash with 5 × 30 mL water, store in 20 % ethanol at 4 °C. **Step 3
    product: fully substituted triazine-dye support; simulator
    `temperature_stage=3`.**

#### Quality control

- Dye loading: 5–20 µmol/mL wet gel (UV at λ_max in supernatant before
  vs after coupling).
- Cl content (ion chromatography of an HF/HClO₄ digest of 10 mg dry
  matrix): < 0.1 % residual Cl after Stage 3 (any > 0.5 % indicates
  incomplete glycine quench).

#### Troubleshooting

- **Dye washes off in salt rinse:** Stage 2 reaction did not run long
  enough. Re-couple at 25 °C for 4–6 h, monitoring A_λ_max plateau.
- **Stage 3 leaves residual Cl:** scale up the glycine to 1 M, hold at
  80 °C, 6 h. Verify by Cl content < 0.1 %.
- **Yellow / brown discolouration after Stage 1:** TCT was older than ~3
  months, partially hydrolysed. Use a fresh, sealed bottle.

#### References

Korpela TK, Mäntsälä P (1968) *Anal. Biochem.* 23:381. Lowe CR, Pearson
JC (1984) *Methods Enzymol.* 104:97. Hermanson (2013) Ch. 15.5.

---

### J.1.9  ACS Conversion — Glyoxyl-chained (glycidol → periodate → multipoint Lys)

**Purpose:** Install glyoxyl (-CH₂-CHO) groups uniformly across the matrix
surface, enabling **multipoint covalent immobilisation** of enzymes via
several Lys residues simultaneously. Multipoint anchoring uplifts T_50
by 10–20 °C versus single-point coupling — the canonical chemistry for
industrial lipase, penicillin-G acylase, and CALB.

**Evidence tier:** `semi_quantitative`.

**DPSim M2 key:** `glyoxyl_chained_activation`. Carries
`aldehyde_multiplier=2.0` (Malaprade cleavage produces 2 aldehydes per
diol pair) and chain-scission penalty (threshold 0.40, max G_DN loss
0.50).

**Based on:** Mateo C et al. (2007) *Biotechnol. Bioeng.* 96:5; Pessela
BCC et al. (2003) *Enzyme Microb. Technol.* 33:199; Guisán JM (1988)
*Enzyme Microb. Technol.* 10:375.

#### Safety

- Glycidol (CAS 556-52-5): suspected carcinogen (H351), skin/eye
  irritant. PPE: nitrile gloves, safety glasses, fume hood.
- Sodium periodate (CAS 7790-28-5): strong oxidiser (H272), skin/eye
  irritant (H315/H319). Avoid contact with reducing agents. Light-
  sensitive — keep in dark.
- Sodium borohydride (CAS 16940-66-2): flammable, water-reactive (H260),
  hydrogen evolution. Use in well-ventilated hood; quench excess with
  ice-cold water in a metal beaker, never glass.
- Waste: separate organic glycidol waste from aqueous periodate; reduce
  any periodate residues with sodium thiosulfate before disposal.

#### What you need (per 10 mL wet gel)

| Reagent | Amount | CAS | Storage |
|---|---|---|---|
| Glycidol | 1 mL | 556-52-5 | 4 °C, dark |
| Sodium hydroxide | 0.4 g | 1310-73-2 | RT, dry |
| Sodium periodate | 100 mg (5 mM) | 7790-28-5 | RT, dark |
| Sodium borohydride | 50 mg | 16940-66-2 | Desiccated, –20 °C |
| 0.1 M sodium bicarbonate, pH 10 | 50 mL | — | 4 °C |
| 25 mM acetate, pH 5 | 50 mL | — | 4 °C |

#### Procedure (16 h overnight + 2 h + 2 h reduction)

1. PPE on.
2. **Glycidol etherification (Step 1, 16 h, pH 11).** Suspend 10 mL wet
   gel in 10 mL water + 0.4 g NaOH (final ~0.5 M). Add 1 mL glycidol
   dropwise with stirring. Rotate at RT, 16 h. The matrix now bears
   1,2-diol-terminated glyceryl ether tethers.
3. Wash with 5 × 30 mL water until pH < 8.5.
4. **Periodate oxidation (Step 2, 2 h, pH 5).** Suspend in 30 mL of 25
   mM acetate buffer pH 5. Add 100 mg NaIO₄ (5 mM final). Cover with
   foil (light-sensitive). Rotate at 4 °C, 2 h. Cleaves vicinal diols
   to glyoxyl (-CH₂-CHO).
5. Wash with 5 × 30 mL water, then 5 × 30 mL of pH 10 carbonate. The
   matrix is now glyoxyl-activated; surface in the simulator as
   `product_acs=GLYOXYL`.
6. **Multipoint Lys coupling (pH 10, 24 h, 25 °C).** Add the enzyme
   solution (1–10 mg/mL in pH 10 carbonate). Rotate at 25 °C, 24 h. At
   pH 10, multiple deprotonated lysine ε-amines anchor simultaneously
   to glyoxyl groups, forming Schiff bases.
7. **NaBH₄ reductive lock-in (Step 4, 2 h).** **MANDATORY for any resin
   intended for CIP cleaning.** Add 50 mg NaBH₄. Rotate at 4 °C, 2 h
   (gentle hydrogen evolution; vent the cap). Reduces the Schiff bases
   to stable secondary amines, locking the multipoint anchors.
8. Wash with 5 × 30 mL pH 8 phosphate, then store in 20 % ethanol at
   4 °C.

#### Quality control

- Glyoxyl density: 50–200 µmol/mL wet gel (titrate with hydroxylamine
  hydrochloride, back-titrate the released HCl with 0.1 M NaOH).
- Multipoint anchor count: T_50 thermal-deactivation assay; expect 5
  + 5 × n_anchors °C uplift versus single-point coupling.
- Residual aldehyde after NaBH₄: < 5 µmol/mL by Schiff-base TNBS assay.

#### Troubleshooting

- **Bead becomes very soft / fragments after Step 2:** periodate dose or
  time too high. Drop NaIO₄ to 2 mM, time to 30 min. The simulator's
  v0.5.1 chain-scission penalty triggers above 40 % conversion.
- **No T_50 uplift versus single-point reference:** glycidol step
  incomplete (insufficient -OH coverage of glyceryl ether). Extend Step
  1 to 24 h; verify diol density before Step 2.
- **Enzyme washes off after a few CIP cycles:** Step 4 NaBH₄ skipped
  or under-dosed. Repeat with 100 mg NaBH₄, 4 h.

#### References

Guisán JM (1988) *Enzyme Microb. Technol.* 10:375. Mateo C, Palomo JM,
Fernandez-Lorente G, Guisán JM, Fernandez-Lafuente R (2007) *Biotechnol.
Bioeng.* 96:5. Pessela BCC, Mateo C, Fuentes M, Vian A, García JL,
Carrascosa AV, Guisán JM, Fernández-Lafuente R (2003) *Enzyme Microb.
Technol.* 33:199.

---

### J.1.10  ACS Conversion — Periodate-direct (vicinal-diol → aldehyde, Malaprade)

**Purpose:** Cleave vicinal cis-diols on diol-rich polysaccharides
(dextran, amylose, pullulan, starch, hyaluronate) directly to aldehyde
pairs. Foundational route for hydrazide / aminooxy / amine + NaBH₃CN
coupling and for oxidised-glycoprotein workflows.

**Evidence tier:** `semi_quantitative`.

**DPSim M2 key:** `periodate_oxidation`. Carries `aldehyde_multiplier=2.0`
(one diol pair → two aldehydes — the v0.5.0 fix for the prior 1:1
under-counting) and chain-scission penalty (threshold 0.30, max G_DN
loss 0.70).

**Based on:** Bobbitt JM (1956) *Adv. Carbohydr. Chem.* 11:1; Malaprade
L (1928) *Bull. Soc. Chim. Fr.* 43:683; Painter T, Larsen B (1973) *Acta
Chem. Scand.* 27:1957.

#### Safety

- Sodium periodate (CAS 7790-28-5): strong oxidiser (H272), skin/eye
  irritant. Light-sensitive — store in dark. Keep separate from
  reducing agents and organic solvents.
- Hydrazide ligands (e.g. ADH, CAS 1071-93-8): low hazard; H315
  (skin irritation).
- Waste: reduce residual periodate with sodium thiosulfate before
  disposal.

#### What you need (per 10 mL wet diol-rich gel)

| Reagent | Amount | CAS | Storage |
|---|---|---|---|
| Sodium periodate | 5–20 mM (50–200 mg) | 7790-28-5 | RT, dark |
| 25 mM acetate, pH 5 | 30 mL | — | 4 °C |
| Adipic acid dihydrazide (ADH) — typical capture | 200 mg | 1071-93-8 | RT |
| Sodium cyanoborohydride | 50 mg (optional reductive cap) | 25895-60-7 | Desiccated, –20 °C |

#### Procedure

1. PPE on. Fume hood for periodate weighing.
2. Suspend 10 mL wet gel in 30 mL acetate buffer pH 5.
3. Add NaIO₄ to 5 mM (50 mg). For dose-response work, vary 2–20 mM.
4. Cover with foil. Rotate at 4 °C, 1–2 h. **Do not exceed 30 % diol
   conversion** if the bead's mechanical integrity matters — see the
   v0.5.1 chain-scission penalty in §6.1.3 of the manual.
5. Quench with sodium thiosulfate (100 mg) for 5 min to consume residual
   IO₄⁻.
6. Wash with 5 × 30 mL cold water until A_232 of the eluate is < 0.05.
7. **Couple a hydrazide / aminooxy / amine ligand within 30 min** (the
   support's aldehyde reactivity decays slowly but the surface adsorbs
   atmospheric amines).
8. Optional: reduce the resulting Schiff bases / hydrazones with NaBH₃CN
   (50 mg, 2 h, pH 7) to lock the linkage permanently.

#### Quality control

- Aldehyde density: 20–100 µmol/mL wet gel (TNBS Schiff-base titration
  or hydroxylamine back-titration).
- Chain scission: monitor uronic-acid release into supernatant by
  carbazole assay. Above 30 % conversion, scission progresses
  monotonically.

#### Troubleshooting

- **Bead loses pressure tolerance:** scission penalty has triggered.
  Drop NaIO₄ to 2–5 mM and time to 30 min.
- **Subsequent hydrazone hydrolyses at low pH:** stabilise with NaBH₃CN
  reduction (Step 8) — converts the labile hydrazone into a stable
  alkylhydrazide.
- **Inconsistent batch-to-batch oxidation:** NaIO₄ photolyses on
  storage; verify with KI/starch assay before use, or use a fresh
  ampoule.

#### References

Malaprade L (1928) *Bull. Soc. Chim. Fr.* 43:683. Bobbitt JM (1956)
*Adv. Carbohydr. Chem.* 11:1. Painter T, Larsen B (1973) *Acta Chem.
Scand.* 27:1957. Hermanson (2013) Ch. 2.5, 19.

---

## J.2 Ligand Coupling

Attach a small-molecule ligand (dye, inhibitor, cofactor, peptide) to the
activated matrix. Select the protocol that matches the activation chemistry
you used in §J.1. The five common strategies covered here, plus click
chemistry for advanced users.

---

### J.2.1  Ligand Coupling — amine on CNBr- or CDI-activated matrix

**Purpose:** Couple a primary-amine-bearing ligand (e.g., peptide, amino
acid, aminated dye) to a CNBr-activated (§J.1.1) or CDI-activated (§J.1.5)
matrix. Forms an isourea (CNBr) or N-alkyl carbamate (CDI) linkage.

**Evidence tier:** `validated_quantitative`

**DPSim M2 key:** no generic CNBr/CDI amine-coupling profile is implemented.
For implemented epoxide ligand routes, use ligand-specific keys such as
`deae_coupling`, `q_coupling`, `cm_coupling`, `protein_a_coupling`, or
`protein_g_coupling`.

**Based on:** Cuatrecasas & Anfinsen (*Annu. Rev. Biochem.* 1971, 40:259);
Hermanson Ch. 16.2.

#### Safety

- GHS pictograms: none intrinsic beyond reagent-specific (the activated gel
  carries the CNBr / CDI inherited hazard until quenched).
- PPE: nitrile gloves, safety glasses, lab coat. Fume hood if the activation
  was CNBr-based.
- Waste: aqueous with trace activator — into the activator's waste stream.

#### What you need (per 10 mL activated wet gel)

| Reagent | Amount | Notes |
|---|---|---|
| Ligand (amine-bearing) | 2-20 μmol per mL wet gel target | In coupling buffer |
| Coupling buffer: 0.1 M NaHCO₃, 0.5 M NaCl, pH 8.3 | 20 mL | Freshly prepared |

#### Procedure

1. Dissolve the ligand in coupling buffer at 2-10 mg/mL. Adjust pH to 8.3
   with 1 M NaOH or 1 M HCl. Filter 0.22 μm if the ligand is clean enough.
2. Combine 10 mL activated wet gel (drained damp) with 20 mL ligand solution
   in a 50 mL tube.
3. Rotate end-over-end at 4 °C overnight (16 h) OR at RT for 2 h.
4. Drain on the sintered funnel, save the filtrate for coupling-yield
   analysis (measure ligand A₂₈₀ or your ligand's signal).
5. Wash with 3 × 30 mL coupling buffer.
6. Quench unreacted activated sites (§J.8.1). **This is critical.**

#### Quality control

- Coupling yield: compare ligand concentration in pre- and post-coupling
  solutions. 60-95 % incorporation is typical.
- Ligand density: (ligand added – ligand in wash) / gel volume.

#### Troubleshooting

- **< 30 % coupling:** ligand concentration too low, or pH drifted down.
  Verify pH at the start of coupling and at 1 h in.
- **Ligand activity lost:** check for non-specific adsorption by running a
  control coupling to an unreacted (non-activated) matrix; the ligand should
  wash off.

#### References

Cuatrecasas P, Anfinsen CB (1971) *Annu. Rev. Biochem.* 40:259. Hermanson (2013) Ch. 16.2.

---

### J.2.2  Ligand Coupling — amine / thiol / hydroxyl on epoxide matrix

**Purpose:** Couple ligands to an epoxide-activated matrix (from
epichlorohydrin §J.1.2 or BDDE §J.1.3). Epoxides react with amines (pH
9-11), thiols (pH 8-9), or hydroxyls (pH 11-12, slow).

**Evidence tier:** `validated_quantitative` for amine/thiol coupling;
`semi_quantitative` for hydroxyl coupling.

**DPSim M2 key:** use the ligand-specific epoxide key, for example
`protein_a_coupling`, `protein_g_coupling`, `deae_coupling`, `q_coupling`,
`cm_coupling`, `phenyl_coupling`, `sp_coupling`, `nta_coupling`, or
`ida_coupling`.

**Based on:** Mateo et al. (*Enzyme Microb. Technol.* 2007, 39:274);
Hermanson Ch. 16.4.

#### Safety

- PPE: nitrile gloves, safety glasses, lab coat.
- Waste: aqueous organic. Residual epoxide gets quenched in §J.8.2.

#### What you need (per 10 mL epoxide-activated wet gel)

| Reagent | Amount | Notes |
|---|---|---|
| Ligand | 5-50 μmol target | For amines, in 20 mL 0.5 M Na₂CO₃ pH 10. For thiols, in 20 mL 0.1 M Na phosphate pH 8.5 with 1 mM EDTA. |

#### Procedure (amine ligand)

1. Dissolve ligand in 0.5 M Na₂CO₃ pH 10 at 2-10 mg/mL.
2. Combine 10 mL activated wet gel with 20 mL ligand solution.
3. Rotate at 25 °C, 16-24 h (amine+epoxide is slow). For heat-sensitive
   ligands, extend to 48 h at RT.
4. Wash with 3 × 30 mL coupling buffer, 3 × 30 mL water.
5. Quench (§J.8.2).

#### Procedure (thiol ligand)

1. Dissolve thiolated ligand in 0.1 M Na phosphate pH 8.5, 1 mM EDTA.
   EDTA prevents oxidative disulfide formation.
2. Combine gel + ligand. Rotate at RT, 2-4 h (thiol+epoxide is fast).
3. Wash, quench (§J.8.2).

#### Quality control

- Amine coupling density: 5-25 μmol/mL wet gel typical.
- Thiol coupling density: 10-40 μmol/mL wet gel typical.

#### Troubleshooting

- **Very low amine coupling:** pH drifted. Add 1 M Na₂CO₃ to restore pH 10.
- **Very low thiol coupling:** thiols oxidised (disulfide). Include TCEP or
  freshly reduce the ligand with DTT then desalt before adding.

#### References

Mateo et al. (2007) *Enzyme Microb. Technol.* 39:274. Hermanson (2013) Ch. 16.4.

---

### J.2.3  Ligand Coupling — thiol on DVS / vinyl sulfone matrix

**Purpose:** Couple thiol-bearing ligands (cysteine-containing peptides,
thiolated probes) to a DVS-activated matrix (§J.1.4). Michael addition, fast
and clean.

**Evidence tier:** `validated_quantitative`

**DPSim M2 key:** `protein_a_vs_coupling` for the built-in Protein A route.
Other thiol/vinyl-sulfone ligand couplings require a calibrated profile or
external assay evidence.

**Based on:** Morpurgo et al. (*Bioconjug. Chem.* 1996, 7:363); Hermanson Ch.
16.5.

#### Safety

- Active gel still carries unreacted vinyl sulfone — a sensitiser. Nitrile
  gloves mandatory.
- Waste: quench post-reaction (§J.8.3) before pooling.

#### What you need (per 10 mL DVS-activated wet gel)

| Reagent | Amount | Notes |
|---|---|---|
| Thiol ligand | 5-30 μmol | In 20 mL 0.1 M Na phosphate pH 8.0, 1 mM EDTA |
| TCEP | 0.5 mM | To keep ligand reduced |

#### Procedure

1. Dissolve thiol ligand. Add TCEP to 0.5 mM. Verify no precipitate.
2. Combine gel + ligand. Rotate at RT, 1-3 h. Coupling is often > 90 %
   complete in 30 min.
3. Wash 3 × 30 mL phosphate buffer.
4. Quench (§J.8.3).

#### Quality control

- Thiol coupling density: 15-40 μmol/mL wet gel.
- Free thiol on the product (should be zero): add Ellman's reagent (DTNB) to
  a 10 μL slurry in 1 mL of 0.1 M Na phosphate pH 8; measure A₄₁₂. A₄₁₂
  > 0.05 indicates unreacted thiol on surface (oxidise with iodoacetamide).

#### Troubleshooting

- **Low coupling:** DVS-activated gel aged before coupling — vinyl sulfone
  hydrolysed. Must couple within 30 min of activation.

#### References

Morpurgo M, Veronese FM, Kachensky D, Harris JM (1996) *Bioconjug. Chem.*
7:363. Hermanson (2013) Ch. 16.5.

---

### J.2.4  Ligand Coupling — hydrazone on aldehyde matrix

**Purpose:** Couple hydrazide-functional ligands to an aldehyde-bearing
matrix (from periodate oxidation of agarose-bound diols — see §J.6.3 for
matrix oxidation). The hydrazone bond is pH-labile and reversible unless
reduced with NaCNBH₃.

**Evidence tier:** `semi_quantitative`

**DPSim M2 key:** `protein_a_hydrazide_coupling` for oxidized Protein A on
hydrazide media. Generic aldehyde/hydrazone coupling is external unless a
specific calibrated profile is added.

**Based on:** O'Shannessy et al. (*J. Immunol. Methods* 1984, 75:11);
Hermanson Ch. 19.2.

#### Safety

- Sodium cyanoborohydride (NaCNBH₃) is highly toxic (H300+H311+H331), and
  releases HCN on contact with acid. Fume hood mandatory.
- PPE: double nitrile gloves, face shield, chemical apron.
- Waste: alkaline aqueous; add 1 M NaOH + sodium hypochlorite before
  disposal to destroy cyanide residue.

#### What you need (per 10 mL aldehyde-activated wet gel)

| Reagent | Amount | CAS |
|---|---|---|
| Hydrazide ligand | 5-30 μmol | — |
| Coupling buffer: 0.1 M Na phosphate pH 6.0 | 20 mL | — |
| NaCNBH₃ | 50 mg | 25895-60-7 |

#### Procedure

1. Dissolve ligand in coupling buffer pH 6.0 (hydrazone forms best at pH
   5-6).
2. Combine 10 mL aldehyde-activated wet gel with 20 mL ligand solution.
3. In the fume hood, add 50 mg NaCNBH₃. Cap.
4. Rotate at RT, 4-24 h.
5. Wash with 3 × 30 mL PBS.
6. Quench unreacted aldehydes with 100 mM ethanolamine or 100 mM glycine
   pH 7.4 + 50 mg NaCNBH₃, 2 h RT (§J.8.5).

#### Quality control

- Coupling yield typically 50-90 %.
- Acid stability: treat 100 μL slurry with 0.1 M HCl 10 min; the hydrazone
  should survive (< 5 % leach) because NaCNBH₃ has reduced it to a stable
  hydrazine.

#### Troubleshooting

- **Ligand leaches over time:** reduction step was skipped or NaCNBH₃
  exhausted (aged reagent). Repeat the reduction with fresh NaCNBH₃.

#### References

O'Shannessy DJ, Dobersen MJ, Quarles RH (1984) *J. Immunol. Methods* 75:11.
Hermanson (2013) Ch. 19.2.

---

### J.2.5  Ligand Coupling — click chemistry (CuAAC or SPAAC)

**Purpose:** Attach an alkyne- or azide-functional ligand to an
azide- or alkyne-functional matrix via 1,3-dipolar cycloaddition. Two
variants: CuAAC (copper-catalysed, fast, needs Cu removal) and SPAAC
(strain-promoted, Cu-free, slower but biocompatible).

**Evidence tier:** `validated_quantitative` for CuAAC on polymeric supports;
`semi_quantitative` for SPAAC on gel matrices.

**DPSim M2 key:** not implemented as a built-in quantitative profile. Treat
CuAAC/SPAAC as external bench chemistry until a calibrated profile and site
balance are added.

**Based on:** Kolb, Finn, Sharpless (*Angew. Chem.* 2001, 40:2004); Meldal &
Tornøe (*Chem. Rev.* 2008, 108:2952); Hermanson Ch. 17.

#### Safety (CuAAC)

- Copper sulfate: H302 (harmful if swallowed), H315, H319, H410.
- Sodium ascorbate: low hazard.
- THPTA / BTTAA (Cu ligand): exclamation mark.
- PPE: nitrile gloves, safety glasses, lab coat.
- Waste: Cu-containing aqueous must go to the heavy-metal waste stream.

#### Safety (SPAAC)

- DBCO reagents: H315, H319, H317. Some are expensive but lab-safe at
  μmolar scale.
- PPE: standard lab PPE.

#### What you need (per 10 mL azide-activated wet gel, CuAAC)

| Reagent | Amount | CAS |
|---|---|---|
| Alkyne ligand | 5-30 μmol | — |
| CuSO₄·5H₂O | 5 mM final | 7758-99-8 |
| Sodium ascorbate | 25 mM final | 134-03-2 |
| THPTA (copper stabiliser) | 25 mM final | 760952-88-3 |
| Coupling buffer: 0.1 M Tris pH 7.4 | 20 mL | — |

#### Procedure (CuAAC)

1. Mix pre-formed Cu(II)-THPTA complex: in a small tube add CuSO₄ and THPTA
   to final concentrations 5 mM and 25 mM in water. Mix 1 min (blue).
2. In the coupling tube, add 10 mL wet gel, 20 mL Tris buffer, the alkyne
   ligand, and the Cu-THPTA premix.
3. Add sodium ascorbate to 25 mM final (this reduces Cu(II) → Cu(I) in situ).
4. Cap, displace headspace with nitrogen or argon (click is O₂-sensitive
   because ascorbate reoxidises).
5. Rotate at RT, 2-4 h, in the dark.
6. Wash with 3 × 30 mL Tris-EDTA (10 mM EDTA) to scavenge Cu, then 5 × 30 mL
   water, then 3 × 30 mL storage buffer.

#### Procedure (SPAAC, Cu-free)

1. Dissolve DBCO-ligand in PBS pH 7.4 at 1-5 mM. DBCO is often DMSO-soluble
   only — keep DMSO ≤ 10 % v/v in the reaction.
2. Combine with 10 mL azide-activated gel + PBS to 30 mL total.
3. Rotate at RT, 4-24 h.
4. Wash with 3 × 30 mL PBS, 3 × 30 mL PBS + 0.1 % Tween-20 (removes
   non-specifically bound DBCO excess), 3 × 30 mL PBS.

#### Quality control

- Fluorescence (if fluorescent ligand) on the gel; compare to free-ligand
  spectrum.
- Coupling yield from solution depletion: 50-95 % (CuAAC), 30-80 % (SPAAC).

#### Troubleshooting

- **CuAAC dead at 30 min:** oxygen ingress. Re-seal, re-add 10 mM ascorbate.
- **SPAAC slow:** DBCO aged / hydrolysed. Use within 1 week of reconstitution.

#### References

Kolb HC, Finn MG, Sharpless KB (2001) *Angew. Chem. Int. Ed.* 40:2004. Meldal M,
Tornøe CW (2008) *Chem. Rev.* 108:2952. Hermanson (2013) Ch. 17.

---

## J.3 Protein Coupling

Immobilise an antibody, enzyme, lectin, or other protein onto an activated
matrix. Protein coupling differs from ligand coupling in three ways:

1. Proteins are large (50-200 kDa). Steric access to internal lysines or
   cysteines is limited; surface residues dominate.
2. Protein activity is sensitive to pH, temperature, and side reactions.
   Prefer mild chemistries.
3. Orientation matters. Random coupling scrambles active-site access; use
   oriented strategies when possible.

Pretreat the protein as in §J.6 before coupling.

---

### J.3.1  Protein Coupling — NHS-ester (EDC/NHS activated matrix)

**Purpose:** Couple amine-bearing proteins (essentially every protein — via
surface lysines and N-terminus) to an NHS-ester-activated matrix. Most
common, most flexible, non-oriented.

**Evidence tier:** `validated_quantitative`

**DPSim M2 key:** `edc_nhs_activation` followed by
`protein_a_nhs_coupling` for the built-in Protein A route. Other proteins
need an explicit calibrated protein-coupling profile.

**Based on:** Staros (*Biochemistry* 1982, 21:3950); Hermanson Ch. 16.3.

#### Safety

- EDC: H302, H315, H319.
- NHS (N-hydroxysuccinimide): H315.
- PPE: nitrile gloves, safety glasses, lab coat.
- Waste: aqueous organic.

#### What you need (per 10 mL wet gel)

| Reagent | Amount | CAS |
|---|---|---|
| Carboxylated matrix (or NHS-activated matrix from vendor) | 10 mL | — |
| EDC·HCl | 50 mg (for in-situ activation) | 25952-53-8 |
| Sulfo-NHS | 15 mg | 106627-54-7 |
| Activation buffer: 0.1 M MES pH 5.0 | 20 mL | — |
| Coupling buffer: 50 mM sodium phosphate pH 7.4, 150 mM NaCl | 20 mL | — |
| Protein | 1-5 mg / mL gel | Pretreated per §J.6 |

#### Procedure

1. (If using pre-activated NHS-agarose from vendor: skip to step 5.)
2. In-situ activation: combine 10 mL carboxylated wet gel + 20 mL MES pH 5
   + 50 mg EDC + 15 mg sulfo-NHS. Rotate RT, 15 min.
3. Rapidly wash with 3 × 30 mL ice-cold MES pH 5 on the funnel. Drain damp.
4. Immediately proceed (NHS-ester half-life ≈ 30 min at pH 7, 10 min at pH 8).
5. Mix drained gel with protein in coupling buffer pH 7.4 (20 mL total).
6. Rotate at 4 °C, 2-4 h (OR RT 1 h for activity-robust proteins).
7. Wash with 3 × 30 mL coupling buffer, 3 × 30 mL PBS + 0.5 M NaCl
   (to remove non-covalently bound protein), 3 × 30 mL PBS.
8. Quench (§J.8.1).

#### Quality control

- Bradford / A₂₈₀ on pre- and post-coupling solutions. 60-90 % of added
  protein typically couples.
- Activity assay on the immobilised protein (e.g., enzyme turnover in a
  packed micro-column). Retained activity is typically 30-80 % of soluble
  protein.

#### Troubleshooting

- **Low coupling:** NHS-ester expired. Re-activate or use fresh matrix.
- **Low activity:** active site lysines got coupled. Try oriented coupling
  (§J.3.4 or §J.3.5) instead.
- **Non-specific sticking:** ionic interactions with matrix. Run a
  higher-salt wash (1 M NaCl).

#### References

Staros JV (1982) *Biochemistry* 21:3950. Hermanson (2013) Ch. 16.3.

---

### J.3.2  Protein Coupling — glutaraldehyde (GA) two-step method

**Purpose:** Immobilise enzymes (esp. proteases, lipases) by first
activating an amine-matrix with glutaraldehyde, then exposing to protein.
Creates an imine / reduced-amine network; robust but non-oriented.

**Evidence tier:** `validated_quantitative` for established enzyme-immobilization protocols

**DPSim M2 key:** `glutaraldehyde_secondary` for secondary amine
crosslinking/reinforcement. Protein immobilization by glutaraldehyde should
also carry ligand-density, activity-retention, and leaching assay records.

**Based on:** Monsan (*J. Mol. Catal.* 1978, 3:371); Migneault et al.
(*BioTechniques* 2004, 37:790); Hermanson Ch. 16.1.

#### Safety

- Glutaraldehyde: H301, H330, H314, H317, H334 (respiratory sensitiser).
  Fume hood mandatory.
- PPE: double nitrile gloves, face shield, chemical apron, lab coat.
- Waste: neutralise with glycine or ethanolamine before disposal into aqueous
  organic waste.

#### What you need (per 10 mL amine-matrix wet gel)

| Reagent | Amount | CAS |
|---|---|---|
| Glutaraldehyde 25 % aq. | 2 mL | 111-30-8 |
| 0.1 M Na phosphate pH 7.0 | 20 mL | — |
| Sodium cyanoborohydride (NaCNBH₃) | 50 mg | 25895-60-7 |
| Protein | 1-5 mg / mL gel | — |

#### Procedure

1. PPE on. Fume hood mandatory for glutaraldehyde.
2. Wash 10 mL amine-matrix with 3 × 30 mL 0.1 M Na phosphate pH 7.
3. Activate: combine gel + 20 mL buffer + 2 mL 25 % glutaraldehyde (final
   ≈ 2.3 % GA). Rotate RT, 1-2 h. Matrix turns yellow.
4. Wash rapidly with 5 × 30 mL phosphate buffer until filtrate is clear.
5. Immediately add protein in 20 mL phosphate buffer. Rotate 4 °C, 16 h.
6. Add 50 mg NaCNBH₃ (in the fume hood) to reduce the Schiff base to a
   stable secondary amine. Rotate 4 °C, 2 h.
7. Wash with 3 × 30 mL PBS + 0.5 M NaCl, 3 × 30 mL PBS.
8. Quench (§J.8.5).

#### Quality control

- Activity: for enzymes, measure before and after coupling. Glutaraldehyde
  often gives high activity (40-80 %) for proteases and lipases.

#### Troubleshooting

- **Gel crosslinks excessively:** GA concentration too high. Reduce to 1 %.
- **Low activity:** reduce coupling time to 4 h or reduce GA concentration.

#### References

Monsan P (1978) *J. Mol. Catal.* 3:371. Migneault I et al. (2004)
*BioTechniques* 37:790. Hermanson (2013) Ch. 16.1.

---

### J.3.3  Protein Coupling — Protein A + DMP crosslinking (oriented IgG)

**Purpose:** Immobilise an antibody in defined orientation by first binding
it via Fc region to immobilised Protein A / G, then crosslinking with
dimethyl pimelimidate (DMP). Fab domains point outward, antigen-binding
retained.

**Evidence tier:** `validated_quantitative`

**DPSim M2 key:** not implemented as a built-in quantitative profile. Treat
DMP-crosslinked Protein A/IgG handling as external bench evidence unless a
specific calibrated model is added.

**Based on:** Schneider et al. (*J. Biol. Chem.* 1982, 257:10766); Hermanson Ch. 20.2.

#### Safety

- DMP: H315, H319. Low hazard.
- PPE: nitrile gloves, safety glasses, lab coat.
- Waste: aqueous.

#### What you need (per 1 mL Protein-A-agarose)

| Reagent | Amount | CAS |
|---|---|---|
| Protein A-agarose | 1 mL | (commercial) |
| IgG | 1-10 mg | — |
| PBS pH 7.4 | 10 mL | — |
| Triethanolamine buffer: 0.2 M, pH 8.2 | 10 mL | 102-71-6 |
| DMP·2HCl (dimethyl pimelimidate dihydrochloride) | 20 mg | 58537-94-3 |
| Quench buffer: 50 mM ethanolamine pH 8.2 | 10 mL | 141-43-5 |
| Storage buffer: PBS + 0.05 % NaN₃ | 20 mL | — |

#### Procedure

1. Equilibrate 1 mL Protein A-agarose with 5 × 2 mL PBS.
2. Incubate gel with 1-10 mg IgG in 5 mL PBS, rotate RT 30-60 min. Affinity
   capture.
3. Wash 3 × 10 mL PBS to remove unbound IgG.
4. Exchange to 10 × 2 mL 0.2 M triethanolamine pH 8.2. Drain.
5. Dissolve 20 mg DMP in 2 mL triethanolamine buffer (fresh — DMP hydrolyses
   in minutes). Quickly add to gel.
6. Rotate RT, 30 min.
7. Quench: drain, add 10 mL 50 mM ethanolamine pH 8.2, rotate 5 min.
8. Wash with 3 × 10 mL PBS, 3 × 10 mL 100 mM glycine pH 2.5 (strips
   uncrosslinked IgG), 3 × 10 mL PBS.
9. Store in PBS + 0.05 % sodium azide at 4 °C.

#### Quality control

- Binding capacity: test with known antigen; should be 60-80 % of
  equivalent solution-phase IgG binding.
- Leaching: incubate gel in 100 mM glycine pH 2.5 for 10 min. IgG leach
  in the supernatant should be < 10 % of immobilised.

#### Troubleshooting

- **High IgG leach on low-pH wash:** crosslinking incomplete. Repeat steps
  5-7 with fresh DMP.
- **Low antigen binding:** DMP over-crosslinked the Fab region. Reduce DMP
  to 10 mg or reduce time to 15 min.

#### References

Schneider C et al. (1982) *J. Biol. Chem.* 257:10766. Hermanson (2013) Ch. 20.2.

---

### J.3.4  Protein Coupling — sortase A (site-specific, LPXTG tag)

**Purpose:** Oriented, site-specific coupling using Sortase A enzyme. The
protein of interest must carry a C-terminal LPXTG tag (genetically engineered).
The matrix must present N-terminal polyglycine (Gly₃ or Gly₅). Sortase
transpeptidates: LPXTG cleaved, LPXT-Gly_n product covalently attached.

**Evidence tier:** `validated_quantitative`

**DPSim M2 key:** not implemented as a built-in quantitative profile. Treat
sortase-mediated coupling as external evidence until calibrated.

**Based on:** Popp & Ploegh (*Angew. Chem. Int. Ed.* 2011, 50:5024);
Mao et al. (*J. Am. Chem. Soc.* 2004, 126:2670).

#### Safety

- Low-hazard reagents throughout. Standard lab PPE.
- Sortase A itself has no known hazards.
- Waste: aqueous.

#### What you need (per 1 mL Gly₃-agarose)

| Reagent | Amount | Notes |
|---|---|---|
| Gly₃-agarose matrix | 1 mL | See §J.2 for coupling a Gly-Gly-Gly peptide to an activated matrix |
| LPXTG-tagged target protein | 50 μmol | Pretreated per §J.6 |
| Sortase A enzyme | 10 μM | Recombinant; Addgene or commercial |
| Sortase buffer: 50 mM Tris-HCl pH 7.5, 150 mM NaCl, 10 mM CaCl₂ | 5 mL | Ca²⁺ is essential |

#### Procedure

1. Equilibrate 1 mL Gly₃-agarose with 3 × 5 mL sortase buffer.
2. Combine gel + 5 mL sortase buffer + 50 μmol LPXTG-protein + 10 μM sortase A.
3. Rotate RT, 2-6 h (monitor reaction by SDS-PAGE; the LPXTG-protein band
   should shift slightly and the soluble supernatant should deplete).
4. Wash with 3 × 10 mL sortase buffer.
5. Wash with 3 × 10 mL sortase buffer WITHOUT CaCl₂ + 5 mM EGTA to
   inactivate residual sortase.
6. Wash 3 × 10 mL storage buffer (PBS + 0.05 % NaN₃). Store 4 °C.

#### Quality control

- Incorporation: 50-90 % of added LPXTG-protein couples.
- Activity: often > 80 % retained because the C-terminus is non-functional
  for most target proteins.

#### Troubleshooting

- **No coupling:** target protein LPXTG tag not accessible (buried).
  Verify by running sortase reaction in solution with a Gly-peptide — should
  produce the cleavage product.
- **Slow coupling:** low sortase activity. Titrate sortase from 1 to 50 μM.

#### References

Popp MW, Ploegh HL (2011) *Angew. Chem. Int. Ed.* 50:5024. Mao H et al.
(2004) *J. Am. Chem. Soc.* 126:2670.

---

### J.3.5  Protein Coupling — oriented IgG via Fc-glycan oxidation + hydrazide

**Purpose:** Couple an IgG in defined orientation by oxidising the carbohydrate
diols in the Fc region (away from the antigen-binding site) to aldehydes,
then coupling to a hydrazide-agarose. Fully oriented, preserves antigen
binding.

**Evidence tier:** `validated_quantitative`

**DPSim M2 key:** `hydrazide_spacer_arm` followed by
`protein_a_hydrazide_coupling` when modeling oxidized Protein A or a
Protein A-like glycoprotein ligand. Other Fc-glycan hydrazone systems need
their own calibrated profile.

**Based on:** O'Shannessy et al. (*J. Immunol. Methods* 1984, 75:11);
Hermanson Ch. 19.2.

#### Safety

- NaIO₄: H272 (oxidiser), H315, H319. Keep dry.
- NaCNBH₃: H300+H311+H331. Fume hood, double gloves.
- PPE: double nitrile, face shield, chemical apron.
- Waste: alkaline + bleach treatment for NaCNBH₃-containing streams (see §J.2.4).

#### What you need (per 5 mg IgG)

| Reagent | Amount | CAS |
|---|---|---|
| IgG (pretreated per §J.6.4) | 5 mg, 1 mg/mL in PBS | — |
| NaIO₄ | 10 mM final | 7790-28-5 |
| Coupling buffer: 0.1 M Na phosphate pH 6.0 | 20 mL | — |
| Hydrazide-agarose (e.g., via hydrazide §J.2.4) | 1 mL | — |
| NaCNBH₃ | 50 mg | 25895-60-7 |

#### Procedure

1. Dissolve NaIO₄ in ice-cold PBS to 100 mM. Add to 5 mg IgG (5 mL at 1 mg/mL)
   to a final 10 mM NaIO₄. **On ice, in the dark, 30 min.** Over-oxidation
   destroys activity.
2. Quench excess NaIO₄ with ethylene glycol (100 mM final, 15 min).
3. Buffer-exchange to pH 6.0 phosphate buffer via PD-10 column (§J.6.4).
4. Add oxidised IgG to 1 mL hydrazide-agarose + 50 mg NaCNBH₃ in the fume hood.
5. Rotate RT, 16-24 h.
6. Wash 3 × 10 mL PBS + 0.5 M NaCl, 3 × 10 mL PBS.
7. Quench residual aldehydes with 100 mM glycine pH 7.4 + 20 mg NaCNBH₃, 2 h RT.
8. Final wash, store.

#### Quality control

- Coupling yield: 50-80 % of oxidised IgG incorporates.
- Antigen binding: typically 60-90 % retained relative to non-oriented
  NHS-coupled IgG.

#### Troubleshooting

- **Low antigen binding:** NaIO₄ concentration or time too high. Reduce to
  5 mM / 15 min.

#### References

O'Shannessy DJ et al. (1984) *J. Immunol. Methods* 75:11. Hermanson (2013) Ch. 19.2.

---

### J.3.6  Protein Coupling — Cys-tagged Protein A / G / L on pyridyl-disulfide support

**Purpose:** Reversibly capture a site-directed Cys variant of Protein A,
Protein G, or Protein L on a pyridyl-disulfide-loaded matrix via thiol-
disulfide exchange. The ligand is held by a single mixed disulfide and
released cleanly by reducing-agent elution, without leaching ligand into
the eluate. Useful for analytical-scale Protein-A/G/L columns that need
periodic ligand refresh, and for capturing Fab fragments (Protein L) or
broader IgG subclasses (Protein G).

**Evidence tier:** `semi_quantitative`.

**DPSim M2 keys:**
- `protein_a_thiol_to_pyridyl_disulfide` (42 kDa, Fc-IgG1 affinity).
- `protein_g_thiol_to_pyridyl_disulfide` (22 kDa, broader Fc subclasses).
- `protein_l_thiol_to_pyridyl_disulfide` (36 kDa, kappa-light-chain / Fab).

All three carry `chemistry_class="thiol_disulfide_exchange"` and declare
`A_343_pyridine_2_thione` as the wet-lab observable for evidence-tier
calibration.

**Based on:** Carlsson J, Drevin H, Axén R (1978) *Biochem. J.* 173:723;
Brocklehurst K, Carlsson J, Kierstan MPJ, Crook EM (1973) *Biochem. J.*
133:573; Hermanson (2013) Ch. 17.4; Nilson BHK et al. (1992) *Eur. J.
Immunol.* 22:2547 (Protein L).

#### Safety

- Cys-tagged Protein A / G / L: low hazard. Store –80 °C, single-thaw.
- DTT (CAS 3483-12-3) / TCEP (CAS 51805-45-9): used at elution, not
  during coupling. Skin/eye irritant; PPE: nitrile gloves, safety
  glasses.
- Pyridine-2-thione, the byproduct of coupling: low hazard, but
  unpleasant odour. Handle the column eluate in the hood.

#### What you need (per 1 mL pyridyl-disulfide-loaded matrix from §J.4.7)

| Reagent | Amount | CAS / source | Storage |
|---|---|---|---|
| Cys-tagged Protein A / G / L | 1–5 mg | Custom, recombinant | –80 °C |
| Coupling buffer (50 mM Na phosphate, 150 mM NaCl, 1 mM EDTA, pH 7.5) | 20 mL | — | 4 °C |
| TCEP (5 mM in coupling buffer, FRESH) | 2 mL | 51805-45-9 | Make fresh |
| Storage buffer (PBS + 0.05 % NaN₃) | 20 mL | — | 4 °C |

#### Procedure

1. PPE on.
2. **Reduce the protein's Cys-tag immediately before coupling.** Combine
   1–5 mg Cys-tagged ligand with 100 µL of 5 mM TCEP in 1 mL coupling
   buffer. Hold at 25 °C, 30 min. (TCEP does NOT need to be removed —
   it does not reduce the matrix's pyridyl-disulfide.)
3. Wash 1 mL pyridyl-disulfide-loaded gel (from §J.4.7) with 5 × 5 mL
   coupling buffer to remove storage solvent.
4. Add the reduced protein solution to the gel slurry. Total volume
   ~ 2 mL. Rotate at 4 °C, 1 h.
5. **Monitor the supernatant at 343 nm.** Pyridine-2-thione released
   stoichiometrically as protein -SH displaces it. ε_343 = 8.08 mM⁻¹
   cm⁻¹. Coupling is complete when A_343 plateaus.
6. Wash with 10 × 5 mL coupling buffer, then 10 × 5 mL storage buffer.
7. Store at 4 °C in storage buffer, ≤ 4 weeks.

#### Quality control

- Coupling yield (from A_343 release): 80–95 % of input ligand for
  well-designed Cys-tag positions; < 50 % suggests buried Cys or
  oxidised dimer.
- Functional binding: load 1 mL human IgG (1 mg/mL) over the column;
  expect breakthrough fractions to be < 5 % of feed concentration.
- Ligand leaching (the headline benefit): elute with 10 mM DTT and
  measure free protein in the eluate. < 0.1 % per cycle is typical;
  multi-cycle ligand refresh is the use case.

#### Troubleshooting

- **Low coupling yield (< 50 %):** Cys-tag is buried in the folded
  protein, or the protein has dimerised via the Cys. Run a non-reducing
  SDS-PAGE on the input — a 2× MW band indicates dimer; reduce
  thoroughly with TCEP, then desalt before coupling.
- **A_343 plateau is reached but capture activity is low:** Cys-tag is
  too close to the binding site, sterically blocking IgG/Fab. Move the
  Cys to the C-terminus or insert a flexible linker.
- **Capture activity drops after 5 cycles:** mixed disulfide is being
  reduced over time by trace thiols in the buffer. Store under nitrogen
  and add 1 mM EDTA to suppress metal-catalysed disulfide reduction.

#### References

Brocklehurst K, Carlsson J, Kierstan MPJ, Crook EM (1973) *Biochem. J.*
133:573. Carlsson J, Drevin H, Axén R (1978) *Biochem. J.* 173:723.
Nilson BHK, Sólomon A, Björck L, Akerström B (1992) *Eur. J. Immunol.*
22:2547. Hermanson (2013) Ch. 17.4.

---

## J.4 Spacer Arm

Spacer arms are short bifunctional molecules inserted between the matrix
and the ligand. They reduce steric hindrance so that larger targets (e.g.,
antibodies binding a small immobilised hapten) can approach the ligand.

Pick a spacer based on (a) length, (b) hydrophilicity (longer alkyl chains
increase non-specific binding), and (c) the functional groups you need at
each end. Spacers are typically coupled to an activated matrix first (§J.1
→ one end of spacer), then the free end of the spacer is activated
(usually by EDC/NHS for a carboxyl end) and reacted with the ligand (§J.2/J.3).

---

### J.4.1  Spacer Arm — Ethylenediamine (EDA, 3 Å diamine)

**Purpose:** Shortest diamine spacer. Both ends primary amines. Use when a
small ligand needs only a slight offset from the matrix surface.

**Evidence tier:** `validated_quantitative`

**Based on:** Cuatrecasas (*J. Biol. Chem.* 1970, 245:3059); Hermanson Ch. 5.2.

#### Safety

- EDA: H302, H312, H314, H317, H334. Strong base, strong sensitiser.
- PPE: nitrile gloves, safety glasses, face shield, lab coat.
- Fume hood for weighing.
- Waste: neutralise before disposal (aqueous organic).

#### What you need (per 10 mL NHS-activated or CNBr-activated wet gel)

| Reagent | Amount | CAS |
|---|---|---|
| Ethylenediamine | 1 mL (neat) or 10 mL of 1 M in coupling buffer | 107-15-3 |
| Coupling buffer: 0.1 M NaHCO₃, 0.5 M NaCl, pH 8.3 | 20 mL | — |

#### Procedure

1. Prepare 1 M EDA in coupling buffer; adjust pH to 8.3 with HCl. **EDA is
   a strong base — add to buffer, not vice versa.**
2. Couple to activated matrix per §J.2.1. Use 20-fold excess EDA over
   activated sites so that mostly one amine of EDA reacts and the other
   stays free.
3. Wash, quench (§J.8.1 for NHS). The gel now presents terminal primary
   amines as the spacer free end.

#### QC

- Ninhydrin test (10 μL gel, add 2 mL 0.1 % ninhydrin in ethanol, heat 90 °C
  5 min): strong purple = abundant primary amines.

#### References

Cuatrecasas P (1970) *J. Biol. Chem.* 245:3059. Hermanson (2013) Ch. 5.2.

---

### J.4.2  Spacer Arm — 1,6-Diaminohexane (11 Å diamine)

**Purpose:** Longer diamine, same chemistry as EDA. Gives 11 Å of reach;
useful for ligands binding into a pocket (e.g., immobilised biotin reaching
into streptavidin's binding site).

**Evidence tier:** `validated_quantitative`

**Based on:** Hermanson Ch. 5.2.

#### Safety

- 1,6-Diaminohexane: H302, H312, H314, H317. Similar hazard profile to EDA
  but less volatile.
- PPE: nitrile gloves, safety glasses, lab coat.
- Waste: aqueous organic, neutralise first.

#### What you need (per 10 mL NHS-activated wet gel)

| Reagent | Amount | CAS |
|---|---|---|
| 1,6-Diaminohexane | 1 g (dissolve in 20 mL coupling buffer) | 124-09-4 |
| Coupling buffer: 0.1 M NaHCO₃, 0.5 M NaCl, pH 8.3 | 20 mL | — |

#### Procedure

Same as §J.4.1 but substitute 1,6-diaminohexane. 1 g in 20 mL = 0.43 M.

#### QC / Refs

Ninhydrin as above. Hermanson (2013) Ch. 5.2.

---

### J.4.3  Spacer Arm — 6-Aminohexanoic acid (9 Å amine-carboxyl)

**Purpose:** Heterobifunctional 9 Å spacer: amine one end, carboxyl the
other. Use when the matrix is amine-activated and the ligand to be coupled
is a carboxyl, or vice versa, via EDC/NHS chemistry.

**Evidence tier:** `validated_quantitative`

**Based on:** Hermanson Ch. 5.3.

#### Safety

- 6-Aminohexanoic acid: low hazard (H315, H319).
- PPE: nitrile gloves, safety glasses, lab coat.
- Waste: aqueous, routine.

#### What you need (per 10 mL NHS-activated amine-matrix)

| Reagent | Amount | CAS |
|---|---|---|
| 6-Aminohexanoic acid | 500 mg | 60-32-2 |
| Coupling buffer: 0.1 M NaHCO₃, 0.5 M NaCl, pH 8.3 | 20 mL | — |

#### Procedure

1. Dissolve 500 mg 6-aminohexanoic acid in 20 mL coupling buffer. pH 8.3.
2. Couple to NHS-activated matrix per §J.2.1. The amine of the spacer couples;
   the carboxyl is left free for later ligand coupling.
3. Wash and store.

#### Carboxyl activation of the spacer free end (when coupling a protein)

- Per §J.3.1 — in-situ EDC/NHS activation, then add protein.

#### Refs

Hermanson (2013) Ch. 5.3.

---

### J.4.4  Spacer Arm — DADPA (3,3'-diamino-N-methyldipropylamine, 11 Å triamine)

**Purpose:** 11 Å spacer with three nitrogen functional handles. Useful for
multi-point attachment or for a heterotrifunctional linker.

**Evidence tier:** `semi_quantitative`

**Based on:** Hermanson Ch. 5.2.

#### Safety

- DADPA: H302, H314, H317. Strong base.
- PPE: nitrile gloves, face shield, lab coat.
- Waste: aqueous organic, neutralise.

#### What you need

| Reagent | Amount | CAS |
|---|---|---|
| DADPA | 500 mg | 105-83-9 |
| Coupling buffer pH 8.3 | 20 mL | — |

#### Procedure

Same as §J.4.1. 500 mg in 20 mL = 0.15 M; 20-fold over activated sites.

#### Refs

Hermanson (2013) Ch. 5.2.

---

### J.4.5  Spacer Arm — PEG bis-amine (~30-350 Å, tunable)

**Purpose:** Polyethylene glycol diamine of defined MW. Highly hydrophilic
(prevents non-specific binding). Lengths from 500 Da (~3 nm) to 5000 Da
(~30 nm).

**Evidence tier:** `validated_quantitative`

**Based on:** Harris JM (ed.) *Poly(ethylene glycol) Chemistry: Biotechnical
and Biomedical Applications* (1992); Hermanson Ch. 18.

#### Safety

- PEG bis-amine (3400 Da): very low hazard. H303 (may be harmful if swallowed).
- PPE: nitrile gloves, safety glasses, lab coat.
- Waste: aqueous, routine.

#### What you need (per 10 mL NHS-activated wet gel)

| Reagent | Amount | CAS |
|---|---|---|
| PEG-bisamine 3.4 kDa | 500 mg | 24991-53-5 (for 3.4 kDa) |
| Coupling buffer pH 8.3 | 20 mL | — |

#### Procedure

1. Dissolve 500 mg PEG-bisamine in 20 mL coupling buffer. Expect a slightly
   viscous solution.
2. Couple to NHS-activated matrix per §J.2.1. Overnight at 4 °C to drive
   the reaction to completion on both ends of any PEG chain that orients
   away from the matrix.
3. Wash with 5 × 30 mL coupling buffer + 0.5 M NaCl (removes non-covalently
   bound PEG), 3 × 30 mL PBS.
4. Quench.

#### QC

- Ninhydrin on end-points: should be strongly positive (many amine termini).
- MW-discrimination: 3.4 kDa PEG gives ~30 nm of reach; confirm by titrating
  with a fluorescent amine probe and measuring accessible density.

#### Refs

Harris JM (ed.) (1992). Hermanson (2013) Ch. 18.

---

### J.4.6  Spacer Arm — Jeffamine (polyether diamine, 600-2000 Da)

**Purpose:** Jeffamine is a family of polyether diamines (commercial,
Huntsman). Lengths 600-2000 Da, more hydrophobic than PEG-bisamine but
cheaper. Use for enzyme immobilization where modest hydrophobicity is OK.

**Evidence tier:** `semi_quantitative`

**Based on:** Product literature (Huntsman); Hermanson Ch. 18.

#### Safety

- Jeffamine: H302, H315, H318.
- PPE: nitrile gloves, safety glasses, lab coat.
- Waste: aqueous organic.

#### Procedure

Same pattern as §J.4.5 with Jeffamine (D-2000 or D-400 depending on desired
length).

#### Refs

Hermanson (2013) Ch. 18.

---

### J.4.7  Arm-distal Activation — Pyridyl-disulfide on amine arm (v0.5.0 ARM_ACTIVATION)

**Purpose:** Convert an arm-distal -NH₂ (installed by §J.4.1 EDA, §J.4.4
DADPA, or another amine spacer) into a pyridyl-disulfide-loaded
electrophile that captures protein -SH via reversible thiol-disulfide
exchange. This is **not** a matrix-side ACS conversion — the polysaccharide
backbone is unchanged. The reaction installs an `R–S–S–pyridyl` handle at
the arm's far end.

**Evidence tier:** `semi_quantitative`.

**DPSim M2 key:** `pyridyl_disulfide_activation`. Step type:
`ModificationStepType.ARM_ACTIVATION`. Pre-condition: `acs_state` must
contain `AMINE_DISTAL > 0` from a prior `SPACER_ARM` step, OR the polymer
family must be chitosan-bearing (native -NH₂ surface). The G6 guardrail
emits BLOCKER if neither is satisfied.

**Important chemistry note (v0.5.0 fix).** Earlier DPSim revisions
labelled the product as `THIOL` and the chemistry class as `"reduction"`.
Both are wrong: a pyridyl-disulfide-loaded matrix carries an
*electrophilic* `R–S–S–pyridyl` group, not a free thiol; coupling is
*thiol-disulfide exchange*, not reduction. (Reduction is what happens at
*elution* when DTT/TCEP cleaves the captured-protein disulfide.) The
v0.5.0 reagent profile has been corrected to `product_acs=PYRIDYL_DISULFIDE`,
`chemistry_class="thiol_disulfide_exchange"`.

**Based on:** Carlsson J et al. (1978) *Biochem. J.* 173:723;
Brocklehurst K et al. (1973) *Biochem. J.* 133:573; Hermanson Ch. 17.4.

#### Safety

- 2,2'-Dipyridyl disulfide / Aldrithiol-2 (CAS 2127-03-9): GHS exclamation
  mark; H315 (skin irritant), H319 (eye irritant). PPE: nitrile gloves,
  safety glasses.
- Methanol (carrier solvent, CAS 67-56-1): flammable (H225), toxic
  (H301/H311/H331). Fume hood for stock prep.
- Pyridine-2-thione (the byproduct, A_343 = 8.08 mM⁻¹ cm⁻¹): low
  hazard, mildly malodorous.
- Waste: organic-aqueous; non-halogenated.

#### What you need (per 10 mL amine-arm-loaded wet gel)

| Reagent | Amount | CAS | Storage |
|---|---|---|---|
| 2,2'-Dipyridyl disulfide (Aldrithiol-2) | 100 mg | 2127-03-9 | 4 °C, dry, dark |
| Methanol (anhydrous) | 5 mL | 67-56-1 | Fume hood |
| Coupling buffer (0.1 M Na phosphate, 1 mM EDTA, pH 7.5) | 20 mL | — | 4 °C |
| Storage buffer (PBS + 0.05 % NaN₃) | 20 mL | — | 4 °C |

#### Procedure

1. PPE on.
2. **Verify the arm-distal -NH₂ density** before proceeding. Run a
   ninhydrin (Kaiser) test on a 50 µL gel sample; expect a strong
   purple-blue colour. Without this verification the simulator's G6
   precondition check will block the run.
3. Wash 10 mL amine-arm-loaded gel with 5 × 30 mL coupling buffer.
4. Dissolve 100 mg 2,2'-dipyridyl disulfide in 5 mL methanol (in the
   hood). Dilute into 20 mL coupling buffer. Final concentration ≈ 20
   mM.
5. Add the dipyridyl disulfide solution to the drained gel. Rotate at
   25 °C, 1 h. Pyridine-2-thione is released stoichiometrically — track
   A_343 of the supernatant; reaction is complete when A_343 plateaus.
6. Wash with 10 × 30 mL coupling buffer, then 10 × 30 mL storage
   buffer. Removes all unreacted dipyridyl disulfide and the released
   pyridine-2-thione.
7. Store at 4 °C in storage buffer, ≤ 2 weeks. The matrix is
   *electrophilic* (S-S exchange-active). Avoid contact with reducing
   agents (DTT, TCEP, β-mercaptoethanol) until intentional elution.

#### Quality control

- Pyridyl-disulfide loading: 10–50 µmol/mL wet gel (back-calculated from
  A_343 release at coupling, ε_343 = 8.08 mM⁻¹ cm⁻¹).
- Activity check: expose 100 µL gel to a known concentration of
  glutathione (1 mM) and read pyridine-2-thione release at 343 nm; the
  ratio of measured to theoretical loading is the active fraction.

#### Troubleshooting

- **No A_343 release:** the prior amine-arm step did not produce
  AMINE_DISTAL > 0. Re-run §J.4.1 EDA or §J.4.4 DADPA, verify by
  ninhydrin test before retrying.
- **Loading drops after 1 week of storage:** PDS is being slowly
  hydrolysed or reduced by trace contaminants. Tighten the EDTA dose
  (1 mM → 5 mM) and store under nitrogen.
- **A_343 release plateaus low (< 30 % of theoretical):** dipyridyl
  disulfide bottle was old (yellow / brown discolouration). Use a fresh
  ampoule.

#### Downstream coupling

After §J.4.7, the matrix is ready for §J.3.6 (Cys-tagged Protein A / G /
L) or for any thiol-bearing ligand (glutathione, terminal-Cys peptides).
Capture is reversible; elute with 10 mM DTT or 5 mM TCEP.

#### References

Brocklehurst K, Carlsson J, Kierstan MPJ, Crook EM (1973) *Biochem. J.*
133:573. Carlsson J, Drevin H, Axén R (1978) *Biochem. J.* 173:723.
Hermanson (2013) Ch. 17.4.

---

## J.5 Metal Charging

IMAC (Immobilised Metal Affinity Chromatography). The matrix has a chelator
group (NTA, IDA, or TED). Charging adds a specific metal ion onto the
chelator. The loaded metal then binds a target with the complementary
metal-coordinating group — most commonly a His-tag on a recombinant protein.

Load the matrix the day of purification. Metals leach during elution; if
the matrix has been used, strip and reload (see final section).

---

### J.5.1  Metal Charging — Ni²⁺ on NTA

**Purpose:** The workhorse for His-tag purification. Ni²⁺-NTA has a Kd of
~10⁻⁶ M for a His₆-tag.

**Evidence tier:** `validated_quantitative`

**DPSim M2 key:** `nickel_charging_nta` for explicit NTA sites. Use
`nickel_charging_ida` for IDA media; the older generic `nickel_charging`
profile does not distinguish the chelator inventory.

**Based on:** Hochuli et al. (*Biotechnology* 1988, 6:1321); Porath et al.
(*Nature* 1975, 258:598).

#### Safety

- NiSO₄·6H₂O: H302, H315, H317, H334, H341, H350, H360, H372, H410. CMR
  reagent.
- PPE: double nitrile gloves, safety glasses, lab coat.
- Waste: Ni-containing aqueous to heavy-metal waste stream. Solid Ni salts:
  do NOT place in general chemical waste.

#### What you need (per 10 mL NTA-agarose bed)

| Reagent | Amount | CAS |
|---|---|---|
| NiSO₄·6H₂O 100 mM | 20 mL | 10101-97-0 |
| Water | ≥ 200 mL | — |
| Storage buffer: 20 % ethanol | 20 mL | 64-17-5 |

#### Procedure

1. Wash NTA-agarose with 5 CV water to remove storage buffer.
2. Load 2 CV of 100 mM NiSO₄ at ≤ 1 CV/min (gravity is fine). Matrix turns
   light blue-green.
3. Wash 10 CV water to remove unbound Ni²⁺.
4. Wash 5 CV binding buffer (usually 50 mM Na phosphate pH 7.5, 300 mM NaCl,
   10 mM imidazole).
5. Matrix is ready for His-tag loading. Do not store charged; re-load the
   day of use.

#### QC

- Colour: light blue-green. If pale, recharge.
- Capacity: 30-50 mg His-tagged protein per mL matrix (specification;
  measure by loading a known protein in excess).

#### Troubleshooting

- **Weak protein binding:** low Ni loading or leached. Strip and recharge.
- **Non-specific protein binding:** histidine-rich non-target proteins
  co-purify. Increase imidazole in binding/wash buffers to 20-40 mM.

#### References

Hochuli E, Döbeli H, Schacher A (1988) *Biotechnology* 6:1321. Porath J et
al. (1975) *Nature* 258:598.

---

### J.5.2  Metal Charging — Co²⁺ on NTA (or CMA)

**Purpose:** Higher-selectivity alternative to Ni²⁺. Binds His-tag less
tightly (Kd ~10⁻⁵ M) but co-purifies fewer endogenous His-rich contaminants.
Use when purity > yield.

**Evidence tier:** `validated_quantitative`

**DPSim M2 key:** `cobalt_charging`. Record whether the chelator is NTA,
IDA, or another ligand in the recipe notes and assay metadata.

#### Safety

- CoCl₂·6H₂O: H302, H317, H334, H341, H350, H360, H410. CMR reagent.
- PPE: double nitrile, safety glasses, lab coat.
- Waste: Co-containing aqueous to heavy-metal waste.

#### Procedure

As §J.5.1, substitute 100 mM CoCl₂·6H₂O. Matrix turns pink-purple.

#### Refs

Hochuli (1988); Porath (1975).

---

### J.5.3  Metal Charging — Cu²⁺ on IDA

**Purpose:** Broad specificity — binds proteins with surface histidines,
cysteines, or acidic patches. Use for screening "generic" metal-binding
proteins.

**Evidence tier:** `validated_quantitative`

**DPSim M2 key:** `copper_charging`. Record IDA/NTA identity and metal
loading assay results; copper selectivity and leaching risk are
chelator-dependent.

#### Safety

- CuSO₄·5H₂O: H302, H315, H319, H410.
- PPE: nitrile gloves, safety glasses, lab coat.
- Waste: Cu-containing aqueous to heavy-metal waste.

#### Procedure

As §J.5.1, substitute 100 mM CuSO₄·5H₂O on an IDA-agarose (not NTA; Cu²⁺
works poorly on NTA). Matrix turns deep blue.

#### QC

- Strong blue colour. Capacity 20-30 mg/mL matrix for general
  metal-binding proteins.

#### Refs

Porath (1975). Hermanson Ch. 10.

---

### J.5.4  Metal Charging — Zn²⁺ on IDA

**Purpose:** Niche use: immobilised lectins, carbonic anhydrases, some
phosphopeptide enrichment (limited performance vs Fe³⁺).

**Evidence tier:** `qualitative_trend`

**DPSim M2 key:** `zinc_charging`. Record chelator identity and measured
metal loading/leaching.

#### Safety

- ZnCl₂: H302, H314, H410.
- PPE: nitrile gloves, face shield, lab coat.
- Waste: Zn-containing aqueous to heavy-metal waste.

#### Procedure

As §J.5.1 with 100 mM ZnCl₂ in water (no organic buffer — ZnCl₂ hydrolyses).
Adjust water pH to 4.5 with HCl before charging.

---

### J.5.5  Metal Charging — Fe³⁺ on IDA (phosphopeptide enrichment)

**Purpose:** Phosphopeptide / phosphoprotein enrichment. Fe³⁺ coordinates to
the phosphate oxygens. Use after a tryptic digest for phosphoproteomics.

**Evidence tier:** `validated_quantitative` for phosphopeptide-enrichment bench practice

**DPSim M2 key:** not implemented as a built-in quantitative profile. Treat
Fe³⁺-IDA phosphopeptide media as external bench evidence unless a calibrated
profile is added.

**Based on:** Andersson & Porath (*Anal. Biochem.* 1986, 154:250).

#### Safety

- FeCl₃·6H₂O: H290, H302, H315, H318.
- PPE: nitrile gloves, safety glasses, lab coat.
- Waste: Fe-containing aqueous; most institutions accept in general aqueous
  waste at trace levels. Check local policy.

#### What you need (per 1 mL IDA-agarose)

| Reagent | Amount | CAS |
|---|---|---|
| FeCl₃·6H₂O | 100 mM in 10 mM HCl, 2 mL | 10025-77-1 |
| 0.1 M acetic acid pH 3.0 | 20 mL | 64-19-7 |

#### Procedure

1. Wash 1 mL IDA-agarose with 5 mL water, then 5 mL 0.1 M acetic acid pH 3.0.
2. Load 2 mL 100 mM FeCl₃ in 10 mM HCl. Matrix turns orange-brown.
3. Wash 10 mL 0.1 M acetic acid pH 3.0 to remove unbound Fe.
4. Equilibrate in binding buffer (typically 0.1 % TFA in 30 % acetonitrile
   for phosphopeptide enrichment).
5. Immediately load sample.

#### Refs

Andersson L, Porath J (1986) *Anal. Biochem.* 154:250.

---

### J.5.bonus Stripping a used IMAC column

When a charged IMAC column has been used (and leached metal), strip
completely before recharging:

1. Wash 5 CV water.
2. Strip with 5 CV 50 mM EDTA, pH 8.0 (chelates and removes all metal).
3. Wash 10 CV water.
4. Recharge per §J.5.1-5.5.

Never re-load metal onto a column that still has residual metal — you'll
co-precipitate oxides.

---

## J.6 Protein Pretreatment

Before coupling a protein to a matrix, pretreat to (a) make the coupling
chemistry effective, (b) preserve activity, and (c) remove contaminants
that compete with the coupling reaction.

---

### J.6.1  Protein Pretreatment — Disulfide reduction with DTT

**Purpose:** Reduce protein disulfide bonds to free thiols. Required for
thiol-maleimide coupling or DVS-thiol coupling (§J.2.3). Not recommended
for proteins whose tertiary structure depends on disulfides (most
antibodies, most secreted proteins).

**Evidence tier:** `validated_quantitative`

#### Safety

- DTT (dithiothreitol): H302, H315, H319. Low hazard.
- Must be removed after reduction — DTT competes with thiols for maleimide.
- PPE: nitrile gloves, safety glasses, lab coat.
- Waste: aqueous, routine.

#### What you need

| Reagent | Amount | CAS |
|---|---|---|
| DTT | 5-10 mM final | 3483-12-3 |
| Reducing buffer: 0.1 M Na phosphate pH 7.5, 1 mM EDTA | 10 mL | — |

#### Procedure

1. Dissolve protein (≥ 1 mg/mL) in reducing buffer.
2. Add DTT from 100 mM stock to 5-10 mM final.
3. Incubate 30 min at RT (or 37 °C for tough disulfides).
4. **Immediately** buffer-exchange to remove DTT (§J.6.4). DTT competes
   with target thiols in coupling.
5. Verify free-thiol generation with Ellman's reagent.

#### Troubleshooting

- **Protein precipitates:** disulfides held the structure. Switch to TCEP
  (§J.6.2) or use a milder DTT concentration (0.5 mM).

---

### J.6.2  Protein Pretreatment — Disulfide reduction with TCEP

**Purpose:** Tris(2-carboxyethyl)phosphine. Reduces disulfides without
needing removal before thiol-maleimide coupling (TCEP doesn't react with
maleimide at normal concentrations). Stronger reductant than DTT. Useful
for disulfide-stable proteins.

**Evidence tier:** `validated_quantitative`

#### Safety

- TCEP·HCl: H315, H319.
- PPE: nitrile gloves, safety glasses, lab coat.
- Waste: aqueous, routine.

#### What you need

| Reagent | Amount | CAS |
|---|---|---|
| TCEP·HCl | 0.5-5 mM final | 51805-45-9 |
| Reducing buffer pH 7.5 | 10 mL | — |

#### Procedure

1. Dissolve protein in reducing buffer.
2. Add TCEP from 500 mM stock (prepared fresh or stored at –80 °C) to
   0.5-5 mM final.
3. Incubate 15-30 min RT.
4. Proceed DIRECTLY to thiol coupling. No buffer exchange needed (unlike DTT).

---

### J.6.3  Protein Pretreatment — Glycan oxidation with NaIO₄

**Purpose:** Convert diols on glycoprotein glycans to aldehydes. Required
for oriented IgG immobilization (§J.3.5).

**Evidence tier:** `validated_quantitative`

#### Safety

- NaIO₄: H272 (oxidiser), H315, H319. Keep dry, away from organics.
- PPE: nitrile gloves, safety glasses, lab coat.
- Work on ice, in the dark.
- Waste: aqueous; neutralise with ethylene glycol before disposal.

#### What you need (per 5 mg glycoprotein)

| Reagent | Amount | CAS |
|---|---|---|
| NaIO₄ | 10 mM final | 7790-28-5 |
| PBS | 5 mL | — |
| Ethylene glycol (quench) | 100 mM final | 107-21-1 |

#### Procedure

1. Dissolve protein at 1 mg/mL in PBS.
2. Add NaIO₄ from 100 mM stock to 10 mM final. On ice, in the dark, 30 min.
3. Quench with ethylene glycol to 100 mM, 15 min.
4. Buffer-exchange to coupling buffer (usually pH 6 phosphate for hydrazone,
   §J.6.4).

---

### J.6.4  Protein Pretreatment — Buffer exchange with PD-10 / Sephadex G-25

**Purpose:** Remove small molecules (amines, reducing agents, salt, dye)
before coupling. Fastest, cheapest method for 0.5-2.5 mL protein samples.

**Evidence tier:** `validated_quantitative`

#### Safety

- No hazardous reagents.
- PPE: nitrile gloves, safety glasses, lab coat.
- Waste: aqueous, routine.

#### What you need

| Reagent | Amount |
|---|---|
| PD-10 column (or equivalent G-25 column) | 1 column |
| Target buffer | 25 mL |

#### Procedure

1. Equilibrate PD-10 with 25 mL target buffer (gravity flow).
2. Apply 2.5 mL protein sample, let enter bed.
3. Wash with 2.5 mL target buffer (discarded).
4. Elute with 3.5 mL target buffer (collected).
5. Protein is in a new buffer, diluted ~1.4-fold.

#### QC

- Verify buffer exchange by pH / conductivity measurement on the eluate.

---

### J.6.5  Protein Pretreatment — Dialysis

**Purpose:** Gentle, slow buffer exchange. Better for aggregation-prone
proteins where PD-10 handling causes denaturation.

**Evidence tier:** `validated_quantitative`

#### Safety

- No hazardous reagents.
- PPE: nitrile gloves, lab coat.
- Waste: aqueous.

#### What you need

| Reagent | Amount |
|---|---|
| Dialysis tubing or cassette, appropriate MWCO (typically 10 kDa for proteins > 30 kDa) | 1 |
| Target buffer | 1 L per 10 mL sample |

#### Procedure

1. Pre-soak dialysis tubing 10 min in water (if dry tubing). Cassettes need
   no pre-soak.
2. Load protein. Place in 1 L target buffer with gentle stir bar at 4 °C.
3. Exchange 3 × 1 L buffer over 24 h (e.g., 4 h, then overnight, then 4 h
   again). Protein concentration unchanged.

---

### J.6.6  Protein Pretreatment — Concentration (Amicon / centrifugal)

**Purpose:** Raise protein concentration to ≥ 1 mg/mL for efficient coupling.

**Evidence tier:** `validated_quantitative`

#### Safety / Waste

- Standard lab practice; no special hazards.

#### What you need

| Reagent | Amount |
|---|---|
| Centrifugal concentrator (appropriate MWCO, typically MWCO = 1/3 × protein MW) | 1 |
| Cold centrifuge | — |

#### Procedure

1. Pre-rinse concentrator with 1 mL buffer (removes glycerol residue).
2. Load protein, centrifuge at 4000 × g (or manufacturer spec), 4 °C.
3. Resuspend concentrate every 10 min to prevent membrane fouling.
4. Stop when target concentration reached. Measure A₂₈₀ or Bradford.

---

## J.7 Washing

Wash steps remove unbound reagents, non-covalently adsorbed contaminants,
and buffer residues. "Over-washing" is rare; "under-washing" is a common
cause of coupling-density overestimation and non-specific binding.

Universal rules:
- Wash at ≥ 3 CV (column volumes) per step.
- Use the same temperature as the step it follows.
- Never let the gel run dry on the funnel (air ingress damages matrix and
  can collapse pores irreversibly).

---

### J.7.1  Washing — Post-activation rinse

**Purpose:** Remove unreacted activator (CNBr, epichlorohydrin, DVS, CDI,
NHS-ester activator) before the gel sits for coupling.

**Buffer:** same chemistry as coupling buffer for the next step. E.g.,
ice-cold 0.1 M NaHCO₃ pH 8.3 for NHS-ester coupling; ice-cold 1 mM HCl for
CNBr-activated gels (preserves activation).

**Volume:** 3-5 CV.
**Temperature:** ice-cold where specified (CNBr, DVS), RT otherwise.

---

### J.7.2  Washing — Post-coupling rinse

**Purpose:** Remove unreacted ligand/protein, leaving only covalently bound.

**Buffer:** coupling buffer (e.g., 0.1 M NaHCO₃ pH 8.3).
**Volume:** 3 CV.

Save the first CV — measure ligand concentration in it to compute coupling
yield by difference (starting ligand minus wash-through ligand = incorporated).

---

### J.7.3  Washing — High-salt wash

**Purpose:** Disrupt ionic interactions between unreacted ligand/protein
and the matrix. Particularly important after CNBr-coupling (isourea is
positively charged) and for hydrophobic matrices.

**Buffer:** PBS + 0.5-1 M NaCl.
**Volume:** 3-5 CV.
**Temperature:** RT.

---

### J.7.4  Washing — Low-pH wash (for affinity media)

**Purpose:** Disrupt residual non-covalent binding on affinity media (e.g.,
Protein A/G columns post-DMP crosslinking, IgG-bound matrices).

**Buffer:** 0.1 M glycine pH 2.5 OR 0.1 M citric acid pH 3.0.
**Volume:** 3 CV.
**Temperature:** RT.
**Key note:** immediately neutralise the gel with 1 M Tris pH 9.0 (1/10
volume) in the collection tube so prolonged low pH doesn't damage the
ligand.

---

### J.7.5  Washing — Detergent wash

**Purpose:** Remove hydrophobically-adsorbed contaminants (lipids,
denatured protein). Use for hydrophobic ligands or when high background
is observed.

**Buffer:** PBS + 0.05 % Tween-20 OR PBS + 0.1 % Triton X-100.
**Volume:** 3 CV.
**Temperature:** RT.
**Follow-up:** always wash with 3 × 3 CV of plain PBS to remove detergent
residue (interferes with subsequent assays).

---

### J.7.6  Washing — Storage equilibration

**Purpose:** Place the finished gel into a stable storage buffer.

**Buffers:**
- For most protein-bearing affinity media: PBS + 0.05 % NaN₃ (antimicrobial)
  at 4 °C. Shelf life: 6-12 months.
- For organic-solvent-stable ligands: 20 % ethanol at 4 °C.
- For IMAC matrix: 20 % ethanol (stripped) or the charged form in binding
  buffer at 4 °C (only if used within days).

**Never freeze an agarose matrix.** Freezing destroys pore structure
irreversibly.

**Label** the storage tube with: date, matrix type, ligand, coupling
density (μmol/mL), buffer, storage T.

---

## J.8 Quenching

Quenching deactivates unreacted activated sites on the matrix after the
ligand has coupled. This is essential — unreacted sites continue to react
(slowly) with any amine, thiol, or other nucleophile that contacts the
gel, including your downstream samples. That produces non-specific
capture, reduced active-site accessibility, and irreproducible binding.

Quench by adding an excess of a harmless small-molecule nucleophile
that will saturate all remaining active sites.

---

### J.8.1  Quenching — NHS-ester / CDI / p-nitrophenyl carbonate

**Purpose:** Deactivate unreacted NHS-ester, CDI, or p-NP-carbonate sites.

**Reagent:** 1 M ethanolamine OR 1 M Tris, pH 8.0.

**Procedure:** drain post-coupling gel. Add 2 CV of 1 M Tris pH 8.0 or
1 M ethanolamine pH 8.0. Rotate 30-60 min at RT. Wash with 3 CV coupling
buffer to remove excess quench reagent.

**Safety:** Ethanolamine H302, H314. PPE: nitrile, face shield. Waste:
aqueous organic, neutralise.

---

### J.8.2  Quenching — Epoxide (BDDE, epichlorohydrin)

**Purpose:** Deactivate unreacted epoxide sites.

**Reagent:** 1 M ethanolamine pH 8.0 (for amine-quench) OR 0.5 M
β-mercaptoethanol (for thiol-quench).

**Procedure:** drain post-coupling gel. Add 2 CV of quench reagent. Rotate
4 h RT to overnight (epoxide is slow). Wash with 3 CV coupling buffer,
3 CV water.

**Safety:** β-mercaptoethanol H301, H310, H315, H317, H330, H410. Fume hood
mandatory. Ethanolamine as above. Waste: aqueous organic (neutralise and
dilute).

---

### J.8.3  Quenching — DVS (vinyl sulfone)

**Purpose:** Deactivate unreacted vinyl-sulfone sites.

**Reagent:** 1 M ethanolamine pH 9.0 OR 0.5 M β-mercaptoethanol in PBS.

**Procedure:** drain post-coupling gel. Add 2 CV quench. Rotate 2 h RT.
Wash with 3 CV PBS.

**Safety:** as §J.8.2. β-mercaptoethanol is the gold standard for vinyl
sulfone quenching (reacts fast); ethanolamine is slower but less hazardous.

---

### J.8.4  Quenching — Maleimide

**Purpose:** Deactivate unreacted maleimide sites.

**Reagent:** 10 mM L-cysteine OR 10 mM β-mercaptoethanol in PBS.

**Procedure:** drain post-coupling gel. Add 2 CV quench reagent. Rotate
30 min RT. Wash with 3 CV PBS.

**Safety:** cysteine low-hazard. β-mercaptoethanol as above.

---

### J.8.5  Quenching — Aldehyde (periodate-oxidised or glutaraldehyde-activated)

**Purpose:** Deactivate unreacted aldehyde sites AND reduce any existing
Schiff bases to stable secondary amines in one step.

**Reagent:** 50 mM NaBH₄ in 0.1 M Na phosphate pH 7.4 (fresh).
Alternative for less-damaging reduction: 50 mM NaCNBH₃ in 0.1 M Na
phosphate pH 7.4.

**Procedure:** drain post-coupling gel. Add 2 CV reducing agent + 100 mM
glycine or ethanolamine (to also cap remaining aldehydes). Rotate 30 min
at RT. Wash with 3 CV PBS.

**Safety:** NaBH₄ H260 (contact with water releases flammable gas), H314.
NaCNBH₃: H300+H311+H331. Fume hood mandatory for both. Waste: NaBH₄ aqueous
— let any residual gas evolve in the hood before capping the waste bottle.
NaCNBH₃ aqueous per §J.2.4 (alkaline + bleach neutralisation).

---

## J.bonus  Sim-to-Bench Decision Tree

A short index showing how to go from the simulator's output to the bench
protocol a first-timer should actually execute. If your M1 simulation
shipped a microsphere with target d32, pore size, and modulus, and you
want a surface functionality X:

```
Target functionality         →  Protocol chain

Affinity capture of IgG      →  §J.1.1 (CNBr)   +  §J.3.3 (Protein A + DMP) [oriented]
                             or  §J.1.5 (CDI)   +  §J.3.1 (NHS-ester)       [non-oriented]

Metal-binding protein (His-tag)→§J.1.3 (BDDE)   +  §J.2.2 (amine ligand: NTA)
                             +  §J.5.1 (Ni²⁺ charging)

Enzyme immobilization         →  §J.1.2 (epichlorohydrin)  +  §J.3.2 (glutaraldehyde)
                             or  §J.1.4 (DVS)   +  §J.2.3 (thiol on cysteine)

Oriented IgG immobilization  →  §J.6.3 (glycan oxidation) + §J.3.5 (Fc-hydrazone)

Click-functionalised matrix  →  §J.1.4 (DVS)   +  §J.2.3 (attach azide-thiol)
                             or vendor azide-agarose +  §J.2.5 (SPAAC)
```

Always end the chain with a §J.7 wash sequence and a §J.8 quench matched to
the last active chemistry. Store per §J.7.6.

---

## References consolidated

- Axén R, Porath J, Ernback S (1967) *Nature* 214:1302-1304.
- Porath J, Låås T, Janson J-C (1975) *J. Chromatogr.* 103:49-62.
- Porath J et al. (1975) *Nature* 258:598-599. (IMAC)
- Cuatrecasas P (1970) *J. Biol. Chem.* 245:3059-3065.
- Cuatrecasas P, Anfinsen CB (1971) *Annu. Rev. Biochem.* 40:259-278.
- Sundberg L, Porath J (1974) *J. Chromatogr.* 90:87-98.
- Matsumoto I, Mizuno Y, Seno N (1980) *J. Chromatogr.* 188:457-464.
- Nilsson K, Mosbach K (1984) *Meth. Enzymol.* 104:56-69.
- Kohn J, Wilchek M (1984) *Appl. Biochem. Biotechnol.* 9:285-305.
- O'Shannessy DJ et al. (1984) *J. Immunol. Methods* 75:11-17.
- Andersson L, Porath J (1986) *Anal. Biochem.* 154:250-254.
- Hearn MTW (1987) *Meth. Enzymol.* 135:102-117.
- Hochuli E, Döbeli H, Schacher A (1988) *Biotechnology* 6:1321-1325.
- Staros JV (1982) *Biochemistry* 21:3950-3955.
- Schneider C et al. (1982) *J. Biol. Chem.* 257:10766-10769.
- Monsan P (1978) *J. Mol. Catal.* 3:371-384.
- Kolb HC, Finn MG, Sharpless KB (2001) *Angew. Chem. Int. Ed.* 40:2004-2021.
- Meldal M, Tornøe CW (2008) *Chem. Rev.* 108:2952-3015.
- Mateo C et al. (2007) *Enzyme Microb. Technol.* 39:274-280.
- Morpurgo M et al. (1996) *Bioconjug. Chem.* 7:363-368.
- Mao H et al. (2004) *J. Am. Chem. Soc.* 126:2670-2671.
- Popp MW, Ploegh HL (2011) *Angew. Chem. Int. Ed.* 50:5024-5032.
- Bethell GS et al. (1979) *J. Biol. Chem.* 254:2572-2574.
- Migneault I et al. (2004) *BioTechniques* 37:790-802.
- Harris JM (ed.) (1992) *Poly(ethylene glycol) Chemistry*, Plenum Press.
- **Hermanson GT (2013) *Bioconjugate Techniques*, 3rd ed., Academic Press.**

---

## Disclaimer

This appendix is provided for informational, research, and training
purposes only. It does not constitute professional engineering advice,
medical advice, or formal peer review. Every protocol in this appendix
uses reagents some of which are classified as carcinogenic, mutagenic,
reproductively toxic, or strongly sensitising in one or more jurisdictions.
Before handling any reagent listed here, users must:

1. Consult the institution's safety office and the reagent's SDS.
2. Obtain approval for any restricted / CMR substance per local policy.
3. Receive hands-on training from a qualified supervisor.
4. Use the fume hood and PPE specified in each protocol without substitution.

All protocols must be reviewed at small scale by a qualified researcher
before routine use. Record every run in a laboratory notebook or electronic
lab notebook. If your wet-lab outcome differs materially from the
simulator's prediction, ingest the assay data through the Calibration panel
or CLI so the model is downgraded, calibrated, or corrected against actual
bench data.

---

## J.11 v0.3.x Addendum — Newly-Surfaced Reagent Protocols

The v0.3.4 audit fix exposed 44 additional reagents in the M2 dropdown that
were already in the backend but had no UI surface. The v0.3.6 follow-on
added two inverse-direction click reagents (alkyne-side variants). This
addendum maps every v0.3.x-era `reagent_key` to its protocol section in
Appendix J above, plus protocol stubs for the eight specialty chemistries
that did not have a dedicated entry in the v9.1 protocol set.

### J.11.1 Reagent → Protocol Cross-Reference Table

| `reagent_key` | M2 chemistry bucket | Appendix J section | Notes |
|---|---|---|---|
| `cnbr_activation` | Hydroxyl Activation | J.1.1 | Full SDS-lite + recipe |
| `ech_activation` | Hydroxyl Activation | J.1.2 | Full |
| `bdge_activation` | Hydroxyl Activation | J.1.3 | (BDDE in J — same chemistry) |
| `dvs_activation` | Hydroxyl Activation | J.1.4 | Full |
| `cdi_activation` | Hydroxyl Activation | J.1.5 | Full |
| `tresyl_chloride_activation` | Hydroxyl Activation | J.1.6 | Full |
| `stmp_secondary` | Secondary Crosslinking | J.1.7 | Full (note: triggerable dual-network) |
| `edc_nhs_activation` | Hydroxyl Activation | J.3.1 | EDC/NHS ester chain |
| `cyanuric_chloride_activation` | Hydroxyl Activation | J.11.2 (new) | Triazine activation; see § J.11.2 below |
| `glyoxyl_chained_activation` | Hydroxyl Activation | J.3.5 | Hydrazide / Fc-glycan oxidation |
| `periodate_oxidation` | Hydroxyl Activation | J.3.5 | Same chain as glyoxyl |
| `pyridyl_disulfide_activation` | Hydroxyl Activation | J.2.3 | Disulfide-exchange thiol coupling |
| `genipin_secondary` | Secondary Crosslinking | J.11.3 (new) | Amine-bridge crosslinker; see § J.11.3 |
| `glutaraldehyde_secondary` | Secondary Crosslinking | J.3.2 | Two-step GA Schiff-base + reduction |
| `glyoxal_dialdehyde` | Secondary Crosslinking | J.3.2 | Same chemistry as GA, smaller bridge |
| `borax_reversible_crosslinking` | Secondary Crosslinking | J.11.4 (new) | Reversibility warning; see § J.11.4 |
| `bis_epoxide_crosslinking` | Secondary Crosslinking | J.1.3 | BDDE / EGDGE chemistry |
| `hrp_h2o2_tyramine` | Secondary Crosslinking | J.11.5 (new) | Phenol radical coupling; see § J.11.5 |
| `alcl3_trivalent_gelant` | Secondary Crosslinking | J.11.6 (new) | NON-BIOTHERAPEUTIC; see § J.11.6 |
| `deae_coupling`, `q_coupling`, `cm_coupling`, `sp_coupling` | Ligand Coupling | J.2.2 | Epoxide + amine route |
| `phenyl_coupling`, `butyl_coupling`, `octyl_coupling`, `hexyl_coupling` | Ligand Coupling | J.2.2 | Epoxide + hydrophobic chain |
| `ida_coupling`, `nta_coupling` | Ligand Coupling | J.2.2 | Chelator coupling on epoxide |
| `glutathione_coupling` | Ligand Coupling | J.2.2 / J.11.7 (new) | Thiol on epoxide; see § J.11.7 for GST-tag context |
| `heparin_coupling` | Ligand Coupling | J.2.2 | Heparin amine on epoxide |
| `protein_a_coupling` | Protein Coupling | J.3.1, J.3.3 | NHS-ester or DMP routes |
| `protein_g_coupling`, `protein_ag_coupling`, `protein_l_coupling` | Protein Coupling | J.3.1 | Same NHS-ester chain |
| `protein_a_cys_coupling`, `protein_g_cys_coupling`, `generic_cys_protein_coupling` | Protein Coupling | J.2.3 | Cys-thiol on DVS or maleimide |
| `protein_a_hydrazide_coupling` | Protein Coupling | J.3.5 | Hydrazide / Fc-glycan oxidation |
| `protein_a_nhs_coupling` | Protein Coupling | J.3.1 | Standard NHS coupling |
| `protein_a_vs_coupling` | Protein Coupling | J.2.3 | DVS coupling chain |
| `streptavidin_coupling` | Protein Coupling | J.3.1 | NHS chain; biotin pre-binding common |
| `con_a_coupling`, `wga_coupling`, `jacalin_coupling`, `lentil_lectin_coupling` | Protein Coupling | J.3.1 | Standard lectin NHS coupling |
| `calmodulin_cbp_tap_coupling` | Protein Coupling | J.11.8 (new) | TAP-tag context; see § J.11.8 |
| `p_aminobenzamidine_coupling` | Protein Coupling | J.2.2 | Trypsin-affinity amine on epoxide |
| `multipoint_stability_uplift` | Protein Coupling | J.3.5 | Glyoxyl multipoint amine |
| `cuaac_click_coupling`, `cuaac_click_alkyne_side` | Click Chemistry | J.2.5 | Same chemistry, opposite handle direction |
| `spaac_click_coupling`, `spaac_click_alkyne_side` | Click Chemistry | J.2.5 | Same chemistry, opposite handle direction |
| `cibacron_blue_f3ga_coupling`, `procion_red_he3b_coupling` | Dye Pseudo-Affinity | J.11.9 (new) | Triazine-anchored dyes; see § J.11.9 |
| `mep_hcic_coupling` | Mixed-Mode HCIC | J.11.10 (new) | MEP HCIC; see § J.11.10 |
| `thiophilic_2me_coupling` | Thiophilic | J.11.11 (new) | T-Sorb / T-Gel; see § J.11.11 |
| `apba_boronate_coupling` | Boronate | J.11.12 (new) | m-APBA on epoxide; see § J.11.12 |
| `peptide_affinity_hwrgwv` | Peptide Affinity | J.3.1 | Standard peptide NHS coupling |
| `oligonucleotide_dna_coupling` | Oligonucleotide | J.11.13 (new) | DNA on CNBr-activated; see § J.11.13 |
| `amylose_mbp_affinity`, `chitin_cbd_intein` | Material-as-Ligand | J.11.14 (new) | Material-as-ligand pattern; see § J.11.14 |
| `dadpa_spacer*`, `dah_spacer*`, `eda_spacer*`, `peg600_spacer*`, `aha_*`, `hydrazide_spacer_arm`, `oligoglycine_spacer`, `aminooxy_peg_linker`, `cystamine_disulfide_spacer`, `succinic_anhydride_carboxylation`, `adh_hydrazone` | Spacer Arm | J.4.* | Various spacer-arm subsections |
| `sm_peg2`, `sm_peg4`, `sm_peg12`, `sm_peg24` | Spacer Arm | J.4.* | NHS-PEG-Maleimide heterobifunctional |
| `nickel_charging`, `cobalt_charging`, `copper_charging`, `zinc_charging`, `nickel_charging_ida`, `nickel_charging_nta`, `edta_stripping` | Metal Charging | J.5.* | Standard IMAC metal-loading chain |
| `tcep_reduction`, `dtt_reduction` | Protein Pretreatment | J.6.* | Reduction protocols |
| `wash_buffer` | Washing | (advisory) | No reaction; mass-balance bookkeeping only |
| `triazine_dye_leakage_advisory` | Washing | (advisory) | Wash endpoint guidance for dye-affinity matrices |
| `ethanolamine_quench`, `mercaptoethanol_quench`, `nabh4_quench`, `acetic_anhydride_quench` | Quenching | J.7.* | Standard quench chain |

> **Reading the table.** A protocol section listed as "(new)" was added in the v0.3.7 documentation cycle. All other sections were present in the v9.1 baseline of Appendix J.

The remainder of § J.11 contains the new protocol stubs.

### J.11.2 Cyanuric Chloride Activation (Triazine Anchor)

**Rationale.** Cyanuric chloride (2,4,6-trichloro-1,3,5-triazine) is the
classical anchor for Cibacron Blue F3GA, Procion Red HE-3B, and other
reactive-dye pseudo-affinity ligands. The first chloride displaces a
matrix -OH or -NH₂; the remaining two are partially hydrolysed or
displaced by the dye chromophore.

**SDS-lite.**
- Hazards: severe respiratory and skin sensitiser; acute aquatic toxicity;
  releases HCl on hydrolysis.
- PPE: butyl-rubber gloves, splash goggles, fume hood, lab coat.
- Waste: aqueous neutralised; do NOT mix with reductants or amines outside
  the planned reaction.

**Recipe (per gram dry matrix).**
1. Equilibrate matrix in **acetone or DMF** (dry organic solvent).
2. Add cyanuric chloride at **5 mM** in the same dry solvent.
3. React **30 min at 0–4 °C** with gentle agitation.
4. Wash sequentially with the dry solvent → 50:50 dry solvent / water →
   water (5 column volumes each).
5. Couple the dye-amine in **0.1 M sodium carbonate, pH 9.5, 4 h at 25 °C**.
6. Block residual chlorides with **1 M ethanolamine, pH 9.0, 2 h at 25 °C**.
7. Wash thoroughly to remove unreacted dye until A₆₂₀ baseline (Cibacron
   Blue) or A₅₃₆ baseline (Procion Red) is reached in the wash.

**Mass-balance check.** Spectrophotometric dye loading by depletion:
`coupled_dye = A_initial − A_final` at the dye's λ_max.

### J.11.3 Genipin Secondary Crosslinking

**Rationale.** Genipin reacts with primary amines (chitosan, lysine
side-chains) to form a stable blue crosslink network. Useful as a
secondary post-coupling crosslink to lock in the M2 functional state;
slow (24 h), mild, biocompatible. Native blue colour from the genipin
chromophore is a useful coupling indicator but interferes with A₅₈₀-band
measurements downstream.

**SDS-lite.**
- Hazards: low acute toxicity; staining; skin sensitisation rare.
- PPE: nitrile gloves, lab coat.
- Waste: aqueous; standard biological-waste channel.

**Recipe.** 2 mM genipin in the post-coupling buffer (pH 5–7), 24 h at
37 °C with gentle agitation. Confirm crosslinking by visible blue colour
intensifying (A₅₈₀ rise plateau) and by a swelling-ratio drop of
20–40%.

### J.11.4 Borax Reversible Crosslinking — TEMPORARY POROGEN ONLY

**Critical safety / scientific note.** Borax (sodium tetraborate)
forms borate-cis-diol esters with adjacent -OH pairs (mannitol-class
diols, agarose, dextran). These crosslinks are **REVERSIBLE**:

- Stable at **pH > 8.5**.
- Dissociate at **pH < 8.5** OR in the presence of competing
  diols / sugars.

Borax-crosslinked beads cannot survive normal chromatography elution
(typical bind/wash buffers are pH 7.4). Use borax ONLY as a temporary
porogen / model network during synthesis, then **always** lock in
the structure with a covalent secondary crosslink (BDDE / ECH /
DVS) before downstream packing.

**SDS-lite.**
- Hazards: reproductive toxicant (Cat. 1B in EU); skin and eye
  irritant.
- PPE: nitrile gloves, splash goggles.
- Waste: aqueous neutralised.

**Recipe.** 50 mM borax buffer, pH 9.5, 1 h at 25 °C. Confirm the
network is in place by transient swelling-ratio drop, then **trigger
the covalent secondary crosslink immediately afterwards**:

- BDDE: 2% v/v in 0.1 M NaOH, 4 h at 50 °C.
- ECH: 5% v/v in 0.5 M NaOH, 6 h at 40 °C.
- DVS: 100 mM in 0.5 M Na₂CO₃, pH 11, 1 h at 25 °C.

Wash with water and 0.1 M acetic acid (pH 4 — drops the borax) until
A₂₃₀ baseline.

### J.11.5 HRP / H₂O₂ / Tyramine Phenol-Radical Crosslinking

**Rationale.** Horseradish peroxidase (HRP) catalyses the formation of
phenoxy radicals from tyramine in the presence of H₂O₂; these radicals
couple to tyrosine residues and to other tyramine molecules, forming a
covalent network. Useful for hyaluronate (HA) bead formation per
Sakai et al. 2009.

**SDS-lite.**
- HRP: low acute toxicity; allergen.
- H₂O₂: corrosive; oxidiser; release O₂ on contact with reductants.
- Tyramine: mild; controlled in some jurisdictions (vasoactive amine).
- PPE: nitrile or butyl gloves, splash goggles, fume hood for H₂O₂
  handling.

**Recipe.** Tyramine pre-conjugated to the polymer (HA-tyramine, 5–10%
loading typical). Initiate with HRP (1 µg/mL) + H₂O₂ (1 mM) in PBS at
pH 7.4, 25 °C, 10–30 min. Quench by adding catalase (10 µg/mL) and
washing.

### J.11.6 AlCl₃ Trivalent Gelant — NON-BIOTHERAPEUTIC RESEARCH USE ONLY

**Critical safety / scientific note.** Al³⁺ forms strong ionic crosslinks
with carboxylate-bearing polymers (alginate, gellan, pectin) by
bridging 3 carboxylates per Al³⁺ — stronger than Ca²⁺. The resulting
gel is mechanically tougher.

**However**, residual aluminum is regulated by FDA (oral and parenteral
limits) and EP (parenteral grade specifications). The
`biotherapeutic_safe = False` flag in the ion-gelant registry blocks
AlCl₃ from default workflows. Use only for research / non-biotherapeutic
applications (food gels for which aluminum residue is documented and
acceptable, or disposable / non-implant matrices).

**SDS-lite.**
- AlCl₃: corrosive; releases HCl on hydrolysis.
- PPE: butyl gloves, splash goggles, fume hood for the anhydrous form.

**Recipe.** 10 mM AlCl₃ external bath, pH 4–5, 5 min at 25 °C. Wash
with water until conductivity baseline. **Always assay residual Al by
ICP-MS or aluminium-specific spectrophotometry before approving the
batch for any contact with biotherapeutic processes.**

### J.11.7 Glutathione Coupling for GST-Tag Affinity

**Rationale.** GST-tagged fusion proteins bind glutathione with µM
affinity. Glutathione is coupled to an epoxide-activated matrix via
its thiol. Eluted by 5–10 mM reduced glutathione in PBS.

**SDS-lite.**
- Glutathione: low toxicity; air-sensitive (oxidises to GSSG).
- PPE: standard.

**Recipe.** Activate matrix with epichlorohydrin or BDDE per § J.1.2 /
§ J.1.3. Couple glutathione at **20 mM in 0.1 M sodium carbonate,
pH 8.5–9.0, 16 h at 25 °C** under inert (N₂) atmosphere. Wash with
PBS until A₂₈₀ baseline.

### J.11.8 Calmodulin Coupling for CBP / TAP Tag Affinity

**Rationale.** Calmodulin binds calmodulin-binding-peptide (CBP) tags
in the presence of Ca²⁺ and elutes when EGTA chelates the Ca²⁺. Used
in the TAP (tandem affinity purification) workflow.

**SDS-lite.**
- Calmodulin: low toxicity; protein.
- EGTA: low toxicity; chelator.
- PPE: standard.

**Recipe.** Activate matrix with NHS-ester chemistry (per § J.3.1).
Couple calmodulin at **2 mg/mL in PBS + 1 mM CaCl₂, pH 7.4, 4 h at
4 °C**. Wash with **PBS + 1 mM CaCl₂** to remove uncoupled protein.
Elute bound CBP-tagged target with **PBS + 5 mM EGTA**.

### J.11.9 Cibacron Blue / Procion Red Dye Pseudo-Affinity Coupling

**Rationale.** Cibacron Blue F3GA binds NAD-binding-pocket proteins
(albumin, lactate dehydrogenase, hexokinase) via a pseudo-affinity
interaction with the dianionic dye-NAD mimicry. Procion Red HE-3B has
similar chemistry with broader specificity.

**SDS-lite.**
- Cibacron Blue F3GA: stains skin, clothing, lab surfaces. Low acute
  toxicity. Once on a surface, removal requires bleach.
- Procion Red HE-3B: same. Persistent staining.
- PPE: nitrile gloves, lab coat (designated dye coat — not your
  primary). Eye protection.

**Recipe.** Activate matrix with cyanuric chloride per § J.11.2.
Couple the dye at **5 mM in 0.1 M sodium carbonate, pH 9.5, 4 h at
25 °C**. Wash exhaustively with water + 1 M NaCl until A₆₂₀ (Cibacron)
or A₅₃₆ (Procion) baseline. **Run a triazine-leakage check** (per
`triazine_dye_leakage_advisory` reagent) at the end of every batch:
load 10 column volumes of clean elution buffer and assay the eluate
spectrophotometrically.

### J.11.10 MEP HCIC (4-Mercaptoethylpyridine) Mixed-Mode

**Rationale.** MEP (4-mercaptoethylpyridine) is a hydrophobic charge-
induction chromatography (HCIC) ligand. At neutral pH the pyridine
nitrogen is uncharged and the ligand binds proteins hydrophobically;
on acidic elution the pyridine protonates and electrostatic repulsion
releases the bound protein. Useful for IgG capture without using
expensive Protein A.

**SDS-lite.**
- MEP: thiol; oxidisable; mild irritant.
- PPE: standard, plus inert (N₂) atmosphere for thiol coupling.

**Recipe.** Activate matrix with DVS or vinyl-sulfone chemistry per
§ J.1.4 / § J.2.3. Couple MEP at **20 mM in 0.1 M phosphate, pH 8,
12 h at 25 °C** under N₂. Wash with PBS. Bind feed at pH 7.4; elute
at pH 4.0 (typical capture of polyclonal IgG: 30–50 mg/mL resin).

### J.11.11 Thiophilic 2-Mercaptoethanol Ligand

**Rationale.** A thiophilic ligand (T-Gel, T-Sorb) is a divinyl-sulfone-
spaced thioether-sulfone group that binds IgG and other antibodies via
a sulfone-sulfur interaction. Captures IgG at high salt; elutes at low
salt. Mild; preserves activity well.

**SDS-lite.**
- Vinyl sulfone: irritant; fumehood handling per § J.1.4.
- 2-Mercaptoethanol: stench; toxic; fumehood mandatory.
- PPE: butyl gloves, fume hood, splash goggles.

**Recipe.** Activate matrix with DVS per § J.1.4. Couple
2-mercaptoethanol at **100 mM in 0.5 M Na₂CO₃, pH 11, 6 h at 25 °C** in
the fume hood. Wash with water + 1 M NaCl until A₂₃₀ baseline. Bind
feed at **0.5 M (NH₄)₂SO₄, pH 7.5**; elute by stepping to **PBS, pH
7.5** (low salt).

### J.11.12 m-Aminophenylboronic Acid (APBA) Boronate Affinity

**Rationale.** Boronate ligands form reversible covalent esters with
cis-diol-containing analytes: glycoproteins, sugars, catecholamines,
and ribose-bearing nucleosides. Bind at pH 8–9 (B(OH)₄⁻ tetrahedral
form); elute at pH 5 (trigonal B(OH)₃ form, no diol-binding) or with
sorbitol / fructose displacement.

**SDS-lite.**
- m-Aminophenylboronic acid (APBA): low acute toxicity; mild irritant.
- PPE: standard.

**Recipe.** Activate matrix with epichlorohydrin per § J.1.2. Couple
APBA at **50 mM in 0.1 M sodium borate, pH 9.0, 16 h at 25 °C**. Wash
with **0.1 M NH₄OAc, pH 8.5**. Bind feed at pH 8.5 in the same buffer;
elute at **0.1 M NH₄OAc, pH 5** OR **0.5 M sorbitol** in the same pH-8.5
buffer.

### J.11.13 Oligonucleotide DNA Affinity Coupling

**Rationale.** Sequence-specific DNA ligands capture DNA-binding
proteins (transcription factors, restriction enzymes). The
oligonucleotide is amine-modified at the 5' end and couples to a
CNBr- or NHS-ester-activated matrix.

**SDS-lite.**
- DNA: low acute toxicity; standard nuclease precautions.
- PPE: gloves to prevent nuclease contamination.

**Recipe.** Activate matrix with CNBr (per § J.1.1) or NHS-ester
(per § J.3.1). Couple **5'-amine oligonucleotide at 100 µM in 0.1 M
sodium phosphate, pH 8.0, 4 h at 25 °C** in nuclease-free conditions.
Wash with **TE buffer + 0.5 M NaCl** until A₂₆₀ baseline. Always
quench with 0.1 M Tris pH 8 to passivate residual reactive groups.

### J.11.14 Material-as-Ligand: Amylose (MBP) and Chitin (CBD-Intein)

**Rationale.** In the material-as-ligand (B9) pattern the polysaccharide
matrix IS the affinity ligand:

- **Amylose** binds MBP-tagged fusion proteins via its β-1,4-glucan
  helix. Eluted by 10 mM maltose in the bind buffer.
- **Chitin** binds CBD-tagged fusions (NEB IMPACT system) via the
  N-acetylglucosamine-binding face of the chitin-binding domain.
  Self-cleavage by thiol-induced intein splicing gives untagged
  product directly off-column.

No coupling chemistry is required — the bead IS the affinity ligand.
The corresponding M1 family solvers (`AMYLOSE`, `CHITIN`) handle bead
formation; the M2 reagent profiles (`amylose_mbp_affinity`,
`chitin_cbd_intein`) carry the binding-equilibrium parameters that
M3 consumes.

**Recipe (capture).**
- Amylose: bind in PBS, pH 7.4, 25 °C; elute with **10 mM maltose** in
  the same buffer.
- Chitin (with intein): bind in PBS + 1 mM EDTA + 0.5 M NaCl, pH 7.5,
  25 °C; **trigger self-cleavage** by adding **50 mM DTT** (or β-ME)
  in the same buffer, incubate 16 h at 4 °C, collect the eluate
  (untagged target).

**SDS-lite.** Both polysaccharides: low toxicity, standard handling.
DTT and β-ME: standard reductant precautions per § J.6.*.

---

*End of J.11 v0.3.x Addendum.*

*End of Appendix J.*
