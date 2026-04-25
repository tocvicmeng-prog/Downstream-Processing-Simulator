"""Tests for run_method_simulation — the v0.2.0 unified M3 entry point.

Reference: docs/performance_recipe_protocol.md, Module M2 (A4).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import pytest

from dpsim.core.performance_recipe import (
    DSDPolicy,
    performance_recipe_from_resolved,
)
from dpsim.core.process_recipe import (
    default_affinity_media_recipe,
)
from dpsim.datatypes import ModelEvidenceTier, ModelManifest
from dpsim.lifecycle.recipe_resolver import resolve_lifecycle_inputs
from dpsim.module3_performance.method_simulation import (
    DSDQuantileResult,
    MethodSimulationResult,
    run_method_simulation,
)


# ─── Mock DSD payload ────────────────────────────────────────────────────────


@dataclass
class _MockDSDPayload:
    """Minimal payload exposing the quantile_table interface used by A4."""

    rows: list[dict[str, float]] = field(default_factory=list)
    d50_m: float = 100e-6

    def quantile_table(self, quantiles):
        if self.rows:
            return self.rows
        return [
            {"quantile": q, "diameter_m": self.d50_m, "mass_fraction": 1.0 / max(1, len(quantiles))}
            for q in quantiles
        ]


def _three_quantile_payload():
    return _MockDSDPayload(
        rows=[
            {"quantile": 0.10, "diameter_m": 60e-6, "mass_fraction": 0.20},
            {"quantile": 0.50, "diameter_m": 100e-6, "mass_fraction": 0.60},
            {"quantile": 0.90, "diameter_m": 160e-6, "mass_fraction": 0.20},
        ]
    )


def _calibrated_fmc():
    @dataclass
    class _FMC:
        estimated_q_max: float = 60.0
        ligand_accessible_area_per_bed_volume: float = 500.0
        reagent_accessible_area_per_bed_volume: float = 1000.0
        functional_ligand_density: float = 5.0
        total_coupled_density: float = 6.0
        activity_retention: float = 0.85
        ligand_leaching_fraction: float = 0.005
        confidence_tier: str = "calibrated"
        model_manifest: ModelManifest | None = None

        def __post_init__(self):
            if self.model_manifest is None:
                self.model_manifest = ModelManifest(
                    model_name="M2.FunctionalMedia",
                    evidence_tier=ModelEvidenceTier.CALIBRATED_LOCAL,
                    valid_domain={},
                    calibration_ref="study_A_2026",
                    assumptions=["FMC calibrated against ligand-density study A."],
                    diagnostics={},
                )

    return _FMC()


# ─── Default fixture ─────────────────────────────────────────────────────────


@pytest.fixture
def default_recipe():
    """Default PerformanceRecipe — d50 column, no DSD payload by default."""
    recipe = default_affinity_media_recipe()
    resolved = resolve_lifecycle_inputs(recipe)
    return performance_recipe_from_resolved(resolved)


# ─── M2-T01 — d50 path with FMC tier inheritance ─────────────────────────────


class TestRunMethodSimulationD50:
    def test_default_recipe_returns_method_simulation_result(self, default_recipe):
        result = run_method_simulation(default_recipe)
        assert isinstance(result, MethodSimulationResult)
        assert result.representative is not None
        assert result.dsd_quantile_results == []
        assert result.gradient_elution is None
        assert result.model_manifest is not None

    def test_load_breakthrough_present(self, default_recipe):
        result = run_method_simulation(default_recipe)
        assert result.representative.load_breakthrough is not None
        assert result.representative.load_breakthrough.dbc_10pct >= 0

    def test_calibrated_fmc_propagates(self, default_recipe):
        result = run_method_simulation(default_recipe, fmc=_calibrated_fmc())
        # Tier inherits CALIBRATED_LOCAL or capped lower (only by mass-balance).
        order = list(ModelEvidenceTier)
        assert order.index(result.model_manifest.evidence_tier) >= order.index(
            ModelEvidenceTier.CALIBRATED_LOCAL
        )
        assert result.model_manifest.calibration_ref == "study_A_2026"

    def test_no_fmc_yields_at_least_semi_quantitative(self, default_recipe):
        result = run_method_simulation(default_recipe)
        order = list(ModelEvidenceTier)
        assert order.index(result.model_manifest.evidence_tier) >= order.index(
            ModelEvidenceTier.SEMI_QUANTITATIVE
        )


# ─── M2-T02 — DSD full-method opt-in ─────────────────────────────────────────


class TestDSDFullMethod:
    @pytest.mark.slow
    def test_full_method_per_quantile(self, default_recipe):
        # Override policy to enable full method.
        recipe = default_recipe
        recipe.dsd_policy = DSDPolicy(
            quantiles=(0.10, 0.50, 0.90),
            run_full_method=True,
            fast_pressure_screen=False,
        )
        payload = _three_quantile_payload()
        result = run_method_simulation(recipe, dsd_payload=payload)
        assert len(result.dsd_quantile_results) == 3
        for q in result.dsd_quantile_results:
            assert isinstance(q, DSDQuantileResult)
            assert q.method_result is not None  # full method ran
            assert q.pressure_drop_Pa > 0
            assert q.diagnostics.get("path") == "full_method"

    def test_full_method_without_payload_raises(self, default_recipe):
        recipe = default_recipe
        recipe.dsd_policy = DSDPolicy(run_full_method=True, fast_pressure_screen=False)
        with pytest.raises(ValueError, match="dsd_payload"):
            run_method_simulation(recipe, dsd_payload=None)


# ─── M2-T03 — Fast pressure screen ───────────────────────────────────────────


class TestDSDFastScreen:
    def test_fast_pressure_screen_skips_lrm(self, default_recipe):
        recipe = default_recipe
        recipe.dsd_policy = DSDPolicy(
            quantiles=(0.10, 0.50, 0.90),
            run_full_method=False,
            fast_pressure_screen=True,
        )
        payload = _three_quantile_payload()
        result = run_method_simulation(recipe, dsd_payload=payload)
        assert len(result.dsd_quantile_results) == 3
        for q in result.dsd_quantile_results:
            assert q.method_result is None  # fast path skips full LRM
            assert q.pressure_drop_Pa > 0
            assert q.dbc_10pct_mol_m3 is None
            assert q.diagnostics.get("path") == "fast_pressure_screen"


# ─── M2-T04 — Gradient elute opt-in flag ─────────────────────────────────────


class TestGradientEluteOptIn:
    def test_default_recipe_has_intent_no_dispatch(self, default_recipe):
        # default recipe has gradient_field="ph" — but the explicit
        # competitive_gradient flag is NOT set, so dispatch does NOT happen.
        assert default_recipe.has_gradient_elute() is True
        result = run_method_simulation(default_recipe)
        assert result.gradient_elution is None  # opt-in not set

    @pytest.mark.slow
    def test_explicit_opt_in_enables_dispatch(self, default_recipe):
        # Set the metadata flag on the elute step.
        elute = default_recipe.elute_step()
        assert elute is not None
        elute.metadata["competitive_gradient"] = True
        result = run_method_simulation(default_recipe)
        assert result.gradient_elution is not None
        assert len(result.gradient_elution.peaks) >= 1


# ─── M2-T05 — Mass-balance gate caps tier ────────────────────────────────────


class TestMassBalanceGate:
    def test_low_n_z_floors_tier(self, default_recipe):
        # Tiny n_z forces poor mass balance; tier should be capped at
        # QUALITATIVE_TREND or weaker.
        default_recipe.n_z = 3
        result = run_method_simulation(default_recipe, fmc=_calibrated_fmc())
        order = list(ModelEvidenceTier)
        if result.model_manifest.diagnostics.get("max_mass_balance_error", 0.0) > 0.05:
            assert order.index(result.model_manifest.evidence_tier) >= order.index(
                ModelEvidenceTier.QUALITATIVE_TREND
            )


# ─── M2-T07 — as_summary is JSON-serializable ────────────────────────────────


class TestAsSummary:
    def test_summary_round_trips_through_json(self, default_recipe):
        result = run_method_simulation(default_recipe)
        summary = result.as_summary()
        # Must round-trip through json without errors.
        encoded = json.dumps(summary)
        decoded = json.loads(encoded)
        assert decoded["weakest_tier"] in {t.value for t in ModelEvidenceTier}
        assert "representative" in decoded
        assert "dsd_quantiles" in decoded
        assert decoded["gradient_elution_simulated"] in {True, False}
