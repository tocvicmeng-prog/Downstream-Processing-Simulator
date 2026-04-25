"""Real Streamlit Custom Components (declare_component).

Unlike the simpler ``components.v1.html`` iframes used for
``impeller_xsec`` and ``column_xsec``, these components have **bidirectional
communication** with Python via ``Streamlit.setComponentValue(...)``.
The component value is delivered to Python on the next Streamlit rerun
and behaves like any other widget return value.

Components in this package use the **static-HTML pattern**: a single
``index.html`` file under ``components/assets/<name>/`` that loads
React + Streamlit's component lib from CDN. No npm build required.
"""

from __future__ import annotations

from dpsim.visualization.components.streamlit_components.stop_button import (
    StopButtonState,
    stop_button,
)
from dpsim.visualization.components.streamlit_components.triptych_panel import (
    triptych_panel,
)

__all__ = [
    "StopButtonState",
    "stop_button",
    "triptych_panel",
]
