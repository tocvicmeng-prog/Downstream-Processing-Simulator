"""Tests for E2 — joblib n_jobs parallelism for DSD-quantile execution.

Reference: docs/handover/V0_5_0_DEPRECATION_REMOVAL_HANDOVER.md §9 v6-Q2.

Closes architect-coherence-audit D4 phase 1: DSDPolicy.n_jobs has been
API-shaped since v0.2.0 / A4 but never connected to a real joblib.Parallel
call. v0.6.0 wires it into ``_run_methods_parallel_or_serial`` so the
per-quantile full-method path can run in parallel.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from unittest.mock import patch

import pytest

from dpsim.core.performance_recipe import (
    DSDPolicy,
    performance_recipe_from_resolved,
)
from dpsim.core.process_recipe import default_affinity_media_recipe
from dpsim.lifecycle.recipe_resolver import resolve_lifecycle_inputs
from dpsim.module3_performance.method_simulation import (
    _run_method_worker,
    _run_methods_parallel_or_serial,
    run_method_simulation,
)


@dataclass
class _MockDSDPayload:
    """Minimal payload exposing quantile_table for the DSD path."""

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


@pytest.fixture
def default_recipe():
    """Default PerformanceRecipe — d50 column, no DSD payload by default."""
    recipe = default_affinity_media_recipe()
    resolved = resolve_lifecycle_inputs(recipe)
    return performance_recipe_from_resolved(resolved)


# ─── _run_methods_parallel_or_serial dispatch ───────────────────────────────


class TestDispatchSerialVsParallel:
    def test_n_jobs_1_uses_serial_path(self, default_recipe):
        """n_jobs=1 must NOT import or call joblib; pure serial."""
        from dpsim.module3_performance.method import run_chromatography_method

        called_count = 0
        original = run_chromatography_method

        def _spy(**kwargs):
            nonlocal called_count
            called_count += 1
            return original(**kwargs)

        with patch(
            "dpsim.module3_performance.method_simulation.run_chromatography_method",
            side_effect=_spy,
        ):
            kwargs_list = [
                {
                    "column": default_recipe.column,
                    "method_steps": list(default_recipe.method_steps),
                    "fmc": None,
                    "process_state": None,
                    "max_pressure_Pa": default_recipe.max_pressure_drop_Pa,
                    "pump_pressure_limit_Pa": default_recipe.pump_pressure_limit_Pa,
                    "n_z": default_recipe.n_z,
                    "D_molecular": default_recipe.D_molecular,
                    "k_ads": default_recipe.k_ads,
                }
            ]
            results = _run_methods_parallel_or_serial(kwargs_list, n_jobs=1)
        assert len(results) == 1
        assert called_count == 1

    def test_empty_list_returns_empty(self):
        """Edge case: empty list returns empty regardless of n_jobs."""
        assert _run_methods_parallel_or_serial([], n_jobs=4) == []

    def test_single_row_skips_parallel_path(self, default_recipe):
        """n_jobs > 1 with only one row should stay serial (skip joblib overhead)."""
        kwargs_list = [
            {
                "column": default_recipe.column,
                "method_steps": list(default_recipe.method_steps),
                "fmc": None,
                "process_state": None,
                "max_pressure_Pa": default_recipe.max_pressure_drop_Pa,
                "pump_pressure_limit_Pa": default_recipe.pump_pressure_limit_Pa,
                "n_z": default_recipe.n_z,
                "D_molecular": default_recipe.D_molecular,
                "k_ads": default_recipe.k_ads,
            }
        ]
        # No assertion on joblib non-import (hard to spy); just check it
        # runs to completion.
        results = _run_methods_parallel_or_serial(kwargs_list, n_jobs=4)
        assert len(results) == 1


# ─── DSDPolicy n_jobs flow ───────────────────────────────────────────────────


class TestDSDPolicyNJobs:
    def test_n_jobs_default_is_1(self):
        policy = DSDPolicy()
        assert policy.n_jobs == 1

    def test_custom_n_jobs_round_trips_through_recipe(self, default_recipe):
        custom = DSDPolicy(
            quantiles=(0.10, 0.50, 0.90),
            run_full_method=True,
            fast_pressure_screen=False,
            n_jobs=4,
        )
        # The PerformanceRecipe carries the policy verbatim.
        recipe = default_recipe
        recipe.dsd_policy = custom
        assert recipe.dsd_policy.n_jobs == 4


# ─── _run_method_worker is picklable (joblib loky requirement) ──────────────


class TestWorkerIsPicklable:
    def test_worker_is_module_level(self):
        """Joblib's loky backend requires a top-level (picklable) callable."""
        import inspect
        # The worker must be defined at module scope, not a closure.
        assert inspect.isfunction(_run_method_worker)
        assert _run_method_worker.__module__ == (
            "dpsim.module3_performance.method_simulation"
        )

    def test_worker_can_be_pickled(self):
        """Sanity check: pickle the worker reference (loky picklability)."""
        import pickle
        roundtripped = pickle.loads(pickle.dumps(_run_method_worker))
        assert roundtripped is _run_method_worker


# ─── End-to-end: n_jobs=1 vs n_jobs>1 produce same results ──────────────────


@pytest.mark.slow
class TestNJobsEquivalence:
    """Serial and parallel runs must produce numerically equivalent results.

    Marked slow because it runs the full M3 method 6× (3 quantiles × 2 modes).
    """

    def test_serial_and_parallel_match(self, default_recipe):
        recipe = default_recipe
        recipe.dsd_policy = DSDPolicy(
            quantiles=(0.10, 0.50, 0.90),
            run_full_method=True,
            fast_pressure_screen=False,
            n_jobs=1,  # serial
        )
        payload = _three_quantile_payload()
        serial = run_method_simulation(recipe, dsd_payload=payload)

        recipe.dsd_policy = DSDPolicy(
            quantiles=(0.10, 0.50, 0.90),
            run_full_method=True,
            fast_pressure_screen=False,
            n_jobs=2,  # parallel
        )
        parallel = run_method_simulation(recipe, dsd_payload=payload)

        # Both runs produce 3 quantile results in the same order.
        assert len(serial.dsd_quantile_results) == len(parallel.dsd_quantile_results) == 3
        for s_q, p_q in zip(serial.dsd_quantile_results, parallel.dsd_quantile_results):
            assert s_q.quantile == p_q.quantile
            # Pressure drop is deterministic for a given column geometry
            # → must match exactly.
            assert s_q.pressure_drop_Pa == pytest.approx(p_q.pressure_drop_Pa)
            # DBC / mass-balance from the LRM solver should match within
            # solver tolerance (BDF rtol=1e-6 → bit-identical in serial/parallel).
            if s_q.dbc_10pct_mol_m3 is not None and p_q.dbc_10pct_mol_m3 is not None:
                assert s_q.dbc_10pct_mol_m3 == pytest.approx(
                    p_q.dbc_10pct_mol_m3, rel=1e-9
                )
