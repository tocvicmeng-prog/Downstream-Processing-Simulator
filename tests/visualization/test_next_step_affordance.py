"""Tests for the post-lifecycle 'what's next' affordance (B-2u / W-063)."""

from __future__ import annotations

from typing import Any

import streamlit as st

from dpsim.visualization.components.next_step_affordance import (
    render_next_step_affordance,
)


class _StubColumn:
    def __init__(self, button_value: bool = False) -> None:
        self.button_value = button_value
        self.button_calls: list[str] = []

    def button(self, label: str, **k: Any) -> bool:
        self.button_calls.append(label)
        return self.button_value


class _StubContainer:
    def __init__(self, *, button_index: int | None = None) -> None:
        # button_index: which column's button to "click" (None = no clicks).
        self._button_index = button_index
        self._cols: list[_StubColumn] = []
        self.markdowns: list[str] = []
        self.captions: list[str] = []

    def markdown(self, t: str) -> None:
        self.markdowns.append(t)

    def caption(self, t: str) -> None:
        self.captions.append(t)

    def columns(self, n: int) -> list[_StubColumn]:
        cols = [
            _StubColumn(button_value=(i == self._button_index))
            for i in range(n)
        ]
        self._cols.extend(cols)
        return cols


class TestNoLifecycleResult:
    def test_returns_silently_when_no_result(self):
        c = _StubContainer()
        render_next_step_affordance(container=c, lifecycle_result=None)
        # No markdown / no caption — silent no-op.
        assert c.markdowns == []
        assert c.captions == []
        assert c._cols == []


class TestRendersThreeButtonsAfterLifecycle:
    def test_three_buttons_appear(self):
        # Reset the jump-flag in case a prior test set it.
        if "_jump_to_calibration_section" in st.session_state:
            del st.session_state["_jump_to_calibration_section"]
        c = _StubContainer()
        # Use a sentinel non-None lifecycle result.
        render_next_step_affordance(
            container=c, lifecycle_result=object(),
        )
        # 3 columns, 3 buttons, no jump flag set since none "clicked".
        assert len(c._cols) == 3
        assert all(len(col.button_calls) == 1 for col in c._cols)
        assert "_jump_to_calibration_section" not in st.session_state


class TestButtonClicksWriteJumpFlag:
    def test_forward_mc_button_writes_flag(self):
        if "_jump_to_calibration_section" in st.session_state:
            del st.session_state["_jump_to_calibration_section"]
        c = _StubContainer(button_index=0)
        render_next_step_affordance(
            container=c, lifecycle_result=object(),
        )
        assert (
            st.session_state.get("_jump_to_calibration_section")
            == "forward_mc"
        )
        del st.session_state["_jump_to_calibration_section"]

    def test_inverse_button_writes_flag(self):
        if "_jump_to_calibration_section" in st.session_state:
            del st.session_state["_jump_to_calibration_section"]
        c = _StubContainer(button_index=1)
        render_next_step_affordance(
            container=c, lifecycle_result=object(),
        )
        assert (
            st.session_state.get("_jump_to_calibration_section")
            == "inverse"
        )
        del st.session_state["_jump_to_calibration_section"]

    def test_multi_column_button_writes_flag(self):
        if "_jump_to_calibration_section" in st.session_state:
            del st.session_state["_jump_to_calibration_section"]
        c = _StubContainer(button_index=2)
        render_next_step_affordance(
            container=c, lifecycle_result=object(),
        )
        assert (
            st.session_state.get("_jump_to_calibration_section")
            == "multi_column"
        )
        del st.session_state["_jump_to_calibration_section"]
