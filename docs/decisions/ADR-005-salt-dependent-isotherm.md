# ADR-005 — Salt-dependent isotherm: Mollerup-simplified modulator now, full SMA later

**Status:** Accepted
**Date:** 2026-05-10
**Decision driver:** v0.8.1 W-034. The 2026-05-04 incremental-close handover §"Future scientific scope" listed salt-dependent K_a (SDM vs Mollerup) as a deferred item. The B-2e scaffolding (`LoadedStateElutionResult.gradient_diagnostics`) has been ready since v0.6.6; what was missing was a science decision on which formulation to wire into the loaded-state elution rhs.

## Context

DPSim's loaded-state elution path (`module3_performance/method.py::run_loaded_state_elution`) supports:

- **pH-driven elution** (Protein A): `_protein_a_elution_suppression(pH_t, process_state)` returns a multiplicative factor that suppresses isotherm equilibrium loading at low pH. The mechanism is wet-lab-calibrated and behaves as a step function around the affinity transition pH.
- **Salt-driven elution** (IEX) — **previously not wired**. The active salt concentration was exposed as a diagnostic via `gradient_diagnostics` but the rhs did not consume it. The v0.7 / v0.8 work hardened the pressure envelope and the streaming monitor; the elution physics gap remained open.

The literature offers three canonical formulations for salt-driven elution:

### Option A — Stoichiometric Displacement Model (SDM)

Velayudhan & Horváth 1986 / Regnier 1985:

```
log K_a = log K_a_ref − ν · log(c_salt / c_salt_ref)
```

i.e. `K_a(c_salt) = K_a_ref · (c_salt_ref / c_salt) ** ν`.

Pure log-log form, single parameter ν per protein. Universally understood, easy to fit. Widely used as the textbook starting point.

### Option B — Mollerup formalism (single-component reduction)

Mollerup 2008 (extended in Mollerup & Hansen 2014):

```
K_eff(c_salt) = K_ref · γ_protein(c_salt)/γ_protein(c_salt_ref) · (c_salt_ref/c_salt)^ν
```

In the dilute, ideal-activity limit (γ ≈ 1), this reduces to the SDM functional form. Mollerup's contribution is the thermodynamic-consistency framework that lets a single-component fit extend correctly to multi-component competitive-IEX. For *single-component* simulation in the dilute limit, the working formula is identical to SDM.

### Option C — Steric Mass Action (SMA, Brooks & Cramer 1992)

```
q_i = K_eq_i · C_i · (q_salt / C_salt) ** z_i
Lambda = sum_i((z_i + sigma_i) · q_i) + q_salt
```

Full mass-action with steric-shielding factor σ. Requires solving a fixed-point at every rhs evaluation for q_salt (the bound counterion concentration). Strictly more capable than SDM/Mollerup; matches displacement-train chromatography phenomena that the simpler models miss.

DPSim's SMA class already exists — `module3_performance/isotherms/sma.py` (Brooks & Cramer 1992). It is currently used as a *static* equilibrium calculator, not wired into any time-domain rhs.

## Decision

**Ship the Mollerup-simplified salt modulator (functionally identical to SDM in the dilute single-component limit) as a thin adapter layer that wraps the existing `LangmuirIsotherm` and is consumed by `method.py::run_loaded_state_elution` at every rhs step.** Tier: `SEMI_QUANTITATIVE` until ν is calibrated wet-lab.

Concretely:

```python
# isotherms/salt_dependent.py
@dataclass(frozen=True)
class SaltModulatedLangmuir:
    base: LangmuirIsotherm
    nu: float = 4.5                    # characteristic charge (literature default)
    c_salt_ref_mol_m3: float = 150.0   # 150 mM ≈ physiological reference

    def equilibrium_loading(self, C, c_salt_t):
        factor = (self.c_salt_ref_mol_m3 / max(c_salt_t, 1e-6)) ** self.nu
        return self.base.equilibrium_loading(C) * factor
```

The rhs in `method.py` mirrors the existing `_protein_a_elution_suppression` pattern:

