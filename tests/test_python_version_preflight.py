"""W-001 / B-0a — Python-version preflight regression tests.

DPSim is pinned to Python 3.11 or 3.12 (``pyproject.toml`` requires-python
``>=3.11,<3.13``; rationale in ``docs/decisions/ADR-001``: scipy BDF +
numba JIT cache issues on newer interpreters, plus ``torch.jit.script``
unsupported on Python 3.14+).

The preflight at ``dpsim.__init__._check_python_version`` raises
``RuntimeError`` at package import time on out-of-range interpreters so
the version mismatch surfaces *before* any solver produces a misleading
output. These tests exercise the helper directly with synthetic
``(major, minor)`` tuples — bypassing the import-time call — to confirm
both the supported and rejection paths.

Without these tests, a future loosening of the bounds in ``__init__``
could silently accept Python 3.13/3.14 and the failure would surface
only as numerical drift in stiff M3 / L2 paths.
"""
from __future__ import annotations

import sys

import pytest

from dpsim import _check_python_version


def test_supported_311_passes() -> None:
    """3.11 is the lower bound of the supported range; must be a no-op."""
    _check_python_version((3, 11))


def test_supported_312_passes() -> None:
    """3.12 is the upper bound of the supported range; must be a no-op."""
    _check_python_version((3, 12))


def test_default_uses_live_interpreter() -> None:
    """Calling without an argument must self-check against ``sys.version_info``.

    Since the test suite itself can only run on a supported interpreter
    (the package import would have failed otherwise), the no-arg call
    must succeed. This guards against a regression where the default
    silently bypasses the check.
    """
    live = (sys.version_info.major, sys.version_info.minor)
    assert (3, 11) <= live < (3, 13), (
        f"Test invariant violated: live interpreter {live} is outside "
        f"the supported range; the import of dpsim should already have "
        f"failed before reaching this test."
    )
    _check_python_version()  # no-arg call exercises the default path


def test_rejects_310_below_minimum() -> None:
    """Python 3.10 lacks the typing features the codebase relies on."""
    with pytest.raises(RuntimeError, match=r"DPSim requires Python 3\.11 or 3\.12"):
        _check_python_version((3, 10))


def test_rejects_313_at_upper_exclusive_bound() -> None:
    """Python 3.13 is the first explicitly-rejected newer version (ADR-001)."""
    with pytest.raises(RuntimeError, match=r"detected 3\.13"):
        _check_python_version((3, 13))


def test_rejects_314_per_torch_jit_script_constraint() -> None:
    """Python 3.14 is the F-arch audit's flagged real-world case.

    ``torch.jit.script`` is unsupported on 3.14+ (relevant to the optional
    ``[optimization]`` extra). The error message must include the detected
    minor version so users can confirm the diagnosis from a copy-paste of
    the traceback.
    """
    with pytest.raises(RuntimeError, match=r"detected 3\.14"):
        _check_python_version((3, 14))


def test_error_message_points_to_remediation() -> None:
    """Message must reference ADR-001 and the README install section.

    A user hitting the preflight error needs (a) the diagnosis (which ADR
    explains the rejection) and (b) the fix (where to read the install
    instructions). Both must appear in the raised message.
    """
    with pytest.raises(RuntimeError) as exc_info:
        _check_python_version((3, 13))
    msg = str(exc_info.value)
    assert "ADR-001" in msg, "Error message must cite the ADR for traceability"
    assert "README" in msg, "Error message must point to the install section"
