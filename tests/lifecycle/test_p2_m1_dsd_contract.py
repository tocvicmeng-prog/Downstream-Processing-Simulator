from pathlib import Path

import pytest

from dpsim.calibration import CalibrationEntry, CalibrationStore
from dpsim.config import load_config
from dpsim.datatypes import RunContext
from dpsim.lifecycle import DownstreamProcessOrchestrator


@pytest.fixture(scope="module")
def p2_lifecycle_result(tmp_path_factory):
    repo_root = Path(__file__).resolve().parents[2]
    params = load_config(repo_root / "configs" / "fast_smoke.toml")
    return DownstreamProcessOrchestrator(
        output_dir=tmp_path_factory.mktemp("p2_m1_dsd")
    ).run(
        params=params,
        propagate_dsd=True,
        dsd_quantiles=(0.10, 0.50, 0.90),
    )


def test_m1_contract_exports_full_bead_size_distribution(p2_lifecycle_result):
    contract = p2_lifecycle_result.m1_contract
    payload = contract.bead_size_distribution

    assert payload is not None
    assert len(payload.diameter_bins_m) == len(p2_lifecycle_result.m1_result.emulsification.d_bins)
    assert sum(payload.volume_fraction) == pytest.approx(1.0, abs=1e-9)
    assert payload.volume_cdf[-1] == pytest.approx(1.0, abs=1e-12)
    assert payload.d10_m == pytest.approx(p2_lifecycle_result.m1_result.emulsification.d10)
    assert payload.d50_m == pytest.approx(p2_lifecycle_result.m1_result.emulsification.d50)
    assert payload.d90_m == pytest.approx(p2_lifecycle_result.m1_result.emulsification.d90)
    assert contract.validate_units() == []


def test_dsd_quantiles_transfer_into_downstream_screen(p2_lifecycle_result):
    payload = p2_lifecycle_result.m1_contract.bead_size_distribution
    expected_rows = payload.quantile_table((0.10, 0.50, 0.90))
    variants = p2_lifecycle_result.dsd_variants
    summary = p2_lifecycle_result.dsd_summary

    assert summary is not None
    assert summary.n_quantiles == 3
    assert summary.dsd_source == payload.source
    assert summary.n_dsd_bins == len(payload.diameter_bins_m)
    assert summary.d50_m == pytest.approx(payload.d50_m)
    assert sum(v.mass_fraction for v in variants) == pytest.approx(1.0, abs=1e-12)
    assert [v.quantile for v in variants] == [0.10, 0.50, 0.90]
    assert [v.bead_diameter_m for v in variants] == pytest.approx(
        [row["diameter_m"] for row in expected_rows]
    )
    assert summary.quantile_selection == "representative"
    assert summary.pressure_drop_weighted_p95_Pa >= summary.pressure_drop_weighted_p50_Pa
    assert summary.q_max_weighted_p50_mol_m3 >= 0.0


