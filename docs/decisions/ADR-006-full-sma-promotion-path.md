# ADR-006 — Full SMA promotion path: cost vs precision

**Status:** Accepted
**Date:** 2026-05-10
**Decision driver:** v0.8.2 W-039. ADR-005 documented the Mollerup-simplified salt modulator as the v0.8.1 starting point and named the full Steric Mass Action (SMA) solver as the eventual promotion target. v0.8.2 ships the promotion path so consumers can swap the adapter when calibration data justifies the precision gain.

## Context

ADR-005 ships `SaltModulatedLangmuir` — the Mollerup-simplified single-component salt modulator. Its trade-offs:

| Aspect | Mollerup-simplified | Full SMA |
|---|---|---|
| Per-rhs cost | O(1) (one `pow`) | O(N_iter) where N_iter ≈ 5–20 (fixed-point on q_salt) |
| Saturation | Ignored — Langmuir base does the saturation in C, not in q_salt | Captured via the ionic capacity constraint Λ |
| Steric shielding | Ignored | Captured via σ |
| Multi-component | Single-component only | Native multi-component |
| Calibration burden | ν, c_salt_ref | z, σ, K_eq, Λ per component |

Both are *correct in their regime*. Mollerup-simplified is right when:
- One protein is being modeled (single-component).
- The bound q stays well below Λ (< ~30 % saturation).
- ν has been fitted but σ is unknown.

Full SMA is right when:
- Multi-component co-elution dynamics matter.
- High-load operation drives q close to Λ.
- σ is fitted (separately from ν).

`SMAIsotherm` (`module3_performance/isotherms/sma.py`, Brooks & Cramer 1992) already implements the full multi-component path with fixed-point iteration on q_salt. It is wired through `EquilibriumAdapter` for `run_gradient_elution` consumers. What is missing: a swap-in target with the exact `equilibrium_loading(C, c_salt_mol_m3)` signature that `SaltModulatedLangmuir` exposes, so consumers can promote without touching the rhs.

## Decision

**Ship `SaltModulatedSMA` as a thin facade adapter wrapping a single-component `SMAIsotherm`.** Same `equilibrium_loading(C, c_salt_mol_m3)` interface as `SaltModulatedLangmuir`. Internally:
- Holds a single-component SMAIsotherm (n_comp = 1).
- Maps the scalar `C` argument to the 1-element array SMA expects.
- Calls the full fixed-point solve and returns the scalar loading.
- Routes through `EquilibriumAdapter` via the existing `_cls_name == "SMAIsotherm"` branch when the user supplies the underlying SMA directly, or via a new `_cls_name == "SaltModulatedSMA"` branch for the facade.

The facade is intentionally narrow:
- **Same `evidence_tier` ladder** as `SaltModulatedLangmuir` — SEMI_QUANTITATIVE default, CALIBRATED_LOCAL with `calibrated_locally=True`. The full SMA does not auto-promote tier; promotion is wet-lab-driven.
- **Single-component only.** Multi-component competition is handled by the underlying `SMAIsotherm` directly with its native multi-component interface — no facade needed for that path.
- **No new physics.** All the math comes from the existing `SMAIsotherm` class. The facade only changes the call-signature shape.

## Consequences

- **Drop-in promotion.** A consumer constructing `SaltModulatedLangmuir(base, ν, c_salt_ref)` can switch to `SaltModulatedSMA(z, σ, K_eq, Λ, c_salt_ref)` without touching the rhs solver caller. The `EquilibriumAdapter` routes either through the same `salt_concentration` state field.
- **Per-rhs cost goes up.** Users opting in to full SMA pay 5–20× the Mollerup-simplified cost. Document this as the explicit cost of the precision gain.
- **Calibration burden visibility.** The facade's constructor exposes z, σ, K_eq, Λ as separate arguments — making the additional calibration burden visible at the call site (no hidden defaults beyond the literature anchors).
- **Mollerup-simplified stays the recommended default** until users have both ν and σ. Without σ, the Mollerup form is a strict subset and there is no fidelity gain.

## Out of scope

- **Multi-component competitive co-elution.** Use `SMAIsotherm` directly; the existing adapter branch handles it.
- **Activity-coefficient corrections** (γ_protein(c_salt)). Same SEMI_QUANTITATIVE-tier reasoning as ADR-005.
- **HIC analog.** HIC has its own salt-dependence physics (Hofmeister-driven, not stoichiometric); the existing `HICIsotherm` is the right home, not this facade.

## References

- Brooks, C.A. & Cramer, S.M. (1992). Steric mass-action ion exchange. *AIChE J.* 38(12), 1969.
- Mollerup, J.M. & Hansen, T.B. (2014). The thermodynamic framework for modeling chromatography. *J. Chromatogr. A* 1352, 32.
- ADR-005 — Salt-dependent isotherm: Mollerup-simplified modulator (v0.8.1 / W-034).
