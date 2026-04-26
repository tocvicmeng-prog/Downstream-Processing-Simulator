"""v0.5.1 — deferred follow-on work for the M2 ACS Converter epic.

Covers the four items deferred from v0.5.0 §8 of the handover:
  1. Cyanuric chloride staged 3-Cl substitution (per-stage rate constants).
  2. Periodate / glyoxyl chain-scission penalty on G_DN above threshold.
  3. Per-protein pyridyl-disulfide couplers (Cys-Protein A / G / L).
  4. CNBr time-window enforcement (G6.5 strengthened from WARNING-only to
     BLOCKER on intervening-step duration > 15 min).
"""

from __future__ import annotations

import pytest

from dpsim.core.process_recipe import (
    LifecycleStage,
    MaterialBatch,
    ProcessRecipe,
    ProcessStep,
    ProcessStepKind,
    TargetProductProfile,
)
from dpsim.core.quantities import Quantity
from dpsim.core.recipe_validation import validate_recipe_first_principles
from dpsim.module2_functionalization.acs import ACSSiteType, ACSProfile
from dpsim.module2_functionalization.modification_steps import (
    ModificationStep,
    ModificationStepType,
    solve_modification_step,
)
from dpsim.module2_functionalization.reagent_profiles import REAGENT_PROFILES
from dpsim.module2_functionalization.surface_area import (
    AccessibleSurfaceModel,
    SurfaceAreaTier,
)


def _surface_model(R: float = 50e-6) -> AccessibleSurfaceModel:
    model = AccessibleSurfaceModel(
        tier=SurfaceAreaTier.EMPIRICAL_PORE,
        bead_radius=R,
        porosity=0.7,
        pore_diameter_mean=100e-9,
    )
    model.compute()
    return model


def _hydroxyl_profile(n_sites: float = 1e-9) -> dict[ACSSiteType, ACSProfile]:
    return {
        ACSSiteType.HYDROXYL: ACSProfile(
            site_type=ACSSiteType.HYDROXYL,
            total_sites=n_sites,
            accessible_sites=n_sites,
        ),
    }


# ─── (1) Cyanuric staged kinetics ──────────────────────────────────────


class TestCyanuricStagedKinetics:
    """Cyanuric chloride should expose per-stage (k_forward, E_a) tuples
    that the activation solver consults when ModificationStep.temperature_stage
    is set. Stage 1 = base rate; Stage 2 ~10x slower; Stage 3 ~100x slower."""

    def test_staged_kinetics_table_populated(self) -> None:
        rp = REAGENT_PROFILES["cyanuric_chloride_activation"]
        assert len(rp.staged_kinetics) == 3
        # Each successive stage should be slower (smaller k_forward).
        k1, k2, k3 = (k for (k, _) in rp.staged_kinetics)
        assert k1 > k2 > k3, (
            f"Successive cyanuric stages should slow ~10x each; got "
            f"k1={k1}, k2={k2}, k3={k3}"
        )

    def test_unstaged_step_uses_base_kinetics(self) -> None:
        """A ModificationStep with temperature_stage=0 should behave
        identically to v0.5.0 (base k_forward, base E_a)."""
        rp = REAGENT_PROFILES["cyanuric_chloride_activation"]
        step = ModificationStep(
            step_type=ModificationStepType.ACS_CONVERSION,
            reagent_key="cyanuric_chloride_activation",
            target_acs=rp.target_acs,
            product_acs=rp.product_acs,
            temperature=rp.temperature_default,
            time=rp.time_default,
            ph=rp.ph_optimum,
            reagent_concentration=10.0,
            temperature_stage=0,
        )
        acs_state = _hydroxyl_profile()
        result = solve_modification_step(
            step, acs_state, _surface_model(), rp,
        )
        assert result.conversion > 0.0

    def test_stage_2_slower_than_stage_1_in_solver(self) -> None:
        """At identical T / time / concentrations, stage 2 should produce
        substantially less conversion than stage 1 because its k_forward
        is ~10x smaller."""
        rp = REAGENT_PROFILES["cyanuric_chloride_activation"]
        # Use a SHORT time so neither stage saturates — the difference
        # between k1 and k2 is visible in the conversion fraction.
        common = dict(
            step_type=ModificationStepType.ACS_CONVERSION,
            reagent_key="cyanuric_chloride_activation",
            target_acs=rp.target_acs,
            product_acs=rp.product_acs,
            temperature=298.15,
            time=60.0,                   # 1 min
            ph=rp.ph_optimum,
            reagent_concentration=1.0,    # low conc → conversion << 1
        )
        step1 = ModificationStep(temperature_stage=1, **common)
        step2 = ModificationStep(temperature_stage=2, **common)
        result1 = solve_modification_step(step1, _hydroxyl_profile(), _surface_model(), rp)
        result2 = solve_modification_step(step2, _hydroxyl_profile(), _surface_model(), rp)
        assert result1.conversion > result2.conversion, (
            f"Stage 1 should outpace stage 2; got conv1={result1.conversion}, "
            f"conv2={result2.conversion}"
        )

    def test_stage_3_slowest(self) -> None:
        """Stage 3 should be the slowest of the three."""
        rp = REAGENT_PROFILES["cyanuric_chloride_activation"]
        common = dict(
            step_type=ModificationStepType.ACS_CONVERSION,
            reagent_key="cyanuric_chloride_activation",
            target_acs=rp.target_acs,
            product_acs=rp.product_acs,
            temperature=298.15,
            time=60.0,
            ph=rp.ph_optimum,
            reagent_concentration=1.0,
        )
        result2 = solve_modification_step(
            ModificationStep(temperature_stage=2, **common),
            _hydroxyl_profile(), _surface_model(), rp,
        )
        result3 = solve_modification_step(
            ModificationStep(temperature_stage=3, **common),
            _hydroxyl_profile(), _surface_model(), rp,
        )
        assert result3.conversion < result2.conversion


