"""v0.5.2 — codex review fixes for v0.5.1 release-breakers.

The v0.5.0 + v0.5.1 unit tests went through ``solve_modification_step``
directly, bypassing the orchestrator's preflight ``_validate_workflow_ordering``
and the recipe-level G6 FSM. Codex review flagged that the actual UI path
fails for the new chemistries because:

  P1-1 ``_STEP_ALLOWED_REACTION_TYPES`` (orchestrator preflight) only
       accepted ``"activation"`` for ACTIVATION; the new
       ``reaction_type="acs_conversion"`` profiles raised ValueError before
       dispatch.
  P1-2 The 3 per-protein pyridyl-disulfide variants and the 4 closed-loop
       generic couplers carry ``functional_mode="affinity_ligand"`` (so they
       surface in the Protein Coupling UI bucket) and ``reaction_type=
       "coupling"``; PROTEIN_COUPLING's allowlist required
       ``"protein_coupling"``, so dispatch raised ValueError.
  P2-1 ``ProcessStepKind`` had no arm-distal-activation kind, so a
       pyridyl-disulfide step had to be encoded as ACTIVATE; G6.1 then
       rejected the canonical INSERT_SPACER → ARM-activate → COUPLE_LIGAND
       sequence with FP_G6_SEQUENCE_OUT_OF_ORDER.
  P2-2 The CNBr 15-min coupling window summed durations via ``_qty_value()``
       which explicitly drops units; ``Quantity(30, "min")`` was treated as
       30 seconds and bypassed the BLOCKER.

These tests exercise each fix end-to-end through the orchestrator preflight
and recipe-level G6 guardrail, so a regression cannot land without surfacing.
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
from dpsim.core.recipe_validation import (
    _qty_to_seconds,
    validate_recipe_first_principles,
)
from dpsim.module2_functionalization.acs import ACSSiteType, ACSProfile
from dpsim.module2_functionalization.modification_steps import (
    ModificationStep,
    ModificationStepType,
    solve_modification_step,
)
from dpsim.module2_functionalization.orchestrator import _validate_workflow_ordering
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


def _pyridyl_disulfide_profile(n_sites: float = 1e-10) -> dict[ACSSiteType, ACSProfile]:
    return {
        ACSSiteType.PYRIDYL_DISULFIDE: ACSProfile(
            site_type=ACSSiteType.PYRIDYL_DISULFIDE,
            total_sites=n_sites,
            accessible_sites=n_sites,
            activated_sites=n_sites,
        ),
    }


def _step(step_type: ModificationStepType, reagent_key: str) -> ModificationStep:
    rp = REAGENT_PROFILES[reagent_key]
    return ModificationStep(
        step_type=step_type,
        reagent_key=reagent_key,
        target_acs=rp.target_acs,
        product_acs=rp.product_acs,
        temperature=rp.temperature_default,
        time=rp.time_default,
        ph=rp.ph_optimum,
        reagent_concentration=10.0,
    )


# ─── (P1-1) Orchestrator preflight accepts ACS converters ──────────────


class TestOrchestratorAcceptsACSConverters:
    """The orchestrator's ``_validate_workflow_ordering()`` runs BEFORE
    ``solve_modification_step()`` and has its own reaction-type allowlist.
    v0.5.1 only updated the dispatcher's allowlist, leaving the orchestrator
    preflight blind to ``reaction_type="acs_conversion"``."""

    @pytest.mark.parametrize("converter_key", [
        "cnbr_activation", "cdi_activation", "tresyl_chloride_activation",
        "cyanuric_chloride_activation", "glyoxyl_chained_activation",
        "periodate_oxidation",
    ])
    def test_silent_alias_path_passes_preflight(self, converter_key: str) -> None:
        """Legacy v0.4.x recipes that build steps with
        ``ModificationStepType.ACTIVATION`` carrying the new
        ``reaction_type="acs_conversion"`` reagents must pass preflight."""
        step = _step(ModificationStepType.ACTIVATION, converter_key)
        # No exception means preflight passed.
        _validate_workflow_ordering([step], _hydroxyl_profile())

    @pytest.mark.parametrize("converter_key", [
        "cnbr_activation", "cdi_activation", "tresyl_chloride_activation",
    ])
    def test_new_acs_conversion_step_passes_preflight(
        self, converter_key: str,
    ) -> None:
        step = _step(ModificationStepType.ACS_CONVERSION, converter_key)
        _validate_workflow_ordering([step], _hydroxyl_profile())

    def test_acs_conversion_product_can_feed_ligand_coupling_preflight(self) -> None:
        """A converter step creates activated ACS for the following coupler.

        Public sequence validation accepts CNBr ACTIVATE -> COUPLE_LIGAND;
        the backend preflight must mirror that lifecycle path when recipes
        are encoded with the v0.5+ ACS_CONVERSION step type.
        """
        steps = [
            _step(ModificationStepType.ACS_CONVERSION, "cnbr_activation"),
            _step(ModificationStepType.LIGAND_COUPLING, "generic_amine_to_cyanate_ester"),
        ]
        _validate_workflow_ordering(steps, _hydroxyl_profile())

    def test_pyridyl_disulfide_passes_preflight_as_arm_activation(self) -> None:
        # Build an AMINE_DISTAL profile so the arm-activation step has a
        # substrate to consume.
        acs_profiles = {
            ACSSiteType.AMINE_DISTAL: ACSProfile(
                site_type=ACSSiteType.AMINE_DISTAL,
                total_sites=1e-10,
                accessible_sites=1e-10,
                activated_sites=1e-10,
            ),
        }
        step = _step(
            ModificationStepType.ARM_ACTIVATION, "pyridyl_disulfide_activation",
        )
        _validate_workflow_ordering([step], acs_profiles)


# ─── (P1-2) PROTEIN_COUPLING accepts coupling reaction_type ────────────


class TestProteinCouplingAcceptsCouplingReagents:
    """The 3 per-protein pyridyl-disulfide variants and the 4 closed-loop
    generic couplers carry ``functional_mode="affinity_ligand"`` (Protein
    Coupling UI bucket) and ``reaction_type="coupling"``. PROTEIN_COUPLING
    dispatch + preflight previously rejected ``"coupling"`` and only
    accepted ``"protein_coupling"``."""

    @pytest.mark.parametrize("variant_key", [
        "protein_a_thiol_to_pyridyl_disulfide",
        "protein_g_thiol_to_pyridyl_disulfide",
        "protein_l_thiol_to_pyridyl_disulfide",
        "protein_thiol_to_pyridyl_disulfide",
    ])
    def test_per_protein_pyridyl_dispatches_via_protein_coupling(
        self, variant_key: str,
    ) -> None:
        step = _step(ModificationStepType.PROTEIN_COUPLING, variant_key)
        # Orchestrator preflight should pass.
        _validate_workflow_ordering([step], _pyridyl_disulfide_profile())
        # Dispatch should run cleanly and produce a result.
        result = solve_modification_step(
            step, _pyridyl_disulfide_profile(), _surface_model(),
            REAGENT_PROFILES[variant_key],
        )
        # Reagent has reaction_type="coupling"; PROTEIN_COUPLING accepts it.
        assert result.conversion >= 0.0  # ran without ValueError

    @pytest.mark.parametrize("coupler_key,target_profile_factory", [
        ("generic_amine_to_imidazolyl_carbonate",
         lambda: {
             ACSSiteType.IMIDAZOLYL_CARBONATE: ACSProfile(
                 site_type=ACSSiteType.IMIDAZOLYL_CARBONATE,
                 total_sites=1e-10, accessible_sites=1e-10, activated_sites=1e-10,
             ),
         }),
        ("generic_amine_to_sulfonate",
         lambda: {
             ACSSiteType.SULFONATE_LEAVING: ACSProfile(
                 site_type=ACSSiteType.SULFONATE_LEAVING,
                 total_sites=1e-10, accessible_sites=1e-10, activated_sites=1e-10,
             ),
         }),
        ("generic_amine_to_cyanate_ester",
         lambda: {
             ACSSiteType.CYANATE_ESTER: ACSProfile(
                 site_type=ACSSiteType.CYANATE_ESTER,
                 total_sites=1e-10, accessible_sites=1e-10, activated_sites=1e-10,
             ),
         }),
    ])
    def test_generic_amine_couplers_dispatch_via_protein_coupling(
        self, coupler_key: str, target_profile_factory,
    ) -> None:
        """The 4 closed-loop generic couplers (CDI / Tresyl / Pyridyl-PDS /
        CNBr canonical-amine routes) all carry ``functional_mode=
        "affinity_ligand"`` and surface in the Protein Coupling bucket. They
        must dispatch cleanly through PROTEIN_COUPLING."""
        step = _step(ModificationStepType.PROTEIN_COUPLING, coupler_key)
        _validate_workflow_ordering([step], target_profile_factory())
        result = solve_modification_step(
            step, target_profile_factory(), _surface_model(),
            REAGENT_PROFILES[coupler_key],
        )
        assert result.conversion >= 0.0


# ─── (P2-1) G6.1 ranks ARM_ACTIVATE after INSERT_SPACER ────────────────


class TestG6PhaseRankingForArmActivation:
    """The canonical ACS_CONVERSION → SPACER_ARM → ARM_ACTIVATE →
    COUPLE_LIGAND sequence must validate. v0.5.1 had ProcessStepKind.ACTIVATE
    at rank 1, blocking any arm-distal activation step that came AFTER an
    INSERT_SPACER step (rank 2)."""

    def _recipe(self, kind_for_pyridyl: ProcessStepKind) -> ProcessRecipe:
        steps = [
            ProcessStep(
                name="cnbr",
                stage=LifecycleStage.M2_FUNCTIONALIZATION,
                kind=ProcessStepKind.ACTIVATE,
                parameters={"reagent_key": "cnbr_activation"},
            ),
            ProcessStep(
                name="amine_arm",
                stage=LifecycleStage.M2_FUNCTIONALIZATION,
                kind=ProcessStepKind.INSERT_SPACER,
                parameters={"reagent_key": "eda_spacer_arm"},
            ),
            ProcessStep(
                name="pyridyl_pds",
                stage=LifecycleStage.M2_FUNCTIONALIZATION,
                kind=kind_for_pyridyl,
                parameters={"reagent_key": "pyridyl_disulfide_activation"},
            ),
            ProcessStep(
                name="couple_protein",
                stage=LifecycleStage.M2_FUNCTIONALIZATION,
                kind=ProcessStepKind.COUPLE_LIGAND,
                parameters={"reagent_key": "protein_a_thiol_to_pyridyl_disulfide"},
            ),
        ]
        return ProcessRecipe(
            target=TargetProductProfile(),
            material_batch=MaterialBatch(polymer_family="agarose_chitosan"),
            steps=steps,
        )

    def test_canonical_arm_activate_kind_validates(self) -> None:
        """The new ProcessStepKind.ARM_ACTIVATE must rank between
        INSERT_SPACER (2) and COUPLE_LIGAND (4)."""
        report = validate_recipe_first_principles(
            self._recipe(ProcessStepKind.ARM_ACTIVATE),
        )
        codes = {issue.code for issue in report.issues}
        assert "FP_G6_SEQUENCE_OUT_OF_ORDER" not in codes, (
            f"Canonical arm-activate sequence should validate; got {codes}"
        )

    def test_legacy_activate_kind_with_pyridyl_reagent_validates(self) -> None:
        """Pre-v0.5.2 recipes encoded pyridyl-disulfide as ACTIVATE because
        ARM_ACTIVATE didn't exist yet. The reagent-key override should
        rescue them so they don't suddenly start failing."""
        report = validate_recipe_first_principles(
            self._recipe(ProcessStepKind.ACTIVATE),
        )
        codes = {issue.code for issue in report.issues}
        assert "FP_G6_SEQUENCE_OUT_OF_ORDER" not in codes, (
            f"Legacy arm-activate-as-ACTIVATE should validate via reagent-"
            f"key override; got {codes}"
        )

    def test_out_of_order_message_mentions_arm_activate(self) -> None:
        steps = [
            ProcessStep(
                name="cnbr",
                stage=LifecycleStage.M2_FUNCTIONALIZATION,
                kind=ProcessStepKind.ACTIVATE,
                parameters={"reagent_key": "cnbr_activation"},
            ),
            ProcessStep(
                name="couple_protein",
                stage=LifecycleStage.M2_FUNCTIONALIZATION,
                kind=ProcessStepKind.COUPLE_LIGAND,
                parameters={"reagent_key": "protein_a_thiol_to_pyridyl_disulfide"},
            ),
            ProcessStep(
                name="pyridyl_pds",
                stage=LifecycleStage.M2_FUNCTIONALIZATION,
                kind=ProcessStepKind.ARM_ACTIVATE,
                parameters={"reagent_key": "pyridyl_disulfide_activation"},
            ),
        ]
        report = validate_recipe_first_principles(
            ProcessRecipe(
                target=TargetProductProfile(),
                material_batch=MaterialBatch(polymer_family="agarose_chitosan"),
                steps=steps,
            )
        )
        sequence_issues = [
            issue for issue in report.issues
            if issue.code == "FP_G6_SEQUENCE_OUT_OF_ORDER"
        ]
        assert sequence_issues
        assert "ARM_ACTIVATE" in sequence_issues[0].message


