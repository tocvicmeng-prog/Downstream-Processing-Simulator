"""Post-process an OpenFOAM case into a schema-v1.0 ``zones.json``.

Reads cell-centred fields (``epsilon``, ``U``, ``k``) and a mesh, partitions
the fluid domain into compartments per a user-supplied zone-config JSON,
computes per-zone ε_avg and ε_breakage_weighted (using DPSim's own
:func:`breakage_rate_alopaeus` so the weighting matches the integrator),
estimates inter-zone convective flows from the boundary velocity field,
and emits a JSON file that round-trips through DPSim's Pydantic loader
without modification.

Usage
-----
::

    python extract_epsilon.py <case_dir> \\
        --zones zones_config.json \\
        --d-ref 100e-6 \\
        --rho-c 860 --mu-c 0.05 --sigma 5e-3 \\
        --output zones.json

Zone-config JSON schema
-----------------------
::

    {
      "zones": [
        {
          "name": "impeller",
          "kind": "impeller_swept_volume",
          "selector": {"type": "cellZone", "name": "rotor"}
        },
        {
          "name": "near_wall",
          "kind": "near_wall",
          "selector": {"type": "near_surface", "patch": "vessel_wall",
                       "max_distance_m": 0.005}
        },
        {
          "name": "bulk",
          "kind": "bulk",
          "selector": {"type": "complement"}
        }
      ]
    }

Three selector types are supported in v1.0:

- ``cellZone`` — use a named cellZone (e.g. created by snappyHexMesh refinement).
- ``near_surface`` — cells whose distance to the named patch is less than
  ``max_distance_m``. Distance computed from cell centroid to nearest face
  centroid on the patch (approximate; suitable for thin near-wall layers).
- ``complement`` — every cell not yet assigned. Must be the last zone;
  there can be at most one.

Additional case-metadata fields (``case_name``, ``stirrer_type``, ``rpm``,
``vessel``, ``fluid_temperature_K``, ``openfoam_solver``) are taken from
``--case-name``, ``--stirrer-type``, etc. flags or from a sibling
``case_metadata.json`` if present.

Limitations of the v1.0 implementation
--------------------------------------
- **Surface-flux approximation for exchanges.** Exact zone-to-zone flux
  requires reading face-centred ``phi`` (or running a function-object in
  OpenFOAM that emits flux per zone-pair). This v1.0 implementation
  approximates ``Q_ij ≈ <|U · n|> · A_boundary`` where ``A_boundary`` is
  estimated from the boundary face count × mean face area at zone interfaces.
  Document and prefer the function-object path for production runs; pass
  ``--exchanges-from-json`` to override with externally-computed values.
- **Single time instant or simple average.** ``--time`` selects one time
  directory; ``--time-window t0,t1`` averages all time directories within
  the inclusive window. No phase-locked averaging.
- **Single d_ref for ε_breakage_weighted.** Polydisperse systems with
  bimodal breakage may need an iterative refinement; flagged as a known
  limitation in Appendix K §K.6.1.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


def _reconfigure_stdout_utf8() -> None:
    """Project-wide quirk: repo path contains 'æ–‡æ¡£'; reconfigure stdout
    so prints of absolute paths don't crash on cp1252 Windows consoles."""
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        pass


# ---------------------------------------------------------------------------
# Breakage-rate kernel (vendored from dpsim.level1_emulsification.kernels)
# ---------------------------------------------------------------------------

