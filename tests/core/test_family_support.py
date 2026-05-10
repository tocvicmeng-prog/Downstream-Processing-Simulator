from dpsim.core.family_support import family_support_record, registered_family_support
from dpsim.core.support_status import SupportStatus
from dpsim.datatypes import ModelEvidenceTier, PolymerFamily


def test_registry_covers_required_audit_families():
    families = {
        record.family.value
        for record in registered_family_support()
    }
    assert PolymerFamily.AGAROSE_CHITOSAN.value in families
    assert PolymerFamily.ALGINATE.value in families
    assert PolymerFamily.CELLULOSE.value in families
    assert PolymerFamily.PLGA.value in families
    assert PolymerFamily.PULLULAN_DEXTRAN.value in families


def test_agarose_chitosan_screening_ceiling_is_semi_quantitative():
    record = family_support_record(PolymerFamily.AGAROSE_CHITOSAN)
    assert record.status == SupportStatus.SCREENING
    assert record.maximum_uncalibrated_tier == ModelEvidenceTier.SEMI_QUANTITATIVE
    assert "pressure-flow curve" in record.calibration_requirements


def test_unregistered_family_falls_back_to_conservative_scaffold():
    record = family_support_record(PolymerFamily.CHITIN)
    assert record.status == SupportStatus.SCAFFOLDED
    assert record.maximum_uncalibrated_tier == ModelEvidenceTier.QUALITATIVE_TREND
