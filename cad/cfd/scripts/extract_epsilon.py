"""Post-process OpenFOAM ε field into a zonal compartment model.

Status: TODO. Stub for the CFD-PBE coupling (cad/cfd/README.md step 4).

Reads time-averaged epsilon from a converged OpenFOAM case, partitions the
fluid domain into compartments (impeller swept volume, near-wall, bulk, and
— for Stirrer B — stator slot exit jets), and emits a JSON file consumable
by ``src/dpsim/cfd/zonal_pbe.py`` for PBE forcing-input integration.

Usage (once implemented):
    python3 extract_epsilon.py <openfoam_case_dir> [-o output.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("case_dir", help="OpenFOAM case directory")
    parser.add_argument("-o", "--output", default="zones.json")
    args = parser.parse_args()

    case = Path(args.case_dir)
    if not (case / "system" / "controlDict").exists():
        print(f"ERROR: not an OpenFOAM case: {case}", file=sys.stderr)
        return 1

    print("TODO: implement ε field extraction")
    print(f"  Case: {case}")
    print(f"  Output: {args.output}")
    print()
    print("Expected steps:")
    print("  1. Read latest time directory (or time-average) from case")
    print("  2. Use fluidfoam or PyFoam to load epsilon, U, k fields")
    print("  3. Partition cells into zones based on:")
    print("     - Impeller swept volume (rotating zone)")
    print("     - Near-wall (cells within 5 mm of vessel wall)")
    print("     - Stator slot exits (Stirrer B only — cells within 2 mm of")
    print("       slot exit, on the outside of the stator)")
    print("     - Bulk (everything else)")
    print("  4. Compute zone-averaged ε weighted by breakage frequency:")
    print("     <ε>_zone = ∫ g(d, ε(x)) dV / ∫ g(d, <ε>) dV")
    print("  5. Compute exchange flow rates between zones (from velocity")
    print("     field crossing zone boundaries)")
    print("  6. Emit JSON with structure:")
    print("     {'zones': [{'name': 'impeller', 'volume': 1e-6, 'eps': 50.0,")
    print("                 'eps_breakage_weighted': 75.0, ...}],")
    print("      'exchanges': [{'from': 'impeller', 'to': 'bulk',")
    print("                     'volumetric_flow': 1e-5, ...}]}")
    print()
    print("Recommended dependencies:")
    print("  - fluidfoam (pip install fluidfoam): clean reader for OpenFOAM")
    print("  - numpy, scipy: zone partitioning math")
    print()
    print("See cad/cfd/README.md for full TODO list.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
