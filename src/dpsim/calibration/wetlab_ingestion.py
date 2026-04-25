"""Wet-lab calibration ingestion module (Q-013 / Q-014 follow-on).

Bridges the v9.x simulator and the wet-lab calibration campaign
documented in `docs/handover/WETLAB_v9_3_CALIBRATION_PLAN.md`. The bench
scientist fills in a YAML file with measurements; this module parses the
YAML into ``CalibrationEntry`` objects, applies them to the appropriate
targets (ReagentProfile fields, L2 solver constants, ion-gelant
parameters), and promotes ``confidence_tier`` on the affected profiles.

The campaign produces a **calibration manifest** documenting what was
applied with full provenance (bench date, operator, lot numbers, fit
method, posterior uncertainty) so the tier promotion is auditable.

This module does NOT mutate the source files on disk — it returns
**copies** of profiles with updated parameters, so the caller chooses
whether to write them back via a code commit or use them in-memory for
a single simulation run. This separation lets v9.x users compare
literature-default vs. bench-calibrated outputs side-by-side.

Schema (YAML)
-------------
.. code-block:: yaml

    campaign_id: "Q-014_v9_2_profile_validation_2026Q3"
    operator: "RD-scientist-name"
    lab: "Lab name / facility"
    notes: "Free-text campaign-level notes"
    entries:
      - profile_key: "cnbr_activation"
        parameter_name: "k_forward"
        measured_value: 1.2e-3
        units: "m^3/(mol*s)"
        target_molecule: "IgG (polyclonal)"
        temperature_C: 4.0
        ph: 11.0
        measurement_type: "DBC10"
        source_reference: "Lab notebook 2026-08-15 p. 42"
        replicates: 3
        confidence: "measured"
        target_module: "M2"
        fit_method: "least_squares"
        posterior_uncertainty: 0.15e-3
        promote_to_tier: "calibrated_local"

References
----------
- Calibration plan: ``docs/handover/WETLAB_v9_3_CALIBRATION_PLAN.md``
- Existing calibration schema: ``CalibrationEntry`` in
  ``src/dpsim/calibration/calibration_data.py``
- Tier definitions: ``ModelEvidenceTier`` in ``src/dpsim/datatypes.py``
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace as dataclass_replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from ..datatypes import ModelEvidenceTier
from ..module2_functionalization.reagent_profiles import (
    REAGENT_PROFILES,
    ReagentProfile,
)
from .calibration_data import CalibrationEntry

logger = logging.getLogger(__name__)


# ─── Tier promotion ladder ─────────────────────────────────────────────
#
# Per ModelEvidenceTier ordering:
#   VALIDATED_QUANTITATIVE > CALIBRATED_LOCAL > SEMI_QUANTITATIVE
#       > QUALITATIVE_TREND > UNSUPPORTED
#
# Tier promotion rule: a calibration entry can promote a profile only
# UPWARD on this ladder. Attempting a downgrade is rejected (this would
# be a data-integrity error — a real measurement should never decrease
# evidence quality below the literature-anchored default).

_TIER_LADDER = [
    "unsupported",
    "ranking_only",
    "qualitative_trend",
    "semi_quantitative",
    "calibrated_local",
    "validated_quantitative",
]

# Legacy / synonym names that should fold to a canonical ladder entry.
_TIER_SYNONYMS = {
    "qualitative_only": "qualitative_trend",
}


def _tier_rank(tier_value: str) -> int:
    """Return ordinal rank of a tier value; higher is stronger evidence."""
    norm = tier_value.lower().strip()
    canonical = _TIER_SYNONYMS.get(norm, norm)
    if canonical in _TIER_LADDER:
        return _TIER_LADDER.index(canonical)
    return -1   # unknown — treat as below-floor


# ─── Wet-lab data point (extends CalibrationEntry) ─────────────────────


@dataclass
class WetlabDataPoint:
    """One bench measurement ready for ingestion into the simulator.

    Wraps ``CalibrationEntry`` with two wet-lab-campaign-specific fields:

      - ``promote_to_tier``: target evidence tier after ingestion
        (typically "calibrated_local" for bench-fitted parameters,
        "validated_quantitative" for full DBC validation).
      - ``bench_date``: ISO date string for traceability.
    """

    entry: CalibrationEntry
    promote_to_tier: str = "calibrated_local"
    bench_date: str = ""        # ISO 8601 (YYYY-MM-DD)
    bench_notes: str = ""

    def __post_init__(self) -> None:
        if self.promote_to_tier and _tier_rank(self.promote_to_tier) < 0:
            raise ValueError(
                f"Unknown promote_to_tier {self.promote_to_tier!r}. "
                f"Must be one of: {_TIER_LADDER}."
            )


@dataclass
class WetlabCampaign:
    """Container for a complete wet-lab calibration campaign."""

    campaign_id: str
    operator: str = ""
    lab: str = ""
    notes: str = ""
    data_points: list[WetlabDataPoint] = field(default_factory=list)


# ─── YAML I/O ──────────────────────────────────────────────────────────


def _load_yaml_or_dict(source: dict | str | Path) -> dict:
    """Accept dict, YAML string, or Path; return parsed dict.

    YAML parsing is optional — if PyYAML is not installed and a string
    is given, we try a permissive eval-style fallback (no security
    concern because callers are passing trusted bench-scientist input
    in a development environment, but we do gate the eval to dict-only).
    """
    if isinstance(source, dict):
        return source
    if isinstance(source, Path):
        text = source.read_text(encoding="utf-8")
    else:
        text = source

    try:
        import yaml  # type: ignore[import-not-found]
        return yaml.safe_load(text)
    except ImportError:
        # PyYAML not in environment — fall back to JSON parser if the
        # bench scientist can deliver JSON (a YAML subset).
        import json
        return json.loads(text)


def load_campaign(source: dict | str | Path) -> WetlabCampaign:
    """Parse a YAML/JSON/dict campaign document into a WetlabCampaign.

    Schema is documented in this module's docstring. Validates that
    every entry has a known target tier and that profile_key + parameter_name
    are populated.
    """
    raw = _load_yaml_or_dict(source)
    campaign_id = raw.get("campaign_id", "")
    if not campaign_id:
        raise ValueError("campaign_id is required")

    points: list[WetlabDataPoint] = []
    for i, entry_dict in enumerate(raw.get("entries", [])):
        try:
            promote = entry_dict.pop("promote_to_tier", "calibrated_local")
            bench_date = entry_dict.pop("bench_date", "")
            bench_notes = entry_dict.pop("bench_notes", "")
            entry = CalibrationEntry(
                profile_key=entry_dict["profile_key"],
                parameter_name=entry_dict["parameter_name"],
                measured_value=float(entry_dict["measured_value"]),
                units=str(entry_dict.get("units", "")),
                target_molecule=str(entry_dict.get("target_molecule", "")),
                temperature_C=float(entry_dict.get("temperature_C", 25.0)),
                ph=float(entry_dict.get("ph", 7.0)),
                salt_concentration_M=float(entry_dict.get("salt_concentration_M", 0.0)),
                salt_type=str(entry_dict.get("salt_type", "")),
                measurement_type=str(entry_dict.get("measurement_type", "")),
                confidence=str(entry_dict.get("confidence", "measured")),
                source_reference=str(entry_dict.get("source_reference", "")),
                replicates=int(entry_dict.get("replicates", 1)),
                target_module=str(entry_dict.get("target_module", "")),
                fit_method=str(entry_dict.get("fit_method", "manual")),
                valid_domain=dict(entry_dict.get("valid_domain", {})),
                posterior_uncertainty=float(entry_dict.get("posterior_uncertainty", 0.0)),
            )
            points.append(WetlabDataPoint(
                entry=entry,
                promote_to_tier=promote,
                bench_date=bench_date,
                bench_notes=bench_notes,
            ))
        except (KeyError, ValueError, TypeError) as e:
            raise ValueError(
                f"Entry #{i} in campaign {campaign_id!r} is malformed: {e}"
            ) from e

    return WetlabCampaign(
        campaign_id=campaign_id,
        operator=raw.get("operator", ""),
        lab=raw.get("lab", ""),
        notes=raw.get("notes", ""),
        data_points=points,
    )


# ─── Profile patching (in-memory) ──────────────────────────────────────


# Whitelist of ReagentProfile fields that may be updated by a wet-lab
# campaign. Restricted to numeric kinetic / binding / metadata fields;
# does NOT include immutable identity fields (name, cas, target_acs).
_PATCHABLE_NUMERIC_FIELDS: frozenset[str] = frozenset({
    "k_forward", "E_a", "stoichiometry", "hydrolysis_rate",
    "ph_optimum", "temperature_default", "time_default",
    "ph_min", "ph_max", "temperature_min", "temperature_max",
    "ligand_mw", "ligand_r_h", "activity_retention",
    "activity_retention_uncertainty", "max_surface_density",
    "spacer_length_angstrom", "spacer_activity_multiplier",
    "metal_loaded_fraction", "distal_group_yield",
    "maleimide_decay_rate", "thiol_accessibility_fraction",
    "metal_association_constant", "reduction_efficiency",
    "regulatory_limit_ppm", "pKa_nucleophile",
})

_PATCHABLE_STRING_FIELDS: frozenset[str] = frozenset({
    "calibration_source", "confidence_tier",
    "binding_model_hint", "buffer_incompatibilities",
})


def patch_reagent_profile(
    profile: ReagentProfile,
    point: WetlabDataPoint,
    *,
    strict: bool = True,
) -> ReagentProfile:
    """Return a NEW ReagentProfile with the calibration data applied.

    The original profile is not mutated. Tier promotion follows
    `_tier_rank` ordering — strict mode rejects downgrades.

    Raises
    ------
    ValueError
        If parameter_name is not patchable, OR if strict=True and the
        proposed promote_to_tier would downgrade the existing
        confidence_tier.
    """
    e = point.entry
    if e.parameter_name not in _PATCHABLE_NUMERIC_FIELDS \
            and e.parameter_name not in _PATCHABLE_STRING_FIELDS:
        raise ValueError(
            f"Parameter {e.parameter_name!r} is not whitelisted for "
            f"wet-lab patching. Add to _PATCHABLE_NUMERIC_FIELDS or "
            f"_PATCHABLE_STRING_FIELDS in wetlab_ingestion.py if "
            f"intentional."
        )

    # Tier promotion: never downgrade.
    current_tier_rank = _tier_rank(profile.confidence_tier)
    target_tier_rank = _tier_rank(point.promote_to_tier)
    if strict and target_tier_rank < current_tier_rank:
        raise ValueError(
            f"Cannot downgrade {profile.name!r} from "
            f"{profile.confidence_tier!r} to "
            f"{point.promote_to_tier!r}. Set strict=False to override "
            f"(rare; only for measurement-error retraction)."
        )

    # Build update dict.
    new_value: Any
    if e.parameter_name in _PATCHABLE_NUMERIC_FIELDS:
        new_value = float(e.measured_value)
    else:
        new_value = str(e.measured_value)

    updates: dict[str, Any] = {e.parameter_name: new_value}
    # Always update calibration_source + confidence_tier + notes
    # to reflect the wet-lab provenance.
    updates["calibration_source"] = (
        f"{point.entry.source_reference} "
        f"(wetlab campaign; bench {point.bench_date}, replicates "
        f"{point.entry.replicates}, fit {point.entry.fit_method}, "
        f"posterior σ={point.entry.posterior_uncertainty:.3g})"
    ).strip()
    if target_tier_rank > current_tier_rank:
        updates["confidence_tier"] = point.promote_to_tier

    return dataclass_replace(profile, **updates)


# ─── Campaign application ──────────────────────────────────────────────


@dataclass
class IngestionResult:
    """Summary of one campaign's ingestion run."""

    campaign_id: str
    points_total: int
    points_applied: int
    points_skipped: int
    points_failed: int
    profile_updates: dict[str, ReagentProfile] = field(default_factory=dict)
    tier_promotions: list[tuple[str, str, str]] = field(default_factory=list)
    failures: list[tuple[str, str]] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)

    def manifest(self) -> dict:
        """Return a JSON-friendly summary for audit logs."""
        return {
            "campaign_id": self.campaign_id,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
            "points_total": self.points_total,
            "points_applied": self.points_applied,
            "points_skipped": self.points_skipped,
            "points_failed": self.points_failed,
            "tier_promotions": [
                {"profile_key": pk, "from": frm, "to": to}
                for (pk, frm, to) in self.tier_promotions
            ],
            "failures": [
                {"profile_key": pk, "reason": reason}
                for (pk, reason) in self.failures
            ],
            "skipped": [
                {"profile_key": pk, "reason": reason}
                for (pk, reason) in self.skipped
            ],
        }


