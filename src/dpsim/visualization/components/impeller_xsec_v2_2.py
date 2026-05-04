"""ImpellerCrossSection v2.2 — disk-style 19-tab Stirrer A in glass beaker.

Successor to v2 with first-principles fluid-mechanics fidelity. Differences
from v2 (commit a8b7c57 / 2044e7f, v0.6.0) called out below.

Changes vs v2
-------------

1. **Beaker rim** (CAD verified 2026-05-01): redrawn with 20° outward flare
   over a 5 mm flare height plus an outer-rim curl. The v2 beaker was a
   straight cylinder with a simplified step at the top.

2. **Stirrer A side-view geometry**: redrawn as a thin (1 mm) horizontal
   disk with **two perimeter tabs visible in cross-section** — one bent
   UP at the left edge, one bent DOWN at the right edge. The v2 rendering
   showed the disk as a horizontal bar with vertical tab-rectangles spread
   across the entire diameter (anatomically wrong — the 19 tabs are at
   the perimeter only, and only the front-most pair are in the cutting
   plane).

3. **Zone-shaded backgrounds** matching the v0.6.2 ``zones.json`` schema
   (Appendix K §K.2): impeller swept volume (orange tint, ε_brk ≈ 110
   W/kg), near-wall strips (slate, ε_avg ≈ 8.5), bulk (default, ε_avg
   ≈ 4.8). Teaches the per-zone ε partitioning that the integrator uses.

4. **Three distinct collision types** rendered as pulsing glyphs:
   - ★ droplet–impeller break-up (most frequent, in impeller zone).
   - ✦ droplet–wall impact (less frequent, near-wall only).
   - ⊕ droplet–droplet coalescence (slow, in bulk only).
   The v2 only showed break-up at the impeller, missing wall impacts and
   coalescence — the latter is the dominant event in bulk per the
   Coulaloglou-Tavlarides kernel (Appendix K §K.2.2).

5. **Asymmetric upper/lower recirculation**: upper figure-8 loops are
   drawn slightly taller than lower loops to honour the net upward axial
   bias from the 10 UP / 9 DOWN tab imbalance.

Geometry (verified 2026-05-01 against ``cad/output/`` STEP files):

    Stirrer A — Ø 59 mm flat disk × 1 mm thick, 19 perimeter tabs
                (10 UP + 9 DOWN, alternating; 90° perpendicular bend;
                10° tangential fan-pitch; tab dim 9 × 8.5 × 1 mm).
    Beaker   — Ø 100 mm inner × 130 mm tall, R=10 mm inner-bottom fillet,
                R=5 mm outer-bottom fillet, 20° outward-flared rim with
                5 mm flare height.

References
----------

- Tatterson G. B. (1991). *Fluid Mixing and Gas Dispersion in Agitated
  Tanks.* McGraw-Hill. — flow-pattern classification for radial-flow
  impellers; the disk-style alternating-tab geometry classifies as a
  serrated-disk variant with dominant radial discharge plus weak axial
  pumping.
- Wu H., Patterson G. K. (1989). *Laser-Doppler measurements of
  turbulent-flow parameters in a stirred mixer.* Chem. Eng. Sci. 44,
  2207–2221. — trailing-vortex pair behind each impeller blade; the
  high-ε breakage zone.
- Padron G., Hall S., Cooke M., et al. (Padron 2005 PhD; Hall 2011
  Can. J. Chem. Eng. 89, 1040–1050). — referenced for context on the
  rotor-stator family (used by ``impeller_xsec_v3`` for Stirrer B).
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from ._html_helper import render_inline_html

_ASSET_PATH: Final[Path] = (
    Path(__file__).parent / "assets" / "impeller_xsec_v2_2.html"
)

_DEFAULT_WIDTH: Final[int] = 320
_DEFAULT_HEIGHT: Final[int] = 380


def render_impeller_xsec_v2_2(
    *,
    rpm: float = 1300.0,
    width: int = _DEFAULT_WIDTH,
    height: int = _DEFAULT_HEIGHT,
    light_theme: bool = False,
) -> None:
    """Render the v2.2 Stirrer A cross-section into the current Streamlit slot.

    API-compatible with :func:`render_impeller_xsec_v2`.

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
    render_inline_html(html, height_px=height + 8, scrolling=False)