# ─── (P2-2) G6.5 honours time units on intervening steps ───────────────


class Test_qty_to_seconds:
    """``_qty_to_seconds`` must convert Quantity values with the standard
    lab time units (s, min, h)."""

    def test_quantity_in_seconds(self) -> None:
        assert _qty_to_seconds(Quantity(120.0, "s", source="t")) == pytest.approx(120.0)

    def test_quantity_in_minutes(self) -> None:
        assert _qty_to_seconds(Quantity(30.0, "min", source="t")) == pytest.approx(1800.0)

    def test_quantity_in_hours(self) -> None:
        assert _qty_to_seconds(Quantity(2.0, "h", source="t")) == pytest.approx(7200.0)

    def test_quantity_in_milliseconds(self) -> None:
        assert _qty_to_seconds(Quantity(500.0, "ms", source="t")) == pytest.approx(0.5)

    def test_bare_float_treated_as_seconds(self) -> None:
        assert _qty_to_seconds(60.0) == pytest.approx(60.0)

    def test_unknown_unit_returns_none(self) -> None:
        # Caller can decide whether to skip the check or raise.
        assert _qty_to_seconds(Quantity(30.0, "fortnight", source="t")) is None

    def test_none_returns_none(self) -> None:
        assert _qty_to_seconds(None) is None


