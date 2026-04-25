"""ParamRow + Help — inline parameter help for DPSim widgets.

The ``param_row`` wrapper renders a label + help icon (``st.popover`` for
click-to-pin behaviour) + Streamlit input + optional unit + optional
evidence badge in a single horizontal row. Drop-in replacement for the
flat ``st.slider`` / ``st.number_input`` / ``st.selectbox`` calls
scattered across ``tabs/``.
"""

from __future__ import annotations

from dpsim.visualization.help.catalog import HELP_CATALOG, get_help
from dpsim.visualization.help.help_widget import (
    labeled_widget,
    param_row,
    render_help,
)

__all__ = [
    "HELP_CATALOG",
    "get_help",
    "labeled_widget",
    "param_row",
    "render_help",
]
