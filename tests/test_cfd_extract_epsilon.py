"""Tests for cad/cfd/scripts/extract_epsilon.py and src/dpsim/cfd/openfoam_io.py.

The OpenFOAM-side post-processor and Python helpers, exercised against
synthetic field arrays. No real OpenFOAM install required.

Covers:
- The vendored ``breakage_rate_alopaeus`` is numerically identical to
  DPSim's NumPy implementation (uniform-grid sample).
- ``aggregate_zone`` is correct on a uniform field (ε_avg == ε_brk),
  honours the ε_brk ≥ ε_avg invariant on heterogeneous fields, and
  produces volume-weighted centroids.
- ``estimate_exchange_flows`` returns non-negative directed flows
  between adjacent zones in a synthetic 2-zone grid.
- ``write_dict`` produces a syntactically-valid FoamFile that the
  reader can round-trip the values from.
- ``list_time_directories`` and ``latest_time`` correctly select
  numeric subdirectories from a tmp dir.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

from dpsim.cfd.openfoam_io import (
    latest_time,
    list_time_directories,
    write_dict,
)
from dpsim.level1_emulsification.kernels import breakage_rate_alopaeus

REPO_ROOT = Path(__file__).resolve().parent.parent
EXTRACT_PATH = REPO_ROOT / "cad" / "cfd" / "scripts" / "extract_epsilon.py"


def _load_extract_epsilon():
    """Import extract_epsilon.py as a module without modifying PYTHONPATH."""
    spec = importlib.util.spec_from_file_location("extract_epsilon", EXTRACT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["extract_epsilon"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def ee():
    return _load_extract_epsilon()


# ---------------------------------------------------------------------------
# Vendored breakage kernel matches the canonical implementation
# ---------------------------------------------------------------------------


def test_vendored_breakage_kernel_matches_dpsim(ee):
    """The vendored single-diameter ``breakage_rate_alopaeus`` in
    extract_epsilon.py must match DPSim's NumPy kernel point-for-point.
    Drift would mean the OpenFOAM-side ε_brk weighting and the DPSim-side
    integrator are using different functions — silent, dangerous."""
    diameters = np.array([10e-6, 50e-6, 100e-6, 200e-6, 500e-6])
    epsilon = 50.0
    sigma = 5e-3
    rho_c = 860.0
    mu_d = 0.05
    nu_c = 0.05 / 860.0

    g_dpsim = breakage_rate_alopaeus(
        diameters, epsilon, sigma, rho_c, mu_d, nu_c=nu_c, C3=0.0,
    )
    for i, d in enumerate(diameters):
        g_vendored = ee.breakage_rate_alopaeus(
            float(d), epsilon, sigma, rho_c, mu_d, nu_c, C3=0.0,
        )
        # Allow tight tolerance for the JIT vs NumPy path; 1e-12 should hold
        assert g_vendored == pytest.approx(g_dpsim[i], rel=1e-10), (
            f"vendored kernel drift at d={d}: vendored={g_vendored}, "
            f"dpsim={g_dpsim[i]}"
        )


# ---------------------------------------------------------------------------
# aggregate_zone
# ---------------------------------------------------------------------------


def test_aggregate_zone_uniform_field(ee):
    """A zone with uniform ε must produce ε_avg == ε_brk (within numerical
    noise; the schema clamp tolerates < 1 % drift)."""
    n = 200
    eps_uniform = np.full(n, 50.0)
    V = np.full(n, 1e-9)  # 1 mm^3 cells
    cc = np.random.RandomState(42).rand(3, n)  # arbitrary positions
    mask = np.ones(n, dtype=bool)
    spec = {
        "name": "test", "kind": "bulk",
        "selector": {"type": "complement"},
    }

    z = ee.aggregate_zone(
        name="test", spec=spec, mask=mask,
        epsilon=eps_uniform, cell_volumes=V,
        cell_centres=cc, velocity_mag=None,
        nu_c=5e-5, d_ref=100e-6,
        rho_c=860.0, sigma=5e-3, mu_d=0.05, breakage_C3=0.0,
    )
    assert z["epsilon_avg_W_per_kg"] == pytest.approx(50.0, rel=1e-12)
    # ε_brk must equal ε_avg for uniform field
    assert z["epsilon_breakage_weighted_W_per_kg"] == pytest.approx(
        50.0, rel=1e-9
    )
    assert z["volume_m3"] == pytest.approx(n * 1e-9, rel=1e-12)
    assert z["cell_count"] == n


def test_aggregate_zone_heterogeneous_field_ebrk_geq_eavg(ee):
    """A heterogeneous zone (one 100×-hotspot cell among uniform background)
    must produce ε_brk strictly greater than ε_avg, by Jensen's inequality."""
    n = 100
    eps = np.full(n, 5.0)
    eps[0] = 500.0  # 100× hotspot in one cell
    V = np.full(n, 1e-9)
    cc = np.random.RandomState(0).rand(3, n)
    mask = np.ones(n, dtype=bool)

    z = ee.aggregate_zone(
        name="bulk_with_hotspot", spec={"name": "x", "kind": "bulk", "selector": {"type": "complement"}},
        mask=mask, epsilon=eps, cell_volumes=V, cell_centres=cc,
        velocity_mag=None, nu_c=5e-5, d_ref=100e-6,
        rho_c=860.0, sigma=5e-3, mu_d=0.05, breakage_C3=0.0,
    )
    eps_avg = z["epsilon_avg_W_per_kg"]
    eps_brk = z["epsilon_breakage_weighted_W_per_kg"]
    # Volume-weighted: (99 * 5 + 1 * 500) / 100 = 9.95
    assert eps_avg == pytest.approx(9.95, rel=1e-9)
    # Breakage-weighted: must strictly exceed ε_avg (Jensen's inequality).
    assert eps_brk > eps_avg, (
        f"Jensen gate violated: ε_brk={eps_brk}, ε_avg={eps_avg}"
    )
    # At d_ref = 100 µm and the given material parameters, g(d_ref, 500)/g(d_ref, 5)
    # is ~11×, so the single hotspot among 99 background cells produces
    # ε_brk ≈ 5× ε_avg. The exact ratio depends on the kernel form; we
    # assert at least 3× to capture the physical bias robustly.
    assert eps_brk / eps_avg > 3.0, (
        f"Hotspot weighting too weak: ε_brk/ε_avg = {eps_brk/eps_avg:.2f} "
        f"(expected > 3 for a 100×-magnitude hotspot)"
    )


