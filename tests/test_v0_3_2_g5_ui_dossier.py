"""G5 (v0.3.2) acceptance tests — Plotly band overlay + ProcessDossier MC.

Per architect § 5.1 — 4 tests across:
  TestBandRender (2)
  TestDossierSerialization (2)

Reference: docs/handover/ARCH_v0_7_P5plusplus_DECOMPOSITION.md § 5.1.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from dpsim.calibration import PosteriorSamples
from dpsim.module3_performance.monte_carlo import run_mc
from dpsim.process_dossier import ProcessDossier, _mc_bands_to_dict
from dpsim.visualization.plots_m3 import plot_mc_breakthrough_bands


# --------------------------------------------------------------------------- #
# Test fixtures: a small synthetic MCBands                                     #
# --------------------------------------------------------------------------- #


def _fake_lrm_solver(params: dict[str, float], tail_mode: bool):
    from dataclasses import dataclass

    @dataclass
    class FakeLRMResult:
        mass_eluted: float
        mass_balance_error: float
        C_outlet: np.ndarray

    q = params["q_max"]
    k = params["K_L"]
    n_t = 80
    return FakeLRMResult(
        mass_eluted=q * k,
        mass_balance_error=1e-4,
        C_outlet=np.linspace(0.0, q * k, n_t),
    )


def _make_mc_bands(n: int = 80, n_seeds: int = 4):
    s = PosteriorSamples.from_marginals(
        ("q_max", "K_L"), [10.0, 1e-3], [0.5, 5e-5]
    )
    return run_mc(s, _fake_lrm_solver, n=n, n_seeds=n_seeds, base_seed=7)


# --------------------------------------------------------------------------- #
# 1) TestBandRender (2)                                                        #
# --------------------------------------------------------------------------- #


class TestBandRender:
    def test_plot_renders_p05_p50_p95_traces(self) -> None:
        bands = _make_mc_bands()
        time = np.linspace(0.0, 600.0, 80)
        fig = plot_mc_breakthrough_bands(time, bands)
        # Expect 4 traces: envelope fill, P95, P50, P05
        trace_names = [t.name for t in fig.data]
        assert "P05 - P95 envelope" in trace_names
        assert "P50 (median)" in trace_names
        assert "P05" in trace_names
        assert "P95" in trace_names
        # Median trace must use teal-500 per DESIGN.md
        median = next(t for t in fig.data if t.name == "P50 (median)")
        assert median.line.color == "#14B8A6"

    def test_plot_surfaces_sa_q4_q5_assumptions_in_footer(self) -> None:
        bands = _make_mc_bands()
        time = np.linspace(0.0, 600.0, 80)
        fig = plot_mc_breakthrough_bands(time, bands)
        # Annotations array should contain footer with SA-Q4 + SA-Q5 cues
        ann_text = "\n".join(a.text for a in (fig.layout.annotations or []))
        assert "SA-Q4" in ann_text
        assert "SA-Q5" in ann_text
        # N samples line is also surfaced
        assert "successful samples" in ann_text


# --------------------------------------------------------------------------- #
# 2) TestDossierSerialization (2)                                              #
# --------------------------------------------------------------------------- #


class TestDossierSerialization:
    def test_mc_bands_round_trip_through_dossier_json(self) -> None:
        bands = _make_mc_bands(n=80, n_seeds=4)

        dossier = ProcessDossier(
            run_id="test-v032-g5",
            timestamp_utc="2026-04-25T00:00:00+00:00",
            full_result=None,
            mc_bands=bands,
        )
        d = dossier.to_json_dict()

        # Smoke: JSON-serialisable
        text = json.dumps(d, default=str)
        loaded = json.loads(text)

        mc = loaded["mc_bands"]
        assert mc is not None
        assert mc["schema_version"] == "mc_bands.1.0"
        assert mc["n_samples"] == bands.n_samples
        assert mc["solver_unstable"] == bands.solver_unstable
        assert "scalar_quantiles" in mc
        assert "mass_eluted" in mc["scalar_quantiles"]
        # convergence diagnostics surfaced
        assert "convergence_diagnostics" in mc
        assert "all_quantiles_stable" in mc["convergence_diagnostics"]

    def test_curve_decimation_bounds_dossier_size(self) -> None:
        # Construct a long-curve MCBands (~500 points) and confirm decimation
        s = PosteriorSamples.from_marginals(
            ("q_max", "K_L"), [10.0, 1e-3], [0.5, 5e-5]
        )

        def long_solver(params, tail_mode):
            from dataclasses import dataclass

            @dataclass
            class R:
                mass_eluted: float
                mass_balance_error: float
                C_outlet: np.ndarray

            q = params["q_max"]
            k = params["K_L"]
            return R(q * k, 1e-4, np.linspace(0.0, q * k, 500))

        bands = run_mc(s, long_solver, n=40, n_seeds=2, base_seed=11)
        # Default decimation is 100
        d = _mc_bands_to_dict(bands, decimate_curves_to=100)
        assert len(d["curve_bands"]["C_outlet_p50"]) == 100
        assert d["curve_bands_decimated_to"] == 100

        # No decimation
        d_full = _mc_bands_to_dict(bands, decimate_curves_to=None)
        assert len(d_full["curve_bands"]["C_outlet_p50"]) == 500
        assert d_full["curve_bands_decimated_to"] is None

    def test_none_mc_bands_does_not_break_dossier(self) -> None:
        dossier = ProcessDossier(
            run_id="test-v032-no-mc",
            timestamp_utc="2026-04-25T00:00:00+00:00",
            full_result=None,
            mc_bands=None,
        )
        d = dossier.to_json_dict()
        assert d["mc_bands"] is None
        # Smoke: JSON-serialises
        json.dumps(d, default=str)
