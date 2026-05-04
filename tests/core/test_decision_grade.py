"""Tests for decision-grade gating policy (W-003 / B-1b, v0.6.4).

Reference: docs/update_workplan_2026-05-04.md §4 → B-1b.

The policy degrades render mode by one step per tier below the policy
floor: NUMBER → INTERVAL → RANK_BAND → SUPPRESS.
"""

from __future__ import annotations

import pytest

from dpsim.core.decision_grade import (
    DECISION_GRADE_POLICY,
    OutputType,
    RenderMode,
    decide_render_mode,
    policy_floor,
    render_value,
)
from dpsim.datatypes import ModelEvidenceTier


# ─── Policy table coverage ───────────────────────────────────────────────────


class TestPolicyCoverage:
    """Every OutputType must have a policy row, and policy_floor must work."""

    @pytest.mark.parametrize("output_type", list(OutputType))
    def test_every_output_type_has_a_policy_row(self, output_type):
        assert output_type in DECISION_GRADE_POLICY
        floor = DECISION_GRADE_POLICY[output_type]
        assert isinstance(floor, ModelEvidenceTier)

    @pytest.mark.parametrize("output_type", list(OutputType))
    def test_policy_floor_returns_same_value(self, output_type):
        assert policy_floor(output_type) == DECISION_GRADE_POLICY[output_type]


# ─── Decision ladder ─────────────────────────────────────────────────────────


class TestDecideRenderMode:
    """The 4-step ladder NUMBER → INTERVAL → RANK_BAND → SUPPRESS."""

    def test_at_floor_renders_number(self):
        # DBC requires VALIDATED_QUANTITATIVE → at floor.
        mode = decide_render_mode(
            OutputType.DBC, ModelEvidenceTier.VALIDATED_QUANTITATIVE
        )
        assert mode == RenderMode.NUMBER

    def test_above_floor_renders_number(self):
        # PRESSURE_DROP requires SEMI_QUANTITATIVE; CALIBRATED_LOCAL is stronger.
        mode = decide_render_mode(
            OutputType.PRESSURE_DROP, ModelEvidenceTier.CALIBRATED_LOCAL
        )
        assert mode == RenderMode.NUMBER

    def test_one_step_below_renders_interval(self):
        # DBC requires VALIDATED_QUANTITATIVE; CALIBRATED_LOCAL is one step below.
        mode = decide_render_mode(
            OutputType.DBC, ModelEvidenceTier.CALIBRATED_LOCAL
        )
        assert mode == RenderMode.INTERVAL

    def test_two_steps_below_renders_rank_band(self):
        # DBC requires VALIDATED_QUANTITATIVE; SEMI_QUANTITATIVE is two below.
        mode = decide_render_mode(
            OutputType.DBC, ModelEvidenceTier.SEMI_QUANTITATIVE
        )
        assert mode == RenderMode.RANK_BAND

    def test_three_steps_below_suppresses(self):
        # DBC requires VALIDATED_QUANTITATIVE; QUALITATIVE_TREND is three below.
        mode = decide_render_mode(
            OutputType.DBC, ModelEvidenceTier.QUALITATIVE_TREND
        )
        assert mode == RenderMode.SUPPRESS

    def test_unsupported_always_suppresses(self):
        # An UNSUPPORTED model never produces decision-grade output.
        for out in OutputType:
            mode = decide_render_mode(out, ModelEvidenceTier.UNSUPPORTED)
            # PRESSURE_DROP is the most lenient (floor SEMI_QUANTITATIVE);
            # UNSUPPORTED is two steps below SEMI → RANK_BAND. Every other
            # output should suppress.
            if out == OutputType.PRESSURE_DROP:
                assert mode == RenderMode.RANK_BAND
            else:
                assert mode == RenderMode.SUPPRESS


# ─── Render value formatting ─────────────────────────────────────────────────


class TestRenderValue:
    """End-to-end: numeric value + tier + output → formatted string + components."""

    def test_number_mode_produces_point_value(self):
        rv = render_value(
            42.31, OutputType.DBC, ModelEvidenceTier.VALIDATED_QUANTITATIVE,
            unit="mg/mL",
        )
        assert rv.mode == RenderMode.NUMBER
        assert rv.point == pytest.approx(42.31)
        assert "42.31" in rv.display
        assert "mg/mL" in rv.display
        assert rv.low is None and rv.high is None

    def test_interval_mode_produces_low_high(self):
        rv = render_value(
            42.0, OutputType.DBC, ModelEvidenceTier.CALIBRATED_LOCAL,
            unit="mg/mL", interval_rel=0.25,
        )
        assert rv.mode == RenderMode.INTERVAL
        assert rv.low == pytest.approx(42.0 * 0.75)
        assert rv.high == pytest.approx(42.0 * 1.25)
        assert "–" in rv.display  # en-dash separator

    def test_rank_band_with_reference_categorises(self):
        rv = render_value(
            10.0, OutputType.DBC, ModelEvidenceTier.SEMI_QUANTITATIVE,
            rank_reference=50.0,
        )
        # ratio 0.2 < 0.5 → LOW
        assert rv.mode == RenderMode.RANK_BAND
        assert rv.rank == "LOW"

    def test_rank_band_high_when_above_threshold(self):
        rv = render_value(
            100.0, OutputType.DBC, ModelEvidenceTier.SEMI_QUANTITATIVE,
            rank_reference=50.0,
        )
        # ratio 2.0 > 1.5 → HIGH
        assert rv.rank == "HIGH"

    def test_rank_band_no_reference_falls_back_to_reportable(self):
        rv = render_value(
            10.0, OutputType.DBC, ModelEvidenceTier.SEMI_QUANTITATIVE,
        )
        assert rv.mode == RenderMode.RANK_BAND
        assert rv.rank == "reportable"

    def test_suppress_mode_returns_placeholder(self):
        rv = render_value(
            42.0, OutputType.DBC, ModelEvidenceTier.QUALITATIVE_TREND,
        )
        assert rv.mode == RenderMode.SUPPRESS
        assert rv.point is None
        assert "decision-grade" in rv.display


# ─── Streamlit-reload safety (per CLAUDE.md v9.0 enum rule) ──────────────────


class TestReloadSafety:
    """Tier comparison must use .value, not identity, to survive Streamlit
    importlib.reload of dpsim.datatypes."""

    def test_decide_with_string_value_still_works(self):
        """A 'tier' object that exposes only .value must still resolve.

        Mimics the post-reload state where the imported enum class is a
        different Python object than the one in sys.modules.
        """
        class _AliasedTier:
            value = ModelEvidenceTier.SEMI_QUANTITATIVE.value

        mode = decide_render_mode(OutputType.PRESSURE_DROP, _AliasedTier())
        # PRESSURE_DROP floor is SEMI_QUANTITATIVE; aliased tier matches → NUMBER.
        assert mode == RenderMode.NUMBER

    def test_unknown_tier_value_treated_as_worst(self):
        class _UnknownTier:
            value = "nonexistent_tier_value"

        mode = decide_render_mode(OutputType.DBC, _UnknownTier())
        # Worst tier vs DBC's VALIDATED_QUANTITATIVE floor → SUPPRESS.
        assert mode == RenderMode.SUPPRESS
