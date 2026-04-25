# Scientific Advisor Review: Rushton-in-Baffled-Tank Cross-Section Fidelity

**Skill:** /scientific-advisor
**Inputs:** `docs/handover/ARCH_v0_4_0_UI_OPTIMIZATION.md`; `.dpsim_tmp/design_handoff/project/components.jsx` lines 804–1168 (`ImpellerCrossSection`); `direction-a.jsx` integration as M1 hardware visualisation for polysaccharide double-emulsion microsphere fabrication.
**Audience:** /architect → /dev-orchestrator → /scientific-coder building module **M-007** (`components.impeller_xsec`).
**Status:** REVIEW COMPLETE. Sign-offs and prescriptions follow.
**Date:** 2026-04-26

---

## 0. Terminology note

The user's "Baker-type stirring system" is read as the canonical fully-baffled stirred-tank reactor (BSTR) used in industrial mixing science — also commonly described in the literature as a **Rushton-disk-turbine in a fully-baffled cylindrical vessel with dished/torispherical bottom**. The standard geometry conventions follow Rushton, Costich & Everett (1950), refined by Nienow (Industrial Mixing, Wiley 2003), and Hemrajani & Tatterson (in *Handbook of Industrial Mixing*). All recommendations below assume this is the intended reference geometry. If "Baker-type" instead refers to a specific OEM tank (e.g. a Baker Perkins reactor), no recommendations need change — that geometry is essentially a fully-baffled BSTR.

---

## 1. Executive summary

The prototype's `ImpellerCrossSection` is a **scientifically defensible side-view caricature**, not a CFD-grade simulation. For a screening-tier (`semi_quantitative` evidence) UI it is on the right side of the line, but five items materially mislead a downstream-processing scientist and must be corrected before M-007 is shipped:

| # | Finding | Severity | Section |
|---|---|---|---|
| F-1 | **Impeller-to-tank ratio D/T = 0.6 violates the Rushton standard (D/T ≈ 1/3)**; this changes the physics qualitatively (not just quantitatively) | HIGH | §A |
| F-2 | **Blade asymmetry (upper 2 × lower) is not Rushton geometry** — real Rushton blades are symmetric about the disk plane (D/10 above + D/10 below) | HIGH | §A |
| F-3 | **Centre-shaft surface vortex dip is wrong for a fully-baffled tank** — baffles suppress the deep vortex; only a small chevron-shaped "cusp" near the shaft survives | HIGH | §A |
| F-4 | **Baffles drawn as two side-strips inside the liquid mislead the user** about the 4-baffle / 90° azimuth convention; in a side-view, only the two in-plane baffles are visible and they sit *flush against the wall*, not floating in the liquid | MEDIUM | §A |
| F-5 | **Drop break-up rendered only at the blade tips misses the dominant trailing-vortex zone** (Wu & Patterson 1989: ε in trailing vortices is 10–100 × the spatial average) | HIGH | §B |

In addition, two affordances are **missing from the prototype** that are cheap to add and materially improve the scientific story:

- **Trailing-vortex pair behind each blade** (visualised as two dashed counter-rotating sub-loops just downstream of each blade tip) — this is where most of the break-up actually happens.
- **High-shear "discharge zone" annulus** drawn around the impeller plane out to ~0.7 × R_tank — colour-coded by Kolmogorov microscale η to anchor the visual to drop-breakup physics.

The trajectory pattern (four macro-loops in 2D cross-section: two on each side of the shaft) is **fundamentally correct** in the prototype — the figure-8 description in the source comments is accurate to the physics of radial discharge from the Rushton disk. **Keep**.

The four /architect §12 questions are answered in §3 below.

---

## 2. Scope and assumptions

