"""Tests for D3 — ProcessDossier as default lifecycle output.

Reference: docs/handover/V0_4_0_ARCHITECTURAL_COHERENCE_HANDOVER.md §11.
Closes architect-coherence-audit D6 (LOW).
"""

from __future__ import annotations

import json

import pytest

from dpsim.core.process_recipe import default_affinity_media_recipe
from dpsim.lifecycle import DownstreamProcessOrchestrator
from dpsim.process_dossier import ProcessDossier


@pytest.fixture(scope="module")
def lifecycle_result():
    """Run the default lifecycle once and share the result across tests."""
    orch = DownstreamProcessOrchestrator()
    return orch.run(recipe=default_affinity_media_recipe(), propagate_dsd=False)


class TestProcessDossierDefault:
    def test_dossier_populated_by_default(self, lifecycle_result):
        """Default lifecycle run produces a ProcessDossier without opt-in."""
        assert lifecycle_result.process_dossier is not None
        assert isinstance(lifecycle_result.process_dossier, ProcessDossier)

    def test_dossier_carries_run_id(self, lifecycle_result):
        dossier = lifecycle_result.process_dossier
        assert isinstance(dossier.run_id, str)
        assert dossier.run_id  # non-empty

    def test_dossier_timestamp_iso8601(self, lifecycle_result):
        dossier = lifecycle_result.process_dossier
        assert "T" in dossier.timestamp_utc  # ISO 8601 format

    def test_dossier_inherits_target_profile_from_recipe(self, lifecycle_result):
        """The dossier carries the recipe's TargetProductProfile."""
        dossier = lifecycle_result.process_dossier
        assert dossier.target_profile is not None
        assert dossier.target_profile.target_ligand == "Protein A"

    def test_dossier_to_json_dict_roundtrips(self, lifecycle_result):
        """The dossier serializes to a JSON-friendly dict."""
        dossier = lifecycle_result.process_dossier
        as_dict = dossier.to_json_dict()
        # Must round-trip through json.dumps without errors
        encoded = json.dumps(as_dict)
        decoded = json.loads(encoded)
        assert isinstance(decoded, dict)

    def test_dossier_has_full_result_attached(self, lifecycle_result):
        """The dossier carries a reference to the M1 FullResult."""
        dossier = lifecycle_result.process_dossier
        assert dossier.full_result is not None
        # The FullResult should at minimum have an emulsification field
        assert hasattr(dossier.full_result, "emulsification")
