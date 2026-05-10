"""SOP / wet-lab procedure export.

W-094 / v0.8.8 — closes audit defect U-26 from the v0.8.5 phase-2
walkthrough. A bench user wants a *Generate wet-lab SOP* button that
turns the configured recipe + envelope + isotherm choice + calibration
state into a procedure document they can take to the bench.

This panel produces a Markdown-formatted SOP and offers it as a
download. Markdown is the right substrate (vs PDF) for a v0.8.8 MVP:
it renders identically inside Streamlit, copy-pastes into Word /
Confluence / Notion, and avoids the 5-minute reportlab build cost.
PDF generation can be added later via the docs/user_manual/build_pdf.py
infrastructure if users ask for it.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import streamlit as st


def _safe(value: Any, fmt: str = "{:.3g}") -> str:
    """Render a numeric or stringy value safely."""
    if value is None:
        return "—"
    if isinstance(value, (int, float)):
        try:
            return fmt.format(value)
        except (ValueError, TypeError):
            return str(value)
    return str(value)


def _build_sop_markdown() -> str:
    """Build the SOP Markdown from current session_state.

    Walks the user-configured M3 method conditions + envelope +
    isotherm spec + calibration state. Produces a wet-lab-readable
    procedure document. Tier-honest — every numeric value carries
    its tier qualification.
    """
    lines: list[str] = []
    lines.append("# Wet-lab procedure — DPSim-generated SOP")
    lines.append("")
    lines.append(
        f"**Generated:** {datetime.now(timezone.utc).isoformat()}  "
    )
    lines.append("**Source:** DPSim v0.8.8 dashboard export  ")
    lines.append(
        "**Tier framing:** SEMI_QUANTITATIVE per ADR-007; promote to "
        "CALIBRATED_LOCAL via wet-lab handshake on the calibration store.  "
    )
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── Mobile phase ─────────────────────────────────────────────────
    mp = st.session_state.get("m3_mobile_phase")
    lines.append("## 1. Mobile phase composition")
    lines.append("")
    if mp is not None:
        lines.append(
            f"| Field | Value |\n"
            f"|---|---|\n"
            f"| Temperature | {_safe(getattr(mp, 'T_C', None))} °C |\n"
            f"| NaCl | {_safe(getattr(mp, 'c_nacl_M', None))} M |\n"
            f"| Glycerol | {_safe(getattr(mp, 'phi_glycerol', None))} (vol fraction) |\n"
            f"| Ethanol | {_safe(getattr(mp, 'phi_ethanol', None))} (vol fraction) |\n"
            f"| μ override | {_safe(getattr(mp, 'custom_mu_pa_s', None))} Pa·s |\n"
        )
    else:
        lines.append(
            "_No mobile phase configured — defaults to MobilePhase() "
            "water-at-20 °C if you press Run without setting one._\n"
        )
    lines.append("")

    # ── Isotherm + binding model ────────────────────────────────────
    iso = st.session_state.get("m3_isotherm_spec")
    lines.append("## 2. Isotherm and binding model")
    lines.append("")
    if iso is not None:
        lines.append(f"**Class:** `{iso.choice.value}`  ")
        lines.append(f"**Estimated tier:** `{iso.estimated_tier.value}`  ")
        lines.append("")
        lines.append("Parameters:")
        lines.append("")
        lines.append("| Parameter | Value |")
        lines.append("|---|---|")
        for k, v in iso.params.items():
            lines.append(f"| `{k}` | {_safe(v)} |")
        lines.append("")
    else:
        lines.append(
            "_No isotherm spec configured — auto-routed isotherm via the "
            "FMC binding-model hint (typically Langmuir for AGAROSE_CHITOSAN)._\n"
        )
    lines.append("")

    # ── Column geometry ──────────────────────────────────────────────
    col_d = st.session_state.get("m3_col_d")
    bed_h = st.session_state.get("m3_bed_h")
    eps_b = st.session_state.get("m3_eps_b")
    flow_ml = st.session_state.get("m3_flow")
    lines.append("## 3. Column geometry and flow")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|---|---|")
    lines.append(f"| Column ID | {_safe(col_d)} mm |")
    lines.append(f"| Bed height | {_safe(bed_h)} cm |")
    lines.append(f"| Bed porosity | {_safe(eps_b)} |")
    lines.append(f"| Operating Q | {_safe(flow_ml)} mL/min |")
    lines.append("")

    # ── Pressure envelope ────────────────────────────────────────────
    env = st.session_state.get("m3_pressure_envelope")
    lines.append("## 4. Pre-flight pressure envelope")
    lines.append("")
    if env is not None:
        op_kpa = float(env.dP_max_operational_pa) / 1.0e3
        pred_kpa = float(env.dP_predicted_pa) / 1.0e3
        q_rec_ml = float(env.Q_recommended_m3_s) * 60.0 * 1.0e6
        lines.append(
            f"- **Operational ceiling**: {op_kpa:.1f} kPa  "
            f"(tier `{env.decision_tier.value}`)\n"
            f"- **Predicted ΔP at Q_set**: {pred_kpa:.1f} kPa  \n"
            f"- **Q_recommended (50 % headroom)**: {q_rec_ml:.2f} mL/min  \n"
            f"- **Headroom ratio (Q_set / Q_max)**: {env.headroom_ratio:.2f}  \n"
        )
        if env.is_blocker:
            lines.append("")
            lines.append(
                "> :warning: **BLOCKER:** Q_set exceeds the operational "
                "ceiling — bed compression is likely. **Do not run** "
                "until Q is reduced to ≤ Q_recommended."
            )
        elif env.is_warning:
            lines.append("")
            lines.append(
                "> :warning: **WARNING:** Q_set is in the warning band. "
                "Consider lowering Q to Q_recommended for headroom "
                "against fouling rise."
            )
    else:
        lines.append(
            "_No envelope cached yet — run the M3 lifecycle once to "
            "populate this section._\n"
        )
    lines.append("")

    # ── Calibration state ────────────────────────────────────────────
    cal_store = st.session_state.get("_cal_store")
    lines.append("## 5. Calibration state")
    lines.append("")
    if cal_store is not None and getattr(cal_store, "entries", None):
        n_entries = len(cal_store.entries)
        lines.append(
            f"**Calibration store loaded:** {n_entries} entry(ies). "
            "Outputs claiming CALIBRATED_LOCAL or above must reference "
            "an entry in this store."
        )
    else:
        lines.append(
            "_No calibration data loaded._ All outputs ship at "
            "SEMI_QUANTITATIVE per ADR-007 / ADR-010. To promote tier "
            "to CALIBRATED_LOCAL, upload wet-lab calibration data via "
            "the Calibration & Uncertainty tab."
        )
    lines.append("")

    # ── Bench procedure ─────────────────────────────────────────────
    lines.append("## 6. Bench procedure")
    lines.append("")
    lines.append(
        "1. **Pack column** to the geometry above (column ID, bed "
        "height). Verify bed porosity by injection of a non-binding "
        "tracer."
    )
    lines.append(
        "2. **Equilibrate** with the mobile phase from §1, ≥ 5 column "
        "volumes, until the UV trace baseline is stable."
    )
    lines.append(
        f"3. **Verify operating Q** = {_safe(flow_ml)} mL/min is at or "
        "below Q_recommended (§4). If above, lower Q before loading."
    )
    lines.append(
        "4. **Load** the feedstock at the operating Q. Monitor ΔP "
        "and the UV breakthrough curve. Stop when 5–10 % breakthrough "
        "is observed (or at the predicted load duration from the "
        "simulation)."
    )
    lines.append(
        "5. **Wash** with the load buffer for ≥ 5 CV until the UV "
        "trace returns to baseline."
    )
    lines.append(
        "6. **Elute** per the isotherm (§2) — pH-step for Protein A, "
        "salt-step for IEX, imidazole-step for IMAC."
    )
    lines.append(
        "7. **Strip + CIP** per resin manufacturer's protocol "
        "(typically 0.1 M NaOH for Protein A; 0.5 M NaOH for IEX/IMAC)."
    )
    lines.append(
        "8. **Re-equilibrate** before the next cycle. Track resin "
        "lifetime against the simulator's empirical first-order "
        "deactivation model."
    )
    lines.append("")

    # ── Footer ───────────────────────────────────────────────────────
    lines.append("---")
    lines.append("")
    lines.append(
        "_This SOP is a tier-aware export from a SEMI_QUANTITATIVE "
        "DPSim simulation. It is **not** a regulatory or GMP-grade "
        "document. Validate every parameter against your wet-lab "
        "calibration before bench use. All physical claims must be "
        "confirmed by the calibration store handshake._  "
    )
    lines.append("")
    lines.append(
        f"_Report generated by DPSim v{__import__('dpsim').__version__} "
        f"on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}._"
    )

    return "\n".join(lines)


def render_sop_export_panel(*, container: Optional[Any] = None) -> None:
    """Render the SOP export affordance.

    W-094 (v0.8.8). Mounted in the M3 results page after a successful
    run.
    """
    target = container if container is not None else st

    target.markdown("**:material/description: Export wet-lab SOP**")
    target.caption(
        "Download a Markdown-formatted procedure document built from "
        "your current dashboard configuration. Tier-honest: every "
        "numeric carries its decision-grade qualification per ADR-007."
    )

    md = _build_sop_markdown()
    target.download_button(
        label="Download SOP (Markdown)",
        data=md,
        file_name=(
            f"dpsim_sop_"
            f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.md"
        ),
        mime="text/markdown",
        key="sop_export_md",
    )

    with target.expander("Preview SOP"):
        target.markdown(md)


__all__ = ["render_sop_export_panel"]
