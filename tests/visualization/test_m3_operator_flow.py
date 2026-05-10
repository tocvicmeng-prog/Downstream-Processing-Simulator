from __future__ import annotations

from types import SimpleNamespace

from dpsim.visualization.tabs.m3.operator_flow import m3_operator_flow_rows


def test_m3_operator_flow_blocks_run_until_m2_exists():
    rows = m3_operator_flow_rows({})
    by_step = {row["step"]: row for row in rows}

    assert by_step["3. Run"]["state"] == "blocked"
    assert by_step["4. Decision"]["state"] == "pending"


def test_m3_operator_flow_reports_pressure_blocker_and_results():
    rows = m3_operator_flow_rows(
        {
            "m2_result": object(),
            "m3_result_bt": object(),
            "m3_pressure_envelope": SimpleNamespace(
                is_blocker=True,
                is_warning=False,
            ),
        }
    )
    by_step = {row["step"]: row for row in rows}

    assert by_step["2. Feasibility"]["state"] == "blocked"
    assert by_step["3. Run"]["state"] == "ready"
    assert by_step["4. Decision"]["state"] == "ready"
    assert by_step["6. SOP/export"]["state"] == "ready"
