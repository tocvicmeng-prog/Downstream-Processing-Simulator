from __future__ import annotations

from dpsim.visualization.run_rail.rail import _diff_group_for_path


def test_diff_group_for_path_maps_scientific_stages():
    assert _diff_group_for_path("target.bead_d50.value") == "Target"
    assert _diff_group_for_path("steps[0].stage.M1_fabrication") == "M1"
    assert _diff_group_for_path("material_batch.ligand_lot") == "M2"
    assert _diff_group_for_path("equipment.column_id") == "M3"
    assert _diff_group_for_path("calibration.profile") == "Calibration"
    assert _diff_group_for_path("owner") == "Recipe"
