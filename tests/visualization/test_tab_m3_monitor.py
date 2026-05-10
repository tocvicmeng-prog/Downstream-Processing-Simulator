"""Smoke tests for the streaming pressure-monitor UI section (B-2i).

These tests exercise the rendering function with a stubbed Streamlit
container to verify the no-upload, valid-upload, and parse-error paths
without requiring a Streamlit runtime.
"""

from __future__ import annotations

from typing import Any

import pytest

from dpsim.core.mobile_phase import MobilePhase
from dpsim.datatypes import PolymerFamily
from dpsim.module3_performance.hydrodynamics import ColumnGeometry
from dpsim.module3_performance.pressure_envelope import (
    compute_pressure_envelope,
)
from dpsim.visualization.tabs.tab_m3_monitor import (
    render_pressure_monitor_section,
)


class _StubColumn:
    """One Streamlit column stub — accepts metric() calls."""

    def __init__(self) -> None:
        self.metric_calls: list[tuple[str, str]] = []
        self.markdowns: list[str] = []
        self.captions: list[str] = []
        # W-092 (v0.8.9): RecoveryAction clickable controls add button() calls
        # on individual columns. The stub returns False so the click handler
        # never fires under tests.
        self.button_calls: list[str] = []

    def metric(self, label: str, value: Any, **kwargs: Any) -> None:
        self.metric_calls.append((label, str(value)))

    def markdown(self, text: str) -> None:
        self.markdowns.append(text)

    def caption(self, text: str) -> None:
        self.captions.append(text)

    def button(self, label: str, **kwargs: Any) -> bool:
        self.button_calls.append(label)
        return False


class _StubContainer:
    """Streamlit-container stub for offline tests.

    Records subheader / caption / info / warning / error / success /
    plotly_chart / metric / file_uploader / columns / download_button
    calls without requiring a live Streamlit runtime.
    """

    def __init__(self, uploaded_bytes: bytes | None = None) -> None:
        self.subheaders: list[str] = []
        self.captions: list[str] = []
        self.infos: list[str] = []
        self.warnings: list[str] = []
        self.errors: list[str] = []
        self.successes: list[str] = []
        self.plotly_charts: list[Any] = []
        self.downloads: list[tuple[str, str]] = []
        self.markdowns: list[str] = []
        self.writes: list[str] = []
        self._uploaded_bytes = uploaded_bytes
        self._columns: list[_StubColumn] = []
        self._expanders: list["_StubExpander"] = []

    # ── Streamlit-imitation surface ────────────────────────────────

    def subheader(self, text: str) -> None:
        self.subheaders.append(text)

    def caption(self, text: str) -> None:
        self.captions.append(text)

    def info(self, text: str) -> None:
        self.infos.append(text)

    def warning(self, text: str) -> None:
        self.warnings.append(text)

    def error(self, text: str) -> None:
        self.errors.append(text)

    def success(self, text: str) -> None:
        self.successes.append(text)

    def plotly_chart(self, fig: Any, **kwargs: Any) -> None:
        self.plotly_charts.append(fig)

    def download_button(
        self, label: str, data: str, **kwargs: Any
    ) -> None:
        self.downloads.append((label, data))

    def file_uploader(self, label: str, **kwargs: Any) -> Any:
        if self._uploaded_bytes is None:
            return None
        return _StubFile(self._uploaded_bytes)

    def columns(self, n: int) -> list[_StubColumn]:
        cols = [_StubColumn() for _ in range(n)]
        self._columns.extend(cols)
        return cols

    # B-2u (W-062, v0.8.4): RecoveryAction timeline ribbon adds
    # markdown / write / expander calls under the trace plot.
    def markdown(self, text: str) -> None:
        self.markdowns.append(text)

    def write(self, text: str) -> None:
        self.writes.append(text)

    def expander(self, label: str, **kwargs: Any) -> "_StubExpander":
        e = _StubExpander()
        self._expanders.append(e)
        return e

    # B-5d (W-076, v0.8.7): MonitorSource selection radio. The stub
    # always returns "CSV replay" so existing tests exercise the
    # CSV-replay code path unchanged.
    def radio(self, label: str, options: list, **kwargs: Any) -> str:
        return "CSV replay"


