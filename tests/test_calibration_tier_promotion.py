"""Tests for C3 — typed-enum tier promotion through CalibrationStore.apply_to_fmc.

Reference: docs/handover/V0_3_0_FAMILY_COVERAGE_HANDOVER.md §10 (v0.4.0 C3 protocol).
Closes architect-coherence-audit D3 finding: calibration tier was previously
propagated only through the string side-channel ``confidence_tier``;
``model_manifest.evidence_tier`` (the typed enum used by
``_build_m3_chrom_manifest``) was never promoted.
"""

from __future__ import annotations

from dataclasses import dataclass


from dpsim.calibration.calibration_data import CalibrationEntry
from dpsim.calibration.calibration_store import CalibrationStore
from dpsim.datatypes import ModelEvidenceTier, ModelManifest


@dataclass
class _MinimalFMC:
    """Minimal FMC shape exposing only what apply_to_fmc reads."""

    estimated_q_max: float = 60.0
    functional_ligand_density: float = 5.0
    activity_retention: float = 0.85
    ligand_leaching_fraction: float = 0.0
    free_protein_wash_fraction: float = 0.0
    charge_density: float = 0.0
    total_coupled_density: float = 6.0
    capacity_area_basis: str = "reagent_accessible"
    ligand_accessible_area_per_bed_volume: float = 500.0
    reagent_accessible_area_per_bed_volume: float = 1000.0
    q_max_confidence: str = "mapped_estimated"
    # v0.5.0 (D2): confidence_tier removed; the model_manifest.evidence_tier
    # typed enum is the single source of truth.
    model_manifest: ModelManifest | None = None


def _semi_fmc(*, calibration_ref: str = "") -> _MinimalFMC:
    return _MinimalFMC(
        model_manifest=ModelManifest(
            model_name="M2.FunctionalMedia",
            evidence_tier=ModelEvidenceTier.SEMI_QUANTITATIVE,
            valid_domain={},
            calibration_ref=calibration_ref,
            assumptions=["Pre-calibration FMC."],
            diagnostics={},
        )
    )


def _calibrated_fmc() -> _MinimalFMC:
    return _MinimalFMC(
        model_manifest=ModelManifest(
            model_name="M2.FunctionalMedia",
            evidence_tier=ModelEvidenceTier.CALIBRATED_LOCAL,
            valid_domain={},
            calibration_ref="prior_calibration",
            assumptions=[],
            diagnostics={},
        )
    )


def _store_with_qmax_entry(measured_value: float = 80.0, source: str = "study_X_2026") -> CalibrationStore:
    store = CalibrationStore()
    store.add(
        CalibrationEntry(
            profile_key="protein_a_coupling",
            parameter_name="estimated_q_max",
            measured_value=measured_value,
            units="mol/m3",
            confidence="high",
            source_reference=source,
        )
    )
    return store


# ─── Promotion behaviour ─────────────────────────────────────────────────────


class TestApplyToFmcPromotesTier:
    def test_semi_quantitative_promotes_to_calibrated_local(self):
        fmc = _semi_fmc()
        store = _store_with_qmax_entry()
        out, overrides = store.apply_to_fmc(fmc)
        assert overrides, "expected at least one override applied"
        assert out.model_manifest is not None
        assert out.model_manifest.evidence_tier == ModelEvidenceTier.CALIBRATED_LOCAL

    def test_calibration_ref_propagates(self):
        fmc = _semi_fmc()
        store = _store_with_qmax_entry(source="study_X_2026")
        out, _ = store.apply_to_fmc(fmc)
        assert "study_X_2026" in (out.model_manifest.calibration_ref or "")

    def test_legacy_string_field_removed(self):
        """v0.5.0 (D2): the confidence_tier string side-channel is gone."""
        fmc = _semi_fmc()
        store = _store_with_qmax_entry()
        out, _ = store.apply_to_fmc(fmc)
        # FMC mock no longer carries the field; the typed enum is authoritative.
        assert not hasattr(out, "confidence_tier")

    def test_assumption_records_promotion(self):
        fmc = _semi_fmc()
        store = _store_with_qmax_entry()
        out, _ = store.apply_to_fmc(fmc)
        assert any(
            "promoted" in a.lower() and "calibration" in a.lower()
            for a in out.model_manifest.assumptions
        )

    def test_no_overrides_means_no_promotion(self):
        """When no calibration entries match, the manifest tier is untouched."""
        fmc = _semi_fmc()
        store = CalibrationStore()  # empty
        out, overrides = store.apply_to_fmc(fmc)
        assert overrides == []
        assert out.model_manifest.evidence_tier == ModelEvidenceTier.SEMI_QUANTITATIVE


# ─── Never-downgrade invariant ───────────────────────────────────────────────


class TestNeverDowngrade:
    def test_already_calibrated_fmc_not_downgraded(self):
        fmc = _calibrated_fmc()
        store = _store_with_qmax_entry()
        out, _ = store.apply_to_fmc(fmc)
        # Already CALIBRATED_LOCAL — must not be promoted-then-replaced
        # (we only promote when current tier is WEAKER than CALIBRATED_LOCAL).
        assert out.model_manifest.evidence_tier == ModelEvidenceTier.CALIBRATED_LOCAL

    def test_validated_quantitative_not_downgraded(self):
        fmc = _MinimalFMC(
            model_manifest=ModelManifest(
                model_name="M2.FunctionalMedia",
                evidence_tier=ModelEvidenceTier.VALIDATED_QUANTITATIVE,
                valid_domain={},
                calibration_ref="external_reference_method",
                assumptions=[],
                diagnostics={},
            )
        )
        store = _store_with_qmax_entry()
        out, _ = store.apply_to_fmc(fmc)
        assert out.model_manifest.evidence_tier == ModelEvidenceTier.VALIDATED_QUANTITATIVE
