"""Multi-column series builder UI panel.

B-2t / W-061 — v0.8.4. Resolves audit defect C5 (Phase 1 §6).

Surfaces the v0.8.2 ADR-009 ``MultiColumnGeometry`` + series
``compute_multi_column_envelope`` machinery as a runnable UI panel.
The user adds rows in a per-column table editor (each row carries
polymer_family + ColumnGeometry fields), supplies a single mobile_phase
+ Q_set across the series, and runs. The result reports per-column
envelopes, the bottleneck column, and the series Q_max / headroom /
decision_tier rolled up per ADR-009.

Cyclic SMB dynamics is explicitly out of scope per ADR-009 — that
remains a v0.9 candidate.
"""

from __future__ import annotations

from dataclasses import replace as _dc_replace
from typing import Any, Optional

import pandas as pd
import streamlit as st

from dpsim.core.decision_grade import OutputType
from dpsim.core.mobile_phase import MobilePhase
from dpsim.datatypes import PolymerFamily
from dpsim.module3_performance.hydrodynamics import ColumnGeometry
from dpsim.module3_performance.multi_column import (
    MultiColumnGeometry,
    MultiColumnPressureEnvelope,
    compute_multi_column_envelope,
)
from dpsim.visualization.decision_grade_render import render_metric


_DEFAULT_ROWS: list[dict[str, Any]] = [
    {
        "name": "capture",
        "family": PolymerFamily.AGAROSE.value,
        "diameter_m": 0.01,
        "bed_height_m": 0.05,
        "bed_porosity": 0.38,
        "particle_porosity": 0.70,
    },
    {
        "name": "polish",
        "family": PolymerFamily.CELLULOSE.value,
        "diameter_m": 0.01,
        "bed_height_m": 0.10,
        "bed_porosity": 0.38,
        "particle_porosity": 0.70,
    },
]


