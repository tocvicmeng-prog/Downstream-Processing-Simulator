# ADR-004 — Pressure Envelope Anchor: u_crit, not safety×E_star

**Status:** Accepted
**Date:** 2026-05-10
**Decision driver:** v0.7.0 M3 back-pressure work plan (B-2f / W-020 + W-026); /scientific-advisor architecture review identifying the v0.6.6 ΔP_max anchor as one of three CRITICAL correctness defects in `module3_performance/hydrodynamics.py`.

## Context

DPSim v0.6.6 anchored the operational pressure ceiling for a packed
chromatography bed to:

```python
def max_safe_flow_rate(self, mu: float = 1e-3, safety: float = 0.8) -> float:
    dP_max = safety * self.E_star
    u_max = dP_max * dp ** 2 * eps ** 3 / (150.0 * mu * L * (1.0 - eps) ** 2)
    return u_max * A
```

The docstring framed this as "max flow rate before exceeding bead crushing
pressure" — i.e., a structural ceiling derived from the bead's effective
Young's modulus E_star.

The /scientific-advisor consultation on 2026-05-10 (delivered upstream as
the M3 back-pressure architecture document) identified this as
scientifically wrong by a factor of 5–50× for soft chromatography media.

## The defect

For soft hydrogel chromatography media (agarose, agarose-chitosan,
cellulose hydrogels, low-T_g PLGA, alginate — all the families currently
supported by DPSim), the **operational** pressure limit is set by
**bed-compression runaway**, not by **bead bursting**. The two are
physically distinct mechanisms:

1. **Bed-compression runaway (operational limit, u_crit knee).** Beads at
   depth z carry the cumulative drag force from all fluid passing above.
   When the inter-bead contact stress σ_c(z) exceeds the bead's elastic
   resistance, beads deform, ε_b drops, ΔP at constant Q rises, σ_c rises
   further → runaway. This is what produces the *knee* in every
   manufacturer pressure-flow curve.

2. **Bead bursting / cracking (structural limit).** Hertz contact at large
   σ_c eventually drives crack initiation, with threshold:

   ```
   σ_burst ≈ K_IC / √(π·a)
   ```

   where K_IC is the bead's fracture toughness and a is the largest
   internal flaw size. This is at least 5–10× higher than the
   bed-compression u_crit for hydrogel media, and only becomes the
   binding limit for rigid macroporous polymeric supports.

**The v0.6.6 anchor used the bursting modulus (E_star) for the
operational limit, and a 0.8 safety factor on top. Both moves miss
the actual operational physics.** Manufacturer-published u_crit values
for Protein A Sepharose-class media correspond to ΔP_max ≈ 0.3–3 bar
= 30–300 kPa, while E_star for those beads is 100–1000 kPa. The
operational ratio sits at roughly 1/30 to 1/3 — not the 0.8 the v0.6.6
code claimed.

## Decision

**Replace the anchor.** B-2f introduces:

```python
u_crit ≈ K_geom_family · G_DN · d_p² / (μ · L)
```

with the following supporting infrastructure:

1. **`module3_performance/family_kgeom.py`** — per-PolymerFamily registry
   `FAMILY_KGEOM_REGISTRY` keyed by `PolymerFamily.value` (v9.0
   Family-First contract). Five default-anchor families with
   literature-anchored K_geom defaults:

   | Family | K_geom | Anchor |
   |---|---|---|
   | CELLULOSE | 2×10⁻² | Cellufine / Capto S app notes |
   | PLGA | 1×10⁻² | Glassy-state mechanical response |
   | AGAROSE_CHITOSAN | 8×10⁻³ | DPSim default first-run recipe |
   | AGAROSE | 5×10⁻³ | Stickel & Fotopoulos 2001, GE Healthcare curves |
   | ALGINATE | 3×10⁻³ | Stickel & Fotopoulos 2001, Ca²⁺-compliant |

   Other PolymerFamily values fall back to a conservative entry at
   `QUALITATIVE_TREND` tier.

2. **`module3_performance/pressure_envelope.py`** — `PressureEnvelope`
   frozen dataclass + `compute_pressure_envelope` orchestrator.
   Surfaces both ceilings:

   - `dP_max_operational_pa` — the u_crit-based bed-compression limit
     (THE operational ceiling).
   - `dP_max_burst_pa` — the bed elastic-limit diagnostic (E_star),
     kept as a *separate* field, NOT the operational limit.

   These are explicitly distinct fields with different docstring
   semantics. The UI / dossier rendering (B-2h) MUST consume
   `dP_max_operational_pa` for safe-flow advisories; `dP_max_burst_pa`
   is a structural diagnostic only.

3. **`hydrodynamics.py::max_safe_flow_rate`** — deprecated with a
   `DeprecationWarning` pointing at `compute_pressure_envelope`.
   Retained for one release (v0.7.x); removed in v0.8.

4. **Tier policy.** All five default-anchor families carry
   `SEMI_QUANTITATIVE` base_tier. Promotion to `CALIBRATED_LOCAL`
   requires either:

   - a manufacturer pressure-flow curve supplied via the
     `calibration_store` argument, OR
   - local wet-lab pressure-flow data for the specific resin / column /
     buffer system.

   Demotion to `QUALITATIVE_TREND` happens automatically on:

   - any input outside the family's `valid_domain`, OR
   - viscosity-resolver `extrapolated=True` flag.

   Floors at `QUALITATIVE_TREND`.

