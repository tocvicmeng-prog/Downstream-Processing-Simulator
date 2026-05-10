from __future__ import annotations

from dpsim.visualization.components.operator_flow import operator_flow_html
from dpsim.visualization.tabs.m1.operator_flow import m1_operator_flow_rows
from dpsim.visualization.tabs.m2.operator_flow import m2_operator_flow_rows


def test_m1_operator_flow_handoff_pending_until_result_exists():
    rows = {row["step"]: row for row in m1_operator_flow_rows({})}

    assert rows["4. Run"]["state"] == "ready"
    assert rows["6. Handoff"]["state"] == "pending"


def test_m1_operator_flow_handoff_ready_after_result():
    rows = {row["step"]: row for row in m1_operator_flow_rows({"result": object()})}

    assert rows["5. Release"]["state"] == "ready"
    assert rows["6. Handoff"]["state"] == "ready"


def test_m2_operator_flow_blocks_without_m1_and_hands_off_after_m2():
    no_m1 = {row["step"]: row for row in m2_operator_flow_rows({})}
    complete = {
        row["step"]: row
        for row in m2_operator_flow_rows({"result": object(), "m2_result": object()})
    }

    assert no_m1["1. M1 handoff"]["state"] == "blocked"
    assert no_m1["4. Run"]["state"] == "blocked"
    assert complete["5. Evidence"]["state"] == "ready"
    assert complete["6. M3 handoff"]["state"] == "ready"


def test_shared_operator_flow_html_escapes_labels():
    html = operator_flow_html(
        [{"step": "<setup>", "state": "ready", "detail": "safe & reviewed"}],
        css_class="dps-stage-flow",
    )

    assert '<div class="dps-stage-flow">' in html
    assert "&lt;setup&gt;" in html
    assert "safe &amp; reviewed" in html