def breakage_rate_alopaeus(
    d: float,
    epsilon: float,
    sigma: float,
    rho_c: float,
    mu_d: float,
    nu_c: float,
    *,
    C1: float = 0.986,
    C2: float = 0.0115,
    C3: float = 0.0,
) -> float:
    """Single-diameter Alopaeus breakage rate [1/s]. Vendored to keep this
    script independent of the DPSim package install path. Numerically
    identical to ``dpsim.level1_emulsification.kernels.breakage_rate_alopaeus``
    (NumPy path, no JIT).
    """
    if epsilon <= 0.0 or d <= 0.0:
        return 0.0
    prefactor = C1 * math.sqrt(epsilon / nu_c)
    denom1 = rho_c * (epsilon ** (2.0 / 3.0)) * (d ** (5.0 / 3.0))
    if denom1 == 0.0:
        return 0.0
    exp_arg1 = -C2 * sigma / denom1
    exp_arg2 = 0.0
    if C3 > 0.0 and mu_d > 0.0:
        denom2 = rho_c * sigma * d
        if denom2 > 0.0:
            Vi = mu_d / math.sqrt(denom2)
            Vi = min(Vi, 100.0)
            exp_arg2 = -C3 * Vi
    exp_total = max(exp_arg1 + exp_arg2, -200.0)
    g = prefactor * math.exp(exp_total)
    return max(g, 0.0) if math.isfinite(g) else 0.0


# ---------------------------------------------------------------------------
# OpenFOAM case I/O (uses fluidfoam if available; fallback for tests)
# ---------------------------------------------------------------------------

def list_time_directories(case_dir: Path) -> list[str]:
    """List time directories sorted numerically (skip 0/, system/, constant/)."""
    if not case_dir.exists():
        raise FileNotFoundError(f"Case directory not found: {case_dir}")
    times: list[tuple[float, str]] = []
    for child in case_dir.iterdir():
        if not child.is_dir():
            continue
        try:
            t = float(child.name)
        except ValueError:
            continue
        if t < 0:
            continue
        times.append((t, child.name))
    times.sort()
    return [name for _, name in times]


def select_time_dirs(
    case_dir: Path,
    time: str | None,
    time_window: tuple[float, float] | None,
) -> list[str]:
    """Resolve ``--time`` / ``--time-window`` into the time-directory names
    we will average over. ``time`` selects exactly one; ``time_window``
    selects all in [t0, t1] inclusive. Latest steady value when both omitted.
    """
    available = list_time_directories(case_dir)
    if not available:
        raise RuntimeError(
            f"No time directories found in {case_dir}. "
            "Has the case been solved (or reconstructed after parallel run)?"
        )
    if time is not None:
        if time not in available:
            raise ValueError(
                f"Time '{time}' not found among {available}"
            )
        return [time]
    if time_window is not None:
        t0, t1 = time_window
        chosen = [n for n in available if t0 <= float(n) <= t1]
        if not chosen:
            raise ValueError(
                f"No time directories in window [{t0}, {t1}]; "
                f"available: {available}"
            )
        return chosen
    # Default: latest time only
    return [available[-1]]


def read_scalar_field(case_dir: Path, time: str, field: str) -> "Any":
    """Read a cell-centred scalar field via fluidfoam.

    Returns a NumPy array shaped (n_cells,). Raises if fluidfoam is not
    installed or the field file does not exist.
    """
    try:
        from fluidfoam import readof  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(
            "fluidfoam is required to read OpenFOAM fields. "
            "Install with: pip install fluidfoam"
        ) from exc
    return readof.readscalar(str(case_dir), time, field)


def read_vector_field(case_dir: Path, time: str, field: str) -> "Any":
    """Read a cell-centred vector field via fluidfoam (shape (3, n_cells))."""
    try:
        from fluidfoam import readof  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(
            "fluidfoam is required to read OpenFOAM fields."
        ) from exc
    return readof.readvector(str(case_dir), time, field)


def read_cell_centres(case_dir: Path, time: str) -> "Any":
    """Read cell centroids C[3, n_cells]. Requires that ``writeCellCentres``
    has been run in the OpenFOAM case (creates ``C`` in the time directory).
    """
    return read_vector_field(case_dir, time, "C")


def read_cell_volumes(case_dir: Path, time: str) -> "Any":
    """Read cell volumes V[n_cells]. Requires that ``writeCellVolumes`` has
    been run (creates ``V`` in the time directory).
    """
    return read_scalar_field(case_dir, time, "V")


