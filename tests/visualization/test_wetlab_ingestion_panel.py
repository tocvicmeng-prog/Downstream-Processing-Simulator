"""Smoke tests for the wet-lab YAML ingestion panel (B-1r / W-057, v0.8.4)."""

from __future__ import annotations

from typing import Any

import streamlit as st  # noqa: F401  # used implicitly via session_state

from dpsim.visualization.tabs.calibration.wetlab_ingestion import (
    IngestionPreviewSummary,
    render_wetlab_ingestion_panel,
)


class _StubFile:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def getvalue(self) -> bytes:
        return self._data


class _StubColumn:
    def __init__(self) -> None:
        self.markdowns: list[str] = []
        self.captions: list[str] = []

    def metric(self, *a: Any, **k: Any) -> None:
        pass

    def markdown(self, text: str) -> None:
        self.markdowns.append(text)

    def caption(self, text: str) -> None:
        self.captions.append(text)


class _StubExpander:
    def __init__(self) -> None:
        self.entries: list[str] = []

    def __enter__(self) -> "_StubExpander":
        return self

    def __exit__(self, *a: Any) -> None:
        pass

    def write(self, s: str) -> None:
        self.entries.append(s)

    def warning(self, s: str) -> None:
        self.entries.append(s)


class _StubContainer:
    def __init__(
        self, uploaded_bytes: bytes | None = None, apply_clicked: bool = False,
    ) -> None:
        self._uploaded = uploaded_bytes
        self._apply = apply_clicked
        self.subheaders: list[str] = []
        self.captions: list[str] = []
        self.markdowns: list[str] = []
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.infos: list[str] = []
        self.successes: list[str] = []
        self.writes: list[str] = []
        self.expanders: list[_StubExpander] = []

    def subheader(self, t: str) -> None:
        self.subheaders.append(t)

    def caption(self, t: str) -> None:
        self.captions.append(t)

    def markdown(self, t: str) -> None:
        self.markdowns.append(t)

    def error(self, t: str) -> None:
        self.errors.append(t)

    def warning(self, t: str) -> None:
        self.warnings.append(t)

    def info(self, t: str) -> None:
        self.infos.append(t)

    def success(self, t: str) -> None:
        self.successes.append(t)

    def write(self, t: str) -> None:
        self.writes.append(t)

    def file_uploader(self, label: str, **k: Any) -> Any:
        if self._uploaded is None:
            return None
        return _StubFile(self._uploaded)

    def columns(self, n: int) -> list[_StubColumn]:
        return [_StubColumn() for _ in range(n)]

    def expander(self, label: str, **k: Any) -> _StubExpander:
        e = _StubExpander()
        self.expanders.append(e)
        return e

    def button(self, label: str, **k: Any) -> bool:
        return self._apply


def test_no_upload_shows_info_message():
    c = _StubContainer(uploaded_bytes=None)
    out = render_wetlab_ingestion_panel(container=c, key_prefix="t")
    assert out is None
    assert any("subheader" not in s for s in c.subheaders)
    assert any("No campaign uploaded yet" in m for m in c.infos)


def test_invalid_yaml_surfaces_error():
    c = _StubContainer(uploaded_bytes=b"not: valid: yaml: at: all\n[")
    render_wetlab_ingestion_panel(container=c, key_prefix="t")
    assert len(c.errors) >= 1


def test_invalid_utf8_surfaces_error():
    c = _StubContainer(uploaded_bytes=b"\xff\xfe\xfd")
    render_wetlab_ingestion_panel(container=c, key_prefix="t")
    assert len(c.errors) == 1
    assert "decode" in c.errors[0].lower()


def test_minimal_valid_campaign_returns_summary():
    yaml_text = b"""\
campaign_id: test_v0_8_4
operator: test_user
lab: test_lab
notes: smoke test
entries: []
"""
    c = _StubContainer(uploaded_bytes=yaml_text)
    out = render_wetlab_ingestion_panel(container=c, key_prefix="t")
    assert out is not None
    assert isinstance(out, IngestionPreviewSummary)
    assert out.campaign_id == "test_v0_8_4"
    assert out.n_total == 0
