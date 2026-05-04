"""B-1d (W-006): regime-guard diagnostics on the zonal CFD-PBE path.

Asserts that every successful integrate_pbe_with_zones call exposes:
  * eta_K_per_zone_m
  * d32_over_eta_K_per_zone
  * d32_over_eta_K_aggregated_min
  * sub_kolmogorov_zones (list, possibly empty)
  * breakage_C3 (from kernels)
  * regime_guard_warnings (list, possibly empty)

Plus: when the system is forced into the sub-Kolmogorov regime (very low
ε so eta_K is large and d32/eta_K stays small), the warning fires.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dpsim.cfd.zonal_pbe import (
    CFDZonesPayload,
    integrate_pbe_with_zones,
    load_zones_json,
)
from dpsim.datatypes import KernelConfig, MaterialProperties

REPO_ROOT = Path(__file__).resolve().parent.parent
STIRRER_A_FIXTURE = (
    REPO_ROOT / "cad" / "cfd" / "cases" / "stirrer_A_beaker_100mL"
    / "zones.example.json"
)


@pytest.fixture
def stirrer_a_payload() -> CFDZonesPayload:
    return load_zones_json(STIRRER_A_FIXTURE)


@pytest.fixture
def material_props() -> MaterialProperties:
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


# ─── Diagnostic shape ────────────────────────────────────────────────────────


class TestRegimeGuardShape:
    """Every result must carry the B-1d diagnostic keys."""

    def test_diagnostics_keys_present(self, stirrer_a_payload, material_props, kernel_config):
        result = integrate_pbe_with_zones(
            stirrer_a_payload, material_props, kernel_config,
            phi_d=0.10, duration_s=0.5,
        )
        diag = result.diagnostics
        for key in (
            "eta_K_per_zone_m",
            "d32_over_eta_K_per_zone",
            "d32_over_eta_K_aggregated_min",
            "sub_kolmogorov_zones",
            "sub_kolmogorov_ratio_threshold",
            "breakage_C3",
            "breakage_model",
            "regime_guard_warnings",
        ):
            assert key in diag, f"missing diagnostic '{key}'"

    def test_eta_K_one_per_zone(self, stirrer_a_payload, material_props, kernel_config):
        result = integrate_pbe_with_zones(
            stirrer_a_payload, material_props, kernel_config,
            phi_d=0.10, duration_s=0.5,
        )
        eta_K = result.diagnostics["eta_K_per_zone_m"]
        zone_names = {z.name for z in stirrer_a_payload.zones}
        assert set(eta_K.keys()) == zone_names
        for value in eta_K.values():
            assert value > 0.0  # finite for all zones with non-zero ε

    def test_breakage_C3_propagated_from_kernels(
        self, stirrer_a_payload, material_props,
    ):
        kernels = KernelConfig.for_pitched_blade()
        # for_pitched_blade sets breakage_C3=2.0 (viscous-correction-on)
        assert kernels.breakage_C3 == 2.0
        result = integrate_pbe_with_zones(
            stirrer_a_payload, material_props, kernels,
            phi_d=0.10, duration_s=0.5,
        )
        assert result.diagnostics["breakage_C3"] == pytest.approx(2.0)

    def test_aggregated_min_is_smallest_finite_ratio(
        self, stirrer_a_payload, material_props, kernel_config,
    ):
        result = integrate_pbe_with_zones(
            stirrer_a_payload, material_props, kernel_config,
            phi_d=0.10, duration_s=0.5,
        )
        per_zone = result.diagnostics["d32_over_eta_K_per_zone"]
        finite = [r for r in per_zone.values() if r > 0.0]
        if finite:
            assert result.diagnostics["d32_over_eta_K_aggregated_min"] == pytest.approx(
                min(finite)
            )


# ─── Sub-Kolmogorov detection ────────────────────────────────────────────────


class TestSubKolmogorovDetection:
    """Force a sub-Kolmogorov regime and confirm the warning fires."""

    def test_sub_kolmogorov_warning_emitted_when_d32_small(
        self, stirrer_a_payload, material_props, kernel_config,
    ):
        # Run a very short integration so d32 stays at the small premix
        # value (100 µm by default — but with small enough mu_oil and
        # high ε, η_K can be ~50 µm too). We pick a very high mu_oil to
        # push η_K up so d32/η_K << 5.
        viscous_props = MaterialProperties(
            rho_oil=860.0,
            mu_oil=5.0,        # 100x normal -> nu = 5/860 ~ 5.8e-3 m^2/s
            rho_aq=1020.0,
            mu_d=0.05,
            sigma=5.0e-3,
            breakage_C3=0.0,
        )
        result = integrate_pbe_with_zones(
            stirrer_a_payload, viscous_props, kernel_config,
            phi_d=0.10, duration_s=0.5,
            d32_premix=10.0e-6,  # 10 µm premix
        )
        # With nu_c huge and d32 small, every zone falls below 5x η_K.
        assert len(result.diagnostics["sub_kolmogorov_zones"]) > 0
        warnings = result.diagnostics["regime_guard_warnings"]
        assert any("Sub-Kolmogorov" in w for w in warnings)

    def test_warning_text_includes_breakage_C3(
        self, stirrer_a_payload, kernel_config,
    ):
        """When the warning fires, the message must surface the active
        breakage_C3 so the user can see whether the viscous correction is on.

        Liao & Lucas 2009 review note: most practical stirred-vessel
        emulsifications operate at d32/η_K ~ 1–10 (i.e. comparable scales),
        so the sub-Kolmogorov warning is expected to fire for the typical
        oil-in-water bench geometry. The diagnostic's value is in tagging
        the regime so downstream render-path layers can decide whether
        the d32 number is decision-grade.
        """
        viscous_props = MaterialProperties(
            rho_oil=860.0,
            mu_oil=1.0,
            rho_aq=1020.0,
            mu_d=0.05,
            sigma=5.0e-3,
            breakage_C3=0.0,
        )
        result = integrate_pbe_with_zones(
            stirrer_a_payload, viscous_props, kernel_config,
            phi_d=0.10, duration_s=0.5,
            d32_premix=20.0e-6,
        )
        warnings = result.diagnostics["regime_guard_warnings"]
        assert any("breakage_C3" in w for w in warnings)
