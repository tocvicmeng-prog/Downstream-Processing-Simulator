"""Multi-column series builder UI panel — STUB landing at B-2s.

The full implementation lands at B-2t (W-061, v0.8.4). This stub
exists so the `tab_calibration.py` dispatcher at B-2s passes mypy
cleanly and the third sub-tab is reachable from the user-facing
navigation. B-2t replaces this file with the real builder.
"""

from __future__ import annotations

from typing import Any

import streamlit as st


def render_multi_column_builder(
    *,
    container: Any = None,
    key_prefix: str = "mcg",
) -> None:
    """Stub — full implementation lands at B-2t / W-061."""
    target = container if container is not None else st
    target.subheader("Multi-column series builder")
    target.info(
        "Multi-column series envelope builder lands at B-2t. The "
        "backend (`module3_performance/multi_column.py`) ships since "
        "v0.8.2; the UI surface activates in the next batch of v0.8.4."
    )


__all__ = ["render_multi_column_builder"]
