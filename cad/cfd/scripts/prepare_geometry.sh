#!/usr/bin/env bash
# Convert STEP files in cad/output/ to STL for snappyHexMesh consumption.
# Assemble stirrer + beaker at the correct insertion depth.
#
# Status: TODO. Requires either:
#   (a) FreeCAD CLI: FreeCAD --console --run-python convert.py
#   (b) gmsh: gmsh -3 -format stl input.step -o output.stl
#   (c) CadQuery (already installed in .venv): use cq.exporters.export
#
# Stub for the OpenFOAM CFD-PBE pipeline (cad/cfd/README.md).

set -euo pipefail

CAD_DIR="$(cd "$(dirname "$0")/../.." && pwd)/output"
CASE_DIR="${CASE_DIR:-${CAD_DIR}/../cfd/cases/stirrer_A_beaker_100mL}"

echo "TODO: assemble geometry"
echo "  CAD STEP source: $CAD_DIR"
echo "  Target case dir: $CASE_DIR/constant/triSurface/"
echo
echo "Required steps:"
echo "  1. Position stirrer at correct insertion depth in beaker"
echo "  2. Subtract from beaker interior to get fluid domain"
echo "  3. Export STL files for snappyHexMesh:"
echo "     - rotor.stl (rotating zone surface)"
echo "     - stator.stl (Stirrer B only, static)"
echo "     - vessel.stl (beaker walls, static)"
echo "     - free_surface.stl (top of liquid, treat as slip wall)"
echo
echo "See cad/cfd/README.md for full TODO list."
exit 0
