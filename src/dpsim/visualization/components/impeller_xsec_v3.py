"""ImpellerCrossSection v3 — small rotor-stator (Stirrer B) in glass beaker.

Replaces the legacy ``impeller_xsec`` (Rushton turbine in BSTR) for the
Stirrer B hardware mode. The legacy component drew a six-blade Rushton
disk in a fully baffled tank — completely wrong instrument geometry for
the Ø 32 mm rotor-stator with 72 perforations actually used.

This v3 component renders:

- **Cross rotor** (4 arms, Ø 25.7 mm × 16 mm tall) inside the stator
  housing.
- **Perforated stator** (Ø 32.03 × 18 mm, 72 Ø 3 mm perforations in a
  3 × 24 grid, closed top with Ø 10 mm shaft passage, open bottom).
- **Bench-loop circulation**: rotor pulls fluid axially in through the
  open stator bottom, accelerates it centrifugally through the rotor
  swept volume, ejects it radially through the 72 perforations as
  high-velocity slot-exit jets, which then circulate back through bulk
  to feed the rotor inlet from below.
- **Slot-exit zone** (ε_brk ≈ 1200 W/kg) shaded distinctly — this is
  where 80–95 % of breakage occurs (Padron 2005, Hall 2011).
- **Three collision types** (★ break / ✦ wall / ⊕ coalesce) with the
  break-up event dominating at the slot exits, not the impeller.

Geometry (verified 2026-05-01 against ``cad/output/`` STEP files):

    Stirrer B rotor — flat sheet "+" with offset finger pairs, root
        Ø 8.5 mm → tip Ø 25.7 mm, R=1 mm fillets, 16 mm axial extent.
    Stirrer B stator — Ø 32.03 mm × 18 mm tall, 2.2 mm wall, closed top
        with Ø 10 mm shaft passage, open bottom; 72 Ø 3 mm perforations
        in a 3 × 24 rectangular grid.
    Beaker — Ø 100 mm inner × 130 mm tall, 20° outward-flared rim.

Operating point (default rendering): 6000 RPM, paraffin-oil continuous
phase. Re_imp ≈ 70 000 (water-equivalent) — fully turbulent in the slot
exits, transitional in bulk.

References
----------

- Padron G. (2005). *Effect of surfactants on drop size distribution in
  a batch, rotor-stator mixer.* PhD thesis, U. of Maryland. — 80–95 %
  of breakage in slot-exit jets.
- Hall S., Cooke M., Pacek A. W., Kowalski A. J., Rothman D. (2011).
  *Scaling-up of silverson rotor-stator mixers.* Can. J. Chem. Eng. 89,
  1040–1050. — confirmation across rotor-stator scales.
- Utomo A. T., Baker M., Pacek A. W. (2009). *The effect of stator
  geometry on the flow pattern and energy dissipation rate in a
  rotor-stator mixer.* Chem. Eng. Sci. 64, 4426–4439. — stator-geometry
  / Np correlations underpinning the dissipation_ratio = 25 in
  ``StirrerGeometry.rotor_stator_B``.
- Coulaloglou & Tavlarides 1977; Alopaeus 2002. — kernel context for
  breakage / coalescence (Appendix K §K.2).
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from ._html_helper import render_inline_html

_ASSET_PATH: Final[Path] = (
    Path(__file__).parent / "assets" / "impeller_xsec_v3.html"
)

_DEFAULT_WIDTH: Final[int] = 320
_DEFAULT_HEIGHT: Final[int] = 380


def render_impeller_xsec_v3(
    *,
    rpm: float = 6000.0,
    width: int = _DEFAULT_WIDTH,
    height: int = _DEFAULT_HEIGHT,
    light_theme: bool = False,
) -> None:
    """Render the v3 Stirrer B (rotor-stator) cross-section into the slot.

    API-compatible shape with :func:`render_impeller_xsec_v2_2`.

    Args:
        rpm: Stirrer rotation speed (RPM). Drives the rotor-spin cadence
            (capped to a legible range in JS).
        width: Iframe width in px.
        height: Iframe height in px (extra +20 px to host the toggle button).
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
