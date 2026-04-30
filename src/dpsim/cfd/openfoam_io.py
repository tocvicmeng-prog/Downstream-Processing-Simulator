"""OpenFOAM I/O helpers for the CFD-PBE coupling.

Status: TODO. Stubs for reading/writing OpenFOAM dictionaries and field
files from Python. Recommended backend: ``fluidfoam`` for clean field
readers; fall back to direct dictionary parsing for system/ files.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


def read_field(case_dir: Path, time: str, field_name: str) -> Any:
    """Read an OpenFOAM volume field (e.g., 'epsilon', 'U', 'k') at a
    specific time directory. Returns a numpy array shaped to the cell
    count.
    """
    raise NotImplementedError(
        "TODO: implement field reader. Use fluidfoam.readof.readvector / "
        "readscalar for the cleanest API."
    )


def list_time_directories(case_dir: Path) -> list[str]:
    """List time directories in an OpenFOAM case (sorted numerically)."""
    raise NotImplementedError("TODO")


def write_dict(path: Path, content: dict) -> None:
    """Write an OpenFOAM dictionary file (system/fvSchemes etc.) from
    a Python dict. Honors the FoamFile header convention.
    """
    raise NotImplementedError("TODO")
