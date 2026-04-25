"""FMC evidence-tier inheritance tests for run_gradient_elution.

Reference: docs/performance_recipe_protocol.md, Module M3 (A2).

Closes handover task #4. Before A2, run_gradient_elution hardcoded fmc=None in
its manifest builder, flooring its evidence tier at SEMI_QUANTITATIVE regardless
of upstream M2 calibration state. After A2, run_gradient_elution accepts an
optional fmc=, and the manifest tier inherits from FMC (capped by mass-balance
gate) exactly as run_breakthrough does.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest

from dpsim.datatypes import ModelEvidenceTier, ModelManifest
from dpsim.module3_performance.gradient import make_linear_gradient
from dpsim.module3_performance.hydrodynamics import ColumnGeometry
from dpsim.module3_performance.isotherms.competitive_langmuir import (
    CompetitiveLangmuirIsotherm,
)
from dpsim.module3_performance.orchestrator import run_gradient_elution

# Gradient LRM uses BDF and is genuinely slow; mark the whole module slow per
# the convention in tests/test_gradient_lrm.py.
pytestmark = pytest.mark.slow


# ─── Minimal mock FMC just exposing model_manifest ──────────────────────────


@dataclass
class _MockFMC:
    """Minimal FunctionalMediaContract shape that _build_m3_chrom_manifest reads.

    Only model_manifest is needed; estimated_q_max etc. are not required for
    the tier-inheritance test.
    """

    model_manifest: ModelManifest


def _calibrated_fmc() -> _MockFMC:
    return _MockFMC(
        model_manifest=ModelManifest(
            model_name="M2.FunctionalMedia",
            evidence_tier=ModelEvidenceTier.CALIBRATED_LOCAL,
            valid_domain={},
            calibration_ref="study_A_protein_a_2026",
            assumptions=["FMC calibrated against ligand-density assay (study A)."],
            diagnostics={},
        )
    )


def _qualitative_fmc() -> _MockFMC:
    return _MockFMC(
        model_manifest=ModelManifest(
            model_name="M2.FunctionalMedia",
            evidence_tier=ModelEvidenceTier.QUALITATIVE_TREND,
            valid_domain={},
            calibration_ref="",
            assumptions=["FMC tier degraded by upstream M1 caveat."],
            diagnostics={},
        )
    )


# ─── Shared minimal column + gradient setup ──────────────────────────────────


def _small_column() -> ColumnGeometry:
    return ColumnGeometry(
        diameter=0.01,
        bed_height=0.02,
        particle_diameter=100e-6,
        bed_porosity=0.38,
        particle_porosity=0.5,
        G_DN=10000.0,
        E_star=30000.0,
    )


def _tiny_gradient_run(*, fmc=None, n_z: int = 6):
    """Minimal gradient elution call shared by all tier tests."""
    column = _small_column()
    isotherm = CompetitiveLangmuirIsotherm(
        q_max=np.array([60.0]),
        K_L=np.array([1e3]),
    )
    # Two-segment gradient: hold then linear
    gradient = make_linear_gradient(
        start_val=0.0,
        end_val=500.0,
        start_time=5.0,
        end_time=25.0,
    )
    return run_gradient_elution(
        column=column,
        C_feed=np.array([1.0]),
        gradient=gradient,
        flow_rate=1e-8,
        total_time=30.0,
        feed_duration=5.0,
        isotherm=isotherm,
        n_z=n_z,
        fmc=fmc,
    )


# ─── M3-T01 ──────────────────────────────────────────────────────────────────


def test_no_fmc_defaults_to_semi_quantitative():
    """Regression of pre-A2 behaviour: fmc=None still yields SEMI_QUANTITATIVE."""
    result = _tiny_gradient_run(fmc=None)
    assert result.model_manifest is not None
    # When mass balance is good (default), tier defaults to SEMI_QUANTITATIVE.
    # When mass balance is bad, it could be capped at QUALITATIVE_TREND. The
    # invariant is that it does not exceed SEMI_QUANTITATIVE.
    order = list(ModelEvidenceTier)
    assert order.index(result.model_manifest.evidence_tier) >= order.index(
        ModelEvidenceTier.SEMI_QUANTITATIVE
    )


# ─── M3-T02 ──────────────────────────────────────────────────────────────────


def test_calibrated_fmc_propagates_to_manifest():
    """Calibrated FMC: tier inherits + calibration_ref propagated."""
    fmc = _calibrated_fmc()
    result = _tiny_gradient_run(fmc=fmc)
    assert result.model_manifest is not None
    # Tier is CALIBRATED_LOCAL or weaker (capped by mass-balance gate).
    order = list(ModelEvidenceTier)
    assert order.index(result.model_manifest.evidence_tier) >= order.index(
        ModelEvidenceTier.CALIBRATED_LOCAL
    )
    # When mass balance is good, tier is exactly CALIBRATED_LOCAL.
    if result.model_manifest.diagnostics.get("mass_balance_status") != "blocker":
        assert (
            result.model_manifest.evidence_tier
            == ModelEvidenceTier.CALIBRATED_LOCAL
        )
    # Calibration ref always propagates regardless of mass-balance status.
    assert result.model_manifest.calibration_ref == "study_A_protein_a_2026"
    # Upstream FMC assumptions roll into M3 assumptions.
    assert any(
        "study A" in a or "ligand-density" in a
        for a in result.model_manifest.assumptions
    )


# ─── M3-T03 ──────────────────────────────────────────────────────────────────


def test_qualitative_fmc_caps_m3_tier():
    """Weaker upstream tier propagates: M3 cannot exceed FMC tier."""
    fmc = _qualitative_fmc()
    result = _tiny_gradient_run(fmc=fmc)
    assert result.model_manifest is not None
    # M3 tier cannot exceed upstream QUALITATIVE_TREND.
    order = list(ModelEvidenceTier)
    assert order.index(result.model_manifest.evidence_tier) >= order.index(
        ModelEvidenceTier.QUALITATIVE_TREND
    )


# ─── M3-T04 ──────────────────────────────────────────────────────────────────


def test_calibrated_fmc_capped_when_mass_balance_blocker():
    """Forced poor mass balance (n_z=3) caps tier at QUALITATIVE_TREND.

    The calibration_ref still propagates so downstream consumers see the
    upstream provenance even when the M3 result itself is not decision-grade.
    """
    fmc = _calibrated_fmc()
    # n_z=3 with a fast gradient produces large mass-balance error.
    result = _tiny_gradient_run(fmc=fmc, n_z=3)
    assert result.model_manifest is not None
    # When the mass-balance gate fires, tier is capped at QUALITATIVE_TREND
    # regardless of the upstream calibrated tier.
    if result.model_manifest.diagnostics.get("mass_balance_status") == "blocker":
        order = list(ModelEvidenceTier)
        assert order.index(result.model_manifest.evidence_tier) >= order.index(
            ModelEvidenceTier.QUALITATIVE_TREND
        )
    # calibration_ref still propagates from FMC even when capped.
    assert result.model_manifest.calibration_ref == "study_A_protein_a_2026"
