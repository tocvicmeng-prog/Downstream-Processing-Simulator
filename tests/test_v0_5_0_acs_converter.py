"""v0.5.0 ACS Converter epic — comprehensive regression tests.

Covers the six DoD areas from the M2 ACS-Converter joint redesign plan:
  1. New enum members and step types land cleanly.
  2. All 7 converter reagents dispatch through the ACS_CONVERSION step type.
  3. Pyridyl-disulfide chemistry is encoded with the corrected
     thiol-disulfide-exchange semantics (gap 2).
  4. Periodate produces 2x aldehyde inventory (gap 4).
  5. Sequence FSM rejects illegal orderings and accepts canonical ones.
  6. Every converter output ACS has at least one downstream consumer
     reagent (gap 1 closed-loop check).
  7. Family-reagent matrix has explicit verdicts for all 7 converters x
     21 polymer families (gap 3 closed-loop check).
"""

from __future__ import annotations

import pytest

from dpsim.datatypes import PolymerFamily
from dpsim.module2_functionalization.acs import (
    ACSSiteType,
    ACSProfile,
)
from dpsim.module2_functionalization.modification_steps import (
    ModificationStep,
    ModificationStepType,
    solve_modification_step,
)
from dpsim.module2_functionalization.orchestrator import validate_sequence
from dpsim.module2_functionalization.reagent_profiles import (
    REAGENT_PROFILES,
    ALLOWED_FUNCTIONAL_MODES,
    ALLOWED_CHEMISTRY_CLASSES,
)
from dpsim.module2_functionalization.surface_area import (
    AccessibleSurfaceModel,
    SurfaceAreaTier,
)
from dpsim.module2_functionalization.family_reagent_matrix import (
    FAMILY_REAGENT_MATRIX,
    check_family_reagent_compatibility,
)


