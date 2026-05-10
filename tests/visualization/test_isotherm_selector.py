"""Tests for the isotherm selector widget (B-1q / W-055, v0.8.4)."""

from __future__ import annotations

from typing import Any

import pytest

from dpsim.datatypes import ModelEvidenceTier, PolymerFamily
from dpsim.visualization.panels.isotherm_selector import (
    IsothermChoice,
    IsothermSpec,
    _default_choice_for,
    render_isotherm_widget,
)


class _StubContainer:
    """Stub Streamlit container for the isotherm-selector tests.

    Returns the seed defaults via number_input/checkbox/selectbox; the
    selectbox returns either the `default_index` value or an explicit
    override via `force_choice`.
    """

    def __init__(
        self,
        *,
        force_choice_value: str | None = None,
        force_calibrated: bool = False,
        force_n_components: int | None = None,
    ) -> None:
        self.force_choice_value = force_choice_value
        self.force_calibrated = force_calibrated
        self.force_n_components = force_n_components
        self.markdowns: list[str] = []
        self.captions: list[str] = []
        self._cols: list[Any] = []

    def markdown(self, text: str) -> None:
        self.markdowns.append(text)

    def caption(self, text: str) -> None:
        self.captions.append(text)

    def selectbox(self, label: str, options: list[str], **kwargs: Any) -> str:
        if self.force_choice_value is not None:
            return self.force_choice_value
        return options[kwargs.get("index", 0)]

    def number_input(self, label: str, **kwargs: Any) -> float:
        if (
            self.force_n_components is not None
            and "Number of components" in label
        ):
            return float(self.force_n_components)
        return float(kwargs.get("value", 0.0))

    def checkbox(self, label: str, **kwargs: Any) -> bool:
        return self.force_calibrated

    def columns(self, n: int) -> list["_StubContainer"]:
        cols = [
            _StubContainer(
                force_choice_value=self.force_choice_value,
                force_calibrated=self.force_calibrated,
                force_n_components=self.force_n_components,
            )
            for _ in range(n)
        ]
        self._cols.extend(cols)
        return cols


# ─── Family-aware default routing ──────────────────────────────────────────


class TestDefaultRouting:
    def test_agarose_chitosan_defaults_to_protein_a(self):
        # B-5a (W-078, v0.8.7): AGAROSE_CHITOSAN is the canonical
        # Protein-A workflow base resin; family default routes to
        # PROTEIN_A now that the dedicated isotherm is selectable.
        choice = _default_choice_for(
            PolymerFamily.AGAROSE_CHITOSAN, binding_model_hint=None,
        )
        assert choice.value == IsothermChoice.PROTEIN_A.value

    def test_alginate_defaults_to_salt_modulated(self):
        # ALGINATE is registered as IEX-friendly per the registry.
        choice = _default_choice_for(PolymerFamily.ALGINATE, None)
        assert choice.value == IsothermChoice.SALT_MODULATED_LANGMUIR.value

    def test_iex_hint_overrides_family(self):
        choice = _default_choice_for(
            PolymerFamily.AGAROSE,
            binding_model_hint="iex_anion",
        )
        # Hint takes precedence over family.
        assert choice.value == IsothermChoice.SALT_MODULATED_LANGMUIR.value

    def test_imac_hint_routes_to_imidazole(self):
        choice = _default_choice_for(
            PolymerFamily.AGAROSE_CHITOSAN,
            binding_model_hint="imac",
        )
        assert choice.value == IsothermChoice.IMIDAZOLE_MODULATED_LANGMUIR.value

    def test_protein_a_hint_routes_to_protein_a(self):
        # B-5a (W-078, v0.8.7): with the bare ProteinA isotherm
        # selectable, the protein_a hint routes to it directly.
        choice = _default_choice_for(
            PolymerFamily.AGAROSE_CHITOSAN,
            binding_model_hint="protein_a",
        )
        assert choice.value == IsothermChoice.PROTEIN_A.value

    def test_hic_hint_routes_to_hic(self):
        # B-5a (W-078, v0.8.7).
        from dpsim.visualization.panels.isotherm_selector import (
            _default_choice_for,
        )
        choice = _default_choice_for(
            PolymerFamily.AGAROSE,
            binding_model_hint="hic",
        )
        assert choice.value == IsothermChoice.HIC.value

    def test_unknown_family_defaults_to_langmuir(self):
        # HYALURONATE not in the family default table → fall through.
        choice = _default_choice_for(PolymerFamily.HYALURONATE, None)
        assert choice.value == IsothermChoice.LANGMUIR.value