- **System.** Polysaccharide double-emulsion microsphere fabrication. Continuous oil phase (μ_c ≈ 1–10 cP, ρ_c ≈ 850–1000 kg/m³). Dispersed aqueous polymer phase containing agarose / chitosan / alginate / similar (μ_d ≈ 5–500 cP depending on concentration and temperature, ρ_d ≈ 1000–1100 kg/m³). Interfacial tension σ ≈ 5–40 mN/m with surfactant (Span 80 / PGPR / Tween).
- **Operating envelope.** N = 100–1200 rpm (1.7–20 rev/s); D_I = 30 mm; T ≈ 50 mm in the prototype (note: this is *bench-scale*, characteristic Re_imp = ρ_c N D² / μ_c spans ~1 500 → 18 000, i.e. transitional to turbulent — Hinze-regime drop breakup applies above Re_imp ≈ 10⁴).
- **Physics scope.** This advisory addresses the *visual fidelity* of a cross-section animation. It does **not** redesign the underlying L1 emulsification PBE solver (`level1_emulsification/`), which already handles Hinze / Calabrese / Davies regime selection in the kernel.
- **Evidence tier of the visual.** `semi_quantitative` — the visual conveys *direction and qualitative shape* of phenomena. It should not be read off as carrying numerical claims (e.g. "the visual shows ε contour, therefore ε = X here"). Honest simplifications are acceptable; misleading simplifications are not.
- **What is out of scope.** Three-dimensional turbulence-resolving rendering, coalescence kernels (briefly mentioned in §B as a "flag" item), chemical kinetics of gelation (M3 territory), and any thermal effects.

---

## 3. Sign-off on architecture-plan §12 open questions

### Q1 — Cross-section physical fidelity

**Status:** REVISION REQUIRED before vendoring `components.jsx` ImpellerCrossSection into M-007. See §A and §B below for the prescriptive change list. The flow-direction model is correct; the geometry has two HIGH-severity defects (D/T ratio, blade asymmetry) and one HIGH-severity defect about the surface vortex.

### Q2 — Column elution visual semantics

**Verdict:** Both should be retained *together*, but with a clearer narrative. Specifically:

- **Bead recolour as the front passes** — KEEP. This is the right way to show *bound payload concentration on the resin*. It matches what an LRM solver outputs at each axial slice.
- **Distinct streaming dots flowing out the bottom** — KEEP, but only *during* elute / wash / CIP, never during load. During elute, the streaming dots represent *eluate-phase target concentration C(t,z)* leaving the bed; during wash they represent flushed impurities; during CIP they represent stripped residuals. The physical meaning differs by phase — the legend should say so.
- **Add** a thin horizontal dashed line *at the front position* labelled `c_front · CV` and a small inline annotation that disappears once the front has passed bedBottom. This makes the "bead recolour" event causally tied to the front, not just decorative.

The current prototype already does most of this; the gap is labelling. Update the on-screen legend per phase.

### Q3 — Evidence-tier roll-up UX

**Verdict:** The architect's third option (lifecycle-aggregated badge in the top bar with a hover-revealed per-stage breakdown) is correct. Rationale:

1. The lifecycle min is the *operational* number — it caps what every downstream metric can claim per `RunReport.compute_min_tier`. That is what someone reading "is this run quantitatively defensible?" wants to see at a glance.
2. The per-stage breakdown is the *diagnostic* number — it tells the user *which* stage is the rate-limiter on evidence quality, which is what they need to know to decide whether to run more wet-lab calibration.
3. Showing only the per-stage chips at the top would invite the eye to read the *highest* tier as the headline, which is exactly the inheritance violation that CLAUDE.md's enum-comparison rule and the scientific-advisor team built the v9.0 evidence model to prevent.

**Minor refinement:** make the per-stage hover panel use the same `EvidenceBadge` component so the colour mapping is consistent with the top-bar badge. Do not introduce a separate "diagnostic" colour scale.

### Q4 — Recipe-diff baseline scope

**Verdict:** Ship the simpler "diff vs last successful run" semantics in v0.4.0. Defer named baselines to v0.4.1.

Rationale:
- The user's pain is "did *this edit* change anything since I ran *just now*?" — last-successful-run is what they will compare against ≥80% of the time.
- Named baselines add (a) a CRUD surface for tagging baselines, (b) UI for choosing the baseline, (c) persistence to disk if the baseline is to survive a session restart. None of (a–c) is intrinsically hard, but together they push v0.4.0 over the milestone budget.
- **Caveat to surface in the diff panel:** if no prior run exists in the current session, the diff should explicitly say *"no baseline yet"* rather than diff-ing against the on-disk recipe (which would yield false positives every time the user modifies an in-memory parameter).

---

## A. Geometry fidelity — recommendations

### A.1 KEEP

