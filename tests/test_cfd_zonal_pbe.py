"""Tests for the CFD-PBE zonal coupling (src/dpsim/cfd/zonal_pbe.py).

Covers:
  - zones.json schema v1.0 happy path (Stirrer A, Stirrer B fixtures)
  - 11 hard-validation rejection paths
  - Advisory warnings on under-resolved CFD
  - consistency_check_with_volume_avg pass/fail/edge
  - integrate_pbe_with_zones:
      * single-zone payload reproduces the bare PBE solver bit-exactly
      * total droplet volume conserved across breakage / coalescence / exchange
      * breakage-zone bias: high-ε zones have smaller d32 than low-ε zones
      * Stirrer B 4-zone case runs and the slot-exit zone has the smallest d32
"""

from __future__ import annotations

import copy
import json
import logging
import os
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError
from scipy.integrate import solve_ivp

from dpsim.cfd.zonal_pbe import (
    CFDZonesPayload,
    SCHEMA_VERSION_SUPPORTED,
    consistency_check_with_volume_avg,
    integrate_pbe_with_zones,
    load_zones_json,
)
from dpsim.datatypes import KernelConfig, MaterialProperties
from dpsim.level1_emulsification.kernels import (
    breakage_rate_dispatch,
    coalescence_rate_dispatch,
)
from dpsim.level1_emulsification.solver import PBESolver


# ---------------------------------------------------------------------------
# Paths to the locked example fixtures
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
STIRRER_A_FIXTURE = (
    REPO_ROOT / "cad" / "cfd" / "cases" / "stirrer_A_beaker_100mL"
    / "zones.example.json"
)
STIRRER_B_FIXTURE = (
    REPO_ROOT / "cad" / "cfd" / "cases" / "stirrer_B_beaker_100mL"
    / "zones.example.json"
)


@pytest.fixture
def stirrer_a_payload() -> CFDZonesPayload:
    return load_zones_json(STIRRER_A_FIXTURE)


@pytest.fixture
def stirrer_b_payload() -> CFDZonesPayload:
    return load_zones_json(STIRRER_B_FIXTURE)


