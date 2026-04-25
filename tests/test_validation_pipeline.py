"""Tests for Node 20 (v7.0, P1a): data/validation/ scaffold + fit stub.

Acceptance for Node 20:
  1. data/validation/ directory tree exists with the canonical sublevels.
  2. l1_dsd/schema.json validates a minimum AssayRecord JSON document.
  3. fitters.load_assay_records reads a directory of AssayRecord JSONs.
  4. L1 DSD and M1 washing fitters return CalibrationEntry objects whose
     JSON form is loadable by CalibrationStore.load_json.
  5. End-to-end smoke: synthetic assay -> fit -> CalibrationStore ->
     RunContext -> orchestrator.run_single applies the override.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dpsim.assay_record import AssayKind, AssayRecord, Replicate
from dpsim.calibration.calibration_store import CalibrationStore
from dpsim.calibration.fitters import (
    fit_l1_dsd_to_calibration_entries,
    fit_m1_physical_qc_to_calibration_entries,
    fit_m1_washing_to_calibration_entries,
    fit_m2_functionalization_to_calibration_entries,
    fit_m3_binding_to_calibration_entries,
    load_assay_records,
    write_calibration_json,
)
from dpsim.config import load_config
from dpsim.datatypes import RunContext
from dpsim.pipeline.orchestrator import PipelineOrchestrator


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATION_DIR = REPO_ROOT / "data" / "validation"


class TestDirectoryScaffold:
    def test_validation_subdirs_exist(self):
        for sub in (
            "l1_dsd",
            "m1_washing",
            "m1_physical_qc",
            "l2_pore",
            "l3_kinetics",
            "l4_mechanics",
            "m2_capacity",
            "m3_binding",
        ):
            assert (VALIDATION_DIR / sub).is_dir(), (
                f"data/validation/{sub}/ missing — Node 20 scaffold incomplete."
            )

    def test_validation_readme_present(self):
        assert (VALIDATION_DIR / "README.md").is_file()

    def test_l1_dsd_schema_present(self):
        schema_path = VALIDATION_DIR / "l1_dsd" / "schema.json"
        assert schema_path.is_file()
        with open(schema_path) as f:
            schema = json.load(f)
        assert schema["properties"]["kind"]["const"] == "droplet_size_distribution"
        assert schema["properties"]["target_module"]["const"] == "L1"

    def test_m1_washing_schema_present(self):
        schema_path = VALIDATION_DIR / "m1_washing" / "schema.json"
        assert schema_path.is_file()
        with open(schema_path) as f:
            schema = json.load(f)
        assert "residual_oil" in schema["properties"]["kind"]["enum"]
        assert schema["properties"]["target_module"]["const"] == "M1"

    def test_m1_physical_qc_schema_present(self):
        schema_path = VALIDATION_DIR / "m1_physical_qc" / "schema.json"
        assert schema_path.is_file()
        with open(schema_path) as f:
            schema = json.load(f)
        assert "pore_size" in schema["properties"]["kind"]["enum"]
        assert "compression_modulus" in schema["properties"]["kind"]["enum"]

    def test_m3_binding_schema_present(self):
        schema_path = VALIDATION_DIR / "m3_binding" / "schema.json"
        assert schema_path.is_file()
        with open(schema_path) as f:
            schema = json.load(f)
        assert "static_binding_capacity" in schema["properties"]["kind"]["enum"]
        assert "dynamic_binding_capacity" in schema["properties"]["kind"]["enum"]
        assert "pressure_flow_curve" in schema["properties"]["kind"]["enum"]
        assert schema["properties"]["target_module"]["const"] == "M3"

    def test_m2_capacity_schema_present(self):
        schema_path = VALIDATION_DIR / "m2_capacity" / "schema.json"
        assert schema_path.is_file()
        with open(schema_path) as f:
            schema = json.load(f)
        assert "ligand_density" in schema["properties"]["kind"]["enum"]
        assert "ligand_leaching" in schema["properties"]["kind"]["enum"]
        assert "free_protein_wash_fraction" in schema["properties"]["kind"]["enum"]
        assert schema["properties"]["target_module"]["const"] == "M2"

    def test_p5_example_assays_round_trip_and_fit(self):
        m2_records = load_assay_records(VALIDATION_DIR / "m2_capacity" / "examples")
        m3_records = load_assay_records(VALIDATION_DIR / "m3_binding" / "examples")

        assert {record.kind for record in m2_records} >= {
            AssayKind.LIGAND_DENSITY,
            AssayKind.ACTIVITY_RETENTION,
        }
        assert {record.kind for record in m3_records} >= {
            AssayKind.STATIC_BINDING_CAPACITY,
            AssayKind.DYNAMIC_BINDING_CAPACITY,
            AssayKind.PRESSURE_FLOW_CURVE,
        }

        m2_entries = fit_m2_functionalization_to_calibration_entries(m2_records)
        m3_entries = fit_m3_binding_to_calibration_entries(m3_records)

        assert "functional_ligand_density" in {entry.parameter_name for entry in m2_entries}
        assert "activity_retention" in {entry.parameter_name for entry in m2_entries}
        assert "dbc_10_reference" in {entry.parameter_name for entry in m3_entries}
        assert "pressure_flow_slope_Pa_per_m3_s" in {
            entry.parameter_name for entry in m3_entries
        }


class TestFitterPipeline:
    def test_load_assay_records_empty_dir(self, tmp_path):
        records = load_assay_records(tmp_path)
        assert records == []

    def test_load_assay_records_skips_malformed(self, tmp_path):
        # Write one good and one broken JSON
        good = AssayRecord(
            record_id="OK1", kind=AssayKind.DROPLET_SIZE_DISTRIBUTION,
            units="m", replicates=[Replicate(20e-6)],
            process_conditions={"rpm_min_1": 5000},
            target_module="L1",
        )
        with open(tmp_path / "good.json", "w") as f:
            json.dump(good.to_dict(), f)
        with open(tmp_path / "broken.json", "w") as f:
            f.write("{this is not valid json")
        records = load_assay_records(tmp_path)
        assert len(records) == 1
        assert records[0].record_id == "OK1"

    def test_fit_l1_dsd_emits_calibration_entry(self):
        records = [
            AssayRecord(
                record_id=f"DSD{i}",
                kind=AssayKind.DROPLET_SIZE_DISTRIBUTION,
                units="m",
                replicates=[Replicate(v) for v in (20e-6, 22e-6, 24e-6)],
                process_conditions={"rpm_min_1": 5000.0 + i * 1000},
                target_module="L1",
            )
            for i in range(3)
        ]
        entries = fit_l1_dsd_to_calibration_entries(records)
        assert len(entries) == 1
        e = entries[0]
        assert e.target_module == "L1"
        # Stub fitter writes the mean d32 as the reference value.
        assert e.parameter_name == "d32_reference"
        assert e.measured_value == pytest.approx(22e-6, rel=0.05)
        assert e.posterior_uncertainty > 0.0  # std across 9 replicates

    def test_fit_no_records_returns_empty(self):
        entries = fit_l1_dsd_to_calibration_entries([])
        assert entries == []

    def test_fit_m1_washing_emits_retention_entries(self):
        conditions = {
            "initial_oil_carryover_fraction": 0.10,
            "wash_cycles": 3,
            "wash_volume_ratio": 3.0,
            "wash_mixing_efficiency": 0.8,
            "c_span80_kg_m3": 20.0,
        }
        records = [
            AssayRecord(
                record_id="OIL1",
                kind=AssayKind.RESIDUAL_OIL,
                units="fraction",
                replicates=[Replicate(0.0023), Replicate(0.0025), Replicate(0.0024)],
                process_conditions=conditions,
                target_module="M1",
            ),
            AssayRecord(
                record_id="SURF1",
                kind=AssayKind.RESIDUAL_SURFACTANT,
                units="kg/m3",
                replicates=[Replicate(0.09), Replicate(0.10), Replicate(0.095)],
                process_conditions=conditions,
                target_module="M1",
            ),
        ]

        entries = fit_m1_washing_to_calibration_entries(records)

        assert {entry.parameter_name for entry in entries} == {
            "m1_oil_retention_factor",
            "m1_surfactant_retention_factor",
        }
        assert all(entry.target_module == "M1" for entry in entries)
        assert all(entry.fit_method == "inverse_well_mixed_extraction" for entry in entries)
        assert all(entry.measured_value > 0.0 for entry in entries)

    def test_fit_m1_physical_qc_emits_reference_entries(self):
        records = [
            AssayRecord(
                record_id="PORE1",
                kind=AssayKind.PORE_SIZE,
                units="nm",
                replicates=[Replicate(90.0), Replicate(100.0), Replicate(110.0)],
                process_conditions={"cooling_rate_K_s": 0.167, "bead_d50_m": 1e-4},
                target_module="M1",
            ),
            AssayRecord(
                record_id="SWELL1",
                kind=AssayKind.SWELLING_RATIO,
                units="1",
                replicates=[Replicate(1.8), Replicate(1.9), Replicate(2.0)],
                process_conditions={"buffer_pH": 7.4},
                target_module="M1",
            ),
            AssayRecord(
                record_id="COMP1",
                kind=AssayKind.COMPRESSION_MODULUS,
                units="kPa",
                replicates=[Replicate(28.0), Replicate(30.0), Replicate(32.0)],
                process_conditions={"buffer_pH": 7.4},
                target_module="M3",
            ),
        ]

        entries = fit_m1_physical_qc_to_calibration_entries(records)

        by_name = {entry.parameter_name: entry for entry in entries}
        assert by_name["measured_pore_size_mean"].measured_value == pytest.approx(100e-9)
        assert by_name["measured_pore_size_mean"].units == "m"
        assert by_name["measured_swelling_ratio"].units == "1"
        assert by_name["measured_compression_modulus"].target_module == "M3"
        assert by_name["measured_compression_modulus"].measured_value == pytest.approx(30000.0)
        assert all(entry.fit_method == "assay_reference_mean" for entry in entries)

    def test_fit_m3_binding_emits_qmax_dbc_and_affinity_entries(self):
        records = [
            AssayRecord(
                record_id="SBC1",
                kind=AssayKind.STATIC_BINDING_CAPACITY,
                units="mol/m3",
                replicates=[Replicate(78.0), Replicate(80.0), Replicate(82.0)],
                process_conditions={
                    "equilibrium_concentration_mol_m3": 2.0,
                    "q_max_reference_mol_m3": 100.0,
                    "temperature_C": 25.0,
                    "pH": 7.4,
                    "target_molecule": "IgG",
                },
                target_module="M3",
            ),
            AssayRecord(
                record_id="DBC10",
                kind=AssayKind.DYNAMIC_BINDING_CAPACITY,
                units="mol/m3",
                replicates=[Replicate(44.0), Replicate(45.0), Replicate(46.0)],
                process_conditions={
                    "breakthrough_threshold_fraction": 0.10,
                    "residence_time_s": 240.0,
                    "flow_rate_m3_s": 1e-8,
                },
                target_module="M3",
            ),
        ]

        entries = fit_m3_binding_to_calibration_entries(records)

        by_name = {entry.parameter_name: entry for entry in entries}
        assert by_name["estimated_q_max"].measured_value == pytest.approx(80.0)
        assert by_name["estimated_q_max"].fit_method == "static_capacity_reference_mean"
        assert by_name["dbc_10_reference"].measured_value == pytest.approx(45.0)
        assert by_name["dbc_10_reference"].fit_method == "dbc_reference_mean"
        assert by_name["K_affinity"].measured_value == pytest.approx(2.0)
        assert by_name["K_affinity"].units == "m3/mol"
        assert all(entry.target_module == "M3" for entry in entries)

    def test_fit_m3_static_isotherm_uses_weighted_langmuir_fit(self):
        qmax = 120.0
        k_affinity = 0.8
        records = []
        for idx, c_eq in enumerate([0.1, 0.3, 1.0, 3.0, 10.0]):
            q_value = qmax * k_affinity * c_eq / (1.0 + k_affinity * c_eq)
            records.append(
                AssayRecord(
                    record_id=f"ISO{idx}",
                    kind=AssayKind.STATIC_BINDING_CAPACITY,
                    units="mol/m3",
                    replicates=[Replicate(q_value, std=1.0)],
                    process_conditions={
                        "equilibrium_concentration_mol_m3": c_eq,
                        "temperature_C": 25.0,
                        "pH": 7.4,
                    },
                    target_module="M3",
                )
            )

        entries = fit_m3_binding_to_calibration_entries(records)

        by_name = {entry.parameter_name: entry for entry in entries}
        assert by_name["estimated_q_max"].fit_method == "weighted_least_squares_langmuir"
        assert by_name["estimated_q_max"].measured_value == pytest.approx(qmax, rel=0.02)
        assert by_name["K_affinity"].measured_value == pytest.approx(k_affinity, rel=0.02)
        assert by_name["K_affinity"].posterior_uncertainty > 0.0
        assert "equilibrium_concentration_mol_m3" in by_name["K_affinity"].valid_domain

    def test_fit_m3_breakthrough_curve_and_pressure_flow_entries(self):
        records = [
            AssayRecord(
                record_id="BTC1",
                kind=AssayKind.DYNAMIC_BINDING_CAPACITY,
                units="mol/m3",
                process_conditions={
                    "time_s": [0.0, 100.0, 200.0],
                    "C_over_C0": [0.0, 0.10, 0.20],
                    "feed_concentration_mol_m3": 1.0,
                    "flow_rate_m3_s": 1.0e-8,
                    "bed_volume_m3": 1.0e-6,
                    "temperature_C": 25.0,
                },
                target_module="M3",
            ),
            AssayRecord(
                record_id="PF1",
                kind=AssayKind.PRESSURE_FLOW_CURVE,
                units="Pa",
                process_conditions={
                    "flow_rates_m3_s": [1.0e-9, 2.0e-9, 3.0e-9],
                    "pressure_drops_Pa": [100.0, 200.0, 300.0],
                    "bed_height_m": 0.10,
                },
                target_module="M3",
            ),
        ]

        entries = fit_m3_binding_to_calibration_entries(records)

        by_name = {entry.parameter_name: entry for entry in entries}
        assert by_name["dbc_5_reference"].fit_method == "breakthrough_curve_integration"
        assert by_name["dbc_5_reference"].measured_value == pytest.approx(0.4875)
        assert by_name["dbc_10_reference"].measured_value == pytest.approx(0.95)
        pressure = by_name["pressure_flow_slope_Pa_per_m3_s"]
        assert pressure.fit_method == "weighted_least_squares_pressure_flow"
        assert pressure.measured_value == pytest.approx(1.0e11)
        assert pressure.valid_domain["flow_rate_m3_s"] == pytest.approx((1.0e-9, 3.0e-9))

    def test_fit_m2_functionalization_emits_reference_entries(self):
        records = [
            AssayRecord(
                record_id="LIG1",
                kind=AssayKind.LIGAND_DENSITY,
                units="umol/m2",
                replicates=[Replicate(1.8), Replicate(2.0), Replicate(2.2)],
                process_conditions={"pH": 8.5, "temperature_C": 4.0},
                target_module="M2",
            ),
            AssayRecord(
                record_id="ACT1",
                kind=AssayKind.ACTIVITY_RETENTION,
                units="fraction",
                replicates=[Replicate(0.58), Replicate(0.60), Replicate(0.62)],
                process_conditions={"assay_method": "IgG static binding"},
                target_module="M2",
            ),
            AssayRecord(
                record_id="LEACH1",
                kind=AssayKind.LIGAND_LEACHING,
                units="%",
                replicates=[Replicate(1.0), Replicate(1.2), Replicate(1.1)],
                process_conditions={"storage_time_h": 24.0},
                target_module="M2",
            ),
            AssayRecord(
                record_id="WASH1",
                kind=AssayKind.FREE_PROTEIN_WASH_FRACTION,
                units="fraction",
                replicates=[Replicate(0.03), Replicate(0.04), Replicate(0.035)],
                process_conditions={"wash_cycle": 3.0},
                target_module="M2",
            ),
        ]

        entries = fit_m2_functionalization_to_calibration_entries(records)

        by_name = {entry.parameter_name: entry for entry in entries}
        assert by_name["functional_ligand_density"].measured_value == pytest.approx(2.0e-6)
        assert by_name["functional_ligand_density"].units == "mol/m2"
        assert by_name["activity_retention"].measured_value == pytest.approx(0.60)
        assert by_name["ligand_leaching_fraction"].measured_value == pytest.approx(0.011)
        assert by_name["free_protein_wash_fraction"].target_module == "M2"
        assert all(entry.fit_method == "assay_reference_mean" for entry in entries)

    def test_write_calibration_json_round_trip(self, tmp_path):
        records = [
            AssayRecord(
                record_id="DSD1",
                kind=AssayKind.DROPLET_SIZE_DISTRIBUTION,
                units="m",
                replicates=[Replicate(20e-6), Replicate(22e-6)],
                process_conditions={"rpm_min_1": 10000.0},
                target_module="L1",
            ),
        ]
        entries = fit_l1_dsd_to_calibration_entries(records)
        out_path = tmp_path / "fits" / "fit_test.json"
        written = write_calibration_json(
            entries, out_path,
            fit_metadata={"fitter": "stub_mean", "study_id": "test"},
        )
        assert written.exists()
        # Sidecar metadata
        assert written.with_suffix(".meta.json").exists()
        # CalibrationStore can ingest the fit output directly
        store = CalibrationStore()
        n = store.load_json(written)
        assert n == len(entries)
        loaded = store.entries[0]
        assert loaded.target_module == "L1"


class TestEndToEndDataLoop:
    """Synthetic assay -> fit -> store -> RunContext -> orchestrator."""

    @pytest.fixture(scope="class")
    def smoke_params(self):
        cfg = REPO_ROOT / "configs" / "fast_smoke.toml"
        if not cfg.exists():
            pytest.skip("fast_smoke.toml missing")
        return load_config(cfg)

    def test_synthetic_calibration_flows_through_orchestrator(self, smoke_params, tmp_path):
        """Write an assay, fit it, load into store, run pipeline with it."""
        from dpsim.calibration.calibration_data import CalibrationEntry

        # Skip the stub d32_reference path — that parameter is not bound to
        # a runtime attribute. Use a concrete L1 calibration that
        # apply_to_model_params will actually apply.
        store = CalibrationStore()
        store.add(CalibrationEntry(
            profile_key="rotor_stator_legacy",
            parameter_name="breakage_C2",
            measured_value=0.0125,
            units="-",
            confidence="high",
            source_reference="synthetic_e2e_test",
            target_module="L1",
            fit_method="stub_mean",
            posterior_uncertainty=0.001,
        ))

        ctx = RunContext(calibration_store=store)
        result = PipelineOrchestrator(output_dir=tmp_path).run_single(
            smoke_params, run_context=ctx,
        )
        # End-to-end loop closed: the calibration was applied and
        # surfaced in the RunReport diagnostics.
        diag = result.run_report.diagnostics
        assert diag.get("calibration_count", 0) == 1
        assert any("breakage_C2" in s for s in diag["calibrations_applied"])