| What | Why it is correct |
|---|---|
| Edge-on side-view convention (disk seen as a thin band; two of six blades visible at left and right tips) | Standard 2D cross-section of an axisymmetric agitator. A user familiar with Nienow Fig. 4-3 / Tatterson Fig. 12.4 will recognise it immediately. |
| Vertical shaft with drive cap above the liquid surface | Correct. The shaft penetrates the liquid; the drive coupling sits above. |
| Disk drawn with a hub (collar) on the shaft | Correct. The Rushton hub is what fixes the disk to the shaft and it is visually distinct. |
| Two glass-highlight strips on the wall | Cosmetic but signals "transparent vessel" — appropriate for a bench-scale beaker visualisation. The user iterated on this in chat round 8; keep. |
| Dished bottom rendered as `Q ${baseY}` curve segments | Correct. Real bench tanks use either flat or dished/torispherical bottoms; the dish is what avoids the "dead zone" at the tank corner. |
| Liquid level above the impeller (`liquidLvl + liquidH * 0.10` from top → impeller at `0.33` from bottom) | Reasonable. Standard recommendation is H/T = 1.0 (liquid height = tank diameter), which roughly matches the prototype's aspect. |

### A.2 REFINE

#### F-1 — D/T ratio

- **Current.** `vesselD = 50, impellerD = 30 → D/T = 0.6`.
- **Standard Rushton.** `D/T = 1/3 (≈0.33)`. Acceptable range 0.3–0.5; 0.6 is non-standard and produces a fundamentally different flow regime (impeller "fills" the tank, kills the four-loop pattern, and creates a more axial discharge near the wall).
- **Prescription.** Set `vesselD = 90, impellerD = 30` (D/T = 0.33, exact Rushton standard). The diagram aspect changes: the disk no longer dominates the visual width. Compensate by **rendering the diagram at a taller aspect ratio** (e.g. width = 200, height = 320) to keep the impeller readable.
- **Alternative.** If the user insists on the current visual aspect for layout reasons, expose a **subtle annotation** under the diagram: `D/T 0.60 · non-standard, illustrative only` so a downstream-processing scientist does not back-of-envelope a blend time from this geometry.

#### F-2 — Blade symmetry

- **Current.** `bladeAbove = 14, bladeBelow = 7` (2:1).
- **Standard Rushton.** Blade height W = D/5 (Rushton 1950); blades attached at disk periphery and **symmetric about the disk plane**, i.e. W/2 above and W/2 below.
- **Prescription.** Replace with `const bladeHalf = impellerW * 0.10; bladeAbove = bladeHalf; bladeBelow = bladeHalf;` (so total blade height = 0.20 × D_I = D/5, in agreement with Rushton standard). Concretely with `impellerW = 60` (in SVG px after the D/T fix above): `bladeAbove = 6, bladeBelow = 6`. The user's earlier-round complaint that "the blade extends too little above the disk" was satisfied by 2 × *the magnitude*; it can be satisfied identically by *symmetrically* increasing both halves.
- **Note for /architect.** The chat-round-9 user request "upper edge ≥ 2× longer than it is now" referred to *magnitude*, not *upper:lower ratio*. The implementer interpreted it as ratio. Symmetry restoration is a re-interpretation of the user's intent in light of physics; flag the change in the M-011 close handover so the user knows.

#### F-3 — Surface vortex with baffles

- **Current.** A central dip ("vortex") whose depth scales with rpm (`dip = Math.min(liquidH * 0.18, 2 + (rpm / 1200) * 14)`).
- **Physics.** In a **fully-baffled tank** (4 baffles, B/T = 1/12, full-height), the macroscopic free-vortex is broken — surface remains essentially flat to within ~5% of liquid depth, even at high rpm. What the user actually sees on a real bench-scale baffled-Rushton system is:
  - A small "cusp" or central depression at the shaft (a few mm deep) caused by the impeller's centripetal pumping right at the shaft.
  - A roughened/aerated upper surface (entrained air bubbles when v_tip > ~1 m/s), but no cone.
  - In *unbaffled* tanks, by contrast, the deep central vortex *is* what the prototype draws, and it scales roughly with N²D² / g (Froude scaling).
- **Prescription.**
  - When the visual labels itself "fully-baffled" / "Rushton-in-Baker": cap the surface dip at `liquidH * 0.04` (small cusp), make it scale weakly with rpm (e.g. `0.5 + (rpm / 1200) * 1.2` in SVG px), and add 1–2 small white circles inside the cusp to suggest entrained-air microbubbles at high rpm.
  - Add a one-line caption beneath the diagram: `4-baffle BSTR · vortex suppressed`.
  - Optional V2: include a `Vessel mode` / `Baffles` toggle that, when set to "unbaffled", restores the deep vortex and removes the baffles. This is genuinely instructive — it shows users *why* baffles exist. Out of scope for v0.4.0; flag for v0.4.x.

