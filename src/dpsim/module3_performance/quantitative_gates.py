"""M3 quantitative-output gating policy (B-2e / W-004, v0.6.5).

Reference: docs/update_workplan_2026-05-04.md §4 → B-2e.

Policy module. Decides what evidence tier an M3 chromatography output
should carry based on which calibration ingredients are present:

  * ``q_max`` (capacity)            — required for any DBC/recovery prediction
  * ``kinetic_constants``           — required for breakthrough shape
  * ``pressure_flow``               — required for column ΔP / packing-pressure call
  * ``cycle_life``                  — required for capacity-loss-per-cycle prediction

Promotion ladder (consumed by ``assign_m3_evidence_tier``):

  * 4/4 calibrated  → VALIDATED_QUANTITATIVE
  * 3/4 calibrated  → CALIBRATED_LOCAL
  * 1–2 calibrated  → SEMI_QUANTITATIVE
  * 0/4 calibrated  → QUALITATIVE_TREND

The render-path layer (``core.decision_grade``) then independently maps
the resulting evidence tier to a NUMBER / INTERVAL / RANK_BAND / SUPPRESS
mode per the policy table — so the M3 orchestrator's job ends at
publishing the tier; the UI does not need to know the gate semantics.

Companion: ``GradientContext`` carries pH and salt gradient parameters
through to the isotherm / transport adapter as a structured object
rather than as ad-hoc manifest text. The current isotherm / transport
adapters do not yet consume it; the adapter refactor is a follow-on
incremental change. This module gives the rest of the codebase the
concrete handle it needs to start passing context.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional

from dpsim.datatypes import ModelEvidenceTier, ModelManifest


# ─── Calibration-coverage assessment ─────────────────────────────────────────


@dataclass(frozen=True)
class M3CalibrationCoverage:
    """Which of the four M3 calibration ingredients are available.

    Each flag is either True (calibrated for this target/system) or False.
    The tier-promotion function counts the True flags and consults the
    policy ladder; partial coverage demotes the tier rather than blocking
    the output (the render-path layer handles the user-facing message).
    """

    q_max_calibrated: bool = False
    kinetic_constants_calibrated: bool = False
    pressure_flow_calibrated: bool = False
    cycle_life_calibrated: bool = False
    notes: str = ""

    @property
    def n_calibrated(self) -> int:
        return sum([
            self.q_max_calibrated,
            self.kinetic_constants_calibrated,
            self.pressure_flow_calibrated,
            self.cycle_life_calibrated,
        ])


def assess_m3_calibration_coverage(
    calibration_entries: list,
    *,
    profile_key: str = "",
    target_molecule: str = "",
) -> M3CalibrationCoverage:
    """Inspect a calibration-entry list and report coverage of the four
    M3 quantitative ingredients.

    A calibration entry counts toward an ingredient when its
    ``parameter_name`` matches the ingredient's keyword set AND
    (if supplied) its ``profile_key`` and ``target_molecule`` match.

    Keyword sets are deliberately permissive — different research groups
    name the same parameter differently (e.g. "q_max" vs "Qmax" vs
    "static_capacity"). The keyword sets cover the canonical DPSim
    spellings; extend them as wet-lab data is ingested with new naming.

    Args:
        calibration_entries: list of dicts (typically
            ``CalibrationEntry.to_dict()``) OR list of CalibrationEntry
            instances. Both shapes accepted.
        profile_key: optional filter — only entries whose
            ``profile_key`` matches contribute.
        target_molecule: optional filter — only entries whose
            ``target_molecule`` matches contribute.
    """
    Q_MAX_KEYS = {"q_max", "qmax", "static_capacity", "binding_capacity"}
    KINETIC_KEYS = {"k_l", "k_kin", "k_ads", "k_film", "k_pore", "k_kinetic"}
    PRESSURE_FLOW_KEYS = {"k_perm", "permeability", "pressure_flow",
                          "delta_p_per_velocity", "ergun_constant"}
    CYCLE_LIFE_KEYS = {"cycle_life", "capacity_loss_per_cycle",
                       "ligand_leaching_per_cycle"}

    def _entry_field(entry, name: str) -> str:
        if hasattr(entry, name):
            return str(getattr(entry, name) or "")
        if isinstance(entry, dict):
            return str(entry.get(name, "") or "")
        return ""

    def _matches_filters(entry) -> bool:
        if profile_key and _entry_field(entry, "profile_key") != profile_key:
            return False
        if target_molecule and _entry_field(entry, "target_molecule") != target_molecule:
            return False
        return True

    seen_q_max = False
    seen_kinetic = False
    seen_pressure = False
    seen_cycle = False

    for entry in calibration_entries:
        if not _matches_filters(entry):
            continue
        param = _entry_field(entry, "parameter_name").lower()
        if param in Q_MAX_KEYS:
            seen_q_max = True
        if param in KINETIC_KEYS:
            seen_kinetic = True
        if param in PRESSURE_FLOW_KEYS:
            seen_pressure = True
        if param in CYCLE_LIFE_KEYS:
            seen_cycle = True

    return M3CalibrationCoverage(
        q_max_calibrated=seen_q_max,
        kinetic_constants_calibrated=seen_kinetic,
        pressure_flow_calibrated=seen_pressure,
        cycle_life_calibrated=seen_cycle,
    )


# ─── Tier-promotion ladder ──────────────────────────────────────────────────


def assign_m3_evidence_tier(coverage: M3CalibrationCoverage) -> ModelEvidenceTier:
    """Map calibration coverage to an M3 evidence tier.

    Locked policy (work plan §4 → B-2e):

      * 4/4 calibrated  → VALIDATED_QUANTITATIVE
      * 3/4 calibrated  → CALIBRATED_LOCAL
      * 1–2 calibrated  → SEMI_QUANTITATIVE
      * 0/4 calibrated  → QUALITATIVE_TREND

    The output is consumed by ``core.decision_grade.decide_render_mode``
    (B-1b) which performs the final policy decision about whether the
    user-facing display is a NUMBER / INTERVAL / RANK_BAND / SUPPRESS.
    """
    n = coverage.n_calibrated
    if n >= 4:
        return ModelEvidenceTier.VALIDATED_QUANTITATIVE
    if n == 3:
        return ModelEvidenceTier.CALIBRATED_LOCAL
    if n >= 1:
        return ModelEvidenceTier.SEMI_QUANTITATIVE
    return ModelEvidenceTier.QUALITATIVE_TREND


# ─── Gradient context ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class GradientContext:
    """Structured pH / salt gradient parameters for the isotherm/transport adapter.

    Currently the M3 orchestrator passes gradient parameters as recipe
    text strings ("gradient_field"="ph", "gradient_start_pH", ...) and
    the isotherm/transport adapter parses them at runtime. That coupling
    works for the existing simple gradient cases but blocks future
    work like:
      * multi-step gradients
      * salt + pH composite gradients
      * gradient with non-monotonic shape

    GradientContext gives the adapter a typed handle. The B-2e scope adds
    the dataclass and a translation helper from recipe parameters; the
    adapter-side consumption is a follow-on PR.

    Fields:
        gradient_field: "ph" | "salt_concentration" | "imidazole" | ""
        start_value, end_value: gradient bounds in the natural unit
            (pH for "ph"; mol/m^3 for "salt_concentration" / "imidazole").
        duration_s: gradient ramp time.
        shape: "linear" | "step" | "exponential" — only "linear" is
            consumed by the current adapter; others are reserved.
    """

    gradient_field: str = ""
    start_value: float = 0.0
    end_value: float = 0.0
    duration_s: float = 0.0
    shape: str = "linear"

    @property
    def is_active(self) -> bool:
        """True iff this context describes a real gradient (vs no-op)."""
        return bool(self.gradient_field) and self.duration_s > 0.0


def gradient_context_from_recipe_params(params: dict) -> Optional[GradientContext]:
    """Parse the recipe-level gradient parameter dict into a GradientContext.

    Returns None when no gradient is declared. Accepts either bare floats
    or values that expose a ``.value`` attribute (e.g. Quantity instances)
    for the numeric fields.
    """
    field_name = str(params.get("gradient_field", "") or "").strip()
    if not field_name:
        return None

    def _coerce(x) -> float:
        if x is None:
            return 0.0
        if hasattr(x, "value"):
            return float(x.value)
        return float(x)

    if field_name == "ph":
        start = _coerce(params.get("gradient_start_pH", params.get("gradient_start_value")))
        end = _coerce(params.get("gradient_end_pH", params.get("gradient_end_value")))
    else:
        start = _coerce(params.get("gradient_start_value"))
        end = _coerce(params.get("gradient_end_value"))

    duration = _coerce(params.get("duration", params.get("gradient_duration_s", 0.0)))
    shape = str(params.get("gradient_shape", "linear") or "linear")

    return GradientContext(
        gradient_field=field_name,
        start_value=start,
        end_value=end,
        duration_s=duration,
        shape=shape,
    )


# ─── Manifest gating (orchestrator hook) ────────────────────────────────────


# Tier ordering — strongest first. Mirrors core.decision_grade._TIER_ORDER and
# is duplicated here to avoid the cross-module dependency (decision_grade is a
# UI-side render-path module; gating is an M3-side policy module).
_TIER_ORDER: tuple[ModelEvidenceTier, ...] = (
    ModelEvidenceTier.VALIDATED_QUANTITATIVE,
    ModelEvidenceTier.CALIBRATED_LOCAL,
    ModelEvidenceTier.SEMI_QUANTITATIVE,
    ModelEvidenceTier.QUALITATIVE_TREND,
    ModelEvidenceTier.UNSUPPORTED,
)


def _tier_index(tier: ModelEvidenceTier) -> int:
    target = str(getattr(tier, "value", tier))
    for idx, member in enumerate(_TIER_ORDER):
        if member.value == target:
            return idx
    return len(_TIER_ORDER) - 1  # unknown → worst


def apply_m3_gate_to_manifest(
    manifest: ModelManifest,
    calibration_entries: list,
    *,
    profile_key: str = "",
    target_molecule: str = "",
) -> ModelManifest:
    """Demote a manifest's evidence tier to the M3 gating ceiling.

    The gate-derived tier is the WORST of (existing tier, gating tier) —
    gating can only demote, never promote. This keeps existing manifest
    logic (mode guards, family caps, etc.) authoritative when it is
    already stricter than the calibration-coverage gate.

    Args:
        manifest: input manifest from the M3 orchestrator.
        calibration_entries: iterable of CalibrationEntry instances OR
            dicts with the same field shape.
        profile_key: optional filter (see ``assess_m3_calibration_coverage``).
        target_molecule: optional filter.

    Returns:
        A new ModelManifest with the demoted evidence tier and updated
        diagnostics (the input manifest is not mutated; ``dataclasses.replace``
        is used).
    """
    coverage = assess_m3_calibration_coverage(
        calibration_entries,
        profile_key=profile_key,
        target_molecule=target_molecule,
    )
    gated_tier = assign_m3_evidence_tier(coverage)
    existing_idx = _tier_index(manifest.evidence_tier)
    gated_idx = _tier_index(gated_tier)
    # Higher index == weaker tier. Take the WORSE (max) of the two.
    final_idx = max(existing_idx, gated_idx)
    final_tier = _TIER_ORDER[final_idx]
    new_diag = dict(manifest.diagnostics or {})
    new_diag["m3_gate_coverage_n"] = coverage.n_calibrated
    new_diag["m3_gate_q_max"] = coverage.q_max_calibrated
    new_diag["m3_gate_kinetic"] = coverage.kinetic_constants_calibrated
    new_diag["m3_gate_pressure_flow"] = coverage.pressure_flow_calibrated
    new_diag["m3_gate_cycle_life"] = coverage.cycle_life_calibrated
    new_diag["m3_gate_tier_only"] = gated_tier.value
    return replace(manifest, evidence_tier=final_tier, diagnostics=new_diag)


__all__ = [
    "GradientContext",
    "M3CalibrationCoverage",
    "apply_m3_gate_to_manifest",
    "assess_m3_calibration_coverage",
    "assign_m3_evidence_tier",
    "gradient_context_from_recipe_params",
]
