from __future__ import annotations

from dpsim.datatypes import ModelEvidenceTier
from dpsim.visualization.components.mode_preflight import (
    scientific_mode_preflight_rows,
)


def test_mode_preflight_distinguishes_mechanistic_mode():
    rows = scientific_mode_preflight_rows(
        "mechanistic",
        weakest_tier=ModelEvidenceTier.QUALITATIVE_TREND,
        has_calibration=False,
    )
    by_field = {row["field"]: row["value"] for row in rows}

    assert by_field["Mode"] == "Mechanistic Research"
    assert "stricter" in by_field["Calibration effect"].lower()
    assert "qualitative_trend" in by_field["Current evidence"]
    assert "not loaded" in by_field["Current evidence"]


def test_unknown_mode_falls_back_to_hybrid():
    rows = scientific_mode_preflight_rows("unknown")
    by_field = {row["field"]: row["value"] for row in rows}

    assert by_field["Mode"] == "Hybrid Coupled"
