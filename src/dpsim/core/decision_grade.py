"""Decision-grade gating policy for DPSim outputs (W-003 / B-1b, v0.6.4).

The DPSim solver layer always produces numeric values. Whether those numbers
are *fit for a decision* depends on the evidence tier of the model that
produced them. This module is the single source of truth for that judgement.

Render-path-only contract
-------------------------
This module makes **no changes** to any solver. It exposes a policy table
and a render-mode decision function that the lifecycle orchestrator and the
UI consult before *displaying* a value. The solver layer's outputs are
unchanged; the same number can render differently depending on which
evidence tier the underlying model carries.

The policy table maps each ``OutputType`` to a minimum required
``ModelEvidenceTier``. The decision rule is a graceful-degradation ladder:

  * tier ≥ required       → ``RenderMode.NUMBER``  (point value, full precision)
  * one step below        → ``RenderMode.INTERVAL`` (point ± policy band)
  * two steps below       → ``RenderMode.RANK_BAND`` (categorical: low/med/high)
  * three or more below   → ``RenderMode.SUPPRESS`` (do not render numerically)

Per the validation release gate (work plan §5), this module is one of the
five gates that must close before DPSim can be presented as
*"validated for downstream-processing release decisions"*. Until every
production-displayed number routes through ``decide_render_mode``, DPSim
remains a screening simulator with explicit evidence tiers.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from dpsim.datatypes import ModelEvidenceTier


# ─── Output taxonomy ─────────────────────────────────────────────────────────


class OutputType(Enum):
    """Discrete categories of DPSim output that share a decision-grade policy.

    The names mirror the user-facing names used in the M1/M2/M3 reports.
    The set is closed: adding a new output requires adding both the enum
    member and a row in ``DECISION_GRADE_POLICY``.
    """

    # M1 — fabrication
    DSD = "dsd"                          # bead size distribution (N(d) curve)
    D32 = "d32"                          # Sauter mean diameter
    PORE_SIZE = "pore_size"              # mean pore size / SEC inverse-size
    MODULUS = "modulus"                  # bulk / single-bead modulus
    RESIDUAL_OIL = "residual_oil"        # oil carryover after wash
    RESIDUAL_SURFACTANT = "residual_surfactant"  # Span-80 carryover

    # M2 — functionalization
    LIGAND_DENSITY = "ligand_density"    # mol/m^3 of immobilised ligand
    COUPLING_YIELD = "coupling_yield"    # fraction of activated sites coupled
    REAGENT_RESIDUAL = "reagent_residual"  # CNBr / CDI / tresyl / epoxide leaching

    # M3 — chromatography performance
    DBC = "dbc"                          # dynamic binding capacity (DBC10 / DBC50)
    PRESSURE_DROP = "pressure_drop"      # column ΔP at flow
    BREAKTHROUGH = "breakthrough"        # breakthrough curve trajectory
    RECOVERY = "recovery"                # elution-pool recovery fraction
    CYCLE_LIFE = "cycle_life"            # capacity loss per CIP / sanitisation cycle


class RenderMode(Enum):
    """How a numeric output should be presented to the user.

    Ordered from most to least informative; ``NUMBER`` is the strongest
    presentation (full point value), ``SUPPRESS`` is the weakest (do not
    display a number at all).
    """

    NUMBER = "number"               # e.g. "DBC = 42.3 mg/mL"
    INTERVAL = "interval"           # e.g. "DBC = 30–55 mg/mL"
    RANK_BAND = "rank_band"         # e.g. "DBC = HIGH"
    SUPPRESS = "suppress"           # e.g. "DBC = (not decision-grade)"


# ─── Policy table ────────────────────────────────────────────────────────────
#
# Per-output minimum-tier requirement for ``RenderMode.NUMBER``. Below the
# requirement, the render mode degrades along the ladder defined by
# ``decide_render_mode``.
#
# Selection rationale:
#   * DSD / D32 / PORE_SIZE / MODULUS — physical-property predictions where
#     calibration against an analogous system (CALIBRATED_LOCAL) is sufficient
#     to anchor magnitudes; SEMI_QUANTITATIVE risks order-of-magnitude error.
#   * LIGAND_DENSITY / COUPLING_YIELD / REAGENT_RESIDUAL — chemistry-specific;
#     extrapolation from analogue chemistries silently fails. Require
#     VALIDATED_QUANTITATIVE for the user-facing number.
#   * DBC / RECOVERY / CYCLE_LIFE — process-defining decisions (column sizing,
#     batch yield, resin lifetime budget). Require VALIDATED_QUANTITATIVE.
#   * PRESSURE_DROP — well-described by Ergun / Blake-Kozeny correlations;
#     SEMI_QUANTITATIVE acceptable for column-sizing decisions.
#   * BREAKTHROUGH — qualitative shape is meaningful even uncalibrated;
#     CALIBRATED_LOCAL acceptable for the curve, but DBC-from-curve still
#     gates on the stricter DBC requirement.
#
# To tighten or relax a policy, edit this table and add a regression test
# for the affected output.
DECISION_GRADE_POLICY: dict[OutputType, ModelEvidenceTier] = {
    OutputType.DSD: ModelEvidenceTier.CALIBRATED_LOCAL,
    OutputType.D32: ModelEvidenceTier.CALIBRATED_LOCAL,
    OutputType.PORE_SIZE: ModelEvidenceTier.CALIBRATED_LOCAL,
    OutputType.MODULUS: ModelEvidenceTier.CALIBRATED_LOCAL,
    OutputType.RESIDUAL_OIL: ModelEvidenceTier.CALIBRATED_LOCAL,
    OutputType.RESIDUAL_SURFACTANT: ModelEvidenceTier.CALIBRATED_LOCAL,
    OutputType.LIGAND_DENSITY: ModelEvidenceTier.VALIDATED_QUANTITATIVE,
    OutputType.COUPLING_YIELD: ModelEvidenceTier.VALIDATED_QUANTITATIVE,
    OutputType.REAGENT_RESIDUAL: ModelEvidenceTier.VALIDATED_QUANTITATIVE,
    OutputType.DBC: ModelEvidenceTier.VALIDATED_QUANTITATIVE,
    OutputType.PRESSURE_DROP: ModelEvidenceTier.SEMI_QUANTITATIVE,
    OutputType.BREAKTHROUGH: ModelEvidenceTier.CALIBRATED_LOCAL,
    OutputType.RECOVERY: ModelEvidenceTier.VALIDATED_QUANTITATIVE,
    OutputType.CYCLE_LIFE: ModelEvidenceTier.VALIDATED_QUANTITATIVE,
}


# Tier ordering — strongest first. Mirrors the order in
# ``ModelEvidenceTier`` (see datatypes.py:173). Compared by ``.value`` so
# Streamlit reload aliasing (which mints new enum classes on every rerun)
# does not silently break identity comparisons.
_TIER_ORDER: tuple[ModelEvidenceTier, ...] = (
    ModelEvidenceTier.VALIDATED_QUANTITATIVE,
    ModelEvidenceTier.CALIBRATED_LOCAL,
    ModelEvidenceTier.SEMI_QUANTITATIVE,
    ModelEvidenceTier.QUALITATIVE_TREND,
    ModelEvidenceTier.UNSUPPORTED,
)


def _tier_index(tier: ModelEvidenceTier) -> int:
    """Return 0-indexed position in the strongest-first ladder.

    Compared by ``.value`` to survive Streamlit ``importlib.reload`` aliasing
    of the dpsim.datatypes module (see CLAUDE.md, v9.0 Family-First UI).
    """
    target = str(getattr(tier, "value", tier))
    for idx, member in enumerate(_TIER_ORDER):
        if member.value == target:
            return idx
    # Unknown tier value: treat as worst (most cautious).
    return len(_TIER_ORDER) - 1


# ─── Decision API ────────────────────────────────────────────────────────────


def decide_render_mode(
    output_type: OutputType,
    tier: ModelEvidenceTier,
) -> RenderMode:
    """Return the render mode for an output at a given evidence tier.

    The ladder degrades by one step per tier below the policy floor:

      * gap == 0 → NUMBER
      * gap == 1 → INTERVAL
      * gap == 2 → RANK_BAND
      * gap >= 3 → SUPPRESS

    where ``gap = _tier_index(tier) - _tier_index(required)`` (a negative
    gap means the tier is *stronger* than required and is treated as 0).

    Args:
        output_type: which DPSim output is about to be rendered.
        tier: weakest evidence tier across the contributing models (use
            ``RunReport.compute_min_tier()`` or ``core.evidence.weakest_tier``).

    Returns:
        Render mode the UI / report layer should use. Solvers do not
        consult this function — they always emit numeric values.
    """
    if output_type not in DECISION_GRADE_POLICY:
        # Defensive default: an output without a policy entry is treated as
        # SUPPRESS to force the developer to add a row before shipping.
        return RenderMode.SUPPRESS

    required = DECISION_GRADE_POLICY[output_type]
    gap = _tier_index(tier) - _tier_index(required)
    if gap <= 0:
        return RenderMode.NUMBER
    if gap == 1:
        return RenderMode.INTERVAL
    if gap == 2:
        return RenderMode.RANK_BAND
    return RenderMode.SUPPRESS


# ─── Rendering helpers ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class RenderedValue:
    """Result of formatting a value through the decision-grade policy.

    Carries both the formatted string (``display``) and the structured
    components (``mode``, ``point``, ``low``, ``high``, ``rank``) so the
    UI layer can choose its own presentation if the default string is not
    suitable.
    """

    mode: RenderMode
    display: str
    point: Optional[float] = None
    low: Optional[float] = None
    high: Optional[float] = None
    rank: Optional[str] = None


# Default rank-band thresholds (relative to point value) used when the
# caller does not pass explicit cut-offs. ``RANK_BAND`` rendering is
# necessarily approximate; callers with domain-specific cut-offs (e.g.
# DBC > 50 mg/mL = HIGH) should pass ``rank_thresholds=`` instead.
_DEFAULT_INTERVAL_REL: float = 0.30   # ±30% interval band
_DEFAULT_RANK_THRESHOLDS: tuple[float, float] = (0.5, 1.5)  # LOW < 0.5x median, HIGH > 1.5x


def render_value(
    value: float,
    output_type: OutputType,
    tier: ModelEvidenceTier,
    *,
    unit: str = "",
    interval_rel: float = _DEFAULT_INTERVAL_REL,
    rank_reference: Optional[float] = None,
) -> RenderedValue:
    """Format a numeric value per the decision-grade policy for its output.

    ``interval_rel`` controls the ± band as a fraction of the value when
    the mode degrades to INTERVAL. ``rank_reference`` (if supplied) is the
    expected median against which RANK_BAND categorises the value as
    LOW / MEDIUM / HIGH; if omitted, RANK_BAND falls back to a single
    ``"reportable"`` rank (since meaningful ranking requires domain context).

    SUPPRESS returns a placeholder string and no numeric components.
    """
    mode = decide_render_mode(output_type, tier)
    unit_suffix = f" {unit}" if unit else ""

    if mode == RenderMode.NUMBER:
        return RenderedValue(
            mode=mode,
            display=f"{value:.4g}{unit_suffix}",
            point=float(value),
        )

    if mode == RenderMode.INTERVAL:
        low = float(value) * (1.0 - interval_rel)
        high = float(value) * (1.0 + interval_rel)
        return RenderedValue(
            mode=mode,
            display=f"{low:.3g}–{high:.3g}{unit_suffix}",
            point=float(value),
            low=low,
            high=high,
        )

    if mode == RenderMode.RANK_BAND:
        if rank_reference is not None and rank_reference > 0.0:
            ratio = float(value) / float(rank_reference)
            low_cut, high_cut = _DEFAULT_RANK_THRESHOLDS
            if ratio < low_cut:
                rank = "LOW"
            elif ratio > high_cut:
                rank = "HIGH"
            else:
                rank = "MEDIUM"
        else:
            rank = "reportable"
        return RenderedValue(
            mode=mode,
            display=f"{rank}{unit_suffix}".strip() or rank,
            rank=rank,
        )

    # SUPPRESS
    return RenderedValue(
        mode=RenderMode.SUPPRESS,
        display="(not decision-grade)",
    )


def policy_floor(output_type: OutputType) -> ModelEvidenceTier:
    """Return the minimum tier required for NUMBER rendering of an output.

    Convenience accessor. Raises ``KeyError`` for outputs without a policy
    row, which forces developers adding new outputs to register them in
    ``DECISION_GRADE_POLICY`` before shipping.
    """
    return DECISION_GRADE_POLICY[output_type]


__all__ = [
    "OutputType",
    "RenderMode",
    "RenderedValue",
    "DECISION_GRADE_POLICY",
    "decide_render_mode",
    "render_value",
    "policy_floor",
]
