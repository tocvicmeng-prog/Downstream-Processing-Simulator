"""Polymer-family support registry for model maturity and calibration gates."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from dpsim.core.support_status import SupportStatus
from dpsim.datatypes import ModelEvidenceTier, PolymerFamily


@dataclass(frozen=True)
class FamilySupportRecord:
    """Scientific support status for one polymer family."""

    family: PolymerFamily
    fabrication_route: str
    l1_model: str
    l2_model: str
    l3_model: str
    l4_model: str
    m2_compatibility: str
    m3_pressure_support: SupportStatus
    status: SupportStatus
    maximum_uncalibrated_tier: ModelEvidenceTier
    calibration_requirements: tuple[str, ...]
    limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["family"] = self.family.value
        data["m3_pressure_support"] = self.m3_pressure_support.value
        data["status"] = self.status.value
        data["maximum_uncalibrated_tier"] = self.maximum_uncalibrated_tier.value
        data["calibration_requirements"] = list(self.calibration_requirements)
        data["limitations"] = list(self.limitations)
        return data


_DEFAULT_CALIBRATION_REQUIREMENTS = (
    "DSD vs RPM/viscosity",
    "pore size and porosity",
    "modulus/compression",
    "pressure-flow curve",
    "static binding or DBC breakthrough",
)


FAMILY_SUPPORT_REGISTRY: dict[str, FamilySupportRecord] = {
    PolymerFamily.AGAROSE_CHITOSAN.value: FamilySupportRecord(
        family=PolymerFamily.AGAROSE_CHITOSAN,
        fabrication_route="thermal agarose gelation with chitosan/genipin secondary network",
        l1_model="rotor-stator PBE screening kernel",
        l2_model="Cahn-Hilliard / empirical pore surrogate",
        l3_model="genipin crosslinking surrogate",
        l4_model="double-network modulus surrogate",
        m2_compatibility="native amine + hydroxyl chemistry; Protein A reference workflow",
        m3_pressure_support=SupportStatus.SCREENING,
        status=SupportStatus.SCREENING,
        maximum_uncalibrated_tier=ModelEvidenceTier.SEMI_QUANTITATIVE,
        calibration_requirements=_DEFAULT_CALIBRATION_REQUIREMENTS,
        limitations=(
            "Pressure and DBC are not point-design claims without packed-bed calibration.",
            "Functional ligand density requires direct assay evidence.",
        ),
    ),
    PolymerFamily.ALGINATE.value: FamilySupportRecord(
        family=PolymerFamily.ALGINATE,
        fabrication_route="ionotropic gelation",
        l1_model="screening transfer from emulsion droplet formation",
        l2_model="ionic gel-front / mesh-size surrogate",
        l3_model="Ca/Ba ion exchange gelation registry",
        l4_model="empirical modulus proxy",
        m2_compatibility="carboxylate chemistry; EDC/NHS routes preferred",
        m3_pressure_support=SupportStatus.SCREENING,
        status=SupportStatus.REQUIRES_CALIBRATION,
        maximum_uncalibrated_tier=ModelEvidenceTier.QUALITATIVE_TREND,
        calibration_requirements=_DEFAULT_CALIBRATION_REQUIREMENTS,
        limitations=("Ionotropic-gel transfer is family-specific and must be calibrated.",),
    ),
    PolymerFamily.CELLULOSE.value: FamilySupportRecord(
        family=PolymerFamily.CELLULOSE,
        fabrication_route="NIPS / phase inversion",
        l1_model="NIPS morphology surrogate",
        l2_model="spinodal-wavelength pore surrogate",
        l3_model="cellulose activation chemistry registry",
        l4_model="empirical modulus proxy",
        m2_compatibility="hydroxyl activation routes; CNBr/CDI compatible",
        m3_pressure_support=SupportStatus.SCREENING,
        status=SupportStatus.REQUIRES_CALIBRATION,
        maximum_uncalibrated_tier=ModelEvidenceTier.QUALITATIVE_TREND,
        calibration_requirements=_DEFAULT_CALIBRATION_REQUIREMENTS,
        limitations=("NIPS morphology is not interchangeable with agarose emulsion gelation.",),
    ),
    PolymerFamily.PLGA.value: FamilySupportRecord(
        family=PolymerFamily.PLGA,
        fabrication_route="solvent evaporation",
        l1_model="emulsion-solvent evaporation screening surrogate",
        l2_model="free-volume / glassy-polymer pore proxy",
        l3_model="surface activation registry",
        l4_model="glassy polymer modulus proxy",
        m2_compatibility="surface activation required; hydrolysis risk",
        m3_pressure_support=SupportStatus.REQUIRES_CALIBRATION,
        status=SupportStatus.REQUIRES_CALIBRATION,
        maximum_uncalibrated_tier=ModelEvidenceTier.QUALITATIVE_TREND,
        calibration_requirements=_DEFAULT_CALIBRATION_REQUIREMENTS,
        limitations=("Organic-solvent route and hydrolysis risk block analogy-based quantitative claims.",),
    ),
    PolymerFamily.PULLULAN_DEXTRAN.value: FamilySupportRecord(
        family=PolymerFamily.PULLULAN_DEXTRAN,
        fabrication_route="neutral polysaccharide composite screening route",
        l1_model="composite transfer surrogate",
        l2_model="pullulan/dextran empirical gel surrogate",
        l3_model="hydroxyl activation registry",
        l4_model="placeholder composite modulus proxy",
        m2_compatibility="hydroxyl activation routes; requires ligand-density assay",
        m3_pressure_support=SupportStatus.SCAFFOLDED,
        status=SupportStatus.SCAFFOLDED,
        maximum_uncalibrated_tier=ModelEvidenceTier.QUALITATIVE_TREND,
        calibration_requirements=_DEFAULT_CALIBRATION_REQUIREMENTS,
        limitations=("Composite support is intentionally screening-only until family data exist.",),
    ),
}


def family_support_record(family: PolymerFamily | str) -> FamilySupportRecord:
    """Return support metadata, falling back to a conservative scaffold row."""
    value = family.value if isinstance(family, PolymerFamily) else str(family)
    if value in FAMILY_SUPPORT_REGISTRY:
        return FAMILY_SUPPORT_REGISTRY[value]
    return FamilySupportRecord(
        family=PolymerFamily(value) if value in {f.value for f in PolymerFamily} else PolymerFamily.AGAROSE_CHITOSAN,
        fabrication_route="unregistered family route",
        l1_model="unregistered",
        l2_model="unregistered",
        l3_model="unregistered",
        l4_model="unregistered",
        m2_compatibility="unregistered",
        m3_pressure_support=SupportStatus.SCAFFOLDED,
        status=SupportStatus.SCAFFOLDED,
        maximum_uncalibrated_tier=ModelEvidenceTier.QUALITATIVE_TREND,
        calibration_requirements=_DEFAULT_CALIBRATION_REQUIREMENTS,
        limitations=(f"No explicit family-support record for {value!r}.",),
    )


def registered_family_support() -> tuple[FamilySupportRecord, ...]:
    """Return registry rows sorted by family value."""
    return tuple(FAMILY_SUPPORT_REGISTRY[key] for key in sorted(FAMILY_SUPPORT_REGISTRY))


__all__ = [
    "FAMILY_SUPPORT_REGISTRY",
    "FamilySupportRecord",
    "family_support_record",
    "registered_family_support",
]
