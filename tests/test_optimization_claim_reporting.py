import numpy as np

from dpsim.datatypes import OptimizationState
from dpsim.optimization.analysis import (
    inverse_design_quality_label,
    pareto_claims_export,
    pareto_decision_claims,
    wetlab_actionability_score,
)


def _state():
    return OptimizationState(
        X_observed=np.zeros((1, 7)),
        Y_observed=np.zeros((1, 3)),
        pareto_X=np.zeros((1, 7)),
        pareto_Y=np.array([[0.1, 0.2, 0.3]]),
        iteration=1,
        hypervolume=0.0,
        pareto_evidence_tiers=["semi_quantitative"],
    )


def test_pareto_decision_claims_use_state_tiers():
    claims = pareto_decision_claims(_state())
    assert len(claims) == 1
    assert len(claims[0]) == 3
    assert claims[0][0].evidence_tier.value == "semi_quantitative"
    assert claims[0][0].assay_required == "DSD"


def test_pareto_claims_export_is_json_safe():
    rows = pareto_claims_export(_state())
    assert rows[0]["claims"][0]["render_mode"]
    assert rows[0]["evidence_tier"] == "semi_quantitative"


def test_actionability_score_decreases_with_missing_assays():
    good = wetlab_actionability_score(
        missing_assays=0,
        reagent_hazard_score=1,
        protocol_duration_h=4,
        pressure_headroom=0.4,
        calibration_distance=0.1,
    )
    bad = wetlab_actionability_score(
        missing_assays=8,
        reagent_hazard_score=4,
        protocol_duration_h=30,
        pressure_headroom=1.2,
        calibration_distance=0.9,
    )
    assert 0.0 <= bad < good <= 1.0


def test_inverse_design_quality_label_blocks_weak_posteriors():
    assert inverse_design_quality_label(n_measurements=3, ess=200.0).startswith("advisory")
    assert inverse_design_quality_label(n_measurements=10, ess=20.0) == "advisory_low_ess"
    assert inverse_design_quality_label(n_measurements=10, ess=200.0) == "calibration_supported"
