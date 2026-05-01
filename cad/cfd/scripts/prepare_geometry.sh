#!/usr/bin/env bash
# prepare_geometry.sh — convert STEP files to STL for snappyHexMesh.
#
# Reads STEP files from cad/output/ (produced by cad/scripts/build_geometry.py),
# triangulates each via gmsh (preferred) or FreeCAD (fallback), and writes
# named-region STL files into the case's constant/triSurface/ directory.
#
# The patch names match the convention used by the OpenFOAM case dicts:
#   vessel_wall, impeller_wall, stator_wall (Stirrer B only).
#
# Usage
# -----
#   prepare_geometry.sh stirrer_A_beaker_100mL
#   prepare_geometry.sh stirrer_B_beaker_100mL
#
# Output
# ------
#   cad/cfd/cases/<case>/constant/triSurface/<patch_name>.stl
set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <case_name>" >&2
    echo "  case_name: stirrer_A_beaker_100mL or stirrer_B_beaker_100mL" >&2
    exit 1
fi

CASE_NAME="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
STEP_DIR="${REPO_ROOT}/cad/output"
CASE_DIR="${REPO_ROOT}/cad/cfd/cases/${CASE_NAME}"
TRI_DIR="${CASE_DIR}/constant/triSurface"

if [[ ! -d "${STEP_DIR}" ]]; then
    echo "ERROR: STEP source directory missing: ${STEP_DIR}" >&2
    echo "Run cad/scripts/build_geometry.py first to generate STEP files." >&2
    exit 1
fi

mkdir -p "${TRI_DIR}"

# Map STEP basename → OpenFOAM patch name (per case)
declare -A STIRRER_A_PARTS=(
    ["beaker_100mm"]="vessel_wall"
    ["stirrer_A_pitched_blade"]="impeller_wall"
)

declare -A STIRRER_B_PARTS=(
    ["beaker_100mm"]="vessel_wall"
    ["stirrer_B_rotor"]="impeller_wall"
    ["stirrer_B_stator"]="stator_wall"
)

case "${CASE_NAME}" in
    stirrer_A_beaker_100mL)
        # shellcheck disable=SC2178
        declare -n PARTS=STIRRER_A_PARTS
        ;;
    stirrer_B_beaker_100mL)
        # shellcheck disable=SC2178
        declare -n PARTS=STIRRER_B_PARTS
        ;;
    *)
        echo "ERROR: unknown case '${CASE_NAME}'" >&2
        exit 1
        ;;
esac

# Pick converter
if command -v gmsh >/dev/null 2>&1; then
    CONVERTER="gmsh"
elif command -v FreeCADCmd >/dev/null 2>&1 || command -v freecadcmd >/dev/null 2>&1; then
    CONVERTER="freecad"
else
    echo "ERROR: neither gmsh nor FreeCADCmd available." >&2
    echo "Install: apt-get install gmsh   OR   conda install -c conda-forge freecad" >&2
    exit 1
fi

echo "Using converter: ${CONVERTER}"
echo "Output STL directory: ${TRI_DIR}"

for STEP_NAME in "${!PARTS[@]}"; do
    STEP_FILE="${STEP_DIR}/${STEP_NAME}.step"
    PATCH_NAME="${PARTS[${STEP_NAME}]}"
    STL_FILE="${TRI_DIR}/${PATCH_NAME}.stl"

    if [[ ! -f "${STEP_FILE}" ]]; then
        echo "WARNING: STEP file missing, skipping: ${STEP_FILE}" >&2
        continue
    fi

    echo "  ${STEP_NAME}.step -> ${PATCH_NAME}.stl"

    if [[ "${CONVERTER}" == "gmsh" ]]; then
        # gmsh: STEP → STL with deflection 0.05 mm (under the 0.1 mm fidelity
        # target in cad/cfd/README.md)
        gmsh -2 -format stl \
            -clmax 0.5 -clmin 0.05 \
            -o "${STL_FILE}" \
            "${STEP_FILE}" \
            >/dev/null
    else
        FREECAD_CLI="$(command -v FreeCADCmd 2>/dev/null || command -v freecadcmd)"
        "${FREECAD_CLI}" -c "
import Part, Mesh
shape = Part.Shape()
shape.read('${STEP_FILE}')
Mesh.Mesh(shape.tessellate(0.05)).write('${STL_FILE}')
"
    fi

    # Rewrite the ASCII-STL solid name so snappyHexMesh picks up the patch
    # label (gmsh emits 'created by Gmsh', FreeCAD emits the file basename).
    if [[ -f "${STL_FILE}" ]]; then
        sed -i "1s/.*/solid ${PATCH_NAME}/" "${STL_FILE}"
        sed -i "\$s/.*/endsolid ${PATCH_NAME}/" "${STL_FILE}"
    fi
done

echo
echo "Done. Next step:"
echo "  cad/cfd/scripts/run_case.sh ${CASE_NAME}"