#### F-4 — Baffle representation

- **Current.** Two thin vertical strips placed inside the liquid at `f = 0.20` and `f = 0.80` (`width: 2.4`, separated from the wall).
- **Physics.** Real baffles are flat plates *bolted against the inner wall*, B/T ≈ 1/12 wide, projecting radially inward by ~B. They are full liquid-depth (sometimes with a small gap at top and bottom). In a **side-view 2D cross-section through the centre-line of two opposing baffles**, the baffles read as **flush rectangles against the inner wall faces**, not as floating strips inside the liquid.
- **Prescription.** Move both baffles to abut the wall (left baffle: `x = wallLeft + 0.5`; right baffle: `x = wallRight - B - 0.5`). Set `B = tankW / 12` (≈ 4 px in current scale; widen to 5–6 px for visual readability). Add a tiny `ǁ` mark or label `B/T ≈ 1/12 · 4× @ 90°` outside the diagram to reassure the viewer that the side-view shows two of the four baffles. The other two are perpendicular to the page plane — **add a small azimuth icon top-right showing four baffles in plan-view** (a circle with four short tangential strokes at 0°/90°/180°/270°), 24×24 px. This single icon resolves the "side-view ambiguity".

### A.3 ADD

| Add | Where | Why |
|---|---|---|
| Plan-view azimuth icon (small circle with 4 baffles at 0°/90°/180°/270°) | Top-right corner of the diagram, 24×24 px | Resolves the F-4 ambiguity in one glance. Standard convention in mixing textbooks. |
| Off-bottom clearance label `C/T = 1/3` near the impeller-to-base distance | Inside the diagram, 9 px monospace text to the right of the impeller | The clearance C is one of the three numbers (D, C, baffle width) that fully specifies a Rushton geometry. Showing it makes the visual self-documenting. |
| Reynolds-number readout next to the existing `v_tip` and `Re` chips | Already present — but **label `Re` as `Re_imp = ρND²/μ`** explicitly so the user can audit the formula | The existing `Re` value is a tip-Reynolds; tip Re and impeller Re differ by π. Be explicit. |

### A.4 REMOVE

| Remove | Why |
|---|---|
| The deep central vortex when the visual is labelled "fully-baffled" | F-3: it is wrong physics for the labelled geometry and would mislead a user back-calculating power consumption. |
| The "back arc of rim" dashed ellipse | This is genuinely confusing in a 2D cross-section. The intent (showing the front rim curves down, hidden back rim curves up) is fine for an isometric, but a *cross-section* by definition slices the vessel in half through a vertical plane — there is no "back rim" because the geometry behind the slice plane is not drawn. **Replace** with a simple horizontal line at the rim, or omit. |
| The "right-wall faint glass highlight" if it is on the same vertical as the right baffle | Visual collision with the relocated baffle (per F-4). Either remove or move the highlight to a non-baffled azimuth. |

---

## B. Mechanical microsphere disruption mechanism

### B.1 Regime classification (decisive for what to draw)

For the DPSim operating envelope (N = 100–1200 rpm, D = 30 mm, μ_c = 1–10 cP, σ = 5–40 mN/m, μ_d up to ~500 cP for concentrated polysaccharide), the dominant break-up regime is the **Hinze inertial-subrange regime** (Hinze 1955; Davies 1985 with viscous correction; Calabrese et al. 1986 for high-viscosity dispersed phase):

- **Hinze maximum stable diameter:** `d_max = (We_crit · σ / ρ_c)^(3/5) · ε^(-2/5)` for inertial subrange where `d > η_K` (Kolmogorov microscale).
- **Calabrese viscous correction (μ_d significant):** `d_max = (We_crit / ρ_c)^(3/5) · σ^(3/5) · ε^(-2/5) · [1 + B · (μ_d / μ_c)^(1/2) · (d_max · ε^(1/3) · ρ_c^(1/2) / σ^(1/2))]^(3/5)`.
- **Where ε is concentrated.** Wu & Patterson (1989) / Ducci & Yianneskis (2005): in a Rushton + baffled tank, the *spatial-average* ε is ~10⁻¹ W/kg at typical conditions, but the **trailing-vortex pair behind each blade** carries ε_max ≈ 10–50 × ε_average, and the **impeller-discharge stream** out to ~0.7 R_tank carries ε ≈ 3–10 × ε_average. The bulk recirculation zones away from the impeller are quiescent (ε ≪ ε_average).

