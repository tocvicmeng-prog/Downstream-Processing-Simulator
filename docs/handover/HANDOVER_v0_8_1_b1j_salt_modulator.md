# HANDOVER — B-1j salt-modulated Langmuir close (v0.8.1)

**Batch:** B-1j
**Work item:** W-034 (HIGH)
**Source delta:** 2026-05-04 incremental-close handover §"Future scientific scope" item 1
**ADR:** ADR-005
**Date:** 2026-05-10

## Summary

Closes the long-deferred "salt-dependent isotherm physics" item. Per
ADR-005, ships the **Mollerup-simplified single-component salt
modulator** as a thin adapter wrapping the existing `LangmuirIsotherm`.
The full SMA mass-action solver (`isotherms/sma.py`, already in the
repo) remains the documented promotion target for when wet-lab ν / σ
data warrants the per-rhs fixed-point cost.

## Files added/modified

| File | Change |
|---|---|
| `docs/decisions/ADR-005-salt-dependent-isotherm.md` | NEW. Documents the SDM-vs-Mollerup-vs-SMA tradeoff. Decision: ship Mollerup-simplified now (functionally identical to SDM in the dilute limit, O(1) per rhs); promote to full SMA when wet-lab justifies it. Literature defaults: ν=4.5, c_salt_ref=150 mM. |
| `src/dpsim/module3_performance/isotherms/salt_dependent.py` | NEW. `salt_modulation_factor` pure-math helper. `SaltModulatedLangmuir` frozen dataclass with `equilibrium_loading(C, c_salt_mol_m3=None)` and `jacobian(C, c_salt_mol_m3=None)`. `evidence_tier` property: SEMI_QUANTITATIVE by default; CALIBRATED_LOCAL when `calibrated_locally=True`. |
| `src/dpsim/module3_performance/isotherms/adapter.py` | Adds a `SaltModulatedLangmuir` branch to `EquilibriumAdapter.equilibrium_loading` so the existing `run_gradient_elution` → `solve_lrm` → adapter wiring routes the `salt_concentration` state field into the new isotherm. |
| `tests/module3_performance/test_salt_dependent_isotherm.py` | NEW. 24 tests: factor math (reference/below/above, ν=0 special case, floor against c_salt=0), adapter modulation, jacobian parallelism, tier ladder, EquilibriumAdapter routing + state updates. |

## Acceptance

- ν=4.5 default for typical 30–60 kDa proteins; c_salt_ref=150 mM PBS reference.
- `salt_modulation_factor(c_ref, c_ref) = 1.0` exactly (no modulation at the calibration point).
- `salt_modulation_factor(c_ref / 2, c_ref) = 2 ** ν` (low-salt enhances binding).
- `salt_modulation_factor(2 · c_ref, c_ref) = (1/2) ** ν` (high-salt drives elution).
- `c_salt = 0` → factor finite via 1×10⁻⁶ floor.
- ν outside [0, 20] rejected; `c_salt_ref ≤ 0` rejected.
- `SaltModulatedLangmuir.equilibrium_loading(C)` (no salt) degrades to base.
- Adapter routes `state["salt_concentration"]` → isotherm at every rhs.
- 24/24 new tests pass; 223/223 pass across module3_performance scope.
- ruff + mypy clean.

## Out of scope (deferred)

- **Full SMA per-rhs solve.** The SMA class exists but isn't wired into the time-domain rhs because the fixed-point on q_salt is ~10× more expensive per step. Future v0.9 promotion path.
- **Multi-component competitive elution.** Mollerup-simplified breaks down when bound proteins compete for finite ionic capacity.
- **Activity-coefficient corrections** (γ_protein(c_salt) terms in the full Mollerup form). SEMI_QUANTITATIVE tier doesn't warrant the calibration burden.
- **Wet-lab ν calibration** — caller responsibility; promotes tier to CALIBRATED_LOCAL via `calibrated_locally=True`.