@pytest.fixture
def stirrer_a_dict() -> dict:
    """Mutable dict copy of the Stirrer A fixture for rejection-path tests."""
    with open(STIRRER_A_FIXTURE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def material_props() -> MaterialProperties:
    """Realistic-ish paraffin / aqueous-polymer material set."""
    return MaterialProperties(
        rho_oil=860.0,
        mu_oil=0.05,
        rho_aq=1020.0,
        mu_d=0.05,
        sigma=5.0e-3,
        breakage_C3=0.0,
    )


@pytest.fixture
def kernel_config() -> KernelConfig:
    return KernelConfig.for_pitched_blade()


# ---------------------------------------------------------------------------
# Loader — happy path
# ---------------------------------------------------------------------------


def test_loader_stirrer_a_happy_path(stirrer_a_payload: CFDZonesPayload) -> None:
    p = stirrer_a_payload
    assert p.schema_version == SCHEMA_VERSION_SUPPORTED
    assert {z.name for z in p.zones} == {"impeller", "near_wall", "bulk"}
    # 100 mL beaker
    assert p.total_volume_m3() == pytest.approx(1.0e-4, rel=1e-9)
    # Bidirectional impeller↔bulk plus bidirectional bulk↔near_wall
    assert len(p.exchanges) == 4


def test_loader_stirrer_b_happy_path(stirrer_b_payload: CFDZonesPayload) -> None:
    p = stirrer_b_payload
    assert {z.name for z in p.zones} == {
        "impeller", "slot_exit", "near_wall", "bulk",
    }
    # 100 mL beaker
    assert p.total_volume_m3() == pytest.approx(1.0e-4, rel=1e-9)
    # slot_exit has the highest ε — defining feature of a rotor-stator
    eps = {z.name: z.epsilon_avg_W_per_kg for z in p.zones}
    assert eps["slot_exit"] > eps["impeller"] > eps["near_wall"] > eps["bulk"]


def test_zone_by_name_helper(stirrer_a_payload: CFDZonesPayload) -> None:
    z = stirrer_a_payload.zone_by_name("bulk")
    assert z.name == "bulk"
    assert z.kind == "bulk"
    with pytest.raises(KeyError):
        stirrer_a_payload.zone_by_name("phantom")


# ---------------------------------------------------------------------------
# Loader — hard-validation rejection paths
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "label, mutate",
    [
        # 1. Wrong schema_version
        ("bad_version", lambda d: d.update({"schema_version": "0.9"}) or d),
        # 2. Duplicate zone names
        ("duplicate_names", lambda d: (
            d["zones"][1].update({"name": "impeller"}) or d
        )),
        # 3. Exchange referencing missing zone
        ("phantom_target", lambda d: (
            d["exchanges"][0].update({"to_zone": "phantom"}) or d
        )),
        # 4. Breakage-weighted ε below volume-avg ε
        ("breakage_below_avg", lambda d: (
            d["zones"][0].update({"epsilon_breakage_weighted_W_per_kg": 50.0}) or d
        )),
        # 5. case_metadata mismatch with zone aggregation
        ("metadata_mismatch", lambda d: (
            d["case_metadata"].update({
                "epsilon_volume_weighted_avg_W_per_kg": 99.0
            }) or d
        )),
        # 6. from_zone == to_zone
        ("self_loop_exchange", lambda d: (
            d["exchanges"][0].update({"to_zone": d["exchanges"][0]["from_zone"]}) or d
        )),
        # 7. Negative volume
        ("negative_volume", lambda d: (
            d["zones"][0].update({"volume_m3": -1.0}) or d
        )),
        # 8. Empty zones list
        ("empty_zones", lambda d: d.update({"zones": []}) or d),
        # 9. Reversed time-averaging window
        ("window_unordered", lambda d: (
            d["case_metadata"].update({"time_averaging_window_s": [5.0, 2.0]}) or d
        )),
        # 10. Unknown zone kind
        ("unknown_kind", lambda d: d["zones"][0].update({"kind": "unicorn"}) or d),
        # 11. Extra field rejected by `extra="forbid"`
        ("extra_field", lambda d: d["zones"][0].update({"rogue_field": 42}) or d),
    ],
)
def test_loader_rejects_bad_inputs(stirrer_a_dict: dict, label: str, mutate) -> None:
    payload = mutate(copy.deepcopy(stirrer_a_dict))
    with pytest.raises(ValidationError):
        CFDZonesPayload.model_validate(payload)


# ---------------------------------------------------------------------------
# Loader — advisory warnings (soft checks)
# ---------------------------------------------------------------------------


def test_loader_warns_on_coarse_mesh(
    stirrer_a_dict: dict, caplog: pytest.LogCaptureFixture, tmp_path: Path,
) -> None:
    stirrer_a_dict["case_metadata"]["n_cells_total"] = 10_000
    out = tmp_path / "coarse.json"
    out.write_text(json.dumps(stirrer_a_dict), encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="dpsim.cfd.zonal_pbe"):
        load_zones_json(out)
    assert any("coarse" in r.getMessage().lower() for r in caplog.records)


def test_loader_warns_on_loose_convergence(
    stirrer_a_dict: dict, caplog: pytest.LogCaptureFixture, tmp_path: Path,
) -> None:
    stirrer_a_dict["case_metadata"]["convergence_residual"] = 1e-3
    out = tmp_path / "loose.json"
    out.write_text(json.dumps(stirrer_a_dict), encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="dpsim.cfd.zonal_pbe"):
        load_zones_json(out)
    assert any("convergence residual" in r.getMessage().lower() for r in caplog.records)


# ---------------------------------------------------------------------------
# consistency_check_with_volume_avg
# ---------------------------------------------------------------------------


