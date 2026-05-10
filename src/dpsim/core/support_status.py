"""Support-status vocabulary shared by docs, UI, and validation code."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class SupportStatus(Enum):
    """Canonical maturity labels for features and model families."""

    LIVE = "live"
    SCREENING = "screening"
    REQUIRES_CALIBRATION = "requires_calibration"
    SCAFFOLDED = "scaffolded"
    DEFERRED = "deferred"
    OUT_OF_SCOPE = "out_of_scope"


@dataclass(frozen=True)
class FeatureSupportRecord:
    """One support-ledger row consumable by both docs and UI."""

    key: str
    title: str
    status: SupportStatus
    owner: str = ""
    evidence: str = ""
    limitations: tuple[str, ...] = ()
    required_calibrations: tuple[str, ...] = ()
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["limitations"] = list(self.limitations)
        data["required_calibrations"] = list(self.required_calibrations)
        return data


SUPPORT_STATUS_DESCRIPTIONS: dict[SupportStatus, str] = {
    SupportStatus.LIVE: "Production-use ready inside its stated validation domain.",
    SupportStatus.SCREENING: "Suitable for trend/ranking use, not unqualified numbers.",
    SupportStatus.REQUIRES_CALIBRATION: "Implemented but blocked from quantitative claims.",
    SupportStatus.SCAFFOLDED: "API or UI exists; physics/data path is incomplete.",
    SupportStatus.DEFERRED: "Designed but intentionally outside the current release line.",
    SupportStatus.OUT_OF_SCOPE: "Rejected for this architecture unless reopened by ADR.",
}


__all__ = [
    "FeatureSupportRecord",
    "SupportStatus",
    "SUPPORT_STATUS_DESCRIPTIONS",
]
