"""Smoke tests for the v0.8.4 calibration tab + forward/inverse panels.

B-2s / W-059 + W-060. Smoke-level: panels return None with an info
banner when no lifecycle inputs are present, and run cleanly when
inputs are present (deferred to integration testing — Streamlit
session_state is hard to fully mock).
"""

from __future__ import annotations

from typing import Any

import pytest

from dpsim.visualization.tabs.calibration.forward_mc import (
    ForwardMCRunInputs,
    render_forward_mc_panel,
)
from dpsim.visualization.tabs.calibration.inverse_inference import (
    InverseRunInputs,
    _DEFAULT_MEASUREMENTS,
    _MIN_MEASUREMENTS,
    _parse_measurements,
)


class _StubColumn:
    def __init__(self) -> None:
        self.metric_calls: list[tuple[str, Any]] = []

    def metric(self, label: str, value: Any, **k: Any) -> None:
        self.metric_calls.append((label, value))

    def slider(self, *a: Any, **k: Any) -> Any:
        return k.get("value", 0)

    def number_input(self, *a: Any, **k: Any) -> Any:
        return k.get("value", 0)

    def radio(self, *a: Any, **k: Any) -> Any:
        opts = k.get("options") or a[1] if len(a) > 1 else []
        return opts[k.get("index", 0)]

    def checkbox(self, *a: Any, **k: Any) -> bool:
        return False


class _StubContainer:
    def __init__(self) -> None:
        self.subheaders: list[str] = []
        self.captions: list[str] = []
        self.markdowns: list[str] = []
        self.infos: list[str] = []
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def subheader(self, t: str) -> None:
        self.subheaders.append(t)

    def caption(self, t: str) -> None:
        self.captions.append(t)

    def markdown(self, t: str) -> None:
        self.markdowns.append(t)

    def info(self, t: str) -> None:
        self.infos.append(t)

    def error(self, t: str) -> None:
        self.errors.append(t)

    def warning(self, t: str) -> None:
        self.warnings.append(t)

    def columns(self, n: int) -> list[_StubColumn]:
        return [_StubColumn() for _ in range(n)]

    def slider(self, *a: Any, **k: Any) -> Any:
        return k.get("value", 0)

    def number_input(self, *a: Any, **k: Any) -> Any:
        return k.get("value", 0)

    def radio(self, *a: Any, **k: Any) -> Any:
        opts = k.get("options") or (a[1] if len(a) > 1 else [])
        return opts[k.get("index", 0)]

    def checkbox(self, *a: Any, **k: Any) -> bool:
        return False

    def button(self, *a: Any, **k: Any) -> bool:
        return False


# ─── Forward MC: no-inputs path ─────────────────────────────────────────────


class TestForwardMCNoInputs:
    def test_renders_info_banner_without_inputs(self):
        c = _StubContainer()
        out = render_forward_mc_panel(container=c, inputs=None)
        assert out is None
        assert any("subheader" in str(s) or s for s in c.subheaders)
        assert len(c.infos) >= 1
        # Banner should mention the lifecycle prerequisite.
        assert any("lifecycle" in i.lower() for i in c.infos)


# ─── Inverse panel: parse-measurements helper ──────────────────────────────


class TestParseMeasurements:
    def test_default_measurement_template_is_fit_ready(self):
        import pandas as pd
        df = pd.DataFrame(_DEFAULT_MEASUREMENTS)
        points, errors = _parse_measurements(df)
        assert len(points) >= _MIN_MEASUREMENTS
        assert errors == []

    def test_clean_dataframe_parses(self):
        import pandas as pd
        df = pd.DataFrame([
            {"Q_m3_s": 1.0e-9, "dP_pa": 2500.0, "sigma_dP_pa": 125.0},
            {"Q_m3_s": 3.0e-9, "dP_pa": 7400.0, "sigma_dP_pa": 370.0},
        ])
        points, errors = _parse_measurements(df)
        assert len(points) == 2
        assert errors == []

    def test_negative_q_skipped(self):
        import pandas as pd
        df = pd.DataFrame([
            {"Q_m3_s": -1.0e-9, "dP_pa": 2500.0, "sigma_dP_pa": 125.0},
            {"Q_m3_s": 3.0e-9, "dP_pa": 7400.0, "sigma_dP_pa": 370.0},
        ])
        points, errors = _parse_measurements(df)
        assert len(points) == 1
        assert len(errors) == 1
        assert "Q_m3_s" in errors[0]

    def test_zero_sigma_skipped(self):
        import pandas as pd
        df = pd.DataFrame([
            {"Q_m3_s": 1.0e-9, "dP_pa": 2500.0, "sigma_dP_pa": 0.0},
        ])
        points, errors = _parse_measurements(df)
        assert len(points) == 0
        assert len(errors) == 1
        assert "sigma_dP_pa" in errors[0]

    def test_malformed_row_handled(self):
        import pandas as pd
        df = pd.DataFrame([
            {"Q_m3_s": "not_a_number", "dP_pa": 2500.0, "sigma_dP_pa": 125.0},
        ])
        points, errors = _parse_measurements(df)
        assert len(points) == 0
        assert len(errors) == 1


# ─── Tab dispatcher resolves inputs from session state ──────────────────────


class TestSessionStateResolution:
    def test_resolve_returns_none_when_no_lifecycle(self, monkeypatch):
        # Clear session state via stub (Streamlit's session_state is a
        # singleton; clearing keys under test by patching the module).
        from dpsim.visualization.tabs import tab_calibration as tc
        from streamlit.runtime.state import SessionStateProxy
        # Direct access: patch session_state get to return None for the
        # lifecycle_result key.
        import streamlit as st

        original = st.session_state.get
        monkeypatch.setattr(
            st.session_state, "get",
            lambda k, *a, **kw: None if k == "lifecycle_result" else original(k, *a, **kw),
        )
        forward, inverse = tc._resolve_inputs_from_session()
        assert forward is None
        assert inverse is None
