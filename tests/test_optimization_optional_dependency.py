"""Optional-dependency guards for the Bayesian optimization engine."""

from __future__ import annotations

import importlib


def test_optimization_engine_imports_without_optional_stack():
    module = importlib.import_module("dpsim.optimization.engine")
    assert hasattr(module, "OptimizationEngine")
    assert hasattr(module, "OptimizationExtraNotInstalledError")