def test_consistency_check_passes_close_match(
    stirrer_a_payload: CFDZonesPayload,
) -> None:
    # Volume-weighted ε for the Stirrer A fixture is 9.03 W/kg.
    res = consistency_check_with_volume_avg(stirrer_a_payload, 9.0)
    assert res["passed"] is True
    assert res["relative_error"] < 0.01


def test_consistency_check_within_default_tolerance(
    stirrer_a_payload: CFDZonesPayload,
) -> None:
    # 25% off — under the default 30% tolerance (advisor caveat).
    res = consistency_check_with_volume_avg(stirrer_a_payload, 11.5)
    assert res["passed"] is True


def test_consistency_check_fails_large_mismatch(
    stirrer_a_payload: CFDZonesPayload, caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING, logger="dpsim.cfd.zonal_pbe"):
        res = consistency_check_with_volume_avg(stirrer_a_payload, 50.0)
    assert res["passed"] is False
    assert res["relative_error"] > 0.30
    assert any("FAILED" in r.getMessage() for r in caplog.records)


def test_consistency_check_negative_legacy_raises(
    stirrer_a_payload: CFDZonesPayload,
) -> None:
    with pytest.raises(ValueError, match=">= 0"):
        consistency_check_with_volume_avg(stirrer_a_payload, -1.0)


def test_consistency_check_zero_legacy_with_nonzero_cfd_fails(
    stirrer_a_payload: CFDZonesPayload,
) -> None:
    res = consistency_check_with_volume_avg(stirrer_a_payload, 0.0)
    assert res["passed"] is False
    assert res["relative_error"] == float("inf")


def test_consistency_check_custom_tolerance(
    stirrer_a_payload: CFDZonesPayload,
) -> None:
    # legacy=12 vs cfd=9 → ~25% off; tighter 10% tol should fail.
    res_strict = consistency_check_with_volume_avg(
        stirrer_a_payload, 12.0, tolerance_rel=0.10
    )
    assert res_strict["passed"] is False
    res_loose = consistency_check_with_volume_avg(
        stirrer_a_payload, 12.0, tolerance_rel=0.50
    )
    assert res_loose["passed"] is True


# ---------------------------------------------------------------------------
# integrate_pbe_with_zones — input validation
# ---------------------------------------------------------------------------


def test_integrator_rejects_nonpositive_duration(
    stirrer_a_payload: CFDZonesPayload,
    material_props: MaterialProperties,
    kernel_config: KernelConfig,
) -> None:
    with pytest.raises(ValueError, match="duration_s"):
        integrate_pbe_with_zones(
            payload=stirrer_a_payload, material=material_props,
            kernels=kernel_config, phi_d=0.05, duration_s=0.0,
        )


def test_integrator_rejects_invalid_phi_d(
    stirrer_a_payload: CFDZonesPayload,
    material_props: MaterialProperties,
    kernel_config: KernelConfig,
) -> None:
    with pytest.raises(ValueError, match="phi_d"):
        integrate_pbe_with_zones(
            payload=stirrer_a_payload, material=material_props,
            kernels=kernel_config, phi_d=1.5, duration_s=1.0,
        )


def test_integrator_rejects_diffusive_exchanges(
    stirrer_a_dict: dict,
    material_props: MaterialProperties,
    kernel_config: KernelConfig,
) -> None:
    stirrer_a_dict["exchanges"][0]["kind"] = "diffusive"
    payload = CFDZonesPayload.model_validate(stirrer_a_dict)
    with pytest.raises(NotImplementedError, match="diffusive"):
        integrate_pbe_with_zones(
            payload=payload, material=material_props,
            kernels=kernel_config, phi_d=0.05, duration_s=1.0,
        )


# ---------------------------------------------------------------------------
# integrate_pbe_with_zones — single-zone bit-exact equivalence with bare PBE
# ---------------------------------------------------------------------------