# ─── (2) Periodate chain-scission penalty ──────────────────────────────


class TestPeriodateChainScission:
    """Above the periodate conversion threshold (~30%), a chain-scission
    penalty must reduce G_DN. Below threshold, G_DN is unchanged."""

    def test_periodate_has_scission_threshold_set(self) -> None:
        rp = REAGENT_PROFILES["periodate_oxidation"]
        assert rp.chain_scission_threshold == pytest.approx(0.30)
        assert rp.chain_scission_max_g_dn_loss == pytest.approx(0.70)

    def test_glyoxyl_chained_has_scission_threshold_set(self) -> None:
        rp = REAGENT_PROFILES["glyoxyl_chained_activation"]
        # Glyoxyl-chained has a higher threshold (the glycidol overlay
        # protects the backbone) and a lower max loss.
        assert rp.chain_scission_threshold == pytest.approx(0.40)
        assert rp.chain_scission_max_g_dn_loss == pytest.approx(0.50)

    def test_other_converters_have_no_scission(self) -> None:
        for key in (
            "cnbr_activation", "cdi_activation", "tresyl_chloride_activation",
            "cyanuric_chloride_activation", "ech_activation", "dvs_activation",
        ):
            rp = REAGENT_PROFILES[key]
            assert rp.chain_scission_max_g_dn_loss == 0.0, (
                f"{key} should not declare chain scission"
            )

    def test_low_conversion_no_scission(self) -> None:
        """Conversion below threshold → result.g_dn_scission_fraction == 0."""
        rp = REAGENT_PROFILES["periodate_oxidation"]
        step = ModificationStep(
            step_type=ModificationStepType.ACS_CONVERSION,
            reagent_key="periodate_oxidation",
            target_acs=rp.target_acs,
            product_acs=rp.product_acs,
            temperature=rp.temperature_default,
            time=60.0,                  # 1 min — driven low
            ph=rp.ph_optimum,
            reagent_concentration=0.1,
        )
        result = solve_modification_step(
            step, _hydroxyl_profile(), _surface_model(), rp,
        )
        assert result.conversion < 0.30, (
            f"Setup should produce sub-threshold conversion; got "
            f"{result.conversion}"
        )
        assert result.g_dn_scission_fraction == 0.0

    def test_high_conversion_triggers_scission(self) -> None:
        """Conversion above threshold → g_dn_scission_fraction in (0, max_loss]."""
        rp = REAGENT_PROFILES["periodate_oxidation"]
        step = ModificationStep(
            step_type=ModificationStepType.ACS_CONVERSION,
            reagent_key="periodate_oxidation",
            target_acs=rp.target_acs,
            product_acs=rp.product_acs,
            temperature=rp.temperature_default,
            time=86400.0,                # 24 h — saturate to ~1.0
            ph=rp.ph_optimum,
            reagent_concentration=1000.0,
        )
        result = solve_modification_step(
            step, _hydroxyl_profile(), _surface_model(), rp,
        )
        assert result.conversion > 0.30
        assert 0.0 < result.g_dn_scission_fraction <= 0.70, (
            f"High-conversion periodate should incur scission penalty; "
            f"got conv={result.conversion}, scission={result.g_dn_scission_fraction}"
        )

    def test_full_conversion_reaches_max_loss(self) -> None:
        """conversion = 1.0 should drive g_dn_scission_fraction to max."""
        rp = REAGENT_PROFILES["periodate_oxidation"]
        step = ModificationStep(
            step_type=ModificationStepType.ACS_CONVERSION,
            reagent_key="periodate_oxidation",
            target_acs=rp.target_acs,
            product_acs=rp.product_acs,
            temperature=rp.temperature_default,
            time=86400.0,
            ph=rp.ph_optimum,
            reagent_concentration=1e6,    # huge excess
        )
        result = solve_modification_step(
            step, _hydroxyl_profile(), _surface_model(), rp,
        )
        # At conversion ≈ 1.0, scission fraction ≈ max_loss = 0.70.
        assert result.g_dn_scission_fraction == pytest.approx(0.70, rel=1e-3)


