"""Family-support panel for model-maturity and calibration requirements."""

from __future__ import annotations

from typing import Any

from dpsim.core.family_support import FamilySupportRecord, family_support_record
from dpsim.datatypes import PolymerFamily


def support_markdown(record: FamilySupportRecord) -> str:
    """Return compact Markdown for a family support row."""
    lines = [
        f"**Family:** `{record.family.value}`",
        f"**Status:** `{record.status.value}`",
        f"**Maximum uncalibrated tier:** `{record.maximum_uncalibrated_tier.value}`",
        f"**Fabrication route:** {record.fabrication_route}",
        f"**M2 compatibility:** {record.m2_compatibility}",
        f"**M3 pressure support:** `{record.m3_pressure_support.value}`",
        "",
        "**Required calibration before quantitative claims:**",
    ]
    lines.extend(f"- {item}" for item in record.calibration_requirements)
    if record.limitations:
        lines.extend(["", "**Limitations:**"])
        lines.extend(f"- {item}" for item in record.limitations)
    return "\n".join(lines)


def render_family_support_panel(
    family: PolymerFamily | str,
    *,
    container: Any = None,
) -> None:
    """Render the support registry row in Streamlit."""
    if container is None:
        import streamlit as st

        container = st
    container.markdown(support_markdown(family_support_record(family)))


__all__ = ["render_family_support_panel", "support_markdown"]
