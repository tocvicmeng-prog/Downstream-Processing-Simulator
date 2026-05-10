"""Tests for M1 plot tier-gating extension (B-1ℓ / W-037, v0.8.2).

Verifies that ``plot_droplet_size_distribution`` carries the tier= kwarg
and routes d32 / d50 annotations through render_decision_grade_annotation
when tier is supplied. tier=None preserves legacy formatting.
"""

from __future__ import annotations

import numpy as np
import pytest

from dpsim.datatypes import EmulsificationResult, ModelEvidenceTier
from dpsim.visualization.plots import plot_droplet_size_distribution


@pytest.fixture
def small_result():
    """Minimal EmulsificationResult for plotting tests."""
    return EmulsificationResult(
        d_bins=np.array([1e-6, 5e-6, 10e-6, 50e-6, 100e-6]),
        n_d=np.array([1.0, 2.0, 3.0, 2.0, 1.0]),
        d32=10.0e-6,
        d43=12.0e-6,
        d10=2.0e-6,
        d50=8.0e-6,
        d90=50.0e-6,
        span=2.0,
        total_volume_fraction=0.05,
        converged=True,
    )


class TestM1PlotTierAware:
    def test_tier_none_keeps_legacy_format(self, small_result):
        fig = plot_droplet_size_distribution(small_result)
        anns = [a.text for a in fig.layout.annotations]
        assert any("d32=" in t for t in anns)
        assert any("d50=" in t for t in anns)
        # Legacy text never carries [INTERVAL] or [RANK] tags.
        for t in anns:
            assert "[INTERVAL]" not in t
            assert "[RANK]" not in t

    def test_tier_validated_quantitative_renders_number(self, small_result):
        # D32 floor is CALIBRATED_LOCAL → VALIDATED_QUANTITATIVE is one
        # tier above the floor → NUMBER mode.
        fig = plot_droplet_size_distribution(
            small_result, tier=ModelEvidenceTier.VALIDATED_QUANTITATIVE,
        )
        anns = [a.text for a in fig.layout.annotations]
        d32_anns = [t for t in anns if "d32" in t]
        assert len(d32_anns) >= 1
        assert "[INTERVAL]" not in d32_anns[0]

    def test_tier_semi_quantitative_emits_interval(self, small_result):
        # D32 floor is CALIBRATED_LOCAL → SEMI_QUANTITATIVE is one
        # tier below → INTERVAL with [INTERVAL] tag.
        fig = plot_droplet_size_distribution(
            small_result, tier=ModelEvidenceTier.SEMI_QUANTITATIVE,
        )
        anns = [a.text for a in fig.layout.annotations]
        tagged = [t for t in anns if "[INTERVAL]" in t]
        # Both d32 and d50 get tagged.
        assert len(tagged) == 2

    def test_tier_unsupported_suppresses_value_text(self, small_result):
        # D32 floor is CALIBRATED_LOCAL → UNSUPPORTED is multi-tier
        # below → SUPPRESS.
        fig = plot_droplet_size_distribution(
            small_result, tier=ModelEvidenceTier.UNSUPPORTED,
        )
        anns = [a.text for a in fig.layout.annotations]
        # No d32 / d50 numeric annotations should remain.
        d_anns = [t for t in anns if "d32=" in t or "d50=" in t]
        assert d_anns == []