### B.2 Implication for the visual

The prototype's "break-up only happens at blade tips" is **incomplete and slightly wrong-headed**. In real Rushton emulsification, drop break-up happens predominantly in:

1. **The trailing-vortex pair behind each blade** (≥50% of break-up events per residence cycle).
2. **The radial discharge stream** out to ~0.7 R_tank (next ~30%).
3. **The bulk turbulent zones** away from the impeller (small contribution, but where coalescence dominates if surfactant is sub-critical).

### B.3 KEEP

- The "shear tier" colour-coding (`low/med/high` mapped to sky/teal/amber) on the **tip-discharge arrows**. Correct semantically — the arrows mark the high-shear region.
- The "droplets recolour to shearColor when passing through the impeller plane" rule. **Keep but expand its trigger zone** — see B.4.
- The `v_tip` readout strip at the bottom and the LOW/MED/HIGH SHEAR badge. The threshold (0.6 m/s, 1.2 m/s) maps roughly to typical Rushton boundaries between transitional and fully-turbulent break-up: ε scales with N³ D², and at v_tip ≈ 1 m/s in a 30-mm impeller the impeller-zone ε crosses ~1 W/kg, the threshold above which Hinze-regime break-up dominates.

### B.4 REFINE

#### Drop-recolour trigger zone

- **Current.** A droplet recolours to shearColor when `Math.abs(y - diskCY) < 6 && Math.abs(Math.abs(x - cx) - diskHalfW) < 8` — i.e. only within a ±6 px vertical band around the disk and within ±8 px horizontally of each blade tip.
- **Refined.** Expand the trigger to the full impeller-discharge annulus on each side: `y in [diskCY - 0.4 · liquidH, diskCY + 0.4 · liquidH]` AND `|x - cx| in [diskHalfW, 0.7 · tankW/2]`. This matches Wu & Patterson's high-ε annulus. To avoid colour saturation everywhere, fade the recolour intensity linearly from 100% at the blade tip to 30% at 0.7 R_tank.
- **Visual clue.** Render this annulus as a faint translucent shaded band (`opacity 0.06`, `fill = shearColor`) so the user sees the high-shear *region*, not just the *droplets that happen to be there*.

#### Blade-tip arrows

- **Current.** Single arrow per blade tip, length 12 px, pointing radially outward.
- **Refined.** Pair the radial discharge with a faint **counter-rotating sub-arrow** just downstream of each blade tip, ~10 px aft, curving in the opposite direction — this is the trailing vortex axis. Render with `strokeDasharray 1 2`, length ~8 px, opacity 0.7. The user sees that the discharge is not a clean jet but creates a vortex pair.

### B.5 ADD

#### Trailing-vortex pair (CRITICAL — this is finding F-5)

- **Where.** Two small counter-rotating closed-curve loops just behind each blade, in the impeller plane (i.e. centred at `(cx ± diskHalfW * 1.3, diskCY)` with vertical extent ±5–7 px).
- **How to draw.** Each loop is a tear-drop or small closed Bézier, animated with `strokeDasharray` cycling at ~3 × the macro-loop dash speed (because trailing vortices are higher frequency than the bulk recirculation). Colour: shearColor at 0.55 opacity.
- **Why.** This is *the* place most break-up happens. Rendering it visually anchors the M1 hardware screen to the actual emulsification kernel. Wu & Patterson 1989, Lee & Yianneskis 1998.
- **Tooltip on hover.** "Trailing-vortex pair · ε_max ~10–50× spatial average. Most drop-break-up events occur here (Wu & Patterson 1989)."

#### High-dissipation discharge band

- **Where.** A faint shaded annulus in the impeller plane out to ~0.7 R_tank as described in B.4.
- **Animation.** Optional. The shaded band itself need not animate; the droplets passing through it will provide the motion cue.

### B.6 REMOVE

