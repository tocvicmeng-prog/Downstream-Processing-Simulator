"""Embedded animated components.

Each component is a self-contained HTML/JS asset rendered via
``streamlit.components.v1.html`` so its RAF loop and SVG attribute
updates stay sandboxed from the parent Streamlit React tree.
"""

from __future__ import annotations

from dpsim.visualization.components.column_xsec import (
    ColumnPhase,
    render_column_xsec,
)
from dpsim.visualization.components.impeller_xsec import render_impeller_xsec
from dpsim.visualization.components.streamlit_components import (
    StopButtonState,
    stop_button,
    triptych_panel,
)

__all__ = [
    "ColumnPhase",
    "StopButtonState",
    "render_column_xsec",
    "render_impeller_xsec",
    "stop_button",
    "triptych_panel",
]
