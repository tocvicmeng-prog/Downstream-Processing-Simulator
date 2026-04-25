"""v0.3.6 — close all tracked v0.3.x follow-ons.

Seven fixes covered:

1. Click chemistry alkyne reference — adds inverse-direction CuAAC /
   SPAAC profiles whose ``target_acs=ALKYNE``. Closes the v0.3.5 ACS
   gap from 23/25 to 24/25 (the remaining ``sulfate_ester`` is a passive
   carrageenan polymer-side group, expected unreferenced).
2. Low-N MC warning — ``run_mc(n<100)`` emits a logger.warning per
   the R-G2-2 mitigation.
3. Joblib parallelism — ``run_mc(n_jobs>1, n_seeds>1)`` actually
   parallelises via joblib.Parallel(backend='loky'); R-G2-4
   determinism gate (n_jobs=1 vs n_jobs=4 byte-identical) preserved.
4. Solver-lambda helper — ``make_langmuir_lrm_solver`` returns a
   callable matching the LRMSolver contract; tail_mode flag tightens
   tolerances; non-physical samples raise ValueError so the driver's
   abort-and-resample path fires.
5. Pectin DE-dependence — ``solve_pectin_chitosan_pec_gelation``
   accepts ``degree_of_esterification``; HM pectin (DE>0.5) routes to
   UNSUPPORTED with a warning.
6. Gellan-alginate mixed K⁺/Ca²⁺ — ``solve_gellan_alginate_gelation``
   accepts ``c_K_bath_mM``; logistic K⁺ saturation lifts the
   reinforcement factor.
7. Pullulan-dextran STMP — ``solve_pullulan_dextran_gelation`` accepts
   ``crosslink_chemistry="stmp"``; pore-size expanded 1/0.85× over
   the ECH baseline.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import logging

import numpy as np
import pytest

from dpsim.calibration import PosteriorSamples
from dpsim.datatypes import (
    MaterialProperties,
    ModelEvidenceTier,
    PolymerFamily,
    SimulationParameters,
)
from dpsim.level2_gelation.v9_5_composites import (
    solve_gellan_alginate_gelation,
    solve_pectin_chitosan_pec_gelation,
    solve_pullulan_dextran_gelation,
)
from dpsim.module2_functionalization.acs import ACSSiteType
from dpsim.module2_functionalization.reagent_profiles import REAGENT_PROFILES
from dpsim.module3_performance.mc_solver_lambdas import (
    make_langmuir_lrm_solver,
)
from dpsim.module3_performance.monte_carlo import run_mc


# --------------------------------------------------------------------------- #
# Fix 1: Click chemistry alkyne reference                                      #
# --------------------------------------------------------------------------- #


class TestClickAlkyneReference:
    def test_inverse_direction_profiles_exist(self) -> None:
        assert "cuaac_click_alkyne_side" in REAGENT_PROFILES
        assert "spaac_click_alkyne_side" in REAGENT_PROFILES

    def test_alkyne_now_referenced_via_target_acs(self) -> None:
        referenced: set[str] = set()
        for profile in REAGENT_PROFILES.values():
            t = getattr(profile, "target_acs", None)
            if t is not None:
                referenced.add(getattr(t, "value", str(t)))
        assert "alkyne" in referenced, (
            "ALKYNE remains unreferenced after the v0.3.6 fix"
        )

    def test_acs_coverage_floor_lifted_to_24(self) -> None:
        """v0.3.5 baseline was 23/25; v0.3.6 should be 24/25 (only
        sulfate_ester remains, by design)."""
        referenced: set[str] = set()
        for profile in REAGENT_PROFILES.values():
            for attr in ("target_acs", "product_acs"):
                v = getattr(profile, attr, None)
                if v is not None:
                    referenced.add(getattr(v, "value", str(v)))
        all_acs = {st.value for st in ACSSiteType}
        coverage_count = len(referenced & all_acs)
        assert coverage_count >= 24
        # The only remaining gap is sulfate_ester (passive κ-carrageenan
        # polymer-side group)
        unreferenced = all_acs - referenced
        assert unreferenced == {"sulfate_ester"}, (
            f"Expected only 'sulfate_ester' unreferenced; "
            f"got {sorted(unreferenced)}"
        )

    def test_inverse_profiles_surface_under_click_chemistry_bucket(self) -> None:
        from dpsim.visualization.tabs.tab_m2 import (
            _reagent_options_for_bucket,
        )
        opts = _reagent_options_for_bucket("Click Chemistry")
        keys = set(opts.values())
        assert "cuaac_click_alkyne_side" in keys
        assert "spaac_click_alkyne_side" in keys


# --------------------------------------------------------------------------- #
# Fix 2: Low-N MC warning                                                      #
# --------------------------------------------------------------------------- #


@dataclass
class _FakeLRMResult:
    mass_eluted: float
    mass_balance_error: float
    C_outlet: np.ndarray


def _trivial_solver(params: dict[str, float], tail_mode: bool) -> _FakeLRMResult:
    val = params["q_max"] * params["K_L"]
    return _FakeLRMResult(
        mass_eluted=val,
        mass_balance_error=1e-4,
        C_outlet=np.linspace(0.0, val, 50),
    )


class TestLowNWarning:
    def test_n_below_100_emits_warning(
        self, caplog: pytest.LogCaptureFixture,
    ) -> None:
        s = PosteriorSamples.from_marginals(
            ("q_max", "K_L"), [10.0, 1e-3], [0.5, 5e-5]
        )
        with caplog.at_level(
            logging.WARNING, logger="dpsim.module3_performance.monte_carlo",
        ):
            run_mc(s, _trivial_solver, n=50, n_seeds=2, base_seed=11)
        msg = "\n".join(r.message for r in caplog.records)
        assert "n=50 < 100" in msg
        assert "AC#3" in msg

    def test_n_at_or_above_100_does_not_emit_low_n_warning(
        self, caplog: pytest.LogCaptureFixture,
    ) -> None:
        s = PosteriorSamples.from_marginals(
            ("q_max", "K_L"), [10.0, 1e-3], [0.5, 5e-5]
        )
        with caplog.at_level(
            logging.WARNING, logger="dpsim.module3_performance.monte_carlo",
        ):
            run_mc(s, _trivial_solver, n=100, n_seeds=2, base_seed=13)
        msg = "\n".join(r.message for r in caplog.records)
        assert "< 100" not in msg


# --------------------------------------------------------------------------- #
# Fix 3: Joblib parallelism                                                    #
# --------------------------------------------------------------------------- #


class TestJoblibParallelism:
    def test_njobs_4_results_match_njobs_1_byte_identical(self) -> None:
        """AC#4 — n_jobs=1 vs n_jobs=4 must produce byte-identical
        outputs because each per-seed sub-run uses base_seed + i
        deterministically."""
        s = PosteriorSamples.from_marginals(
            ("q_max", "K_L"), [10.0, 1e-3], [0.5, 5e-5]
        )
        a = run_mc(s, _trivial_solver, n=40, n_seeds=4, n_jobs=1, base_seed=42)
        b = run_mc(s, _trivial_solver, n=40, n_seeds=4, n_jobs=4, base_seed=42)
        assert a.scalar_quantiles == b.scalar_quantiles
        np.testing.assert_array_equal(
            a.curve_bands["C_outlet_p50"], b.curve_bands["C_outlet_p50"],
        )
        np.testing.assert_array_equal(
            a.curve_bands["C_outlet_p05"], b.curve_bands["C_outlet_p05"],
        )

    def test_njobs_4_aggregates_clip_counts_from_workers(self) -> None:
        """The parallel path must merge per-worker clip_counts back into
        the parent's diagnostic dict."""
        s = PosteriorSamples.from_marginals(
            ("q_max", "K_L"), [10.0, 1e-3], [3.0, 3e-4]
        )
        clips = {"q_max": (9.5, 10.5)}
        bands = run_mc(
            s, _trivial_solver, n=80, n_seeds=4, n_jobs=4,
            parameter_clips=clips, base_seed=23,
        )
        # In the previous (buggy) parallel path, n_clipped would be {}.
        assert bands.n_clipped.get("q_max", 0) > 0


