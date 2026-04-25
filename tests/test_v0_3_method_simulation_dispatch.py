"""G3 acceptance tests — MethodSimulationResult MC dispatch.

Per architect § 3.3 (6 tests across TestDispatch, TestSchemaCompat,
TestRecipeIntegration). The smoke-baseline preservation gate (AC#5 /
R-G3-1) is the load-bearing test in this suite — when
``monte_carlo_n_samples=0`` the legacy result must remain byte-identical
to v0.2.x.

Reference: docs/handover/ARCH_v0_7_P5plusplus_DECOMPOSITION.md § 3.3.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest

from dpsim.calibration import PosteriorSamples
from dpsim.core.performance_recipe import DSDPolicy, PerformanceRecipe
from dpsim.module3_performance.method_simulation import (
    MethodSimulationResult,
    _maybe_run_monte_carlo,
)
from dpsim.module3_performance.monte_carlo import MCBands


# --------------------------------------------------------------------------- #
# Test fixtures: synthetic LRM-shaped solver                                   #
# --------------------------------------------------------------------------- #


@dataclass
class FakeLRMResult:
    mass_eluted: float
    mass_balance_error: float
    C_outlet: np.ndarray


def fake_lrm_solver(params: dict[str, float], tail_mode: bool) -> FakeLRMResult:
    q = params["q_max"]
    k = params["K_L"]
    n_t = 100
    return FakeLRMResult(
        mass_eluted=q * k,
        mass_balance_error=1e-4,
        C_outlet=np.linspace(0.0, q * k, n_t),
    )


def make_minimal_recipe(monte_carlo_n_samples: int = 0,
                        parameter_clips: dict | None = None) -> PerformanceRecipe:
    """Construct a minimal valid PerformanceRecipe for MC-only tests.

    The MC dispatch (`_maybe_run_monte_carlo`) reads only ``recipe.dsd_policy``,
    so the rest of the recipe can be a stub.
    """
    from dpsim.module3_performance.hydrodynamics import ColumnGeometry

    column = ColumnGeometry(
        diameter=0.01,
        bed_height=0.10,
        particle_diameter=50e-6,
    )
    policy = DSDPolicy(
        monte_carlo_n_samples=monte_carlo_n_samples,
        monte_carlo_n_seeds=4,
        monte_carlo_parameter_clips=parameter_clips,
    )
    return PerformanceRecipe(
        column=column,
        method_steps=[],
        feed_concentration_mol_m3=1.0,
        feed_duration_s=600.0,
        total_time_s=1800.0,
        dsd_policy=policy,
    )


# --------------------------------------------------------------------------- #
# 1) TestDispatch (3)                                                          #
# --------------------------------------------------------------------------- #


class TestDispatch:
    def test_n_samples_zero_returns_none(self) -> None:
        """AC#5 / R-G3-1: smoke baseline preserved bit-identically."""
        recipe = make_minimal_recipe(monte_carlo_n_samples=0)
        s = PosteriorSamples.from_marginals(("q_max", "K_L"), [10.0, 1e-3], [0.5, 5e-5])
        result = _maybe_run_monte_carlo(
            recipe=recipe,
            posterior_samples=s,
            mc_lrm_solver=fake_lrm_solver,
        )
        assert result is None

    def test_n_samples_positive_returns_mcbands(self) -> None:
        recipe = make_minimal_recipe(monte_carlo_n_samples=20)
        s = PosteriorSamples.from_marginals(("q_max", "K_L"), [10.0, 1e-3], [0.5, 5e-5])
        result = _maybe_run_monte_carlo(
            recipe=recipe,
            posterior_samples=s,
            mc_lrm_solver=fake_lrm_solver,
        )
        assert result is not None
        assert isinstance(result, MCBands)
        assert result.n_samples == 20
        assert "mass_eluted" in result.scalar_quantiles

    def test_default_n_samples_is_zero(self) -> None:
        """Default DSDPolicy has monte_carlo_n_samples=0 (off)."""
        policy = DSDPolicy()
        assert policy.monte_carlo_n_samples == 0
        assert policy.monte_carlo_n_seeds == 4
        assert policy.monte_carlo_parameter_clips is None


# --------------------------------------------------------------------------- #
# 2) TestSchemaCompat (2)                                                      #
# --------------------------------------------------------------------------- #


