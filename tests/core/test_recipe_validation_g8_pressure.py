"""B-2h / W-028 tests: G8 pressure-envelope sanity gate.

Recipe-side pre-flight that surfaces obviously-unsafe flow rates BEFORE
the lifecycle orchestrator starts the long M1+M2+M3 chain. Mirrors the
G7 pH-window shape from B-1a.

Scope limit per docstring: G8 cannot compute the full PressureEnvelope
because G_DN_updated and bead_d32 are not yet available at recipe-
validation time. The lifecycle-side check (W-025) does the full
envelope. G8 only checks for obviously-pathological declared flow
rates.
"""

from __future__ import annotations

from typing import Any

from dpsim.core.process_recipe import (
    LifecycleStage,
    ProcessRecipe,
    ProcessStep,
    ProcessStepKind,
    TargetProductProfile,
)
from dpsim.core.recipe_validation import _g8_pressure_envelope_check
from dpsim.core.validation import ValidationReport, ValidationSeverity


def _make_recipe(*, flow_rate: Any) -> ProcessRecipe:
    """Single-step recipe with the given flow_rate parameter."""
    return ProcessRecipe(
        target=TargetProductProfile(),
        steps=[
            ProcessStep(
                stage=LifecycleStage.M3_PERFORMANCE,
                kind=ProcessStepKind.LOAD,
                name="load",
                parameters={"flow_rate": flow_rate},
            ),
        ],
    )


class TestG8FlowRateSanity:
    """G8 flags negative and absurdly-large flow rates."""

    def test_positive_normal_flow_passes(self) -> None:
        # 5 mL/min ≈ 8.3e-8 m³/s — typical analytical chromatography.
        report = ValidationReport()
        recipe = _make_recipe(flow_rate=8.3e-8)
        _g8_pressure_envelope_check(recipe, fmc=None, report=report)
        # No issues triggered.
        assert not any(
            i.code.startswith("FP_G8") for i in report.issues
        )

    def test_negative_flow_blocks(self) -> None:
        report = ValidationReport()
        recipe = _make_recipe(flow_rate=-1e-7)
        _g8_pressure_envelope_check(recipe, fmc=None, report=report)
        codes = [i.code for i in report.issues]
        assert "FP_G8_FLOW_RATE_NEGATIVE" in codes

    def test_negative_flow_severity_is_blocker(self) -> None:
        report = ValidationReport()
        recipe = _make_recipe(flow_rate=-1e-7)
        _g8_pressure_envelope_check(recipe, fmc=None, report=report)
        for issue in report.issues:
            if issue.code == "FP_G8_FLOW_RATE_NEGATIVE":
                assert issue.severity == ValidationSeverity.BLOCKER

    def test_extreme_flow_warns(self) -> None:
        # 1e-3 m³/s = 1 L/s = absurd for chromatography.
        report = ValidationReport()
        recipe = _make_recipe(flow_rate=1e-3)
        _g8_pressure_envelope_check(recipe, fmc=None, report=report)
        codes = [i.code for i in report.issues]
        assert "FP_G8_FLOW_RATE_EXTREME" in codes

    def test_extreme_flow_severity_is_warning(self) -> None:
        report = ValidationReport()
        recipe = _make_recipe(flow_rate=1e-3)
        _g8_pressure_envelope_check(recipe, fmc=None, report=report)
        for issue in report.issues:
            if issue.code == "FP_G8_FLOW_RATE_EXTREME":
                assert issue.severity == ValidationSeverity.WARNING


class TestG8MissingFlowRate:
    """G8 silently skips steps without a flow_rate (e.g. pack steps)."""

    def test_no_flow_rate_silent_skip(self) -> None:
        report = ValidationReport()
        recipe = ProcessRecipe(
            target=TargetProductProfile(),
            steps=[
                ProcessStep(
                    stage=LifecycleStage.M3_PERFORMANCE,
                    kind=ProcessStepKind.PACK_COLUMN,
                    name="pack",
                    parameters={},  # no flow_rate
                ),
            ],
        )
        _g8_pressure_envelope_check(recipe, fmc=None, report=report)
        assert not any(i.code.startswith("FP_G8") for i in report.issues)

    def test_invalid_flow_rate_silent_skip(self) -> None:
        # Non-coercible value → silent skip (don't fail the whole gate).
        report = ValidationReport()
        recipe = _make_recipe(flow_rate="not_a_number")
        _g8_pressure_envelope_check(recipe, fmc=None, report=report)
        assert not any(i.code.startswith("FP_G8") for i in report.issues)


class TestG8FmcOptional:
    """fmc=None is the v0.7 default; gate still runs."""

    def test_fmc_none_works(self) -> None:
        report = ValidationReport()
        recipe = _make_recipe(flow_rate=1e-7)
        _g8_pressure_envelope_check(recipe, fmc=None, report=report)
        # No errors — gate completes cleanly.
        assert isinstance(report, ValidationReport)