# --------------------------------------------------------------------------- #
# Fix 4: Solver-lambda helper                                                  #
# --------------------------------------------------------------------------- #


class TestMakeLangmuirLRMSolver:
    def test_returns_callable_matching_lrm_solver_contract(self) -> None:
        from dpsim.module3_performance.hydrodynamics import ColumnGeometry
        col = ColumnGeometry(
            diameter=0.01, bed_height=0.1, particle_diameter=50e-6,
        )
        solver = make_langmuir_lrm_solver(
            column=col,
            C_feed=1.0,
            feed_duration=600.0,
            flow_rate=1.0e-8,
            total_time=1200.0,
        )
        assert callable(solver)

    def test_rejects_missing_q_max_or_K_L_in_parameter_names(self) -> None:
        from dpsim.module3_performance.hydrodynamics import ColumnGeometry
        col = ColumnGeometry(
            diameter=0.01, bed_height=0.1, particle_diameter=50e-6,
        )
        with pytest.raises(ValueError, match="q_max"):
            make_langmuir_lrm_solver(
                column=col,
                C_feed=1.0, feed_duration=600.0, flow_rate=1e-8,
                total_time=1200.0,
                parameter_names=("alpha", "beta"),
            )

    def test_non_physical_sample_raises_value_error(self) -> None:
        from dpsim.module3_performance.hydrodynamics import ColumnGeometry
        col = ColumnGeometry(
            diameter=0.01, bed_height=0.1, particle_diameter=50e-6,
        )
        solver = make_langmuir_lrm_solver(
            column=col,
            C_feed=1.0, feed_duration=600.0, flow_rate=1e-8,
            total_time=1200.0,
        )
        # Negative q_max is non-physical; must trigger the
        # abort-and-resample path in the driver.
        with pytest.raises(ValueError, match="Non-physical Langmuir"):
            solver({"q_max": -10.0, "K_L": 1e-3}, False)
        with pytest.raises(ValueError, match="Non-physical Langmuir"):
            solver({"q_max": 10.0, "K_L": 0.0}, False)


