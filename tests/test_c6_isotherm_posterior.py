"""Tests for C6 — Protein A pH-shape parameter posterior diagnostics.

Reference: docs/handover/V0_3_0_FAMILY_COVERAGE_HANDOVER.md §10 (v0.4.0 C6).
Closes the P5+ scope gap flagged by scientific-advisor §5: pH_transition and
pH_steepness posterior widths now surface in M3 calibration diagnostics.
"""

from __future__ import annotations

import pytest

from dpsim.calibration.calibration_data import CalibrationEntry
from dpsim.calibration.calibration_store import CalibrationStore
from dpsim.lifecycle.orchestrator import _m3_calibration_posterior_diagnostics


def _store_with_posteriors() -> CalibrationStore:
    """Build a calibration store with q_max + pH_transition + pH_steepness posteriors."""
    store = CalibrationStore()
    store.add(
        CalibrationEntry(
            profile_key="protein_a_coupling",
            parameter_name="estimated_q_max",
            measured_value=80.0,
            posterior_uncertainty=8.0,  # 10% sigma
            target_module="M3",
            units="mol/m3",
        )
    )
    store.add(
        CalibrationEntry(
            profile_key="protein_a_coupling",
            parameter_name="protein_a_pH_transition",
            measured_value=4.2,
            posterior_uncertainty=0.21,  # 5% sigma
            target_module="M3",
            units="1",
        )
    )
    store.add(
        CalibrationEntry(
            profile_key="protein_a_coupling",
            parameter_name="protein_a_pH_steepness",
            measured_value=4.0,
            posterior_uncertainty=0.4,  # 10% sigma
            target_module="M3",
            units="1/pH",
        )
    )
    return store


class TestpHShapePosteriorDiagnostics:
    """The pH-shape posterior widths are surfaced as M3 calibration diagnostics."""

    def test_pH_transition_relative_uncertainty_emitted(self):
        from unittest.mock import MagicMock

        # Mock M3 result + method + fmc with the minimal attributes the
        # diagnostics function reads.
        m3_result = MagicMock(dbc_10pct=10.0)
        method = MagicMock(step_results=[])
        fmc = MagicMock(estimated_q_max=80.0)

        store = _store_with_posteriors()
        diagnostics = _m3_calibration_posterior_diagnostics(
            calibration_store=store,
            m3_result=m3_result,
            method=method,
            fmc=fmc,
        )
        assert "protein_a_pH_transition_calibration_relative_uncertainty" in diagnostics
        # 0.21 / 4.2 = 0.05
        assert diagnostics[
            "protein_a_pH_transition_calibration_relative_uncertainty"
        ] == pytest.approx(0.05, rel=0.05)
        assert diagnostics["protein_a_pH_transition_calibration_sigma"] == pytest.approx(
            0.21, rel=0.05
        )

    def test_pH_steepness_relative_uncertainty_emitted(self):
        from unittest.mock import MagicMock

        m3_result = MagicMock(dbc_10pct=10.0)
        method = MagicMock(step_results=[])
        fmc = MagicMock(estimated_q_max=80.0)

        store = _store_with_posteriors()
        diagnostics = _m3_calibration_posterior_diagnostics(
            calibration_store=store,
            m3_result=m3_result,
            method=method,
            fmc=fmc,
        )
        assert "protein_a_pH_steepness_calibration_relative_uncertainty" in diagnostics
        # 0.4 / 4.0 = 0.10
        assert diagnostics[
            "protein_a_pH_steepness_calibration_relative_uncertainty"
        ] == pytest.approx(0.10, rel=0.05)
        assert diagnostics["protein_a_pH_steepness_calibration_sigma"] == pytest.approx(
            0.4, rel=0.05
        )

    def test_no_pH_posteriors_no_keys_emitted(self):
        from unittest.mock import MagicMock

        m3_result = MagicMock(dbc_10pct=10.0)
        method = MagicMock(step_results=[])
        fmc = MagicMock(estimated_q_max=80.0)

        # Store with only q_max posterior (no pH_transition / pH_steepness).
        store = CalibrationStore()
        store.add(
            CalibrationEntry(
                profile_key="protein_a_coupling",
                parameter_name="estimated_q_max",
                measured_value=80.0,
                posterior_uncertainty=8.0,
                target_module="M3",
                units="mol/m3",
            )
        )
        diagnostics = _m3_calibration_posterior_diagnostics(
            calibration_store=store,
            m3_result=m3_result,
            method=method,
            fmc=fmc,
        )
        assert "protein_a_pH_transition_calibration_relative_uncertainty" not in diagnostics
        assert "protein_a_pH_steepness_calibration_relative_uncertainty" not in diagnostics

    def test_max_uncertainty_includes_pH_shape(self):
        """The aggregate max-uncertainty diagnostic includes the pH-shape posteriors."""
        from unittest.mock import MagicMock

        m3_result = MagicMock(dbc_10pct=10.0)
        method = MagicMock(step_results=[])
        fmc = MagicMock(estimated_q_max=80.0)

        store = _store_with_posteriors()
        diagnostics = _m3_calibration_posterior_diagnostics(
            calibration_store=store,
            m3_result=m3_result,
            method=method,
            fmc=fmc,
        )
        # max relative is the largest of all relative uncertainties; with
        # q_max=10%, pH_transition=5%, pH_steepness=10%, max should be ≥ 10%.
        assert "calibration_posterior_relative_uncertainty_max" in diagnostics
        assert diagnostics[
            "calibration_posterior_relative_uncertainty_max"
        ] >= 0.095