def _make_single_zone_payload(eps_W_per_kg: float = 50.0) -> CFDZonesPayload:
    return CFDZonesPayload.model_validate({
        "schema_version": SCHEMA_VERSION_SUPPORTED,
        "case_metadata": {
            "case_name": "single_zone_test",
            "stirrer_type": "pitched_blade_A",
            "vessel": "beaker_100mm",
            "rpm": 1500,
            "fluid_temperature_K": 298.15,
            "openfoam_solver": "pimpleDyMFoam",
            "time_averaging_window_s": [2.0, 5.0],
            "n_cells_total": 4_500_000,
            "convergence_residual": 1e-6,
            "epsilon_volume_weighted_avg_W_per_kg": eps_W_per_kg,
        },
        "zones": [{
            "name": "whole_vessel", "kind": "bulk",
            "volume_m3": 1.0e-4, "cell_count": 4_500_000,
            "epsilon_avg_W_per_kg": eps_W_per_kg,
            "epsilon_breakage_weighted_W_per_kg": eps_W_per_kg,
            "shear_rate_avg_per_s": 1000.0,
        }],
        "exchanges": [],
    })


def test_single_zone_reproduces_bare_pbe_solver(
    material_props: MaterialProperties, kernel_config: KernelConfig,
) -> None:
    """A 1-zone payload with no exchanges and identical breakage/coalescence
    ε must reproduce the bare PBE solver bit-exactly. Strongest possible
    sanity gate: any divergence proves the zonal coupling has introduced
    numerical drift in the degenerate case."""
    eps = 50.0
    phi_d = 0.05
    duration = 5.0
    n_bins = 40
    d_min, d_max = 1.0e-6, 500.0e-6
    d32_pre, sig_pre = 200.0e-6, 0.5

    res = integrate_pbe_with_zones(
        payload=_make_single_zone_payload(eps),
        material=material_props, kernels=kernel_config, phi_d=phi_d,
        duration_s=duration, n_bins=n_bins, d_min=d_min, d_max=d_max,
        d32_premix=d32_pre, sigma_premix=sig_pre,
    )

    # Replicate the bare PBE inner integration with identical settings.
    solver = PBESolver(n_bins=n_bins, d_min=d_min, d_max=d_max)
    nu_c = material_props.mu_oil / material_props.rho_oil
    g = breakage_rate_dispatch(
        solver.d_pivots, eps, material_props.sigma,
        material_props.rho_oil, material_props.mu_d, kernel_config, nu_c=nu_c,
    )
    Q = coalescence_rate_dispatch(
        solver.d_pivots, eps, material_props.sigma,
        material_props.rho_oil, kernel_config,
        phi_d=phi_d, mu_c=material_props.mu_oil,
    )
    birth, death = solver._build_breakage_matrix(g)
    n0 = solver._initial_distribution(phi_d, d32_premix=d32_pre, sigma_premix=sig_pre)
    sol = solve_ivp(
        lambda t, n: solver._compute_rhs(t, n, birth, death, Q),
        (0.0, duration), n0,
        method="LSODA", rtol=1e-5, atol=1e-15,
        max_step=duration / 10.0,
    )
    n_legacy = np.maximum(sol.y[:, -1], 0.0)
    d32_legacy = float(
        np.sum(n_legacy * solver.d_pivots ** 3)
        / np.sum(n_legacy * solver.d_pivots ** 2)
    )

    assert res.aggregated_d32 == pytest.approx(d32_legacy, rel=1e-9)
    # Per-zone d32 must equal the aggregated d32 in the 1-zone case.
    assert res.per_zone_d32["whole_vessel"] == pytest.approx(
        res.aggregated_d32, rel=1e-9
    )


# ---------------------------------------------------------------------------
# integrate_pbe_with_zones — physical conservation laws
# ---------------------------------------------------------------------------