# --------------------------------------------------------------------------- #
# Fix 5: Pectin DE-dependence                                                  #
# --------------------------------------------------------------------------- #


class TestPectinDEDependence:
    def test_low_methoxy_default_is_qualitative_trend(self) -> None:
        props = replace(
            MaterialProperties(),
            polymer_family=PolymerFamily.PECTIN_CHITOSAN,
        )
        result = solve_pectin_chitosan_pec_gelation(
            SimulationParameters(), props, R_droplet=50e-6,
            degree_of_esterification=0.40,
        )
        diag = result.model_manifest.diagnostics
        assert diag["hm_pectin_unsupported"] is False
        assert diag["degree_of_esterification"] == 0.40
        assert (
            result.model_manifest.evidence_tier.value
            == ModelEvidenceTier.QUALITATIVE_TREND.value
        )

    def test_high_methoxy_routes_to_unsupported_tier(self) -> None:
        props = replace(
            MaterialProperties(),
            polymer_family=PolymerFamily.PECTIN_CHITOSAN,
        )
        result = solve_pectin_chitosan_pec_gelation(
            SimulationParameters(), props, R_droplet=50e-6,
            degree_of_esterification=0.70,
        )
        diag = result.model_manifest.diagnostics
        assert diag["hm_pectin_unsupported"] is True
        assert (
            result.model_manifest.evidence_tier.value
            == ModelEvidenceTier.UNSUPPORTED.value
        )
        assumption_text = "\n".join(result.model_manifest.assumptions)
        assert "HIGH-METHOXY PECTIN" in assumption_text
        assert "sugar-acid" in assumption_text

    def test_de_out_of_range_raises_value_error(self) -> None:
        props = replace(
            MaterialProperties(),
            polymer_family=PolymerFamily.PECTIN_CHITOSAN,
        )
        with pytest.raises(ValueError, match="degree_of_esterification"):
            solve_pectin_chitosan_pec_gelation(
                SimulationParameters(), props, R_droplet=50e-6,
                degree_of_esterification=1.5,
            )


# --------------------------------------------------------------------------- #
# Fix 6: Gellan-alginate mixed K+/Ca2+                                         #
# --------------------------------------------------------------------------- #


