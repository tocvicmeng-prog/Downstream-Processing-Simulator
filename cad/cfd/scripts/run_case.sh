#!/usr/bin/env bash
# run_case.sh — execute the full OpenFOAM CFD-PBE pipeline for a case.
#
# Stages
# ------
#   1. blockMesh                  background hex mesh from blockMeshDict
#   2. surfaceFeatureExtract      extract sharp edges from STL
#   3. snappyHexMesh -overwrite   castellate + snap + layer
#   4. checkMesh                  mesh-quality gates
#   5. decomposePar               split for parallel
#   6. mpirun -n N pimpleDyMFoam  transient solve with sliding mesh
#   7. reconstructPar             merge time directories
#   8. postProcess writeCellCentres writeCellVolumes  (for extract_epsilon.py)
#
# Requires
# --------
#   - OpenFOAM v11+ (or .com/.org build with pimpleDyMFoam, snappyHexMesh)
#   - prepare_geometry.sh has been run (STL files in constant/triSurface/)
#   - mpirun (for parallel)
#
# Usage
# -----
#   run_case.sh stirrer_A_beaker_100mL [--cores 8]
set -euo pipefail

CASE_NAME="${1:-}"
CORES="${CORES:-8}"

# Parse --cores N
shift || true
while [[ $# -gt 0 ]]; do
    case "$1" in
        --cores)
            CORES="$2"; shift 2;;
        *)
            echo "ERROR: unknown flag $1" >&2; exit 1;;
    esac
done

if [[ -z "${CASE_NAME}" ]]; then
    echo "Usage: $0 <case_name> [--cores N]" >&2
    echo "  case_name: stirrer_A_beaker_100mL or stirrer_B_beaker_100mL" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
CASE_DIR="${REPO_ROOT}/cad/cfd/cases/${CASE_NAME}"

if [[ ! -d "${CASE_DIR}" ]]; then
    echo "ERROR: case directory missing: ${CASE_DIR}" >&2
    exit 1
fi

if [[ ! -d "${CASE_DIR}/constant/triSurface" ]] || \
   [[ -z "$(ls -A "${CASE_DIR}/constant/triSurface" 2>/dev/null || true)" ]]; then
    echo "ERROR: STL files missing. Run prepare_geometry.sh ${CASE_NAME} first." >&2
    exit 1
fi

# Sanity: OpenFOAM environment loaded?
if ! command -v blockMesh >/dev/null 2>&1; then
    echo "ERROR: OpenFOAM environment not loaded." >&2
    echo "  source /opt/openfoam11/etc/bashrc   (or equivalent)" >&2
    exit 1
fi

cd "${CASE_DIR}"

# Restore initial conditions
if [[ -d "0.org" ]]; then
    rm -rf 0
    cp -r 0.org 0
fi

echo "==> Stage 1/8: blockMesh"
blockMesh > log.blockMesh 2>&1

echo "==> Stage 2/8: surfaceFeatureExtract"
if [[ -f system/surfaceFeatureExtractDict ]]; then
    surfaceFeatureExtract > log.surfaceFeatureExtract 2>&1
else
    echo "  (no surfaceFeatureExtractDict; skipping — relying on snappy auto-edges)"
fi

echo "==> Stage 3/8: snappyHexMesh -overwrite"
snappyHexMesh -overwrite > log.snappyHexMesh 2>&1

echo "==> Stage 4/8: checkMesh"
if ! checkMesh > log.checkMesh 2>&1; then
    echo "WARNING: checkMesh reported issues; review log.checkMesh." >&2
fi

echo "==> Stage 5/8: decomposePar"
decomposePar -force > log.decomposePar 2>&1

echo "==> Stage 6/8: pimpleDyMFoam (parallel, ${CORES} cores)"
mpirun -n "${CORES}" pimpleDyMFoam -parallel > log.pimpleDyMFoam 2>&1

echo "==> Stage 7/8: reconstructPar"
reconstructPar -latestTime > log.reconstructPar 2>&1

echo "==> Stage 8/8: writeCellCentres + writeCellVolumes (for extract_epsilon.py)"
postProcess -func writeCellCentres -latestTime > log.writeCellCentres 2>&1
postProcess -func writeCellVolumes -latestTime > log.writeCellVolumes 2>&1

echo
echo "Done. Next step:"
echo "  python3 ${SCRIPT_DIR}/extract_epsilon.py ${CASE_DIR} \\"
echo "      --zones ${CASE_DIR}/zones_config.json \\"
echo "      --output ${CASE_DIR}/zones.json \\"
echo "      --case-name ${CASE_NAME}"
