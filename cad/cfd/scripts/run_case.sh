#!/usr/bin/env bash
# OpenFOAM case runner: blockMesh → snappyHexMesh → decomposePar →
# pimpleDyMFoam → reconstructPar.
#
# Status: TODO. Requires OpenFOAM v11+ (or .com/.org build with
# pimpleDyMFoam available) and a fully-populated case directory.
#
# Usage: ./run_case.sh <case_directory> [--cores N]

set -euo pipefail

CASE="${1:-}"
CORES="${CORES:-8}"

if [ -z "$CASE" ] || [ ! -d "$CASE" ]; then
    echo "Usage: $0 <case_directory>"
    echo "Example: $0 ../cases/stirrer_A_beaker_100mL"
    exit 1
fi

cd "$CASE"

echo "TODO: implement case execution"
echo "  Case: $CASE"
echo "  Cores: $CORES"
echo
echo "Expected steps once case dictionaries are populated:"
echo "  1. blockMesh                              # background hex mesh"
echo "  2. surfaceFeatureExtract                  # edges from STL"
echo "  3. snappyHexMesh -overwrite               # cut + snap + layer"
echo "  4. checkMesh                              # quality check"
echo "  5. decomposePar                           # split for parallel"
echo "  6. mpirun -n \$CORES pimpleDyMFoam -parallel"
echo "  7. reconstructPar"
echo "  8. python3 ../../scripts/extract_epsilon.py ."
echo
echo "See cad/cfd/README.md for setup details."
exit 0