# ─── Widget render — Langmuir default path ────────────────────────────────


class TestLangmuirRender:
    def test_returns_langmuir_spec(self):
        # Use HYALURONATE to get the Langmuir family default (was
        # AGAROSE_CHITOSAN before B-5a / v0.8.7 routed that to PROTEIN_A).
        c = _StubContainer()
        spec = render_isotherm_widget(
            container=c, key_prefix="t",
            polymer_family=PolymerFamily.HYALURONATE,
            binding_model_hint=None,
        )
        assert isinstance(spec, IsothermSpec)
        assert spec.choice.value == IsothermChoice.LANGMUIR.value
        assert "q_max_mol_m3" in spec.params
        assert "K_L_m3_mol" in spec.params
        # Bare Langmuir has no salt parameters.
        assert "nu" not in spec.params
        assert "c_salt_ref_mol_m3" not in spec.params

    def test_langmuir_tier_semi_quantitative(self):
        c = _StubContainer()
        spec = render_isotherm_widget(
            container=c, key_prefix="t",
            polymer_family=PolymerFamily.HYALURONATE,
        )
        # No calibrated_locally key for bare Langmuir → SEMI_QUANTITATIVE.
        assert spec.estimated_tier == ModelEvidenceTier.SEMI_QUANTITATIVE


class TestHICAndProteinARender:
    """B-5a (W-078, v0.8.7): HIC + PROTEIN_A bare-isotherm sub-forms."""

    def test_renders_hic_parameters(self):
        c = _StubContainer(
            force_choice_value=IsothermChoice.HIC.value,
        )
        spec = render_isotherm_widget(
            container=c, key_prefix="t",
            polymer_family=PolymerFamily.AGAROSE,
            binding_model_hint="hic",
        )
        assert spec.choice.value == IsothermChoice.HIC.value
        for k in ("q_max_mol_m3", "K_0_m3_mol", "m_salt_m3_mol", "salt_type"):
            assert k in spec.params

    def test_renders_protein_a_parameters(self):
        c = _StubContainer(
            force_choice_value=IsothermChoice.PROTEIN_A.value,
        )
        spec = render_isotherm_widget(
            container=c, key_prefix="t",
            polymer_family=PolymerFamily.AGAROSE_CHITOSAN,
            binding_model_hint="protein_a",
        )
        assert spec.choice.value == IsothermChoice.PROTEIN_A.value
        for k in ("q_max_mol_m3", "K_a_max_m3_mol", "pH_transition", "steepness"):
            assert k in spec.params


class TestToIsothermHICAndProteinA:
    """B-5a (W-078, v0.8.7): converter coverage for HIC + PROTEIN_A."""

    def test_to_isotherm_hic(self):
        from dpsim.visualization.panels.isotherm_selector import to_isotherm
        spec = IsothermSpec(
            choice=IsothermChoice.HIC,
            params={
                "q_max_mol_m3": 60.0, "K_0_m3_mol": 0.02,
                "m_salt_m3_mol": 0.008, "salt_type": "ammonium_sulfate",
            },
        )
        iso = to_isotherm(spec)
        assert type(iso).__name__ == "HICIsotherm"
        assert iso.q_max == 60.0
        assert iso.m_salt == 0.008

    def test_to_isotherm_protein_a(self):
        from dpsim.visualization.panels.isotherm_selector import to_isotherm
        spec = IsothermSpec(
            choice=IsothermChoice.PROTEIN_A,
            params={
                "q_max_mol_m3": 65.0, "K_a_max_m3_mol": 2.0e5,
                "pH_transition": 3.2, "steepness": 6.0,
            },
        )
        iso = to_isotherm(spec)
        assert type(iso).__name__ == "ProteinAIsotherm"
        assert iso.q_max == 65.0
        assert iso.pH_transition == 3.2


# ─── Widget render — modulated paths ──────────────────────────────────────


