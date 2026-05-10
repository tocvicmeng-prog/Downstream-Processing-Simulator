"""Top-of-page SEMI_QUANTITATIVE banner.

B-1r / W-058 — v0.8.4. Resolves audit defect W-1 (Phase 1 §6).

Persistent banner rendered as the first child of every stage. Surfaces
the weakest evidence tier across the lifecycle result + whether
calibration data is loaded into the calibration store. Three visual
states reuse the existing semantic palette (no new colours per
DESIGN.md).

The README guardrail — "do not describe DPSim outputs as 'validated'
unless the calibration store carries the wet-lab data that justifies
the claim" — is the canonical project framing. The banner enforces
visibility of that framing at the top of every screen.
"""

from __future__ import annotations

from typing import Any, Optional

import streamlit as st

from dpsim.datatypes import ModelEvidenceTier


_TIER_LABEL: dict[str, str] = {
    ModelEvidenceTier.VALIDATED_QUANTITATIVE.value: "VALIDATED_QUANTITATIVE",
    ModelEvidenceTier.CALIBRATED_LOCAL.value: "CALIBRATED_LOCAL",
    ModelEvidenceTier.SEMI_QUANTITATIVE.value: "SEMI_QUANTITATIVE",
    ModelEvidenceTier.QUALITATIVE_TREND.value: "QUALITATIVE_TREND",
    ModelEvidenceTier.UNSUPPORTED.value: "UNSUPPORTED",
}


def render_tier_banner(
    *,
    container: Any = None,
    weakest_tier: Optional[ModelEvidenceTier] = None,
    has_calibration: bool = False,
) -> None:
    """Render the persistent tier-state banner.

    Three visual states (compared by tier ``.value`` per the AST gate):

    * **GREEN — calibrated**: when ``has_calibration is True`` AND the
      weakest tier is at or above CALIBRATED_LOCAL. Outputs render with
      the calibration handshake honoured.
    * **AMBER — semi-quantitative**: the default state. Outputs render
      as INTERVAL bands; calibration store is empty or has not yet
      promoted any output to CALIBRATED_LOCAL.
    * **RED — qualitative or unsupported**: a critical input is
      qualitative-trend or unsupported. Outputs render as RANK_BAND or
      SUPPRESS.

    The banner text always quotes the README guardrail.
    """
    target = container if container is not None else st

    if weakest_tier is None:
        # No lifecycle result yet — show the default-state banner.
        target.info(
            "**Evidence tier: SEMI_QUANTITATIVE INTERVAL (default).** "
            "DPSim outputs render as bands until calibration data is "
            "loaded. Do **not** describe results as \"validated\" without "
            "wet-lab handshake."
        )
        return

    tier_value = weakest_tier.value
    tier_label = _TIER_LABEL.get(tier_value, tier_value)
    strong_tiers = {
        ModelEvidenceTier.VALIDATED_QUANTITATIVE.value,
        ModelEvidenceTier.CALIBRATED_LOCAL.value,
    }
    weak_tiers = {
        ModelEvidenceTier.QUALITATIVE_TREND.value,
        ModelEvidenceTier.UNSUPPORTED.value,
    }

    if tier_value in strong_tiers and has_calibration:
        target.success(
            f"**Evidence tier: {tier_label} (with calibration loaded).** "
            "Outputs honour the calibration store. Validation domain "
            "limits still apply — see the validation report on each "
            "result panel."
        )
    elif tier_value in weak_tiers:
        target.error(
            f"**Evidence tier: {tier_label}.** A critical input is "
            "qualitative-trend or unsupported. Outputs render as "
            "rank-bands or are suppressed entirely. Treat results as "
            "screening inputs, not as design numbers."
        )
    else:
        # SEMI_QUANTITATIVE, or strong tier without calibration.
        if tier_value in strong_tiers:
            target.warning(
                f"**Evidence tier: {tier_label} (calibration not loaded).** "
                "Outputs render as bands until calibration data is "
                "ingested. Do **not** describe results as \"validated\" "
                "without wet-lab handshake."
            )
        else:
            target.info(
                f"**Evidence tier: {tier_label} INTERVAL.** "
                "Outputs render as bands; quantitative magnitudes "
                "approximate. Do **not** describe results as "
                "\"validated\" without wet-lab handshake."
            )


__all__ = ["render_tier_banner"]
