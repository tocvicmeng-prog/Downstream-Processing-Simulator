"""Tests for C2 — ModelMode-conditional manifest gating in M3.

Reference: docs/handover/V0_3_0_FAMILY_COVERAGE_HANDOVER.md §10 (v0.4.0 C2).
Closes architect-coherence-audit Deficit 2 for the M3 stage.
"""

from __future__ import annotations


from dpsim.datatypes import ModelEvidenceTier, ModelManifest
from dpsim.module3_performance.method import (
    _apply_mode_guard,
    _read_model_mode,
)


def _semi_manifest() -> ModelManifest:
    return ModelManifest(
        model_name="M3.method.test",
        evidence_tier=ModelEvidenceTier.SEMI_QUANTITATIVE,
        valid_domain={},
        calibration_ref="",
        assumptions=[],
        diagnostics={},
    )


def _calibrated_manifest() -> ModelManifest:
    return ModelManifest(
        model_name="M3.method.test",
        evidence_tier=ModelEvidenceTier.CALIBRATED_LOCAL,
        valid_domain={},
        calibration_ref="study_X",
        assumptions=[],
        diagnostics={},
    )


# ─── _read_model_mode ────────────────────────────────────────────────────────


class TestReadModelMode:
    def test_dict_returns_value(self):
        assert _read_model_mode({"model_mode": "empirical_engineering"}) == "empirical_engineering"

    def test_dict_missing_returns_empty(self):
        assert _read_model_mode({}) == ""

    def test_none_returns_empty(self):
        assert _read_model_mode(None) == ""

    def test_object_attribute_works(self):
        class _PS:
            model_mode = "mechanistic_research"
        assert _read_model_mode(_PS()) == "mechanistic_research"

    def test_normalises_case_and_whitespace(self):
        assert _read_model_mode({"model_mode": "  HYBRID_COUPLED "}) == "hybrid_coupled"


# ─── hybrid_coupled (default) — no change ────────────────────────────────────


class TestHybridCoupledNoChange:
    def test_hybrid_uncalibrated_no_change(self):
        manifest = _semi_manifest()
        out = _apply_mode_guard(
            manifest, {"model_mode": "hybrid_coupled"}, has_calibration=False
        )
        assert out.evidence_tier == ModelEvidenceTier.SEMI_QUANTITATIVE
        assert out.assumptions == []
        assert "mode_guard_empirical_uncalibrated" not in out.diagnostics
        assert "exploratory_only" not in out.diagnostics

    def test_no_mode_no_change(self):
        manifest = _semi_manifest()
        out = _apply_mode_guard(manifest, {}, has_calibration=False)
        assert out.evidence_tier == ModelEvidenceTier.SEMI_QUANTITATIVE


# ─── empirical_engineering ──────────────────────────────────────────────────


class TestEmpiricalEngineeringMode:
    def test_uncalibrated_caps_at_qualitative(self):
        manifest = _semi_manifest()
        out = _apply_mode_guard(
            manifest,
            {"model_mode": "empirical_engineering"},
            has_calibration=False,
        )
        assert out.evidence_tier == ModelEvidenceTier.QUALITATIVE_TREND
        assert out.diagnostics.get("mode_guard_empirical_uncalibrated") is True
        assert any("empirical_engineering" in a for a in out.assumptions)

    def test_calibrated_no_cap(self):
        """When the FMC is calibrated, empirical mode does NOT cap the tier."""
        manifest = _calibrated_manifest()
        out = _apply_mode_guard(
            manifest,
            {"model_mode": "empirical_engineering"},
            has_calibration=True,
        )
        assert out.evidence_tier == ModelEvidenceTier.CALIBRATED_LOCAL
        assert "mode_guard_empirical_uncalibrated" not in out.diagnostics


# ─── mechanistic_research — always exploratory ──────────────────────────────


class TestMechanisticResearchMode:
    def test_uncalibrated_tagged_exploratory(self):
        manifest = _semi_manifest()
        out = _apply_mode_guard(
            manifest,
            {"model_mode": "mechanistic_research"},
            has_calibration=False,
        )
        assert out.diagnostics.get("exploratory_only") is True
        assert out.diagnostics.get("mode_guard_mechanistic") is True
        # Mechanistic mode tags the result as exploratory but does NOT
        # downgrade the tier — the exploratory flag is the actionable
        # signal; the tier still reflects the underlying calibration state.
        assert out.evidence_tier == ModelEvidenceTier.SEMI_QUANTITATIVE
        assert any("mechanistic" in a.lower() for a in out.assumptions)

    def test_calibrated_still_exploratory(self):
        """Mechanistic mode is exploratory regardless of calibration state."""
        manifest = _calibrated_manifest()
        out = _apply_mode_guard(
            manifest,
            {"model_mode": "mechanistic_research"},
            has_calibration=True,
        )
        # Tier stays at calibrated_local (don't downgrade), but the
        # exploratory_only diagnostic flag and assumption are added.
        assert out.evidence_tier == ModelEvidenceTier.CALIBRATED_LOCAL
        assert out.diagnostics.get("exploratory_only") is True
        assert any("mechanistic" in a.lower() for a in out.assumptions)
