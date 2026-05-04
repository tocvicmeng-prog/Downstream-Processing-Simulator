"""B-1b UI integration: tests for decision-grade Streamlit render helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from dpsim.core.decision_grade import OutputType, RenderMode
from dpsim.datatypes import ModelEvidenceTier
from dpsim.visualization.decision_grade_render import (
    caption_for_mode,
    format_decision_graded,
    gate_decision_for,
    render_metric,
)


# ─── Pure formatting ────────────────────────────────────────────────────────


class TestFormatDecisionGraded:
    def test_number_mode_at_floor(self):
        # PRESSURE_DROP floor is SEMI_QUANTITATIVE
        mode, display = format_decision_graded(
            value=42_000.0,  # 42 kPa in Pa
            output_type=OutputType.PRESSURE_DROP,
            tier=ModelEvidenceTier.SEMI_QUANTITATIVE,
            unit="kPa", scale=1.0 / 1000.0,
        )
        assert mode == RenderMode.NUMBER
        assert "42" in display
        assert "kPa" in display

    def test_interval_mode_one_below(self):
        # DBC floor is VALIDATED_QUANTITATIVE; CALIBRATED_LOCAL is one below
        mode, display = format_decision_graded(
            value=42.0,
            output_type=OutputType.DBC,
            tier=ModelEvidenceTier.CALIBRATED_LOCAL,
            unit="mg/mL",
        )
        assert mode == RenderMode.INTERVAL
        assert "–" in display

    def test_rank_band_two_below(self):
        mode, display = format_decision_graded(
            value=42.0,
            output_type=OutputType.DBC,
            tier=ModelEvidenceTier.SEMI_QUANTITATIVE,
            rank_reference=50.0,
        )
        assert mode == RenderMode.RANK_BAND
        # 42/50 = 0.84 → MEDIUM (between 0.5 and 1.5)
        assert "MEDIUM" in display

    def test_suppress_mode(self):
        mode, display = format_decision_graded(
            value=42.0,
            output_type=OutputType.DBC,
            tier=ModelEvidenceTier.QUALITATIVE_TREND,
        )
        assert mode == RenderMode.SUPPRESS
        assert "decision-grade" in display

    def test_scale_applied_before_format(self):
        """scale=1e6 should turn 0.0001 m into 100 (µm)."""
        mode, display = format_decision_graded(
            value=0.0001,
            output_type=OutputType.D32,
            tier=ModelEvidenceTier.CALIBRATED_LOCAL,
            unit="µm", scale=1e6,
        )
        assert mode == RenderMode.NUMBER
        assert "100" in display


# ─── Captions ────────────────────────────────────────────────────────────────


class TestCaptionForMode:
    def test_number_returns_empty(self):
        assert caption_for_mode(RenderMode.NUMBER) == ""

    @pytest.mark.parametrize("mode", [
        RenderMode.INTERVAL, RenderMode.RANK_BAND, RenderMode.SUPPRESS,
    ])
    def test_non_number_returns_explanation(self, mode):
        text = caption_for_mode(mode)
        assert text != ""
        assert len(text) > 20  # non-trivial explanation


# ─── Gate convenience ───────────────────────────────────────────────────────


class TestGateDecisionFor:
    def test_passes_through_to_decide_render_mode(self):
        # Same contract as core.decision_grade.decide_render_mode
        assert gate_decision_for(
            OutputType.PRESSURE_DROP, ModelEvidenceTier.SEMI_QUANTITATIVE
        ) == RenderMode.NUMBER
        assert gate_decision_for(
            OutputType.DBC, ModelEvidenceTier.QUALITATIVE_TREND
        ) == RenderMode.SUPPRESS


# ─── Streamlit st.metric wrapper ────────────────────────────────────────────


class TestRenderMetric:
    """Verify render_metric calls st.metric with the gate-formatted string."""

    def test_calls_st_metric_with_formatted_value(self):
        from dpsim.visualization import decision_grade_render as mod
        fake_metric = MagicMock()
        with patch.object(mod.st, "metric", fake_metric):
            render_metric(
                "Pressure",
                value=42_000.0,
                output_type=OutputType.PRESSURE_DROP,
                tier=ModelEvidenceTier.SEMI_QUANTITATIVE,
                unit="kPa", scale=1.0 / 1000.0,
            )
        assert fake_metric.called
        args, kwargs = fake_metric.call_args
        assert args[0] == "Pressure"
        # Second positional arg is the formatted display value.
        assert "42" in args[1]
        assert "kPa" in args[1]

    def test_help_includes_caption_when_degraded(self):
        from dpsim.visualization import decision_grade_render as mod
        fake_metric = MagicMock()
        with patch.object(mod.st, "metric", fake_metric):
            render_metric(
                "DBC",
                value=42.0,
                output_type=OutputType.DBC,
                tier=ModelEvidenceTier.CALIBRATED_LOCAL,  # one below → INTERVAL
                unit="mg/mL",
            )
        kwargs = fake_metric.call_args.kwargs
        help_text = kwargs.get("help") or ""
        assert "interval" in help_text.lower()

    def test_help_omits_caption_when_number_mode(self):
        from dpsim.visualization import decision_grade_render as mod
        fake_metric = MagicMock()
        with patch.object(mod.st, "metric", fake_metric):
            render_metric(
                "Pressure",
                value=42_000.0,
                output_type=OutputType.PRESSURE_DROP,
                tier=ModelEvidenceTier.VALIDATED_QUANTITATIVE,  # at/above floor
                unit="kPa", scale=1.0 / 1000.0,
            )
        # No degradation → help should be None (or empty), not a caption.
        kwargs = fake_metric.call_args.kwargs
        help_text = kwargs.get("help")
        assert not help_text  # None or ""

    def test_user_help_concatenated_with_caption(self):
        from dpsim.visualization import decision_grade_render as mod
        fake_metric = MagicMock()
        with patch.object(mod.st, "metric", fake_metric):
            render_metric(
                "DBC",
                value=42.0,
                output_type=OutputType.DBC,
                tier=ModelEvidenceTier.CALIBRATED_LOCAL,  # → INTERVAL
                unit="mg/mL",
                help="Dynamic binding capacity at 10% breakthrough.",
            )
        help_text = fake_metric.call_args.kwargs.get("help") or ""
        assert "Dynamic binding capacity" in help_text
        assert "interval" in help_text.lower()


# ─── tab_m3.py reference site smoke ─────────────────────────────────────────


def test_tab_m3_imports_with_render_metric():
    """The tab module must import cleanly post-B-1b reference-site wiring."""
    from dpsim.visualization.tabs import tab_m3  # noqa: F401
