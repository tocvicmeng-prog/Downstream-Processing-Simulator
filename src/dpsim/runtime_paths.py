"""Runtime path policy for DPSim output, cache, and temporary files.

Windows OneDrive folders and locked AppData temp locations can make scientific
test runs fail before solver code is exercised. This module centralizes the
fallback policy so CLI commands, tests, and CI use DPSim-owned directories.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def _base_runtime_dir() -> Path:
    """Return the writable per-user DPSim runtime base directory."""
    env_base = os.environ.get("DPSIM_RUNTIME_DIR")
    if env_base:
        return Path(env_base).expanduser()
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        return Path(local_appdata) / "DPSim"
    return Path.home() / ".dpsim"


def runtime_temp_dir() -> Path:
    """Return the directory used for temporary files."""
    return Path(os.environ.get("DPSIM_TMPDIR", _base_runtime_dir() / "tmp")).expanduser()


def runtime_cache_dir() -> Path:
    """Return the directory used for local package/test caches."""
    return Path(os.environ.get("DPSIM_CACHE_DIR", _base_runtime_dir() / "cache")).expanduser()


def default_output_dir(*parts: str) -> Path:
    """Return a default output directory outside the source tree."""
    base = Path(os.environ.get("DPSIM_OUTPUT_DIR", _base_runtime_dir() / "output")).expanduser()
    return base.joinpath(*parts) if parts else base


def configure_runtime_environment() -> None:
    """Create and export DPSim-owned temp/cache directories."""
    tmp = runtime_temp_dir()
    cache = runtime_cache_dir()
    tmp.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    for key in ("TEMP", "TMP", "TMPDIR"):
        os.environ[key] = str(tmp)
    os.environ.setdefault("PIP_CACHE_DIR", str(cache / "pip"))
    os.environ.setdefault("MPLCONFIGDIR", str(cache / "matplotlib"))
    Path(os.environ["PIP_CACHE_DIR"]).mkdir(parents=True, exist_ok=True)
    Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)
    tempfile.tempdir = str(tmp)