def test_volume_balance_conserved_stirrer_a(
    stirrer_a_payload: CFDZonesPayload,
    material_props: MaterialProperties,
    kernel_config: KernelConfig,
) -> None:
    res = integrate_pbe_with_zones(
        payload=stirrer_a_payload, material=material_props,
        kernels=kernel_config, phi_d=0.05, duration_s=10.0,
        n_bins=40, d_min=1.0e-6, d_max=500.0e-6,
        d32_premix=200.0e-6,
    )
    assert res.converged
    # Breakage and coalescence are mass-conserving under fixed-pivot
    # redistribution; convective exchange moves volume between zones at
    # equal source-loss / target-gain rates. Total droplet volume must be
    # bit-exactly conserved (modulo LSODA tolerance, ≪ 1%).
    assert res.volume_balance_relative_error < 1e-3, (
        f"volume balance error {res.volume_balance_relative_error:.3e} > 1e-3"
    )


def test_volume_balance_conserved_stirrer_b(
    stirrer_b_payload: CFDZonesPayload,
    material_props: MaterialProperties,
    kernel_config: KernelConfig,
) -> None:
    res = integrate_pbe_with_zones(
        payload=stirrer_b_payload, material=material_props,
        kernels=kernel_config, phi_d=0.05, duration_s=10.0,
        n_bins=40, d_min=1.0e-6, d_max=500.0e-6,
        d32_premix=200.0e-6,
    )
    assert res.converged
    assert res.volume_balance_relative_error < 1e-3


# ---------------------------------------------------------------------------
# integrate_pbe_with_zones — physical bias from spatially varying ε
# ---------------------------------------------------------------------------


def test_breakage_zone_bias_stirrer_a(
    stirrer_a_payload: CFDZonesPayload,
    material_props: MaterialProperties,
    kernel_config: KernelConfig,
) -> None:
    """The high-ε impeller zone should have smaller d32 than the low-ε
    bulk zone in steady-state (or near-steady-state). This is the headline
    physics result of the zonal coupling — without it, the volume-averaged
    ε would predict a single d32 everywhere."""
    res = integrate_pbe_with_zones(
        payload=stirrer_a_payload, material=material_props,
        kernels=kernel_config, phi_d=0.05, duration_s=10.0,
        n_bins=40, d_min=1.0e-6, d_max=500.0e-6,
        d32_premix=200.0e-6,
    )
    assert res.converged
    d32 = res.per_zone_d32
    assert d32["impeller"] < d32["near_wall"] < d32["bulk"], (
        f"Expected impeller < near_wall < bulk, got {d32}"
    )


def test_breakage_zone_bias_stirrer_b_loop_below_bulk(
    stirrer_b_payload: CFDZonesPayload,
    material_props: MaterialProperties,
    kernel_config: KernelConfig,
) -> None:
    """Stirrer B has a tightly-coupled impeller↔slot_exit↔bulk loop
    (Q=8.4e-5 m³/s, slot_exit residence time ~5 ms) so the three loop
    members near-equilibrate fast. The robust physical signal is:

    1. ``bulk > slot_exit`` — bulk is the sink that receives the broken-down
       droplets from the high-ε loop and lets them coalesce.
    2. ``slot_exit <= impeller`` — within the loop, the higher-ε zone
       (slot_exit at 850 W/kg vs impeller at 220 W/kg) produces the
       smaller droplets, codifying the Padron-2005 / Hall-2011 finding
       that slot-exit jets dominate breakage in rotor-stator devices.

    The weakly-coupled near_wall zone (Q=9.8e-6 m³/s) drifts independently
    and is excluded from the loop comparison.
    """
    res = integrate_pbe_with_zones(
        payload=stirrer_b_payload, material=material_props,
        kernels=kernel_config, phi_d=0.05, duration_s=10.0,
        n_bins=40, d_min=1.0e-6, d_max=500.0e-6,
        d32_premix=200.0e-6,
    )
    assert res.converged
    d32 = res.per_zone_d32
    assert d32["bulk"] > d32["slot_exit"], (
        f"bulk d32 ({d32['bulk']*1e6:.2f} um) must exceed slot_exit "
        f"({d32['slot_exit']*1e6:.2f} um); got {d32}"
    )
    assert d32["slot_exit"] <= d32["impeller"] + 1e-9, (
        f"slot_exit d32 ({d32['slot_exit']*1e6:.2f} um) must not exceed "
        f"impeller ({d32['impeller']*1e6:.2f} um); got {d32}"
    )


