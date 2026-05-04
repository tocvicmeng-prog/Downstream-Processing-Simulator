"""ImpellerCrossSection — Rushton-disk turbine in a baffled tank (BSTR).

Embedded animated SVG side-view of a Rushton-disk turbine operating in
a fully-baffled cylindrical tank (4 × baffle, B/T = 1/12, full-depth)
with a dished bottom — the "Baker-type" stirring system used for
polysaccharide double-emulsion microsphere fabrication in M1.

The rendering follows the prescriptions in
``docs/handover/SA_v0_4_0_RUSHTON_FIDELITY.md``:

    * Standard Rushton geometry: D/T = 1/3, blade height = D/5,
      symmetric about the disk plane (Rushton 1950).
    * Suppressed surface vortex (small cusp only) — fully-baffled
      tank physics (Nienow 1997).
    * Baffles drawn flush against the wall; plan-view azimuth icon
      top-right resolves the 4-baffle / 90° ambiguity.
    * Trailing-vortex pair behind each blade (Wu & Patterson 1989) —
      this is where most drop-break-up actually occurs (ε_max ≈ 10–50×
      spatial-average ε).
    * Faint shaded high-ε discharge annulus out to ~0.7 R_tank.
    * Droplet size decremented stochastically on each impeller-plane
      passage (Hinze inertial-subrange break-up; Calabrese viscous
      correction is a solver-side concern, not a visual one).
    * f_pass readout: ``f_pass ≈ N_Q · N · (πD³/4) · 4 / V_liquid``,
      with ``N_Q ≈ 0.75`` for Rushton (Calabrese 1986).

References to the underlying papers are repeated inline in the HTML
asset for users who view-source the iframe.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from ._html_helper import render_inline_html

_ASSET_PATH: Final[Path] = Path(__file__).parent / "assets" / "impeller_xsec.html"

# Default visual dimensions. Width is wider than the prototype (200 vs
# 180) to accommodate the standard D/T = 1/3 geometry without the
# diagram looking spindly, per SA §A.2 F-1.
_DEFAULT_WIDTH: Final[int] = 320
_DEFAULT_HEIGHT: Final[int] = 360


def render_impeller_xsec(
    *,
    rpm: float = 420.0,
    width: int = _DEFAULT_WIDTH,
    height: int = _DEFAULT_HEIGHT,
    impeller_d_mm: float = 30.0,
    tank_d_mm: float = 90.0,
    liquid_volume_ml: float = 100.0,
    n_blades: int = 6,
    light_theme: bool = False,
) -> None:
    """Render the impeller cross-section into the current Streamlit slot.

    Args:
        rpm: Stirrer rotation speed, revolutions per minute. Drives blade
            rotation phase, dash-offset on flow lines, surface-cusp
            depth (small under baffled conditions), shear tier, and the
            ``f_pass`` readout.
        width: Iframe width in px.
        height: Iframe height in px.
        impeller_d_mm: Rushton-disk impeller diameter in mm. Default 30.
        tank_d_mm: Tank inner diameter in mm. Default 90 (so D/T = 1/3,
            standard Rushton ratio per Nienow 1997 / Paul 2004).
        liquid_volume_ml: Liquid working volume in mL. Used in the
            ``f_pass`` calculation. Default 100 mL.
        n_blades: Number of blades on the Rushton disk. Default 6 (the
            classic Rushton turbine; 4-blade and 8-blade variants exist
            but are uncommon in lab-scale emulsification).
        light_theme: When ``True``, render with the light-theme palette
            (the iframe applies its own ``.dps-light`` body class).
    """
    template = _ASSET_PATH.read_text(encoding="utf-8")
    html = (
        template.replace("__RPM__", f"{rpm:.2f}")
        .replace("__WIDTH__", str(int(width)))
        .replace("__HEIGHT__", str(int(height)))
        .replace("__IMPELLER_D_MM__", f"{impeller_d_mm:.2f}")
        .replace("__TANK_D_MM__", f"{tank_d_mm:.2f}")
        .replace("__LIQUID_VOLUME_ML__", f"{liquid_volume_ml:.2f}")
        .replace("__N_BLADES__", str(int(n_blades)))
        .replace("__THEME__", "light" if light_theme else "dark")
    )
    render_inline_html(html, height_px=height + 8, scrolling=False)