# ─── (3) Per-protein pyridyl-disulfide couplers ────────────────────────


class TestPerProteinPyridylDisulfide:
    """Three new per-protein variants follow the protein_a_cys_coupling
    / protein_g_cys_coupling pattern but route through PYRIDYL_DISULFIDE
    rather than MALEIMIDE."""

    @pytest.mark.parametrize("variant_key,expected_mw,expected_hint", [
        ("protein_a_thiol_to_pyridyl_disulfide", 42000.0, "fc_affinity"),
        ("protein_g_thiol_to_pyridyl_disulfide", 22000.0, "fc_affinity"),
        ("protein_l_thiol_to_pyridyl_disulfide", 36000.0, "affinity"),
    ])
    def test_variant_targets_pyridyl_disulfide_with_correct_metadata(
        self, variant_key: str, expected_mw: float, expected_hint: str,
    ) -> None:
        rp = REAGENT_PROFILES[variant_key]
        assert rp.target_acs == ACSSiteType.PYRIDYL_DISULFIDE
        assert rp.chemistry_class == "thiol_disulfide_exchange"
        assert rp.functional_mode == "affinity_ligand"
        assert rp.is_macromolecule is True
        assert rp.ligand_mw == pytest.approx(expected_mw)
        assert rp.binding_model_hint == expected_hint
        assert "A_343" in rp.wetlab_observable

    def test_variants_use_reversible_redox_hazard(self) -> None:
        for key in (
            "protein_a_thiol_to_pyridyl_disulfide",
            "protein_g_thiol_to_pyridyl_disulfide",
            "protein_l_thiol_to_pyridyl_disulfide",
        ):
            assert REAGENT_PROFILES[key].hazard_class == "reversible_redox"

    def test_variants_route_under_protein_coupling_bucket(self) -> None:
        """The 3 variants share functional_mode='affinity_ligand' so they
        surface under the existing Protein Coupling bucket — no new
        dropdown bucket needed."""
        from dpsim.visualization.tabs.tab_m2 import _BUCKET_TO_MODES
        for key in (
            "protein_a_thiol_to_pyridyl_disulfide",
            "protein_g_thiol_to_pyridyl_disulfide",
            "protein_l_thiol_to_pyridyl_disulfide",
        ):
            mode = REAGENT_PROFILES[key].functional_mode
            buckets = [
                b for b, modes in _BUCKET_TO_MODES.items() if mode in modes
            ]
            assert buckets, f"{key} mode={mode} surfaces in no bucket"


# ─── (4) CNBr time-window enforcement (G6.5 strengthened) ──────────────


