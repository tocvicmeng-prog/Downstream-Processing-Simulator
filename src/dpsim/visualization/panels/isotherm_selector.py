"""Isotherm selector + parameter editor.

B-1q / W-055 — v0.8.4. Resolves audit defect C2 (Phase 1 §6).

Five isotherm classes are now reachable from the UI:

* :class:`dpsim.module3_performance.isotherms.langmuir.LangmuirIsotherm`
* :class:`dpsim.module3_performance.isotherms.salt_dependent.SaltModulatedLangmuir`
  (ADR-005, v0.8.1)
* :class:`dpsim.module3_performance.isotherms.imidazole_dependent.ImidazoleModulatedLangmuir`
  (v0.8.2)
* :class:`dpsim.module3_performance.isotherms.sma_modulated.SaltModulatedSMA`
  (ADR-006, v0.8.2)
* :class:`dpsim.module3_performance.isotherms.competitive_salt_dependent.SaltModulatedCompetitiveLangmuir`
  (v0.8.2)

Family-First default routing per the v9.0 contract: the polymer family
+ the M2 binding-model hint together drive the default selection.
Comparisons throughout the dispatch are by ``.value`` per the AST gate
(extended in B-0i / W-052 to cover ``IsothermChoice``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import streamlit as st

from dpsim.datatypes import ModelEvidenceTier, PolymerFamily


class IsothermChoice(Enum):
    """Closed set of UI-selectable isotherms (managed enum per B-0i).

    B-5a (W-078, v0.8.7): HIC and PROTEIN_A added. Closes the Phase 1
    audit defect S-5 — HIC and ProteinA bare classes were defined in
    backend but unreachable from the user-facing dropdown.
    """

    LANGMUIR = "langmuir"
    SALT_MODULATED_LANGMUIR = "salt_modulated_langmuir"
    IMIDAZOLE_MODULATED_LANGMUIR = "imidazole_modulated_langmuir"
    SALT_MODULATED_SMA = "salt_modulated_sma"
    SALT_MODULATED_COMPETITIVE_LANGMUIR = "salt_modulated_competitive_langmuir"
    HIC = "hic"
    PROTEIN_A = "protein_a"


_CHOICE_LABEL: dict[str, str] = {
    IsothermChoice.LANGMUIR.value: "Langmuir (single-component)",
    IsothermChoice.SALT_MODULATED_LANGMUIR.value:
        "Salt-modulated Langmuir (IEX, ADR-005)",
    IsothermChoice.IMIDAZOLE_MODULATED_LANGMUIR.value:
        "Imidazole-modulated Langmuir (IMAC)",
    IsothermChoice.SALT_MODULATED_SMA.value:
        "Salt-modulated SMA (full Steric Mass Action, ADR-006)",
    IsothermChoice.SALT_MODULATED_COMPETITIVE_LANGMUIR.value:
        "Salt-modulated competitive Langmuir (multi-component IEX)",
    IsothermChoice.HIC.value:
        "HIC (hydrophobic interaction, salt-driven)",
    IsothermChoice.PROTEIN_A.value:
        "Protein A / G / L (pH-dependent affinity for IgG capture)",
}


@dataclass(frozen=True)
class IsothermSpec:
    """User-facing isotherm specification.

    Attributes
    ----------
    choice :
        Selected isotherm class.
    params :
        Parameter dict. The keys depend on choice (see _DEFAULTS_BY_CHOICE).
    estimated_tier :
        SEMI_QUANTITATIVE by default; CALIBRATED_LOCAL when the user
        flags ``calibrated_locally`` for the modulated adapters.
    """

    choice: IsothermChoice
    params: dict[str, Any] = field(default_factory=dict)
    estimated_tier: ModelEvidenceTier = ModelEvidenceTier.SEMI_QUANTITATIVE


# Family-First default selection table. Comparisons by .value.
_FAMILY_TO_DEFAULT_CHOICE: dict[str, IsothermChoice] = {
    # B-5a (W-078, v0.8.7): Protein A workflow families now route to
    # the dedicated ProteinA isotherm (was bare Langmuir before HIC +
    # PROTEIN_A entered the selector). The user can still override.
    PolymerFamily.AGAROSE_CHITOSAN.value: IsothermChoice.PROTEIN_A,
    PolymerFamily.AGAROSE.value: IsothermChoice.PROTEIN_A,
    PolymerFamily.AGAROSE_DEXTRAN.value: IsothermChoice.LANGMUIR,
    PolymerFamily.CHITOSAN.value: IsothermChoice.LANGMUIR,
    # Cellulose / PLGA — usually screening; bare Langmuir is the safer default.
    PolymerFamily.CELLULOSE.value: IsothermChoice.LANGMUIR,
    PolymerFamily.PLGA.value: IsothermChoice.LANGMUIR,
    # Material-as-ligand families default to Langmuir (no salt/imidazole physics).
    PolymerFamily.AMYLOSE.value: IsothermChoice.LANGMUIR,
    PolymerFamily.CHITIN.value: IsothermChoice.LANGMUIR,
    # Anionic gel families that frequently host IEX ligands.
    PolymerFamily.ALGINATE.value: IsothermChoice.SALT_MODULATED_LANGMUIR,
    PolymerFamily.DEXTRAN.value: IsothermChoice.SALT_MODULATED_LANGMUIR,
}


# Hint-aware override (M2 binding-model hint takes precedence over family).
def _default_choice_for(
    polymer_family: PolymerFamily,
    binding_model_hint: Optional[str],
) -> IsothermChoice:
    """Pick the family-aware default isotherm for the given context."""
    hint_lower = (binding_model_hint or "").strip().lower()
    if hint_lower.startswith("iex_") or hint_lower in ("iex", "ion_exchange"):
        return IsothermChoice.SALT_MODULATED_LANGMUIR
    if hint_lower in ("imac", "ni_nta", "co_nta"):
        return IsothermChoice.IMIDAZOLE_MODULATED_LANGMUIR
    if hint_lower in ("hic", "phenyl", "butyl", "octyl"):
        # B-5a (W-078, v0.8.7): HIC has dedicated physics — return the
        # bare HIC isotherm now that it is selectable.
        return IsothermChoice.HIC
    if hint_lower in ("protein_a", "protein_g", "protein_l"):
        # B-5a (W-078, v0.8.7): ProteinA has pH-dependent affinity
        # physics — return the bare ProteinA isotherm now that it is
        # selectable.
        return IsothermChoice.PROTEIN_A
    fam_key = polymer_family.value
    return _FAMILY_TO_DEFAULT_CHOICE.get(fam_key, IsothermChoice.LANGMUIR)


# Per-choice parameter defaults. Each dict's keys define the sub-form.
_DEFAULTS_BY_CHOICE: dict[str, dict[str, Any]] = {
    IsothermChoice.LANGMUIR.value: {
        "q_max_mol_m3": 100.0,
        "K_L_m3_mol": 1.0e3,
    },
    IsothermChoice.SALT_MODULATED_LANGMUIR.value: {
        "q_max_mol_m3": 100.0,
        "K_L_m3_mol": 1.0e3,
        "nu": 4.5,
        "c_salt_ref_mol_m3": 150.0,
        "calibrated_locally": False,
    },
    IsothermChoice.IMIDAZOLE_MODULATED_LANGMUIR.value: {
        "q_max_mol_m3": 80.0,
        "K_L_m3_mol": 1.0e4,
        "n": 1.5,
        "c_imidazole_ref_mol_m3": 50.0,
        "calibrated_locally": False,
    },
    IsothermChoice.SALT_MODULATED_SMA.value: {
        "z": 4.5,
        "sigma": 50.0,
        "K_eq": 1.0e-3,
        "Lambda": 1000.0,
        "c_salt_ref_mol_m3": 150.0,
        "calibrated_locally": False,
    },
    IsothermChoice.SALT_MODULATED_COMPETITIVE_LANGMUIR.value: {
        "n_components": 2,
        "q_max_mol_m3": [100.0, 80.0],
        "K_L_m3_mol": [1.0e3, 5.0e2],
        "nu": [6.0, 3.0],
        "c_salt_ref_mol_m3": 150.0,
        "calibrated_locally": False,
    },
    IsothermChoice.HIC.value: {
        "q_max_mol_m3": 50.0,
        "K_0_m3_mol": 0.01,
        "m_salt_m3_mol": 0.005,
        "salt_type": "ammonium_sulfate",
        "calibrated_locally": False,
    },
    IsothermChoice.PROTEIN_A.value: {
        "q_max_mol_m3": 60.0,
        "K_a_max_m3_mol": 1.0e5,
        "pH_transition": 3.5,
        "steepness": 5.0,
        "calibrated_locally": False,
    },
}


def _render_langmuir_subform(
    container: Any, key_prefix: str, seed: dict[str, Any],
) -> dict[str, Any]:
    """Bare Langmuir parameter inputs (q_max + K_L)."""
    cols = container.columns(2)
    q_max = cols[0].number_input(
        "q_max (mol/m³)", min_value=1.0, max_value=500.0,
        value=float(seed.get("q_max_mol_m3", 100.0)), step=1.0,
        key=f"{key_prefix}_qmax",
    )
    K_L = cols[1].number_input(
        "K_L (m³/mol)", min_value=1.0, max_value=1.0e6,
        value=float(seed.get("K_L_m3_mol", 1.0e3)), step=10.0,
        key=f"{key_prefix}_KL",
    )
    return {"q_max_mol_m3": float(q_max), "K_L_m3_mol": float(K_L)}


def _render_salt_modulated_langmuir_subform(
    container: Any, key_prefix: str, seed: dict[str, Any],
) -> dict[str, Any]:
    """Salt-modulated Langmuir (ADR-005): bare Langmuir + ν + c_salt_ref."""
    p = _render_langmuir_subform(container, key_prefix, seed)
    cols = container.columns(2)
    nu = cols[0].number_input(
        "ν (characteristic charge)", min_value=0.5, max_value=15.0,
        value=float(seed.get("nu", 4.5)), step=0.1,
        key=f"{key_prefix}_nu",
        help="Mid-range for IgG-class proteins ≈ 4.5; Mollerup formalism.",
    )
    c_ref = cols[1].number_input(
        "c_salt reference (mM)", min_value=10.0, max_value=500.0,
        value=float(seed.get("c_salt_ref_mol_m3", 150.0)), step=10.0,
        key=f"{key_prefix}_cref",
        help="Reference salt at which K_L was fitted. PBS ≈ 150 mM.",
    )
    cal = container.checkbox(
        "ν / c_salt_ref calibrated locally (promotes tier to CALIBRATED_LOCAL)",
        value=bool(seed.get("calibrated_locally", False)),
        key=f"{key_prefix}_cal",
    )
    p.update(
        nu=float(nu),
        c_salt_ref_mol_m3=float(c_ref),
        calibrated_locally=bool(cal),
    )
    return p


def _render_imidazole_modulated_subform(
    container: Any, key_prefix: str, seed: dict[str, Any],
) -> dict[str, Any]:
    """IMAC imidazole-modulated Langmuir."""
    p = _render_langmuir_subform(container, key_prefix, seed)
    cols = container.columns(2)
    n = cols[0].number_input(
        "n (imidazole-competition exponent)", min_value=0.5, max_value=8.0,
        value=float(seed.get("n", 1.5)), step=0.1,
        key=f"{key_prefix}_n",
        help="Mid-range for His6 on Ni-NTA ≈ 1.5.",
    )
    c_ref = cols[1].number_input(
        "c_imidazole reference (mM)", min_value=5.0, max_value=500.0,
        value=float(seed.get("c_imidazole_ref_mol_m3", 50.0)), step=5.0,
        key=f"{key_prefix}_cref",
        help="Standard IMAC load buffer ≈ 50 mM imidazole.",
    )
    cal = container.checkbox(
        "n / c_imidazole_ref calibrated locally",
        value=bool(seed.get("calibrated_locally", False)),
        key=f"{key_prefix}_cal",
    )
    p.update(
        n=float(n),
        c_imidazole_ref_mol_m3=float(c_ref),
        calibrated_locally=bool(cal),
    )
    return p


def _render_sma_subform(
    container: Any, key_prefix: str, seed: dict[str, Any],
) -> dict[str, Any]:
    """Full SMA — z / σ / K_eq / Λ + c_salt_ref."""
    cols = container.columns(2)
    z = cols[0].number_input(
        "z (characteristic charge)", min_value=0.5, max_value=15.0,
        value=float(seed.get("z", 4.5)), step=0.1,
        key=f"{key_prefix}_z",
    )
    sigma = cols[1].number_input(
        "σ (steric shielding)", min_value=0.0, max_value=200.0,
        value=float(seed.get("sigma", 50.0)), step=5.0,
        key=f"{key_prefix}_sigma",
        help="σ=0 reduces SMA toward Mollerup-simplified shape.",
    )
    cols2 = container.columns(2)
    K_eq = cols2[0].number_input(
        "K_eq (SMA equilibrium constant)", min_value=1.0e-6, max_value=1.0,
        value=float(seed.get("K_eq", 1.0e-3)), step=1.0e-4, format="%.6f",
        key=f"{key_prefix}_Keq",
    )
    Lambda = cols2[1].number_input(
        "Λ (ionic capacity, mol/m³)", min_value=10.0, max_value=5000.0,
        value=float(seed.get("Lambda", 1000.0)), step=50.0,
        key=f"{key_prefix}_Lambda",
    )
    c_ref = container.number_input(
        "c_salt reference (mM)", min_value=10.0, max_value=500.0,
        value=float(seed.get("c_salt_ref_mol_m3", 150.0)), step=10.0,
        key=f"{key_prefix}_cref",
    )
    cal = container.checkbox(
        "z / σ / Λ calibrated locally",
        value=bool(seed.get("calibrated_locally", False)),
        key=f"{key_prefix}_cal",
    )
    return {
        "z": float(z), "sigma": float(sigma),
        "K_eq": float(K_eq), "Lambda": float(Lambda),
        "c_salt_ref_mol_m3": float(c_ref),
        "calibrated_locally": bool(cal),
    }


def _render_competitive_salt_subform(
    container: Any, key_prefix: str, seed: dict[str, Any],
) -> dict[str, Any]:
    """Multi-component salt-modulated Langmuir (per-ν per component)."""
    n_comp = container.number_input(
        "Number of components", min_value=2, max_value=6,
        value=int(seed.get("n_components", 2)), step=1,
        key=f"{key_prefix}_ncomp",
    )
    n_comp = int(n_comp)
    container.caption(
        "Per-component q_max / K_L / ν. Edit cells; rows above n add "
        "if pre-seeded. v0.8.x supports 2–6 components in screening."
    )
    seed_q = list(seed.get("q_max_mol_m3", [100.0] * n_comp))
    seed_K = list(seed.get("K_L_m3_mol", [1.0e3] * n_comp))
    seed_nu = list(seed.get("nu", [4.5] * n_comp))
    while len(seed_q) < n_comp:
        seed_q.append(100.0)
    while len(seed_K) < n_comp:
        seed_K.append(1.0e3)
    while len(seed_nu) < n_comp:
        seed_nu.append(4.5)

    q_list: list[float] = []
    K_list: list[float] = []
    nu_list: list[float] = []
    for i in range(n_comp):
        cols = container.columns(3)
        q_list.append(float(cols[0].number_input(
            f"q_max[{i}]", min_value=1.0, max_value=500.0,
            value=float(seed_q[i]), step=1.0,
            key=f"{key_prefix}_q{i}",
        )))
        K_list.append(float(cols[1].number_input(
            f"K_L[{i}]", min_value=1.0, max_value=1.0e6,
            value=float(seed_K[i]), step=10.0,
            key=f"{key_prefix}_K{i}",
        )))
        nu_list.append(float(cols[2].number_input(
            f"ν[{i}]", min_value=0.5, max_value=15.0,
            value=float(seed_nu[i]), step=0.1,
            key=f"{key_prefix}_nu{i}",
        )))

    c_ref = container.number_input(
        "c_salt reference (mM)", min_value=10.0, max_value=500.0,
        value=float(seed.get("c_salt_ref_mol_m3", 150.0)), step=10.0,
        key=f"{key_prefix}_cref",
    )
    cal = container.checkbox(
        "ν array calibrated locally",
        value=bool(seed.get("calibrated_locally", False)),
        key=f"{key_prefix}_cal",
    )
    return {
        "n_components": n_comp,
        "q_max_mol_m3": q_list,
        "K_L_m3_mol": K_list,
        "nu": nu_list,
        "c_salt_ref_mol_m3": float(c_ref),
        "calibrated_locally": bool(cal),
    }


def _render_hic_subform(
    container: Any, key_prefix: str, seed: dict[str, Any],
) -> dict[str, Any]:
    """HIC isotherm parameter inputs: q_max, K_0, m_salt, salt_type.

    B-5a (W-078, v0.8.7). HIC physics: K_a(c_salt) = K_0 · exp(m_salt · c_salt),
    where c_salt is the lyotropic salt concentration and m_salt encodes the
    salting-out coefficient. Both K_0 and m_salt are protein- and salt-specific
    and almost always require local calibration.
    """
    cols = container.columns(2)
    q_max = cols[0].number_input(
        "q_max (mol/m³)", min_value=1.0, max_value=500.0,
        value=float(seed.get("q_max_mol_m3", 50.0)), step=1.0,
        key=f"{key_prefix}_qmax",
    )
    K_0 = cols[1].number_input(
        "K_0 — base affinity at zero salt (m³/mol)",
        min_value=1.0e-4, max_value=1.0e3,
        value=float(seed.get("K_0_m3_mol", 0.01)),
        step=1.0e-3, format="%.4f",
        key=f"{key_prefix}_K0",
        help="Affinity extrapolated to zero salt — usually small for HIC.",
    )
    cols2 = container.columns(2)
    m_salt = cols2[0].number_input(
        "m_salt — salting-out coefficient (m³/mol)",
        min_value=0.0, max_value=1.0,
        value=float(seed.get("m_salt_m3_mol", 0.005)),
        step=0.001, format="%.4f",
        key=f"{key_prefix}_msalt",
        help="Mid-range for IgG / phenyl ≈ 0.005; protein- and salt-specific.",
    )
    salt_type = cols2[1].selectbox(
        "Salt type",
        options=["ammonium_sulfate", "sodium_sulfate", "sodium_chloride", "potassium_phosphate"],
        index=["ammonium_sulfate", "sodium_sulfate", "sodium_chloride", "potassium_phosphate"].index(
            seed.get("salt_type", "ammonium_sulfate")
        ),
        key=f"{key_prefix}_salt",
        help="Hofmeister-series anion identity. Used for validation gates.",
    )
    cal = container.checkbox(
        "K_0 / m_salt calibrated locally (promotes tier to CALIBRATED_LOCAL)",
        value=bool(seed.get("calibrated_locally", False)),
        key=f"{key_prefix}_cal",
    )
    return {
        "q_max_mol_m3": float(q_max),
        "K_0_m3_mol": float(K_0),
        "m_salt_m3_mol": float(m_salt),
        "salt_type": str(salt_type),
        "calibrated_locally": bool(cal),
    }


def _render_protein_a_subform(
    container: Any, key_prefix: str, seed: dict[str, Any],
) -> dict[str, Any]:
    """Protein A pH-dependent affinity.

    B-5a (W-078, v0.8.7). Sigmoid K_a(pH) = K_a_max / (1 + exp(steepness ·
    (pH_transition − pH))). Default values are anchored to MabSelect SuRe /
    IgG capture; pH_transition ≈ 3.5 (canonical low-pH elution); steepness ≈ 5
    matches the sharp Protein A elution curve.
    """
    cols = container.columns(2)
    q_max = cols[0].number_input(
        "q_max (mol/m³)", min_value=1.0, max_value=200.0,
        value=float(seed.get("q_max_mol_m3", 60.0)), step=1.0,
        key=f"{key_prefix}_qmax",
        help="Typical Protein A resin DBC ≈ 30-70 mg/mL ≈ 50-90 mol/m³.",
    )
    K_a_max = cols[1].number_input(
        "K_a_max — neutral-pH affinity (m³/mol)",
        min_value=1.0e3, max_value=1.0e7,
        value=float(seed.get("K_a_max_m3_mol", 1.0e5)),
        step=1.0e4, format="%.0f",
        key=f"{key_prefix}_Kamax",
        help="Very high — Protein A has nM-range K_d at neutral pH.",
    )
    cols2 = container.columns(2)
    pH_transition = cols2[0].number_input(
        "pH_transition (half-maximal K_a)",
        min_value=2.0, max_value=6.0,
        value=float(seed.get("pH_transition", 3.5)),
        step=0.1, format="%.1f",
        key=f"{key_prefix}_pHt",
        help="Canonical low-pH elution ≈ 3.5; tune to your antibody's tolerance.",
    )
    steepness = cols2[1].number_input(
        "Sigmoid steepness (1/pH unit)",
        min_value=1.0, max_value=15.0,
        value=float(seed.get("steepness", 5.0)),
        step=0.5, format="%.1f",
        key=f"{key_prefix}_steep",
        help="Higher = sharper transition; ≈ 5 matches typical Protein A.",
    )
    cal = container.checkbox(
        "K_a_max / pH_transition calibrated locally",
        value=bool(seed.get("calibrated_locally", False)),
        key=f"{key_prefix}_cal",
    )
    return {
        "q_max_mol_m3": float(q_max),
        "K_a_max_m3_mol": float(K_a_max),
        "pH_transition": float(pH_transition),
        "steepness": float(steepness),
        "calibrated_locally": bool(cal),
    }


_SUBFORM_BY_CHOICE: dict[str, Any] = {
    IsothermChoice.LANGMUIR.value: _render_langmuir_subform,
    IsothermChoice.SALT_MODULATED_LANGMUIR.value:
        _render_salt_modulated_langmuir_subform,
    IsothermChoice.IMIDAZOLE_MODULATED_LANGMUIR.value:
        _render_imidazole_modulated_subform,
    IsothermChoice.SALT_MODULATED_SMA.value: _render_sma_subform,
    IsothermChoice.SALT_MODULATED_COMPETITIVE_LANGMUIR.value:
        _render_competitive_salt_subform,
    IsothermChoice.HIC.value: _render_hic_subform,
    IsothermChoice.PROTEIN_A.value: _render_protein_a_subform,
}


def render_isotherm_widget(
    *,
    container: Any = None,
    key_prefix: str = "iso",
    polymer_family: PolymerFamily,
    binding_model_hint: Optional[str] = None,
    initial: Optional[IsothermSpec] = None,
) -> IsothermSpec:
    """Render the family-aware isotherm selector + parameter sub-form.

    The dropdown defaults to the selection from
    :func:`_default_choice_for` based on family + M2 binding hint. The
    parameter sub-form swaps based on the chosen class. All comparisons
    are by ``.value`` per the AST gate (B-0i / W-052).
    """
    target = container if container is not None else st

    default_choice = (
        initial.choice if initial is not None
        else _default_choice_for(polymer_family, binding_model_hint)
    )
    choice_values = [c.value for c in IsothermChoice]
    default_index = choice_values.index(default_choice.value)

    target.markdown("**Isotherm**")
    chosen_value = target.selectbox(
        "Isotherm class",
        options=choice_values,
        index=default_index,
        format_func=lambda v: _CHOICE_LABEL.get(v, v),
        key=f"{key_prefix}_choice",
    )

    chosen = IsothermChoice(chosen_value)

    # Seed parameters: prefer the user's initial spec if it matches the
    # current choice; otherwise fall back to the per-choice defaults.
    if (
        initial is not None
        and initial.choice.value == chosen.value
    ):
        seed_params = dict(initial.params)
    else:
        seed_params = dict(_DEFAULTS_BY_CHOICE[chosen.value])

    subform = _SUBFORM_BY_CHOICE[chosen.value]
    params = subform(target, f"{key_prefix}_p", seed_params)

    estimated_tier = (
        ModelEvidenceTier.CALIBRATED_LOCAL
        if bool(params.get("calibrated_locally", False))
        else ModelEvidenceTier.SEMI_QUANTITATIVE
    )

    return IsothermSpec(
        choice=chosen,
        params=params,
        estimated_tier=estimated_tier,
    )


def to_isotherm(spec: IsothermSpec) -> Any:
    """Instantiate a backend isotherm from an :class:`IsothermSpec`.

    B-4d / W-072 (v0.8.6). Bridges the UI's user-facing IsothermSpec
    into the backend isotherm class hierarchy so the lifecycle can
    consume the user's choice. Without this helper the spec would
    remain UI-side only — the v0.8.4 wiring break flagged in
    AUDIT_v0_8_5_e2e_phase3_architecture.md §A-2 / §A-4.

    Returns
    -------
    Backend isotherm instance: LangmuirIsotherm | SaltModulatedLangmuir |
    ImidazoleModulatedLangmuir | SaltModulatedSMA |
    SaltModulatedCompetitiveLangmuir.
    """
    import numpy as _np
    from dpsim.module3_performance.isotherms.langmuir import LangmuirIsotherm
    p = dict(spec.params)
    if spec.choice.value == IsothermChoice.LANGMUIR.value:
        return LangmuirIsotherm(
            q_max=float(p.get("q_max_mol_m3", 100.0)),
            K_L=float(p.get("K_L_m3_mol", 1.0e3)),
        )
    if spec.choice.value == IsothermChoice.SALT_MODULATED_LANGMUIR.value:
        from dpsim.module3_performance.isotherms.salt_dependent import (
            SaltModulatedLangmuir,
        )
        return SaltModulatedLangmuir(
            base=LangmuirIsotherm(
                q_max=float(p.get("q_max_mol_m3", 100.0)),
                K_L=float(p.get("K_L_m3_mol", 1.0e3)),
            ),
            nu=float(p.get("nu", 4.5)),
            c_salt_ref_mol_m3=float(p.get("c_salt_ref_mol_m3", 150.0)),
        )
    if spec.choice.value == IsothermChoice.IMIDAZOLE_MODULATED_LANGMUIR.value:
        from dpsim.module3_performance.isotherms.imidazole_dependent import (
            ImidazoleModulatedLangmuir,
        )
        return ImidazoleModulatedLangmuir(
            base=LangmuirIsotherm(
                q_max=float(p.get("q_max_mol_m3", 80.0)),
                K_L=float(p.get("K_L_m3_mol", 1.0e4)),
            ),
            n=float(p.get("n", 1.5)),
            c_imidazole_ref_mol_m3=float(p.get("c_imidazole_ref_mol_m3", 50.0)),
        )
    if spec.choice.value == IsothermChoice.SALT_MODULATED_SMA.value:
        from dpsim.module3_performance.isotherms.sma_modulated import (
            SaltModulatedSMA,
        )
        return SaltModulatedSMA(
            z=float(p.get("z", 4.5)),
            sigma=float(p.get("sigma", 50.0)),
            K_eq=float(p.get("K_eq", 1.0e-3)),
            Lambda=float(p.get("Lambda", 1000.0)),
            c_salt_ref_mol_m3=float(p.get("c_salt_ref_mol_m3", 150.0)),
        )
    if spec.choice.value == IsothermChoice.SALT_MODULATED_COMPETITIVE_LANGMUIR.value:
        from dpsim.module3_performance.isotherms.competitive_langmuir import (
            CompetitiveLangmuirIsotherm,
        )
        from dpsim.module3_performance.isotherms.competitive_salt_dependent import (
            SaltModulatedCompetitiveLangmuir,
        )
        q_arr = _np.asarray(p.get("q_max_mol_m3", [100.0, 80.0]), dtype=float)
        K_arr = _np.asarray(p.get("K_L_m3_mol", [1.0e3, 5.0e2]), dtype=float)
        nu_arr = _np.asarray(p.get("nu", [6.0, 3.0]), dtype=float)
        return SaltModulatedCompetitiveLangmuir(
            base=CompetitiveLangmuirIsotherm(q_max=q_arr, K_L=K_arr),
            nu=nu_arr,
            c_salt_ref_mol_m3=float(p.get("c_salt_ref_mol_m3", 150.0)),
        )
    if spec.choice.value == IsothermChoice.HIC.value:
        from dpsim.module3_performance.isotherms.hic import HICIsotherm
        return HICIsotherm(
            q_max=float(p.get("q_max_mol_m3", 50.0)),
            K_0=float(p.get("K_0_m3_mol", 0.01)),
            m_salt=float(p.get("m_salt_m3_mol", 0.005)),
            salt_type=str(p.get("salt_type", "ammonium_sulfate")),
        )
    if spec.choice.value == IsothermChoice.PROTEIN_A.value:
        from dpsim.module3_performance.isotherms.protein_a import (
            ProteinAIsotherm,
        )
        return ProteinAIsotherm(
            q_max=float(p.get("q_max_mol_m3", 60.0)),
            K_a_max=float(p.get("K_a_max_m3_mol", 1.0e5)),
            pH_transition=float(p.get("pH_transition", 3.5)),
            steepness=float(p.get("steepness", 5.0)),
        )
    raise ValueError(f"Unknown IsothermChoice: {spec.choice!r}")


__all__ = [
    "IsothermChoice",
    "IsothermSpec",
    "render_isotherm_widget",
    "to_isotherm",
]
