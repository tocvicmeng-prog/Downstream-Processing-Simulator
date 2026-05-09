"""B-1h / W-030 tests: decision-grade enum extension for pressure-envelope outputs.

Covers the four new ``OutputType`` members added in B-1h:

* ``PRESSURE_LIMIT`` — operational ΔP_max ceiling
* ``Q_MAX`` — max safe flow rate (inverted u_crit)
* ``U_CRIT`` — critical superficial velocity
* ``PRESSURE_HEADROOM`` — ΔP / ΔP_max ratio (always rendered)

Acceptance per architect §3.6: PRESSURE_LIMIT / Q_MAX / U_CRIT mirror
the existing PRESSURE_DROP policy (min tier SEMI_QUANTITATIVE → INTERVAL;
promote to NUMBER at CALIBRATED_LOCAL). PRESSURE_HEADROOM is
tier-independent (renders as NUMBER for any reasonable envelope tier
because it's a dimensionless ratio).
"""

from __future__ import annotations

from dpsim.core.decision_grade import (
    DECISION_GRADE_POLICY,
    OutputType,
    RenderMode,
    decide_render_mode,
)
from dpsim.datatypes import ModelEvidenceTier


# ─── Enum membership ─────────────────────────────────────────────────────────


class TestNewOutputTypeMembers:
    """The four new pressure-envelope OutputType members exist."""

    def test_pressure_limit_member_exists(self) -> None:
        assert OutputType.PRESSURE_LIMIT.value == "pressure_limit"

    def test_q_max_member_exists(self) -> None:
        assert OutputType.Q_MAX.value == "q_max"

    def test_u_crit_member_exists(self) -> None:
        assert OutputType.U_CRIT.value == "u_crit"

    def test_pressure_headroom_member_exists(self) -> None:
        assert OutputType.PRESSURE_HEADROOM.value == "pressure_headroom"


# ─── Policy table ────────────────────────────────────────────────────────────


class TestPolicyTableRows:
    """Each new OutputType has a row in DECISION_GRADE_POLICY."""

    def test_pressure_limit_floor_is_semi_quantitative(self) -> None:
        # Mirrors PRESSURE_DROP (Kozeny-Carman / Ergun well-described).
        assert (
            DECISION_GRADE_POLICY[OutputType.PRESSURE_LIMIT]
            == ModelEvidenceTier.SEMI_QUANTITATIVE
        )

    def test_q_max_floor_is_semi_quantitative(self) -> None:
        assert (
            DECISION_GRADE_POLICY[OutputType.Q_MAX]
            == ModelEvidenceTier.SEMI_QUANTITATIVE
        )

    def test_u_crit_floor_is_semi_quantitative(self) -> None:
        assert (
            DECISION_GRADE_POLICY[OutputType.U_CRIT]
            == ModelEvidenceTier.SEMI_QUANTITATIVE
        )

    def test_pressure_headroom_floor_is_qualitative_trend(self) -> None:
        # Headroom is dimensionless; always meaningful regardless of tier.
        assert (
            DECISION_GRADE_POLICY[OutputType.PRESSURE_HEADROOM]
            == ModelEvidenceTier.QUALITATIVE_TREND
        )


# ─── Render-mode behaviour: PRESSURE_LIMIT / Q_MAX / U_CRIT ──────────────────
#
# These three mirror PRESSURE_DROP: floor at SEMI_QUANTITATIVE.
# Tier ladder (strongest first):
#   VALIDATED_QUANTITATIVE → NUMBER
#   CALIBRATED_LOCAL       → NUMBER
#   SEMI_QUANTITATIVE      → NUMBER (at the floor)
#   QUALITATIVE_TREND      → INTERVAL (gap == 1)
#   UNSUPPORTED            → RANK_BAND (gap == 2)


class TestPressureLimitRenderMode:
    def test_validated_quantitative_renders_as_number(self) -> None:
        assert (
            decide_render_mode(
                OutputType.PRESSURE_LIMIT, ModelEvidenceTier.VALIDATED_QUANTITATIVE
            )
            == RenderMode.NUMBER
        )

    def test_calibrated_local_renders_as_number(self) -> None:
        # Manufacturer pressure-flow curve supplied.
        assert (
            decide_render_mode(
                OutputType.PRESSURE_LIMIT, ModelEvidenceTier.CALIBRATED_LOCAL
            )
            == RenderMode.NUMBER
        )

    def test_semi_quantitative_renders_as_number_at_floor(self) -> None:
        # Default tier from family_kgeom literature anchor.
        assert (
            decide_render_mode(
                OutputType.PRESSURE_LIMIT, ModelEvidenceTier.SEMI_QUANTITATIVE
            )
            == RenderMode.NUMBER
        )

    def test_qualitative_trend_renders_as_interval(self) -> None:
        # Triggered when valid_domain violation demotes the envelope tier.
        assert (
            decide_render_mode(
                OutputType.PRESSURE_LIMIT, ModelEvidenceTier.QUALITATIVE_TREND
            )
            == RenderMode.INTERVAL
        )

    def test_unsupported_renders_as_rank_band(self) -> None:
        assert (
            decide_render_mode(
                OutputType.PRESSURE_LIMIT, ModelEvidenceTier.UNSUPPORTED
            )
            == RenderMode.RANK_BAND
        )


