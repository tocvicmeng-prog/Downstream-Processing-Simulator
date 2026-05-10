"""Spreadsheet → CalibrationEntry import with column-mapping wizard.

W-089 / v0.8.8 — closes audit defect U-19 / S-18 from the v0.8.5
walkthrough. At v0.8.7 calibration data could only be imported via
hand-authored YAML matching `wetlab_ingestion`'s schema. Bench users
typically have Excel / CSV exports from instrument software (UV
binding curves, salt-step plate reads, etc.). This panel:

1. Accepts CSV upload.
2. Shows the column headers and lets the user map them to the
   :class:`CalibrationEntry` schema fields.
3. Builds one CalibrationEntry per data row.
4. Appends the entries into ``st.session_state['_cal_store']``.

XLSX support is gated behind a runtime import (openpyxl) — when not
installed, a clear caption tells the user to convert their Excel file
to CSV first or install the optional dependency.
"""

from __future__ import annotations

import io
from typing import Any, Optional

import streamlit as st


_SCHEMA_FIELDS: tuple[str, ...] = (
    "profile_key",
    "parameter_name",
    "measured_value",
    "units",
    "target_molecule",
    "temperature_C",
    "ph",
    "salt_concentration_M",
    "salt_type",
    "source_reference",
)
_REQUIRED_FIELDS: frozenset[str] = frozenset({
    "profile_key", "parameter_name", "measured_value", "units",
})


def _read_uploaded(uploaded: Any) -> tuple[Any, str]:
    """Decode the uploaded file into a pandas DataFrame.

    Returns (df, error_msg). df is None on error.
    """
    try:
        import pandas as pd
    except ImportError as exc:
        return None, f"pandas required for spreadsheet import: {exc}"
    name = getattr(uploaded, "name", "")
    raw = uploaded.getvalue()
    try:
        if name.lower().endswith(".csv"):
            df = pd.read_csv(io.BytesIO(raw))
        elif name.lower().endswith((".xlsx", ".xls")):
            try:
                df = pd.read_excel(io.BytesIO(raw))
            except ImportError as exc:
                return None, (
                    f"XLSX support requires openpyxl: {exc}. "
                    "Convert to CSV or `pip install openpyxl`."
                )
        else:
            return None, f"Unsupported file extension: {name!r}. CSV or XLSX expected."
    except Exception as exc:  # noqa: BLE001
        return None, f"Failed to parse {name}: {exc}"
    return df, ""


def _row_to_calibration_entry(
    row: dict[str, Any], mapping: dict[str, str],
) -> Any:
    """Convert one DataFrame row + column-mapping into a CalibrationEntry."""
    from dpsim.calibration.calibration_data import CalibrationEntry

    def _get(field: str, default: Any = "") -> Any:
        col = mapping.get(field, "")
        if not col or col == "(unset)":
            return default
        return row.get(col, default)

    return CalibrationEntry(
        profile_key=str(_get("profile_key")),
        parameter_name=str(_get("parameter_name")),
        measured_value=float(_get("measured_value", 0.0)),
        units=str(_get("units")),
        target_molecule=str(_get("target_molecule", "")),
        temperature_C=float(_get("temperature_C", 25.0)),
        ph=float(_get("ph", 7.0)),
        salt_concentration_M=float(_get("salt_concentration_M", 0.0)),
        salt_type=str(_get("salt_type", "")),
        source_reference=str(_get("source_reference", "")),
    )


def render_spreadsheet_calibration_import_panel(
    *,
    container: Optional[Any] = None,
) -> None:
    """Render the CSV/XLSX → CalibrationEntry importer.

    W-089 (v0.8.8). Mounted in the Calibration & Uncertainty tab next
    to the YAML wet-lab uploader.
    """
    target = container if container is not None else st

    target.markdown(
        ":material/upload_file: **Spreadsheet calibration import** "
        "(CSV / XLSX with column mapping)"
    )
    target.caption(
        "For bench users with Excel / CSV exports rather than YAML. "
        "Upload your file, map each column to a CalibrationEntry "
        "field, then commit the parsed entries into the calibration "
        "store. Profile_key + parameter_name + measured_value + units "
        "are required; the rest default sensibly."
    )

    uploaded = target.file_uploader(
        "Upload spreadsheet",
        type=["csv", "xlsx", "xls"],
        key="ssh_cal_upload",
    )
    if uploaded is None:
        target.info(
            "Expected columns (you'll map them in the next step): "
            "`profile_key` (e.g. `protein_a_coupling`), "
            "`parameter_name` (e.g. `q_max`, `K_L`), "
            "`measured_value`, `units`. Plus optional context columns: "
            "target_molecule, temperature_C, ph, salt_concentration_M, "
            "salt_type, source_reference."
        )
        return

    df, err = _read_uploaded(uploaded)
    if df is None:
        target.error(err)
        return

    target.success(
        f"Parsed {len(df)} rows × {len(df.columns)} columns. "
        "Map your columns below; defaults guess by header similarity."
    )
    with target.expander("Preview uploaded data"):
        target.dataframe(df.head(20), use_container_width=True)

    # Column mapping UI.
    target.markdown("**Column mapping**")
    column_options = ["(unset)"] + list(df.columns.astype(str))

    def _guess_default(field_name: str) -> str:
        """Heuristic: pick a column whose name closely matches the field."""
        for col in df.columns:
            if str(col).strip().lower() == field_name.lower():
                return str(col)
        return "(unset)"

    mapping: dict[str, str] = {}
    cols = target.columns(2)
    for i, field in enumerate(_SCHEMA_FIELDS):
        target_col = cols[i % 2]
        required_marker = " *" if field in _REQUIRED_FIELDS else ""
        default_idx = column_options.index(_guess_default(field))
        mapping[field] = target_col.selectbox(
            f"{field}{required_marker}",
            options=column_options,
            index=default_idx,
            key=f"ssh_cal_map_{field}",
            help=(
                "Required field." if field in _REQUIRED_FIELDS
                else "Optional — leave (unset) to use the schema default."
            ),
        )

    # Validate required mappings.
    missing = [
        f for f in _REQUIRED_FIELDS
        if mapping.get(f, "(unset)") == "(unset)"
    ]
    if missing:
        target.warning(
            f"Required field(s) not mapped: {', '.join(sorted(missing))}. "
            "Cannot commit until every required field is mapped."
        )
        return

    # Commit.
    if target.button(
        ":material/check: Commit to calibration store",
        key="ssh_cal_commit",
        type="primary",
    ):
        try:
            new_entries = []
            for _, row in df.iterrows():
                entry = _row_to_calibration_entry(
                    row=row.to_dict(), mapping=mapping,
                )
                new_entries.append(entry)
        except (ValueError, TypeError) as exc:
            target.error(f"Failed to convert rows: {exc}")
            return

        # Append to the calibration store; create one if absent.
        from dpsim.calibration.calibration_store import CalibrationStore
        store = st.session_state.get("_cal_store")
        if store is None:
            store = CalibrationStore(entries=[])
        existing = list(getattr(store, "entries", []))
        existing.extend(new_entries)
        store = CalibrationStore(entries=existing)
        st.session_state["_cal_store"] = store
        target.success(
            f":material/check_circle: Committed {len(new_entries)} entries "
            f"({len(existing)} total in store). Run the lifecycle to apply."
        )


__all__ = ["render_spreadsheet_calibration_import_panel"]
