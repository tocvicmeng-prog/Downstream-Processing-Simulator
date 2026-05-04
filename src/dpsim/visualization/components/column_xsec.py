"""ColumnCrossSection — packed-bed chromatography longitudinal cross-section.

Embedded animated SVG side-view of a packed-bed affinity column with a
moving "buffer front" that recolours microspheres as it passes —
visualising the four operational phases of a chromatography cycle:

- **load** — teal liquid front; microspheres turn from empty → bound
  (filled). Streaming dots are off (target is being captured).
- **wash** — pale-blue liquid front; bound payload retained on beads;
  impurities flush as gray streaming dots out the bottom.
- **elute** — amber liquid front; bound payload releases AND streams
  out as teal dots (eluate target concentration).
- **cip** — magenta liquid front; everything strips off; magenta
  streaming dots represent stripped residuals.

Per the SA Q2 sign-off in ``SA_v0_4_0_RUSHTON_FIDELITY.md``: the visual
keeps BOTH bead recolour (bound payload concentration on resin) AND
distinct streaming dots (eluate / wash / CIP outflow), with
phase-dependent legend labels so the meaning is unambiguous.

Phase tab state is communicated via the ``phase`` template substitution
(URL-param-style; the iframe re-renders on phase change). This avoids
the postMessage round-trip and keeps the iframe stateless.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final, Literal

from ._html_helper import render_inline_html

ColumnPhase = Literal["load", "wash", "elute", "cip"]

_ASSET_PATH: Final[Path] = Path(__file__).parent / "assets" / "column_xsec.html"

_DEFAULT_WIDTH: Final[int] = 280
_DEFAULT_HEIGHT: Final[int] = 360


def render_column_xsec(
    *,
    phase: ColumnPhase = "load",
    width: int = _DEFAULT_WIDTH,
    height: int = _DEFAULT_HEIGHT,
    column_length_mm: float = 150.0,
    column_diameter_mm: float = 11.0,
    bed_fraction: float = 0.78,
    particle_count: int = 92,
    light_theme: bool = False,
) -> None:
    """Render the column cross-section into the current Streamlit slot.

    Args:
        phase: Operating phase. Drives buffer-front colour, streaming-
            dot semantics, bead-recolour rule, and the legend label.
        width: Iframe width in px.
        height: Iframe height in px.
        column_length_mm: Bed length, surfaced in the legend.
        column_diameter_mm: Inner diameter, surfaced in the legend.
        bed_fraction: Bed length as a fraction of the column. The
            remainder is split between inlet manifold + frit + outlet
            manifold + frit. Default 0.78 matches typical lab-scale
            geometry (e.g. ~5 mm inlet manifold + ~117 mm bed in a
            150-mm column).
        particle_count: Number of microspheres drawn. Default 92.
        light_theme: When ``True``, use the light-theme palette.
    """
    template = _ASSET_PATH.read_text(encoding="utf-8")
    html = (
        template.replace("__PHASE__", str(phase))
        .replace("__WIDTH__", str(int(width)))
        .replace("__HEIGHT__", str(int(height)))
        .replace("__COLUMN_LENGTH_MM__", f"{column_length_mm:.1f}")
        .replace("__COLUMN_DIAMETER_MM__", f"{column_diameter_mm:.1f}")
        .replace("__BED_FRACTION__", f"{bed_fraction:.3f}")
        .replace("__PARTICLE_COUNT__", str(int(particle_count)))
        .replace("__THEME__", "light" if light_theme else "dark")
    )
    render_inline_html(html, height_px=height + 40, scrolling=False)
