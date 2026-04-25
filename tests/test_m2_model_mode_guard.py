"""Tests for D5 — M2 ModelMode enforcement.

Reference: docs/handover/V0_4_0_ARCHITECTURAL_COHERENCE_HANDOVER.md §11.
Closes architect-coherence-audit Deficit 2 for the M2 stage. Mirrors C2 (M3
mode guard) so M2 FMC manifests receive the same mode-conditional gating.
"""

from __future__ import annotations

from dataclasses import replace


from dpsim.core.process_recipe import default_affinity_media_recipe
from dpsim.datatypes import ModelEvidenceTier, ModelMode
from dpsim.lifecycle import DownstreamProcessOrchestrator


def _run_with_mode(mode: ModelMode):
    """Run the default lifecycle with the given ModelMode and return the FMC."""
    from dpsim.config import load_config
    from pathlib import Path

    params = load_config(Path("configs/fast_smoke.toml"))
    # Override model_mode while keeping everything else identical.
    params = replace(params, model_mode=mode)

    recipe = default_affinity_media_recipe()
    orch = DownstreamProcessOrchestrator()
    return orch.run(recipe=recipe, params=params, propagate_dsd=False)


class TestM2ModelModeGuard:
    def test_hybrid_coupled_default_no_mode_flags(self):
        """HYBRID_COUPLED is the canonical mode; no mode-guard diagnostics fire."""
        result = _run_with_mode(ModelMode.HYBRID_COUPLED)
        manifest = result.functional_media_contract.model_manifest
        assert manifest is not None
        # Default mode → no exploratory_only / mode_guard_empirical_uncalibrated.
        assert manifest.diagnostics.get("exploratory_only") is not True
        assert (
            manifest.diagnostics.get("mode_guard_empirical_uncalibrated") is not True
        )

    def test_empirical_engineering_uncalibrated_caps_fmc_tier(self):
        """Empirical mode without calibration caps the FMC manifest at QUALITATIVE_TREND."""
        result = _run_with_mode(ModelMode.EMPIRICAL_ENGINEERING)
        manifest = result.functional_media_contract.model_manifest
        assert manifest is not None
        # Default lifecycle has no calibration → empirical mode caps tier.
        order = list(ModelEvidenceTier)
        assert order.index(manifest.evidence_tier) >= order.index(
            ModelEvidenceTier.QUALITATIVE_TREND
        )
        assert manifest.diagnostics.get("mode_guard_empirical_uncalibrated") is True

    def test_mechanistic_research_tags_fmc_exploratory(self):
        """Mechanistic mode tags FMC manifest as exploratory_only."""
        result = _run_with_mode(ModelMode.MECHANISTIC_RESEARCH)
        manifest = result.functional_media_contract.model_manifest
        assert manifest is not None
        assert manifest.diagnostics.get("exploratory_only") is True
        assert manifest.diagnostics.get("mode_guard_mechanistic") is True

    def test_m2_and_m3_modes_consistent(self):
        """M2 and M3 manifests both reflect the same ModelMode under the same run."""
        result = _run_with_mode(ModelMode.MECHANISTIC_RESEARCH)
        m2_manifest = result.functional_media_contract.model_manifest
        m3_manifest = (
            result.m3_method.model_manifest
            if result.m3_method is not None
            else None
        )
        assert m2_manifest is not None
        assert m3_manifest is not None
        # Both should be tagged exploratory_only when mode is mechanistic.
        assert m2_manifest.diagnostics.get("exploratory_only") is True
        assert m3_manifest.diagnostics.get("exploratory_only") is True