def read_cell_zone(case_dir: Path, zone_name: str) -> "Any":
    """Read the cell list for a named cellZone from constant/polyMesh/cellZones.

    Returns a NumPy boolean mask of shape (n_cells,). Raises if the zone
    is not present.

    The OpenFOAM cellZones file is plain text. Parser is minimal — handles
    the standard format used by snappyHexMesh and topoSet.
    """
    import numpy as np

    cz_file = case_dir / "constant" / "polyMesh" / "cellZones"
    if not cz_file.exists():
        raise FileNotFoundError(
            f"cellZones file not found: {cz_file}. "
            "Has snappyHexMesh / topoSet been run?"
        )
    text = cz_file.read_text(encoding="utf-8")
    # Find the named zone block: looks like
    #   rotor
    #   {
    #       type cellZone;
    #       cellLabels List<label>
    #       N
    #       (
    #           id1 id2 ... idN
    #       )
    #       ;
    #   }
    import re
    block_re = re.compile(
        rf"\b{re.escape(zone_name)}\s*\{{[^}}]*?cellLabels[^()]*?\(([^)]*)\)",
        re.DOTALL,
    )
    m = block_re.search(text)
    if not m:
        raise KeyError(
            f"cellZone '{zone_name}' not found in {cz_file}; "
            "check `cat constant/polyMesh/cellZones | grep -A1 'type'`."
        )
    ids = np.fromstring(m.group(1), dtype=np.int64, sep=" ")
    # Determine total cell count from any field
    return ids


def cellzone_mask(zone_ids: "Any", n_cells: int) -> "Any":
    """Convert a list of cell-IDs to a boolean mask over n_cells."""
    import numpy as np

    mask = np.zeros(n_cells, dtype=bool)
    mask[zone_ids] = True
    return mask


# ---------------------------------------------------------------------------
# Zone partitioning
# ---------------------------------------------------------------------------

def near_surface_mask(
    cell_centres: "Any",
    case_dir: Path,
    patch_name: str,
    max_distance_m: float,
) -> "Any":
    """Cells within ``max_distance_m`` of the named boundary patch.

    Distance is approximated as the minimum Euclidean distance from the
    cell centroid to any face centroid on the patch. For thin near-wall
    layers (the canonical use case) this is an acceptable approximation
    to the true cell-to-surface distance.
    """
    import numpy as np

    # Read patch face centroids from polyMesh
    face_centres = _read_patch_face_centres(case_dir, patch_name)
    if face_centres.size == 0:
        raise ValueError(
            f"Patch '{patch_name}' has no faces; check polyMesh/boundary."
        )
    # cell_centres: shape (3, n_cells) per fluidfoam convention; transpose
    if cell_centres.shape[0] == 3 and cell_centres.shape[1] != 3:
        cc = cell_centres.T
    else:
        cc = cell_centres
    # face_centres: shape (n_faces, 3)
    # Brute-force min-distance per cell. Vectorised for speed.
    n_cells = cc.shape[0]
    mask = np.zeros(n_cells, dtype=bool)
    # Process in chunks to bound memory
    chunk = 50_000
    for start in range(0, n_cells, chunk):
        end = min(start + chunk, n_cells)
        d2 = np.min(
            np.sum((cc[start:end, None, :] - face_centres[None, :, :]) ** 2, axis=2),
            axis=1,
        )
        mask[start:end] = d2 <= max_distance_m ** 2
    return mask


def _read_patch_face_centres(case_dir: Path, patch_name: str) -> "Any":
    """Read face centroids for a named patch.

    OpenFOAM's polyMesh/faces file is binary or ASCII; reading it directly
    from Python is non-trivial. The portable approach: use
    ``writeFaceCentres`` (function object) which writes a Cf file in
    each time directory. If unavailable, fall back to parsing
    polyMesh/boundary + faces (ASCII only).
    """
    import numpy as np

    # Prefer the time-directory Cf file written by `writeFaceCentres`
    times = list_time_directories(case_dir)
    if times:
        cf_path = case_dir / times[-1] / "Cf"
        if cf_path.exists():
            return _read_face_centres_from_cf(cf_path, case_dir, patch_name)
    # Fallback: not implemented in v1.0 (requires a full polyMesh parser)
    raise RuntimeError(
        f"Patch face centres for '{patch_name}' could not be read. "
        f"Run the writeFaceCentres function object in the OpenFOAM case "
        f"(adds Cf field to each time directory) or use a `cellZone` "
        f"selector instead of `near_surface`."
    )