class TestGellanAlginateMixedBath:
    def test_default_ca_only_baseline_factor(self) -> None:
        props = replace(
            MaterialProperties(),
            polymer_family=PolymerFamily.GELLAN_ALGINATE,
        )
        result = solve_gellan_alginate_gelation(
            SimulationParameters(), props, R_droplet=50e-6,
        )
        diag = result.model_manifest.diagnostics
        assert diag["mixed_bath"] is False
        assert diag["C_K_bath_mM"] == 0.0
        # Baseline factor 1.20
        assert abs(diag["g_reinforcement_factor"] - 1.20) < 1e-9

    def test_mixed_bath_lifts_reinforcement_factor(self) -> None:
        props = replace(
            MaterialProperties(),
            polymer_family=PolymerFamily.GELLAN_ALGINATE,
        )
        baseline = solve_gellan_alginate_gelation(
            SimulationParameters(), props, R_droplet=50e-6,
        )
        mixed = solve_gellan_alginate_gelation(
            SimulationParameters(), props, R_droplet=50e-6,
            c_K_bath_mM=200.0,
        )
        bf = baseline.model_manifest.diagnostics["g_reinforcement_factor"]
        mf = mixed.model_manifest.diagnostics["g_reinforcement_factor"]
        assert mf > bf
        # Logistic with K_sat=100, max_boost=0.20: at K=200, boost ≈ 0.133
        assert mf == pytest.approx(1.20 + 0.20 * (200.0 / 300.0), abs=1e-6)
        assert mixed.model_manifest.diagnostics["mixed_bath"] is True

    def test_negative_K_bath_raises_value_error(self) -> None:
        props = replace(
            MaterialProperties(),
            polymer_family=PolymerFamily.GELLAN_ALGINATE,
        )
        with pytest.raises(ValueError, match="c_K_bath_mM"):
            solve_gellan_alginate_gelation(
                SimulationParameters(), props, R_droplet=50e-6,
                c_K_bath_mM=-10.0,
            )

    def test_zero_ca_bath_raises_value_error(self) -> None:
        props = replace(
            MaterialProperties(),
            polymer_family=PolymerFamily.GELLAN_ALGINATE,
        )
        with pytest.raises(ValueError, match="c_Ca_bath_mM"):
            solve_gellan_alginate_gelation(
                SimulationParameters(), props, R_droplet=50e-6,
                c_Ca_bath_mM=0.0,
            )


# --------------------------------------------------------------------------- #
# Fix 7: Pullulan-dextran STMP variant                                         #
# --------------------------------------------------------------------------- #


class TestPullulanDextranSTMP:
    def test_default_ech_chemistry(self) -> None:
        props = replace(
            MaterialProperties(),
            polymer_family=PolymerFamily.PULLULAN_DEXTRAN,
        )
        result = solve_pullulan_dextran_gelation(
            SimulationParameters(), props, R_droplet=50e-6,
        )
        assert result.model_manifest.diagnostics["primary_chemistry"] == "ECH"
        assert (
            result.model_manifest.diagnostics["crosslink_chemistry"] == "ech"
        )

    def test_stmp_variant_expands_pore_size(self) -> None:
        props = replace(
            MaterialProperties(),
            polymer_family=PolymerFamily.PULLULAN_DEXTRAN,
        )
        ech = solve_pullulan_dextran_gelation(
            SimulationParameters(), props, R_droplet=50e-6,
            crosslink_chemistry="ech",
        )
        stmp = solve_pullulan_dextran_gelation(
            SimulationParameters(), props, R_droplet=50e-6,
            crosslink_chemistry="stmp",
        )
        assert (
            stmp.model_manifest.diagnostics["primary_chemistry"] == "STMP"
        )
        if ech.pore_size_mean > 0 and stmp.pore_size_mean > 0:
            ratio = stmp.pore_size_mean / ech.pore_size_mean
            # 1/0.85 ≈ 1.176×
            assert ratio == pytest.approx(1.0 / 0.85, rel=1e-3)

    def test_stmp_assumption_block_mentions_phosphate(self) -> None:
        props = replace(
            MaterialProperties(),
            polymer_family=PolymerFamily.PULLULAN_DEXTRAN,
        )
        result = solve_pullulan_dextran_gelation(
            SimulationParameters(), props, R_droplet=50e-6,
            crosslink_chemistry="stmp",
        )
        text = "\n".join(result.model_manifest.assumptions)
        assert "STMP" in text
        assert "phosphate" in text.lower()

    def test_invalid_crosslink_chemistry_raises_value_error(self) -> None:
        props = replace(
            MaterialProperties(),
            polymer_family=PolymerFamily.PULLULAN_DEXTRAN,
        )
        with pytest.raises(ValueError, match="crosslink_chemistry"):
            solve_pullulan_dextran_gelation(
                SimulationParameters(), props, R_droplet=50e-6,
                crosslink_chemistry="genipin",
            )
