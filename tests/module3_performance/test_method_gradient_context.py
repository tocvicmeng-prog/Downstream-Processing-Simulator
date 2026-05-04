"""B-2e follow-on: GradientContext consumption in M3 method adapter.

Verifies that ``ChromatographyMethodStep.gradient_context`` is consumed
by ``run_loaded_state_elution`` and ``_elution_pH`` in preference to the
legacy ``gradient_field`` / ``gradient_start`` / ``gradient_end`` triple.
Backward-compat is asserted: legacy-only steps still produce the same
elution pH and the same _resolve_gradient output.
"""

from __future__ import annotations

import pytest

from dpsim.module3_performance.method import (
    ChromatographyMethodStep,
    ChromatographyOperation,
    BufferCondition,
    _elution_pH,
    _resolve_gradient,
    default_protein_a_method_steps,
)
from dpsim.module3_performance.quantitative_gates import GradientContext


# ─── Resolver ────────────────────────────────────────────────────────────────


class TestResolveGradient:
    def test_no_gradient_returns_none(self):
        step = ChromatographyMethodStep(
            name="elute",
            operation=ChromatographyOperation.ELUTE,
            duration_s=300.0,
            buffer=BufferCondition(pH=3.5),
        )
        assert _resolve_gradient(step) is None

    def test_typed_context_preferred(self):
        ctx = GradientContext(
            gradient_field="ph",
            start_value=8.0, end_value=4.0,
            duration_s=200.0,
        )
        step = ChromatographyMethodStep(
            name="elute",
            operation=ChromatographyOperation.ELUTE,
            duration_s=999.0,
            # Legacy fields say something different — typed context wins.
            gradient_field="salt_concentration",
            gradient_start=10.0,
            gradient_end=500.0,
            gradient_context=ctx,
        )
        resolved = _resolve_gradient(step)
        assert resolved is ctx
        assert resolved.gradient_field == "ph"
        assert resolved.start_value == 8.0
        assert resolved.duration_s == 200.0

    def test_legacy_fields_fall_back(self):
        step = ChromatographyMethodStep(
            name="elute",
            operation=ChromatographyOperation.ELUTE,
            duration_s=300.0,
            gradient_field="ph",
            gradient_start=7.4,
            gradient_end=3.5,
        )
        resolved = _resolve_gradient(step)
        assert resolved is not None
        assert resolved.gradient_field == "ph"
        assert resolved.start_value == 7.4
        assert resolved.end_value == 3.5
        assert resolved.duration_s == 300.0  # inherited from step

    def test_legacy_partial_returns_none(self):
        """Legacy field set but start/end missing → no resolution."""
        step = ChromatographyMethodStep(
            name="elute",
            operation=ChromatographyOperation.ELUTE,
            duration_s=300.0,
            gradient_field="ph",
            gradient_start=None,
            gradient_end=None,
        )
        assert _resolve_gradient(step) is None

    def test_inactive_typed_context_falls_back_to_legacy(self):
        """An inactive (zero-duration) typed context must yield to legacy."""
        ctx = GradientContext(gradient_field="ph", duration_s=0.0)
        step = ChromatographyMethodStep(
            name="elute",
            operation=ChromatographyOperation.ELUTE,
            duration_s=300.0,
            gradient_field="ph",
            gradient_start=7.4,
            gradient_end=3.5,
            gradient_context=ctx,
        )
        resolved = _resolve_gradient(step)
        assert resolved is not None
        # Falls through to a legacy-derived context, not the inactive one.
        assert resolved is not ctx
        assert resolved.start_value == 7.4


# ─── _elution_pH consumes typed context ─────────────────────────────────────


class TestElutionPH:
    def test_none_step_returns_default(self):
        assert _elution_pH(None) == pytest.approx(3.5)

    def test_typed_context_drives_end_pH(self):
        step = ChromatographyMethodStep(
            name="elute",
            operation=ChromatographyOperation.ELUTE,
            duration_s=300.0,
            buffer=BufferCondition(pH=7.4),
            gradient_context=GradientContext(
                gradient_field="ph",
                start_value=7.4, end_value=2.5,
                duration_s=300.0,
            ),
        )
        assert _elution_pH(step) == pytest.approx(2.5)

    def test_legacy_path_still_works(self):
        step = ChromatographyMethodStep(
            name="elute",
            operation=ChromatographyOperation.ELUTE,
            duration_s=300.0,
            buffer=BufferCondition(pH=7.4),
            gradient_field="ph",
            gradient_start=7.4, gradient_end=3.0,
        )
        assert _elution_pH(step) == pytest.approx(3.0)

    def test_no_gradient_falls_back_to_buffer_pH(self):
        step = ChromatographyMethodStep(
            name="elute",
            operation=ChromatographyOperation.ELUTE,
            duration_s=300.0,
            buffer=BufferCondition(pH=4.5),
        )
        assert _elution_pH(step) == pytest.approx(4.5)

    def test_non_pH_gradient_falls_back_to_buffer(self):
        """Salt gradient should not affect pH — buffer pH is used."""
        step = ChromatographyMethodStep(
            name="elute",
            operation=ChromatographyOperation.ELUTE,
            duration_s=300.0,
            buffer=BufferCondition(pH=7.0),
            gradient_context=GradientContext(
                gradient_field="salt_concentration",
                start_value=50.0, end_value=1000.0,
                duration_s=300.0,
            ),
        )
        assert _elution_pH(step) == pytest.approx(7.0)


# ─── Default factory populates both paths ────────────────────────────────────


class TestDefaultFactoryPopulatesBoth:
    def test_default_elute_step_has_gradient_context(self):
        steps = default_protein_a_method_steps()
        elute = next(s for s in steps if s.operation == ChromatographyOperation.ELUTE)
        assert elute.gradient_context is not None
        assert elute.gradient_context.gradient_field == "ph"
        assert elute.gradient_context.start_value == pytest.approx(7.4)
        assert elute.gradient_context.end_value == pytest.approx(3.5)
        # Legacy fields preserved for back-compat too.
        assert elute.gradient_field == "ph"
        assert elute.gradient_start == pytest.approx(7.4)
        assert elute.gradient_end == pytest.approx(3.5)

    def test_default_elute_pH_via_resolver(self):
        steps = default_protein_a_method_steps()
        elute = next(s for s in steps if s.operation == ChromatographyOperation.ELUTE)
        assert _elution_pH(elute) == pytest.approx(3.5)
