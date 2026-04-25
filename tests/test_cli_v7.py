"""Tests for Node 24 (v7.0.1, audit N4): batch / dossier / ingest CLI subcommands.

Acceptance for Node 24:
  1. ``python -m dpsim --help`` lists batch, dossier, ingest as commands.
  2. Each command's ``--help`` produces non-empty output without crash.
  3. ``batch`` runs the fast_smoke config and prints quantile-resolved
     bead radii + mass fractions.
  4. ``dossier`` runs the fast_smoke config and writes a valid
     ProcessDossier JSON to the requested path.
  5. ``ingest L1``, ``ingest M1``, ``ingest M1QC``, ``ingest M2``, and ``ingest M3`` read
     AssayRecord JSONs from a directory and write CalibrationStore-loadable
     fit JSON.
  6. ``--quantiles`` parser rejects out-of-range / malformed input with a
     clear error.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SMOKE_CFG = REPO_ROOT / "configs" / "fast_smoke.toml"


def _run_cli(*args, cwd=None):
    """Invoke `python -m dpsim ...` and return CompletedProcess."""
    return subprocess.run(
        [sys.executable, "-m", "dpsim", *args],
        cwd=cwd or REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )


class TestCliRegistration:
    def test_top_level_help_lists_new_commands(self):
        cp = _run_cli("--help")
        assert cp.returncode == 0
        for cmd in ("batch", "dossier", "ingest", "recipe"):
            assert cmd in cp.stdout, f"CLI --help missing {cmd!r}: {cp.stdout!r}"

    def test_each_subcommand_help_works(self):
        for cmd in ("batch", "dossier", "ingest", "recipe"):
            cp = _run_cli(cmd, "--help")
            assert cp.returncode == 0, f"`dpsim {cmd} --help` failed: {cp.stderr}"
            assert "usage" in cp.stdout.lower()


class TestBatchCommand:
    def test_batch_runs_fast_smoke(self, tmp_path):
        if not SMOKE_CFG.exists():
            pytest.skip("fast_smoke.toml missing")
        cp = _run_cli(
            "batch", str(SMOKE_CFG),
            "--quantiles", "0.25,0.50,0.75",
            "--output", str(tmp_path),
            "--quiet",
        )
        assert cp.returncode == 0, cp.stderr
        assert "Batch Variability Results" in cp.stdout
        assert "Per-quantile representative bead radii" in cp.stdout
        # Quantile lines must be present
        for q in ("0.250", "0.500", "0.750"):
            assert f"q={q}" in cp.stdout

    def test_batch_rejects_bad_quantiles(self, tmp_path):
        if not SMOKE_CFG.exists():
            pytest.skip("fast_smoke.toml missing")
        cp = _run_cli(
            "batch", str(SMOKE_CFG),
            "--quantiles", "0.25,1.5,0.75",  # 1.5 is out of (0,1)
            "--output", str(tmp_path),
            "--quiet",
        )
        assert cp.returncode != 0
        assert "0,1" in cp.stderr or "must" in cp.stderr.lower()


class TestRecipeCommand:
    def test_recipe_export_default_and_validate_toml(self, tmp_path):
        out = tmp_path / "default_recipe.toml"
        cp = _run_cli("recipe", "export-default", "--output", str(out))
        assert cp.returncode == 0, cp.stderr
        assert out.exists()

        cp = _run_cli("recipe", "validate", str(out))
        assert cp.returncode == 0, cp.stderr
        assert "validation: ok" in cp.stdout

    def test_lifecycle_accepts_recipe_json(self, tmp_path):
        from dpsim.core.process_recipe import default_affinity_media_recipe
        from dpsim.core.recipe_io import save_process_recipe

        if not SMOKE_CFG.exists():
            pytest.skip("fast_smoke.toml missing")
        recipe_path = save_process_recipe(
            default_affinity_media_recipe(),
            tmp_path / "recipe.json",
        )
        cp = _run_cli(
            "lifecycle",
            str(SMOKE_CFG),
            "--recipe",
            str(recipe_path),
            "--no-dsd",
            "--output",
            str(tmp_path / "lifecycle"),
            "--quiet",
        )
        assert cp.returncode == 0, cp.stderr
        assert "Downstream Lifecycle Results" in cp.stdout
        assert "M1 DSD:" in cp.stdout
        assert "M1 wash residuals:" in cp.stdout
        assert "M1 wash model:" in cp.stdout
        assert "M3 DBC10" in cp.stdout

    def test_lifecycle_adaptive_dsd_mode_prints_tail_metric(self, tmp_path):
        if not SMOKE_CFG.exists():
            pytest.skip("fast_smoke.toml missing")
        cp = _run_cli(
            "lifecycle",
            str(SMOKE_CFG),
            "--dsd-mode",
            "adaptive",
            "--dsd-max-representatives",
            "5",
            "--output",
            str(tmp_path / "lifecycle_adaptive"),
            "--quiet",
        )
        assert cp.returncode == 0, cp.stderr
        assert "DSD screen:" in cp.stdout
        assert "mode = adaptive_quantiles_5" in cp.stdout
        assert "dP p95" in cp.stdout

    def test_lifecycle_dsd_breakthrough_prints_dbc_tail_metric(self, tmp_path):
        if not SMOKE_CFG.exists():
            pytest.skip("fast_smoke.toml missing")
        cp = _run_cli(
            "lifecycle",
            str(SMOKE_CFG),
            "--dsd-mode",
            "adaptive",
            "--dsd-max-representatives",
            "2",
            "--dsd-breakthrough",
            "--output",
            str(tmp_path / "lifecycle_dsd_breakthrough"),
            "--quiet",
        )
        assert cp.returncode == 0, cp.stderr
        assert "DSD breakthrough:" in cp.stdout
        assert "DBC10 mean/p50/p95" in cp.stdout


class TestDossierCommand:
    def test_dossier_writes_valid_json(self, tmp_path):
        if not SMOKE_CFG.exists():
            pytest.skip("fast_smoke.toml missing")
        out = tmp_path / "dossier.json"
        cp = _run_cli(
            "dossier", str(SMOKE_CFG),
            "--output", str(out),
            "--notes", "v7.0.1 CLI smoke",
            "--quiet",
        )
        assert cp.returncode == 0, cp.stderr
        assert out.exists()
        with open(out) as f:
            d = json.load(f)
        # Schema sanity
        assert d["dossier_kind"] == "ProcessDossier"
        assert d["schema_version"] == "1.0"
        assert d["notes"] == "v7.0.1 CLI smoke"
        assert "L1" in d["result_summary"]
        assert d["run_report"]["min_evidence_tier"] != ""
        # CLI summary printed the dossier path
        assert "dossier written to" in cp.stdout


class TestIngestCommand:
    def test_ingest_l1_round_trip(self, tmp_path):
        from dpsim.assay_record import AssayKind, AssayRecord, Replicate

        # Build a synthetic AssayRecord JSON
        assay_dir = tmp_path / "assays"
        assay_dir.mkdir()
        rec = AssayRecord(
            record_id="CLI-INGEST-001",
            kind=AssayKind.DROPLET_SIZE_DISTRIBUTION,
            units="m",
            replicates=[Replicate(20e-6), Replicate(22e-6), Replicate(24e-6)],
            process_conditions={"rpm_min_1": 5000.0},
            target_module="L1",
        )
        with open(assay_dir / "dsd_001.json", "w") as f:
            json.dump(rec.to_dict(), f)

        out = tmp_path / "fit.json"
        cp = _run_cli(
            "ingest", "L1",
            "--assay-dir", str(assay_dir),
            "--output", str(out),
        )
        assert cp.returncode == 0, cp.stderr
        assert out.exists()
        # Output must be loadable by CalibrationStore
        from dpsim.calibration.calibration_store import CalibrationStore
        store = CalibrationStore()
        n = store.load_json(out)
        assert n >= 1
        assert store.entries[0].target_module == "L1"
        # Sidecar metadata file is written
        assert out.with_suffix(".meta.json").exists()

    def test_ingest_m1_washing_round_trip(self, tmp_path):
        from dpsim.assay_record import AssayKind, AssayRecord, Replicate

        assay_dir = tmp_path / "m1_assays"
        assay_dir.mkdir()
        conditions = {
            "initial_oil_carryover_fraction": 0.10,
            "wash_cycles": 3,
            "wash_volume_ratio": 3.0,
            "wash_mixing_efficiency": 0.8,
            "c_span80_kg_m3": 20.0,
        }
        records = [
            AssayRecord(
                record_id="CLI-M1-OIL",
                kind=AssayKind.RESIDUAL_OIL,
                units="fraction",
                replicates=[Replicate(0.0024), Replicate(0.0026)],
                process_conditions=conditions,
                target_module="M1",
            ),
            AssayRecord(
                record_id="CLI-M1-SURF",
                kind=AssayKind.RESIDUAL_SURFACTANT,
                units="kg/m3",
                replicates=[Replicate(0.09), Replicate(0.10)],
                process_conditions=conditions,
                target_module="M1",
            ),
        ]
        for idx, record in enumerate(records):
            with open(assay_dir / f"m1_{idx}.json", "w") as f:
                json.dump(record.to_dict(), f)

        out = tmp_path / "m1_washing_fit.json"
        cp = _run_cli(
            "ingest", "M1",
            "--assay-dir", str(assay_dir),
            "--output", str(out),
        )

        assert cp.returncode == 0, cp.stderr
        assert out.exists()
        from dpsim.calibration.calibration_store import CalibrationStore
        store = CalibrationStore()
        n = store.load_json(out)
        assert n == 2
        assert {entry.target_module for entry in store.entries} == {"M1"}
        assert "inverse_well_mixed_extraction" in out.with_suffix(".meta.json").read_text()

    def test_ingest_m1_physical_qc_round_trip(self, tmp_path):
        from dpsim.assay_record import AssayKind, AssayRecord, Replicate

        assay_dir = tmp_path / "m1_qc_assays"
        assay_dir.mkdir()
        records = [
            AssayRecord(
                record_id="CLI-M1-PORE",
                kind=AssayKind.PORE_SIZE,
                units="nm",
                replicates=[Replicate(90.0), Replicate(100.0), Replicate(110.0)],
                process_conditions={"cooling_rate_K_s": 0.167},
                target_module="M1",
            ),
            AssayRecord(
                record_id="CLI-M1-COMP",
                kind=AssayKind.COMPRESSION_MODULUS,
                units="kPa",
                replicates=[Replicate(28.0), Replicate(30.0), Replicate(32.0)],
                process_conditions={"buffer_pH": 7.4},
                target_module="M3",
            ),
        ]
        for idx, record in enumerate(records):
            with open(assay_dir / f"m1_qc_{idx}.json", "w") as f:
                json.dump(record.to_dict(), f)

        out = tmp_path / "m1_physical_qc_fit.json"
        cp = _run_cli(
            "ingest", "M1QC",
            "--assay-dir", str(assay_dir),
            "--output", str(out),
        )

        assert cp.returncode == 0, cp.stderr
        assert out.exists()
        from dpsim.calibration.calibration_store import CalibrationStore
        store = CalibrationStore()
        n = store.load_json(out)
        assert n == 2
        assert {entry.fit_method for entry in store.entries} == {"assay_reference_mean"}
        assert "measured_pore_size_mean" in {entry.parameter_name for entry in store.entries}
        assert "assay_reference_mean" in out.with_suffix(".meta.json").read_text()

    def test_ingest_m3_binding_round_trip(self, tmp_path):
        from dpsim.assay_record import AssayKind, AssayRecord, Replicate

        assay_dir = tmp_path / "m3_assays"
        assay_dir.mkdir()
        records = [
            AssayRecord(
                record_id="CLI-M3-SBC",
                kind=AssayKind.STATIC_BINDING_CAPACITY,
                units="mol/m3",
                replicates=[Replicate(78.0), Replicate(80.0), Replicate(82.0)],
                process_conditions={
                    "equilibrium_concentration_mol_m3": 2.0,
                    "q_max_reference_mol_m3": 100.0,
                    "target_molecule": "IgG",
                },
                target_module="M3",
            ),
            AssayRecord(
                record_id="CLI-M3-DBC10",
                kind=AssayKind.DYNAMIC_BINDING_CAPACITY,
                units="mol/m3",
                replicates=[Replicate(44.0), Replicate(45.0), Replicate(46.0)],
                process_conditions={"breakthrough_threshold_fraction": 0.10},
                target_module="M3",
            ),
        ]
        for idx, record in enumerate(records):
            with open(assay_dir / f"m3_{idx}.json", "w") as f:
                json.dump(record.to_dict(), f)

        out = tmp_path / "m3_binding_fit.json"
        cp = _run_cli(
            "ingest", "M3",
            "--assay-dir", str(assay_dir),
            "--output", str(out),
        )

        assert cp.returncode == 0, cp.stderr
        assert out.exists()
        from dpsim.calibration.calibration_store import CalibrationStore
        store = CalibrationStore()
        n = store.load_json(out)
        assert n == 3
        assert {entry.target_module for entry in store.entries} == {"M3"}
        assert "estimated_q_max" in {entry.parameter_name for entry in store.entries}
        assert "dbc_10_reference" in {entry.parameter_name for entry in store.entries}
        assert "K_affinity" in {entry.parameter_name for entry in store.entries}
        assert "m3_binding_capacity" in out.with_suffix(".meta.json").read_text()

    def test_ingest_m2_functionalization_round_trip(self, tmp_path):
        from dpsim.assay_record import AssayKind, AssayRecord, Replicate

        assay_dir = tmp_path / "m2_assays"
        assay_dir.mkdir()
        records = [
            AssayRecord(
                record_id="CLI-M2-LIG",
                kind=AssayKind.LIGAND_DENSITY,
                units="umol/m2",
                replicates=[Replicate(1.8), Replicate(2.0), Replicate(2.2)],
                process_conditions={"target_molecule": "IgG"},
                target_module="M2",
            ),
            AssayRecord(
                record_id="CLI-M2-WASH",
                kind=AssayKind.FREE_PROTEIN_WASH_FRACTION,
                units="fraction",
                replicates=[Replicate(0.03), Replicate(0.04), Replicate(0.035)],
                process_conditions={"wash_cycle": 3.0},
                target_module="M2",
            ),
        ]
        for idx, record in enumerate(records):
            with open(assay_dir / f"m2_{idx}.json", "w") as f:
                json.dump(record.to_dict(), f)

        out = tmp_path / "m2_functionalization_fit.json"
        cp = _run_cli(
            "ingest", "M2",
            "--assay-dir", str(assay_dir),
            "--output", str(out),
        )

        assert cp.returncode == 0, cp.stderr
        assert out.exists()
        from dpsim.calibration.calibration_store import CalibrationStore
        store = CalibrationStore()
        n = store.load_json(out)
        assert n == 2
        assert {entry.target_module for entry in store.entries} == {"M2"}
        assert "functional_ligand_density" in {entry.parameter_name for entry in store.entries}
        assert "free_protein_wash_fraction" in {entry.parameter_name for entry in store.entries}
        assert "m2_functionalization_reference" in out.with_suffix(".meta.json").read_text()

    def test_ingest_missing_dir_clear_error(self, tmp_path):
        cp = _run_cli(
            "ingest", "L1",
            "--assay-dir", str(tmp_path / "does_not_exist"),
        )
        assert cp.returncode != 0
        assert "does not exist" in cp.stderr

    def test_ingest_empty_dir_warns(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        out = tmp_path / "fit.json"
        cp = _run_cli(
            "ingest", "L1",
            "--assay-dir", str(empty),
            "--output", str(out),
        )
        # Empty dir is a warning, not an error
        assert cp.returncode == 0, cp.stderr
        assert "no AssayRecord JSONs" in cp.stdout
        assert not out.exists()


class TestUncertaintyCommand:
    """Audit N5 (Node 25): uncertainty CLI surfaces --n-jobs and --engine."""

    def test_unified_engine_default(self, tmp_path):
        if not SMOKE_CFG.exists():
            pytest.skip("fast_smoke.toml missing")
        cp = _run_cli(
            "uncertainty", str(SMOKE_CFG),
            "--n-samples", "3", "--seed", "42",
        )
        assert cp.returncode == 0, cp.stderr
        # Unified output schema markers
        assert "Unified UQ" in cp.stdout
        assert "kinds=[material_property]" in cp.stdout
        assert "engine=unified" in cp.stdout

    def test_legacy_engine_flag_routes_through_unified(self, tmp_path):
        """Node 30: --engine legacy runs the merged engine with no
        posterior injection (scripts get the same MaterialProperties
        perturbations they got in v7.0.x, but in the unified output
        schema). The legacy UncertaintyResult header is gone."""
        if not SMOKE_CFG.exists():
            pytest.skip("fast_smoke.toml missing")
        cp = _run_cli(
            "uncertainty", str(SMOKE_CFG),
            "--n-samples", "3", "--seed", "42",
            "--engine", "legacy",
        )
        assert cp.returncode == 0, cp.stderr
        assert "engine=legacy" in cp.stdout
        assert "Unified UQ" in cp.stdout
        # Without a calibration store, no posterior kinds are sampled.
        assert "kinds=[material_property]" in cp.stdout

    def test_n_jobs_flag_accepted(self, tmp_path):
        """--n-jobs > 1 must not crash (joblib clamps; loky safe)."""
        if not SMOKE_CFG.exists():
            pytest.skip("fast_smoke.toml missing")
        cp = _run_cli(
            "uncertainty", str(SMOKE_CFG),
            "--n-samples", "2", "--seed", "7",
            "--n-jobs", "2",
            "--engine", "legacy",
        )
        assert cp.returncode == 0, cp.stderr