| Remove | Why |
|---|---|
| The "droplets travel at constant size around the loops" implicit assumption (no current visual representation, but the absence of size change is itself misleading) | A droplet that has passed through the impeller plane should be *smaller* than one that has not. **Add** (not remove): randomly re-seed each droplet's `size` field to a smaller value when it passes through the trigger zone. Even a 30% size reduction on impeller passage is a vastly more honest visual. |

### B.7 FLAG (do not implement, but document)

- **Coalescence is not represented.** In a real surfactant-stabilised emulsion, break-up rate ≈ coalescence rate at steady state — the d_max evolves to a dynamic equilibrium, not a one-way decrease. The prototype shows only break-up. **Acceptable** for screening (the underlying solver does include coalescence kernels — the *visual* is a simplification). Add a one-line caveat in the M-011 close handover and in the on-screen tooltip: `Visual shows break-up only · coalescence balance handled in solver · Lemenand 2003`.

---

## C. Microsphere trajectory pattern

### C.1 KEEP

#### The four-loop macro-recirculation pattern

The prototype's core flow model — **two adjacent vertical loops on each side of the shaft (so four macro-loops in 2D)** — is **fundamentally correct** for a Rushton + fully-baffled tank. The flow is:
1. Radial discharge from blade tips outward to the wall.
2. Wall impingement → split into upward (above-impeller) and downward (below-impeller) streams.
3. Upper stream rises along the wall, traverses the surface inward, descends along the shaft, returns to the impeller from above.
4. Lower stream descends along the wall, traverses the bottom inward, ascends along the shaft, returns to the impeller from below.

This is the canonical Rushton flow described in Rushton (1950) and confirmed by every LDA and PIV measurement since (Yianneskis et al. 1987; Schäfer et al. 1997; Roussinova et al. 2003). **Keep verbatim.**

#### The dashed-stroke + arrowhead animation convention

Communicates direction unambiguously and is consistent with how mixing textbooks render flow patterns. **Keep.**

### C.2 REFINE

#### Loop asymmetry under the dished bottom

- **Current.** The upper and lower loops are roughly the same vertical extent.
- **Physics.** The lower loop is constrained by the dished bottom; in real systems the lower-loop turning radius at the bottom is roughly 0.5–0.7 × the upper-loop turning radius at the surface.
- **Prescription.** Make `lowerLoopY = tankBottomY - liquidH * 0.13` (slightly closer to the bottom than current `0.10`), and **add a Bézier handle at the dish-bottom corners** so the lower loop's path follows the dish geometry, not a sharp 90° turn. ~3 lines of SVG path-d adjustment.

#### Stokes-number-aware droplet motion

- **Current.** Droplets follow loop streamlines exactly.
- **Physics.** For polysaccharide microspheres in oil at typical DPSim conditions:
  - Droplet diameter d ≈ 50–100 µm.
  - Density difference Δρ ≈ |ρ_d - ρ_c| ≈ 100–200 kg/m³ (aqueous-in-oil).
  - Continuous-phase viscosity μ_c ≈ 1–10 cP.
  - Characteristic flow timescale τ_f ≈ L/U ≈ 0.05 m / 1 m/s = 0.05 s.
  - Stokes number St = (ρ_d · d² · U) / (18 · μ_c · L) ≈ 10⁻³ → 10⁻². **St ≪ 1 → droplets follow streamlines essentially as tracers.**
- **Verdict.** The prototype's "droplets ride the streamlines" is **correct** for typical DPSim conditions. **Keep**.
- **Caveat for high-viscosity continuous-phase regimes.** If the user enters μ_c ≥ 50 cP (rare but possible for some polysaccharide-in-PDMS systems), St rises and droplets begin to deviate from streamlines. Worth a one-line note in the M-011 close handover; not worth implementing in v0.4.0.

### C.3 ADD

#### Impeller-zone passage frequency annotation

- **Where.** A small, secondary readout next to `v_tip` showing `f_pass ≈ N_Q · N · 4 / V_liquid`, where N_Q ≈ 0.75 is the Rushton pumping number. At N = 420 rpm, D = 30 mm, V_liquid ≈ 100 mL: f_pass ≈ 0.75 × 7 × (π × 0.030³ / 4) × 4 / 100e-6 ≈ 6 passes per second per parcel. Display as `f_pass ≈ 6 Hz` or `~6 passes/s`.
- **Why.** Drop-breakup kinetics in PBE solvers are driven by passage frequency through the high-shear zone. Surfacing this number in the UI ties the visualisation to the underlying solver's input parameter set.
- **Source.** Calabrese et al. 1986; Maaß et al. 2011 (review of breakage models in stirred tanks).
- **Tooltip.** "Impeller-zone passage frequency. Each droplet visits the high-shear zone ≈ N_Q × N × (π D³/4) × 4 / V_liquid times per second on average. Drives drop-breakup kinetics in the population-balance solver."