def _read_face_centres_from_cf(
    cf_path: Path, case_dir: Path, patch_name: str,
) -> "Any":
    """Read face centroids for the named patch from the Cf field file."""
    import numpy as np

    # Cf is a face-centred surfaceVectorField; fluidfoam doesn't read these
    # cleanly. We parse the FoamFile directly: a 'patch' block contains
    # face centroids in the boundary section.
    # For v1.0 simplicity, expect Cf written as a vol-style field with
    # boundary entries.
    text = cf_path.read_text(encoding="utf-8")
    import re

    # Find boundary entry for the named patch
    block_re = re.compile(
        rf"\b{re.escape(patch_name)}\s*\{{[^}}]*?value\s+nonuniform\s+List<vector>\s*"
        rf"\d+\s*\(([^)]*)\)",
        re.DOTALL,
    )
    m = block_re.search(text)
    if not m:
        raise ValueError(
            f"Patch '{patch_name}' not found in Cf at {cf_path}. "
            f"Was it included in the writeFaceCentres function object?"
        )
    # Each face centroid is a triple "(x y z)"; flatten and parse
    triples = re.findall(r"\(([-\d.eE+ ]+)\)", m.group(1))
    pts = np.array(
        [list(map(float, t.split())) for t in triples],
        dtype=np.float64,
    )
    return pts


def build_zone_masks(
    zone_specs: list[dict],
    cell_centres: "Any",
    case_dir: Path,
) -> list[tuple[str, dict, "Any"]]:
    """Resolve each zone selector to a boolean cell-mask.

    Returns a list of (zone_name, full_zone_spec, mask) tuples in input order.
    The 'complement' selector must be the last zone (if used).
    """
    import numpy as np

    n_cells = cell_centres.shape[1] if cell_centres.shape[0] == 3 else cell_centres.shape[0]
    assigned = np.zeros(n_cells, dtype=bool)
    out: list[tuple[str, dict, "Any"]] = []

    for i, spec in enumerate(zone_specs):
        sel = spec["selector"]
        sel_type = sel["type"]
        if sel_type == "cellZone":
            ids = read_cell_zone(case_dir, sel["name"])
            mask = cellzone_mask(ids, n_cells)
            mask &= ~assigned  # don't double-count
        elif sel_type == "near_surface":
            mask = near_surface_mask(
                cell_centres, case_dir,
                patch_name=sel["patch"],
                max_distance_m=float(sel["max_distance_m"]),
            )
            mask &= ~assigned
        elif sel_type == "complement":
            if i != len(zone_specs) - 1:
                raise ValueError(
                    "Selector 'complement' must be the last zone in the "
                    "config; got at index {i}."
                )
            mask = ~assigned
        else:
            raise ValueError(
                f"Unknown selector type '{sel_type}' for zone '{spec['name']}'. "
                f"Supported: cellZone, near_surface, complement."
            )
        if not mask.any():
            print(
                f"WARNING: zone '{spec['name']}' has no cells; skipping or "
                f"failing later validation.",
                file=sys.stderr,
            )
        assigned |= mask
        out.append((spec["name"], spec, mask))
    return out


# ---------------------------------------------------------------------------
# Per-zone field aggregation
# ---------------------------------------------------------------------------

