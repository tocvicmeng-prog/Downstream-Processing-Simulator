"""Parametric CAD geometry generator for DPSim CFD validation.

Generates STEP AP242 files (importable as fully editable parts in SolidWorks
2018+) and STL meshes. Dimensions sourced from ``src/dpsim/datatypes.py``,
2026-03-27 measurement photos, and 2026-05-01 user corrections.

Run:
  .venv/Scripts/python.exe cad/scripts/build_geometry.py
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import cadquery as cq

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

OUT = Path(__file__).resolve().parents[1] / "output"
OUT.mkdir(parents=True, exist_ok=True)

STL_TOL_MM = 0.05


# --------------------------------------------------------------------------- #
# Stirrer A — disk-style 19-tab impeller
# --------------------------------------------------------------------------- #
def build_stirrer_A() -> cq.Workplane:
    """Disk-style impeller, 19 tangential-facing tabs alternating up/down.

    Per 2026-05-01 user corrections (v3):
      - Original construction: a flat circular plate Ø59 mm. Tab outlines
        are cut around the EDGE of the plate, then each tab is bent UP or
        DOWN perpendicular (90°) to the disk plane.
      - 19 tabs total. 10 bent UP (above disk), 9 bent DOWN, alternating
        around the circumference.
      - Tab face after bending is in the **tangential-axial plane**
        (perpendicular to the radius vector at that location) — NOT in the
        radial-axial plane. The tab is a tangential wall, not a radial
        paddle.
      - Each tab face is angled 10° from purely tangential (toward radial)
        — the fan-pitch that drives flow when the disk rotates. All tabs
        are pitched in the same rotational sense (consistent with the
        engraved rotation arrow on the disk).
      - 18 mm = total axial span from top of UP-fin tips to bottom of
        DOWN-fin tips. With 1 mm disk thickness → each fin's axial height
        ≈ 8.5 mm.
      - No outer lip; zero gap between tab base and disk.
    """
    D_outer = 59.0
    D_shaft = 8.0
    disk_thick = 1.0
    n_tabs = 19
    fin_tangential = 9.0    # tangential width of each tab base (along disk circumference)
    fin_axial = 8.5         # axial height of each tab after bending
    fin_thick = 1.0         # sheet metal thickness (radial dimension after bend)
    fan_pitch_deg = 10.0    # face angle from purely tangential (toward radial)
    # Per 2026-05-01 v5 user correction: fin outline is a true parallelogram.
    # Both leading and trailing edges are parallel, tilted forward at ~85°
    # from disc surface (i.e., 5° forward shear from the vertical/axial
    # direction). The top edge is parallel to the bottom edge.
    edge_tilt_deg = 5.0     # forward shear of leading & trailing edges from vertical
    shaft_length = 120.0

    R_outer = D_outer / 2.0
    R_shaft = D_shaft / 2.0

    # Flat disk with central shaft hole
    disk = (
        cq.Workplane("XY")
        .circle(R_outer)
        .circle(R_shaft)
        .extrude(disk_thick)
        .translate((0, 0, -disk_thick / 2.0))
    )
    # Shaft above disk
    shaft = (
        cq.Workplane("XY")
        .circle(R_shaft)
        .extrude(shaft_length)
        .translate((0, 0, disk_thick / 2.0))
    )
    assembly = disk.union(shaft)

    angle_step = 360.0 / n_tabs   # ~18.95°
    edge_shift = fin_axial * math.tan(math.radians(edge_tilt_deg))  # ~0.74 mm
    for i in range(n_tabs):
        angle_deg = i * angle_step
        going_up = (i % 2 == 0)
        # Tab outline: parallelogram in YZ plane (Y=tangential, Z=axial),
        # extruded radially by fin_thick mm. "+Y" = forward (rotation direction).
        # Both leading and trailing edges tilt forward by edge_tilt_deg.
        #   Bottom-rear (BR):    (-fin_tang/2, 0)
        #   Bottom-forward (BF): (+fin_tang/2, 0)
        #   Top-forward (TF):    (+fin_tang/2 + edge_shift, fin_axial)
        #   Top-rear (TR):       (-fin_tang/2 + edge_shift, fin_axial)
        v_BR = (-fin_tangential / 2.0, 0)
        v_BF = (+fin_tangential / 2.0, 0)
        v_TF = (+fin_tangential / 2.0 + edge_shift, fin_axial)
        v_TR = (-fin_tangential / 2.0 + edge_shift, fin_axial)
        profile = (
            cq.Workplane("YZ")
            .moveTo(*v_BR)
            .lineTo(*v_BF)
            .lineTo(*v_TF)
            .lineTo(*v_TR)
            .close()
        )
        # Extrude radially: in YZ workplane, extrude direction is +X (radial outward)
        tab = profile.extrude(fin_thick).translate((R_outer - fin_thick, 0, 0))
        # Mirror to below-disk for DOWN tabs by flipping Z
        if not going_up:
            tab = tab.mirror("XY")
            tab = tab.translate((0, 0, -disk_thick / 2.0))
        else:
            tab = tab.translate((0, 0, disk_thick / 2.0))

        # Apply fan pitch: rotate about the tab's axial centerline.
        x_centroid = R_outer - fin_thick / 2.0
        pivot1 = (x_centroid, 0, 0)
        pivot2 = (x_centroid, 0, 1)
        tab = tab.rotate(pivot1, pivot2, fan_pitch_deg)
        # Rotate to angular position around disk axis
        tab = tab.rotate((0, 0, 0), (0, 0, 1), angle_deg)
        assembly = assembly.union(tab)

    return assembly


# --------------------------------------------------------------------------- #
# Stirrer B — rotor with tapered offset fingers
# --------------------------------------------------------------------------- #
def build_stirrer_B_rotor() -> cq.Workplane:
    """Stirrer B rotor: flat lance-shape "+" sheet with offset finger pairs.

    Per 2026-05-01 user correction (v3, after re-examining bottom photo):
      - Cross-blade is a flat sheet-metal "+" (NOT chunky tapered bars)
      - Each of the 4 fingers is LANCEOLATE: wider at the root (near
        center), tapering to a sharp pointed tip at the outer edge
      - All 4 fingers are co-planar (sheet thickness 2 mm axial)
      - 180°-paired fingers are parallel-but-not-coincident: each finger
        is offset perpendicular to its length so its centerline does not
        pass through the geometric shaft axis
      - Finger root width ~3 mm, tip width ~0.5 mm (nearly pointed)

    Source: datatypes.py:330 rotor_stator_B
      - Cross-blade root Ø 8.5 mm → tip Ø 25.7 mm
      - 4 arms, blade_thickness 2 mm
    """
    R_shaft = 8.5 / 2.0           # 4.25 mm
    R_tip = 25.7 / 2.0            # 12.85 mm
    finger_root_width = 3.0       # tangential width at root
    # Per 2026-05-01 v6 user correction: leading edge is NOT pointed.
    # Fingers taper from 3 mm root to 2 mm flat outer edge.
    finger_tip_width = 2.0        # tangential width at flat (blunt) tip
    finger_offset = 1.0           # perpendicular offset from shaft centerline
    # 180° finger pairs are parallel-but-not-coincident: each finger's
    # centerline is shifted perpendicular to its length by ±offset, so
    # opposing fingers don't share a common axis.
    # Per 2026-05-01 v4 user correction: finger axial extent ≈ inner stator
    # height (stator H = 18 mm − closed top 1.5 mm = 16.5 mm inner cavity).
    # Lower edge of fingers starts at z=0 (= bottom of shaft = open bottom
    # of stator). 0.5 mm clearance to the closed top → fingers extend to
    # z = 16 mm.
    z_finger_bot = 0.0
    z_finger_top = 16.0
    finger_axial = z_finger_top - z_finger_bot
    shaft_length_above = 80.0

    # Central shaft passes through the entire rotor body and extends above
    shaft = (
        cq.Workplane("XY")
        .circle(R_shaft)
        .extrude(z_finger_top + shaft_length_above)
    )
    rotor = shaft

    # Build cross-blade as ONE closed 2D outline that wraps around the shaft.
    # Each finger has 4 corners (inner_trailing, outer_trailing, outer_leading,
    # inner_leading) defined relative to its own CCW direction. With each
    # finger's centerline shifted perpendicular by `finger_offset`, opposing
    # 180° finger pairs are parallel-but-not-coincident.
    half_root = finger_root_width / 2.0   # 1.5 mm
    half_tip = finger_tip_width / 2.0     # 1.0 mm (flat blunt tip, NOT pointed)
    R_neck = R_shaft + 0.5                # 4.75 mm

    # Compute corner coordinates for each finger
    # F0 (+X dir, centerline Y = -finger_offset)
    F0_in_trail = (R_neck, -finger_offset - half_root)
    F0_out_trail = (R_tip, -finger_offset - half_tip)
    F0_out_lead = (R_tip, -finger_offset + half_tip)
    F0_in_lead = (R_neck, -finger_offset + half_root)
    # F1 (+Y dir, centerline X = +finger_offset)
    F1_in_trail = (+finger_offset + half_root, R_neck)
    F1_out_trail = (+finger_offset + half_tip, R_tip)
    F1_out_lead = (+finger_offset - half_tip, R_tip)
    F1_in_lead = (+finger_offset - half_root, R_neck)
    # F2 (-X dir, centerline Y = +finger_offset)
    F2_in_trail = (-R_neck, +finger_offset + half_root)
    F2_out_trail = (-R_tip, +finger_offset + half_tip)
    F2_out_lead = (-R_tip, +finger_offset - half_tip)
    F2_in_lead = (-R_neck, +finger_offset - half_root)
    # F3 (-Y dir, centerline X = -finger_offset)
    F3_in_trail = (-finger_offset - half_root, -R_neck)
    F3_out_trail = (-finger_offset - half_tip, -R_tip)
    F3_out_lead = (-finger_offset + half_tip, -R_tip)
    F3_in_lead = (-finger_offset + half_root, -R_neck)

    # Connecting arcs between adjacent fingers' inner-leading and next
    # finger's inner-trailing necks. Negative radius makes the arc concave
    # toward the shaft (wrapping around it).
    R_arc = -R_neck   # negative: concave toward origin

    profile = (
        cq.Workplane("XY")
        .moveTo(*F0_in_trail)
        .lineTo(*F0_out_trail)
        .lineTo(*F0_out_lead)
        .lineTo(*F0_in_lead)
        .radiusArc(F1_in_trail, R_arc)
        .lineTo(*F1_out_trail)
        .lineTo(*F1_out_lead)
        .lineTo(*F1_in_lead)
        .radiusArc(F2_in_trail, R_arc)
        .lineTo(*F2_out_trail)
        .lineTo(*F2_out_lead)
        .lineTo(*F2_in_lead)
        .radiusArc(F3_in_trail, R_arc)
        .lineTo(*F3_out_trail)
        .lineTo(*F3_out_lead)
        .lineTo(*F3_in_lead)
        .radiusArc(F0_in_trail, R_arc)
        .close()
    )
    crossblade = profile.extrude(finger_axial).translate((0, 0, z_finger_bot))
    # Per 2026-05-01 v7 user correction: smooth the root transition between
    # finger and shaft by filleting the vertical (|Z) edges of the cross-
    # blade. Targets the 8 inner-neck edges plus the 8 outer-tip-corner
    # edges. Filleting the entire blade shape produces smoother visual and
    # CFD-friendly transitions; the inner-neck fillets are the ones that
    # blend the finger root into the connecting arc.
    try:
        crossblade = crossblade.edges("|Z").fillet(1.0)
    except Exception:
        # If global fillet fails, try a smaller radius
        try:
            crossblade = crossblade.edges("|Z").fillet(0.5)
        except Exception:
            pass
    rotor = rotor.union(crossblade)

    return rotor


# --------------------------------------------------------------------------- #
# Stirrer B — stator with center hole in top
# --------------------------------------------------------------------------- #
def build_stirrer_B_stator() -> cq.Workplane:
    """Stirrer B stator: closed top with center shaft-passage hole.

    Per 2026-05-01 user correction:
      - Top is closed except for a center hole slightly larger than the
        rotor's drive-shaft diameter (Ø 8.5 mm shaft → Ø 10 mm hole).
    """
    OD = 32.03
    WALL = 2.2
    ID = OD - 2 * WALL
    H = 18.0
    PERF_D = 3.0
    TOP_THICK = 1.5
    SHAFT_HOLE_D = 10.0          # slightly > 8.5 mm rotor shaft

    # Build closed cylinder
    stator_outer = cq.Workplane("XY").circle(OD / 2.0).extrude(H)
    # Inner bore (cuts everything except the closed top)
    stator_bore = (
        cq.Workplane("XY")
        .workplane(offset=-0.01)
        .circle(ID / 2.0)
        .extrude(H - TOP_THICK + 0.01)
    )
    stator = stator_outer.cut(stator_bore)
    # Center shaft-passage hole through the closed top
    shaft_hole = (
        cq.Workplane("XY")
        .workplane(offset=H - TOP_THICK - 0.01)
        .circle(SHAFT_HOLE_D / 2.0)
        .extrude(TOP_THICK + 0.02)
    )
    stator = stator.cut(shaft_hole)

    # Perforations: 36 holes (3 rows × 12 columns, uniform rectangular grid)
    n_perf_circ = 12
    n_perf_rows = 3
    angle_step = 360.0 / n_perf_circ
    row_spacing = (H - TOP_THICK) / (n_perf_rows + 1)
    z_rows = [(i + 1) * row_spacing for i in range(n_perf_rows)]
    hole_length = WALL + 2.0
    hole_start_x = ID / 2.0 - 1.0
    for z in z_rows:
        for j in range(n_perf_circ):
            angle_deg = j * angle_step
            hole_solid = (
                cq.Workplane("YZ")
                .circle(PERF_D / 2.0)
                .extrude(hole_length)
                .translate((hole_start_x, 0, z))
                .rotate((0, 0, 0), (0, 0, 1), angle_deg)
            )
            stator = stator.cut(hole_solid)

    return stator


# --------------------------------------------------------------------------- #
# Beaker — Ø100 × 130 mm with bottom fillet + outward-flared rim
# --------------------------------------------------------------------------- #
def build_beaker() -> cq.Workplane:
    """Beaker with R=10 mm inner-bottom fillet and 20° outward-flared rim.

    Per 2026-05-01 user correction:
      - Inner bottom-to-wall corner: R = 10 mm fillet (transition arc)
      - Top rim: outward curve at 20° from vertical, extending 5 mm radially
    """
    ID = 100.0
    WALL = 1.5
    H = 130.0
    OD = ID + 2 * WALL
    BASE_THICK = 2.5
    BOTTOM_FILLET = 10.0
    FLARE_HEIGHT = 5.0 / math.tan(math.radians(20.0))   # axial extent of flare
    # Hmm — user said flare extends 5 mm OUTWARD, at 20° from vertical.
    # So the flare RADIAL component = 5 mm. AXIAL = 5 / tan(20°) ≈ 13.7 mm.
    # That feels too tall; re-interpret as radial extension = 5 mm with the
    # flared section extending until it has gained 5 mm of radius.
    flare_dr = 5.0
    flare_dz = flare_dr / math.tan(math.radians(20.0))   # 13.74 mm axial

    # Use a revolution-based construction: define the inner profile as a
    # 2D sketch in the XZ plane, then revolve about the Z axis.
    # Profile: outer edge from (R_outer_base, 0) → (R_outer_base, H_main) →
    # flared rim → top inner edge → ... → back to start.
    # Simpler: build the wall by revolving a closed polyline that defines
    # the cross-section.
    #
    # Cross-section (radius vs. height):
    #   z=0 to z=BASE_THICK: solid base from r=0 to r=OD/2
    #   z=BASE_THICK: the start of the inner cavity at r=ID/2, with R=10
    #     fillet rounding to r=0 at z=BASE_THICK+10 (no, fillet is between
    #     the inner wall and the inner base — only the inside corner)
    #   At the top, the wall flares outward.
    #
    # We'll build by:
    #   1. Construct outer body as cylinder OD x H, then add base.
    #   2. Cut inner cavity with 2D revolution profile that has the 10mm
    #      bottom fillet.
    #   3. Add a flared rim at the top.
    H_straight = H - flare_dz   # height before the flare starts

    # Outer body: straight cylinder + flared top + R=5 mm fillet at outer
    # bottom corner (smooth transition from outer bottom to outer wall).
    OUTER_BOTTOM_FILLET = 5.0
    profile = (
        cq.Workplane("XZ")
        .moveTo(0, 0)
        .lineTo(OD / 2.0 - OUTER_BOTTOM_FILLET, 0)
        .radiusArc((OD / 2.0, OUTER_BOTTOM_FILLET), -OUTER_BOTTOM_FILLET)
        .lineTo(OD / 2.0, H_straight)
        .lineTo(OD / 2.0 + flare_dr, H)
        .lineTo(0, H)
        .close()
    )
    body = profile.revolve(360, (0, 0, 0), (0, 1, 0))

    # Inner cavity profile (with R=10 fillet at the inner bottom corner)
    # We define the cavity from the inside as a 2D profile in XZ plane.
    # Inner bottom: starts at center, rises to r=ID/2 with the 10mm fillet.
    # We construct the cavity profile as straight lines + a fillet later.
    R_in = ID / 2.0
    # Path: start at (0, BASE_THICK), go to (R_in - BOTTOM_FILLET, BASE_THICK),
    # arc to (R_in, BASE_THICK + BOTTOM_FILLET), straight up to (R_in, H_straight),
    # then flare outward to (R_in + flare_dr, H), then close back along top.
    cavity_pts = [
        (0, BASE_THICK),
        (R_in - BOTTOM_FILLET, BASE_THICK),
    ]
    # Use radiusArc for clean quarter-circle fillet at inner-bottom corner.
    # Arc center is at (R_in - R_fillet, BASE_THICK + R_fillet); start at
    # (R_in - R_fillet, BASE_THICK) on horizontal floor; end at
    # (R_in, BASE_THICK + R_fillet) on inner wall. Arc curves outward (CCW).
    cavity = (
        cq.Workplane("XZ")
        .moveTo(0, BASE_THICK)
        .lineTo(R_in - BOTTOM_FILLET, BASE_THICK)
        .radiusArc((R_in, BASE_THICK + BOTTOM_FILLET), -BOTTOM_FILLET)
        .lineTo(R_in, H_straight)
        .lineTo(R_in + flare_dr, H + 0.5)
        .lineTo(0, H + 0.5)
        .close()
    )
    cavity_solid = cavity.revolve(360, (0, 0, 0), (0, 1, 0))
    beaker = body.cut(cavity_solid)
    return beaker


# --------------------------------------------------------------------------- #
# Jacketed vessel — closed top, inner-bottom fillet, fillets on closure
# --------------------------------------------------------------------------- #
def build_jacketed_vessel() -> cq.Workplane:
    """Jacketed vessel with closed top + shaft hole + bottom + closure fillets.

    Per 2026-05-01 user correction:
      - Closed top connecting inner and outer walls
      - Right-angle corners on the closure get R = 5 mm fillets
      - Inner-wall-to-inner-bottom junction: R = 10 mm fillet
      - Top has a center hole for the stirring shaft (Ø 12 mm assumed)
    """
    INNER_ID = 92.0
    INNER_WALL = 1.0
    JACKET_GAP = 8.0
    OUTER_WALL = 1.0
    H = 160.0
    BASE_THICK = 3.0
    TOP_THICK = 3.0                  # closed top thickness
    BOTTOM_FILLET = 10.0
    CLOSURE_FILLET = 5.0
    SHAFT_HOLE_D = 12.0              # generous clearance for stirring shaft
    STUB_OD = 8.0
    STUB_ID = 6.0
    STUB_LENGTH = 25.0

    inner_OD = INNER_ID + 2 * INNER_WALL
    outer_ID = inner_OD + 2 * JACKET_GAP
    outer_OD = outer_ID + 2 * OUTER_WALL

    # Build via revolution profile to control fillets cleanly.
    # Cross-section (positive X half) of the jacketed vessel:
    #   Outer edge: r=outer_OD/2 from z=0 to z=H
    #   Top: closed across from outer to inner with a flat region
    #   Inner bore: r=INNER_ID/2 from z=H to z=BASE_THICK (going down)
    #   Inner bottom corner with R=10 fillet
    #   Annular jacket cavity inside the walls
    R_in = INNER_ID / 2.0
    R_inO = inner_OD / 2.0
    R_outI = outer_ID / 2.0
    R_outO = outer_OD / 2.0

    # The vessel body (positive X half cross-section, then revolved):
    # Closed envelope: outer cylinder + inner cylinder + base + top + shaft hole
    # Outer body now uses a R=5 mm curved transition between the outer
    # bottom and outer wall (per 2026-05-01 user correction).
    OUTER_BOTTOM_FILLET = 5.0
    outer_profile = (
        cq.Workplane("XZ")
        .moveTo(0, 0)
        .lineTo(R_outO - OUTER_BOTTOM_FILLET, 0)
        .radiusArc((R_outO, OUTER_BOTTOM_FILLET), -OUTER_BOTTOM_FILLET)
        .lineTo(R_outO, H)
        .lineTo(0, H)
        .close()
    )
    outer_solid = outer_profile.revolve(360, (0, 0, 0), (0, 1, 0))
    # Jacket cavity: annular gap between R=R_inO and R=R_outI, from z=BASE_THICK
    # to z=H-TOP_THICK
    jacket_outer = (
        cq.Workplane("XY")
        .workplane(offset=BASE_THICK)
        .circle(R_outI)
        .extrude(H - BASE_THICK - TOP_THICK)
    )
    jacket_inner = (
        cq.Workplane("XY")
        .workplane(offset=BASE_THICK - 0.01)
        .circle(R_inO)
        .extrude(H - BASE_THICK - TOP_THICK + 0.02)
    )
    jacket_cavity = jacket_outer.cut(jacket_inner)
    body = outer_solid.cut(jacket_cavity)
    # Inner bore through the inner glass wall, with R=10 fillet at base.
    # Revolve a 2D profile: starts at (0, BASE_THICK), goes to
    # (R_in - 10, BASE_THICK), arcs to (R_in, BASE_THICK + 10), straight up,
    # closes through center at top.
    cavity = (
        cq.Workplane("XZ")
        .moveTo(0, BASE_THICK)
        .lineTo(R_in - BOTTOM_FILLET, BASE_THICK)
        .radiusArc((R_in, BASE_THICK + BOTTOM_FILLET), -BOTTOM_FILLET)
        .lineTo(R_in, H + 0.5)
        .lineTo(0, H + 0.5)
        .close()
    )
    cavity_solid = cavity.revolve(360, (0, 0, 0), (0, 1, 0))
    body = body.cut(cavity_solid)

    # Center shaft hole through the closed top (Ø SHAFT_HOLE_D)
    shaft_hole = (
        cq.Workplane("XY")
        .workplane(offset=H - TOP_THICK - 0.01)
        .circle(SHAFT_HOLE_D / 2.0)
        .extrude(TOP_THICK + 0.02)
    )
    body = body.cut(shaft_hole)

    # Apply R=5 mm fillets to right-angle edges of the closure (top)
    try:
        body = body.faces(">Z").edges().fillet(CLOSURE_FILLET)
    except Exception:
        # Fallback: try without face filter
        try:
            body = body.edges("not(|Z)").fillet(CLOSURE_FILLET)
        except Exception:
            pass

    # Hose stubs (illustrative)
    for z, angle in [(30.0, 0.0), (130.0, 180.0)]:
        stub = (
            cq.Workplane("YZ")
            .circle(STUB_OD / 2.0)
            .extrude(STUB_LENGTH)
            .translate((R_outO - 0.5, 0, z))
            .rotate((0, 0, 0), (0, 0, 1), angle)
        )
        stub_bore = (
            cq.Workplane("YZ")
            .circle(STUB_ID / 2.0)
            .extrude(STUB_LENGTH + 1.0)
            .translate((R_outO - 1.0, 0, z))
            .rotate((0, 0, 0), (0, 0, 1), angle)
        )
        body = body.union(stub).cut(stub_bore)

    return body


# --------------------------------------------------------------------------- #
# Export driver
# --------------------------------------------------------------------------- #
def export(part: cq.Workplane, name: str) -> None:
    step_path = OUT / f"{name}.step"
    stl_path = OUT / f"{name}.stl"
    cq.exporters.export(part, str(step_path), exportType="STEP")
    cq.exporters.export(part, str(stl_path), exportType="STL", tolerance=STL_TOL_MM)
    print(f"  ✓ {name}")


def main() -> None:
    print("DPSim CFD geometry generator (v2 — 2026-05-01 corrections)")
    print("=" * 60)
    print(f"Output: {OUT}")
    print(f"STL deflection: {STL_TOL_MM} mm")
    print()

    print("Building parts...")

    a = build_stirrer_A()
    export(a, "stirrer_A_pitched_blade")

    rotor_b = build_stirrer_B_rotor()
    export(rotor_b, "stirrer_B_rotor")

    stator_b = build_stirrer_B_stator()
    export(stator_b, "stirrer_B_stator")

    beaker = build_beaker()
    export(beaker, "beaker_100mm")

    jacket = build_jacketed_vessel()
    export(jacket, "jacketed_vessel_92mm")

    print()
    print("Done.")


if __name__ == "__main__":
    main()
