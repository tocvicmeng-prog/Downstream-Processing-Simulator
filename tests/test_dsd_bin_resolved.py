"""Tests for C5 — bin-resolved DSD propagation.

Reference: docs/handover/V0_3_0_FAMILY_COVERAGE_HANDOVER.md §10 (v0.4.0 C5).
Closes architect-coherence-audit Deficit 3 — replaces the 3-quantile collapse
with a true bin-resolved propagation path.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from dpsim.lifecycle.orchestrator import (
    _dsd_distribution_bin_rows,
    _dsd_representative_rows,
)


@dataclass
class _MockDSDPayload:
    """Minimal DSD payload exposing diameter_bins_m, volume_fraction, quantile_table."""

    diameter_bins_m: list[float]
    volume_fraction: list[float]

    def quantile_table(self, quantiles):
        # crude: take cumulative distribution and pick diameters at quantiles
        bin_rows = _dsd_distribution_bin_rows(self)
        if not bin_rows:
            return []
        out = []
        sorted_rows = sorted(bin_rows, key=lambda r: float(r["quantile"]))
        for q in quantiles:
            picked = sorted_rows[0]
            for row in sorted_rows:
                if float(row["quantile"]) >= q:
                    picked = row
                    break
            out.append(
                {
                    "quantile": float(q),
                    "diameter_m": float(picked["diameter_m"]),
                    "mass_fraction": 0.0,
                }
            )
        return out

    def validate(self) -> list[str]:
        return []


def _ten_bin_payload() -> _MockDSDPayload:
    diameters = [10e-6 * (1.5 ** i) for i in range(10)]
    weights = [0.1] * 10
    return _MockDSDPayload(diameters, weights)


def _thirty_bin_payload() -> _MockDSDPayload:
    diameters = [5e-6 * (1.2 ** i) for i in range(30)]
    weights = [1.0 / 30.0] * 30
    return _MockDSDPayload(diameters, weights)


# ─── bin_resolved mode ───────────────────────────────────────────────────────


class TestBinResolvedMode:
    def test_ten_bins_all_returned(self):
        payload = _ten_bin_payload()
        rows, label = _dsd_representative_rows(
            payload, quantiles=(), mode="bin_resolved", max_representatives=0
        )
        assert len(rows) == 10
        assert "bin_resolved_10_bins" in label

    def test_thirty_bins_all_returned(self):
        """No downsampling — bin_resolved must return all 30 bins."""
        payload = _thirty_bin_payload()
        rows, label = _dsd_representative_rows(
            payload, quantiles=(), mode="bin_resolved", max_representatives=0
        )
        assert len(rows) == 30
        assert "bin_resolved_30_bins" in label

    def test_mass_fractions_sum_to_one(self):
        payload = _thirty_bin_payload()
        rows, _ = _dsd_representative_rows(
            payload, quantiles=(), mode="bin_resolved", max_representatives=0
        )
        total = sum(float(r["mass_fraction"]) for r in rows)
        assert total == pytest.approx(1.0, rel=1e-6)

    def test_representative_source_is_distribution_bin(self):
        payload = _ten_bin_payload()
        rows, _ = _dsd_representative_rows(
            payload, quantiles=(), mode="bin_resolved", max_representatives=0
        )
        for row in rows:
            assert row["representative_source"] == "distribution_bin"


# ─── existing modes unchanged ────────────────────────────────────────────────


class TestExistingModesUnchanged:
    def test_representative_mode_uses_quantiles(self):
        payload = _thirty_bin_payload()
        rows, label = _dsd_representative_rows(
            payload,
            quantiles=(0.10, 0.50, 0.90),
            mode="representative",
            max_representatives=9,
        )
        assert len(rows) == 3
        assert label == "representative"

    def test_adaptive_mode_caps_at_max_representatives(self):
        """30-bin payload with max_representatives=9 → adaptive quantiles."""
        payload = _thirty_bin_payload()
        rows, label = _dsd_representative_rows(
            payload,
            quantiles=(),
            mode="adaptive",
            max_representatives=9,
        )
        assert len(rows) == 9
        assert "adaptive_quantiles" in label

    def test_adaptive_mode_short_distribution_returns_all_bins(self):
        """10-bin payload with max_representatives=15 → all bins."""
        payload = _ten_bin_payload()
        rows, label = _dsd_representative_rows(
            payload,
            quantiles=(),
            mode="adaptive",
            max_representatives=15,
        )
        assert len(rows) == 10
        assert label == "distribution_bins"


# ─── invalid mode rejected ───────────────────────────────────────────────────


class TestInvalidMode:
    def test_unknown_mode_rejected_in_orchestrator(self):
        from dpsim.core.process_recipe import default_affinity_media_recipe
        from dpsim.lifecycle import DownstreamProcessOrchestrator

        orch = DownstreamProcessOrchestrator()
        recipe = default_affinity_media_recipe()
        with pytest.raises(ValueError, match="dsd_mode must be"):
            orch.run(recipe=recipe, dsd_mode="bogus_mode", propagate_dsd=True)
