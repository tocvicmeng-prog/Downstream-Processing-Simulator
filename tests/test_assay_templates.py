from pathlib import Path


def test_validation_templates_cover_required_assays():
    root = Path(__file__).resolve().parents[1] / "data" / "validation" / "templates"
    expected = {
        "l1_dsd_template.csv",
        "interfacial_tension_template.csv",
        "dispersed_phase_viscosity_template.csv",
        "pore_size_porosity_template.csv",
        "swelling_ratio_template.csv",
        "modulus_compression_template.csv",
        "ligand_density_template.csv",
        "activity_retention_template.csv",
        "residual_reagent_template.csv",
        "ligand_leaching_template.csv",
        "pressure_flow_template.csv",
        "static_binding_template.csv",
        "dbc_breakthrough_template.csv",
    }
    found = {path.name for path in root.glob("*_template.csv")}
    assert expected <= found


def test_templates_share_required_import_columns():
    root = Path(__file__).resolve().parents[1] / "data" / "validation" / "templates"
    required = {
        "assay_id",
        "sample_id",
        "target_molecule",
        "polymer_family",
        "mobile_phase",
        "pH",
        "temperature_C",
        "replicate",
        "value",
        "unit",
        "instrument",
        "operator",
    }
    for path in root.glob("*_template.csv"):
        header = path.read_text(encoding="utf-8").splitlines()[0].split(",")
        assert required <= set(header), path.name
