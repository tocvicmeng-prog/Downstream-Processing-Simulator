"""Tests for the pressure indicator component (B-3a..B-3d, v0.8.5).

Exercises the pure helpers (`_band`, `_resolve_dp`, `_help_modal_md`,
`_digit_html`, `_placeholder_html`) plus the integration entry-point
`render_pressure_indicator` against an offline stub container — no live
Streamlit runtime required.

Validation gates:
  * Gate 39 — band boundaries and colour mapping.
  * Gate 40 — popover content (operational ceiling at tier, formula
    summary, ranked remediations).
  * Gate 41 — placeholder for the no-envelope-yet first-load case.
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
from dpsim.visualization.components.pressure_indicator import (
    _BAND_COLOR,
    _band,
    _digit_html,
    _help_modal_md,
    _placeholder_html,
    _resolve_dp,
    render_pressure_indicator,
)


# ─── Stubs ─────────────────────────────────────────────────────────────────


class _StubPopover:
    """Records markdown calls inside an `st.popover` context."""

    def __init__(self) -> None:
        self.markdowns: list[str] = []

    def __enter__(self) -> "_StubPopover":
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    def markdown(self, text: str) -> None:
        self.markdowns.append(text)


class _StubColumn:
    """One Streamlit column — accepts caption / popover calls."""

    def __init__(self) -> None:
        self.captions: list[str] = []
        self.popovers: list[_StubPopover] = []

    def caption(self, text: str) -> None:
        self.captions.append(text)

    def popover(self, label: str, **kwargs: Any) -> _StubPopover:
        p = _StubPopover()
        self.popovers.append(p)
        return p


class _StubContainer:
    """Stub Streamlit container with the surface the indicator needs."""

    def __init__(self) -> None:
        self._columns: list[_StubColumn] = []
        self.htmls: list[str] = []

    def columns(self, spec: Any, **kwargs: Any) -> list[_StubColumn]:
        n = len(spec) if isinstance(spec, (list, tuple)) else int(spec)
        cols = [_StubColumn() for _ in range(n)]
        self._columns.extend(cols)
        # Return only the most recent batch — mirrors Streamlit semantics.
        return cols[-n:]

    def html(self, body: str) -> None:
        self.htmls.append(body)


# ─── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def envelope_ok():
    """Envelope at low headroom — should map to GREEN."""
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


# ─── Pure helpers ──────────────────────────────────────────────────────────


class TestBand:
    @pytest.mark.parametrize(
        "ratio,expected",
        [
            (0.0, "green"),
            (0.50, "green"),
            (0.69, "green"),
            (0.70, "amber"),
            (0.85, "amber"),
            (0.99, "amber"),
            (1.00, "red"),
            (2.00, "red"),
        ],
    )
    def test_band_boundaries(self, ratio, expected):
        assert _band(ratio) == expected

    def test_band_color_palette_matches_design(self):
        assert _BAND_COLOR["gray"] == "#94A3B8"
        assert _BAND_COLOR["green"] == "#10B981"
        assert _BAND_COLOR["amber"] == "#F59E0B"
        assert _BAND_COLOR["red"] == "#EF4444"


class TestResolveDp:
    def test_no_live_reading_renders_neutral_zero(self, envelope_ok):
        dp, source = _resolve_dp(envelope_ok, current_dp_pa=None)
        assert dp == pytest.approx(0.0)
        assert source == "no input"

    def test_uses_live_reading_when_provided(self, envelope_ok):
        dp, source = _resolve_dp(envelope_ok, current_dp_pa=12345.0)
        assert dp == 12345.0
        assert source == "live"


class TestHelpModalMd:
    def test_contains_operational_ceiling(self, envelope_ok):
        md = _help_modal_md(envelope_ok)
        assert "Maximum safe back pressure" in md
        # The operational ceiling should appear in kPa.
        op_kpa = envelope_ok.dP_max_operational_pa / 1.0e3
        assert f"{op_kpa:.1f} kPa" in md

    def test_contains_decision_tier(self, envelope_ok):
        md = _help_modal_md(envelope_ok)
        assert envelope_ok.decision_tier.value in md

    def test_contains_calculation_formula(self, envelope_ok):
        md = _help_modal_md(envelope_ok)
        assert "u_crit" in md
        assert "K_geom" in md
        assert "G_DN" in md

    def test_contains_ranked_remediations_in_order(self, envelope_ok):
        md = _help_modal_md(envelope_ok)
        # Reversibility-ordered remediations.
        i_q = md.find("Lower Q to Q_recommended")
        i_wash = md.find("Switch to wash buffer")
        i_repack = md.find("Stop flow and repack")
        i_emerg = md.find("Emergency stop")
        assert 0 <= i_q < i_wash < i_repack < i_emerg

    def test_contains_tier_aware_interval(self, envelope_ok):
        md = _help_modal_md(envelope_ok)
        # The interval bracket "lo – hi kPa" should be present.
        assert "Tier-aware interval" in md
        assert "kPa" in md


class TestDigitHtml:
    def test_renders_value_in_kpa(self, envelope_ok):
        html = _digit_html(
            dp_pa=42_000.0,
            op_max_pa=envelope_ok.dP_max_operational_pa,
            ratio=0.42,
            band="green",
            decision_tier=envelope_ok.decision_tier.value,
            source="predicted",
        )
        assert "42.0" in html  # 42_000 Pa → 42.0 kPa
        assert _BAND_COLOR["green"] in html

    def test_red_band_html_uses_red_color(self):
        html = _digit_html(
            dp_pa=99_999.0,
            op_max_pa=80_000.0,
            ratio=1.25,
            band="red",
            decision_tier="semi_quantitative",
            source="live",
        )
        assert _BAND_COLOR["red"] in html

    def test_renders_geist_mono(self):
        html = _digit_html(
            dp_pa=10_000.0,
            op_max_pa=80_000.0,
            ratio=0.125,
            band="green",
            decision_tier="semi_quantitative",
            source="predicted",
        )
        assert "Geist Mono" in html
        # Tabular numerals required by DESIGN.md.
        assert "tnum" in html


class TestPlaceholderHtml:
    def test_clearly_labeled(self):
        html = _placeholder_html()
        assert "0.0" in html
        assert "no live pressure input" in html
        assert _BAND_COLOR["gray"] in html


# ─── Integration via stub container ───────────────────────────────────────


class TestRenderIntegration:
    def test_renders_placeholder_when_envelope_none(self):
        container = _StubContainer()
        render_pressure_indicator(envelope=None, container=container)
        # Header columns created (label + ?).
        assert len(container._columns) == 2
        # Body html emitted is the placeholder.
        assert len(container.htmls) == 1
        assert "0.0" in container.htmls[0]
        assert _BAND_COLOR["gray"] in container.htmls[0]
        # No popover when envelope absent (the ? is a disabled caption).
        assert len(container._columns[1].popovers) == 0

    def test_renders_digit_and_popover_when_envelope_present(
        self, envelope_ok
    ):
        container = _StubContainer()
        render_pressure_indicator(
            envelope=envelope_ok, container=container
        )
        # Two columns for the header row.
        assert len(container._columns) == 2
        # Popover created on the right column.
        assert len(container._columns[1].popovers) == 1
        # Popover body contains the modal markdown.
        modal_text = container._columns[1].popovers[0].markdowns[0]
        assert "Maximum safe back pressure" in modal_text
        # Digit body emitted.
        assert len(container.htmls) == 1
        # Missing live input remains a neutral zero, not a predicted pressure.
        assert "no live pressure input" in container.htmls[0]
        assert _BAND_COLOR["gray"] in container.htmls[0]

    def test_live_reading_overrides_predicted(self, envelope_ok):
        container = _StubContainer()
        render_pressure_indicator(
            envelope=envelope_ok,
            current_dp_pa=envelope_ok.dP_max_operational_pa * 1.05,
            container=container,
        )
        # ratio > 1.0 → red band.
        assert _BAND_COLOR["red"] in container.htmls[0]
        assert "live" in container.htmls[0]

    def test_normal_live_reading_is_green(self, envelope_ok):
        container = _StubContainer()
        render_pressure_indicator(
            envelope=envelope_ok,
            current_dp_pa=envelope_ok.dP_max_operational_pa * 0.1,
            container=container,
        )
        assert _BAND_COLOR["green"] in container.htmls[0]
        assert "live" in container.htmls[0]
