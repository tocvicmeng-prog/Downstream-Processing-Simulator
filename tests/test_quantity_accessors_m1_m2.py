"""Tests for F2 + F4 — M1 and M2 typed Quantity accessor properties.

Reference: docs/handover/V0_6_0_QUANTITY_ACCESSORS_AND_PARALLELISM_HANDOVER.md
§9 v6.1-Q3 + §10 (v0.6.1 / E3.M2-accessors and v0.6.2 / M1 accessors).

Mirrors v0.6.0 / E1 (M3 dataclass accessors) for the M2 and M1 stages.
"""

from __future__ import annotations

import pytest

from dpsim.core.process_recipe import default_affinity_media_recipe
from dpsim.core.quantities import Quantity
from dpsim.lifecycle import DownstreamProcessOrchestrator


@pytest.fixture(scope="module")
def lifecycle_result():
    """Run the default lifecycle once and share the result across tests."""
    orch = DownstreamProcessOrchestrator()
    return orch.run(recipe=default_affinity_media_recipe(), propagate_dsd=False)


# ─── F2 — FunctionalMediaContract typed accessors ───────────────────────────


class TestFMCAccessors:
    def test_bead_d50_q(self, lifecycle_result):
        fmc = lifecycle_result.functional_media_contract
        q = fmc.bead_d50_q
        assert isinstance(q, Quantity)
        assert q.value == pytest.approx(fmc.bead_d50)
        assert q.unit == "m"

    def test_porosity_q_dimensionless(self, lifecycle_result):
        fmc = lifecycle_result.functional_media_contract
        assert fmc.porosity_q.unit == "1"
        assert fmc.porosity_q.value == pytest.approx(fmc.porosity)

    def test_pore_size_mean_q_unit_conversion(self, lifecycle_result):
        fmc = lifecycle_result.functional_media_contract
        nm_value = fmc.pore_size_mean_q.as_unit("nm").value
        assert nm_value == pytest.approx(fmc.pore_size_mean * 1e9)

    def test_estimated_q_max_q(self, lifecycle_result):
        fmc = lifecycle_result.functional_media_contract
        assert fmc.estimated_q_max_q.unit == "mol/m3"
        assert fmc.estimated_q_max_q.value == pytest.approx(fmc.estimated_q_max)

    def test_activity_retention_q(self, lifecycle_result):
        fmc = lifecycle_result.functional_media_contract
        assert fmc.activity_retention_q.unit == "1"
        assert fmc.activity_retention_q.value == pytest.approx(fmc.activity_retention)

    def test_functional_ligand_density_q(self, lifecycle_result):
        fmc = lifecycle_result.functional_media_contract
        assert fmc.functional_ligand_density_q.unit == "mol/m2"


# ─── F2 — ModificationResult typed accessors ────────────────────────────────


class TestModificationResultAccessors:
    def test_conversion_q(self, lifecycle_result):
        history = lifecycle_result.m2_microsphere.modification_history
        assert history
        first = history[0]
        assert first.conversion_q.unit == "1"
        assert first.conversion_q.value == pytest.approx(first.conversion)

    def test_delta_G_DN_q(self, lifecycle_result):
        history = lifecycle_result.m2_microsphere.modification_history
        first = history[0]
        assert first.delta_G_DN_q.unit == "Pa"
        assert first.delta_G_DN_q.value == pytest.approx(first.delta_G_DN)


# ─── F2 — ACSProfile typed accessors ────────────────────────────────────────


class TestACSProfileAccessors:
    def test_total_sites_q(self, lifecycle_result):
        microsphere = lifecycle_result.m2_microsphere
        # Take the first ACS profile from the post-modification inventory
        first_profile = next(iter(microsphere.acs_profiles.values()))
        assert first_profile.total_sites_q.unit == "mol"
        assert first_profile.total_sites_q.value == pytest.approx(
            first_profile.total_sites
        )

    def test_remaining_sites_q(self, lifecycle_result):
        microsphere = lifecycle_result.m2_microsphere
        first_profile = next(iter(microsphere.acs_profiles.values()))
        assert first_profile.remaining_sites_q.unit == "mol"
        # remaining_sites is itself a property; the _q accessor should agree.
        assert first_profile.remaining_sites_q.value == pytest.approx(
            first_profile.remaining_sites
        )

    def test_total_density_q(self, lifecycle_result):
        microsphere = lifecycle_result.m2_microsphere
        first_profile = next(iter(microsphere.acs_profiles.values()))
        assert first_profile.total_density_q.unit == "mol/m2"


# ─── F4 — M1 result accessors ───────────────────────────────────────────────


class TestEmulsificationResultAccessors:
    def test_d32_q(self, lifecycle_result):
        e = lifecycle_result.m1_result.emulsification
        assert e.d32_q.unit == "m"
        assert e.d32_q.value == pytest.approx(e.d32)

    def test_d50_q_unit_conversion_to_um(self, lifecycle_result):
        e = lifecycle_result.m1_result.emulsification
        um_value = e.d50_q.as_unit("um").value
        assert um_value == pytest.approx(e.d50 * 1e6)

    def test_span_q_dimensionless(self, lifecycle_result):
        e = lifecycle_result.m1_result.emulsification
        assert e.span_q.unit == "1"


class TestGelationResultAccessors:
    def test_pore_size_mean_q(self, lifecycle_result):
        g = lifecycle_result.m1_result.gelation
        assert g.pore_size_mean_q.unit == "m"
        nm_value = g.pore_size_mean_q.as_unit("nm").value
        assert nm_value == pytest.approx(g.pore_size_mean * 1e9)

    def test_porosity_q_dimensionless(self, lifecycle_result):
        g = lifecycle_result.m1_result.gelation
        assert g.porosity_q.unit == "1"

    def test_alpha_final_q(self, lifecycle_result):
        g = lifecycle_result.m1_result.gelation
        assert g.alpha_final_q.unit == "1"


class TestCrosslinkingResultAccessors:
    def test_p_final_q(self, lifecycle_result):
        x = lifecycle_result.m1_result.crosslinking
        assert x.p_final_q.unit == "1"
        assert x.p_final_q.value == pytest.approx(x.p_final)

    def test_G_chitosan_final_q(self, lifecycle_result):
        x = lifecycle_result.m1_result.crosslinking
        assert x.G_chitosan_final_q.unit == "Pa"

    def test_xi_final_q(self, lifecycle_result):
        x = lifecycle_result.m1_result.crosslinking
        assert x.xi_final_q.unit == "m"


class TestMechanicalResultAccessors:
    def test_G_DN_q_kpa_conversion(self, lifecycle_result):
        m = lifecycle_result.m1_result.mechanical
        kpa_value = m.G_DN_q.as_unit("kPa").value
        assert kpa_value == pytest.approx(m.G_DN / 1000.0)

    def test_E_star_q(self, lifecycle_result):
        m = lifecycle_result.m1_result.mechanical
        assert m.E_star_q.unit == "Pa"
        assert m.E_star_q.value == pytest.approx(m.E_star)

    def test_G_agarose_and_chitosan_q(self, lifecycle_result):
        m = lifecycle_result.m1_result.mechanical
        assert m.G_agarose_q.unit == "Pa"
        assert m.G_chitosan_q.unit == "Pa"

    def test_pore_size_and_xi_mesh_q(self, lifecycle_result):
        m = lifecycle_result.m1_result.mechanical
        assert m.pore_size_mean_q.unit == "m"
        assert m.xi_mesh_q.unit == "m"