class TestG6CNBrTimeWindowHonoursUnits:
    """G6.5 (CNBr 15-min window) must trigger the BLOCKER on a 30-minute
    wash regardless of whether it's declared in seconds or minutes."""

    def _recipe(self, wash_time_qty: Quantity) -> ProcessRecipe:
        return ProcessRecipe(
            target=TargetProductProfile(),
            material_batch=MaterialBatch(polymer_family="agarose"),
            steps=[
                ProcessStep(
                    name="cnbr",
                    stage=LifecycleStage.M2_FUNCTIONALIZATION,
                    kind=ProcessStepKind.ACTIVATE,
                    parameters={
                        "reagent_key": "cnbr_activation",
                        "time": Quantity(600.0, "s", source="recipe"),
                    },
                ),
                ProcessStep(
                    name="long_wash",
                    stage=LifecycleStage.M2_FUNCTIONALIZATION,
                    kind=ProcessStepKind.WASH,
                    parameters={
                        "reagent_key": "wash_buffer",
                        "time": wash_time_qty,
                    },
                ),
                ProcessStep(
                    name="couple_amine",
                    stage=LifecycleStage.M2_FUNCTIONALIZATION,
                    kind=ProcessStepKind.COUPLE_LIGAND,
                    parameters={
                        "reagent_key": "generic_amine_to_cyanate_ester",
                        "time": Quantity(900.0, "s", source="recipe"),
                    },
                ),
            ],
        )

    def test_30_minutes_in_minutes_unit_triggers_blocker(self) -> None:
        """A 30-min wash declared as Quantity(30, 'min') must be treated as
        1800 s, not 30 s, and trigger FP_G6_CNBR_HYDROLYSIS_LOSS."""
        report = validate_recipe_first_principles(
            self._recipe(Quantity(30.0, "min", source="recipe")),
        )
        codes = {issue.code for issue in report.issues}
        assert "FP_G6_CNBR_HYDROLYSIS_LOSS" in codes

    def test_30_minutes_in_seconds_unit_triggers_blocker(self) -> None:
        """Same 30-min wash declared as Quantity(1800, 's') must also trigger
        the BLOCKER. Sanity check that the conversion-aware path is symmetric."""
        report = validate_recipe_first_principles(
            self._recipe(Quantity(1800.0, "s", source="recipe")),
        )
        codes = {issue.code for issue in report.issues}
        assert "FP_G6_CNBR_HYDROLYSIS_LOSS" in codes

    def test_30_seconds_passes(self) -> None:
        """Sanity check: a 30-second wash (not minutes!) is well below
        the 7.5-min warning floor and should not trigger any G6.5 issue."""
        report = validate_recipe_first_principles(
            self._recipe(Quantity(30.0, "s", source="recipe")),
        )
        codes = {issue.code for issue in report.issues}
        assert "FP_G6_CNBR_HYDROLYSIS_LOSS" not in codes
        assert "FP_G6_CNBR_WINDOW_AT_RISK" not in codes

    def test_2_hours_in_hours_unit_triggers_blocker(self) -> None:
        """A 2-hour wash declared as Quantity(2, 'h') = 7200 s must trigger."""
        report = validate_recipe_first_principles(
            self._recipe(Quantity(2.0, "h", source="recipe")),
        )
        codes = {issue.code for issue in report.issues}
        assert "FP_G6_CNBR_HYDROLYSIS_LOSS" in codes