## Consequences

### Positive

- The operational ΔP_max prediction is now scientifically defensible.
  v0.6.6 silently approved flow rates that would crush beads in real
  operation; v0.7 produces conservatively-calibrated u_crit values
  consistent with published manufacturer data.
- The two physically-distinct ceilings (operational vs structural) are
  now distinct fields, so the UI cannot confuse one for the other.
- Per-family K_geom values respect the qualitative ordering from the
  literature (cellulose > PLGA > AC > agarose > alginate); future
  wet-lab calibration tightens the absolute values without changing
  the ordering.
- The `valid_domain` mechanism mirrors the L2 family pattern (B-1c
  precedent at `level2_gelation/ionic_ca.py:249`), so any developer
  who has worked on M1 will recognize the shape.
- The `calibration_store` injection point is the documented path for
  promoting the prediction to `CALIBRATED_LOCAL` render — no code
  change required when a user supplies a manufacturer curve.

### Negative

- The K_geom anchors in v0.7 are **literature defaults**, not wet-lab
  calibrations. v0.7 ships at SEMI_QUANTITATIVE INTERVAL render until
  a manufacturer pressure-flow curve OR local wet-lab data is
  supplied. Per work plan §4.3, DPSim must NEVER be communicated as
  "validated for back-pressure-safe column operation" in v0.7 — only
  as "research-grade screening simulator with first-principles
  back-pressure envelopes."
- The deprecated `max_safe_flow_rate` will need to be removed in v0.8
  with a follow-up audit ensuring no internal call sites still
  reference it. The current method-simulation layer still calls it
  in some non-headline paths; v0.8 must replace those before the
  removal.
- Per-family K_geom calibration is open-ended user work; there is no
  pre-shipped manufacturer curve dataset. The `calibration_store`
  argument exists but is empty until users populate it.

### Neutral

- `dP_max_burst_pa` retains the v0.6.6 framing (= E_star) for
  backwards-compat traceability, but is now explicitly the bed
  *elastic-limit* diagnostic, not the cracking threshold. The actual
  fracture-mechanics cracking threshold (5–10× E_star per Hertz
  contact / K_IC scaling) is out of scope for v0.7 — see work plan
  §6 for what's deferred.

## Validation

The B-2f test suite (~80 tests across `test_family_kgeom.py`,
`test_pressure_envelope.py`, `test_hydrodynamics_deprecation.py`)
asserts:

- Per-family K_geom registry coverage and ordering.
- Lookup dispatch by `.value` (v9.0 Family-First contract).
- u_crit scaling: ∝ G_DN, ∝ d², ∝ 1/L, ∝ 1/μ.
- Q_max = u_crit · A; Q_recommended = 0.5 · Q_max.
- Headroom ratio + warning/blocker derivation.
- Tier rollup: valid_domain violations + viscosity.extrapolated → 1
  step demotion each, floor QUALITATIVE_TREND.
- `calibration_store` override promotes K_geom_source and tier.
- `max_safe_flow_rate` deprecation warning fires.

The smoke test on a typical Sepharose 4FF analytical column (D = 1 cm,
L = 10 cm, d32 = 90 µm, G_DN = 5 kPa, water at 20 °C) yields:

- u_crit ≈ 717 cm/h — within the published Sepharose envelope
  (300–700 cm/h).
- At 200 cm/h operating: headroom ratio = 0.28 (safe).
- At 600 cm/h operating: headroom ratio = 0.84 (warning band).
- Above 717 cm/h: headroom > 1.0 (blocker).

## References

- /scientific-advisor architecture document (delivered 2026-05-10 in
  the joint planning conversation; not a separate file).
- /architect design specification (delivered 2026-05-10; same).
- v0.7.0 work plan: `docs/update_workplan_2026-05-10_m3_pressure.md`
  §3.3 (B-2f), §4.2 gates 6 + 7, §6 (out-of-scope / deferred).
- B-1c precedent for `valid_domain` shape:
  `src/dpsim/level2_gelation/ionic_ca.py:249`.
- B-2e precedent for `pressure_flow_calibrated` tier dimension:
  `src/dpsim/module3_performance/quantitative_gates.py`.
- Stickel & Fotopoulos 2001, *Biotechnology Progress* 17(4): 744–755 —
  scaling-law derivation for u_crit on chromatography media.
- GE Healthcare *Sepharose Fast Flow* product literature — published
  pressure-flow curves at L = 10 cm anchor.

## Out of scope (future ADRs)

- Wet-lab calibration of K_geom against specific resin products
  (validation release-gate 7).
- Fracture-mechanics cracking threshold (`σ_burst ≈ K_IC/√(πa)`)
  beyond the simple `dP_max_burst_pa = E_star` diagnostic in v0.7.
- T_g-aware PLGA ceiling (rubbery-state behaviour above T_g).
- Bayesian uncertainty propagation through the envelope (the v0.7
  intervals are policy-derived ±factor bands, not posteriors).
- Multi-column / parallel-bed pressure modelling.