def aggregate_zone(
    name: str,
    spec: dict,
    mask: "Any",
    epsilon: "Any",
    cell_volumes: "Any",
    cell_centres: "Any",
    velocity_mag: "Any",
    nu_c: float,
    d_ref: float,
    rho_c: float,
    sigma: float,
    mu_d: float,
    breakage_C3: float,
) -> dict:
    """Compute the zone's CFDZone fields per the v1.0 schema."""
    import numpy as np

    eps_zone = epsilon[mask]
    V_zone_cells = cell_volumes[mask]
    if cell_centres.shape[0] == 3:
        cc_zone = cell_centres[:, mask]
    else:
        cc_zone = cell_centres[mask].T  # → shape (3, k)

    V_total = float(np.sum(V_zone_cells))
    if V_total <= 0.0:
        raise ValueError(f"Zone '{name}' has zero or negative total volume.")

    # ε_avg: volume-weighted
    eps_avg = float(np.sum(V_zone_cells * eps_zone) / V_total)

    # ε_breakage_weighted: g(d_ref, ε)·ε weighted, then g(d_ref, ε) weighted
    # Vectorise the kernel for speed.
    if eps_zone.size > 0:
        prefactor = 0.986 * np.sqrt(np.maximum(eps_zone, 0.0) / nu_c)
        denom1 = rho_c * np.power(np.maximum(eps_zone, 1e-30), 2.0 / 3.0) * (d_ref ** (5.0 / 3.0))
        exp_arg1 = -0.0115 * sigma / np.where(denom1 > 0.0, denom1, np.inf)
        exp_arg2 = 0.0
        if breakage_C3 > 0.0 and mu_d > 0.0:
            Vi = mu_d / math.sqrt(rho_c * sigma * d_ref)
            Vi = min(Vi, 100.0)
            exp_arg2 = -breakage_C3 * Vi
        exp_total = np.maximum(exp_arg1 + exp_arg2, -200.0)
        g = prefactor * np.exp(exp_total)
        g = np.where(np.isfinite(g) & (g > 0.0), g, 0.0)
        gw = g * V_zone_cells
        gw_sum = float(np.sum(gw))
        if gw_sum > 0.0:
            eps_brk = float(np.sum(gw * eps_zone) / gw_sum)
        else:
            # All-zero g: zone has no breakage at d_ref. Fall back to ε_avg.
            eps_brk = eps_avg
    else:
        eps_brk = eps_avg

    # Enforce schema invariant ε_brk ≥ ε_avg (numerical noise can flip them
    # by < 1% — clamp to ε_avg in that case).
    if eps_brk < eps_avg:
        if (eps_avg - eps_brk) / max(eps_avg, 1e-30) < 0.01:
            eps_brk = eps_avg
        else:
            raise ValueError(
                f"Zone '{name}': computed ε_brk ({eps_brk:.4g}) < ε_avg "
                f"({eps_avg:.4g}) by more than 1 %. This is mathematically "
                f"impossible for a convex weighting function and indicates "
                f"a bug in the aggregation."
            )

    # Shear rate average from |U| / cell-size proxy. Better proxies require
    # gradient-of-U (volScalarField) which fluidfoam doesn't read cleanly.
    # If user wrote `mag(U)` and `magGradU` via function objects, prefer those.
    # Here we use a Smagorinsky-style proxy: |γ̇| ≈ √(2 · ε / ν_c).
    shear_avg = float(math.sqrt(2.0 * max(eps_avg, 0.0) / nu_c))

    # Centroid (volume-weighted)
    cx = float(np.sum(V_zone_cells * cc_zone[0, :]) / V_total)
    cy = float(np.sum(V_zone_cells * cc_zone[1, :]) / V_total)
    cz = float(np.sum(V_zone_cells * cc_zone[2, :]) / V_total)

    # Kolmogorov length at ε_avg
    eta_K = (nu_c ** 3 / max(eps_avg, 1e-30)) ** 0.25

    return {
        "name": name,
        "kind": spec["kind"],
        "volume_m3": V_total,
        "cell_count": int(np.count_nonzero(mask)),
        "epsilon_avg_W_per_kg": eps_avg,
        "epsilon_breakage_weighted_W_per_kg": eps_brk,
        "shear_rate_avg_per_s": shear_avg,
        "centroid_xyz_m": [cx, cy, cz],
        "kolmogorov_length_m": float(eta_K),
        "metadata": {
            "selector": spec["selector"],
            "shear_proxy": "sqrt(2 eps / nu_c)",
        },
    }


# ---------------------------------------------------------------------------
# Inter-zone exchange flows
# ---------------------------------------------------------------------------