#### Dead-zone shading at the dish-corner radii

- **Where.** A faint translucent shaded region in each lower corner (`opacity 0.05`, `fill = "rgba(148,163,184,0.5)"`), roughly a 15-px-radius triangle at each `(wallLeft, tankBottomY)` and `(wallRight, tankBottomY)`.
- **Why.** Real bench-scale Rushton tanks have stagnant zones at the dish corners — droplets that get parked there are out of the high-shear zone for several seconds. Rendering them invites the user to ask "should I move my impeller closer to the bottom?" — exactly the engineering question the M1 hardware screen is supposed to support.
- **Tooltip.** "Stagnant corner · droplets trapped here are not refreshed by the macro-loop. Reducing C/T from 1/3 to 1/4 shrinks this zone (Tatterson 1991)."

### C.4 REMOVE

| Remove | Why |
|---|---|
| The "smooth Bézier from tip to wall to upper-loop-Y to shaft" pattern, in favour of explicit segment endpoints | The current implementation is fine, but it draws the recirculation as a *single* Bézier per loop. Real Rushton flow has **two distinct turning regions** (tip → wall, then wall → surface). Splitting into two segments per loop (already done in `sampleLoop`, but not in the rendered SVG path) makes the visual match the trajectory math. The droplet sampler is correct; the visible path should mirror it. |

### C.5 Two specific path adjustments

For the M-007 implementer, the upper-loop path should be `M tip → Q midwall → wall → L upper → Q midsurface → shaft → L tip`. The current `M tip → Q ... wall → L wall → Q ... shaft → L tip` is structurally fine; just ensure the **upper-loop midsurface control point** is *above* the rim ellipse, not on it (otherwise the loop appears to "exit" the liquid). Set `controlY = liquidLvl - 4` to keep the curve cleanly inside.

Lower-loop equivalently: midbottom control point at `tankBottomY + 4` (i.e. just below the apparent dish, since the cross-section continues inside the dish profile).

---

## 4. Implementation guidance for /scientific-coder

When M-007 is built, the following ordering minimises rework:

1. **Geometry first.** Apply F-1 (D/T), F-2 (blade symmetry), F-4 (baffle position), and the `azimuth icon` add. Run a visual diff against the prototype screenshots in `.dpsim_tmp/design_handoff/project/screenshots/` and confirm the diagram still reads as a stirred tank.
2. **Surface-vortex correction (F-3).** Apply with the small-cusp formula. Test at N = 100, 600, 1200 rpm — the cusp should be visually undetectable at 100 rpm and a barely-visible 1–2 px depression at 1200 rpm.
3. **Trailing-vortex pair (B.5 ADD).** Independent of geometry; add as two new SVG `<path>` elements per side. ~25 lines of SVG.
4. **Discharge annulus shading (B.4).** A single translucent rectangle behind the existing flow lines.
5. **Droplet-size shrinkage on impeller passage (B.6).** Modify the `droplets.useMemo` to track an `originalSize` and a current `size`, decrement on impeller-plane crossing.
6. **Passage-frequency readout (C.3 ADD).** Add a third row to the existing `v_tip` strip; ~3 lines of SVG `<text>`.
7. **Loop-path refinement (C.5).** Adjust the existing two `<path>` elements per side; no structural change.

Estimate: total ~120 LOC of incremental SVG/JS edits to the vendored `ImpellerCrossSection`. Visual snapshot tests should be re-baselined per change.

---

## 5. References

Primary:

