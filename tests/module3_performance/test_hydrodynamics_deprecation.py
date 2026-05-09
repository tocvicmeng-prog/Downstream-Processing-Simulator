"""B-2f / W-020 tests: max_safe_flow_rate deprecation.

The v0.6.6 ``ColumnGeometry.max_safe_flow_rate(safety=0.8)`` anchored
ΔP_max to ``safety × E_star`` (the bursting modulus). For soft
chromatography media the operational limit is set by bed-compression
u_crit, not by bead bursting; the two are physically distinct and
u_crit is typically 5–50× lower than the bursting limit.

B-2f deprecates the method (one-release migration window). It still
returns a value (the bursting bound), but emits a DeprecationWarning
pointing callers at compute_pressure_envelope. v0.8 will remove it.
"""

from __future__ import annotations

import warnings

import pytest

from dpsim.module3_performance.hydrodynamics import ColumnGeometry


class TestDeprecationWarning:
    """The method emits DeprecationWarning."""

    def test_emits_deprecation_warning(self) -> None:
        col = ColumnGeometry()
        with pytest.warns(DeprecationWarning, match="max_safe_flow_rate"):
            col.max_safe_flow_rate()

    def test_warning_mentions_replacement(self) -> None:
        col = ColumnGeometry()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            col.max_safe_flow_rate()
        assert len(caught) == 1
        assert "compute_pressure_envelope" in str(caught[0].message)

    def test_warning_is_deprecation_category(self) -> None:
        col = ColumnGeometry()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            col.max_safe_flow_rate()
        assert issubclass(caught[0].category, DeprecationWarning)


class TestStillReturnsValue:
    """The method still computes a value during its deprecation window."""

    def test_returns_positive_float(self) -> None:
        col = ColumnGeometry()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = col.max_safe_flow_rate()
        assert result > 0.0
        assert isinstance(result, float)

    def test_safety_factor_scales_linearly(self) -> None:
        # ΔP_max = safety × E_star, so Q_max scales linearly with safety.
        col = ColumnGeometry()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            q1 = col.max_safe_flow_rate(safety=0.5)
            q2 = col.max_safe_flow_rate(safety=1.0)
        import math

        assert math.isclose(q2 / q1, 2.0, rel_tol=1e-9)


class TestMigrationDocstring:
    """The method's docstring points to the replacement."""

    def test_docstring_mentions_deprecation(self) -> None:
        doc = ColumnGeometry.max_safe_flow_rate.__doc__ or ""
        assert "DEPRECATED" in doc

    def test_docstring_mentions_compute_pressure_envelope(self) -> None:
        doc = ColumnGeometry.max_safe_flow_rate.__doc__ or ""
        assert "compute_pressure_envelope" in doc