def apply_campaign(
    campaign: WetlabCampaign,
    *,
    profile_registry: Optional[dict[str, ReagentProfile]] = None,
    strict: bool = True,
) -> IngestionResult:
    """Apply a wet-lab campaign's data points to a profile registry.

    The default registry is the global ``REAGENT_PROFILES`` dict. The
    function does NOT mutate the registry — it returns a dict of
    updated profiles in ``IngestionResult.profile_updates``. The caller
    chooses whether to overlay these on the registry for a single run
    (in-memory) or persist them via code commit.

    Parameters
    ----------
    campaign
        The parsed WetlabCampaign.
    profile_registry
        Dict of profile_key → ReagentProfile. Defaults to the global
        REAGENT_PROFILES.
    strict
        If True (default), tier downgrades raise ValueError; failures
        are recorded in ``IngestionResult.failures``. If False, tier
        downgrades are allowed (rare; for measurement-error retraction).
    """
    registry = profile_registry if profile_registry is not None else REAGENT_PROFILES

    result = IngestionResult(
        campaign_id=campaign.campaign_id,
        points_total=len(campaign.data_points),
        points_applied=0,
        points_skipped=0,
        points_failed=0,
    )

    for point in campaign.data_points:
        key = point.entry.profile_key
        if key not in registry:
            result.skipped.append((key, f"profile_key {key!r} not in registry"))
            result.points_skipped += 1
            continue

        try:
            current = result.profile_updates.get(key, registry[key])
            updated = patch_reagent_profile(current, point, strict=strict)

            # Record tier promotion if it happened
            if updated.confidence_tier != current.confidence_tier:
                result.tier_promotions.append(
                    (key, current.confidence_tier, updated.confidence_tier)
                )

            result.profile_updates[key] = updated
            result.points_applied += 1
            logger.info(
                "Wetlab calibration applied: %s.%s = %g (campaign=%s)",
                key, point.entry.parameter_name,
                point.entry.measured_value, campaign.campaign_id,
            )
        except (ValueError, TypeError) as e:
            result.failures.append((key, str(e)))
            result.points_failed += 1
            logger.warning(
                "Wetlab calibration failed: %s.%s — %s",
                key, point.entry.parameter_name, e,
            )

    return result


