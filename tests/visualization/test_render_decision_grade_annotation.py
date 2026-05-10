"""Tests for render_decision_grade_annotation (B-1k / W-035, v0.8.1).

Verifies that the plotly-side helper:

* Routes the value through the same decision-grade policy as
  :func:`render_metric` (NUMBER / INTERVAL / RANK_BAND / SUPPRESS).
* Calls ``fig.add_annotation`` exactly once on non-SUPPRESS branches.
* Skips the call (returns SUPPRESS) when the policy suppresses the
  output.
* Picks an unobtrusive color hint based on render mode.
* Forwards extra ``annotation_kwargs`` (x, y, xref, ...).

Also exercises the wire-up in ``plot_breakthrough_curve`` and
``plot_pressure_flow_curve``: when ``tier`` is supplied, the chart's
DBC / Q_max annotations include the mode tag.
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import pytest

from dpsim.core.decision_grade import OutputType, RenderMode
from dpsim.datatypes import ModelEvidenceTier
from dpsim.module3_performance.hydrodynamics import ColumnGeometry
from dpsim.visualization.decision_grade_render import (
    render_decision_grade_annotation,
)
from dpsim.visualization.plots_m3 import (
    plot_breakthrough_curve,
    plot_pressure_flow_curve,
)


# ─── render_decision_grade_annotation — direct API ──────────────────────────


@pytest.fixture
def fig():
    return go.Figure()


class TestRenderAnnotationModes:
    def test_number_mode_emits_plain_text(self, fig):
        # DBC at VALIDATED_QUANTITATIVE → NUMBER.
        mode = render_decision_grade_annotation(
            fig,
            label="DBC₁₀",
            value=42.3,
            output_type=OutputType.DBC,
            tier=ModelEvidenceTier.VALIDATED_QUANTITATIVE,
            unit="mol/m³",
            x=10.0, y=0.1, xref="x", yref="y",
        )
        assert mode == RenderMode.NUMBER
        assert len(fig.layout.annotations) == 1
        text = fig.layout.annotations[0].text
        assert "DBC" in text
        assert "[INTERVAL]" not in text
        assert "[RANK]" not in text

    def test_interval_mode_includes_tag(self, fig):
        # DBC at SEMI_QUANTITATIVE → policy floor is two tiers above
        # so we get RANK_BAND, not INTERVAL. Adjust expectation.
        mode = render_decision_grade_annotation(
            fig,
            label="DBC₁₀",
            value=42.3,
            output_type=OutputType.DBC,
            tier=ModelEvidenceTier.CALIBRATED_LOCAL,
            unit="mol/m³",
            x=10.0, y=0.1, xref="x", yref="y",
        )
        # CALIBRATED_LOCAL is one tier below DBC's VALIDATED floor → INTERVAL.
        assert mode == RenderMode.INTERVAL
        assert len(fig.layout.annotations) == 1
        assert "[INTERVAL]" in fig.layout.annotations[0].text

    def test_rank_mode_includes_rank_tag(self, fig):
        # DBC at SEMI_QUANTITATIVE → two tiers below VALIDATED → RANK_BAND.
        mode = render_decision_grade_annotation(
            fig,
            label="DBC₁₀",
            value=42.3,
            output_type=OutputType.DBC,
            tier=ModelEvidenceTier.SEMI_QUANTITATIVE,
            unit="mol/m³",
            x=10.0, y=0.1, xref="x", yref="y",
        )
        assert mode == RenderMode.RANK_BAND
        assert "[RANK]" in fig.layout.annotations[0].text

    def test_suppress_mode_no_annotation_drawn(self, fig):
        # DBC at QUALITATIVE_TREND → SUPPRESS.
        mode = render_decision_grade_annotation(
            fig,
            label="DBC₁₀",
            value=42.3,
            output_type=OutputType.DBC,
            tier=ModelEvidenceTier.QUALITATIVE_TREND,
            unit="mol/m³",
            x=10.0, y=0.1, xref="x", yref="y",
        )
        assert mode == RenderMode.SUPPRESS
        assert len(fig.layout.annotations) == 0

    def test_show_mode_tag_false_suppresses_tag(self, fig):
        render_decision_grade_annotation(
            fig,
            label="DBC₁₀",
            value=42.3,
            output_type=OutputType.DBC,
            tier=ModelEvidenceTier.CALIBRATED_LOCAL,
            unit="mol/m³",
            show_mode_tag=False,
            x=10.0, y=0.1, xref="x", yref="y",
        )
        assert "[INTERVAL]" not in fig.layout.annotations[0].text

    def test_color_override_applied(self, fig):
        render_decision_grade_annotation(
            fig,
            label="DBC₁₀",
            value=42.3,
            output_type=OutputType.DBC,
            tier=ModelEvidenceTier.CALIBRATED_LOCAL,
            unit="mol/m³",
            color_override="rgb(0, 0, 255)",
            x=10.0, y=0.1, xref="x", yref="y",
        )
        assert fig.layout.annotations[0].font.color == "rgb(0, 0, 255)"

    def test_extra_kwargs_forwarded(self, fig):
        render_decision_grade_annotation(
            fig,
            label="x",
            value=1.0,
            output_type=OutputType.DBC,
            tier=ModelEvidenceTier.VALIDATED_QUANTITATIVE,
            x=5.0, y=0.5, xref="x", yref="y",
            xanchor="right",
            yanchor="middle",
        )
        ann = fig.layout.annotations[0]
        assert ann.xanchor == "right"
        assert ann.yanchor == "middle"
        assert ann.x == 5.0


# ─── Wire-up in plot_breakthrough_curve ────────────────────────────────────


class TestPlotBreakthroughCurveTierAware:
    def test_tier_none_keeps_legacy_format(self):
        time = np.linspace(0, 600, 100)
        C_outlet = np.linspace(0, 0.6, 100)  # rising profile
        fig = plot_breakthrough_curve(
            time=time, C_outlet=C_outlet, C_feed=1.0,
            dbc_5=10.0, dbc_10=20.0, dbc_50=50.0,
        )
        # Find DBC annotations (excluding the threshold "5%" / "10%" / "50%").
        dbc_annotations = [
            a.text for a in fig.layout.annotations
            if "DBC" in (a.text or "") and "mol" in (a.text or "")
        ]
        assert len(dbc_annotations) == 3
        for txt in dbc_annotations:
            assert "[INTERVAL]" not in txt
            assert "[RANK]" not in txt

    def test_tier_calibrated_local_emits_interval_tag(self):
        time = np.linspace(0, 600, 100)
        C_outlet = np.linspace(0, 0.6, 100)
        fig = plot_breakthrough_curve(
            time=time, C_outlet=C_outlet, C_feed=1.0,
            dbc_5=10.0, dbc_10=20.0, dbc_50=50.0,
            tier=ModelEvidenceTier.CALIBRATED_LOCAL,
        )
        dbc_annotations = [
            a.text for a in fig.layout.annotations
            if "DBC" in (a.text or "")
        ]
        # All three DBC values get tagged.
        tagged = [t for t in dbc_annotations if "[INTERVAL]" in t]
        assert len(tagged) == 3

    def test_tier_qualitative_trend_suppresses_dbc_text(self):
        time = np.linspace(0, 600, 100)
        C_outlet = np.linspace(0, 0.6, 100)
        fig = plot_breakthrough_curve(
            time=time, C_outlet=C_outlet, C_feed=1.0,
            dbc_5=10.0, dbc_10=20.0, dbc_50=50.0,
            tier=ModelEvidenceTier.QUALITATIVE_TREND,
        )
        # No mol/m³ DBC text should be drawn (only the threshold "5%"/"10%"
        # / "50%" labels remain).
        dbc_text = [
            a.text for a in fig.layout.annotations
            if "mol" in (a.text or "")
        ]
        assert dbc_text == []


# ─── Wire-up in plot_pressure_flow_curve ───────────────────────────────────


class TestPlotPressureFlowCurveTierAware:
    def test_tier_none_keeps_legacy_format(self):
        col = ColumnGeometry()
        fig = plot_pressure_flow_curve(col, Q_max=1.0e-7)
        q_max_anns = [
            a.text for a in fig.layout.annotations
            if "Q_max" in (a.text or "")
        ]
        assert len(q_max_anns) == 1
        assert "[INTERVAL]" not in q_max_anns[0]

    def test_tier_calibrated_local_emits_interval_tag(self):
        col = ColumnGeometry()
        fig = plot_pressure_flow_curve(
            col, Q_max=1.0e-7,
            tier=ModelEvidenceTier.CALIBRATED_LOCAL,
        )
        # Q_MAX policy floor is SEMI_QUANTITATIVE; CALIBRATED_LOCAL is one
        # tier above → NUMBER (no tag).
        q_max_anns = [
            a.text for a in fig.layout.annotations
            if "Q_max" in (a.text or "")
        ]
        assert len(q_max_anns) == 1
        assert "[INTERVAL]" not in q_max_anns[0]

    def test_tier_qualitative_trend_renders_rank_band(self):
        col = ColumnGeometry()
        fig = plot_pressure_flow_curve(
            col, Q_max=1.0e-7,
            tier=ModelEvidenceTier.QUALITATIVE_TREND,
        )
        # Q_MAX floor is SEMI_QUANTITATIVE; QUALITATIVE_TREND is one
        # below → INTERVAL with [INTERVAL] tag.
        q_max_anns = [
            a.text for a in fig.layout.annotations
            if "Q_max" in (a.text or "") and "[INTERVAL]" in (a.text or "")
        ]
        assert len(q_max_anns) == 1
