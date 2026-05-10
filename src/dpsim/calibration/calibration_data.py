"""Calibration data types for user-supplied measured parameters.

v6.0-alpha: Typed schema with units, target molecule, validity domain,
and source reference (audit F2 requirement).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass
class CalibrationEntry:
    """A single calibration measurement for a reagent profile parameter.

    Captures not just the value, but the conditions under which it was
    measured, so the simulator can validate applicability.

    Attributes:
        profile_key: Reagent profile key (e.g., "protein_a_coupling").
        parameter_name: Parameter being calibrated (e.g., "q_max", "K_L",
            "activity_retention", "estimated_q_max").
        measured_value: The measured value in the specified units.
        units: SI or common units (e.g., "mg/mL", "mol/m3", "fraction").
        target_molecule: Identity of the target protein/analyte.
        temperature_C: Measurement temperature [Celsius].
        ph: Measurement pH.
        salt_concentration_M: Salt concentration [M] during measurement.
        salt_type: Salt identity (e.g., "NaCl", "(NH4)2SO4").
        measurement_type: How the value was measured.
        confidence: Data quality tier.
        source_reference: Literature reference or lab notebook ID.
        replicates: Number of independent replicates.
    """
    profile_key: str
    parameter_name: str
    measured_value: float
    units: str
    target_molecule: str = ""
    temperature_C: float = 25.0
    ph: float = 7.0
    salt_concentration_M: float = 0.0
    salt_type: str = ""
    measurement_type: str = ""    # "static_binding", "DBC10", "DBC5", "batch_uptake"
    confidence: str = "measured"  # "measured", "literature", "estimated"
    source_reference: str = ""
    replicates: int = 1
    # v6.1: cross-module calibration support
    target_module: str = ""       # "L1", "L2", "L3", "L4", "M2", "M3", "" (legacy FMC)
    fit_method: str = "manual"    # "manual", "least_squares", "bayesian"
    valid_domain: dict = field(default_factory=dict)  # parameter ranges where calibration applies
    posterior_uncertainty: float = 0.0  # standard deviation of fitted parameter
    # v0.6.5 (B-2a / W-009): assay quantitation / detection limit.
    # Below this measured value the assay is operationally non-detectable;
    # the wash-residuals model uses it to gate "meets_assay_limit" flags
    # and to upgrade the evidence tier from QUALITATIVE_TREND when present.
    # Units must match the parameter (mol/m^3 for concentrations).
    assay_detection_limit: float = 0.0     # 0 = not measured / not declared
    assay_quantitation_limit: float = 0.0  # LOQ; >= LOD when both set

    def to_dict(self) -> dict:
        """Serialize to dict for JSON storage."""
        return {
            "profile_key": self.profile_key,
            "parameter_name": self.parameter_name,
            "measured_value": self.measured_value,
            "units": self.units,
            "target_molecule": self.target_molecule,
            "temperature_C": self.temperature_C,
            "ph": self.ph,
            "salt_concentration_M": self.salt_concentration_M,
            "salt_type": self.salt_type,
            "measurement_type": self.measurement_type,
            "confidence": self.confidence,
            "source_reference": self.source_reference,
            "replicates": self.replicates,
            "target_module": self.target_module,
            "fit_method": self.fit_method,
            "valid_domain": self.valid_domain,
            "posterior_uncertainty": self.posterior_uncertainty,
            "assay_detection_limit": self.assay_detection_limit,
            "assay_quantitation_limit": self.assay_quantitation_limit,
        }

    @classmethod
    def from_dict(cls, d: dict) -> CalibrationEntry:
        """Deserialize from dict."""
        return cls(
            profile_key=d["profile_key"],
            parameter_name=d["parameter_name"],
            measured_value=float(d["measured_value"]),
            units=d.get("units", ""),
            target_molecule=d.get("target_molecule", ""),
            temperature_C=float(d.get("temperature_C", 25.0)),
            ph=float(d.get("ph", 7.0)),
            salt_concentration_M=float(d.get("salt_concentration_M", 0.0)),
            salt_type=d.get("salt_type", ""),
            measurement_type=d.get("measurement_type", ""),
            confidence=d.get("confidence", "measured"),
            source_reference=d.get("source_reference", ""),
            replicates=int(d.get("replicates", 1)),
            target_module=d.get("target_module", ""),
            fit_method=d.get("fit_method", "manual"),
            valid_domain=d.get("valid_domain", {}),
            posterior_uncertainty=float(d.get("posterior_uncertainty", 0.0)),
            assay_detection_limit=float(d.get("assay_detection_limit", 0.0)),
            assay_quantitation_limit=float(d.get("assay_quantitation_limit", 0.0)),
        )


@dataclass(frozen=True)
class CalibrationDataset:
    """A governed wet-lab assay dataset before fitting or tier promotion."""

    dataset_id: str
    assay_ids: tuple[str, ...]
    assay_kind: str
    target_molecule: str = ""
    polymer_family: str = ""
    mobile_phase: str = ""
    temperature_C: Optional[float] = None
    ph: Optional[float] = None
    salt_concentration_M: Optional[float] = None
    source_file: str = ""
    quality_status: str = "unchecked"
    issues: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["assay_ids"] = list(self.assay_ids)
        data["issues"] = list(self.issues)
        return data

    @property
    def content_hash(self) -> str:
        blob = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CalibrationApplicability:
    """Result of checking whether a calibration applies to a recipe context."""

    applicable: bool
    status: str
    reasons: tuple[str, ...] = ()
    matched_domain: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["reasons"] = list(self.reasons)
        return data


@dataclass(frozen=True)
class CalibrationFit:
    """First-class artifact emitted by calibration fitting workflows."""

    fit_id: str
    parameter_name: str
    value: float
    units: str
    fit_method: str
    source_assay_ids: tuple[str, ...]
    diagnostics: dict[str, Any] = field(default_factory=dict)
    valid_domain: dict[str, Any] = field(default_factory=dict)
    posterior_uncertainty: float = 0.0
    tier_promotion_recommendation: str = "none"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["source_assay_ids"] = list(self.source_assay_ids)
        return data

    @property
    def content_hash(self) -> str:
        blob = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()