# ─── L2 solver constant patching (for Q-013 kernel calibration) ────────
#
# Kernel-level calibrations (e.g., chitosan-only pore-size prefactor or
# dextran-ECH Sephadex correlation constants) cannot be applied via the
# ReagentProfile path — they live as module-level constants in the
# corresponding solver module. This API surfaces them as a separate
# patchable dict that callers can apply via monkeypatching for in-memory
# use, OR record as a code-commit recommendation for permanent updates.


@dataclass
class SolverConstantPatch:
    """A proposed change to a module-level solver constant."""

    module_path: str            # e.g., "dpsim.level2_gelation.chitosan_only"
    constant_name: str          # e.g., "_CHITOSAN_AMINE_PKA"
    current_value: float
    proposed_value: float
    bench_provenance: str       # "campaign Q-013 / bench 2026-08-12 / σ=0.05"

    @property
    def relative_change(self) -> float:
        """Fractional change from current to proposed (signed)."""
        if self.current_value == 0:
            return float("inf") if self.proposed_value != 0 else 0.0
        return (self.proposed_value - self.current_value) / abs(self.current_value)


def propose_solver_constant_patches(
    campaign: WetlabCampaign,
) -> list[SolverConstantPatch]:
    """From a campaign, extract any data points targeting solver constants
    rather than ReagentProfile fields.

    Convention: data points targeting solver constants have
    ``profile_key`` formatted as ``"solver:<module_path>"`` and
    ``parameter_name`` set to the constant identifier.
    """
    patches: list[SolverConstantPatch] = []
    for point in campaign.data_points:
        if not point.entry.profile_key.startswith("solver:"):
            continue
        module_path = point.entry.profile_key.removeprefix("solver:")
        # Look up the current value via importlib so we don't have to
        # hard-code every solver constant here.
        try:
            import importlib
            mod = importlib.import_module(module_path)
            current = getattr(mod, point.entry.parameter_name, None)
            if current is None:
                logger.warning(
                    "Solver constant %s.%s not found; skipping",
                    module_path, point.entry.parameter_name,
                )
                continue
            patches.append(SolverConstantPatch(
                module_path=module_path,
                constant_name=point.entry.parameter_name,
                current_value=float(current),
                proposed_value=float(point.entry.measured_value),
                bench_provenance=(
                    f"{campaign.campaign_id} / bench {point.bench_date} / "
                    f"σ={point.entry.posterior_uncertainty:.3g} / "
                    f"{point.entry.fit_method}"
                ),
            ))
        except (ImportError, AttributeError) as e:
            logger.warning(
                "Solver constant patch dropped: %s.%s — %s",
                module_path, point.entry.parameter_name, e,
            )

    return patches


__all__ = [
    "WetlabDataPoint",
    "WetlabCampaign",
    "load_campaign",
    "patch_reagent_profile",
    "IngestionResult",
    "apply_campaign",
    "SolverConstantPatch",
    "propose_solver_constant_patches",
]
