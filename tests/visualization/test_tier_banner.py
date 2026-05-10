"""Tests for the top-of-page tier banner (B-1r / W-058, v0.8.4)."""

from __future__ import annotations

from typing import Any

from dpsim.datatypes import ModelEvidenceTier
from dpsim.visualization.shell.tier_banner import render_tier_banner


class _StubContainer:
    def __init__(self) -> None:
        self.successes: list[str] = []
        self.warnings: list[str] = []
        self.errors: list[str] = []
        self.infos: list[str] = []
        # W-090 (v0.8.8): tier-promotion hint surfaced as a caption.
        self.captions: list[str] = []

    def success(self, t: str) -> None:
        self.successes.append(t)

    def warning(self, t: str) -> None:
        self.warnings.append(t)

    def error(self, t: str) -> None:
        self.errors.append(t)

    def info(self, t: str) -> None:
        self.infos.append(t)

    def caption(self, t: str) -> None:
        self.captions.append(t)


class TestDefaultPath:
    def test_no_tier_renders_default_info_banner(self):
        c = _StubContainer()
        render_tier_banner(container=c, weakest_tier=None, has_calibration=False)
        assert len(c.infos) == 1
        assert "SEMI_QUANTITATIVE" in c.infos[0]
        assert "validated" in c.infos[0].lower()


class TestStrongTierPaths:
    def test_validated_with_calibration_green(self):
        c = _StubContainer()
        render_tier_banner(
            container=c,
            weakest_tier=ModelEvidenceTier.VALIDATED_QUANTITATIVE,
            has_calibration=True,
        )
        assert len(c.successes) == 1
        assert "VALIDATED_QUANTITATIVE" in c.successes[0]

    def test_calibrated_local_with_calibration_green(self):
        c = _StubContainer()
        render_tier_banner(
            container=c,
            weakest_tier=ModelEvidenceTier.CALIBRATED_LOCAL,
            has_calibration=True,
        )
        assert len(c.successes) == 1

    def test_strong_tier_without_calibration_amber(self):
        c = _StubContainer()
        render_tier_banner(
            container=c,
            weakest_tier=ModelEvidenceTier.VALIDATED_QUANTITATIVE,
            has_calibration=False,
        )
        # When the user hasn't loaded calibration, even a strong tier
        # should warn rather than celebrate.
        assert len(c.warnings) == 1


class TestSemiQuantitativeBand:
    def test_semi_quantitative_renders_info_banner(self):
        c = _StubContainer()
        render_tier_banner(
            container=c,
            weakest_tier=ModelEvidenceTier.SEMI_QUANTITATIVE,
            has_calibration=False,
        )
        assert len(c.infos) == 1
        assert "SEMI_QUANTITATIVE" in c.infos[0]


class TestWeakTierPaths:
    def test_qualitative_trend_red_banner(self):
        c = _StubContainer()
        render_tier_banner(
            container=c,
            weakest_tier=ModelEvidenceTier.QUALITATIVE_TREND,
            has_calibration=False,
        )
        assert len(c.errors) == 1
        assert "QUALITATIVE_TREND" in c.errors[0]

    def test_unsupported_red_banner(self):
        c = _StubContainer()
        render_tier_banner(
            container=c,
            weakest_tier=ModelEvidenceTier.UNSUPPORTED,
            has_calibration=False,
        )
        assert len(c.errors) == 1