class TestSaltModulatedLangmuirRender:
    def test_renders_salt_parameters(self):
        c = _StubContainer(
            force_choice_value=IsothermChoice.SALT_MODULATED_LANGMUIR.value,
        )
        spec = render_isotherm_widget(
            container=c, key_prefix="t",
            polymer_family=PolymerFamily.ALGINATE,
        )
        assert spec.choice.value == IsothermChoice.SALT_MODULATED_LANGMUIR.value
        assert "nu" in spec.params
        assert "c_salt_ref_mol_m3" in spec.params

    def test_calibrated_flag_promotes_tier(self):
        c = _StubContainer(
            force_choice_value=IsothermChoice.SALT_MODULATED_LANGMUIR.value,
            force_calibrated=True,
        )
        spec = render_isotherm_widget(
            container=c, key_prefix="t",
            polymer_family=PolymerFamily.ALGINATE,
        )
        assert spec.estimated_tier == ModelEvidenceTier.CALIBRATED_LOCAL


class TestImidazoleModulatedRender:
    def test_renders_imidazole_parameters(self):
        c = _StubContainer(
            force_choice_value=IsothermChoice.IMIDAZOLE_MODULATED_LANGMUIR.value,
        )
        spec = render_isotherm_widget(
            container=c, key_prefix="t",
            polymer_family=PolymerFamily.AGAROSE_CHITOSAN,
            binding_model_hint="imac",
        )
        assert spec.choice.value == IsothermChoice.IMIDAZOLE_MODULATED_LANGMUIR.value
        assert "n" in spec.params
        assert "c_imidazole_ref_mol_m3" in spec.params


class TestSMARender:
    def test_renders_sma_parameters(self):
        c = _StubContainer(
            force_choice_value=IsothermChoice.SALT_MODULATED_SMA.value,
        )
        spec = render_isotherm_widget(
            container=c, key_prefix="t",
            polymer_family=PolymerFamily.ALGINATE,
        )
        assert spec.choice.value == IsothermChoice.SALT_MODULATED_SMA.value
        for k in ("z", "sigma", "K_eq", "Lambda", "c_salt_ref_mol_m3"):
            assert k in spec.params


class TestCompetitiveSaltRender:
    def test_renders_per_component_arrays(self):
        c = _StubContainer(
            force_choice_value=IsothermChoice.SALT_MODULATED_COMPETITIVE_LANGMUIR.value,
            force_n_components=3,
        )
        spec = render_isotherm_widget(
            container=c, key_prefix="t",
            polymer_family=PolymerFamily.ALGINATE,
        )
        assert spec.params["n_components"] == 3
        assert isinstance(spec.params["q_max_mol_m3"], list)
        assert len(spec.params["q_max_mol_m3"]) == 3
        assert len(spec.params["nu"]) == 3


# ─── Initial seed propagation ──────────────────────────────────────────────


class TestInitialSeed:
    def test_initial_spec_propagates_choice(self):
        seed = IsothermSpec(
            choice=IsothermChoice.SALT_MODULATED_LANGMUIR,
            params={
                "q_max_mol_m3": 250.0, "K_L_m3_mol": 5.0e3,
                "nu": 6.0, "c_salt_ref_mol_m3": 200.0,
                "calibrated_locally": False,
            },
        )
        c = _StubContainer(
            force_choice_value=IsothermChoice.SALT_MODULATED_LANGMUIR.value,
        )
        spec = render_isotherm_widget(
            container=c, key_prefix="t",
            polymer_family=PolymerFamily.AGAROSE_CHITOSAN,
            initial=seed,
        )
        assert spec.choice.value == seed.choice.value
        # Seed values flow through the stub (which echoes value=...).
        assert spec.params["q_max_mol_m3"] == pytest.approx(250.0)
        assert spec.params["nu"] == pytest.approx(6.0)


# ─── AST-gate compliance ──────────────────────────────────────────────────


class TestASTGateCompliance:
    def test_module_uses_no_is_comparisons(self):
        """The selector module must use only `.value` comparisons on
        IsothermChoice; the AST scanner test enforces this globally,
        but we duplicate the check here as a unit-test sentinel."""
        import inspect
        from dpsim.visualization.panels import isotherm_selector

        source = inspect.getsource(isotherm_selector)
        # Forbidden patterns:
        assert "is IsothermChoice." not in source
        assert "is not IsothermChoice." not in source