- Rushton, J. H., Costich, E. W., & Everett, H. J. (1950). *Power characteristics of mixing impellers*. Chemical Engineering Progress, 46, 467–476.
- Hinze, J. O. (1955). *Fundamentals of the hydrodynamic mechanism of splitting in dispersion processes*. AIChE Journal, 1(3), 289–295.
- Davies, J. T. (1985). *Drop sizes of emulsions related to turbulent energy dissipation rates*. Chemical Engineering Science, 40(5), 839–842.
- Calabrese, R. V., Chang, T. P. K., & Dang, P. T. (1986). *Drop breakup in turbulent stirred-tank contactors. Part I: Effect of dispersed-phase viscosity*. AIChE Journal, 32(4), 657–666.
- Wu, H., & Patterson, G. K. (1989). *Laser-Doppler measurements of turbulent-flow parameters in a stirred mixer*. Chemical Engineering Science, 44(10), 2207–2221.
- Yianneskis, M., Popiolek, Z., & Whitelaw, J. H. (1987). *An experimental study of the steady and unsteady flow characteristics of stirred reactors*. Journal of Fluid Mechanics, 175, 537–555.
- Lee, K. C., & Yianneskis, M. (1998). *Turbulence properties of the impeller stream of a Rushton turbine*. AIChE Journal, 44(1), 13–24.
- Schäfer, M., Yianneskis, M., Wächter, P., & Durst, F. (1997). *Trailing vortices around a 45° pitched-blade impeller*. AIChE Journal, 43(9), 2233–2244.
- Roussinova, V. T., Kresta, S. M., & Weetman, R. (2003). *Low frequency macroinstabilities in a stirred tank: scale-up and prediction*. Chemical Engineering Science, 58(11), 2297–2311.
- Ducci, A., & Yianneskis, M. (2005). *Direct determination of energy dissipation in stirred vessels with two-point LDA*. AIChE Journal, 51(8), 2133–2149.

Reviews and textbooks:

- Nienow, A. W., Edwards, M. F., & Harnby, N. (Eds.). (1997). *Mixing in the Process Industries* (2nd ed.). Butterworth-Heinemann.
- Paul, E. L., Atiemo-Obeng, V. A., & Kresta, S. M. (Eds.). (2004). *Handbook of Industrial Mixing: Science and Practice*. Wiley-Interscience.
- Tatterson, G. B. (1991). *Fluid Mixing and Gas Dispersion in Agitated Tanks*. McGraw-Hill.
- Maaß, S., Wollny, S., Voigt, A., & Kraume, M. (2011). *Experimental comparison of measurement techniques for drop size distributions in liquid/liquid dispersions*. Experiments in Fluids, 50, 259–269.
- Lemenand, T., Della Valle, D., Zellouf, Y., & Peerhossaini, H. (2003). *Droplets formation in turbulent mixing of two immiscible fluids*. International Journal of Multiphase Flow, 29(5), 813–840.

---

## 6. Sign-off

| Question / Section | Verdict |
|---|---|
| §A — Geometry | REVISION REQUIRED — apply F-1, F-2, F-3, F-4 and the listed adds before M-007 ships. |
| §B — Disruption mechanism | REVISION REQUIRED — apply trailing-vortex (B.5) and discharge-annulus (B.4) adds. Drop-shrinkage on impeller passage is the most cost-effective single fix. |
| §C — Trajectories | APPROVED with refinements — the macro-pattern is correct; apply the lower-loop dish geometry tweak (C.2) and add the passage-frequency readout (C.3). Stokes-number assumption (tracer-like) is correct for typical DPSim conditions. |
| §3 / Q1 — Cross-section fidelity | REVISION REQUIRED (per §A and §B above). |
| §3 / Q2 — Column elution semantics | APPROVED (with phase-dependent legend labels). |
| §3 / Q3 — Evidence-tier UX | APPROVED (architect's third option). |
| §3 / Q4 — Recipe-diff baseline | APPROVED ("last successful run" semantics; defer named baselines to v0.4.1). |

The architecture document `ARCH_v0_4_0_UI_OPTIMIZATION.md` may proceed to /dev-orchestrator with these revisions integrated into the M-007 protocol.

---

## 7. Disclaimer

This scientific analysis is provided for informational, research, and advisory purposes only. It does not constitute professional engineering advice, medical advice, or formal peer review. All hypotheses and experimental designs should be validated through appropriate laboratory experimentation and, where applicable, reviewed by qualified domain experts before implementation. Numerical estimates (D/T ratios, blade fractions, Stokes numbers, passage frequencies) are derived from canonical mixing-engineering literature; they are accurate at the screening tier but should not be used in safety-critical or regulatory contexts without site-specific calibration. The author is an AI assistant and the analysis should be treated as a structured starting point for further investigation.