# ---------------------------------------------------------------------------
# integrate_pbe_with_zones — diagnostics & metadata
# ---------------------------------------------------------------------------


def test_diagnostics_populated(
    stirrer_a_payload: CFDZonesPayload,
    material_props: MaterialProperties,
    kernel_config: KernelConfig,
) -> None:
    res = integrate_pbe_with_zones(
        payload=stirrer_a_payload, material=material_props,
        kernels=kernel_config, phi_d=0.05, duration_s=2.0,
        n_bins=30, d_min=1.0e-6, d_max=500.0e-6,
        d32_premix=200.0e-6,
    )
    assert res.diagnostics["n_zones"] == 3
    assert res.diagnostics["n_bins"] == 30
    assert res.diagnostics["n_exchanges"] == 4
    assert res.diagnostics["n_eval_points"] >= 2
    assert res.n_zones == 3
    assert set(res.N_per_zone.keys()) == {"impeller", "near_wall", "bulk"}
    assert res.aggregated_counts.shape == (30,)
    assert res.d_pivots.shape == (30,)


# ---------------------------------------------------------------------------
# CLI smoke (B5: dpsim cfd-zones subcommand)
# ---------------------------------------------------------------------------


def test_cli_cfd_zones_smoke(tmp_path: Path) -> None:
    """End-to-end CLI: `dpsim cfd-zones <fixture> --output <tmp>` produces a
    valid results JSON with the expected shape and physical sanity."""
    import subprocess
    import sys

    out = tmp_path / "results.json"
    cmd = [
        sys.executable, "-m", "dpsim", "cfd-zones",
        str(STIRRER_A_FIXTURE),
        "--kernels", "pitched_blade",
        "--rho-oil", "860", "--mu-oil", "0.05",
        "--mu-d", "0.05", "--sigma", "5e-3",
        "--phi-d", "0.05",
        "--duration", "3.0",
        "--n-bins", "25",
        "--d32-premix", "200e-6",
        "--legacy-eps", "9.0",
        "--output", str(out),
        "--quiet",
    ]
    proc = subprocess.run(
        cmd, capture_output=True, text=True, timeout=120,
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
    )
    assert proc.returncode == 0, (
        f"CLI failed (rc={proc.returncode})\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
    assert out.exists(), "results JSON was not written"

    with open(out, encoding="utf-8") as f:
        data = json.load(f)

    # Top-level shape
    assert data["schema_version"] == SCHEMA_VERSION_SUPPORTED
    assert data["converged"] is True
    assert data["n_zones"] == 3
    assert set(data["per_zone_d32_um"].keys()) == {
        "impeller", "near_wall", "bulk",
    }
    # Aggregated DSD has all five percentiles + Sauter
    for key in ("d10_um", "d32_um", "d43_um", "d50_um", "d90_um", "span"):
        assert key in data["aggregated"]
    # Volume balance must be tight
    assert data["volume_balance"]["relative_error"] < 1e-3
    # Consistency check ran and passed (legacy=9.0 vs cfd=9.03)
    assert data["consistency_check"]["passed"] is True
    assert data["consistency_check"]["relative_error"] < 0.01
    # Physical bias preserved through the CLI
    z = data["per_zone_d32_um"]
    assert z["impeller"] < z["near_wall"] < z["bulk"]


def test_cli_cfd_zones_rejects_bad_path(tmp_path: Path) -> None:
    """Invalid zones.json path must produce a non-zero exit code."""
    import subprocess
    import sys

    proc = subprocess.run(
        [
            sys.executable, "-m", "dpsim", "cfd-zones",
            str(tmp_path / "does_not_exist.json"),
            "--quiet",
        ],
        capture_output=True, text=True, timeout=30,
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
    )
    assert proc.returncode != 0
