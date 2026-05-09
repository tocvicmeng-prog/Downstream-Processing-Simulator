"""Multi-objective Bayesian optimization with BoTorch.

v0.8.0 (B-2j): ``OptimizationEngine`` is now lazy-loaded via
``__getattr__`` so importing :mod:`dpsim.optimization.objectives`
(no torch dependency) works in environments without the optional
``[optimization]`` extra installed. Importing ``OptimizationEngine``
itself still requires torch + botorch + gpytorch.
"""

from __future__ import annotations

from typing import Any

from .objectives import PARAM_BOUNDS, PARAM_NAMES, compute_objectives

__all__ = [
    "OptimizationEngine",
    "compute_objectives",
    "PARAM_NAMES",
    "PARAM_BOUNDS",
]


def __getattr__(name: str) -> Any:
    if name == "OptimizationEngine":
        from .engine import OptimizationEngine
        return OptimizationEngine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