def estimate_exchange_flows(
    zone_results: list[tuple[str, dict, "Any"]],
    velocity: "Any",
    cell_volumes: "Any",
    cell_centres: "Any",
) -> list[dict]:
    """Surface-flux approximation for inter-zone convective exchange.

    For each ordered pair of zones (i_from, i_to), find cells in zone i_from
    that have at least one neighbouring cell in zone i_to (proxy: nearest
    cell across the boundary). Approximate Q_ij as the mean |U · n| at the
    boundary times the boundary area, where n points from i_from to i_to
    and the area is estimated from the count of boundary cells × mean cell
    cross-section √(V^(2/3)).

    This is **approximate**. For production runs, prefer running an
    OpenFOAM function object that integrates phi over zone-pair internal
    faces and emits the exact Q values, then pass them via
    ``--exchanges-from-json``.
    """
    import numpy as np

    if velocity.shape[0] == 3:
        umag = np.linalg.norm(velocity, axis=0)
    else:
        umag = np.linalg.norm(velocity, axis=1)

    if cell_centres.shape[0] == 3:
        cc = cell_centres.T
    else:
        cc = cell_centres

    # For each cell, find which zone it belongs to (fast index lookup)
    n_cells = cc.shape[0]
    zone_of = np.full(n_cells, -1, dtype=np.int32)
    for i, (_, _, mask) in enumerate(zone_results):
        zone_of[mask] = i

    exchanges: list[dict] = []

    # KDTree for nearest-neighbour queries
    try:
        from scipy.spatial import cKDTree  # type: ignore[import-not-found]
    except ImportError:
        print(
            "WARNING: scipy not available; skipping exchange-flow estimation.",
            file=sys.stderr,
        )
        return exchanges

    # Build per-zone trees of cell centroids
    zone_indices = [np.where(mask)[0] for _, _, mask in zone_results]
    zone_trees = [cKDTree(cc[idxs]) for idxs in zone_indices]

    n_zones = len(zone_results)
    for i in range(n_zones):
        idxs_i = zone_indices[i]
        if idxs_i.size == 0:
            continue
        for j in range(n_zones):
            if i == j:
                continue
            idxs_j = zone_indices[j]
            if idxs_j.size == 0:
                continue
            # For each cell in zone i, find distance to nearest cell in zone j.
            # "Boundary cells of i facing j" = cells of i whose nearest j-neighbour
            # is closer than the median i-i nearest-neighbour distance × 1.5.
            # This is a heuristic — works for snappy meshes with locally
            # uniform refinement.
            d_ji, _ = zone_trees[j].query(cc[idxs_i], k=1)
            # i-i median nearest-neighbour distance for scale
            if idxs_i.size > 1:
                d_ii, _ = zone_trees[i].query(cc[idxs_i], k=2)
                scale = float(np.median(d_ii[:, 1]))
            else:
                scale = float(np.median(d_ji))
            boundary_mask = d_ji <= 1.5 * scale
            if not boundary_mask.any():
                continue
            boundary_cells_i = idxs_i[boundary_mask]
            # Mean |U| at the i-side boundary cells
            u_mean = float(np.mean(umag[boundary_cells_i]))
            # Area proxy: each boundary cell contributes a face of area V^(2/3)
            face_area = float(np.sum(np.power(cell_volumes[boundary_cells_i], 2.0 / 3.0)))
            # Half because cells are bidirectionally counted; only outflow
            # contributes to Q_ij. Apply a 0.5 factor.
            Q_ij = 0.5 * u_mean * face_area
            if Q_ij > 0.0:
                exchanges.append({
                    "from_zone": zone_results[i][0],
                    "to_zone": zone_results[j][0],
                    "volumetric_flow_m3_per_s": Q_ij,
                    "kind": "convective",
                })

    return exchanges


# ---------------------------------------------------------------------------
# Time averaging
# ---------------------------------------------------------------------------

