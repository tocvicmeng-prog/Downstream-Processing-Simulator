"""Run-vs-run comparison panel.

W-095 / v0.8.8 — closes audit defect U-27 from
``AUDIT_v0_8_5_e2e_phase2_user.md``: a wet-lab user iterating on
conditions cannot ask the simulator to overlay their last several
configurations. v0.8.7's `lifecycle_result` is replaced on every Run.

This panel provides a cumulative-snapshot mechanism. After each run
the user can click *Snapshot this run* to capture a small, JSON-
serialisable summary into ``st.session_state["run_history"]`` (a list
of dicts). The comparison view renders the snapshot list as a
side-by-side table with the key M3 outputs — DBC, peak ΔP, headroom,
breakthrough time, isotherm class, mobile phase composition.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import streamlit as st


_HISTORY_KEY = "run_history"
_MAX_SNAPSHOTS = 10


def _build_snapshot_for_current_run() -> Optional[dict[str, Any]]:
    """Pull a small summary from the current session_state."""
    bt = st.session_state.get("m3_result_bt")
    env = st.session_state.get("m3_pressure_envelope")
    iso = st.session_state.get("m3_isotherm_spec")
    mp = st.session_state.get("m3_mobile_phase")
    if bt is None and env is None:
        return None
    snap: dict[str, Any] = {
        "label": (
            f"run @ {datetime.now(timezone.utc).strftime('%H:%M:%S')}"
        ),
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    if bt is not None:
        snap["dbc_5pct_mol_m3"] = float(getattr(bt, "dbc_5pct", float("nan")))
        snap["dbc_10pct_mol_m3"] = float(getattr(bt, "dbc_10pct", float("nan")))
        snap["dbc_50pct_mol_m3"] = float(getattr(bt, "dbc_50pct", float("nan")))
    if env is not None:
        snap["dP_predicted_kpa"] = float(env.dP_predicted_pa) / 1.0e3
        snap["dP_max_op_kpa"] = float(env.dP_max_operational_pa) / 1.0e3
        snap["headroom_ratio"] = float(env.headroom_ratio)
        snap["Q_max_ml_min"] = float(env.Q_max_m3_s) * 60.0 * 1.0e6
        snap["polymer_family"] = (
            env.polymer_family.value
            if hasattr(env.polymer_family, "value") else str(env.polymer_family)
        )
        snap["decision_tier"] = (
            env.decision_tier.value
            if hasattr(env.decision_tier, "value") else str(env.decision_tier)
        )
    if iso is not None:
        snap["isotherm"] = (
            iso.choice.value
            if hasattr(iso.choice, "value") else str(iso.choice)
        )
    if mp is not None:
        snap["T_C"] = float(getattr(mp, "T_C", 0.0))
        snap["c_nacl_M"] = float(getattr(mp, "c_nacl_M", 0.0))
    snap["flow_ml_min"] = float(st.session_state.get("m3_flow", 0.0))
    return snap


def render_run_compare_panel(*, container: Optional[Any] = None) -> None:
    """Render the run-history snapshot + compare view.

    W-095 (v0.8.8). Mounted in M3 results page. Click *Snapshot this
    run* after each run; the comparison table accumulates.
    """
    target = container if container is not None else st

    target.markdown("**:material/compare_arrows: Run history & compare**")
    target.caption(
        "Snapshot the current run for cross-run comparison. Capacity "
        f"limit: {_MAX_SNAPSHOTS} most recent (older snapshots are "
        "rolled off)."
    )

    cols = target.columns([2, 1, 1])
    if cols[0].button(
        ":material/photo_camera: Snapshot this run",
        key="rc_snap",
        use_container_width=True,
    ):
        snap = _build_snapshot_for_current_run()
        if snap is None:
            target.warning("No run output to snapshot — run M3 first.")
        else:
            history = list(st.session_state.get(_HISTORY_KEY, []))
            history.append(snap)
            history = history[-_MAX_SNAPSHOTS:]
            st.session_state[_HISTORY_KEY] = history
            target.success(
                f"Snapshot captured ({len(history)} total)."
            )

    history = list(st.session_state.get(_HISTORY_KEY, []))
    if cols[1].button(
        "Clear history",
        key="rc_clear",
        use_container_width=True,
    ):
        st.session_state[_HISTORY_KEY] = []
        history = []

    target.caption(f"Current snapshots: {len(history)}")
    if not history:
        return

    # Render side-by-side table.
    try:
        import pandas as pd
        df = pd.DataFrame(history)
        # Re-order: label first, derived metrics last.
        col_order = (
            ["label"]
            + [c for c in df.columns if c not in ("label", "ts")]
            + ["ts"]
        )
        df = df[[c for c in col_order if c in df.columns]]
        target.dataframe(df, use_container_width=True, hide_index=True)
    except ImportError:
        target.json(history)


__all__ = ["render_run_compare_panel"]