def test_adaptive_dsd_mode_uses_distribution_bins_when_runtime_allows(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    params = load_config(repo_root / "configs" / "fast_smoke.toml")

    result = DownstreamProcessOrchestrator(output_dir=tmp_path).run(
        params=params,
        propagate_dsd=True,
        dsd_mode="adaptive",
        dsd_max_representatives=64,
    )

    payload = result.m1_contract.bead_size_distribution
    expected_bins = sum(1 for w in payload.volume_fraction if w > 1e-12)
    summary = result.dsd_summary

    assert summary.quantile_selection == "distribution_bins"
    assert summary.n_quantiles == expected_bins
    assert summary.n_quantiles > 3
    assert summary.represented_mass_fraction == pytest.approx(1.0, abs=1e-9)
    assert sum(v.mass_fraction for v in result.dsd_variants) == pytest.approx(1.0, abs=1e-9)
    assert {v.representative_source for v in result.dsd_variants} == {"distribution_bin"}
    assert summary.pressure_drop_weighted_p95_Pa <= summary.pressure_drop_max_Pa
    assert summary.bed_compression_weighted_p95_fraction <= summary.max_bed_compression_fraction


def test_dsd_resolved_breakthrough_is_optional_and_weighted(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    params = load_config(repo_root / "configs" / "fast_smoke.toml")

    result = DownstreamProcessOrchestrator(output_dir=tmp_path).run(
        params=params,
        propagate_dsd=True,
        dsd_mode="adaptive",
        dsd_max_representatives=3,
        dsd_run_breakthrough=True,
    )

    summary = result.dsd_summary

    assert summary.breakthrough_simulated is True
    assert all(variant.breakthrough_simulated for variant in result.dsd_variants)
    assert summary.dbc_10_weighted_mean_mol_m3 >= 0.0
    assert summary.dbc_10_weighted_p95_mol_m3 >= summary.dbc_10_weighted_p05_mol_m3
    assert summary.max_breakthrough_mass_balance_error >= 0.0
    assert result.graph.nodes["DSD"].diagnostics["breakthrough_simulated"] is True


def test_m3_binding_calibration_reaches_fmc_and_breakthrough(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    params = load_config(repo_root / "configs" / "fast_smoke.toml")
    store = CalibrationStore()
    store.add(CalibrationEntry(
        profile_key="m3_binding",
        parameter_name="estimated_q_max",
        measured_value=80.0,
        units="mol/m3",
        confidence="high",
        source_reference="synthetic_static_capacity",
        target_module="M3",
        fit_method="static_capacity_reference_mean",
        measurement_type="static_binding_capacity",
    ))
    store.add(CalibrationEntry(
        profile_key="m3_binding",
        parameter_name="K_affinity",
        measured_value=2.0,
        units="m3/mol",
        confidence="medium",
        source_reference="synthetic_langmuir_static_point",
        target_module="M3",
        fit_method="langmuir_single_point_from_static_capacity",
        measurement_type="static_binding_isotherm",
    ))
    store.add(CalibrationEntry(
        profile_key="m3_binding",
        parameter_name="dbc_10_reference",
        measured_value=45.0,
        units="mol/m3",
        confidence="medium",
        source_reference="synthetic_dbc10",
        target_module="M3",
        fit_method="dbc_reference_mean",
        measurement_type="dynamic_binding_capacity_10pct",
    ))

    result = DownstreamProcessOrchestrator(output_dir=tmp_path).run(
        params=params,
        run_context=RunContext(calibration_store=store),
        propagate_dsd=False,
    )

    assert result.functional_media_contract.estimated_q_max == pytest.approx(80.0)
    fmc_diag = result.graph.nodes["FMC"].diagnostics
    m3_diag = result.graph.nodes["M3"].diagnostics
    assert fmc_diag["q_max_confidence"] == "calibrated"
    assert any("estimated_q_max" in item for item in fmc_diag["calibrations_applied"])
    assert m3_diag["m3_process_state"]["K_affinity"] == pytest.approx(2.0)
    assert m3_diag["dbc_10_reference_mol_m3"] == pytest.approx(45.0)
    assert "dbc_10_relative_error" in m3_diag


def test_m1_physical_qc_calibration_conditions_lifecycle_handoff(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    params = load_config(repo_root / "configs" / "fast_smoke.toml")
    store = CalibrationStore()
    store.add(CalibrationEntry(
        profile_key="m1_physical_qc",
        parameter_name="measured_pore_size_mean",
        measured_value=120e-9,
        units="m",
        confidence="high",
        source_reference="synthetic pore assay",
        target_module="M1",
        fit_method="assay_reference_mean",
        measurement_type="pore_size",
    ))
    store.add(CalibrationEntry(
        profile_key="m1_physical_qc",
        parameter_name="measured_porosity",
        measured_value=0.62,
        units="1",
        confidence="high",
        source_reference="synthetic porosity assay",
        target_module="M1",
        fit_method="assay_reference_mean",
        measurement_type="porosity",
    ))
    store.add(CalibrationEntry(
        profile_key="m1_physical_qc",
        parameter_name="measured_swelling_ratio",
        measured_value=1.8,
        units="1",
        confidence="medium",
        source_reference="synthetic swelling assay",
        target_module="M1",
        fit_method="assay_reference_mean",
        measurement_type="swelling_ratio",
    ))
    store.add(CalibrationEntry(
        profile_key="m1_physical_qc",
        parameter_name="measured_compression_modulus",
        measured_value=50000.0,
        units="Pa",
        confidence="medium",
        source_reference="synthetic compression assay",
        target_module="M3",
        fit_method="assay_reference_mean",
        measurement_type="compression_modulus",
    ))

    result = DownstreamProcessOrchestrator(output_dir=tmp_path).run(
        params=params,
        run_context=RunContext(calibration_store=store),
        propagate_dsd=False,
    )

    assert result.m1_contract.pore_size_mean == pytest.approx(120e-9)
    assert result.m1_contract.porosity == pytest.approx(0.62)
    assert result.m2_microsphere.m1_contract.porosity == pytest.approx(0.62)
    assert result.functional_media_contract.pore_size_mean == pytest.approx(120e-9)
    assert result.functional_media_contract.E_star_updated == pytest.approx(50000.0)
    m1_diag = result.graph.nodes["M1"].diagnostics
    m3_diag = result.graph.nodes["M3"].diagnostics
    assert any("pore_size_mean" in item for item in m1_diag["physical_qc_overrides"])
    assert m1_diag["measured_swelling_ratio"] == pytest.approx(1.8)
    assert m3_diag["E_star_physical_qc_value"] == pytest.approx(50000.0)
    assert "M1_PHYSICAL_QC_APPLIED" in {issue.code for issue in result.validation.issues}
    assert "M3_PHYSICAL_QC_APPLIED" in {issue.code for issue in result.validation.issues}


def test_m1_washing_residuals_and_calibration_hooks_are_explicit(p2_lifecycle_result):
    contract = p2_lifecycle_result.m1_contract

    assert 0.0 <= contract.oil_removal_efficiency <= 1.0
    assert contract.residual_oil_volume_fraction >= 0.0
    assert contract.residual_surfactant_concentration_kg_m3 >= 0.0
    assert contract.washing_model is not None
    assert contract.washing_model.wash_cycles == 3
    assert contract.washing_model.per_cycle_oil_removal > 0.0
    assert contract.washing_model.model_manifest is not None
    assert any("surfactant" in note.lower() for note in contract.washing_assumptions)
    assert "bead_size_distribution" in contract.calibration_hooks
    assert "pore_structure" in contract.calibration_hooks
    assert "swelling" in contract.calibration_hooks
    assert "mechanics" in contract.calibration_hooks
    assert "wash_residuals" in contract.calibration_hooks
