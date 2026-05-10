"""Structured decision claims for user-facing DPSim outputs.

The decision-grade gate determines how a numeric solver output may be shown.
``DecisionClaim`` preserves that decision as data so reports, UI panels, and
future APIs can carry the same claim semantics instead of passing around only
formatted strings.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Optional

from dpsim.core.decision_grade import (
    OutputType,
    RenderedValue,
    RenderMode,
    policy_floor,
    render_value,
)
from dpsim.datatypes import ModelEvidenceTier


_REASON_BY_MODE: dict[RenderMode, str] = {
    RenderMode.NUMBER: "Evidence tier meets the policy floor for point-value display.",
    RenderMode.INTERVAL: "Evidence tier is one step below the policy floor; show an interval.",
    RenderMode.RANK_BAND: "Evidence tier is two steps below the policy floor; show rank only.",
    RenderMode.SUPPRESS: "Evidence tier is too weak for a decision-grade displayed value.",
}


@dataclass(frozen=True)
class DecisionClaim:
    """Structured record of a displayed downstream-processing result."""

    name: str
    value: float
    unit: str
    output_type: OutputType
    evidence_tier: ModelEvidenceTier
    required_tier: ModelEvidenceTier
    render_mode: RenderMode
    valid_domain_status: str
    uncertainty_interval: Optional[tuple[float, float]]
    calibration_ref: str
    assay_required: str
    display: str
    rendered: RenderedValue
    claim_allowed: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation for dossiers, SOPs, and exports."""
        data = asdict(self)
        data["output_type"] = self.output_type.value
        data["evidence_tier"] = self.evidence_tier.value
        data["required_tier"] = self.required_tier.value
        data["render_mode"] = self.render_mode.value
        data["rendered"]["mode"] = self.rendered.mode.value
        return data


def make_decision_claim(
    value: float,
    output_type: OutputType,
    tier: ModelEvidenceTier,
    *,
    name: str = "",
    unit: str = "",
    scale: float = 1.0,
    rank_reference: Optional[float] = None,
    valid_domain_status: str = "unknown",
    uncertainty_interval: Optional[tuple[float, float]] = None,
    calibration_ref: str = "",
    assay_required: str = "",
    reason: str = "",
) -> DecisionClaim:
    """Create a structured claim from a solver value and evidence tier.

    ``scale`` is display-only, matching
    ``visualization.decision_grade_render.format_decision_graded``.
    """
    scaled = float(value) * float(scale)
    rendered = render_value(
        scaled,
        output_type,
        tier,
        unit=unit,
        rank_reference=rank_reference,
    )
    return DecisionClaim(
        name=name or output_type.value,
        value=float(value),
        unit=unit,
        output_type=output_type,
        evidence_tier=tier,
        required_tier=policy_floor(output_type),
        render_mode=rendered.mode,
        valid_domain_status=valid_domain_status,
        uncertainty_interval=uncertainty_interval,
        calibration_ref=calibration_ref,
        assay_required=assay_required,
        display=rendered.display,
        rendered=rendered,
        claim_allowed=rendered.mode != RenderMode.SUPPRESS,
        reason=reason or _REASON_BY_MODE[rendered.mode],
    )


__all__ = ["DecisionClaim", "make_decision_claim"]