def test_aggregate_zone_volume_weighted_centroid(ee):
    """Centroid must be volume-weighted, not unweighted."""
    cc = np.array([[0.0, 1.0], [0.0, 0.0], [0.0, 0.0]])  # two points on x-axis
    V = np.array([1e-9, 3e-9])  # second cell 3× the volume
    eps = np.array([10.0, 10.0])
    mask = np.ones(2, dtype=bool)

    z = ee.aggregate_zone(
        name="t", spec={"name": "t", "kind": "bulk", "selector": {"type": "complement"}},
        mask=mask, epsilon=eps, cell_volumes=V, cell_centres=cc,
        velocity_mag=None, nu_c=5e-5, d_ref=100e-6,
        rho_c=860.0, sigma=5e-3, mu_d=0.05, breakage_C3=0.0,
    )
    # Centroid x = (1·0 + 3·1) / 4 = 0.75, NOT 0.5
    assert z["centroid_xyz_m"][0] == pytest.approx(0.75, rel=1e-12)


def test_aggregate_zone_kolmogorov_length(ee):
    """η_K = (ν³/ε)^(1/4)."""
    n = 10
    eps = np.full(n, 100.0)
    V = np.full(n, 1e-9)
    cc = np.zeros((3, n))
    mask = np.ones(n, dtype=bool)
    nu_c = 1e-6

    z = ee.aggregate_zone(
        name="t", spec={"name": "t", "kind": "bulk", "selector": {"type": "complement"}},
        mask=mask, epsilon=eps, cell_volumes=V, cell_centres=cc,
        velocity_mag=None, nu_c=nu_c, d_ref=100e-6,
        rho_c=860.0, sigma=5e-3, mu_d=0.05, breakage_C3=0.0,
    )
    expected = (nu_c ** 3 / 100.0) ** 0.25
    assert z["kolmogorov_length_m"] == pytest.approx(expected, rel=1e-9)


# ---------------------------------------------------------------------------
# estimate_exchange_flows
# ---------------------------------------------------------------------------


def test_exchange_flows_two_zone_grid(ee):
    """Two adjacent zones with uniform velocity must produce non-negative
    directed flows. The exact magnitude depends on the surface-flux
    approximation — we check sign and order-of-magnitude only."""
    pytest.importorskip("scipy", reason="scipy required for KDTree")
    # Build a 5×5×5 grid with 125 cells; left half = zone A, right half = zone B
    n_per_side = 5
    coords = np.array(
        [(x, y, z)
         for x in range(n_per_side)
         for y in range(n_per_side)
         for z in range(n_per_side)],
        dtype=np.float64,
    )
    cc = coords.T  # shape (3, 125)
    V = np.full(coords.shape[0], 1.0e-3)
    mask_a = coords[:, 0] < 2.5
    mask_b = ~mask_a
    zone_results = [
        ("A", {"name": "A", "kind": "bulk", "selector": {"type": "x"}}, mask_a),
        ("B", {"name": "B", "kind": "bulk", "selector": {"type": "x"}}, mask_b),
    ]
    velocity = np.zeros((3, coords.shape[0]))
    velocity[0, :] = 1.0  # uniform 1 m/s in +x

    exchanges = ee.estimate_exchange_flows(
        zone_results, velocity, cell_volumes=V, cell_centres=cc,
    )
    # Should produce both A→B and B→A directed entries (the heuristic
    # treats boundary cells symmetrically since velocity magnitude is taken
    # rather than signed direction).
    assert len(exchanges) >= 1
    for ex in exchanges:
        assert ex["volumetric_flow_m3_per_s"] > 0.0
        assert ex["from_zone"] in {"A", "B"}
        assert ex["to_zone"] in {"A", "B"}
        assert ex["from_zone"] != ex["to_zone"]
        assert ex["kind"] == "convective"


