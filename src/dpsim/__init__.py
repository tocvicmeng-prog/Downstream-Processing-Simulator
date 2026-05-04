"""Downstream Processing Simulator.

The package is a fork of the upstream microsphere simulation stack,
re-scoped around a clean-slate process lifecycle: M1 fabrication,
M2 functionalization, and M3 affinity chromatography.

v0.5.0 (D1): the legacy top-level convenience exports
(``SimulationParameters``, ``FullResult``, ``run_pipeline``,
``PipelineOrchestrator``) have been removed from this module's public
API. They are still defined in their respective implementation modules
and remain available under their canonical paths:

  - ``from dpsim.datatypes import SimulationParameters, FullResult``
  - ``from dpsim.pipeline.orchestrator import PipelineOrchestrator``

Application code should use the lifecycle-layer entry points instead:

  - ``from dpsim.lifecycle import run_default_lifecycle, run_m1_from_recipe``
  - ``from dpsim.module3_performance.method_simulation import run_method_simulation``
  - ``from dpsim.core.process_recipe import default_affinity_media_recipe``
  - ``from dpsim.core.performance_recipe import performance_recipe_from_resolved``
"""
from __future__ import annotations

import sys

__version__ = "0.6.6"

# Supported Python range. Mirrors pyproject.toml's `requires-python` and
# docs/decisions/ADR-001. Two-tuple (major, minor); upper bound exclusive.
_PYTHON_MIN: tuple[int, int] = (3, 11)
_PYTHON_MAX_EXCL: tuple[int, int] = (3, 13)


def _check_python_version(version: tuple[int, int] | None = None) -> None:
    """Fail fast on unsupported Python versions.

    DPSim is pinned to Python 3.11 or 3.12 (see ``pyproject.toml`` and
    ``docs/decisions/ADR-001``). Older interpreters lack required typing /
    library features; newer interpreters exhibit:

      - scipy BDF + numba JIT cache issues (per ADR-001), and
      - ``torch.jit.script`` unsupported on Python 3.14+ (relevant to the
        optional ``[optimization]`` extra).

    The check fires at package import time, surfacing the version mismatch
    before any solver or test produces a misleading result. Without the
    check, DPSim runs silently on Python 3.13/3.14 and can return numerically
    incorrect outputs for stiff M3 / L2 paths.

    Args:
        version: ``(major, minor)`` tuple. Defaults to the live
            ``sys.version_info`` so the import-time call self-checks.
            Tests pass a synthetic tuple to exercise the rejection paths.

    Raises:
        RuntimeError: with a remediation message if the detected version
            lies outside the supported half-open range ``[3.11, 3.13)``.
    """
    if version is None:
        version = (sys.version_info.major, sys.version_info.minor)
    if version < _PYTHON_MIN or version >= _PYTHON_MAX_EXCL:
        major, minor = version
        raise RuntimeError(
            f"DPSim requires Python "
            f"{_PYTHON_MIN[0]}.{_PYTHON_MIN[1]} or "
            f"{_PYTHON_MAX_EXCL[0]}.{_PYTHON_MAX_EXCL[1] - 1}; "
            f"detected {major}.{minor}. Newer interpreters trigger scipy "
            f"BDF + numba JIT cache issues (see docs/decisions/ADR-001) "
            f"and torch.jit.script is unsupported on Python 3.14+. "
            f"Recreate the venv with Python 3.11 or 3.12; see the README "
            f"install section."
        )


_check_python_version()

from .lifecycle.orchestrator import (
    DownstreamProcessOrchestrator,
    run_default_lifecycle,
)

__all__ = [
    "DownstreamProcessOrchestrator",
    "__version__",
    "_check_python_version",
    "run_default_lifecycle",
]