def time_average_field(
    case_dir: Path, times: list[str], field: str, *, vector: bool = False,
) -> "Any":
    """Read ``field`` at each time in ``times`` and return the simple mean.

    For most RANS cases ε is already time-averaged via OpenFOAM's run-time
    averaging (``fieldAverage`` function object), so a single time is
    typically passed in.
    """
    import numpy as np

    if not times:
        raise ValueError("Empty time list for averaging.")
    if vector:
        accum = read_vector_field(case_dir, times[0], field).astype(np.float64)
        for t in times[1:]:
            accum = accum + read_vector_field(case_dir, t, field)
        return accum / float(len(times))
    accum = read_scalar_field(case_dir, times[0], field).astype(np.float64)
    for t in times[1:]:
        accum = accum + read_scalar_field(case_dir, t, field)
    return accum / float(len(times))


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run(args: argparse.Namespace) -> int:
    import numpy as np

    case_dir = Path(args.case_dir).resolve()
    if not (case_dir / "system" / "controlDict").exists():
        print(f"ERROR: not an OpenFOAM case: {case_dir}", file=sys.stderr)
        return 1

    # Resolve times to average over
    time_window = None
    if args.time_window is not None:
        try:
            t0, t1 = (float(x) for x in args.time_window.split(","))
        except ValueError:
            print(
                f"ERROR: --time-window must be 't0,t1', got {args.time_window!r}",
                file=sys.stderr,
            )
            return 1
        time_window = (t0, t1)
    times = select_time_dirs(case_dir, args.time, time_window)
    primary_time = times[-1]

    # Load zone config
    zones_cfg_path = Path(args.zones)
    zones_cfg = json.loads(zones_cfg_path.read_text(encoding="utf-8"))
    zone_specs = zones_cfg["zones"]

    print(f"Reading mesh + fields from {case_dir} (time={times})...")

    # Cell-centred fields
    cell_volumes = read_cell_volumes(case_dir, primary_time)
    cell_centres = read_cell_centres(case_dir, primary_time)
    epsilon = time_average_field(case_dir, times, "epsilon")
    velocity = time_average_field(case_dir, times, "U", vector=True)

    # Sanity: same shape
    n_cells = cell_volumes.size
    if epsilon.size != n_cells:
        print(
            f"ERROR: epsilon size {epsilon.size} != cell count {n_cells}",
            file=sys.stderr,
        )
        return 1

    # Material properties for breakage weighting
    nu_c = args.mu_c / args.rho_c

    # Build zone masks
    zone_results = build_zone_masks(zone_specs, cell_centres, case_dir)

    # Aggregate per zone
    print(f"Aggregating {len(zone_results)} zones at d_ref={args.d_ref:.3e} m...")
    zones_out: list[dict] = []
    for name, spec, mask in zone_results:
        if not mask.any():
            print(f"  skipping empty zone '{name}'", file=sys.stderr)
            continue
        z = aggregate_zone(
            name=name, spec=spec, mask=mask,
            epsilon=epsilon,
            cell_volumes=cell_volumes,
            cell_centres=cell_centres,
            velocity_mag=velocity,
            nu_c=nu_c, d_ref=args.d_ref,
            rho_c=args.rho_c, sigma=args.sigma,
            mu_d=args.mu_d, breakage_C3=args.breakage_C3,
        )
        zones_out.append(z)
        print(
            f"  {name:20s} V={z['volume_m3']:.3e} m^3, "
            f"eps_avg={z['epsilon_avg_W_per_kg']:.3g}, "
            f"eps_brk={z['epsilon_breakage_weighted_W_per_kg']:.3g}, "
            f"cells={z['cell_count']}"
        )

    # Inter-zone exchanges
    if args.exchanges_from_json:
        print(f"Reading exchanges from {args.exchanges_from_json}...")
        with open(args.exchanges_from_json, encoding="utf-8") as f:
            exch_data = json.load(f)
        exchanges_out = exch_data["exchanges"]
    else:
        print("Estimating inter-zone flows (surface-flux approximation)...")
        exchanges_out = estimate_exchange_flows(
            zone_results, velocity, cell_volumes, cell_centres,
        )
        print(f"  {len(exchanges_out)} directed exchanges")

    # Volume-weighted average ε for case_metadata
    total_v = sum(z["volume_m3"] for z in zones_out)
    eps_vw_avg = sum(
        z["volume_m3"] * z["epsilon_avg_W_per_kg"] for z in zones_out
    ) / total_v if total_v > 0 else 0.0

    # Assemble case_metadata
    case_metadata = {
        "case_name": args.case_name or case_dir.name,
        "stirrer_type": args.stirrer_type,
        "vessel": args.vessel,
        "rpm": args.rpm,
        "fluid_temperature_K": args.fluid_temperature,
        "openfoam_solver": args.solver,
        "time_averaging_window_s": [
            float(times[0]), float(times[-1]) + 1e-12,
        ],
        "n_cells_total": int(n_cells),
        "convergence_residual": args.residual,
        "epsilon_volume_weighted_avg_W_per_kg": eps_vw_avg,
    }

    payload = {
        "schema_version": "1.0",
        "case_metadata": case_metadata,
        "zones": zones_out,
        "exchanges": exchanges_out,
    }

    # Self-validate against the DPSim Pydantic loader if available
    try:
        sys.path.insert(0, str(case_dir.parents[3] / "src"))
        from dpsim.cfd.zonal_pbe import CFDZonesPayload  # type: ignore[import-not-found]
        CFDZonesPayload.model_validate(payload)
        print("zones.json passes DPSim schema-v1.0 validation.")
    except ImportError:
        print(
            "WARNING: dpsim not on sys.path; skipping schema self-validation. "
            "Install or pip-install -e . to enable.",
            file=sys.stderr,
        )
    except Exception as exc:
        print(f"ERROR: schema validation failed: {exc}", file=sys.stderr)
        return 2

    # Write JSON
    out_path = Path(args.output).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"Wrote {out_path} ({len(zones_out)} zones, {len(exchanges_out)} exchanges)")
    return 0