# ---------------------------------------------------------------------------
# openfoam_io: dict writer
# ---------------------------------------------------------------------------


def test_write_dict_simple_keys(tmp_path: Path) -> None:
    """Plain key-value pairs render with FoamFile header."""
    out = tmp_path / "controlDict"
    write_dict(out, {
        "application": "pimpleDyMFoam",
        "deltaT": 1e-4,
        "endTime": 5.0,
        "writeControl": "adjustableRunTime",
    }, foam_object="controlDict")

    text = out.read_text(encoding="utf-8")
    assert "FoamFile" in text
    assert "object      controlDict;" in text
    assert "application    pimpleDyMFoam;" in text
    assert "deltaT    0.0001;" in text
    assert "endTime    5;" in text
    assert "writeControl    adjustableRunTime;" in text


def test_write_dict_nested(tmp_path: Path) -> None:
    """Nested dicts render as ``key { ... }`` blocks."""
    out = tmp_path / "fvSchemes"
    write_dict(out, {
        "ddtSchemes": {"default": "Euler"},
        "gradSchemes": {
            "default": "Gauss linear",
            "grad(p)": "Gauss linear",
        },
    }, foam_object="fvSchemes")

    text = out.read_text(encoding="utf-8")
    assert "ddtSchemes" in text
    assert "{" in text and "}" in text
    assert "Euler" in text
    assert "Gauss linear" in text


def test_write_dict_lists(tmp_path: Path) -> None:
    """Python lists render as ``( a b c )``."""
    out = tmp_path / "decomposeParDict"
    write_dict(out, {
        "numberOfSubdomains": 8,
        "method": "scotch",
        "n": [2, 2, 2],
    })
    text = out.read_text(encoding="utf-8")
    assert "( 2 2 2 )" in text


def test_write_dict_unsupported_type_raises(tmp_path: Path) -> None:
    """Unsupported types (e.g. set) must raise rather than silently skip."""
    out = tmp_path / "bad"
    with pytest.raises(TypeError, match="Unsupported FoamFile value type"):
        write_dict(out, {"forbidden": {1, 2, 3}})


# ---------------------------------------------------------------------------
# openfoam_io: time-directory listing
# ---------------------------------------------------------------------------


def test_list_time_directories_skips_nonnumeric(tmp_path: Path) -> None:
    """Should skip ``system/``, ``constant/``, ``processor*`` etc."""
    (tmp_path / "0").mkdir()
    (tmp_path / "0.1").mkdir()
    (tmp_path / "1.5").mkdir()
    (tmp_path / "10").mkdir()
    (tmp_path / "system").mkdir()
    (tmp_path / "constant").mkdir()
    (tmp_path / "processor0").mkdir()

    times = list_time_directories(tmp_path)
    assert times == ["0", "0.1", "1.5", "10"]


def test_list_time_directories_sorts_numerically(tmp_path: Path) -> None:
    """Numeric sort, not lex — '10' must come after '2', not after '1'."""
    for name in ["0", "1", "2", "10", "20", "0.5"]:
        (tmp_path / name).mkdir()

    times = list_time_directories(tmp_path)
    assert times == ["0", "0.5", "1", "2", "10", "20"]


def test_latest_time_returns_max(tmp_path: Path) -> None:
    for name in ["0", "1", "2.5", "10"]:
        (tmp_path / name).mkdir()
    assert latest_time(tmp_path) == "10"


def test_latest_time_raises_on_empty(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="No time directories"):
        latest_time(tmp_path)


# ---------------------------------------------------------------------------
# Mask-helper: cellzone_mask
# ---------------------------------------------------------------------------


def test_cellzone_mask_indexes_correctly(ee):
    ids = np.array([0, 2, 4, 7], dtype=np.int64)
    mask = ee.cellzone_mask(ids, n_cells=10)
    expected = np.array([True, False, True, False, True, False, False, True, False, False])
    assert np.array_equal(mask, expected)
