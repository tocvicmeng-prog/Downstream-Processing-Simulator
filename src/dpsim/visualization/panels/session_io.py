"""Save/load session — JSON snapshot of the user's dashboard inputs.

W-093 / v0.8.8 — closes audit defect U-25 from
``AUDIT_v0_8_5_e2e_phase2_user.md``: a bench user returning to the
dashboard the next day cannot pick up where they left off because
Streamlit's session_state is not persisted across reloads.

This panel exports the session_state's user-input keys to a JSON file
and re-imports them on demand. Only the *user-input* keys are
snapshotted — not the runtime artefacts (lifecycle_result,
forward_mc_bands, etc.) which are regenerable from inputs by re-running.

Caveats:
  * Streamlit widget keys persist their values via session_state, so
    re-loading a snapshot before any widget renders sets the widget's
    initial value.
  * Complex objects (dataclasses, numpy arrays) are not snapshotted;
    they would re-instantiate as plain dicts. The snapshot is
    intentionally conservative — it covers scalar inputs, not derived
    state.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import streamlit as st


# Keys that ARE snapshotted: anything starting with these prefixes.
# Conservative whitelist — easy to extend as new widgets land.
_SNAPSHOTTED_PREFIXES: tuple[str, ...] = (
    "m1_",      # M1 fabrication inputs
    "m2_",      # M2 functionalisation inputs (excluding m2_result which is derived)
    "m3_",      # M3 column-method inputs (excluding m3_result_* which is derived)
    "fmc_",     # Forward MC inputs
    "inv_",     # Inverse inference inputs
    "opt_",     # Optimization inputs
    "p6_",      # Lifecycle run controls
    "pi_",      # Pressure indicator user actions
)

# Keys explicitly excluded — runtime artefacts, not inputs.
_DERIVED_KEYS: frozenset[str] = frozenset({
    "m2_result",
    "m3_result_bt",
    "m3_result_ge",
    "m3_result_method",
    "m3_result_cat",
    "m3_result_val",
    "m3_pressure_envelope",
    "m3_latest_dp_pa",
    "m3_latest_state",
    "lifecycle_result",
    "forward_mc_bands",
    "forward_mc_step_program_result",
    "posterior_envelope",
    "posterior_log_cov",
    "multi_column_envelope",
    "opt_state",
})


def _is_snapshottable(key: str, value: Any) -> bool:
    """True iff this session_state entry should land in the snapshot.

    The whitelist + blacklist + JSON-serialisability guard rails out
    runtime artefacts and unsalvageable Python objects.
    """
    if not isinstance(key, str):
        return False
    if key in _DERIVED_KEYS:
        return False
    if not key.startswith(_SNAPSHOTTED_PREFIXES):
        return False
    try:
        json.dumps(value)  # serialisability probe
    except (TypeError, ValueError):
        return False
    return True


def _build_snapshot() -> dict[str, Any]:
    """Iterate session_state and emit the snapshot dict."""
    snapshot: dict[str, Any] = {}
    for key in list(st.session_state.keys()):
        value = st.session_state.get(key)
        if _is_snapshottable(str(key), value):
            snapshot[str(key)] = value
    return snapshot


def _apply_snapshot(snapshot: dict[str, Any]) -> int:
    """Write the snapshot back into session_state. Returns number applied."""
    n = 0
    for key, value in snapshot.items():
        if not _is_snapshottable(str(key), value):
            continue
        st.session_state[str(key)] = value
        n += 1
    return n


def render_session_io_panel(*, container: Any = None) -> None:
    """Render the save/load session affordance.

    W-093 (v0.8.8). Place in the sidebar so the user can save a
    snapshot at any moment and restore it on the next visit.
    """
    target = container if container is not None else st.sidebar

    target.divider()
    target.markdown("**:material/save: Sessions**")
    target.caption(
        "Snapshot user inputs (recipes, geometry, mobile phase, "
        "isotherm spec, etc.) to JSON for resume / sharing. Runtime "
        "artefacts re-run from inputs."
    )

    snapshot = _build_snapshot()
    snapshot_json = json.dumps(
        {
            "schema_version": 1,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "session_state": snapshot,
        },
        indent=2,
        sort_keys=True,
    )
    target.download_button(
        label=f"Save session ({len(snapshot)} keys)",
        data=snapshot_json,
        file_name=(
            f"dpsim_session_"
            f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
        ),
        mime="application/json",
        key="sess_io_save",
    )

    uploaded = target.file_uploader(
        "Restore session (JSON)",
        type=["json"],
        key="sess_io_load",
    )
    if uploaded is not None:
        try:
            payload = json.loads(uploaded.getvalue().decode("utf-8"))
            session = payload.get("session_state", {})
            n_applied = _apply_snapshot(session)
            target.success(
                f"Restored {n_applied} keys. Refresh the page to see "
                "the values populated in widgets."
            )
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError) as exc:
            target.error(f"Could not restore session: {exc}")


__all__ = ["render_session_io_panel"]
