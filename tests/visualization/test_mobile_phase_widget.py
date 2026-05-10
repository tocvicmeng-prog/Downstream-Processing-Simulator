"""Tests for the mobile-phase composition widget (B-1p / W-053, v0.8.4).

Stub-Streamlit-container approach (mirrors test_tab_m3_monitor.py).
"""

from __future__ import annotations

from typing import Any

import pytest

from dpsim.core.mobile_phase import MobilePhase
from dpsim.visualization.panels.mobile_phase import render_mobile_phase_widget


class _StubContainer:
    """Minimal Streamlit-container stub recording widget calls.

    The widget under test calls: markdown, caption, columns, slider,
    checkbox, number_input. The stub returns the seed value for each
    slider/number_input/checkbox so the widget renders the seed back.
    """

    def __init__(
        self,
        slider_returns: dict[str, float] | None = None,
        checkbox_return: bool = False,
        number_input_return: float = 1.0e-3,
    ) -> None:
        self.slider_returns = slider_returns or {}
        self.checkbox_return = checkbox_return
        self.number_input_return = number_input_return
        self.markdowns: list[str] = []
        self.captions: list[str] = []
        self._cols_returned: list[Any] = []

    def markdown(self, text: str) -> None:
        self.markdowns.append(text)

    def caption(self, text: str) -> None:
        self.captions.append(text)

    def slider(self, label: str, **kwargs: Any) -> float:
        # Return the seed unless overridden via slider_returns[label].
        return self.slider_returns.get(label, kwargs.get("value", 0.0))

    def checkbox(self, label: str, **kwargs: Any) -> bool:
        return self.checkbox_return

    def number_input(self, label: str, **kwargs: Any) -> float:
        return self.number_input_return

    def columns(self, n: int) -> list["_StubContainer"]:
        cols = [
            _StubContainer(
                slider_returns=self.slider_returns,
                checkbox_return=self.checkbox_return,
                number_input_return=self.number_input_return,
            )
            for _ in range(n)
        ]
        self._cols_returned.extend(cols)
        return cols


# ─── Default seed path ──────────────────────────────────────────────────────


class TestDefaultSeed:
    def test_returns_default_mobile_phase(self):
        c = _StubContainer()
        mp = render_mobile_phase_widget(container=c, key_prefix="t")
        assert isinstance(mp, MobilePhase)
        # Default MobilePhase fields are preserved when the user does
        # not move any sliders.
        default = MobilePhase()
        assert mp.T_C == pytest.approx(default.T_C)
        assert mp.c_nacl_M == pytest.approx(default.c_nacl_M)
        assert mp.phi_glycerol == pytest.approx(default.phi_glycerol)
        assert mp.phi_ethanol == pytest.approx(default.phi_ethanol)
        assert mp.custom_mu_pa_s is None

    def test_seed_propagates(self):
        c = _StubContainer()
        seed = MobilePhase(
            T_C=37.0, c_nacl_M=0.20, phi_glycerol=0.10, phi_ethanol=0.05,
        )
        mp = render_mobile_phase_widget(
            container=c, key_prefix="t", initial=seed,
        )
        assert mp.T_C == pytest.approx(37.0)
        assert mp.c_nacl_M == pytest.approx(0.20)
        assert mp.phi_glycerol == pytest.approx(0.10)
        assert mp.phi_ethanol == pytest.approx(0.05)


# ─── Custom-μ override ──────────────────────────────────────────────────────


class TestCustomMuOverride:
    def test_no_override_leaves_mu_none(self):
        c = _StubContainer(checkbox_return=False)
        mp = render_mobile_phase_widget(container=c, key_prefix="t")
        assert mp.custom_mu_pa_s is None

    def test_override_sets_mu(self):
        c = _StubContainer(checkbox_return=True, number_input_return=2.5e-3)
        mp = render_mobile_phase_widget(container=c, key_prefix="t")
        assert mp.custom_mu_pa_s == pytest.approx(2.5e-3)


# ─── Frozen output type ────────────────────────────────────────────────────


class TestFrozenOutput:
    def test_returns_frozen_dataclass(self):
        c = _StubContainer()
        mp = render_mobile_phase_widget(container=c, key_prefix="t")
        # MobilePhase is frozen — assignment raises FrozenInstanceError
        # (subclass of AttributeError).
        with pytest.raises(AttributeError):
            mp.T_C = 99.0  # type: ignore[misc]


# ─── Layout calls ──────────────────────────────────────────────────────────


class TestLayout:
    def test_renders_header_and_caption(self):
        c = _StubContainer()
        render_mobile_phase_widget(container=c, key_prefix="t")
        # Widget emits one markdown header + at least one caption.
        assert any("Mobile phase" in m for m in c.markdowns)
        assert len(c.captions) >= 1

    def test_column_layout_used(self):
        c = _StubContainer()
        render_mobile_phase_widget(container=c, key_prefix="t")
        # Two pairs of columns (4 sub-containers).
        assert len(c._cols_returned) == 4
