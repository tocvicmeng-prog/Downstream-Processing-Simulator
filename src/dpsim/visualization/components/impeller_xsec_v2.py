"""ImpellerCrossSection v2 — disk-style 19-tab Stirrer A in glass beaker.

Embedded animated SVG with a four-state toggle button cycling through:

    1. side-view cross-section · opaque agitator
    2. bottom-up cross-section · opaque agitator
    3. side-view cross-section · transparent agitator (emphasises flow +
       droplet collisions)
    4. bottom-up cross-section · transparent agitator

Geometry sourced from ``cad/scripts/build_geometry.py`` (verified
2026-05-01 against measurement photos):

    Stirrer A — Ø 59 mm flat disk, 1 mm thick, 19 perimeter tabs
                (10 UP + 9 DOWN, alternating; 90° perpendicular bend;
                10° tangential fan-pitch).
    Beaker   — Ø 100 mm inner, 130 mm tall, R=10 mm inner-bottom fillet,
                R=5 mm outer-bottom fillet, 20° outward-flared rim.

Drop-in replacement for ``render_impeller_xsec`` when Stirrer A is
selected. The legacy Rushton component remains for the rotor-stator
hardware mode.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import streamlit.components.v1 as components

_ASSET_PATH: Final[Path] = (
    Path(__file__).parent / "assets" / "impeller_xsec_v2.html"
)

_DEFAULT_WIDTH: Final[int] = 320
_DEFAULT_HEIGHT: Final[int] = 380   # +20 px vs. v1 to fit toggle button


def render_impeller_xsec_v2(
    *,
    rpm: float = 1300.0,
    width: int = _DEFAULT_WIDTH,
    height: int = _DEFAULT_HEIGHT,
    light_theme: bool = False,
) -> None:
    """Render the v2 impeller cross-section into the current Streamlit slot.

    Args:
        rpm: Stirrer rotation speed (RPM). Drives the on-screen rotation
            cadence; capped to a legible range for visualisation.
        width: Iframe width in px.
        height: Iframe height in px (extra +20 px over v1 to host the
            toggle button at top-right).
        light_theme: When ``True``, render with the light-theme palette.
    """
    template = _ASSET_PATH.read_text(encoding="utf-8")
    html = (
        template.replace("__RPM__", f"{rpm:.2f}")
        .replace("__WIDTH__", str(int(width)))
        .replace("__HEIGHT__", str(int(height)))
        .replace("__THEME__", "light" if light_theme else "dark")
    )
    components.html(html, height=height + 8, scrolling=False)
