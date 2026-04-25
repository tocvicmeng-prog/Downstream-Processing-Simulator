"""Tests for C7 — family-aware Protein A scope-of-claim guard.

Reference: docs/handover/V0_3_0_FAMILY_COVERAGE_HANDOVER.md §10.

Closes architect-coherence-audit D6 + scientific-advisor §4 leak: the M3
Protein A defaults are calibrated for agarose+chitosan substrate and were
silently used regardless of upstream polymer family. v0.4.0 caps the manifest
tier at QUALITATIVE_TREND for non-A+C families when no calibration is loaded
and emits an explicit scope-of-claim warning.
"""

from __future__ import annotations

from dataclasses import dataclass


from dpsim.datatypes import ModelEvidenceTier, ModelManifest
from dpsim.module3_performance.method import (
    _cap_manifest_for_non_ac_family,
    _protein_a_family_warning,
)


# ─── _protein_a_family_warning ───────────────────────────────────────────────


class TestFamilyWarning:
    def test_no_family_returns_empty(self):
        assert _protein_a_family_warning(None) == ""
        assert _protein_a_family_warning({}) == ""

    def test_agarose_chitosan_returns_empty(self):
        assert _protein_a_family_warning({"polymer_family": "agarose_chitosan"}) == ""

    def test_alginate_returns_warning(self):
        warning = _protein_a_family_warning({"polymer_family": "alginate"})
        assert "alginate" in warning
        assert "agarose+chitosan" in warning

    def test_cellulose_returns_warning(self):
        warning = _protein_a_family_warning({"polymer_family": "cellulose"})
        assert "cellulose" in warning
        assert "calibrated" in warning.lower()

    def test_plga_returns_warning(self):
        warning = _protein_a_family_warning({"polymer_family": "plga"})
        assert "plga" in warning

    def test_fallback_to_fmc(self):
        @dataclass
        class _MockFMC:
            polymer_family: str = "alginate"

        warning = _protein_a_family_warning({}, fmc=_MockFMC())
        assert "alginate" in warning


# ─── _cap_manifest_for_non_ac_family ─────────────────────────────────────────


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
        calibration_ref="study_X_2026",
        assumptions=[],
        diagnostics={},
    )


def _qualitative_manifest() -> ModelManifest:
    return ModelManifest(
        model_name="M3.method.test",
        evidence_tier=ModelEvidenceTier.QUALITATIVE_TREND,
        valid_domain={},
        calibration_ref="",
        assumptions=[],
        diagnostics={},
    )


class TestCapManifest:
    def test_semi_quantitative_capped_at_qualitative(self):
        original = _semi_manifest()
        capped = _cap_manifest_for_non_ac_family(original, "warning text")
        assert capped.evidence_tier == ModelEvidenceTier.QUALITATIVE_TREND

    def test_already_qualitative_unchanged_tier(self):
        original = _qualitative_manifest()
        capped = _cap_manifest_for_non_ac_family(original, "warning text")
        assert capped.evidence_tier == ModelEvidenceTier.QUALITATIVE_TREND

    def test_calibrated_local_not_downgraded(self):
        original = _calibrated_manifest()
        capped = _cap_manifest_for_non_ac_family(original, "warning text")
        # Calibrated for this family → trust the calibration; no downgrade.
        assert capped.evidence_tier == ModelEvidenceTier.CALIBRATED_LOCAL

    def test_validated_quantitative_not_downgraded(self):
        original = ModelManifest(
            model_name="M3.method.test",
            evidence_tier=ModelEvidenceTier.VALIDATED_QUANTITATIVE,
            valid_domain={},
            calibration_ref="external_reference",
            assumptions=[],
            diagnostics={},
        )
        capped = _cap_manifest_for_non_ac_family(original, "warning text")
        assert capped.evidence_tier == ModelEvidenceTier.VALIDATED_QUANTITATIVE

    def test_diagnostic_flag_set(self):
        original = _semi_manifest()
        capped = _cap_manifest_for_non_ac_family(original, "warning text")
        assert capped.diagnostics.get("non_ac_family_cap_applied") is True

    def test_warning_recorded_in_assumptions(self):
        original = _semi_manifest()
        capped = _cap_manifest_for_non_ac_family(original, "warning text")
        assert any("non-A+C family" in a for a in capped.assumptions)