def _df_to_geometry(
    df: pd.DataFrame,
) -> tuple[Optional[MultiColumnGeometry], list[str]]:
    """Convert the editor DataFrame into a MultiColumnGeometry.

    Returns (geometry_or_None, errors). Skips malformed rows; surfaces
    a one-line error per skipped row. Family resolution by ``.value``.
    """
    columns: list[ColumnGeometry] = []
    families: list[PolymerFamily] = []
    errors: list[str] = []
    family_lookup = {f.value: f for f in PolymerFamily}
    for idx, row in df.iterrows():
        try:
            fam_value = str(row["family"]).strip().lower()
            family = family_lookup.get(fam_value)
            if family is None:
                errors.append(
                    f"Row {idx}: unknown polymer_family={fam_value!r}"
                )
                continue
            col = ColumnGeometry(
                diameter=float(row["diameter_m"]),
                bed_height=float(row["bed_height_m"]),
                bed_porosity=float(row["bed_porosity"]),
                particle_porosity=float(row["particle_porosity"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"Row {idx}: malformed cell — {exc}")
            continue
        columns.append(col)
        families.append(family)
    if not columns:
        return None, errors
    return MultiColumnGeometry(
        columns=tuple(columns),
        polymer_families=tuple(families),
        name="series",
    ), errors


def render_multi_column_builder(
    *,
    container: Any = None,
    key_prefix: str = "mcg",
) -> Optional[MultiColumnPressureEnvelope]:
    """Render the multi-column series-builder UI.

    Result is cached on ``st.session_state['multi_column_envelope']``.
    """
    target = container if container is not None else st

    target.subheader("Multi-column series builder")
    target.caption(
        "Build a series of columns (capture + polish, two-stack, etc.) "
        "and inspect the rolled-up envelope: per-column ΔP / Q_max, the "
        "bottleneck column, and the series Q_max / headroom / decision "
        "tier. Cyclic SMB physics is a v0.9 candidate per ADR-009."
    )

    seed_rows = st.session_state.get(f"{key_prefix}_rows", _DEFAULT_ROWS)
    seed_df = pd.DataFrame(seed_rows)
    family_options = sorted(f.value for f in PolymerFamily)
    edited_df = target.data_editor(
        seed_df,
        num_rows="dynamic",
        column_config={
            "name": st.column_config.TextColumn(
                "Column name", help="Free-form label e.g. capture / polish.",
            ),
            "family": st.column_config.SelectboxColumn(
                "Polymer family", options=family_options,
                help="Family used for K_geom lookup (ADR-004).",
            ),
            "diameter_m": st.column_config.NumberColumn(
                "Diameter (m)", min_value=0.001, max_value=0.5,
                format="%.4f",
            ),
            "bed_height_m": st.column_config.NumberColumn(
                "Bed height (m)", min_value=0.005, max_value=2.0,
                format="%.3f",
            ),
            "bed_porosity": st.column_config.NumberColumn(
                "Bed porosity ε_b", min_value=0.05, max_value=0.95,
                format="%.2f",
            ),
            "particle_porosity": st.column_config.NumberColumn(
                "Particle porosity ε_p", min_value=0.05, max_value=0.95,
                format="%.2f",
            ),
        },
        key=f"{key_prefix}_editor",
        use_container_width=True,
    )
    st.session_state[f"{key_prefix}_rows"] = edited_df.to_dict(orient="records")

    cols = target.columns(2)
    Q_set_mL_min = cols[0].number_input(
        "Series Q (mL/min)",
        min_value=0.001, max_value=10000.0,
        value=1.0, step=0.1, format="%.3f",
        key=f"{key_prefix}_Q",
        help="The series flow rate is constant through every column.",
    )
    Q_set_m3_s = float(Q_set_mL_min) / 60.0e6
    series_name = cols[1].text_input(
        "Series name",
        value="capture+polish",
        key=f"{key_prefix}_name",
    )

    mobile_phase = (
        st.session_state.get("mobile_phase") or MobilePhase()
    )

    run = target.button(
        "Run series envelope",
        key=f"{key_prefix}_run",
        type="primary",
    )

    cached = st.session_state.get("multi_column_envelope")
    if not run and cached is None:
        return None

    if run:
        geometry, parse_errors = _df_to_geometry(edited_df)
        if parse_errors:
            with target.expander("Parse errors"):
                for e in parse_errors:
                    target.warning(e)
        if geometry is None:
            target.error(
                "No valid columns parsed. Add at least one row with a "
                "known polymer_family + valid geometry."
            )
            return None
        geometry = _dc_replace(geometry, name=series_name)
        try:
            cached = compute_multi_column_envelope(
                geometry=geometry,
                mobile_phase=mobile_phase,
                Q_set_m3_s=Q_set_m3_s,
            )
        except (ValueError, KeyError) as exc:
            target.error(f"Series envelope failed: {exc}")
            return None
        st.session_state["multi_column_envelope"] = cached

    if cached is None:
        return None
    env: MultiColumnPressureEnvelope = cached

    target.markdown(f"**Series:** `{env.name}` ({env.n_columns} columns)")
    cols_s = target.columns(3)
    render_metric(
        "Series Q_max",
        value=env.series_Q_max_m3_s,
        output_type=OutputType.Q_MAX,
        tier=env.decision_tier,
        unit="mL/min",
        scale=1.0e6 * 60.0,
        container=cols_s[0],
        help="min_i Q_max_i — the bottleneck column sets the ceiling.",
    )
    render_metric(
        "Series Q_recommended",
        value=env.series_Q_recommended_m3_s,
        output_type=OutputType.Q_MAX,
        tier=env.decision_tier,
        unit="mL/min",
        scale=1.0e6 * 60.0,
        container=cols_s[1],
        help="50% of series Q_max (fouling-headroom buffer).",
    )
    render_metric(
        "Series headroom",
        value=min(env.series_headroom_ratio, 9.99),
        output_type=OutputType.PRESSURE_HEADROOM,
        tier=env.decision_tier,
        unit="%",
        scale=100.0,
        container=cols_s[2],
        help="max_i headroom_i — worst column drives the verdict.",
    )

    if env.is_blocker:
        target.error(
            f"BLOCKER — series headroom = {env.series_headroom_ratio:.2f}. "
            "At least one column would exceed its operational ceiling."
        )
    elif env.is_warning:
        target.warning(
            f"WARNING — series headroom = {env.series_headroom_ratio:.2f}. "
            "Approaching the bottleneck column's ceiling."
        )
    else:
        target.success(
            f"OK — operating at {env.series_headroom_ratio*100:.0f}% of "
            "the bottleneck column's Q_max."
        )

    per_column = env.per_column  # tuple[PressureEnvelope, ...]
    q_max_values = [pc.Q_max_m3_s for pc in per_column]
    bottleneck_idx = q_max_values.index(min(q_max_values))
    target.markdown("**Per-column envelopes**")
    rows: list[dict[str, Any]] = []
    for i, pc in enumerate(per_column):
        marker = " ◀ bottleneck" if i == bottleneck_idx else ""
        rows.append({
            "Column": f"col[{i}]{marker}",
            "ΔP_predicted (kPa)": float(pc.dP_predicted_pa) / 1.0e3,
            "ΔP_max_op (kPa)": float(pc.dP_max_operational_pa) / 1.0e3,
            "Q_max (mL/min)": float(pc.Q_max_m3_s) * 1.0e6 * 60.0,
            "Headroom": float(pc.headroom_ratio),
            "Tier": pc.decision_tier.value,
        })
    target.dataframe(
        pd.DataFrame(rows), use_container_width=True, hide_index=True,
    )
    target.caption(
        f"Total ΔP_predicted = {env.total_dP_predicted_pa / 1.0e3:.2f} kPa. "
        f"Decision tier (weakest across columns) = "
        f"`{env.decision_tier.value}`."
    )

    if env.valid_domain_violations:
        with target.expander(
            f"valid_domain violations ({len(env.valid_domain_violations)})"
        ):
            for v in env.valid_domain_violations:
                target.write(f"• {v}")

    return env


__all__ = ["render_multi_column_builder"]