_SEVEN_CONVERTERS = (
    "cnbr_activation",
    "cdi_activation",
    "tresyl_chloride_activation",
    "cyanuric_chloride_activation",
    "glyoxyl_chained_activation",
    "periodate_oxidation",
    "pyridyl_disulfide_activation",
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


def _amine_distal_profile(n_sites: float = 1e-10) -> dict[ACSSiteType, ACSProfile]:
    return {
        ACSSiteType.AMINE_DISTAL: ACSProfile(
            site_type=ACSSiteType.AMINE_DISTAL,
            total_sites=n_sites,
            accessible_sites=n_sites,
        ),
    }


# ─── (1) Enum members and step types ───────────────────────────────────


class TestEnumExpansion:
    """Verify new ACSSiteType and ModificationStepType members exist."""

    def test_pyridyl_disulfide_acs_member_exists(self) -> None:
        assert ACSSiteType.PYRIDYL_DISULFIDE.value == "pyridyl_disulfide"

    def test_acs_conversion_step_type_exists(self) -> None:
        assert ModificationStepType.ACS_CONVERSION.value == "acs_conversion"

    def test_arm_activation_step_type_exists(self) -> None:
        assert ModificationStepType.ARM_ACTIVATION.value == "arm_activation"

    def test_acs_converter_functional_mode_registered(self) -> None:
        assert "acs_converter" in ALLOWED_FUNCTIONAL_MODES

    def test_arm_activator_functional_mode_registered(self) -> None:
        assert "arm_activator" in ALLOWED_FUNCTIONAL_MODES

    def test_thiol_disulfide_exchange_chemistry_class_registered(self) -> None:
        assert "thiol_disulfide_exchange" in ALLOWED_CHEMISTRY_CLASSES

    def test_tresyl_amine_chemistry_class_registered(self) -> None:
        assert "tresyl_amine" in ALLOWED_CHEMISTRY_CLASSES


# ─── (2) Converter step dispatch ───────────────────────────────────────


class TestConverterStepDispatch:
    """Each of the 7 converters dispatches through ACS_CONVERSION (or
    ARM_ACTIVATION for pyridyl-disulfide) and produces the expected ACS."""

    @pytest.mark.parametrize("reagent_key", [
        "cnbr_activation", "cdi_activation", "tresyl_chloride_activation",
        "cyanuric_chloride_activation", "glyoxyl_chained_activation",
        "periodate_oxidation",
    ])
    def test_matrix_side_converter_produces_expected_acs(
        self, reagent_key: str,
    ) -> None:
        rp = REAGENT_PROFILES[reagent_key]
        assert rp.reaction_type == "acs_conversion", (
            f"{reagent_key} should be tagged reaction_type=acs_conversion, "
            f"got {rp.reaction_type!r}"
        )
        assert rp.functional_mode == "acs_converter"

        step = ModificationStep(
            step_type=ModificationStepType.ACS_CONVERSION,
            reagent_key=reagent_key,
            target_acs=rp.target_acs,
            product_acs=rp.product_acs,
            temperature=rp.temperature_default,
            time=rp.time_default,
            ph=rp.ph_optimum,
            reagent_concentration=10.0,
        )
        acs_state = _hydroxyl_profile()
        result = solve_modification_step(
            step, acs_state, _surface_model(), rp,
        )
        assert result.conversion > 0.0
        assert rp.product_acs in acs_state, (
            f"{reagent_key} did not create product profile {rp.product_acs}"
        )

    def test_pyridyl_disulfide_dispatches_via_arm_activation(self) -> None:
        rp = REAGENT_PROFILES["pyridyl_disulfide_activation"]
        assert rp.reaction_type == "arm_activation"
        assert rp.functional_mode == "arm_activator"

        step = ModificationStep(
            step_type=ModificationStepType.ARM_ACTIVATION,
            reagent_key="pyridyl_disulfide_activation",
            target_acs=rp.target_acs,
            product_acs=rp.product_acs,
            temperature=rp.temperature_default,
            time=rp.time_default,
            ph=rp.ph_optimum,
            reagent_concentration=10.0,
        )
        acs_state = _amine_distal_profile()
        result = solve_modification_step(
            step, acs_state, _surface_model(), rp,
        )
        assert result.conversion > 0.0
        assert ACSSiteType.PYRIDYL_DISULFIDE in acs_state

    def test_legacy_activation_step_still_works_for_ech(self) -> None:
        """Silent-alias guarantee — v0.4.x recipes using ECH/DVS as
        ModificationStepType.ACTIVATION must still dispatch correctly."""
        rp = REAGENT_PROFILES["ech_activation"]
        step = ModificationStep(
            step_type=ModificationStepType.ACTIVATION,
            reagent_key="ech_activation",
            target_acs=rp.target_acs,
            product_acs=rp.product_acs,
            temperature=rp.temperature_default,
            time=rp.time_default,
            ph=rp.ph_optimum,
            reagent_concentration=20.0,
        )
        acs_state = _hydroxyl_profile()
        result = solve_modification_step(
            step, acs_state, _surface_model(), rp,
        )
        assert result.conversion > 0.0
        assert ACSSiteType.EPOXIDE in acs_state


# ─── (3) Pyridyl-disulfide corrected chemistry ─────────────────────────


class TestPyridylDisulfideChemistry:
    """Gap 2: the v0.4.19 audit found product_acs=THIOL and
    chemistry_class='reduction' both chemically wrong. The v0.5.0 fix
    must have product_acs=PYRIDYL_DISULFIDE and chemistry_class=
    'thiol_disulfide_exchange'."""

    def test_product_acs_is_pyridyl_disulfide_not_thiol(self) -> None:
        rp = REAGENT_PROFILES["pyridyl_disulfide_activation"]
        assert rp.product_acs == ACSSiteType.PYRIDYL_DISULFIDE
        assert rp.product_acs != ACSSiteType.THIOL  # explicit anti-regression

    def test_chemistry_class_is_thiol_disulfide_exchange_not_reduction(self) -> None:
        rp = REAGENT_PROFILES["pyridyl_disulfide_activation"]
        assert rp.chemistry_class == "thiol_disulfide_exchange"
        assert rp.chemistry_class != "reduction"  # explicit anti-regression

    def test_target_acs_is_amine_distal(self) -> None:
        rp = REAGENT_PROFILES["pyridyl_disulfide_activation"]
        assert rp.target_acs == ACSSiteType.AMINE_DISTAL

    def test_protein_thiol_coupler_targets_pyridyl_disulfide(self) -> None:
        rp = REAGENT_PROFILES["protein_thiol_to_pyridyl_disulfide"]
        assert rp.target_acs == ACSSiteType.PYRIDYL_DISULFIDE
        assert rp.chemistry_class == "thiol_disulfide_exchange"

    def test_pyridyl_disulfide_has_a_343_observable(self) -> None:
        rp = REAGENT_PROFILES["pyridyl_disulfide_activation"]
        assert "A_343" in rp.wetlab_observable, (
            "Pyridyl-disulfide must declare the A_343 pyridine-2-thione "
            "observable for evidence-tier anchoring."
        )


# ─── (4) Periodate stoichiometry fix ───────────────────────────────────


class TestPeriodateAldehydeMultiplier:
    """Gap 4: one Malaprade cleavage of one diol pair produces TWO
    aldehydes. The aldehyde_multiplier=2.0 field must double the
    downstream ALDEHYDE inventory relative to sites_consumed."""

    def test_periodate_aldehyde_multiplier_is_two(self) -> None:
        rp = REAGENT_PROFILES["periodate_oxidation"]
        assert rp.aldehyde_multiplier == 2.0

    def test_glyoxyl_aldehyde_multiplier_is_two(self) -> None:
        rp = REAGENT_PROFILES["glyoxyl_chained_activation"]
        assert rp.aldehyde_multiplier == 2.0

    def test_other_converters_do_not_double(self) -> None:
        for key in (
            "cnbr_activation", "cdi_activation", "tresyl_chloride_activation",
            "cyanuric_chloride_activation", "ech_activation", "dvs_activation",
        ):
            rp = REAGENT_PROFILES[key]
            assert rp.aldehyde_multiplier == 1.0, (
                f"{key} should not double its product ACS"
            )

    def test_periodate_doubles_downstream_aldehyde(self) -> None:
        """End-to-end: hand a known diol-OH inventory to the solver
        through the activation path; expect ALDEHYDE inventory at 2x
        sites_consumed."""
        rp = REAGENT_PROFILES["periodate_oxidation"]
        # Generous excess reagent so conversion approaches 1 — keeps the
        # downstream-doubling check independent of conversion fraction.
        n_oh = 1e-9
        step = ModificationStep(
            step_type=ModificationStepType.ACS_CONVERSION,
            reagent_key="periodate_oxidation",
            target_acs=rp.target_acs,
            product_acs=rp.product_acs,
            temperature=rp.temperature_default,
            time=86400.0,           # 24 h — drive to plateau
            ph=rp.ph_optimum,
            reagent_concentration=1000.0,
        )
        acs_state = _hydroxyl_profile(n_sites=n_oh)
        result = solve_modification_step(
            step, acs_state, _surface_model(), rp,
        )
        oh_consumed = result.acs_after[ACSSiteType.HYDROXYL].activated_consumed_sites
        ald_created = acs_state[ACSSiteType.ALDEHYDE].accessible_sites
        # Aldehyde inventory ≈ 2 × consumed diol pairs (within 1% rounding).
        assert ald_created == pytest.approx(2.0 * oh_consumed, rel=1e-3), (
            f"Expected aldehyde count = 2 * consumed_diol; got "
            f"ald_created={ald_created:.4e}, oh_consumed={oh_consumed:.4e}"
        )


# ─── (5) Sequence FSM ──────────────────────────────────────────────────


class TestSequenceFSM:
    """validate_sequence enforces the canonical Converter -> Arm ->
    Ligand -> Ion-charging order with allowed skips and explicit
    rejections of illegal orderings."""

    def _step(self, step_type: ModificationStepType, reagent_key: str) -> ModificationStep:
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

    def test_canonical_order_is_valid(self) -> None:
        steps = [
            self._step(ModificationStepType.ACS_CONVERSION, "cnbr_activation"),
            self._step(ModificationStepType.LIGAND_COUPLING, "generic_amine_to_cyanate_ester"),
        ]
        violations = validate_sequence(steps, polymer_family="agarose")
        assert violations == []

    def test_metal_charge_without_ligand_blocks(self) -> None:
        steps = [
            self._step(ModificationStepType.ACS_CONVERSION, "cnbr_activation"),
            self._step(ModificationStepType.METAL_CHARGING, "nickel_charging"),
        ]
        violations = validate_sequence(steps, polymer_family="agarose")
        assert any("METAL_CHARGING" in v for v in violations)

    def test_pyridyl_disulfide_without_arm_blocks_on_non_native_amine_family(
        self,
    ) -> None:
        steps = [
            self._step(ModificationStepType.ARM_ACTIVATION, "pyridyl_disulfide_activation"),
            self._step(ModificationStepType.LIGAND_COUPLING, "protein_thiol_to_pyridyl_disulfide"),
        ]
        violations = validate_sequence(steps, polymer_family="agarose")
        assert any("arm-distal" in v for v in violations), (
            f"Expected arm-distal precondition violation; got {violations}"
        )

    def test_pyridyl_disulfide_passes_on_chitosan_native_amine(self) -> None:
        steps = [
            self._step(ModificationStepType.ARM_ACTIVATION, "pyridyl_disulfide_activation"),
            self._step(ModificationStepType.LIGAND_COUPLING, "protein_thiol_to_pyridyl_disulfide"),
        ]
        violations = validate_sequence(steps, polymer_family="chitosan")
        # No arm-distal blocker because chitosan is native-amine.
        assert not any("arm-distal" in v for v in violations), (
            f"Native-amine family should pass arm-distal check; got {violations}"
        )

    def test_pyridyl_disulfide_with_explicit_arm_passes(self) -> None:
        steps = [
            self._step(ModificationStepType.ACS_CONVERSION, "ech_activation"),
            self._step(ModificationStepType.SPACER_ARM, "eda_spacer_arm"),
            self._step(ModificationStepType.ARM_ACTIVATION, "pyridyl_disulfide_activation"),
            self._step(ModificationStepType.LIGAND_COUPLING, "protein_thiol_to_pyridyl_disulfide"),
        ]
        violations = validate_sequence(steps, polymer_family="agarose")
        assert violations == [], f"Canonical arm path should pass; got {violations}"

    def test_ligand_before_converter_blocks(self) -> None:
        steps = [
            self._step(ModificationStepType.LIGAND_COUPLING, "generic_amine_to_cyanate_ester"),
            self._step(ModificationStepType.ACS_CONVERSION, "cnbr_activation"),
        ]
        violations = validate_sequence(steps, polymer_family="agarose")
        assert any("later-phase" in v for v in violations)

    def test_cip_required_glyoxyl_without_nabh4_blocks(self) -> None:
        steps = [
            self._step(ModificationStepType.ACS_CONVERSION, "glyoxyl_chained_activation"),
            self._step(ModificationStepType.LIGAND_COUPLING, "multipoint_stability_uplift"),
        ]
        violations = validate_sequence(
            steps, polymer_family="agarose", cip_required=True,
        )
        assert any("NaBH4" in v for v in violations)

    def test_cip_required_glyoxyl_with_nabh4_passes(self) -> None:
        steps = [
            self._step(ModificationStepType.ACS_CONVERSION, "glyoxyl_chained_activation"),
            self._step(ModificationStepType.LIGAND_COUPLING, "multipoint_stability_uplift"),
            self._step(ModificationStepType.QUENCHING, "nabh4_quench"),
        ]
        violations = validate_sequence(
            steps, polymer_family="agarose", cip_required=True,
        )
        assert violations == []


# ─── (6) Closed-loop pairing ───────────────────────────────────────────


class TestClosedLoopPairing:
    """Gap 1: every converter's output ACS must have at least one
    downstream consumer reagent (target_acs == output_acs). Without
    this, the M2 ACS-matching contract silently breaks."""

    @pytest.mark.parametrize("converter_key", _SEVEN_CONVERTERS)
    def test_every_converter_has_a_consumer(self, converter_key: str) -> None:
        rp = REAGENT_PROFILES[converter_key]
        output = rp.product_acs
        assert output is not None, (
            f"{converter_key} has product_acs=None; cannot close loop."
        )
        consumers = [
            k for k, p in REAGENT_PROFILES.items()
            if p.target_acs == output and k != converter_key
        ]
        assert consumers, (
            f"{converter_key} produces {output.value} but no other reagent "
            f"consumes it. Add a coupling reagent with target_acs="
            f"ACSSiteType.{output.name}."
        )


# ─── (7) Family-reagent matrix coverage ────────────────────────────────


class TestFamilyMatrixCoverage:
    """Gap 3: every (converter, polymer_family) tuple must have an
    explicit verdict. Default-None ('no opinion') would silently bypass
    the G4 guardrail."""

    @pytest.mark.parametrize("converter_key", _SEVEN_CONVERTERS)
    def test_every_converter_x_family_has_explicit_verdict(
        self, converter_key: str,
    ) -> None:
        missing: list[str] = []
        for family in PolymerFamily:
            entry = check_family_reagent_compatibility(family, converter_key)
            if entry is None:
                missing.append(family.value)
        assert not missing, (
            f"{converter_key} missing matrix entries for: {missing}"
        )

    def test_cnbr_alginate_blocked(self) -> None:
        entry = check_family_reagent_compatibility(
            PolymerFamily.ALGINATE, "cnbr_activation",
        )
        assert entry is not None
        assert entry.compatibility == "incompatible"

    def test_periodate_dextran_compatible(self) -> None:
        entry = check_family_reagent_compatibility(
            PolymerFamily.DEXTRAN, "periodate_oxidation",
        )
        assert entry is not None
        assert entry.compatibility == "compatible"

    def test_pyridyl_disulfide_chitosan_compatible(self) -> None:
        entry = check_family_reagent_compatibility(
            PolymerFamily.CHITOSAN, "pyridyl_disulfide_activation",
        )
        assert entry is not None
        assert entry.compatibility == "compatible"

    def test_total_new_entries_count(self) -> None:
        new_keys_in_matrix = sum(
            1 for e in FAMILY_REAGENT_MATRIX
            if e.reagent_key in _SEVEN_CONVERTERS
        )
        n_families = len(list(PolymerFamily))
        assert new_keys_in_matrix == 7 * n_families, (
            f"Expected 7 converters × {n_families} families = "
            f"{7 * n_families} entries; got {new_keys_in_matrix}."
        )