def _build_cnbr_recipe(intervening_minutes: list[float]) -> ProcessRecipe:
    """Helper: build a recipe with CNBr activation + N intervening washes
    of given durations + a coupling step. Each intervening step declares
    a structured Quantity for ``time`` so G6.5 can sum the gap."""
    steps: list[ProcessStep] = [
        ProcessStep(
            name="cnbr",
            stage=LifecycleStage.M2_FUNCTIONALIZATION,
            kind=ProcessStepKind.ACTIVATE,
            parameters={
                "reagent_key": "cnbr_activation",
                "time": Quantity(600.0, "s", source="recipe"),
            },
        ),
    ]
    for i, mins in enumerate(intervening_minutes):
        steps.append(
            ProcessStep(
                name=f"wash_{i}",
                stage=LifecycleStage.M2_FUNCTIONALIZATION,
                kind=ProcessStepKind.WASH,
                parameters={
                    "reagent_key": "wash_buffer",
                    "time": Quantity(mins * 60.0, "s", source="recipe"),
                },
            ),
        )
    steps.append(
        ProcessStep(
            name="couple_amine",
            stage=LifecycleStage.M2_FUNCTIONALIZATION,
            kind=ProcessStepKind.COUPLE_LIGAND,
            parameters={
                "reagent_key": "generic_amine_to_cyanate_ester",
                "time": Quantity(900.0, "s", source="recipe"),
            },
        ),
    )
    return ProcessRecipe(
        target=TargetProductProfile(),
        material_batch=MaterialBatch(polymer_family="agarose"),
        steps=steps,
    )


class TestCNBrTimeWindow:
    """G6.5 should emit:
      - BLOCKER when intervening-step time > 15 min
      - WARNING when 7.5 < intervening-step time <= 15 min
      - WARNING (existing) when no downstream coupling step
      - clean (no issue) when intervening time <= 7.5 min
    """

    def test_immediate_coupling_passes(self) -> None:
        recipe = _build_cnbr_recipe(intervening_minutes=[])
        report = validate_recipe_first_principles(recipe)
        codes = {issue.code for issue in report.issues}
        assert "FP_G6_CNBR_HYDROLYSIS_LOSS" not in codes
        assert "FP_G6_CNBR_WINDOW_AT_RISK" not in codes

    def test_short_intervening_wash_passes(self) -> None:
        recipe = _build_cnbr_recipe(intervening_minutes=[5.0])
        report = validate_recipe_first_principles(recipe)
        codes = {issue.code for issue in report.issues}
        assert "FP_G6_CNBR_HYDROLYSIS_LOSS" not in codes
        assert "FP_G6_CNBR_WINDOW_AT_RISK" not in codes

    def test_at_risk_intervening_wash_warns(self) -> None:
        # 10 min intervening → in the (7.5, 15] window → WARNING
        recipe = _build_cnbr_recipe(intervening_minutes=[10.0])
        report = validate_recipe_first_principles(recipe)
        codes = {issue.code for issue in report.issues}
        assert "FP_G6_CNBR_WINDOW_AT_RISK" in codes

    def test_long_intervening_wash_blocks(self) -> None:
        # 30 min intervening → exceeds 15 min limit → BLOCKER
        recipe = _build_cnbr_recipe(intervening_minutes=[30.0])
        report = validate_recipe_first_principles(recipe)
        codes = {issue.code for issue in report.issues}
        assert "FP_G6_CNBR_HYDROLYSIS_LOSS" in codes

    def test_multiple_intervening_steps_summed(self) -> None:
        # 8 + 8 = 16 min total → exceeds 15 min limit → BLOCKER
        recipe = _build_cnbr_recipe(intervening_minutes=[8.0, 8.0])
        report = validate_recipe_first_principles(recipe)
        codes = {issue.code for issue in report.issues}
        assert "FP_G6_CNBR_HYDROLYSIS_LOSS" in codes

    def test_no_followup_coupling_still_warns(self) -> None:
        """Pre-existing 'no follow-up coupling' WARNING must still fire."""
        steps = [
            ProcessStep(
                name="cnbr",
                stage=LifecycleStage.M2_FUNCTIONALIZATION,
                kind=ProcessStepKind.ACTIVATE,
                parameters={"reagent_key": "cnbr_activation"},
            ),
        ]
        recipe = ProcessRecipe(
            target=TargetProductProfile(),
            material_batch=MaterialBatch(polymer_family="agarose"),
            steps=steps,
        )
        report = validate_recipe_first_principles(recipe)
        codes = {issue.code for issue in report.issues}
        assert "FP_G6_CNBR_NO_COUPLING_FOLLOWUP" in codes
