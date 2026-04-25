"""Shared test fixtures for dpsim tests."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
import numpy as np

from dpsim.runtime_paths import configure_runtime_environment, default_output_dir, runtime_temp_dir
from dpsim.datatypes import (
    MaterialProperties,
    MixerGeometry,
    SimulationParameters,
)


configure_runtime_environment()
os.environ.setdefault("DPSIM_OUTPUT_DIR", str(default_output_dir("tests")))
Path(os.environ["DPSIM_OUTPUT_DIR"]).mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(runtime_temp_dir())


@pytest.fixture
def default_params():
    """Default simulation parameters."""
    return SimulationParameters()


@pytest.fixture
def default_props():
    """Default material properties."""
    return MaterialProperties()


@pytest.fixture
def default_mixer():
    """Default mixer geometry."""
    return MixerGeometry()


@pytest.fixture
def rng():
    """Seeded random number generator for reproducible tests."""
    return np.random.default_rng(42)