class TestQMaxRenderMode:
    """Q_MAX mirrors PRESSURE_LIMIT exactly."""

    def test_calibrated_local_number(self) -> None:
        assert (
            decide_render_mode(OutputType.Q_MAX, ModelEvidenceTier.CALIBRATED_LOCAL)
            == RenderMode.NUMBER
        )

    def test_qualitative_trend_interval(self) -> None:
        assert (
            decide_render_mode(OutputType.Q_MAX, ModelEvidenceTier.QUALITATIVE_TREND)
            == RenderMode.INTERVAL
        )


class TestUCritRenderMode:
    """U_CRIT mirrors PRESSURE_LIMIT exactly."""

    def test_semi_quantitative_number(self) -> None:
        assert (
            decide_render_mode(
                OutputType.U_CRIT, ModelEvidenceTier.SEMI_QUANTITATIVE
            )
            == RenderMode.NUMBER
        )

    def test_qualitative_trend_interval(self) -> None:
        assert (
            decide_render_mode(
                OutputType.U_CRIT, ModelEvidenceTier.QUALITATIVE_TREND
            )
            == RenderMode.INTERVAL
        )


# ─── Render-mode behaviour: PRESSURE_HEADROOM ────────────────────────────────


class TestPressureHeadroomRenderMode:
    """PRESSURE_HEADROOM is tier-independent (always renders as NUMBER for any
    real envelope tier — UNSUPPORTED is the only suppression case)."""

    def test_validated_quantitative_number(self) -> None:
        assert (
            decide_render_mode(
                OutputType.PRESSURE_HEADROOM,
                ModelEvidenceTier.VALIDATED_QUANTITATIVE,
            )
            == RenderMode.NUMBER
        )

    def test_calibrated_local_number(self) -> None:
        assert (
            decide_render_mode(
                OutputType.PRESSURE_HEADROOM, ModelEvidenceTier.CALIBRATED_LOCAL
            )
            == RenderMode.NUMBER
        )

    def test_semi_quantitative_number(self) -> None:
        assert (
            decide_render_mode(
                OutputType.PRESSURE_HEADROOM, ModelEvidenceTier.SEMI_QUANTITATIVE
            )
            == RenderMode.NUMBER
        )

    def test_qualitative_trend_number_at_floor(self) -> None:
        # Floor is QUALITATIVE_TREND → still NUMBER at the floor.
        assert (
            decide_render_mode(
                OutputType.PRESSURE_HEADROOM, ModelEvidenceTier.QUALITATIVE_TREND
            )
            == RenderMode.NUMBER
        )

    def test_unsupported_demotes_to_interval(self) -> None:
        # Only UNSUPPORTED falls below the floor.
        assert (
            decide_render_mode(
                OutputType.PRESSURE_HEADROOM, ModelEvidenceTier.UNSUPPORTED
            )
            == RenderMode.INTERVAL
        )


# ─── Cross-policy consistency ────────────────────────────────────────────────


class TestCrossPolicyConsistency:
    """The new PRESSURE_LIMIT/Q_MAX/U_CRIT policies are consistent with the
    existing PRESSURE_DROP policy — they all carry the same SEMI_QUANTITATIVE
    floor, since they are governed by the same hydrodynamic correlations."""

    def test_pressure_outputs_share_floor_with_pressure_drop(self) -> None:
        floor = DECISION_GRADE_POLICY[OutputType.PRESSURE_DROP]
        assert DECISION_GRADE_POLICY[OutputType.PRESSURE_LIMIT] == floor
        assert DECISION_GRADE_POLICY[OutputType.Q_MAX] == floor
        assert DECISION_GRADE_POLICY[OutputType.U_CRIT] == floor

    def test_headroom_floor_weaker_than_pressure_outputs(self) -> None:
        # Headroom (ratio) needs less calibration than the absolute outputs
        # because it's dimensionless.
        from dpsim.core.decision_grade import _tier_index

        headroom_idx = _tier_index(
            DECISION_GRADE_POLICY[OutputType.PRESSURE_HEADROOM]
        )
        limit_idx = _tier_index(DECISION_GRADE_POLICY[OutputType.PRESSURE_LIMIT])
        # Higher index = weaker tier in this codebase's ordering.
        assert headroom_idx > limit_idx