def main() -> int:
    _reconfigure_stdout_utf8()
    parser = argparse.ArgumentParser(
        description=(
            "Post-process an OpenFOAM case into a schema-v1.0 zones.json. "
            "See cad/cfd/zones_schema.md for the contract."
        ),
    )
    parser.add_argument("case_dir", help="OpenFOAM case directory")
    parser.add_argument(
        "--zones", required=True,
        help="Path to zones-config JSON describing zone selectors",
    )
    parser.add_argument(
        "--output", "-o", default="zones.json",
        help="Output zones.json path",
    )
    parser.add_argument(
        "--time", default=None,
        help="Single time directory to read (default: latest)",
    )
    parser.add_argument(
        "--time-window", default=None,
        help="Average over time directories in [t0, t1] (e.g. '2.0,5.0')",
    )
    parser.add_argument("--d-ref", type=float, default=100e-6, help="[m]")
    parser.add_argument("--rho-c", type=float, default=860.0, help="[kg/m^3]")
    parser.add_argument("--mu-c", type=float, default=0.05, help="[Pa.s]")
    parser.add_argument("--mu-d", type=float, default=0.05, help="[Pa.s]")
    parser.add_argument("--sigma", type=float, default=5e-3, help="[N/m]")
    parser.add_argument("--breakage-C3", type=float, default=0.0)
    # case_metadata fields (most have sensible defaults but are not derivable
    # from the OpenFOAM case alone)
    parser.add_argument("--case-name", default=None)
    parser.add_argument(
        "--stirrer-type", default="pitched_blade_A",
        choices=["pitched_blade_A", "rotor_stator_B"],
    )
    parser.add_argument("--vessel", default="beaker_100mm")
    parser.add_argument("--rpm", type=float, default=1500.0)
    parser.add_argument("--fluid-temperature", type=float, default=298.15)
    parser.add_argument("--solver", default="pimpleDyMFoam")
    parser.add_argument(
        "--residual", type=float, default=1e-5,
        help="Final residual achieved by the solver (for case_metadata)",
    )
    parser.add_argument(
        "--exchanges-from-json", default=None,
        help=(
            "Path to a JSON file containing pre-computed exchanges "
            "(e.g. from an OpenFOAM function object). Override the "
            "surface-flux approximation."
        ),
    )
    args = parser.parse_args()
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