class _StubExpander:
    """Stub for st.expander context manager."""

    def __init__(self) -> None:
        self.entries: list[str] = []

    def __enter__(self) -> "_StubExpander":
        return self

    def __exit__(self, *a: Any) -> None:
        pass

    def write(self, t: str) -> None:
        self.entries.append(t)


class _StubFile:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def getvalue(self) -> bytes:
        return self._data


# ─── Fixture ───────────────────────────────────────────────────────────────


@pytest.fixture
def envelope():
    column = ColumnGeometry()
    mp = MobilePhase()
    pre = compute_pressure_envelope(
        polymer_family=PolymerFamily.AGAROSE,
        column=column,
        mobile_phase=mp,
        Q_set_m3_s=1e-9,
    )
    return compute_pressure_envelope(
        polymer_family=PolymerFamily.AGAROSE,
        column=column,
        mobile_phase=mp,
        Q_set_m3_s=pre.Q_recommended_m3_s * 0.1,
    )


# ─── Tests ─────────────────────────────────────────────────────────────────


class TestRenderNoUpload:
    def test_emits_subheader_and_info(self, envelope):
        container = _StubContainer(uploaded_bytes=None)
        render_pressure_monitor_section(envelope=envelope, container=container)
        assert any("monitor" in s.lower() for s in container.subheaders)
        assert len(container.infos) >= 1
        assert "uploaded" in container.infos[0].lower()

    def test_offers_example_download(self, envelope):
        container = _StubContainer(uploaded_bytes=None)
        render_pressure_monitor_section(envelope=envelope, container=container)
        assert len(container.downloads) == 1
        label, data = container.downloads[0]
        assert "example" in label.lower()
        assert "t_s" in data and "dP_pa" in data and "Q_m3_s" in data

    def test_no_plot_without_upload(self, envelope):
        container = _StubContainer(uploaded_bytes=None)
        render_pressure_monitor_section(envelope=envelope, container=container)
        assert len(container.plotly_charts) == 0


class TestRenderSmoothUpload:
    def test_smooth_csv_renders_success(self, envelope):
        # Build a minimal CSV at envelope.Q_set + dP_predicted (OK band).
        Q_set = envelope.Q_set_m3_s
        dp = envelope.dP_predicted_pa
        text = "t_s,dP_pa,Q_m3_s\n"
        for t in range(5):
            text += f"{float(t)},{dp},{Q_set}\n"
        container = _StubContainer(uploaded_bytes=text.encode("utf-8"))
        render_pressure_monitor_section(envelope=envelope, container=container)
        assert len(container.successes) >= 1
        assert "OK" in container.successes[0]
        # B-2u (W-062, v0.8.4) added the per-rule action timeline plot
        # below the trace plot — total of 2 plotly charts now.
        assert len(container.plotly_charts) == 2
        # The 5-column metrics row must be populated.
        assert len(container._columns) >= 1


class TestRenderBadCsv:
    def test_unparseable_header_error(self, envelope):
        bad = b"not,a,header\nfoo,bar,baz\n"
        container = _StubContainer(uploaded_bytes=bad)
        render_pressure_monitor_section(envelope=envelope, container=container)
        assert len(container.errors) == 1
        assert "csv parse failed" in container.errors[0].lower()

    def test_invalid_utf8_error(self, envelope):
        # Bytes that don't decode as UTF-8.
        bad = b"\xff\xfe\xfd"
        container = _StubContainer(uploaded_bytes=bad)
        render_pressure_monitor_section(envelope=envelope, container=container)
        assert len(container.errors) == 1
        assert "decode" in container.errors[0].lower()
