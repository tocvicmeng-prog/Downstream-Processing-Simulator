"""Tests for plots_m2 tier-gating extension (B-1q / W-056, v0.8.4)."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from dpsim.datatypes import ModelEvidenceTier
from dpsim.visualization.plots_m2 import plot_surface_area_comparison


@dataclass
class _SurfaceModel:
    """Minimal stub mimicking AccessibleSurfaceModel's read interface."""

    external_area: float = 1.0e-9
    internal_geometric_area: float = 5.0e-9
    reagent_accessible_area: float = 4.0e-9
    ligand_accessible_area: float = 3.0e-9

    @dataclass
    class _Tier:
        value: str = "calibrated_local"

    tier: "_SurfaceModel._Tier" = None  # type: ignore[assignment]
    trust_level: str = "GREEN"

    def __post_init__(self) -> None:
        if self.tier is None:
            self.tier = _SurfaceModel._Tier()


@pytest.fixture
def surface_model():
    return _SurfaceModel()


class TestLegacyPath:
    def test_tier_none_keeps_legacy_trust_badge(self, surface_model):
        fig = plot_surface_area_comparison(surface_model, tier=None)
        assert fig is not None
        anns = [a.text for a in fig.layout.annotations]
        # Legacy "Trust:" badge present, no [INTERVAL]/[RANK] tags.
        assert any("Trust" in t for t in anns)
        for t in anns:
            assert "[INTERVAL]" not in t
            assert "[RANK]" not in t


class TestTierGatedPath:
    def test_validated_quantitative_renders_number(self, surface_model):
        fig = plot_surface_area_comparison(
            surface_model, tier=ModelEvidenceTier.VALIDATED_QUANTITATIVE,
        )
        assert fig is not None
        anns = [a.text for a in fig.layout.annotations]
        # No legacy "Trust:" string under the tier-aware path.
        assert all("Trust:" not in t for t in anns)
        assert any("Accessible area" in t for t in anns)

    def test_semi_quantitative_emits_interval(self, surface_model):
        # MODULUS floor is CALIBRATED_LOCAL → SEMI_QUANTITATIVE → INTERVAL.
        fig = plot_surface_area_comparison(
            surface_model, tier=ModelEvidenceTier.SEMI_QUANTITATIVE,
        )
        anns = [a.text for a in fig.layout.annotations]
        tagged = [t for t in anns if "[INTERVAL]" in t]
        assert len(tagged) == 1

    def test_unsupported_suppresses(self, surface_model):
        fig = plot_surface_area_comparison(
            surface_model, tier=ModelEvidenceTier.UNSUPPORTED,
        )
        anns = [a.text for a in fig.layout.annotations]
        # MODULUS at UNSUPPORTED → SUPPRESS → no annotation drawn.
        assert all("Accessible area" not in t for t in anns)


class TestNoneSurface:
    def test_none_surface_returns_none(self):
        assert plot_surface_area_comparison(None, tier=None) is None