```python
salt_t = gradient_value_at_time(t) if _grad_ctx and _grad_ctx.gradient_field == "salt" else None
salt_factor = salt_modulator(salt_t) if salt_t is not None else 1.0
q_eq = isotherm.equilibrium_loading(Cp, pH_t) * pa_suppression * salt_factor
```

When no salt gradient is active (or the isotherm is not salt-modulated), the factor is 1.0 — no behavior change for the existing pH-driven and isocratic paths.

### Why Mollerup-simplified instead of full SMA

1. **One-line rhs cost.** The Mollerup factor is `(c_ref/c_salt) ** ν` — an O(1) evaluation per timestep. Full SMA requires a fixed-point solve for `q_salt` at every rhs call, which is feasible but ~10× more expensive.

2. **SDM and Mollerup-simplified are functionally identical in the dilute single-component regime.** No fidelity loss vs the textbook SDM; we get the Mollerup framework as a documented promotion path for free.

3. **The full SMA class already exists.** Promoting from Mollerup-simplified to SMA later means *swapping the adapter*, not rewriting the time-domain solver. The SMA class is the documented promotion target once wet-lab data justifies the cost.

4. **Tier-gating still applies.** The SEMI_QUANTITATIVE INTERVAL render mode for elution-derived metrics (peak time, peak width, recovery fraction) does not require quantitative ν — a literature-anchored ν gives the right *shape* of the elution profile, and the tier ladder ensures users see the rendering caveat.

### Why ν = 4.5 is the literature default

Typical IEX proteins (~30–60 kDa, mAb subdomain, lysozyme, BSA) have characteristic charge ν in the range [2, 8]. The midpoint ν = 4.5 reflects the modal protein-A-eluted IgG payload that drives most users of this code. A user-calibrated ν in `SaltModulatedLangmuir` overrides the default.

### Why c_salt_ref = 150 mM

Phosphate-buffered saline reference. Most IEX load buffers are 100–200 mM total ionic strength; 150 mM is the de facto convention for reporting K_a values in literature.

## Out of scope

- **Multi-component competitive elution.** A two-protein co-elution simulation requires the full SMA solve. Mollerup-simplified breaks down when bound proteins compete for finite ionic capacity Lambda.
- **σ (steric shielding).** Single-component Mollerup-simplified does not model bead-pore steric exclusion of the eluting protein at high q. Only matters near saturation; outside the typical operating regime.
- **Activity coefficient corrections.** Mollerup's full form includes γ_protein(c_salt) terms for non-ideal protein-salt interactions. SEMI_QUANTITATIVE precision does not warrant the extra calibration burden.

## Consequences

- **Salt-driven elution dynamics become physics-aware.** Previously, a recipe with a salt gradient would produce a flat (no-effect) elution profile; the gradient was visible only as a label in `gradient_diagnostics`. After v0.8.1, the rhs sees `c_salt(t)` and the K_a modulator drives peak time + recovery realistically.
- **Tier remains SEMI_QUANTITATIVE INTERVAL** until users calibrate ν against their own protein-resin pair. The `calibration_store` injection point lifts the tier to `CALIBRATED_LOCAL` per Mollerup formalism's standard fit (`log K_a vs log c_salt`).
- **The full SMA class stays reachable.** Future work can construct a `SaltModulatedSMA` adapter on the same interface (`equilibrium_loading(C, c_salt)`) without changing any rhs caller.

## References

- Velayudhan, A. & Horváth, C. (1986). On the stoichiometric retention model for protein chromatography. *J. Chromatogr.* 367, 160.
- Brooks, C.A. & Cramer, S.M. (1992). Steric mass-action ion exchange. *AIChE J.* 38(12), 1969.
- Mollerup, J.M. (2008). A review of the thermodynamics of protein adsorption. *Chem. Eng. Technol.* 31(6), 864.
- Mollerup, J.M. & Hansen, T.B. (2014). The thermodynamic framework for modeling chromatography. *J. Chromatogr. A* 1352, 32.
