"""Tests for the multi-column series builder UI (B-2t / W-061, v0.8.4)."""

from __future__ import annotations

import pandas as pd

from dpsim.datatypes import PolymerFamily
from dpsim.module3_performance.multi_column import MultiColumnGeometry
from dpsim.visualization.tabs.calibration.multi_column import _df_to_geometry


class TestDfToGeometry:
    def test_default_two_row_capture_polish(self):
        df = pd.DataFrame([
            {
                "name": "capture",
                "family": PolymerFamily.AGAROSE.value,
                "diameter_m": 0.01,
                "bed_height_m": 0.05,
                "bed_porosity": 0.38,
                "particle_porosity": 0.70,
            },
            {
                "name": "polish",
                "family": PolymerFamily.CELLULOSE.value,
                "diameter_m": 0.01,
                "bed_height_m": 0.10,
                "bed_porosity": 0.38,
                "particle_porosity": 0.70,
            },
        ])
        geom, errors = _df_to_geometry(df)
        assert errors == []
        assert isinstance(geom, MultiColumnGeometry)
        assert geom.n_columns == 2
        assert geom.polymer_families[0].value == PolymerFamily.AGAROSE.value
        assert geom.polymer_families[1].value == PolymerFamily.CELLULOSE.value

    def test_unknown_family_skipped_with_error(self):
        df = pd.DataFrame([
            {
                "name": "good",
                "family": PolymerFamily.AGAROSE.value,
                "diameter_m": 0.01,
                "bed_height_m": 0.05,
                "bed_porosity": 0.38,
                "particle_porosity": 0.70,
            },
            {
                "name": "bad",
                "family": "not_a_real_family",
                "diameter_m": 0.01,
                "bed_height_m": 0.05,
                "bed_porosity": 0.38,
                "particle_porosity": 0.70,
            },
        ])
        geom, errors = _df_to_geometry(df)
        assert geom is not None
        assert geom.n_columns == 1
        assert len(errors) == 1
        assert "unknown polymer_family" in errors[0]

    def test_malformed_value_skipped(self):
        df = pd.DataFrame([
            {
                "name": "bad",
                "family": PolymerFamily.AGAROSE.value,
                "diameter_m": "not_numeric",
                "bed_height_m": 0.05,
                "bed_porosity": 0.38,
                "particle_porosity": 0.70,
            },
        ])
        geom, errors = _df_to_geometry(df)
        assert geom is None
        assert len(errors) == 1

    def test_empty_dataframe_returns_none(self):
        df = pd.DataFrame([])
        geom, errors = _df_to_geometry(df)
        assert geom is None

    def test_three_column_series(self):
        df = pd.DataFrame([
            {
                "name": f"col_{i}",
                "family": PolymerFamily.AGAROSE.value,
                "diameter_m": 0.01,
                "bed_height_m": 0.05 + i * 0.02,
                "bed_porosity": 0.38,
                "particle_porosity": 0.70,
            } for i in range(3)
        ])
        geom, errors = _df_to_geometry(df)
        assert errors == []
        assert geom is not None
        assert geom.n_columns == 3
