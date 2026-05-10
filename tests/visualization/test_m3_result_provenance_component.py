from __future__ import annotations


def test_m3_result_provenance_component_exports_helpers():
    from dpsim.visualization.tabs.m3.result_provenance import (
        render_m3_result_provenance,
        store_direct_m3_provenance,
    )

    assert callable(render_m3_result_provenance)
    assert callable(store_direct_m3_provenance)