class TestSchemaCompat:
    def test_optional_field_dataclass_default_is_none(self) -> None:
        """Existing v0.x consumers see monte_carlo=None unless opted in.

        Verified via the dataclass field default itself — no need to
        construct a full MethodSimulationResult (whose representative
        type has a 9-field constructor).
        """
        import dataclasses

        fields = {
            f.name: f for f in dataclasses.fields(MethodSimulationResult)
        }
        assert "monte_carlo" in fields
        assert fields["monte_carlo"].default is None

    def test_as_summary_includes_monte_carlo_key(self) -> None:
        """as_summary surfaces 'monte_carlo' for both None and populated."""
        # Stub a representative-shaped object that as_summary touches.
        # The representative is only read for load_breakthrough fields
        # via duck-typing; we can mock with the smallest necessary
        # surface.
        from unittest.mock import MagicMock

        from dpsim.datatypes import ModelEvidenceTier, ModelManifest

        rep_stub = MagicMock()
        rep_stub.method_steps = []
        rep_stub.operability.pressure_drop_Pa = 1.0e5
        rep_stub.operability.bed_compression_fraction = 0.0
        rep_stub.load_breakthrough = None

        manifest = ModelManifest(
            model_name="test",
            evidence_tier=ModelEvidenceTier.SEMI_QUANTITATIVE,
        )

        result_off = MethodSimulationResult(
            representative=rep_stub,
            dsd_quantile_results=[],
            gradient_elution=None,
            model_manifest=manifest,
            assumptions=[],
            wet_lab_caveats=[],
        )
        summary_off = result_off.as_summary()
        assert "monte_carlo" in summary_off
        assert summary_off["monte_carlo"] is None

        recipe = make_minimal_recipe(monte_carlo_n_samples=20)
        s = PosteriorSamples.from_marginals(("q_max", "K_L"),
                                            [10.0, 1e-3], [0.5, 5e-5])
        bands = _maybe_run_monte_carlo(
            recipe=recipe,
            posterior_samples=s,
            mc_lrm_solver=fake_lrm_solver,
        )
        result_on = MethodSimulationResult(
            representative=rep_stub,
            dsd_quantile_results=[],
            gradient_elution=None,
            model_manifest=manifest,
            assumptions=[],
            wet_lab_caveats=[],
            monte_carlo=bands,
        )
        summary_on = result_on.as_summary()
        assert summary_on["monte_carlo"] is not None
        assert summary_on["monte_carlo"]["n_samples"] == 20
        assert "scalar_quantiles" in summary_on["monte_carlo"]
        assert "convergence_pass" in summary_on["monte_carlo"]


# --------------------------------------------------------------------------- #
# 3) TestRecipeIntegration (1)                                                 #
# --------------------------------------------------------------------------- #


class TestRecipeIntegration:
    def test_recipe_clips_propagate_to_run_mc(self) -> None:
        """Recipe-level monte_carlo_parameter_clips must reach run_mc()."""
        recipe = make_minimal_recipe(
            monte_carlo_n_samples=200,
            parameter_clips={"q_max": (9.5, 10.5)},
        )
        s = PosteriorSamples.from_marginals(
            ("q_max", "K_L"), [10.0, 1e-3], [3.0, 3e-4]
        )
        captured: list[float] = []

        def capture_solver(params: dict[str, float], tail_mode: bool) -> FakeLRMResult:
            captured.append(params["q_max"])
            return fake_lrm_solver(params, tail_mode)

        bands = _maybe_run_monte_carlo(
            recipe=recipe,
            posterior_samples=s,
            mc_lrm_solver=capture_solver,
        )
        assert bands is not None
        assert all(9.5 - 1e-12 <= q <= 10.5 + 1e-12 for q in captured)
        # Clip diagnostic captured
        assert bands.n_clipped.get("q_max", 0) > 0


# --------------------------------------------------------------------------- #
# 4) Smoke baseline guard: missing posterior or solver → None + warning        #
# --------------------------------------------------------------------------- #


def test_dispatch_skipped_when_posterior_missing(caplog: pytest.LogCaptureFixture) -> None:
    recipe = make_minimal_recipe(monte_carlo_n_samples=20)
    with caplog.at_level("WARNING", logger="dpsim.module3_performance.method_simulation"):
        result = _maybe_run_monte_carlo(
            recipe=recipe,
            posterior_samples=None,
            mc_lrm_solver=fake_lrm_solver,
        )
    assert result is None
    assert any("MC dispatch skipped" in r.message for r in caplog.records)


def test_dispatch_skipped_when_solver_missing(caplog: pytest.LogCaptureFixture) -> None:
    recipe = make_minimal_recipe(monte_carlo_n_samples=20)
    s = PosteriorSamples.from_marginals(("q_max", "K_L"), [10.0, 1e-3], [0.5, 5e-5])
    with caplog.at_level("WARNING", logger="dpsim.module3_performance.method_simulation"):
        result = _maybe_run_monte_carlo(
            recipe=recipe,
            posterior_samples=s,
            mc_lrm_solver=None,
        )
    assert result is None
